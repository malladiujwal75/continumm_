#!/usr/bin/env python3
"""
Production bootstrap: creates just the shared `product::known-issues` bank
(mission, mental model) without loading any synthetic demo customers.

The hackathon demo path is `POST /api/demo/seed`, which does this AND loads
five synthetic customers — use that for judging. Use this script instead
when wiring Continuum up to a real support queue, where customer banks get
created on the fly as real customers file their first ticket
(see MemoryService.ensure_customer_bank, called from AgentService).

Usage:
    python -m scripts.bootstrap_banks
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.memory_service import MemoryService


def main() -> None:
    from hindsight_client import Hindsight

    kwargs = {"base_url": settings.hindsight_base_url}
    if settings.hindsight_api_key:
        kwargs["api_key"] = settings.hindsight_api_key
    client = Hindsight(**kwargs)

    memory = MemoryService(client, settings)
    memory.ensure_shared_bank()
    print(f"Shared bank ready: {settings.shared_bank_id}")


if __name__ == "__main__":
    main()
