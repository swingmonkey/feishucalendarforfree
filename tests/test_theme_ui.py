"""Theme and header layout regressions that do not require network access."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QApplication, QFrame, QWidget

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
