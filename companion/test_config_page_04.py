"""Tests the rules-editor's suggestion chips and its two "always full,
never collapsed" disclosures, and the whole Calendar card's render()/
handle_post() contract - status verdict/detail across every branch,
copy-fidelity pins, forbidden-vocabulary and secret-containment guards,
the calendar row's own palette/selection-state, and handle_post()'s
calendar_theme_id/connect/disconnect/replace resolution.

The copy-fidelity checks pin the historically-approved wording as a
literal Python string inside the test itself (never a read of any
planning document at test time), and assert config_page.py's live
constant still equals that literal AND that the text reaches a render.
"""
import html
import pathlib
import re
import time

import pytest

import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion.layout import escape_html
from companion.pages import config_page
from companion.settings import rules as rules_settings
from server import device_config, history_db
from companion_markup import parse_html
from server.plane import calendar_rules, colour_rules


def _calendar_status(rendered):
    """The (state, pill text, detail text) of the one `.calendar-status` row on a rendered Display
    page, read from the served HTML."""
    doc = parse_html(rendered)
    row = doc.select_one(".calendar-status")
    assert row is not None, "expected a .calendar-status row"
    pill = row.select_one(".calendar-status__pill")
    detail = row.select_one(".calendar-status__detail")
    return row.attrs.get("data-calendar-state"), pill.text().strip(), detail.text().strip()


# Four distinguishable _calendar_connection_html() states: (configured, drift, last_synced_at).
_CALENDAR_GROUP_STATES = (
    (False, False, None),
    (True, False, None),
    (True, False, "2026-09-07T09:00:00+00:00"),
    (False, True, None),
)


def _calendar_connection_call(configured, drift, last_synced_at):
    """_calendar_connection_html() returns the status row plus the Manage dialog as one string."""
    return config_page._calendar_connection_html(
        configured, drift, last_synced_at, None, "2026-09-07T09:12:04+00:00", 0)


def test_rules_suggestion_chips_present_with_data_and_absent_with_no_events(tmp_path):
    """up to five suggestion chips render with data-kind/data-value from recent runway events, and
    none render when there are no events"""
    tmpdir = str(tmp_path)
    with history_db.open_db(tmpdir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2", callsign="AFR1380")
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
        "state_dir": tmpdir,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert 'class="rule-suggestion-chip" data-kind="callsign" data-value="AFR1380"' in rules_segment, (
        "expected a suggestion chip for the seeded callsign")

    empty_rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
        "state_dir": None,
    }, scope=config_page.SCOPE_DISPLAY)
    empty_segment = cp.rules_row_segment(empty_rendered)
    assert "rule-suggestion-chip" not in empty_segment, (
        "expected no suggestion chips when there are no recent events")


def test_plain_render_carries_the_precedence_sentence_and_no_how_it_works_disclosure():
    """a plain Display render always carries the full precedence sentence under the special
    looks, and the Calendar row no longer carries a "How it works" disclosure"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert escape_html(i18n.t(rules_settings.SPECIAL_LOOKS_ORDER)) in rules_segment, (
        "expected the full precedence sentence under the special looks")
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(
        rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[calendar_start:calendar_end]
    assert "How it works" not in calendar_segment
    assert "<details" not in calendar_segment.split('class="calendar-status"', 1)[1], (
        "expected no disclosure toggle in the Calendar connection block")
    assert "It only colours a flight already on screen." not in rendered
    assert "The most specific match wins." not in rendered


def test_rules_section_carries_no_dirty_section_attr():
    """the rules panel, inside the Frame colours card, carries no data-dirty-section attribute of
    its own - the card's OWN outer wrapper carries the one attribute for all four usages, exactly
    like the Poll section carries none"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert config_page.DIRTY_SECTION_ATTR not in rules_segment, (
        "expected the rules panel to carry no data-dirty-section attribute")


def test_rules_french_render_shows_french_row_label_and_button():
    """a French Display render of the special looks shows 'Allures spéciales', the 'Ajouter une
    allure spéciale' action and the 'Ajouter l’allure' submit button"""
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    for text in ("Allures spéciales", "Ajouter une allure spéciale", "Ajouter l’allure"):
        assert escape_html(text) in rendered, "expected the French %r" % (text,)


def test_calendar_forbidden_vocabulary_absent():
    """the Calendar card's copy carries none of the phase's banned affirmative real-time-
    awareness or crew-role vocabulary, while still carrying the mandated negated 'does not track'
    construction verbatim"""
    blob = " ".join([
        config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_CALENDAR],
        config_page.CALENDAR_HOW_IT_WORKS_BODY,
        config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT,
        config_page.CALENDAR_STATUS_CONNECTED_VERDICT,
        config_page.CALENDAR_STATUS_ZERO_TEMPLATE,
        config_page.CALENDAR_STATUS_DETAIL_TEMPLATE,
        config_page.CALENDAR_STATUS_PERMISSION_UNSAFE,
        config_page.CALENDAR_NONE_LEAD,
    ]).lower()
    forbidden_phrases = (
        "watches", "watch for", "follows", "monitors", "notifies",
        "currently flying", "in the air now", "on duty", "crew",
        "roster", "pilot", "duty roster",
    )
    bad = [phrase for phrase in forbidden_phrases if phrase in blob]
    assert not bad, "forbidden vocabulary found: %r" % (bad,)
    assert not re.search(r"\btracks\b|\bis tracking\b|\bwatching\b|\bmonitoring\b", blob), (
        "found an affirmative tracking/watching/monitoring claim")
    assert "does not track" in blob, (
        "expected the mandated negated 'does not track ... on its own' construction")


def test_calendar_secret_never_reaches_render_function(tmp_path):
    """with the calendar secret file holding a URL carrying a distinctive token, render() emits
    the masked host + ellipsis fragment but never the token, the path segment, the query-
    parameter name, or the whole raw URL"""
    token = "sk1-distinctive-token-2rv9"
    host = "private-crew-calendar.example.internal"
    path = "feeds/roster-export"
    query_param = "auth_token"
    url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
    tmpdir = str(tmp_path)
    assert calendar_rules.save_calendar_url(tmpdir, url) is True
    configured = calendar_rules.calendar_is_configured(tmpdir)
    assert configured, "expected calendar_is_configured() to report True with the secret file written"
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=configured,
        calendar_last_synced_at=None, state_dir=tmpdir)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert escape_html("%s…" % host) in rendered, (
        "expected the masked host + ellipsis fragment to appear once connected")
    for needle in (token, path, query_param, url):
        assert needle not in rendered, "expected %r never to appear in the rendered page" % (needle,)


def test_calendar_no_preview_no_count_in_rendered_page(tmp_path):
    """a populated calendar registry (real-shaped routes/airline codes) never surfaces any
    airport code or airline code, while the status row's own entry count DOES appear (the
    code-isolation half carried forward, the count-prohibition half retired)"""
    tmpdir = str(tmp_path)
    entries = [
        {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
         "start_at": 1893456000.0, "end_at": 1893459600.0},
        {"airline_iata": "AF", "origin_iata": "NCE", "destination_iata": "ORY",
         "start_at": 1893484800.0, "end_at": 1893488400.0},
        {"airline_iata": "BA", "origin_iata": "LHR", "destination_iata": "ORY",
         "start_at": 1893500000.0, "end_at": 1893503600.0},
    ]
    # This check's subject is the Settings page's rendered copy, not retention - an explicit
    # `now` bracketing the 2030-dated fixture entries keeps them in-window regardless of the
    # wall clock (render() itself never reads this file back, so this has no effect on the
    # assertions below, but it keeps the write path exercised the same way every run).
    now = 1893456000.0
    assert calendar_rules.write_calendar_registry(
        tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now), (
        "expected the fixture registry write to succeed")
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at="2026-09-07T09:00:00+00:00",
        calendar_entry_count=len(entries),
        colour_rules={kind: {} for kind in colour_rules.RULE_KINDS})
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    for code_pattern in (r"\bORY\b", r"\bTLS\b", r"\bNCE\b", r"\bLHR\b", r"\bAF\b", r"\bBA\b"):
        assert not re.search(code_pattern, rendered), (
            "expected no calendar-derived code matching %r anywhere on the rendered page" % (code_pattern,))
    # The status row deliberately DOES show a derived flight count now - the
    # old prohibition on a count is retired; only the specific airport/airline codes stay
    # forbidden (code isolation, unaffected).
    assert re.search(r"\b3\s+flights\s+in\s+the\s+next\s+48\s+h\b", rendered.lower()), (
        "expected the status detail's own flight-count phrase")


def test_calendar_d01_registry_entries_never_appear_in_rules_list(tmp_path):
    """with both a populated calendar registry and one hand-added colour rule, the rendered
    rules list shows exactly the manual rule and no calendar-sourced row"""
    tmpdir = str(tmp_path)
    entries = [
        {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
         "start_at": 1893456000.0, "end_at": 1893459600.0},
    ]
    # This check's subject is calendar-entry isolation from the rules list, not retention - see
    # the comment in the previous check for why `now` brackets the 2030-dated fixture entry.
    now = 1893456000.0
    assert calendar_rules.write_calendar_registry(
        tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now), (
        "expected the fixture registry write to succeed")
    result = colour_rules.add_rule(tmpdir, colour_rules.RULE_KIND_CALLSIGN, "AFR1234", "black")
    assert result in (colour_rules.ADD_OK_NEW, colour_rules.ADD_OK_REPLACED), (
        "expected the manual rule to be added, got %r" % (result,))
    registry = colour_rules.load_colour_rules(tmpdir)
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at="2026-09-07T09:00:00+00:00",
        colour_rules=registry)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert "AFR1234" in rules_segment, "expected the manually-added rule's key to appear in the rules list"
    for code_pattern in (r"\bORY\b", r"\bTLS\b"):
        assert not re.search(code_pattern, rules_segment), (
            "expected no calendar-sourced row (matching %r) in the rules editor" % (code_pattern,))


def test_aspect_calendar_row_palette_populated_in_order():
    """the calendar row's table carries one leading Same-as-departures option plus exactly one
    radio per registered theme, each id once, and the table carries no id attribute of its own

    The no-id clause is load-bearing: look_table_html() has four call sites on one page, and an
    id emitted inside it would be four identical ids.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    start, end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[start:end]
    table_match = re.search(r'<table class="look-table"[^>]*>', calendar_segment)
    assert table_match, "expected a .look-table inside the calendar row"
    assert ' id="' not in table_match.group(0)
    radio_values = re.findall(r'name="calendar_theme_id" value="([^"]*)"', calendar_segment)
    real_ids = [rid for rid in radio_values if rid]
    assert sorted(real_ids) == sorted(device_config.THEME_IDS), real_ids
    assert len(real_ids) == len(set(real_ids))
    assert len(radio_values) - len(real_ids) == 1, (
        "expected exactly one leading Same-as-departures option")


def test_calendar_theme_chip_grid_saved_value_is_checked():
    """with a saved calendar_theme_id, that chip's radio carries checked and no other
    calendar_theme_id radio (including the leading 'Same as departures' chip) does"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    ctx["device_config"] = dict(ctx["device_config"], calendar_theme_id="black")
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    # Every calendar_theme_id radio also carries a form="settings-form"
    # attribute between class="visually-hidden" and checked.
    checked_ids = re.findall(
        r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
        rendered)
    assert checked_ids == ["black"], (
        "expected exactly the saved calendar_theme_id ('black') checked, got %r" % (checked_ids,))


def test_calendar_theme_chip_grid_same_as_departures_checked_when_unset():
    """with no saved calendar_theme_id, only the leading 'Same as departures' chip is checked -
    never the chip matching the currently-selected base theme

    An unset calendar_theme_id checks the leading "Same as departures"
    chip (submitting the empty string), never the chip matching the base theme itself.
    """
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    ctx["device_config"] = dict(ctx["device_config"], theme="black")
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    checked_ids = re.findall(
        r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
        rendered)
    assert checked_ids == [""], (
        "expected only the leading 'Same as departures' chip (value='') checked when "
        "calendar_theme_id is unset, got %r" % (checked_ids,))


def test_handle_post_calendar_theme_id_valid_persists_and_carries_forward(tmp_path):
    """handle_post with a valid calendar_theme_id persists it and carries every other field
    forward"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"calendar_theme_id": "white"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["calendar_theme_id"] == "white", (
        "expected calendar_theme_id 'white' on disk, got %r" % (on_disk["calendar_theme_id"],))
    assert on_disk["theme"] == "black", (
        "expected the existing theme 'black' to be carried forward unchanged, got %r" % (on_disk["theme"],))


@pytest.mark.parametrize(
    "payload",
    ["chartreuse", "../../etc/passwd", "sky'; DROP TABLE flights; --"],
    ids=["invalid-id", "path-traversal-shaped", "sql-shaped"],
)
def test_handle_post_calendar_theme_id_adversarial_rejected(tmp_path, payload):
    """handle_post with a non-member calendar_theme_id (a plain invalid id, a path-traversal-
    shaped payload, and a SQL-shaped payload) rejects the whole submission and writes nothing -
    '' is explicitly exempted from this rejection

    "" is not on this adversarial list - it is the Aspect card's own legitimate "Same as
    departures" clear signal, covered by its own dedicated round-trip check above.
    """
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"calendar_theme_id": payload}, ctx)
    after = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for calendar_theme_id=%r, got %r" % (payload, flash_key))
    assert before == after, (
        "expected device_config.json to be byte-identical for calendar_theme_id=%r, it changed" % (payload,))


def test_handle_post_calendar_theme_id_absent_leaves_unchanged(tmp_path):
    """handle_post with no calendar_theme_id field at all leaves an already-saved value
    untouched"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    device_config.save_device_config(tmpdir, calendar_theme_id="green")
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["calendar_theme_id"] == "green", (
        "expected calendar_theme_id to remain 'green' when the field is absent, got %r"
        % (on_disk["calendar_theme_id"],))


def test_calendar_connect_field_never_carries_value_in_either_state():
    """the write-only calendar_url field renders in the merged _calendar_connection_html()'s own
    markup for both the connected and not-connected states and never carries a value attribute"""
    for configured in (False, True):
        rendered = _calendar_connection_call(configured, False, None)
        assert 'name="calendar_url"' in rendered, (
            "expected the calendar_url field when configured=%r" % (configured,))
        after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
        assert "value=" not in after_name, (
            "expected no value attribute on the calendar_url field when configured=%r" % (configured,))


def test_calendar_containment_at_the_renderer_five_needles(tmp_path):
    """the merged _calendar_connection_html(), called directly rather than through render(),
    never emits the token, host, path segment, query-parameter name, or whole URL of a configured
    calendar, even though it now also renders the connect/replace form and the disconnect button"""
    token = "sk1-distinctive-token-9fq2"
    host = "private-roster-calendar.example.internal"
    path = "feeds/duty-export"
    query_param = "auth_token"
    url = "https://%s/%s?%s=%s" % (host, path, query_param, token)
    tmpdir = str(tmp_path)
    assert calendar_rules.save_calendar_url(tmpdir, url) is True
    configured = calendar_rules.calendar_is_configured(tmpdir)
    drift = calendar_rules.calendar_secret_mode_is_unsafe(tmpdir)
    group_html = _calendar_connection_call(configured, drift, None)
    for needle in (token, host, path, query_param, url):
        assert needle not in group_html, (
            "expected %r never to appear in the merged _calendar_connection_html()'s own markup" % (needle,))


def test_calendar_disconnect_checkbox_never_appears_in_calendar_connection():
    """_calendar_connection_html() renders no calendar_disconnect checkbox in any of its four
    states (disconnecting is its own standalone form, not an in-form checkbox)"""
    for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
        rendered = _calendar_connection_call(configured, drift, last_synced_at)
        assert 'name="calendar_disconnect"' not in rendered, (
            "state %r: expected _calendar_connection_html() to render no calendar_disconnect "
            "checkbox at all (D-08 retires it)" % ((configured, drift),))


def test_look_supersection_carries_exactly_one_dirty_section_named_aspect():
    """Display's Look supersection carries exactly ONE data-dirty-section card (named 'Aspect'),
    in both the connected and not-connected states - down from the two ('Aspect'/'Calendar') it
    carried before the calendar's connection block folded into the Aspect card's own Calendar
    row"""
    for configured in (False, True):
        ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=configured, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        look_start = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        look_end = cp.runway_section_start(rendered, look_start)
        look_segment = rendered[look_start:look_end]
        count = look_segment.count(config_page.DIRTY_SECTION_ATTR + "=")
        assert count == 1, (
            "configured=%r: expected exactly one data-dirty-section card under Look, got %d" % (configured, count))
        expected_attr = '%s="%s"' % (
            config_page.DIRTY_SECTION_ATTR, escape_html(i18n.t(config_page.ASPECT_HEADING)))
        assert expected_attr in look_segment, (
            "configured=%r: expected the one Look card's dirty-section attribute to name the Aspect heading"
            % (configured,))


def test_calendar_connection_never_nests_a_form_inside_another_in_either_state():
    """the merged _calendar_connection_html()'s own return value (the card plus its data-only
    disconnect-form sibling) never nests one <form> inside another, in any of its four
    distinguishable states"""
    for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
        rendered = _calendar_connection_call(configured, drift, last_synced_at)
        depth = 0
        pos = 0
        while True:
            open_pos = rendered.find("<form", pos)
            close_pos = rendered.find("</form>", pos)
            if open_pos == -1 and close_pos == -1:
                break
            if open_pos != -1 and (close_pos == -1 or open_pos < close_pos):
                assert depth < 1, (
                    "state %r: expected no <form> nested inside another <form>" % ((configured, drift),))
                depth += 1
                pos = open_pos + len("<form")
            else:
                depth -= 1
                pos = close_pos + len("</form>")


def test_calendar_row_no_inline_js_and_palette_cross_submits_form():
    """the calendar row renders no inline event-handler attribute and no <script> tag, and every
    calendar_theme_id radio in its palette cross-submits into the settings form via
    form=settings-form"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[calendar_start:calendar_end]
    assert "<script" not in calendar_segment, "expected no <script> tag inside the Calendar row"
    assert not re.search(r'\son\w+="', calendar_segment), (
        "expected no inline on*= event-handler attribute inside the Calendar row")
    radio_count = calendar_segment.count('name="calendar_theme_id"')
    with_form = len(re.findall(
        r'name="calendar_theme_id" value="[^"]*"[^>]*form="%s"' % re.escape(config_page.SETTINGS_FORM_ID),
        calendar_segment))
    assert radio_count > 0, "expected at least one calendar_theme_id radio in the Calendar row"
    assert with_form == radio_count, (
        "expected every calendar_theme_id radio (%d) to cross-submit via form=%r, got %d"
        % (radio_count, config_page.SETTINGS_FORM_ID, with_form))


def test_calendar_disconnect_confirm_page_posts_back_with_confirm_preset():
    """calendar_disconnect_confirm_page() renders a form posting to CALENDAR_DISCONNECT_ROUTE
    with the confirm field pre-set to the accepted value, plus a plain cancel link to Display"""
    rendered = config_page.calendar_disconnect_confirm_page({})
    expected_form = (
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        config_page.CALENDAR_DISCONNECT_ROUTE,
        config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD,
        html.escape(config_page.CALENDAR_DISCONNECT_CONFIRM_VALUE, quote=True),
    )
    assert expected_form in rendered, (
        "expected the confirm page's form to post to the same route with the confirm field pre-set")
    # Calendar moved from Device to Display, so the cancel link
    # points back to the page the disconnect action itself lives on.
    assert 'href="%s"' % layout.DISPLAY_ROUTE in rendered, "expected a cancel link back to the Display page"
    assert "<fieldset" not in rendered and "<legend" not in rendered, (
        "expected no <fieldset>/<legend> on the confirm page")


def test_calendar_disconnect_form_is_not_inside_settings_form_on_display_scope():
    """on the Display scope, the calendar disconnect form's opening tag appears after the
    settings form's own closing tag - it is a sibling, never a descendant"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    settings_form_close = rendered.find("</form>")
    disconnect_form_open = rendered.find(
        '<form id="%s" method="post" action="%s"'
        % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE))
    assert settings_form_close != -1, "expected the settings form to be present"
    assert disconnect_form_open != -1, "expected the disconnect form to be present on the Display scope"
    assert disconnect_form_open >= settings_form_close, (
        "expected the disconnect form's opening tag to appear AFTER the settings form's closing tag")


def test_calendar_connect_form_appears_before_the_runway_card_on_display_scope():
    """on the Display scope, the calendar connect/replace form's own <form> opening tag renders
    inside the Calendar row and strictly before the Runway card's own radio input"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    calendar_row_index = rendered.index('data-look-usage="%s"' % config_page.COLOUR_USAGE_CALENDAR)
    connect_form_index = rendered.index(
        '<form class="calendar-sheet__form" method="post" action="%s"' % config_page.CALENDAR_CONNECT_ROUTE)
    runway_index = rendered.index('name="tracked_runway"')
    assert calendar_row_index < connect_form_index < runway_index, (
        "expected Calendar row < connect form < Runway card, got %d, %d, %d"
        % (calendar_row_index, connect_form_index, runway_index))


def test_calendar_disconnect_form_absent_when_not_configured_or_on_device_scope():
    """the disconnect form is absent when the calendar is neither configured nor drifted, and
    absent from the Device scope, which never renders the Calendar group at all"""
    not_connected_ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    display_rendered = config_page.render(not_connected_ctx, scope=config_page.SCOPE_DISPLAY)
    assert config_page.CALENDAR_DISCONNECT_ROUTE not in display_rendered, (
        "expected no disconnect form when the calendar is not configured or drifted")
    connected_ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    device_rendered = config_page.render(connected_ctx, scope=config_page.SCOPE_DEVICE)
    assert config_page.CALENDAR_DISCONNECT_ROUTE not in device_rendered, (
        "expected no disconnect form on the Device scope, which never renders Calendar")


def test_calendar_status_drift_names_remedy_and_nothing_forbidden():
    """the permission-drift status string names the remedy (paste the feed URL again) and names
    no path separator, filename, or part of a URL"""
    text = config_page.CALENDAR_STATUS_PERMISSION_UNSAFE
    assert "/" not in text and "\\" not in text, "expected no path separator in the drift status string"
    assert ".json" not in text and ".ics" not in text and "calendar_rules" not in text, (
        "expected no filename in the drift status string")
    assert "http" not in text.lower(), "expected no part of a URL in the drift status string"
    assert "paste" in text.lower(), (
        "expected the drift status to name the remedy (paste the link again)")


def test_handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves(tmp_path):
    """the single most important check in this family: a form that changes an unrelated
    setting and carries an empty calendar_url field with no checkbox, submitted twice in a row
    via handle_post(), leaves a configured calendar and its fetched entries completely untouched

    This is the regression the checkbox exists to prevent, and it is invisible to any check that
    only exercises the calendar fields deliberately.
    """
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
    now = time.time()
    entries = [{
        "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
        "start_at": now + 3600, "end_at": now + 7200}]
    assert calendar_rules.write_calendar_registry(tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
    ctx = {"state_dir": tmpdir}
    for _ in range(2):
        flash_key = config_page.handle_post({"theme": "white", "calendar_url": ""}, ctx)
        assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    assert calendar_rules.calendar_is_configured(tmpdir), (
        "expected the calendar to remain configured after two unrelated saves")
    registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
    assert len(registry["entries"]) == 1, (
        "expected the fetched entry to survive untouched, got %r" % (registry["entries"],))


def test_handle_post_disconnect_clears_url_and_registry(tmp_path):
    """handle_post with the disconnect checkbox at its expected value succeeds, disconnects the
    calendar, and empties its fetched-entries registry"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
    now = time.time()
    entries = [{
        "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
        "start_at": now + 3600, "end_at": now + 7200}]
    assert calendar_rules.write_calendar_registry(tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    assert not calendar_rules.calendar_is_configured(tmpdir), "expected the calendar to be disconnected"
    registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
    assert not registry["entries"], "expected zero entries after disconnect, got %r" % (registry["entries"],)


def test_handle_post_replace_url_stores_new_value_and_clears_registry(tmp_path):
    """handle_post with a different non-empty URL stores the new URL and clears the previous
    calendar's fetched-entries registry"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/old.ics") is True
    now = time.time()
    entries = [{
        "airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
        "start_at": now + 3600, "end_at": now + 7200}]
    assert calendar_rules.write_calendar_registry(tmpdir, entries, None, "2026-09-07T09:00:00+00:00", now=now)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"calendar_url": "https://example.invalid/new.ics"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    new_url = calendar_rules.configured_calendar_url(tmpdir)
    assert new_url == "https://example.invalid/new.ics", "expected the new URL to be stored, got %r" % (new_url,)
    registry = calendar_rules.load_calendar_registry(tmpdir, now=now)
    assert not registry["entries"], "expected zero entries after replacing the URL, got %r" % (registry["entries"],)


def test_handle_post_contradiction_rejects_whole_save_including_unrelated_field(tmp_path):
    """handle_post with a non-empty URL together with the disconnect checkbox, plus a changed
    unrelated setting, rejects the whole save - neither the calendar nor the unrelated setting is
    written (contradiction, all-or-nothing)"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
    before_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    before_url = calendar_rules.configured_calendar_url(tmpdir)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {
            "theme": "white",
            "calendar_url": "https://example.invalid/other.ics",
            "calendar_disconnect": config_page.CALENDAR_DISCONNECT_CHECKBOX_VALUE,
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    after_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert before_device == after_device, (
        "expected device_config.json to be byte-identical, the unrelated setting was written")
    assert calendar_rules.configured_calendar_url(tmpdir) == before_url, (
        "expected the previously configured calendar to be unchanged")


def test_handle_post_crafted_disconnect_value_rejects_whole_save(tmp_path):
    """handle_post with a crafted calendar_disconnect value rejects the whole save - neither the
    calendar nor the unrelated setting is written"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
    before_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    before_url = calendar_rules.configured_calendar_url(tmpdir)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"theme": "white", "calendar_disconnect": "yes"}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    after_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert before_device == after_device, (
        "expected device_config.json to be byte-identical, the unrelated setting was written")
    assert calendar_rules.configured_calendar_url(tmpdir) == before_url, (
        "expected the previously configured calendar to be unchanged")


def test_handle_post_overlength_url_rejects_whole_save(tmp_path):
    """handle_post with a calendar_url longer than CALENDAR_URL_MAX_LEN rejects the whole save -
    neither the calendar nor the unrelated setting is written"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    assert calendar_rules.save_calendar_url(tmpdir, "https://example.invalid/feed.ics") is True
    before_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    before_url = calendar_rules.configured_calendar_url(tmpdir)
    overlength = "https://example.invalid/" + "a" * (config_page.CALENDAR_URL_MAX_LEN + 100)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"theme": "white", "calendar_url": overlength}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    after_device = pathlib.Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert before_device == after_device, (
        "expected device_config.json to be byte-identical, the unrelated setting was written")
    assert calendar_rules.configured_calendar_url(tmpdir) == before_url, (
        "expected the previously configured calendar to be unchanged")
