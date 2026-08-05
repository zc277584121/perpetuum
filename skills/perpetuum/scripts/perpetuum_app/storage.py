"""File-backed storage for the Perpetuum runtime."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


DEFAULT_ACTIVATION = {
    "version": 1,
    "timezone": "Asia/Shanghai",
    "poll_interval_minutes": 30,
    "report": {
        "enabled": True,
        "time": "09:00",
        "force": False,
    },
    "service": {
        "host": "127.0.0.1",
        "port": 8765,
        "heartbeat_seconds": 5,
        "agent_startup_seconds": 8,
        "stop_requested": False,
        "restart_requested": False,
    },
    "projects": {},
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def runtime_home(explicit: Optional[Path] = None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("PERPETUUM_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".perpetuum").resolve()


def activation_path(home: Path) -> Path:
    return home / "activation.yaml"


def runner_dir(home: Path) -> Path:
    return home / "runner"


def runner_state_path(home: Path) -> Path:
    return runner_dir(home) / "state.json"


def runner_events_path(home: Path) -> Path:
    return runner_dir(home) / "events.log"


def projects_dir(home: Path) -> Path:
    return home / "projects"


def project_dir(home: Path, project_id: str) -> Path:
    return projects_dir(home) / project_id


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError):
        return default


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=str(path.parent),
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def write_json(path: Path, value: Any) -> None:
    atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
    )


def append_event(path: Path, event: str, **fields: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"time": utc_now(), "event": event}
    payload.update(fields)
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, line.encode("utf-8"))
    finally:
        os.close(descriptor)


def ensure_home(home: Path) -> Dict[str, Any]:
    home.mkdir(parents=True, exist_ok=True)
    runner_dir(home).mkdir(parents=True, exist_ok=True)
    projects_dir(home).mkdir(parents=True, exist_ok=True)

    config = read_json(activation_path(home))
    if not isinstance(config, dict):
        config = json.loads(json.dumps(DEFAULT_ACTIVATION))
        write_json(activation_path(home), config)
    else:
        merged = merge_defaults(config, DEFAULT_ACTIVATION)
        if merged != config:
            write_json(activation_path(home), merged)
        config = merged

    state = read_json(runner_state_path(home))
    if not isinstance(state, dict):
        state = default_runner_state()
        write_json(runner_state_path(home), state)
    runner_events_path(home).touch(exist_ok=True)
    return config


def merge_defaults(value: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(value)
    for key, default in defaults.items():
        if key not in result:
            result[key] = json.loads(json.dumps(default))
        elif isinstance(default, dict) and isinstance(result[key], dict):
            result[key] = merge_defaults(result[key], default)
    return result


def default_runner_state() -> Dict[str, Any]:
    return {
        "version": 1,
        "service": {
            "status": "stopped",
            "pid": None,
            "started_at": None,
            "stopped_at": None,
        },
        "last_tick_at": None,
        "last_activation_check_at": None,
        "next_activation_check_at": None,
        "last_report_date": None,
        "active_root": None,
        "active_reporter": None,
        "last_error": None,
    }


def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    normalized = re.sub(r"-+", "-", normalized).strip("-_")
    return normalized or "project"


def project_id_for_path(path: Path) -> str:
    resolved = str(path.expanduser().resolve())
    digest = hashlib.sha1(resolved.encode("utf-8")).hexdigest()[:8]
    return f"{slugify(path.name)}-{digest}"


def detect_agent_kind() -> str:
    if os.environ.get("CLAUDECODE") or os.environ.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude"
    if os.environ.get("CODEX_THREAD_ID") or os.environ.get("CODEX_CI"):
        return "codex"
    return "codex"


def agent_command(kind: str) -> str:
    return "claude" if kind == "claude" else "codex"


def validate_window(window: str) -> str:
    if "-" not in window:
        raise ValueError("时间窗口必须使用 HH:MM-HH:MM 格式")
    start, end = window.split("-", 1)
    for value, allow_24 in ((start, False), (end, True)):
        match = re.fullmatch(r"(\d{2}):(\d{2})", value)
        if not match:
            raise ValueError("时间窗口必须使用 HH:MM-HH:MM 格式")
        hour, minute = int(match.group(1)), int(match.group(2))
        if minute > 59 or hour > 24 or (hour == 24 and (minute != 0 or not allow_24)):
            raise ValueError("时间窗口包含无效时间")
    return window


def register_project(
    home: Path,
    path: Path,
    name: Optional[str] = None,
    project_id: Optional[str] = None,
    agent: Optional[str] = None,
    window: str = "00:00-24:00",
) -> str:
    config = ensure_home(home)
    resolved = path.expanduser().resolve()
    if not resolved.is_dir():
        raise ValueError(f"项目目录不存在：{resolved}")

    validate_window(window)
    selected_agent = agent or detect_agent_kind()
    if selected_agent not in {"codex", "claude"}:
        raise ValueError("Agent 只能是 codex 或 claude")

    selected_id = slugify(project_id) if project_id else project_id_for_path(resolved)
    harness = project_dir(home, selected_id)
    harness.mkdir(parents=True, exist_ok=True)
    (harness / "reports").mkdir(exist_ok=True)
    (harness / "runtime").mkdir(exist_ok=True)

    display_name = name or resolved.name
    project_config_path = harness / "project.yaml"
    existing_project = read_json(project_config_path)
    if isinstance(existing_project, dict):
        existing_path = Path(str(existing_project.get("path", ""))).expanduser()
        if existing_path and existing_path.resolve() != resolved:
            raise ValueError(f"项目 ID 已被其他目录使用：{selected_id}")

    project_config = {
        "version": 1,
        "id": selected_id,
        "name": display_name,
        "path": str(resolved),
        "agent": {
            "kind": selected_agent,
            "command": agent_command(selected_agent),
        },
        "created_at": (
            existing_project.get("created_at")
            if isinstance(existing_project, dict)
            else utc_now()
        ),
        "updated_at": utc_now(),
    }
    write_json(project_config_path, project_config)

    templates = project_templates(display_name, resolved)
    for relative, content in templates.items():
        target = harness / relative
        if not target.exists():
            atomic_write_text(target, content)

    runtime_state = harness / "runtime" / "state.json"
    if not runtime_state.exists():
        write_json(
            runtime_state,
            {
                "version": 1,
                "status": "idle",
                "current_task": None,
                "active_sessions": [],
                "last_activity_at": utc_now(),
                "last_result": "项目已注册，等待首次激活。",
            },
        )
    (harness / "runtime" / "events.log").touch(exist_ok=True)

    projects = config.setdefault("projects", {})
    existing_activation = projects.get(selected_id, {})
    projects[selected_id] = {
        "enabled": existing_activation.get("enabled", True),
        "paused": existing_activation.get("paused", False),
        "force_run": existing_activation.get("force_run", False),
        "windows": existing_activation.get("windows", [window]),
    }
    if not existing_activation:
        projects[selected_id]["windows"] = [window]
    write_json(activation_path(home), config)
    append_event(
        runner_events_path(home),
        "project_registered",
        project_id=selected_id,
        project_path=str(resolved),
    )
    return selected_id


def project_templates(name: str, path: Path) -> Dict[str, str]:
    return {
        "goal.md": (
            f"# {name}：长期目标\n\n"
            "## 目标\n\n"
            "请在启动前补充经过人类确认的长期目标。\n\n"
            "## 背景与当前进度\n\n"
            f"- 项目目录：`{path}`\n"
            "- 请补充已有成果、已知问题和重要决定。\n\n"
            "## 可用资源\n\n"
            "- 请补充机器、数据、服务、工具和权限。\n\n"
            "## 边界与底线\n\n"
            "- 不自动更新 Agent、Skill、插件或认证配置。\n"
            "- 请补充成本、安全、合规和业务边界。\n\n"
            "## 进展证据\n\n"
            "- 请说明哪些测试、实验、产物或指标可以证明真实进展。\n"
        ),
        "plan.md": (
            "# Task 计划\n\n"
            "## 当前 Task\n\n"
            "暂无。\n\n"
            "## 候选 Task\n\n"
            "等待 Explorer 根据 Goal 和项目证据建立。\n\n"
            "## 暂不处理\n\n"
            "暂无。\n"
        ),
        "history.md": (
            "# 可信历史\n\n"
            "只记录已完成 Task 的精简结论、证据和重要决定；"
            "不记录每次轮询或每轮对话。\n"
        ),
        "inbox.md": (
            "# 人类指令\n\n"
            "## 已处理\n\n"
            "暂无。\n\n"
            "## 人类追加（待处理）\n\n"
            "暂无。\n"
        ),
        "questions.md": (
            "# 业务问题\n\n"
            "## 待人类回答\n\n"
            "暂无。\n\n"
            "## 已吸收\n\n"
            "暂无。\n\n"
            "## 人类回复（追加区）\n\n"
            "暂无。\n"
        ),
        "escalations.md": (
            "# 管控异常\n\n"
            "## 待处理\n\n"
            "暂无。\n\n"
            "## 已恢复\n\n"
            "暂无。\n\n"
            "## 人类回复（追加区）\n\n"
            "暂无。\n"
        ),
        "reports/latest.md": (
            f"# {name}：最新日报\n\n"
            "尚未生成日报。\n"
        ),
    }


def list_project_ids(home: Path) -> List[str]:
    config = ensure_home(home)
    projects = config.get("projects", {})
    return sorted(projects.keys()) if isinstance(projects, dict) else []


def load_project(home: Path, project_id: str) -> Optional[Dict[str, Any]]:
    value = read_json(project_dir(home, project_id) / "project.yaml")
    return value if isinstance(value, dict) else None


def load_project_state(home: Path, project_id: str) -> Dict[str, Any]:
    value = read_json(project_dir(home, project_id) / "runtime" / "state.json")
    return value if isinstance(value, dict) else {}


def read_text(path: Path, limit: int = 500_000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ""
    if len(data) > limit:
        data = data[-limit:]
        prefix = "……文件较大，仅显示末尾内容……\n\n"
    else:
        prefix = ""
    return prefix + data.decode("utf-8", errors="replace")


def append_human_message(path: Path, title: str, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = text.strip()
    if not clean:
        raise ValueError("内容不能为空")
    block = f"\n\n### {title} · {utc_now()}\n\n{clean}\n"
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, block.encode("utf-8"))
    finally:
        os.close(descriptor)


def update_project_control(home: Path, project_id: str, action: str) -> None:
    config = ensure_home(home)
    projects = config.get("projects", {})
    if project_id not in projects:
        raise ValueError(f"未知项目：{project_id}")
    entry = projects[project_id]
    if action == "pause":
        entry["paused"] = True
    elif action == "resume":
        entry["paused"] = False
    elif action == "run":
        entry["force_run"] = True
    else:
        raise ValueError(f"未知控制动作：{action}")
    write_json(activation_path(home), config)
    append_event(
        runner_events_path(home),
        "project_control",
        project_id=project_id,
        action=action,
    )


def set_project_windows(home: Path, project_id: str, windows: List[str]) -> None:
    if not windows:
        raise ValueError("至少需要一个时间窗口")
    normalized = [validate_window(str(window).strip()) for window in windows]
    config = ensure_home(home)
    projects = config.get("projects", {})
    if project_id not in projects:
        raise ValueError(f"未知项目：{project_id}")
    projects[project_id]["windows"] = normalized
    write_json(activation_path(home), config)
    append_event(
        runner_events_path(home),
        "project_windows_updated",
        project_id=project_id,
        windows=normalized,
    )


def consume_project_force_flags(
    home: Path, project_ids: Iterable[str]
) -> None:
    config = ensure_home(home)
    changed = False
    projects = config.get("projects", {})
    for project_id in project_ids:
        entry = projects.get(project_id)
        if isinstance(entry, dict) and entry.get("force_run"):
            entry["force_run"] = False
            changed = True
    if changed:
        write_json(activation_path(home), config)
