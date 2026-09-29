# Your support bot forgets everything. Ours remembers everyone.

Every support team has the same bad day, on repeat: a customer opens a
ticket, explains their setup, gets a fix — and three weeks later opens
another ticket and explains the exact same setup again, to an agent (human
or AI) with zero memory of the first conversation. Meanwhile, two other
customers are hitting the *same underlying bug*, and nobody connects the
dots until someone manually digs through the ticket queue.

That's the problem we built **Continuum** to fix, using
[Hindsight](https://hindsight.vectorize.io) as the memory layer.

## Two kinds of memory, one closed loop

Most "AI agent with memory" demos show one thing: the bot remembers your
name. Continuum uses Hindsight for two distinct memory patterns at once:

- **Per-customer memory.** Every customer gets their own Hindsight bank.
  Their environment, what they've already tried, how they tend to feel,
  and what's already been resolved all live there — so the agent never
  asks them to repeat themselves.
- **Shared, cross-customer memory.** Resolved tickets that turn out to be
  systemic bugs — not one-off user error — get distilled into a shared
  bank. When a *different* customer describes a similar problem, the agent
  recognizes it immediately: "this is a known issue affecting several
  users this week," instead of re-diagnosing from scratch.

The two memories aren't separate features bolted together — they share
one closed loop. Every reply comes out of a single `reflect()` call that
returns both the response text *and* structured signals (sentiment,
resolved, root cause, whether it's a known issue). Those signals get
written straight back into memory. The next ticket — from this customer,
or any customer — recalls against a bank that just got smarter. That
write-back is the actual learning, not just storage.

## Why it matters

This isn't a novelty. It's a workflow real support teams already pay
vendors five figures a year to get partially right. The value is concrete:
fewer repeated diagnostic questions, faster time-to-resolution on
recurring bugs, and a support agent that gets visibly better with every
ticket instead of resetting to zero every conversation.

We built it in a day, with directives governing tone and policy,
auto-refreshing mental models keeping a live "Customer Profile" and
"Known Issues Digest," and a side-by-side comparison mode that shows the
exact same message handled with memory on and memory off — so the value
of persistent memory isn't a claim, it's something you can watch happen.

*Built for the "AI Agents That Learn Using Hindsight" hackathon.*
