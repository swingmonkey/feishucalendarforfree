"""日程统计 —— 月度热力图与负荷摘要。

数字全部来自本地事实层：打开面板不产生任何网络请求，也不起 node 进程。
这是「有了本地库之后才能做的事」，所以 It 只读 store，不参与同步。
"""

import calendar
from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

import event_store
import stats
import theme

_WEEK_HEADERS = stats.WEEKDAY_LABELS


def _build_palette(name: str) -> dict:
    """热力图与卡片的取色，全部从设计令牌派生。

    热力梯度沿用 token-monitor 的「深蓝 → 亮青」路线：低负荷是冷灰，
    越忙越往青蓝亮部走。原来这里是飞书蓝（#3370FF）单色系五档，
    和整套新外观不搭。
    """
    t = theme.tokens(name)
    if theme.is_dark(name):
        cells = [
            "rgba(255,255,255,0.05)",
            "rgba(14,116,144,0.70)",
            "rgba(8,145,178,0.85)",
            "rgba(34,211,238,0.90)",
            "#67e8f9",
        ]
        cell_text = ["#9aa7b8", "#bae6fd", "#e0f2fe", "#07111f", "#07111f"]
    else:
        cells = [
            "rgba(12,16,22,0.05)",
            "#cffafe",
            "#7dd3e8",
            "#22b8d4",
            "#0e7490",
        ]
        cell_text = ["#6b7684", "#0c1016", "#0c1016", "#ffffff", "#ffffff"]
    return {
        "cell": cells,
        "cell_text": cell_text,
        "bar": t["accent_from"],
        "bar_grad": (
            "qlineargradient(x1:0, y1:1, x2:0, y2:0, "
            f"stop:0 {t['accent_to']}, stop:1 {t['accent_from']})"
        ),
        "card": (
            f"QFrame#statsCard {{ background: {t['glass']}; "
            f"border: 1px solid {t['glass_border_soft']}; "
            f"border-radius: {theme.RADIUS['md']}px; }}"
        ),
        "muted": f"color: {t['muted']};",
        "value": f"color: {t['text']}; font-weight: 600;",
    }


class StatsDialog(QDialog):
    """Heatmap + load summary for one month, read from the local store."""

    def __init__(self, store, theme: str = "dark", today: datetime = None, parent=None):
        super().__init__(parent)
        self._store = store
        self._theme = theme
        self._today = (today or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
        self._year = self._today.year
        self._month = self._today.month
        self._palette = _build_palette(theme)

        self.setWindowTitle("日程统计")
        self._build_ui()
        self._reload()

    # ── Layout ──

    def _build_ui(self):
        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        # 内容放进滚动区：热力格子是固定尺寸，月份换一行（5 周 / 6 周）
        # 就会差出一整排。写死窗口高度时多出来的那部分直接把正文压扁，
        # 摘要行的标签高度会被压成 0，整个「本月概况」变成一块空面板。
        content = QWidget()
        outer = QVBoxLayout(content)
        outer.setContentsMargins(20, 16, 20, 8)
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
        self.grid.setSpacing(6)
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

        self._content = content
        # 固定高度就等于把它压扁：让内容保持自然高度，窗口放不下时滚动
        content.setMinimumHeight(content.sizeHint().height())
        self.scroll = QScrollArea()
        self.scroll.setObjectName("statsScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setWidget(content)
        shell.addWidget(self.scroll, 1)

        bottom_wrap = QWidget()
        bottom = QHBoxLayout(bottom_wrap)
        bottom.setContentsMargins(20, 6, 20, 14)
        self.hint_label = QLabel("统计来自本地日程库，不含全天日程时长")
        self.hint_label.setStyleSheet(self._palette["muted"])
        bottom.addWidget(self.hint_label, 1)
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("secondaryBtn")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        bottom.addWidget(close_btn)
        shell.addWidget(bottom_wrap)

    def _sync_height(self):
        """内容填好之后再量一次：热力格子是固定尺寸，5 周和 6 周的
        月份差一整排，摘要行也是每月不同。量完把内容的最小高度钉住，
        滚动区才不会把它压回去。"""
        layout = self._content.layout()
        if layout is not None:
            layout.activate()
        need = layout.totalSizeHint().height() if layout is not None else 0
        if need and self._content.minimumHeight() != need:
            self._content.setMinimumHeight(need)
        self._fit_size()

    def showEvent(self, event):
        # 构造时子控件还没被 polish 过，sizeHint 全是初值；必须等真正
        # 显示出来再量一次，否则窗口仍按 165px 的内容高度定高。
        super().showEvent(event)
        self._sync_height()

    def _fit_size(self):
        """按内容定窗口尺寸，最多长到屏幕可用区。

        宽度取内容的最小宽度：按星期分布那七列各带一个「4 小时 15 分」
        的标签，压到 520 会把右侧的数值裁掉。高度取内容的自然高度。
        """
        need_h = self._content.minimumHeight() + 76
        need_w = max(self._content.minimumSizeHint().width() + 24, 560)
        screen = self.screen() or QGuiApplication.primaryScreen()
        limit_h, limit_w = 860, 900
        if screen is not None:
            avail = screen.availableGeometry()
            limit_h = min(limit_h, avail.height() - 80)
            limit_w = min(limit_w, avail.width() - 60)
        self.resize(min(need_w, limit_w), max(560, min(need_h, limit_h)))

    def _nav_button(self, text: str) -> QPushButton:
        button = QPushButton(text)
        # 不用 secondaryBtn：它带 6/14px 的 padding，28px 宽的按钮里
        # 内容区会被挤成 0，文字直接消失
        button.setObjectName("navBtn")
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
        self._sync_height()

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
        accent = theme.tokens(self._theme)["accent_from"]
        border = (
            f"border: 2px solid {accent};"
            if is_today
            else "border: 1px solid transparent;"
        )
        cell.setText(str(stat.day.day))
        cell.setStyleSheet(
            f"background: {self._palette['cell'][level]};"
            f"color: {self._palette['cell_text'][level]};"
            f"border-radius: 8px; {border}"
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
            # 默认边距 9px，六行叠起来就是 108px 的空白；这里只需要一条
            # 基线对齐的「标签 —— 数值」行
            line.setContentsMargins(0, 0, 0, 0)
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
            bar.setFixedWidth(26)
            bar.setFixedHeight(max(3, int(64 * minutes / peak)) if minutes else 3)
            bar.setStyleSheet(
                f"background: {self._palette['bar_grad'] if minutes else self._palette['cell'][0]};"
                "border-radius: 4px;"
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
