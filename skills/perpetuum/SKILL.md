---
name: perpetuum
description: >
  Set up, supervise, and control a persistent multi-layer "explore →
  execute → escalate" agent loop on a project. Use whenever a user asks
  to keep an agent running on a task across sessions or days — finding
  bugs, polishing writing, distilling a style, watching feeds, scanning
  for gaps, or any task whose value grows with how many findings the
  agent produces. Also use when the user wants to inspect, pause, resume,
  stop, or send a new instruction to an already-running perpetuum task.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# perpetuum

A persistent three-layer "explore → execute → escalate" loop on top of
`cc-use`. Designed for tasks whose value grows with how many findings
or improvements an agent can produce over hours or days.

This file is a router. Every mechanism below has a one-paragraph
summary here; details live in `references/`. Read the relevant
reference when the user's intent matches the corresponding section.

## When to invoke this skill

- The user wants to **start a new persistent loop** on a project
  (bug hunting, style distillation, PR/issue triage, observability
  scanning, etc.)
- The user wants to **inspect, pause, resume, stop, or nudge** an
  already-running loop
- The user wants to **answer an escalation** the loop has surfaced
- The user wants to **run multiple loops in parallel** on the same
  project via git worktree

If the user's intent isn't clear from "use perpetuum" alone, ask
before doing anything.

## Route by intent

| User wants to… | Read |
|---|---|
| Start a new task | `references/setup.md` + skim `examples/` |
| See current status | `references/status.md` |
| Pause / resume / stop / kill | `references/control.md` |
| Push an instruction / answer an escalation | `references/feedback.md` |
| Parallel lines via git worktree | `references/worktree.md` |
| Write or adjust `trigger.sh` | `references/trigger.md` |
| Understand the design rationale | `references/design.md` |

## How it works (architecture in one screen)

```
Layer 4   you + host agent     monitor + relay (optional)
   ↓
Layer 3   trigger.sh           heartbeat: paste prompts, wait for done
   ↓                                       flags, sleep, loop
Layer 2   middle agent (tmux)  judge + dispatch, two prompts:
   ↕                                       1_explore.md  (plan)
                                           2_execute.md  (dispatch + judge)
Layer 1   inner agent          fresh context per dispatch — has no
   (cc-use)                    memory of previous cycles, cannot
                               rubber-stamp known behavior
```

The split between Layer 1 (producer, fresh context) and Layer 2 (judge,
persistent context) is the **GAN-like discriminator / generator
separation** that prevents the self-certifying problem of `/goal` or
Ralph Loop. Layer 1 reports back to Layer 2; Layer 2 commits, fixes,
or escalates.

## Mechanisms (one paragraph each)

Each mechanism is summarized here; for the full procedure see the
linked reference.

- **Ratchet (monotonic progress).** Every accepted finding becomes a
  local `git commit`; every reject is a `git reset`. The branch is
  monotonically improving — borrowed from Karpathy's AutoResearch
  pattern, but for tasks without a scalar metric. Details in
  `references/design.md`.

- **Exploration vs exploitation split.** Two prompts per cycle.
  `1_explore.md` is divergent (list dimensions, sample broadly,
  populate the backlog). `2_execute.md` is convergent (work through
  the backlog, commit or escalate). Lexically-sorted files mean you
  can drop a `3_reflect.md` in to add a reflection phase without
  touching code. Details in `references/trigger.md`.

- **Async human escalation.** `escalations.md` is the channel for
  ambiguous decisions the agent can't make alone. Agent writes Open
  items with A/B/C options; human writes answers in Resolved. New
  cycles run while questions sit unanswered — the loop never blocks
  on the human. Details in `references/feedback.md`.

- **Inbox (human → agent push).** `inbox.md` is where the user nudges
  the agent: SKIP, PRIORITIZE, ADD, STOP, DIRECTION, NOTE, or plain
  natural language. Read at every cycle's explore phase. Details in
  `references/feedback.md`.

- **Trigger abstraction.** Three trigger types — `schedule` (every N
  minutes), `conditional` (poll an external state like `gh pr list`),
  `webhook` (event-driven). Same Layer 2 and Layer 1; only Layer 3
  differs. Default in examples is `schedule` with a 2-minute interval —
  see cost note below. Details in `references/trigger.md`.

- **Control signals.** `touch .paused` / `rm .paused` to pause and
  resume; `touch .stop_after_current` to gracefully stop after the
  current cycle; `pkill -f trigger.sh` + `tmux kill-session` for hard
  stop. File-level signals, no new protocol. Details in
  `references/control.md`.

- **Parallel lines via git worktree.** For several perpetuum tasks
  on the same project, use `git worktree add` so each task gets its
  own branch and directory. `_meta.md` records the worktree
  metadata. Details in `references/worktree.md`.

- **File-as-contract.** `plan.md` is agent-maintained (humans should
  route changes through `inbox.md`); `inbox.md` is human-write;
  `escalations.md` is bidirectional with the "agent writes Open,
  human writes Resolved" convention. Nothing is enforced at the
  filesystem level — it's a convention, not a lock. Details in
  `references/feedback.md`.

## Task layout

When a task is initialized:

```
<project-or-worktree>/
└── .perpetuum/
    └── <task-name>/
        ├── _meta.md             worktree/branch metadata
        ├── trigger.sh           per-task; adjusted during setup
        ├── 1_explore.md         prompt 1: plan
        ├── 2_execute.md         prompt 2: dispatch + judge + record
        ├── plan.md              agent-maintained state machine
        ├── inbox.md             human → agent
        ├── escalations.md       agent ↔ human
        ├── trigger.log
        └── state/
            └── .cycle_done_*    per-cycle sync flags (transient)
```

Any file matching `[0-9]+(\.[0-9]+)?_*.md` in the task directory is
fed to Layer 2 in lexical order, one per cycle phase. Default is 2
(`1_explore.md`, `2_execute.md`); add `3_reflect.md` for a reflection
phase, `1.5_check.md` to insert a step between, etc.

## Dependencies

Before initializing a new task, confirm:

1. **The `cc-use` skill is available in the current agent's skill
   environment.** Layer 2 uses it to dispatch Layer 1. The install
   location depends on which host agent is running; just check
   whether the current agent can resolve `cc-use`. If missing, ask
   the user whether to install it; after installing, the user may
   need to reload skills (varies by host agent — Claude Code has
   `/reload-skills`, others may need a TUI restart).

2. **`tmux` is installed locally.** Run `tmux -V`.

Don't proceed with setup if either is missing.

## Suitability gate (REQUIRED before any new init)

Not every task fits this architecture. A bad fit wastes the user's
tokens. Before creating files, judge fit with the user explicitly.

- **Strong fit**: "find more of X" / "converge toward Y" / "watch
  for Z" tasks. Dimensional structure. Per-finding independence.
- **Poor fit**: one-shot tasks; strongly linear builds; tasks needing
  synchronous human decisions; tasks shorter than ~30 minutes total.

The full suitability questionnaire and reshape guidance is in
`references/setup.md`. If a task is borderline, ask the user the
gating questions there before proceeding.

## Core invariants (do not violate)

These are the things that keep the loop honest. Don't weaken them
when adjusting prompts or scripts:

1. Every accepted finding becomes a local `git commit`.
2. `plan.md` is agent-maintained; humans route changes through
   `inbox.md`.
3. Layer 1 always runs in fresh context (per `cc-use` delegate, not a
   reused inner session within a cycle).
4. Layer 2's prompts are atomic and lexically ordered; don't fuse
   them.
5. Sync uses `.cycle_done_*` flag + tmux silence fallback + total
   timeout — all three are needed; don't drop one.

## After-setup briefing

When you finish initializing a task, walk the user through:

- How a cycle runs (trigger → explore → execute → sleep)
- What files they can edit (`inbox.md`, `escalations.md`, prompts,
  trigger config) and what to leave alone (`plan.md` is agent-owned)
- How to talk to you vs. edit files directly — both work
- Pause / resume / graceful stop / hard kill commands
- Whether to `.gitignore` `.perpetuum/`
- **Cost / rate-limit awareness** — the default 2-minute cadence is
  full throttle. Confirm budget and offer to dial it down before
  launching. Full briefing template in `references/setup.md`.

Don't skip this. A user who doesn't know they can pause / edit
`inbox.md` will `pkill` the loop in panic the first time they want
to change something.

## Language rule

The markdown files this skill generates (`plan.md`, `inbox.md`,
`escalations.md`, the two prompt files, and any text written into
them at runtime) are for the user to read.

If the user speaks any non-English language and doesn't explicitly
ask for another, generate all human-facing content (prompts, plan
items, escalation entries, status messages) in that language.

**Boundary:** this rule applies only to perpetuum's own files and
to the perpetuum ↔ human interaction. It does **not** apply to the
project's own code, code comments, commit messages, documentation,
or anything the inner agent produces as part of the actual task
work — those follow the project's existing conventions.

File names, config keys, shell variables, and scripts are always
English (cross-language stable).
