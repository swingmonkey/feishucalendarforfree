"""OTA updater: check GitHub releases and apply in-place updates.

Design notes
------------
* The app is normally run from source (`python main.py`), so the update
  strategy is: download the release source zipball, overlay its files on
  top of the current install directory, then relaunch.
* Only the Python standard library is used (urllib / zipfile) — no extra
  dependency.
* User data is preserved: `config.json`, `.git`, `__pycache__`, and
  `.workbuddy` are never overwritten.
* The actual UI (download progress, confirm dialog) lives in
  `update_dialog.py`; this module is the head-less core so it can be unit
  tested with a mocked network.
"""

import json
import os
import sys
import shutil
import zipfile
import tempfile
import subprocess
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

from PySide6.QtCore import QThread, Signal

try:
    from __version__ import APP_VERSION
except Exception:  # pragma: no cover - import safety net
    APP_VERSION = "0.0.0"

REPO = "swingmonkey/feishucalendarforfree"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
REPO_WEB = f"https://github.com/{REPO}"

# Files / directories that must never be overwritten by an update.
_EXCLUDE = {"config.json", ".git", "__pycache__", ".workbuddy", ".idea", ".vscode"}


def parse_version(tag: str):
    """'v2.0.1' -> (2, 0, 1). Non-numeric segments count as 0."""
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
    """True if `latest_tag` is strictly newer than `current`."""
    try:
        return parse_version(latest_tag) > parse_version(current)
    except Exception:
        return False


def get_latest_release(timeout: int = 12):
    """Fetch latest release metadata.

    Returns a dict, or None when the repo has no releases yet (HTTP 404).
    """
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
            {
                "name": a.get("name", ""),
                "browser_download_url": a.get("browser_download_url", ""),
                "size": a.get("size", 0),
            }
            for a in (data.get("assets") or [])
        ],
    }


def find_exe_asset(release):
    """Return the Windows EXE asset of a release ({name, browser_download_url}).

    Prefers the canonical ``飞书日程.exe`` name, falls back to any ``*.exe``.
    Returns None when the release has no Windows artifact yet.
    """
    exes = [
        a for a in (release.get("assets") or [])
        if (a.get("name") or "").lower().endswith(".exe")
    ]
    if not exes:
        return None
    for a in exes:
        if a["name"].lower() == "飞书日程.exe":
            return a
    return exes[0]


def install_frozen_windows(exe_url: str, progress_cb=None):
    """Self-replace a PyInstaller onefile EXE with a freshly downloaded one.

    Windows locks the image file of a running process against deletion and
    writing, but renaming it is allowed — so: download alongside as
    ``.download``, rename the running file to ``.old``, move the new file
    into place.  ``restart_application()`` then launches the new binary,
    and ``cleanup_old_executable()`` removes the stale ``.old`` next start.
    """
    exe_path = os.path.abspath(sys.executable)
    downloading = exe_path + ".download"
    old = exe_path + ".old"
    download(exe_url, downloading, progress_cb=progress_cb)
    try:
        os.rename(exe_path, old)
        os.rename(downloading, exe_path)
    except OSError:
        # Roll back so the app stays runnable at the original path.
        if not os.path.exists(exe_path) and os.path.exists(old):
            try:
                os.rename(old, exe_path)
            except OSError:
                pass
        raise


def cleanup_old_executable():
    """Best-effort delete the '.old' EXE left by a previous self-update.

    Called early in the NEW process: by then the old process has exited,
    so its renamed image file is finally unlocked and removable.
    """
    if not getattr(sys, "frozen", False):
        return
    old = os.path.abspath(sys.executable) + ".old"
    if os.path.exists(old):
        try:
            os.unlink(old)
        except OSError:
            pass


def download(url: str, dest: str, progress_cb=None, timeout: int = 60):
    """Download `url` to `dest`, reporting (downloaded, total) via progress_cb."""
    req = Request(url, headers={"User-Agent": "feishucalendar-updater"})
    with urlopen(req, timeout=timeout) as resp:
        total = int(resp.headers.get("Content-Length", 0) or 0)
        downloaded = 0
        chunk = 64 * 1024
        with open(dest, "wb") as f:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                f.write(buf)
                downloaded += len(buf)
                if progress_cb:
                    progress_cb(downloaded, total)


def apply_update(zip_path: str, base_dir: str):
    """Extract `zip_path` and overlay its files into `base_dir`.

    The GitHub zipball nests everything under a single `repo-tag/` folder,
    which is stripped. Excluded paths (config.json, .git, ...) are skipped.
    """
    tmp = tempfile.mkdtemp(prefix="fc_update_")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp)
        entries = os.listdir(tmp)
        if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
            src_root = os.path.join(tmp, entries[0])
        else:
            src_root = tmp
        for root, dirs, files in os.walk(src_root):
            # prune excluded directories in place
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
    """Launch a fresh instance of the app, then quit the current one."""
    if getattr(sys, "frozen", False):
        args = [sys.executable]
    else:
        here = os.path.dirname(os.path.abspath(__file__))
        main_py = os.path.join(here, "main.py")
        args = [sys.executable, main_py]
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
    # Fallback so the old process never lingers
    try:
        sys.exit(0)
    except SystemExit:
        pass


class UpdateWorker(QThread):
    """Background downloader that drives the UpdateDialog progress bar."""

    progress = Signal(int, int)          # downloaded, total
    finished = Signal(bool, str)         # success, message

    def __init__(self, zipball_url: str, base_dir: str, exe_url: str = None):
        super().__init__()
        self.zipball_url = zipball_url
        self.base_dir = base_dir
        self.exe_url = exe_url          # frozen Windows self-update asset URL
        self._zip = tempfile.mktemp(suffix=".zip")

    def run(self):
        try:
            if self.exe_url:
                install_frozen_windows(
                    self.exe_url,
                    progress_cb=lambda d, t: self.progress.emit(d, t),
                )
            else:
                download(
                    self.zipball_url,
                    self._zip,
                    progress_cb=lambda d, t: self.progress.emit(d, t),
                )
                apply_update(self._zip, self.base_dir)
            self.finished.emit(True, "更新已应用，即将重启")
        except Exception as e:  # noqa: BLE001 - surface any failure to UI
            self.finished.emit(False, f"更新失败：{e}")
        finally:
            try:
                os.unlink(self._zip)
            except OSError:
                pass


class CheckWorker(QThread):
    """Background release check; emits the release dict (or None) on finish."""

    result = Signal(object)

    def run(self):
        try:
            self.result.emit(get_latest_release())
        except Exception:  # noqa: BLE001 - network errors just mean "no update"
            self.result.emit(None)
