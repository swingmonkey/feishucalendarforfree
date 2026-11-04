"""首页「正在连接飞书」等待动效（ConnectingOrb）的用例。

自绘控件的「好不好看」没法断言，但有三件事必须钉死，否则它随时会退化：
  · 隐藏时不能空转——这是个常驻桌面的小挂件，面板切走后还在跑 60fps
    重绘就是白烧电；
  · 旋转角度必须真的参与渲染——否则「动效」只是一张静态图，动画在跑
    而画面不动，用户看到的还是「卡住了」；
  · 换肤要跟着换——深色台面上用浅色配色会糊成一团。

渲染断言走 ``QWidget.render(QImage)`` 而不是 ``grab()``：先铺一层黑底，
再数「比黑底亮」的像素，跟窗口背景、主题、DPR 都无关。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest

import widgets


def _render(orb: widgets.ConnectingOrb) -> QImage:
    img = QImage(orb.size(), QImage.Format.Format_ARGB32)
    img.fill(QColor("#000000"))
    orb.render(img)
    return img


def _lit_pixels(img: QImage, threshold: int = 24) -> int:
    """数出「明显比纯黑亮」的像素，用来判断这块地方确实画了东西。"""
    count = 0
    for y in range(img.height()):
        for x in range(img.width()):
            if QColor(img.pixel(x, y)).lightness() > threshold:
                count += 1
    return count


def _raw(img: QImage) -> bytes:
    return bytes(img.constBits())


@pytest.fixture
def orb():
    widget = widgets.ConnectingOrb()
    yield widget
    widget.stop()
    widget.deleteLater()


def test_orb_is_square(orb):
    """光弧是正圆，控件被压扁就会变成椭圆——布局里必须锁成正方形。"""
    assert orb.width() == orb.height() == widgets.ConnectingOrb.SIDE


def test_orb_paints_a_ring(orb):
    lit = _lit_pixels(_render(orb))
    # 78×78 的画布上，一圈直径 54 的圆弧加光晕至少占几百个像素
    assert lit > 400, f"只画出 {lit} 个像素，光弧基本没画出来"


def test_rotation_actually_changes_the_frame(orb):
    """动画在跑但画面不变是最糟的失败模式：看起来和卡死一模一样。"""
    orb.setProperty("spin", 0.0)
    first = _raw(_render(orb))
    orb.setProperty("spin", 180.0)
    rotated = _raw(_render(orb))
    assert first != rotated, "改了旋转角度画面却没变化"


def test_sweep_and_breath_change_the_frame(orb):
    orb.setProperty("sweep", 60.0)
    tight = _raw(_render(orb))
    orb.setProperty("sweep", 150.0)
    wide = _raw(_render(orb))
    assert tight != wide, "光弧张开角度没有参与渲染"

    orb.setProperty("breath", 0.0)
    quiet = _raw(_render(orb))
    orb.setProperty("breath", 1.0)
    bright = _raw(_render(orb))
    assert quiet != bright, "呼吸相位没有参与渲染"


def test_dark_and_light_palettes_differ(orb):
    orb.set_dark(True)
    dark = _raw(_render(orb))
    orb.set_dark(False)
    light = _raw(_render(orb))
    assert dark != light, "换肤后颜色没变，浅色主题下光弧会糊成一片"


def test_spins_only_while_visible(orb):
    """隐藏即停：面板切走后不该继续以 60fps 重绘。"""
    assert not orb.is_spinning(), "构造完就不该开跑，还没人看见它"

    orb.show()
    QTest.qWait(80)
    assert orb.is_spinning(), "显示后动效必须起来"

    orb.hide()
    QTest.qWait(30)
    assert not orb.is_spinning(), "隐藏后动效必须停掉"
