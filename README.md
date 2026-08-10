# 飞书日程桌面助手 (FeishuCalendarDesktop)

在 Windows / macOS 桌面显示飞书日历日程的**月历 / 周计划双视图**应用，支持添加、删除、查看、拖拽改期日程，并参考 [WeekToDo](https://github.com/manuelernestog/weektodo) 的交互理念做了组件化重构。

底层对接飞书日历的方式不变：仍然通过 `lark-cli` 读取与写入日程（认证统一走 lark-cli 用户授权，应用内扫码登录），**飞书读写能力完全保留**。

## 功能

- **月 / 周双视图** - 顶部「月 / 周」切换。月历网格纵览整月；周计划（weektodo 风格）以 7 列展示本周每天的可滚动日程卡片
- **拖拽改期** - 在月历格之间、或在周计划各列之间拖动日程卡片即可改期，自动写回飞书
- **日程颜色 / 分类** - 新建或查看日程时可设置颜色（本地分类，按 event id 存于 config.json，不影响飞书）
- **重复日程** - 创建时选择每天 / 每工作日 / 每周 / 每两周 / 每月，写入飞书 RFC5545 重复规则；读取时按规则在视图内展开显示（♻ 标记）
- **子任务 / Markdown** - 描述支持 Markdown 渲染；描述中以 `- [ ]` 书写的勾选清单会渲染为可交互子任务，勾选后写回飞书
- **日程预览** - 格内显示时间和部分标题，放不下自动截断，悬停查看完整标题
- **当日详情** - 点击"+N更多"查看某天全部日程列表，点击日程查看详情
- **日程详情** - 点击日程查看完整信息（时间、组织者、会议链接等）
- **搜索功能** - 关键词搜索过去12个月至未来3个月的所有日程，支持标题/描述/发起人搜索
- **鼠标悬停高亮** - 鼠标移到日期格上自动变色强调
- **添加/删除日程** - 通过表单创建或一键删除日程
- **可调节窗口** - 拖拽右下角调整窗口大小，尺寸自动保存
- **置顶切换** - 📌置顶 / 📍不置顶，图标一目了然
- **今天高亮** - 当天日期用蓝色圆圈标记
- **最小化** - 标题栏「—」一键最小化窗口，托盘点击恢复
- **一键登录按钮** - 月历栏「⚙ 一键登录」打开应用内授权；已授权后自动隐藏
- **设置面板** - 配置登录、开机启动、透明度、刷新间隔
- **桌面快捷方式** - 首次运行自动在桌面创建快捷方式（Windows .lnk / macOS symlink），仅创建一次
- **应用内扫码登录** - 首次启动自动弹出登录窗口，扫码或网页授权，无需手动配置
- **开机启动** - 可设置开机自动运行
- **系统托盘** - 后台运行，托盘菜单快捷操作
- **主题切换** - 深色 / 浅色主题
- **自动刷新** - 定时自动同步最新日程
- **授权后自动刷新** - 检测到授权错误时自动重试获取日程
- **错误信息可复制** - 错误提示支持选中和复制，方便排查问题
- **导出日程** - 一键导出当前范围日程到 Excel

## 认证方式（lark-cli 用户授权）

```bash
npm install -g @larksuite/cli
lark-cli config init
lark-cli auth login --scope "calendar:calendar.event:read" --scope "calendar:calendar:read"
```

> **注意：** `--recommend` 不包含日历日程读取权限，必须使用上面的 `--scope` 参数明确指定。

## 安装与运行

### Windows

#### 方式一：直接运行 EXE（推荐）

1. 下载 `dist/飞书日程.exe`
2. 双击运行
3. 首次运行点击 ⚙ 设置按钮配置认证方式

#### 方式二：从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

或双击 `启动飞书日程.bat`。

#### 打包 EXE

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "飞书日程" \
  --paths "." \
  --hidden-import openpyxl \
  --hidden-import config \
  --hidden-import styles \
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
  main.py
```

生成的 EXE 在 `dist/飞书日程.exe`。

### macOS

#### 方式一：直接运行 .app（推荐）

1. 下载 `dist/飞书日程.app.zip` 并解压
2. 首次打开若提示"无法验证开发者"，右键 → 打开 → 打开
3. 首次运行点击 ⚙ 设置按钮配置认证方式

> 配置文件位于 `~/Library/Application Support/FeishuCalendar/config.json`

#### 方式二：从源码运行

```bash
# 安装依赖
pip3 install -r requirements.txt

# 运行
python3 main.py
```

或双击 `启动飞书日程.command`。

#### 打包 .app

```bash
bash build_macos.sh
```

生成的 .app 在 `dist/飞书日程.app`。

## 使用说明

### 桌面窗口

- **拖动** - 按住窗口顶部拖动移动位置
- **调整大小** - 拖拽窗口右下角 ⇲ 图标调整大小
- **月 / 周** - 切换月历网格 / 周计划视图
- **+** - 添加日程
- **🔍** - 搜索日程（跨月搜索历史和未来日程）
- **⟳** - 刷新日程
- **📤** - 导出当前范围日程到 Excel
- **📌/📍** - 切换置顶（图标区分状态）
- **⚙** - 打开设置
- **◐** - 切换深色/浅色主题
- **✕** - 隐藏到系统托盘

### 月历网格 / 周计划

- 每个日期格最多显示 3 条日程，超出显示"+N更多"
- 点击日程条 → 查看日程详情
- 点击"+N更多" → 查看当日全部日程列表，点击列表中日程查看详情
- 拖动日程卡片到其他日期格 / 其他周列 → 改期并写回飞书
- 鼠标悬停日期格 → 变色高亮强调
- 全天事件显示"全天"标记；重复事件显示 ♻ 标记
- 今天用蓝色圆圈标记
- 点击日期格空白处 → 快速添加该日日程

### 搜索功能

- 点击 🔍 按钮打开搜索对话框
- 自动加载过去12个月至未来3个月的所有日程
- 输入关键词实时搜索日程标题、描述、发起人
- 点击搜索结果自动跳转到该日程所在月份，并弹出当日日程列表

### 设置面板

- **登录飞书账号** - 打开应用内登录窗口（扫码 / 网页授权，device flow）
- **开机启动** - 开关开机自动运行（Windows 写注册表，macOS 写 LaunchAgent）
- **自动刷新间隔** - 设置日程自动刷新频率（60-3600秒）
- **窗口透明度** - 调整窗口透明度（50%-100%）

## 项目结构

```
FeishuCalendarDesktop/
├── main.py                # 程序入口，系统托盘
├── main_window.py         # 主窗口（月/周视图切换、刷新/错误重试/设置/增删/拖拽改期/持久化）
├── month_view.py          # 月历网格视图组件
├── week_view.py           # 周计划视图组件（weektodo 风格 7 列）
├── widgets.py             # 共享小组件：日期徽标、可点击标签、紧凑日程标签（拖拽源）、日格（放置目标）
├── models_event.py        # 事件模型：时间解析、重复展开、Markdown→HTML、颜色/子任务工具
├── event_card.py          # 日程卡片组件（颜色条 / ♻ 徽标 / 拖拽源）
├── day_detail_dialog.py   # 当日详情对话框
├── search_dialog.py       # 搜索对话框
├── add_event_dialog.py    # 添加日程对话框（颜色 + 重复规则）
├── event_detail_dialog.py # 日程详情对话框（Markdown / 子任务 / 颜色 / 重复）
├── login_dialog.py        # 应用内扫码/网页登录（lark-cli device flow）
├── lark_cli.py            # lark-cli 同步封装（备用）
├── lark_cli_async.py      # lark-cli 异步封装（QProcess；Windows 优先 node 直调，避免 cmd/PowerShell 拆解参数）
├── settings_dialog.py     # 设置对话框（开机启动跨平台分发）
├── export_dialog.py       # 导出日程到 Excel
├── utils.py               # 共享的日期范围计算与日程排序工具
├── config.py              # 配置管理（macOS 配置存放在 ~/Library/Application Support）
├── styles.py              # 主题样式（深色/浅色 + 周视图/切换按钮/拖放高亮）
├── requirements.txt       # Python 依赖
├── config.example.json    # 配置文件示例
├── 启动飞书日程.bat        # Windows 启动脚本
├── 启动飞书日程.command    # macOS 启动脚本
└── build_macos.sh         # macOS PyInstaller 打包脚本
```

> **架构约定**：飞书读写能力集中在 `lark_cli.py` / `lark_cli_async.py`（通过 QProcess 调 node 版 `lark-cli`），重构只改动 UI 层；新增的拖拽改期、颜色、重复、子任务全部复用既有读写接口，不改变与飞书的数据通路。

## 配置文件

首次运行后自动生成 `config.json`：
- Windows：EXE 同目录
- macOS：`~/Library/Application Support/FeishuCalendar/config.json`
- 源码运行：脚本同目录

```json
{
  "window_x": 100,
  "window_y": 100,
  "window_width": 440,
  "window_height": 640,
  "auto_refresh_interval": 300,
  "theme": "dark",
  "opacity": 0.95,
  "pin_to_top": true,
  "calendar_id": "primary",
  "view_mode": "month",
  "event_colors": {},
  "auto_start": false
}
```

> `config.json` 已在 `.gitignore` 中排除，不会上传个人配置。
<img width="1006" height="714" alt="image" src="https://github.com/user-attachments/assets/c580b150-df0c-449b-bded-02fb96217853" />

## 隐私说明

- 本项目不存储任何飞书账号凭据
- lark-cli 授权信息由 lark-cli 独立管理
- 所有日程数据通过 API 实时获取，不在本地持久化

## 技术栈

- **Python 3.10+** + **PySide6 (Qt6)** - 桌面 GUI 框架
- **lark-cli** - 飞书 CLI 工具（可选）
- **飞书开放平台 API** - 直接 REST API 调用（可选）
- **PyInstaller** - 打包为独立 EXE（Windows） / .app（macOS）

## 开发笔记

### Windows 上的关键技术要点

1. **lark-cli 是 .CMD 文件** - QProcess 无法直接执行，需通过 `powershell.exe` 调用
2. **PowerShell `&` 运算符** - 路径含空格时必须用 `&` 前缀
3. **`self.event` 陷阱** - 在 QObject 子类中不能使用 `self.event` 属性名，会覆盖 `QObject.event()` 虚方法导致 C++ 段错误
4. **PyInstaller 打包** - 需使用安装了 PySide6 的同一 Python 环境运行 PyInstaller，所有本地 .py 模块需加入 `--hidden-import`
5. **EXE 配置路径** - 打包后需用 `sys.frozen` 判断并使用 `sys.executable` 目录而非 `__file__` 目录
6. **lark-cli scope 授权** - `--recommend` 不含 `calendar:calendar.event:read`，需用 `--scope` 参数单独指定
7. **Python 字符串转义** - 在 setHtml 字符串中使用 `\\"` 会导致 SyntaxError，应改用字符串拼接

### macOS 上的关键技术要点

1. **lark-cli 直接调用** - macOS 上 lark-cli 是带 shebang 的可执行脚本，QProcess 可直接 `process.start(bin, args)`，无需 PowerShell 中转
2. **`creationflags` 仅 Windows 支持** - `subprocess.run` 在 macOS 上不接受 `creationflags`，需用 `sys.platform == "win32"` 条件包裹
3. **.app 内目录只读** - PyInstaller 打包的 .app bundle 内 `Contents/MacOS/` 不可写，配置文件改存 `~/Library/Application Support/FeishuCalendar/`
4. **开机启动用 LaunchAgent** - 写 `~/Library/LaunchAgents/FeishuCalendarDesktop.plist`，配合 `launchctl load/unload`
5. **字体回退** - `QFont("Segoe UI")` 在 macOS 不存在会触发字体回退警告，用 `setFamilies([...])` 提供跨平台候选
6. **首次启动 Gatekeeper** - 未签名 .app 双击会被拦，需右键 → 打开，或在终端 `xattr -dr com.apple.quarantine 飞书日程.app`

## License

[MIT](LICENSE)
