# Status: inspecting a running task

Read this when the user asks "how's it going?" or invokes
this skill with no arguments.

## Default behavior when invoked with no arguments

If the user invokes the skill with no specific instruction, treat it as
"report current status". That means:

1. List all perpetuum tasks in the current project (or all known
   locations)
2. For each, report:
   - is `trigger.sh` running?
   - is it paused?
   - which cycle is it on?
   - how many Done items in plan.md, how many Pending?
   - how many unresolved escalations?
   - last commit?
3. Surface any **unanswered escalations** prominently — those are
   things only the human can move forward.

Keep the summary short. Detail on demand.

## Status-gathering commands (read-only, do not disturb)

```bash
TASK=.perpetuum/<task-name>

# Process state
pgrep -af "$TASK/trigger.sh" | head -1
test -f $TASK/.paused && echo "PAUSED" || echo "not paused"
test -f $TASK/.stop_after_current && echo "STOP REQUESTED"

# Where are we
tail -20 $TASK/trigger.log

# Plan summary
echo "Pending: $(grep -c '^- \[ \]' $TASK/plan.md)"
echo "Done:    $(grep -c '^- \[x\]' $TASK/plan.md)"
echo "Esc'd:   $(grep -c '^- \[→\]' $TASK/plan.md)"

# Escalations to show the human
awk '/^## Open/,/^## Resolved/' $TASK/escalations.md

# Recent commits
git -C <project-root> log --oneline -10
```

## Looking inside the loop (without disturbing it)

If the user wants to see *what the agent is actually thinking* right now:

```bash
# Attach read-only to the middle CC TUI if a cycle is currently running
tmux attach -t '=middle-<task>' -r

# Or just snapshot the current screen
tmux capture-pane -t '=middle-<task>:' -p

```

Inspect the uniquely named Layer-1 session reported by the current execute
phase through the cc-use skill.

**Important: `tmux attach -r` (read-only) is safe.** Without `-r`, you
would steal the active client and the agent would notice (cursor
position changes, etc.). Always use `-r`.

## Producing a readable summary for the user

When reporting back, structure it like this:

```
## adversarial-testing
Running (cycle 13/20, sleeping until ~06:35)
- Plan: 47 Done / 12 Pending / 2 Escalated
- Commits since start: 18
- ⚠ 2 unanswered escalations:
  - (cycle 4) ambiguous CLI flag off-by-one — A: align to 1-based / B: 0-based / C: leave
  - (cycle 8) tool semantics — A: literal match / B: rename verb / C: dual verb
- Last log line: "execute done 13-1780464144e"
```

Lead with **what needs the user's attention** (escalations), then the
running stats, then logs/commits. The user might only read the top line.

## When a task looks stuck

If a cycle has been running far longer than expected:

| Symptom | Probable cause |
|---|---|
| `trigger.log` last line is "waiting for done flag" for hours | Layer 1 may still be running a long task; check the tmux snapshot |
| Last log line is hours old, no new log entry | trigger.sh might have crashed; `pgrep -f trigger.sh` to confirm |
| Many cycle_done residual flags in `state/` | sync got desynchronized; manual `rm` and relaunch is usually fine |
| `tmux has-session` returns no for middle session | normal while sleeping between cycles; if trigger.log says a cycle is active, the middle CC died and the in-flight cycle should be relaunched |

Recovery is almost always: **stop, delete stale signals, relaunch.**
State is in files; loss of in-flight cycle costs one round of work, not
the whole project.
