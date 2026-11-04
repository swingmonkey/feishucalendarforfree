"""Offline regressions for the in-app QR login flow."""

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

import login_dialog
import qrgen

_LOGIN_URL = "https://accounts.feishu.cn/oauth/v1/device/verify?user_code=ABCD-EFGH"


def test_qrcode_is_drawn_locally_without_shelling_out(monkeypatch):
    """二维码必须自己画，不能再借 ``lark-cli auth qrcode``。

    原来的实现调的是 ``auth qrcode <url> --output qr.png --size 256``，
    而 lark-cli 根本没有 ``--size`` 这个参数：命令每次都以非零码退出，
    界面永远停在「二维码不可用」，登录等于彻底卡死。这条用例钉住
    「一个子进程都不起，也要有能扫的图」。
    """
    app = QApplication.instance() or QApplication([])
    fake = SimpleNamespace(qr_label=QLabel())
    calls = []

    def fake_lark_cli(args, timeout=60, cwd=None):
        calls.append(args)
        return 1, "", "unknown flag: --size"

    monkeypatch.setattr(login_dialog, "_lark_cli", fake_lark_cli)

    login_dialog.LoginDialog._generate_qrcode(fake, _LOGIN_URL)

    assert calls == [], "生成二维码不该再依赖 lark-cli"

    pixmap = fake.qr_label.pixmap()
    assert not pixmap.isNull()
    # 整数倍缩放：边长是「模块数 + 8 个静区模块」的整数倍，所以要求正方形、够大
    assert pixmap.width() == pixmap.height()
    assert pixmap.width() >= 150
    app.processEvents()


def test_qrcode_image_actually_decodes_to_the_login_url():
    """画出来的图能不能扫，是这个功能唯一的验收标准。"""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    image = login_dialog._qr_pixmap(qrgen.make_qr(_LOGIN_URL)).toImage()
    image = image.convertToFormat(image.Format.Format_RGB32)
    buffer = np.frombuffer(bytes(image.constBits()), dtype=np.uint8)
    frame = buffer.reshape(image.height(), image.bytesPerLine())[:, : image.width() * 4]
    frame = frame.reshape(image.height(), image.width(), 4)

    text, _points, _straight = cv2.QRCodeDetector().detectAndDecode(frame)
    assert text == _LOGIN_URL


def test_qrcode_failure_falls_back_to_text(monkeypatch):
    """编码失败时给一句人话，别让整个登录框跟着崩。"""
    fake = SimpleNamespace(qr_label=QLabel())

    def boom(_url):
        raise ValueError("数据太长")

    monkeypatch.setattr(login_dialog.qrgen, "make_qr", boom)

    login_dialog.LoginDialog._generate_qrcode(fake, "https://example.com")

    assert "失败" in fake.qr_label.text()
    assert "example.com" not in fake.qr_label.text()
