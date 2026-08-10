"""Async Lark CLI wrapper using QProcess for Qt-integrated async execution."""

import json
import sys
import shutil
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import QObject, QProcess, Signal

from lark_cli import find_lark_cli, LarkCliError
from utils import month_range, wide_range, event_sort_key


def _escape_ps_arg(arg: str) -> str:
    """Escape a single argument for PowerShell single-quoted string."""
    # Use single quotes - PowerShell treats them as literal
    # Only need to escape single quotes by doubling them
    return "'" + arg.replace("'", "''") + "'"


class LarkCliAsync(QObject):
    """Async wrapper for lark-cli commands using QProcess."""

    agenda_fetched = Signal(list)
    search_fetched = Signal(list)
    fetch_error = Signal(str)
    event_created = Signal(dict)
    create_error = Signal(str)
    event_deleted = Signal(str)
    delete_error = Signal(str)
    event_updated = Signal(dict)
    update_error = Signal(str)

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self._bin = find_lark_cli()
        self._config = config

    def _start_process(self, args: list[str], on_success, on_error):
        """Start a lark-cli process asynchronously via QProcess.

        Note: lark-cli uses its own stored credentials from `auth login`.
        We do NOT pass --app-id/--app-secret because shortcut commands
        like +agenda don't support those flags (causes 'unknown flag' error).
        """
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAll()).decode("utf-8", errors="replace").strip()
            # Release the QProcess once the call completes to avoid leaking
            # one process object per request.
            process.deleteLater()

            if not output:
                on_error("lark-cli 没有输出，请检查授权状态\n\n请确认已完成以下步骤：\n1. lark-cli auth login --scope \"calendar:calendar.event:read\" --scope \"calendar:calendar:read\"\n2. 在浏览器中扫码授权")
                return

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                # Try line by line for multi-line output
                for line in output.split("\n"):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                else:
                    on_error(f"无法解析 lark-cli 输出:\n{output[:500]}")
                    return

            if data.get("ok"):
                on_success(data.get("data", []))
            else:
                err = data.get("error", {})
                msg = err.get("message", "未知错误")
                if err.get("hint"):
                    msg += f"\n{err['hint']}"

                # Detect missing scope errors and provide exact fix command
                err_type = err.get("type", "")
                full_msg = msg.lower()
                if "missing required scope" in full_msg or ("scope" in full_msg and "calendar" in full_msg):
                    import re
                    # Strategy 1: Extract from lark-cli's own hint: --scope "calendar:xxx"
                    scope_match = re.search(r'--scope\s+["\']([^"\']+)["\']', msg)
                    if scope_match:
                        scope = scope_match.group(1)
                        msg += f'\n\n请运行以下命令授权缺失的权限：\nlark-cli auth login --scope "{scope}"'
                    else:
                        # Strategy 2: Extract from "missing required scope(s): xxx"
                        scope_match = re.search(r'missing required scope\(s\):\s*(\S+)', msg, re.IGNORECASE)
                        if scope_match:
                            scope = scope_match.group(1).rstrip('.,;')
                            msg += f'\n\n请运行以下命令授权缺失的权限：\nlark-cli auth login --scope "{scope}"'
                        else:
                            # Strategy 3: Match calendar:xxx.yyy.zzz pattern (include dots)
                            scope_match = re.search(r'(calendar:[\w:.]+)', msg)
                            if scope_match:
                                scope = scope_match.group(1)
                                msg += f'\n\n请运行以下命令授权缺失的权限：\nlark-cli auth login --scope "{scope}"'
                            else:
                                msg += '\n\n请运行以下命令授权日历权限：\nlark-cli auth login --scope "calendar:calendar.event:read" --scope "calendar:calendar:read"'
                elif err_type == "authorization" or "auth" in full_msg:
                    msg += '\n\n请运行: lark-cli auth login --scope "calendar:calendar.event:read" --scope "calendar:calendar:read"'
                on_error(msg)

        process.finished.connect(on_finished)

        # Build full command — lark-cli uses stored auth, no app credentials needed
        full_cmd = [self._bin] + args + ["--format", "json"]

        # On Windows, lark-cli is typically a npm .CMD wrapper.
        # QProcess cannot execute .CMD directly. 优先定位真实 node 入口
        # (node_modules/@larksuite/cli/scripts/run.js) 用 node 直调：
        # QProcess -> node 是单一参数解析层，JSON 里的双引号能正确往返；
        # 旧方案经 PowerShell 中转时，QProcess 会把 JSON 的双引号转义成 \"，
        # PowerShell 单引号字符串原样透传，导致 lark-cli 收到非法 JSON
        # （报错 "--data invalid JSON FORMAT"）。
        if sys.platform == "win32":
            run_js = None
            try:
                bin_path = Path(self._bin).resolve()
                cand = bin_path.parent / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
                if cand.is_file():
                    run_js = str(cand)
            except (OSError, ValueError):
                run_js = None
            node = shutil.which("node")
            if node and run_js:
                # 注意：这里不能再带 full_cmd（其首元素是 lark-cli.CMD 路径），
                # 否则 lark-cli 会把该路径当作子命令（报 unknown command "....CMD"）。
                # node run.js 直接吃原始 args。
                process.start(node, [run_js] + args + ["--format", "json"])
            else:
                # 回退：PowerShell 中转（旧逻辑）
                ps_parts = [_escape_ps_arg(c) for c in full_cmd]
                ps_command = "& " + " ".join(ps_parts)
                process.start("powershell.exe", [
                    "-NoProfile",
                    "-Command",
                    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " + ps_command,
                ])
        else:
            process.start(full_cmd[0], full_cmd[1:])

    def fetch_agenda(self, date: datetime, monthly: bool = False):
        """Fetch calendar agenda for a date range.

        Args:
            date: Reference date.
            monthly: If True, fetch the entire month containing date.
        """
        tz = "+08:00"
        if monthly:
            start, end = month_range(date)
        else:
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(hour=23, minute=59, second=59)
        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        def on_success(data):
            if isinstance(data, list):
                data.sort(key=event_sort_key)
                self.agenda_fetched.emit(data)
            else:
                self.agenda_fetched.emit([])

        def on_error(msg):
            self.fetch_error.emit(msg)

        self._start_process(
            ["calendar", "+agenda", "--start", start_str, "--end", end_str],
            on_success,
            on_error,
        )

    def search_events(self, months_back: int = 12, months_forward: int = 3):
        """Fetch events from a wide date range for search purposes.

        Args:
            months_back: How many months before now to search.
            months_forward: How many months after now to search.
        """
        tz = "+08:00"
        start, end = wide_range(months_back, months_forward)
        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        def on_success(data):
            if isinstance(data, list):
                data.sort(key=event_sort_key)
                self.search_fetched.emit(data)
            else:
                self.search_fetched.emit([])

        def on_error(msg):
            self.fetch_error.emit(msg)

        self._start_process(
            ["calendar", "+agenda", "--start", start_str, "--end", end_str],
            on_success,
            on_error,
        )

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        calendar_id: str = "primary",
        rrule: str = None,
    ):
        """Create a new calendar event.

        ``rrule`` is an optional RFC5545 recurrence rule passed straight through
        to ``lark-cli calendar +create --rrule``. ``None``/empty means a normal
        one-off event.
        """
        tz = "+08:00"
        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        args = [
            "calendar",
            "+create",
            "--summary",
            summary,
            "--start",
            start_str,
            "--end",
            end_str,
            "--calendar-id",
            calendar_id,
        ]
        if description:
            args.extend(["--description", description])
        if rrule:
            args.extend(["--rrule", rrule])

        def on_success(data):
            self.event_created.emit(data if isinstance(data, dict) else {})

        def on_error(msg):
            self.create_error.emit(msg)

        self._start_process(args, on_success, on_error)

    def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        need_notification: bool = False,
    ):
        """Delete a calendar event."""
        args = [
            "calendar",
            "events",
            "delete",
            "--calendar-id",
            calendar_id,
            "--event-id",
            event_id,
            "--need-notification",
            str(need_notification).lower(),
        ]

        def on_success(data):
            self.event_deleted.emit(event_id)

        def on_error(msg):
            self.delete_error.emit(msg)

        self._start_process(args, on_success, on_error)

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: str = "",
        start: datetime = None,
        end: datetime = None,
        description: str = "",
        rrule: str = None,
    ):
        """Update an existing calendar event via raw API call.

        Uses lark-cli's raw API mode: `api PATCH /open-apis/...`
        ``rrule`` optionally replaces the recurrence rule (RFC5545).
        """
        body = {}
        if summary:
            body["summary"] = summary
        if start:
            tz = "+08:00"
            body["start_time"] = {
                "timestamp": str(int(start.timestamp())),
                "timezone": "Asia/Shanghai",
            }
        if end:
            body["end_time"] = {
                "timestamp": str(int(end.timestamp())),
                "timezone": "Asia/Shanghai",
            }
        if description is not None:
            body["description"] = description
        if rrule is not None:
            body["recurrence"] = rrule

        # Resolve calendar_id
        if not calendar_id or calendar_id == "primary":
            calendar_id = "primary"

        api_path = f"/open-apis/calendar/v4/calendars/{calendar_id}/events/{event_id}"
        args = [
            "api",
            "PATCH",
            api_path,
            "--data",
            json.dumps(body),
        ]

        def on_success(data):
            self.event_updated.emit(data if isinstance(data, dict) else {})

        def on_error(msg):
            self.update_error.emit(msg)

        self._start_process(args, on_success, on_error)
