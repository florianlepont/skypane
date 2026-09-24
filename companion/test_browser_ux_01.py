#!/usr/bin/env python3
"""Part 01 of `companion/test_browser_ux.py` (33-21-PLAN.md, TST-11), the
first of the browser_ux chain's four migration plans (33-21..33-24).

Covers the original file's check() calls #1-#18 (the self-referential
coverage-gap ledger guard, deleted with an `R` reason, plus the
Flights detail-row toggle, three `.filter-bar__meta` siblings (Flights/
Airlines/Health), the Airlines two-per-row grid, Health's registry table
and no-JS floor, the settings pages' reveal/persist/leave-guard family,
the Frame strip switch, and the three runway cards / theme-chip selection
signal). Every test below drives a real headless Chromium against a real
`companion/app.py` subprocess, through the guarded `page`/`new_context`
fixtures (`companion/conftest.py`), and never constructs or navigates to
any URL outside `server.base_url()` — a `127.0.0.1:<ephemeral-port>`
origin the guarded fixture itself created. A missing/unlaunchable
Chromium is a hard failure under CI / `SKYPANE_REQUIRE_BROWSER=1` (the
`browser` fixture override in `companion/conftest.py`), never a silent
skip.

Read-only checks (no test below POSTs a settings save; the ones that
commit a field but only ever click Annuler leave nothing on disk) share
one module-scoped, read-only `server` fixture (33-MIGRATION-RULES.md
section 2). The four checks that DO persist a real setting through the
UI — the two settings-page reveal/persist checks, the bar's own
hide-on-load/reveal-on-edit/save check, and the Frame strip switch check
— each get their own function-scoped `make_app_server` server, so no
xdist worker ever sees another test's leftover on-disk state.
"""
import pytest

from companion import auth
from server import device_config
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _bar_text, _click_control, _commit_field,
    _guard_armed, _login, _no_js_page, _save_via_bar, _set_ui_theme,
    _wait_for_bar, _wait_for_bar_hidden, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only 22-AUDIT.md-methodology fixture (36 runway
    events, ~40 days of battery history, 3 gallery renders, 2 unresolved
    prefixes, 1 manual resolution, 2 colour rules, wake_interval_s 300,
    quiet hours 23:00-07:00) every read-only check in this module measures
    against — module-scoped because none of them POSTs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# ===========================================================================
# 22-09-PLAN.md Task 1 (X5/T-22-32): the Flights detail row's icon-only
# toggle.
# ===========================================================================

def test_flights_detail_row_expands_and_collapses(page, server):
    """a Flights detail row expands and collapses from an icon-only toggle with no visible
    text, a >=44x44 synthesized hit area and an accessible name that swaps with the
    state, flipping aria-expanded and toggling the row aria-controls resolves to; and a
    click on a non-interactive cell of the same row expands it, while a click on the
    toggle itself toggles exactly once (22-09-PLAN.md Task 1, X5/T-22-32)"""
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    toggle = page.locator("[data-row-toggle]").first
    toggle.wait_for(state="visible")
    if toggle.get_attribute("aria-expanded") != "false":
        raise AssertionError(
            "expected the first row-toggle to start collapsed (aria-expanded=false)")
    controls_id = toggle.get_attribute("aria-controls")
    if not controls_id:
        raise AssertionError("expected the row-toggle to carry aria-controls")
    detail_row = page.locator("#" + controls_id)
    if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
        raise AssertionError("expected the detail row to start collapsed")

    # Icon-only: no visible text, a real accessible name.
    label_text = toggle.inner_text().strip()
    if any(ch.isalnum() for ch in label_text):
        # The decorative chevron glyph is the icon, not a label; any
        # alphanumeric character here would be a visible text label.
        raise AssertionError(
            "expected the toggle to render no visible text label, got %r"
            % (label_text,))
    collapsed_name = toggle.get_attribute("aria-label")
    if not collapsed_name:
        raise AssertionError("expected the icon-only toggle to carry an aria-label")

    # The real hit area: a 22x22 visual box plus the ::before's negative
    # 11px inset on every side.
    hit = toggle.evaluate(
        "el => { var r = el.getBoundingClientRect();"
        " var s = getComputedStyle(el, '::before');"
        " return [r.width - parseFloat(s.left) - parseFloat(s.right),"
        " r.height - parseFloat(s.top) - parseFloat(s.bottom)]; }")
    if not hit or hit[0] < 44 or hit[1] < 44:
        raise AssertionError(
            "expected the toggle's hit area to measure at least 44x44 in "
            "both axes, measured %r" % (hit,))

    toggle.click()
    if toggle.get_attribute("aria-expanded") != "true":
        raise AssertionError("expected aria-expanded to flip to true after a click")
    if "flight-detail-row--collapsed" in (detail_row.get_attribute("class") or ""):
        raise AssertionError(
            "expected the detail row's collapsed class to be removed after expanding")
    expanded_name = toggle.get_attribute("aria-label")
    if expanded_name == collapsed_name:
        raise AssertionError(
            "expected the accessible name to change with the state, it stayed %r"
            % (collapsed_name,))
    # A click ON the toggle must toggle exactly ONCE: the row's own
    # delegated handler returns early for an interactive target, so an
    # unguarded handler would double-toggle back to collapsed.
    if not expanded_name:
        raise AssertionError("expected an aria-label in the expanded state too")

    toggle.click()
    if toggle.get_attribute("aria-expanded") != "false":
        raise AssertionError(
            "expected aria-expanded to flip back to false after a second click")
    if "flight-detail-row--collapsed" not in (detail_row.get_attribute("class") or ""):
        raise AssertionError(
            "expected the detail row's collapsed class to return after collapsing")
    if toggle.get_attribute("aria-label") != collapsed_name:
        raise AssertionError("expected the collapsed accessible name to return")

    # The whole row is clickable: a click on a plain, non-interactive cell
    # expands the same row.
    row = page.locator("[data-flight-row]").first
    if "flight-row--clickable" not in (row.get_attribute("class") or ""):
        raise AssertionError(
            "expected flight-rows.js to add its own clickable marker class "
            "to each summary row at load")
    row.locator("td").nth(2).click()
    if toggle.get_attribute("aria-expanded") != "true":
        raise AssertionError("expected a click on a non-interactive cell to expand the row")


# ===========================================================================
# 27-08-PLAN.md Task 2 (CFG-69): the Quiet hours caption link's own hit
# target — it sits in a dense strip cell beside a switch, the exact
# geometry that already produced this file's 30x45 pager and 43x43
# handle. Measured on Home (the strip is one shared component, D-23; the
# status-pages check proves it is the SAME markup on Display), at the
# 360px floor, in both themes.
# ===========================================================================

def test_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px(new_context, server):
    """the Quiet hours caption's schedule link clears the 44px hit-target floor by
    real hit-testing in its own frame-strip cell, in both themes, at the 360px
    floor, on both Home and Display, with neither page gaining horizontal scroll
    from the addition (CFG-69, 27-08-PLAN.md Task 2)"""
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        recorded = {}
        for route in ("/", "/display"):
            page.goto(server.base_url() + route)
            overflow = page.evaluate(
                "document.documentElement.scrollWidth > "
                "document.documentElement.clientWidth")
            if overflow:
                raise AssertionError(
                    "%s: expected no horizontal page scroll at 360px with the "
                    "schedule link in the strip — the link is a FLOOR addition, "
                    "not one that pushes the strip past the viewport" % (route,))
        page.goto(server.base_url() + "/")
        for theme in ("light", "dark"):
            _set_ui_theme(page, theme)
            seen = _assert_hit_target(
                page, "a.frame-strip__schedule-link",
                "the Quiet hours caption's schedule link, in its own frame-strip "
                "cell, %s theme" % theme)
            recorded[theme] = (seen["visual"], seen["hit"])
        if recorded["light"][1][0] < 44 or recorded["light"][1][1] < 44:
            raise AssertionError(
                "expected the light-theme hit area to clear 44px, got %r" % (
                    recorded["light"][1],))
        if recorded["dark"][1][0] < 44 or recorded["dark"][1][1] < 44:
            raise AssertionError(
                "expected the dark-theme hit area to clear 44px, got %r" % (
                    recorded["dark"][1],))
    finally:
        context.close()


# ===========================================================================
# 27-08-PLAN.md Task 3 (CFG-70): `.copy-btn` (a Flights detail row) and
# `.row-toggle` (the Flights list's own toggle) — measured in THEIR OWN
# containers, never a declared-vs-resolved assumption. `.row-toggle`
# reuses `.copy-btn`'s values verbatim (style.css's own comment), so both
# are measured here as ONE check about the family, not two independent
# ones — the shape that let a declared 44 ship beside a resolved 34x26 in
# the first place.
#
# `.row-toggle` and the desktop `.copy-btn` trio only exist in
# `.data-table-wrap`, which this app's own responsive rule hides below
# 960px in favour of `.history-cards` — there is no 360px rendering of
# either to measure, so they are measured at the narrowest width they
# actually occupy (960px) instead, in both themes. The mobile `.copy-btn`
# trio (inside each `.history-card`'s own `<details>`) DOES render at
# 360px and is measured there, in both themes, closing the literal 360px
# case for this family too.
# ===========================================================================

def test_copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_containers(new_context, server):
    """every icon control in the .copy-btn/.row-toggle family resolves to the 44px
    hit-target floor in its OWN container, by real hit-testing rather than a
    declared value: .row-toggle and the desktop Flights detail row's three
    .copy-btn (hex/timestamp/callsign, each hovered/focused to clear the
    opacity-at-rest reveal) at 960px, and the mobile <details> card's own three
    .copy-btn at the 360px floor — both in both themes, ONE check for the whole
    family sharing .copy-btn's values (CFG-70, 27-08-PLAN.md Task 3)"""
    recorded = {}

    def _measure_desktop(page):
        toggle = page.locator("[data-row-toggle]").first
        toggle.wait_for(state="visible")
        controls_id = toggle.get_attribute("aria-controls")
        if toggle.get_attribute("aria-expanded") != "true":
            toggle.click()
        page.wait_for_timeout(50)
        detail_sel = "#" + controls_id
        page.locator(detail_sel).hover()
        seen = _assert_hit_target(
            page, "[data-row-toggle]",
            "the Flights list's own row-toggle, in ITS OWN container (the "
            "summary row, not the detail row's grid)")
        recorded["row-toggle/desktop"] = (seen["visual"], seen["hit"])
        for label, value in (
                ("hex", "399023"), ("timestamp", "2026-08-01T22:31:40+00:00"),
                ("callsign", "AFR135")):
            sel = '%s [data-copy-value="%s"]' % (detail_sel, value)
            page.locator(sel).focus()
            seen = _assert_hit_target(
                page, sel,
                "the %s .copy-btn, in ITS OWN container (the Flights detail "
                "row's grid, hovered/focused so its opacity/pointer-events "
                "reveal fires)" % (label,))
            recorded["copy-btn/desktop/%s" % label] = (seen["visual"], seen["hit"])

    def _measure_mobile(page):
        card = page.locator(".history-card").first
        card.wait_for(state="visible")
        card.locator("summary").first.click()
        for label, value in (
                ("hex", "399023"), ("timestamp", "2026-08-01T22:31:40+00:00"),
                ("callsign", "AFR135")):
            sel = '.history-card [data-copy-value="%s"]' % (value,)
            seen = _assert_hit_target(
                page, sel,
                "the mobile %s .copy-btn, in ITS OWN container (the "
                "<details> card, not the desktop grid)" % (label,))
            recorded["copy-btn/mobile/%s" % label] = (seen["visual"], seen["hit"])

    context_desktop = new_context(viewport={"width": 960, "height": 900})
    try:
        page = context_desktop.new_page()
        _login(page, server.base_url())
        for theme in ("light", "dark"):
            page.goto(server.base_url() + "/flights")
            _set_ui_theme(page, theme)
            _measure_desktop(page)
    finally:
        context_desktop.close()

    context_mobile = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context_mobile.new_page()
        _login(page, server.base_url())
        for theme in ("light", "dark"):
            page.goto(server.base_url() + "/flights")
            _set_ui_theme(page, theme)
            _measure_mobile(page)
    finally:
        context_mobile.close()

    for key, (visual, hit) in recorded.items():
        if hit[0] < 44 or hit[1] < 44:
            raise AssertionError(
                "%s: expected a resolved hit area >=44x44, got %r (visual box "
                "%r) — a declared 44 is not a resolved 44"
                % (key, hit, visual))


def test_flights_filter_count_and_clear_share_one_line_at_390px(new_context, server):
    """at 390px on Flights the filter count and the Clear control report the same
    bounding-box top — Clear never drops alone onto its own line (B11,
    22-09-PLAN.md Task 3, a regression of Phase 18's A-18)"""
    # B11 (22-09-PLAN.md Task 3): Phase 18's A-18 REGRESSING A SECOND TIME
    # — at 390px "Clear" dropped alone onto its own line under the filter
    # bar. Two `nowrap` siblings in a wrapping flex container do not wrap
    # as a unit; one `.filter-bar__meta` group does. Measured, not
    # inspected: equal getBoundingClientRect().top is the contract, and
    # this assertion fails if it ever reopens a third time.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        count = page.locator("[data-filter-count]").first
        clear = page.locator("[data-filter-clear]").first
        count.wait_for(state="visible")
        clear.wait_for(state="visible")
        count_box = count.bounding_box()
        clear_box = clear.bounding_box()
        if count_box is None or clear_box is None:
            raise AssertionError("expected both the count and Clear to have a box at 390px")
        if round(count_box["y"]) != round(clear_box["y"]):
            raise AssertionError(
                "expected the filter count and Clear to report the same top at "
                "390px (A-18 regressing a second time), got %r and %r"
                % (count_box["y"], clear_box["y"]))
        if page.viewport_size["width"] != 390:
            raise AssertionError("expected the measurement to be taken at 390px")
    finally:
        context.close()


def test_airlines_grid_renders_two_cards_per_row_at_390px(new_context, server):
    """at 390px every Airlines illustration grid renders exactly two cards per row
    (never the one-per-row auto-fill collapse that made the page 5800px tall),
    with each row's two columns equal within 1px, the main grid's cards near the
    159px the contract predicts, and the whole page under 3800px (X7,
    22-11-PLAN.md Task 2, ceiling recalibrated by quick task 260921-v9c for the
    27->36 airline count)"""
    # X7 (22-11-PLAN.md Task 2): the audit measured a 5800px Airlines page
    # at 390px because `repeat(auto-fill, minmax(200px, 1fr))` collapses
    # to ONE column inside a 342px content column. Only a real layout
    # engine resolves auto-fill, so this is measured rather than asserted
    # off the stylesheet.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        # The gap strip carries its own narrower `.illustration-grid
        # illustration-grid--gap`, so each grid is measured on its own
        # rather than pooling two grids' rows into one histogram.
        curated = ".illustration-grid:not(.illustration-grid--gap)"
        page.locator(curated + " .airline-card").first.wait_for(state="visible")
        grids = page.eval_on_selector_all(
            ".illustration-grid",
            "els => els.map(el => Array.from("
            "  el.querySelectorAll('.airline-card')).map(card => {"
            "    const r = card.getBoundingClientRect();"
            "    return {top: Math.round(r.y), width: r.width};"
            "}))")
        if len(grids) < 1:
            raise AssertionError("expected at least one illustration grid on Airlines")
        widest_row = None
        for grid_index, cards in enumerate(grids):
            if not cards:
                raise AssertionError("expected grid %d to hold cards" % (grid_index,))
            rows = {}
            for card in cards:
                rows.setdefault(card["top"], []).append(card)
            ordered = [rows[top] for top in sorted(rows)]
            for index, row in enumerate(ordered):
                # Every row but a grid's last holds exactly two; the last
                # may hold one when that grid's card count is odd.
                if len(row) > 2 or (index < len(ordered) - 1 and len(row) != 2):
                    raise AssertionError(
                        "expected exactly two cards per row at 390px, grid %d row "
                        "%d held %d" % (grid_index, index, len(row)))
                if len(row) == 2 and abs(row[0]["width"] - row[1]["width"]) > 1:
                    raise AssertionError(
                        "expected the two columns to be equal within 1px, got %r "
                        "and %r" % (row[0]["width"], row[1]["width"]))
                if len(row) == 2 and (
                        widest_row is None
                        or row[0]["width"] > widest_row[0]["width"]):
                    widest_row = row
        if widest_row is None:
            raise AssertionError(
                "expected at least one full two-card row to measure at 390px")
        # 22-UI-SPEC.md §2's own arithmetic for the page's main content
        # column: (342 - 24) / 2.
        if not (150 <= widest_row[0]["width"] <= 170):
            raise AssertionError(
                "expected each card near the 159px the contract predicts, got %r"
                % (widest_row[0]["width"],))
        # X7's second half: the 5800px collapsed page roughly halves under
        # a working two-per-row grid. Originally pinned at 3200px against
        # a measured 2594px baseline for the 27 airlines on the grid when
        # 22-11 shipped this check (22-11-SUMMARY.md). Recalibrated here
        # (quick task 260921-v9c) after nine more illustrated carriers
        # (27->36 airlines) legitimately grew the grid: CI measured
        # 3318px for the new, correctly-laid-out two-per-row page, so the
        # ceiling moves to 3800px — comparable proportional headroom to
        # the original (roughly +15% over the freshly measured baseline,
        # vs the original's +23%), while staying nowhere near the ~2x a
        # real one-per-row collapse would produce (~6600px on today's
        # card count). Measured, with headroom, so this fails on a
        # regression rather than on a pixel — and moves again,
        # deliberately, the next time the airline count legitimately
        # changes.
        height = page.evaluate("document.documentElement.scrollHeight")
        if height > 3800:
            raise AssertionError(
                "expected the two-per-row grid to roughly halve the audit's 5800px "
                "page, measured %r" % (height,))
        if page.viewport_size["width"] != 390:
            raise AssertionError("expected the measurement to be taken at 390px")
    finally:
        context.close()


def test_airlines_filter_count_and_clear_share_one_line_at_390px(new_context, server):
    """at 390px on Airlines the filter count and the Clear control report the same
    bounding-box top, both inside the one shared .filter-bar__meta group plan
    22-09 introduced — adopted verbatim, no per-page variant (B11, 22-11-PLAN.md
    Task 3, the second of the three filtered pages)"""
    # B11 (22-11-PLAN.md Task 3): the SECOND of the three filtered pages.
    # Same defect, same shared `.filter-bar__meta` group plan 22-09 added
    # — adopted verbatim, never forked into a per-page variant, which is
    # how Phase 18's A-18 came back the first time. Measured, like its
    # Flights sibling: equal getBoundingClientRect().top is the contract.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        count = page.locator("[data-filter-count]").first
        clear = page.locator("[data-filter-clear]").first
        count.wait_for(state="visible")
        clear.wait_for(state="visible")
        count_box = count.bounding_box()
        clear_box = clear.bounding_box()
        if count_box is None or clear_box is None:
            raise AssertionError("expected both the count and Clear to have a box at 390px")
        if round(count_box["y"]) != round(clear_box["y"]):
            raise AssertionError(
                "expected the Airlines filter count and Clear to report the same "
                "top at 390px (A-18 regressing), got %r and %r"
                % (count_box["y"], clear_box["y"]))
        # Adopted, not forked: the pair is inside the one shared group
        # element, and Airlines adds no variant of its own.
        in_group = page.eval_on_selector_all(
            ".filter-bar__meta",
            "els => els.map(el => [!!el.querySelector('[data-filter-count]'),"
            " !!el.querySelector('[data-filter-clear]')])")
        if in_group != [[True, True]]:
            raise AssertionError(
                "expected exactly one .filter-bar__meta group on Airlines holding "
                "both controls, got %r" % (in_group,))
        if page.viewport_size["width"] != 390:
            raise AssertionError("expected the measurement to be taken at 390px")
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_health_registry_table_fits_1280px(new_context, server, lang):
    """at 1280px in BOTH languages Health's unresolved-prefix table reports
    scrollWidth === clientWidth on its .data-table-wrap, the Resolve column sits
    inside that wrap's own box (reachable with no horizontal scrolling) and no
    header is clipped — the French table measured 1026px against an 830px wrap
    before the stacked cells and the shortened headers (B12, 22-12-PLAN.md Task 2)"""
    # B12 (22-12-PLAN.md Task 2): the audit measured the unresolved-prefix
    # table overflowing a 1280px desktop in French — "EXEMPLE D'INDIC"
    # clipped, and the Resolve column only reachable by scrolling a
    # container whose one affordance is a 12px shadow. The lever choice
    # was made BY THIS MEASUREMENT, not by eye (the same discipline that
    # settled the Flights table): only a real layout engine resolves
    # `.data-table`'s `min-width: max-content` floor against six columns
    # of real content in two languages.
    #
    # Measured here at every step, wrap clientWidth 830px:
    #   before          EN  886   FR 1026
    #   stacked cells   EN  830   FR  900
    #   + short FR hdrs EN  830   FR  830
    #
    # Each language is fully independent (no cross-language comparison in
    # this check), so the two are parametrized rather than looped.
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        page.goto(base_url + "/health")
        page.locator("table.data-table--registry").first.wait_for(state="visible")
        box = page.eval_on_selector(
            "table.data-table--registry",
            "table => {"
            "  const wrap = table.closest('.data-table-wrap');"
            "  const heads = Array.from(table.querySelectorAll('th'));"
            "  const resolve = heads[heads.length - 1];"
            "  const cells = Array.from("
            "    table.querySelectorAll('tbody tr'))"
            "    .map(tr => tr.children[tr.children.length - 1]);"
            "  return {"
            "    sw: wrap.scrollWidth, cw: wrap.clientWidth,"
            "    wrapRight: wrap.getBoundingClientRect().right,"
            "    resolveRight: Math.max(resolve.getBoundingClientRect().right,"
            "      ...cells.map(td => td.getBoundingClientRect().right)),"
            "    headClipped: heads.filter("
            "      h => h.scrollWidth > h.clientWidth + 1).map(h => h.textContent),"
            "    rowCount: table.querySelectorAll('tbody tr').length,"
            "  };"
            "}")
        if box["rowCount"] < 1:
            raise AssertionError(
                "expected the seeded registry to render at least one row (%s)"
                % (lang,))
        if box["sw"] != box["cw"]:
            raise AssertionError(
                "expected .data-table-wrap scrollWidth === clientWidth at "
                "1280px in %s, got %r vs %r (B12)"
                % (lang, box["sw"], box["cw"]))
        # "Reachable without horizontal scrolling" is the audit's own
        # wording — asserted as a geometric fact, not inferred from the
        # scrollWidth equality above.
        if box["resolveRight"] > box["wrapRight"] + 1:
            raise AssertionError(
                "expected the Resolve column to sit inside the wrap's own box "
                "at 1280px in %s, got right edge %r vs %r"
                % (lang, box["resolveRight"], box["wrapRight"]))
        if box["headClipped"]:
            raise AssertionError(
                "expected no clipped header at 1280px in %s, got %r"
                % (lang, box["headClipped"]))
        if page.viewport_size["width"] != 1280:
            raise AssertionError("expected the measurement to be taken at 1280px")
    finally:
        context.close()


def test_health_filter_count_and_clear_share_one_line_at_390px(new_context, server):
    """at 390px on Health the filter count and the Clear control report the same
    bounding-box top, both inside the one shared .filter-bar__meta group — the
    third and last of the three filtered pages — and the page header's Updated
    clock carries .time-value, never .mono (B11/C5, 22-12-PLAN.md Task 3)"""
    # B11 (22-12-PLAN.md Task 3): the THIRD and last of the three filtered
    # pages. Same defect, same shared `.filter-bar__meta` group plan
    # 22-09 added and plan 22-11 adopted — taken verbatim again, never
    # forked into a per-page variant, which is how Phase 18's A-18 came
    # back the first time. Measured, like both its siblings: equal
    # getBoundingClientRect().top is the contract, so a third regression
    # fails here instead of being noticed by eye.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/health")
        count = page.locator("[data-filter-count]").first
        clear = page.locator("[data-filter-clear]").first
        count.wait_for(state="visible")
        clear.wait_for(state="visible")
        count_box = count.bounding_box()
        clear_box = clear.bounding_box()
        if count_box is None or clear_box is None:
            raise AssertionError("expected both the count and Clear to have a box at 390px")
        if round(count_box["y"]) != round(clear_box["y"]):
            raise AssertionError(
                "expected the Health filter count and Clear to report the same "
                "top at 390px (A-18 regressing a third time), got %r and %r"
                % (count_box["y"], clear_box["y"]))
        in_group = page.eval_on_selector_all(
            ".filter-bar__meta",
            "els => els.map(el => [!!el.querySelector('[data-filter-count]'),"
            " !!el.querySelector('[data-filter-clear]')])")
        if in_group != [[True, True]]:
            raise AssertionError(
                "expected exactly one .filter-bar__meta group on Health holding "
                "both controls, got %r" % (in_group,))
        # C5: the page header's own clock left the monospace family for
        # the one time-value role.
        clock_class = page.eval_on_selector("[data-refresh-clock]", "el => el.className")
        if "mono" in clock_class.split() or "time-value" not in clock_class.split():
            raise AssertionError(
                "expected the page header's Updated clock on .time-value and not "
                "on .mono, got %r" % (clock_class,))
        if page.viewport_size["width"] != 390:
            raise AssertionError("expected the measurement to be taken at 390px")
    finally:
        context.close()


def test_the_no_js_floor_holds_for_health(new_context, server):
    """with scripts blocked Health renders in full — all four tiles with their
    label/verdict/detail slots each exactly once, the registry filter bar and
    Clear, the unresolved-prefix rows, and a per-row Resolve action that actually
    navigates to the Airlines resolve surface (D-09's floor asserted at this
    plan's own commit, 22-12-PLAN.md Task 3)"""
    # D-09 asks the floor to hold THROUGHOUT the phase, so it is asserted
    # at THIS plan's own commit rather than deferred to the phase-closing
    # sweep. This plan rebuilds every tile body, restructures a table's
    # cells and re-wraps a filter bar — all server-rendered, and all of
    # it must therefore be complete with scripts blocked.
    with _no_js_page(new_context, server.base_url(), "/health") as page:
        tiles = page.eval_on_selector_all(".stat-tile", "els => els.length")
        if tiles != 4:
            raise AssertionError(
                "expected all four Health tiles to render with scripts blocked, "
                "got %d" % (tiles,))
        # Every tile is complete, not merely present.
        slots = page.eval_on_selector_all(
            ".stat-tile",
            "els => els.map(el => ["
            "  el.querySelectorAll(':scope > .stat-tile__caption').length,"
            "  el.querySelectorAll("
            "    ':scope > .widget-verdict, :scope > .stat-tile__value,"
            "     :scope > .empty-state > .empty-state__heading').length,"
            "  el.querySelectorAll("
            "    ':scope > .widget-detail, :scope > .empty-state >"
            "     .empty-state__body').length])")
        for index, slot in enumerate(slots):
            if slot != [1, 1, 1]:
                raise AssertionError(
                    "expected tile %d to render its label/verdict/detail slots "
                    "exactly once each with scripts blocked, got %r"
                    % (index, slot))
        if not page.query_selector(".filter-bar [data-filter-input]"):
            raise AssertionError("expected the registry filter bar with scripts blocked")
        if not page.query_selector("[data-filter-clear]"):
            raise AssertionError("expected the Clear control with scripts blocked")
        # The table OR its card fallback — whichever the viewport
        # resolves to — must be present, and the Resolve action reachable
        # from it.
        rows = page.eval_on_selector_all(
            "table.data-table--registry tbody tr, ul.data-cards > li", "els => els.length")
        if rows < 1:
            raise AssertionError(
                "expected the unresolved-prefix rows (table or card fallback) with "
                "scripts blocked, got %d" % (rows,))
        # `:visible` matters: this card list and this table are BOTH in
        # the DOM at every width (the `.data-cards ~ .data-table-wrap`
        # toggle is CSS-only, by design, so the no-JS path has both), and
        # the card list renders first. The reachable one is whichever the
        # viewport actually shows — which is the thing "reachable without
        # scripts" means.
        resolve = page.locator('a[href^="/airlines?resolve="]:visible').first
        if resolve.count() == 0:
            raise AssertionError(
                "expected the per-row Resolve action to be reachable with scripts "
                "blocked")
        href = resolve.get_attribute("href")
        with page.expect_navigation():
            resolve.click()
        if "/airlines" not in page.url or "resolve=" not in page.url:
            raise AssertionError(
                "expected the Resolve link (%r) to navigate to the Airlines "
                "resolve surface with scripts blocked, got %r" % (href, page.url))


# ----------------------------------------------------------------
# 22-01-PLAN.md Task 3 (D-01/D-02, B1/T1/T8): the four checks this whole
# plan exists to make possible. Each one saves a real setting through the
# real UI, so each gets its own function-scoped, seeded server.
# ----------------------------------------------------------------

def test_display_reveal_and_persist_across_all_field_kinds(page, make_app_server):
    """Display: a theme chip, a runway card and a quiet-hours time field each commit
    via change, REVEAL the bar, and PERSIST to DISK once Enregistrer is clicked
    (form=-attached radio and time-input field kinds — the Enable-display checkbox
    this check also covered is retired outright by 22-05-PLAN.md Task 1,
    X1/D-04/D-12.1; retargeted from the retired auto-save onto the restored bar by
    28-10-PLAN.md Task 1, CFG-77/CFG-78)"""
    # 28-10-PLAN.md Task 1 (CFG-77/CFG-78): RETARGETED from auto-save onto
    # the restored bar — the pre-27-04 name is genuinely honest again: a
    # committed edit REVEALS the bar (never a click before that) and only
    # Enregistrer PERSISTS it (never a click-free auto-save). Its real
    # value (three cross-DOM form=-attached field KINDS — radio-as-chip,
    # radio-as-card, time input — each genuinely committing, revealing
    # the bar, and persisting once saved) survives unchanged.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)
    theme_ids = device_config.THEME_IDS
    runway_ids = device_config.RUNWAY_IDS

    def on_disk():
        return device_config.load_device_config(server.tmpdir)

    # 1. Theme chip (Frame colours card, form=-attached, rendered as a
    # sibling of <form id="settings-form">).
    page.goto(base_url + "/display")
    target_theme = theme_ids[1]
    theme_sel = 'input[name="theme"][value="%s"]' % target_theme
    _click_control(page, theme_sel)
    _wait_for_bar(page)
    _save_via_bar(page)
    if on_disk()["theme"] != target_theme:
        raise AssertionError(
            "expected the theme chip's committed value to reach disk, got %r"
            % (on_disk()["theme"],))

    # 2. Runway card (also a sibling of the form).
    target_runway = runway_ids[1]
    runway_sel = 'input[name="tracked_runway"][value="%s"]' % target_runway
    _click_control(page, runway_sel)
    _wait_for_bar(page)
    _save_via_bar(page)
    if str(on_disk()["tracked_runway"]) != str(target_runway):
        raise AssertionError(
            "expected the runway card's committed value to reach disk, got %r"
            % (on_disk()["tracked_runway"],))

    # 3. Enable-display checkbox — RETIRED outright by 22-05-PLAN.md
    # Task 1 (X1/D-04/D-12.1): the Frame strip is now the ONLY on/off
    # control for the screen, so this settings page no longer renders a
    # display_enabled checkbox for the B1 regression to cover here at
    # all. No replacement checkbox exists on Display any more (Quiet
    # hours' own on/off checkbox is retired the same way) — the
    # remaining two field kinds below (radio, time input) still prove
    # the cross-DOM form= delegation this check exists for.

    # 4. Quiet-hours time field (a sibling of the form). .fill()
    # dispatches `input` only (Playwright's own documented contract) —
    # never `change` — so _commit_field() fires the real `change` a blur
    # would, which is the exact commit the bar's own document-level
    # listener is waiting for.
    quiet_sel = 'input[name="quiet_hours_start"]'
    page.fill(quiet_sel, "22:15")
    _commit_field(page, quiet_sel)
    _wait_for_bar(page)
    _save_via_bar(page)
    if str(on_disk()["quiet_hours_start"]) != "22:15":
        raise AssertionError(
            "expected the quiet-hours time field's committed value to reach "
            "disk, got %r" % (on_disk()["quiet_hours_start"],))


def test_device_reveal_and_persist_stays_in_step_with_display(page, make_app_server):
    """Device: the wake-interval field commits via change, REVEALS the bar, and
    PERSISTS to DISK once Enregistrer is clicked, proving the two scopes stay in
    step (B1) — witnessed by the wake-interval field since the Diagnostic LED
    stopped being a Save-governed control (retargeted in place by 23-07-PLAN.md
    Task 2, D2/CFG-36; retargeted from the retired auto-save onto the restored bar
    by 28-10-PLAN.md Task 1, CFG-77/CFG-78)"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)
    # 23-07-PLAN.md Task 2 (D2/CFG-36, X1/D-04): RETARGETED IN PLACE from
    # the Diagnostic LED checkbox to the wake-interval field. The LED is
    # no longer a Save-governed control at all — it is a role="switch"
    # applying instantly over /quick/led. 28-10-PLAN.md Task 1
    # (CFG-77/CFG-78): retargeted AGAIN, from auto-save onto the
    # restored bar — the wake-interval field commits via change, REVEALS
    # the bar, and PERSISTS to DISK once Enregistrer is clicked, exactly
    # like Display's own fields, proving the two scopes still stay in
    # step.
    page.goto(base_url + "/device")
    wake_sel = 'input[name="wake_interval_s"]'
    before = page.eval_on_selector(wake_sel, "el => el.value")
    target = "1800" if before != "1800" else "3600"
    page.fill(wake_sel, target)
    _commit_field(page, wake_sel)
    _wait_for_bar(page)
    _save_via_bar(page)
    stored = device_config.load_device_config(server.tmpdir)["wake_interval_s"]
    if str(stored) != target:
        raise AssertionError(
            "expected the edited wake interval to reach disk, got %r" % (stored,))
    # And the LED switch, which is NOT part of that form, must be unmoved
    # by the save — the whole point of T-23-25.
    led_state = page.eval_on_selector(
        '[data-quick-region] button[role="switch"]',
        "el => el.getAttribute('aria-checked')")
    if led_state not in ("true", "false"):
        raise AssertionError(
            "expected the Device page to render an LED switch with a real "
            "aria-checked, got %r" % (led_state,))


def test_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves(page, make_app_server):
    """the bar (the single [data-static-save-fallback] Save affordance, relocated
    inside it, never a second button) is server-rendered VISIBLE — the no-JS
    floor — and hides IMMEDIATELY once script proves itself live; an edit
    REVEALS it again, naming the changed section via [data-dirty-count]; and
    clicking its own Save persists to disk through a real navigation — the
    INVERSE of 27-03-PLAN.md Task 2 (CFG-64) and 27-04-PLAN.md Task 4
    (CFG-63)'s own retired polarity, which this check's former name asserted
    (D-01/CFG-64/CFG-77/CFG-78, retargeted onto the restored bar by
    28-10-PLAN.md Task 2)"""
    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): RETARGETED — the polarity
    # this check asserted is INVERTED, not a mechanical swap.
    # 27-03-PLAN.md Task 2 (CFG-64) and 27-04-PLAN.md Task 4 (CFG-63)
    # both asserted the fallback Save button stayed HIDDEN before AND
    # after an edit, because neither of their models had a visible save
    # affordance to reveal (auto-save's own bar never returned; CFG-64's
    # fallback button was purely a scripts-blocked floor with nothing
    # left to click). 28-08-PLAN.md restored the bar as the SAME element
    # (`[data-static-save-fallback]`, relocated inside the bar's own
    # markup rather than duplicated) — server-rendered VISIBLE now,
    # because the bar's own visible state IS the no-JS floor; hidden by
    # script the instant script proves itself live (dirty-state.js's own
    # `bar.hidden = true` at init, before any listener is attached);
    # revealed again the instant a real edit exists. This is the exact
    # clause a future reader would "correct" back to the retired
    # polarity — written down here so they do not.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)

    page.goto(base_url + "/display")
    bar = page.locator("[data-dirty-bar]")
    # 1. Script has proven itself live: the bar hides at init, on a page
    #    with no edits at all.
    if bar.is_visible():
        raise AssertionError(
            "expected the bar to be HIDDEN immediately once script runs on "
            "a fresh load — dirty-state.js's own bar.hidden = true at init, "
            "the no-JS-floor polarity this check exists to pin down")

    theme_ids = device_config.THEME_IDS
    target = theme_ids[2]
    _click_control(page, 'input[name="theme"][value="%s"]' % target)
    # 2. An edit REVEALS the bar — the opposite of the retired contract,
    #    which asserted nothing on the page was ever supposed to show a
    #    save affordance again.
    _wait_for_bar(page)
    count_text = _bar_text(page)
    if not count_text:
        raise AssertionError(
            "expected [data-dirty-count] to name the changed section once "
            "the bar reveals, got an empty string")

    # 3. Clicking the bar's own Save persists to disk through a real
    #    navigation.
    _save_via_bar(page)
    stored = device_config.load_device_config(server.tmpdir)["theme"]
    if stored != target:
        raise AssertionError(
            "expected the theme edit to reach disk once the bar's own Save "
            "is clicked, got %r" % (stored,))


def test_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit(page, server):
    """the leave-guard stays armed for a field that has been edited but never fired
    change (the bar already visible and already naming the section, the
    restored model's no-silent-phase clause — strictly more than the retired
    save-status region ever asserted); the guard STAYS ARMED, not disarmed, the
    instant change commits the edit, because a committed-but-unsaved change is
    exactly what the restored guard exists to warn about; and Annuler is the
    guard's own exit, disarming it and hiding the bar (the re-arm-after-Cancel
    clause is 28-11-PLAN.md's own check, not duplicated here) (D-10,
    <restored_guard_semantics>, retargeted from the retired auto-save's own
    inverted disarm-on-commit contract by 28-10-PLAN.md Task 2, CFG-77/CFG-78;
    27-04-PLAN.md Task 4, CFG-63)"""
    # 28-10-PLAN.md Task 2 (CFG-77/CFG-78): REWRITTEN, not a mechanical
    # swap — the assertion this check made is INVERTED by the
    # restoration, and half its subject (the save-status region) is
    # deleted outright.
    #
    # 27-04-PLAN.md Task 4 (D-10/CFG-63) asserted the guard DISARMED the
    # instant a change COMMITTED — correct under auto-save, where a
    # committed change was already saved and there was nothing left to
    # warn about. Under the restored bar (<restored_guard_semantics> in
    # 28-10-PLAN.md), a committed-but-unsaved change is EXACTLY what the
    # guard exists to warn about — it stays armed until Enregistrer or
    # Annuler. Asserting the old disarm-on-commit clause here would
    # prove the retired contract, not the current one.
    #
    # The save-status-silent clause is gone with the region itself;
    # replaced by the equivalent-or-stronger bar clause below — the
    # restored model has no silent phase at all, since the bar is
    # already visible and already naming the section the instant the
    # edit is merely TYPED, before any commit.
    #
    # The re-arm-after-Cancel clause (a NEW edit after Annuler re-arming
    # the guard) is 28-11-PLAN.md's own check — not duplicated here; see
    # that plan's leave-guard re-arm check for the clause this one
    # deliberately stops short of.
    #
    # This check never clicks Enregistrer, only Annuler — nothing it
    # does reaches disk, so it shares the module's read-only server.
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/device")

    # a. Fresh load: disarmed.
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to start disarmed on a clean page load")

    wake_sel = 'input[name="wake_interval_s"]'
    before = page.eval_on_selector(wake_sel, "el => el.value")
    target = "1800" if before != "1800" else "3600"

    # b. TYPE without committing — `input` fires per keystroke; `change`
    #    does not fire until focus leaves the field. This is the
    #    uncommitted state, and it is still true, at equal strength,
    #    after this restoration.
    page.eval_on_selector(wake_sel, "el => el.focus()")
    page.keyboard.press("ControlOrMeta+A")
    page.keyboard.type(target)
    if page.eval_on_selector(wake_sel, "el => el.value") != target:
        raise AssertionError(
            "expected the typed value to be held by the field before any commit")
    if not _guard_armed(page):
        raise AssertionError(
            "expected the leave-guard to be armed for an edited-but-uncommitted "
            "field (D-10) — countDifferences() > 0 the moment a keystroke "
            "differs, never waiting for change")
    # The equivalent-or-stronger replacement for the deleted silent-region
    # clause: the restored model has NO silent phase — the bar is already
    # visible and [data-dirty-count] already names the section even
    # before this edit commits.
    _wait_for_bar(page)
    if not _bar_text(page):
        raise AssertionError(
            "expected [data-dirty-count] to already name the changed section "
            "for a merely-typed, uncommitted edit — the restored model has no "
            "silent phase, which is strictly more than the retired region ever "
            "asserted")

    # c. COMMIT it — blur fires `change`. Under the restored semantics
    #    the guard STAYS ARMED: a committed-but-unsaved change is
    #    exactly what it exists to warn about.
    page.keyboard.press("Tab")
    if not _guard_armed(page):
        raise AssertionError(
            "expected the leave-guard to STAY ARMED the instant change "
            "commits the edit — a committed change is unsaved until "
            "Enregistrer, not the retired auto-save contract where a commit "
            "disarmed the guard because it was already persisted")
    stored = device_config.load_device_config(server.tmpdir)["wake_interval_s"]
    if str(stored) == target:
        raise AssertionError(
            "the committed value already reached disk with no Save click — "
            "this check's own premise (unsaved-but-committed) does not hold")

    # d. Click Annuler: the guard DISARMS and the bar hides.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm once Annuler is clicked")


# --- 28-11-PLAN.md Task 3 (CFG-77): the leave-guard's re-arm-after-Cancel
# clause — the one nothing in the phase proves. The check above
# (28-10-PLAN.md Task 2) proves armed-on-typed-edit,
# stays-armed-through-commit and disarmed-by-Cancel, and stops there BY
# DESIGN (its own comment names this one). CFG-77's own binding wording:
# "does not disarm the leave-guard permanently... kept exactly where
# CFG-63's own carve-out already put it" (.planning/REQUIREMENTS.md).
# `git show 6dea46a`'s own header names the historical defect this
# records: a naive Cancel handler sets suppressGuard = true once and
# never clears it, leaving the guard dead for the rest of the page's
# life while steps 1-3 below alone would still pass against that exact
# defect. This check never clicks Enregistrer either, so it too shares
# the module's read-only server.
def test_the_leave_guard_re_arms_after_a_new_edit_following_cancel(page, server):
    """the leave-guard's re-arm-after-Cancel clause — CFG-77's own 'does not
    disarm the leave-guard permanently... kept exactly where CFG-63's own
    carve-out already put it' — has executable coverage for the first time:
    fresh load (disarmed) -> edit (armed) -> Annuler (disarmed) -> a NEW edit
    (RE-ARMED, the clause nothing else in this phase proves, and exactly the
    defect a Cancel handler that sets suppressGuard=true once and never clears
    it reproduces) -> a second Annuler (disarmed again, so a one-shot re-arm
    cannot pass); reuses the existing _guard_armed() beforeunload probe
    throughout — never a second one (CFG-77, 28-11-PLAN.md Task 3;
    complements 28-10-PLAN.md Task 2's own armed-on-typed-edit/stays-armed-
    through-commit/disarmed-by-Cancel check, which deliberately stops short of
    this clause)"""
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/display")

    # 1. Fresh load: disarmed, bar hidden.
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to start disarmed on a clean page load")
    _wait_for_bar_hidden(page)

    runway_sel = 'input[name="tracked_runway"]'
    current_runway = page.eval_on_selector("%s:checked" % runway_sel, "el => el.value")
    first_target = next(r for r in device_config.RUNWAY_IDS if r != current_runway)
    second_target = next(
        r for r in device_config.RUNWAY_IDS
        if r != current_runway and r != first_target)

    # 2. Edit a field: armed, bar visible. Kept minimal on purpose — the
    #    check above already proves the typed-vs-committed distinction;
    #    this step is only the precondition steps 3-5 need.
    _click_control(page, '%s[value="%s"]' % (runway_sel, first_target))
    if not _guard_armed(page):
        raise AssertionError("expected the leave-guard to arm for a real edit")
    _wait_for_bar(page)

    # 3. Click Annuler: disarmed, bar hides.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm once Annuler is clicked")

    # 4. THE WHOLE POINT. A NEW edit that FOLLOWS a Cancel must RE-ARM
    #    the guard — nothing else in this phase proves it, and it is
    #    exactly what a naive `suppressGuard = true` (set once in the
    #    Cancel handler, never cleared) gets wrong, while steps 1-3
    #    above alone would still pass against that defect.
    _click_control(page, '%s[value="%s"]' % (runway_sel, second_target))
    if not _guard_armed(page):
        raise AssertionError(
            "expected the leave-guard to RE-ARM for an edit that follows a "
            "Cancel — CFG-77's own 'does not disarm the leave-guard "
            "permanently... kept exactly where CFG-63's own carve-out "
            "already put it', and exactly the defect a Cancel handler that "
            "sets suppressGuard=true once and never clears it reproduces")
    _wait_for_bar(page)

    # 5. A SECOND Annuler disarms again — a re-arm that can only happen
    #    once is the same defect wearing a different number.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm on a SECOND Annuler too")


def test_strip_switch_applies_without_the_leave_guard_while_other_navigation_still_warns(
        page, make_app_server):
    """activating a Frame strip switch with unsaved Display edits present applies over
    fetch WITHOUT navigating, leaves the leave-guard ARMED for the edit still in
    the form and the switch still pressable, and raises no dialog, while a plain
    nav-link navigation with the same unsaved edit still raises one (22-05-PLAN.md
    Task 3, D-04; retargeted in place by 23-07-PLAN.md Task 1, which is what took
    the navigation away)"""
    # 22-05-PLAN.md Task 3 (D-04): a real browser proof, not a read of
    # dirty-state.js's private suppressGuard variable. Chromium
    # (headless, under Playwright) surfaces a beforeunload guard's own
    # preventDefault() as a real `dialog` event of type "beforeunload" -
    # confirmed experimentally against a minimal fixture before this
    # check was written - so listening for that event and asserting its
    # presence/absence is a genuine, non-cosmetic behavioural probe.
    #
    # This check flips a real setting (display_enabled) through the
    # strip's own quick-switch endpoint, so it gets its own
    # function-scoped server.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/display")
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))

    # 23-07-PLAN.md Task 1 (D2/CFG-36): RETARGETED IN PLACE, and made
    # strictly stronger. This check used to assert the switch NAVIGATES.
    # D2 is the decision that it no longer does: the flip lands under
    # the finger and the POST goes out over fetch, so there is no
    # unload at all and the dialog this check is about cannot fire for
    # a mechanical reason.
    #
    # That would make the original assertion vacuous, so it is replaced
    # by the property that actually matters now and that the original
    # could not reach: after the switch has applied, the leave-guard
    # must still be ARMED for the unsaved edit that is still sitting in
    # the form. That is the real hazard the conversion introduced —
    # dirty-state.js disarms its guard for any [data-quick-switch]
    # submit, and on a page whose form was already dirty nothing would
    # ever re-arm it. quick-switch.js listens in the capture phase and
    # stops propagation precisely so that listener never runs for a
    # submission that is not happening.
    #
    # 27-04-PLAN.md Task 4 (CFG-63): a radio commits (fires change) the
    # instant it is clicked, which now means auto-save begins and the
    # guard disarms again a moment later — a radio click can no longer
    # hold this check's own "unsaved edit" precondition open. Focusing
    # and TYPING would not survive either: clicking the switch button
    # shifts DOM focus away from the field, which BLURS it and fires
    # the very `change` that would commit and auto-save it before the
    # assertion below even runs. countDifferences() (the guard's own
    # predicate) reads the field's LIVE value against the load-time
    # snapshot and needs no event at all to see a difference, so the
    # value is set directly with no focus taken and no event
    # dispatched — nothing to blur, nothing to commit.
    quiet_sel = 'input[name="quiet_hours_start"]'
    page.eval_on_selector(quiet_sel, "el => { el.value = '04:44'; }")
    if not _guard_armed(page):
        raise AssertionError(
            "control: the leave-guard was not armed before the switch was "
            "touched, so the assertion below would prove nothing")
    before = device_config.load_device_config(server.tmpdir)["display_enabled"]
    switch_sel = 'form[action="/quick/display"] button[type="submit"]'
    with page.expect_response(
            lambda r: r.url.split("?")[0] == base_url + "/quick/display"):
        page.click(switch_sel)
    page.wait_for_timeout(400)
    if dialogs:
        raise AssertionError(
            "expected NO beforeunload dialog when activating the strip's own "
            "switch with unsaved edits present, got %r" % (dialogs,))
    after = device_config.load_device_config(server.tmpdir)["display_enabled"]
    if after == before:
        raise AssertionError("expected the strip switch's own change to persist")
    if page.url.split("?")[0] != base_url + "/display":
        raise AssertionError(
            "expected the switch to apply WITHOUT navigating (D2), but the "
            "page moved to %r" % (page.url,))
    if not _guard_armed(page):
        raise AssertionError(
            "the leave-guard was left DISARMED after a switch applied on a "
            "page that still holds an unsaved edit — dirty-state.js disarms "
            "for any [data-quick-switch] submit and re-arms only on the next "
            "edit, so a form that was already dirty would lose its guard for "
            "the rest of the page's life (D2/CFG-36, 23-07-PLAN.md Task 1)")
    # The switch must also still be pressable: a submit-guard that
    # disabled it on the way out would leave a dead control on a page
    # that never reloads.
    if page.eval_on_selector(switch_sel, "el => el.disabled"):
        raise AssertionError(
            "the switch was left disabled after applying — with no navigation "
            "to replace the page, a disabled switch stays disabled forever")

    # Reset: reload, make the SAME kind of unsaved edit again, then
    # navigate away by a plain nav link - no [data-quick-switch] form
    # involved at all - and the guard must still warn. Same focus-free
    # value set as above, for the same reason: clicking the nav link
    # would blur a FOCUSED field and commit it before the navigation's
    # own beforeunload check ever runs.
    page.goto(base_url + "/display")
    dialogs[:] = []
    page.eval_on_selector(quiet_sel, "el => { el.value = '05:55'; }")
    with page.expect_navigation():
        page.click('a[href="/"]')
    if "beforeunload" not in dialogs:
        raise AssertionError(
            "expected a PLAIN navigation with the same unsaved edit to still "
            "raise the beforeunload dialog, got %r" % (dialogs,))


def test_three_runway_cards_share_one_line_at_390px(new_context, server):
    """at 390px the three runway cards report one shared line (equal tops), equal
    heights, and BOTH their border-excluded and their outer widths equal within
    1px at a border total of exactly 2.0 each - 22-10's stated T6 allowance for
    the selected card's 2px border is deleted, closed by 22-15-PLAN.md Task 1 -
    and each still clears 44x44 - never a 2 + 1 orphan (B9, 22-10-PLAN.md Task 2)
    - with the transform neutralised for the read and EXACTLY ONE card proven to
    carry 23-10's selection scale"""
    # B9 (22-AUDIT.md, 22-10-PLAN.md Task 2). The measured defect was a
    # 2 + 1 orphan at 390px: 150x150, 150x150, then a lone 308x217. Only
    # a real layout engine can see this, which is why it lives here and
    # not in a string-comparison harness.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.wait_for_load_state("networkidle")
        # 23-10-PLAN.md Task 1 (D3/CFG-32): the selected card now also
        # carries a `transform: scale(...)` — the "selection answers"
        # clause. A transform IS reflected in getBoundingClientRect(),
        # which reports the VISUAL box, and is NOT reflected in the
        # layout box. T6 and B9 are both statements about the LAYOUT box
        # (a border that grew a flex item and pushed its siblings; a
        # card that wrapped onto its own line), so the transform is
        # neutralised for the duration of the measurement — with its own
        # transition neutralised first, or the read below would catch
        # the 180ms unwind mid-flight and measure a value that is
        # neither the scaled nor the unscaled box.
        #
        # Neutralising it is only honest if the scale is really there,
        # so the real computed transform is captured BEFORE the
        # override and asserted below: exactly one of the three cards
        # must be scaled (the selected one), and the other two must not
        # be. That pairing is what keeps this check from passing for a
        # build that dropped the scale entirely.
        boxes = page.evaluate(
            "() => [...document.querySelectorAll('.runway-card')]"
            ".map(e => { const live = getComputedStyle(e).transform; "
            "e.style.transition = 'none'; e.style.transform = 'none'; "
            "const b = e.getBoundingClientRect(); "
            "const s = getComputedStyle(e); "
            "const bw = parseFloat(s.borderLeftWidth) "
            "+ parseFloat(s.borderRightWidth); "
            "e.style.removeProperty('transform'); "
            "e.style.removeProperty('transition'); "
            "return {w: b.width, inner: b.width - bw, border: bw, "
            "h: b.height, top: b.top, left: b.left, live: live}; })")
        if len(boxes) != 3:
            raise AssertionError("expected 3 runway cards, got %d" % len(boxes))
        scaled = [b["live"] for b in boxes if b["live"] not in ("none", "")]
        if len(scaled) != 1:
            raise AssertionError(
                "expected EXACTLY ONE of the three runway cards to carry the "
                "selection scale (D3's 'selecting a card answers with a small "
                "scale'), got %r — this measurement neutralises the transform to "
                "read the LAYOUT box, so it is only meaningful while the "
                "transform genuinely exists"
                % ([b["live"] for b in boxes],))

        tops = [b["top"] for b in boxes]
        if max(tops) - min(tops) > 0.5:
            raise AssertionError(
                "expected all three cards on ONE line (equal tops), got %r - a "
                "2 + 1 orphan is exactly B9's defect" % (tops,))
        heights = [b["h"] for b in boxes]
        if max(heights) - min(heights) > 0.5:
            raise AssertionError("expected three equal card heights, got %r" % (heights,))
        lefts = sorted(b["left"] for b in boxes)
        if lefts != [b["left"] for b in sorted(boxes, key=lambda b: b["left"])]:
            raise AssertionError("expected three distinct columns")

        # B9's "equal within 1px" is asserted on the cards' BORDER-EXCLUDED
        # widths, which is what "three equal columns" actually means and
        # what the flex rule controls - AND, since 22-15-PLAN.md Task 1
        # closed T6, on their outer widths too.
        #
        # 22-10-PLAN.md's STATED EXCEPTION IS DELETED HERE. It read: the
        # cards' outer widths are not equal within 1px, because the saved
        # card carries `.runway-card--selected`'s 2px border against its
        # siblings' 1px and `box-sizing: border-box` does not hold the
        # OUTER box of a `flex: 1 1 0` item (measured 98.67 against
        # 96.66/96.67 at 390px). It named 22-15-PLAN.md as the plan that
        # removes it. That plan holds every selected-state border
        # constant at 1px and carries selection on `box-shadow: inset 0
        # 0 0 2px`, which occupies no layout space, so `inner` and `w`
        # have converged and the allowance is gone: plain equality on
        # BOTH, and every card's own border total must now be exactly
        # 2.0 (1px per side) with no second value permitted.
        inners = [b["inner"] for b in boxes]
        if max(inners) - min(inners) > 1.0:
            raise AssertionError(
                "expected three equal card widths within 1px once each card's own "
                "border is excluded, got %r (outer %r)"
                % (inners, [b["w"] for b in boxes]))
        outers = [b["w"] for b in boxes]
        if max(outers) - min(outers) > 1.0:
            raise AssertionError(
                "expected three equal card OUTER widths within 1px now that T6 is "
                "closed - a selected card must be the same size as its siblings, "
                "got %r (inner %r)" % (outers, inners))
        borders = sorted({round(b["border"], 2) for b in boxes})
        if borders != [2.0]:
            raise AssertionError(
                "expected every card's border total to be exactly 2.0 (1px per "
                "side) in every selection state - T6 moved the 2px accent signal "
                "to an inset ring, got border totals %r" % (borders,))
        # Touch target, confirmed by measurement rather than assumed: the
        # cards get narrower, and the hidden radio's register entry is
        # exempt BY DELEGATION to this wrapping <label>, so the label
        # itself must still clear 44px in BOTH axes.
        for b in boxes:
            if b["w"] < 44 or b["h"] < 44:
                raise AssertionError(
                    "every runway card must stay >=44x44 for the hidden radio's "
                    "exempt-by-delegation touch-target entry, got %r" % (b,))
    finally:
        context.close()


def test_selecting_a_theme_chip_answers_and_moves_no_layout_box(new_context, server):
    """at 390px selecting a palette chip ANSWERS - the chip's border-colour changes
    to the accent, an inset accent ring (box-shadow) appears, and the
    .palette-chip__name wash changes - while its own LAYOUT box (offsetWidth/
    Height/Left/Top), the grid's own box and EVERY chip's position inside it are
    plain-equal before and after, so T6 cannot recur through the selection signal
    (D3/CFG-32, 23-10-PLAN.md Task 1; re-pointed to .palette-chip and narrowed off
    the scale/transition clauses 30-07-PLAN.md deliberately did not add, by
    30-08-PLAN.md Task 2, CFG-85)"""
    # 23-10-PLAN.md Task 1 (D3/CFG-32). Two statements that only a real
    # layout engine can make together:
    #
    #   1. Selection ANSWERS - the chip scales, and its body's wash
    #      fades in over var(--motion-fast) rather than cutting.
    #   2. Selection moves NO layout box - T6's defect (a selected card
    #      a different size from its siblings, measured at 98.67px
    #      against 96.66px at 390px) cannot recur through a transform,
    #      and this is the measurement that says so rather than the
    #      reasoning that assumes it.
    #
    # The box is read through offsetWidth/offsetHeight/offsetLeft/
    # offsetTop, NOT getBoundingClientRect(): the offset* family reports
    # the LAYOUT box and is transform-independent by definition, which
    # is exactly the distinction this check exists to prove. Plain
    # equality, no tolerance - these are integers from the same element
    # measured twice.
    #
    # POSITIONS ARE MEASURED RELATIVE TO THE CHIP GRID, not to the page,
    # and that is a correction this check needed rather than a
    # convenience: selecting a chip makes the form dirty, and 23-09's
    # save bar replaces the section's own inline fallback Save button
    # when it arrives, which removes a real 36px from the page ABOVE
    # this card (measured: every chip moved from y=1608 to y=1572). That
    # is another plan's intended behaviour, it happens whichever chip is
    # clicked, and a page-absolute assertion would report it as this
    # plan's layout shift. The statement that belongs here is that
    # nothing inside the grid moved, and every chip in the grid is
    # measured, not just the clicked one.
    #
    # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from the retired
    # [data-usage-panel-target]/label.theme-chip departures panel to
    # details.usage-row[data-usage="departures"]/label.palette-chip. The
    # "answers with a scale" half of this check's ORIGINAL property does
    # NOT survive the rebuild — confirmed directly against style.css
    # (30-07-PLAN.md Task 1's own comment): the selected .palette-chip's
    # :has(input:checked) rule adds exactly three consequences
    # (border-colour, inset box-shadow ring, the .palette-chip__name
    # wash) and NO transform/transition, a DELIBERATE, already-recorded
    # 30-07 decision ("a fourth [treatment] would also need a new
    # transition declared on this component's own base rule, out of
    # this plan's scope"). Restating a scale/transition-duration
    # assertion the real CSS no longer produces would make this check
    # permanently red for a reason that is not a defect, so the
    # property actually proved here is the one that DOES still hold:
    # selection paints instantly via border/box-shadow/wash, and — the
    # half that matters for T6 — moves no layout box at all, since
    # box-shadow is `inset` and only the border's COLOUR (never its
    # width) changes.
    #
    # This check clicks a radio but never Enregistrer, so nothing here
    # reaches disk and it shares the module's read-only server.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.wait_for_load_state("networkidle")

        probe = (
            "() => {"
            "const row = document.querySelector("
            "'details.usage-row[data-usage=\"departures\"]');"
            "if (!row) return {error: 'no departures row'};"
            "const chips = [...row.querySelectorAll('label.palette-chip')]"
            ".filter(c => c.querySelector('input[type=radio]'));"
            "if (chips.length < 2) return {error: 'chips: ' + chips.length};"
            "const target = chips.find("
            "c => !c.querySelector('input[type=radio]').checked);"
            "if (!target) return {error: 'every chip is already checked'};"
            "const grid = target.closest('.palette');"
            "if (!grid) return {error: 'no .palette'};"
            "const read = e => { const s = getComputedStyle(e);"
            "const name = e.querySelector('.palette-chip__name');"
            "const ns = name ? getComputedStyle(name) : null;"
            "return {w: e.offsetWidth, h: e.offsetHeight,"
            " left: e.offsetLeft - grid.offsetLeft,"
            " top: e.offsetTop - grid.offsetTop,"
            " borderColor: s.borderColor, boxShadow: s.boxShadow,"
            " wash: ns ? ns.backgroundColor : null}; };"
            "return {value: target.querySelector('input[type=radio]').value,"
            " chip: read(target),"
            " grid: {w: grid.offsetWidth, h: grid.offsetHeight},"
            " all: chips.map(c => { const r = read(c);"
            " return [r.w, r.h, r.left, r.top]; })};"
            "}")
        before = page.evaluate(probe)
        if before.get("error"):
            raise AssertionError(
                "could not find an unchecked palette chip: %s" % (before["error"],))
        value = before["value"]
        _click_control(
            page,
            'details.usage-row[data-usage="departures"] '
            'label.palette-chip input[type=radio][value="%s"]' % value)
        # No transition to wait out any more (see the comment above) - a
        # short settle for the change event/repaint is still cheap
        # insurance.
        page.wait_for_timeout(200)
        after = page.evaluate(
            probe.replace(
                "const target = chips.find("
                "c => !c.querySelector('input[type=radio]').checked);",
                "const target = chips.find("
                "c => c.querySelector('input[type=radio]').value === "
                + repr(value).replace("'", '"') + ");"))
        if after.get("error"):
            raise AssertionError("could not re-find the clicked chip: %s" % (after["error"],))

        # --- 1. the answer is real -------------------
        if before["chip"]["boxShadow"] not in ("none", ""):
            raise AssertionError(
                "expected an UNSELECTED palette chip to carry no box-shadow, got "
                "%r" % (before["chip"]["boxShadow"],))
        if after["chip"]["boxShadow"] in ("none", ""):
            raise AssertionError(
                "expected the newly-selected chip to carry the accent inset ring "
                "(30-07-PLAN.md Task 1: box-shadow inset 0 0 0 2px), got %r - a "
                "chip that switches state with no visible signal at all is the "
                "behaviour this check exists to catch" % (after["chip"]["boxShadow"],))
        if before["chip"]["borderColor"] == after["chip"]["borderColor"]:
            raise AssertionError(
                "expected the selected chip's border-colour to change to the "
                "accent, both read %r" % (after["chip"]["borderColor"],))
        if before["chip"]["wash"] == after["chip"]["wash"]:
            raise AssertionError(
                "expected the selected chip's .palette-chip__name wash to change "
                "on selection, both read %r" % (after["chip"]["wash"],))

        # --- 2. and nothing moved --------------------
        for key in ("w", "h", "left", "top"):
            if before["chip"][key] != after["chip"][key]:
                raise AssertionError(
                    "the chip's own LAYOUT box changed on selection: %s went from "
                    "%r to %r. T6's defect was exactly this (98.67px against "
                    "96.66px at 390px); a border-colour/inset-shadow selection "
                    "signal must change no layout box at all"
                    % (key, before["chip"][key], after["chip"][key]))
        if before["grid"] != after["grid"]:
            raise AssertionError(
                "the chip grid's own layout box changed on selection: %r -> %r"
                % (before["grid"], after["grid"]))
        if before["all"] != after["all"]:
            moved = [
                (i, b, a) for i, (b, a)
                in enumerate(zip(before["all"], after["all"])) if b != a]
            raise AssertionError(
                "chips MOVED inside the grid when one of them was selected - "
                "siblings shifting is the visible half of T6, and it is exactly "
                "what a border-width or padding-based selection signal does. "
                "[index, before [w,h,left,top], after]: %r" % (moved,))
    finally:
        context.close()
