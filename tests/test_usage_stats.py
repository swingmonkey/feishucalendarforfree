import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import usage_stats


class _MemoryConfig:
    def __init__(self, values=None):
        self._data = values or {}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def test_ensure_install_id_generates_and_reuses_value():
    cfg = _MemoryConfig()
    first = usage_stats.ensure_install_id(cfg)
    second = usage_stats.ensure_install_id(cfg)
    assert len(first) == 32
    assert first == second
    assert int(first, 16) >= 0


def test_heartbeat_posts_expected_payload_and_parses_response():
    response = {"cumulative_users": 7, "active_users_30d": 3}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(response).encode()

    with mock.patch.object(usage_stats, "urlopen", return_value=_Response()) as m:
        result = usage_stats.heartbeat(
            "0123456789abcdef0123456789abcdef",
            "2.1.3",
            "win32",
        )

    assert result == response
    request = m.call_args.args[0]
    assert request.full_url.endswith("/v1/heartbeat")
    assert json.loads(request.data.decode()) == {
        "install_id": "0123456789abcdef0123456789abcdef",
        "version": "2.1.3",
        "platform": "win32",
    }


def test_fetch_stats_returns_none_on_network_error():
    with mock.patch.object(usage_stats, "urlopen", side_effect=OSError("offline")):
        assert usage_stats.fetch_stats() is None


def test_stats_worker_emits_result():
    app = QApplication.instance() or QApplication([])
    response = {"cumulative_users": 9, "active_users_30d": 4}
    with mock.patch.object(usage_stats, "fetch_stats", return_value=response):
        worker = usage_stats.StatsWorker()
        received = []
        worker.result.connect(received.append)
        worker.run()
        app.processEvents()
    assert received == [response]


def test_stats_worker_does_not_abort_process_while_request_is_running():
    """A slow request must not leave a QThread that aborts interpreter exit."""
    root = Path(__file__).resolve().parents[1]
    script = """
import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication

import usage_stats

app = QCoreApplication([])
usage_stats.fetch_stats = lambda: time.sleep(30)
worker = usage_stats.StatsWorker()
worker.start()
time.sleep(0.2)
print("exiting")
"""
    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "exiting" in completed.stdout
