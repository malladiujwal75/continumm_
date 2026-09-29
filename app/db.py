"""
SQLite system of record for the literal support-ticket transcript.

This is deliberately separate from Hindsight: Hindsight stores the agent's
*distilled memory* (facts worth remembering), while this stores the exact
thread a support console needs to render. Mixing the two would make the
memory bank noisy with UI concerns and make the transcript lossy.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    plan        TEXT NOT NULL DEFAULT 'Free',
    environment TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id          TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL REFERENCES customers(id),
    subject     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   TEXT NOT NULL REFERENCES tickets(id),
    role        TEXT NOT NULL,              -- 'customer' | 'agent' | 'system'
    content     TEXT NOT NULL,
    memory_mode TEXT NOT NULL DEFAULT 'on',  -- 'on' | 'off' — which strategy produced this reply
    meta_json   TEXT NOT NULL DEFAULT '{}',  -- structured signals (sentiment, resolved, ...) as JSON
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_messages_ticket ON messages(ticket_id);
"""


class Database:
    """Thin wrapper that owns the connection lifecycle and schema init."""

    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True) if Path(path).parent != Path("") else None
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        finally:
            conn.close()

    def reset(self) -> None:
        """Drops and recreates all tables. Used by the demo-data seeder."""
        with self._connect() as conn:
            conn.executescript(
                "DROP TABLE IF EXISTS messages;"
                "DROP TABLE IF EXISTS tickets;"
                "DROP TABLE IF EXISTS customers;"
            )
            conn.executescript(SCHEMA)
