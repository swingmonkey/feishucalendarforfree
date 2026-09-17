# Silent Update, Pin, Usage Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v2.1.3 with safe background Windows updates, unified always-on-top controls, and anonymous install/active-user statistics shown in About.

**Architecture:** The desktop app generates a local random install ID and sends a background heartbeat to a small stdlib HTTP/SQLite service hosted on HP. Windows updates download and verify into a pending file, then apply on the next startup. Pin state stays in `config.json` and is exposed through the overflow menu, tray menu, and Appearance settings.

**Tech Stack:** Python 3.10+, PySide6, `urllib`, `sqlite3`, `ThreadingHTTPServer`, pytest, GitHub Actions, Nginx, systemd.

## Global Constraints

- Target release version is exactly `2.1.3`.
- Desktop runtime dependencies must remain limited to existing `requirements.txt`.
- Silent EXE replacement only runs when `sys.frozen`, `sys.platform == "win32"`, an EXE asset exists, and SHA-256 verification succeeds.
- Statistics use a random install ID only; never send or store Feishu account data, calendar data, hostnames, MAC addresses, IP addresses, or device fingerprints.
- Store only `sha256(install_id + pepper)` on the server.
- Statistics and update failures must never block startup or show an error dialog.
- Statistics endpoint is `https://www.airtraffic.site/feishu-calendar-stats`.
- Use PowerShell on this Windows machine; do not invoke Bash locally.
- Run Qt tests with `QT_QPA_PLATFORM=offscreen`.

---

## File Structure

Create:

- `usage_stats.py`: install ID, heartbeat, stats fetch, background workers.
- `stats_server/__init__.py`: server package marker.
- `stats_server/app.py`: HTTP routes, validation, SQLite storage.
- `stats_server/requirements.txt`: intentionally contains only a comment because the service uses the standard library.
- `stats_server/feishu-calendar-stats.service`: systemd unit template.
- `stats_server/nginx-location.conf`: Nginx location snippet.
- `stats_server/README.md`: deployment and operations instructions.
- `tests/test_usage_stats.py`: client and worker tests.
- `tests/test_stats_server.py`: API and database tests.

Modify:

- `config.py`: add and validate `install_id`.
- `updater.py`: add pending-update download, verification, metadata, and apply functions.
- `main.py`: apply pending update before UI startup and send heartbeat in the background.
- `main_window.py`: expose pin state changes and add an update-ready Toast.
- `settings_dialog.py`: add Appearance pin control and About usage statistics.
- `tests/test_updater.py`: cover pending update behavior.
- `tests/test_theme_ui.py`: cover tray and settings pin controls.
- `tests/test_refactor_features.py`: cover About statistics states.
- `build_windows.ps1`: add `usage_stats` hidden import.
- `build_macos.sh`: add `usage_stats` hidden import.
- `README.md`: document new behavior, privacy, and stats deployment.
- `__version__.py`: set `APP_VERSION = "2.1.3"`.

---

### Task 1: Persist the Anonymous Install ID

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: existing `Config.DEFAULTS` and `_validated`.
- Produces: `Config.get("install_id") -> str`, always either empty or 32-64 lowercase hexadecimal characters.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_config.py`:

```python
def test_install_id_valid_value_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    install_id = "0123456789abcdef0123456789abcdef"
    (tmp_path / "config.json").write_text(
        json.dumps({"install_id": install_id}),
        encoding="utf-8",
    )
    cfg = config_module.Config()
    assert cfg.get("install_id") == install_id


def test_install_id_invalid_value_is_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({"install_id": "not-an-id"}),
        encoding="utf-8",
    )
    cfg = config_module.Config()
    assert cfg.get("install_id") == ""
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_config.py -q
```

Expected: FAIL because `install_id` is not in `DEFAULTS`.

- [ ] **Step 3: Implement validation**

Add `"install_id": ""` to `Config.DEFAULTS`. In `_validated`, add:

```python
elif key == "install_id":
    if (
        not isinstance(value, str)
        or not 32 <= len(value.strip()) <= 64
        or any(ch not in "0123456789abcdef" for ch in value.strip().lower())
    ):
        value = ""
    else:
        value = value.strip().lower()
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add config.py tests/test_config.py
git commit -m "feat: 增加匿名安装标识配置"
```

---

### Task 2: Implement the Statistics Client

**Files:**
- Create: `usage_stats.py`
- Create: `tests/test_usage_stats.py`

**Interfaces:**
- Consumes: `Config.get`, `Config.set`.
- Produces:
  - `ensure_install_id(config: Config) -> str`
  - `heartbeat(install_id: str, version: str, platform: str, timeout: int = 6) -> dict | None`
  - `fetch_stats(timeout: int = 6) -> dict | None`
  - `HeartbeatWorker(install_id: str, version: str, platform: str)`
  - `StatsWorker()`
  - Both workers emit `result = Signal(object)`.

- [ ] **Step 1: Write failing tests**

Create `tests/test_usage_stats.py`:

```python
import json
import os
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import usage_stats
from config import Config


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
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_usage_stats.py -q
```

Expected: FAIL because `usage_stats` does not exist.

- [ ] **Step 3: Implement the client**

Create `usage_stats.py` with:

```python
"""Anonymous install heartbeat and aggregate usage statistics."""

import json
import logging
import sys
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import QThread, Signal

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
    except (HTTPError, URLError, OSError, ValueError, json.JSONDecodeError) as exc:
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


class HeartbeatWorker(QThread):
    result = Signal(object)

    def __init__(self, install_id: str, version: str, platform: str):
        super().__init__()
        self.install_id = install_id
        self.version = version
        self.platform = platform

    def run(self):
        self.result.emit(
            heartbeat(self.install_id, self.version, self.platform)
        )


class StatsWorker(QThread):
    result = Signal(object)

    def run(self):
        self.result.emit(fetch_stats())
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_usage_stats.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add usage_stats.py tests/test_usage_stats.py
git commit -m "feat: 增加匿名使用统计客户端"
```

---

### Task 3: Implement the Statistics Server

**Files:**
- Create: `stats_server/__init__.py`
- Create: `stats_server/app.py`
- Create: `stats_server/requirements.txt`
- Create: `tests/test_stats_server.py`

**Interfaces:**
- Consumes: JSON heartbeat bodies with `install_id`, `version`, and `platform`.
- Produces:
  - `StatsStore(db_path: str, pepper: str)` with `record_heartbeat(payload) -> dict`
  - `StatsStore.get_stats() -> dict`
  - `create_server(host: str, port: int, db_path: str, pepper: str) -> ThreadingHTTPServer`
  - Routes `/health`, `/v1/heartbeat`, `/v1/stats`.

- [ ] **Step 1: Write failing server tests**

Create `tests/test_stats_server.py`:

```python
import json
import sqlite3
import threading
from urllib.request import Request, urlopen

import pytest

from stats_server.app import StatsStore, create_server


@pytest.fixture
def server(tmp_path):
    instance = create_server(
        "127.0.0.1",
        0,
        str(tmp_path / "stats.db"),
        "test-pepper",
    )
    thread = threading.Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    instance.server_close()
    thread.join(timeout=2)


def _request(server, path, payload=None):
    port = server.server_address[1]
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=3) as response:
        return response.status, json.loads(response.read().decode())


def test_health(server):
    status, body = _request(server, "/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_heartbeat_deduplicates_installs(server, tmp_path):
    install_id = "0123456789abcdef0123456789abcdef"
    payload = {"install_id": install_id, "version": "2.1.3", "platform": "win32"}
    _, first = _request(server, "/v1/heartbeat", payload)
    _, second = _request(server, "/v1/heartbeat", payload)
    assert first["cumulative_users"] == 1
    assert second["cumulative_users"] == 1

    with sqlite3.connect(tmp_path / "stats.db") as db:
        stored = db.execute("SELECT install_hash FROM installs").fetchone()[0]
    assert stored != install_id


def test_invalid_heartbeat_returns_400(server):
    with pytest.raises(Exception) as exc:
        _request(
            server,
            "/v1/heartbeat",
            {"install_id": "bad", "version": "2.1.3", "platform": "win32"},
        )
    assert "400" in str(exc.value)


def test_stats_counts_active_window(tmp_path):
    store = StatsStore(str(tmp_path / "stats.db"), "pepper")
    store.record_heartbeat(
        {
            "install_id": "a" * 32,
            "version": "2.1.3",
            "platform": "win32",
        }
    )
    with sqlite3.connect(tmp_path / "stats.db") as db:
        db.execute(
            "UPDATE installs SET last_seen = last_seen - ?",
            (31 * 24 * 60 * 60,),
        )
    assert store.get_stats()["active_users_30d"] == 0
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_stats_server.py -q
```

Expected: FAIL because `stats_server.app` does not exist.

- [ ] **Step 3: Implement the server**

Create `stats_server/__init__.py` as an empty file.

Create `stats_server/app.py` with:

```python
"""Small anonymous usage statistics API using only the Python standard library."""

import argparse
import hashlib
import json
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VALID_PLATFORMS = {"win32", "darwin"}
MAX_BODY = 4096


def _valid_install_id(value) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip().lower()
    return 32 <= len(value) <= 64 and all(ch in "0123456789abcdef" for ch in value)


class StatsStore:
    def __init__(self, db_path: str, pepper: str):
        self.db_path = db_path
        self.pepper = pepper
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=5)

    def _init_db(self):
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS installs (
                    install_hash TEXT PRIMARY KEY,
                    first_seen INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    app_version TEXT NOT NULL,
                    platform TEXT NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_installs_last_seen "
                "ON installs(last_seen)"
            )

    def _hash(self, install_id: str) -> str:
        value = (self.pepper + install_id.strip().lower()).encode("utf-8")
        return hashlib.sha256(value).hexdigest()

    def record_heartbeat(self, payload: dict):
        install_id = payload.get("install_id")
        version = payload.get("version")
        platform = payload.get("platform")
        if not _valid_install_id(install_id):
            raise ValueError("invalid install_id")
        if not isinstance(version, str) or not 1 <= len(version.strip()) <= 32:
            raise ValueError("invalid version")
        if platform not in VALID_PLATFORMS:
            raise ValueError("invalid platform")

        now = int(time.time())
        install_hash = self._hash(install_id)
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO installs
                    (install_hash, first_seen, last_seen, app_version, platform)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(install_hash) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    app_version = excluded.app_version,
                    platform = excluded.platform
                """,
                (install_hash, now, now, version.strip(), platform),
            )
        return self.get_stats()

    def get_stats(self):
        cutoff = int(time.time()) - 30 * 24 * 60 * 60
        with self._connect() as db:
            total = db.execute("SELECT COUNT(*) FROM installs").fetchone()[0]
            active = db.execute(
                "SELECT COUNT(*) FROM installs WHERE last_seen >= ?",
                (cutoff,),
            ).fetchone()[0]
        return {
            "cumulative_users": int(total),
            "active_users_30d": int(active),
            "generated_at": int(time.time()),
        }


class StatsHandler(BaseHTTPRequestHandler):
    store: StatsStore

    def log_message(self, format, *args):
        return

    def _send(self, status: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok"})
        elif self.path == "/v1/stats":
            self._send(200, self.store.get_stats())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/heartbeat":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > MAX_BODY:
                raise ValueError("invalid body size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("body must be an object")
            result = self.store.record_heartbeat(payload)
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"error": "invalid request"})
            return
        self._send(200, result)


def create_server(host: str, port: int, db_path: str, pepper: str):
    handler = type(
        "StatsHandlerWithStore",
        (StatsHandler,),
        {"store": StatsStore(db_path, pepper)},
    )
    return ThreadingHTTPServer((host, port), handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--db", required=True)
    parser.add_argument("--pepper-file", required=True)
    args = parser.parse_args()

    pepper_path = Path(args.pepper_file)
    if pepper_path.exists():
        pepper = pepper_path.read_text(encoding="utf-8").strip()
    else:
        pepper = __import__("secrets").token_hex(32)
        pepper_path.write_text(pepper + "\n", encoding="utf-8")
        pepper_path.chmod(0o600)
    if not pepper:
        raise SystemExit("empty pepper file")

    server = create_server(args.host, args.port, args.db, pepper)
    print(f"feishu-calendar-stats listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
```

Create `stats_server/requirements.txt` with:

```text
# No third-party packages: the service uses Python's standard library.
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_stats_server.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add stats_server tests/test_stats_server.py
git commit -m "feat: 增加匿名使用统计服务"
```

---

### Task 4: Add About-Page Statistics and Appearance Pin Control

**Files:**
- Modify: `settings_dialog.py`
- Modify: `main_window.py`
- Test: `tests/test_refactor_features.py`
- Test: `tests/test_theme_ui.py`

**Interfaces:**
- Consumes: `usage_stats.StatsWorker`, `Config.get`, `Config.set`.
- Produces:
  - `SettingsDialog.pin_changed = Signal(bool)`
  - `SettingsDialog.pin_check`
  - `SettingsDialog.usage_total_label`
  - `SettingsDialog.usage_active_label`
  - `SettingsDialog._on_stats_result(stats)`
- MainWindow consumes `pin_changed` and applies it immediately.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_refactor_features.py`:

```python
class _FakeStatsWorker(QObject):
    result = Signal(object)

    def __init__(self, result=None, parent=None):
        super().__init__(parent)
        self._result = result

    def start(self):
        QTimer.singleShot(0, lambda: self.result.emit(self._result))


def test_settings_about_shows_usage_stats(monkeypatch, cfg):
    monkeypatch.setattr(settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((True, True), parent))
    monkeypatch.setattr(
        settings_dialog.usage_stats,
        "StatsWorker",
        lambda parent=None: _FakeStatsWorker(
            {"cumulative_users": 12, "active_users_30d": 5},
            parent,
        ),
    )
    dlg = settings_dialog.SettingsDialog(cfg)
    app.processEvents()
    assert "12" in dlg.usage_total_label.text()
    assert "5" in dlg.usage_active_label.text()
    dlg.close()


def test_settings_about_handles_stats_unavailable(monkeypatch, cfg):
    monkeypatch.setattr(settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker((True, True), parent))
    monkeypatch.setattr(
        settings_dialog.usage_stats,
        "StatsWorker",
        lambda parent=None: _FakeStatsWorker(None, parent),
    )
    dlg = settings_dialog.SettingsDialog(cfg)
    app.processEvents()
    assert "暂不可用" in dlg.usage_status_label.text()
    dlg.close()
```

Add to `tests/test_theme_ui.py`:

```python
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
    monkeypatch.setattr(settings_dialog, "AuthStatusWorker", lambda parent: _FakeStatusWorker(parent))
    monkeypatch.setattr(settings_dialog.usage_stats, "StatsWorker", lambda parent=None: _FakeStatsWorker(parent))
    config = _MemoryConfig({"pin_to_top": True})
    dialog = settings_dialog.SettingsDialog(config)
    received = []
    dialog.pin_changed.connect(received.append)
    dialog.pin_check.setChecked(False)
    assert config.get("pin_to_top") is False
    assert received == [False]
    dialog.close()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_refactor_features.py tests/test_theme_ui.py -q
```

Expected: FAIL because `StatsWorker`, `pin_check`, and usage labels do not exist.

- [ ] **Step 3: Implement settings UI**

In `settings_dialog.py`:

```python
import usage_stats

class SettingsDialog(QDialog):
    settings_changed = Signal()
    login_succeeded = Signal()
    pin_changed = Signal(bool)

    def __init__(...):
        ...
        self._stats_worker = None
        ...
        self._start_auth_check()
        self._start_stats_load()
```

Add to Appearance:

```python
self.pin_check = QCheckBox("窗口置顶显示")
self.pin_check.setChecked(self.config.get("pin_to_top", True))
self.pin_check.stateChanged.connect(self._on_pin_changed)
appearance_layout.addWidget(self.pin_check)
```

Add to About:

```python
usage_group = QGroupBox("使用情况")
usage_layout = QVBoxLayout(usage_group)
self.usage_total_label = QLabel("正在获取使用数据…")
self.usage_total_label.setObjectName("detailValue")
self.usage_active_label = QLabel("")
self.usage_active_label.setObjectName("detailValue")
self.usage_status_label = QLabel("匿名统计，不包含飞书账号、日程内容和设备标识。")
self.usage_status_label.setObjectName("detailLabel")
self.usage_status_label.setWordWrap(True)
usage_layout.addWidget(self.usage_total_label)
usage_layout.addWidget(self.usage_active_label)
usage_layout.addWidget(self.usage_status_label)
layout.addWidget(usage_group)
```

Add methods:

```python
def _start_stats_load(self):
    self.usage_status_label.setText("正在获取使用数据…")
    self._stats_worker = usage_stats.StatsWorker(self)
    self._stats_worker.result.connect(self._on_stats_result)
    self._stats_worker.start()

def _on_stats_result(self, stats):
    if not stats:
        self.usage_total_label.setText("")
        self.usage_active_label.setText("")
        self.usage_status_label.setText("统计暂不可用")
        return
    total = int(stats.get("cumulative_users", 0))
    active = int(stats.get("active_users_30d", 0))
    self.usage_total_label.setText(f"累计使用人数：{total} 人")
    self.usage_active_label.setText(f"近 30 天活跃：{active} 人")
    self.usage_status_label.setText(
        "匿名统计，不包含飞书账号、日程内容和设备标识。"
    )

def _on_pin_changed(self, state):
    pinned = state == Qt.CheckState.Checked.value
    self.config.set("pin_to_top", pinned)
    self.pin_changed.emit(pinned)
    self.settings_changed.emit()
```

Add `_stats_worker` to `closeEvent` cleanup.

In `main_window.py` connect:

```python
dialog.pin_changed.connect(self._on_pin_setting_changed)
```

Add:

```python
def _on_pin_setting_changed(self, pinned: bool):
    self._set_pinned(pinned)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_refactor_features.py tests/test_theme_ui.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add settings_dialog.py main_window.py tests/test_refactor_features.py tests/test_theme_ui.py
git commit -m "feat: 完善置顶入口与使用人数展示"
```

---

### Task 5: Add Pending Update Download and Apply

**Files:**
- Modify: `updater.py`
- Modify: `tests/test_updater.py`

**Interfaces:**
- Consumes: existing `find_exe_asset`, `download_sha256_sums`, `download`, `compute_sha256`, `parse_version`.
- Produces:
  - `pending_update_path() -> str`
  - `pending_metadata_path() -> str`
  - `prepare_pending_update(release: dict, progress_cb=None) -> tuple[bool, str]`
  - `apply_pending_update(current_version: str = APP_VERSION) -> bool`
  - `SilentUpdateWorker(release: dict)` with `finished = Signal(bool, str)`.

- [ ] **Step 1: Write failing updater tests**

Add to `tests/test_updater.py`:

```python
def test_prepare_pending_update_writes_verified_file(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    exe.write_bytes(b"old")
    monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updater.sys, "platform", "win32")
    monkeypatch.setattr(updater.sys, "executable", str(exe))
    monkeypatch.setattr(
        updater,
        "download_sha256_sums",
        lambda release: {"FeishuCalendar.exe": updater.compute_sha256(str(_new_file))},
    )
    release = {
        "tag": "v2.1.3",
        "assets": [{"name": "FeishuCalendar.exe", "browser_download_url": "u"}],
    }
    _new_file = tmp_path / "new.exe"
    _new_file.write_bytes(b"new")

    def fake_download(url, dest, progress_cb=None, timeout=60):
        with open(dest, "wb") as f:
            f.write(_new_file.read_bytes())

    monkeypatch.setattr(updater, "download", fake_download)
    ok, message = updater.prepare_pending_update(release)
    assert ok is True
    assert "2.1.3" in message
    assert open(updater.pending_update_path(), "rb").read() == b"new"
    metadata = json.loads(open(updater.pending_metadata_path(), encoding="utf-8").read())
    assert metadata["tag"] == "v2.1.3"


def test_apply_pending_update_replaces_executable(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    pending = tmp_path / "app.exe.pending"
    meta = tmp_path / "app.exe.pending.json"
    exe.write_bytes(b"old")
    pending.write_bytes(b"new")
    meta.write_text(
        json.dumps(
            {
                "tag": "v2.1.3",
                "asset_name": "FeishuCalendar.exe",
                "sha256": updater.compute_sha256(str(pending)),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updater.sys, "platform", "win32")
    monkeypatch.setattr(updater.sys, "executable", str(exe))
    assert updater.apply_pending_update("2.1.2") is True
    assert exe.read_bytes() == b"new"
    assert not pending.exists()
    assert not meta.exists()


def test_apply_pending_update_rejects_bad_hash(tmp_path, monkeypatch):
    exe = tmp_path / "app.exe"
    pending = tmp_path / "app.exe.pending"
    meta = tmp_path / "app.exe.pending.json"
    exe.write_bytes(b"old")
    pending.write_bytes(b"new")
    meta.write_text(
        json.dumps({"tag": "v2.1.3", "sha256": "0" * 64}),
        encoding="utf-8",
    )
    monkeypatch.setattr(updater.sys, "frozen", True, raising=False)
    monkeypatch.setattr(updater.sys, "platform", "win32")
    monkeypatch.setattr(updater.sys, "executable", str(exe))
    assert updater.apply_pending_update("2.1.2") is False
    assert exe.read_bytes() == b"old"
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_updater.py -q
```

Expected: FAIL because pending update functions do not exist.

- [ ] **Step 3: Implement pending updates**

In `updater.py`, add:

```python
def pending_update_path() -> str:
    return os.path.abspath(sys.executable) + ".pending"


def pending_metadata_path() -> str:
    return pending_update_path() + ".json"


def _write_json_atomic(path: str, payload: dict):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def prepare_pending_update(release: dict, progress_cb=None):
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return False, "当前平台不支持静默更新"
    tag = release.get("tag", "")
    if not is_newer(tag, APP_VERSION):
        return False, "版本无需更新"
    asset = find_exe_asset(release)
    if not asset:
        return False, "未找到 EXE 更新资产"
    expected_hash = download_sha256_sums(release).get(asset.get("name", ""), "")
    if not expected_hash:
        return False, "更新缺少 SHA-256 校验"

    pending = pending_update_path()
    downloading = pending + ".download"
    metadata = pending_metadata_path()
    try:
        download(
            asset["browser_download_url"],
            downloading,
            progress_cb=progress_cb,
        )
        if compute_sha256(downloading).lower() != expected_hash.lower():
            raise ValueError("SHA-256 校验失败")
        os.replace(downloading, pending)
        _write_json_atomic(
            metadata,
            {
                "tag": tag,
                "asset_name": asset.get("name", ""),
                "sha256": expected_hash.lower(),
                "staged_at": int(__import__("time").time()),
            },
        )
        return True, f"新版本 {tag} 已准备好"
    except Exception as exc:
        for path in (downloading, pending, metadata):
            try:
                os.unlink(path)
            except OSError:
                pass
        return False, str(exc)


def apply_pending_update(current_version: str = APP_VERSION) -> bool:
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return False
    pending = pending_update_path()
    metadata_path = pending_metadata_path()
    if not os.path.isfile(pending) or not os.path.isfile(metadata_path):
        return False
    try:
        with open(metadata_path, encoding="utf-8") as handle:
            metadata = json.load(handle)
        tag = metadata.get("tag", "")
        expected_hash = metadata.get("sha256", "")
        if not is_newer(tag, current_version):
            return False
        if len(expected_hash) != 64:
            return False
        if compute_sha256(pending).lower() != expected_hash.lower():
            return False

        exe = os.path.abspath(sys.executable)
        old = exe + ".old"
        os.replace(exe, old)
        try:
            os.replace(pending, exe)
        except OSError:
            os.replace(old, exe)
            raise
        os.unlink(metadata_path)
        return True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


class SilentUpdateWorker(QThread):
    finished = Signal(bool, str)

    def __init__(self, release: dict):
        super().__init__()
        self.release = release

    def run(self):
        ok, message = prepare_pending_update(self.release)
        self.finished.emit(ok, message)
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_updater.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add updater.py tests/test_updater.py
git commit -m "feat: 增加后台暂存更新"
```

---

### Task 6: Wire Startup, Tray Pin, and Update Toast

**Files:**
- Modify: `main.py`
- Modify: `main_window.py`
- Test: `tests/test_refactor_features.py`

**Interfaces:**
- Consumes: `apply_pending_update`, `SilentUpdateWorker`, `usage_stats.ensure_install_id`, `usage_stats.HeartbeatWorker`.
- Produces:
  - `MainWindow.notify_update_ready(tag: str)`
  - Tray checkable `pin_action`.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_refactor_features.py`:

```python
def test_update_ready_toast_is_non_modal(w):
    w.notify_update_ready("2.1.3")
    assert w.toast.isVisible()
    assert "2.1.3" in w.toast.msg_label.text()
```

Add to `tests/test_theme_ui.py`:

```python
def test_tray_menu_has_pin_action(monkeypatch):
    from main import TrayApp
    QApplication.instance() or QApplication([])
    config = _MemoryConfig({"pin_to_top": True})
    monkeypatch.setattr("main.Config", lambda: config)
    monkeypatch.setattr("main.create_app_icon", lambda: QIcon())
    monkeypatch.setattr("main.MainWindow.show", lambda self: None)
    app = TrayApp(["test"])
    try:
        texts = [action.text() for action in app.tray.contextMenu().actions()]
        assert any("窗口置顶" in text for text in texts)
    finally:
        app.tray.hide()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_refactor_features.py tests/test_theme_ui.py -q
```

Expected: FAIL because `notify_update_ready` and tray pin action do not exist.

- [ ] **Step 3: Implement integration**

In `main_window.py` add:

```python
def notify_update_ready(self, tag: str):
    self.toast.show_message(
        f"新版本 v{tag.lstrip('vV')} 已准备好，将在下次启动时安装",
        kind="success",
        duration=6000,
    )
```

In `main.py`:

```python
import usage_stats

def _setup_tray(self):
    ...
    self.pin_action = QAction("窗口置顶", self)
    self.pin_action.setCheckable(True)
    self.pin_action.setChecked(self.widget._pinned)
    self.pin_action.triggered.connect(self.widget._set_pinned)
    menu.addAction(self.pin_action)
    menu.aboutToShow.connect(
        lambda: self.pin_action.setChecked(self.widget._pinned)
    )

def _on_update_checked(self, release):
    if not release or not updater.is_newer(
        release.get("tag", ""),
        updater.APP_VERSION,
    ):
        return
    if getattr(sys, "frozen", False) and sys.platform == "win32":
        self._silent_update_worker = updater.SilentUpdateWorker(release)
        self._silent_update_worker.finished.connect(
            self._on_silent_update_finished
        )
        self._silent_update_worker.start()
        return
    self.widget.notify_update(release)

def _on_silent_update_finished(self, ok, message):
    if ok:
        tag = self._last_checked_release.get("tag", "")
        self.widget.notify_update_ready(tag)
    elif self._last_checked_release:
        self.widget.notify_update(self._last_checked_release)

def _setup_usage_stats(self):
    from PySide6.QtCore import QTimer

    QTimer.singleShot(6000, self._send_usage_heartbeat)

def _send_usage_heartbeat(self):
    install_id = usage_stats.ensure_install_id(self.config)
    self._usage_worker = usage_stats.HeartbeatWorker(
        install_id,
        APP_VERSION,
        sys.platform,
    )
    self._usage_worker.start()
```

Store `self._last_checked_release = release` in `_on_update_checked`. Call `self._setup_usage_stats()` from `TrayApp.__init__`.

In `main()` before `Config()`:

```python
if updater.apply_pending_update():
    updater.restart_application()
    return
```

- [ ] **Step 4: Run tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest tests/test_refactor_features.py tests/test_theme_ui.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add main.py main_window.py tests/test_refactor_features.py tests/test_theme_ui.py
git commit -m "feat: 接入静默更新托盘置顶与心跳"
```

---

### Task 7: Build Scripts, Documentation, and Version

**Files:**
- Modify: `build_windows.ps1`
- Modify: `build_macos.sh`
- Modify: `README.md`
- Modify: `__version__.py`
- Create: `stats_server/feishu-calendar-stats.service`
- Create: `stats_server/nginx-location.conf`
- Create: `stats_server/README.md`

**Interfaces:**
- Consumes: all previous tasks.
- Produces: v2.1.3 package definition and deployment artifacts.

- [ ] **Step 1: Update build files**

Add `--hidden-import usage_stats` to both PyInstaller command lists.

- [ ] **Step 2: Add deployment files**

Create `stats_server/feishu-calendar-stats.service`:

```ini
[Unit]
Description=Feishu Calendar anonymous usage statistics
After=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/feishu-calendar-stats
ExecStart=/usr/bin/python3 /home/ubuntu/feishu-calendar-stats/app.py --host 127.0.0.1 --port 8010 --db /home/ubuntu/feishu-calendar-stats/stats.db --pepper-file /home/ubuntu/feishu-calendar-stats/pepper
Restart=always
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Create `stats_server/nginx-location.conf`:

```nginx
location ^~ /feishu-calendar-stats/ {
    proxy_pass http://127.0.0.1:8010/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP "";
    proxy_set_header X-Forwarded-For "";
    client_max_body_size 8k;
    access_log off;
}
```

Create `stats_server/README.md` with install, firewall, systemd, Nginx, health check, backup, and privacy commands.

- [ ] **Step 3: Update README and version**

Document:

- Windows pending update behavior.
- Pin controls in overflow menu, tray, and settings.
- About-page user metrics.
- Statistics privacy statement.
- Stats service deployment path and endpoint.

Change:

```python
APP_VERSION = "2.1.3"
```

- [ ] **Step 4: Run compile and tests**

Run:

```powershell
python -m compileall -q . -x "(^|/)(dist|build|\.git)(/|$)"
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q
```

Expected: compile exits 0 and all tests pass.

- [ ] **Step 5: Commit**

```powershell
git add build_windows.ps1 build_macos.sh README.md __version__.py stats_server
git commit -m "release: 准备 v2.1.3 静默更新与使用统计"
```

---

### Task 8: Deploy, Verify, and Release v2.1.3

**Files:**
- Read: `stats_server/README.md`
- Modify server only: `/home/ubuntu/feishu-calendar-stats/`
- Modify server Nginx only: active `www.airtraffic.site` HTTPS server.

**Interfaces:**
- Consumes: committed v2.1.3 code and stats server artifacts.
- Produces: live statistics endpoint and GitHub Release `v2.1.3`.

- [ ] **Step 1: Deploy the stats server before tagging**

Upload `stats_server/app.py` to HP and install the systemd unit. Use an explicit backup of the active Nginx configuration before adding the location snippet.

- [ ] **Step 2: Verify the live endpoint**

Run:

```powershell
$id = [guid]::NewGuid().ToString('N')
$body = @{ install_id = $id; version = '2.1.3'; platform = 'win32' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'https://www.airtraffic.site/feishu-calendar-stats/v1/heartbeat' -ContentType 'application/json' -Body $body
Invoke-RestMethod -Uri 'https://www.airtraffic.site/feishu-calendar-stats/v1/stats'
```

Expected: heartbeat returns integer `cumulative_users` and `active_users_30d`; stats returns the same schema.

- [ ] **Step 3: Run final local verification**

Run:

```powershell
git status --short
python -m compileall -q . -x "(^|/)(dist|build|\.git)(/|$)"
$env:QT_QPA_PLATFORM='offscreen'; python -m pytest -q
```

Expected: clean worktree, compile exit 0, all tests pass.

- [ ] **Step 4: Build Windows locally**

Run:

```powershell
$env:FC_APP_NAME='FeishuCalendar'
powershell -NoProfile -ExecutionPolicy Bypass -File build_windows.ps1
```

Expected: `dist/FeishuCalendar.exe` exists and launch smoke test does not crash.

- [ ] **Step 5: Push and tag**

```powershell
git push origin main
git tag v2.1.3
git push origin v2.1.3
```

- [ ] **Step 6: Verify GitHub Actions and Release**

Wait for the tag workflow. Verify the release has:

- `FeishuCalendar.exe`
- `FeishuCalendar.app.zip`
- `SHA256SUMS`

Download the Release EXE and verify its hash against `SHA256SUMS`.

- [ ] **Step 7: Record the final evidence**

Report:

- Commit and tag.
- Test and compile results.
- Live heartbeat response.
- Release asset names and checksum result.
- Any remaining limitation, especially macOS not supporting silent replacement.
