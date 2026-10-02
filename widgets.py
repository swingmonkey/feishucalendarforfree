"""Shared calendar widgets: date badge, clickable label, compact grid event
label (drag source) and the day cell (drop target for drag-to-reschedule).

Extracted from the old ``calendar_widget.py`` so the month and week views can
share identical building blocks, mirroring weektodo's component approach.
"""

import json
from datetime import datetime

from PySide6.QtCore import QByteArray, QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QFont, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from config import Config
from models_event import get_event_color, has_recurrence, is_all_day_event, parse_event_time

# MIME type used to carry a dragged event between cells / week columns.
EVENT_MIME = "application/x-feishu-event"

# Max events shown per day cell before the "+N more" affordance.
# 默认字号（10px → 行高 18px）下的上限；字号调大后按预算动态收缩。
MAX_VISIBLE_EVENTS = 3
_GRID_VISIBLE_BUDGET = 54  # 3 × 18px

# 日格里除日程条以外的固定占用：日期徽标行高 + 上下边距/间距余量
_DAY_NUM_HEIGHT = 18
_CELL_CHROME = 6
_MORE_ROW_HEIGHT = 14  # 「+N更多」需要独占一行


def visible_event_count(
    grid_font: int = 10,
    cell_height: int | None = None,
    reserve_more: bool = False,
) -> int:
    """按日程字号推算日格内可容纳的日程条数（至少 1 条，至多 MAX_VISIBLE_EVENTS）。

    行高 = 字号 + 8（与 styles._event_font_rules 的 max-height 一致），
    字号调大时自动少显示几条，避免挤爆日格。

    ``cell_height`` 给定时改用日格实际高度计算，而不是固定的像素预算——
    否则窗口压矮或出现 6 行月份时，唯一的「+N更多」入口会被挤出日格，
    藏在里面的日程将彻底无法点开。
    """
    try:
        grid_font = int(grid_font)
    except (TypeError, ValueError):
        grid_font = 10
    row_h = max(12, grid_font + 8)
    if cell_height:
        try:
            available = int(cell_height) - _DAY_NUM_HEIGHT - _CELL_CHROME
        except (TypeError, ValueError):
            available = 0
        if reserve_more:
            available -= _MORE_ROW_HEIGHT
        # 已知日格高度时按实际空间算；连一条都放不下也要留 1 条，
        # 不能退回固定像素预算，否则矮窗口里反而显示更多、挤掉「+N更多」。
        return max(1, min(MAX_VISIBLE_EVENTS, available // row_h))
    return max(1, min(MAX_VISIBLE_EVENTS, _GRID_VISIBLE_BUDGET // row_h))


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
        self._circle_color = QColor("#3370FF")
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
    # 拖拽改期被拒绝（如重复日程）时向外汇报，避免变成吞掉点击的死手势
    drag_blocked = Signal()
    context_menu_requested = Signal(dict, QPoint)

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
                if self._start_drag():
                    self._dragging = True
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and not self._dragging:
            self.clicked.emit(self.event_data)
        self._press_pos = None
        super().mouseReleaseEvent(ev)

    def contextMenuEvent(self, ev):
        self.context_menu_requested.emit(self.event_data, ev.globalPos())
        ev.accept()

    def _is_recurring(self) -> bool:
        return bool(
            self.event_data.get("_is_recurring_instance") or has_recurrence(self.event_data)
        )

    def _start_drag(self) -> bool:
        """启动拖拽；返回 False 表示这次手势不能改期（调用方不要置 _dragging）。"""
        if self._is_recurring():
            # 重复日程改期会牵动整个序列，暂不支持。
            # 这里必须返回 False 而不是让 _dragging 保持 True，
            # 否则松手时既不拖拽也不触发 clicked，手势被完全吞掉。
            self.drag_blocked.emit()
            return False
        drag = QDrag(self)
        drag.setMimeData(build_event_mime(self.event_data))
        drag.exec(Qt.DropAction.MoveAction)
        return True


class DayCell(QFrame):
    """A single day cell in the calendar grid (drop target for reschedule)."""

    event_clicked = Signal(dict)
    more_clicked = Signal(datetime)
    add_clicked = Signal(datetime)
    reschedule_requested = Signal(str, datetime, str, str, bool)
    # 子日程标签想拖拽但被拒（重复日程）时向上传递
    drag_blocked = Signal()
    # 用户在日程标签上右键
    event_context_menu = Signal(dict, QPoint)
    # 用户在日格空白处右键：(日期, 全局坐标)
    background_context_menu = Signal(datetime, QPoint)

    def __init__(self, date: datetime, events: list, is_current_month: bool, config: Config = None, parent=None):
        super().__init__(parent)
        self.cell_date = date
        # events: list of (event_dict, is_continuation) tuples
        self._events = events
        self._is_current_month = is_current_month
        self._is_today = date.date() == datetime.now().date()
        self._config = config
        self._hover = False
        self._drop = False
        self._cursor = False
        self._visible_limit = 0
        self._event_widgets: list[QWidget] = []
        self._more_widget: QWidget | None = None
        self._layout: QVBoxLayout | None = None
        self._date_lbl: QLabel | None = None
        self._press_pos: QPoint | None = None
        self._pressed_background = False
        # 单元格同样不贡献水平最小宽度，保证 7 列严格等宽（与表头对齐）
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setAcceptDrops(True)
        self._setup_ui()
        self.setMouseTracking(True)

    def _base_object_name(self) -> str:
        if self._is_today:
            return "dayCellToday"
        if not self._is_current_month:
            return "dayCellOther"
        return "dayCell"

    def _refresh_object_name(self):
        """合成样式名：拖拽落点 > 键盘游标 > 悬停 > 基础态。"""
        base = self._base_object_name()
        if self._drop:
            name = base + "Drop"
        elif self._cursor:
            name = base + "Cursor"
        elif self._hover:
            name = base + "Hover"
        else:
            name = base
        if name != self.objectName():
            self.setObjectName(name)
            # objectName 变化后必须重新抛光，否则 QSS 不会生效
            self.style().unpolish(self)
            self.style().polish(self)

    def _setup_ui(self):
        self._refresh_object_name()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(1)
        self._layout = layout

        if self._is_today:
            date_lbl = DateCircleLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNumToday")
        elif not self._is_current_month:
            date_lbl = QLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNumOther")
        else:
            date_lbl = QLabel(str(self.cell_date.day))
            date_lbl.setObjectName("dayNum")
        date_lbl.setFixedHeight(_DAY_NUM_HEIGHT)
        self._date_lbl = date_lbl
        layout.addWidget(date_lbl)

        # 末尾常驻弹簧，日程条一律插在它前面
        layout.addStretch()
        self._rebuild_event_area()

    def _grid_font(self) -> int:
        return self._config.get("grid_font_size", 10) if self._config else 10

    def _compute_limit(self) -> int:
        """按日格实际高度决定显示几条；放不下时给「+N更多」留一行。"""
        font = self._grid_font()
        height = self.height()
        if height <= 0:
            return visible_event_count(font)
        limit = visible_event_count(font, cell_height=height)
        if len(self._events) > limit:
            limit = visible_event_count(font, cell_height=height, reserve_more=True)
        return max(1, limit)

    def _rebuild_event_area(self):
        limit = self._compute_limit()
        if limit == self._visible_limit and self._event_widgets:
            return
        self._visible_limit = limit
        self._clear_event_area()

        insert_at = self._layout.count() - 1  # 常驻弹簧之前
        for item in self._events[:limit]:
            if isinstance(item, tuple):
                ev, is_cont = item
            else:
                ev, is_cont = item, False
            lbl = GridEventLabel(ev, is_continuation=is_cont, config=self._config)
            lbl.clicked.connect(self._on_event_clicked)
            lbl.drag_blocked.connect(self.drag_blocked.emit)
            lbl.context_menu_requested.connect(self.event_context_menu)
            self._event_widgets.append(lbl)
            self._layout.insertWidget(insert_at, lbl)
            insert_at += 1

        remaining = len(self._events) - limit
        if remaining > 0:
            more_lbl = ClickableLabel(f"+{remaining}更多")
            more_lbl.setObjectName("moreLabel")
            more_lbl.setToolTip(f"查看当天全部 {len(self._events)} 项日程")
            more_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
            more_lbl.clicked.connect(lambda: self.more_clicked.emit(self.cell_date))
            self._more_widget = more_lbl
            self._layout.insertWidget(insert_at, more_lbl)

    def _clear_event_area(self):
        for w in self._event_widgets:
            self._layout.removeWidget(w)
            w.setParent(None)
            w.deleteLater()
        self._event_widgets = []
        if self._more_widget is not None:
            self._layout.removeWidget(self._more_widget)
            self._more_widget.setParent(None)
            self._more_widget.deleteLater()
            self._more_widget = None

    def _on_event_clicked(self, event: dict):
        self.event_clicked.emit(event)

    def set_cursor_active(self, active: bool):
        """键盘游标高亮（方向键在日期间移动时的落点指示）。"""
        if self._cursor == active:
            return
        self._cursor = active
        self._refresh_object_name()

    # ── Drag & drop (reschedule) ──

    def dragEnterEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
            self._drop = True
            self._refresh_object_name()
        else:
            super().dragEnterEvent(ev)

    def dragMoveEvent(self, ev):
        if ev.mimeData().hasFormat(EVENT_MIME):
            ev.acceptProposedAction()
        else:
            super().dragMoveEvent(ev)

    def dragLeaveEvent(self, ev):
        self._drop = False
        self._refresh_object_name()
        super().dragLeaveEvent(ev)

    def dropEvent(self, ev):
        self._drop = False
        self._refresh_object_name()
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

    # ── Click empty area of the cell to add an event ──

    def _is_background_pos(self, pos) -> bool:
        """空白处判定：日格自身或日期徽标都算「空白」。

        日期徽标也是 QLabel 子控件，若不算进去会出现「点 28 没反应、
        点 29 的空地却弹新建」这种同一格内不一致的命中区。
        """
        child = self.childAt(pos)
        return child is None or child is self._date_lbl

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._press_pos = ev.position().toPoint()
            self._pressed_background = self._is_background_pos(self._press_pos)
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton and self._press_pos is not None:
            moved = (ev.position().toPoint() - self._press_pos).manhattanLength()
            # 按下与松开之间没有明显位移才算点击，避免拖拽改期后误弹新建框
            if moved < QApplication.startDragDistance() and self._pressed_background:
                if self._is_background_pos(ev.position().toPoint()):
                    self.add_clicked.emit(self.cell_date)
        self._press_pos = None
        self._pressed_background = False
        super().mouseReleaseEvent(ev)

    def contextMenuEvent(self, ev):
        if self._is_background_pos(ev.pos()):
            self.background_context_menu.emit(self.cell_date, ev.globalPos())
        ev.accept()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        # 窗口缩放会改变日格高度，可容纳条数需要跟着重算，
        # 否则「+N更多」这一唯一入口会被挤出格子。
        if not self._layout:
            return
        self._rebuild_event_area()

    def enterEvent(self, ev):
        """Highlight cell on hover."""
        self._hover = True
        self._refresh_object_name()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        """Restore cell appearance when mouse leaves."""
        self._hover = False
        self._refresh_object_name()
        super().leaveEvent(ev)
