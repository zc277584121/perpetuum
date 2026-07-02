# Task: process the triaged GitHub items

For each item in `plan.md` `## Pending` that the explore phase added
> ⚠️ **Important: `cc-use` is an installed Agent Skill, not a shell command.**
> Use it via your host agent's skill mechanism (your host will load
> cc-use's SKILL.md and know how to dispatch the inner agent). **Do not**
> run `cc-use` directly with the Bash tool — that bypasses the skill
> protocol and will fail.
>
> If your environment does not recognize `cc-use` as a skill, or `cc-use`
> reports an inner-agent startup failure (a known issue exists for Codex
> outer agents in `--dangerously-bypass-approvals-and-sandbox` mode where
> cc-use's hardcoded `--ask-for-approval` / `--sandbox` flags clash —
> upstream cc-use issue, not perpetuum): **do not fall back to
> Bash-running cc-use, do not spawn a sub-agent yourself, do not write
> the work into this session's context directly.** Surface it as a
> blocked-on-environment escalation to `escalations.md` and stop the
> cycle there. The whole point of the three-layer architecture is the
> fresh-context inner agent; faking it locally defeats the purpose.
this cycle, dispatch to the inner agent via `cc-use`. **You judge what
the inner agent finds and decide what to commit / comment / escalate.**

Steps:

1. For each Pending item this cycle, dispatch a focused task to the
   inner agent via the `cc-use` skill. Require, in plain language (not
   specific CLI flags — cc-use's own `SKILL.md` decides how it
   satisfies these, and that can change independently of perpetuum):
   - the project at `/<absolute-path-to-${REPO}-checkout>` — must be
     absolute
   - the agent family matching the outer agent (`claude`, `codex`, etc.)
   - a **fresh, no-memory inner session** every dispatch — never a
     reused one, which would quietly let Layer 1 accumulate memory
     across items/cycles
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
   - Dispatch a second inner call asking to implement the fix
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
   - Reshape and re-dispatch with more context, OR
   - Mark `[BLOCKED]` with what's missing

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
