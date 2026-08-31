"""Offline tests for configuration recovery and persistence."""

import json

import config as config_module


def test_invalid_values_are_replaced_with_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({
            "window_width": -1,
            "window_height": "large",
            "auto_refresh_interval": True,
            "theme": "neon",
            "view_mode": "year",
            "opacity": 99,
            "pin_to_top": "yes",
            "event_colors": [],
            "calendar_id": "",
        }),
        encoding="utf-8",
    )
    cfg = config_module.Config()
    assert cfg.get("window_width") == 440
    assert cfg.get("window_height") == 640
    assert cfg.get("auto_refresh_interval") == 300
    assert cfg.get("theme") == "dark"
    assert cfg.get("view_mode") == "month"
    assert cfg.get("opacity") == 1.0
    assert cfg.get("pin_to_top") is True
    assert cfg.get("event_colors") == {}
    assert cfg.get("calendar_id") == "primary"


def test_malformed_json_recovers_to_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text("{broken", encoding="utf-8")
    cfg = config_module.Config()
    assert cfg.get("theme") == "dark"
    assert cfg.get("view_mode") == "month"


def test_save_replaces_file_atomically(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = config_module.Config()
    cfg.set("theme", "light")
    data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert data["theme"] == "light"
    assert not (tmp_path / "config.json.tmp").exists()
