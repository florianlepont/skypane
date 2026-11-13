#!/usr/bin/env python3
"""Browser checks for the per-device Location and detection page: the scripts-blocked flow, the
submit rule per mode, the Search button's quiet style against the accent Save, and (scripts on)
the dirty bar, Cancel and leave-guard behaviour. Layout and hit targets are measured in
test_browser_place_page.py.

Every server is function-scoped because most checks save a setting. Layout numbers are measured
on the rendered page in the control's own container, never read from the stylesheet.
"""
import os
import re

import pytest

from co_manager_browser_support import SUBPIXEL
from co_manager_browser_support import Rig as UserRig
from co_manager_browser_support import _open as _open_as
from place_map_support import Hosts, open_details
from companion import auth
from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from server import airports, device_config, device_dirs, fleet_db, hardware
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow, _bar_text, _guard_armed, _login, _no_js_page, _wait_for_bar, _wait_for_bar_hidden,
)

pytestmark = pytest.mark.browser

SEARCH = "cdg"
CDG = "LFPG"
CDG_RUNWAY = "08L/26R"
OTHER_CDG_RUNWAY = "09L/27R"
RADIUS_ERROR = "Enter a whole number of kilometres from 2 to 28."
RUNWAY_ERROR = "Choose a runway."
AIRPORT_ERROR = "Choose an airport."
NUMBER_ERROR = "Enter a number such as 48.8566."
PARIS = "Europe/Paris"
SAVE = "button.dirty-bar__save"
SEARCH_BUTTON = "#airport-filter-submit"
MODE_RUNWAY_LABEL = "label:has(#place-mode-runway)"
MODE_AREA_LABEL = "label:has(#place-mode-area)"


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


def _place(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        device = [d for d in fleet_db.list_devices(conn)][0]
        return fleet_db.frame_position(conn, device["id"])
    finally:
        conn.close()


def _config_bytes(server):
    path = device_config.device_config_path(server.state_dir)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as handle:
        return handle.read()


def _lang(base_url, lang):
    return [{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}]


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
def test_no_js_filter_pick_save_360(new_context, make_app_server, lang, search_button):
    """Scripts blocked at 360 px: filter the airport list, pick the airport through its link,
    choose a runway card and save with the visible Save; the setting and the airport's position
    are read back from disk, and the fallback explanation and the open details card show."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/detection?mode=runway", viewport=VIEWPORT_MIN_SUPPORTED,
                     cookies=_lang(base_url, lang)) as page:
        if not page.is_visible(".place-fallback") or page.is_visible("#place-map"):
            raise AssertionError("the no-script fallback is not what shows")
        if not page.eval_on_selector("#details", "el => el.open"):
            raise AssertionError("the details card is closed without scripts")
        page.fill("#airport-filter", SEARCH)
        if page.inner_text(SEARCH_BUTTON).strip() != search_button:
            raise AssertionError("lang=%s: unexpected search button label" % lang)
        _submit(page, SEARCH_BUTTON)
        with page.expect_navigation():
            page.click("a.place-airport__link[data-icao=%s]" % CDG)
        page.click("label.runway-card:has(input[value='%s'])" % CDG_RUNWAY)
        response = _submit(page, SAVE)
        if response.status != 200:
            raise AssertionError("lang=%s: save ended on HTTP %d" % (lang, response.status))
        if _inline_errors(page):
            raise AssertionError("lang=%s: errors after the save: %r" % (lang, _inline_errors(page)))
    if _stored(server) != SAVED_RUNWAY:
        raise AssertionError("lang=%s: disk holds %r" % (lang, _stored(server)))
    place = _place(server)
    airport = airports.find_airport(CDG)
    if place is None or (place["latitude"], place["longitude"]) != (
            round(airport.lat, 4), round(airport.lon, 4)):
        raise AssertionError("lang=%s: the position row is %r" % (lang, place))


def test_no_js_typed_coordinates_save_in_area_mode(new_context, make_app_server):
    """Scripts blocked: latitude, longitude, label, radius and time zone typed into the fields
    and saved in the area mode store the same data the map would."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    with _no_js_page(new_context, server.base_url(), "/detection",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click(MODE_AREA_LABEL)
        page.fill("#place-lat", "43.2965")
        page.fill("#place-lon", "5.3698")
        page.fill("#place-label", "Marseille")
        page.fill("#place-radius", "14")
        page.select_option("#place-timezone", PARIS)
        response = _submit(page, SAVE)
        if response.status != 200 or _inline_errors(page):
            raise AssertionError("the save was refused: %r" % (_inline_errors(page),))
        if "Detection now follows the area within 14 km of Marseille" not in page.inner_text("body"):
            raise AssertionError("the saved toast does not name the place")
    if _stored(server) != {"mode": "position", "radius_km": 14}:
        raise AssertionError("disk holds %r" % (_stored(server),))
    place = _place(server)
    if (place["name"], place["latitude"], place["longitude"]) != ("Marseille", 43.2965, 5.3698):
        raise AssertionError("the position row is %r" % (place,))


def test_native_validation_never_blocks_a_save_with_the_other_modes_fields_invalid(
        new_context, make_app_server):
    """Runway mode saves while the radius holds an invalid value and the area mode saves
    while no runway is checked: the form is novalidate and only the posted mode is checked."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    base_url = server.base_url()
    with _no_js_page(new_context, base_url, "/detection", viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click(MODE_AREA_LABEL)
        page.fill("#place-radius", "99")
        page.click(MODE_RUNWAY_LABEL)
        page.click("label.runway-card:has(input[value='%s'])" % OTHER_CDG_RUNWAY)
        response = _submit(page, SAVE)
        if response.status != 200 or _inline_errors(page):
            raise AssertionError("the save was refused: %r" % (_inline_errors(page),))
    expected = {"mode": "runway", "airport": CDG, "runway": OTHER_CDG_RUNWAY}
    if _stored(server) != expected:
        raise AssertionError("disk holds %r, expected %r" % (_stored(server), expected))
    with _no_js_page(new_context, base_url, "/detection", viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click(MODE_AREA_LABEL)
        page.fill("#place-lat", "43.3")
        page.fill("#place-lon", "5.4")
        page.fill("#place-radius", "9")
        response = _submit(page, SAVE)
        if response.status != 200 or _inline_errors(page):
            raise AssertionError("the save was refused: %r" % (_inline_errors(page),))
    if _stored(server) != {"mode": "position", "radius_km": 9}:
        raise AssertionError("disk holds %r" % (_stored(server),))


@pytest.mark.parametrize("name,seed_detection,route,mode_label,prepare,expected", [
    ("airport-missing", SAVED_POSITION, "/detection", MODE_RUNWAY_LABEL, None, AIRPORT_ERROR),
    ("latitude-missing", None, "/detection", MODE_AREA_LABEL, ("#place-lat", ""), NUMBER_ERROR),
    ("radius-missing", None, "/detection", MODE_AREA_LABEL, ("#place-radius", ""),
     RADIUS_ERROR),
    ("radius-too-big", None, "/detection", MODE_AREA_LABEL, ("#place-radius", "99"),
     RADIUS_ERROR),
])
def test_missing_value_inline_error_per_mode(
        new_context, make_app_server, name, seed_detection, route, mode_label, prepare,
        expected):
    """Each mode with its own value missing answers HTTP 400 with the exact inline error and
    leaves the stored file byte for byte unchanged."""
    server = make_app_server(seed=_seed(seed_detection), fake_providers=True)
    base_url = server.base_url()
    before = _config_bytes(server)
    with _no_js_page(new_context, base_url, route, viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.click(mode_label)
        if name.startswith("latitude") or name.startswith("radius"):
            page.fill("#place-lat", "43.3")
            page.fill("#place-lon", "5.4")
        if prepare:
            page.fill(*prepare)
        response = _submit(page, SAVE)
        if response.status != 400:
            raise AssertionError("%s: HTTP %d" % (name, response.status))
        if expected not in _inline_errors(page):
            raise AssertionError(
                "%s: expected %r, the page shows %r" % (name, expected, _inline_errors(page)))
    if _config_bytes(server) != before:
        raise AssertionError("%s: a refused save changed the stored file" % name)


_STYLE_PROBE = (
    "sel => { const el = document.querySelector(sel); const s = getComputedStyle(el);"
    " return {bg: s.backgroundColor, h: el.getBoundingClientRect().height}; }")


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP])
def test_search_button_is_not_accent_and_44px(new_context, make_app_server, viewport):
    """The Search airports button is the quiet wash, not the accent fill the Save button
    carries, and is at least 44 px tall at both widths."""
    server = make_app_server(seed=_seed(), fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/detection?mode=runway", viewport=viewport) as page:
        search = page.evaluate(_STYLE_PROBE, SEARCH_BUTTON)
        save = page.evaluate(_STYLE_PROBE, SAVE)
    if save["bg"] in ("rgba(0, 0, 0, 0)", "transparent"):
        raise AssertionError("the Save button has no fill, so the comparison means nothing")
    if search["bg"] == save["bg"]:
        raise AssertionError("the Search button wears the accent fill %s" % search["bg"])
    if search["h"] < 44 - SUBPIXEL:
        raise AssertionError("the Search button is %.1f px tall at %dpx" % (
            search["h"], viewport["width"]))


def test_accent_budget(new_context, make_app_server):
    """The accent fill (derived from the Save button) is painted only on the Save buttons (and
    the current segment of the space switch an administrator sees, and the selected segment of
    the mode switch and the theme and language switches, graphite pills by the segmented-control rule, the current sidebar item,
    the current tab bar pill, the icon chip of the frame popover's Add row and the icon tile of the More panel's Console card): never on an airport row, a summary value or a
    runway card. A closed dialog's own primary action (the unsaved-changes question) is not
    painted and is left out."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    probe = (
        "accent => [...document.querySelectorAll('body *')].filter("
        " el => !el.closest('dialog') && getComputedStyle(el).backgroundColor === accent)"
        ".map(el => el.tagName.toLowerCase() + '.' + el.className.toString().trim()"
        " + '|' + (el.htmlFor || ''))")
    allowed = ("dirty-bar__save", "skip-link", "space-switch__segment--current", "place-mode",
               "sidebar-link--active", "frame-row__icon", "tab-bar__pill", "tab-bar__slider",
               "theme-option--active", "link-card__icon")
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
    Hosts(context)
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
    if route.startswith("/detection"):
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    return page, dialogs


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_mode_toggle_reveals_dirty_bar_and_cancel_restores(new_context, make_app_server, lang):
    """Choosing the other mode reveals the bar with the one message every page uses, and Cancel
    puts the saved mode back and hides the bar."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, _dialogs = _open(new_context, server, lang=lang)
    _wait_for_bar_hidden(page)
    page.click(MODE_AREA_LABEL)
    _wait_for_bar(page)
    expected = page.get_attribute("[data-dirty-bar]", "data-dirty-initial-text")
    if _bar_text(page).strip() != expected:
        raise AssertionError("lang=%s: the bar reads %r" % (lang, _bar_text(page)))
    if lang == "en" and _bar_text(page).strip() != "Unsaved changes":
        raise AssertionError("the English bar reads %r" % _bar_text(page))
    page.click("[data-dirty-cancel]")
    _wait_for_bar_hidden(page)
    page.wait_for_function("() => document.getElementById('place-mode-runway').checked")


@pytest.mark.parametrize("lang,sections", [("en", "Detection, Place"), ("fr", "Détection, Lieu")])
def test_changing_both_areas_names_them_after_the_message(new_context, make_app_server, lang,
                                                          sections):
    """On a wide screen the page name only shows when several areas changed: the same message, a
    colon and the list of the areas."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, _dialogs = _open(new_context, server, lang=lang, viewport=VIEWPORT_DESKTOP)
    _wait_for_bar_hidden(page)
    page.click(MODE_AREA_LABEL)
    open_details(page)
    page.fill("#place-lat", "43.1")
    lead = page.get_attribute("[data-dirty-bar]", "data-dirty-several")
    page.wait_for_function(
        "expected => document.querySelector('[data-dirty-count]').textContent === expected",
        arg="%s %s" % (lead, sections), timeout=10000)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_on_a_phone_changing_both_areas_keeps_the_short_message(new_context, make_app_server, lang):
    """the one-line message of a phone's bar never holds the list of areas (it would be cut)"""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, _dialogs = _open(new_context, server, lang=lang)
    _wait_for_bar_hidden(page)
    page.click(MODE_AREA_LABEL)
    open_details(page)
    page.fill("#place-lat", "43.1")
    expected = page.get_attribute("[data-dirty-bar]", "data-dirty-initial-text")
    page.wait_for_function(
        "expected => document.querySelector('[data-dirty-count]').textContent === expected",
        arg=expected, timeout=10000)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_editing_a_coordinate_reads_the_one_message(new_context, make_app_server, lang):
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, _dialogs = _open(new_context, server, lang=lang)
    _wait_for_bar_hidden(page)
    open_details(page)
    page.fill("#place-lat", "43.1")
    _wait_for_bar(page)
    expected = page.get_attribute("[data-dirty-bar]", "data-dirty-initial-text")
    if _bar_text(page).strip() != expected:
        raise AssertionError("lang=%s: the bar reads %r" % (lang, _bar_text(page)))


def _follow_airport_link(page):
    """Follow the airport list's link for CDG. The list is built by the page's script, so the
    link is awaited before it is clicked."""
    link = ".place-airport__link[data-icao='%s']" % CDG
    page.wait_for_selector(link, state="attached")
    with page.expect_navigation():
        page.evaluate("selector => document.querySelector(selector).click()", link)


def _carry_radius_through_a_filter(page):
    """Type a radius in the area mode, then follow the airport list's own link (a page-local
    navigation: the list stays in the page for the plain form and when the map cannot run;
    the map's own picks update the page in place)."""
    page.click(MODE_AREA_LABEL)
    page.fill("#place-radius", "12")
    page.click(MODE_RUNWAY_LABEL)
    _follow_airport_link(page)


def test_filter_and_pick_do_not_raise_leave_guard_and_keep_radius(new_context, make_app_server):
    """The page's own filter and pick navigations raise no leave prompt, and the radius typed
    before them is still there, with the bar visible and marked as carried."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, dialogs = _open(new_context, server)
    _carry_radius_through_a_filter(page)
    page.wait_for_function("() => document.getElementById('place-radius').value === '12'")
    if dialogs:
        raise AssertionError("the page's own navigations raised %r" % dialogs)
    _wait_for_bar(page)
    if page.get_attribute("[data-dirty-bar]", "data-dirty-carried") is None:
        raise AssertionError("the bar is not marked as carrying unsaved values")
    if not _guard_armed(page):
        raise AssertionError("the leave guard is not armed on the carried state")
    if not page.is_checked("#place-mode-runway"):
        raise AssertionError("picking an airport did not select the runway mode")


def test_cancel_in_carried_state_returns_to_stored_value(new_context, make_app_server):
    """Cancel on the carried state goes to the plain page and shows the stored radius."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, _dialogs = _open(new_context, server)
    _carry_radius_through_a_filter(page)
    _wait_for_bar(page)
    with page.expect_navigation():
        page.click("[data-dirty-cancel]")
    # The administrator's own frame is addressed by its id, so the plain page
    # is that frame's /detection.
    plain = page.url.split("#")[0].split("?")[0]
    if not re.fullmatch(
            re.escape(server.base_url()) + r"/devices/d_[0-9a-f]{8}/detection", plain) \
            or "?" in page.url.split("#")[0]:
        raise AssertionError("Cancel landed on %s" % page.url)
    page.wait_for_function("() => document.getElementById('place-radius').value === '7'")
    if not page.is_checked("#place-mode-area"):
        raise AssertionError("Cancel did not restore the stored area mode")


LEAVE_DIALOG = "dialog[data-leave-dialog]"


def _click_another_page(page):
    page.locator("a[href$='/flights']:visible").first.click()


def _wait_leave_dialog(page):
    page.wait_for_function(
        "() => { const d = document.querySelector('%s'); return !!d && d.open; }" % LEAVE_DIALOG,
        timeout=5000)


def test_real_leave_asks_in_the_page_dialog(new_context, make_app_server):
    """An unsaved edit followed by a click on another page's link asks in the page's own
    unsaved-changes dialog, not the browser's prompt, and Discard then leaves."""
    server = make_app_server(seed=_seed(SAVED_RUNWAY), fake_providers=True)
    page, dialogs = _open(new_context, server)
    here = page.url
    page.click(MODE_AREA_LABEL)
    _wait_for_bar(page)
    _click_another_page(page)
    _wait_leave_dialog(page)
    if page.url != here:
        raise AssertionError("the page left before the question was answered: %s" % page.url)
    if dialogs:
        raise AssertionError("the browser's own prompt appeared as well: %r" % dialogs)
    page.click(LEAVE_DIALOG + " [data-leave-dialog-secondary]")
    page.wait_for_url("**/flights", timeout=15000)


def test_back_forward_cache_rearms_guard(new_context, make_app_server):
    """After a page-local navigation and a trip back, an unsaved edit is guarded again."""
    server = make_app_server(seed=_seed(SAVED_POSITION), fake_providers=True)
    page, dialogs = _open(new_context, server)
    page.click(MODE_RUNWAY_LABEL)
    _follow_airport_link(page)
    page.go_back()
    page.wait_for_load_state()
    page.click(MODE_RUNWAY_LABEL)
    page.click(MODE_AREA_LABEL)
    page.fill("#place-radius", "11")
    _wait_for_bar(page)
    if not _guard_armed(page):
        raise AssertionError("the guard stayed disarmed after returning to the page")
    del dialogs[:]
    _click_another_page(page)
    _wait_leave_dialog(page)
    if dialogs:
        raise AssertionError("a later real leave raised the browser's prompt: %r" % dialogs)


# A user's Display page no longer holds the place; the Location and detection page does.

USER_VIEWPORTS = (VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP)
NOTE_LINK = "dialog#dlg-quiet-hours .quiet-timezone-note a"
# Words an ordinary user's page must never carry.
ADMIN_WORDS = re.compile(r"\b(Admin\w*|Console|Fleet|Releases?|Device)\b", re.IGNORECASE)


class DisplayRig(UserRig):
    """The shared fleet with two locations owned by the frame's owner."""

    def __init__(self, server):
        super().__init__(server)
        self.display = "%sdisplay" % self.path
        self.detection = "%sdetection" % self.path
        conn = fleet_db.connect(self.state_dir)
        try:
            self.home_id = fleet_db.add_location(
                conn, "Home", 48.8566, 2.3522, "Europe/Paris",
                owner_user_id=self.seed.owner_id)
            self.office_id = fleet_db.add_location(
                conn, "Office", 48.7262, 2.3652, "Europe/Paris",
                owner_user_id=self.seed.owner_id)
        finally:
            conn.close()

    def stored_location(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.get_device(conn, self.seed.owned_id)["location_id"]
        finally:
            conn.close()

    def stored_place(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.frame_position(conn, self.seed.owned_id)
        finally:
            conn.close()


@pytest.fixture
def drig(app_server_in_process):
    return DisplayRig(app_server_in_process)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", USER_VIEWPORTS)
def test_a_user_display_has_no_place_controls_and_no_quiet_hours_note(
        new_context, drig, lang, theme, viewport):
    context, page = _open_as(
        new_context, drig, "owner", path=drig.display, lang=lang, theme=theme,
        viewport=viewport)
    try:
        failure = _assert_no_page_overflow(page, "user display", viewport["width"])
        if failure:
            raise AssertionError(failure)
        for selector in (
                "section.detection-card", "#location-picker", "select[name=location_id]",
                "select[name=timezone]"):
            if page.locator(selector).count():
                raise AssertionError("Display still renders %s" % selector)
        if page.locator(NOTE_LINK).count():
            raise AssertionError("Display still renders the quiet-hours note")
        if page.locator("input[name=quiet_hours_start]").count():
            raise AssertionError("Display still renders a quiet-hours control")
        visible = page.locator("main").inner_text()
        if lang == "en" and ADMIN_WORDS.search(visible):
            raise AssertionError("user page carries %r" % ADMIN_WORDS.search(visible).group(0))
    finally:
        context.close()


def test_the_note_link_opens_the_location_page(new_context, drig):
    context, page = _open_as(new_context, drig, "owner", path=drig.path)
    Hosts(context)
    try:
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        page.locator("a.home-switch__window").click()
        page.wait_for_function(
            "() => document.querySelector('dialog#dlg-quiet-hours').open", timeout=10000)
        with page.expect_navigation():
            page.locator(NOTE_LINK).click()
        if not page.url.endswith("/detection#details"):
            raise AssertionError("landed on %s" % page.url)
    finally:
        context.close()


def test_a_user_changes_the_place_on_the_location_page_with_scripts_blocked(new_context, drig):
    context, page = _open_as(
        new_context, drig, "owner", path=drig.detection, java_script_enabled=False)
    try:
        page.click(MODE_AREA_LABEL)
        page.fill("#place-lat", "43.2965")
        page.fill("#place-lon", "5.3698")
        page.fill("#place-label", "Marseille")
        page.fill("#place-radius", "14")
        _submit(page, SAVE)
        place = drig.stored_place()
        if place is None or (place["name"], place["latitude"], place["longitude"]) != (
                "Marseille", 43.2965, 5.3698):
            raise AssertionError("the position row is %r" % (place,))
    finally:
        context.close()
