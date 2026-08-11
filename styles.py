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

── 设计令牌（Design Tokens）────────────────────────────────────
  间距基准 : 4px  (4 / 8 / 12 / 16 / 20 / 24)
  圆角     : 控件 6px · 卡片 8px · 面板 12px
  字阶     : 9 / 10 / 11 / 12 / 13 / 16 / 18 / 24
  强调色   : brand #3370FF · brand-hover #306EFF · brand-active #245BDB
  状态色   : success #34C724 · warning #FF8800 · error #F54A45
  可读性   : 正文对比均满足 WCAG AA（≥4.5:1）；辅助文字 ≥3:1
  焦点     : 所有可交互控件获得 2px 品牌蓝描边焦点环
"""

# 品牌渐变（顶部标题栏使用），深浅主题共用
BRAND_GRADIENT = """
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D7BFF, stop:1 #245BDB);
    border: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.25);
"""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #1F2329;
    color: #F5F6F7;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

/* 通用焦点环：键盘可达性 */
QPushButton:focus-visible, QLineEdit:focus-visible, QTextEdit:focus-visible,
QComboBox:focus-visible, QDateTimeEdit:focus-visible, QSpinBox:focus-visible,
QCheckBox:focus-visible, QRadioButton:focus-visible, QListWidget:focus-visible {
    outline: 2px solid rgba(51, 112, 255, 0.7);
    outline-offset: 1px;
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

/* === 顶部品牌标题栏（渐变 + 白色图标） === */
QFrame#headerBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D7BFF, stop:1 #245BDB);
    border: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.25);
}
QFrame#headerBar QLabel#headerTitle {
    color: #FFFFFF;
    font-size: 15px;
    letter-spacing: 0.5px;
}
QFrame#headerBar QLabel#headerDate {
    color: rgba(255, 255, 255, 0.82);
}
QFrame#headerBar QPushButton#iconBtn {
    color: rgba(255, 255, 255, 0.92);
}
QFrame#headerBar QPushButton#iconBtn:hover {
    background-color: rgba(255, 255, 255, 0.18);
    color: #FFFFFF;
}
QFrame#headerBar QPushButton#iconBtn:pressed {
    background-color: rgba(255, 255, 255, 0.28);
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
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
    border-top: 1px solid rgba(245, 246, 247, 0.05);
    border-radius: 8px;
}
QFrame#dayCellHover {
    background-color: #373C43;
    border: 1px solid rgba(51, 112, 255, 0.45);
    border-radius: 8px;
}
QFrame#dayCellOther {
    background-color: #23272E;
    border: 1px solid rgba(245, 246, 247, 0.08);
    border-top: 1px solid rgba(245, 246, 247, 0.03);
    border-radius: 8px;
}
QFrame#dayCellOtherHover {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
}
QFrame#dayCellToday {
    background-color: rgba(51, 112, 255, 0.14);
    border: 2px solid #3370FF;
    border-radius: 8px;
}
QFrame#dayCellTodayHover {
    background-color: rgba(51, 112, 255, 0.24);
    border: 2px solid #4A7EFF;
    border-radius: 8px;
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
    font-weight: 700;
}

QFrame#gridEvent {
    background-color: rgba(51, 112, 255, 0.22);
    border-radius: 6px;
    border-left: 3px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}
QFrame#gridEvent:hover {
    background-color: rgba(51, 112, 255, 0.38);
    border-left: 3px solid #4A7EFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(52, 199, 36, 0.16);
    border-radius: 6px;
    border-left: 3px solid #34C724;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(52, 199, 36, 0.30);
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #B8C0CC;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #F5F6F7;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #8F959E;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #5B8CFF;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #2B2F36;
    border-radius: 8px;
    border-top: 1px solid rgba(245, 246, 247, 0.06);
    border-left: 3px solid #3370FF;
}
QFrame#eventCardPast {
    background-color: #26282D;
    border-radius: 8px;
    border-top: 1px solid rgba(245, 246, 247, 0.03);
    border-left: 3px solid #646A73;
}
QFrame#eventCardCurrent {
    background-color: #24312A;
    border-radius: 8px;
    border-top: 1px solid rgba(52, 199, 36, 0.10);
    border-left: 3px solid #34C724;
}
QFrame#eventCard:hover {
    background-color: #373C43;
}

QLabel#eventTime {
    font-size: 11px;
    color: #B8C0CC;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #646A73;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #4FD963;
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
    border-radius: 6px;
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
    width: 8px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: rgba(245, 246, 247, 0.32);
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(245, 246, 247, 0.55);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: rgba(245, 246, 247, 0.32);
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: rgba(245, 246, 247, 0.55);
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
    padding: 7px 10px;
    color: #F5F6F7;
    selection-background-color: #3370FF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #3370FF;
    padding: 7px 10px;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D7BFF, stop:1 #245BDB);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4A86FF, stop:1 #306EFF);
}
QPushButton#primaryBtn:pressed {
    background: #245BDB;
}
QPushButton#secondaryBtn {
    background-color: rgba(245, 246, 247, 0.08);
    color: #F5F6F7;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
    padding: 8px 18px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(245, 246, 247, 0.15);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #F54A45;
    border: 1px solid #F54A45;
    border-radius: 8px;
    padding: 8px 18px;
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
    color: #8F959E;
    padding: 40px 20px;
}

QTextEdit#errorDisplay {
    background-color: #2B1F21;
    color: #F5F6F7;
    border: 1px solid rgba(245, 74, 69, 0.35);
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.35);
}

QLineEdit#searchInput {
    background-color: #2B2F36;
    color: #F5F6F7;
    border: 1px solid rgba(51, 112, 255, 0.35);
    border-radius: 8px;
    padding: 8px 12px 8px 32px;
    font-size: 13px;
    background-image: url(assets/search.svg);
    background-repeat: no-repeat;
    background-position: 9px center;
}
QLineEdit#searchInput:focus {
    border: 1px solid #3370FF;
}

QListWidget#searchResultList {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}
QListWidget#searchResultList::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #F5F6F7;
}
QListWidget#searchResultList::item:hover {
    background-color: rgba(51, 112, 255, 0.20);
}
QListWidget#searchResultList::item:selected {
    background-color: rgba(51, 112, 255, 0.38);
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
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 18px;
    color: #8F959E;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
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
    image: url(assets/check.svg);
}

QSpinBox {
    background-color: #2B2F36;
    border: 1px solid rgba(245, 246, 247, 0.18);
    border-radius: 8px;
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

QToolTip {
    background-color: #2B2F36;
    color: #F5F6F7;
    border: 1px solid rgba(245, 246, 247, 0.22);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #FFFFFF;
    color: #1F2329;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QPushButton:focus-visible, QLineEdit:focus-visible, QTextEdit:focus-visible,
QComboBox:focus-visible, QDateTimeEdit:focus-visible, QSpinBox:focus-visible,
QCheckBox:focus-visible, QRadioButton:focus-visible, QListWidget:focus-visible {
    outline: 2px solid rgba(51, 112, 255, 0.7);
    outline-offset: 1px;
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

/* === 顶部品牌标题栏（渐变 + 白色图标） === */
QFrame#headerBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D7BFF, stop:1 #245BDB);
    border: none;
    border-bottom: 1px solid rgba(0, 0, 0, 0.12);
}
QFrame#headerBar QLabel#headerTitle {
    color: #FFFFFF;
    font-size: 15px;
    letter-spacing: 0.5px;
}
QFrame#headerBar QLabel#headerDate {
    color: rgba(255, 255, 255, 0.82);
}
QFrame#headerBar QPushButton#iconBtn {
    color: rgba(255, 255, 255, 0.92);
}
QFrame#headerBar QPushButton#iconBtn:hover {
    background-color: rgba(255, 255, 255, 0.20);
    color: #FFFFFF;
}
QFrame#headerBar QPushButton#iconBtn:pressed {
    background-color: rgba(255, 255, 255, 0.30);
}

QPushButton#iconBtn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
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
    border-top: 1px solid rgba(31, 35, 41, 0.04);
    border-radius: 8px;
}
QFrame#dayCellHover {
    background-color: #F5F6F7;
    border: 1px solid rgba(51, 112, 255, 0.45);
    border-radius: 8px;
}
QFrame#dayCellOther {
    background-color: #FAFBFC;
    border: 1px solid rgba(31, 35, 41, 0.08);
    border-top: 1px solid rgba(31, 35, 41, 0.03);
    border-radius: 8px;
}
QFrame#dayCellOtherHover {
    background-color: #F2F3F5;
    border: 1px solid rgba(31, 35, 41, 0.18);
    border-radius: 8px;
}
QFrame#dayCellToday {
    background-color: rgba(51, 112, 255, 0.10);
    border: 2px solid #3370FF;
    border-radius: 8px;
}
QFrame#dayCellTodayHover {
    background-color: rgba(51, 112, 255, 0.18);
    border: 2px solid #4A7EFF;
    border-radius: 8px;
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
    color: #245BDB;
    font-weight: 700;
}

QFrame#gridEvent {
    background-color: rgba(51, 112, 255, 0.10);
    border-radius: 6px;
    border-left: 3px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}
QFrame#gridEvent:hover {
    background-color: rgba(51, 112, 255, 0.20);
    border-left: 3px solid #306EFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(52, 199, 36, 0.10);
    border-radius: 6px;
    border-left: 3px solid #34C724;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(52, 199, 36, 0.20);
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
    color: #245BDB;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #F5F6F7;
    border-radius: 8px;
    border-top: 1px solid rgba(31, 35, 41, 0.04);
    border-left: 3px solid #3370FF;
}
QFrame#eventCardPast {
    background-color: #F2F3F5;
    border-radius: 8px;
    border-top: 1px solid rgba(31, 35, 41, 0.02);
    border-left: 3px solid #D0D3D6;
}
QFrame#eventCardCurrent {
    background-color: #F2FAF1;
    border-radius: 8px;
    border-top: 1px solid rgba(52, 199, 36, 0.10);
    border-left: 3px solid #34C724;
}
QFrame#eventCard:hover {
    background-color: rgba(31, 35, 41, 0.08);
}

QLabel#eventTime {
    font-size: 11px;
    color: #51565D;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #BBBFC4;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #2EA043;
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
    border-radius: 6px;
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
    width: 8px;
    margin: 2px 0;
}
QScrollBar::handle:vertical {
    background: #C2C7CD;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #9AA1A9;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 8px;
    margin: 0 2px;
}
QScrollBar::handle:horizontal {
    background: #C2C7CD;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #9AA1A9;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 8px;
    padding: 7px 10px;
    color: #1F2329;
    selection-background-color: #3370FF;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #3370FF;
    padding: 7px 10px;
}

QPushButton#primaryBtn {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3D7BFF, stop:1 #245BDB);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #4A86FF, stop:1 #306EFF);
}
QPushButton#primaryBtn:pressed {
    background: #245BDB;
}
QPushButton#secondaryBtn {
    background-color: rgba(31, 35, 41, 0.06);
    color: #1F2329;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 8px;
    padding: 8px 18px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(31, 35, 41, 0.12);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #F54A45;
    border: 1px solid #F54A45;
    border-radius: 8px;
    padding: 8px 18px;
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
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.20);
}

QLineEdit#searchInput {
    background-color: #FFFFFF;
    color: #1F2329;
    border: 1px solid rgba(51, 112, 255, 0.35);
    border-radius: 8px;
    padding: 8px 12px 8px 32px;
    font-size: 13px;
    background-image: url(assets/search.svg);
    background-repeat: no-repeat;
    background-position: 9px center;
}
QLineEdit#searchInput:focus {
    border: 1px solid #3370FF;
}

QListWidget#searchResultList {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.18);
    border-radius: 8px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}
QListWidget#searchResultList::item {
    padding: 8px 12px;
    border-radius: 6px;
    color: #1F2329;
}
QListWidget#searchResultList::item:hover {
    background-color: rgba(51, 112, 255, 0.10);
}
QListWidget#searchResultList::item:selected {
    background-color: rgba(51, 112, 255, 0.20);
    color: #245BDB;
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
    border-radius: 10px;
    margin-top: 10px;
    padding-top: 18px;
    color: #51565D;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
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
    image: url(assets/check.svg);
}

QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid rgba(31, 35, 41, 0.12);
    border-radius: 8px;
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

QToolTip {
    background-color: #1F2329;
    color: #F5F6F7;
    border: 1px solid rgba(31, 35, 41, 0.4);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}
"""


def _extra_rules(name: str) -> str:
    """Additional QSS for the weektodo-style refactor (view toggle, week
    planner columns, drag highlight, subtasks). Theme-aware colors."""
    dark = name != "light"
    if dark:
        col_bg = "#262626"
        col_border = "rgba(115, 115, 115, 0.12)"
        col_today_border = "#4B3FE3"
        drop_bg = "#1a2e1e"
        drop_border = "#15A877"
        date_color = "#E5E5E5"
        add_color = "#A1A1A1"
        add_hover = "#AAB7FF"
        range_color = "#737373"
        toggle_fg = "#A1A1A1"
        toggle_hover = "#E5E5E5"
    else:
        col_bg = "#FFFFFF"
        col_border = "rgba(115, 115, 115, 0.12)"
        col_today_border = "#4B3FE3"
        drop_bg = "rgba(21, 168, 119, 0.10)"
        drop_border = "#15A877"
        date_color = "#171717"
        add_color = "#737373"
        add_hover = "#4B3FE3"
        range_color = "#737373"
        toggle_fg = "#737373"
        toggle_hover = "#171717"

    return f"""
/* === View toggle (month / week) === */
QPushButton#toggleBtn {{
    background-color: transparent;
    border: 1px solid {col_border};
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 32px;
    color: {toggle_fg};
    font-size: 13px;
}}
QPushButton#toggleBtn:hover {{
    background-color: rgba(115, 115, 115, 0.20);
    color: {toggle_hover};
}}
QPushButton#toggleBtnActive {{
    background-color: #4B3FE3;
    border: 1px solid #4B3FE3;
    border-radius: 6px;
    padding: 4px 10px;
    min-width: 32px;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 13px;
}}

/* === Week planner columns === */
QFrame#weekDayCol {{
    background-color: {col_bg};
    border: 1px solid {col_border};
    border-radius: 8px;
}}
QFrame#weekDayColToday {{
    background-color: {col_bg};
    border: 2px solid {col_today_border};
    border-radius: 8px;
}}
QFrame#weekDayColDrop {{
    background-color: {drop_bg};
    border: 2px dashed {drop_border};
    border-radius: 8px;
}}
QLabel#weekColDate {{
    font-size: 11px;
    font-weight: 600;
    color: {date_color};
}}
QLabel#weekColAdd {{
    font-size: 16px;
    color: {add_color};
}}
QLabel#weekColAdd:hover {{
    color: {add_hover};
}}
QLabel#weekRangeLabel {{
    font-size: 12px;
    color: {range_color};
    padding: 4px 0;
}}
"""


def get_theme(name: str) -> str:
    """Get QSS stylesheet by theme name."""
    base = LIGHT_THEME if name == "light" else DARK_THEME
    return base + _extra_rules(name)
