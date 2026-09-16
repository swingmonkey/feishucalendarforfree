"""应用内飞书登录对话框。

通过 lark-cli 的 Device Flow 完成授权（全程无需记忆命令）：
1. 发起 no-wait 登录拿到 verification_url + device_code
2. 在对话框内显示二维码（lark-cli 生成 PNG）与授权链接
3. 用户扫码 / 网页授权后，**后台线程自动轮询完成登录**，
   对话框检测到授权成功会自行关闭，无需再点「我已授权」。

授权凭据由 lark-cli 全局持久化，应用重启无需重新登录；
本模块只在 config 中记录 auth_completed 标记，用于区分
「首次使用」与「登录过期」两种引导文案。
"""

import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

LOGIN_SCOPES = ["calendar:calendar.event:read", "calendar:calendar:read"]

# 轮询总时长与 device flow 链接有效期对齐（10 分钟）
_POLL_TOTAL_SECONDS = 600
_POLL_INTERVAL_SECONDS = 3

# 仍在运行的轮询线程登记表：对话框可能先关闭，线程不能被强行销毁，
# 运行结束后自行注销并回收。
_LIVE_WORKERS: list = []

# 仍在等待用户授权时 CLI 输出中的典型关键词
_PENDING_KEYWORDS = (
    "pending", "waiting", "slow_down", "authorization_pending",
    "timeout", "timed out", "超时", "等待", "轮询", "请在", "扫码", "尚未",
)
# 用户明确拒绝 / 设备码失效，应立即提示而不是继续轮询
_FATAL_KEYWORDS = (
    "denied", "access_denied", "expired", "invalid_device",
    "拒绝", "过期", "失效",
)

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
    kwargs = {}
    if sys.platform == "win32":
        # 避免每次调用都弹出黑色控制台窗口
        kwargs["creationflags"] = 0x08000000
    try:
        proc = subprocess.run(
            prefix + list(args),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            **kwargs,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        # 轮询场景下超时等同于「仍在等待授权」
        return -1, "", "lark-cli 执行超时"
    except Exception as e:  # noqa: BLE001
        return -1, "", str(e)


def has_lark_auth() -> bool:
    """lark-cli 用户身份是否已授权（status == ready）。"""
    rc, out, _ = _lark_cli(["auth", "status"], timeout=15)
    if rc == 0:
        try:
            data = json.loads(out)
            return data.get("identities", {}).get("user", {}).get("status") == "ready"
        except json.JSONDecodeError:
            pass
    return False


def mark_authed(config):
    """成功登录 / 成功拉取日程后持久化「已完成授权」标记。"""
    if config is not None and not config.get("auth_completed"):
        config.set("auth_completed", True)


class AuthStatusWorker(QThread):
    """后台检测 lark-cli 安装与授权状态，避免阻塞 UI。"""

    checked = Signal(bool, bool)  # cli_installed, authorized

    def run(self):
        cli_installed = shutil.which("lark-cli") is not None
        authed = has_lark_auth() if cli_installed else False
        self.checked.emit(cli_installed, authed)


class _DeviceCodeWorker(QThread):
    """后台轮询 device-code 授权结果，用户在手机上确认后自动成功。"""

    finished_ok = Signal()
    finished_err = Signal(str)
    still_waiting = Signal()

    def __init__(self, device_code: str, parent=None):
        super().__init__(parent)
        self._device_code = device_code

    def run(self):
        deadline = time.monotonic() + _POLL_TOTAL_SECONDS
        while time.monotonic() < deadline:
            if self.isInterruptionRequested():
                return
            rc, out, err = _lark_cli(
                ["auth", "login", "--device-code", self._device_code], timeout=20
            )
            if rc == 0:
                self.finished_ok.emit()
                return
            text = (err or out or "").lower()
            if any(k in text for k in _FATAL_KEYWORDS):
                self.finished_err.emit((err or out or "授权被拒绝").strip())
                return
            if any(k in text for k in _PENDING_KEYWORDS):
                self.still_waiting.emit()
            else:
                # 无法识别的输出：再轮询一轮，避免偶发文本差异把用户挡在外面
                self.still_waiting.emit()
            # 可中断的等待
            waited = 0
            while waited < _POLL_INTERVAL_SECONDS:
                if self.isInterruptionRequested():
                    return
                self.msleep(250)
                waited += 0.25
        self.finished_err.emit("授权超时（二维码 10 分钟内有效），请重新打开登录窗口")


class LoginDialog(QDialog):
    """飞书登录对话框：二维码 + 授权链接，授权后自动关闭。"""

    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("登录飞书")
        self.setFixedSize(400, 588)
        self._device_code = None
        self._verification_url = None
        self._worker = None
        self._setup_ui()
        self._start_login()

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(10)

        # 品牌徽标 + 标题
        head = QHBoxLayout()
        head.setSpacing(10)
        badge = QLabel("日")
        badge.setObjectName("loginBadge")
        badge.setFixedSize(40, 40)
        head.addWidget(badge)
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("登录飞书账号")
        title.setObjectName("detailTitle")
        title.setStyleSheet("font-size: 16px;")
        subtitle = QLabel("扫码或打开链接授权日历权限，授权后自动完成")
        subtitle.setObjectName("detailLabel")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        head.addLayout(title_box)
        head.addStretch()
        layout.addLayout(head)

        # 二维码卡片
        self.qr_card = QFrame()
        self.qr_card.setObjectName("qrCard")
        self.qr_card.setFixedSize(248, 248)
        card_layout = QVBoxLayout(self.qr_card)
        card_layout.setContentsMargins(10, 10, 10, 10)
        self.qr_label = QLabel("正在生成二维码...")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qr_label.setStyleSheet("color: #646A73; font-size: 12px; background: transparent;")
        card_layout.addWidget(self.qr_label)
        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(self.qr_card)
        qr_row.addStretch()
        layout.addLayout(qr_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("detailLabel")
        self.status_label.setStyleSheet("font-size: 12px; color: #646A73;")
        self.status_label.setWordWrap(True)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.retry_btn = QPushButton("重新生成二维码")
        self.retry_btn.setObjectName("linkBtn")
        self.retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.retry_btn.setVisible(False)
        self.retry_btn.clicked.connect(self._start_login)
        retry_row = QHBoxLayout()
        retry_row.addStretch()
        retry_row.addWidget(self.retry_btn)
        retry_row.addStretch()
        layout.addLayout(retry_row)

        # 主操作行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self.copy_btn = QPushButton("复制链接")
        self.copy_btn.setObjectName("secondaryBtn")
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._on_copy_url)
        btn_row.addWidget(self.copy_btn)

        self.open_btn = QPushButton("打开授权页面")
        self.open_btn.setObjectName("primaryBtn")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self._on_open_url)
        btn_row.addWidget(self.open_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

        cancel_btn = QPushButton("稍后再说")
        cancel_btn.setObjectName("linkBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(cancel_btn)
        layout.addLayout(bottom)

    # --------------------------------------------------------------- login
    def _start_login(self):
        """发起 device flow 并启动后台自动轮询。"""
        # 停掉旧轮询
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
        self.retry_btn.setVisible(False)
        self.qr_label.setText("正在生成二维码...")
        self.status_label.setText("正在发起登录...")
        self.copy_btn.setEnabled(False)
        self.open_btn.setEnabled(False)

        args = ["auth", "login", "--no-wait", "--json", "--scope", " ".join(LOGIN_SCOPES)]
        rc, out, err = _lark_cli(args, timeout=30)
        if rc != 0:
            self._fail(f"发起登录失败：{err or out}")
            return
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            self._fail(f"lark-cli 返回异常：{out[:200]}")
            return

        self._device_code = data.get("device_code")
        self._verification_url = data.get("verification_url")
        if not self._device_code or not self._verification_url:
            self._fail("lark-cli 未返回授权链接，请检查 lark-cli 版本")
            return
        self._generate_qrcode(self._verification_url)

        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(True)
        self.status_label.setText(
            "请使用飞书 App 扫描二维码，或在浏览器中完成授权。\n"
            "授权成功后窗口会自动关闭，链接 10 分钟内有效。"
        )
        self._start_polling()

    def _start_polling(self):
        # 不设置 parent：对话框若提前关闭，线程仍可安全跑完并自行注销
        self._worker = _DeviceCodeWorker(self._device_code)
        self._worker.finished_ok.connect(self._on_success)
        self._worker.finished_err.connect(self._fail)
        self._worker.still_waiting.connect(self._on_waiting)
        self._worker.finished.connect(self._on_worker_finished)
        _LIVE_WORKERS.append(self._worker)
        self._worker.start()

    def _on_worker_finished(self):
        worker = self.sender()
        if worker in _LIVE_WORKERS:
            _LIVE_WORKERS.remove(worker)

    def _on_waiting(self):
        if self.status_label.text().startswith("请使用飞书"):
            self.status_label.setText(
                "请使用飞书 App 扫描二维码，或在浏览器中完成授权。\n"
                "正在等待授权确认…"
            )

    def _generate_qrcode(self, url: str):
        try:
            tmp_dir = Path(tempfile.gettempdir())
            out_name = "feishu-login-qr.png"
            rc, _, _ = _lark_cli(
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
                                224,
                                224,
                                Qt.AspectRatioMode.KeepAspectRatio,
                                Qt.TransformationMode.SmoothTransformation,
                            )
                        )
                        return
            self.qr_label.setText("二维码生成失败\n请使用下方链接授权")
        except Exception as e:  # noqa: BLE001
            self.qr_label.setText(f"二维码生成失败：{e}")

    # ------------------------------------------------------------- actions
    def _on_open_url(self):
        if self._verification_url:
            QDesktopServices.openUrl(QUrl(self._verification_url))

    def _on_copy_url(self):
        if not self._verification_url:
            return
        QApplication.clipboard().setText(self._verification_url)
        self.copy_btn.setText("已复制")
        QTimer.singleShot(1800, lambda: self.copy_btn.setText("复制链接"))

    def _on_success(self):
        mark_authed(self._config)
        self.accept()

    def _fail(self, msg: str):
        self.status_label.setText(f"登录遇到问题：{msg}")
        self.status_label.setStyleSheet("font-size: 12px; color: #F54A45;")
        self.qr_label.setText("二维码不可用")
        self.retry_btn.setVisible(True)

    def closeEvent(self, ev):
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
        super().closeEvent(ev)
