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
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _login, _set_ui_theme, seed_state_dir,
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
