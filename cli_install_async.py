"""lark-cli 自动安装的 QProcess 包装。

和 ``lark_cli`` / ``lark_cli_async`` 同样的分法：纯逻辑留在 ``cli_installer``，
这里只管起进程、搬输出、判结果。界面线程不能阻塞在一次可能几十秒的
``npm install`` 上，所以连超时都要在 Qt 的事件循环里做。
"""

from __future__ import annotations

import shutil

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

import cli_installer


class InstallWorker(QObject):
    """Run ``npm install -g @larksuite/cli`` and stream its output.

    ``verifier`` 默认是「退出码 0 且 which 得到 lark-cli」；测试里换成只看
    退出码的版本，免得测试机上必须真的装一份。
    """

    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, argv=None, npm=None, verifier=None, parent=None):
        super().__init__(parent)
        self._npm = npm if npm is not None else cli_installer.find_npm()
        if argv is None:
            argv = cli_installer.install_argv(self._npm) if self._npm else []
        self._argv = argv
        self._verify = verifier or cli_installer.is_usable
        self._proc: QProcess | None = None
        self._buffer: list[str] = []
        self._settled = False
        self._timer: QTimer | None = None

    # ── 生命周期 ──

    def start(self):
        if not self._argv:
            self._settle(False, "没找到 npm，无法自动安装。")
            return
        proc = QProcess(self)
        proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        proc.readyReadStandardOutput.connect(self._drain)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_error)
        self._proc = proc

        # 慢网络下 npm 能磨很久，但界面不能无限转下去。
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(cli_installer.INSTALL_TIMEOUT_S * 1000)

        proc.start(self._argv[0], self._argv[1:])

    def cancel(self):
        if self._proc is not None and self._proc.state() != QProcess.ProcessState.NotRunning:
            self._proc.kill()
            self._proc.waitForFinished(1500)

    def dispose(self):
        if self._timer is not None:
            self._timer.stop()
        self.cancel()
        self._proc = None

    # ── 输出 ──

    def _drain(self):
        if self._proc is None:
            return
        raw = bytes(self._proc.readAllStandardOutput()).decode("utf-8", "replace")
        for line in raw.splitlines():
            text = line.rstrip()
            if not text:
                continue
            self._buffer.append(text)
            self.log.emit(text)

    def _on_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self._settle(False, f"无法启动 {self._argv[0]}，请确认 Node.js 安装完整。")

    def _on_timeout(self):
        self.cancel()
        self._settle(
            False,
            f"安装超过 {cli_installer.INSTALL_TIMEOUT_S} 秒仍未完成，已中止。\n"
            "网络慢的话可以换镜像后重试：npm config set registry https://registry.npmmirror.com",
        )

    def _on_finished(self, code, _status):
        self._drain()
        if self._timer is not None:
            self._timer.stop()

        # 新装的 bin 往往不在 .app 继承到的 PATH 里，先补再判定，
        # 否则会出现「npm 说装好了，应用还说找不到」。
        if self._npm:
            directory = cli_installer.npm_bin_dir(self._npm)
            cli_installer.refresh_path(directory)

        if self._verify(code):
            where = shutil.which(cli_installer.BIN_NAME) or "lark-cli"
            self._settle(True, f"lark-cli 已安装：{where}")
        else:
            self._settle(False, cli_installer.explain_failure("\n".join(self._buffer)))

    def _settle(self, ok: bool, message: str):
        if self._settled:
            return
        self._settled = True
        self.finished.emit(ok, message)
