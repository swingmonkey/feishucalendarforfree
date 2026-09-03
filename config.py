"""Configuration management for FeishuCalendarDesktop."""

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def get_app_dir() -> Path:
    """Get the application directory for storing config.json.

    Platform behavior:
    - Windows frozen EXE: EXE's directory (portable, next to the .exe).
    - macOS frozen .app: ~/Library/Application Support/FeishuCalendar/
    - Source run: script's directory.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            app_support = Path.home() / "Library" / "Application Support" / "FeishuCalendar"
            app_support.mkdir(parents=True, exist_ok=True)
            return app_support
        return Path(sys.executable).parent
    return Path(__file__).parent


class Config:
    """Manages application configuration persisted to JSON."""

    DEFAULTS = {
        "window_x": 100,
        "window_y": 100,
        "window_width": 440,
        "window_height": 640,
        "auto_refresh_interval": 300,
        "theme": "dark",
        "opacity": 0.95,
        "pin_to_top": True,
        "calendar_id": "primary",
        "auto_start": False,
        "view_mode": "month",
        "event_colors": {},
        "desktop_shortcut_created": False,
        "check_update_on_start": True,
    }

    _POSITIVE_INT_KEYS = {"window_width", "window_height", "auto_refresh_interval"}
    _ENUMS = {
        "theme": {"dark", "light"},
        "view_mode": {"month", "week"},
    }

    def __init__(self):
        self._path = get_app_dir() / "config.json"
        self._data: dict = {}
        self.load()

    @classmethod
    def _validated(cls, data: dict) -> dict:
        """Return only safe, supported persisted values, with defaults filled."""
        clean = {}
        for key, default in cls.DEFAULTS.items():
            value = data.get(key, default)
            if key in cls._POSITIVE_INT_KEYS:
                if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                    value = default
            elif key in cls._ENUMS:
                if value not in cls._ENUMS[key]:
                    value = default
            elif key == "opacity":
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    value = default
                else:
                    value = max(0.2, min(1.0, float(value)))
            elif key == "event_colors":
                if not isinstance(value, dict):
                    value = {}
            elif key in {"pin_to_top", "auto_start", "desktop_shortcut_created", "check_update_on_start"}:
                if not isinstance(value, bool):
                    value = default
            elif key == "calendar_id":
                if not isinstance(value, str) or not value.strip():
                    value = default
            clean[key] = value
        return clean

    def load(self):
        """Load configuration from file and safely recover malformed values."""
        raw = {}
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    raw = loaded
            except (json.JSONDecodeError, OSError, TypeError) as e:
                logger.warning("Failed to load config from %s: %s", self._path, e)
                raw = {}
        self._data = self._validated(raw)

    def save(self):
        """Atomically save configuration so a crash cannot leave truncated JSON."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
                f.write("\n")
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self._path)
        except OSError as e:
            logger.error("Failed to save config to %s: %s", self._path, e)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()
