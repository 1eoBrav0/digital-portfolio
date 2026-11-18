"""Обновляет Excel-отчёт за январь–июнь 2026 по исходному CSV. Python 3.8+."""

import argparse
import csv
import os
import posixpath
import re
import sys
import tempfile
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.dom import Node, minidom
from zipfile import BadZipFile, ZipFile


HERE = Path(__file__).resolve().parent
COLUMNS = ("Номер заказа", "Дата", "Канал", "Категория", "Количество",
           "Цена за ед., ₽", "Скидка, %", "Статус")
CHANNELS = {"Сайт", "Соцсети", "Маркетплейс"}
CATEGORIES = {"Посуда", "Текстиль", "Хранение", "Освещение"}
STATUSES = {"Оплачен", "Отменён"}
EPOCH = date(1899, 12, 30)
CENT = Decimal("0.01")


def number(raw):
    value = Decimal(raw.strip().replace(",", "."))
    if not value.is_finite():
        raise ValueError("нужно конечное число")
    return value


def load_orders(path):
    records, seen = [], set()
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if len(reader.fieldnames or ()) != len(COLUMNS) or set(reader.fieldnames) != set(COLUMNS):
            raise ValueError("заголовок CSV должен содержать поля из orders.csv")
        for row in reader:
            try:
                if None in row or any(row[col] is None for col in COLUMNS):
                    raise ValueError("неверное количество столбцов")
                order_id, day, channel, category, qty, price, discount, status = (
                    row[k].strip() for k in COLUMNS)
                if not order_id or order_id in seen:
                    raise ValueError("пустой или повторяющийся номер заказа")
                if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", order_id) or len(order_id) > 32767:
                    raise ValueError("номер заказа нельзя записать в ячейку Excel")
                day = datetime.strptime(day, "%d.%m.%Y").date()
                if day.year != 2026 or day.month > 6:
                    raise ValueError("дата должна быть в январе–июне 2026 года")
                if channel not in CHANNELS or category not in CATEGORIES or status not in STATUSES:
                    raise ValueError("неизвестный канал, категория или статус")
                qty, price, discount = int(qty), number(price), number(discount)
                if qty < 1 or price < 0 or not 0 <= discount <= 100:
                    raise ValueError("проверьте количество, цену и скидку от 0 до 100 %")
                discount /= 100
                net = (qty * price * (1 - discount)).quantize(CENT, rounding=ROUND_HALF_UP)
                net = net if status == "Оплачен" else Decimal(0)
                records.append((order_id, day, channel, category, qty, price, discount, status, net))
                if len(records) > 1048572:
                    raise ValueError("достигнут предел строк листа Excel")
                seen.add(order_id)
            except (ValueError, InvalidOperation) as error:
                raise ValueError(f"строка CSV {reader.line_num}: {error}") from error
    return records


def children(node, name):
    return [n for n in node.childNodes if n.nodeType == Node.ELEMENT_NODE and n.localName == name]


def descendants(node, name):
    return list(node.getElementsByTagNameNS("*", name))


def text(node):
    return "".join(n.data for n in node.childNodes if n.nodeType in (Node.TEXT_NODE, Node.CDATA_SECTION_NODE))


def element(parent, name):
    prefix = f"{parent.prefix}:" if parent.prefix else ""
    node = parent.ownerDocument.createElementNS(parent.namespaceURI, prefix + name)
    parent.appendChild(node)
    return node


def assign(node, value):
    for child in list(node.childNodes):
        node.removeChild(child)
    node.appendChild(node.ownerDocument.createTextNode(str(value)))


def decimal_text(value):
    return format(value, "f") if isinstance(value, Decimal) else str(value)


def set_cell(cell, value, formula=None):
    for child in list(cell.childNodes):
        cell.removeChild(child)
    if cell.hasAttribute("t"):
        cell.removeAttribute("t")
    if formula is not None:
        assign(element(cell, "f"), formula)
    if value is None:
        return
    if isinstance(value, str):
        cell.setAttribute("t", "inlineStr")
        assign(element(element(cell, "is"), "t"), value)
    else:
        assign(element(cell, "v"), decimal_text(value))


def get_paths(package, source):
    directory, filename = posixpath.split(source)
    relpath = posixpath.join(directory, "_rels", filename + ".rels")
    rels = minidom.parseString(package.read(relpath))
    paths = {}
    for rel in descendants(rels, "Relationship"):
        target = rel.getAttribute("Target")
        if rel.getAttribute("TargetMode") != "External":
            paths[rel.getAttribute("Id")] = (target.lstrip("/") if target.startswith("/") else
                                             posixpath.normpath(posixpath.join(directory, target)))
    return paths


def relationship_id(node):
    return node.getAttributeNS("http://schemas.openxmlformats.org/officeDocument/2006/relationships", "id")


def report_values(records, overview_cells, shared):
    monthly = defaultdict(Decimal)
    counts = defaultdict(int)
    by_category = defaultdict(Decimal)
    for _, day, _, category, _, _, _, status, net in records:
        if status == "Оплачен":
            monthly[day.month] += net
            counts[day.month] += 1
            by_category[category] += net
    revenue, paid = sum(monthly.values(), Decimal(0)), sum(counts.values())
    results = {"B8": revenue, "D8": paid, "H8": revenue / paid if paid else 0}
    for month in range(1, 7):
        row = month + 14
        results[f"C{row}"] = monthly[month]
        results[f"D{row}"] = counts[month]
        results[f"E{row}"] = monthly[month] / counts[month] if counts[month] else 0
    for row in range(25, 29):
        category = cell_text(overview_cells[f"B{row}"], shared)
        if category not in CATEGORIES:
            raise ValueError("категории в шаблоне и CSV не совпадают")
        results[f"C{row}"] = by_category[category]
        results[f"D{row}"] = by_category[category] / revenue if revenue else 0
    return results


def cell_text(cell, shared):
    kind = cell.getAttribute("t")
    if kind == "inlineStr":
        return "".join(text(t) for t in descendants(cell, "t"))
    raw = children(cell, "v")
    value = text(raw[0]) if raw else ""
    return shared[int(value)] if kind == "s" else value


def replace_records(source, table, records):
    table_node = table.documentElement
    table_range = re.fullmatch(r"A4:I(\d+)", table_node.getAttribute("ref"))
    if not table_range:
        raise ValueError("ожидается таблица заказов, начинающаяся в A4")
    old_end = int(table_range.group(1))
    new_end = 4 + max(len(records), 1)
    data = descendants(source, "sheetData")[0]
    rows = {int(r.getAttribute("r")): r for r in children(data, "row")}
    prototype = rows[5].cloneNode(True)
    alternate = rows[6].cloneNode(True) if old_end >= 6 else prototype
    for row_number, row in rows.items():
        if 5 <= row_number <= old_end:
            data.removeChild(row)
    following = min((n for n in rows if n > old_end), default=None)
    reference = rows.get(following)
    for offset, record in enumerate(records or [(None,) * 9], start=5):
        row = (alternate if offset % 2 == 0 else prototype).cloneNode(True)
        row.setAttribute("r", str(offset))
        cells = {re.sub(r"\d+", "", c.getAttribute("r")): c for c in children(row, "c")}
        for letter, raw in zip("ABCDEFGHI", record):
            c = cells[letter]
            c.setAttribute("r", letter + str(offset))
            if letter == "I":
                formula = f'IF(H{offset}="Оплачен",ROUND(E{offset}*F{offset}*(1-G{offset}),2),0)'
                set_cell(c, raw or 0, formula)
            else:
                set_cell(c, (raw - EPOCH).days if isinstance(raw, date) else raw)
        if reference:
            data.insertBefore(row, reference)
        else:
            data.appendChild(row)
    for node in [table_node] + descendants(table, "autoFilter") + descendants(source, "autoFilter"):
        if node.getAttribute("ref") == f"A4:I{old_end}":
            node.setAttribute("ref", f"A4:I{new_end}")
    for node in descendants(source, "dimension"):
        ref = re.sub(rf"(:I){old_end}$", lambda m: f"{m[1]}{new_end}", node.getAttribute("ref"))
        node.setAttribute("ref", ref)
    return old_end, new_end


def update_overview(overview, records, shared, old_end, new_end):
    cells = {c.getAttribute("r"): c for c in descendants(overview, "c")}
    values = report_values(records, cells, shared)
    for address in ("C5", "H5"):
        set_cell(cells[address], "Все")
    range_end = re.compile(rf"(:\$[A-I]\$){old_end}(?!\d)")
    for address, value in values.items():
        c = cells[address]
        formula = text(children(c, "f")[0])
        formula = range_end.sub(lambda m: m[1] + str(new_end), formula)
        set_cell(c, value, formula)
    return values, cells


def update_chart(doc, cells, shared):
    for ref in descendants(doc, "numRef") + descendants(doc, "strRef"):
        f = children(ref, "f")
        if not f:
            continue
        match = re.fullmatch(r"'?Обзор'?!\$?([A-Z]+)\$?(\d+)(?::\$?([A-Z]+)\$?(\d+))?", text(f[0]))
        if not match:
            continue
        col, start, end_col, end = match.groups()
        if end_col and end_col != col:
            continue
        cached = children(ref, "numCache") + children(ref, "strCache")
        if not cached:
            continue
        cache = cached[0]
        for pt in children(cache, "pt"):
            cache.removeChild(pt)
        vals = [cell_text(cells[f"{col}{row}"], shared)
                for row in range(int(start), int(end or start) + 1)]
        counter = children(cache, "ptCount") or [element(cache, "ptCount")]
        counter[0].setAttribute("val", str(len(vals)))
        for idx, val in enumerate(vals):
            pt = element(cache, "pt")
            pt.setAttribute("idx", str(idx))
            assign(element(pt, "v"), val)


def generate(template, output, records):
    with ZipFile(template) as original:
        documents = {}
        def read_xml(name):
            documents[name] = minidom.parseString(original.read(name))
            return documents[name]
        workbook = read_xml("xl/workbook.xml")
        links = get_paths(original, "xl/workbook.xml")
        sheets = {s.getAttribute("name"): links[relationship_id(s)] for s in descendants(workbook, "sheet")}
        overview, source = read_xml(sheets["Обзор"]), read_xml(sheets["Заказы"])
        parts = get_paths(original, sheets["Заказы"])
        table = read_xml(parts[relationship_id(descendants(source, "tablePart")[0])])
        shared = []
        if "xl/sharedStrings.xml" in original.namelist():
            strings = minidom.parseString(original.read("xl/sharedStrings.xml"))
            shared = ["".join(text(t) for t in descendants(si, "t")) for si in descendants(strings, "si")]
        bounds = replace_records(source, table, records)
        values, cells = update_overview(overview, records, shared, *bounds)
        for name in original.namelist():
            if re.fullmatch(r"xl/(?:drawings/)?charts/chart\d+\.xml", name):
                update_chart(read_xml(name), cells, shared)
        calc = descendants(workbook, "calcPr") or [element(workbook.documentElement, "calcPr")]
        for prop, flag in (("calcMode", "auto"), ("fullCalcOnLoad", "1"), ("forceFullCalc", "1")):
            calc[0].setAttribute(prop, flag)
        omit = set()
        if "xl/calcChain.xml" in original.namelist():
            omit.add("xl/calcChain.xml")
            workbook_rels = read_xml("xl/_rels/workbook.xml.rels")
            for rel in descendants(workbook_rels, "Relationship"):
                if rel.getAttribute("Type").endswith("/calcChain"):
                    rel.parentNode.removeChild(rel)
            content_types = read_xml("[Content_Types].xml")
            for override in descendants(content_types, "Override"):
                if override.getAttribute("PartName") == "/xl/calcChain.xml":
                    override.parentNode.removeChild(override)
        with ZipFile(output, "w") as result:
            for item in original.infolist():
                if item.filename in omit:
                    continue
                doc = documents.get(item.filename)
                result.writestr(item, doc.toxml(encoding="utf-8") if doc else original.read(item))
    with ZipFile(output) as result:
        if result.testzip() is not None:
            raise ValueError("не удалось проверить целостность XLSX")
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", nargs="?", type=Path, default=HERE / "orders.csv", help="CSV с заказами")
    parser.add_argument("--template", type=Path, default=HERE / "sales-report.xlsx", help="исходная книга")
    parser.add_argument("--output", type=Path, required=True, help="путь к результирующей книге .xlsx")
    args = parser.parse_args()
    dest = args.output.resolve()
    if dest.suffix.lower() != ".xlsx":
        parser.error("выходной файл должен иметь расширение .xlsx")
    if any(dest == p.resolve() or (dest.exists() and p.exists() and dest.samefile(p))
           for p in (args.csv, args.template)):
        parser.error("выберите другой выходной файл, чтобы сохранить оригинал")
    tmp = None
    try:
        records = load_orders(args.csv)
        with tempfile.NamedTemporaryFile(dir=dest.parent, suffix=".xlsx", delete=False) as handle:
            tmp = Path(handle.name)
        values = generate(args.template, tmp, records)
        os.replace(tmp, dest)
        print(f"Выручка: {values['B8']:.2f} ₽. Оплачено: {values['D8']}. "
              f"Средний чек: {Decimal(values['H8']).quantize(CENT, rounding=ROUND_HALF_UP):.2f} ₽.")
    except (OSError, ValueError, KeyError, IndexError, BadZipFile) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    finally:
        if tmp and tmp.exists():
            tmp.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main())
