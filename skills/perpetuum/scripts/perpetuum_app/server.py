"""Local HTTP API and static frontend."""

from __future__ import annotations

import json
import mimetypes
import os
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from . import storage


PROJECT_PATH = re.compile(r"^/api/projects/([^/]+)(?:/(inbox|response|control))?$")


def process_alive(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def project_summary(home: Path, project_id: str, activation: Dict[str, Any]) -> Dict[str, Any]:
    project = storage.load_project(home, project_id) or {}
    state = storage.load_project_state(home, project_id)
    latest_report = storage.read_text(
        storage.project_dir(home, project_id) / "reports" / "latest.md",
        limit=50_000,
    )
    entry = activation.get("projects", {}).get(project_id, {})
    return {
        "id": project_id,
        "name": project.get("name", project_id),
        "path": project.get("path", ""),
        "agent": project.get("agent", {}),
        "status": state.get("status", "unknown"),
        "current_task": state.get("current_task"),
        "last_activity_at": state.get("last_activity_at"),
        "last_result": state.get("last_result"),
        "paused": bool(entry.get("paused", False)),
        "enabled": bool(entry.get("enabled", True)),
        "windows": entry.get("windows", []),
        "latest_report": latest_report,
    }


def global_status(home: Path) -> Dict[str, Any]:
    activation = storage.ensure_home(home)
    runner_state = storage.read_json(
        storage.runner_state_path(home),
        storage.default_runner_state(),
    )
    service = runner_state.get("service", {})
    service["alive"] = process_alive(service.get("pid"))
    projects = [
        project_summary(home, project_id, activation)
        for project_id in storage.list_project_ids(home)
    ]
    return {
        "home": str(home),
        "activation": activation,
        "runner": runner_state,
        "projects": projects,
    }


def project_detail(home: Path, project_id: str) -> Dict[str, Any]:
    activation = storage.ensure_home(home)
    if project_id not in activation.get("projects", {}):
        raise KeyError(project_id)
    harness = storage.project_dir(home, project_id)
    files = {}
    for name in (
        "goal.md",
        "plan.md",
        "history.md",
        "inbox.md",
        "questions.md",
        "escalations.md",
    ):
        files[name] = storage.read_text(harness / name)
    files["reports/latest.md"] = storage.read_text(harness / "reports" / "latest.md")
    files["runtime/events.log"] = storage.read_text(
        harness / "runtime" / "events.log",
        limit=200_000,
    )
    return {
        "summary": project_summary(home, project_id, activation),
        "project": storage.load_project(home, project_id),
        "runtime": storage.load_project_state(home, project_id),
        "files": files,
    }


def read_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0 or length > 1_000_000:
        raise ValueError("请求内容为空或过大")
    raw = handler.rfile.read(length)
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("请求必须是 JSON 对象")
    return value


def handler_factory(home: Path) -> Any:
    static_root = Path(__file__).resolve().parent / "frontend"

    class Handler(BaseHTTPRequestHandler):
        server_version = "Perpetuum/0.2"

        def log_message(self, format_string: str, *args: Any) -> None:
            del format_string, args

        def send_json(self, value: Any, status: int = 200) -> None:
            data = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def send_error_json(self, status: int, message: str) -> None:
            self.send_json({"ok": False, "error": message}, status)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/status":
                self.send_json(global_status(home))
                return
            match = PROJECT_PATH.fullmatch(parsed.path)
            if match and not match.group(2):
                try:
                    self.send_json(project_detail(home, unquote(match.group(1))))
                except KeyError:
                    self.send_error_json(HTTPStatus.NOT_FOUND, "项目不存在")
                return
            self.serve_static(parsed.path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            match = PROJECT_PATH.fullmatch(parsed.path)
            if not match or not match.group(2):
                self.send_error_json(HTTPStatus.NOT_FOUND, "接口不存在")
                return
            project_id = unquote(match.group(1))
            action = match.group(2)
            try:
                body = read_body(self)
                if storage.load_project(home, project_id) is None:
                    raise KeyError(project_id)
                if action == "inbox":
                    storage.append_human_message(
                        storage.project_dir(home, project_id) / "inbox.md",
                        "前端指令",
                        str(body.get("text", "")),
                    )
                    storage.append_event(
                        storage.runner_events_path(home),
                        "human_message_added",
                        project_id=project_id,
                        channel="inbox",
                    )
                elif action == "response":
                    channel = str(body.get("channel", "questions"))
                    if channel not in {"questions", "escalations"}:
                        raise ValueError("回复通道必须是 questions 或 escalations")
                    storage.append_human_message(
                        storage.project_dir(home, project_id) / f"{channel}.md",
                        "人类回复",
                        str(body.get("text", "")),
                    )
                    storage.append_event(
                        storage.runner_events_path(home),
                        "human_message_added",
                        project_id=project_id,
                        channel=channel,
                    )
                elif action == "control":
                    control_action = str(body.get("action", ""))
                    if control_action == "window":
                        windows = body.get("windows", [])
                        if not isinstance(windows, list):
                            raise ValueError("时间窗口必须是列表")
                        storage.set_project_windows(home, project_id, windows)
                    else:
                        storage.update_project_control(
                            home,
                            project_id,
                            control_action,
                        )
                self.send_json({"ok": True})
            except KeyError:
                self.send_error_json(HTTPStatus.NOT_FOUND, "项目不存在")
            except (ValueError, json.JSONDecodeError) as exc:
                self.send_error_json(HTTPStatus.BAD_REQUEST, str(exc))
            except OSError as exc:
                self.send_error_json(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

        def serve_static(self, request_path: str) -> None:
            relative = "index.html" if request_path == "/" else request_path.lstrip("/")
            candidate = (static_root / relative).resolve()
            if static_root not in candidate.parents and candidate != static_root:
                self.send_error_json(HTTPStatus.FORBIDDEN, "禁止访问")
                return
            if not candidate.is_file():
                self.send_error_json(HTTPStatus.NOT_FOUND, "页面不存在")
                return
            data = candidate.read_bytes()
            content_type = mimetypes.guess_type(str(candidate))[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    return Handler


class RuntimeServer:
    def __init__(self, home: Path, host: str, port: int) -> None:
        self.server = ThreadingHTTPServer((host, port), handler_factory(home))
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self.thread = threading.Thread(
            target=self.server.serve_forever,
            name="perpetuum-http",
            daemon=True,
        )
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=5)
