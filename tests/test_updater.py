"""OTA updater 离线回归测试（mock 网络，无需真实 GitHub）。"""
import os
import json
import zipfile
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
from unittest import mock

import updater


# ── 版本解析 ──
def test_parse_version():
    assert updater.parse_version("v2.0.0") == (2, 0, 0)
    assert updater.parse_version("2.1") == (2, 1, 0)
    assert updater.parse_version("v1.9.9") == (1, 9, 9)
    assert updater.parse_version("weird") == (0, 0, 0)


def test_is_newer():
    assert updater.is_newer("v2.0.1", "2.0.0") is True
    assert updater.is_newer("v2.0.0", "2.0.0") is False
    assert updater.is_newer("v1.9.9", "2.0.0") is False


# ── apply_update 覆盖 + 排除 ──
def _make_zip(path, tag="repo-2.0.1"):
    src = tempfile.mkdtemp()
    root = os.path.join(src, tag)
    os.makedirs(root)
    (Path(root) / "a.txt").write_text("NEW")
    (Path(root) / "config.json").write_text('{"hack": 1}')
    os.makedirs(Path(root) / ".git")
    (Path(root) / ".git" / "x").write_text("g")
    with zipfile.ZipFile(path, "w") as z:
        for dp, _, fns in os.walk(src):
            for fn in fns:
                fp = os.path.join(dp, fn)
                z.write(fp, os.path.relpath(fp, src))
    return src


def test_apply_update_excludes_config_and_git():
    zp = tempfile.mktemp(suffix=".zip")
    _make_zip(zp)
    base = tempfile.mkdtemp()
    (Path(base) / "config.json").write_text('{"keep": 1}')
    try:
        updater.apply_update(zp, base)
        # 普通文件被覆盖
        assert (Path(base) / "a.txt").read_text() == "NEW"
        # config.json 保留用户原值（未被 zip 内覆盖）
        assert json.loads((Path(base) / "config.json").read_text()) == {"keep": 1}
        # 排除目录不被写入
        assert not (Path(base) / ".git").exists()
    finally:
        os.unlink(zp)


# ── restart 启动新进程 ──
def test_restart_launches_new_process():
    with mock.patch.object(updater.subprocess, "Popen") as m_popen, \
            mock.patch.object(updater.sys, "exit", lambda *a: None):
        updater.restart_application()
        assert m_popen.called


# ── UI 构造不崩 ──
def test_update_dialog_construct():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from update_dialog import UpdateDialog

    release = {"tag": "v2.0.1", "body": "# 更新\n- 修复样式", "zipball_url": "http://x/z.zip"}
    dlg = UpdateDialog(release, "2.0.0")
    assert dlg.windowTitle() == "发现新版本"
    dlg.close()


def test_settings_check_update_opens_dialog():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from config import Config
    from settings_dialog import SettingsDialog

    release = {"tag": "v9.9.9", "body": "x", "zipball_url": "http://x/z.zip"}
    with mock.patch.object(updater, "get_latest_release", return_value=release), \
            mock.patch("update_dialog.UpdateDialog") as m_dlg:
        m_dlg.return_value.exec.return_value = None
        dlg = SettingsDialog(Config())
        dlg._on_check_update()
        assert m_dlg.called
        dlg.close()


def test_get_latest_release_returns_none_without_release():
    """仓库没有 release 时（HTTP 404）应返回 None，而非抛异常。"""
    import urllib.error

    class _Resp:
        code = 404

    with mock.patch.object(updater, "urlopen", side_effect=urllib.error.HTTPError(None, 404, "n/a", None, None)):
        assert updater.get_latest_release() is None


# ── 冻结(EXE)模式自更新 ──

def test_find_exe_asset_prefers_canonical_name():
    rel = {"assets": [
        {"name": "飞书日程.app.zip", "browser_download_url": "u-app", "size": 1},
        {"name": "FeishuCalendar.exe", "browser_download_url": "u-any", "size": 2},
        {"name": "飞书日程.exe", "browser_download_url": "u-exe", "size": 3},
    ]}
    assert updater.find_exe_asset(rel)["browser_download_url"] == "u-exe"


def test_find_exe_asset_fallback_and_missing():
    rel_any = {"assets": [{"name": "App.exe", "browser_download_url": "u"}]}
    assert updater.find_exe_asset(rel_any)["browser_download_url"] == "u"
    assert updater.find_exe_asset({}) is None
    assert updater.find_exe_asset({"assets": [{"name": "readme.txt"}]}) is None


def test_cleanup_old_executable_noop_in_source_mode(tmp=None):
    """源码运行时清理函数应为安全 no-op（不抛异常）。"""
    updater.cleanup_old_executable()


def test_update_worker_accepts_exe_url():
    """UpdateWorker 兼容旧签名，同时支持冻结模式 exe_url 参数。"""
    w = updater.UpdateWorker("http://x/zipball", "/tmp")
    assert w.exe_url is None
    w2 = updater.UpdateWorker(None, "", exe_url="http://x/app.exe")
    assert w2.exe_url == "http://x/app.exe"
