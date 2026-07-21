# adversarial-testing

Run continuous adversarial / exploratory testing on a CLI / TUI / SDK
project. The loop dispatches ephemeral test operations to fresh-context
inner agents, judges results, commits real fixes, escalates ambiguous
product questions.

## Task shape

- "Find more of X" — more bugs, more UX gaps, more inconsistencies
- Cartesian product of dimensions (connector type × state × config × ...)
- Inner agent does throwaway CLI/TUI/SDK operations, not persistent tests
- Middle agent classifies findings into:
  - clearly fixable → inner agent fixes + git commit
  - clearly broken but design-decision needed → escalations.md
  - benign / not a bug → noted in plan.md, moved on
- Trigger type: **schedule** (every N minutes, M cycles total)

## When to use this example

Use when the user has:
- A working project they want continuous quality pressure on
- Clear "real bug" vs "design ambiguity" distinction
- Ability to receive 5-30 small commits per day across multiple cycles
- A bashrc / environment with the relevant API keys / credentials so the
  agent can exercise real backends

## Files in this template

| File | What you need to customize |
|---|---|
| `trigger.sh` | `MIDDLE_SESSION`, `MAX_ITER`, `SLEEP_BETWEEN_CYCLES`, possibly the timeouts |
| `prompts/1_explore.md` | The "test dimensions examples" block — replace with this project's actual axes |
| `prompts/2_execute.md` | The absolute project path and commit-style guidance if the project has conventions |
| `plan.md` | Leave empty, agent fills it |
| `inbox.md` | Leave empty, user fills as they go |
| `escalations.md` | Leave empty |
| `_meta.md` | Fill once at init time |

## Recommended adaptations

- If the project's CLI has many subcommands, **list them explicitly** in
  `prompts/1_explore.md`'s dimension hints — don't make the agent guess from
  the binary name.
- If the project has known fragile areas, **list them in the agent's
  context** via `prompts/1_explore.md` so it doesn't redundantly poke at them.
- If the user has strong opinions on what's a "real bug" vs "by design",
  reflect that in `prompts/2_execute.md`'s classification guidance.

## Real-world reference

This example is the abstraction of a loop dogfooded in early development
of perpetuum. In one ~6.5-hour stretch on a moderately-sized backend
codebase it produced 4 real bug fixes, 2 escalations with full A/B/C
trade-offs, and 25+ planned follow-up items, with the inner agent
dispatched 11 times.
