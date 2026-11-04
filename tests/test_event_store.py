"""Offline tests for the local SQLite event fact layer.

These tests never touch lark-cli or the network: every case builds plain
Feishu-shaped event dicts and asserts on what the store hands back.
"""

from datetime import datetime, timedelta

import pytest

import event_store


def ev(
    event_id,
    start,
    end,
    summary="会议",
    description="",
    organizer="张三",
    recurrence=None,
    all_day=False,
    calendar_id="primary",
):
    """Build an event dict shaped like lark-cli ``calendar +agenda`` output."""
    if all_day:
        start_time = {"date": start.strftime("%Y-%m-%d"), "timezone": "UTC"}
        end_time = {"date": end.strftime("%Y-%m-%d"), "timezone": "UTC"}
    else:
        start_time = {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
        end_time = {"datetime": end.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
    payload = {
        "event_id": event_id,
        "summary": summary,
        "description": description,
        "start_time": start_time,
        "end_time": end_time,
        "organizer_calendar_id": calendar_id,
        "event_organizer": {"display_name": organizer},
    }
    if recurrence:
        payload["recurrence"] = recurrence
    return payload


@pytest.fixture()
def conn(tmp_path):
    connection = event_store.connect(tmp_path / "events.db")
    yield connection
    connection.close()


def at(day, hour=10):
    return datetime(2026, 11, day, hour, 0, 0)


# ── upsert semantics ─────────────────────────────────────────────────────────


def test_upsert_is_idempotent(conn):
    """Re-syncing the same event must not duplicate it."""
    event = ev("e1", at(3), at(3, 11))
    event_store.upsert_many(conn, [event], at(1), at(30))
    event_store.upsert_many(conn, [event], at(1), at(30))
    assert event_store.count(conn) == 1


def test_upsert_updates_changed_fields(conn):
    event_store.upsert_many(conn, [ev("e1", at(3), at(3, 11), summary="旧标题")], at(1), at(30))
    event_store.upsert_many(conn, [ev("e1", at(3), at(3, 11), summary="新标题")], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30))
    assert len(result) == 1
    assert result[0]["summary"] == "新标题"


def test_upsert_preserves_unknown_fields(conn):
    """The raw payload must round-trip untouched so views keep working."""
    event = ev("e1", at(3), at(3, 11))
    event["meeting_url"] = "https://example.com/room"
    event["attendees"] = [{"name": "李四"}]
    event_store.upsert_many(conn, [event], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30))
    assert result[0]["meeting_url"] == "https://example.com/room"
    assert result[0]["attendees"] == [{"name": "李四"}]


def test_upsert_skips_events_without_id(conn):
    broken = ev("", at(3), at(3, 11))
    event_store.upsert_many(conn, [broken], at(1), at(30))
    assert event_store.count(conn) == 0


def test_upsert_tolerates_non_list_payload(conn):
    assert event_store.upsert_many(conn, None, at(1), at(30)) == 0


# ── range queries ────────────────────────────────────────────────────────────


def test_query_range_returns_overlapping_events(conn):
    event_store.upsert_many(conn, [
        ev("before", at(1), at(2)),
        ev("inside", at(10), at(10, 11)),
        ev("after", at(25), at(26)),
    ], at(1), at(30))
    result = event_store.query_range(conn, at(5), at(15))
    assert [e["event_id"] for e in result] == ["inside"]


def test_query_range_includes_event_spanning_start_boundary(conn):
    """A multi-day event starting before the window must still be returned."""
    event_store.upsert_many(conn, [ev("span", at(1), at(8))], at(1), at(30))
    result = event_store.query_range(conn, at(5), at(10))
    assert [e["event_id"] for e in result] == ["span"]


def test_query_range_includes_recurring_series_started_earlier(conn):
    """Recurring templates start before the window but occur inside it."""
    event_store.upsert_many(conn, [
        ev("weekly", at(2), at(2, 11), recurrence="FREQ=WEEKLY;BYDAY=MO"),
    ], at(1), at(30))
    result = event_store.query_range(conn, at(16), at(30))
    assert [e["event_id"] for e in result] == ["weekly"]


def test_query_range_sorted_by_start(conn):
    event_store.upsert_many(conn, [
        ev("late", at(20), at(20, 11)),
        ev("early", at(5), at(5, 11)),
    ], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30))
    assert [e["event_id"] for e in result] == ["early", "late"]


def test_query_range_honours_calendar_id(conn):
    event_store.upsert_many(conn, [
        ev("primary_event", at(5), at(5, 11)),
        ev("other_event", at(6), at(6, 11), calendar_id="cal_2"),
    ], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30), calendar_id="cal_2")
    assert [e["event_id"] for e in result] == ["other_event"]


def test_all_day_event_roundtrip(conn):
    event = ev("allday", at(3), at(3), all_day=True)
    event_store.upsert_many(conn, [event], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30))
    assert result[0]["start_time"]["date"] == "2026-11-03"
    assert event_store.all_day_flags(conn)["allday"] is True


# ── coverage bookkeeping ─────────────────────────────────────────────────────


def test_covered_ranges_records_synced_window(conn):
    event_store.upsert_many(conn, [], at(1), at(30))
    spans = event_store.covered_ranges(conn)
    assert len(spans) == 1
    start, end = spans[0]
    assert datetime.fromtimestamp(start) == at(1)
    assert datetime.fromtimestamp(end) == at(30)


def test_is_range_covered_after_sync(conn):
    event_store.upsert_many(conn, [], at(1), at(30))
    assert event_store.is_range_covered(conn, at(5), at(10)) is True
    assert event_store.is_range_covered(conn, at(5), datetime(2026, 12, 10)) is False


def test_is_range_covered_false_on_empty_store(conn):
    assert event_store.is_range_covered(conn, at(5), at(10)) is False


# ── pruning removed upstream ─────────────────────────────────────────────────


def test_prune_removes_events_missing_from_snapshot(conn):
    """An event deleted in Feishu must disappear after the range re-syncs."""
    event_store.upsert_many(conn, [
        ev("keep", at(5), at(5, 11)),
        ev("gone", at(6), at(6, 11)),
    ], at(1), at(30))
    event_store.upsert_many(conn, [ev("keep", at(5), at(5, 11))], at(1), at(30))
    result = event_store.query_range(conn, at(1), at(30))
    assert [e["event_id"] for e in result] == ["keep"]


def test_empty_snapshot_clears_only_that_range(conn):
    """Deleting the last event of a day locally must show up as an empty day."""
    event_store.upsert_many(conn, [ev("last", at(5), at(5, 11))], at(1), at(30))
    event_store.upsert_many(conn, [], at(1), at(10))
    assert event_store.query_range(conn, at(1), at(10)) == []


def test_malformed_payload_does_not_wipe_cache(conn):
    """A broken/absent response must never destroy the local cache."""
    event_store.upsert_many(conn, [ev("keep", at(5), at(5, 11))], at(1), at(30))
    event_store.upsert_many(conn, None, at(1), at(30))
    event_store.upsert_many(conn, {"ok": False}, at(1), at(30))
    assert event_store.count(conn) == 1


def test_prune_respects_range_boundaries(conn):
    """Events outside the synced window are never pruned."""
    event_store.upsert_many(conn, [
        ev("inside", at(5), at(5, 11)),
        ev("outside", at(28), at(28, 11)),
    ], at(1), at(30))
    event_store.upsert_many(conn, [], at(1), at(10))
    remaining = [e["event_id"] for e in event_store.query_range(conn, at(1), at(30))]
    assert remaining == ["outside"]


def test_prune_drops_deleted_recurring_series(conn):
    """``+agenda`` always returns live series, so a missing series is deleted."""
    event_store.upsert_many(conn, [
        ev("series", at(2), at(2, 11), recurrence="FREQ=WEEKLY;BYDAY=MO"),
    ], at(1), at(30))
    # 下一窗口只覆盖 11-20 之后，系列模板起始于 11-02 仍应被清掉
    event_store.upsert_many(conn, [], datetime(2026, 11, 20), at(30))
    assert event_store.count(conn) == 0


# ── delete & search ──────────────────────────────────────────────────────────


def test_delete_event_removes_row(conn):
    event_store.upsert_many(conn, [ev("e1", at(5), at(5, 11))], at(1), at(30))
    assert event_store.delete_event(conn, "e1") is True
    assert event_store.count(conn) == 0


def test_delete_event_missing_returns_false(conn):
    assert event_store.delete_event(conn, "nope") is False


def test_search_matches_summary_description_and_organizer(conn):
    event_store.upsert_many(conn, [
        ev("a", at(5), at(5, 11), summary="塔台协调会"),
        ev("b", at(6), at(6, 11), description="讨论管制员资质"),
        ev("c", at(7), at(7, 11), organizer="廖总"),
    ], at(1), at(30))
    assert [e["event_id"] for e in event_store.search(conn, "塔台")] == ["a"]
    assert [e["event_id"] for e in event_store.search(conn, "资质")] == ["b"]
    assert [e["event_id"] for e in event_store.search(conn, "廖总")] == ["c"]


def test_search_is_case_insensitive(conn):
    event_store.upsert_many(conn, [ev("a", at(5), at(5, 11), summary="Briefing")], at(1), at(30))
    assert [e["event_id"] for e in event_store.search(conn, "briefing")] == ["a"]


def test_search_empty_query_returns_nothing(conn):
    event_store.upsert_many(conn, [ev("a", at(5), at(5, 11))], at(1), at(30))
    assert event_store.search(conn, "   ") == []


def test_search_escapes_like_wildcards(conn):
    """``%`` must be matched literally, not as a wildcard."""
    event_store.upsert_many(conn, [
        ev("pct", at(5), at(5, 11), summary="完成度 100%"),
        ev("other", at(6), at(6, 11), summary="无关"),
    ], at(1), at(30))
    assert [e["event_id"] for e in event_store.search(conn, "%")] == ["pct"]


# ── durability ───────────────────────────────────────────────────────────────


def test_corrupted_db_self_heals(tmp_path):
    db_path = tmp_path / "events.db"
    db_path.write_bytes(b"this is not a sqlite file")
    connection = event_store.connect(db_path)
    assert event_store.count(connection) == 0
    event_store.upsert_many(connection, [ev("e1", at(5), at(5, 11))], at(1), at(30))
    assert event_store.count(connection) == 1
    connection.close()


def test_two_connections_share_data(tmp_path):
    db_path = tmp_path / "events.db"
    first = event_store.connect(db_path)
    event_store.upsert_many(first, [ev("e1", at(5), at(5, 11))], at(1), at(30))
    second = event_store.connect(db_path)
    assert event_store.count(second) == 1
    first.close()
    second.close()


def test_reopen_keeps_events(tmp_path):
    """The whole point: a restart must not lose the calendar."""
    db_path = tmp_path / "events.db"
    connection = event_store.connect(db_path)
    event_store.upsert_many(connection, [ev("e1", at(5), at(5, 11))], at(1), at(30))
    connection.close()
    reopened = event_store.connect(db_path)
    assert event_store.count(reopened) == 1
    reopened.close()


def test_prune_drops_rows_older_than_retention(tmp_path):
    connection = event_store.connect(tmp_path / "events.db")
    old = datetime.now() - timedelta(days=800)
    event_store.upsert_many(
        connection,
        [ev("ancient", old, old + timedelta(hours=1))],
        old, old + timedelta(days=1),
    )
    event_store.upsert_many(connection, [ev("fresh", at(5), at(5, 11))], at(1), at(30))
    event_store.enforce_retention(connection, days=370)
    assert [e["event_id"] for e in event_store.query_range(connection, at(1), at(30))] == ["fresh"]
    connection.close()


# ── v2.11.3：启动容错与跨日历清理 ──────────────────────────────────────────
# 用户报告的两个真实故障：数据目录不可写时整个应用起不来；其他日历上被
# 上游删除的日程永久残留在缓存里（+agenda 不带 --calendar-id，返回的是
# 账号下所有日历的合并结果）。


def test_connect_falls_back_to_memory_when_directory_unwritable(tmp_path):
    """数据目录只读时不能抛异常：退回内存库，本次运行照常可用。"""
    blocked = tmp_path / "blocked"
    blocked.mkdir()
    blocked.chmod(0o500)  # r-x：不可写
    try:
        conn = event_store.connect(blocked / "events.db")
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        conn.close()
    finally:
        blocked.chmod(0o700)


def test_prune_with_default_calendar_covers_all_calendars(conn):
    """默认 calendar_id 表示「所有日历的合并快照」，清理要跨日历。"""
    start, end = datetime(2026, 11, 1), datetime(2026, 11, 30, 23, 59, 59)
    primary = ev("a", at(4), at(4, 11), calendar_id="primary")
    other = ev("b", at(5), at(5, 11), calendar_id="work-cal")

    event_store.store_snapshot(conn, [primary, other], start, end)
    assert {e["event_id"] for e in event_store.read_range(conn, start, end)} == {"a", "b"}

    # 上游删掉了 b：第二次快照只剩 a，b 必须一起消失
    event_store.store_snapshot(conn, [primary], start, end)
    ids = {e["event_id"] for e in event_store.read_range(conn, start, end)}
    assert "a" in ids
    assert "b" not in ids


def test_prune_with_explicit_calendar_only_touches_that_calendar(conn):
    """显式指定日历时不越界：另一本日历的行不受影响。

    注意 ``"primary"`` 本身就是 DEFAULT_CALENDAR_ID，用它当「显式指定」
    区分不出两条路径；这里必须用一本非默认日历。
    """
    start, end = datetime(2026, 11, 1), datetime(2026, 11, 30, 23, 59, 59)
    primary = ev("a", at(4), at(4, 11), calendar_id="primary")
    other = ev("b", at(5), at(5, 11), calendar_id="work-cal")
    event_store.store_snapshot(conn, [primary, other], start, end)

    # 只同步 work-cal 且结果为空：只能删 work-cal 的行
    event_store.store_snapshot(conn, [], start, end, calendar_id="work-cal")
    ids = {e["event_id"] for e in event_store.read_range(conn, start, end)}
    assert "b" not in ids
    assert "a" in ids
