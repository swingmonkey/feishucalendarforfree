"""Shared calendar widgets: date badge, clickable label, compact grid event
label (drag source) and the day cell (drop target for drag-to-reschedule).

Extracted from the old ``calendar_widget.py`` so the month and week views can
share identical building blocks, mirroring weektodo's component approach.
"""

import json
from datetime import datetime

from PySide6.QtCore import Qt, QMimeData, QPoint, QByteArray, Signal, QSize, QEvent
from PySide6.QtGui import QMouseEvent, QDrag, QPainter, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QApplication,
    QWidget,
    QSizePolicy,
)

from models_event import parse_event_time, is_all_day_event, has_recurrence, get_event_color
from config import Config

# MIME type used to carry a dragged event between cells / week columns.
EVENT_MIME = "application/x-feishu-event"

# Max events shown per day cell before the "+N more" affordance.
MAX_VISIBLE_EVENTS = 3


def build_event_mime(event: dict) -> QMimeData:
    """Build QMimeData carrying the minimal info needed to reschedule ``event``."""
    start = parse_event_time(event.get("start_time", {}))
    end = parse_event_time(event.get("end_time", {}))
    payload = {
        "event_id": event.get("event_id", ""),
        "calendar_id": event.get("organizer_calendar_id", "primary")
        or event.get("calendar_id", "primary"),
        "summary": event.get("summary", ""),
        "start_iso": start.isoformat(),
        "end_iso": end.isoformat(),
        "is_recurring": bool(event.get("_is_recurring_instance") or has_recurrence(event)),
    }
    mime = QMimeData()
    mime.setData(EVENT_MIME, QByteArray(json.dumps(payload).encode("utf-8")))
    mime.setText(event.get("summary", ""))
    return mime


def parse_event_mime(mime) -> dict | None:
    """Parse a dropped ``EVENT_MIME`` payload, or ``None`` if absent."""
    raw = bytes(mime.data(EVENT_MIME))
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


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

        cx = self.width() // 2
        cy = self.height() // 2
        radius = min(self._circle_radius, self.height() // 2 - 1)

        painter.setBrush(self._circle_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

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
    """Compact clickable event label for the calendar grid (drag source)."""

    clicked = Signal(dict)

    def __init__(self, event: dict, is_continuation: bool = False, config: Config = None, parent=None):
        super().__init__(parent)
        # Don't use self.event — it shadows QObject.event()
        self.event_data = event
        self._is_continuation = is_continuation
        self._press_pos: QPoint | None = None
        self._dragging = False
        if is_continuation:
            self.setObjectName("gridEventMultiDay")
        else:
            self.setObjectName("gridEvent")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # 关键：事件标签不贡献水平最小宽度，否则长标题会把所在列撑宽，
        # 导致网格列宽不均、与表头星期错位。
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._setup_ui()
        self._apply_color(config)

    def _apply_color(self, config):
        color = get_event_color(config, self.event_data.get("event_id", ""))
        if color:
            self.setStyleSheet(f"border-left: 2px solid {color};")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 0, 3, 0)
        layout.setSpacing(2)

        all_day = is_all_day_event(self.event_data)
        start = parse_event_time(self.event_data.get("start_time", {}))
        recurring = bool(self.event_data.get("_is_recurring_instance") or has_recurrence(self.event_data))

        if self._is_continuation:
            time_text = "↳"
        elif all_day:
            time_text = "全天"
        else:
            time_text = start.strftime("%H:%M")
        if recurring:
            time_text = "♻ " + time_text

        time_lbl = QLabel(time_text)
        time_lbl.setObjectName("gridEventTime")
        layout.addWidget(time_lbl)

        summary = self.event_data.get("summary", "(无标题)")
        if not isinstance(summary, str):
            summary = str(summary)
        title_lbl = QLabel(summary)
        title_lbl.setObjectName("gridEventTitle")
        layout.addWidget(title_lbl, 1)

        if self._is_continuation:
            self.setToolTip(f"↳ 继续: {summary}")
        else:
            self.setToolTip(f"{time_text}  {summary}")

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._press_pos = ev.position().toPoint()
            self._dragging = False
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if (
            self._press_pos is not None
            and ev.buttons() & Qt.MouseButton.LeftButton
            and not self._dragging
        ):
            if (ev.position().toPoint() - self._press_pos).manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
                self._start_drag()
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self.clicked.emit(self.event_data)
        self._press_pos = None
        super().mouseReleaseEvent(ev)

    def _start_drag(self):
        recurring = bool(self.event_data.get("_is_recurring_instance") or has_recurrence(self.event_data))
        if recurring:
            return  # 重复日程暂不支持拖拽改期（会改动整个序列）
        drag = QDrag(self)
        drag.setMimeData(build_event_mime(self.event_data))
        drag.exec(Qt.DropAction.MoveAction)


class DayCell(QFrame):
    """A single day cell in the calendar grid (drop target for reschedule)."""

    event_clicked = Signal(dict)
    more_clicked = Signal(datetime)
    add_clicked = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)

    def __init__(self, date: datetime, events: list, is_current_month: bool, config: Config = None, parent=None):
        super().__init__(parent)
        self.cell_date = date
        # events: list of (event_dict, is_continuation) tuples
        self._events = events
        self._is_current_month = is_current_month
        self._is_today = date.date() == datetime.now().date()
        self._config = config
        self._original_object_name = ""
        # 单元格同样不贡献水平最小宽度，保证 7 列严格等宽（与表头对齐）
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setAcceptDrops(True)
        self._setup_ui()
        self.setMouseTracking(True)

    def _setup_ui(self):
        if self._is_today:
            self.setObjectName("dayCellToday")
        elif not self._is_current_month:
            self.setObjectName("dayCellOther")
        else:
            self.setObjectName("dayCell")
        self._original_object_name = self.objectName()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)

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

        visible = self._events[:MAX_VISIBLE_EVENTS]
        remaining = len(self._events) - MAX_VISIBLE_EVENTS

        for item in visible:
            if isinstance(item, tuple):
                ev, is_cont = item
            else:
                ev, is_cont = item, False
            lbl = GridEventLabel(ev, is_continuation=is_cont, config=self._config)
            lbl.clicked.connect(self._on_event_clicked)
            layout.addWidget(lbl)

        if remaining > 0:
            more_lbl = ClickableLabel(f"+{remaining}更多")
            more_lbl.setObjectName("moreLabel")
            more_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            more_lbl.clicked.connect(lambda: self.more_clicked.emit(self.cell_date))
            layout.addWidget(more_lbl)

        layout.addStretch()

    def _on_event_clicked(self, event: dict):
        self.event_clicked.emit(event)

    # ── Drag & drop (reschedule) ──

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
        else:
            super().dragEnterEvent(ev)

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
        else:
            super().dragMoveEvent(ev)

    def dropEvent(self, ev):
        payload = parse_event_mime(ev.mimeData())
        if payload:
            ev.acceptProposedAction()
            self.reschedule_requested.emit(
                payload["event_id"],
                self.cell_date,
                payload["start_iso"],
                payload["end_iso"],
                payload.get("is_recurring", False),
            )
        else:
            super().dropEvent(ev)

    def mousePressEvent(self, ev):
        """Click on empty area of the cell to add event for this date."""
        if ev.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(ev.position().toPoint())
            if child is None:
                self.add_clicked.emit(self.cell_date)
        super().mousePressEvent(ev)

    def enterEvent(self, ev):
        """Highlight cell on hover."""
        self.setObjectName(self._original_object_name + "Hover")
        self.setStyle(self.style())
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        """Restore cell appearance when mouse leaves."""
        self.setObjectName(self._original_object_name)
        self.setStyle(self.style())
        super().leaveEvent(ev)
