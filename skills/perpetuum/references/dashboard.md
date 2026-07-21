# Dashboard: optional web UI for watching (and lightly steering) a task

This is **not installed or run by default**. It lives at
`scripts/dashboard/` inside this skill and has its own `uv`-managed
Python dependencies (FastAPI + Uvicorn) — it is not part of the core
perpetuum mechanism, which stays pure bash + file contract with zero
dependency on this existing. Don't set it up just because a task
started; only set it up when the user actually asks for a visual way
to watch a task.

## When to offer it

If the user asks to "see", "watch", "view", or "visualize" a running
perpetuum task (rather than reading `plan.md`/`escalations.md`
directly or asking you for a status summary), this is the tool.

**Always ask before running it** — it needs `uv` installed and pulls
its own dependencies on first run (network access, a few seconds).
Don't assume the user wants this just because a task exists. A good
prompt: "Want a live dashboard for this task? It's a small local web
server (needs `uv`), read-mostly, and lets you pause/resume/answer
questions from a browser instead of editing files by hand."

## What it needs

- `uv` on PATH (same as any other Python tooling in this ecosystem).
- The task must already be running (has a `.perpetuum/<task>/` directory
  with `plan.md` etc.) — this only reads/writes the same file contract
  everything else in this skill uses.

## Launching it

```bash
cd <perpetuum-skill-dir>/scripts/dashboard
uv run web.py --task-dir /abs/path/to/project/.perpetuum/<task-name>
```

Default port is `8420`, bound to `127.0.0.1` only (not exposed to the
network). If the user is on a remote machine over SSH, tell them to
forward the port before opening it in a browser:

```bash
ssh -L 8420:localhost:8420 <the-remote-host>
```

Then open `http://localhost:8420` locally. Don't bind it to `0.0.0.0`
or otherwise expose it on the network — it has write endpoints (pause,
inbox, resolving escalations), and there's no auth in front of it.

## What it does

- **Live tab**: progress (branches on trigger type — `schedule` shows a
  round counter + ETA; `conditional`/`webhook` show an event count
  instead, since there's no fixed total for those), a session picker
  that mirrors any live tmux pane read-only (pure `capture-pane`
  snapshots — never a live `attach`, so it cannot perturb the running
  session), recent Done items, open
  escalations (answerable via option buttons when the escalation
  listed options, always with a free-text fallback), pause/resume,
  graceful stop, and pushing a note to `inbox.md`.
- **History tab**: read-only. If `.memsearch/` is configured for the
  project, this surfaces `.memsearch/memory/*.md` and `PROJECT.md` —
  memsearch keys memory by project path, not by tmux session, so
  Layer 1 and Layer 2 activity is naturally interleaved into one
  chronological feed here; this deliberately does not try to
  split it back into "Layer 1 vs Layer 2" or force entries into exact
  "cycle N" boxes — trigger.log's cycle boundaries are used only for a
  best-effort "cycle ~N" hint, not an exact mapping. If memsearch
  isn't configured, this tab is just empty — that's fine, it's not a
  hard dependency.
- **Files tab**: read-only browser for every file under this task's
  `.perpetuum/<task>/` directory — both prompts, `trigger.sh`,
  `_meta.md`, and the raw `plan.md`/`inbox.md`/`escalations.md`. There
  is no write path from this tab; the API endpoint validates the
  requested path can't escape the task directory (no `../` traversal).

## What it never touches

Same boundary as everything else in this skill: `plan.md` is
agent-owned and never written by the dashboard. Writes are limited to
`inbox.md`'s Pending section, `escalations.md`'s Resolved section, and
the `.paused` / `.stop_after_current` control flags — the same things
a human is already documented as allowed to edit by hand in
`references/feedback.md` and `references/control.md`.
