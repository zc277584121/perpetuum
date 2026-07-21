"""Read-only parsers over perpetuum's existing file-based state.

Nothing here writes to any perpetuum file, and none of Layer 1/2/3's
behavior changes because this module exists — it only reads the same
files/tmux panes a human already inspects by hand.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


def _tail(path: Path, n: int = 4000) -> str:
    """Last n chars — for logs, where only recent content matters."""
    if not path.exists():
        return ""
    return path.read_text(errors="replace")[-n:]


def _read_all(path: Path) -> str:
    """Whole file — for scripts/config where early lines matter too."""
    if not path.exists():
        return ""
    return path.read_text(errors="replace")


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout
    except Exception:
        return ""


@dataclass
class Layer3Status:
    iter_current: int | None = None
    iter_max: int | None = None
    phase: str = "unknown"  # explore | execute | sleeping | done | unknown
    trigger_type: str = "unknown"
    last_event: str = ""


@dataclass
class Layer2Status:
    pending: int = 0
    done: int = 0
    escalated: int = 0
    session_name: str = ""
    pane_tail: list[str] = field(default_factory=list)


@dataclass
class GlobalStatus:
    escalations_open: int = 0
    recent_commits: list[str] = field(default_factory=list)


ITER_RE = re.compile(r"#+ ITER (\d+) / (\d+) #+")
PHASE_SEND_RE = re.compile(r"\[(\d_\w+)\] sending prompt")
PHASE_DONE_RE = re.compile(r"\[(\d_\w+)\] complete")
SLEEP_RE = re.compile(r"Sleeping (\d+)s before next cycle")
COMPLETE_RE = re.compile(r"complete after (\d+) iterations")


def parse_trigger_log(task_dir: Path) -> Layer3Status:
    text = _tail(task_dir / "trigger.log")
    status = Layer3Status()
    for line in text.splitlines():
        m = ITER_RE.search(line)
        if m:
            status.iter_current, status.iter_max = int(m.group(1)), int(m.group(2))
        m = PHASE_SEND_RE.search(line)
        if m:
            status.phase = "explore" if "explore" in m.group(1) else "execute"
        m = PHASE_DONE_RE.search(line)
        if m:
            status.phase = "judging/idle"
        if SLEEP_RE.search(line):
            status.phase = "sleeping"
        if COMPLETE_RE.search(line):
            status.phase = "done"
        if line.strip():
            status.last_event = line.strip()

    meta = _read_all(task_dir / "_meta.md")
    tm = re.search(r"trigger type\**:\s*`?(\w+)", meta)
    if tm:
        status.trigger_type = tm.group(1)
    return status


DONE_RE = re.compile(r"^- \[x\]", re.MULTILINE)
PENDING_RE = re.compile(r"^- \[ \]", re.MULTILINE)
ESCALATED_MARK_RE = re.compile(r"^- \[x\].*\[→\]", re.MULTILINE)


def parse_plan_md(task_dir: Path) -> tuple[int, int]:
    text = _read_all(task_dir / "plan.md")
    pending = len(PENDING_RE.findall(text))
    done = len(DONE_RE.findall(text))
    return pending, done


def parse_escalations_md(task_dir: Path) -> int:
    text = _read_all(task_dir / "escalations.md")
    if "## Resolved" in text:
        open_section = text.split("## Open", 1)[-1].split("## Resolved", 1)[0]
    else:
        open_section = text
    # Strip HTML comments — the shipped template's "delete when you have
    # real ones" example entry lives inside one and shouldn't count.
    open_section = re.sub(r"<!--.*?-->", "", open_section, flags=re.DOTALL)
    return len(re.findall(r"^### \(cycle", open_section, re.MULTILINE))


def read_middle_session(task_dir: Path) -> str:
    """Resolve MIDDLE_SESSION the same way trigger.sh itself does, by
    actually running trigger.sh's own setup lines in a subshell — this
    works regardless of each example's specific naming convention,
    instead of guessing at the expression with regex.
    """
    trigger_sh_path = task_dir / "trigger.sh"
    text = _read_all(trigger_sh_path)
    lines = text.splitlines()
    task_line = next(
        (i for i, l in enumerate(lines) if l.strip().startswith("TASK_DIR=")), None
    )
    cutoff = next(
        (i for i, l in enumerate(lines) if l.strip().startswith("MIDDLE_SESSION=")),
        None,
    )
    if task_line is None or cutoff is None:
        return "unknown"
    # TASK_DIR's real assignment depends on $0, which isn't meaningful
    # under `bash -c` — pin it to the actual path instead, then replay
    # the rest of trigger.sh's own setup lines verbatim.
    script = (
        f'TASK_DIR="{trigger_sh_path.parent}"\n'
        + "\n".join(lines[task_line + 1 : cutoff + 1])
        + '\necho "$MIDDLE_SESSION"'
    )
    out = _run(["bash", "-c", script])
    name = out.strip().splitlines()[-1] if out.strip() else ""
    return name or "unknown"


_SEPARATOR_LINE_RE = re.compile(r"^[\s\-─━═_·]*$")

# Keep pane rendering independent of agent-specific TUI wording. Show the raw,
# unfiltered tail as a small teaser and let a human page through the actual
# scrollback in the terminal viewer. Both views use read-only `capture-pane`
# snapshots and never attach a client to the running session.


def tmux_pane_tail(session: str, lines: int = 12) -> list[str]:
    out = _run(["tmux", "capture-pane", "-t", f"={session}:", "-p", "-S", f"-{lines}"])
    if not out:
        return []
    return [l for l in out.splitlines() if l.strip()][-lines:]


def tmux_pane_full(session: str, scan: int = 2000) -> str:
    """A large scrollback snapshot for a human to page through in the
    dashboard's own terminal viewer. Plain text (-p, no -e), so no ANSI
    escapes leak into the viewer widget.
    """
    return _run(["tmux", "capture-pane", "-t", f"={session}:", "-p", "-S", f"-{scan}"], timeout=8)


def tmux_pane_fingerprint(session: str, scan: int = 40) -> str:
    """A cheap hash of recent pane content, for the dashboard to detect
    'did anything actually change' between refreshes on its own, rather
    than trusting that the visible tail looks different.
    """
    import hashlib

    out = _run(["tmux", "capture-pane", "-t", f"={session}:", "-p", "-S", f"-{scan}"])
    return hashlib.sha1(out.encode("utf-8", errors="replace")).hexdigest()


def tmux_session_alive(session: str) -> bool:
    return (
        subprocess.run(
            ["tmux", "has-session", "-t", f"={session}"],
            capture_output=True,
        ).returncode
        == 0
    )


def git_recent_commits(repo: Path, n: int = 5) -> list[str]:
    out = _run(["git", "-C", str(repo), "log", f"-{n}", "--oneline"])
    return [l for l in out.splitlines() if l.strip()]


TS_RE = re.compile(r"^\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]")
SLEEP_LINE_RE = re.compile(r"^\[([^\]]+)\]\s+Sleeping (\d+)s before next cycle")


def next_cycle_eta_seconds(task_dir: Path) -> int | None:
    """Seconds until the next scheduled cycle, or None if not currently
    in the sleep window (mid-cycle, or the run has already finished).
    """
    import datetime

    text = _tail(task_dir / "trigger.log", n=4000)
    lines = text.splitlines()
    last_sleep_at: str | None = None
    last_sleep_secs = 0
    for line in lines:
        m = SLEEP_LINE_RE.match(line)
        if m:
            last_sleep_at, last_sleep_secs = m.group(1), int(m.group(2))
        elif "##########" in line or "complete after" in line:
            last_sleep_at = None  # a new cycle/end started since the last sleep
    if last_sleep_at is None:
        return None
    try:
        started = datetime.datetime.strptime(last_sleep_at, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
    elapsed = (datetime.datetime.now() - started).total_seconds()
    remaining = int(last_sleep_secs - elapsed)
    return max(remaining, 0)


DONE_BLOCK_RE = re.compile(
    r"^- \[x\] \(cycle ([^)]+)\) \[([^\]]+)\] (.+?)\n((?:  - .+\n?)*)", re.MULTILINE
)


def recent_done_items(task_dir: Path, n: int = 5) -> list[dict]:
    text = _read_all(task_dir / "plan.md")
    items = []
    for m in DONE_BLOCK_RE.finditer(text):
        cycle, dim, title, body = m.groups()
        status_m = re.search(r"status:\s*(.+)", body)
        items.append(
            {
                "cycle": cycle,
                "dim": dim,
                "title": title.strip(),
                "status": status_m.group(1).strip() if status_m else "?",
            }
        )
    return items[-n:]


def inbox_pending(task_dir: Path) -> list[str]:
    text = _read_all(task_dir / "inbox.md")
    if "## Pending" not in text:
        return []
    section = text.split("## Pending", 1)[1].split("## Processed", 1)[0]
    return [
        l.strip()[2:].strip()
        for l in section.splitlines()
        if l.strip().startswith("- ") and l.strip() not in ("- (your items here)",)
    ]


# --------------------------------------------------------------------------
# Human-facing summary: outcome-oriented, not layer-oriented. Branches on
# trigger_type because "cycle N of M, next in Ns" only means something for
# `schedule` — conditional/webhook tasks don't have a linear progress axis.
# --------------------------------------------------------------------------


def task_started_at(task_dir: Path):
    import datetime

    meta = _read_all(task_dir / "_meta.md")
    m = re.search(r"created\**:\s*`?(\d{4}-\d{2}-\d{2})", meta)
    if m:
        try:
            return datetime.datetime.strptime(m.group(1), "%Y-%m-%d")
        except ValueError:
            pass
    log_path = task_dir / "trigger.log"
    if log_path.exists():
        first_line = log_path.read_text(errors="replace").splitlines()[0:5]
        for line in first_line:
            tm = TS_RE.match(line)
            if tm:
                return datetime.datetime.strptime(tm.group(1), "%Y-%m-%d %H:%M:%S")
    return datetime.datetime.fromtimestamp(log_path.stat().st_ctime) if log_path.exists() else None


def format_elapsed(started) -> str:
    import datetime

    if started is None:
        return "unknown"
    delta = datetime.datetime.now() - started
    total_min = int(delta.total_seconds() // 60)
    h, m = divmod(total_min, 60)
    return f"{h}h {m}m" if h else f"{m}m"


def dispatch_count_estimate(task_dir: Path) -> int:
    """Cheap, agent-agnostic cost proxy: count of Done items in plan.md.
    Each represents at least one real inner-agent dispatch. Deliberately
    NOT a token/dollar figure — see TODO.md for why."""
    _, done = parse_plan_md(task_dir)
    return done


def cycle_count_seen(task_dir: Path) -> int:
    """How many cycles have actually fired, for conditional/webhook tasks
    where there's no fixed MAX_ITER progress bar to show instead."""
    text = _tail(task_dir / "trigger.log", n=200_000)
    return len(re.findall(r"##+ ITER \d+", text))


def render_progress_bar(current: int, total: int, width: int = 24) -> str:
    if total <= 0:
        return ""
    filled = int(width * min(current, total) / total)
    return "█" * filled + "░" * (width - filled)


def parse_escalation_options(block_text: str) -> list[str]:
    """Pull the '**Options:**' bullets out of one escalation block, if any."""
    if "**Options:**" not in block_text:
        return []
    tail = block_text.split("**Options:**", 1)[1]
    opts = re.findall(r"^\s*-\s*\*\*[A-Z]\*\*:\s*(.+)$", tail, re.MULTILINE)
    if not opts:
        opts = re.findall(r"^\s*-\s*([A-Z]:.+)$", tail, re.MULTILINE)
    return [o.strip() for o in opts]


# --------------------------------------------------------------------------
# History — read-only. memsearch (if configured) keys its memory by
# *project path*, not by tmux session, so Layer 1 and Layer 2 activity
# ends up interleaved in the same files — there's no reliable way to
# split "this entry was Layer 1 vs Layer 2" back out, so this doesn't
# try to. What IS reliably structured is the `### HH:MM` timestamp per
# entry, so this is presented as a chronological feed, not force-fit
# into per-cycle boxes (trigger.log's cycle boundaries are used only as
# a best-effort "cycle ~N" annotation, never claimed as exact).
# --------------------------------------------------------------------------


def list_memsearch_history(project_root: Path) -> list[dict]:
    """Every .memsearch/memory/*.md file, newest first, as raw markdown
    text for the caller to render however it likes (this module doesn't
    render anything — it's read-only passthrough)."""
    mem_dir = project_root / ".memsearch" / "memory"
    if not mem_dir.is_dir():
        return []
    files = sorted(mem_dir.glob("*.md"), reverse=True)
    return [{"date": f.stem, "content": _read_all(f)} for f in files]


def read_project_memory_summary(project_root: Path) -> str:
    """The rolling PROJECT.md summary, if memsearch maintains one."""
    return _read_all(project_root / ".memsearch" / "PROJECT.md")


def cycle_time_windows(task_dir: Path) -> list[dict]:
    """[{cycle, start, end}] best-effort windows parsed from trigger.log,
    used only to *annotate* history entries with an approximate cycle
    number — never treated as an exact mapping.
    """
    text = _tail(task_dir / "trigger.log", n=200_000)
    windows: list[dict] = []
    current_cycle = None
    current_start = None
    for line in text.splitlines():
        m = ITER_RE.search(line)
        ts = TS_RE.match(line)
        if m:
            if current_cycle is not None and current_start is not None and ts:
                windows.append({"cycle": current_cycle, "start": current_start, "end": ts.group(1)})
            current_cycle = int(m.group(1))
            current_start = ts.group(1) if ts else None
    return windows


def list_tmux_sessions() -> list[str]:
    """All live tmux sessions available to the read-only session picker."""
    out = _run(["tmux", "list-sessions", "-F", "#{session_name}"])
    return sorted(l.strip() for l in out.splitlines() if l.strip())


# --------------------------------------------------------------------------
# Files — read-only browsing of the task directory itself (prompts,
# trigger.sh, _meta.md, the raw state files, etc). No write path exists
# anywhere in this module for arbitrary files — only the specific,
# already-documented writes in controls.py (inbox.md/escalations.md/
# .paused/.stop_after_current) are ever touched.
# --------------------------------------------------------------------------

_SKIP_DIRS = {"state", "__pycache__", ".git"}


def list_task_files(task_dir: Path) -> list[str]:
    """Relative paths of every file under the task dir, sorted, skipping
    transient sync-flag noise in state/."""
    out = []
    for p in task_dir.rglob("*"):
        if p.is_dir():
            continue
        if any(part in _SKIP_DIRS for part in p.relative_to(task_dir).parts):
            continue
        out.append(str(p.relative_to(task_dir)))
    return sorted(out)


def read_task_file(task_dir: Path, rel_path: str) -> str:
    """Read one file by path relative to the task dir. Raises ValueError
    if the resolved path would escape task_dir (no path traversal)."""
    target = (task_dir / rel_path).resolve()
    task_dir_resolved = task_dir.resolve()
    if task_dir_resolved not in target.parents and target != task_dir_resolved:
        raise ValueError("path escapes task directory")
    if not target.is_file():
        raise ValueError("not a file")
    return _read_all(target)
