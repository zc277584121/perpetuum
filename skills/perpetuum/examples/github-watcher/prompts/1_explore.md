# Task: triage new GitHub activity (plan only, do not execute)

The outer trigger.sh has detected new issues / PRs on `${REPO}` updated
since the last cycle. Your job is to look at them and plan how to
handle each. **Do not act on them yet** — execution is the next prompt.

Steps:

1. Read `plan.md` to see what's already been handled (or escalated) in
   previous cycles. Avoid redundant work.

2. Read `inbox.md` `## Pending`. Apply each item to your priorities for
   this cycle. Move processed items to `## Processed` with a one-line note.

3. List the new items. Use `gh` to fetch their content:

   ```bash
   gh pr list --repo ${REPO} --search "updated:>$(cat .perpetuum/<task>/state/last_seen) state:open" \
     --json number,title,author,body,labels,headRefName
   ```

   Or for issues:

   ```bash
   gh issue list --repo ${REPO} --search "updated:>$(cat .perpetuum/<task>/state/last_seen) state:open" \
     --json number,title,author,body,labels
   ```

4. For each new item, do a quick categorization:

   - **Bug report with reproducible steps** → plan to verify + investigate
   - **PR fixing something** → plan to read the diff + judge
   - **Feature request** → plan to write a thoughtful response or
     escalate if it's a real direction question
   - **Duplicate / spam / off-topic** → plan to comment/close with a
     short message
   - **Question / how-to** → plan to answer or point to docs

5. Append items to `plan.md` `## Pending` in priority order. Use this
   format:

   ```
   - [ ] [#<number>] [<kind>] short title — first thought on disposition
   ```

   Kind = `bug` | `pr` | `feature-req` | `dup` | `question` | `other`.

6. **Don't execute anything yet.** No commits, no comments, no fix
   attempts. Just plan.

7. Final action (don't forget):

   ```
   echo "explore done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```
