# Control: pause / resume / stop / kill

Read this when the user wants to control a running perpetuum task —
pause it, resume it, stop it gracefully, or kill it.

## The four control states

All control is done by **file signals** plus standard process / tmux
commands. No new protocol, no message bus, no API.

| State | How to enter | How to leave |
|---|---|---|
| Running | (default after launch) | any of below |
| **Paused** | `touch .perpetuum/<task>/.paused` | `rm .perpetuum/<task>/.paused` |
| **Stopped (graceful)** | `touch .perpetuum/<task>/.stop_after_current` | (process exits naturally; relaunch trigger.sh to resume) |
| **Killed (hard)** | `pkill -f trigger.sh` then `tmux kill-session -t middle-<task>` | relaunch trigger.sh |
| **Done (full cleanup)** | see below | can't — this is the end of this task's line |

## What each one actually does

### Pause

`trigger.sh` finishes the *current cycle* (does not interrupt mid-cycle
— prompts in flight complete normally), then enters a polling loop
that checks for `.paused` every 60 seconds. The per-cycle middle CC TUI
is normally cleaned up at cycle end; state is preserved in files. Nothing
is lost.

Resume removes the flag; on the next poll trigger.sh proceeds to the
next cycle. **Resume costs nothing.**

Use case: "I want to read the latest plan.md and write some inbox
items before the next cycle picks them up."

### Stop (graceful)

`trigger.sh` finishes the current cycle, checks the flag, exits
cleanly. The per-cycle middle CC TUI is normally killed at cycle end.
`plan.md` / `escalations.md` are in a clean state because the cycle
finished.

To resume: just run `trigger.sh` again. State is in files; it picks up
where it left off and starts a fresh middle session for the next cycle.

Use case: "I'm done for the week, stop cleanly. I'll restart
Monday."

### Kill (hard)

Just kill the process and optionally the tmux session. There may be a
half-written cycle, escalation, or commit. Usually the next launch
recovers because plan.md is mostly self-consistent and worst case
re-does a small piece of work.

Use case: "Something is wrong, just stop." (Or: process is wedged.)

### Done (full cleanup)

Normal cycles kill the middle CC TUI after each cycle, but hard stops,
crashes, or manual experiments can still leave stale middle or inner
`cc-use` sessions in tmux. Full cleanup removes those leftovers when the
user is genuinely finished — this is a distinct state, not just a harder
version of "kill":

```bash
pkill -f trigger.sh
tmux kill-session -t middle-<task>
tmux kill-session -t ccu-<project-name>   # cc-use's Layer 1 session — same
                                           # derivation cc-use itself uses:
                                           # session_name_for_project(project, agent)
```

**Only kill the `ccu-*` session if you're sure nothing else needs that
project's inner session for continuity** — `cc-use`'s own default is to
keep it alive indefinitely across unrelated future work on the same
project. If the user has other tasks or ad hoc `cc-use` usage on the
same project, leave it and only kill stale middle sessions.

Use case: "This task is done for good — PR merged, moving on, clean up
everything." Not the same as "pause" or "stop for now."

## Natural language mapping

When the user talks to you ("Layer 4"), translate their language into
the right command. Map liberally:

| User says | You do |
|---|---|
| pause / stop for now / hold on | `touch .paused` |
| resume / keep going / start again | `rm .paused` |
| stop after this round / wrap up | `touch .stop_after_current` |
| kill it / force stop | `pkill -f trigger.sh; tmux kill-session -t middle-<task>` |
| I'm done with this for good / clean everything up | full cleanup — see "Done (full cleanup)" above; confirm before killing the `ccu-*` session, it may be shared with other work on the same project |
| start again / relaunch | `nohup .perpetuum/<task>/trigger.sh > /dev/null 2>&1 &` |
| is it paused? / is it running? | check both: `ls .paused 2>/dev/null` and `pgrep -f trigger.sh` |

For ambiguous wording ("stop"), ask if they mean pause (resumable
in seconds) or graceful stop (resumable later, but needs relaunch).

## How to confirm state

Quick read-only check:

```bash
TASK=.perpetuum/<task>
echo "trigger.sh running: $(pgrep -f $TASK/trigger.sh | head -1 || echo no)"
echo "paused flag:        $(test -f $TASK/.paused && echo yes || echo no)"
echo "stop flag:          $(test -f $TASK/.stop_after_current && echo yes || echo no)"
echo "middle tmux:        $(tmux has-session -t middle-<task> 2>/dev/null && echo alive || echo dead)"
echo "last log line:      $(tail -1 $TASK/trigger.log)"
```

Use this when the user asks "is it running?" or "what state is it in?"

## When multiple tasks exist

If the user has multiple perpetuum tasks (e.g. one per worktree),
their natural-language reference is often ambiguous: "pause the
testing one". Clarify by listing what's actually running:

```bash
ls -1 .perpetuum/*/trigger.sh 2>/dev/null | while read t; do
  TD=$(dirname "$t")
  echo "- $(basename $TD): $(pgrep -fc $t > /dev/null && echo running || echo not running)"
done
```

…then ask which one they meant.
