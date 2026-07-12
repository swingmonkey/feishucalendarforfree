"""Lark CLI wrapper - encapsulates all lark-cli subprocess calls."""

import json
import subprocess
import shutil
from datetime import datetime, timedelta
from typing import Optional


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
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=0x08000000,  # CREATE_NO_WINDOW
            )
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
        tz = "+08:00"
        if start is None:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end is None:
            end = start.replace(hour=23, minute=59, second=59)

        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        args = ["calendar", "+agenda", "--start", start_str, "--end", end_str]
        result = self._run(args)
        return result.get("data", [])

    def create_event(
        self,
        summary: str,
        start: datetime,
        end: datetime,
        description: str = "",
        calendar_id: str = "primary",
    ) -> dict:
        """Create a new calendar event.

        Args:
            summary: Event title.
            start: Start datetime.
            end: End datetime.
            description: Event description.
            calendar_id: Calendar ID (default: primary).

        Returns:
            Created event data.
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

        result = self._run(args)
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
        self._run(args)
        return True

    def get_event(self, calendar_id: str, event_id: str) -> dict:
        """Get details of a single calendar event.

        Args:
            calendar_id: Calendar ID.
            event_id: Event ID.

        Returns:
            Event detail data.
        """
        args = [
            "calendar",
            "+get",
            "--calendar-id",
            calendar_id,
            "--event-id",
            event_id,
        ]
        result = self._run(args)
        return result.get("data", {})

    def search_events(
        self,
        query: str = "",
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Search calendar events by keyword and time range.

        Args:
            query: Search keyword.
            start: Start datetime.
            end: End datetime.

        Returns:
            List of matching events.
        """
        tz = "+08:00"
        if start is None:
            start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        if end is None:
            end = start + timedelta(days=7)

        start_str = start.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")
        end_str = end.strftime(f"%Y-%m-%dT%H:%M:%S{tz}")

        args = [
            "calendar",
            "+search-event",
            "--start",
            start_str,
            "--end",
            end_str,
        ]
        if query:
            args.extend(["--query", query])

        result = self._run(args)
        return result.get("data", {}).get("items", [])
