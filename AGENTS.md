# AGENTS.md — 飞书日程桌面助手

## 定位
Windows/macOS 桌面月历日程应用（PySide6 GUI），展示飞书日历日程，支持添加/删除/搜索/导出，认证统一走 lark-cli 用户授权（应用内扫码登录）。

## 怎么跑
```bash
python -m pip install -r requirements.txt   # PySide6 + openpyxl
python main.py                              # 或双击 启动飞书日程.bat
python -m pytest                            # 10 个测试：utils 日期范围/排序逻辑
```
首次运行自动弹登录窗口（lark-cli device flow：二维码/网页授权，scope 见 login_dialog.py LOGIN_SCOPES）。

## 技术栈
Python 3.10+ / PySide6 (Qt6) / openpyxl；lark-cli（npm 全局，跨项目共享授权凭据）。

## 目录与约定
- `main.py` 入口+托盘；`calendar_widget.py` 月历网格；`login_dialog.py` 应用内登录
- `lark_cli_async.py` 异步封装（QProcess）；**Windows 必须 node 直调 run.js**（cmd/PowerShell 会拆解 `--data` JSON 的双引号和 URL 的 `&`，报 invalid JSON）
- **scope 是单个空格分隔参数**：`--scope "calendar:calendar.event:read calendar:calendar:read"`；重复写 `--scope A --scope B` 只保留最后一个会漏 event:read（login_dialog.py:LOGIN_SCOPES，勿改回循环传 --scope）
- 月历 7 列等宽约定：GridEventLabel/DayCell 水平 sizePolicy=Ignored，表头用 QGridLayout，勿让内容撑宽列
- `config.json` 存窗口/主题/刷新间隔（`.gitignore` 排除，不含任何凭据）

## 当前状态
- 认证仅 lark-cli 用户授权（App ID/Secret 模式已移除，feishu_api.py 已删除）
- 已修复：日期星期错位、编辑日程 invalid JSON、node 直调参数、新版 lark-cli scope 授权（单字符串）
- 已添加（2026-08-08）：`tests/test_utils.py`（10 用例）+ pytest.ini（`pythonpath=.`）；CI 已移除（不需要）
