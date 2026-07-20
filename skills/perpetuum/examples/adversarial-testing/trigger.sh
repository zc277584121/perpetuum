#!/usr/bin/env bash
# perpetuum task: adversarial-testing
# Trigger type: schedule
#
# Cycle: paste prompt 1 (explore) → wait done flag (or silence fallback)
#     -> paste prompt 2 (execute) → wait done flag (or silence fallback)
#     -> sleep, then next cycle, up to MAX_ITER total.
#
# Control:
#   pause    : touch .paused              (resume: remove it)
#   stop     : touch .stop_after_current  (graceful exit after current cycle)
#   kill     : pkill -f trigger.sh; tmux kill-session -t "=$MIDDLE_SESSION"

set -uo pipefail

# ============================ Configuration ===============================
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
# PROJECT_ROOT defaults to the worktree root (two levels above .perpetuum/<task>)
# Override if you keep .perpetuum/ at a non-standard depth.
PROJECT_ROOT="$(cd "$TASK_DIR/../.." && pwd)"

# Unique tmux session name. Two perpetuum tasks must not share this.
MIDDLE_SESSION="middle-adv-$(basename "$PROJECT_ROOT")"
MIDDLE_SESSION_TARGET="=$MIDDLE_SESSION"
MIDDLE_PANE_TARGET="=$MIDDLE_SESSION:"
# Exact targets prevent tmux from matching a same-prefix sibling session.
SCHEDULER_GUARD_DIR="$TASK_DIR/scheduler.guard"

# Inner-agent command for Layer 2 (a fresh per-cycle agent TUI in tmux).
# Default: Claude Code with permissions bypassed.
# For Codex CLI users, override before running, e.g.:
#   AGENT_CMD="codex --dangerously-bypass-approvals-and-sandbox" .perpetuum/<task>/trigger.sh
# Or (safer, sandboxed workspace writes only):
#   AGENT_CMD="codex --full-auto" .perpetuum/<task>/trigger.sh
# Other coding-CLI agents (Cursor, Windsurf, etc.) work too — set AGENT_CMD
# to whatever command starts that agent in your terminal.
AGENT_CMD="${AGENT_CMD:-claude --dangerously-skip-permissions}"

MAX_ITER=20
SLEEP_BETWEEN_CYCLES=120           # 2 min — see SKILL.md cost note before running
WAIT_PHASE_TIMEOUT=21600           # 6h per phase before force-end (generous)
SILENCE_THRESHOLD=1200             # 20 min tmux silence = phase done (fallback)
POLL_INTERVAL=30                   # check every 30s
TUI_BOOT_WAIT=25                   # wait after spawning fresh CC TUI
# ==========================================================================

LOG="$TASK_DIR/trigger.log"

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

# Send a multi-line prompt into the middle TUI using the same key sequence
# cc-use uses: C-u (clear input) → load-buffer from tmpfile → paste-buffer -d
# → Enter → C-m → Enter. The triple-submit handles a known Codex CLI TUI
# quirk in tmux where Enter alone sometimes doesn't commit
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
  # it). Claude Code doesn't have this popup and Escape may interfere
  # with its TUI modals there, so we only send it for Codex. The branch
  # is keyed on AGENT_CMD content (no hardcoded agent name in the loop)
  # so future agents can opt in by matching their command string here.
  case "$AGENT_CMD" in
    codex*) tmux send-keys -t "$MIDDLE_PANE_TARGET" Escape; sleep 0.3 ;;
  esac

  tmux send-keys -t "$MIDDLE_PANE_TARGET" Enter
  sleep 0.7
  tmux send-keys -t "$MIDDLE_PANE_TARGET" C-m
  sleep 0.7
  tmux send-keys -t "$MIDDLE_PANE_TARGET" Enter
}

# Three-layered sync: flag file → tmux pane silence → total timeout
wait_for_done() {
  local cycle_id="$1"
  local timeout="$2"
  local flag="$TASK_DIR/state/.cycle_done_${cycle_id}"
  local start
  start=$(date +%s)
  local prev=""
  local silent=0

  log "  waiting for: $(basename "$flag") (timeout=${timeout}s, silence=${SILENCE_THRESHOLD}s)"

  while true; do
    sleep "$POLL_INTERVAL"

    if [ -f "$flag" ]; then
      log "  -> done via flag: $(cat "$flag")"
      rm -f "$flag"
      return 0
    fi

    local snap
    snap=$(tmux capture-pane -t "$MIDDLE_PANE_TARGET" -p 2>/dev/null | sha256sum | awk '{print $1}')
    if [ "$snap" = "$prev" ]; then
      silent=$((silent + POLL_INTERVAL))
      if [ "$silent" -ge "$SILENCE_THRESHOLD" ]; then
        log "  -> done via silence (${silent}s)"
        return 0
      fi
    else
      silent=0
      prev="$snap"
    fi

    if [ $(($(date +%s) - start)) -ge "$timeout" ]; then
      log "  -> force-end via timeout"
      return 1
    fi
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
    prompt_text=$(sed "s/\${CYCLE_ID}/${cycle_id}-${phase}/g" "$prompt_file")
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
    log "paused, waiting for $TASK_DIR/.paused removal..."
    sleep 60
  done
}

check_stop() {
  [ -f "$TASK_DIR/.stop_after_current" ]
}

# =============================== Main loop ================================
main() {
  mkdir -p "$TASK_DIR/state"
  touch "$TASK_DIR/plan.md" "$TASK_DIR/inbox.md" "$TASK_DIR/escalations.md"

  log ""
  log "===== perpetuum adversarial-testing started, MAX_ITER=$MAX_ITER ====="
  log "project: $PROJECT_ROOT"
  log "session: $MIDDLE_SESSION"
  log ""

  acquire_scheduler
  trap cleanup EXIT
  trap 'exit 130' INT TERM

  for ITER in $(seq 1 "$MAX_ITER"); do
    check_pause
    check_stop && { log "graceful stop requested"; break; }

    log ""
    log "########## ITER $ITER / $MAX_ITER ##########"
    run_cycle "${ITER}-$(date +%s)" || break

    check_stop && { log "graceful stop after cycle $ITER"; break; }

    if [ "$ITER" -lt "$MAX_ITER" ]; then
      log "Sleeping ${SLEEP_BETWEEN_CYCLES}s before next cycle..."
      sleep "$SLEEP_BETWEEN_CYCLES"
    fi
  done

  log ""
  log "===== complete after $ITER iterations ====="
}

main "$@"
