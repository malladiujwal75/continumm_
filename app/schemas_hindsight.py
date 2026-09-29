"""
Everything that shapes *how* Hindsight thinks for this bank: the mission,
the support-policy directives applied to every reply, the JSON schema used
to pull structured learning signals out of `reflect()`, and the two mental
models that keep an always-current digest per customer and across the
whole customer base.

Kept as plain data in one place so the "what does the agent believe/follow"
surface is auditable at a glance — a judge (or a teammate) can read this
file top to bottom and know the agent's whole policy layer.
"""
from __future__ import annotations

CUSTOMER_BANK_MISSION = (
    "You are the long-term memory for a customer support agent at {product}. "
    "Remember each customer's environment (device, OS, plan, integrations), "
    "what troubleshooting steps they have already tried, what has already "
    "been resolved, and how they tend to feel (frustrated, patient, technical "
    "vs non-technical). Never make the customer repeat information you "
    "already have."
)

SHARED_BANK_MISSION = (
    "You are the collective memory of every support ticket ever resolved for "
    "{product}, across all customers. Remember which bugs and issues are "
    "recurring, which modules they affect, and what fix or workaround "
    "resolved them. Do not store any individual customer's personal details "
    "here — only the technical shape of the issue and its resolution."
)

# Support-policy directives, created once on every customer bank at creation
# time so every reply from that bank is governed by the same rules.
SUPPORT_DIRECTIVES: list[dict] = [
    {
        "name": "tone",
        "content": (
            "Be warm, concise, and specific. Never ask the customer to repeat "
            "information already in memory — reference it instead. If the "
            "customer sounds frustrated, acknowledge it in one short sentence "
            "before troubleshooting."
        ),
        "priority": 10,
    },
    {
        "name": "known-issue-disclosure",
        "content": (
            "If the issue matches a known, unresolved systemic bug, say so "
            "plainly and set expectations on a fix — do not pretend it is a "
            "one-off local problem."
        ),
        "priority": 8,
    },
    {
        "name": "refund-policy",
        "content": (
            "You may offer service credit up to one month's plan value without "
            "escalation. Anything larger requires a human to approve — say you "
            "are looping in a human rather than promising it yourself."
        ),
        "priority": 5,
    },
]

# response_schema passed to reflect(): the agent's reply AND the structured
# signals we write back into memory come out of the same call.
AGENT_REFLECT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "reply": {
            "type": "string",
            "description": "The support agent's reply to send to the customer.",
        },
        "sentiment": {
            "type": "string",
            "enum": ["positive", "neutral", "frustrated", "angry"],
            "description": "The customer's apparent sentiment in their latest message.",
        },
        "resolved": {
            "type": "boolean",
            "description": "True if this reply fully resolves the customer's issue.",
        },
        "root_cause_tag": {
            "type": ["string", "null"],
            "description": "A short slug for the underlying cause, e.g. 'sync-timeout-vpn', or null if not yet diagnosed.",
        },
        "is_known_issue": {
            "type": "boolean",
            "description": "True if this matches a systemic issue affecting multiple customers, not a one-off.",
        },
        "module": {
            "type": ["string", "null"],
            "description": "The product module or feature area this ticket concerns, e.g. 'sync-engine', 'billing', 'mobile-app'.",
        },
    },
    "required": ["reply", "sentiment", "resolved", "is_known_issue"],
}

CUSTOMER_PROFILE_MENTAL_MODEL = dict(
    name="Customer Profile",
    source_query=(
        "Summarize this customer: who they are, their environment/plan, what "
        "they have already tried, any unresolved issues, their sentiment "
        "trend across tickets, and anything they've explicitly asked not to "
        "be asked again."
    ),
)

KNOWN_ISSUES_MENTAL_MODEL = dict(
    name="Known Issues Digest",
    source_query=(
        "List the current recurring issues affecting multiple customers: "
        "what module each affects, how many times it has come up, and the "
        "workaround or fix status for each."
    ),
)
