"""Lark CLI wrapper - encapsulates all lark-cli subprocess calls."""

import json
import subprocess
import shutil
import sys
from datetime import datetime, timedelta
from typing import Optional

from lark_cli_args import (
    agenda_args,
    search_event_args,
    create_event_args,
    delete_event_args,
    get_event_args,
)


def find_lark_cli() -> str:
    """Find the lark-cli executable path."""
    path = shutil.which("lark-cli")
    if path:
        return path
    # Fallback to npm global bin
    return "lark-cli"


class LarkCliError(Exception):
    """Exception raised when lark-cli command fails."""

    def __init__(self, message: str, error_type: str = "", hint: str = ""):
        super().__init__(message)
        self.error_type = error_type
        self.hint = hint


class LarkCli:
    """Wrapper for lark-cli calendar commands."""

    def __init__(self):
        self._bin = find_lark_cli()

    def _run(self, args: list[str]) -> dict:
        """Run a lark-cli command and return parsed JSON response."""
        cmd = [self._bin] + args + ["--format", "json"]
        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": 30,
        }
        # CREATE_NO_WINDOW — Windows only, hides the console popup
        if sys.platform == "win32":
            kwargs["creationflags"] = 0x08000000
        try:
            result = subprocess.run(cmd, **kwargs)
        except subprocess.TimeoutExpired:
            raise LarkCliError("lark-cli 命令超时，请重试")
        except FileNotFoundError:
            raise LarkCliError(
                "未找到 lark-cli，请先运行: npx @larksuite/cli@latest install"
            )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Try to parse stdout as JSON
        if stdout:
            try:
                data = json.loads(stdout)
                if data.get("ok"):
                    return data
                else:
                    err = data.get("error", {})
                    raise LarkCliError(
                        err.get("message", "未知错误"),
                        err.get("type", ""),
                        err.get("hint", ""),
                    )
            except json.JSONDecodeError:
                pass

        # Try stderr
        if stderr:
            try:
                data = json.loads(stderr)
                err = data.get("error", {})
                raise LarkCliError(
                    err.get("message", stderr),
                    err.get("type", ""),
                    err.get("hint", ""),
                )
            except json.JSONDecodeError:
                raise LarkCliError(stderr)

        if result.returncode != 0:
            raise LarkCliError(f"lark-cli 返回错误码 {result.returncode}")

        return {"ok": True, "data": []}

    def check_auth(self) -> bool:
        """Check if lark-cli is configured and authorized."""
        try:
            self._run(["calendar", "+agenda"])
            return True
        except LarkCliError:
            return False

    def get_agenda(
        self, start: Optional[datetime] = None, end: Optional[datetime] = None
    ) -> list[dict]:
        """Get calendar agenda for a date range.

        Args:
            start: Start datetime (defaults to today 00:00)
            end: End datetime (defaults to today 23:59)

        Returns:
            List of event dictionaries.
        """
        if start is None:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end is None:
            end = start.replace(hour=23, minute=59, second=59)

        result = self._run(agenda_args(start, end))
        return result.get("data", [])

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        calendar_id: str = "primary",
        rrule: str = None,
    ) -> dict:
        """Create a new calendar event.

        Args:
            summary: Event title.
            start: Start datetime.
            end: End datetime.
            description: Event description.
            calendar_id: Calendar ID (default: primary).
            rrule: Optional RFC5545 recurrence rule.

        Returns:
            Created event data.
        """
        result = self._run(
            create_event_args(summary, start, end, description, calendar_id, rrule)
        )
        return result.get("data", {})

    def delete_event(
        self,
        calendar_id: str,
        event_id: str,
        need_notification: bool = False,
    ) -> bool:
        """Delete a calendar event.

        Args:
            calendar_id: Calendar ID.
            event_id: Event ID.
            need_notification: Whether to notify attendees.

        Returns:
            True if deleted successfully.
        """
        self._run(delete_event_args(calendar_id, event_id, need_notification))
        return True

    def get_event(self, calendar_id: str, event_id: str) -> dict:
        """Get details of a single calendar event.

        Args:
            calendar_id: Calendar ID.
            event_id: Event ID.

        Returns:
            Event detail data.
        """
        result = self._run(get_event_args(calendar_id, event_id))
        return result.get("data", {})

    def search_events(
        self,
        query: str = "",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Search calendar events by keyword and time range (server-side).

        Args:
            query: Search keyword.
            start: Start datetime.
            end: End datetime.

        Returns:
            List of matching events.
        """
        if start is None:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end is None:
            end = start + timedelta(days=7)

        result = self._run(search_event_args(query, start, end))
        return result.get("data", {}).get("items", [])
