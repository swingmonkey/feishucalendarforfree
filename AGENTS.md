# AGENTS.md — 飞书日程桌面助手

## 定位
Windows/macOS 桌面月历日程应用（PySide6 GUI），展示飞书日历日程，支持添加/删除/搜索/导出，认证统一走 lark-cli 用户授权（应用内扫码登录）。

## 怎么跑
```bash
python -m pip install -r requirements.txt   # PySide6 + openpyxl
python main.py                              # 或双击 启动飞书日程.bat
```
首次运行不弹任何模态框：显示内联加载面板，未登录/授权过期时切换到登录引导面板（lark-cli device flow：二维码/网页授权，scope 见 login_dialog.py LOGIN_SCOPES）。授权成功一次后凭据由 lark-cli 全局持久化，重启免登录。

## 技术栈
Python 3.10+ / PySide6 (Qt6) / openpyxl；lark-cli（npm 全局，跨项目共享授权凭据）。

## 目录与约定
- `main.py` 入口+托盘（托盘菜单精简）；`main_window.py` 主窗口：QStackedWidget 状态机（索引 0 月视图 / 1 周视图 / 2 加载 / 3 登录引导 / 4 错误）、头部溢出菜单（more_btn+QMenu）、Toast、拖拽改期/持久化
- `ui_common.py` 通用 UI：`Toast`（主窗口底部胶囊轻提示，info/success/warning/error + 可选动作按钮）与 `ConfirmDialog`（飞书风格确认框，danger=True 红色按钮，静态 `ask()`）；新增弹窗优先用这两者，不要重新引入 QMessageBox
- `login_dialog.py` device flow：`_DeviceCodeWorker` 线程自动轮询、成功自动关窗；线程不设 parent 并登记到模块级 `_LIVE_WORKERS`，finished 后自行注销（对话框可能先关闭，禁止销毁运行中的 QThread）；`AuthStatusWorker` 供设置页异步检测；`mark_authed(config)` 写 `auth_completed/auth_user`
- 启动认证判定：成功拉取日程即 mark_authed；错误文本命中授权类关键词（scope/auth/unauthorized/token/credential/login/授权/登录/登陆/认证/身份）走 auth 面板（未登录过 welcome、登录过 expired），未装 lark-cli 走 no_cli 安装引导，其余错误走 error 面板；已成功加载后的后台刷新失败只发 Toast，不抢占视图
- `month_view.py` 月历网格组件；`week_view.py` 周计划组件（weektodo 风格 7 列）
- `widgets.py` 共享小组件（日期徽标 / 可点击标签 / 紧凑日程标签=拖拽源 / 日格=放置目标）；`models_event.py` 事件模型（时间解析、重复展开 RFC5545、Markdown→HTML、颜色/子任务工具）
- `event_card.py` 日程卡片（颜色条 / ♻ 徽标 / 拖拽源）；`day_detail_dialog.py` + `search_dialog.py` 由旧 calendar_widget.py 拆分而出
- `lark_cli_async.py` 异步封装（QProcess）；**Windows 必须 node 直调 run.js**（cmd/PowerShell 会拆解 `--data` JSON 的双引号和 URL 的 `&`，报 invalid JSON）
- 月历 7 列等宽约定：GridEventLabel/DayCell 水平 sizePolicy=Ignored，表头用 QGridLayout，勿让内容撑宽列
- 飞书读写能力集中在 `lark_cli.py`/`lark_cli_async.py`，**重构只动 UI 层**：拖拽改期复用 `update_event`，重复写入复用 `+create --rrule`/`patch recurrence`，颜色仅存本地 `config.json.event_colors`，子任务即描述里的 Markdown 勾选清单 `- [ ]`
- `config.json` 存窗口/主题（默认 light、opacity 1.0）/刷新间隔/视图模式/颜色/`auth_completed`/`auth_user`（`.gitignore` 排除，不含任何凭据）
- UI 统一飞书设计语言：品牌蓝 #3370FF（hover #4E83FD、pressed #245BDB），成功 #34C724、警告 #FF8800、危险 #F54A45，中性色 N 系列；QSS 集中在 `styles.py`（get_theme(name)），新控件先加 objectName 再在两套主题补样式，勿在代码里散落硬编码色值

## 当前状态
- 认证仅 lark-cli 用户授权（App ID/Secret 模式已移除，feishu_api.py 已删除）
- 已重构：拆分 calendar_widget.py 为 main_window + month_view + week_view + widgets + dialogs；新增月/周双视图、拖拽改期、颜色分类、重复日程、Markdown 子任务
- v2.1 体验改造：启动零模态弹窗与登录态持久化（状态机面板替代登录框）；Toast/ConfirmDialog/内联红字替代全部 QMessageBox；头部按钮收敛为 月|周、＋、⟳、⋯、—、✕（搜索/导出/置顶/主题/登录/设置收入 ⋯ 菜单）；styles.py 按飞书设计令牌整体重写（默认浅色）；设置页改 4 Tab + 异步状态检测
- 离线回归测试：`tests/test_refactor_features.py`（19 例，覆盖头部收敛、启动加载面板、登录状态机四种模式、auth 错误分类、Toast/ConfirmDialog、mark_authed、设置页异步状态），另有 test_config / test_updater 等；需 `QT_QPA_PLATFORM=offscreen` + PySide6（注意：offscreen 插件无字体库，截图验证 UI 需用 `QT_QPA_PLATFORM=windows` 且不 show 直接 grab）
- 最近提交已推送 GitHub（origin/main）；v2.1 改造目前仅在本地工作区，尚未提交/推送/提 PR
