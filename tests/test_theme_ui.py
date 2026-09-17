"""Theme and header layout regressions that do not require network access."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QFrame, QWidget

from app_icon import create_app_icon
from config import Config
from lark_cli_async import LarkCliAsync
from main_window import MainWindow


class _MemoryConfig(Config):
    def __init__(self, values: dict):
        self._data = values

    def save(self):
        pass


def test_header_logo_and_compact_layout():
    app = QApplication.instance() or QApplication([])
    original_fetch = LarkCliAsync.fetch_agenda
    LarkCliAsync.fetch_agenda = lambda self, current_date, monthly=True: self.agenda_fetched.emit([])
    try:
        config = _MemoryConfig(
            {
                "window_width": 480,
                "window_height": 640,
                "window_x": 0,
                "window_y": 0,
                "opacity": 0.95,
                "pin_to_top": False,
                "view_mode": "month",
                "theme": "dark",
                "auto_refresh_interval": 999999,
            }
        )
        window = MainWindow(config)
        window.show()

        try:
            for width, title_visible in ((440, False), (480, True)):
                window.resize(width, 640)
                app.processEvents()
                assert window.width() == width
                assert window.header_logo.size().width() == 44
                assert window.header_logo.size().height() == 44
                logo = window.header_logo.pixmap()
                assert logo.width() / logo.devicePixelRatio() == 40
                assert logo.height() / logo.devicePixelRatio() == 40
                assert window.header_title.isVisible() is title_visible

                header = window.findChild(QFrame, "headerBar")
                widgets = [
                    widget
                    for widget in header.findChildren(QWidget)
                    if widget.isVisible() and widget.width() > 0 and widget.height() > 0
                ]
                rects = {
                    widget: QRect(widget.mapTo(header, QPoint(0, 0)), widget.size())
                    for widget in widgets
                }
                for index, first in enumerate(widgets):
                    for second in widgets[index + 1 :]:
                        if first.isAncestorOf(second) or second.isAncestorOf(first):
                            continue
                        overlap = rects[first].intersected(rects[second])
                        assert overlap.isEmpty(), (
                            f"header widgets overlap at {width}px: "
                            f"{first.objectName()} / {second.objectName()}"
                        )
        finally:
            window.close()
    finally:
        LarkCliAsync.fetch_agenda = original_fetch


def test_window_identity_is_ready_for_taskbar(monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        LarkCliAsync,
        "fetch_agenda",
        lambda self, current_date, monthly=True: self.agenda_fetched.emit([]),
    )
    config = _MemoryConfig(
        {
            "window_width": 480,
            "window_height": 640,
            "window_x": 0,
            "window_y": 0,
            "opacity": 1.0,
            "pin_to_top": False,
            "view_mode": "month",
            "theme": "light",
            "auto_refresh_interval": 999999,
        }
    )
    window = MainWindow(config)
    try:
        assert window.windowTitle() == "飞书日程"
        assert not window.windowIcon().isNull()
        assert window.windowType() == Qt.WindowType.Window

        window.show()
        window.showMinimized()
        app.processEvents()
        assert window.isMinimized()
    finally:
        window.close()


def test_app_icon_uses_trimmed_artwork():
    QApplication.instance() or QApplication([])
    image = create_app_icon().pixmap(64, 64).toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 32:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    width = right - left + 1
    height = bottom - top + 1
    assert width >= image.width() * 0.80
    assert height >= image.height() * 0.60


def test_packaged_ico_uses_enlarged_artwork():
    QApplication.instance() or QApplication([])
    image = QIcon("assets/icon.ico").pixmap(256, 256).toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 64:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    assert right - left + 1 >= image.width() * 0.80
    assert bottom - top + 1 >= image.height() * 0.60


def test_settings_pin_checkbox_updates_config(monkeypatch):
    from PySide6.QtCore import QObject, QTimer, Signal

    import settings_dialog

    class _FakeStatusWorker(QObject):
        checked = Signal(bool, bool)

        def __init__(self, parent=None):
            super().__init__(parent)

        def start(self):
            QTimer.singleShot(0, lambda: self.checked.emit(True, True))

    class _FakeStatsWorker(QObject):
        result = Signal(object)

        def __init__(self, parent=None):
            super().__init__(parent)

        def start(self):
            QTimer.singleShot(0, lambda: self.result.emit(None))

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(
        settings_dialog,
        "AuthStatusWorker",
        lambda parent: _FakeStatusWorker(parent),
    )
    monkeypatch.setattr(
        settings_dialog.usage_stats,
        "StatsWorker",
        lambda parent=None: _FakeStatsWorker(parent),
    )
    config = _MemoryConfig({"pin_to_top": True})
    dialog = settings_dialog.SettingsDialog(config)
    received = []
    dialog.pin_changed.connect(received.append)
    dialog.pin_check.setChecked(False)
    assert config.get("pin_to_top") is False
    assert received == [False]
    dialog.close()


def test_tray_menu_pin_action_tracks_window_state():
    from main import _build_tray_menu

    class _FakeWidget:
        def __init__(self):
            self._pinned = True

        def _set_pinned(self, pinned):
            self._pinned = pinned

        def _show_widget(self):
            pass

        def hide(self):
            pass

        def refresh_events(self):
            pass

        def _on_add_event(self):
            pass

        def open_login(self):
            pass

        def _on_settings(self):
            pass

    QApplication.instance() or QApplication([])
    widget = _FakeWidget()
    menu, pin_action = _build_tray_menu(
        widget,
        lambda: None,
        lambda: None,
        None,
    )

    assert pin_action.isCheckable()
    assert pin_action.isChecked()
    assert any("窗口置顶" in action.text() for action in menu.actions())

    widget._pinned = False
    menu.aboutToShow.emit()
    assert not pin_action.isChecked()
