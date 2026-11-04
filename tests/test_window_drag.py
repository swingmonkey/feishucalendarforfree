"""顶栏拖动：交互控件放行，背板/标签/空隙都是拖动把手。

原先「childAt is None 才拖」在顶栏几乎永远不成立——布局背板 QWidget
也是 childAt 的命中结果，窗口实际拖不动（2026-11-04 用户反馈）。
"""

import sys

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

import main_window as mw

app = QApplication.instance() or QApplication(sys.argv[:1])


def _press_event(x=50.0, y=20.0, gx=1500.0, gy=600.0):
    return QMouseEvent(
        __import__("PySide6.QtCore", fromlist=["QEvent"]).QEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(gx, gy),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# ── 判定函数 ───────────────────────────────────────────────────────────────


def test_interactive_children_block_drag():
    assert mw._is_interactive_child(QPushButton("x"))
    assert mw._is_interactive_child(QLineEdit())
    assert not mw._is_interactive_child(QLabel("logo"))
    assert not mw._is_interactive_child(QWidget())  # 布局背板
    assert not mw._is_interactive_child(None)  # 控件间空隙


# ── mousePressEvent 接线 ───────────────────────────────────────────────────


def _make_window(monkeypatch, tmp_path):
    import config as config_module
    import event_store
    from config import Config
    from lark_cli_async import LarkCliAsync

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = Config()
    conn = event_store.connect(tmp_path / "events.db")
    monkeypatch.setattr(LarkCliAsync, "fetch_agenda", lambda self, *a, **kw: None)
    win = mw.MainWindow(cfg, store=conn)
    win.refresh_timer.stop()
    return win, conn


def test_press_on_backdrop_starts_drag(monkeypatch, tmp_path):
    win, conn = _make_window(monkeypatch, tmp_path)
    try:
        # childAt 命中背板（非交互类）→ 记录拖动偏移
        monkeypatch.setattr(win, "childAt", lambda p: QWidget())
        win.mousePressEvent(_press_event(gx=1500, gy=600))
        assert win._drag_offset is not None
        win._drag_offset = None
    finally:
        win.dispose()
        win.deleteLater()
        conn.close()
        app.processEvents()


def test_press_on_button_does_not_drag(monkeypatch, tmp_path):
    win, conn = _make_window(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(win, "childAt", lambda p: QPushButton())
        win.mousePressEvent(_press_event())
        assert win._drag_offset is None
    finally:
        win.dispose()
        win.deleteLater()
        conn.close()
        app.processEvents()


def test_press_outside_titlebar_ignores_drag(monkeypatch, tmp_path):
    win, conn = _make_window(monkeypatch, tmp_path)
    try:
        monkeypatch.setattr(win, "childAt", lambda p: None)
        win.mousePressEvent(_press_event(y=300.0))  # 内容区
        assert win._drag_offset is None
    finally:
        win.dispose()
        win.deleteLater()
        conn.close()
        app.processEvents()
