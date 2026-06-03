# Task: choose the next paragraph to polish (plan only)

Steps:

1. Read `draft.md` end-to-end. Don't skim.

2. Read `plan.md` Done to see which sections have been recently
   touched, with what edit kinds, and what survived (KEPT) vs reverted.

3. Read `inbox.md` and `style_notes.md` (if exists). Apply.

4. Choose **one** section / paragraph to work on. Prioritize using:
   - Sections never touched this run
   - Sections with the largest gap between "what it tries to say" and
     "what it actually conveys"
   - Sections that other readers would skip / get bored / get lost on
   - Avoid: the strongest paragraphs (don't fix what isn't broken)
   - Avoid: sections touched in the last 3 cycles (rotation)

5. Decide what kind of edit:
   - Clarity (untangle phrasing)
   - Tightness (cut redundancy)
   - Flow (transitions, paragraph breaks)
   - Argument strength (sharpen claim, better evidence)
   - Voice (tone consistency, persona)
   - Opening / closing hook
   - Structure (move or merge)

6. Write a **3-line diagnosis** of the chosen section: what's wrong
   right now, in what way, and what direction the edit should go.
   This is the "before summary" — saved into plan.md Pending.

7. Append to plan.md Pending:

   ```
   - [ ] [<section>] [<edit kind>] short description
     - diagnosis: <3-line summary of what's wrong>
   ```

8. **Do not edit yet.**

9. Final action:

   ```
   echo "explore done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```
