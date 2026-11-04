"""次级表面的配色来源守卫。

设计语言改造（v2.9.0 起）把颜色收进 theme.py 令牌、由 styles.py 外观层拼成
QSS。剩下的风险不是「现在不好看」，而是以后有人图省事在组件里再写一行
`setStyleSheet("color: #F54A45")`——内联样式优先级最高，换主题时那一行会
原地留在旧配色里。这组测试钉的就是这件事：共享组件不许带色值，语义色必须
能从生成的样式表里查到。
"""

import ast
import os
import re

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QLabel

import styles
import theme
import ui_common

_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")

# 这些组件是「所有界面共用」的那一层，一旦带死色值就会到处漏
_SHARED_MODULES = ("ui_common.py", "today_bar.py")


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _literal_colors(path):
    """文件里真正会执行的代码中带十六进制色值的字符串。

    色值只可能出现在字符串里，所以不能简单排除字符串；但要豁免 docstring
    （这里几处 docstring 为了讲历史特意写了旧色值）。
    """
    tree = ast.parse(open(path, encoding="utf-8").read())
    doc_ids = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", None)
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                doc_ids.add(id(body[0].value))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in doc_ids:
                continue
            found += _HEX.findall(node.value)
    return found


def test_shared_components_carry_no_literal_colors():
    """共享组件里不许出现十六进制色值（颜色只能来自令牌或样式表）。"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in _SHARED_MODULES:
        offenders = _literal_colors(os.path.join(root, name))
        assert not offenders, f"{name} 又写死了色值: {offenders}"


def test_toast_icon_switches_object_name_inst_of_inline_color(qapp):
    from PySide6.QtWidgets import QWidget

    parent = QWidget()
    toast = ui_common.Toast(parent)

    for kind, expected in (
        ("success", "toastIconSuccess"),
        ("warning", "toastIconWarning"),
        ("error", "toastIconError"),
        ("info", "toastIconInfo"),
    ):
        toast.show_message("测试", kind=kind, duration=0)
        assert toast.icon_label.objectName() == expected
        # 关键：颜色不在内联样式里，才能跟着主题走
        assert toast.icon_label.styleSheet() == ""

    # 未知 kind 退回 info，而不是抛异常把提示吞掉
    toast.show_message("测试", kind="nonsense", duration=0)
    assert toast.icon_label.objectName() == "toastIconInfo"


def test_set_message_kind_maps_semantic_names(qapp):
    label = QLabel("提示")
    ui_common.set_message_kind(label, "warn")
    assert label.objectName() == "formWarn"
    assert label.styleSheet() == ""

    ui_common.set_message_kind(label, "success")
    assert label.objectName() == "formSuccess"

    # 脏值退回 error：提示文字宁可显红也不能没颜色
    ui_common.set_message_kind(label, "whatever")
    assert label.objectName() == "formError"


@pytest.mark.parametrize("name", ["dark", "light"])
def test_skin_layer_defines_the_secondary_surfaces(name):
    """外观层必须给全这些选择器，否则它们会退回基础层的飞书旧配色。"""
    skin = styles._skin_rules(name)
    t = theme.tokens(name)
    for selector in (
        "QLabel#toastIconSuccess",
        "QLabel#toastIconWarning",
        "QLabel#toastIconError",
        "QLabel#formWarn",
        "QLabel#formSuccess",
        "QLabel#confirmIconDanger",
        "QPushButton#colorSwatchSelected",
        "QLabel#qrPlaceholder",
        "QLabel#loginTitle",
    ):
        assert selector in skin, f"{name} 外观层缺少 {selector}"

    # 语义色取自令牌，不是抄一份新的
    assert t["danger"] in skin
    assert t["warn_text"] in skin
    assert t["qr_ink"] in skin


def test_confirm_icon_overrides_the_base_feishu_blue():
    """基础层里确认框图标还是 #3370FF；外观层排在后面才压得住。"""
    base = styles._menu_dialog_rules("dark")
    # 外观层的注释会提到旧色值讲原因，只查真正生效的声明
    skin = re.sub(r"/\*.*?\*/", "", styles._skin_rules("dark"), flags=re.S)
    assert "#3370FF" in base
    assert "QLabel#confirmIcon" in skin
    assert "#3370FF" not in skin


@pytest.mark.parametrize(
    "selector",
    [
        "QPushButton#dangerBtn",
        "QPushButton#closeBtn:hover, QToolButton#closeBtn:hover",
        "QFrame#dayCellToday",
        "QFrame#eventCardCurrent",
        "QFrame#gridEventMultiDay",
        "QFrame#weekDayColDrop",
    ],
)
def test_semantic_surfaces_actually_change_with_theme(selector):
    """这些规则以前把深色主题的 rgba 直接抄进外观层，浅色主题拿到同一串。

    断言「两套主题拼出来的声明不同」比断言具体色值有用：它不锁死配色，
    只锁死「换肤必须真的换肤」。
    """
    def rule(name):
        # _skin_rules 返回的是已格式化的 QSS（单花括号），选择器列表还会换行
        text = re.sub(r"\s+", " ", styles._skin_rules(name))
        m = re.search(re.escape(selector) + r" \{[^}]*\}", text)
        assert m, f"{name} 外观层找不到 {selector}"
        return m.group(0)

    assert rule("dark") != rule("light")
    # 而且两串里都不许出现另一套主题的 danger/success RGB
    assert "239,68,68" not in rule("light")
    assert "52,211,153" not in rule("light")


# ── 顶栏 / 标签栏对比度守卫（v2.11.2）───────────────────────────────────────
# 用户报告：深色下顶栏文字与背景太相似；浅色下薄荷绿淡染选中段几乎看不见。
# 修复用 muted_strong（比 muted 高一档的次级文字）+ 实底 accent 选中段。


def _srgb_channel(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r, g, b = (int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * _srgb_channel(r) + 0.7152 * _srgb_channel(g) + 0.0722 * _srgb_channel(b)


def _contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def test_muted_strong_is_readable_on_both_themes():
    for name in ("dark", "light"):
        t = theme.tokens(name)
        assert "muted_strong" in t, f"{name} 缺 muted_strong 令牌"
        assert _contrast(t["muted_strong"], t["bg"]) >= 4.5


def test_muted_strong_is_stronger_than_muted():
    for name in ("dark", "light"):
        t = theme.tokens(name)
        bg = t["bg"]
        assert _contrast(t["muted_strong"], bg) > _contrast(t["muted"], bg)


def test_selected_segment_uses_solid_accent():
    # 选中段从「accent 淡染 + accent 文字」改为实底 accent + accent_ink：
    # 浅色下淡染薄荷绿在白底上几乎不可见
    for name in ("dark", "light"):
        t = theme.tokens(name)
        rule = styles._skin_rules(name)
        idx = rule.find("QPushButton#toggleBtnActive")
        assert idx >= 0
        block = rule[idx:idx + 400]
        assert f"color: {t['accent_ink']}" in block
        assert f"background-color: {t['accent']}" in block


def test_top_bar_secondary_text_uses_muted_strong():
    for name in ("dark", "light"):
        t = theme.tokens(name)
        rule = styles._skin_rules(name)
        # 分段控件未选中段 / 图标按钮 / 日期标题
        for anchor in ("QPushButton#toggleBtn {", "QPushButton#iconBtn, QToolButton#iconBtn"):
            idx = rule.find(anchor)
            assert idx >= 0
            assert t["muted_strong"] in rule[idx:idx + 400]


def test_dialog_tab_bar_uses_muted_strong():
    for name in ("dark", "light"):
        t = theme.tokens(name)
        rule = styles._skin_rules(name)
        idx = rule.find("QDialog QTabBar::tab {")
        assert idx >= 0
        assert t["muted_strong"] in rule[idx:idx + 300]


def test_light_muted_meets_body_text_contrast():
    """浅色 muted 用在 detailLabel / stateMessage 等 10–12px 正文上。

    原值 #66707c 对 bg 只有约 4.21:1，达不到正文 4.5:1 的门槛。
    """
    t = theme.tokens("light")
    assert _contrast(t["muted"], t["bg"]) >= 4.5
