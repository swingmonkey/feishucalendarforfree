"""Headless CLI — ask the calendar a question without opening a window.

    python -m headless today                 # 今天的日程
    python -m headless next --json           # 下一条（给脚本 / Stream Deck）
    python -m headless range --start 2026-11-01 --end 2026-11-30
    python -m headless search 评审 --json

Defaults to the local store, so it works offline, without auth and without
PySide6 on the import path. ``--source lark`` goes to Feishu through lark-cli,
``--source ics`` reads an exported ``.ics`` file.

Output contract: one line per event in text mode; a stable JSON envelope in
``--json`` mode. Exit codes — 0 ok, 1 backend failure, 2 bad usage.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

import backends as backends_module
import event_store


def _day_bounds(now: datetime):
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1) - timedelta(seconds=1)


def _make_backend(args):
    if args.source == "ics":
        return backends_module.build_backend("ics", path=args.ics)
    return backends_module.build_backend("lark")


def _row(occ) -> dict:
    organizer = ""
    data = occ.event.get("event_organizer", {})
    if isinstance(data, dict):
        organizer = str(data.get("display_name", "") or "")
    return {
        "date": occ.start.strftime("%Y-%m-%d"),
        "start": "全天" if occ.all_day else occ.start.strftime("%H:%M"),
        "end": "全天" if occ.all_day else occ.end.strftime("%H:%M"),
        "summary": occ.summary,
        "organizer": organizer,
        "event_id": str(occ.event.get("event_id", "") or ""),
        "all_day": occ.all_day,
        "running": occ.start <= datetime.now() < occ.end,
    }


def _emit(rows: list, as_json: bool, command: str) -> None:
    if as_json:
        payload = {
            "command": command,
            "generated_at": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "count": len(rows),
            "events": rows,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not rows:
        print("没有日程")
        return
    for row in rows:
        span = "全天" if row["all_day"] else f"{row['start']}-{row['end']}"
        extra = f"  ({row['organizer']})" if row["organizer"] else ""
        print(f"{row['date']} {span}  {row['summary']}{extra}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m headless",
        description="不打开窗口，直接从命令行读取日程。",
    )
    # 公共选项挂在每个子命令上（而不是顶层）：`headless today --json` 才是
    # 用户会敲的顺序；放在顶层会导致「子命令之后再写参数」直接报错。
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", help="输出 JSON（便于脚本消费）")
    common.add_argument(
        "--source",
        default="store",
        choices=["store", "lark", "ics"],
        help="数据来源：本地缓存（默认）/ 飞书 / ICS 文件",
    )
    common.add_argument("--db", default=None, help="指定 events.db 路径")
    common.add_argument("--ics", default=None, help="--source ics 时的 .ics 文件")
    common.add_argument("--limit", type=int, default=0, help="最多输出 N 条（0 表示不限）")

    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("today", parents=[common], help="今天的日程")
    sub.add_parser("next", parents=[common], help="接下来的一条日程")

    range_parser = sub.add_parser("range", parents=[common], help="指定区间内的日程")
    range_parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    range_parser.add_argument("--end", required=True, help="YYYY-MM-DD")

    search_parser = sub.add_parser("search", parents=[common], help="按关键词搜索")
    search_parser.add_argument("query", help="关键词")

    return parser


def _parse_day(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"日期格式应为 YYYY-MM-DD：{value}") from exc


def run(args) -> list:
    if args.source == "store":
        conn = event_store.connect(args.db) if args.db else event_store.connect()
        try:
            return _query(args, backends_module.build_backend("store", conn=conn))
        finally:
            # 命令行是一次性的：进程虽会退出，但显式关掉能避免 ResourceWarning
            conn.close()
    return _query(args, _make_backend(args))


def _query(args, backend) -> list:
    now = datetime.now()

    if args.command == "today":
        start, end = _day_bounds(now)
        occurrences = backend.fetch_range(start, end)
        rows = [_row(o) for o in occurrences]
    elif args.command == "next":
        start, end = now, now + timedelta(days=7)
        occurrences = [occ for occ in backend.fetch_range(start, end) if occ.end > now]
        rows = [_row(o) for o in occurrences[:1]]
    elif args.command == "range":
        start = _parse_day(args.start)
        end = _parse_day(args.end).replace(hour=23, minute=59, second=59)
        occurrences = backend.fetch_range(start, end)
        rows = [_row(o) for o in occurrences]
    else:  # search
        rows = [_row(occ) for occ in backend.search(args.query)]

    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    return rows


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        rows = run(args)
    except backends_module.BackendError as exc:
        print(f"读取失败：{exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _emit(rows, args.json, args.command)
    return 0


if __name__ == "__main__":
    sys.exit(main())
