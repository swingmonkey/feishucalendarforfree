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

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import Config
from event_card import EventCard
from models_event import expand_events_for_range, is_all_day_event, parse_event_time
from widgets import EVENT_MIME, parse_event_mime

WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class _DayList(QWidget):
    """列内的日程容器：只有点在真正的空白处才发「新建」。

    旧实现在 ``DayColumn`` 上用 ``childAt() is None`` 判定，但整个列体都被
    ``QScrollArea`` 覆盖，几乎永远命中 scroll area/viewport，
    「点击空白处新建」在周视图里基本失效。这里改为在列表自身判定。
    """

    background_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._press_pos: QPoint | None = None
        self._pressed_background = False

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._press_pos = ev.position().toPoint()
            self._pressed_background = self.childAt(self._press_pos) is None
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._pressed_background:
            moved = (ev.position().toPoint() - (self._press_pos or ev.position().toPoint())).manhattanLength()
            if moved < QApplication.startDragDistance() and self.childAt(ev.position().toPoint()) is None:
                self.background_clicked.emit()
        self._press_pos = None
        self._pressed_background = False
        super().mouseReleaseEvent(ev)


class DayColumn(QFrame):
    """One day in the week board — header + all-day strip + scrollable event list."""

    event_clicked = Signal(dict)
    event_delete_requested = Signal(dict)
    add_event_for_date = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)
    event_context_menu = Signal(dict, QPoint)
    background_context_menu = Signal(datetime, QPoint)
    drag_blocked = Signal()

    def __init__(self, date: datetime, config: Config, parent=None):
        super().__init__(parent)
        self.col_date = date
        self._config = config
        self._is_today = date.date() == datetime.now().date()
        self._card_widgets: list[QWidget] = []
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
        date_str = self._day_caption(self.col_date)
        self._title = QLabel(f"{wd}\n{date_str}")
        self._title.setObjectName("weekColDate")
        h.addWidget(self._title)
        h.addStretch()
        add_btn = QLabel("+")
        add_btn.setObjectName("weekColAdd")
        add_btn.setToolTip("在这一天新建日程")
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.mousePressEvent = lambda ev: self.add_event_for_date.emit(self.col_date)
        h.addWidget(add_btn)
        layout.addWidget(header)

        # 全天日程独立成条，不再和定时日程按开始时间混排
        self._allday_bar = QFrame()
        self._allday_bar.setObjectName("weekAllDayBar")
        self._allday_layout = QVBoxLayout(self._allday_bar)
        self._allday_layout.setContentsMargins(2, 2, 2, 2)
        self._allday_layout.setSpacing(2)
        self._allday_bar.setVisible(False)
        layout.addWidget(self._allday_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._list = _DayList()
        self._list_layout = QVBoxLayout(self._list)
        self._list_layout.setContentsMargins(2, 2, 2, 2)
        self._list_layout.setSpacing(4)
        self._list.background_clicked.connect(
            lambda: self.add_event_for_date.emit(self.col_date)
        )
        self._list_layout.addStretch()
        scroll.setWidget(self._list)
        layout.addWidget(scroll, 1)

    def _reset_list(self):
        """清空定时列表并复原「末尾常驻弹簧」的结构。

        弹簧必须只留一个且永远在最后，否则 insertWidget 会插到弹簧后面，
        收尾时再 takeAt 掉的就不是弹簧而是最后一张卡片。
        """
        self._clear_cards()
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget is not None and widget not in self._card_widgets:
                widget.setParent(None)
                widget.deleteLater()
        self._list_layout.addStretch()

    def _apply_object_name(self):
        self.setObjectName("weekDayColToday" if self._is_today else "weekDayCol")

    @staticmethod
    def _day_caption(date: datetime) -> str:
        # 周列里月份重复显示没有意义：默认只显示日号，每月 1 号显示「月/日」
        return date.strftime("%m/%d") if date.day == 1 else str(date.day)

    def set_date(self, date: datetime):
        self.col_date = date
        self._is_today = date.date() == datetime.now().date()
        self._apply_object_name()
        wd = WEEKDAY_NAMES[date.weekday()]
        self._title.setText(f"{wd}\n{self._day_caption(date)}")

    @staticmethod
    def _as_item(item):
        if isinstance(item, tuple):
            return item
        return item, False

    def set_events(self, events):
        """``events`` 为 ``[(event, is_continuation), ...]``；全天与定时分区渲染。"""
        self._is_today = self.col_date.date() == datetime.now().date()
        self._apply_object_name()
        self._reset_list()
        while self._allday_layout.count():
            item = self._allday_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)
                item.widget().deleteLater()

        items = [self._as_item(e) for e in events]
        all_day = [it for it in items if is_all_day_event(it[0])]
        timed = [it for it in items if not is_all_day_event(it[0])]

        self._allday_bar.setVisible(bool(all_day))
        for ev, is_cont in all_day:
            self._add_card(self._allday_layout, ev, is_cont, compact=True)

        # 卡片插在末尾弹簧之前，卡片本身不参与拉伸（高度由内容决定）
        insert_at = self._list_layout.count() - 1
        for ev, is_cont in timed:
            self._add_card(self._list_layout, ev, is_cont, compact=False, index=insert_at)
            insert_at += 1

    def _clear_cards(self):
        for w in self._card_widgets:
            w.setParent(None)
            w.deleteLater()
        self._card_widgets = []

    def _add_card(self, target_layout, ev: dict, is_cont: bool, compact: bool, index: int | None = None):
        card = EventCard(ev, config=self._config, is_continuation=is_cont)
        if compact:
            card.setObjectName("eventCardAllDay")
        # 列很窄也允许标题换行，但卡片高度必须由内容决定，不能吃掉整列
        card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        card.clicked.connect(self.event_clicked)
        card.delete_clicked.connect(self.event_delete_requested)
        card.context_menu_requested.connect(self.event_context_menu)
        card.drag_blocked.connect(self.drag_blocked)
        self._card_widgets.append(card)
        if index is None:
            target_layout.addWidget(card)
        else:
            target_layout.insertWidget(index, card)

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
        if ev.button() == Qt.MouseButton.RightButton:
            self.background_context_menu.emit(self.col_date, ev.globalPos())
            ev.accept()
            return
        super().mousePressEvent(ev)

    def contextMenuEvent(self, ev):
        self.background_context_menu.emit(self.col_date, ev.globalPos())
        ev.accept()


class WeekView(QWidget):
    """weektodo-style 7-column week planner."""

    event_clicked = Signal(dict)
    event_delete_requested = Signal(dict)
    add_event_for_date = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)
    event_context_menu = Signal(dict, QPoint)
    day_background_menu = Signal(datetime, QPoint)
    drag_blocked = Signal()

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

        # 周范围标题由主窗口的 monthBar 统一显示（那里已有「MM/DD - MM/DD」），
        # 这里再放一份只会让用户看到两行同义日期。
        self.range_label = QWidget()
        self.range_label.setFixedHeight(0)
        self.range_label.setVisible(False)
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
        if hasattr(self.range_label, "setText"):
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
                col.event_context_menu.connect(self.event_context_menu)
                col.background_context_menu.connect(self.day_background_menu)
                col.drag_blocked.connect(self.drag_blocked)
                self._columns.append(col)
                self.board_layout.addWidget(col, 1)
        else:
            for i, col in enumerate(self._columns):
                col.set_date(days[i])

        for i, col in enumerate(self._columns):
            # 全天排前面（会被抽进顶部全天条），其余按开始时间排序
            items = sorted(
                by_day.get(days[i].strftime("%Y-%m-%d"), []),
                key=lambda t: (
                    is_all_day_event(t[0]),
                    parse_event_time(t[0].get("start_time", {})),
                ),
            )
            col.set_events(items)

    def events_for_date(self, date: datetime) -> list[dict]:
        result = []
        for e in self.events:
            start = parse_event_time(e.get("start_time", {}))
            end = parse_event_time(e.get("end_time", {}))
            if start.date() <= date.date() <= end.date():
                result.append(e)
        return result
