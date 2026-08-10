"""Main application window — refactored from the old ``CalendarWidget``.

This is the orchestrator. It owns the toolbar (with the month/week toggle),
the active calendar view (``MonthView`` or ``WeekView``), and all the
cross-cutting logic that used to live inside the monolithic ``CalendarWidget``:
refresh, auth-retry, settings, export, search, add/delete, theme, pin,
window drag/resize and geometry persistence.

Crucially, it does **not** touch the Feishu read/write layer
(``lark_cli.py`` / ``lark_cli_async.py``). Drag-to-reschedule simply calls the
existing ``LarkCliAsync.update_event`` — the same method the edit dialog uses.
"""

import calendar as cal_module
from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QMouseEvent

from lark_cli_async import LarkCliAsync
from month_view import MonthView
from week_view import WeekView
from day_detail_dialog import DayDetailDialog
from event_detail_dialog import EventDetailDialog
from add_event_dialog import AddEventDialog
from settings_dialog import SettingsDialog
from export_dialog import ExportDialog
from search_dialog import SearchDialog
from config import Config
from styles import get_theme

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


class MainWindow(QMainWindow):
    """Borderless, always-on-top desktop calendar with month/week views."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.lark_cli = LarkCliAsync(config, self)
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.events: list[dict] = []
        self._view_mode = self.config.get("view_mode", "month")
        if self._view_mode not in ("month", "week"):
            self._view_mode = "month"
        self._drag_offset: QPoint | None = None
        self._pinned = self.config.get("pin_to_top", True)

        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.setInterval(250)
        self._geometry_save_timer.timeout.connect(self._persist_geometry)

        # Connect async signals
        self.lark_cli.agenda_fetched.connect(self._on_events_fetched)
        self.lark_cli.fetch_error.connect(self._on_fetch_error)
        self.lark_cli.event_deleted.connect(self._on_deleted)
        self.lark_cli.delete_error.connect(self._on_delete_error)
        self.lark_cli.event_updated.connect(self._on_event_updated)
        self.lark_cli.update_error.connect(self._on_update_error)

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._setup_timer()
        self._resize_grip_size = 16
        self.refresh_events()

    # ── Window setup ──

    def _setup_window(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        w = self.config.get("window_width", 440)
        h = self.config.get("window_height", 640)
        self.setMinimumSize(360, 480)
        self.resize(w, h)
        self.move(self.config.get("window_x", 100), self.config.get("window_y", 100))
        self.setWindowOpacity(float(self.config.get("opacity", 0.95)))

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_month_bar())

        # Views
        self.month_view = MonthView(self.config, self)
        self.week_view = WeekView(self.config, self)
        for view in (self.month_view, self.week_view):
            view.event_clicked.connect(self._show_event_detail)
            view.add_event_for_date.connect(self._on_add_event_for_date)
            view.reschedule_requested.connect(self._on_reschedule)
        self.month_view.day_activated.connect(self._show_day_detail)
        self.week_view.event_delete_requested.connect(self._confirm_delete)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.month_view)
        self.stack.addWidget(self.week_view)
        layout.addWidget(self.stack, 1)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setContentsMargins(0, 4, 0, 6)
        layout.addWidget(self.status_label)

        self.resize_grip = QLabel("⇲")
        self.resize_grip.setObjectName("resizeGrip")
        self.resize_grip.setFixedSize(16, 16)
        self.resize_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 4, 2)
        grip_layout.addStretch()
        grip_layout.addWidget(self.resize_grip)
        layout.addLayout(grip_layout)

        self._apply_view_mode()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(44)
        h = QHBoxLayout(header)
        h.setContentsMargins(12, 4, 8, 4)
        h.setSpacing(4)

        title = QLabel("飞书日程")
        title.setObjectName("headerTitle")
        h.addWidget(title)
        h.addStretch()

        # Month / Week toggle
        self.month_toggle = QPushButton("月")
        self.month_toggle.setObjectName("toggleBtn")
        self.month_toggle.setToolTip("月视图")
        self.month_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_toggle.clicked.connect(lambda: self._set_view_mode("month"))
        h.addWidget(self.month_toggle)

        self.week_toggle = QPushButton("周")
        self.week_toggle.setObjectName("toggleBtn")
        self.week_toggle.setToolTip("周视图（weektodo 风格）")
        self.week_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.week_toggle.clicked.connect(lambda: self._set_view_mode("week"))
        h.addWidget(self.week_toggle)

        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("iconBtn")
        self.add_btn.setToolTip("添加日程")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_event)
        h.addWidget(self.add_btn)

        self.search_btn = QPushButton("🔍")
        self.search_btn.setObjectName("iconBtn")
        self.search_btn.setToolTip("搜索日程")
        self.search_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_btn.clicked.connect(self._on_search)
        h.addWidget(self.search_btn)

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setObjectName("iconBtn")
        self.refresh_btn.setToolTip("刷新")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_events)
        h.addWidget(self.refresh_btn)

        self.export_btn = QPushButton("📤")
        self.export_btn.setObjectName("iconBtn")
        self.export_btn.setToolTip("导出日程到 Excel")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.clicked.connect(self._on_export)
        h.addWidget(self.export_btn)

        self.pin_btn = QPushButton("📌" if self._pinned else "📍")
        self.pin_btn.setObjectName("iconBtn")
        self.pin_btn.setToolTip("置顶" if self._pinned else "取消置顶")
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.clicked.connect(self._toggle_pin)
        h.addWidget(self.pin_btn)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("iconBtn")
        self.settings_btn.setToolTip("设置")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._on_settings)
        h.addWidget(self.settings_btn)

        self.theme_btn = QPushButton("◐")
        self.theme_btn.setObjectName("iconBtn")
        self.theme_btn.setToolTip("切换主题")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._toggle_theme)
        h.addWidget(self.theme_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("iconBtn")
        close_btn.setToolTip("隐藏到托盘")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        h.addWidget(close_btn)
        return header

    def _build_month_bar(self) -> QWidget:
        bar = QFrame()
        bar.setFixedHeight(32)
        h = QHBoxLayout(bar)
        h.setContentsMargins(8, 2, 8, 2)
        h.setSpacing(4)

        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("iconBtn")
        prev_btn.setToolTip("上一个")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(lambda: self._change_period(-1))
        h.addWidget(prev_btn)

        self.date_label = QLabel()
        self.date_label.setObjectName("headerDate")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self.date_label, 1)

        next_btn = QPushButton("›")
        next_btn.setObjectName("iconBtn")
        next_btn.setToolTip("下一个")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(lambda: self._change_period(1))
        h.addWidget(next_btn)

        today_btn = QPushButton("今天")
        today_btn.setObjectName("iconBtn")
        today_btn.setToolTip("回到今天")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setFixedWidth(44)
        today_btn.clicked.connect(self._go_today)
        h.addWidget(today_btn)

        self._update_period_label()
        return bar

    # ── View mode ──

    def _set_view_mode(self, mode: str):
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self.config.set("view_mode", mode)
        self._apply_view_mode()
        self._render_active_view()

    def _apply_view_mode(self):
        self.month_toggle.setObjectName("toggleBtnActive" if self._view_mode == "month" else "toggleBtn")
        self.week_toggle.setObjectName("toggleBtnActive" if self._view_mode == "week" else "toggleBtn")
        self.month_toggle.setStyle(self.month_toggle.style())
        self.week_toggle.setStyle(self.week_toggle.style())
        self.stack.setCurrentIndex(0 if self._view_mode == "month" else 1)
        self._update_period_label()

    def _active_view(self):
        return self.month_view if self._view_mode == "month" else self.week_view

    def _render_active_view(self):
        self._active_view().set_events(self.events, self.current_date)

    # ── Period navigation ──

    def _change_period(self, delta: int):
        if self._view_mode == "month":
            if delta > 0:
                if self.current_date.month == 12:
                    self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month + 1)
            else:
                if self.current_date.month == 1:
                    self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        else:  # week
            self.current_date += timedelta(weeks=delta)
        self._update_period_label()
        self.refresh_events()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._update_period_label()
        self.refresh_events()

    def _update_period_label(self):
        if self._view_mode == "month":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            is_current = self.current_date.year == today.year and self.current_date.month == today.month
            month_str = self.current_date.strftime("%Y年%m月")
            self.date_label.setText("本月  " + month_str if is_current else month_str)
        else:
            monday = self.current_date - timedelta(days=self.current_date.weekday())
            sunday = monday + timedelta(days=6)
            self.date_label.setText(f"{monday.strftime('%m/%d')} - {sunday.strftime('%m/%d')}")

    # ── Theme / pin / settings ──

    def _apply_theme(self):
        self.setStyleSheet(get_theme(self.config.get("theme", "dark")))

    def _toggle_theme(self):
        cur = self.config.get("theme", "dark")
        self.config.set("theme", "light" if cur == "dark" else "dark")
        self._apply_theme()

    def _toggle_pin(self):
        self._pinned = not self._pinned
        self.config.set("pin_to_top", self._pinned)
        if self._pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            self.pin_btn.setText("📌")
            self.pin_btn.setToolTip("取消置顶")
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
            self.pin_btn.setText("📍")
            self.pin_btn.setToolTip("置顶")
        self.show()

    def _on_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        self.setWindowOpacity(float(self.config.get("opacity", 0.95)))
        self.refresh_timer.setInterval(self.config.get("auto_refresh_interval", 300) * 1000)
        self.refresh_events()

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start(self.config.get("auto_refresh_interval", 300) * 1000)

    # ── Refresh / fetch ──

    def refresh_events(self):
        self.status_label.setText("正在获取日程...")
        self.refresh_btn.setEnabled(False)
        self.lark_cli.fetch_agenda(self.current_date, monthly=True)

    def _on_events_fetched(self, events: list):
        self._stop_auth_retry()
        self._clear_error_panel()
        self.events = events
        self._render_active_view()
        count = len(events)
        if count == 0:
            self.status_label.setText("当前范围无日程")
        else:
            self.status_label.setText(f"共 {count} 项日程  |  更新于 {datetime.now().strftime('%H:%M')}")
        self.refresh_btn.setEnabled(True)

    def _on_fetch_error(self, error_msg: str):
        self.status_label.setText("获取失败")
        self.refresh_btn.setEnabled(True)
        self._show_error(error_msg)
        if any(kw in error_msg.lower() for kw in ["scope", "auth", "授权", "login"]):
            if not hasattr(self, "_auth_retry_timer") or not self._auth_retry_timer:
                self._auth_retry_timer = QTimer(self)
                self._auth_retry_timer.timeout.connect(self._on_auth_retry)
            self._auth_retry_count = 0
            self._auth_retry_timer.start(15000)

    def _clear_error_panel(self):
        if getattr(self, "_error_panel", None) is not None:
            self.stack.removeWidget(self._error_panel)
            self._error_panel.deleteLater()
            self._error_panel = None
        # Always make sure the real view is showing after a successful fetch.
        self.stack.setCurrentIndex(0 if self._view_mode == "month" else 1)

    def _show_error(self, error_msg: str):
        # Replace the active view with an error panel until next successful fetch.
        from PySide6.QtWidgets import QTextEdit, QVBoxLayout

        self._clear_error_panel()
        panel = QWidget()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(20, 20, 20, 20)
        pl.setSpacing(12)
        err_widget = QTextEdit()
        err_widget.setReadOnly(True)
        err_widget.setPlainText(f"获取日程失败\n\n{error_msg}")
        err_widget.setObjectName("errorDisplay")
        pl.addWidget(err_widget)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        retry_btn = QPushButton("已授权，重新获取")
        retry_btn.setObjectName("primaryBtn")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self.refresh_events)
        btn_row.addWidget(retry_btn)
        pl.addLayout(btn_row)
        self._error_panel = panel
        self.stack.addWidget(panel)
        self.stack.setCurrentWidget(panel)

    def _on_auth_retry(self):
        self._auth_retry_count = getattr(self, "_auth_retry_count", 0) + 1
        if self._auth_retry_count > 10:
            if hasattr(self, "_auth_retry_timer") and self._auth_retry_timer:
                self._auth_retry_timer.stop()
            return
        self.status_label.setText(f"正在重试获取日程（第 {self._auth_retry_count} 次）...")
        self.refresh_events()

    def _stop_auth_retry(self):
        if hasattr(self, "_auth_retry_timer") and self._auth_retry_timer:
            self._auth_retry_timer.stop()

    # ── Drag to reschedule ──

    def _on_reschedule(self, event_id: str, new_date: datetime, start_iso: str, end_iso: str, is_recurring: bool):
        if is_recurring:
            QMessageBox.information(self, "提示", "重复日程暂不支持拖拽改期（会改动整个序列）。\n可在日程详情中编辑。")
            return
        try:
            start = datetime.fromisoformat(start_iso)
            end = datetime.fromisoformat(end_iso)
        except ValueError:
            return
        duration = end - start
        new_start = datetime(new_date.year, new_date.month, new_date.day, start.hour, start.minute, start.second)
        new_end = new_start + duration
        ev = next((e for e in self.events if e.get("event_id") == event_id), None)
        calendar_id = ev.get("organizer_calendar_id", "primary") if ev else "primary"
        self.status_label.setText("正在改期...")
        self.lark_cli.update_event(
            calendar_id=calendar_id,
            event_id=event_id,
            start=new_start,
            end=new_end,
        )

    def _on_event_updated(self, data: dict):
        self.status_label.setText("已更新")
        self.refresh_events()

    def _on_update_error(self, error_msg: str):
        self.status_label.setText("更新失败")
        QMessageBox.critical(self, "更新失败", error_msg)

    # ── Detail / day dialogs ──

    def _show_event_detail(self, event: dict):
        dialog = EventDetailDialog(event, self.lark_cli, self, config=self.config)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.event_updated.connect(lambda _: self.refresh_events())
        dialog.exec()

    def _show_day_detail(self, date: datetime):
        day_events = self.month_view.events_for_date(date)
        dialog = DayDetailDialog(date, day_events, self.lark_cli, self, config=self.config)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.exec()

    def _on_add_event(self):
        dialog = AddEventDialog(self.lark_cli, self, config=self.config)
        dialog.event_created.connect(lambda: self.refresh_events())
        dialog.exec()

    def _on_add_event_for_date(self, date: datetime):
        dialog = AddEventDialog(self.lark_cli, self, default_date=date, config=self.config)
        dialog.event_created.connect(lambda: self.refresh_events())
        dialog.exec()

    def _on_export(self):
        if not self.events:
            QMessageBox.information(self, "提示", "当前没有日程可导出")
            return
        dialog = ExportDialog(self.events, self.current_date, self)
        dialog.exec()

    def _on_search(self):
        dialog = SearchDialog(self.lark_cli, self)
        dialog.event_selected.connect(self._on_search_result_selected)
        dialog.exec()

    def _on_search_result_selected(self, event: dict):
        start = parse_event_time_compat(event)
        self.current_date = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._update_period_label()
        self.refresh_events()
        self._show_day_detail(start)

    # ── Delete ──

    def _confirm_delete(self, event: dict):
        summary = event.get("summary", "(无标题)")
        reply = QMessageBox.question(
            self, "删除日程", f"确定要删除日程「{summary}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_event(event)

    def _delete_event(self, event: dict):
        self.status_label.setText("正在删除...")
        event_id = event.get("event_id", "")
        calendar_id = event.get("organizer_calendar_id", "primary")
        self.lark_cli.delete_event(calendar_id=calendar_id, event_id=event_id)

    def _on_deleted(self, event_id: str):
        self.status_label.setText("日程已删除")
        self.refresh_events()

    def _on_delete_error(self, error_msg: str):
        self.status_label.setText("删除失败")
        QMessageBox.critical(self, "删除失败", error_msg)

    # ── Window dragging & resizing ──

    def _is_in_resize_grip(self, pos) -> bool:
        rect = self.rect()
        return (
            pos.x() >= rect.width() - self._resize_grip_size
            and pos.y() >= rect.height() - self._resize_grip_size
        )

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            pos = ev.position()
            if self._is_in_resize_grip(pos):
                self._resize_start = ev.globalPosition().toPoint()
                self._resize_start_size = self.size()
                self._resizing = True
                ev.accept()
                return
            if pos.y() <= 76:
                self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
                ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if getattr(self, "_resizing", False) and ev.buttons() & Qt.MouseButton.LeftButton:
            delta = ev.globalPosition().toPoint() - self._resize_start
            new_w = max(self.minimumWidth(), self._resize_start_size.width() + delta.x())
            new_h = max(self.minimumHeight(), self._resize_start_size.height() + delta.y())
            self.resize(new_w, new_h)
            ev.accept()
            return
        if self._drag_offset is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_offset)
            ev.accept()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if getattr(self, "_resizing", False):
            self._resizing = False
            self._save_window_size()
            ev.accept()
            return
        if self._drag_offset is not None:
            self._drag_offset = None
            pos = self.pos()
            self.config.set("window_x", pos.x())
            self.config.set("window_y", pos.y())
            ev.accept()

    def resizeEvent(self, ev):
        self._save_window_size()
        super().resizeEvent(ev)

    def _save_window_size(self):
        self._geometry_save_timer.start()

    def _persist_geometry(self):
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())

    def closeEvent(self, ev):
        pos = self.pos()
        self.config.set("window_x", pos.x())
        self.config.set("window_y", pos.y())
        super().closeEvent(ev)


def parse_event_time_compat(event: dict) -> datetime:
    """Parse an event's start time for navigation (uses models_event helper)."""
    from models_event import parse_event_time

    return parse_event_time(event.get("start_time", {}))
