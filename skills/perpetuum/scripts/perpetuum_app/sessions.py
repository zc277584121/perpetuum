"""Top-level tmux session management."""

from __future__ import annotations

import secrets
import shlex
import subprocess
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def session_name(role: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"perpetuum-{role}-{stamp}-{secrets.token_hex(3)}"


def session_exists(name: str) -> bool:
    return (
        subprocess.run(
            ["tmux", "has-session", "-t", f"={name}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        == 0
    )


def is_owned_top_session(name: str, role: str) -> bool:
    if role not in {"root", "reporter"}:
        return False
    return bool(
        re.fullmatch(
            rf"perpetuum-{role}-\d{{8}}-\d{{6}}-[0-9a-f]{{6}}",
            name,
        )
    )


def capture_session(name: str, lines: int = 200) -> str:
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", f"={name}:0.0", "-p", "-S", f"-{lines}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return result.stdout


def kill_session(name: str) -> None:
    subprocess.run(
        ["tmux", "kill-session", "-t", f"={name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


def cc_use_tmux_tmpdir(path: Optional[Path] = None) -> Path:
    resolved = path or (Path.home() / ".cc-use" / "tmux")
    resolved.mkdir(mode=0o700, parents=True, exist_ok=True)
    resolved.chmod(0o700)
    return resolved


def launch_session(
    role: str,
    command: str,
    cwd: Path,
    prompt: str,
    startup_seconds: int = 8,
    kind: str = "codex",
    tmux_tmpdir: Optional[Path] = None,
) -> str:
    name = session_name(role)
    argv = shlex.split(command)
    if not argv:
        raise RuntimeError("Agent 启动命令为空")
    inner_tmux_tmpdir = cc_use_tmux_tmpdir(tmux_tmpdir)

    result = subprocess.run(
        [
            "tmux",
            "new-session",
            "-d",
            "-s",
            name,
            "-x",
            "200",
            "-y",
            "60",
            "-c",
            str(cwd),
            "env",
            f"TMUX_TMPDIR={inner_tmux_tmpdir}",
            *argv,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "无法创建 tmux session")

    time.sleep(max(1, startup_seconds))
    if not session_exists(name):
        raise RuntimeError("Agent TUI 在接收任务前已经退出")

    try:
        buffer_name = f"pp-{secrets.token_hex(4)}"
        pane_target = f"={name}:0.0"
        load = subprocess.run(
            ["tmux", "load-buffer", "-b", buffer_name, "-"],
            input=prompt,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if load.returncode != 0:
            raise RuntimeError(load.stderr.strip() or "无法写入 tmux buffer")

        paste = subprocess.run(
            ["tmux", "paste-buffer", "-d", "-b", buffer_name, "-t", pane_target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if paste.returncode != 0:
            raise RuntimeError(paste.stderr.strip() or "无法投递 tmux buffer")
        if kind == "codex":
            subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, "Escape"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            time.sleep(0.3)
        for key in ("Enter", "C-m", "Enter"):
            sent = subprocess.run(
                ["tmux", "send-keys", "-t", pane_target, key],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if sent.returncode != 0:
                raise RuntimeError(sent.stderr.strip() or "无法提交 TUI 输入")
            time.sleep(0.2)
    except Exception:
        kill_session(name)
        raise
    return name
