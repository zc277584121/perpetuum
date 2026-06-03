# perpetuum ♾️

## 🛑 Why your `/goal` runs go nowhere

You've probably tried `/goal` in Claude Code or Codex. It runs for a
few minutes, decides "task complete", and stops. **That's not perpetual.
That's just "unattended for 20 minutes."**

`perpetuum` is what lets your coding agent actually run **while you
sleep, while you're at lunch, while you're on vacation.** It keeps
producing work for hours and days, asks for your input asynchronously
when it needs you, and never decides on its own that the job is done.

Think of it as letting your coding agent moonlight as your night-shift
coworker. You hand it a project, go to bed, come back to a stack of
commits and a short list of "hey, you need to decide this one" notes.

The specific things that go wrong with `/goal` — and how `perpetuum`
fixes each:

| What you've seen | Why it happens | What `perpetuum` does |
|---|---|---|
| ⏱️ Runs 20 min and stops — you wanted overnight | Single-session loop, no real continuation beyond one task | Triggers (schedule / conditional / webhook) keep the loop alive across cycles, restarts, days |
| 🤡 Agent self-certifies "done" | Same context produces and judges | Three layers: middle judges, fresh inner via `cc-use` produces — they never share context |
| 🐛 Silent regression | No ratchet to roll back bad steps | Every accepted finding becomes a local `git commit`; rejects never enter history |
| 🧠 Context rot after a few hours | All state lives in conversation | State lives in markdown files; middle re-reads them every cycle |
| 🚧 Human-in-loop is a hard wall | Ambiguity → stops and waits for you | Async `escalations.md` — loop keeps going on everything else while you answer offline |
| 🔀 Plan and execute entangled | One prompt does both | Two prompts per cycle (`1_explore.md`, `2_execute.md`); drop `3_reflect.md` in to add reflection |

## 🚀 Quick Start

```bash
npx skills add zc277584121/perpetuum --all -g
```

Then in any project, ask your coding agent:

> Use perpetuum to run continuous adversarial testing on this project
> for the next couple of days.

The skill walks you through a suitability gate (is this actually a task
that benefits from a persistent loop?), picks the closest example,
customizes prompts and trigger for your case, confirms cost/cadence
with you, then launches.

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

## 🏗️ Architecture

```
            ┌────────────────────────────────────────────────────────┐
            │ Layer 4   you + host agent (Claude Code / Codex TUI)   │
            │           you describe the task; agent sets up,        │
            │           monitors, relays your nudges (optional)      │
            └──────────────────────┬─────────────────────────────────┘
                                   │ spawns
                                   ▼
            ┌────────────────────────────────────────────────────────┐
            │ Layer 3   trigger.sh — the dumb heartbeat              │
            │           paste 1_explore.md → wait → paste 2_execute  │
            │           → wait → sleep. Loop until done or stopped.  │
            │           triggers: schedule / conditional / webhook   │
            └──────────────────────┬─────────────────────────────────┘
                                   │ pastes prompt into tmux
                                   ▼
            ┌────────────────────────────────────────────────────────┐
            │ Layer 2   middle agent — persistent CC TUI in tmux     │
            │   phase 1 explore: read plan/inbox → append new items  │
            │   phase 2 execute: dispatch to Layer 1 → judge result  │
            │                    → commit OR escalate to human       │
            └──────────────────────┬─────────────────────────────────┘
                                   │ cc-use delegate
                                   ▼
            ┌────────────────────────────────────────────────────────┐
            │ Layer 1   inner agent — fresh CC, zero priors          │
            │           runs the actual work, reports observations   │
            │           never sees previous cycles → can't rubber-   │
            │           stamp known behavior                          │
            └────────────────────────────────────────────────────────┘
```

Everything is files. State, memory, signals, history, human input —
markdown + git + tmux + a couple of `touch` flags. No vector DB,
no framework lock-in, no daemon, no agent SDK.

A task on a project looks like:

```
.perpetuum/<task>/
├── plan.md              agent writes — what's done / pending
├── inbox.md             YOU write    — nudges, priorities, skips
├── escalations.md       agent ↔ you  — ambiguous decisions, A/B/C
├── trigger.sh           per-task     — heartbeat config
├── 1_explore.md         prompt 1     — planning
├── 2_execute.md         prompt 2     — dispatching + judging
├── _meta.md             set once     — branch / worktree metadata
├── .paused              signal       — pause the loop
├── .stop_after_current  signal       — graceful stop
└── trigger.log
```

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
fresh-context inner agent. The skill checks at init time and prompts you
if missing:

```bash
npx skills add zc277584121/cc-use --all -g
```

If you haven't used `cc-use` before, its README is the prerequisite
read.

## 📜 License

MIT — see [LICENSE](LICENSE).
