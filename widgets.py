"""Shared calendar widgets: date badge, clickable label, compact grid event
label (drag source) and the day cell (drop target for drag-to-reschedule).

Extracted from the old ``calendar_widget.py`` so the month and week views can
share identical building blocks, mirroring weektodo's component approach.
"""

import json
import math
from datetime import datetime

from PySide6.QtCore import (
    Property,
    QByteArray,
    QEasingCurve,
    QMimeData,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QConicalGradient,
    QDrag,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

import hover_popover
import theme
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
    """今天日号：青蓝渐变圆底 + 深墨数字。

    原实现是纯色圆（#3370FF）+ 白字。改成渐变后白字在浅青那一端对比不足，
    所以文字取 ``accent_ink``（深墨）——整颗像一枚发光的小标记，也是整个
    界面唯一带渐变填充的元素。
    """

    def __init__(self, text: str, parent=None, dark: bool = True):
        super().__init__(text, parent)
        self._dark = dark
        self._circle_radius = 8

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        colors = theme.paint_colors("dark" if self._dark else "light")
        radius = min(self._circle_radius, self.height() // 2 - 1)
        cx = self.width() // 2
        cy = self.height() // 2

        grad = QLinearGradient(QPointF(cx - radius, cy - radius), QPointF(cx + radius, cy + radius))
        grad.setColorAt(0.0, QColor(*colors["beam_from"]))
        grad.setColorAt(1.0, QColor(*colors["beam_to"]))
        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)

        painter.setPen(QColor("#07111f") if self._dark else QColor("#ffffff"))
        font = QFont(self.font())
        font.setBold(True)
        font.setPixelSize(10)
        painter.setFont(font)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()


class ElidedLabel(QLabel):
    """单行文本，放不下时尾部省略号，而不是被父容器硬切半个字。

    QLabel 没有自动缩略能力，日程标题一长就会在格子边缘被生硬截断，
    看起来像渲染 bug。这里在 resize 时按当前宽度重算 elided 文本，
    完整标题仍由外层 QFrame 的 tooltip 提供。
    """

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)

    def setText(self, text: str):
        self._full_text = text
        super().setText(text)
        self._apply_elide()

    def fullText(self) -> str:
        return self._full_text

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._apply_elide()

    def _apply_elide(self):
        width = self.width()
        if width <= 12:
            return
        elided = self.fontMetrics().elidedText(
            self._full_text, Qt.TextElideMode.ElideRight, width
        )
        if elided != super().text():
            super().setText(elided)


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
        title_lbl = ElidedLabel(summary)
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

    def _theme_name(self) -> str:
        return (self._config.get("theme", "dark") if self._config else "dark")

    def enterEvent(self, ev):
        hover_popover.show_for(
            self,
            hover_popover.event_detail_widget(self.event_data, self._theme_name()),
            self._theme_name(),
        )
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        hover_popover.schedule_close()
        super().leaveEvent(ev)

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
        # 左右 4px 让日号与格子边缘有点呼吸；上下 3+3 保持
        # _CELL_CHROME 预算不变（那里按上下边距合计 6px 算可见条数）
        layout.setContentsMargins(4, 3, 3, 3)
        layout.setSpacing(2)
        self._layout = layout

        if self._is_today:
            dark = not (self._config and self._config.get("theme", "dark") == "light")
            date_lbl = DateCircleLabel(str(self.cell_date.day), dark=dark)
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

    def _theme_name(self) -> str:
        return (self._config.get("theme", "dark") if self._config else "dark")

    def _day_events(self) -> list[dict]:
        """_events 里混着 (event, is_cont) 元组，摘要只要 dict。"""
        return [
            (item[0] if isinstance(item, tuple) else item)
            for item in self._events
        ]

    def enterEvent(self, ev):
        """Highlight cell on hover; 350ms 后弹出当天日程摘要（防扫过误触）。"""
        self._hover = True
        self._refresh_object_name()
        hover_popover.show_for(
            self,
            hover_popover.day_summary_widget(
                self.cell_date, self._day_events(), self._theme_name()
            ),
            self._theme_name(),
            delay_ms=350,
        )
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        """Restore cell appearance when mouse leaves."""
        self._hover = False
        self._refresh_object_name()
        hover_popover.schedule_close()
        super().leaveEvent(ev)


class ConnectingOrb(QWidget):
    """等待动效：一圈青蓝渐变光弧沿着细轨道转。

    为什么换掉系统 ``QProgressBar``：那种「不确定进度」是一根来回扫的灰条，
    与这套「深色台面 + 青蓝光晕 + 极细线」的设计语言毫无关系，而且它只有
    一维的往返，看两秒就像卡住了。

    这里让三件事同时动，周期互不成整数倍，肉眼抓不到重复的「节拍」：

    ==========  =======  ======================================
    角度 spin    1500ms   光弧匀速转圈（匀速才不会每次过同一角度就顿一下）
    角宽 sweep   2600ms   张开 78°→158°→78°，像在「吸气吐气」
    呼吸 breath  2100ms   外圈光晕的透明度随之起伏
    ==========  =======  ======================================

    另外两层静态层负责质感：轨道（细，低透明度）和中心的一点微光核心。
    弧的头端额外补一团径向光斑——没有它，圆头笔帽在深色底上会显得「切断」，
    有它才像一道光真的在扫过。

    隐藏即停：这是个常驻桌面的小挂件，面板切走后继续 60fps 重绘纯属浪费电。
    """

    SIDE = 96  # 控件边长：轨道直径 66 + 两侧各 15 的光晕余量
    _SPIN_MS = 1500
    _SWEEP_MS = 2600
    _BREATH_MS = 2100
    _TRACK_PEN = 1.2
    _ARC_PEN = 3.4

    def __init__(self, parent=None, dark: bool = True):
        super().__init__(parent)
        self._dark = bool(dark)
        self._spin = 0.0
        self._sweep = 118.0
        self._breath = 0.0
        self.setFixedSize(self.SIDE, self.SIDE)
        # 透明底 + 不吃鼠标：气泡只负责发光，别把父级的点击挡掉
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        self._spin_anim = self._loop(b"spin", self._SPIN_MS, [(0.0, 0.0), (1.0, 360.0)], linear=True)
        self._sweep_anim = self._loop(b"sweep", self._SWEEP_MS, [(0.0, 78.0), (0.5, 158.0), (1.0, 78.0)])
        self._breath_anim = self._loop(b"breath", self._BREATH_MS, [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)])

    # ── 动画属性 ──────────────────────────────────────────────────
    # QPropertyAnimation 只认 Qt 属性，所以这三个值要走 Property 暴露。

    def _get_spin(self) -> float:
        return self._spin

    def _set_spin(self, value: float):
        self._spin = float(value)
        self.update()

    def _get_sweep(self) -> float:
        return self._sweep

    def _set_sweep(self, value: float):
        self._sweep = float(value)
        self.update()

    def _get_breath(self) -> float:
        return self._breath

    def _set_breath(self, value: float):
        self._breath = float(value)
        self.update()

    spin = Property(float, _get_spin, _set_spin)
    sweep = Property(float, _get_sweep, _set_sweep)
    breath = Property(float, _get_breath, _set_breath)

    # ── 生命周期 ──────────────────────────────────────────────────

    def _loop(
        self,
        prop: bytes,
        duration: int,
        stops: list[tuple[float, float]],
        linear: bool = False,
    ) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, prop, self)
        anim.setDuration(duration)
        anim.setLoopCount(-1)  # 无限循环
        # 转圈必须匀速：用任何缓动，每一圈都会在同一个角度慢下来，
        # 变成肉眼可见的「顿一下」。呼吸类才需要缓动。
        anim.setEasingCurve(
            QEasingCurve.Type.Linear if linear else QEasingCurve.Type.InOutSine
        )
        for at, value in stops:
            anim.setKeyValueAt(at, value)
        return anim

    def _animations(self) -> tuple[QPropertyAnimation, ...]:
        return (self._spin_anim, self._sweep_anim, self._breath_anim)

    def is_spinning(self) -> bool:
        return self._spin_anim.state() == QPropertyAnimation.State.Running

    def start(self):
        for anim in self._animations():
            if anim.state() != QPropertyAnimation.State.Running:
                anim.start()
        self.update()

    def stop(self):
        for anim in self._animations():
            anim.stop()

    def set_dark(self, dark: bool):
        dark = bool(dark)
        if dark == self._dark:
            return
        self._dark = dark
        self.update()

    def showEvent(self, ev):
        super().showEvent(ev)
        self.start()

    def hideEvent(self, ev):
        self.stop()
        super().hideEvent(ev)

    # ── 自绘 ──────────────────────────────────────────────────────

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        colors = theme.paint_colors("dark" if self._dark else "light")
        beam_from = QColor(*colors["beam_from"])
        beam_to = QColor(*colors["beam_to"])
        dark = self._dark

        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        half = min(self.width(), self.height()) / 2.0
        ring_r = half * 0.69  # 66px 直径，两侧留出光晕的溢出空间

        self._paint_halo(painter, center, half, beam_to, dark)
        self._paint_track(painter, center, ring_r, colors, dark)
        self._paint_arc(painter, center, ring_r, beam_from, beam_to, dark)
        self._paint_tip(painter, center, ring_r, beam_from, dark)
        self._paint_core(painter, center, beam_from, beam_to)
        painter.end()

    def _paint_halo(self, painter: QPainter, center: QPointF, halo_r: float, color: QColor, dark: bool):
        """环状光晕：亮度峰值压在轨道上，不是压在圆心。

        圆心亮起来会变成一块「蓝色圆饼」；峰值在轨道半径上才像真的在发光。
        透明度随 breath 起伏，是「它在工作」最便宜的暗示。
        """
        peak = int((44 if dark else 16) + (18 if dark else 7) * self._breath)
        grad = QRadialGradient(center, halo_r)
        for pos, alpha in ((0.0, 0), (0.32, int(peak * 0.30)), (0.70, peak), (1.0, 0)):
            tint = QColor(color)
            tint.setAlpha(alpha)
            grad.setColorAt(pos, tint)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(center, halo_r, halo_r)

    def _paint_track(self, painter: QPainter, center: QPointF, ring_r: float, colors: dict, dark: bool):
        track = QColor(*colors["track"])
        track.setAlpha(40 if dark else 34)
        pen = QPen(track)
        pen.setWidthF(self._TRACK_PEN)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, ring_r, ring_r)

    def _head_angle(self) -> float:
        """弧头所在角度（度，3 点方向起逆时针为正）。

        取 ``-spin``：spin 随时间递增，取负号后弧头角度递减，看上去就是
        顺时针转——和系统里绝大多数加载指示器一致。逆时针看着「有道理」，
        用久了总觉得反着来。
        """
        return -self._spin

    def _paint_arc(
        self,
        painter: QPainter,
        center: QPointF,
        ring_r: float,
        beam_from: QColor,
        beam_to: QColor,
        dark: bool,
    ):
        """主光弧：锥形渐变，弧尾淡出到全透明，弧头最亮。

        只做「从弧头逆时针画到弧尾」这一种画法：视觉上的顺/逆时针交给
        弧头角度本身（见 ``_head_angle``）去决定，跨度符号始终为正。
        混着用会让渐变方向和实际弧段对不上——那是这张图最容易踩的坑。
        """
        rect = QRectF(center.x() - ring_r, center.y() - ring_r, ring_r * 2, ring_r * 2)
        span = max(2.0, min(360.0, self._sweep))
        frac = span / 360.0
        head = self._head_angle()

        # 锥形渐变的角度是「3 点方向起、逆时针」递增，弧也是逆时针画，
        # 所以把渐变原点定在弧头上，位置 0 就是弧头、位置 frac 就是弧尾。
        grad = QConicalGradient(center, head)
        mid = 148 if dark else 205
        for pos, color, alpha in ((0.00, beam_to, 255), (0.46, beam_from, mid), (1.00, beam_from, 0)):
            tint = QColor(color)
            tint.setAlpha(alpha)
            grad.setColorAt(pos * frac, tint)

        pen = QPen(QBrush(grad), self._ARC_PEN)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(rect, int(head * 16), int(span * 16))

    def _paint_tip(self, painter: QPainter, center: QPointF, ring_r: float, color: QColor, dark: bool):
        """弧头的一小团光斑：让弧的起点像「光」，而不像一条被剪断的线。"""
        rad = math.radians(self._head_angle())
        tip = QPointF(center.x() + ring_r * math.cos(rad), center.y() - ring_r * math.sin(rad))
        radius = self._ARC_PEN * 2.2
        grad = QRadialGradient(tip, radius)
        for pos, alpha in ((0.0, 168 if dark else 150), (0.55, 58 if dark else 44), (1.0, 0)):
            tint = QColor(color)
            tint.setAlpha(alpha)
            grad.setColorAt(pos, tint)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(tip, radius, radius)

    def _paint_core(self, painter: QPainter, center: QPointF, beam_from: QColor, beam_to: QColor):
        """圆心一点微光，跟着呼吸缩放。"""
        radius = 2.0 + 1.2 * self._breath
        grad = QRadialGradient(center, radius)
        head = QColor(beam_from)
        head.setAlpha(235)
        tail = QColor(beam_to)
        tail.setAlpha(90)
        grad.setColorAt(0.0, head)
        grad.setColorAt(1.0, tail)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(grad)
        painter.drawEllipse(center, radius, radius)


class FloatingSurface(QWidget):
    """常驻桌面的浮窗形态基类：无边框、置顶、可拖、位置记得住。

    今日条和桌面小组件共用这套行为。两条语义不是随手写的：

    · **位移小于 4px 视为点击而不是拖拽**——这类挂件没有按钮，点开主窗口
      是它的主要出口；不区分就会在每次拖拽结束时弹出一个窗口。
    · **位置存 -1 表示「用户没手动摆过」**，回落到主屏右下角而不是 (0,0)。
      负坐标的副屏上会退回默认位置，这是已知限制，不要当成 bug 改。

    窗口标志用 ``Tool``：它不进 Mission Control、不占 Dock，正是桌面挂件
    该有的形态。代价是 ``Tool`` 窗口只跟当前 Space——真跨 Space 要设
    ``NSWindow.collectionBehavior``，那需要 ObjC 桥，本项目不引新依赖所以没做。
    """

    activated = Signal()
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_offset: QPoint | None = None
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    # ── Placement ──

    def restore_position(self, x: int, y: int):
        """Place the surface; ``-1`` means "bottom-right of the primary screen"."""
        if x >= 0 and y >= 0:
            self.move(x, y)
            return
        screen = self.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        self.adjustSize()
        self.move(area.right() - self.width() - 24, area.bottom() - self.height() - 24)

    # ── Interaction ──

    def close_surface(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()
            return
        super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_offset is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_offset)
            ev.accept()
            return
        super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._drag_offset is not None:
            moved = (ev.globalPosition().toPoint() - self.frameGeometry().topLeft()) - self._drag_offset
            self._drag_offset = None
            if moved.manhattanLength() < 4:
                # 没拖动 → 视为「打开主窗口」
                self.activated.emit()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        self.activated.emit()
        ev.accept()
