"""Scheduled JSON / CSV export of the local agenda.

The app already exports the visible range to Excel by hand. This module is the
programmable counterpart: a rolling snapshot dropped into a folder on a
schedule so other tools (Obsidian, a spreadsheet, Grafana) can consume it
without anyone clicking anything.

Rules that keep it safe to run unattended:

- Writes are atomic (temp file + ``os.replace``), so a reader never sees a
  half-written file.
- A failure logs and returns ``[]`` — a scheduled job must never raise into a
  Qt slot or pop a dialog at breakfast.
- ``export_last_run`` is only advanced after the files are on disk, so a
  failure retries on the next tick instead of silently skipping a day.
"""

import csv
import io
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import event_store
from models_event import parse_event_time
from reminder import collect_occurrences

logger = logging.getLogger(__name__)

SCHEDULE_OFF = "off"
SCHEDULE_DAILY = "daily"
SCHEDULE_WEEKLY = "weekly"
SCHEDULES = (SCHEDULE_OFF, SCHEDULE_DAILY, SCHEDULE_WEEKLY)

# 导出的滚动窗口：回看一周便于复盘，前瞻一个月覆盖排期
DAYS_BACK = 7
DAYS_FORWARD = 30

CSV_COLUMNS = ["date", "start", "end", "all_day", "summary", "organizer", "event_id", "recurring"]


def snapshot_range(now: datetime = None, days_back: int = DAYS_BACK, days_forward: int = DAYS_FORWARD):
    """Return the ``(start, end)`` a snapshot covers."""
    now = now or datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days_back)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_forward, hours=23, minutes=59, seconds=59)
    return start, end


def atomic_write_text(path: Path, text: str) -> Path:
    """Write ``text`` to ``path`` via a temp sibling + ``os.replace``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)
    return path


def _row(occ) -> dict:
    organizer = ""
    data = occ.event.get("event_organizer", {})
    if isinstance(data, dict):
        organizer = str(data.get("display_name", "") or "")
    recurring = bool(occ.event.get("recurrence"))
    return {
        "date": occ.start.strftime("%Y-%m-%d"),
        "start": "全天" if occ.all_day else occ.start.strftime("%H:%M"),
        "end": "全天" if occ.all_day else occ.end.strftime("%H:%M"),
        "all_day": "1" if occ.all_day else "0",
        "summary": occ.summary,
        "organizer": organizer,
        "event_id": str(occ.event.get("event_id", "") or ""),
        "recurring": "1" if recurring else "0",
    }


def build_rows(events, start: datetime, end: datetime) -> list:
    return [_row(occ) for occ in collect_occurrences(events or [], start, end)]


def build_json(rows: list, generated_at: datetime = None) -> str:
    payload = {
        "generated_at": (generated_at or datetime.now()).strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "FeishuCalendarDesktop",
        "count": len(rows),
        "events": rows,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def build_csv(rows: list) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def export_snapshot(conn, dest_dir, now: datetime = None,
                    days_back: int = DAYS_BACK, days_forward: int = DAYS_FORWARD) -> list:
    """Write ``events-YYYYMMDD.json`` + ``.csv``; returns the paths written."""
    now = now or datetime.now()
    start, end = snapshot_range(now, days_back, days_forward)
    events = event_store.read_range(conn, start, end)
    rows = build_rows(events, start, end)

    folder = Path(dest_dir)
    stem = f"events-{now.strftime('%Y%m%d')}"
    written = [
        atomic_write_text(folder / f"{stem}.json", build_json(rows, now)),
        atomic_write_text(folder / f"{stem}.csv", build_csv(rows)),
    ]
    return written


# ── Scheduling ──────────────────────────────────────────────────────────────


def is_due(config, now: datetime = None) -> bool:
    """True when a scheduled export should run at ``now``."""
    now = now or datetime.now()
    schedule = str(config.get("export_schedule", SCHEDULE_OFF) or SCHEDULE_OFF)
    if schedule not in (SCHEDULE_DAILY, SCHEDULE_WEEKLY):
        return False
    if not str(config.get("export_dir", "") or "").strip():
        return False

    last = str(config.get("export_last_run", "") or "").strip()
    if not last:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
    except ValueError:
        return True

    if schedule == SCHEDULE_DAILY:
        return last_dt.date() != now.date()
    # weekly：同一 ISO 周内只跑一次
    last_year, last_week, _ = last_dt.isocalendar()
    year, week, _ = now.isocalendar()
    return (last_year, last_week) != (year, week)


def run_if_due(conn, config, now: datetime = None) -> list:
    """Run the scheduled export when due. Never raises."""
    now = now or datetime.now()
    try:
        if not is_due(config, now):
            return []
        written = export_snapshot(conn, config.get("export_dir"), now)
    except Exception as exc:  # noqa: BLE001 - 定时任务失败只能记日志，不能弹窗
        logger.warning("Scheduled export failed: %s", exc)
        return []
    # 落盘成功后才推进时间戳，失败下次重试而不是跳过一整天
    config.set("export_last_run", now.strftime("%Y-%m-%dT%H:%M:%S"))
    logger.info("Exported agenda snapshot to %s", written[0].parent)
    return written


def parse_export_time(value: str):
    """Parse a persisted export timestamp; ``None`` when unusable."""
    try:
        return datetime.fromisoformat(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None


def event_start(event: dict) -> datetime:
    """Small helper re-exported for callers that only need one timestamp."""
    return parse_event_time(event.get("start_time", {}))
