"""Real-browser flow of an administrator opening someone else's frame from
Fleet: the detail header's icon buttons, Open personal view, the Viewing-owner strip, the personal
pages keeping the frame's address, and Back to Fleet. At 360 and 1280 px, in
English and French, light and dark, with 44px hit areas and no sideways
overflow."""
import re

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44

_WORDS = {
    "en": {
        "personal": "Open personal view",
        "viewing": "You are viewing %s’s frame" % fx.OWNER_EMAIL,
        "back": "Back to Fleet"},
    "fr": {
        "personal": "Ouvrir la vue personnelle",
        "viewing": "Vous consultez le cadre de %s" % fx.OWNER_EMAIL,
        "back": "Retour à la flotte"},
}

# True once the control owns its own centre: a cross-document view transition
# is still running until then and hit-testing lands on the root element.
_OWNS_ITS_CENTRE = (
    "(selector) => { const e = document.querySelector(selector);"
    " if (!e) return false; const r = e.getBoundingClientRect();"
    " return document.elementFromPoint(r.left + r.width / 2,"
    " r.top + r.height / 2) === e; }")


_SLAB_COLOURS = (
    "() => { const e = document.querySelector('.frame-notice');"
    " const b = e.querySelector('a');"
    " const s = getComputedStyle(e), l = getComputedStyle(b);"
    " return {bg: s.backgroundColor, fg: s.color, btnBg: l.backgroundColor, btnFg: l.color,"
    " center: getComputedStyle(b).justifyContent, align: getComputedStyle(b).textAlign}; }")


def _luminance(css):
    channels = [int(float(v)) / 255 for v in re.findall(r"[\d.]+", css)[:3]]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _ratio(a, b):
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def _assert_slab_contrast(page, where):
    colours = page.evaluate(_SLAB_COLOURS)
    assert _ratio(colours["bg"], colours["fg"]) >= 7, (where, colours)
    assert _ratio(colours["btnBg"], colours["btnFg"]) >= 7, (where, colours)
    assert colours["center"] == "center" and colours["align"] == "center", (where, colours)


_MARKER_BOXES = (
    "() => { const e = document.querySelector('.frame-notice');"
    " const r = e.getBoundingClientRect(), b = e.querySelector('a').getBoundingClientRect();"
    " const t = e.querySelector('.frame-notice__text').getBoundingClientRect();"
    " return {left: r.left, right: r.right, top: r.top, w: innerWidth, btnH: b.height,"
    " btnW: b.width, btnL: b.left, btnR: b.right, textClip: e.querySelector('.frame-notice__text').scrollWidth"
    " > Math.ceil(t.width) + 1, strong: e.querySelector('strong').textContent}; }")


def _assert_marker_whole(page, where):
    box = page.evaluate(_MARKER_BOXES)
    assert box["btnH"] >= MIN_TAP_PX - 0.5 and box["btnW"] >= MIN_TAP_PX, (where, box)
    assert box["btnL"] >= box["left"] and box["btnR"] <= box["right"] + 0.5, (where, box)
    assert not box["textClip"], (where, box)
    assert box["strong"] == fx.OWNER_EMAIL, (where, box)


def _open_fleet(new_context, server, viewport, lang, scheme):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


def _open_personal_view(page, server, seed, words, viewport):
    row = page.locator(".fleet-head")
    item = row.locator('a.fleet-icon-button[title="%s"]' % words["personal"])
    item.wait_for(state="visible")
    for link in row.locator("a.fleet-icon-button").all():
        box = link.bounding_box()
        assert box["height"] >= MIN_TAP_PX - 0.5 and box["width"] >= MIN_TAP_PX - 0.5
    assert not _assert_no_page_overflow(page, "fleet-header", viewport["width"])
    with page.expect_navigation():
        item.click()
    page.wait_for_url(server.base_url() + "/devices/%s/" % seed.owned_id)
    page.locator(".frame-notice").wait_for(state="visible")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_fleet_to_a_foreign_frame_and_back(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    words = _WORDS[lang]
    where = "scope/%d/%s/%s" % (viewport["width"], lang, scheme)
    context, page, seed = _open_fleet(new_context, server, viewport, lang, scheme)
    try:
        _open_personal_view(page, server, seed, words, viewport)
        strip = page.locator(".frame-notice")
        assert strip.inner_text().startswith(words["viewing"]), where
        assert strip.bounding_box()["height"] >= MIN_TAP_PX
        assert float(strip.evaluate("e => getComputedStyle(e).fontSize")[:-2]) >= 15, where
        assert strip.evaluate("e => getComputedStyle(e).position") == "sticky", where
        _assert_slab_contrast(page, where)
        _assert_marker_whole(page, where)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        page.wait_for_function(_OWNS_ITS_CENTRE, arg=".frame-notice a", timeout=10000)
        _assert_hit_target(page, ".frame-notice a", where)

        # The personal pages keep the frame being viewed.
        prefix = "/devices/%s" % seed.owned_id
        nav = page.locator("nav:visible a[href$='/flights']").first
        assert nav.get_attribute("href") == prefix + "/flights"
        with page.expect_navigation():
            nav.click()
        page.wait_for_url(server.base_url() + prefix + "/flights")
        page.locator(".frame-notice").wait_for(state="visible")

        # Back to Fleet.
        viewed_name = page.locator(".frame-menu__name").first.inner_text().strip()
        page.wait_for_function(_OWNS_ITS_CENTRE, arg=".frame-notice a", timeout=10000)
        with page.expect_navigation():
            page.locator(".frame-notice a", has_text=words["back"]).click()
        page.wait_for_url(server.base_url() + "/fleet?frame=" + seed.owned_id)
        assert re.search(r"/fleet\?frame=%s$" % re.escape(seed.owned_id), page.url)
        page.locator(".fleet-head").wait_for(state="visible")
        assert page.locator(".fleet-head__title").inner_text().strip() == viewed_name, where
    finally:
        context.close()


def test_the_strip_is_absent_on_a_console_page_of_the_same_frame(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open_fleet(
        new_context, server, VIEWPORT_DESKTOP, "en", "light")
    try:
        page.goto(server.base_url() + "/fleet?frame=%s&view=battery" % seed.owned_id)
        page.locator("main").wait_for(state="visible")
        assert page.locator(".frame-notice").count() == 0
        page.goto(server.base_url() + "/devices/%s/flights" % seed.owned_id)
        page.locator(".frame-notice").wait_for(state="visible")
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_marker_shows_on_every_personal_page_and_stays_while_scrolling(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    words = _WORDS[lang]
    context, page, seed = _open_fleet(new_context, server, viewport, lang, scheme)
    try:
        page.route("https://tile.openstreetmap.org/**", lambda route: route.fulfill(status=204))
        for path in ("/", "/flights", "/detection", "/display", "/airlines"):
            where = "scope/%s/%d/%s/%s" % (path, viewport["width"], lang, scheme)
            page.goto(server.base_url() + "/devices/%s%s" % (seed.owned_id, path))
            page.locator(".frame-notice").wait_for(state="visible")
            assert page.locator(".frame-notice").inner_text().startswith(words["viewing"]), where
            assert not _assert_no_page_overflow(page, where, viewport["width"])
            _assert_slab_contrast(page, where)
            _assert_marker_whole(page, where)
            page.evaluate("document.querySelector('main').style.minHeight = '4000px'")
            page.evaluate("window.scrollTo(0, 1200)")
            page.wait_for_function("window.scrollY > 600")
            top = page.evaluate(
                "document.querySelector('.frame-notice').getBoundingClientRect().top")
            assert -0.5 <= top <= 60, (where, top)
    finally:
        context.close()


def test_a_long_owner_address_wraps_whole_and_keeps_the_button(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open_fleet(
        new_context, server, VIEWPORT_MIN_SUPPORTED, "en", "light")
    try:
        page.goto(server.base_url() + "/devices/%s/flights" % seed.owned_id)
        page.locator(".frame-notice").wait_for(state="visible")
        page.evaluate(
            "document.querySelector('.frame-notice strong').textContent ="
            " 'camille.durand.longue-adresse.pour-test@sous-domaine.exemple-entreprise.example.test'")
        box = page.evaluate(_MARKER_BOXES)
        assert not box["textClip"] and box["btnH"] >= MIN_TAP_PX - 0.5, box
        assert not _assert_no_page_overflow(page, "long", 360)
        assert page.evaluate(
            "getComputedStyle(document.querySelector('.frame-notice__text')).textOverflow") \
            == "clip"
    finally:
        context.close()
