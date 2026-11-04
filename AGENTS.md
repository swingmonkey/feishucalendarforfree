# AGENTS.md — 飞书日程桌面助手

## 定位
Windows/macOS 桌面月历日程应用（PySide6 GUI），展示飞书日历日程，支持添加/删除/搜索/导出，认证统一走 lark-cli 用户授权（应用内扫码登录）。

## 怎么跑
```bash
python -m pip install -r requirements.txt   # PySide6 + openpyxl
python main.py                              # 或双击 启动飞书日程.bat
```
首次运行不弹任何模态框：显示内联加载面板，未登录/授权过期时切换到登录引导面板（lark-cli device flow：二维码/网页授权，scope 见 login_dialog.py LOGIN_SCOPES）。授权成功一次后凭据由 lark-cli 全局持久化，重启免登录。

## 本地 CI（推送前门禁）

```bash
python3 tools/ci.py                  # ruff → compileall → pytest + 覆盖率门禁 ≥70%
python3 tools/ci.py --fast           # 跳过覆盖率统计
python3 tools/ci.py --build          # 额外打一次本机安装包
python3 tools/ci.py --install-hook   # 装 pre-push 钩子，推送前自动拦截
```

与 `.github/workflows/ci.yml` 同源（同样三条命令、同样的 compileall 排除规则），但多了一条线上没有的 `--cov-fail-under=70`：推 workflow 需要 `workflow` 权限，当前推送凭据没有，所以这条门禁只在本地生效。**改完代码至少跑一次，别靠记忆敲四行。**

- 解释器默认取 `.venv`，可用 `--python` 或 `$CI_PYTHON` 覆盖；缺依赖直接以退出码 2 退出，脚本不负责装包
- pytest 退出码 ≥128（PySide6 进程收尾信号）只有在输出证明「全部通过」时才忽略，绝不凭空放过
- `.coveragerc` 已 omit `shibokensupport/*` 与 `signature_bootstrap.py`——那是 PySide6 导入期写到工作目录又删掉的临时文件，计入分母会让覆盖率莫名其妙地漂


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
- **`cli_installer.py` 负责装 lark-cli**：纯逻辑（探测 npm/node、构造安装命令、刷新 PATH、翻译 npm 报错），`cli_install_async.py` 是 QProcess 外壳（逐行输出、300 秒超时、可取消）。两条铁律——① 不自动 sudo，全局目录不可写时只给建议；② 装完必须 `refresh_path(npm_bin_dir(npm))`，否则会出现「npm 说装好了、应用还说找不到」，因为 .app 从 Finder 继承的 PATH 里没有 npm 的全局 bin。`main.py:_extend_path_for_app_bundle` 也靠它补 PATH，让终端里装过的用户重启就能被识别
- **`event_store.py` 是本地事实层（v2.4）**：日程落 SQLite（`events.db`，与 config.json 同目录）。视图只从 store 读，`lark_cli_async` 只往 store 写。改渲染路径时不要绕过 store 直接读 `self.events`——`self.events` 是 store 当前窗口的投影，不是事实源
  - `upsert_many(conn, events, range_start, range_end)`：幂等写入 + 记录已同步区间；`prune` 只删「与本次区间重叠」或「更早开始的重复系列」且快照里没有的行。**非 list 载荷（None/dict）一律不动库**，防止坏响应清空缓存
  - `query_range` 的语义是**区间重叠**（`end_ts >= start AND start_ts <= end`），且**始终带出更早开始的重复系列**——否则重复日程在后续月份不展开
  - `read_range` / `store_snapshot` / `is_covered` 是给 UI 用的安全壳：库出问题返回空 / 0 / False，不允许把异常抛进 Qt 槽
  - 损坏库自愈在 `connect()` 里做：重命名为 `.corrupt-<ts>` 后重建，绝不阻塞启动
  - 全天日程的 `end_ts` 归一成当天 23:59:59，否则当天 10:00 发起的区间查询会漏掉它（`end_ts == start_ts`）
- **`utils.view_range(view_mode, current_date)` 是拉取区间的唯一真源**：月视图 = 本月 ±7 天（月历网格最多前后各溢 6 天），周视图 = 周一~周日 ±7 天。**不要再按「整月」拉取**——周视图跨月那一周会缺列（v2.3 的 D2 bug）
- `_set_view_mode` 切视图时先查 `event_store.is_covered`，已同步过的窗口只从本地重绘，不再起 node 进程；未覆盖才 `refresh_events()`
- 搜索是本地优先：`SearchDialog` 先用 `event_store.read_range` 出结果（离线可用），服务端结果回来后按 `event_id` 合并、服务端覆盖本地
- **`reminder.py` 是提醒的唯一决策点（v2.5）**：30 秒心跳，只读本地库，不发任何网络请求
  - 纯函数层（`collect_occurrences` / `due_reminders` / `find_conflicts` / `day_load_minutes` / `current_or_next` / `tray_summary` / `in_quiet_hours`）全部接收显式 `now`，禁止在这里调 `datetime.now()`，否则又变成不可测
  - `ReminderService` 只做三件事：读库、判类、发信号。**去重记账在发通知之前**（`event_store.mark_notified`），宁可丢一条也不重复轰炸
  - 去重键是「某一次发生」`<event_id>@<start>`，不是 `event_id`：每周例会下周要再提醒一次；`conflict:<date>` / `overload:<date>` 才是按天
  - 冲突与超载按**整天**取数（扫描窗只有 1 小时），否则早上算不到下午的会议
  - 免打扰命中时**直接返回、不记账**，否则静音期间的事件会白白消耗掉一次提醒
  - 已开始的事件不再提醒：`START_GRACE_SECONDS = 30`，超时就说明错过发车了
- **通知递送方向是单向的**：`MainWindow.notify_requested` → `TrayApp._on_notify_requested`。主窗口不知道托盘长什么样；没有托盘（headless/CI）时降级成 Toast，不允许静默丢弃
- **托盘摘要是「不打开窗口也要能看」的层**：`MainWindow._refresh_ambient()` 同时刷新 tooltip 与今日条，由 `tray_summary_changed` 信号推给 `main.py`。托盘菜单顶部那行是 disabled QAction——它只是信息，不能被点
- `today_bar.py` 是**独立顶层窗口**（无 parent、无边框、置顶、可拖），吃不到 application 级 QSS，换肤必须走 `apply_theme()`；点掉窄条 = 关闭该功能（写 `today_bar_enabled=False`），否则每次重启又冒出来等于没关
- 提醒相关配置全部由 `config.json` 驱动，设置页「提醒」Tab 改完下一次心跳即生效，**不需要重启**
- **`stats.py` 只算不画，`stats_dialog.py` 只画不算**：统计的输入永远是「事件列表 + 显式区间」，禁止在 stats 里读 clock 或 store；面板打开不触发同步，全部数字来自本地库
  - 全天日程计入「事项数」但不计入时长——否则一个公司假日就能把「会议小时」拉满
  - 热力图分档是 `HEAT_THRESHOLDS = (60, 120, 240)` + `heat_level()`，0 分钟必须返回 0（空白），别把阈值写成从 0 开始
  - `longest_streak` 必须校验日期相邻：只数条目会把 1/2/3/5 号算成连续 4 天
- **`exporter.py` 是唯一允许写用户目录的地方**，三条约束：原子写（temp + `os.replace`）、失败只记日志绝不弹窗、`export_last_run` 在落盘成功后才推进（失败下次重试而不是跳过一整天）
  - 定时检查在 `MainWindow._setup_export_timer`（启动 15 秒后首查 + 每 30 分钟），判定逻辑全在 `exporter.is_due`
  - 导出的是滚动窗口（回看 7 天 / 前瞻 30 天），**不是全量备份**，UI 文案别写成「备份」
- **`occurrences.py` 是 Qt-free 的具体发生层**：`collect(events, start, end)` 负责展开 RRULE、去重（键 `<event_id>@<start>`）、排序。`reminder` / `stats` / `backends` / `headless` 全部复用它，**不要在别处再写一遍展开逻辑**
  - 它必须保持不 import PySide6：`tests/test_headless.py::test_cli_runs_without_pyside6` 会检查这一点，破坏它等于让命令行入口在无显示的服务器上起不来
- **`backends.py` 的定位要说清**：协议 + 三实现（lark-cli / 本地库 / ICS），当前由 **headless CLI 与测试**消费；**GUI 故意不走它**，因为它是同步的，把窗口刷新塞进同步调用会让界面卡几秒。GUI 继续用 `lark_cli_async`（QProcess）。别误以为它是死代码，也别顺手把 GUI 改成同步调用
  - `fetch_range` / `search` 统一返回 **Occurrence**（不是原始 dict），否则每个调用方都要自己展开重复规则
  - 只读后端（本地库、ICS）的写入方法抛 `ReadOnlyBackend`，不许静默成功
  - ICS 解析只处理 VEVENT + SUMMARY/DTSTART/DTEND/DESCRIPTION/LOCATION/ORGANIZER/RRULE，含折行展开；未知属性忽略而不是猜
- **`headless.py` 的输出是对外契约**：`--json` 信封 `{command, generated_at, count, events[]}`，退出码 0/1/2。公共选项挂在**子命令**上（`headless today --json`），挪到顶层会让「子命令后写参数」直接报错
- **覆盖率门禁在 CI**（`.coveragerc` 排除 tests/，`--cov-fail-under=70`）：本地实测应用代码 75%，新模块别把它拉下去。UI 弹窗类（export_dialog / login_dialog）天然低覆盖，属于已知区间，不必为凑数字写假测试
- 月历 7 列等宽约定：GridEventLabel/DayCell 水平 sizePolicy=Ignored，表头用 QGridLayout，勿让内容撑宽列
- **日格样式名是拼接出来的**：`DayCell._refresh_object_name()` 按「基础名(dayCell/dayCellOther/dayCellToday) + Drop > Cursor > Hover」合成，改样式时这 6 个新后缀（`…Drop` / `…Cursor`）两套主题都要补
- **日格可容纳条数按实际高度算**：`widgets.visible_event_count(grid_font, cell_height, reserve_more)`，窗口压矮或 6 行月份时自动收缩，但必须给「+N更多」留一行（`_MORE_ROW_HEIGHT`）——它是隐藏日程唯一的入口，被挤出去就再也点不开了；`DayCell.resizeEvent` 会重算
- **快捷键一律包一层 modal 守卫**（`main_window._setup_shortcuts`）：对话框是主窗口的子窗口，Qt 的 WindowShortcut 在对话框内照样触发，否则在标题框敲 `n` 会再弹一个新建框
- **删除确认放在发出删除的那个窗口里**（`EventDetailDialog` / `DayDetailDialog` 各自弹 ConfirmDialog）；主窗口连的是 `_delete_event` 而不是 `_confirm_delete`，避免弹两次
- 飞书读写能力集中在 `lark_cli.py`/`lark_cli_async.py`，**重构只动 UI 层**：拖拽改期复用 `update_event`，重复写入复用 `+create --rrule`/`patch recurrence`，颜色仅存本地 `config.json.event_colors`，子任务即描述里的 Markdown 勾选清单 `- [ ]`
- **lark-cli `calendar +create` 没有 `--location`**（只有原生 `calendar events create --data` 才带 location 字段），所以新建对话框的「地点」按 `add_event_dialog.compose_description()` 以 `📍 地点：` 追加进描述，**不要再给 `create_event` 传 `location=`**（会 TypeError 并让表单永久卡在「创建中…」）
- **全天日程（`start_time.date`）不要用 timestamp 写回**：勾选子任务时只改描述、不传 start/end，否则整天事件会被改成带具体时刻的定时事件
- `config.json` 存窗口/主题（默认 dark、opacity 1.0）/刷新间隔/视图模式/颜色/`grid_font_size`/`list_font_size`/`usage_stats_enabled`/`auth_completed`/`auth_user`（`.gitignore` 排除，不含任何凭据）
- **视觉的真源是 `theme.py`，不是 `styles.py` 里那些十六进制**：令牌分三层——字体栈（`SANS_STACK` / `MONO_STACK`）、尺度（`RADIUS` / `SPACE` / `FONT_SIZE` / `DURATION` / `EASING_ENTER`）、双主题调色板（`_DARK` / `_LIGHT`，`tokens(name)` 取用，未知主题名退回深色不抛异常）。`paint_colors(name)` 给 QPainter 自绘用
  - 外观层是 `styles._skin_rules(name)`，**追加在 `get_theme()` 最末尾**，靠 QSS「同特异性后定义者生效」压住基础层；它只改颜色/边框/圆角/字族，**刻意不动布局尺寸**（min-height、padding、grid 间距），日历密度是原有功能的一部分
  - 改外观时**先看基础层有没有带前缀的规则**：`QDialog QPushButton#primaryBtn`、`QDialog QTabBar::tab`、`QDialog QGroupBox` 这类带 `QDialog` 前缀的选择器特异性更高，只写 `QPushButton#primaryBtn` 是压不住的（对话框里的主按钮曾经一直是老的飞书蓝就是这个原因）
  - 基础层的飞书蓝 #3370FF 仍留在 `styles.py` 里当兜底，新写控件不要再抄它；要颜色就 `theme.tokens(...)`
- **QSS 里的 `QWidget` 是个陷阱**：`QMainWindow, QDialog, QWidget { background-color: bg }` 会把 QLabel / QCheckBox 一起刷成窗口底色，落在比背景更亮的组框表面（`surface`）上就是一道道深色横条。底色只给窗口和对话框，字体/文字色另立一条不带 `background` 的 `QWidget` 规则
- **主窗口台面是自绘的**：`MainWindow.paintEvent` + `_backdrop()` 烘焙 QPixmap 缓存（key = 宽/高/主题名/DPR），画深底 + 右上径向光晕 + 20° 旋转青蓝光带。换肤时必须丢弃缓存（`_apply_theme` 里已做）。QSS 里看不到这一层，改配色要去 `theme.PAINT`
- **不要用 `setFixedSize` 关住对话框**：`QVBoxLayout` 在空间不够时会把子控件压到低于 sizeHint——标签高度变 0、组框里的控件叠在一起，而且没有任何报错。设置窗和统计窗都栽过（520×560 / 520×620 vs 实际需要 613×727 / 654×860）。做法是让内容决定尺寸（`SettingsDialog._fit_to_content` / `StatsDialog._fit_size`），放不下时滚动（统计窗用 QScrollArea）或退回屏幕可用区
  - 量尺寸要在 `showEvent` 之后：构造期子控件还没被 polish，`sizeHint` 全是初值
  - `QGroupBox` 的 QSS `margin` 不计入 `sizeHint`，四值 `padding` 会同向压缩内容区，所以对话框里的组框用 `margin-top: 8px; padding: 2px 0 0 0`，标题就压在边框线上（Qt 官方示例的做法）
- **UI 改动必须真的看一眼**：QSS 和自绘都没有单元测试能断言。`tools/ui_shot.py` 灌 18 条中文示例日程，在 `QT_QPA_PLATFORM=offscreen` 下用 `QWidget.grab()` 截月/周视图（这台机器没有屏幕录制权限，`screencapture` 拿不到窗口）。冒烟命令：`QT_QPA_PLATFORM=offscreen .venv/bin/python tools/ui_shot.py .ui_shot dark`（第二参数换成 `light` 出浅色）
- **日程字号可调（v2.1.6）**：`config.grid_font_size`（月视图，默认 10）/ `config.list_font_size`（周·列表视图，默认 13），范围 9-24px，设置页「外观」Tab 两个滑块；实现方式是 `styles._event_font_rules()` 生成覆盖规则**追加在主题 QSS 末尾**（同名选择器后定义者生效），不改两套大模板；时间与次要信息由主字号派生（月视图 -1、列表 -2）。改字号必须同步放开 `QFrame#gridEvent` 的 min/max-height（行高 = 字号 +6/+8），否则大字号会被裁；字号变化后 `MainWindow._on_settings_changed` 会 `_render_active_view()` 重建视图

## 当前状态
- **v2.7.0 后端协议与 headless（已实现）**：新增 `occurrences.py`（Qt-free 具体发生层，reminder/stats/backends 共用）、`backends.py`（`CalendarBackend` 协议 + lark-cli / 本地库 / ICS 三实现）、`headless.py`（`python -m headless today|next|range|search`）；CI 加覆盖率门禁（`--cov-fail-under=70`，本地 75%）
  - 测试：`tests/test_backends.py`（19）、`tests/test_headless.py`（12，含「不得 import PySide6」与 `-m` 入口用例）
  - 全量 **440 例**，`ruff check` 全绿，应用代码覆盖率 75%
- **v2.6.0 洞察与可编程导出（已实现）**：新增 `stats.py` + `stats_dialog.py`（月热力图 / 负荷摘要 / 星期分布）、`exporter.py`（定时 JSON+CSV 原子写）；README 补「隐私说明」与「实验性功能」
  - 测试：`tests/test_stats.py`（16）、`tests/test_exporter.py`（14）、`tests/test_stats_ui.py`（9）
- **v2.5.0 提醒与常驻形态（已实现）**：新增 `reminder.py`（会前提醒 / 冲突 / 超载 / 免打扰）+ `today_bar.py`（桌面窄条），托盘标题与菜单顶行动态化
  - 测试：`tests/test_reminder.py`（27 例，纯逻辑 + 服务去重/静默/降级）、`tests/test_ambient.py`（12 例，托盘摘要信号、今日条开关/换肤/关闭、通知降级、提醒配置校验）
- **v2.4.0 本地事实层（已实现）**：新增 `event_store.py`（SQLite）+ `utils.view_range`，主窗口改为「先本地出图 → 再远端校准」；同时修掉周视图跨月漏日程（D2）、离线不可用（D1/D7）、全量覆盖非增量（D3）
  - 测试：`tests/test_event_store.py`（29 例，含幂等、区间重叠、prune 边界、重复系列、损坏自愈、LIKE 转义）、`tests/test_view_range.py`（30 例，含 2026/2027 全年 24 个月的网格覆盖性质测试）、`tests/test_local_first.py`（11 例，主窗口集成：缓存先出图、重启不丢、离线保留视图、跨月双侧显示、已同步窗口不联网、离线搜索）
  - 全量 **331 例**，`ruff check` 全绿
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
- 当前测试总量 **260 例**（199 + 38 + 23），`ruff check` 全绿
- v2.3.0 增量更新：见下方「增量更新（exe_delta.py）」；Windows EXE 从 53.51 MiB 降到 3.01 MiB（省 94.4%），失败自动回退全量
- v2.2.0 发布约定：推 `v*` 标签触发 `.github/workflows/release.yml`（CI 跑测试 → 打包 Windows EXE + macOS zip → 挂到 Release → 生成并挂 `SHA256SUMS`）。客户端 Windows 静默更新依赖 Release 里的 `.exe` 资产 + `SHA256SUMS`，两者缺一则退回「发现新版本」Toast 引导手动下载；**勿删这两个资产**。CI 用 `FC_APP_NAME=FeishuCalendar` 产出 ASCII 名 `FeishuCalendar.exe`，客户端 `find_exe_asset()` 会回退到 `exes[0]` 命中它
- 新增模块后记得同步 `build_windows.ps1` 与 `build_macos.sh` 的 `--hidden-import` 清单（仓库里的 `*.spec` 被 gitignore，是本地构建产物，不用管）

## Git 仓库：状态判定铁律（接手必读）
- **版本真源**是 `__version__.py` 的 `APP_VERSION`（当前 `2.3.0`），关于页与 OTA 更新器共用；发版只改这一处 + bump Release tag
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

### 增量更新（exe_delta.py，v2.3.0 起）
- **为什么必须按成员而不是按字节**：CArchive 里成员顺序拼接，前面任一成员变长会让后面整体偏移。实测固定偏移分块命中率 **0%**、FastCDC 命中率 **0%**，看着像"没有可复用内容"，其实是字节基座被整体挪动了。**成员边界才是稳定的复用单位**
- 实测 v2.1.6 → v2.2.0：239 个成员里 **236 个逐字节相同**，只有 `PYZ.pyz` / `base_library.zip` / `main` 变了 → 补丁 3.01 MiB vs 全量 53.51 MiB（**省 94.4%**），且 `apply_delta` 能**字节级复现官方产物**（`tests/test_exe_delta.py` 有真实样本往返用例）
- 补丁里装：目标 EXE 的引导程序 + TOC + cookie + 变更成员原文；未变成员不装数据，客户端从本机旧 EXE 按偏移切片复制
- **安全边界**：补丁头带 `base_sha256`，本机 EXE 不匹配就拒绝（防止把补丁打到错误基线）；产出结果先比 `target_sha256_prefix`，再由 `SHA256SUMS` 权威校验。**任何一步失败都静默回退全量下载**——补丁只是优化，不是唯一路径
- 生成侧在 CI：`tools/make_delta.py` 通过 API 找上一个带 `.exe` 的正式版作基座；找不到时**以退出码 2 结束**，工作流跳过补丁上传（首个版本会这样，属正常）
- ⚠️ 改了 `updater.py` 的导入就要同步 `build_windows.ps1` / `build_macos.sh` 的 `--hidden-import` 清单
- ⚠️ 峰值内存约 2×EXE（基座 + 结果各 ~53 MiB），只在更新时短暂占用
