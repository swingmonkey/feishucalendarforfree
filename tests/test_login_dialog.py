"""Offline regressions for the in-app QR login flow."""

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QLabel

import login_dialog


def test_qrcode_uses_private_relative_workdir(monkeypatch):
    app = QApplication.instance() or QApplication([])
    fake = SimpleNamespace(qr_label=QLabel())
    state = {}

    def fake_lark_cli(args, timeout=60, cwd=None):
        assert cwd is not None
        state["cwd"] = cwd
        output_index = args.index("--output") + 1
        output_name = args[output_index]
        state["output_name"] = output_name
        assert not os.path.isabs(output_name)

        image = QImage(16, 16, QImage.Format.Format_ARGB32)
        image.fill(QColor("#3370FF"))
        assert image.save(os.path.join(cwd, output_name), "PNG")
        return 0, "", ""

    monkeypatch.setattr(login_dialog, "_lark_cli", fake_lark_cli)

    login_dialog.LoginDialog._generate_qrcode(fake, "https://example.com/login")

    assert state["output_name"] == "qr.png"
    assert not os.path.exists(state["cwd"])
    assert not fake.qr_label.pixmap().isNull()
    assert fake.qr_label.pixmap().width() == 224
    assert fake.qr_label.pixmap().height() == 224
    app.processEvents()
