"""
Adapter/Facade over the `hindsight-client` SDK.

Nothing outside this file calls the Hindsight SDK directly. That keeps the
rest of the app decoupled from SDK specifics, makes the integration
testable with a fake client (see tests/fake_hindsight.py), and gives one
place to reason about bank layout, tags, and directive/mental-model setup.

Bank layout:
  - `product::known-issues`   (shared)  — cross-customer distilled issues
  - `customer::{customer_id}` (per-customer) — that customer's history
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from .config import Settings
from .schemas_hindsight import (
    AGENT_REFLECT_SCHEMA,
    CUSTOMER_BANK_MISSION,
    CUSTOMER_PROFILE_MENTAL_MODEL,
    KNOWN_ISSUES_MENTAL_MODEL,
    SHARED_BANK_MISSION,
    SUPPORT_DIRECTIVES,
)

logger = logging.getLogger("continuum.memory")


class HindsightLike(Protocol):
    """The subset of the Hindsight SDK surface this app depends on.

    A Protocol rather than importing the SDK's concrete class means tests
    can hand in any object with these methods — no SDK required to run the
    unit-test suite.
    """

    def create_bank(self, bank_id: str, **kwargs: Any) -> Any: ...
    def create_directive(self, bank_id: str, name: str, content: str,
                          priority: int = 0, is_active: bool = True,
                          tags: Optional[list[str]] = None) -> Any: ...
    def list_directives(self, bank_id: str, **kwargs: Any) -> Any: ...
    def create_mental_model(self, bank_id: str, name: str, source_query: str,
                             **kwargs: Any) -> Any: ...
    def list_mental_models(self, bank_id: str, **kwargs: Any) -> Any: ...
    def refresh_mental_model(self, bank_id: str, mental_model_id: str) -> Any: ...
    def get_mental_model(self, bank_id: str, mental_model_id: str, **kwargs: Any) -> Any: ...
    def retain(self, bank_id: str, content: Any, **kwargs: Any) -> Any: ...
    def retain_batch(self, bank_id: str, items: list[dict], **kwargs: Any) -> Any: ...
    def recall(self, bank_id: str, query: str, **kwargs: Any) -> Any: ...
    def reflect(self, bank_id: str, query: str, **kwargs: Any) -> Any: ...


@dataclass
class RecalledMemory:
    text: str
    tags: list[str]
    score: Optional[float] = None


@dataclass
class ReflectOutcome:
    reply: str
    sentiment: str
    resolved: bool
    is_known_issue: bool
    root_cause_tag: Optional[str]
    module: Optional[str]
    based_on_memory_count: int
    based_on_directive_count: int
    raw_text: str


class MemoryService:
    """The agent's memory: two-bank layout, directives, mental models."""

    def __init__(self, client: HindsightLike, settings: Settings):
        self.client = client
        self.settings = settings

    # ------------------------------------------------------------------
    # Bank bootstrap
    # ------------------------------------------------------------------

    def ensure_shared_bank(self) -> None:
        bank_id = self.settings.shared_bank_id
        self.client.create_bank(
            bank_id=bank_id,
            name="Known Issues",
            mission=SHARED_BANK_MISSION.format(product=self.settings.product_name),
        )
        self.client.create_mental_model(
            bank_id=bank_id,
            name=KNOWN_ISSUES_MENTAL_MODEL["name"],
            source_query=KNOWN_ISSUES_MENTAL_MODEL["source_query"],
            tags=["digest"],
        )
        logger.info("shared bank ready: %s", bank_id)

    def ensure_customer_bank(self, customer_id: str, customer_name: str) -> str:
        bank_id = self.settings.customer_bank_id(customer_id)
        self.client.create_bank(
            bank_id=bank_id,
            name=f"Customer memory — {customer_name}",
            mission=CUSTOMER_BANK_MISSION.format(product=self.settings.product_name),
        )
        for directive in SUPPORT_DIRECTIVES:
            self.client.create_directive(
                bank_id=bank_id,
                name=directive["name"],
                content=directive["content"],
                priority=directive["priority"],
            )
        self.client.create_mental_model(
            bank_id=bank_id,
            name=CUSTOMER_PROFILE_MENTAL_MODEL["name"],
            source_query=CUSTOMER_PROFILE_MENTAL_MODEL["source_query"],
            tags=["digest"],
        )
        logger.info("customer bank ready: %s", bank_id)
        return bank_id

    # ------------------------------------------------------------------
    # Retain (writing memory)
    # ------------------------------------------------------------------

    def retain_customer_message(self, customer_id: str, ticket_id: str,
                                 content: str, context: str = "support ticket") -> None:
        self.client.retain(
            bank_id=self.settings.customer_bank_id(customer_id),
            content=content,
            context=context,
            tags=[f"ticket:{ticket_id}"],
        )

    def retain_resolution(self, customer_id: str, ticket_id: str, outcome: ReflectOutcome) -> None:
        summary = (
            f"Ticket {ticket_id}: {outcome.raw_text}. "
            f"Sentiment observed: {outcome.sentiment}. "
            f"Resolved: {outcome.resolved}."
        )
        if outcome.root_cause_tag:
            summary += f" Root cause: {outcome.root_cause_tag}."
        tags = [f"ticket:{ticket_id}", "resolution"]
        if outcome.resolved:
            tags.append("resolved")
        self.client.retain(
            bank_id=self.settings.customer_bank_id(customer_id),
            content=summary,
            context="ticket resolution",
            tags=tags,
        )

    def retain_known_issue(self, outcome: ReflectOutcome, ticket_id: str) -> None:
        """Distill a systemic issue into the shared cross-customer bank.

        Deliberately excludes any customer-identifying detail — only the
        technical shape of the issue and how it was fixed.
        """
        module = outcome.module or "unspecified-module"
        content = (
            f"Recurring issue in module '{module}'. Root cause: "
            f"{outcome.root_cause_tag or 'undiagnosed'}. "
            f"Resolution notes: {outcome.raw_text}"
        )
        self.client.retain(
            bank_id=self.settings.shared_bank_id,
            content=content,
            context="known issue",
            tags=["known-issue", f"module:{module}", f"ticket:{ticket_id}"],
        )

    def seed_history(self, customer_id: str, items: list[dict]) -> None:
        """Bulk-load synthetic ticket history so a demo customer looks like
        they have weeks of real interaction history instantly."""
        self.client.retain_batch(
            bank_id=self.settings.customer_bank_id(customer_id),
            items=items,
        )

    def seed_resolved_ticket(self, customer_id: str, ticket_id: str, timestamp: str,
                              customer_message: str, resolution_summary: str,
                              sentiment: str, resolved: bool,
                              root_cause_tag: Optional[str], is_known_issue: bool,
                              module: Optional[str]) -> None:
        """Backfill a single already-resolved historical ticket straight into
        memory (both the customer bank and, if systemic, the shared bank),
        skipping the live reflect() call since the outcome is already known.
        Used only by the demo-data seeder.
        """
        self.client.retain_batch(
            bank_id=self.settings.customer_bank_id(customer_id),
            items=[
                {
                    "content": customer_message,
                    "context": "support ticket",
                    "timestamp": timestamp,
                    "tags": [f"ticket:{ticket_id}"],
                },
                {
                    "content": (
                        f"Ticket {ticket_id}: {resolution_summary} "
                        f"Sentiment observed: {sentiment}. Resolved: {resolved}."
                        + (f" Root cause: {root_cause_tag}." if root_cause_tag else "")
                    ),
                    "context": "ticket resolution",
                    "timestamp": timestamp,
                    "tags": [f"ticket:{ticket_id}", "resolution"] + (["resolved"] if resolved else []),
                },
            ],
        )
        if is_known_issue:
            mod = module or "unspecified-module"
            self.client.retain(
                bank_id=self.settings.shared_bank_id,
                content=(
                    f"Recurring issue in module '{mod}'. Root cause: "
                    f"{root_cause_tag or 'undiagnosed'}. Resolution notes: {resolution_summary}"
                ),
                context="known issue",
                timestamp=timestamp,
                tags=["known-issue", f"module:{mod}", f"ticket:{ticket_id}"],
            )

    # ------------------------------------------------------------------
    # Recall (reading memory)
    # ------------------------------------------------------------------

    def recall_known_issues(self, query: str, max_results_tokens: int = 800) -> list[RecalledMemory]:
        result = self.client.recall(
            bank_id=self.settings.shared_bank_id,
            query=query,
            budget="low",
            max_tokens=max_results_tokens,
            tags=["known-issue"],
        )
        out: list[RecalledMemory] = []
        for r in getattr(result, "results", []) or []:
            score = None
            scores = getattr(r, "scores", None)
            if scores is not None:
                score = getattr(scores, "final", None)
            out.append(RecalledMemory(text=r.text, tags=list(getattr(r, "tags", None) or []), score=score))
        return out

    # ------------------------------------------------------------------
    # Reflect (generating the reply + structured learning signal)
    # ------------------------------------------------------------------

    def reflect_reply(self, customer_id: str, message: str,
                       known_issue_context: list[RecalledMemory]) -> ReflectOutcome:
        context_lines = [f"Product: {self.settings.product_name}."]
        if known_issue_context:
            context_lines.append("Potentially related known issues on file:")
            for m in known_issue_context:
                context_lines.append(f"- {m.text}")
        context_lines.append(f'Customer\'s latest message: "{message}"')

        response = self.client.reflect(
            bank_id=self.settings.customer_bank_id(customer_id),
            query=message,
            budget="mid",
            context="\n".join(context_lines),
            response_schema=AGENT_REFLECT_SCHEMA,
            apply_all_directives=True,
        )

        structured = getattr(response, "structured_output", None) or {}
        based_on = getattr(response, "based_on", None)
        memory_count = len(getattr(based_on, "memories", None) or []) if based_on else 0
        directive_count = len(getattr(based_on, "directives", None) or []) if based_on else 0

        return ReflectOutcome(
            reply=structured.get("reply") or getattr(response, "text", "") or "",
            sentiment=structured.get("sentiment", "neutral"),
            resolved=bool(structured.get("resolved", False)),
            is_known_issue=bool(structured.get("is_known_issue", False)),
            root_cause_tag=structured.get("root_cause_tag"),
            module=structured.get("module"),
            based_on_memory_count=memory_count,
            based_on_directive_count=directive_count,
            raw_text=getattr(response, "text", "") or structured.get("reply", ""),
        )

    # ------------------------------------------------------------------
    # Mental models (always-current digests shown in the UI)
    # ------------------------------------------------------------------

    def _find_mental_model_id(self, bank_id: str, name: str) -> Optional[str]:
        models = self.client.list_mental_models(bank_id=bank_id)
        for m in getattr(models, "items", None) or []:
            if getattr(m, "name", None) == name:
                return getattr(m, "id", None)
        return None

    def refresh_customer_profile(self, customer_id: str) -> None:
        bank_id = self.settings.customer_bank_id(customer_id)
        mm_id = self._find_mental_model_id(bank_id, CUSTOMER_PROFILE_MENTAL_MODEL["name"])
        if mm_id:
            self.client.refresh_mental_model(bank_id=bank_id, mental_model_id=mm_id)

    def refresh_known_issues_digest(self) -> None:
        bank_id = self.settings.shared_bank_id
        mm_id = self._find_mental_model_id(bank_id, KNOWN_ISSUES_MENTAL_MODEL["name"])
        if mm_id:
            self.client.refresh_mental_model(bank_id=bank_id, mental_model_id=mm_id)

    def get_mental_model_content(self, bank_id: str, name: str) -> Optional[str]:
        models = self.client.list_mental_models(bank_id=bank_id, detail="content")
        for m in getattr(models, "items", None) or []:
            if getattr(m, "name", None) == name:
                return getattr(m, "content", None)
        return None

    def customer_profile(self, customer_id: str) -> Optional[str]:
        return self.get_mental_model_content(
            self.settings.customer_bank_id(customer_id),
            CUSTOMER_PROFILE_MENTAL_MODEL["name"],
        )

    def known_issues_digest(self) -> Optional[str]:
        return self.get_mental_model_content(
            self.settings.shared_bank_id,
            KNOWN_ISSUES_MENTAL_MODEL["name"],
        )
