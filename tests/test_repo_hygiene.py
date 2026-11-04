"""仓库卫生：门禁与发版脚本里那些「看着对、实际不生效」的地方。

不是产品代码，但出错都是静默的——覆盖率规则放宽会让门禁失真，
签名校验不退出会打出一个打不开的包，版本号写错会让发版基线看歪。
"""

import re
from pathlib import Path

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


def test_agents_md_points_at_version_source_without_hardcoding():
    """文档里写死版本号必然过时——这是它当初停在 2.9.0 的根本原因。

    所以这里不比对具体数字（那样每次 bump 都要改一次测试），
    而是要求：指向 __version__.py，且不出现「当前 `x.y.z`」这种写法。
    """
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "__version__.py" in text
    assert "APP_VERSION" in text
    assert not re.search(r"当前 `\d+\.\d+\.\d+`", text)
