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
                    # Running as frozen EXE - use the EXE path directly
                    exe_path = f'"{sys.executable}"'
                else:
                    exe_path = sys.executable
                    # If running as script, add main.py
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
    except OSError as e:
        return False


class SettingsDialog(QDialog):
    """Settings dialog for app configuration."""

    settings_changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("设置")
        self.setFixedSize(440, 560)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("设置")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        # === Feishu API Settings ===
        api_group = QGroupBox("飞书应用凭证")
        api_layout = QFormLayout(api_group)
        api_layout.setSpacing(8)

        hint = QLabel(
            "配置飞书应用凭证后，可直接通过 API 获取日程，\n"
            "无需依赖 lark-cli 授权。留空则使用 lark-cli 默认授权。"
        )
        hint.setObjectName("detailLabel")
        hint.setWordWrap(True)
        api_layout.addRow(hint)

        self.app_id_input = QLineEdit()
        self.app_id_input.setPlaceholderText("cli_xxxxxxxx")
        self.app_id_input.setText(self.config.get("app_id", ""))
        api_layout.addRow("App ID", self.app_id_input)

        self.app_secret_input = QLineEdit()
        self.app_secret_input.setPlaceholderText("应用密钥")
        self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.app_secret_input.setText(self.config.get("app_secret", ""))
        api_layout.addRow("App Secret", self.app_secret_input)

        show_secret_btn = QPushButton("显示")
        show_secret_btn.setObjectName("secondaryBtn")
        show_secret_btn.setFixedWidth(60)
        show_secret_btn.clicked.connect(self._toggle_secret_visibility)
        api_layout.addRow("", show_secret_btn)

        layout.addWidget(api_group)

        # === General Settings ===
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

        layout.addStretch()

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

    def _toggle_secret_visibility(self):
        if self.app_secret_input.echoMode() == QLineEdit.EchoMode.Password:
            self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.app_secret_input.setEchoMode(QLineEdit.EchoMode.Password)

    def _on_opacity_change(self, val):
        self.opacity_label.setText(f"窗口透明度: {val}%")

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
