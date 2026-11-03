"""Shared date-range, event-sorting and timezone helpers for both API backends."""

from datetime import datetime, timedelta


def month_range(date: datetime):
    """Return (start, end) covering the entire month containing ``date``."""
    start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1) - timedelta(seconds=1)
    else:
        end = start.replace(month=start.month + 1) - timedelta(seconds=1)
    return start, end


def wide_range(months_back: int = 12, months_forward: int = 3):
    """Return (start, end) spanning ``months_back`` before today to
    ``months_forward`` after today."""
    now = datetime.now()
    # Start: first day of the month `months_back` months ago
    start = datetime(now.year, now.month, 1)
    for _ in range(months_back):
        if start.month == 1:
            start = start.replace(year=start.year - 1, month=12)
        else:
            start = start.replace(month=start.month - 1)

    # End: last second of the month `months_forward` months from now
    end_month = now.month + months_forward
    end_year = now.year
    while end_month > 12:
        end_month -= 12
        end_year += 1
    if end_month == 12:
        end = datetime(end_year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end = datetime(end_year, end_month + 1, 1) - timedelta(seconds=1)
    return start, end


# 视图两侧各留 7 天缓冲：月历网格最多渲染前后各 6 天，周视图拖拽/跨天
# 日程也需要邻近日期的数据。留 7 天既盖住网格，又不会拉回整月。
MONTH_BUFFER_DAYS = 7
WEEK_BUFFER_DAYS = 7


def view_range(view_mode: str, current_date: datetime):
    """Return the ``(start, end)`` a view actually needs from the backend.

    Previously every refresh asked for "the whole month" regardless of the
    view, so a week spanning two months showed an empty column for the
    neighbouring month. The range is derived from what the view renders:

    - ``month``: the calendar grid can spill up to 6 days into the adjacent
      months on either side, so the month plus a 7-day buffer.
    - ``week``: Monday to Sunday, plus the same 7-day buffer.

    Unknown modes fall back to ``month`` (matching ``config.view_mode``
    validation) so a bad persisted value can never produce an empty window.
    """
    day = current_date.replace(hour=0, minute=0, second=0, microsecond=0)

    if view_mode == "week":
        monday = day - timedelta(days=day.weekday())
        start = monday - timedelta(days=WEEK_BUFFER_DAYS)
        end = monday + timedelta(days=6 + WEEK_BUFFER_DAYS)
    else:
        month_start, month_end = month_range(day)
        start = month_start - timedelta(days=MONTH_BUFFER_DAYS)
        end = month_end + timedelta(days=MONTH_BUFFER_DAYS)

    return start, end.replace(hour=23, minute=59, second=59, microsecond=0)


def event_sort_key(event: dict):
    """Return a comparable sort key for an event's start time.

    Always returns a float so mixed event shapes (timestamp vs datetime vs
    date) never cause a ``TypeError`` during ``list.sort``. Events whose time
    cannot be parsed sort to the end.
    """
    st = event.get("start_time", {})
    if not isinstance(st, dict):
        return float("inf")

    ts = st.get("timestamp", "")
    if ts:
        try:
            return float(ts)
        except (ValueError, TypeError):
            pass

    dt_str = st.get("datetime", "")
    if dt_str:
        try:
            return datetime.fromisoformat(dt_str).replace(tzinfo=None).timestamp()
        except (ValueError, TypeError):
            pass

    date_str = st.get("date", "")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").timestamp()
        except (ValueError, TypeError):
            pass

    return float("inf")


def get_local_tz_offset() -> str:
    """Return the system local timezone offset as ``'+08:00'`` format.

    Uses the running machine's local timezone so users outside China get
    correct start/end times instead of a hard-coded +08:00.
    """
    try:
        offset = datetime.now().astimezone().utcoffset()
    except (ValueError, OSError):
        return "+08:00"
    if offset is None:
        return "+08:00"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    hours = abs(total_minutes) // 60
    minutes = abs(total_minutes) % 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def get_local_tz_name() -> str:
    """Return the IANA timezone name (e.g. ``'Asia/Shanghai'``) when
    determinable, falling back to a sensible default."""
    try:
        tz = datetime.now().astimezone().tzinfo
        if tz is not None and hasattr(tz, "key"):
            return tz.key
    except (ValueError, OSError):
        pass
    return "Asia/Shanghai"
