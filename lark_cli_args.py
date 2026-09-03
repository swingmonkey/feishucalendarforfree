"""Shared argument builders for lark-cli calendar commands.

Used by both ``lark_cli.py`` (sync ``subprocess``) and ``lark_cli_async.py``
(async ``QProcess``) so that argument construction lives in exactly one place.
Every builder returns a ``list[str]`` ready to be appended with the global
``--format json`` flag by the caller.
"""

from datetime import datetime
from typing import Optional

from utils import get_local_tz_offset


def _fmt_dt(dt: datetime) -> str:
    """Format a datetime for lark-cli ``--start`` / ``--end`` with the
    system's local timezone offset."""
    return dt.strftime(f"%Y-%m-%dT%H:%M:%S{get_local_tz_offset()}")


def agenda_args(start: datetime, end: datetime) -> list[str]:
    """Arguments for ``calendar +agenda --start ... --end ...``."""
    return [
        "calendar", "+agenda",
        "--start", _fmt_dt(start),
        "--end", _fmt_dt(end),
    ]


def search_event_args(query: str, start: datetime, end: datetime) -> list[str]:
    """Arguments for ``calendar +search-event --query ... --start ... --end ...``.

    Uses lark-cli's server-side keyword search instead of fetching a wide
    agenda range and filtering locally.
    """
    args = [
        "calendar", "+search-event",
        "--start", _fmt_dt(start),
        "--end", _fmt_dt(end),
    ]
    if query:
        args.extend(["--query", query])
    return args


def create_event_args(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    calendar_id: str = "primary",
    rrule: Optional[str] = None,
) -> list[str]:
    """Arguments for ``calendar +create ...``."""
    args = [
        "calendar", "+create",
        "--summary", summary,
        "--start", _fmt_dt(start),
        "--end", _fmt_dt(end),
        "--calendar-id", calendar_id,
    ]
    if description:
        args.extend(["--description", description])
    if rrule:
        args.extend(["--rrule", rrule])
    return args


def delete_event_args(
    calendar_id: str,
    event_id: str,
    need_notification: bool = False,
) -> list[str]:
    """Arguments for ``calendar events delete ...``."""
    return [
        "calendar", "events", "delete",
        "--calendar-id", calendar_id,
        "--event-id", event_id,
        "--need-notification", str(need_notification).lower(),
    ]


def get_event_args(calendar_id: str, event_id: str) -> list[str]:
    """Arguments for ``calendar +get ...``."""
    return [
        "calendar", "+get",
        "--calendar-id", calendar_id,
        "--event-id", event_id,
    ]
