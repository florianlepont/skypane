"""Real-browser checks of the admin console (Fleet, Users, Locations, Audit
log) and of the reduced view a plain user gets: layout at the smallest phone
width, 44px touch targets, operation with scripts blocked, both themes, French,
the absence of every administrator entry for a user, and a pairing round trip
whose code comes from the real byos issue path.

Every pairing code here is generated at test time and never written down."""
import os
import re
import sys
import time

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _in_both_themes, _login,
    _set_ui_theme)
from companion_app_server import served_asset
from server import fleet_db, hardware, pairing_code

pytestmark = pytest.mark.browser

_STUB_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stub-server")
if _STUB_SERVER_DIR not in sys.path:
    sys.path.insert(0, _STUB_SERVER_DIR)

import byos_server  # noqa: E402

MIN_TAP_PX = 44
CONSOLE_PATHS = ("/fleet", "/users", "/locations", "/audit")
ADMIN_ONLY_PATHS = ("/fleet", "/users", "/audit", "/update", "/device")
ADMIN_ONLY_CONTROLS = (
    "wake_interval_s", "led_enabled", "tracked_runway", "Poll now")

# One probe over every element: the colours and the motion declarations it
# resolves to, as strings.
_STYLE_VALUES = (
    "() => { const colours = new Set(), motion = new Set();"
    " for (const el of document.querySelectorAll('body *')) {"
    "  const s = getComputedStyle(el);"
    "  for (const p of ['color', 'backgroundColor', 'borderTopColor',"
    "                   'borderBottomColor', 'outlineColor'])"
    "   colours.add(s[p]);"
    "  motion.add([s.transitionProperty, s.transitionDuration,"
    "              s.animationName].join('|'));"
    " }"
    " return {colours: [...colours], motion: [...motion]}; }")
# The shared button classes the console reuses, added to a reference page so
# their resolved paint counts as already in use.
_ADD_EXISTING_BUTTONS = (
    "() => { for (const cls of ['calendar-disconnect-btn']) {"
    " const b = document.createElement('button'); b.type = 'submit';"
    " b.className = cls; b.textContent = 'x';"
    " document.querySelector('main').appendChild(b); } }")
REFERENCE_PATHS = ("/", "/display", "/health", "/flights", "/airlines", "/update", "/account")
def _no_sideways_scroll(page):
    return page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def _height(page, selector):
    return page.locator(selector).first.bounding_box()["height"]


def _admin_page(new_context, server, path, viewport=None, seed=True, **context_args):
    if seed:
        fx.seed_fleet(server.state_dir)
    extra = {} if viewport is None else {"viewport": viewport}
    context = new_context(**extra, **context_args)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    return context, page


def _user_context(new_context, server, viewport=None):
    seed = fx.seed_fleet(server.state_dir)
    cookie = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    name, value = cookie.split("=", 1)
    extra = {} if viewport is None else {"viewport": viewport}
    context = new_context(**extra)
    context.add_cookies([{
        "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
        "sameSite": "Strict"}])
    return context, seed


def _flash(page):
    return page.locator('[role="status"], [role="alert"]').first


# --- Test 1: layout at 360 px --------------------------------------------

@pytest.mark.parametrize("path", CONSOLE_PATHS)
def test_console_pages_fit_a_phone_and_collapse_tables(
        new_context, app_server_in_process, path):
    context, page = _admin_page(
        new_context, app_server_in_process, path, VIEWPORT_MIN_SUPPORTED)
    try:
        assert _no_sideways_scroll(page)
        assert not page.locator("main table:visible").count()
        page.set_viewport_size(VIEWPORT_DESKTOP)
        assert _no_sideways_scroll(page)
    finally:
        context.close()


# --- Test 2: touch targets -----------------------------------------------

def test_forms_and_confirm_controls_meet_the_touch_target(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page = _admin_page(new_context, server, "/fleet", VIEWPORT_MIN_SUPPORTED)
    try:
        for selector in (
                "#pair-code", "#pair-owner", 'form[action="/fleet/pair"] button',
                "#register-mac", 'form[action="/fleet/register"] button',
                "ul.data-cards details.fleet-confirm > summary"):
            assert _height(page, selector) >= MIN_TAP_PX, selector
        page.locator("ul.data-cards details.fleet-confirm > summary").first.click()
        assert _height(
            page, "ul.data-cards details.fleet-confirm[open] button") >= MIN_TAP_PX
        page.goto(server.base_url() + "/users")
        for selector in (
                "#invite-email", "#invite-role", 'form[action="/users/invite"] button',
                "ul.data-cards details.fleet-confirm > summary"):
            assert _height(page, selector) >= MIN_TAP_PX, selector
        page.locator("ul.data-cards details.fleet-confirm > summary").first.click()
        assert _height(
            page, "ul.data-cards details.fleet-confirm[open] button") >= MIN_TAP_PX
        page.goto(server.base_url() + "/locations")
        for selector in (
                "#new-name", "#new-lat", "#new-lon", "#new-tz",
                'form[action="/locations/add"] button'):
            assert _height(page, selector) >= MIN_TAP_PX, selector
    finally:
        context.close()


def test_audit_pager_links_meet_the_touch_target(new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            for index in range(60):
                fleet_db.audit_append(
                    conn, fx.ACTOR, "pairing.claim", "device", "d_00000001", "ok",
                    None, now=2_000_000_000 + index)
    finally:
        conn.close()
    context, page = _admin_page(
        new_context, server, "/audit", VIEWPORT_MIN_SUPPORTED, seed=False)
    try:
        assert _height(page, ".audit-pager .text-link") >= MIN_TAP_PX
    finally:
        context.close()


# --- Test 3: scripts blocked ---------------------------------------------

def test_console_works_with_scripts_blocked(new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id,
                  code=pairing_code.generate_code())
    context = new_context(java_script_enabled=False, viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())

        page.goto(server.base_url() + "/fleet")
        summary = page.locator("details.fleet-confirm > summary:visible").first
        summary.click()
        assert page.locator("details.fleet-confirm[open]:visible").count() == 1
        summary.click()
        assert page.locator("details.fleet-confirm[open]").count() == 0

        page.fill("#register-mac", fx.MAC_NEW)
        page.fill("#register-hash", fx.SECRET_HASH)
        page.select_option("#register-hardware", hardware.available_types()[0])
        page.click('form[action="/fleet/register"] button')
        page.wait_for_url("**/fleet")
        assert _flash(page).is_visible()

        page.goto(server.base_url() + "/users")
        page.fill("#invite-email", "invited@example.test")
        page.click('form[action="/users/invite"] button')
        page.wait_for_url("**/users")
        assert _flash(page).is_visible()
        assert "invited@example.test" in page.content()

        page.goto(server.base_url() + "/locations")
        page.fill("#new-name", "Test place")
        page.fill("#new-lat", "48.7253")
        page.fill("#new-lon", "2.3592")
        page.click('form[action="/locations/add"] button')
        page.wait_for_url("**/locations")
        assert _flash(page).is_visible()
        assert "Test place" in page.content()
    finally:
        context.close()


def test_pair_form_posts_and_redirects_with_scripts_blocked(
        new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    code = pairing_code.generate_code()
    fx.issue_code(server.state_dir, seed.pending_id, code=code)
    context = new_context(java_script_enabled=False, viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet")
        page.fill("#pair-code", code)
        page.select_option("#pair-owner", str(seed.user_id))
        page.click('form[action="/fleet/pair"] button')
        page.wait_for_url("**/fleet")
        assert "Frame paired" in _flash(page).inner_text()
    finally:
        context.close()


# --- Test 4: themes and French -------------------------------------------

@pytest.mark.parametrize("path", CONSOLE_PATHS)
def test_console_renders_in_both_themes(new_context, app_server_in_process, path):
    context, page = _admin_page(
        new_context, app_server_in_process, path, VIEWPORT_MIN_SUPPORTED)
    try:
        for paint in _in_both_themes(page):
            assert paint["canvas"] != paint["text"]
            assert _no_sideways_scroll(page)
            assert page.locator("main").is_visible()
    finally:
        context.close()


def test_console_renders_in_french(new_context, app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr",
            "url": server.base_url()}])
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/fleet")
        nav = page.locator("nav").first.inner_text()
        for label in ("Cadres", "Utilisateurs", "Lieux", "Journal d’audit"):
            assert label in nav, label
        assert _no_sideways_scroll(page)
    finally:
        context.close()


# --- Test 5: the user's view ---------------------------------------------

def test_user_sees_no_administrator_entry(new_context, app_server_in_process):
    server = app_server_in_process
    context, seed = _user_context(new_context, server, VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        home = "%s/devices/%s/" % (server.base_url(), seed.owned_id)
        for suffix in ("", "display", "health", "flights"):
            page.goto(home + suffix)
            served = page.content()
            live = page.evaluate("document.documentElement.outerHTML")
            hrefs = page.evaluate(
                "[...document.querySelectorAll('[href],[action]')]"
                ".map(e => e.getAttribute('href') || e.getAttribute('action'))")
            for path in ADMIN_ONLY_PATHS:
                assert not any(
                    href == path or href.startswith(path + "/") or
                    href.startswith(path + "?") for href in hrefs), (suffix, path)
            for marker in ADMIN_ONLY_CONTROLS:
                assert marker not in served and marker not in live, (suffix, marker)
        page.goto(home)
        tabs = [t.strip() for t in page.locator(
            ".tab-bar > a, .tab-bar > .tab-bar__link").all_inner_texts() if t.strip()]
        assert tabs == ["Home", "Flights", "Display", "Health", "Account"], tabs
    finally:
        context.close()


@pytest.mark.parametrize("path", ADMIN_ONLY_PATHS + ("/locations/1/edit",))
def test_admin_urls_are_the_unknown_path_page_for_a_user(
        new_context, app_server_in_process, path):
    server = app_server_in_process
    context, seed = _user_context(new_context, server)
    try:
        page = context.new_page()
        unknown = page.goto(server.base_url() + "/no-such-page-here")
        unknown_body = page.locator("main").inner_text()
        response = page.goto(server.base_url() + path)
        assert unknown.status == 404
        assert response.status == 404
        assert page.locator("main").inner_text() == unknown_body
    finally:
        context.close()


# --- Test 6: no dialog, no confirm(), no new colour or motion ------------

def test_new_pages_ship_no_dialog_or_confirm(app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    cookie = fx.admin_cookie(server.state_dir)
    for path in CONSOLE_PATHS:
        status, _headers, body = fx.get(server, cookie, path)
        assert status == 200
        assert "<dialog" not in body and "confirm(" not in body, path
        for src in re.findall(r'<script[^>]*\ssrc="([^"]+)"', body):
            script = served_asset(server, src)
            assert "<dialog" not in script and "confirm(" not in script, src


def _resolved_values(page, server, paths, probe=False):
    colours, motion = set(), set()
    for path in paths:
        page.goto(server.base_url() + path)
        page.locator("main").wait_for(state="visible")
        if probe:
            page.evaluate(_ADD_EXISTING_BUTTONS)
        seen = page.evaluate(_STYLE_VALUES)
        colours.update(seen["colours"])
        motion.update(seen["motion"])
    return colours, motion


def test_console_resolves_only_colours_and_motion_the_app_already_uses(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page = _admin_page(new_context, server, "/", VIEWPORT_DESKTOP)
    try:
        for theme in ("light", "dark"):
            _set_ui_theme(page, theme)
            known_colours, known_motion = _resolved_values(
                page, server, REFERENCE_PATHS, probe=True)
            colours, motion = _resolved_values(page, server, CONSOLE_PATHS)
            assert colours <= known_colours, (theme, colours - known_colours)
            assert motion <= known_motion, (theme, motion - known_motion)
    finally:
        context.close()


# --- Test 7: pairing round trip ------------------------------------------

def test_pairing_flow_in_the_browser(new_context, app_server_in_process, monkeypatch):
    server = app_server_in_process
    context, page = _admin_page(new_context, server, "/fleet", VIEWPORT_DESKTOP)
    try:
        page.fill("#register-mac", fx.MAC_NEW)
        page.fill("#register-hash", fx.SECRET_HASH)
        page.select_option("#register-hardware", hardware.available_types()[0])
        page.click('form[action="/fleet/register"] button')
        page.wait_for_url("**/fleet")
        conn = fleet_db.connect(server.state_dir)
        try:
            pending_id = fleet_db.get_pending_by_mac(conn, fx.MAC_NEW)["id"]
        finally:
            conn.close()
        code = _issue_through_byos(server.state_dir, pending_id, monkeypatch)

        wrong = pairing_code.generate_code()
        while wrong == code:
            wrong = pairing_code.generate_code()
        page.fill("#pair-code", wrong)
        page.click('form[action="/fleet/pair"] button')
        first_text = _refusal_text(page)
        assert first_text

        page.goto(server.base_url() + "/fleet")
        other = pairing_code.generate_code()
        while other in (code, wrong):
            other = pairing_code.generate_code()
        page.fill("#pair-code", other)
        page.click('form[action="/fleet/pair"] button')
        assert _strip_codes(first_text, wrong) == _strip_codes(_refusal_text(page), other)

        page.goto(server.base_url() + "/fleet")
        page.fill("#pair-code", code)
        page.select_option("#pair-owner", str(_owner_id(server.state_dir)))
        page.click('form[action="/fleet/pair"] button')
        page.wait_for_url("**/fleet")
        assert "Frame paired" in _flash(page).inner_text()
        conn = fleet_db.connect(server.state_dir)
        try:
            assert fleet_db.get_device_by_mac(conn, fx.MAC_NEW) is not None
        finally:
            conn.close()
    finally:
        context.close()


def _issue_through_byos(state_dir, pending_id, monkeypatch):
    """Let the real byos pending path issue a code, with the code chosen
    here so the test can type it."""
    code = pairing_code.generate_code()
    conn = fleet_db.connect(state_dir)
    try:
        row = fleet_db.get_pending(conn, pending_id)
    finally:
        conn.close()
    profile = hardware.get_profile(row["hardware_type"], os.environ)
    with monkeypatch.context() as patch:
        patch.setattr(byos_server.pairing_code, "generate_code", lambda: code)
        assert byos_server._pending_panel(
            state_dir, row, profile, int(time.time()), 3900, "1.0.0") is not None
    return code


def _owner_id(state_dir):
    conn = fleet_db.connect(state_dir)
    try:
        return fleet_db.get_user_by_email(conn, fx.OWNER_EMAIL)["id"]
    finally:
        conn.close()


def _refusal_text(page):
    return " ".join(page.locator(
        '[role="alert"], .field-error').all_inner_texts())


def _strip_codes(text, code):
    return " ".join(text.replace(code, "").split())
