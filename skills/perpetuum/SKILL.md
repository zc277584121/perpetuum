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

**What ships here is a framework, not fixed source code.** The
architecture (three layers, two prompts, three trigger families,
file-as-contract, async escalation) is what's fixed and what makes the
loop reliable. Everything else — the wording in `prompts/1_explore.md`
and `prompts/2_execute.md`, the bash in `trigger.sh`, the classification
logic the middle agent applies, even the exact structure of `plan.md` /
`inbox.md` / `escalations.md` — are **templates to adapt to the user's
specific task, domain, project, and language**. When you set up a new
task with the user, treat the files copied from `examples/` as starting
points and rewrite them to fit. Don't treat them as immutable scripts.
This is what keeps a small skill flexible enough to handle adversarial
testing, ML hyperparameter sweeps, PR review, migrations, and style
polish without code changes.

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
| See/watch a task visually, in a browser | `references/dashboard.md` — **ask before setting it up**, it's optional |

## How it works (architecture in one screen)

```
Layer 4   you + host agent     monitor + relay (optional)
   ↓
Layer 3   trigger.sh           persistent scheduler: start fresh Layer 2,
   ↓                                       paste prompts, wait, clean up
Layer 2   middle agent (tmux)  fresh per cycle; judge + dispatch:
   ↕                                       1_explore.md  (plan)
                                           2_execute.md  (dispatch + judge)
Layer 1   inner agent          fresh context per dispatch — has no
   (cc-use)                    memory of previous cycles, cannot
                               rubber-stamp known behavior
```

The split between Layer 1 (producer, fresh context) and Layer 2 (judge,
fresh-per-cycle context) is the **GAN-like discriminator / generator
separation** that prevents the self-certifying problem of `/goal` or
Ralph Loop. Layer 1 reports back to Layer 2; Layer 2 commits, fixes,
or escalates. Layer 3 is the persistent scheduler; durable memory lives
in files and git, not in a long-lived Layer 2 TUI conversation.

**Fresh context is not the same as no information.** Layer 1 has no
memory of *previous cycles' conversation* — that's what prevents
self-certification. But the dispatch prompt for *this* task can and
should carry whatever this one bounded piece of work needs: relevant
file paths, a specific instruction, prior decisions from
`escalations.md` or `plan.md` that constrain this item. Layer 2 rebuilds
the accumulated picture by re-reading those files at the start of each
cycle; it's responsible for writing the necessary slice of it into each
dispatch's task text. Withholding context isn't "more fresh" — it just
makes Layer 1 rediscover the same things every cycle, or miss a
constraint that was already decided.

## Mechanisms (one paragraph each)

Each mechanism is summarized here; for the full procedure see the
linked reference.

- **Ratchet (monotonic progress).** The middle agent judges each
  Layer-1 proposal *before* committing; rejected proposals never
  become commits. Accepted ones land as a local `git commit`, giving
  the branch a clean append-only log that doubles as the durability
  mechanism across sessions. Same family of idea as Karpathy's
  AutoResearch ratchet, with the judge slightly earlier in the loop.
  Details in `references/design.md`.

- **Exploration vs exploitation split.** Two prompts per cycle.
  `prompts/1_explore.md` is divergent (list dimensions, sample broadly,
  populate the backlog). `prompts/2_execute.md` is convergent (work through
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
  `webhook` (event-driven). They share the same per-cycle Layer 2 and
  Layer 1 contract; only Layer 3's wake-up condition differs. Default in
  examples is `schedule` with a 2-minute interval — see cost note below.
  Details in `references/trigger.md`.

- **Control signals.** `touch .paused` / `rm .paused` to pause and
  resume; `touch .stop_after_current` to gracefully stop after the
  current cycle; `pkill -f trigger.sh` + `tmux kill-session` for hard
  stop. Layer 2 is normally killed after each cycle, but cleanup commands
  still include the fixed middle tmux session name for stale sessions.
  File-level signals, no new protocol. Details in `references/control.md`.

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
        ├── prompts/
        │   ├── 1_explore.md     prompt 1: plan
        │   └── 2_execute.md     prompt 2: dispatch + judge + record
        ├── plan.md              agent-maintained state machine
        ├── inbox.md             human → agent
        ├── escalations.md       agent ↔ human
        ├── trigger.log
        └── state/
            └── .cycle_done_*    per-cycle sync flags (transient)
```

Any file matching `prompts/[0-9]+(\.[0-9]+)?_*.md` is fed to Layer 2
in lexical order, one per cycle phase. Default is 2
(`prompts/1_explore.md`, `prompts/2_execute.md`); add
`prompts/3_reflect.md` for a reflection phase,
`prompts/1.5_check.md` to insert a step between, etc.

Keeping prompts in a subdirectory separates editable templates from
runtime state (`plan.md` / `inbox.md` / `escalations.md`) — users can
edit the `prompts/` dir freely without mixing prompt edits and state
edits.

### What the state files actually look like

Use these as templates when you generate or judge file content. Match
the structure; render the content in the user's language per the
language rule below.

`plan.md` — agent-maintained:

```markdown
## Pending
- [ ] [auth] test expired token refresh
- [ ] [parse] malformed XML input

## Done
- [x] (cycle 3) [auth] login flow
  - operation: cli login --user x
  - observed: 200 + valid JWT
  - status: PASS
- [x] (cycle 5) [parse] xss in error envelope
  - status: [FIXED] commit:abc1234
```

`inbox.md` — user writes; agent reads and absorbs every cycle:

```markdown
## Pending
- SKIP: postgres backend, not shipping
- PRIORITIZE: PR #123 first
- NOTE: I'm OOO Friday, no urgent escalations

## Processed
- (cycle 6) SKIP applied — removed 4 postgres items from plan.md
```

`escalations.md` — agent writes `## Open` items; user fills
`## Resolved`:

```markdown
## Open
### (cycle 4) off-by-one in --range flag
A: 1-based inclusive (matches head/tail/sed)
B: 0-based half-open (matches array semantics in most languages)
C: leave both, document the discrepancy

## Resolved
```

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
  middle agent (Layer 2) runs in a tmux session that Layer 3 recreates
  for each cycle, using a fixed per-task session name.

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

Underneath these two heuristics is an internal five-dimension
checklist (goal narrowness, judgeable signal, step granularity,
error tolerance, time horizon — full detail in
`references/setup.md`). **Don't recite this checklist to the user.**
Instead:

- Check the user's description against all five silently.
- Ask only about dimensions still unresolved, and only where the
  answer would actually change the setup (trigger type, cadence,
  escalation policy, which example to start from). Don't ask a
  dimension just to have asked it.
- Ask one at a time, in your own words, fit to the user's task and
  language. Wait for the answer before asking the next — never queue
  up several questions in one message.
- If the user's first message already answers a dimension clearly,
  don't ask it again.

If the task is still borderline after that, reshape it with the user
(e.g. turn "refactor X" into "scan X module-by-module and surface one
smell per module"), or recommend a non-perpetuum approach (single
agent run, one-off `cc-use` dispatch). Checklist detail in
`references/setup.md`.

### 3. Pick an example and create the task directory

Look at `examples/` for the closest task shape and copy that
directory's contents to `<project>/.perpetuum/<task-name>/`. Then
customize:

- `prompts/1_explore.md` — replace generic dimension hints with this
  project's actual axes; use the user's language
- `prompts/2_execute.md` — set the project's absolute path; adjust
  commit-style and classification policy to the project. Dispatching
  to Layer 1 is a hard requirement: every dispatch must use a fresh,
  no-memory inner session. With the current `cc-use` helper, that means
  requiring `--replace` on every `delegate` call. If `cc-use` changes
  its fresh-start mechanism later, update this instruction at the same
  time; do not weaken it to a best-effort request. If a specific extra
  skill (beyond `cc-use`) would materially help this task, note that
  too — ask adaptively, see `references/setup.md` → "Recommending extra
  skills"
- `trigger.sh` — set `MIDDLE_SESSION` to something unique for this task
  line, adjust `MAX_ITER`, decide trigger type (schedule / conditional /
  webhook). The fixed name is reused across cycles, but Layer 3 kills the
  session after each cycle and starts it fresh for the next one. If you
  need multiple independent trigger families on the same project, either
  route them through one queue/drainer or give them distinct task
  directories/worktrees and distinct `MIDDLE_SESSION` names; do not let
  multiple schedulers write into the same middle TUI. The script also
  reads an `AGENT_CMD` env var: default is Claude Code, but users on
  Codex / Cursor / etc. can override before launch (e.g.
  `AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox"` or the
  safer `AGENT_CMD="codex --full-auto"`). Mention this explicitly to
  non-Claude-Code users.
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

## Known Codex compatibility quirks (already handled)

For Codex CLI users, two tmux/TUI quirks are handled by the default
`trigger.sh`. No user action needed; documented here so you know
what the extra send-key lines are for:

1. **Codex tmux "Enter doesn't commit" bug**
   ([openai/codex#12645](https://github.com/openai/codex/issues/12645)).
   `send_prompt` uses the same five-step sequence cc-use uses
   (`C-u` → `paste-buffer -d` → `Enter` → `C-m` → `Enter`).

2. **"Create a plan?" popup on complex prompts.** Codex pops this on
   long planning-style prompts (our `1_explore.md` triggers it).
   `send_prompt` detects Codex via `$AGENT_CMD` and sends `Escape`
   after paste to dismiss it.

The execute prompts in `examples/` instruct the middle agent to
**escalate** any cc-use failure rather than work around it locally —
surface it as a blocked-on-environment item in `escalations.md` and
stop the cycle, do not fake a fresh inner context within your own
conversation.

## Core invariants (do not violate)

These are the things that keep the loop honest. Don't weaken them
when adjusting prompts or scripts:

1. Every accepted finding becomes a local `git commit`.
2. `plan.md` is agent-maintained; humans route changes through
   `inbox.md`.
3. Layer 1 always runs in fresh context. Every dispatch to Layer 1
   must create a fresh, no-memory inner session — never one reused
   from a prior cycle, which would silently give Layer 1 memory of
   past cycles. With the current `cc-use` helper, every `delegate`
   call must use `--replace`; if `cc-use` changes its fresh-start
   mechanism later, update the perpetuum prompts and setup docs in the
   same change. Do not leave this as a soft requirement that Layer 2
   can forget to enforce.
4. Layer 2 is fresh per cycle. Layer 3 owns the fixed middle tmux session
   name, starts it at cycle beginning, sends the phase prompts, and kills
   it after the cycle. Persistent state belongs in `plan.md`, `inbox.md`,
   `escalations.md`, artifacts, and git.
5. Layer 2's prompts are atomic and lexically ordered; don't fuse
   them.
6. Sync uses `.cycle_done_*` flag + tmux silence fallback + total
   timeout — all three are needed; don't drop one.

## After-setup briefing

After launching, walk the user through these in their language. The
user just handed a coding agent the keys to their codebase; they need
to know how to drive.

- **How a cycle runs.** Trigger fires → Layer 3 starts a fresh middle
  tmux session with this task's fixed session name → middle agent reads
  `plan.md` / `inbox.md` → prompt 1 plans, prompt 2 dispatches via
  `cc-use` and judges results → commits, escalates, or records → Layer 3
  kills the middle session, sleeps, then repeats. The state that carries
  forward lives in files and git.

- **What they can edit, and how.**
  - `inbox.md` — yes, anytime, write a one-liner under `## Pending`
  - `escalations.md` — yes, write answers in `## Resolved`
  - `prompts/1_explore.md` / `prompts/2_execute.md` — yes, the next cycle picks up
    edits
  - `trigger.sh` — yes for cadence / `MAX_ITER`
  - `plan.md` — **avoid**, agent-owned; route changes through
    `inbox.md`
  - `_meta.md` — static after setup

- **Talk to you or edit files — both work.** They can say things in
  natural language to the host agent and you translate to file
  operations; or they can edit files directly in their editor. Make
  both paths explicit; some users prefer one, some the other.

  Translation table for common natural-language requests (English
  phrasings shown — map equivalent intent in any user language to the
  same operation):

  | User intent | You do |
  |---|---|
  | "pause" / "stop for now" / "hold on" | `touch .perpetuum/<task>/.paused` |
  | "resume" / "keep going" / "start again" | `rm .perpetuum/<task>/.paused` |
  | "stop gracefully" / "finish this cycle and stop" | `touch .perpetuum/<task>/.stop_after_current` |
  | "kill it" / "force stop" / "just stop" | `pkill -f trigger.sh ; tmux kill-session -t middle-<task>` |
  | "skip X" / "don't bother with X" | append `SKIP: X` to `inbox.md` `## Pending` |
  | "prioritize Y" / "Y first" | append `PRIORITIZE: Y` to `inbox.md` |
  | "add a test/scan for Z" | append `ADD: Z` to `inbox.md` |
  | "change direction to W" | append `DIRECTION: W` to `inbox.md` |
  | "for question X, pick option A" | edit the matching `escalations.md` Open item, add the answer, move to `## Resolved` |
  | "what's the status?" / "what's it doing?" | tail `trigger.log` + summarize `plan.md` Pending/Done counts + list any unresolved escalations |

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
