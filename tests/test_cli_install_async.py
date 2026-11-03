"""安装器 QProcess 层：能跑完、能报错、能把输出交给界面。

不起真的 npm（慢且要联网），用 /bin/sh 造出成功与失败两种情形。
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QEventLoop, QTimer

from cli_install_async import InstallWorker


def _wait(worker, timeout_ms=15000):
    """Run the worker to completion and return (ok, message, log lines)."""
    result = {"ok": None, "message": "", "logs": []}
    loop = QEventLoop()

    def on_log(line):
        result["logs"].append(line)

    def on_finished(ok, message):
        result["ok"] = ok
        result["message"] = message
        loop.quit()

    worker.log.connect(on_log)
    worker.finished.connect(on_finished)
    worker.start()

    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)
    guard.start(timeout_ms)
    loop.exec()
    worker.dispose()
    return result["ok"], result["message"], result["logs"]


@pytest.mark.skipif(
    not Path("/bin/sh").exists(), reason="需要 /bin/sh"
)
def test_success_streams_output_and_reports_ok():
    worker = InstallWorker(
        argv=["/bin/sh", "-c", "echo installed 1.0.0; exit 0"],
        npm=None,
        verifier=lambda code: code == 0,
    )
    ok, message, logs = _wait(worker)
    assert ok is True
    assert any("installed 1.0.0" in line for line in logs)
    assert "已安装" in message


@pytest.mark.skipif(
    not Path("/bin/sh").exists(), reason="需要 /bin/sh"
)
def test_failure_translates_permission_error():
    worker = InstallWorker(
        argv=["/bin/sh", "-c", "echo 'npm ERR! code EACCES'; exit 1"],
        npm=None,
        verifier=lambda code: code == 0,
    )
    ok, message, _ = _wait(worker)
    assert ok is False
    assert "权限" in message


@pytest.mark.skipif(
    not Path("/bin/sh").exists(), reason="需要 /bin/sh"
)
def test_missing_command_reports_failed_start():
    worker = InstallWorker(
        argv=["/nonexistent/npm-definitely-not-here", "install"],
        npm=None,
        verifier=lambda code: code == 0,
    )
    ok, message, _ = _wait(worker)
    assert ok is False
    assert "无法启动" in message or "安装失败" in message


def test_no_argv_settles_immediately():
    worker = InstallWorker(argv=[], npm=None)
    ok, message, _ = _wait(worker, timeout_ms=3000)
    assert ok is False
    assert "npm" in message
