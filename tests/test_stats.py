"""Insight statistics derived from the local store."""

from datetime import datetime, timedelta

import pytest

import stats


def ev(event_id, start, minutes=60, all_day=False, recurrence=None):
    payload = {
        "event_id": event_id,
        "summary": event_id,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
    }
    if all_day:
        payload["start_time"] = {"date": start.strftime("%Y-%m-%d")}
        payload["end_time"] = {"date": start.strftime("%Y-%m-%d")}
    else:
        payload["start_time"] = {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
        payload["end_time"] = {
            "datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        }
    if recurrence:
        payload["recurrence"] = [recurrence]
    return payload


def at(day, hour=0, minute=0):
    return datetime(2026, 11, day, hour, minute)


# ── Daily load ──────────────────────────────────────────────────────────────


def test_daily_stats_sums_timed_minutes():
    days = stats.daily_stats([ev("a", at(3, 9), 90), ev("b", at(3, 14), 30)], at(3), at(3, 23, 59))
    assert days[at(3).date()].minutes == 120
    assert days[at(3).date()].events == 2


def test_all_day_events_count_but_add_no_minutes():
    days = stats.daily_stats([ev("trip", at(3), all_day=True)], at(3), at(3, 23, 59))
    stat = days[at(3).date()]
    assert stat.events == 1
    assert stat.minutes == 0


def test_daily_stats_covers_every_day_in_range():
    days = stats.daily_stats([], at(1), at(5, 23, 59))
    assert len(days) == 5


def test_recurring_series_shows_up_on_each_occurrence():
    days = stats.daily_stats([ev("w", at(3, 10), recurrence="FREQ=WEEKLY;BYDAY=TU")], at(3), at(17, 23, 59))
    assert days[at(3).date()].minutes == 60
    assert days[at(10).date()].minutes == 60
    assert days[at(17).date()].minutes == 60


# ── Heatmap grid ────────────────────────────────────────────────────────────


def test_month_grid_is_monday_first_and_rectangular():
    grid = stats.month_grid([], 2026, 11)
    assert all(len(week) == 7 for week in grid)
    # 2026-11-01 是周日 → 首行前 6 格为空
    assert grid[0][6].day.day == 1
    assert grid[0][0] is None


def test_month_grid_only_contains_days_of_that_month():
    grid = stats.month_grid([], 2026, 11)
    days = [cell.day.day for week in grid for cell in week if cell is not None]
    assert days == list(range(1, 31))


def test_heat_level_buckets():
    assert stats.heat_level(0) == 0
    assert stats.heat_level(30) == 1
    assert stats.heat_level(60) == 2
    assert stats.heat_level(180) == 3
    assert stats.heat_level(600) == 4


# ── Summary ─────────────────────────────────────────────────────────────────


def test_summary_totals_and_busiest_day():
    events = [ev("a", at(3, 9), 120), ev("b", at(4, 9), 30)]
    summary = stats.summarize(events, at(1), at(7, 23, 59))
    assert summary.total_minutes == 150
    assert summary.total_events == 2
    assert summary.active_days == 2
    assert summary.busiest.day == at(3).date()


def test_summary_ignores_empty_days_for_busiest():
    summary = stats.summarize([], at(1), at(7, 23, 59))
    assert summary.busiest is None
    assert summary.total_minutes == 0


def test_weekday_minutes_distribution():
    events = [ev("mon", datetime(2026, 11, 2, 9), 60), ev("tue", datetime(2026, 11, 3, 9), 120)]
    summary = stats.summarize(events, datetime(2026, 11, 1), datetime(2026, 11, 7, 23, 59))
    assert summary.weekday_minutes[0] == 60   # 周一
    assert summary.weekday_minutes[1] == 120  # 周二
    assert summary.weekday_minutes[5] == 0


def test_longest_streak_counts_consecutive_days():
    days = {
        at(1).date(): stats.DayStat(at(1).date(), 30, 1),
        at(2).date(): stats.DayStat(at(2).date(), 30, 1),
        at(3).date(): stats.DayStat(at(3).date(), 30, 1),
        at(5).date(): stats.DayStat(at(5).date(), 30, 1),
    }
    assert stats.longest_streak(days) == 3


def test_longest_streak_zero_when_no_events():
    days = {at(1).date(): stats.DayStat(at(1).date(), 0, 0)}
    assert stats.longest_streak(days) == 0


def test_average_is_per_active_day_not_per_calendar_day():
    summary = stats.summarize([ev("a", at(3, 9), 120)], at(1), at(10, 23, 59))
    assert summary.days == 10
    assert summary.active_days == 1
    assert summary.average_minutes_per_active_day == 120


def test_format_minutes_reads_naturally():
    assert stats.format_minutes(0) == "—"
    assert stats.format_minutes(45) == "45 分"
    assert stats.format_minutes(120) == "2 小时"
    assert stats.format_minutes(150) == "2 小时 30 分"


@pytest.mark.parametrize("month", [1, 2, 12])
def test_month_bounds_are_inclusive(month):
    start, end = stats.month_bounds(2026, month)
    assert start.day == 1
    assert (end + timedelta(seconds=1)).day == 1
