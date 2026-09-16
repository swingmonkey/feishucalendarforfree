"""Dialog for adding a new calendar event (async version).

功能：
- 标题 / 起止时间 / 重复规则（RFC5545 rrule 透传 lark-cli）/ 地点 / 描述
- 本地颜色标记（按 event id 存入 config.event_colors）

v2.1：校验与创建错误改为对话框内联红字提示，不再弹 QMessageBox。
"""

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from config import Config
from models_event import PALETTE, set_event_color

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
            border = "#FFFFFF" if self._selected else "rgba(115,115,115,0.35)"
            ring = "box-shadow: none;"
        else:
            bg = "transparent"
            border = "#FFFFFF" if self._selected else "rgba(115,115,115,0.45)"
            ring = ""
        width = 3 if self._selected else 1
        self.setStyleSheet(
            f"border-radius: 11px; background-color: {bg};"
            f"border: {width}px solid {border}; {ring}"
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
        self._config = config or Config()
        self._default_date = default_date
        self._chosen_color = ""  # "" means no color
        self._creating = False
        self.setWindowTitle("添加飞书日程")
        self.setFixedSize(420, 560)
        self._setup_ui()

        self.lark_cli.event_created.connect(self._on_created)
        self.lark_cli.create_error.connect(self._on_create_error)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)

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

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("地点（可选）")
        form.addRow("地点  ", self.location_input)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("日程描述（支持 Markdown，可用 - [ ] 添加子任务）")
        self.desc_input.setMaximumHeight(80)
        form.addRow("描述  ", self.desc_input)

        layout.addLayout(form)

        # Color picker（仅本地显示）
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
        color_wrap = QHBoxLayout()
        color_wrap.addWidget(color_label)
        color_wrap.addLayout(color_row, 1)
        layout.addLayout(color_wrap)

        self.form_message = QLabel("")
        self.form_message.setObjectName("formError")
        self.form_message.setWordWrap(True)
        self.form_message.setVisible(False)
        layout.addWidget(self.form_message)

        layout.addStretch()

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.create_btn = QPushButton("创建日程")
        self.create_btn.setObjectName("primaryBtn")
        self.create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self.create_btn)

        layout.addLayout(btn_row)

    def _on_color_chosen(self, hex_value: str):
        self._chosen_color = hex_value
        for sw in self._swatches:
            sw.set_selected(sw._hex == hex_value)

    def _on_start_changed(self):
        start = self.start_input.dateTime().toPython()
        new_end = start + timedelta(hours=1)
        self.end_input.setDateTime(new_end)

    def _show_message(self, text: str):
        self.form_message.setText(text)
        self.form_message.setVisible(True)

    def _on_create(self):
        if self._creating:
            return
        summary = self.summary_input.text().strip()
        if not summary:
            self._show_message("请输入日程标题")
            self.summary_input.setFocus()
            return

        start = self.start_input.dateTime().toPython()
        end = self.end_input.dateTime().toPython()
        if end <= start:
            self._show_message("结束时间必须晚于开始时间")
            return

        description = self.desc_input.toPlainText().strip()
        location = self.location_input.text().strip()
        rrule = RECURRENCE_OPTIONS[self.recurrence_combo.currentIndex()][1]

        self._set_creating(True)
        self.form_message.setVisible(False)
        self.create_btn.setText("创建中…")

        self.lark_cli.create_event(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=location or None,
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
        self._show_message(f"创建失败：{error_msg[:150]}")

    def _set_creating(self, creating: bool):
        self._creating = creating
        for w in self.findChildren(QPushButton):
            w.setEnabled(not creating)
        self.summary_input.setEnabled(not creating)
        self.start_input.setEnabled(not creating)
        self.end_input.setEnabled(not creating)
        self.location_input.setEnabled(not creating)
        self.desc_input.setEnabled(not creating)
        self.recurrence_combo.setEnabled(not creating)
