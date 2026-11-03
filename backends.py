"""Calendar backends — one protocol, three implementations.

The app talks to exactly one place for "give me the events in this range" and
"write this change back". Today that place is ``lark-cli``; tomorrow it could
be CalDAV, an ICS subscription, or the local store itself.

Why bother when there is only one real remote? Because the *shape* of the
protocol is what keeps the views honest: a view may only call
``fetch_range`` / ``search``, never "run lark-cli". The headless CLI uses the
same three implementations, so the protocol is exercised on every run rather
than being aspirational scaffolding.

Read-only backends raise :class:`ReadOnlyBackend` instead of pretending to
succeed — a CLI or future view that tries to write must fail loudly.

**Boundary worth knowing:** the GUI does *not* call this module yet. It uses
``lark_cli_async``, which wraps lark-cli in a ``QProcess`` so the UI thread is
never blocked; routing the window through a synchronous backend would freeze
it for seconds per refresh. The protocol therefore serves the CLI and tests
today, and is the seam a future async backend (or a second remote) plugs into.
"""

import json
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable

import event_store
from models_event import parse_event_time
from occurrences import collect as collect_occurrences
from occurrences import to_occurrence
from utils import get_local_tz_name


class BackendError(Exception):
    """Any failure raised by a backend (never a raw OSError/subprocess error)."""


class ReadOnlyBackend(BackendError):
    """Raised when a write is attempted on a read-only backend."""


@runtime_checkable
class CalendarBackend(Protocol):
    """Minimal surface a calendar source must provide."""

    name: str

    def fetch_range(self, start: datetime, end: datetime) -> list:
        """Events (occurrences included) overlapping ``[start, end]``."""

    def search(self, query: str, start: datetime = None, end: datetime = None) -> list:
        """Keyword search over summary / description / organizer."""

    def create(self, payload: dict) -> dict:
        """Create one event; returns the created event data."""

    def update(self, event_id: str, payload: dict) -> dict:
        """Patch one event; returns the updated event data."""

    def delete(self, event_id: str, calendar_id: str = None) -> bool:
        """Delete one event."""


# ── Remote: lark-cli ────────────────────────────────────────────────────────


class LarkCliBackend:
    """The production backend: Feishu calendar through the lark-cli binary."""

    name = "lark-cli"

    def __init__(self, cli=None):
        if cli is None:
            from lark_cli import LarkCli

            cli = LarkCli()
        self._cli = cli

    def fetch_range(self, start: datetime, end: datetime) -> list:
        """Return occurrences (recurring series already expanded).

        Every backend returns the same shape — ready-to-render occurrences — so
        callers never need to know whether their source expands RRULEs.
        """
        try:
            events = self._cli.get_agenda(start, end)
        except Exception as exc:  # noqa: BLE001 - 统一成 BackendError 给上层
            raise BackendError(str(exc)) from exc
        return collect_occurrences(events, start, end)

    def search(self, query: str, start: datetime = None, end: datetime = None) -> list:
        """Keyword search; like :meth:`fetch_range`, returns occurrences."""
        try:
            events = self._cli.search_events(query, start, end)
        except Exception as exc:  # noqa: BLE001
            raise BackendError(str(exc)) from exc
        return [to_occurrence(event) for event in events]

    def create(self, payload: dict) -> dict:
        try:
            return self._cli.create_event(
                summary=payload.get("summary", ""),
                start=payload["start"],
                end=payload["end"],
                description=payload.get("description", ""),
                calendar_id=payload.get("calendar_id", "primary"),
                rrule=payload.get("rrule"),
            )
        except Exception as exc:  # noqa: BLE001
            raise BackendError(str(exc)) from exc

    def update(self, event_id: str, payload: dict) -> dict:
        body = {}
        if payload.get("summary"):
            body["summary"] = payload["summary"]
        if payload.get("start"):
            body["start_time"] = {
                "timestamp": str(int(payload["start"].timestamp())),
                "timezone": get_local_tz_name(),
            }
        if payload.get("end"):
            body["end_time"] = {
                "timestamp": str(int(payload["end"].timestamp())),
                "timezone": get_local_tz_name(),
            }
        if "description" in payload:
            body["description"] = payload.get("description") or ""
        if payload.get("rrule") is not None:
            body["recurrence"] = payload["rrule"]

        calendar_id = payload.get("calendar_id") or "primary"
        path = f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
        try:
            return self._cli._run(["api", "PATCH", path, "--data", json.dumps(body)])
        except Exception as exc:  # noqa: BLE001
            raise BackendError(str(exc)) from exc

    def delete(self, event_id: str, calendar_id: str = None) -> bool:
        try:
            return self._cli.delete_event(calendar_id or "primary", event_id)
        except Exception as exc:  # noqa: BLE001
            raise BackendError(str(exc)) from exc


# ── Local: the SQLite fact layer ────────────────────────────────────────────


class StoreBackend:
    """Read-only backend over ``events.db`` — what the headless CLI defaults to.

    Needs no auth, no network and no display, which is the whole point of a
    headless command: a Stream Deck or a shell prompt should be able to ask
    "what is next" without spawning node.
    """

    name = "store"

    def __init__(self, conn=None):
        self._conn = conn if conn is not None else event_store.connect()

    def fetch_range(self, start: datetime, end: datetime) -> list:
        return collect_occurrences(event_store.read_range(self._conn, start, end), start, end)

    def search(self, query: str, start: datetime = None, end: datetime = None) -> list:
        occurrences = [to_occurrence(event) for event in event_store.search(self._conn, query)]
        if start is None and end is None:
            return occurrences
        # 用有界默认值而不是 datetime.min/max：后者跨平台做 timestamp 会溢出
        low = start or datetime(1970, 1, 1)
        high = end or datetime(2100, 1, 1)
        return [occ for occ in occurrences if occ.end >= low and occ.start <= high]

    def create(self, payload: dict) -> dict:
        raise ReadOnlyBackend("本地缓存只读；写入请使用飞书账号")

    def update(self, event_id: str, payload: dict) -> dict:
        raise ReadOnlyBackend("本地缓存只读；写入请使用飞书账号")

    def delete(self, event_id: str, calendar_id: str = None) -> bool:
        raise ReadOnlyBackend("本地缓存只读；写入请使用飞书账号")


def _overlaps(event: dict, start: datetime, end: datetime) -> bool:
    occ = collect_occurrences([event], start, end)
    return bool(occ)


# ── Local: ICS subscription (read-only) ─────────────────────────────────────


class IcsBackend:
    """Read-only backend for an ``.ics`` file (exported calendar / subscription).

    Deliberately minimal: unfolds continuation lines, reads VEVENT blocks and
    the handful of properties the views need. Unknown properties are ignored
    rather than guessed at — a calendar that invents data is worse than one
    that shows less.
    """

    name = "ics"

    def __init__(self, path):
        self._path = path

    @property
    def path(self):
        return self._path

    def events(self) -> list:
        try:
            with open(self._path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as exc:
            raise BackendError(f"无法读取 ICS 文件：{exc}") from exc
        return parse_ics(text)

    def fetch_range(self, start: datetime, end: datetime) -> list:
        return collect_occurrences(self.events(), start, end)

    def search(self, query: str, start: datetime = None, end: datetime = None) -> list:
        needle = (query or "").strip().lower()
        events = self.events()
        if start is not None or end is not None:
            low = start or datetime(1970, 1, 1)
            high = end or datetime(2100, 1, 1)
            events = [event for event in events if _overlaps(event, low, high)]
        if needle:
            events = [
                event
                for event in events
                if needle in str(event.get("summary", "")).lower()
                or needle in str(event.get("description", "")).lower()
            ]
        return [to_occurrence(event) for event in events]

    def create(self, payload: dict) -> dict:
        raise ReadOnlyBackend("ICS 订阅只读")

    def update(self, event_id: str, payload: dict) -> dict:
        raise ReadOnlyBackend("ICS 订阅只读")

    def delete(self, event_id: str, calendar_id: str = None) -> bool:
        raise ReadOnlyBackend("ICS 订阅只读")


def _unfold(text: str) -> list:
    """Join RFC5545 folded lines (continuations start with space or tab)."""
    lines: list = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _split_property(line: str):
    head, _, value = line.partition(":")
    name = head.split(";", 1)[0].strip().upper()
    params = head.split(";")[1:]
    return name, params, value


def _parse_dt(value: str, params: list):
    value = value.strip()
    is_date = any(p.upper() == "VALUE=DATE" for p in params) or (
        len(value) == 8 and value.isdigit()
    )
    if is_date and len(value) >= 8:
        try:
            parsed = datetime.strptime(value[:8], "%Y%m%d")
        except ValueError:
            return None, True
        return parsed, True
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S"):
        try:
            parsed = datetime.strptime(value, fmt)
        except ValueError:
            continue
        if fmt.endswith("Z"):
            # UTC → 本地，否则跨时区会议会显示成错误的时间
            parsed = parsed.replace(tzinfo=None) + (datetime.now() - datetime.utcnow())
        return parsed, False
    return None, False


def parse_ics(text: str) -> list:
    """Parse VEVENT blocks into the app's event dict shape."""
    events: list = []
    current = None
    for line in _unfold(text):
        upper = line.strip().upper()
        if upper == "BEGIN:VEVENT":
            current = {}
            continue
        if upper == "END:VEVENT":
            if current is not None:
                event = _finish_event(current)
                if event is not None:
                    events.append(event)
            current = None
            continue
        if current is None or ":" not in line:
            continue

        name, params, value = _split_property(line)
        if name == "SUMMARY":
            current["summary"] = value.strip()
        elif name == "DESCRIPTION":
            current["description"] = value.replace("\\n", "\n").replace("\\,", ",").strip()
        elif name == "UID":
            current["uid"] = value.strip()
        elif name == "LOCATION":
            current["location"] = value.strip()
        elif name == "DTSTART":
            current["start"], current["all_day"] = _parse_dt(value, params)
        elif name == "DTEND":
            current["end"], _ = _parse_dt(value, params)
        elif name == "ORGANIZER":
            current["organizer"] = value.replace("mailto:", "").strip()
        elif name == "RRULE":
            current["recurrence"] = value.strip()

    events.sort(key=lambda e: parse_event_time(e.get("start_time", {})))
    return events


def _finish_event(raw: dict):
    start = raw.get("start")
    if start is None:
        return None
    end = raw.get("end")
    if end is None:
        end = start + (timedelta(days=1) if raw.get("all_day") else timedelta(hours=1))

    if raw.get("all_day"):
        start_time = {"date": start.strftime("%Y-%m-%d")}
        end_time = {"date": end.strftime("%Y-%m-%d")}
    else:
        start_time = {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S")}
        end_time = {"datetime": end.strftime("%Y-%m-%dT%H:%M:%S")}

    event = {
        "event_id": raw.get("uid") or f"ics-{start.strftime('%Y%m%dT%H%M%S')}",
        "summary": raw.get("summary", ""),
        "description": raw.get("description", ""),
        "organizer_calendar_id": "ics",
        "start_time": start_time,
        "end_time": end_time,
    }
    if raw.get("recurrence"):
        event["recurrence"] = [raw["recurrence"]]
    organizer = raw.get("organizer")
    if organizer:
        event["event_organizer"] = {"display_name": organizer}
    location = raw.get("location")
    if location:
        event["location"] = {"name": location}
    return event


def build_backend(source: str = "store", **kwargs) -> CalendarBackend:
    """Factory used by the headless CLI and by tests."""
    source = (source or "store").lower()
    if source == "store":
        return StoreBackend(kwargs.get("conn"))
    if source == "lark":
        return LarkCliBackend(kwargs.get("cli"))
    if source == "ics":
        path = kwargs.get("path")
        if not path:
            raise BackendError("--ics 需要一个 .ics 文件路径")
        return IcsBackend(path)
    raise BackendError(f"未知来源：{source}")
