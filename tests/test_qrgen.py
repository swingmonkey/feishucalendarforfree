"""qrgen 的回归测试。

参考矩阵是固定向量：改编码器后如果扫不出来了，这里必须红。向量本身
用 OpenCV 的 QRCodeDetector 解码过一遍，保证不是「自己验证自己」。
"""

import pytest

import qrgen

# https://accounts.feishu.cn/oauth/v1/device/verify?user_code=ABCD-EFGH
# 版本 5 / 纠错 M；# 是深色模块
_REFERENCE_URL = "https://accounts.feishu.cn/oauth/v1/device/verify?user_code=ABCD-EFGH"
_REFERENCE_ROWS = [
    "#######.#.#...#.#.##.....####.#######",
    "#.....#....#######..##..#.#...#.....#",
    "#.###.#..#.#....##.###..#.##..#.###.#",
    "#.###.#.##.##......##..#.#.#..#.###.#",
    "#.###.#.##....#.#......#.####.#.###.#",
    "#.....#.###.###...##.##.##....#.....#",
    "#######.#.#.#.#.#.#.#.#.#.#.#.#######",
    "........#..##.##.#####..#.##.........",
    "#...#.#######.....#...###.#..#####..#",
    "###....#....#.#.#..###.....###..##.#.",
    ".#..#.#.##.##...##..#..#####.#.#..#..",
    "..#..#.#...#.##..##..####......#..##.",
    "####..##.#.#..##.#####..#..#####.####",
    ".#.###.##..#..#####.##.##.###...##...",
    ".########.....##..#..####.####.####..",
    "#......####...#.#....####.#...###.###",
    "..#..##.##.###..#...#...##.#.##..####",
    "#.##.#.##..##.#..###.#...####...#..#.",
    "##..####..##...#..##...#####.#.###...",
    ".##..#.##.#.##.#######.##...#.###.##.",
    "###.#.#......#...#..####.....###..#..",
    "#..##..##..#.####.#..#.#.####..##..#.",
    ".#...###...#..##.#.....#...#...####..",
    "..##....#..#.######.#.##..##...##.#.#",
    "####.##....##..#..##..####...##..###.",
    "#....#..#.#..#..#..###.#######.##.#..",
    "..###.##........###.#..#..##.#.#..#..",
    "..####..###.#....#...#.##.#...#.#.#..",
    "##.#..####.##..#.#.#.##.#..######.###",
    "........###.##.####....#.####...#....",
    "#######.#..#...##.#.######..#.#.#..#.",
    "#.....#..#.##.......##......#...###..",
    "#.###.#.##..##..#..##...##..#########",
    "#.###.#..######...##..#...######.#..#",
    "#.###.#...####.#.###.####....##..#...",
    "#.....#..#.....#######....#.##..#.##.",
    "#######.##.#.#..##...##....#...#.####",
]


def _as_rows(matrix):
    return ["".join("#" if v else "." for v in row) for row in matrix]


def test_reference_url_matches_fixed_vector():
    assert _as_rows(qrgen.make_qr(_REFERENCE_URL)) == _REFERENCE_ROWS


def test_size_follows_version():
    # 版本 n 的边长是 17 + 4n；短内容应该落进最小的版本
    assert len(qrgen.make_qr("hi")) == 21
    assert len(qrgen.make_qr("x" * 40)) == 29


def test_matrix_is_square_and_has_three_finders():
    matrix = qrgen.make_qr(_REFERENCE_URL)
    size = len(matrix)
    assert all(len(row) == size for row in matrix)
    # 三个角上的 7×7 定位图案：外圈全深，中心 3×3 全深，中间一圈留白
    for top, left in ((0, 0), (0, size - 7), (size - 7, 0)):
        for dy in range(7):
            for dx in range(7):
                dark = matrix[top + dy][left + dx]
                if dy in (0, 6) or dx in (0, 6):
                    assert dark, "定位图案外圈应为深色"
                elif dy in (1, 5) or dx in (1, 5):
                    assert not dark, "定位图案第二圈应为浅色"
                else:
                    assert dark, "定位图案中心应为深色"


def test_timing_pattern_alternates():
    matrix = qrgen.make_qr(_REFERENCE_URL)
    for i in range(8, len(matrix) - 8):
        assert matrix[6][i] == (i % 2 == 0)
        assert matrix[i][6] == (i % 2 == 0)


def test_rejects_content_beyond_capacity():
    with pytest.raises(ValueError):
        qrgen.make_qr("x" * 400)


def test_decodes_with_opencv_when_available():
    """有 OpenCV 时做一次端到端解码；CI 没装就跳过。"""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")

    matrix = qrgen.make_qr(_REFERENCE_URL)
    size, scale, quiet = len(matrix), 6, 4
    side = (size + quiet * 2) * scale
    image = np.full((side, side), 255, dtype=np.uint8)
    for row in range(size):
        for col in range(size):
            if matrix[row][col]:
                y, x = (row + quiet) * scale, (col + quiet) * scale
                image[y : y + scale, x : x + scale] = 0

    text, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    assert text == _REFERENCE_URL
