# Task: plan this cycle's exploration (do not execute)

You can use any API keys / credentials available in `~/.bashrc` during
later test phases. They are available to the inner agent too.

Walk through these steps **and only these steps**:

1. Read the test history file (`.perpetuum/<task>/plan.md`) to know what
   was tested before and what fixes were already made.

2. Check the inbox (`.perpetuum/<task>/inbox.md`):
   - For each item in `## Pending`, decide how to act (SKIP / PRIORITIZE /
     ADD / STOP / DIRECTION / NOTE — treat plain-language items as NOTE)
   - Move processed items to `## Processed` with a one-line note on how
     they were applied to the plan
   - This shapes everything below

3. Look at the existing Pending items in `plan.md` — anything still
   uncompleted that should remain for this cycle?

4. Generate **new** exploration items for this cycle. Do an E2E
   testing pass over the project. List the testing dimensions that
   apply to this project, take their Cartesian product, and pick a
   sample of new combinations to explore.

   *Examples of dimensions* (replace with this project's actual axes
   when you customize this template):
   - **Surface**: CLI commands × subcommands × flags
   - **State**: empty / first-run / resumed / interrupted / restarted
   - **Backends**: each interchangeable backend (DB, cache, blob store, ...)
   - **Inputs**: small / large / boundary / malformed / unicode
   - **Connectors / integrations** (each provider with available keys)
   - **TUI flows** inside Claude Code / Codex (skills, hooks, MCP servers)
   - **SDKs** (each language client)
   - **Errors**: every documented error path

   Balance breadth vs depth — if recent cycles have repeatedly hit the
   same category, deliberately switch. If the plan has 8+ categories
   but each is shallow, go deeper instead. **You decide; don't lock
   yourself into a single strategy.**

5. Append new items to `plan.md` under `## Pending`. Format each as:

   ```
   - [ ] [<dimension>/<sub>] short description of what to test
   ```

   Don't number them. Don't add priorities unless you need to.

6. **Stop. Do not execute anything yet.** Execution is the next prompt.
   Just record the plan.

7. As the **last** action, run this shell command (don't forget!):

   ```
   echo "explore done ${CYCLE_ID}" > .perpetuum/<TASK_NAME>/state/.cycle_done_${CYCLE_ID}
   ```

   Replace `<TASK_NAME>` with the actual directory name where this file
   lives. The outer trigger.sh is waiting for this flag and will time
   out at 20 minutes of silence if you forget.
