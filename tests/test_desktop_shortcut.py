"""桌面快捷方式：冻结包要能链到自己，失败不能假装成功。

起因是一次真机部署：从 Release 装好 FeishuCalendar.app 后首次启动，
config.json 里 ``desktop_shortcut_created`` 是 true，桌面上却什么都没有。
原因在 ``_create_macos_shortcut``——它只认源码目录下的 ``dist/飞书日程.app``，
而冻结包里那个路径不存在，函数静默跑完，调用方照样把标记写死，
于是「下次重试」永远等不到。
"""

import sys
from pathlib import Path

import pytest

import main as main_module
from config import Config


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    return Config()


def _fake_bundle(tmp_path: Path) -> tuple[Path, Path]:
    """造一个冻结包的骨架：X.app/Contents/MacOS/X。"""
    bundle = tmp_path / "FeishuCalendar.app"
    binary = bundle / "Contents" / "MacOS" / "FeishuCalendar"
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b"")
    return bundle, binary


def test_frozen_macos_links_its_own_bundle(tmp_path, monkeypatch):
    bundle, binary = _fake_bundle(tmp_path)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(binary), raising=False)

    assert main_module._create_macos_shortcut(desktop) is True

    link = desktop / "FeishuCalendar.app"
    assert link.is_symlink(), "冻结版应该把当前 bundle 软链到桌面"
    assert link.resolve() == bundle.resolve()


def test_source_run_still_links_dist_bundle(tmp_path, monkeypatch):
    """源码运行时行为不变：仍然优先链 dist/ 里的构建产物。"""
    dist_bundle = tmp_path / "dist" / "飞书日程.app"
    dist_bundle.mkdir(parents=True)
    desktop = tmp_path / "Desktop"
    desktop.mkdir()

    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(main_module, "__file__", str(tmp_path / "main.py"))

    assert main_module._create_macos_shortcut(desktop) is True
    assert (desktop / "飞书日程.app").is_symlink()


def test_failure_does_not_mark_done(tmp_path, monkeypatch):
    """找不到可链的目标时，不能写「已完成」，否则再也不会重试。"""
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(main_module, "__file__", str(tmp_path / "main.py"))

    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    config = Config()
    assert config.get("desktop_shortcut_created") is False

    main_module._ensure_desktop_shortcut(config, desktop=desktop)

    assert config.get("desktop_shortcut_created") is False, (
        "什么都没链上却写了已完成，下次启动就不会再试"
    )
