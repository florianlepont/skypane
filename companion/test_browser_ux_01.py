#!/usr/bin/env python3
"""Browser checks for the Flights row-level picture action, the Flights/Airlines/Health filter-bar
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
    _bar_text, _click_control, _commit_field,
    _guard_armed, _login, _no_js_page, _save_via_bar, _wait_for_bar, _wait_for_bar_hidden, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only seeded fixture every read-only check in this module measures
    against — module-scoped because none of them POSTs.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


LIGHTBOX = "#panel-lookup-dialog"


def _tab_to(page, selector, limit=80):
    """Press Tab from the top of the page until `selector` holds focus, or fail."""
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    for _ in range(limit):
        page.keyboard.press("Tab")
        if page.evaluate("(sel) => document.activeElement === document.querySelector(sel)", selector):
            return
    raise AssertionError("expected Tab to reach %r within %d presses" % (selector, limit))


def test_flights_picture_action_opens_by_keyboard_and_pointer(new_context, server):
    """Every Flights row carries one direct "View picture" link: it takes visible keyboard
    focus, Enter opens the shared lightbox dialog with that row's own picture, Escape closes
    it and returns focus to the link, and a pointer click does the same.
    """
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        rows = page.locator("table.data-table--flights tr[data-flight-row]")
        links = page.locator("table.data-table--flights a[data-view-panel-src]")
        rows.first.wait_for(state="visible")
        if links.count() != rows.count() or rows.count() < 2:
            raise AssertionError(
                "expected one picture link per rendered flight row, got %d links for %d rows"
                % (links.count(), rows.count()))
        for retired in ("[data-row-toggle]", "tr.flight-detail-row", "[data-copy-value]",
                        ".data-table-wrap [aria-expanded]"):
            if page.locator(retired).count():
                raise AssertionError("did not expect %r on the simplified Flights page" % retired)

        first_selector = "table.data-table--flights tr[data-flight-row] a[data-view-panel-src]"
        link = links.first
        expected_src = link.get_attribute("data-view-panel-src")
        name = link.get_attribute("aria-label")
        if not name or not name.startswith("View picture of "):
            raise AssertionError("expected the link to name its flight, got %r" % (name,))

        _tab_to(page, first_selector)
        outline = link.evaluate(
            "el => [getComputedStyle(el).outlineStyle, parseFloat(getComputedStyle(el).outlineWidth)]")
        if outline[0] == "none" or outline[1] < 1:
            raise AssertionError("expected a visible focus outline on the picture link, got %r" % (outline,))
        page.keyboard.press("Enter")
        dialog = page.locator(LIGHTBOX)
        dialog.wait_for(state="visible")
        if dialog.evaluate("el => el.open") is not True:
            raise AssertionError("expected Enter on the picture link to open the dialog")
        if not dialog.get_attribute("aria-label"):
            raise AssertionError("expected the dialog to carry an accessible name")
        shown = dialog.locator("img.lightbox__image").get_attribute("src")
        if shown != expected_src:
            raise AssertionError("expected the dialog to show %r, got %r" % (expected_src, shown))
        page.keyboard.press("Escape")
        if dialog.evaluate("el => el.open"):
            raise AssertionError("expected Escape to close the dialog")
        if not page.evaluate("(sel) => document.activeElement === document.querySelector(sel)", first_selector):
            raise AssertionError("expected focus to return to the picture link after closing")

        links.nth(1).click()
        if not dialog.evaluate("el => el.open"):
            raise AssertionError("expected a pointer click on the picture link to open the dialog")
        if page.url.endswith(".png") or "/gallery/" in page.url:
            raise AssertionError("expected the script to keep the page in place, not follow the link")
    finally:
        context.close()


def test_flights_mobile_cards_each_carry_a_picture_action_at_390_and_360(new_context, server):
    """At 390 and 360 px every phone card shows its picture link inside the card, at the 44px
    tap floor, with no horizontal page scroll, in English and in French.
    """
    for lang, label in (("en", "View picture"), ("fr", "Voir l\u2019image")):
        for viewport in (VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED):
            context = new_context(viewport=viewport)
            try:
                context.add_cookies([{
                    "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
                page = context.new_page()
                _login(page, server.base_url())
                page.goto(server.base_url() + "/flights")
                cards = page.locator("li.history-card")
                cards.first.wait_for(state="visible")
                where = "%s at %dpx" % (lang, viewport["width"])
                if not cards.count():
                    raise AssertionError("expected phone cards (%s)" % where)
                measured = page.evaluate(
                    "() => [...document.querySelectorAll('li.history-card')].map(li => {"
                    "  const a = li.querySelector('a[data-view-panel-src]');"
                    "  if (!a) return null;"
                    "  const r = a.getBoundingClientRect(), c = li.getBoundingClientRect();"
                    "  return {text: a.textContent.trim(), w: r.width, h: r.height,"
                    "          inside: r.left >= c.left - 0.5 && r.right <= c.right + 0.5,"
                    "          label: a.getAttribute('aria-label')};"
                    "})")
                for index, item in enumerate(measured):
                    if item is None:
                        raise AssertionError("card %d has no picture link (%s)" % (index, where))
                    if item["text"] != label or not item["label"].startswith(label):
                        raise AssertionError(
                            "card %d link reads %r / %r, expected %r (%s)"
                            % (index, item["text"], item["label"], label, where))
                    if not item["inside"] or item["h"] < 44:
                        raise AssertionError(
                            "card %d link is clipped or under 44px tall: %r (%s)"
                            % (index, item, where))
                if page.evaluate(
                        "document.documentElement.scrollWidth > document.documentElement.clientWidth"):
                    raise AssertionError("expected no horizontal page scroll (%s)" % where)
                if page.locator("li.history-card details, li.history-card summary").count():
                    raise AssertionError("did not expect a card disclosure (%s)" % where)
                cards.first.locator("a[data-view-panel-src]").click()
                if not page.locator(LIGHTBOX).evaluate("el => el.open"):
                    raise AssertionError("expected a tap on the card link to open the dialog (%s)" % where)
            finally:
                context.close()


def test_flights_picture_link_works_without_scripts(new_context, server):
    """With scripts blocked the picture action is still a real link: following it serves the
    archived render, not a script-only path.
    """
    with _no_js_page(new_context, server.base_url(), "/flights") as page:
        link = page.locator("table.data-table--flights a[data-view-panel-src]").first
        link.wait_for(state="visible")
        href = link.get_attribute("href")
        if not href or not href.startswith("/gallery/"):
            raise AssertionError("expected a real /gallery/ href, got %r" % (href,))
        response = page.goto(server.base_url() + href)
        if response is None or response.status != 200 or "image/png" not in response.headers.get("content-type", ""):
            raise AssertionError("expected the link to serve the archived PNG, got %r" % (response,))


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
        # produce. The 6600px ceiling carries headroom over the measured baseline (about
        # 6200px with every card showing its source and owner rows plus its action) for the
        # current airline count, so this fails on a regression rather than on a pixel, and
        # moves again deliberately whenever the airline count legitimately changes.
        height = page.evaluate("document.documentElement.scrollHeight")
        if height > 6600:
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
    """At 390px selecting a cell of the departures look table answers — the cell's border-colour
    changes to the accent, an inset accent ring (box-shadow) appears, and its wash changes —
    while its own layout box, the table's own box, and every cell's position inside it are
    plain-equal before and after, so a selected cell can never be a different size from its
    siblings through the selection signal.
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
        # The table is the no-script control; open its disclosure directly, since with scripts
        # its summary opens the look sheet instead.
        page.eval_on_selector(
            '[data-look-usage="departures"] details.look-edit', "d => { d.open = true; }")

        probe = (
            "() => {"
            "const row = document.querySelector("
            "'[data-look-usage=\"departures\"] details.look-edit');"
            "if (!row) return {error: 'no departures table'};"
            "const chips = [...row.querySelectorAll('label.look-cell')]"
            ".filter(c => c.querySelector('input[type=radio]'));"
            "if (chips.length < 2) return {error: 'chips: ' + chips.length};"
            "const target = chips.find("
            "c => !c.querySelector('input[type=radio]').checked);"
            "if (!target) return {error: 'every chip is already checked'};"
            "const grid = target.closest('.look-table');"
            "if (!grid) return {error: 'no .look-table'};"
            "const read = e => { const s = getComputedStyle(e);"
            "const ns = s;"
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
                "could not find an unchecked table cell: %s" % (before["error"],))
        value = before["value"]
        _click_control(
            page,
            '[data-look-usage="departures"] details.look-edit '
            'label.look-cell input[type=radio][value="%s"]' % value)
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
                "expected an UNSELECTED table cell to carry no box-shadow, got "
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
                "expected the selected cell's wash to change "
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
