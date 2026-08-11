"""Update confirmation + progress dialog (OTA)."""

import os

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
)
from PySide6.QtCore import Qt, QTimer

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

    def _start_update(self):
        zipball = self.release.get("zipball_url")
        if not zipball:
            self.status_label.setText("错误：未找到更新包下载地址")
            return
        self.update_btn.setEnabled(False)
        self.later_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("正在下载更新…")
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._worker = updater.UpdateWorker(zipball, base_dir)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

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
