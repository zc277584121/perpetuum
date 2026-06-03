# Task: choose what to scan this cycle (plan only)

You are scanning the project for observability gaps — places where, in
production, you would be blind. Missing logs at error paths. Missing
metrics around state changes. Missing trace spans around external calls.

Steps:

1. Read `plan.md` Done to see which modules / files / dimensions have
   been scanned, and what was added vs escalated.

2. Read `inbox.md` `## Pending` and apply.

3. Read the project structure once if you haven't this cycle:

   ```bash
   find . -type d -not -path '*/.*' -not -path '*/node_modules/*' \
     -not -path '*/__pycache__/*' | head -50
   ```

   List the modules / packages.

4. Pick a target for this cycle. Prefer:
   - Modules that have never been scanned (check plan.md Done)
   - Modules that handle external integrations (highest gap risk)
   - Modules with recent commits that didn't touch logging
   - Don't repeat: skip modules scanned in the last 5 cycles

5. Decide what *kind* of observability to focus on this cycle:
   - **Error path coverage** — every `except` / `catch` / `if err`
     branch has a log?
   - **State transitions** — every important state mutation has an
     audit event?
   - **External calls** — every network / RPC / DB call has a trace
     span and latency metric?
   - **Configuration** — startup logs the effective config?
   - **Counters** — important domain events have counters
     (requests by route, jobs by status, etc)?

   One kind per cycle. Don't try to do them all at once.

6. Append to `plan.md` Pending:

   ```
   - [ ] [<module>] [<obs kind>] short description of what to look for
   ```

7. **Do not start scanning yet.**

8. Final action:

   ```
   echo "explore done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```
