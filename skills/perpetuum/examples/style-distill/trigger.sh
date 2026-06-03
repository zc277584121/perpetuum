#!/usr/bin/env bash
# perpetuum task: style-distill
# Trigger type: schedule
#
# Cycle: explore (pick what to rewrite) → execute (rewrite + score + ratchet)
# Ratchet is git-based: every accepted edit is a commit; reverts undo.

set -uo pipefail

TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$TASK_DIR/../.." && pwd)"
MIDDLE_SESSION="middle-style-$(basename "$PROJECT_ROOT")"

MAX_ITER=50                        # style runs typically need many cycles
SLEEP_BETWEEN_CYCLES=120           # 2 min — see SKILL.md cost note before running
WAIT_PHASE_TIMEOUT=3600
SILENCE_THRESHOLD=600              # 10 min — text edits are quicker
POLL_INTERVAL=20
TUI_BOOT_WAIT=25

LOG="$TASK_DIR/trigger.log"

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
  local p="$1"
  tmux set-buffer -b style_prompt "$p"
  tmux paste-buffer -t "$MIDDLE_SESSION" -b style_prompt
  sleep 1
  tmux send-keys -t "$MIDDLE_SESSION" Enter
  sleep 1
  tmux send-keys -t "$MIDDLE_SESSION" Enter 2>/dev/null || true
}

wait_for_done() {
  local cycle_id="$1"; local timeout="$2"
  local flag="$TASK_DIR/state/.cycle_done_${cycle_id}"
  local start; start=$(date +%s); local prev=""; local silent=0
  log "  waiting for: $(basename "$flag")"
  while true; do
    sleep "$POLL_INTERVAL"
    if [ -f "$flag" ]; then
      log "  -> done via flag: $(cat "$flag")"
      rm -f "$flag"; return 0
    fi
    local snap; snap=$(tmux capture-pane -t "$MIDDLE_SESSION" -p 2>/dev/null | sha256sum | awk '{print $1}')
    if [ "$snap" = "$prev" ]; then
      silent=$((silent + POLL_INTERVAL))
      [ "$silent" -ge "$SILENCE_THRESHOLD" ] && { log "  -> silence"; return 0; }
    else silent=0; prev="$snap"; fi
    [ $(($(date +%s) - start)) -ge "$timeout" ] && return 1
  done
}

run_cycle() {
  local cycle_id="$1"
  for prompt_file in $(ls "$TASK_DIR"/[0-9]*_*.md 2>/dev/null | sort); do
    local phase; phase=$(basename "$prompt_file" .md | sed 's/[^a-zA-Z0-9_]/_/g')
    log "[$phase] sending prompt"
    local pt; pt=$(sed "s/\${CYCLE_ID}/${cycle_id}-${phase}/g" "$prompt_file")
    send_prompt "$pt"
    wait_for_done "${cycle_id}-${phase}" "$WAIT_PHASE_TIMEOUT"
    log "[$phase] complete"
  done
}

check_pause() {
  while [ -f "$TASK_DIR/.paused" ]; do
    log "paused..."
    sleep 60
  done
}
check_stop() { [ -f "$TASK_DIR/.stop_after_current" ]; }

main() {
  mkdir -p "$TASK_DIR/state"
  touch "$TASK_DIR/plan.md" "$TASK_DIR/inbox.md" "$TASK_DIR/escalations.md"

  if [ ! -f "$TASK_DIR/draft.md" ]; then
    log "ERROR: $TASK_DIR/draft.md not found. Create your v0 draft first."
    exit 1
  fi
  if [ ! -d "$TASK_DIR/target_corpus" ] || [ -z "$(ls "$TASK_DIR/target_corpus" 2>/dev/null)" ]; then
    log "ERROR: $TASK_DIR/target_corpus/ missing or empty. Populate with target author's articles."
    exit 1
  fi

  log ""
  log "===== style-distill started, MAX_ITER=$MAX_ITER ====="
  ensure_middle_session

  for ITER in $(seq 1 "$MAX_ITER"); do
    check_pause
    check_stop && { log "graceful stop"; break; }

    log ""
    log "########## ITER $ITER / $MAX_ITER ##########"
    run_cycle "${ITER}-$(date +%s)"

    check_stop && break

    if [ "$ITER" -lt "$MAX_ITER" ]; then
      log "sleeping ${SLEEP_BETWEEN_CYCLES}s..."
      sleep "$SLEEP_BETWEEN_CYCLES"
    fi
  done

  log "===== complete after $ITER iterations ====="
}

main "$@"
