"""Month grid view — a reusable component extracted from the old
``CalendarWidget``. It owns the 7-column month grid (with multi-day expansion
and recurring-event expansion) and forwards user intent through signals:

- ``event_clicked(event)``
- ``day_activated(date)``      (+N more / day header)
- ``add_event_for_date(date)`` (click empty cell)
- ``reschedule_requested(event_id, new_date, start_iso, end_iso, is_recurring)``
"""

import calendar as cal_module
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
)

from widgets import DayCell, ClickableLabel, DateCircleLabel
from models_event import parse_event_time, expand_events_for_range
from config import Config

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


class MonthView(QWidget):
    """Borderless month-grid calendar view."""

    event_clicked = Signal(dict)
    day_activated = Signal(datetime)
    add_event_for_date = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.events: list[dict] = []
        self._events_by_date: dict = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_weekday_header())

        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(2)
        layout.addWidget(self.grid_container, 1)

    def _build_weekday_header(self) -> QWidget:
        header = QFrame()
        header.setFixedHeight(24)
        g = QGridLayout(header)
        g.setContentsMargins(4, 0, 4, 0)
        g.setSpacing(2)
        for i, name in enumerate(WEEKDAY_NAMES):
            lbl = QLabel(name)
            if i >= 5:
                lbl.setObjectName("weekDayWeekend")
            else:
                lbl.setObjectName("weekDay")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(lbl, 0, i)
            g.setColumnStretch(i, 1)
        return header

    # ── Public API ──

    def set_context(self, current_date: datetime):
        self.current_date = current_date

    def set_events(self, events: list[dict], current_date: datetime):
        self.current_date = current_date
        self.events = events
        self._render_grid()

    # ── Rendering ──

    def _month_bounds(self):
        month_start = self.current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if month_start.month == 12:
            month_end = month_start.replace(year=month_start.year + 1, month=1) - timedelta(days=1)
        else:
            month_end = month_start.replace(month=month_start.month + 1) - timedelta(days=1)
        return month_start, month_end

    def _group_events_by_date(self, month_start, month_end) -> dict:
        """Group events by date, expanding multi-day and recurring events."""
        expanded = expand_events_for_range(self.events, month_start, month_end)

        events_by_date: dict[str, list] = {}
        for ev in expanded:
            start = parse_event_time(ev.get("start_time", {}))
            end = parse_event_time(ev.get("end_time", {}))
            start_date = max(start.date(), month_start.date())
            end_date = min(end.date(), month_end.date())
            if start_date > end_date:
                continue
            span = (end_date - start_date).days + 1
            for i in range(span):
                current = start_date + timedelta(days=i)
                date_key = current.strftime("%Y-%m-%d")
                is_continuation = current != start.date()
                events_by_date.setdefault(date_key, []).append((ev, is_continuation))
        return events_by_date

    def _render_grid(self):
        self._clear_grid()
        month_start, month_end = self._month_bounds()
        self._events_by_date = self._group_events_by_date(month_start, month_end)

        cal = cal_module.Calendar(firstweekday=0)  # Monday = 0
        weeks = cal.monthdatescalendar(self.current_date.year, self.current_date.month)

        for row, week in enumerate(weeks):
            for col, date_obj in enumerate(week):
                date_key = date_obj.strftime("%Y-%m-%d")
                day_events = self._events_by_date.get(date_key, [])
                is_current_month = date_obj.month == self.current_date.month

                cell = DayCell(
                    date=datetime(date_obj.year, date_obj.month, date_obj.day),
                    events=day_events,
                    is_current_month=is_current_month,
                    config=self.config,
                )
                cell.event_clicked.connect(self.event_clicked)
                cell.more_clicked.connect(self.day_activated)
                cell.add_clicked.connect(self.add_event_for_date)
                cell.reschedule_requested.connect(self.reschedule_requested)
                self.grid_layout.addWidget(cell, row, col)

        for row in range(len(weeks)):
            self.grid_layout.setRowStretch(row, 1)
        for col in range(7):
            self.grid_layout.setColumnStretch(col, 1)

    def _clear_grid(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def events_for_date(self, date: datetime) -> list[dict]:
        """Return the original (non-expanded) events spanning ``date``."""
        result = []
        for e in self.events:
            start = parse_event_time(e.get("start_time", {}))
            end = parse_event_time(e.get("end_time", {}))
            if start.date() <= date.date() <= end.date():
                result.append(e)
        return result
