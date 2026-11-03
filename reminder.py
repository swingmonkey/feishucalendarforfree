"""Coming-soon reminders, conflict detection and daily overload alerts.

The app could show a calendar but never told you anything. This module is the
"it talks back" layer: a 30-second heartbeat that turns stored events into at
most a handful of notifications per day.

Design notes:

- All the decision logic lives in pure functions that take an explicit ``now``,
  so behaviour is testable without Qt or a real clock.
- Emitted notifications are recorded in the ``notified`` table by occurrence
  key, which is why a weekly meeting pings again next week while a refresh one
  minute later does not.
- A reminder is never emitted for an event that already started: a laptop
  waking from sleep must not shout about a meeting that began an hour ago.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Signal

import event_store
from occurrences import Occurrence
from occurrences import collect as _collect_occurrences

logger = logging.getLogger(__name__)

DEFAULT_LEAD_MINUTES = 10
SCAN_INTERVAL_MS = 30_000
# 扫描窗口：往未来看 1 小时足够覆盖最大提前量（30 分钟），
# 往过去看 1 分钟用于兜住扫描抖动。
LOOKAHEAD_MINUTES = 60

# 允许「已经过了开始时间多久还补提醒」：定时器 30 秒一跳，宽限取同一量级，
# 再晚就说明错过发车了，不该在会议进行中打断用户。
START_GRACE_SECONDS = 30

ALL_DAY_REMINDER_SUPPRESSED = True


@dataclass(frozen=True)
class ReminderHit:
    occurrence: Occurrence
    minutes_until: int

    @property
    def key(self) -> str:
        return self.occurrence.key


def collect_occurrences(events, start: datetime, end: datetime) -> list:
    """Occurrences overlapping ``[start, end]`` (see :mod:`occurrences`)."""
    return _collect_occurrences(events, start, end)


# ── Reminder decisions ──────────────────────────────────────────────────────


def due_reminders(
    occurrences,
    now: datetime,
    lead_minutes: int,
    notified,
    suppress_all_day: bool = ALL_DAY_REMINDER_SUPPRESSED,
) -> list[ReminderHit]:
    """Return occurrences that should raise a reminder right now.

    An occurrence qualifies when it starts within ``lead_minutes``, has not
    already fired, and has not started yet (one minute of slack absorbs timer
    jitter). All-day events are excluded by default: "today is a company
    holiday" is not something to be interrupted for.
    """
    lead = max(0, int(lead_minutes))
    hits: list[ReminderHit] = []
    for occ in occurrences:
        if suppress_all_day and occ.all_day:
            continue
        if occ.key in notified:
            continue
        if occ.end <= now:
            continue
        # 以秒为单位判断：``lead=0``（准时提醒）的含义是「正好到点」，
        # 用整分钟比较会让它永远落在窗口外。30 秒宽限吸收定时器抖动。
        ahead = (occ.start - now).total_seconds()
        if ahead > lead * 60 or ahead < -START_GRACE_SECONDS:
            continue
        hits.append(ReminderHit(occ, max(0, int(round(ahead / 60.0)))))
    return hits


def find_conflicts(occurrences) -> list[list[Occurrence]]:
    """Group timed occurrences into connected overlap clusters of two or more."""
    timed = sorted(
        (o for o in occurrences if not o.all_day and o.end > o.start),
        key=lambda o: (o.start, o.end),
    )
    groups: list[list[Occurrence]] = []
    cluster: list[Occurrence] = []
    cluster_end = None
    for occ in timed:
        if cluster and occ.start < cluster_end:
            cluster.append(occ)
            cluster_end = max(cluster_end, occ.end)
            continue
        if len(cluster) > 1:
            groups.append(cluster)
        cluster = [occ]
        cluster_end = occ.end
    if len(cluster) > 1:
        groups.append(cluster)
    return groups


def day_load_minutes(occurrences, day: datetime) -> int:
    """Total minutes of timed events overlapping ``day`` (all-day excluded)."""
    day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    total = 0.0
    for occ in occurrences:
        if occ.all_day:
            continue
        start = max(occ.start, day_start)
        end = min(occ.end, day_end)
        if end > start:
            total += (end - start).total_seconds() / 60.0
    return int(round(total))


def current_or_next(occurrences, now: datetime):
    """Return ``(occurrence, is_running)`` for the next agenda item, or ``None``."""
    upcoming = [o for o in occurrences if o.end > now]
    if not upcoming:
        return None
    upcoming.sort(key=lambda o: (o.start, o.end))
    for occ in upcoming:
        if occ.start <= now < occ.end:
            return occ, True
    return upcoming[0], False


def format_hhmm(value: datetime) -> str:
    return value.strftime("%H:%M")


def _shorten(text: str, limit: int = 12) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def tray_summary(events, now: datetime, empty: str = "今天没有日程") -> str:
    """One-line tray tooltip: how many today, plus what is next."""
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = collect_occurrences(events or [], day_start, day_start + timedelta(days=1))
    if not today:
        return empty
    found = current_or_next(today, now)
    count = len(today)
    if found is None:
        return f"今天 {count} 项"
    occ, running = found
    title = _shorten(occ.summary or "未命名日程")
    if running:
        return f"进行中 {title} · 今天 {count} 项"
    return f"今天 {count} 项 · {format_hhmm(occ.start)} {title}"


def describe_hit(hit: ReminderHit) -> str:
    """Notification body for one reminder."""
    occ = hit.occurrence
    when = "全天" if occ.all_day else format_hhmm(occ.start)
    if hit.minutes_until <= 0:
        lead = "即将开始"
    else:
        lead = f"{hit.minutes_until} 分钟后开始"
    parts = [f"{when} · {lead}"]
    organizer = ""
    data = occ.event.get("event_organizer", {})
    if isinstance(data, dict):
        organizer = str(data.get("display_name", "") or "")
    if organizer:
        parts.append(f"发起人 {organizer}")
    location = occ.event.get("location", {})
    if isinstance(location, dict):
        name = str(location.get("name", "") or "")
        if name:
            parts.append(name)
    return " · ".join(parts)


def describe_conflict(group) -> tuple[str, str]:
    names = "、".join(_shorten(o.summary or "未命名", 10) for o in group[:3])
    title = f"日程冲突：{len(group)} 项同时段"
    body = f"{format_hhmm(group[0].start)} 起 {names}"
    return title, body


def describe_overload(minutes: int, threshold_hours: float) -> tuple[str, str]:
    hours = minutes / 60.0
    return (
        "今日会议时长超载",
        f"已排 {hours:.1f} 小时（阈值 {threshold_hours:g} 小时），注意留白",
    )


# ── Quiet hours ─────────────────────────────────────────────────────────────


def _parse_hhmm(value: str, fallback: tuple[int, int]) -> tuple[int, int]:
    try:
        hour, minute = str(value).strip().split(":")
        return max(0, min(23, int(hour))), max(0, min(59, int(minute)))
    except (ValueError, AttributeError):
        return fallback


def in_quiet_hours(now: datetime, start: str, end: str) -> bool:
    """True inside ``[start, end)``, handling windows that wrap midnight."""
    start_hm = _parse_hhmm(start, (22, 0))
    end_hm = _parse_hhmm(end, (8, 0))
    if start_hm == end_hm:
        return False
    current = now.hour * 60 + now.minute
    start_min = start_hm[0] * 60 + start_hm[1]
    end_min = end_hm[0] * 60 + end_hm[1]
    if start_min < end_min:
        return start_min <= current < end_min
    return current >= start_min or current < end_min


# ── Service ─────────────────────────────────────────────────────────────────


class ReminderService(QObject):
    """Heartbeat that turns the local store into a few notifications per day.

    Every emitted item is recorded in the store first, so a crash between the
    two can at worst lose one notification — never repeat one forever.
    """

    notified = Signal(str, str)
    tick = Signal()

    def __init__(self, store, config, parent=None, interval_ms: int = SCAN_INTERVAL_MS):
        super().__init__(parent)
        self._store = store
        self._config = config
        self._interval_ms = max(5_000, int(interval_ms))
        self._timer = QTimer(self)
        self._timer.setInterval(self._interval_ms)
        self._timer.timeout.connect(self.scan)

    def start(self):
        if not self._timer.isActive():
            self._timer.start()

    def stop(self):
        self._timer.stop()

    def scan(self, now: datetime = None) -> list[tuple[str, str]]:
        """Run one pass; returns the ``(title, body)`` pairs that were emitted."""
        now = now or datetime.now()
        config = self._config

        if self._quiet_now(now):
            self.tick.emit()
            return []

        lead = int(config.get("reminder_lead_minutes", DEFAULT_LEAD_MINUTES) or 0)
        window_start = now - timedelta(minutes=1)
        window_end = now + timedelta(minutes=max(LOOKAHEAD_MINUTES, lead + 5))

        # 冲突与超载按「整天」判断：只看 1 小时扫描窗会把下午的日程算漏，
        # 于是 8 点看着空的日历却在 15 点突然报超载。
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        read_start = min(window_start, day_start)
        read_end = max(window_end, day_end)

        try:
            events = event_store.read_range(self._store, read_start, read_end)
        except Exception as exc:  # noqa: BLE001 - 提醒绝不能把应用带崩
            logger.warning("Reminder scan could not read the store: %s", exc)
            return []

        occurrences = collect_occurrences(events, read_start, read_end)
        emitted: list[tuple[str, str]] = []
        try:
            emitted.extend(self._reminders(occurrences, now, lead))
            emitted.extend(self._conflicts(occurrences, now))
            emitted.extend(self._overload(occurrences, now))
        except Exception as exc:  # noqa: BLE001 - 同上，降级为静默
            logger.warning("Reminder scan failed: %s", exc)

        for title, body in emitted:
            self.notified.emit(title, body)
        self.tick.emit()
        return emitted

    # ── individual alert kinds ──

    def _reminders(self, occurrences, now, lead: int) -> list[tuple[str, str]]:
        if not self._config.get("reminder_enabled", True):
            return []
        keys = [o.key for o in occurrences]
        notified = event_store.notified_keys(self._store, keys)
        out = []
        for hit in due_reminders(occurrences, now, lead, notified):
            event_store.mark_notified(self._store, [hit.key])
            out.append((hit.occurrence.summary or "日程提醒", describe_hit(hit)))
        return out

    def _conflicts(self, occurrences, now) -> list[tuple[str, str]]:
        if not self._config.get("conflict_alert_enabled", True):
            return []
        todays = [o for o in occurrences if o.start.date() == now.date()]
        groups = find_conflicts(todays)
        if not groups:
            return []
        key = f"conflict:{now:%Y-%m-%d}"
        if event_store.is_notified(self._store, key):
            return []
        event_store.mark_notified(self._store, [key])
        return [describe_conflict(groups[0])]

    def _overload(self, occurrences, now) -> list[tuple[str, str]]:
        if not self._config.get("overload_alert_enabled", True):
            return []
        try:
            threshold = float(self._config.get("overload_threshold_hours", 6) or 0)
        except (TypeError, ValueError):
            threshold = 6.0
        if threshold <= 0:
            return []
        todays = [o for o in occurrences if o.start.date() == now.date()]
        minutes = day_load_minutes(todays, now)
        if minutes < threshold * 60:
            return []
        key = f"overload:{now:%Y-%m-%d}"
        if event_store.is_notified(self._store, key):
            return []
        event_store.mark_notified(self._store, [key])
        return [describe_overload(minutes, threshold)]

    def _quiet_now(self, now: datetime) -> bool:
        if not self._config.get("quiet_hours_enabled", False):
            return False
        return in_quiet_hours(
            now,
            self._config.get("quiet_start", "22:00"),
            self._config.get("quiet_end", "08:00"),
        )


def today_summary(store, config, now: datetime = None) -> str:
    """Tray text for the current day, read straight from the store."""
    now = now or datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    try:
        events = event_store.read_range(store, day_start, day_start + timedelta(days=1))
    except Exception:  # noqa: BLE001 - 托盘文案失败不该影响主界面
        return "今天没有日程"
    return tray_summary(events, now)


def prune_notifications(conn, days: int = event_store.RETENTION_DAYS) -> int:
    """Drop notification records past the retention window."""
    cutoff = int(time.time()) - int(days) * 86400
    try:
        with conn:
            cursor = conn.execute("DELETE FROM notified WHERE fired_at < ?", (cutoff,))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Notification log sweep failed: %s", exc)
        return 0
    return cursor.rowcount
