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
uses to fix each. **Click each one to expand for the full explanation
and an ASCII diagram:**

<details>
<summary><b>1. Vague goals, wide operating space → the agent drifts off-target</b></summary>

<br>

`/goal`-style tools accept whatever sentence you typed as the goal
and give the agent unlimited interpretive freedom. With nothing
actively pulling it back to the main thread or vetting its mid-run
decisions, it wanders.

**→ perpetuum** requires the goal to be narrow and judgeable
before it starts, and in every round it explicitly separates
"where should we head next?" from "do this concrete piece of
work and check the result". Because the part that proposes the
work and the part that accepts it stay distinct, drift gets
caught and "fake progress" can't quietly accumulate.

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


perpetuum: narrow goal (suitability gate) + plan + judge every cycle

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

</details>

<details>
<summary><b>2. No continuation mechanism → one short run and you're done</b></summary>

<br>

`/goal` is single-session. Even the "infinite loop" variants are
blindly time-triggered, no concept of event or condition. But a
lot of "keep this going" work runs on events, not a clock —
watching for new PRs and triaging them as they arrive, reacting
to alerts when they fire, scanning whenever the codebase changes.
The loop needs to span sessions, restarts, and respond to
different kinds of trigger.

**→ perpetuum** gives the loop a real continuation mechanism:
it can run on a fixed schedule, or wake up when something
outside changes (a new PR appears, a file is touched, an alert
fires), or react to incoming events. The same loop persists
across sessions, restarts, days — pick whatever trigger matches
the work.

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
       ↑ single segment on the time axis.
         "Find more bugs forever", "watch for new PRs",
         "react to alerts" → impossible past the first run.


perpetuum: stitch "Problem 1's solution" across the time axis,
indefinitely, on whichever kind of trigger fits the work.

   Triggers:

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

</details>

<details>
<summary><b>3. Human-in-the-loop is a wall, not a sluice → the first ambiguity freezes everything</b></summary>

<br>

Traditional loops have no way to keep going when they hit something
they can't decide alone. They guess wrong or stop and wait — and if
you're not at the terminal, "wait" means dead.

**→ perpetuum** makes the human-in-the-loop interaction
asynchronous. When the agent hits something only you can decide,
it writes the question down (along with the concrete options it
considered) and keeps going on everything else; you answer in
your own time. You can also nudge the running loop with a new
instruction at any moment without stopping it. Nothing blocks on
you being at the keyboard.

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


perpetuum: async channels keep the main loop progressing while
the human's input arrives whenever it arrives.

   Main loop (always progressing):

   cycle 1 ──►──► cycle 2 ──►──► cycle 3 ──►──► cycle N ──►──► ...
      │              │              │
      │ ambiguous     │ ambiguous     │ judge rejects
      │ → write out   │ → write out   │ a bad proposal
      ▼              ▼              ▼ → no commit happens
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

       Key:  ambiguity → goes to a queue (loop keeps going)
             off-track step → judge rejects it; no commit happens
             human-not-there → that's fine, the loop is async by design
```

</details>

The three solutions multiply: every cycle stays on-target (P1), the
time axis extends across triggers and restarts (P2), human input
arrives async without freezing anything (P3). Together that's what
"actually perpetual" means in practice.

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

Four layers, each tied to one of the three problems above. Read the
right-side tags first — they're the whole point.

```
   ┌────────────────────────────────────────────────────────┐
   │ 👁️  Layer 4   you + host agent (Claude Code / Codex)   │
   │      describe the task, nudge it, pause, resume, stop  │
   │      — all in natural language                         │
   └───────────────────────────┬────────────────────────────┘
                               │ launches
                               ▼
 ↻ ┌────────────────────────────────────────────────────────┐ ──► solves P2
 ↻ │ ⏰ Layer 3   trigger — heartbeat, loops every cycle    │    "no continuation":
 ↻ │      schedule  |  conditional  |  webhook              │    time, event, or
 ↻ │      keeps running until you stop it                   │    condition keeps
 ↻ └───────────────────────────┬────────────────────────────┘    the loop alive
                               │ kicks off next cycle
                               ▼
   ┌────────────────────────────────────────────────────────┐ ──► solves P1
   │ 🧠 Layer 2   middle agent — judge + dispatcher         │    "agent drifts":
   │                                                        │    narrow goal
   │      🔍 EXPLORE                                        │    + plan / judge
   │         re-read state · re-check direction             │    split keeps
   │         queue the next pending items                   │    work on-target
   │                                                        │
   │      ⚖️ EXECUTE                                        │
   │         for each pending item:                         │
   │            dispatch to Layer 1   ──►                   │
   │            judge the report:                           │
   │               ✅ pass   → record + commit              │
   │               🐛 bug    → fix + commit                 │
   │               ❓ ambig  → queue for human (no block) ──┼──► solves P3
   └───────────────────────────┬────────────────────▲───────┘    "human is a wall":
                               │ dispatch           │ report     ambiguity goes
                               ▼                    │            to an async queue,
   ┌────────────────────────────────────────────────┴───────┐    loop keeps going
   │ 🤖 Layer 1   inner agent — fresh context, zero priors  │
   │      runs the operation, observes, reports back        │
   │      no memory of past cycles ⇒ can't self-certify     │
   └────────────────────────────────────────────────────────┘
```

Layer 4 is optional — you can drive the state files directly. The
host agent is just a friendlier UI on top of the same file contracts.

## 🎮 Using It

After installation, perpetuum is a normal skill. From your coding
agent's TUI, name it explicitly and describe what you want it doing
overnight (or longer):

```text
Use perpetuum to run continuous adversarial testing against this CLI
for the next 30 cycles. Categories I care about: auth, parser, error
paths. Open A/B/C when a failure mode is ambiguous.
```

```text
Use perpetuum to watch this repo's GitHub issues and triage new ones
every hour. Tag them, suggest labels, escalate only the ones that
need a product decision.
```

```text
Use perpetuum to keep finding observability gaps in the worker module
for ~20 cycles, then stop and let me review. Commit each gap-fix as
a separate commit so I can cherry-pick.
```

```text
Use perpetuum to iteratively polish this draft article toward
Karpathy's writing style. His articles are in target_corpus/. Use BLEU
+ readability + a stylistic-similarity LLM judge as the metric. Stop
when the metric plateaus for 5 cycles.
```

```text
Use perpetuum to watch CI on the main branch. When a build fails,
diagnose, propose a fix, commit it to a fix/<short-name> branch, and
open a PR. Don't push to main directly. Run on the webhook trigger.
```

```text
Use perpetuum to comb every PR in this repo for security-relevant
diffs (auth, secrets, network). For each PR write a one-paragraph
risk note. Run on the conditional trigger — only spin up when a new
PR arrives.
```

### Why these tasks fit

The pattern they share:

- **A clear, narrow goal**, not "make this project better".
- **A judgeable signal** — pass/fail, a number that goes up, a diff
  someone can review. Without one, the ratchet has nothing to ratchet on.
- **Many small steps**, not one big atomic delivery — perpetuum's
  advantage compounds over cycles.
- **Tolerance for the inner agent being wrong sometimes** — the
  outer judge catches it, but if a single wrong step is catastrophic
  (e.g. deploying to prod), this is the wrong tool.
- **Either the work itself takes a long time, or you want to do a
  small step many times over many days.** A 10-minute task doesn't
  need perpetuum; a 10-cycle task across a long weekend does.

### When it's the wrong tool

Don't reach for perpetuum if:

- **One-shot tasks.** "Rename this function across the codebase",
  "write a regex for this log format" — these are single steps, not
  loops. Use `/goal` or a normal coding session.
- **The goal isn't judgeable.** "Make this UI look nicer", "rewrite
  this in a more elegant way" with no concrete criterion. Without
  something Layer 2 can grade, fake progress is indistinguishable
  from real progress.
- **Every step needs synchronous human input.** Pair-programming on
  a new feature, exploring a design space together — the whole point
  of perpetuum is that you're *not* at the terminal. If you would
  be anyway, just talk to your coding agent directly.
- **Irreversible actions on every step.** Sending emails to real
  users, hitting production APIs that charge money, deleting data.
  perpetuum's ratchet is local — it can roll back a commit, not an
  email or a charge.
- **You need the answer in the next 10 minutes.** perpetuum trades
  wall-clock time for unattended time. If you're waiting, you're
  using it wrong.

The skill walks you through a suitability gate at init — it will
push back, or refuse, if your task lands in the second list. It
also picks the closest example from
[`examples/`](skills/perpetuum/examples/) (currently:
`adversarial-testing`, `github-watcher`, `style-distill`,
`article-polish`, `observability-gap`), customizes the prompts and
trigger for your case, walks through a cost/cadence check, then
launches.

<details>
<summary><b>What the state files actually look like</b></summary>

<br>

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

</details>

### While it's running

Once launched, the task is a black box. You don't need to know which
layer is doing what; you only need to know which **kinds** of operations
you can send in, and what comes out.

```
                    ┌──────────────────────────────────────┐
                    │                                      │
                    │      ⚫  a perpetuum task running    │ ──► 📜 git commits
                    │            (the loop, hidden)        │     (the actual work)
                    │                                      │
                    └──────────────────────────────────────┘
                       ▲          ▲           ▲          ▲
                       │          │           │          │
                  ✍️ nudge   💬 answer   ⏸️ pause   👀 watch
                  push new   resolve     ▶️ resume   read-only
                  direction  open A/B/C  🛑 stop    progress
                  or skips   questions                    feed
                       ▲          ▲           ▲          ▲
                       │          │           │          │
                       └──────────┴─────┬─────┴──────────┘
                                        │
                              all in natural language
                                        │
                                        ▼
                  👤 you ──► 👁️ host agent (Claude Code / Codex / …)

           "perpetuum, focus on auth this week"
           "the off-by-one question — go with option B"
           "pause until I've looked at the last few commits"
           "what's it working on right now?"
           "stop after the current cycle"
```

The host agent translates your sentences into the underlying file
operations. You never have to remember a flag name or a file path —
if you can describe the change in plain English, you can drive the
loop.

## 🧬 Design philosophy

The three core problems above are what perpetuum solves. To solve
them it leans on nine deliberate design choices — each individually
well-known, none combined like this in prior art. These are the
same nine axes the comparison table below scores every project on,
in the same order. Read this section, then read the table; the
table will then read like a checklist instead of a wall of emoji.

1. **Discriminator / Generator separation** (from GANs). Layer 2 is
   the discriminator — it sees the entire history, judges every
   proposal, but does not run code itself. Layer 1 is the generator —
   fresh context every dispatch, runs the actual operation, has no
   memory of what came before. Because they share no context, neither
   can fake a result the other would accept. This is what kills the
   self-certifying failure mode in `/goal` and Ralph Loop.

2. **Monotonic ratchet** via local `git commit`. Layer 2 judges every
   Layer 1 proposal *before* it becomes a commit — rejected ones
   never enter history. Accepted ones land as a clean append-only
   sequence on the branch, and `git log` doubles as the durability
   mechanism across sessions, machines, and reboots. Without a
   ratchet, you can't tell progress from noise on a long run.

3. **Three-layer architecture** (dumb → smart → dumb). Layer 3 is
   intentionally a few hundred lines of bash — no LLM, no judgment,
   just heartbeat. Layer 2 is the only smart layer. Layer 1 is a
   fresh-context worker with no opinions of its own. Splitting the
   smart middle from a dumb-cheap outer wrapper is what keeps the
   middle agent's context clean over long runs and what makes the
   loop crash-tolerant.

4. **Exploration vs Exploitation split** at the prompt level.
   Phase 1 (`prompts/1_explore.md`) is divergent — re-read state,
   re-check direction, queue new pending items. Phase 2
   (`prompts/2_execute.md`) is convergent — work down the queue,
   one item at a time, commit or escalate. Fusing them into one
   prompt is what makes long Ralph-style runs drift.

5. **File-based persistent memory.** plan / inbox / escalations +
   the git log are the entire memory system. No vector DB, no
   embeddings. Layer 2 re-reads these files at the start of every
   cycle, so context rot stays bounded and state survives any
   restart — pause at noon, resume at midnight, next cycle picks
   up exactly where the last one left off.

6. **Asynchronous human escalation.** When Layer 2 hits an ambiguous
   decision (off-by-one semantics, naming convention, product-call),
   it writes A/B/C options to `escalations.md ## Open` and *moves
   on to the next item*. The human answers when convenient; the
   loop never blocks waiting for a reply. This is what makes
   "overnight, no synchronous attention" actually work.

7. **Trigger abstraction.** Layer 3 supports three trigger families:
   schedule (every N minutes), conditional (poll an external state
   like `gh pr list`), webhook (react to incoming events). All
   three feed the same Layer 2 / Layer 1 stack — switching trigger
   doesn't touch the judge or executor.

8. **File-as-contract.** Who can edit which file is a convention,
   not enforced by code: agent owns `plan.md`, human owns `inbox.md`,
   both touch `escalations.md` at different sections. Cleaner than
   role-based access control, debuggable with `cat`, mergeable with
   `git`.

9. **Host-agnostic dispatch.** Layer 1 is launched through
   [`cc-use`](https://github.com/zc277584121/cc-use), which speaks
   either Claude Code or Codex (and 40+ other coding-agent CLIs).
   The same skill, prompts, file contracts, and trigger logic run
   identically against whichever host you have installed — a task
   started under Claude Code can be picked up later under Codex,
   because the state is just files on disk.

Removing any one of these breaks something. See
[`skills/perpetuum/references/design.md`](skills/perpetuum/references/design.md)
for the long-form rationale on each.

## 📊 Comparison with related projects

| Project | disc/gen split | ratchet | multi-layer | explore/exploit split | persistent memory | async human | trigger abstraction | file contract | Claude+Codex |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Claude Code [plan mode](https://code.claude.com/docs/en/plan-mode) | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Codex `/plan` mode | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Claude Code [`/goal`](https://code.claude.com/docs/en/goal) | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Codex [`/goal`](https://github.com/openai/codex) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| [`goalbuddy`](https://github.com/tolibear/goalbuddy) | ❌ | ⚠️ | ❌ | ⚠️ | ✅ | ❌ | ❌ | ✅ | ✅ |
| [`OpenSpec`](https://github.com/Fission-AI/OpenSpec) | ❌ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ❌ | ✅ | ✅ |
| [Ralph Loop](https://ghuntley.com/loop/) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ⚠️ |
| [`recursive-improve`](https://github.com/kayba-ai/recursive-improve) | ❌ | ✅ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ | ❌ |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [EvoSkills](https://arxiv.org/abs/2604.01687) | ❌ | ✅ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ⚠️ | ❌ |
| nuwa-skill / [persona](https://github.com/migueldeguzman/persona) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| **`perpetuum`** (this) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

`perpetuum` is the only one with every column checked — the
combination is the point.

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
