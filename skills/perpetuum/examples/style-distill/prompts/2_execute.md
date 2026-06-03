# Task: execute the planned edit and ratchet

The ratchet runs locally. **You apply the edit, score it, and either
commit or revert based on the score delta.** No human judgment involved
in keep-or-revert — the oracle decides.

Steps:

1. Read `plan.md` `## Pending` — there should be ≥1 Pending item from
   the explore phase. Pick the top one.

2. Record current state:

   ```bash
   cd .perpetuum/<TASK_NAME>
   SCORE_BEFORE=$(python style_score.py target_corpus/ draft.md)
   ```

3. Dispatch the edit. You can either:
   - Edit `draft.md` directly (simple cases)
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
   - Dispatch via `cc-use delegate` if the edit is involved
     (`--project /<abs-path>`, `--agent claude`, task = "rewrite the
     <section> of draft.md to <intended change>; don't change other
     sections")

4. Score the edit:

   ```bash
   SCORE_AFTER=$(python style_score.py target_corpus/ draft.md)
   ```

5. Ratchet decision:

   ```bash
   IMPROVEMENT=$(python -c "print(${SCORE_AFTER} - ${SCORE_BEFORE})")
   # If improvement > epsilon (defined in style_score.py top), keep.
   ```

   - **Improvement positive (above epsilon)**:
     - `git add draft.md`
     - `git commit -m "style: <section>: <one-line description>"`
     - In `plan.md` move item to Done with `status: KEPT score:<before>→<after>`
   - **No improvement (or worse)**:
     - `git checkout draft.md` (revert)
     - In `plan.md` move item to Done with `status: REVERTED score:<before>=<after>`
     - Optionally append a follow-up Pending item with a different approach

6. **No escalation for keep/revert** — that's the oracle's job. But
   escalate if:
   - The oracle has clearly broken (NaN, OOM, can't import)
   - The corpus is too sparse (score swings wildly between cycles)
   - You suspect the oracle is gameable and the score is improving
     but the writing is getting worse — write this to `escalations.md`
     so the human can sanity-check

7. Record. Every Done item:

   ```
   - [x] (cycle ${CYCLE_ID}) [<section>] [<edit kind>] short desc
     - operation: what was rewritten and how
     - observed: score <before> → <after> (delta: <diff>)
     - status: KEPT commit:abc1234 | REVERTED | ESCALATED
   ```

8. **🔴 Final action:**

   ```
   echo "execute done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

## When to stop

If the score plateaus for many cycles (e.g. 10 cycles in a row with no
KEPT edits), write that observation to `escalations.md` — it's a signal
the user should either:
- Reread the draft and decide if it's actually good (might be done!)
- Switch oracle (the current oracle has been exhausted)
- Add more target_corpus files (more signal for the agent to chase)
