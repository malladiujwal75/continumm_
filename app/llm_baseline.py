"""
The honest "without Hindsight" baseline: a single stateless chat completion
against an OpenAI-compatible endpoint (Groq by default), with no retain, no
recall, no memory of any kind — just the raw customer message and a generic
system prompt. This is what the side-by-side demo compares against.

Uses plain httpx against the OpenAI-compatible `/chat/completions` shape so
no extra SDK is needed beyond a dependency `hindsight-client` already pulls
in transitively.
"""
from __future__ import annotations

import logging

import httpx

from .config import Settings

logger = logging.getLogger("continuum.baseline")

SYSTEM_PROMPT = (
    "You are a helpful customer support agent. You have no prior history "
    "with this customer and no knowledge of past tickets — answer using "
    "only what they tell you in this single message."
)


class BaselineLLM:
    """Stateless chat completion — the 'no memory' comparison strategy."""

    def __init__(self, settings: Settings, timeout: float = 30.0):
        self.settings = settings
        self.timeout = timeout

    def reply(self, message: str) -> str:
        if not self.settings.baseline_llm_api_key:
            return (
                "[No GROQ_API_KEY configured — this is a placeholder reply. "
                "Set GROQ_API_KEY in .env to see the real stateless baseline.] "
                "Thanks for reaching out — could you tell me more about your "
                "setup (device, OS, what you've already tried) so I can help?"
            )
        url = f"{self.settings.baseline_llm_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.baseline_llm_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message},
            ],
            "temperature": 0.4,
            "max_tokens": 300,
        }
        headers = {"Authorization": f"Bearer {self.settings.baseline_llm_api_key}"}
        try:
            resp = httpx.post(url, json=payload, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # pragma: no cover - network path, exercised via fakes in tests
            logger.warning("baseline LLM call failed: %s", exc)
            return (
                "Sorry — I'm having trouble reaching support right now. "
                "Could you try again in a moment?"
            )
