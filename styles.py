"""QSS stylesheets for FeishuCalendarDesktop."""

DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #1e1e2e;
    color: #cdd6f4;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: bold;
    color: #89b4fa;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #a6adc8;
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
    color: #a6adc8;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: #313244;
    color: #cdd6f4;
}
QPushButton#iconBtn:pressed {
    background-color: #45475a;
}

/* === Month grid === */

/* Weekday header */
QLabel#weekDay {
    font-size: 11px;
    color: #a6adc8;
    font-weight: bold;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #f38ba8;
    font-weight: bold;
}

/* Day cells */
QFrame#dayCell {
    background-color: #313244;
    border: 1px solid #1e1e2e;
    border-radius: 4px;
}
QFrame#dayCellOther {
    background-color: #181825;
    border: 1px solid #1e1e2e;
    border-radius: 4px;
}
QFrame#dayCellToday {
    background-color: #313244;
    border: 2px solid #89b4fa;
    border-radius: 4px;
}

/* Day number */
QLabel#dayNum {
    font-size: 11px;
    color: #cdd6f4;
    font-weight: bold;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #45475a;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #89b4fa;
    font-weight: bold;
}

/* Grid event label */
QFrame#gridEvent {
    background-color: #45475a;
    border-radius: 3px;
    border-left: 2px solid #89b4fa;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: #585b70;
    border-left: 2px solid #b4befe;
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #a6adc8;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #cdd6f4;
}

/* More label */
QLabel#moreLabel {
    font-size: 9px;
    color: #6c7086;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #89b4fa;
}

/* === Event card (used in day detail dialog) === */

QFrame#eventCard {
    background-color: #313244;
    border-radius: 8px;
    border-left: 3px solid #89b4fa;
}
QFrame#eventCardPast {
    background-color: #2a2a3c;
    border-radius: 8px;
    border-left: 3px solid #585b70;
}
QFrame#eventCardCurrent {
    background-color: #2a3a2e;
    border-radius: 8px;
    border-left: 3px solid #a6e3a1;
}
QFrame#eventCard:hover {
    background-color: #3b3d52;
}

QLabel#eventTime {
    font-size: 11px;
    color: #a6adc8;
    font-weight: bold;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #585b70;
    font-weight: bold;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #a6e3a1;
    font-weight: bold;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #cdd6f4;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #585b70;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #6c7086;
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
    color: #6c7086;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #f38ba8;
    color: #1e1e2e;
}

/* Scroll area */
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
    background: #45475a;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #585b70;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* Input fields */
QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #313244;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 6px 8px;
    color: #cdd6f4;
    selection-background-color: #89b4fa;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #89b4fa;
}

/* Buttons */
QPushButton#primaryBtn {
    background-color: #89b4fa;
    color: #1e1e2e;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #b4befe;
}
QPushButton#primaryBtn:pressed {
    background-color: #74c7ec;
}
QPushButton#secondaryBtn {
    background-color: #313244;
    color: #cdd6f4;
    border: 1px solid #45475a;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: #45475a;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #6c7086;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #45475a;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #585b70;
    padding: 40px 20px;
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: bold;
    color: #89b4fa;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #a6adc8;
}
QLabel#detailValue {
    font-size: 13px;
    color: #cdd6f4;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #f5f5f5;
    color: #1e1e2e;
    font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
    font-size: 13px;
}

QLabel#headerTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1976d2;
    padding: 2px 0px;
}
QLabel#headerDate {
    font-size: 12px;
    color: #666;
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
    color: #666;
    font-size: 15px;
}
QPushButton#iconBtn:hover {
    background-color: #e0e0e0;
    color: #333;
}
QPushButton#iconBtn:pressed {
    background-color: #d0d0d0;
}

/* === Month grid === */

QLabel#weekDay {
    font-size: 11px;
    color: #666;
    font-weight: bold;
}
QLabel#weekDayWeekend {
    font-size: 11px;
    color: #e53935;
    font-weight: bold;
}

QFrame#dayCell {
    background-color: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}
QFrame#dayCellOther {
    background-color: #f5f5f5;
    border: 1px solid #e0e0e0;
    border-radius: 4px;
}
QFrame#dayCellToday {
    background-color: #fff;
    border: 2px solid #1976d2;
    border-radius: 4px;
}

QLabel#dayNum {
    font-size: 11px;
    color: #333;
    font-weight: bold;
}
QLabel#dayNumOther {
    font-size: 11px;
    color: #bbb;
}
QLabel#dayNumToday {
    font-size: 12px;
    color: #1976d2;
    font-weight: bold;
}

QFrame#gridEvent {
    background-color: #e3f2fd;
    border-radius: 3px;
    border-left: 2px solid #1976d2;
    max-height: 18px;
    min-height: 16px;
}
QFrame#gridEvent:hover {
    background-color: #bbdefb;
    border-left: 2px solid #42a5f5;
}
QLabel#gridEventTime {
    font-size: 9px;
    color: #666;
}
QLabel#gridEventTitle {
    font-size: 10px;
    color: #333;
}

QLabel#moreLabel {
    font-size: 9px;
    color: #999;
    padding: 0px 2px;
}
QLabel#moreLabel:hover {
    color: #1976d2;
}

/* === Event card (used in day detail dialog) === */

QFrame#eventCard {
    background-color: #ffffff;
    border-radius: 8px;
    border-left: 3px solid #1976d2;
}
QFrame#eventCardPast {
    background-color: #f0f0f0;
    border-radius: 8px;
    border-left: 3px solid #bbb;
}
QFrame#eventCardCurrent {
    background-color: #e8f5e9;
    border-radius: 8px;
    border-left: 3px solid #4caf50;
}
QFrame#eventCard:hover {
    background-color: #f0f4ff;
}

QLabel#eventTime {
    font-size: 11px;
    color: #666;
    font-weight: bold;
}
QLabel#eventTimePast {
    font-size: 11px;
    color: #bbb;
    font-weight: bold;
}
QLabel#eventTimeCurrent {
    font-size: 11px;
    color: #4caf50;
    font-weight: bold;
}
QLabel#eventTitle {
    font-size: 13px;
    color: #1e1e2e;
    font-weight: 500;
}
QLabel#eventTitlePast {
    font-size: 13px;
    color: #bbb;
    font-weight: 500;
}
QLabel#eventMeta {
    font-size: 11px;
    color: #999;
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
    color: #999;
    font-size: 12px;
}
QPushButton#deleteBtn:hover {
    background-color: #ef5350;
    color: #fff;
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
    background: #ccc;
    border-radius: 3px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #aaa;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QDateTimeEdit {
    background-color: #fff;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 6px 8px;
    color: #1e1e2e;
    selection-background-color: #1976d2;
}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus, QDateTimeEdit:focus {
    border: 1px solid #1976d2;
}

QPushButton#primaryBtn {
    background-color: #1976d2;
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #2196f3;
}
QPushButton#primaryBtn:pressed {
    background-color: #1565c0;
}
QPushButton#secondaryBtn {
    background-color: #e0e0e0;
    color: #333;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 8px 16px;
}
QPushButton#secondaryBtn:hover {
    background-color: #d0d0d0;
}

QLabel#statusLabel {
    font-size: 11px;
    color: #999;
    padding: 4px 0px;
}

QLabel#resizeGrip {
    font-size: 10px;
    color: #ccc;
}

QLabel#emptyLabel {
    font-size: 13px;
    color: #bbb;
    padding: 40px 20px;
}

QLabel#detailTitle {
    font-size: 16px;
    font-weight: bold;
    color: #1976d2;
}
QLabel#detailLabel {
    font-size: 12px;
    color: #666;
}
QLabel#detailValue {
    font-size: 13px;
    color: #1e1e2e;
}
"""


def get_theme(name: str) -> str:
    """Get QSS stylesheet by theme name."""
    if name == "light":
        return LIGHT_THEME
    return DARK_THEME
