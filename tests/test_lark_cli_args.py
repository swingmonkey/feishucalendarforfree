"""Unit tests for lark_cli_args.py — shared lark-cli argument builders."""

from datetime import datetime

from lark_cli_args import (
    agenda_args,
    search_event_args,
    create_event_args,
    delete_event_args,
    get_event_args,
)

# A fixed reference time for deterministic tests
START = datetime(2026, 7, 15, 10, 0, 0)
END = datetime(2026, 7, 15, 11, 0, 0)


def _tz_suffix():
    """Get the local timezone offset suffix used by the builders."""
    from utils import get_local_tz_offset
    return get_local_tz_offset()


class TestAgendaArgs:
    def test_basic_structure(self):
        args = agenda_args(START, END)
        assert args[0] == "calendar"
        assert args[1] == "+agenda"
        assert "--start" in args
        assert "--end" in args

    def test_start_end_values(self):
        args = agenda_args(START, END)
        tz = _tz_suffix()
        start_idx = args.index("--start")
        end_idx = args.index("--end")
        assert args[start_idx + 1] == f"2026-07-15T10:00:00{tz}"
        assert args[end_idx + 1] == f"2026-07-15T11:00:00{tz}"


class TestSearchEventArgs:
    def test_basic_structure(self):
        args = search_event_args("meeting", START, END)
        assert args[0] == "calendar"
        assert args[1] == "+search-event"
        assert "--query" in args
        assert "--start" in args
        assert "--end" in args

    def test_query_value(self):
        args = search_event_args("项目周会", START, END)
        query_idx = args.index("--query")
        assert args[query_idx + 1] == "项目周会"

    def test_empty_query_omits_flag(self):
        args = search_event_args("", START, END)
        assert "--query" not in args

    def test_none_query_omits_flag(self):
        args = search_event_args(None, START, END)  # type: ignore
        assert "--query" not in args


class TestCreateEventArgs:
    def test_basic_structure(self):
        args = create_event_args("Test Event", START, END)
        assert args[0] == "calendar"
        assert args[1] == "+create"
        assert "--summary" in args
        assert "--calendar-id" in args

    def test_summary_value(self):
        args = create_event_args("团队站会", START, END)
        idx = args.index("--summary")
        assert args[idx + 1] == "团队站会"

    def test_default_calendar_id(self):
        args = create_event_args("Test", START, END)
        idx = args.index("--calendar-id")
        assert args[idx + 1] == "primary"

    def test_custom_calendar_id(self):
        args = create_event_args("Test", START, END, calendar_id="cal_123")
        idx = args.index("--calendar-id")
        assert args[idx + 1] == "cal_123"

    def test_description_optional(self):
        args = create_event_args("Test", START, END, description="")
        assert "--description" not in args

    def test_description_present(self):
        args = create_event_args("Test", START, END, description="详情")
        idx = args.index("--description")
        assert args[idx + 1] == "详情"

    def test_rrule_optional(self):
        args = create_event_args("Test", START, END, rrule=None)
        assert "--rrule" not in args

    def test_rrule_present(self):
        args = create_event_args("Test", START, END, rrule="FREQ=DAILY")
        idx = args.index("--rrule")
        assert args[idx + 1] == "FREQ=DAILY"


class TestDeleteEventArgs:
    def test_basic_structure(self):
        args = delete_event_args("primary", "evt_123")
        assert args[0] == "calendar"
        assert args[1] == "events"
        assert args[2] == "delete"
        assert "--calendar-id" in args
        assert "--event-id" in args
        assert "--need-notification" in args

    def test_default_notification_false(self):
        args = delete_event_args("primary", "evt_1")
        idx = args.index("--need-notification")
        assert args[idx + 1] == "false"

    def test_notification_true(self):
        args = delete_event_args("primary", "evt_1", need_notification=True)
        idx = args.index("--need-notification")
        assert args[idx + 1] == "true"


class TestGetEventArgs:
    def test_basic_structure(self):
        args = get_event_args("primary", "evt_456")
        assert args[0] == "calendar"
        assert args[1] == "+get"
        assert "--calendar-id" in args
        assert "--event-id" in args

    def test_values(self):
        args = get_event_args("cal_789", "evt_000")
        c_idx = args.index("--calendar-id")
        e_idx = args.index("--event-id")
        assert args[c_idx + 1] == "cal_789"
        assert args[e_idx + 1] == "evt_000"
