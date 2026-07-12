"""Dialog for viewing calendar event details."""

from datetime import datetime
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFrame,
)
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from event_card import parse_event_time, is_all_day_event


class EventDetailDialog(QDialog):
    """Dialog showing full details of a calendar event."""

    event_delete_requested = Signal(dict)

    def __init__(self, event: dict, parent=None):
        super().__init__(parent)
        # Use 'event_data' not 'event' — 'event' shadows QObject.event()
        self.event_data = event
        self.setWindowTitle("日程详情")
        self.setFixedSize(420, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
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
            time_str = f"{start.strftime('%Y-%m-%d %H:%M')} - {end.strftime('%H:%M')}"
            if start.strftime("%Y-%m-%d") != end.strftime("%Y-%m-%d"):
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

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("detailLabel")
        return lbl

    def _value(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("detailValue")
        lbl.setWordWrap(True)
        return lbl

    def _on_delete(self):
        """Emit delete signal and close dialog."""
        self.event_delete_requested.emit(self.event_data)
        self.accept()
