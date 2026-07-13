"""FeishuCalendarDesktop - Main entry point with system tray."""

import os
import sys
import shutil
from pathlib import Path
from PySide6.QtWidgets import (
    QApplication,
    QSystemTrayIcon,
    QMenu,
    QMessageBox,
)
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import Qt

from config import Config
from calendar_widget import CalendarWidget


def _extend_path_for_app_bundle():
    """Extend PATH so macOS .app bundles can find npm/brew-installed CLIs.

    When launched from Finder/Spotlight, a .app inherits only a minimal
    PATH (/usr/bin:/bin:...) and cannot find lark-cli / node installed via
    npm global, homebrew, or nvm. We manually prepend those locations.
    """
    home = Path.home()
    extra = [
        str(home / ".npm-global" / "bin"),
        str(home / ".local" / "bin"),
        "/usr/local/bin",
        "/opt/homebrew/bin",
    ]
    # nvm-installed node binaries
    nvm_dir = home / ".nvm" / "versions" / "node"
    if nvm_dir.exists():
        for d in nvm_dir.iterdir():
            if d.is_dir():
                extra.append(str(d / "bin"))
    current = os.environ.get("PATH", "")
    parts = [p for p in current.split(os.pathsep) if p]
    for d in extra:
        if d not in parts and Path(d).is_dir():
            parts.append(d)
    os.environ["PATH"] = os.pathsep.join(parts)


def create_app_icon() -> QIcon:
    """Create a simple application icon programmatically."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#4B3FE3"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(QColor("#171717"))
    # Cross-platform font stack: SF/PingFang on macOS, YaHei/Segoe on Windows
    font = QFont("PingFang SC, SF Pro Text, Microsoft YaHei UI, Segoe UI", 28, QFont.Weight.Bold)
    font.setFamilies(["PingFang SC", "SF Pro Text", "Microsoft YaHei UI", "Segoe UI"])
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "日")
    painter.end()
    return QIcon(pixmap)


class TrayApp(QApplication):
    """Main application with system tray."""

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("飞书日程")
        self.setQuitOnLastWindowClosed(False)

        self.config = Config()
        self.icon = create_app_icon()
        self.widget = CalendarWidget(self.config)
        self._setup_tray()
        self.widget.show()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("飞书日程 - 点击显示")

        menu = QMenu()
        show_action = QAction("显示日程", self)
        show_action.triggered.connect(self._show_widget)
        menu.addAction(show_action)

        hide_action = QAction("隐藏窗口", self)
        hide_action.triggered.connect(self.widget.hide)
        menu.addAction(hide_action)

        menu.addSeparator()

        refresh_action = QAction("刷新日程", self)
        refresh_action.triggered.connect(self.widget.refresh_events)
        menu.addAction(refresh_action)

        add_action = QAction("添加日程", self)
        add_action.triggered.connect(self.widget._on_add_event)
        menu.addAction(add_action)

        menu.addSeparator()

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.widget._on_settings)
        menu.addAction(settings_action)

        about_action = QAction("关于", self)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self._quit)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.widget.isVisible():
                self.widget.hide()
            else:
                self._show_widget()

    def _show_widget(self):
        self.widget.show()
        self.widget.raise_()
        self.widget.activateWindow()

    def _show_about(self):
        QMessageBox.about(
            self.widget,
            "关于飞书日程",
            "<h3>飞书日程桌面助手</h3>"
            "<p>在桌面显示飞书日历日程（Windows / macOS）</p>"
            "<p>功能：查看 / 添加 / 删除飞书日程</p>"
            "<p style='color: gray;'>基于 PySide6 + lark-cli 构建</p>"
            "<p style='color: gray;'>参考 PaperTodo 设计理念</p>",
        )

    def _quit(self):
        pos = self.widget.pos()
        self.config.set("window_x", pos.x())
        self.config.set("window_y", pos.y())
        self.config.set("window_width", self.widget.width())
        self.config.set("window_height", self.widget.height())
        self.tray.hide()
        self.quit()


def main():
    # Make sure npm/brew/nvm-installed CLIs (lark-cli, node) are reachable
    # even when launched from a .app bundle with a minimal PATH.
    _extend_path_for_app_bundle()

    config = Config()

    # Check if we have either lark-cli or app credentials
    has_lark_cli = shutil.which("lark-cli") is not None
    has_app_credentials = bool(config.get("app_id", "") and config.get("app_secret", ""))

    # Launch the main app regardless of auth state — if not configured yet,
    # pop up the settings dialog so the user can configure credentials
    # instead of hard-exiting with only an "OK" button.
    app = TrayApp(sys.argv)

    if not has_lark_cli and not has_app_credentials:
        QMessageBox.information(
            app.widget,
            "首次使用",
            "未检测到 lark-cli 且未配置飞书应用凭证。\n\n"
            "请在弹出的设置面板中配置认证方式：\n"
            "• 方式一：安装 lark-cli（推荐个人使用）\n"
            "• 方式二：填写飞书应用 App ID 和 App Secret\n\n"
            "配置完成后点击保存即可使用。",
        )
        # Auto-open the settings dialog for first-time setup
        app.widget._on_settings()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
