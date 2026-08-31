"""OTA updater: check GitHub releases and apply in-place updates."""

import json
import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
from urllib.request import urlopen, Request
from urllib.error import HTTPError

from PySide6.QtCore import QThread, Signal

try:
    from __version__ import APP_VERSION
except Exception:  # pragma: no cover
    APP_VERSION = "0.0.0"

REPO = "swingmonkey/feishucalendarforfree"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
REPO_WEB = f"https://github.com/{REPO}"
_EXCLUDE = {"config.json", ".git", "__pycache__", ".workbuddy", ".idea", ".vscode"}


def parse_version(tag: str):
    tag = (tag or "").lstrip("vV").strip()
    parts = []
    for seg in tag.split("."):
        num = ""
        for ch in seg:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def is_newer(latest_tag: str, current: str = APP_VERSION) -> bool:
    try:
        return parse_version(latest_tag) > parse_version(current)
    except Exception:
        return False


def get_latest_release(timeout: int = 12):
    try:
        req = Request(API_LATEST, headers={"User-Agent": "feishucalendar-updater"})
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return None
        raise
    return {
        "tag": data.get("tag_name", ""),
        "name": data.get("name") or data.get("tag_name", ""),
        "html_url": data.get("html_url", ""),
        "body": data.get("body", ""),
        "zipball_url": data.get("zipball_url", ""),
        "published_at": data.get("published_at", ""),
        "assets": [
            {"name": a.get("name", ""), "browser_download_url": a.get("browser_download_url", ""), "size": a.get("size", 0)}
            for a in (data.get("assets") or [])
        ],
    }


def find_exe_asset(release):
    exes = [a for a in (release.get("assets") or []) if (a.get("name") or "").lower().endswith(".exe")]
    if not exes:
        return None
    for a in exes:
        if a.get("name", "").lower() == "飞书日程.exe":
            return a
    return exes[0]


def install_frozen_windows(exe_url: str, progress_cb=None):
    exe_path = os.path.abspath(sys.executable)
    downloading = exe_path + ".download"
    old = exe_path + ".old"
    download(exe_url, downloading, progress_cb=progress_cb)
    try:
        os.replace(exe_path, old)
        os.replace(downloading, exe_path)
    except OSError:
        if not os.path.exists(exe_path) and os.path.exists(old):
            try:
                os.replace(old, exe_path)
            except OSError:
                pass
        raise


def cleanup_old_executable():
    if not getattr(sys, "frozen", False):
        return
    old = os.path.abspath(sys.executable) + ".old"
    try:
        os.unlink(old)
    except OSError:
        pass


def download(url: str, dest: str, progress_cb=None, timeout: int = 60):
    req = Request(url, headers={"User-Agent": "feishucalendar-updater"})
    with urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        with open(dest, "wb") as f:
            while True:
                buf = resp.read(64 * 1024)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                if progress_cb:
                    progress_cb(downloaded, total)


def _safe_extract(zf: zipfile.ZipFile, destination: str):
    """Extract a ZIP only when every member stays below destination."""
    base = os.path.realpath(destination)
    for info in zf.infolist():
        name = info.filename.replace("\\", "/")
        if name.startswith("/") or any(part == ".." for part in name.split("/")):
            raise ValueError(f"unsafe archive path: {info.filename}")
        target = os.path.realpath(os.path.join(destination, name))
        if os.path.commonpath((base, target)) != base:
            raise ValueError(f"unsafe archive path: {info.filename}")
        # Reject symbolic-link members; the updater only needs regular files/dirs.
        mode = (info.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise ValueError(f"symlink is not allowed: {info.filename}")
    zf.extractall(destination)


def apply_update(zip_path: str, base_dir: str):
    tmp = tempfile.mkdtemp(prefix="fc_update_")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            _safe_extract(zf, tmp)
        entries = os.listdir(tmp)
        src_root = os.path.join(tmp, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])) else tmp
        for root, dirs, files in os.walk(src_root):
            dirs[:] = [d for d in dirs if d not in _EXCLUDE and not d.startswith(".")]
            for fn in files:
                if fn in _EXCLUDE:
                    continue
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, src_root)
                if rel.split(os.sep)[0] in _EXCLUDE:
                    continue
                target = os.path.join(base_dir, rel)
                os.makedirs(os.path.dirname(target), exist_ok=True)
                shutil.copy2(full, target)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def restart_application():
    args = [sys.executable] if getattr(sys, "frozen", False) else [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")]
    try:
        subprocess.Popen(args)
    except Exception:
        pass
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
    except Exception:
        app = None
    if app is not None:
        app.quit()
    try:
        sys.exit(0)
    except SystemExit:
        pass


class UpdateWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(bool, str)

    def __init__(self, zipball_url: str, base_dir: str, exe_url: str = None):
        super().__init__()
        self.zipball_url = zipball_url
        self.base_dir = base_dir
        self.exe_url = exe_url
        self._zip = tempfile.mktemp(suffix=".zip")

    def run(self):
        try:
            if self.exe_url:
                install_frozen_windows(self.exe_url, progress_cb=lambda d, t: self.progress.emit(d, t))
            else:
                download(self.zipball_url, self._zip, progress_cb=lambda d, t: self.progress.emit(d, t))
                apply_update(self._zip, self.base_dir)
            self.finished.emit(True, "更新已应用，即将重启")
        except Exception as e:
            self.finished.emit(False, f"更新失败：{e}")
        finally:
            try:
                os.unlink(self._zip)
            except OSError:
                pass


class CheckWorker(QThread):
    result = Signal(object)

    def run(self):
        try:
            self.result.emit(get_latest_release())
        except Exception:
            self.result.emit(None)
