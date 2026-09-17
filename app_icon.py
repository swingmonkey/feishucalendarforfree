"""Shared application icon loading.

Keeping the icon source in one module makes the tray icon, window/title-bar
icon and in-app logo stay in sync across source runs and PyInstaller bundles.
"""

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication

_ICON_SOURCE_CANDIDATES = (
    Path("icon.iconset") / "icon_128x128.png",
    Path("tray.png"),
    Path("icon_1024.png"),
)
_ICON_SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
_ALPHA_THRESHOLD = 64
_CONTENT_SCALE = 0.92
_trimmed_source: QPixmap | None = None


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
    """Build the tray/app icon from the same trimmed artwork as the window."""
    source = _load_trimmed_source()
    if source is not None:
        icon = QIcon()
        for size in _ICON_SIZES:
            icon.addPixmap(_fit_pixmap(source, size))
        return icon
    return QIcon(_fallback_pixmap(64))


def _load_trimmed_source() -> QPixmap | None:
    """Load the highest-quality app artwork and remove transparent padding."""
    global _trimmed_source
    if _trimmed_source is not None:
        return _trimmed_source

    assets_dir = resolve_assets_dir()
    source = None
    for relative_path in _ICON_SOURCE_CANDIDATES:
        path = assets_dir / relative_path
        if not path.is_file():
            continue
        candidate = QPixmap(str(path))
        if not candidate.isNull():
            source = candidate
            break
    if source is None:
        return None

    image = source.toImage()
    left, top = image.width(), image.height()
    right = bottom = -1
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y).alpha() > _ALPHA_THRESHOLD:
                left = min(left, x)
                top = min(top, y)
                right = max(right, x)
                bottom = max(bottom, y)
    if right >= left and bottom >= top:
        source = source.copy(left, top, right - left + 1, bottom - top + 1)

    _trimmed_source = source
    return source


def _fit_pixmap(source: QPixmap, size: int) -> QPixmap:
    """Fit app artwork into a transparent square with a small safe margin."""
    size = max(1, size)
    inner = max(1, int(round(size * _CONTENT_SCALE)))
    scaled = source.scaled(
        inner,
        inner,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    canvas = QPixmap(size, size)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawPixmap(
        (size - scaled.width()) // 2,
        (size - scaled.height()) // 2,
        scaled,
    )
    painter.end()
    return canvas


def create_app_logo_pixmap(size: int = 32) -> QPixmap:
    """Return the same trimmed app artwork used by the window and tray icons.

    The source PNGs contain faint low-alpha pixels around the artwork. Using a
    low threshold makes the crop span almost the whole image, leaving the logo
    visibly small. A meaningful alpha threshold removes that padding so the
    in-window logo, taskbar icon and tray icon all present the same artwork at
    the same visual size.
    """
    source = _load_trimmed_source()
    if source is None:
        source = _fallback_pixmap(max(64, size * 4))

    app = QApplication.instance()
    dpr = float(app.devicePixelRatio()) if app is not None else 1.0
    pixel_size = max(1, int(round(size * dpr)))
    canvas = _fit_pixmap(source, pixel_size)
    canvas.setDevicePixelRatio(dpr)
    return canvas
