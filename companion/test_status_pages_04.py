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

from companion import i18n, layout
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
