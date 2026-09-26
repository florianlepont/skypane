"""Companion view-page tests: most of the JS-source contracts
(panel-lookup.js, flight-rows.js, list-filter.js, freshness.js), the
Airlines resolve-dialog action row and unresolved-airline link, Flights'
refresh-region/row-identity/detail-reveal/Show-more contracts, and Home's
battery ring, relative-age elements and French render.

CSS/JS checks fetch served bytes from a running `companion/app.py`;
everything else calls `*_page.render()` directly, in-process.
"""
import math
import os
import re

import pytest

import companion.app as app_module
import companion.draw as draw
import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
from companion.pages import airlines_page, health_page, history_page, home_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import at_rule_blocks, css_rules, declarations_for, rules_with_selector
from server import history_db
from server.plane import illustrations


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk
    ."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def panel_lookup_js(app):
    """companion/static/panel-lookup.js's served text, fetched over HTTP
    instead of opened from disk ."""
    return served_asset(app, "/static/panel-lookup.js")


# --- module-local raw-string row locator (the summary-row sibling of
# companion_markup's Node-returning vp.row_block() - several checks below
# need a plain substring/`in`/`.count()` test over a row's own raw
# markup, which a parsed Node has no serializer for; see
# test_view_pages_02.py's own identical precedent). ---------------------

def _row_block(rendered, tag, group_index):
    pattern = r"<%s[^>]*data-filter-group=\"%d\"[^>]*>(.*?)</%s>" % (
        tag, group_index, tag)
    match = re.search(pattern, rendered, re.S)
    return match.group(1) if match else None


_SCRIPT_ROUTE_NAME_RE = re.compile(r"^[A-Z0-9_]*SCRIPT_ROUTE$")


def _all_static_script_routes():
    """Every companion/app.py `*_SCRIPT_ROUTE` constant's value - the
    served static-JS surface, enumerated from the production module's
    own registered route names rather than a filesystem glob over
    companion/static/*.js (: no production source is opened as
    text, and this floor tracks whatever app.py itself registers rather
    than going stale against a hand-written list)."""
    names = [name for name in dir(app_module) if _SCRIPT_ROUTE_NAME_RE.match(name)]
    return sorted({getattr(app_module, name) for name in names})


_HOME_RELATIVE_ELEMENT_RE = re.compile(
    r'<time datetime="([^"]*)" data-relative>([^<]*)</time>')


def _home_seeded_ctx(tmp, now, flight_ts):
    vp.seed_runway_events(tmp, [
        {"ts": flight_ts, "hex": "3c6444", "callsign": "AFR1380",
         "airline": "Air France", "origin": "ORY", "destination": "TLS",
         "confirmed_state": "departing"},
    ])
    with history_db.open_db(tmp) as conn:
        history_db.record_device_health(conn, flight_ts, battery_mv=3750)
    return {
        "state_dir": str(tmp), "now": now,
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "last_checkin_ts": flight_ts,
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "ok",
                         "battery_state": "ok",
                         "device_detail_html": "",
                         "pipeline_html": ""},
        "simple_mode": False,
    }


# --- panel-lookup.js's date-math ban (B5, Task 1) --------

_PANEL_LOOKUP_FORBIDDEN_DATE_TOKENS = (
    r"\bnew\s+Date\(", r"\bDate\.now\b", r"\btoISOString\b", r"\btoLocaleDateString\b",
    r"\btoLocaleTimeString\b", r"\btoLocaleString\b", r"\bgetHours\b", r"\bgetMinutes\b",
    r"\bgetTime\b", r"\bIntl\.DateTimeFormat\b",
)


def test_panel_lookup_js_does_no_date_math_of_any_kind(panel_lookup_js):
    """companion/static/panel-lookup.js contains no date-parsing or date-formatting API at all
    (new Date/Date.now/toISOString/toLocale*/getHours/getMinutes/getTime/Intl.DateTimeFormat)
    and assigns the first-seen/last-seen attribute values straight to textContent — the
    property that keeps Paris-local rule enforceable server-side (B5,
    Task 1)"""
    from companion_markup import strip_js_comments_and_strings

    stripped = strip_js_comments_and_strings(panel_lookup_js)
    found = [pattern for pattern in _PANEL_LOOKUP_FORBIDDEN_DATE_TOKENS
             if re.search(pattern, stripped)]
    assert not found, (
        "expected panel-lookup.js to do no date parsing or formatting, found %r" % (found,))
    for attr in (airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
                 airlines_page._VIEW_PANEL_LAST_SEEN_ATTR):
        assert ('getAttribute("%s")' % attr) in panel_lookup_js, (
            "expected panel-lookup.js to read %s off the trigger" % (attr,))
    for var in ("firstSeen", "lastSeen"):
        assert ("textContent = %s;" % var) in panel_lookup_js, (
            "expected panel-lookup.js to assign %s straight to textContent, unmodified" % (var,))


def test_resolve_dialog_save_and_close_share_one_action_row(tmp_path, served_css):
    """the resolve dialog's Save and Close share ONE .lightbox__actions row — quiet Close first,
    primary Save second and re-attached to its form by the native form= attribute — while the
    no-JS fallback keeps its own submit inside its own form, and the row's rule declares
    flex/centre/space-between with no shared height (C4) and no .btn-- family (B5,
     Task 1)"""
    rendered = airlines_page.render({})
    row = re.search(
        r'<div class="%s">(.*?)</div>' % re.escape(airlines_page.LIGHTBOX_ACTIONS_CLASS),
        rendered, re.S)
    assert row is not None, "expected one .lightbox__actions row in the rendered dialog"
    assert rendered.count('class="%s"' % airlines_page.LIGHTBOX_ACTIONS_CLASS) == 1
    body = row.group(1)
    assert airlines_page._VIEW_PANEL_CLOSE_ATTR in body
    dialog_form_id = airlines_page.MANUAL_RESOLVE_FORM_ID + "-dialog"
    assert ('<button type="submit" form="%s">' % dialog_form_id) in body
    close_at = body.index(airlines_page._VIEW_PANEL_CLOSE_ATTR)
    submit_at = body.index('type="submit"')
    assert close_at < submit_at, "expected the quiet Close to precede the primary in the action row"
    assert ('id="%s"' % dialog_form_id) in rendered
    dialog_form = re.search(
        r'<form class="%s" id="%s".*?</form>'
        % (re.escape(airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS), re.escape(dialog_form_id)),
        rendered, re.S)
    assert dialog_form is not None, "expected to locate the dialog's resolve form"
    assert 'type="submit"' not in dialog_form.group(0), (
        "expected the dialog form's own submit to have moved into the action row")

    vp.seed_unresolved_prefixes(tmp_path, {
        "XYZ": {
            "count": 4, "first_seen": "2026-09-09T15:49:27+00:00",
            "last_seen": "2026-09-11T06:05:00+00:00", "example_callsign": "XYZ123",
        },
    })
    fallback = airlines_page.render(
        {"state_dir": str(tmp_path), "now": "2026-09-13T09:00:00+00:00", "resolve_prefix": "XYZ"})
    nojs_form = re.search(
        r'<form class="%s" id="%s" .*?</form>'
        % (re.escape(airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS),
           re.escape(airlines_page.MANUAL_RESOLVE_FORM_ID)),
        fallback, re.S)
    assert nojs_form is not None, (
        "expected the no-JS fallback's resolve form with its own unsuffixed id")
    assert 'type="submit"' in nojs_form.group(0), (
        "expected the no-JS fallback's submit to stay inside its own form — the scriptless "
        "floor must not depend on a form= re-attachment")

    rule = declarations_for(served_css, "." + airlines_page.LIGHTBOX_ACTIONS_CLASS)
    assert rule.get("display") == "flex"
    assert rule.get("align-items") == "center"
    assert rule.get("justify-content") == "space-between"
    for forbidden in ("height", "min-height", "border-radius"):
        assert forbidden not in rule, (
            "expected the action row to declare no %r, got %r" % (forbidden, rule))
    btn_family = [selector for rule in css_rules(served_css) for selector in rule.selectors
                  if ".btn--" in selector]
    assert not btn_family, "expected no .btn-- family anywhere in style.css, got %r" % (btn_family,)


def test_airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary():
    """a normal Airlines render carries no Editing badge and no per-card Replace control
    anywhere (both deleted outright) — while every airline-card__zoom trigger still
    carries the SAME full data-view-panel-* vocabulary, its size derived from the module's
    own _VIEW_PANEL_*_ATTR constants rather than a hardcoded number"""
    rendered = airlines_page.render({})

    assert "banner__pill" not in rendered, (
        "expected no Editing badge anywhere — the page-wide editing mode is gone")
    assert "calendar-disconnect-btn" not in rendered, (
        "expected zero per-card Replace controls anywhere — the affordance moved into the "
        "dialog (CFG-81)")

    triggers = re.findall(
        r'<(?:button type="button"|a href="[^"]*") class="airline-card__zoom" .*?</(?:button|a)>',
        rendered, re.S)
    assert len(triggers) >= 2, "expected the curated grid to render triggers to count vocabulary against"

    attr_names = {
        getattr(airlines_page, name) for name in dir(airlines_page)
        if re.match(r"^_VIEW_PANEL_[A-Z0-9_]*_ATTR$", name)
        and name != "_VIEW_PANEL_CLOSE_ATTR"
    }
    expected_count = len(attr_names)

    counts = set()
    for trigger in triggers:
        found = set(re.findall(r'(data-view-panel-[a-z-]+)=', trigger))
        assert found == attr_names, (
            "expected every airline-card__zoom trigger to carry the same data-view-panel-* "
            "attribute set %r, got %r" % (sorted(attr_names), sorted(found)))
        counts.add(len(found))
    assert counts == {expected_count}, (
        "expected every trigger to carry exactly %d data-view-panel-* attributes, got %r"
        % (expected_count, counts))


def test_airlines_manual_count_is_a_filter_control_in_the_filter_bar(tmp_path, served_css):
    """the manual-resolution count renders as a real filter control INSIDE the Airlines filter
    bar wearing .airline-card__chip's label voice — the 12px bare link and its copied
    [data-filter-clear] property list are retired, leaving only a hover-additive rule — and
    one entry reads '1 manual resolution' (FR '1 resolution manuelle') while two read
    '2 manual resolutions' (X7 + /B16, Task 2)"""
    registry = {"QQQ": {"airline_name": "Air France",
                        "created_at": "2026-09-01T10:00:00+00:00"}}
    rendered = airlines_page.render({"state_dir": str(tmp_path), "manual_resolutions": registry})
    two = airlines_page.render({"state_dir": str(tmp_path), "manual_resolutions": dict(
        registry, RRR={"airline_name": "KLM", "created_at": "2026-09-02T10:00:00+00:00"})})
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = airlines_page.render(
            {"state_dir": str(tmp_path), "manual_resolutions": registry})
    finally:
        prefs.set_request_prefs(lang="en")

    bar = re.search(r'<div class="filter-bar">(.*?)</div>\s*<div class="empty-state"',
                    rendered, re.S)
    assert bar is not None, "expected to locate the rendered filter bar"
    assert "data-filter-set=\"manual\"" in bar.group(1), (
        "expected the manual-resolution control INSIDE the filter bar, not as loose prose below it")
    assert 'class="airline-card__chip manual-summary"' in bar.group(1), (
        "expected the control to reuse the card-chip label voice verbatim")
    assert rendered.count('data-filter-set="manual"') == 1

    assert not rules_with_selector(served_css, ".manual-summary"), (
        "expected the .manual-summary base rule block to be gone — the chip class now carries "
        "the whole treatment, and a surviving copy is a fork")
    assert rules_with_selector(served_css, ".manual-summary:hover"), (
        "expected .manual-summary to survive as the hover-only additive rule")

    assert "1 manual resolution<" in rendered, (
        "expected the singular form for exactly one manual resolution, got %r"
        % (re.findall(r'data-filter-set="manual">([^<]*)<', rendered),))
    assert "2 manual resolutions<" in two, (
        "expected the plural form for two manual resolutions, got %r"
        % (re.findall(r'data-filter-set="manual">([^<]*)<', two),))
    assert "1 résolution manuelle<" in rendered_fr, (
        "expected the French singular, got %r"
        % (re.findall(r'data-filter-set="manual">([^<]*)<', rendered_fr),))


def test_airlines_grid_is_two_fixed_columns_below_960px(served_css):
    """below 960px .illustration-grid takes a FIXED repeat(2, minmax(0, 1fr)) template — two
    cards per row with a zero column minimum — while the desktop auto-fill idiom above 960px
    is left untouched (X7, Task 2)"""
    declaration = declarations_for(
        served_css, ".illustration-grid", at_rules=("@media (max-width: 959.98px)",))
    assert declaration, (
        "expected a sub-960px .illustration-grid rule giving the grid a fixed template")
    assert declaration.get("grid-template-columns") == "repeat(2, minmax(0, 1fr))", (
        "expected exactly two columns with a zero minimum, got %r" % (declaration,))

    base = declarations_for(served_css, ".illustration-grid")
    assert "auto-fill" in base.get("grid-template-columns", ""), (
        "expected the desktop auto-fill idiom to be left alone above 960px, got %r" % (base,))


def test_unresolved_link_absent_for_resolved_airline(tmp_path):
    """a formatted row with a resolved airline produces a Flight cell (desktop) and a phone
    card (mobile) carrying neither a one-hop resolve link nor the retired two-hop Health
    route"""
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": "lkr01", "callsign": "LINKRES",
            "airline": "AFR", "origin": "LFPO", "destination": "LFPG",
        },
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = _row_block(rendered, "tr", 0)
    li_block = _row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None, (
        "could not locate row block for a resolved-airline row")
    for label, block in (("desktop cell", tr_block), ("mobile card", li_block)):
        assert "?resolve=" not in block, (
            "did not expect a resolve link in the %s for a resolved airline" % label)
        assert "/health" not in block, (
            "did not expect the retired two-hop Health link in the %s" % label)


def test_unresolved_link_present_once_each_for_unresolved_airline(tmp_path):
    """a formatted row whose airline is unresolved produces exactly one ONE-HOP resolve anchor
    in the desktop Flight cell and exactly one on the phone card, both naming the prefix
    derived from that row's own callsign"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "lku01", "callsign": "LINKUNR"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = _row_block(rendered, "tr", 0)
    li_block = _row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None, (
        "could not locate row block for an unresolved-airline row")
    href_attr = 'href="%s"' % (history_page.RESOLVE_LINK_HREF_TEMPLATE % "LIN")
    for label, block in (("desktop cell", tr_block), ("mobile card", li_block)):
        assert block.count(href_attr) == 1, (
            "expected exactly one one-hop resolve link (%s) in the %s, found %d"
            % (href_attr, label, block.count(href_attr)))
        assert history_page.RESOLVE_LINK_TEXT in block
        assert "/health" not in block, (
            "expected the retired two-hop Health route to be gone from the %s" % label)
    assert history_page.resolve_prefix_for_callsign("LINKUNR") == "LIN", (
        "expected the prefix to be derived from the callsign itself")


def test_unresolved_link_keyed_on_airline_not_route(tmp_path):
    """a row whose route is unresolved but whose airline IS resolved produces no unresolved-
    airline link - the link is keyed on the airline label, not on the route label"""
    from server.plane import render as panel_render

    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "lkro1", "callsign": "LINKROUTE",
         "airline": "AFR"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = _row_block(rendered, "tr", 0)
    li_block = _row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None, (
        "could not locate row block for a route-only-unresolved row")
    assert panel_render.ROUTE_FALLBACK_TEXT in tr_block, (
        "expected the Route cell to still render the fallback text")
    assert "?resolve=" not in tr_block, (
        "did not expect a resolve link when only the route is unresolved")
    assert "?resolve=" not in li_block, "did not expect a resolve link on the phone card either"


def test_airline_fallback_distinct_from_route_fallback(tmp_path, served_css):
    """a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct
    strings in two distinct columns, and the unresolved-link's spacing class is styled in
    style.css and present in the rendered anchor"""
    from server.plane import render as panel_render

    assert history_page.AIRLINE_FALLBACK_TEXT != panel_render.ROUTE_FALLBACK_TEXT
    spacing_class = re.compile(
        r"\.%s(?![-\w])" % re.escape(history_page.UNRESOLVED_LINK_CLASS.split()[-1]))
    assert any(spacing_class.search(selector)
               for rule in css_rules(served_css) for selector in rule.selectors), (
        "expected UNRESOLVED_LINK_CLASS's spacing class to be styled in style.css")

    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "af01", "callsign": "AIRFB1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    tr_block = _row_block(rendered, "tr", 0)
    li_block = _row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None, (
        "could not locate row block for a no-airline row")
    for label, block in (("desktop", tr_block), ("mobile", li_block)):
        assert history_page.AIRLINE_FALLBACK_TEXT in block
        assert panel_render.ROUTE_FALLBACK_TEXT in block
        assert block.count(panel_render.ROUTE_FALLBACK_TEXT) == 1, (
            "expected ROUTE_FALLBACK_TEXT exactly once (Route column only) in the %s row, "
            "found %d" % (label, block.count(panel_render.ROUTE_FALLBACK_TEXT)))
        assert 'class="%s"' % history_page.UNRESOLVED_LINK_CLASS in block, (
            "expected the unresolved-link's class attribute in the %s row" % label)


def test_hex_only_row_promotes_hex_to_primary(tmp_path):
    """a callsign-less row's desktop Flight cell is empty with zero copy buttons and no
    visible hex; the mobile card still promotes the hex to its primary slot with a
    no-copy-button 'no callsign' note; a callsign+hex row is unaffected; a row with
    neither renders without raising"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:02:00+00:00", "hex": "34560d"},
        {"ts": "2026-08-27T10:01:00+00:00"},
        {"ts": "2026-08-27T10:00:00+00:00", "callsign": "CTRL01"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))

    tr_block = _row_block(rendered, "tr", 0)
    li_block = _row_block(rendered, "li", 0)
    assert tr_block is not None and li_block is not None, (
        "could not locate row block for the hex-only row")
    assert "34560d" not in tr_block, (
        "did not expect the hex value visible in the desktop summary row")
    assert tr_block.count("data-copy-value") == 0, (
        "expected zero copy buttons in the hex-only desktop row, got %d"
        % tr_block.count("data-copy-value"))

    assert '<span class="cell-primary mono">34560d</span>' in li_block, (
        "expected the mobile card's primary line to carry the hex")
    assert ('<span class="cell-secondary">%s</span>' % history_page.NO_CALLSIGN_NOTE_TEXT) in li_block, (
        "expected the mobile card's primary line to carry the no-callsign note")

    tr_block_1 = _row_block(rendered, "tr", 1)
    assert tr_block_1 is not None, "could not locate row block for the both-falsy row"
    flight_td = re.search(r"<td>(.*?)</td>", tr_block_1, re.S)
    assert flight_td is not None, "expected a <td> for the both-falsy row's When cell"
    assert tr_block_1.count("data-copy-value") == 0, (
        "expected zero copy buttons in the both-falsy desktop row")

    tr_block_2 = _row_block(rendered, "tr", 2)
    assert tr_block_2 is not None and "CTRL01" in tr_block_2, (
        "expected the control row's callsign to render unchanged")
    assert history_page.NO_CALLSIGN_NOTE_TEXT not in tr_block_2, (
        "did not expect the no-callsign note on a row with a callsign")


def test_resolve_link_template_matches_the_airlines_resolve_view():
    """history_page.RESOLVE_LINK_HREF_TEMPLATE is built from airlines_page.AIRLINES_ROUTE and
    RESOLVE_QUERY_PARAM (never a re-typed literal), the retired two-hop Health constant is
    gone, and resolve_prefix_for_callsign() derives a prefix only for a callsign the
    registry writer's own shape gate would accept"""
    from server.plane import manual_resolutions

    expected = "%s?%s=%%s" % (airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
    assert history_page.RESOLVE_LINK_HREF_TEMPLATE == expected
    assert not hasattr(history_page, "UNRESOLVED_LINK_HREF"), (
        "expected the retired two-hop Health link constant to be gone")
    for callsign, expected_prefix in (
            ("AFR1234", "AFR"), ("tvf16vb ", "TVF"), ("ZZP9", "ZZP"),
            ("ZZP", None), ("", None), (None, None), ("12A345", None)):
        got = history_page.resolve_prefix_for_callsign(callsign)
        assert got == expected_prefix, (
            "expected resolve_prefix_for_callsign(%r) -> %r, got %r"
            % (callsign, expected_prefix, got))
    assert manual_resolutions.normalise_prefix("AFR") == "AFR", (
        "expected the shared prefix normaliser to accept a derived prefix")


def test_day_separators_group_rows_by_europe_paris_calendar_day(tmp_path):
    """the rendered Flights table carries exactly one day-separator row per EUROPE/PARIS
    calendar day present in the rows — Today / Yesterday / an absolute date, translated in
    both languages — and a row whose UTC day differs from its Paris day is grouped by the
    Paris one"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-26T10:00:00+00:00", "hex": "ds01", "callsign": "DAYONE"},
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "ds02", "callsign": "DAYTWO"},
        {"ts": "2026-08-27T22:30:00+00:00", "hex": "ds03", "callsign": "DAYTHREE"},
    ])
    now = "2026-08-28T09:00:00+00:00"
    rendered_en = history_page.render(vp.history_ctx(tmp_path, now=now))
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path, now=now))
    finally:
        prefs.set_request_prefs(lang="en")

    expected = {
        "en": ["Today", "Yesterday", "26 Aug"],
        "fr": ["Aujourd’hui", "Hier", "26 août"],
    }
    for lang, rendered in (("en", rendered_en), ("fr", rendered_fr)):
        rows = re.findall(
            r'<tr class="flight-day-row"><th scope="colgroup" colspan="6"'
            r' class="text-label">(.*?)</th></tr>', rendered)
        assert rows == expected[lang], (
            "expected the %s separators to read %r, got %r" % (lang, expected[lang], rows))
        table = vp.table_markup(rendered)
        assert table is not None, "could not locate the rendered table (%s)" % lang
        first_sep = table.index('class="flight-day-row"')
        second_sep = table.index('class="flight-day-row"', first_sep + 1)
        assert first_sep < table.index("DAYTHREE") < second_sep, (
            "expected the 22:30 UTC row (00:30 Paris the next day) to sit under its own "
            "separator (%s)" % lang)
        assert table.index("DAYTWO") >= second_sep, (
            "expected the 10:00 UTC row to sit under the SECOND separator (%s)" % lang)


def test_day_label_is_the_paris_day_formatters_own_output_and_never_sticky(served_css):
    """the day separator's absolute label is the day portion of layout.local_clock_text()'s own
    cross-day output in both languages, paris_day() degrades to None rather than raising, and
    the separator's CSS rule declares no positioning

    A source-text grep for the word "strftime" is dropped: the equivalence asserted below (the
    day label equals the day PORTION of layout.local_clock_text()'s own cross-day output)
    already proves the label is the shared Paris-local formatter's own output rather than a
    second date-formatting path, which is all that grep added.
    """
    raw_ts = "2026-08-26T10:00:00+00:00"
    parsed = layout.parse_iso(raw_ts)
    day = history_page.paris_day(raw_ts)
    assert day is not None, "expected paris_day() to date a well-formed timestamp"
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            label = history_page.day_label(day, None)
            formatter = layout.local_clock_text(parsed, layout._FULL_TIMESTAMP_SENTINEL_NOW)
        finally:
            prefs.set_request_prefs(lang="en")
        assert formatter.rsplit(" ", 1)[0] == label, (
            "expected the %s absolute day label (%r) to equal the day portion of "
            "local_clock_text()'s own cross-day output (%r)" % (lang, label, formatter))
    for bad in (None, "", "not-a-timestamp", 17):
        assert history_page.paris_day(bad) is None, "expected paris_day(%r) to degrade to None" % (bad,)
    assert history_page.day_label(day, day) == i18n.t_lang("Today", "en"), (
        "expected a same-day group to read Today")

    rule = declarations_for(served_css, ".flight-day-row th")
    combined = " ".join("%s:%s" % (k, v) for k, v in rule.items())
    assert "position" not in combined and "sticky" not in combined, (
        "expected the day separator to declare no positioning at all, got %r" % (rule,))


def test_every_flights_row_carries_a_stable_event_identity(tmp_path):
    """every rendered Flights row carries a non-empty, unique event identity in BOTH
    representations, the table and the card list name the same event set, and a newer
    detection arriving at the top leaves every existing row's identity unchanged — the
    property the row's position does not have and the whole basis of the new-row highlight"""
    older = [
        {"ts": "2026-08-27T09:00:00+00:00", "hex": "id01", "callsign": "IDONE"},
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "id02", "callsign": "IDTWO"},
    ]
    vp.seed_runway_events(tmp_path, older)
    before = history_page.render(vp.history_ctx(tmp_path))
    attr = layout.REFRESH_ROW_ID_ATTR

    def _ids(rendered, tag):
        return re.findall(r"<%s[^>]*\s%s=\"([^\"]*)\"" % (tag, re.escape(attr)), rendered)

    tr_ids = _ids(before, "tr")
    li_ids = _ids(before, "li")
    assert len(tr_ids) == 4, (
        "expected both the summary row and its sibling detail row to carry %r in the "
        "desktop table (4 for 2 events), found %r" % (attr, tr_ids))
    assert len(li_ids) == 2, "expected every phone card to carry %r, found %r" % (attr, li_ids)
    assert all(tr_ids + li_ids), "expected every identity attribute to be non-empty"
    assert sorted(set(tr_ids)) == sorted(set(li_ids)), (
        "expected the table and the card list to name the SAME events")
    assert len(set(li_ids)) == len(li_ids), "expected two rows never to share one identity"

    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T11:00:00+00:00", "hex": "id03", "callsign": "IDTHREE"},
    ])
    after = history_page.render(vp.history_ctx(tmp_path))
    after_ids = _ids(after, "li")
    assert len(after_ids) == 3, "expected three phone cards after the insertion, got %r" % (after_ids,)
    assert after_ids[1:] == li_ids, (
        "expected a newer event arriving at the TOP to leave every existing row's identity "
        "untouched — before %r, after %r" % (li_ids, after_ids))
    assert after_ids[0] not in li_ids, (
        "expected the newly-arrived event to carry an identity no existing row already had")


def test_flights_declares_its_refresh_regions_and_never_the_filter_input(tmp_path):
    """the rendered Flights page carries exactly one data-loaded-at marker and a witness for
    every one of its REFRESH_SWAP_SELECTORS_BY_PAGE regions, and no region names the filter
    input list-filter.js captured at load"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "rr01", "callsign": "REGION"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert rendered.count("data-loaded-at") == 1, (
        "expected exactly one data-loaded-at marker on Flights, found %d"
        % rendered.count("data-loaded-at"))
    selectors = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_FLIGHTS]
    witnesses = {
        ".page-header__freshness": 'class="page-header__freshness',
        "ul.history-cards": '<ul class="history-cards"',
        ".data-table-wrap": 'class="data-table-wrap"',
        "[data-filter-count]": "data-filter-count ",
        ".flights-more": 'class="flights-more"',
    }
    assert sorted(witnesses) == sorted(selectors), (
        "Flights' registry entry is %r, and this check knows how to witness %r"
        % (sorted(selectors), sorted(witnesses)))
    for selector in selectors:
        assert witnesses[selector] in rendered, (
            "registry region %r matches nothing in the rendered Flights page" % (selector,))
    for selector in selectors:
        assert "data-filter-input" not in selector, (
            "the filter input is a swap target (%r) — list-filter.js captures it once at "
            "load, so replacing it leaves the filter permanently dead" % (selector,))


def test_detail_row_height_animates_and_a_closed_row_is_unreachable(tmp_path, served_css, app):
    """the Flights detail row animates open through a grid reveal wrapper inside its own <td>
    (grid-template-rows 0fr, var(--motion-fast), an @starting-style entry, scoped to the
    class flight-rows.js adds to <html>), neither interpolate-size nor calc-size() appears,
    and the collapsed end state is still display: none — the one state that takes a closed
    row out of both the tab order and the accessibility tree (D3/,
    Task 2)"""
    entry = declarations_for(
        served_css, ".flight-rows-live .flight-detail-row__reveal", at_rules=("@starting-style",))
    assert entry.get("grid-template-rows") == "0fr", (
        "expected the detail row's height to animate from grid-template-rows: 0fr in an "
        "@starting-style entry for the reveal wrapper, got %r" % (entry,))
    for rule in css_rules(served_css):
        for prop, value in rule.declarations:
            for banned in ("interpolate-size", "calc-size("):
                assert banned not in prop and banned not in value, (
                    "companion/static/style.css declares %r in %r — Chromium-only, banned by "
                    "23-01's own guard" % (banned, rule.selectors))

    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "rv01", "callsign": "REVEAL"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    detail = vp.detail_row_block(rendered, 0)
    assert detail is not None, "expected a server-rendered detail row"
    assert "flight-detail-row__reveal" in detail, (
        "expected the detail cell's content to sit inside the grid reveal wrapper")
    assert detail.index("flight-detail-row__reveal") < detail.index("flight-detail-row__grid"), (
        "expected the reveal wrapper to WRAP the detail grid, not to follow it")

    js = vp.strip_js_line_and_block_comments(served_asset(app, "/static/flight-rows.js"))
    assert "flight-rows-live" in js, (
        "expected flight-rows.js to add its own live-script class")
    reveal = declarations_for(
        served_css, ".flight-rows-live .flight-detail-row__reveal")
    assert reveal.get("display") == "grid" and "grid-template-rows" in reveal, (
        "expected the reveal wrapper to be a grid whose row track is what animates, got %r"
        % (reveal,))
    assert reveal.get("transition", "").find("var(--motion-fast)") != -1, (
        "expected the reveal transition to spend var(--motion-fast), got %r" % (reveal,))

    collapsed = declarations_for(served_css, ".flight-detail-row--collapsed")
    assert collapsed.get("display") == "none", (
        "expected the collapsed detail row to resolve to display: none, got %r" % (collapsed,))


def test_the_chevron_turns_and_carries_no_reduced_motion_block_of_its_own(served_css):
    """the row-toggle chevron transitions TRANSFORM on var(--motion-fast) and adds no per-rule
    reduced-motion block — the global override already covers a plain transform for free,
    and the stylesheet's live prefers-reduced-motion count is unmoved at 3 (D3/,
    references/control-density.md:78, Task 2)"""
    glyph = declarations_for(served_css, ".row-toggle__glyph")
    assert glyph, "expected a .row-toggle__glyph rule"
    transition = glyph.get("transition", "")
    assert transition, (
        "expected the chevron to take a transition of its own, got %r" % (glyph,))
    assert "var(--motion-fast)" in transition, (
        "expected the chevron transition to spend var(--motion-fast), got %r" % (transition,))
    assert "transform" in transition, (
        "expected the chevron to transition TRANSFORM specifically, got %r" % (transition,))
    reduced_motion = [block for block in at_rule_blocks(served_css)
                      if "prefers-reduced-motion" in block]
    assert len(reduced_motion) == 3, (
        "expected companion/static/style.css to carry exactly 3 prefers-reduced-motion blocks, "
        "got %r" % (reduced_motion,))


def test_the_phone_cards_own_face_is_its_disclosure_summary(tmp_path):
    """the phone card's own face IS the native disclosure's <summary> — the primary line, the
    secondary line, the time and the thumbnail and airline name all inside it, so a tap
    anywhere opens the card with no script at all — while the one-hop resolve link stays on
    the card and OUT of the summary, and the disclosure body still holds exactly the three
    copy buttons"""
    from PIL import Image

    key = illustrations.normalise_airline_key("Air France")
    override_path = illustrations.override_path_for_key(key, str(tmp_path))
    os.makedirs(os.path.dirname(override_path), exist_ok=True)
    Image.new("RGB", (4, 4), color=(200, 200, 200)).save(override_path, format="PNG")
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "fc01", "callsign": "FACEONE",
         "airline": "Air France"},
        {"ts": "2026-08-27T09:00:00+00:00", "hex": "fc02", "callsign": "FACETWO"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    li = _row_block(rendered, "li", 0)
    assert li is not None, "could not locate the phone card"
    summary = re.search(r'<summary class="history-card__summary">(.*?)</summary>', li, re.S)
    assert summary is not None, (
        "expected the card's own face to BE the disclosure's <summary>, got %r" % (li[:300],))
    face = summary.group(1)
    for part in ("history-card__primary", "history-card__secondary",
                 "history-card__airline", "history-card__thumb",
                 "history-card__airline-name", "history-card__time"):
        assert part in face, "expected %r to be part of the card's tappable face" % (part,)

    li_unresolved = _row_block(rendered, "li", 1)
    assert li_unresolved is not None, "could not locate the unresolved-airline card"
    assert history_page.RESOLVE_LINK_TEXT in li_unresolved, (
        "expected the unresolved card to still carry its one-hop resolve link somewhere")
    unresolved_summary = re.search(
        r'<summary class="history-card__summary">(.*?)</summary>', li_unresolved, re.S)
    assert unresolved_summary is not None, "expected the unresolved card to have a face summary too"
    assert history_page.RESOLVE_LINK_TEXT not in unresolved_summary.group(1), (
        "did not expect the resolve LINK inside the summary")
    assert "<a " not in unresolved_summary.group(1) and "<button" not in unresolved_summary.group(1), (
        "did not expect any nested control inside the card's summary")

    assert li.count("<details") == 1 and li.count("</details>") == 1, (
        "expected exactly one <details> per card")
    body = li[li.index("</summary>"):]
    assert body.count("data-copy-value") == 3, (
        "expected the disclosure body to still hold exactly the three copy buttons, got %d"
        % body.count("data-copy-value"))


def test_history_card_primary_grid_pins_the_timestamp_track(tmp_path, served_css):
    """the phone summary card's .history-card__primary line is a two-track CSS grid
    (minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time
    (white-space: nowrap, no margin-left: auto), and all three primary_value_html branches —
    callsign, hex-plus-note, empty — produce a child set the grid can place with no third,
    unclassified top-level child (2026-09-17 audit P1, Task 2)"""
    primary_block = declarations_for(served_css, ".history-card__primary")
    assert primary_block, "could not locate the .history-card__primary rule block"
    assert primary_block.get("display") == "grid", (
        "expected .history-card__primary to declare display: grid, got %r" % (primary_block,))
    tracks = primary_block.get("grid-template-columns", "").strip()
    assert re.match(r"^minmax\(\s*0\s*,\s*1fr\s*\)\s+auto$", tracks), (
        "expected grid-template-columns to declare exactly two tracks, got %r" % (tracks,))
    assert "justify-content" not in primary_block, (
        "expected justify-content ABSENT from .history-card__primary, found it in %r"
        % (primary_block,))

    time_block = declarations_for(served_css, ".history-card__time")
    assert time_block, "could not locate the .history-card__time rule block"
    assert time_block.get("white-space") == "nowrap", (
        "expected .history-card__time to declare white-space: nowrap, got %r" % (time_block,))
    assert "margin-left" not in time_block, (
        "expected .history-card__time to declare no margin-left, found %r" % (time_block,))

    branches = (
        ("callsign", {"ts": "2026-09-21T10:00:00+00:00", "callsign": "GRD01"}),
        ("hex-plus-note", {"ts": "2026-09-21T10:00:00+00:00", "hex": "abc123"}),
        ("empty", {"ts": "2026-09-21T10:00:00+00:00"}),
    )
    for name, fields in branches:
        sub = tmp_path / name
        vp.seed_runway_events(sub, [fields])
        rendered = history_page.render(vp.history_ctx(sub))
        li_block = _row_block(rendered, "li", 0)
        assert li_block is not None, "%s branch: could not locate the rendered card" % name
        primary_match = re.search(
            r'<div class="history-card__primary">(.*?)</div>', li_block, re.S)
        assert primary_match is not None, (
            "%s branch: could not locate .history-card__primary markup" % name)
        primary_markup = primary_match.group(1)
        assert primary_markup.count('<span class="history-card__time">') == 1, (
            "%s branch: expected exactly one history-card__time (track-2) child" % name)
        track2_start = primary_markup.index('<span class="history-card__time">')
        track1_markup = primary_markup[:track2_start]
        track1_children = re.findall(
            r'<span class="(cell-primary|cell-secondary)[^"]*"', track1_markup)
        assert track1_children, (
            "%s branch: expected at least one track-1 child before the timestamp span" % name)
        unclassified = re.sub(
            r'<span class="cell-(?:primary|secondary)[^"]*">.*?</span>', "",
            track1_markup, flags=re.S).strip()
        assert not unclassified, (
            "%s branch: expected every child before the timestamp span to be a classified "
            "track-1 child, found leftover unclassified markup %r"
            % (name, unclassified))


def test_flights_reveal_state_reproduces_from_the_url_alone(tmp_path, app):
    """two renders of a 36-row fixture at the SAME ?limit= value produce byte-identical
    pagination state (standing in for freshness.js's own re-fetch of the unchanged
    window.location.href), '.flights-more' is a declared swap region, and freshness.js
    carries exactly one fetch( call targeting window.location.href verbatim — the
    structural half of the refresh-survival property this harness can prove without a
    browser"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-%02dT10:00:00+00:00" % i, "hex": "rv%02d" % i, "callsign": "REV%02d" % i}
        for i in range(1, 37)
    ])
    ctx = vp.history_ctx(tmp_path, flights_limit="30")
    first = history_page.render(ctx)
    second = history_page.render(ctx)
    for label, rendered in (("first", first), ("second", second)):
        card_count = rendered.count('<li class="history-card"')
        assert card_count == 30, "%s render: expected 30 cards, got %d" % (label, card_count)
        nav_match = re.search(r'<nav class="flights-more">(.*?)</nav>', rendered, re.S)
        assert nav_match is not None, "%s render: expected a non-empty Show-more nav" % label
        href_match = re.search(r'href="([^"]+)"', nav_match.group(1))
        assert href_match is not None and href_match.group(1) == "/flights?limit=45", (
            "%s render: expected the Show-more anchor's href to be /flights?limit=45, got %r"
            % (label, href_match.group(1) if href_match else None))
    first_cards_match = re.search(r'<ul class="history-cards">(.*?)</ul>', first, re.S)
    second_cards_match = re.search(r'<ul class="history-cards">(.*?)</ul>', second, re.S)
    assert first_cards_match is not None and second_cards_match is not None
    assert first_cards_match.group(1) == second_cards_match.group(1), (
        "expected two renders of the SAME ?limit= ctx to produce byte-identical "
        "ul.history-cards markup")

    selectors = layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_FLIGHTS]
    assert ".flights-more" in selectors, (
        "expected '.flights-more' to be a declared REFRESH_SWAP_SELECTORS_BY_PAGE region, "
        "got %r" % (selectors,))

    js_source = vp.strip_js_line_and_block_comments(served_asset(app, "/static/freshness.js"))
    fetch_calls = re.findall(r"fetch\(\s*([^,)]+)", js_source)
    assert len(fetch_calls) == 1, (
        "expected exactly one fetch( call in freshness.js, found %d: %r"
        % (len(fetch_calls), fetch_calls))
    assert fetch_calls[0].strip() == "window.location.href", (
        "expected freshness.js's one fetch( call to target window.location.href, got %r"
        % (fetch_calls[0].strip(),))


def test_flights_reveal_control_is_a_plain_anchor_no_script_mentions(tmp_path, app):
    """the Show-more anchor renders with an href and no onclick/data- attribute and is never a
    <button> or <form>, and zero companion/static/*.js files mention its 'flights-more'
    class (scanned-route floor >= 17, printed on failure) — a no-JS control proof, not merely
    a render"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-%02dT10:00:00+00:00" % i, "hex": "nj%02d" % i, "callsign": "NOJS%02d" % i}
        for i in range(1, 21)
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    nav_match = re.search(r'<nav class="flights-more">(.*?)</nav>', rendered, re.S)
    assert nav_match is not None, "expected a non-empty <nav class=\"flights-more\"> in a 20-row render"
    nav_html = nav_match.group(1)
    assert nav_html.startswith("<a ") and nav_html.count("<a ") == 1, (
        "expected the Show-more nav's one child to be a plain <a>, got %r" % (nav_html,))
    assert "<button" not in nav_html and "<form" not in nav_html
    assert "href=" in nav_html, "expected the Show-more anchor to carry an href"
    assert "onclick" not in nav_html
    assert not re.search(r'\sdata-[a-z-]+=', nav_html), (
        "did not expect a data-prefixed attribute on the Show-more anchor")

    routes = _all_static_script_routes()
    assert len(routes) >= 17, (
        "FLOOR TRIPPED: expected at least 17 companion static JS routes, found %d: %r"
        % (len(routes), routes))
    hits_by_route = {}
    for route in routes:
        stripped = vp.strip_js_line_and_block_comments(served_asset(app, route))
        lines_with_hit = [ln for ln in stripped.splitlines() if "flights-more" in ln]
        if lines_with_hit:
            hits_by_route[route] = lines_with_hit
    unsanctioned = {
        route: lines for route, lines in hits_by_route.items() if route != "/static/freshness.js"}
    assert not unsanctioned, (
        "expected only freshness.js's own generic swap-registry mirror to mention "
        "'flights-more' — found it in %r too (scanned %d routes)"
        % (sorted(unsanctioned), len(routes)))
    if "/static/freshness.js" in hits_by_route:
        targeted = [
            ln for ln in hits_by_route["/static/freshness.js"]
            if re.search(r'querySelector\(|addEventListener|\.click\(|\.href', ln)]
        assert not targeted, (
            "expected freshness.js's 'flights-more' mention(s) to be plain swap-registry "
            "array entries, found a targeted reference: %r" % (targeted,))


def test_flights_reveal_anchor_has_a_matching_css_selector(tmp_path, served_css):
    """the Show-more anchor's rendered tag agrees with a REAL CSS selector match (rightmost
    compound's tag qualifier, if any) — not merely a class-string substring shared between
    the markup and style.css"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-%02dT10:00:00+00:00" % i, "hex": "cm%02d" % i, "callsign": "CSSM%02d" % i}
        for i in range(1, 21)
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    nav_match = re.search(r'<nav class="flights-more">(.*?)</nav>', rendered, re.S)
    assert nav_match is not None, "expected a non-empty <nav class=\"flights-more\"> in a 20-row render"
    tag_match = re.search(r'<(\w+)\b[^>]*\bclass="([^"]*)"', nav_match.group(1))
    assert tag_match is not None, "expected the Show-more nav's child to carry a class attribute"
    tag, classes = tag_match.group(1), tag_match.group(2).split()
    assert "calendar-disconnect-btn" in classes, (
        "expected the Show-more control to carry calendar-disconnect-btn, got classes %r"
        % (classes,))

    candidate_selectors = []
    for rule in css_rules(served_css):
        for sel in rule.selectors:
            if ".calendar-disconnect-btn" in sel:
                candidate_selectors.append(sel)
    assert candidate_selectors, (
        "expected at least one CSS rule selector mentioning .calendar-disconnect-btn")

    reachable = False
    for sel in candidate_selectors:
        compounds = sel.split()
        subject = compounds[-1]
        qualifier_match = re.match(r'^([a-zA-Z][a-zA-Z0-9-]*)?\.calendar-disconnect-btn$', subject)
        if qualifier_match is None:
            continue
        qualifier_tag = qualifier_match.group(1)
        if len(compounds) == 1 and (qualifier_tag is None or qualifier_tag.lower() == tag.lower()):
            reachable = True
            break
    assert reachable, (
        "expected a CSS selector whose rightmost compound has no tag qualifier or matches "
        "the rendered <%s>, with no ancestor compound to its left — found only %r, none of "
        "which actually paints <%s class=\"calendar-disconnect-btn\">"
        % (tag, candidate_selectors, tag))


_FLIGHTS_LIMIT_HOSTILE_INPUTS = (
    None, "", " ", "abc", "1.5", "-1", "0", "14", "15", "50", "51",
    "999999999", "1e9", "0x10", True, False, [], {}, object(),
)

# Stable, worker-independent ids: repr(object()) embeds the object's own
# memory address, which differs between xdist worker processes and makes
# pytest-xdist refuse to run ("Different tests were collected between
# gw0 and gwN") - an id derived from each input's own index is stable.
_FLIGHTS_LIMIT_HOSTILE_INPUT_IDS = [
    repr(value) if type(value) is not object else "opaque-object-%d" % i
    for i, value in enumerate(_FLIGHTS_LIMIT_HOSTILE_INPUTS)
]


@pytest.mark.parametrize(
    "raw", _FLIGHTS_LIMIT_HOSTILE_INPUTS, ids=_FLIGHTS_LIMIT_HOSTILE_INPUT_IDS)
def test_flights_limit_clamps_every_hostile_input_into_bounds(raw):
    """history_page.flights_limit() clamps all 19 hostile inputs into [15, 50] without
    raising"""
    result = history_page.flights_limit({"flights_limit": raw})
    assert isinstance(result, int) and not isinstance(result, bool), (
        "flights_limit(%r) returned %r, expected a plain int" % (raw, result))
    assert history_page.FLIGHTS_PAGE_SIZE <= result <= history_page.HISTORY_ROW_LIMIT, (
        "flights_limit(%r) returned %r, outside [%d, %d]"
        % (raw, result, history_page.FLIGHTS_PAGE_SIZE, history_page.HISTORY_ROW_LIMIT))


def test_flights_render_defers_entirely_to_flights_limit_for_hostile_ctx_values(tmp_path):
    """history_page.render() clamps a hostile ctx['flights_limit'] value into exactly the
    card count flights_limit() itself computes — the behavioural proof that render() has no
    second, unvalidated arithmetic path of its own on the raw threaded value, and
    HISTORY_ROW_LIMIT is the ceiling a huge hostile value clamps to

    A source/AST introspection proof that render() calls flights_limit() exactly once, never
    reads ctx['flights_limit'] directly, and performs no arithmetic of its own on the raw
    threaded value is dropped in favour of stronger behavioural evidence: if render() had any
    second path onto the raw value (its own arithmetic, a different default, a raise), the
    observed card count below would diverge from flights_limit()'s own clamp for at least
    one of these hostile inputs.
    """
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-01T%02d:00:00+00:00" % (i % 24), "hex": "cl%03d" % i,
         "callsign": "CLAMP%03d" % i}
        for i in range(60)
    ])
    for raw in ("abc", "-1", "0", "999999999", "1e9", None, "", " ", True, [], {}):
        expected = history_page.flights_limit({"flights_limit": raw})
        rendered = history_page.render(vp.history_ctx(tmp_path, flights_limit=raw))
        card_count = rendered.count('<li class="history-card"')
        assert card_count == min(expected, 60), (
            "flights_limit=%r: expected render() to defer to flights_limit()'s own clamp "
            "(%d cards, seeded 60), got %d" % (raw, min(expected, 60), card_count))
    assert history_page.flights_limit({"flights_limit": "999999999"}) == history_page.HISTORY_ROW_LIMIT, (
        "expected a huge hostile value to clamp AT HISTORY_ROW_LIMIT, not below it")


def test_the_count_animates_without_its_text_production_moving(app):
    """the filter count animates its ELEMENT and never its number: the template-driven text
    production is untouched, the text is written before the class is added, the class is
    removed and re-added across a forced reflow so a second change restarts it, and it
    fires only when the rendered value actually differs"""
    js = vp.strip_js_line_and_block_comments(served_asset(app, "/static/list-filter.js"))
    for token in ('getAttribute("data-filter-count-template")',
                  '.replace("%d", String(visibleCount))',
                  '.replace("%d", String(totalCount))'):
        assert token in js, (
            "expected the count's text production to be unchanged (%r)" % (token,))
    assert "is-fading-in" in js, (
        "expected the count to spend the stylesheet's existing changed-value animation")
    count_at = js.index("var countEl = document.querySelector(COUNT_SELECTOR);")
    block = js[count_at:count_at + 1400]
    text_at = block.index("countEl.textContent =")
    class_at = block.index("classList.add(")
    assert text_at < class_at, (
        "expected the count's text to be written BEFORE the animation class is added")
    assert "classList.remove(" in block, (
        "expected the animation class to be removed and re-added so a second change restarts it")
    assert "offsetWidth" in block, (
        "expected a forced reflow between the removal and the re-add")
    assert "!==" in block, (
        "expected the animation to fire only when the rendered text actually differs")


def test_phone_card_route_and_state_carry_the_existing_middle_dot(tmp_path):
    """the phone card's "ORY → JFK Departing" line carries the module's EXISTING
    cell-inline-sep middle dot between the route and the state, reused rather than
    reinvented"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "sep01", "callsign": "SEPCARD",
         "origin": "LFPO", "destination": "KJFK", "confirmed_state": "departing"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    match = re.search(r'<div class="history-card__secondary">(.*?)</div>', rendered, re.S)
    assert match is not None, "could not locate the phone card's secondary line"
    expected = (
        "<span>LFPO → KJFK</span>"
        '<span class="%s">%s</span>'
        "<span>Departing</span>"
    ) % (history_page.CELL_SEPARATOR_CLASS, layout.escape_html(history_page.CELL_SEPARATOR_TEXT))
    assert match.group(1) == expected, (
        "expected the route and state to be joined by the module's existing middle-dot "
        "separator, got %r" % (match.group(1),))


def test_raw_iso_survives_only_behind_the_copy_control(tmp_path):
    """the raw ISO timestamp appears only inside a data-copy-value attribute, while the visible
    full timestamp is the Europe/Paris local clock in the .time-value role on both the
    desktop detail row and the phone card"""
    raw_ts = "2026-08-27T10:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": raw_ts, "hex": "iso01", "callsign": "ISOROW"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert ('data-copy-value="%s"' % raw_ts) in rendered, (
        "expected the raw ISO to survive as the copy control's value")
    stripped = re.sub(r'data-copy-value="[^"]*"', "", rendered)
    assert raw_ts not in stripped, (
        "expected the raw ISO timestamp to appear ONLY inside a data-copy-value attribute")
    visible = history_page.full_local_time_text(raw_ts)
    assert visible != raw_ts, "expected a formatted local clock, not the raw ISO"
    assert ('<dd class="time-value">%s</dd>' % visible) in rendered, (
        "expected the visible full timestamp to read %r" % (visible,))
    assert ('<dd class="mono">%s' % raw_ts) not in rendered, (
        "did not expect the raw ISO in a monospace dd")


def test_phone_cards_carry_the_airline_name_and_artwork_thumbnail(tmp_path, served_css):
    """a phone card carries the airline name and, when real artwork exists for it, the Airlines
    gallery's own served frame as a thumbnail joining the shared white-backing/hairline/
    radius rule in a contain-fitted 56px box — and no <img> at all when no artwork file
    exists"""
    from PIL import Image

    key = illustrations.normalise_airline_key("Air France")
    override_path = illustrations.override_path_for_key(key, str(tmp_path))
    os.makedirs(os.path.dirname(override_path), exist_ok=True)
    Image.new("RGB", (4, 4), color=(200, 200, 200)).save(override_path, format="PNG")
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "th01", "callsign": "THUMBED",
         "airline": "Air France"},
        {"ts": "2026-08-27T09:00:00+00:00", "hex": "th02", "callsign": "NOART",
         "airline": "Totally Unknown Air"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    li_thumbed = _row_block(rendered, "li", 0)
    li_noart = _row_block(rendered, "li", 1)
    assert li_thumbed is not None and li_noart is not None, "could not locate both phone cards"
    assert 'class="history-card__airline-name">Air France<' in li_thumbed, (
        "expected the phone card to carry the airline name on its own face")
    expected_img = (
        '<img class="history-card__thumb" loading="lazy" decoding="async" src="%s%s.png"'
        % (history_page.ILLUSTRATION_ROUTE_PREFIX, key))
    assert expected_img in li_thumbed, (
        "expected the phone card to carry the artwork thumbnail, got %r" % (li_thumbed[:200],))
    assert "history-card__thumb" not in li_noart, (
        "did not expect a thumbnail for an airline with no artwork file")
    assert "history-card__airline-name" in li_noart, (
        "expected every card to name its airline, artwork or not")

    shared_rules = [r for r in css_rules(served_css) if "img.history-card__thumb" in r.selectors]
    assert any(
        ".now-showing__image" in r.selectors and ".preview-frame__image" in r.selectors
        for r in shared_rules), (
        "expected img.history-card__thumb to join the shared white-backing/hairline/radius "
        "rule .now-showing__image and .preview-frame__image already share")
    assert any(
        dict(r.declarations).get("height") == "56px"
        and dict(r.declarations).get("object-fit") == "contain"
        for r in shared_rules), (
        "expected img.history-card__thumb's own rule to declare a fixed 56px-tall box with "
        "contain fitting")


def test_no_prefix_registry_duplicated_on_history(tmp_path):
    """the rendered History page contains no prefix-registry table and no element carrying the
    registry table's own headers"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "reg01", "callsign": "REGCHK"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert health_page.UNRESOLVED_SECTION_HEADING not in rendered, (
        "did not expect Health's Unresolved-prefixes registry heading on History")
    assert "<th>Prefix</th>" not in rendered and "<th>First seen</th>" not in rendered, (
        "did not expect the registry table's own column headers on History")


def test_flights_french_render_translates_headings_not_data(tmp_path):
    """a French render of Flights shows the French page title, column headers and filter label,
    while a seeded callsign stays untranslated data"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1",
         "airline": "AFR", "origin": "LFPO", "destination": "LFPG",
         "confirmed_state": "departing", "corroborated": "True"},
    ])
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    for needle in (
            ">Vols<", ">Quand<", ">Trajet<", ">Sens<", "Indicatif",
            "Filtrer par indicatif ou code hex"):
        assert needle in rendered, "expected the French %r in a French Flights render" % (needle,)
    assert "FLT1" in rendered, "expected the seeded callsign 'FLT1' to stay untranslated data"


def test_flights_full_seeded_render_french_end_to_end(tmp_path):
    """a fully-seeded Flights render under lang='fr' shows every new French string (column
    headers, direction words, the unresolved-airline fallback, the no-callsign note, the
    disclosure summary and the filter's Clear button) with no English leaking in, the seeded
    callsign stays untranslated data, and the identical seeded render under the default
    language still carries every pre-existing English needle"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "aaa111", "callsign": "FLT1",
         "airline": None, "confirmed_state": "departing", "corroborated": "True"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "bbb222", "callsign": "",
         "airline": None, "confirmed_state": "arriving", "corroborated": "False"},
    ])
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    for needle in (
            ">Vols<", "Compagnie inconnue", "aucun indicatif",
            "Au départ", "À l’arrivée", ">Quand<", ">Vol<", ">Trajet<", ">Sens<",
            "Plus de détails", "Effacer"):
        assert needle in rendered_fr, "expected the French %r in the French Flights render" % (needle,)
    for english_only in (
            "Airline unknown", "no callsign", "Departing", "Arriving",
            ">When<", ">Flight<", ">Route<", ">State<"):
        assert english_only not in rendered_fr, (
            "expected no English %r leaking into the French render" % (english_only,))
    assert "FLT1" in rendered_fr, "expected the seeded callsign to stay untranslated data"

    rendered_en = history_page.render(vp.history_ctx(tmp_path))
    for needle in (
            '<h1 class="page-title">Flights</h1>', history_page.AIRLINE_FALLBACK_TEXT,
            history_page.NO_CALLSIGN_NOTE_TEXT, "Departing", "Arriving",
            ">When<", ">Flight<", ">Route<", ">State<"):
        assert needle in rendered_en, (
            "expected the English %r in the default-language Flights render" % (needle,))


def test_flights_catalog_keys_all_present_in_merged_catalog():
    """every key in companion/i18n_fr/flights.py's own CATALOG is also a key of the merged
    companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up
   """
    import companion.i18n_fr as i18n_fr
    import companion.i18n_fr.flights as i18n_fr_flights

    missing = [k for k in i18n_fr_flights.CATALOG if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from the merged CATALOG: %r" % (missing,)


def test_home_page_render_with_seeded_state(tmp_path):
    """home_page.render() with seeded flights, a battery reading and a gallery entry renders
    the hero picture, the battery percentage estimate, escaped recent flights, and the
    Next-update headline, with .preview-frame before .recent-flight in document order"""
    now = "2026-08-27T12:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
         "airline": "Air France", "origin": "ORY", "destination": "TLS",
         "confirmed_state": "departing"},
        {"ts": "2026-08-27T11:40:00+00:00", "hex": "4b1a72", "callsign": "<XYZ>"},
    ])
    with history_db.open_db(tmp_path) as conn:
        history_db.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
    ctx = {
        "state_dir": str(tmp_path), "now": now,
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "warn",
                         "battery_state": "ok",
                         "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                         "pipeline_html": "<p>A little stale</p>"},
        "simple_mode": False,
    }
    rendered = home_page.render(ctx)
    for needle in (
            '<h1 class="page-title">Home</h1>', "AFR1380", "Air France", "ORY → TLS",
            'src="/gallery/2026-08-27T11-50-00+00-00.png"', "3750 mV",
            "≈ 38%", "Next update ≈"):
        assert needle in rendered, "expected %r in the Home page" % (needle,)
    assert "<XYZ>" not in rendered and "&lt;XYZ&gt;" in rendered, (
        "expected the hostile callsign to be escaped")
    assert rendered.count('class="recent-flight"') == 2, "expected exactly two recent-flight rows"
    assert rendered.index('<figure class="preview-frame">') < rendered.index('class="recent-flight"'), (
        "expected .preview-frame before .recent-flight in document order")


def test_home_battery_ring_is_the_same_drawing_at_a_smaller_size(tmp_path):
    """Home's Battery tile draws exactly one ring, inside that tile, whose drawn fraction
    equals the '≈ NN%' it still prints beside its own millivolt detail and verdict; the
    ring is SMALLER than Health's yet identical to it in radius-over-box and
    stroke-over-box, proving one emitter at two sizes rather than two components; the
    frame verdict still appears exactly once; and a device with no reading draws no ring
    at all"""
    now = "2026-08-27T12:00:00+00:00"
    home_dir = tmp_path / "home"
    blank_dir = tmp_path / "blank"
    with history_db.open_db(home_dir) as conn:
        history_db.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3690)
    health_state = {"device_state": "ok", "pipeline_state": "ok",
                    "battery_state": "ok",
                    "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                    "pipeline_html": "<p>Fresh</p>"}
    ctx = {"state_dir": str(home_dir), "now": now, "gallery_entries": [],
           "last_checkin_ts": "2026-08-27T11:55:00+00:00",
           "device_config": {"wake_interval_s": 900, "display_enabled": True},
           "health_state": health_state, "simple_mode": False}
    rendered = home_page.render(ctx)

    def _rings(markup):
        return (re.findall(r'<circle class="%s"[^>]*/>' % re.escape(draw.DRAWING_RING_TRACK_CLASS), markup),
                re.findall(r'<circle class="%s"[^>]*/>' % re.escape(draw.DRAWING_RING_VALUE_CLASS), markup))

    tracks, values = _rings(rendered)
    assert len(tracks) == 1 and len(values) == 1, (
        "expected exactly one ring on Home, got %d track(s) and %d value arc(s)"
        % (len(tracks), len(values)))

    battery_at = rendered.index(home_page.BATTERY_ROW_LABEL)
    data_at = rendered.index(home_page.DATA_ROW_LABEL)
    ring_at = rendered.index(draw.DRAWING_RING_TRACK_CLASS)
    assert battery_at < ring_at < data_at, (
        "the ring is not inside the Battery tile — battery caption at %d, ring at %d, next "
        "tile's caption at %d" % (battery_at, ring_at, data_at))

    tile = rendered[battery_at:data_at]
    for needle in ("≈ 32%", "3690 mV"):
        assert needle in tile, "expected the Battery tile to still print %r" % (needle,)
    assert 'class="text-body widget-verdict"' in tile, "expected the Battery tile to still print its verdict"

    radius = float(re.search(r' r="([0-9.]+)"', values[0]).group(1))
    dash = re.search(r'stroke-dasharray="([0-9.]+) ', values[0])
    drawn = float(dash.group(1)) if dash else 2 * math.pi * radius
    drawn_fraction = drawn / (2 * math.pi * radius)
    assert abs(drawn_fraction - 0.32) <= 0.0005, (
        "Home's ring draws %.4f of its circumference while the tile prints '≈ 32%%' beside "
        "it (CFG-40, SEED-006 curve)" % (drawn_fraction,))

    health_dir = tmp_path / "home-ring-health"
    with history_db.open_db(health_dir) as conn:
        for minute, mv in ((50, 3600), (55, 3690)):
            history_db.record_device_health(conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
    health_rendered = health_page.render({"state_dir": str(health_dir), "now": now})

    def _geometry(markup, where):
        svg = re.search(
            r'<svg class="%s[^"]*" viewBox="0 0 ([0-9.]+) [0-9.]+"' % re.escape(draw.DRAWING_FIGURE_CLASS),
            markup)
        assert svg is not None, "found no ring figure on %s" % where
        side = float(svg.group(1))
        arc = _rings(markup)[1][0]
        return (side, float(re.search(r' r="([0-9.]+)"', arc).group(1)),
                float(re.search(r'stroke-width="([0-9.]+)"', arc).group(1)))

    home_geom = _geometry(rendered, "Home")
    health_geom = _geometry(health_rendered, "Health")
    assert home_geom[0] < health_geom[0], (
        "Home's ring is not SMALLER than Health's — %r against %r"
        % (home_geom[0], health_geom[0]))
    for index, label in ((1, "radius"), (2, "stroke width")):
        home_ratio = home_geom[index] / home_geom[0]
        health_ratio = health_geom[index] / health_geom[0]
        assert abs(home_ratio - health_ratio) <= 0.001, (
            "the two rings disagree about %s as a proportion of their own box: Home %.4f, "
            "Health %.4f" % (label, home_ratio, health_ratio))

    verdicts = [text for text in home_page.FRAME_STATE_TEXT.values() if rendered.count(text)]
    for text in verdicts:
        assert rendered.count(text) == 1, (
            "expected the frame verdict %r exactly once on Home, got %d" % (text, rendered.count(text)))

    blank_ctx = dict(ctx, state_dir=str(blank_dir))
    blank_rendered = home_page.render(blank_ctx)
    for class_name in (draw.DRAWING_RING_TRACK_CLASS, draw.DRAWING_RING_VALUE_CLASS):
        assert class_name not in blank_rendered, (
            "a device with no battery reading rendered %r on Home" % (class_name,))


def test_home_recent_flight_age_is_an_element_reading_exactly_as_before(tmp_path):
    """Home's recent-flight relative age is a <time data-relative> element carrying the ROW's
    own instant, reading exactly what it reads today in both languages, with C5's
    .time-value/.cell-inline-sep/.time-value__age split and its parentheses intact
    (23-03, D14)"""
    now = "2026-08-27T12:00:00+00:00"
    flight_ts = "2026-08-27T11:50:00+00:00"
    for lang in ("en", "fr"):
        sub = tmp_path / lang
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = home_page.render(_home_seeded_ctx(sub, now, flight_ts))
            expected_age = layout.relative_age_text(600, lang=lang)
            cell = re.search(
                r'<span class="time-value">([^<]*)</span>'
                r'<span class="cell-inline-sep">·</span>'
                r'<span class="time-value__age">\((.*?)\)</span>', rendered)
            assert cell is not None, (
                "lang=%s: expected the recent-flight time cell to keep C5's clock/age split"
                % (lang,))
            element = _HOME_RELATIVE_ELEMENT_RE.fullmatch(cell.group(2))
            assert element is not None, (
                "lang=%s: expected the age half to be a <time data-relative> element, got %r"
                % (lang, cell.group(2)))
            assert element.group(2) == expected_age, (
                "lang=%s: expected Home's recent-flight age to read exactly what it reads "
                "today (%r), got %r" % (lang, expected_age, element.group(2)))
            assert element.group(1), "lang=%s: expected a non-empty datetime attribute" % (lang,)
            assert layout.age_seconds(element.group(1), now) == 600, (
                "lang=%s: expected the element's own instant to carry the ROW's moment"
                % (lang,))
            assert "&lt;time" not in rendered, (
                "lang=%s: found a double-escaped '&lt;time'" % (lang,))
        finally:
            prefs.set_request_prefs(lang="en")


def test_home_rendered_caption_carries_the_element_through_the_template(tmp_path):
    """Home's rendered-picture caption carries concise_timestamp_html()'s <time data-relative>
    element THROUGH its i18n template's own %s — as markup, never double-escaped — with the
    caption's wording and the age's text unchanged in both languages (23-03, D14)"""
    now = "2026-08-27T12:00:00+00:00"
    flight_ts = "2026-08-27T11:50:00+00:00"
    gallery_iso = "2026-08-27T11:50:00+00:00"
    for lang in ("en", "fr"):
        sub = tmp_path / lang
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = home_page.render(_home_seeded_ctx(sub, now, flight_ts))
            caption = re.search(
                r'<figcaption class="preview-frame__caption text-label">(.*?)</figcaption>',
                rendered, re.S)
            assert caption is not None, "lang=%s: expected the rendered-picture caption" % (lang,)
            expected_caption = i18n.t_lang(
                home_page.RENDERED_CAPTION_TEMPLATE, lang) % layout.concise_timestamp_html(
                    gallery_iso, now, lang=lang)
            assert caption.group(1).startswith(expected_caption), (
                "lang=%s: expected the caption to be its unchanged wording around "
                "concise_timestamp_html()'s own output %r, got %r"
                % (lang, expected_caption, caption.group(1)))
            element = _HOME_RELATIVE_ELEMENT_RE.search(caption.group(1))
            assert element is not None, (
                "lang=%s: expected the caption's relative half to be a <time data-relative> "
                "element, got %r" % (lang, caption.group(1)))
            assert element.group(2) == layout.relative_age_text(600, lang=lang), (
                "lang=%s: expected the caption's age to read exactly what it reads today"
                % (lang,))
            assert "&lt;time" not in caption.group(1), (
                "lang=%s: the caption template double-escaped the element" % (lang,))
        finally:
            prefs.set_request_prefs(lang="en")


def test_recent_flight_thumb_resolved_vs_placeholder(tmp_path):
    """a recent-flight row whose airline resolves to a real illustration file renders exactly
    one lazily-loaded /illustration/ thumbnail <img>; a null/unrecognised airline AND an
    airline whose normalised key resolves to no file on disk anywhere (override or
    vendored) both render the dashed placeholder span with no <img> at all (fix)"""
    no_state_dir = str(tmp_path / "absent" / "nested")
    resolved_row = {"callsign": "AFR1380", "airline": "Air France"}
    thumb_resolved = home_page._recent_flight_thumb_html(resolved_row, no_state_dir)
    assert thumb_resolved.count("<img") == 1, "expected exactly one <img> for a resolved airline"
    assert 'loading="lazy"' in thumb_resolved, "expected the thumbnail <img> to be lazily loaded"
    assert "/illustration/air-france.png" in thumb_resolved, (
        "expected the resolved illustration route in the <img> src")
    unresolved_row = {"callsign": "XYZ", "airline": None}
    thumb_placeholder = home_page._recent_flight_thumb_html(unresolved_row, no_state_dir)
    assert "<img" not in thumb_placeholder, "expected no <img> at all for a null/unrecognised airline"
    assert "recent-flight__thumb--placeholder" in thumb_placeholder, (
        "expected the dashed placeholder span for a null/unrecognised airline")
    no_artwork_row = {"callsign": "EZS123", "airline": "easyJet Europe"}
    thumb_no_artwork = home_page._recent_flight_thumb_html(no_artwork_row, no_state_dir)
    assert "<img" not in thumb_no_artwork, (
        "expected no <img> for an airline whose normalised key resolves to no file on disk")
    assert "recent-flight__thumb--placeholder" in thumb_no_artwork, (
        "expected the dashed placeholder span for an airline with no artwork file")


def test_hero_figure_precedes_status_card_with_flight_one_liner_when_known(tmp_path):
    """the hero's flight one-liner (callsign in .mono, then airline, then the route) appears
    when the current flight is known and is absent otherwise, and the page reads header ->
    .frame-strip -> .home-status-grid -> .home-picture-row (.preview-frame before
    .recent-flight inside it)"""
    no_state_dir = str(tmp_path / "absent" / "nested")
    hero_ctx = {
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "now": "2026-08-27T12:00:00+00:00",
    }
    current_flight_row = {
        "callsign": "AFR1380", "airline": "Air France", "origin": "ORY",
        "destination": "TLS", "confirmed_state": "departing",
    }
    hero_with_flight = home_page._current_picture_html(hero_ctx, current_flight_row)
    assert "preview-frame__flight" in hero_with_flight, (
        "expected the flight one-liner when the current flight is known")
    assert '<span class="mono">AFR1380</span> · Air France · ORY → TLS' in hero_with_flight
    hero_without_flight = home_page._current_picture_html(hero_ctx, None)
    assert "preview-frame__flight" not in hero_without_flight, (
        "expected no flight one-liner when there is no current flight")

    full_ctx = {
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "now": "2026-08-27T12:00:00+00:00", "health_state": {}, "device_config": {},
        "state_dir": no_state_dir,
    }
    rendered = home_page.render(full_ctx)
    header_pos = rendered.index('<h1 class="page-title">')
    strip_pos = rendered.index('class="frame-strip stat-tile stat-tile--accent"')
    tiles_pos = rendered.index('class="dashboard-grid home-status-grid"')
    picture_row_pos = rendered.index('class="home-columns home-picture-row"')
    assert header_pos < strip_pos < tiles_pos < picture_row_pos, (
        "expected header -> .frame-strip -> .home-status-grid -> .home-picture-row, got "
        "positions %d, %d, %d, %d" % (header_pos, strip_pos, tiles_pos, picture_row_pos))
    assert rendered.index('<figure class="preview-frame">') < rendered.index('id="home-flights"'), (
        "expected .preview-frame before the recent-flights section inside .home-picture-row")


def test_home_page_french_render_translates_headings_and_alt_text_not_data(tmp_path):
    """under a French request Home's headings ('Vols récents'/'Voir tous les vols') and a
    thumbnail's alt text translate while the callsign/airline name stay untranslated data
    """
    no_state_dir = str(tmp_path / "absent" / "nested")
    ctx = {
        "gallery_entries": [],
        "now": "2026-08-27T12:00:00+00:00", "health_state": {}, "device_config": {},
        "state_dir": no_state_dir,
    }
    row = {"callsign": "AFR1380", "airline": "Air France"}
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = home_page.render(ctx)
        thumb = home_page._recent_flight_thumb_html(row, ctx["state_dir"])
    finally:
        prefs.set_request_prefs(lang="en")
    for needle in ("Vols récents", "Voir tous les vols"):
        assert needle in rendered, "expected the French heading/link %r" % (needle,)
    assert "Illustration Air France" in thumb, (
        "expected the French alt-text template applied to the untranslated airline name")
    assert "Air France" in thumb, "expected the airline name itself to stay untranslated data"
