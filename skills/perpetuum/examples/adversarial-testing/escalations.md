# Escalations

> Questions the agent surfaces for human judgment. Each item has
> context + the specific question + 2–3 options with trade-offs.
>
> When you're ready to answer, edit the item in place to add your
> decision, then move it to `## Resolved`. The agent does NOT move items
> here — moving is the human's signal of "I've decided".

## Open

<!-- Example (delete when you have real ones):

### (cycle 3-abc1234) off-by-one between two CLI subcommands

**Context:** Subcommand A reports line ranges as `[start, end]` 1-based
inclusive. Subcommand B accepts `--range start:end` as 0-based
half-open. Feeding A's output directly into B silently drops the first
line. This is the kind of papercut that erodes user trust without ever
producing a hard error.

**Question:** Align on which convention? This is a public-contract
decision affecting any consumer of the CLI's structured output.

**Options:**
- **A (recommended):** Standardize on 1-based inclusive across both
  commands. Smallest change for tooling consumers, matches common
  shell tools (head, tail, sed). Documented breaking change.
- **B:** Standardize on 0-based half-open. Matches array semantics
  in most languages. Larger blast radius for existing users.
- **C:** Leave both, document the off-by-one. Cheapest but most
  surprising.
-->

## Resolved

<!-- Human moves answered items here with their decision. -->
