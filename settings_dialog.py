"""Settings dialog — tabbed (通用 / 账号 / 外观 / 关于).

v2.1 调整：
- 登录状态检测走后台线程，不再卡住界面；
- 「检查更新」结果以内联文案呈现，不再弹 QMessageBox；
- 登录成功后主动发出 settings_changed，主窗口立即重新拉取日程。
"""

import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import updater
import usage_stats
from config import Config
from login_dialog import AuthStatusWorker, LoginDialog


class SettingsDialog(QDialog):
    """Tabbed settings dialog."""

    settings_changed = Signal()
    login_succeeded = Signal()
    pin_changed = Signal(bool)

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setFixedSize(520, 560)
        self._status_worker = None
        self._check_worker = None
        self._stats_worker = None
        self._setup_ui()
        self._start_auth_check()
        self._start_stats_load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_general_tab(), "通用")
        self.tabs.addTab(self._build_connection_tab(), "账号")
        self.tabs.addTab(self._build_appearance_tab(), "外观")
        self.tabs.addTab(self._build_about_tab(), "关于")
        layout.addWidget(self.tabs, 1)

        # Bottom close button
        bottom = QHBoxLayout()
        bottom.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)
        layout.setContentsMargins(0, 12, 16, 16)

    # ── General tab ──

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        refresh_group = QGroupBox("自动刷新")
        refresh_layout = QFormLayout(refresh_group)
        interval_row = QHBoxLayout()
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(60, 3600)
        self.interval_spin.setSingleStep(60)
        self.interval_spin.setValue(self.config.get("auto_refresh_interval", 300))
        self.interval_spin.setSuffix(" 秒")
        self.interval_spin.valueChanged.connect(self._on_interval_changed)
        interval_row.addWidget(self.interval_spin)
        interval_row.addWidget(QLabel("（1-60 分钟）"))
        interval_row.addStretch()
        refresh_layout.addRow("刷新间隔：", self._wrap_row(interval_row))
        layout.addWidget(refresh_group)

        startup_group = QGroupBox("开机启动")
        startup_layout = QVBoxLayout(startup_group)
        self.auto_start_check = QCheckBox("开机时自动启动飞书日程")
        self.auto_start_check.setChecked(self.config.get("auto_start", False))
        self.auto_start_check.stateChanged.connect(self._on_auto_start_changed)
        startup_layout.addWidget(self.auto_start_check)
        layout.addWidget(startup_group)

        update_group = QGroupBox("版本更新")
        update_layout = QVBoxLayout(update_group)
        self.update_check = QCheckBox("启动时自动检查更新")
        self.update_check.setChecked(self.config.get("check_update_on_start", True))
        self.update_check.stateChanged.connect(self._on_update_check_changed)
        update_layout.addWidget(self.update_check)
        check_row = QHBoxLayout()
        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setObjectName("secondaryBtn")
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.clicked.connect(self._on_check_update)
        check_row.addWidget(self.check_update_btn)
        self.update_result_label = QLabel("")
        self.update_result_label.setObjectName("detailLabel")
        self.update_result_label.setWordWrap(True)
        check_row.addWidget(self.update_result_label, 1)
        update_layout.addLayout(check_row)
        layout.addWidget(update_group)

        layout.addStretch()
        return tab

    def _wrap_row(self, row_layout):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        w.setLayout(row_layout)
        return w

    # ── Connection tab ──

    def _build_connection_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        auth_group = QGroupBox("飞书账号")
        auth_layout = QVBoxLayout(auth_group)
        auth_layout.setSpacing(8)

        self.auth_status_label = QLabel("正在检测登录状态…")
        self.auth_status_label.setObjectName("detailValue")
        auth_layout.addWidget(self.auth_status_label)

        hint = QLabel(
            "登录凭据由 lark-cli 全局保存，重启应用、重启电脑都无需重新登录；\n"
            "仅当授权过期或在其他设备上被撤销时才需要重新扫码。"
        )
        hint.setObjectName("detailLabel")
        hint.setWordWrap(True)
        auth_layout.addWidget(hint)

        self.login_btn = QPushButton("登录飞书账号")
        self.login_btn.setObjectName("primaryBtn")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self.login_btn)
        btn_row.addStretch()
        auth_layout.addLayout(btn_row)
        layout.addWidget(auth_group)

        layout.addStretch()
        return tab

    def _start_auth_check(self):
        self.auth_status_label.setText("正在检测登录状态…")
        self.auth_status_label.setStyleSheet("color: #8F959E;")
        self.login_btn.setEnabled(False)
        self._status_worker = AuthStatusWorker(self)
        self._status_worker.checked.connect(self._on_auth_status)
        self._status_worker.start()

    def _on_auth_status(self, cli_installed: bool, authed: bool):
        self.login_btn.setEnabled(True)
        if not cli_installed:
            self.auth_status_label.setText("● 未检测到 lark-cli，请先安装：npm install -g @larksuite/cli")
            self.auth_status_label.setStyleSheet("color: #FF8800;")
            self.login_btn.setText("重新检测")
        elif authed:
            self.auth_status_label.setText("● 已登录（重启应用无需重新登录）")
            self.auth_status_label.setStyleSheet("color: #2EA121;")
            self.login_btn.setText("重新登录")
        else:
            self.auth_status_label.setText("○ 未登录")
            self.auth_status_label.setStyleSheet("color: #F54A45;")
            self.login_btn.setText("登录飞书账号")

    def _on_login(self):
        dialog = LoginDialog(self, config=self.config)
        accepted = dialog.exec() == LoginDialog.DialogCode.Accepted
        if accepted:
            self.login_succeeded.emit()
        self._start_auth_check()

    # ── Appearance tab ──

    def _build_appearance_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        theme_group = QGroupBox("主题")
        theme_layout = QVBoxLayout(theme_group)
        self.light_radio = QRadioButton("浅色（飞书默认）")
        self.dark_radio = QRadioButton("深色")
        self.theme_group = QButtonGroup(self)
        self.theme_group.addButton(self.light_radio)
        self.theme_group.addButton(self.dark_radio)
        current_theme = self.config.get("theme", "light")
        self.light_radio.setChecked(current_theme == "light")
        self.dark_radio.setChecked(current_theme == "dark")
        self.light_radio.toggled.connect(self._on_theme_changed)
        theme_layout.addWidget(self.light_radio)
        theme_layout.addWidget(self.dark_radio)
        layout.addWidget(theme_group)

        behavior_group = QGroupBox("窗口行为")
        behavior_layout = QVBoxLayout(behavior_group)
        self.pin_check = QCheckBox("窗口置顶显示")
        self.pin_check.setChecked(self.config.get("pin_to_top", True))
        self.pin_check.stateChanged.connect(self._on_pin_changed)
        behavior_layout.addWidget(self.pin_check)
        layout.addWidget(behavior_group)

        opacity_group = QGroupBox("窗口透明度")
        opacity_layout = QVBoxLayout(opacity_group)
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(float(self.config.get("opacity", 1.0)) * 100))
        self.opacity_label = QLabel(f"{self.opacity_slider.value()}%")
        self.opacity_slider.valueChanged.connect(self._on_opacity_changed)
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        layout.addWidget(opacity_group)

        layout.addStretch()
        return tab

    # ── About tab ──

    def _build_about_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        title = QLabel("飞书日程")
        title.setObjectName("detailTitle")
        title.setStyleSheet("font-size: 18px;")
        layout.addWidget(title)

        from __version__ import APP_VERSION as __version__

        version_label = QLabel(f"版本 {__version__}")
        version_label.setObjectName("detailLabel")
        layout.addWidget(version_label)

        desc = QLabel(
            "飞书日历桌面小工具，支持月视图 / 周视图、拖拽改期、"
            "本地颜色标记、Excel 导出、全局搜索、开机自启。\n"
            "数据通过飞书官方 lark-cli 读取，不经过任何第三方服务器。"
        )
        desc.setObjectName("detailLabel")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        link_row = QHBoxLayout()
        self.repo_btn = QPushButton("项目主页")
        self.repo_btn.setObjectName("linkBtn")
        self.repo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.repo_btn.clicked.connect(lambda: self._open_url(updater.REPO_WEB))
        link_row.addWidget(self.repo_btn)

        self.download_btn = QPushButton("下载最新版")
        self.download_btn.setObjectName("linkBtn")
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.clicked.connect(lambda: self._open_url(updater.RELEASES_LATEST))
        link_row.addWidget(self.download_btn)
        link_row.addStretch()
        layout.addLayout(link_row)

        usage_group = QGroupBox("使用情况")
        usage_layout = QVBoxLayout(usage_group)
        self.usage_total_label = QLabel("正在获取使用数据…")
        self.usage_total_label.setObjectName("detailValue")
        self.usage_active_label = QLabel("")
        self.usage_active_label.setObjectName("detailValue")
        self.usage_status_label = QLabel(
            "匿名统计，不包含飞书账号、日程内容和设备标识。"
        )
        self.usage_status_label.setObjectName("detailLabel")
        self.usage_status_label.setWordWrap(True)
        usage_layout.addWidget(self.usage_total_label)
        usage_layout.addWidget(self.usage_active_label)
        usage_layout.addWidget(self.usage_status_label)
        layout.addWidget(usage_group)

        layout.addStretch()
        return tab

    def _open_url(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    # ── Handlers ──

    def _on_auto_start_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.config.set("auto_start", enabled)
        self._set_auto_start(enabled)
        self.settings_changed.emit()

    def _set_auto_start(self, enabled: bool):
        """Register / unregister auto-start (Windows registry / macOS LaunchAgent)."""
        if sys.platform == "win32":
            self._set_windows_autostart(enabled)
        elif sys.platform == "darwin":
            self._set_macos_autostart(enabled)

    def _set_windows_autostart(self, enabled: bool):
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        try:
            if enabled:
                exe = sys.executable
                if getattr(sys, "frozen", False):
                    cmd = f'"{exe}"'
                else:
                    pythonw = Path(exe).with_name("pythonw.exe")
                    target = str(pythonw if pythonw.exists() else exe)
                    script = str(Path(__file__).parent / "main.py")
                    cmd = f'"{target}" "{script}"'
                winreg.SetValueEx(key, "FeishuCalendar", 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, "FeishuCalendar")
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)

    def _set_macos_autostart(self, enabled: bool):
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_path = plist_dir / "com.feishu.calendar.plist"
        if enabled:
            plist_dir.mkdir(parents=True, exist_ok=True)
            app = Path(__file__).parent / "dist" / "飞书日程.app"
            if app.exists():
                program = str(app / "Contents" / "MacOS" / "飞书日程")
            else:
                python = sys.executable
                script = str(Path(__file__).parent / "main.py")
                program = f"{python} {script}"
            plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.feishu.calendar</string>
  <key>ProgramArguments</key><array><string>/bin/sh</string><string>-c</string><string>{program}</string></array>
  <key>RunAtLoad</key><true/>
</dict></plist>"""
            plist_path.write_text(plist, encoding="utf-8")
            subprocess.Popen(["launchctl", "load", str(plist_path)])
        else:
            if plist_path.exists():
                subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
                plist_path.unlink()

    def _on_update_check_changed(self, state):
        enabled = state == Qt.CheckState.Checked.value
        self.config.set("check_update_on_start", enabled)
        self.settings_changed.emit()

    def _on_check_update(self):
        self.update_result_label.setText("正在检查…")
        self.update_result_label.setStyleSheet("color: #8F959E;")
        self.check_update_btn.setEnabled(False)
        self._check_worker = updater.CheckWorker(self)
        self._check_worker.result.connect(self._on_check_result)
        self._check_worker.start()

    def _on_check_result(self, release):
        self.check_update_btn.setEnabled(True)
        if not release:
            self.update_result_label.setText("检查失败，请稍后重试")
            self.update_result_label.setStyleSheet("color: #F54A45;")
            return
        tag = release.get("tag", "")
        if updater.is_newer(tag, updater.APP_VERSION):
            self.update_result_label.setText(f"发现新版本 {tag}")
            self.update_result_label.setStyleSheet("color: #3370FF;")
            from update_dialog import UpdateDialog
            dlg = UpdateDialog(release, updater.APP_VERSION, self)
            dlg.exec()
        else:
            self.update_result_label.setText(f"已是最新版本（v{updater.APP_VERSION}）")
            self.update_result_label.setStyleSheet("color: #2EA121;")

    def _on_theme_changed(self):
        if self.light_radio.isChecked():
            self.config.set("theme", "light")
        else:
            self.config.set("theme", "dark")
        self.settings_changed.emit()

    def _start_stats_load(self):
        self.usage_status_label.setText("正在获取使用数据…")
        self._stats_worker = usage_stats.StatsWorker(self)
        self._stats_worker.result.connect(self._on_stats_result)
        self._stats_worker.start()

    def _on_stats_result(self, stats):
        if not isinstance(stats, dict):
            self.usage_total_label.setText("")
            self.usage_active_label.setText("")
            self.usage_status_label.setText("统计暂不可用")
            return

        def count(key):
            try:
                return max(0, int(stats.get(key, 0)))
            except (TypeError, ValueError):
                return 0

        self.usage_total_label.setText(
            f"累计使用人数：{count('cumulative_users')} 人"
        )
        self.usage_active_label.setText(
            f"近 30 天活跃：{count('active_users_30d')} 人"
        )
        self.usage_status_label.setText(
            "匿名统计，不包含飞书账号、日程内容和设备标识。"
        )

    def _on_pin_changed(self, state):
        pinned = state == Qt.CheckState.Checked.value
        self.config.set("pin_to_top", pinned)
        self.pin_changed.emit(pinned)
        self.settings_changed.emit()

    def _on_interval_changed(self, value: int):
        self.config.set("auto_refresh_interval", value)
        self.settings_changed.emit()

    def _on_opacity_changed(self, value: int):
        opacity = value / 100.0
        self.opacity_label.setText(f"{value}%")
        self.config.set("opacity", opacity)
        if self.parent():
            self.parent().setWindowOpacity(opacity)

    def closeEvent(self, ev):
        # 等待后台检测线程退出，避免对话框销毁后线程仍在运行
        for worker in (self._status_worker, self._check_worker, self._stats_worker):
            if worker is not None and hasattr(worker, "isRunning") and worker.isRunning():
                worker.requestInterruption()
                worker.quit()
                worker.wait(2000)
        super().closeEvent(ev)
