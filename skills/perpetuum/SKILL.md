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

## Setting up a new task

Setup is the longest interaction this skill has with the user. Don't
rush it — a mis-launched perpetuum task wastes hours and tokens. Walk
the user through the steps below. Detail for each step lives in
`references/setup.md`; this section is the overview.

### 1. Prerequisites — confirm both are present

These are the only two things the skill depends on. Don't proceed if
either is missing.

- **`cc-use` skill** must be available in whichever skill environment
  the current host agent uses. Layer 2 of perpetuum dispatches every
  unit of work to a fresh inner agent via `cc-use`. Without it, there
  is no Layer 1.

  Install it the same way perpetuum was installed:

  ```bash
  npx skills add zc277584121/cc-use --all -g
  ```

  After installing, the user may need to reload skills before the
  current agent can see it. The exact command varies by host agent —
  Claude Code has `/reload-skills`; other agents may need a TUI
  restart. Follow that agent's docs.

- **`tmux`** must be installed locally. Verify with `tmux -V`. The
  middle agent (Layer 2) lives in a persistent tmux session for the
  duration of the task.

If `cc-use` is missing, ask the user whether to install it. If `tmux`
is missing, point them to their package manager and stop — perpetuum
cannot run without it.

### 2. Suitability gate — judge fit with the user

Not every task fits this architecture. A bad fit wastes the user's
tokens. Don't skip this step.

- **Strong fit**: "find more of X" / "converge toward Y" / "watch
  for Z" tasks. Dimensional structure. Per-finding independence.
- **Poor fit**: one-shot tasks; strongly linear builds; tasks needing
  synchronous human decisions; tasks shorter than ~30 minutes total.

If the task is borderline, reshape it with the user (e.g. turn
"refactor X" into "scan X module-by-module and surface one smell per
module"), or recommend a non-perpetuum approach (single agent run,
one-off `cc-use` dispatch). Full questionnaire in
`references/setup.md`.

### 3. Pick an example and create the task directory

Look at `examples/` for the closest task shape and copy that
directory's contents to `<project>/.perpetuum/<task-name>/`. Then
customize:

- `1_explore.md` — replace generic dimension hints with this
  project's actual axes; use the user's language
- `2_execute.md` — set the `--project` absolute path; adjust
  commit-style and classification policy to the project
- `trigger.sh` — set `MIDDLE_SESSION` to something unique, adjust
  `MAX_ITER`, decide trigger type (schedule / conditional / webhook)
- `_meta.md` — fill in worktree path, branch, parent repo, merge
  target
- Leave `plan.md`, `inbox.md`, `escalations.md` empty (their skeletons
  are already in the example)
- `chmod +x trigger.sh`

For parallel tasks on the same project, set up via `git worktree`
first — see `references/worktree.md`.

### 4. Cost / cadence confirmation — say this out loud

The default `SLEEP_BETWEEN_CYCLES` in schedule-type examples is
**2 minutes**, intended for full throttle. With `MAX_ITER=20`, the
loop burns through all 20 cycles in a few hours; each cycle costs O(a
few inner-agent dispatches via `cc-use`).

Before launching, ask the user:

- Do they have token budget for ~MAX_ITER cycles at this cadence?
- Are they on a usage-based plan (cost matters) or a flat plan (rate
  limits matter)?
- Will they babysit the first few cycles, or launch and walk away?

If they hesitate: bump `SLEEP_BETWEEN_CYCLES` (1800 = 30 min, 3600 =
1 hour), reduce `MAX_ITER`, or switch to the `conditional` trigger
pattern (only fires when there's real new work).

Don't skip this step. A "$X overnight" surprise is the easiest way to
make the user pull the plug on perpetuum forever.

### 5. Optional first-cycle trial

For first-time users, suggest a trial with `MAX_ITER=1`:

```bash
sed -i.bak 's/^MAX_ITER=.*/MAX_ITER=1/' .perpetuum/<task>/trigger.sh
.perpetuum/<task>/trigger.sh        # foreground, watch one cycle
mv .perpetuum/<task>/trigger.sh.bak .perpetuum/<task>/trigger.sh
```

Inspect `plan.md`, `escalations.md`, and `git log` after the trial.
Adjust prompts if anything went sideways before running 20 cycles.

### 6. Suggest `.gitignore` and launch

```bash
echo '.perpetuum/' >> <project>/.gitignore   # unless the user wants state in git
nohup .perpetuum/<task>/trigger.sh > /dev/null 2>&1 &
```

Or hand the launch command to the user to start when they're ready.

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

After launching, walk the user through these in their language. The
user just handed a coding agent the keys to their codebase; they need
to know how to drive.

- **How a cycle runs.** Trigger fires → middle agent reads `plan.md`
  / `inbox.md` → pastes prompt 1 to plan, then prompt 2 to dispatch
  via `cc-use` → judges each result → commits, escalates, or
  records. Then sleep, repeat. The whole thing keeps going across
  cycles, restarts, and your absence.

- **What they can edit, and how.**
  - `inbox.md` — yes, anytime, write a one-liner under `## Pending`
  - `escalations.md` — yes, write answers in `## Resolved`
  - `1_explore.md` / `2_execute.md` — yes, the next cycle picks up
    edits
  - `trigger.sh` — yes for cadence / `MAX_ITER`
  - `plan.md` — **avoid**, agent-owned; route changes through
    `inbox.md`
  - `_meta.md` — static after setup

- **Talk to you or edit files — both work.** They can say "perpetuum,
  pause the testing task" / "skip postgres" / "PR #123 is urgent" to
  the host agent and you translate to file operations; or they can
  edit files directly in their editor. Make this explicit; some users
  prefer one, some the other.

- **Pause / resume / stop / kill.** File signals:
  ```
  touch .paused                  # pause after current cycle
  rm .paused                     # resume
  touch .stop_after_current      # graceful stop
  pkill -f trigger.sh ; tmux kill-session -t middle-<task>   # hard
  ```

- **Reset the cost expectation.** Reiterate what `SLEEP_BETWEEN_CYCLES`
  and `MAX_ITER` are set to and what that implies for spend over the
  next N hours. The cost conversation in step 4 happened before they
  knew the system; remind them now.

Don't skip the briefing. A user who doesn't know they can pause and
edit `inbox.md` will `pkill` the loop in panic the first time they
want to change anything.

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
