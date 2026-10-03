"""Tests the screen-registry split (scope_groups()/screens.py), the
Diagnostic LED's single-switch contract, the Display/Device supersection
structure (section-intro headings, the --nested modifier count, the
merged-Aspect-card <h2> order), the instant-switch/form-nesting
restructure, French/English i18n copy checks, scope-aware
render()/handle_post() (hidden fields, out-of-scope-checkbox
carry-forward), the conditional screen selector, and the next-wake
caption suffix plus the one computed Quiet-hours delay sentence across
its DUE/HELD/UNKNOWN branches. No running companion/app.py server is
needed for this slice.
"""
import sys

import pytest

import companion.layout as layout
import companion.prefs as prefs
from companion import i18n_fr
from companion.i18n_fr import display as i18n_fr_display
from companion.pages import config_page
from server import device_config
from server.plane import colour_rules


# Rendering the Display scope opens <state_dir>/history.db, so every render
# and flash lookup below gets a per-test state dir under tmp_path, never a
# host path. The module-level contexts are filled in per test too.
STATE_DIR = None


@pytest.fixture(autouse=True)
def _per_test_state_dir(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    monkeypatch.setattr(sys.modules[__name__], "STATE_DIR", state_dir)
    monkeypatch.setitem(_TASK2_BASE_CTX, "state_dir", state_dir)
    monkeypatch.setitem(_TASK3_I18N_CTX, "state_dir", state_dir)


def test_scope_groups_follow_the_screen_registry():
    """scope_groups() renders the display/device pages from companion/screens.py's per-screen
    declaration - disjoint, together equal to the legacy single page - and unknown screen ids
    fall back to the default screen"""
    from companion import screens
    screen = screens.screen_type()
    assert config_page.scope_groups(config_page.SCOPE_DISPLAY) == tuple(screen["everyday_groups"]), (
        "expected the display scope to render the screen's everyday groups")
    assert config_page.scope_groups(config_page.SCOPE_DEVICE) == tuple(screen["advanced_groups"]), (
        "expected the device scope to render the screen's advanced groups")
    everyday = set(config_page.scope_groups(config_page.SCOPE_DISPLAY))
    advanced = set(config_page.scope_groups(config_page.SCOPE_DEVICE))
    assert not (everyday & advanced), "expected no settings group on both pages, got %r" % (everyday & advanced,)
    assert set(config_page.scope_groups(config_page.SCOPE_ALL)) == everyday | advanced, (
        "expected the legacy all-scope to be exactly the union of the two pages")
    assert screens.screen_type("no-such-screen") is screens.screen_type(), (
        "expected an unknown screen id to fall back to the default screen")
    assert screens.current_screen_id({"screen_id": "no-such-screen"}) == screens.DEFAULT_SCREEN_ID, (
        "expected a hostile ctx screen_id to resolve to the default screen")


def test_the_led_group_renders_one_switch_and_no_surviving_checkbox():
    """config_page.led_group() renders exactly ONE control for the setting - a server-rendered
    role=switch whose aria-checked is the stored value in both directions, named by the setting,
    described by its state span AND the group's own caption, attached across the DOM to its own
    /quick/led form - and no input[name="led_enabled"] checkbox survives beside it"""
    for stored in (True, False):
        rendered = config_page.led_group(stored)
        assert 'name="led_enabled"' not in rendered, (
            "stored=%r: an input named led_enabled still renders in the LED group - the switch "
            "and a surviving checkbox would be TWO controls for one setting, the exact defect "
            "X1/D-04 exists to remove" % (stored,))
        expected = (
            '<button type="submit" class="switch" role="switch" aria-checked="%s"'
            ' aria-labelledby="%s" aria-describedby="%s %s" %s form="%s">'
            % ("true" if stored else "false",
               config_page.QUICK_LED_LABEL_ID, config_page.QUICK_LED_STATE_ID,
               config_page.LED_SECTION_CAPTION_ID, layout.QUICK_SWITCH_CONTROL_ATTR,
               config_page.QUICK_LED_FORM_ID))
        assert expected in rendered, (
            "stored=%r: expected the server-rendered switch %r - aria-checked is the SAVED "
            "value, the name is the setting, and the group's own caption stays reachable as a "
            "description; got %r" % (stored, expected, rendered))
        assert rendered.count('role="switch"') == 1, (
            "stored=%r: expected exactly ONE control in the LED group, got %d role=switch elements"
            % (stored, rendered.count('role="switch"')))
        # The button is attached ACROSS the DOM to a form that is a sibling of #settings-form: the
        # group renders INSIDE the settings form, and a <form> can never nest inside another.
        assert ('form="%s"' % config_page.QUICK_LED_FORM_ID) in rendered, (
            "stored=%r: the switch must reach its own form through a form= attribute - the "
            "cross-DOM idiom the Send-a-test button already uses, because this card renders "
            "inside <form id=\"settings-form\">" % (stored,))
        assert config_page.LED_SECTION_CAPTION_ID in rendered, "stored=%r: the group's caption id is gone" % (stored,)
        assert layout.QUICK_SWITCH_REGION_ATTR in rendered, (
            "stored=%r: the LED card carries no %s - quick-switch.js has nothing to mark pending"
            % (stored, layout.QUICK_SWITCH_REGION_ATTR))
        assert layout.QUICK_STATE_ON_ATTR in rendered and layout.QUICK_STATE_OFF_ATTR in rendered, (
            "stored=%r: expected both state wordings server-rendered" % (stored,))


def test_the_quick_led_form_is_a_sibling_of_the_settings_form(tmp_path):
    """config_page.quick_led_form_html() is an EMPTY form carrying its own method/action/id, the
    handshake attribute and the two hidden fields with the posted state inverted from the
    stored one - and render() places it as a SIBLING of the settings form on the Device scope and
    not at all on Display

    The <form> must never nest inside <form id="settings-form">: HTML forbids it and the browser
    silently drops the inner one, which would make the switch post the SETTINGS route instead - a
    partial settings save.
    """
    section = config_page.quick_led_form_html(True)
    assert section.startswith('<form method="post" action="/quick/led" '), (
        "expected the LED quick form to open with its own literal method/action, got %r" % (section[:120],))
    assert ('id="%s"' % config_page.QUICK_LED_FORM_ID) in section, (
        "expected the form to carry the id the switch's form= attribute names")
    assert "data-quick-switch" in section, (
        "expected the D-04 handshake attribute on the form - dirty-state.js and quick-switch.js both key on it")
    for token in ('<input type="hidden" name="state" value="off">',
                  '<input type="hidden" name="return_to" value="/device">'):
        assert token in section, "expected %r in the LED quick form, got %r" % (token, section)
    assert config_page.quick_led_form_html(False).count('name="state" value="on"') == 1, (
        "the posted state must be the OPPOSITE of the stored one, or pressing the switch with "
        "scripts blocked re-asserts the state it is already in")
    assert "<button" not in section, (
        "the form stays EMPTY - its button lives in the LED card and reaches it across the DOM")
    # And on a real Device render it is a sibling, not a descendant.
    tmp = str(tmp_path)
    device_config.save_device_config(tmp, led_enabled=True)
    ctx = {"state_dir": tmp, "device_config": device_config.load_device_config(tmp)}
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    form_open = device.index('<form class="config-form"')
    form_close = device.index("</form>", form_open)
    quick_at = device.index('action="/quick/led"')
    assert not (form_open < quick_at < form_close), (
        "the LED quick form renders INSIDE <form id=\"settings-form\"> - a nested <form> is "
        "dropped by every browser and the switch would post /settings instead, which is a "
        "partial settings save (T-23-25)")
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert "/quick/led" not in display, "expected no LED quick form on the Display scope, which has no LED group"


def test_display_scope_carries_runway_and_calendar_device_carries_neither():
    """scope_groups(SCOPE_DISPLAY) contains Runway and Calendar, and scope_groups(SCOPE_DEVICE)
    contains neither"""
    from companion import screens
    display_groups = config_page.scope_groups(config_page.SCOPE_DISPLAY)
    device_groups = config_page.scope_groups(config_page.SCOPE_DEVICE)
    assert screens.GROUP_RUNWAY in display_groups and screens.GROUP_CALENDAR in display_groups, (
        "expected Runway and Calendar in scope_groups(SCOPE_DISPLAY), got %r" % (display_groups,))
    assert screens.GROUP_RUNWAY not in device_groups and screens.GROUP_CALENDAR not in device_groups, (
        "expected neither Runway nor Calendar in scope_groups(SCOPE_DEVICE), got %r" % (device_groups,))


_TASK2_BASE_CTX = {
    "device_config": {
        "display_enabled": True, "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
    },
    "state_dir": None, "poll_cooldown_remaining": 0,
}


def test_display_render_carries_no_form_nested_inside_a_form():
    """the rendered Display page contains no <form> nested inside another <form> anywhere

    A whole-body scan for any "<form" whose nearest preceding unclosed "<form" has not yet been
    closed - i.e. no <form> is ever a descendant of another <form> anywhere in the rendered
    Display page.
    """
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    depth = 0
    pos = 0
    while True:
        open_pos = rendered.find("<form", pos)
        close_pos = rendered.find("</form>", pos)
        if open_pos == -1 and close_pos == -1:
            break
        if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
            assert depth < 1, (
                "expected no <form> nested inside another <form>, found one opening at offset %d" % open_pos)
            depth += 1
            pos = open_pos + len("<form")
        else:
            depth -= 1
            pos = close_pos + len("</form>")
    assert depth == 0, "expected every <form> to be closed, got an unbalanced depth of %d" % depth


def test_two_scheduled_inputs_carry_form_settings_form():
    """the two remaining scheduled inputs (quiet_hours_start, quiet_hours_end) carry
    form="settings-form" via the SETTINGS_FORM_ID constant, and neither display_enabled
    nor quiet_hours_enabled renders on the Display page any more"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    for needle in (
            '<input type="time" name="quiet_hours_start" value="22:00" required'
            ' lang="en" form="settings-form"',
            '<input type="time" name="quiet_hours_end" value="06:00" required'
            ' lang="en" form="settings-form"'):
        assert needle in rendered, "expected %r in the rendered Display page" % (needle,)
    assert 'name="display_enabled"' not in rendered and 'name="quiet_hours_enabled"' not in rendered, (
        "expected no display_enabled/quiet_hours_enabled input on the Display page")


def test_schedule_cards_carry_no_quick_action_markup():
    """the Quiet hours card carries no quick-action markup any more - its switch moved into the
    shared Frame strip; the Screen on/off card this check used to also cover is
    retired outright"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    for heading in (config_page.QUIET_HOURS_SECTION_HEADING,):
        start = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.QUIET_HOURS_GROUP_HEADING_ID, heading))
        next_heading = rendered.find('<h2 class="text-heading"', start + 1)
        segment = rendered[start:next_heading] if next_heading != -1 else rendered[start:]
        assert "quick-action" not in segment, "expected the %r card to carry no quick-action markup" % (heading,)


def test_handle_post_same_field_set_after_restructure_saves_the_same_config(tmp_path):
    """a POST through handle_post() with the same field set as before the instant-switch
    restructure still produces the same saved config"""
    tmp = str(tmp_path)
    key = config_page.handle_post(
        {
            "scope": "display", "theme": "black", "display_enabled": "on",
            "quiet_hours_enabled": "on", "quiet_hours_start": "23:00",
            "quiet_hours_end": "07:00",
        },
        {"state_dir": tmp})
    assert key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (key,)
    cfg = device_config.load_device_config(tmp)
    assert (
        cfg["theme"] == "black" and cfg["display_enabled"] is True
        and cfg["quiet_hours_enabled"] is True
        and cfg["quiet_hours_start"] == "23:00" and cfg["quiet_hours_end"] == "07:00"
    ), "expected the same field set to persist identically, got %r" % (cfg,)


_TASK3_I18N_CTX = {
    "device_config": {
        "display_enabled": True, "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
    },
    "state_dir": None, "poll_cooldown_remaining": 0,
    "calendar_configured": True, "calendar_last_synced_at": None,
    "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
}


def test_device_render_carries_no_edit_artwork_markup_in_either_language():
    """the Device render contains no edit-artwork markup and no ?edit=1 link, in either
    language"""
    for lang in ("en", "fr"):
        try:
            prefs.set_request_prefs(lang=lang)
            rendered = config_page.render(
                {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0},
                scope=config_page.SCOPE_DEVICE)
        finally:
            prefs.set_request_prefs(lang="en")
        assert "edit-artwork" not in rendered, "lang=%r: expected no edit-artwork markup on the Device page (D-36)" % (lang,)
        assert "?edit=1" not in rendered, "lang=%r: expected no ?edit=1 link on the Device page (D-36)" % (lang,)


def test_every_display_catalogue_key_is_a_key_of_the_merged_catalog():
    """every legacy CATALOG key (if any) of companion/i18n_fr/display.py is a key of the merged
    companion.i18n_fr.CATALOG, and every MESSAGES id is a key of the merged companion.i18n_fr.BY_ID
    (the auto-merge package actually picked this module up)"""
    missing_catalog = [
        key for key in getattr(i18n_fr_display, "CATALOG", {}) if key not in i18n_fr.CATALOG]
    assert not missing_catalog, (
        "expected every companion/i18n_fr/display.py CATALOG key in the merged CATALOG, "
        "missing %r" % (missing_catalog,))
    missing_messages = [
        msg_id for msg_id in getattr(i18n_fr_display, "MESSAGES", {}) if msg_id not in i18n_fr.BY_ID]
    assert not missing_messages, (
        "expected every companion/i18n_fr/display.py MESSAGES id in the merged BY_ID, "
        "missing %r" % (missing_messages,))


def test_submitted_scope_and_return_route_are_allowlisted():
    """submitted_scope() and submitted_return_route() are strict allowlists: unknown scopes
    degrade to the legacy all-scope and any non-member return_to falls back to /display"""
    assert config_page.submitted_scope({}) == config_page.SCOPE_ALL, (
        "expected a form without a scope field to resolve to the legacy all-scope")
    assert config_page.submitted_scope({"scope": "device"}) == config_page.SCOPE_DEVICE, (
        "expected scope=device to resolve to SCOPE_DEVICE")
    assert config_page.submitted_scope({"scope": "<script>"}) == config_page.SCOPE_ALL, (
        "expected a crafted scope to degrade to the all-scope, never be echoed")
    assert config_page.submitted_return_route({"return_to": "/device"}) == "/device", (
        "expected /device to be an allowed return route")
    for hostile in ("https://evil.example", "//evil.example", "/settings", "/login", ""):
        assert config_page.submitted_return_route({"return_to": hostile}) == "/display", (
            "expected %r to fall back to /display" % hostile)


def test_aspect_scoped_render_carries_hidden_fields_and_omits_other_groups():
    """render(scope=display/device) carries the matching hidden fields and only its own groups,
    including locating the rules row (inside the Aspect card) by its own data-usage attribute;
    the legacy render(ctx) carries no scope field; a hostile scope never reaches the markup"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    legacy = config_page.render(ctx)
    assert 'name="scope" value="display"' in display and 'name="return_to" value="/display"' in display, (
        "expected the display scope's hidden scope/return_to fields")
    assert 'name="scope" value="device"' in device and 'name="return_to" value="/device"' in device, (
        "expected the device scope's hidden scope/return_to fields")
    assert 'name="scope"' not in legacy, "expected the legacy all-scope render to carry no scope field"
    assert 'name="led_enabled"' not in display, "expected no LED group on the Display page"
    assert 'name="tracked_runway"' in display, "expected the runway group to render on the Display page (D-10)"
    assert 'name="tracked_runway"' not in device, "expected no runway group on the Device page (D-10)"
    assert 'name="quiet_hours_enabled"' not in device, "expected no quiet-hours group on the Device page"
    assert display.count('<h1 class="page-title">Display</h1>') == 1, "expected the Display page title"
    assert device.count('<h1 class="page-title">Device</h1>') == 1, "expected the Device page title"
    assert config_page.POLL_SECTION_HEADING not in display, "expected the manual-refresh section off the Display page"
    rules_row_marker = 'data-usage="%s"' % config_page.COLOUR_USAGE_RULES
    assert rules_row_marker in display, "expected the rules row, inside the Aspect card, on the Display page (D-11)"
    assert config_page.POLL_SECTION_HEADING in device, "expected the manual-refresh section on the Device page"
    assert rules_row_marker not in device, "expected the rules row off the Device page (D-11)"
    hostile = config_page.render(ctx, scope="<script>")
    assert 'name="scope"' not in hostile and "&lt;script&gt;" not in hostile, (
        "expected a hostile scope value to degrade to the legacy all-scope, never to be echoed")


def test_handle_post_scope_carries_out_of_scope_checkboxes_forward(tmp_path):
    """handle_post() treats a checkbox absent from an out-of-scope group as 'leave unchanged' (a
    Display save never flips the LED, a Device save never flips the screen or quiet hours), leaves
    display_enabled/quiet_hours_enabled/led_enabled unchanged even in-scope and on the legacy
    unscoped form while still honouring an explicit value, and a scoped submission without the
    Calendar group always carries the calendar forward"""
    tmp = str(tmp_path)
    device_config.save_device_config(
        tmp, led_enabled=True, display_enabled=True, quiet_hours_enabled=True,
        theme="white", tracked_runway="3")
    # Display-page save: no LED field on the page -> LED stays True.
    key = config_page.handle_post(
        {"scope": "display", "theme": "black", "display_enabled": "on",
         "quiet_hours_enabled": "on"}, {"state_dir": tmp})
    assert key == config_page.FLASH_SAVED, "expected FLASH_SAVED for the display-page save, got %r" % key
    cfg = device_config.load_device_config(tmp)
    assert cfg["led_enabled"] is True and cfg["theme"] == "black", (
        "expected led_enabled carried forward and theme persisted, got %r" % (cfg,))
    # Device-page save: no display/quiet fields -> both stay True. The LED's control is a
    # role="switch" posting to /quick/led, so an absent led_enabled here means "leave alone",
    # same as display_enabled's own absence has meant since 22-05.
    key = config_page.handle_post({"scope": "device", "tracked_runway": "06-24"}, {"state_dir": tmp})
    assert key == config_page.FLASH_SAVED, "expected FLASH_SAVED for the device-page save, got %r" % key
    cfg = device_config.load_device_config(tmp)
    assert cfg["display_enabled"] is True and cfg["quiet_hours_enabled"] is True, (
        "expected display/quiet-hours carried forward on a device-page save, got %r" % (cfg,))
    assert cfg["led_enabled"] is True and cfg["tracked_runway"] == "06-24", (
        "expected a Device save that names no led_enabled to LEAVE it True and to persist its "
        "own runway, got %r" % (cfg,))
    # And the explicit value is still honoured, which is what makes the clause above a statement
    # about ABSENCE rather than about led_enabled having stopped being writable here.
    key = config_page.handle_post(
        {"scope": "device", "led_enabled": config_page.LED_CHECKBOX_VALUE}, {"state_dir": tmp})
    assert key == config_page.FLASH_SAVED and device_config.load_device_config(tmp)["led_enabled"] is True, (
        "expected an explicit led_enabled value to still be honoured")
    # Calendar moved from Device to Display's everyday_groups: a
    # device-page submission now ignores even a stray calendar_disconnect field, while a
    # display-page submission's calendar fields are live.
    assert config_page.submitted_calendar_signal({"scope": "device"}) == config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD, (
        "expected a device-page submission without calendar fields to carry the calendar forward")
    assert config_page.submitted_calendar_signal(
        {"scope": "device", "calendar_disconnect": "on"}) == config_page.CALENDAR_URL_SIGNAL_CARRY_FORWARD, (
        "expected a device-page submission to ignore a stray calendar_disconnect field (D-11)")
    assert config_page.submitted_calendar_signal(
        {"scope": "display", "calendar_disconnect": "on"}) == config_page.CALENDAR_URL_SIGNAL_CLEAR, (
        "expected a display-page submission's calendar_disconnect field to resolve clear now that "
        "Calendar renders there (D-11)")
    # display_enabled and quiet_hours_enabled now resolve absent to "leave unchanged"
    # UNCONDITIONALLY, including on this legacy unscoped SCOPE_ALL path.
    key = config_page.handle_post({"theme": "white"}, {"state_dir": tmp})
    cfg = device_config.load_device_config(tmp)
    assert key == config_page.FLASH_SAVED and cfg["display_enabled"] is True, (
        "expected the legacy unscoped save to LEAVE display_enabled unchanged (True), got %r"
        % (cfg["display_enabled"],))






def test_render_carries_no_screen_selector_today():
    """render() at Display and Device scope contains no <select name="screen_id"> today (a
    single-member registry has no real choice to offer)"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    assert '<select name="screen_id"' not in display and '<select name="screen_id"' not in device, (
        "expected no screen selector with today's single-member registry")








def test_neither_scope_renders_an_edit_artwork_link():
    """neither the Display nor the Device scope renders an Edit-artwork link or markup any more -
    the link and its builder are deleted outright"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    href_fragment = "/airlines?edit=1"
    assert href_fragment not in display, "expected no Edit-artwork link on the Display page"
    assert href_fragment not in device, "expected no Edit-artwork link on the Device page (D-36)"
    assert "edit-artwork" not in display and "edit-artwork" not in device, (
        "expected no edit-artwork markup on either scope (D-36)")
    assert "_edit_artwork_link_html" not in dir(config_page), (
        "expected _edit_artwork_link_html() to be deleted outright (D-36)")


def test_with_next_wake_helper_contract():
    """_with_next_wake() returns the caption byte-identical for a falsy clock and appends '(next
    wake ≈ HH:MM)' when the clock is known"""
    assert config_page._with_next_wake("caption.", None) == "caption.", (
        "expected the caption unchanged for a falsy next_wake_clock")
    assert config_page._with_next_wake("caption.", "") == "caption.", (
        "expected the caption unchanged for an empty-string next_wake_clock")
    got = config_page._with_next_wake("caption.", "14:10")
    assert got == "caption. (next wake ≈ 14:10)", (
        "expected the suffix appended when next_wake_clock is known, got %r" % (got,))


def test_retired_screen_field_cannot_block_a_valid_settings_save(tmp_path):
    errors = {}
    outcome = config_page.handle_post(
        {"theme": "black", "screen_id": "unknown"},
        {"state_dir": str(tmp_path)}, errors=errors)
    assert outcome == config_page.FLASH_SAVED
    assert errors == {}
    saved = device_config.load_device_config(str(tmp_path))
    assert saved["theme"] == "black"
    assert "screen_id" not in saved
