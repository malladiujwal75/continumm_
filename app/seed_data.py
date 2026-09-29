"""
Loads data/seed_tickets.json and populates both the SQLite transcript store
and Hindsight memory, so a demo starts with weeks of believable history
instead of an empty bank. Historical tickets are written straight into
memory (they're already resolved — no need to burn a live reflect() call
per line of history); only the "live_ticket" per customer is left for the
actual demo conversation to run through the real agent loop.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .memory_service import MemoryService
from .repository import CustomerRepository, TicketRepository

DEFAULT_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_tickets.json"


def _iso(days_ago: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def seed_all(customers_repo: CustomerRepository, tickets_repo: TicketRepository,
             memory: MemoryService, seed_path: Path = DEFAULT_SEED_PATH) -> dict[str, Any]:
    payload = json.loads(Path(seed_path).read_text())

    memory.ensure_shared_bank()

    live_tickets: list[dict[str, Any]] = []

    for cust in payload["customers"]:
        customers_repo.create(
            name=cust["name"], plan=cust["plan"], environment=cust["environment"],
            customer_id=cust["id"],
        )
        memory.ensure_customer_bank(cust["id"], cust["name"])

        for h in cust.get("history", []):
            ts = _iso(h["days_ago"])
            tickets_repo.create(
                customer_id=cust["id"], subject=h["subject"], status="resolved",
                ticket_id=h["ticket_id"], created_at=ts,
            )
            tickets_repo.add_message(
                h["ticket_id"], role="customer", content=h["customer_message"],
                memory_mode="on", created_at=ts,
            )
            tickets_repo.add_message(
                h["ticket_id"], role="agent", content=h["agent_reply"], memory_mode="on",
                meta={
                    "sentiment": h["sentiment"], "resolved": h["resolved"],
                    "is_known_issue": h["is_known_issue"], "root_cause_tag": h["root_cause_tag"],
                    "module": h["module"], "seeded": True,
                },
                created_at=ts,
            )
            memory.seed_resolved_ticket(
                customer_id=cust["id"], ticket_id=h["ticket_id"], timestamp=ts,
                customer_message=h["customer_message"], resolution_summary=h["resolution_summary"],
                sentiment=h["sentiment"], resolved=h["resolved"],
                root_cause_tag=h["root_cause_tag"], is_known_issue=h["is_known_issue"],
                module=h["module"],
            )

        live = cust.get("live_ticket")
        if live:
            ticket = tickets_repo.create(customer_id=cust["id"], subject=live["subject"], status="open")
            live_tickets.append({
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "ticket_id": ticket.id,
                "suggested_message": live["customer_message"],
            })

        # Bring the mental models up to date with the history we just wrote.
        if cust.get("history"):
            memory.refresh_customer_profile(cust["id"])

    memory.refresh_known_issues_digest()

    return {
        "customers_seeded": len(payload["customers"]),
        "live_tickets": live_tickets,
    }
