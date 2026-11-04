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
        # 今天必须有事：今日条和「今日」高亮都要有内容可看
        (4, 9, 30, 60, "运行监督管理"),
        (4, 15, 0, 45, "空管参考案例整理"),
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
        QTimer.singleShot(0, shoot_surfaces)

    def shoot_surfaces() -> None:
        """次级表面：今日条 + 四个对话框。

        这些地方没有自绘，QSS 一改就会变，但「变了什么」只能看图——
        尤其是配色是不是真的从主题令牌来的（切主题两张图必须不一样）。
        """
        from datetime import datetime as _dt

        from add_event_dialog import AddEventDialog
        from event_detail_dialog import EventDetailDialog
        from export_dialog import ExportDialog
        from ui_common import ConfirmDialog

        def save(widget, name: str) -> None:
            path = out_dir / f"{name}-{theme_name}.png"
            widget.grab().save(str(path))
            print("saved", path, path.stat().st_size)

        def save_over_backdrop(widget, name: str) -> None:
            """窄条是半透明玻璃，直接存是张透明图，看上去只是一块灰。

            先合成到台面底色上，才知道玻璃层、描边和圆角在真实桌面上是什么样。
            """
            from PySide6.QtGui import QColor, QPainter, QPixmap

            import theme

            shot = widget.grab()
            canvas = QPixmap(shot.size())
            canvas.fill(QColor(theme.tokens(theme_name)["bg"]))
            painter = QPainter(canvas)
            painter.drawPixmap(0, 0, shot)
            painter.end()
            path = out_dir / f"{name}-{theme_name}.png"
            canvas.save(str(path))
            print("saved", path, path.stat().st_size)

        # 今日条是独立顶层窗口，grab() 它自己，不吃主窗口的样式表
        win.config.set("today_bar_enabled", True)
        win._apply_today_bar()
        app.processEvents()
        bar = win._today_bar
        bar.set_events(win._today_events(), _dt.now())
        app.processEvents()
        save_over_backdrop(bar, "todaybar")
        win.config.set("today_bar_enabled", False)
        bar.hide()

        events = win._today_events() or []
        probe = events[0] if events else {
            "event_id": "probe",
            "summary": "塔台管制检查准备",
            "start_time": {"timestamp": str(int(_dt(2026, 11, 4, 10, 0).timestamp()))},
            "end_time": {"timestamp": str(int(_dt(2026, 11, 4, 11, 0).timestamp()))},
        }

        for name, dlg in (
            ("dlg-add", AddEventDialog(win.lark_cli, default_date=_dt.now(), config=win.config)),
            ("dlg-detail", EventDetailDialog(probe, config=win.config)),
            ("dlg-export", ExportDialog(events or [probe], _dt.now())),
            (
                "dlg-confirm",
                ConfirmDialog("删除日程", "确定要删除「塔台管制检查准备」吗？", danger=True),
            ),
        ):
            dlg.show()
            app.processEvents()
            save(dlg, name)
            dlg.deleteLater()

        # 设置窗：逐页截图（按钮/控件样式改动的重灾区，必须每页过目）
        from settings_dialog import SettingsDialog

        settings = SettingsDialog(win.config, parent=win)
        settings.show()
        app.processEvents()
        for i in range(settings.tabs.count()):
            settings.tabs.setCurrentIndex(i)
            app.processEvents()
            save(settings, f"dlg-settings-tab{i}")
        settings.deleteLater()

        win.dispose()
        app.quit()

    QTimer.singleShot(2200, shoot)
    QTimer.singleShot(20000, app.quit)
    app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
