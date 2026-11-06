#!/usr/bin/env python3
"""Browser checks for the map of the Location and detection page: tiles, the draggable pin and
its fields, the attribution, the failure modes (tile host down, library blocked) and the Referer
the tile host receives.

Both external hosts are answered by `page.route` (test-support/place_map_support.py): nothing
reaches the network. Waits are on the page's own state (`map-ready`, loaded tiles, settled
animations, a control owning its centre), never fixed sleeps; boxes are measured only after the
finite animations ended and the cross-document view transition is over.
"""
import pytest

from co_manager_browser_support import SUBPIXEL
from companion import auth, page_policy
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _login, _set_ui_theme)
from server import airports
from place_map_support import (
    CLEAR_BOX, DETAILS_SHOWN, HIT_PROBE as _HIT_PROBE, MIN_PX, SETTLED as _SETTLED, Hosts,
    open_details as _open_details, saved_place, seed as _seed, stored as _stored)

pytestmark = pytest.mark.browser

SAVE = "button.dirty-bar__save"
MAP = "#place-map"
READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"
# Finite animations and transitions are over; a never-ending one is not waited for.
ANIMATIONS_DONE = (
    "() => document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")
NOTICE_SHOWN = "() => !document.getElementById('place-notice').hidden"
STATUS_HAS = "text => document.getElementById('place-status').textContent.includes(text)"
PIN_BOX = (
    "() => { const p = document.querySelector('#place-map .place-pin');"
    " if (!p) return null; const r = p.getBoundingClientRect();"
    " return {x: r.left + 22, y: r.top + 42, left: r.left, top: r.top}; }")


def _raised(errors):
    """The page's script errors, minus the browser's own note that a cross-document view
    transition was skipped (it comes from the stylesheet's opt-in, not from any script)."""
    return [e for e in errors if "ViewTransition" not in e]


def _wait_settled(page):
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
    page.wait_for_function(_SETTLED, timeout=10000)
    page.locator(MAP).scroll_into_view_if_needed()
    page.wait_for_function(ANIMATIONS_DONE, timeout=10000)


def _open(new_context, server, viewport, lang="en", theme=None, route="/detection",
          wait_tiles=True, init_script=None, context_options=None, **host_kwargs):
    context = new_context(viewport=viewport, **(context_options or {}))
    if init_script:
        context.add_init_script(init_script)
    hosts = Hosts(context, **host_kwargs)
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_function(READY, timeout=15000)
    if wait_tiles:
        page.wait_for_function(TILES_LOADED, timeout=15000)
    if theme is not None:
        _set_ui_theme(page, theme)
    _wait_settled(page)
    return context, page, hosts, errors


def _map_box(page):
    return page.locator(MAP).bounding_box()


def _tap_map(page, fx, fy):
    """Chooses My position (Airport mode draws a tappable pin for every airport, so a tap
    there may select one), then clicks at the given fractions of the part of the map nothing
    floats over."""
    if not page.is_checked("#place-mode-area"):
        page.click("label.place-mode:has(#place-mode-area)")
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length === 0", timeout=5000)
    box = page.evaluate(CLEAR_BOX)
    x, y = box["x"] + box["width"] * fx, box["y"] + box["height"] * fy
    page.mouse.click(x, y)
    return x, y


def _field(page, field_id):
    return page.locator("#" + field_id).input_value()


def _wait_pin(page, x, y):
    """The pin's tip sits at (x, y) once the marker is placed."""
    page.wait_for_function(
        "args => { const p = document.querySelector('#place-map .place-pin');"
        " if (!p) return false; const r = p.getBoundingClientRect();"
        " return Math.abs(r.left + 22 - args.x) < 3 && Math.abs(r.top + 42 - args.y) < 3; }",
        arg={"x": x, "y": y}, timeout=10000)


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_tap_drops_the_pin_and_fills_the_fields_then_dragging_adjusts_them(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, errors = _open(new_context, server, viewport)
    try:
        if page.locator(MAP + " .place-pin").count():
            raise AssertionError("a pin shows before anything is chosen")
        x, y = _tap_map(page, 0.5, 0.55)
        _wait_pin(page, x, y)
        first = (_field(page, "place-lat"), _field(page, "place-lon"))
        if not first[0] or not first[1]:
            raise AssertionError("the fields stayed empty after a tap: %r" % (first,))
        if len(first[0].split(".")[1]) != 4:
            raise AssertionError("latitude is not rounded to 4 decimals: %r" % first[0])
        page.wait_for_function(STATUS_HAS, arg="Pin placed at %s, %s" % first, timeout=5000)
        pin = page.evaluate(PIN_BOX)
        page.mouse.move(pin["x"], pin["y"] - 10)
        page.mouse.down()
        page.mouse.move(pin["x"] + 50, pin["y"] - 10 + 30, steps=6)
        page.mouse.up()
        page.wait_for_function(
            "before => document.getElementById('place-lat').value !== before",
            arg=first[0], timeout=10000)
        _wait_pin(page, pin["x"] + 50, pin["y"] + 30)
        moved = (_field(page, "place-lat"), _field(page, "place-lon"))
        if moved == first:
            raise AssertionError("dragging did not change the fields")
        if hosts.image_requests:
            raise AssertionError("library images were requested: %r" % hosts.image_requests)
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


def test_typing_coordinates_moves_the_pin(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_details(page)
        page.fill("#place-lat", "45.7578")
        page.fill("#place-lon", "4.8320")
        page.wait_for_function(
            "() => { const p = document.querySelector('#place-map .place-pin');"
            " if (!p) return false;"
            " const m = document.getElementById('place-map').getBoundingClientRect();"
            " const r = p.getBoundingClientRect();"
            " return r.left > m.left && r.right < m.right && r.top > m.top && r.bottom < m.bottom; }",
            timeout=10000)
        if (_field(page, "place-lat"), _field(page, "place-lon")) != ("45.7578", "4.8320"):
            raise AssertionError("the typed fields were rewritten")
    finally:
        context.close()


def test_the_coordinates_are_not_on_the_page_until_their_link_asks_and_a_saved_place_opens_pinned(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, route="/detection?airport=LFPG")
    try:
        if page.evaluate(DETAILS_SHOWN):
            raise AssertionError("the coordinates card shows while the map runs")
        if page.locator(".place-derived, .place-more, .place-saved").count():
            raise AssertionError("the summary line or the saved-settings disclosure is back")
        _open_details(page)
        if not page.is_visible("#details select[name=timezone]"):
            raise AssertionError("the time zone is out of reach through the details link")
        if not page.locator(MAP + " .place-pin").count():
            raise AssertionError("an airport page opens without its pin")
        if page.is_visible(".place-fallback"):
            raise AssertionError("the fallback explanation shows while the map runs")
        if abs(float(_field(page, "place-lat")) - 49.0097) > 0.01:
            raise AssertionError("the pin fields do not hold the airport")
    finally:
        context.close()


CREDITS = "#place-credits"
INFO = "#place-info"


def _open_credits(page):
    page.click(INFO)
    page.wait_for_function(
        "() => !document.getElementById('place-credits').hidden", timeout=5000)


def test_the_attribution_sits_behind_a_round_i_button_on_the_map_and_links_to_the_copyright_page(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        if page.locator(MAP + " .leaflet-control-attribution").count():
            raise AssertionError("the library's own credit strip is back")
        button = page.locator(INFO)
        box = button.bounding_box()
        if box["width"] < MIN_PX - SUBPIXEL or box["height"] < MIN_PX - SUBPIXEL:
            raise AssertionError("the i button is %r" % box)
        if page.is_visible(CREDITS) or button.get_attribute("aria-expanded") != "false":
            raise AssertionError("the credits show before the button is used")
        _open_credits(page)
        if button.get_attribute("aria-expanded") != "true":
            raise AssertionError("aria-expanded did not follow")
        link = page.locator(CREDITS + " .place-credits__attribution a")
        if link.inner_text().strip() != "© OpenStreetMap contributors":
            raise AssertionError("attribution reads %r" % link.inner_text())
        if link.get_attribute("href") != "https://www.openstreetmap.org/copyright":
            raise AssertionError("attribution links to %r" % link.get_attribute("href"))
        if "ODbL" not in page.inner_text(CREDITS) or "Nominatim" not in page.inner_text(CREDITS):
            raise AssertionError("the credits lack the data and search sources")
        popover, viewport = page.locator(CREDITS).bounding_box(), page.viewport_size
        if popover["x"] < -SUBPIXEL or popover["x"] + popover["width"] > viewport["width"] + SUBPIXEL:
            raise AssertionError("the credits leave the viewport: %r" % popover)
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => document.getElementById('place-credits').hidden", timeout=5000)
        _open_credits(page)
        page.mouse.click(8, viewport["height"] / 2)
        page.wait_for_function(
            "() => document.getElementById('place-credits').hidden", timeout=5000)
    finally:
        context.close()


def test_every_tile_request_carries_the_page_origin_as_referer(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        if not hosts.tile_requests:
            raise AssertionError("no tile was requested")
        expected = server.base_url().rstrip("/") + "/"
        bad = [(u, h.get("referer")) for u, h in hosts.tile_requests if h.get("referer") != expected]
        if bad:
            raise AssertionError("tile requests with a wrong Referer (want %r): %r" % (expected, bad[:3]))
        wrong_host = [u for u, _h in hosts.tile_requests
                      if not u.startswith("https://tile.openstreetmap.org/")]
        if wrong_host:
            raise AssertionError("a tile came from another host: %r" % wrong_host)
    finally:
        context.close()


def _assert_controls(page, width):
    failure = _assert_no_page_overflow(page, "/detection", width)
    if failure:
        raise AssertionError(failure)
    selectors = [
        "label.place-mode", "#place-search", "form.place-search button", INFO, "#place-locate",
        "label.runway-card"]
    if width >= 960:
        selectors += [MAP + " .leaflet-control-zoom-in", MAP + " .leaflet-control-zoom-out"]
    failures = page.evaluate(_HIT_PROBE, {"selectors": selectors, "min": MIN_PX - SUBPIXEL})
    if failures:
        raise AssertionError("controls too small or covered at %dpx: %r" % (width, failures))
    box = _map_box(page)
    if box["x"] < -SUBPIXEL or box["x"] + box["width"] > width + SUBPIXEL:
        raise AssertionError("the map leaves the viewport: %r" % box)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_map_page_layout_and_controls(new_context, make_app_server, viewport, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, viewport, lang, theme)
    try:
        _assert_controls(page, viewport["width"])
        if lang == "fr":
            _open_credits(page)
            if page.locator(CREDITS + " .place-credits__attribution a").inner_text() != (
                    "© contributeurs d’OpenStreetMap"):
                raise AssertionError("the attribution is not French")
    finally:
        context.close()


def _save_area_place(server, page):
    """Saving by the pin and the fields works after the map failed."""
    page.click("label.place-mode:has(#place-mode-area)")
    _open_details(page)
    page.fill("#place-label", "Test spot")
    with page.expect_navigation() as info:
        page.click(SAVE)
    if info.value.status != 200:
        raise AssertionError("save ended on HTTP %d" % info.value.status)
    return saved_place(server)


def test_with_the_tile_host_down_the_notice_shows_and_the_pin_still_saves(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, hosts, errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, wait_tiles=False, tiles="abort")
    try:
        page.wait_for_function(NOTICE_SHOWN, timeout=15000)
        text = page.inner_text("#place-notice")
        if text != "The map pictures could not load. The pin and the coordinates still work.":
            raise AssertionError("the notice reads %r" % text)
        if not page.locator("#place-notice").evaluate("el => el.closest('.place-panel') !== null"):
            raise AssertionError("the notice is outside the panel")
        x, y = _tap_map(page, 0.45, 0.5)
        _wait_pin(page, x, y)
        place = _save_area_place(server, page)
        if place is None or place["name"] != "Test spot":
            raise AssertionError("the pin was not saved: %r" % (place,))
        if _stored(server)["mode"] != "position":
            raise AssertionError("mode not stored: %r" % (_stored(server),))
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


def test_with_the_library_blocked_the_plain_form_shows_and_saves(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    hosts = Hosts(context)
    context.route("**/static/vendor/leaflet/leaflet.js", lambda route: route.abort())
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    console = []
    page.on("console", lambda message: console.append(message) if message.type == "error" else None)
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/detection")
        page.wait_for_function(
            "() => document.getElementById('place-map').hidden", timeout=10000)
        page.wait_for_function(_SETTLED, timeout=10000)
        if page.evaluate(READY):
            raise AssertionError("map-ready is set without the library")
        if not page.is_visible(".place-fallback"):
            raise AssertionError("the fallback explanation is hidden")
        if not page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the details card is closed")
        for hidden in ("form.place-search", "#place-locate", INFO, MAP):
            if page.is_visible(hidden):
                raise AssertionError("%s shows without the library" % hidden)
        page.fill("#place-lat", "48.8566")
        page.fill("#place-lon", "2.3522")
        page.fill("#place-label", "Plain form")
        page.click("label.place-mode:has(#place-mode-area)")
        with page.expect_navigation() as info:
            page.click(SAVE)
        if info.value.status != 200:
            raise AssertionError("save ended on HTTP %d" % info.value.status)
        place = saved_place(server)
        if place is None or place["name"] != "Plain form":
            raise AssertionError("the plain form did not save: %r" % (place,))
        own = [m.text for m in console if "leaflet.js" not in m.text and "ERR_" not in m.text
               and "Failed to load resource" not in m.text]
        if _raised(errors) or own:
            raise AssertionError("the page's own scripts raised %r %r" % (errors, own))
        if hosts.image_requests:
            raise AssertionError("library images were requested")
    finally:
        context.close()


def test_the_map_page_keeps_the_policy_headers_of_the_map_policy(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    Hosts(context)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        response = page.goto(server.base_url() + "/detection")
        headers = response.headers
        if headers.get("content-security-policy") != page_policy.MAP_CONTENT_SECURITY_POLICY:
            raise AssertionError("CSP is %r" % headers.get("content-security-policy"))
        if headers.get("permissions-policy") != page_policy.MAP_PERMISSIONS_POLICY:
            raise AssertionError("Permissions-Policy is %r" % headers.get("permissions-policy"))
    finally:
        context.close()



# --- Use my position -----------------------------------------------------------------

LOCATE = "#place-locate"
PARIS_FIX = {"latitude": 48.8566, "longitude": 2.3522, "accuracy": 25}
# Counts getCurrentPosition calls and keeps the options of the last one.
COUNT_CALLS = """
window.__geoCalls = 0;
const real = navigator.geolocation.getCurrentPosition.bind(navigator.geolocation);
navigator.geolocation.getCurrentPosition = function (ok, err, options) {
  window.__geoCalls += 1; window.__geoOptions = options; return real(ok, err, options);
};
"""
# Holds the call open so a test can see the busy state and answer by hand.
HOLD_CALLS = """
window.__geoCalls = 0;
navigator.geolocation.getCurrentPosition = function (ok, err, options) {
  window.__geoCalls += 1; window.__geoOptions = options; window.__geoPending = {ok: ok, err: err};
};
"""
NO_GEOLOCATION = (
    "Object.defineProperty(Navigator.prototype, 'geolocation', {get: () => undefined});")
DENIED = ("Location access is blocked for this site. Allow it in your browser settings, or "
          "search a place, tap the map or pick an airport.")
UNAVAILABLE = "Your position could not be found. Try again outside, or search a place."
TIMED_OUT = "Finding your position took too long. Try again, or search a place."


def _status(page, text):
    page.wait_for_function(
        "text => document.getElementById('place-status').textContent === text", arg=text,
        timeout=10000)


def test_geolocation_is_called_only_on_a_tap_and_moves_the_pin(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, init_script=COUNT_CALLS,
        context_options={"geolocation": PARIS_FIX, "permissions": ["geolocation"]})
    try:
        if page.evaluate("() => window.__geoCalls") != 0:
            raise AssertionError("geolocation was called on load")
        page.click(LOCATE)
        page.wait_for_function(
            "() => document.getElementById('place-lat').value === '48.8566'", timeout=10000)
        if page.input_value("#place-lon") != "2.3522":
            raise AssertionError("longitude is %r" % page.input_value("#place-lon"))
        if page.evaluate("() => window.__geoCalls") != 1:
            raise AssertionError("expected one call")
        options = page.evaluate("() => window.__geoOptions")
        if options != {"enableHighAccuracy": False, "timeout": 10000, "maximumAge": 60000}:
            raise AssertionError("options were %r" % options)
        _status(page, "Position found (about 25 m). Check the pin, then save.")
        if page.inner_text(LOCATE).strip() != "Use my position":
            raise AssertionError("the button label stayed busy: %r" % page.inner_text(LOCATE))
        if page.is_disabled(LOCATE):
            raise AssertionError("the button stayed disabled")
        if not page.locator(MAP + " .place-pin").count():
            raise AssertionError("no pin after the position was found")
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


MESSAGE_HAS = (
    "text => { const m = document.getElementById('place-message');"
    " return !m.hidden && getComputedStyle(m).display !== 'none' && m.textContent === text; }")


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_the_round_locate_button_places_the_pin_and_switches_to_my_position(
        new_context, make_app_server, viewport):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, errors = _open(
        new_context, server, viewport,
        context_options={"geolocation": PARIS_FIX, "permissions": ["geolocation"]})
    try:
        if not page.is_checked("#place-mode-runway"):
            raise AssertionError("the page does not start in Airport mode")
        page.click(LOCATE)
        page.wait_for_function(
            "() => document.getElementById('place-lat').value === '48.8566'", timeout=10000)
        if not page.is_checked("#place-mode-area"):
            raise AssertionError("a found position did not switch to My position")
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-circle')", timeout=5000)
        page.wait_for_function(
            MESSAGE_HAS, arg="Position found (about 25 m). Check the pin, then save.", timeout=5000)
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        clear = page.evaluate(CLEAR_BOX)
        pin = page.evaluate(PIN_BOX)
        if not (clear["x"] <= pin["x"] <= clear["x"] + clear["width"]
                and clear["y"] <= pin["y"] <= clear["y"] + clear["height"] + 42):
            raise AssertionError("the pin %r is not in the clear part of the map %r" % (pin, clear))
        if _raised(errors):
            raise AssertionError("the page raised %r" % errors)
    finally:
        context.close()


def test_a_refused_position_shows_a_short_message_on_the_map(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        page.click(LOCATE)
        page.wait_for_function(MESSAGE_HAS, arg=DENIED, timeout=10000)
        if page.locator(MAP + " .place-pin").count() or not page.is_checked("#place-mode-runway"):
            raise AssertionError("a refusal changed the pin or the mode")
    finally:
        context.close()


def test_the_position_sentence_is_french_on_the_french_page(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, lang="fr",
        context_options={"geolocation": PARIS_FIX, "permissions": ["geolocation"]})
    try:
        page.click(LOCATE)
        _status(page, "Position trouvée (à environ 25 m). Vérifiez le repère, puis enregistrez.")
    finally:
        context.close()


def test_the_busy_state_and_each_error_state_show_their_sentence(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, init_script=HOLD_CALLS)
    try:
        for code, sentence in ((1, DENIED), (2, UNAVAILABLE), (3, TIMED_OUT)):
            page.click(LOCATE)
            page.wait_for_function("() => !!window.__geoPending", timeout=5000)
            if not page.is_disabled(LOCATE):
                raise AssertionError("the button is not disabled while waiting")
            if page.inner_text(LOCATE).strip() != "Looking for your position…":
                raise AssertionError("busy label reads %r" % page.inner_text(LOCATE))
            _status(page, "Looking for your position…")
            page.evaluate("code => { const p = window.__geoPending; window.__geoPending = null;"
                          " p.err({code: code}); }", code)
            _status(page, sentence)
            page.wait_for_function(
                "() => !document.getElementById('place-locate').disabled", timeout=5000)
            if page.inner_text(LOCATE).strip() != "Use my position":
                raise AssertionError("the label did not come back")
        if page.locator(MAP + " .place-pin").count():
            raise AssertionError("an error placed a pin")
        if page.input_value("#place-lat") != "":
            raise AssertionError("an error filled the fields")
    finally:
        context.close()


def test_a_blocked_permission_shows_the_denied_sentence(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, init_script=COUNT_CALLS)
    try:
        page.click(LOCATE)
        _status(page, DENIED)
        if page.evaluate("() => window.__geoCalls") != 1:
            raise AssertionError("expected exactly one call")
    finally:
        context.close()


def test_the_button_is_hidden_when_the_browser_has_no_geolocation(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_MIN_SUPPORTED, init_script=NO_GEOLOCATION)
    try:
        if page.is_visible(LOCATE):
            raise AssertionError("the locate button shows without geolocation")
        if not page.is_visible(MAP):
            raise AssertionError("the map is gone with it")
    finally:
        context.close()


def test_the_locate_button_is_a_44px_target_under_the_search_field(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    for viewport in (VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP):
        context, page, _hosts, _errors = _open(new_context, server, viewport)
        try:
            failures = page.evaluate(
                _HIT_PROBE, {"selectors": [LOCATE, "form.place-search button", "#place-search"],
                             "min": MIN_PX - SUBPIXEL})
            if failures:
                raise AssertionError("controls too small or covered: %r" % failures)
        finally:
            context.close()


# --- Nearest airport and airport dots ------------------------------------------------

NEAREST = "#place-nearest"


def _airport_point(icao, north_km):
    airport = airports.find_airport(icao)
    return airport, "%.4f" % (airport.lat + north_km / 111.0), "%.4f" % airport.lon


def test_a_pin_near_an_airport_offers_to_follow_its_runway(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    airport, lat, lon = _airport_point("LFPG", 1.5)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        if not page.is_hidden(NEAREST):
            raise AssertionError("the offer shows with no pin")
        _open_details(page)
        page.fill("#place-lat", lat)
        page.fill("#place-lon", lon)
        page.wait_for_function(
            "() => !document.getElementById('place-nearest').hidden", timeout=5000)
        want = "Nearest airport: %s, 2 km. Follow its runway?" % airport.name
        if page.inner_text(NEAREST + " .place-nearest__text") != want:
            raise AssertionError("the offer reads %r" % page.inner_text(NEAREST))
        button = page.locator(NEAREST + " button")
        if button.inner_text() != "Follow %s" % airport.name:
            raise AssertionError("the button reads %r" % button.inner_text())
        if button.bounding_box()["height"] < MIN_PX - SUBPIXEL:
            raise AssertionError("the button is under 44 px")
        with page.expect_navigation():
            button.click()
        if "airport=LFPG" not in page.url:
            raise AssertionError("landed on %s" % page.url)
        page.wait_for_function(READY, timeout=15000)
        if not page.is_checked("#place-mode-runway"):
            raise AssertionError("runway mode is not selected")
        if not page.locator("label.runway-card").count():
            raise AssertionError("the airport's runways are not listed")
        if not page.is_hidden(NEAREST):
            raise AssertionError("the offer shows for the airport already followed")
    finally:
        context.close()


def test_a_pin_far_from_every_airport_offers_nothing(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _open_details(page)
        page.fill("#place-lat", "47.0000")
        page.fill("#place-lon", "2.5000")
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
        if not page.is_hidden(NEAREST):
            raise AssertionError("an offer shows far from every airport")
    finally:
        context.close()


def test_airport_pins_choosing_one_follows_its_link(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(
        new_context, server, VIEWPORT_DESKTOP, route="/detection?airport=LFPG")
    try:
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length >= 1", timeout=5000)
        for _ in range(3):
            page.click(MAP + " .leaflet-control-zoom-out")
            page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        # A dot in the part of the map the card leaves clear.
        clear_dot = (
            "() => { const card = document.querySelector('.place-card').getBoundingClientRect();"
            " const own = document.querySelector('input[name=airport][form]').value;"
            " const hit = [...document.querySelectorAll('#place-map .place-dot__mark')].find((d) => {"
            "   const r = d.getBoundingClientRect(); return d.dataset.icao !== own"
            "   && r.left > card.right + 30 && r.right < window.innerWidth - 80"
            "   && r.top > 60 && r.bottom < window.innerHeight - 80; });"
            " return hit ? hit.dataset.icao : null; }")
        page.wait_for_function(clear_dot, timeout=10000)
        icao = page.evaluate(clear_dot)
        dot = page.locator(MAP + " .place-dot:has(.place-dot__mark[data-icao='%s'])" % icao)
        box = dot.bounding_box()
        if box["width"] < MIN_PX - SUBPIXEL or box["height"] < MIN_PX - SUBPIXEL:
            raise AssertionError("a dot hit box is %r" % box)
        with page.expect_navigation():
            dot.click()
        page.wait_for_function(READY, timeout=15000)
        if "airport=%s" % icao not in page.url or not page.is_checked("#place-mode-runway"):
            raise AssertionError("choosing the dot landed on %s" % page.url)
        lfpb = airports.find_airport(icao)
        if abs(float(page.input_value("#place-lat")) - lfpb.lat) > 0.0002:
            raise AssertionError("the pin is not on the chosen airport")
    finally:
        context.close()


def test_the_area_circle_follows_the_radius_and_the_mode(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page, _hosts, _errors = _open(new_context, server, VIEWPORT_DESKTOP)
    try:
        _tap_map(page, 0.5, 0.5)
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-pin')", timeout=5000)
        page.click("label.place-mode:has(#place-mode-runway)")
        page.wait_for_function(
            "() => !document.querySelector('#place-map .place-circle')", timeout=5000)
        page.click("label.place-mode:has(#place-mode-area)")
        page.wait_for_function(
            "() => !!document.querySelector('#place-map .place-circle')", timeout=5000)
        width = "() => document.querySelector('#place-map .place-circle').getBoundingClientRect().width"
        page.fill("#place-radius", "9")
        page.wait_for_function(ANIMATIONS_DONE, timeout=10000)
        small = page.evaluate(width)
        page.fill("#place-radius", "18")
        page.wait_for_function(
            "before => document.querySelector('#place-map .place-circle')"
            ".getBoundingClientRect().width > before * 1.5", arg=small, timeout=5000)
        stroke = page.evaluate(
            "() => getComputedStyle(document.querySelector('#place-map .place-circle')).stroke")
        accent = page.evaluate(
            "() => { const s = document.createElement('i'); s.style.color = 'var(--color-accent)';"
            " document.body.appendChild(s); const c = getComputedStyle(s).color; s.remove(); return c; }")
        if stroke != accent:
            raise AssertionError("circle stroke %r is not the accent %r" % (stroke, accent))
    finally:
        context.close()
