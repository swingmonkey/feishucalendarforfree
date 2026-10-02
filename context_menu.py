"""右键菜单构建。

此前全项目没有任何 ``setContextMenuPolicy`` / ``contextMenuEvent``，
右键在所有控件上都是死的：查看、编辑、删除、复制、改颜色都得先点开
模态详情框。这里把「事件菜单 / 日格菜单 / 窗口空白菜单」集中成三个
构造函数，保证两个视图和主窗口的措辞、分隔线、危险项位置完全一致。
"""

from datetime import datetime

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

from models_event import PALETTE, get_event_color

MENU_OBJECT_NAME = "appMenu"


def _new_menu(parent) -> QMenu:
    menu = QMenu(parent)
    menu.setObjectName(MENU_OBJECT_NAME)
    return menu


def _weekday_cn(date: datetime) -> str:
    return "一二三四五六日"[date.weekday()]


def build_event_menu(
    parent,
    event: dict,
    config=None,
    *,
    on_open=None,
    on_duplicate=None,
    on_delete=None,
    on_set_color=None,
) -> QMenu:
    """单个日程的右键菜单。

    ``on_open`` 查看/编辑、``on_duplicate`` 复制一份、``on_delete`` 删除，
    颜色子菜单直接写本地 ``config.event_colors``（仅本地显示，不写回飞书）。
    """
    menu = _new_menu(parent)
    summary = event.get("summary", "")
    if not isinstance(summary, str):
        summary = str(summary)
    title = summary or "(无标题)"
    if len(title) > 18:
        title = title[:18] + "…"

    if on_open is not None:
        act = menu.addAction("查看 / 编辑")
        act.triggered.connect(on_open)
    if on_duplicate is not None:
        act = menu.addAction(f"复制日程（{title}）")
        act.triggered.connect(on_duplicate)

    event_id = event.get("event_id", "")
    if on_set_color is not None and event_id:
        color_menu = menu.addMenu("颜色")
        color_menu.setObjectName(MENU_OBJECT_NAME)
        group = QActionGroup(color_menu)
        group.setExclusive(True)
        current = get_event_color(config, event_id)

        clear = QAction("无颜色", color_menu)
        clear.setCheckable(True)
        clear.setChecked(not current)
        clear.triggered.connect(lambda: on_set_color(""))
        group.addAction(clear)
        color_menu.addAction(clear)

        for name, hex_value in PALETTE:
            act = QAction(name, color_menu)
            act.setCheckable(True)
            act.setChecked(current == hex_value)
            act.triggered.connect(lambda _checked=False, hex=hex_value: on_set_color(hex))
            group.addAction(act)
            color_menu.addAction(act)

    if on_delete is not None:
        menu.addSeparator()
        act = menu.addAction("删除日程")
        act.triggered.connect(on_delete)
    return menu


def build_day_menu(
    parent,
    date: datetime,
    *,
    has_events: bool = False,
    on_add=None,
    on_open_day=None,
    on_today=None,
) -> QMenu:
    """日格空白处的右键菜单。"""
    menu = _new_menu(parent)
    label = f"{date.month}月{date.day}日（周{_weekday_cn(date)}）"

    if on_add is not None:
        act = menu.addAction(f"新建日程  {label}")
        act.triggered.connect(on_add)
    if on_open_day is not None:
        act = menu.addAction(f"查看当日日程  {label}")
        act.setEnabled(bool(has_events))
        act.triggered.connect(on_open_day)

    if on_today is not None:
        menu.addSeparator()
        act = menu.addAction("回到今天")
        act.triggered.connect(on_today)
    return menu


def build_background_menu(
    parent,
    *,
    view_mode: str = "month",
    pinned: bool = False,
    on_add=None,
    on_refresh=None,
    on_today=None,
    on_set_view=None,
    on_toggle_pin=None,
    on_settings=None,
    on_search=None,
) -> QMenu:
    """主窗口空白处（非日程）的右键菜单。"""
    menu = _new_menu(parent)

    if on_add is not None:
        act = menu.addAction("新建日程  (N)")
        act.triggered.connect(on_add)
    if on_search is not None:
        act = menu.addAction("搜索日程  (F)")
        act.triggered.connect(on_search)
    if on_refresh is not None:
        act = menu.addAction("刷新日程  (R)")
        act.triggered.connect(on_refresh)
    if on_today is not None:
        act = menu.addAction("回到今天  (T)")
        act.triggered.connect(on_today)

    if on_set_view is not None:
        menu.addSeparator()
        group = QActionGroup(menu)
        group.setExclusive(True)
        for mode, text, key in (("month", "月视图", "M"), ("week", "周视图", "W")):
            act = QAction(f"{text}  ({key})", menu)
            act.setCheckable(True)
            act.setChecked(view_mode == mode)
            act.triggered.connect(lambda _checked=False, m=mode: on_set_view(m))
            group.addAction(act)
            menu.addAction(act)

    if on_toggle_pin is not None or on_settings is not None:
        menu.addSeparator()
    if on_toggle_pin is not None:
        act = QAction("窗口置顶", menu)
        act.setCheckable(True)
        act.setChecked(bool(pinned))
        act.triggered.connect(on_toggle_pin)
        menu.addAction(act)
    if on_settings is not None:
        act = menu.addAction("设置…")
        act.triggered.connect(on_settings)
    return menu
