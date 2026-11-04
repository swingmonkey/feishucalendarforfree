# Handoff：桌面小组件（深度参考 token-monitor）

> 写于 2026-11-04，接手前请先读 AGENTS.md（项目约定真源）。
> 参考源码：`/Users/foye/Applications/token-monitor-app`（完整应用，含 Swift 小组件与 Electron 快照桥）；
> `../tm-ref/` 只有官网 CSS，**别拿它当视觉真源**（差异见下）。

## 0. 一句话现状

三档自绘桌面小组件（`desktop_widget.py`，583 行）已写完并人工目检通过，主窗口/设置页/config 接线已完成，
**但测试、截图工具、打包清单、AGENTS.md、门禁、提交全部未做**；工作树 9 个文件未提交（列表见 §5）。

## 1. 路线决策（用户已拍板，不要推翻）

- **Qt 自绘浮窗小组件**，不是 macOS WidgetKit：真 WidgetKit 需要付费开发者 Team ID + Developer ID 双
  provisioning + 公证 + Xcode target，参考项目自己的 `native/macos/README.md:15` 明说
  "ad-hoc host and extension cannot access that App Group"；本仓 `release.yml` 零签名 secret，硬阻塞。
- **内容三档全做**（small / medium / large），对应 macOS 小组件的真实尺寸。
- 未来若买开发者账号：Python 侧照抄参考项目的「JSON 快照 + schemaVersion 硬校验 + 原子写」即可零返工接 Swift 扩展。

## 2. 视觉真源（这条最重要）

参考的是 **SwiftUI 实现**（`native/macos/TokenMonitorWidget/Widget*Views.swift`），不是官网 CSS：

| 项 | 原生实现 | 官网 CSS（勿用） |
| --- | --- | --- |
| 台面 | 近实心 `rgb(0.035,0.043,0.055)` + 斜向渐变（右上白 2.5% → 左下 accent 13%） | 高透玻璃 `rgba(40,44,52,.42)` + backdrop blur |
| 阴影/高光 | 无 | 多重 box-shadow + inset |
| 动画 | 无（WidgetKit 快照静态化） | wdg-cell-in 等 9 组 keyframes |

所有数值已落进 `theme.py`：`WIDGET_SIZES` / `WIDGET_SIZE_LABELS` / `widget_size_choices()` /
`WIDGET_FONT` / `WIDGET_LAYOUT` / `_WIDGET`（双主题） / `widget_tokens(name)`。
**desktop_widget.py 里不允许出现写死的颜色或尺寸**——这是硬约定，测试要守（见 §6）。
参考实现把小组件写死深色（`.environment(\.colorScheme,.dark)`），我们两套都做了，
理由是「换肤必须真的换肤」已是项目约定（`tests/test_skin_surfaces.py` 守着）。

## 3. 已完成（按文件）

- **`widgets.py`**：新增 `FloatingSurface` 基类——frameless+Tool+置顶+半透明、拖拽（位移 <4px 视为点击）、
  `restore_position(-1 回落主屏右下)`、`activated`/`closed` 信号。`TodayBar` 已改为继承它，公开 API 不变，
  现有 50 例测试全过。
- **`desktop_widget.py`（新）**：
  - 数据层 `build_snapshot(events, now, synced_ts)` 纯函数 → `WidgetSnapshot`（今日数/分钟、下一条、
    明细≤4 行、近 7 天趋势、本月热力（`stats.month_grid` **转置**成星期为行）、本月小时、周负载行、
    更新时间、stale）。
  - 呈现层 `DesktopWidget(FloatingSurface)`：三档 `paintEvent` 全自绘；热力五档（`stats.heat_level`）；
    趋势曲线 Catmull-Rom 转三次贝塞尔（控制点 `(next-prev)/6`、线宽 1.8、round cap）；3px 胶囊条；
    底部 footer band（左=更新时间/过期 ⚠，右=本月小时）。
  - 右键菜单：打开主窗口 / 换尺寸 / 关闭（尺寸标签与设置页共用 `theme.widget_size_choices()`）。
  - 空态（「暂无日程数据/打开飞书日程一次」）、未同步、stale（20 分钟，`STALE_SECONDS`）。
- **`event_store.py`**：新增 `last_synced_ts()` + UI 安全壳 `last_synced()`（坏库返回 None，风格对齐
  `read_range`）。
- **`main_window.py`**：`_widget_events()`（本月+前 7 天，**不要放宽**，趋势只要 7 天）、`_widget_snapshot()`、
  `_apply_desktop_widget()`、`_on_widget_size_changed()`（先存落点再换档重新落位）、`_on_widget_closed()`
  （=写 config 关功能，与今日条同语义）、`_save_widget_geometry()`；已接 `_refresh_ambient`（30s 心跳即刷新）、
  `_apply_theme`、`_on_settings_changed`、启动 `__init__` 后段、`dispose()`、`closeEvent`。
- **`main.py`**：托盘退出时补 `_save_widget_geometry()`。
- **`config.py`**：`widget_enabled` / `widget_size`（枚举）/ `widget_x` / `widget_y`（int，-1=自动落位）。
- **`settings_dialog.py`**：外观页「桌面挂件」组（开关 + 三档单选），handler 走 `settings_changed` 即时生效。

## 4. 未完成（按优先级，接手后从上往下做）

1. **端到端接线冒烟**：上次中断于 `QMenu.exec()` 在 offscreen 下开阻塞事件循环永不返回——
   打桩即可（`QMenu.exec = fake_exec` 捕获菜单），或只断言菜单不 exec。
2. **`tests/test_desktop_widget.py`**（还不存在），建议覆盖：
   - `build_snapshot`：today_count/minutes、trend 长度与方向（最旧→最新）、热力转置（7 行星期 × N 列周）、
     空态、stale 边界（19 分钟 False / 21 分钟 True）、无 synced_ts → stale=True 且文案「尚未同步」；
   - `DesktopWidget`：三档 `setSize` 后 `width/height == theme.WIDGET_SIZES[key]`、脏 key 回退 medium；
     `apply_theme` 后 `_t` 换套；空数据 offscreen `grab()` 不炸；
   - `_qcolor`：3 元组不透明、4 元组 alpha×255（0.03→7 而不是 0）；
   - 接线：`widget_enabled=True` → `_apply_desktop_widget()` 可见；`close_requested` → config False；
     `size_change_requested` → config + 尺寸变化；`event_store.last_synced` 坏库返回 None。
   - 守卫：desktop_widget.py 源码无十六进制色值（照抄 `test_skin_surfaces.py` 的 AST 扫法，docstring 豁免）。
3. **`tools/ui_shot.py`** 补小组件截图：现成渲染逻辑在 `/tmp/widget_shot.py`（会话临时文件，随时可能没了），
   搬进去；注意小组件要合成到底色上再存（同今日条的 `save_over_backdrop`，否则透明像素看不出玻璃/台面）。
4. **打包清单**：`build_macos.sh` 与 `build_windows.ps1` 的 hidden-import 各加 `desktop_widget`
   （AGENTS.md 的同步义务）。
5. **AGENTS.md** 记新约定（§2 的令牌约定、FloatingSurface、footer band、QColor alpha 坑、QFont.Weight）。
6. **跑门禁 + 提交**：`QT_QPA_PLATFORM=offscreen .venv/bin/python tools/ci.py`，全绿后提交
   （用户本轮态度：提交可以，发版等指示）。
7. 视觉微调待看：medium 左列 subline 行高、large「本周负载」只有 3 行时的留白、
   footer 左 60%/右 40% 分区在极端文案下可能重叠（届时改为分别测宽）。

## 5. 工作树状态（`a698cad` 之后全部未提交）

```
M config.py  event_store.py  main.py  main_window.py  settings_dialog.py  theme.py  today_bar.py  widgets.py
?? desktop_widget.py
```

## 6. 本轮踩过的坑（接手前必读）

- **`QColor(r,g,b,a)` 第四参是 0-255 整数**：令牌里的 0-1 小数直接传会被截成 0 → 全透明且**不报错**。
  症状是热力格/台面渐变/分隔线/进度条轨道同时消失，看着像布局错。已用 `desktop_widget._qcolor()` 统一转换，
  新增自绘颜色必须走它。
- **PySide6 没有 `QFont.Weight.SemiBold`**，只有 `DemiBold`。
- **自绘文字对齐**：`AlignVCenter` 配整块区块矩形会把眉题甩到竖直中央（小档盖住大数字、大档跑到柱条下面）；
  眉题一律 `AlignTop`。单位「项」要按数字的字体度量算基线（`baseline = center - h/2 + ascent`），
  不能按矩形底对齐。
- **热力格上限是参考实现的产物不是审美**：原生 cell 上限 9.5px 是「44% 宽度要塞 16 周」的约束；
  我们只画当月 ≤6 列，照抄会留大片空白，所以 `WIDGET_LAYOUT["heat_cell_max"]=13` 且按「填满可用面积」取。
- **`QMenu.exec()` 在冒烟脚本里会挂死**（offscreen 无用户交互）；测试里打桩。
- 本机 `grep`/ripgrep 对部分中文源文件失灵（判为二进制），用 Read 或 `python3`。
- pytest 必须带 `--basetemp=.pytest_tmp`（沙箱 shim 的 mkdir EEXIST）。
- 仓库数据通路红线：`occurrences.py` 保持 Qt-free（有测试守着）；视图只从 store 读，不在重绘路径起 node。

## 7. 验证命令

```bash
# 渲染六张目检图（临时脚本，做完 §4.3 后由 ui_shot.py 取代）
QT_QPA_PLATFORM=offscreen .venv/bin/python /tmp/widget_shot.py
# 门禁
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/ci.py
# 人工看图
open .ui_shot/widget-large-dark.png .ui_shot/widget-medium-light.png
```

已人工目检过的六张：`.ui_shot/widget-{small,medium,large}-{dark,light}.png`（渲染正常：热力填满、
footer 两端不撞、浅色蓝阶可读）。
