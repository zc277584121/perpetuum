# Task: scan + propose + commit or escalate

> Use the `cc-use` skill for every Layer-1 operation. If cc-use is not
> available, the inner session is not ready, or its identity cannot be
> verified, record a blocked-on-environment escalation and stop the item.
> Do not perform Layer-1 work in the Layer-2 session.
Use `cc-use` to dispatch the scan to the inner agent. Take its findings,
classify each, and either commit the obvious additions or escalate the
opinionated ones.

Steps:

1. Read `plan.md` Pending. Process the items planned this cycle.

2. For each, dispatch to the inner agent via the `cc-use` skill.
   Require:
   - the project at `/<abs-path>` — must be absolute
   - the agent family matching the outer agent (`claude`, `codex`, etc.)
   - a uniquely named session that has not been used by an earlier
     item or cycle; include the task, cycle, item, and a
     collision-resistant suffix in the name
   - readiness checks, task delivery, monitoring, and follow-up
     guidance for this item all use that same session
   - Task: "Scan `<module>` for `<obs kind>` gaps. For each candidate,
     report: file path, line range, current behavior, what's missing
     (log/metric/span/event), and a suggested addition consistent with
     the project's existing observability conventions."
   - **Important:** ask the inner agent to *read existing logs in the
     same module first* to learn the convention before proposing new
     ones. Otherwise you'll get style drift.
   - Include anything from `plan.md`/`escalations.md` that already
     bears on this module — Layer 1 has no memory of earlier cycles
     and only knows what's in this task text.

3. For each finding the inner agent reports, classify:

   **a. Clearly missing, obvious addition matching existing conventions:**
   - Ask the same inner session to make the addition
   - Verify the project still builds / tests still pass
   - Commit: `obsv(<module>): add <log/metric/span> for <event>`
   - Mark `[ADDED]` in plan.md with commit SHA

   **b. Missing but addition involves a convention choice:**
   (new metric naming, ambiguous log level, new label dimension)
   - Don't add. Move to `escalations.md` with options.
   - Mark `[→]` in plan.md

   **c. Looks like a gap but actually intentional silence:**
   (high-cardinality counter, expected silent path)
   - Don't add. Note in plan.md as `[SKIP]` with reason.

   **d. False positive (inner agent misread the code):**
   - Mark `[FALSE-POSITIVE]` with brief note.

   After accepting or rejecting the item, close its named session. A
   retry that requires fresh context starts another uniquely named
   session.

4. Record. Every Done item:

   ```
   - [x] (cycle ${CYCLE_ID}) [<module>] [<obs kind>] short title
     - finding: file:line — what's currently happening
     - proposal: what observation to add
     - status: [ADDED] commit:abc1234 | [→ escalated] | [SKIP] reason | [FALSE-POSITIVE]
   ```

5. New follow-up scan targets discovered → append to Pending.

6. **🔴 Final action:**

   ```
   echo "execute done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

## Quality bar — what counts as a real gap

- **Real gap:** in production you'd say "I have no idea why this
  happened". Add it.
- **Cosmetic gap:** you'd be slightly more comfortable but it's
  already reconstructible from existing data. Skip.
- **Volume risk:** adding this log would create 10× current log
  volume. Escalate (don't decide unilaterally).
- **PII concern:** adding this would log a user identifier without
  obvious need. Escalate.

The goal is *useful* observability, not *complete* observability. A
firehose of logs is its own outage.
