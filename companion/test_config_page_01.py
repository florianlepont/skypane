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
import json
import os
import re

import companion.i18n as i18n
import companion.pages.config_page as config_page
import companion.test_config_page_helpers as cp
from companion.layout import escape_html
from server import device_config
from server.plane import colour_rules

HERE = os.path.dirname(os.path.abspath(__file__))


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


def test_no_js_floor_holds_on_display_and_device_after_the_checkbox_removal(tmp_path):
    """D-09's no-JS floor holds at this plan's own commit: scripts-blocked Display and Device
    renders each carry a reachable fallback Save button, form="settings-form"-ASSOCIATED with a
    plain server-rendered form (relocated into the restored .dirty-bar by 28-08-PLAN.md Task 1,
    CFG-77/CFG-78 — never a literal descendant of the form any more, and native submission is
    unchanged in substance either way), and a plain (no-JS) POST still round-trips the Quiet
    hours schedule"""
    base_ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
    }
    for scope in (config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
        rendered = config_page.render(base_ctx, scope=scope)
        assert config_page.STATIC_SAVE_FALLBACK_ATTR in rendered
        assert '<form class="config-form"' in rendered
    # A save posted without any script (a plain, URL-encoded POST body,
    # exactly what a no-JS browser submits) still round-trips the Quiet
    # hours schedule — the one control this plan leaves on the Display
    # page for this setting.
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post(
        {"scope": "display", "quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}, ctx)
    assert flash_key == config_page.FLASH_SAVED
    on_disk = device_config.load_device_config(str(tmp_path))
    assert on_disk["quiet_hours_start"] == "22:15" and on_disk["quiet_hours_end"] == "06:45"


def test_handle_post_display_enabled_three_shapes(tmp_path):
    """handle_post() resolves display_enabled through all three shapes: absent LEAVES the stored
    value unchanged (D-12.1, retargeted from the pre-22-05 absent-means-False bug),
    DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key
    and leaves a pre-existing device_config.json byte-identical"""
    absent_dir = tmp_path / "absent"
    device_config.save_device_config(str(absent_dir), display_enabled=True)
    flash_key = config_page.handle_post({"theme": "black"}, {"state_dir": str(absent_dir)})
    assert flash_key == config_page.FLASH_SAVED
    on_disk = device_config.load_device_config(str(absent_dir))
    assert on_disk["display_enabled"] is True, (
        "expected an absent display_enabled to LEAVE the stored True value unchanged")

    explicit_dir = tmp_path / "explicit"
    flash_key = config_page.handle_post(
        {"display_enabled": config_page.DISPLAY_CHECKBOX_VALUE}, {"state_dir": str(explicit_dir)})
    assert flash_key == config_page.FLASH_SAVED
    on_disk = device_config.load_device_config(str(explicit_dir))
    assert on_disk["display_enabled"] is True

    crafted_dir = tmp_path / "crafted"
    cp.write_device_config(crafted_dir, "black", "3", led_enabled=True)
    config_path = device_config.device_config_path(str(crafted_dir))
    with open(config_path, "r") as fh:
        doc = json.load(fh)
    doc["display_enabled"] = True
    with open(config_path, "w") as fh:
        json.dump(doc, fh)
    before = open(config_path, "rb").read()
    flash_key = config_page.handle_post({"display_enabled": "<crafted>"}, {"state_dir": str(crafted_dir)})
    after = open(config_path, "rb").read()
    assert flash_key == config_page.FLASH_SAVE_FAILED
    assert before == after


def test_handle_post_theme_only_save_never_flips_display_quiet_hours_or_led_off(tmp_path):
    """REGRESSION GUARD (T-22-16/T-23-25, 22-RESEARCH.md Pitfall 1): a settings save that only
    changes the theme leaves display_enabled, quiet_hours_enabled AND led_enabled EXACTLY as
    they were, across all eight starting True/False combinations — extended in place from the
    two-flag/four-combination version 22-05 landed, never duplicated beside it"""
    for i, (start_display, start_quiet, start_led) in enumerate((
            (True, True, True), (True, True, False),
            (True, False, True), (True, False, False),
            (False, True, True), (False, True, False),
            (False, False, True), (False, False, False))):
        case_dir = tmp_path / str(i)
        device_config.save_device_config(
            str(case_dir), display_enabled=start_display, quiet_hours_enabled=start_quiet,
            led_enabled=start_led)
        flash_key = config_page.handle_post({"theme": "white"}, {"state_dir": str(case_dir)})
        assert flash_key == config_page.FLASH_SAVED
        on_disk = device_config.load_device_config(str(case_dir))
        assert on_disk["display_enabled"] is start_display, (
            "REGRESSION (T-22-16): a theme-only save flipped display_enabled")
        assert on_disk["quiet_hours_enabled"] is start_quiet, (
            "REGRESSION (T-22-16): a theme-only save flipped quiet_hours_enabled")
        assert on_disk["led_enabled"] is start_led, (
            "REGRESSION (T-22-16/T-23-25): a theme-only save flipped led_enabled — the LED's "
            "control is a /quick/led switch now, so its absence from a settings body means "
            "'this form never had a way to change it', not 'the user unticked a box' (D-12.1)")
        assert on_disk["theme"] == "white"


def test_every_settings_group_is_named_exactly_once():
    """all four Config settings groups (Theme/Runway/Diagnostic LED/Poll) are named exactly
    once, all via the shared <h2 class="text-heading"> role, with zero <legend> and zero
    <fieldset> anywhere on the page (06.6.4.1.1-05, D-01)"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx)
    # 19-11-PLAN.md Task 3 / 23-07-PLAN.md Task 2: Runway's and Diagnostic
    # LED's own <h2> each carry an id (an aria-labelledby target); "Theme"
    # is retired from this list along with theme_fieldset() (21-05-PLAN.md
    # Task 1, D-06) — its replacement only ever renders on the Display scope.
    heading_ids = {
        "Runway": config_page.RUNWAY_GROUP_HEADING_ID,
        "Diagnostic LED": config_page.QUICK_LED_LABEL_ID,
    }
    for name in ("Runway", "Diagnostic LED", config_page.POLL_SECTION_HEADING):
        heading_id = heading_ids.get(name)
        if heading_id:
            heading = '<h2 class="text-heading" id="%s">%s</h2>' % (escape_html(heading_id), name)
        else:
            heading = '<h2 class="text-heading">%s</h2>' % name
        assert rendered.count(heading) == 1
    assert "<legend" not in rendered
    assert "<fieldset" not in rendered
    assert '<p class="text-label">Theme</p>' not in rendered, (
        "the Theme group must not be named twice via the superseded text-label paragraph")


def test_render_opens_with_shared_page_header():
    """Settings opens with the shared layout.page_header() component, not a bare <h1>"""
    rendered = config_page.render({
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert '<h1 class="page-title">Settings</h1>' in rendered
    assert '<h1 class="text-heading">' not in rendered


def test_settings_form_carries_config_form_class_hook():
    """the settings form keeps the stable config-form class hook the desktop two-column
    fieldset layout targets"""
    rendered = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert 'class="config-form"' in rendered
    expected_tag = (
        '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        % (config_page.SETTINGS_FORM_ID, config_page.SETTINGS_ROUTE))
    assert expected_tag in rendered
    assert rendered.count('<form class="config-form"') == 1


def test_aspect_card_covers_every_registered_theme_with_own_id_and_label():
    """the Aspect card's three palettes each render one radio per registered theme, in registry
    order, each carrying its own registry id/translated label/data-preview-src and
    form=settings-form, with arrivals/calendar carrying exactly one leading Same-as-departures
    option and departures exactly zero (D-06, 30-05-PLAN.md Task 1, replacing the retired
    frame-colours-card version of this check)"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    theme_ids = device_config.THEME_IDS
    assert theme_ids, "THEME_IDS is empty - nothing to render"
    for field_name, leading_expected in (
            ("theme", 0), ("theme_arriving", 1), ("calendar_theme_id", 1)):
        radio_values = re.findall(
            r'name="%s" value="([^"]*)" class="visually-hidden"' % re.escape(field_name), rendered)
        real_ids = [rid for rid in radio_values if rid]
        leading_count = len(radio_values) - len(real_ids)
        assert leading_count == leading_expected
        assert real_ids == list(theme_ids)
        total = len(radio_values)
        with_form = len(re.findall(
            r'name="%s" value="[^"]*" class="visually-hidden"( form="%s")'
            % (re.escape(field_name), re.escape(config_page.SETTINGS_FORM_ID)), rendered))
        assert with_form == total
    for theme_id in theme_ids:
        assert 'value="%s"' % escape_html(theme_id) in rendered
        label_needle = escape_html(i18n.t(device_config.theme_label(theme_id)))
        assert label_needle in rendered
        preview_needle = 'data-preview-src="%s%s.png?live=1"' % (
            config_page.THEME_PREVIEW_ROUTE_PREFIX, theme_id)
        assert preview_needle in rendered


def test_aspect_card_default_selects_exactly_the_white_departures_option():
    """the Aspect card rendered with the default theme id marks exactly the White chip selected
    in the departures palette, and exactly the leading Same-as-departures option selected in the
    arrivals/calendar palettes, each asserted per group (D-06/D-07, 30-05-PLAN.md Task 1,
    replacing the retired frame-colours-card version of this check)"""
    rendered = config_page.render({
        "device_config": {"theme": device_config.DEFAULT_THEME_ID, "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    for field_name, expected_value in (
            ("theme", device_config.DEFAULT_THEME_ID),
            ("theme_arriving", ""),
            ("calendar_theme_id", "")):
        checked = re.findall(
            r'name="%s" value="([^"]*)" class="visually-hidden"[^>]*checked' % re.escape(field_name),
            rendered)
        assert checked == [expected_value]


def test_runway_fieldset_exactly_three_radios():
    """runway_fieldset() emits exactly three runway radio inputs"""
    rendered = config_page.runway_fieldset("3")
    assert rendered.count('name="tracked_runway"') == 3


def test_runway_fieldset_cards_visually_hidden_radio_and_selected_class():
    """runway_fieldset('3') renders three selectable cards, each wrapping a visually-hidden
    radio, with only the '3' card selected (D-05)"""
    rendered = config_page.runway_fieldset("3", images_available=())
    assert rendered.count('<label class="runway-card') == 3
    assert rendered.count("runway-card--selected") == 1
    # Polish fix 4 (D-14c): each radio also carries form="settings-form",
    # inserted between class="visually-hidden" and checked.
    assert (
        'value="3" class="visually-hidden" form="%s" checked' % config_page.SETTINGS_FORM_ID
        in rendered)
    assert "display:none" not in rendered and "display: none" not in rendered
    assert rendered.count('class="visually-hidden"') >= 3


def test_runway_fieldset_cards_image_rendering_per_card():
    """runway_fieldset('3', images_available=('3', '06-24')) renders an <img> inside exactly
    those two cards, none in the third (D-05)"""
    rendered = config_page.runway_fieldset("3", images_available=("3", "06-24"))
    assert rendered.count("<img") == 2
    assert "/runway-image/3.png" in rendered and "/runway-image/06-24.png" in rendered
    assert "/runway-image/02-20.png" not in rendered


def test_palette_swatch_html_matches_the_live_registry_band_facts():
    """_palette_swatch_html() draws exactly the registry-derived 5-of-18 banded themes with a
    band child, renders a plain theme as one solid <span> with no opacity, and space-joins
    extra_class onto its class attribute (CFG-85)"""
    # 30-02-PLAN.md Task 1: derived from the live registry at check time,
    # never restated as a literal count.
    banded = [
        theme_id for theme_id in device_config.THEME_IDS
        if "palette-swatch__band" in config_page._palette_swatch_html(theme_id)
    ]
    expect_banded = [
        theme_id for theme_id in device_config.THEME_IDS
        if "band_index" in device_config.THEMES[theme_id]
        and device_config.THEMES[theme_id]["band_index"] != device_config.THEMES[theme_id]["departing_index"]
    ]
    assert banded == expect_banded
    white_html = config_page._palette_swatch_html("white")
    assert white_html.count("<span") == 1
    grey_html = config_page._palette_swatch_html("grey")
    assert "opacity" not in grey_html, (
        "expected a dithered theme's swatch to carry NO opacity style (the swatch rendering "
        "contract)")
    assert 'class="palette-swatch"' in white_html
    extra_html = config_page._palette_swatch_html("white", extra_class="usage-row__swatch")
    assert 'class="palette-swatch usage-row__swatch"' in extra_html
    field_html = config_page._palette_swatch_html("band_blue_field")
    assert "palette-swatch__band" not in field_html, (
        "band_blue_field has departing_index == band_index in the live registry and must "
        "render SOLID, not banded")


def test_palette_grid_html_renders_one_chip_per_registered_theme_in_order_no_photo():
    """_palette_grid_html() renders one chip per registered theme in device_config.THEME_IDS
    order, zero <img>, data-preview-src and form="settings-form" on every chip, exactly one
    selected check glyph, leading_html before the chips, and no id attribute of its own
    (CFG-85)"""
    g = config_page._palette_grid_html("theme", "red", radio_form_id=config_page.SETTINGS_FORM_ID)
    ids = re.findall(r'<input type="radio" name="theme" value="([^"]+)"', g)
    assert ids == list(device_config.THEME_IDS)
    assert g.count("<img") == 0
    # Count the OUTER swatch wrapper specifically (aria-hidden="true") —
    # the literal "palette-swatch" alone would double-count a banded
    # chip's own band-child class.
    outer_swatch_count = g.count('aria-hidden="true" style="background:')
    assert outer_swatch_count == len(device_config.THEME_IDS)
    preview_src_count = g.count('data-preview-src="%s' % config_page.THEME_PREVIEW_ROUTE_PREFIX)
    assert preview_src_count == len(device_config.THEME_IDS)
    form_attr_count = g.count('form="settings-form"')
    assert form_attr_count == len(device_config.THEME_IDS)
    selected_needle = 'value="red" class="visually-hidden" form="settings-form" checked'
    assert g.count(selected_needle) == 1 and g.count(" checked") == 1
    assert g.count("palette-chip__check") == 1
    lead = config_page._palette_grid_html(
        "theme_arriving", None, leading_html="<label id=LEAD></label>")
    assert lead.index("LEAD") < lead.index("palette-chip")
    assert ' id="' not in re.sub(r'data-preview-src="[^"]*"', "", g), (
        "expected _palette_grid_html() to emit no id attribute of its own - three call sites on "
        "one page sharing an id is the exact CFG-68 collision trap")


def test_usage_row_summary_html_joins_row_label_and_meta_with_one_em_dash_source():
    """_usage_row_summary_html() renders a well-formed <summary> joining the translated row
    label and meta text via ASPECT_ROW_SUMMARY_TEMPLATE's single em-dash source, and renders no
    swatch at all when theme_id is None (the rules row) (CFG-85)"""
    s = config_page._usage_row_summary_html(config_page.COLOUR_USAGE_DEPARTURES, "red")
    assert s.startswith("<summary") and s.rstrip().endswith("</summary>")
    assert "usage-row__swatch" in s and "usage-row__name" in s and "usage-row__meta" in s
    assert "Departures" in s and "Red" in s
    assert "—" in s, "expected the em-dash join from ASPECT_ROW_SUMMARY_TEMPLATE"
    s_rules = config_page._usage_row_summary_html(
        config_page.COLOUR_USAGE_RULES, None, meta_text="No rules yet")
    assert "usage-row__swatch" not in s_rules, (
        "expected the rules row (theme_id=None) to render NO swatch element at all")
    assert "No rules yet" in s_rules


@contextlib.contextmanager
def _temporary_registry(entries):
    """Swap device_config.RUNWAYS/RUNWAY_IDS for `entries` and put them back. A context manager
    rather than a try/finally at each call site: this fixture mutates a module-level registry
    every other check in this file reads, and one missed restore would make an unrelated
    neighbour fail in a way nobody would trace back to here. Used only by the one check below
    that needs a hostile registry entry to swap in."""
    was_runways = device_config.RUNWAYS
    was_ids = device_config.RUNWAY_IDS
    device_config.RUNWAYS = entries
    device_config.RUNWAY_IDS = tuple(entries)
    try:
        yield
    finally:
        device_config.RUNWAYS = was_runways
        device_config.RUNWAY_IDS = was_ids


def _runway_entry(label):
    return {"label": label, "tag_text": label, "empty_heading": label}


def test_runway_fieldset_escapes_a_hostile_registry_label():
    """runway_fieldset() escapes a hostile registry label rather than dropping or interpolating
    it unescaped (T-25-03-B, narrowed from the retired schematic map's own coverage by
    27-05-PLAN.md Task 3, CFG-66)"""
    hostile = 'Runway <script>"x"</script> (07/25)'
    with _temporary_registry({"h": _runway_entry(hostile)}):
        rendered = config_page.runway_fieldset("h")
        assert "<script>" not in rendered, "a registry label containing markup reached the page unescaped"
        assert "&lt;script&gt;" in rendered, "expected the hostile registry label to render escaped, not dropped"


def test_the_controls_semantics_and_the_photographs_survive_the_maps_removal():
    """the control's own semantics and the photographs survive the map's removal — the row
    keeps role="radiogroup" with the same aria-labelledby/aria-describedby ids,
    current_runway_id=None marks nothing selected and leaves no radio checked, and the three
    runway photographs still render from the session-gated route and still exist on disk
    (CFG-66, retitled from the retired schematic map's own check by 27-05-PLAN.md Task 3)"""
    rendered = config_page.runway_fieldset("3")
    for fragment in (
            'role="radiogroup"',
            'aria-labelledby="%s"' % config_page.RUNWAY_GROUP_HEADING_ID,
            'aria-describedby="%s"' % config_page.RUNWAY_SECTION_CAPTION_ID):
        assert fragment in rendered
    none_selected = config_page.runway_fieldset(None)
    assert "runway-card--selected" not in none_selected
    assert " checked" not in none_selected
    empty = config_page.runway_fieldset("3", images_available=())
    assert "<img" not in empty
    with_images = config_page.runway_fieldset("3", images_available=device_config.RUNWAY_IDS)
    assert with_images.count("<img") == len(device_config.RUNWAY_IDS)
    assert config_page.RUNWAY_IMAGE_ROUTE_PREFIX in with_images
    for runway_id in device_config.RUNWAY_IDS:
        path = os.path.join(HERE, "static", "runway-%s.png" % runway_id)
        assert os.path.exists(path), (
            "%s is gone from disk - the developer objected to the drawn map, not to the "
            "photographs, and deleting real imagery here would be an unrelated, irreversible "
            "loss" % (path,))
