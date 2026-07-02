"""perpetuum dashboard — web version.

Optional, read-mostly companion for watching (and lightly steering) a
running perpetuum task from a browser. Not installed by default and
not required for perpetuum itself to work — see references/dashboard.md
for when to offer this to the user.

Usage:
    uv run web.py --task-dir /path/to/project/.perpetuum/<task-name>
    Then either open the URL directly (if on the same machine) or, over
    SSH, forward the port first: ssh -L 8420:localhost:8420 <host>

Reads: plan.md / escalations.md / inbox.md / trigger.log / trigger.sh /
_meta.md / .memsearch/*, plus live tmux panes and `cc-use project-status`.

Writes: only what a human is already documented as allowed to write by
hand — inbox.md's Pending section, escalations.md's Resolved section,
and the .paused / .stop_after_current control flags. plan.md is never
touched.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import controls
import parsers

app = FastAPI(title="perpetuum dashboard")

STATE = {"task_dir": None, "agent": "claude", "cc_use_bin": ""}


def task_dir() -> Path:
    return STATE["task_dir"]


def project_root() -> Path:
    return task_dir().parent.parent


@app.get("/api/status")
def api_status():
    td = task_dir()
    status = parsers.parse_trigger_log(td)
    pending, done = parsers.parse_plan_md(td)
    started = parsers.task_started_at(td)

    eta = None
    if status.trigger_type == "schedule" and status.iter_max:
        eta = parsers.next_cycle_eta_seconds(td)

    return {
        "task_name": td.name,
        "trigger_type": status.trigger_type,
        "phase": status.phase,
        "iter_current": status.iter_current,
        "iter_max": status.iter_max,
        "cycles_seen": parsers.cycle_count_seen(td),
        "next_check_in_s": eta,
        "elapsed": parsers.format_elapsed(started),
        "pending": pending,
        "done": done,
        "work_done_estimate": parsers.dispatch_count_estimate(td),
        "paused": controls.is_paused(td),
        "stop_requested": controls.is_stop_requested(td),
    }


@app.get("/api/done")
def api_done(n: int = 15):
    return parsers.recent_done_items(task_dir(), n=n)


@app.get("/api/escalations")
def api_escalations():
    items = controls.list_open_escalations(task_dir())
    return [
        {"index": i, "title": title, "options": parsers.parse_escalation_options(block)}
        for i, (title, block) in enumerate(items)
    ]


@app.get("/api/inbox")
def api_inbox():
    return parsers.inbox_pending(task_dir())


@app.get("/api/sessions")
def api_sessions():
    sessions = parsers.list_watchable_sessions()
    l2 = parsers.read_middle_session(task_dir())
    cc = parsers.cc_use_status(STATE["cc_use_bin"], str(project_root()), STATE["agent"])
    l1 = cc.get("config", {}).get("session") if cc.get("config", {}).get("session_available") else None
    return {"sessions": sessions, "layer2_default": l2, "layer1_active": l1}


@app.get("/api/pane")
def api_pane(session: str, lines: int = 400):
    if not parsers.tmux_session_alive(session):
        raise HTTPException(404, "session not found")
    return {"session": session, "text": parsers.tmux_pane_full(session, scan=lines)}


@app.get("/api/history")
def api_history():
    return {
        "project_summary": parsers.read_project_memory_summary(project_root()),
        "days": parsers.list_memsearch_history(project_root()),
        "cycle_windows": parsers.cycle_time_windows(task_dir()),
    }


@app.get("/api/files")
def api_files():
    return parsers.list_task_files(task_dir())


@app.get("/api/file")
def api_file(path: str):
    try:
        return {"path": path, "content": parsers.read_task_file(task_dir(), path)}
    except ValueError as e:
        raise HTTPException(400, str(e))


class InboxIn(BaseModel):
    text: str


@app.post("/api/inbox")
def post_inbox(body: InboxIn):
    controls.push_inbox(task_dir(), body.text)
    return {"ok": True}


class ResolveIn(BaseModel):
    index: int
    answer: str


@app.post("/api/escalations/resolve")
def post_resolve(body: ResolveIn):
    ok = controls.resolve_escalation(task_dir(), body.index, body.answer)
    if not ok:
        raise HTTPException(400, "could not resolve — index out of range or file changed")
    return {"ok": True}


@app.post("/api/pause")
def post_pause():
    now_paused = not controls.is_paused(task_dir())
    controls.set_paused(task_dir(), now_paused)
    return {"paused": now_paused}


@app.post("/api/stop")
def post_stop():
    controls.request_stop_after_current(task_dir())
    return {"ok": True}


static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    return FileResponse(static_dir / "index.html")


def main() -> None:
    ap = argparse.ArgumentParser(description="perpetuum web dashboard")
    ap.add_argument("--task-dir", required=True, type=Path)
    ap.add_argument("--agent", default="claude")
    ap.add_argument("--cc-use-bin", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8420)
    args = ap.parse_args()

    STATE["task_dir"] = args.task_dir.resolve()
    STATE["agent"] = args.agent
    STATE["cc_use_bin"] = args.cc_use_bin or shutil.which("cc-use") or str(
        Path.home() / ".claude/skills/cc-use/scripts/cc-use"
    )

    import uvicorn

    print(f"perpetuum dashboard: http://{args.host}:{args.port}")
    print("Over SSH? Forward it first: ssh -L {0}:localhost:{0} <this-host>".format(args.port))
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
