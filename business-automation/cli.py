"""Process a local JSON/XML export. Uses no network and sends no messages."""
import argparse
import json
from pathlib import Path
from crm_clean import import_clients
from catalog_exchange import apply_exchange
from team_digest import build_digest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("kind", choices=["crm", "catalog", "team"])
    parser.add_argument("input", type=Path)
    parser.add_argument("--offers", type=Path)
    parser.add_argument("--as-of")
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    all_paths = [p.resolve() for p in (args.input, args.offers, args.db, args.report) if p]
    if len(set(all_paths)) != len(all_paths):
        parser.error("inputs, database and report must have different paths")
    if args.report.exists():
        parser.error("choose a new report path to preserve previous evidence")
    if args.kind == "catalog":
        if not args.offers:
            parser.error("catalog requires --offers")
        report = apply_exchange(args.db, args.input.read_bytes(), args.offers.read_bytes())
    else:
        data = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if args.kind == "team" and not args.as_of:
            parser.error("team requires --as-of with explicit timezone")
        report = import_clients(args.db, data) if args.kind == "crm" else build_digest(args.db, data, args.as_of)
    with args.report.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f"Saved {args.report}")


if __name__ == "__main__":
    main()
