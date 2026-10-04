"""Companion view-page tests: most of the JS-source contracts
(panel-lookup.js, list-filter.js, freshness.js), the
Airlines resolve-dialog action row and unresolved-airline link, Flights'
refresh-region/row-identity/detail-reveal/Show-more contracts, and Home's
battery ring, relative-age elements and French render.

CSS/JS checks fetch served bytes from a running `companion/app.py`;
everything else calls `*_page.render()` directly, in-process.
"""
import os
import re

import pytest

import companion.app as app_module
import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
from companion.pages import airlines_page, health_page, history_page, home_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for, rules_with_selector
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


def test_airlines_filter_bar_has_no_manual_resolution_control(tmp_path, served_css):
    """the Airlines filter bar is the plain search pill: no "N manual resolutions" summary
    control in either language, no style rule for it, while the per-card "Resolved by hand"
    chip still renders (the retired count was owner feedback)"""
    registry = {"QQQ": {"airline_name": "Air France",
                        "created_at": "2026-09-01T10:00:00+00:00"}}
    ctx = {"state_dir": str(tmp_path), "manual_resolutions": registry}
    rendered = airlines_page.render(ctx)
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = airlines_page.render(ctx)
    finally:
        prefs.set_request_prefs(lang="en")
    for page in (rendered, rendered_fr):
        bar = re.search(r'<div class="filter-bar">(.*?)<div class="empty-state ', page, re.S)
        assert bar is not None, "expected to locate the rendered filter bar"
        assert "manual" not in bar.group(1).lower() and "manuelle" not in bar.group(1).lower()
        assert "data-filter-set" not in page
    assert not rules_with_selector(served_css, ".manual-summary")
    assert not rules_with_selector(served_css, ".manual-summary:hover")
    assert '<span class="airline-card__chip">Resolved by hand</span>' in rendered
    assert '<span class="airline-card__chip">Résolue à la main</span>' in rendered_fr


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

    ident = vp.row_block(rendered, "li", 0).select_one(".history-card__callsign")
    assert ident.text() == "34560d %s" % history_page.NO_CALLSIGN_NOTE_TEXT, (
        "expected the mobile card's identity slot to carry the hex and the no-callsign note")
    assert ident.select_one(".history-card__note").text() == history_page.NO_CALLSIGN_NOTE_TEXT
    assert "data-copy-value" not in li_block

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
            r'<tr class="flight-day-row" data-filter-day><th scope="colgroup" colspan="5"'
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
    assert history_page.day_label(day, day) == i18n.t_lang(history_page._DAY_TODAY_LABEL, "en"), (
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
    assert len(tr_ids) == 2, (
        "expected every desktop table row to carry %r (2 for 2 events), found %r"
        % (attr, tr_ids))
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


def test_the_phone_card_is_a_boarding_pass_with_resolve_and_picture_actions(tmp_path):
    """the phone card reads head (identity + picture action), route line, then stub (artwork +
    time), carries the one-hop resolve link only for an unnamed airline, and has no
    disclosure, summary or copy control"""
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
    names = ["2026-08-27T08-00-00+00-00.png"]
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    li = vp.row_block(rendered, "li", 0)
    assert li is not None, "could not locate the phone card"
    assert not li.select("details") and not li.select("summary")
    assert not li.select("[data-copy-value]")
    bands = [child.attrs.get("class") for child in li.children if not isinstance(child, str)]
    assert bands == ["history-card__head", "history-card__route", "history-card__stub"]
    head = li.select_one(".history-card__head")
    assert head.select_one(".history-card__callsign").text() == "FACEONE"
    assert head.select_one(".history-card__airline").text() == "Air France"
    assert head.select_one("a.history-card__picture[data-view-panel-src]") is not None
    assert li.select_one(".history-card__stub img.history-card__art") is not None
    assert li.select_one(".history-card__stub .history-card__when") is not None
    assert history_page.RESOLVE_LINK_TEXT not in li.text(), (
        "did not expect a resolve link for a named airline")

    unresolved = vp.row_block(rendered, "li", 1)
    assert unresolved is not None, "could not locate the unresolved-airline card"
    identity = unresolved.select_one(".history-card__head .history-card__id")
    assert identity.select_one(".history-card__airline--unknown").text() == "Airline unknown"
    assert identity.select_one(".history-card__resolve a").text() == history_page.RESOLVE_LINK_TEXT
    assert unresolved.select("a[data-view-panel-src]")


def test_phone_card_identity_branches_and_time_never_wrap(tmp_path, served_css):
    """every identity branch (callsign, hex plus note, neither) renders one callsign slot and one
    airline line in the card head, the stub's time column never wraps, and the airline line
    ellipsises rather than growing the card"""
    when_block = declarations_for(served_css, ".history-card__when")
    assert when_block.get("white-space") == "nowrap"
    airline_block = declarations_for(served_css, ".history-card__airline")
    assert airline_block.get("white-space") == "nowrap"
    assert airline_block.get("text-overflow") == "ellipsis"

    branches = (
        ("callsign", {"ts": "2026-09-21T10:00:00+00:00", "callsign": "GRD01"}, "GRD01"),
        ("hex-plus-note", {"ts": "2026-09-21T10:00:00+00:00", "hex": "abc123"},
         "abc123 " + history_page.NO_CALLSIGN_NOTE_TEXT),
        ("empty", {"ts": "2026-09-21T10:00:00+00:00"}, ""),
    )
    for name, fields, expected in branches:
        sub = tmp_path / name
        vp.seed_runway_events(sub, [fields])
        rendered = history_page.render(vp.history_ctx(sub))
        li = vp.row_block(rendered, "li", 0)
        assert li is not None, "%s branch: could not locate the rendered card" % name
        identity = li.select_one(".history-card__head .history-card__id")
        assert len(identity.select(".history-card__callsign")) == 1, name
        assert identity.select_one(".history-card__callsign").text() == expected, name
        assert len(identity.select(".history-card__airline")) == 1, name


def test_freshness_refetches_the_current_url_verbatim(app):
    """freshness.js carries exactly one fetch( call and it targets window.location.href
    verbatim, so a background refresh of Flights re-requests whatever URL the visitor is on"""
    js_source = vp.strip_js_line_and_block_comments(served_asset(app, "/static/freshness.js"))
    fetch_calls = re.findall(r"fetch\(\s*([^,)]+)", js_source)
    assert len(fetch_calls) == 1, (
        "expected exactly one fetch( call in freshness.js, found %d: %r"
        % (len(fetch_calls), fetch_calls))
    assert fetch_calls[0].strip() == "window.location.href", (
        "expected freshness.js's one fetch( call to target window.location.href, got %r"
        % (fetch_calls[0].strip(),))


def test_the_count_animates_without_its_text_production_moving(app):
    """the filter count animates its ELEMENT and never its number: the template-driven text
    production is untouched, the text is written before the class is added, the class is
    removed and re-added across a forced reflow so a second change restarts it, and it
    fires only when the rendered value actually differs"""
    js = vp.strip_js_line_and_block_comments(served_asset(app, "/static/list-filter.js"))
    for token in ('getAttribute("data-filter-count-template")',
                  '.replace("#", String(visibleCount))',
                  '.replace("#", String(totalCount))'):
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


def test_phone_card_route_line_mutes_the_home_end_and_names_the_direction(tmp_path):
    """the phone card's route line carries origin and destination as two codes with the plane
    glyph and the direction label between them; the home end (the origin of a departure, the
    destination of an arrival) is muted; a row with no route reads the shared fallback"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "rt01", "callsign": "DEPCARD",
         "origin": "ORY", "destination": "KEF", "confirmed_state": "departing"},
        {"ts": "2026-08-27T09:00:00+00:00", "hex": "rt02", "callsign": "ARRCARD",
         "origin": "NCE", "destination": "ORY", "confirmed_state": "arriving"},
        {"ts": "2026-08-27T08:00:00+00:00", "hex": "rt03", "callsign": "NOROUTE",
         "confirmed_state": "departing"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    for index, origin, destination, home, direction in (
            (0, "ORY", "KEF", "from", "Departing"), (1, "NCE", "ORY", "to", "Arriving")):
        route = vp.row_block(rendered, "li", index).select_one(".history-card__route")
        assert route.select_one(".history-card__code--from").text() == origin
        assert route.select_one(".history-card__code--to").text() == destination
        homes = route.select(".history-card__code--home")
        assert len(homes) == 1 and "history-card__code--%s" % home in homes[0].attrs["class"]
        assert route.select_one(".history-card__track svg use").attrs["href"] == "#icon-plane"
        assert route.select_one(".history-card__dir").text() == direction
    route = vp.row_block(rendered, "li", 2).select_one(".history-card__route")
    assert route.select_one(".history-card__code--none").text() == history_page.ROUTE_FALLBACK_TEXT
    assert not route.select(".history-card__code--to")


def test_raw_iso_timestamp_is_never_rendered(tmp_path):
    """neither the raw ISO timestamp nor a full-timestamp label appears anywhere in the Flights
    page: the owner-facing time is the concise local clock plus relative age"""
    raw_ts = "2026-08-27T10:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": raw_ts, "hex": "iso01", "callsign": "ISOROW"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert "ISOROW" in rendered
    assert raw_ts not in rendered.replace('datetime="%s"' % raw_ts, "")
    assert "Full timestamp" not in rendered


def test_phone_cards_carry_the_airline_name_and_artwork_plate(tmp_path, served_css):
    """a phone card carries the airline name and, when real artwork exists for it, the Airlines
    gallery's own served frame as a contain-fitted plate on the shared white image backdrop —
    and, when no artwork file exists, a dashed "No illustration" placeholder, never an <img>"""
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
    li_thumbed = vp.row_block(rendered, "li", 0)
    li_noart = vp.row_block(rendered, "li", 1)
    assert li_thumbed is not None and li_noart is not None, "could not locate both phone cards"
    assert li_thumbed.select_one(".history-card__airline").text() == "Air France"
    img = li_thumbed.select_one(".history-card__stub img.history-card__art")
    assert img.attrs["src"] == "%s%s.png" % (history_page.ILLUSTRATION_ROUTE_PREFIX, key)
    assert img.attrs["alt"] == "Air France illustration"
    assert img.attrs["loading"] == "lazy"
    assert not li_noart.select("img"), (
        "did not expect an <img> for an airline with no artwork file")
    placeholder = li_noart.select_one(".history-card__stub .history-card__art--empty")
    assert placeholder.text() == "No illustration"
    assert li_noart.select_one(".history-card__airline").text() == "Totally Unknown Air"

    plate = declarations_for(served_css, "img.history-card__art")
    shared = declarations_for(served_css, ".now-showing__image")
    assert plate.get("background") == shared.get("background")
    assert plate.get("object-fit") == "contain"
    assert declarations_for(served_css, ".history-card__art--empty").get("border-style") == "dashed"


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
            ">Vols<", ">Quand<", ">Trajet<", ">Sens<", "Image",
            "Filtrer les vols"):
        assert needle in rendered, "expected the French %r in a French Flights render" % (needle,)
    assert "FLT1" in rendered, "expected the seeded callsign 'FLT1' to stay untranslated data"


def test_flights_full_seeded_render_french_end_to_end(tmp_path):
    """a fully-seeded Flights render under lang='fr' shows every new French string (column
    headers, direction words, the unresolved-airline fallback, the no-callsign note and the
    filter's Clear button) with no English leaking in, the seeded
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
            "Effacer",):
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
    """every key in companion/i18n_fr/flights.py's own CATALOG/MESSAGES is also a key of the
    merged companion.i18n_fr.CATALOG/BY_ID, proving the auto-merge package picked the module up.
    flights.py has fully migrated onto stable ids: it exports MESSAGES, not CATALOG, so the
    CATALOG half reduces to an always-empty check for that module — kept rather than deleted so a
    regression back to a CATALOG export is still caught.
   """
    import companion.i18n_fr as i18n_fr
    import companion.i18n_fr.flights as i18n_fr_flights

    missing = [
        k for k in getattr(i18n_fr_flights, "CATALOG", {})
        if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from the merged CATALOG: %r" % (missing,)

    missing_ids = [
        k for k in getattr(i18n_fr_flights, "MESSAGES", {})
        if k not in i18n_fr.BY_ID]
    assert not missing_ids, "ids missing from the merged BY_ID: %r" % (missing_ids,)


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


def test_home_latest_image_has_no_caption_and_its_alt_names_the_flight(tmp_path):
    """Home prints nothing under the latest image: no <figcaption>, no "Rendered"/"Généré"
    line and no flight line; the image's alt text still identifies the current flight, in both
    languages"""
    now = "2026-08-27T12:00:00+00:00"
    flight_ts = "2026-08-27T11:50:00+00:00"
    for lang in ("en", "fr"):
        sub = tmp_path / lang
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = home_page.render(_home_seeded_ctx(sub, now, flight_ts))
            figure = re.search(r'<figure class="preview-frame">(.*?)</figure>', rendered, re.S)
            assert figure is not None, "lang=%s: expected the picture figure" % (lang,)
            assert "<figcaption" not in figure.group(1), "lang=%s: found a caption" % (lang,)
            assert "preview-frame__caption" not in rendered and "preview-frame__flight" not in rendered
            for banned in ("Rendered", "Généré"):
                assert banned not in rendered, "lang=%s: found %r" % (lang, banned)
            alt = re.search(r'<img class="preview-frame__image"[^>]* alt="([^"]*)"', rendered)
            assert alt is not None, "lang=%s: expected the picture's alt text" % (lang,)
            lead = ("The picture currently on the frame: " if lang == "en"
                    else "L’image actuellement affichée sur le cadre\u00a0: ")
            assert alt.group(1).startswith(lead) and len(alt.group(1)) > len(lead), (
                "lang=%s: expected the alt text to carry the flight line, got %r"
                % (lang, alt.group(1)))
        finally:
            prefs.set_request_prefs(lang="en")


def test_flights_when_cell_age_is_a_live_time_element(tmp_path):
    """Flights desktop table's When column renders its relative age as a live
    <time data-relative> element (layout.relative_time_html()'s own markup) carrying the
    row's own instant, reading exactly what relative_age_text() reads today, with the
    cell-primary/cell-inline-sep/cell-secondary shape _merged_cell() also emits, and no
    double-escaping"""
    now = "2026-09-27T12:00:00+00:00"
    ts = "2026-09-27T11:50:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": ts, "hex": "3c6444", "callsign": "AFR1380",
         "airline": "Air France", "origin": "ORY", "destination": "TLS"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, now=now))
    tr_block = vp.row_block(rendered, "tr", 0)
    assert tr_block is not None, "expected to locate the seeded row"
    when_cell = tr_block.select("td")[0]
    element = when_cell.select_one("time[data-relative]")
    expected_age = layout.relative_age_text(600)
    assert element.text() == expected_age, (
        "expected the When cell's age text to read exactly relative_age_text()'s own output, "
        "got %r" % (element.text(),))
    assert element.attrs.get("datetime"), "expected a non-empty datetime attribute"
    assert layout.age_seconds(element.attrs["datetime"], now) == 600, (
        "expected the element's own instant to carry the row's own moment")
    assert when_cell.find("span", cls=history_page.CELL_PRIMARY_CLASS) is not None
    assert when_cell.find("span", cls=history_page.CELL_SECONDARY_CLASS) is not None
    assert "&lt;time" not in rendered, "found a double-escaped '&lt;time' on Flights"


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
