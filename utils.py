"""Shared date-range and event-sorting helpers for both API backends."""

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
