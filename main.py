"""FeishuCalendarDesktop - Main entry point with system tray."""

import sys
import shutil
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
    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
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
            "<p>在 Windows 桌面显示飞书日历日程</p>"
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
    config = Config()

    # Check if we have either lark-cli or app credentials
    has_lark_cli = shutil.which("lark-cli") is not None
    has_app_credentials = bool(config.get("app_id", "") and config.get("app_secret", ""))

    if not has_lark_cli and not has_app_credentials:
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "缺少配置",
            "未检测到 lark-cli 且未配置飞书应用凭证。\n\n"
            "请选择以下方式之一：\n\n"
            "方式一：安装 lark-cli\n"
            "  npm install -g @larksuite/cli\n"
            "  lark-cli config init\n"
            "  lark-cli auth login --recommend\n\n"
            "方式二：在设置中配置飞书应用凭证\n"
            "  在飞书开放平台创建应用，获取 App ID 和 App Secret",
        )
        sys.exit(1)

    app = TrayApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
