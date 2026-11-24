from contextlib import closing
import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from crm_clean import import_clients
from catalog_exchange import apply_exchange, parse
from team_digest import build_digest
from run_demo import clients, exchange, tasks, AS_OF


class Checks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = str(Path(self.temp.name) / "demo.sqlite")

    def test_crm_full_reconciliation_and_audit(self):
        report = import_clients(self.db, clients())
        self.assertEqual([report[k] for k in ("input", "inserted", "duplicates", "review", "rejected")], [1130, 1000, 100, 10, 20])
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("select count(*) from source_rows").fetchone()[0], 1130)

    def test_crm_replay_survives_restart(self):
        import_clients(self.db, clients())
        report = import_clients(self.db, clients())
        self.assertTrue(report["replayed"])
        self.assertEqual(report["new_writes"], 0)

    def test_crm_same_email_different_name_not_merged(self):
        import_clients(self.db, [{"name": "Alpha", "email": "a@example.invalid"}])
        report = import_clients(self.db, [{"name": "Beta", "email": "A@EXAMPLE.INVALID"}])
        self.assertEqual(report["review"], 1)
        self.assertEqual(report["total_clients"], 1)

    def test_crm_concurrent_replay(self):
        import_clients(self.db, [])
        with ThreadPoolExecutor(2) as pool:
            reports = list(pool.map(lambda _: import_clients(self.db, clients()), range(2)))
        self.assertEqual(sum(r["new_writes"] for r in reports), 1130)

    def test_crm_parameterized_sql(self):
        report = import_clients(self.db, [{"name": "Robert'); DROP TABLE clients;--", "email": "robert@example.invalid"}, None, {"name": 42, "email": "a@example.invalid"}])
        self.assertEqual(report["inserted"], 1)
        self.assertEqual(report["rejected"], 2)

    def test_catalog_update_and_replay(self):
        self.assertEqual(apply_exchange(self.db, *exchange(0))["inserted"], 60)
        self.assertEqual(apply_exchange(self.db, *exchange(1))["updated"], 12)
        self.assertEqual(apply_exchange(self.db, *exchange(1))["applied_now"], 0)
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("select price_kopeks,stock from products where id='item-000'").fetchone(), (10000, 17))

    def test_catalog_invalid_batch_cannot_partially_update(self):
        apply_exchange(self.db, *exchange(0))
        cat, offers = exchange(1)
        with self.assertRaises(ValueError):
            apply_exchange(self.db, cat, offers.replace(b"975.00", b"-1.00"))
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("select price_kopeks from products where id='item-000'").fetchone()[0], 9000)

    def test_catalog_rejects_unknown_product(self):
        cat, offers = exchange()
        with self.assertRaises(ValueError):
            parse(cat, offers.replace(b"item-059", b"item-999"))

    def test_catalog_rejects_nonfinite_fractional_or_negative(self):
        cat, offers = exchange()
        for bad in (b"NaN", b"Infinity", b"1.001", b"-1"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse(cat, offers.replace(b"90.00", bad))

    def test_catalog_rejects_xml_entities(self):
        cat, offers = exchange()
        with self.assertRaises(ValueError):
            parse(b'<!DOCTYPE foo [<!ENTITY x "no">]>' + cat, offers)

    def test_catalog_rejects_missing_offer_and_wrong_catalog(self):
        cat, _ = exchange(count=60)
        _, offers = exchange(count=59)
        with self.assertRaises(ValueError):
            parse(cat, offers)
        cat, offers = exchange()
        with self.assertRaises(ValueError):
            parse(cat, offers.replace(b"ser-demo-catalog", b"other"))

    def test_catalog_older_snapshot_cannot_overwrite(self):
        apply_exchange(self.db, *exchange(1))
        with self.assertRaises(ValueError):
            apply_exchange(self.db, *exchange(0))

    def test_catalog_unique_sku_conflict_rolls_back(self):
        apply_exchange(self.db, *exchange(0))
        cat, offers = exchange(1)
        cat = cat.replace(b"OFF-000", b"OFF-001").replace(b"OFF-002", b"OFF-000").replace(b"OFF-001</", b"OFF-002</", 1)
        with self.assertRaises((ValueError, sqlite3.IntegrityError)):
            apply_exchange(self.db, cat, offers)
        with closing(sqlite3.connect(self.db)) as con, con:
            self.assertEqual(con.execute("select price_kopeks from products where id='item-000'").fetchone()[0], 9000)

    def test_team_counts_workload_and_cycle(self):
        report = build_digest(self.db, tasks(), AS_OF)
        self.assertEqual([report[k] for k in ("total", "completed", "open", "overdue", "due_today", "blocked", "new_reminders")], [48, 16, 32, 12, 8, 4, 24])
        self.assertEqual(report["mean_completion_hours"], 31.5)
        self.assertEqual(sum(report["workload_minutes"].values()), sum(t["remaining_minutes"] for t in tasks()))

    def test_team_no_duplicate_reminders(self):
        build_digest(self.db, tasks(), AS_OF)
        report = build_digest(self.db, tasks(), AS_OF)
        self.assertEqual(report["new_reminders"], 0)
        self.assertEqual(report["sent_messages"], 0)

    def test_team_timezone_boundary(self):
        row = tasks()[40]
        row["due"] = "2026-11-25T14:30:00+00:00"
        report = build_digest(self.db, [row], AS_OF)
        self.assertEqual(report["due_today"], 1)
        row["due"] = "2026-11-25T15:30:00+00:00"
        self.assertEqual(build_digest(self.db, [row], AS_OF)["due_today"], 0)

    def test_team_invalid_snapshot_is_atomic(self):
        rows = tasks()
        rows[-1]["due"] = "2026-11-25T12:00:00"
        with self.assertRaises(ValueError):
            build_digest(self.db, rows, AS_OF)
        self.assertFalse(Path(self.db).exists())

    def test_team_done_not_overdue(self):
        row = tasks()[0]
        row["due"] = row["completed"]
        report = build_digest(self.db, [row], AS_OF)
        self.assertEqual(report["overdue"], 0)
        self.assertEqual(report["new_reminders"], 0)

    def test_team_duplicate_ids_and_bad_completion(self):
        for rows in ([tasks()[0], tasks()[0]], [{**tasks()[0], "completed": None}], [{**tasks()[20], "remaining_minutes": True}]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                build_digest(self.db, rows, AS_OF)


if __name__ == "__main__":
    unittest.main()
