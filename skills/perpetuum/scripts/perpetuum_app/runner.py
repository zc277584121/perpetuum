"""Background scheduler and top-level session lifecycle."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import scheduler, sessions, storage
from .server import RuntimeServer


def parse_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class Runner:
    def __init__(self, home: Path) -> None:
        self.home = home
        self.skill_root = Path(__file__).resolve().parents[2]
        self.state = storage.read_json(
            storage.runner_state_path(home),
            storage.default_runner_state(),
        )
        if not isinstance(self.state, dict):
            self.state = storage.default_runner_state()
        self.force_stop = False

    def save_state(self) -> None:
        storage.write_json(storage.runner_state_path(self.home), self.state)

    def event(self, event: str, **fields: Any) -> None:
        storage.append_event(storage.runner_events_path(self.home), event, **fields)

    def safe_run_dir(self, run_dir: Path) -> bool:
        root = (storage.runner_dir(self.home) / "runs").resolve()
        try:
            relative = run_dir.resolve().relative_to(root)
        except (OSError, ValueError):
            return False
        return bool(relative.parts)

    def cleanup_run_dir(self, run_dir: Path) -> None:
        if self.safe_run_dir(run_dir):
            shutil.rmtree(run_dir, ignore_errors=True)
            return
        self.event("unsafe_run_dir_ignored", run_dir=str(run_dir))

    def activation_check_due(self, config: Dict[str, Any], now: datetime) -> bool:
        projects = config.get("projects", {})
        if isinstance(projects, dict):
            if any(
                isinstance(entry, dict) and entry.get("force_run", False)
                for entry in projects.values()
            ):
                return True
        last = parse_utc(self.state.get("last_activation_check_at"))
        interval = max(1, int(config.get("poll_interval_minutes", 30)))
        return last is None or now - last >= timedelta(minutes=interval)

    def update_next_check(self, config: Dict[str, Any], now: datetime) -> None:
        interval = max(1, int(config.get("poll_interval_minutes", 30)))
        self.state["last_activation_check_at"] = storage.utc_now()
        self.state["next_activation_check_at"] = (
            now + timedelta(minutes=interval)
        ).isoformat().replace("+00:00", "Z")

    def project_payloads(self, project_ids: List[str]) -> List[Dict[str, Any]]:
        payloads = []
        for project_id in project_ids:
            project = storage.load_project(self.home, project_id)
            if not project:
                self.write_control_escalation(
                    project_id,
                    "Runner 找不到项目配置",
                    "项目已在 activation.yaml 注册，但 project.yaml 缺失或无法解析。",
                    "本次不会启动该项目。请检查项目 Harness 是否被移动或损坏。",
                )
                continue
            project_path = Path(str(project.get("path", ""))).expanduser()
            if not project_path.is_dir():
                self.write_control_escalation(
                    project_id,
                    "Runner 无法访问项目目录",
                    f"project.yaml 指向的目录不存在或不可访问：{project_path}",
                    "本次不会启动该项目。请恢复目录或修正 project.yaml 后再验证。",
                )
                continue
            raw_agent = project.get("agent", {})
            agent = raw_agent if isinstance(raw_agent, dict) else {}
            kind = str(agent.get("kind", "codex"))
            if kind not in {"codex", "claude"}:
                self.write_control_escalation(
                    project_id,
                    "Runner 无法识别 Agent 类型",
                    f"project.yaml 中的 Agent 类型无效：{kind}",
                    "本次不会启动该项目。请把 Agent 类型修正为 codex 或 claude。",
                )
                continue
            payloads.append(
                {
                    "id": project_id,
                    "name": project.get("name", project_id),
                    "path": str(project_path.resolve()),
                    "harness": str(storage.project_dir(self.home, project_id)),
                    "agent": {"kind": kind},
                }
            )
        return payloads

    def create_dispatch(
        self,
        role: str,
        projects: List[Dict[str, Any]],
    ) -> Tuple[Path, Path, Path, str]:
        run_id = (
            f"{role}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-"
            f"{os.getpid()}-{time.monotonic_ns() % 1_000_000:06d}"
        )
        run_dir = storage.runner_dir(self.home) / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        dispatch_path = run_dir / "dispatch.json"
        receipt_path = run_dir / "receipt.json"
        templates_dir = self.skill_root / "references" / "templates"
        references = {
            "architecture": str(self.skill_root / "references" / "architecture.md"),
            "root_supervisor": str(templates_dir / "root-supervisor.md"),
            "project_supervisor": str(templates_dir / "project-supervisor.md"),
            "task_supervisor": str(templates_dir / "task-supervisor.md"),
            "explorer": str(templates_dir / "explorer.md"),
            "executor": str(templates_dir / "executor.md"),
            "validator": str(templates_dir / "validator.md"),
            "reporter": str(templates_dir / "reporter.md"),
            "human_communication": str(
                self.skill_root / "references" / "human-communication.md"
            ),
            "runtime": str(self.skill_root / "references" / "runtime.md"),
        }
        dispatch = {
            "version": 1,
            "role": role,
            "run_id": run_id,
            "created_at": storage.utc_now(),
            "perpetuum_home": str(self.home),
            "runner_state": str(storage.runner_state_path(self.home)),
            "projects": projects,
            "references": references,
            "receipt_path": str(receipt_path),
        }
        storage.write_json(dispatch_path, dispatch)
        return run_dir, dispatch_path, receipt_path, run_id

    def build_prompt(
        self,
        role: str,
        dispatch_path: Path,
        receipt_path: Path,
    ) -> str:
        if role == "root":
            role_name = "Root Supervisor"
            primary_reference = (
                self.skill_root
                / "references"
                / "templates"
                / "root-supervisor.md"
            )
            task = (
                "按照 dispatch 中的项目列表，从 Root 向下调用 Project Supervisor，"
                "让每个项目至多推进一个 Task，并汇总所有项目结果。"
            )
        else:
            role_name = "Reporter"
            primary_reference = (
                self.skill_root / "references" / "templates" / "reporter.md"
            )
            task = "独立检查所有已注册项目和 Runner 健康，并分别写入今天的项目日报。"

        return f"""你现在是 Perpetuum 的 {role_name}。

先完整读取：
1. dispatch：{dispatch_path}
2. 角色规范：{primary_reference}
3. dispatch 中列出的其他必要 References

本次任务：{task}

严格遵守：
- 所有 Agent 上下级调用使用当前安装的 cc-use Skill，并使用唯一 session；不要在这里硬编码或猜测 cc-use 命令。
- 不自动更新 Codex、Claude Code、Skill、插件、模型或认证配置；遇到更新提示时跳过。
- 不使用非交互式 Agent 模式代替 TUI。
- 无论成功、Idle、部分失败还是无法继续，都要关闭你创建的直属子 session。
- 最后把一个 JSON 对象原子写入 {receipt_path}。至少包含 status、summary、projects、finished_at；先写同目录临时文件，再 rename。
- 写完回执后等待 Runner 回收当前 session，不要自行启动新的长期循环。
"""

    def launch_top_level(
        self,
        role: str,
        project_ids: List[str],
        config: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        projects = self.project_payloads(project_ids)
        if not projects:
            return None

        run_dir, dispatch_path, receipt_path, run_id = self.create_dispatch(
            role,
            projects,
        )
        first_agent = projects[0].get("agent", {})
        kind = str(first_agent.get("kind", "codex"))
        startup_seconds = int(
            config.get("service", {}).get("agent_startup_seconds", 8)
        )
        prompt = self.build_prompt(role, dispatch_path, receipt_path)
        try:
            command = sessions.agent_command(kind)
            session = sessions.launch_session(
                role=role,
                command=command,
                cwd=Path(projects[0]["path"]),
                prompt=prompt,
                startup_seconds=startup_seconds,
                kind=kind,
            )
        except Exception as exc:
            self.cleanup_run_dir(run_dir)
            for project in projects:
                self.write_control_escalation(
                    project["id"],
                    f"无法启动 {role} session",
                    str(exc),
                    "Runner 已停止本次顶层调用。请检查 tmux、Agent TUI、环境变量和认证，再使用“立即运行”验证。",
                )
            self.state["last_error"] = str(exc)
            self.event(
                "top_session_launch_failed",
                role=role,
                project_ids=[project["id"] for project in projects],
                error=str(exc),
            )
            return None

        active = {
            "role": role,
            "run_id": run_id,
            "session": session,
            "project_ids": [project["id"] for project in projects],
            "dispatch_path": str(dispatch_path),
            "receipt_path": str(receipt_path),
            "run_dir": str(run_dir),
            "started_at": storage.utc_now(),
        }
        self.event(
            "top_session_started",
            role=role,
            run_id=run_id,
            session=session,
            project_ids=active["project_ids"],
        )
        return active

    def reconcile_active(
        self,
        state_key: str,
        config: Dict[str, Any],
    ) -> None:
        active = self.state.get(state_key)
        if not isinstance(active, dict):
            return

        session = str(active.get("session", ""))
        receipt_path = Path(str(active.get("receipt_path", "")))
        run_dir = Path(str(active.get("run_dir", "")))
        raw_project_ids = active.get("project_ids", [])
        project_ids = (
            [str(value) for value in raw_project_ids]
            if isinstance(raw_project_ids, list)
            else []
        )
        role = str(active.get("role", "unknown"))
        owned_session = sessions.is_owned_top_session(session, role)
        valid_receipt = (
            self.safe_run_dir(run_dir)
            and receipt_path.name == "receipt.json"
            and receipt_path.parent.resolve() == run_dir.resolve()
        )

        if valid_receipt and receipt_path.is_file():
            receipt = storage.read_json(receipt_path, {})
            if owned_session and sessions.session_exists(session):
                sessions.kill_session(session)
            self.event(
                "top_session_completed",
                role=role,
                run_id=active.get("run_id"),
                session=session,
                project_ids=project_ids,
                receipt=receipt,
            )
            if role == "reporter":
                local = scheduler.local_now(str(config.get("timezone", "UTC")))
                self.state["last_report_date"] = local.strftime("%Y-%m-%d")
            self.state[state_key] = None
            self.cleanup_run_dir(run_dir)
            return

        if owned_session and sessions.session_exists(session):
            return

        for project_id in project_ids:
            self.write_control_escalation(
                project_id,
                f"{role} session 在写入完成回执前消失",
                (
                    f"Runner 检查到 tmux session {session} 已不存在，"
                    f"且没有找到回执文件 {receipt_path}。"
                ),
                (
                    "本次顶层调用被视为失败。请查看 runner/events.log 和项目 runtime/events.log，"
                    "确认是否存在 TUI 退出、认证、环境变量或人工关闭 session 的问题；"
                    "处理后使用“立即运行”验证。"
                ),
            )
        self.event(
            "top_session_lost",
            role=role,
            run_id=active.get("run_id"),
            session=session,
            project_ids=project_ids,
        )
        if role == "reporter":
            local = scheduler.local_now(str(config.get("timezone", "UTC")))
            self.state["last_report_date"] = local.strftime("%Y-%m-%d")
        self.state[state_key] = None
        self.cleanup_run_dir(run_dir)

    def write_control_escalation(
        self,
        project_id: str,
        title: str,
        detail: str,
        action: str,
    ) -> None:
        harness = storage.project_dir(self.home, project_id)
        if not harness.is_dir():
            self.event(
                "unattached_escalation",
                project_id=project_id,
                title=title,
                detail=detail,
            )
            return
        block = (
            f"\n\n### {title} · {storage.utc_now()}\n\n"
            f"**发生了什么**\n\n{detail}\n\n"
            "**影响**\n\n本次自动工作链路没有获得可信完成结果，"
            "项目不会把这次运行计为已完成 Task。\n\n"
            "**已尝试的恢复**\n\nRunner 已检查完成回执和顶层 tmux session，"
            "并停止继续假设本次运行成功。\n\n"
            "**为什么不能自动处理**\n\n继续重试可能重复消耗额度、覆盖现场或制造并行 Task，"
            "需要先确认底层原因。\n\n"
            f"**人类需要做什么**\n\n{action}\n\n"
            "**恢复验证**\n\n处理后触发一次项目运行，确认 Root、Project、Task 链路"
            "能够写入完成回执，并在日报中出现可信结果。\n\n"
            f"**原始状态**\n\n- Runner 日志：`{storage.runner_events_path(self.home)}`\n"
            f"- 项目运行日志：`{harness / 'runtime' / 'events.log'}`\n"
        )
        path = harness / "escalations.md"
        descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(descriptor, block.encode("utf-8"))
        finally:
            os.close(descriptor)
        project_state = storage.load_project_state(self.home, project_id)
        project_state.update(
            {
                "status": "control_blocked",
                "last_activity_at": storage.utc_now(),
                "last_result": title,
            }
        )
        storage.write_json(harness / "runtime" / "state.json", project_state)
        storage.append_event(
            harness / "runtime" / "events.log",
            "control_escalation",
            title=title,
        )

    def clear_report_force(self, config: Dict[str, Any]) -> None:
        del config
        current = storage.ensure_home(self.home)
        report = current.get("report", {})
        if isinstance(report, dict) and report.get("force", False):
            report["force"] = False
            storage.write_json(storage.activation_path(self.home), current)

    def tick(self) -> None:
        config = storage.ensure_home(self.home)
        now = datetime.now(timezone.utc)
        self.state["last_tick_at"] = storage.utc_now()

        self.reconcile_active("active_root", config)
        self.reconcile_active("active_reporter", config)

        service = config.get("service", {})
        stopping = bool(service.get("stop_requested", False))
        restarting = bool(service.get("restart_requested", False))
        if stopping or restarting:
            self.state["service"]["status"] = "draining"
            self.save_state()
            return

        if self.activation_check_due(config, now):
            self.update_next_check(config, now)
            eligible = scheduler.eligible_projects(config)
            if eligible and not self.state.get("active_root"):
                active = self.launch_top_level("root", eligible, config)
                storage.consume_project_force_flags(self.home, eligible)
                if active:
                    self.state["active_root"] = active
            self.event("activation_checked", eligible_project_ids=eligible)

        if (
            scheduler.report_due(config, self.state.get("last_report_date"))
            and not self.state.get("active_reporter")
        ):
            project_ids = storage.list_project_ids(self.home)
            active = self.launch_top_level("reporter", project_ids, config)
            if active:
                self.state["active_reporter"] = active
            else:
                local = scheduler.local_now(str(config.get("timezone", "UTC")))
                self.state["last_report_date"] = local.strftime("%Y-%m-%d")
            self.clear_report_force(config)

        self.state["last_error"] = None
        self.save_state()

    def should_exit(self) -> Optional[str]:
        config = storage.ensure_home(self.home)
        service = config.get("service", {})
        if self.force_stop:
            return "stop"
        active = self.state.get("active_root") or self.state.get("active_reporter")
        if active:
            return None
        if service.get("restart_requested", False):
            return "restart"
        if service.get("stop_requested", False):
            return "stop"
        return None

    def force_cleanup(self) -> None:
        for key in ("active_root", "active_reporter"):
            active = self.state.get(key)
            if not isinstance(active, dict):
                continue
            session = str(active.get("session", ""))
            role = str(active.get("role", ""))
            if (
                sessions.is_owned_top_session(session, role)
                and sessions.session_exists(session)
            ):
                sessions.kill_session(session)
            raw_project_ids = active.get("project_ids", [])
            project_ids = raw_project_ids if isinstance(raw_project_ids, list) else []
            for project_id in project_ids:
                self.write_control_escalation(
                    project_id,
                    "Perpetuum 服务被强制停止",
                    f"顶层 session {session} 在未完成回执时被终止。",
                    "确认没有遗留的子 session 或半完成业务变更，再重新启动服务并手动触发项目验证。",
                )
            self.state[key] = None


def reset_service_request(home: Path, key: str) -> None:
    config = storage.ensure_home(home)
    service = config.setdefault("service", {})
    service[key] = False
    storage.write_json(storage.activation_path(home), config)


def run_daemon(home: Path) -> int:
    config = storage.ensure_home(home)
    runner = Runner(home)
    service = config.get("service", {})
    host = str(service.get("host", "127.0.0.1"))
    port = int(service.get("port", 8765))
    heartbeat = max(1, int(service.get("heartbeat_seconds", 5)))

    def handle_signal(signum: int, frame: Any) -> None:
        del signum, frame
        runner.force_stop = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    try:
        server = RuntimeServer(home, host, port)
        server.start()
    except Exception as exc:
        runner.state["service"] = {
            "status": "stopped",
            "pid": None,
            "started_at": None,
            "stopped_at": storage.utc_now(),
            "url": f"http://{host}:{port}",
        }
        runner.state["last_error"] = str(exc)
        runner.save_state()
        runner.event("service_start_failed", error=str(exc), host=host, port=port)
        return 1

    runner.state["service"] = {
        "status": "running",
        "pid": os.getpid(),
        "started_at": storage.utc_now(),
        "stopped_at": None,
        "url": f"http://{host}:{port}",
    }
    runner.save_state()
    runner.event("service_started", pid=os.getpid(), host=host, port=port)
    exit_mode = "stop"
    try:
        while True:
            try:
                runner.tick()
            except Exception as exc:
                runner.state["last_error"] = str(exc)
                runner.save_state()
                runner.event(
                    "runner_tick_failed",
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
            exit_mode = runner.should_exit() or ""
            if exit_mode:
                break
            time.sleep(heartbeat)
    finally:
        server.stop()
        if runner.force_stop:
            runner.force_cleanup()
        runner.state["service"].update(
            {
                "status": "stopped",
                "pid": None,
                "stopped_at": storage.utc_now(),
            }
        )
        runner.save_state()
        runner.event("service_stopped", mode=exit_mode)

    if exit_mode == "restart" and not runner.force_stop:
        reset_service_request(home, "restart_requested")
        reset_service_request(home, "stop_requested")
        os.execv(
            sys.executable,
            [
                sys.executable,
                "-m",
                "perpetuum_app.runner",
                "--home",
                str(home),
            ],
        )
    reset_service_request(home, "stop_requested")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Perpetuum background runner")
    parser.add_argument("--home", type=Path)
    args = parser.parse_args()
    raise SystemExit(run_daemon(storage.runtime_home(args.home)))


if __name__ == "__main__":
    main()
