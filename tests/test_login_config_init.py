"""首次配置引导：lark-cli not_configured 检测、init 链接抓取、登录框接线。

背景（2026-11-04 v2.10.1）：config init 之前 lark-cli 的一切授权命令都会
返回 JSON 错误 ``{"error": {"subtype": "not_configured", ...}}``，登录框
原来只把原始 JSON 甩给用户。现在自动转入「首次配置」模式：后台跑
``config init --new``、流式抓授权链接、画二维码，完成后自动继续登录。
"""

import sys

import pytest
from PySide6.QtWidgets import QApplication

import login_dialog as ld
from config import Config

app = QApplication.instance() or QApplication(sys.argv[:1])


class _FakeSignal:
    """最小信号替身：只记录槽函数，供测试手动 emit。"""

    def __init__(self):
        self.slots = []

    def connect(self, fn, *a, **kw):
        self.slots.append(fn)

    def emit(self, *args):
        for fn in list(self.slots):
            fn(*args)


class _FakeInitWorker:
    """_ConfigInitWorker 替身，带真实 QThread 的 finished/isRunning 接口。"""

    def __init__(self, parent=None):
        self.url_found = _FakeSignal()
        self.finished_rc = _FakeSignal()
        self.finished = _FakeSignal()
        self.stopped = False
        self._running = False

    def start(self):
        self._running = True

    def stop(self):
        self.stopped = True
        self._running = False

    def isRunning(self):
        return self._running


# ── not_configured 检测 ────────────────────────────────────────────────────


def test_detects_json_error_payload():
    payload = (
        '{"ok": false, "error": {"type": "config", "subtype": "not_configured",'
        ' "message": "not configured", "hint": "run lark-cli config init --new"}}'
    )
    assert ld._is_not_configured(payload)


def test_detects_mixed_stderr_output():
    # node 等其他进程的输出混在前面，JSON 解析会失败，字符串兜底要接住
    text = 'env: node: No such file or directory\n{"error":{"subtype":"not_configured"}}'
    assert ld._is_not_configured(text)


def test_rejects_other_errors():
    assert not ld._is_not_configured('{"error": {"subtype": "access_denied"}}')
    assert not ld._is_not_configured("")
    assert not ld._is_not_configured("lark-cli 执行超时")


# ── init 链接抓取 ──────────────────────────────────────────────────────────


def test_extract_init_url_from_qr_hint_line():
    line = "  https://open.feishu.cn/page/cli?user_code=MCBR-XEYG&lpv=1.0.98&from=cli\n"
    url = ld.extract_init_url(line)
    assert url is not None
    assert url.startswith("https://open.feishu.cn/page/cli?")
    assert "user_code=MCBR-XEYG" in url
    assert not url.endswith("\n")


def test_extract_init_url_strips_trailing_cjk_punct():
    line = "或打开以下链接完成配置：https://open.feishu.cn/page/cli?user_code=AB12-CD34）"
    url = ld.extract_init_url(line)
    assert url is not None
    assert url.endswith("AB12-CD34")


def test_extract_init_url_none_for_plain_line():
    assert ld.extract_init_url("正在获取你的应用配置结果...") is None
    assert ld.extract_init_url("") is None
    # 其他域名的链接不认
    assert ld.extract_init_url("see https://example.com/page/cli?x=1") is None


# ── 登录框接线：not_configured 自动转入初始化模式 ─────────────────────────


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    import config as config_module

    monkeypatch.setattr(config_module, "get_app_dir", lambda: tmp_path)
    return Config()


def test_login_dialog_enters_init_mode(cfg, monkeypatch):
    monkeypatch.setattr(
        ld,
        "_lark_cli",
        lambda args, timeout=60, cwd=None: (
            1,
            "",
            '{"ok": false, "error": {"type": "config", "subtype": "not_configured"}}',
        ),
    )
    started = {}

    class FakeInitWorker(_FakeInitWorker):
        def __init__(self, parent=None):
            super().__init__(parent)
            started["created"] = True

        def start(self):
            super().start()
            started["started"] = True

    monkeypatch.setattr(ld, "_ConfigInitWorker", FakeInitWorker)

    dlg = ld.LoginDialog(config=cfg)
    try:
        assert started.get("created") and started.get("started")
        assert "首次配置" in dlg.status_label.text()
        assert not dlg.copy_btn.isEnabled()
    finally:
        dlg.deleteLater()
        app.processEvents()


def test_init_success_triggers_relogin(cfg, monkeypatch):
    """config init 成功（rc==0）后应自动重新走登录流程。"""
    calls = {"n": 0}

    def fake_lark_cli(args, timeout=60, cwd=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return (1, "", '{"error": {"subtype": "not_configured"}}')
        # 第二次（init 完成后重试）返回正常 device flow 应答
        return (
            0,
            '{"device_code": "DC", "verification_url": "https://open.feishu.cn/page/v?x=1"}',
            "",
        )

    monkeypatch.setattr(ld, "_lark_cli", fake_lark_cli)
    monkeypatch.setattr(ld, "_ConfigInitWorker", _FakeInitWorker)
    polled = {}

    def fake_start_polling(self):
        polled["yes"] = True

    monkeypatch.setattr(ld.LoginDialog, "_start_polling", fake_start_polling)

    dlg = ld.LoginDialog(config=cfg)
    try:
        assert calls["n"] == 1
        dlg._on_init_done(0)  # 模拟 init 进程成功退出
        assert calls["n"] == 2  # 自动重新发起登录
        assert polled.get("yes")
    finally:
        dlg.deleteLater()
        app.processEvents()


# ── 生命周期（v2.11.3）─────────────────────────────────────────────────────
# AGENTS.md 的约定：线程不设 parent、登记到 _LIVE_WORKERS、finished 后注销；
# 禁止销毁仍在运行的 QThread。_ConfigInitWorker 此前漏了这套，且「稍后再说」
# 走 reject() 不触发 closeEvent，config init 子进程会一直挂着。


def _enter_init_mode(cfg, monkeypatch):
    monkeypatch.setattr(
        ld, "_lark_cli", lambda *a, **kw: (1, "", '{"error": {"subtype": "not_configured"}}')
    )
    monkeypatch.setattr(ld, "_ConfigInitWorker", _FakeInitWorker)
    return ld.LoginDialog(config=cfg)


def test_init_worker_is_registered_in_live_workers(cfg, monkeypatch):
    dlg = _enter_init_mode(cfg, monkeypatch)
    try:
        assert dlg._init_worker in ld._LIVE_WORKERS
    finally:
        dlg.reject()
        dlg.deleteLater()
        app.processEvents()


def test_reject_stops_init_worker(cfg, monkeypatch):
    """「稍后再说」连接的是 reject()，不走 closeEvent，必须自己收尾。"""
    dlg = _enter_init_mode(cfg, monkeypatch)
    try:
        dlg.reject()
        assert dlg._init_worker.stopped is True
        assert dlg._closed is True
    finally:
        dlg.deleteLater()
        app.processEvents()


def test_init_done_ignored_after_close(cfg, monkeypatch):
    """窗口已关，init 才返回成功：不得再发起一次登录。"""
    dlg = _enter_init_mode(cfg, monkeypatch)
    polled = {}
    monkeypatch.setattr(ld.LoginDialog, "_start_login", lambda self: polled.setdefault("yes", True))
    try:
        dlg.reject()
        dlg._on_init_done(0)
        assert not polled
    finally:
        dlg.deleteLater()
        app.processEvents()
