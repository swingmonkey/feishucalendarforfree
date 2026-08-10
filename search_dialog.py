"""Search dialog — keyword search across a wide date range.

Extracted from the old ``calendar_widget.py``.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PySide6.QtCore import Qt, Signal

from models_event import parse_event_time, is_all_day_event


class SearchDialog(QDialog):
    """Search dialog for finding events by keyword across a wide date range."""

    event_selected = Signal(dict)  # emits the selected event

    def __init__(self, lark_cli, parent=None):
        super().__init__(parent)
        self._lark_cli = lark_cli
        self._all_events: list = []
        self.setWindowTitle("搜索日程")
        self.setFixedSize(420, 520)
        self._setup_ui()

        self._lark_cli.search_fetched.connect(self._on_search_fetched)
        self._lark_cli.fetch_error.connect(self._on_fetch_error)

        self._start_search()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        title = QLabel("搜索日程")
        title.setObjectName("detailTitle")
        layout.addWidget(title)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("正在加载日程数据...")
        self.search_input.setObjectName("searchInput")
        self.search_input.setReadOnly(True)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        self.result_label = QLabel("正在加载日程...")
        self.result_label.setObjectName("detailLabel")
        layout.addWidget(self.result_label)

        self.result_list = QListWidget()
        self.result_list.setObjectName("searchResultList")
        self.result_list.itemDoubleClicked.connect(self._on_item_activated)
        self.result_list.itemClicked.connect(self._on_item_activated)
        layout.addWidget(self.result_list, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _start_search(self):
        self._lark_cli.search_events(months_back=12, months_forward=3)

    def _on_search_fetched(self, events: list):
        self._all_events = events
        self.search_input.setReadOnly(False)
        self.search_input.setPlaceholderText("输入关键词搜索日程标题、描述或发起人...")
        self.search_input.setFocus()
        if events:
            self.result_label.setText(f"已加载 {len(events)} 条日程，请输入关键词搜索")
        else:
            self.result_label.setText("未找到任何日程")

    def _on_fetch_error(self, error_msg: str):
        self.result_label.setText(f"加载失败: {error_msg}")
        self.search_input.setPlaceholderText("加载失败")

    def _on_search(self, text: str):
        text = text.strip().lower()
        self.result_list.clear()

        if not text:
            self.result_label.setText(f"已加载 {len(self._all_events)} 条日程，请输入关键词搜索")
            return

        matches = []
        for ev in self._all_events:
            summary = str(ev.get("summary", "")).lower()
            description = str(ev.get("description", "")).lower()
            organizer = ""
            org_data = ev.get("event_organizer", {})
            if isinstance(org_data, dict):
                organizer = str(org_data.get("display_name", "")).lower()

            if text in summary or text in description or text in organizer:
                matches.append(ev)

        self.result_label.setText(f"共 {len(matches)} 条结果")

        for ev in matches:
            start = parse_event_time(ev.get("start_time", {}))
            summary = ev.get("summary", "(无标题)")
            all_day = is_all_day_event(ev)
            if all_day:
                time_str = start.strftime("%m-%d 全天")
            else:
                time_str = start.strftime("%m-%d %H:%M")
            display = f"{time_str}  {summary}"

            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, ev)
            self.result_list.addItem(item)

    def _on_item_activated(self, item: QListWidgetItem):
        ev = item.data(Qt.ItemDataRole.UserRole)
        if ev:
            self.event_selected.emit(ev)
            self.accept()

    def closeEvent(self, ev):
        try:
            self._lark_cli.search_fetched.disconnect(self._on_search_fetched)
            self._lark_cli.fetch_error.disconnect(self._on_fetch_error)
        except RuntimeError:
            pass
        super().closeEvent(ev)
