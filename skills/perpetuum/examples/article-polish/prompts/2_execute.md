# Task: edit + blind-judge + keep or revert

Steps:

1. Read the Pending item from `plan.md` (top one). Note the diagnosis.

2. Save a snapshot of the current section text (you'll need it for the
   blind judge):
   - Copy current text of the target section into a string `BEFORE_TEXT`

> ⚠️ **Important: `cc-use` is an installed Agent Skill, not a shell command.**
> Use it via your host agent's skill mechanism (your host will load
> cc-use's SKILL.md and know how to dispatch the inner agent). **Do not**
> run `cc-use` directly with the Bash tool — that bypasses the skill
> protocol and will fail.
>
> If your environment does not recognize `cc-use` as a skill, or `cc-use`
> reports an inner-agent startup failure (a known issue exists for Codex
> outer agents in `--dangerously-bypass-approvals-and-sandbox` mode where
> cc-use's hardcoded `--ask-for-approval` / `--sandbox` flags clash —
> upstream cc-use issue, not perpetuum): **do not fall back to
> Bash-running cc-use, do not spawn a sub-agent yourself, do not write
> the work into this session's context directly.** Surface it as a
> blocked-on-environment escalation to `escalations.md` and stop the
> cycle there. The whole point of the three-layer architecture is the
> fresh-context inner agent; faking it locally defeats the purpose.
3. Apply the edit. Either directly or via cc-use dispatch (preferred
   for non-trivial edits — the fresh inner agent has no priors). If you
   dispatch, require a fresh, no-memory inner session. With the current
   `cc-use` helper, that means every `delegate` call must use
   `--replace`; if `cc-use` later changes its fresh-start mechanism,
   use the documented replacement mechanism and update this prompt.

4. Save the new text as `AFTER_TEXT`.

5. **Blind judge** via a separate cc-use dispatch. This is the
   discriminator. The fresh inner agent has no context of what edit
   was made. This dispatch also requires a fresh, no-memory session;
   with the current `cc-use` helper, every `delegate` call must use
   `--replace`. Ask:

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
