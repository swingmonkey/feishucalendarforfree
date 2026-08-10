"""Week planner view (weektodo-style).

A 7-column week board (Mon–Sun). Each column is a scrollable list of event
cards ordered by start time, with its own date header (today highlighted).
Dragging a card from one column onto another reschedules the event (the drop
emits ``reschedule_requested`` which the main window turns into a Feishu write).

Signals mirror :class:`MonthView` so the main window treats both uniformly:
- ``event_clicked(event)``
- ``add_event_for_date(date)``  (click an empty column area)
- ``event_delete_requested(event)``
- ``reschedule_requested(event_id, new_date, start_iso, end_iso, is_recurring)``
"""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QSizePolicy,
)

from models_event import parse_event_time, expand_events_for_range
from widgets import EVENT_MIME, parse_event_mime
from event_card import EventCard
from config import Config

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class DayColumn(QFrame):
    """One day in the week board — header + scrollable event card list."""

    event_clicked = Signal(dict)
    event_delete_requested = Signal(dict)
    add_event_for_date = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)

    def __init__(self, date: datetime, config: Config, parent=None):
        super().__init__(parent)
        self.col_date = date
        self._config = config
        self._is_today = date.date() == datetime.now().date()
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._setup_ui()

    def _setup_ui(self):
        self._apply_object_name()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        header = QFrame()
        header.setFixedHeight(46)
        h = QHBoxLayout(header)
        h.setContentsMargins(6, 2, 6, 2)
        wd = WEEKDAY_NAMES[self.col_date.weekday()]
        date_str = self.col_date.strftime("%m/%d")
        self._title = QLabel(f"{wd}\n{date_str}")
        self._title.setObjectName("weekColDate")
        h.addWidget(self._title)
        h.addStretch()
        add_btn = QLabel("+")
        add_btn.setObjectName("weekColAdd")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.mousePressEvent = lambda ev: self.add_event_for_date.emit(self.col_date)
        h.addWidget(add_btn)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list = QWidget()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(2, 2, 2, 2)
        self._list_layout.setSpacing(4)
        self._list_layout.addStretch()
        scroll.setWidget(self._list)
        layout.addWidget(scroll, 1)

    def _apply_object_name(self):
        self.setObjectName("weekDayColToday" if self._is_today else "weekDayCol")

    def set_date(self, date: datetime):
        self.col_date = date
        self._is_today = date.date() == datetime.now().date()
        self._apply_object_name()
        wd = WEEKDAY_NAMES[date.weekday()]
        self._title.setText(f"{wd}\n{date.strftime('%m/%d')}")

    def set_events(self, events: list[dict]):
        # Remove existing cards (keep the trailing stretch spacer).
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        if not events:
            return
        self._list_layout.takeAt(self._list_layout.count() - 1)  # drop stretch
        for ev in events:
            card = EventCard(ev, config=self._config)
            card.clicked.connect(self.event_clicked)
            card.delete_clicked.connect(self.event_delete_requested)
            self._list_layout.addWidget(card)
        self._list_layout.addStretch()

    # ── Drag & drop ──

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
            self.setObjectName("weekDayColDrop")
            self.setStyle(self.style())
        else:
            super().dragEnterEvent(ev)

    def dragLeaveEvent(self, ev):
        self._apply_object_name()
        self.setStyle(self.style())
        super().dragLeaveEvent(ev)

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
        else:
            super().dragMoveEvent(ev)

    def dropEvent(self, ev):
        self._apply_object_name()
        self.setStyle(self.style())
        payload = parse_event_mime(ev.mimeData())
        if payload:
            ev.acceptProposedAction()
            self.reschedule_requested.emit(
                payload["event_id"],
                self.col_date,
                payload["start_iso"],
                payload["end_iso"],
                payload.get("is_recurring", False),
            )
        else:
            super().dropEvent(ev)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            child = self.childAt(ev.position().toPoint())
            if child is None:
                self.add_event_for_date.emit(self.col_date)
        super().mousePressEvent(ev)


class WeekView(QWidget):
    """weektodo-style 7-column week planner."""

    event_clicked = Signal(dict)
    event_delete_requested = Signal(dict)
    add_event_for_date = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.anchor_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.events: list[dict] = []
        self._columns: list[DayColumn] = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.range_label = QLabel()
        self.range_label.setObjectName("weekRangeLabel")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.range_label)

        self.board = QWidget()
        self.board_layout = QHBoxLayout(self.board)
        self.board_layout.setContentsMargins(4, 4, 4, 4)
        self.board_layout.setSpacing(2)
        layout.addWidget(self.board, 1)

    def _week_bounds(self):
        monday = self.anchor_date - timedelta(days=self.anchor_date.weekday())
        sunday = monday + timedelta(days=6)
        return monday, sunday

    def set_events(self, events: list[dict], anchor_date: datetime):
        self.anchor_date = anchor_date
        self.events = events
        self._render()

    def _render(self):
        monday, sunday = self._week_bounds()
        self.range_label.setText(f"{monday.strftime('%Y年%m月%d日')} - {sunday.strftime('%m月%d日')}")

        expanded = expand_events_for_range(self.events, monday, sunday)
        days = [monday + timedelta(days=i) for i in range(7)]
        by_day: dict[str, list] = {d.strftime("%Y-%m-%d"): [] for d in days}
        for ev in expanded:
            start = parse_event_time(ev.get("start_time", {}))
            end = parse_event_time(ev.get("end_time", {}))
            start_date = max(start.date(), monday.date())
            end_date = min(end.date(), sunday.date())
            if start_date > end_date:
                continue
            span = (end_date - start_date).days + 1
            for i in range(span):
                cur = start_date + timedelta(days=i)
                key = cur.strftime("%Y-%m-%d")
                if key in by_day:
                    is_cont = cur != start.date()
                    by_day[key].append((ev, is_cont))

        if len(self._columns) != 7:
            for c in self._columns:
                c.deleteLater()
            self._columns = []
            for i in range(7):
                col = DayColumn(days[i], self.config, self)
                col.event_clicked.connect(self.event_clicked)
                col.event_delete_requested.connect(self.event_delete_requested)
                col.add_event_for_date.connect(self.add_event_for_date)
                col.reschedule_requested.connect(self.reschedule_requested)
                self._columns.append(col)
                self.board_layout.addWidget(col, 1)
        else:
            for i, col in enumerate(self._columns):
                col.set_date(days[i])

        for i, col in enumerate(self._columns):
            items = sorted(
                by_day.get(days[i].strftime("%Y-%m-%d"), []),
                key=lambda t: parse_event_time(t[0].get("start_time", {})),
            )
            col.set_events([ev for ev, _ in items])

    def events_for_date(self, date: datetime) -> list[dict]:
        result = []
        for e in self.events:
            start = parse_event_time(e.get("start_time", {}))
            end = parse_event_time(e.get("end_time", {}))
            if start.date() <= date.date() <= end.date():
                result.append(e)
        return result
