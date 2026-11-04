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
    # "yes" 不是合法 bool，回退默认值——v2.11.2 起默认不置顶
    assert cfg.get("pin_to_top") is False
    assert cfg.get("event_colors") == {}
    assert cfg.get("calendar_id") == "primary"
    assert cfg.get("auth_completed") is False
    assert cfg.get("auth_user") == ""


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


def test_install_id_valid_value_is_preserved(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    install_id = "0123456789abcdef0123456789abcdef"
    (tmp_path / "config.json").write_text(
        json.dumps({"install_id": install_id}),
        encoding="utf-8",
    )
    cfg = config_module.Config()
    assert cfg.get("install_id") == install_id


def test_install_id_invalid_value_is_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        json.dumps({"install_id": "not-an-id"}),
        encoding="utf-8",
    )
    cfg = config_module.Config()
    assert cfg.get("install_id") == ""


def test_pin_to_top_defaults_off(tmp_path, monkeypatch):
    """v2.11.2：日历窗口默认不再置顶，想要的用户手动打开。"""
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = config_module.Config()
    assert cfg.get("pin_to_top") is False
