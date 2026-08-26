# Windows PyInstaller 打包脚本 — 生成 dist\飞书日程.exe
# 使用方法：双击 build_windows.bat，或命令行执行：
#   powershell -NoProfile -ExecutionPolicy Bypass -File build_windows.ps1
# 可用环境变量 PY 指定 Python：  $env:PY = "C:\path\to\python.exe"
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

# 产物名：默认中文名；CI 环境可设 FC_APP_NAME 覆盖为 ASCII 名，
# 避免 GitHub Actions 等链路吞掉非 ASCII 字符导致附件命名错误
if ($env:FC_APP_NAME) { $AppName = $env:FC_APP_NAME } else { $AppName = "飞书日程" }

Write-Host "=== 飞书日程 Windows 打包 ===" -ForegroundColor Cyan

# ── 选择 Python ──
# 优先级：环境变量 PY > PATH 中的 python > py 启动器(-3)
$candidates = @()
if ($env:PY -and (Test-Path $env:PY)) { $candidates += , @($env:PY) }
$c = Get-Command python -ErrorAction SilentlyContinue
if ($c) { $candidates += , @($c.Source) }
$c = Get-Command py -ErrorAction SilentlyContinue
if ($c) { $candidates += , @($c.Source, "-3") }

$py = $null
foreach ($cand in $candidates) {
    $exe = $cand[0]
    $pre = @()
    if ($cand.Count -gt 1) { $pre = $cand[1..($cand.Count - 1)] }
    try {
        $ver = & $exe @pre -c "import sys; print('%d%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ver -and [int]$ver -ge 310) {
            $py = @{ Exe = $exe; Pre = $pre }
            break
        }
    } catch { continue }
}
if (-not $py) {
    Write-Host "[错误] 未找到 Python 3.10+，请安装后勾选 Add to PATH。" -ForegroundColor Red
    exit 1
}
$ver = & $py.Exe @($py.Pre) --version
Write-Host "使用 Python：$ver"

# ── 依赖与 PyInstaller ──
& $py.Exe @($py.Pre) -c "import PySide6, openpyxl" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "未检测到依赖，正在安装 requirements.txt ..."
    & $py.Exe @($py.Pre) -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Write-Host "[错误] 依赖安装失败。" -ForegroundColor Red; exit 1 }
}
& $py.Exe @($py.Pre) -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "正在安装 pyinstaller ..."
    & $py.Exe @($py.Pre) -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) { Write-Host "[错误] pyinstaller 安装失败。" -ForegroundColor Red; exit 1 }
}

# ── 清理上次构建产物 ──
Remove-Item -LiteralPath "build", "dist", "$AppName.spec" -Recurse -Force -ErrorAction SilentlyContinue

# ── 打包参数 ──
$args = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", $AppName,
    "--add-data", "assets;assets",
    "--paths", ".",
    "--hidden-import", "openpyxl",
    "--hidden-import", "config",
    "--hidden-import", "styles",
    "--hidden-import", "lark_cli",
    "--hidden-import", "lark_cli_async",
    "--hidden-import", "models_event",
    "--hidden-import", "widgets",
    "--hidden-import", "month_view",
    "--hidden-import", "week_view",
    "--hidden-import", "main_window",
    "--hidden-import", "event_card",
    "--hidden-import", "add_event_dialog",
    "--hidden-import", "event_detail_dialog",
    "--hidden-import", "day_detail_dialog",
    "--hidden-import", "search_dialog",
    "--hidden-import", "settings_dialog",
    "--hidden-import", "export_dialog",
    "--hidden-import", "updater",
    "--hidden-import", "update_dialog",
    "--hidden-import", "__version__",
    "main.py"
)
if (Test-Path "assets\icon.ico") { $args += @("--icon", "assets\icon.ico") }

& $py.Exe @($py.Pre) @args
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n[错误] 打包失败，请检查上方日志。" -ForegroundColor Red
    exit 1
}

$out = Join-Path $PSScriptRoot "dist\$AppName.exe"
Write-Host ""
Write-Host "构建完成：$out" -ForegroundColor Green
Get-ChildItem "dist" | Format-Table Name, Length -AutoSize
