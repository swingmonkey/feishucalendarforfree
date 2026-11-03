"""日程统计 —— 月度热力图与负荷摘要。

数字全部来自本地事实层：打开面板不产生任何网络请求，也不起 node 进程。
这是「有了本地库之后才能做的事」，所以 It 只读 store，不参与同步。
"""

import calendar
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

import event_store
import stats

_WEEK_HEADERS = stats.WEEKDAY_LABELS

_LIGHT = {
    "cell": ["#F2F3F5", "#D6E4FF", "#ADC6FF", "#3370FF", "#1F4CD6"],
    "cell_text": ["#646A73", "#1F2329", "#1F2329", "#FFFFFF", "#FFFFFF"],
    "bar": "#3370FF",
    "card": "QFrame#statsCard { background: #FFFFFF; border: 1px solid #E4E6EB; border-radius: 8px; }",
    "muted": "color: #646A73;",
    "value": "color: #1F2329; font-weight: 600;",
}
_DARK = {
    "cell": ["#2A2D34", "#1E355C", "#2A4C86", "#3370FF", "#6E8FF5"],
    "cell_text": ["#8F959E", "#C9D4E8", "#E5E6EB", "#FFFFFF", "#0B1B33"],
    "bar": "#4E83FD",
    "card": "QFrame#statsCard { background: #23262D; border: 1px solid #3A3F4B; border-radius: 8px; }",
    "muted": "color: #A6ADBB;",
    "value": "color: #E5E6EB; font-weight: 600;",
}


class StatsDialog(QDialog):
    """Heatmap + load summary for one month, read from the local store."""

    def __init__(self, store, theme: str = "light", today: datetime = None, parent=None):
        super().__init__(parent)
        self._store = store
        self._theme = theme
        self._today = (today or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        self._year = self._today.year
        self._month = self._today.month
        self._palette = _DARK if theme == "dark" else _LIGHT

        self.setWindowTitle("日程统计")
        self.setFixedSize(520, 620)
        self._build_ui()
        self._reload()

    # ── Layout ──

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 16)
        outer.setSpacing(12)

        nav = QHBoxLayout()
        self.prev_btn = self._nav_button("‹")
        self.prev_btn.clicked.connect(lambda: self._shift_month(-1))
        self.next_btn = self._nav_button("›")
        self.next_btn.clicked.connect(lambda: self._shift_month(1))
        self.month_label = QLabel("")
        self.month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.month_label.setFont(font)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.month_label, 1)
        nav.addWidget(self.next_btn)
        outer.addLayout(nav)

        self.grid_host = QWidget()
        self.grid = QGridLayout(self.grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(4)
        outer.addWidget(self.grid_host)

        outer.addLayout(self._build_legend())

        self.summary_card = QFrame()
        self.summary_card.setObjectName("statsCard")
        self.summary_layout = QVBoxLayout(self.summary_card)
        self.summary_layout.setContentsMargins(14, 12, 14, 12)
        self.summary_layout.setSpacing(6)
        outer.addWidget(self.summary_card)

        self.weekday_card = QFrame()
        self.weekday_card.setObjectName("statsCard")
        self.weekday_layout = QVBoxLayout(self.weekday_card)
        self.weekday_layout.setContentsMargins(14, 12, 14, 12)
        self.weekday_layout.setSpacing(8)
        outer.addWidget(self.weekday_card)

        outer.addStretch()

        bottom = QHBoxLayout()
        self.hint_label = QLabel("统计来自本地日程库，不含全天日程时长")
        self.hint_label.setStyleSheet(self._palette["muted"])
        bottom.addWidget(self.hint_label, 1)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        outer.addLayout(bottom)

    def _nav_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("secondaryBtn")
        button.setFixedSize(28, 26)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        return button

    def _build_legend(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)
        label = QLabel("少")
        label.setStyleSheet(self._palette["muted"])
        row.addWidget(label)
        for level in range(5):
            swatch = QLabel("")
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(
                f"background: {self._palette['cell'][level]}; border-radius: 3px;"
            )
            row.addWidget(swatch)
        more = QLabel("多")
        more.setStyleSheet(self._palette["muted"])
        row.addWidget(more)
        row.addStretch()
        return row

    # ── Data ──

    def _events(self) -> list:
        start, end = stats.month_bounds(self._year, self._month)
        # 多取前一周，重复日程的展开边界才不会被月份切掉
        return event_store.read_range(self._store, start - timedelta(days=7), end)

    def _reload(self):
        self.month_label.setText(f"{self._year} 年 {self._month} 月")
        events = self._events()
        self._fill_grid(events)
        self._fill_summary(events)

    def _fill_grid(self, events):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for column, name in enumerate(_WEEK_HEADERS):
            header = QLabel(name)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setStyleSheet(self._palette["muted"])
            self.grid.addWidget(header, 0, column)

        weeks = stats.month_grid(events, self._year, self._month)
        for row_index, week in enumerate(weeks, start=1):
            for column, stat in enumerate(week):
                cell = self._make_cell(stat)
                self.grid.addWidget(cell, row_index, column)

    def _make_cell(self, stat) -> QLabel:
        cell = QLabel("")
        cell.setFixedSize(62, 46)
        cell.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if stat is None:
            cell.setStyleSheet("background: transparent;")
            return cell

        level = stats.heat_level(stat.minutes)
        is_today = stat.day == self._today.date()
        border = "border: 2px solid #3370FF;" if is_today else "border: 1px solid transparent;"
        cell.setText(str(stat.day.day))
        cell.setStyleSheet(
            f"background: {self._palette['cell'][level]};"
            f"color: {self._palette['cell_text'][level]};"
            f"border-radius: 6px; {border}"
        )
        detail = [stat.day.strftime("%m月%d日")]
        if stat.events:
            detail.append(f"{stat.events} 项日程")
            detail.append(stats.format_minutes(stat.minutes))
        else:
            detail.append("无日程")
        cell.setToolTip(" · ".join(detail))
        return cell

    def _fill_summary(self, events):
        while self.summary_layout.count():
            item = self.summary_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        start, end = stats.month_bounds(self._year, self._month)
        summary = stats.summarize(events, start, end)

        rows = [
            ("本月会议时长", stats.format_minutes(summary.total_minutes)),
            ("日程总数", f"{summary.total_events} 项"),
            (
                "最忙一天",
                f"{summary.busiest.day.strftime('%m月%d日')} · {stats.format_minutes(summary.busiest.minutes)}"
                if summary.busiest
                else "—",
            ),
            ("有日程的天数", f"{summary.active_days} / {summary.days} 天"),
            ("最长连续", f"{summary.longest_streak} 天"),
            ("活跃日均", stats.format_minutes(summary.average_minutes_per_active_day)),
        ]
        for title, value in rows:
            line = QHBoxLayout()
            name = QLabel(title)
            name.setStyleSheet(self._palette["muted"])
            text = QLabel(value)
            text.setStyleSheet(self._palette["value"])
            line.addWidget(name)
            line.addStretch()
            line.addWidget(text)
            holder = QWidget()
            holder.setLayout(line)
            self.summary_layout.addWidget(holder)

        self._fill_weekdays(summary.weekday_minutes)

    def _fill_weekdays(self, weekday_minutes):
        while self.weekday_layout.count():
            item = self.weekday_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        title = QLabel("按星期分布")
        title.setStyleSheet(self._palette["muted"])
        self.weekday_layout.addWidget(title)

        peak = max(weekday_minutes) or 1
        row = QHBoxLayout()
        row.setSpacing(6)
        for index, minutes in enumerate(weekday_minutes):
            column = QVBoxLayout()
            column.setSpacing(2)

            value = QLabel(stats.format_minutes(minutes) if minutes else "")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setStyleSheet(self._palette["muted"])

            bar = QFrame()
            bar.setFixedWidth(34)
            bar.setFixedHeight(max(3, int(48 * minutes / peak)) if minutes else 3)
            bar.setStyleSheet(
                f"background: {self._palette['bar'] if minutes else self._palette['cell'][0]};"
                "border-radius: 3px;"
            )
            bar_holder = QWidget()
            bar_layout = QVBoxLayout(bar_holder)
            bar_layout.setContentsMargins(0, 0, 0, 0)
            bar_layout.addStretch()
            bar_layout.addWidget(bar, 0, Qt.AlignmentFlag.AlignHCenter)

            name = QLabel(stats.WEEKDAY_LABELS[index])
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name.setStyleSheet(self._palette["muted"])

            column.addWidget(value)
            column.addWidget(bar_holder, 1)
            column.addWidget(name)
            holder = QWidget()
            holder.setLayout(column)
            row.addWidget(holder)
        self.weekday_layout.addLayout(row)

    # ── Navigation ──

    def _shift_month(self, delta: int):
        # 用「从纪元起的月份序号」做加减，delta 绝对值大于 1 也不会算错
        total = self._year * 12 + (self._month - 1) + int(delta)
        self._year, zero_based_month = divmod(total, 12)
        self._month = zero_based_month + 1
        self._reload()


def days_in_month(year: int, month: int) -> int:
    """Kept public for tests and calendar math elsewhere."""
    return calendar.monthrange(year, month)[1]
