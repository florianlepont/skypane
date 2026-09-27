"""Unit tests for the named steps `server/poll_cycle.py`'s run_once split
introduces (server/poll_cycle.py's CycleContext and its step functions):

  * decide_hold() - the pure battery_empty > display_off > quiet_hours
    precedence, isolated from any I/O
  * publish_canvas() - the one render -> pack -> write -> gallery
    sequence every former "publish copy" now shares
  * the live-path step call order and the hold path's own restricted
    call surface (added once detect_flight/load_display_slots/... exist)

Covers ARC-01's "the typed pure core" and "one publish path" truths.
Every assertion is a return value, a CycleContext field, or a gallery/
panel.bin write - never source text.
"""
import os

import pytest

import server.plane.render as render
import server.poll_cycle as poll_cycle


# --- decide_hold(): pure precedence, no I/O ---------------------------------


@pytest.mark.parametrize(
    "battery_critical, display_enabled, quiet_remaining, expected",
    [
        (True, False, 100, "battery_empty"),
        (False, False, 100, "display_off"),
        (False, True, 100, "quiet_hours"),
        (False, True, None, None),
        # quiet_remaining=0 is a real, non-None value - `is not None`
        # reads it the same as any other in-progress countdown.
        (False, True, 0, "quiet_hours"),
    ],
)
def test_decide_hold_precedence(battery_critical, display_enabled, quiet_remaining, expected):
    assert poll_cycle.decide_hold(battery_critical, display_enabled, quiet_remaining) == expected


def test_decide_hold_battery_empty_outranks_display_off_and_quiet_hours():
    """battery_critical=True wins even when display_off/quiet_hours would
    also independently apply - the flat-pack priority the module's own
    docstring describes."""
    assert poll_cycle.decide_hold(True, False, 100) == "battery_empty"


def test_decide_hold_display_off_outranks_quiet_hours():
    assert poll_cycle.decide_hold(False, False, 100) == "display_off"


# --- publish_canvas(): the one render -> pack -> write -> gallery path -----


def _ctx(state_dir, now_iso="2026-09-27T12:00:00+00:00"):
    return poll_cycle.CycleContext(
        state_dir=state_dir, snapshot=None, geofence=None, caddy_log=None, now_iso=now_iso)


def _gallery_pngs(state_dir):
    gallery_dir = os.path.join(state_dir, poll_cycle.GALLERY_DIRNAME)
    if not os.path.isdir(gallery_dir):
        return []
    return [name for name in os.listdir(gallery_dir) if name.endswith(".png")]


def test_publish_canvas_first_write_returns_true_and_writes_one_gallery_entry_named_from_now_iso(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir, now_iso="2026-09-27T08:30:00+00:00")
    canvas = render.build_canvas(None, "empty")

    changed = poll_cycle.publish_canvas(ctx, canvas)

    assert changed is True
    assert ctx.panel_changed is True
    assert os.path.exists(os.path.join(state_dir, "panel.bin"))
    assert _gallery_pngs(state_dir) == ["2026-09-27T08-30-00+00-00.png"]


def test_publish_canvas_unchanged_panel_returns_false_and_writes_no_new_gallery_entry(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir)
    canvas = render.build_canvas(None, "empty")

    poll_cycle.publish_canvas(ctx, canvas)  # first write: changed
    before = _gallery_pngs(state_dir)

    changed = poll_cycle.publish_canvas(ctx, canvas)  # identical canvas: unchanged

    assert changed is False
    assert ctx.panel_changed is False
    assert _gallery_pngs(state_dir) == before
    assert len(before) == 1


def test_publish_canvas_a_later_changed_canvas_still_returns_true(tmp_path):
    state_dir = str(tmp_path)
    ctx = _ctx(state_dir, now_iso="2026-09-27T09:00:00+00:00")
    empty_canvas = render.build_canvas(None, "empty")
    battery_empty_canvas = render.build_canvas(None, "battery_empty")

    poll_cycle.publish_canvas(ctx, empty_canvas)
    ctx.now_iso = "2026-09-27T09:05:00+00:00"

    changed = poll_cycle.publish_canvas(ctx, battery_empty_canvas)

    assert changed is True
    assert ctx.panel_changed is True
    assert len(_gallery_pngs(state_dir)) == 2
