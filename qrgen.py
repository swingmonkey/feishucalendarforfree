"""二维码编码器（Byte 模式 / 纠错等级 M）。

为什么自己写：登录页要把 device-flow 的 verification_url 画成二维码，
原先靠 `lark-cli auth qrcode` 生成，一旦命令参数或 CLI 版本对不上，
用户就只剩一句「二维码不可用」——登录直接卡死。为一张二维码再引一个
第三方包，又要改两套打包脚本的 hidden-import，不划算。

只实现到版本 10（足够放下 213 字节的 URL），只做 Byte 模式与 M 等级。
生成结果用 tests/test_qrgen.py 里的固定向量比对（向量由 segno 生成），
保证与标准实现逐模块一致。
"""

from __future__ import annotations

# 纠错等级 M：版本 -> (每块纠错码字数, [(块数, 每块数据码字数), ...])
_EC_M: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
    7: (18, [(4, 31)]),
    8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}

# 对齐图案中心坐标
_ALIGN: dict[int, tuple[int, ...]] = {
    1: (),
    2: (6, 18),
    3: (6, 22),
    4: (6, 26),
    5: (6, 30),
    6: (6, 34),
    7: (6, 22, 38),
    8: (6, 24, 42),
    9: (6, 26, 46),
    10: (6, 28, 50),
}

# 版本信息（版本 7 起才有），18 位 BCH
_VERSION_BITS: dict[int, int] = {
    7: 0x07C94,
    8: 0x085BC,
    9: 0x09A99,
    10: 0x0A4D3,
}

# 格式信息（15 位 BCH），索引是掩码号；这里只需要纠错等级 M
_FORMAT_BITS_M = (0x5412, 0x5125, 0x5E7C, 0x5B4B, 0x45F9, 0x40CE, 0x4F97, 0x4AA0)

_EC_BITS_M = 0b00  # 纠错等级在格式信息里的编码


# ── GF(256) 与 Reed-Solomon ──────────────────────────────


def _gf_tables():
    exp = [0] * 512
    log = [0] * 256
    x = 1
    for i in range(255):
        exp[i] = x
        log[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        exp[i] = exp[i - 255]
    return exp, log


_EXP, _LOG = _gf_tables()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def _rs_generator(degree: int) -> list[int]:
    poly = [1]
    for i in range(degree):
        # 乘上 (x - α^i)
        new = [0] * (len(poly) + 1)
        for j, coef in enumerate(poly):
            new[j] ^= coef
            new[j + 1] ^= _gf_mul(coef, _EXP[i])
        poly = new
    return poly


def _rs_remainder(data: list[int], degree: int) -> list[int]:
    gen = _rs_generator(degree)
    rem = [0] * degree
    for byte in data:
        factor = byte ^ rem[0]
        rem.pop(0)
        rem.append(0)
        if factor:
            for i in range(degree):
                rem[i] ^= _gf_mul(gen[i + 1], factor)
    return rem


# ── 位流构造 ────────────────────────────────────────────


def _data_capacity(version: int) -> int:
    _, blocks = _EC_M[version]
    return sum(count * words for count, words in blocks)


def _encode_data(payload: bytes, version: int) -> list[int]:
    capacity = _data_capacity(version)
    count_bits = 8 if version <= 9 else 16
    bits: list[int] = []

    def push(value: int, length: int):
        for i in range(length - 1, -1, -1):
            bits.append((value >> i) & 1)

    push(0b0100, 4)  # Byte 模式
    push(len(payload), count_bits)
    for byte in payload:
        push(byte, 8)

    # 终止符最多 4 位
    push(0, min(4, capacity * 8 - len(bits)))
    # 补到字节边界
    while len(bits) % 8:
        bits.append(0)

    codewords = [int("".join(str(b) for b in bits[i : i + 8]), 2) for i in range(0, len(bits), 8)]
    # 填充码字 0xEC / 0x11 交替
    pad = (0xEC, 0x11)
    index = 0
    while len(codewords) < capacity:
        codewords.append(pad[index % 2])
        index += 1
    return codewords


def _interleave(codewords: list[int], version: int) -> list[int]:
    ec_per_block, blocks = _EC_M[version]
    chunks = []
    offset = 0
    for count, words in blocks:
        for _ in range(count):
            chunks.append(codewords[offset : offset + words])
            offset += words

    ec_blocks = [_rs_remainder(chunk, ec_per_block) for chunk in chunks]

    result: list[int] = []
    max_len = max(len(c) for c in chunks)
    for i in range(max_len):
        for chunk in chunks:
            if i < len(chunk):
                result.append(chunk[i])
    for i in range(ec_per_block):
        for block in ec_blocks:
            result.append(block[i])
    return result


# ── 矩阵布局 ────────────────────────────────────────────


class _Matrix:
    def __init__(self, version: int):
        self.version = version
        self.size = 17 + 4 * version
        self.modules = [[False] * self.size for _ in range(self.size)]
        self.reserved = [[False] * self.size for _ in range(self.size)]

    def set_function(self, row: int, col: int, dark: bool):
        if 0 <= row < self.size and 0 <= col < self.size:
            self.modules[row][col] = dark
            self.reserved[row][col] = True

    def place_finder(self, row: int, col: int):
        for dy in range(-1, 8):
            for dx in range(-1, 8):
                r, c = row + dy, col + dx
                if not (0 <= r < self.size and 0 <= c < self.size):
                    continue
                inside = 0 <= dy <= 6 and 0 <= dx <= 6
                edge = dy in (0, 6) or dx in (0, 6)
                core = 2 <= dy <= 4 and 2 <= dx <= 4
                self.set_function(r, c, inside and (edge or core))

    def place_alignment(self):
        coords = _ALIGN[self.version]
        for row in coords:
            for col in coords:
                # 三个角上的对齐图案与定位图案重叠，跳过
                if (row, col) in ((6, 6), (6, coords[-1]), (coords[-1], 6)):
                    continue
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        dark = max(abs(dy), abs(dx)) != 1
                        self.set_function(row + dy, col + dx, dark)

    def place_timing(self):
        for i in range(8, self.size - 8):
            dark = i % 2 == 0
            self.set_function(6, i, dark)
            self.set_function(i, 6, dark)

    def place_dark_module(self):
        self.set_function(self.size - 8, 8, True)

    def place_format(self, mask: int):
        bits = _FORMAT_BITS_M[mask]
        for i in range(15):
            dark = (bits >> i) & 1 == 1
            # 副本一：沿第 8 列自上而下，跳过定位图案占用的第 6 行
            if i < 6:
                row = i
            elif i < 8:
                row = i + 1
            else:
                row = self.size - 15 + i
            self.set_function(row, 8, dark)
            # 副本二：沿第 8 行自右向左，右下角接着左下角
            if i < 8:
                col = self.size - 1 - i
            elif i == 8:
                col = 7
            else:
                col = 14 - i
            self.set_function(8, col, dark)

    def place_version(self):
        bits = _VERSION_BITS.get(self.version)
        if bits is None:
            return
        for i in range(18):
            dark = (bits >> i) & 1 == 1
            row, col = i // 3, i % 3
            self.set_function(row, self.size - 11 + col, dark)
            self.set_function(self.size - 11 + col, row, dark)

    def place_data(self, codewords: list[int]):
        bits = []
        for word in codewords:
            for i in range(7, -1, -1):
                bits.append((word >> i) & 1)

        index = 0
        col = self.size - 1
        upward = True
        while col > 0:
            if col == 6:  # 跳过竖直的定位图案列
                col -= 1
            rows = range(self.size - 1, -1, -1) if upward else range(self.size)
            for row in rows:
                for offset in (0, 1):
                    c = col - offset
                    if self.reserved[row][c]:
                        continue
                    dark = bits[index] == 1 if index < len(bits) else False
                    self.modules[row][c] = dark
                    index += 1
            upward = not upward
            col -= 2


_MASKS = (
    lambda r, c: (r + c) % 2 == 0,
    lambda r, c: r % 2 == 0,
    lambda r, c: c % 3 == 0,
    lambda r, c: (r + c) % 3 == 0,
    lambda r, c: (r // 2 + c // 3) % 2 == 0,
    lambda r, c: (r * c) % 2 + (r * c) % 3 == 0,
    lambda r, c: ((r * c) % 2 + (r * c) % 3) % 2 == 0,
    lambda r, c: ((r + c) % 2 + (r * c) % 3) % 2 == 0,
)


def _apply_mask(matrix: _Matrix, mask: int) -> _Matrix:
    """返回套用掩码后的副本；功能图案（reserved）不受影响。"""
    fn = _MASKS[mask]
    out = _Matrix(matrix.version)
    out.modules = [row[:] for row in matrix.modules]
    out.reserved = [row[:] for row in matrix.reserved]
    for row in range(matrix.size):
        for col in range(matrix.size):
            if not matrix.reserved[row][col] and fn(row, col):
                out.modules[row][col] = not out.modules[row][col]
    return out


def _penalty(modules: list[list[bool]]) -> int:
    size = len(modules)
    score = 0

    # 规则 1：同色连续 ≥5
    for lines in (modules, [list(col) for col in zip(*modules, strict=True)]):
        for line in lines:
            run = 1
            for i in range(1, size):
                if line[i] == line[i - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + (run - 5)
                    run = 1
            if run >= 5:
                score += 3 + (run - 5)

    # 规则 2：2×2 同色块
    for row in range(size - 1):
        for col in range(size - 1):
            v = modules[row][col]
            if (
                modules[row][col + 1] == v
                and modules[row + 1][col] == v
                and modules[row + 1][col + 1] == v
            ):
                score += 3

    # 规则 3：形似定位图案的 1:1:3:1:1
    pattern_a = [True, False, True, True, True, False, True, False, False, False, False]
    pattern_b = list(reversed(pattern_a))
    for lines in (modules, [list(col) for col in zip(*modules, strict=True)]):
        for line in lines:
            for i in range(size - 10):
                window = line[i : i + 11]
                if window == pattern_a or window == pattern_b:
                    score += 40

    # 规则 4：深浅比例偏离 50%
    dark = sum(sum(1 for v in row if v) for row in modules)
    percent = dark * 100 // (size * size)
    score += 10 * (abs(percent - 50) // 5)
    return score


# ── 对外接口 ────────────────────────────────────────────


def make_qr(text: str) -> list[list[bool]]:
    """把文本编码成二维码矩阵（True = 深色模块）。"""
    payload = text.encode("utf-8")
    version = None
    for candidate in sorted(_EC_M):
        # 4 位模式 + 计数位 + 数据
        count_bits = 8 if candidate <= 9 else 16
        needed_bits = 4 + count_bits + len(payload) * 8
        if needed_bits <= _data_capacity(candidate) * 8:
            version = candidate
            break
    if version is None:
        raise ValueError("内容过长，超出版本 10 的容量")

    codewords = _interleave(_encode_data(payload, version), version)
    matrix = _Matrix(version)
    matrix.place_finder(0, 0)
    matrix.place_finder(0, matrix.size - 7)
    matrix.place_finder(matrix.size - 7, 0)
    matrix.place_alignment()
    matrix.place_timing()
    matrix.place_dark_module()
    matrix.place_version()
    # 先用掩码 0 把格式信息区占住：这几圈模块是固定的，数据不能写进去，
    # 否则数据会整体前移，扫出来就是一片乱码。真实掩码值最后再覆盖。
    matrix.place_format(0)
    matrix.place_data(codewords)

    best = None
    best_score = None
    for mask in range(8):
        candidate = _apply_mask(matrix, mask)
        candidate.place_format(mask)
        score = _penalty(candidate.modules)
        if best_score is None or score < best_score:
            best, best_score = candidate, score
    return best.modules
