"""仓库卫生：门禁与发版脚本里那些「看着对、实际不生效」的地方。

不是产品代码，但出错都是静默的——覆盖率规则放宽会让门禁失真，
签名校验不退出会打出一个打不开的包，版本号写错会让发版基线看歪。
"""

from pathlib import Path

from __version__ import APP_VERSION

ROOT = Path(__file__).resolve().parent.parent

# 本文件自身含有 "... " 之类的字面量，扫描时按行看即可


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


def test_agents_md_documents_current_version():
    """版本真源说明必须与实际 APP_VERSION 一致，否则发版会照着旧基线 bump。"""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert f"当前 `{APP_VERSION}`" in text
