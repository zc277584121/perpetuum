# Feedback: inbox and escalations

This reference covers the two human-↔-agent communication channels.
Read this when the user wants to push a new instruction in, answer
something the agent asked, or generally adjust direction without
stopping the loop.

## Two channels, mirror-symmetric

```
                  ┌─────── inbox.md ──────────┐  ← user pushes
                  │  user writes instructions, │
                  │  agent reads at every      │
                  │  cycle's prompt 1          │
                  └────────────────────────────┘

                  ┌─── escalations.md ────────┐  ← agent pulls
                  │  agent writes uncertain    │
                  │  cases with options, user  │
                  │  fills in answers          │
                  └────────────────────────────┘
```

Both are markdown with two sections. Both stay local (not in git
unless the user opted in).

## inbox.md — user → agent

### Structure

```markdown
# Inbox

> Write what you want the agent to know/do under "## Pending".
> The agent reads this at the start of every cycle and migrates
> processed items to "## Processed".

## Pending

- (your items here)

## Processed

- (agent moves processed items here, with a brief note)
```

### Recommended verbs (not enforced)

These help the agent parse intent, but plain natural-language sentences
work too:

| Verb | Meaning |
|---|---|
| `SKIP:` | drop this from the backlog, don't try it again |
| `PRIORITIZE:` | move this to the front of the next cycle |
| `ADD:` | add a new dimension/category I want covered |
| `STOP:` | stop doing X (e.g. "stop editing README, I'm taking it over") |
| `DIRECTION:` | shift focus from one area to another |
| `NOTE:` | informational, no action required, but use as context |

### Example

```markdown
## Pending

- SKIP: postgres backend swap — I'm not going to support PG, drop those
- PRIORITIZE: PR #123 just landed, look at it before backlog
- ADD: add a dimension: behavior under network partition (kill the
  milvus container mid-add)
- NOTE: I'm out of office tomorrow, don't escalate anything urgent
- (plain natural language also works: the agent reads anything you write here)
```

### When the agent processes inbox items

In prompt 1 (the explore phase), the agent should:
1. Read `## Pending`
2. For each item, decide how to act:
   - `SKIP` → annotate `plan.md` Pending entries with skip markers,
     or remove them
   - `PRIORITIZE` → reorder the Pending list
   - `ADD` → append to Pending
   - `STOP` → respect the constraint going forward
   - `DIRECTION` → reflect in next cycle's exploration choice
   - `NOTE` → just absorb as context
3. Move processed items to `## Processed`, optionally with a one-line
   note about how it was handled and which cycle

## escalations.md — agent → user

### Structure

```markdown
# Escalations

> Questions the agent surfaces for human judgment. Write your answer
> under "## Resolved" (move the item there too), or edit a Pending item
> in-place if you just want to clarify.

## Open

### (cycle <id>) Brief title

**Context:** what's being tested / why it matters
**Question:** what's ambiguous / what specifically needs the human's input
**Options:** A / B / C with trade-offs

## Resolved

(answered items move here with the user's answer)
```

### Good escalations vs. bad ones

A good escalation is **actionable in five minutes** by the user.

| Bad | Good |
|---|---|
| "What should I do?" | "PR #123 changes a public API name. Options: A keep old name as alias / B break and document / C bikeshed in maintainers chat." |
| "Need help with the auth flow" | "OAuth callback should fail open or fail closed on Slack 5xx? Spec doesn't say. A: silent skip with WARN log / B: hard error 503. Both are reasonable." |
| "Decided to skip this for now" | (don't escalate; just mark plan.md item BLOCKED with reason) |

In `prompts/2_execute.md`, instruct the middle agent to:
- Always include **context + question + 2–3 options with trade-offs**
- Use the user's language (per the Language rule)
- Move items to `## Resolved` only after the user has answered (the user
  fills in answers themselves; the agent doesn't move them
  preemptively)

### How the user answers

Three valid forms:

1. **Pick a letter** — `A` / `B` / `pick C`
2. **Write a sentence** — `keep backward-compatible, add an alias`
3. **Decline to decide** — `SKIP for now, decide later` (the agent then drops
   the item from active consideration)

After answering, the user moves the item to `## Resolved` themselves
(small social contract: the user owns the move because that signals
"I've decided"). Or they can ask Layer 4 agent to do it for them.

## Three-tier write hierarchy

When the user wants to express something, suggest the lightest
appropriate tier:

| Intent | Use |
|---|---|
| Answer a specific question the agent asked | edit `escalations.md` |
| Push a new instruction or shift | edit `inbox.md` |
| Quickly remove a single Pending item | also `inbox.md` with `SKIP:` |
| Change the prompt template behavior permanently | edit `prompts/1_explore.md` or `prompts/2_execute.md` directly |
| Reshape `plan.md` directly | discouraged, but allowed (see below) |

## plan.md editing

Filesystem doesn't lock plan.md. If the user really wants to edit it
directly:

- Append-only changes (add a new Pending item) are usually safe.
- Reordering / removing items is risky — the next cycle might re-discover
  what was removed or skip items mid-execution.
- Editing existing `[x]` Done entries to change the recorded status is
  almost never what the user wants — git history is the source of truth
  for what actually happened.

Default suggestion: **route through `inbox.md`**. Only edit plan.md
directly if the user is explicit and accepts the risk.

## Closing the loop: when the user wants to discuss before answering

If the user opens an escalation, reads the question, and wants to talk
through it before answering — that's a Layer 4 conversation with you,
not a perpetuum operation. Have the conversation, help them think,
then either you or they write the final answer into `escalations.md`.
The middle agent does not need to be in this conversation.
