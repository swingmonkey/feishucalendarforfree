"""Direct Feishu Calendar API client - no lark-cli dependency.

Uses Feishu Open API with app credentials (App ID + App Secret).
Requires the app to have calendar permissions.
"""

import json
import urllib.request
import urllib.parse
import os
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtCore import QObject, QThread, Signal


FEISHU_BASE = "https://open.feishu.cn/open-apis"

# Bypass system proxy to avoid WinError 10061 (proxy not running)
_NO_PROXY_HANDLER = urllib.request.ProxyHandler({})
_NO_PROXY_OPENER = urllib.request.build_opener(_NO_PROXY_HANDLER)
urllib.request.install_opener(_NO_PROXY_OPENER)


class FeishuApiWorker(QObject):
    """Worker that runs API calls in a background thread."""

    result_ready = Signal(object)  # emits result data or None
    error_occurred = Signal(str)   # emits error message

    def __init__(self, app_id: str, app_secret: str, parent=None):
        super().__init__(parent)
        self._app_id = app_id
        self._app_secret = app_secret
        self._token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def _get_token(self) -> str:
        """Get or refresh tenant_access_token."""
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        url = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
        body = json.dumps({"app_id": self._app_id, "app_secret": self._app_secret}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") != 0:
            raise Exception(f"获取 token 失败: {data.get('msg', '未知错误')}")
        self._token = data["tenant_access_token"]
        self._token_expiry = datetime.now() + timedelta(seconds=data.get("expire", 7200) - 300)
        return self._token

    def _api_call(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Make an authenticated API call."""
        token = self._get_token()
        url = f"{FEISHU_BASE}{path}"
        if params:
            query = urllib.parse.urlencode(params)
            url = f"{url}?{query}"

        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def fetch_agenda(self, start: datetime, end: datetime, calendar_id: str = "primary"):
        """Fetch calendar events in a date range."""
        # Use primary calendar endpoint
        path = "/calendar/v1/calendars/primary/events"
        params = {
            "start_time": str(int(start.timestamp())),
            "end_time": str(int(end.timestamp())),
            "page_size": "200",
        }
        all_events = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            data = self._api_call("GET", path, params=params)
            if data.get("code") != 0:
                raise Exception(f"获取日程失败: {data.get('msg', '未知错误')}")
            items = data.get("data", {}).get("items", [])
            all_events.extend(items)
            page_token = data.get("data", {}).get("page_token")
            if not page_token or not data.get("data", {}).get("has_more"):
                break
        self.result_ready.emit(all_events)

    def create_event(self, summary: str, start: datetime, end: datetime,
                     description: str = "", calendar_id: str = "primary"):
        """Create a new calendar event."""
        path = "/calendar/v1/calendars/primary/events"
        body = {
            "summary": summary,
            "start_time": str(int(start.timestamp())),
            "end_time": str(int(end.timestamp())),
            "description": description,
        }
        data = self._api_call("POST", path, body=body)
        if data.get("code") != 0:
            raise Exception(f"创建日程失败: {data.get('msg', '未知错误')}")
        self.result_ready.emit(data.get("data", {}).get("event", {}))

    def delete_event(self, calendar_id: str, event_id: str):
        """Delete a calendar event."""
        path = f"/calendar/v1/calendars/primary/events/{event_id}"
        data = self._api_call("DELETE", path)
        if data.get("code") != 0:
            raise Exception(f"删除日程失败: {data.get('msg', '未知错误')}")
        self.result_ready.emit(event_id)


class FeishuApiAsync(QObject):
    """Async wrapper for FeishuApiWorker, with same signal interface as LarkCliAsync."""

    agenda_fetched = Signal(list)
    fetch_error = Signal(str)
    event_created = Signal(dict)
    create_error = Signal(str)
    event_deleted = Signal(str)
    delete_error = Signal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker = FeishuApiWorker(
            config.get("app_id", ""),
            config.get("app_secret", ""),
            parent=self,
        )
        # Connect worker signals
        self._worker.result_ready.connect(self._on_result)
        self._worker.error_occurred.connect(self._on_error)
        self._pending_op = None  # track what operation we're doing

    def _on_result(self, data):
        if self._pending_op == "agenda":
            if isinstance(data, list):
                # Sort by start_time
                def sort_key(e):
                    st = e.get("start_time", {})
                    if isinstance(st, dict):
                        ts = st.get("timestamp", "")
                        if ts:
                            return int(ts)
                    return 0
                data.sort(key=sort_key)
                self.agenda_fetched.emit(data)
            else:
                self.agenda_fetched.emit([])
        elif self._pending_op == "create":
            self.event_created.emit(data if isinstance(data, dict) else {})
        elif self._pending_op == "delete":
            self.event_deleted.emit(str(data))
        self._pending_op = None

    def _on_error(self, msg):
        if self._pending_op == "agenda":
            self.fetch_error.emit(msg)
        elif self._pending_op == "create":
            self.create_error.emit(msg)
        elif self._pending_op == "delete":
            self.delete_error.emit(msg)
        self._pending_op = None

    def _run_async(self, func, *args, **kwargs):
        """Run a function in a background thread."""
        self._pending_op = kwargs.pop("_op", None)
        thread = QThread(self)
        worker = FeishuApiWorker(
            self._config.get("app_id", ""),
            self._config.get("app_secret", ""),
        )
        worker.moveToThread(thread)

        def run():
            try:
                func(worker, *args, **kwargs)
            except Exception as e:
                worker.error_occurred.emit(str(e))

        def cleanup():
            worker.deleteLater()
            thread.quit()
            thread.deleteLater()

        thread.started.connect(run)
        thread.finished.connect(cleanup)
        worker.result_ready.connect(self._on_result)
        worker.error_occurred.connect(self._on_error)
        thread.start()

    def fetch_agenda(self, date: datetime, monthly: bool = False):
        """Fetch calendar agenda for a date range."""
        if monthly:
            start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if date.month == 12:
                end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                end = date.replace(month=date.month + 1, day=1) - timedelta(seconds=1)
        else:
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(hour=23, minute=59, second=59)

        self._run_async(
            lambda w: w.fetch_agenda(start, end),
            _op="agenda",
        )

    def create_event(self, summary: str, start: datetime, end: datetime,
                     description: str = "", calendar_id: str = "primary"):
        self._run_async(
            lambda w: w.create_event(summary, start, end, description, calendar_id),
            _op="create",
        )

    def delete_event(self, calendar_id: str, event_id: str, need_notification: bool = False):
        self._run_async(
            lambda w: w.delete_event(calendar_id, event_id),
            _op="delete",
        )
