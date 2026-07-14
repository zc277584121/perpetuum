# perpetuum ♾️

> Loop engineering for coding agents, done production-grade — a
> perpetual-motion engine, not a thought experiment.

> 🧬 **What this actually is — a Skill, not a script.** `perpetuum`
> ships as an [Agent Skill](https://skills.sh): a small set of
> architectural ideas, prompt templates, trigger patterns, and a
> handful of working examples. When you say "use perpetuum to do X",
> your coding agent picks the closest example, **rewrites the prompts
> and `trigger.sh` for your specific task in your own language**,
> confirms what's tunable with you, then launches. The bash and the
> prompts inside aren't fixed code — they're starting points the
> agent edits to fit your case. That's why ~1 kLOC of plumbing ends
> up flexible enough for tasks as different as ML training sweeps,
> per-PR review, adversarial testing, and style polish: **the
> architecture is fixed, the implementation is generated to fit**.

## 🛑 Why your `/goal` runs go nowhere

You've probably tried `/goal` in Claude Code or Codex, or wired up a
Ralph Loop. What happens, every time: either it runs for a few minutes
and just stops, or it drifts off the main thread and keeps needing you
to step in for decisions.

That's not perpetual. That's just "unattended for 20 minutes."

Designing a system that actually holds up — instead of just wiring a
prompt to a scheduler — is what people are starting to call **loop
engineering**. Most attempts at it stop at exactly this wall.

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

But a trigger that fires into an empty queue is just a heartbeat
with nothing to do — perpetual *timing* isn't perpetual *substance*.
That's the other half of the mechanism, easy to miss: every cycle's
**explore** phase doesn't just recheck direction, it appends
newly-discovered work to `plan.md`'s Pending list — new test angles,
new follow-ups, new edge cases the last cycle's result surfaced. So
execution both drains the queue and refills it in the same breath.
Without that, a trigger firing on schedule forever would just
rediscover an empty todo list a few cycles in and idle — "still
running" but with nothing left to do.

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
             plan.md isn't just read each cycle, it's refilled: explore
             adds new Pending items as fast as execute drains them —
             the trigger keeps *timing* perpetual, this keeps it *fed*.
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

🐛 **Adversarial bug-hunting on a CLI tool**

```text
Use perpetuum to run continuous adversarial testing against this CLI
for the next 30 cycles. Categories I care about: auth, parser, error
paths. Open A/B/C when a failure mode is ambiguous.
```

📥 **GitHub issue triage on a busy repo**

```text
Use perpetuum to watch this repo's GitHub issues and triage new ones
every hour. Tag them, suggest labels, escalate only the ones that
need a product decision.
```

👁️ **Observability gap discovery in a service module**

```text
Use perpetuum to keep finding observability gaps in the worker module
for ~20 cycles, then stop and let me review. Commit each gap-fix as
a separate commit so I can cherry-pick.
```

✍️ **Style transfer toward a target author's voice**

```text
Use perpetuum to iteratively polish this draft article toward
Karpathy's writing style. His articles are in target_corpus/. Use BLEU
+ readability + a stylistic-similarity LLM judge as the metric. Stop
when the metric plateaus for 5 cycles.
```

🧪 **ML hyperparameter sweep / overnight training run**

```text
Use perpetuum to keep training this LoRA overnight. Each cycle, pick
one hyperparameter to vary (lr, rank, dropout, batch size), kick off
a short training run, eval on the val set, record val loss + a sample
generation. Stop after 50 trials or when val loss hasn't improved for
10 cycles. Commit one row to results.csv per trial. Cap each
hyperparameter's range up front and keep the val set off-limits to
the loop — that's how this kind of sweep avoids local-optimum
dead-ends and metric-hacking shortcuts.
```

🚦 **CI failure triage on the main branch**

```text
Use perpetuum to watch CI on the main branch. When a build fails,
diagnose, propose a fix, commit it to a fix/<short-name> branch, and
open a PR. Don't push to main directly. Run on the webhook trigger.
```

🔍 **Per-PR security risk review**

```text
Use perpetuum to comb every PR in this repo for security-relevant
diffs (auth, secrets, network). For each PR write a one-paragraph
risk note. Run on the conditional trigger — only spin up when a new
PR arrives.
```

🔁 **Long, mechanical migration across a large codebase**

```text
Use perpetuum to migrate every call site of `old_api.call(...)` to
`new_api.call(..., context=...)` in this repo. One module per cycle:
read it, edit the call sites, run that module's tests, commit. Skip
test files for now. Open A/B/C if a call site has non-trivial
side-effect semantics.
```

After you describe a task this way, the skill walks you through a
short back-and-forth — what "done" looks like for your case, how
often to run, where to commit, which decisions to auto-make vs
escalate — and only launches once both sides agree. The first
message is a request; the actual config is nailed down in that gate
before any cycles burn tokens.

The list above isn't exhaustive. **Anything that fits the criteria
below — narrow goal, judgeable signal, many small steps, etc. — is a
candidate, even if it has nothing to do with code:** literature
reviews that compound over days, dataset curation, slow translation
of a large doc, long-form prompt tuning, anything where "a little
more, every hour" is what you want.

### Why these tasks fit

The pattern they share:

- **A clear, narrow goal**, not "make this project better". *e.g. the
  adversarial example names auth / parser / error paths; the ML sweep
  names which 4 hyperparameters to vary; the migration names one
  exact call-site pattern.*
- **A judgeable signal** — pass/fail, a number that moves, a diff
  someone can review. Without one, the ratchet has nothing to ratchet
  on. *e.g. CI watcher uses build status; ML sweep uses val loss;
  style polish uses BLEU + LLM judge; migration uses module-level
  test pass.*
- **Many small steps**, not one big atomic delivery — perpetuum's
  advantage compounds over cycles. *e.g. 30 adversarial cycles, 50
  hyperparameter trials, one PR scanned per arrival, one module
  migrated per cycle.*
- **Tolerance for the inner agent being wrong sometimes** — the
  outer judge catches it, but if a single wrong step is catastrophic
  (e.g. deploying to prod), this is the wrong tool. *e.g. the CI
  watcher fixes go through a PR, never `git push` to main; migration
  commits are per-module, easy to revert.*
- **Either the work itself takes a long time, or you want to do a
  small step many times over many days.** A 10-minute task doesn't
  need perpetuum; a 10-cycle task across a long weekend does. *e.g.
  ML sweeps span overnight, PR review compounds as PRs arrive over a
  week, migration may take days of small commits.*

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
in the same order.

1. **Ralph Loop, generalized — the heartbeat that keeps things
   moving.** The original [Ralph Loop](https://ghuntley.com/loop/)
   is the simplest possible "keep moving" engine: a `while true` in
   a shell script that re-prompts the agent over and over. That
   infinite-loop instinct is the raw driving force behind anything
   "perpetual" — without it, you get one response and you stop.
   perpetuum's Layer 3 is that same heartbeat, but generalized to
   three trigger families instead of just one: **schedule** (the
   Ralph default — every N minutes), **conditional** (poll an
   external state like `gh pr list` and only fire on real change),
   **webhook** (react to incoming events). Same Layer 2 / Layer 1
   stack behind all three. This is what lets one skill cover both
   "spin up every hour" and "spin up when a PR arrives" without
   rewriting the inner loop.

2. **Discriminator / Generator separation** (from GANs). Layer 2 is
   the discriminator — it sees the entire history, judges every
   proposal, but does not run code itself. Layer 1 is the generator —
   fresh context every dispatch, runs the actual operation, has no
   memory of what came before. Because they share no context, neither
   can fake a result the other would accept. This is what kills the
   self-certifying failure mode in `/goal` and Ralph Loop, where the
   same agent both produces and grades — over a long run, that
   collapses into "everything is fine, keep going".

3. **Asynchronous human escalation — the thing that makes "perpetual"
   actually perpetual.** When Layer 2 hits an ambiguous decision
   (off-by-one semantics, naming convention, product call) it writes
   A/B/C options to `escalations.md ## Open` and **moves on to the
   next item in the same cycle**. The human answers later, whenever
   convenient. The loop never blocks waiting for a reply. Without
   this, the first hard question you hit while you're asleep stops
   the whole engine until you wake up; with it, the loop runs through
   the night, builds a small queue of decisions waiting for you, and
   keeps producing on everything that isn't blocked. This is the
   single feature most other autonomous-loop projects don't have, and
   it's the difference between "runs unattended for 20 minutes" and
   "runs unattended for a week".

4. **Monotonic ratchet** via local `git commit`. Layer 2 judges every
   Layer 1 proposal *before* it becomes a commit — rejected ones
   never enter history. Accepted ones land as a clean append-only
   sequence on the branch, and `git log` doubles as the durability
   mechanism across sessions, machines, and reboots. Without a
   ratchet, you can't tell progress from noise on a long run.

5. **Exploration vs Exploitation split** at the prompt level.
   Phase 1 (`prompts/1_explore.md`) is divergent — re-read state,
   re-check direction, queue new pending items. Phase 2
   (`prompts/2_execute.md`) is convergent — work down the queue,
   one item at a time, commit or escalate. Fusing them into one
   prompt is what makes long Ralph-style runs drift — but it's also
   what keeps the run *perpetual* in substance, not just in timing:
   Phase 1 adds to `plan.md`'s Pending list every cycle, Phase 2
   drains it, so the backlog is replenished as fast as it's consumed
   instead of running dry a few cycles into a long trigger schedule.

6. **File-based persistent memory, no vector DB required for the
   loop's own state.** plan / inbox / escalations + the git log are
   the entire memory system Layer 2 needs to keep the loop itself
   running — this working set is small enough to re-read in full
   every cycle, so it never needs an embedding store. Layer 2
   re-reads these files at the start of every cycle, so context rot
   stays bounded and state survives any restart — pause at noon,
   resume at midnight, next cycle picks up exactly where the last
   one left off.

   If you want the explore phase to also draw on a much larger pool
   of history — this person's past decisions and style across other
   work, not just this loop's own backlog — that's a different,
   optional layer. A memory-search tool with vector retrieval (e.g.
   [MemSearch](https://github.com/zilliztech/memsearch)) can plug in
   alongside the file-based core for that, not instead of it.

7. **Architectural decoupling and responsibility separation.** Each
   layer owns one well-defined job: Layer 3 owns "keep ticking",
   Layer 2 owns "judge and dispatch", Layer 1 owns "do one bounded
   piece of work in fresh context". **Inside** each layer the
   implementation is freely swappable — Layer 3 could be `trigger.sh`,
   cron, a GitHub Actions runner, or a Lambda; Layer 2 could be
   Claude Code, Codex, Cursor, or another coding-agent TUI; Layer 1
   could be any `cc-use`-supported agent. The interfaces between
   layers (file state, tmux paste, `cc-use delegate`) are what stays
   stable; everything else is interchangeable. This is why the same
   small skill stays lightweight yet handles wildly different
   scenarios — the **architecture is the contract**, the pieces inside
   are not.

8. **File-as-contract.** Who can edit which file is a convention,
   not enforced by code: agent owns `plan.md`, human owns `inbox.md`,
   both touch `escalations.md` at different sections. Cleaner than
   role-based access control, debuggable with `cat`, mergeable with
   `git`.

9. **Host-agnostic dispatch, no vendor lock-in.** Because perpetuum
   ships as an [Agent Skill](https://skills.sh) — a few hundred lines
   of bash plus prompt templates, not a service or a framework — it
   stays **lightweight and host-agnostic by construction**. The
   actual coding agent is loaded at runtime via
   [`cc-use`](https://github.com/zc277584121/cc-use), which speaks
   Claude Code, Codex CLI, Cursor, Windsurf, Gemini CLI, Goose, and
   40+ other coding-agent CLIs. A task started in one host can be
   picked up later in another, because nothing in the skill is bound
   to a specific agent's SDK, API, or proprietary protocol — the
   state is just files on disk. **No vendor lock-in.** This matters
   because coding agents move fast — flags get renamed, pricing
   changes, models deprecate. You don't want your "always running"
   infrastructure to die the day your preferred CLI ships a breaking
   change.

Removing any one of these breaks something. See
[`skills/perpetuum/references/design.md`](skills/perpetuum/references/design.md)
for the long-form rationale on each.

## 📊 Loop engineering: comparison with related projects

| Project | trigger abstraction | disc/gen split | async human | ratchet | explore/exploit split | persistent memory | multi-layer | file contract | Claude+Codex |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Claude Code [plan mode](https://code.claude.com/docs/en/plan-mode) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Codex `/plan` mode | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| Claude Code [`/goal`](https://code.claude.com/docs/en/goal) | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Codex [`/goal`](https://github.com/openai/codex) | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| Claude Code [`/loop`](https://code.claude.com/docs/en/scheduled-tasks) | ⚠️ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| [`goalbuddy`](https://github.com/tolibear/goalbuddy) | ❌ | ❌ | ❌ | ⚠️ | ⚠️ | ✅ | ❌ | ✅ | ✅ |
| [`OpenSpec`](https://github.com/Fission-AI/OpenSpec) | ❌ | ❌ | ❌ | ❌ | ⚠️ | ✅ | ❌ | ✅ | ✅ |
| [Ralph Loop](https://ghuntley.com/loop/) | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ | ❌ | ❌ | ⚠️ |
| [`loop-engineering`](https://github.com/cobusgreyling/loop-engineering) | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ | ✅ | ⚠️ | ❌ | ✅ |
| [`recursive-improve`](https://github.com/kayba-ai/recursive-improve) | ❌ | ❌ | ❌ | ✅ | ❌ | ⚠️ | ❌ | ❌ | ❌ |
| [Karpathy AutoResearch](https://github.com/karpathy/autoresearch) | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| [EvoSkills](https://arxiv.org/abs/2604.01687) | ❌ | ❌ | ❌ | ✅ | ⚠️ | ⚠️ | ❌ | ⚠️ | ❌ |
| [`nuwa-skill`](https://github.com/alchaincyf/nuwa-skill) | ❌ | ⚠️ | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ✅ |
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
