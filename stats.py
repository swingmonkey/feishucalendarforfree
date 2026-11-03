"""Calendar insight statistics computed from the local store.

Everything here is a pure function over a list of events plus an explicit
range: no Qt, no clock, no network. That keeps the numbers testable and lets
the stats panel answer instantly — the whole point of having a local fact
layer is that "how busy was October" costs a SQLite query, not a sync.

Only timed events contribute minutes; all-day events are counted separately so
a company holiday does not inflate "meeting hours".
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from reminder import collect_occurrences

WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"]

# 热力图的着色分档（分钟）：1-59 / 60-119 / 120-239 / 240+，0 为空白
HEAT_THRESHOLDS = (60, 120, 240)
HEAT_MAX_LEVEL = 4


@dataclass(frozen=True)
class DayStat:
    """One calendar day's load."""

    day: date
    minutes: int
    events: int

    @property
    def hours(self) -> float:
        return self.minutes / 60.0


def _day_key(value) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def daily_stats(events, start: datetime, end: datetime) -> dict:
    """Map every day in ``[start, end]`` to a :class:`DayStat`."""
    occurrences = collect_occurrences(events or [], start, end)
    first = _day_key(start)
    last = _day_key(end)
    days: dict = {}
    cursor = first
    while cursor <= last:
        days[cursor] = DayStat(cursor, 0, 0)
        cursor += timedelta(days=1)

    for occ in occurrences:
        day = occ.start.date()
        if day not in days:
            continue
        stat = days[day]
        if occ.all_day:
            days[day] = DayStat(day, stat.minutes, stat.events + 1)
            continue
        minutes = int(round((occ.end - occ.start).total_seconds() / 60.0))
        days[day] = DayStat(day, stat.minutes + minutes, stat.events + 1)
    return days


def month_bounds(year: int, month: int) -> tuple:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(year, month + 1, 1) - timedelta(seconds=1)
    return start, end


def month_grid(events, year: int, month: int) -> list:
    """Weeks (Monday-first) of ``DayStat | None`` for a month heatmap."""
    start, end = month_bounds(year, month)
    days = daily_stats(events, start, end)
    first = start.date()
    last = end.date()
    lead = first.weekday()

    cells = [None] * lead + [days[first + timedelta(days=i)] for i in range((last - first).days + 1)]
    while len(cells) % 7:
        cells.append(None)
    return [cells[i : i + 7] for i in range(0, len(cells), 7)]


def heat_level(minutes: int) -> int:
    """Bucket index (0-4) used by the heatmap colour ramp."""
    if minutes <= 0:
        return 0
    return min(HEAT_MAX_LEVEL, 1 + sum(1 for t in HEAT_THRESHOLDS if minutes >= t))


@dataclass(frozen=True)
class Summary:
    days: int
    total_events: int
    total_minutes: int
    active_days: int
    busiest: DayStat | None
    longest_streak: int
    weekday_minutes: tuple

    @property
    def total_hours(self) -> float:
        return self.total_minutes / 60.0

    @property
    def average_minutes_per_active_day(self) -> int:
        if not self.active_days:
            return 0
        return int(round(self.total_minutes / self.active_days))


def longest_streak(days: dict) -> int:
    """Longest run of consecutive calendar days that each hold at least one event."""
    best = current = 0
    previous = None
    for day in sorted(days):
        if not days[day].events:
            current = 0
            previous = None
            continue
        # 必须校验「日期相邻」，只数条目会把 1、2、3、5 号算成连续 4 天
        if previous is not None and day == previous + timedelta(days=1):
            current += 1
        else:
            current = 1
        best = max(best, current)
        previous = day
    return best


def summarize(events, start: datetime, end: datetime) -> Summary:
    """Aggregate a range into the numbers the stats panel shows."""
    days = daily_stats(events, start, end)
    weekday_minutes = [0] * 7
    total_minutes = 0
    total_events = 0
    active_days = 0
    busiest = None

    for day in sorted(days):
        stat = days[day]
        total_minutes += stat.minutes
        total_events += stat.events
        weekday_minutes[day.weekday()] += stat.minutes
        if stat.events:
            active_days += 1
        if busiest is None or stat.minutes > busiest.minutes:
            busiest = stat

    return Summary(
        days=len(days),
        total_events=total_events,
        total_minutes=total_minutes,
        active_days=active_days,
        busiest=busiest if (busiest and busiest.events) else None,
        longest_streak=longest_streak(days),
        weekday_minutes=tuple(weekday_minutes),
    )


def format_minutes(minutes: int) -> str:
    """``150`` → ``"2 小时 30 分"``; ``0`` → ``"—"``."""
    if minutes <= 0:
        return "—"
    hours, rest = divmod(int(minutes), 60)
    if hours and rest:
        return f"{hours} 小时 {rest} 分"
    if hours:
        return f"{hours} 小时"
    return f"{rest} 分"


def format_hours(minutes: int) -> str:
    return f"{minutes / 60.0:.1f} 小时"
