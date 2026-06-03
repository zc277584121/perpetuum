---
name: perpetuum
description: >
  Set up, supervise and control a persistent multi-layer "explore → execute →
  escalate" agent loop on a project. Use this skill whenever a user asks to
  keep an agent running on a task across sessions or days — finding bugs,
  polishing writing, distilling a style, watching feeds, scanning for gaps,
  or any task whose value grows with how many findings the agent produces.
  Also use when the user wants to inspect, pause, resume, stop, or send a new
  instruction to an already-running perpetuum task.
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
  - Glob
  - Grep
---

# perpetuum

You help the user **set up, supervise, and control** a persistent
"explore → execute → escalate" agent loop on their project. The user
describes a task; you decide if it fits, then either initialize a new
task or operate on a running one.

## Route based on the user's intent

| User wants to… | Read |
|---|---|
| Start a new perpetuum task | `references/setup.md` + skim `examples/` |
| See current status of a task | `references/status.md` |
| Pause / resume / stop / kill a running task | `references/control.md` |
| Push a new instruction in, or answer an escalation | `references/feedback.md` |
| Run several lines in parallel via git worktree | `references/worktree.md` |
| Write or adjust `trigger.sh` for a specific task | `references/trigger.md` |
| Understand why the design is the way it is | `references/design.md` |

If the user's intent is unclear, ask. Don't guess.

## Language rule

The markdown files this skill generates (`plan.md`, `inbox.md`,
`escalations.md`, the two prompt files, READMEs in `.perpetuum/<task>/`,
and any text you write *into* those files at runtime) are **for the user
to read**. Their language should match the user's.

So: if the user speaks Chinese (or any other language) and does not
explicitly ask for another, generate all human-facing content
(prompts, plan items, escalation entries, status messages) in that
language.

**Boundary:** this rule applies *only* to perpetuum's own files and to
the perpetuum ↔ human interaction. It does **not** apply to the project's
own code, code comments, commit messages, documentation, or anything the
inner agent produces *as part of the actual task work* — those follow the
project's existing conventions. If the project writes commits in English,
the inner agent writes commits in English even when the user talks to you
in Chinese.

File names, config keys, shell variables, and scripts are always English
(cross-language stable).

## Dependencies (check before init)

Before initializing a new task, confirm:

1. **`cc-use` skill is installed.** Layer 2 of the loop uses it to dispatch
   Layer 1 work. Check by looking for `~/.claude/skills/cc-use/` (or
   wherever the host agent stores skills). If missing, ask the user
   whether to install it. After install the user may need to reload skills
   — Claude Code users can try `/reload-skills`; other agents may need a
   TUI restart, follow that agent's docs.

2. **`tmux` is installed.** Run `tmux -V`. Layer 2 lives in a persistent
   tmux session.

Don't proceed with setup if either is missing.

## Suitability gate (REQUIRED before any new init)

Not every task fits this architecture. A bad fit wastes the user's tokens
and time without producing findings. Before you create files for a new
task, judge fit with the user explicitly.

### Strong fit

- "Find more of X" tasks where every finding has independent value
  (bug hunting, fuzzing, vulnerability scans, observability gap audits,
  API consistency scans, error-message polish)
- "Converge toward Y" tasks with a quantifiable or semi-quantifiable
  closeness signal (style distillation against a reference corpus,
  doc polish toward a target, configuration tuning toward a metric)
- "Watch for Z" tasks driven by external state change
  (GitHub issue/PR feeds, log alerts, file watches)
- Tasks with an obvious *dimensional* expansion (Cartesian product of
  axes the agent can sample)
- Tasks where individual findings can be independently committed

### Poor fit (do not init)

- One-shot tasks ("rewrite this function in style X") — direct agent
  invocation is better, perpetuum is overkill
- Strongly linear builds where step N depends on step N-1's decision
- Tasks that need the human to make the *very next* decision (no
  "continue with the rest while I think" surface)
- Pure aesthetic judgments with no proxy for "closer to good"
- Tasks shorter than ~30 minutes total

### When in doubt, ask the user

- "Is this a 'more is better' task, or a 'one-and-done' task?"
- "If the agent does something wrong mid-run, can you live with reverting
  that commit and moving on?"
- "Can you name the kind of question that should make the agent stop
  and ask you, vs. the kind it should just decide on its own?"
- "After running for a day, would you be OK with most findings being
  useful and a few being noise?"

Based on the answers:
- **Strong fit** → proceed to setup
- **Partial fit** → reshape the task with the user (e.g. turn "refactor X"
  into "scan X module-by-module and surface one smell per module")
- **Poor fit** → tell the user honestly and suggest an alternative (single
  agent run, `cc-use` one-off dispatch, manual review, etc.)

## Core invariants (do not violate)

Everything in perpetuum hinges on these. Don't let the user or yourself
break them when adjusting prompts or scripts.

1. **Every accepted finding becomes a git commit, locally.** This is
   the ratchet. No commit, no progress signal, no rollback handle.
   Local branch commits are fine — the user decides later whether to
   push or merge.
2. **`plan.md` is agent-maintained.** Users *can* edit it (filesystem
   doesn't lock), but the convention is they don't; they push changes
   through `inbox.md` instead. State your suggestion clearly when telling
   the user about the file.
3. **Layer 1 always runs in fresh context** (a cc-use delegate per task,
   not a persistent inner session reused across tasks within a cycle).
   This preserves exploration independence.
4. **Layer 2's two prompts are atomic and sequential.** Prompt 1 plans,
   prompt 2 executes. Don't fuse them. If you want a third phase
   (e.g. reflection), add a `3_*.md`; sequence is just lexical sort.
5. **Sync uses `.cycle_done_*` flag + tmux silence fallback + total
   timeout.** Three layers. Don't replace with a single mechanism.

## Layout when a task is initialized

```
<project>/                       ← any git repo
└── .perpetuum/
    └── <task-name>/             ← created by you during setup
        ├── _meta.md             ← worktree/branch metadata
        ├── trigger.sh           ← per-task, you adjust during setup
        ├── 1_explore.md         ← prompt 1: read history, plan
        ├── 2_execute.md         ← prompt 2: dispatch, judge, record
        ├── plan.md              ← agent-maintained state machine
        ├── inbox.md             ← human → agent channel
        ├── escalations.md       ← agent → human channel
        ├── trigger.log          ← runtime log
        └── state/
            └── .cycle_done_*    ← per-cycle sync flags
```

Optional prompts: `3_reflect.md`, `1.5_check.md`, etc. — anything
matching `[0-9]+(\.[0-9]+)?_*.md` in this directory is fed to Layer 2
in lexical order, one per cycle phase.

`_meta.md` is filled in once during setup and rarely changes. See
`references/worktree.md` for what goes in it.

## After setup: what to tell the user

When you finish initializing a task, **always walk the user through these
five things** in their language. They are launching a long-running
process; they need to know what they own and what perpetuum owns.

### 1. How the cycle runs

> Layer 3 (`trigger.sh`) wakes up on its trigger (every 40 minutes by
> default, or on a condition you configured), pastes prompt 1 into the
> middle CC TUI, waits for a done signal, then pastes prompt 2, waits
> again, sleeps. That's one cycle. You configured it for N cycles total.

### 2. What they can edit, and how

| File | Edit how |
|---|---|
| `inbox.md` | Yes — write a one-liner under `## 待消化` whenever you want to nudge it. Agent reads it at the start of each cycle. |
| `escalations.md` | Yes — when agent has asked you something, write your answer under `## 已解决`. |
| `1_explore.md` / `2_execute.md` | Yes — these are *your* prompt templates. Adjust phrasing, add constraints, the next cycle picks it up. |
| `trigger.sh` | Yes for trigger type / interval / max iterations. |
| `plan.md` | **Avoid** — it's the agent's state machine. To change priorities or skip todos, use `inbox.md`. The system won't crash if you edit it, but format drift may confuse the next cycle. |
| `_meta.md` | Static once setup finishes. |

### 3. Talk to me or edit files — both work

The user can either:
- **Talk to you** in the host agent: "perpetuum, pause the testing task"
  or "tell the adversarial task to skip postgres". You translate to
  the file operations below.
- **Edit files directly** in their editor / shell — same effect.

Make this explicit. Some users prefer one, some the other. Both are
first-class.

### 4. Pause / resume / stop

```bash
touch .perpetuum/<task>/.paused                  # pause after current cycle
rm .perpetuum/<task>/.paused                     # resume
touch .perpetuum/<task>/.stop_after_current      # graceful stop
pkill -f trigger.sh                              # hard stop
tmux kill-session -t middle-<task>               # also kill the TUI
```

When the user says "暂停" / "pause" / "停一下", touch `.paused`. When they
say "继续" / "resume", remove it. When they say "结束" / "stop after this
one" / "stop gracefully", touch `.stop_after_current`. See
`references/control.md` for full detail.

### 5. Don't put `.perpetuum/` in git unless they want it

After init, suggest:

```bash
echo '.perpetuum/' >> .gitignore
```

…unless the user wants the plan / history committed to the repo
(legitimate choice for team review). Their call.

### 6. Cost / rate-limit awareness — say this out loud

The default `SLEEP_BETWEEN_CYCLES` in the schedule-type examples is
**2 minutes**. This means after a cycle finishes, the next one starts
2 minutes later. With `MAX_ITER=20` you can blow through your full
20 cycles in a few hours — and the inner-agent dispatches that
happen each cycle are the dominant token cost.

**Before they launch, ask the user:**
- Do they have token budget / API quota for ~N cycles at this cadence?
  (Where N is `MAX_ITER`, and one cycle typically costs O(several inner
  agent dispatches × the complexity of each).)
- Are they on a usage-based plan where cost matters, or a flat plan
  where rate limits matter more?
- Are they OK leaving it running while they sleep, or do they want
  to babysit the first 2–3 cycles?

**Tell them how to dial down if needed:**
- Increase `SLEEP_BETWEEN_CYCLES` (e.g. 1800 = 30 min, 3600 = 1 hour)
- Decrease `MAX_ITER`
- Switch to a conditional trigger type (only fires on real external
  events; see `references/trigger.md`)
- Run a 1-iteration trial first by temporarily setting `MAX_ITER=1`

The default of 2 min assumes the user *wants* full throttle. If they
hesitate when you mention cost, default to 20 minutes or longer.

## Things you should not do

- Don't build a real config schema. Configuration is shell variables
  at the top of `trigger.sh`, file signals, and lexical file ordering.
  Adding YAML/TOML config is over-engineering.
- Don't add a `companion: true` flag or any awareness of whether a Layer
  4 agent is watching. The skill is layer-4-agnostic by design.
- Don't write persistent test code, persistent benchmark code, or any
  "throwaway artifact left behind" for the testing/exploration use cases —
  if the user's task is exploratory, Layer 1 should do ephemeral CLI/TUI
  operations and record observations in `plan.md`. Persistent test files
  signal "already covered" to the next cycle and shrink exploration.
- Don't invent a new memory format (vector DB, embedding cache, structured
  log). Markdown + git + tmux capture-pane is the entire memory system.
- Don't promise the user it'll run forever. The point of "perpetuum" is
  ironic — what it actually gives you is "keep going across calendar time
  without losing state".
