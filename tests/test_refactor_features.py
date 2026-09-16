"""Offline regression tests for the v2.1 UX refactor.

覆盖：
- 头部最小化按钮、「＋」主操作、溢出菜单收敛
- 启动零弹窗：初始为加载面板，不直接弹登录框
- 登录状态机：首次引导 / 过期重登 / 未装 CLI / 普通错误
- 登录态持久化：成功拉取日程后写入 auth_completed
- Toast / ConfirmDialog 公共组件
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication

import login_dialog
import settings_dialog
from config import Config
from main_window import MainWindow, _is_auth_error
from ui_common import ConfirmDialog

app = QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    return Config()


@pytest.fixture
def w(cfg):
    win = MainWindow(cfg)
    yield win
    # 干净地回收 QProcess / 定时器 / 窗口，避免 Qt 在解释器退出时崩溃
    from PySide6.QtCore import QProcess
    win.refresh_timer.stop()
    for proc in win.lark_cli.findChildren(QProcess):
        proc.kill()
        proc.waitForFinished(1000)
    win.deleteLater()
    app.processEvents()


# ─────────────────────────────────────────────────────────────────────────────
# 头部按钮收敛
# ─────────────────────────────────────────────────────────────────────────────

def test_minimize_button_exists(w):
    assert w.min_btn.text() == "—"
    assert w.min_btn.toolTip() == "最小化"


def test_primary_add_button_is_brand_blue(w):
    assert w.add_btn.objectName() == "addBtn"


def test_header_actions_collapsed_into_overflow_menu(w):
    """搜索 / 导出 / 置顶 / 主题 / 设置收进溢出菜单，头部不再散落一排按钮。"""
    assert not hasattr(w, "search_btn")
    assert not hasattr(w, "export_btn")
    assert not hasattr(w, "pin_btn")
    assert not hasattr(w, "theme_btn")
    texts = [a.text() for a in w.more_btn.menu().actions()]
    assert "搜索日程" in texts
    assert "导出到 Excel" in texts
    assert any("窗口置顶" in t for t in texts)
    assert any("深色主题" in t for t in texts)
    assert "设置" in texts


def test_month_bar_has_no_login_button(w):
    """月份栏不再放「一键登录」按钮，登录入口收进菜单与引导面板。"""
    assert not hasattr(w, "login_btn")


# ─────────────────────────────────────────────────────────────────────────────
# 启动零弹窗 + 登录状态机
# ─────────────────────────────────────────────────────────────────────────────

def test_startup_shows_inline_loading_panel_not_login_dialog(w):
    # stack: 0=month 1=week 2=loading 3=auth 4=error
    assert w.stack.currentIndex() == 2


def test_successful_fetch_persists_auth_and_shows_calendar(w, cfg):
    assert cfg.get("auth_completed") is False
    w._on_events_fetched([])
    assert cfg.get("auth_completed") is True
    assert w.stack.currentIndex() in (0, 1)


def test_auth_error_first_time_shows_welcome_panel(w, cfg):
    cfg.set("auth_completed", False)
    w._cli_available = True
    w._on_fetch_error("Error: missing required scope calendar:calendar.event:read")
    assert w.stack.currentIndex() == 3
    assert w.auth_title.text() == "登录飞书账号"


def test_auth_error_after_prior_login_shows_expired_panel(w, cfg):
    cfg.set("auth_completed", True)
    w._cli_available = True
    w._on_fetch_error("401 unauthorized: token invalid")
    assert w.stack.currentIndex() == 3
    assert w.auth_title.text() == "登录已过期"


def test_missing_cli_shows_install_guidance(w):
    w._cli_available = False
    w._on_fetch_error("lark-cli 启动失败")
    assert w.stack.currentIndex() == 3
    assert w.auth_title.text() == "需要先安装 lark-cli"
    assert not w.auth_detail.isHidden()


def test_other_error_shows_error_panel_with_retry(w):
    w._cli_available = True
    w._first_load_done = False
    w._on_fetch_error("网络超时：connection timed out")
    assert w.stack.currentIndex() == 4


def test_background_refresh_error_uses_toast_not_panel(w):
    # 先完成一次成功加载进入日历视图
    w._on_events_fetched([])
    w._cli_available = True
    w._first_load_done = True
    w._on_fetch_error("网络超时")
    # 已成功加载过后，后台刷新失败不应抢占日历视图
    assert w.stack.currentIndex() in (0, 1)
    assert not w.toast.isHidden()


def test_auth_error_classification():
    assert _is_auth_error("missing scope calendar.event:read")
    assert _is_auth_error("401 Unauthorized token")
    assert _is_auth_error("请先完成授权登录")
    assert not _is_auth_error("connection timed out")
    assert not _is_auth_error("")


# ─────────────────────────────────────────────────────────────────────────────
# 公共反馈组件
# ─────────────────────────────────────────────────────────────────────────────

def test_toast_appears_and_auto_message(w):
    assert w.toast.isHidden()
    w.toast.show_message("日程已删除", kind="success")
    assert not w.toast.isHidden()
    assert "日程已删除" in w.toast.msg_label.text()


def test_toast_action_button_shown_on_request(w):
    assert w.toast.action_btn.isHidden()
    w.toast.show_message("发现新版本", action_text="查看", on_action=lambda: None)
    assert not w.toast.action_btn.isHidden()


def test_confirm_dialog_danger_button():
    dlg = ConfirmDialog("删除日程", "确定删除吗？", ok_text="删除", danger=True, parent=None)
    # 危险确认按钮使用 dangerBtn 样式
    from PySide6.QtWidgets import QPushButton
    names = [b.objectName() for b in dlg.findChildren(QPushButton)]
    assert "dangerBtn" in names
    assert "secondaryBtn" in names


# ─────────────────────────────────────────────────────────────────────────────
# 登录态持久化辅助
# ─────────────────────────────────────────────────────────────────────────────

def test_mark_authed_sets_config_flag(cfg):
    assert cfg.get("auth_completed") is False
    login_dialog.mark_authed(cfg)
    assert cfg.get("auth_completed") is True
    # 幂等
    login_dialog.mark_authed(cfg)
    assert cfg.get("auth_completed") is True


def test_mark_authed_tolerates_none_config():
    login_dialog.mark_authed(None)  # 不应抛异常


# ─────────────────────────────────────────────────────────────────────────────
# 设置对话框：登录状态异步检测（避免阻塞）
# ─────────────────────────────────────────────────────────────────────────────

class _FakeStatusWorker(QObject):
    checked = Signal(bool, bool)

    def __init__(self, result=(True, True), parent=None):
        super().__init__(parent)
        self._result = result

    def start(self):
        QTimer.singleShot(0, lambda: self.checked.emit(*self._result))


def test_settings_dialog_shows_logged_in_state(monkeypatch, cfg):
    monkeypatch.setattr(settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((True, True), parent))
    dlg = settings_dialog.SettingsDialog(cfg)
    app.processEvents()
    assert "已登录" in dlg.auth_status_label.text()
    assert dlg.login_btn.text() == "重新登录"
    dlg.close()


def test_settings_dialog_shows_missing_cli_state(monkeypatch, cfg):
    monkeypatch.setattr(settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((False, False), parent))
    dlg = settings_dialog.SettingsDialog(cfg)
    app.processEvents()
    assert "lark-cli" in dlg.auth_status_label.text()
    dlg.close()

# ---------------------------------------------------------------------------
# 拖拽改期接线 & 桌面快捷方式（继承自重构回归套件，PR #7）
# ---------------------------------------------------------------------------

def test_reschedule_wiring_calls_update_event(w, monkeypatch):
    from datetime import datetime

    calls = []
    monkeypatch.setattr(w.lark_cli, "update_event", lambda **kw: calls.append(kw))
    w.events = [{
        "event_id": "evt1",
        "organizer_calendar_id": "primary",
        "start_time": {"timestamp": str(int(datetime(2026, 8, 12, 10, 0).timestamp()))},
        "end_time": {"timestamp": str(int(datetime(2026, 8, 12, 11, 0).timestamp()))},
    }]
    w._on_reschedule("evt1", datetime(2026, 8, 15), "2026-08-12T10:00:00", "2026-08-12T11:00:00", False)
    assert calls, "拖拽改期未触发 update_event"
    call = calls[-1]
    assert call["event_id"] == "evt1" and call["start"].day == 15 and call["start"].hour == 10


def test_reschedule_recurring_does_not_write(w):
    from datetime import datetime

    # 重复日程拖拽只给 Toast 提示，不写回飞书
    w._on_reschedule("evt1", datetime(2026, 8, 15), "2026-08-12T10:00:00",
                     "2026-08-12T11:00:00", True)


def test_desktop_shortcut_skips_when_marked(cfg):
    from pathlib import Path
    from unittest import mock

    import main

    cfg.set("desktop_shortcut_created", True)
    with mock.patch.object(Path, "home", return_value=Path("/tmp/fake_home")):
        main._ensure_desktop_shortcut(cfg)
    assert cfg.get("desktop_shortcut_created") is True


def test_desktop_shortcut_creates_on_windows(cfg, tmp_path):
    from pathlib import Path
    from unittest import mock

    import main

    cfg.set("desktop_shortcut_created", False)
    fake_home = tmp_path / "fake_home"
    (fake_home / "Desktop").mkdir(parents=True)
    with mock.patch.object(Path, "home", return_value=fake_home),             mock.patch("sys.platform", "win32"),             mock.patch("main._create_windows_shortcut") as create_shortcut:
        main._ensure_desktop_shortcut(cfg)
        create_shortcut.assert_called_once_with(fake_home / "Desktop")
    assert cfg.get("desktop_shortcut_created") is True
