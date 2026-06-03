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

## What each one actually does

### Pause

`trigger.sh` finishes the *current cycle* (does not interrupt mid-cycle
— prompts in flight complete normally), then enters a polling loop
that checks for `.paused` every 60 seconds. The middle CC TUI stays
alive in tmux, the inner cc-use session stays alive. Nothing is lost.

Resume removes the flag; on the next poll trigger.sh proceeds to the
next cycle. **Resume costs nothing.**

Use case: "I want to read the latest plan.md and write some inbox
items before the next cycle picks them up."

### Stop (graceful)

`trigger.sh` finishes the current cycle, checks the flag, exits
cleanly. The middle CC TUI and inner cc-use session are still alive
in tmux (they don't know trigger.sh stopped). plan.md / escalations.md
are in a clean state because the cycle finished.

To resume: just run `trigger.sh` again. It will reuse the middle
session if it's still there, otherwise start a fresh one. State is
in files; it picks up where it left off.

Use case: "I'm done for the week, stop cleanly. I'll restart
Monday."

### Kill (hard)

Just kill the process and optionally the tmux session. There may be a
half-written cycle, escalation, or commit. Usually the next launch
recovers because plan.md is mostly self-consistent and worst case
re-does a small piece of work.

Use case: "Something is wrong, just stop." (Or: process is wedged.)

## Natural language mapping

When the user talks to you ("Layer 4"), translate their language into
the right command. Map liberally:

| User says | You do |
|---|---|
| 暂停 / pause / stop for now / hold on | `touch .paused` |
| 继续 / resume / keep going / start again | `rm .paused` |
| 结束 / stop after this round / wrap up | `touch .stop_after_current` |
| 强制停 / kill it / 杀掉 / 停掉 | `pkill -f trigger.sh; tmux kill-session -t middle-<task>` |
| 重启 / start again / relaunch | `nohup .perpetuum/<task>/trigger.sh > /dev/null 2>&1 &` |
| 现在是暂停的吗?/ 跑着吗? | check both: `ls .paused 2>/dev/null` and `pgrep -f trigger.sh` |

For ambiguous wording ("停一下"), ask if they mean pause (resumable
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
