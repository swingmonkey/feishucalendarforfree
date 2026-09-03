"""Unit tests for models_event.py — time parsing, recurrence expansion,
Markdown conversion, color helpers and task-list round-tripping.

These tests are pure-Python (no Qt display required) and run under
``QT_QPA_PLATFORM=offscreen`` in CI.
"""

from datetime import datetime, timedelta

import pytest

from models_event import (
    PALETTE,
    parse_event_time,
    is_all_day_event,
    expand_recurrence,
    expand_events_for_range,
    has_recurrence,
    markdown_to_html,
    parse_task_list,
    rebuild_description,
    get_event_color,
    set_event_color,
    _parse_rrule,
    _add_months,
)


# ─────────────────────────────────────────────────────────────────────────────
# parse_event_time
# ─────────────────────────────────────────────────────────────────────────────

class TestParseEventTime:
    def test_timestamp(self):
        dt = parse_event_time({"timestamp": "1700000000", "timezone": "Asia/Shanghai"})
        assert isinstance(dt, datetime)
        assert dt == datetime.fromtimestamp(1700000000)

    def test_datetime_iso(self):
        dt = parse_event_time({"datetime": "2026-07-15T10:00:00+08:00"})
        assert dt == datetime(2026, 7, 15, 10, 0, 0)

    def test_datetime_naive(self):
        dt = parse_event_time({"datetime": "2026-07-15T10:00:00"})
        assert dt == datetime(2026, 7, 15, 10, 0, 0)

    def test_date_only(self):
        dt = parse_event_time({"date": "2026-07-15", "timezone": "UTC"})
        assert dt == datetime(2026, 7, 15, 0, 0, 0)

    def test_empty_dict_returns_now(self):
        dt = parse_event_time({})
        assert isinstance(dt, datetime)
        # Should be very close to now
        assert abs((dt - datetime.now()).total_seconds()) < 5

    def test_non_dict_returns_now(self):
        dt = parse_event_time("not a dict")
        assert isinstance(dt, datetime)

    def test_invalid_timestamp_falls_through(self):
        # Invalid timestamp but valid datetime should use datetime
        dt = parse_event_time({"timestamp": "abc", "datetime": "2026-01-01T09:00:00"})
        assert dt == datetime(2026, 1, 1, 9, 0, 0)


# ─────────────────────────────────────────────────────────────────────────────
# is_all_day_event
# ─────────────────────────────────────────────────────────────────────────────

class TestIsAllDayEvent:
    def test_all_day_true(self):
        ev = {"start_time": {"date": "2026-07-15", "timezone": "UTC"}}
        assert is_all_day_event(ev) is True

    def test_timed_event_false(self):
        ev = {"start_time": {"datetime": "2026-07-15T10:00:00+08:00"}}
        assert is_all_day_event(ev) is False

    def test_timestamp_event_false(self):
        ev = {"start_time": {"timestamp": "1700000000"}}
        assert is_all_day_event(ev) is False

    def test_date_and_datetime_false(self):
        # Has both date and datetime — not all-day
        ev = {"start_time": {"date": "2026-07-15", "datetime": "2026-07-15T10:00:00+08:00"}}
        assert is_all_day_event(ev) is False

    def test_missing_start_time(self):
        assert is_all_day_event({}) is False


# ─────────────────────────────────────────────────────────────────────────────
# Recurrence: _parse_rrule, _add_months
# ─────────────────────────────────────────────────────────────────────────────

class TestParseRrule:
    def test_daily(self):
        parts = _parse_rrule("FREQ=DAILY;INTERVAL=1")
        assert parts["FREQ"] == "DAILY"
        assert parts["INTERVAL"] == "1"

    def test_weekly_byday(self):
        parts = _parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        assert parts["FREQ"] == "WEEKLY"
        assert parts["BYDAY"] == "MO,WE,FR"

    def test_count_and_until(self):
        parts = _parse_rrule("FREQ=MONTHLY;COUNT=12;UNTIL=20270101T000000Z")
        assert parts["COUNT"] == "12"
        assert parts["UNTIL"] == "20270101T000000Z"

    def test_empty_string(self):
        assert _parse_rrule("") == {}

    def test_none(self):
        assert _parse_rrule(None) == {}

    def test_list_input(self):
        assert _parse_rrule(["FREQ=DAILY"]) == {"FREQ": "DAILY"}


class TestAddMonths:
    def test_simple_add(self):
        assert _add_months(datetime(2026, 1, 15), 1) == datetime(2026, 2, 15)

    def test_year_wrap(self):
        assert _add_months(datetime(2026, 12, 15), 1) == datetime(2027, 1, 15)

    def test_multiple_months(self):
        assert _add_months(datetime(2026, 1, 15), 14) == datetime(2027, 3, 15)

    def test_day_clamp_jan31_to_feb(self):
        # Jan 31 + 1 month -> Feb 28 (or 29 in leap year)
        result = _add_months(datetime(2026, 1, 31), 1)
        assert result.month == 2
        assert result.day == 28  # 2026 is not a leap year

    def test_day_clamp_leap_year(self):
        result = _add_months(datetime(2024, 1, 31), 1)
        assert result.day == 29  # 2024 is a leap year


# ─────────────────────────────────────────────────────────────────────────────
# expand_recurrence
# ─────────────────────────────────────────────────────────────────────────────

def _make_event(
    start="2026-07-15T10:00:00+08:00",
    end="2026-07-15T11:00:00+08:00",
    recurrence=None,
    event_id="evt_1",
):
    ev = {
        "event_id": event_id,
        "summary": "Recurring Event",
        "start_time": {"datetime": start},
        "end_time": {"datetime": end},
    }
    if recurrence is not None:
        ev["recurrence"] = recurrence
    return ev


RANGE_START = datetime(2026, 7, 1)
RANGE_END = datetime(2026, 7, 31, 23, 59, 59)


class TestExpandRecurrence:
    def test_no_recurrence_returns_empty(self):
        ev = _make_event(recurrence=None)
        assert expand_recurrence(ev, RANGE_START, RANGE_END) == []

    def test_empty_recurrence_string(self):
        ev = _make_event(recurrence="")
        assert expand_recurrence(ev, RANGE_START, RANGE_END) == []

    def test_daily_in_range(self):
        ev = _make_event(
            start="2026-07-10T10:00:00+08:00",
            recurrence="FREQ=DAILY",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        # July 10-31 = 22 occurrences
        assert len(occs) == 22
        assert all(o["_is_recurring_instance"] for o in occs)
        assert all(o["_recurrence_key"].startswith("evt_1@") for o in occs)

    def test_daily_with_count(self):
        ev = _make_event(
            start="2026-07-10T10:00:00+08:00",
            recurrence="FREQ=DAILY;COUNT=5",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) == 5

    def test_daily_with_interval(self):
        ev = _make_event(
            start="2026-07-01T10:00:00+08:00",
            recurrence="FREQ=DAILY;INTERVAL=2",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        # July 1,3,5,...,31 = 16 occurrences
        assert len(occs) == 16

    def test_weekly_byday_mwfw(self):
        ev = _make_event(
            start="2026-07-06T10:00:00+08:00",  # Monday
            recurrence="FREQ=WEEKLY;BYDAY=MO,WE,FR",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        # July 2026: MO=6,13,20,27; WE=8,15,22,29; FR=10,17,24,31 = 12
        assert len(occs) == 12
        weekdays = {o["start_time"]["datetime"][:10] for o in occs}
        assert "2026-07-06" in weekdays
        assert "2026-07-08" in weekdays
        assert "2026-07-10" in weekdays

    def test_weekly_with_interval(self):
        ev = _make_event(
            start="2026-07-06T10:00:00+08:00",
            recurrence="FREQ=WEEKLY;INTERVAL=2;BYDAY=MO",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        # Every 2 weeks on Monday: July 6, 20 = 2 (Aug 3 is out of range)
        assert len(occs) == 2

    def test_monthly(self):
        ev = _make_event(
            start="2026-07-15T10:00:00+08:00",
            recurrence="FREQ=MONTHLY",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) == 1
        assert occs[0]["start_time"]["datetime"].startswith("2026-07-15")

    def test_monthly_before_range_fast_forward(self):
        ev = _make_event(
            start="2026-01-15T10:00:00+08:00",
            recurrence="FREQ=MONTHLY",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) == 1
        assert occs[0]["start_time"]["datetime"].startswith("2026-07-15")

    def test_yearly(self):
        ev = _make_event(
            start="2026-07-15T10:00:00+08:00",
            recurrence="FREQ=YEARLY",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) == 1

    def test_until_terminates(self):
        ev = _make_event(
            start="2026-07-10T10:00:00+08:00",
            recurrence="FREQ=DAILY;UNTIL=20260715T000000Z",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        # July 10,11,12,13,14 (until July 15 00:00 UTC = July 15 08:00 CST,
        # so July 15 10:00 CST event is after UNTIL -> excluded)
        assert len(occs) == 5

    def test_occurrence_preserves_duration(self):
        ev = _make_event(
            start="2026-07-10T10:00:00+08:00",
            end="2026-07-10T12:30:00+08:00",  # 2.5 hour duration
            recurrence="FREQ=DAILY",
        )
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) > 0
        first = occs[0]
        start_dt = parse_event_time(first["start_time"])
        end_dt = parse_event_time(first["end_time"])
        assert (end_dt - start_dt) == timedelta(hours=2, minutes=30)

    def test_invalid_freq_returns_empty(self):
        ev = _make_event(recurrence="FREQ=INVALID")
        assert expand_recurrence(ev, RANGE_START, RANGE_END) == []

    def test_recurrence_as_list(self):
        ev = _make_event(recurrence=["FREQ=DAILY"])
        ev["start_time"] = {"datetime": "2026-07-10T10:00:00+08:00"}
        occs = expand_recurrence(ev, RANGE_START, RANGE_END)
        assert len(occs) == 22


class TestExpandEventsForRange:
    def test_mix_recurring_and_non_recurring(self):
        recurring = _make_event(
            start="2026-07-10T10:00:00+08:00",
            recurrence="FREQ=DAILY;COUNT=3",
            event_id="rec",
        )
        one_off = _make_event(
            start="2026-07-20T10:00:00+08:00",
            recurrence=None,
            event_id="one",
        )
        result = expand_events_for_range([recurring, one_off], RANGE_START, RANGE_END)
        # Original recurring + 3 occurrences + one_off = 5
        assert len(result) == 5

    def test_non_recurring_passes_through(self):
        ev = _make_event(recurrence=None)
        result = expand_events_for_range([ev], RANGE_START, RANGE_END)
        assert result == [ev]


class TestHasRecurrence:
    def test_with_string(self):
        assert has_recurrence({"recurrence": "FREQ=DAILY"}) is True

    def test_with_list(self):
        assert has_recurrence({"recurrence": ["FREQ=DAILY"]}) is True

    def test_empty_string(self):
        assert has_recurrence({"recurrence": ""}) is False

    def test_none(self):
        assert has_recurrence({"recurrence": None}) is False

    def test_missing_key(self):
        assert has_recurrence({}) is False


# ─────────────────────────────────────────────────────────────────────────────
# markdown_to_html
# ─────────────────────────────────────────────────────────────────────────────

class TestMarkdownToHtml:
    def test_empty(self):
        assert markdown_to_html("") == ""
        assert markdown_to_html(None) == ""

    def test_plain_text(self):
        html = markdown_to_html("Hello world")
        assert "<p>Hello world</p>" in html

    def test_headings(self):
        html = markdown_to_html("# H1\n## H2\n### H3")
        assert "<h1>H1</h1>" in html
        assert "<h2>H2</h2>" in html
        assert "<h3>H3</h3>" in html

    def test_bold(self):
        html = markdown_to_html("**bold text**")
        assert "<b>bold text</b>" in html

    def test_italic(self):
        html = markdown_to_html("*italic text*")
        assert "<i>italic text</i>" in html

    def test_inline_code(self):
        html = markdown_to_html("Use `print()` to output")
        assert "<code>print()</code>" in html

    def test_link(self):
        html = markdown_to_html("[GitHub](https://github.com)")
        assert 'href="https://github.com"' in html
        assert ">GitHub</a>" in html

    def test_mailto_link(self):
        html = markdown_to_html("[Email](mailto:test@example.com)")
        assert 'href="mailto:test@example.com"' in html

    def test_unordered_list(self):
        html = markdown_to_html("- item1\n- item2\n- item3")
        assert "<ul>" in html
        assert "</ul>" in html
        assert html.count("<li>") == 3

    def test_ordered_list(self):
        html = markdown_to_html("1. first\n2. second\n3. third")
        assert "<ul>" in html
        assert "first" in html
        assert "second" in html
        assert "third" in html

    def test_task_list_unchecked(self):
        html = markdown_to_html("- [ ] task one")
        assert '<input type="checkbox" disabled >' in html
        assert "task one" in html

    def test_task_list_checked(self):
        html = markdown_to_html("- [x] done task")
        assert 'checked' in html
        assert "done task" in html

    def test_task_list_uppercase_x(self):
        html = markdown_to_html("- [X] done task")
        assert 'checked' in html

    def test_blockquote(self):
        html = markdown_to_html("> quoted text")
        assert "<blockquote>quoted text</blockquote>" in html

    def test_horizontal_rule(self):
        html = markdown_to_html("---")
        assert "<hr>" in html

    def test_html_escaping(self):
        html = markdown_to_html("<script>alert('xss')</script>")
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_ampersand_escaping(self):
        html = markdown_to_html("A & B")
        assert "A &amp; B" in html

    def test_multiline_paragraphs(self):
        html = markdown_to_html("para1\n\npara2")
        assert html.count("<p>") == 2

    def test_single_char_line_not_ordered_list(self):
        # "1" alone should be a paragraph, not an ordered list item
        html = markdown_to_html("1")
        assert "<p>1</p>" in html


# ─────────────────────────────────────────────────────────────────────────────
# parse_task_list / rebuild_description
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskList:
    def test_parse_mixed(self):
        desc = "Some notes\n- [ ] task1\n- [x] task2\nMore text"
        tasks = parse_task_list(desc)
        assert len(tasks) == 2
        assert tasks[0] == {"done": False, "text": "task1"}
        assert tasks[1] == {"done": True, "text": "task2"}

    def test_parse_empty(self):
        assert parse_task_list("") == []
        assert parse_task_list(None) == []

    def test_parse_no_tasks(self):
        assert parse_task_list("Just a description") == []

    def test_rebuild_preserves_non_task_text(self):
        orig = "Header notes\n- [ ] old task\nFooter"
        tasks = [{"done": True, "text": "updated task"}]
        result = rebuild_description(orig, tasks)
        assert "Header notes" in result
        assert "Footer" in result
        assert "- [x] updated task" in result
        assert "old task" not in result

    def test_rebuild_empty_tasks_removes_task_lines(self):
        orig = "Notes\n- [ ] remove me"
        result = rebuild_description(orig, [])
        assert "remove me" not in result
        assert "Notes" in result

    def test_round_trip(self):
        orig = "Meeting notes\n- [ ] prepare slides\n- [x] send invite"
        tasks = parse_task_list(orig)
        rebuilt = rebuild_description(orig, tasks)
        tasks2 = parse_task_list(rebuilt)
        assert tasks == tasks2


# ─────────────────────────────────────────────────────────────────────────────
# Color helpers
# ─────────────────────────────────────────────────────────────────────────────

class FakeConfig:
    """Minimal in-memory config for testing color helpers."""
    def __init__(self):
        self._data = {"event_colors": {}}

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestColorHelpers:
    def test_palette_has_entries(self):
        assert len(PALETTE) >= 6
        for name, hex_color in PALETTE:
            assert name
            assert hex_color.startswith("#")

    def test_get_uncolored_returns_none(self):
        config = FakeConfig()
        assert get_event_color(config, "evt_1") is None

    def test_set_and_get_color(self):
        config = FakeConfig()
        set_event_color(config, "evt_1", "#FF0000")
        assert get_event_color(config, "evt_1") == "#FF0000"

    def test_clear_color_with_none(self):
        config = FakeConfig()
        set_event_color(config, "evt_1", "#FF0000")
        set_event_color(config, "evt_1", None)
        assert get_event_color(config, "evt_1") is None

    def test_none_config_safe(self):
        assert get_event_color(None, "evt_1") is None
        # Should not raise
        set_event_color(None, "evt_1", "#FF0000")
