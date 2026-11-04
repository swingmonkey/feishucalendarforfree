"""Integration tests for the local-first refresh path (v2.4).

Covers the behaviour that motivated the SQLite fact layer:

- the window paints from the local store before the network answers;
- a successful sync is persisted, so a restart is not a blank calendar;
- an offline / expired-auth refresh keeps the cached calendar on screen;
- the fetched range follows the view, not the calendar month (D2);
- deleting an event drops it locally even if the follow-up sync fails.
"""

import sys
from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

import event_store
from config import Config
from lark_cli_async import LarkCliAsync
from main_window import MainWindow
from utils import view_range

app = QApplication.instance() or QApplication(sys.argv[:1])


def _event(event_id="evt_1", start=None, summary="周会"):
    start = start or datetime(2026, 11, 12, 10)
    return {
        "event_id": event_id,
        "summary": summary,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {"datetime": (start.replace(hour=start.hour + 1)).strftime("%Y-%m-%dT%H:%M:%S+08:00")},
    }


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    return Config()


@pytest.fixture
def calls(monkeypatch):
    """Record fetch requests instead of spawning lark-cli."""
    recorded = []
    monkeypatch.setattr(
        LarkCliAsync,
        "fetch_agenda",
        lambda self, current_date, monthly=False, view_mode=None: recorded.append(
            {"date": current_date, "view_mode": view_mode}
        ),
    )
    return recorded


@pytest.fixture
def store(tmp_path):
    conn = event_store.connect(tmp_path / "events.db")
    yield conn
    conn.close()


@pytest.fixture
def win(cfg, store, calls):
    window = MainWindow(cfg, store=store)
    window.current_date = datetime(2026, 11, 15)
    yield window
    window.dispose()
    window.deleteLater()
    app.processEvents()


def test_startup_paints_from_cache_before_network(win, store):
    event_store.upsert_many(
        store, [_event()], datetime(2026, 10, 25), datetime(2026, 12, 7, 23, 59, 59)
    )
    win.refresh_events()

    assert [e["event_id"] for e in win.events] == ["evt_1"]
    assert "本地缓存" in win.status_label.text()
    # 仍然发起了同步：缓存只是先手，不是终点
    assert win.stack.currentIndex() == 0


def test_empty_cache_shows_loading_panel(win):
    win._first_load_done = False
    win.refresh_events()
    assert win.stack.currentIndex() == 2, "无缓存时应显示加载面板"


def test_sync_is_persisted_for_next_launch(win, store):
    win._on_events_fetched([_event("evt_9", datetime(2026, 11, 20, 10))])
    assert event_store.count(store) == 1

    # 「重启」= 新连接读同一个库
    reopened = event_store.connect(store.execute("PRAGMA database_list").fetchone()[2])
    try:
        assert event_store.count(reopened) == 1
    finally:
        reopened.close()


def test_fetch_range_follows_the_view(win, calls):
    win.refresh_events()
    win._set_view_mode("week")
    assert calls[-1]["view_mode"] == "week"


def test_offline_refresh_keeps_cached_calendar(win, store):
    event_store.upsert_many(
        store, [_event()], datetime(2026, 10, 25), datetime(2026, 12, 7, 23, 59, 59)
    )
    win.refresh_events()
    assert win.stack.currentIndex() == 0

    # 授权过期 + 断网：不得把日历换成登录面板
    win._on_fetch_error("token expired: unauthorized")
    assert win.stack.currentIndex() == 0
    assert win.events, "缓存日程必须仍然可读"
    assert "本地缓存" in win.status_label.text()


def test_auth_error_without_cache_still_shows_login(win):
    win._first_load_done = False
    win._cli_available = True
    win._on_fetch_error("token expired: unauthorized")
    assert win.stack.currentIndex() == 3


def test_delete_drops_event_locally(win, store):
    win._on_events_fetched([_event("evt_1"), _event("evt_2", datetime(2026, 11, 13, 10))])
    assert event_store.count(store) == 2

    win._on_deleted("evt_1")
    assert event_store.count(store) == 1
    assert all(e["event_id"] != "evt_1" for e in win.events)


def test_hidden_month_rows_survive_resync(win, store):
    """A month synced earlier stays readable when switching to another month."""
    win._on_events_fetched([_event("nov", datetime(2026, 11, 20, 10))])
    win.current_date = datetime(2027, 1, 15)
    win.refresh_events()  # 1 月无缓存、未同步 → 只发请求
    assert event_store.count(store) == 1, "切到未同步的月份不应清空旧数据"


def test_week_spanning_two_months_shows_both_sides(win, calls):
    """D2 回归：10-26 ~ 11-01 这一周，两侧日程都要出现。"""
    win.current_date = datetime(2026, 10, 28)
    win._set_view_mode("week")

    start, end = view_range("week", datetime(2026, 10, 28))
    assert start <= datetime(2026, 10, 26) and end >= datetime(2026, 11, 1, 23, 59)

    win._on_events_fetched([
        _event("oct", datetime(2026, 10, 28, 9)),
        _event("nov", datetime(2026, 11, 1, 15)),
    ])

    assert {e["event_id"] for e in win.events} == {"oct", "nov"}


def test_switching_to_a_covered_week_does_not_hit_the_network(win, calls):
    """已同步过的窗口只从本地重绘，不再起一个 node 进程。"""
    win.current_date = datetime(2026, 10, 28)
    win._set_view_mode("week")
    win._on_events_fetched([])  # 该周同步完成（本周无日程也是合法结果）

    win._set_view_mode("month")  # 月份窗口还没同步过，允许联网
    baseline = len(calls)
    win._set_view_mode("week")  # 周窗口已覆盖 → 不应再打网络

    assert len(calls) == baseline


def test_search_dialog_searches_the_local_store_offline(win, store, monkeypatch):
    """D7：服务端搜索不可用时，本地索引仍然能搜出结果。"""
    from search_dialog import SearchDialog

    monkeypatch.setattr(LarkCliAsync, "search_events", lambda self, **kw: None)
    event_store.upsert_many(
        store,
        [_event("evt_1", datetime(2026, 11, 12, 10), summary="塔台协调会")],
        datetime(2026, 10, 25),
        datetime(2026, 12, 7, 23, 59, 59),
    )

    dialog = SearchDialog(win.lark_cli, win, store=store)
    try:
        dialog._on_fetch_error("network unreachable")
        dialog.search_input.setText("塔台")
        assert dialog.result_list.count() == 1
        assert "本地" in dialog.result_label.text()
    finally:
        dialog.close()


def test_on_events_fetched_uses_request_range(win, store, monkeypatch):
    """落库区间必须是「发出请求时」的区间，不是响应到达时的当前视图。

    快速翻页时 11 月的响应会在视图已经切到 12 月之后才到；若按当前视图落库，
    旧响应会 prune 掉 12 月缓存，还把 12 月误标成已同步，之后不再联网补数据。
    """
    captured = {}
    real = event_store.store_snapshot

    def spy(conn, events, start, end, *a, **kw):
        captured["start"], captured["end"] = start, end
        return real(conn, events, start, end, *a, **kw)

    monkeypatch.setattr(event_store, "store_snapshot", spy)

    win.current_date = datetime(2026, 12, 15)  # 视图已经翻到 12 月
    req_start = datetime(2026, 11, 1)
    req_end = datetime(2026, 11, 30, 23, 59, 59)

    win._on_events_fetched([], req_start, req_end)

    assert captured["start"] == req_start
    assert captured["end"] == req_end
