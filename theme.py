"""设计令牌（Design Tokens）—— 界面视觉的单一真源。

体系移植自 Javis603/token-monitor 的 `site/styles/tokens.css`：
深色玻璃台面、青蓝单向渐变、极细分隔线、等宽数字。原项目是网页，
这里做的是**令牌层的移植**，不是把网页像素搬进 Qt——日历是功能密集的
小窗口（440–720px），字号与间距必须按桌面控件的密度重算。

三层结构：
    theme.py        令牌（本文件）：颜色、圆角、间距、字阶、动效曲线
    styles.py       QSS 生成：读令牌拼出选择器规则
    *_view.py       自绘：QSS 表达不了的光晕 / 渐变描边

Why a separate module: 改造前 50 个十六进制色值散落在 1697 行 QSS 里，
换一个色要全文搜索替换，且深浅两套主题各写一遍容易漂移。集中到这里后，
QSS 只引用语义名（`t["glass"]`），改一处即全局生效。

注意 Qt 的两个硬限制：
  · QSS 没有 CSS 变量，所以令牌是 Python 常量、用 f-string 注入
  · QSS 没有 backdrop-filter，所谓「玻璃」只能用半透明色近似——
    真正的模糊在 Qt 里要 QGraphicsBlurEffect 逐控件加，代价远大于收益
"""

from __future__ import annotations

# ── 字体 ────────────────────────────────────────────────────────────
# 正文沿用系统无衬线；数字用等宽（token-monitor 里所有数字都是 mono +
# tabular，这是整套界面最有辨识度的骨架——日历里时间、日号、计数全是数字）
SANS_STACK = (
    '"SF Pro Text", "PingFang SC", "Microsoft YaHei UI", '
    '"Segoe UI", sans-serif'
)
MONO_STACK = (
    '"SF Mono", "JetBrains Mono", "Cascadia Mono", Menlo, '
    'Consolas, "Courier New", monospace'
)

# ── 非颜色令牌 ───────────────────────────────────────────────────────
# 圆角只有三档，与原项目 --r-sm/md/lg 一致
RADIUS = {"sm": 10, "md": 12, "lg": 14}

# 间距基准 4px（原项目 rem 体系折算到桌面密度后的取值）
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 20}

# 动效：微交互 130–180ms，入场 800–1300ms
# 曲线 cubic-bezier(.16,1,.3,1) 在 Qt 里对应 OutExpo
DURATION = {"fast": 130, "mid": 180, "slow": 260, "enter": 900}
EASING_ENTER = "OutExpo"
EASING_HOVER = "OutCubic"

# 字阶：原项目网页用 4.9rem/2.65rem 的宣传级字阶，桌面日历用不到。
# 这里是按「一屏塞下 6 行日历」的密度重算过的等价层级。
FONT_SIZE = {
    "eyebrow": 10,   # 全大写小标签（如「本月」）
    "label": 10,     # 次要说明
    "body": 12,      # 正文 / 日程标题
    "sub": 11,       # 次要信息 / 时间
    "title": 14,     # 面板标题
}

# ── 颜色令牌 ─────────────────────────────────────────────────────────
# 语义名对照原项目的 CSS 变量：
#   bg/stage          → --bg / --stage-bg
#   glass/glass_strong→ --widget-bg / --widget-bg-strong
#   line              → --surface-border
#   accent_from/to    → --accent-from / --accent-to
_COMMON = {
    "radius_sm": RADIUS["sm"],
    "radius_md": RADIUS["md"],
    "radius_lg": RADIUS["lg"],
}

_DARK = {
    # 台面
    "bg": "#14171c",
    "stage": "#07080b",
    "chrome": "#14171c",
    "nav_bg": "rgba(7,8,11,0.72)",
    # 文字
    "text": "#eaf2ff",
    "text_strong": "#f4f8ff",
    "muted": "#9aa7b8",
    "soft": "rgba(234,242,255,0.52)",
    "eyebrow": "rgba(234,242,255,0.62)",
    # 强调
    "accent": "#5b9dff",
    "accent_from": "#22d3ee",
    "accent_to": "#5b9dff",
    "accent_ink": "#07111f",
    "link": "#7fb0ff",
    "warn": "#f59e0b",
    "warn_text": "#fbbf24",
    "danger": "#ef4444",
    # danger 在深底上要更亮才读得清（关闭按钮 hover、危险按钮文字），
    # 浅底上反过来要更暗——这两个值不能共用一个 hex
    "danger_hover": "#fca5a5",
    "success": "#34d399",
    # 语义色的淡底版本：确认框图标圆徽、Toast 图标这类地方要「有色但不抢」，
    # 直接用纯色会糊成一块。写死 rgba 就又回到改造前那种散落色值的老路。
    "accent_soft": "rgba(91,157,255,0.16)",
    "danger_soft": "rgba(239,68,68,0.16)",
    "success_soft": "rgba(52,211,153,0.16)",
    "warn_soft": "rgba(245,158,11,0.16)",
    # 面与线
    "surface": "rgba(255,255,255,0.05)",
    "surface_2": "rgba(255,255,255,0.08)",
    "line": "rgba(255,255,255,0.10)",
    "line_soft": "rgba(255,255,255,0.06)",
    "line_strong": "rgba(255,255,255,0.16)",
    # 玻璃
    "glass": "rgba(40,44,52,0.42)",
    "glass_strong": "rgba(40,44,52,0.50)",
    "glass_border": "rgba(232,238,244,0.24)",
    "glass_border_soft": "rgba(232,238,244,0.14)",
    # 主按钮：白底深字（原项目最克制的一笔——强调色只给渐变，主按钮不用）
    "btn_primary_bg": "#ffffff",
    "btn_primary_fg": "#14171c",
    "btn_primary_hover": "#f2f6ff",
    "on_strong": "#14171c",
    # 日程配色的底色（左侧色条 + 淡底）
    "event_ink": "rgba(91,157,255,0.22)",
    "event_ink_hover": "rgba(91,157,255,0.34)",
    # 滚动条
    "scroll_handle": "rgba(255,255,255,0.14)",
    "scroll_handle_hover": "rgba(255,255,255,0.24)",
    # 二维码卡片两套主题都固定白底（深浅模块要有足够对比度才扫得出来），
    # 所以卡片里的占位文字必须用墨色而不是 muted——浅色主题的 muted 是灰，
    # 深色主题的 muted 是浅蓝白，后者落在白卡上直接看不见。
    "qr_ink": "#646A73",
}

_LIGHT = {
    "bg": "#f6f7f9",
    "stage": "#ffffff",
    "chrome": "#ffffff",
    "nav_bg": "rgba(255,255,255,0.78)",
    "text": "#1a2029",
    "text_strong": "#0c1016",
    "muted": "#6b7684",
    "soft": "rgba(26,32,41,0.52)",
    "eyebrow": "rgba(26,32,41,0.62)",
    # 浅色下青蓝要压暗才够对比（#22d3ee 在白底上几乎看不见）
    "accent": "#2563eb",
    "accent_from": "#0891b2",
    "accent_to": "#2563eb",
    "accent_ink": "#ffffff",
    "link": "#1d5fd0",
    "warn": "#c2750a",
    "warn_text": "#a4600a",
    "danger": "#dc2626",
    "danger_hover": "#b91c1c",
    "success": "#0f9d70",
    # 淡底版本（与深色主题同构，alpha 略低——白底上同样的透明度会更显眼）
    "accent_soft": "rgba(37,99,235,0.10)",
    "danger_soft": "rgba(220,38,38,0.10)",
    "success_soft": "rgba(15,157,112,0.10)",
    "warn_soft": "rgba(194,117,10,0.12)",
    "surface": "rgba(12,16,22,0.035)",
    "surface_2": "rgba(12,16,22,0.06)",
    "line": "rgba(12,16,22,0.10)",
    "line_soft": "rgba(12,16,22,0.07)",
    "line_strong": "rgba(12,16,22,0.16)",
    "glass": "rgba(255,255,255,0.72)",
    "glass_strong": "rgba(255,255,255,0.88)",
    "glass_border": "rgba(12,16,22,0.10)",
    "glass_border_soft": "rgba(12,16,22,0.07)",
    "btn_primary_bg": "#0c1016",
    "btn_primary_fg": "#ffffff",
    "btn_primary_hover": "#1e2630",
    "on_strong": "#ffffff",
    "event_ink": "rgba(37,99,235,0.14)",
    "event_ink_hover": "rgba(37,99,235,0.24)",
    "scroll_handle": "rgba(12,16,22,0.16)",
    "scroll_handle_hover": "rgba(12,16,22,0.28)",
    "qr_ink": "#646A73",
}


def alpha(hex_color: str, opacity: float) -> str:
    """把 ``#rrggbb`` 令牌派生成 ``rgba(...)``，给淡底 / 描边 / hover 用。

    外观层以前直接写 ``rgba(239,68,68,0.45)``——那是深色主题 danger 的 RGB，
    浅色主题拿到同一串，等于换肤换不掉。派生之后真源只有一个 hex 令牌，
    透明度是局部信息，留在调用处写。
    """
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{opacity})"


def tokens(name: str) -> dict:
    """取一套令牌。``name`` 为 "light" 时返回浅色，其余一律深色。

    未知主题名不抛异常：主题值来自用户配置文件，脏值应该退回默认
    而不是让应用起不来。
    """
    palette = _LIGHT if name == "light" else _DARK
    merged = dict(_COMMON)
    merged.update(palette)
    merged["mono"] = MONO_STACK
    merged["sans"] = SANS_STACK
    return merged


def is_dark(name: str) -> bool:
    return name != "light"


# ── 自绘用的数值版本 ─────────────────────────────────────────────────
# QSS 能用 rgba 字符串，QPainter 需要 QColor。这里给出与令牌同源的
# RGB + alpha，避免自绘代码里再写死一遍颜色。
PAINT = {
    "dark": {
        "glow": (42, 51, 64),
        "beam_from": (34, 211, 238),
        "beam_to": (91, 157, 255),
        "today_ring": (34, 211, 238),
        "today_ring_alt": (91, 157, 255),
        "stage": (7, 8, 11),
        "bg": (20, 23, 28),
        # 细轨道的基色：深色主题用白、浅色主题用墨，透明度由调用方给
        "track": (255, 255, 255),
    },
    "light": {
        "glow": (210, 226, 245),
        "beam_from": (8, 145, 178),
        "beam_to": (37, 99, 235),
        "today_ring": (8, 145, 178),
        "today_ring_alt": (37, 99, 235),
        "stage": (255, 255, 255),
        "bg": (246, 247, 249),
        "track": (12, 16, 22),
    },
}


def paint_colors(name: str) -> dict:
    return PAINT["light"] if name == "light" else PAINT["dark"]


# ── 桌面小组件（desktop_widget.py 专用）───────────────────────────────
# 数值抄自 token-monitor 的 **SwiftUI 实现**（native/macos/TokenMonitorWidget/），
# 不是官网 CSS。这个区别很关键：官网那套是高透玻璃（rgba(40,44,52,.42) +
# backdrop blur），而原生小组件其实是「近实心纯色 + 一条极淡的斜向渐变」
# 假造质感——没有 vibrancy、没有阴影、没有 inset 高光、几乎没有动画
# （WidgetKit 靠快照静态渲染）。照抄原生这一版对 Qt 也更友好：QPainter 本来
# 就能画，不用去追拿不到的壁纸模糊。
#
# 参考实现用 .environment(\.colorScheme, .dark) 把小组件写死成深色。我们两套
# 都做：这个应用有真正的浅色主题，而且「换肤必须真的换肤」已经是项目约定
# （见 tests/test_skin_surfaces.py），深色专属的小组件会当场违反它。
WIDGET_SIZES = {
    # WidgetKit 的真实尺寸（small 是正方形），单位是逻辑点
    "small": (170, 170),
    "medium": (364, 170),
    "large": (364, 382),
}

WIDGET_SIZE_LABELS = {"small": "小", "medium": "中", "large": "大"}


def widget_size_choices() -> list:
    """``[("small", "小 · 170×170"), ...]``——挂件右键菜单和设置页共用一份。

    两处各写各的标签，早晚会有一处写着「中」另一处写着「Medium」。
    """
    return [
        (key, f"{WIDGET_SIZE_LABELS[key]} · {width}×{height}")
        for key, (width, height) in WIDGET_SIZES.items()
    ]

# 字阶同样抄自原生实现。8.5 / 7.5 这两档在桌面尺度上极小，是刻意照抄——
# 小组件的信息层级靠「大数字 vs 行名 vs 数值」三级拉开，不是靠颜色。
WIDGET_FONT = {
    "metric_small": 37,   # small 档大数字
    "metric": 42,         # medium/large 档大数字
    "title": 10,          # 模块标题（大写）
    "row_label": 10,      # 明细行名
    "value": 8.5,         # 明细行数值
    "detail": 7.5,        # 辅助说明
}

WIDGET_LAYOUT = {
    "radius": 16,          # 系统给 WidgetKit 裁圆角，浮窗要自己画
    "padding": 12,
    "gap": 8,
    "footer_height": 14,   # 底部一行：左更新时间、右次要指标，各档共用
    "trend_height": 34,    # small 档趋势曲线区
    "metric_block_height": 76,   # large 档「大数字 + 曲线」区
    "quota_block_height": 80,    # large 档配额/明细区
    "heat_week_ratio": 0.44,     # large 档热力图占宽比例
    "bar_height": 3,
    "trend_stroke": 1.8,
    # 热力格子：参考实现给的是 5–9.5px，那是「44% 宽度里要塞 16 周」的产物，
    # 不是审美上限。我们只画当月（≤6 列），照抄上限会留一大片空白，
    # 所以这里按「填满可用面积」取，只留一个防呆上限。
    "heat_cell_min": 5.0,
    "heat_cell_max": 13.0,
    "heat_gap": 2.5,
}

_WIDGET = {
    "dark": {
        "base": (9, 11, 14),               # Color(r:.035, g:.043, b:.055)
        "grad_from": (255, 255, 255, 0.025),   # 右上，几乎看不见的白
        "grad_to": (91, 157, 255, 0.13),       # 左下，accent 淡染
        "number": (243, 251, 247),
        "muted": (163, 173, 187),
        "chart": (115, 189, 245),
        "hairline": (255, 255, 255, 0.14),
        # 热力五档：0 是「空白但不消失」，4 实心。分档阈值用 stats.HEAT_THRESHOLDS
        "heat": [
            (255, 255, 255, 0.03),
            (90, 170, 255, 0.18),
            (120, 190, 255, 0.45),
            (150, 210, 255, 0.80),
            (180, 230, 255, 1.00),
        ],
        "track": (255, 255, 255, 0.07),
        "fill_alpha": 0.82,
    },
    "light": {
        # 浅色不是把深色取反：白底上「白 2.5% 的渐变」等于没画，
        # 所以渐变改成青蓝淡染压向白，主体仍然是近实心
        "base": (247, 249, 252),
        "grad_from": (8, 145, 178, 0.05),
        "grad_to": (37, 99, 235, 0.10),
        "number": (12, 16, 22),
        "muted": (92, 102, 118),
        "chart": (37, 99, 235),
        "hairline": (12, 16, 22, 0.12),
        "heat": [
            (12, 16, 22, 0.05),
            (37, 99, 235, 0.18),
            (37, 99, 235, 0.38),
            (37, 99, 235, 0.62),
            (37, 99, 235, 0.88),
        ],
        "track": (12, 16, 22, 0.08),
        "fill_alpha": 0.9,
    },
}


def widget_tokens(name: str) -> dict:
    """取一组小组件自绘数值（QPainter 用，全部是 RGBA 元组）。"""
    return _WIDGET["light"] if name == "light" else _WIDGET["dark"]
