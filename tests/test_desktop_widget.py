"""桌面小组件：数据层、呈现层与主窗口接线。

设计约定（见 docs/superpowers/plans/2026-11-04-desktop-widget-handoff.md）：
desktop_widget.py 里不许出现写死的颜色或尺寸——所有数值走 theme 令牌。
这组测试既钉行为，也用 AST 扫描钉住这条约定。
"""

import ast
import os
import re
from datetime import datetime, timedelta

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

import desktop_widget
import event_store
import theme
from desktop_widget import DesktopWidget, WidgetSnapshot, build_snapshot

app = QApplication.instance() or QApplication([])


def ev(event_id, start, minutes=60, summary=None, all_day=False):
    payload = {
        "event_id": event_id,
        "summary": summary or event_id,
        "organizer_calendar_id": "primary",
    }
    if all_day:
        payload["start_time"] = {"date": start.strftime("%Y-%m-%d")}
        payload["end_time"] = {"date": start.strftime("%Y-%m-%d")}
    else:
        payload["start_time"] = {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")}
        payload["end_time"] = {
            "datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        }
    return payload


def at(day, hour, minute=0):
    return datetime(2026, 11, day, hour, minute)


NOW = at(4, 10)  # 2026-11-04 周三，10:00


# ── build_snapshot：数据层 ────────────────────────────────────────────────


def test_snapshot_counts_today_events_and_minutes():
    events = [
        ev("a", at(4, 9), minutes=30),
        ev("b", at(4, 15), minutes=60),
        ev("c", at(5, 9)),  # 明天，不算今天
    ]
    snap = build_snapshot(events, NOW, int(NOW.timestamp()))
    assert snap.today_count == 2
    assert snap.today_minutes == 90
    assert "2 项" in snap.headline


def test_snapshot_all_day_counts_as_item_not_minutes():
    events = [ev("a", at(4, 0), all_day=True)]
    snap = build_snapshot(events, NOW, int(NOW.timestamp()))
    assert snap.today_count == 1
    assert snap.today_minutes == 0


def test_snapshot_trend_is_seven_days_oldest_to_newest():
    events = [ev("a", at(4, 9), minutes=30)]
    snap = build_snapshot(events, NOW, int(NOW.timestamp()))
    assert len(snap.trend) == 7
    # 最旧在前：今天（30 分钟）必须是最后一个
    assert snap.trend[-1] == 30
    assert all(m == 0 for m in snap.trend[:-1])


def test_snapshot_heat_is_weekday_rows():
    """热力图必须转置成「星期为行」：固定 7 行，每行长度一致。"""
    events = [ev("a", at(2, 9), minutes=60), ev("b", at(4, 9), minutes=120)]
    snap = build_snapshot(events, NOW, int(NOW.timestamp()))
    assert len(snap.heat) == 7
    assert len({len(row) for row in snap.heat}) == 1
    # 2026-11-04 是周三 → 第 3 行（周二索引 2）今天的档位应是最高之一
    assert max(snap.heat[2]) > 0


def test_snapshot_rows_are_upcoming_only_with_time_prefix():
    events = [
        ev("past", at(4, 8), minutes=30),   # 已结束，不进明细
        ev("now", at(4, 9), minutes=120),   # 进行中，end >= now
        ev("next", at(4, 15)),
    ]
    snap = build_snapshot(events, NOW, int(NOW.timestamp()))
    assert len(snap.rows) == 2
    assert snap.rows[0][0] == "09:00"
    assert snap.rows[1][0] == "15:00"
    assert snap.subline.startswith("进行中 09:00")


def test_snapshot_empty_state():
    snap = build_snapshot([], NOW, None)
    assert snap.empty is True
    assert snap.today_count == 0
    assert snap.headline == "今天没有日程"


def test_snapshot_stale_boundary():
    fresh = int(NOW.timestamp()) - 19 * 60
    stale = int(NOW.timestamp()) - 21 * 60
    assert build_snapshot([ev("a", NOW)], NOW, fresh).stale is False
    assert build_snapshot([ev("a", NOW)], NOW, stale).stale is True


def test_snapshot_without_sync_is_stale_and_says_so():
    snap = build_snapshot([ev("a", NOW)], NOW, None)
    assert snap.stale is True
    assert snap.updated_text == "尚未同步"


def test_snapshot_updated_text_buckets():
    ts = int(NOW.timestamp())
    assert build_snapshot([], NOW, ts - 30).updated_text == "刚刚更新"
    assert "分钟前" in build_snapshot([], NOW, ts - 5 * 60).updated_text
    assert "小时前" in build_snapshot([], NOW, ts - 3 * 3600).updated_text
    assert "更新" in build_snapshot([], NOW, ts - 2 * 86400).updated_text


# ── DesktopWidget：呈现层 ────────────────────────────────────────────────


@pytest.mark.parametrize("key, size", theme.WIDGET_SIZES.items())
def test_widget_size_matches_tokens(key, size):
    w = DesktopWidget(size_key=key)
    assert (w.width(), w.height()) == size


def test_widget_unknown_size_falls_back_to_medium():
    w = DesktopWidget(size_key="giant")
    assert w.size_key == "medium"
    assert (w.width(), w.height()) == theme.WIDGET_SIZES["medium"]


def test_widget_apply_theme_swaps_tokens():
    w = DesktopWidget(theme_name="dark")
    dark_number = w._t["number"]
    w.apply_theme("light")
    assert w._theme == "light"
    assert w._t["number"] != dark_number
    w.apply_theme("nonsense")  # 未知主题退回深色，不抛异常
    assert w._theme == "dark"


@pytest.mark.parametrize("key", list(theme.WIDGET_SIZES))
def test_widget_grab_offscreen_does_not_crash(key):
    """空数据和满数据两态、三档尺寸都能离屏渲染。"""
    w = DesktopWidget(size_key=key)
    w.set_snapshot(WidgetSnapshot())
    w.grab()
    events = [ev("a", at(4, 9), minutes=30), ev("b", at(4, 15)), ev("c", at(5, 9))]
    w.set_snapshot(build_snapshot(events, NOW, int(NOW.timestamp())))
    w.grab()


def test_qcolor_three_tuple_is_opaque():
    c = desktop_widget._qcolor((91, 157, 255))
    assert (c.red(), c.green(), c.blue()) == (91, 157, 255)
    assert c.alpha() == 255


def test_qcolor_four_tuple_scales_alpha():
    # 0.03×255=7.65 → round=8：关键是 alpha 非 0（直接把 0.03 传给 QColor 会被截成 0）
    c = desktop_widget._qcolor((255, 255, 255, 0.03))
    assert c.alpha() == 8
    c = desktop_widget._qcolor((255, 255, 255, 0.42))
    assert c.alpha() == 107


def test_widget_context_menu_does_not_exec(monkeypatch):
    """offscreen 下 QMenu.exec 会开阻塞事件循环永不返回——只验证菜单被构建。"""
    executed = []
    from PySide6.QtWidgets import QMenu

    class FakeMenu(QMenu):
        def exec(self, *a, **kw):  # noqa: N802
            executed.append(True)
            return None

    monkeypatch.setattr(desktop_widget, "QMenu", FakeMenu)
    w = DesktopWidget(size_key="medium")
    w.set_snapshot(build_snapshot([ev("a", NOW)], NOW, int(NOW.timestamp())))

    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent

    ce = QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100))
    w.contextMenuEvent(ce)
    assert executed == [True]


# ── 主窗口接线 ───────────────────────────────────────────────────────────


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = config_module.Config()
    cfg.set("widget_enabled", False)
    return cfg


@pytest.fixture
def store(tmp_path):
    conn = event_store.connect(tmp_path / "events.db")
    yield conn
    conn.close()


@pytest.fixture
def win(cfg, store, monkeypatch):
    import lark_cli_async
    from main_window import MainWindow

    monkeypatch.setattr(lark_cli_async.LarkCliAsync, "fetch_agenda", lambda self, *a, **kw: None)
    window = MainWindow(cfg, store=store)
    window.refresh_timer.stop()
    yield window
    window.dispose()
    window.deleteLater()
    app.processEvents()


def test_apply_widget_shows_when_enabled(win):
    win.config.set("widget_enabled", True)
    win._apply_desktop_widget()
    assert win._widget is not None
    assert win._widget.isVisible()


def test_apply_widget_hides_when_disabled(win):
    win.config.set("widget_enabled", True)
    win._apply_desktop_widget()
    win.config.set("widget_enabled", False)
    win._apply_desktop_widget()
    assert not win._widget.isVisible()


def test_close_request_disables_feature_in_config(win):
    win.config.set("widget_enabled", True)
    win._apply_desktop_widget()
    win._widget.close_requested.emit()
    assert win.config.get("widget_enabled", False) is False


def test_size_change_persists_and_resizes(win):
    win.config.set("widget_enabled", True)
    win._apply_desktop_widget()
    old = win._widget.size_key
    win._on_widget_size_changed("large" if old != "large" else "small")
    assert win.config.get("widget_size", "medium") in theme.WIDGET_SIZES
    assert win._widget.size_key != old
    assert (win._widget.width(), win._widget.height()) == theme.WIDGET_SIZES[win._widget.size_key]


def test_last_synced_bad_db_returns_none(tmp_path):
    """UI 安全壳：坏库返回 None，风格对齐 read_range。"""
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not a sqlite file" * 100)
    assert event_store.last_synced(event_store.connect(bad)) is None


def test_missing_db_last_synced_is_none(tmp_path):
    assert event_store.last_synced(event_store.connect(tmp_path / "none.db")) is None


# ── 守卫：不许写死颜色 ───────────────────────────────────────────────────

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def test_desktop_widget_carries_no_literal_colors():
    """desktop_widget.py 源码不许出现十六进制色值（docstring 豁免）。"""
    path = os.path.join(os.path.dirname(desktop_widget.__file__), "desktop_widget.py")
    tree = ast.parse(open(path, encoding="utf-8").read())
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                doc_ids.add(id(body[0].value))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in doc_ids:
                continue
            found += _HEX.findall(node.value)
    assert found == []
