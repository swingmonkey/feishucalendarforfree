"""共享 UI 组件：Toast 轻提示与确认对话框。

设计目标：用不打断操作的轻量反馈替代散落各处的 QMessageBox 弹窗。
- ``Toast``：主窗口底部居中的玻璃胶囊提示，自动消失，可带一个操作按钮。
- ``ConfirmDialog``：模态确认框（危险操作走 dangerBtn，颜色由主题令牌给）。

这里只放字形、文案和布局；一切颜色都交给 styles 的外观层。以前这两个组件
把飞书四色写死在内联样式里，内联优先级最高，换主题换不动它。
"""

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# kind -> 图标字形。颜色不在这里：样式表按 objectName（toastIconSuccess 等）
# 给，切主题才会跟着变。
_TOAST_GLYPH = {
    "info": "●",
    "success": "✓",
    "warning": "!",
    "error": "✕",
}


def _icon_object_name(kind: str) -> str:
    normalized = kind if kind in _TOAST_GLYPH else "info"
    return "toastIcon" + normalized.title()


# 提示文字的三种语义色，同样交给样式表按 objectName 给
_MESSAGE_NAMES = {"error": "formError", "warn": "formWarn", "success": "formSuccess"}


def repolish(widget) -> None:
    """objectName 改了要让 Qt 重新匹配选择器，否则还是按旧名字渲染。"""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)


def set_message_kind(label: QLabel, kind: str = "error") -> None:
    """给一行提示文字换语义色（error / warn / success）。

    以前各处直接 ``label.setStyleSheet("color: #F54A45")``：内联样式优先级最高，
    换主题换不动，而且四个对话框各写各的红。
    """
    name = _MESSAGE_NAMES.get(kind, _MESSAGE_NAMES["error"])
    if label.objectName() != name:
        label.setObjectName(name)
        repolish(label)


# 字段名列宽，和设置窗骨架的 CAP_W 同值：两个窗口并排看时左列要对得上
FIELD_CAP_W = 76


def field_caption(text: str) -> QLabel:
    """表单左侧字段名：定宽 + 次要色，与设置窗同一套骨架。

    以前这里写的是 ``form.addRow("标题  ", ...)``——裸字符串拿不到样式表
    （QFormLayout 生成的 QLabel 没有 objectName），右对齐只能靠尾随空格凑，
    字号也比设置窗的字段名亮一档。
    """
    label = QLabel(text)
    label.setObjectName("fieldCap")
    label.setFixedWidth(FIELD_CAP_W)
    return label


class Toast(QFrame):
    """主窗口底部居中的轻提示。

    用法::

        self.toast.show_message("已保存", kind="success")
        self.toast.show_message("发现新版本", action_text="查看", on_action=...)
    """

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setVisible(False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(8)

        self.icon_label = QLabel("")
        self.icon_label.setObjectName("toastIcon")
        self.icon_label.setFixedWidth(16)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label)

        self.msg_label = QLabel("")
        self.msg_label.setObjectName("toastMsg")
        self.msg_label.setWordWrap(False)
        layout.addWidget(self.msg_label, 1)

        self.action_btn = QPushButton("")
        self.action_btn.setObjectName("toastAction")
        self.action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.action_btn.setVisible(False)
        self.action_btn.clicked.connect(self._handle_action)
        layout.addWidget(self.action_btn)

        self._on_action = None

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("toastClose")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        layout.addWidget(self.close_btn)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        # 父窗口尺寸变化时重新定位
        parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.parent() and event.type() == QEvent.Type.Resize:
            if self.isVisible():
                self._reposition()
        return super().eventFilter(obj, event)

    def _reposition(self):
        parent = self.parentWidget()
        if parent is None:
            return
        self.adjustSize()
        # 限制最大宽度不超过父窗口
        max_w = parent.width() - 48
        if self.width() > max_w:
            self.setFixedWidth(max_w)
            self.adjustSize()
        x = (parent.width() - self.width()) // 2
        y = parent.height() - self.height() - 34
        self.move(max(12, x), max(12, y))

    def _handle_action(self):
        callback = self._on_action
        self.hide()
        if callback is not None:
            callback()

    def show_message(
        self,
        message: str,
        kind: str = "info",
        action_text: str = None,
        on_action=None,
        duration: int = 3200,
    ):
        self.icon_label.setText(_TOAST_GLYPH.get(kind, _TOAST_GLYPH["info"]))
        icon_name = _icon_object_name(kind)
        if self.icon_label.objectName() != icon_name:
            self.icon_label.setObjectName(icon_name)
            repolish(self.icon_label)
        self.msg_label.setText(message)

        if action_text and on_action is not None:
            self.action_btn.setText(action_text)
            self._on_action = on_action
            self.action_btn.setVisible(True)
        else:
            self._on_action = None
            self.action_btn.setVisible(False)

        self.adjustSize()
        self._reposition()
        self.raise_()
        self.show()
        if duration and duration > 0:
            self._timer.start(duration)


class ConfirmDialog(QDialog):
    """确认对话框。

    静态方法 :meth:`ask` 返回 True/False；危险操作（如删除）传 danger=True，
    确认按钮改用 dangerBtn（语义色由主题令牌给）。
    """

    def __init__(
        self,
        title: str,
        message: str,
        ok_text: str = "确定",
        cancel_text: str = "取消",
        danger: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedWidth(400)
        self._setup_ui(title, message, ok_text, cancel_text, danger)

    def _setup_ui(self, title, message, ok_text, cancel_text, danger):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(10)

        icon_lbl = QLabel("!" if danger else "i")
        icon_lbl.setObjectName("confirmIconDanger" if danger else "confirmIcon")
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(icon_lbl)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("confirmTitle")
        header.addWidget(title_lbl, 1)
        layout.addLayout(header)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("confirmMessage")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        separator = QFrame()
        separator.setObjectName("dialogSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(separator)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addStretch()

        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        ok_btn = QPushButton(ok_text)
        ok_btn.setObjectName("dangerBtn" if danger else "primaryBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        ok_btn.clicked.connect(self.accept)
        row.addWidget(ok_btn)

        layout.addLayout(row)

    @staticmethod
    def ask(
        parent,
        title: str,
        message: str,
        ok_text: str = "确定",
        danger: bool = False,
        cancel_text: str = "取消",
    ) -> bool:
        dlg = ConfirmDialog(title, message, ok_text, cancel_text, danger, parent)
        return dlg.exec() == QDialog.DialogCode.Accepted
