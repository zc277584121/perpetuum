# Design notes: why perpetuum is shaped the way it is

This document is the long-form rationale. You don't need to read it
to use perpetuum. Read it if you're modifying the skill, designing a
new example, or trying to understand why certain decisions are
non-negotiable.

## Three core problems, three core solutions

This is the framing the whole project is organized around. Every
mechanism elsewhere in this doc either implements one of these three
solutions or supports one of them. (The README has the same framing
with ASCII diagrams; this section is the prose version for people
reading the design docs directly.)

### Problem 1 — Vague goal, wide operating space → drift

`/goal` and Ralph-style loops take whatever sentence the user typed
as the goal and give the agent unlimited interpretive freedom. With
nothing actively pulling the agent back to the main thread, or
vetting its mid-run output, it wanders off-target.

**perpetuum's answer (a two-part mechanism in Layer 2):**

- A **suitability gate** at setup forces a narrow, judgeable goal
  up front. Vague tasks get reshaped or rejected before init.
- Every cycle, Layer 2 runs two prompts: `prompts/1_explore.md`
  re-checks direction (where should we go next, what's still
  pending, are we drifting?) and `prompts/2_execute.md` dispatches
  Layer 1 work and judges the result before it can become a commit.
  The plan-then-judge cycle is what stops "fake progress" from
  accumulating.

This is the discriminator/generator separation from GANs, but
applied at the loop level rather than at the model level.

### Problem 2 — No continuation mechanism → one short run and done

`/goal` is single-session. Even "infinite loop" variants are blindly
time-triggered, no concept of event or condition. But real "do more
of this" work — find more bugs, fit a metric tighter, watch for new
PRs — needs the loop to span sessions, restarts, and different kinds
of trigger.

**perpetuum's answer (Layer 3):**

Layer 3 (`trigger.sh`) abstracts triggers into three families:

- `schedule` — every N minutes, run a cycle
- `conditional` — poll an external state (`gh pr list`, file watch,
  log alert) and only run when something changed
- `webhook` — react to event-driven input

All three feed the same Layer 2/Layer 1 stack. Arbitrarily many
cycles can then be stitched together on the time axis — across
sessions, machine reboots, days, weeks.

### Problem 3 — Human-in-the-loop is a wall → ambiguity freezes everything

Traditional loops have no way to keep going when they hit something
they can't decide alone. They guess wrong or stop and wait — and if
the user isn't at the terminal, "wait" means dead.

**perpetuum's answer (three async channels):**

- `escalations.md` — agent writes ambiguous decisions with A/B/C
  options to a queue. The user fills answers in when convenient.
  The loop never blocks; it notes "this one's escalated, moving on
  to the next" and continues.
- `inbox.md` — user pushes instructions in (SKIP, PRIORITIZE,
  DIRECTION, etc.) whenever they want. The next cycle's explore
  phase reads and applies them.
- **Layer 4** — the host coding agent the user is talking to. It
  monitors all the files, translates natural-language requests into
  file operations, and coordinates. The user doesn't have to know
  the file layout to drive the loop.

Git history doubles as the durability + audit log: the middle agent
judges each Layer-1 proposal before it becomes a commit, so rejected
outputs never enter history in the first place. The branch stays
clean and append-only.

### How the three solutions compose

```
narrow goal + Layer 2 plan/judge   ×   Layer 3 trigger abstraction   ×   async escalation + inbox + git
       (P1 solved)                          (P2 solved)                       (P3 solved)
       
       = actually perpetual
```

Remove any one of the three and the loop fails in a specific way:

- Without P1's solution, even with infinite triggers and async human
  support, the agent drifts and produces garbage forever.
- Without P2's solution, you have one safe high-quality run that
  ends. Not "perpetual".
- Without P3's solution, the first ambiguity freezes the loop and
  needs a human in the loop synchronously.

## The core invariant

**Every accepted finding becomes a local git commit.** Without this,
there is no ratchet. Without a ratchet, the loop has nothing to make
"progress" mean. Without "progress", you have Ralph Loop — which is
fine for short tasks but degenerates over long runs because there is
no rollback handle for bad changes.

Everything else in perpetuum exists to support this invariant safely:
- The three-layer split prevents the same agent from being judge and
  executor (which leads to "self-certifying" bad commits)
- The two-prompt sequence separates "what should we do next" from
  "do it and judge it" (which prevents premature commits during
  planning)
- The escalation channel handles cases where committing would be
  premature (the agent doesn't know, only the human does)
- The pause / stop signals let the user inspect state without
  damaging the ratchet history

## Eight supporting ideas

The three solutions above are perpetuum's reason to exist. The
implementation borrows from eight smaller, already-named ideas. None
is original to perpetuum; what's original is how they're combined to
make the three solutions practical to run.

| # | Idea | Where it shows up in perpetuum |
|---|---|---|
| 1 | Discriminator / Generator separation (GANs) | Layer 2 judges, Layer 1 generates. They never share context. **Implements P1's judge half.** |
| 2 | Monotonic ratchet | Every Done item is a commit. plan.md `[x]` is append-only by convention. **Safety net for P3 (off-track steps undone silently).** |
| 3 | Three-layer architecture (stupid → smart → stupid) | trigger.sh is dumb, middle is smart, inner is dumb. **The structural shape of P1 + P3 together.** |
| 4 | Exploration vs Exploitation prompt split | `prompts/1_explore.md` plans, `prompts/2_execute.md` does. **Implements P1's plan half.** |
| 5 | File-based persistent memory | plan.md + inbox.md + escalations.md + git log. No vector DB needed for this working set — small enough to re-read in full each cycle. Optional vector-retrieval memory (e.g. [MemSearch](https://github.com/zilliztech/memsearch)) can plug in alongside it for broader personal history. **Enables P2 (state survives triggered cycles) and P3 (async channels are just files).** |
| 6 | Asynchronous human escalation | escalations.md never blocks the loop. New cycles still run. **Implements P3's escalations channel.** |
| 7 | Trigger abstraction | schedule / conditional / webhook are all valid Layer 3 implementations. Same Layer 2/1. **Implements P2.** |
| 8 | File-as-contract | Who can edit which file is a convention, not enforcement. Cleaner than role-based access. **Makes P3's shared-file channels safe in practice.** |

Removing any one of these breaks something:

- Remove (1) → middle agent self-certifies; quality drops over time
- Remove (2) → no rollback; bad commits accumulate; can't tell progress from noise
- Remove (3) → middle agent's context bloats with execution noise; long runs degrade
- Remove (4) → planning and execution mix; agent commits during planning, or plans during execution
- Remove (5) → state lost across sessions; restart loses everything
- Remove (6) → human must be online; loop stops whenever a tough question appears
- Remove (7) → can't adapt to event-driven tasks; only schedule works
- Remove (8) → users edit plan.md mid-cycle; race conditions; format drift

## Architecture as inheritance

```
Ralph Loop:           bash while + single prompt
                              ↓
                          add ratchet
                              ↓
recursive-improve:    improve → run → eval → keep or revert
                              ↓
                          add file-contract + frozen evaluator
                              ↓
Karpathy AutoResearch: 3 files (one frozen) + scalar metric + git ratchet
                              ↓
                          add: judge/executor separation
                          add: human escalation
                          add: trigger abstraction
                          add: exploration/exploitation split
                              ↓
                       Perpetuum
```

Each step adds something the previous lacked. None of the prior art
combines all eight pieces.

## Why "perpetual" is ironic

Physics: perpetual motion machines are impossible.

This skill: the loop *does* stop — when MAX_ITER is hit, when the user
sends graceful stop, when token budget runs out, when the host machine
reboots. What it gives you is *continuity of state across stops*.

A perpetuum task can be paused at noon, resumed at 11pm, killed in a
crash recovery, and relaunched the next morning — and the next cycle
picks up exactly where it left off, because state is files and git.

That's the actual product. The "perpetual motion" framing is the marketing.

## Why two prompts, not one, not three

### Why not one

If prompt 1 and prompt 2 are merged, the middle agent will sometimes
plan-then-execute mid-thought (good when it works, terrible when it
commits something that wasn't fully planned). The hard split forces
"plan everything that's going in `plan.md` Pending → stop → execute
from Pending only".

### Why two is the default

`prompts/1_explore.md` and `prompts/2_execute.md` cover the two cognitive modes:
divergent (what could be done) and convergent (do what's in the plan).
The middle agent switches mode cleanly because they are physically
different prompts pasted into the TUI at different times.

### When three (or more) helps

If your task has a distinct *reflection* phase ("look at what was done
this cycle, identify patterns, adjust `plan.md` for next cycle"), add
`3_reflect.md`. trigger.sh picks it up automatically (lexical sort of
`prompts/[0-9]*_*.md`).

If your task has a distinct *check-the-world* phase before exploring
(e.g. "fetch GitHub PR list and write it to inbox before planning"),
add `1.5_check.md` or `0_fetch.md`.

The general rule: each phase should be **atomic and have a clear
question it answers**. Don't add a phase just for the sake of structure.

## Why agents must always re-read plan.md at cycle start

Layer 2 is a persistent CC TUI. Its conversation context accumulates
across cycles. Without forced re-reads, it would rely on "I remember
from earlier we decided to skip postgres" — which is fragile if the
user edited plan.md or inbox.md between cycles.

The two prompt templates explicitly say "read plan.md / inbox.md /
escalations.md history" at the start. This makes the agent's behavior
**deterministic on file state**, not on conversation memory. This is
the same trick Ralph Loop uses (fresh context every cycle); perpetuum
gets most of the benefit without paying the cold-start cost every
cycle.

## Why .perpetuum/ is dot-prefixed

- Hidden from `ls` by default — reduces clutter in user's project view
- Signals "machine-managed directory, not human-managed source"
- Easy to `.gitignore` (`.perpetuum/`) without affecting anything else
- Mirrors `.git/`, `.cc-use/`, etc — established UNIX convention

## Why we trust silence as a fallback sync signal

The done-flag is the primary sync. Silence (20 min tmux pane unchanged)
is the fallback. The total timeout is the safety net.

Three layers because **the agent sometimes forgets to write the flag**.
First-cycle prompts in our own dogfooding showed this: the agent
finishes the work, returns to the prompt waiting state, and never
runs the final `echo > .cycle_done_*` command. Silence catches this.
Total timeout catches the case where everything wedges.

Without silence fallback, every forgotten flag means a 6-hour stall.
Without total timeout, a real wedge means infinite hang. Without the
flag, every cycle pays the 20-minute silence wait even when work
finishes in 5 minutes.

All three are needed. None is redundant.

## What perpetuum is not

- Not a model-level optimizer (use Darwin Gödel for that)
- Not a skill-evolution framework (use EvoSkills for that)
- Not a persona-distillation skill (use nuwa for the one-shot version,
  or build a perpetuum task with style-distill as its goal for the
  iterative version)
- Not a CI/CD replacement (perpetuum can call CI, but doesn't replace it)
- Not a benchmark runner (although it can run benchmarks; see
  Karpathy AutoResearch for the cleaner-shaped solution to that)
- Not a substitute for the user thinking about their problem. The
  suitability gate exists because perpetuum on the wrong task is
  just an expensive way to burn tokens.

## Open design questions

These are real and unresolved. Don't hide them from advanced users.

1. **Local-optima trap.** The ratchet is greedy. If `prompts/1_explore.md`'s
   "breadth vs depth balance" guidance fails, the agent will dig the
   same well over and over. Mitigations: explicit category-switch
   directives in inbox; periodic human review; running multiple tasks
   on different worktrees with different priors.
2. **Inner agent priors.** Layer 1 has *some* prior from training, even
   without conversation context. For tasks where neutrality matters
   (e.g. fairness audits), this is a limit. Mitigations: prompt
   instructions, multiple Layer 1 dispatches with different framings.
3. **Reward hacking.** If you wire `plan.md` Done count to a reward
   signal anywhere, the agent will optimize for that count. Don't.
   Keep oracle and incentive structurally separate.
4. **Sync edge cases.** Network blips, tmux respawns, token-limit
   pauses all cause sync glitches. The three-layer sync handles most.
   We learn new edge cases as we run more tasks.
