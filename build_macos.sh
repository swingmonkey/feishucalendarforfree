#!/usr/bin/env bash
# macOS PyInstaller 打包脚本 — 生成 FeishuCalendar.app
# 使用方法：bash build_macos.sh
set -e

cd "$(dirname "$0")"

APP_NAME="飞书日程"
BUNDLE_ID="com.swingmonkey.feishucalendar"
ENTRY="main.py"

# 清理上次构建产物
rm -rf build dist "${APP_NAME}.spec"

# 使用与项目相同的 Python 环境
PY="${PYTHON:-python3}"
if ! "$PY" -c "import PySide6" >/dev/null 2>&1; then
    echo "未检测到 PySide6，正在安装依赖..."
    "$PY" -m pip install -r requirements.txt pyinstaller
fi

"$PY" -m PyInstaller \
    --noconfirm \
    --onedir \
    --windowed \
    --name "$APP_NAME" \
    --osx-bundle-identifier "$BUNDLE_ID" \
    --icon "assets/icon.icns" \
    --add-data "assets:assets" \
    --paths "." \
    --hidden-import openpyxl \
    --hidden-import config \
    --hidden-import styles \
    --hidden-import lark_cli \
    --hidden-import lark_cli_async \
    --hidden-import feishu_api \
    --hidden-import calendar_widget \
    --hidden-import event_card \
    --hidden-import add_event_dialog \
    --hidden-import event_detail_dialog \
    --hidden-import settings_dialog \
    --hidden-import export_dialog \
    "$ENTRY"

# 拷贝 icon.icns 到 .app/Contents/Resources/ 作为 Finder/Dock 图标（PyInstaller 已经做了，双保险）
cp -f assets/icon.icns "dist/${APP_NAME}.app/Contents/Resources/icon-windowed.icns" 2>/dev/null || true

echo ""
echo "构建完成：dist/${APP_NAME}.app"
ls -la "dist/"
