"""Dialog for viewing and editing calendar event details."""

from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFrame,
    QLineEdit,
    QTextEdit,
    QDateTimeEdit,
    QMessageBox,
    QStackedWidget,
    QWidget,
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from event_card import parse_event_time, is_all_day_event


class EventDetailDialog(QDialog):
    """Dialog showing full details of a calendar event, with edit mode."""

    event_delete_requested = Signal(dict)
    event_updated = Signal(dict)

    def __init__(self, event: dict, lark_cli_async=None, parent=None):
        super().__init__(parent)
        # Use 'event_data' not 'event' — 'event' shadows QObject.event()
        self.event_data = event
        self.lark_cli = lark_cli_async
        self._edit_mode = False
        self.setWindowTitle("日程详情")
        self.setMinimumSize(420, 480)
        self.resize(440, 520)
        self._setup_ui()

        # Connect async update signals if API client is available
        if self.lark_cli:
            self.lark_cli.event_updated.connect(self._on_updated)
            self.lark_cli.update_error.connect(self._on_update_error)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Stacked widget for view/edit modes
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_view_mode())  # index 0
        self.stack.addWidget(self._build_edit_mode())  # index 1
        layout.addWidget(self.stack, 1)

    # ─── View Mode ───

    def _build_view_mode(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Title
        summary = self.event_data.get("summary", "(无标题)")
        title = QLabel(str(summary))
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(115, 115, 115, 0.18); background-color: rgba(115, 115, 115, 0.18); max-height: 1px;")
        layout.addWidget(sep)

        # Details form
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)

        start = parse_event_time(self.event_data.get("start_time", {}))
        end = parse_event_time(self.event_data.get("end_time", {}))
        all_day = is_all_day_event(self.event_data)

        # Time
        if all_day:
            time_str = f"{start.strftime('%Y-%m-%d')} 全天"
            if start.strftime("%Y-%m-%d") != end.strftime("%Y-%m-%d"):
                time_str = f"{start.strftime('%Y-%m-%d')} - {end.strftime('%Y-%m-%d')} 全天"
        else:
            if start.strftime("%Y-%m-%d") == end.strftime("%Y-%m-%d"):
                time_str = f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}"
            else:
                time_str = f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%Y-%m-%d %H:%M')}"
        form.addRow(self._label("时间"), self._value(time_str))

        # Duration
        if not all_day:
            duration = end - start
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            dur_str = ""
            if hours > 0:
                dur_str += f"{hours}小时"
            if minutes > 0:
                dur_str += f"{minutes}分钟"
            if dur_str:
                form.addRow(self._label("时长"), self._value(dur_str))

        # Organizer
        organizer = self.event_data.get("event_organizer", {})
        if isinstance(organizer, dict) and organizer.get("display_name"):
            form.addRow(self._label("组织者"), self._value(str(organizer["display_name"])))

        # RSVP status
        rsvp = self.event_data.get("self_rsvp_status", "")
        rsvp_map = {"accept": "已接受", "decline": "已拒绝", "tentative": "待定", "needs_action": "未回复"}
        rsvp_text = rsvp_map.get(rsvp, rsvp)
        if rsvp_text:
            form.addRow(self._label("参会状态"), self._value(rsvp_text))

        # Free/busy
        fb = self.event_data.get("free_busy_status", "")
        fb_map = {"busy": "忙碌", "free": "空闲"}
        fb_text = fb_map.get(fb, fb)
        if fb_text:
            form.addRow(self._label("状态"), self._value(fb_text))

        # Description
        desc = self.event_data.get("description", "")
        if desc:
            desc_label = QLabel(str(desc))
            desc_label.setObjectName("detailValue")
            desc_label.setWordWrap(True)
            form.addRow(self._label("描述"), desc_label)

        # Visibility
        vis = self.event_data.get("visibility", "")
        vis_map = {"default": "默认", "public": "公开", "private": "私密"}
        vis_text = vis_map.get(vis, vis)
        if vis_text:
            form.addRow(self._label("可见性"), self._value(vis_text))

        layout.addLayout(form)

        # Meeting link
        vchat = self.event_data.get("vchat", {})
        if isinstance(vchat, dict) and vchat.get("meeting_url"):
            meeting_btn = QPushButton("加入视频会议")
            meeting_btn.setObjectName("primaryBtn")
            meeting_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            meeting_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(vchat["meeting_url"])))
            layout.addWidget(meeting_btn)

        # App link
        app_link = self.event_data.get("app_link", "")
        if app_link:
            open_btn = QPushButton("在飞书中打开")
            open_btn.setObjectName("secondaryBtn")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(app_link)))
            layout.addWidget(open_btn)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        edit_btn = QPushButton("编辑")
        edit_btn.setObjectName("primaryBtn")
        edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        edit_btn.clicked.connect(self._enter_edit_mode)
        btn_row.addWidget(edit_btn)

        delete_btn = QPushButton("删除日程")
        delete_btn.setObjectName("dangerBtn")
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(self._on_delete)
        btn_row.addWidget(delete_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

        return widget

    # ─── Edit Mode ───

    def _build_edit_mode(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("编辑日程")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(115, 115, 115, 0.18); background-color: rgba(115, 115, 115, 0.18); max-height: 1px;")
        layout.addWidget(sep)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Summary
        self.edit_summary = QLineEdit()
        summary = self.event_data.get("summary", "")
        self.edit_summary.setText(str(summary) if summary else "")
        self.edit_summary.setPlaceholderText("请输入日程标题")
        form.addRow("标题  ", self.edit_summary)

        # Start time
        start = parse_event_time(self.event_data.get("start_time", {}))
        self.edit_start = QDateTimeEdit()
        self.edit_start.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.edit_start.setCalendarPopup(True)
        self.edit_start.setDateTime(start)
        form.addRow("开始  ", self.edit_start)

        # End time
        end = parse_event_time(self.event_data.get("end_time", {}))
        self.edit_end = QDateTimeEdit()
        self.edit_end.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.edit_end.setCalendarPopup(True)
        self.edit_end.setDateTime(end)
        form.addRow("结束  ", self.edit_end)

        # Description
        self.edit_desc = QTextEdit()
        desc = self.event_data.get("description", "")
        self.edit_desc.setPlainText(str(desc) if desc else "")
        self.edit_desc.setPlaceholderText("日程描述（可选）")
        self.edit_desc.setMaximumHeight(80)
        form.addRow("描述  ", self.edit_desc)

        layout.addLayout(form)
        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self._exit_edit_mode)
        btn_row.addWidget(cancel_btn)

        self.save_btn = QPushButton("保存修改")
        self.save_btn.setObjectName("primaryBtn")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self.save_btn)

        layout.addLayout(btn_row)
        return widget

    # ─── Mode Switching ───

    def _enter_edit_mode(self):
        self._edit_mode = True
        self.stack.setCurrentIndex(1)

    def _exit_edit_mode(self):
        self._edit_mode = False
        self.stack.setCurrentIndex(0)

    # ─── Save / Update ───

    def _on_save(self):
        summary = self.edit_summary.text().strip()
        if not summary:
            QMessageBox.warning(self, "提示", "请输入日程标题")
            return

        start = self.edit_start.dateTime().toPython()
        end = self.edit_end.dateTime().toPython()

        if end <= start:
            QMessageBox.warning(self, "提示", "结束时间必须晚于开始时间")
            return

        description = self.edit_desc.toPlainText().strip()

        if not self.lark_cli:
            QMessageBox.warning(self, "提示", "无法连接到飞书API")
            return

        # Disable UI and show saving state
        self.save_btn.setText("保存中...")
        self.save_btn.setEnabled(False)
        for w in self.findChildren(QPushButton):
            w.setEnabled(False)

        event_id = self.event_data.get("event_id", "")
        calendar_id = self.event_data.get("organizer_calendar_id", "primary")

        self.lark_cli.update_event(
            calendar_id=calendar_id,
            event_id=event_id,
            summary=summary,
            start=start,
            end=end,
            description=description,
        )

    def _on_updated(self, data: dict):
        """Handle successful update."""
        # Update local event data
        if isinstance(data, dict) and data:
            self.event_data.update(data)
        self.event_updated.emit(self.event_data)
        QMessageBox.information(self, "成功", "日程已更新")
        self.accept()

    def _on_update_error(self, error_msg: str):
        """Handle update error."""
        self.save_btn.setText("保存修改")
        for w in self.findChildren(QPushButton):
            w.setEnabled(True)
        QMessageBox.critical(self, "更新失败", error_msg)

    # ─── Delete ───

    def _on_delete(self):
        """Emit delete signal and close dialog."""
        self.event_delete_requested.emit(self.event_data)
        self.accept()

    # ─── Helpers ───

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("detailLabel")
        return lbl

    def _value(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("detailValue")
        lbl.setWordWrap(True)
        return lbl
