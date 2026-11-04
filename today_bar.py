"""今日条 —— 常驻桌面的低打扰窄条。

主窗口是「我要看日程时才打开」的形态，托盘标题是「不打开也能瞄一眼」的
形态，这个窄条补的是第三种：**一直摆在屏幕上**，只用一行说清今天还剩什么。

刻意做成无边框、置顶、可拖动、可关闭：日历工具不该占用窗口管理器的注意力，
用户把它拖到副屏角落就等于把它忘掉了。
"""

from datetime import datetime

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import reminder as reminder_module
import theme


def _style_for(theme_name: str) -> dict:
    """按主题名拼出窄条的四段 QSS。

    窄条是无 parent 的顶层窗口，吃不到 application 级样式表（styles.get_theme），
    只能自己设。但色值必须从 theme.tokens 取：改造前这里写死了一套飞书旧色板
    （#1F2329/#E4E6EB/#3A3F4B），主窗口换成深色台面后，它是屏幕上唯一还留着
    旧配色的东西，而且切主题时不会跟着变。
    """
    t = theme.tokens(theme_name)
    fs = theme.FONT_SIZE
    return {
        "card": (
            "QFrame#todayBarCard {{ "
            "background-color: {glass}; border: 1px solid {border}; "
            "border-radius: {radius}px; }}".format(
                glass=t["glass_strong"],
                border=t["glass_border"],
                radius=theme.RADIUS["md"],
            )
        ),
        "title": (
            f"color: {t['text_strong']}; font-family: {t['sans']}; "
            f"font-size: {fs['body']}px; font-weight: 600;"
        ),
        "detail": f"color: {t['muted']}; font-family: {t['sans']}; font-size: {fs['sub']}px;",
        "close": (
            f"QPushButton {{ border: none; background: transparent; "
            f"color: {t['muted']}; font-size: {fs['body']}px; }}"
            f"QPushButton:hover {{ color: {t['danger']}; }}"
        ),
    }


class TodayBar(QWidget):
    """Frameless always-on-top strip showing what is left of today."""

    activated = Signal()
    closed = Signal()

    def __init__(self, parent=None, dark: bool = False):
        super().__init__(parent)
        self._drag_offset: QPoint | None = None
        self._theme = "dark" if dark else "light"
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("todayBar")
        self._build_ui()
        self.set_dark(dark)
        self.set_events([], datetime.now())

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame(self)
        self.card.setObjectName("todayBarCard")
        self.card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer.addWidget(self.card)

        row = QHBoxLayout(self.card)
        row.setContentsMargins(12, 7, 8, 7)
        row.setSpacing(8)

        text_column = QVBoxLayout()
        text_column.setContentsMargins(0, 0, 0, 0)
        text_column.setSpacing(0)

        self.primary_label = QLabel("今天没有日程")
        self.primary_label.setObjectName("todayBarPrimary")
        text_column.addWidget(self.primary_label)

        self.detail_label = QLabel("")
        self.detail_label.setObjectName("todayBarDetail")
        self.detail_label.setVisible(False)
        text_column.addWidget(self.detail_label)
        row.addLayout(text_column, 1)

        self.close_btn = QPushButton("✕", self.card)
        self.close_btn.setObjectName("todayBarClose")
        self.close_btn.setFixedSize(18, 18)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self._on_close)
        row.addWidget(self.close_btn, 0, Qt.AlignmentFlag.AlignTop)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(200)
        self.setMaximumWidth(360)

    # ── Appearance ──

    def set_dark(self, dark: bool):
        self.apply_theme("dark" if dark else "light")

    def apply_theme(self, theme_name: str):
        self._theme = "light" if theme_name == "light" else "dark"
        style = _style_for(self._theme)
        self.card.setStyleSheet(style["card"])
        self.primary_label.setStyleSheet(style["title"])
        self.detail_label.setStyleSheet(style["detail"])
        self.close_btn.setStyleSheet(style["close"])

    # ── Content ──

    def set_events(self, events, now: datetime = None):
        """Update the strip from stored events (recurring occurrences included)."""
        now = now or datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        occurrences = reminder_module.collect_occurrences(
            events or [], day_start, day_start.replace(hour=23, minute=59, second=59)
        )
        self.primary_label.setText(reminder_module.tray_summary(events, now))

        found = reminder_module.current_or_next(occurrences, now)
        if found is None:
            self.detail_label.setVisible(False)
            return
        occ, running = found
        remaining = [
            o for o in occurrences if o.start > now and not o.all_day
        ]
        parts = []
        if not running:
            parts.append("下一项 " + reminder_module.format_hhmm(occ.start))
        if remaining:
            parts.append(f"之后还有 {len(remaining)} 项")
        self.detail_label.setText(" · ".join(parts))
        self.detail_label.setVisible(bool(parts))

    # ── Placement ──

    def restore_position(self, x: int, y: int):
        """Place the bar; ``-1`` means "bottom-right of the primary screen"."""
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

    def _on_close(self):
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
