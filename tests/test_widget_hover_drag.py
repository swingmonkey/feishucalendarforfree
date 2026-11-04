"""GridEventLabel 的悬停接线 + FloatingSurface 的拖拽/点击判定。

两条都是 v2.11.x 引入的回归：

· ``GridEventLabel.__init__`` 把 ``config`` 传给了 ``_apply_color()`` 却没存到
  ``self._config``，``_theme_name()`` 每次抛 ``AttributeError``——月视图日程条的
  悬停详情从来没生效过，异常还压在 Qt 事件处理器里。
· ``FloatingSurface.mouseReleaseEvent`` 用「松手时的窗口位置」算位移，可窗口在
  ``mouseMoveEvent`` 里已经被移到 ``global - offset``，于是位移恒等于 0，
  每次拖拽结束都当点击、弹出主窗口。
"""

import sys

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import widgets

app = QApplication.instance() or QApplication(sys.argv[:1])


class _Cfg:
    """只回答 theme 的最小配置替身，避免碰真实用户配置。"""

    def __init__(self, name: str = "light"):
        self._name = name

    def get(self, key, default=None):
        return self._name if key == "theme" else default


def _ev() -> dict:
    return {
        "event_id": "e1",
        "summary": "周例会",
        "start_time": {"datetime": "2026-11-04T10:00:00+08:00"},
        "end_time": {"datetime": "2026-11-04T11:00:00+08:00"},
    }


# ── GridEventLabel：主题读取 ────────────────────────────────────────────────


def test_grid_event_label_keeps_config():
    lbl = widgets.GridEventLabel(_ev(), config=_Cfg("light"))
    assert lbl._theme_name() == "light"


def test_grid_event_label_defaults_to_dark_without_config():
    lbl = widgets.GridEventLabel(_ev())
    assert lbl._theme_name() == "dark"


# ── FloatingSurface：拖拽 vs 点击 ──────────────────────────────────────────


def _mouse(kind, x, y, gx, gy, buttons=Qt.MouseButton.LeftButton):
    return QMouseEvent(
        kind,
        QPointF(x, y),
        QPointF(gx, gy),
        Qt.MouseButton.LeftButton,
        buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def _surface():
    s = widgets.FloatingSurface()
    s.resize(200, 100)
    s.move(100, 100)
    s.show()
    app.processEvents()
    return s


def test_drag_release_does_not_activate():
    """拖动 100px 后松手：这是拖拽，不该弹主窗口。"""
    s = _surface()
    fired = []
    s.activated.connect(lambda: fired.append(True))
    try:
        s.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 10, 10, 110, 110))
        s.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 10, 10, 210, 210))
        s.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 10, 10, 210, 210))
        assert fired == []
    finally:
        s.close()
        s.deleteLater()
        app.processEvents()


def test_click_without_movement_activates():
    """原地点击（位移 2px）仍然要打开主窗口。"""
    s = _surface()
    fired = []
    s.activated.connect(lambda: fired.append(True))
    try:
        s.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 10, 10, 110, 110))
        s.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 10, 10, 112, 111))
        assert fired == [True]
    finally:
        s.close()
        s.deleteLater()
        app.processEvents()
