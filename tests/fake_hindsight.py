"""
A fake Hindsight client implementing the same method surface as the real
`hindsight-client` SDK (verified against v0.10.1's actual signatures — see
PLAN.md section 3). Lets the whole app be exercised in tests with zero
network access and zero API key.

It's a small in-memory simulation, not a mock: retain actually stores
text, recall does simple substring/keyword scoring, reflect fabricates a
plausible structured response from what's in memory. Good enough to prove
the orchestration logic (agent_service.py, main.py routes) is wired
correctly end to end.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any, Optional


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


@dataclass
class _Bank:
    bank_id: str
    name: str = ""
    mission: str = ""
    memories: list[dict] = field(default_factory=list)
    directives: list[dict] = field(default_factory=list)
    mental_models: dict[str, dict] = field(default_factory=dict)


class FakeHindsight:
    def __init__(self, base_url: str = "http://fake", api_key: Optional[str] = None):
        self.base_url = base_url
        self.banks: dict[str, _Bank] = {}
        self.reflect_queue: list[dict] = []  # optional scripted responses for tests

    # -- bank / directive / mental model management -----------------

    def create_bank(self, bank_id: str, **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.setdefault(bank_id, _Bank(bank_id=bank_id))
        bank.name = kwargs.get("name", bank.name)
        bank.mission = kwargs.get("mission", bank.mission)
        return SimpleNamespace(bank_id=bank_id, name=bank.name, mission=bank.mission)

    def create_directive(self, bank_id: str, name: str, content: str,
                          priority: int = 0, is_active: bool = True,
                          tags: Optional[list[str]] = None) -> SimpleNamespace:
        bank = self.banks[bank_id]
        d = {"id": str(uuid.uuid4()), "name": name, "content": content, "priority": priority}
        bank.directives.append(d)
        return SimpleNamespace(**d)

    def list_directives(self, bank_id: str, **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.get(bank_id)
        items = [SimpleNamespace(**d) for d in (bank.directives if bank else [])]
        return SimpleNamespace(items=items, total=len(items))

    def create_mental_model(self, bank_id: str, name: str, source_query: str,
                             **kwargs: Any) -> SimpleNamespace:
        bank = self.banks[bank_id]
        mm_id = str(uuid.uuid4())
        bank.mental_models[mm_id] = {
            "id": mm_id, "bank_id": bank_id, "name": name,
            "source_query": source_query, "content": None,
        }
        return SimpleNamespace(mental_model_id=mm_id, operation_id=str(uuid.uuid4()))

    def list_mental_models(self, bank_id: str, **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.get(bank_id)
        items = [SimpleNamespace(**mm) for mm in (bank.mental_models.values() if bank else [])]
        return SimpleNamespace(items=items, total=len(items))

    def refresh_mental_model(self, bank_id: str, mental_model_id: str) -> SimpleNamespace:
        bank = self.banks[bank_id]
        mm = bank.mental_models[mental_model_id]
        texts = [m["content"] for m in bank.memories]
        mm["content"] = f"[{mm['name']} digest over {len(texts)} memories] " + " | ".join(texts[-5:])
        return SimpleNamespace(**mm)

    def get_mental_model(self, bank_id: str, mental_model_id: str, **kwargs: Any):
        return SimpleNamespace(**self.banks[bank_id].mental_models[mental_model_id])

    # -- retain / recall / reflect -----------------------------------

    def retain(self, bank_id: str, content: Any, **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.setdefault(bank_id, _Bank(bank_id=bank_id))
        bank.memories.append({
            "content": content,
            "tags": kwargs.get("tags") or [],
            "timestamp": kwargs.get("timestamp"),
            "context": kwargs.get("context"),
        })
        return SimpleNamespace(success=True, bank_id=bank_id, items_count=1)

    def retain_batch(self, bank_id: str, items: list[dict], **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.setdefault(bank_id, _Bank(bank_id=bank_id))
        for item in items:
            bank.memories.append({
                "content": item.get("content"),
                "tags": item.get("tags") or [],
                "timestamp": item.get("timestamp"),
                "context": item.get("context"),
            })
        return SimpleNamespace(success=True, bank_id=bank_id, items_count=len(items))

    def recall(self, bank_id: str, query: str, **kwargs: Any) -> SimpleNamespace:
        bank = self.banks.get(bank_id)
        results = []
        if bank:
            required_tags = set(kwargs.get("tags") or [])
            q_words = _words(query)
            for m in bank.memories:
                if required_tags and not required_tags.issubset(set(m["tags"])):
                    continue
                overlap = len(q_words & _words(str(m["content"])))
                if overlap > 0:
                    results.append(SimpleNamespace(
                        id=str(uuid.uuid4()), text=m["content"], tags=m["tags"],
                        scores=SimpleNamespace(final=float(overlap)),
                    ))
        return SimpleNamespace(results=results, trace=None, entities=None, chunks=None)

    def reflect(self, bank_id: str, query: str, **kwargs: Any) -> SimpleNamespace:
        if self.reflect_queue:
            scripted = self.reflect_queue.pop(0)
            return SimpleNamespace(
                text=scripted.get("reply", ""),
                structured_output=scripted,
                based_on=SimpleNamespace(
                    memories=[SimpleNamespace()] * scripted.get("_memory_count", 0),
                    mental_models=[], directives=[SimpleNamespace()] * scripted.get("_directive_count", 0),
                ),
            )
        bank = self.banks.get(bank_id, _Bank(bank_id=bank_id))
        memory_count = len(bank.memories)
        directive_count = len(bank.directives)
        known = "vpn" in query.lower() or "sync" in query.lower()
        reply = (
            f"Thanks for the update — based on your history I can see this connects to "
            f"{memory_count} prior notes on file. Let's get this sorted."
            if memory_count
            else "Thanks for reaching out — could you tell me a bit more about your setup?"
        )
        structured = {
            "reply": reply,
            "sentiment": "frustrated" if "again" in query.lower() else "neutral",
            "resolved": memory_count > 0,
            "is_known_issue": known and memory_count > 2,
            "root_cause_tag": "sync-timeout-vpn" if "vpn" in query.lower() else None,
            "module": "sync-engine" if known else None,
        }
        return SimpleNamespace(
            text=reply,
            structured_output=structured,
            based_on=SimpleNamespace(
                memories=[SimpleNamespace()] * memory_count,
                mental_models=[], directives=[SimpleNamespace()] * directive_count,
            ),
        )
