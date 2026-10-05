"""Tests companion.pages.config_page's render() group layout, led_group(),
quiet_hours_group(), wake_interval_group(), handle_post()'s
display_enabled/quiet_hours resolution and its theme-only-save guard, the
settings form's class hooks, the Aspect card's per-theme palette
rendering, and runway_fieldset()'s cards/escaping/photograph survival.
Each test calls config_page directly against a tmp_path-backed state
directory; no running companion/app.py server is needed.
"""
import contextlib
import json
import os
import re

from companion import i18n
import companion.pages.config_page as config_page
import companion.test_config_page_helpers as cp
from companion.layout import escape_html
from companion.settings import look
from companion.test_config_page_helpers import i18n_lang
from companion_markup import parse_html
from server import device_config
from server.plane import colour_rules

HERE = os.path.dirname(os.path.abspath(__file__))


# ======================================================================
# Section 1: render()'s group layout, led_group(), quiet_hours_group()
# (markup/order/escaping/presets), wake_interval_group() (markup/value
# contract/render() placement).
# ======================================================================


def test_render_emits_no_fieldset_or_legend_four_groups_three_runway_cards_and_save_button():
    """render() emits no <fieldset>/<legend> and no .theme-chip-grid on this legacy SCOPE_ALL
    render, four theme-status-wrapped groups (Runway/Diagnostic LED/Quiet hours/Wake
    interval), three runway-card labels, and a Save settings submit button"""
    ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx)
    assert "<fieldset" not in rendered
    assert "<legend" not in rendered
    assert rendered.count('class="theme-status"') == 4
    assert "theme-chip-grid" not in rendered
    assert rendered.count('<label class="runway-card') == 3
    assert "Save settings" in rendered


def test_led_group_carries_the_switch_and_its_state_attribute_sequence():
    """led_group() emits the switch and preserves its class/role/aria-checked attribute sequence
    in both states, with no settings-checkbox label"""
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
    """quiet_hours_group() renders no on/off checkbox (the Frame strip is the only control left),
    one type="time" input each for Start/End with their current values, no theme-status__row,
    and no disabled attribute"""
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
    """quiet_hours_group()'s field order is heading, then caption, then Start, then End, in
    document order"""
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
    type="time" input"""
    rendered = config_page.quiet_hours_group("23:00", "07:00")
    caption_pos = rendered.index("section-caption")
    preset_pos = rendered.index(config_page.QUIET_HOURS_PRESET_ATTR)
    time_pos = rendered.index('type="time"')
    assert caption_pos < preset_pos < time_pos


def test_handle_post_preset_filled_submission_treated_identically_to_hand_typed(tmp_path):
    """handle_post() persists a Night-preset-shaped submission (quiet_hours_start/end equal to
    device_config's own defaults) exactly as it would a hand-typed value - no new server code
    path"""
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
    # No scope renders a quiet_hours_enabled checkbox; the Frame strip is
    # the only on/off control left.
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
    # The caption carries its own id, the number input's aria-describedby target.
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
    # "Theme" does not render on this legacy SCOPE_ALL page, so it is
    # excluded from this order check.
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
    """no settings render (legacy SCOPE_ALL, Display, Device) carries a display_enabled
    or quiet_hours_enabled input — the Frame strip is the only on/off control for either
    setting"""
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
    """the no-JS floor holds: scripts-blocked Display and Device renders each carry a reachable
    fallback Save button, form="settings-form"-associated with a plain server-rendered form
    (never a literal descendant of the form, though native submission is unchanged in substance
    either way), and a plain (no-JS) POST still round-trips the Quiet hours schedule"""
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
    # hours schedule — the one control the Display page leaves for this
    # setting.
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post(
        {"scope": "display", "quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}, ctx)
    assert flash_key == config_page.FLASH_SAVED
    on_disk = device_config.load_device_config(str(tmp_path))
    assert on_disk["quiet_hours_start"] == "22:15" and on_disk["quiet_hours_end"] == "06:45"


def test_handle_post_display_enabled_three_shapes(tmp_path):
    """handle_post() resolves display_enabled through all three shapes: absent LEAVES the stored
    value unchanged, DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the
    save-failed flash key and leaves a pre-existing device_config.json byte-identical"""
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
    """REGRESSION GUARD: a settings save that only changes the theme leaves display_enabled,
    quiet_hours_enabled AND led_enabled EXACTLY as they were, across all eight starting
    True/False combinations"""
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
    <fieldset> anywhere on the page"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx)
    # Runway's and Diagnostic LED's own <h2> each carry an id (an
    # aria-labelledby target); "Theme" is excluded from this list because
    # its replacement only ever renders on the Display scope.
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
    """the look card's three no-script tables each render one radio per registered theme, in
    registry order, each with form=settings-form and a frame-preview data-preview-src, with
    arrivals/calendar carrying exactly one leading Same-as-departures option and departures
    exactly zero; every theme's look read-back is the radio's accessible name"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    root = parse_html(rendered)
    theme_ids = device_config.THEME_IDS
    assert theme_ids, "THEME_IDS is empty - nothing to render"
    for field_name, leading_expected in (
            ("theme", 0), ("theme_arriving", 1), ("calendar_theme_id", 1)):
        radios = [
            node for node in root.find_all("input")
            if node.attrs.get("type") == "radio" and node.attrs.get("name") == field_name]
        values = [node.attrs["value"] for node in radios]
        real_ids = [value for value in values if value]
        assert len(values) - len(real_ids) == leading_expected
        assert sorted(real_ids) == sorted(theme_ids), (
            "expected one %s radio per registered theme, got %r" % (field_name, real_ids))
        assert len(real_ids) == len(set(real_ids))
        assert all(node.attrs.get("form") == config_page.SETTINGS_FORM_ID for node in radios)
        for node in radios:
            if node.attrs["value"]:
                assert node.parent.attrs.get("data-preview-src", "").startswith(
                    config_page.FRAME_PREVIEW_ROUTE_PREFIX + node.attrs["value"] + ".png?")
    with i18n_lang("en"):
        for theme_id in theme_ids:
            sentence = look.look_sentence(theme_id)
            assert escape_html(sentence) in rendered or escape_html(sentence.lower()) in rendered.lower()


def test_aspect_card_default_selects_exactly_the_white_departures_option():
    """the look card rendered with the default theme id checks exactly the plain-paper radio in
    the departures table, and exactly the leading Same-as-departures option in the
    arrivals/calendar tables, each asserted per group"""
    rendered = config_page.render({
        "device_config": {"theme": device_config.DEFAULT_THEME_ID, "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    root = parse_html(rendered)
    for field_name, expected_value in (
            ("theme", device_config.DEFAULT_THEME_ID),
            ("theme_arriving", ""),
            ("calendar_theme_id", "")):
        checked = [
            node.attrs["value"] for node in root.find_all("input")
            if node.attrs.get("name") == field_name and "checked" in node.attrs]
        assert checked == [expected_value]


def test_runway_fieldset_exactly_three_radios():
    """runway_fieldset() emits exactly three runway radio inputs"""
    rendered = config_page.runway_fieldset("3")
    assert rendered.count('name="tracked_runway"') == 3


def test_runway_fieldset_cards_visually_hidden_radio_and_selected_class():
    """runway_fieldset('3') renders three selectable cards, each wrapping a visually-hidden
    radio, with only the '3' card selected"""
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
    those two cards, none in the third"""
    rendered = config_page.runway_fieldset("3", images_available=("3", "06-24"))
    assert rendered.count("<img") == 2
    assert "/runway-image/3.png" in rendered and "/runway-image/06-24.png" in rendered
    assert "/runway-image/02-20.png" not in rendered


def test_look_swatch_matches_the_live_registry_band_facts():
    """look.swatch_svg() draws a diagonal band exactly for the registry's band themes, a soft
    (dithered) ink as a translucent fill over white paper and a solid ink fully opaque, with no
    style attribute, and space-joins extra_class onto its class attribute"""
    banded = [
        theme_id for theme_id in device_config.THEME_IDS
        if "<polygon" in look.swatch_svg(theme_id)]
    expect_banded = [
        theme_id for theme_id in device_config.THEME_IDS
        if "band_index" in device_config.THEMES[theme_id]]
    assert banded == expect_banded
    for theme_id in device_config.THEME_IDS:
        svg = look.swatch_svg(theme_id)
        assert "style=" not in svg
        theme = device_config.THEMES[theme_id]
        translucent = svg.count('fill-opacity="%s"' % look.SOFT_INK_OPACITY)
        expected = int(bool(theme.get("dithered"))) + int(bool(theme.get("band_dithered")))
        assert translucent == expected, (theme_id, svg)
    red_hex = look.colour_hex(look.COLOUR_RED)
    assert 'fill="%s"' % red_hex in look.swatch_svg("red")
    assert 'class="look-swatch extra"' in look.swatch_svg("white", extra_class="extra")


def test_look_table_renders_one_radio_per_registered_theme_and_explains_every_gap():
    """look.look_table_html() renders one radio per registered theme (plain paper beside the
    colour x style grid), checks exactly the selected one, associates every radio with the
    given form, puts leading_html first, and marks every grid cell with no theme as a gap
    whose accessible text carries its reason"""
    preview = lambda theme_id: "/p/%s.png" % theme_id  # noqa: E731
    html = look.look_table_html("theme", "red", "Departures", preview)
    root = parse_html(html)
    radios = [node for node in root.find_all("input") if node.attrs.get("type") == "radio"]
    assert sorted(node.attrs["value"] for node in radios) == sorted(device_config.THEME_IDS)
    assert [node.attrs["value"] for node in radios if "checked" in node.attrs] == ["red"]
    assert all(node.attrs.get("form") == config_page.SETTINGS_FORM_ID for node in radios)
    gaps = root.find_all("td", cls="look-table__gap")
    grid_cells = len(look.COLOURS) * len(look.STYLE_COLUMNS)
    assert len(gaps) == grid_cells - (len(device_config.THEME_IDS) - 1)
    with i18n_lang("en"):
        for gap in gaps:
            assert gap.text().split(". ", 1)[1] in [
                i18n.t(message) for message in look.REASON_MESSAGES.values()]
    lead = look.look_table_html(
        "theme_arriving", None, "Arrivals", preview, leading_html="<label id=LEAD></label>",
        form_id=None)
    assert lead.index("LEAD") < lead.index("look-cell")
    assert 'form="' not in lead


def test_look_sentence_reads_every_theme_back_from_its_three_choices():
    """look.look_sentence() reads every theme back as colour plus style ("Red, stripe on
    soft"), the colourless theme as "Plain paper", and the three choices resolve back to the
    same theme id"""
    with i18n_lang("en"):
        assert look.look_sentence("band_red_field") == "Red, stripe on soft"
        assert look.look_sentence("grey") == "Black, soft"
        assert look.look_sentence("white") == "Plain paper"
    for theme_id in device_config.THEME_IDS:
        colour, background, stripe = look.theme_axes(theme_id)
        assert look.resolve(colour or look.COLOUR_BLACK, background, stripe) == theme_id


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
    it unescaped"""
    hostile = 'Runway <script>"x"</script> (07/25)'
    with _temporary_registry({"h": _runway_entry(hostile)}):
        rendered = config_page.runway_fieldset("h")
        assert "<script>" not in rendered, "a registry label containing markup reached the page unescaped"
        assert "&lt;script&gt;" in rendered, "expected the hostile registry label to render escaped, not dropped"


def test_the_controls_semantics_and_the_photographs_survive_the_maps_removal():
    """the control's own semantics and the photographs survive the map's removal — the row
    keeps role="radiogroup" with the same aria-labelledby/aria-describedby ids,
    current_runway_id=None marks nothing selected and leaves no radio checked, and the three
    runway photographs still render from the session-gated route and still exist on disk"""
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
