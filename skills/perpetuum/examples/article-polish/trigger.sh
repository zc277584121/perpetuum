#!/usr/bin/env bash
# perpetuum task: article-polish
# Trigger type: schedule

set -uo pipefail

TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$TASK_DIR/../.." && pwd)"
MIDDLE_SESSION="middle-polish-$(basename "$PROJECT_ROOT")"

# Inner-agent command for Layer 2 (the persistent agent TUI in tmux).
# Default: Claude Code with permissions bypassed.
# For Codex CLI users, override before running, e.g.:
#   AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox" .perpetuum/<task>/trigger.sh
# Or (safer, sandboxed workspace writes only):
#   AGENT_CMD="codex --full-auto" .perpetuum/<task>/trigger.sh
# Other coding-CLI agents (Cursor, Windsurf, etc.) work too — set AGENT_CMD
# to whatever command starts that agent in your terminal.
AGENT_CMD="${AGENT_CMD:-claude --dangerously-skip-permissions}"

MAX_ITER=30
SLEEP_BETWEEN_CYCLES=120           # 2 min — see SKILL.md cost note before running
WAIT_PHASE_TIMEOUT=2400
SILENCE_THRESHOLD=600
POLL_INTERVAL=20
TUI_BOOT_WAIT=25

LOG="$TASK_DIR/trigger.log"
log() { echo "[$(date '+%F %T')] $*" | tee -a "$LOG"; }

ensure_middle_session() {
  if ! tmux has-session -t "$MIDDLE_SESSION" 2>/dev/null; then
    log "Starting $MIDDLE_SESSION (cwd=$PROJECT_ROOT)"
    tmux new-session -d -s "$MIDDLE_SESSION" -c "$PROJECT_ROOT" "$AGENT_CMD"
    sleep "$TUI_BOOT_WAIT"
  fi
}

send_prompt() {
  tmux set-buffer -b ap_prompt "$1"
  tmux paste-buffer -t "$MIDDLE_SESSION" -b ap_prompt
  sleep 1; tmux send-keys -t "$MIDDLE_SESSION" Enter
  sleep 1; tmux send-keys -t "$MIDDLE_SESSION" Enter 2>/dev/null || true
}

wait_for_done() {
  local cid="$1" tout="$2"
  local flag="$TASK_DIR/state/.cycle_done_${cid}"
  local start; start=$(date +%s); local prev=""; local silent=0
  log "  waiting for: $(basename "$flag")"
  while true; do
    sleep "$POLL_INTERVAL"
    if [ -f "$flag" ]; then log "  -> flag: $(cat "$flag")"; rm -f "$flag"; return 0; fi
    local snap; snap=$(tmux capture-pane -t "$MIDDLE_SESSION" -p 2>/dev/null | sha256sum | awk '{print $1}')
    if [ "$snap" = "$prev" ]; then
      silent=$((silent + POLL_INTERVAL))
      [ "$silent" -ge "$SILENCE_THRESHOLD" ] && { log "  -> silence"; return 0; }
    else silent=0; prev="$snap"; fi
    [ $(($(date +%s) - start)) -ge "$tout" ] && return 1
  done
}

run_cycle() {
  local cid="$1"
  for pf in $(ls "$TASK_DIR"/prompts/[0-9]*_*.md 2>/dev/null | sort); do
    local phase; phase=$(basename "$pf" .md | sed 's/[^a-zA-Z0-9_]/_/g')
    log "[$phase] sending prompt"
    local pt; pt=$(sed "s/\${CYCLE_ID}/${cid}-${phase}/g" "$pf")
    send_prompt "$pt"
    wait_for_done "${cid}-${phase}" "$WAIT_PHASE_TIMEOUT"
    log "[$phase] complete"
  done
}

check_pause() { while [ -f "$TASK_DIR/.paused" ]; do log "paused..."; sleep 60; done; }
check_stop() { [ -f "$TASK_DIR/.stop_after_current" ]; }

main() {
  mkdir -p "$TASK_DIR/state"
  touch "$TASK_DIR/plan.md" "$TASK_DIR/inbox.md" "$TASK_DIR/escalations.md"

  [ -f "$TASK_DIR/draft.md" ] || { log "ERROR: draft.md required"; exit 1; }

  log ""
  log "===== article-polish started, MAX_ITER=$MAX_ITER ====="
  ensure_middle_session

  for ITER in $(seq 1 "$MAX_ITER"); do
    check_pause; check_stop && { log "graceful stop"; break; }
    log ""
    log "########## ITER $ITER / $MAX_ITER ##########"
    run_cycle "${ITER}-$(date +%s)"
    check_stop && break
    [ "$ITER" -lt "$MAX_ITER" ] && { log "sleeping..."; sleep "$SLEEP_BETWEEN_CYCLES"; }
  done
  log "===== complete after $ITER iterations ====="
}

main "$@"
