"""Time-window evaluation for project activation."""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


def local_now(timezone_name: str) -> datetime:
    previous = os.environ.get("TZ")
    try:
        os.environ["TZ"] = timezone_name
        if hasattr(time, "tzset"):
            time.tzset()
        return datetime.now()
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        if hasattr(time, "tzset"):
            time.tzset()


def parse_clock(value: str, allow_24: bool = False) -> int:
    match = re.fullmatch(r"(\d{2}):(\d{2})", value)
    if not match:
        raise ValueError(f"无效时间：{value}")
    hour, minute = int(match.group(1)), int(match.group(2))
    if minute > 59 or hour > 24:
        raise ValueError(f"无效时间：{value}")
    if hour == 24 and (minute != 0 or not allow_24):
        raise ValueError(f"无效时间：{value}")
    return hour * 60 + minute


def normalize_window(window: Any) -> Tuple[str, str, Optional[List[int]]]:
    if isinstance(window, str):
        if "-" not in window:
            raise ValueError(f"无效时间窗口：{window}")
        start, end = window.split("-", 1)
        return start, end, None
    if isinstance(window, dict):
        start = str(window.get("start", ""))
        end = str(window.get("end", ""))
        raw_days = window.get("days")
        days = [int(day) for day in raw_days] if isinstance(raw_days, list) else None
        return start, end, days
    raise ValueError(f"无效时间窗口：{window}")


def window_matches(window: Any, now: datetime) -> bool:
    start_text, end_text, days = normalize_window(window)
    start = parse_clock(start_text)
    end = parse_clock(end_text, allow_24=True)
    minute = now.hour * 60 + now.minute

    if start == end:
        matches_time = True
        start_day = now.weekday()
    elif start < end:
        matches_time = start <= minute < end
        start_day = now.weekday()
    else:
        matches_time = minute >= start or minute < end
        start_day = now.weekday() if minute >= start else (now.weekday() - 1) % 7

    if not matches_time:
        return False
    return days is None or start_day in days


def project_is_eligible(entry: Dict[str, Any], now: datetime) -> bool:
    if not entry.get("enabled", True) or entry.get("paused", False):
        return False
    if entry.get("force_run", False):
        return True
    windows = entry.get("windows", [])
    if not isinstance(windows, list) or not windows:
        return False
    for window in windows:
        try:
            if window_matches(window, now):
                return True
        except (TypeError, ValueError):
            continue
    return False


def eligible_projects(config: Dict[str, Any], now: Optional[datetime] = None) -> List[str]:
    current = now or local_now(str(config.get("timezone", "UTC")))
    projects = config.get("projects", {})
    if not isinstance(projects, dict):
        return []
    return sorted(
        project_id
        for project_id, entry in projects.items()
        if isinstance(entry, dict) and project_is_eligible(entry, current)
    )


def report_due(
    config: Dict[str, Any],
    last_report_date: Optional[str],
    now: Optional[datetime] = None,
) -> bool:
    report = config.get("report", {})
    if not isinstance(report, dict) or not report.get("enabled", True):
        return False
    if report.get("force", False):
        return True
    current = now or local_now(str(config.get("timezone", "UTC")))
    today = current.strftime("%Y-%m-%d")
    if last_report_date == today:
        return False
    try:
        target = parse_clock(str(report.get("time", "09:00")))
    except ValueError:
        target = 9 * 60
    return current.hour * 60 + current.minute >= target
