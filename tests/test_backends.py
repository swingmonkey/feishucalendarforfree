"""Calendar backend protocol and its three implementations."""

from datetime import datetime, timedelta

import pytest

import backends
import event_store


def ev(event_id, start, minutes=60, summary=None, recurrence=None):
    payload = {
        "event_id": event_id,
        "summary": summary or event_id,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {"datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")},
    }
    if recurrence:
        payload["recurrence"] = [recurrence]
    return payload


# ── Protocol conformance ────────────────────────────────────────────────────


def test_all_backends_satisfy_the_protocol():
    conn = event_store.connect(":memory:")
    try:
        assert isinstance(backends.StoreBackend(conn), backends.CalendarBackend)
    finally:
        conn.close()

    class FakeCli:
        def get_agenda(self, start, end):
            return []

        def search_events(self, *a, **kw):
            return []

    assert isinstance(backends.LarkCliBackend(FakeCli()), backends.CalendarBackend)
    assert isinstance(backends.IcsBackend("x.ics"), backends.CalendarBackend)


def test_build_backend_rejects_unknown_source():
    with pytest.raises(backends.BackendError):
        backends.build_backend("exchange")


def test_build_backend_requires_a_path_for_ics():
    with pytest.raises(backends.BackendError):
        backends.build_backend("ics")


# ── Store backend ───────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path):
    conn = event_store.connect(tmp_path / "events.db")
    event_store.upsert_many(
        conn,
        [ev("a", datetime(2026, 11, 3, 10), summary="评审")],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    yield conn
    conn.close()


def test_store_fetch_returns_occurrences(store):
    backend = backends.StoreBackend(store)
    result = backend.fetch_range(datetime(2026, 11, 3), datetime(2026, 11, 3, 23, 59))
    assert [o.summary for o in result] == ["评审"]


def test_store_fetch_expands_recurring_series(store):
    event_store.upsert_many(
        store,
        [ev("w", datetime(2026, 11, 3, 9), recurrence="FREQ=WEEKLY;BYDAY=TU")],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    backend = backends.StoreBackend(store)
    result = backend.fetch_range(datetime(2026, 11, 3), datetime(2026, 11, 17, 23, 59))
    assert len([o for o in result if o.key.startswith("w@")]) == 3


def test_store_search_is_case_insensitive(store):
    backend = backends.StoreBackend(store)
    assert backend.search("评审")
    assert backend.search("不存在") == []


def test_store_is_read_only(store):
    backend = backends.StoreBackend(store)
    with pytest.raises(backends.ReadOnlyBackend):
        backend.create({})
    with pytest.raises(backends.ReadOnlyBackend):
        backend.update("a", {})
    with pytest.raises(backends.ReadOnlyBackend):
        backend.delete("a")


# ── ICS backend ─────────────────────────────────────────────────────────────

ICS_SAMPLE = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:evt-1
SUMMARY:塔台协调会
DTSTART:20261103T100000
DTEND:20261103T113000
DESCRIPTION:地点在三楼\\n带上资料
LOCATION:运行指挥中心
ORGANIZER:mailto:liao@example.com
END:VEVENT
BEGIN:VEVENT
UID:evt-2
SUMMARY:全天培训
DTSTART;VALUE=DATE:20261104
DTEND;VALUE=DATE:20261105
END:VEVENT
BEGIN:VEVENT
UID:evt-3
SUMMARY:一个很长的标题会被折
 行成两行
DTSTART:20261105T090000
DTEND:20261105T100000
END:VEVENT
END:VCALENDAR
"""


@pytest.fixture
def ics_file(tmp_path):
    path = tmp_path / "calendar.ics"
    path.write_text(ICS_SAMPLE, encoding="utf-8")
    return path


def test_ics_parses_timed_event(ics_file):
    events = backends.IcsBackend(ics_file).events()
    first = events[0]
    assert first["summary"] == "塔台协调会"
    assert first["start_time"]["datetime"] == "2026-11-03T10:00:00"
    assert first["end_time"]["datetime"] == "2026-11-03T11:30:00"
    assert first["event_organizer"]["display_name"] == "liao@example.com"
    assert "带上资料" in first["description"]


def test_ics_parses_all_day_event_as_date_only(ics_file):
    events = backends.IcsBackend(ics_file).events()
    all_day = [e for e in events if e["event_id"] == "evt-2"][0]
    assert all_day["start_time"] == {"date": "2026-11-04"}


def test_ics_unfolds_continuation_lines(ics_file):
    events = backends.IcsBackend(ics_file).events()
    folded = [e for e in events if e["event_id"] == "evt-3"][0]
    assert folded["summary"] == "一个很长的标题会被折行成两行"


def test_ics_fetch_range_filters_by_time(ics_file):
    backend = backends.IcsBackend(ics_file)
    result = backend.fetch_range(datetime(2026, 11, 3), datetime(2026, 11, 3, 23, 59))
    assert [o.summary for o in result] == ["塔台协调会"]


def test_ics_search_matches_summary(ics_file):
    backend = backends.IcsBackend(ics_file)
    assert [o.summary for o in backend.search("协调")] == ["塔台协调会"]


def test_ics_is_read_only(ics_file):
    backend = backends.IcsBackend(ics_file)
    with pytest.raises(backends.ReadOnlyBackend):
        backend.create({})


def test_ics_missing_file_raises_backend_error(tmp_path):
    backend = backends.IcsBackend(tmp_path / "nope.ics")
    with pytest.raises(backends.BackendError):
        backend.events()


# ── lark-cli backend ────────────────────────────────────────────────────────


class FakeCli:
    def __init__(self):
        self.calls = []

    def get_agenda(self, start, end):
        self.calls.append(("agenda", start, end))
        return [ev("a", datetime(2026, 11, 3, 10), summary="评审")]

    def search_events(self, query, start, end):
        self.calls.append(("search", query))
        return [ev("a", datetime(2026, 11, 3, 10), summary="评审")]

    def create_event(self, **kwargs):
        self.calls.append(("create", kwargs))
        return {"event_id": "new"}

    def delete_event(self, calendar_id, event_id, need_notification=False):
        self.calls.append(("delete", calendar_id, event_id))
        return True

    def _run(self, args):
        self.calls.append(("run", args))
        return {"data": {"event_id": "patched"}}


def test_lark_fetch_delegates_and_expands():
    cli = FakeCli()
    result = backends.LarkCliBackend(cli).fetch_range(
        datetime(2026, 11, 3), datetime(2026, 11, 3, 23, 59)
    )
    assert [o.summary for o in result] == ["评审"]
    assert cli.calls[0][0] == "agenda"


def test_lark_create_maps_payload_fields():
    cli = FakeCli()
    backends.LarkCliBackend(cli).create(
        {
            "summary": "新会",
            "start": datetime(2026, 11, 3, 10),
            "end": datetime(2026, 11, 3, 11),
            "description": "备注",
        }
    )
    kind, kwargs = cli.calls[0]
    assert kind == "create"
    assert kwargs["summary"] == "新会"
    assert kwargs["description"] == "备注"


def test_lark_update_uses_the_patch_api():
    cli = FakeCli()
    backends.LarkCliBackend(cli).update("evt-1", {"summary": "改名"})
    kind, args = cli.calls[0]
    assert kind == "run"
    assert args[0] == "api" and args[1] == "PATCH"
    assert "evt-1" in args[2]


def test_lark_delete_delegates():
    cli = FakeCli()
    assert backends.LarkCliBackend(cli).delete("evt-1") is True
    assert cli.calls[0] == ("delete", "primary", "evt-1")


def test_lark_wraps_failures_as_backend_error():
    class Boom:
        def get_agenda(self, *a):
            raise RuntimeError("lark-cli 未安装")

    with pytest.raises(backends.BackendError):
        backends.LarkCliBackend(Boom()).fetch_range(datetime.now(), datetime.now())
