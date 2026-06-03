# Task: edit + blind-judge + keep or revert

Steps:

1. Read the Pending item from `plan.md` (top one). Note the diagnosis.

2. Save a snapshot of the current section text (you'll need it for the
   blind judge):
   - Copy current text of the target section into a string `BEFORE_TEXT`

3. Apply the edit. Either directly or via cc-use dispatch (preferred
   for non-trivial edits — the fresh inner agent has no priors).

4. Save the new text as `AFTER_TEXT`.

5. **Blind judge** via a separate cc-use dispatch. This is the
   discriminator. The fresh inner agent has no context of what edit
   was made. Ask:

   > Here are two versions of the same paragraph from an article about
   > [topic]. Label them A and B in random order (you decide which is
   > which, don't tell me). Pick the better version with reasons.
   > Criteria: [list — clarity, tightness, persuasiveness, voice
   > consistency, factual accuracy]. If they are roughly equivalent,
   > say so.
   >
   > A:
   > [randomized order — either BEFORE or AFTER]
   >
   > B:
   > [the other one]

   The dispatch must include the article's overall topic / argument
   so the judge isn't picking purely on stylistic local quality.

6. Decision based on judge's verdict:
   - **Judge picks AFTER** → commit:
     `git commit -m "polish: <section>: <edit kind> — <one-line>"`
     Move to Done, status `KEPT`.
   - **Judge picks BEFORE** → revert: `git checkout draft.md`
     Move to Done, status `REVERTED`.
   - **Judge says tied** → escalate. Move to escalations.md with both
     versions and the judge's reasoning. Mark `[→]` in plan.md.

7. Record. Every Done item:

   ```
   - [x] (cycle ${CYCLE_ID}) [<section>] [<edit kind>] short title
     - diagnosis: <from explore phase>
     - edit summary: what changed
     - judge's verdict: A | B | tied
     - status: KEPT commit:abc1234 | REVERTED | ESCALATED
   ```

8. **🔴 Final action:**

   ```
   echo "execute done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

## Anti-self-certifying guardrails

- The blind judge **must** be a separate cc-use dispatch (fresh
  context). Do not judge the edit yourself using the middle TUI's
  conversation history — you've seen the edit being made and will be
  biased.
- The randomization of A/B order is non-negotiable. Without it the
  judge defaults to "A" disproportionately.
- If the judge consistently picks "AFTER" for 5 cycles straight, that
  is a *suspicious* signal (either you're a great editor or the judge
  is biased). Note it in plan.md as a flag for the human.
