import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from bridge import Bridge, InvalidOrder


def order(oid='ORDER-1', qty=2, sku='CUP-01'):
    return {'id':oid, 'currency':'RUB', 'items':[{'sku':sku,'qty':qty}]}


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.sqlite'
        self.b = Bridge(self.path)
        self.b.seed()

    def tearDown(self):
        self.b.close()
        self.tmp.cleanup()

    def test_exact_total_and_reservation(self):
        self.assertEqual(self.b.accept(order())['total_kopecks'], 258000)
        self.assertEqual(self.b.db.execute("SELECT qty FROM stock WHERE sku='CUP-01'").fetchone()[0], 10)

    def test_duplicate_survives_restart(self):
        self.b.accept(order())
        self.b.close()
        self.b = Bridge(self.path)
        self.b.seed()
        self.assertEqual(self.b.accept(order())['status'], 'duplicate')
        self.assertEqual(self.b.db.execute("SELECT qty FROM stock WHERE sku='CUP-01'").fetchone()[0], 10)

    def test_conflicting_id_is_rejected(self):
        self.b.accept(order())
        with self.assertRaises(InvalidOrder):
            self.b.accept(order(qty=3))

    def test_invalid_quantities(self):
        for qty in [0,-1,1.5,True,'2',10001]:
            with self.subTest(qty=qty), self.assertRaises(InvalidOrder):
                self.b.accept(order(qty=qty))

    def test_currency_and_structure(self):
        for raw in [None, [], {}, {**order(),'currency':'USD'}, {**order(),'id':'=SUM(A1)'}, {**order(),'items':[]}]:
            with self.subTest(raw=raw), self.assertRaises(InvalidOrder):
                self.b.accept(raw)

    def test_atomic_rollback_on_unknown_product(self):
        raw = order()
        raw['items'].append({'sku':'MISSING','qty':1})
        with self.assertRaises(InvalidOrder):
            self.b.accept(raw)
        self.assertEqual(self.b.report()['orders'], [])
        self.assertEqual(self.b.db.execute("SELECT qty FROM stock WHERE sku='CUP-01'").fetchone()[0], 12)

    def test_no_overselling(self):
        self.b.accept(order(qty=12))
        with self.assertRaises(InvalidOrder):
            self.b.accept(order('ORDER-2',1))

    def test_merge_items_before_stock_check(self):
        raw = order(qty=8)
        raw['items'].append({'sku':'CUP-01','qty':8})
        with self.assertRaises(InvalidOrder):
            self.b.accept(raw)

    def test_reordered_items_are_same_order(self):
        raw = order()
        raw['items'].append({'sku':'FILTER-02','qty':1})
        self.b.accept(raw)
        raw['items'].reverse()
        self.assertEqual(self.b.accept(raw)['status'], 'duplicate')

    def test_retry_after_timeout(self):
        self.b.accept(order())
        self.b.deliver(fail_once=True)
        self.assertEqual(self.b.report()['orders'][0]['status'], 'retry')
        self.b.deliver()
        report = self.b.report()
        self.assertEqual(report['orders'][0]['attempts'], 2)
        self.assertEqual(report['receiver_count'], 1)

    def test_lost_acknowledgement_does_not_duplicate(self):
        self.b.accept(order())
        self.b.deliver(crash_after_receive=True)
        self.b.deliver()
        self.assertEqual(self.b.report()['receiver_count'], 1)
        self.assertEqual(self.b.report()['orders'][0]['status'], 'sent')

    def test_concurrent_acceptance(self):
        def accept(_):
            b = Bridge(self.path)
            try:
                return b.accept(order())['status']
            finally:
                b.close()
        with ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(accept, range(8)))
        self.assertEqual(statuses.count('accepted'),1)
        self.assertEqual(statuses.count('duplicate'),7)
        self.assertEqual(self.b.db.execute("SELECT qty FROM stock WHERE sku='CUP-01'").fetchone()[0], 10)


if __name__ == '__main__':
    unittest.main(verbosity=2)
