#!/usr/bin/env python3
"""Browser checks of the Flights search, empty state, sort and Load more. Tapping the search
icon turns the title row into the field in place, so the direction control and the list keep the
same top at 360 and 390 px in English and French (the field covers exactly the 44px title row);
the field closes again once empty and blurred. The search covers the whole history (an old call
sign beyond the first page is found); a search that matches nothing shows the empty card with
plain chips, no table header and no Load more, on the phone and the desktop. With more
flights stored than one page shows, Load more appends the next flights in place (same document,
same scroll position, focus on the first new row, the address updated), the sort changes the
order and survives Load more, and without scripts the plain links still work and land on the
first new row of the list the viewport shows. The Airlines collection answers a search that
matches nothing with the same empty card.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.pages import history_page
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow, _login,
    _no_js_page,
)

pytestmark = pytest.mark.browser

LIMIT = history_page.HISTORY_ROW_LIMIT
TOTAL = LIMIT + 20
LOTS = 2 * LIMIT + 20
OLDEST = "AFR100"
CARD = "li.history-card"
MORE = "a.history-more__link:visible"
FIELD = "[data-flights-search]"
ROW = "tr[data-flight-row]"
EMPTY = "[data-flights-empty]"
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
_TOPS = (
    "() => { const top = (s) => document.querySelector(s).getBoundingClientRect().top;"
    " return {chips: top('.filter-bar--chips'), card: top('li.history-card'),"
    "  header: document.querySelector('.page-header').getBoundingClientRect().height}; }")




def _seed_flights(state_dir, count):
    """`count` Air France departures, five minutes apart on 3 Sep 2026 (newest last seeded);
    the oldest is AFR100."""
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-09-03T%02d:%02d:00+00:00" % (hour, minute),
         "hex": "4c%04x" % (hour * 60 + minute), "callsign": "AFR%d" % (100 + hour * 60 + minute),
         "airline": "Air France", "origin": "ORY", "destination": "NCE",
         "confirmed_state": "departing"}
        for hour in range(12) for minute in range(0, 60, 5)][:count])


@pytest.fixture(scope="module")
def many(module_app_server_factory):
    return module_app_server_factory(seed=lambda d: _seed_flights(d, TOTAL), fake_providers=True)


@pytest.fixture(scope="module")
def lots(module_app_server_factory):
    return module_app_server_factory(seed=lambda d: _seed_flights(d, LOTS), fake_providers=True)


def _seed_two_days(state_dir):
    """LIMIT flights on 4 Sep and six older ones on 3 Sep: Load more adds a new day."""
    events = [
        {"ts": "2026-09-04T%02d:%02d:00+00:00" % (n // 12, n % 12 * 5),
         "hex": "4d%04x" % n, "callsign": "AFR%d" % (200 + n), "airline": "Air France",
         "origin": "ORY", "destination": "NCE", "confirmed_state": "departing"}
        for n in range(LIMIT)]
    events += [
        {"ts": "2026-09-03T10:%02d:00+00:00" % (n * 5), "hex": "4e%04x" % n,
         "callsign": "AFR%d" % (900 + n), "airline": "Air France", "origin": "ORY",
         "destination": "NCE", "confirmed_state": "departing"} for n in range(6)]
    vp.seed_runway_events(state_dir, events)


@pytest.fixture(scope="module")
def two_days(module_app_server_factory):
    return module_app_server_factory(seed=_seed_two_days, fake_providers=True)


@pytest.fixture(scope="module")
def few(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


@pytest.fixture(scope="module")
def bare(module_app_server_factory):
    return module_app_server_factory(
        seed=lambda d: vp.seed_flight_card_variety(d, with_gallery=False), fake_providers=True)


def _open(new_context, server, viewport, lang="en", route="/flights"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(ROW if viewport["width"] >= 960 else CARD).first.wait_for(state="visible")
    # The cross-document view transition has ended once the list owns its own centre.
    page.wait_for_function(
        "() => { const e = document.querySelector('li.history-card, tr[data-flight-row]');"
        " const r = e.getBoundingClientRect(); const t = document.elementFromPoint("
        "r.left + r.width / 2, r.top + Math.min(r.height / 2, 10));"
        " return !!t && t !== document.documentElement; }", timeout=15000)
    return context, page


def _count(page, selector):
    return page.evaluate("(s) => document.querySelectorAll(s).length", selector)


def _wait_count(page, selector, expected):
    page.wait_for_function(
        "([s, n]) => document.querySelectorAll(s).length === n", arg=[selector, expected],
        timeout=10000)


def _first_callsign(page):
    return page.evaluate(
        "() => (document.querySelector('li.history-card .history-card__callsign') || {})"
        ".textContent")


def _choose_sort(page, value):
    """Open the sort menu and pick one order, the way a finger does."""
    page.locator(".collection-sort > summary").click()
    page.locator('.collection-sort__option:has(input[value="%s"])' % value).click()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["phone", "desktop"])
def test_back_after_a_first_search_shows_the_full_list(new_context, many, viewport):
    """the first search gets a history entry of its own, so Back returns to the list as it
    was and does not leave Flights"""
    context, page = _open(new_context, many, viewport)
    try:
        start = page.url
        page.evaluate("() => { window.__marker = 'same document'; }")
        page.locator(FIELD).evaluate("el => el.closest('form').scrollIntoView()")
        if viewport["width"] < 960:
            page.locator(FIELD).click()
        page.fill(FIELD, "AFR1")
        page.wait_for_function("() => location.search.indexOf('q=AFR1') >= 0", timeout=10000)
        page.press(FIELD, "Enter")
        page.wait_for_function("() => location.search.indexOf('q=AFR1') >= 0", timeout=10000)
        page.go_back()
        page.wait_for_function(
            "() => location.search.indexOf('q=') < 0 && document.readyState === 'complete'",
            timeout=10000)
        assert page.url == start
        page.wait_for_function(
            "(n) => document.querySelectorAll('li.history-card, tr[data-flight-row]').length >= n",
            arg=10, timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_search_opens_in_the_title_row_without_moving_the_list(new_context, few, viewport, lang):
    context, page = _open(new_context, few, viewport, lang)
    try:
        before = page.evaluate(_TOPS)
        icon = page.locator(FIELD).bounding_box()
        assert icon["width"] >= 44 - 0.5 and icon["height"] >= 44 - 0.5, icon
        page.click(FIELD)
        page.wait_for_function(
            "() => document.querySelector('.filter-bar--title').getBoundingClientRect().width"
            " > 200", timeout=5000)
        assert page.evaluate(_TOPS) == before
        field = page.locator(".filter-bar--title").bounding_box()
        header = page.locator(".page-header").bounding_box()
        assert abs(field["y"] - header["y"]) <= 0.5 and abs(field["height"] - 44) <= 0.5, (
            field, header)
        page.keyboard.type("tvf")
        page.wait_for_function(
            "() => document.querySelector('[data-flights-search]').value === 'tvf'", timeout=5000)
        # The answer replaces the list under the field, which keeps its place.
        _wait_count(page, CARD, 1)
        page.click(".filter-bar--title [data-flights-clear]")
        page.wait_for_function(
            "() => document.querySelector('[data-flights-search]').value === ''", timeout=5000)
        _wait_count(page, CARD, len(vp.FLIGHT_CARD_FLIGHTS))
        page.locator(".page-title").click(force=True)
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.wait_for_function(
            "() => document.querySelector('.filter-bar--title').getBoundingClientRect().width"
            " <= 48", timeout=5000)
        assert page.evaluate(_TOPS) == before
        assert not _assert_no_page_overflow(page, "flights search", viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_load_more_appends_in_place_keeping_the_scroll_and_the_focus(
        new_context, many, viewport, lang):
    """Load more does not navigate: a marker on window survives, the scroll position is the
    one it was at, the next flights join both lists, the shown-count and address follow, the
    button goes with the last page and the first new row takes the focus."""
    context, page = _open(new_context, many, viewport, lang)
    try:
        assert _count(page, CARD) == LIMIT and _count(page, ROW) == LIMIT
        assert str(LIMIT) in page.locator(".history-more__count").inner_text()
        link = page.locator(MORE)
        assert link.bounding_box()["height"] >= 44 - 0.5
        assert link.inner_text() == ("Load more" if lang == "en" else "Charger plus")
        link.scroll_into_view_if_needed()
        page.evaluate("() => { window.__marker = 'same document'; window.scrollBy(0, 40); }")
        page.wait_for_function("() => window.scrollY > 0")
        before = page.evaluate("() => window.scrollY")
        link.click()
        _wait_count(page, CARD, TOTAL)
        _wait_count(page, ROW, TOTAL)
        assert page.evaluate("() => window.__marker") == "same document"
        assert abs(page.evaluate("() => window.scrollY") - before) <= 1
        assert page.locator(MORE).count() == 0
        assert page.locator("[data-history-more]").count() == 0
        assert page.url.endswith("/flights?more=1"), page.url
        assert page.evaluate("() => document.querySelectorAll('#flights-new').length") == 1
        anchor = "flights-new" if viewport["width"] >= 960 else "flights-new-card"
        assert page.evaluate(
            "(s) => [...document.querySelectorAll(s)].indexOf(document.getElementById('%s'))"
            % anchor, ROW if viewport["width"] >= 960 else CARD) == LIMIT
        page.wait_for_function(
            "(id) => document.activeElement && document.activeElement.id === id", arg=anchor,
            timeout=5000)
        # The new rows continue the day group and the table instead of repeating them.
        assert _count(page, "section.history-day") == 1
        assert _count(page, "tr.flight-day-row") == 1
    finally:
        context.close()


def test_load_more_animates_the_new_rows_never_a_whole_day_section(new_context, two_days):
    """a day that Load more adds is not lifted as one tall block: only its first rows enter"""
    context, page = _open(new_context, two_days, VIEWPORT_PHONE)
    try:
        page.evaluate("""() => {
          window.__entered = [];
          new MutationObserver((records) => {
            for (const r of records) {
              if (r.target.classList.contains('reveal-appended')) {
                window.__entered.push(r.target.tagName + '.' + r.target.className);
              }
            }
          }).observe(document.body, {subtree: true, attributes: true, attributeFilter: ['class']});
        }""")
        link = page.locator(MORE)
        link.scroll_into_view_if_needed()
        link.click()
        _wait_count(page, CARD, LIMIT + 6)
        page.wait_for_function(_SETTLED, timeout=10000)
        entered = page.evaluate("() => window.__entered")
        assert entered, "the new rows should enter with the short entrance"
        assert not [name for name in entered if "history-day" in name or "SECTION" in name], entered
        assert all(name.startswith("LI.") for name in entered), entered
    finally:
        context.close()


def test_load_more_keeps_its_button_and_focus_while_flights_remain(new_context, lots):
    context, page = _open(new_context, lots, VIEWPORT_PHONE)
    try:
        link = page.locator(MORE)
        link.focus()
        link.click()
        _wait_count(page, CARD, 2 * LIMIT)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('a.history-more__link')")
        assert page.url.endswith("/flights?more=1")
        assert str(2 * LIMIT) in page.locator(".history-more__count").inner_text()
        page.locator(MORE).click()
        _wait_count(page, CARD, LOTS)
        assert page.locator(MORE).count() == 0
        assert page.url.endswith("/flights?more=2")
    finally:
        context.close()


@pytest.mark.parametrize("viewport,anchor", [
    (VIEWPORT_PHONE, "flights-new-card"), (VIEWPORT_DESKTOP, "flights-new")],
    ids=["390", "1280"])
def test_load_more_works_without_scripts_and_lands_on_the_first_new_row(
        new_context, many, viewport, anchor):
    """With scripts blocked the plain link loads the next page and the browser lands on the first
    new row of the list the viewport shows (on the desktop too: the anchor is on the table row)."""
    with _no_js_page(new_context, many.base_url(), "/flights", viewport=viewport) as page:
        selector = ROW if viewport["width"] >= 960 else CARD
        assert _count(page, selector) == LIMIT
        page.click(MORE)
        page.wait_for_url("**/flights?more=1*")
        assert _count(page, selector) == TOTAL
        assert page.locator(MORE).count() == 0
        page.wait_for_function(
            "(id) => { const r = document.getElementById(id).getBoundingClientRect();"
            " return window.scrollY > 0 && r.height > 0 && r.top >= -1 && r.top < innerHeight; }",
            arg=anchor, timeout=10000)


def test_the_link_is_absent_when_everything_fits_on_one_page(new_context, few):
    context, page = _open(new_context, few, VIEWPORT_MIN_SUPPORTED)
    try:
        assert page.locator(MORE).count() == 0
    finally:
        context.close()


def test_an_invalid_more_value_shows_the_first_page(new_context, many):
    context, page = _open(new_context, many, VIEWPORT_MIN_SUPPORTED, route="/flights?more=-3")
    try:
        assert _count(page, CARD) == LIMIT
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_search_finds_a_flight_older_than_the_loaded_page(new_context, many, viewport):
    """The oldest call sign is not among the first LIMIT rows; typing it finds it over the whole
    history, says one flight matches and keeps the address in step."""
    context, page = _open(new_context, many, viewport)
    try:
        selector = ROW if viewport["width"] >= 960 else CARD
        assert _count(page, "[data-flights-search]") == 1
        assert OLDEST not in page.content()
        page.click(FIELD)
        page.keyboard.type(OLDEST.lower())
        _wait_count(page, selector, 1)
        assert OLDEST in page.locator(selector).first.evaluate("e => e.textContent")
        page.wait_for_function(
            "() => document.querySelector('[data-filter-count]').textContent === '1 flight matches'")
        assert page.evaluate(
            "() => document.querySelectorAll('.filter-chip__count').length") == 0
        assert page.locator(MORE).count() == 0
        assert "q=afr100" in page.url
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_a_search_with_no_match_shows_one_coherent_empty_card(new_context, many, viewport, lang):
    """The chips stay plain direction labels, no table header,
    no shown-count line and no Load more stay under the card, whose body quotes the whole
    history and whose Clear brings the list back."""
    context, page = _open(new_context, many, viewport, lang)
    try:
        page.click(FIELD)
        page.keyboard.type("zzzz")
        card = page.locator(EMPTY)
        card.wait_for(state="visible")
        assert card.locator(".empty-state__heading").inner_text() == (
            "No matching flights" if lang == "en" else "Aucun vol correspondant")
        assert str(TOTAL) in card.locator(".empty-state__body").inner_text()
        labels = page.evaluate(
            "() => [...document.querySelectorAll('.filter-chip')].map(e => e.textContent.trim())")
        assert not any(ch.isdigit() for label in labels for ch in label), labels
        assert len(labels) == 3, labels
        assert _count(page, "thead") == 0 and _count(page, "table") == 0
        assert _count(page, CARD) == 0 and _count(page, ".history-more") == 0
        assert not _assert_no_page_overflow(page, "empty flights", viewport["width"])
        clear = card.locator("a")
        assert clear.inner_text() == ("Clear" if lang == "en" else "Effacer")
        assert clear.bounding_box()["height"] >= 44 - 0.5
        page.evaluate("() => { window.__marker = 'same document'; }")
        clear.click()
        _wait_count(page, ROW if viewport["width"] >= 960 else CARD, LIMIT)
        assert page.evaluate("() => window.__marker") == "same document"
        assert page.input_value(FIELD) == "" and _count(page, EMPTY) == 0
    finally:
        context.close()


def test_the_sort_changes_the_order_and_survives_load_more(new_context, many):
    """Choosing "Oldest first" lists the oldest flight first in place; Load more then appends
    the next flights in that order and the address keeps the sort."""
    context, page = _open(new_context, many, VIEWPORT_PHONE)
    try:
        assert _first_callsign(page) != OLDEST
        page.evaluate("() => { window.__marker = 'same document'; }")
        _choose_sort(page, "oldest")
        page.wait_for_function(
            "(c) => document.querySelector('li.history-card .history-card__callsign')"
            ".textContent === c", arg=OLDEST, timeout=10000)
        assert "sort=oldest" in page.url
        assert page.evaluate("() => document.querySelector('input[name=sort]:checked').value") == (
            "oldest")
        page.locator(MORE).click()
        _wait_count(page, CARD, TOTAL)
        assert _first_callsign(page) == OLDEST
        last = page.evaluate(
            "() => [...document.querySelectorAll('li.history-card .history-card__callsign')]"
            ".pop().textContent")
        assert last != OLDEST
        assert page.url.endswith("sort=oldest&more=1"), page.url
        assert page.evaluate("() => window.__marker") == "same document"
        _choose_sort(page, "airline")
        # Each group is named by its airline, never by the sort's own name.
        page.wait_for_function(
            "() => { const first = document.querySelector('section.history-day');"
            " return first.querySelector('h2').textContent"
            " === first.querySelector('.history-card__airline').textContent; }",
            timeout=10000)
        assert _count(page, CARD) == LIMIT
    finally:
        context.close()


def test_arrow_keys_walk_the_sort_menu_without_closing_it(new_context, many):
    """with the keyboard the menu stays open on the radio just chosen, so the next arrow reaches
    the third order in the same visit; the list follows each step"""
    context, page = _open(new_context, many, VIEWPORT_DESKTOP)
    try:
        page.locator(".collection-sort > summary").click()
        page.locator('.collection-sort__option input[value="newest"]').focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_function("() => location.search.indexOf('sort=oldest') >= 0", timeout=10000)
        page.wait_for_function(
            "() => { const a = document.activeElement;"
            " return !!a && a.matches('input[name=sort]') && a.value === 'oldest'"
            " && a.closest('details').open; }", timeout=10000)
        page.keyboard.press("ArrowDown")
        page.wait_for_function("() => location.search.indexOf('sort=airline') >= 0", timeout=10000)
        page.wait_for_function(
            "() => { const a = document.activeElement;"
            " return !!a && a.matches('input[name=sort]') && a.value === 'airline'"
            " && a.closest('details').open; }", timeout=10000)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('.collection-sort').open", timeout=5000)
    finally:
        context.close()


def test_arrow_keys_walk_the_airlines_sort_menu_without_closing_it(new_context, few):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    page = context.new_page()
    _login(page, few.base_url())
    page.goto(few.base_url() + "/airlines")
    page.wait_for_function(_SETTLED, timeout=15000)
    try:
        page.locator(".collection-sort > summary").click()
        first = page.locator('.collection-sort__option input[name="sort"]:checked')
        first.focus()
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            "() => { const a = document.activeElement;"
            " return !!a && a.matches('input[name=sort]') && a.checked"
            " && a.closest('details').open; }", timeout=10000)
        page.keyboard.press("ArrowDown")
        page.wait_for_function(
            "() => { const a = document.activeElement;"
            " return !!a && a.matches('input[name=sort]') && a.checked"
            " && a.closest('details').open && "
            "document.querySelectorAll('input[name=sort]:checked').length === 1; }", timeout=10000)
    finally:
        context.close()


def test_a_pointer_choice_still_closes_the_sort_menu(new_context, many):
    context, page = _open(new_context, many, VIEWPORT_DESKTOP)
    try:
        _choose_sort(page, "oldest")
        page.wait_for_function("() => location.search.indexOf('sort=oldest') >= 0", timeout=10000)
        page.wait_for_function(
            "() => !document.querySelector('.collection-sort').open", timeout=5000)
    finally:
        context.close()


def test_the_sort_works_without_scripts(new_context, many):
    with _no_js_page(new_context, many.base_url(), "/flights", viewport=VIEWPORT_PHONE) as page:
        _choose_sort(page, "oldest")
        page.click(".history-controls__apply")
        page.wait_for_url("**sort=oldest*")
        assert _first_callsign(page) == OLDEST
        page.click(MORE)
        page.wait_for_url("**sort=oldest*more=1*")
        assert _first_callsign(page) == OLDEST and _count(page, CARD) == TOTAL


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [1280, 1440])
def test_the_desktop_search_shares_the_title_row_clear_of_the_frame_button(
        new_context, few, width, lang):
    """From 1280px the search sits on the title's row at its right edge, clear of the frame
    button, and is as wide as the 44px row is high (nothing floats between title and chips)."""
    context, page = _open(new_context, few, {"width": width, "height": 800}, lang)
    try:
        box = lambda s: page.locator(s).first.bounding_box()  # noqa: E731
        field, title, button = box(".filter-bar--title"), box(".page-title"), box(".frame-menu__button")
        chips = box(".history-controls")
        assert field["x"] >= title["x"] + title["width"], (field, title)
        assert field["x"] + field["width"] <= button["x"] + 0.5, (field, button)
        assert field["y"] < title["y"] + title["height"] and field["y"] + field["height"] > title["y"]
        assert abs(field["height"] - 44) <= 0.5 and chips["y"] >= field["y"] + field["height"]
    finally:
        context.close()


def test_the_desktop_search_wraps_left_aligned_under_the_title_when_the_row_is_narrow(
        new_context, few):
    context, page = _open(new_context, few, {"width": 1100, "height": 800})
    try:
        field, title = page.locator(".filter-bar--title").bounding_box(), page.locator(
            ".page-title").bounding_box()
        assert field["y"] >= title["y"] + title["height"] - 0.5, (field, title)
        assert abs(field["x"] - title["x"]) <= 1, (field, title)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_a_phone_row_without_a_render_leads_with_a_stand_in_and_no_empty_gutter(
        new_context, bare, viewport):
    """With no archived render a phone row leads with its stand-in (a 44px box), and its text
    starts right after it, not after an empty lead column."""
    context, page = _open(new_context, bare, viewport)
    try:
        rows = page.evaluate(
            "() => [...document.querySelectorAll('li.history-card')].map(li => {"
            " const lead = li.querySelector('.history-card__thumb').getBoundingClientRect();"
            " const text = li.querySelector('.row__text').getBoundingClientRect();"
            " return {lead: lead.width, gap: text.left - lead.right};})")
        assert rows and all(row["lead"] == 44 and 0 <= row["gap"] <= 16 for row in rows), rows
    finally:
        context.close()


# --- Without a connection ---------------------------------------------------------------------

_OFFLINE_TOAST = "[data-quick-toast] .toast"
_OFFLINE_WORDS = {
    "en": ("Couldn't update the list", "Check your connection and try again."),
    "fr": ("Impossible de mettre la liste à jour", "Vérifiez votre connexion et réessayez."),
}


def _same_page(page, server):
    """The document the test opened is still the one shown, on the app's own address."""
    assert page.url.startswith(server.base_url()), page.url
    assert page.evaluate("() => window.__marker") == "same document"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_search_without_a_connection_keeps_the_list_and_says_so(new_context, many, lang):
    """offline, typing in the search leaves the page and its flights where they are and an error
    toast says the list could not be updated; once back online the same search answers"""
    context, page = _open(new_context, many, VIEWPORT_PHONE, lang)
    try:
        page.evaluate("() => { window.__marker = 'same document'; }")
        context.set_offline(True)
        page.click(FIELD)
        page.keyboard.type(OLDEST.lower())
        toast = page.locator(_OFFLINE_TOAST)
        toast.wait_for(state="visible", timeout=10000)
        title, detail = _OFFLINE_WORDS[lang]
        assert title in toast.inner_text() and detail in toast.inner_text(), toast.inner_text()
        _same_page(page, many)
        assert _count(page, CARD) == LIMIT
        assert page.input_value(FIELD) == OLDEST.lower()
        assert "q=" not in page.url
        context.set_offline(False)
        page.press(FIELD, "Enter")
        _wait_count(page, CARD, 1)
        _same_page(page, many)
        assert "q=afr100" in page.url
        # The answer takes the notice back.
        toast.wait_for(state="detached", timeout=5000)
    finally:
        context.close()


def test_load_more_without_a_connection_keeps_the_list_and_can_be_tried_again(new_context, many):
    """offline, Load more adds nothing, stays on the page, shows the toast and is ready again:
    the same tap appends the next flights once the connection is back"""
    context, page = _open(new_context, many, VIEWPORT_PHONE)
    try:
        page.evaluate("() => { window.__marker = 'same document'; }")
        link = page.locator(MORE)
        link.scroll_into_view_if_needed()
        context.set_offline(True)
        link.click()
        page.locator(_OFFLINE_TOAST).wait_for(state="visible", timeout=10000)
        _same_page(page, many)
        assert _count(page, CARD) == LIMIT
        page.wait_for_function(
            "() => !document.querySelector('a.history-more__link[aria-busy]')", timeout=5000)
        assert page.url.endswith("/flights"), page.url
        context.set_offline(False)
        page.locator(_OFFLINE_TOAST + " .toast__dismiss").click()
        page.locator(_OFFLINE_TOAST).wait_for(state="hidden", timeout=5000)
        page.locator(MORE).click()
        _wait_count(page, CARD, TOTAL)
        _same_page(page, many)
    finally:
        context.close()


def test_a_sort_without_a_connection_goes_back_to_the_order_shown(new_context, many):
    """offline, choosing another order changes nothing: the page stays, the toast shows and the
    menu names the order the list is really in"""
    context, page = _open(new_context, many, VIEWPORT_PHONE)
    try:
        page.evaluate("() => { window.__marker = 'same document'; }")
        first = _first_callsign(page)
        context.set_offline(True)
        _choose_sort(page, "oldest")
        page.locator(_OFFLINE_TOAST).wait_for(state="visible", timeout=10000)
        _same_page(page, many)
        assert _first_callsign(page) == first
        page.wait_for_function(
            "() => document.querySelector('input[name=sort]:checked').value === 'newest'",
            timeout=5000)
        assert "sort=" not in page.url
    finally:
        context.close()


# --- What a change downloads ------------------------------------------------------------------

def _answer_to(page, part, act):
    """`(address, size)` of the answer to the list request `act` causes."""
    with page.expect_response(
            lambda r: "/flights" in r.url and "part=%s" % part in r.url, timeout=10000) as info:
        act()
    response = info.value
    return response.url, len(response.body())


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_load_more_downloads_only_the_next_flights(new_context, lots, viewport):
    """each Load more step asks for the next flights alone: the second answer is no heavier than
    the first, both far lighter than the page, and the address shown stays the plain one"""
    context, page = _open(new_context, lots, viewport)
    try:
        whole = len(page.content())
        selector = ROW if viewport["width"] >= 960 else CARD
        _url, first = _answer_to(page, "new", page.locator(MORE).click)
        _wait_count(page, selector, 2 * LIMIT)
        _url, second = _answer_to(page, "new", page.locator(MORE).click)
        _wait_count(page, selector, LOTS)
        assert second <= first * 1.1 and first < 0.75 * whole, (first, second, whole)
        assert page.url.endswith("/flights?more=2"), page.url
        # One day group and one day row, as on the page loaded whole.
        assert _count(page, "section.history-day") == 1
        assert _count(page, "tr.flight-day-row") == 1
        assert len(set(page.evaluate(
            "() => [...document.querySelectorAll('[id]')].map((e) => e.id)"))) == page.evaluate(
            "() => document.querySelectorAll('[id]').length"), "an id is repeated"
    finally:
        context.close()


def test_a_filter_change_downloads_the_list_without_the_page_around_it(new_context, many):
    """a chip, the sort and a search each ask for the list alone; the address shown never
    carries the fragment's own parameter and reloading it gives the same list"""
    context, page = _open(new_context, many, VIEWPORT_PHONE)
    try:
        whole = len(page.content())
        _url, sorted_size = _answer_to(page, "list", lambda: _choose_sort(page, "oldest"))
        page.wait_for_function(
            "(c) => document.querySelector('li.history-card .history-card__callsign')"
            ".textContent === c", arg=OLDEST, timeout=10000)
        page.click(FIELD)
        _url, found_size = _answer_to(page, "list", lambda: page.keyboard.type("afr10"))
        page.wait_for_function("() => location.search.indexOf('q=afr10') >= 0", timeout=10000)
        assert sorted_size < 0.9 * whole and found_size < sorted_size, (
            sorted_size, found_size, whole)
        assert "part=" not in page.url
        shown = page.evaluate(
            "() => [...document.querySelectorAll('li.history-card')].map((c) => c.dataset.flightId)")
        page.reload()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.evaluate(
            "() => [...document.querySelectorAll('li.history-card')].map((c) => c.dataset.flightId)"
        ) == shown
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_list_says_it_is_busy_while_a_slow_search_is_out(new_context, many, viewport):
    """on a slow network the list the search will replace is marked busy from the moment the
    request leaves until its answer is shown; an offline failure clears the mark too"""
    context, page = _open(new_context, many, viewport)
    try:
        held = []

        released = []

        def slow(route):
            if released:
                route.continue_()
            else:
                held.append(route)

        busy = ("() => [...document.querySelectorAll('.history-cards, .data-table-wrap')]"
                ".filter((e) => e.getClientRects().length)"
                ".map((e) => e.getAttribute('aria-busy'))")
        assert page.evaluate(busy) == [None]
        page.route("**/flights?*part=list*", slow)
        page.click(FIELD)
        page.keyboard.type(OLDEST.lower())
        page.wait_for_function(
            "() => [...document.querySelectorAll('.history-cards, .data-table-wrap')]"
            ".some((e) => e.getClientRects().length && e.getAttribute('aria-busy') === 'true')",
            timeout=10000)
        for _wait in range(100):
            if held:
                break
            page.wait_for_timeout(50)
        assert held, "the request was held"
        released.append(True)
        for route in held:
            route.continue_()
        _wait_count(page, ROW if viewport["width"] >= 960 else CARD, 1)
        assert page.evaluate(busy) == [None]
    finally:
        context.close()
