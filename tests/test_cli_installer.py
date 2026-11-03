"""lark-cli 自动安装：环境探测、命令构造、路径刷新、失败翻译。

这些是安装链路里最容易「看起来对、实际不做」的部分——比如装完了却
``shutil.which`` 还是找不到，因为 npm 的全局 bin 不在 .app 继承到的 PATH 里。
所以纯逻辑都单独测，QProcess 那层只留薄薄一层壳。
"""

import os
import shutil
import sys
from pathlib import Path

import cli_installer as ci

# ── 命令构造 ─────────────────────────────────────────────────────────────────


def test_install_argv_posix(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert ci.install_argv("/usr/local/bin/npm") == [
        "/usr/local/bin/npm", "install", "-g", ci.NPM_PACKAGE,
    ]


def test_install_argv_windows_goes_through_cmd(monkeypatch):
    """Windows 上 npm 是 .cmd 包装，QProcess 不能直接 CreateProcess 它。"""
    monkeypatch.setattr(sys, "platform", "win32")
    argv = ci.install_argv(r"C:\Program Files\nodejs\npm.cmd")
    assert argv[:2] == ["cmd", "/c"]
    assert argv[-3:] == ["install", "-g", ci.NPM_PACKAGE]


# ── npm 全局 bin 目录 ────────────────────────────────────────────────────────


def test_bin_dir_posix_appends_bin(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    fake = lambda argv, **kw: type("R", (), {"stdout": "/opt/node\n", "returncode": 0})()
    assert ci.npm_bin_dir("/opt/node/bin/npm", runner=fake) == Path("/opt/node/bin")


def test_bin_dir_windows_is_prefix_itself(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    fake = lambda argv, **kw: type("R", (), {"stdout": r"C:\Users\me\AppData\Roaming\npm" + "\n", "returncode": 0})()
    assert ci.npm_bin_dir("npm.cmd", runner=fake) == Path(r"C:\Users\me\AppData\Roaming\npm")


def test_bin_dir_returns_none_when_npm_says_nothing(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    fake = lambda argv, **kw: type("R", (), {"stdout": "", "returncode": 1})()
    assert ci.npm_bin_dir("/x/npm", runner=fake) is None


# ── 环境探测 ─────────────────────────────────────────────────────────────────


def test_detect_reports_missing_npm(monkeypatch):
    monkeypatch.setattr(ci, "find_npm", lambda: None)
    monkeypatch.setattr(ci.shutil, "which", lambda name: None)
    env = ci.detect()
    assert env.npm is None
    assert env.can_install is False
    assert "npm" in env.blocker or "Node" in env.blocker


def test_detect_finds_cli_after_path_refresh(tmp_path, monkeypatch):
    """装完之后必须能立刻被 which 找到，否则「安装成功但不可用」。"""
    bin_dir = tmp_path / "npm-bin"
    bin_dir.mkdir()
    exe = bin_dir / "lark-cli"
    exe.write_text("#!/bin/sh\necho 1.0.0\n")
    exe.chmod(0o755)

    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    assert shutil.which("lark-cli") is None

    ci.refresh_path(str(bin_dir))

    assert str(bin_dir) in os.environ["PATH"].split(os.pathsep)
    assert shutil.which("lark-cli") == str(exe)


def test_refresh_path_is_idempotent(tmp_path, monkeypatch):
    d = tmp_path / "bin"
    d.mkdir()
    monkeypatch.setenv("PATH", f"/usr/bin{os.pathsep}{d}")
    ci.refresh_path(str(d))
    assert os.environ["PATH"].split(os.pathsep).count(str(d)) == 1


def test_refresh_path_stores_absolute_dir(tmp_path, monkeypatch):
    """PATH 会被子进程继承，相对路径换个 cwd 就失效了。"""
    d = tmp_path / "bin"
    d.mkdir()
    monkeypatch.setenv("PATH", "/usr/bin")
    monkeypatch.chdir(tmp_path)

    added = ci.refresh_path("bin")

    assert added == [str(d.resolve())]
    assert str(d.resolve()) in os.environ["PATH"].split(os.pathsep)


def test_refresh_path_skips_missing_dirs(tmp_path, monkeypatch):
    monkeypatch.setenv("PATH", "/usr/bin")
    ci.refresh_path(str(tmp_path / "nope"))
    assert str(tmp_path / "nope") not in os.environ["PATH"]


# ── 失败翻译 ─────────────────────────────────────────────────────────────────


def test_explain_permission_error():
    text = ci.explain_failure("npm ERR! code EACCES\nnpm ERR! permission denied")
    assert "权限" in text


def test_explain_network_error():
    text = ci.explain_failure("npm ERR! code ETIMEDOUT")
    assert "网络" in text or "镜像" in text


def test_explain_unknown_keeps_tail():
    text = ci.explain_failure("line1\nline2\nweird thing happened")
    assert "weird thing happened" in text


def test_explain_empty_output():
    assert ci.explain_failure("") == "安装失败，未拿到任何输出。"
