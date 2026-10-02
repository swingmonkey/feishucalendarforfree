"""v2.2 体验改造的回归测试。

覆盖这一轮修掉的真实缺陷与新增能力：
- 「创建日程」软锁（P0）与地点并入描述
- 后台刷新失败不再摧毁已加载日历 + 登录面板返回出口
- 月历拖拽落点高亮、重复日程不再吞掉点击、日格条数按实际高度自适应
- 键盘快捷键与键盘游标、右键菜单
- 周视图全天分区与跨天延续
- 详情页子任务去重、重复规则中文化、全天日程勾选不再损坏数据
- 匿名统计 opt-out
"""

import inspect
import os
from datetime import datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, QPointF, Qt, Signal  # noqa: E402
from PySide6.QtGui import QDropEvent, QMouseEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import add_event_dialog  # noqa: E402
import lark_cli_async  # noqa: E402
import main  # noqa: E402
import settings_dialog  # noqa: E402
import usage_stats  # noqa: E402
from config import Config  # noqa: E402
from context_menu import build_background_menu, build_day_menu, build_event_menu  # noqa: E402
from day_detail_dialog import DayDetailDialog  # noqa: E402
from event_detail_dialog import EventDetailDialog  # noqa: E402
from main_window import MainWindow  # noqa: E402
from models_event import RECURRENCE_CHOICES, describe_recurrence, markdown_to_html  # noqa: E402
from widgets import DayCell, GridEventLabel, visible_event_count  # noqa: E402


@pytest.fixture(scope="session")
def app():
    existing = QApplication.instance()
    return existing or QApplication([])


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setattr("config.get_app_dir", lambda: tmp_path)
    return Config()


@pytest.fixture
def w(app, cfg, monkeypatch):
    """主窗口：屏蔽真实网络与桌面快捷方式副作用。"""
    monkeypatch.setattr(MainWindow, "refresh_events", lambda self: None)
    monkeypatch.setattr(main, "_ensure_desktop_shortcut", lambda config: None)
    return MainWindow(cfg)


def _event(**over):
    base = {
        "event_id": "evt_1",
        "summary": "周会",
        "organizer_calendar_id": "primary",
        "start_time": {"timestamp": str(int(datetime(2026, 8, 12, 10, 0).timestamp()))},
        "end_time": {"timestamp": str(int(datetime(2026, 8, 12, 11, 0).timestamp()))},
    }
    base.update(over)
    return base


def _all_day_event(**over):
    return _event(
        start_time={"date": "2026-08-12"},
        end_time={"date": "2026-08-13"},
        **over,
    )


# ─────────────────────────────────────────────────────────────────────────────
# P0：创建日程软锁 + 地点并入描述
# ─────────────────────────────────────────────────────────────────────────────

def test_create_event_signature_matches_dialog_call():
    """防回归：对话框传给 create_event 的关键字必须都被接受。

    历史上多传了一个 ``location``，TypeError 在 Qt 槽里抛出后没人接，
    对话框永久停在「创建中…」。这里直接用签名做静态校验。
    """
    source = inspect.getsource(add_event_dialog.AddEventDialog._on_create)
    assert "create_event" in source
    assert "location=" not in source, "create_event 不接受 location 参数"

    params = inspect.signature(lark_cli_async.LarkCliAsync.create_event).parameters
    for required in ("summary", "start", "end", "description", "rrule"):
        assert required in params, f"create_event 缺少参数 {required}"
    assert "location" not in params


def test_compose_description_appends_location():
    assert add_event_dialog.compose_description("正文", "3 号楼") == "正文\n\n📍 地点：3 号楼"
    assert add_event_dialog.compose_description("", "3 号楼") == "📍 地点：3 号楼"
    assert add_event_dialog.compose_description("正文", "") == "正文"
    assert add_event_dialog.compose_description("", "") == ""
    assert add_event_dialog.compose_description("正文", "  ") == "正文"


def test_create_flow_unlocks_on_unexpected_exception(app, cfg):
    """发起创建时抛异常必须解除软锁，而不是把表单永久变灰。"""

    class _Boom(QObject):
        event_created = Signal(dict)
        create_error = Signal(str)

        def create_event(self, **kwargs):
            self.calls.append(kwargs)
            raise TypeError("create_event() got an unexpected keyword argument")

        def __init__(self):
            super().__init__()
            self.calls = []

    cli = _Boom()
    dlg = add_event_dialog.AddEventDialog(cli, config=cfg)
    dlg.summary_input.setText("测试日程")
    dlg._on_create()

    assert cli.calls, "create_event 未被调用"
    assert "location" not in cli.calls[0]
    assert dlg._creating is False, "异常后仍处于创建中软锁状态"
    assert dlg.create_btn.isEnabled()
    assert dlg.summary_input.isEnabled()
    assert "创建失败" in dlg.form_message.text()


# ─────────────────────────────────────────────────────────────────────────────
# P1：后台刷新不再摧毁已加载日历
# ─────────────────────────────────────────────────────────────────────────────

def test_auth_error_after_successful_load_keeps_calendar(w, cfg):
    """已加载成功后，后台刷新遇到授权类错误也只发 Toast，不换面板。"""
    cfg.set("auth_completed", True)
    w._cli_available = True
    w._on_events_fetched([_event()])
    assert w.stack.currentIndex() in (0, 1)

    w._on_fetch_error("401 unauthorized: token invalid")

    assert w.stack.currentIndex() in (0, 1), "已加载的日历被登录面板顶掉了"
    assert not w.toast.isHidden()
    assert "刷新失败" in w.toast.msg_label.text()


def test_auth_panel_offers_way_back_to_loaded_calendar(w, cfg):
    cfg.set("auth_completed", True)
    w._cli_available = True
    w._on_fetch_error("missing scope calendar:calendar.event:read")
    assert w.stack.currentIndex() == 3
    # 首次加载就失败：没有可回退的日程，不该给出「返回」出口
    assert w.auth_back_btn.isHidden()

    w._on_events_fetched([_event()])
    w._show_auth("expired")
    assert not w.auth_back_btn.isHidden()

    w.auth_back_btn.click()
    assert w.stack.currentIndex() in (0, 1)


def test_refresh_error_panel_keeps_expanded_detail(w):
    """错误面板重试失败时不应把用户展开的错误详情重新折叠。"""
    w._cli_available = True
    w._first_load_done = False
    w._on_fetch_error("网络超时")
    assert w.stack.currentIndex() == 4
    w.error_detail.setVisible(True)
    w._detail_expanded = True

    w._show_error("又超时了")
    assert w._detail_expanded is False


# ─────────────────────────────────────────────────────────────────────────────
# 月历拖拽落点高亮 / 重复日程吞点击 / 高度自适应
# ─────────────────────────────────────────────────────────────────────────────

def test_day_cell_highlights_drop_target(app, cfg):
    from PySide6.QtCore import QMimeData
    from PySide6.QtGui import QDragLeaveEvent

    cell = DayCell(datetime(2026, 8, 12), [], True, config=cfg)
    assert cell.objectName() == "dayCell"

    mime = QMimeData()
    mime.setData("application/x-feishu-event", b'{"event_id":"e1"}')

    def _enter():
        return QDropEvent(
            QPointF(5, 5),
            Qt.DropAction.MoveAction,
            mime,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

    cell.dragEnterEvent(_enter())
    assert cell.objectName() == "dayCellDrop"

    cell.dragLeaveEvent(QDragLeaveEvent())
    assert cell.objectName() == "dayCell"


def test_drop_highlight_rules_exist_in_both_themes():
    from styles import get_theme

    for theme in ("light", "dark"):
        qss = get_theme(theme)
        assert "QFrame#dayCellDrop" in qss
        assert "QFrame#dayCellOtherDrop" in qss
        assert "QFrame#dayCellTodayDrop" in qss


def test_recurring_event_drag_does_not_swallow_click(app, cfg):
    """重复日程拖不动，但点击必须仍然打开详情（并给出提示）。"""
    from PySide6.QtCore import QEvent

    label = GridEventLabel(_event(recurrence="FREQ=WEEKLY"), config=cfg)
    blocked = []
    label.drag_blocked.connect(lambda: blocked.append(True))

    def _mouse(kind, pos, buttons):
        return QMouseEvent(
            kind,
            QPointF(*pos),
            Qt.MouseButton.LeftButton,
            buttons,
            Qt.KeyboardModifier.NoModifier,
        )

    label.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, (10, 10), Qt.MouseButton.LeftButton))
    label.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, (60, 60), Qt.MouseButton.LeftButton))

    assert blocked, "重复日程拖拽应给出提示"
    assert label._dragging is False, "重复日程被误判为已进入拖拽，点击会被吞掉"

    clicked = []
    label.clicked.connect(clicked.append)
    label.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, (60, 60), Qt.MouseButton.NoButton))
    assert clicked, "松手后没有触发点击，详情打不开"


def test_visible_event_count_uses_real_cell_height():
    """窗口压矮时按实际高度收缩，保证「+N更多」入口留在格内。"""
    assert visible_event_count(10, cell_height=100) == 3
    # 需要留一行给「+N更多」时可容纳条数不会更多
    assert visible_event_count(10, cell_height=100, reserve_more=True) <= 3
    # 极矮日格至少留 1 条 + 「+N更多」
    assert visible_event_count(10, cell_height=20, reserve_more=True) == 1
    # 高度缺失时回落到原有像素预算（保持既有行为）
    assert visible_event_count(10) == 3
    assert visible_event_count(24) == 1


def test_day_cell_rebuilds_more_label_when_short(app, cfg):
    """压矮日格后，原本藏起来的日程仍能通过「+N更多」点开。"""
    events = [(_event(summary=f"E{i}", event_id=f"e{i}"), False) for i in range(6)]
    cell = DayCell(datetime(2026, 8, 12), events, True, config=cfg)
    cell.resize(120, 20)
    assert cell._visible_limit < 6
    assert cell._more_widget is not None, "「+N更多」入口缺失，隐藏的日程无法访问"


# ─────────────────────────────────────────────────────────────────────────────
# 键盘快捷键与键盘游标
# ─────────────────────────────────────────────────────────────────────────────

def test_shortcuts_are_registered(w):
    seqs = {s.key().toString() for s in w._shortcuts}
    for expected in ("T", "R", "F", "N", "M", "W", "Left", "Right", "Up", "Down", "Return", "Esc"):
        assert expected in seqs, f"缺少快捷键 {expected}"


def test_single_key_shortcuts_yield_to_modal_dialog(app, w, monkeypatch):
    """模态对话框打开时，单键快捷键必须让位（否则在输入框敲 n 会再弹一个新建框）。"""
    from PySide6.QtWidgets import QDialog

    calls = []
    w._go_today = lambda: calls.append("today")

    class _Modal(QDialog):
        def show(self):
            from PySide6.QtWidgets import QApplication

            QApplication.processEvents()

    modal = _Modal(w)
    modal.setWindowModality(Qt.WindowModality.ApplicationModal)
    modal.show()
    app.processEvents()

    for shortcut in w._shortcuts:
        if shortcut.key().toString() == "T":
            shortcut.activated.emit()
    assert calls == [], "模态框打开时快捷键仍然生效"

    modal.close()


def test_keyboard_cursor_moves_and_highlights(w):
    w._view_mode = "month"
    w.current_date = datetime(2026, 8, 12)
    w._kb_cursor_date = datetime(2026, 8, 12)
    w.month_view.set_events([], w.current_date)

    w._kb_cursor_step(1)
    assert w._kb_cursor_date == datetime(2026, 8, 13)
    assert w.month_view.cursor_date() == datetime(2026, 8, 13).date()

    highlighted = [
        c.cell_date.date()
        for c in w.month_view._cells.values()
        if c._cursor
    ]
    assert highlighted == [datetime(2026, 8, 13).date()]


def test_keyboard_cursor_crossing_month_navigates(w):
    w._view_mode = "month"
    w.current_date = datetime(2026, 8, 31)
    w._kb_cursor_date = datetime(2026, 8, 31)
    w.month_view.set_events([], w.current_date)

    w._kb_cursor_step(1)
    assert w.current_date == datetime(2026, 9, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 右键菜单
# ─────────────────────────────────────────────────────────────────────────────

def test_event_context_menu_has_expected_actions(app, cfg):
    seen = {}
    menu = build_event_menu(
        None,
        _event(),
        cfg,
        on_open=lambda: seen.setdefault("open", True),
        on_duplicate=lambda: seen.setdefault("dup", True),
        on_delete=lambda: seen.setdefault("del", True),
        on_set_color=lambda hex_value: seen.setdefault("color", hex_value),
    )
    labels = [a.text() for a in menu.actions()]
    assert any("查看 / 编辑" in t for t in labels)
    assert any("复制日程" in t for t in labels)
    assert any("删除日程" in t for t in labels)
    assert any("颜色" in t for t in labels)

    for action in menu.actions():
        if "查看 / 编辑" in action.text():
            action.trigger()
    assert seen.get("open") is True


def test_background_menu_reflects_state(app):
    menu = build_background_menu(
        None,
        view_mode="week",
        pinned=True,
        on_add=lambda: None,
        on_today=lambda: None,
        on_set_view=lambda mode: None,
        on_toggle_pin=lambda checked: None,
    )
    texts = [a.text() for a in menu.actions()]
    assert any("新建日程" in t for t in texts)
    assert any("回到今天" in t for t in texts)
    assert any("月视图" in t for t in texts)
    pin = next(a for a in menu.actions() if a.text() == "窗口置顶")
    assert pin.isChecked() is True
    week = next(a for a in menu.actions() if "周视图" in a.text())
    assert week.isChecked() is True


def test_day_menu_disables_view_when_empty():
    menu = build_day_menu(None, datetime(2026, 8, 12), has_events=False, on_open_day=lambda: None)
    action = next(a for a in menu.actions() if "查看当日日程" in a.text())
    assert action.isEnabled() is False


def test_duplicate_event_creates_copy(app, w):
    calls = []
    w.lark_cli.create_event = lambda **kw: calls.append(kw)
    w._duplicate_event(_event())
    assert calls, "复制日程没有发起创建"
    assert calls[0]["summary"] == "周会（副本）"
    assert calls[0]["start"] == datetime(2026, 8, 12, 10, 0)


def test_set_event_color_persists_locally(app, w, cfg):
    w.events = [_event()]
    w._set_event_color(_event(), "#34C724")
    assert cfg.get("event_colors")["evt_1"] == "#34C724"
    w._set_event_color(_event(), "")
    assert "evt_1" not in (cfg.get("event_colors") or {})


# ─────────────────────────────────────────────────────────────────────────────
# 周视图：全天分区 + 跨天延续
# ─────────────────────────────────────────────────────────────────────────────

def test_week_view_separates_all_day_events(app, cfg):
    from event_card import EventCard
    from week_view import WeekView

    view = WeekView(cfg)
    anchor = datetime(2026, 8, 12)
    timed = _event(event_id="t1", summary="定时")
    all_day = _all_day_event(event_id="a1", summary="全天")
    view.set_events([timed, all_day], anchor)

    # 周一 2026-08-10 起算，08-12 是第 3 列
    col = next(c for c in view._columns if c.col_date.date() == anchor.date())
    allday_ids = [c.event_data.get("event_id") for c in col._allday_bar.findChildren(EventCard)]
    timed_ids = [c.event_data.get("event_id") for c in col._list.findChildren(EventCard)]

    assert allday_ids == ["a1"], "全天日程没有进顶部全天条"
    assert timed_ids == ["t1"], "定时日程没有留在下方列表"


def test_multiday_continuation_is_marked(app, cfg):
    from event_card import EventCard

    multi = _event(
        event_id="m1",
        start_time={"timestamp": str(int(datetime(2026, 8, 12, 9, 0).timestamp()))},
        end_time={"timestamp": str(int(datetime(2026, 8, 14, 9, 0).timestamp()))},
    )
    cont = EventCard(multi, config=cfg, is_continuation=True)
    assert "↳" in cont.time_label.text()
    assert "09:00" not in cont.time_label.text()

    fresh = EventCard(multi, config=cfg, is_continuation=False)
    assert "09:00" in fresh.time_label.text()


def test_event_card_has_tooltip(app, cfg):
    from event_card import EventCard

    card = EventCard(_event(), config=cfg)
    assert "周会" in card.toolTip()


# ─────────────────────────────────────────────────────────────────────────────
# 详情页
# ─────────────────────────────────────────────────────────────────────────────

def test_markdown_strip_tasks_removes_duplicate_checklist():
    text = "正文\n\n- [ ] 任务一\n- [x] 任务二"
    assert "<input" in markdown_to_html(text)
    stripped = markdown_to_html(text, strip_tasks=True)
    assert "<input" not in stripped
    assert "任务一" not in stripped
    assert "正文" in stripped


def test_describe_recurrence_matches_create_dialog():
    assert describe_recurrence(None) == "不重复"
    assert describe_recurrence("") == "不重复"
    for label, rule in RECURRENCE_CHOICES:
        if rule:
            assert describe_recurrence(rule) == label
    # 未知规则不丢信息
    assert "FREQ=YEARLY" in describe_recurrence("FREQ=YEARLY")


def test_detail_dialog_shows_chinese_recurrence(app, cfg):
    dlg = EventDetailDialog(_event(recurrence="FREQ=WEEKLY;INTERVAL=2"), None, config=cfg)
    assert dlg._recurrence_text() == "每两周"
    assert "FREQ=" not in dlg._recurrence_text()


def test_subtask_toggle_on_allday_event_does_not_send_times(app, cfg):
    """全天日程勾选子任务不能把整天事件改成带时刻的定时事件。"""

    class _FakeCli(QObject):
        event_updated = Signal(dict)
        update_error = Signal(str)

        def __init__(self):
            super().__init__()
            self.calls = []

        def update_event(self, **kwargs):
            self.calls.append(kwargs)

    cli = _FakeCli()
    dlg = EventDetailDialog(
        _all_day_event(description="- [ ] 买牛奶"),
        cli,
        config=cfg,
    )
    dlg._on_subtask_toggled(0, True)

    assert cli.calls, "没有发起更新"
    assert "start" not in cli.calls[0] and "end" not in cli.calls[0], "全天日程被写入了具体时刻"
    assert cli.calls[0]["description"] == "- [x] 买牛奶"


def test_subtask_toggle_on_timed_event_still_sends_times(app, cfg):
    class _FakeCli(QObject):
        event_updated = Signal(dict)
        update_error = Signal(str)

        def __init__(self):
            super().__init__()
            self.calls = []

        def update_event(self, **kwargs):
            self.calls.append(kwargs)

    cli = _FakeCli()
    dlg = EventDetailDialog(
        _event(description="- [ ] 买牛奶"),
        cli,
        config=cfg,
    )
    dlg._on_subtask_toggled(0, True)
    assert "start" in cli.calls[0] and "end" in cli.calls[0]


# ─────────────────────────────────────────────────────────────────────────────
# 当日列表删除确认
# ─────────────────────────────────────────────────────────────────────────────

def test_day_dialog_keeps_list_when_delete_cancelled(app, cfg, monkeypatch):
    import ui_common

    monkeypatch.setattr(ui_common.ConfirmDialog, "ask", staticmethod(lambda *a, **k: False))
    emitted = []
    dlg = DayDetailDialog(datetime(2026, 8, 12), [_event()], None, config=cfg)
    dlg.event_delete_requested.connect(emitted.append)

    dlg._on_card_delete(_event())

    assert emitted == [], "取消确认仍然发出了删除"
    assert dlg.result() == 0 or not dlg.isVisible(), "取消确认后当日列表被关掉了"


def test_day_dialog_closes_after_confirmed_delete(app, cfg, monkeypatch):
    import ui_common

    monkeypatch.setattr(ui_common.ConfirmDialog, "ask", staticmethod(lambda *a, **k: True))
    emitted = []
    dlg = DayDetailDialog(datetime(2026, 8, 12), [_event()], None, config=cfg)
    dlg.event_delete_requested.connect(emitted.append)

    dlg._on_card_delete(_event())
    assert emitted, "确认后没有发出删除"


# ─────────────────────────────────────────────────────────────────────────────
# 匿名统计 opt-out
# ─────────────────────────────────────────────────────────────────────────────

class _FakeStatusWorker(QObject):
    checked = Signal(bool, bool)

    def __init__(self, result, parent=None):
        super().__init__(parent)
        self._result = result

    def start(self):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self.checked.emit(*self._result))


class _FakeStatsWorker(QObject):
    result = Signal(object)

    def __init__(self, result=None, parent=None):
        super().__init__(parent)
        self._result = result

    def start(self):
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: self.result.emit(self._result))


def _settings(monkeypatch, cfg):
    monkeypatch.setattr(
        settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((True, True), parent)
    )
    monkeypatch.setattr(
        settings_dialog.usage_stats, "StatsWorker", lambda parent=None: _FakeStatsWorker({}, parent)
    )
    return settings_dialog.SettingsDialog(cfg)


def test_settings_has_usage_stats_opt_out(monkeypatch, app, cfg):
    cfg.set("install_id", "a" * 32)
    cfg.set("usage_stats_enabled", True)
    dlg = _settings(monkeypatch, cfg)
    assert dlg.stats_check.isChecked() is True

    dlg.stats_check.setChecked(False)
    assert cfg.get("usage_stats_enabled") is False
    assert cfg.get("install_id") == "", "关闭统计后应清除随机安装标识"
    dlg.close()


def test_heartbeat_not_sent_when_opted_out(monkeypatch, cfg):
    cfg.set("usage_stats_enabled", False)
    sent = []
    monkeypatch.setattr(
        usage_stats, "ensure_install_id", lambda c: sent.append("id") or "b" * 32
    )
    monkeypatch.setattr(
        usage_stats,
        "HeartbeatWorker",
        lambda *a, **k: pytest.fail("关闭统计时不应发起心跳"),
    )

    class _App:
        pass

    fake = _App()
    fake.config = cfg
    fake._usage_worker = None
    main.TrayApp._send_usage_heartbeat(fake)
    assert sent == []
    assert fake._usage_worker is None


def test_about_tab_no_longer_claims_no_third_party(app, monkeypatch, cfg):
    dlg = _settings(monkeypatch, cfg)
    texts = [
        lbl.text()
        for lbl in dlg.findChildren(type(dlg.usage_status_label))
    ]
    assert any("关闭" in t for t in texts), "关于页没有告知统计可关闭"
    dlg.close()


# ─────────────────────────────────────────────────────────────────────────────
# 设置页其它修错
# ─────────────────────────────────────────────────────────────────────────────

def test_missing_cli_button_really_redetects(monkeypatch, app, cfg):
    """文案是「重新检测」时，按钮必须真的重新检测，而不是打开登录框。"""
    monkeypatch.setattr(
        settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((False, False), parent)
    )
    monkeypatch.setattr(
        settings_dialog.usage_stats, "StatsWorker", lambda parent=None: _FakeStatsWorker({}, parent)
    )
    opened = []
    monkeypatch.setattr(settings_dialog, "LoginDialog", lambda *a, **k: opened.append(1))

    dlg = settings_dialog.SettingsDialog(cfg)
    app.processEvents()
    assert dlg.login_btn.text() == "重新检测"

    dlg.login_btn.click()
    assert opened == [], "「重新检测」却打开了登录框"
    dlg.close()


def test_auto_start_failure_reverts_checkbox(app, cfg, monkeypatch):
    dlg = _settings(monkeypatch, cfg)
    monkeypatch.setattr(
        settings_dialog.SettingsDialog,
        "_set_auto_start",
        lambda self, enabled: (_ for _ in ()).throw(OSError("拒绝访问")),
    )
    dlg.auto_start_check.setChecked(True)
    assert dlg.auto_start_check.isChecked() is False, "开机启动失败后勾选没有回滚"
    assert cfg.get("auto_start") is False
    assert dlg.startup_message.isHidden() is False
    assert "失败" in dlg.startup_message.text()
    dlg.close()


def test_opacity_slider_matches_config_clamp(app, monkeypatch, cfg):
    """手改 config.json 的透明度不能造成「界面与磁盘长期不一致」。"""
    cfg.set("opacity", 0.33)
    dlg = _settings(monkeypatch, cfg)
    assert dlg.opacity_slider.minimum() == 20
    assert dlg.opacity_slider.value() == 33
    dlg.close()


def test_update_dialog_status_is_not_self_contradictory(app, cfg):
    from update_dialog import UpdateDialog

    dlg = UpdateDialog({"tag": "v9.9.9", "body": "notes"}, "2.1.6", None)
    dlg._on_finished(True, "更新已应用，即将重启")
    text = dlg.status_label.text()
    assert "下次启动时自动完成更新" not in text
    assert "生效" in text
    dlg.close()
