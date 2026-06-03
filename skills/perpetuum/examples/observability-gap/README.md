# observability-gap

Scan a codebase for missing observability — error paths that don't log,
metrics that don't exist, traces that don't cover important spans,
configuration drift between expected and actual.

This example is **observation-mode** of adversarial-testing. Instead of
"find bugs", it's "find places where you'd be blind in production".

## Task shape

- Iterate over the codebase by module / package / directory
- For each, inspect error paths, exception handlers, key state transitions
- Flag any place that:
  - catches an exception but doesn't log
  - returns an error to caller without metrics
  - changes important state without an audit log entry
  - has no trace span around an external call
- Categorize fixes:
  - simple obvious additions → commit
  - opinionated (log level, metric naming) → escalate
- Trigger type: **schedule** (every ~30 min)

## Why this is worth its own example

In early dogfooding on a real codebase, the adversarial-testing example
*spontaneously* discovered several observability commits (per-component
counts, startup config logs, failed-job WARNING signals, auth-failure
metrics). Carving it
out into a dedicated task type lets you:
- Focus the loop entirely on this dimension
- Use a different inner-agent prompt that biases toward "what would
  I want to see in a Loki dashboard" rather than "is this correct"
- Avoid mixing "fix bugs" commits with "add log" commits in history

## Files

| File | Customize |
|---|---|
| `trigger.sh` | `MIDDLE_SESSION`, `MAX_ITER` |
| `1_explore.md` | Module list / scan strategy |
| `2_execute.md` | Logging conventions (log level taxonomy, metric naming) |
| `_meta.md` | Once |

## Conventions worth committing to

Before running, decide:
- **Log levels**: when do you use DEBUG vs INFO vs WARN vs ERROR?
- **Metric naming**: prefix convention, units, labels
- **Trace span boundaries**: which calls deserve their own span?
- **Error vs warning**: when does a failure deserve a metric counter
  separate from the existing error log?

Put these in `_meta.md` or a `conventions.md` you reference from
`2_execute.md`. Otherwise the agent will make ad-hoc choices and
your codebase will end up with inconsistent observability — which is
worse than less observability.

## Strong recommendation: run on a feature branch

Observability commits accumulate fast (10–30 per day at peak). Merge
them as a batch when you're satisfied, rather than letting them trickle
into main one by one.
