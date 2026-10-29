"""SQLite ledger store (standard library only)."""
import json
import sqlite3
import threading
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS subscribers (id TEXT PRIMARY KEY, dob TEXT);
CREATE TABLE IF NOT EXISTS subscriptions (
    subscriber_id TEXT NOT NULL, tax_year INTEGER NOT NULL,
    amount_pence INTEGER NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('cash', 'stocks')));
CREATE TABLE IF NOT EXISTS events (kind TEXT NOT NULL, detail TEXT NOT NULL);
"""


class Store:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self._db.executescript(SCHEMA)

    def _run(self, sql: str, args: tuple = ()) -> list:
        with self._lock, self._db:
            return self._db.execute(sql, args).fetchall()

    def add_subscriber(self, id: str, dob: date | None) -> None:
        self._run("INSERT OR REPLACE INTO subscribers VALUES (?, ?)", (id, dob.isoformat() if dob else None))

    def subscriber_dob(self, id: str) -> date | None:
        rows = self._run("SELECT dob FROM subscribers WHERE id = ?", (id,))
        return date.fromisoformat(rows[0][0]) if rows and rows[0][0] else None

    def record(self, id: str, tax_year: int, amount_pence: int, kind: str) -> None:
        # REQ-ALW-001: every subscription is stored against its tax year
        self._run("INSERT INTO subscriptions VALUES (?, ?, ?, ?)", (id, tax_year, amount_pence, kind))

    def totals(self, id: str, tax_year: int) -> tuple[int, int]:
        """(total, cash) accepted pence for a subscriber in a tax year."""
        rows = self._run(
            "SELECT COALESCE(SUM(amount_pence), 0),"
            " COALESCE(SUM(CASE WHEN kind = 'cash' THEN amount_pence END), 0)"
            " FROM subscriptions WHERE subscriber_id = ? AND tax_year = ?",
            (id, tax_year),
        )
        return rows[0][0], rows[0][1]

    def record_event(self, kind: str, detail: dict) -> None:
        self._run("INSERT INTO events VALUES (?, ?)", (kind, json.dumps(detail, sort_keys=True)))

    def events(self) -> list:
        return [{"kind": k, "detail": json.loads(d)} for k, d in self._run("SELECT kind, detail FROM events")]
