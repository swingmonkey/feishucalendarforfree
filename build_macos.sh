#!/usr/bin/env bash
# macOS PyInstaller 鎵撳寘鑴氭湰 鈥?鐢熸垚 FeishuCalendar.app
# 浣跨敤鏂规硶锛歜ash build_macos.sh
set -e

cd "$(dirname "$0")"

# 浜х墿鍚嶏細榛樿涓枃鍚嶏紱CI 鍙 FC_APP_NAME 瑕嗙洊涓?ASCII 鍚?APP_NAME="${FC_APP_NAME:-椋炰功鏃ョ▼}"
BUNDLE_ID="com.swingmonkey.feishucalendar"
ENTRY="main.py"

# 娓呯悊涓婃鏋勫缓浜х墿
rm -rf build dist "${APP_NAME}.spec"

# 浣跨敤涓庨」鐩浉鍚岀殑 Python 鐜
PY="${PYTHON:-python3}"
if ! "$PY" -c "import PySide6" >/dev/null 2>&1; then
    echo "鏈娴嬪埌 PySide6锛屾鍦ㄥ畨瑁呬緷璧?.."
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
    --hidden-import ui_common \
    --hidden-import lark_cli \
    --hidden-import lark_cli_async \
    --hidden-import models_event \
    --hidden-import widgets \
    --hidden-import month_view \
    --hidden-import week_view \
    --hidden-import main_window \
    --hidden-import event_card \
    --hidden-import add_event_dialog \
    --hidden-import event_detail_dialog \
    --hidden-import day_detail_dialog \
    --hidden-import search_dialog \
    --hidden-import settings_dialog \
    --hidden-import export_dialog \
    --hidden-import updater \
    --hidden-import update_dialog \
    --hidden-import __version__ \
    "$ENTRY"

# 鎷疯礉 icon.icns 鍒?.app/Contents/Resources/ 浣滀负 Finder/Dock 鍥炬爣锛圥yInstaller 宸茬粡鍋氫簡锛屽弻淇濋櫓锛?cp -f assets/icon.icns "dist/${APP_NAME}.app/Contents/Resources/icon-windowed.icns" 2>/dev/null || true

echo ""
echo "鏋勫缓瀹屾垚锛歞ist/${APP_NAME}.app"

# 鎵撴垚 zip 渚涗笂浼?Release锛堝湪鑴氭湰鍐呭仛锛岄伩鍏?CI 鍐呰仈鍛戒护鐨勪腑鏂囩紪鐮侀棶棰橈級
ditto -c -k --sequesterRsrc --keepParent "dist/${APP_NAME}.app" "dist/${APP_NAME}.app.zip"

ls -la "dist/"

