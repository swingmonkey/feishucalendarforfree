"""生成 EXE 的成员级增量补丁（CI 侧脚本，仅标准库）。

用法（在发版工作流里）::

    python tools/make_delta.py --new dist/FeishuCalendar.exe \
                               --out dist/FeishuCalendar.exe.delta \
                               [--repo OWNER/NAME] [--current-tag vX.Y.Z]

脚本会通过 GitHub API 找到**上一个正式发布**（有 .exe 资产的那个），下载它的
EXE 作为基座，再调用 :func:`exe_delta.build_delta` 生成补丁。

找不到可用的上一版时会以退出码 2 结束——工作流据此跳过补丁上传，客户端自然
回退到全量下载（这是正常路径，不是失败）。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import exe_delta as ed  # noqa: E402

API = "https://api.github.com"
UA = "feishucalendar-release-delta"
EXIT_NO_BASE = 2


def _api_get(path: str) -> object:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def find_previous_release(repo: str, current_tag: str) -> dict | None:
    """最近一个「不是当前 tag、且带 .exe 资产」的正式发布。"""
    releases = _api_get(f"/repos/{repo}/releases?per_page=100")
    if not isinstance(releases, list):
        return None
    candidates = []
    for rel in releases:
        if not isinstance(rel, dict) or rel.get("draft"):
            continue
        tag = rel.get("tag_name") or ""
        if not tag or tag == current_tag:
            continue
        exe = next(
            (
                a
                for a in (rel.get("assets") or [])
                if (a.get("name") or "").lower().endswith(".exe")
            ),
            None,
        )
        if not exe:
            continue
        candidates.append((rel.get("published_at") or "", tag, exe))
    if not candidates:
        return None
    candidates.sort(key=lambda t: t[0])
    _, tag, exe = candidates[-1]
    return {"tag": tag, "asset": exe}


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as f:
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            f.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True, help="本次构建出的 EXE")
    ap.add_argument("--out", required=True, help="补丁输出路径")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", ""))
    ap.add_argument("--current-tag", default=os.environ.get("GITHUB_REF_NAME", ""))
    ap.add_argument("--base", default="", help="直接指定基座 EXE（跳过 API 查找，主要给本地调试用）")
    args = ap.parse_args()

    new_path = Path(args.new)
    if not new_path.is_file():
        print(f"[delta] 找不到新 EXE: {new_path}", file=sys.stderr)
        return 1

    target = new_path.read_bytes()

    base_path: Path | None = None
    tmp_base = None
    if args.base:
        base_path = Path(args.base)
        if not base_path.is_file():
            print(f"[delta] 找不到基座 EXE: {base_path}", file=sys.stderr)
            return 1
    else:
        if not args.repo:
            print("[delta] 缺少 --repo / GITHUB_REPOSITORY", file=sys.stderr)
            return EXIT_NO_BASE
        prev = find_previous_release(args.repo, args.current_tag)
        if not prev:
            print("[delta] 找不到带 EXE 的上一版发布，跳过增量补丁")
            return EXIT_NO_BASE
        tmp_base = new_path.parent / "_delta_base.exe"
        print(f"[delta] 基座版本 {prev['tag']} / {prev['asset']['name']}")
        download(prev["asset"]["browser_download_url"], tmp_base)
        base_path = tmp_base

    try:
        base = base_path.read_bytes()
        delta = ed.build_delta(base, target)
    except ed.DeltaError as exc:
        print(f"[delta] 基座不可用（{exc}），跳过增量补丁")
        return EXIT_NO_BASE
    finally:
        if tmp_base is not None and tmp_base.exists():
            try:
                tmp_base.unlink()
            except OSError:
                pass

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(delta)

    stats = ed.delta_stats(delta)
    print(
        f"[delta] 全量 {len(target) / 1048576:.2f} MiB -> 补丁 {len(delta) / 1048576:.2f} MiB"
        f"（{stats['ratio'] * 100:.1f}%，省 {100 - stats['ratio'] * 100:.1f}%），"
        f"变更成员 {stats['n_changed']} 个"
    )
    print(f"[delta] base_sha256    = {stats['base_sha256']}")
    print(f"[delta] target_sha256  = {ed.sha256_bytes(target)}")
    print(f"[delta] delta_sha256   = {ed.sha256_bytes(delta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
