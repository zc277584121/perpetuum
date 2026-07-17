# Worktree: running multiple perpetuum tasks in parallel

Read this when the user wants to run several perpetuum tasks on the
same project at the same time (e.g. one finding bugs on `main`, one
polishing docs on `docs-work`, one auditing API consistency on
`api-audit`).

## Why git worktree

A perpetuum task **commits aggressively**. If two tasks share the same
branch, their commits interleave and the ratchet semantics get messy
("Done items" from one task become "history" for the other). Worktrees
give each task its own branch and physical directory.

The default mode — no worktree, just commit to current branch — is
fine for a single task or a single line of work. Switch to worktree
mode only when the user actually has parallel lines.

## The standard procedure

### 1. From the parent repo, create a worktree

```bash
cd <parent-repo>
git worktree add ../<project>-<task-tag>  <new-branch>
# Example:
git worktree add ../project-docs  docs-polish
git worktree add ../project-api   api-audit
```

`<new-branch>` is created from `HEAD` if it doesn't exist. To start
from a specific point: `git worktree add -b <branch> <path> <start-point>`.

### 2. Set up perpetuum inside the new worktree

```bash
cd ../<project>-<task-tag>
mkdir -p .perpetuum/<task-name>
# ...follow normal setup flow (references/setup.md) from here
```

### 3. Fill `_meta.md` with worktree context

```markdown
# Task metadata

- **task name**: <task-name>
- **created**: 2026-06-03
- **worktree path**: /home/you/project-docs
- **branch**: docs-polish
- **started from**: main@abc1234
- **parent repo**: /home/you/project
- **merge target**: main
- **trigger type**: schedule
```

`merge target` is informational — it tells the user (and any future agent
re-reading the meta) where this branch is "headed". perpetuum doesn't
auto-merge.

### 4. Use a distinct middle tmux session name per task

In each task's `trigger.sh`:

```bash
MIDDLE_SESSION="middle-<task-tag>"   # must be unique across tasks
```

This is **critical** — if two trigger.sh use the same session name,
they will paste into the same TUI and corrupt each other.

Suggested convention: `middle-<task-name>` or `middle-<task-tag>` where
the tag is short and unique. A task reuses its own fixed name across
cycles, but Layer 3 kills and recreates that tmux session for each
cycle.

### 5. Launch independently

Each worktree has its own trigger.sh in its own `.perpetuum/`. Launch
them independently:

```bash
cd /home/you/project && nohup .perpetuum/adversarial-testing/trigger.sh > /dev/null 2>&1 &
cd /home/you/project-docs && nohup .perpetuum/docs-polish/trigger.sh > /dev/null 2>&1 &
cd /home/you/project-api && nohup .perpetuum/api-audit/trigger.sh > /dev/null 2>&1 &
```

## Listing parallel tasks

Rely on `git worktree list` rather than maintaining a custom index file:

```bash
git -C <parent-repo> worktree list
# /home/you/project        abc1234 [main]
# /home/you/project-docs   def5678 [docs-polish]
# /home/you/project-api    deadbef [api-audit]
```

To see which worktrees have perpetuum tasks:

```bash
for wt in $(git -C <parent-repo> worktree list --porcelain | awk '/^worktree /{print $2}'); do
  echo "=== $wt ==="
  ls -d "$wt"/.perpetuum/*/ 2>/dev/null
done
```

## Merging back

perpetuum does **not** auto-merge. When the user is happy with a
worktree's progress and wants to merge:

```bash
cd <parent-repo>
git merge <branch>          # or PR via gh / web
# or
git rebase <branch>
```

After merge, the user can `git worktree remove <path>` to clean up.

Suggest **graceful stop first** (`touch .stop_after_current`), wait for
trigger.sh to exit, then merge. Merging while the task is still running
is fine but produces weirder history (commits during merge).

## Recipe: "I want one perpetuum task per open issue category"

A common pattern. Example: GitHub project has issues tagged `bug`,
`docs`, `performance`. User wants a separate perpetuum line per tag.

```bash
for tag in bug docs perf; do
  git worktree add ../project-$tag $tag-$(date +%Y%m%d)
  cd ../project-$tag
  # Set up perpetuum with example=adversarial-testing, customize
  # 1_explore.md to scope only to the given tag
  cd -
done
```

Each task focuses, doesn't interfere with others. Merge whenever each
is ready.

## Anti-pattern: don't run two tasks on the same branch

Don't try:

```bash
# DON'T:
cd <project>
mkdir .perpetuum/task-a
mkdir .perpetuum/task-b
# launch both
```

Both tasks committing to the same branch will:
- Interleave commits unpredictably
- Confuse each task's "Done" tracking
- Compete for the same git lock occasionally
- Make rollback ambiguous (which task's commit do you revert?)

If the user insists on this for some reason (e.g. tasks that genuinely
don't make commits and only fill `plan.md`), at minimum:
- Each task in its own subdirectory of `.perpetuum/`
- Each task with its own `MIDDLE_SESSION` name in trigger.sh
- Accept that ratchet semantics are weaker without per-task branches
