"""FeishuCalendarDesktop - Main entry point with system tray."""

import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMenu,
    QSystemTrayIcon,
)

import updater
from app_icon import create_app_icon
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


class TrayApp(QApplication):
    """Main application with system tray."""

    def __init__(self, argv):
        super().__init__(argv)
        self.setApplicationName("飞书日程")
        self.setQuitOnLastWindowClosed(False)

        self.config = Config()
        self.icon = create_app_icon()
        self.setWindowIcon(self.icon)
        self.widget = MainWindow(self.config)
        self.widget.setWindowIcon(self.icon)
        self._setup_tray()
        self.widget.show()
        self._setup_update_check()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setToolTip("飞书日程 - 点击显示")

        menu = QMenu()
        menu.setObjectName("trayMenu")
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

        login_action = QAction("登录 / 重新登录", self)
        login_action.triggered.connect(self.widget.open_login)
        menu.addAction(login_action)

        menu.addSeparator()

        settings_action = QAction("设置", self)
        settings_action.triggered.connect(self.widget._on_settings)
        menu.addAction(settings_action)

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

    def _setup_update_check(self):
        """Silently check for a newer release shortly after launch."""
        if not self.config.get("check_update_on_start", True):
            return
        from PySide6.QtCore import QTimer

        QTimer.singleShot(4000, self._background_check)

    def _background_check(self):
        self._check_worker = updater.CheckWorker()
        self._check_worker.result.connect(self._on_update_checked)
        self._check_worker.start()

    def _on_update_checked(self, release):
        if not release:
            return
        if updater.is_newer(release.get("tag", ""), updater.APP_VERSION):
            # 不再弹窗打断，仅在主窗口底部给一条可点击的轻提示
            self.widget.notify_update(release)

    def _quit(self):
        pos = self.widget.pos()
        self.config.set("window_x", pos.x())
        self.config.set("window_y", pos.y())
        self.config.set("window_width", self.widget.width())
        self.config.set("window_height", self.widget.height())
        self.tray.hide()
        self.quit()


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
    # Configure logging so config.py and other modules can surface warnings
    # (e.g. config save failures) without requiring external setup.
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Make sure npm/brew/nvm-installed CLIs (lark-cli, node) are reachable
    # even when launched from a .app bundle with a minimal PATH.
    _extend_path_for_app_bundle()

    # Remove the '.old' EXE left behind by a previous frozen self-update
    # (no-op when running from source).
    updater.cleanup_old_executable()

    config = Config()

    # Create a desktop shortcut on first run (before TrayApp loads its own
    # Config instance, so the flag is persisted and not overwritten to False).
    _ensure_desktop_shortcut(config)

    # 启动不再做任何阻塞式授权检查、也不弹登录/提示框：
    # 主窗口会直接加载，未安装 lark-cli / 未登录 / 加载失败均以内联
    # 状态面板引导，登录成功后由 lark-cli 全局持久化，重启无需重登。
    app = TrayApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
