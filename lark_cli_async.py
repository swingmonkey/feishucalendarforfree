"""Async Lark CLI wrapper using QProcess for Qt-integrated async execution."""

import json
import sys
import shutil
from datetime import datetime, timedelta
from typing import Optional
from PySide6.QtCore import QObject, QProcess, Signal

from lark_cli import find_lark_cli, LarkCliError


def _escape_ps_arg(arg: str) -> str:
    """Escape a single argument for PowerShell single-quoted string."""
    # Use single quotes - PowerShell treats them as literal
    # Only need to escape single quotes by doubling them
    return "'" + arg.replace("'", "''") + "'"


class LarkCliAsync(QObject):
    """Async wrapper for lark-cli commands using QProcess."""

    agenda_fetched = Signal(list)
    fetch_error = Signal(str)
    event_created = Signal(dict)
    create_error = Signal(str)
    event_deleted = Signal(str)
    delete_error = Signal(str)

    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self._bin = find_lark_cli()
        self._config = config

    def _get_auth_args(self) -> list[str]:
        """Return --app-id/--app-secret args if configured."""
        if self._config:
            app_id = self._config.get("app_id", "")
            app_secret = self._config.get("app_secret", "")
            if app_id and app_secret:
                return ["--app-id", app_id, "--app-secret", app_secret]
        return []

    def _start_process(self, args: list[str], on_success, on_error):
        """Start a lark-cli process asynchronously via QProcess."""
        process = QProcess(self)
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        def on_finished(exit_code, exit_status):
            output = bytes(process.readAll()).decode("utf-8", errors="replace").strip()

            if not output:
                on_error("lark-cli 没有输出，请检查授权状态")
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
                    on_error(f"无法解析 lark-cli 输出: {output[:300]}")
                    return

            if data.get("ok"):
                on_success(data.get("data", []))
            else:
                err = data.get("error", {})
                msg = err.get("message", "未知错误")
                if err.get("hint"):
                    msg += f"\n{err['hint']}"
                on_error(msg)

        process.finished.connect(on_finished)

        # Build full command with optional app credentials
        full_cmd = [self._bin] + args + self._get_auth_args() + ["--format", "json"]

        # On Windows, lark-cli is typically a .CMD file
        # QProcess cannot execute .CMD directly, and cmd.exe is blocked
        # Solution: use PowerShell with & call operator to run the command
        if sys.platform == "win32":
            # Build PowerShell command string with proper escaping
            # Use & call operator so PowerShell treats the quoted path as a command
            # Set OutputEncoding to UTF-8 to avoid mojibake on Chinese Windows
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
            # First day of the month
            start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Last day of the month
            if date.month == 12:
                end = date.replace(year=date.year + 1, month=1, day=1) - timedelta(seconds=1)
            else:
                end = date.replace(month=date.month + 1, day=1) - timedelta(seconds=1)
        else:
            start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start.replace(hour=23, minute=59, second=59)
        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        def on_success(data):
            if isinstance(data, list):
                # Sort by start_time: use 'datetime' for timed events,
                # fall back to 'date' for all-day events
                def sort_key(e):
                    st = e.get("start_time", {})
                    if not isinstance(st, dict):
                        return ""
                    return st.get("datetime", "") or st.get("date", "") or ""
                data.sort(key=sort_key)
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

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        calendar_id: str = "primary",
    ):
        """Create a new calendar event."""
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
