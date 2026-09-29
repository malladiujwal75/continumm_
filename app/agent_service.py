"""
Orchestration layer. Two Strategy implementations share one interface so
the "with memory" vs "without memory" comparison is structural, not a
prompt trick:

  - WithMemoryStrategy: recall known issues -> reflect (memory-grounded,
    directive-governed, structured output) -> write the outcome back into
    memory (the closed learning loop).
  - NoMemoryStrategy: one stateless LLM call, nothing retained, nothing
    recalled.

Both are driven by AgentService, which also owns the ticket transcript
(via TicketRepository) so routes stay thin.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Protocol

from .llm_baseline import BaselineLLM
from .memory_service import MemoryService, ReflectOutcome
from .repository import Message, TicketRepository

logger = logging.getLogger("continuum.agent")


@dataclass
class AgentReply:
    text: str
    memory_mode: str  # "on" | "off"
    meta: dict


class AgentStrategy(ABC):
    """Common interface for the two comparison strategies."""

    mode: str

    @abstractmethod
    def respond(self, customer_id: str, ticket_id: str, message: str) -> AgentReply: ...


class NoMemoryStrategy(AgentStrategy):
    mode = "off"

    def __init__(self, baseline: BaselineLLM):
        self.baseline = baseline

    def respond(self, customer_id: str, ticket_id: str, message: str) -> AgentReply:
        text = self.baseline.reply(message)
        return AgentReply(text=text, memory_mode=self.mode, meta={"note": "stateless — no memory used"})


class WithMemoryStrategy(AgentStrategy):
    mode = "on"

    def __init__(self, memory: MemoryService,
                 on_outcome: Optional["OutcomeHook"] = None):
        self.memory = memory
        self.on_outcome = on_outcome

    def respond(self, customer_id: str, ticket_id: str, message: str) -> AgentReply:
        # 1. Log the raw customer message into their memory bank.
        self.memory.retain_customer_message(customer_id, ticket_id, message)

        # 2. Pre-flight: is this already a known systemic issue?
        known = self.memory.recall_known_issues(message)

        # 3. Generate the reply, grounded in this customer's memory + the
        #    known-issue snippets, governed by directives, with structured
        #    learning signals attached.
        outcome: ReflectOutcome = self.memory.reflect_reply(customer_id, message, known)

        # 4. Write the outcome back — this is the "learning" part. Every
        #    resolved ticket makes the next recall/reflect smarter.
        self.memory.retain_resolution(customer_id, ticket_id, outcome)
        if outcome.is_known_issue:
            self.memory.retain_known_issue(outcome, ticket_id)

        if self.on_outcome:
            self.on_outcome(customer_id, ticket_id, outcome)

        meta = {
            "sentiment": outcome.sentiment,
            "resolved": outcome.resolved,
            "is_known_issue": outcome.is_known_issue,
            "root_cause_tag": outcome.root_cause_tag,
            "module": outcome.module,
            "memories_used": outcome.based_on_memory_count,
            "directives_applied": outcome.based_on_directive_count,
            "known_issues_matched": [m.text for m in known],
        }
        return AgentReply(text=outcome.reply, memory_mode=self.mode, meta=meta)


class OutcomeHook(Protocol):
    def __call__(self, customer_id: str, ticket_id: str, outcome: ReflectOutcome) -> None: ...


class AgentService:
    """Ties strategies to the ticket transcript. Routes call this, nothing else."""

    def __init__(self, tickets: TicketRepository, memory: MemoryService, baseline: BaselineLLM):
        self.tickets = tickets
        self.memory = memory
        self.with_memory = WithMemoryStrategy(memory)
        self.without_memory = NoMemoryStrategy(baseline)

    def handle_message(self, customer_id: str, ticket_id: str, message: str,
                        memory_mode: str = "on") -> Message:
        self.tickets.add_message(ticket_id, role="customer", content=message, memory_mode=memory_mode)

        strategy: AgentStrategy = self.with_memory if memory_mode == "on" else self.without_memory
        reply = strategy.respond(customer_id, ticket_id, message)

        if reply.meta.get("resolved"):
            self.tickets.set_status(ticket_id, "resolved")

        return self.tickets.add_message(
            ticket_id, role="agent", content=reply.text, memory_mode=reply.memory_mode, meta=reply.meta
        )
