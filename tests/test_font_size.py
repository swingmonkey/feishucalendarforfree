"""Offline tests for the adjustable event font size (月视图 / 周·列表视图)."""

import config as config_module
import styles
from widgets import MAX_VISIBLE_EVENTS, visible_event_count


# ── Config: defaults & clamping ──

def test_font_size_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = config_module.Config()
    assert cfg.get("grid_font_size") == 10
    assert cfg.get("list_font_size") == 13


def test_font_size_out_of_range_is_clamped(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        '{"grid_font_size": 2, "list_font_size": 99}', encoding="utf-8"
    )
    cfg = config_module.Config()
    assert cfg.get("grid_font_size") == 9
    assert cfg.get("list_font_size") == 24


def test_font_size_invalid_type_falls_back(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    (tmp_path / "config.json").write_text(
        '{"grid_font_size": "big", "list_font_size": true}', encoding="utf-8"
    )
    cfg = config_module.Config()
    assert cfg.get("grid_font_size") == 10
    assert cfg.get("list_font_size") == 13


def test_font_size_persists(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    cfg = config_module.Config()
    cfg.set("grid_font_size", 16)
    cfg.set("list_font_size", 18)
    cfg.save()
    assert config_module.Config().get("grid_font_size") == 16
    assert config_module.Config().get("list_font_size") == 18


# ── Stylesheet injection ──

def _rule_for(qss: str, selector: str) -> str:
    """Return the last rule block for ``selector`` (later rules win)."""
    blocks = [b for b in qss.split("}") if selector in b]
    return blocks[-1] if blocks else ""


def test_default_theme_matches_legacy_sizes():
    qss = styles.get_theme("light")
    assert "font-size: 10px" in _rule_for(qss, "QLabel#gridEventTitle")
    assert "font-size: 9px" in _rule_for(qss, "QLabel#gridEventTime")
    assert "font-size: 13px" in _rule_for(qss, "QLabel#eventTitle")
    assert "font-size: 11px" in _rule_for(qss, "QLabel#eventTime")


def test_grid_font_size_is_injected():
    qss = styles.get_theme("light", grid_font=16, list_font=13)
    assert "font-size: 16px" in _rule_for(qss, "QLabel#gridEventTitle")
    assert "font-size: 15px" in _rule_for(qss, "QLabel#gridEventTime")
    # 行高必须随字号放开，否则大字号会被裁掉
    row = _rule_for(qss, "QFrame#gridEvent")
    assert "min-height: 22px" in row
    assert "max-height: 24px" in row


def test_list_font_size_is_injected():
    qss = styles.get_theme("dark", grid_font=10, list_font=20)
    assert "font-size: 20px" in _rule_for(qss, "QLabel#eventTitle")
    assert "font-size: 18px" in _rule_for(qss, "QLabel#eventMeta")
    # 月视图不受影响
    assert "font-size: 10px" in _rule_for(qss, "QLabel#gridEventTitle")


def test_both_themes_accept_font_sizes():
    for name in ("light", "dark"):
        qss = styles.get_theme(name, grid_font=12, list_font=15)
        assert "font-size: 12px" in _rule_for(qss, "QLabel#gridEventTitle")
        assert "font-size: 15px" in _rule_for(qss, "QLabel#eventTitle")


def test_font_rules_clamp_invalid_input():
    qss = styles.get_theme("light", grid_font="x", list_font=None)
    assert "font-size: 10px" in _rule_for(qss, "QLabel#gridEventTitle")
    assert "font-size: 13px" in _rule_for(qss, "QLabel#eventTitle")


def test_font_rules_keep_theme_colors():
    light = styles.get_theme("light", grid_font=14)
    dark = styles.get_theme("dark", grid_font=14)
    assert "#1F2329" in _rule_for(light, "QLabel#gridEventTitle")
    assert "#F0F1F2" in _rule_for(dark, "QLabel#gridEventTitle")


# ── Day cell capacity ──

def test_visible_event_count_shrinks_with_font_size():
    assert visible_event_count(10) == MAX_VISIBLE_EVENTS == 3
    assert visible_event_count(12) == 2
    assert visible_event_count(16) == 2
    assert visible_event_count(24) == 1


def test_visible_event_count_never_below_one():
    for size in range(9, 25):
        assert visible_event_count(size) >= 1
    # 非法输入回退到默认 10px（行高 18px）
    assert visible_event_count("bad") == visible_event_count(10)
