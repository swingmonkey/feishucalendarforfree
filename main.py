"""FeishuCalendarDesktop - Main entry point with system tray."""

import os
import sys
import shutil
import subprocess
import tempfile
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
from main_window import MainWindow


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


def _resolve_assets_dir() -> Path:
    """Resolve the directory containing bundled assets (icon.png etc).

    Works for both source runs (project root/assets/) and PyInstaller bundles.
    PyInstaller --add-data "assets:assets" places files under:
      - macOS onedir .app: <App>.app/Contents/Resources/assets/
      - Windows/Linux onedir/onefile: <exe_dir>/assets/ (or _MEIPASS/assets/)
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base = Path(sys.executable).resolve().parent.parent / "Resources"
        else:
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidate = base / "assets"
        if candidate.is_dir():
            return candidate
        return base
    return Path(__file__).resolve().parent / "assets"


def create_app_icon() -> QIcon:
    """Load the tray/app icon from assets (Pikachu icon), falling back to
    a programmatically drawn icon if assets are missing."""
    assets_dir = _resolve_assets_dir()
    # Prefer tray.png (small, transparent-background, good for menu bar)
    for candidate in ("tray.png", "icon_1024.png"):
        p = assets_dir / candidate
        if p.is_file():
            icon = QIcon(str(p))
            if not icon.isNull():
                return icon
    # Fallback: original programmatic icon
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#4B3FE3"))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(QColor("#171717"))
    font = QFont()
    font.setFamilies(["PingFang SC", "SF Pro Text", "Microsoft YaHei UI", "Segoe UI"])
    font.setPixelSize(28)
    font.setWeight(QFont.Weight.Bold)
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
        self.widget = MainWindow(self.config)
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


def _has_lark_auth() -> bool:
    """Check whether the lark-cli user identity is authorized (ready)."""
    import json

    from login_dialog import _lark_cli

    rc, out, _ = _lark_cli(["auth", "status"], timeout=15)
    if rc == 0:
        try:
            data = json.loads(out)
            return data.get("identities", {}).get("user", {}).get("status") == "ready"
        except json.JSONDecodeError:
            pass
    return False


def _ensure_desktop_shortcut(config):
    """首次运行时自动在桌面创建快捷方式（Windows .lnk / macOS symlink）。

    用 config 标记 desktop_shortcut_created，只创建一次；失败不阻塞启动。
    快捷方式已存在（例如手动删除标记）时直接补标记，不重复创建。
    """
    if config.get("desktop_shortcut_created"):
        return
    desktop = Path.home() / "Desktop"
    if not desktop.exists():
        return
    try:
        # 快捷方式已存在则视为完成，避免重复创建
        candidate = None
        if sys.platform == "win32":
            candidate = desktop / "飞书日程.lnk"
        elif sys.platform == "darwin":
            candidate = desktop / "飞书日程.app"
            if not candidate.exists():
                candidate = desktop / "启动飞书日程.command"
        if candidate is not None and candidate.exists():
            config.set("desktop_shortcut_created", True)
            return
        if sys.platform == "win32":
            _create_windows_shortcut(desktop)
        elif sys.platform == "darwin":
            _create_macos_shortcut(desktop)
        config.set("desktop_shortcut_created", True)
    except Exception:
        # 创建失败不阻塞启动，下次运行会重试
        pass


def _create_windows_shortcut(desktop: Path):
    """用 PowerShell COM 创建 .lnk，指向 pythonw + main.py（无控制台窗口）。"""
    script = Path(__file__).resolve()
    target = Path(sys.executable).with_name("pythonw.exe")
    if not target.exists():
        target = Path(sys.executable)
    lnk = desktop / "飞书日程.lnk"

    ps = (
        "$ws = New-Object -ComObject WScript.Shell" + "\n"
        + f"$s = $ws.CreateShortcut('{lnk}')" + "\n"
        + f"$s.TargetPath = '{target}'" + "\n"
        + f"$s.Arguments = '\"{script}\"'" + "\n"
        + f"$s.WorkingDirectory = '{script.parent}'" + "\n"
        + "$s.Save()" + "\n"
    )
    # 写入临时 .ps1（UTF-8 with BOM），避免命令行中文编码问题
    fd, tmp = tempfile.mkstemp(suffix=".ps1")
    try:
        with os.fdopen(fd, "w", encoding="utf-8-sig") as f:
            f.write(ps)
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", tmp],
            check=True,
            capture_output=True,
            timeout=60,
        )
    finally:
        os.unlink(tmp)


def _create_macos_shortcut(desktop: Path):
    """macOS：优先软链 .app，否则软链启动脚本 .command。"""
    app = Path(__file__).parent / "dist" / "飞书日程.app"
    if app.exists():
        link = desktop / "飞书日程.app"
        if not link.exists():
            link.symlink_to(app)
        return
    cmd = Path(__file__).parent / "启动飞书日程.command"
    if cmd.exists():
        link = desktop / "启动飞书日程.command"
        if not link.exists():
            link.symlink_to(cmd)


def main():
    # Make sure npm/brew/nvm-installed CLIs (lark-cli, node) are reachable
    # even when launched from a .app bundle with a minimal PATH.
    _extend_path_for_app_bundle()

    config = Config()

    # Create a desktop shortcut on first run (before TrayApp loads its own
    # Config instance, so the flag is persisted and not overwritten to False).
    _ensure_desktop_shortcut(config)

    # Check if we have either lark-cli or app credentials
    has_lark_cli = shutil.which("lark-cli") is not None

    # Launch the main app regardless of auth state — if not configured yet,
    # pop up the settings dialog so the user can configure credentials
    # instead of hard-exiting with only an "OK" button.
    app = TrayApp(sys.argv)

    if not has_lark_cli:
        QMessageBox.information(
            app.widget,
            "首次使用",
            "未检测到 lark-cli。\n\n请先在命令行执行：\n"
            "  npm install -g @larksuite/cli\n\n"
            "安装完成后重新启动本应用即可扫码登录。",
        )
    elif not _has_lark_auth():
        from login_dialog import LoginDialog

        dlg = LoginDialog(app.widget)
        dlg.exec()
        if _has_lark_auth():
            app.widget.refresh_events()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
