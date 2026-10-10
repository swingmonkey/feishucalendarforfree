import gc
import sys

from PySide6.QtWidgets import QApplication

_app = None


def pytest_sessionstart(session):
    global _app
    _app = QApplication.instance() or QApplication(sys.argv[:1])


def pytest_sessionfinish(session, exitstatus):
    global _app
    gc.collect()
    _app = None
    gc.collect()
