#!/usr/bin/env python3
"""本地 CI —— 与线上 workflow 同源的门禁，跑在推送之前。

为什么要有这个东西：覆盖率门禁（``--cov-fail-under=70``）推不进仓库，
推送凭据缺 ``workflow`` 权限。既然线上跑不了，就让它在这里跑——同一套
阈值、同一套排除规则、同一条命令，而不是靠人记得手动敲四行。

和 ``.github/workflows/ci.yml`` 的对应关系：

    ruff check .                    →  步骤 2
    compileall -q . -x ...          →  步骤 3
    pytest -q（QT_QPA_PLATFORM=offscreen）  →  步骤 4
    --cov-fail-under=70             →  步骤 4（线上缺失的那条，在这里补上）

刻意不做的事：不装依赖、不改虚拟环境。环境不对就报错退出，让人自己修——
本地 CI 的职责是判断，不是自愈。

用法::

    python3 tools/ci.py                  # 全量门禁
    python3 tools/ci.py --fast           # 跳过覆盖率统计（约快 3 秒）
    python3 tools/ci.py --build          # 额外打一次本机安装包
    python3 tools/ci.py --install-hook   # 装 pre-push 钩子，推送前自动跑
    python3 tools/ci.py --uninstall-hook # 卸掉钩子
    python3 tools/ci.py --python PATH    # 指定解释器

退出码：0 全过，1 有门禁失败，2 环境不满足。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = ROOT / ".git" / "hooks" / "pre-push"
HOOK_MARKER = "# feishu-calendar local CI gate"

# 与 .github/workflows/ci.yml 的 compileall 排除规则一致，另外补上本地
# 才会出现的临时目录（pytest 的 basetemp、发版核对的下载目录）。
COMPILE_EXCLUDE = r"(^|/)(\.git|\.venv|venv|dist|build|\.pytest_tmp|\.release_check)/"

PYTEST_FAILURE = re.compile(r"\b\d+ (failed|error)")
PYTEST_PASSED = re.compile(r"\b(\d+) passed")
COV_TOTAL = re.compile(r"^TOTAL\s+.*?(\d+(?:\.\d+)?)%", re.MULTILINE)

# coverage 报的残留路径警告会淹没真正的失败原因，逐行剔掉。
_NOISE = re.compile(r"CoverageWarning|couldnt-parse|coverage\._warn")


def summarize(output: str, limit: int = 30) -> str:
    """Keep the lines that explain a failure, drop coverage's path whining."""
    kept = [
        line for line in output.splitlines()
        if line.strip() and not _NOISE.search(line)
    ]
    return "\n".join(kept[-limit:])


class StepFailed(Exception):
    pass


# ── 环境 ─────────────────────────────────────────────────────────────────────


def pick_python(explicit: str | None) -> Path:
    """Resolve the interpreter used for every step.

    Order matters: an explicit ``--python`` wins, then ``$CI_PYTHON``, then the
    project venv, then whatever is running this script. The venv preference is
    what stops the "python3 has no pytest" class of failure — this repo's
    system Python and the venv are different versions with different packages.
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.environ.get("CI_PYTHON"):
        return Path(os.environ["CI_PYTHON"]).expanduser().resolve()
    for candidate in (
        ROOT / ".venv" / "bin" / "python",
        ROOT / ".venv" / "Scripts" / "python.exe",
    ):
        if candidate.exists():
            return candidate
    return Path(sys.executable)


def check_environment(py: Path) -> None:
    if not py.exists():
        raise SystemExit(f"找不到解释器：{py}")
    probe = "import sys; print('%d.%d' % sys.version_info[:2])"
    got = subprocess.run([str(py), "-c", probe], capture_output=True, text=True)
    if got.returncode != 0:
        raise SystemExit(f"解释器无法运行：{py}\n{got.stderr.strip()}")
    version = tuple(int(x) for x in got.stdout.strip().split("."))
    if version < (3, 10):
        raise SystemExit(f"需要 Python 3.10+，当前是 {got.stdout.strip()}")

    missing = []
    for module, label in (
        ("pytest", "pytest"),
        ("pytest_cov", "pytest-cov"),
        ("ruff", "ruff"),
        ("PySide6", "PySide6"),
    ):
        probe = subprocess.run(
            [str(py), "-c", f"import {module}"], capture_output=True, text=True
        )
        if probe.returncode != 0:
            missing.append(label)
    if missing:
        raise SystemExit(
            f"{py} 缺少依赖：{', '.join(missing)}\n"
            f"请先执行：{py} -m pip install -r requirements.txt -r requirements-dev.txt"
        )


# ── 步骤 ─────────────────────────────────────────────────────────────────────


def _base_env() -> dict[str, str]:
    env = dict(os.environ)
    # 与线上一致：没有显示服务器，Qt 必须走 offscreen 才能建窗口。
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    return env


def step_lint(py: Path) -> str:
    proc = subprocess.run(
        [str(py), "-m", "ruff", "check", "."], cwd=ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise StepFailed(proc.stdout + proc.stderr)
    return "ruff 无告警"


def step_compile(py: Path) -> str:
    proc = subprocess.run(
        [str(py), "-m", "compileall", "-q", ".", "-x", COMPILE_EXCLUDE],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise StepFailed(proc.stdout + proc.stderr)
    return "全部源文件可编译"


def step_tests(py: Path, *, coverage: bool, min_cov: int) -> str:
    """Run pytest and separate three failure modes the CI conflates.

    1. Real test failures — fail, always.
    2. Coverage below the threshold — fail. This is the gate that could not be
       pushed to GitHub, so it has to be loud here.
    3. Exit code >= 128 with a clean summary — PySide6 occasionally dies during
       process teardown *after* every test passed. The workflow already ignores
       this; we keep the same tolerance but only when the output proves the run
       was clean, never on a bare signal.
    """
    cmd = [str(py), "-m", "pytest", "-q"]
    if coverage:
        cmd += ["--cov=.", "--cov-report=term", f"--cov-fail-under={min_cov}"]
    cmd += ["--basetemp=.pytest_tmp"]

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=_base_env())
    output = proc.stdout + proc.stderr
    tail = output.strip().splitlines()[-1] if output.strip() else "(无输出)"

    failed = PYTEST_FAILURE.search(output)
    passed = PYTEST_PASSED.search(output)
    coverage_short = "Required test coverage of" in output
    cov_match = COV_TOTAL.search(output)
    cov_note = f"，覆盖率 {cov_match.group(1)}%" if cov_match else ""

    if failed:
        raise StepFailed(output)
    if proc.returncode == 0:
        return f"{passed.group(1) if passed else '?'} 例通过{cov_note}"
    if coverage_short:
        raise StepFailed(f"覆盖率低于门槛 {min_cov}%{cov_note}\n{output}")
    if proc.returncode >= 128 and passed:
        print(f"    ! pytest 退出码 {proc.returncode}（PySide6 进程收尾信号），"
              f"但结果干净：{tail}")
        return f"{passed.group(1)} 例通过{cov_note}（收尾信号已忽略）"
    raise StepFailed(output)


def step_build(py: Path) -> str:
    """Build a local installer, matching what the release workflow produces."""
    if sys.platform == "darwin":
        script = ROOT / "build_macos.sh"
        cmd = ["bash", str(script)]
        env = dict(os.environ, FC_APP_NAME="FeishuCalendar", PYTHON=str(py))
    elif sys.platform.startswith("win"):
        script = ROOT / "build_windows.ps1"
        cmd = [
            "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
            "-File", str(script),
        ]
        env = dict(os.environ, FC_APP_NAME="FeishuCalendar")
    else:
        raise StepFailed("--build 只支持 macOS 与 Windows；Linux 上请走线上构建。")

    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise StepFailed(proc.stdout + proc.stderr)
    return "本机安装包已产出（dist/）"


# ── 钩子 ─────────────────────────────────────────────────────────────────────


def install_hook(py: Path) -> None:
    hooks_dir = HOOK_PATH.parent
    if not hooks_dir.exists():
        raise SystemExit(f"{hooks_dir} 不存在，这个目录不是 git 仓库？")
    if HOOK_PATH.exists():
        existing = HOOK_PATH.read_text(encoding="utf-8", errors="replace")
        if HOOK_MARKER not in existing:
            raise SystemExit(
                f"{HOOK_PATH} 已存在且不是本工具生成的，为免覆盖他人的钩子，已停止。"
            )
    script = (
        "#!/bin/sh\n"
        f"{HOOK_MARKER} — 由 tools/ci.py --install-hook 生成\n"
        "# 推送前跑一遍与线上同源的门禁；失败即拦截本次推送。\n"
        f'exec "{py}" "{ROOT / "tools" / "ci.py"}"\n'
    )
    HOOK_PATH.write_text(script, encoding="utf-8")
    HOOK_PATH.chmod(0o755)
    print(f"已安装 pre-push 钩子：{HOOK_PATH}")


def uninstall_hook() -> None:
    if not HOOK_PATH.exists():
        print("没有 pre-push 钩子，无需卸载。")
        return
    if HOOK_MARKER not in HOOK_PATH.read_text(encoding="utf-8", errors="replace"):
        raise SystemExit("钩子不是本工具生成的，未删除。")
    HOOK_PATH.unlink()
    print(f"已删除 pre-push 钩子：{HOOK_PATH}")


# ── 主流程 ───────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="本地 CI 门禁（与 .github/workflows/ci.yml 同源）"
    )
    parser.add_argument("--python", help="指定解释器，默认用 .venv 里的那个")
    parser.add_argument("--fast", action="store_true", help="跳过覆盖率统计")
    parser.add_argument("--min-cov", type=int, default=70, help="覆盖率下限，默认 70")
    parser.add_argument("--build", action="store_true", help="额外打一次本机安装包")
    parser.add_argument("--install-hook", action="store_true", help="安装 pre-push 钩子")
    parser.add_argument("--uninstall-hook", action="store_true", help="卸载 pre-push 钩子")
    parser.add_argument("--quiet", action="store_true", help="只在失败时输出细节")
    args = parser.parse_args(argv)

    py = pick_python(args.python)

    if args.uninstall_hook:
        uninstall_hook()
        return 0
    if args.install_hook:
        check_environment(py)
        install_hook(py)
        return 0

    print(f"本地 CI  ·  {py}")
    print(f"仓库      ·  {ROOT}")
    try:
        check_environment(py)
    except SystemExit as exc:
        print(f"\n环境不满足：{exc}", file=sys.stderr)
        return 2

    steps: list[tuple[str, str]] = [
        ("lint", "ruff check ."),
        ("compile", "compileall 全量语法检查"),
    ]
    if args.fast:
        steps.append(("test", "pytest（不含覆盖率）"))
    else:
        steps.append(("test", f"pytest + 覆盖率门禁 ≥{args.min_cov}%"))
    if args.build:
        steps.append(("build", "打包本机安装包"))

    results: list[tuple[str, bool, str, float]] = []
    failed = False
    for index, (key, label) in enumerate(steps, 1):
        print(f"\n[{index}/{len(steps)}] {label}")
        started = time.time()
        try:
            if key == "lint":
                detail = step_lint(py)
            elif key == "compile":
                detail = step_compile(py)
            elif key == "test":
                detail = step_tests(py, coverage=not args.fast, min_cov=args.min_cov)
            else:
                detail = step_build(py)
            elapsed = time.time() - started
            results.append((label, True, detail, elapsed))
            print(f"    ✓ {detail}  ({elapsed:.1f}s)")
        except StepFailed as exc:
            elapsed = time.time() - started
            results.append((label, False, "失败", elapsed))
            print(f"    ✗ 失败  ({elapsed:.1f}s)")
            body = summarize(str(exc))
            if body:
                if args.quiet:
                    print(f"    {body.splitlines()[0]}")
                else:
                    print("    " + "\n    ".join(body.splitlines()))
            failed = True
            break

    total = sum(item[3] for item in results)
    print("\n" + "─" * 52)
    for label, ok, detail, elapsed in results:
        mark = "PASS" if ok else "FAIL"
        print(f"{mark}  {label:<28} {elapsed:6.1f}s  {detail}")
    if len(results) < len(steps):
        skipped = [label for _, label in steps[len(results):]]
        print(f"SKIP  {' / '.join(skipped)}（前面的步骤已失败）")
    print("─" * 52)
    print(f"{'门禁通过' if not failed else '门禁未通过'} · 累计 {total:.1f}s")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
