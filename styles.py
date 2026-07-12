"""QSS stylesheets for FeishuCalendarDesktop - TRAE Work Design System.

Color tokens mapped from TRAE Work design library:
  Brand:  #4B3FE3 (primary), #6A6FFF (hover), #3F31C6 (active)
  Text:   #171717 (default), #404040 (secondary), #737373 (tertiary), #A1A1A1 (disabled)
  BG:     #FFFFFF (base), #F5F5F5 (surface), #E5E5E5 (tertiary)
  Border: rgba(115,115,115,0.12) / 0.18 / 0.36
  Status: #2F74FF (info), #15A877 (success), #FEA900 (alert), #E27900 (warning), #E8463A (error)
"""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #171717;
    color: #E5E5E5;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 600;
    color: #AAB7FF;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #737373;
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
    color: #A1A1A1;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: rgba(115, 115, 115, 0.20);
    color: #E5E5E5;
}
QPushButton#iconBtn:pressed {
    background-color: rgba(115, 115, 115, 0.36);
}

/* === Month grid === */

QLabel#weekDay {
    font-size: 11px;
    color: #737373;
    font-weight: 600;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #FF8080;
    font-weight: 600;
}

QFrame#dayCell {
    background-color: #262626;
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 6px;
}
QFrame#dayCellOther {
    background-color: #171717;
    border: 1px solid rgba(115, 115, 115, 0.08);
    border-radius: 6px;
}
QFrame#dayCellToday {
    background-color: #262626;
    border: 2px solid #4B3FE3;
    border-radius: 6px;
}

QLabel#dayNum {
    font-size: 11px;
    color: #E5E5E5;
    font-weight: 600;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #525252;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #AAB7FF;
    font-weight: 600;
}

QFrame#gridEvent {
    background-color: rgba(75, 63, 227, 0.15);
    border-radius: 4px;
    border-left: 2px solid #4B3FE3;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: rgba(75, 63, 227, 0.25);
    border-left: 2px solid #6A6FFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(21, 168, 119, 0.10);
    border-radius: 4px;
    border-left: 2px solid #15A877;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(21, 168, 119, 0.20);
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #A1A1A1;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #E5E5E5;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #525252;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #AAB7FF;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #262626;
    border-radius: 8px;
    border-left: 3px solid #4B3FE3;
}
QFrame#eventCardPast {
    background-color: #1e1e1e;
    border-radius: 8px;
    border-left: 3px solid #525252;
}
QFrame#eventCardCurrent {
    background-color: #1a2e1e;
    border-radius: 8px;
    border-left: 3px solid #15A877;
}
QFrame#eventCard:hover {
    background-color: #303030;
}

QLabel#eventTime {
    font-size: 11px;
    color: #A1A1A1;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #525252;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #15A877;
    font-weight: 600;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #E5E5E5;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #525252;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #737373;
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
    color: #525252;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #E8463A;
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
    background: rgba(115, 115, 115, 0.36);
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(115, 115, 115, 0.55);
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #262626;
    border: 1px solid rgba(115, 115, 115, 0.18);
    border-radius: 6px;
    padding: 6px 8px;
    color: #E5E5E5;
    selection-background-color: #4B3FE3;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #4B3FE3;
}

QPushButton#primaryBtn {
    background-color: #4B3FE3;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #6A6FFF;
}
QPushButton#primaryBtn:pressed {
    background-color: #3F31C6;
}
QPushButton#secondaryBtn {
    background-color: rgba(115, 115, 115, 0.12);
    color: #E5E5E5;
    border: 1px solid rgba(115, 115, 115, 0.18);
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(115, 115, 115, 0.20);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #E8463A;
    border: 1px solid #E8463A;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#dangerBtn:hover {
    background-color: #E8463A;
    color: #FFFFFF;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #525252;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #404040;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #525252;
    padding: 40px 20px;
}

QTextEdit#errorDisplay {
    background-color: #1a1a1a;
    color: #E5E5E5;
    border: 1px solid rgba(232, 70, 58, 0.3);
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(75, 63, 227, 0.3);
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: 600;
    color: #AAB7FF;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #737373;
}
QLabel#detailValue {
    font-size: 13px;
    color: #E5E5E5;
}

QGroupBox {
    border: 1px solid rgba(115, 115, 115, 0.18);
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 16px;
    color: #A1A1A1;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QCheckBox {
    color: #E5E5E5;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(115, 115, 115, 0.36);
    border-radius: 4px;
    background: #262626;
}
QCheckBox::indicator:checked {
    background: #4B3FE3;
    border-color: #4B3FE3;
}

QSpinBox {
    background-color: #262626;
    border: 1px solid rgba(115, 115, 115, 0.18);
    border-radius: 6px;
    padding: 4px 8px;
    color: #E5E5E5;
}
QSpinBox:focus {
    border: 1px solid #4B3FE3;
}

QSlider::groove:horizontal {
    background: rgba(115, 115, 115, 0.20);
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #E5E5E5;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid rgba(115, 115, 115, 0.36);
}
QSlider::sub-page:horizontal {
    background: #4B3FE3;
    border-radius: 2px;
}

QRadioButton {
    color: #E5E5E5;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(115, 115, 115, 0.36);
    border-radius: 8px;
    background: #262626;
}
QRadioButton::indicator:checked {
    border-color: #4B3FE3;
    background: #262626;
}
QRadioButton::indicator:checked::after {
    width: 10px;
    height: 10px;
    border-radius: 5px;
    background: #4B3FE3;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #FFFFFF;
    color: #171717;
    font-family: "SF Pro Text", "PingFang SC", "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: 600;
    color: #4B3FE3;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #737373;
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
    color: #737373;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: rgba(115, 115, 115, 0.12);
    color: #171717;
}
QPushButton#iconBtn:pressed {
    background-color: rgba(115, 115, 115, 0.20);
}

/* === Month grid === */

QLabel#weekDay {
    font-size: 11px;
    color: #737373;
    font-weight: 600;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #E63737;
    font-weight: 600;
}

QFrame#dayCell {
    background-color: #FFFFFF;
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 6px;
}
QFrame#dayCellOther {
    background-color: #F5F5F5;
    border: 1px solid rgba(115, 115, 115, 0.08);
    border-radius: 6px;
}
QFrame#dayCellToday {
    background-color: #FFFFFF;
    border: 2px solid #4B3FE3;
    border-radius: 6px;
}

QLabel#dayNum {
    font-size: 11px;
    color: #171717;
    font-weight: 600;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #A1A1A1;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #4B3FE3;
    font-weight: 600;
}

QFrame#gridEvent {
    background-color: rgba(75, 63, 227, 0.08);
    border-radius: 4px;
    border-left: 2px solid #4B3FE3;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: rgba(75, 63, 227, 0.16);
    border-left: 2px solid #6A6FFF;
}
QFrame#gridEventMultiDay {
    background-color: rgba(21, 168, 119, 0.08);
    border-radius: 4px;
    border-left: 2px solid #15A877;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEventMultiDay:hover {
    background-color: rgba(21, 168, 119, 0.16);
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #737373;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #171717;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #A1A1A1;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #4B3FE3;
}

/* === Event card === */

QFrame#eventCard {
    background-color: #F5F5F5;
    border-radius: 8px;
    border-left: 3px solid #4B3FE3;
}
QFrame#eventCardPast {
    background-color: #E5E5E5;
    border-radius: 8px;
    border-left: 3px solid #D4D4D4;
}
QFrame#eventCardCurrent {
    background-color: rgba(21, 168, 119, 0.08);
    border-radius: 8px;
    border-left: 3px solid #15A877;
}
QFrame#eventCard:hover {
    background-color: rgba(115, 115, 115, 0.08);
}

QLabel#eventTime {
    font-size: 11px;
    color: #737373;
    font-weight: 600;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #A1A1A1;
    font-weight: 600;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #15A877;
    font-weight: 600;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #171717;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #A1A1A1;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #737373;
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
    color: #A1A1A1;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #E8463A;
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
    background: #D4D4D4;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #BABABA;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #FFFFFF;
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 6px;
    padding: 6px 8px;
    color: #171717;
    selection-background-color: #4B3FE3;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #000000;
}

QPushButton#primaryBtn {
    background-color: #262626;
    color: #FFFFFF;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
}
QPushButton#primaryBtn:hover {
    background-color: #404040;
}
QPushButton#primaryBtn:pressed {
    background-color: #171717;
}
QPushButton#secondaryBtn {
    background-color: rgba(115, 115, 115, 0.08);
    color: #171717;
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: rgba(115, 115, 115, 0.16);
}

QPushButton#dangerBtn {
    background-color: transparent;
    color: #E8463A;
    border: 1px solid #E8463A;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#dangerBtn:hover {
    background-color: #E8463A;
    color: #FFFFFF;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #A1A1A1;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #D4D4D4;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #A1A1A1;
    padding: 40px 20px;
}

QTextEdit#errorDisplay {
    background-color: #FEF2F2;
    color: #171717;
    border: 1px solid rgba(232, 70, 58, 0.3);
    border-radius: 6px;
    padding: 12px;
    font-size: 12px;
    selection-background-color: rgba(75, 63, 227, 0.2);
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: 600;
    color: #4B3FE3;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #737373;
}
QLabel#detailValue {
    font-size: 13px;
    color: #171717;
}

QGroupBox {
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 8px;
    margin-top: 8px;
    padding-top: 16px;
    color: #404040;
    font-weight: 600;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

QCheckBox {
    color: #171717;
    spacing: 8px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(115, 115, 115, 0.36);
    border-radius: 4px;
    background: #FFFFFF;
}
QCheckBox::indicator:checked {
    background: #4B3FE3;
    border-color: #4B3FE3;
}

QSpinBox {
    background-color: #FFFFFF;
    border: 1px solid rgba(115, 115, 115, 0.12);
    border-radius: 6px;
    padding: 4px 8px;
    color: #171717;
}
QSpinBox:focus {
    border: 1px solid #000000;
}

QSlider::groove:horizontal {
    background: #E5E5E5;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #FFFFFF;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
    border: 1px solid rgba(115, 115, 115, 0.36);
}
QSlider::sub-page:horizontal {
    background: #4B3FE3;
    border-radius: 2px;
}

QRadioButton {
    color: #171717;
    spacing: 8px;
}
QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid rgba(115, 115, 115, 0.36);
    border-radius: 8px;
    background: #FFFFFF;
}
QRadioButton::indicator:checked {
    border-color: #4B3FE3;
    background: #FFFFFF;
}
QRadioButton::indicator:checked::after {
    width: 10px;
    height: 10px;
    border-radius: 5px;
    background: #4B3FE3;
}
"""


def get_theme(name: str) -> str:
    """Get QSS stylesheet by theme name."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
