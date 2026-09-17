"""Anonymous install heartbeat and aggregate usage statistics."""

import json
import logging
import sys
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)

STATS_BASE_URL = "https://www.airtraffic.site/feishu-calendar-stats"
HEARTBEAT_URL = STATS_BASE_URL + "/v1/heartbeat"
STATS_URL = STATS_BASE_URL + "/v1/stats"
USER_AGENT = "FeishuCalendarDesktop-usage/1.0"


def ensure_install_id(config) -> str:
    install_id = config.get("install_id", "")
    if not install_id:
        install_id = uuid.uuid4().hex
        config.set("install_id", install_id)
    return install_id


def _request_json(url: str, payload: dict | None = None, timeout: int = 6):
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, OSError, ValueError) as exc:
        logger.info("Usage statistics request failed: %s", exc)
        return None
    if not isinstance(value, dict):
        return None
    return value


def heartbeat(
    install_id: str,
    version: str,
    platform: str = sys.platform,
    timeout: int = 6,
):
    return _request_json(
        HEARTBEAT_URL,
        {
            "install_id": install_id,
            "version": version,
            "platform": platform,
        },
        timeout=timeout,
    )


def fetch_stats(timeout: int = 6):
    return _request_json(STATS_URL, timeout=timeout)


class _DaemonResultWorker(QObject):
    """Run one request without letting QThread outlive application shutdown."""

    result = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread = None
        self._finished = threading.Event()
        self._interrupted = threading.Event()

    def start(self):
        if self.isRunning():
            return
        self._finished.clear()
        self._interrupted.clear()
        self._thread = threading.Thread(
            target=self._execute,
            name=type(self).__name__,
            daemon=True,
        )
        self._thread.start()

    def _execute(self):
        try:
            self.run()
        except Exception:
            logger.exception("Background usage statistics worker failed")
        finally:
            self._finished.set()

    def _emit_result(self, value):
        if self._interrupted.is_set():
            return
        try:
            self.result.emit(value)
        except RuntimeError:
            # The dialog may have been closed after wait() timed out.
            pass

    def run(self):
        raise NotImplementedError

    def isRunning(self):
        return self._thread is not None and self._thread.is_alive()

    def requestInterruption(self):
        self._interrupted.set()

    def quit(self):
        self._interrupted.set()

    def wait(self, timeout_ms=30000):
        return self._finished.wait(max(0, timeout_ms) / 1000)


class HeartbeatWorker(_DaemonResultWorker):
    def __init__(
        self,
        install_id: str,
        version: str,
        platform: str,
        parent=None,
    ):
        super().__init__(parent)
        self.install_id = install_id
        self.version = version
        self.platform = platform

    def run(self):
        self._emit_result(
            heartbeat(self.install_id, self.version, self.platform)
        )


class StatsWorker(_DaemonResultWorker):
    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        self._emit_result(fetch_stats())
