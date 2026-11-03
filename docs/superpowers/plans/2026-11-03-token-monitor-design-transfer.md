# Token Monitor 设计迁移改造方案（feishucalendarforfree v2.4）

> **参照物**：[Javis603/token-monitor](https://github.com/Javis603/token-monitor) v0.85.0（Electron + Node，1142 commits）
> **被改造对象**：feishucalendarforfree v2.3.0（PySide6，10.4k LOC，260 例测试）
> **原则**：抄设计，不抄功能；抄分层，不抄技术栈。

**Goal:** 把 token-monitor 已验证的「本地优先 + 解析/呈现解耦 + 一源多形态 + 主动告警 + 可编程导出」五项设计，落到飞书日程桌面端，同时修掉当前架构里三个真实缺陷（无本地层、跨月漏日程、零提醒）。

**Architecture:** 新增 `event_store.py` 作为本地 SQLite 事实层，`lark_cli_async` 降级为「远端同步器」；主窗口与托盘、今日条、提醒器都从 store 读，不再各自持有内存数组。

**Tech Stack:** 保持 Python 3.10+ / PySide6 / 标准库 `sqlite3`，不引入新依赖。

> **实施进度**：Phase 1（v2.4.0）已实现并本地提交（`caa21a1`），331 例测试全绿。
> Phase 2–4 未开始。

---

## 一、token-monitor 的设计内核（值得迁移的部分）

| # | 设计原则 | token-monitor 的做法 | 为什么有效 |
|---|---|---|---|
| P1 | **本地优先，双模式** | Mode A 单机零服务器；Mode B 多设备同步为 opt-in | 主路径不依赖网络/服务端，启动即用，失败面小 |
| P2 | **解析与呈现解耦** | 底层 `tokscale` 二进制负责日志解析与计费，App 只做 UI/同步/限额 | 数据源可换（38+ 工具）而 UI 不动；单一变更点 |
| P3 | **滚动窗口 + 本地归档** | 370 天窗口；工具删旧会话后仍保留已观测的每日用量 | 上游数据会被清理，本地归档让历史连续 |
| P4 | **一源多形态 + 布局可配** | 同一份数据渲染到刘海/边缘停靠/菜单栏/原生组件/浮窗，菜单栏布局可拖拽 | 呈现形态决定使用频率；用户按场景选，而不是被迫开主窗口 |
| P5 | **主动告警可插拔** | `plugins/quota-alerts`：限额将尽时主动推送 | 工具从「查得到的面板」升级成「会说话的助手」 |
| P6 | **导出可编程** | CSV/JSON 手动或定时写入指定文件夹（适配表格/Obsidian/Grafana） | 数据能被别的工具消费，产品边界外扩 |
| P7 | **边界显式声明** | 隐私（提示词/代码不出本机）、实验性（非官方 API 无兼容保证）、安全（插件未沙箱）逐条写明 | 降低误用与信任成本 |

**不建议迁移**：Electron 技术栈、未沙箱插件系统、48 工具栏的广度、Notch 面板（需 Swift 原生）、多设备 Hub（日程本已在飞书云端同步，本地配置同步收益远低于成本）。

---

## 二、现状诊断（代码级证据）

### D1 无本地数据层 —— 最严重的架构缺口
全仓无 `sqlite` / 缓存模块（`grep sqlite|cache|\.db` 零命中）。日程只存在于 `MainWindow.events` 内存数组（main_window.py:147），重启即空。后果：

- **离线不可用**：断网/飞书故障时窗口是白板，连昨天看过的日程都看不到。
- **每次交互都付冷启动税**：`refresh_events()` 切月、切周、回到今天、300s 定时刷新、每次增删改后都触发一次 `QProcess` → 启动 `node` 跑 lark-cli（lark_cli_async.py:51-187）。node 冷启动 1-3s，而用户只是想翻到下个月。

### D2 视图范围与拉取范围不一致（真实 Bug）
`refresh_events()` 固定 `monthly=True`（main_window.py:954），永远只拉当前月。周视图下若一周跨月（如 10-26 ~ 11-01），11 月侧列**永远是空的**，且无任何提示。

### D3 刷新是全量覆盖，非增量
`_on_events_fetched()` 直接 `self.events = events`（main_window.py:958）。没有 diff、没有 tombstone、没有"上游删了这条"的概念，也就无法支撑任何本地历史。

### D4 零主动提醒能力
`grep Notification|notify|提醒|remind` 在业务代码零命中（`notify_update` 只是更新提示）。一个日历应用没有「10 分钟后开会」的系统通知——这是产品级缺口，不是体验细节。

### D5 托盘是哑的
`tray.setToolTip("飞书日程 - 点击显示")`（main.py:143）静态不变。用户在菜单栏/托盘区看不到「下一条日程是什么」「今天还有几项」——必须点开窗口才能获得信息，使用频次天然被压低。

### D6 单一呈现形态
只有「主窗口 + 托盘菜单」两态。对照 P4，缺的是**常驻的低打扰形态**：今天的日程条、下一条倒计时、浮窗。

### D7 搜索只能在线
`+search-event` 是服务端接口（lark_cli_async.py:214-240）。本地无索引，断网即搜索不可用。

### D8 门禁缺覆盖率
CI 有 ruff + compileall + pytest 三绿（.github/workflows/ci.yml），但无 coverage 阈值。260 例测试是资产，但新增模块没有"必须被覆盖"的约束。

---

## 三、迁移映射矩阵

| token-monitor | 飞书日程的等价物 | 收益 | 成本 | 优先级 |
|---|---|---|---|---|
| P1 本地优先 | `event_store.py`（SQLite）+ 缓存优先渲染、后台校准 | ★★★★★ 修 D1/D3/D7，离线可用，翻月瞬时 | 中 | **P0** |
| P3 滚动窗口 + 归档 | 本地保留过去 12 / 未来 3 个月，超出上游范围的本地副本不删 | ★★★★ 支撑搜索、统计、历史对照 | 低（P1 顺带） | **P0** |
| P5 主动告警 | 会前提醒 + 日程冲突 + 单日超载阈值 | ★★★★★ 修 D4，产品性质改变 | 中 | **P1** |
| P4 一源多形态 | 托盘动态标题（今日剩余/下一条）+ 今日条 + 浮窗 | ★★★★★ 修 D5/D6，提升日活 | 中 | **P1** |
| P6 可编程导出 | 定时导出 JSON/CSV 到指定目录（兼容 Obsidian） | ★★★ 与现有 Excel 导出互补 | 低 | **P2** |
| P— 统计洞察 | 日程热力图 / 周会议时长 / 连续使用 | ★★★ 现有 usage_stats 只统计安装数，无用户价值 | 中 | **P2** |
| P2 解析/呈现解耦 | `CalendarBackend` 协议（lark-cli / ICS / CalDAV） | ★★ 长期架构弹性，当前只有一种后端 | 中高 | **P3** |
| P7 边界声明 | README 隐私与实验性章节 | ★★ 信任成本 | 极低 | **P2** |
| 定时窗口刷新 | 范围感知拉取（修 D2） | ★★★★ Bug 修复 | 低 | **P0** |

---

## 四、分阶段实施方案

### Phase 1（v2.4.0）· 本地事实层 —— 修 D1 / D2 / D3 / D7

**新增 `event_store.py`**（仅标准库 `sqlite3`）：

```
events(
  event_id TEXT, calendar_id TEXT, summary TEXT,
  start_ts INTEGER, end_ts INTEGER, all_day INTEGER,
  rrule TEXT, description TEXT, organizer TEXT,
  color TEXT, raw_json TEXT, updated_at INTEGER,
  PRIMARY KEY (event_id, calendar_id)
)
sync_ranges(range_start INTEGER, range_end INTEGER, synced_at INTEGER)
```

关键接口（全部纯函数式，便于 offscreen 单测）：

- `upsert_many(conn, events, range_start, range_end)` —— 幂等写入 + 记录已同步范围
- `query_range(conn, start, end)` —— 含跨天事件（`start_ts < end AND end_ts > start`）
- `covered_ranges(conn)` —— 返回已同步区间，用于判断"这个月能不能直接本地出图"
- `search(conn, query)` —— 本地 LIKE + 标题/描述/发起人，离线兜底

**改造点：**

1. `main_window.refresh_events()`：先 `query_range` 立刻出图（本地命中则 0ms），再异步 `fetch_agenda` 校准；未覆盖范围才打网络。
2. **修 D2**：拉取范围按视图算——月视图 = 本月 + 前后各 7 天缓冲；周视图 = 该周起止 ± 7 天。抽 `utils.view_range(view_mode, current_date)` 纯函数，配单测。
3. `_on_events_fetched()`：改为 `upsert_many` 后重新 `query_range`，不再直接覆盖数组。
4. `search_dialog`：先本地 `search()` 出结果，再异步补服务端结果（去重合并）。
5. 写入成功（create/update/delete）后同事务更新 store，保证本地即时一致。

**验收：** 断网启动仍显示上次日程；翻月 <100ms；周跨月不再缺事件；新增 `tests/test_event_store.py`（含跨天、跨月、重复日程、并发写、损坏库自愈）。

---

### Phase 2（v2.5.0）· 主动提醒与常驻形态 —— 修 D4 / D5 / D6

1. **`reminder.py`**：30s 心跳扫描未来 60 分钟窗口，按 `config.reminder_lead_minutes`（默认 10，可 0/5/10/15/30）触发 `QSystemTrayIcon.showMessage`；同 event_id 只提醒一次（store 记 `notified_at`）。
2. **冲突/超载告警**：同时间段 ≥2 项 → 冲突提示；单日非全天日程总时长 > 阈值（默认 6h）→ 一次轻提示。对应 P5 的 quota-alerts。
3. **托盘动态标题**：`今日 N 项 · 下一条 14:30 评审`（超长截断）。手动刷新时同步更新，不做常驻 tick，避免耗电。
4. **今日条（可选开关）**：无边框置顶窄条，显示今天剩余日程，鼠标穿透可选——对标 Edge Dock。
5. 设置页「提醒」Tab：开关、提前量、冲突告警、超载阈值、免打扰时段。

**验收：** 3 分钟后的测试日程能在 10 分钟前弹通知且仅弹一次；免打扰时段内静默；托盘标题随日程变化；`tests/test_reminder.py` 全绿。

---

### Phase 3（v2.6.0）· 洞察与可编程导出

1. **日程统计页**：月热力图（每日会议小时数着色）、周会议时长、最忙日、连续记录天数。数据全部来自 store，零额外请求。
2. **定时导出**：`config.export_dir` + 周期（每日/每周），写 `events-YYYYMMDD.json` + `.csv`，原子写（temp + `os.replace`）；失败只记日志不弹窗。
3. README 补「隐私边界」（本地只存日程元数据，不含附件正文；匿名统计 opt-out 生效路径）与「实验性功能」标注。

---

### Phase 4（v2.7.0）· 后端抽象与 headless

1. `CalendarBackend` 协议：`fetch_range / create / update / delete / search`。`LarkCliBackend` 为唯一实现，`IcsBackend` 作为只读本地订阅。
2. **headless CLI**：`python -m fcf today --json`，输出今日日程给脚本/快捷指令/Stream Deck 消费——对标 token-monitor 的 headless agent。
3. 覆盖率门禁：CI 加 `--cov-fail-under=70`，新增模块不得拉低。

---

## 五、全局约束

- 不引入新第三方依赖（`requirements.txt` 保持 PySide6 + openpyxl）。
- 所有 store 访问经单一封装，UI 层不得直接拼 SQL。
- 写库用 `PRAGMA journal_mode=WAL` + 事务，损坏时删库重建并由远端重灌（不得阻塞启动）。
- 现有 260 例测试必须全绿；`ruff check` 零告警。
- Qt 测试统一 `QT_QPA_PLATFORM=offscreen`。
- 版本真源仍为 `__version__.py`；每阶段独立发版，支持随时回退。
- 新增模块须同步 `build_windows.ps1` / `build_macos.sh` 的 `--hidden-import`。

---

## 六、预期结果

| 指标 | 现状 | Phase 1 后 | Phase 2 后 |
|---|---|---|---|
| 断网可用 | 否 | 是（最近 12/3 个月） | 是 |
| 翻月响应 | 1-3s（node 冷启动） | <100ms | <100ms |
| 周视图跨月 | 缺事件 | 正确 | 正确 |
| 会前提醒 | 无 | 无 | 有 |
| 离线搜索 | 不可用 | 可用 | 可用 |
| 常驻可见信息 | 无 | 无 | 托盘标题 + 今日条 |
