"""桌面小组件 —— 常驻桌面的三档卡片。

外观深度参考 token-monitor 的 **SwiftUI 实现**
（``native/macos/TokenMonitorWidget/Widget*Views.swift``），不是它的官网 CSS：
原生小组件并不用高透玻璃 + backdrop blur，而是「近实心纯色 + 一条极淡的斜向
渐变」假造质感，没有阴影、没有 inset 高光、几乎没有动画（WidgetKit 靠快照
静态渲染）。这个差别对 Qt 反而是好消息——能画的东西本来就更少。

所有数值都在 ``theme.WIDGET_*`` 里，本文件不出现任何写死的颜色或尺寸。

三档的分工照抄参考实现的信息层级（大数字 → 行名 → 数值三级），
内容换成日历的：

    small   170×170  眉题 + 今日事项数 + 近 7 天趋势曲线
    medium  364×170  左：今日大数字与下一条  右：本月热力图
    large   364×382  大数字+曲线 / 今日明细 / 热力图 + 本周负载
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QMenu

import occurrences
import reminder
import stats
import theme
from widgets import FloatingSurface

# 数据超过这个时长没同步就在角标上提示（参考实现是 20 分钟）
STALE_SECONDS = 20 * 60


# ── 数据层：纯函数，不碰 Qt，方便单测 ─────────────────────────────────


@dataclass
class WidgetSnapshot:
    """一次重绘要用的全部数字。"""

    today_count: int = 0
    today_minutes: int = 0
    headline: str = "今天没有日程"
    subline: str = ""
    rows: list = field(default_factory=list)          # [(时间文本, 标题)]
    trend: list = field(default_factory=list)         # 近 7 天分钟数
    heat: list = field(default_factory=list)          # 星期为行、周为列的档位
    month_minutes: int = 0
    week_rows: list = field(default_factory=list)     # [(周几标签, 分钟)]
    week_max: int = 0
    updated_text: str = ""
    stale: bool = False
    empty: bool = False


def build_snapshot(events, now: datetime, synced_ts: int | None = None) -> WidgetSnapshot:
    """把本地事件算成小组件要显示的数字。

    ``events`` 是 store 里已同步窗口内的事件（含重复规则未展开的原始行），
    展开一律走 ``occurrences`` / ``stats``，这里不再写第二遍展开逻辑。
    """
    events = events or []
    snap = WidgetSnapshot()

    if synced_ts:
        snap.updated_text = _updated_text(now, int(synced_ts))
        snap.stale = (int(now.timestamp()) - int(synced_ts)) > STALE_SECONDS
    else:
        snap.updated_text = "尚未同步"
        snap.stale = True

    if not events:
        snap.empty = True
        return snap

    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start.replace(hour=23, minute=59, second=59)

    occurrences_list = occurrences.collect(events, day_start, day_end)
    snap.today_count = len(occurrences_list)
    snap.today_minutes = sum(
        int(round((o.end - o.start).total_seconds() / 60.0))
        for o in occurrences_list
        if not o.all_day
    )
    snap.headline = f"今天 {snap.today_count} 项" if snap.today_count else "今天没有日程"

    current_or_next = _current_or_next(occurrences_list, now)
    if current_or_next is not None:
        occ, running = current_or_next
        label = "进行中" if running else "下一项"
        snap.subline = f"{label} {_hhmm(occ.start)} {occ.summary}".strip()

    upcoming = [o for o in occurrences_list if o.end >= now][:4]
    snap.rows = [(_hhmm(o.start), o.summary) for o in upcoming]

    # 近 7 天趋势（含今天）：起点必须是 6 天前的 00:00。
    # 用 now - 6d 会保留当前时刻，6 天前 00:00–此刻 之间结束的日程被
    # occurrences.collect 的 end < start 过滤掉，第一个点会偏小。
    trend_days = stats.daily_stats(events, day_start - timedelta(days=6), day_end)
    snap.trend = [
        trend_days[(now - timedelta(days=i)).date()].minutes for i in range(6, -1, -1)
    ]

    # 本月热力：month_grid 是「周为行」，参考实现是「星期为行」，转置一次
    grid = stats.month_grid(events, now.year, now.month)
    snap.heat = [
        # 转置：month_grid 是「周为行」，参考实现是「星期为行」；每行固定 7 格
        [stats.heat_level(cell.minutes) if cell else -1 for cell in week]
        for week in zip(*grid, strict=False)
    ]
    snap.month_minutes = sum(
        stat.minutes for stat in stats.daily_stats(
            events, *stats.month_bounds(now.year, now.month)
        ).values()
    )

    # 本周负载：周一到今天（参考实现的明细只列有内容的行）
    monday = now - timedelta(days=now.weekday())
    week_days = stats.daily_stats(events, monday.replace(hour=0, minute=0), day_end)
    snap.week_rows = [
        (stats.WEEKDAY_LABELS[day.weekday()], stat.minutes)
        for day, stat in sorted(week_days.items())
    ]
    snap.week_max = max([m for _, m in snap.week_rows] + [0])
    return snap


def _hhmm(value: datetime) -> str:
    return value.strftime("%H:%M")


def _updated_text(now: datetime, synced_ts: int) -> str:
    delta = max(0, int(now.timestamp()) - int(synced_ts))
    if delta < 60:
        return "刚刚更新"
    if delta < 3600:
        return f"{delta // 60} 分钟前更新"
    if delta < 86400:
        return f"{delta // 3600} 小时前更新"
    return datetime.fromtimestamp(synced_ts).strftime("%m-%d %H:%M") + " 更新"


def _current_or_next(occurrences, now: datetime):
    """判定「进行中 / 下一项」直接复用 reminder，不在这里再写一遍。"""
    return reminder.current_or_next(occurrences, now)


# ── 呈现层：全自绘 ────────────────────────────────────────────────────


def _qcolor(value) -> QColor:
    """令牌颜色 → QColor。令牌里是 (r,g,b) 或 (r,g,b,a)，a 用 0-1。

    QColor 的第四个参数要的是 **0-255 整数**：把 0.03 直接传进去会被截成 0，
    画出来全透明且不报错。这个 bug 靠肉眼极难发现——热力格、台面渐变、
    分隔线、进度条轨道会同时消失，看起来像布局错了。
    """
    if isinstance(value, str):
        return QColor(value)
    r, g, b = int(value[0]), int(value[1]), int(value[2])
    if len(value) == 4:
        return QColor(r, g, b, int(round(float(value[3]) * 255)))
    return QColor(r, g, b)


class DesktopWidget(FloatingSurface):
    """三档桌面小组件。尺寸/配色变了就 ``update()`` 重绘，不做动画。"""

    size_change_requested = Signal(str)
    close_requested = Signal()

    def __init__(self, parent=None, size_key: str = "medium", theme_name: str = "dark"):
        super().__init__(parent)
        self.setObjectName("desktopWidget")
        self._theme = "light" if theme_name == "light" else "dark"
        self._snapshot = WidgetSnapshot()
        self._t = theme.widget_tokens(self._theme)
        self.setSize(size_key)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    # ── 配置 ──

    def setSize(self, size_key: str):
        key = size_key if size_key in theme.WIDGET_SIZES else "medium"
        self._size_key = key
        width, height = theme.WIDGET_SIZES[key]
        self.setFixedSize(width, height)
        self.update()

    @property
    def size_key(self) -> str:
        return self._size_key

    def apply_theme(self, theme_name: str):
        self._theme = "light" if theme_name == "light" else "dark"
        self._t = theme.widget_tokens(self._theme)
        self.update()

    def set_snapshot(self, snapshot: WidgetSnapshot):
        self._snapshot = snapshot
        self.update()

    # ── 交互 ──

    def contextMenuEvent(self, ev):
        """右键：小组件表面没有任何按钮，出口只能挂在这里。"""
        menu = QMenu(self)
        menu.addAction("打开主窗口", lambda: self.activated.emit())
        size_menu = menu.addMenu("尺寸")
        for key, label in theme.widget_size_choices():
            action = size_menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(key == self._size_key)
            action.triggered.connect(lambda _=False, k=key: self.size_change_requested.emit(k))
        menu.addSeparator()
        menu.addAction("关闭小组件", lambda: self.close_requested.emit())
        menu.exec(ev.globalPos())

    # ── 绘制 ──

    def paintEvent(self, ev):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        self._paint_backdrop(painter, rect)

        pad = theme.WIDGET_LAYOUT["padding"]
        footer_h = float(theme.WIDGET_LAYOUT["footer_height"])
        # 底部留一整行给「更新时间 / 次要指标」，三档共用同一条基线。
        # 不留的话 medium 档的小时数和更新时间会在右下角叠成两行。
        body = rect.adjusted(pad, pad, -pad, -pad - footer_h)
        snap = self._snapshot
        if snap.empty:
            self._paint_empty(painter, body)
            self._paint_footer(painter, body, snap, "")
            painter.end()
            return

        if self._size_key == "small":
            self._paint_small(painter, body, snap)
            right = ""
        elif self._size_key == "medium":
            self._paint_medium(painter, body, snap)
            right = f"本月 {stats.format_hours(snap.month_minutes)}"
        else:
            self._paint_large(painter, body, snap)
            right = f"本月 {stats.format_hours(snap.month_minutes)}"

        footer = QRectF(body.left(), body.bottom() + 4, body.width(), footer_h - 4)
        self._paint_footer(painter, footer, snap, right)
        painter.end()

    def _paint_backdrop(self, painter: QPainter, rect: QRectF):
        """近实心底色 + 一条几乎看不见的斜向渐变。

        渐变方向是右上→左下（参考实现 topTrailing → bottomLeading）；
        浅色主题不能照抄「白色 2.5%」——白底上等于没画，所以令牌里
        给的是青蓝淡染压向白。
        """
        radius = float(theme.WIDGET_LAYOUT["radius"])
        t = self._t
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qcolor(t["base"]))
        painter.drawRoundedRect(rect, radius, radius)

        grad = QLinearGradient(rect.topRight(), rect.bottomLeft())
        grad.setColorAt(0.0, _qcolor(t["grad_from"]))
        grad.setColorAt(1.0, _qcolor(t["grad_to"]))
        painter.setBrush(grad)
        painter.drawRoundedRect(rect, radius, radius)

    # ── 三档布局 ──

    def _paint_small(self, painter: QPainter, body: QRectF, snap: WidgetSnapshot):
        self._paint_eyebrow(painter, body, "今天")
        metric_rect = body.adjusted(0, 16, 0, -theme.WIDGET_LAYOUT["trend_height"])
        self._paint_metric(painter, metric_rect, str(snap.today_count), "项")
        trend_rect = QRectF(
            body.left(), body.bottom() - theme.WIDGET_LAYOUT["trend_height"],
            body.width(), theme.WIDGET_LAYOUT["trend_height"] - 4,
        )
        self._paint_trend(painter, trend_rect, snap.trend)

    def _paint_medium(self, painter: QPainter, body: QRectF, snap: WidgetSnapshot):
        left_w = body.width() * 0.42
        left = QRectF(body.left(), body.top(), left_w, body.height())
        right = QRectF(body.left() + left_w + 10, body.top(), body.width() - left_w - 10, body.height())

        self._paint_eyebrow(painter, left, "今天")
        metric_rect = QRectF(left.left(), left.top() + 15, left.width(), 46)
        self._paint_metric(painter, metric_rect, str(snap.today_count), "项")
        sub_rect = QRectF(left.left(), metric_rect.bottom() + 4, left.width(), 30)
        self._paint_lines(painter, sub_rect, [snap.subline] if snap.subline else ["今天没有安排"])

        self._paint_eyebrow(painter, right, "本月热力")
        heat_rect = QRectF(right.left(), right.top() + 15, right.width(), right.height() - 15)
        self._paint_heat(painter, heat_rect, snap.heat)

    def _paint_large(self, painter: QPainter, body: QRectF, snap: WidgetSnapshot):
        lay = theme.WIDGET_LAYOUT
        top = QRectF(body.left(), body.top(), body.width(), lay["metric_block_height"])
        self._paint_eyebrow(painter, top, "今天")
        metric_rect = QRectF(top.left(), top.top() + 15, top.width() * 0.4, top.height() - 15)
        self._paint_metric(painter, metric_rect, str(snap.today_count), "项")
        trend_rect = QRectF(top.left() + top.width() * 0.46, top.top() + 18,
                            top.width() * 0.54, top.height() - 22)
        self._paint_trend(painter, trend_rect, snap.trend)

        y = top.bottom() + 6
        self._paint_divider(painter, QRectF(body.left(), y, body.width(), 1))
        y += 7

        rows_rect = QRectF(body.left(), y, body.width(), lay["quota_block_height"])
        self._paint_rows(painter, rows_rect, snap.rows)
        y = rows_rect.bottom() + 6
        self._paint_divider(painter, QRectF(body.left(), y, body.width(), 1))
        y += 7

        bottom = QRectF(body.left(), y, body.width(), body.bottom() - y)
        heat_w = bottom.width() * lay["heat_week_ratio"]
        heat_rect = QRectF(bottom.left(), bottom.top() + 14, heat_w, bottom.height() - 14)
        self._paint_eyebrow(painter, QRectF(bottom.left(), bottom.top(), heat_w, 14), "本月")
        self._paint_heat(painter, heat_rect, snap.heat)

        self._paint_divider(
            painter, QRectF(bottom.left() + heat_w + 8, bottom.top() + 10, 1, bottom.height() - 10)
        )
        detail = QRectF(bottom.left() + heat_w + 18, bottom.top(),
                        bottom.width() - heat_w - 18, bottom.height())
        self._paint_eyebrow(painter, detail, "本周负载")
        self._paint_bars(painter, QRectF(detail.left(), detail.top() + 15, detail.width(),
                                        detail.height() - 15), snap.week_rows, snap.week_max)

    # ── 元素 ──

    def _paint_eyebrow(self, painter: QPainter, rect: QRectF, text: str):
        """眉题：10px、大写、字距拉开、次要色。层级靠字号字重，不靠颜色。

        一律贴顶画。以前用 AlignVCenter，调用方给的矩形是整个区块的高度，
        结果眉题落到区块正中——小档里盖住大数字，大档里跑到柱条下面。
        """
        font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["title"], QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(self._color("muted"))
        painter.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                         text.upper() if text.isascii() else text)

    def _paint_metric(self, painter: QPainter, rect: QRectF, number: str, unit: str):
        """大数字 + 单位。数字用等宽栈（tabular），单位小一号且**同基线**。

        单位不能按矩形底部对齐：矩形是整个区块的高度，那样「项」会掉到
        离数字很远的地方。基线要从数字自己的字体度量算。
        """
        size = (theme.WIDGET_FONT["metric_small"] if self._size_key == "small"
                else theme.WIDGET_FONT["metric"])
        font = self._font(theme.MONO_STACK, size, QFont.Weight.DemiBold)
        fm = QFontMetrics(font)
        painter.setFont(font)
        painter.setPen(self._color("number"))
        # 参考实现给大数字 -1.5 的左偏移，等宽数字的左侧空隙在视觉上偏大
        painter.drawText(
            QRectF(rect.left() - 1.5, rect.top(), rect.width(), rect.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            number,
        )
        baseline = rect.center().y() - fm.height() / 2 + fm.ascent()

        unit_font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["row_label"], QFont.Weight.Medium)
        uf = QFontMetrics(unit_font)
        painter.setFont(unit_font)
        painter.setPen(self._color("muted"))
        painter.drawText(
            QRectF(rect.left() + fm.horizontalAdvance(number) + 3,
                   baseline - uf.ascent(), rect.width(), uf.height()),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
            unit,
        )

    def _paint_lines(self, painter: QPainter, rect: QRectF, lines: list):
        font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["row_label"], QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(self._color("muted"))
        metrics = QFontMetrics(font)
        for idx, text in enumerate(lines):
            line_rect = QRectF(rect.left(), rect.top() + idx * (metrics.height() + 2),
                               rect.width(), metrics.height())
            painter.drawText(line_rect,
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             self._elide(metrics, text, rect.width()))

    def _paint_rows(self, painter: QPainter, rect: QRectF, rows: list):
        """今日明细：时间列定宽等宽，标题列吃掉剩余宽度并省略号收尾。"""
        if not rows:
            self._paint_lines(painter, rect, ["今天没有安排"])
            return
        time_font = self._font(theme.MONO_STACK, theme.WIDGET_FONT["row_label"], QFont.Weight.Medium)
        title_font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["row_label"], QFont.Weight.DemiBold)
        fm_time = QFontMetrics(time_font)
        time_w = fm_time.horizontalAdvance("00:00") + 6
        for idx, (when, title) in enumerate(rows[:4]):
            y = rect.top() + idx * (fm_time.height() + 3)
            painter.setFont(time_font)
            painter.setPen(self._color("muted"))
            painter.drawText(QRectF(rect.left(), y, time_w, fm_time.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, when)
            painter.setFont(title_font)
            painter.setPen(self._color("number"))
            painter.drawText(QRectF(rect.left() + time_w, y, rect.width() - time_w, fm_time.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             self._elide(QFontMetrics(title_font), title, rect.width() - time_w))

    def _paint_heat(self, painter: QPainter, rect: QRectF, heat: list):
        """星期为行、周为列。档位来自 stats.heat_level，颜色来自令牌五档。

        -1 是月历网格里的空白格（不属于本月），画 clear 而不是画「0 档」——
        否则月初月末会出现一排假的「空闲日」。
        """
        if not heat or not heat[0]:
            return
        rows = len(heat)
        cols = max(len(week) for week in heat)
        gap = theme.WIDGET_LAYOUT["heat_gap"]
        cell = self._heat_cell(rect, cols, rows)
        radius = min(1.5, cell / 3)
        painter.setPen(Qt.PenStyle.NoPen)
        for r, week in enumerate(heat):
            for c, level in enumerate(week):
                if level < 0:
                    continue
                x = rect.left() + c * (cell + gap)
                y = rect.top() + r * (cell + gap)
                rgba = self._t["heat"][min(level, len(self._t["heat"]) - 1)]
                painter.setBrush(_qcolor(rgba))
                painter.drawRoundedRect(QRectF(x, y, cell, cell), radius, radius)

    def _heat_cell(self, rect: QRectF, cols: int, rows: int) -> float:
        """在「不溢出」和「不小于可读下限」之间取格子边长。"""
        lay = theme.WIDGET_LAYOUT
        gap = lay["heat_gap"]
        fit_w = (rect.width() - gap * (cols - 1)) / max(1, cols)
        fit_h = (rect.height() - gap * (rows - 1)) / max(1, rows)
        return max(lay["heat_cell_min"], min(lay["heat_cell_max"], fit_w, fit_h))

    def _paint_bars(self, painter: QPainter, rect: QRectF, rows: list, maximum: int):
        """本周负载：行名 + 3px 胶囊条 + 数值。参考实现的 PercentageBar。"""
        if not rows:
            return
        label_font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["row_label"], QFont.Weight.Medium)
        value_font = self._font(theme.MONO_STACK, theme.WIDGET_FONT["value"], QFont.Weight.Medium)
        fm = QFontMetrics(label_font)
        bar_h = float(theme.WIDGET_LAYOUT["bar_height"])
        row_h = max(bar_h + 6, fm.height() + 3)
        label_w = fm.horizontalAdvance("一") + 8
        value_w = QFontMetrics(value_font).horizontalAdvance("000分") + 4
        track_w = max(10.0, rect.width() - label_w - value_w - 10)
        track = self._t["track"]
        chart = self._t["chart"]
        for idx, (label, minutes) in enumerate(rows[-6:]):
            y = rect.top() + idx * row_h
            if y + row_h > rect.bottom():
                break
            painter.setFont(label_font)
            painter.setPen(self._color("muted"))
            painter.drawText(QRectF(rect.left(), y, label_w, row_h),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
            bar_rect = QRectF(rect.left() + label_w, y + (row_h - bar_h) / 2, track_w, bar_h)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_qcolor(track))
            painter.drawRoundedRect(bar_rect, bar_h / 2, bar_h / 2)
            ratio = 0.0 if not maximum else max(0.0, min(1.0, minutes / maximum))
            if ratio > 0:
                fill = _qcolor(chart)
                fill.setAlphaF(self._t["fill_alpha"])
                painter.setBrush(fill)
                painter.drawRoundedRect(
                    QRectF(bar_rect.left(), bar_rect.top(), bar_rect.width() * ratio, bar_h),
                    bar_h / 2, bar_h / 2,
                )
            painter.setFont(value_font)
            painter.setPen(self._color("muted"))
            painter.drawText(QRectF(bar_rect.right() + 4, y, value_w, row_h),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                             f"{minutes}" if minutes else "—")

    def _paint_trend(self, painter: QPainter, rect: QRectF, values: list):
        """近 7 天趋势曲线：Catmull-Rom 转三次贝塞尔，控制点取 (next-prev)/6。"""
        pts = [v for v in (values or [])]
        if len(pts) < 2:
            return
        peak = max(max(pts), 1)
        step = rect.width() / (len(pts) - 1)
        points = [
            QPointF(rect.left() + i * step,
                    rect.bottom() - (v / peak) * (rect.height() - 4) - 2)
            for i, v in enumerate(pts)
        ]
        path = QPainterPath(points[0])
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1 = points[i]
            p2 = points[i + 1]
            p3 = points[i + 2] if i + 2 < len(points) else p2
            path.cubicTo(
                QPointF(p1.x() + (p2.x() - p0.x()) / 6, p1.y() + (p2.y() - p0.y()) / 6),
                QPointF(p2.x() - (p3.x() - p1.x()) / 6, p2.y() - (p3.y() - p1.y()) / 6),
                p2,
            )
        pen = QPen(_qcolor(self._t["chart"]))
        pen.setWidthF(float(theme.WIDGET_LAYOUT["trend_stroke"]))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _paint_divider(self, painter: QPainter, rect: QRectF):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_qcolor(self._t["hairline"]))
        painter.drawRect(rect)

    def _paint_empty(self, painter: QPainter, body: QRectF):
        """空态文案照抄参考实现的两行结构：状态 + 该做什么。"""
        title_font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["row_label"] + 2,
                                QFont.Weight.DemiBold)
        hint_font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["value"], QFont.Weight.Medium)
        painter.setFont(title_font)
        painter.setPen(self._color("number"))
        painter.drawText(QRectF(body.left(), body.center().y() - 16, body.width(), 18),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "暂无日程数据")
        painter.setFont(hint_font)
        painter.setPen(self._color("muted"))
        painter.drawText(QRectF(body.left(), body.center().y() + 2, body.width(), 14),
                         Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter, "打开飞书日程一次")

    def _paint_footer(self, painter: QPainter, rect: QRectF, snap: WidgetSnapshot, right: str = ""):
        """底部一行：左边数据新鲜度，右边次要指标。

        过期时前面加 ⚠（参考实现换的是图标 + 次要色；这里颜色已经统一是
        次要色，不加符号就只剩文字，无障碍模式下也读不出状态）。
        """
        font = self._font(theme.SANS_STACK, theme.WIDGET_FONT["detail"], QFont.Weight.Medium)
        painter.setFont(font)
        metrics = QFontMetrics(font)
        painter.setPen(self._color("muted"))
        if snap.updated_text:
            text = ("⚠ " + snap.updated_text) if snap.stale else snap.updated_text
            painter.drawText(QRectF(rect.left(), rect.top(), rect.width() * 0.6, rect.height()),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             self._elide(metrics, text, rect.width() * 0.6))
        if right:
            painter.drawText(QRectF(rect.left() + rect.width() * 0.4, rect.top(),
                                    rect.width() * 0.6, rect.height()),
                             Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, right)

    # ── 小工具 ──

    def _font(self, stack: str, pixel_size: float, weight: QFont.Weight) -> QFont:
        font = QFont()
        # theme 里的字体栈是 QSS 写法（带引号、逗号分隔），QFont 取第一个族名即可
        family = stack.split(",")[0].strip().strip('"')
        font.setFamily(family)
        font.setPixelSize(max(8, int(round(pixel_size))))
        font.setWeight(weight)
        return font

    def _color(self, key: str) -> QColor:
        value = self._t[key]
        return _qcolor(value)

    @staticmethod
    def _elide(metrics: QFontMetrics, text: str, width: float) -> str:
        return metrics.elidedText(text, Qt.TextElideMode.ElideRight, int(max(0, width)))
