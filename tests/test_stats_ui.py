"""Stats panel + scheduled export, wired into the window and settings."""

import sys
from datetime import datetime, timedelta

import pytest
from PySide6.QtWidgets import QApplication, QLabel

import event_store
import exporter
from config import Config
from lark_cli_async import LarkCliAsync
from main_window import MainWindow
from settings_dialog import SettingsDialog
from stats_dialog import StatsDialog

app = QApplication.instance() or QApplication(sys.argv[:1])


def _event(event_id, start, minutes=60, summary=None):
    return {
        "event_id": event_id,
        "summary": summary or event_id,
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
    monkeypatch.setattr(LarkCliAsync, "fetch_agenda", lambda self, *a, **kw: None)
    window = MainWindow(cfg, store=store)
    window.refresh_timer.stop()
    window.export_timer.stop()
    yield window
    window.dispose()
    window.deleteLater()
    app.processEvents()


# ── Menu entry ──────────────────────────────────────────────────────────────


def test_more_menu_exposes_statistics(win):
    texts = [action.text() for action in win.more_btn.menu().actions()]
    assert "日程统计" in texts
    # 统计排在搜索之后、Excel 导出之前：先看洞察，再导出
    assert texts.index("日程统计") < texts.index("导出到 Excel")


# ── Stats dialog ────────────────────────────────────────────────────────────


def test_stats_dialog_paints_a_full_month_grid(win, store):
    event_store.upsert_many(
        store,
        [_event("a", datetime(2026, 11, 5, 10), 120), _event("b", datetime(2026, 11, 6, 9), 30)],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    dialog = StatsDialog(store, theme="light", today=datetime(2026, 11, 15))
    try:
        # 7 个星期表头 + 当月天数
        cells = [dialog.grid.itemAt(i).widget() for i in range(dialog.grid.count())]
        numbered = [c for c in cells if c is not None and c.text().isdigit()]
        assert len(numbered) == 30
        assert dialog.month_label.text() == "2026 年 11 月"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_stats_dialog_navigates_months(win, store):
    dialog = StatsDialog(store, today=datetime(2026, 11, 15))
    try:
        dialog._shift_month(1)
        assert dialog.month_label.text() == "2026 年 12 月"
        dialog._shift_month(1)
        assert dialog.month_label.text() == "2027 年 1 月"
        dialog._shift_month(-2)
        assert dialog.month_label.text() == "2026 年 11 月"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def _summary_texts(dialog) -> list[str]:
    texts = []
    for index in range(dialog.summary_layout.count()):
        holder = dialog.summary_layout.itemAt(index).widget()
        texts.extend(label.text() for label in holder.findChildren(QLabel))
    return texts


def test_stats_dialog_shows_peak_load(win, store):
    event_store.upsert_many(
        store,
        [_event("long", datetime(2026, 11, 12, 9), 300, summary="长会")],
        datetime(2026, 11, 1),
        datetime(2026, 11, 30, 23, 59),
    )
    dialog = StatsDialog(store, today=datetime(2026, 11, 15))
    try:
        texts = _summary_texts(dialog)
        assert any("11月12日" in t for t in texts)
        assert any("5 小时" in t for t in texts)
        assert "本月会议时长" in texts
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


# ── Scheduled export ────────────────────────────────────────────────────────


def test_window_runs_due_export_and_reports_it(win, store, tmp_path):
    out = tmp_path / "exports"
    win.config.set("export_dir", str(out))
    win.config.set("export_schedule", "daily")
    win.config.set("export_last_run", "")

    win._run_scheduled_export()

    assert list(out.glob("events-*.json"))
    assert "已导出" in win.status_label.text()
    assert win.config.get("export_last_run")


def test_window_skips_export_when_switched_off(win, store, tmp_path):
    out = tmp_path / "exports"
    win.config.set("export_dir", str(out))
    win.config.set("export_schedule", "off")

    win._run_scheduled_export()

    assert not out.exists()


def test_export_schedule_is_persisted_from_settings(cfg, tmp_path):
    dialog = SettingsDialog(cfg)
    try:
        index = dialog.export_combo.findData("weekly")
        dialog.export_combo.setCurrentIndex(index)
        assert cfg.get("export_schedule") == "weekly"
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_export_directory_is_picked_and_shown(cfg, tmp_path, monkeypatch):
    target = tmp_path / "chosen"
    target.mkdir()
    monkeypatch.setattr(
        "settings_dialog.QFileDialog.getExistingDirectory", lambda *a, **kw: str(target)
    )
    dialog = SettingsDialog(cfg)
    try:
        dialog._on_pick_export_dir()
        assert cfg.get("export_dir") == str(target)
        assert str(target) in dialog.export_dir_label.text()
    finally:
        dialog.close()
        dialog.deleteLater()
        app.processEvents()


def test_is_due_respects_off(tmp_path, cfg):
    cfg.set("export_dir", str(tmp_path))
    cfg.set("export_schedule", "off")
    assert exporter.is_due(cfg, datetime(2026, 11, 3, 9)) is False
