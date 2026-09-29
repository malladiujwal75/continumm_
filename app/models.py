"""Pydantic request/response schemas for the API layer."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class CustomerOut(BaseModel):
    id: str
    name: str
    plan: str
    environment: str
    created_at: str


class TicketOut(BaseModel):
    id: str
    customer_id: str
    subject: str
    status: str
    created_at: str


class MessageOut(BaseModel):
    id: int
    ticket_id: str
    role: str
    content: str
    memory_mode: str
    meta: dict[str, Any]
    created_at: str


class SendMessageIn(BaseModel):
    message: str
    memory_mode: str = "on"  # "on" | "off"


class CompareIn(BaseModel):
    customer_id: str
    message: str
    ticket_id: Optional[str] = None


class CompareOut(BaseModel):
    with_memory: MessageOut | dict
    without_memory: dict


class SeedResultOut(BaseModel):
    customers_seeded: int
    live_tickets: list[dict]


class MemoryInsightOut(BaseModel):
    customer_profile: Optional[str] = None
    known_issues_digest: Optional[str] = None
