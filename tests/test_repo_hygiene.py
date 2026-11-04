"""仓库卫生：门禁与发版脚本里那些「看着对、实际不生效」的地方。

不是产品代码，但出错都是静默的——覆盖率规则放宽会让门禁失真，
签名校验不退出会打出一个打不开的包，版本号写错会让发版基线看歪。
"""

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# 本文件自身含有 "... " 之类的字面量，扫描时按行看即可

# ``https://token@host/...`` 与 ``https://user:token@host/...`` 都算内嵌凭据
_CREDENTIAL_IN_URL = re.compile(r"://[^/\s@]+@")
# 只认各家明确带前缀的长令牌，避免把文档里的示例字符串误判成泄漏
_TOKEN_PATTERNS = re.compile(
    r"gh[pousr]_[A-Za-z0-9]{30,}"
    r"|github_pat_[A-Za-z0-9_]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
    ).stdout


def _require_git_checkout() -> None:
    if shutil.which("git") is None or not (ROOT / ".git").exists():
        pytest.skip("需要 git 工作区")


def _require_local_checkout() -> None:
    """CI 的 actions/checkout 自己会往 URL 里塞凭据，那边不适用 remote 这条规则。"""
    _require_git_checkout()
    if os.environ.get("GITHUB_ACTIONS"):
        pytest.skip("CI checkout 的 remote URL 自带凭据，本机规则不适用")


def test_remote_urls_carry_no_credentials():
    """把 token 拼进 remote URL，等于把它明文摊在 ``.git/config`` 里。

    这枚 token 是 ``gho_`` 开头的 OAuth 令牌，和 ``gh`` 自己存在钥匙串里的是同一枚：
    读 ``.git/config`` 的人（备份、同步盘、贴日志）就拿到了仓库写权限。
    正确做法是干净 URL + 凭据助手（``gh auth git-credential``）。
    """
    _require_local_checkout()
    remotes = _git("remote").split()
    assert remotes, "仓库没有任何 remote，无从校验"
    for name in remotes:
        for url in _git("remote", "get-url", "--all", name).splitlines():
            # 刻意不用 assert：pytest 的断言内省会原样打印 url，等于把令牌又抄进日志
            if _CREDENTIAL_IN_URL.search(url):
                raise AssertionError(
                    f"remote {name} 的地址内嵌了凭据："
                    f"{_CREDENTIAL_IN_URL.sub('://***@', url)}\n"
                    f"改成干净地址：git remote set-url {name} "
                    "https://github.com/<owner>/<repo>.git"
                )


def test_tracked_files_hold_no_hardcoded_tokens():
    """令牌一旦进了提交就不再是本地问题——历史、fork、镜像全都跟着走。"""
    _require_git_checkout()
    offenders = []
    for rel in _git("ls-files").splitlines():
        path = ROOT / rel
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue  # 二进制、软链、读不到的一律跳过
        if _TOKEN_PATTERNS.search(text):
            offenders.append(rel)
    assert not offenders, f"这些被跟踪的文件里写死了令牌：{offenders}"


def test_coveragerc_only_excludes_bare_ellipsis():
    r"""``\.\.\.`` 无锚点，会把所有含 ``...`` 的行排除出覆盖率统计。

    那些行包括 ``"正在加载日程数据..."`` 这类字符串，排除后覆盖率虚高，
    ``--cov-fail-under`` 门禁就跟着失真。
    """
    text = (ROOT / ".coveragerc").read_text(encoding="utf-8")
    assert r"^\s*\.\.\.\s*$" in text


def test_build_script_exits_on_codesign_failure():
    """codesign 校验写在 ``&&`` 列表里，``set -e`` 拦不住失败。"""
    text = (ROOT / "build_macos.sh").read_text(encoding="utf-8")
    # 注释里也提到了 codesign --verify，用带 if ! 的完整锚点定位真正的校验
    assert "if ! codesign --verify" in text
    tail = text.split("if ! codesign --verify")[1]
    assert "exit 1" in tail[:300]


def test_agents_md_points_at_version_source_without_hardcoding():
    """文档里写死版本号必然过时——这是它当初停在 2.9.0 的根本原因。

    所以这里不比对具体数字（那样每次 bump 都要改一次测试），
    而是要求：指向 __version__.py，且不出现「当前 `x.y.z`」这种写法。
    """
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "__version__.py" in text
    assert "APP_VERSION" in text
    assert not re.search(r"当前 `\d+\.\d+\.\d+`", text)
