#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

for trigger in "$SKILL_DIR"/examples/*/trigger.sh; do
  bash -n "$trigger"
done

if grep -RInE 'tmux (has-session|kill-session) -t "\$MIDDLE_SESSION"' \
  "$SKILL_DIR/examples" "$SKILL_DIR/references/trigger.md"; then
  echo "unqualified middle session target found" >&2
  exit 1
fi

if grep -RInE 'tmux (send-keys|capture-pane|paste-buffer).*"\$MIDDLE_SESSION"' \
  "$SKILL_DIR/examples" "$SKILL_DIR/references/trigger.md"; then
  echo "unqualified middle pane target found" >&2
  exit 1
fi

if grep -RInE -- '--replace|scripts/cc-use|ccu-|cc-use (delegate|monitor|project-status|scrollback|snapshot|kill)|session_name_for_project' \
  "$SKILL_DIR/SKILL.md" "$SKILL_DIR/references" "$SKILL_DIR/examples" \
  "$SKILL_DIR/scripts/dashboard/parsers.py" "$SKILL_DIR/scripts/dashboard/web.py"; then
  echo "cc-use implementation detail found in perpetuum contract" >&2
  exit 1
fi

for prompt in "$SKILL_DIR"/examples/*/prompts/2_execute.md; do
  grep -Fq 'uniquely named' "$prompt" || {
    echo "missing unique Layer-1 session requirement: $prompt" >&2
    exit 1
  }
  grep -Eiq 'close|closed' "$prompt" || {
    echo "missing Layer-1 session cleanup requirement: $prompt" >&2
    exit 1
  }
done

for trigger in "$SKILL_DIR"/examples/*/trigger.sh; do
  grep -Fq 'middle session unavailable' "$trigger" || {
    echo "missing middle-session failure detection: $trigger" >&2
    exit 1
  }
done

if command -v tmux >/dev/null 2>&1; then
  base="perpetuum-target-check-$$"
  sibling="${base}-restart"

  cleanup() {
    tmux kill-session -t "=$base" >/dev/null 2>&1 || true
    tmux kill-session -t "=$sibling" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT

  tmux new-session -d -s "$sibling"
  tmux has-session -t "$base"
  if tmux has-session -t "=$base" 2>/dev/null; then
    echo "exact target unexpectedly matched a prefix sibling" >&2
    exit 1
  fi
  tmux kill-session -t "=$sibling"

  tmux new-session -d -s "$base"
  tmux send-keys -t "=$base:" 'printf perpetuum-exact-target-ok' Enter
  sleep 1
  tmux capture-pane -t "=$base:" -p | grep -Fq 'perpetuum-exact-target-ok'
  tmux kill-session -t "=$base"
  trap - EXIT
fi

echo "perpetuum validation passed"
