#!/usr/bin/env bash
# macOS 启动脚本（双击运行）
# 切换到脚本所在目录
cd "$(dirname "$0")" || exit 1

# 优先使用 python3，回退到 python
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "未找到 python，请先安装 Python 3.10+"
    echo "  brew install python3"
    read -n 1 -s -r -p "按任意键退出..."
    exit 1
fi

# 检查依赖
if ! "$PY" -c "import PySide6" >/dev/null 2>&1; then
    echo "未检测到 PySide6，正在安装依赖..."
    "$PY" -m pip install -r requirements.txt
fi

"$PY" main.py
