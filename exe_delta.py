"""PyInstaller onefile EXE 的成员级增量更新（仅标准库）。

背景
----
打包产物是 ~53 MiB 的单文件 EXE（PE 引导程序 + 追加的 CArchive）。实测两个
相邻版本：239 个归档成员里 **236 个逐字节相同**，只有 ``PYZ.pyz`` /
``base_library.zip`` / ``main`` 变了。因此「只下载变化的部分」是可行的。

为什么不按文件字节做差分
------------------------
CArchive 里所有成员是顺序拼接的，前面任何一个成员变长都会让后面整体偏移。
实测固定偏移分块命中率 0%、FastCDC 命中率 0%——不是内容没被复用，而是字节
基座被整体挪动了。**成员边界才是稳定的复用单位**，所以按成员搬运。

补丁里装什么
------------
* 目标 EXE 的引导程序、TOC、cookie（成员偏移随大小变化，必须由补丁携带）
* 压缩字节与基座不同的成员原文
* 未变成员不装数据，客户端从本机旧 EXE 按偏移切片复制

安全设计
--------
补丁头带 ``base_sha256``：只有本机 EXE 的 sha256 与之相符才允许打补丁，
避免把补丁应用到错误的基线上。应用结果再与 ``target_sha256`` 比对，最终仍由
``SHA256SUMS`` 权威校验。任何一步失败都应回退到全量下载（见 :mod:`updater`）
——补丁只是优化路径，绝不是唯一路径。
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

COOKIE_MAGIC = b"MEI\x0c\x0b\x0a\x0b\x0e"
COOKIE_FORMAT = "!8sIIII64s"
COOKIE_LENGTH = struct.calcsize(COOKIE_FORMAT)

TOC_ENTRY_FORMAT = "!IIIIBc"
TOC_ENTRY_LENGTH = struct.calcsize(TOC_ENTRY_FORMAT)

DELTA_MAGIC = b"FCDELTA1"
DELTA_VERSION = 1
# magic, version, target_size, base_sha256, target_sha256[:16], stub/toc/cookie, 变更成员数
DELTA_HEADER_FORMAT = "!8sIQ32s16sIIIII"
DELTA_HEADER_LENGTH = struct.calcsize(DELTA_HEADER_FORMAT)
# 每个变更成员：name_len, data_length, uncompressed_length, flag, typecode, name, data
DELTA_MEMBER_FORMAT = "!HIIBc"
DELTA_MEMBER_HEADER_LENGTH = struct.calcsize(DELTA_MEMBER_FORMAT)


class DeltaError(Exception):
    """补丁本身有问题（损坏、基座不匹配、版本不认识等）。

    调用方应捕获它并回退到全量下载。
    """


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass
class ArchiveEntry:
    """CArchive 里的一个成员。"""

    name: str
    offset: int  # 相对归档起点
    data_length: int  # 归档内长度（压缩后）
    uncompressed_length: int
    compression_flag: int
    typecode: str


@dataclass
class CArchive:
    """PyInstaller onefile 可执行文件的结构视图。"""

    data: bytes
    archive_start: int
    toc_offset: int  # 相对 archive_start
    toc_length: int
    cookie_start: int

    @property
    def stub(self) -> bytes:
        """PE 引导程序（归档之前的部分）。"""
        return self.data[: self.archive_start]

    @property
    def toc_bytes(self) -> bytes:
        start = self.archive_start + self.toc_offset
        return self.data[start : start + self.toc_length]

    @property
    def cookie_bytes(self) -> bytes:
        return self.data[self.cookie_start :]

    def member_bytes(self, entry: ArchiveEntry) -> bytes:
        start = self.archive_start + entry.offset
        return self.data[start : start + entry.data_length]


def parse_toc_bytes(blob: bytes) -> list[ArchiveEntry]:
    """解析一段 TOC 字节，按顺序返回成员；成员名尾部的 NUL 填充会被去掉。"""
    entries: list[ArchiveEntry] = []
    pos = 0
    while pos < len(blob):
        if pos + TOC_ENTRY_LENGTH > len(blob):
            raise DeltaError("TOC 被截断")
        entry_len, offset, dlen, ulen, flag, typecode = struct.unpack(
            TOC_ENTRY_FORMAT, blob[pos : pos + TOC_ENTRY_LENGTH]
        )
        pos += TOC_ENTRY_LENGTH
        name_len = entry_len - TOC_ENTRY_LENGTH
        if name_len < 0 or pos + name_len > len(blob):
            raise DeltaError("TOC 成员名长度非法")
        name = blob[pos : pos + name_len].rstrip(b"\x00").decode("utf-8", "replace")
        pos += name_len
        entries.append(
            ArchiveEntry(
                name=name,
                offset=offset,
                data_length=dlen,
                uncompressed_length=ulen,
                compression_flag=flag,
                typecode=typecode.decode("latin-1", "replace"),
            )
        )
    return entries


def parse_carchive(data: bytes) -> CArchive:
    """解析 onefile EXE；不是合法的 PyInstaller 归档就抛 :class:`DeltaError`。"""
    cookie_start = data.rfind(COOKIE_MAGIC)
    if cookie_start < 0:
        raise DeltaError("找不到 CArchive cookie，不是 PyInstaller onefile 产物")

    cookie = data[cookie_start : cookie_start + COOKIE_LENGTH]
    if len(cookie) < COOKIE_LENGTH:
        raise DeltaError("cookie 被截断")
    _magic, archive_length, toc_offset, toc_length, _pyver, pylib = struct.unpack(
        COOKIE_FORMAT, cookie
    )
    if not pylib.rstrip(b"\x00"):
        raise DeltaError("cookie 缺少 python 库名")

    end = cookie_start + COOKIE_LENGTH
    start = end - archive_length
    if start < 0 or toc_offset + toc_length > archive_length:
        raise DeltaError("cookie 里的长度字段不自洽")

    return CArchive(
        data=data,
        archive_start=start,
        toc_offset=toc_offset,
        toc_length=toc_length,
        cookie_start=cookie_start,
    )


def entries_of(data: bytes) -> tuple[CArchive, list[ArchiveEntry]]:
    archive = parse_carchive(data)
    return archive, parse_toc_bytes(archive.toc_bytes)


# ── 补丁格式 ────────────────────────────────────────────────────────────────
#
#   头（固定 88 字节）
#     magic           8s   b"FCDELTA1"
#     version         I
#     target_size     Q    目标 EXE 总长度
#     base_sha256    32s   补丁所基于的旧 EXE 的 sha256 原始字节
#     target_sha256  16s   目标 EXE 的 sha256 前 16 字节
#     stub_len        I
#     toc_offset      I    相对归档起点
#     toc_len         I
#     cookie_len      I
#     n_changed       I
#   段（按此顺序紧跟头部）
#     stub | toc | cookie | changed[]...
#
# 目标成员的**目标偏移**无需单独存放：解析补丁携带的 TOC 即可获得；
# 未变成员的**源偏移**则从本机旧 EXE 的 TOC 里按名字查。


def build_delta(base: bytes, target: bytes) -> bytes:
    """生成把 ``base`` 变成 ``target`` 所需的补丁。

    只在 CI 里使用（需要同时拿到上一版与这一版 EXE）。
    """
    base_archive, base_entries = entries_of(base)
    target_archive, target_entries = entries_of(target)
    base_by_name = {e.name: e for e in base_entries}

    changed: list[bytes] = []
    for entry in target_entries:
        old = base_by_name.get(entry.name)
        if old is not None:
            same_shape = (
                old.data_length == entry.data_length
                and old.uncompressed_length == entry.uncompressed_length
                and old.compression_flag == entry.compression_flag
            )
            if same_shape and base_archive.member_bytes(old) == target_archive.member_bytes(entry):
                continue  # 可从本机磁盘直接搬运，不必进补丁
        name_bytes = entry.name.encode("utf-8")
        changed.append(
            struct.pack(
                DELTA_MEMBER_FORMAT,
                len(name_bytes),
                entry.data_length,
                entry.uncompressed_length,
                entry.compression_flag,
                entry.typecode.encode("latin-1", "replace"),
            )
            + name_bytes
            + target_archive.member_bytes(entry)
        )

    header = struct.pack(
        DELTA_HEADER_FORMAT,
        DELTA_MAGIC,
        DELTA_VERSION,
        len(target),
        bytes.fromhex(sha256_bytes(base)),
        bytes.fromhex(sha256_bytes(target))[:16],
        len(target_archive.stub),
        target_archive.toc_offset,
        len(target_archive.toc_bytes),
        len(target_archive.cookie_bytes),
        len(changed),
    )
    return b"".join(
        [
            header,
            target_archive.stub,
            target_archive.toc_bytes,
            target_archive.cookie_bytes,
            *changed,
        ]
    )


def read_delta_header(delta: bytes) -> dict:
    """解析补丁头；只做格式与版本检查，不做完整性校验。"""
    if len(delta) < DELTA_HEADER_LENGTH:
        raise DeltaError("补丁太短，疑似下载不完整")
    (
        magic,
        version,
        target_size,
        base_sha,
        tgt_sha,
        stub_len,
        toc_offset,
        toc_len,
        cookie_len,
        n_changed,
    ) = struct.unpack(DELTA_HEADER_FORMAT, delta[:DELTA_HEADER_LENGTH])
    if magic != DELTA_MAGIC:
        raise DeltaError("补丁魔数不匹配")
    if version != DELTA_VERSION:
        raise DeltaError(f"不支持的补丁版本 {version}")
    return {
        "version": version,
        "target_size": target_size,
        "base_sha256": base_sha.hex(),
        "target_sha256_prefix": tgt_sha.hex(),
        "stub_len": stub_len,
        "toc_offset": toc_offset,
        "toc_len": toc_len,
        "cookie_len": cookie_len,
        "n_changed": n_changed,
    }


def apply_delta(base: bytes, delta: bytes) -> bytes:
    """把补丁应用到本机已有的旧 EXE 字节上，返回新的 EXE 字节。

    调用方必须随后用 ``SHA256SUMS`` 校验结果；补丁里的 ``target_sha256_prefix``
    只是快速自检。
    """
    header = read_delta_header(delta)
    if header["base_sha256"] != sha256_bytes(base):
        raise DeltaError("本机 EXE 与补丁基座不匹配（可能已经打过一次补丁）")

    pos = DELTA_HEADER_LENGTH
    stub_len = header["stub_len"]
    toc_len, cookie_len = header["toc_len"], header["cookie_len"]
    if len(delta) < pos + stub_len + toc_len + cookie_len:
        raise DeltaError("补丁被截断（头部之后的数据不足）")

    stub = delta[pos : pos + stub_len]
    pos += stub_len
    toc = delta[pos : pos + toc_len]
    pos += toc_len
    cookie = delta[pos : pos + cookie_len]
    pos += cookie_len

    supplied: dict[str, bytes] = {}
    for _ in range(header["n_changed"]):
        if pos + DELTA_MEMBER_HEADER_LENGTH > len(delta):
            raise DeltaError("补丁被截断（成员头）")
        name_len, dlen, _ulen, _flag, _tc = struct.unpack(
            DELTA_MEMBER_FORMAT, delta[pos : pos + DELTA_MEMBER_HEADER_LENGTH]
        )
        pos += DELTA_MEMBER_HEADER_LENGTH
        if pos + name_len + dlen > len(delta):
            raise DeltaError("补丁被截断（成员数据）")
        name = delta[pos : pos + name_len].decode("utf-8", "replace")
        pos += name_len
        supplied[name] = delta[pos : pos + dlen]
        pos += dlen

    target_entries = parse_toc_bytes(toc)
    base_archive, base_entries = entries_of(base)
    base_by_name = {e.name: e for e in base_entries}

    out = bytearray(header["target_size"])
    out[:stub_len] = stub
    for entry in target_entries:
        dest = stub_len + entry.offset
        end = dest + entry.data_length
        if end > len(out):
            raise DeltaError(f"成员 {entry.name} 超出目标文件长度")
        payload = supplied.get(entry.name)
        if payload is not None:
            out[dest:end] = payload
            continue
        old = base_by_name.get(entry.name)
        if old is None:
            raise DeltaError(f"补丁缺少成员 {entry.name}，无法从本机复制")
        if old.data_length != entry.data_length:
            raise DeltaError(f"成员 {entry.name} 长度不一致，补丁与本机不匹配")
        src = base_archive.archive_start + old.offset
        out[dest:end] = base[src : src + entry.data_length]

    toc_dest = stub_len + header["toc_offset"]
    out[toc_dest : toc_dest + len(toc)] = toc
    out[len(out) - len(cookie) :] = cookie
    return bytes(out)


def delta_stats(delta: bytes) -> dict:
    """给日志/测试用的摘要信息。"""
    header = read_delta_header(delta)
    return {
        **header,
        "delta_bytes": len(delta),
        "full_bytes": header["target_size"],
        "ratio": len(delta) / header["target_size"] if header["target_size"] else 0.0,
    }
