from contextlib import closing
"""Offline import of a documented, restricted CommerceML catalog/offers subset."""
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import sqlite3
import xml.etree.ElementTree as ET

NS = "urn:1C.ru:commerceml_2"


def xml(data):
    if len(data) > 2_000_000:
        raise ValueError("XML exceeds 2 MB")
    text = data.decode("utf-8-sig")
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("DTD/entities are forbidden")
    root = ET.fromstring(text)
    if root.tag not in ("КоммерческаяИнформация", "{" + NS + "}КоммерческаяИнформация"):
        raise ValueError("unexpected root or namespace")
    for element in root.iter():
        if element.tag.startswith("{"):
            namespace, name = element.tag[1:].split("}", 1)
            if namespace != NS:
                raise ValueError("unexpected namespace")
            element.tag = name
    if root.get("ВерсияСхемы") != "2.10":
        raise ValueError("only the documented 2.10 subset is supported")
    stamp = datetime.fromisoformat(root.get("ДатаФормирования", ""))
    if stamp.tzinfo is None:
        raise ValueError("generation time requires a timezone")
    return root, stamp.timestamp()


def required(element, path):
    values = element.findall(path)
    if len(values) != 1 or not (values[0].text or "").strip():
        raise ValueError("missing or ambiguous field: " + path)
    return values[0].text.strip()


def parse(catalog_bytes, offer_bytes):
    root, stamp = xml(catalog_bytes)
    offers, offer_stamp = xml(offer_bytes)
    cats, packs = root.findall("Каталог"), offers.findall("ПакетПредложений")
    if len(cats) != 1 or len(packs) != 1 or stamp != offer_stamp:
        raise ValueError("one catalog and matching offers timestamp required")
    cat, pack = cats[0], packs[0]
    catalog_id = required(cat, "Ид")
    if required(pack, "ИдКаталога") != catalog_id:
        raise ValueError("catalog IDs differ")
    items = {}
    for product in cat.findall("Товары/Товар"):
        ident = required(product, "Ид")
        if ident in items:
            raise ValueError("duplicate product ID")
        unit = product.find("БазоваяЕдиница")
        if unit is None or unit.get("Код") != "796":
            raise ValueError("only pieces (796) supported")
        items[ident] = {"name": required(product, "Наименование"), "sku": required(product, "Артикул")}
    seen, skus = set(), set()
    for offer in pack.findall("Предложения/Предложение"):
        ident = required(offer, "Ид")
        if ident not in items or ident in seen:
            raise ValueError("unknown or repeated offer ID")
        seen.add(ident)
        prices = offer.findall("Цены/Цена")
        if len(prices) != 1 or required(prices[0], "Валюта") != "RUB" or required(prices[0], "Коэффициент") != "1":
            raise ValueError("one RUB price with coefficient 1 required")
        try:
            price = Decimal(required(prices[0], "ЦенаЗаЕдиницу"))
            qty = Decimal(required(offer, "Количество"))
            if not price.is_finite() or not qty.is_finite() or not 0 <= price <= 1_000_000_000 or price * 100 != (price * 100).to_integral_value() or not 0 <= qty <= 1_000_000_000 or qty != qty.to_integral_value():
                raise ValueError("invalid price or stock")
        except InvalidOperation as exc:
            raise ValueError("invalid number") from exc
        item = items[ident]
        if item["sku"] in skus:
            raise ValueError("duplicate SKU")
        skus.add(item["sku"])
        item.update(price_kopeks=int(price * 100), stock=int(qty))
    if not items or seen != set(items):
        raise ValueError("each product needs exactly one offer")
    return catalog_id, stamp, items


def apply_exchange(db, catalog_bytes, offer_bytes):
    catalog_id, stamp, items = parse(catalog_bytes, offer_bytes)
    digest = hashlib.sha256(catalog_bytes + b"\0" + offer_bytes).hexdigest()
    with closing(sqlite3.connect(db, timeout=10)) as con, con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY, name TEXT, sku TEXT UNIQUE, price_kopeks INTEGER, stock INTEGER);
        CREATE TABLE IF NOT EXISTS exchange_batches(digest TEXT PRIMARY KEY, report TEXT);
        CREATE TABLE IF NOT EXISTS state(singleton INTEGER PRIMARY KEY CHECK(singleton=1), catalog_id TEXT, stamp REAL);
        """)
        con.execute("BEGIN IMMEDIATE")
        previous = con.execute("SELECT report FROM exchange_batches WHERE digest=?", (digest,)).fetchone()
        if previous:
            return {**json.loads(previous[0]), "replayed": True, "applied_now": 0}
        state = con.execute("SELECT catalog_id,stamp FROM state WHERE singleton=1").fetchone()
        if state and (state[0] != catalog_id or stamp <= state[1]):
            raise ValueError("different catalog, stale or conflicting snapshot")
        counts = dict(inserted=0, updated=0, unchanged=0)
        for ident, item in items.items():
            values = (item["name"], item["sku"], item["price_kopeks"], item["stock"])
            previous = con.execute("SELECT name,sku,price_kopeks,stock FROM products WHERE id=?", (ident,)).fetchone()
            counts["inserted" if previous is None else "unchanged" if previous == values else "updated"] += 1
            con.execute("INSERT INTO products VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,sku=excluded.sku,price_kopeks=excluded.price_kopeks,stock=excluded.stock", (ident, *values))
        con.execute("INSERT INTO state VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET catalog_id=excluded.catalog_id,stamp=excluded.stamp", (catalog_id, stamp))
        report = {**counts, "products": con.execute("SELECT COUNT(*) FROM products").fetchone()[0], "replayed": False, "applied_now": counts["inserted"] + counts["updated"], "digest": digest}
        con.execute("INSERT INTO exchange_batches VALUES(?,?)", (digest, json.dumps(report)))
        return report
