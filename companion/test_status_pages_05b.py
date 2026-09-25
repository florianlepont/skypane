"""Companion status-page tests: `layout.relative_time_html()`'s <time
data-relative> wrapping, the French health catalogue, the Airlines
gallery's header/card count/chips/search-filter bar and its non-goal
guards, the click-to-enlarge lightbox, and the illustration-replace form.

Filter-bar and CSS checks assert on rendered pages and the served
stylesheet, never on production source text; everything else calls
`companion.layout`/`companion.pages.airlines_page` directly, in-process.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

import companion.app as app
import companion.test_status_pages_helpers as shp
from companion import i18n, illustration_normalize, layout, prefs
from companion.i18n_fr import health as i18n_fr_health
from companion.pages import airlines_page, health_page, history_page
from companion_app_server import served_stylesheet
from companion_markup import css_rules, declarations_for, parse_html, rules_with_selector
from server import history_db
from server.plane import illustrations

_RELATIVE_ELEMENT_RE = re.compile(r'<time datetime="([^"]*)" data-relative>([^<]*)</time>')


# --- module-scoped read-only server, for the served-CSS checks only --------

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


# --- shared helpers, local to this part -------------------------------------

def _battery_section_heading(lang="en"):
    """The battery-trend heading's own rendered text, computed the SAME way
    _battery_trend_section_html() computes it."""
    return i18n.t_lang(health_page.BATTERY_SECTION_HEADING_TEMPLATE, lang) % (
        health_page.BATTERY_TREND_WINDOW_DAYS // 30)


def _card_slice(rendered, airline_name):
    """The one `.airline-card` block for `airline_name`, bounded by the next
    card's opening tag (or end of string)."""
    name_index = rendered.index(">%s<" % airline_name)
    card_start = rendered.rindex('<div class="airline-card"', 0, name_index)
    next_start = rendered.find('<div class="airline-card"', card_start + 1)
    return rendered[card_start:] if next_start == -1 else rendered[card_start:next_start]


def _rendered_pages_with_search_inputs(tmp_path):
    """Render every page this app renders an <input type="search"> on today —
    Compagnies' gallery filter, Health's registry filter (seeded so it
    appears) and Flights' history filter — and return their rendered HTML.
    Rewritten from an ast-based module-wide source scan to
    the rendered behaviour on the pages actually served."""
    tmp = str(tmp_path)
    airlines_rendered = airlines_page.render(shp.ctx(tmp))
    now = shp.now()
    shp.seed_unresolved_prefixes(tmp, {
        "ABC": {"count": 3, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    health_rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))
    shp.seed_runway_events(tmp, [{"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    history_rendered = history_page.render(shp.ctx(tmp))
    return [airlines_rendered, health_rendered, history_rendered]


# ==========================================================================
# layout.py's <time data-relative> element convention for a relative time
# ==========================================================================


def test_relative_time_html_wraps_the_one_ladder_in_both_languages():
    """layout.relative_time_html() renders a <time datetime=... data-relative> element whose
    own text EQUALS layout.relative_age_text()'s output for all four buckets in BOTH
    languages, and whose instant names the same moment that text describes (23-03, D14)"""
    ages = (30, 180, 7200, 90000)
    base = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    now_iso = shp.iso(base)
    try:
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            for age in ages:
                ts = shp.iso(base - timedelta(seconds=age))
                rendered = layout.relative_time_html(ts, now_iso)
                match = _RELATIVE_ELEMENT_RE.search(rendered)
                assert match is not None, (
                    "lang=%s age=%ds: expected a <time datetime=... data-relative> element, "
                    "got %r" % (lang, age, rendered))
                instant, inner = match.group(1), match.group(2)
                expected = layout.relative_age_text(age, lang=lang)
                assert inner == expected, (
                    "lang=%s age=%ds: expected the element's own text to EQUAL "
                    "relative_age_text()'s output %r, got %r"
                    % (lang, age, expected, inner))
                assert instant, "lang=%s age=%ds: expected a non-empty machine-readable instant" % (
                    lang, age)
                assert layout.parse_iso(instant) is not None
                assert layout.age_seconds(instant, now_iso) == age, (
                    "lang=%s age=%ds: expected the element's instant to name the SAME moment "
                    "its text describes, got %r" % (lang, age, instant))
    finally:
        prefs.set_request_prefs(lang="en")


def test_relative_time_html_degrades_without_an_invented_instant():
    """layout.relative_time_html() degrades to escaped plain text — never a raise, never a
    <time> element carrying an empty or invented instant — for a falsy, None, unparseable or
    mismatched timestamp (23-03)"""
    now_iso = "2026-09-13T12:00:00+00:00"
    for ts, label in (("", "a falsy timestamp"), (None, "a None timestamp"),
                      ("not-a-date", "an unparseable timestamp")):
        rendered = layout.relative_time_html(ts, now_iso)
        assert "<time" not in rendered, (
            "%s must NOT produce a <time> element — an element with an empty or invented "
            "instant is worse than no element, got %r" % (label, rendered))
    # A mismatched now_ts (naive vs aware) is the one degrade path
    # age_seconds() alone catches; it must not raise either.
    assert "<time" not in layout.relative_time_html("2026-09-13T11:00:00+00:00", "not-a-date")
    # And the degrade path still escapes: an unparseable timestamp is the
    # one value here that can carry hostile bytes.
    hostile = layout.relative_time_html('<script>alert(1)</script>', now_iso)
    assert "<script>" not in hostile


def test_future_form_shares_the_past_ladders_own_buckets():
    """layout.relative_future_text() reads the SAME s/m/h/d bucket boundaries the past ladder
    reads (asserted at and around all three), is never negative, is never the past form, and
    clamps an already-elapsed instant to the zero bucket, in both languages (23-03)"""
    boundaries = (0, 1, 59, 60, 61, 3599, 3600, 3601, 86399, 86400, 86401, 900000)
    quantity_re = re.compile("(\\d+)\\u00a0(\\S+)")
    try:
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            for seconds in boundaries:
                past = layout.relative_age_text(seconds, lang=lang)
                future = layout.relative_future_text(seconds, lang=lang)
                assert future, "lang=%s seconds=%d: expected a non-empty future form" % (lang, seconds)
                assert "-" not in future, (
                    "lang=%s seconds=%d: a future form must never carry a negative number, "
                    "got %r" % (lang, seconds, future))
                assert future != past, (
                    "lang=%s seconds=%d: the future form must not be the past form — both "
                    "read %r" % (lang, seconds, future))
                if lang == "en":
                    rearranged = "in " + past[:-len(" ago")]
                    assert future == rearranged, (
                        "lang=en seconds=%d: expected the future form to name the SAME bucket "
                        "and the SAME number the past form names (%r), got %r"
                        % (seconds, rearranged, future))
                    continue
                past_quantity = quantity_re.search(past)
                future_quantity = quantity_re.search(future)
                if past_quantity is None:
                    assert future_quantity is None, (
                        "lang=fr seconds=%d: the past form collapses the sub-minute bucket to "
                        "a phrase with no number (%r) and the future form must collapse the "
                        "same bucket, got %r" % (seconds, past, future))
                    continue
                assert future_quantity is not None, (
                    "lang=fr seconds=%d: expected the future form to carry a quantity with a "
                    "real U+00A0 the way the past form %r does, got %r" % (seconds, past, future))
                assert future_quantity.groups() == past_quantity.groups(), (
                    "lang=fr seconds=%d: expected the future form to name the SAME number and "
                    "unit the past form names %r, got %r"
                    % (seconds, past_quantity.groups(), future_quantity.groups()))
            # The clamp: an already-elapsed "future" instant resolves to the
            # zero bucket, never to a negative and never to a past-tense
            # string.
            assert layout.relative_future_text(-5, lang=lang) == layout.relative_future_text(
                0, lang=lang), "lang=%s: an already-elapsed future instant must resolve to the zero bucket" % (lang,)
    finally:
        prefs.set_request_prefs(lang="en")


def test_relative_time_html_reads_a_future_instant_forwards():
    """layout.relative_time_html() reads a FUTURE instant through the future form and a past
    one through the past form — one function, both directions, bounded and non-negative one
    second either side of now, in both languages (23-03, for 23-06's countdown)"""
    base = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
    now_iso = shp.iso(base)
    try:
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            for delta, direction in ((timedelta(seconds=1), "past"), (timedelta(seconds=-1), "future")):
                rendered = layout.relative_time_html(shp.iso(base - delta), now_iso)
                match = _RELATIVE_ELEMENT_RE.search(rendered)
                assert match is not None, "lang=%s %s: expected a <time> element, got %r" % (
                    lang, direction, rendered)
                assert "-" not in match.group(2), "lang=%s %s: expected no negative number, got %r" % (
                    lang, direction, match.group(2))
            ahead = layout.relative_time_html(shp.iso(base + timedelta(minutes=4)), now_iso)
            ahead_match = _RELATIVE_ELEMENT_RE.search(ahead)
            assert ahead_match is not None, "lang=%s: expected a <time> element for a future instant" % (lang,)
            assert ahead_match.group(2) == layout.relative_future_text(240, lang=lang), (
                "lang=%s: expected a future instant's element to carry the future form %r, "
                "got %r" % (lang, layout.relative_future_text(240, lang=lang), ahead_match.group(2)))
    finally:
        prefs.set_request_prefs(lang="en")


def test_concise_timestamp_htmls_relative_half_is_now_an_element():
    """layout.concise_timestamp_html()'s parenthesised relative half is now a
    <time data-relative> element, its text unchanged, with its outer mono span, its title,
    its absolute-first ordering and its no-raw-ISO rule all untouched (23-03)"""
    now_iso = "2026-09-12T12:00:00+00:00"
    ts = "2026-09-11T22:30:00+00:00"  # 00:30 Paris the NEXT day (CEST)
    rendered = layout.concise_timestamp_html(ts, now_iso)
    match = _RELATIVE_ELEMENT_RE.search(rendered)
    assert match is not None, (
        "expected concise_timestamp_html()'s relative half to be a <time data-relative> "
        "element, got %r" % (rendered,))
    expected_age = layout.relative_age_text(layout.age_seconds(ts, now_iso))
    assert match.group(2) == expected_age
    assert rendered.startswith('<span class="mono" title="')
    assert rendered.endswith("</span>")
    clock = layout.local_clock_text(layout.parse_iso(ts), layout.parse_iso(now_iso))
    assert rendered.index(layout.escape_html(clock)) < rendered.index("<time"), (
        "expected absolute-first ordering to be preserved (D-02/06.6 OQ1)")
    assert ts not in rendered, (
        "expected zero occurrences of the RAW ISO string — the element's own instant is the "
        "Europe/Paris form (D-05/B4, 22-06 Task 3)")


# ==========================================================================
# companion/pages/health_page.py rendered through t(), with its French
# catalogue
# ==========================================================================


def test_health_page_renders_in_french(tmp_path):
    """health_page.render() under lang='fr' carries the French page title and at least three
    other French strings, and none of a short list of English source strings with distinct
    French forms """
    tmp = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(tmp, [(shp.ago(120), 3800)])
    shp.seed_runway_events(tmp, [{
        "ts": shp.ago(300), "callsign": "AFR1234", "icao24": "abc123", "corroborated": "True"}])
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    assert "État" in rendered, "expected the French page title (État, via the shared nav catalogue)"
    for french_text in ("Écran", "Serveur et données", "Se connecte normalement"):
        assert french_text in rendered, "expected the French string %r in the rendered page" % (french_text,)
    for english_text in (
            "Screen status and server data quality, in one place.",
            _battery_section_heading("en"), "Checking in normally", "Server & data"):
        assert english_text not in rendered, (
            "expected no English source string %r to leak into the French render" % (english_text,))


def test_health_page_renders_byte_identical_in_english(tmp_path):
    """health_page.render() under lang='en' (the default) is byte-for-byte unchanged for a
    seeded state — pinned representative substrings """
    tmp = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(tmp, [(shp.ago(120), 3800)])
    try:
        prefs.set_request_prefs(lang="en")
        rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))
    finally:
        prefs.set_request_prefs(lang="en")
    for english_text in (
            health_page.PAGE_PURPOSE_TEXT, health_page.SCREEN_SECTION_HEADING,
            layout.escape_html(health_page.SERVER_DATA_SECTION_HEADING),
            _battery_section_heading(), health_page.DEVICE_STATE_TEXT["ok"], "Health"):
        assert english_text in rendered, "expected the unchanged English string %r under lang='en'" % (
            english_text,)


def test_health_page_device_and_pipeline_timestamps_fully_localise_under_french(tmp_path):
    """compute_health_state()'s device_html/device_detail_html/pipeline_html fields (and
    health_page.render()'s own page) fully localise their timestamps under lang='fr' — no
    English month abbreviation or ' ago' survives — proving the request-language ContextVar
    is resolved at the correct point relative to when this state is computed (Polish fix 2)"""
    tmp = str(tmp_path)
    now_iso = "2026-09-12T00:00:00+00:00"
    device_ts = "2026-09-10T23:58:00+00:00"
    shp.seed_device_health(tmp, [(device_ts, 3800)])
    shp.seed_meta(tmp, **{
        history_db.META_LAST_PIPELINE_RUN: device_ts, history_db.META_LAST_DETECTION: device_ts})
    try:
        prefs.set_request_prefs(lang="fr")
        state = health_page.compute_health_state(tmp, now=now_iso)
        rendered = health_page.render(dict(shp.ctx(tmp, now_iso), health_state=state))
    finally:
        prefs.set_request_prefs(lang="en")
    fragments = (state["device_html"], state["device_detail_html"], state["pipeline_html"], rendered)
    for fragment in fragments:
        assert "sept." in fragment, "expected the French month abbreviation 'sept.' in %r" % (fragment,)
        assert " ago" not in fragment, "expected no English ' ago' in %r" % (fragment,)
        for english_month in (
                "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                "Oct", "Nov", "Dec"):
            assert english_month not in fragment, (
                "expected no English month abbreviation %r in %r" % (english_month, fragment))
    assert "il y a 1" in state["device_detail_html"], (
        "expected the French relative-age connector 'il y a 1' in device_detail_html")


def test_health_catalog_every_key_and_value_is_a_nonempty_str():
    """every key of companion/i18n_fr/health.py's own CATALOG is a non-empty str mapping to a
    non-empty str"""
    bad = [
        (key, value) for key, value in i18n_fr_health.CATALOG.items()
        if not isinstance(key, str) or not key or not isinstance(value, str) or not value]
    assert not bad, "expected every CATALOG key/value to be a non-empty str, found: %r" % (bad,)


# ==========================================================================
# companion/pages/airlines_page.py — the illustration gallery
# ==========================================================================


def test_airlines_page_opens_with_shared_page_header(tmp_path):
    """Airlines opens with the shared layout.page_header() component, not a bare <h1>"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    assert '<h1 class="page-title">Airlines</h1>' in rendered
    assert '<h1 class="text-heading">' not in rendered


def test_gallery_renders_one_card_per_target_airline(tmp_path):
    """the gallery renders exactly one .airline-card per illustrations.target_airline_names()
    entry (36 against today's data)"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    expected = len(illustrations.target_airline_names())
    assert rendered.count('class="airline-card"') == expected


def test_every_card_image_source_passes_route_membership_test(tmp_path):
    """every rendered card image source, with the route prefix stripped, is a member of
    illustrations.target_filenames() — every rendered URL provably passes the route's own
    membership test"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    targets = set(illustrations.target_filenames())
    prefix = airlines_page.ILLUSTRATION_ROUTE_PREFIX
    sources = re.findall(r'src="([^"]+)"', rendered)
    assert sources, "expected at least one <img src=...> in the rendered gallery"
    for src in sources:
        assert src.startswith(prefix) and src.endswith(".png"), (
            "expected every image source to be %s{key}.png, got %r" % (prefix, src))
        filename = src[len(prefix):]
        assert filename in targets, "%r is not a member of illustrations.target_filenames()" % (filename,)


def test_air_caraibes_card_has_three_upper_cased_chips_including_a350_1000(tmp_path):
    """the Air Caraïbes card renders exactly three chips (A330, A350-1000, ATR72) — the
    A350-1000 shape-slug-validation trap is not fallen into"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    card_slice = _card_slice(rendered, "Air Caraïbes")
    got_chips = re.findall(r'class="airline-card__chip">([^<]+)<', card_slice)
    assert got_chips == ["A330", "A350-1000", "ATR72"], (
        "expected exactly [A330, A350-1000, ATR72] chips for Air Caraïbes, got %r" % (got_chips,))


def test_primary_only_airline_renders_no_chips_container(tmp_path):
    """an airline with no variant entries (Air France) renders no .airline-card__chips
    container at all"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    card_slice = _card_slice(rendered, "Air France")
    assert "airline-card__chips" not in card_slice


def test_variant_chip_label_covers_both_domains():
    """variant_chip_label() upper-cases every alphanumeric type code verbatim and word-cases
    the Embraer/Beechcraft manufacturer forms"""
    cases = {
        "a320": "A320", "atr72": "ATR72", "a330": "A330", "b737": "B737",
        "a350-1000": "A350-1000", "embraer": "Embraer", "beechcraft1900d": "Beechcraft 1900D",
    }
    for shape, expected in cases.items():
        assert airlines_page.variant_chip_label(shape) == expected


def test_illustration_route_prefix_matches_app_constant():
    """airlines_page.ILLUSTRATION_ROUTE_PREFIX equals app.ILLUSTRATION_IMAGE_ROUTE_PREFIX (the
    duplicated-not-imported route-prefix contract)"""
    assert airlines_page.ILLUSTRATION_ROUTE_PREFIX == app.ILLUSTRATION_IMAGE_ROUTE_PREFIX


def test_every_card_image_carries_matching_intrinsic_dimensions(tmp_path):
    """every rendered card image carries width/height attributes matching
    illustration_normalize.ILLUSTRATION_TARGET_WIDTH/HEIGHT exactly"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    tags = re.findall(r'<img class="airline-card__image"[^>]*>', rendered)
    expected = len(illustrations.target_airline_names())
    assert len(tags) == expected
    expected_attr = 'width="%d" height="%d"' % (
        illustration_normalize.ILLUSTRATION_TARGET_WIDTH, illustration_normalize.ILLUSTRATION_TARGET_HEIGHT)
    for tag in tags:
        assert expected_attr in tag, "expected %r in every card image tag, missing from %r" % (expected_attr, tag)


def test_gallery_filter_bar_carries_all_four_contract_markers_exactly_once(tmp_path):
    """the gallery filter bar carries exactly one each of
    data-filter-input/-count/-clear/-empty"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    for marker in ("data-filter-input", "data-filter-count", "data-filter-clear", "data-filter-empty"):
        assert rendered.count(marker) == 1, "expected exactly one %r marker, got %d" % (
            marker, rendered.count(marker))


def test_gallery_filter_clear_control_is_a_real_button(tmp_path):
    """the gallery filter bar's Clear control is a real <button type="button"> (retired)"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    assert '<button type="button" data-filter-clear>Clear</button>' in rendered


def test_gallery_filter_label_for_matches_input_id(tmp_path):
    """the gallery filter label's for attribute equals the search input's id, and that id is
    the hyphen-free value Task 1 pins (superseding the now-stale
    06. §7.2 row)"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    assert airlines_page._FILTER_INPUT_ID == "airlines_gallery_filter_input", (
        "expected the hyphen-free input id pinned by quick task 260921-p2w Task 1, got %r"
        % (airlines_page._FILTER_INPUT_ID,))
    expected_label = '<label class="text-label" for="%s">' % airlines_page._FILTER_INPUT_ID
    assert expected_label in rendered
    assert ('<input type="search" id="%s" autocomplete="off" spellcheck="false" '
            'autocapitalize="characters" data-filter-input>' % airlines_page._FILTER_INPUT_ID
            in rendered)


def test_compagnies_and_health_filter_inputs_carry_safari_autofill_suppression_attributes(tmp_path):
    """Compagnies' gallery filter input and Health's registry filter input both carry
    autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill
    suppression)"""
    attrs = ('autocomplete="off"', 'spellcheck="false"', 'autocapitalize="characters"')
    tmp = str(tmp_path)
    airlines_rendered = airlines_page.render(shp.ctx(tmp))
    now = shp.now()
    shp.seed_unresolved_prefixes(tmp, {
        "ABC": {"count": 3, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    health_rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))
    for possessive, rendered in (("Compagnies'", airlines_rendered), ("Health's", health_rendered)):
        for attr in attrs:
            assert attr in rendered, (
                "expected %s search filter input to carry %r — without it, iOS Safari offers "
                "contact/phone-number autofill on the field" % (possessive, attr))


def test_every_rendered_search_input_carries_safari_autofill_suppression_attributes(tmp_path):
    """every <input type="search"> this app can render — Compagnies' gallery filter, Health's
    registry filter (seeded so it appears) and Flights' history filter — carries
    autocomplete=off/spellcheck=false/autocapitalize=characters, so a fourth filter bar cannot
    reintroduce the Safari contact/phone-number autofill defect the developer photographed on
    2026-09-21 (rewritten from an ast-based source scan to the rendered behaviour on every
    page known to render one today)"""
    pages = _rendered_pages_with_search_inputs(tmp_path)
    total = 0
    for rendered in pages:
        inputs = parse_html(rendered).find_all(tag="input", attrs={"type": "search"})
        total += len(inputs)
        for node in inputs:
            for attr, expected in (
                    ("autocomplete", "off"), ("spellcheck", "false"), ("autocapitalize", "characters")):
                assert node.attrs.get(attr) == expected, (
                    "iOS Safari offers contact/phone-number autofill on a search input missing "
                    "%s=%r, got %r" % (attr, expected, node.attrs))
    assert total >= 3, (
        "expected at least 3 <input type=\"search\"> occurrences across the pages this app "
        "renders (the floor known at plan time), found only %d — this would let the check "
        "pass vacuously if every filter input were deleted" % total)


def test_no_filter_input_id_anywhere_in_the_app_contains_a_hyphen(tmp_path):
    """no *_FILTER_INPUT_ID constant value and no rendered <input type="search"> id, across
    every page this app renders one on, contains a hyphen — the documented WebKit/Safari
    trigger that offers the user's own Contacts phone numbers on a name-less type="search"
    field even with autocomplete="off" set (rewritten from an ast-based source/tag scan to a
    direct check of the real production constants plus the rendered id each one produces)"""
    mechanism = (
        "WebKit/Safari renders a contacts icon inside a text input and offers phone numbers "
        "from the user's OWN Contacts card when the field's id contains a hyphen, ignoring "
        "autocomplete=\"off\""
    )
    for module, name in (
            (airlines_page, "airlines_page"), (health_page, "health_page"),
            (history_page, "history_page")):
        value = module._FILTER_INPUT_ID
        assert "-" not in value, "%s — %s._FILTER_INPUT_ID = %r" % (mechanism, name, value)
    pages = _rendered_pages_with_search_inputs(tmp_path)
    for rendered in pages:
        for node in parse_html(rendered).find_all(tag="input", attrs={"type": "search"}):
            input_id = node.attrs.get("id", "")
            assert "-" not in input_id, "%s — rendered id %r" % (mechanism, input_id)


def test_gallery_filter_count_and_empty_body_name_the_real_total(tmp_path):
    """the gallery filter bar's count text and empty-state body both name the real (36) card
    total"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    total = len(illustrations.target_airline_names())
    count_text = "%d of %d shown" % (total, total)
    assert count_text in rendered
    empty_body = airlines_page._FILTER_EMPTY_BODY_TEMPLATE % total
    assert empty_body in rendered


def test_every_card_carries_distinct_filter_text_and_group(tmp_path):
    """every card carries a data-filter-text equal to its own lower-cased airline name, and
    the set of data-filter-group values has the same size as the card count"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    for airline_name in illustrations.target_airline_names():
        expected_text = 'data-filter-text="%s"' % airline_name.lower()
        assert expected_text in rendered, "expected %r for airline %r" % (expected_text, airline_name)
    groups = re.findall(r'data-filter-group="(\d+)"', rendered)
    assert len(set(groups)) == len(illustrations.target_airline_names()), (
        "expected as many distinct data-filter-group values as target airlines, got %d "
        "distinct of %d total occurrences" % (len(set(groups)), len(groups)))


def test_airlines_page_imports_no_history_db_or_sqlite_but_does_import_poll_loop():
    """companion/pages/airlines_page.py imports no history-database module and no sqlite
    module (a non-goal: no detection-history cross-reference), and does import poll_loop"""
    # A runtime check of airlines_page's own module namespace, which name
    # IS bound there being a fact about its own import statements — never
    # a sys.modules-membership check, since poll_loop (which this module
    # IS required to import) itself imports sqlite3/history_db.
    import sqlite3
    import server.poll_loop as poll_loop_module
    from server import history_db
    bound_values = list(vars(airlines_page).values())
    assert sqlite3 not in bound_values, "airlines_page.py must not import sqlite3 (D-17 non-goal)"
    assert history_db not in bound_values, (
        "airlines_page.py must not import server.history_db (D-17 non-goal)")
    assert vars(airlines_page).get("poll_loop") is poll_loop_module, (
        "expected airlines_page to import poll_loop (phase 13 D-11 supersession)")


def test_airlines_page_no_longer_renders_registry_or_stats_headers(tmp_path):
    """the rendered Airlines gallery contains none of the migrated unresolved-prefix registry
    or resolution-statistics table column headers (non-goal)"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    for header in ("Prefix", "First seen", "Last seen", "Example callsign", "Source", "Description"):
        assert ("<th>%s</th>" % header) not in rendered, (
            "the Airlines gallery must not render the migrated %r column header (D-13)" % header)


def test_health_page_still_renders_both_migrated_header_sets(tmp_path):
    """the rendered Health page still contains both migrated header sets — the content moved,
    it was not lost"""
    tmp = str(tmp_path)
    registry = {"ABC": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "ABC123"}}
    shp.seed_unresolved_prefixes(tmp, registry)
    shp.seed_runway_events(tmp, [{"ts": shp.iso(shp.now()), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(tmp))
    for header in ("Prefix", "First seen", "Last seen", "Example callsign", "Source", "Description"):
        assert ("<th>%s</th>" % header) in rendered, (
            "expected Health to still render the migrated %r column header" % header)


def test_airlines_page_module_exposes_no_deleted_diagnostics_symbol():
    """importing companion.pages.airlines_page raises no error, and the module exposes none
    of the deleted diagnostics symbols"""
    for name in (
            "unresolved_rows", "coverage_status", "resolution_stats", "STATS_UNAVAILABLE_TEXT",
            "RESOLUTION_WINDOW_DAYS", "_registry_row_html", "_registry_table_html",
            "_registry_section", "_resolved_headline_html", "_stats_table_html", "_safe_query"):
        assert not hasattr(airlines_page, name), (
            "airlines_page module must no longer expose the deleted diagnostics symbol %r" % name)


# ==========================================================================
# The click-to-enlarge lightbox
# ==========================================================================


def test_airline_card_zoom_button_attrs_match_expected(tmp_path):
    """every card wraps its image in exactly one .airline-card__zoom button whose
    data-view-panel-src is byte-identical to that same card's <img src>, whose
    data-view-panel-caption equals CARD_IMAGE_ALT_TEMPLATE %% name, and whose aria-label
    equals ZOOM_LABEL_TEMPLATE %% name"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    for airline_name in ("Air Caraïbes", "Air France"):
        card_slice = _card_slice(rendered, airline_name)
        zoom_buttons = re.findall(r'<button type="button" class="airline-card__zoom"[^>]*>', card_slice)
        assert len(zoom_buttons) == 1, (
            "expected exactly one .airline-card__zoom button wrapping %r's image, got %d"
            % (airline_name, len(zoom_buttons)))
        button_tag = zoom_buttons[0]

        img_src_match = re.search(r'<img class="airline-card__image" src="([^"]+)"', card_slice)
        assert img_src_match, "expected an .airline-card__image with a src attribute for %r" % (airline_name,)
        img_src = img_src_match.group(1)

        src_attr_match = re.search(r'data-view-panel-src="([^"]+)"', button_tag)
        assert src_attr_match and src_attr_match.group(1) == img_src, (
            "expected the zoom button's data-view-panel-src to be byte-identical to %r's card "
            "image src (%r), got %r"
            % (airline_name, img_src, src_attr_match.group(1) if src_attr_match else None))

        expected_caption = layout.escape_html(airlines_page.CARD_IMAGE_ALT_TEMPLATE % airline_name)
        caption_attr_match = re.search(r'data-view-panel-caption="([^"]+)"', button_tag)
        assert caption_attr_match and caption_attr_match.group(1) == expected_caption, (
            "expected %r's zoom button caption attribute to equal %r, got %r"
            % (airline_name, expected_caption, caption_attr_match.group(1) if caption_attr_match else None))

        expected_aria = layout.escape_html(airlines_page.ZOOM_LABEL_TEMPLATE % airline_name)
        aria_match = re.search(r'aria-label="([^"]+)"', button_tag)
        assert aria_match and aria_match.group(1) == expected_aria, (
            "expected %r's zoom button aria-label to equal %r, got %r"
            % (airline_name, expected_aria, aria_match.group(1) if aria_match else None))


def test_lightbox_dialog_renders_once_wide_with_own_note_text(tmp_path):
    """the shared lightbox dialog is emitted exactly once, carries both the lightbox and
    lightbox--wide classes plus all three lightbox__* elements and the close attribute, and
    its note element renders empty (LIGHTBOX_NOTE is deliberately '' after live developer
    feedback rejected both the original and the reworded copy; the element still exists for
    panel-lookup.js's shared guard clause)"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    dialog_count = rendered.count('id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID)
    assert dialog_count == 1, "expected exactly one #%s dialog, got %d" % (
        airlines_page.LIGHTBOX_DIALOG_ID, dialog_count)
    assert '<dialog class="lightbox lightbox--wide"' in rendered
    for marker in ("lightbox__image", "lightbox__caption", "lightbox__note", airlines_page._VIEW_PANEL_CLOSE_ATTR):
        assert marker in rendered, "expected %r in the rendered dialog markup" % (marker,)
    assert airlines_page.LIGHTBOX_NOTE == "", (
        "expected airlines_page.LIGHTBOX_NOTE to be the empty string (developer's own call "
        "that this lightbox needs no note), got %r" % (airlines_page.LIGHTBOX_NOTE,))
    assert '<p class="lightbox__note text-body"></p>' in rendered


def test_airline_card_zoom_stylesheet_contract(css_text):
    """.airline-card__zoom neutralizes the base button rule's height/padding/border/background
    and declares the zoom cursor, and declares no pointer-events property anywhere — the
    retired orientation gate (a misreading of the developer's original request, corrected on
    the same live test) must not silently return"""
    zoom_rules = rules_with_selector(css_text, ".airline-card__zoom")
    assert zoom_rules, "expected a .airline-card__zoom rule in the served stylesheet"
    base = dict(zoom_rules[0].declarations)
    for prop, value in (
            ("height", "auto"), ("padding", "0"), ("border", "none"),
            ("background", "none"), ("cursor", "zoom-in")):
        assert base.get(prop) == value, (
            "expected %s: %s inside the base .airline-card__zoom rule, got %r" % (prop, value, base))
    assert not any("pointer-events" in dict(rule.declarations) for rule in zoom_rules), (
        "expected no .airline-card__zoom rule to declare pointer-events at all")
    assert not any(
        "orientation: portrait" in " ".join(rule.at_rules) for rule in css_rules(css_text)), (
        "expected the retired orientation gate to be fully removed")


def test_mobile_button_override_block_and_source_order(css_text):
    """the mobile-only button override exists as a @media (max-width: 959.98px) block,
    declares a bare `button` rule with height: 36px and font-size: 14px, sits AFTER the base
    `button` rule in source order (the mechanism that lets it win at equal specificity), and
    the base rule's own desktop values (height: 30px, font-size: 13px) are untouched
    (06.6.4.1.1-03 D-18b)"""
    at_rule = "@media (max-width: 959.98px)"
    rules = css_rules(css_text)
    candidates = [
        index for index, rule in enumerate(rules)
        if rule.selectors == ("button",) and rule.at_rules == (at_rule,)
        and dict(rule.declarations).get("height") == "36px"
        and dict(rule.declarations).get("font-size") == "14px"
    ]
    assert len(candidates) == 1, (
        "expected exactly one %r block to declare a bare `button { height: 36px; "
        "font-size: 14px; }` rule, found %d" % (at_rule, len(candidates)))
    media_index = candidates[0]
    base_candidates = [
        (index, rule) for index, rule in enumerate(rules)
        if rule.selectors == ("button",) and rule.at_rules == ()
    ]
    assert base_candidates, "expected a base `button` rule outside any @media block"
    base_index, base_rule = base_candidates[0]
    assert base_index < media_index, (
        "expected the base `button {` rule to come BEFORE the mobile override that wins over it")
    base_decls = dict(base_rule.declarations)
    assert base_decls.get("height") == "30px"
    assert base_decls.get("font-size") == "13px"


def test_lightbox_wide_max_width_matches_illustration_target_width(css_text):
    """.lightbox--wide's max-width equals illustration_normalize.ILLUSTRATION_TARGET_WIDTH — a
    future change to the normalized frame size cannot silently leave the dialog capped at a
    stale width"""
    decls = declarations_for(css_text, ".lightbox--wide")
    max_width = decls.get("max-width", "")
    match = re.match(r"(\d+)px$", max_width)
    assert match, "expected a max-width: Npx declaration inside .lightbox--wide, got %r" % (max_width,)
    assert int(match.group(1)) == illustration_normalize.ILLUSTRATION_TARGET_WIDTH


# ------------------------------------------------------------------------
# The illustration-replace control, relocated from a per-card disclosure
# into the shared lightbox.
# ------------------------------------------------------------------------


def test_replace_form_action_matches_trigger_attribute_membership(tmp_path):
    """exactly one lightbox replace form is rendered, and every card's zoom trigger carries a
    data-view-panel-replace-action attribute (one per illustrations.target_airline_names()
    entry) whose value, with the route prefix stripped, is a member of illustrations.
    target_filenames() — mirroring the existing image-source membership check"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    form_count = rendered.count('<form class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
    assert form_count == 1, "expected exactly one lightbox replace form, got %d" % form_count
    targets = set(illustrations.target_filenames())
    prefix = airlines_page.ILLUSTRATION_ROUTE_PREFIX
    actions = re.findall(r'data-view-panel-replace-action="([^"]+)"', rendered)
    per_airline = 1
    expected = per_airline * len(illustrations.target_airline_names())
    assert len(actions) == expected, (
        "expected %d replace-action triggers (%d per target airline), got %d"
        % (expected, per_airline, len(actions)))
    for action in set(actions):
        assert actions.count(action) == per_airline, (
            "expected each airline's replace action to appear exactly %d time(s), %r "
            "appeared %d" % (per_airline, action, actions.count(action)))
    for action in actions:
        assert action.startswith(prefix) and action.endswith(".png"), (
            "expected every replace-action trigger to be %s{key}.png, got %r" % (prefix, action))
        filename = action[len(prefix):]
        assert filename in targets, "%r is not a member of illustrations.target_filenames()" % (filename,)


def test_replace_form_declares_post_multipart_enctype_and_present_action(tmp_path):
    """the single lightbox replace form declares method="post", enctype="multipart/form-data"
    — a missing enctype would silently send the file as a filename string, a real failure
    mode, not a formality — and a literally present action="" placeholder for
    panel-lookup.js to overwrite"""
    rendered = airlines_page.render(shp.ctx(str(tmp_path)))
    forms = re.findall(r'<form class="%s"[^>]*>' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, rendered)
    assert len(forms) == 1, "expected exactly one replace form, got %d" % len(forms)
    form_tag = forms[0]
    assert 'method="post"' in form_tag
    assert 'enctype="multipart/form-data"' in form_tag, (
        "expected enctype=\"multipart/form-data\" in %r — a form missing the enctype would "
        "silently send the file as a filename string" % (form_tag,))
    assert 'action=""' in form_tag, (
        "expected a literally present action=\"\" placeholder in %r" % (form_tag,))
