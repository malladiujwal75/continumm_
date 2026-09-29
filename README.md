# Continuum

**A memory-native customer support agent, built on [Hindsight](https://hindsight.vectorize.io).**
Built for the "AI Agents That Learn Using Hindsight" hackathon.

Continuum remembers each customer across tickets — their environment, what
they've already tried, how they feel — *and* remembers across customers: a
bug three people hit this week gets recognized as a known issue the moment
a fourth customer describes it. Every reply writes its own outcome back
into memory, so the agent is measurably smarter on ticket 20 than on
ticket 1. See [`PLAN.md`](PLAN.md) for the full architecture writeup and
how this maps to the judging criteria.

## Quickstart

You need **Python 3.10+** and either a Hindsight Cloud account (fastest,
no Docker) or Docker (fully self-hosted). Pick one.

### Path A — Hindsight Cloud (recommended)

1. Sign up at [ui.hindsight.vectorize.io](https://ui.hindsight.vectorize.io)
   and create a memory bank org.
2. Click **Connect → Create API Key**, copy it.
3. Under **Billing**, apply promo code `MEMHACK99` for $50 free credit.
4. `cp .env.example .env` and fill in `HINDSIGHT_API_KEY`. Optionally add
   a `GROQ_API_KEY` from [console.groq.com](https://console.groq.com) —
   this only powers the "memory off" comparison baseline; the app runs
   fine without it (it falls back to a labeled placeholder reply).
5. `./run.sh` — starts the app at **http://localhost:8000**.

### Path B — self-hosted (Docker)

1. `cp .env.example .env`, set `GROQ_API_KEY` (Hindsight itself uses Groq
   as its LLM provider here — free tier is fine).
2. `docker compose up` — starts Hindsight (ports 8888/9999) and the app
   (port 8000).
3. Open **http://localhost:8000**.

### Running the demo

1. Click **Seed demo history** — loads five synthetic customers, several
   with weeks of realistic prior tickets already written into memory.
2. Select **Marcus Chen**, send his prefilled live message. The agent
   references his VPN environment and — because he explicitly said so in
   an earlier ticket — never suggests restarting his router.
3. Select **Dana Whitfield**, send her live message. Her issue matches two
   *other* customers' resolved tickets, distilled into the shared
   known-issues bank — the agent flags it as systemic on the first try.
4. Type any message and click **Compare with / without memory** to see
   the exact same input handled with and without Hindsight, side by side.

A full shot-by-shot script is in [`content/video_script.md`](content/video_script.md).

## Running the tests

```bash
pip install -r requirements-dev.txt
pytest -v
```

18 tests exercise the full request path — repositories, the Hindsight
adapter, both agent strategies, and every API route — against a
`FakeHindsight` test double (`tests/fake_hindsight.py`) that implements
the same method surface as the real SDK. No network access or API key
required to run the suite.

## Project structure

```
app/
  config.py            settings from environment variables
  db.py                SQLite schema + connection lifecycle
  repository.py         Repository pattern: Customer/Ticket/Message
  schemas_hindsight.py  bank missions, directives, reflect response_schema,
                         mental model definitions — the agent's whole
                         policy layer in one auditable file
  memory_service.py     Adapter/Facade over hindsight-client
  llm_baseline.py       stateless "no memory" comparison baseline (Groq)
  agent_service.py      Strategy pair (WithMemory / NoMemory) + closed
                         learning loop + transcript orchestration
  seed_data.py           loads data/seed_tickets.json into DB + memory
  main.py                FastAPI routes
frontend/index.html       single-file vanilla JS console UI, no build step
data/seed_tickets.json    synthetic customers + multi-week ticket history
content/                  article / social post / video script drafts
                           (hackathon content-guide deliverables)
scripts/bootstrap_banks.py  production bootstrap (shared bank only, no
                             demo data) — see its docstring
tests/                    pytest suite + FakeHindsight test double
PLAN.md                   architecture, design patterns, phased build log
```

## Submission checklist

- [x] GitHub repo with clean, documented, tested code
- [ ] Demo video — record using `content/video_script.md`
- [ ] Live demo to judges — `./run.sh` or `docker compose up`, then walk
      the flow above
- [x] Content deliverables drafted — `content/article.md`,
      `content/social_post.md`, `content/video_script.md` (personalize
      before posting)
- [x] Explanation of Hindsight memory usage — `PLAN.md` §3–4, and visible
      live in the UI's Memory Insight panel (memories used, directives
      applied, mental-model digests, known-issue matches)
