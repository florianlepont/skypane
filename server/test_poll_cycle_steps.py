"""Unit tests for the named steps run_once's split introduces in
server/poll_cycle.py - CycleContext and its step functions:

  * decide_hold() - the pure battery_empty > display_off > quiet_hours
    precedence, isolated from any I/O
  * publish_canvas() - the one render -> pack -> write -> gallery
    sequence every former "publish copy" now shares
  * the live path's own step call order (detect_flight,
    load_display_slots, update_battery_low, advance_display_queue,
    render_and_publish, record, persist, log_cycle), and the hold path's
    restricted call surface (never detects, publishes at most once)

Every assertion is a return value, a CycleContext field, a recorded call
order, or a gallery/panel.bin write - never source text.
"""
import os

import pytest

import server.device_config as device_config
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


# --- live-path step order, and the hold path's restricted call surface -----


_LIVE_STEP_NAMES = (
    "detect_flight", "load_display_slots", "update_battery_low",
    "advance_display_queue", "render_and_publish", "record", "persist", "log_cycle",
)


def test_live_path_calls_its_named_steps_in_order(tmp_path, monkeypatch):
    """Spies on every live-path step (wrapping, never replacing, so
    behaviour still runs for real) and asserts the exact call order the
    module's own run_once() docstring promises."""
    order = []

    def _wrap(name):
        real = getattr(poll_cycle, name)

        def spy(*args, **kwargs):
            order.append(name)
            return real(*args, **kwargs)

        monkeypatch.setattr(poll_cycle, name, spy)

    for name in _LIVE_STEP_NAMES:
        _wrap(name)

    # An empty-sky snapshot (no live network call - detect_flight takes
    # the injected-snapshot path) still runs every live step once, ending
    # in the empty-state render branch on a fresh state_dir.
    poll_cycle.run_once(snapshot={}, state_dir=str(tmp_path))

    assert order == list(_LIVE_STEP_NAMES)


def test_hold_path_never_detects_and_publishes_at_most_once(tmp_path, monkeypatch):
    """The hold path (display_off here) must never touch detect_flight -
    an off period with no scheduled end must not query the aggregators
    unbounded - and repaints at most once per cycle (once on entry, never
    again on an unchanged repeat)."""
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, display_enabled=False)

    detect_calls = []
    monkeypatch.setattr(poll_cycle, "detect_flight", lambda ctx: detect_calls.append(ctx))

    publish_calls = []
    real_publish = poll_cycle.publish_canvas

    def _spy_publish(ctx, canvas):
        publish_calls.append(canvas)
        return real_publish(ctx, canvas)

    monkeypatch.setattr(poll_cycle, "publish_canvas", _spy_publish)

    poll_cycle.run_once(state_dir=state_dir)  # hold entry: repaints once
    poll_cycle.run_once(state_dir=state_dir)  # hold repeat: no boundary crossed

    assert detect_calls == []
    assert len(publish_calls) == 1
