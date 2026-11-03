"""前置依赖（lark-cli）自动安装。

应用的整条数据通路都挂在飞书官方 ``lark-cli`` 上。它没装时以前只摆一行
命令让人自己复制，现在这里是「装得上」的那一半：探测 node/npm、执行全局
安装、把新出现的 bin 目录塞回 PATH，并在失败时把 npm 的报错翻成人话。

两个刻意的取舍：

- **不自动 sudo。** 全局目录不可写时给建议，不替用户提权。能在用户机器上
  装东西已经是边界，跨过提权那道线必须由人自己决定。
- **装完立刻 refresh_path。** npm 的全局 bin 通常不在 .app 从 Finder 继承到
  的 PATH 里，少了这一步就会得到「安装成功但应用仍然说找不到」。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

NPM_PACKAGE = "@larksuite/cli"
BIN_NAME = "lark-cli"

# npm 在慢网络下可以磨很久；超过这个时间就当失败，别让面板一直转。
INSTALL_TIMEOUT_S = 300

# .app 从 Finder 启动时只继承最小 PATH。这些是 npm / volta / fnm / brew
# 常见的全局 bin 位置，装完的新文件最可能落在这里。
_FALLBACK_BIN_DIRS = (
    "~/.npm-global/bin",
    "~/.local/bin",
    "~/.volta/bin",
    "~/.bun/bin",
    "/usr/local/bin",
    "/opt/homebrew/bin",
)


# ── 命令构造 ─────────────────────────────────────────────────────────────────


def install_argv(npm: str) -> list[str]:
    """Build the global-install command for this platform.

    Windows 上 npm 是 ``.cmd`` 包装脚本，QProcess 直接 CreateProcess 它会失败，
    必须经 cmd.exe 转一手。
    """
    if sys.platform == "win32":
        return ["cmd", "/c", npm, "install", "-g", NPM_PACKAGE]
    return [npm, "install", "-g", NPM_PACKAGE]


def npm_bin_dir(npm: str, runner=subprocess.run) -> Path | None:
    """Where npm puts global executables.

    POSIX 是 ``<prefix>/bin``，Windows 直接在 ``<prefix>`` 下。问 npm 本身
    比猜路径可靠——nvm、volta、自定义 prefix 都不会猜错。
    """
    try:
        proc = runner(
            [npm, "prefix", "-g"], capture_output=True, text=True, timeout=15
        )
    except (OSError, subprocess.SubprocessError):
        return None
    lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    if not lines:
        return None
    base = Path(lines[-1])
    return base if sys.platform == "win32" else base / "bin"


# ── PATH ─────────────────────────────────────────────────────────────────────


def refresh_path(*dirs: str | Path | None) -> list[str]:
    """Prepend the given dirs to ``PATH`` (dedup, existing only).

    Returns the dirs actually added, so callers can report what changed.
    Always stores absolute paths: ``PATH`` is inherited by subprocesses with
    their own working directory, and a relative entry silently stops working
    the moment the cwd changes.
    """
    parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
    added: list[str] = []
    for d in dirs:
        if not d:
            continue
        try:
            resolved = str(Path(d).expanduser().resolve())
        except OSError:
            continue
        if not Path(resolved).is_dir() or resolved in parts:
            continue
        parts.insert(0, resolved)
        added.append(resolved)
    if added:
        os.environ["PATH"] = os.pathsep.join(parts)
    return added


def candidate_bin_dirs() -> list[Path]:
    """Common places a CLI might live, newest-tool-first."""
    home = Path.home()
    dirs = [Path(p).expanduser() for p in _FALLBACK_BIN_DIRS]
    nvm_root = home / ".nvm" / "versions" / "node"
    if nvm_root.is_dir():
        # 版本目录名带排序前缀，倒序取最新的几个
        for version_dir in sorted(nvm_root.iterdir(), reverse=True)[:3]:
            if version_dir.is_dir():
                dirs.insert(0, version_dir / "bin")
    return dirs


def find_npm() -> str | None:
    """Locate npm even when the launcher's PATH is minimal."""
    found = shutil.which("npm") or shutil.which("npm.cmd")
    if found:
        return found
    for directory in candidate_bin_dirs():
        for name in ("npm", "npm.cmd"):
            probe = directory / name
            if probe.exists():
                return str(probe)
    return None


def bootstrap_path() -> list[str]:
    """Make npm's global bin reachable, so a *previous* install is found too.

    Called at startup: users who installed lark-cli from a terminal still get
    "not found" inside a Finder-launched .app, because the bundle never saw
    their shell's PATH.
    """
    npm = find_npm()
    extra = [npm_bin_dir(npm)] if npm else []
    return refresh_path(*extra, *candidate_bin_dirs())


# ── 环境探测 ─────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Environment:
    """What the app can see right now, and why auto-install may be blocked."""

    cli: str | None
    npm: str | None
    node: str | None
    blocker: str | None

    @property
    def installed(self) -> bool:
        return self.cli is not None

    @property
    def can_install(self) -> bool:
        return self.blocker is None and self.npm is not None


def detect(npm: str | None = None) -> Environment:
    """Cheap probe: no subprocess, so the panel can call it freely.

    全局 bin 目录不在这里算——那需要跑一次 ``npm prefix``，装完由 worker
    现算即可。
    """
    cli = shutil.which(BIN_NAME)
    npm = npm or find_npm()
    node = shutil.which("node")

    blocker = None
    if cli is None:
        if npm is None:
            blocker = (
                "没找到 npm。自动安装需要 Node.js（自带 npm），"
                "请先安装 Node.js 再回来重试。"
            )
        elif node is None:
            blocker = "找到了 npm 却没有 node，Node.js 的安装可能不完整，建议重装。"
    return Environment(cli=cli, npm=npm, node=node, blocker=blocker)


# ── 失败翻译 ─────────────────────────────────────────────────────────────────


def explain_failure(output: str) -> str:
    """Turn npm's error codes into something a non-terminal user can act on."""
    text = (output or "").strip()
    if not text:
        return "安装失败，未拿到任何输出。"
    low = text.lower()
    if "eacces" in low or "permission denied" in low:
        return (
            "没有写入权限：npm 的全局目录不允许当前用户写入。\n"
            "两个选项——\n"
            "1) 改用用户级目录：npm config set prefix ~/.npm-global，"
            "再把 ~/.npm-global/bin 加进 PATH；\n"
            "2) 在终端里用 sudo 手动执行安装命令。"
        )
    if any(
        key in low
        for key in ("etimedout", "econnreset", "econnrefused", "enotfound", "network")
    ):
        return (
            "网络没能连上 npm 源。\n"
            "可以先换镜像再重试：npm config set registry https://registry.npmmirror.com"
        )
    if "e404" in low or "404 not found" in low:
        return "npm 源上找不到 @larksuite/cli，请确认 npm 源地址没有被改成镜像不完整的源。"
    tail = "\n".join(text.splitlines()[-6:])
    return f"安装失败，npm 最后几行输出：\n{tail}"


def is_usable(code: int) -> bool:
    """Success means both "npm exited 0" *and* "we can now see the binary"."""
    return code == 0 and shutil.which(BIN_NAME) is not None
