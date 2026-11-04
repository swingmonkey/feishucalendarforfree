"""UI 截图验收工具：灌入示例数据，在 offscreen 下截出月/周视图。

用法：
    QT_QPA_PLATFORM=offscreen .venv/bin/python tools/ui_shot.py [输出目录]

为什么需要它：QSS 和自绘的视觉效果没有单元测试能断言，改动样式后
必须真的看一眼。这台机器没有屏幕录制权限，screencapture 拿不到窗口，
所以走 QWidget.grab() 这条离屏路径。
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def seed(store_path: Path, year: int, month: int) -> None:
    """往库里灌一个月左右的示例日程，让截图有内容可看。"""
    import event_store

    conn = event_store.connect(store_path)
    base = datetime(year, month, 1, 0, 0, 0)

    samples = [
        (1, 9, 30, 30, "周会 · 运行办"),
        (2, 14, 0, 60, "塔台管制检查准备"),
        (3, 10, 0, 90, "党务会议"),
        (3, 16, 30, 60, "案例复盘"),
        (5, 8, 30, 45, "交接班"),
        (5, 11, 0, 30, "英语广播脚本评审"),
        (8, 15, 0, 120, "西南局行政检查"),
        (9, 9, 0, 60, "周会 · 运行办"),
        (11, 13, 30, 30, "航线协调"),
        (12, 10, 0, 60, "质量复盘"),
        (15, 9, 0, 60, "周会 · 运行办"),
        (16, 14, 0, 90, "执照管理专题"),
        (18, 10, 30, 90, "EnglishMaster 迭代"),
        (19, 16, 0, 60, "Obsidian 案例导入"),
        (22, 9, 0, 60, "周会 · 运行办"),
        (23, 11, 0, 45, "空管参考案例整理"),
        (25, 15, 0, 120, "季度绩效面谈"),
        (26, 9, 30, 60, "运行监督管理"),
    ]

    events = []
    for day, hour, minute, dur, title in samples:
        start = base.replace(day=day, hour=hour, minute=minute)
        end = start + timedelta(minutes=dur)
        events.append(
            {
                "event_id": f"seed-{year}{month:02d}-{day}-{hour}{minute}",
                "summary": title,
                "start_time": {"timestamp": str(int(start.timestamp())), "tz": "Asia/Shanghai"},
                "end_time": {"timestamp": str(int(end.timestamp())), "tz": "Asia/Shanghai"},
            }
        )

    span_start = base - timedelta(days=10)
    span_end = base.replace(day=28) + timedelta(days=10)
    event_store.upsert_many(conn, events, span_start, span_end)
    print(f"seeded {event_store.count(conn)} events into {store_path}")
    conn.close()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    out_dir = Path(args[0]) if args else ROOT / ".ui_shot"
    theme_name = args[1] if len(args) > 1 else "dark"
    if not out_dir.is_dir():
        out_dir.mkdir(parents=True)

    app = QApplication(sys.argv[:1])

    tmp = Path(tempfile.mkdtemp()) / "events.db"
    seed(tmp, 2026, 11)

    import event_store

    event_store.default_db_path = lambda: tmp

    import config as config_module

    config_module.get_app_dir = lambda: tmp.parent

    from config import Config
    from main_window import MainWindow

    config = Config()
    config.set("theme", theme_name)
    config.set("window_width", 720)
    config.set("window_height", 860)

    win = MainWindow(config)
    win.resize(720, 860)
    win.move(0, 0)
    win.show()

    def shoot() -> None:
        # 先截图月视图
        win._set_view_mode("month")
        app.processEvents()
        QTimer.singleShot(900, lambda: shoot_week())

    def shoot_week() -> None:
        path = out_dir / f"month-{theme_name}.png"
        win.grab().save(str(path))
        print("saved", path, path.stat().st_size)

        win._set_view_mode("week")
        app.processEvents()
        QTimer.singleShot(900, shoot_week2)

    def shoot_week2() -> None:
        path = out_dir / f"week-{theme_name}.png"
        win.grab().save(str(path))
        print("saved", path, path.stat().st_size)

        # 「正在连接飞书」是自绘动效，静态断言看不出来，必须留一张实拍。
        # 光弧转到哪个角度取决于等了多久，所以取两帧，好确认它真的在转。
        win._show_loading()
        app.processEvents()
        QTimer.singleShot(400, shoot_loading)
        QTimer.singleShot(700, shoot_loading_moved)

    def shoot_loading() -> None:
        path = out_dir / f"loading-{theme_name}.png"
        win.grab().save(str(path))
        print("saved", path, path.stat().st_size)

    def shoot_loading_moved() -> None:
        path = out_dir / f"loading-{theme_name}-b.png"
        win.grab().save(str(path))
        print("saved", path, path.stat().st_size)
        win.dispose()
        app.quit()

    QTimer.singleShot(2200, shoot)
    QTimer.singleShot(16000, app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
