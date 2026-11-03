"""Search dialog — keyword search across a wide date range.

Extracted from the old ``calendar_widget.py``.

Search is local-first: the on-disk event store answers immediately (and
answers at all when the network is down), then the server-side result set is
merged in once ``+search-event`` returns. The two sources are deduped by
``event_id`` with the server copy winning.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

import event_store
from models_event import is_all_day_event, parse_event_time
from utils import event_sort_key, wide_range


class SearchDialog(QDialog):
    """Search dialog for finding events by keyword across a wide date range."""

    event_selected = Signal(dict)  # emits the selected event

    def __init__(self, lark_cli, parent=None, store=None):
        super().__init__(parent)
        self._lark_cli = lark_cli
        self._store = store
        self._all_events: list = []
        # 服务端结果不可用时置 True：结果数后面要标明"本地"，
        # 否则用户会以为搜到的就是全部。
        self._offline = False
        self._signals_detached = False
        self.setWindowTitle("搜索日程")
        self.setFixedSize(420, 520)
        self._setup_ui()

        self._lark_cli.search_fetched.connect(self._on_search_fetched)
        self._lark_cli.fetch_error.connect(self._on_fetch_error)

        self._load_local()
        self._start_search()

    def _load_local(self):
        """Seed the dialog from the local store so search works offline."""
        if self._store is None:
            return
        start, end = wide_range(months_back=12, months_forward=3)
        local = event_store.read_range(self._store, start, end)
        if not local:
            return
        self._merge_events(local)
        self.search_input.setReadOnly(False)
        self.search_input.setPlaceholderText("输入关键词搜索日程标题、描述或发起人...")
        self.search_input.setFocus()
        self.result_label.setText(f"本地已加载 {len(self._all_events)} 条日程，正在同步…")

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

    def _merge_events(self, events: list):
        """Merge ``events`` into the result pool, server copy winning per id."""
        merged = {}
        for ev in self._all_events:
            key = ev.get("event_id") or f"anon:{id(ev)}"
            merged[key] = ev
        for ev in events:
            key = ev.get("event_id") or f"anon:{id(ev)}"
            merged[key] = ev
        self._all_events = sorted(merged.values(), key=event_sort_key)

    def _on_search_fetched(self, events: list):
        self._offline = False
        self._merge_events(events)
        self.search_input.setReadOnly(False)
        self.search_input.setPlaceholderText("输入关键词搜索日程标题、描述或发起人...")
        self.search_input.setFocus()
        if self._all_events:
            self.result_label.setText(f"已加载 {len(self._all_events)} 条日程，请输入关键词搜索")
        else:
            self.result_label.setText("未找到任何日程")
        self._on_search(self.search_input.text())

    def _on_fetch_error(self, error_msg: str):
        if self._all_events:
            # 离线可用：本地结果照常搜索，网络失败只降级提示。
            self._offline = True
            self.result_label.setText(
                f"网络不可用，仅搜索本地 {len(self._all_events)} 条日程"
            )
            self._on_search(self.search_input.text())
            return
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

        suffix = " · 本地" if self._offline else ""
        self.result_label.setText(f"共 {len(matches)} 条结果{suffix}")

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
        # 收尾阶段 lark_cli 可能已经被销毁（父窗口析构 / 进程退出）。
        # 对已删除的 C++ 对象、或已断开过的连接再 disconnect 不会抛异常，
        # 只会留下一条 libpyside 警告，所以要同时挡住"对象没了"和"关过两次"。
        import shiboken6

        if not self._signals_detached and shiboken6.isValid(self._lark_cli):
            self._signals_detached = True
            try:
                self._lark_cli.search_fetched.disconnect(self._on_search_fetched)
                self._lark_cli.fetch_error.disconnect(self._on_fetch_error)
            except RuntimeError:
                pass
        super().closeEvent(ev)
