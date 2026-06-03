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

There are **three specific reasons** today's autonomous-agent attempts
fail at "perpetual" — and three corresponding mechanisms perpetuum
uses to fix each:

1. **Vague goals, wide operating space → the agent drifts off-target.**
   `/goal`-style tools accept whatever sentence you typed as the goal
   and give the agent unlimited interpretive freedom. With nothing
   actively pulling it back to the main thread or vetting its mid-run
   decisions, it wanders.
   **→ perpetuum** forces a narrow, judgeable goal up front
   (suitability gate), then uses Layer 2's two-prompt **plan / judge**
   cycle every round — `plan` re-checks the direction the agent is
   heading, `judge` rejects "fake progress" from Layer 1 before it
   becomes a commit.

2. **No continuation mechanism → one short run and you're done.**
   `/goal` is single-session. Even the "infinite loop" variants are
   blindly time-triggered, no concept of event or condition. But
   real "do more of this" work — find more bugs, fit a metric
   tighter, watch for new PRs — needs the loop to span sessions,
   restarts, and different kinds of trigger.
   **→ perpetuum's Layer 3** abstracts triggers into three kinds
   (`schedule` / `conditional` / `webhook`) and stitches arbitrarily
   many cycles together on the time axis.

3. **Human-in-the-loop is a wall, not a sluice → the first ambiguity
   freezes everything.** Traditional loops have no way to keep going
   when they hit something they can't decide alone. They guess wrong
   or stop and wait — and if you're not at the terminal, "wait"
   means dead.
   **→ perpetuum** has three async channels — `escalations.md`
   (agent surfaces A/B/C options for ambiguous decisions),
   `inbox.md` (you push instructions back in whenever), and
   **Layer 4** (the host agent you're talking to, which monitors,
   coordinates, and translates your natural-language asks into file
   operations) — so the loop keeps progressing while you answer at
   your own pace.

📖 **For the full design rationale with ASCII diagrams of each
problem and its solution, see [The three core problems,
visualized](#-the-three-core-problems-visualized) below**
(or just scroll down — it's the heart of the doc).

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

## 🎯 The three core problems, visualized

The three failure modes from the intro, drawn out so the design choices
are concrete. These three diagrams are the heart of why `perpetuum`
exists; everything else (the eight ideas below, the comparison table,
the `cc-use` mechanics) is supporting infrastructure.

### Problem 1 — Goal too vague, operating space too wide → drift

```
Today (/goal, Ralph Loop): the goal sentence is open to interpretation,
agent roams a huge unconstrained space.

   ┌──────────────────────────────────────────────────────────────────┐
   │                                                                  │
   │     goal: "make this project better" ← user's one sentence,      │
   │            no metric, no boundary                                │
   │                                                                  │
   │   start                                                          │
   │     ●──►──►──►──╮                                                │
   │                 ╰──►──►──►──╮                                    │
   │                             ╰──►──►──►   ❓ off-target           │
   │                                       ╰──►──►──►──►              │
   │                                                  ╰──►──►──►──►   │
   │                                                            ❓❓  │
   │                                                                  │
   └──────────────────────────────────────────────────────────────────┘
       ↑ boundary = the entire interpretive space; nobody steers,
                    agent goes wherever, however far


perpetuum: narrow goal (suitability gate) + Layer 2 plan + Layer 2 judge

   ┌── suitability gate forces a narrow, judgeable goal up front ──┐
   │                                                               │
   │         🔍 plan          ⚖️ judge         🔍 plan               │
   │       (rechecks dir)   (rejects fake)   (rechecks dir)         │
   │             ▼               ▼                ▼                 │
   │   start     │               │                │                 │
   │     ●──►──►─●──►──►──►──►──►●──►──►──►──►──►─●──►──►──►──►─►   │
   │             ↑               ↑                ↑                 │
   │      pull back on-target  reject fake     explore new          │
   │                           progress         direction (safely)  │
   │                                                                │
   └────────────────────────────────────────────────────────────────┘

       Key:  the boundary is intentionally narrow,
             plan re-steers periodically, judge vetoes bad single steps.
```

### Problem 2 — No continuation: one short run and done

```
Today: a /goal run is a one-shot. Done = ended.

   ┌──────────────────────────────────────┐
   │                                      │
   │  start ●──►──►──►──►──► done/stuck ▮ │
   │        ╰──── one-shot ────╯           │
   │                                      │
   │  then what? nothing. ☠                │
   │                                      │
   └──────────────────────────────────────┘
       ↑ single segment on the time axis. "Find more bugs forever",
         "fit a metric tighter", "watch for new PRs" → impossible.


perpetuum: Layer 3 trigger abstraction stitches "Problem 1's solution"
across the time axis, indefinitely.

   Triggers (Layer 3):

      ⏰ schedule        🔔 conditional         📨 webhook
      (every N min)     (poll external state)   (event-driven)
          │                  │                       │
          ▼                  ▼                       ▼
   ┌──────────┐ sleep ┌──────────┐ sleep ┌──────────┐ sleep ┌──────────┐
   │ ►cycle 1►│ ───── │ ►cycle 2►│ ───── │ ►cycle 3►│ ───── │ ►cycle N►│ ...
   │ (P1 solv)│       │ (P1 solv)│       │ (P1 solv)│       │ (P1 solv)│
   │ ratchet ✓│       │ ratchet ✓│       │ ratchet ✓│       │ ratchet ✓│
   └──────────┘       └──────────┘       └──────────┘       └──────────┘
        ↓                 ↓                  ↓                  ↓
        plan.md ←── persisted ←── persisted ←── persisted ←── persisted

       Key:  each cycle = a safe short segment (Problem 1's solution).
             Concatenated, they form genuine "perpetual" work.
             Triggers are how cycles know when to start:
               schedule    → do it more, on a timer
               conditional → only run when external state changed
               webhook     → only run on an external event
```

### Problem 3 — Human-in-the-loop is a wall → ambiguity freezes the run

```
Today: hit ambiguity → stop and wait synchronously. Human asleep = dead.

   ┌─────────────────────────────────────────────────────────────┐
   │                                                             │
   │   start ●──►──►──►─── ⚠️ "A or B?"                            │
   │                            │                                │
   │                            │ wait for human                 │
   │                            ▼                                │
   │                        ▮ stuck ▮ stuck ▮ ...                │
   │                                                             │
   │   human is sleeping / out / busy → task dies here ☠          │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘


perpetuum: three async channels keep the main loop progressing while
the human's input arrives whenever it arrives.

   Main loop (Layer 2/3, always progressing):

   cycle 1 ──►──► cycle 2 ──►──► cycle 3 ──►──► cycle N ──►──► ...
      │              │              │
      │ ambiguous     │ ambiguous     │ went off-track
      │ → write out   │ → write out   │ → git reset (ratchet,
      ▼              ▼              ▼   never enters main branch)
   ╔════════════════════════════════════════════════╗
   ║  escalations.md   (agent writes; human answers ║
   ║                    when convenient)             ║
   ║   ## Open                                       ║
   ║   - A / B / C ?                                 ║
   ║   - Pick a naming convention                    ║
   ║                                                 ║
   ║   ## Resolved   (you fill in at your own pace)  ║
   ╚═════════════════════╤═══════════════════════════╝
                         │
                         │ you answered
                         ▼
   ╔════════════════════════════════════════════════╗
   ║  inbox.md   (you push instructions in)         ║
   ║   ## Pending                                    ║
   ║   - SKIP: postgres                              ║
   ║   - PRIORITIZE: PR #123                         ║
   ║   - DIRECTION: focus on auth module             ║
   ╚═════════════════════╤═══════════════════════════╝
                         │
                         │ next cycle's explore phase reads & applies
                         ▼
                  cycle N+1 ──►──► ...

   And one layer up:

   ┌────────────────────────────────────────────────────────────────┐
   │  Layer 4   you + host coding agent (Claude Code / Codex)       │
   │  - monitor:  tail trigger.log / tmux -r to watch middle agent  │
   │  - translate: you say "pause the testing task" / "skip pg"     │
   │              → agent translates to file operations             │
   │  - coordinate: read escalations / inbox / plan, surface what   │
   │              needs your attention                              │
   └────────────────────────────────────────────────────────────────┘

       Key:  ambiguity → escalations (loop keeps going)
             off-track step → git reset (ratchet undoes silently)
             human-not-there → that's fine, async by design
```

### How the three solutions compose

```
                     Problem 1               Problem 2              Problem 3
                  ┌──────────────┐        ┌─────────────┐        ┌──────────────┐
   today's /goal: │ wide goal,    │   +    │ one-shot run │   +    │ human = wall  │
                  │ agent drifts  │        │              │        │              │
                  └──────────────┘        └─────────────┘        └──────────────┘
                        │                        │                       │
                        ▼                        ▼                       ▼
                  ┌──────────────┐        ┌─────────────┐        ┌──────────────┐
   perpetuum:     │ narrow goal + │   ×    │ Layer 3      │   ×    │ async escal+  │
                  │ Layer 2       │        │ schedule/    │        │ inbox + git   │
                  │ plan + judge  │        │ conditional/ │        │ safety net    │
                  │               │        │ webhook      │        │               │
                  └──────────────┘        └─────────────┘        └──────────────┘

   Multiplied together → "actual perpetual":
     ① every step stays on-target (no drift)
     ② time axis extends indefinitely (no ending)
     ③ humans dipping in/out doesn't freeze anything (no wall)
```

## 🧬 Supporting ideas (eight building blocks)

The three core problems above are what perpetuum actually solves. The
implementation borrows from eight related ideas — each individually
well-known, none combined like this in prior art. They're the
plumbing that makes the three core mechanisms run reliably; they're
not themselves the point.

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
