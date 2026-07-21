# Task: process the triaged GitHub items

For each item in `plan.md` `## Pending` that the explore phase added
this cycle, dispatch to the inner agent via `cc-use`. **You judge what
the inner agent finds and decide what to commit / comment / escalate.**

> If cc-use is not available, the inner session is not ready, or its
> identity cannot be verified, record a blocked-on-environment
> escalation and stop the item. Do not perform Layer-1 work in the
> Layer-2 session.

Steps:

1. For each Pending item this cycle, dispatch a focused task to the
   inner agent via the `cc-use` skill. Require:
   - the project at `/<absolute-path-to-${REPO}-checkout>` — must be
     absolute
   - the agent family matching the outer agent (`claude`, `codex`, etc.)
   - a uniquely named session that has not been used by an earlier
     item or cycle; include the task, cycle, item, and a
     collision-resistant suffix in the name
   - readiness checks, task delivery, monitoring, and follow-up
     guidance for this item all use that same session
   - Task: read PR/issue #N, attempt the relevant investigation
     (reproduce, read diff, check the docs, etc.), report back with:
     - what they found
     - their suggested disposition (fix / comment-and-close / merge-with-tweak / escalate)
     - relevant evidence (file paths, line numbers, error messages)
     - Include the PR/issue number, repo context, and anything from
       `escalations.md` that already constrains this item — Layer 1
       starts with none of that unless it's in this task text.

2. When the inner agent returns, classify:

   **a. Clear bug, simple obvious fix:**
   - Ask the same inner session to implement the fix
   - Verify locally
   - Commit with clean message (no AI trailer)
   - Optionally push to a branch and have inner agent draft a PR comment
   - Mark `[FIXED]` in plan.md with commit SHA

   **b. Clear PR you can accept:**
   - Inner agent checks the PR out, runs the relevant tests, reports
   - You write the approval comment (or escalate if uncertain)
   - Mark `[APPROVED]` in plan.md

   **c. Duplicate / invalid / off-topic:**
   - Draft a courteous reply explaining
   - Suggest the user post the comment (don't auto-post unless they
     have configured perpetuum to auto-comment — check `_meta.md` or
     `inbox.md` for "auto-comment: yes")
   - Mark `[CLOSED-DRAFT]` and put the draft text in plan.md

   **d. Needs design decision:**
   - Move to `escalations.md` with full context + 2–3 options
   - Mark `[→]` in plan.md

   **e. Inner agent couldn't determine:**
   - Send more context to the same named session, OR
   - Mark `[BLOCKED]` with what's missing

   After accepting or rejecting the item, close its named session. A
   retry that requires fresh context starts another uniquely named
   session.

3. Record. Every Done item must have:

   ```
   - [x] (cycle ${CYCLE_ID}) [#<number>] [<kind>] short title
     - investigation: what the inner agent did
     - finding: what they reported
     - disposition: [FIXED commit:xxx] / [APPROVED] / [CLOSED-DRAFT] / [→ escalated] / [BLOCKED reason]
   ```

4. New follow-up tasks discovered → append to plan.md Pending.

5. **🔴 Final action:**

   ```
   echo "execute done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

   No matter how many PRs you triaged, the **last** action is writing
   this flag. Don't sit at the prompt waiting for the user.

## Safety guardrails

- **Never push directly to `main` / production branches.** Always use a
  feature branch and let the human merge.
- **Never auto-comment on issues** unless `_meta.md` explicitly enables
  it. Default is: agent drafts, human posts.
- **Never close issues automatically.** Drafts only.
- **Never approve or merge PRs.** Inner agent investigates and reports;
  human merges.

The point of perpetuum-on-GitHub is to amplify the maintainer's review
bandwidth, not to replace their judgment on what goes into the project.
