"""Generate only synthetic inputs, run the three demos, save reproducible evidence."""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from crm_clean import import_clients
from catalog_exchange import apply_exchange, NS
from team_digest import build_digest

AS_OF = "2026-11-25T12:00:00+09:00"


def clients():
    rows = [{"name": f"Учебный клиент {i:04}", "email": f"client{i:04}@example.invalid"} for i in range(1000)]
    rows += [{"name": "  " + row["name"] + "  ", "email": row["email"].upper()} for row in rows[:100]]
    rows += [{"name": f"Другой клиент {i}", "email": f"client{i:04}@example.invalid"} for i in range(10)]
    rows += [{"name": "Ошибочная запись", "email": f"broken-{i}"} for i in range(20)]
    return rows


def exchange(version=0, count=60):
    def node(parent, tag, text=None, **attrs):
        result = ET.SubElement(parent, tag, attrs)
        if text is not None:
            result.text = str(text)
        return result
    attrs = {"ВерсияСхемы": "2.10", "ДатаФормирования": f"2026-11-{24 + version}T08:00:00+09:00", "xmlns": NS}
    root = ET.Element("КоммерческаяИнформация", attrs)
    cat = node(root, "Каталог")
    node(cat, "Ид", "ser-demo-catalog")
    node(cat, "Наименование", "Учебный каталог канцелярии")
    owner = node(cat, "Владелец")
    node(owner, "Ид", "demo-owner")
    node(owner, "Наименование", "Вымышленный магазин Ser Office")
    products = node(cat, "Товары")
    offers_root = ET.Element("КоммерческаяИнформация", attrs)
    pack = node(offers_root, "ПакетПредложений")
    node(pack, "Ид", "ser-demo-offers")
    node(pack, "Наименование", "Розничные предложения")
    node(pack, "ИдКаталога", "ser-demo-catalog")
    price_types = node(pack, "ТипыЦен")
    price_type = node(price_types, "ТипЦены")
    node(price_type, "Ид", "retail")
    node(price_type, "Наименование", "Розничная")
    node(price_type, "Валюта", "RUB")
    offers = node(pack, "Предложения")
    names = ["Блокнот", "Папка", "Маркер", "Ручка", "Альбом", "Пенал"]
    for i in range(count):
        ident = f"item-{i:03}"
        product = node(products, "Товар")
        node(product, "Ид", ident)
        node(product, "Артикул", f"OFF-{i:03}")
        node(product, "Наименование", f"{names[i % 6]} · серия {i // 6 + 1}")
        node(product, "БазоваяЕдиница", "шт", Код="796", НаименованиеПолное="Штука", МеждународноеСокращение="PCE")
        offer = node(offers, "Предложение")
        node(offer, "Ид", ident)
        price = node(node(offer, "Цены"), "Цена")
        node(price, "ИдТипаЦены", "retail")
        node(price, "ЦенаЗаЕдиницу", f"{90 + i * 15 + (10 if version and i < 12 else 0)}.00")
        node(price, "Валюта", "RUB")
        node(price, "Коэффициент", "1")
        node(offer, "Количество", 20 + i % 17 - (3 if version and i < 8 else 0))
    return tuple(ET.tostring(r, encoding="utf-8", xml_declaration=True) for r in (root, offers_root))


def tasks():
    now = datetime.fromisoformat(AS_OF)
    rows = []
    for i in range(48):
        done = i < 16
        due = now + timedelta(days=3)
        if 16 <= i < 28:
            due = now - timedelta(hours=(i - 15) * 2)
        elif 28 <= i < 36:
            due = now + timedelta(hours=4)
        rows.append({"id": f"TASK-{i + 1:03}", "title": ["Проверить макет", "Согласовать выгрузку", "Обновить описание", "Протестировать форму"][i % 4] + f" / пакет {i // 4 + 1}", "owner": f"Специалист {i % 4 + 1}", "status": "done" if done else "blocked" if 36 <= i < 40 else "doing" if i % 2 else "todo", "created": (now - timedelta(days=7)).isoformat(), "due": due.isoformat(), "completed": (now - timedelta(days=6) + timedelta(hours=i)).isoformat() if done else None, "remaining_minutes": 0 if done else 30 + i % 6 * 30})
    return rows


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    inputs = output / "inputs"
    inputs.mkdir(exist_ok=True)
    write_json(inputs / "clients.json", clients())
    write_json(inputs / "tasks.json", tasks())
    for version, suffix in [(0, "initial"), (1, "updated")]:
        for kind, data in zip(("catalog", "offers"), exchange(version)):
            (inputs / f"{kind}-{suffix}.xml").write_bytes(data)
    with tempfile.TemporaryDirectory(prefix="ser-demo-") as temp:
        crm_db, catalog_db, team_db = [str(Path(temp) / f"{name}.sqlite") for name in ("crm", "catalog", "team")]
        crm = import_clients(crm_db, clients())
        crm_repeat = import_clients(crm_db, clients())
        initial = apply_exchange(catalog_db, *exchange(0))
        updated = apply_exchange(catalog_db, *exchange(1))
        repeat = apply_exchange(catalog_db, *exchange(1))
        digest = build_digest(team_db, tasks(), AS_OF)
        repeat_digest = build_digest(team_db, tasks(), AS_OF)
    report = {"disclosure": "Synthetic demonstration, not a client engagement or revenue uplift measurement.", "crm": {"first": crm, "repeat": crm_repeat}, "catalog": {"initial": initial, "update": updated, "repeat": repeat}, "team": {"first": digest, "repeat": repeat_digest}}
    write_json(output / "report.json", report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("result"))
    args = parser.parse_args()
    summary = run(args.output)
    print(json.dumps({"crm": summary["crm"]["first"], "catalog": summary["catalog"]["update"], "team": {k: v for k, v in summary["team"]["first"].items() if k != "attention"}}, ensure_ascii=False, indent=2))
