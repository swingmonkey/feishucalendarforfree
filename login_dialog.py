# -*- coding: utf-8 -*-
"""应用内飞书登录对话框。

通过 lark-cli 的 Device Flow 完成授权：
1. 发起 no-wait 登录拿到 verification_url + device_code
2. 在对话框内显示二维码（lark-cli 生成 PNG）与授权链接
3. 用户扫码/打开网页授权后，点「我已授权」由后台线程收尾（--device-code）
"""

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QFrame,
)

LOGIN_SCOPES = ["calendar:calendar.event:read", "calendar:calendar:read"]


_LARK_RUN_JS = None


def _resolve_lark_cmd():
    """返回可直接交给 subprocess 的 lark-cli 命令前缀。

    Windows 上 lark-cli 是 npm 的 .CMD 包装（cmd 会拆解 URL 里的 & 等字符），
    因此优先定位其真实 node 入口 scripts/run.js 直接调用，绕开 cmd 解析；
    找不到时回退 cmd /c 方式。输出均为 UTF-8，必须显式指定 encoding。
    """
    global _LARK_RUN_JS
    if _LARK_RUN_JS:
        return ["node", _LARK_RUN_JS]
    exe = shutil.which("lark-cli")
    if exe:
        run_js = Path(exe).resolve().parent / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
        if run_js.is_file():
            _LARK_RUN_JS = str(run_js)
            return ["node", _LARK_RUN_JS]
    if exe:
        if exe.lower().endswith((".cmd", ".bat")):
            return ["cmd", "/c", exe]
        return [exe]
    return None


def _lark_cli(args, timeout=60):
    """运行 lark-cli，返回 (exit_code, stdout, stderr)。"""
    prefix = _resolve_lark_cmd()
    if not prefix:
        return -1, "", "未找到 lark-cli，请先执行 npm install -g @larksuite/cli"
    try:
        proc = subprocess.run(
            prefix + list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "lark-cli 执行超时"
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


class _DeviceCodeWorker(QThread):
    """后台执行 device-code 收尾授权（用户授权后应立即返回）。"""

    finished_ok = Signal()
    finished_err = Signal(str)

    def __init__(self, device_code: str, parent=None):
        super().__init__(parent)
        self._device_code = device_code

    def run(self):
        rc, out, err = _lark_cli(
            ["auth", "login", "--device-code", self._device_code], timeout=180
        )
        if rc == 0:
            self.finished_ok.emit()
        else:
            self.finished_err.emit((err or out or f"退出码 {rc}").strip())


class LoginDialog(QDialog):
    """飞书登录对话框：二维码 + 授权链接 + 完成按钮。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录飞书")
        self.setFixedSize(440, 560)
        self._device_code = None
        self._verification_url = None
        self._worker = None
        self._setup_ui()
        self._start_login()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        title = QLabel("登录飞书账号")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        self.qr_label = QLabel("正在生成二维码...")
        self.qr_label.setObjectName("detailLabel")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setFixedHeight(280)
        layout.addWidget(self.qr_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("detailLabel")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        url_box = QFrame()
        url_layout = QVBoxLayout(url_box)
        url_layout.setContentsMargins(0, 0, 0, 0)
        url_lbl = QLabel("或复制下面的链接到浏览器打开：")
        url_lbl.setObjectName("detailLabel")
        url_layout.addWidget(url_lbl)
        self.url_edit = QTextEdit()
        self.url_edit.setReadOnly(True)
        self.url_edit.setFixedHeight(56)
        self.url_edit.setObjectName("detailLabel")
        url_layout.addWidget(self.url_edit)
        layout.addWidget(url_box)

        # 按钮行
        btn_row = QHBoxLayout()
        self.open_btn = QPushButton("打开授权页面")
        self.open_btn.setObjectName("primaryBtn")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self._on_open_url)
        btn_row.addWidget(self.open_btn)

        self.done_btn = QPushButton("我已授权，完成登录")
        self.done_btn.setObjectName("secondaryBtn")
        self.done_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.done_btn.setEnabled(False)
        self.done_btn.clicked.connect(self._on_user_done)
        btn_row.addWidget(self.done_btn)
        layout.addLayout(btn_row)

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, 0, Qt.AlignmentFlag.AlignRight)

    # --------------------------------------------------------------- login
    def _start_login(self):
        self.status_label.setText("正在发起登录...")
        args = ["auth", "login", "--no-wait", "--json"]
        for scope in LOGIN_SCOPES:
            args += ["--scope", scope]
        rc, out, err = _lark_cli(args, timeout=30)
        if rc != 0:
            self.status_label.setText(f"❌ 发起登录失败：{err or out}")
            return
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            self.status_label.setText(f"❌ lark-cli 返回异常：{out[:200]}")
            return

        self._device_code = data.get("device_code")
        self._verification_url = data.get("verification_url")
        self.url_edit.setPlainText(self._verification_url or "")
        self._generate_qrcode(self._verification_url or "")

        self.status_label.setText(
            "请使用飞书 App 扫描二维码，或点击下方按钮在浏览器中完成授权，\n"
            "授权后点击「我已授权，完成登录」。链接 10 分钟内有效。"
        )
        self.done_btn.setEnabled(True)

    def _generate_qrcode(self, url: str):
        try:
            tmp_dir = Path(tempfile.gettempdir())
            out_name = "feishu-login-qr.png"
            rc, _, err = _lark_cli(
                ["auth", "qrcode", url, "--output", out_name, "--size", "256"],
                timeout=30,
            )
            if rc == 0:
                img_path = tmp_dir / out_name
                if img_path.exists():
                    pixmap = QPixmap(str(img_path))
                    if not pixmap.isNull():
                        self.qr_label.setPixmap(
                            pixmap.scaled(
                                260,
                                260,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                        return
            self.qr_label.setText("二维码生成失败，请使用下方链接授权")
        except Exception as e:  # noqa: BLE001
            self.qr_label.setText(f"二维码生成失败：{e}")

    # ------------------------------------------------------------- actions
    def _on_open_url(self):
        if self._verification_url:
            QDesktopServices.openUrl(QUrl(self._verification_url))

    def _on_user_done(self):
        if not self._device_code:
            return
        self.done_btn.setEnabled(False)
        self.status_label.setText("正在完成登录...")
        self._worker = _DeviceCodeWorker(self._device_code, self)
        self._worker.finished_ok.connect(self._on_success)
        self._worker.finished_err.connect(self._on_fail)
        self._worker.start()

    def _on_success(self):
        self.status_label.setText("✅ 登录成功！")
        QMessageBox.information(self, "登录成功", "已授权飞书日历读写权限。")
        self.accept()

    def _on_fail(self, msg: str):
        self.done_btn.setEnabled(True)
        self.status_label.setText(f"❌ 登录未完成：{msg}\n如已授权仍失败，可重新打开本窗口再试。")
