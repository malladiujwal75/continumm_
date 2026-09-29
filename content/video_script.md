# Demo video script — target ~2:30

Record the console UI at `localhost:8000`. Seed demo data before hitting
record so the walkthrough is smooth. Suggested screen capture at 1080p,
narrate live rather than adding voiceover in post — it's faster and
sounds more authentic for a hackathon demo.

---

**0:00 – 0:20 — The problem (talking head or voiceover over a blank
inbox / generic chatbot screenshot)**

> "Every support team has the same bad day on repeat: a customer explains
> their setup, gets a fix, and three weeks later explains the exact same
> setup to an agent that's forgotten everything. Meanwhile two other
> customers are hitting the same bug and nobody connects the dots. That's
> what I built Continuum to fix, using Hindsight as the memory layer."

**0:20 – 0:35 — Seed the demo data**

Click **Seed demo history**. Narrate while it loads:

> "This instantly loads five customers with weeks of real ticket history
> already in memory — so you can see what week six looks like, not just
> message one."

**0:35 – 1:10 — Individual memory (Marcus)**

Select **Marcus Chen**. Point out his ticket history in the thread (VPN
sync issue, twice, then a different mobile bug). Send his live message
("it's happening again — third time this month").

> "Watch what happens. The agent doesn't ask him what device he's on or
> whether he's tried restarting his router — because he told us three
> weeks ago that restarting his router never works, and it remembers
> that. It goes straight to a fix."

Point at the right-hand **Memory Insight** panel: memories used, sentiment,
resolved badge.

**1:10 – 1:40 — Collective memory (Dana)**

Select **Dana Whitfield**. Send her live message about sync failing after
her laptop wakes from sleep.

> "Dana's never reported this before. But two *other* customers did, in
> the last two weeks — and their resolved tickets got distilled into a
> shared 'known issues' memory. Watch the agent flag it immediately as a
> known issue, not a one-off."

Point at the **known issue** badge and the Known Issues Digest panel.

**1:40 – 2:05 — Before / after, same message**

Back on Marcus's ticket, type his message again and click **Compare with
/ without memory**. Show both cards side by side.

> "Same exact message, two strategies. On the left: grounded in memory,
> policy-aware, specific. On the right: a stateless call with zero
> context. That's the entire value proposition in one screenshot."

**2:05 – 2:25 — How it's built (quick architecture beat)**

Cut to PLAN.md or narrate over the code:

> "Under the hood, every reply comes from one Hindsight reflect() call
> that returns the response text and structured signals — sentiment, root
> cause, whether it's systemic — in the same call. Those signals get
> written straight back into memory, so the next ticket recalls against a
> bank that just got smarter. That closed loop is the actual learning."

**2:25 – 2:30 — Close**

> "Continuum — memory-native support, built on Hindsight. Repo link
> below."

---

## Shot checklist
- [ ] Seed demo data on camera (shows it's not pre-baked)
- [ ] At least one full customer thread with visible history
- [ ] The Known Issues badge triggering on a *different* customer
- [ ] The compare view, side by side, same message
- [ ] One sentence on the closed learning loop (memory-use judging weight
      is 25% — make it visible, not just claimed)
