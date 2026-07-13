# 飞书日程桌面助手 (FeishuCalendarDesktop)

在 Windows / macOS 桌面显示飞书日历日程的月历网格视图，支持添加、删除、查看日程。

参考 [PaperTodo](https://github.com/snownico0722/PaperTodo) 的设计理念，支持 lark-cli 和飞书开放平台 API 两种方式对接飞书日历。

## 功能

- **月历网格视图** - 整月日程一目了然，每个日期格内直接显示日程
- **日程预览** - 格内显示时间和部分标题，放不下自动截断，悬停查看完整标题
- **当日详情** - 点击"+N更多"查看某天全部日程列表，点击日程查看详情
- **日程详情** - 点击日程查看完整信息（时间、组织者、会议链接等）
- **搜索功能** - 关键词搜索过去12个月至未来3个月的所有日程，支持标题/描述/发起人搜索
- **鼠标悬停高亮** - 鼠标移到日期格上自动变色强调
- **添加/删除日程** - 通过表单创建或一键删除日程
- **可调节窗口** - 拖拽右下角调整窗口大小，尺寸自动保存
- **置顶切换** - 📌置顶 / 📍不置顶，图标一目了然
- **今天高亮** - 当天日期用蓝色圆圈标记
- **设置面板** - 配置飞书应用凭证、开机启动、透明度、刷新间隔
- **双模式认证** - 支持 lark-cli 用户授权 或 飞书 App ID/Secret 直接 API 调用
- **开机启动** - 可设置开机自动运行
- **系统托盘** - 后台运行，托盘菜单快捷操作
- **主题切换** - 深色 / 浅色主题
- **自动刷新** - 定时自动同步最新日程
- **授权后自动刷新** - 检测到授权错误时自动重试获取日程
- **错误信息可复制** - 错误提示支持选中和复制，方便排查问题
- **导出日程** - 一键导出当月日程到 Excel

## 两种认证方式

### 方式一：lark-cli 用户授权（推荐个人使用）

```bash
npm install -g @larksuite/cli
lark-cli config init
lark-cli auth login --scope "calendar:calendar.event:read" --scope "calendar:calendar:read"
```

> **注意：** `--recommend` 不包含日历日程读取权限，必须使用上面的 `--scope` 参数明确指定。

### 方式二：飞书应用凭证（推荐企业/团队部署）

1. 在[飞书开放平台](https://open.feishu.cn/)创建企业自建应用
2. 开启日历权限（`calendar:calendar`、`calendar:calendar:readonly`）
3. 在应用设置中填入 App ID 和 App Secret

配置后无需安装 lark-cli，直接通过飞书 API 获取日程。

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
  --hidden-import feishu_api \
  --hidden-import calendar_widget \
  --hidden-import event_card \
  --hidden-import add_event_dialog \
  --hidden-import event_detail_dialog \
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
- **+** - 添加日程
- **🔍** - 搜索日程（跨月搜索历史和未来日程）
- **⟳** - 刷新日程
- **📤** - 导出当月日程到 Excel
- **📌/📍** - 切换置顶（图标区分状态）
- **⚙** - 打开设置
- **◐** - 切换深色/浅色主题
- **✕** - 隐藏到系统托盘

### 月历网格

- 每个日期格最多显示 3 条日程，超出显示"+N更多"
- 点击日程条 → 查看日程详情
- 点击"+N更多" → 查看当日全部日程列表，点击列表中日程查看详情
- 鼠标悬停日期格 → 变色高亮强调
- 全天事件显示"全天"标记
- 今天用蓝色圆圈标记
- 点击日期格空白处 → 快速添加该日日程

### 搜索功能

- 点击 🔍 按钮打开搜索对话框
- 自动加载过去12个月至未来3个月的所有日程
- 输入关键词实时搜索日程标题、描述、发起人
- 点击搜索结果自动跳转到该日程所在月份，并弹出当日日程列表

### 设置面板

- **飞书应用凭证** - 配置 App ID 和 App Secret（可切换显示/隐藏）
- **清除凭证** - 一键清除凭证，切换到 lark-cli 模式
- **测试连接** - 验证 API 凭证是否有效（结果可复制）
- **开机启动** - 开关开机自动运行（Windows 写注册表，macOS 写 LaunchAgent）
- **自动刷新间隔** - 设置日程自动刷新频率（60-3600秒）
- **窗口透明度** - 调整窗口透明度（50%-100%）

## 项目结构

```
FeishuCalendarDesktop/
├── main.py                # 程序入口，系统托盘
├── calendar_widget.py     # 月历网格主窗口、搜索对话框、当日详情对话框
├── feishu_api.py          # 飞书 API 直接调用（App ID/Secret 模式）
├── lark_cli.py            # lark-cli 同步封装（备用）
├── lark_cli_async.py      # lark-cli 异步封装（QProcess；Windows 走 PowerShell，macOS 直接调用）
├── event_card.py          # 日程卡片组件
├── add_event_dialog.py    # 添加日程对话框
├── event_detail_dialog.py # 日程详情对话框
├── settings_dialog.py     # 设置对话框（开机启动跨平台分发）
├── export_dialog.py       # 导出日程到 Excel
├── config.py              # 配置管理（macOS 配置存放在 ~/Library/Application Support）
├── styles.py              # 主题样式（深色/浅色）
├── requirements.txt       # Python 依赖
├── config.example.json    # 配置文件示例
├── 启动飞书日程.bat        # Windows 启动脚本
├── 启动飞书日程.command    # macOS 启动脚本
└── build_macos.sh         # macOS PyInstaller 打包脚本
```

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
  "app_id": "",
  "app_secret": "",
  "auto_start": false
}
```

> `config.json` 已在 `.gitignore` 中排除，不会上传个人配置。
<img width="1006" height="714" alt="image" src="https://github.com/user-attachments/assets/c580b150-df0c-449b-bded-02fb96217853" />

## 隐私说明

- 本项目不存储任何飞书账号凭据
- App ID 和 App Secret 保存在本地 `config.json` 中，已被 `.gitignore` 排除
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
