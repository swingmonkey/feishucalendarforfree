# 飞书日程桌面助手 (FeishuCalendarDesktop)

在 Windows 桌面显示飞书日历日程的月历网格视图，支持添加、删除、查看日程。

参考 [PaperTodo](https://github.com/snownico0722/PaperTodo) 的设计理念，使用 [lark-cli](https://github.com/larksuite/cli) 对接飞书日历 API。

## 功能

- **月历网格视图** - 整月日程一目了然，每个日期格内直接显示日程
- **日程预览** - 格内显示时间和部分标题，放不下自动截断，悬停查看完整标题
- **当日详情** - 点击"+N更多"查看某天全部日程列表
- **日程详情** - 点击日程查看完整信息（时间、组织者、会议链接等）
- **添加日程** - 通过表单创建新的飞书日历日程
- **删除日程** - 一键删除不需要的日程
- **可调节窗口** - 拖拽右下角调整窗口大小，尺寸自动保存
- **自动刷新** - 定时自动同步最新日程
- **系统托盘** - 后台运行，托盘菜单快捷操作
- **主题切换** - 深色 / 浅色主题
- **窗口拖动** - 拖拽窗口顶部移动位置，位置自动保存

## 截图

<!-- 可在此处添加截图 -->

## 技术栈

- **Python 3.10+** + **PySide6 (Qt6)** - 桌面 GUI 框架
- **lark-cli** - 飞书官方命令行工具，通过 QProcess 异步调用
- **QProcess + PowerShell** - 在 Windows 上异步执行 lark-cli 命令，不阻塞 UI

## 前置要求

1. **Node.js** - 用于安装 lark-cli
2. **Python 3.10+** - 运行环境
3. **lark-cli** - 飞书 CLI 工具

## 安装

### 1. 安装 lark-cli

```bash
npm install -g @larksuite/cli
```

### 2. 配置飞书授权

```bash
lark-cli config init
lark-cli auth login --recommend
```

按提示在浏览器中完成飞书扫码授权。

### 3. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

或双击 `启动飞书日程.bat`。

## 使用说明

### 桌面窗口

- 窗口默认置顶显示在桌面右上角
- **拖动** - 按住窗口顶部拖动移动位置
- **调整大小** - 拖拽窗口右下角 ⇲ 图标调整大小
- **+** - 打开添加日程对话框
- **⟳** - 手动刷新日程
- **📌** - 切换窗口置顶
- **◐** - 切换深色/浅色主题
- **✕** - 隐藏到系统托盘

### 月份导航

- **‹** - 上个月
- **›** - 下个月
- **今天** - 回到本月

### 月历网格

- 每个日期格最多显示 3 条日程，超出显示"+N更多"
- 点击日程条 → 查看日程详情
- 点击"+N更多" → 查看当日全部日程列表
- 全天事件显示"全天"标记
- 今天高亮显示（蓝色边框）

### 系统托盘

- **单击托盘图标** - 显示/隐藏窗口
- **右键托盘图标** - 打开菜单（显示、隐藏、刷新、添加、关于、退出）

## 项目结构

```
FeishuCalendarDesktop/
├── main.py                # 程序入口，系统托盘
├── calendar_widget.py     # 月历网格主窗口
├── lark_cli.py            # lark-cli 同步封装（备用）
├── lark_cli_async.py      # lark-cli 异步封装（QProcess + PowerShell）
├── event_card.py          # 日程卡片组件
├── add_event_dialog.py    # 添加日程对话框
├── event_detail_dialog.py # 日程详情对话框
├── config.py              # 配置管理
├── styles.py              # 主题样式（深色/浅色）
├── requirements.txt       # Python 依赖
├── config.example.json    # 配置文件示例
└── 启动飞书日程.bat        # Windows 启动脚本
```

## lark-cli 命令映射

| 功能 | lark-cli 命令 |
|---|---|
| 查看日程 | `lark-cli calendar +agenda --start <start> --end <end> --format json` |
| 创建日程 | `lark-cli calendar +create --summary <title> --start <start> --end <end> --format json` |
| 删除日程 | `lark-cli calendar events delete --calendar-id <cal_id> --event-id <event_id> --format json` |

## 配置文件

首次运行后自动生成 `config.json`：

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
  "calendar_id": "primary"
}
```

> `config.json` 已在 `.gitignore` 中排除，不会上传个人配置。
<img width="1006" height="714" alt="image" src="https://github.com/user-attachments/assets/c580b150-df0c-449b-bded-02fb96217853" />

## 隐私说明

- 本项目不存储任何飞书账号凭据，授权信息由 lark-cli 管理
- `config.json` 仅保存窗口位置和主题偏好，已被 `.gitignore` 排除
- 所有日程数据通过 lark-cli 实时获取，不在本地持久化

## 开发笔记

### Windows 上的关键技术要点

1. **lark-cli 是 .CMD 文件** - QProcess 无法直接执行，需通过 `powershell.exe` 调用
2. **PowerShell `&` 运算符** - lark-cli 路径含空格时，必须用 `&` 前缀使 PowerShell 将其视为命令而非字符串
3. **UTF-8 编码** - PowerShell 默认编码可能导致中文乱码，需设置 `[Console]::OutputEncoding`
4. **`self.event` 陷阱** - 在 QObject 子类中不能使用 `self.event` 属性名，它会覆盖 `QObject.event()` 虚方法导致 C++ 段错误

## License

[MIT](LICENSE)
