"""Write-side actions — every one of these mirrors an action a human is
already documented as allowed to do by hand (see perpetuum's
references/feedback.md and references/control.md). Nothing here touches
plan.md, which stays agent-owned.
"""

from __future__ import annotations

import re
from pathlib import Path


def is_paused(task_dir: Path) -> bool:
    return (task_dir / ".paused").exists()


def set_paused(task_dir: Path, paused: bool) -> None:
    flag = task_dir / ".paused"
    if paused:
        flag.touch()
    else:
        flag.unlink(missing_ok=True)


def is_stop_requested(task_dir: Path) -> bool:
    return (task_dir / ".stop_after_current").exists()


def request_stop_after_current(task_dir: Path) -> None:
    (task_dir / ".stop_after_current").touch()


def push_inbox(task_dir: Path, text: str) -> None:
    """Append one line under inbox.md's '## Pending' section — the same
    place a human is told to write free-text nudges by hand.
    """
    path = task_dir / "inbox.md"
    content = path.read_text(errors="replace") if path.exists() else "# Inbox\n\n## Pending\n\n## Processed\n"
    if "## Pending" not in content:
        content += "\n## Pending\n\n## Processed\n"
    head, _, rest = content.partition("## Pending")
    # Insert right after '## Pending', before the next '##' heading (or EOF).
    m = re.search(r"\n## ", rest[1:])
    insert_at = m.start() + 1 if m else len(rest)
    new_rest = rest[:insert_at] + f"\n- {text}\n" + rest[insert_at:]
    path.write_text(head + "## Pending" + new_rest)


def list_open_escalations(task_dir: Path) -> list[tuple[str, str]]:
    """Return [(title, full block text)] for every '### (cycle ...)' entry
    currently under '## Open'.
    """
    path = task_dir / "escalations.md"
    if not path.exists():
        return []
    content = path.read_text(errors="replace")
    if "## Open" not in content:
        return []
    open_section = content.split("## Open", 1)[1].split("## Resolved", 1)[0]
    # Strip HTML comments first — the shipped template ships an example
    # entry inside a <!-- --> block ("delete when you have real ones"),
    # which a naive '### ' scan would otherwise count as a real, open
    # escalation forever if nobody deletes the comment.
    open_section = re.sub(r"<!--.*?-->", "", open_section, flags=re.DOTALL)
    blocks = re.split(r"\n(?=### )", open_section.strip())
    results = []
    for b in blocks:
        b = b.strip()
        if not b.startswith("### "):
            continue
        title = b.splitlines()[0][4:].strip()
        results.append((title, b))
    return results


def resolve_escalation(task_dir: Path, index: int, answer: str) -> bool:
    """Move the index-th open escalation to '## Resolved', appending the
    human's answer. Returns False if index is out of range.
    """
    path = task_dir / "escalations.md"
    if not path.exists():
        return False
    content = path.read_text(errors="replace")
    if "## Open" not in content or "## Resolved" not in content:
        return False

    before_open, rest = content.split("## Open", 1)
    open_section, after_resolved_marker = rest.split("## Resolved", 1)

    blocks = re.split(r"\n(?=### )", open_section.strip())
    blocks = [b for b in blocks if b.strip().startswith("### ")]
    if index < 0 or index >= len(blocks):
        return False

    chosen = blocks.pop(index).strip()
    resolved_block = chosen + f"\n\n**Human decision:** {answer}\n"

    new_open_section = ("\n\n".join(blocks) + "\n\n") if blocks else "(none currently open)\n\n"
    new_content = (
        before_open
        + "## Open\n\n"
        + new_open_section
        + "## Resolved"
        + "\n\n"
        + resolved_block
        + after_resolved_marker.lstrip("\n")
    )
    path.write_text(new_content)
    return True
