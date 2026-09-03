"""Shared event model, recurrence expansion, markdown rendering and local
color/subtask helpers for FeishuCalendarDesktop.

This module is the single source of truth for parsing Feishu event time
fields, expanding recurring events for display, turning Markdown descriptions
into Qt-compatible HTML, and managing the *local-only* color & subtask
enhancements (these are never sent to Feishu — colors are keyed by event id in
``config.json`` and subtasks live inside the event description as a Markdown
task list, so they round-trip through the existing write path untouched).
"""

from datetime import datetime, timedelta

# Time parsing / all-day detection were originally defined in ``event_card.py``.
# They live here now so every view, widget and dialog imports the same logic.
# ``event_card`` re-exports them for backward compatibility.


def parse_event_time(time_data) -> datetime:
    """Parse event time from a lark-cli / Feishu ``start_time`` / ``end_time`` dict.

    Handles:
    - Timed events (lark-cli): ``{'datetime': '2026-07-15T10:00:00+08:00'}``
    - All-day events (lark-cli): ``{'date': '2026-07-15', 'timezone': 'UTC'}``
    - Feishu API: ``{'timestamp': '1690000000', 'timezone': 'Asia/Shanghai'}``
    """
    if not isinstance(time_data, dict):
        return datetime.now()
    # Feishu API: 'timestamp' (Unix seconds as string)
    ts_str = time_data.get("timestamp", "")
    if ts_str:
        try:
            return datetime.fromtimestamp(int(ts_str))
        except (ValueError, TypeError):
            pass
    # lark-cli: 'datetime' like '2026-07-15T10:00:00+08:00'
    dt_str = time_data.get("datetime", "")
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str)
            # Strip tzinfo to avoid offset-naive vs offset-aware comparison errors
            return dt.replace(tzinfo=None)
        except (ValueError, TypeError):
            pass
    # All-day: 'date' like '2026-07-15'
    date_str = time_data.get("date", "")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    return datetime.now()


def is_all_day_event(event: dict) -> bool:
    """Return True if the event is all-day (date-only, no datetime/timestamp)."""
    start = event.get("start_time", {})
    if isinstance(start, dict):
        return bool(start.get("date")) and not start.get("datetime") and not start.get("timestamp")
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Color palette (local-only categorization)
# ─────────────────────────────────────────────────────────────────────────────

# (display name, hex) — weektodo-style category colors.
PALETTE = [
    ("蓝", "#4B3FE3"),
    ("青", "#15A877"),
    ("橙", "#FEA900"),
    ("红", "#E8463A"),
    ("紫", "#9B5DE5"),
    ("粉", "#F15BB5"),
    ("绿", "#2F9E44"),
    ("灰", "#737373"),
]


def get_event_color(config, event_id: str):
    """Return the local color hex for ``event_id`` or ``None`` if uncolored."""
    colors = (config.get("event_colors") if config else None) or {}
    return colors.get(event_id)


def set_event_color(config, event_id: str, hex_value):
    """Persist a local color for ``event_id`` (``None`` clears it)."""
    if not config:
        return
    colors = config.get("event_colors") or {}
    if hex_value:
        colors[event_id] = hex_value
    else:
        colors.pop(event_id, None)
    config.set("event_colors", colors)


# ─────────────────────────────────────────────────────────────────────────────
# Recurrence expansion (display only — does not touch Feishu writes)
# ─────────────────────────────────────────────────────────────────────────────

_WEEKDAY_IDX = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def _parse_rrule(rrule_raw) -> dict:
    """Parse an RFC5545 RRULE string (or list) into an upper-case key dict."""
    if isinstance(rrule_raw, list):
        rrule_raw = rrule_raw[0] if rrule_raw else ""
    if not isinstance(rrule_raw, str) or not rrule_raw:
        return {}
    parts = {}
    for kv in rrule_raw.split(";"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            parts[k.strip().upper()] = v.strip()
    return parts


def _parse_until(value: str) -> datetime | None:
    """Parse an RRULE UNTIL value (``YYYYMMDD[T...Z]`` or ISO date)."""
    value = value.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%dT%H%M%S", "%Y%m%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _time_dict_for(dt: datetime, original: dict) -> dict:
    """Mirror ``original`` time-dict shape but with ``dt`` substituted."""
    if isinstance(original, dict) and original.get("date"):
        return {"date": dt.strftime("%Y-%m-%d"), "timezone": original.get("timezone", "Asia/Shanghai")}
    if isinstance(original, dict) and original.get("timestamp"):
        return {
            "timestamp": str(int(dt.timestamp())),
            "timezone": original.get("timezone", "Asia/Shanghai"),
        }
    return {"datetime": dt.isoformat()}


def _add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    # Clamp day to the last day of the target month
    day = min(dt.day, [31, 29 if (year % 4 == 0 and year % 100 != 0) or year % 400 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
    return dt.replace(year=year, month=month, day=day)


def expand_recurrence(event: dict, range_start: datetime, range_end: datetime) -> list[dict]:
    """Expand a recurring Feishu event into per-occurrence dicts within the range.

    The original ``event`` is treated as the series template. Each generated
    occurrence is a shallow copy with adjusted ``start_time`` / ``end_time`` and
    two marker keys:

    - ``_recurrence_key`` — stable id ``<event_id>@<occurrence iso>``
    - ``_is_recurring_instance`` — ``True``

    Returns ``[]`` for non-recurring events or unparseable rules.
    """
    rrule_raw = event.get("recurrence")
    if isinstance(rrule_raw, list):
        rrule_raw = rrule_raw[0] if rrule_raw else ""
    if not isinstance(rrule_raw, str) or not rrule_raw:
        return []

    parts = _parse_rrule(rrule_raw)
    freq = parts.get("FREQ", "").upper()
    if not freq:
        return []

    interval = max(1, int(parts.get("INTERVAL", "1") or 1))
    count = int(parts["COUNT"]) if parts.get("COUNT") else None
    until_dt = _parse_until(parts["UNTIL"]) if parts.get("UNTIL") else None
    byday = (
        [d.strip()[:2].upper() for d in parts["BYDAY"].split(",") if d.strip()]
        if parts.get("BYDAY")
        else []
    )
    byday_idx = {_WEEKDAY_IDX[b] for b in byday if b in _WEEKDAY_IDX}

    start = parse_event_time(event.get("start_time", {}))
    end = parse_event_time(event.get("end_time", {}))
    duration = end - start
    if duration.total_seconds() <= 0:
        duration = timedelta(hours=1)

    results: list[dict] = []
    made = 0
    guard = 0

    if freq == "WEEKLY" and byday_idx:
        # Day-by-day scan across the visible window (bounded to ~1 week of slack).
        cur = max(start, range_start - timedelta(days=7))
        # Anchor week (Monday of the start date's week) for INTERVAL calculation.
        start_week_monday = start - timedelta(days=start.weekday())
        while cur <= range_end and guard < 600:
            guard += 1
            if cur.weekday() in byday_idx and cur >= start:
                cur_week_monday = cur - timedelta(days=cur.weekday())
                weeks_diff = (cur_week_monday - start_week_monday).days // 7
                if weeks_diff % interval == 0:
                    results.append(_make_occurrence(event, cur, duration))
                    made += 1
            cur += timedelta(days=1)
            if count is not None and made >= count:
                break
            if until_dt is not None and cur > until_dt:
                break
        return results

    # DAILY / MONTHLY / YEARLY — step by interval, fast-forward to the window.
    if freq == "DAILY":
        cur = start
        if cur < range_start:
            skip = (range_start - start).days // interval
            cur = start + timedelta(days=max(0, skip) * interval)
    elif freq == "MONTHLY":
        cur = start
        while cur < range_start and guard < 600:
            guard += 1
            cur = _add_months(cur, interval)
    elif freq == "YEARLY":
        cur = start
        while cur < range_start and guard < 600:
            guard += 1
            cur = _add_months(cur, 12 * interval)
    else:
        return results

    while cur <= range_end and guard < 600:
        guard += 1
        if cur >= start:
            results.append(_make_occurrence(event, cur, duration))
            made += 1
        if freq == "DAILY":
            cur += timedelta(days=interval)
        elif freq == "MONTHLY":
            cur = _add_months(cur, interval)
        elif freq == "YEARLY":
            cur = _add_months(cur, 12 * interval)
        else:
            break
        if count is not None and made >= count:
            break
        if until_dt is not None and cur > until_dt:
            break
    return results


def _make_occurrence(event: dict, dt: datetime, duration: timedelta) -> dict:
    occ = dict(event)
    occ["start_time"] = _time_dict_for(dt, event.get("start_time", {}))
    occ["end_time"] = _time_dict_for(dt + duration, event.get("end_time", {}))
    occ["_recurrence_key"] = f"{event.get('event_id', '')}@{dt.strftime('%Y%m%dT%H%M%S')}"
    occ["_is_recurring_instance"] = True
    return occ


def has_recurrence(event: dict) -> bool:
    """Return True if the event carries a recurrence rule."""
    r = event.get("recurrence")
    if isinstance(r, list):
        return bool(r)
    return bool(r)


def expand_events_for_range(events: list[dict], range_start: datetime, range_end: datetime) -> list[dict]:
    """Return ``events`` with each recurring event expanded into its occurrences.

    The original series template is kept (so it still shows on its first date),
    and expanded occurrences are appended. Non-recurring events pass through.
    """
    out: list[dict] = []
    for ev in events:
        out.append(ev)
        if has_recurrence(ev):
            out.extend(expand_recurrence(ev, range_start, range_end))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → HTML (for the detail view & subtasks)
# ─────────────────────────────────────────────────────────────────────────────

def markdown_to_html(text: str) -> str:
    """Minimal Markdown → HTML converter safe for ``QLabel.setHtml``.

    Supports: headings, bold/italic/code, links, unordered/ordered lists,
    task lists (``- [ ]`` / ``- [x]``), blockquotes, horizontal rules and
    line breaks. Intentionally avoids raw HTML pass-through for safety.
    """
    if not text:
        return ""
    lines = text.splitlines()
    out: list[str] = []
    i = 0
    in_list = False

    def close_list():
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    def inline(s: str) -> str:
        # Escape HTML first, then re-introduce allowed markup.
        s = (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        # inline code
        import re

        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # bold / italic
        s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", s)
        # links [text](url) — only http(s)/mailto
        s = re.sub(
            r"\[([^\]]+)\]\((https?://[^\s)]+|mailto:[^\s)]+)\)",
            r'<a href="\2">\1</a>',
            s,
        )
        return s

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            close_list()
            i += 1
            continue
        if stripped.startswith("### "):
            close_list(); out.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            close_list(); out.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            close_list(); out.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("> "):
            close_list(); out.append(f"<blockquote>{inline(stripped[2:])}</blockquote>")
        elif stripped in ("---", "***", "___"):
            close_list(); out.append("<hr>")
        elif stripped.startswith("- [ ] ") or stripped.startswith("- [x] ") or stripped.startswith("- [X] "):
            if not in_list:
                out.append("<ul>"); in_list = True
            checked = "checked" if stripped[3] in "xX" else ""
            out.append(f'<li><input type="checkbox" disabled {checked}> {inline(stripped[6:])}</li>')
        elif stripped.startswith("- "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(stripped[2:])}</li>")
        elif len(stripped) >= 3 and stripped[0].isdigit() and stripped[1:].startswith(". "):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append(f"<li>{inline(stripped.split('. ', 1)[1])}</li>")
        else:
            close_list()
            out.append(f"<p>{inline(stripped)}</p>")
        i += 1
    close_list()
    return "".join(out)


# ─────────────────────────────────────────────────────────────────────────────
# Subtasks — implemented as a Markdown task list inside the description.
# ─────────────────────────────────────────────────────────────────────────────

def parse_task_list(description: str) -> list[dict]:
    """Extract ``[{'done': bool, 'text': str}, ...]`` from a description."""
    tasks: list[dict] = []
    if not description:
        return tasks
    for line in description.splitlines():
        s = line.strip()
        if s.startswith("- [ ] "):
            tasks.append({"done": False, "text": s[6:].strip()})
        elif s.startswith("- [x] ") or s.startswith("- [X] "):
            tasks.append({"done": True, "text": s[6:].strip()})
    return tasks


def rebuild_description(orig_description: str, tasks: list[dict]) -> str:
    """Return ``orig_description`` with its task-list lines replaced by ``tasks``."""
    kept: list[str] = []
    for line in (orig_description or "").splitlines():
        s = line.strip()
        if s.startswith("- [ ] ") or s.startswith("- [x] ") or s.startswith("- [X] "):
            continue
        kept.append(line)
    body = "\n".join(kept).strip()
    task_lines = "\n".join(
        f"- [{'x' if t['done'] else ' '}] {t['text']}" for t in tasks
    )
    if task_lines:
        return (body + "\n\n" + task_lines).strip()
    return body
