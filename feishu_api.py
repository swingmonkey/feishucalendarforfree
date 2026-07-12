"""Direct Feishu Calendar API client - no lark-cli dependency.

Uses Feishu Open API v4 with app credentials (App ID + App Secret).
Requires the app to have calendar permissions and bot capability enabled.
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


class FeishuApiError(Exception):
    """Feishu API error with helpful message."""

    def __init__(self, code: int, msg: str, app_id: str = ""):
        self.code = code
        self.msg = msg
        # Add helpful hints for common errors
        hints = {
            190007: "\n\n提示：应用未开启机器人能力。请在飞书开放平台 → 应用能力 → 机器人，开启机器人功能。",
            191000: "\n\n提示：日历未找到。请确保应用有日历访问权限。",
            191002: "\n\n提示：应用没有日历访问权限。请在飞书开放平台添加日历权限：\n- calendar:calendar:readonly（读取日历）\n- calendar:calendar（管理日历）",
            99991663: "\n\n提示：App ID 或 App Secret 不正确，请检查。",
            99991661: "\n\n提示：tenant_access_token 无效或已过期。",
            99991672: "\n\n提示：应用缺少所需权限。请前往飞书开放平台添加日历权限：\n- calendar:calendar:readonly（读取日历）\n- calendar:calendar（管理日历）\n- 开启机器人能力\n- 创建版本并发布",
        }
        hint = hints.get(code, "")

        # Extract permission link from Feishu API error message
        if app_id and code == 99991672:
            hint += f"\n\n一键开通权限：\nhttps://open.feishu.cn/app/{app_id}/auth?q=calendar:calendar:readonly,calendar:calendar&op_from=openapi&token_type=tenant"

        super().__init__(f"[{code}] {msg}{hint}")


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
        self._calendar_id: Optional[str] = None

    def _get_token(self) -> str:
        """Get or refresh tenant_access_token."""
        if self._token and self._token_expiry and datetime.now() < self._token_expiry:
            return self._token

        url = f"{FEISHU_BASE}/auth/v3/tenant_access_token/internal"
        body = json.dumps({"app_id": self._app_id, "app_secret": self._app_secret}).encode()
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            raise Exception(f"获取 token 网络错误: HTTP {e.code}")
        except urllib.error.URLError as e:
            raise Exception(f"获取 token 网络错误: {e.reason}")

        if data.get("code") != 0:
            raise FeishuApiError(data.get("code", -1), data.get("msg", "未知错误"))
        self._token = data["tenant_access_token"]
        self._token_expiry = datetime.now() + timedelta(seconds=data.get("expire", 7200) - 300)
        return self._token

    def _api_call(self, method: str, path: str, params: dict = None, body: dict = None) -> dict:
        """Make an authenticated API call to Feishu Open API v4."""
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
                "Content-Type": "application/json; charset=utf-8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            # Try to read error response body
            try:
                err_body = e.read().decode()
                err_data = json.loads(err_body)
                raise FeishuApiError(
                    err_data.get("code", e.code),
                    err_data.get("msg", f"HTTP {e.code}"),
                    self._app_id,
                )
            except (json.JSONDecodeError, UnicodeDecodeError):
                raise Exception(f"API 调用失败: HTTP {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"网络错误: {e.reason}")

        if result.get("code") != 0:
            raise FeishuApiError(
                result.get("code", -1),
                result.get("msg", "未知错误"),
                self._app_id,
            )
        return result

    def _get_primary_calendar_id(self) -> str:
        """Get the primary calendar ID.

        Feishu API v4: GET /calendar/v4/calendars/primary
        Returns the primary calendar ID for the current identity.
        """
        if self._calendar_id:
            return self._calendar_id

        # Try the primary calendar endpoint
        try:
            data = self._api_call("GET", "/calendar/v4/calendars/primary")
            cal_id = data.get("data", {}).get("calendar", {}).get("calendar_id", "")
            if cal_id:
                self._calendar_id = cal_id
                return cal_id
        except FeishuApiError:
            pass

        # Fallback: list calendars and use the first one
        data = self._api_call("GET", "/calendar/v4/calendars", params={"page_size": "50"})
        calendar_list = data.get("data", {}).get("calendar_list", [])
        if not calendar_list:
            # Try old format
            calendar_list = data.get("data", {}).get("items", [])

        for cal in calendar_list:
            cal_id = cal.get("calendar_id", "")
            cal_type = cal.get("type", cal.get("calendar_type", ""))
            # Use primary or shared type calendars
            if cal_type in ("primary", "shared", ""):
                self._calendar_id = cal_id
                return cal_id

        if calendar_list:
            self._calendar_id = calendar_list[0].get("calendar_id", "")
            return self._calendar_id

        raise Exception("未找到可用日历，请确保应用有日历访问权限")

    def fetch_agenda(self, start: datetime, end: datetime, calendar_id: str = ""):
        """Fetch calendar events in a date range using Feishu API v4."""
        # Get the real calendar ID if not provided
        if not calendar_id or calendar_id == "primary":
            calendar_id = self._get_primary_calendar_id()

        path = f"/calendar/v4/calendars/{calendar_id}/events"
        params = {
            "start_time": str(int(start.timestamp())),
            "end_time": str(int(end.timestamp())),
            "page_size": "500",
        }
        all_events = []
        page_token = None
        while True:
            if page_token:
                params["page_token"] = page_token
            data = self._api_call("GET", path, params=params)
            items = data.get("data", {}).get("items", [])
            all_events.extend(items)
            page_token = data.get("data", {}).get("page_token")
            if not page_token or not data.get("data", {}).get("has_more"):
                break
        self.result_ready.emit(all_events)

    def create_event(self, summary: str, start: datetime, end: datetime,
                     description: str = "", calendar_id: str = ""):
        """Create a new calendar event using Feishu API v4."""
        if not calendar_id or calendar_id == "primary":
            calendar_id = self._get_primary_calendar_id()

        path = f"/calendar/v4/calendars/{calendar_id}/events"
        body = {
            "summary": summary,
            "start_time": {
                "timestamp": str(int(start.timestamp())),
                "timezone": "Asia/Shanghai",
            },
            "end_time": {
                "timestamp": str(int(end.timestamp())),
                "timezone": "Asia/Shanghai",
            },
            "description": description,
        }
        data = self._api_call("POST", path, body=body)
        event = data.get("data", {}).get("event", data.get("data", {}))
        self.result_ready.emit(event)

    def delete_event(self, calendar_id: str, event_id: str):
        """Delete a calendar event using Feishu API v4."""
        if not calendar_id or calendar_id == "primary":
            calendar_id = self._get_primary_calendar_id()

        path = f"/calendar/v4/calendars/{calendar_id}/events/{event_id}"
        self._api_call("DELETE", path)
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
        self._pending_op = None

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
                        dt_str = st.get("datetime", "")
                        if dt_str:
                            return dt_str
                        date_str = st.get("date", "")
                        if date_str:
                            return date_str
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
