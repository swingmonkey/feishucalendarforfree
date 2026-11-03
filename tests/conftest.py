import gc
import sys

import pytest
from PySide6.QtWidgets import QApplication

import event_store

_app = None


def pytest_sessionstart(session):
    global _app
    _app = QApplication.instance() or QApplication(sys.argv[:1])


def pytest_sessionfinish(session, exitstatus):
    global _app
    gc.collect()
    _app = None
    gc.collect()


@pytest.fixture(autouse=True)
def isolated_event_store(tmp_path, monkeypatch):
    """Never let a test write ``events.db`` into the real app directory.

    ``MainWindow`` opens the store with no explicit path, so redirect the
    default location into the test's own tmp dir. Tests that pass an explicit
    path (``test_event_store``) are unaffected.
    """
    monkeypatch.setattr(event_store, "default_db_path", lambda: tmp_path / "events.db")
    return tmp_path / "events.db"
