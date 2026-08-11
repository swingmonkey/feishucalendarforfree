"""Settings dialog for configuring App ID, App Secret, auto-start, etc."""

import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QSpinBox,
    QGroupBox,
    QMessageBox,
    QTabWidget,
    QWidget,
    QTextEdit,
    QFrame,
    QApplication,
)
from PySide6.QtCore import Qt, Signal

import updater


def _auto_start_label() -> str:
    """Stable identifier used both for Windows registry value name and
    macOS LaunchAgent plist filename (without extension)."""
    return "FeishuCalendarDesktop"


# ---------------------------------------------------------------------------
# Windows: HKEY_CURRENT_USER\...\Run
# ---------------------------------------------------------------------------
def _is_auto_start_windows() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, _auto_start_label())
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def _set_auto_start_windows(enabled: bool, exe_path: str = None) -> bool:
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        if enabled:
            if exe_path is None:
                if getattr(sys, "frozen", False):
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = sys.executable
                    if exe_path.endswith("python.exe"):
                        import pathlib
                        main_py = pathlib.Path(__file__).parent / "main.py"
                        exe_path = f'"{exe_path}" "{main_py}"'
                    else:
                        exe_path = f'"{exe_path}"'
            winreg.SetValueEx(key, _auto_start_label(), 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, _auto_start_label())
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# macOS: ~/Library/LaunchAgents/<label>.plist
# ---------------------------------------------------------------------------
def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_auto_start_label()}.plist"


def _resolve_macos_executable() -> str:
    """Resolve the command to launch on macOS at login.

    Frozen .app: open the bundle.
    Source run: <python> <main.py>.
    """
    if getattr(sys, "frozen", False):
        # sys.executable is .../FeishuCalendar.app/Contents/MacOS/FeishuCalendar
        app_path = Path(sys.executable).parent.parent.parent
        return f'open "{app_path}"'
    import shutil
    py = sys.executable or shutil.which("python3") or "python3"
    main_py = Path(__file__).parent / "main.py"
    return f'"{py}" "{main_py}"'


def _is_auto_start_macos() -> bool:
    return _launch_agent_path().exists()


def _set_auto_start_macos(enabled: bool) -> bool:
    plist = _launch_agent_path()
    if not enabled:
        try:
            plist.unlink(missing_ok=True)
            # Unload if currently loaded
            import subprocess
            subprocess.run(
                ["launchctl", "unload", str(plist)],
                capture_output=True,
                text=True,
            )
        except OSError:
            pass
        return True

    # Build a LaunchAgent plist that runs the app at login
    plist.parent.mkdir(parents=True, exist_ok=True)
    cmd = _resolve_macos_executable()
    # Use sh -c so we can handle quoted commands / `open ...`
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_auto_start_label()}</string>
    <key>ProgramArguments</key>
    <array>
        <string>sh</string>
        <string>-c</string>
        <string>{cmd}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
    try:
        plist.write_text(content, encoding="utf-8")
        import subprocess
        subprocess.run(
            ["launchctl", "load", str(plist)],
            capture_output=True,
            text=True,
        )
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Platform dispatcher
# ---------------------------------------------------------------------------
def is_auto_start_enabled() -> bool:
    """Check if auto-start is enabled on the current platform."""
    if sys.platform == "darwin":
        return _is_auto_start_macos()
    if sys.platform == "win32":
        return _is_auto_start_windows()
    # Linux/other: not supported
    return False


def set_auto_start(enabled: bool, exe_path: str = None) -> bool:
    """Enable or disable auto-start on the current platform."""
    if sys.platform == "darwin":
        return _set_auto_start_macos(enabled)
    if sys.platform == "win32":
        return _set_auto_start_windows(enabled, exe_path=exe_path)
    return False


class SettingsDialog(QDialog):
    """Settings dialog with tabs for connection and general settings."""

    settings_changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setFixedSize(520, 620)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("设置")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()

        # === Tab 1: Connection ===
        tabs.addTab(self._build_connection_tab(), "飞书连接")

        # === Tab 2: General ===
        tabs.addTab(self._build_general_tab(), "通用设置")

        layout.addWidget(tabs, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("保存")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)

        layout.addLayout(btn_row)

    def _build_connection_tab(self) -> QWidget:
        """Build the connection configuration tab (lark-cli 授权，唯一认证方式)."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        hint = QLabel(
            "应用使用 lark-cli 用户授权连接飞书日历。 首次使用点击下方按钮登录，扫码或网页授权日历读写权限即可。"
        )
        hint.setObjectName("detailLabel")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        cli_group = QGroupBox("飞书账号")
        cli_layout = QVBoxLayout(cli_group)
        cli_layout.setSpacing(6)

        import shutil
        has_cli = shutil.which("lark-cli") is not None
        self.cli_status_label = QLabel()
        if has_cli:
            self.cli_status_label.setText("✅ 已检测到 lark-cli")
            self.cli_status_label.setStyleSheet("color: #34C724; font-size: 12px;")
        else:
            self.cli_status_label.setText("❌ 未检测到 lark-cli，请先执行：npm install -g @larksuite/cli")
            self.cli_status_label.setStyleSheet("color: #F54A45; font-size: 12px;")
        self.cli_status_label.setWordWrap(True)
        cli_layout.addWidget(self.cli_status_label)

        self.login_btn = QPushButton("登录飞书账号（扫码 / 网页授权）")
        self.login_btn.setObjectName("primaryBtn")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login_clicked)
        cli_layout.addWidget(self.login_btn)

        layout.addWidget(cli_group)
        layout.addStretch()
        return tab

    def _on_login_clicked(self):
        """打开应用内登录对话框（二维码 + 网页授权）。"""
        from login_dialog import LoginDialog

        dlg = LoginDialog(self)
        dlg.exec()
        # 登录后刷新 lark-cli 状态提示
        import shutil
        has_cli = shutil.which("lark-cli") is not None
        if has_cli:
            self.cli_status_label.setText("✅ 已检测到 lark-cli")
            self.cli_status_label.setStyleSheet("color: #34C724; font-size: 12px;")

    def _build_general_tab(self) -> QWidget:
        """Build the general settings tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # General settings
        general_group = QGroupBox("通用设置")
        general_layout = QFormLayout(general_group)
        general_layout.setSpacing(8)

        self.auto_start_check = QCheckBox("开机自动启动")
        self.auto_start_check.setChecked(is_auto_start_enabled())
        general_layout.addRow(self.auto_start_check)

        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(60, 3600)
        self.refresh_spin.setSuffix(" 秒")
        self.refresh_spin.setValue(self.config.get("auto_refresh_interval", 300))
        general_layout.addRow("自动刷新间隔", self.refresh_spin)

        self.opacity_label = QLabel(f"窗口透明度: {int(self.config.get('opacity', 0.95) * 100)}%")
        from PySide6.QtWidgets import QSlider
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(50, 100)
        self.opacity_slider.setValue(int(self.config.get("opacity", 0.95) * 100))
        self.opacity_slider.valueChanged.connect(self._on_opacity_change)
        general_layout.addRow(self.opacity_label)
        general_layout.addRow(self.opacity_slider)

        layout.addWidget(general_group)

        # About
        about_group = QGroupBox("关于")
        about_layout = QVBoxLayout(about_group)
        about_label = QLabel(
            f"飞书日程桌面助手 v{updater.APP_VERSION}\n\n"
            "在桌面显示飞书日历日程（Windows / macOS）\n"
            "支持月历网格视图、添加/删除/导出日程\n\n"
            "GitHub: github.com/swingmonkey/feishucalendarforfree\n"
            "License: MIT"
        )
        about_label.setObjectName("detailLabel")
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)

        self.check_update_btn = QPushButton("检查更新")
        self.check_update_btn.setObjectName("secondaryBtn")
        self.check_update_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.check_update_btn.clicked.connect(self._on_check_update)
        about_layout.addWidget(self.check_update_btn)

        layout.addWidget(about_group)

        layout.addStretch()
        return tab

    def _on_opacity_change(self, val):
        self.opacity_label.setText(f"窗口透明度: {val}%")

    def _on_check_update(self):
        """Check GitHub for a newer release and prompt to update."""
        self.check_update_btn.setEnabled(False)
        self.check_update_btn.setText("检查中…")
        try:
            release = updater.get_latest_release()
        except Exception as e:
            self.check_update_btn.setEnabled(True)
            self.check_update_btn.setText("检查更新")
            QMessageBox.information(self, "检查更新", f"检查失败：{e}")
            return
        self.check_update_btn.setEnabled(True)
        self.check_update_btn.setText("检查更新")
        if not release or not release.get("tag"):
            QMessageBox.information(self, "检查更新", "无法获取版本信息")
            return
        if updater.is_newer(release.get("tag", "")):
            from update_dialog import UpdateDialog

            dlg = UpdateDialog(release, updater.APP_VERSION, self)
            dlg.exec()
        else:
            QMessageBox.information(self, "检查更新", "已是最新版本 ✓")

    def _on_save(self):
        self.config.set("auto_refresh_interval", self.refresh_spin.value())
        self.config.set("opacity", self.opacity_slider.value() / 100.0)

        # Auto-start
        auto_start = self.auto_start_check.isChecked()
        set_auto_start(auto_start)
        self.config.set("auto_start", auto_start)

        self.settings_changed.emit()
        self.accept()
