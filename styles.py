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

FONT_STACK = (
    '"SF Pro Text", "PingFang SC", "Microsoft YaHei UI", '
    '"Segoe UI", sans-serif'
)

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
    margin-top: 20px;
    padding: 18px 12px 12px 12px;
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
        "grid_time": "#B8C0CC",
        "grid_title": "#F0F1F2",
        "more": "#8F959E",
        "list_time": "#A9B0B8",
        "list_time_past": "#646A73",
        "list_time_current": "#4FD963",
        "list_title": "#F0F1F2",
        "list_title_past": "#646A73",
        "list_meta": "#8F959E",
    },
    "light": {
        "grid_time": "#646A73",
        "grid_title": "#1F2329",
        "more": "#8F959E",
        "list_time": "#51565D",
        "list_time_past": "#BBBFC4",
        "list_time_current": "#2EA121",
        "list_title": "#1F2329",
        "list_title_past": "#BBBFC4",
        "list_meta": "#8F959E",
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
    )
