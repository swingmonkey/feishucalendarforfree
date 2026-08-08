"""utils.py 日期范围与排序逻辑测试"""

from datetime import datetime

from utils import event_sort_key, month_range, wide_range


class TestMonthRange:
    def test_normal_month(self):
        start, end = month_range(datetime(2026, 3, 15, 12, 30))
        assert start == datetime(2026, 3, 1)
        assert end == datetime(2026, 3, 31, 23, 59, 59)

    def test_december(self):
        start, end = month_range(datetime(2026, 12, 5))
        assert start == datetime(2026, 12, 1)
        assert end == datetime(2026, 12, 31, 23, 59, 59)

    def test_february_leap(self):
        start, end = month_range(datetime(2028, 2, 10))
        assert end == datetime(2028, 2, 29, 23, 59, 59)


class TestWideRange:
    def test_spans_back_and_forward(self):
        start, end = wide_range(months_back=1, months_forward=1)
        assert start.day == 1
        assert start.hour == 0
        assert end.second == 59


class TestEventSortKey:
    def test_timestamp(self):
        event = {"start_time": {"timestamp": "1700000000"}}
        assert event_sort_key(event) == 1700000000.0

    def test_datetime_str(self):
        event = {"start_time": {"datetime": "2026-03-15T10:00:00"}}
        key = event_sort_key(event)
        assert isinstance(key, float)
        assert key > 0

    def test_date_str(self):
        event = {"start_time": {"date": "2026-03-15"}}
        key = event_sort_key(event)
        assert isinstance(key, float)
        assert key > 0

    def test_missing_time_sorts_last(self):
        assert event_sort_key({}) == float("inf")
        assert event_sort_key({"start_time": {}}) == float("inf")
        assert event_sort_key({"start_time": None}) == float("inf")

    def test_invalid_values_sorted_last(self):
        assert event_sort_key({"start_time": {"timestamp": "abc"}}) == float("inf")
        assert event_sort_key({"start_time": {"datetime": "not-a-date"}}) == float("inf")

    def test_sort_ordering(self):
        events = [
            {"start_time": {"date": "2026-03-20"}},
            {},
            {"start_time": {"timestamp": "1700000000"}},
            {"start_time": {"datetime": "2026-03-15T10:00:00"}},
        ]
        sorted_events = sorted(events, key=event_sort_key)
        assert sorted_events[-1] == {}  # 无时间事件排最后
