"""Day detail dialog — lists all events for a single day.

Extracted from the old ``calendar_widget.py`` so the calendar views stay small
and focused (weektodo-style component separation).
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFrame,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal

from models_event import parse_event_time, is_all_day_event
from event_card import EventCard
from add_event_dialog import AddEventDialog
from event_detail_dialog import EventDetailDialog
from config import Config

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]


class DayDetailDialog(QDialog):
    """Dialog showing all events for a specific day."""

    event_delete_requested = Signal(dict)

    def __init__(self, date: datetime, events: list, lark_cli_async=None, parent=None, config: Config = None):
        super().__init__(parent)
        self.cell_date = date
        self._events = events
        self._lark_cli = lark_cli_async
        self._config = config
        self.setWindowTitle("当日日程")
        self.setFixedSize(360, 480)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        wd = WEEKDAY_NAMES[self.cell_date.weekday()]
        date_str = self.cell_date.strftime("%Y年%m月%d日")
        is_today = self.cell_date.date() == datetime.now().date()

        title_text = f"{date_str}  周{wd}"
        if is_today:
            title_text = f"● 今天  {date_str}  周{wd}"

        title = QLabel(title_text)
        title.setObjectName("detailTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        count_lbl = QLabel(f"共 {len(self._events)} 项日程")
        count_lbl.setObjectName("detailLabel")
        layout.addWidget(count_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(115, 115, 115, 0.18); background-color: rgba(115, 115, 115, 0.18); max-height: 1px;")
        layout.addWidget(sep)

        if not self._events:
            empty = QLabel("当天没有日程安排")
            empty.setObjectName("emptyLabel")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(empty)
        else:
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            container = QWidget()
            vlay = QVBoxLayout(container)
            vlay.setContentsMargins(0, 0, 0, 0)
            vlay.setSpacing(6)

            for ev in self._events:
                card = EventCard(ev)
                card.clicked.connect(self._show_event_detail)
                card.delete_clicked.connect(self._on_card_delete)
                vlay.addWidget(card)

            vlay.addStretch()
            scroll.setWidget(container)
            layout.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if self._lark_cli:
            add_btn = QPushButton("添加日程")
            add_btn.setObjectName("primaryBtn")
            add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            add_btn.clicked.connect(self._on_add_event)
            btn_row.addWidget(add_btn)

        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_add_event(self):
        dialog = AddEventDialog(self._lark_cli, self, default_date=self.cell_date, config=self._config)
        dialog.event_created.connect(lambda: self.accept())
        dialog.exec()

    def _show_event_detail(self, event: dict):
        dialog = EventDetailDialog(event, self._lark_cli, self)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.event_updated.connect(lambda _: self.accept())
        dialog.exec()

    def _on_card_delete(self, event: dict):
        self.event_delete_requested.emit(event)
        self.accept()
