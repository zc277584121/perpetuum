"""Cron evaluation for project activation and daily reports."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter


def utc_text(value: Optional[datetime] = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def timezone_info(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"无效时区：{timezone_name}") from exc


def local_now(
    timezone_name: str,
    now: Optional[datetime] = None,
) -> datetime:
    zone = timezone_info(timezone_name)
    if now is None:
        return datetime.now(zone)
    if now.tzinfo is None:
        return now.replace(tzinfo=zone)
    return now.astimezone(zone)


def validate_cron(expression: str) -> str:
    value = str(expression).strip()
    if len(value.split()) != 5 or not croniter.is_valid(value):
        raise ValueError(f"无效 cron 表达式：{expression}；请使用标准五字段语法")
    return value


def normalize_crons(expressions: Any) -> List[str]:
    if not isinstance(expressions, list) or not expressions:
        raise ValueError("至少需要一个 cron 表达式")
    result = []
    for expression in expressions:
        value = validate_cron(str(expression))
        if value not in result:
            result.append(value)
    return result


def validate_project_schedule(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("schedule.yaml 必须是 YAML 对象")
    timezone_name = str(value.get("timezone", "Asia/Shanghai")).strip()
    timezone_info(timezone_name)
    return {
        "version": 1,
        "timezone": timezone_name,
        "enabled": bool(value.get("enabled", True)),
        "paused": bool(value.get("paused", False)),
        "force_run": bool(value.get("force_run", False)),
        "cron": normalize_crons(value.get("cron", [])),
    }


def schedule_minute(
    schedule: Dict[str, Any],
    now: Optional[datetime] = None,
) -> str:
    current = local_now(str(schedule.get("timezone", "Asia/Shanghai")), now)
    return current.strftime("%Y-%m-%dT%H:%M%z")


def matching_crons(
    schedule: Dict[str, Any],
    now: Optional[datetime] = None,
) -> List[str]:
    normalized = validate_project_schedule(schedule)
    current = local_now(normalized["timezone"], now).replace(second=0, microsecond=0)
    return [
        expression
        for expression in normalized["cron"]
        if croniter.match(expression, current)
    ]


def project_trigger(
    schedule: Dict[str, Any],
    last_cron_minute: Optional[str],
    now: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    normalized = validate_project_schedule(schedule)
    if not normalized["enabled"] or normalized["paused"]:
        return None
    if normalized["force_run"]:
        return {
            "reason": "manual",
            "matched_cron": None,
            "cron_minute": None,
            "triggered_at": utc_text(now),
        }
    minute = schedule_minute(normalized, now)
    if minute == last_cron_minute:
        return None
    matches = matching_crons(normalized, now)
    if not matches:
        return None
    return {
        "reason": "cron",
        "matched_cron": matches[0],
        "cron_minute": minute,
        "triggered_at": utc_text(now),
    }


def next_schedule_check(now: Optional[datetime] = None) -> str:
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    next_minute = current.replace(second=0, microsecond=0) + timedelta(minutes=1)
    return next_minute.isoformat().replace("+00:00", "Z")


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
    current = local_now(str(config.get("timezone", "UTC")), now)
    today = current.strftime("%Y-%m-%d")
    if last_report_date == today:
        return False
    value = str(report.get("time", "09:00"))
    try:
        hour_text, minute_text = value.split(":", 1)
        target = int(hour_text) * 60 + int(minute_text)
        if not (0 <= int(hour_text) <= 23 and 0 <= int(minute_text) <= 59):
            raise ValueError
    except (TypeError, ValueError):
        target = 9 * 60
    return current.hour * 60 + current.minute >= target
