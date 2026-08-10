"""Event card widget for displaying a single calendar event.

Now supports the weektodo-style enhancements requested in the refactor:
- a left color stripe driven by the local color registry (``config.event_colors``)
- a ♻ badge for recurring events
- drag-and-drop rescheduling (the card is a drag *source*; month/week cells
  are the drop targets)

Time parsing / all-day detection now live in :mod:`models_event` and are
re-exported here for backward compatibility.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Signal, Qt, QPoint
from PySide6.QtGui import QMouseEvent, QDrag
from PySide6.QtWidgets import QApplication

from models_event import (
    parse_event_time,
    is_all_day_event,
    has_recurrence,
    get_event_color,
)
from widgets import build_event_mime
from config import Config

# Re-export for legacy imports (``from event_card import parse_event_time``).
__all__ = ["EventCard", "parse_event_time", "is_all_day_event"]


class EventCard(QFrame):
    """A card widget displaying a single calendar event."""

    clicked = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, event: dict, config: Config = None, parent=None):
        super().__init__(parent)
        # IMPORTANT: use 'event_data' not 'event' — 'event' would shadow
        # QObject.event(), a core Qt virtual method, causing C++ segfaults.
        self.event_data = event
        self._config = config
        self._press_pos: QPoint | None = None
        self._dragging = False
        self._is_past = False
        self._is_current = False
        self._all_day = is_all_day_event(event)
        self._setup_ui()
        self._apply_color()
        self._update_status()

    def _apply_color(self):
        color = get_event_color(self._config, self.event_data.get("event_id", ""))
        if color:
            self.setStyleSheet(f"border-left: 3px solid {color};")

    def _setup_ui(self):
        self.setObjectName("eventCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        start = parse_event_time(self.event_data.get("start_time", {}))
        end = parse_event_time(self.event_data.get("end_time", {}))
        recurring = bool(self.event_data.get("_is_recurring_instance") or has_recurrence(self.event_data))
        if self._all_day:
            time_text = "全天"
        else:
            time_text = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        if recurring:
            time_text = "♻ " + time_text

        self.time_label = QLabel(time_text)
        self.time_label.setObjectName("eventTime")
        top_row.addWidget(self.time_label)

        top_row.addStretch()

        self.delete_btn = QPushButton("x")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.setToolTip("删除日程")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.event_data))
        top_row.addWidget(self.delete_btn)

        layout.addLayout(top_row)

        summary = self.event_data.get("summary", "(无标题)")
        if not isinstance(summary, str):
            summary = str(summary)
        self.title_label = QLabel(summary)
        self.title_label.setObjectName("eventTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.title_label)

        meta_parts = []
        organizer = self.event_data.get("event_organizer", {})
        if isinstance(organizer, dict) and organizer.get("display_name"):
            meta_parts.append(str(organizer["display_name"]))

        vchat = self.event_data.get("vchat", {})
        if isinstance(vchat, dict) and vchat.get("meeting_url"):
            meta_parts.append("有视频会议")

        if meta_parts:
            self.meta_label = QLabel("  ".join(meta_parts))
            self.meta_label.setObjectName("eventMeta")
            layout.addWidget(self.meta_label)

    def _update_status(self):
        """Update visual status based on current time."""
        now = datetime.now()
        start = parse_event_time(self.event_data.get("start_time", {}))
        end = parse_event_time(self.event_data.get("end_time", {}))

        if now > end:
            self._is_past = True
        elif start <= now <= end:
            self._is_current = True

        if self._is_past:
            self.setObjectName("eventCardPast")
            self.time_label.setObjectName("eventTimePast")
            self.title_label.setObjectName("eventTitlePast")
        elif self._is_current:
            self.setObjectName("eventCardCurrent")
            self.time_label.setObjectName("eventTimeCurrent")
        else:
            self.setObjectName("eventCard")
            self.time_label.setObjectName("eventTime")
            self.title_label.setObjectName("eventTitle")

    # ── Drag to reschedule ──

    def mousePressEvent(self, ev: QMouseEvent):
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
                # Don't start a drag when the press began on the delete button.
                child = self.childAt(self._press_pos)
                if child is self.delete_btn:
                    return
                self._dragging = True
                recurring = bool(self.event_data.get("_is_recurring_instance") or has_recurrence(self.event_data))
                if not recurring:
                    drag = QDrag(self)
                    drag.setMimeData(build_event_mime(self.event_data))
                    drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self.clicked.emit(self.event_data)
        self._press_pos = None
        super().mouseReleaseEvent(ev)

    def refresh_status(self):
        """Re-evaluate and refresh the card's time status."""
        self._is_past = False
        self._is_current = False
        self._update_status()
