"""node 解析与 PATH 扩展：Finder 启动的 .app 找不到 node 的根因修复。

背景（2026-11-04 v2.10.0 真机踩坑）：用户机器上 node 只存在于
``~/.workbuddy/binaries/node/versions/*/bin``，lark-cli shim 第一行是
``#!/usr/bin/env node``。从 Finder 启动时 PATH 只有 /usr/bin:/bin:...，
登录框直接报 ``env: node: No such file or directory``。
"""

import os
from pathlib import Path

import cli_installer as ci
import login_dialog


def _make_home(tmp_path, layout: dict[str, bool]) -> None:
    """在假 home 下造目录；True = 里面放一个可执行的 node。"""
    for rel, with_node in layout.items():
        p = tmp_path / rel
        p.mkdir(parents=True, exist_ok=True)
        if with_node:
            node = p / "node"
            node.write_text("#!/bin/sh\n", encoding="utf-8")
            node.chmod(0o755)


# ── candidate_bin_dirs：版本管理器目录 ──────────────────────────────────────


def test_candidate_dirs_cover_workbuddy_node(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _make_home(
        tmp_path,
        {".workbuddy/binaries/node/versions/22.22.2-6/bin": "x"},
    )
    dirs = ci.candidate_bin_dirs()
    assert tmp_path / ".workbuddy/binaries/node/versions/22.22.2-6/bin" in dirs


def test_candidate_dirs_cover_fnm_node(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _make_home(
        tmp_path,
        {".local/share/fnm/node-versions/v22.11.0/installation/bin": "x"},
    )
    dirs = ci.candidate_bin_dirs()
    assert (
        tmp_path / ".local/share/fnm/node-versions/v22.11.0/installation/bin" in dirs
    )


def test_candidate_dirs_still_cover_nvm(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _make_home(tmp_path, {".nvm/versions/node/v20.18.0/bin": "x"})
    dirs = ci.candidate_bin_dirs()
    assert tmp_path / ".nvm/versions/node/v20.18.0/bin" in dirs


# ── login_dialog._find_node ─────────────────────────────────────────────────


def test_find_node_uses_which_first(monkeypatch):
    monkeypatch.setattr(login_dialog.shutil, "which", lambda n: "/usr/bin/node" if n == "node" else None)
    assert login_dialog._find_node() == "/usr/bin/node"


def test_find_node_scans_version_dirs_when_path_is_bare(monkeypatch, tmp_path):
    """Finder 启动的真实场景：which 全空，node 藏在版本管理器目录里。"""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(login_dialog.shutil, "which", lambda n: None)
    _make_home(
        tmp_path,
        {".workbuddy/binaries/node/versions/22.22.2-6/bin": "x"},
    )
    found = login_dialog._find_node()
    assert found == str(tmp_path / ".workbuddy/binaries/node/versions/22.22.2-6/bin/node")
    assert os.access(found, os.X_OK)


def test_find_node_returns_none_when_nowhere(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(login_dialog.shutil, "which", lambda n: None)
    # CI runner 真装着 node（/usr/local/bin），不隔离候选目录就会扫到真的
    monkeypatch.setattr("cli_installer.candidate_bin_dirs", lambda: [])
    assert login_dialog._find_node() is None


# ── _resolve_lark_cmd：node 必须是绝对路径 ──────────────────────────────────


def test_resolve_lark_cmd_prefers_run_js_with_absolute_node(monkeypatch, tmp_path):
    """裸 'node' 依赖运行时 PATH——Finder 启动时必炸，必须换绝对路径。"""
    monkeypatch.setattr(login_dialog, "_LARK_RUN_JS", None)
    npm_bin = tmp_path / ".npm-global" / "bin"
    run_js = npm_bin / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
    run_js.parent.mkdir(parents=True)
    run_js.write_text("// run.js\n", encoding="utf-8")
    fake_cli = npm_bin / "lark-cli"
    fake_cli.write_text("#!/usr/bin/env node\n", encoding="utf-8")

    def fake_which(name):
        if name == "lark-cli":
            return str(fake_cli)
        return None  # node 在 PATH 里找不到——正是线上炸掉的场景

    monkeypatch.setattr(login_dialog.shutil, "which", fake_which)
    monkeypatch.setattr(
        login_dialog, "_find_node", lambda: "/wb/node/bin/node"
    )
    argv = login_dialog._resolve_lark_cmd()
    assert argv == ["/wb/node/bin/node", str(run_js)]


def test_resolve_lark_cmd_finds_run_js_in_lib_node_modules(monkeypatch, tmp_path):
    """POSIX 的 npm 全局包在 prefix/lib/node_modules，bin/ 里只有 shim。"""
    monkeypatch.setattr(login_dialog, "_LARK_RUN_JS", None)
    prefix = tmp_path / ".npm-global"
    shim = prefix / "bin" / "lark-cli"
    shim.parent.mkdir(parents=True)
    shim.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    run_js = prefix / "lib" / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
    run_js.parent.mkdir(parents=True)
    run_js.write_text("// run.js\n", encoding="utf-8")

    def fake_which(name):
        return str(shim) if name == "lark-cli" else None

    monkeypatch.setattr(login_dialog.shutil, "which", fake_which)
    monkeypatch.setattr(login_dialog, "_find_node", lambda: str(tmp_path / "n"))
    argv = login_dialog._resolve_lark_cmd()
    assert argv[0] == str(tmp_path / "n")
    assert argv[1] == str(run_js)


def test_resolve_lark_cmd_follows_symlink_to_run_js(monkeypatch, tmp_path):
    """真机布局：bin/lark-cli 本身就是指向 run.js 的 symlink。"""
    monkeypatch.setattr(login_dialog, "_LARK_RUN_JS", None)
    prefix = tmp_path / ".npm-global"
    run_js = prefix / "lib" / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
    run_js.parent.mkdir(parents=True)
    run_js.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    shim = prefix / "bin" / "lark-cli"
    shim.parent.mkdir(parents=True)
    shim.symlink_to(run_js)

    def fake_which(name):
        return str(shim) if name == "lark-cli" else None

    monkeypatch.setattr(login_dialog.shutil, "which", fake_which)
    monkeypatch.setattr(login_dialog, "_find_node", lambda: str(tmp_path / "n"))
    argv = login_dialog._resolve_lark_cmd()
    assert argv == [str(tmp_path / "n"), str(run_js)]


def test_resolve_lark_cmd_caches_run_js_but_refinds_node(monkeypatch):
    """缓存命中 run.js 时 node 路径仍要现查——两次调用间 node 可能装好。"""
    calls = []

    def fake_find():
        calls.append(1)
        return "/n/node"

    monkeypatch.setattr(login_dialog, "_LARK_RUN_JS", "/cached/run.js")
    monkeypatch.setattr(login_dialog, "_find_node", fake_find)
    argv = login_dialog._resolve_lark_cmd()
    assert argv == ["/n/node", "/cached/run.js"]
    assert calls  # _find_node 真的被调了


# ── main.py PATH 扩展 ───────────────────────────────────────────────────────


def test_extend_path_covers_version_manager_dirs(monkeypatch, tmp_path):
    import main as main_mod

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    _make_home(
        tmp_path,
        {".workbuddy/binaries/node/versions/22.22.2-6/bin": "x"},
    )
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    main_mod._extend_path_for_app_bundle()
    parts = os.environ["PATH"].split(os.pathsep)
    assert str(tmp_path / ".workbuddy/binaries/node/versions/22.22.2-6/bin") in parts
    # fallback 常量（~/.npm-global 等）在 import 时已按真实 home 展开，
    # 这里只验证「动态扫描的版本目录」进入 PATH；fallback 顺序无断言价值。
    assert parts[:2] == ["/usr/bin", "/bin"]  # 原 PATH 没被破坏
