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
- `month_view.py` 月历网格组件；`week_view.py` 周计划组件（weektodo 风格 7 列，顶部有独立「全天」条，跨天延续日显示 `↳`）
- `context_menu.py` 右键菜单构造（事件 / 日格 / 窗口空白三处共用，措辞与危险项位置保持一致）；各视图只负责把 `event_context_menu` / `day_background_menu` 信号转发给主窗口
- `widgets.py` 共享小组件（日期徽标 / 可点击标签 / 紧凑日程标签=拖拽源 / 日格=放置目标）；`models_event.py` 事件模型（时间解析、重复展开 RFC5545、Markdown→HTML、颜色/子任务工具、`RECURRENCE_CHOICES` 重复规则真源）
- `event_card.py` 日程卡片（颜色条 / ♻ 徽标 / 拖拽源 / ↳ 延续）；`day_detail_dialog.py` + `search_dialog.py` 由旧 calendar_widget.py 拆分而出
- `lark_cli_async.py` 异步封装（QProcess）；**Windows 必须 node 直调 run.js**（cmd/PowerShell 会拆解 `--data` JSON 的双引号和 URL 的 `&`，报 invalid JSON）
- 月历 7 列等宽约定：GridEventLabel/DayCell 水平 sizePolicy=Ignored，表头用 QGridLayout，勿让内容撑宽列
- **日格样式名是拼接出来的**：`DayCell._refresh_object_name()` 按「基础名(dayCell/dayCellOther/dayCellToday) + Drop > Cursor > Hover」合成，改样式时这 6 个新后缀（`…Drop` / `…Cursor`）两套主题都要补
- **日格可容纳条数按实际高度算**：`widgets.visible_event_count(grid_font, cell_height, reserve_more)`，窗口压矮或 6 行月份时自动收缩，但必须给「+N更多」留一行（`_MORE_ROW_HEIGHT`）——它是隐藏日程唯一的入口，被挤出去就再也点不开了；`DayCell.resizeEvent` 会重算
- **快捷键一律包一层 modal 守卫**（`main_window._setup_shortcuts`）：对话框是主窗口的子窗口，Qt 的 WindowShortcut 在对话框内照样触发，否则在标题框敲 `n` 会再弹一个新建框
- **删除确认放在发出删除的那个窗口里**（`EventDetailDialog` / `DayDetailDialog` 各自弹 ConfirmDialog）；主窗口连的是 `_delete_event` 而不是 `_confirm_delete`，避免弹两次
- 飞书读写能力集中在 `lark_cli.py`/`lark_cli_async.py`，**重构只动 UI 层**：拖拽改期复用 `update_event`，重复写入复用 `+create --rrule`/`patch recurrence`，颜色仅存本地 `config.json.event_colors`，子任务即描述里的 Markdown 勾选清单 `- [ ]`
- **lark-cli `calendar +create` 没有 `--location`**（只有原生 `calendar events create --data` 才带 location 字段），所以新建对话框的「地点」按 `add_event_dialog.compose_description()` 以 `📍 地点：` 追加进描述，**不要再给 `create_event` 传 `location=`**（会 TypeError 并让表单永久卡在「创建中…」）
- **全天日程（`start_time.date`）不要用 timestamp 写回**：勾选子任务时只改描述、不传 start/end，否则整天事件会被改成带具体时刻的定时事件
- `config.json` 存窗口/主题（默认 light、opacity 1.0）/刷新间隔/视图模式/颜色/`grid_font_size`/`list_font_size`/`usage_stats_enabled`/`auth_completed`/`auth_user`（`.gitignore` 排除，不含任何凭据）
- UI 统一飞书设计语言：品牌蓝 #3370FF（hover #4E83FD、pressed #245BDB），成功 #34C724、警告 #FF8800、危险 #F54A45，中性色 N 系列；QSS 集中在 `styles.py`（`get_theme(name, grid_font, list_font)`），新控件先加 objectName 再在两套主题补样式，勿在代码里散落硬编码色值
- **日程字号可调（v2.1.6）**：`config.grid_font_size`（月视图，默认 10）/ `config.list_font_size`（周·列表视图，默认 13），范围 9-24px，设置页「外观」Tab 两个滑块；实现方式是 `styles._event_font_rules()` 生成覆盖规则**追加在主题 QSS 末尾**（同名选择器后定义者生效），不改两套大模板；时间与次要信息由主字号派生（月视图 -1、列表 -2）。改字号必须同步放开 `QFrame#gridEvent` 的 min/max-height（行高 = 字号 +6/+8），否则大字号会被裁；字号变化后 `MainWindow._on_settings_changed` 会 `_render_active_view()` 重建视图

## 当前状态
- 认证仅 lark-cli 用户授权（App ID/Secret 模式已移除，feishu_api.py 已删除）
- 已重构：拆分 calendar_widget.py 为 main_window + month_view + week_view + widgets + dialogs；新增月/周双视图、拖拽改期、颜色分类、重复日程、Markdown 子任务
- v2.1 体验改造：启动零模态弹窗与登录态持久化（状态机面板替代登录框）；Toast/ConfirmDialog/内联红字替代全部 QMessageBox；头部按钮收敛为 月|周、＋、⟳、⋯、—、✕（搜索/导出/置顶/主题/登录/设置收入 ⋯ 菜单）；styles.py 按飞书设计令牌整体重写（默认浅色）；设置页改 4 Tab + 异步状态检测
- 离线回归测试：`tests/test_refactor_features.py`（覆盖头部收敛、启动加载面板、登录状态机四种模式、auth 错误分类、Toast/ConfirmDialog、mark_authed、设置页异步状态）、`tests/test_ux_improvements.py`（v2.2 体验改造），另有 test_config / test_updater 等；需 `QT_QPA_PLATFORM=offscreen` + PySide6（注意：offscreen 插件无字体库，截图验证 UI 需用 `QT_QPA_PLATFORM=windows` 且不 show 直接 grab）
- v2.1.5 已提交并推送 origin/main（`1e513ba`），与 GitHub 最新 Release v2.1.5 一致
- v2.1.6：日程字号可调（月视图 10px / 周·列表 13px，9-24px 两档滑块），测试 `tests/test_font_size.py`（12 项）
- **v2.2 体验改造（已发布 v2.2.0）**，测试 `tests/test_ux_improvements.py`（38 例）：
  - 修 P0：「创建日程」点下去就永久卡在「创建中…」（`location=` 传给了不接受的 `create_event`，TypeError 无兜底）；地点改为写入描述
  - 修 P1：后台自动刷新遇到授权类关键词会把已加载的日历换成登录面板且**无出口**；现在一律只发 Toast，登录面板在还有日程时提供「继续查看已加载日程」
  - 修 P1：月历拖拽没有落点高亮（补 `…Drop` 样式）；重复日程拖拽会**吞掉点击**（`_dragging` 提前置位），现在不吞点击并给 Toast
  - 修 P1：日格条数改按实际高度算，矮窗口/6 行月份下「+N更多」不再被挤出格子（此前隐藏日程彻底无法访问）
  - 新增：全套键盘快捷键 + ↑↓ 键盘游标（跨月自动翻页）、右键菜单（事件/日格/窗口）、复制日程
  - 新增：周视图全天日程独立成条、跨天延续日显示 `↳`、日程卡悬停提示
  - 修：详情页子任务显示两遍（`markdown_to_html(strip_tasks=True)`）；重复规则一处中文一处 RFC5545 原文（真源移到 `models_event.RECURRENCE_CHOICES`）；全天日程勾选子任务会被改成定时事件
  - 修：删除确认框在本窗口弹出（此前先关窗口再弹确认，取消也一起丢）；设置页「重新检测」按钮文案与行为不符；开机启动写注册表失败不回滚；透明度滑块下限与 config clamp 不一致
  - 新增：匿名统计 opt-out（`config.usage_stats_enabled`，设置 → 通用），关闭时清除 `install_id`；关于页不再宣称「不经过任何第三方服务器」
- 当前测试总量 **237 例**（199 + 38），`ruff check` 全绿
- v2.2.0 发布约定：推 `v*` 标签触发 `.github/workflows/release.yml`（CI 跑测试 → 打包 Windows EXE + macOS zip → 挂到 Release → 生成并挂 `SHA256SUMS`）。客户端 Windows 静默更新依赖 Release 里的 `.exe` 资产 + `SHA256SUMS`，两者缺一则退回「发现新版本」Toast 引导手动下载；**勿删这两个资产**。CI 用 `FC_APP_NAME=FeishuCalendar` 产出 ASCII 名 `FeishuCalendar.exe`，客户端 `find_exe_asset()` 会回退到 `exes[0]` 命中它
- 新增模块后记得同步 `build_windows.ps1` 与 `build_macos.sh` 的 `--hidden-import` 清单（仓库里的 `*.spec` 被 gitignore，是本地构建产物，不用管）

## Git 仓库：状态判定铁律（接手必读）
- **版本真源**是 `__version__.py` 的 `APP_VERSION`（当前 `2.2.0`），关于页与 OTA 更新器共用；发版只改这一处 + bump Release tag
- ⚠️ 本机 `refs/remotes/origin/main` 显示**不可靠**（曾长期停在旧 commit `2a4f326`，`git status` 也看不出 ahead/behind）。**判断远程真实状态一律以 GitHub 网页 / API 为准**，不要相信本地 remote-tracking ref
- ⚠️ **禁止在 `C:\Users\77427\feishucalendarforfree` 执行 `git pull` / `git reset --hard origin/main`**：远程曾有被 force push 成残缺版本的先例，pull 会删掉本地 30+ 源文件
- 需要覆盖远程时用 `git push --force-with-lease=main:<期望的远程sha> origin main`，**先在本地给旧提交建备份分支**（如 `backup/orphan-4df042e`，仅本地不推送）
- 环境：本机 git 直连需 `git -c http.sslVerify=false`（schannel 证书吊销检查失败）；WorkBuddy Bash 的 PATH 被裁，命令前置 `PATH="/usr/bin:/bin:$PATH";`

### 事故记录：2026-09-19 远程被孤儿提交覆盖
- 现象：远程 main 被 force push 为 `4df042e`（2026-09-19 23:24，commit message 带 `Closes: #1, #2, #3`，疑似 AI agent 产出）。该提交**无父提交**，整仓只剩 `main.py` + submodule `temp_feishu_repo`
- 危害：那个 main.py import 了 `updater`/`config`/`main_window`/`app_icon`/`usage_stats`/`ui_common` 等本地并不存在的模块，代码残缺、无法运行；当时本地领先远程 53 个 commit
- 处理：备份分支 `backup/orphan-4df042e` → `git push --force-with-lease=main:4df042e... origin main` → 远程恢复为 `1e513ba`，根目录 40+ 文件全部回来，Releases（v2.0.0~v2.1.5）未受影响
- 教训：任何"仓库文件数骤减 / 提交无父 / 凭空出现 submodule"的情况，先停手核对，不要同步

## OTA 自动更新（updater.py）
- 查询 `https://api.github.com/repos/swingmonkey/feishucalendarforfree/releases/latest`，下载 `zipball_url` 后剥去 `repo-tag/` 顶层目录覆盖本地，**排除 `config.json` / `.git`**，最后重启进程；仅用标准库（urllib/zipfile/subprocess）
- 触发：启动 4 秒后静默检查（`config.json` 的 `check_update_on_start` 可关）；手动入口在设置 → 检查更新
- Windows 打包版：后台静默下载暂存到 pending 路径，下次启动或用户确认后 `apply_pending_update()` + `restart_application()`；非 Windows/源码运行保留可点击轻提示
- 发新版只需打新的 GitHub Release，客户端会自动检测到；**前提是别再让 force push 把仓库清掉**
