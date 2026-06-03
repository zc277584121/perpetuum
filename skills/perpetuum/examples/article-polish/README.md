# article-polish

Iteratively read and polish a single document — an article, a doc page,
a README, a proposal. Each cycle picks one paragraph, improves it, and
either keeps or reverts based on judgment.

## Task shape vs style-distill

`style-distill` has a frozen scalar oracle (similarity to target corpus).
`article-polish` does **not** — it relies on the agent's judgment of
"this is better writing now". So the keep/revert decision is qualitative.

Use this when:
- You don't have a target corpus
- You want general writing improvement (clarity, tightness, flow,
  argument strength) rather than mimicry of a specific voice
- You accept that the ratchet is softer (an LLM judging "better" is
  not as reliable as a numeric score)

Use `style-distill` instead when:
- You have a target style and corpus
- You want strict ratchet semantics

## Task shape

- "Make this article as good as it can be"
- One paragraph per cycle, focused
- Keep/revert based on a multi-criteria LLM judgment (clarity +
  tightness + factual + voice)
- Trigger type: **schedule** (every ~15–30 min)

## Files

| File | Customize |
|---|---|
| `trigger.sh` | `MAX_ITER`, `SLEEP_BETWEEN_CYCLES` |
| `prompts/1_explore.md` | Genre-specific quality criteria for *your* doc |
| `prompts/2_execute.md` | Edit + judge logic; what counts as "better" |
| `draft.md` | Your starting document |
| `style_notes.md` | (Optional) constraints — voice, audience, tone, hard rules |

## How keep/revert works without a scalar oracle

The middle agent is the judge. To avoid self-certifying:

1. Before edit: save current text + write 3-line summary of its weaknesses
2. After edit: write 3-line summary of how the edit addressed those weaknesses
3. Compare both texts using **a separate cc-use dispatch** (fresh
   inner agent, no context of what you just did) asking it to pick
   the better version blindly (A vs B) with reasons
4. If blind judge picks the new version → commit. If old → revert. If
   tied → escalate to human.

This is the GAN-style discriminator-without-shared-context pattern.

## Anti-patterns

- Don't let the middle agent grade its own edits without the fresh
  inner judge. It will confirmation-bias toward keeping its work.
- Don't keep editing the same paragraph cycle after cycle. Force
  rotation — `prompts/1_explore.md` includes a "least recently touched"
  heuristic.
- Don't measure "length reduction" as quality. Sometimes shorter is
  better, sometimes not.
