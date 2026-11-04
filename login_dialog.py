"""应用内飞书登录对话框。

通过 lark-cli 的 Device Flow 完成授权（全程无需记忆命令）：
1. 发起 no-wait 登录拿到 verification_url + device_code
2. 在对话框内直接画出二维码（本地编码，不依赖 lark-cli 的画图子命令）与授权链接
3. 用户扫码 / 网页授权后，**后台线程自动轮询完成登录**，
   对话框检测到授权成功会自行关闭，无需再点「我已授权」。

授权凭据由 lark-cli 全局持久化，应用重启无需重新登录；
本模块只在 config 中记录 auth_completed 标记，用于区分
「首次使用」与「登录过期」两种引导文案。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

import qrgen
from ui_common import set_message_kind

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


def _find_node() -> str | None:
    """定位 node 可执行文件，返回绝对路径。

    Finder 启动的 .app 只有最小 PATH，裸 ``node`` 找不到；nvm/WorkBuddy/fnm
    管的版本目录更不在里面。which 失败后扫 cli_installer 的候选目录兜底。
    """
    found = shutil.which("node")
    if found:
        return found
    import cli_installer

    for directory in cli_installer.candidate_bin_dirs():
        probe = directory / "node"
        if probe.is_file() and os.access(probe, os.X_OK):
            return str(probe)
    return None


def _resolve_lark_cmd():
    """返回可直接交给 subprocess 的 lark-cli 命令前缀。

    Windows 上 lark-cli 是 npm 的 .CMD 包装（cmd 会拆解 URL 里的 & 等字符），
    因此优先定位其真实 node 入口 scripts/run.js 直接调用，绕开 cmd 解析；
    找不到时回退 cmd /c 方式。输出均为 UTF-8，必须显式指定 encoding。

    node 一律用 _find_node() 的绝对路径：lark-cli shim 是
    ``#!/usr/bin/env node``，.app 环境里 env 找不到 node 就报
    「env: node: No such file or directory」（v2.10.0 真机踩过）。
    """
    global _LARK_RUN_JS
    node = _find_node() or "node"
    if _LARK_RUN_JS:
        # run.js 路径可以缓存，node 要现查——两次调用之间用户可能装好了 node
        return [node, _LARK_RUN_JS]
    exe = shutil.which("lark-cli")
    if exe:
        # POSIX 的 npm 全局 bin 里 lark-cli 常是直接指向 run.js 的 symlink
        #（或 bin 旁只有 shim；包本体在 prefix/lib/node_modules）。resolve
        # 后若就是 run.js 直接用；否则按 Windows（prefix/node_modules）与
        # POSIX（prefix/lib/node_modules）两种布局探测。
        exe_path = Path(exe).resolve()
        if exe_path.name == "run.js" and exe_path.is_file():
            _LARK_RUN_JS = str(exe_path)
            return [node, _LARK_RUN_JS]
        for base in (exe_path.parent, exe_path.parent.parent / "lib"):
            run_js = base / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
            if run_js.is_file():
                _LARK_RUN_JS = str(run_js)
                return [node, _LARK_RUN_JS]
    if exe:
        if exe.lower().endswith((".cmd", ".bat")):
            return ["cmd", "/c", exe]
        return [exe]
    return None


def _lark_cli(args, timeout=60, cwd=None):
    """运行 lark-cli，返回 (exit_code, stdout, stderr)。"""
    prefix = _resolve_lark_cmd()
    if not prefix:
        return -1, "", "未找到 lark-cli，请先执行 npm install -g @larksuite/cli"
    kwargs = {"cwd": cwd}
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


def _qr_pixmap(matrix, target: int = 248) -> QPixmap:
    """把模块矩阵画成位图：整数倍缩放 + 4 模块静区，保证边缘锐利。

    二维码做成非整数缩放后模块边缘会糊，手机扫起来时好时坏；这里按
    整像素对齐，宁可尺寸小一点也不用平滑插值。``target`` 取 248 是为了
    把 248×248 的二维码卡片填满（37 模块 + 8 静区 = 45，45×5 = 225）。
    """
    count = len(matrix)
    total = count + 8  # 四周各留 4 个模块的静区
    scale = max(1, target // total)
    side = total * scale
    image = QImage(side, side, QImage.Format.Format_ARGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#0b0f14"))
    for row_index, row in enumerate(matrix):
        for col_index, dark in enumerate(row):
            if dark:
                painter.drawRect(
                    (4 + col_index) * scale,
                    (4 + row_index) * scale,
                    scale,
                    scale,
                )
    painter.end()
    return QPixmap.fromImage(image)


class AuthStatusWorker(QThread):
    """后台检测 lark-cli 安装与授权状态，避免阻塞 UI。"""

    checked = Signal(bool, bool)  # cli_installed, authorized

    def run(self):
        cli_installed = shutil.which("lark-cli") is not None
        authed = has_lark_auth() if cli_installed else False
        self.checked.emit(cli_installed, authed)


# ── 首次配置引导（lark-cli 未初始化时自动发起 config init）────────────────

_INIT_URL_RE = re.compile(r"https://open\.feishu\.cn/page/cli\?\S+")


def _is_not_configured(output: str) -> bool:
    """识别 lark-cli 的「未初始化」错误（config init 前一切授权都会被拒）。

    lark-cli 的错误是 JSON（error.subtype == "not_configured"），但 stderr
    可能混入 node 等其他行，JSON 解析失败时按字符串兜底。
    """
    text = output or ""
    try:
        data = json.loads(text)
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict) and err.get("subtype") == "not_configured":
            return True
    except (json.JSONDecodeError, ValueError):
        pass
    return "not_configured" in text


def extract_init_url(line: str) -> str | None:
    """从 config init 的输出行里抓授权链接（进程会阻塞等用户完成）。"""
    m = _INIT_URL_RE.search(line or "")
    if not m:
        return None
    url = m.group(0).rstrip("\uff0c\u3002\u3001)\uff09\"\u300b\u3009")  # 防中文标点粘尾
    return url


class _ConfigInitWorker(QThread):
    """后台执行 `lark-cli config init --new` 并流式抓取授权链接。

    该命令会阻塞直到用户在浏览器完成应用创建（可能几分钟），所以
    绝不能走 _lark_cli（有 timeout）。逐行读 stdout，一拿到链接就发
    url_found——二维码可以先画出来，不必等进程结束。
    """

    url_found = Signal(str)
    finished_rc = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._proc: subprocess.Popen | None = None

    def run(self):
        prefix = _resolve_lark_cmd()
        if not prefix:
            self.finished_rc.emit(-1)
            return
        try:
            self._proc = subprocess.Popen(
                prefix + ["config", "init", "--new", "--lang", "zh"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except Exception:  # noqa: BLE001 - 启动失败按非零退出处理
            self.finished_rc.emit(-1)
            return
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            url = extract_init_url(line)
            if url:
                self.url_found.emit(url)
        rc = self._proc.wait()
        self.finished_rc.emit(rc)

    def stop(self):
        """对话框关闭时终止 init 进程（用户可能中途放弃）。"""
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()


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
        self._init_worker: _ConfigInitWorker | None = None
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
        title.setObjectName("loginTitle")
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
        self.qr_label.setObjectName("qrPlaceholder")
        self.qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.qr_label)
        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(self.qr_card)
        qr_row.addStretch()
        layout.addLayout(qr_row)

        self.status_label = QLabel("")
        self.status_label.setObjectName("detailLabel")
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
            combined = f"{out}\n{err}"
            if _is_not_configured(combined):
                # lark-cli 装了但没绑定应用：自动发起 config init，把
                # 「跑命令、抓链接、画二维码」整个流程收进应用内，
                # 首次用户不需要开终端（2026-11-04 v2.10.1 真机踩坑）。
                self._enter_init_mode()
                return
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

    def _enter_init_mode(self):
        """首次配置：后台跑 config init，授权链接直接画成二维码。"""
        self.qr_label.setText("正在准备首次配置…")
        self.status_label.setText(
            "lark-cli 还没有绑定飞书应用。\n"
            "已自动发起首次配置：请扫描二维码或打开链接，\n"
            "按页面引导创建应用（自动授予日历权限），完成后会自动继续登录。"
        )
        set_message_kind(self.status_label, "info")
        self.copy_btn.setEnabled(False)
        self.open_btn.setEnabled(False)

        self._init_worker = _ConfigInitWorker()
        self._init_worker.url_found.connect(self._on_init_url)
        self._init_worker.finished_rc.connect(self._on_init_done)
        self._init_worker.start()

    def _on_init_url(self, url: str):
        self._verification_url = url
        self._generate_qrcode(url)
        self.copy_btn.setEnabled(True)
        self.open_btn.setEnabled(True)

    def _on_init_done(self, rc: int):
        if rc == 0:
            self._verification_url = None
            self.status_label.setText("首次配置完成，正在发起登录…")
            set_message_kind(self.status_label, "info")
            self._start_login()
        else:
            self._fail(
                "首次配置未完成（已取消或失败）。\n点击「重新生成二维码」可再次发起。"
            )

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
        """本地画二维码，不依赖 `lark-cli auth qrcode`。

        原先是让 lark-cli 生成图片再读回来，命令写的是
        `auth qrcode <url> --output qr.png --size 256`——`--size` 这个参数
        lark-cli 根本没有，命令每次都以非零码退出，界面永远停在「二维码
        不可用」，登录直接卡死。自己画既没有版本差异，也不用起 node 子进程。
        """
        try:
            matrix = qrgen.make_qr(url)
        except Exception as e:  # noqa: BLE001
            self.qr_label.setText(f"二维码生成失败：{e}\n请使用下方链接授权")
            return
        self.qr_label.setPixmap(_qr_pixmap(matrix))

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
        set_message_kind(self.status_label, "error")
        self.qr_label.setText("二维码不可用")
        self.retry_btn.setVisible(True)

    def closeEvent(self, ev):
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.quit()
        if self._init_worker is not None:
            self._init_worker.stop()
        super().closeEvent(ev)
