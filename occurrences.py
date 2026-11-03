"""Concrete event occurrences, resolved without Qt.

A "occurrence" is one real slot in the calendar: a non-recurring event, or one
instance of a recurring series after the RRULE has been expanded. Reminders,
statistics and the headless CLI all need exactly this resolution, and none of
them should depend on the GUI toolkit to get it.

Keeping this module Qt-free is what lets ``python -m headless`` run on a server
with no display and no PySide6 installed.
"""

from dataclasses import dataclass
from datetime import datetime

from models_event import expand_recurrence, has_recurrence, is_all_day_event, parse_event_time


@dataclass(frozen=True)
class Occurrence:
    """One concrete instance of an event (recurring series already expanded)."""

    key: str
    summary: str
    start: datetime
    end: datetime
    all_day: bool
    event: dict


def occurrence_key(event: dict) -> str:
    """Stable id for one occurrence: ``<event_id>@<start>``.

    The series template and its expanded first occurrence resolve to the same
    key, which is what keeps :func:`collect` free of duplicates.
    """
    event_id = str(event.get("event_id") or "")
    start = parse_event_time(event.get("start_time", {}))
    return f"{event_id}@{start.strftime('%Y%m%dT%H%M%S')}"


def to_occurrence(event: dict) -> Occurrence:
    """Normalise one event dict into an :class:`Occurrence`."""
    start = parse_event_time(event.get("start_time", {}))
    end = parse_event_time(event.get("end_time", {}))
    all_day = is_all_day_event(event)
    if all_day:
        # 全天日程只有日期：归一成整天，否则当天 10:00 发起的区间判断会漏掉它
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(hour=23, minute=59, second=59, microsecond=0)
    elif end < start:
        end = start
    return Occurrence(
        key=occurrence_key(event),
        summary=str(event.get("summary", "") or ""),
        start=start,
        end=end,
        all_day=all_day,
        event=event,
    )


def collect(events, start: datetime, end: datetime) -> list:
    """Every occurrence overlapping ``[start, end]``, deduplicated, time-sorted."""
    out: dict = {}
    for event in events or []:
        if not isinstance(event, dict):
            continue
        if has_recurrence(event):
            expanded = expand_recurrence(event, start, end)
            candidates = expanded or [event]
        else:
            candidates = [event]
        for candidate in candidates:
            occ = to_occurrence(candidate)
            if occ.end < start or occ.start > end:
                continue
            out.setdefault(occ.key, occ)
    return sorted(out.values(), key=lambda o: (o.start, o.end))
