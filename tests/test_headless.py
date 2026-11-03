"""Headless CLI: read the calendar without a window (or Qt)."""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

import event_store
import headless

REPO = Path(__file__).resolve().parent.parent


def ev(event_id, start, minutes=60, summary=None):
    return {
        "event_id": event_id,
        "summary": summary or event_id,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {"datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")},
    }


@pytest.fixture
def db(tmp_path):
    """A store holding one event later today, so ``today``/``next`` have a hit."""
    path = tmp_path / "events.db"
    conn = event_store.connect(path)
    now = datetime.now().replace(microsecond=0)
    later = now + timedelta(minutes=90)
    if later.date() != now.date():
        later = now.replace(hour=23, minute=30, second=0)
    event_store.upsert_many(
        conn,
        [ev("today-1", later, 30, summary="塔台班前会"), ev("far", now + timedelta(days=40), 60, summary="远期")],
        now - timedelta(days=1),
        now + timedelta(days=2),
    )
    conn.close()
    return str(path)


def test_today_json_envelope(db, capsys):
    assert headless.main(["today", "--db", db, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "today"
    assert payload["count"] == 1
    assert payload["events"][0]["summary"] == "塔台班前会"
    assert payload["events"][0]["organizer"] == "张三"


def test_today_text_output(db, capsys):
    assert headless.main(["today", "--db", db]) == 0
    out = capsys.readouterr().out
    assert "塔台班前会" in out
    assert "张三" in out


def test_next_returns_a_single_event(db, capsys):
    assert headless.main(["next", "--db", db, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["command"] == "next"


def test_empty_day_prints_a_readable_message(tmp_path, capsys):
    path = tmp_path / "empty.db"
    event_store.connect(path).close()
    assert headless.main(["today", "--db", str(path)]) == 0
    assert "没有日程" in capsys.readouterr().out


def test_range_filters_by_dates(db, capsys):
    start = (datetime.now() + timedelta(days=39)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=41)).strftime("%Y-%m-%d")
    assert headless.main(["range", "--db", db, "--start", start, "--end", end, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [e["summary"] for e in payload["events"]] == ["远期"]


def test_bad_date_is_a_usage_error(db, capsys):
    assert headless.main(["range", "--db", db, "--start", "11/03/2026", "--end", "2026-11-30"]) == 2
    assert "YYYY-MM-DD" in capsys.readouterr().err


def test_limit_caps_the_output(db, capsys):
    start = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    end = (datetime.now() + timedelta(days=41)).strftime("%Y-%m-%d")
    assert headless.main(["range", "--db", db, "--start", start, "--end", end, "--limit", "1", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["count"] == 1


def test_ics_source_reads_a_file(tmp_path, capsys):
    ics = tmp_path / "cal.ics"
    ics.write_text(
        "BEGIN:VCALENDAR\n"
        "BEGIN:VEVENT\nUID:x\nSUMMARY:ICS 会议\n"
        "DTSTART:20261103T100000\nDTEND:20261103T110000\n"
        "END:VEVENT\nEND:VCALENDAR\n",
        encoding="utf-8",
    )
    assert (
        headless.main(
            ["range", "--source", "ics", "--ics", str(ics), "--start", "2026-11-03", "--end", "2026-11-03", "--json"]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert [e["summary"] for e in payload["events"]] == ["ICS 会议"]


def test_missing_ics_file_reports_failure(tmp_path, capsys):
    assert (
        headless.main(
            ["today", "--source", "ics", "--ics", str(tmp_path / "nope.ics")]
        )
        == 1
    )
    assert "读取失败" in capsys.readouterr().err


def test_search_uses_the_backend(db, capsys):
    assert headless.main(["search", "班前会", "--db", db, "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [e["summary"] for e in payload["events"]] == ["塔台班前会"]


def test_cli_runs_without_pyside6():
    """A headless command must not drag the GUI toolkit onto the import path."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, headless; "
            "assert 'PySide6' not in sys.modules, 'headless imported Qt'; "
            "print('ok')",
        ],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ok" in result.stdout


def test_module_entry_point_runs(tmp_path):
    path = tmp_path / "events.db"
    event_store.connect(path).close()
    result = subprocess.run(
        [sys.executable, "-m", "headless", "today", "--db", str(path), "--json"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["count"] == 0
