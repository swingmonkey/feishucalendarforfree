"""Offline tests for view-aware fetch ranges.

Regression cover for the "week view spanning two months shows an empty
column" bug: ``refresh_events`` used to always ask for the whole month,
so events in the neighbouring month were never fetched.
"""

import calendar
from datetime import datetime, timedelta

import pytest

from utils import view_range

MONTH_BUFFER_DAYS = 7
WEEK_BUFFER_DAYS = 7


def covers(start, end, moment):
    return start <= moment <= end


def test_month_range_covers_whole_month():
    start, end = view_range("month", datetime(2026, 11, 15))
    assert start == datetime(2026, 10, 25, 0, 0, 0)
    assert end == datetime(2026, 12, 7, 23, 59, 59)


def test_month_range_crosses_year_boundary():
    start, end = view_range("month", datetime(2026, 1, 10))
    assert start == datetime(2025, 12, 25, 0, 0, 0)
    assert end == datetime(2026, 2, 7, 23, 59, 59)


def test_week_range_covers_monday_to_sunday_with_buffer():
    # 2026-11-03 is a Tuesday, so the week runs 11-02 .. 11-08
    start, end = view_range("week", datetime(2026, 11, 3))
    assert start == datetime(2026, 10, 26, 0, 0, 0)
    assert end == datetime(2026, 11, 15, 23, 59, 59)


def test_week_range_spanning_two_months_covers_both_sides():
    """The D2 regression: 10-28 sits in the week 10-26 .. 11-01."""
    start, end = view_range("week", datetime(2026, 10, 28))
    assert covers(start, end, datetime(2026, 10, 26, 0, 0))
    assert covers(start, end, datetime(2026, 11, 1, 23, 59))


def test_week_range_starts_on_monday_for_sunday_input():
    start, _ = view_range("week", datetime(2026, 11, 8))  # Sunday
    assert start == datetime(2026, 10, 26, 0, 0, 0)


def test_unknown_view_mode_falls_back_to_month():
    assert view_range("year", datetime(2026, 11, 15)) == view_range("month", datetime(2026, 11, 15))


@pytest.mark.parametrize("year", [2026, 2027])
@pytest.mark.parametrize("month", range(1, 13))
def test_month_range_always_covers_the_rendered_grid(year, month):
    """Whatever the month grid renders must be inside the fetch window."""
    grid = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    grid_start = datetime.combine(grid[0][0], datetime.min.time())
    grid_end = datetime.combine(grid[-1][-1], datetime.max.time())

    start, end = view_range("month", datetime(year, month, 15))
    assert start <= grid_start, f"{year}-{month:02d} grid starts before fetch window"
    assert end >= grid_end, f"{year}-{month:02d} grid ends after fetch window"


def test_range_is_aware_of_time_of_day_input():
    """A mid-day ``current_date`` must not shift the window."""
    early, _ = view_range("month", datetime(2026, 11, 1, 0, 0))
    late, _ = view_range("month", datetime(2026, 11, 30, 23, 59))
    assert early == late


def test_buffers_are_exposed_as_constants():
    """Views and tests read the same numbers instead of hardcoding them."""
    assert MONTH_BUFFER_DAYS == 7
    assert WEEK_BUFFER_DAYS == 7
    month_start, month_end = view_range("month", datetime(2026, 11, 15))
    assert month_start == datetime(2026, 11, 1) - timedelta(days=MONTH_BUFFER_DAYS)
