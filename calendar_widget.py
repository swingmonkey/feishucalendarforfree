"""Main desktop calendar widget - borderless, always-on-top, month grid view."""

import calendar as cal_module
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
    QDialog,
)
from PySide6.QtCore import Qt, QTimer, QPoint, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QPen, QFont

from lark_cli_async import LarkCliAsync
from event_card import EventCard, parse_event_time, is_all_day_event
from add_event_dialog import AddEventDialog
from event_detail_dialog import EventDetailDialog
from settings_dialog import SettingsDialog
from export_dialog import ExportDialog
from config import Config
from styles import get_theme

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]
MAX_VISIBLE_EVENTS = 3  # Max events shown per day cell before "+N more"


class DateCircleLabel(QLabel):
    """A QLabel that draws a circle around the text (for today's date)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self._circle_color = QColor("#4B3FE3")
        self._circle_radius = 10

    def set_circle_color(self, color: str):
        self._circle_color = QColor(color)
        self.update()

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw circle
        cx = self.width() // 2
        cy = self.height() // 2
        radius = min(self._circle_radius, self.height() // 2 - 1)

        # Filled circle background
        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        # Draw text on top (white for contrast)
        painter.setPen(QColor("#ffffff"))
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()


class ClickableLabel(QLabel):
    """A QLabel that emits a clicked signal."""
    clicked = Signal()

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(ev)


class GridEventLabel(QFrame):
    """Compact clickable event label for the calendar grid."""

    clicked = Signal(dict)

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        # Don't use self.event — it shadows QObject.event()
        self.event_data = event
        self.setObjectName("gridEvent")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 0, 3, 0)
        layout.setSpacing(2)

        all_day = is_all_day_event(self.event_data)
        start = parse_event_time(self.event_data.get("start_time", {}))

        if all_day:
            time_text = "全天"
        else:
            time_text = start.strftime("%H:%M")

        time_lbl = QLabel(time_text)
        time_lbl.setObjectName("gridEventTime")
        layout.addWidget(time_lbl)

        summary = self.event_data.get("summary", "(无标题)")
        if not isinstance(summary, str):
            summary = str(summary)
        title_lbl = QLabel(summary)
        title_lbl.setObjectName("gridEventTitle")
        layout.addWidget(title_lbl, 1)

        self.setToolTip(f"{time_text}  {summary}")

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(ev)


class DayCell(QFrame):
    """A single day cell in the calendar grid."""

    event_clicked = Signal(dict)
    more_clicked = Signal(datetime)

    def __init__(self, date: datetime, events: list, is_current_month: bool, parent=None):
        super().__init__(parent)
        self.cell_date = date
        self._events = events
        self._is_current_month = is_current_month
        self._is_today = date.date() == datetime.now().date()
        self._setup_ui()

    def _setup_ui(self):
        if self._is_today:
            self.setObjectName("dayCellToday")
        elif not self._is_current_month:
            self.setObjectName("dayCellOther")
        else:
            self.setObjectName("dayCell")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

        # Date number
        if self._is_today:
            date_lbl = DateCircleLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNumToday")
        elif not self._is_current_month:
            date_lbl = QLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNumOther")
        else:
            date_lbl = QLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNum")
        date_lbl.setFixedHeight(18)
        layout.addWidget(date_lbl)

        # Event labels (up to MAX_VISIBLE_EVENTS)
        visible = self._events[:MAX_VISIBLE_EVENTS]
        remaining = len(self._events) - MAX_VISIBLE_EVENTS

        for ev in visible:
            lbl = GridEventLabel(ev)
            lbl.clicked.connect(self._on_event_clicked)
            layout.addWidget(lbl)

        # "+N more" label
        if remaining > 0:
            more_lbl = ClickableLabel(f"+{remaining}更多")
            more_lbl.setObjectName("moreLabel")
            more_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            more_lbl.clicked.connect(lambda: self.more_clicked.emit(self.cell_date))
            layout.addWidget(more_lbl)

        layout.addStretch()

    def _on_event_clicked(self, event: dict):
        self.event_clicked.emit(event)


class DayDetailDialog(QDialog):
    """Dialog showing all events for a specific day."""

    event_delete_requested = Signal(dict)

    def __init__(self, date: datetime, events: list, parent=None):
        super().__init__(parent)
        self.cell_date = date
        self._events = events
        self.setWindowTitle("当日日程")
        self.setFixedSize(360, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Date title
        wd = WEEKDAY_NAMES[self.cell_date.weekday()]
        date_str = self.cell_date.strftime("%Y年%m月%d日")
        is_today = self.cell_date.date() == datetime.now().date()

        title_text = f"{date_str}  周{wd}"
        if is_today:
            title_text = f"● 今天  {date_str}  周{wd}"

        title = QLabel(title_text)
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        count_lbl = QLabel(f"共 {len(self._events)} 项日程")
        count_lbl.setObjectName("detailLabel")
        layout.addWidget(count_lbl)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(115, 115, 115, 0.18); background-color: rgba(115, 115, 115, 0.18); max-height: 1px;")
        layout.addWidget(sep)

        if not self._events:
            empty = QLabel("当天没有日程安排")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            container = QWidget()
            vlay = QVBoxLayout(container)
            vlay.setContentsMargins(0, 0, 0, 0)
            vlay.setSpacing(6)

            for ev in self._events:
                card = EventCard(ev)
                card.clicked.connect(self._show_event_detail)
                card.delete_clicked.connect(self._on_card_delete)
                vlay.addWidget(card)

            vlay.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll, 1)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _show_event_detail(self, event: dict):
        dialog = EventDetailDialog(event, self)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.exec()

    def _on_card_delete(self, event: dict):
        self.event_delete_requested.emit(event)
        self.accept()


class CalendarWidget(QMainWindow):
    """Borderless, always-on-top desktop calendar with month grid view."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        # Choose API backend: FeishuApiAsync if app credentials configured, else lark-cli
        app_id = config.get("app_id", "")
        app_secret = config.get("app_secret", "")
        if app_id and app_secret:
            from feishu_api import FeishuApiAsync
            self.lark_cli = FeishuApiAsync(config, self)
        else:
            self.lark_cli = LarkCliAsync(config, self)
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.events: list[dict] = []
        self._drag_offset: QPoint | None = None
        self._pinned = self.config.get("pin_to_top", True)

        # Connect async signals
        self.lark_cli.agenda_fetched.connect(self._on_events_fetched)
        self.lark_cli.fetch_error.connect(self._on_fetch_error)
        self.lark_cli.event_deleted.connect(self._on_deleted)
        self.lark_cli.delete_error.connect(self._on_delete_error)

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._setup_timer()
        self._resize_grip_size = 16  # pixels from bottom-right corner for resize grip
        self.refresh_events()

    def _setup_window(self):
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        # Resizable window with minimum size
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
        layout.addWidget(self._build_weekday_header())

        # Calendar grid
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(2)
        layout.addWidget(self.grid_container, 1)

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setContentsMargins(0, 4, 0, 6)
        layout.addWidget(self.status_label)

        # Resize grip indicator (bottom-right corner)
        self.resize_grip = QLabel("⇲")
        self.resize_grip.setObjectName("resizeGrip")
        self.resize_grip.setFixedSize(16, 16)
        self.resize_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 4, 2)
        grip_layout.addStretch()
        grip_layout.addWidget(self.resize_grip)
        layout.addLayout(grip_layout)

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

        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("iconBtn")
        self.add_btn.setToolTip("添加日程")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_event)
        h.addWidget(self.add_btn)

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
        prev_btn.setToolTip("上个月")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(lambda: self._change_month(-1))
        h.addWidget(prev_btn)

        self.date_label = QLabel()
        self.date_label.setObjectName("headerDate")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self.date_label, 1)

        next_btn = QPushButton("›")
        next_btn.setObjectName("iconBtn")
        next_btn.setToolTip("下个月")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(lambda: self._change_month(1))
        h.addWidget(next_btn)

        today_btn = QPushButton("今天")
        today_btn.setObjectName("iconBtn")
        today_btn.setToolTip("回到本月")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.setFixedWidth(44)
        today_btn.clicked.connect(self._go_today)
        h.addWidget(today_btn)

        self._update_month_label()
        return bar

    def _build_weekday_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(24)
        h = QHBoxLayout(header)
        h.setContentsMargins(4, 0, 4, 0)
        h.setSpacing(2)

        for i, name in enumerate(WEEKDAY_NAMES):
            lbl = QLabel(name)
            if i >= 5:
                lbl.setObjectName("weekDayWeekend")
            else:
                lbl.setObjectName("weekDay")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            h.addWidget(lbl, 1)

        return header

    def _update_month_label(self):
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        is_current_month = (
            self.current_date.year == today.year and self.current_date.month == today.month
        )
        month_str = self.current_date.strftime("%Y年%m月")
        if is_current_month:
            label = f"本月  {month_str}"
        else:
            label = month_str
        self.date_label.setText(label)

    def _change_month(self, delta: int):
        if delta > 0:
            if self.current_date.month == 12:
                self.current_date = self.current_date.replace(
                    year=self.current_date.year + 1, month=1
                )
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month + 1)
        else:
            if self.current_date.month == 1:
                self.current_date = self.current_date.replace(
                    year=self.current_date.year - 1, month=12
                )
            else:
                self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        self._update_month_label()
        self.refresh_events()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._update_month_label()
        self.refresh_events()

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
        # Apply new opacity
        self.setWindowOpacity(float(self.config.get("opacity", 0.95)))
        # Apply new refresh interval
        self.refresh_timer.setInterval(self.config.get("auto_refresh_interval", 300) * 1000)
        # Rebuild API client if credentials changed
        app_id = self.config.get("app_id", "")
        app_secret = self.config.get("app_secret", "")
        was_feishu_api = isinstance(self.lark_cli, FeishuApiAsync) if 'FeishuApiAsync' in dir() else False
        should_use_feishu_api = bool(app_id and app_secret)
        if was_feishu_api != should_use_feishu_api:
            # Disconnect old signals
            try:
                self.lark_cli.agenda_fetched.disconnect()
                self.lark_cli.fetch_error.disconnect()
                self.lark_cli.event_deleted.disconnect()
                self.lark_cli.delete_error.disconnect()
            except RuntimeError:
                pass
            if should_use_feishu_api:
                from feishu_api import FeishuApiAsync
                self.lark_cli = FeishuApiAsync(self.config, self)
            else:
                self.lark_cli = LarkCliAsync(self.config, self)
            self.lark_cli.agenda_fetched.connect(self._on_events_fetched)
            self.lark_cli.fetch_error.connect(self._on_fetch_error)
            self.lark_cli.event_deleted.connect(self._on_deleted)
            self.lark_cli.delete_error.connect(self._on_delete_error)
        # Refresh events (in case app credentials changed)
        self.refresh_events()

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start(self.config.get("auto_refresh_interval", 300) * 1000)

    def refresh_events(self):
        self.status_label.setText("正在获取日程...")
        self.refresh_btn.setEnabled(False)
        self.lark_cli.fetch_agenda(self.current_date, monthly=True)

    def _on_events_fetched(self, events: list):
        self.events = events
        self._render_grid()
        count = len(events)
        if count == 0:
            self.status_label.setText("本月无日程")
        else:
            self.status_label.setText(
                f"共 {count} 项日程  |  更新于 {datetime.now().strftime('%H:%M')}"
            )
        self.refresh_btn.setEnabled(True)

    def _on_fetch_error(self, error_msg: str):
        self.status_label.setText("获取失败")
        self.refresh_btn.setEnabled(True)
        self._clear_grid()
        lbl = QLabel(f"获取日程失败\n\n{error_msg}")
        lbl.setObjectName("emptyLabel")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setWordWrap(True)
        self.grid_layout.addWidget(lbl, 0, 0, 1, 7)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _render_grid(self):
        self._clear_grid()

        # Group events by date string
        events_by_date: dict[str, list[dict]] = {}
        for ev in self.events:
            start = parse_event_time(ev.get("start_time", {}))
            date_key = start.strftime("%Y-%m-%d")
            if date_key not in events_by_date:
                events_by_date[date_key] = []
            events_by_date[date_key].append(ev)

        # Build calendar grid using Python's calendar module
        cal = cal_module.Calendar(firstweekday=0)  # Monday = 0
        weeks = cal.monthdatescalendar(self.current_date.year, self.current_date.month)

        for row, week in enumerate(weeks):
            for col, date_obj in enumerate(week):
                date_key = date_obj.strftime("%Y-%m-%d")
                day_events = events_by_date.get(date_key, [])
                is_current_month = date_obj.month == self.current_date.month

                cell = DayCell(
                    date=datetime(date_obj.year, date_obj.month, date_obj.day),
                    events=day_events,
                    is_current_month=is_current_month,
                )
                cell.event_clicked.connect(self._show_event_detail)
                cell.more_clicked.connect(self._show_day_detail)
                self.grid_layout.addWidget(cell, row, col)

        # Equal-sized rows and columns
        for row in range(len(weeks)):
            self.grid_layout.setRowStretch(row, 1)
        for col in range(7):
            self.grid_layout.setColumnStretch(col, 1)

    def _show_event_detail(self, event: dict):
        EventDetailDialog(event, self).exec()

    def _show_day_detail(self, date: datetime):
        date_key = date.strftime("%Y-%m-%d")
        day_events = [
            e for e in self.events
            if parse_event_time(e.get("start_time", {})).strftime("%Y-%m-%d") == date_key
        ]
        dialog = DayDetailDialog(date, day_events, self)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.exec()

    def _on_add_event(self):
        dialog = AddEventDialog(self.lark_cli, self)
        dialog.event_created.connect(lambda: self.refresh_events())
        dialog.exec()

    def _on_export(self):
        if not self.events:
            QMessageBox.information(self, "提示", "当前没有日程可导出")
            return
        dialog = ExportDialog(self.events, self.current_date, self)
        dialog.exec()

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

    # --- Window dragging & resizing ---
    def _is_in_resize_grip(self, pos) -> bool:
        """Check if position is in the bottom-right resize grip area."""
        rect = self.rect()
        return (
            pos.x() >= rect.width() - self._resize_grip_size
            and pos.y() >= rect.height() - self._resize_grip_size
        )

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            pos = ev.position()
            if self._is_in_resize_grip(pos):
                # Start resizing
                self._resize_start = ev.globalPosition().toPoint()
                self._resize_start_size = self.size()
                self._resizing = True
                ev.accept()
                return
            if pos.y() <= 76:
                self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
                ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if getattr(self, '_resizing', False) and ev.buttons() & Qt.MouseButton.LeftButton:
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
        if getattr(self, '_resizing', False):
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
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())

    def closeEvent(self, ev):
        pos = self.pos()
        self.config.set("window_x", pos.x())
        self.config.set("window_y", pos.y())
        super().closeEvent(ev)
