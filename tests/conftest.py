import os
import sys
import gc

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

_app = None


def pytest_sessionstart(session):
    global _app
    _app = QApplication.instance() or QApplication(sys.argv)


def pytest_sessionfinish(session, exitstatus):
    global _app
    gc.collect()
    if _app is not None:
        _app.close()
        _app = None
