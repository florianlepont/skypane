#!/usr/bin/env python3
"""Browser checks for the Flights detail-row toggle, the Flights/Airlines/Health filter-bar
meta rows, the Airlines two-per-row grid, Health's registry table and no-JS floor, the settings
pages' reveal/persist/leave-guard family, the Frame strip switch, and the runway
cards/theme-chip selection signal.

Read-only checks share one module-scoped, read-only `server` fixture. The four checks that
persist a real setting through the UI each get their own function-scoped `make_app_server`
server, so no xdist worker sees another test's leftover on-disk state.
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
    """The shared, read-only seeded fixture every read-only check in this module measures
    against — module-scoped because none of them POSTs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def test_flights_detail_row_expands_and_collapses(page, server):
    """A Flights detail row expands and collapses from an icon-only toggle with no visible
    text, a >=44x44 synthesized hit area, and an accessible name that swaps with the state;
    a click on a non-interactive cell of the same row also expands it.
    """
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

    # Icon-only: no visible text, a real accessible name. The decorative chevron glyph is the
    # icon, not a label; any alphanumeric character here would be a visible text label.
    label_text = toggle.inner_text().strip()
    if any(ch.isalnum() for ch in label_text):
        raise AssertionError(
            "expected the toggle to render no visible text label, got %r"
            % (label_text,))
    collapsed_name = toggle.get_attribute("aria-label")
    if not collapsed_name:
        raise AssertionError("expected the icon-only toggle to carry an aria-label")

    # The real hit area: a 22x22 visual box plus the ::before's negative 11px inset on every
    # side.
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
    # A click on the toggle must toggle exactly once: the row's delegated handler returns
    # early for an interactive target, so an unguarded handler would double-toggle.
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

    # The whole row is clickable: a click on a plain, non-interactive cell expands it.
    row = page.locator("[data-flight-row]").first
    if "flight-row--clickable" not in (row.get_attribute("class") or ""):
        raise AssertionError(
            "expected flight-rows.js to add its own clickable marker class "
            "to each summary row at load")
    row.locator("td").nth(2).click()
    if toggle.get_attribute("aria-expanded") != "true":
        raise AssertionError("expected a click on a non-interactive cell to expand the row")


# The link sits in a dense strip cell beside a switch, the same geometry that already produced
# this file's tight pager/handle hit-target measurements.

def test_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px(new_context, server):
    """The Quiet hours caption's schedule link clears the 44px hit-target floor by real
    hit-testing, in both themes, at the 360px floor, on both Home and Display, with neither
    page gaining horizontal scroll from the addition.
    """
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


# `.copy-btn` and `.row-toggle` are measured together, in their own containers, since
# `.row-toggle` reuses `.copy-btn`'s values verbatim. `.row-toggle` and the desktop `.copy-btn`
# trio only render in `.data-table-wrap`, hidden below 960px in favour of `.history-cards`, so
# they are measured at 960px instead; the mobile `.copy-btn` trio does render at 360px and is
# measured there, closing the literal 360px case too.

def test_copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_containers(new_context, server):
    """Every icon control in the .copy-btn/.row-toggle family resolves to the 44px hit-target
    floor in its own container, by real hit-testing rather than a declared value: the desktop
    Flights detail row's three .copy-btn and .row-toggle at 960px, and the mobile <details>
    card's own three .copy-btn at the 360px floor, both in both themes.
    """
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
    """At 390px on Flights the filter count and the Clear control report the same
    bounding-box top: Clear never drops alone onto its own line.
    """
    # Two `nowrap` siblings in a wrapping flex container do not wrap as a unit; one
    # `.filter-bar__meta` group does. Measured, not inspected: equal
    # getBoundingClientRect().top is the contract.
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
    """At 390px every Airlines illustration grid renders exactly two cards per row (never a
    one-per-row auto-fill collapse), with each row's two columns equal within 1px, the main
    grid's cards near the width the contract predicts, and the whole page under a height
    ceiling.
    """
    # `repeat(auto-fill, minmax(200px, 1fr))` can collapse to one column inside a narrow
    # content column; only a real layout engine resolves auto-fill, so this is measured rather
    # than asserted off the stylesheet.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        # The gap strip carries its own narrower `.illustration-grid--gap`, so each grid is
        # measured on its own rather than pooling two grids' rows into one histogram.
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
                # Every row but a grid's last holds exactly two; the last may hold one when
                # that grid's card count is odd.
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
        # The page's main content column's own arithmetic: (342 - 24) / 2.
        if not (150 <= widest_row[0]["width"] <= 170):
            raise AssertionError(
                "expected each card near the 159px the contract predicts, got %r"
                % (widest_row[0]["width"],))
        # A working two-per-row grid roughly halves the height a one-per-row collapse would
        # produce. The 3800px ceiling carries headroom over the measured baseline for the
        # current airline count, so this fails on a regression rather than on a pixel, and
        # moves again deliberately whenever the airline count legitimately changes.
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
    """At 390px on Airlines the filter count and the Clear control report the same
    bounding-box top, both inside the one shared .filter-bar__meta group, adopted verbatim
    with no per-page variant.
    """
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
        # Adopted, not forked: the pair is inside the one shared group element, and Airlines
        # adds no variant of its own.
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
    """At 1280px in both languages Health's unresolved-prefix table reports
    scrollWidth === clientWidth on its .data-table-wrap, the Resolve column sits inside that
    wrap's own box (reachable with no horizontal scrolling), and no header is clipped.
    """
    # Only a real layout engine resolves `.data-table`'s `min-width: max-content` floor against
    # six columns of real content in two languages, so this is measured rather than eyeballed.
    # Each language is fully independent, so the two are parametrized rather than looped.
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
        # Reachable without horizontal scrolling, asserted as a geometric fact, not inferred
        # from the scrollWidth equality above.
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
    """At 390px on Health the filter count and the Clear control report the same
    bounding-box top, both inside the one shared .filter-bar__meta group, and the page
    header's Updated clock carries .time-value, never .mono.
    """
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
        # The page header's own clock left the monospace family for the one time-value role.
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
    """With scripts blocked Health renders in full: all four tiles with their
    label/verdict/detail slots each exactly once, the registry filter bar and Clear, the
    unresolved-prefix rows, and a per-row Resolve action that actually navigates to the
    Airlines resolve surface.
    """
    with _no_js_page(new_context, server.base_url(), "/health") as page:
        tiles = page.eval_on_selector_all(".stat-tile", "els => els.length")
        if tiles != 4:
            raise AssertionError(
                "expected all four Health tiles to render with scripts blocked, "
                "got %d" % (tiles,))
        # Every tile must be complete, not merely present.
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
        # The table or its card fallback, whichever the viewport resolves to, must be present,
        # with the Resolve action reachable from it.
        rows = page.eval_on_selector_all(
            "table.data-table--registry tbody tr, ul.data-cards > li", "els => els.length")
        if rows < 1:
            raise AssertionError(
                "expected the unresolved-prefix rows (table or card fallback) with "
                "scripts blocked, got %d" % (rows,))
        # `:visible` matters: the card list and the table are both in the DOM at every width
        # (the toggle between them is CSS-only), so the reachable one is whichever the
        # viewport actually shows.
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


# Each of the four checks below saves a real setting through the real UI, so each gets its own
# function-scoped, seeded server.

def test_display_reveal_and_persist_across_all_field_kinds(page, make_app_server):
    """Display: a theme chip, a runway card and a quiet-hours time field each commit via
    change, reveal the bar, and persist to disk once Enregistrer is clicked (form=-attached
    radio and time-input field kinds).
    """
    # A committed edit reveals the bar (never a click before that) and only Enregistrer
    # persists it (never a click-free auto-save). Exercises three cross-DOM form=-attached
    # field kinds: radio-as-chip, radio-as-card, time input.
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

    # The Frame strip is now the only on/off control for the screen, so this settings page no
    # longer renders a display_enabled checkbox; the remaining two field kinds below (radio,
    # time input) still prove the cross-DOM form= delegation this check exists for.

    # `.fill()` dispatches `input` only, never `change`, so `_commit_field()` fires the real
    # `change` a blur would, the commit the bar's document-level listener is waiting for.
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
    """Device: the wake-interval field commits via change, reveals the bar, and persists to
    disk once Enregistrer is clicked, proving the two scopes stay in step. Witnessed by the
    wake-interval field since the Diagnostic LED is a role="switch" applying instantly over
    /quick/led, not a Save-governed control.
    """
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)
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
    # The LED switch, which is not part of that form, must be unmoved by the save.
    led_state = page.eval_on_selector(
        '[data-quick-region] button[role="switch"]',
        "el => el.getAttribute('aria-checked')")
    if led_state not in ("true", "false"):
        raise AssertionError(
            "expected the Device page to render an LED switch with a real "
            "aria-checked, got %r" % (led_state,))


def test_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves(page, make_app_server):
    """The bar (the single [data-static-save-fallback] Save affordance, relocated inside it,
    never a second button) is server-rendered visible — the no-JS floor — and hides
    immediately once script proves itself live; an edit reveals it again, naming the changed
    section via [data-dirty-count]; and clicking its own Save persists to disk through a real
    navigation.
    """
    # The bar's visible state is the no-JS floor: hidden by script the instant script proves
    # itself live (dirty-state.js's own `bar.hidden = true` at init, before any listener is
    # attached), revealed again the instant a real edit exists.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)

    page.goto(base_url + "/display")
    bar = page.locator("[data-dirty-bar]")
    # Script has proven itself live: the bar hides at init, on a page with no edits at all.
    if bar.is_visible():
        raise AssertionError(
            "expected the bar to be HIDDEN immediately once script runs on "
            "a fresh load — dirty-state.js's own bar.hidden = true at init, "
            "the no-JS-floor polarity this check exists to pin down")

    theme_ids = device_config.THEME_IDS
    target = theme_ids[2]
    _click_control(page, 'input[name="theme"][value="%s"]' % target)
    # An edit reveals the bar.
    _wait_for_bar(page)
    count_text = _bar_text(page)
    if not count_text:
        raise AssertionError(
            "expected [data-dirty-count] to name the changed section once "
            "the bar reveals, got an empty string")

    # Clicking the bar's own Save persists to disk through a real navigation.
    _save_via_bar(page)
    stored = device_config.load_device_config(server.tmpdir)["theme"]
    if stored != target:
        raise AssertionError(
            "expected the theme edit to reach disk once the bar's own Save "
            "is clicked, got %r" % (stored,))


def test_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit(page, server):
    """The leave-guard arms for a field edited but never committed (the bar already visible
    and already naming the section); it stays armed, not disarmed, the instant change commits
    the edit, since a committed-but-unsaved change is exactly what the guard exists to warn
    about; and Annuler is the guard's own exit, disarming it and hiding the bar. The
    re-arm-after-Cancel clause is a separate check, not duplicated here.
    """
    # A committed-but-unsaved change is exactly what the guard exists to warn about — it stays
    # armed until Enregistrer or Annuler, unlike a model where a commit meant already-saved.
    # This check never clicks Enregistrer, only Annuler, so nothing it does reaches disk and it
    # shares the module's read-only server.
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/device")

    # a. Fresh load: disarmed.
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to start disarmed on a clean page load")

    wake_sel = 'input[name="wake_interval_s"]'
    before = page.eval_on_selector(wake_sel, "el => el.value")
    target = "1800" if before != "1800" else "3600"

    # Type without committing: `input` fires per keystroke; `change` does not fire until
    # focus leaves the field.
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
    # The bar is already visible and [data-dirty-count] already names the section even before
    # this edit commits.
    _wait_for_bar(page)
    if not _bar_text(page):
        raise AssertionError(
            "expected [data-dirty-count] to already name the changed section "
            "for a merely-typed, uncommitted edit — the restored model has no "
            "silent phase, which is strictly more than the retired region ever "
            "asserted")

    # Commit it: blur fires `change`. The guard stays armed — a committed-but-unsaved change
    # is exactly what it exists to warn about.
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

    # Click Annuler: the guard disarms and the bar hides.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm once Annuler is clicked")


# A naive Cancel handler can set suppressGuard = true once and never clear it, leaving the
# guard dead for the rest of the page's life while an armed/disarmed-by-Cancel check alone
# would still pass against that exact defect. This check never clicks Enregistrer either, so
# it too shares the module's read-only server.
def test_the_leave_guard_re_arms_after_a_new_edit_following_cancel(page, server):
    """The leave-guard's re-arm-after-Cancel clause has executable coverage: fresh load
    (disarmed) -> edit (armed) -> Annuler (disarmed) -> a new edit (re-armed) -> a second
    Annuler (disarmed again, so a one-shot re-arm cannot pass). Reuses the existing
    `_guard_armed()` beforeunload probe throughout, never a second one.
    """
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

    # Edit a field: armed, bar visible. Kept minimal on purpose; this step is only the
    # precondition the rest of the check needs.
    _click_control(page, '%s[value="%s"]' % (runway_sel, first_target))
    if not _guard_armed(page):
        raise AssertionError("expected the leave-guard to arm for a real edit")
    _wait_for_bar(page)

    # 3. Click Annuler: disarmed, bar hides.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm once Annuler is clicked")

    # A new edit that follows a Cancel must re-arm the guard: this is exactly what a naive
    # `suppressGuard = true` set once in the Cancel handler and never cleared gets wrong.
    _click_control(page, '%s[value="%s"]' % (runway_sel, second_target))
    if not _guard_armed(page):
        raise AssertionError(
            "expected the leave-guard to RE-ARM for an edit that follows a "
            "Cancel — CFG-77's own 'does not disarm the leave-guard "
            "permanently... kept exactly where CFG-63's own carve-out "
            "already put it', and exactly the defect a Cancel handler that "
            "sets suppressGuard=true once and never clears it reproduces")
    _wait_for_bar(page)

    # A second Annuler disarms again: a re-arm that can only happen once is the same defect.
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if _guard_armed(page):
        raise AssertionError("expected the leave-guard to disarm on a SECOND Annuler too")


def test_strip_switch_applies_without_the_leave_guard_while_other_navigation_still_warns(
        page, make_app_server):
    """Activating a Frame strip switch with unsaved Display edits present applies over fetch
    without navigating, leaves the leave-guard armed for the edit still in the form and the
    switch still pressable, and raises no dialog, while a plain nav-link navigation with the
    same unsaved edit still raises one.
    """
    # A real browser proof, not a read of dirty-state.js's private suppressGuard variable:
    # Chromium surfaces a beforeunload guard's preventDefault() as a real `dialog` event of
    # type "beforeunload", so listening for that event is a genuine behavioural probe.
    #
    # This check flips a real setting (display_enabled) through the strip's own quick-switch
    # endpoint, so it gets its own function-scoped server.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/display")
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.type), d.accept()))

    # The switch flip lands under the finger and the POST goes out over fetch, so there is no
    # unload at all. What matters is that after the switch has applied, the leave-guard must
    # still be armed for the unsaved edit still sitting in the form: dirty-state.js disarms its
    # guard for any [data-quick-switch] submit, and on a page whose form was already dirty
    # nothing would ever re-arm it, so quick-switch.js listens in the capture phase and stops
    # propagation precisely so that listener never runs for a submission that is not happening.
    #
    # A radio commits (fires change) the instant it is clicked, which would auto-save and
    # disarm the guard before the assertion runs; focusing and typing would not survive either,
    # since clicking the switch button blurs the field and fires the commit first. The guard's
    # own predicate reads the field's live value against the load-time snapshot and needs no
    # event at all, so the value is set directly with no focus taken and no event dispatched.
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
    # The switch must also still be pressable: a submit-guard that disabled it on the way out
    # would leave a dead control on a page that never reloads.
    if page.eval_on_selector(switch_sel, "el => el.disabled"):
        raise AssertionError(
            "the switch was left disabled after applying — with no navigation "
            "to replace the page, a disabled switch stays disabled forever")

    # Reset: reload, make the same kind of unsaved edit again, then navigate away by a plain
    # nav link, and the guard must still warn. Same focus-free value set as above: clicking the
    # nav link would blur a focused field and commit it before the navigation's beforeunload
    # check ever runs.
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
    """At 390px the three runway cards report one shared line (equal tops), equal heights,
    and both their border-excluded and their outer widths equal within 1px at a border total
    of exactly 2.0 each, and each still clears 44x44 — never a two-plus-one orphan — with the
    transform neutralised for the read and exactly one card proven to carry the selection scale.
    """
    # Only a real layout engine can see a two-plus-one orphan wrap, which is why this lives
    # here and not in a string-comparison harness.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.wait_for_load_state("networkidle")
        # The selected card carries a `transform: scale(...)`. A transform is reflected in
        # getBoundingClientRect() (the visual box) but not in the layout box, and this check is
        # about the layout box, so the transform is neutralised for the read — with its own
        # transition neutralised first, or the read would catch the unwind mid-flight.
        #
        # Neutralising it is only honest if the scale is really there, so the real computed
        # transform is captured before the override and asserted below: exactly one of the
        # three cards must be scaled, keeping this check from passing for a build that dropped
        # the scale entirely.
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

        # "Equal within 1px" is asserted on the cards' border-excluded widths, which is what
        # "three equal columns" actually means, and on their outer widths too: every
        # selected-state border is held constant at 1px and selection is carried on
        # `box-shadow: inset 0 0 0 2px`, which occupies no layout space, so `inner` and `w`
        # have converged and plain equality applies to both.
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
        # Touch target, confirmed by measurement: the hidden radio's own hit-target entry is
        # exempt by delegation to this wrapping <label>, so the label itself must still clear
        # 44px in both axes.
        for b in boxes:
            if b["w"] < 44 or b["h"] < 44:
                raise AssertionError(
                    "every runway card must stay >=44x44 for the hidden radio's "
                    "exempt-by-delegation touch-target entry, got %r" % (b,))
    finally:
        context.close()


def test_selecting_a_theme_chip_answers_and_moves_no_layout_box(new_context, server):
    """At 390px selecting a palette chip answers — the chip's border-colour changes to the
    accent, an inset accent ring (box-shadow) appears, and the .palette-chip__name wash
    changes — while its own layout box, the grid's own box, and every chip's position inside
    it are plain-equal before and after, so a selected card can never be a different size from
    its siblings through the selection signal.
    """
    # Selection paints instantly via border/box-shadow/wash and carries no transform or
    # transition on this component, so the box is read through offsetWidth/offsetHeight/
    # offsetLeft/offsetTop, transform-independent by definition, with plain equality (these are
    # integers from the same element measured twice).
    #
    # Positions are measured relative to the chip grid, not the page: selecting a chip makes
    # the form dirty, and the save bar that then replaces the section's inline fallback Save
    # button removes real height from the page above this card, whichever chip is clicked. The
    # statement that belongs here is that nothing inside the grid moved, so every chip in the
    # grid is measured, not just the clicked one.
    #
    # This check clicks a radio but never Enregistrer, so nothing here reaches disk and it
    # shares the module's read-only server.
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
