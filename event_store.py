"""Local SQLite fact layer for calendar events.

The app used to keep events in a single in-memory list owned by the main
window, which meant: no offline access, a cold ``node`` subprocess on every
month switch, and no way to tell whether Feishu had dropped an event.

This module is the local source of truth. Views read from here; the lark-cli
sync path only *writes* here. Design constraints:

- Standard library only (``sqlite3``), no new runtime dependencies.
- Every public function takes an explicit connection so it is trivially
  testable without Qt.
- A corrupt database is quarantined and rebuilt instead of blocking startup —
  the remotes re-fill it on the next successful sync.
- Pruning is conservative: a blank snapshot never wipes the cache.
"""

import json
import logging
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from models_event import parse_event_time

logger = logging.getLogger(__name__)

DB_FILENAME = "events.db"

# 与 token-monitor 的滚动窗口一致：本地保留一年多的历史，超出后清掉。
RETENTION_DAYS = 370

DEFAULT_CALENDAR_ID = "primary"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id    TEXT    NOT NULL,
    calendar_id TEXT    NOT NULL DEFAULT 'primary',
    summary     TEXT    NOT NULL DEFAULT '',
    description TEXT    NOT NULL DEFAULT '',
    organizer   TEXT    NOT NULL DEFAULT '',
    start_ts    INTEGER NOT NULL,
    end_ts      INTEGER NOT NULL,
    all_day     INTEGER NOT NULL DEFAULT 0,
    rrule       TEXT    NOT NULL DEFAULT '',
    raw_json    TEXT    NOT NULL,
    updated_at  INTEGER NOT NULL,
    PRIMARY KEY (event_id, calendar_id)
);
CREATE INDEX IF NOT EXISTS idx_events_start ON events(start_ts);
CREATE INDEX IF NOT EXISTS idx_events_end   ON events(end_ts);
CREATE INDEX IF NOT EXISTS idx_events_range ON events(calendar_id, start_ts, end_ts);

CREATE TABLE IF NOT EXISTS sync_ranges (
    calendar_id TEXT    NOT NULL DEFAULT 'primary',
    range_start INTEGER NOT NULL,
    range_end   INTEGER NOT NULL,
    synced_at   INTEGER NOT NULL,
    PRIMARY KEY (range_start, range_end, calendar_id)
);

-- 已发出的提醒（按「某次发生」而非「某个日程」记账）：
-- 每周例会下周一要再提醒一次，而同一场会刷新一分钟后不能重复提醒。
CREATE TABLE IF NOT EXISTS notified (
    event_key TEXT    PRIMARY KEY,
    fired_at  INTEGER NOT NULL
);
"""


# ── Connection lifecycle ─────────────────────────────────────────────────────


def default_db_path() -> Path:
    """Return ``<app dir>/events.db`` (same directory as ``config.json``)."""
    from config import get_app_dir

    return get_app_dir() / DB_FILENAME


def _open(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), timeout=5)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(_SCHEMA)
        # Touch the table so a corrupt file fails here, not on first query.
        conn.execute("SELECT COUNT(*) FROM events").fetchone()
    except sqlite3.DatabaseError:
        conn.close()
        raise
    return conn


def _quarantine(path: Path) -> None:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.corrupt-{stamp}")
    try:
        path.replace(target)
        logger.warning("Quarantined corrupt event store to %s", target)
    except OSError as exc:  # pragma: no cover - filesystem edge case
        logger.error("Could not quarantine %s (%s); recreating in place", path, exc)
        path.unlink(missing_ok=True)
    for suffix in ("-wal", "-shm"):
        path.with_name(path.name + suffix).unlink(missing_ok=True)


def connect(db_path=None) -> sqlite3.Connection:
    """Open (and if needed create) the local event store.

    A corrupt file is moved aside and replaced with an empty store rather than
    raising: the app must always start, and the next sync re-fills the cache.
    """
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _open(path)
    except sqlite3.DatabaseError as exc:
        logger.warning("Event store at %s is unusable (%s); rebuilding", path, exc)
    _quarantine(path)
    return _open(path)


# ── Normalisation ────────────────────────────────────────────────────────────


def _calendar_id(event: dict) -> str:
    value = event.get("organizer_calendar_id") or event.get("calendar_id") or ""
    return str(value) if str(value).strip() else DEFAULT_CALENDAR_ID


def _organizer(event: dict) -> str:
    data = event.get("event_organizer", {})
    if isinstance(data, dict):
        return str(data.get("display_name", "") or "")
    return ""


def _rrule(event: dict) -> str:
    raw = event.get("recurrence")
    if isinstance(raw, list):
        return ";".join(str(item) for item in raw if item)
    return str(raw) if raw else ""


def _is_all_day(event: dict) -> bool:
    start = event.get("start_time", {})
    if isinstance(start, dict):
        return bool(start.get("date")) and not start.get("datetime") and not start.get("timestamp")
    return False


def _normalise(event: dict):
    """Turn a Feishu event dict into a row tuple, or ``None`` when unusable."""
    if not isinstance(event, dict):
        return None
    event_id = str(event.get("event_id") or "").strip()
    if not event_id:
        return None

    all_day = _is_all_day(event)
    start = parse_event_time(event.get("start_time", {}))
    end = parse_event_time(event.get("end_time", {}))

    if all_day:
        # 全天日程只有日期：归一成 00:00:00 → 23:59:59，否则当天 10:00
        # 发起的区间查询会因为 end_ts == start_ts 而漏掉它。
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        if end < start:
            end = start
        end = end.replace(hour=23, minute=59, second=59, microsecond=0)
    elif end < start:
        end = start

    raw = json.dumps(event, ensure_ascii=False)
    return (
        event_id,
        _calendar_id(event),
        str(event.get("summary", "") or ""),
        str(event.get("description", "") or ""),
        _organizer(event),
        int(start.timestamp()),
        int(end.timestamp()),
        1 if all_day else 0,
        _rrule(event),
        raw,
        int(time.time()),
    )


def _load(row) -> dict:
    try:
        return json.loads(row["raw_json"])
    except (json.JSONDecodeError, TypeError):  # pragma: no cover - defensive
        return {
            "event_id": row["event_id"],
            "summary": row["summary"],
            "start_time": {"timestamp": str(row["start_ts"])},
            "end_time": {"timestamp": str(row["end_ts"])},
        }


# ── Writes ───────────────────────────────────────────────────────────────────


def upsert_many(
    conn: sqlite3.Connection,
    events,
    range_start: datetime,
    range_end: datetime,
    calendar_id: str = DEFAULT_CALENDAR_ID,
    prune: bool = True,
) -> int:
    """Insert or update ``events`` and record that the range is now synced.

    ``prune`` deletes rows the snapshot no longer contains, but only within the
    synced window: rows that overlap ``[range_start, range_end]``, plus active
    recurring series that began earlier (``+agenda`` always returns those, so
    their absence means the series was deleted upstream).

    A non-list payload (``None``, a dict, a parse failure) is a no-op: it never
    touches stored rows, so a broken response cannot wipe the cache.

    Returns the number of events written.
    """
    if not isinstance(events, list):
        return 0

    rows = [r for r in (_normalise(e) for e in events) if r is not None]
    start_ts = int(range_start.timestamp())
    end_ts = int(range_end.timestamp())

    with conn:
        conn.executemany(
            """
            INSERT INTO events
                (event_id, calendar_id, summary, description, organizer,
                 start_ts, end_ts, all_day, rrule, raw_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id, calendar_id) DO UPDATE SET
                summary     = excluded.summary,
                description = excluded.description,
                organizer   = excluded.organizer,
                start_ts    = excluded.start_ts,
                end_ts      = excluded.end_ts,
                all_day     = excluded.all_day,
                rrule       = excluded.rrule,
                raw_json    = excluded.raw_json,
                updated_at  = excluded.updated_at
            """,
            rows,
        )

        if prune:
            conn.execute("DROP TABLE IF EXISTS temp._sync_ids")
            conn.execute("CREATE TEMP TABLE _sync_ids (event_id TEXT PRIMARY KEY)")
            if rows:
                conn.executemany(
                    "INSERT OR IGNORE INTO temp._sync_ids (event_id) VALUES (?)",
                    [(r[0],) for r in rows],
                )
            conn.execute(
                """
                DELETE FROM events
                WHERE calendar_id = ?
                  AND event_id NOT IN (SELECT event_id FROM temp._sync_ids)
                  AND (
                        (end_ts >= ? AND start_ts <= ?)
                     OR (rrule != '' AND start_ts <= ?)
                  )
                """,
                (calendar_id, start_ts, end_ts, end_ts),
            )
            conn.execute("DROP TABLE temp._sync_ids")

        conn.execute(
            """
            INSERT INTO sync_ranges (calendar_id, range_start, range_end, synced_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(range_start, range_end, calendar_id) DO UPDATE SET
                synced_at = excluded.synced_at
            """,
            (calendar_id, start_ts, end_ts, int(time.time())),
        )

    return len(rows)


def delete_event(conn: sqlite3.Connection, event_id: str, calendar_id=None) -> bool:
    """Remove a single event locally. Returns True when a row was deleted."""
    event_id = str(event_id or "").strip()
    if not event_id:
        return False
    with conn:
        if calendar_id:
            cursor = conn.execute(
                "DELETE FROM events WHERE event_id = ? AND calendar_id = ?",
                (event_id, str(calendar_id)),
            )
        else:
            cursor = conn.execute("DELETE FROM events WHERE event_id = ?", (event_id,))
    return cursor.rowcount > 0


def store_snapshot(conn, events, range_start, range_end, calendar_id=DEFAULT_CALENDAR_ID) -> int:
    """``upsert_many`` for UI callers: a cache problem must not break syncing."""
    try:
        return upsert_many(conn, events, range_start, range_end, calendar_id=calendar_id)
    except sqlite3.Error as exc:
        logger.warning("Local event write failed: %s", exc)
        return 0


# ── Reads ────────────────────────────────────────────────────────────────────


def query_range(
    conn: sqlite3.Connection,
    start: datetime,
    end: datetime,
    calendar_id=None,
) -> list[dict]:
    """Return events overlapping ``[start, end]``, sorted by start time.

    Recurring series that started earlier are always included — their
    occurrences may fall inside the window, and the views expand them.
    """
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    # 窗口起点对 end_ts、窗口终点对 start_ts：重叠判断是
    # 「结束于窗口开始之后」且「开始于窗口结束之前」。
    params = [start_ts, end_ts, end_ts]
    sql = """
        SELECT raw_json FROM events
        WHERE ((end_ts >= ? AND start_ts <= ?) OR (rrule != '' AND start_ts <= ?))
    """
    if calendar_id:
        sql += " AND calendar_id = ?"
        params.append(str(calendar_id))
    sql += " ORDER BY start_ts, end_ts"

    rows = conn.execute(sql, params).fetchall()
    return [_load(row) for row in rows]


def search(conn: sqlite3.Connection, query: str, limit: int = 200) -> list[dict]:
    """Case-insensitive keyword search over summary / description / organizer."""
    text = (query or "").strip().lower()
    if not text:
        return []
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    rows = conn.execute(
        """
        SELECT raw_json FROM events
        WHERE lower(summary)     LIKE ? ESCAPE '\\'
           OR lower(description) LIKE ? ESCAPE '\\'
           OR lower(organizer)   LIKE ? ESCAPE '\\'
        ORDER BY start_ts DESC
        LIMIT ?
        """,
        (pattern, pattern, pattern, int(limit)),
    ).fetchall()
    return [_load(row) for row in rows]


def count(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])


def read_range(conn, start: datetime, end: datetime, calendar_id=None) -> list[dict]:
    """``query_range`` for UI callers: a broken cache yields ``[]``, never raises."""
    try:
        return query_range(conn, start, end, calendar_id)
    except sqlite3.Error as exc:
        logger.warning("Local event query failed: %s", exc)
        return []


def all_day_flags(conn: sqlite3.Connection) -> dict:
    """Map ``event_id`` → whether it is an all-day event."""
    rows = conn.execute("SELECT event_id, all_day FROM events").fetchall()
    return {row["event_id"]: bool(row["all_day"]) for row in rows}


# ── Coverage bookkeeping ─────────────────────────────────────────────────────


def covered_ranges(conn: sqlite3.Connection, calendar_id: str = DEFAULT_CALENDAR_ID) -> list:
    """Return synced ``(start_ts, end_ts)`` spans, oldest first."""
    rows = conn.execute(
        "SELECT range_start, range_end FROM sync_ranges "
        "WHERE calendar_id = ? ORDER BY range_start",
        (str(calendar_id),),
    ).fetchall()
    return [(int(row["range_start"]), int(row["range_end"])) for row in rows]


def last_synced_ts(conn: sqlite3.Connection, calendar_id: str = DEFAULT_CALENDAR_ID) -> int | None:
    """Most recent ``synced_at`` across synced ranges; ``None`` if nothing synced."""
    row = conn.execute(
        "SELECT MAX(synced_at) AS ts FROM sync_ranges WHERE calendar_id = ?",
        (str(calendar_id),),
    ).fetchone()
    if not row or row["ts"] is None:
        return None
    return int(row["ts"])


def last_synced(conn, calendar_id: str = DEFAULT_CALENDAR_ID):
    """``last_synced_ts`` for UI callers: a broken cache reads as "never synced"."""
    try:
        return last_synced_ts(conn, calendar_id)
    except sqlite3.Error as exc:
        logger.warning("Local sync timestamp read failed: %s", exc)
        return None


def is_range_covered(
    conn: sqlite3.Connection,
    start: datetime,
    end: datetime,
    calendar_id: str = DEFAULT_CALENDAR_ID,
) -> bool:
    """True when a previously synced span fully contains ``[start, end]``."""
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())
    for span_start, span_end in covered_ranges(conn, calendar_id):
        if span_start <= start_ts and span_end >= end_ts:
            return True
    return False


def is_covered(
    conn,
    start: datetime,
    end: datetime,
    calendar_id: str = DEFAULT_CALENDAR_ID,
) -> bool:
    """``is_range_covered`` for UI callers: a broken cache reads as "not covered"."""
    try:
        return is_range_covered(conn, start, end, calendar_id)
    except sqlite3.Error as exc:
        logger.warning("Local coverage check failed: %s", exc)
        return False


def enforce_retention(conn: sqlite3.Connection, days: int = RETENTION_DAYS) -> int:
    """Drop events and sync spans older than the rolling retention window.

    Safe to call on every launch: a cache problem must never block startup.
    """
    cutoff = int(time.time()) - int(days) * 86400
    try:
        with conn:
            cursor = conn.execute("DELETE FROM events WHERE end_ts < ?", (cutoff,))
            conn.execute("DELETE FROM sync_ranges WHERE range_end < ?", (cutoff,))
            conn.execute("DELETE FROM notified WHERE fired_at < ?", (cutoff,))
    except sqlite3.Error as exc:
        logger.warning("Retention sweep failed: %s", exc)
        return 0
    return cursor.rowcount


# ── Notification bookkeeping ─────────────────────────────────────────────────


def mark_notified(conn: sqlite3.Connection, keys, when=None) -> int:
    """Record that reminders for ``keys`` have been delivered. Idempotent."""
    items = [str(k) for k in (keys or []) if str(k or "").strip()]
    if not items:
        return 0
    stamp = int(when if when is not None else time.time())
    try:
        with conn:
            conn.executemany(
                "INSERT INTO notified (event_key, fired_at) VALUES (?, ?) "
                "ON CONFLICT(event_key) DO NOTHING",
                [(key, stamp) for key in items],
            )
    except sqlite3.Error as exc:
        # 记不住就宁可多提醒一次，也不能让提醒流程抛进 Qt 槽
        logger.warning("Could not record notification: %s", exc)
        return 0
    return len(items)


def is_notified(conn: sqlite3.Connection, key: str) -> bool:
    try:
        row = conn.execute(
            "SELECT 1 FROM notified WHERE event_key = ?", (str(key),)
        ).fetchone()
    except sqlite3.Error as exc:
        logger.warning("Notification lookup failed: %s", exc)
        return False
    return row is not None


def notified_keys(conn: sqlite3.Connection, keys) -> set:
    """Subset of ``keys`` already notified (one query, chunked by 400)."""
    items = [str(k) for k in (keys or []) if str(k or "").strip()]
    found: set = set()
    for offset in range(0, len(items), 400):
        chunk = items[offset : offset + 400]
        placeholders = ",".join("?" * len(chunk))
        try:
            rows = conn.execute(
                f"SELECT event_key FROM notified WHERE event_key IN ({placeholders})",
                chunk,
            ).fetchall()
        except sqlite3.Error as exc:
            logger.warning("Notification lookup failed: %s", exc)
            return found
        found.update(str(row[0]) for row in rows)
    return found
