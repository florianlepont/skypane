"""Real-browser checks of the Airline collection (/airlines): at 360 and 1280 px, in English and
French, in both themes, nothing overflows sideways, every card, chip, select, field and button is at
least 44 px high and owns its centre, the badge pills are 44 px high, and the headline is the first
thing under the page header. A card opens its read-only sheet with the focus inside, Escape closes
it and returns the focus to the card, and a dimmed card keeps the text colour of a seen card (the
dimming is on the picture only). With scripts blocked the chips, sort and field work through the
Apply button and a card opens its sheet through the hash link.

State is always waited for (settled page, owned centres, focus), never read right after an input."""
import re
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _no_js_page,
    _set_ui_theme,
    seed_state_dir,
)
from server import history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
CARD = "a.collection-card"
SEEN_CARD = CARD + ":not(.collection-card--unseen)"
UNSEEN_CARD = CARD + ".collection-card--unseen"
TOTAL_SPOTTED = 3

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "el => { const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    """The shared fixture (36 Air France flights) plus Iberia three times and TAP Portugal once,
    the last a minute ago so it carries the New pill."""
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, days in enumerate((20, 10, 5)):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(days=days)).isoformat(), hex="ib%04d" % index,
                callsign="IBE%03d" % index, aircraft_type="A320", confirmed_state="departing",
                airline="Iberia Airlines")
        history_db.record_runway_event(
            conn, ts=(now - timedelta(minutes=1)).isoformat(), hex="tp0001", callsign="TAP001",
            aircraft_type="A21N", confirmed_state="arriving", airline="TAP Portugal")


def _wait_owns_centre(page, selector):
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        "sel => { const el = document.querySelector(sel); const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
        arg=selector, timeout=10000)


def _wait_theme_painted(page):
    """Wait until the colour transition of a theme switch has ended: no running animation and
    the card's colours equal on two successive polls."""
    page.wait_for_function(
        "() => { const s = getComputedStyle(document.querySelector('a.collection-card'));"
        " const key = s.backgroundColor + '|' + s.color + '|' +"
        " getComputedStyle(document.body).backgroundColor;"
        " const same = window.__paintKey === key; window.__paintKey = key;"
        " return same && document.getAnimations().length === 0; }", timeout=10000)


def _open(new_context, base_url, viewport, lang="en", theme="light", query=""):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + "/airlines" + query)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(SEEN_CARD).first.wait_for(state="visible")
    _set_ui_theme(page, theme)
    _wait_theme_painted(page)
    _wait_owns_centre(page, SEEN_CARD)
    return context, page


def _channels(css):
    """(r, g, b, alpha) of a computed colour in rgb() or color(srgb ...) form."""
    numbers = [float(n) for n in re.findall(r"[-\d.]+", css.split("/")[0])]
    alpha = float(css.split("/")[1].strip(" )")) if "/" in css else 1.0
    if css.startswith("color(srgb"):
        numbers = [n * 255 for n in numbers[:3]]
    return numbers[0], numbers[1], numbers[2], alpha


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _contrast(foreground, background):
    red, green, blue, alpha = _channels(foreground)
    base = _channels(background)
    blended = tuple(alpha * c + (1 - alpha) * b for c, b in zip((red, green, blue), base[:3]))
    lighter, darker = sorted((_luminance(blended), _luminance(base[:3])), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_collection_does_not_overflow_and_its_targets_are_44px(
        new_context, make_app_server, label, viewport, theme, lang):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        assert not _assert_no_page_overflow(page, "collection", viewport["width"])
        columns = page.eval_on_selector(
            ".collection-grid", "el => getComputedStyle(el).gridTemplateColumns.split(' ').length")
        assert columns == (2 if viewport["width"] < 700 else 4)
        for selector in (
                SEEN_CARD, UNSEEN_CARD, ".filter-chip", ".collection-sort select",
                "#collection-filter", ".collection-controls__apply"):
            _wait_owns_centre(page, selector)
            box = page.locator(selector).first.bounding_box()
            assert box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, (selector, box)
            assert page.locator(selector).first.evaluate(_OWNS_CENTRE), selector
        for pill in page.locator(".collection-badge").all():
            assert pill.bounding_box()["height"] >= 44 - 0.5
        assert page.locator(".collection-badge--earned").count() == 1
        assert page.locator(".collection-badge--locked").count() == 4
        assert page.locator(".collection-badge--locked .visually-hidden").first.inner_text(
        ).startswith("Locked" if lang == "en" else "Verrouillé")
        assert page.locator(".collection-progress__bar").bounding_box()["height"] >= 12 - 0.5
    finally:
        context.close()


def test_the_headline_is_the_first_thing_under_the_page_header(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED)
    try:
        first = page.evaluate(
            "() => { const header = document.querySelector('main .page-header');"
            " let el = header.nextElementSibling;"
            " while (el && el.classList.contains('flash-slot')) el = el.nextElementSibling;"
            " return el.querySelector('.collection-progress__headline')"
            " ? el.querySelector('.collection-progress__headline').textContent : null; }")
        assert first is not None and first.startswith("%d of " % TOTAL_SPOTTED)
        assert first.endswith(" airlines spotted")
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_card_opens_its_read_only_sheet_and_escape_returns_to_the_card(
        new_context, make_app_server, label, viewport):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        card = page.locator(SEEN_CARD).first
        target = card.get_attribute("href").lstrip("#")
        card.click()
        page.wait_for_function(
            "id => { const d = document.getElementById(id);"
            " return d.open && d.contains(document.activeElement); }", arg=target, timeout=10000)
        sheet = page.locator("#" + target)
        assert sheet.locator("form, input, button, a[href*='/airlines/']").count() == 0
        assert "Times seen" in sheet.inner_text() and "Rarity" in sheet.inner_text()
        page.keyboard.press("Escape")
        page.wait_for_function(
            "([id, href]) => { const d = document.getElementById(id);"
            " return !d.open && document.activeElement"
            " && document.activeElement.getAttribute('href') === href; }",
            arg=[target, "#" + target], timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_a_dimmed_card_keeps_the_text_of_a_seen_card(new_context, make_app_server, theme):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, theme=theme)
    try:
        probe = (
            "sel => { const card = document.querySelector(sel);"
            " const cs = el => getComputedStyle(el);"
            " const picture = card.querySelector('.collection-card__art');"
            " return {name: cs(card.querySelector('.collection-card__name')).color,"
            " seen: cs(card.querySelector('.collection-card__seen')).color,"
            " background: cs(card).backgroundColor, cardOpacity: cs(card).opacity,"
            " pictureOpacity: cs(picture).opacity, pictureFilter: cs(picture).filter}; }")
        seen = page.evaluate(probe, SEEN_CARD)
        unseen = page.evaluate(probe, UNSEEN_CARD)
        assert unseen["cardOpacity"] == "1" and seen["pictureOpacity"] == "1"
        assert unseen["pictureOpacity"] == "0.45" and "grayscale(1)" in unseen["pictureFilter"]
        assert unseen["name"] == seen["name"] and unseen["seen"] == seen["seen"]
        for colour in (unseen["name"], unseen["seen"]):
            assert _contrast(colour, unseen["background"]) >= 4.5, (theme, colour, unseen)
        assert "Not seen yet" in page.locator(UNSEEN_CARD).first.inner_text()
    finally:
        context.close()


def test_chips_sort_and_the_field_work_through_apply_without_script(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), "/airlines",
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(CARD).count() > TOTAL_SPOTTED
        page.locator("label.filter-chip", has_text="Spotted").click()
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(CARD).count() == TOTAL_SPOTTED
        assert page.locator(UNSEEN_CARD).count() == 0
        page.locator(".collection-sort select").select_option("az")
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        names = page.locator(".collection-card__name").all_inner_texts()
        assert names == sorted(names, key=str.casefold)
        page.fill("#collection-filter", "iberia")
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(".collection-card__name").all_inner_texts() == ["Iberia Airlines"]
        assert "q=iberia" in page.url and "sort=az" in page.url and "show=spotted" in page.url


def test_a_card_opens_its_sheet_through_the_hash_link_without_script(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), "/airlines",
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_function(_SETTLED, timeout=15000)
        card = page.locator(SEEN_CARD).first
        target = card.get_attribute("href").lstrip("#")
        _wait_owns_centre(page, SEEN_CARD)
        card.click()
        page.wait_for_function(
            "id => { const d = document.getElementById(id);"
            " return d && getComputedStyle(d).display !== 'none'"
            " && d.getBoundingClientRect().height > 0; }", arg=target, timeout=10000)
        assert page.locator("#" + target + " a.modal__dismiss").is_visible()


def test_the_text_filter_hides_cards_instantly_with_script(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.fill("#collection-filter", "tap por")
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('.collection-item'))"
            ".filter(li => !li.hidden).length === 1", timeout=10000)
        assert page.locator(".collection-item:not([hidden]) .collection-card__name").inner_text(
        ) == "TAP Portugal"
    finally:
        context.close()


def test_the_collection_is_two_taps_from_home_on_a_phone_and_one_on_desktop(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator(".tab-bar__more > summary").click()
        link = page.locator(".tab-bar__more-panel a", has_text="Airline collection")
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        page.wait_for_url("**/airlines")
        assert page.locator(".collection-progress__headline").is_visible()
    finally:
        context.close()
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_function(_SETTLED, timeout=15000)
        with page.expect_navigation():
            page.locator("nav.sidebar-nav a", has_text="Airline collection").click()
        page.wait_for_url("**/airlines")
        assert page.locator(".collection-progress__headline").is_visible()
    finally:
        context.close()
