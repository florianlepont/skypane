#!/usr/bin/env python3
"""Browser checks for the per-device Detection page: the scripts-blocked flow, the hidden-panel
submit rule per mode, measured layout and hit targets, the Search button's quiet style against
the accent Save, and (scripts on) the dirty bar, Cancel and leave-guard behaviour.

Every server is function-scoped because most checks save a setting. Layout numbers are measured
on the rendered page in the control's own container, never read from the stylesheet.
"""
import os

import pytest

from companion import auth
from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from server import airports, device_config, device_dirs, fleet_db, hardware
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow,
    _bar_text, _guard_armed, _login, _no_js_page, _wait_for_bar, _wait_for_bar_hidden,
)

pytestmark = pytest.mark.browser

SEARCH = "cdg"
CDG = "LFPG"
CDG_RUNWAY = "08L/26R"
OTHER_CDG_RUNWAY = "09L/27R"
RADIUS_ERROR = "Enter a whole number of kilometres from 2 to 28."
RUNWAY_ERROR = "Choose a runway."
AIRPORT_ERROR = "Choose an airport."
SAVE = "button.dirty-bar__save"
SEARCH_BUTTON = "button.detection-search"
MODE_RUNWAY_LABEL = "label[for=detection-mode-runway]"
MODE_POSITION_LABEL = "label[for=detection-mode-position]"


def _seed(detection=None):
    """A seed(state_dir) callback: the signed-in administrator owns one in-France location
    named Home, and `detection`, when given, is the stored setting."""
    def seed(state_dir):
        session_cookie_for_state_dir(state_dir)
        conn = fleet_db.connect(state_dir)
        try:
            owner = fleet_db.get_user_by_email(conn, TEST_ADMIN_EMAIL)["id"]
            fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
            fleet_db.add_device(
                conn, "aa:bb:cc:00:00:04", "d" * 64, hardware.LEGACY_KEY, owner,
                name="Live frame", state_path=device_dirs.LIVE_STATE_PATH)
            fleet_db.add_location(conn, "Home", 48.8566, 2.3522, "Europe/Paris",
                                  owner_user_id=owner)
        finally:
            conn.close()
        if detection is not None:
            device_config.save_device_config(state_dir, detection=detection)
    return seed


SAVED_RUNWAY = {"mode": "runway", "airport": CDG, "runway": CDG_RUNWAY}
SAVED_POSITION = {"mode": "position", "radius_km": 7}


def _stored(server):
    return device_config.load_device_config(server.state_dir).get("detection")


def _config_bytes(server):
    path = device_config.device_config_path(server.state_dir)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def _lang(base_url, lang):
    return [{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}]


def _largest_airport():
    return max(airports.load_catalogue().values(), key=lambda a: len(a.runways))


def _submit(page, selector):
    """Click a submit control and return the response of the navigation it causes."""
    with page.expect_navigation() as info:
        page.click(selector)
    return info.value


def _inline_errors(page):
    return [el.inner_text().strip() for el in page.query_selector_all(".field-error")]


# Scripts blocked.

@pytest.mark.parametrize("lang,search_button", [
    ("en", "Search airports"), ("fr", "Rechercher des aéroports")])
def test_no_js_search_pick_save_360(new_context, make_app_server, lang, search_button):
    """Scripts blocked at 360 px: search, pick the airport through its result link, choose a
    runway card and save with the visible Save; the setting is read back from disk."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/detection", viewport=VIEWPORT_MIN_SUPPORTED,
                     cookies=_lang(base_url, lang)) as page:
        page.fill("#airport-q", SEARCH)
        if page.inner_text(SEARCH_BUTTON).strip() != search_button:
            raise AssertionError("lang=%s: unexpected search button label" % lang)
        _submit(page, SEARCH_BUTTON)
        result = page.locator("a.detection-result", has_text="Charles de Gaulle").first
        with page.expect_navigation():
            result.click()
        page.click("label.runway-card:has(input[value='%s'])" % CDG_RUNWAY)
        response = _submit(page, SAVE)
        if response.status != 200:
            raise AssertionError("lang=%s: save ended on HTTP %d" % (lang, response.status))
    if _stored(server) != SAVED_RUNWAY:
        raise AssertionError("lang=%s: disk holds %r" % (lang, _stored(server)))


def test_hidden_panel_runway_valid_position_invalid(new_context, make_app_server):
    """Airport and runway mode with a valid runway saves while the hidden position panel holds
    an invalid radius: native validation never blocks the submit."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/detection", viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click(MODE_POSITION_LABEL)
        page.fill("#detection-radius", "99")
        page.click(MODE_RUNWAY_LABEL)
        if page.is_visible("#detection-radius"):
            raise AssertionError("the position panel is still visible in runway mode")
        page.click("label.runway-card:has(input[value='%s'])" % OTHER_CDG_RUNWAY)
        response = _submit(page, SAVE)
        if response.status != 200 or _inline_errors(page):
            raise AssertionError(
                "the save was refused: %r" % (_inline_errors(page),))
    expected = {"mode": "runway", "airport": CDG, "runway": OTHER_CDG_RUNWAY}
    if _stored(server) != expected:
        raise AssertionError("disk holds %r, expected %r" % (_stored(server), expected))


def test_hidden_panel_position_valid_runway_unchecked(new_context, make_app_server):
    """Around a location with a valid location and radius saves while the hidden runway panel
    lists an airport's runways with none checked."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    base_url = server.base_url()
    route = "/detection?airport=%s&mode=position" % CDG
    with _no_js_page(new_context, base_url, route, viewport=VIEWPORT_MIN_SUPPORTED) as page:
        if not page.locator("input[name=runway]").count():
            raise AssertionError("the hidden runway panel lists no runway cards")
        if page.locator("input[name=runway]:checked").count():
            raise AssertionError("a runway is checked; the case needs none")
        if page.is_visible("input[name=runway] >> nth=0"):
            raise AssertionError("the runway panel is visible in position mode")
        page.fill("#detection-radius", "9")
        response = _submit(page, SAVE)
        if response.status != 200 or _inline_errors(page):
            raise AssertionError("the save was refused: %r" % (_inline_errors(page),))
    if _stored(server) != {"mode": "position", "radius_km": 9}:
        raise AssertionError("disk holds %r" % (_stored(server),))
    conn = fleet_db.connect(server.state_dir)
    try:
        located = [row for row in fleet_db.list_locations(conn)]
    finally:
        conn.close()
    if len(located) != 1:
        raise AssertionError("the seeded location disappeared")


@pytest.mark.parametrize("name,seed_detection,route,mode_label,prepare,expected", [
    ("runway-missing", None, "/detection?airport=%s&mode=runway" % CDG, None, None, RUNWAY_ERROR),
    ("airport-missing", SAVED_POSITION, "/detection", MODE_RUNWAY_LABEL, None, AIRPORT_ERROR),
    ("radius-missing", None, "/detection", MODE_POSITION_LABEL, ("#detection-radius", ""),
     RADIUS_ERROR),
    ("radius-too-big", None, "/detection", MODE_POSITION_LABEL, ("#detection-radius", "99"),
     RADIUS_ERROR),
])
def test_missing_value_inline_error_per_mode(
        new_context, make_app_server, name, seed_detection, route, mode_label, prepare,
        expected):
    """Each mode with its own value missing answers HTTP 200 with the exact inline error and
    leaves the stored file byte for byte unchanged."""
    server = make_app_server(seed=_seed(seed_detection), fake_providers=True)
    base_url = server.base_url()
    before = _config_bytes(server)
    with _no_js_page(new_context, base_url, route, viewport=VIEWPORT_MIN_SUPPORTED) as page:
        if mode_label:
            page.click(mode_label)
        if prepare:
            page.fill(*prepare)
        response = _submit(page, SAVE)
        if response.status != 200:
            raise AssertionError("%s: HTTP %d" % (name, response.status))
        if expected not in _inline_errors(page):
            raise AssertionError(
                "%s: expected %r, the page shows %r" % (name, expected, _inline_errors(page)))
    if _config_bytes(server) != before:
        raise AssertionError("%s: a refused save changed the stored file" % name)


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE])
def test_no_horizontal_overflow_and_hit_targets_360(new_context, make_app_server, viewport):
    """With the airport that has the most runways, the page does not scroll sideways, and every
    result row and runway card measures at least 44 px in both axes in its own container."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    base_url = server.base_url()
    biggest = _largest_airport()
    if len(biggest.runways) < 3:
        raise AssertionError("the catalogue has no airport with many runways")
    probe = (
        "sel => [...document.querySelectorAll(sel)].map(el => {"
        " const r = el.getBoundingClientRect(); return [r.width, r.height]; })")
    for route, selector in (
            ("/detection?q=lf", "a.detection-result"),
            ("/detection?airport=%s&mode=runway" % biggest.icao, "label.runway-card")):
        with _no_js_page(new_context, base_url, route, viewport=viewport) as page:
            failure = _assert_no_page_overflow(page, route, viewport["width"])
            if failure:
                raise AssertionError(failure)
            boxes = page.evaluate(probe, selector)
            if selector == "label.runway-card" and len(boxes) != len(biggest.runways):
                raise AssertionError(
                    "expected %d runway cards, found %d" % (len(biggest.runways), len(boxes)))
            if not boxes:
                raise AssertionError("%s matched nothing on %s" % (selector, route))
            small = [b for b in boxes if b[0] < 44 or b[1] < 44]
            if small:
                raise AssertionError(
                    "%s under 44 px at %dpx on %s: %r" % (selector, viewport["width"], route,
                                                         small))


def test_mode_segments_wrap_without_clipping_in_french(new_context, make_app_server):
    """The two mode segments stay inside their box in French at 360 px and measure 44 px."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/detection", viewport=VIEWPORT_MIN_SUPPORTED,
                     cookies=_lang(base_url, "fr")) as page:
        rows = page.evaluate(
            "() => [...document.querySelectorAll('.detection-modes .theme-form label')]"
            ".map(el => [el.scrollWidth, el.clientWidth, el.getBoundingClientRect().height,"
            " el.textContent.trim()])")
        failure = _assert_no_page_overflow(page, "/detection (fr)", 360)
    if failure:
        raise AssertionError(failure)
    if len(rows) != 2:
        raise AssertionError("expected two mode segments, found %r" % (rows,))
    for scroll_w, client_w, height, text in rows:
        if scroll_w > client_w or height < 44:
            raise AssertionError(
                "segment %r is clipped or short: scroll %s, client %s, height %s"
                % (text, scroll_w, client_w, height))


_STYLE_PROBE = (
    "sel => { const el = document.querySelector(sel); const s = getComputedStyle(el);"
    " return {bg: s.backgroundColor, h: el.getBoundingClientRect().height}; }")


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP])
def test_search_button_is_not_accent_and_44px(new_context, make_app_server, viewport):
    """The Search airports button is the quiet wash, not the accent fill the Save button
    carries, and is at least 44 px tall at both widths."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/detection", viewport=viewport) as page:
        search = page.evaluate(_STYLE_PROBE, SEARCH_BUTTON)
        save = page.evaluate(_STYLE_PROBE, SAVE)
    if save["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
        raise AssertionError("the Save button has no fill, so the comparison means nothing")
    if search["bg"] == save["bg"]:
        raise AssertionError("the Search button wears the accent fill %s" % search["bg"])
    if search["h"] < 44:
        raise AssertionError("the Search button is %.1f px tall at %dpx" % (
            search["h"], viewport["width"]))


def test_accent_budget(new_context, make_app_server):
    """The accent fill (derived from the Save button) is painted only on the Save buttons and
    the selected mode segment: never on a result row, a summary value or a runway card."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    probe = (
        "accent => [...document.querySelectorAll('body *')].filter("
        " el => getComputedStyle(el).backgroundColor === accent)"
        ".map(el => el.tagName.toLowerCase() + '.' + el.className.toString().trim()"
        " + '|' + (el.htmlFor || ''))")
    allowed = ("dirty-bar__save", "detection-location-save", "|detection-mode-", "skip-link")
    for route in ("/detection?q=lf", "/detection?airport=%s&mode=runway" % CDG):
        with _no_js_page(new_context, server.base_url(), route,
                         viewport=VIEWPORT_MIN_SUPPORTED) as page:
            accent = page.evaluate(_STYLE_PROBE, SAVE)["bg"]
            painted = page.evaluate(probe, accent)
        if not any("dirty-bar__save" in item for item in painted):
            raise AssertionError("%s: the accent probe did not find the Save button" % route)
        stray = [item for item in painted if not any(token in item for token in allowed)]
        if stray:
            raise AssertionError("%s: accent fill on %r" % (route, stray))


# Scripts on.

def _open(new_context, server, route="/detection", lang=None, viewport=VIEWPORT_MIN_SUPPORTED):
    context = new_context(viewport=viewport)
    if lang:
        context.add_cookies(_lang(server.base_url(), lang))
    page = context.new_page()
    _login(page, server.base_url())
    dialogs = []

    def on_dialog(dialog):
        dialogs.append(dialog.type)
        dialog.accept()

    page.on("dialog", on_dialog)
    page.goto(server.base_url() + route)
    return page, dialogs


@pytest.mark.parametrize("lang,section", [("en", "Detection"), ("fr", "Détection")])
def test_mode_toggle_reveals_dirty_bar_and_cancel_restores(new_context, make_app_server,
                                                          lang, section):
    """Toggling the mode reveals the bar naming the Detection section, the inactive panel is
    out of the layout, and Cancel puts the saved mode back and hides the bar."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, _dialogs = _open(new_context, server, lang=lang)
    _wait_for_bar_hidden(page)
    page.click(MODE_POSITION_LABEL)
    _wait_for_bar(page)
    suffix = page.get_attribute("[data-dirty-bar]", "data-dirty-changed-suffix")
    if _bar_text(page).strip() != section + suffix:
        raise AssertionError("lang=%s: the bar reads %r" % (lang, _bar_text(page)))
    if lang == "en" and _bar_text(page).strip() != "Detection changed":
        raise AssertionError("the English bar reads %r" % _bar_text(page))
    display = page.eval_on_selector(
        ".detection-panel--runway", "el => getComputedStyle(el).display")
    tabbable = page.eval_on_selector(
        "input[name=runway]", "el => el.offsetParent === null")
    if display != "none" or not tabbable:
        raise AssertionError("the inactive runway panel is still in the layout")
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    if not page.is_checked("#detection-mode-runway"):
        raise AssertionError("Cancel did not restore the saved mode")


def _carry_radius_through_a_search(page):
    """Type a radius in position mode, search and pick an airport in runway mode, then switch
    back to position mode."""
    page.click(MODE_POSITION_LABEL)
    page.fill("#detection-radius", "12")
    page.click(MODE_RUNWAY_LABEL)
    page.fill("#airport-q", SEARCH)
    with page.expect_navigation():
        page.click(SEARCH_BUTTON)
    with page.expect_navigation():
        page.locator("a.detection-result", has_text="Charles de Gaulle").first.click()
    page.click(MODE_POSITION_LABEL)


def test_search_after_toggle_does_not_raise_leave_guard_and_keeps_radius(
        new_context, make_app_server):
    """The page's own search and pick navigations raise no leave prompt, and the radius typed
    before them is still there, with the bar visible and marked as carried."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, dialogs = _open(new_context, server)
    _carry_radius_through_a_search(page)
    if dialogs:
        raise AssertionError("the page's own navigations raised %r" % dialogs)
    if page.input_value("#detection-radius") != "12":
        raise AssertionError("the radius reads %r" % page.input_value("#detection-radius"))
    _wait_for_bar(page)
    if page.get_attribute("[data-dirty-bar]", "data-dirty-carried") is None:
        raise AssertionError("the bar is not marked as carrying unsaved values")
    if not _guard_armed(page):
        raise AssertionError("the leave guard is not armed on the carried state")


def test_cancel_in_carried_state_returns_to_stored_value(new_context, make_app_server):
    """Cancel on the carried state goes to the plain page and shows the stored radius."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, _dialogs = _open(new_context, server)
    _carry_radius_through_a_search(page)
    _wait_for_bar(page)
    with page.expect_navigation():
        page.click("[data-dirty-cancel]")
    if page.url.split("#")[0] != server.base_url() + "/detection":
        raise AssertionError("Cancel landed on %s" % page.url)
    if not page.is_checked("#detection-mode-position"):
        page.click(MODE_POSITION_LABEL)
    if page.input_value("#detection-radius") != "7":
        raise AssertionError("the radius reads %r" % page.input_value("#detection-radius"))


def test_real_leave_still_prompts(new_context, make_app_server):
    """An unsaved edit followed by a click on another page's link still raises the prompt."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, dialogs = _open(new_context, server)
    page.click(MODE_POSITION_LABEL)
    _wait_for_bar(page)
    page.click("a.text-link.detection-link")
    page.wait_for_load_state()
    if "beforeunload" not in dialogs:
        raise AssertionError("leaving with an unsaved edit raised no prompt: %r" % dialogs)


def test_back_forward_cache_rearms_guard(new_context, make_app_server):
    """After a page-local navigation and a trip back, an unsaved edit is guarded again."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, dialogs = _open(new_context, server)
    page.click(MODE_RUNWAY_LABEL)
    page.fill("#airport-q", SEARCH)
    with page.expect_navigation():
        page.click(SEARCH_BUTTON)
    page.go_back()
    page.wait_for_load_state()
    page.click(MODE_RUNWAY_LABEL)
    page.click(MODE_POSITION_LABEL)
    page.fill("#detection-radius", "11")
    _wait_for_bar(page)
    if not _guard_armed(page):
        raise AssertionError("the guard stayed disarmed after returning to the page")
    del dialogs[:]
    page.click("a.text-link.detection-link")
    page.wait_for_load_state()
    if "beforeunload" not in dialogs:
        raise AssertionError("a later real leave raised no prompt: %r" % dialogs)
