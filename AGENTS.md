# AGENTS.md — 飞书日程桌面助手

## 定位
Windows/macOS 桌面月历日程应用（PySide6 GUI），展示飞书日历日程，支持添加/删除/搜索/导出，认证统一走 lark-cli 用户授权（应用内扫码登录）。

## 怎么跑
```bash
python -m pip install -r requirements.txt   # PySide6 + openpyxl
python main.py                              # 或双击 启动飞书日程.bat
```
首次运行自动弹登录窗口（lark-cli device flow：二维码/网页授权，scope 见 login_dialog.py LOGIN_SCOPES）。

## 技术栈
Python 3.10+ / PySide6 (Qt6) / openpyxl；lark-cli（npm 全局，跨项目共享授权凭据）。

## 目录与约定
- `main.py` 入口+托盘；`main_window.py` 主窗口（月/周视图切换、刷新/错误重试/拖拽改期/持久化）
- `month_view.py` 月历网格组件；`week_view.py` 周计划组件（weektodo 风格 7 列）
- `widgets.py` 共享小组件（日期徽标 / 可点击标签 / 紧凑日程标签=拖拽源 / 日格=放置目标）；`models_event.py` 事件模型（时间解析、重复展开 RFC5545、Markdown→HTML、颜色/子任务工具）
- `event_card.py` 日程卡片（颜色条 / ♻ 徽标 / 拖拽源）；`day_detail_dialog.py` + `search_dialog.py` 由旧 calendar_widget.py 拆分而出
- `lark_cli_async.py` 异步封装（QProcess）；**Windows 必须 node 直调 run.js**（cmd/PowerShell 会拆解 `--data` JSON 的双引号和 URL 的 `&`，报 invalid JSON）
- 月历 7 列等宽约定：GridEventLabel/DayCell 水平 sizePolicy=Ignored，表头用 QGridLayout，勿让内容撑宽列
- 飞书读写能力集中在 `lark_cli.py`/`lark_cli_async.py`，**重构只动 UI 层**：拖拽改期复用 `update_event`，重复写入复用 `+create --rrule`/`patch recurrence`，颜色仅存本地 `config.json.event_colors`，子任务即描述里的 Markdown 勾选清单 `- [ ]`
- `config.json` 存窗口/主题/刷新间隔/视图模式/颜色（`.gitignore` 排除，不含任何凭据）

## 当前状态
- 认证仅 lark-cli 用户授权（App ID/Secret 模式已移除，feishu_api.py 已删除）
- 已重构：拆分 calendar_widget.py 为 main_window + month_view + week_view + widgets + dialogs；新增月/周双视图、拖拽改期、颜色分类、重复日程、Markdown 子任务
- 已移植协作者 UI 增强到新架构（`main_window.py`）：最小化按钮（`min_btn`→`showMinimized`）、桌面快捷方式自动创建（`main.py:_ensure_desktop_shortcut`，config 键 `desktop_shortcut_created`）、已授权后隐藏「一键登录」按钮（`_update_login_btn_visibility`，逻辑在 `login_dialog.has_lark_auth`）
- 离线回归测试：`tests/test_refactor_features.py`（11 例，覆盖月/周切换、重复展开、子任务往返、拖拽改期接线、登录按钮显隐、桌面快捷方式逻辑），需 `QT_QPA_PLATFORM=offscreen` + PySide6
- 最近提交已推送 GitHub（origin/main）
