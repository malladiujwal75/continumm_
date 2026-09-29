"""
Repository pattern: isolates SQL from the rest of the app. Each repository
takes a `Database` and exposes plain, typed methods — no ORM, no query
strings leaking into services or routes.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from .db import Database


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


@dataclass
class Customer:
    id: str
    name: str
    plan: str
    environment: str
    created_at: str


@dataclass
class Ticket:
    id: str
    customer_id: str
    subject: str
    status: str
    created_at: str


@dataclass
class Message:
    id: int
    ticket_id: str
    role: str
    content: str
    memory_mode: str
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


class CustomerRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, name: str, plan: str = "Free", environment: str = "",
               customer_id: Optional[str] = None, created_at: Optional[str] = None) -> Customer:
        cid = customer_id or new_id("cust")
        with self.db.cursor() as cur:
            if created_at:
                cur.execute(
                    "INSERT INTO customers (id, name, plan, environment, created_at) VALUES (?, ?, ?, ?, ?)",
                    (cid, name, plan, environment, created_at),
                )
            else:
                cur.execute(
                    "INSERT INTO customers (id, name, plan, environment) VALUES (?, ?, ?, ?)",
                    (cid, name, plan, environment),
                )
        return self.get(cid)  # type: ignore[return-value]

    def get(self, customer_id: str) -> Optional[Customer]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
            row = cur.fetchone()
        return Customer(**dict(row)) if row else None

    def list(self) -> list[Customer]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM customers ORDER BY created_at ASC")
            rows = cur.fetchall()
        return [Customer(**dict(r)) for r in rows]


class TicketRepository:
    def __init__(self, db: Database):
        self.db = db

    def create(self, customer_id: str, subject: str, status: str = "open",
               ticket_id: Optional[str] = None, created_at: Optional[str] = None) -> Ticket:
        tid = ticket_id or new_id("tick")
        with self.db.cursor() as cur:
            if created_at:
                cur.execute(
                    "INSERT INTO tickets (id, customer_id, subject, status, created_at) VALUES (?, ?, ?, ?, ?)",
                    (tid, customer_id, subject, status, created_at),
                )
            else:
                cur.execute(
                    "INSERT INTO tickets (id, customer_id, subject, status) VALUES (?, ?, ?, ?)",
                    (tid, customer_id, subject, status),
                )
        return self.get(tid)  # type: ignore[return-value]

    def get(self, ticket_id: str) -> Optional[Ticket]:
        with self.db.cursor() as cur:
            cur.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
            row = cur.fetchone()
        return Ticket(**dict(row)) if row else None

    def list_for_customer(self, customer_id: str) -> list[Ticket]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM tickets WHERE customer_id = ? ORDER BY created_at ASC",
                (customer_id,),
            )
            rows = cur.fetchall()
        return [Ticket(**dict(r)) for r in rows]

    def set_status(self, ticket_id: str, status: str) -> None:
        with self.db.cursor() as cur:
            cur.execute("UPDATE tickets SET status = ? WHERE id = ?", (status, ticket_id))

    def add_message(self, ticket_id: str, role: str, content: str,
                     memory_mode: str = "on", meta: Optional[dict[str, Any]] = None,
                     created_at: Optional[str] = None) -> Message:
        meta = meta or {}
        with self.db.cursor() as cur:
            if created_at:
                cur.execute(
                    "INSERT INTO messages (ticket_id, role, content, memory_mode, meta_json, created_at) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (ticket_id, role, content, memory_mode, json.dumps(meta), created_at),
                )
            else:
                cur.execute(
                    "INSERT INTO messages (ticket_id, role, content, memory_mode, meta_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (ticket_id, role, content, memory_mode, json.dumps(meta)),
                )
            new_row_id = cur.lastrowid
            cur.execute("SELECT * FROM messages WHERE id = ?", (new_row_id,))
            row = cur.fetchone()
        d = dict(row)
        d["meta"] = json.loads(d.pop("meta_json") or "{}")
        return Message(**d)

    def list_messages(self, ticket_id: str) -> list[Message]:
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT * FROM messages WHERE ticket_id = ? ORDER BY created_at ASC, id ASC",
                (ticket_id,),
            )
            rows = cur.fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["meta"] = json.loads(d.pop("meta_json") or "{}")
            out.append(Message(**d))
        return out
