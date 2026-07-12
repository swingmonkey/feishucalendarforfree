"""Settings dialog for configuring App ID, App Secret, auto-start, etc."""

import os
import sys
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


def is_auto_start_enabled() -> bool:
    """Check if auto-start is enabled in Windows registry."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, "FeishuCalendarDesktop")
        winreg.CloseKey(key)
        return True
    except (FileNotFoundError, OSError):
        return False


def set_auto_start(enabled: bool, exe_path: str = None) -> bool:
    """Enable or disable auto-start in Windows registry."""
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
            winreg.SetValueEx(key, "FeishuCalendarDesktop", 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, "FeishuCalendarDesktop")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except OSError:
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
        """Build the connection configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Mode hint
        mode_hint = QLabel(
            "选择一种方式连接飞书日历：\n"
            "• 方式一（推荐）：安装 lark-cli，扫码授权即可使用\n"
            "• 方式二：填写飞书应用凭证（App ID + App Secret）"
        )
        mode_hint.setObjectName("detailLabel")
        mode_hint.setWordWrap(True)
        layout.addWidget(mode_hint)

        # === Method 1: lark-cli ===
        cli_group = QGroupBox("方式一：lark-cli 授权（推荐）")
        cli_layout = QVBoxLayout(cli_group)
        cli_layout.setSpacing(6)

        cli_hint = QTextEdit()
        cli_hint.setReadOnly(True)
        cli_hint.setMaximumHeight(170)
        cli_hint.setHtml(
            "<b>安装和使用步骤：</b><br>"
            "1. 安装 Node.js（https://nodejs.org）<br>"
            "2. 打开命令行，执行：<br>"
            "&nbsp;&nbsp;&nbsp;<code>npm install -g @larksuite/cli</code><br>"
            "3. 初始化配置：<br>"
            "&nbsp;&nbsp;&nbsp;<code>lark-cli config init</code><br>"
            "4. 扫码登录授权（必须包含日历读取权限）：<br>"
            "&nbsp;&nbsp;&nbsp;<code>lark-cli auth login --scope \"calendar:calendar.event:read\" --scope \"calendar:calendar:read\"</code><br>"
            "5. 完成后无需在此页面填写任何内容，直接保存即可<br>"
            "<br><b>注意：</b>--recommend 不包含日历日程读取权限，"
            "必须使用上面的 --scope 参数指定。"
        )
        cli_layout.addWidget(cli_hint)

        # Check lark-cli status
        import shutil
        has_cli = shutil.which("lark-cli") is not None
        status_label = QLabel()
        if has_cli:
            status_label.setText("✅ 已检测到 lark-cli，可直接使用")
            status_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        else:
            status_label.setText("❌ 未检测到 lark-cli，请按上方步骤安装")
            status_label.setStyleSheet("color: #f38ba8; font-size: 12px;")
        cli_layout.addWidget(status_label)

        layout.addWidget(cli_group)

        # === Method 2: App credentials ===
        api_group = QGroupBox("方式二：飞书应用凭证")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(6)

        api_hint = QTextEdit()
        api_hint.setReadOnly(True)
        api_hint.setMaximumHeight(170)
        api_hint.setHtml(
            "<b>获取步骤：</b><br>"
            "1. 访问飞书开放平台 https://open.feishu.cn<br>"
            "2. 创建企业自建应用<br>"
            "3. 在「应用能力」中开启「机器人」<br>"
            "4. 在「权限管理」中添加日历权限：<br>"
            "&nbsp;&nbsp;&nbsp;• calendar:calendar:readonly（读取日历）<br>"
            "&nbsp;&nbsp;&nbsp;• calendar:calendar（管理日历）<br>"
            "5. 在「版本管理与发布」中创建版本并发布<br>"
            "6. 复制 App ID 和 App Secret 填入下方"
        )
        api_layout.addRow(api_hint)

        self.app_id_input = QLineEdit()
        self.app_id_input.setPlaceholderText("cli_xxxxxxxx")
        self.app_id_input.setText(self.config.get("app_id", ""))
        api_layout.addRow("App ID", self.app_id_input)

        secret_row = QHBoxLayout()
        self.app_secret_input = QLineEdit()
        self.app_secret_input.setPlaceholderText("应用密钥")
        self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.app_secret_input.setText(self.config.get("app_secret", ""))
        secret_row.addWidget(self.app_secret_input)

        show_secret_btn = QPushButton("显示")
        show_secret_btn.setObjectName("secondaryBtn")
        show_secret_btn.setFixedWidth(50)
        show_secret_btn.clicked.connect(self._toggle_secret_visibility)
        secret_row.addWidget(show_secret_btn)
        api_layout.addRow("App Secret", secret_row)

        note_label = QLabel("提示：留空 App ID 和 App Secret 则使用方式一（lark-cli）")
        note_label.setObjectName("detailLabel")
        note_label.setWordWrap(True)
        api_layout.addRow(note_label)

        # Test connection and clear credentials buttons
        test_row = QHBoxLayout()
        test_btn = QPushButton("测试连接")
        test_btn.setObjectName("primaryBtn")
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.clicked.connect(self._on_test_connection)
        test_row.addStretch()
        test_row.addWidget(test_btn)

        clear_btn = QPushButton("清除凭证")
        clear_btn.setObjectName("secondaryBtn")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_credentials)
        test_row.addWidget(clear_btn)
        api_layout.addRow(test_row)

        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMaximumHeight(100)
        self.test_result.setObjectName("detailLabel")
        api_layout.addRow(self.test_result)

        layout.addWidget(api_group)

        layout.addStretch()
        return tab

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
            "飞书日程桌面助手 v2.0\n\n"
            "在 Windows 桌面显示飞书日历日程\n"
            "支持月历网格视图、添加/删除/导出日程\n\n"
            "GitHub: github.com/swingmonkey/feishucalendarforfree\n"
            "License: MIT"
        )
        about_label.setObjectName("detailLabel")
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)
        layout.addWidget(about_group)

        layout.addStretch()
        return tab

    def _toggle_secret_visibility(self):
        if self.app_secret_input.echoMode() == QLineEdit.EchoMode.Password:
            self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_clear_credentials(self):
        """Clear App ID and App Secret fields, switching to lark-cli mode."""
        self.app_id_input.clear()
        self.app_secret_input.clear()
        self.test_result.setPlainText("已清除凭证，保存后将使用方式一（lark-cli）")
        self.test_result.setStyleSheet("color: #a6e3a1; font-size: 12px;")

    def _on_opacity_change(self, val):
        self.opacity_label.setText(f"窗口透明度: {val}%")

    def _on_test_connection(self):
        """Test Feishu API connection with current credentials."""
        app_id = self.app_id_input.text().strip()
        app_secret = self.app_secret_input.text().strip()

        if not app_id or not app_secret:
            self.test_result.setPlainText("⚠ 请先填写 App ID 和 App Secret")
            self.test_result.setStyleSheet("color: #f38ba8; font-size: 12px;")
            return

        self.test_result.setPlainText("正在测试连接...")
        self.test_result.setStyleSheet("color: #a6adc8; font-size: 12px;")
        QApplication.processEvents()

        try:
            from feishu_api import FeishuApiWorker
            worker = FeishuApiWorker(app_id, app_secret)
            # Step 1: Get token
            worker._get_token()
            # Step 2: Try to list calendars
            worker._get_primary_calendar_id()
            self.test_result.setPlainText(
                "✅ 连接成功！\n"
                f"Token 获取成功，日历 ID: {worker._calendar_id[:30]}...\n"
                "可以保存设置并使用。"
            )
            self.test_result.setStyleSheet("color: #a6e3a1; font-size: 12px;")
        except Exception as e:
            msg = str(e)
            self.test_result.setPlainText(f"❌ 连接失败\n{msg}")
            self.test_result.setStyleSheet("color: #f38ba8; font-size: 12px;")

    def _on_save(self):
        app_id = self.app_id_input.text().strip()
        app_secret = self.app_secret_input.text().strip()

        self.config.set("app_id", app_id)
        self.config.set("app_secret", app_secret)
        self.config.set("auto_refresh_interval", self.refresh_spin.value())
        self.config.set("opacity", self.opacity_slider.value() / 100.0)

        # Auto-start
        auto_start = self.auto_start_check.isChecked()
        set_auto_start(auto_start)
        self.config.set("auto_start", auto_start)

        self.settings_changed.emit()
        self.accept()
