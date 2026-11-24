from contextlib import closing
"""Conservative client import: exact identity matches only; ambiguous rows need review."""
import hashlib
import json
import re
import sqlite3
import unicodedata


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize(row):
    if not isinstance(row, dict):
        raise ValueError("record must be an object")
    name = row.get("name", "")
    email = row.get("email", "")
    if not isinstance(name, str) or not isinstance(email, str):
        raise ValueError("name and email must be strings")
    name = " ".join(unicodedata.normalize("NFKC", name).split())
    email = email.strip().casefold()
    if not 2 <= len(name) <= 160 or not re.fullmatch(r"[^\s@]{1,64}@[^\s@.]+(?:\.[^\s@.]+)+", email) or len(email) > 254:
        raise ValueError("invalid name or email")
    return name, email


def import_clients(db, records):
    if not isinstance(records, list) or len(records) > 100_000:
        raise ValueError("expected at most 100000 records")
    digest = hashlib.sha256(canonical(records).encode()).hexdigest()
    with closing(sqlite3.connect(db, timeout=10)) as con, con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS clients(id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL);
        CREATE TABLE IF NOT EXISTS batches(digest TEXT PRIMARY KEY, report TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_rows(batch TEXT, row_no INTEGER, raw TEXT NOT NULL,
          outcome TEXT NOT NULL, client_id INTEGER, reason TEXT NOT NULL, PRIMARY KEY(batch,row_no));
        """)
        con.execute("BEGIN IMMEDIATE")
        previous = con.execute("SELECT report FROM batches WHERE digest=?", (digest,)).fetchone()
        if previous:
            return {**json.loads(previous[0]), "replayed": True, "new_writes": 0}
        stats = dict(input=len(records), inserted=0, duplicates=0, review=0, rejected=0)
        for i, row in enumerate(records, 1):
            client_id, reason = None, ""
            try:
                name, email = normalize(row)
                existing = con.execute("SELECT id,name FROM clients WHERE email=?", (email,)).fetchone()
                if existing:
                    if existing[1].casefold() == name.casefold():
                        outcome, client_id = "duplicates", existing[0]
                    else:
                        outcome, reason = "review", "same email, different name: manual decision required"
                else:
                    client_id = con.execute("INSERT INTO clients(name,email) VALUES(?,?)", (name, email)).lastrowid
                    outcome = "inserted"
            except ValueError as exc:
                outcome, reason = "rejected", str(exc)
            stats[outcome] += 1
            con.execute("INSERT INTO source_rows VALUES(?,?,?,?,?,?)", (digest, i, canonical(row), outcome, client_id, reason))
        stats.update(total_clients=con.execute("SELECT COUNT(*) FROM clients").fetchone()[0], replayed=False, new_writes=len(records), batch=digest)
        con.execute("INSERT INTO batches VALUES(?,?)", (digest, canonical(stats)))
        return stats
