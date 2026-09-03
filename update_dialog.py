"""Update confirmation + progress dialog (OTA)."""

import os
import sys

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices

import updater


class UpdateDialog(QDialog):
    """Shown when a newer version is available. Downloads and applies it."""

    def __init__(self, release, current_version, parent=None):
        super().__init__(parent)
        self.release = release
        self.current_version = current_version
        self.setWindowTitle("发现新版本")
        self.setMinimumWidth(460)
        self._worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        tag = (self.release.get("tag") or "").lstrip("v")
        info = QLabel(f"当前版本：v{self.current_version}\n最新版本：v{tag}")
        info.setObjectName("detailTitle")
        layout.addWidget(info)

        body = (self.release.get("body") or "").strip() or "（无更新说明）"
        if len(body) > 1200:
            body = body[:1200] + "\n…"
        note = QPlainTextEdit(body)
        note.setReadOnly(True)
        note.setMaximumHeight(160)
        note.setObjectName("detailLabel")
        layout.addWidget(note)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        self.status_label.setObjectName("detailLabel")
        layout.addWidget(self.status_label)

        row = QHBoxLayout()
        row.addStretch()
        self.later_btn = QPushButton("稍后")
        self.later_btn.setObjectName("secondaryBtn")
        self.later_btn.clicked.connect(self.reject)
        row.addWidget(self.later_btn)

        self.update_btn = QPushButton("立即更新")
        self.update_btn.setObjectName("primaryBtn")
        self.update_btn.clicked.connect(self._start_update)
        row.addWidget(self.update_btn)
        layout.addLayout(row)

    def _resolve_expected_hash(self, asset_name: str) -> str:
        """Download SHA256SUMS from the release and look up the expected hash
        for ``asset_name``.  Returns empty string when no checksums are
        published (older releases) or the file is not listed."""
        sums = updater.download_sha256_sums(self.release)
        if not sums:
            return ""
        # Exact match first
        if asset_name in sums:
            return sums[asset_name]
        # Case-insensitive / suffix match fallback
        lower = asset_name.lower()
        for fname, h in sums.items():
            if fname.lower() == lower or fname.lower().endswith(lower):
                return h
        return ""

    def _start_update(self):
        frozen = getattr(sys, "frozen", False)

        if frozen and sys.platform == "win32":
            # PyInstaller EXE：直接下载 Release 里的新 EXE 自替换
            asset = updater.find_exe_asset(self.release)
            if not asset:
                self.status_label.setText("最新版本暂未上传 EXE 安装包，已为你打开下载页面…")
                self._open_releases_page()
                return
            asset_name = asset.get("name", "")
            expected_hash = self._resolve_expected_hash(asset_name)
            self._begin(
                updater.UpdateWorker(
                    None, "",
                    exe_url=asset.get("browser_download_url"),
                    expected_hash=expected_hash,
                )
            )
            return

        if frozen:
            # macOS .app 暂不支持应用内自更新，引导到 Releases 页面
            self.update_btn.setEnabled(False)
            self.later_btn.setEnabled(False)
            self.status_label.setText("请到 Releases 页面下载最新 .app 替换，正在为你打开…")
            QTimer.singleShot(1200, self._open_releases_page)
            return

        zipball = self.release.get("zipball_url")
        if not zipball:
            self.status_label.setText("错误：未找到更新包下载地址")
            return
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Source-run zipball updates are not checksum-verified (the zipball
        # is generated on-the-fly by GitHub, not a named release asset).
        self._begin(updater.UpdateWorker(zipball, base_dir))

    def _begin(self, worker):
        self._worker = worker
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("正在下载更新…")
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _open_releases_page(self):
        QDesktopServices.openUrl(QUrl(updater.REPO_WEB + "/releases/latest"))

    def _on_progress(self, done, total):
        if total and total > 0:
            self.progress.setValue(int(done * 100 / total))

    def _on_finished(self, ok, msg):
        self.status_label.setText(msg)
        if ok:
            self.update_btn.setText("重启中…")
            # Let the label paint before we relaunch
            QTimer.singleShot(800, updater.restart_application)
        else:
            self.update_btn.setEnabled(True)
            self.later_btn.setEnabled(True)
            self.progress.setVisible(False)
