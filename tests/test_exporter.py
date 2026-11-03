"""Scheduled JSON/CSV export of the local agenda snapshot."""

import csv
import io
import json
from datetime import datetime, timedelta

import pytest

import event_store
import exporter


def ev(event_id, start, minutes=60, summary=None):
    return {
        "event_id": event_id,
        "summary": summary or event_id,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {"datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")},
    }


class FakeConfig:
    def __init__(self, **values):
        self._data = {
            "export_schedule": "daily",
            "export_dir": "",
            "export_last_run": "",
        }
        self._data.update(values)

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


@pytest.fixture
def conn(tmp_path):
    connection = event_store.connect(tmp_path / "events.db")
    yield connection
    connection.close()


# ── Atomic writes ───────────────────────────────────────────────────────────


def test_atomic_write_leaves_no_temp_file(tmp_path):
    path = exporter.atomic_write_text(tmp_path / "a.txt", "hello")
    assert path.read_text(encoding="utf-8") == "hello"
    assert not list(tmp_path.glob("*.tmp"))


def test_atomic_write_creates_missing_directories(tmp_path):
    path = exporter.atomic_write_text(tmp_path / "deep" / "deeper" / "a.txt", "x")
    assert path.exists()


# ── Payload shape ───────────────────────────────────────────────────────────


def test_json_payload_is_stable_and_parsable():
    rows = exporter.build_rows([ev("a", datetime(2026, 11, 3, 10), summary="评审")], datetime(2026, 11, 1), datetime(2026, 11, 30, 23, 59))
    payload = json.loads(exporter.build_json(rows, datetime(2026, 11, 3, 12, 0)))
    assert payload["count"] == 1
    assert payload["source"] == "FeishuCalendarDesktop"
    assert payload["events"][0]["summary"] == "评审"
    assert payload["events"][0]["start"] == "10:00"


def test_csv_header_and_escaping():
    rows = exporter.build_rows(
        [ev("a", datetime(2026, 11, 3, 10), summary='评审, 带"引号"')],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    parsed = list(csv.DictReader(io.StringIO(exporter.build_csv(rows))))
    assert list(parsed[0].keys()) == exporter.CSV_COLUMNS
    assert parsed[0]["summary"] == '评审, 带"引号"'


def test_snapshot_writes_two_files_with_the_export_date(tmp_path, conn):
    event_store.upsert_many(
        conn,
        [ev("a", datetime(2026, 11, 5, 10))],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    written = exporter.export_snapshot(conn, tmp_path / "out", datetime(2026, 11, 3, 20, 0))
    names = sorted(p.name for p in written)
    assert names == ["events-20261103.csv", "events-20261103.json"]
    assert all(p.exists() for p in written)


def test_snapshot_only_includes_the_rolling_window(tmp_path, conn):
    event_store.upsert_many(
        conn,
        [ev("inside", datetime(2026, 11, 5, 10)), ev("far", datetime(2027, 6, 1, 10))],
        datetime(2026, 1, 1),
        datetime(2027, 12, 31),
    )
    written = exporter.export_snapshot(conn, tmp_path / "out", datetime(2026, 11, 3, 20, 0))
    payload = json.loads(written[0].read_text(encoding="utf-8"))
    assert [e["event_id"] for e in payload["events"]] == ["inside"]


# ── Scheduling ──────────────────────────────────────────────────────────────


def test_off_schedule_never_runs(tmp_path):
    config = FakeConfig(export_schedule="off", export_dir=str(tmp_path))
    assert exporter.is_due(config, datetime(2026, 11, 3, 9)) is False


def test_missing_directory_never_runs():
    config = FakeConfig(export_schedule="daily", export_dir="")
    assert exporter.is_due(config, datetime(2026, 11, 3, 9)) is False


def test_daily_runs_once_per_day(tmp_path):
    config = FakeConfig(export_dir=str(tmp_path), export_last_run="2026-11-03T08:00:00")
    assert exporter.is_due(config, datetime(2026, 11, 3, 18)) is False
    assert exporter.is_due(config, datetime(2026, 11, 4, 8)) is True


def test_weekly_runs_once_per_iso_week(tmp_path):
    config = FakeConfig(export_schedule="weekly", export_dir=str(tmp_path), export_last_run="2026-11-03T08:00:00")
    assert exporter.is_due(config, datetime(2026, 11, 6, 8)) is False
    assert exporter.is_due(config, datetime(2026, 11, 9, 8)) is True


def test_corrupt_last_run_triggers_a_run(tmp_path):
    config = FakeConfig(export_dir=str(tmp_path), export_last_run="not-a-date")
    assert exporter.is_due(config, datetime(2026, 11, 3, 9)) is True


def test_run_if_due_stamps_the_run(tmp_path, conn):
    config = FakeConfig(export_dir=str(tmp_path / "out"))
    written = exporter.run_if_due(conn, config, datetime(2026, 11, 3, 9, 30))
    assert written
    assert config.get("export_last_run") == "2026-11-03T09:30:00"
    assert exporter.run_if_due(conn, config, datetime(2026, 11, 3, 10)) == []


def test_run_if_due_swallows_failures_and_does_not_stamp(tmp_path, conn):
    """A read-only destination must be logged, not raised, and retried later."""
    blocked = tmp_path / "file-in-the-way"
    blocked.write_text("x", encoding="utf-8")
    config = FakeConfig(export_dir=str(blocked / "nested"))

    assert exporter.run_if_due(conn, config, datetime(2026, 11, 3, 9)) == []
    assert config.get("export_last_run") == ""
