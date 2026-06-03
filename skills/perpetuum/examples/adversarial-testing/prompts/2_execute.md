# Task: execute this cycle's plan (dispatch + judge + record)

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
Use the `cc-use` skill to delegate the actual testing work to an inner
agent. **You do not run the tests yourself.** You plan, dispatch, judge,
record, and escalate.

Walk through these steps:

1. Read `.perpetuum/<task>/plan.md` `## Pending` section. Pick items to
   process this cycle — don't try to do all of them if the list is
   large; this is best-effort within reasonable time.

2. For each picked item:

   a. **Dispatch.** Call `cc-use delegate` with:
      - `--project /<absolute-path-to-project-or-worktree>` (must be absolute!)
      - `--agent claude` (or `codex`, matching the outer agent family)
      - The task description: instruct the inner agent to do *ephemeral
        CLI / TUI / SDK operations*, **never** to write persistent unit
        tests. The inner agent should report what it tried, what it
        observed, and any anomalies.

   b. **Judge.** When the inner agent returns:
      - **Clearly correct behavior** → mark in plan.md as PASS
      - **Clearly a bug, simple fix** → dispatch a second inner call
        asking it to fix; verify the fix; commit with a clean message
        (no AI trailer); mark FIXED in plan.md with commit hash
      - **Bug but the fix involves a design decision** (public API
        rename, deprecation path, UX trade-off) → don't fix. Move to
        escalations.md. Mark in plan.md with `[→]`
      - **Inner agent's test was malformed / missing context** → reshape
        the task and re-dispatch; do not mark as failure
      - **Blocked** (missing env, external dep down) → mark BLOCKED with
        reason

3. Record. Every Done item in `plan.md` **must** have three fields:

   ```
   - [x] (cycle ${CYCLE_ID}) [<dim>] short title
     - operation: the exact command(s) or step(s) attempted
     - observed: the actual output / behavior
     - status: PASS | [FIXED] commit:abc1234 | [FAILED] reason | [BLOCKED] reason
   ```

   Do not abbreviate. A future agent or human will use these to know
   what was already exercised.

4. Escalate. For items moved to `escalations.md`, write:

   ```
   ### (cycle ${CYCLE_ID}) brief title

   **Context:** what was being tested, why it matters
   **Question:** what's ambiguous, what specifically needs the human's input
   **Options:**
   - **A:** option with trade-offs
   - **B:** option with trade-offs
   - **C:** option with trade-offs (optional)
   ```

   Write the escalation in the user's language. Make it answerable in
   five minutes — include enough evidence so the human doesn't have to
   reproduce.

5. New follow-up items discovered during this cycle that warrant a
   future test → **append to `plan.md` Pending**, do not put in Done.

6. **🔴 Final action — do not forget this!**

   ```
   echo "execute done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

   Replace `<TASK_NAME>` with the actual directory name. The outer
   trigger.sh is waiting for this flag. If you don't write it, the
   outer process pays a 20-minute silence-fallback penalty for nothing.

   No matter how much you did this cycle — fixes, escalations,
   follow-ups, partial work — the **last** step must be writing this
   flag. Do not stop at the prompt waiting for the user to tell you
   what to do next.
