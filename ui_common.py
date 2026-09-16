"""共享 UI 组件：Toast 轻提示与飞书风格确认对话框。

设计目标：用不打断操作的轻量反馈替代散落各处的 QMessageBox 弹窗。
- ``Toast``：主窗口底部居中的深色胶囊提示，自动消失，可带一个操作按钮。
- ``ConfirmDialog``：飞书风格的模态确认框（危险操作为红色主按钮）。
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

# kind -> (图标, 图标颜色)
_TOAST_STYLE = {
    "info": ("●", "#3370FF"),
    "success": ("✓", "#34C724"),
    "warning": ("!", "#FF8800"),
    "error": ("✕", "#F54A45"),
}


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
        glyph, color = _TOAST_STYLE.get(kind, _TOAST_STYLE["info"])
        self.icon_label.setText(glyph)
        self.icon_label.setStyleSheet(f"color: {color}; font-weight: 700;")
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
    """飞书风格确认对话框。

    静态方法 :meth:`ask` 返回 True/False；危险操作（如删除）传 danger=True，
    确认按钮变为品牌红。
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
        self.setFixedWidth(380)
        self._setup_ui(title, message, ok_text, cancel_text, danger)

    def _setup_ui(self, title, message, ok_text, cancel_text, danger):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(10)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("detailTitle")
        title_lbl.setStyleSheet("font-size: 15px;")
        layout.addWidget(title_lbl)

        msg_lbl = QLabel(message)
        msg_lbl.setObjectName("detailLabel")
        msg_lbl.setStyleSheet("font-size: 13px; color: #646A73;")
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl)

        layout.addSpacing(6)

        row = QHBoxLayout()
        row.addStretch()

        cancel_btn = QPushButton(cancel_text)
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        row.addWidget(cancel_btn)

        ok_btn = QPushButton(ok_text)
        ok_btn.setObjectName("dangerBtn" if danger else "primaryBtn")
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
