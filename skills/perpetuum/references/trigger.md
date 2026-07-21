# Trigger: writing trigger.sh per task

Read this when adapting `trigger.sh` for a new task or task type. Each
task has its own `trigger.sh` — the skill doesn't enforce one shape,
it provides building blocks and example patterns.

## Three trigger types

| Type | When to use | Sketch |
|---|---|---|
| **schedule** | "every N minutes, run a cycle" (default) | `for i in $(seq 1 N); do run_cycle; sleep INTERVAL; done` |
| **conditional** | "check a state, run a cycle if it changed" (GitHub PRs, file watches, log alerts) | `while true; do CHECK or skip; run_cycle; sleep POLL_INTERVAL; done` |
| **webhook** | "external service pushes events, react immediately" (CI hook, Slack callback) | `socat / netcat tiny listener that writes to a queue; queue drainer runs cycles` |

For most tasks `schedule` is correct. Use the others only when the
task is genuinely event-driven.

## Common skeleton (all types share this)

```bash
#!/usr/bin/env bash
set -uo pipefail

# === Configuration (top of file, plain shell vars, no YAML) ===
PROJECT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
MIDDLE_SESSION="middle-<UNIQUE_TAG>"
MIDDLE_SESSION_TARGET="=$MIDDLE_SESSION"
MIDDLE_PANE_TARGET="=$MIDDLE_SESSION:"
SCHEDULER_GUARD_DIR="$TASK_DIR/scheduler.guard"

# tmux normally accepts unique session-name prefixes. The leading `=` forces
# an exact session match; the trailing `:` addresses that session's active pane.
# Keep the plain name only for `new-session -s`, which creates the session.

# Inner-agent command for Layer 2. Layer 2 is created fresh for each cycle with
# this fixed session name, then killed after the cycle. Default = Claude Code,
# permissions bypassed. Override for other coding-CLI agents:
#   Codex CLI:  AGENT_KIND=codex
#               AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox"
#               or (safer) AGENT_CMD="codex --full-auto"
#   Cursor, Windsurf, etc.: AGENT_CMD="whatever-starts-your-agent"
AGENT_KIND="${AGENT_KIND:-claude}"
AGENT_CMD="${AGENT_CMD:-claude --dangerously-skip-permissions}"

MAX_ITER=20
SLEEP_BETWEEN_CYCLES=120         # 2 min default — adjust based on cost tolerance
WAIT_PHASE_TIMEOUT=3600        # per-prompt-phase total timeout
SILENCE_THRESHOLD=1200         # tmux pane silent for this long = done
POLL_INTERVAL=30
TUI_BOOT_WAIT=25

LOG="$TASK_DIR/trigger.log"

# === Shared helpers ===
log()   { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

acquire_scheduler() {
  if mkdir "$SCHEDULER_GUARD_DIR" 2>/dev/null; then
    printf '%s\n' "$$" > "$SCHEDULER_GUARD_DIR/pid"
    return 0
  fi

  local existing_pid=""
  [ -f "$SCHEDULER_GUARD_DIR/pid" ] && existing_pid="$(cat "$SCHEDULER_GUARD_DIR/pid" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && ! kill -0 "$existing_pid" 2>/dev/null; then
    rm -rf "$SCHEDULER_GUARD_DIR"
    mkdir "$SCHEDULER_GUARD_DIR"
    printf '%s\n' "$$" > "$SCHEDULER_GUARD_DIR/pid"
    return 0
  fi

  log "another trigger.sh instance is already running for this task; exiting"
  exit 0
}

release_scheduler() {
  rm -f "$SCHEDULER_GUARD_DIR/pid"
  rmdir "$SCHEDULER_GUARD_DIR" 2>/dev/null || true
}

start_middle_session() {
  if tmux has-session -t "$MIDDLE_SESSION_TARGET" 2>/dev/null; then
    log "Removing stale $MIDDLE_SESSION before starting a fresh cycle"
    tmux kill-session -t "$MIDDLE_SESSION_TARGET" >/dev/null 2>&1 || true
  fi
  log "Starting $MIDDLE_SESSION (cwd=$PROJECT_ROOT)"
  tmux new-session -d -s "$MIDDLE_SESSION" -c "$PROJECT_ROOT" "$AGENT_CMD"
  sleep "$TUI_BOOT_WAIT"
}

stop_middle_session() {
  tmux kill-session -t "$MIDDLE_SESSION_TARGET" >/dev/null 2>&1 || true
}

cleanup() {
  stop_middle_session
  release_scheduler
}

# Send a multi-line prompt into the middle TUI: C-u (clear input) →
# load-buffer from tmpfile → paste-buffer -d → Enter → C-m → Enter.
# The triple-submit supports Codex CLI in tmux, where Enter alone may not commit
# (https://github.com/openai/codex/issues/12645). Claude Code accepts the
# same sequence without issue, so we don't branch by agent family.
send_prompt() {
  local prompt_text="$1"
  local tmp
  tmp=$(mktemp)
  printf '%s' "$prompt_text" > "$tmp"
  tmux send-keys -t "$MIDDLE_PANE_TARGET" C-u
  tmux load-buffer -b pp_prompt "$tmp"
  tmux paste-buffer -d -b pp_prompt -t "$MIDDLE_PANE_TARGET"
  rm -f "$tmp"
  sleep 0.5

  # Codex-specific: dismiss the "Create a plan?" suggestion that Codex
  # sometimes pops up when it detects a complex prompt
  # (our explore phase prompt is exactly the kind of thing that triggers
  # it). Other agent families do not receive this compatibility key.
  case "$AGENT_KIND" in
    codex) tmux send-keys -t "$MIDDLE_PANE_TARGET" Escape; sleep 0.3 ;;
  esac

  tmux send-keys -t "$MIDDLE_PANE_TARGET" Enter
  sleep 0.7
  tmux send-keys -t "$MIDDLE_PANE_TARGET" C-m
  sleep 0.7
  tmux send-keys -t "$MIDDLE_PANE_TARGET" Enter
}

wait_for_done() {
  local cycle_id="$1"
  local timeout="$2"
  local flag="$TASK_DIR/state/.cycle_done_${cycle_id}"
  local start=$(date +%s)
  local prev=""
  local silent=0
  while true; do
    sleep "$POLL_INTERVAL"
    if [ -f "$flag" ]; then rm -f "$flag"; return 0; fi
    if ! tmux has-session -t "$MIDDLE_SESSION_TARGET" 2>/dev/null; then
      log "middle session unavailable"
      return 1
    fi
    local pane
    local snap
    if ! pane=$(tmux capture-pane -t "$MIDDLE_PANE_TARGET" -p 2>/dev/null); then
      log "middle pane unavailable"
      return 1
    fi
    snap=$(printf '%s' "$pane" | sha256sum | awk '{print $1}')
    if [ "$snap" = "$prev" ]; then
      silent=$((silent + POLL_INTERVAL))
      [ "$silent" -ge "$SILENCE_THRESHOLD" ] && return 0
    else
      silent=0; prev="$snap"
    fi
    [ $(($(date +%s) - start)) -ge "$timeout" ] && return 1
  done
}

run_cycle() {
  local cycle_id="$1"
  local status=0
  start_middle_session
  # Glob the prompts/ subdirectory in lexical order: 1_explore.md → 2_execute.md → ...
  for prompt_file in $(ls "$TASK_DIR"/prompts/[0-9]*_*.md | sort); do
    local phase=$(basename "$prompt_file" .md)
    local prompt_text=$(sed "s/\${CYCLE_ID}/$cycle_id/g" "$prompt_file")
    log "[$phase] sending prompt"
    send_prompt "$prompt_text"
    if ! wait_for_done "$cycle_id-$phase" "$WAIT_PHASE_TIMEOUT"; then
      log "[$phase] failed or timed out"
      status=1
      break
    fi
    log "[$phase] complete"
  done
  stop_middle_session
  return "$status"
}

# === Control signal checks ===
check_pause() {
  while [ -f "$TASK_DIR/.paused" ]; do
    log "paused, waiting for $TASK_DIR/.paused removal..."
    sleep 60
  done
}

check_stop() {
  if [ -f "$TASK_DIR/.stop_after_current" ]; then
    log "graceful stop requested"
    return 0
  fi
  return 1
}

# === MAIN LOOP — varies per trigger type, see below ===
```

The `MAIN LOOP` is what differs across trigger types.

## Schedule trigger (the default)

```bash
# === MAIN LOOP (schedule) ===
mkdir -p "$TASK_DIR/state"
log "===== perpetuum task <name> started, MAX_ITER=$MAX_ITER ====="
acquire_scheduler
trap cleanup EXIT
trap 'exit 130' INT TERM

for ITER in $(seq 1 "$MAX_ITER"); do
  check_pause
  check_stop && break

  log ""
  log "########## ITER $ITER / $MAX_ITER ##########"
  run_cycle "${ITER}-$(date +%s)" || break

  check_stop && break

  if [ "$ITER" -lt "$MAX_ITER" ]; then
    log "Sleeping ${SLEEP_BETWEEN_CYCLES}s..."
    sleep "$SLEEP_BETWEEN_CYCLES"
  fi
done
log "===== complete after $ITER iterations ====="
```

## Conditional trigger (poll an external state)

For "run a cycle whenever GitHub has a new PR I haven't seen":

```bash
# === MAIN LOOP (conditional) ===
mkdir -p "$TASK_DIR/state"
LAST_SEEN_FILE="$TASK_DIR/state/last_seen"
[ -f "$LAST_SEEN_FILE" ] || date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ > "$LAST_SEEN_FILE"
log "===== perpetuum conditional task <name> started, MAX_ITER=$MAX_ITER ====="
acquire_scheduler
trap cleanup EXIT
trap 'exit 130' INT TERM

POLL_FREQ=3600  # 1 hour
ITER=0
while [ "$ITER" -lt "$MAX_ITER" ]; do
  check_pause
  check_stop && break

  # Your custom check command — return nonempty stdout to trigger
  NEW=$(gh pr list --search "updated:>$(cat $LAST_SEEN_FILE) state:open" \
        --json number,title --jq '. | length')

  if [ "$NEW" -gt 0 ]; then
    ITER=$((ITER + 1))
    log "########## triggered: $NEW new PRs ##########"
    run_cycle "${ITER}-$(date +%s)" || break
    date -u +%Y-%m-%dT%H:%M:%SZ > "$LAST_SEEN_FILE"
  else
    log "no change; sleep ${POLL_FREQ}s"
  fi

  sleep "$POLL_FREQ"
done
```

## Webhook trigger (event-driven)

For hard event-driven, you typically need a tiny long-running listener
plus a queue. Simplest form using `inotifywait` on a queue directory:

```bash
# A separate script (or service) writes event files to QUEUE_DIR.
# Your webhook handler is whatever — GitHub webhook → nginx → small CGI
# → touch QUEUE_DIR/$(uuid). perpetuum just consumes:

QUEUE_DIR="$TASK_DIR/state/queue"
mkdir -p "$QUEUE_DIR"
log "===== perpetuum webhook task <name> started, MAX_ITER=$MAX_ITER ====="
acquire_scheduler
trap cleanup EXIT
trap 'exit 130' INT TERM

ITER=0
while [ "$ITER" -lt "$MAX_ITER" ]; do
  check_pause
  check_stop && break

  # Block until something arrives
  inotifywait -q -e create "$QUEUE_DIR" >/dev/null
  EVENT_FILE=$(ls -1 "$QUEUE_DIR" | head -1)
  if [ -n "$EVENT_FILE" ]; then
    ITER=$((ITER + 1))
    log "########## event: $EVENT_FILE ##########"
    run_cycle "${ITER}-$(date +%s)" || break
    rm "$QUEUE_DIR/$EVENT_FILE"
  fi
done
```

Many users will not need webhooks — the conditional pattern handles
99% of "react to external state" cases with simpler operational
overhead (no listener, no port).

## Things that should go in trigger.sh

- Configuration constants at the top
- Trigger type's main loop
- Stop / pause signal checks at every loop iteration
- Logging to `trigger.log`

## Things that should NOT go in trigger.sh

- The prompt content (it's in `prompts/1_explore.md` / `prompts/2_execute.md`)
- Decisions about what to do with findings (Layer 2 / the middle agent does that)
- Any code that reads `plan.md` or `escalations.md` (only the middle agent reads those)
- The cycle's actual work (delegated to middle agent via tmux paste)

Keep trigger.sh **dumb**. It is Layer 3, the stupid heartbeat. All
intelligence is in Layer 2's prompts.

When changing the bundled trigger templates, run `scripts/validate.sh`. It
syntax-checks every example and exercises tmux exact-target behavior against a
deliberate prefix-collision session.
