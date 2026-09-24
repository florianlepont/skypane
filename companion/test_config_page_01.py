"""Part 01 of the `companion/test_config_page.py` migration chain
(33-09-PLAN.md): the original harness's `check()` calls #1-#33, covering
`companion.pages.config_page`'s render() group layout, led_group(),
quiet_hours_group() (markup, field order, escaping, the three time
presets), wake_interval_group() (markup, value-attribute contract,
render() placement/prefill), handle_post()'s display_enabled/quiet_hours
resolution and its theme-only-save regression guard, the settings form's
class hooks, the Aspect card's per-theme palette rendering, and
runway_fieldset()'s cards/escaping/photograph survival.

Every check calls `companion.pages.config_page`'s own functions directly,
in-process, against a `tmp_path`-backed state directory — none of this
slice needs a running `companion/app.py` server. The original harness's
self-referential aspect-repin bookkeeping guard (the first `check()` call
in this slice, which opened the legacy harness's own source to grep def
names) is DELETED, not ported: it asserts plan-history bookkeeping, not
application behaviour (R, 33-MIGRATION-RULES.md section 3).
"""
import contextlib
import re

import companion.pages.config_page as config_page
import companion.test_config_page_helpers as cp
from companion.layout import escape_html
from server import device_config
from server.plane import colour_rules


# ======================================================================
# Section 1: render()'s group layout, led_group(), quiet_hours_group()
# (markup/order/escaping/presets), wake_interval_group() (markup/value
# contract/render() placement).
# ======================================================================


def test_render_emits_no_fieldset_or_legend_five_groups_three_runway_cards_and_save_button():
    """render() emits no <fieldset>/<legend> and no .theme-chip-grid on this legacy SCOPE_ALL
    render (Theme's card retired outright, D-01/21-05-PLAN.md Task 1 D-06), five
    theme-status-wrapped groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications
    — Display's own card retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1), three
    runway-card labels, and a Save settings submit button"""
    ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx)
    assert "<fieldset" not in rendered
    assert "<legend" not in rendered
    assert rendered.count('class="theme-status"') == 5
    assert "theme-chip-grid" not in rendered
    assert rendered.count('<label class="runway-card') == 3
    assert "Save settings" in rendered


def test_led_group_carries_the_switch_and_its_state_attribute_sequence():
    """led_group() emits the switch and preserves its class/role/aria-checked attribute sequence
    in both states, with the retired settings-checkbox label gone (retargeted in place from
    the checkbox's own sequence by 23-07-PLAN.md Task 2)"""
    checked_html = config_page.led_group(True)
    unchecked_html = config_page.led_group(False)
    assert 'class="settings-checkbox"' not in checked_html
    for name, rendered, expected_state in (
            ("led_group(True)", checked_html, "true"),
            ("led_group(False)", unchecked_html, "false")):
        expected = 'class="switch" role="switch" aria-checked="%s"' % expected_state
        assert rendered.count(expected) == 1, "expected %s to carry exactly one %r" % (name, expected)
        assert rendered.count('class="switch__thumb"') == 1
    assert 'aria-checked="true"' not in unchecked_html


def test_quiet_hours_group_markup_no_checkbox_and_time_inputs():
    """quiet_hours_group() renders no on/off checkbox at all any more (the Frame strip is the only
    control left, 22-05-PLAN.md Task 1 X1/D-04/D-12.1), one type="time" input each for Start/End
    with their current values, no theme-status__row, and no disabled attribute"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    assert 'name="quiet_hours_enabled"' not in rendered
    assert "settings-checkbox" not in rendered
    assert 'name="quiet_hours_start"' in rendered and 'type="time"' in rendered
    assert 'value="23:00"' in rendered
    assert 'name="quiet_hours_end"' in rendered
    assert 'value="07:00"' in rendered
    assert "checked" not in rendered
    assert "theme-status__row" not in rendered
    assert "disabled" not in rendered


def test_quiet_hours_group_field_order_heading_caption_start_end():
    """quiet_hours_group()'s field order is heading, then caption, then Start, then End, in document
    order — the enable checkbox this order used to include is retired outright (22-05-PLAN.md
    Task 1, X1/D-04/D-12.1)"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    heading_close = rendered.index("</h2>")
    caption_pos = rendered.index("section-caption")
    start_pos = rendered.index('name="quiet_hours_start"')
    end_pos = rendered.index('name="quiet_hours_end"')
    assert heading_close < caption_pos < start_pos < end_pos


def test_quiet_hours_group_escapes_crafted_current_values():
    """quiet_hours_group() escapes a crafted current_start value — no raw <script> substring
    reaches the markup"""
    rendered = config_page.quiet_hours_group('"><script>', "07:00")
    assert "<script>" not in rendered


def test_quiet_hours_group_renders_exactly_three_button_presets():
    """quiet_hours_group() renders exactly three data-quiet-preset <button type="button">
    elements"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    assert rendered.count(config_page.QUIET_HOURS_PRESET_ATTR) == 3
    preset_buttons = re.findall(
        r'<button\b[^>]*%s[^>]*>' % re.escape(config_page.QUIET_HOURS_PRESET_ATTR), rendered)
    assert len(preset_buttons) == 3
    for button_html in preset_buttons:
        assert 'type="button"' in button_html


def test_quiet_hours_group_night_preset_matches_device_config_defaults():
    """the Night preset's data-preset-start/data-preset-end equal server.device_config's
    DEFAULT_QUIET_HOURS_START/DEFAULT_QUIET_HOURS_END"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    expected = 'data-preset-start="%s" data-preset-end="%s"' % (
        device_config.DEFAULT_QUIET_HOURS_START, device_config.DEFAULT_QUIET_HOURS_END)
    assert expected in rendered


def test_quiet_hours_group_workday_preset_carries_expected_times():
    """the Work day preset carries data-preset-start="08:00" data-preset-end="18:00\""""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    assert 'data-preset-start="08:00" data-preset-end="18:00"' in rendered


def test_quiet_hours_group_always_on_preset_disables_with_no_time_attrs():
    """the Always-on preset carries data-preset-enabled="0" and no data-preset-start/
    data-preset-end attributes"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    always_on_match = re.search(r'<button\b[^>]*data-preset-enabled="0"[^>]*>', rendered)
    assert always_on_match, "expected exactly one button carrying data-preset-enabled=\"0\""
    button_html = always_on_match.group(0)
    assert "data-preset-start" not in button_html and "data-preset-end" not in button_html


def test_quiet_hours_group_preset_row_between_caption_and_time_inputs():
    """the preset button row appears after the section caption and before the first
    type="time" input (D-14's locked position, retargeted by 22-05-PLAN.md Task 1 now that
    the checkbox it used to follow is gone)"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    caption_pos = rendered.index("section-caption")
    preset_pos = rendered.index(config_page.QUIET_HOURS_PRESET_ATTR)
    time_pos = rendered.index('type="time"')
    assert caption_pos < preset_pos < time_pos


def test_handle_post_preset_filled_submission_treated_identically_to_hand_typed(tmp_path):
    """handle_post() persists a Night-preset-shaped submission (quiet_hours_start/end equal to
    device_config's own defaults) exactly as it would a hand-typed value - no new server code
    path (T-19-38)"""
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post(
        {
            "quiet_hours_enabled": config_page.QUIET_HOURS_CHECKBOX_VALUE,
            "quiet_hours_start": config_page.QUIET_HOURS_PRESET_NIGHT_START,
            "quiet_hours_end": config_page.QUIET_HOURS_PRESET_NIGHT_END,
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVED
    on_disk = device_config.load_device_config(str(tmp_path))
    assert on_disk["quiet_hours_start"] == config_page.QUIET_HOURS_PRESET_NIGHT_START
    assert on_disk["quiet_hours_end"] == config_page.QUIET_HOURS_PRESET_NIGHT_END


def test_render_wires_quiet_hours_group_after_led_before_save_button():
    """render() wires quiet_hours_group() with the saved current values, positioned after
    Diagnostic LED and before the Save settings button"""
    rendered = config_page.render({
        "device_config": {
            "theme": "black", "tracked_runway": "3", "led_enabled": True,
            "quiet_hours_enabled": True, "quiet_hours_start": "22:30",
            "quiet_hours_end": "06:15",
        },
        "poll_cooldown_remaining": 0,
    })
    assert 'value="22:30"' in rendered and 'value="06:15"' in rendered
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): no scope renders a
    # quiet_hours_enabled checkbox any more; the Frame strip is the only
    # on/off control left.
    assert 'name="quiet_hours_enabled"' not in rendered
    led_heading_pos = rendered.index(config_page.LED_SECTION_HEADING)
    quiet_heading_pos = rendered.index(config_page.QUIET_HOURS_SECTION_HEADING)
    save_button_pos = rendered.index("Save settings")
    assert led_heading_pos < quiet_heading_pos < save_button_pos


def test_wake_interval_group_markup_in_range_value():
    """wake_interval_group(120) emits one .theme-status[data-dirty-section] wrapper, the locked
    heading/caption, one type="number" input with min/max from device_config and the locked
    placeholder and a matching value, and none of <fieldset>/<legend>/settings-checkbox"""
    rendered = config_page.wake_interval_group(120)
    assert rendered.count('class="theme-status"') == 1
    assert config_page.DIRTY_SECTION_ATTR in rendered
    expected_heading = (
        '<h2 class="text-heading">%s</h2>' % escape_html(config_page.WAKE_INTERVAL_SECTION_HEADING))
    assert rendered.count(expected_heading) == 1
    # 19-11-PLAN.md Task 3 (D-12/A-30): the caption carries its own id
    # (the number input's aria-describedby target).
    expected_caption = (
        '<p class="text-label section-caption" id="%s">%s</p>'
        % (
            escape_html(config_page.WAKE_INTERVAL_SECTION_CAPTION_ID),
            escape_html(config_page.WAKE_INTERVAL_SECTION_CAPTION)))
    assert rendered.count(expected_caption) == 1
    expected_input = (
        '<input type="number" id="%s" name="wake_interval_s"' % config_page.WAKE_INTERVAL_INPUT_ID)
    assert rendered.count(expected_input) == 1
    assert 'min="%d"' % device_config.WAKE_INTERVAL_MIN_S in rendered
    assert 'max="%d"' % device_config.WAKE_INTERVAL_MAX_S in rendered
    assert 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT in rendered
    assert 'value="120"' in rendered
    assert "<fieldset" not in rendered
    assert "<legend" not in rendered
    assert "settings-checkbox" not in rendered


def test_wake_interval_group_value_attribute_only_for_in_range_non_bool_int():
    """wake_interval_group() emits a value attribute only for an in-range, non-bool int
    (None/True/False/a str/30/59/3601/7200 all emit none; 60/3600/120 each emit theirs) — an
    out-of-range or wrong-typed value would fail native constraint validation and block the
    whole form"""
    no_value_cases = (None, True, False, "120", 30, 59, 3601, 7200)
    for case in no_value_cases:
        assert "value=" not in config_page.wake_interval_group(case), (
            "expected wake_interval_group(%r) to emit no value attribute" % (case,))
    for case, expected in ((60, 60), (3600, 3600), (120, 120)):
        rendered = config_page.wake_interval_group(case)
        assert 'value="%d"' % expected in rendered


def test_render_places_wake_interval_last_and_resolves_prefill():
    """render() places Wake interval last in the locked five-group order, resolves no value
    attribute when neither source is present, prefers an on-disk wake_interval_s over
    ctx['wake_interval_env_default'], and falls back to the ctx default when the on-disk value
    is None"""
    base_ctx = {
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(base_ctx)
    # 21-05-PLAN.md Task 1 (D-06): "Theme" no longer renders anywhere on
    # this legacy SCOPE_ALL page — dropped from this locked-order list.
    headings = [
        "Runway", config_page.LED_SECTION_HEADING,
        config_page.QUIET_HOURS_SECTION_HEADING,
        config_page.WAKE_INTERVAL_SECTION_HEADING,
    ]
    positions = [rendered.index(h) for h in headings]
    assert positions == sorted(positions)
    assert "value=" not in rendered.split('name="wake_interval_s"')[1].split(">")[0]

    on_disk_ctx = dict(base_ctx)
    on_disk_ctx["device_config"] = dict(base_ctx["device_config"], wake_interval_s=180)
    on_disk_ctx["wake_interval_env_default"] = 900
    rendered = config_page.render(on_disk_ctx)
    assert 'value="180"' in rendered

    fallback_ctx = dict(base_ctx)
    fallback_ctx["wake_interval_env_default"] = 900
    rendered = config_page.render(fallback_ctx)
    assert 'value="900"' in rendered


def test_no_page_and_no_scope_renders_a_display_or_quiet_hours_on_off_checkbox(tmp_path):
    """X1/D-04: no settings render (legacy SCOPE_ALL, Display, Device) carries a display_enabled
    or quiet_hours_enabled input any more — the Frame strip is the only on/off control for either
    setting (22-05-PLAN.md Task 1, superseding 12-05-PLAN.md/10-05-PLAN.md's own checkbox markup)"""
    base_ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
    }
    legacy = config_page.render(base_ctx)
    display = config_page.render(base_ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(base_ctx, scope=config_page.SCOPE_DEVICE)
    for rendered, name in ((legacy, "legacy"), (display, "display"), (device, "device")):
        assert 'name="display_enabled"' not in rendered, (
            "expected no display_enabled input on the %s render" % (name,))
        assert 'name="quiet_hours_enabled"' not in rendered, (
            "expected no quiet_hours_enabled input on the %s render" % (name,))
