"""Shared application icon loading.

Keeping the icon source in one module makes the tray icon, window/title-bar
icon and in-app logo stay in sync across source runs and PyInstaller bundles.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication


def resolve_assets_dir() -> Path:
    """Resolve the directory containing bundled assets.

    Works for both source runs (project root/assets/) and PyInstaller bundles.
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "darwin":
            base = Path(sys.executable).resolve().parent.parent / "Resources"
        else:
            base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        candidate = base / "assets"
        if candidate.is_dir():
            return candidate
        return base
    return Path(__file__).resolve().parent / "assets"


def _fallback_pixmap(size: int = 64) -> QPixmap:
    """Programmatically drawn fallback used only if asset files are missing."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor("#3370FF"))
    painter.setPen(Qt.PenStyle.NoPen)
    radius = max(3, size // 8)
    painter.drawRoundedRect(2, 2, size - 4, size - 4, radius, radius)
    painter.setPen(QColor("#FFFFFF"))
    font = QFont()
    font.setFamilies(["PingFang SC", "SF Pro Text", "Microsoft YaHei UI", "Segoe UI"])
    font.setPixelSize(max(12, int(size * 0.44)))
    font.setWeight(QFont.Weight.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "日")
    painter.end()
    return pixmap


def create_app_icon() -> QIcon:
    """Load the tray/app icon from assets, with a drawn fallback."""
    assets_dir = resolve_assets_dir()
    # tray.png is transparent-background and reads well in the system tray.
    for candidate in ("tray.png", "icon_1024.png"):
        path = assets_dir / candidate
        if path.is_file():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return QIcon(_fallback_pixmap(64))


def create_app_logo_pixmap(size: int = 32) -> QPixmap:
    """Return the app artwork scaled to fill an in-window logo label.

    The source PNG has transparent padding around the artwork. Scaling it
    directly makes the visible logo look much smaller than its label, so trim
    the transparent bounds before fitting it into a square canvas.
    """
    app = QApplication.instance()
    dpr = float(app.devicePixelRatio()) if app is not None else 1.0
    pixel_size = max(1, int(round(size * dpr)))
    source_size = max(128, pixel_size * 4)
    source = create_app_icon().pixmap(source_size, source_size)
    image = source.toImage()

    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > 8:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)

    canvas = QPixmap(pixel_size, pixel_size)
    canvas.fill(Qt.GlobalColor.transparent)
    if right >= left and bottom >= top:
        trimmed = source.copy(left, top, right - left + 1, bottom - top + 1)
        scaled = trimmed.scaled(
            pixel_size,
            pixel_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(
            (pixel_size - scaled.width()) // 2,
            (pixel_size - scaled.height()) // 2,
            scaled,
        )
        painter.end()

    canvas.setDevicePixelRatio(dpr)
    return canvas
