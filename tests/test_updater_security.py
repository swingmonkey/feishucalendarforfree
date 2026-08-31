"""Security regression tests for updater archive extraction."""

import zipfile
from pathlib import Path

import pytest

from updater import _safe_extract


def test_safe_extract_rejects_parent_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../../outside.txt", "nope")
    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="unsafe archive path"):
            _safe_extract(zf, str(tmp_path / "out"))


def test_safe_extract_allows_normal_archive(tmp_path):
    archive = tmp_path / "ok.zip"
    out = tmp_path / "out"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("repo-tag/main.py", "print('ok')")
    out.mkdir()
    with zipfile.ZipFile(archive) as zf:
        _safe_extract(zf, str(out))
    assert (out / "repo-tag" / "main.py").read_text() == "print('ok')"
    assert not (Path(tmp_path) / "main.py").exists()
