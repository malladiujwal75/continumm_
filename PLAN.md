# Continuum — Memory-Native Support Agent
### Built for "AI Agents That Learn Using Hindsight"

## 1. Problem chosen, and why

Category: **Operations & Support → Customer Support Agent**, with a twist that turns it
into two Hindsight memory patterns at once instead of one:

- **Per-customer memory** (`customer::{id}` bank) — the agent remembers *this*
  customer's environment, what it already tried, and how it feels — across
  tickets, not just within one chat.
- **Shared cross-customer memory** (`product::known-issues` bank) — resolved
  tickets that turn out to be systemic get distilled into a shared bank, so
  the agent recognizes "this is the same bug three other people hit this
  week" the moment a new customer describes it.

Why this beats a plain "remembers your chats" bot:
- **Real business case.** Every SaaS company with a support inbox has this
  pain — reps re-reading ticket history, customers repeating themselves,
  the same bug reported five times before someone connects the dots. This
  is a "would pay $50/month" workflow, not a novelty.
- **Memory is structurally the star.** The demo isn't "the bot remembers my
  name" — it's a visible before/after: ticket #1 is generic, ticket #5 skips
  three diagnostic questions because the agent already knows the answers,
  and a *different* customer's ticket gets flagged as a known issue because
  of what a *third* customer reported last week. That's individual learning
  **and** collective learning from one memory substrate.
- **Explainable in 60 seconds.** One screen, one toggle (memory on/off),
  one side-by-side reply for the same message.

Rejected alternatives: a Deal Intelligence agent (harder to fake believable
multi-week CRM state in one day) and an Incident Response agent (overlaps
technically with the known-issues idea here, but support has a punchier,
faster demo and a clearer non-technical audience for the judges).

## 2. What "learning" means here (the closed loop)

Hindsight's `reflect()` doesn't just answer — it can return **structured
output** alongside the reply. Continuum uses that to close the loop:

```
customer message
      │
      ▼
 recall(product::known-issues)  ──▶ "is this already a known bug?"
      │
      ▼
 reflect(customer::{id}, context = message + known-issue snippets,
         response_schema = {reply, sentiment, resolved, root_cause_tag,
                             is_known_issue}, apply_all_directives=True)
      │
      ├─▶ structured_output.reply           → shown to the customer
      │
      └─▶ retain(customer::{id}, "resolution + sentiment + root cause")
                │
                └─▶ if is_known_issue:
                        retain(product::known-issues, distilled signature)
```

Every resolved ticket **writes back** into memory. The next ticket — from
this customer, or any customer — recalls against a bank that just got
smarter. That write-back is the actual "learning," not just storage.

## 3. Hindsight surface area used

| Feature | Used for |
|---|---|
| `retain` / `retain_batch` | Logging ticket events, resolutions, and demo history seeding |
| `recall` | Pre-flight check against the shared known-issues bank |
| `reflect` (+ `response_schema`, `apply_all_directives`) | Generating the agent's reply and extracting structured learning signals in one call |
| `create_directive` / directives | Org support policy (tone, refund cap, escalation rule) applied consistently per reply |
| `create_mental_model` / `refresh_mental_model` | Auto-refreshing "Customer Profile" (per customer) and "Known Issues Digest" (shared) — pre-computed, always-current summaries shown in the UI |
| Tags (`ticket:{id}`, `module:{x}`, `resolved`) | Filtering recall/reflect and grouping by feature area |

## 4. Architecture

```
frontend/index.html  (vanilla JS console, no build step)
        │  fetch() JSON
        ▼
app/main.py  (FastAPI routes)
        │
        ├── app/agent_service.py   — orchestration + the two Strategy
        │        │                    implementations (with/without memory)
        │        ▼
        ├── app/memory_service.py  — Adapter/Facade over hindsight-client
        │        ▼
        │   Hindsight (Cloud or self-hosted, via hindsight-client SDK)
        │
        ├── app/llm_baseline.py    — direct Groq call, no memory at all
        │                             (the honest "without Hindsight" baseline)
        │
        └── app/repository.py      — SQLite: customers, tickets, messages
                 ▼
            app/db.py  (system of record for the raw transcript)
```

**Separation of concerns is deliberate:** Hindsight is the agent's semantic
*memory* (distilled facts, not raw chat logs); SQLite is the system of
record for the literal transcript the UI renders. Conflating the two would
make the memory bank noisy and the transcript lossy.

### Design patterns
- **Adapter/Facade** (`MemoryService`) — isolates the rest of the app from
  the Hindsight SDK, so it's mockable in tests and swappable if the SDK
  changes.
- **Strategy** (`AgentStrategy` → `WithMemoryStrategy`, `NoMemoryStrategy`) —
  same interface, two behaviours, which is exactly what the side-by-side
  demo needs and keeps the comparison honest (no special-casing in routes).
- **Repository** (`CustomerRepository`, `TicketRepository`) — isolates SQL
  from business logic.
- **Dependency injection** via FastAPI `Depends` — services are constructed
  once and injected, so tests substitute a fake `MemoryService` cleanly.
- **Observer-style write-back hook** (`on_ticket_resolved`) — decouples "a
  ticket got resolved" from "what memory writes that implies."

## 5. Data model (SQLite — system of record)

```
customers(id, name, plan, environment, created_at)
tickets(id, customer_id, subject, status, created_at)
messages(id, ticket_id, role, content, memory_mode, created_at)
```

## 6. Phased build (how this was actually built)

| Phase | Deliverable |
|---|---|
| 0 | Confirm real `hindsight-client` v0.10.1 API surface against source (avoids guessed method signatures) |
| 1 | `memory_service.py` — bank bootstrap, retain/recall/reflect wrappers, directive + mental-model setup |
| 2 | `db.py` + `repository.py` — SQLite schema and repositories |
| 3 | `agent_service.py` — Strategy pair + closed learning loop |
| 4 | `main.py` — FastAPI routes (customers, thread, send message, seed demo data, memory insights) |
| 5 | `frontend/index.html` — console UI: thread, memory-on/off toggle, memory insight panel |
| 6 | `tests/` — fake Hindsight double + pytest suite exercising the full API via `TestClient` |
| 7 | Packaging — README, `.env.example`, `docker-compose.yml`, seed data, content-guide drafts, zip |

## 7. Running it (two paths, pick one)

**A — Hindsight Cloud (fastest, no Docker):** sign up, apply promo code
`MEMHACK99` for $50 credit, copy the API key into `.env`. See `README.md`.

**B — Self-hosted:** `docker compose up` starts Hindsight locally (Groq as
the LLM provider) alongside the FastAPI app.

## 8. Judging-criteria checklist

- **Innovation (30%)** — two memory patterns (individual + collective) wired
  through one closed learning loop, not a single-bank chatbot.
- **Use of Hindsight memory (25%)** — retain, recall, reflect with structured
  output, directives, and auto-refreshing mental models are all exercised;
  the UI makes the recalled memories and mental-model content visible, not
  hidden behind the reply text.
- **Technical implementation (20%)** — typed, tested, documented, clean
  separation of concerns; `tests/` runs against a fake Hindsight client so
  the whole request path is verified without needing live credentials.
- **User experience (15%)** — one screen, one toggle, a memory panel that
  narrates *why* the agent said what it said.
- **Real-world impact (10%)** — a workflow real support teams already pay
  vendors for; the known-issues bank is a genuinely new value-add on top of
  "remembers the customer."
