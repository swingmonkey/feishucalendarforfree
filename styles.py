"""QSS stylesheets for FeishuCalendarDesktop - 飞书（Lark）设计规范。

色板取自飞书开放平台「小程序设计规范 - 视觉规范」与 Arco Design 中性色板：
  Brand:  #3370FF (primary), #4E83FD (hover), #245BDB (active/pressed)
  Neutral (N 系列灰阶，浅→深): N50 #FFFFFF, N100 #F5F6F7, N200 #F2F3F5,
          N300 #DEE0E3, N400 #D0D3D6, N500 #BBBFC4, N600 #8F959E,
          N700 #646A73, N800 #51565D, N900 #1F2329
  文字规则: 一级标题/正文 N900；二级标题/正文 N700；辅助信息 N600；Disable N400
  背景: 页面 N200 / 卡片 N50；控件描边 N300；分割线 N900 12%
  Hover: N900 8%；Press: N900 12%
  Status: #3370FF (info/link), #34C724 (success), #FF8800 (warning), #F54A45 (error)

── 设计令牌（Design Tokens）────────────────────────────────────
  间距基准 : 4px  (4 / 8 / 12 / 16 / 20 / 24)
  圆角     : 控件 6px · 卡片 8px · 菜单/面板 8px
  字阶     : 9 / 10 / 11 / 12 / 13 / 16 / 18 / 24
  焦点     : 可交互控件获得 2px 品牌蓝焦点环
"""

import theme

FONT_STACK = theme.SANS_STACK
MONO_STACK = theme.MONO_STACK

DARK_THEME = f"""
QMainWindow, QDialog, QWidget {{
    background-color: #1F2329;
    color: #E5E6EB;
    font-family: {FONT_STACK};
    font-size: 13px;
}}
/* 标签/单选/复选默认透明，避免在白色卡片上出现灰底色块 */
QLabel, QCheckBox, QRadioButton {{ background-color: transparent; }}

/* 通用焦点环：键盘可达性 */
QPushButton:focus-visible, QLineEdit:focus-visible, QTextEdit:focus-visible,
QComboBox:focus-visible, QDateTimeEdit:focus-visible, QSpinBox:focus-visible,
QCheckBox:focus-visible, QRadioButton:focus-visible, QListWidget:focus-visible,
QToolButton:focus-visible, QTabWidget:focus-visible {{
    outline: 2px solid rgba(51, 112, 255, 0.7);
    outline-offset: 1px;
}}

/* === 顶部标题栏（深色：N900 实底 + 细分隔线） === */
QFrame#headerBar {{
    background-color: #1F2329;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}}
QLabel#headerTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #F5F6F7;
    padding: 2px 2px;
}}
QFrame#monthBar {{
    background-color: #1F2329;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}}
QLabel#headerDate {{
    font-size: 12px;
    color: #BBBFC4;
    font-weight: 500;
}}

/* === 分段控件（月 / 周） === */
QFrame#segmented {{
    background-color: #2B2F36;
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 6px;
}}
QPushButton#toggleBtn {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 3px 12px;
    min-width: 30px;
    color: #BBBFC4;
    font-size: 12px;
}}
QPushButton#toggleBtn:hover {{
    color: #F5F6F7;
}}
QPushButton#toggleBtnActive {{
    background-color: #3A3F47;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 4px;
    padding: 3px 12px;
    min-width: 30px;
    color: #FFFFFF;
    font-weight: 600;
    font-size: 12px;
}}

/* === 标题栏图标按钮 === */
QPushButton#iconBtn, QToolButton#iconBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #BBBFC4;
    font-size: 15px;
}}
QPushButton#iconBtn:hover, QToolButton#iconBtn:hover {{
    background-color: rgba(255, 255, 255, 0.08);
    color: #F5F6F7;
}}
QPushButton#iconBtn:pressed, QToolButton#iconBtn:pressed {{
    background-color: rgba(255, 255, 255, 0.14);
}}
QPushButton#closeBtn, QToolButton#closeBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 28px; min-height: 28px;
    max-width: 28px; max-height: 28px;
    color: #BBBFC4;
    font-size: 14px;
}}
QPushButton#closeBtn:hover, QToolButton#closeBtn:hover {{
    background-color: #F54A45;
    color: #FFFFFF;
}}
QPushButton#todayBtn {{
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 6px;
    padding: 3px 12px;
    color: #BBBFC4;
    font-size: 12px;
}}
QPushButton#todayBtn:hover {{ color: #F5F6F7; background-color: rgba(255,255,255,0.08); }}

/* 蓝色主操作「＋」按钮 */
QPushButton#addBtn {{
    background-color: #3370FF;
    border: none;
    border-radius: 6px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 600;
    padding-bottom: 2px;
}}
QPushButton#addBtn:hover {{ background-color: #4E83FD; }}
QPushButton#addBtn:pressed {{ background-color: #245BDB; }}

/* === Month grid === */
QLabel#weekDay {{
    font-size: 11px;
    color: #8F959E;
    font-weight: 500;
}}
QLabel#weekDayWeekend {{
    font-size: 11px;
    color: #F76965;
    font-weight: 500;
}}

QFrame#dayCell {{
    background-color: #26292E;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
}}
QFrame#dayCellHover {{
    background-color: #2E3239;
    border: 1px solid rgba(51, 112, 255, 0.55);
    border-radius: 8px;
}}
QFrame#dayCellOther {{
    background-color: #22252A;
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 8px;
}}
QFrame#dayCellOtherHover {{
    background-color: #26292E;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
}}
QFrame#dayCellToday {{
    background-color: rgba(51, 112, 255, 0.16);
    border: 1.5px solid #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellTodayHover {{
    background-color: rgba(51, 112, 255, 0.26);
    border: 1.5px solid #4E83FD;
    border-radius: 8px;
}}
/* 拖拽改期的落点指示：与周视图 weekDayColDrop 保持同一套视觉语言 */
QFrame#dayCellDrop {{
    background-color: rgba(51, 112, 255, 0.18);
    border: 2px dashed #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellOtherDrop {{
    background-color: rgba(51, 112, 255, 0.12);
    border: 2px dashed #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellTodayDrop {{
    background-color: rgba(51, 112, 255, 0.24);
    border: 2px dashed #4E83FD;
    border-radius: 8px;
}}
/* 键盘游标（↑↓ 移动到的日期） */
QFrame#dayCellCursor {{
    border: 2px solid #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellOtherCursor {{
    border: 2px solid rgba(51, 112, 255, 0.65);
    border-radius: 8px;
}}
QFrame#dayCellTodayCursor {{
    border: 2px solid #245BDB;
    border-radius: 8px;
}}

QLabel#dayNum {{ font-size: 11px; color: #E5E6EB; font-weight: 600; }}
QLabel#dayNumOther {{ font-size: 11px; color: #646A73; }}
QLabel#dayNumToday {{ font-size: 12px; color: #FFFFFF; font-weight: 700; }}

QFrame#gridEvent {{
    background-color: rgba(51, 112, 255, 0.24);
    border-radius: 4px;
    border-left: 3px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}}
QFrame#gridEvent:hover {{
    background-color: rgba(51, 112, 255, 0.42);
}}
QFrame#gridEventMultiDay {{
    background-color: rgba(52, 199, 36, 0.18);
    border-radius: 4px;
    border-left: 3px solid #34C724;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}}
QFrame#gridEventMultiDay:hover {{ background-color: rgba(52, 199, 36, 0.32); }}
QLabel#gridEventTime {{ font-size: 9px; color: #B8C0CC; }}
QLabel#gridEventTitle {{ font-size: 10px; color: #F0F1F2; }}

QLabel#moreLabel {{ font-size: 9px; color: #8F959E; padding: 0px 2px; }}
QLabel#moreLabel:hover {{ color: #4E83FD; }}

/* === Event card === */
QFrame#eventCard {{
    background-color: #2A2D33;
    border-radius: 8px;
    border-left: 3px solid #3370FF;
}}
QFrame#eventCardPast {{
    background-color: #25282D;
    border-radius: 8px;
    border-left: 3px solid #51565D;
}}
QFrame#eventCardCurrent {{
    background-color: rgba(52, 199, 36, 0.14);
    border-radius: 8px;
    border-left: 3px solid #34C724;
}}
QFrame#eventCard:hover {{ background-color: #33373E; }}
/* 跨天延续日：淡一些，和「起始日」区分开 */
QFrame#eventCardCont {{
    background-color: rgba(42, 45, 51, 0.65);
    border-radius: 8px;
    border-left: 3px solid #51565D;
}}
QFrame#eventCardCont:hover {{ background-color: #2E3239; }}
/* 全天日程：顶部独立成条 */
QFrame#eventCardAllDay {{
    background-color: rgba(15, 179, 118, 0.16);
    border-radius: 6px;
    border-left: 3px solid #0FB376;
}}
QFrame#eventCardAllDay:hover {{ background-color: rgba(15, 179, 118, 0.26); }}
QFrame#weekAllDayBar {{
    background-color: rgba(255, 255, 255, 0.03);
    border-radius: 6px;
}}

QLabel#eventTime {{ font-size: 11px; color: #A9B0B8; font-weight: 600; }}
QLabel#eventTimePast {{ font-size: 11px; color: #646A73; font-weight: 600; }}
QLabel#eventTimeCurrent {{ font-size: 11px; color: #4FD963; font-weight: 600; }}
QLabel#eventTitle {{ font-size: 13px; color: #F0F1F2; font-weight: 500; }}
QLabel#eventTitlePast {{ font-size: 13px; color: #646A73; font-weight: 500; }}
QLabel#eventMeta {{ font-size: 11px; color: #8F959E; }}

QPushButton#deleteBtn {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 0px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
    color: #646A73;
    font-size: 12px;
}}
QPushButton#deleteBtn:hover {{ background-color: #F54A45; color: #FFFFFF; }}

QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: rgba(255,255,255,0.22); border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,0.42); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0 2px; }}
QScrollBar::handle:horizontal {{ background: rgba(255,255,255,0.22); border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: rgba(255,255,255,0.42); }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit, QSpinBox {{
    background-color: #2B2F36;
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 6px;
    padding: 7px 10px;
    color: #F0F1F2;
    selection-background-color: #3370FF;
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus {{
    border: 1px solid #3370FF;
}}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QDateTimeEdit:disabled {{
    color: #646A73;
    background-color: #26292E;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QDateTimeEdit::drop-down, QDateEdit::drop-down {{ border: none; background: transparent; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: #2B2F36;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: rgba(51,112,255,0.25);
    selection-color: #FFFFFF;
}}

/* === 按钮（飞书扁平风） === */
QPushButton#primaryBtn {{
    background-color: #3370FF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
}}
QPushButton#primaryBtn:hover {{ background-color: #4E83FD; }}
QPushButton#primaryBtn:pressed {{ background-color: #245BDB; }}
QPushButton#primaryBtn:disabled {{ background-color: rgba(51,112,255,0.40); color: rgba(255,255,255,0.7); }}

QPushButton#secondaryBtn {{
    background-color: transparent;
    color: #E5E6EB;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 6px;
    padding: 7px 18px;
}}
QPushButton#secondaryBtn:hover {{ background-color: rgba(255,255,255,0.08); border-color: rgba(255,255,255,0.28); }}
QPushButton#secondaryBtn:pressed {{ background-color: rgba(255,255,255,0.14); }}
QPushButton#secondaryBtn:disabled {{ color: #51565D; border-color: rgba(255,255,255,0.10); }}

QPushButton#dangerBtn {{
    background-color: transparent;
    color: #F76965;
    border: 1px solid rgba(245,74,69,0.55);
    border-radius: 6px;
    padding: 7px 18px;
}}
QPushButton#dangerBtn:hover {{ background-color: #F54A45; color: #FFFFFF; border-color: #F54A45; }}

QPushButton#linkBtn {{
    background-color: transparent;
    border: none;
    color: #3370FF;
    padding: 4px 2px;
    text-align: left;
}}
QPushButton#linkBtn:hover {{ color: #4E83FD; }}

QLabel#formError {{ color: #F76965; font-size: 12px; }}

QLabel#statusLabel {{ font-size: 11px; color: #8F959E; padding: 3px 0px; }}
QLabel#resizeGrip {{ font-size: 11px; color: #51565D; }}
QLabel#emptyLabel {{ font-size: 13px; color: #8F959E; padding: 40px 20px; }}

QTextEdit#errorDisplay, QTextEdit#stateDetail {{
    background-color: rgba(245, 74, 69, 0.08);
    color: #E5E6EB;
    border: 1px solid rgba(245, 74, 69, 0.30);
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.35);
}}
QTextEdit#codeBox {{
    background-color: #2B2F36;
    color: #F0F1F2;
    border: 1px solid #3A3F47;
    border-radius: 6px;
    padding: 10px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
}}

QLineEdit#searchInput {{
    background-color: #2B2F36;
    color: #F0F1F2;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 6px;
    padding: 8px 12px 8px 32px;
    font-size: 13px;
    background-image: url(assets/search.svg);
    background-repeat: no-repeat;
    background-position: 9px center;
}}
QLineEdit#searchInput:focus {{ border: 1px solid #3370FF; }}

QListWidget#searchResultList {{
    background-color: #2B2F36;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}}
QListWidget#searchResultList::item {{ padding: 8px 12px; border-radius: 4px; color: #E5E6EB; }}
QListWidget#searchResultList::item:hover {{ background-color: rgba(51,112,255,0.18); }}
QListWidget#searchResultList::item:selected {{ background-color: rgba(51,112,255,0.35); color: #FFFFFF; }}

QLabel#detailTitle {{ font-size: 16px; font-weight: 600; color: #F5F6F7; }}
QLabel#detailLabel {{ font-size: 12px; color: #8F959E; }}
QLabel#detailValue {{ font-size: 13px; color: #E5E6EB; }}

QGroupBox {{
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 16px;
    color: #BBBFC4;
    font-weight: 600;
}}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; top: 2px; left: 14px; padding: 0 6px; }}

QCheckBox {{ color: #E5E6EB; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid rgba(255,255,255,0.30);
    border-radius: 4px; background: #2B2F36;
}}
QCheckBox::indicator:hover {{ border-color: #3370FF; }}
QCheckBox::indicator:checked {{ background: #3370FF; border-color: #3370FF; image: url(assets/check.svg); }}

QSpinBox {{ padding: 4px 8px; }}
QSpinBox:focus {{ border: 1px solid #3370FF; }}

QSlider::groove:horizontal {{ background: rgba(255,255,255,0.18); height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: #FFFFFF; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; border: 1px solid rgba(255,255,255,0.30);
}}
QSlider::handle:horizontal:hover {{ border-color: #3370FF; }}
QSlider::sub-page:horizontal {{ background: #3370FF; border-radius: 2px; }}

QRadioButton {{ color: #E5E6EB; spacing: 8px; }}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid rgba(255,255,255,0.30);
    border-radius: 8px; background: #2B2F36;
}}
QRadioButton::indicator:checked {{
    border: 4px solid #26292E;
    background-color: #3370FF;
    width: 8px; height: 8px;
    border-radius: 8px;
}}

QToolTip {{
    background-color: #2B2F36;
    color: #F5F6F7;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* === Tab（飞书下划线式） === */
QTabWidget::pane {{ border: none; border-top: 1px solid rgba(255,255,255,0.08); top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: #8F959E;
    padding: 8px 18px;
    margin-right: 4px;
    border: none;
    font-size: 13px;
}}
QTabBar::tab:selected {{ color: #F5F6F7; font-weight: 600; border-bottom: 2px solid #3370FF; margin-bottom: -1px; }}
QTabBar::tab:hover:!selected {{ color: #E5E6EB; }}

/* === 菜单（溢出菜单 / 托盘） === */
QMenu {{
    background-color: #2B2F36;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 22px 6px 14px;
    border-radius: 6px;
    color: #E5E6EB;
    font-size: 13px;
}}
QMenu::item:selected {{ background-color: rgba(51,112,255,0.22); color: #FFFFFF; }}
QMenu::item:disabled {{ color: #51565D; }}
QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.10); margin: 5px 8px; }}
QMenu::indicator {{ left: 8px; width: 14px; }}

/* === 进度条 === */
QProgressBar {{
    background-color: rgba(255,255,255,0.10);
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background-color: #3370FF; border-radius: 4px; }}

/* === 状态面板（加载 / 登录引导 / 错误） === */
QLabel#stateIcon {{ font-size: 40px; color: #3370FF; padding: 4px; }}
QLabel#stateTitle {{ font-size: 15px; font-weight: 600; color: #F5F6F7; }}
QLabel#stateMessage {{ font-size: 12px; color: #8F959E; }}
QFrame#qrCard {{
    background-color: #FFFFFF;
    border: 1px solid rgba(255,255,255,0.18);
    border-radius: 10px;
}}
QLabel#loginBadge {{
    background-color: #3370FF;
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}}

/* === Toast 轻提示（深色胶囊，深浅主题通用） === */
QFrame#toast {{
    background-color: #2B2F36;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 8px;
}}
QLabel#toastIcon {{ font-size: 14px; background: transparent; }}
QLabel#toastMsg {{ color: #F5F6F7; font-size: 12px; background: transparent; }}
QPushButton#toastAction {{
    background-color: transparent;
    border: none;
    color: #4E83FD;
    font-size: 12px;
    padding: 2px 6px;
}}
QPushButton#toastAction:hover {{ color: #7BA3FD; }}
QPushButton#toastClose {{
    background-color: transparent; border: none;
    color: #8F959E; font-size: 12px;
    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
}}
QPushButton#toastClose:hover {{ color: #F5F6F7; }}
"""


LIGHT_THEME = f"""
QMainWindow, QDialog, QWidget {{
    background-color: #F2F3F5;
    color: #1F2329;
    font-family: {FONT_STACK};
    font-size: 13px;
}}
/* 标签/单选/复选默认透明，避免在白色卡片上出现灰底色块 */
QLabel, QCheckBox, QRadioButton {{ background-color: transparent; }}

QPushButton:focus-visible, QLineEdit:focus-visible, QTextEdit:focus-visible,
QComboBox:focus-visible, QDateTimeEdit:focus-visible, QSpinBox:focus-visible,
QCheckBox:focus-visible, QRadioButton:focus-visible, QListWidget:focus-visible,
QToolButton:focus-visible, QTabWidget:focus-visible {{
    outline: 2px solid rgba(51, 112, 255, 0.55);
    outline-offset: 1px;
}}

/* === 顶部标题栏（飞书白：实底白 + N300 分隔线） === */
QFrame#headerBar {{
    background-color: #FFFFFF;
    border: none;
    border-bottom: 1px solid #DEE0E3;
}}
QLabel#headerTitle {{
    font-size: 14px;
    font-weight: 600;
    color: #1F2329;
    padding: 2px 2px;
}}
QFrame#monthBar {{
    background-color: #FFFFFF;
    border: none;
    border-bottom: 1px solid #EBEDF0;
}}
QLabel#headerDate {{
    font-size: 12px;
    color: #646A73;
    font-weight: 500;
}}

/* === 分段控件（月 / 周） === */
QFrame#segmented {{
    background-color: #F2F3F5;
    border: 1px solid #E5E6EB;
    border-radius: 6px;
}}
QPushButton#toggleBtn {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 3px 12px;
    min-width: 30px;
    color: #646A73;
    font-size: 12px;
}}
QPushButton#toggleBtn:hover {{ color: #1F2329; }}
QPushButton#toggleBtnActive {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 4px;
    padding: 3px 12px;
    min-width: 30px;
    color: #1F2329;
    font-weight: 600;
    font-size: 12px;
}}

/* === 标题栏图标按钮 === */
QPushButton#iconBtn, QToolButton#iconBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #646A73;
    font-size: 15px;
}}
QPushButton#iconBtn:hover, QToolButton#iconBtn:hover {{
    background-color: #F2F3F5;
    color: #1F2329;
}}
QPushButton#iconBtn:pressed, QToolButton#iconBtn:pressed {{
    background-color: #E5E6EB;
}}
QPushButton#closeBtn, QToolButton#closeBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 28px; min-height: 28px;
    max-width: 28px; max-height: 28px;
    color: #646A73;
    font-size: 14px;
}}
QPushButton#closeBtn:hover, QToolButton#closeBtn:hover {{
    background-color: #F54A45;
    color: #FFFFFF;
}}
QPushButton#todayBtn {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 3px 12px;
    color: #646A73;
    font-size: 12px;
}}
QPushButton#todayBtn:hover {{ color: #1F2329; background-color: #F5F6F7; border-color: #BBBFC4; }}

/* 蓝色主操作「＋」按钮 */
QPushButton#addBtn {{
    background-color: #3370FF;
    border: none;
    border-radius: 6px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    color: #FFFFFF;
    font-size: 17px;
    font-weight: 600;
    padding-bottom: 2px;
}}
QPushButton#addBtn:hover {{ background-color: #4E83FD; }}
QPushButton#addBtn:pressed {{ background-color: #245BDB; }}

/* === Month grid === */
QLabel#weekDay {{ font-size: 11px; color: #8F959E; font-weight: 500; }}
QLabel#weekDayWeekend {{ font-size: 11px; color: #F54A45; font-weight: 500; }}

QFrame#dayCell {{
    background-color: #FFFFFF;
    border: 1px solid #EBEDF0;
    border-radius: 8px;
}}
QFrame#dayCellHover {{
    background-color: #F5F6F7;
    border: 1px solid rgba(51, 112, 255, 0.55);
    border-radius: 8px;
}}
QFrame#dayCellOther {{
    background-color: #F7F8FA;
    border: 1px solid #F0F1F2;
    border-radius: 8px;
}}
QFrame#dayCellOtherHover {{
    background-color: #F2F3F5;
    border: 1px solid #DEE0E3;
    border-radius: 8px;
}}
QFrame#dayCellToday {{
    background-color: rgba(51, 112, 255, 0.10);
    border: 1.5px solid #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellTodayHover {{
    background-color: rgba(51, 112, 255, 0.18);
    border: 1.5px solid #4E83FD;
    border-radius: 8px;
}}
/* 拖拽改期的落点指示：与周视图 weekDayColDrop 保持同一套视觉语言 */
QFrame#dayCellDrop {{
    background-color: rgba(51, 112, 255, 0.10);
    border: 2px dashed #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellOtherDrop {{
    background-color: rgba(51, 112, 255, 0.06);
    border: 2px dashed #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellTodayDrop {{
    background-color: rgba(51, 112, 255, 0.16);
    border: 2px dashed #245BDB;
    border-radius: 8px;
}}
/* 键盘游标（↑↓ 移动到的日期） */
QFrame#dayCellCursor {{
    border: 2px solid #3370FF;
    border-radius: 8px;
}}
QFrame#dayCellOtherCursor {{
    border: 2px solid rgba(51, 112, 255, 0.6);
    border-radius: 8px;
}}
QFrame#dayCellTodayCursor {{
    border: 2px solid #245BDB;
    border-radius: 8px;
}}

QLabel#dayNum {{ font-size: 11px; color: #1F2329; font-weight: 600; }}
QLabel#dayNumOther {{ font-size: 11px; color: #BBBFC4; }}
QLabel#dayNumToday {{ font-size: 12px; color: #FFFFFF; font-weight: 700; }}

QFrame#gridEvent {{
    background-color: rgba(51, 112, 255, 0.10);
    border-radius: 4px;
    border-left: 3px solid #3370FF;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}}
QFrame#gridEvent:hover {{ background-color: rgba(51, 112, 255, 0.20); border-left: 3px solid #306EFF; }}
QFrame#gridEventMultiDay {{
    background-color: rgba(52, 199, 36, 0.10);
    border-radius: 4px;
    border-left: 3px solid #34C724;
    max-height: 18px;
    min-height: 16px;
    padding-left: 4px;
}}
QFrame#gridEventMultiDay:hover {{ background-color: rgba(52, 199, 36, 0.22); }}
QLabel#gridEventTime {{ font-size: 9px; color: #646A73; }}
QLabel#gridEventTitle {{ font-size: 10px; color: #1F2329; }}

QLabel#moreLabel {{ font-size: 9px; color: #8F959E; padding: 0px 2px; }}
QLabel#moreLabel:hover {{ color: #245BDB; }}

/* === Event card === */
QFrame#eventCard {{
    background-color: #FFFFFF;
    border-radius: 8px;
    border-left: 3px solid #3370FF;
}}
QFrame#eventCardPast {{
    background-color: #F7F8FA;
    border-radius: 8px;
    border-left: 3px solid #D0D3D6;
}}
QFrame#eventCardCurrent {{
    background-color: #F2FAF1;
    border-radius: 8px;
    border-left: 3px solid #34C724;
}}
QFrame#eventCard:hover {{ background-color: #F5F6F7; }}
/* 跨天延续日：淡一些，和「起始日」区分开 */
QFrame#eventCardCont {{
    background-color: #F7F8FA;
    border-radius: 8px;
    border-left: 3px solid #BBBFC4;
}}
QFrame#eventCardCont:hover {{ background-color: #F2F3F5; }}
/* 全天日程：顶部独立成条 */
QFrame#eventCardAllDay {{
    background-color: rgba(15, 179, 118, 0.12);
    border-radius: 6px;
    border-left: 3px solid #0FB376;
}}
QFrame#eventCardAllDay:hover {{ background-color: rgba(15, 179, 118, 0.20); }}
QFrame#weekAllDayBar {{
    background-color: #F7F8FA;
    border-radius: 6px;
}}

QLabel#eventTime {{ font-size: 11px; color: #51565D; font-weight: 600; }}
QLabel#eventTimePast {{ font-size: 11px; color: #BBBFC4; font-weight: 600; }}
QLabel#eventTimeCurrent {{ font-size: 11px; color: #2EA121; font-weight: 600; }}
QLabel#eventTitle {{ font-size: 13px; color: #1F2329; font-weight: 500; }}
QLabel#eventTitlePast {{ font-size: 13px; color: #BBBFC4; font-weight: 500; }}
QLabel#eventMeta {{ font-size: 11px; color: #8F959E; }}

QPushButton#deleteBtn {{
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 0px;
    min-width: 22px; min-height: 22px;
    max-width: 22px; max-height: 22px;
    color: #BBBFC4;
    font-size: 12px;
}}
QPushButton#deleteBtn:hover {{ background-color: #F54A45; color: #FFFFFF; }}

QScrollArea {{ border: none; background-color: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px 0; }}
QScrollBar::handle:vertical {{ background: #C9CDD4; border-radius: 4px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: #A6ABB4; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 0 2px; }}
QScrollBar::handle:horizontal {{ background: #C9CDD4; border-radius: 4px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: #A6ABB4; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: transparent; }}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit, QSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 7px 10px;
    color: #1F2329;
    selection-background-color: #3370FF;
    selection-color: #FFFFFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QComboBox:focus, QDateTimeEdit:focus, QSpinBox:focus {{
    border: 1px solid #3370FF;
}}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled, QDateTimeEdit:disabled {{
    color: #BBBFC4;
    background-color: #F7F8FA;
}}
QComboBox::drop-down {{ border: none; width: 24px; }}
QDateTimeEdit::drop-down, QDateEdit::drop-down {{ border: none; background: transparent; width: 22px; }}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 4px;
    outline: none;
    selection-background-color: #E8F1FF;
    selection-color: #1F2329;
}}

/* === 按钮（飞书扁平风） === */
QPushButton#primaryBtn {{
    background-color: #3370FF;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 7px 18px;
    font-weight: 500;
}}
QPushButton#primaryBtn:hover {{ background-color: #4E83FD; }}
QPushButton#primaryBtn:pressed {{ background-color: #245BDB; }}
QPushButton#primaryBtn:disabled {{ background-color: #B7CEFD; color: #FFFFFF; }}

QPushButton#secondaryBtn {{
    background-color: #FFFFFF;
    color: #1F2329;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 7px 18px;
}}
QPushButton#secondaryBtn:hover {{ background-color: #F5F6F7; border-color: #BBBFC4; }}
QPushButton#secondaryBtn:pressed {{ background-color: #EDEEF0; }}
QPushButton#secondaryBtn:disabled {{ color: #BBBFC4; background-color: #F7F8FA; }}

QPushButton#dangerBtn {{
    background-color: #FFFFFF;
    color: #F54A45;
    border: 1px solid rgba(245, 74, 69, 0.55);
    border-radius: 6px;
    padding: 7px 18px;
}}
QPushButton#dangerBtn:hover {{ background-color: #F54A45; color: #FFFFFF; border-color: #F54A45; }}

QPushButton#linkBtn {{
    background-color: transparent;
    border: none;
    color: #3370FF;
    padding: 4px 2px;
    text-align: left;
}}
QPushButton#linkBtn:hover {{ color: #245BDB; }}

QLabel#formError {{ color: #F54A45; font-size: 12px; }}

QLabel#statusLabel {{ font-size: 11px; color: #8F959E; padding: 3px 0px; }}
QLabel#resizeGrip {{ font-size: 11px; color: #C9CDD4; }}
QLabel#emptyLabel {{ font-size: 13px; color: #8F959E; padding: 40px 20px; }}

QTextEdit#errorDisplay, QTextEdit#stateDetail {{
    background-color: #FDF4F3;
    color: #1F2329;
    border: 1px solid rgba(245, 74, 69, 0.30);
    border-radius: 6px;
    padding: 10px;
    font-size: 12px;
    selection-background-color: rgba(51, 112, 255, 0.20);
}}
QTextEdit#codeBox {{
    background-color: #F5F6F7;
    color: #1F2329;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 10px;
    font-family: Consolas, 'Courier New', monospace;
    font-size: 13px;
}}

QLineEdit#searchInput {{
    background-color: #FFFFFF;
    color: #1F2329;
    border: 1px solid #DEE0E3;
    border-radius: 6px;
    padding: 8px 12px 8px 32px;
    font-size: 13px;
    background-image: url(assets/search.svg);
    background-repeat: no-repeat;
    background-position: 9px center;
}}
QLineEdit#searchInput:focus {{ border: 1px solid #3370FF; }}

QListWidget#searchResultList {{
    background-color: #FFFFFF;
    border: 1px solid #EBEDF0;
    border-radius: 6px;
    padding: 4px;
    font-size: 12px;
    outline: none;
}}
QListWidget#searchResultList::item {{ padding: 8px 12px; border-radius: 4px; color: #1F2329; }}
QListWidget#searchResultList::item:hover {{ background-color: #F5F6F7; }}
QListWidget#searchResultList::item:selected {{ background-color: #E8F1FF; color: #245BDB; }}

QLabel#detailTitle {{ font-size: 16px; font-weight: 600; color: #1F2329; }}
QLabel#detailLabel {{ font-size: 12px; color: #8F959E; }}
QLabel#detailValue {{ font-size: 13px; color: #1F2329; }}

QGroupBox {{
    border: 1px solid #EBEDF0;
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 16px;
    color: #51565D;
    font-weight: 600;
    background-color: #FFFFFF;
}}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; top: 2px; left: 14px; padding: 0 6px; }}

QCheckBox {{ color: #1F2329; spacing: 8px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid #BBBFC4;
    border-radius: 4px; background: #FFFFFF;
}}
QCheckBox::indicator:hover {{ border-color: #3370FF; }}
QCheckBox::indicator:checked {{ background: #3370FF; border-color: #3370FF; image: url(assets/check.svg); }}

QSpinBox {{ padding: 4px 8px; }}
QSpinBox:focus {{ border: 1px solid #3370FF; }}

QSlider::groove:horizontal {{ background: #DEE0E3; height: 4px; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: #FFFFFF; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; border: 1px solid #BBBFC4;
}}
QSlider::handle:horizontal:hover {{ border-color: #3370FF; }}
QSlider::sub-page:horizontal {{ background: #3370FF; border-radius: 2px; }}

QRadioButton {{ color: #1F2329; spacing: 8px; }}
QRadioButton::indicator {{
    width: 16px; height: 16px;
    border: 1px solid #BBBFC4;
    border-radius: 8px; background: #FFFFFF;
}}
QRadioButton::indicator:checked {{
    border: 4px solid #FFFFFF;
    background-color: #3370FF;
    width: 8px; height: 8px;
    border-radius: 8px;
}}

QToolTip {{
    background-color: #1F2329;
    color: #F5F6F7;
    border: 1px solid rgba(0, 0, 0, 0.4);
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* === Tab（飞书下划线式） === */
QTabWidget::pane {{ border: none; border-top: 1px solid #EBEDF0; top: -1px; }}
QTabBar::tab {{
    background: transparent;
    color: #646A73;
    padding: 8px 18px;
    margin-right: 4px;
    border: none;
    font-size: 13px;
}}
QTabBar::tab:selected {{ color: #1F2329; font-weight: 600; border-bottom: 2px solid #3370FF; margin-bottom: -1px; }}
QTabBar::tab:hover:!selected {{ color: #1F2329; }}

/* === 菜单（溢出菜单 / 托盘） === */
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{
    padding: 6px 22px 6px 14px;
    border-radius: 6px;
    color: #1F2329;
    font-size: 13px;
}}
QMenu::item:selected {{ background-color: #F2F3F5; }}
QMenu::item:disabled {{ color: #BBBFC4; }}
QMenu::separator {{ height: 1px; background: #EBEDF0; margin: 5px 8px; }}
QMenu::indicator {{ left: 8px; width: 14px; }}

/* === 进度条 === */
QProgressBar {{
    background-color: #F2F3F5;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{ background-color: #3370FF; border-radius: 4px; }}

/* === 状态面板（加载 / 登录引导 / 错误） === */
QLabel#stateIcon {{ font-size: 40px; color: #3370FF; padding: 4px; }}
QLabel#stateTitle {{ font-size: 15px; font-weight: 600; color: #1F2329; }}
QLabel#stateMessage {{ font-size: 12px; color: #646A73; }}
QFrame#qrCard {{
    background-color: #FFFFFF;
    border: 1px solid #DEE0E3;
    border-radius: 10px;
}}
QLabel#loginBadge {{
    background-color: #3370FF;
    color: #FFFFFF;
    border-radius: 10px;
    font-size: 18px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}}

/* === Toast 轻提示（深色胶囊，深浅主题通用） === */
QFrame#toast {{
    background-color: #2B2F36;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 8px;
}}
QLabel#toastIcon {{ font-size: 14px; background: transparent; }}
QLabel#toastMsg {{ color: #F5F6F7; font-size: 12px; background: transparent; }}
QPushButton#toastAction {{
    background-color: transparent;
    border: none;
    color: #6AA1FF;
    font-size: 12px;
    padding: 2px 6px;
}}
QPushButton#toastAction:hover {{ color: #9DBEFF; }}
QPushButton#toastClose {{
    background-color: transparent; border: none;
    color: #8F959E; font-size: 12px;
    min-width: 20px; max-width: 20px; min-height: 20px; max-height: 20px;
}}
QPushButton#toastClose:hover {{ color: #F5F6F7; }}
"""


def _menu_dialog_rules(name: str) -> str:
    """Theme rules shared by menus, dialogs and popup controls."""
    dark = name != "light"
    if dark:
        dialog_bg = "#1F2329"
        surface = "#2B2F36"
        surface_alt = "#262A31"
        text = "#F5F6F7"
        muted = "#B8C0CC"
        disabled = "#646A73"
        border = "rgba(245, 246, 247, 0.16)"
        border_strong = "rgba(245, 246, 247, 0.24)"
        hover = "rgba(245, 246, 247, 0.08)"
        pressed = "rgba(245, 246, 247, 0.14)"
        separator = "rgba(245, 246, 247, 0.12)"
        menu_selected_bg = "rgba(51, 112, 255, 0.24)"
        menu_selected_text = "#FFFFFF"
        menu_pressed_bg = "rgba(51, 112, 255, 0.34)"
        input_bg = "#2B2F36"
        input_disabled_bg = "#262A31"
        logo_bg = "rgba(255, 255, 255, 0.08)"
        logo_border = "rgba(255, 255, 255, 0.14)"
    else:
        dialog_bg = "#FFFFFF"
        surface = "#FFFFFF"
        surface_alt = "#F5F6F7"
        text = "#1F2329"
        muted = "#646A73"
        disabled = "#BBBFC4"
        border = "rgba(31, 35, 41, 0.14)"
        border_strong = "rgba(31, 35, 41, 0.22)"
        hover = "rgba(31, 35, 41, 0.06)"
        pressed = "rgba(31, 35, 41, 0.12)"
        separator = "rgba(31, 35, 41, 0.10)"
        menu_selected_bg = "#EAF0FF"
        menu_selected_text = "#245BDB"
        menu_pressed_bg = "#D9E5FF"
        input_bg = "#FFFFFF"
        input_disabled_bg = "#F7F8FA"
        logo_bg = "#F2F3F5"
        logo_border = "#DEE0E3"

    return f"""
/* === Window logo === */
QLabel#headerLogo {{
    background-color: {logo_bg};
    border: 1px solid {logo_border};
    border-radius: 12px;
    padding: 0px;
}}

/* === Menus (main overflow + tray) === */
QMenu {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 7px;
}}
QMenu::item {{
    background-color: transparent;
    color: {text};
    border-radius: 6px;
    padding: 9px 30px 9px 14px;
    margin: 1px 2px;
    min-width: 188px;
    font-size: 13px;
}}
QMenu::item:selected {{
    background-color: {menu_selected_bg};
    color: {menu_selected_text};
}}
QMenu::item:pressed {{
    background-color: {menu_pressed_bg};
    color: {menu_selected_text};
}}
QMenu::item:disabled {{
    color: {disabled};
}}
QMenu::separator {{
    height: 1px;
    background-color: {separator};
    margin: 6px 10px;
}}
QMenu::indicator {{
    width: 16px;
    height: 16px;
    margin-left: 6px;
}}

/* === Header overflow button === */
QToolButton#moreBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 0px;
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
}}
QToolButton#moreBtn:hover {{
    background-color: {hover};
}}
QToolButton#moreBtn:pressed, QToolButton#moreBtn:checked {{
    background-color: {pressed};
}}
QToolButton#moreBtn::menu-indicator {{
    image: none;
    width: 0px;
    height: 0px;
}}

/* === Dialogs and message boxes === */
QDialog, QMessageBox {{
    background-color: {dialog_bg};
    color: {text};
}}
QDialog QLabel, QMessageBox QLabel {{
    background-color: transparent;
    color: {text};
}}
QDialog QLabel#detailTitle {{
    color: {text};
    font-size: 16px;
    font-weight: 600;
}}
QDialog QLabel#detailLabel {{
    color: {muted};
    font-size: 12px;
}}
QDialog QLabel#detailValue {{
    color: {text};
    font-size: 13px;
}}
QLabel#confirmIcon, QLabel#confirmIconDanger {{
    border-radius: 14px;
    font-size: 15px;
    font-weight: 700;
}}
QLabel#confirmIcon {{
    background-color: rgba(51, 112, 255, 0.14);
    color: #3370FF;
}}
QLabel#confirmIconDanger {{
    background-color: rgba(245, 74, 69, 0.14);
    color: #F54A45;
}}
QLabel#confirmTitle {{
    color: {text};
    font-size: 15px;
    font-weight: 600;
}}
QLabel#confirmMessage {{
    color: {muted};
    font-size: 13px;
}}
QMessageBox QLabel#qt_msgbox_label {{
    min-width: 260px;
}}
QFrame#dialogSeparator {{
    color: {separator};
    background-color: {separator};
    border: none;
    max-height: 1px;
}}

QDialog QLineEdit, QDialog QTextEdit, QDialog QPlainTextEdit, QDialog QComboBox,
QDialog QDateTimeEdit, QDialog QDateEdit, QDialog QSpinBox {{
    background-color: {input_bg};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 7px 10px;
    selection-background-color: #3370FF;
    selection-color: #FFFFFF;
}}
QDialog QLineEdit:focus, QDialog QTextEdit:focus, QDialog QPlainTextEdit:focus,
QDialog QComboBox:focus, QDialog QDateTimeEdit:focus, QDialog QDateEdit:focus,
QDialog QSpinBox:focus {{
    border: 1px solid #3370FF;
}}
QDialog QLineEdit:disabled, QDialog QTextEdit:disabled, QDialog QPlainTextEdit:disabled,
QDialog QComboBox:disabled, QDialog QDateTimeEdit:disabled, QDialog QDateEdit:disabled,
QDialog QSpinBox:disabled {{
    background-color: {input_disabled_bg};
    color: {disabled};
}}
QDialog QPlainTextEdit#detailLabel {{
    padding: 10px;
    border-radius: 8px;
}}

QDialogButtonBox QPushButton, QMessageBox QPushButton {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 7px;
    padding: 7px 18px;
    min-width: 66px;
    min-height: 18px;
}}
QDialogButtonBox QPushButton:hover, QMessageBox QPushButton:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}
QDialogButtonBox QPushButton:pressed, QMessageBox QPushButton:pressed {{
    background-color: {pressed};
}}
QDialogButtonBox QPushButton:default, QMessageBox QPushButton:default {{
    background-color: #3370FF;
    border-color: #3370FF;
    color: #FFFFFF;
    font-weight: 600;
}}
QDialogButtonBox QPushButton:default:hover, QMessageBox QPushButton:default:hover {{
    background-color: #4A86FF;
    border-color: #4A86FF;
}}
QDialogButtonBox QPushButton:disabled, QMessageBox QPushButton:disabled {{
    background-color: {surface_alt};
    border-color: {separator};
    color: {disabled};
}}
QDialog QPushButton#primaryBtn {{
    background-color: #3370FF;
    color: #FFFFFF;
    border: 1px solid #3370FF;
    border-radius: 6px;
    padding: 7px 18px;
    min-height: 18px;
    font-weight: 500;
}}
QDialog QPushButton#primaryBtn:hover {{
    background-color: #4E83FD;
    border-color: #4E83FD;
}}
QDialog QPushButton#primaryBtn:pressed {{
    background-color: #245BDB;
    border-color: #245BDB;
}}
QDialog QPushButton#primaryBtn:disabled {{
    background-color: rgba(51, 112, 255, 0.42);
    border-color: transparent;
    color: rgba(255, 255, 255, 0.74);
}}
QDialog QPushButton#secondaryBtn {{
    background-color: transparent;
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 6px;
    padding: 7px 18px;
    min-height: 18px;
}}
QDialog QPushButton#secondaryBtn:hover {{
    background-color: {hover};
    border-color: {border_strong};
}}
QDialog QPushButton#secondaryBtn:pressed {{
    background-color: {pressed};
}}
QDialog QPushButton#dangerBtn {{
    background-color: rgba(245, 74, 69, 0.08);
    color: #F54A45;
    border: 1px solid rgba(245, 74, 69, 0.58);
    border-radius: 6px;
    padding: 7px 18px;
    min-height: 18px;
    font-weight: 500;
}}
QDialog QPushButton#dangerBtn:hover {{
    background-color: #F54A45;
    border-color: #F54A45;
    color: #FFFFFF;
}}
QDialog QPushButton#dangerBtn:pressed {{
    background-color: #D93F3A;
    border-color: #D93F3A;
}}

/* === Tabs === */
QDialog QTabWidget::pane {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    top: -1px;
}}
QDialog QTabBar::tab {{
    background-color: transparent;
    color: {muted};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 18px;
    margin-right: 4px;
    min-width: 68px;
    font-size: 13px;
}}
QDialog QTabBar::tab:hover:!selected {{
    background-color: {hover};
    color: {text};
}}
QDialog QTabBar::tab:selected {{
    background-color: transparent;
    color: #3370FF;
    border-bottom: 2px solid #3370FF;
    font-weight: 600;
}}
QDialog QTabBar::tab:disabled {{
    color: {disabled};
}}

QDialog QGroupBox {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: 8px;
    /* QGroupBox 的 sizeHint 不包含 QSS 的 margin，所以 margin-top
       必须小：标题就压在边框线上（Qt 官方示例的做法）。原来 20px
       的 margin 叠上四值 padding，把内容区挤到 0 高——设置面板的
       「自动刷新」「开机启动」曾只剩一条细线，按钮也被裁掉下半截。 */
    margin-top: 8px;
    padding: 2px 0px 0px 0px;
    color: {text};
    font-weight: 600;
}}
QDialog QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    top: 2px;
    padding: 0 6px;
    color: {muted};
    background-color: transparent;
}}

QDialog QCheckBox, QDialog QRadioButton {{
    color: {text};
    spacing: 8px;
    padding: 2px 0;
}}

/* === Combo and calendar popups === */
QComboBox QAbstractItemView {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border_strong};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: #3370FF;
    selection-color: #FFFFFF;
    outline: none;
}}
QComboBox QAbstractItemView::item {{
    min-height: 26px;
    padding: 4px 10px;
    border-radius: 5px;
}}
QComboBox QAbstractItemView::item:hover {{
    background-color: {hover};
}}
QComboBox QAbstractItemView::item:selected {{
    background-color: #3370FF;
    color: #FFFFFF;
}}

QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: {surface_alt};
    border-bottom: 1px solid {border};
}}
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: {text};
    border: none;
    border-radius: 6px;
    padding: 6px 10px;
}}
QCalendarWidget QToolButton:hover {{
    background-color: {hover};
}}
QCalendarWidget QSpinBox {{
    background-color: {surface};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    padding: 3px 6px;
}}
QCalendarWidget QAbstractItemView {{
    background-color: {surface};
    color: {text};
    selection-background-color: #3370FF;
    selection-color: #FFFFFF;
    outline: none;
}}
QCalendarWidget QAbstractItemView:disabled {{
    color: {disabled};
}}

QProgressBar {{
    background-color: {surface_alt};
    color: {text};
    border: 1px solid {border};
    border-radius: 6px;
    min-height: 14px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: #3370FF;
    border-radius: 5px;
}}
"""


def _extra_rules(name: str) -> str:
    """Additional QSS for the week planner (columns, drag highlight)."""
    dark = name != "light"
    if dark:
        col_bg = "#26292E"
        col_border = "rgba(255,255,255,0.08)"
        col_today_border = "#3370FF"
        drop_bg = "rgba(51,112,255,0.16)"
        drop_border = "#3370FF"
        date_color = "#E5E6EB"
        add_color = "#8F959E"
        add_hover = "#4E83FD"
        range_color = "#8F959E"
    else:
        col_bg = "#FFFFFF"
        col_border = "#EBEDF0"
        col_today_border = "#3370FF"
        drop_bg = "rgba(51,112,255,0.10)"
        drop_border = "#3370FF"
        date_color = "#1F2329"
        add_color = "#8F959E"
        add_hover = "#3370FF"
        range_color = "#646A73"

    return f"""
/* === Week planner columns === */
QFrame#weekDayCol {{
    background-color: {col_bg};
    border: 1px solid {col_border};
    border-radius: 8px;
}}
QFrame#weekDayColToday {{
    background-color: {col_bg};
    border: 1.5px solid {col_today_border};
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
    padding: 3px 0;
}}
"""


# ── 日程字号（用户可调）──────────────────────────────────────
# 默认值与两套主题内置值保持一致：月视图 10px、周·列表视图 13px。
DEFAULT_GRID_FONT = 10
DEFAULT_LIST_FONT = 13
_FONT_RANGE = (9, 24)

_EVENT_FONT_COLORS = {
    "dark": {
        "grid_time": "#9aa7b8",
        "grid_title": "#eaf2ff",
        "more": "#9aa7b8",
        "list_time": "#9aa7b8",
        "list_time_past": "rgba(234,242,255,0.52)",
        "list_time_current": "#34d399",
        "list_title": "#eaf2ff",
        "list_title_past": "#9aa7b8",
        "list_meta": "#9aa7b8",
    },
    "light": {
        "grid_time": "#6b7684",
        "grid_title": "#1a2029",
        "more": "#6b7684",
        "list_time": "#6b7684",
        "list_time_past": "rgba(26,32,41,0.52)",
        "list_time_current": "#0f9d70",
        "list_title": "#1a2029",
        "list_title_past": "#6b7684",
        "list_meta": "#6b7684",
    },
}


def _clamp_font(value, fallback: int) -> int:
    try:
        value = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(_FONT_RANGE[0], min(_FONT_RANGE[1], value))


def _event_font_rules(
    name: str,
    grid_font: int = DEFAULT_GRID_FONT,
    list_font: int = DEFAULT_LIST_FONT,
) -> str:
    """日程字号覆盖规则，追加在主题末尾（同名选择器后定义者生效）。

    月视图日格内的日程是单行布局（时间 + 标题），行高必须随字号一起放开，
    否则字号调大会被写死的 min/max-height 裁掉。
    """
    grid_font = _clamp_font(grid_font, DEFAULT_GRID_FONT)
    list_font = _clamp_font(list_font, DEFAULT_LIST_FONT)
    grid_sub = max(8, grid_font - 1)   # 月视图：时间 / "更多"
    list_sub = max(9, list_font - 2)   # 周·列表视图：时间 / 次要信息
    row_min = grid_font + 6            # 默认 10px → 16/18px，与历史一致
    row_max = grid_font + 8
    c = _EVENT_FONT_COLORS["light" if name == "light" else "dark"]
    return f"""
/* ── 日程字号（用户可调）── */
QFrame#gridEvent, QFrame#gridEventMultiDay {{
    min-height: {row_min}px;
    max-height: {row_max}px;
}}
QLabel#gridEventTime {{ font-size: {grid_sub}px; color: {c["grid_time"]}; }}
QLabel#gridEventTitle {{ font-size: {grid_font}px; color: {c["grid_title"]}; }}
QLabel#moreLabel {{ font-size: {grid_sub}px; color: {c["more"]}; padding: 0px 2px; }}
QLabel#eventTime {{ font-size: {list_sub}px; color: {c["list_time"]}; font-weight: 600; }}
QLabel#eventTimePast {{ font-size: {list_sub}px; color: {c["list_time_past"]}; font-weight: 600; }}
QLabel#eventTimeCurrent {{ font-size: {list_sub}px; color: {c["list_time_current"]}; font-weight: 600; }}
QLabel#eventTitle {{ font-size: {list_font}px; color: {c["list_title"]}; font-weight: 500; }}
QLabel#eventTitlePast {{ font-size: {list_font}px; color: {c["list_title_past"]}; font-weight: 500; }}
QLabel#eventMeta {{ font-size: {list_sub}px; color: {c["list_meta"]}; }}
"""


def _skin_rules(name: str) -> str:
    """外观重塑层：把 token-monitor 的设计语言覆盖到飞书骨架之上。

    为什么是「覆写」而不是重写：原有 1697 行 QSS 里有大量布局约束
    （min-height、padding、grid 内边距），那些是功能性的、与视觉风格无关。
    这里只重定义颜色 / 边框 / 圆角 / 字体族，靠 QSS「后定义者生效」的
    层叠规则压在上面，尺寸一律不碰——所以日历的密度、日格能放下几条
    日程、按钮点击区域，全部保持原样。

    令牌来自 theme.py，语义名与原项目 tokens.css 一一对应。
    """
    t = theme.tokens(name)
    dark = theme.is_dark(name)
    # 日格与日程卡在深色下靠「白 alpha」堆叠出层次，浅色下必须反过来用
    # 「黑 alpha」，否则白底上叠白会彻底消失。
    cell_bg = "rgba(255,255,255,0.05)" if dark else "rgba(12,16,22,0.045)"
    cell_bg_hover = "rgba(255,255,255,0.085)" if dark else "rgba(12,16,22,0.075)"
    cell_other = "rgba(255,255,255,0.016)" if dark else "rgba(12,16,22,0.022)"
    head_bg = t["nav_bg"]
    # 下拉箭头要自己给图：QSS 一旦给 ::drop-down 设了宽度，Qt 就不再画
    # 默认箭头，只留一个空白的右内边距
    chevron = "assets/chevron-down.svg" if dark else "assets/chevron-down-dark.svg"
    chevron_up = "assets/chevron-up.svg" if dark else "assets/chevron-up-dark.svg"
    # 未勾选的方框要在组框表面上看得见轮廓，line_strong 在深色下偏淡
    box_border = "rgba(255,255,255,0.26)" if dark else "rgba(12,16,22,0.22)"

    return f"""
/* ═══════════════════════════════════════════════════════════
   外观层 · 覆盖颜色/边框/圆角/字族，不改布局尺寸
   令牌见 theme.py；数值体系移植自 token-monitor/tokens.css
   ═══════════════════════════════════════════════════════════ */

/* ── 台面 ── */
QMainWindow {{
    background-color: transparent;
}}
QWidget#appSurface, QWidget#monthView, QWidget#weekView,
QWidget#gridContainer, QWidget#viewStack {{
    background-color: transparent;
}}
QMainWindow, QDialog {{
    background-color: {t["bg"]};
    color: {t["text"]};
    font-family: {FONT_STACK};
}}
/* 别把 QWidget 写进上面那一条：QSS 的 QWidget 会连 QLabel / QCheckBox
   一起刷成窗口底色，落在比背景更亮的组框表面（surface）上就是一道道
   深色横条——设置窗的复选框曾经就是这副样子。所以底色只给窗口和
   对话框架，字体/文字颜色另立一条不带 background 的规则。 */
QWidget {{
    color: {t["text"]};
    font-family: {FONT_STACK};
}}
QLabel, QCheckBox, QRadioButton {{
    background-color: transparent;
}}
QDialog {{
    background-color: {t["bg"]};
}}

/* 焦点环：细一档，用青蓝而不是纯蓝 */
QPushButton:focus-visible, QLineEdit:focus-visible, QTextEdit:focus-visible,
QComboBox:focus-visible, QDateTimeEdit:focus-visible, QSpinBox:focus-visible,
QCheckBox:focus-visible, QRadioButton:focus-visible, QListWidget:focus-visible,
QToolButton:focus-visible, QTabWidget:focus-visible {{
    outline: 2px solid {t["accent"]};
    outline-offset: 1px;
}}

/* ── 顶部：半透明玻璃条，让背景光带透上来 ── */
QFrame#headerBar {{
    background-color: {head_bg};
    border: none;
    border-bottom: 1px solid {t["line_soft"]};
}}
QLabel#headerTitle {{
    color: {t["text_strong"]};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.01em;
}}
QFrame#monthBar {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {t["line_soft"]};
}}
QLabel#headerDate {{
    color: {t["muted"]};
    font-family: {MONO_STACK};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
}}

/* ── 分段控件：玻璃槽 + 白色滑块 ── */
QFrame#segmented {{
    background-color: {t["surface"]};
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QPushButton#toggleBtn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: {t["muted"]};
    font-size: 11px;
    font-weight: 600;
}}
QPushButton#toggleBtn:hover {{
    color: {t["text_strong"]};
    background-color: {t["surface"]};
}}
QPushButton#toggleBtnActive {{
    background-color: {t["btn_primary_bg"]};
    border: none;
    border-radius: 8px;
    color: {t["btn_primary_fg"]};
    font-weight: 700;
    font-size: 11px;
}}

/* ── 图标按钮 ── */
QPushButton#iconBtn, QToolButton#iconBtn, QToolButton#moreBtn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: {t["muted"]};
    font-size: 14px;
}}
QPushButton#iconBtn:hover, QToolButton#iconBtn:hover, QToolButton#moreBtn:hover {{
    background-color: {t["surface_2"]};
    color: {t["text_strong"]};
}}
QPushButton#iconBtn:pressed, QToolButton#iconBtn:pressed,
QToolButton#moreBtn:pressed, QToolButton#moreBtn:checked {{
    background-color: {t["surface_2"]};
}}
QPushButton#closeBtn, QToolButton#closeBtn {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: {t["muted"]};
}}
QPushButton#closeBtn:hover, QToolButton#closeBtn:hover {{
    background-color: {theme.alpha(t["danger"], 0.18)};
    color: {t["danger_hover"]};
}}

/* 主操作：纯白（原项目最克制的一笔——强调色只给渐变，主按钮不给） */
QPushButton#addBtn {{
    background-color: {t["btn_primary_bg"]};
    border: none;
    border-radius: 9px;
    color: {t["btn_primary_fg"]};
    font-weight: 700;
}}
QPushButton#addBtn:hover {{
    background-color: {t["btn_primary_hover"]};
}}
QPushButton#addBtn:pressed {{
    background-color: {t["btn_primary_bg"]};
}}
QPushButton#todayBtn {{
    background-color: {t["surface"]};
    border: 1px solid {t["line"]};
    border-radius: 999px;
    color: {t["text"]};
    font-size: 11px;
    font-weight: 600;
    padding: 3px 12px;
}}
QPushButton#todayBtn:hover {{
    background-color: {t["surface_2"]};
    border-color: {t["line_strong"]};
    color: {t["text_strong"]};
}}

/* ── 星期表头：小号大写、字距放开 ── */
QLabel#weekDay {{
    color: {t["eyebrow"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
}}
QLabel#weekDayWeekend {{
    color: {t["soft"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.08em;
}}

/* 日格：一层薄面，不描边。相邻格子的 1px 边会叠成 2px 亮线，
   在深色底上像砖缝；用透明边保持盒模型尺寸、视觉上只留面块的间隙 */
QFrame#dayCell {{
    background-color: {cell_bg};
    border: 1px solid transparent;
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellHover {{
    background-color: {cell_bg_hover};
    border: 1px solid {t["line_strong"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellOther {{
    background-color: {cell_other};
    border: 1px solid transparent;
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellOtherHover {{
    background-color: {cell_bg};
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
/* 今天：青蓝描边 + 极淡的同色底，是全界面唯一的「发光」元素 */
QFrame#dayCellToday {{
    background-color: {theme.alpha(t["accent_from"], 0.075)};
    border: 1.5px solid {t["accent_from"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellTodayHover {{
    background-color: {theme.alpha(t["accent_from"], 0.12)};
    border: 1.5px solid {t["accent_from"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellDrop, QFrame#dayCellOtherDrop, QFrame#dayCellTodayDrop {{
    background-color: {theme.alpha(t["accent_to"], 0.14)};
    border: 1.5px dashed {t["accent"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellCursor {{
    border: 1.5px solid {t["accent"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellOtherCursor {{
    border: 1.5px solid {t["glass_border_soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#dayCellTodayCursor {{
    border: 1.5px solid {t["accent_from"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}

/* 日号：等宽数字——一列日期上下对齐，扫视时不会左右跳 */
QLabel#dayNum {{
    font-family: {MONO_STACK};
    font-size: 11px;
    font-weight: 600;
    color: {t["text"]};
}}
QLabel#dayNumOther {{
    font-family: {MONO_STACK};
    font-size: 11px;
    color: {t["soft"]};
}}
QLabel#dayNumToday {{
    font-family: {MONO_STACK};
    font-size: 11px;
    font-weight: 800;
    color: {t["accent_from"]};
}}

/* ── 月视图日程条：2px 左侧色条，不是整块实底 ── */
QFrame#gridEvent {{
    background-color: {t["event_ink"]};
    border: none;
    border-left: 2px solid {t["accent"]};
    border-radius: 4px;
}}
QFrame#gridEvent:hover {{
    background-color: {t["event_ink_hover"]};
}}
QFrame#gridEventMultiDay {{
    background-color: {theme.alpha(t["success"], 0.14)};
    border: none;
    border-left: 2px solid {t["success"]};
    border-radius: 4px;
}}
QFrame#gridEventMultiDay:hover {{
    background-color: {theme.alpha(t["success"], 0.24)};
}}
QLabel#gridEventTime {{
    font-family: {MONO_STACK};
    color: {t["muted"]};
    font-weight: 600;
}}
QLabel#gridEventTitle {{
    color: {t["text"]};
    font-weight: 500;
}}
QLabel#moreLabel {{
    font-family: {MONO_STACK};
    font-size: 9px;
    color: {t["muted"]};
}}
QLabel#moreLabel:hover {{
    color: {t["accent"]};
}}

/* ── 周视图日程卡：玻璃面 + 左色条 ── */
QFrame#eventCard {{
    background-color: {t["glass"]};
    border: 1px solid {t["glass_border_soft"]};
    border-left: 2px solid {t["accent"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#eventCard:hover {{
    background-color: {t["glass_strong"]};
    border-color: {t["line"]};
    border-left-color: {t["accent"]};
}}
QFrame#eventCardPast {{
    background-color: {t["surface"]};
    border: 1px solid {t["line_soft"]};
    border-left: 2px solid {t["soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#eventCardCurrent {{
    background-color: {theme.alpha(t["success"], 0.10)};
    border: 1px solid {theme.alpha(t["success"], 0.28)};
    border-left: 2px solid {t["success"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#eventCardCont {{
    background-color: {cell_other};
    border: 1px solid transparent;
    border-left: 2px solid {t["line_strong"]};
    border-radius: {theme.RADIUS["sm"]}px;
}}
QFrame#eventCardCont:hover {{
    background-color: {cell_bg};
}}
QFrame#eventCardAllDay {{
    background-color: {theme.alpha(t["success"], 0.12)};
    border: none;
    border-left: 2px solid {t["success"]};
    border-radius: 6px;
}}
QFrame#eventCardAllDay:hover {{
    background-color: {theme.alpha(t["success"], 0.20)};
}}
QFrame#weekAllDayBar {{
    background-color: {cell_other};
    border: 1px solid {t["line_soft"]};
    border-radius: 8px;
}}

QLabel#eventTime {{
    font-family: {MONO_STACK};
    color: {t["muted"]};
    font-weight: 600;
    letter-spacing: -0.01em;
}}
QLabel#eventTimePast {{
    font-family: {MONO_STACK};
    color: {t["soft"]};
    font-weight: 600;
}}
QLabel#eventTimeCurrent {{
    font-family: {MONO_STACK};
    color: {t["success"]};
    font-weight: 700;
}}
QLabel#eventTitle {{
    color: {t["text"]};
    font-weight: 500;
}}
QLabel#eventTitlePast {{
    color: {t["muted"]};
    font-weight: 400;
}}
QLabel#eventMeta {{
    color: {t["muted"]};
}}
QPushButton#deleteBtn {{
    background-color: transparent;
    border: none;
    border-radius: 6px;
    color: {t["soft"]};
}}
QPushButton#deleteBtn:hover {{
    background-color: {theme.alpha(t["danger"], 0.16)};
    color: {t["danger_hover"]};
}}

/* ── 周视图列 ── */
QFrame#weekDayCol {{
    background-color: {cell_other};
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["md"]}px;
}}
QFrame#weekDayColToday {{
    background-color: {theme.alpha(t["accent_from"], 0.05)};
    border: 1px solid {t["accent_from"]};
    border-radius: {theme.RADIUS["md"]}px;
}}
QFrame#weekDayColDrop {{
    background-color: {theme.alpha(t["accent_to"], 0.10)};
    border: 1.5px dashed {t["accent"]};
    border-radius: {theme.RADIUS["md"]}px;
}}
QLabel#weekColDate {{
    font-family: {MONO_STACK};
    font-size: 11px;
    font-weight: 700;
    color: {t["text"]};
}}
QLabel#weekColAdd {{
    color: {t["soft"]};
    font-size: 13px;
    border-radius: 6px;
}}
QLabel#weekColAdd:hover {{
    color: {t["text_strong"]};
    background-color: {t["surface_2"]};
}}
QLabel#weekRangeLabel {{
    font-family: {MONO_STACK};
    font-size: 11px;
    font-weight: 600;
    color: {t["muted"]};
}}

/* ── 表单控件 ── */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit, QSpinBox {{
    background-color: {t["surface"]};
    border: 1px solid {t["line"]};
    border-radius: {theme.RADIUS["sm"]}px;
    padding: 5px 8px;
    color: {t["text"]};
    selection-background-color: {t["accent"]};
    selection-color: {t["accent_ink"]};
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus,
QDateTimeEdit:focus, QSpinBox:focus {{
    border: 1px solid {t["accent"]};
    background-color: {t["surface_2"]};
}}
QLineEdit:disabled, QTextEdit:disabled, QComboBox:disabled,
QDateTimeEdit:disabled, QSpinBox:disabled {{
    color: {t["soft"]};
    background-color: {cell_other};
}}
QComboBox QAbstractItemView {{
    background-color: {t["glass_strong"]};
    border: 1px solid {t["line"]};
    border-radius: 8px;
    selection-background-color: {t["surface_2"]};
    selection-color: {t["text_strong"]};
    outline: none;
}}

/* ── 按钮体系 ── */
QPushButton#primaryBtn, QDialogButtonBox QPushButton:default, QMessageBox QPushButton:default {{
    background-color: {t["btn_primary_bg"]};
    border: none;
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["btn_primary_fg"]};
    font-weight: 700;
    padding: 6px 16px;
}}
QPushButton#primaryBtn:hover, QDialogButtonBox QPushButton:default:hover,
QMessageBox QPushButton:default:hover {{
    background-color: {t["btn_primary_hover"]};
}}
QPushButton#primaryBtn:pressed, QDialogButtonBox QPushButton:default:pressed {{
    background-color: {t["btn_primary_bg"]};
}}
QPushButton#primaryBtn:disabled, QDialogButtonBox QPushButton:default:disabled {{
    background-color: {t["surface_2"]};
    color: {t["soft"]};
}}
/* 对话框里的主按钮要带 QDialog 前缀重写一遍：基础层的
   QDialog QPushButton#primaryBtn 靠这个前缀压过了上面那条，
   按钮一直是老的飞书蓝 #3370FF，和青蓝渐变的主色调对不上。 */
QDialog QPushButton#primaryBtn {{
    background-color: {t["btn_primary_bg"]};
    border: 1px solid transparent;
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["btn_primary_fg"]};
    padding: 6px 16px;
    font-weight: 700;
}}
QDialog QPushButton#primaryBtn:hover {{
    background-color: {t["btn_primary_hover"]};
    border-color: transparent;
}}
QDialog QPushButton#primaryBtn:pressed {{
    background-color: {t["btn_primary_bg"]};
    border-color: transparent;
}}
QDialog QPushButton#primaryBtn:disabled {{
    background-color: {t["surface_2"]};
    border-color: transparent;
    color: {t["soft"]};
}}
QPushButton#secondaryBtn, QDialogButtonBox QPushButton, QMessageBox QPushButton {{
    background-color: transparent;
    border: 1px solid {t["line_strong"]};
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["text"]};
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#secondaryBtn:hover, QDialogButtonBox QPushButton:hover,
QMessageBox QPushButton:hover {{
    background-color: {t["surface_2"]};
    border-color: {t["glass_border"]};
    color: {t["text_strong"]};
}}
QPushButton#secondaryBtn:pressed, QDialogButtonBox QPushButton:pressed {{
    background-color: {t["surface"]};
}}
QPushButton#secondaryBtn:disabled, QDialogButtonBox QPushButton:disabled {{
    color: {t["soft"]};
    border-color: {t["line_soft"]};
}}
QPushButton#dangerBtn {{
    background-color: transparent;
    border: 1px solid {theme.alpha(t["danger"], 0.45)};
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["danger"]};
    padding: 6px 14px;
    font-weight: 600;
}}
QPushButton#dangerBtn:hover {{
    background-color: {theme.alpha(t["danger"], 0.14)};
    border-color: {theme.alpha(t["danger"], 0.7)};
    color: {t["danger_hover"]};
}}
QPushButton#linkBtn {{
    background-color: transparent;
    border: none;
    color: {t["link"]};
    font-weight: 500;
}}
QPushButton#linkBtn:hover {{
    color: {t["accent"]};
}}
/* 统计窗的 ‹ › 导航：28px 见方，不能带 secondaryBtn 的横向 padding */
QPushButton#navBtn {{
    background-color: {t["surface"]};
    border: 1px solid {t["line"]};
    border-radius: 8px;
    color: {t["text"]};
    padding: 0px;
    font-size: 13px;
}}
QPushButton#navBtn:hover {{
    background-color: {t["surface_2"]};
    border-color: {t["glass_border"]};
}}

/* ── 滚动条：细、无轨道感 ── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {t["scroll_handle"]};
    border-radius: 4px;
    min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{
    background: {t["scroll_handle_hover"]};
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {t["scroll_handle"]};
    border-radius: 4px;
    min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {t["scroll_handle_hover"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0; border: none; background: none;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: none;
}}
QScrollArea {{
    background: transparent;
    border: none;
}}

/* ── 菜单：玻璃面板 ── */
QMenu {{
    background-color: {t["glass_strong"]};
    border: 1px solid {t["glass_border_soft"]};
    border-radius: {theme.RADIUS["md"]}px;
    padding: 6px;
    color: {t["text"]};
}}
QMenu::item {{
    background-color: transparent;
    border-radius: 8px;
    padding: 6px 18px 6px 12px;
    color: {t["text"]};
}}
QMenu::item:selected {{
    background-color: {t["surface_2"]};
    color: {t["text_strong"]};
}}
QMenu::item:pressed {{
    background-color: {t["surface"]};
}}
QMenu::item:disabled {{
    color: {t["soft"]};
}}
QMenu::separator {{
    height: 1px;
    background: {t["line_soft"]};
    margin: 5px 8px;
}}
QMenu::indicator {{
    width: 14px; height: 14px;
}}

/* ── 标签页 ── */
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    border: none;
    border-bottom: 1.5px solid transparent;
    padding: 7px 14px;
    color: {t["muted"]};
    font-weight: 600;
}}
QTabBar::tab:hover:!selected {{
    color: {t["text"]};
}}
QTabBar::tab:selected {{
    color: {t["text_strong"]};
    border-bottom: 1.5px solid {t["accent"]};
}}
/* 对话框里的标签页要收窄：基础层给的是 18px 内边距 + 68px 最小宽度，
   五个中文短标签（通用/提醒/账号/外观/关于）在 520px 宽的设置窗里
   撑出滚动箭头，「关于」直接被藏掉。选择器要连 QDialog 前缀一起写，
   否则特异性输给基础层的 QDialog QTabBar::tab。 */
QDialog QTabBar::tab {{
    background-color: transparent;
    border: none;
    border-bottom: 1.5px solid transparent;
    min-width: 0px;
    padding: 7px 13px;
    margin-right: 2px;
    color: {t["muted"]};
    font-size: 13px;
    font-weight: 600;
}}
QDialog QTabBar::tab:hover:!selected {{
    background-color: transparent;
    color: {t["text"]};
}}
QDialog QTabBar::tab:selected {{
    background-color: transparent;
    color: {t["text_strong"]};
    border-bottom: 1.5px solid {t["accent"]};
}}

/* ── 提示气泡 ── */
QToolTip {{
    background-color: {t["glass_strong"]};
    border: 1px solid {t["glass_border_soft"]};
    border-radius: 8px;
    color: {t["text_strong"]};
    padding: 5px 9px;
}}

/* ── 进度条 ── */
QProgressBar {{
    background-color: {t["surface"]};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background-color: {t["accent"]};
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t["accent_from"]}, stop:1 {t["accent_to"]});
    border-radius: 3px;
}}

/* ── 复选框 / 单选框 ── */
/* 复选框只调间距与文字色：一旦用 QSS 给 ::indicator 设 background/image，
   Qt 就不再画系统的勾选标记，只剩一个纯色方块——分不清「已选」和「禁用」。
   尺寸与勾选交给系统风格，深色下会自动适配。 */
QCheckBox, QRadioButton {{
    color: {t["text"]};
    spacing: 7px;
}}
/* 勾选框只换配色，不动尺寸和勾选标记：基础层用飞书蓝 #3370FF 的老
   配色，落在青蓝渐变的新台面上像一块外来补丁。background / border 换
   成令牌，image 仍交给 assets/check.svg（白描边），勾选态照样看得见。 */
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {t["line_strong"]};
    background-color: {t["surface_2"]};
}}
QCheckBox::indicator {{
    border-radius: 4px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {t["accent"]};
}}
QCheckBox::indicator:checked {{
    background-color: {t["accent"]};
    border-color: {t["accent"]};
    image: url(assets/check.svg);
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
/* 选中态用「外环 + 中空」，不是实心点：16px 里留 6px 的洞，
   外面 5px 全是强调色，一眼能看出这是个选中了的圆钮。 */
QRadioButton::indicator:checked {{
    background-color: {t["surface"]};
    border: 5px solid {t["accent"]};
    width: 6px;
    height: 6px;
    border-radius: 8px;
}}

QGroupBox {{
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["md"]}px;
    /* 同 QDialog QGroupBox：margin 要小，padding 不要四值 */
    margin-top: 8px;
    padding: 2px 0px 0px 0px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    top: 0px;
    left: 12px;
    padding: 0 6px;
    background-color: transparent;
    color: {t["muted"]};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.06em;
}}

QSlider::groove:horizontal {{
    height: 4px;
    background: {t["surface_2"]};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    background: {t["btn_primary_bg"]};
    border: 1px solid {t["line"]};
}}
QSlider::handle:horizontal:hover {{
    background: {t["accent"]};
    border-color: {t["accent"]};
}}
QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {t["accent_from"]}, stop:1 {t["accent_to"]});
    border-radius: 2px;
}}

/* ── 加载 / 授权 / 空态面板 ── */
QLabel#stateIcon {{
    color: {t["accent"]};
}}
QLabel#stateTitle {{
    color: {t["text_strong"]};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#stateMessage {{
    color: {t["muted"]};
}}
QTextEdit#stateDetail, QTextEdit#errorDisplay {{
    background-color: {cell_other};
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["muted"]};
    font-family: {MONO_STACK};
    font-size: 11px;
}}
QTextEdit#codeBox {{
    background-color: {cell_other};
    border: 1px solid {t["line_soft"]};
    border-radius: {theme.RADIUS["sm"]}px;
    color: {t["text"]};
    font-family: {MONO_STACK};
    font-size: 11px;
}}
QLabel#statusLabel {{
    color: {t["muted"]};
    font-size: 10px;
}}
QLabel#emptyLabel {{
    color: {t["muted"]};
    font-size: 12px;
}}
QLabel#formError {{
    color: {t["danger"]};
    font-size: 11px;
}}
/* 提示行的另外两种语义色。ui_common.set_message_kind 按 kind 切 objectName，
   各处不再自己写死 #FF8800 / #2EA121。 */
QLabel#formWarn {{
    color: {t["warn_text"]};
    font-size: 11px;
}}
QLabel#formSuccess {{
    color: {t["success"]};
    font-size: 11px;
}}
QLabel#resizeGrip {{
    color: {t["soft"]};
}}

/* ── 搜索结果 ── */
QLineEdit#searchInput {{
    background-color: {t["surface"]};
    border: 1px solid {t["line"]};
    border-radius: {theme.RADIUS["sm"]}px;
    padding: 7px 10px;
    color: {t["text"]};
}}
QLineEdit#searchInput:focus {{
    border: 1px solid {t["accent"]};
    background-color: {t["surface_2"]};
}}
QListWidget#searchResultList {{
    background-color: transparent;
    border: none;
    outline: none;
}}
QListWidget#searchResultList::item {{
    background-color: transparent;
    border-radius: 8px;
    padding: 6px 8px;
    color: {t["text"]};
}}
QListWidget#searchResultList::item:hover {{
    background-color: {t["surface"]};
}}
QListWidget#searchResultList::item:selected {{
    background-color: {t["event_ink"]};
    color: {t["text_strong"]};
}}

/* ── 对话框内容 ── */
QLabel#detailTitle {{
    color: {t["text_strong"]};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#detailLabel {{
    color: {t["muted"]};
    font-size: 11px;
    font-weight: 600;
}}
QLabel#detailValue {{
    color: {t["text"]};
    font-size: 12px;
}}
QLabel#confirmTitle {{
    color: {t["text_strong"]};
    font-size: 14px;
    font-weight: 600;
}}
QLabel#confirmMessage {{
    color: {t["muted"]};
    font-size: 12px;
}}
/* 确认框图标圆徽：基础层（_menu_dialog_rules）这里还是飞书蓝 #3370FF 和
   品牌红 #F54A45，特异性与这里相同，只能靠外观层排在最后压色。 */
QLabel#confirmIcon, QLabel#confirmIconDanger {{
    border: 1px solid {t["line_soft"]};
    border-radius: 14px;
    font-size: 14px;
    font-weight: 700;
}}
QLabel#confirmIcon {{
    background-color: {t["accent_soft"]};
    color: {t["accent"]};
}}
QLabel#confirmIconDanger {{
    background-color: {t["danger_soft"]};
    border-color: {t["danger_soft"]};
    color: {t["danger"]};
}}
QFrame#dialogSeparator {{
    background-color: {t["line_soft"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
/* 二维码卡片两套主题都用白底：深浅模块必须有足够对比度，浅色主题下
   主按钮那种深底会把二维码变成反色，部分手机扫不出来。 */
QFrame#qrCard {{
    background-color: #ffffff;
    border: 1px solid {t["line"]};
    border-radius: {theme.RADIUS["md"]}px;
}}
/* 卡片里的占位文字用固定墨色（qr_ink），理由和卡片白底一样：它不在主题面上。 */
QLabel#qrPlaceholder {{
    color: {t["qr_ink"]};
    background-color: transparent;
    font-size: 12px;
}}
QLabel#loginTitle {{
    color: {t["text_strong"]};
    font-size: 16px;
    font-weight: 600;
}}
/* 取色器色块：色值本身是数据（内联给），描边是主题（这里给）。
   以前选中态写死 #FFFFFF，浅色主题下白描边落在白卡上等于没有选中。 */
QPushButton#colorSwatch {{
    border: 1px solid {t["line_strong"]};
    border-radius: 11px;
}}
QPushButton#colorSwatch:hover {{
    border: 1px solid {t["text_strong"]};
}}
QPushButton#colorSwatchSelected {{
    border: 3px solid {t["btn_primary_bg"]};
    border-radius: 11px;
}}
QLabel#loginBadge {{
    color: {t["muted"]};
    background-color: {t["surface"]};
    border: 1px solid {t["line_soft"]};
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 10px;
    font-weight: 600;
}}

/* ── Toast ── */
QFrame#toast {{
    background-color: {t["glass_strong"]};
    border: 1px solid {t["glass_border_soft"]};
    border-radius: {theme.RADIUS["md"]}px;
}}
/* 图标按 kind 切 objectName（toastIconInfo / Success / Warning / Error）。
   以前 ui_common 用内联 setStyleSheet 写死飞书四色（#3370FF/#34C724/#FF8800/
   #F54A45），内联优先级压过一切样式表，切主题时它纹丝不动。 */
QLabel#toastIcon, QLabel#toastIconInfo, QLabel#toastIconSuccess,
QLabel#toastIconWarning, QLabel#toastIconError {{
    font-size: 14px;
    font-weight: 700;
    background-color: transparent;
}}
QLabel#toastIcon, QLabel#toastIconInfo {{
    color: {t["accent"]};
}}
QLabel#toastIconSuccess {{
    color: {t["success"]};
}}
QLabel#toastIconWarning {{
    color: {t["warn_text"]};
}}
QLabel#toastIconError {{
    color: {t["danger"]};
}}
QLabel#toastMsg {{
    color: {t["text_strong"]};
    font-size: 12px;
}}
QPushButton#toastAction {{
    background-color: transparent;
    border: none;
    color: {t["link"]};
    font-size: 11px;
    font-weight: 700;
}}
QPushButton#toastAction:hover {{
    color: {t["accent"]};
}}
QPushButton#toastClose {{
    background-color: transparent;
    border: none;
    color: {t["soft"]};
    border-radius: 6px;
}}
QPushButton#toastClose:hover {{
    background-color: {t["surface_2"]};
    color: {t["text"]};
}}
/* ── 设置窗：表单骨架 ──
   五个页面共用一套「字段名 + 控件」行，控件宽度和高度都统一在这里，
   代码里不再各写各的。 */
QScrollArea#settingsScroll, QScrollArea#settingsScroll > QWidget > QWidget,
QWidget#settingsPage {{
    background-color: transparent;
    border: none;
}}
/* 基础层把 QWidget 也写进了底色选择器，行容器跟着被刷上窗口底色：
   浅色主题下每个组框里都多出一块浅灰条，看着像控件没对齐。这里只给
   行容器去掉底色，别去动组框自己的表面色。 */
QWidget#formRow {{
    background-color: transparent;
}}
QDialog QCheckBox::indicator, QDialog QRadioButton::indicator {{
    border: 1px solid {box_border};
}}
QDialog QGroupBox::title {{
    color: {t["text_strong"]};
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0px;
    padding: 0 7px;
    left: 12px;
}}
QLabel#fieldCap {{
    color: {t["muted"]};
    font-size: 12px;
    background: transparent;
}}
QLabel#valueLabel {{
    color: {t["text_strong"]};
    font-family: {MONO_STACK};
    font-size: 12px;
    background: transparent;
}}
QLabel#aboutTitle {{
    color: {t["text_strong"]};
    font-size: 18px;
    font-weight: 700;
    background: transparent;
}}
QFrame#dialogRule {{
    background-color: {t["line_soft"]};
    border: none;
    max-height: 1px;
    min-height: 1px;
}}
/* 输入控件统一高度。原来是 7px 上下内边距 + 13px 字 = 41px，桌面设置窗里
   偏高，而且 QSpinBox / QComboBox / QTimeEdit 各算各的，行与行对不齐。 */
QDialog QLineEdit, QDialog QTextEdit, QDialog QPlainTextEdit, QDialog QComboBox,
QDialog QDateTimeEdit, QDialog QDateEdit, QDialog QTimeEdit,
QDialog QSpinBox, QDialog QDoubleSpinBox {{
    padding: 4px 9px;
    min-height: 22px;
    border-radius: {theme.RADIUS["sm"]}px;
}}
/* 别在这里设 min-width：QStyleSheetStyle 会用 setMinimumWidth 覆盖
   setFixedWidth 的约束，控件宽度就变成 sizeHint 而不再是代码指定的值
   （下拉框 150 变成 135，一行里的控件右边界对不齐）。 */
/* 与数字框同高：spin 因为内部有两个 9px 箭头，sizeHint 天然比 combo 高 4px，
   同一列里一眼能看出参差。 */
QDialog QComboBox {{
    padding-right: 4px;
    min-height: 26px;
}}
QDialog QComboBox::down-arrow {{
    image: url({chevron});
    width: 11px;
    height: 11px;
}}
/* 数字框右侧的上下按钮不设样式时会用系统白底，圆角外露出一块直角。
   一旦定制 ::up-button / ::down-button，Qt 就不再画默认箭头，所以箭头
   也得自己给图。 */
QDialog QSpinBox, QDialog QDoubleSpinBox, QDialog QTimeEdit, QDialog QDateEdit,
QDialog QDateTimeEdit {{
    padding-right: 20px;
}}
QDialog QSpinBox::up-arrow, QDialog QDoubleSpinBox::up-arrow,
QDialog QTimeEdit::up-arrow, QDialog QDateEdit::up-arrow,
QDialog QDateTimeEdit::up-arrow {{
    image: url({chevron_up});
    width: 9px;
    height: 9px;
}}
QDialog QSpinBox::down-arrow, QDialog QDoubleSpinBox::down-arrow,
QDialog QTimeEdit::down-arrow, QDialog QDateEdit::down-arrow,
QDialog QDateTimeEdit::down-arrow {{
    image: url({chevron});
    width: 9px;
    height: 9px;
}}
QDialog QSpinBox::up-button, QDialog QDoubleSpinBox::up-button,
QDialog QTimeEdit::up-button, QDialog QDateEdit::up-button,
QDialog QDateTimeEdit::up-button {{
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 17px;
    margin: 1px 1px 0 0;
    border: none;
    background: transparent;
}}
QDialog QSpinBox::down-button, QDialog QDoubleSpinBox::down-button,
QDialog QTimeEdit::down-button, QDialog QDateEdit::down-button,
QDialog QDateTimeEdit::down-button {{
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 17px;
    margin: 0 1px 1px 0;
    border: none;
    background: transparent;
}}
/* 基础层是 QDialog QPushButton#secondaryBtn（7px/18px + min-height 18），
   比外观层不带前缀的那条特异性高，按钮会比输入框高出 3px，同一行里
   基线不齐。带上前缀重写一遍。 */
QDialog QPushButton#secondaryBtn, QDialog QPushButton#dangerBtn,
QDialog QPushButton#linkBtn {{
    padding: 4px 14px;
    min-height: 22px;
}}
QDialog QPushButton#linkBtn {{
    padding: 4px 2px;
    font-weight: 600;
}}
QDialog QPushButton#secondaryBtn:disabled, QDialog QPushButton#primaryBtn:disabled {{
    color: {t["soft"]};
    background-color: {t["surface"]};
    border-color: {t["line_soft"]};
}}
/* 禁用态要看得出来：只灰一点点在深色底上等于没提示，
   免打扰时段那两个时间框关闭时几乎和可用时一样。 */
QDialog QLineEdit:disabled, QDialog QTextEdit:disabled, QDialog QPlainTextEdit:disabled,
QDialog QComboBox:disabled, QDialog QDateTimeEdit:disabled, QDialog QDateEdit:disabled,
QDialog QTimeEdit:disabled, QDialog QSpinBox:disabled, QDialog QDoubleSpinBox:disabled {{
    background-color: {t["stage"]};
    color: {t["soft"]};
    border-color: {t["line_soft"]};
}}
QDialog QCheckBox:disabled, QDialog QRadioButton:disabled {{
    color: {t["soft"]};
}}
/* QAbstractSpinBox 内部有一层自己的编辑区，外层 :disabled 的 color 到不了
   文字；可用态也一样，浅色主题下数字框里的字会比同行的标签更灰。 */
QDialog QSpinBox QLineEdit, QDialog QDoubleSpinBox QLineEdit,
QDialog QTimeEdit QLineEdit, QDialog QDateEdit QLineEdit,
QDialog QDateTimeEdit QLineEdit {{
    color: {t["text"]};
    background: transparent;
}}
QDialog QTimeEdit:disabled, QDialog QDateEdit:disabled, QDialog QDateTimeEdit:disabled,
QDialog QSpinBox:disabled, QDialog QDoubleSpinBox:disabled {{
    color: {t["soft"]};
}}
QDialog QTimeEdit:disabled QLineEdit, QDialog QSpinBox:disabled QLineEdit,
QDialog QDoubleSpinBox:disabled QLineEdit {{
    color: {t["soft"]};
    background: transparent;
}}
QDialog QComboBox::drop-down {{
    width: 22px;
    border: none;
}}
"""


def get_theme(
    name: str,
    grid_font: int = DEFAULT_GRID_FONT,
    list_font: int = DEFAULT_LIST_FONT,
) -> str:
    """Get QSS stylesheet by theme name.

    grid_font / list_font 为用户可调的日程字号（px），默认与主题内置值一致。
    """
    base = LIGHT_THEME if name == "light" else DARK_THEME
    return (
        base
        + _menu_dialog_rules(name)
        + _extra_rules(name)
        + _event_font_rules(name, grid_font, list_font)
        # 外观层放最后：同特异性下后定义者生效，这是整套换肤的落点。
        # 它只覆盖颜色/边框/圆角/字族，字号仍由上面的 _event_font_rules
        # 按用户配置决定。
        + _skin_rules(name)
    )
