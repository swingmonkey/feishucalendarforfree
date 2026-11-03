"""Reminder / conflict / overload logic and the notification service.

These tests pin the behaviour a calendar app owes its user: a meeting that
starts in ten minutes produces exactly one notification, overlapping meetings
produce exactly one conflict warning, and quiet hours silence everything.
"""

from datetime import datetime, timedelta

import pytest

import event_store
import reminder


def ev(event_id, start, minutes=60, summary=None, all_day=False, recurrence=None):
    payload = {
        "event_id": event_id,
        "summary": summary or event_id,
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


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute)


@pytest.fixture
def conn(tmp_path):
    connection = event_store.connect(tmp_path / "events.db")
    yield connection
    connection.close()


# ── Occurrence collection ───────────────────────────────────────────────────


def test_collects_single_event_once():
    events = [ev("a", at(3, 10))]
    occ = reminder.collect_occurrences(events, at(3, 0), at(3, 23))
    assert len(occ) == 1
    assert occ[0].key.startswith("a@")


def test_recurring_series_is_expanded_not_duplicated():
    """The template and its first occurrence must collapse into one row."""
    events = [ev("weekly", at(3, 10), recurrence="FREQ=WEEKLY;BYDAY=TU")]
    occ = reminder.collect_occurrences(events, at(3, 0), at(17, 23))
    starts = sorted(o.start for o in occ)
    assert starts == [at(3, 10), at(10, 10), at(17, 10)]
    assert len({o.key for o in occ}) == len(occ)


def test_collect_occurrences_ignores_out_of_window_events():
    events = [ev("far", at(20, 10))]
    assert reminder.collect_occurrences(events, at(3, 0), at(5, 23)) == []


# ── Reminder timing ─────────────────────────────────────────────────────────


def test_reminder_fires_inside_lead_window():
    occ = reminder.collect_occurrences([ev("a", at(3, 10))], at(3, 0), at(3, 23))
    hits = reminder.due_reminders(occ, at(3, 9, 55), lead_minutes=10, notified=set())
    assert [h.key for h in hits] == [occ[0].key]
    assert hits[0].minutes_until == 5


def test_reminder_does_not_fire_before_lead_window():
    occ = reminder.collect_occurrences([ev("a", at(3, 10))], at(3, 0), at(3, 23))
    assert reminder.due_reminders(occ, at(3, 9, 30), lead_minutes=10, notified=set()) == []


def test_reminder_is_skipped_once_notified():
    occ = reminder.collect_occurrences([ev("a", at(3, 10))], at(3, 0), at(3, 23))
    hits = reminder.due_reminders(occ, at(3, 9, 55), 10, notified={occ[0].key})
    assert hits == []


def test_reminder_never_fires_for_an_event_that_already_started():
    """A scan that starts late must not shout about a meeting under way."""
    occ = reminder.collect_occurrences([ev("a", at(3, 10))], at(3, 0), at(3, 23))
    assert reminder.due_reminders(occ, at(3, 10, 3), 10, notified=set()) == []


def test_all_day_events_do_not_produce_reminders():
    occ = reminder.collect_occurrences([ev("trip", at(3, 0), all_day=True)], at(3, 0), at(3, 23))
    assert reminder.due_reminders(occ, at(3, 0, 5), 24 * 60, notified=set()) == []


def test_lead_minutes_zero_fires_at_start_time():
    occ = reminder.collect_occurrences([ev("a", at(3, 10))], at(3, 0), at(3, 23))
    assert reminder.due_reminders(occ, at(3, 10, 0), 0, notified=set())
    assert reminder.due_reminders(occ, at(3, 10, 1), 0, notified=set()) == []


# ── Conflicts and load ──────────────────────────────────────────────────────


def test_conflict_group_contains_overlapping_events():
    occ = reminder.collect_occurrences(
        [ev("a", at(3, 10)), ev("b", at(3, 10, 30), summary="重叠")],
        at(3, 0),
        at(3, 23),
    )
    groups = reminder.find_conflicts(occ)
    assert len(groups) == 1
    assert {o.key.split("@")[0] for o in groups[0]} == {"a", "b"}


def test_back_to_back_meetings_are_not_a_conflict():
    occ = reminder.collect_occurrences(
        [ev("a", at(3, 10), minutes=60), ev("b", at(3, 11), minutes=60)],
        at(3, 0),
        at(3, 23),
    )
    assert reminder.find_conflicts(occ) == []


def test_all_day_events_never_conflict():
    occ = reminder.collect_occurrences(
        [ev("trip", at(3, 0), all_day=True), ev("a", at(3, 10))],
        at(3, 0),
        at(3, 23),
    )
    assert reminder.find_conflicts(occ) == []


def test_day_load_sums_timed_durations():
    occ = reminder.collect_occurrences(
        [ev("a", at(3, 9), minutes=90), ev("b", at(3, 14), minutes=30)],
        at(3, 0),
        at(3, 23),
    )
    assert reminder.day_load_minutes(occ, at(3, 0)) == 120


def test_day_load_ignores_all_day_events():
    occ = reminder.collect_occurrences(
        [ev("trip", at(3, 0), all_day=True), ev("a", at(3, 9), minutes=60)],
        at(3, 0),
        at(3, 23),
    )
    assert reminder.day_load_minutes(occ, at(3, 0)) == 60


# ── Tray summary ────────────────────────────────────────────────────────────


def test_tray_summary_shows_count_and_next_event():
    events = [ev("a", at(3, 10), summary="评审"), ev("b", at(3, 16), summary="复盘")]
    text = reminder.tray_summary(events, at(3, 9))
    assert text == "今天 2 项 · 10:00 评审"


def test_tray_summary_marks_running_event():
    events = [ev("a", at(3, 10), summary="评审")]
    assert reminder.tray_summary(events, at(3, 10, 20)).startswith("进行中 评审")


def test_tray_summary_when_day_is_empty():
    assert reminder.tray_summary([], at(3, 9)) == "今天没有日程"


def test_tray_summary_truncates_long_titles():
    events = [ev("a", at(3, 10), summary="天府机场塔台管制专业行政检查准备会")]
    text = reminder.tray_summary(events, at(3, 9))
    assert len(text) <= 30
    assert text.endswith("…")


# ── Quiet hours ─────────────────────────────────────────────────────────────


def test_quiet_hours_wrap_midnight():
    assert reminder.in_quiet_hours(datetime(2026, 11, 3, 23, 30), "22:00", "08:00") is True
    assert reminder.in_quiet_hours(datetime(2026, 11, 4, 7, 0), "22:00", "08:00") is True
    assert reminder.in_quiet_hours(datetime(2026, 11, 3, 12, 0), "22:00", "08:00") is False


def test_quiet_hours_same_day_window():
    assert reminder.in_quiet_hours(datetime(2026, 11, 3, 13, 0), "12:00", "14:00") is True
    assert reminder.in_quiet_hours(datetime(2026, 11, 3, 15, 0), "12:00", "14:00") is False


class FakeConfig:
    def __init__(self, **overrides):
        self._data = {
            "reminder_enabled": True,
            "reminder_lead_minutes": 10,
            "conflict_alert_enabled": True,
            "overload_alert_enabled": True,
            "overload_threshold_hours": 6,
            "quiet_hours_enabled": False,
            "quiet_start": "22:00",
            "quiet_end": "08:00",
        }
        self._data.update(overrides)

    def get(self, key, default=None):
        return self._data.get(key, default)


# ── Service ─────────────────────────────────────────────────────────────────


def _seed(conn, events, now):
    event_store.store_snapshot(
        conn, events, now - timedelta(days=1), now + timedelta(days=1)
    )


def test_service_emits_exactly_one_reminder(conn):
    now = at(3, 9, 55)
    _seed(conn, [ev("a", at(3, 10), summary="塔台协调会")], now)
    service = reminder.ReminderService(conn, FakeConfig())
    first = service.scan(now)
    assert len(first) == 1
    assert "塔台协调会" in first[0][0]
    assert "10:00" in first[0][1]
    assert service.scan(now + timedelta(seconds=30)) == []


def test_service_dedupes_by_occurrence_start(conn):
    """A weekly meeting next week is a different occurrence and must re-notify."""
    now = at(3, 9, 55)
    _seed(conn, [ev("weekly", at(3, 10), recurrence="FREQ=WEEKLY;BYDAY=TU")], now)
    service = reminder.ReminderService(conn, FakeConfig())
    assert len(service.scan(now)) == 1
    later = at(10, 9, 55)
    assert len(service.scan(later)) == 1


def test_service_respects_quiet_hours(conn):
    now = datetime(2026, 11, 3, 23, 55)
    _seed(conn, [ev("a", datetime(2026, 11, 4, 0, 0))], now)
    service = reminder.ReminderService(
        conn, FakeConfig(quiet_hours_enabled=True, quiet_start="22:00", quiet_end="08:00")
    )
    assert service.scan(now) == []


def test_service_reports_conflict_once_per_day(conn):
    now = at(3, 9)
    _seed(conn, [ev("a", at(3, 10)), ev("b", at(3, 10, 30))], now)
    service = reminder.ReminderService(conn, FakeConfig(reminder_enabled=False))
    first = service.scan(now)
    assert len(first) == 1 and "冲突" in first[0][0]
    assert service.scan(now + timedelta(minutes=1)) == []


def test_service_reports_overload_once_per_day(conn):
    now = at(3, 8)
    events = [ev(f"m{i}", at(3, 9 + i), minutes=120) for i in range(4)]
    _seed(conn, events, now)
    service = reminder.ReminderService(
        conn,
        FakeConfig(reminder_enabled=False, conflict_alert_enabled=False, overload_threshold_hours=6),
    )
    first = service.scan(now)
    assert len(first) == 1 and "超载" in first[0][0]
    assert service.scan(now + timedelta(minutes=1)) == []


def test_service_disabled_does_nothing(conn):
    now = at(3, 9, 55)
    _seed(conn, [ev("a", at(3, 10))], now)
    service = reminder.ReminderService(
        conn,
        FakeConfig(
            reminder_enabled=False,
            conflict_alert_enabled=False,
            overload_alert_enabled=False,
        ),
    )
    assert service.scan(now) == []


def test_service_survives_a_broken_store():
    class Boom:
        def execute(self, *a, **kw):
            raise RuntimeError("db gone")

    service = reminder.ReminderService(Boom(), FakeConfig())
    assert service.scan(at(3, 9, 55)) == []
