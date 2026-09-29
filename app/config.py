"""
Central configuration. Everything is read from environment variables so the
same code runs against Hindsight Cloud or a self-hosted instance, and
against any OpenAI-compatible LLM gateway for the no-memory baseline.

Nothing here talks to the network — it just resolves settings.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _env_bool(name: str, default: bool = False) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    # --- Hindsight ---
    hindsight_base_url: str = field(default_factory=lambda: _env(
        "HINDSIGHT_BASE_URL", "http://localhost:8888"
    ))
    hindsight_api_key: str = field(default_factory=lambda: _env("HINDSIGHT_API_KEY", ""))

    # --- No-memory baseline LLM (OpenAI-compatible endpoint, e.g. Groq) ---
    baseline_llm_base_url: str = field(default_factory=lambda: _env(
        "BASELINE_LLM_BASE_URL", "https://api.groq.com/openai/v1"
    ))
    baseline_llm_api_key: str = field(default_factory=lambda: _env("GROQ_API_KEY", ""))
    baseline_llm_model: str = field(default_factory=lambda: _env(
        "BASELINE_LLM_MODEL", "openai/gpt-oss-120b"
    ))

    # --- App ---
    product_name: str = field(default_factory=lambda: _env("PRODUCT_NAME", "Nimbus Sync"))
    db_path: str = field(default_factory=lambda: _env("DB_PATH", "continuum.db"))
    shared_bank_id: str = field(default_factory=lambda: _env(
        "SHARED_BANK_ID", "product::known-issues"
    ))
    demo_mode: bool = field(default_factory=lambda: _env_bool("DEMO_MODE", True))

    def customer_bank_id(self, customer_id: str) -> str:
        return f"customer::{customer_id}"


settings = Settings()
