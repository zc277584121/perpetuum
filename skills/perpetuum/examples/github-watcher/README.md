# github-watcher

Watch a GitHub repository for new issues / PRs (or external feed events)
and let perpetuum triage each as it appears. Inner agent reads the
issue/PR, classifies it, optionally fixes simple ones, escalates the
ambiguous ones.

## Task shape

- **Conditional trigger** — cycles fire only when new GitHub activity
  arrives, not on a fixed schedule
- "More is better" — every triaged item is a unit of progress
- Inner agent can read the issue, check related code, attempt simple
  fixes, draft replies, all in fresh context
- Middle agent classifies:
  - clearly a bug with obvious fix → commit fix, comment on issue
  - clearly invalid / duplicate → suggest comment for user to send
  - needs human design decision → escalation
- Trigger type: **conditional** (polls `gh pr list` / `gh issue list`)

## When to use this example

- Project has a steady stream of issues / PRs (more than a few per week)
- You can give the agent `GITHUB_TOKEN` with read+comment access
- You're willing to review the agent's classifications before pushing
  comments / merging fixes (or you're OK with auto-commit-to-branch
  and PR for review)

## When NOT to use this example

- One-off triage (just use Claude Code interactively)
- Project where every issue requires deep human judgment (use perpetuum
  for monitoring + escalation, but expect most items to land in
  escalations.md)

## Required environment

- `gh` CLI installed and authenticated (`gh auth status` returns OK)
- `GITHUB_TOKEN` exported in `~/.bashrc` (or available to the agent)
- `tmux` + `cc-use` (perpetuum baseline)

## Files

| File | What to customize |
|---|---|
| `trigger.sh` | `REPO`, `WATCH_QUERY` (which issues/PRs to track), `POLL_FREQ` |
| `prompts/1_explore.md` | Triage rubric for this project's domain |
| `prompts/2_execute.md` | Commit / comment policies (push or PR? comment language?) |
| `_meta.md` | Fill in once |

## How the loop runs differently from schedule type

```
loop forever:
  if .paused exists: wait
  if .stop_after_current exists: exit
  query: gh pr list (updated since last_seen)
  if new items found:
    update last_seen
    increment cycle counter
    paste prompt 1 → wait
    paste prompt 2 → wait
  else:
    log "no change" and sleep POLL_FREQ
```

So cycle count grows only when real work happens. `MAX_ITER=20` means
"after 20 real cycles, stop and let me review" — not "stop after 20
polls".
