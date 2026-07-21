#!/usr/bin/env bash
# perpetuum task: github-watcher
# Trigger type: conditional (polls gh, fires cycle on change)
#
# Cycle fires when `gh pr list` returns items updated after our last_seen
# timestamp. Otherwise the loop just polls and sleeps.

set -uo pipefail

# ============================ Configuration ===============================
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$TASK_DIR/../.." && pwd)"

MIDDLE_SESSION="middle-gh-$(basename "$PROJECT_ROOT")"
MIDDLE_SESSION_TARGET="=$MIDDLE_SESSION"
MIDDLE_PANE_TARGET="=$MIDDLE_SESSION:"
# Exact targets prevent tmux from matching a same-prefix sibling session.
SCHEDULER_GUARD_DIR="$TASK_DIR/scheduler.guard"

# === Customize for your repo ===
REPO="owner/repo"                                # <-- CHANGE ME
WATCH_QUERY="state:open"                         # what to consider "new activity"
# Examples:
#   WATCH_QUERY="state:open label:bug"           # only bug-labeled
#   WATCH_QUERY="state:open author:not-team"     # only outside contributions
# ===============================

# Inner-agent command for Layer 2 (a fresh per-cycle agent TUI in tmux).
# Default: Claude Code with permissions bypassed.
# For Codex CLI users, override before running, e.g.:
#   AGENT_KIND=codex AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox" .perpetuum/<task>/trigger.sh
# Or (safer, sandboxed workspace writes only):
#   AGENT_KIND=codex AGENT_CMD="codex --full-auto" .perpetuum/<task>/trigger.sh
# Other coding-CLI agents (Cursor, Windsurf, etc.) work too — set AGENT_CMD
# to whatever command starts that agent in your terminal.
AGENT_KIND="${AGENT_KIND:-claude}"
AGENT_CMD="${AGENT_CMD:-claude --dangerously-skip-permissions}"

MAX_ITER=20                        # how many real cycles before we stop
POLL_FREQ=3600                     # 1 hour between polls
WAIT_PHASE_TIMEOUT=10800           # 3h per phase
SILENCE_THRESHOLD=900              # 15 min silence = phase done
POLL_INTERVAL=30
TUI_BOOT_WAIT=25
# ==========================================================================

LOG="$TASK_DIR/trigger.log"
LAST_SEEN_FILE="$TASK_DIR/state/last_seen"

log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

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
  tmux new-session -d -s "$MIDDLE_SESSION" -c "$PROJECT_ROOT" \
    "$AGENT_CMD"
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
# same sequence without issue, so we don't branch by agent.
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
  local start; start=$(date +%s)
  local prev=""
  local silent=0
  log "  waiting for: $(basename "$flag")"
  while true; do
    sleep "$POLL_INTERVAL"
    if [ -f "$flag" ]; then
      log "  -> done via flag: $(cat "$flag")"
      rm -f "$flag"; return 0
    fi
    if ! tmux has-session -t "$MIDDLE_SESSION_TARGET" 2>/dev/null; then
      log "  -> middle session unavailable"
      return 1
    fi
    local pane
    local snap
    if ! pane=$(tmux capture-pane -t "$MIDDLE_PANE_TARGET" -p 2>/dev/null); then
      log "  -> middle pane unavailable"
      return 1
    fi
    snap=$(printf '%s' "$pane" | sha256sum | awk '{print $1}')
    if [ "$snap" = "$prev" ]; then
      silent=$((silent + POLL_INTERVAL))
      [ "$silent" -ge "$SILENCE_THRESHOLD" ] && { log "  -> done via silence"; return 0; }
    else
      silent=0; prev="$snap"
    fi
    [ $(($(date +%s) - start)) -ge "$timeout" ] && { log "  -> timeout"; return 1; }
  done
}

run_cycle() {
  local cycle_id="$1"
  local status=0
  start_middle_session
  for prompt_file in $(ls "$TASK_DIR"/prompts/[0-9]*_*.md 2>/dev/null | sort); do
    local phase
    phase=$(basename "$prompt_file" .md | sed 's/[^a-zA-Z0-9_]/_/g')
    log "[$phase] sending prompt"
    local prompt_text
    prompt_text=$(sed -e "s/\${CYCLE_ID}/${cycle_id}-${phase}/g" \
                       -e "s|\${REPO}|${REPO}|g" "$prompt_file")
    send_prompt "$prompt_text"
    if ! wait_for_done "${cycle_id}-${phase}" "$WAIT_PHASE_TIMEOUT"; then
      log "[$phase] failed or timed out"
      status=1
      break
    fi
    log "[$phase] complete"
  done
  stop_middle_session
  return "$status"
}

check_pause() {
  while [ -f "$TASK_DIR/.paused" ]; do
    log "paused, waiting for .paused removal..."
    sleep 60
  done
}

check_stop() { [ -f "$TASK_DIR/.stop_after_current" ]; }

# Returns nonzero stdout if there is new activity since last_seen.
check_for_new_activity() {
  local since
  since=$(cat "$LAST_SEEN_FILE")
  gh pr list --repo "$REPO" \
    --search "updated:>$since $WATCH_QUERY" \
    --json number,title,updatedAt 2>/dev/null \
    | jq -r '.[].number' \
    | head -20
}

# =============================== Main loop ================================
main() {
  mkdir -p "$TASK_DIR/state"
  touch "$TASK_DIR/plan.md" "$TASK_DIR/inbox.md" "$TASK_DIR/escalations.md"

  if [ ! -f "$LAST_SEEN_FILE" ]; then
    date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ > "$LAST_SEEN_FILE"
    log "first run; backfilling last_seen to 24h ago: $(cat "$LAST_SEEN_FILE")"
  fi

  log ""
  log "===== github-watcher started, MAX_ITER=$MAX_ITER, repo=$REPO ====="
  acquire_scheduler
  trap cleanup EXIT
  trap 'exit 130' INT TERM

  local iter=0
  while [ "$iter" -lt "$MAX_ITER" ]; do
    check_pause
    check_stop && { log "graceful stop requested"; break; }

    local new_items
    new_items=$(check_for_new_activity)

    if [ -z "$new_items" ]; then
      log "no new activity since $(cat "$LAST_SEEN_FILE"); sleeping ${POLL_FREQ}s"
      sleep "$POLL_FREQ"
      continue
    fi

    iter=$((iter + 1))
    log ""
    log "########## CYCLE $iter / $MAX_ITER triggered ##########"
    log "new items: $(echo "$new_items" | tr '\n' ' ')"

    run_cycle "${iter}-$(date +%s)" || break

    # Update last_seen so we don't reprocess. Use the time we started
    # checking, not "now", to avoid race with items arriving mid-cycle.
    date -u +%Y-%m-%dT%H:%M:%SZ > "$LAST_SEEN_FILE"

    check_stop && { log "graceful stop"; break; }
  done

  log ""
  log "===== complete after $iter real cycles ====="
}

main "$@"
