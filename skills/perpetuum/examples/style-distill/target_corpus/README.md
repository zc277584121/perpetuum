# target_corpus

Place the target author's articles here, one per file.

## Format

- Plain `.md` or `.txt` files
- One article per file (not concatenated)
- File names don't matter; the score function globs `*.md` and `*.txt`

## Recommended size

- **Minimum: 5 articles** (oracle has too little signal otherwise)
- **Comfortable: 10–30 articles** (most use cases)
- **Diminishing returns past ~50** (oracle saturates)

## What to include

- Articles representative of the style you want
- Same author, similar genre / register (don't mix the author's
  technical blog with their fiction unless that's intentional)
- Recent enough to reflect current voice (style evolves over years)

## What NOT to include

- The starting `draft.md` itself (you'd be measuring distance to itself)
- Articles you wrote *with help from the same target* (circular oracle)
- Translations (the score function is roughly language-aware via the
  unicode range pattern, but mixing languages confuses it)

## After populating

Run a baseline:

```bash
python ../style_score.py . ../draft.md
```

…to see your starting score. Then launch `trigger.sh`.

## Replacing files mid-run

You can swap in new corpus files between cycles, but this **shifts the
oracle**. Existing score history becomes incomparable. Note the swap in
`inbox.md` so the agent (and future you) knows about the discontinuity.
