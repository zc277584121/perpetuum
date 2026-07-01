# Setup: initializing a new perpetuum task

This reference walks you through creating a new `.perpetuum/<task>/`
directory in the user's project. Read this when the user wants to
start a new task.

## Prerequisites checked already?

Before you reach this file, `SKILL.md` already had you confirm:
- `cc-use` skill is installed
- `tmux` is installed
- The task passes the **suitability gate**

If you skipped the suitability gate, go back to `SKILL.md` and walk
through it now. It is not optional.

## The suitability checklist (internal — don't recite this to the user)

Five dimensions. For each, decide silently whether the user's own
description already answers it. If not, and if the answer would
change how the task gets set up, ask about it — one question, in
your own words, fit to the task and the user's language. Don't read
this list to the user as a form, and don't ask a dimension whose
answer wouldn't change anything.

1. **Goal narrowness.** Is there a bounded scope, or is it "make this
   better" with no boundary? *Unresolved example: "watch for
   problems" — doesn't say what kind. Ask what categories of finding
   actually matter here.*
2. **Judgeable signal.** Is there something Layer 2 can grade —
   pass/fail, a number that moves, a diff a human could review? *If
   the user gives no criterion, ask what "done" or "better" looks
   like for one item.*
3. **Step granularity.** Does the task decompose into many small,
   independent units, or is it one atomic delivery? *If it sounds
   monolithic, ask whether it can be split — module-by-module,
   PR-by-PR, trial-by-trial.*
4. **Error tolerance.** Can a wrong Layer-1 step be caught and rolled
   back (a commit), or is a single mistake catastrophic (prod
   deploy, real email, money movement)? *If any step sounds
   irreversible, ask how it should be gated — PR instead of direct
   push, dry-run instead of a live call, etc.*
5. **Time horizon.** Does this need to run for hours or days across
   many cycles, or is it actually a 10-minute task? *If unclear, ask
   how long they expect this to take, or how many cycles they're
   picturing.*

Skip any dimension the user's first message already answers clearly.
Ask the remaining ones one at a time — never all five in one message,
and stop asking once the borderline cases (see `SKILL.md`) are
resolved either way.

## Step 1 — Pick an example as starting point

Look at `examples/` and find the closest match:

| User's task shape | Closest example |
|---|---|
| Find bugs, fuzz, scan for vulnerabilities, error UX gaps | `adversarial-testing/` |
| Watch GitHub issues/PRs/etc and act on them | `github-watcher/` |
| Match writing style to a reference corpus | `style-distill/` |
| Iteratively improve a single document | `article-polish/` |
| Scan codebase for logging/observability gaps | `observability-gap/` |

If nothing is an exact fit, pick the closest and adapt it during the
next steps. Do not write from scratch — examples encode many small
lessons (prompt structure, file conventions, sync mechanism).

## Step 2 — Decide on git worktree mode

Ask the user: are there other perpetuum tasks already running on this
project, or do they plan to run several in parallel?

- **No / just this one** → set up directly in the project root. Task
  files go in `<project>/.perpetuum/<task>/`. Commits go to the current
  branch.
- **Yes / multiple lines** → use git worktree. See
  `references/worktree.md` for the full procedure.

## Step 3 — Choose a task name

Suggest a short, hyphenated, English name based on what the task does.
The directory will be `.perpetuum/<task-name>/`. Examples:
`adversarial-testing`, `pr-watcher`, `style-distill-karpathy`,
`docs-polish`, `observability-audit`.

## Step 4 — Create the directory

```bash
mkdir -p <project>/.perpetuum/<task-name>/state
```

## Step 5 — Copy and adapt files from the example

For each file in the chosen example:

1. Copy to `.perpetuum/<task-name>/`
2. Customize. Specifically:
   - **`prompts/1_explore.md`** — rewrite to describe the task's actual
     scope. Use the example's structure (read history, plan new items,
     append to `plan.md`, write done-flag) but replace the task-specific
     instructions. Use the user's language.
   - **`prompts/2_execute.md`** — adjust the dispatch logic. The
     `cc-use delegate --project /abs/path --agent <agent-family> --replace`
     line must use the **absolute path** of the project (or the worktree
     path, if using worktrees). `--agent` should match the host
     coding-CLI agent the user is on (`claude`, `codex`, etc.). Always
     include `--replace` — without it, `cc-use` reuses the existing
     inner session by default, which silently breaks Layer 1's
     zero-priors invariant over the life of the task.
   - **`trigger.sh`** — see `references/trigger.md`. Adjust:
     - `AGENT_CMD` — defaults to Claude Code. For Codex CLI users,
       suggest exporting `AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox"`
       (or the safer `codex --full-auto`) before running. The trigger
       script picks it up from the environment, so no edit to the
       file itself is needed for users on other agents — but mention
       it explicitly so they know.
     - `MAX_ITER` (default 20, but reasonable for the task)
     - `SLEEP_BETWEEN_CYCLES` (default 120s = 2 min — full throttle;
       bump to 1800 or 3600 if the user has cost concerns)
     - `WAIT_PHASE_TIMEOUT` / `SILENCE_THRESHOLD`
     - `MIDDLE_SESSION` name (e.g. `middle-adv-<project-short>`)
     - Trigger type (schedule, conditional, webhook)
   - **`plan.md`** — start empty with `## Pending` and `## Done`
     sections.
   - **`inbox.md`** — start with the `## Pending` and `## Processed` (or
     English equivalent) skeleton.
   - **`escalations.md`** — start empty with `## Open` and `## Resolved`.
   - **`_meta.md`** — fill in:

```markdown
# Task metadata

- **task name**: <task-name>
- **created**: <ISO date>
- **worktree path**: <abs path>
- **branch**: <current git branch>
- **started from**: <branch>@<sha>
- **parent repo**: <abs path of parent repo>
- **merge target**: <branch>   (where the user wants to merge back, if applicable)
- **trigger type**: schedule | conditional | webhook
```

## Step 6 — Make `trigger.sh` executable

```bash
chmod +x .perpetuum/<task-name>/trigger.sh
```

## Step 7 — Suggest .gitignore

```bash
echo '.perpetuum/' >> <project>/.gitignore
```

…unless the user wants the perpetuum state tracked (team-shared usage,
historical record). Ask, then act.

## Step 7.5 — Confirm cost / rate-limit awareness explicitly

The default `SLEEP_BETWEEN_CYCLES` is **2 minutes** — designed for full
throttle. Before launch, walk through the cost implications with the
user out loud:

- One cycle ≈ several inner-agent dispatches via `cc-use` (the bulk of
  the spend) plus the middle agent's prompt 1 + prompt 2 turns
- At 2-minute cadence with `MAX_ITER=20`, the loop will burn through 20
  cycles in a few hours
- Ask:
  - "Do you have token budget / API quota for ~20 cycles at full
    cadence on this account?"
  - "Are you on a usage-based plan (cost matters) or a flat plan
    (rate limits matter)?"
  - "Will you babysit the first few cycles, or are you launching and
    walking away?"
- If they hesitate, suggest:
  - Bump `SLEEP_BETWEEN_CYCLES` to 1800 (30 min) or 3600 (1 hour)
  - Reduce `MAX_ITER` (e.g. start with 5)
  - Use the `github-watcher` style **conditional** trigger if their
    task is actually event-driven (only fires when there's real new
    work — much cheaper than schedule)

This is a one-minute conversation that prevents a "why did this cost
$X overnight" surprise. Do not skip it. Even users who said "yes I
understand the cost" once may not have understood the actual rate.

## Step 8 — Pre-flight: trial one cycle if the user is uncertain

For first-time users, suggest a quick trial run with `MAX_ITER=1`
before unleashing 20. After 1 cycle they can see whether the prompts
produced sensible output, then bump MAX_ITER back up.

```bash
# Temporarily set MAX_ITER=1
sed -i.bak 's/^MAX_ITER=.*/MAX_ITER=1/' .perpetuum/<task>/trigger.sh
.perpetuum/<task>/trigger.sh
# Inspect plan.md, escalations.md, the git log
# Restore
mv .perpetuum/<task>/trigger.sh.bak .perpetuum/<task>/trigger.sh
```

## Step 9 — Walk the user through the "after setup" briefing

This is the most important step. The user is about to leave a coding
agent unattended on their codebase. They need to understand the
contract. Walk through the five points listed in the SKILL.md
"After setup: what to tell the user" section — in their language.

Do not skip this. A user who doesn't know they can edit `inbox.md` or
touch `.paused` will end up `pkill`-ing the whole thing in panic at 3am.

## Step 10 — Launch (or hand off)

Two options. Ask the user which they prefer.

```bash
# A: launch now in background
nohup .perpetuum/<task>/trigger.sh > /dev/null 2>&1 &

# B: hand the launch command to the user, they start when ready
echo "When you're ready:  nohup .perpetuum/<task>/trigger.sh &"
```

## Common adjustments after first cycle

After cycle 1 the user often wants to tweak:

- **Done-flag reminder is not strong enough** in `prompts/2_execute.md` →
  raise the warning, put it at top *and* bottom of the prompt
- **Prompt 1 produces too many TODOs / too few** → adjust the
  Cartesian-product/dimension language
- **Layer 1 is "fixing" things you wanted reviewed first** → add a
  list of "must escalate, do not auto-fix" categories to `prompts/2_execute.md`
- **Layer 1 keeps trying the same blocked dimension** → add a "if
  category X has been BLOCKED before, skip" instruction to `prompts/1_explore.md`

These adjustments are normal. Make them with the user, don't push your
own preferences.
