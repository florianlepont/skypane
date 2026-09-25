"""Part 04 (second half) of the `companion/test_config_page.py` migration
chain (33-12-PLAN.md): the original harness's `check()` calls #188-#228
(minus #196, deleted - see below), covering the screen-registry split
(scope_groups()/screens.py), the Diagnostic LED's single-switch contract
(the LED quick-form sibling-of-settings-form guard), the Display/Device
supersection structure (three section-intro headings each, the --nested
modifier count, the merged-Aspect-card <h2> order), the Task 2 instant-
switch/form-nesting restructure (D-19/Pitfall 1), the French/English i18n
copy checks, scope-aware render()/handle_post() (hidden fields, out-of-
scope-checkbox carry-forward), the conditional screen selector, and the
next-wake caption suffix plus the one computed Quiet-hours delay sentence
across its DUE/HELD/UNKNOWN branches.

Every check calls `companion.pages.config_page`'s own functions directly,
in-process, against a `tmp_path`-backed state directory when it needs one on
disk at all - no running `companion/app.py` server is needed for this slice.

Check #196 (`_no_card_builder_function_ever_calls_section_intro_html_after_
the_merge`) is DELETED, not ported: it opened `companion/pages/config_page.py`
from disk and `ast.parse()`d it to find `section_intro_html()` call sites
inside the settings-card builder functions (a G2/TST-12 source-text read with
no test-side workaround, since the property it protects has no OWN
observable trace beyond the one the rendered markup already carries).
That rendered-markup trace - which builder produced which <h2>, classified
as a settings-card title vs. a supersection intro - is exactly what
`test_title_form_inventory_classifies_every_h2_text_heading_on_both_routes_
after_the_merge` (row 195, ported below) already counts by running render()
and inspecting its output; the AST check added no coverage beyond that.
"""
import re
import sys

import pytest

import companion.layout as layout
import companion.prefs as prefs
from companion import app as companion_app
from companion import i18n_fr
from companion.i18n_fr import display as i18n_fr_display
from companion.layout import escape_html
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
    /quick/led form - and no input[name="led_enabled"] checkbox survives beside it (D2/CFG-36,
    X1/D-04, 23-07-PLAN.md Task 2)"""
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
    D-04 handshake attribute and the two hidden fields with the posted state inverted from the
    stored one - and render() places it as a SIBLING of the settings form on the Device scope and
    not at all on Display (D2/CFG-36, 23-07-PLAN.md Task 2)

    The <form> must never nest inside <form id="settings-form">: HTML forbids it and the browser
    silently drops the inner one, which would make the switch post the SETTINGS route instead - a
    partial settings save, the exact shape T-23-25 is about.
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
        "the form stays EMPTY - its button lives in the LED card and reaches it across the DOM, "
        "mirroring notifications_test_section()'s own shape")
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
    contains neither (D-10/D-11)"""
    from companion import screens
    display_groups = config_page.scope_groups(config_page.SCOPE_DISPLAY)
    device_groups = config_page.scope_groups(config_page.SCOPE_DEVICE)
    assert screens.GROUP_RUNWAY in display_groups and screens.GROUP_CALENDAR in display_groups, (
        "expected Runway and Calendar in scope_groups(SCOPE_DISPLAY), got %r" % (display_groups,))
    assert screens.GROUP_RUNWAY not in device_groups and screens.GROUP_CALENDAR not in device_groups, (
        "expected neither Runway nor Calendar in scope_groups(SCOPE_DEVICE), got %r" % (device_groups,))


def test_display_render_carries_three_section_intros_in_locked_order():
    """the Display scope renders exactly three section-intro headings, in the locked Look/What it
    watches/When it is on order, and the Device scope renders exactly three of its own, in the
    locked When it wakes/How it tells you/When you can't wait order (D-12, retargeted by
    28-04-PLAN.md Task 1/CFG-72 from 'the Device scope renders none')"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    assert display.count("section-intro") == 3, (
        "expected exactly three section-intro occurrences on Display, got %d" % display.count("section-intro"))
    look_pos = display.find('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
    watches_pos = display.find('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID)
    on_pos = display.find('id="%s"' % config_page.DISPLAY_ON_SECTION_ID)
    assert -1 not in (look_pos, watches_pos, on_pos), "expected all three supersection heading ids to be present"
    assert look_pos < watches_pos < on_pos, "expected Look < What it watches < When it is on in document order"
    assert device.count("section-intro") == 3, (
        "expected exactly three section-intro occurrences on Device, got %d" % device.count("section-intro"))
    wakes_pos = device.find('id="%s"' % config_page.DEVICE_WAKES_SECTION_ID)
    tells_pos = device.find('id="%s"' % config_page.DEVICE_TELLS_SECTION_ID)
    poll_pos = device.find('id="%s"' % config_page.DEVICE_POLL_SECTION_ID)
    assert -1 not in (wakes_pos, tells_pos, poll_pos), (
        "expected all three Device supersection heading ids to be present")
    assert wakes_pos < tells_pos < poll_pos, (
        "expected When it wakes < How it tells you < When you can't wait in document order")


def test_every_grouped_card_under_a_display_supersection_carries_nested_class():
    """every grouped card the Display scope renders under one of its three supersections carries
    a --nested modifier class - down to 3 occurrences (Aspect's page-section--nested, Runway's and
    Quiet hours' theme-status--nested) now that the Calendar card's own separate
    page-section--nested wrapper is retired (D-12, CFG-85)"""
    ctx = {
        "device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
        "calendar_configured": True, "calendar_last_synced_at": None,
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    }
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    for needle in (
            "theme-status theme-status--nested",
            'class="page-section aspect-card page-section--nested"'):
        assert needle in display, "expected %r on the Display scope" % (needle,)
    assert display.count('class="page-section page-section--nested"') == 0, (
        "expected no bare page-section page-section--nested wrapper on Display - the Calendar "
        "card that used to emit it is retired")
    nested_count = display.count("theme-status--nested") + display.count("page-section--nested")
    assert nested_count == 3, "expected exactly 3 --nested occurrences on Display, got %d" % nested_count


def test_display_h2_order_matches_the_merged_aspect_card_placement():
    """the Display scope's rendered <h2> order is exactly Look, Aspect, What it watches, Runway,
    When it is on, Quiet hours - the separate Calendar heading this order used to also name is
    retired outright now that its connection block folds into the Aspect card's own Calendar row
    - and every calendar_theme_id radio still carries a form="settings-form" attribute (CFG-85,
    replacing the retired _display_h2_order_matches_d12_after_calendar_placement_fix)"""
    ctx = {
        "device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
        "calendar_configured": True, "calendar_last_synced_at": None,
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    }
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    headings = re.findall(r'<h2[^>]*>(.*?)</h2>', display)
    expected = [
        layout.FRAME_STRIP_HEADING,
        config_page.DISPLAY_LOOK_HEADING, config_page.ASPECT_HEADING,
        config_page.DISPLAY_WATCHES_HEADING,
        "Runway", config_page.DISPLAY_ON_HEADING,
        config_page.QUIET_HOURS_SECTION_HEADING,
    ]
    assert headings == expected, "expected <h2> order %r, got %r" % (expected, headings)
    calendar_radio_count = display.count('name="calendar_theme_id"')
    calendar_radio_with_form_count = len(
        re.findall(r'name="calendar_theme_id"[^>]*form="%s"' % config_page.SETTINGS_FORM_ID, display))
    assert calendar_radio_count > 0 and calendar_radio_with_form_count == calendar_radio_count, (
        "expected every one of the %d calendar_theme_id radios to carry form=\"%s\", got %d"
        % (calendar_radio_count, config_page.SETTINGS_FORM_ID, calendar_radio_with_form_count))


def test_title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge():
    """the title-form inventory, re-run after the calendar merge: both settings routes'
    h2.text-heading instances count and classify as 6 settings-card titles (form A, 3 on Device +
    3 on Display, down from 4 now that Calendar's own separate heading is retired) + 3
    supersection intros (form B) + 2 unrelated headings, with the counts re-derived by RUNNING
    rather than restated as the pre-merge 8/4/3/1 literal, and the two label vocabularies still
    never overlapping (CFG-85, replacing the retired
    _title_form_inventory_classifies_every_h2_text_heading_on_both_routes)"""
    ctx_display = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
        "calendar_configured": True, "calendar_last_synced_at": None,
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    }
    ctx_device = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 5,
    }
    display = config_page.render(ctx_display, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx_device, scope=config_page.SCOPE_DEVICE)

    counts = {}
    for label, rendered in (("display", display), ("device", device)):
        total = rendered.count('class="text-heading"')
        form_a = rendered.count('%s="' % config_page.DIRTY_SECTION_ATTR)
        form_b = rendered.count("section-intro")
        counts[label] = (total, form_a, form_b, total - form_a - form_b)
    # RE-DERIVED BY RUNNING (30-06-PLAN.md Task 3, CFG-85): Display's own tuple moves from
    # (8, 4, 3, 1) to (7, 3, 3, 1) - one fewer h2.text-heading instance and one fewer form-A card
    # title, both for the identical reason (the Calendar card's own separate heading is retired).
    # Device's own tuple is untouched.
    expected = {"display": (7, 3, 3, 1), "device": (7, 3, 3, 1)}
    assert counts == expected, (
        "expected {route: (total h2.text-heading, form-A card titles, form-B supersection "
        "intros, unclassified)} == %r, measured %r by running" % (expected, counts))

    card_title_headings = {
        "display": (config_page.ASPECT_HEADING, "Runway", config_page.QUIET_HOURS_SECTION_HEADING),
        "device": (
            config_page.LED_SECTION_HEADING, config_page.WAKE_INTERVAL_SECTION_HEADING,
            config_page.NOTIFICATIONS_SECTION_HEADING),
    }
    for route, rendered in (("display", display), ("device", device)):
        for heading in card_title_headings[route]:
            needle = ">%s</h2>" % escape_html(heading)
            assert needle in rendered, (
                "expected the settings-card heading %r to render inside its own [data-dirty-section] "
                "tile on the %s scope, and it did not" % (heading, route))
        assert len(card_title_headings[route]) == counts[route][1], (
            "expected exactly %d form-A card titles named on %s, the allowlist names %d"
            % (counts[route][1], route, len(card_title_headings[route])))

    # The two unclassified instances, identified by name - neither is a settings card or a
    # supersection intro. Unchanged by the merge (both survive it untouched).
    frame_strip_needle = ">%s</h2>" % escape_html(layout.FRAME_STRIP_HEADING)
    assert frame_strip_needle in display and frame_strip_needle not in device, (
        "expected the Frame strip's own <h2> (Display's unclassified instance) to render on "
        "Display and never on Device")
    poll_needle = '<h2 class="text-heading">%s</h2>' % escape_html(config_page.POLL_SECTION_HEADING)
    assert poll_needle in device and poll_needle not in display, (
        "expected Poll's own <h2> (Device's unclassified instance) to render on Device and never "
        "on Display (Display never renders Poll)")

    # OUTCOME 2 still holds: the two label vocabularies never overlap.
    overlap = (
        set(card_title_headings["display"]) | set(card_title_headings["device"])
    ) & {
        config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
        config_page.DISPLAY_ON_HEADING, config_page.DEVICE_WAKES_HEADING,
        config_page.DEVICE_TELLS_HEADING, config_page.DEVICE_POLL_HEADING,
    }
    assert not overlap, (
        "expected the settings-card vocabulary and the supersection-label vocabulary to share no "
        "text - found %r in both, which would mean a card's own identity and a group's own label "
        "had collapsed into the same word" % (overlap,))


def test_device_scope_wraps_all_four_settings_cards_with_the_nested_modifier():
    """the cheap structural guard, NOT the real proof (that is test_browser_ux.py's cross-page
    getComputedStyle comparator): the Device scope's rendered output wraps all four of its
    settings cards with the --nested modifier (three theme-status--nested, one
    page-section--nested) and carries zero unmodified settings-card wrappers of either base class
    (CFG-72, 28-04-PLAN.md Task 2)"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
    }
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    nested_theme_status = device.count('class="theme-status theme-status--nested"')
    assert nested_theme_status == 3, (
        "expected exactly 3 theme-status--nested settings-card wrappers on Device (LED, wake "
        "interval, notifications), got %d" % nested_theme_status)
    nested_page_section = device.count('class="page-section page-section--nested"')
    assert nested_page_section == 1, (
        "expected exactly 1 page-section--nested settings-card wrapper on Device (Poll), got %d"
        % nested_page_section)
    assert device.count('class="theme-status"') == 0, (
        "expected zero unmodified .theme-status settings-card wrappers on Device, got %d"
        % device.count('class="theme-status"'))
    assert device.count('class="page-section"') == 0, (
        "expected zero unmodified .page-section settings-card wrappers on Device, got %d"
        % device.count('class="page-section"'))


_TASK2_BASE_CTX = {
    "device_config": {
        "display_enabled": True, "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
    },
    "state_dir": None, "poll_cooldown_remaining": 0,
}


def test_display_render_carries_exactly_two_quick_action_forms():
    """a Display render contains exactly one action="/quick/display" form and one
    action="/quick/quiet-hours" form (D-19)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    assert rendered.count('action="%s"' % config_page.QUICK_DISPLAY_ROUTE) == 1, (
        "expected exactly one action=\"/quick/display\" form")
    assert rendered.count('action="%s"' % config_page.QUICK_QUIET_HOURS_ROUTE) == 1, (
        "expected exactly one action=\"/quick/quiet-hours\" form")


def test_quick_action_forms_are_not_descendants_of_settings_form():
    """neither instant-switch form is a descendant of <form id=settings-form> - both render in
    the shared Frame strip, before the settings form even opens (D-01/D-02/Pitfall 1)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    settings_form_open = rendered.index('<form class="config-form"')
    for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
        quick_form_pos = rendered.index('action="%s"' % route)
        assert quick_form_pos < settings_form_open, (
            "expected the %s instant-switch form to appear in the Frame strip, before the "
            "settings form even opens, not nested inside it" % route)


def test_display_render_carries_no_form_nested_inside_a_form():
    """the rendered Display page contains no <form> nested inside another <form> anywhere
    (D-19/Pitfall 1, the required structural fix)

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
    form="settings-form" via the SETTINGS_FORM_ID constant (D-19), and neither display_enabled
    nor quiet_hours_enabled renders on the Display page any more (22-05-PLAN.md Task 1,
    X1/D-04/D-12.1)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    for needle in (
            '<input type="time" name="quiet_hours_start" value="22:00" required'
            ' lang="en" form="settings-form"',
            '<input type="time" name="quiet_hours_end" value="06:00" required'
            ' lang="en" form="settings-form"'):
        assert needle in rendered, "expected %r in the rendered Display page" % (needle,)
    assert 'name="display_enabled"' not in rendered and 'name="quiet_hours_enabled"' not in rendered, (
        "expected no display_enabled/quiet_hours_enabled input on the Display page")


def test_display_render_has_exactly_one_quick_action_pair_inside_the_strip():
    """a Display render carries exactly one .quick-action--on/--off pair per switch, both inside
    .frame-strip (D-01/D-02)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    on_off_count = (
        rendered.count('quick-action quick-action--on')
        + rendered.count('quick-action quick-action--off'))
    assert on_off_count == 2, (
        "expected exactly two .quick-action--on/--off cells (Screen + Quiet hours), got %d" % (on_off_count,))
    strip_start = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
    strip_end = rendered.index('<form class="config-form"', strip_start)
    strip_segment = rendered[strip_start:strip_end]
    assert (
        strip_segment.count('quick-action quick-action--on')
        + strip_segment.count('quick-action quick-action--off') == 2
    ), "expected both quick-action cells to sit inside .frame-strip"


def test_schedule_cards_carry_no_quick_action_markup():
    """the Quiet hours card carries no quick-action markup any more - its switch moved into the
    shared Frame strip (D-01/D-02); the Screen on/off card this check used to also cover is
    retired outright by 22-05-PLAN.md Task 1 (X1/D-04/D-12.1)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    for heading in (config_page.QUIET_HOURS_SECTION_HEADING,):
        start = rendered.index(
            '<h2 class="text-heading" id="%s">%s</h2>'
            % (config_page.QUIET_HOURS_GROUP_HEADING_ID, heading))
        next_heading = rendered.find('<h2 class="text-heading"', start + 1)
        segment = rendered[start:next_heading] if next_heading != -1 else rendered[start:]
        assert "quick-action" not in segment, "expected the %r card to carry no quick-action markup" % (heading,)


def test_quick_action_forms_carry_return_to_the_display_route():
    """both instant-switch forms on Display carry a return_to hidden input whose value is the
    Display route (R-02)

    A DIFFERENT, pre-existing "return_to" hidden field also lives inside <form id="settings-form">
    itself (D-10's own scope-aware save-and-return-to-the-same-page mechanism) - same field NAME,
    different form, different route, no collision. Scoped to each quick-action <form>...</form>
    block specifically, not a whole-page substring count.
    """
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    needle = '<input type="hidden" name="return_to" value="%s">' % layout.DISPLAY_ROUTE
    for route in (config_page.QUICK_DISPLAY_ROUTE, config_page.QUICK_QUIET_HOURS_ROUTE):
        form_start = rendered.index('action="%s"' % route)
        form_end = rendered.index("</form>", form_start)
        assert needle in rendered[form_start:form_end], "expected %r inside the %s form" % (needle, route)


def test_frame_strip_renders_after_header_before_first_section_intro():
    """the Frame strip renders immediately after the page header and before the first
    section-intro on Display (D-02)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    header_pos = rendered.index('<h1 class="page-title">')
    strip_pos = rendered.index('<div class="frame-strip stat-tile stat-tile--accent"')
    intro_pos = rendered.index('class="section-intro"')
    assert header_pos < strip_pos < intro_pos, (
        "expected the page header, then the Frame strip, then the first section-intro, got "
        "positions %d, %d, %d" % (header_pos, strip_pos, intro_pos))


def test_applies_next_wake_sentence_appears_exactly_twice():
    """the shared "Applies the next time the frame wakes up." sentence appears exactly twice on
    the Display page - once per Frame-strip instant switch, and no longer a third time under the
    Quiet hours card's own caption now that CFG-79 confines it to one place per page (29-05-PLAN.md
    Task 2; widened to three by 22-05-PLAN.md Task 2 D-04, narrowed back here)"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    count = rendered.count(escape_html(layout.QUICK_ACTION_APPLIES_SENTENCE))
    assert count == 2, (
        "expected the shared instant-switch delay sentence to appear exactly twice (once per "
        "Frame-strip switch cell, and nowhere under the Quiet hours card any more), got %d" % count)


def test_handle_post_same_field_set_after_restructure_saves_the_same_config(tmp_path):
    """a POST through handle_post() with the same field set as before the Task 2 restructure
    still produces the same saved config (D-13/T-20-26)"""
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


def test_french_display_render_carries_french_headings_no_english():
    """a French Display render (prefs.set_request_prefs(lang='fr')) carries the three
    supersection headings, the purpose sentence and the instant-switch sentence in French, and
    none of their English counterparts (D-05)"""
    try:
        prefs.set_request_prefs(lang="fr")
        fr_rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    for french_text in ("Aspect", "Ce qu’il surveille", "Quand il est allumé",
                         "Tout ce que le cadre affiche, et quand.",
                         "S’applique au prochain réveil du cadre."):
        assert french_text in fr_rendered, "expected %r in the French Display render" % (french_text,)
    for english_text in ("Look", "What it watches", "When it is on",
                          "Everything about what the frame shows and when.",
                          "Applies the next time the frame wakes up."):
        assert english_text not in fr_rendered, "expected %r to be absent from the French Display render" % (english_text,)


def test_french_display_and_device_render_translate_registry_labels():
    """a French Display render translates the default theme name ('White' -> 'Blanc') and
    default runway label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), and both scopes' screen
    caption translates 'Plane frame' -> 'Cadre avion', while the theme/runway ids stay
    untranslated attribute values (Polish fix 5, D-05)

    device_config.theme_label()/runway_label()'s registry text and screens.py's screen label are
    translated at their config_page.py display sites via i18n.t(), backed by
    companion/i18n_fr/registry.py - the default theme ("white" -> "White"/"Blanc") and default
    runway ("3" -> "Runway 3 (07/25)"/"Piste 3 (07/25)") both apply here since _TASK3_I18N_CTX's
    device_config carries neither key.
    """
    try:
        prefs.set_request_prefs(lang="fr")
        fr_display = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
        fr_device = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DEVICE)
    finally:
        prefs.set_request_prefs(lang="en")
    for french_text in ("Blanc", "Piste 3 (07/25)", "Cadre avion"):
        assert french_text in fr_display, "expected the French %r in the French Display render" % (french_text,)
    assert "Cadre avion" in fr_device, "expected the French screen label in the French Device render"
    assert "Runway 3 (07/25)" not in fr_display, "expected %r to be absent from the French Display render" % (
        "Runway 3 (07/25)",)
    assert 'value="white"' in fr_display and 'value="3"' in fr_display, (
        "expected the theme/runway ids themselves to stay untranslated attribute values")


def test_aspect_display_render_still_carries_every_pinned_english_string():
    """an English (default) Display render still contains every pre-existing English string this
    file's own checks assert, updated for CFG-85's rebuild (both the former Frame colours card's
    and the calendar connection block's own caption constants dropped, ASPECT_HEADING gained,
    everything else kept) - t() never touches the default-language render (D-05, 30-05-PLAN.md
    Task 2/30-06-PLAN.md Task 3, replacing the retired
    _english_display_render_still_carries_every_pinned_english_string)"""
    rendered = config_page.render(_TASK3_I18N_CTX, scope=config_page.SCOPE_DISPLAY)
    for english_text in (
            config_page.DISPLAY_LOOK_HEADING, config_page.DISPLAY_WATCHES_HEADING,
            config_page.DISPLAY_ON_HEADING, config_page.DISPLAY_PAGE_PURPOSE,
            layout.QUICK_ACTION_APPLIES_SENTENCE, config_page.ASPECT_HEADING,
            config_page.RUNWAY_SECTION_CAPTION, config_page.CALENDAR_HOW_IT_WORKS_SUMMARY):
        assert escape_html(english_text) in rendered, "expected the English constant %r to still render verbatim" % (
            english_text,)


def test_device_render_carries_no_edit_artwork_markup_in_either_language():
    """the Device render contains no edit-artwork markup and no ?edit=1 link, in either language
    (D-36)"""
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
    """every key of companion/i18n_fr/display.py is a key of the merged companion.i18n_fr.CATALOG
    (the auto-merge package actually picked this module up)"""
    missing = [key for key in i18n_fr_display.CATALOG if key not in i18n_fr.CATALOG]
    assert not missing, "expected every companion/i18n_fr/display.py key in the merged CATALOG, missing %r" % (missing,)


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
    the legacy render(ctx) carries no scope field; a hostile scope never reaches the markup
    (30-05-PLAN.md Task 2, replacing the retired
    _scoped_render_carries_hidden_fields_and_omits_other_groups)"""
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
    Calendar group always carries the calendar forward (D-12.1, 22-05-PLAN.md Task 1; the
    led_enabled half retargeted in place from absent-means-False by 23-07-PLAN.md Task 2)"""
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
    # Calendar moved from Device to Display's everyday_groups (20-07-PLAN.md Task 1, D-11): a
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
    # UNCONDITIONALLY, including on this legacy unscoped SCOPE_ALL path (X1/D-04/D-12.1, T-22-16).
    key = config_page.handle_post({"theme": "white"}, {"state_dir": tmp})
    cfg = device_config.load_device_config(tmp)
    assert key == config_page.FLASH_SAVED and cfg["display_enabled"] is True, (
        "expected the legacy unscoped save to LEAVE display_enabled unchanged (True), got %r"
        % (cfg["display_enabled"],))


def test_screen_selector_empty_for_the_real_single_member_registry():
    """_screen_selector_html() returns the empty string for the real single-member screens
    registry"""
    rendered = config_page._screen_selector_html("plane-frame")
    assert rendered == "", "expected the empty string for today's single-member registry, got %r" % (rendered,)


def test_screen_selector_renders_for_a_multi_member_registry():
    """_screen_selector_html() emits exactly one <select name="screen_id"> with one <option> per
    registered screen type, the current one selected, and a non-empty accessible name once a
    second screen type is registered"""
    from companion import screens
    saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
    try:
        screens.SCREEN_TYPES["rer-board"] = {
            "label": "RER board", "description": "d",
            "everyday_groups": (), "advanced_groups": (),
            "has_colour_rules": False, "has_manual_poll": False,
        }
        screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
        rendered = config_page._screen_selector_html("plane-frame")
        assert '<select name="screen_id"' in rendered, (
            "expected a <select name=\"screen_id\"> once a second screen type is registered")
        assert rendered.count("<option") == 2, "expected exactly one <option> per registered screen type, got %r" % (
            rendered,)
        assert 'value="plane-frame" selected' in rendered, (
            "expected the current screen id's option to carry the selected attribute")
        assert 'value="rer-board" selected' not in rendered, (
            "expected only the current screen id's option to carry selected")
        assert "<label" in rendered and 'for="screen-id-selector"' in rendered, (
            "expected a <label for=...> supplying the control's accessible name")
    finally:
        screens.SCREEN_TYPES.clear()
        screens.SCREEN_TYPES.update(saved_types)
        screens.SCREEN_IDS = saved_ids


def test_render_carries_no_screen_selector_today():
    """render() at Display and Device scope contains no <select name="screen_id"> today (a
    single-member registry has no real choice to offer)"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    device = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
    assert '<select name="screen_id"' not in display and '<select name="screen_id"' not in device, (
        "expected no screen selector with today's single-member registry")


def test_handle_post_rejects_a_crafted_screen_id(tmp_path):
    """handle_post() rejects a crafted screen_id with FLASH_SAVE_FAILED, notes a field error, and
    writes nothing (all-or-nothing)"""
    tmp = str(tmp_path)
    device_config.save_device_config(tmp, theme="white")
    errors = {}
    key = config_page.handle_post(
        {"theme": "black", "screen_id": "not-a-real-screen"}, {"state_dir": tmp}, errors=errors)
    assert key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED for a crafted screen_id, got %r" % (key,)
    assert "screen_id" in errors, "expected a field error noted for screen_id"
    cfg = device_config.load_device_config(tmp)
    assert cfg["theme"] == "white", "expected the whole save rejected - theme must not have changed to 'black'"


def test_valid_screen_id_round_trips(tmp_path):
    """a valid screen_id round-trips through save_device_config()"""
    tmp = str(tmp_path)
    key = config_page.handle_post({"screen_id": "plane-frame"}, {"state_dir": tmp})
    assert key == config_page.FLASH_SAVED, "expected FLASH_SAVED for a valid screen_id, got %r" % (key,)
    cfg = device_config.load_device_config(tmp)
    assert cfg["screen_id"] == "plane-frame", "expected screen_id='plane-frame' to round-trip, got %r" % (
        cfg["screen_id"],)


def test_screen_selector_renders_the_field_error_message():
    """_screen_selector_html() renders the screen_id field-level error message exactly once when
    errors carries one

    _screen_selector_html() is the only render call site for screen_id and, unlike every sibling
    field this plan touches, used to never render its own _field_error_html() message. Only
    reachable through a multi-member registry, same as the sibling checks above.
    """
    from companion import screens
    saved_types, saved_ids = dict(screens.SCREEN_TYPES), screens.SCREEN_IDS
    try:
        screens.SCREEN_TYPES["rer-board"] = {
            "label": "RER board", "description": "d",
            "everyday_groups": (), "advanced_groups": (),
            "has_colour_rules": False, "has_manual_poll": False,
        }
        screens.SCREEN_IDS = tuple(screens.SCREEN_TYPES)
        errors = {"screen_id": config_page.ERROR_INVALID_CHOICE}
        rendered = config_page._screen_selector_html("plane-frame", errors=errors)
        expected = escape_html(config_page.ERROR_INVALID_CHOICE)
        assert rendered.count(expected) == 1, (
            "expected the screen_id field-error message to appear exactly once, got %r" % (rendered,))
    finally:
        screens.SCREEN_TYPES.clear()
        screens.SCREEN_TYPES.update(saved_types)
        screens.SCREEN_IDS = saved_ids


def test_neither_scope_renders_an_edit_artwork_link():
    """neither the Display nor the Device scope renders an Edit-artwork link or markup any more -
    the link and its builder are deleted outright (D-36)"""
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


def test_affected_captions_gain_the_suffix_only_when_known():
    """each of Runway/LED/Wake-interval's own caption gains the '(next wake ≈ HH:MM)' suffix when
    the value is known, and is byte-identical to its own constant when it is not (D-13; narrowed
    by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired, and by
    22-05-PLAN.md Task 1 X1/D-04/D-12.1 once Quiet hours' own caption moves to its own computed
    delay sentence instead - the Frame colours card's own caption never gains this suffix
    either)"""
    known_ctx = {
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
    }
    unknown_ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    known_display = config_page.render(known_ctx, scope=config_page.SCOPE_DISPLAY)
    known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
    unknown_display = config_page.render(unknown_ctx, scope=config_page.SCOPE_DISPLAY)
    unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
    # THEME_SECTION_CAPTION/QUIET_HOURS_SECTION_CAPTION are deliberately NOT in this list any
    # more - see their own retirements' history for why (21-05/22-05-PLAN.md).
    for caption in (
            config_page.RUNWAY_SECTION_CAPTION,
            config_page.LED_SECTION_CAPTION,
            config_page.WAKE_INTERVAL_SECTION_CAPTION):
        # escape_html() is what the render pipeline actually applies - several of these captions
        # carry an apostrophe, so the RAW constant never appears verbatim in the rendered HTML.
        escaped_caption = escape_html(caption)
        escaped_suffix = config_page.NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % "14:10"
        assert (
            (escaped_caption + escaped_suffix) in known_display
            or (escaped_caption + escaped_suffix) in known_device
        ), "expected %r to gain the suffix when the next-wake value is known" % (caption,)
        assert escaped_caption in (unknown_display + unknown_device), (
            "expected %r to render byte-identical to its own constant when unknown" % (caption,))
        assert (escaped_caption + " (next wake") not in (unknown_display + unknown_device), (
            "expected %r to carry no suffix when the next-wake value is unknown" % (caption,))


def test_device_header_shows_next_wake_line_when_known():
    """the Device page header carries a 'Next wake ≈ HH:MM' line when the value is known and none
    at all when it is not (D-13's 'Home and Device show' wording)"""
    known_ctx = {
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
    }
    unknown_ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    known_device = config_page.render(known_ctx, scope=config_page.SCOPE_DEVICE)
    assert "Next wake" in known_device and "≈ 14:10" in known_device, (
        "expected the Device header to carry a Next wake ≈ HH:MM line when known")
    unknown_device = config_page.render(unknown_ctx, scope=config_page.SCOPE_DEVICE)
    assert "Next wake" not in unknown_device, "expected no Next wake line in the Device header when the value is unknown"


def test_quiet_hours_caption_and_flash_agree_on_the_due_branch():
    """with a due result, the Frame strip carries the DUE delay sentence exactly twice (once per
    switch cell), the Quiet hours card's own caption carries NO delay sentence any more
    (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the DUE delay sentence
    naming the same computed time, unaffected by the caption change (D-04)"""
    ctx = {
        "device_config": {"wake_interval_s": 900, "quiet_hours_enabled": False},
        "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
    }
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    expected_delay_fragment = escape_html("Applies at the next wake, around 14:10.")
    strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
    strip_end = display.index('<form class="config-form"', strip_start)
    assert display.count(expected_delay_fragment) == 2, (
        "expected the DUE delay sentence to appear exactly twice (once per Frame-strip switch "
        "cell), got %d in %r" % (display.count(expected_delay_fragment), display))
    assert expected_delay_fragment in display[strip_start:strip_end], (
        "expected the DUE delay sentence inside the Frame strip's own slice")
    caption = re.search(
        r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
        % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
    assert caption, "the Quiet hours card's own caption is gone"
    assert expected_delay_fragment not in caption.group(1), (
        "expected the Quiet hours card's OWN caption to carry NO delay sentence any more (CFG-79) "
        "- found it in %r" % (caption.group(1),))
    flash = companion_app._resolve_flash_text(
        companion_app.FLASH_KEY_SAVED, STATE_DIR,
        last_checkin_ts=ctx["last_checkin_ts"], device_cfg=ctx["device_config"])
    assert flash == "Saved — applies at the next wake, around 14:10.", "expected the DUE flash text, got %r" % (flash,)


def test_quiet_hours_caption_and_flash_agree_on_the_held_branch():
    """with a held result (the nightly regression fixture), the Frame strip carries the HELD
    delay sentence exactly twice (once per switch cell), the Quiet hours card's own caption
    carries NO delay sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save flash
    still reads the HELD delay sentence naming the window's own end, never the generic due wording
    (D-04, 22-UI-SPEC.md §3.3 binding rule 6)

    The nightly regression fixture: quiet hours 23:00-07:00 Europe/Paris, last check-in 22:58,
    clock 02:00 the next morning (a non-DST January date) - held, never late.
    """
    device_cfg = {
        "wake_interval_s": 900, "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    ctx = {
        "device_config": device_cfg,
        "last_checkin_ts": "2026-01-15T22:58:00+01:00", "now": "2026-01-16T02:00:00+01:00",
        "state_dir": STATE_DIR, "poll_cooldown_remaining": 0,
    }
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    expected_delay_fragment = escape_html("Applies when quiet hours end, around 07:00.")
    strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
    strip_end = display.index('<form class="config-form"', strip_start)
    assert display.count(expected_delay_fragment) == 2, (
        "expected the HELD delay sentence to appear exactly twice (once per Frame-strip switch "
        "cell), got %d in %r" % (display.count(expected_delay_fragment), display))
    assert expected_delay_fragment in display[strip_start:strip_end], (
        "expected the HELD delay sentence inside the Frame strip's own slice")
    caption = re.search(
        r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
        % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
    assert caption, "the Quiet hours card's own caption is gone"
    assert expected_delay_fragment not in caption.group(1), (
        "expected the Quiet hours card's OWN caption to carry NO delay sentence any more (CFG-79) "
        "- found it in %r" % (caption.group(1),))
    flash = companion_app._resolve_flash_text(
        companion_app.FLASH_KEY_SAVED, STATE_DIR,
        last_checkin_ts=ctx["last_checkin_ts"], device_cfg=device_cfg)
    assert flash == "Saved — applies when quiet hours end, around 07:00.", "expected the HELD flash text, got %r" % (
        flash,)


def test_quiet_hours_caption_and_flash_agree_on_the_unknown_branch():
    """with no check-in at all, the Frame strip carries the UNKNOWN delay sentence exactly twice
    (once per switch cell), the Quiet hours card's own caption carries NO delay sentence any more
    (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the UNKNOWN delay
    sentence, which names no time (D-04)"""
    ctx = {"device_config": {}, "state_dir": STATE_DIR, "poll_cooldown_remaining": 0}
    display = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    expected_delay_fragment = escape_html("Applies the next time the frame wakes up.")
    strip_start = display.index('<div class="frame-strip stat-tile stat-tile--accent"')
    strip_end = display.index('<form class="config-form"', strip_start)
    assert display.count(expected_delay_fragment) == 2, (
        "expected the UNKNOWN delay sentence to appear exactly twice (once per Frame-strip switch "
        "cell), got %d in %r" % (display.count(expected_delay_fragment), display))
    assert expected_delay_fragment in display[strip_start:strip_end], (
        "expected the UNKNOWN delay sentence inside the Frame strip's own slice")
    caption = re.search(
        r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
        % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), display)
    assert caption, "the Quiet hours card's own caption is gone"
    assert expected_delay_fragment not in caption.group(1), (
        "expected the Quiet hours card's OWN caption to carry NO delay sentence any more (CFG-79) "
        "- found it in %r" % (caption.group(1),))
    flash = companion_app._resolve_flash_text(companion_app.FLASH_KEY_SAVED, STATE_DIR)
    assert flash == "Saved — applies the next time the frame wakes up.", "expected the UNKNOWN flash text, got %r" % (
        flash,)
