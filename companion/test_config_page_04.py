"""Part 04 (first half) of the `companion/test_config_page.py` migration chain
(33-12-PLAN.md): the original harness's `check()` calls #146-#187, covering
the rules-editor's suggestion chips and its two "always full, never
collapsed" disclosures, and the whole Calendar card's render()/handle_post()
contract - status verdict/detail across every branch (not configured,
pending, fetch-failed, synced, unparseable, drifted), the phase-20/21
specification copy-fidelity pins, forbidden-vocabulary and secret-
containment guards, the calendar row's own palette/selection-state, and
handle_post()'s calendar_theme_id/connect/disconnect/replace resolution
(including the single most important check in this plan, D-07's
empty-field-no-checkbox no-op regression).

Every check calls `companion.pages.config_page`'s own functions directly,
in-process, against a `tmp_path`-backed state directory when it needs one on
disk at all - no running `companion/app.py` server is needed for this slice.

The two checks that used to read the phase 20/21 companion suggestions
specification documents out of the repository's own planning history
(TST-12's own named hotspot for this plan, D-14a..c) are rewritten as
`test_calendar_copy_fidelity_locked_to_the_phase_20_wording` and
`test_calendar_merged_button_copy_locked_to_the_phase_21_wording`: the
historically-approved copy is pinned as a literal Python string inside the
test itself (never a read of any planning document at test time), and the
assertions prove `config_page.py`'s live constant still equals that literal
AND that the text still reaches a real render.
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
from server import device_config, history_db
from server.plane import calendar_rules, colour_rules


def _calendar_status_parts(rendered):
    """The .status-row verdict/detail pair a Calendar-status check reads
    (20-09-PLAN.md Task 1, D-14b) - layout.status_row()'s own two spans,
    never a bare <p class="calendar-status"> (retired)."""
    match = re.search(
        r'<span class="status-row__verdict">(.*?)</span>'
        r'<span class="status-row__detail">(.*?)</span>',
        rendered, re.S)
    assert match, "expected a .status-row element"
    return match.group(1), match.group(2)


_CALENDAR_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_CONNECTED_VERDICT, quote=True)
_CALENDAR_NOT_CONNECTED_ESCAPED = html.escape(config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT, quote=True)

# Four distinguishable _calendar_connection_html() states: (configured, drift, last_synced_at).
_CALENDAR_GROUP_STATES = (
    (False, False, None),
    (True, False, None),
    (True, False, "2026-09-07T09:00:00+00:00"),
    (False, True, None),
)


def _calendar_connection_call(configured, drift, last_synced_at):
    """_calendar_connection_html() returns a (row_body_html, disconnect_form_html) tuple - the row
    body nests inside a <details>, the disconnect <form> must not (30-PATTERNS.md). Every check
    below treats the two joined as one string, exactly matching the retired calendar-card
    builder's own shape."""
    return "".join(config_page._calendar_connection_html(
        configured, drift, last_synced_at, None, "2026-09-07T09:12:04+00:00",
        0, None, "white"))


def test_rules_suggestion_chips_present_with_data_and_absent_with_no_events(tmp_path):
    """up to five suggestion chips render with data-kind/data-value from recent runway events, and
    none render when there are no events (D-15e)"""
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


def test_plain_render_carries_both_disclosures_in_full_never_collapsed():
    """a plain Display render always carries the full 'How rules combine' and Calendar 'How it
    works' <details> disclosures, never a collapsed one-sentence variant (D-17)

    D-17 (21-01-PLAN.md Task 2): the display mode that used to collapse both disclosures to one
    plain sentence is deleted outright.
    """
    ctx = {
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    rules_segment = cp.rules_row_segment(rendered)
    assert escape_html(config_page.RULES_HOW_RULES_COMBINE_SUMMARY) in rules_segment, (
        "expected the full 'How rules combine' <details> disclosure")
    assert "<details>" in rules_segment, "expected a <details> disclosure for rules"
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(
        rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[calendar_start:calendar_end]
    assert escape_html(config_page.CALENDAR_HOW_IT_WORKS_SUMMARY) in calendar_segment, (
        "expected the full Calendar 'How it works' <details> disclosure")
    # D-17: neither collapsed one-sentence variant may appear anywhere in the rendered body -
    # their exact punctuation never occurs as a substring of the full <details> body text above,
    # so this is an unambiguous check, not a coincidental prefix match.
    assert "It only colours a flight already on screen." not in rendered, (
        "expected no collapsed one-sentence Calendar disclosure anywhere")
    assert "The most specific match wins." not in rendered, (
        "expected no collapsed one-sentence rules disclosure anywhere")


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
    """a French Display render of the Frame colours card's rules row/panel shows 'Règles par vol'
    and 'Ajouter la règle' (D-05, retargeted from the retired Flight-colours heading)"""
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
    assert "Règles par vol" in rendered, "expected the French rules row label 'Règles par vol'"
    assert "Ajouter la règle" in rendered, "expected the French Add-rule button 'Ajouter la règle'"


def test_calendar_status_not_configured_is_exclusive():
    """with no calendar configured, render() emits the 'Not connected' verdict with an empty
    detail (D-14b)"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_NOT_CONNECTED_ESCAPED, (
        "expected the 'Not connected' verdict, got %r" % (verdict,))
    assert not detail, "expected an empty detail when not configured, got %r" % (detail,)


def test_calendar_status_configured_pending_is_exclusive():
    """with a calendar configured and no fetch attempt recorded yet, render() emits the
    'Connected' verdict with an empty detail (D-14b)"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_CONNECTED_ESCAPED, "expected the 'Connected' verdict, got %r" % (verdict,)
    assert not detail, (
        "expected an empty detail when configured with no attempt recorded yet, got %r" % (detail,))


def test_calendar_status_configured_fetch_failed_is_exclusive():
    """with a calendar configured, an attempt recorded, and no usable sync, render() emits the
    mapped 'The feed could not be read' detail - never an exception's own text (D-14b/T-20-30)"""
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None,
        calendar_last_attempt_at=1893456000.0)
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_CONNECTED_ESCAPED, "expected the 'Connected' verdict, got %r" % (verdict,)
    assert detail == escape_html(config_page.CALENDAR_STATUS_FETCH_FAILED_DETAIL), (
        "expected the mapped fetch-failed sentence, got %r" % (detail,))


def test_calendar_status_configured_synced_is_exclusive_with_relative_age():
    """with a calendar configured and a last_synced_at present, render() emits the 'Connected'
    verdict with a detail carrying the entry count and a relative-age fragment, never a bare ISO
    string (D-14b)"""
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at="2026-09-07T09:00:00+00:00", calendar_entry_count=12)
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_CONNECTED_ESCAPED, "expected the 'Connected' verdict, got %r" % (verdict,)
    assert "12" in detail, "expected the entry count '12' in the detail, got %r" % (detail,)
    assert "ago" in detail, "expected a relative-age fragment, proving relative_age_text() was used"


def test_calendar_status_unparseable_synced_falls_back_to_no_detail():
    """with a calendar configured and a last_synced_at that is present but unparseable, the empty
    detail is used rather than a fabricated time (D-14b)"""
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at="not-a-real-timestamp")
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_CONNECTED_ESCAPED, "expected the 'Connected' verdict, got %r" % (verdict,)
    assert not detail, "expected an empty detail for an unparseable stored value, got %r" % (detail,)


def test_calendar_copy_fidelity_locked_to_the_phase_20_wording():
    """the status detail template, the fetch-failed sentence, the Connect button text, and the
    Replace-URL disclosure summary are each locked to the phase 20 wording verbatim, so a
    paraphrase fails rather than merely looking different (D-14a..c)

    Copy fixed by the Phase 20 Companion Suggestions round (D-14a..c). The four literal constants
    below are the historically-approved wording; the assertions prove config_page.py's own
    constants still equal them verbatim AND that they actually reach a real render, not merely
    exist as an unused module attribute.
    """
    assert config_page.CALENDAR_STATUS_DETAIL_TEMPLATE == "%d upcoming flights · checked %s"
    assert config_page.CALENDAR_STATUS_FETCH_FAILED_DETAIL == "The feed could not be read"
    assert config_page.CALENDAR_CONNECT_BUTTON_TEXT == "Connect calendar"
    assert config_page.CALENDAR_REPLACE_URL_SUMMARY == "Replace the feed URL"

    fetch_failed = config_page.render(
        dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None,
             calendar_last_attempt_at=1893456000.0),
        scope=config_page.SCOPE_DISPLAY)
    assert escape_html(config_page.CALENDAR_STATUS_FETCH_FAILED_DETAIL) in fetch_failed, (
        "expected the fetch-failed sentence to actually render")

    not_connected = config_page.render(
        dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None),
        scope=config_page.SCOPE_DISPLAY)
    assert escape_html(config_page.CALENDAR_CONNECT_BUTTON_TEXT) in not_connected, (
        "expected the Connect button text to actually render when not connected")

    connected = config_page.render(
        dict(cp.CALENDAR_BASE_CTX, calendar_configured=True,
             calendar_last_synced_at="2026-09-07T09:00:00+00:00", calendar_entry_count=3),
        scope=config_page.SCOPE_DISPLAY)
    assert escape_html(config_page.CALENDAR_REPLACE_URL_SUMMARY) in connected, (
        "expected the Replace-URL disclosure summary to actually render when connected")


def test_calendar_merged_button_copy_locked_to_the_phase_21_wording():
    """the merged card's own two new short button-text constants (the connected-state Replace
    button, the small grey Disconnect button) are each locked to the phase 21 wording verbatim
    (D-13/D-14)

    Copy fixed by the Phase 21 Companion Feedback Round 3 (D-13/D-14), matching the discipline
    `test_calendar_copy_fidelity_locked_to_the_phase_20_wording` established for the phase-20
    strings.
    """
    assert config_page.CALENDAR_REPLACE_BUTTON_TEXT == "Replace"
    assert config_page.CALENDAR_DISCONNECT_BUTTON_TEXT == "Disconnect"
    connected = config_page.render(
        dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None),
        scope=config_page.SCOPE_DISPLAY)
    assert escape_html(config_page.CALENDAR_REPLACE_BUTTON_TEXT) in connected, (
        "expected the Replace button text to actually render when connected")
    assert escape_html(config_page.CALENDAR_DISCONNECT_BUTTON_TEXT) in connected, (
        "expected the Disconnect button text to actually render when connected")


def test_calendar_forbidden_vocabulary_absent():
    """the Calendar card's copy carries none of the phase's banned affirmative real-time-
    awareness or crew-role vocabulary, while still carrying the mandated negated 'does not track'
    construction verbatim"""
    blob = " ".join([
        config_page.FRAME_COLOURS_ROW_LABELS[config_page.COLOUR_USAGE_CALENDAR],
        config_page.CALENDAR_HOW_IT_WORKS_BODY,
        config_page.CALENDAR_STATUS_NOT_CONNECTED_VERDICT,
        config_page.CALENDAR_STATUS_CONNECTED_VERDICT,
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
    parameter name, or the whole raw URL (T-16-SECRET, extended by 21-07-PLAN.md Task 2 for the
    new masked-URL line, D-14/R-10)"""
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
    airport code or airline code, while the status row's own entry count DOES appear (D-14b;
    the phase 16 specification's D-01 code-isolation half carried forward, its
    count-prohibition half retired)"""
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
    # D-14b (this plan's own status row) deliberately DOES show a derived flight count now - the
    # old prohibition on a count is retired; only the specific airport/airline codes stay
    # forbidden (the phase 16 specification's own D-01 isolation, unaffected).
    assert re.search(r"\b3\s+upcoming\s+flights?\b", rendered.lower()), (
        "expected the D-14b status detail's own flight-count phrase")


def test_calendar_d01_registry_entries_never_appear_in_rules_list(tmp_path):
    """with both a populated calendar registry and one hand-added colour rule, the rendered
    rules list shows exactly the manual rule and no calendar-sourced row (16-VALIDATION.md
    registry row, D-01)"""
    tmpdir = str(tmp_path)
    entries = [
        {"airline_iata": "AF", "origin_iata": "ORY", "destination_iata": "TLS",
         "start_at": 1893456000.0, "end_at": 1893459600.0},
    ]
    # This check's subject is D-01 isolation from the rules list, not retention - see the
    # comment in the previous check for why `now` brackets the 2030-dated fixture entry.
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
    """the calendar row's palette carries one leading Same-as-departures option plus exactly one
    entry per registered theme, in registry order, with no id attribute of its own (D-06/D-09,
    30-05-PLAN.md Task 1)

    The calendar row's palette is a real role="radiogroup", populated in registry order with
    name="calendar_theme_id", carrying no id attribute - the no-id clause is load-bearing:
    _palette_grid_html() has three call sites on one page, and an id emitted inside it would be
    three identical ids.
    """
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    start, end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_CALENDAR)
    calendar_segment = rendered[start:end]
    grid_match = re.search(r'<div class="palette" role="radiogroup"[^>]*>', calendar_segment)
    assert grid_match, "expected a .palette role=radiogroup grid inside the calendar row"
    assert ' id="' not in grid_match.group(0), (
        "expected the calendar row's palette to carry no id attribute, got %r" % (grid_match.group(0),))
    radio_values = re.findall(r'name="calendar_theme_id" value="([^"]*)"', calendar_segment)
    real_ids = [rid for rid in radio_values if rid]
    assert real_ids == list(device_config.THEME_IDS), (
        "expected the calendar palette populated in registry order, got %r" % (real_ids,))
    leading_count = len(radio_values) - len(real_ids)
    assert leading_count == 1, (
        "expected exactly one leading Same-as-departures option, got %d" % leading_count)


def test_calendar_theme_chip_grid_saved_value_is_checked():
    """with a saved calendar_theme_id, that chip's radio carries checked and no other
    calendar_theme_id radio (including the leading 'Same as departures' chip) does (D-06/D-09)"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    ctx["device_config"] = dict(ctx["device_config"], calendar_theme_id="black")
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    # D-12 fix (20-REVIEW.md verification gap): every calendar_theme_id radio also carries a
    # form="settings-form" attribute between class="visually-hidden" and checked.
    checked_ids = re.findall(
        r'name="calendar_theme_id" value="([^"]*)" class="visually-hidden" form="settings-form" checked',
        rendered)
    assert checked_ids == ["black"], (
        "expected exactly the saved calendar_theme_id ('black') checked, got %r" % (checked_ids,))


def test_calendar_theme_chip_grid_same_as_departures_checked_when_unset():
    """with no saved calendar_theme_id, only the leading 'Same as departures' chip is checked -
    never the chip matching the currently-selected base theme (D-06/D-09, replacing the retired
    pre-D-09 default-to-base-theme behaviour)

    R-07's own new semantics: an unset calendar_theme_id checks the leading "Same as departures"
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
    '' is explicitly exempted from this rejection (D-09)

    21-05-PLAN.md Task 2 (D-09/R-07): "" is retargeted OUT of this adversarial list - it is now
    the Aspect card's own legitimate "Same as departures" clear signal, covered by its own
    dedicated round-trip check above.
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
    markup for both the connected and not-connected states and never carries a value attribute
    (D-13/D-14, retargeted after calendar_connect_section()'s retirement)"""
    for configured in (False, True):
        rendered = _calendar_connection_call(configured, False, None)
        assert 'name="calendar_url"' in rendered, (
            "expected the calendar_url field when configured=%r" % (configured,))
        after_name = rendered.split('name="calendar_url"', 1)[1].split(">", 1)[0]
        assert "value=" not in after_name, (
            "expected no value attribute on the calendar_url field when configured=%r" % (configured,))


def test_calendar_connect_wraps_in_details_only_when_configured():
    """the merged _calendar_connection_html() wraps its connect form in <details
    class=calendar-url-disclosure> 'Replace the feed URL' only when configured, and renders it
    unwrapped, posting to CALENDAR_CONNECT_ROUTE, when not (D-13/D-14, retargeted after
    calendar_connect_section()'s retirement)"""
    # The merged card ALSO always renders a second, unrelated <details> ("How it works") in every
    # state, so this check scans for the Replace disclosure's own specific class rather than a
    # bare "<details" substring, which would always be true now.
    connected_html = _calendar_connection_call(True, False, None)
    assert 'class="calendar-url-disclosure"' in connected_html, (
        "expected the connect form wrapped in <details class=calendar-url-disclosure> when configured")
    assert escape_html(config_page.CALENDAR_REPLACE_URL_SUMMARY) in connected_html, (
        "expected the Replace-the-feed-URL summary when configured")
    not_connected_html = _calendar_connection_call(False, False, None)
    assert 'class="calendar-url-disclosure"' not in not_connected_html, (
        "expected the connect form unwrapped (no calendar-url-disclosure) when not configured")
    assert 'action="%s"' % config_page.CALENDAR_CONNECT_ROUTE in not_connected_html, (
        "expected the connect form to post to CALENDAR_CONNECT_ROUTE either way")


def test_calendar_containment_at_the_renderer_five_needles(tmp_path):
    """the merged _calendar_connection_html(), called directly rather than through render(),
    never emits the token, host, path segment, query-parameter name, or whole URL of a configured
    calendar, even though it now also renders the connect/replace form and the disconnect button
    (T-17-SECRET, retargeted after calendar_connect_section()'s retirement)"""
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
    states (D-08/A-26: disconnecting is now its own standalone form, not an in-form checkbox)"""
    for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
        rendered = _calendar_connection_call(configured, drift, last_synced_at)
        assert 'name="calendar_disconnect"' not in rendered, (
            "state %r: expected _calendar_connection_html() to render no calendar_disconnect "
            "checkbox at all (D-08 retires it)" % ((configured, drift),))


def test_calendar_disconnect_form_appears_only_when_expected():
    """the merged _calendar_connection_html() renders its disconnect form only when the calendar
    is connected or drifted, posting to CALENDAR_DISCONNECT_ROUTE with a hidden, empty, data-
    confirm-field-carrying confirm field, alongside a visible small Disconnect button cross-
    submitting via form= (D-08/A-26/D-14, retargeted after calendar_disconnect_section()'s
    retirement)"""
    for configured, drift, last_synced_at in _CALENDAR_GROUP_STATES:
        rendered = _calendar_connection_call(configured, drift, last_synced_at)
        has_form = (
            '<form id="%s" method="post" action="%s"'
            % (config_page.CALENDAR_DISCONNECT_FORM_ID, config_page.CALENDAR_DISCONNECT_ROUTE)
        ) in rendered
        expected = configured or drift
        assert has_form == expected, (
            "state %r: expected disconnect-form presence %r, got %r" % ((configured, drift), expected, has_form))
        if has_form:
            assert 'data-confirm-field' in rendered, "expected the hidden confirm field to carry data-confirm-field"
            assert 'name="%s" value=""' % config_page.CALENDAR_DISCONNECT_CONFIRM_FIELD in rendered, (
                "expected the hidden confirm field to render with an EMPTY value")
            assert "data-confirm=" in rendered, "expected a data-confirm attribute carrying the confirm question"
            assert (
                'form="%s" class="calendar-disconnect-btn"' % config_page.CALENDAR_DISCONNECT_FORM_ID
            ) in rendered, "expected a visible Disconnect button cross-submitting via form="
        else:
            # A plain not-connected render (no drift either) shows the URL field and the primary
            # Connect button - and no Replace disclosure, no Disconnect button, no data-confirm
            # attribute at all.
            assert "calendar-disconnect-btn" not in rendered, (
                "expected no Disconnect button when neither configured nor drifted")
            assert "data-confirm=" not in rendered, (
                "expected no data-confirm attribute when neither configured nor drifted")
            assert 'class="calendar-url-disclosure"' not in rendered, (
                "expected no Replace disclosure when neither configured nor drifted")


def test_look_supersection_carries_exactly_one_dirty_section_named_aspect():
    """Display's Look supersection carries exactly ONE data-dirty-section card (named 'Aspect'),
    in both the connected and not-connected states - down from the two ('Aspect'/'Calendar') it
    carried before the calendar's connection block folded into the Aspect card's own Calendar row
    (CFG-85, replacing the retired data-dirty-section="Calendar" count check, whose own property
    this merge changes rather than merely relocates)"""
    for configured in (False, True):
        ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=configured, calendar_last_synced_at=None)
        rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
        look_start = rendered.index('id="%s"' % config_page.DISPLAY_LOOK_SECTION_ID)
        look_end = rendered.index('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID, look_start)
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
    distinguishable states (D-13/Pitfall 2)"""
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


def test_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr():
    """the calendar connection block renders inside the Calendar row, after that row's own
    palette, after the settings form's own closing tag and the Aspect card's own heading, still
    under the Aspect card's own dirty-section tracking attribute - with the Disconnect button
    inside the row and the disconnect form OUTSIDE the card, the button's form= naming that exact
    sibling (CFG-85, replacing the retired _calendar_placement_after_display_form_close_with_dirty_attr)

    Asserts the RELATIONSHIP rather than the endpoints separately - a check that only asserted
    all pieces existed would pass even if the button pointed at nothing.
    """
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    form_start = rendered.index('<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID)
    form_end = rendered.index("</form>", form_start)
    aspect_heading_pos = rendered.index('id="%s">%s</h2>' % (
        config_page.ASPECT_HEADING_ID, escape_html(i18n.t(config_page.ASPECT_HEADING))))
    calendar_start, calendar_end = cp.aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_CALENDAR)
    assert form_end < aspect_heading_pos < calendar_start, (
        "expected </form> < the Aspect heading < the Calendar row, got %d/%d/%d"
        % (form_end, aspect_heading_pos, calendar_start))
    calendar_segment = rendered[calendar_start:calendar_end]
    palette_pos = calendar_segment.index('class="palette"')
    status_row_pos = calendar_segment.index('class="status-row')
    assert palette_pos < status_row_pos, "expected the palette to precede the connection block's own status row"
    disconnect_btn_match = re.search(
        r'<button type="submit" form="([^"]*)" class="calendar-disconnect-btn">', calendar_segment)
    assert disconnect_btn_match, "expected the Disconnect button inside the Calendar row"
    disconnect_form_needle = '<form id="%s"' % config_page.CALENDAR_DISCONNECT_FORM_ID
    assert disconnect_form_needle not in calendar_segment, (
        "expected the disconnect form OUTSIDE the Calendar row, found it inside")
    assert disconnect_btn_match.group(1) == config_page.CALENDAR_DISCONNECT_FORM_ID, (
        "expected the Disconnect button's form= to name %r, got %r"
        % (config_page.CALENDAR_DISCONNECT_FORM_ID, disconnect_btn_match.group(1)))
    assert disconnect_form_needle in rendered[calendar_end:], (
        "expected the disconnect form as a sibling of the whole Aspect card")
    assert config_page.DIRTY_SECTION_ATTR in rendered[:calendar_start], (
        "expected the Aspect card's own dirty-section tracking attribute to precede the row")


def test_calendar_row_no_inline_js_and_palette_cross_submits_form():
    """the calendar row renders no inline event-handler attribute and no <script> tag, and every
    calendar_theme_id radio in its palette cross-submits into the settings form via
    form=settings-form (CFG-85, replacing the retired calendar-card no-inline-JS/chip-grid
    cross-submits check)"""
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
    with the confirm field pre-set to the accepted value, plus a plain cancel link to Display
    (D-08/A-26, retargeted from Device by 20-07-PLAN.md Task 1/D-11)"""
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
    # Calendar moved from Device to Display (20-07-PLAN.md Task 1, D-11), so the cancel link
    # points back to the page the disconnect action itself lives on.
    assert 'href="%s"' % layout.DISPLAY_ROUTE in rendered, "expected a cancel link back to the Display page"
    assert "<fieldset" not in rendered and "<legend" not in rendered, (
        "expected no <fieldset>/<legend> on the confirm page")


def test_calendar_disconnect_form_is_not_inside_settings_form_on_display_scope():
    """on the Display scope, the calendar disconnect form's opening tag appears after the
    settings form's own closing tag - it is a sibling, never a descendant (D-08/A-26, retargeted
    from Device by 20-07-PLAN.md Task 1/D-11, and again by 21-07-PLAN.md Task 1/D-14 for the
    id-first attribute order)"""
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
    immediately after the Calendar row and strictly before the Runway card's own radio input,
    never after the whole page's groups (Polish fix 4, D-14c)"""
    ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    calendar_row_index = rendered.index('data-usage="%s"' % config_page.COLOUR_USAGE_CALENDAR)
    connect_form_index = rendered.index('<form method="post" action="%s"' % config_page.CALENDAR_CONNECT_ROUTE)
    runway_index = rendered.index('name="tracked_runway"')
    assert calendar_row_index < connect_form_index < runway_index, (
        "expected Calendar row < connect form < Runway card, got %d, %d, %d"
        % (calendar_row_index, connect_form_index, runway_index))


def test_calendar_disconnect_form_absent_when_not_configured_or_on_device_scope():
    """the disconnect form is absent when the calendar is neither configured nor drifted, and
    absent from the Device scope, which never renders the Calendar group at all (D-08/A-26,
    retargeted from Display by 20-07-PLAN.md Task 1/D-11)"""
    not_connected_ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None)
    display_rendered = config_page.render(not_connected_ctx, scope=config_page.SCOPE_DISPLAY)
    assert config_page.CALENDAR_DISCONNECT_ROUTE not in display_rendered, (
        "expected no disconnect form when the calendar is not configured or drifted")
    connected_ctx = dict(cp.CALENDAR_BASE_CTX, calendar_configured=True, calendar_last_synced_at=None)
    device_rendered = config_page.render(connected_ctx, scope=config_page.SCOPE_DEVICE)
    assert config_page.CALENDAR_DISCONNECT_ROUTE not in device_rendered, (
        "expected no disconnect form on the Device scope, which never renders Calendar")


def test_calendar_status_drift_is_exclusive_and_precedes_not_configured():
    """with the stored calendar link's permissions drifted, render() emits the 'Not connected'
    verdict with the drift detail sentence - the drift branch, checked before 'not configured',
    still wins (D-02 ordering, D-14b)"""
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=False, calendar_last_synced_at=None, calendar_drift=True)
    verdict, detail = _calendar_status_parts(config_page.render(ctx, scope=config_page.SCOPE_DISPLAY))
    assert verdict == _CALENDAR_NOT_CONNECTED_ESCAPED, (
        "expected the 'Not connected' verdict when drifted, got %r" % (verdict,))
    assert detail == escape_html(config_page.CALENDAR_STATUS_PERMISSION_UNSAFE), (
        "expected the drift detail sentence, got %r" % (detail,))


def test_calendar_status_drift_names_remedy_and_nothing_forbidden():
    """the permission-drift status string names the remedy (paste the feed URL again) and names
    no path separator, filename, or part of a URL (D-02, 17-CONTEXT.md prohibitions)"""
    text = config_page.CALENDAR_STATUS_PERMISSION_UNSAFE
    assert "/" not in text and "\\" not in text, "expected no path separator in the drift status string"
    assert ".json" not in text and ".ics" not in text and "calendar_rules" not in text, (
        "expected no filename in the drift status string")
    assert "http" not in text.lower(), "expected no part of a URL in the drift status string"
    assert "paste" in text.lower() and "feed url" in text.lower(), (
        "expected the drift status to name the remedy (paste the feed URL again)")


def test_handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves(tmp_path):
    """the single most important check in this plan (D-07): a form that changes an unrelated
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
    calendar, and empties its fetched-entries registry (D-04)"""
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
    calendar's fetched-entries registry (D-05)"""
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
    written (D-07 contradiction, all-or-nothing)"""
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
