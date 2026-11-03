"""no_cli 面板上的「自动安装」交互。

三件事必须成立：已经装好时不该再跑 npm、环境不允许时该去下载页而不是
硬装、确认之后才真的起安装进程。用一个假 worker 记录 start 有没有被调用，
不在这里跑真的 npm。
"""

import pytest
from PySide6.QtCore import QObject, Signal

import cli_installer
import main_window as mw_module
from config import Config


class _FakeWorker(QObject):
    log = Signal(str)
    finished = Signal(bool, str)

    instances: list["_FakeWorker"] = []

    def __init__(self, npm=None, parent=None):
        super().__init__(parent)
        self.npm = npm
        self.started = False
        _FakeWorker.instances.append(self)

    def start(self):
        self.started = True

    def dispose(self):
        pass


@pytest.fixture
def win(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    _FakeWorker.instances = []
    w = mw_module.MainWindow(Config())
    # 千万别在测试里真的去拉飞书
    monkeypatch.setattr(w, "refresh_events", lambda *a, **k: None)
    w._auth_mode = "no_cli"
    yield w
    w.dispose()
    w.deleteLater()


def _env(cli=None, npm="/opt/npm", node="/opt/node", blocker=None):
    return cli_installer.Environment(cli=cli, npm=npm, node=node, blocker=blocker)


def test_already_installed_skips_install(win, monkeypatch):
    monkeypatch.setattr(
        mw_module.cli_installer, "detect", lambda npm=None: _env(cli="/usr/local/bin/lark-cli")
    )
    monkeypatch.setattr(mw_module, "InstallWorker", _FakeWorker)

    win._on_auth_primary()

    assert win._cli_available is True
    assert not _FakeWorker.instances, "已经装好了还去跑 npm 是多余动作"


def test_missing_node_opens_download_page(win, monkeypatch):
    monkeypatch.setattr(
        mw_module.cli_installer,
        "detect",
        lambda npm=None: _env(npm=None, node=None, blocker="没找到 npm。"),
    )
    monkeypatch.setattr(mw_module, "InstallWorker", _FakeWorker)
    opened: list[str] = []
    monkeypatch.setattr(
        mw_module.QDesktopServices,
        "openUrl",
        staticmethod(lambda url: opened.append(url.toString())),
    )

    win._on_auth_primary()

    assert opened and "nodejs.org" in opened[0]
    assert not _FakeWorker.instances
    assert win._install_worker is None


def test_confirmed_starts_worker(win, monkeypatch):
    monkeypatch.setattr(mw_module.cli_installer, "detect", lambda npm=None: _env())
    monkeypatch.setattr(mw_module, "InstallWorker", _FakeWorker)
    monkeypatch.setattr(mw_module.ConfirmDialog, "ask", staticmethod(lambda *a, **k: True))

    win._on_auth_primary()

    assert _FakeWorker.instances, "确认后应当起安装"
    assert _FakeWorker.instances[0].started is True
    assert win._install_worker is _FakeWorker.instances[0]
    # 安装期间主按钮不可重复点
    assert win.auth_primary_btn.isEnabled() is False


def test_cancelled_confirm_does_nothing(win, monkeypatch):
    monkeypatch.setattr(mw_module.cli_installer, "detect", lambda npm=None: _env())
    monkeypatch.setattr(mw_module, "InstallWorker", _FakeWorker)
    monkeypatch.setattr(mw_module.ConfirmDialog, "ask", staticmethod(lambda *a, **k: False))

    win._on_auth_primary()

    assert not _FakeWorker.instances
    assert win.auth_primary_btn.isEnabled() is True


def test_done_ok_marks_cli_available(win, monkeypatch):
    win._install_worker = _FakeWorker()
    win._on_cli_install_done(True, "lark-cli 已安装：/opt/bin/lark-cli")
    assert win._cli_available is True
    assert win._install_worker is None


def test_done_failure_keeps_panel_usable(win, monkeypatch):
    win._install_worker = _FakeWorker()
    win._on_cli_install_done(False, "没有写入权限")

    assert win._cli_available is False
    assert win._install_worker is None
    assert win.auth_primary_btn.isEnabled() is True
    assert "权限" in win.auth_detail.toPlainText()


def test_install_log_keeps_tail_only(win):
    for i in range(40):
        win._on_cli_install_log(f"line {i}")
    text = win.auth_detail.toPlainText()
    assert "line 39" in text
    assert "line 0\n" not in text
