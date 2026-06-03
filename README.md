# perpetuum

## Why your `/goal` runs go nowhere

If you've tried Claude Code's `/goal`, Codex's equivalent, or wired up a Ralph
Loop yourself, you've probably hit some flavor of this:

- **The agent self-certifies.** It runs for a while, decides it's done, and
  the result doesn't actually hold up. There's no separation between the
  thing doing the work and the thing judging the work — they share the same
  context, the same biases, the same "let's move on" instinct.
- **No real progress signal.** Without a ratchet, the loop can silently
  regress: bad edits stick because nobody notices, and you can't roll a
  specific finding back without unwinding everything.
- **Context rot.** A multi-hour run accumulates conversation. By cycle 6
  the model is paying more attention to "what we already tried" than to
  the actual problem.
- **Human-in-the-loop is a hard wall, not a soft exit.** The first time
  the agent hits something ambiguous, it either guesses wrong or stops
  and waits. If you're not at the terminal, the whole loop is dead.
- **No trigger abstraction.** "Every 40 minutes" is the only shape. You
  can't actually drive it from real events (a new PR, a file change, an
  alert) without building the plumbing yourself.
- **Exploration and execution are entangled.** The agent plans, executes,
  and judges in the same prompt — which means it often commits things it
  hadn't really planned, or plans things it isn't going to do.

`perpetuum` (Latin for "perpetual motion" — the name is ironic; perpetual
motion is impossible, but with the right scaffolding the loop can come
close enough) is the combination of mechanisms that fixes those
specific failures. It isn't a smarter model and it isn't a bigger
framework. It's a thin skill that arranges things so:

| Failure mode above | What `perpetuum` does about it |
|---|---|
| Self-certifying agent | A **three-layer architecture** — the agent doing the work is a fresh `cc-use` dispatch with no priors; the agent judging the work is a different, persistent middle agent; neither shares context with the other. |
| No progress signal | **Ratchet by git commit.** Every accepted finding becomes a local commit; rejected ones never enter history. Rollback is just `git reset`. |
| Context rot | **File-based persistent memory** (`plan.md`, `inbox.md`, `escalations.md`). State lives on disk, not in conversation. The middle agent re-reads files at every cycle start. |
| Hard human-wall | **Asynchronous human escalation.** Ambiguous decisions go into `escalations.md` with full A/B/C options. The loop keeps running on everything else. You answer when you have time. |
| No trigger abstraction | **Three trigger types** — schedule, conditional (poll an external state), webhook (event-driven). Same loop, swap the trigger file. |
| Explore/execute entangled | **Two prompts per cycle.** `1_explore.md` plans only, `2_execute.md` dispatches only. Lexically-sorted files mean you can drop a `3_reflect.md` in to add a reflection phase without touching code. |

The result: a loop that can actually run for hours, days, or weeks
without you watching it, and produces work you can audit afterwards
because state is in markdown and history is in git.

## Quick Start

Install to all supported agents at once:

```bash
npx skills add zc277584121/perpetuum --all -g
```

Then in any project, ask your coding agent:

> Use perpetuum to run continuous adversarial testing on this project for
> the next couple of days.

The skill walks you through:

1. A **suitability gate** — is this actually the kind of task that benefits
   from a persistent loop? (Not all tasks are.)
2. Picking the closest example from `examples/` and materializing it under
   `.perpetuum/<task-name>/` in your project.
3. A **cost / rate-limit check** — the default cadence is aggressive
   (2 min between cycles); you confirm you want full throttle or dial
   down before launch.
4. Launching `trigger.sh` and a short briefing on what files you can
   edit and how to pause / resume / stop the loop.

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

Other supported agents include `windsurf`, `github-copilot`, `cline`, `roo`,
`gemini-cli`, `goose`, `kilo`, `augment`, `opencode`, and
[40+ more](https://skills.sh).

> **Project vs Global**: Without `-g`, the skill installs into the current
> project for the selected agent. With `-g`, it installs globally and is
> available across projects.

### Dependency: `cc-use`

`perpetuum` requires the [`cc-use`](https://github.com/zc277584121/cc-use)
skill — the middle layer uses it to dispatch every unit of work to a
fresh-context inner agent. The skill checks at init time and prompts you
to install if missing:

```bash
npx skills add zc277584121/cc-use --all -g
```

You also need `tmux` (`tmux -V` to verify) and `git` available locally.

## Updating

```bash
# Check for updates
npx skills check

# Update all globally installed skills to latest
npx skills update
```

To update a project-level install, re-run the `npx skills add` command.

## Using It

After installation, perpetuum is a normal skill. From your coding agent's
TUI:

```text
Use perpetuum to watch this repo's GitHub issues and triage new ones every
hour. I'll review escalations whenever I get to them.
```

```text
Use perpetuum to iteratively polish this draft article toward Karpathy's
writing style. I've put his articles in target_corpus/.
```

```text
Use perpetuum to keep finding observability gaps in the worker module.
Run for ~20 cycles, then stop and let me review.
```

The skill picks the closest example, customizes the prompts and trigger
for your specific task, and launches it.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 4   the host agent you are talking to                  │  optional,
│           (it called this skill, can monitor + relay)        │  human-friendly
└────────────────────────┬─────────────────────────────────────┘
                         │ spawns
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 3   trigger.sh — schedule / conditional / webhook      │  stupid heartbeat
└────────────────────────┬─────────────────────────────────────┘
                         │ pastes prompt into
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 2   middle agent (persistent CC TUI in tmux)           │  smart explorer +
│           reads plan + inbox + escalations history           │  judge + dispatcher
│           dispatches, judges, records, escalates             │
└────────────────────────┬─────────────────────────────────────┘
                         │ cc-use delegate
┌────────────────────────▼─────────────────────────────────────┐
│ Layer 1   inner agent (fresh-context CC)                     │  stupid worker,
│           does the actual work this cycle, reports back      │  no priors
└──────────────────────────────────────────────────────────────┘
```

Everything is files. State, memory, signals, history, human input —
markdown + git + tmux + a couple of `touch` flags. No vector DB, no
framework lock-in, no daemon, no agent SDK.

A task running on a project looks like:

```
<your-project>/
└── .perpetuum/
    └── <task-name>/
        ├── _meta.md             worktree/branch metadata
        ├── trigger.sh           per-task; you adjust at init
        ├── 1_explore.md         prompt 1: plan
        ├── 2_execute.md         prompt 2: dispatch + judge + record
        ├── plan.md              agent-maintained state machine
        ├── inbox.md             human → agent channel (free text)
        ├── escalations.md       agent → human channel (A/B/C options)
        ├── trigger.log
        ├── .paused              (signal, optional)
        ├── .stop_after_current  (signal, optional)
        └── state/
            └── .cycle_done_*
```

## Philosophy

`perpetuum` is built from eight ideas. Individually, none is new.
The combination is what makes it work.

1. **Discriminator / Generator separation** (from GANs) — Layer 2 judges,
   Layer 1 generates, they never share context.
2. **Monotonic ratchet** — every Done becomes a commit, every reject
   never enters history. `git reset` is the rollback.
3. **Three-layer architecture** (stupid → smart → stupid) — heartbeat
   at the top, intelligence in the middle, focused execution at the
   bottom.
4. **Exploration vs Exploitation split** — two prompts, one per mental
   mode. Fused, they confuse each other.
5. **File-based persistent memory** — plan/inbox/escalations + git log
   is the entire memory system. Survives sessions, reboots, restarts.
6. **Asynchronous human escalation** — escalations never block the
   loop. New cycles still run while the human is offline.
7. **Trigger abstraction** — schedule, conditional, webhook are all
   valid Layer 3 implementations. The middle and inner layers don't care.
8. **File-as-contract** — who can edit which file is a convention,
   not enforcement. Cleaner than role-based access control.

Removing any one of these breaks something. See
[`skills/perpetuum/references/design.md`](skills/perpetuum/references/design.md)
for the long-form rationale.

## Comparison with related projects

| Project | discriminator/generator | ratchet | multi-layer | explore/exploit split | persistent memory | async human | trigger abstraction | file contract |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Claude Code [`/goal`](https://code.claude.com/docs/en/goal) | ⚠ same-context Haiku judge | ✗ | ✗ | ✗ | ✗ session-bound | ✗ blocks | ✗ schedule only | ✗ |
| Codex [`/goal`](https://github.com/openai/codex) | ✗ | ✗ | ✗ | ✗ | △ thread store | ✗ blocks | ✗ schedule only | ✗ |
| [Ralph Loop](https://ghuntley.com/loop/) | ✗ | ✗ | ✗ | ✗ | △ files | ✗ blocks | ✗ `while true` | ✗ |
| [`recursive-improve`](https://github.com/kayba-ai/recursive-improve) | ✗ | ✓ | ✗ | ✗ | △ | ✗ | ✗ | ✗ |
| [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) | ✗ frozen evaluator | ✓✓ | ✗ single agent | ✗ | ✓ files | ✗ | ✗ schedule | ✓✓ |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | ✗ self-modifying | ✓ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| [EvoSkills](https://arxiv.org/abs/2604.01687) | ✗ | ✓ | ✗ | △ | △ | ✗ | ✗ | △ |
| nuwa-skill / [persona](https://github.com/migueldeguzman/persona) | ✗ | ✗ | ✗ | ✗ | △ prompt-level | ✗ | ✗ | ✗ |
| **perpetuum** (this) | ✓✓ | ✓ | ✓✓ | ✓ | ✓ | ✓✓ | ✓ | ✓ |

Each of the existing projects is deeper than `perpetuum` on some single
axis — Karpathy's contract is more elegant for problems with a scalar
metric, Darwin Gödel modifies its own model code, EvoSkills evolves
multi-file skill packages. `perpetuum`'s contribution is that it
combines the axes none of the others combine, in particular **async
human escalation** + **trigger abstraction** + **explore/exploit split**,
at a complexity level a single developer can fork and modify in an
afternoon.

## Dependency

`perpetuum` builds on [`cc-use`](https://github.com/zc277584121/cc-use),
which provides the outer-supervises-inner tmux dispatch primitive that
Layer 2 uses to spawn Layer 1. If you haven't used `cc-use` before, its
README is the prerequisite read.

## License

MIT — see [LICENSE](LICENSE).
