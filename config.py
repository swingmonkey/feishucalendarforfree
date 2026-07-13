"""Configuration management for FeishuCalendarDesktop."""

import json
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Get the application directory for storing config.json.

    Platform behavior:
    - Windows frozen EXE: EXE's directory (portable, next to the .exe).
    - macOS frozen .app: ~/Library/Application Support/FeishuCalendar/
      (the .app bundle's Contents/MacOS/ is read-only).
    - Source run: script's directory.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            # .app bundle: Contents/MacOS/<exe> is read-only.
            # Use the standard macOS per-user app-support location.
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
        "auto_refresh_interval": 300,  # seconds
        "theme": "dark",  # dark | light
        "opacity": 0.95,
        "pin_to_top": True,
        "calendar_id": "primary",
        "app_id": "",
        "app_secret": "",
        "auto_start": False,
    }

    def __init__(self):
        self._path = get_app_dir() / "config.json"
        self._data: dict = {}
        self.load()

    def load(self):
        """Load configuration from file."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._data = {}
        # Fill defaults
        for key, val in self.DEFAULTS.items():
            if key not in self._data:
                self._data[key] = val

    def save(self):
        """Save configuration to file."""
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except IOError:
            pass

    def get(self, key: str, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()
