"""Dialog for adding a new calendar event (async version).

Extended in the weektodo-style refactor with:
- a local color picker (stored per event id in ``config.event_colors``)
- a recurrence selector that writes an RFC5545 ``--rrule`` through to lark-cli
"""

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
    QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from models_event import PALETTE, set_event_color
from config import Config

RECURRENCE_OPTIONS = [
    ("不重复", None),
    ("每天", "FREQ=DAILY"),
    ("每工作日", "FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR"),
    ("每周", "FREQ=WEEKLY"),
    ("每两周", "FREQ=WEEKLY;INTERVAL=2"),
    ("每月", "FREQ=MONTHLY"),
]


class ColorSwatch(QPushButton):
    """A small circular color button used in the color picker."""

    selected = Signal(str)  # hex or "" for clear

    def __init__(self, name: str, hex_value: str, parent=None):
        super().__init__(parent)
        self._name = name
        self._hex = hex_value
        self.setFixedSize(22, 22)
        self.setToolTip(name)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._selected = False
        self._render()
        self.clicked.connect(lambda: self.selected.emit(self._hex))

    def _render(self):
        if self._hex:
            bg = self._hex
            border = self._hex if self._selected else "rgba(115,115,115,0.4)"
        else:
            bg = "transparent"
            border = self._hex if self._selected else "rgba(115,115,115,0.4)"
        self.setStyleSheet(
            f"border-radius: 11px; background-color: {bg}; border: 2px solid {border};"
        )

    def set_selected(self, selected: bool):
        self._selected = selected
        self._render()


class AddEventDialog(QDialog):
    """Dialog for creating a new Feishu calendar event."""

    event_created = Signal(dict)

    def __init__(self, lark_cli_async, parent=None, default_date=None, config: Config = None):
        super().__init__(parent)
        self.lark_cli = lark_cli_async
        self._config = config
        self._default_date = default_date
        self._chosen_color = ""  # "" means no color
        self.setWindowTitle("添加飞书日程")
        self.setFixedSize(420, 520)
        self._setup_ui()

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

        if self._default_date:
            base_start = self._default_date.replace(hour=9, minute=0, second=0, microsecond=0)
            base_end = base_start + timedelta(minutes=60)
        else:
            base_start = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            base_end = base_start + timedelta(minutes=60)

        self.start_input = QDateTimeEdit()
        self.start_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.start_input.setCalendarPopup(True)
        self.start_input.setDateTime(base_start)
        self.start_input.dateTimeChanged.connect(self._on_start_changed)
        form.addRow("开始  ", self.start_input)

        self.end_input = QDateTimeEdit()
        self.end_input.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.end_input.setCalendarPopup(True)
        self.end_input.setDateTime(base_end)
        form.addRow("结束  ", self.end_input)

        self.recurrence_combo = QComboBox()
        for label, _ in RECURRENCE_OPTIONS:
            self.recurrence_combo.addItem(label)
        form.addRow("重复  ", self.recurrence_combo)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("日程描述（支持 Markdown，可用 - [ ] 添加子任务）")
        self.desc_input.setMaximumHeight(80)
        form.addRow("描述  ", self.desc_input)

        layout.addLayout(form)

        # Color picker
        color_label = QLabel("颜色")
        color_label.setObjectName("detailLabel")
        color_row = QHBoxLayout()
        color_row.setSpacing(6)
        self._swatches = []
        none_swatch = ColorSwatch("无", "", self)
        none_swatch.set_selected(True)
        none_swatch.selected.connect(self._on_color_chosen)
        color_row.addWidget(none_swatch)
        self._swatches.append(none_swatch)
        for name, hex_value in PALETTE:
            sw = ColorSwatch(name, hex_value, self)
            sw.selected.connect(self._on_color_chosen)
            color_row.addWidget(sw)
            self._swatches.append(sw)
        color_row.addStretch()
        layout.addLayout(color_row)

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

    def _on_color_chosen(self, hex_value: str):
        self._chosen_color = hex_value
        for sw in self._swatches:
            sw.set_selected(sw._hex == hex_value)

    def _on_start_changed(self):
        start = self.start_input.dateTime().toPython()
        # Default duration 1h when start changes.
        new_end = start + timedelta(hours=1)
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
        rrule = RECURRENCE_OPTIONS[self.recurrence_combo.currentIndex()][1]

        self._set_creating(True)
        self.create_btn.setText("创建中...")

        self.lark_cli.create_event(
            summary=summary,
            start=start,
            end=end,
            description=description,
            rrule=rrule,
        )

    def _on_created(self, data: dict):
        # Persist the chosen color locally (keyed by the new event id).
        if self._config and self._chosen_color:
            event_id = data.get("event_id") if isinstance(data, dict) else ""
            if event_id:
                set_event_color(self._config, event_id, self._chosen_color)
        self.event_created.emit(data)
        self.accept()

    def _on_create_error(self, error_msg: str):
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
        self.recurrence_combo.setEnabled(not creating)
