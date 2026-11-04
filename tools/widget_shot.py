"""小组件截图验收工具：灌入示例数据，在 offscreen 下截出三档 × 双主题。

用法：
    QT_QPA_PLATFORM=offscreen .venv/bin/python tools/widget_shot.py [输出目录]

和 ui_shot.py 同一条离屏路径（本机没有屏幕录制权限）。小组件表面是
浮窗自绘，直接 grab() 会带透明像素，所以先合成到一块中性底色上再存，
否则玻璃/台面的渐变在 PNG 里看不出来。
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QColor, QPainter, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

import desktop_widget as dw  # noqa: E402
import event_store  # noqa: E402


def iso(day: datetime) -> dict:
    return {"datetime": day.strftime("%Y-%m-%dT%H:%M:%S+08:00")}


def seed_events(now: datetime) -> list:
    evs = []
    for i, (h, m, dur, title) in enumerate([
        (9, 30, 60, "运行监督管理"),
        (14, 0, 90, "塔台管制检查准备"),
        (15, 0, 45, "空管参考案例整理"),
        (16, 30, 60, "案例复盘"),
        (19, 0, 30, "英语广播脚本评审"),
    ]):
        s = now.replace(hour=h, minute=m)
        evs.append({
            "event_id": f"t{i}",
            "summary": title,
            "start_time": iso(s),
            "end_time": iso(s + timedelta(minutes=dur)),
        })
    for day in range(1, 29, 2):
        s = datetime(now.year, now.month, day, 10, 0)
        evs.append({
            "event_id": f"h{day}",
            "summary": "例会",
            "start_time": iso(s),
            "end_time": iso(s + timedelta(minutes=120)),
        })
    return evs


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".ui_shot"
    if not out.is_dir():
        out.mkdir(parents=True)

    now = datetime.now().replace(second=0, microsecond=0)
    with tempfile.TemporaryDirectory() as tmp:
        conn = event_store.connect(Path(tmp) / "events.db")
        start = now.replace(day=1, hour=0, minute=0)
        end = now + timedelta(days=3)
        event_store.upsert_many(conn, seed_events(now), start, end)
        events = event_store.read_range(conn, start - timedelta(days=7), end)
        conn.close()

    snap = dw.build_snapshot(events, now, int((now - timedelta(minutes=34)).timestamp()))
    print(f"今日 {snap.today_count} 项 | 热力 {len(snap.heat)}x{len(snap.heat[0])} | 周行 {snap.week_rows}")

    for theme_name in ("dark", "light"):
        for size in ("small", "medium", "large"):
            w = dw.DesktopWidget(size_key=size, theme_name=theme_name)
            w.set_snapshot(snap)
            w.show()
            for _ in range(3):
                app.processEvents()
            shot = w.grab()
            canvas = QPixmap(shot.size())
            canvas.fill(QColor(120, 125, 135))
            p = QPainter(canvas)
            p.drawPixmap(0, 0, shot)
            p.end()
            name = f"widget-{size}-{theme_name}.png"
            canvas.save(str(out / name))
            print("saved", name)
            w.close()


if __name__ == "__main__":
    main()
