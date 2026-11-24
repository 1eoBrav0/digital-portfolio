"""Offline order integration demo. Python 3.11+, standard library only."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from pathlib import Path


class InvalidOrder(ValueError):
    pass


def normalize(raw):
    if not isinstance(raw, dict):
        raise InvalidOrder('Order must be an object')
    oid = raw.get('id')
    if not isinstance(oid, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,60}', oid):
        raise InvalidOrder('Invalid order id')
    if raw.get('currency') != 'RUB':
        raise InvalidOrder('Only RUB is supported')
    items = raw.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise InvalidOrder('Expected 1–100 items')
    merged = {}
    for item in items:
        if not isinstance(item, dict):
            raise InvalidOrder('Invalid item')
        sku, qty = item.get('sku'), item.get('qty')
        if not isinstance(sku, str) or not re.fullmatch(r'[A-Z0-9-]{1,40}', sku):
            raise InvalidOrder('Invalid SKU')
        if type(qty) is not int or not 1 <= qty <= 10000:
            raise InvalidOrder('Quantity must be an integer from 1 to 10000')
        merged[sku] = merged.get(sku, 0) + qty
        if merged[sku] > 10000:
            raise InvalidOrder('Combined quantity too large')
    return {'id': oid, 'currency': 'RUB', 'items': [
        {'sku': sku, 'qty': merged[sku]} for sku in sorted(merged)]}


class Bridge:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=10)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS stock(sku TEXT PRIMARY KEY, price INTEGER NOT NULL CHECK(price>=0), qty INTEGER NOT NULL CHECK(qty>=0));
        CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY, digest TEXT NOT NULL, total INTEGER NOT NULL, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS outbox(order_id TEXT PRIMARY KEY REFERENCES orders(id), status TEXT NOT NULL DEFAULT 'pending', attempts INTEGER NOT NULL DEFAULT 0, error TEXT);
        CREATE TABLE IF NOT EXISTS receiver(order_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        ''')

    def close(self):
        self.db.close()

    def seed(self):
        # INSERT OR IGNORE never replenishes already reserved stock on a rerun.
        with self.db:
            self.db.executemany('INSERT OR IGNORE INTO stock VALUES(?,?,?)',
                                [('CUP-01', 129000, 12), ('FILTER-02', 59000, 20), ('BEANS-03', 89000, 15)])

    def accept(self, raw):
        order = normalize(raw)
        payload = json.dumps(order, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        try:
            # Serialize stock checks and updates across concurrent processes.
            self.db.execute('BEGIN IMMEDIATE')
            old = self.db.execute('SELECT digest,total FROM orders WHERE id=?', (order['id'],)).fetchone()
            if old:
                if old[0] != digest:
                    raise InvalidOrder('Same ID has conflicting content')
                self.db.commit()
                return {'id': order['id'], 'status': 'duplicate', 'total_kopecks': old[1]}
            total = 0
            for item in order['items']:
                stock = self.db.execute('SELECT price,qty FROM stock WHERE sku=?', (item['sku'],)).fetchone()
                if not stock:
                    raise InvalidOrder('Unknown SKU: ' + item['sku'])
                if stock[1] < item['qty']:
                    raise InvalidOrder('Insufficient stock: ' + item['sku'])
                total += stock[0] * item['qty']
            for item in order['items']:
                self.db.execute('UPDATE stock SET qty=qty-? WHERE sku=?', (item['qty'], item['sku']))
            self.db.execute('INSERT INTO orders VALUES(?,?,?,?)', (order['id'], digest, total, payload))
            self.db.execute('INSERT INTO outbox(order_id) VALUES(?)', (order['id'],))
            self.db.commit()
            return {'id': order['id'], 'status': 'accepted', 'total_kopecks': total}
        except Exception:
            self.db.rollback()
            raise

    def deliver(self, fail_once=False, crash_after_receive=False):
        """Local receiver simulator. Real integrations need receiver idempotency too."""
        rows = self.db.execute("SELECT o.id,o.payload,b.attempts FROM orders o JOIN outbox b ON o.id=b.order_id WHERE b.status!='sent' ORDER BY o.id").fetchall()
        for oid, payload, attempts in rows:
            with self.db:
                self.db.execute('UPDATE outbox SET attempts=attempts+1 WHERE order_id=?', (oid,))
            if fail_once and attempts == 0:
                with self.db:
                    self.db.execute("UPDATE outbox SET status='retry',error='Simulated timeout' WHERE order_id=?", (oid,))
                continue
            # Deliberately separate transactions model lost acknowledgement.
            with self.db:
                self.db.execute('INSERT OR IGNORE INTO receiver VALUES(?,?)', (oid, payload))
            if crash_after_receive:
                return
            with self.db:
                self.db.execute("UPDATE outbox SET status='sent',error=NULL WHERE order_id=?", (oid,))

    def report(self):
        return {
            'orders': [dict(zip(['id', 'total_kopecks', 'status', 'attempts'], row)) for row in self.db.execute('SELECT o.id,o.total,b.status,b.attempts FROM orders o JOIN outbox b ON o.id=b.order_id ORDER BY o.id')],
            'stock': [dict(zip(['sku','price_kopecks','available'], row)) for row in self.db.execute('SELECT * FROM stock ORDER BY sku')],
            'receiver_count': self.db.execute('SELECT count(*) FROM receiver').fetchone()[0]
        }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', default='sample-orders.json')
    p.add_argument('--db', default='demo.sqlite')
    p.add_argument('--output', default='result')
    args = p.parse_args()
    bridge = Bridge(args.db)
    bridge.seed()
    events = []
    try:
        for raw in json.loads(Path(args.input).read_text(encoding='utf-8')):
            try:
                events.append(bridge.accept(raw))
            except InvalidOrder as error:
                events.append({'id': raw.get('id', '?') if isinstance(raw, dict) else '?', 'status': 'rejected', 'reason': str(error)})
        bridge.deliver(fail_once=True)
        after_timeout = bridge.report()
        bridge.deliver()
        report = {'demo': True, 'events': events, 'after_timeout': after_timeout, **bridge.report()}
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        with (out / 'orders.csv').open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id','total_kopecks','status','attempts'])
            writer.writeheader()
            writer.writerows(report['orders'])
        print(json.dumps({'orders':len(report['orders']), 'receiver':report['receiver_count'], 'events':events}, ensure_ascii=False, indent=2))
    finally:
        bridge.close()


if __name__ == '__main__':
    main()
