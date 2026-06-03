# style-distill

Iteratively rewrite a draft article so its style converges on a target
author's corpus. This is the text-space analog of Karpathy's AutoResearch:
fixed corpus as evaluator, draft as editable asset, similarity score as
scalar metric, monotonic ratchet keeps only improvements.

## Task shape

- **Optimization-under-fixed-metric** — not a "find more bugs" loop, but
  a "make the draft closer to target" loop
- The corpus and the scoring function are **frozen** during the run.
  Only the draft changes.
- Each cycle:
  1. explore: pick a paragraph or stylistic axis to work on
  2. execute: rewrite, score, keep-if-improved else revert
- Trigger type: **schedule** (every ~20 min, until target score reached
  or MAX_ITER exhausted)

## When to use this example

- You want a new article to read like a specific author (yourself,
  someone you've studied, a brand voice)
- You have a corpus of that author's work (~10–50 articles, plain text)
- You can write or accept a scoring function (start with cosine
  similarity of embeddings; refine later)

## When NOT to use this example

- You want creative novelty more than style fidelity (the ratchet
  punishes novelty)
- The target style is too narrow (one paragraph of corpus → overfits
  to that exact wording)
- You don't have time to inspect intermediate drafts (this loop **can**
  optimize toward a degenerate "looks like target" without being good
  writing; sanity-check periodically)

## Required setup

```
.perpetuum/<task>/
├── trigger.sh, 1_explore.md, 2_execute.md, plan.md, inbox.md,
│   escalations.md, _meta.md  (standard)
├── draft.md                  ← the article you're polishing (you write the v0)
├── target_corpus/            ← directory of target author's articles
│   ├── article_001.md
│   ├── article_002.md
│   └── ...
└── style_score.py            ← scoring function (see template)
```

The agent commits to a git branch on every accepted edit. Reverts are
`git reset --hard HEAD~1`. The branch history *is* the ratchet log.

## How the ratchet works

```
agent reads draft.md + plan.md
agent edits one section of draft.md
score_before = python style_score.py target_corpus/ draft.md@HEAD~1
score_after  = python style_score.py target_corpus/ draft.md
if score_after > score_before + EPSILON:
    git commit                          # keep
    mark Done in plan.md with old→new score
else:
    git reset --hard HEAD~1             # revert
    mark Done in plan.md with old=new=score and "no improvement"
```

`EPSILON` lives at the top of `style_score.py`. Small enough that real
improvements pass, big enough that noise doesn't.

## Files

| File | Customize |
|---|---|
| `trigger.sh` | `MAX_ITER`, `SLEEP_BETWEEN_CYCLES` (shorter than testing — 15–20 min is fine) |
| `1_explore.md` | The "style dimensions" the agent should sample |
| `2_execute.md` | The exact `style_score.py` call signature you use |
| `style_score.py` | Replace the placeholder logic with your real scoring |
| `target_corpus/` | Put the target author's articles here |
| `draft.md` | Your starting draft |

## Anti-overfitting checklist

- Don't put just 1-2 corpus files. Aim for ≥10.
- Don't reuse the same corpus you used to *write* the v0 draft.
- Periodically read what the agent produced — does it still read as
  a coherent argument, or has it become "stylistic mush"?
- Consider a second oracle (LLM judge of "is this actually good writing?")
  layered on top of similarity score.
