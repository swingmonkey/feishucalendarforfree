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
