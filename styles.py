# -*- coding: utf-8 -*-
"""QSS stylesheets for FeishuCalendarDesktop - 飞书（Lark）设计规范。

色板取自飞书开放平台「小程序设计规范 - 视觉规范」：
  Brand:  #3370FF (primary), #306EFF (hover), #245BDB (active)
  Neutral (N 系列灰阶，浅→深): N50 #FFFFFF, N100 #F5F6F7, N200 #F2F3F5,
          N300 #DEE0E3, N400 #D0D3D6, N500 #BBBFC4, N600 #8F959E,
          N700 #646A73, N800 #51565D, N900 #1F2329
  文字规则: 一级标题/正文 N900；二级标题/正文 N600；辅助信息 N500；Disable N400
  图标规则: 一级 N800；二级 N600；三级 N500；Disable N400
  背景: N50 / N100 / N200；可交互控件描边 N400；卡片描边 N300
  分割线: N900 15% 透明度；Hover N900 8%；Press N900 12%
  Status: #3370FF (info/link), #34C724 (success), #FF8800 (warning), #F54A45 (error)
  间距: 4px 为基准单位扩展；按钮桌面端高度 40/36/32/24px
"""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #1F2329;
    color: #F5F6F7;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 600;
    color: #FFFFFF;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #8F959E;
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #8F959E;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: rgba(245, 246, 247, 0.08);
    color: #F5F6F7;
}
QPushButton#iconBtn:pressed {
    background-color: rgba(245, 246, 247, 0.12);
}

/* === Month grid === */

QLabel#weekDay {
    font-size: 11px;
    color: #8F959E;
    font-weight: 600;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #F54A45;
    font-weight: 600;
}

QFrame#dayCell {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.15);
    border-radius: 6px;
}
QFrame#dayCellHover {
    background-color: #373C43;
    border: 1px solid rgba(51, 112, 255, 0.45);
    border-radius: 6px;
}
QFrame#dayCellOther {
    background-color: #1F2329;
    border: 1px solid rgba(245, 246, 247, 0.08);
    border-radius: 6px;
}
QFrame#dayCellOtherHover {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 6px;
}
QFrame#dayCellToday {
    background-color: #2B2F36;
    border: 2px solid #3370FF;
    border-radius: 6px;
}
QFrame#dayCellTodayHover {
    background-color: #373C43;
    border: 2px solid #4A7EFF;
    border-radius: 6px;
}

QLabel#dayNum {
    font-size: 11px;
    color: #F5F6F7;
    font-weight: 600;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #646A73;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #FFFFFF;
    font-weight: 600;
}

QFrame#gridEvent {
    background-color: rgba(51, 112, 255, 0.22);
    border-radius: 4px;
    border-left: 2px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: rgba(51, 112, 255, 0.35);
    border-left: 2px solid #4A7EFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(52, 199, 36, 0.16);
    border-radius: 4px;
    border-left: 2px solid #34C724;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(52, 199, 36, 0.28);
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #8F959E;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #F5F6F7;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #646A73;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #3370FF;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #2B2F36;
    border-radius: 8px;
    border-left: 3px solid #3370FF;
}
QFrame#eventCardPast {
    background-color: #26282D;
    border-radius: 8px;
    border-left: 3px solid #646A73;
}
QFrame#eventCardCurrent {
    background-color: #24312A;
    border-radius: 8px;
    border-left: 3px solid #34C724;
}
QFrame#eventCard:hover {
    background-color: #373C43;
}

QLabel#eventTime {
    font-size: 11px;
    color: #8F959E;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #646A73;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #34C724;
    font-weight: 600;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #F5F6F7;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #646A73;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #8F959E;
}

QPushButton#deleteBtn {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
    min-width: 22px;
    min-height: 22px;
    max-width: 22px;
    max-height: 22px;
    color: #646A73;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #F54A45;
    color: #FFFFFF;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: rgba(245, 246, 247, 0.36);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(245, 246, 247, 0.55);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 6px;
    padding: 6px 8px;
    color: #F5F6F7;
    selection-background-color: #3370FF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #3370FF;
}

QPushButton#primaryBtn {
    background-color: #3370FF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #306EFF;
}
QPushButton#primaryBtn:pressed {
    background-color: #245BDB;
}
QPushButton#secondaryBtn {
    background-color: rgba(245, 246, 247, 0.08);
    color: #F5F6F7;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(245, 246, 247, 0.15);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #F54A45;
    border: 1px solid #F54A45;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#dangerBtn:hover {
    background-color: #F54A45;
    color: #FFFFFF;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #646A73;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #51565D;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #646A73;
    padding: 40px 20px;
}

QTextEdit#errorDisplay {
    background-color: #2B1F21;
    color: #F5F6F7;
    border: 1px solid rgba(245, 74, 69, 0.35);
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.35);
}

QLineEdit#searchInput {
    background-color: #2B2F36;
    color: #F5F6F7;
    border: 1px solid rgba(51, 112, 255, 0.35);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit#searchInput:focus {
    border: 1px solid #3370FF;
}

QListWidget#searchResultList {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}
QListWidget#searchResultList::item {
    padding: 8px 12px;
    border-radius: 4px;
    color: #F5F6F7;
}
QListWidget#searchResultList::item:hover {
    background-color: rgba(51, 112, 255, 0.20);
}
QListWidget#searchResultList::item:selected {
    background-color: rgba(51, 112, 255, 0.35);
    color: #FFFFFF;
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: 600;
    color: #FFFFFF;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #8F959E;
}
QLabel#detailValue {
    font-size: 13px;
    color: #F5F6F7;
}

QGroupBox {
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 16px;
    color: #8F959E;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QCheckBox {
    color: #F5F6F7;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(245, 246, 247, 0.36);
    border-radius: 4px;
    background: #2B2F36;
}
QCheckBox::indicator:checked {
    background: #3370FF;
    border-color: #3370FF;
}

QSpinBox {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 6px;
    padding: 4px 8px;
    color: #F5F6F7;
}
QSpinBox:focus {
    border: 1px solid #3370FF;
}

QSlider::groove:horizontal {
    background: rgba(245, 246, 247, 0.20);
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #F5F6F7;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid rgba(245, 246, 247, 0.36);
}
QSlider::sub-page:horizontal {
    background: #3370FF;
    border-radius: 2px;
}

QRadioButton {
    color: #F5F6F7;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(245, 246, 247, 0.36);
    border-radius: 8px;
    background: #2B2F36;
}
QRadioButton::indicator:checked {
    border-color: #3370FF;
    background: #2B2F36;
}
QRadioButton::indicator:checked::after {
    width: 10px;
    height: 10px;
    border-radius: 5px;
    background: #3370FF;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #FFFFFF;
    color: #1F2329;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 600;
    color: #1F2329;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #8F959E;
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 4px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #646A73;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: rgba(31, 35, 41, 0.08);
    color: #1F2329;
}
QPushButton#iconBtn:pressed {
    background-color: rgba(31, 35, 41, 0.12);
}

/* === Month grid === */

QLabel#weekDay {
    font-size: 11px;
    color: #8F959E;
    font-weight: 600;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #F54A45;
    font-weight: 600;
}

QFrame#dayCell {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 6px;
}
QFrame#dayCellHover {
    background-color: #F5F6F7;
    border: 1px solid rgba(51, 112, 255, 0.45);
    border-radius: 6px;
}
QFrame#dayCellOther {
    background-color: #F5F6F7;
    border: 1px solid rgba(31, 35, 41, 0.08);
    border-radius: 6px;
}
QFrame#dayCellOtherHover {
    background-color: #F2F3F5;
    border: 1px solid rgba(31, 35, 41, 0.18);
    border-radius: 6px;
}
QFrame#dayCellToday {
    background-color: #FFFFFF;
    border: 2px solid #3370FF;
    border-radius: 6px;
}
QFrame#dayCellTodayHover {
    background-color: #F5F6F7;
    border: 2px solid #4A7EFF;
    border-radius: 6px;
}

QLabel#dayNum {
    font-size: 11px;
    color: #1F2329;
    font-weight: 600;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #BBBFC4;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #3370FF;
    font-weight: 600;
}

QFrame#gridEvent {
    background-color: rgba(51, 112, 255, 0.10);
    border-radius: 4px;
    border-left: 2px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: rgba(51, 112, 255, 0.18);
    border-left: 2px solid #306EFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(52, 199, 36, 0.10);
    border-radius: 4px;
    border-left: 2px solid #34C724;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(52, 199, 36, 0.18);
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #646A73;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #1F2329;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #BBBFC4;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #3370FF;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #F5F6F7;
    border-radius: 8px;
    border-left: 3px solid #3370FF;
}
QFrame#eventCardPast {
    background-color: #F2F3F5;
    border-radius: 8px;
    border-left: 3px solid #D0D3D6;
}
QFrame#eventCardCurrent {
    background-color: #F2FAF1;
    border-radius: 8px;
    border-left: 3px solid #34C724;
}
QFrame#eventCard:hover {
    background-color: rgba(31, 35, 41, 0.08);
}

QLabel#eventTime {
    font-size: 11px;
    color: #646A73;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #BBBFC4;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #34C724;
    font-weight: 600;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #1F2329;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #BBBFC4;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #8F959E;
}

QPushButton#deleteBtn {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px;
    min-width: 22px;
    min-height: 22px;
    max-width: 22px;
    max-height: 22px;
    color: #BBBFC4;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #F54A45;
    color: #FFFFFF;
}

QScrollArea {
    border: none;
    background-color: transparent;
}
QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #D0D3D6;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #BBBFC4;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 6px;
    padding: 6px 8px;
    color: #1F2329;
    selection-background-color: #3370FF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #3370FF;
}

QPushButton#primaryBtn {
    background-color: #3370FF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #306EFF;
}
QPushButton#primaryBtn:pressed {
    background-color: #245BDB;
}
QPushButton#secondaryBtn {
    background-color: rgba(31, 35, 41, 0.06);
    color: #1F2329;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(31, 35, 41, 0.12);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #F54A45;
    border: 1px solid #F54A45;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#dangerBtn:hover {
    background-color: #F54A45;
    color: #FFFFFF;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #8F959E;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #D0D3D6;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #BBBFC4;
    padding: 40px 20px;
}

QTextEdit#errorDisplay {
    background-color: #FDF4F3;
    color: #1F2329;
    border: 1px solid rgba(245, 74, 69, 0.35);
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.20);
}

QLineEdit#searchInput {
    background-color: #FFFFFF;
    color: #1F2329;
    border: 1px solid rgba(51, 112, 255, 0.35);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit#searchInput:focus {
    border: 1px solid #3370FF;
}

QListWidget#searchResultList {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.18);
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}
QListWidget#searchResultList::item {
    padding: 8px 12px;
    border-radius: 4px;
    color: #1F2329;
}
QListWidget#searchResultList::item:hover {
    background-color: rgba(51, 112, 255, 0.10);
}
QListWidget#searchResultList::item:selected {
    background-color: rgba(51, 112, 255, 0.18);
    color: #3370FF;
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: 600;
    color: #1F2329;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #8F959E;
}
QLabel#detailValue {
    font-size: 13px;
    color: #1F2329;
}

QGroupBox {
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 16px;
    color: #51565D;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QCheckBox {
    color: #1F2329;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(31, 35, 41, 0.36);
    border-radius: 4px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #3370FF;
    border-color: #3370FF;
}

QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 6px;
    padding: 4px 8px;
    color: #1F2329;
}
QSpinBox:focus {
    border: 1px solid #3370FF;
}

QSlider::groove:horizontal {
    background: #D0D3D6;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid rgba(31, 35, 41, 0.36);
}
QSlider::sub-page:horizontal {
    background: #3370FF;
    border-radius: 2px;
}

QRadioButton {
    color: #1F2329;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(31, 35, 41, 0.36);
    border-radius: 8px;
    background: #FFFFFF;
}
QRadioButton::indicator:checked {
    border-color: #3370FF;
    background: #FFFFFF;
}
QRadioButton::indicator:checked::after {
    width: 10px;
    height: 10px;
    border-radius: 5px;
    background: #3370FF;
}
"""


def get_theme(name: str) -> str:
    """Get QSS stylesheet by theme name."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
