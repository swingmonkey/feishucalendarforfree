"""悬停信息窗 —— token-monitor helpPopover / limit-detail-tooltip 的 Qt 移植。

行为真源（renderer/helpPopover.js + selectControl.js 的 popupPosition）：
- enter **立即显示**；离开后 150ms 才关（期间移回触发器或弹层则取消关闭）
- 定位相对锚点矩形（非光标）：gap=4、视口 gutter=8、宽 min(280, 屏宽-16)、
  优先开在下方，放不下且上方更宽裕 → 翻到上方
- 同屏单例：新开先关旧
- 表面：玻璃底 rgba(48,52,56,0.76)（亮色主题翻转），边框 1px
  rgba(232,238,244,0.22)，圆角 7px，阴影 0 10px 28px rgba(0,0,0,0.2)
  （Qt 没有 backdrop-filter，半透明会直接透出底下内容，无模糊）

Qt 落地要点：
- 弹层是**独立顶层窗口**（ToolTip 级，不抢焦点），不是内嵌子控件——
  对应 HTML Popover API 的「顶层绘制、不受祖先裁剪」
- 触发器销毁时弹层必须跟着关（否则留一个孤儿浮窗）
- 整格悬停（月视图日格）信息量大且容易误触，show_for 支持 delay_ms
  做打开延迟；小控件（日程卡/月格日程条）用 0（立即开）
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

import models_event
import theme

POPOVER_WIDTH = 280
CLOSE_DELAY_MS = 150
GAP = 4
GUTTER = 8

# 当前打开的实例与关闭计时器（同屏单例）
_ACTIVE: HoverPopover | None = None
_OPEN_TIMER: QTimer | None = None
_CLOSE_TIMER: QTimer | None = None


def popup_position(
    anchor_rect: QRect,
    size: QRect,
    screen_rect: QRect,
    gap: int = GAP,
    gutter: int = GUTTER,
) -> tuple[QPoint, bool]:
    """计算弹层全局落点。返回 (左上角坐标, 是否开在锚点上方)。

    直译 selectControl.js 的 popupPosition：优先下方；下方高度不够且
    上方更宽裕才翻上去；水平 gutter 夹取防出屏。
    """
    below = screen_rect.bottom() - anchor_rect.bottom() - gap - gutter
    above = anchor_rect.top() - gap - gutter
    opens_above = size.height() > below and above > below

    width = size.width()
    # align='end'：右缘对齐锚点右缘，再夹取
    left = anchor_rect.right() - width
    left = max(screen_rect.left() + gutter, min(left, screen_rect.right() - width - gutter))
    if opens_above:
        top = anchor_rect.top() - gap - size.height()
    else:
        top = anchor_rect.bottom() + gap
    return QPoint(left, top), opens_above


def _anchor_global_rect(anchor: QWidget) -> QRect:
    top_left = anchor.mapToGlobal(QPoint(0, 0))
    return QRect(top_left, anchor.size())


def cancel_close() -> None:
    """移回触发器/弹层：撤销待执行的关闭。"""
    global _CLOSE_TIMER  # noqa: PLW0603
    if _CLOSE_TIMER is not None:
        _CLOSE_TIMER.stop()
        _CLOSE_TIMER = None


def schedule_close(delay_ms: int = CLOSE_DELAY_MS) -> None:
    """离开触发器/弹层：延迟关闭，期间移回即取消。"""
    global _CLOSE_TIMER  # noqa: PLW0603
    cancel_close()
    if _ACTIVE is None:
        return
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(_close_active)
    timer.start(delay_ms)
    _CLOSE_TIMER = timer


def _close_active() -> None:
    global _ACTIVE  # noqa: PLW0603
    if _ACTIVE is not None:
        pop = _ACTIVE
        _ACTIVE = None
        pop.close()
        pop.deleteLater()


def _screen_for(anchor: QWidget) -> QRect:
    screen = anchor.screen() or QApplication.primaryScreen()
    if screen is None:
        return QRect(0, 0, 1920, 1080)
    return screen.availableGeometry()


class HoverPopover(QWidget):
    """无边框置顶浮层。不要直接实例化，走模块级 show_for()。"""

    def __init__(self, theme_name: str, content: QWidget, width: int = POPOVER_WIDTH):
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMouseTracking(True)
        self._theme_name = theme_name
        self._anchor: QWidget | None = None

        body_layout = QVBoxLayout(self)
        body_layout.setContentsMargins(1, 1, 1, 1)  # 边框画在 paintEvent
        body_layout.addWidget(content)

        self.setFixedWidth(width)

    # ── 表面自绘（token-monitor 弹层表面）──
    def paintEvent(self, ev):
        t = theme.tokens(self._theme_name)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        painter.setPen(QPen(QColor(t["line_strong"]), 1))
        painter.setBrush(QColor(t["popover_bg"]))
        painter.drawRoundedRect(rect, 7, 7)

    def enterEvent(self, ev):
        cancel_close()
        super().enterEvent(ev)

    def leaveEvent(self, ev):
        schedule_close()
        super().leaveEvent(ev)


def show_for(
    anchor: QWidget,
    content: QWidget,
    theme_name: str,
    width: int = POPOVER_WIDTH,
    delay_ms: int = 0,
) -> None:
    """在 anchor 附近弹出 content（同屏单例：新开先关旧）。

    delay_ms > 0 时为打开延迟（整格悬停防误触）；延迟期间再次调用
    show_for 会重置计时。
    """
    global _ACTIVE, _OPEN_TIMER  # noqa: PLW0603
    cancel_close()

    def _open():
        global _ACTIVE, _OPEN_TIMER  # noqa: PLW0603
        _OPEN_TIMER = None
        if _ACTIVE is not None:
            old = _ACTIVE
            _ACTIVE = None
            old.close()
            old.deleteLater()
        if not anchor.isVisible():
            return
        pop = HoverPopover(theme_name, content, width)
        # 触发器销毁（换页/重建格子）时弹层必须跟着关
        anchor.destroyed.connect(_close_active)
        pop._anchor = anchor  # noqa: SLF001
        pop.adjustSize()
        screen = _screen_for(anchor)
        pos, _above = popup_position(
            _anchor_global_rect(anchor), QRect(0, 0, pop.width(), pop.height()), screen
        )
        # 垂直超高时夹取（内容可滚动场景不适用，当前内容都是短摘要）
        pop.move(pos)
        pop.show()
        _ACTIVE = pop

    if delay_ms <= 0:
        _open()
        return
    if _OPEN_TIMER is not None:
        _OPEN_TIMER.stop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(_open)
    timer.start(delay_ms)
    _OPEN_TIMER = timer


# ── 内容构建（settings-help-popover 的排版语言：标题 + 键值行 + 底注）──────


def _label(text: str, object_name: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName(object_name)
    lbl.setWordWrap(True)
    lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
    return lbl


def event_detail_widget(event: dict, theme_name: str) -> QWidget:
    """单条日程的悬停详情：标题 / 时间 / 地点 / 状态 / 组织者 / 描述。"""
    box = QFrame()
    box.setObjectName("popoverBody")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(5)

    summary = event.get("summary") or "(无标题)"
    layout.addWidget(_label(summary, "popoverTitle"))

    start = models_event.parse_event_time(event.get("start_time", {}))
    end = models_event.parse_event_time(event.get("end_time", {}))
    all_day = "date" in (event.get("start_time") or {})
    if all_day:
        time_text = start.strftime("%m月%d日") + " · 全天"
    elif start.date() == end.date():
        time_text = f"{start.strftime('%m月%d日 %H:%M')} – {end.strftime('%H:%M')}"
    else:
        time_text = f"{start.strftime('%m月%d日 %H:%M')} – {end.strftime('%m月%d日 %H:%M')}"
    layout.addWidget(_label(time_text, "popoverValue"))

    now = datetime.now()
    if all_day:
        status = ""
    elif now < start:
        status = "未开始"
    elif now <= end:
        status = "进行中"
    else:
        status = "已结束"
    extras: list[tuple[str, str]] = []
    if status:
        extras.append(("状态", status))
    recurring = bool(event.get("_is_recurring_instance") or models_event.has_recurrence(event))
    if recurring:
        extras.append(("重复", "重复日程"))
    location = event.get("location")
    if isinstance(location, dict) and location.get("name"):
        extras.append(("地点", str(location["name"])))
    organizer = event.get("event_organizer")
    if isinstance(organizer, dict) and organizer.get("display_name"):
        extras.append(("组织者", str(organizer["display_name"])))
    vchat = event.get("vchat")
    if isinstance(vchat, dict) and vchat.get("meeting_url"):
        extras.append(("视频会议", "含会议链接"))
    for key, val in extras:
        row = QHBoxLayout()
        row.setSpacing(10)
        key_lbl = _label(key, "popoverKey")
        val_lbl = _label(val, "popoverValue")
        key_lbl.setFixedWidth(56)
        row.addWidget(key_lbl)
        row.addWidget(val_lbl, 1)
        layout.addLayout(row)

    desc = (event.get("description") or "").strip()
    if desc:
        desc = desc if len(desc) <= 160 else desc[:160] + "…"
        layout.addWidget(_label(desc, "popoverDesc"))
    return box


def day_summary_widget(date: datetime, events: list[dict], theme_name: str) -> QWidget:
    """月视图日格的悬停摘要：当天全部日程（最多列 6 条）。"""
    box = QFrame()
    box.setObjectName("popoverBody")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    weekday = "一二三四五六日"[date.weekday()]
    layout.addWidget(_label(f"{date.month}月{date.day}日 周{weekday}", "popoverTitle"))

    if not events:
        layout.addWidget(_label("当天没有日程", "popoverMuted"))
        return box

    for ev in events[:6]:
        start = models_event.parse_event_time(ev.get("start_time", {}))
        all_day = "date" in (ev.get("start_time") or {})
        time_text = "全天" if all_day else start.strftime("%H:%M")
        row = QHBoxLayout()
        row.setSpacing(8)
        dot = QLabel("●")
        dot.setObjectName("popoverDot")
        dot.setFixedWidth(12)
        row.addWidget(dot)
        time_lbl = _label(time_text, "popoverKey")
        time_lbl.setFixedWidth(40)
        row.addWidget(time_lbl)
        title = (ev.get("summary") or "(无标题)").strip()
        if len(title) > 22:
            title = title[:22] + "…"
        row.addWidget(_label(title, "popoverValue"), 1)
        layout.addLayout(row)

    if len(events) > 6:
        layout.addWidget(_label(f"还有 {len(events) - 6} 项日程…", "popoverMuted"))
    return box
