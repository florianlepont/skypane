#!/usr/bin/env python3
"""Browser checks for the Flights phone list (day groups of flight rows below 960 px): no
horizontal overflow at 390 and 360 px in both themes and both languages, flat glass day groups
and centred direction segments, the icon-only picture action at the 44px floor and operable
from the keyboard into the shared lightbox, the search and the direction narrowing the list in place and updating
the count, the rows working with scripts blocked, and the desktop table unchanged at 1280 px.
"""
import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _assert_no_page_overflow, _in_both_themes, _login, _no_js_page,
)

pytestmark = pytest.mark.browser

LIGHTBOX = "#panel-lookup-dialog"
CARD = "li.history-card"
FIRST_ACTION = "li.history-card .history-card__thumb"


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """A read-only server seeded with every card variant and one archived render."""
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


def _open_flights(new_context, server, viewport, lang="en"):
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/flights")
    page.locator(CARD).first.wait_for(state="visible")
    return context, page


_CARD_PROBE = (
    "() => [...document.querySelectorAll('li.history-card')].map(li => {"
    "  const c = li.getBoundingClientRect();"
    "  const inside = [...li.querySelectorAll('*')].every(el => {"
    "    const r = el.getBoundingClientRect();"
    "    return r.width === 0 || (r.left >= c.left - 0.5 && r.right <= c.right + 0.5);"
    "  });"
    "  const chip = li.querySelector('.history-card__thumb, .row__chip').getBoundingClientRect();"
    "  const label = li.querySelector('.row__label');"
    "  const detail = li.querySelector('.row__detail');"
    "  const value = li.querySelector('.row__value').getBoundingClientRect();"
    "  const text = li.querySelector('.row__text').getBoundingClientRect();"
    "  return {callsign: li.querySelector('.history-card__callsign').textContent,"
    "          inside, height: c.height,"
    "          readable: label.scrollWidth <= label.clientWidth + 1"
    "                    && detail.clientHeight <= 2 * parseFloat(getComputedStyle(detail).lineHeight) + 1"
    "                    && (detail.textContent.length > 40"
    "                        || detail.scrollHeight <= detail.clientHeight + 1),"
    "          controls: li.querySelectorAll('a, button').length,"
    "          oneRow: chip.top < value.bottom && value.top < chip.bottom"
    "                  && text.right <= value.left + 0.5};"
    "})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_cards_fit_the_phone_in_both_themes(new_context, server, viewport, lang):
    """At 390 and 360 px, in English and French, light and dark: the page never scrolls
    sideways, every row keeps its content inside its own box, is at least 54px tall, and shows
    the lead, the text and the value on one row without the text running under the value, with
    the label unclipped, the detail at most two lines (unclipped unless it is a very long
    name) and at most one control per row."""
    context, page = _open_flights(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            where = "Flights cards (%s, %s)" % (lang, theme["theme"])
            failure = _assert_no_page_overflow(page, where, expected_width=viewport["width"])
            if failure:
                raise AssertionError(failure)
            for card in page.evaluate(_CARD_PROBE):
                if not (card["inside"] and card["oneRow"] and card["height"] >= 54
                        and card["readable"] and card["controls"] <= 1):
                    raise AssertionError("%s: card %r is broken: %r" % (where, card["callsign"], card))
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_picture_action_is_a_44px_keyboard_operable_lightbox_trigger(new_context, server, viewport):
    """The card's icon action hit-tests at no less than 44px on both axes, takes a visible focus
    ring from the keyboard, opens the shared lightbox with its own picture on Enter, returns
    focus on Escape, and opens it again on a tap, without leaving the page."""
    context, page = _open_flights(new_context, server, viewport)
    try:
        _assert_hit_target(page, FIRST_ACTION, "Flights card picture action")
        action = page.locator(FIRST_ACTION).first
        expected_src = action.get_attribute("data-view-panel-src")
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        for _ in range(80):
            page.keyboard.press("Tab")
            if action.evaluate("el => el === document.activeElement"):
                break
        else:
            raise AssertionError("expected Tab to reach the card's picture action")
        outline = action.evaluate(
            "el => [getComputedStyle(el).outlineStyle, parseFloat(getComputedStyle(el).outlineWidth)]")
        if outline[0] == "none" or outline[1] < 1:
            raise AssertionError("expected a visible focus ring, got %r" % (outline,))
        page.keyboard.press("Enter")
        dialog = page.locator(LIGHTBOX)
        dialog.wait_for(state="visible")
        shown = dialog.locator("img.lightbox__image").get_attribute("src")
        if shown != expected_src:
            raise AssertionError("expected the lightbox to show %r, got %r" % (expected_src, shown))
        page.keyboard.press("Escape")
        page.wait_for_function(
            "s => !document.querySelector(s).open", arg=LIGHTBOX, timeout=10000)
        if not action.evaluate("el => el === document.activeElement"):
            raise AssertionError("expected focus to return to the picture action")
        page.locator(FIRST_ACTION).nth(1).click()
        page.wait_for_function(
            "s => document.querySelector(s).open", arg=LIGHTBOX, timeout=10000)
        if "/gallery/" in page.url:
            raise AssertionError("expected a tap to open the lightbox in place")
    finally:
        context.close()


def test_search_narrows_the_list_in_place_and_updates_the_count(new_context, server):
    """Typing in the search narrows the list to the matching flights without leaving the page
    and the count reads how many match; the inline clear brings every card back."""
    context, page = _open_flights(new_context, server, VIEWPORT_PHONE)
    try:
        total = page.locator(CARD).count()
        page.evaluate("() => { window.__marker = 'same document'; }")
        page.fill("[data-flights-search]", "obs")
        page.wait_for_function(_ONLY_OBS, timeout=10000)
        page.wait_for_function(
            "() => document.querySelector('[data-filter-count]').textContent === '1 flight matches'",
            timeout=10000)
        page.click(".filter-bar__clear")
        page.wait_for_function(
            "(n) => document.querySelectorAll('li.history-card').length === n"
            " && document.querySelector('[data-flights-search]').value === ''",
            arg=total, timeout=10000)
        if page.evaluate("() => window.__marker") != "same document":
            raise AssertionError("expected the list to change without a page load")
    finally:
        context.close()


_ONLY_OBS = (
    "() => { const rows = [...document.querySelectorAll('li.history-card')];"
    " return rows.length === 1 && rows[0].querySelector('.history-card__callsign')"
    ".textContent === 'OBS412'; }")


@pytest.fixture(scope="module")
def folded_server(module_app_server_factory):
    """Variety seed plus a stored-twice copy of its first flight, as the poll loop writes."""
    return module_app_server_factory(seed=vp.seed_home_tile_variety, fake_providers=True)


_COUNTS_VS_CARDS = (
    "() => ({labels: [...document.querySelectorAll('.filter-chip')].map(l => l.textContent.trim()),"
    " cards: [...document.querySelectorAll('li.history-card')].filter(li => li.offsetParent)"
    "   .map(li => li.dataset.filterKind),"
    " days: [...document.querySelectorAll('section.history-day')]"
    "   .filter(li => li.offsetParent).length})")


def test_each_chip_lists_the_folded_cards_of_its_direction(new_context, folded_server):
    """a pass stored twice shows as one card: each chip then lists exactly the folded cards of its
    direction (5 / 4 / 1), and the chips themselves carry no number"""
    context, page = _open_flights(new_context, folded_server, VIEWPORT_PHONE)
    try:
        for chip, kind, expected in (
                ("All", None, 5), ("Departures", "departing", 4), ("Arrivals", "arriving", 1)):
            page.locator(".filter-chip", has_text=chip).click()
            page.wait_for_function(
                "(n) => document.querySelectorAll('li.history-card').length === n",
                arg=expected, timeout=10000)
            state = page.evaluate(_COUNTS_VS_CARDS)
            shown = [k for k in state["cards"] if kind in (None, k)]
            if len(state["cards"]) != len(shown) or len(shown) != expected:
                raise AssertionError("expected %s to list %d folded cards, got %r"
                                     % (chip, expected, state))
        if page.evaluate(_COUNTS_VS_CARDS)["labels"] != ["All", "Departures", "Arrivals"]:
            raise AssertionError("expected plain chip labels")
    finally:
        context.close()


@pytest.fixture(scope="module")
def full_server(module_app_server_factory):
    """Fifty distinct flights, the most the Flights page ever lists."""
    def seed(state_dir):
        vp.seed_runway_events(state_dir, [
            {"ts": "2026-09-%02dT%02d:%02d:00+00:00" % (1 + i // 24, (i % 24) // 6 + 6, (i % 6) * 10),
             "hex": "4b%04x" % i, "callsign": "TVF%02d" % i, "airline": "Transavia France",
             "origin": "ORY", "destination": "BRI",
             "confirmed_state": "arriving" if i % 5 == 0 else "departing", "corroborated": True}
            for i in range(50)])
    return module_app_server_factory(seed=seed, fake_providers=True)


def test_each_chip_lists_its_cards_with_all_fifty_loaded(new_context, full_server):
    """with 50 flights loaded at once, each chip lists 50 / 40 / 10 cards, the count line reads
    50 flights, and there is no Show-more control"""
    context, page = _open_flights(new_context, full_server, VIEWPORT_PHONE)
    try:
        if page.locator(CARD).count() != 50 or page.locator(".flights-more").count():
            raise AssertionError("expected 50 cards and no Show-more control")
        for chip, kind, expected in (
                ("All", None, 50), ("Departures", "departing", 40), ("Arrivals", "arriving", 10)):
            page.locator(".filter-chip", has_text=chip).click()
            page.wait_for_function(
                "(n) => document.querySelectorAll('li.history-card').length === n",
                arg=expected, timeout=10000)
            state = page.evaluate(_COUNTS_VS_CARDS)
            if len(state["cards"]) != expected or any(kind not in (None, k) for k in state["cards"]):
                raise AssertionError("expected %s to list %d cards, got %r"
                                     % (chip, expected, state))
        page.locator(".filter-chip", has_text="All").click()
        page.wait_for_function(
            "() => document.querySelectorAll('li.history-card').length === 50", timeout=10000)
        count = page.locator("[data-filter-count]").text_content()
        if count != "50 flights":
            raise AssertionError("expected '50 flights', got %r" % (count,))
        failure = _assert_no_page_overflow(page, "50 flights", expected_width=VIEWPORT_PHONE["width"])
        if failure:
            raise AssertionError(failure)
    finally:
        context.close()


_GROUP_PROBE = (
    "() => ({groups: [...document.querySelectorAll('section.history-day')].map(g => ({"
    "  label: g.querySelector('h2.section-label').textContent.trim(),"
    "  glass: getComputedStyle(g.querySelector('ul.group')).backgroundColor,"
    "  nested: g.querySelectorAll('.group .group').length,"
    "  rows: g.querySelectorAll('li.history-card').length})),"
    " tracks: [...document.querySelectorAll('.filter-chip')].map(l => {"
    "   const box = l.querySelector('.filter-chip__box');"
    "   const b = box.getBoundingClientRect(); const range = document.createRange();"
    "   range.selectNodeContents(box); const t = range.getBoundingClientRect();"
    "   return {dx: (t.left + t.right - b.left - b.right) / 2,"
    "           dy: (t.top + t.bottom - b.top - b.bottom) / 2}; })})")


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED], ids=["390", "360"])
def test_each_day_is_one_glass_group_and_the_segments_are_centred(
        new_context, server, viewport, lang):
    """One glass group per day, each holding its flight rows with no group inside a group; the
    direction segments centre their count and label in their pill; the first segment keeps a
    visible focus ring from the keyboard."""
    context, page = _open_flights(new_context, server, viewport, lang)
    try:
        for theme in _in_both_themes(page):
            state = page.evaluate(_GROUP_PROBE)
            where = "%s/%s/%d" % (lang, theme["theme"], viewport["width"])
            if len(state["groups"]) != 2 or any(g["nested"] or not g["rows"] for g in state["groups"]):
                raise AssertionError("expected two flat day groups (%s): %r" % (where, state["groups"]))
            if any(g["glass"] in ("rgba(0, 0, 0, 0)", "transparent") for g in state["groups"]):
                raise AssertionError("expected a glass fill on every group (%s)" % where)
            for track in state["tracks"]:
                if abs(track["dx"]) > 1 or abs(track["dy"]) > 1:
                    raise AssertionError("expected centred segment content (%s): %r" % (where, track))
        page.evaluate("() => document.activeElement && document.activeElement.blur()")
        page.keyboard.press("Tab")
        page.wait_for_function(
            "() => { const e = document.activeElement; return e && e.type === 'radio' || "
            "e && e.matches('[data-flights-search], a, button'); }")
    finally:
        context.close()


def test_cards_render_and_link_without_scripts(new_context, server):
    """With scripts blocked the cards are server-rendered as they are with scripts, and the
    picture action is a real link that serves the archived render."""
    with _no_js_page(new_context, server.base_url(), "/flights", viewport=VIEWPORT_PHONE) as page:
        cards = page.locator(CARD)
        cards.first.wait_for(state="visible")
        if cards.count() != len(vp.FLIGHT_CARD_FLIGHTS):
            raise AssertionError("expected one card per flight, got %d" % cards.count())
        href = page.locator(FIRST_ACTION).first.get_attribute("href")
        response = page.goto(server.base_url() + href)
        if response is None or response.status != 200:
            raise AssertionError("expected the card link to serve the archived render, got %r" % (response,))


def test_desktop_keeps_the_table_and_hides_the_cards(new_context, server):
    """At 1280 px the cards are hidden and the flights table is shown, its picture links still
    reading "View picture"."""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        table = page.locator("table.data-table--flights")
        table.wait_for(state="visible")
        if page.locator("ul.history-cards").is_visible():
            raise AssertionError("expected the phone cards hidden at 1280px")
        links = table.locator("a[data-view-panel-src]")
        if links.count() != len(vp.FLIGHT_CARD_FLIGHTS):
            raise AssertionError("expected one table link per flight, got %d" % links.count())
        texts = set(links.all_text_contents())
        if texts != {"View picture"}:
            raise AssertionError("expected every table link to read View picture, got %r" % (texts,))
    finally:
        context.close()


_VISIBLE_CALLSIGNS = (
    "() => [...document.querySelectorAll('li.history-card')]"
    ".filter(li => li.offsetParent).map(li =>"
    " li.querySelector('.history-card__callsign').textContent)")
_CHIP_LABELS = (
    "() => [...document.querySelectorAll('.filter-chip')].map(l => l.textContent.trim())")


_SETTLE_JS = """async (selectors) => {
  const rects = () => selectors.map(s => {
    const el = document.querySelector(s);
    const r = el ? el.getBoundingClientRect() : null;
    return r ? [r.x, r.y, r.width, r.height].join() : "missing";
  }).join("|");
  let last = rects();
  let still = 0;
  const deadline = performance.now() + 5000;
  while (still < 5) {
    await new Promise(resolve => requestAnimationFrame(resolve));
    const now = rects();
    still = now === last ? still + 1 : 0;
    last = now;
    if (performance.now() > deadline) {
      throw new Error("layout still moving: " + last);
    }
  }
}"""


def _wait_until_still(page, *selectors):
    """Block until every selector's box has held still for five animation frames, so a click
    is aimed at where the element will stay (the phone search animates open and re-wraps the
    chips, which moves the empty state under the pointer)."""
    page.evaluate(_SETTLE_JS, list(selectors))


def _wait_callsigns(page, expected):
    page.wait_for_function(
        "(want) => JSON.stringify([...document.querySelectorAll('li.history-card')]"
        ".filter(li => li.offsetParent).map(li =>"
        " li.querySelector('.history-card__callsign').textContent)) === JSON.stringify(want)",
        arg=expected, timeout=10000)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_direction_chips_fit_one_row_at_360(new_context, server, lang):
    """the three chips are plain labels that sit on one row inside the page at 360px, none cut
    off and each at least 44px tall"""
    context, page = _open_flights(new_context, server, VIEWPORT_MIN_SUPPORTED, lang)
    try:
        page.wait_for_function("() => document.readyState === 'complete'")
        boxes = page.evaluate(
            "() => [...document.querySelectorAll('.filter-chip')].map(l => {"
            " const r = l.getBoundingClientRect(); const t = l.querySelector('.filter-chip__text');"
            " return {top: r.top, left: r.left, right: r.right, height: r.height,"
            " cut: t.scrollWidth > t.clientWidth, digits: /[0-9]/.test(l.textContent)}; })")
        if len(boxes) != 3 or any(b["digits"] or b["cut"] for b in boxes):
            raise AssertionError("expected three uncut plain chips, got %r" % (boxes,))
        if len({round(b["top"]) for b in boxes}) != 1 or boxes[-1]["right"] > 360 or boxes[0]["left"] < 0:
            raise AssertionError("expected one row inside 360px, got %r" % (boxes,))
        if any(b["height"] < 43.5 for b in boxes):
            raise AssertionError("expected 44px chip targets, got %r" % (boxes,))
    finally:
        context.close()


def test_direction_chips_filter_and_clear(new_context, server):
    """The chips are plain labels (no number, whatever the search), filter the list in
    place, combine with the search text, drop a day group left with no flight, and the empty
    card's Clear resets both the text and the chip."""
    context, page = _open_flights(new_context, server, VIEWPORT_PHONE)
    try:
        labels = page.evaluate(_CHIP_LABELS)
        if labels != ["All", "Departures", "Arrivals"]:
            raise AssertionError("expected plain chip labels, got %r" % (labels,))
        page.locator(".filter-chip", has_text="Arrivals").click()
        _wait_callsigns(page, ["AFR6152"])
        heads = page.evaluate(
            "() => [...document.querySelectorAll('section.history-day')]"
            ".filter(li => li.offsetParent).length")
        if heads != 1:
            raise AssertionError("expected one day header to stay, got %d" % heads)
        if page.evaluate(_CHIP_LABELS) != labels:
            raise AssertionError("expected a chosen direction to leave the labels alone")
        # Text and chip combine: no departure matches "afr", so nothing shows.
        page.locator(".filter-chip", has_text="Departures").click()
        page.fill("[data-flights-search]", "afr")
        empty = page.locator("[data-flights-empty]")
        empty.wait_for(state="visible")
        _wait_callsigns(page, [])
        if page.evaluate(_CHIP_LABELS) != labels:
            raise AssertionError("expected plain chip labels under the empty card, got %r"
                                 % (page.evaluate(_CHIP_LABELS),))
        if page.locator("table thead").count() or page.locator(".history-more").count():
            raise AssertionError("expected no table header and no Load more under the empty card")
        _wait_until_still(page, ".filter-bar__search", ".filter-bar__chips",
                          "[data-flights-empty] a")
        empty.locator("a").click()
        page.wait_for_function(
            "() => !document.querySelector('[data-flights-empty]')"
            " && document.querySelectorAll('li.history-card').length === 5", timeout=10000)
        if page.input_value("[data-flights-search]") != "":
            raise AssertionError("expected Clear to empty the search")
        if not page.locator(".filter-chip input[value='']").is_checked():
            raise AssertionError("expected Clear to put the chip back on All")
    finally:
        context.close()


def test_search_matches_airline_and_airport_text_and_inline_clear(new_context, server):
    """The search finds a flight by airline name and by airport code, and the inline clear
    empties the field."""
    context, page = _open_flights(new_context, server, VIEWPORT_PHONE)
    try:
        for query, expected in (("transavia", ["TVF72YL"]), ("kef", ["TVF72YL"]),
                                ("opo", ["OBS412"])):
            page.fill("[data-flights-search]", query)
            _wait_callsigns(page, expected)
        page.locator(".filter-bar__clear").click()
        if page.input_value("[data-flights-search]") != "":
            raise AssertionError("expected the inline clear to empty the search")
        page.wait_for_function(
            "() => document.querySelectorAll('li.history-card').length === 5", timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED])
def test_search_collapses_expands_and_keeps_44px_targets(new_context, server, viewport):
    """On a phone the search rests as a square icon button beside the chips, opens over the row
    on focus and while it holds text, uses 16px text (no iOS zoom) and keeps a 44px clear
    target, in both themes with no horizontal overflow."""
    context, page = _open_flights(new_context, server, viewport)
    try:
        for _theme in _in_both_themes(page):
            box = page.locator(".filter-bar__search input").bounding_box()
            if not (44 <= box["width"] <= 56 and box["height"] >= 44):
                raise AssertionError("expected a collapsed icon-sized field, got %r" % (box,))
            _assert_no_page_overflow(page, "collapsed filter bar")
        page.locator(".filter-bar__search input").focus()
        page.wait_for_function(
            "() => document.querySelector('.filter-bar__search').getBoundingClientRect().width > 250")
        font = page.eval_on_selector(
            ".filter-bar__search input", "el => parseFloat(getComputedStyle(el).fontSize)")
        if font < 16:
            raise AssertionError("expected 16px+ search text, got %r" % (font,))
        page.fill("[data-flights-search]", "tvf")
        page.locator(".filter-bar__clear").wait_for(state="visible")
        _assert_hit_target(page, ".filter-bar__clear", "inline clear")
        page.locator(".filter-chip input").first.focus()
        page.wait_for_timeout(300)
        width = page.eval_on_selector(
            ".filter-bar__search", "el => el.getBoundingClientRect().width")
        if width < 250:
            raise AssertionError("expected the search to stay open while it holds text")
        _assert_no_page_overflow(page, "expanded filter bar")
    finally:
        context.close()


def test_desktop_search_is_always_open_in_the_title_row(new_context, server):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        page.locator(".filter-bar__search").wait_for(state="visible")
        field = page.locator(".filter-bar__search").bounding_box()
        header = page.locator(".page-header").bounding_box()
        title = page.locator(".page-title").bounding_box()
        # On the title's row (centred against the title, so a few pixels below the header top).
        if (field["width"] < 300 or not header["y"] - 1 <= field["y"] <= header["y"] + 4
                or field["x"] < title["x"] + title["width"]
                or field["y"] + field["height"] > header["y"] + header["height"] + 1):
            raise AssertionError("expected an open search right of the title, got %r %r %r"
                                 % (field, title, header))
    finally:
        context.close()


def test_the_controls_work_as_a_plain_form_without_scripts(new_context, server):
    """Without a script the chips, the sort and an Apply button (a 44px target) are shown, the
    search is the plain full-width field, and sending the form filters the list by the
    server."""
    with _no_js_page(new_context, server.base_url(), "/flights", viewport=VIEWPORT_PHONE) as page:
        for selector in (".filter-bar__chips", ".collection-sort > summary", ".history-controls__apply"):
            if not page.locator(selector).is_visible():
                raise AssertionError("expected %s shown with scripts blocked" % selector)
        if page.locator(".history-controls__apply").bounding_box()["height"] < 44 - 0.5:
            raise AssertionError("expected a 44px Apply button")
        if page.locator(".filter-bar__search input").bounding_box()["width"] < 250:
            raise AssertionError("expected the plain full-width search without scripts")
        page.fill("[data-flights-search]", "obs")
        page.keyboard.press("Enter")
        page.wait_for_url("**/flights?q=obs*")
        if page.locator(CARD).count() != 1:
            raise AssertionError("expected the server to answer the search with one flight")
        page.locator(".filter-chip", has_text="Arrivals").click()
        page.click(".history-controls__apply")
        page.wait_for_url("**kind=arriving*")
        if page.locator(CARD).count() != 0 or page.locator("[data-flights-empty]").count() != 1:
            raise AssertionError("expected the empty card for no arrival matching obs")
        page.click("[data-flights-empty] a")
        page.wait_for_url("**/flights")
        if page.locator(CARD).count() != 5:
            raise AssertionError("expected the plain Clear link to bring every flight back")


def test_airlines_search_pill_has_no_chips_and_both_clears_work(new_context, server):
    """Airlines shares the component as a plain search pill (no chips); the inline clear and the
    empty state's Clear both empty the field."""
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines/manage")
        page.locator("[data-filter-input]").wait_for(state="visible")
        if page.locator(".filter-chip").count():
            raise AssertionError("expected no chips on the Airlines filter bar")
        page.fill("[data-filter-input]", "zzzzq")
        page.locator("[data-filter-empty]").wait_for(state="visible")
        page.locator("[data-filter-empty] [data-filter-clear]").click()
        if page.input_value("[data-filter-input]") != "":
            raise AssertionError("expected the empty state's Clear to empty the search")
        page.fill("[data-filter-input]", "air")
        page.locator(".filter-bar__clear").click()
        if page.input_value("[data-filter-input]") != "":
            raise AssertionError("expected the inline clear to empty the search")
        _assert_no_page_overflow(page, "airlines filter bar")
    finally:
        context.close()


_VISIBLE_TEXT = """sel => [...document.querySelectorAll(sel)].map(row => {
    const copy = row.cloneNode(true);
    copy.querySelectorAll('.visually-hidden').forEach(e => e.remove());
    return {text: copy.textContent, planes: row.querySelectorAll('use[href="#icon-plane"]').length,
            callsignSlot: row.querySelector('.history-card__callsign') !== null,
            filter: row.getAttribute('data-filter-text')};
})"""


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport,selector", [
    (VIEWPORT_PHONE, "li.history-card"), (VIEWPORT_DESKTOP, "tr[data-flight-row]")],
    ids=["phone-cards", "desktop-table"])
def test_a_flights_row_has_no_plane_icon_and_no_call_sign(
        new_context, server, viewport, selector, lang):
    """No plane icon and no visible call sign in any row; a search by call sign still finds the
    row, and the picture control (when the row has one) still names the flight."""
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang,
                          "url": server.base_url()}])
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        page.locator(selector).first.wait_for(state="visible")
        rows = page.evaluate(_VISIBLE_TEXT, selector)
        assert rows
        for row in rows:
            assert row["planes"] == 0
            assert row["text"].strip()
        for call_sign in [flight[0] for flight in vp.FLIGHT_CARD_FLIGHTS]:
            for row in rows:
                assert call_sign not in row["text"]
        page.fill("[data-flights-search]", "obs412")
        page.wait_for_function(
            """sel => { const rows = [...document.querySelectorAll(sel)];
                        const shown = rows.filter(r => !r.hidden && r.offsetParent !== null);
                        return shown.length === 1
                            && shown[0].getAttribute('data-filter-text').includes('obs412'); }""",
            arg=selector, timeout=10000)
    finally:
        context.close()


def test_a_phone_row_is_two_lines_airline_then_direction(new_context, server):
    """The title is the airline, the line under it the direction and aircraft; the clock sits
    over the age at the right."""
    context = new_context(viewport=VIEWPORT_PHONE)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/flights")
        page.locator("li.history-card").first.wait_for(state="visible")
        probe = page.evaluate(
            """() => [...document.querySelectorAll('li.history-card')].map(li => ({
                title: li.querySelector('.row__label .history-card__airline').textContent,
                detail: li.querySelector('.row__detail') ? li.querySelector('.row__detail').textContent : '',
                value: li.querySelector('.row__value').textContent}))""")
        assert all(row["title"].strip() for row in probe)
        assert any(row["detail"].startswith(("Departing", "Arriving")) for row in probe)
        assert all(row["value"].strip() for row in probe)
    finally:
        context.close()
