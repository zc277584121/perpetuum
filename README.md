# perpetuum ♾️

> A perpetual-motion engine for coding agents — production-grade,
> not a thought experiment.

## 🛑 Why your `/goal` runs go nowhere

You've probably tried `/goal` in Claude Code or Codex, or wired up a
Ralph Loop. What happens, every time: either it runs for a few minutes
and just stops, or it drifts off the main thread and keeps needing you
to step in for decisions.

That's not perpetual. That's just "unattended for 20 minutes."

`perpetuum` is what lets your coding agent **actually keep running —
truly, perpetually, until you tell it to stop.** It works while you
sleep, while you're at lunch, while you're on vacation. It needs no
synchronous human attention.

Think of it as letting your coding agent moonlight as your night-shift
coworker. You hand it a project, go to bed, come back to a stack of
commits and a short list of "hey, you need to decide this one" notes.
**Day after day, indefinitely** — never interrupted, never blocking on
your reply. Like a steady, diligent collaborator who just keeps working.

The specific things that go wrong with `/goal` and Ralph-style loops —
and how `perpetuum` fixes each:

| What you've seen | Why it happens | What `perpetuum` does |
|---|---|---|
| ⏱️ Runs 20 min, the agent declares "task complete", and stops — you wanted overnight | Single-session loop where the same context both produces and judges; the agent **self-certifies** "done" and there's no continuation mechanism | **GAN-like three-layer split** (middle judges, fresh inner via `cc-use` produces — no shared context, no self-certifying) + **trigger abstraction** (schedule / conditional / webhook) keeps the loop alive across cycles, restarts, days |
| 🪨 Makes bad calls, drifts off the main thread, or stalls waiting for you on every ambiguity | When unsure, the agent has only three options: guess wrong, wander off-track, or block on you | **Async escalation channel** — `escalations.md` surfaces ambiguous decisions with A/B/C options instead of guessing or stalling; the loop keeps progressing on everything else while you answer offline |
| 🐛 Silent regression | No **ratchet** to roll back bad steps | Every accepted finding becomes a local `git commit`; rejects never enter history. The branch is monotonically improving (à la Karpathy AutoResearch) |
| 🧠 Context rot after a few hours | All state lives in conversation | **File-based persistent history** — `plan.md` / `inbox.md` / `escalations.md` survive across sessions; the middle agent re-reads them every cycle instead of relying on context memory |

## 📦 Installation

Install using [`npx skills`](https://skills.sh).

### Install to all supported agents

```bash
# Global — available in all projects, all supported agents
npx skills add zc277584121/perpetuum --all -g

# Project-level — current project only, all supported agents
npx skills add zc277584121/perpetuum --all
```

<details>
<summary><b>Install to a specific agent</b></summary>

```bash
npx skills add zc277584121/perpetuum -a claude-code -g
npx skills add zc277584121/perpetuum -a codex -g
npx skills add zc277584121/perpetuum -a cursor -g
```

Other supported agents include `windsurf`, `github-copilot`, `cline`,
`roo`, `gemini-cli`, `goose`, `kilo`, `augment`, `opencode`, and
[40+ more](https://skills.sh).

> **Project vs Global**: Without `-g`, the skill installs into the
> current project for the selected agent. With `-g`, it installs
> globally and is available across projects.

</details>

You also need `tmux` and `git` available locally.

Then in any project, ask your coding agent:

> Use perpetuum to run continuous adversarial testing on this project
> for the next couple of days.

The skill walks you through a suitability gate (is this actually a task
that benefits from a persistent loop?), picks the closest example,
customizes prompts and trigger for your case, confirms cost/cadence
with you, then launches.

## 🏗️ Architecture

```
        ┌─────────────────────────────────────────────────────────────────┐
        │ 👁️ Layer 4   you + host agent — global monitor & control       │
        │     describe task; watch via `tail` / `tmux -r`; nudge via files│
        │     pause / resume / stop signals; relay natural-language ops   │
        └────────────────────────────────┬────────────────────────────────┘
                                         │ launches
                                         ▼
   ↻ ↻ ↻ ┌─────────────────────────────────────────────────────────────────┐
   ↻     │ ⏰ Layer 3   trigger.sh — heartbeat, loops every cycle ↻        │
   ↻     │     loop until MAX_ITER or .stop_after_current:                 │
   ↻     │       check .paused signal                                      │
   ↻     │       paste prompts/1_explore.md → wait for done flag                   │
   ↻     │       paste prompts/2_execute.md → wait for done flag                   │
   ↻     │       sleep SLEEP_BETWEEN_CYCLES                                │
   ↻ ↻ ↻ │     trigger modes:  schedule  |  conditional  |  webhook        │
         └────────────────────────────────┬────────────────────────────────┘
                                          │ pastes prompt into tmux
                                          ▼
         ┌─────────────────────────────────────────────────────────────────┐
         │ 🧠 Layer 2   middle agent — judge + dispatcher (persistent TUI) │
         │                                                                 │
         │     ┌─ 🔍 phase 1: EXPLORE ────────────────────────────────┐    │
         │     │ read plan.md / inbox.md / escalations.md ## Resolved │    │
         │     │ sample new items (Cartesian product of dimensions)   │    │
         │     │ append to plan.md ## Pending                         │    │
         │     └─────────────────────────────────────────────────────┘    │
         │                                                                 │
         │     ┌─ ⚖️ phase 2: EXECUTE ────────────────────────────────┐    │
         │     │ for each Pending item:                                │    │
         │     │    cc-use delegate ──► Layer 1                        │    │
         │     │    Layer 1 reports observations back ◄──┐             │    │
         │     │    judge the report:                    │             │    │
         │     │       ✅ PASS  → record to plan.md ## Done            │    │
         │     │       🐛 BUG   → dispatch fix + `git commit` (ratchet)│    │
         │     │       ❓ AMBIG → escalations.md ## Open (async)       │    │
         │     └─────────────────────────────────────────────────────┘    │
         └────────────────────────────────┬───────────────────────┬────────┘
                                          │ dispatch              ▲
                                          ▼                       │ report back
         ┌─────────────────────────────────────────────────────────┴───────┐
         │ 🤖 Layer 1   inner agent — fresh CC, zero priors                │
         │     runs the actual operation: CLI command, code read, edit.    │
         │     observes outcome, returns findings to Layer 2.              │
         │     no memory of previous cycles → can't rubber-stamp behavior  │
         └─────────────────────────────────────────────────────────────────┘
```

A few design choices in this layout do the most work — these are also
the answers to "what's the technique behind this?":

- **GAN-like discriminator / generator split** between Layer 2 (judge)
  and Layer 1 (producer). They share no context — Layer 2 sees the whole
  history but can't run the work itself; Layer 1 runs the work but can't
  see history. Neither can fake a result the other would accept. This
  is what stops the self-certifying problem you see in `/goal` and Ralph
  Loop, where the same agent both produces and judges.
- **Monotonic ratchet** via local `git commit`. Every accepted finding
  is a commit; every reject is a `git reset`. The branch is therefore
  monotonically improving — borrowed from Karpathy's AutoResearch
  pattern, but without requiring a scalar metric.
- **Exploration vs exploitation as separate prompts.** Phase 1
  (`prompts/1_explore.md`) is divergent — list new dimensions, sample broadly,
  populate the backlog. Phase 2 (`prompts/2_execute.md`) is convergent — work
  through the backlog one item at a time, commit or escalate. Merging
  them into one prompt is what makes long Ralph-style runs go off the
  rails.
- **File-based persistent history** — `plan.md` is the running log of
  what's been tried, what worked, what was escalated. The middle agent
  re-reads it every cycle, so context rot can't accumulate and a session
  can be paused, killed, or relaunched without losing state.
- **Layer 3 is intentionally dumb.** It only paces and signals. All
  decisions live in Layer 2's two prompt files, which you can edit at
  any time without restarting anything. Trigger configuration is
  per-task (not per-skill), so a task can change its own heartbeat
  without touching the rest of the system.

Layer 4 is optional — you can interact with the state files directly.
The host agent is just a friendlier UI on top of the same file
contracts.

## 🎮 Using It

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

### What the state files actually look like

```markdown
# plan.md   (agent-maintained)
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

```markdown
# inbox.md   (you write)
## Pending
- SKIP: postgres backend, not shipping
- PRIORITIZE: PR #123 first
- NOTE: I'm OOO Friday, no urgent escalations
```

```markdown
# escalations.md   (agent writes ## Open, you fill ## Resolved)
## Open
### (cycle 4) off-by-one in --range flag
A: 1-based inclusive (matches head/tail/sed)
B: 0-based half-open (matches array semantics in most languages)
C: leave both, document the discrepancy
```

### While it's running

Three channels of interaction — pick whichever is easiest:

| You want to… | Do this |
|---|---|
| ✍️ Nudge the agent ("focus on X", "skip Y", "PR #123 is urgent") | Append a line to `inbox.md` under `## Pending` |
| 💬 Answer a question the agent asked | Edit the item in `escalations.md`, add your answer, move to `## Resolved` |
| 👀 See what's happening right now | `tail -f .perpetuum/<task>/trigger.log` or `tmux attach -t middle-<task> -r` (read-only) |
| ⏸️ Pause until you've reviewed | `touch .perpetuum/<task>/.paused` |
| ▶️ Resume | `rm .perpetuum/<task>/.paused` |
| 🛑 Stop gracefully after current cycle | `touch .perpetuum/<task>/.stop_after_current` |
| 💥 Kill hard | `pkill -f trigger.sh; tmux kill-session -t middle-<task>` |

Or just tell your host agent: "perpetuum, pause the testing task" /
"resume" / "skip the postgres tests" — it translates to the file
operations.

## 🧬 Philosophy

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
   loop. New cycles run while the human is offline.
7. **Trigger abstraction** — schedule, conditional, webhook are all
   valid Layer 3 implementations.
8. **File-as-contract** — who can edit which file is a convention,
   not enforcement. Cleaner than role-based access control.

Removing any one of these breaks something. See
[`skills/perpetuum/references/design.md`](skills/perpetuum/references/design.md)
for the long-form rationale.

## 📊 Comparison with related projects

| Project | disc/gen split | ratchet | multi-layer | explore/exploit split | persistent memory | async human | trigger abstraction | file contract |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Claude Code [`/goal`](https://code.claude.com/docs/en/goal) | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Codex [`/goal`](https://github.com/openai/codex) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| [Ralph Loop](https://ghuntley.com/loop/) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| [`recursive-improve`](https://github.com/kayba-ai/recursive-improve) | ❌ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [EvoSkills](https://arxiv.org/abs/2604.01687) | ❌ | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ⚠️ |
| nuwa-skill / [persona](https://github.com/migueldeguzman/persona) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| **`perpetuum`** (this) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Each of the other projects is deeper than `perpetuum` on some single
axis — Karpathy's contract is more elegant for problems with a scalar
metric, Darwin Gödel modifies its own model code, EvoSkills evolves
multi-file skill packages. `perpetuum`'s contribution is the
combination none of the others combine — especially the three axes
most relevant to "keep running across days": **async human
escalation**, **trigger abstraction**, and **explore/exploit split**.

## 🔄 Updating

```bash
npx skills check       # what's stale?
npx skills update      # update everything globally installed
```

To update a project-level install, re-run the `npx skills add` command.

## 🔗 Dependency: `cc-use`

`perpetuum` requires the [`cc-use`](https://github.com/zc277584121/cc-use)
skill — Layer 2 uses it to dispatch every unit of work to a
fresh-context inner agent. The skill checks at init time and prompts
you if missing:

```bash
npx skills add zc277584121/cc-use --all -g
```

If you haven't used `cc-use` before, its README is the prerequisite
read.

## 📜 License

MIT — see [LICENSE](LICENSE).
