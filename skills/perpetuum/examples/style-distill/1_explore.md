# Task: plan this cycle's stylistic edit (do not edit yet)

You are iteratively rewriting `draft.md` to match the style of the
target author whose work is in `target_corpus/`. The score function
`style_score.py` is the oracle — higher score = closer to target.

Steps:

1. Read `draft.md` (current state) and `plan.md` (history of edits and
   scores). Note the current score (last `score_after` in Done log).

2. Read `inbox.md` `## Pending` and apply.

3. Read 2–3 random files from `target_corpus/` to refresh your sense
   of the target style — *not* to copy specific phrases, but to feel
   the rhythm, vocabulary, sentence length, paragraph structure.

4. Look at `draft.md` and pick **one** section / paragraph / sentence
   to work on this cycle. The choice should:
   - Be small enough to edit in one focused pass (one paragraph, one
     transition, one opening line)
   - Be where the gap between current and target style feels biggest
     (clunky phrasing, mismatched tone, wrong cadence)
   - Avoid sections recently edited (check plan.md Done)

5. Decide *what kind* of edit:
   - sentence-length adjustment
   - vocabulary swap (toward target's word choice)
   - rhythm / cadence
   - paragraph reorganization
   - opening / closing line strengthening
   - transition tightening
   - voice / persona (active vs passive, distance, formality)

6. Append to `plan.md` `## Pending`:

   ```
   - [ ] [<section>] [<edit kind>] short description of intended change
   ```

7. **Don't make the edit yet.** Execution next.

8. Final action:

   ```
   echo "explore done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

## A note on overfitting

If recent cycles have all been the same edit kind, **deliberately
switch** — pick a different stylistic axis. The risk with style-distill
is the agent finds one cheap way to bump the score (e.g. shortening all
sentences) and optimizes only that.
