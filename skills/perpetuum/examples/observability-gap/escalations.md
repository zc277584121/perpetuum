# Escalations

> Observability additions where convention/policy choice is needed.

## Open

<!-- Examples:

### (cycle 3) [worker] [counter] should failed jobs have a per-reason breakdown?

**Background:** Worker currently emits `worker.jobs.failed` counter
without labels. There are ~6 distinct failure reasons (timeout,
auth, embedding-quota, etc).

**Question:** Add a `reason` label so we can break down failures by
type. But labels carry cardinality cost.

**Options:**
- **A:** Add `reason` label, restrict to ≤10 enumerated values.
- **B:** Keep aggregate counter, add separate counters per reason
  (worker.jobs.failed.auth, worker.jobs.failed.timeout, ...).
- **C:** Keep as is, expect operators to grep logs for reason.
-->

## Resolved
