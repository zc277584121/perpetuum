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
| **Killed (hard)** | `pkill -f trigger.sh` then `tmux kill-session -t '=middle-<task>'` | relaunch trigger.sh |
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

### Apply configuration changes after the current cycle

`trigger.sh` reads shell configuration such as cadence and iteration limits when
the process starts. To change those values without interrupting a cycle, wait on
the scheduler guard PID, not a tmux session-name prefix:

```bash
TASK=.perpetuum/<task>
touch "$TASK/.stop_after_current"
PID=$(cat "$TASK/scheduler.guard/pid")
while kill -0 "$PID" 2>/dev/null; do sleep 5; done
rm -f "$TASK/.stop_after_current"
nohup "$TASK/trigger.sh" > /dev/null 2>&1 &
```

The scheduler guard PID is the trigger process identity. Use it for process
lifecycle checks. When a tmux session check is needed, use an exact target such
as `tmux has-session -t "=$NAME"`.

### Kill (hard)

Just kill the process and optionally the tmux session. There may be a
half-written cycle, escalation, or commit. Usually the next launch
recovers because plan.md is mostly self-consistent and worst case
re-does a small piece of work.

Use case: "Something is wrong, just stop." (Or: process is wedged.)

### Done (full cleanup)

Normal cycles kill the middle CC TUI after each cycle, but hard stops,
crashes, or manual experiments can still leave stale sessions. Full cleanup
removes those leftovers when the user is genuinely finished — this is a
distinct state, not just a harder version of "kill":

```bash
pkill -f trigger.sh
tmux kill-session -t '=middle-<task>'
```

Then use the `cc-use` skill to close only the uniquely named Layer-1 sessions
created for this perpetuum task. Do not infer a project-wide default session or
close sessions owned by another task or by ad hoc cc-use work.

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
| kill it / force stop | `pkill -f trigger.sh; tmux kill-session -t '=middle-<task>'` |
| I'm done with this for good / clean everything up | full cleanup — see "Done (full cleanup)" above; close only the named Layer-1 sessions owned by this task |
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
echo "middle tmux:        $(tmux has-session -t '=middle-<task>' 2>/dev/null && echo alive || echo dead)"
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
