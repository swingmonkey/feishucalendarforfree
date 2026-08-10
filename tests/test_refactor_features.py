"""重构后关键交互的离线回归测试（不依赖真实飞书/网络）。

覆盖：
- 月/周视图切换
- 重复日程展开
- 子任务 Markdown 勾选清单 往返（用于写回飞书描述）
- 拖拽改期 接线（调用 update_event 写回飞书）
- 一键登录按钮 按授权状态显隐
- 桌面快捷方式 创建逻辑
"""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

from PySide6.QtWidgets import QApplication


def test_refactor_features():
    # 应用单例
    app = QApplication.instance() or QApplication([])

    # 阻断真实 lark-cli / 网络 / 登录弹窗
    from lark_cli_async import LarkCliAsync
    import login_dialog
    update_calls = []

    def fake_fetch(self, current_date, monthly=True):
        self.agenda_fetched.emit([])

    LarkCliAsync.fetch_agenda = fake_fetch
    LarkCliAsync.update_event = lambda self, **kw: update_calls.append(kw)
    login_dialog.has_lark_auth = lambda: False

    from config import Config
    from main_window import MainWindow

    config = Config()
    w = MainWindow(config)
    w.show()
    assert hasattr(w, "min_btn") and w.min_btn.toolTip() == "最小化"
    assert hasattr(w, "login_btn")

    # 月/周切换
    w._set_view_mode("week")
    assert w.stack.currentIndex() == 1
    w._set_view_mode("month")
    assert w.stack.currentIndex() == 0

    # 重复日程展开
    from models_event import expand_events_for_range, has_recurrence
    base = datetime(2026, 8, 10, 9, 0, 0)
    evt = {
        "event_id": "evt_daily",
        "summary": "每日站会",
        "start_time": {"timestamp": str(int(base.timestamp())), "timezone": "Asia/Shanghai"},
        "end_time": {"timestamp": str(int((base + timedelta(hours=1)).timestamp())), "timezone": "Asia/Shanghai"},
        "recurrence": "FREQ=DAILY;COUNT=5",
    }
    assert has_recurrence(evt)
    occ = expand_events_for_range([evt], datetime(2026, 8, 1), datetime(2026, 8, 31, 23, 59, 59))
    rec = [e for e in occ if e.get("_is_recurring_instance")]
    assert len(rec) == 5 and all(e["_is_recurring_instance"] for e in rec)

    # 子任务 Markdown 往返
    from models_event import parse_task_list, rebuild_description
    desc = "会议说明\n\n- [ ] 准备材料\n- [x] 发送通知"
    tasks = parse_task_list(desc)
    assert tasks == [{"done": False, "text": "准备材料"}, {"done": True, "text": "发送通知"}]
    tasks[0]["done"] = True
    new_desc = rebuild_description(desc, tasks)
    assert "- [x] 准备材料" in new_desc and "会议说明" in new_desc
    assert parse_task_list(new_desc) == tasks

    # 拖拽改期 接线
    w.events = [{
        "event_id": "evt1", "organizer_calendar_id": "primary",
        "start_time": {"timestamp": str(int(datetime(2026, 8, 12, 10, 0).timestamp()))},
        "end_time": {"timestamp": str(int(datetime(2026, 8, 12, 11, 0).timestamp()))},
    }]
    w._on_reschedule("evt1", datetime(2026, 8, 15), "2026-08-12T10:00:00", "2026-08-12T11:00:00", False)
    assert update_calls, "拖拽改期未触发 update_event"
    call = update_calls[-1]
    assert call["event_id"] == "evt1" and call["start"].day == 15 and call["start"].hour == 10

    # 一键登录按钮 显隐
    login_dialog.has_lark_auth = lambda: True
    w._update_login_btn_visibility()
    assert not w.login_btn.isVisible()
    login_dialog.has_lark_auth = lambda: False
    w._update_login_btn_visibility()
    assert w.login_btn.isVisible()

    # 桌面快捷方式 逻辑（临时 home，不污染真实桌面）
    import shutil
    shutil.rmtree("/tmp/fake_home", ignore_errors=True)
    from main import _ensure_desktop_shortcut
    cfg = Config()
    cfg.set("desktop_shortcut_created", True)
    with mock.patch.object(Path, "home", return_value=Path("/tmp/fake_home")):
        _ensure_desktop_shortcut(cfg)
        assert not (Path("/tmp/fake_home") / "Desktop" / "飞书日程.lnk").exists()
    cfg2 = Config()
    cfg2.set("desktop_shortcut_created", False)
    fh = Path("/tmp/fake_home")
    (fh / "Desktop").mkdir(parents=True, exist_ok=True)
    with mock.patch.object(Path, "home", return_value=fh), mock.patch("sys.platform", "win32"):
        _ensure_desktop_shortcut(cfg2)
        assert (fh / "Desktop" / "飞书日程.lnk").exists()
        assert cfg2.get("desktop_shortcut_created") is True
