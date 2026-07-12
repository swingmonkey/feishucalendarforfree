"""Dialog for adding a new calendar event (async version)."""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QPushButton,
    QHBoxLayout,
    QLabel,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal


class AddEventDialog(QDialog):
    """Dialog for creating a new Feishu calendar event."""

    event_created = Signal(dict)

    def __init__(self, lark_cli_async, parent=None):
        super().__init__(parent)
        self.lark_cli = lark_cli_async
        self.setWindowTitle("添加飞书日程")
        self.setFixedSize(400, 420)
        self._setup_ui()

        # Connect async signals
        self.lark_cli.event_created.connect(self._on_created)
        self.lark_cli.create_error.connect(self._on_create_error)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("新建日程")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.summary_input = QLineEdit()
        self.summary_input.setPlaceholderText("请输入日程标题")
        form.addRow("标题  ", self.summary_input)

        self.start_input = QDateTimeEdit()
        self.start_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_input.setCalendarPopup(True)
        self.start_input.setDateTime(datetime.now())
        # When start time changes, auto-set end time to start + 1 minute
        self.start_input.dateTimeChanged.connect(self._on_start_changed)
        form.addRow("开始  ", self.start_input)

        self.end_input = QDateTimeEdit()
        self.end_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_input.setCalendarPopup(True)
        self.end_input.setDateTime(datetime.now() + timedelta(minutes=1))
        form.addRow("结束  ", self.end_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("日程描述（可选）")
        self.desc_input.setMaximumHeight(80)
        form.addRow("描述  ", self.desc_input)

        layout.addLayout(form)
        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.create_btn = QPushButton("创建日程")
        self.create_btn.setObjectName("primaryBtn")
        self.create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self.create_btn)

        layout.addLayout(btn_row)

    def _on_start_changed(self):
        """When start time changes, auto-set end time to start + 1 minute."""
        start = self.start_input.dateTime().toPython()
        new_end = start + timedelta(minutes=1)
        self.end_input.setDateTime(new_end)

    def _on_create(self):
        summary = self.summary_input.text().strip()
        if not summary:
            QMessageBox.warning(self, "提示", "请输入日程标题")
            return

        start = self.start_input.dateTime().toPython()
        end = self.end_input.dateTime().toPython()

        if end <= start:
            QMessageBox.warning(self, "提示", "结束时间必须晚于开始时间")
            return

        description = self.desc_input.toPlainText().strip()

        # Disable UI and show creating state
        self._set_creating(True)
        self.create_btn.setText("创建中...")

        # Call async create
        self.lark_cli.create_event(
            summary=summary,
            start=start,
            end=end,
            description=description,
        )

    def _on_created(self, data: dict):
        """Handle successful creation."""
        self.event_created.emit(data)
        self.accept()

    def _on_create_error(self, error_msg: str):
        """Handle creation error."""
        self._set_creating(False)
        self.create_btn.setText("创建日程")
        QMessageBox.critical(self, "创建失败", error_msg)

    def _set_creating(self, creating: bool):
        for w in self.findChildren(QPushButton):
            w.setEnabled(not creating)
        self.summary_input.setEnabled(not creating)
        self.start_input.setEnabled(not creating)
        self.end_input.setEnabled(not creating)
        self.desc_input.setEnabled(not creating)
