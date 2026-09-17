"""Small anonymous usage statistics API using only the Python standard library."""

import argparse
import hashlib
import json
import secrets
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
    return 32 <= len(value) <= 64 and all(
        ch in "0123456789abcdef" for ch in value
    )


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
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
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
        pepper = secrets.token_hex(32)
        pepper_path.write_text(pepper + "\n", encoding="utf-8")
        pepper_path.chmod(0o600)
    if not pepper:
        raise SystemExit("empty pepper file")

    server = create_server(args.host, args.port, args.db, pepper)
    print(f"feishu-calendar-stats listening on {args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
