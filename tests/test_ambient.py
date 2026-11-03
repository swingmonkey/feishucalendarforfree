"""Ambient surfaces (tray title / today bar) and the reminder delivery path.

The store and reminder logic have their own tests; this file pins the wiring:
that the window actually publishes a tray summary, that the today bar only
appears when asked for, and that a notification still reaches the user when the
platform has no tray to show it in.
"""

import sys
from datetime import datetime, timedelta

import pytest
from PySide6.QtWidgets import QApplication

import event_store
import main as main_module
import reminder
from config import Config
from lark_cli_async import LarkCliAsync
from main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv[:1])


def _event(event_id, start, summary="评审", minutes=60):
    return {
        "event_id": event_id,
        "summary": summary,
        "organizer_calendar_id": "primary",
        "event_organizer": {"display_name": "张三"},
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {"datetime": (start + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S+08:00")},
    }


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    return Config()


@pytest.fixture
def store(tmp_path):
    conn = event_store.connect(tmp_path / "events.db")
    yield conn
    conn.close()


@pytest.fixture
def win(cfg, store, monkeypatch):
    monkeypatch.setattr(
        LarkCliAsync, "fetch_agenda", lambda self, *a, **kw: None
    )
    window = MainWindow(cfg, store=store)
    window.refresh_timer.stop()
    yield window
    window.dispose()
    window.deleteLater()
    app.processEvents()


# ── Tray summary ────────────────────────────────────────────────────────────


def test_window_publishes_tray_summary_for_today(win, store):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    event_store.upsert_many(
        store,
        [_event("a", today_start.replace(hour=23, minute=45), summary="塔台班前会")],
        today_start,
        today_start + timedelta(days=1),
    )

    received = []
    win.tray_summary_changed.connect(received.append)
    win._refresh_ambient()

    assert received
    assert "今天 1 项" in received[-1]
    assert "塔台班前会" in received[-1]


def test_window_reports_empty_day(win, store):
    received = []
    win.tray_summary_changed.connect(received.append)
    win._refresh_ambient()
    assert received == ["今天没有日程"]


# ── Today bar ───────────────────────────────────────────────────────────────


def test_today_bar_is_not_created_unless_enabled(win):
    assert win._today_bar is None


def test_today_bar_appears_when_enabled(win, store):
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    event_store.upsert_many(
        store,
        [_event("a", day_start.replace(hour=23, minute=45), summary="夜航讲评")],
        day_start,
        day_start + timedelta(days=1),
    )

    win.config.set("today_bar_enabled", True)
    win._apply_today_bar()

    assert win._today_bar is not None
    assert win._today_bar.isVisible()
    assert "夜航讲评" in win._today_bar.primary_label.text()


def test_closing_the_today_bar_switches_the_feature_off(win):
    win.config.set("today_bar_enabled", True)
    win._apply_today_bar()
    win._today_bar._on_close()
    assert win.config.get("today_bar_enabled") is False


def test_today_bar_follows_theme(win):
    win.config.set("theme", "dark")
    win.config.set("today_bar_enabled", True)
    win._apply_today_bar()
    assert "rgba(35, 38, 45" in win._today_bar.card.styleSheet()
    win.config.set("theme", "light")
    win._apply_today_bar()
    assert "rgba(255, 255, 255" in win._today_bar.card.styleSheet()


# ── Notification delivery ───────────────────────────────────────────────────


def test_reminder_from_service_reaches_the_notification_signal(win, store):
    now = datetime.now().replace(microsecond=0)
    event_store.upsert_many(
        store,
        [_event("soon", now + timedelta(minutes=5), summary="起飞前协同")],
        now - timedelta(hours=1),
        now + timedelta(hours=2),
    )

    received = []
    win.notify_requested.connect(lambda title, body: received.append((title, body)))
    win.config.set("reminder_lead_minutes", 10)
    emitted = win.reminder.scan(now)

    assert len(emitted) == 1
    assert received == emitted
    assert "起飞前协同" in received[0][0]


def test_notification_falls_back_to_toast_without_a_tray():
    """No tray (headless / CI) must still surface the reminder in-window."""

    class FakeToast:
        def __init__(self):
            self.messages = []

        def show_message(self, message, **kwargs):
            self.messages.append(message)

    class FakeWidget:
        def __init__(self):
            self.toast = FakeToast()

    class FakeApp:
        def __init__(self):
            self.tray = None
            self.widget = FakeWidget()

    fake = FakeApp()
    main_module.TrayApp._on_notify_requested(fake, "日程提醒", "10:00 · 5 分钟后开始")

    assert fake.widget.toast.messages
    assert "日程提醒" in fake.widget.toast.messages[0]


# ── Config validation for the new keys ──────────────────────────────────────


def test_reminder_settings_are_clamped_and_defaulted():
    clean = Config._validated(
        {
            "reminder_lead_minutes": 999,
            "overload_threshold_hours": 99,
            "quiet_start": "25:99",
            "quiet_end": "7:5",
            "reminder_enabled": "yes",
        }
    )
    assert clean["reminder_lead_minutes"] == 120
    assert clean["overload_threshold_hours"] == 24.0
    assert clean["quiet_start"] == "22:00"     # 非法 → 默认
    assert clean["quiet_end"] == "07:05"       # 合法但格式不规范 → 归一
    assert clean["reminder_enabled"] is True   # 非布尔 → 默认


def test_negative_lead_falls_back_to_default():
    clean = Config._validated({"reminder_lead_minutes": -5})
    assert clean["reminder_lead_minutes"] == 10


def test_today_bar_position_round_trips(tmp_path):
    import config as config_module

    original = config_module.get_app_dir
    config_module.get_app_dir = lambda: tmp_path
    try:
        cfg = Config()
        cfg.set("today_bar_x", 1200)
        cfg.set("today_bar_y", 40)
        assert Config().get("today_bar_x") == 1200
        assert Config().get("today_bar_y") == 40
    finally:
        config_module.get_app_dir = original


def test_quiet_hours_default_window_is_overnight():
    assert reminder.in_quiet_hours(datetime(2026, 11, 3, 23, 0), "22:00", "08:00")
