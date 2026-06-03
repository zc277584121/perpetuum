# perpetuum

## Why your `/goal` runs go nowhere

If you've tried Claude Code's `/goal`, Codex's equivalent, or a Ralph Loop,
you've probably hit one of these:

| Failure you've seen | Why it happens | What `perpetuum` does |
|---|---|---|
| Agent self-certifies "done" | Same context produces and judges | Three layers: middle agent judges, inner agent (fresh `cc-use` dispatch) produces — they never share context |
| Silent regression | No ratchet to roll back bad steps | Every accepted finding is a local `git commit`; reverts never enter history |
| Context rot after a few hours | All state lives in conversation | State lives in markdown files; middle agent re-reads them at every cycle start |
| Human-in-loop is a hard wall | Ambiguity → agent stops and waits | Async `escalations.md` — loop keeps running on everything else while you answer offline |
| Only "every N minutes" triggers | No trigger abstraction | Three trigger types: schedule, conditional (poll an external state), webhook |
| Plan and execute entangled | One prompt does both | Two prompts per cycle (`1_explore.md`, `2_execute.md`), lexically sorted — add `3_reflect.md` if you want a reflection phase |

`perpetuum` (Latin for "perpetual motion" — the name is ironic, but the
state continuity is real) is the combination of these mechanisms. It is
a thin skill, not a framework: ~50 lines of shell, a few markdown files,
git as the ratchet, tmux as the runtime. You can fork it and modify it
in an afternoon.

## Quick Start

```bash
npx skills add zc277584121/perpetuum --all -g
```

Then in any project, ask your coding agent:

> Use perpetuum to run continuous adversarial testing on this project
> for the next couple of days.

The skill walks you through a suitability gate (is this actually a task
that benefits from a persistent loop?), picks the closest example,
customizes the prompts and trigger for your specific case, confirms the
cost/cadence with you, and launches.

## Installation

Install using [`npx skills`](https://skills.sh).

### Install to all supported agents

```bash
# Global — available in all projects, all supported agents
npx skills add zc277584121/perpetuum --all -g

# Project-level — current project only, all supported agents
npx skills add zc277584121/perpetuum --all
```

### Install to a specific agent

```bash
npx skills add zc277584121/perpetuum -a claude-code -g
npx skills add zc277584121/perpetuum -a codex -g
npx skills add zc277584121/perpetuum -a cursor -g
```

Other supported agents include `windsurf`, `github-copilot`, `cline`,
`roo`, `gemini-cli`, `goose`, `kilo`, `augment`, `opencode`, and
[40+ more](https://skills.sh).

### Dependency: `cc-use`

`perpetuum` requires the [`cc-use`](https://github.com/zc277584121/cc-use)
skill — Layer 2 uses it to dispatch every unit of work to a fresh
inner agent. The skill checks at init time and prompts you if missing:

```bash
npx skills add zc277584121/cc-use --all -g
```

You also need `tmux` and `git` locally.

## Updating

```bash
npx skills check       # what's stale?
npx skills update      # update everything globally installed
```

## Architecture

```
                ┌─────────────────────────────────────────────────────────┐
                │ Layer 4  YOU + host coding agent (Claude Code / Codex)  │
                │                                                          │
                │  YOU:  "Use perpetuum to find bugs for 2 days"           │
                │  agent: walks you through setup, then monitors,          │
                │         relays your natural-language nudges as files     │
                │  (optional — you can interact with files directly)       │
                └─────────────────────────────┬───────────────────────────┘
                                              │ spawns
                                              ▼
                ┌─────────────────────────────────────────────────────────┐
                │ Layer 3  trigger.sh — the dumb heartbeat                │
                │                                                          │
                │  loop until MAX_ITER or .stop_after_current:             │
                │    check .paused (block while present)                   │
                │    paste 1_explore.md  → wait .cycle_done_flag           │
                │    paste 2_execute.md  → wait .cycle_done_flag           │
                │    sleep SLEEP_BETWEEN_CYCLES (default 2 min)            │
                │                                                          │
                │  trigger types:   schedule  |  conditional  |  webhook   │
                │                   (every N) (poll gh, etc) (event-driven)│
                └─────────────────────────────┬───────────────────────────┘
                                              │ pastes prompt text
                                              ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ Layer 2  Middle agent — persistent CC TUI inside tmux                       │
 │                                                                              │
 │  ┌─ phase 1: EXPLORE (read 1_explore.md) ─────────────────────────────┐    │
 │  │  read plan.md ──► know what's done                                  │    │
 │  │  read inbox.md ──► absorb human nudges, move to ## Processed        │    │
 │  │  read escalations.md ## Resolved ──► absorb answered questions      │    │
 │  │  decide dimensions to sample (cartesian product, breadth vs depth)  │    │
 │  │  append items to plan.md ## Pending                                 │    │
 │  └────────────────────────────────────────────────────────────────────┘    │
 │                                                                              │
 │  ┌─ phase 2: EXECUTE (read 2_execute.md) ─────────────────────────────┐    │
 │  │  for each Pending item:                                              │    │
 │  │     cc-use delegate ──────────────────────► Layer 1 (one at a time) │    │
 │  │     judge inner agent's report:                                      │    │
 │  │        PASS    → record to plan.md ## Done                           │    │
 │  │        BUG     → 2nd dispatch to fix; commit; ratchet ↑              │    │
 │  │        AMBIG   → write to escalations.md ## Open (async, no block)  │    │
 │  │        FALSE+  → reshape task, re-dispatch                           │    │
 │  └────────────────────────────────────────────────────────────────────┘    │
 └────────────────────────────────────────────────┬───────────────────────────┘
                                                  │ cc-use delegate
                                                  ▼
 ┌────────────────────────────────────────────────────────────────────────────┐
 │ Layer 1  Inner agent — fresh CC, no priors                                  │
 │                                                                              │
 │  prompt: "Test that `mycli add --no-upload` produces the same searchable   │
 │           results as `--upload` on the same machine. Try real commands,    │
 │           report what you observed."                                         │
 │                                                                              │
 │  runs commands → observes outputs → reports back to middle.                  │
 │  cannot see what was tested before → cannot rubber-stamp known behavior.    │
 └────────────────────────────────────────────────────────────────────────────┘

 ╔════════════════════════════════════════════════════════════════════════════╗
 ║  .perpetuum/<task>/  —  state and contracts, all in markdown + git           ║
 ╠════════════════════════════════════════════════════════════════════════════╣
 ║                                                                              ║
 ║  plan.md              agent writes      inbox.md           YOU write         ║
 ║  ────────────────                       ─────────────                        ║
 ║  ## Pending                              ## Pending                          ║
 ║  - [ ] [auth] test expired token         - SKIP: pg backend, not shipping    ║
 ║  - [ ] [parse] malformed XML             - PRIORITIZE: PR #123 first         ║
 ║                                          - NOTE: I'm OOO Friday              ║
 ║  ## Done                                                                     ║
 ║  - [x] (c3) [auth] login flow            ## Processed                        ║
 ║    - operation: cli login --user x        (agent moves items here once       ║
 ║    - observed: 200 + valid JWT             absorbed into plan)               ║
 ║    - status: PASS                                                            ║
 ║  - [x] (c5) [parse] xss in error envelope                                    ║
 ║    - status: [FIXED] commit:abc1234     escalations.md   agent writes ↑      ║
 ║                                          ──────────────  YOU answer ↓        ║
 ║                                          ## Open                             ║
 ║  ──────────────                          ### (c4) off-by-one in --range      ║
 ║  signals (touch to set, rm to clear):       A: 1-based, B: 0-based-half,    ║
 ║    .paused                                  C: leave (document)              ║
 ║    .stop_after_current                                                       ║
 ║                                          ## Resolved                         ║
 ║  state/.cycle_done_*  (transient sync     (YOU move items here with answer  ║
 ║                        between Layer 2     once decided)                     ║
 ║                        and Layer 3)                                          ║
 ║                                                                              ║
 ║  ──────────────                                                              ║
 ║  trigger.sh    1_explore.md    2_execute.md    _meta.md    trigger.log      ║
 ║  (per task)    (prompt 1)      (prompt 2)      (set once)  (Layer 3 logs)   ║
 ╚════════════════════════════════════════════════════════════════════════════╝
```

Everything is files. State, memory, signals, history, human input — all
markdown + git + tmux + a couple of `touch` flags. No vector DB, no
framework lock-in, no daemon, no agent SDK.

## Using It

After installation, perpetuum is a normal skill. From your coding
agent's TUI, name it explicitly:

```text
Use perpetuum to watch this repo's GitHub issues and triage new ones
every hour. I'll review escalations whenever I get to them.
```

```text
Use perpetuum to iteratively polish this draft article toward Karpathy's
writing style. I've put his articles in target_corpus/.
```

```text
Use perpetuum to keep finding observability gaps in the worker module
for ~20 cycles, then stop and let me review.
```

The skill picks the closest example from
[`examples/`](skills/perpetuum/examples/) (currently:
`adversarial-testing`, `github-watcher`, `style-distill`,
`article-polish`, `observability-gap`), customizes the prompts and
`trigger.sh` for your specific task, walks through a cost/cadence
check, then launches.

### While it's running

Three channels of interaction. Use whichever is easiest:

| You want to… | Do this |
|---|---|
| Nudge the agent ("focus on X this week", "skip Y", "PR #123 is urgent") | Append a line to `inbox.md` under `## Pending` |
| Answer a question the agent asked | Edit the item in `escalations.md`, add your answer, move to `## Resolved` |
| See what's happening right now | `tail -f .perpetuum/<task>/trigger.log` or `tmux attach -t middle-<task> -r` (read-only) |
| Pause until you've reviewed | `touch .perpetuum/<task>/.paused` |
| Resume | `rm .perpetuum/<task>/.paused` |
| Stop gracefully after current cycle | `touch .perpetuum/<task>/.stop_after_current` |
| Kill hard | `pkill -f trigger.sh; tmux kill-session -t middle-<task>` |

Or just tell your host agent: "perpetuum, pause the testing task" /
"resume" / "skip the postgres tests". It translates to the file
operations.

## Philosophy

`perpetuum` is built from eight ideas. Individually none is new. The
combination is what makes the loop survive long runs.

1. **Discriminator / Generator separation** (from GANs) — Layer 2
   judges, Layer 1 generates, they never share context.
2. **Monotonic ratchet** — every Done becomes a commit; every reject
   never enters history. `git reset` is the rollback.
3. **Three-layer architecture** (stupid → smart → stupid) — heartbeat
   at the top, intelligence in the middle, focused execution at the
   bottom.
4. **Exploration vs Exploitation split** — two prompts, one per mental
   mode. Fused, they confuse each other.
5. **File-based persistent memory** — plan / inbox / escalations + git
   log is the entire memory system. Survives sessions, reboots, restarts.
6. **Asynchronous human escalation** — escalations never block the
   loop. New cycles still run while the human is offline.
7. **Trigger abstraction** — schedule, conditional, webhook are all
   valid Layer 3 implementations. Layers 2 and 1 don't care.
8. **File-as-contract** — who can edit which file is a convention,
   not enforcement. Cleaner than role-based access control.

Removing any one of these breaks something. See
[`skills/perpetuum/references/design.md`](skills/perpetuum/references/design.md)
for the long-form rationale.

## Comparison with related projects

| Project | disc/gen split | ratchet | multi-layer | explore/exploit split | persistent memory | async human | trigger abstraction | file contract |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Claude Code [`/goal`](https://code.claude.com/docs/en/goal) | ⚠ same-context Haiku judge | ✗ | ✗ | ✗ | ✗ session-bound | ✗ blocks | ✗ schedule only | ✗ |
| Codex [`/goal`](https://github.com/openai/codex) | ✗ | ✗ | ✗ | ✗ | △ thread store | ✗ blocks | ✗ schedule only | ✗ |
| [Ralph Loop](https://ghuntley.com/loop/) | ✗ | ✗ | ✗ | ✗ | △ files | ✗ blocks | ✗ `while true` | ✗ |
| [`recursive-improve`](https://github.com/kayba-ai/recursive-improve) | ✗ | ✓ | ✗ | ✗ | △ | ✗ | ✗ | ✗ |
| [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) | ✗ frozen evaluator | ✓✓ | ✗ | ✗ | ✓ | ✗ | ✗ schedule | ✓✓ |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | ✗ self-modifying | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [EvoSkills](https://arxiv.org/abs/2604.01687) | ✗ | ✓ | ✗ | △ | △ | ✗ | ✗ | △ |
| nuwa-skill / [persona](https://github.com/migueldeguzman/persona) | ✗ | ✗ | ✗ | ✗ | △ prompt-level | ✗ | ✗ | ✗ |
| **perpetuum** (this) | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ |

Each of the other projects is deeper than `perpetuum` on some single
axis — Karpathy's contract is more elegant for problems with a scalar
metric, Darwin Gödel modifies its own model code, EvoSkills evolves
multi-file skill packages. `perpetuum`'s contribution is the combination
none of the others combine — especially the three axes most relevant
to "keep running across days":  **async human escalation**,
**trigger abstraction**, and **explore/exploit split**.

## License

MIT — see [LICENSE](LICENSE).
