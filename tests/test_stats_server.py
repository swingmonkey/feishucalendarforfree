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
