from contextlib import closing
"""Daily operational report with a persistent local reminder queue. No messages sent."""
from datetime import datetime
import json
import sqlite3


def instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def build_digest(db, tasks, as_of):
    now = instant(as_of)
    ids, validated = set(), []
    for task in tasks:
        ident = task["id"]
        if not isinstance(ident, str) or not ident or ident in ids:
            raise ValueError("unique nonempty task IDs required")
        ids.add(ident)
        if task["status"] not in ("todo", "doing", "blocked", "done"):
            raise ValueError("invalid task status")
        if not isinstance(task["owner"], str) or not task["owner"].strip():
            raise ValueError("owner required")
        minutes = task["remaining_minutes"]
        if type(minutes) is not int or not 0 <= minutes <= 100_000:
            raise ValueError("remaining_minutes must be a nonnegative integer")
        created, due = instant(task["created"]), instant(task["due"])
        if due < created or created > now:
            raise ValueError("invalid task chronology")
        done = instant(task["completed"]) if task.get("completed") else None
        if (task["status"] == "done") != bool(done) or (done and (done < created or done > now or minutes != 0)):
            raise ValueError("invalid completion")
        validated.append((task, due, created, done))
    report = dict(total=len(tasks), completed=0, overdue=0, due_today=0, blocked=0, open=0, workload_minutes={}, attention=[], completion_hours=[])
    with closing(sqlite3.connect(db, timeout=10)) as con, con:
        con.execute("CREATE TABLE IF NOT EXISTS reminders(day TEXT, task_id TEXT, payload TEXT, PRIMARY KEY(day,task_id))")
        con.execute("BEGIN IMMEDIATE")
        added = 0
        for task, due, created, done in validated:
            if done:
                report["completed"] += 1
                report["completion_hours"].append((done - created).total_seconds() / 3600)
                continue
            report["open"] += 1
            report["workload_minutes"].setdefault(task["owner"], 0)
            report["workload_minutes"][task["owner"]] += task["remaining_minutes"]
            flags = []
            if due < now:
                flags.append("overdue")
            elif due.astimezone(now.tzinfo).date() == now.date():
                flags.append("due_today")
            if task["status"] == "blocked":
                flags.append("blocked")
            for flag in flags:
                report[flag] += 1
            if flags:
                row = {"id": task["id"], "owner": task["owner"], "title": task["title"], "due": task["due"], "flags": flags}
                report["attention"].append(row)
                added += con.execute("INSERT OR IGNORE INTO reminders VALUES(?,?,?)", (now.date().isoformat(), task["id"], json.dumps(row, ensure_ascii=False))).rowcount
        hours = report.pop("completion_hours")
        report.update(as_of=as_of, mean_completion_hours=round(sum(hours) / len(hours), 2) if hours else None, new_reminders=added, sent_messages=0)
        report["attention"].sort(key=lambda x: ("overdue" not in x["flags"], instant(x["due"]), x["id"]))
    return report
