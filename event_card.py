"""Event card widget for displaying a single calendar event."""

from datetime import datetime
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Signal, Qt


def parse_event_time(time_data) -> datetime:
    """Parse event time from lark-cli response.

    Handles both timed events (with 'datetime' field) and all-day events
    (with 'date' field only).
    """
    if not isinstance(time_data, dict):
        return datetime.now()
    # Timed event: has 'datetime' field like '2026-07-15T10:00:00+08:00'
    dt_str = time_data.get("datetime", "")
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str)
            # Strip timezone to avoid offset-naive vs offset-aware comparison errors
            return dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
    # All-day event: has 'date' field like '2026-07-15'
    date_str = time_data.get("date", "")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return datetime.now()


def is_all_day_event(event: dict) -> bool:
    """Check if an event is an all-day event (date-only, no datetime)."""
    start = event.get("start_time", {})
    if isinstance(start, dict):
        return bool(start.get("date")) and not start.get("datetime")
    return False


class EventCard(QFrame):
    """A card widget displaying a single calendar event."""

    clicked = Signal(dict)
    delete_clicked = Signal(dict)

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        # IMPORTANT: use 'event_data' not 'event' — 'event' would shadow
        # QObject.event(), a core Qt virtual method, causing C++ segfaults.
        self.event_data = event
        self._is_past = False
        self._is_current = False
        self._all_day = is_all_day_event(event)
        self._setup_ui()
        self._update_status()

    def _setup_ui(self):
        self.setObjectName("eventCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(4)

        # Top row: time + delete button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Time label
        start = parse_event_time(self.event_data.get("start_time", {}))
        end = parse_event_time(self.event_data.get("end_time", {}))
        if self._all_day:
            time_text = "全天"
        else:
            time_text = f"{start.strftime('%H:%M')} - {end.strftime('%H:%M')}"
        self.time_label = QLabel(time_text)
        self.time_label.setObjectName("eventTime")
        top_row.addWidget(self.time_label)

        top_row.addStretch()

        # Delete button
        self.delete_btn = QPushButton("x")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.setToolTip("删除日程")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.event_data))
        top_row.addWidget(self.delete_btn)

        layout.addLayout(top_row)

        # Title
        summary = self.event_data.get("summary", "(无标题)")
        if not isinstance(summary, str):
            summary = str(summary)
        self.title_label = QLabel(summary)
        self.title_label.setObjectName("eventTitle")
        self.title_label.setWordWrap(True)
        self.title_label.setCursor(Qt.CursorShape.PointingHandCursor)
        layout.addWidget(self.title_label)

        # Meta info (organizer, location, etc.)
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

        # Use objectName switching instead of dynamic properties
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

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.event_data)
        super().mousePressEvent(ev)

    def refresh_status(self):
        """Re-evaluate and refresh the card's time status."""
        self._is_past = False
        self._is_current = False
        self._update_status()
