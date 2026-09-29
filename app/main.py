"""
FastAPI routes. Thin by design: everything here is wiring — DB session,
service construction (via dependency injection), and turning
dataclasses/SDK objects into JSON. All actual logic lives in
agent_service.py / memory_service.py / repository.py.
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .agent_service import AgentService, NoMemoryStrategy, WithMemoryStrategy
from .config import settings
from .db import Database
from .llm_baseline import BaselineLLM
from .memory_service import MemoryService
from .models import (
    CompareIn,
    CustomerOut,
    MemoryInsightOut,
    MessageOut,
    SeedResultOut,
    SendMessageIn,
    TicketOut,
)
from .repository import CustomerRepository, Message, TicketRepository
from .seed_data import seed_all

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("continuum.api")

app = FastAPI(title="Continuum — Memory-Native Support Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------------------------------------------------------------------
# Dependency wiring
# ---------------------------------------------------------------------

@lru_cache
def get_db() -> Database:
    return Database(settings.db_path)


@lru_cache
def get_hindsight_client():
    """Real Hindsight client, constructed lazily so importing this module
    (e.g. for tests, which override this dependency) never requires network
    access or credentials."""
    from hindsight_client import Hindsight
    kwargs = {"base_url": settings.hindsight_base_url}
    if settings.hindsight_api_key:
        kwargs["api_key"] = settings.hindsight_api_key
    return Hindsight(**kwargs)


def get_memory_service(client=Depends(get_hindsight_client)) -> MemoryService:
    return MemoryService(client, settings)


def get_baseline_llm() -> BaselineLLM:
    return BaselineLLM(settings)


def get_customer_repo(db: Database = Depends(get_db)) -> CustomerRepository:
    return CustomerRepository(db)


def get_ticket_repo(db: Database = Depends(get_db)) -> TicketRepository:
    return TicketRepository(db)


def get_agent_service(
    tickets: TicketRepository = Depends(get_ticket_repo),
    memory: MemoryService = Depends(get_memory_service),
    baseline: BaselineLLM = Depends(get_baseline_llm),
) -> AgentService:
    return AgentService(tickets, memory, baseline)


# ---------------------------------------------------------------------
# Serializers
# ---------------------------------------------------------------------

def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id, ticket_id=m.ticket_id, role=m.role, content=m.content,
        memory_mode=m.memory_mode, meta=m.meta, created_at=m.created_at,
    )


# ---------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "product": settings.product_name}


@app.get("/api/customers", response_model=list[CustomerOut])
def list_customers(repo: CustomerRepository = Depends(get_customer_repo)):
    return [CustomerOut(**vars(c)) for c in repo.list()]


@app.get("/api/customers/{customer_id}/tickets", response_model=list[TicketOut])
def list_tickets(customer_id: str, repo: TicketRepository = Depends(get_ticket_repo)):
    return [TicketOut(**vars(t)) for t in repo.list_for_customer(customer_id)]


@app.get("/api/tickets/{ticket_id}/messages", response_model=list[MessageOut])
def list_messages(ticket_id: str, repo: TicketRepository = Depends(get_ticket_repo)):
    return [_message_out(m) for m in repo.list_messages(ticket_id)]


@app.post("/api/tickets/{ticket_id}/messages", response_model=MessageOut)
def send_message(
    ticket_id: str, body: SendMessageIn,
    tickets: TicketRepository = Depends(get_ticket_repo),
    agent: AgentService = Depends(get_agent_service),
):
    ticket = tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="ticket not found")
    reply = agent.handle_message(
        customer_id=ticket.customer_id, ticket_id=ticket_id,
        message=body.message, memory_mode=body.memory_mode,
    )
    return _message_out(reply)


@app.post("/api/compare")
def compare(
    body: CompareIn,
    memory: MemoryService = Depends(get_memory_service),
    baseline: BaselineLLM = Depends(get_baseline_llm),
):
    """Runs the SAME message through both strategies side by side. The
    with-memory branch has real effects (it retains); the without-memory
    branch is a single stateless call. Neither is written to the ticket
    transcript — this is a comparison view, not a sent reply."""
    if not body.customer_id:
        raise HTTPException(status_code=400, detail="customer_id is required")

    ticket_id = body.ticket_id or "compare"
    with_memory = WithMemoryStrategy(memory).respond(body.customer_id, ticket_id, body.message)
    without_memory = NoMemoryStrategy(baseline).respond(body.customer_id, ticket_id, body.message)
    return {
        "with_memory": {"text": with_memory.text, "meta": with_memory.meta},
        "without_memory": {"text": without_memory.text, "meta": without_memory.meta},
    }


@app.get("/api/customers/{customer_id}/memory", response_model=MemoryInsightOut)
def customer_memory(customer_id: str, memory: MemoryService = Depends(get_memory_service)):
    return MemoryInsightOut(
        customer_profile=memory.customer_profile(customer_id),
        known_issues_digest=memory.known_issues_digest(),
    )


@app.post("/api/customers/{customer_id}/memory/refresh", response_model=MemoryInsightOut)
def refresh_customer_memory(customer_id: str, memory: MemoryService = Depends(get_memory_service)):
    """Manually re-runs the Customer Profile mental model so the UI can show
    the digest catching up right after new tickets, without waiting for the
    bank's normal refresh cadence."""
    memory.refresh_customer_profile(customer_id)
    return MemoryInsightOut(
        customer_profile=memory.customer_profile(customer_id),
        known_issues_digest=memory.known_issues_digest(),
    )


@app.post("/api/known-issues/refresh", response_model=MemoryInsightOut)
def refresh_known_issues(memory: MemoryService = Depends(get_memory_service)):
    memory.refresh_known_issues_digest()
    return MemoryInsightOut(customer_profile=None, known_issues_digest=memory.known_issues_digest())


@app.post("/api/demo/seed", response_model=SeedResultOut)
def seed_demo(
    db: Database = Depends(get_db),
    customers: CustomerRepository = Depends(get_customer_repo),
    tickets: TicketRepository = Depends(get_ticket_repo),
    memory: MemoryService = Depends(get_memory_service),
):
    db.reset()
    result = seed_all(customers, tickets, memory)
    return SeedResultOut(**result)


# ---------------------------------------------------------------------
# Static frontend (single-file console UI)
# ---------------------------------------------------------------------

_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.isdir(_FRONTEND_DIR):
    @app.get("/")
    def index():
        return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")
