"""Part 04 of the `companion/test_status_pages.py` migration chain
(33-28-PLAN.md): the original harness's `check()` calls #140-#171 (minus
the `anomaly_active("/nonexistent/...")` root-unsafe check, pulled forward
into 33-25) — the nested-card heading-to-content rhythm allowlist and its
two CSS rhythm rules, the Resolution-statistics table's `data-table--prose`
opt-out and its Description-column muting (markup + builder + stylesheet),
the registry's mobile `.data-cards` representation (completeness, the
toggle contract, pairing with the desktop table, the stacked-cell/
shortened-French-header fit) and the standing no-chrome-with-no-data rule,
the battery readout's humanised detail and its typographic split, the
`anomaly_active()`/banner-presence agreement, the stat-tile reframe and
tile-icon survival guards, the auto-refresh pill's markup and stylesheet
contracts, the pipeline tile's second line (present and absent), the
persistent honest-clock freshness note, four one-line UI-regression fixes,
two spacing-pair guards, the `<summary>` accent rule, and the fetch/swap
loop's cross-file contracts (the interaction-skip guard, the swap-selector
registry's one-definition/one-key-set proof, the server-rendered page key,
the three things the loop must not repaint, Flights joining the loop, and
the new-row highlight diff).

One check in this slice, pinning that a reversal of an earlier auto-refresh
decision is recorded in prose at both places it touches, is deleted rather
than ported (TST-12 rubric P/J): it opened `companion/static/freshness.js`
for a quick-task identifier and a house "SUPERSEDED" token, and separately
opened a phase context document under the planning tree for the same pair
beside the original decision's wording — plan-history prose in a header
comment and a planning document, with no rendered or served behaviour
behind either assertion.

Two checks in this slice read a production `.py` source file for a text
fragment with no observable consequence beyond a check this module already
makes structurally (TST-12 rubric S), and drop that fragment: whether the
swap-selector tuple is redefined a second time in `companion/pages/
health_page.py` is already provable by identity (the module attribute
either IS the registry's own object or it structurally is not, given
Python never interns distinct tuple literals across modules), and whether
`companion/layout.py`'s own comment explains an exclusion in prose is not
something a served page or script can disagree with.

One check's stylesheet half asserts on the file's own opening comment
block (an "accent colour is reserved for these elements" list) rather
than a rendered rule (rubric C); the comment-only clause is dropped and
the rule-body clause it pairs with (a real declaration on a real
selector) is kept.

Every CSS check in this slice (rubric C) fetches the stylesheet
`companion/app.py` actually serves and asserts on it structurally via
`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`
— never a regex/substring probe over the raw served text (33-FOLLOWUPS.md
F-01) — reusing 33-26/33-27's single module-scoped read-only server
(`_module_server`/`css_text`), since none of the checks below mutate
server state. A source-order fact (one rule sitting before or after
another) is proven by comparing each rule's INDEX in `css_rules()`'s
ordered list, never by comparing string offsets in raw text.

Every check in this slice that reads `companion/static/freshness.js` or
`companion/static/battery-trend.js` (rubric J) fetches it with
`served_asset()` instead of opening it from disk. Some of those checks
need the file's own quoted string literals (a selector, an attribute
name) intact, so this module's own `strip_js_line_and_block_comments()`
helper (added to `companion/test_status_pages_helpers.py` for this chain
— `companion_markup.strip_js_comments_and_strings()` erases string
literals too, which this slice's checks cannot afford) blanks only the
comments, mirroring the legacy harness's own `_js_code_without_comments()`
idiom exactly. Whether a given check strips comments or reads the raw
served text follows the SAME choice the legacy check itself made — no
check in this slice changes what it looks for, only where it looks.

Every other check in this module calls `companion.pages.health_page`/
`companion.layout`/`companion.i18n`/`companion.i18n_fr.health`/
`companion.illustration_normalize` directly, in-process, seeding fixtures
under `tmp_path` via `companion.test_status_pages_helpers`.
"""
import re
from datetime import timedelta

import pytest

from companion import i18n, illustration_normalize, layout
from companion.i18n_fr import health as i18n_fr_health
from companion.pages import airlines_page, health_page, history_page
import companion.test_status_pages_helpers as shp
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for, rules_with_selector
from server import history_db


# --- module-scoped read-only server, for the served-CSS/JS checks only -----

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


@pytest.fixture(scope="module")
def freshness_js(_module_server):
    return served_asset(_module_server, "/static/freshness.js")


@pytest.fixture(scope="module")
def battery_trend_js(_module_server):
    return served_asset(_module_server, "/static/battery-trend.js")


# --- shared helpers, local to this part (mirrors 33-26/33-27's own copy) ---

def _battery_section_heading(lang="en"):
    """The battery-trend heading's own rendered text, computed the SAME
    way `_battery_trend_section_html()` computes it."""
    return i18n.t_lang(health_page.BATTERY_SECTION_HEADING_TEMPLATE, lang) % (
        health_page.BATTERY_TREND_WINDOW_DAYS // 30)


def _rule_index(rules, selector, at_rules=()):
    """The index of the first rule in `rules` (as returned by
    `css_rules()`, source order preserved) whose selectors include
    `selector` exactly under `at_rules`. Raises `AssertionError` — never
    silently returns -1 — when no such rule exists, so a source-order
    comparison built on this cannot pass vacuously."""
    for index, rule in enumerate(rules):
        if selector in rule.selectors and rule.at_rules == at_rules:
            return index
    raise AssertionError(
        "no rule for selector %r under at_rules %r" % (selector, at_rules))


def _rule_with_selectors(rules, selectors, at_rules=()):
    """The one rule in `rules` whose selector SET equals `selectors`
    exactly under `at_rules`, or `None`."""
    wanted = set(selectors)
    for rule in rules:
        if set(rule.selectors) == wanted and rule.at_rules == at_rules:
            return rule
    return None


# ==========================================================================
# The nested-card heading-to-content rhythm allowlist, and its two CSS rules
# ==========================================================================


def test_nested_card_heading_rhythm_holds_for_every_allowed_element(tmp_path, css_text):
    """All three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics)
    show one heading-to-content rhythm in both the empty and seeded state — the element after
    </h2> is either rhythm-governed p.text-body or a member of the verified no-top-margin
    allowlist — and style.css's demotion rule/prose rhythm rule carry the sketch's two margin
    values in the right source order"""
    allowed = (
        '<p class="text-body">', '<p class="text-body section-caption">',
        '<p class="text-label section-caption">',
        '<p id="%s"' % health_page.BATTERY_READOUT_ID, "<div ", "<details", "<svg ",
        '<ul class="data-cards">')
    for seeded in (False, True):
        state_dir = tmp_path / ("seeded" if seeded else "empty")
        state_dir.mkdir()
        state_dir = str(state_dir)
        now = shp.now()
        if seeded:
            shp.seed_device_health(state_dir, [
                (shp.iso(now - timedelta(minutes=3)), 4200),
                (shp.iso(now - timedelta(minutes=1)), 4190),
            ])
            shp.seed_runway_events(state_dir, [
                {"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
            shp.seed_unresolved_prefixes(state_dir, {
                "JAF": {"count": 4, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                        "example_callsign": "JAF412"},
            })
        rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))
        headings_to_check = [
            _battery_section_heading(), health_page.UNRESOLVED_SECTION_HEADING]
        if seeded:
            headings_to_check.append(health_page.STATS_SECTION_HEADING)
        else:
            assert health_page.STATS_SECTION_HEADING not in rendered, (
                "expected the empty Resolution-statistics section to be entirely absent")
        for heading in headings_to_check:
            heading_at = rendered.index(">%s" % heading)
            after = rendered[rendered.index("</h2>", heading_at) + len("</h2>"):]
            if after.startswith("</section>"):
                continue
            assert after.startswith(allowed), (
                "seeded=%s: %r is followed by %r, outside the no-top-margin allowlist"
                % (seeded, heading, after[:60]))

    rules = css_rules(css_text)
    heading_decls = declarations_for(css_text, ".page-section--nested > h2")
    assert heading_decls.get("margin-bottom") == "var(--space-md)", (
        "expected the nested-card heading demotion rule to declare the sketch's medium bottom margin")
    prose_rule = next(
        rule for rule in rules if ".page-section--nested > p.text-body" in rule.selectors)
    assert ".battery-trend-section > p.text-body" in prose_rule.selectors, (
        "expected the prose rhythm rule to also cover .battery-trend-section > p.text-body")
    assert dict(prose_rule.declarations).get("margin") == "0 0 var(--space-sm)", (
        "expected the prose rhythm rule to declare zero above and the small space below")
    assert (_rule_index(rules, ".page-section--nested > h2")
            < _rule_index(rules, ".page-section--nested > p.text-body")), (
        "expected the prose rhythm rule to sit after the heading rule it pairs with")


def test_resolution_statistics_table_is_the_only_data_table_prose(tmp_path, css_text):
    """Exactly the Resolution-statistics table carries data-table--prose, neither the battery
    readings table nor the unresolved-prefix registry table does, and style.css's
    .data-table--prose sits after .data-table with the shared max-content floor still intact on
    the base rule"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4190),
    ])
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))

    assert rendered.count("data-table--prose") == 1
    stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
    prose_at = rendered.index("data-table--prose")
    assert prose_at > stats_at, "expected the opted-out table to be the Resolution-statistics one"
    unresolved_at = rendered.index(health_page.UNRESOLVED_SECTION_HEADING)
    assert not (unresolved_at < prose_at < stats_at), (
        "the unresolved-prefix registry table must not carry data-table--prose")
    readings_at = rendered.index(_battery_section_heading())
    assert not (readings_at < prose_at < unresolved_at), (
        "the battery readings table must not carry data-table--prose")

    rules = css_rules(css_text)
    assert _rule_index(rules, ".data-table") < _rule_index(rules, ".data-table--prose"), (
        "equal specificity means source order decides: .data-table--prose must follow .data-table")
    assert declarations_for(css_text, ".data-table").get("min-width") == "max-content", (
        "expected .data-table to still declare the shared no-crop floor")
    assert declarations_for(css_text, ".data-table--prose").get("min-width") == "0", (
        "expected .data-table--prose to neutralise the floor with min-width: 0")


def test_description_column_is_the_only_muted_column(tmp_path, css_text):
    """The Description column is the only muted column end to end — markup (exactly
    len(_SOURCE_ROWS) desc cells, all inside Resolution-statistics), builder (data_table()'s
    desc_columns contract: inert default, byte-identical mono-only output, additive-only
    desc-only output, both-roles joining mono first) and stylesheet (.data-table td.desc's 70%
    muted colour, no min-width, no opacity, no muted token anywhere in the file)"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))

    expected = len(health_page._SOURCE_ROWS)
    desc_count = rendered.count('<td class="desc">')
    assert desc_count == expected, (
        "expected exactly %d desc-class cells (one per _SOURCE_ROWS entry), got %d"
        % (expected, desc_count))

    stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
    unresolved_at = rendered.index(health_page.UNRESOLVED_SECTION_HEADING)
    battery_at = rendered.index(_battery_section_heading())
    first_desc_at = rendered.index('<td class="desc">')
    assert first_desc_at > stats_at, (
        "expected every desc cell to live in the Resolution-statistics table")
    assert not (unresolved_at < first_desc_at < stats_at), (
        "the unresolved-prefix registry table must carry no desc cell")
    assert not (battery_at < first_desc_at < unresolved_at), (
        "the battery readings table must carry no desc cell")

    plain = layout.data_table(["A", "B"], [["1", "2"]])
    assert 'class="desc"' not in plain and 'class="mono"' not in plain
    mono_only = layout.data_table(["A", "B"], [["1", "2"]], mono_columns=(0,))
    assert '<td class="mono">1</td>' in mono_only
    desc_only = layout.data_table(["A", "B"], [["1", "2"]], desc_columns=(1,))
    assert desc_only.replace(' class="desc"', "") == plain, (
        "expected desc_columns to change only the added class, nothing else")
    both = layout.data_table(["A", "B"], [["1", "2"]], mono_columns=(0,), desc_columns=(0,))
    assert '<td class="mono desc">1</td>' in both, (
        "expected a cell named by both keywords to carry both classes, mono first")

    desc_decls = declarations_for(css_text, ".data-table td.desc")
    assert desc_decls.get("color") == "color-mix(in srgb, var(--color-text) 70%, transparent)", (
        "expected .data-table td.desc to reuse the file's existing 70% muted strength")
    assert "min-width" not in desc_decls, (
        "a min-width in .data-table td.desc is the horizontal overflow .data-table--prose "
        "removed returning one breakpoint down")
    assert "opacity" not in desc_decls, (
        "expected colour, not opacity — opacity would fade the cell's border hairline too")
    for rule in css_rules(css_text):
        for prop, value in rule.declarations:
            assert "--color-text-muted" not in prop and "--color-text-muted" not in value, (
                "a second muted value/token is the thing this stylesheet's own comments forbid")


def test_stats_cards_list_is_complete_and_precedes_the_table(tmp_path):
    """The Resolution-statistics table has a complete mobile .data-cards representation — one
    item per _SOURCE_ROWS entry, every label/full-gloss/count present, positioned before its
    unchanged desktop table"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc001", "route_source": "fresh_hit"},
        {"ts": shp.iso(now), "hex": "abc002", "route_source": "cache_hit"},
        {"ts": shp.iso(now), "hex": "abc003", "route_source": "cache_hit"},
        {"ts": shp.iso(now), "hex": "abc004", "route_source": "airline_only"},
        {"ts": shp.iso(now), "hex": "abc005", "route_source": "miss"},
    ])
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))

    assert rendered.count('<ul class="data-cards">') == 1
    expected_items = len(health_page._SOURCE_ROWS)
    item_count = rendered.count('<li class="data-card">')
    assert item_count == expected_items, (
        'expected exactly %d <li class="data-card"> items, got %d' % (expected_items, item_count))

    stats_at = rendered.index(health_page.STATS_SECTION_HEADING)
    cards_at = rendered.index('<ul class="data-cards">')
    prose_at = rendered.index("data-table--prose")
    assert stats_at < cards_at < prose_at, (
        "expected the card list to sit after the Resolution-statistics heading and "
        "before its data-table--prose table")

    card_slice = rendered[cards_at:rendered.index("</ul>", cards_at) + len("</ul>")]
    with history_db.open_db(state_dir) as conn:
        stats = health_page.resolution_stats(conn, health_page.RESOLUTION_WINDOW_DAYS)
    for label, gloss, count in stats["rows"]:
        assert layout.escape_html(label) in card_slice
        assert layout.escape_html(gloss) in card_slice, (
            "expected the FULL gloss inside the card-list slice, untruncated")
        assert str(count) in card_slice

    assert rendered.count("data-table--prose") == 1
    assert rendered.count('<td class="desc">') == len(health_page._SOURCE_ROWS)


def test_data_cards_toggle_contract_and_untouched_rules(css_text):
    """The .data-cards mobile toggle contract exists at both breakpoints, .data-card__label
    mirrors .data-table th's label tier by value, .data-table-wrap's scroll-edge shadow stays
    intact, and the three literal selectors this harness indexes by elsewhere are all still
    present"""
    base_decls = declarations_for(css_text, ".data-cards ~ .data-table-wrap")
    assert base_decls.get("display") == "none", (
        "expected the base .data-cards ~ .data-table-wrap rule to hide the desktop table")

    media = ("@media (min-width: 960px)",)
    hide_cards_decls = declarations_for(css_text, ".data-cards", at_rules=media)
    assert hide_cards_decls.get("display") == "none", (
        "expected the >=960px .data-cards rule to hide the mobile card list")
    show_table_decls = declarations_for(css_text, ".data-cards ~ .data-table-wrap", at_rules=media)
    assert show_table_decls.get("display") == "block", (
        "expected the >=960px .data-cards ~ .data-table-wrap rule to reveal the desktop table")

    label_decls = declarations_for(css_text, ".data-card__label")
    th_decls = declarations_for(css_text, ".data-table th")
    for prop in ("font-size", "color"):
        assert label_decls.get(prop) == th_decls.get(prop), (
            "expected .data-card__label's %r declaration to be string-equal to .data-table "
            "th's, got %r vs %r" % (prop, label_decls.get(prop), th_decls.get(prop)))

    wrap_decls = declarations_for(css_text, ".data-table-wrap")
    assert "background-attachment" in wrap_decls, (
        "expected .data-table-wrap's scroll-edge shadow to remain intact")

    rules = css_rules(css_text)
    for literal in (".data-table", ".data-table--prose", ".data-table td.desc"):
        assert any(literal in rule.selectors for rule in rules), (
            "expected the harness's own pinned selector %r to still exist" % literal)


def test_registry_mobile_cards_paired_with_the_desktop_table(tmp_path):
    """The registry's mobile .data-cards representation is exactly paired with its table by
    (data-filter-text, data-filter-group), carries concise_timestamp_html()'s own First/Last seen
    markup exactly once each while the desktop table carries the stacked cell built from the same
    two formatters over the same now, positioned between the filter bar and the table wrap, and
    every column (prefix, count, both timestamps, example callsign) is reachable in the card
    slice"""
    state_dir = str(tmp_path)
    now = shp.now()
    now_iso = shp.iso(now)
    prefixes = {
        "ABC": {"count": 12, "first_seen": shp.iso(now - timedelta(days=6)),
                "last_seen": shp.iso(now - timedelta(hours=1)),
                "example_callsign": "ABC123"},
        "XYZ": {"count": 3, "first_seen": shp.iso(now - timedelta(days=4)),
                "last_seen": shp.iso(now - timedelta(hours=5)),
                "example_callsign": "XYZ456"},
        "QRS": {"count": 27, "first_seen": shp.iso(now - timedelta(days=9)),
                "last_seen": shp.iso(now - timedelta(minutes=20)),
                "example_callsign": "QRS789"},
    }
    shp.seed_unresolved_prefixes(state_dir, prefixes)
    rendered = health_page.render(shp.ctx(state_dir, now_iso))

    rows = health_page.unresolved_rows(state_dir)
    expected_count = len(rows)
    assert expected_count == len(prefixes)

    tr_pattern = re.compile(
        r'<tr class="[^"]*" data-filter-text="([^"]*)" data-filter-group="(\d+)">')
    li_pattern = re.compile(
        r'<li class="data-card" data-filter-text="([^"]*)" data-filter-group="(\d+)">')
    tr_matches = tr_pattern.findall(rendered)
    li_matches = li_pattern.findall(rendered)

    assert len(tr_matches) == expected_count
    assert len(li_matches) == expected_count

    tr_pairs = {(text, int(group)) for text, group in tr_matches}
    li_pairs = {(text, int(group)) for text, group in li_matches}
    assert tr_pairs == li_pairs, (
        "expected the <tr> and <li> (filter-text, filter-group) pair sets to be equal")

    distinct_groups = {group for _text, group in tr_matches}
    assert len(distinct_groups) == expected_count
    filter_text_elements = rendered.count("data-filter-text=")
    assert filter_text_elements == 2 * expected_count, (
        "expected exactly twice the row count's worth of data-filter-text elements (2N)")

    filter_bar_at = rendered.index('<div class="filter-bar">')
    cards_at = rendered.index('<ul class="data-cards">', filter_bar_at)
    table_wrap_at = rendered.index('<div class="data-table-wrap">', cards_at)
    assert filter_bar_at < cards_at < table_wrap_at, (
        "expected filter bar, then card list, then table wrap, in that document order")
    cards_end = rendered.index("</ul>", cards_at) + len("</ul>")
    card_slice = rendered[cards_at:cards_end]
    table_wrap_slice = rendered[table_wrap_at:]

    for prefix, count, first_seen, last_seen, example_callsign in rows:
        first_html = layout.concise_timestamp_html(first_seen, now_iso, fallback="")
        last_html = layout.concise_timestamp_html(last_seen, now_iso, fallback="")
        assert rendered.count(first_html) == 1 and first_html in card_slice, (
            "expected First seen markup exactly once, in the card slice")
        assert rendered.count(last_html) == 1 and last_html in card_slice, (
            "expected Last seen markup exactly once, in the card slice")
        for raw_ts in (first_seen, last_seen):
            clock = layout.escape_html(
                layout.local_clock_text(layout.parse_iso(raw_ts), layout.parse_iso(now_iso)))
            age = layout.escape_html(
                layout.relative_age_text(layout.age_seconds(raw_ts, now_iso)))
            expected_cell = (
                '<span class="cell-primary" title="%s">%s</span>'
                '<span class="cell-inline-sep">%s</span>'
                '<span class="cell-secondary">%s</span>'
            ) % (
                layout.escape_html(health_page._full_local_timestamp_text(raw_ts)),
                clock, health_page._REGISTRY_CELL_SEPARATOR_TEXT, age)
            assert expected_cell in table_wrap_slice, (
                "expected the table's cell to be the two stacked lines built from the SAME "
                "formatters concise_timestamp_html() composes")
            assert clock in first_html or clock in last_html, (
                "expected the stacked clock line to be the same text the card's own "
                "concise_timestamp_html() output carries")
        assert layout.escape_html(prefix) in card_slice
        assert str(count) in card_slice
        assert layout.escape_html(example_callsign) in card_slice
        assert first_html in card_slice
        assert last_html in card_slice


def test_registry_table_fits_by_stacked_cells_and_short_french_headers(tmp_path, css_text):
    """The unresolved-prefix table fits by the two levers headless measurement selected — the
    Flights stacked-cell precedent scoped to its own data-table--registry modifier (the base
    no-crop floor kept), plus two shortened French headers with the retired long forms gone and
    the English sources untouched — and never by a 1100px card fallback"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 12, "first_seen": shp.iso(now - timedelta(days=6)),
                "last_seen": shp.iso(now - timedelta(hours=1)),
                "example_callsign": "ABC123"},
    })
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))

    assert '<table class="data-table data-table--registry">' in rendered, (
        "expected the registry table to carry the additive data-table--registry modifier")
    table_at = rendered.index('<div class="data-table-wrap">')
    table_slice = rendered[table_at:]
    assert table_slice.count('<span class="cell-primary" title=') == 2, (
        "expected both timestamp cells to render a stacked primary line")
    assert table_slice.count('<span class="cell-secondary">') == 2, (
        "expected both timestamp cells to render a stacked secondary line")
    assert '<span class="mono" title=' not in table_slice, (
        "expected the one-line concise_timestamp_html() cell to be gone from the table")

    rules = css_rules(css_text)
    for selector in ("table.data-table--registry .cell-primary",
                     "table.data-table--registry .cell-secondary",
                     "table.data-table--registry .cell-inline-sep"):
        assert rules_with_selector(css_text, selector), (
            "expected style.css to carry a rule for %r" % (selector,))
    assert not any(".data-table--registry" in rule.selectors for rule in rules), (
        "expected no bare .data-table--registry rule — this table keeps the base "
        "min-width: max-content no-crop floor, unlike .data-table--prose")
    at_rule_preludes = {at_rule for rule in rules for at_rule in rule.at_rules}
    assert not any("1100px" in at_rule for at_rule in at_rule_preludes), (
        "expected no 1100px card-fallback breakpoint — measurement showed levers 1 and 2 "
        "fit the table in both languages, so lever 3 was not applied")

    assert i18n_fr_health.CATALOG.get("First seen") == "Première fois", (
        "expected the shortened French 'First seen' header")
    assert i18n_fr_health.CATALOG.get("Last seen") == "Dernière fois", (
        "expected the shortened French 'Last seen' header")
    for retired in ("Vu pour la première fois", "Vu pour la dernière fois"):
        assert retired not in i18n_fr_health.CATALOG.values(), (
            "expected the retired long French header %r to be gone" % (retired,))
    assert health_page._REGISTRY_HEADERS[2:4] == ("First seen", "Last seen"), (
        "expected the English header sources to be unchanged")


def test_no_chrome_for_empty_registry_and_no_cross_page_leak(tmp_path):
    """No card chrome renders for an empty registry (filter bar and .data-cards both absent,
    empty_state() present instead); both migrated tables together render exactly two .data-cards
    lists; History and Airlines carry zero occurrences of the new card class names"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty_dir = str(empty_dir)
    now = shp.now()
    rendered_empty = health_page.render(shp.ctx(empty_dir, shp.iso(now)))
    unresolved_at = rendered_empty.index(">%s</h2>" % health_page.UNRESOLVED_SECTION_HEADING)
    assert health_page.STATS_SECTION_HEADING not in rendered_empty, (
        "expected the empty Resolution-statistics section to be entirely absent")
    section_slice = rendered_empty[unresolved_at:]
    assert "data-card" not in section_slice, (
        "expected no .data-cards/.data-card markup in an empty registry's section")
    assert "filter-bar" not in section_slice, (
        "expected no filter bar in an empty registry's section")
    assert health_page._NO_GAPS_HEADING in section_slice, (
        "expected the empty_state() no-gaps heading in an empty registry's section")

    both_dir = tmp_path / "both"
    both_dir.mkdir()
    both_dir = str(both_dir)
    shp.seed_runway_events(both_dir, [
        {"ts": shp.iso(now), "hex": "abc111", "route_source": "fresh_hit"}])
    shp.seed_unresolved_prefixes(both_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    rendered_both = health_page.render(shp.ctx(both_dir, shp.iso(now)))
    cards_list_count = rendered_both.count('<ul class="data-cards">')
    assert cards_list_count == 2, (
        "expected exactly two <ul class=\"data-cards\"> lists (stats + registry) when both "
        "have data, got %d" % cards_list_count)

    leak_dir = tmp_path / "leak"
    leak_dir.mkdir()
    leak_dir = str(leak_dir)
    history_rendered = history_page.render(shp.ctx(leak_dir, shp.iso(now)))
    airlines_rendered = airlines_page.render(shp.ctx(leak_dir, shp.iso(now)))
    for page_name, rendered_page in (
            ("history_page", history_rendered), ("airlines_page", airlines_rendered)):
        assert "data-card" not in rendered_page, (
            "expected zero data-card(s) occurrences in %s's rendered output" % page_name)


# ==========================================================================
# The battery readout's humanised detail and typographic split
# ==========================================================================


def test_humanised_battery_readout_end_to_end(tmp_path, battery_trend_js):
    """The battery readout carries its id, role="status", both value/detail spans and a
    humanised visible detail with the machine-precise ISO only in the tooltip, every chart hit
    target carries data-when, and battery-trend.js's shipped source still reads that attribute,
    both span classes, and the readout's id literal"""
    state_dir = str(tmp_path)
    base = shp.now().replace(hour=12, minute=0, second=0, microsecond=0)
    readings = [
        (shp.iso(base - timedelta(minutes=6)), 4210),
        (shp.iso(base - timedelta(minutes=3)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
    ]
    shp.seed_device_health(state_dir, readings)
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(base)))

    section_start = rendered.index('<section class="%s' % health_page.BATTERY_SECTION_CLASS)
    section_end = rendered.index("</section>", section_start) + len("</section>")
    section_html = rendered[section_start:section_end]

    readout_start = section_html.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
    readout_end = section_html.index("</p>", readout_start) + len("</p>")
    readout_html = section_html[readout_start:readout_end]
    assert 'role="status"' in readout_html
    assert "battery-readout__value" in readout_html
    assert "battery-readout__detail" in readout_html
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", readout_html), (
        "expected zero raw ISO occurrences anywhere in the readout")
    title_match = re.search(r'title="([^"]*)"', readout_html)
    assert title_match is not None, "expected the detail span to carry a title attribute"
    assert re.search(r"^\d{1,2} \w+ \d{2}:\d{2} \(", title_match.group(1)), (
        "expected the title to be a full 'D Mon HH:MM (Nx ago)' local timestamp")
    visible = re.sub(r"<[^>]*>", "", readout_html)
    assert title_match.group(1) in visible, (
        "expected the title to equal the readout's own visible text")

    assert section_html.count("data-when=") == 3, (
        "expected one data-when attribute per chart hit target")

    for token in ("data-when", "battery-readout__value", "battery-readout__detail"):
        assert token in battery_trend_js, "expected battery-trend.js to reference %r" % token
    assert ('getElementById("%s")' % health_page.BATTERY_READOUT_ID) in battery_trend_js, (
        "expected battery-trend.js to still look up the readout by its id literal")


def test_readout_typographic_split_stylesheet_guard(css_text):
    """style.css's .mono reach-through covers both .stat-tile__value and .battery-readout in one
    rule, and .battery-readout__detail carries the Label size, the regular weight and the file's
    existing 70% muted strength"""
    mono_rule = next(
        rule for rule in css_rules(css_text) if ".stat-tile__value .mono" in rule.selectors)
    assert ".battery-readout .mono" in mono_rule.selectors, (
        "expected .battery-readout .mono to join .stat-tile__value .mono's own selector list, "
        "not get a second rule")

    detail_decls = declarations_for(css_text, ".battery-readout__detail")
    assert detail_decls.get("font-size") == "var(--font-label-size)", (
        "expected .battery-readout__detail to set the Label size")
    assert detail_decls.get("font-weight") == "var(--weight-regular)", (
        "expected .battery-readout__detail to set the regular weight")
    assert detail_decls.get("color") == "color-mix(in srgb, var(--color-text) 70%, transparent)", (
        "expected .battery-readout__detail to reuse this file's existing 70% muted strength")


# ==========================================================================
# anomaly_active()/banner agreement, the stat-tile reframe, tile-icon survival
# ==========================================================================


def test_anomaly_active_agrees_with_the_banner_both_directions(tmp_path):
    """anomaly_active() and the anomaly banner's presence agree in both directions, across
    healthy and unhealthy fixtures"""
    now = shp.now()
    fixtures = []

    healthy = tmp_path / "healthy"
    healthy.mkdir()
    healthy = str(healthy)
    shp.seed_device_health(healthy, [(shp.iso(now), 4200)])
    shp.seed_meta(healthy, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    fixtures.append((healthy, shp.iso(now)))

    stale_device = tmp_path / "stale-device"
    stale_device.mkdir()
    stale_device = str(stale_device)
    _, default_device_error_s = health_page.wake.device_staleness_thresholds(None)
    shp.seed_device_health(
        stale_device, [(shp.ago(default_device_error_s + 60), 4000)])
    shp.seed_meta(stale_device, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    fixtures.append((stale_device, shp.iso(now)))

    battery_drop = tmp_path / "battery-drop"
    battery_drop.mkdir()
    battery_drop = str(battery_drop)
    shp.seed_device_health(battery_drop, [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ])
    shp.seed_meta(battery_drop, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    fixtures.append((battery_drop, shp.iso(now)))

    for state_dir, ts in fixtures:
        verdict = health_page.anomaly_active(state_dir, ts)
        rendered = health_page.render(shp.ctx(state_dir, ts))
        banner_present = health_page.ANOMALY_BANNER_TEXT in rendered
        assert verdict == banner_present, (
            "anomaly_active()=%r disagreed with the banner's presence=%r for %r"
            % (verdict, banner_present, state_dir))


def test_section_builder_markup_survives_the_stat_tile_reframe(tmp_path):
    """Battery and corroboration section-builder markup (dot, table, svg) survives the stat-tile
    reframe untouched"""
    state_dir = str(tmp_path)
    base = shp.now()
    readings = [
        (shp.iso(base - timedelta(minutes=2)), 4200),
        (shp.iso(base - timedelta(minutes=1)), 4190),
        (shp.iso(base), 4180),
    ]
    shp.seed_device_health(state_dir, readings)
    shp.seed_runway_events(state_dir, [
        dict(ts=shp.iso(base), hex="abc123", confirmed_state="DEPARTING", corroborated="True")])
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(base)))
    assert "dot--" in rendered, "expected at least one dot-- status class to survive the reframe"
    assert '<table class="data-table data-table--readings">' in rendered, (
        "expected the battery table to survive the reframe")
    assert "<svg" in rendered, "expected the battery sparkline svg to survive the reframe"


def test_health_tile_icons_are_tile_only_and_no_heading_carries_a_glyph(tmp_path):
    """Health's three Health-signal icons are tile-only (device, pipeline, corroboration, all
    whitelisted and tile-tinted) and no Health <h2> — empty or seeded render — carries a glyph
    any more; health_page.ICON_BATTERY is gone from the module namespace"""
    three = (
        health_page.ICON_DEVICE, health_page.ICON_PIPELINE, health_page.ICON_CORROBORATION)
    assert len(set(three)) == 3, "expected the three tile-only Health icon constants to be distinct"
    for icon_id in three:
        assert icon_id in layout.ICON_IDS
    assert not hasattr(health_page, "ICON_BATTERY"), (
        "health_page.ICON_BATTERY must be gone from the module namespace")

    def _headings_carry_no_glyph(rendered, expected_heading_count):
        heads = re.findall(r"<h2\b.*?</h2>", rendered, re.S)
        assert len(heads) == expected_heading_count, (
            "expected Health to render %d headings, got %d" % (expected_heading_count, len(heads)))
        for head in heads:
            assert "<svg" not in head, (
                "no Health heading may carry a glyph any more, found one in: %r" % head[:140])
        assert "#icon-battery" not in rendered, (
            "the retired icon-battery glyph must not be referenced anywhere in the page body")

    state_dir = str(tmp_path)
    empty_rendered = health_page.render(shp.ctx(state_dir))
    assert empty_rendered.count("<use") == 4, (
        "expected exactly four <use occurrences on the empty render (three tile icons plus "
        "the auto-refresh pill icon)")
    for icon_id in three:
        assert empty_rendered.count("#" + icon_id) == 1
    assert empty_rendered.count(layout.STAT_TILE_ICON_CLASS) == 3, (
        "expected exactly three glyphs to carry the tile tint class")
    _headings_carry_no_glyph(empty_rendered, 5)

    now = shp.now()
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    seeded_rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))
    assert seeded_rendered.count("<use") == 5, (
        "expected exactly five <use occurrences on a seeded render (the same four plus "
        "icon-search in the unresolved-prefixes filter bar)")
    _headings_carry_no_glyph(seeded_rendered, 5)


# The auto-refresh-reversal prose-recording check (pinning that the reversal is written down at
# both prose sites it touches) is deleted, not ported. It opened companion/static/freshness.js for
# a quick-task identifier and the house "SUPERSEDED" token, and separately opened a phase context
# document under the planning tree for the same pair beside the original decision's wording — plan
# history prose recorded in a header comment and a planning document, with no rendered or served
# behaviour behind either assertion (TST-12 rubric P/J).


# ==========================================================================
# The auto-refresh pill's markup/stylesheet contracts, the fetch-and-swap
# loop's own contract, and the pipeline tile's second line
# ==========================================================================


def test_freshness_js_carries_the_refresh_loop_contract(freshness_js):
    """freshness.js's shipped source carries the loop's own contract — a named interval constant
    inside the 30-60s band, both halves of pause (setInterval+clearInterval) and visibility
    (visibilitychange+document.hidden), the double-start guard, and the retired reload form gone
    entirely while fetch(/DOMParser/replaceChild/importNode are required present as this file's
    own reviewed exception to the forbidden-sink/no-URL-taking-navigation-form/ES5-safe-subset
    disciplines, which otherwise still hold unchanged"""
    js = freshness_js
    m = re.search(r"AUTO_REFRESH_INTERVAL_MS\s*=\s*(\d+)", js)
    assert m, "expected AUTO_REFRESH_INTERVAL_MS to be a named constant"
    interval_ms = int(m.group(1))
    assert 30000 <= interval_ms <= 60000, (
        "interval %d ms falls outside the developer's chosen 30-60s band" % interval_ms)

    assert "setInterval" in js and "clearInterval" in js, (
        "expected both setInterval and clearInterval — the pause half of the loop")
    assert "visibilitychange" in js and "document.hidden" in js, (
        "expected both a visibilitychange listener and a document.hidden read")
    assert "intervalHandle !== null" in js, (
        "expected the double-start guard (a no-op start when a handle already exists)")
    assert "location.reload" not in js, "expected the retired reload form to be gone entirely"

    for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML",
                 "document.write", "eval(", "XMLHttpRequest"):
        assert sink not in js, "forbidden sink discipline broken: %r found in freshness.js" % sink
    for nav in ("location.href =", "location.assign", "location.replace", "window.open"):
        assert nav not in js, "URL-taking navigation form found in freshness.js: %r" % nav
    for token in ("let ", "const ", "=>", "`"):
        assert token not in js, "ES5-safe subset broken: %r found in freshness.js" % token
    for required in ("setInterval", "fetch(", "DOMParser", "replaceChild", "importNode"):
        assert required in js, "expected %r to be present in freshness.js" % required


def test_auto_refresh_pill_markup_contract_holds_seeded_and_fresh(tmp_path):
    """The auto-refresh pill's markup contract (marker attribute, inline element, hidden-by-
    default, live data-loaded-at exactly once page-wide, the pill-copy constant's own value,
    inside .page-header, preceding the purpose sentence) holds on a real render both seeded and on
    a fresh state directory with no readings at all — proven unconditional, not coupled to the
    battery chart's own render branch"""
    for label, seed_readings in (("seeded", True), ("fresh/no-readings", False)):
        state_dir = tmp_path / ("seeded" if seed_readings else "fresh")
        state_dir.mkdir()
        state_dir = str(state_dir)
        now = shp.now()
        if seed_readings:
            shp.seed_device_health(state_dir, [
                (shp.iso(now - timedelta(minutes=1)), 4200),
                (shp.iso(now), 4190),
            ])
        now_iso = shp.iso(now)
        rendered = health_page.render(shp.ctx(state_dir, now_iso))
        assert rendered.count("data-refresh-pill") == 1, (
            "%s state: expected exactly one pill marker attribute" % label)
        start = rendered.index("data-refresh-pill")
        tag = rendered[rendered.rindex("<", 0, start):rendered.index(">", start) + 1]
        assert tag.startswith("<span"), (
            "%s state: expected the pill to be an inline <span>, got %r" % (label, tag[:40]))
        assert " hidden" in tag, (
            "%s state: expected the pill to carry the bare hidden attribute" % label)
        assert ('data-loaded-at="%s"' % now_iso) in rendered, (
            "%s state: expected data-loaded-at to carry the real now value" % label)
        assert rendered.count("data-loaded-at") == 1, (
            "%s state: expected exactly one data-loaded-at, page-wide" % label)
        assert health_page.REFRESH_PILL_TEXT in rendered, (
            "%s state: expected the pill copy constant's own value in the rendered page" % label)
        header_start = rendered.index('<div class="page-header">')
        header_end = rendered.index("</div>", header_start) + len("</div>")
        assert "data-refresh-pill" in rendered[header_start:header_end], (
            "%s state: expected the pill inside the .page-header div" % label)
        purpose_at = rendered.index(layout.escape_html(health_page.PAGE_PURPOSE_TEXT))
        assert start < purpose_at, (
            "%s state: expected the pill to precede the purpose sentence" % label)


def test_refresh_pill_stylesheet_contract(css_text):
    """style.css's .refresh-pill / .refresh-pill[hidden] / pill-scoped icon rules each carry
    their load-bearing declaration — the [hidden] override hides by visibility with no display
    value at all — .banner__pill still precedes .refresh-pill in source order, and the pill is
    taken out of .page-header's block flow entirely via a .page-header-scoped absolute-position
    rule rather than kept in flow with a reserved line box"""
    pill_decls = declarations_for(css_text, ".refresh-pill")
    assert pill_decls.get("display") == "inline-flex", (
        "expected .refresh-pill to declare an inline-level flex display")

    hidden_decls = declarations_for(css_text, ".refresh-pill[hidden]")
    assert hidden_decls.get("visibility") == "hidden", (
        "expected .refresh-pill[hidden] to hide by visibility — without this override the "
        "pill's own display declaration beats the user-agent [hidden] rule")
    assert "display" not in hidden_decls, (
        "expected .refresh-pill[hidden] to declare no display value at all")

    assert rules_with_selector(css_text, ".refresh-pill .icon"), (
        "expected a pill-scoped icon-size override — .icon is 20px, the pill is 20px tall")

    rules = css_rules(css_text)
    assert _rule_index(rules, ".banner__pill") < _rule_index(rules, ".refresh-pill"), (
        "expected .banner__pill to still precede .refresh-pill in source order")

    header_decls = declarations_for(css_text, ".page-header")
    assert header_decls.get("position") == "relative", (
        "expected .page-header to establish a containing block for the out-of-flow pill")

    scoped_decls = declarations_for(css_text, ".page-header .refresh-pill")
    assert scoped_decls.get("position") == "absolute", (
        "expected .page-header .refresh-pill to be positioned absolutely")
    assert "top" in scoped_decls and "right" in scoped_decls, (
        "expected .page-header .refresh-pill to declare explicit top/right offsets")


def test_pipeline_tile_second_line_renders_last_detection_timestamp(tmp_path):
    """The pipeline tile's new second line renders META_LAST_DETECTION's timestamp byte-
    identically to concise_timestamp_html(), reusing the existing muted text-label/section-caption
    tier — never battery-readout__detail, whose class name would collide with the
    BATTERY_READOUT_ID absence guards"""
    state_dir = str(tmp_path)
    now = shp.now()
    now_iso = shp.iso(now)
    detection_iso = shp.iso(now - timedelta(minutes=5))
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: now_iso,
        history_db.META_LAST_DETECTION: detection_iso,
    })
    rendered = health_page.render(shp.ctx(state_dir, now_iso))
    expected_detail = layout.concise_timestamp_html(detection_iso, now_iso)
    assert rendered.count(expected_detail) == 1, (
        "expected the pipeline tile's second line to render concise_timestamp_html() "
        "byte-identically for the seeded META_LAST_DETECTION value exactly once")
    assert health_page.LAST_DETECTION_LABEL in rendered, (
        "expected the second line's label text in the rendered page")
    assert 'class="stat-tile__meta text-label section-caption"' in rendered, (
        "expected the second line to reuse the existing muted text-label/section-caption tier")
    second_line_slice = rendered.split('<p class="stat-tile__meta')[1].split("</p>")[0]
    assert "battery-readout" not in second_line_slice, (
        "expected the second line's own markup to carry no 'battery-readout' substring")


def test_pipeline_tile_second_line_falls_back_honestly_when_no_detection(tmp_path):
    """The pipeline tile's second line renders its honest no-reading-yet fallback when
    META_LAST_DETECTION is absent, never an empty element or a dangling label"""
    state_dir = str(tmp_path)
    now_iso = shp.iso(shp.now())
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: now_iso})
    rendered = health_page.render(shp.ctx(state_dir, now_iso))
    fallback_html = layout.escape_html("no reading yet")
    second_line_start = rendered.index('<p class="stat-tile__meta text-label section-caption">')
    second_line_end = rendered.index("</p>", second_line_start) + len("</p>")
    second_line = rendered[second_line_start:second_line_end]
    assert fallback_html in second_line, (
        "expected the pipeline tile's second line to render the honest fallback when "
        "META_LAST_DETECTION is absent")
    assert health_page.LAST_DETECTION_LABEL in second_line, (
        "expected the second line's label to still render alongside the fallback")


def test_health_header_renders_the_persistent_freshness_note(tmp_path):
    """Health's header renders an honest 'Updated HH:MM' clock — server-rendered as the text of a
    <time data-relative> element, never the ladder's zero bucket, so the value is true with
    scripts blocked and live with them (no relative-age suffix, the full Europe/Paris local
    timestamp — never the raw ISO — in the clock span's title) beside the unchanged hidden refresh
    pill and NO Pause/Resume toggle (zero data-refresh-toggle/data-pause-text/data-resume-text,
    zero <button>), all inside one block-level .page-header__freshness wrapper that is the
    .page-header's next child right after the <h1>, in prefix/clock/pill source order"""
    state_dir = str(tmp_path)
    now_iso = shp.iso(shp.now())
    rendered = health_page.render(shp.ctx(state_dir, now_iso))

    prefix = layout.escape_html(health_page.FRESHNESS_PREFIX_TEXT)
    assert prefix in rendered, "expected the honest 'Updated ' prefix text in the rendered page"
    assert health_page.FRESHNESS_PREFIX_TEXT == "Updated "

    assert '<p class="page-header__freshness' in rendered, (
        "expected a block-level .page-header__freshness wrapper")
    wrapper_start = rendered.index('<p class="page-header__freshness')
    wrapper_end = rendered.index("</p>", wrapper_start) + len("</p>")
    wrapper_slice = rendered[wrapper_start:wrapper_end]
    assert "data-refresh-pill" in wrapper_slice, (
        "expected the hidden refresh pill inside the freshness wrapper")

    outside = re.sub(r"<time [^>]*data-relative[^>]*>.*?</time>", "", wrapper_slice, flags=re.S)
    assert " ago" not in outside and "il y a" not in outside, (
        "expected every relative age inside .page-header__freshness to be a live "
        "<time data-relative> element")
    assert wrapper_slice.count("data-relative") == 1, (
        "expected exactly one <time data-relative> element inside .page-header__freshness")

    inside = re.search(r"<time [^>]*data-relative[^>]*>(.*?)</time>", wrapper_slice, flags=re.S)
    assert inside is not None, "expected the freshness value to BE a <time data-relative> element"
    for lang in ("en", "fr"):
        assert inside.group(1) != layout.escape_html(layout.relative_age_text(0, lang=lang)), (
            "the server must not render the ladder's zero bucket as this element's own text")
    assert " ago" not in inside.group(1) and "il y a" not in inside.group(1), (
        "the server renders a relative age where the no-JS floor needs a value that stays true")

    assert wrapper_slice.count("data-refresh-clock") == 1, (
        "expected exactly one data-refresh-clock span")
    clock_at = wrapper_slice.index("data-refresh-clock")
    clock_tag = wrapper_slice[
        wrapper_slice.rindex("<", 0, clock_at):wrapper_slice.index(">", clock_at) + 1]
    expected_title = layout.escape_html(health_page._full_local_timestamp_text(now_iso))
    assert ('title="%s"' % expected_title) in clock_tag, (
        "expected the clock span's title to carry the full Europe/Paris local timestamp")
    assert now_iso not in clock_tag, (
        "expected the raw ISO instant NOT to survive verbatim in the clock span's title")

    for needle in ("data-refresh-toggle", "data-pause-text", "data-resume-text"):
        assert needle not in wrapper_slice, (
            "expected zero occurrences of %r inside .page-header__freshness" % needle)
    assert "<button" not in wrapper_slice, "expected no <button> inside .page-header__freshness"

    prefix_at = wrapper_slice.index(prefix)
    assert prefix_at < clock_at < wrapper_slice.index("data-refresh-pill"), (
        "expected prefix, then clock, then pill in that source order")

    header_start = rendered.index('<div class="page-header">')
    header_end = rendered.index("</div>", header_start) + len("</div>")
    assert wrapper_start >= header_start and wrapper_end <= header_end, (
        "expected the freshness wrapper inside the .page-header div")
    header_slice = rendered[header_start:header_end]
    title_end = header_slice.index("</h1>") + len("</h1>")
    between = header_slice[title_end:]
    assert between.startswith('<p class="page-header__freshness'), (
        "expected the freshness wrapper to be .page-header's next block-level child right "
        "after the <h1>")

    pill_at = rendered.index("data-refresh-pill")
    pill_tag = rendered[rendered.rindex("<", 0, pill_at):rendered.index(">", pill_at) + 1]
    assert pill_tag.startswith("<span"), "expected the pill to still be an inline <span>"
    assert " hidden" in pill_tag, "expected the pill to still carry the bare hidden attribute"
    assert ('data-loaded-at="%s"' % now_iso) in rendered, (
        "expected data-loaded-at to still carry the real now value")


# ==========================================================================
# Four one-line UI-regression fixes, two spacing-pair guards, the <summary>
# accent rule
# ==========================================================================


def test_uir_03_07_12_13_one_line_fixes_hold_together(tmp_path, css_text):
    """The four UIR-03/07/12/13 one-line fixes hold together: .banner wraps with a nowrap
    .banner__label rendered on the anomaly banner's lead span, .banner__pill gains min-width: 0
    while keeping flex: none and its source position before .refresh-pill, .airline-card__image
    gains height: auto alongside its surviving aspect-ratio, the .data-table--prose first-column
    nowrap rule exists after the base rule, and the rendered Battery trend heading's sibling
    caption follows immediately with no leading em dash of its own"""
    banner_decls = declarations_for(css_text, ".banner")
    assert banner_decls.get("flex-wrap") == "wrap", "expected .banner to declare flex-wrap: wrap"

    label_decls = declarations_for(css_text, ".banner__label")
    assert label_decls.get("white-space") == "nowrap", (
        "expected .banner__label to declare white-space: nowrap")

    pill_decls = declarations_for(css_text, ".banner__pill")
    assert pill_decls.get("min-width") == "0", "expected .banner__pill to declare min-width: 0"
    assert pill_decls.get("flex") == "none", "expected .banner__pill to still declare flex: none"
    rules = css_rules(css_text)
    assert _rule_index(rules, ".banner__pill") < _rule_index(rules, ".refresh-pill"), (
        "expected .banner__pill to still precede .refresh-pill in source order")

    image_decls = declarations_for(css_text, ".airline-card__image")
    assert image_decls.get("height") == "auto", (
        "expected .airline-card__image to declare height: auto")
    expected_aspect_ratio = "%d / %d" % illustration_normalize.ILLUSTRATION_TARGET_SIZE
    assert image_decls.get("aspect-ratio") == expected_aspect_ratio, (
        "expected .airline-card__image to declare aspect-ratio: %s" % expected_aspect_ratio)

    assert rules_with_selector(css_text, ".data-table--prose th:first-child"), (
        "expected a .data-table--prose th:first-child rule")
    assert (_rule_index(rules, ".data-table--prose")
            < _rule_index(rules, ".data-table--prose th:first-child")), (
        "expected the .data-table--prose :first-child nowrap rule to follow the base rule")
    nowrap_decls = declarations_for(css_text, ".data-table--prose th:first-child")
    assert nowrap_decls.get("white-space") == "nowrap", (
        "expected the .data-table--prose :first-child rule to declare white-space: nowrap")

    banner_dir = tmp_path / "banner"
    banner_dir.mkdir()
    rendered = health_page.render(shp.ctx(str(banner_dir)))
    assert ('class="banner banner--warn"' in rendered
            or 'class="banner banner--anomaly"' in rendered), (
        "expected a fresh empty state dir to render an anomaly banner")
    banner_at = rendered.index('<div class="banner ')
    assert 'class="banner__label"' in rendered[banner_at:], (
        "expected the banner's lead span to carry class=\"banner__label\"")
    label_open = rendered.index('<span class="banner__label">', banner_at)
    label_close = rendered.index("</span>", label_open)
    label_text = rendered[label_open:label_close]
    assert re.search(r">\d+ (warning|error)s?:\Z", label_text), (
        "expected the count-and-noun lead text inside the banner__label span")
    assert rendered.find("<span>", banner_at, label_open) == -1, (
        "expected no bare <span> lead ahead of the banner__label span")

    caption_dir = tmp_path / "caption"
    caption_dir.mkdir()
    rendered2 = health_page.render(shp.ctx(str(caption_dir)))
    heading_marker = '<h2 class="text-heading">%s</h2>' % layout.escape_html(
        _battery_section_heading())
    after_heading = rendered2[rendered2.index(heading_marker) + len(heading_marker):]
    caption_open = '<p class="text-label section-caption">'
    assert after_heading.startswith(caption_open), (
        "expected the battery heading's sibling caption <p> to follow </h2> immediately")
    caption_text_start = after_heading[len(caption_open):]
    assert not caption_text_start.startswith("—") and not caption_text_start.startswith(" —"), (
        "expected the sibling caption to carry no leading em dash of its own")


def test_dashboard_grid_and_battery_trend_section_keep_their_two_role_spacing_split(css_text):
    """The two-role spacing split holds as a pair: .dashboard-grid's margin-bottom equals
    .page-section's own same-section card-to-card value (var(--space-lg)), while
    .battery-trend-section's section-transition margin-bottom stays the larger, untouched
    var(--space-2xl)"""
    grid_mb = declarations_for(css_text, ".dashboard-grid").get("margin-bottom")
    page_section_mb = declarations_for(css_text, ".page-section").get("margin-bottom")
    trend_mb = declarations_for(css_text, ".battery-trend-section").get("margin-bottom")

    assert grid_mb == page_section_mb, (
        "expected .dashboard-grid's margin-bottom (%r) to equal .page-section's own "
        "same-section card-to-card value (%r)" % (grid_mb, page_section_mb))
    assert trend_mb != grid_mb, (
        "expected .battery-trend-section's section-transition margin-bottom (%r) to stay "
        "LARGER than .dashboard-grid's card-to-card margin-bottom (%r)" % (trend_mb, grid_mb))
    assert grid_mb == "var(--space-lg)", (
        "expected .dashboard-grid to use the --space-lg token by name, got %r" % (grid_mb,))
    assert trend_mb == "var(--space-2xl)", (
        "expected .battery-trend-section's margin-bottom to stay var(--space-2xl), got %r"
        % (trend_mb,))


def test_desktop_padding_and_mobile_density_pair_holds_together(css_text):
    """The desktop-padding/mobile-density pair holds together: .page-section, .theme-status and
    .battery-trend-section all still declare padding: var(--space-md) in their own base rules, and
    one shared rule inside the @media (min-width: 960px) block raises all three to padding:
    var(--space-lg)"""
    selectors = (".page-section", ".theme-status", ".battery-trend-section")
    for selector in selectors:
        decls = declarations_for(css_text, selector)
        assert decls.get("padding") == "var(--space-md)", (
            "expected %r's base rule to still declare padding: var(--space-md)" % (selector,))

    media = ("@media (min-width: 960px)",)
    rule = _rule_with_selectors(css_rules(css_text), selectors, at_rules=media)
    assert rule is not None, (
        "expected a single rule covering .page-section, .theme-status and "
        ".battery-trend-section inside the @media (min-width: 960px) block")
    assert dict(rule.declarations).get("padding") == "var(--space-lg)", (
        "expected the shared @media (min-width: 960px) rule to declare padding: var(--space-lg)")


def test_bare_summary_rule_declares_the_accent_colour(css_text):
    """The bare summary rule declares var(--color-accent) — the file's own accent-reservation
    list explaining the broadening lives in the stylesheet's header comment, which carries no
    rendered behaviour of its own and is not asserted here (TST-12 rubric C)"""
    summary_decls = declarations_for(css_text, "summary")
    assert summary_decls.get("color") == "var(--color-accent)", (
        "expected the bare summary rule to declare the accent colour")


# ==========================================================================
# The interaction-skip guard, and the fetch-and-swap loop's cross-file
# contracts (one registry, one page key, three skip rules, the new-row diff)
# ==========================================================================


def test_interaction_skip_guard_cross_file_contract(tmp_path, freshness_js):
    """The interaction-skip guard's cross-file contract: a fixture rich enough to actually render
    a disclosure, a filter input and a chart hit target, and freshness.js's shipped source still
    checks for a focused INPUT/SUMMARY and health_page.SPARKLINE_HIT_CLASS's own literal value but
    no longer checks for an open <details> at all"""
    state_dir = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(state_dir, [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4190),
    ])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 2, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])
    rendered = health_page.render(shp.ctx(state_dir, shp.iso(now)))
    assert "<details" in rendered, "expected at least one <details> disclosure to actually render"
    assert "data-filter-input" in rendered, (
        "expected the registry filter input to actually render")
    assert health_page.SPARKLINE_HIT_CLASS in rendered, (
        "expected the battery chart's hit-target class to actually render")

    js = freshness_js
    assert "details[open]" not in js, (
        "freshness.js must not check for an open <details> disclosure any more")
    for tag_literal in ("INPUT", "SUMMARY"):
        assert tag_literal in js, (
            "freshness.js no longer names %r among the focusable elements it skips on"
            % tag_literal)
    assert health_page.SPARKLINE_HIT_CLASS in js, (
        "freshness.js no longer references SPARKLINE_HIT_CLASS's own literal value")


def test_swap_selectors_pinned_both_directions(freshness_js):
    """Every layout.REFRESH_SWAP_SELECTORS_BY_PAGE entry, on every page key, appears verbatim in
    freshness.js, and freshness.js never carries a .sparkline-hit selector literal, a
    [data-filter-input] reference, or a details[...] selector — the three regions this loop must
    never swap"""
    js = freshness_js
    for page_key, selectors in sorted(layout.REFRESH_SWAP_SELECTORS_BY_PAGE.items()):
        for selector in selectors:
            assert selector in js, (
                "expected layout.REFRESH_SWAP_SELECTORS_BY_PAGE[%r] entry %r verbatim in "
                "freshness.js" % (page_key, selector))
    assert ".sparkline-hit\"" not in js and ".sparkline-hit'" not in js, (
        "freshness.js must never carry a .sparkline-hit selector literal — swapping the "
        "sparkline would leave battery-trend.js permanently dead")
    assert "[data-filter-input]" not in js, (
        "freshness.js must never reference [data-filter-input] — swapping the registry filter "
        "would leave list-filter.js permanently dead")
    assert "details[" not in js, (
        "freshness.js must never carry a details[...] selector literal as a swap target")


def test_swap_registry_has_one_definition_site_and_one_key_set(freshness_js):
    """The swap registry has ONE definition site (health_page.REFRESH_SWAP_SELECTORS resolves
    from layout.REFRESH_SWAP_SELECTORS_BY_PAGE and is that same object, with Health's five regions
    in their existing order) and ONE key set (the script's registry keys equal the Python's, in
    both directions), with every selector appearing exactly once per registry entry in the
    script's comment-stripped code and the registry actually read"""
    registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
    assert hasattr(health_page, "REFRESH_SWAP_SELECTORS"), (
        "expected health_page.REFRESH_SWAP_SELECTORS to survive as a name — every existing "
        "reader and every shipped pin resolves through it")
    assert health_page.REFRESH_SWAP_SELECTORS is registry[layout.REFRESH_PAGE_HEALTH], (
        "expected health_page.REFRESH_SWAP_SELECTORS to BE the registry's Health entry, not a "
        "copy of it — a copy is a second definition site with extra steps")
    assert health_page.REFRESH_SWAP_SELECTORS == (
        ".dashboard-grid",
        "div.banner--anomaly, div.banner--warn",
        "section.banner",
        ".page-header__freshness",
        'a[href="/health"]'), (
        "Health's five regions, in their existing order, are unchanged by the move")

    js = freshness_js
    block = re.search(r"var SWAP_SELECTORS_BY_PAGE = \{(.*?)\n  \};", js, flags=re.S)
    assert block is not None, (
        "expected a single var SWAP_SELECTORS_BY_PAGE = { ... }; registry block in freshness.js")
    js_keys = set(re.findall(r'"([a-z][a-z0-9-]*)":', block.group(1)))
    py_keys = set(registry)
    assert js_keys == py_keys, (
        "freshness.js's registry keys and layout.REFRESH_SWAP_SELECTORS_BY_PAGE's are not the "
        "same set — only in Python: %r; only in the script: %r"
        % (sorted(py_keys - js_keys), sorted(js_keys - py_keys)))

    code = shp.strip_js_line_and_block_comments(js)
    expected_hits = {}
    for selectors in registry.values():
        for selector in selectors:
            expected_hits[selector] = expected_hits.get(selector, 0) + 1
    for selector, want in sorted(expected_hits.items()):
        got = code.count(selector)
        assert got == want, (
            "the selector %r appears %d time(s) in freshness.js's own code (comments "
            "stripped), expected %d" % (selector, got, want))
    assert code.count("SWAP_SELECTORS_BY_PAGE") >= 2, (
        "SWAP_SELECTORS_BY_PAGE is declared in freshness.js but never read")


def test_page_key_is_server_rendered_and_gates_the_loop(freshness_js):
    """The swap registry is selected by a page key the SERVER renders on <body> — present for
    every registry key and for a page with no entry at all — and freshness.js reads that
    attribute and resolves it with an own-property test, so an unknown key is a no-op rather than
    an inherited Object property"""
    code = shp.strip_js_line_and_block_comments(freshness_js)
    assert layout.REFRESH_PAGE_ATTR in code, (
        "freshness.js never reads the page key attribute — the page key is how one loop "
        "serves three pages")
    assert "hasOwnProperty" in code, (
        "expected freshness.js to resolve the page key with an own-property test")

    for page_key in sorted(layout.REFRESH_SWAP_SELECTORS_BY_PAGE):
        doc = layout.page_shell(title="T", active=page_key, body="<p>b</p>")
        marker = '%s="%s"' % (layout.REFRESH_PAGE_ATTR, page_key)
        body_at = doc.index("<body")
        body_tag = doc[body_at:doc.index(">", body_at) + 1]
        assert marker in body_tag, (
            "expected the page key on the <body> tag itself (never inside a swap target)")

    no_entry_key = layout.nav_slug(layout.AIRLINES_ROUTE)
    assert no_entry_key not in layout.REFRESH_SWAP_SELECTORS_BY_PAGE, (
        "this clause needs a page that declares NO swap regions")
    doc = layout.page_shell(title="T", active=no_entry_key, body="<p>b</p>")
    assert ('%s="%s"' % (layout.REFRESH_PAGE_ATTR, no_entry_key)) in doc, (
        "expected every authenticated document to carry its own page key, including pages "
        "that declare no swap regions")


def test_freshness_loop_knows_three_things_it_must_not_repaint(freshness_js):
    """freshness.js knows three things it must not repaint: swapNodes() keeps its unchanged-
    region and focused-region skips and gains a per-region pending skip, and tick() stands the
    whole cycle down while dirty-state.js's own window.SkyPaneDirtyState.hasUncommittedEdits()
    reports unsaved edits — with the interval, ladder, ceiling, in-flight guard and
    redirect:manual all untouched"""
    js = freshness_js
    code = shp.strip_js_line_and_block_comments(js)
    swap_at = code.index("function swapNodes(")
    swap_body = code[swap_at:code.index("\n  }", swap_at)]
    assert "isEqualNode" in swap_body and "contains" in swap_body, (
        "expected the unchanged-region and focused-region skips to survive untouched")

    assert ('var PENDING_ATTR = "%s";' % layout.REFRESH_PENDING_ATTR) in code, (
        "expected freshness.js to name layout.REFRESH_PENDING_ATTR in its own constant")
    assert "PENDING_ATTR" in swap_body or "PENDING_SELECTOR" in swap_body, (
        "expected swapNodes() to skip a region marked pending")

    tick_at = code.index("function tick(")
    tick_body = code[tick_at:code.index("\n  }", tick_at)]
    assert "unsavedEdits" in tick_body or "UnsavedEdits" in tick_body, (
        "expected tick() itself to stand the whole cycle down while the settings form has "
        "unsaved edits")
    assert "PENDING_ATTR" not in tick_body and "PENDING_SELECTOR" not in tick_body, (
        "the pending skip is PER REGION, not per tick")

    assert "SkyPaneDirtyState" in code, (
        "expected the dirty-form gate to read window.SkyPaneDirtyState")
    edits_at = code.index("function unsavedEdits(")
    edits_body = code[edits_at:code.index("\n  }", edits_at)]
    assert "hasUncommittedEdits" in edits_body, (
        "expected the gate itself to call SkyPaneDirtyState.hasUncommittedEdits()")

    for needle in ("AUTO_REFRESH_INTERVAL_MS = 45000", "RETRY_CEILING_MS = 600000",
                   "RETRY_BASE_MS", "inFlight", "failAndRetry()", "isEqualNode",
                   'redirect: "manual"'):
        assert needle in js, "expected %r to survive untouched" % (needle,)


def test_flights_swap_registry_entry_covers_and_excludes_the_right_regions():
    """Flights' swap registry entry covers the phone card list, the desktop table, the live count
    and the freshness line, EXCLUDES every element list-filter.js captures once at load (the
    input, Clear, the empty state and the set hooks), nests no entry inside another, and is keyed
    by nav_slug()'s own value"""
    registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
    assert layout.REFRESH_PAGE_FLIGHTS in registry, (
        "expected Flights to declare its own swap regions")
    flights = registry[layout.REFRESH_PAGE_FLIGHTS]
    assert layout.REFRESH_PAGE_FLIGHTS == layout.nav_slug(layout.FLIGHTS_ROUTE), (
        "expected the Flights key to be nav_slug()'s own value, never a second vocabulary")
    for needle in ("history-cards", "data-table-wrap", "data-filter-count"):
        assert any(needle in selector for selector in flights), (
            "expected Flights' swap regions to cover %r" % (needle,))
    assert ".page-header__freshness" in flights, (
        "expected Flights' freshness line to be a swap target, like Home's and Health's")
    for forbidden in ("data-filter-input", "data-filter-clear", "data-filter-empty",
                      "data-filter-set"):
        for selector in flights:
            assert forbidden not in selector, (
                "Flights' swap regions name %r (%r) — list-filter.js captures that element "
                "once at load, so replacing it leaves the filter permanently dead"
                % (forbidden, selector))
    for outer in flights:
        for inner in flights:
            assert outer is inner or not inner.startswith(outer + " "), (
                "Flights' regions %r and %r are nested — a swap can detach a node another "
                "entry is about to replace" % (outer, inner))


def test_freshness_new_row_highlight_is_a_diff_never_a_first_paint(freshness_js):
    """freshness.js's new-row highlight is a DIFF over server-rendered row identity: its two
    cross-file literals equal layout.REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS, the known set is
    populated from the page as first rendered rather than empty, the diff runs from applySwap()
    and from nowhere else, resolves the set with an own-property test, applies one class through
    classList and never removes it, and writes no markup"""
    code = shp.strip_js_line_and_block_comments(freshness_js)
    for name, value in (("ROW_ID_ATTR", layout.REFRESH_ROW_ID_ATTR),
                        ("NEW_ROW_CLASS", layout.REFRESH_NEW_ROW_CLASS)):
        assert ('var %s = "%s";' % (name, value)) in code, (
            "expected freshness.js to name layout.REFRESH_%s in its own constant" % name)
    assert "function markNewRows(" in code, (
        "expected freshness.js to carry the new-row diff as its own function")
    assert code.count("markNewRows(") == 2, (
        "expected exactly one definition and one call of markNewRows() — the diff belongs to "
        "the swap and to nothing else")
    apply_at = code.index("function applySwap(")
    apply_body = code[apply_at:code.index("\n  }", apply_at)]
    assert "markNewRows(" in apply_body, (
        "expected applySwap() to run the diff AFTER the regions are replaced")
    init_at = code.index("var knownRowIds")
    init_line = code[init_at:code.index("\n", init_at)]
    assert "collectRowIds()" in init_line, (
        "expected the known-identity set to be populated from the page as first rendered")
    mark_at = code.index("function markNewRows(")
    mark_body = code[mark_at:code.index("\n  }", mark_at)]
    assert "hasOwnProperty" in mark_body, (
        "expected the diff to test the known set with an own-property test")
    assert "classList.add" in mark_body, (
        "expected the highlight to be applied as a class on an existing node")
    assert not ("NEW_ROW_CLASS" in code and "classList.remove(NEW_ROW_CLASS" in code), (
        "expected nothing to remove the highlight class")
    for sink in ("innerHTML", "insertAdjacentHTML", "document.write", "outerHTML"):
        assert sink not in mark_body, (
            "expected the diff to use no markup-writing DOM sink, found %r" % (sink,))
