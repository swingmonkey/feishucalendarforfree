"""Main application window — refactored from the old ``CalendarWidget``.

This is the orchestrator. It owns the toolbar (with the month/week toggle),
the active calendar view (``MonthView`` or ``WeekView``), and all the
cross-cutting logic that used to live inside the monolithic ``CalendarWidget``:
refresh, auth guidance, settings, export, search, add/delete, theme, pin,
window drag/resize and geometry persistence.

UX principles (v2.1+):
- 启动不弹窗：未登录 / 未装 lark-cli / 加载中 / 出错都以内联状态面板呈现；
- 反馈不弹窗：成功 / 失败 / 警告统一走底部 Toast，危险操作才用 ConfirmDialog；
- 登录态持久：凭据由 lark-cli 全局保存，应用重启直接拉取日程，绝不强制重登；
- 头部按钮收敛：搜索 / 导出 / 置顶 / 主题 / 设置收进「⋯」溢出菜单。

It does **not** touch the Feishu read/write layer
(``lark_cli.py`` / ``lark_cli_async.py``).
"""

import shutil
from datetime import datetime, timedelta

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from add_event_dialog import AddEventDialog
from app_icon import create_app_icon, create_app_logo_pixmap
from config import Config
from day_detail_dialog import DayDetailDialog
from event_detail_dialog import EventDetailDialog
from export_dialog import ExportDialog
from lark_cli_async import LarkCliAsync
from login_dialog import LoginDialog, mark_authed
from month_view import MonthView
from search_dialog import SearchDialog
from settings_dialog import SettingsDialog
from styles import get_theme
from ui_common import ConfirmDialog, Toast
from week_view import WeekView

WEEKDAY_NAMES = ["一", "二", "三", "四", "五", "六", "日"]
HEADER_TITLE_MIN_WIDTH = 480

# 错误信息中出现这些关键词时，判定为授权问题，引导重新登录
_AUTH_KEYWORDS = (
    "scope", "auth", "unauthorized", "token", "credential", "login",
    "授权", "登录", "登陆", "认证", "身份",
)


def _is_auth_error(error_msg: str) -> bool:
    text = (error_msg or "").lower()
    return any(k in text for k in _AUTH_KEYWORDS)


def _short_error(error_msg: str, limit: int = 120) -> str:
    """把可能很长的 CLI 错误压缩成适合 Toast 的一行。"""
    line = next((ln.strip() for ln in (error_msg or "").splitlines() if ln.strip()), "未知错误")
    return line if len(line) <= limit else line[:limit] + "…"


class MainWindow(QMainWindow):
    """Borderless, always-on-top desktop calendar with month/week views."""

    def __init__(self, config: Config, parent=None):
        super().__init__(parent)
        self.config = config
        self.lark_cli = LarkCliAsync(config, self)
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.events: list[dict] = []
        self._view_mode = self.config.get("view_mode", "month")
        if self._view_mode not in ("month", "week"):
            self._view_mode = "month"
        self._drag_offset: QPoint | None = None
        self._pinned = self.config.get("pin_to_top", True)
        self._cli_available = shutil.which("lark-cli") is not None
        self._first_load_done = False
        self._auth_mode = "welcome"

        self._geometry_save_timer = QTimer(self)
        self._geometry_save_timer.setSingleShot(True)
        self._geometry_save_timer.setInterval(250)
        self._geometry_save_timer.timeout.connect(self._persist_geometry)

        # Connect async signals
        self.lark_cli.agenda_fetched.connect(self._on_events_fetched)
        self.lark_cli.fetch_error.connect(self._on_fetch_error)
        self.lark_cli.event_deleted.connect(self._on_deleted)
        self.lark_cli.delete_error.connect(self._on_delete_error)
        self.lark_cli.event_updated.connect(self._on_event_updated)
        self.lark_cli.update_error.connect(self._on_update_error)
        # event_created / create_error 由新建对话框自行处理（含内联错误），
        # 对话框接受后会通过其 event_created 信号触发这里的刷新。

        self._setup_window()
        self._setup_ui()
        self._apply_theme()
        self._setup_timer()
        self._resize_grip_size = 16
        # 启动直接拉取日程；加载过程用内联面板反馈，不弹任何模态框
        self._show_loading()
        self.refresh_events()

    # ── Window setup ──

    def _setup_window(self):
        self.setWindowTitle("飞书日程")
        self.setWindowIcon(create_app_icon())
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self._pinned:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        w = max(self.config.get("window_width", 480), 440)
        h = self.config.get("window_height", 640)
        self.setMinimumSize(440, 480)
        self.resize(w, h)
        self.move(self.config.get("window_x", 100), self.config.get("window_y", 100))
        self.setWindowOpacity(float(self.config.get("opacity", 1.0)))

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_month_bar())

        # Views
        self.month_view = MonthView(self.config, self)
        self.week_view = WeekView(self.config, self)
        for view in (self.month_view, self.week_view):
            view.event_clicked.connect(self._show_event_detail)
            view.add_event_for_date.connect(self._on_add_event_for_date)
            view.reschedule_requested.connect(self._on_reschedule)
        self.month_view.day_activated.connect(self._show_day_detail)
        self.week_view.event_delete_requested.connect(self._confirm_delete)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.month_view)   # 0
        self.stack.addWidget(self.week_view)    # 1
        self.stack.addWidget(self._build_loading_panel())  # 2
        self.stack.addWidget(self._build_auth_panel())     # 3
        self.stack.addWidget(self._build_error_panel())    # 4
        layout.addWidget(self.stack, 1)

        self.status_label = QLabel("准备就绪")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setContentsMargins(0, 3, 0, 4)
        layout.addWidget(self.status_label)

        self.resize_grip = QLabel("⇲")
        self.resize_grip.setObjectName("resizeGrip")
        self.resize_grip.setFixedSize(16, 16)
        self.resize_grip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grip_layout = QHBoxLayout()
        grip_layout.setContentsMargins(0, 0, 4, 2)
        grip_layout.addStretch()
        grip_layout.addWidget(self.resize_grip)
        layout.addLayout(grip_layout)

        # Toast 浮在主窗口底部
        self.toast = Toast(self)

        self._apply_view_mode()
        self._update_compact_header()

    def _build_header(self) -> QWidget:
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(56)
        h = QHBoxLayout(header)
        h.setContentsMargins(10, 6, 8, 6)
        h.setSpacing(3)

        self.header_logo = QLabel()
        self.header_logo.setObjectName("headerLogo")
        self.header_logo.setFixedSize(44, 44)
        self.header_logo.setPixmap(create_app_logo_pixmap(40))
        self.header_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header_logo.setToolTip("飞书日程")
        h.addWidget(self.header_logo)

        self.header_title = QLabel("飞书日程")
        self.header_title.setObjectName("headerTitle")
        h.addWidget(self.header_title)
        h.addStretch()

        # Month / Week segmented control
        segmented = QFrame()
        segmented.setObjectName("segmented")
        seg_layout = QHBoxLayout(segmented)
        seg_layout.setContentsMargins(2, 2, 2, 2)
        seg_layout.setSpacing(0)

        self.month_toggle = QPushButton("月")
        self.month_toggle.setObjectName("toggleBtn")
        self.month_toggle.setToolTip("月视图")
        self.month_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.month_toggle.clicked.connect(lambda: self._set_view_mode("month"))
        seg_layout.addWidget(self.month_toggle)

        self.week_toggle = QPushButton("周")
        self.week_toggle.setObjectName("toggleBtn")
        self.week_toggle.setToolTip("周视图")
        self.week_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.week_toggle.clicked.connect(lambda: self._set_view_mode("week"))
        seg_layout.addWidget(self.week_toggle)
        h.addWidget(segmented)

        h.addSpacing(2)

        self.add_btn = QPushButton("+")
        self.add_btn.setObjectName("addBtn")
        self.add_btn.setToolTip("添加日程")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_event)
        h.addWidget(self.add_btn)

        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setObjectName("iconBtn")
        self.refresh_btn.setToolTip("刷新日程")
        self.refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_events)
        h.addWidget(self.refresh_btn)

        h.addWidget(self._build_more_menu())

        self.min_btn = QPushButton("—")
        self.min_btn.setObjectName("iconBtn")
        self.min_btn.setToolTip("最小化")
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.clicked.connect(self.showMinimized)
        h.addWidget(self.min_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setProperty("class", "iconBtn")
        close_btn.setToolTip("隐藏到系统托盘")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        h.addWidget(close_btn)
        return header

    def _update_compact_header(self):
        """Hide the text title first when the window is at its narrowest."""
        if hasattr(self, "header_title"):
            self.header_title.setVisible(self.width() >= HEADER_TITLE_MIN_WIDTH)

    def _build_more_menu(self) -> QToolButton:
        """溢出菜单：搜索 / 导出 / 置顶 / 主题 / 设置。"""
        self.more_btn = QToolButton()
        self.more_btn.setObjectName("iconBtn")
        self.more_btn.setText("⋯")
        self.more_btn.setToolTip("更多操作")
        self.more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        menu = QMenu(self)
        menu.setObjectName("appMenu")
        search_action = menu.addAction("搜索日程")
        search_action.triggered.connect(self._on_search)
        export_action = menu.addAction("导出到 Excel")
        export_action.triggered.connect(self._on_export)
        menu.addSeparator()

        self.pin_action = QAction("窗口置顶", self)
        self.pin_action.setCheckable(True)
        self.pin_action.setChecked(self._pinned)
        self.pin_action.triggered.connect(lambda checked: self._set_pinned(checked))
        menu.addAction(self.pin_action)

        self.theme_action = QAction("深色主题", self)
        self.theme_action.setCheckable(True)
        self.theme_action.setChecked(self.config.get("theme", "light") == "dark")
        self.theme_action.triggered.connect(self._set_dark_theme)
        menu.addAction(self.theme_action)
        menu.addSeparator()

        login_action = menu.addAction("登录 / 重新登录")
        login_action.triggered.connect(self.open_login)
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(self._on_settings)

        menu.aboutToShow.connect(self._sync_menu)
        self.more_btn.setMenu(menu)
        return self.more_btn

    def _sync_menu(self):
        self.pin_action.setChecked(self._pinned)
        self.theme_action.setChecked(self.config.get("theme", "light") == "dark")
        # QSS 对 QMenu::indicator 支持有限，用文本勾号直观呈现开关状态
        self.pin_action.setText(("✓ " if self._pinned else "    ") + "窗口置顶")
        dark = self.config.get("theme", "light") == "dark"
        self.theme_action.setText(("✓ " if dark else "    ") + "深色主题")

    def _build_month_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("monthBar")
        bar.setFixedHeight(34)
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 2, 10, 2)
        h.setSpacing(4)

        prev_btn = QPushButton("‹")
        prev_btn.setObjectName("iconBtn")
        prev_btn.setToolTip("上一个")
        prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        prev_btn.clicked.connect(lambda: self._change_period(-1))
        h.addWidget(prev_btn)

        self.date_label = QLabel()
        self.date_label.setObjectName("headerDate")
        self.date_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h.addWidget(self.date_label, 1)

        next_btn = QPushButton("›")
        next_btn.setObjectName("iconBtn")
        next_btn.setToolTip("下一个")
        next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        next_btn.clicked.connect(lambda: self._change_period(1))
        h.addWidget(next_btn)

        today_btn = QPushButton("今天")
        today_btn.setObjectName("todayBtn")
        today_btn.setToolTip("回到今天")
        today_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        today_btn.clicked.connect(self._go_today)
        h.addWidget(today_btn)

        self._update_period_label()
        return bar

    # ── State panels (loading / login guidance / error) ──

    def _build_loading_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addStretch()

        self.loading_bar = QProgressBar()
        self.loading_bar.setRange(0, 0)  # 不确定进度（忙碌指示）
        self.loading_bar.setFixedWidth(160)
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(self.loading_bar)
        row.addStretch()
        layout.addLayout(row)

        title = QLabel("正在连接飞书")
        title.setObjectName("stateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        msg = QLabel("正在同步最新日程，请稍候…")
        msg.setObjectName("stateMessage")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(msg)
        layout.addStretch(2)
        return panel

    def _build_auth_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addStretch()

        badge = QLabel("日")
        badge.setObjectName("loginBadge")
        badge.setFixedSize(56, 56)
        badge_row = QHBoxLayout()
        badge_row.addStretch()
        badge_row.addWidget(badge)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        self.auth_title = QLabel("登录飞书账号")
        self.auth_title.setObjectName("stateTitle")
        self.auth_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.auth_title)

        self.auth_message = QLabel("")
        self.auth_message.setObjectName("stateMessage")
        self.auth_message.setWordWrap(True)
        self.auth_message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.auth_message)

        self.auth_detail = QTextEdit()
        self.auth_detail.setObjectName("stateDetail")
        self.auth_detail.setReadOnly(True)
        self.auth_detail.setFixedHeight(56)
        self.auth_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.auth_detail.setVisible(False)
        layout.addWidget(self.auth_detail)

        self.auth_primary_btn = QPushButton("登录飞书")
        self.auth_primary_btn.setObjectName("primaryBtn")
        self.auth_primary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auth_primary_btn.clicked.connect(self._on_auth_primary)
        row1 = QHBoxLayout()
        row1.addStretch()
        self.auth_primary_btn.setFixedWidth(180)
        row1.addWidget(self.auth_primary_btn)
        row1.addStretch()
        layout.addLayout(row1)

        self.auth_secondary_btn = QPushButton("")
        self.auth_secondary_btn.setObjectName("secondaryBtn")
        self.auth_secondary_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.auth_secondary_btn.setVisible(False)
        self.auth_secondary_btn.clicked.connect(self._on_auth_secondary)
        row2 = QHBoxLayout()
        row2.addStretch()
        self.auth_secondary_btn.setFixedWidth(180)
        row2.addWidget(self.auth_secondary_btn)
        row2.addStretch()
        layout.addLayout(row2)

        layout.addStretch(2)
        return panel

    def _build_error_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)
        layout.addStretch()

        icon = QLabel("!")
        icon.setObjectName("stateIcon")
        icon.setFixedSize(56, 56)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(
            "border-radius: 28px; background-color: rgba(245,74,69,0.12);"
            "color: #F54A45; font-size: 26px; font-weight: 700;"
        )
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(icon)
        row.addStretch()
        layout.addLayout(row)

        title = QLabel("暂时无法获取日程")
        title.setObjectName("stateTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        hint = QLabel("网络或飞书连接出现问题，可稍后重试；若持续失败请重新登录。")
        hint.setObjectName("stateMessage")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.error_detail = QTextEdit()
        self.error_detail.setObjectName("stateDetail")
        self.error_detail.setReadOnly(True)
        self.error_detail.setFixedHeight(120)
        self.error_detail.setVisible(False)
        layout.addWidget(self.error_detail)

        detail_btn = QPushButton("查看错误详情")
        detail_btn.setObjectName("linkBtn")
        detail_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._detail_expanded = False

        def toggle_detail():
            self._detail_expanded = not self._detail_expanded
            self.error_detail.setVisible(self._detail_expanded)
            detail_btn.setText("收起错误详情" if self._detail_expanded else "查看错误详情")

        detail_btn.clicked.connect(toggle_detail)
        dr = QHBoxLayout()
        dr.addStretch()
        dr.addWidget(detail_btn)
        dr.addStretch()
        layout.addLayout(dr)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        relogin_btn = QPushButton("重新登录")
        relogin_btn.setObjectName("secondaryBtn")
        relogin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        relogin_btn.clicked.connect(self.open_login)
        btn_row.addWidget(relogin_btn)
        retry_btn = QPushButton("重试")
        retry_btn.setObjectName("primaryBtn")
        retry_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        retry_btn.clicked.connect(self.refresh_events)
        btn_row.addWidget(retry_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch(2)
        return panel

    def _show_loading(self):
        self.stack.setCurrentIndex(2)

    def _show_calendar_view(self):
        self.stack.setCurrentIndex(0 if self._view_mode == "month" else 1)

    def _show_auth(self, mode: str):
        """mode: welcome（首次）/ expired（过期）/ no_cli（未安装 CLI）。"""
        self._auth_mode = mode
        self.auth_detail.setVisible(False)
        self.auth_secondary_btn.setVisible(False)
        if mode == "no_cli":
            self.auth_title.setText("需要先安装 lark-cli")
            self.auth_message.setText(
                "本应用通过飞书官方 lark-cli 读取日历。\n"
                "请在终端执行下面的命令安装，安装后点击重试："
            )
            self.auth_detail.setObjectName("codeBox")
            self.auth_detail.setPlainText("npm install -g @larksuite/cli")
            self.auth_detail.setVisible(True)
            self.auth_primary_btn.setText("复制安装命令")
            self.auth_secondary_btn.setText("我已安装，重试")
            self.auth_secondary_btn.setVisible(True)
        elif mode == "expired":
            self.auth_title.setText("登录已过期")
            self.auth_message.setText("飞书授权已失效，重新登录后即可继续同步日程。\n登录一次即可长期保持，重启应用无需重复登录。")
            self.auth_primary_btn.setText("重新登录")
        else:
            self.auth_title.setText("登录飞书账号")
            self.auth_message.setText("使用飞书 App 扫码或在浏览器中授权日历权限。\n登录一次即可长期保持，重启应用无需重复登录。")
            self.auth_primary_btn.setText("登录飞书")
        # 切换 objectName 后需重新抛光以使 QSS 生效
        self.auth_detail.style().unpolish(self.auth_detail)
        self.auth_detail.style().polish(self.auth_detail)
        self.stack.setCurrentIndex(3)

    def _show_error(self, error_msg: str):
        self.error_detail.setPlainText(error_msg or "未知错误")
        self.error_detail.setVisible(False)
        self._detail_expanded = False
        self.stack.setCurrentIndex(4)

    def _on_auth_primary(self):
        if self._auth_mode == "no_cli":
            QApplication.clipboard().setText("npm install -g @larksuite/cli")
            self.toast.show_message("安装命令已复制到剪贴板", kind="success")
            return
        self.open_login()

    def _on_auth_secondary(self):
        if self._auth_mode == "no_cli":
            self._cli_available = shutil.which("lark-cli") is not None
            if self._cli_available:
                self.toast.show_message("已检测到 lark-cli", kind="success")
                self._show_loading()
                self.refresh_events()
            else:
                self.toast.show_message("仍未检测到 lark-cli，请确认安装成功", kind="warning")

    # ── View mode ──

    def _set_view_mode(self, mode: str):
        if mode == self._view_mode:
            return
        self._view_mode = mode
        self.config.set("view_mode", mode)
        self._apply_view_mode()
        self._render_active_view()

    def _apply_view_mode(self):
        self.month_toggle.setObjectName("toggleBtnActive" if self._view_mode == "month" else "toggleBtn")
        self.week_toggle.setObjectName("toggleBtnActive" if self._view_mode == "week" else "toggleBtn")
        self.month_toggle.setStyle(self.month_toggle.style())
        self.week_toggle.setStyle(self.week_toggle.style())
        if self.stack.currentIndex() in (0, 1):
            self.stack.setCurrentIndex(0 if self._view_mode == "month" else 1)
        self._update_period_label()

    def _active_view(self):
        return self.month_view if self._view_mode == "month" else self.week_view

    def _render_active_view(self):
        self._active_view().set_events(self.events, self.current_date)

    # ── Period navigation ──

    def _change_period(self, delta: int):
        if self._view_mode == "month":
            if delta > 0:
                if self.current_date.month == 12:
                    self.current_date = self.current_date.replace(year=self.current_date.year + 1, month=1)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month + 1)
            else:
                if self.current_date.month == 1:
                    self.current_date = self.current_date.replace(year=self.current_date.year - 1, month=12)
                else:
                    self.current_date = self.current_date.replace(month=self.current_date.month - 1)
        else:  # week
            self.current_date += timedelta(weeks=delta)
        self._update_period_label()
        self.refresh_events()

    def _go_today(self):
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self._update_period_label()
        self.refresh_events()

    def _update_period_label(self):
        if self._view_mode == "month":
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            is_current = self.current_date.year == today.year and self.current_date.month == today.month
            month_str = self.current_date.strftime("%Y年%m月")
            self.date_label.setText("本月  " + month_str if is_current else month_str)
        else:
            monday = self.current_date - timedelta(days=self.current_date.weekday())
            sunday = monday + timedelta(days=6)
            self.date_label.setText(f"{monday.strftime('%m/%d')} - {sunday.strftime('%m/%d')}")

    # ── Theme / pin / settings ──

    def _apply_theme(self):
        # 应用到 application 级别：登录框等独立顶层窗口即便没有父窗口也能统一风格
        qss = get_theme(self.config.get("theme", "light"))
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(qss)
        else:
            self.setStyleSheet(qss)

    def _toggle_theme(self):
        cur = self.config.get("theme", "light")
        self.config.set("theme", "light" if cur == "dark" else "dark")
        self._apply_theme()

    def _set_dark_theme(self, dark: bool):
        self.config.set("theme", "dark" if dark else "light")
        self._apply_theme()

    def _set_pinned(self, pinned: bool):
        self._pinned = pinned
        self.config.set("pin_to_top", pinned)
        if pinned:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _toggle_pin(self):
        self._set_pinned(not self._pinned)

    def _on_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.login_succeeded.connect(self._on_settings_login)
        dialog.pin_changed.connect(self._on_pin_setting_changed)
        dialog.exec()

    def _on_settings_login(self):
        self._cli_available = True
        self.toast.show_message("登录成功，正在同步日程…", kind="success")
        self._show_loading()
        self.refresh_events()

    def _on_settings_changed(self):
        # 外观 / 定时器等设置变化：即时生效，无需重新拉取数据
        self.setWindowOpacity(float(self.config.get("opacity", 1.0)))
        self._apply_theme()
        self.refresh_timer.setInterval(self.config.get("auto_refresh_interval", 300) * 1000)

    def _on_pin_setting_changed(self, pinned: bool):
        self._set_pinned(pinned)

    def _setup_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_events)
        self.refresh_timer.start(self.config.get("auto_refresh_interval", 300) * 1000)

    # ── Login ──

    def open_login(self):
        """打开应用内扫码登录；成功后自动刷新，重启后由 lark-cli 保持登录态。"""
        dialog = LoginDialog(self, config=self.config)
        if dialog.exec() == LoginDialog.DialogCode.Accepted:
            self._cli_available = True
            self.toast.show_message("登录成功，正在同步日程…", kind="success")
            self._show_loading()
            self.refresh_events()

    # ── Refresh / fetch ──

    def refresh_events(self):
        self.status_label.setText("正在获取日程…")
        self.refresh_btn.setEnabled(False)
        if not self._first_load_done and self.stack.currentIndex() not in (3, 4):
            self._show_loading()
        self.lark_cli.fetch_agenda(self.current_date, monthly=True)

    def _on_events_fetched(self, events: list):
        self._first_load_done = True
        self.events = events
        # 能成功拉取日程即说明授权有效，持久化登录态，重启不再引导登录
        mark_authed(self.config)
        self._show_calendar_view()
        self._render_active_view()
        count = len(events)
        if count == 0:
            self.status_label.setText("当前范围无日程")
        else:
            self.status_label.setText(f"共 {count} 项日程  |  更新于 {datetime.now().strftime('%H:%M')}")
        self.refresh_btn.setEnabled(True)

    def _on_fetch_error(self, error_msg: str):
        self.refresh_btn.setEnabled(True)
        self.status_label.setText("获取失败")
        if not self._cli_available:
            self._show_auth("no_cli")
            return
        if _is_auth_error(error_msg):
            mode = "welcome" if not self.config.get("auth_completed") else "expired"
            self._show_auth(mode)
            return
        # 首次加载失败才用错误面板占位；后台自动刷新失败仅用 Toast 轻提示
        if not self._first_load_done:
            self._show_error(error_msg)
        else:
            self.toast.show_message(f"日程刷新失败：{_short_error(error_msg)}", kind="error",
                                    action_text="重试", on_action=self.refresh_events, duration=5000)

    # ── Drag to reschedule ──

    def _on_reschedule(self, event_id: str, new_date: datetime, start_iso: str, end_iso: str, is_recurring: bool):
        if is_recurring:
            self.toast.show_message("重复日程暂不支持拖拽改期，可在日程详情中编辑", kind="warning")
            return
        try:
            start = datetime.fromisoformat(start_iso)
            end = datetime.fromisoformat(end_iso)
        except ValueError:
            return
        duration = end - start
        new_start = datetime(new_date.year, new_date.month, new_date.day, start.hour, start.minute, start.second)
        new_end = new_start + duration
        self.status_label.setText("正在改期…")
        self.lark_cli.update_event(
            calendar_id=next(
                (e.get("organizer_calendar_id", "primary") for e in self.events if e.get("event_id") == event_id),
                "primary",
            ),
            event_id=event_id,
            start=new_start,
            end=new_end,
        )

    def _on_event_updated(self, data: dict):
        self.status_label.setText("已更新")
        # 详情对话框仍打开时（如勾选子任务），反馈由对话框内联承担，不弹 Toast
        if QApplication.activeModalWidget() is None:
            self.toast.show_message("日程已更新", kind="success")
        self.refresh_events()

    def _on_update_error(self, error_msg: str):
        self.status_label.setText("更新失败")
        if QApplication.activeModalWidget() is None:
            self.toast.show_message(f"更新失败：{_short_error(error_msg)}", kind="error", duration=5000)

    # ── Detail / day dialogs ──

    def _show_event_detail(self, event: dict):
        dialog = EventDetailDialog(event, self.lark_cli, self, config=self.config)
        dialog.event_delete_requested.connect(self._confirm_delete)
        # 保存成功由 lark_cli.event_updated 统一处理（Toast + 刷新）
        dialog.exec()

    def _show_day_detail(self, date: datetime):
        day_events = self.month_view.events_for_date(date)
        dialog = DayDetailDialog(date, day_events, self.lark_cli, self, config=self.config)
        dialog.event_delete_requested.connect(self._confirm_delete)
        dialog.exec()

    def _on_add_event(self):
        dialog = AddEventDialog(self.lark_cli, self, config=self.config)
        dialog.event_created.connect(lambda: self.refresh_events())
        dialog.exec()

    def _on_add_event_for_date(self, date: datetime):
        dialog = AddEventDialog(self.lark_cli, self, default_date=date, config=self.config)
        dialog.event_created.connect(lambda: self.refresh_events())
        dialog.exec()

    def _on_export(self):
        if not self.events:
            self.toast.show_message("当前范围没有日程可导出", kind="info")
            return
        dialog = ExportDialog(self.events, self.current_date, self)
        dialog.export_done.connect(self._on_export_done)
        dialog.exec()

    def _on_export_done(self, ok: bool, info: str):
        if ok:
            import os
            folder = os.path.dirname(info)
            self.toast.show_message(
                f"已导出到：{os.path.basename(info)}",
                kind="success",
                action_text="打开文件夹",
                on_action=lambda: self._open_folder(folder),
                duration=5000,
            )
        else:
            self.toast.show_message("导出失败，请检查文件是否被占用", kind="error", duration=5000)

    @staticmethod
    def _open_folder(path: str):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def _on_search(self):
        dialog = SearchDialog(self.lark_cli, self)
        dialog.event_selected.connect(self._on_search_result_selected)
        dialog.exec()

    def _on_search_result_selected(self, event: dict):
        start = parse_event_time_compat(event)
        self.current_date = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        self._update_period_label()
        self.refresh_events()
        self._show_day_detail(start)

    # ── Delete ──

    def _confirm_delete(self, event: dict):
        summary = event.get("summary", "(无标题)")
        ok = ConfirmDialog.ask(
            self,
            "删除日程",
            f"确定要删除日程「{summary}」吗？\n删除后无法恢复。",
            ok_text="删除",
            danger=True,
        )
        if ok:
            self._delete_event(event)

    def _delete_event(self, event: dict):
        self.status_label.setText("正在删除…")
        event_id = event.get("event_id", "")
        calendar_id = event.get("organizer_calendar_id", "primary")
        self.lark_cli.delete_event(calendar_id=calendar_id, event_id=event_id)

    def _on_deleted(self, event_id: str):
        self.status_label.setText("日程已删除")
        self.toast.show_message("日程已删除", kind="success")
        self.refresh_events()

    def _on_delete_error(self, error_msg: str):
        self.status_label.setText("删除失败")
        self.toast.show_message(f"删除失败：{_short_error(error_msg)}", kind="error", duration=5000)

    # ── Update notification ──

    def notify_update(self, release: dict):
        """启动后台检查发现新版本时，以 Toast 轻提示代替模态弹窗。"""
        tag = (release.get("tag") or "").lstrip("vV")
        if not tag:
            return

        def open_dialog():
            import updater
            from update_dialog import UpdateDialog
            dlg = UpdateDialog(release, updater.APP_VERSION, self)
            dlg.exec()

        self.toast.show_message(
            f"发现新版本 v{tag}",
            kind="info",
            action_text="查看",
            on_action=open_dialog,
            duration=8000,
        )

    # ── Window dragging & resizing ──

    def _is_in_resize_grip(self, pos) -> bool:
        rect = self.rect()
        return (
            pos.x() >= rect.width() - self._resize_grip_size
            and pos.y() >= rect.height() - self._resize_grip_size
        )

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MouseButton.LeftButton:
            pos = ev.position()
            if self._is_in_resize_grip(pos):
                self._resize_start = ev.globalPosition().toPoint()
                self._resize_start_size = self.size()
                self._resizing = True
                ev.accept()
                return
            if pos.y() <= 78:
                self._drag_offset = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
                ev.accept()

    def mouseMoveEvent(self, ev: QMouseEvent):
        if getattr(self, "_resizing", False) and ev.buttons() & Qt.MouseButton.LeftButton:
            delta = ev.globalPosition().toPoint() - self._resize_start
            new_w = max(self.minimumWidth(), self._resize_start_size.width() + delta.x())
            new_h = max(self.minimumHeight(), self._resize_start_size.height() + delta.y())
            self.resize(new_w, new_h)
            ev.accept()
            return
        if self._drag_offset is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_offset)
            ev.accept()

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if getattr(self, "_resizing", False):
            self._resizing = False
            self._save_window_size()
            ev.accept()
            return
        if self._drag_offset is not None:
            self._drag_offset = None
            pos = self.pos()
            self.config.set("window_x", pos.x())
            self.config.set("window_y", pos.y())
            ev.accept()

    def resizeEvent(self, ev):
        self._update_compact_header()
        self._save_window_size()
        super().resizeEvent(ev)

    def _save_window_size(self):
        self._geometry_save_timer.start()

    def _persist_geometry(self):
        self.config.set("window_width", self.width())
        self.config.set("window_height", self.height())

    def closeEvent(self, ev):
        pos = self.pos()
        self.config.set("window_x", pos.x())
        self.config.set("window_y", pos.y())
        super().closeEvent(ev)


def parse_event_time_compat(event: dict) -> datetime:
    """Parse an event's start time for navigation (uses models_event helper)."""
    from models_event import parse_event_time

    return parse_event_time(event.get("start_time", {}))
