"""悬停信息弹窗（hover_popover）：定位算法 / 单例 / 内容构建。

行为真源是 token-monitor 的 helpPopover.js + selectControl.js.popupPosition，
这里把「能算的部分」全部用纯数据钉死。
"""

import sys
from datetime import datetime, timedelta

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QLabel

import hover_popover as hp

app = QApplication.instance() or QApplication(sys.argv[:1])


# ── 定位算法 ────────────────────────────────────────────────────────────────


def _screen(h=800, w=1280):
    return QRect(0, 0, w, h)


def test_opens_below_by_default():
    anchor = QRect(600, 100, 80, 24)
    size = QRect(0, 0, 280, 120)
    pos, above = hp.popup_position(anchor, size, _screen())
    assert not above
    assert pos.y() == anchor.bottom() + hp.GAP
    # align='end'：右缘对齐锚点右缘
    assert pos.x() == anchor.right() - 280


def test_flips_above_when_below_cannot_fit():
    # 锚点贴近视口底部，下方放不下、上方宽裕
    anchor = QRect(600, 760, 80, 24)
    size = QRect(0, 0, 280, 120)
    pos, above = hp.popup_position(anchor, size, _screen(h=800))
    assert above
    assert pos.y() == anchor.top() - hp.GAP - 120


def test_stays_below_when_above_is_not_wider():
    # 下方放不下，但上方更局促：不翻转（对齐 popupPosition 的 above>below 条件）
    anchor = QRect(600, 100, 80, 24)
    size = QRect(0, 0, 280, 700)
    pos, above = hp.popup_position(anchor, size, _screen(h=800))
    assert not above


def test_horizontal_clamp_keeps_popover_on_screen():
    # 锚点右缘超出可容纳范围：右对齐会越界，必须夹回 gutter 内
    screen = _screen(w=1000)
    anchor = QRect(900, 100, 150, 24)  # right=1049，右对齐需要 x=769 > 上限 711
    size = QRect(0, 0, 280, 100)
    pos, _ = hp.popup_position(anchor, size, screen)
    assert pos.x() == screen.right() - 280 - hp.GUTTER
    assert pos.x() >= screen.left() + hp.GUTTER


def test_vertical_clamp_keeps_popover_on_screen():
    # 锚点在屏幕下部、弹层上下都放不下：不许越出屏幕（v2.11.0 之前
    # 只做水平夹取，弹层会被屏幕上下边缘裁掉一截——「日期显示不全」的
    # 另一种形态）
    screen = _screen(h=800)
    anchor = QRect(600, 700, 80, 24)
    size = QRect(0, 0, 280, 760)
    pos, above = hp.popup_position(anchor, size, screen)
    assert above
    assert pos.y() >= screen.top() + hp.GUTTER
    assert pos.y() + size.height() <= screen.bottom() + 1 - hp.GUTTER


def test_vertical_clamp_caps_below_opening():
    # 下方放不下且上方更局促：保持向下开，但底缘必须夹回屏幕内
    screen = _screen(h=800)
    anchor = QRect(600, 100, 80, 24)
    size = QRect(0, 0, 280, 700)
    pos, above = hp.popup_position(anchor, size, screen)
    assert not above
    assert pos.y() + size.height() <= screen.bottom() + 1 - hp.GUTTER


# ── 内容构建 ────────────────────────────────────────────────────────────────


def _event(**over):
    start = datetime(2026, 11, 4, 9, 0)
    ev = {
        "event_id": "e1",
        "summary": "塔台管制检查准备",
        "start_time": {"datetime": start.strftime("%Y-%m-%dT%H:%M:%S+08:00")},
        "end_time": {
            "datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S+08:00")
        },
        "location": {"name": "天府机场塔台"},
        "description": "梳理岗位培训与资质管理材料",
    }
    ev.update(over)
    return ev


def test_event_detail_widget_shows_key_fields():
    w = hp.event_detail_widget(_event(), "dark")
    texts = [lbl.text() for lbl in w.findChildren(QLabel)]
    joined = "\n".join(texts)
    assert "塔台管制检查准备" in joined
    assert "09:00" in joined and "10:00" in joined
    assert "天府机场塔台" in joined
    assert "梳理岗位培训与资质管理材料" in joined
    # 当天 09:00-11:00 的相对状态取决于当前时刻，只断言三选一
    assert any(s in joined for s in ("未开始", "进行中", "已结束"))


def test_event_detail_widget_all_day_and_long_desc_truncated():
    ev = _event(
        start_time={"date": "2026-11-04", "timezone": "UTC"},
        end_time={"date": "2026-11-04", "timezone": "UTC"},
        description="长" * 300,
    )
    w = hp.event_detail_widget(ev, "dark")
    joined = "\n".join(lbl.text() for lbl in w.findChildren(QLabel))
    assert "全天" in joined
    desc = next(t for t in joined.splitlines() if t.startswith("长"))
    assert desc.endswith("…") and len(desc) <= 161


def test_day_summary_widget_groups_and_limits():
    day = datetime(2026, 11, 4)
    events = [_event(event_id=f"e{i}", summary=f"日程{i}") for i in range(8)]
    w = hp.day_summary_widget(day, events, "dark")
    texts = [lbl.text() for lbl in w.findChildren(QLabel)]
    assert "11月04日 周三" in texts[0]
    assert any("还有 2 项日程" in t for t in texts)
    # 只列前 6 条
    titles = [t for t in texts if t.startswith("日程")]
    assert len(titles) == 6


def test_day_summary_widget_empty_state():
    w = hp.day_summary_widget(datetime(2026, 11, 4), [], "dark")
    texts = [lbl.text() for lbl in w.findChildren(QLabel)]
    assert "当天没有日程" in texts


# ── 日期完整性（v2.11.1：详情里日期显示不全的回归）─────────────────────────


def _joined(w) -> str:
    return "\n".join(lbl.text() for lbl in w.findChildren(QLabel))


def test_event_detail_all_day_range_shows_end_date():
    # 多天全天日程只显示开始日期 = 「日期显示不全」，结束日期必须带上
    y = datetime.now().year
    ev = _event(start_time={"date": f"{y}-11-04"}, end_time={"date": f"{y}-11-06"})
    assert "11月04日 – 11月06日 · 全天" in _joined(hp.event_detail_widget(ev, "dark"))


def test_event_detail_single_day_all_day_unchanged():
    y = datetime.now().year
    ev = _event(start_time={"date": f"{y}-11-04"}, end_time={"date": f"{y}-11-04"})
    assert "11月04日 · 全天" in _joined(hp.event_detail_widget(ev, "dark"))


def test_event_detail_cross_day_timed_shows_both_dates():
    y = datetime.now().year
    ev = _event(
        start_time={"datetime": f"{y}-11-04T14:00:00+08:00"},
        end_time={"datetime": f"{y}-11-05T15:30:00+08:00"},
    )
    assert "11月04日 14:00 – 11月05日 15:30" in _joined(hp.event_detail_widget(ev, "dark"))


def test_event_detail_cross_year_date_includes_year():
    # 跨年日程只写「01月05日」无法与今年区分，必须补年份
    y = datetime.now().year + 1
    ev = _event(
        start_time={"datetime": f"{y}-01-05T14:00:00+08:00"},
        end_time={"datetime": f"{y}-01-05T15:30:00+08:00"},
    )
    assert f"{y}年01月05日 14:00 – 15:30" in _joined(hp.event_detail_widget(ev, "dark"))


def test_event_detail_cross_year_range_marks_both_ends():
    # 12月30日 → 1月2日：起点今年、终点跨年，两端都要能区分
    y = datetime.now().year
    ev = _event(
        start_time={"datetime": f"{y}-12-30T14:00:00+08:00"},
        end_time={"datetime": f"{y + 1}-01-02T15:30:00+08:00"},
    )
    joined = _joined(hp.event_detail_widget(ev, "dark"))
    assert f"{y}年12月30日 14:00 – {y + 1}年01月02日 15:30" in joined


def test_day_summary_title_includes_year_for_other_year():
    y = datetime.now().year + 1
    w = hp.day_summary_widget(datetime(y, 1, 5), [], "dark")
    assert f"{y}年01月05日 周二" in w.findChildren(QLabel)[0].text()


# ── 单例与延迟关闭 ─────────────────────────────────────────────────────────


def test_show_for_is_singleton(monkeypatch, qtbot=None):
    from PySide6.QtWidgets import QWidget

    a = QWidget()
    b = QWidget()
    a.resize(60, 20)
    b.resize(60, 20)
    a.show()
    b.show()
    try:
        hp.show_for(a, QLabel("A"), "dark")
        app.processEvents()
        first = hp._ACTIVE
        assert first is not None and first.isVisible()

        hp.show_for(b, QLabel("B"), "dark")
        app.processEvents()
        assert hp._ACTIVE is not first
        assert hp._ACTIVE.isVisible()
    finally:
        hp._close_active()
        a.deleteLater()
        b.deleteLater()
        app.processEvents()


def test_schedule_close_then_cancel():
    from PySide6.QtWidgets import QWidget

    a = QWidget()
    a.resize(60, 20)
    a.show()
    try:
        hp.show_for(a, QLabel("A"), "dark")
        app.processEvents()
        hp.schedule_close(delay_ms=10)
        hp.cancel_close()
        app.processEvents()
        assert hp._ACTIVE is not None  # 被取消，没有关
        hp._close_active()
    finally:
        a.deleteLater()
        app.processEvents()


# ── 打开延迟计时器（v2.11.3 回归）───────────────────────────────────────────
# 用户报告：快速划过月历时弹层会凭空出现且关不掉。


def test_schedule_close_cancels_pending_open():
    """延迟期内鼠标已离开：待触发的打开计时器必须撤销。

    否则弹层在鼠标离开后才弹出，而此时鼠标不在弹层上，不会再有 leave
    事件来关闭它——弹层会一直挂着。
    """
    from PySide6.QtWidgets import QWidget

    anchor = QWidget()
    anchor.show()
    hp.show_for(anchor, QLabel("内容"), "dark", delay_ms=5000)
    assert hp._OPEN_TIMER is not None
    hp.schedule_close()
    assert hp._OPEN_TIMER is None
    hp.cancel_close()
    anchor.deleteLater()


def test_is_alive_false_after_anchor_destroyed():
    """延迟期间日格被重建销毁：_open 不得再访问已删除的 C++ 对象。"""
    import shiboken6
    from PySide6.QtWidgets import QWidget

    anchor = QWidget()
    anchor.show()
    assert hp._is_alive(anchor) is True
    shiboken6.delete(anchor)
    assert hp._is_alive(anchor) is False
