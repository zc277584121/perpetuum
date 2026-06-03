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

# === Customize for your repo ===
REPO="owner/repo"                                # <-- CHANGE ME
WATCH_QUERY="state:open"                         # what to consider "new activity"
# Examples:
#   WATCH_QUERY="state:open label:bug"           # only bug-labeled
#   WATCH_QUERY="state:open author:not-team"     # only outside contributions
# ===============================

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

ensure_middle_session() {
  if ! tmux has-session -t "$MIDDLE_SESSION" 2>/dev/null; then
    log "Starting $MIDDLE_SESSION (cwd=$PROJECT_ROOT)"
    tmux new-session -d -s "$MIDDLE_SESSION" -c "$PROJECT_ROOT" \
      'claude --dangerously-skip-permissions'
    sleep "$TUI_BOOT_WAIT"
  fi
}

send_prompt() {
  local prompt_text="$1"
  tmux set-buffer -b gh_prompt "$prompt_text"
  tmux paste-buffer -t "$MIDDLE_SESSION" -b gh_prompt
  sleep 1
  tmux send-keys -t "$MIDDLE_SESSION" Enter
  sleep 1
  tmux send-keys -t "$MIDDLE_SESSION" Enter 2>/dev/null || true
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
    local snap
    snap=$(tmux capture-pane -t "$MIDDLE_SESSION" -p 2>/dev/null | sha256sum | awk '{print $1}')
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
  for prompt_file in $(ls "$TASK_DIR"/[0-9]*_*.md 2>/dev/null | sort); do
    local phase
    phase=$(basename "$prompt_file" .md | sed 's/[^a-zA-Z0-9_]/_/g')
    log "[$phase] sending prompt"
    local prompt_text
    prompt_text=$(sed -e "s/\${CYCLE_ID}/${cycle_id}-${phase}/g" \
                       -e "s|\${REPO}|${REPO}|g" "$prompt_file")
    send_prompt "$prompt_text"
    wait_for_done "${cycle_id}-${phase}" "$WAIT_PHASE_TIMEOUT"
    log "[$phase] complete"
  done
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

    ensure_middle_session
    run_cycle "${iter}-$(date +%s)"

    # Update last_seen so we don't reprocess. Use the time we started
    # checking, not "now", to avoid race with items arriving mid-cycle.
    date -u +%Y-%m-%dT%H:%M:%SZ > "$LAST_SEEN_FILE"

    check_stop && { log "graceful stop"; break; }
  done

  log ""
  log "===== complete after $iter real cycles ====="
}

main "$@"
