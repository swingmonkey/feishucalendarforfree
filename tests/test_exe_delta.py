"""exe_delta 的离线回归测试。

用一个「长得像 PyInstaller onefile」的合成 EXE（引导程序 + 成员 + TOC + cookie）
覆盖格式解析、补丁生成、应用与各类拒绝/回退路径；另外在本地存在真实产物时
(v2.1.6 / v2.2.0) 再跑一次字节级往返，那个用例在没有样本时自动跳过。
"""

import hashlib
import struct
import sys

import pytest

import exe_delta as ed
import updater

COOKIE_MAGIC = ed.COOKIE_MAGIC
COOKIE_LEN = ed.COOKIE_LENGTH


def make_exe(stub: bytes, members: list[tuple[str, bytes, str]], flag: int = 1) -> bytes:
    """构造一个结构合法的假 onefile EXE，供测试解析/补丁逻辑。"""
    body = bytearray()
    index = []
    for name, data, typecode in members:
        index.append((name, len(body), len(data), len(data), flag, typecode))
        body += data

    toc = bytearray()
    for name, offset, dlen, ulen, f, typecode in index:
        raw = name.encode("utf-8")
        raw += b"\x00" * ((-len(raw)) % 16)  # 与 PyInstaller 一致按 16 字节对齐
        toc += struct.pack("!IIIIBc", 18 + len(raw), offset, dlen, ulen, f, typecode.encode())
        toc += raw

    archive_len = len(body) + len(toc) + COOKIE_LEN
    cookie = struct.pack(
        "!8sIIII64s",
        COOKIE_MAGIC,
        archive_len,
        len(body),  # TOC 相对归档起点的偏移
        len(toc),
        312,
        b"python312.dll",
    )
    return stub + bytes(body) + bytes(toc) + cookie


STUB = b"MZ" + b"\x90" * 510
QT = b"Qt6Core" * 400
PYZ = b"PYZ-body" * 300
MAIN = b"main-code"


def base_exe():
    return make_exe(STUB, [("PySide6/Qt6Core.dll", QT, "b"), ("PYZ.pyz", PYZ, "z"), ("main", MAIN, "s")])


def target_exe():
    return make_exe(
        STUB + b"\x01",  # 引导程序也变了（真实构建里确实会变）
        [
            ("PySide6/Qt6Core.dll", QT, "b"),
            ("PYZ.pyz", PYZ + b"-changed", "z"),
            ("main", MAIN + b"-v2", "s"),
        ],
    )


# ── 解析 ────────────────────────────────────────────────────────────────────

def test_parse_carchive_recovers_members():
    archive, entries = ed.entries_of(base_exe())
    assert archive.stub == STUB
    assert [e.name for e in entries] == ["PySide6/Qt6Core.dll", "PYZ.pyz", "main"]
    assert archive.member_bytes(entries[0]) == QT


def test_parse_carchive_rejects_plain_file():
    with pytest.raises(ed.DeltaError):
        ed.parse_carchive(b"not an executable at all")


def test_parse_carchive_rejects_truncated_cookie():
    data = base_exe()
    with pytest.raises(ed.DeltaError):
        ed.parse_carchive(data[: len(data) - 10])


# ── 补丁生成 ────────────────────────────────────────────────────────────────

def test_delta_only_carries_changed_members():
    delta = ed.build_delta(base_exe(), target_exe())
    header = ed.read_delta_header(delta)
    assert header["n_changed"] == 2, "只有 PYZ.pyz 与 main 变了，Qt 应复用（引导程序不算成员）"
    names = _changed_names(delta)
    assert "PySide6/Qt6Core.dll" not in names, "未变的大成员不应进补丁"
    assert names == {"PYZ.pyz", "main"}


def _changed_names(delta: bytes) -> set[str]:
    header = ed.read_delta_header(delta)
    pos = ed.DELTA_HEADER_LENGTH + header["stub_len"] + header["toc_len"] + header["cookie_len"]
    out = set()
    for _ in range(header["n_changed"]):
        name_len, dlen, _u, _f, _t = struct.unpack(
            ed.DELTA_MEMBER_FORMAT, delta[pos : pos + ed.DELTA_MEMBER_HEADER_LENGTH]
        )
        pos += ed.DELTA_MEMBER_HEADER_LENGTH
        out.add(delta[pos : pos + name_len].decode())
        pos += name_len + dlen
    return out


def test_delta_is_much_smaller_than_full_when_payload_unchanged():
    big = b"X" * (4 * 1024 * 1024)
    base = make_exe(STUB, [("huge.dll", big, "b"), ("PYZ.pyz", PYZ, "z")])
    target = make_exe(STUB + b"\x02", [("huge.dll", big, "b"), ("PYZ.pyz", PYZ + b"x", "z")])
    delta = ed.build_delta(base, target)
    assert len(delta) < len(target) / 10, "大成员未变时补丁应远小于全量"


# ── 补丁应用 ────────────────────────────────────────────────────────────────

def test_apply_delta_reproduces_target_byte_for_byte():
    base, target = base_exe(), target_exe()
    out = ed.apply_delta(base, ed.build_delta(base, target))
    assert out == target
    assert hashlib.sha256(out).hexdigest() == hashlib.sha256(target).hexdigest()


def test_apply_delta_with_no_changes_still_exact():
    base = base_exe()
    out = ed.apply_delta(base, ed.build_delta(base, base))
    assert out == base


def test_apply_delta_records_target_size_and_hash():
    base, target = base_exe(), target_exe()
    header = ed.read_delta_header(ed.build_delta(base, target))
    assert header["target_size"] == len(target)
    assert header["base_sha256"] == hashlib.sha256(base).hexdigest()
    assert header["target_sha256_prefix"] == hashlib.sha256(target).hexdigest()[:32]


def test_apply_delta_handles_added_and_removed_members():
    base = make_exe(STUB, [("keep.dll", QT, "b"), ("drop.dll", MAIN, "b")])
    target = make_exe(STUB, [("keep.dll", QT, "b"), ("new.dll", PYZ, "b")])
    out = ed.apply_delta(base, ed.build_delta(base, target))
    assert out == target
    names = {e.name for e in ed.parse_toc_bytes(ed.parse_carchive(out).toc_bytes)}
    assert "new.dll" in names and "drop.dll" not in names


# ── 拒绝 / 回退 ─────────────────────────────────────────────────────────────

def test_apply_delta_rejects_wrong_base():
    base, target = base_exe(), target_exe()
    delta = ed.build_delta(base, target)
    with pytest.raises(ed.DeltaError, match="基座不匹配"):
        ed.apply_delta(target, delta)  # 拿目标当基座


def test_apply_delta_rejects_truncated_patch():
    base, target = base_exe(), target_exe()
    delta = ed.build_delta(base, target)
    for cut in (10, len(delta) // 3, len(delta) - 5):
        with pytest.raises(ed.DeltaError):
            ed.apply_delta(base, delta[:cut])


def test_apply_delta_rejects_bad_magic_and_version():
    base, target = base_exe(), target_exe()
    delta = bytearray(ed.build_delta(base, target))
    bad = bytearray(delta)
    bad[0:8] = b"XXXXXXXX"
    with pytest.raises(ed.DeltaError, match="魔数"):
        ed.apply_delta(base, bytes(bad))
    bad2 = bytearray(delta)
    bad2[8:12] = struct.pack("!I", 99)
    with pytest.raises(ed.DeltaError, match="版本"):
        ed.apply_delta(base, bytes(bad2))


def test_apply_delta_rejects_non_exe_base():
    delta = ed.build_delta(base_exe(), target_exe())
    with pytest.raises(ed.DeltaError):
        ed.apply_delta(b"MZ not really an exe", delta)


def test_delta_stats_reports_ratio():
    delta = ed.build_delta(base_exe(), target_exe())
    stats = ed.delta_stats(delta)
    assert stats["delta_bytes"] == len(delta)
    assert 0 < stats["ratio"] < 1


# ── 与 updater 的接线 ───────────────────────────────────────────────────────

def _win_frozen(monkeypatch, tmp_path, base_bytes):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    exe = tmp_path / "FeishuCalendar.exe"
    exe.write_bytes(base_bytes)
    monkeypatch.setattr(sys, "executable", str(exe))
    return exe


def _release(delta_bytes=None):
    assets = [{"name": "FeishuCalendar.exe", "browser_download_url": "https://x/FeishuCalendar.exe"}]
    if delta_bytes is not None:
        assets.append({"name": "FeishuCalendar.exe.delta", "browser_download_url": "https://x/d.delta"})
    return {"tag": "v9.9.9", "assets": assets}


def test_find_delta_asset():
    assert updater.find_delta_asset(_release(b"x"))["name"].endswith(".delta")
    assert updater.find_delta_asset(_release()) is None


def test_build_exe_via_delta_writes_verified_file(monkeypatch, tmp_path):
    base, target = base_exe(), target_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    monkeypatch.setattr(updater, "download_bytes", lambda url, timeout=120: ed.build_delta(base, target))
    dest = tmp_path / "out.download"

    ok = updater.build_exe_via_delta(_release(b"x"), str(dest), hashlib.sha256(target).hexdigest())
    assert ok is True
    assert dest.read_bytes() == target


def test_build_exe_via_delta_rejects_when_hash_mismatch(monkeypatch, tmp_path):
    """补丁产出与 SHA256SUMS 不符时必须失败，绝不留下文件。"""
    base, target = base_exe(), target_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    monkeypatch.setattr(updater, "download_bytes", lambda url, timeout=120: ed.build_delta(base, target))
    dest = tmp_path / "out.download"

    ok = updater.build_exe_via_delta(_release(b"x"), str(dest), "0" * 64)
    assert ok is False
    assert not dest.exists(), "校验失败仍留下了文件"


def test_build_exe_via_delta_falls_back_when_no_patch(monkeypatch, tmp_path):
    base = base_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    dest = tmp_path / "out.download"
    assert updater.build_exe_via_delta(_release(), str(dest), "0" * 64) is False


def test_build_exe_via_delta_falls_back_on_corrupt_patch(monkeypatch, tmp_path):
    base = base_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    monkeypatch.setattr(updater, "download_bytes", lambda url, timeout=120: b"garbage-not-a-delta")
    dest = tmp_path / "out.download"
    assert updater.build_exe_via_delta(_release(b"x"), str(dest), "0" * 64) is False
    assert not dest.exists()


def test_build_exe_via_delta_noop_when_not_frozen(monkeypatch, tmp_path):
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert updater.build_exe_via_delta(_release(b"x"), str(tmp_path / "o"), "0" * 64) is False


def test_prepare_pending_update_prefers_delta(monkeypatch, tmp_path):
    """有可用补丁时不应触发全量下载。"""
    base, target = base_exe(), target_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    monkeypatch.setattr(updater, "download_bytes", lambda url, timeout=120: ed.build_delta(base, target))
    monkeypatch.setattr(updater, "download_sha256_sums", lambda rel, timeout=15: {
        "FeishuCalendar.exe": hashlib.sha256(target).hexdigest()
    })
    pending = tmp_path / "app.exe.pending"
    meta = tmp_path / "app.exe.pending.json"
    monkeypatch.setattr(updater, "pending_update_path", lambda: str(pending))
    monkeypatch.setattr(updater, "pending_metadata_path", lambda: str(meta))
    monkeypatch.setattr(
        updater, "download",
        lambda *a, **k: pytest.fail("有增量补丁时不应走全量下载"),
    )

    ok, message = updater.prepare_pending_update(_release(b"x"))
    assert ok is True, message
    assert pending.read_bytes() == target


def test_prepare_pending_update_falls_back_to_full(monkeypatch, tmp_path):
    """补丁不可用时必须自动回退到全量下载（保持原有行为）。"""
    base, target = base_exe(), target_exe()
    _win_frozen(monkeypatch, tmp_path, base)
    monkeypatch.setattr(updater, "download_sha256_sums", lambda rel, timeout=15: {
        "FeishuCalendar.exe": hashlib.sha256(target).hexdigest()
    })
    pending = tmp_path / "app.exe.pending"
    monkeypatch.setattr(updater, "pending_update_path", lambda: str(pending))
    monkeypatch.setattr(updater, "pending_metadata_path", lambda: str(tmp_path / "m.json"))

    def fake_download(url, dest, progress_cb=None, timeout=60):
        with open(dest, "wb") as f:
            f.write(target)

    monkeypatch.setattr(updater, "download", fake_download)

    ok, message = updater.prepare_pending_update(_release(b"x"))  # 补丁存在但内容是垃圾
    assert ok is True, message
    assert pending.read_bytes() == target


# ── 真实产物往返（需要本地样本，缺失时跳过）─────────────────────────────────

_REAL = [
    (r"216.exe", "v2.1.6"),
    (r"220.exe", "v2.2.0"),
]


def _real_paths():
    import os
    import tempfile

    base = os.path.join(tempfile.gettempdir(), "fc-delta")
    paths = [os.path.join(base, n) for n, _ in _REAL]
    return paths if all(os.path.isfile(p) for p in paths) else None


@pytest.mark.skipif(_real_paths() is None, reason="本地没有 v2.1.6 / v2.2.0 样本 EXE")
def test_real_exe_delta_roundtrip():
    """真实产物：补丁必须能字节级复现官方新版，且显著小于全量。"""
    old_path, new_path = _real_paths()
    with open(old_path, "rb") as f:
        base = f.read()
    with open(new_path, "rb") as f:
        target = f.read()

    delta = ed.build_delta(base, target)
    assert len(delta) < len(target) * 0.2, "增量补丁应显著小于全量"
    assert ed.apply_delta(base, delta) == target
