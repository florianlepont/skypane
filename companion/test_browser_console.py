# SPDX-License-Identifier: AGPL-3.0-only
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
from companion import auth, legacy_pages
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _in_both_themes, _login,
    _set_ui_theme)
from companion_app_server import served_asset
from server import fleet_db, fleet_ops, hardware, pairing_code

pytestmark = pytest.mark.browser

_STUB_SERVER_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "stub-server")
if _STUB_SERVER_DIR not in sys.path:
    sys.path.insert(0, _STUB_SERVER_DIR)

import byos_server  # noqa: E402

MIN_TAP_PX = 44
CONSOLE_PATHS = ("/fleet", "/users", "/audit")
ADMIN_ONLY_PATHS = (
    "/fleet", "/users", "/audit", "/update", "/airlines/manage")
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
# The shared button, filter-chip and status-pill classes the console reuses, added to a
# reference page so their resolved paint counts as already in use.
_ADD_EXISTING_BUTTONS = (
    "() => { for (const cls of ['btn btn--secondary']) {"
    " const b = document.createElement('button'); b.type = 'submit';"
    " b.className = cls; b.textContent = 'x';"
    " document.querySelector('main').appendChild(b); }"
    " const chip = document.createElement('a'); chip.className = 'filter-chip';"
    " chip.href = '/'; chip.innerHTML ="
    "  '<span class=\"filter-chip__box\"><span class=\"filter-chip__text\">x</span></span>';"
    " document.querySelector('main').appendChild(chip);"
    " for (const tone of ['active', 'invited', 'disabled']) {"
    "  const pill = document.createElement('span');"
    "  pill.className = 'banner__pill users-pill users-pill--' + tone; pill.textContent = 'x';"
    "  document.querySelector('main').appendChild(pill); } }")
REFERENCE_PATHS = ("/", "/display", "/fleet?frame=live&view=battery", "/flights", "/airlines", "/airlines/manage", "/update", "/account")
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


def click_add(page):
    """Choose Add a frame in the Fleet list (it leads to the Add a frame page)."""
    page.locator(".fleet-add-button").click()
    page.wait_for_url("**/pair-frame")


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
        # A table element may stay in the DOM as cards (display other than
        # table); none may lay out as a wide table on a phone.
        assert not page.locator("main table:visible").evaluate_all(
            "els => els.filter(e => getComputedStyle(e).display === 'table').length")
        page.set_viewport_size(VIEWPORT_DESKTOP)
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def _seed_long_co_manager_row(server):
    seed = fx.seed_fleet(server.state_dir)
    long_email = "a-very-long-co-manager-address-" + "x" * 40 + "@example.test"
    conn = fleet_db.connect(server.state_dir)
    try:
        with fleet_db.transaction(conn):
            user_id = fleet_db.add_user(conn, long_email, "user")
            fleet_db.audit_append(
                conn, fx.ACTOR, "device.co_manager_remove", "device", seed.owned_id,
                "ok", {"co_manager_user_id": user_id, "via": "reassign"})
    finally:
        conn.close()
    return long_email


@pytest.mark.parametrize("viewport", [
    {"width": 1000, "height": 900}, VIEWPORT_MIN_SUPPORTED])
def test_audit_co_manager_row_shows_person_and_reason(
        new_context, app_server_in_process, viewport):
    long_email = _seed_long_co_manager_row(app_server_in_process)
    context, page = _admin_page(
        new_context, app_server_in_process, "/audit", viewport, seed=False)
    try:
        page.locator("ul.audit-cards summary").first.click()
        page.locator("ul.audit-cards details[open]").wait_for(state="visible")
        text = page.locator("ul.audit-cards").inner_text()
        assert long_email in text
        assert "Frame reassigned to a new owner" in text
        assert _no_sideways_scroll(page)
    finally:
        context.close()


# --- Test 2: touch targets -----------------------------------------------

def test_forms_and_confirm_controls_meet_the_touch_target(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page = _admin_page(new_context, server, "/fleet", VIEWPORT_MIN_SUPPORTED)
    try:
        assert _height(page, ".fleet-add-button") >= MIN_TAP_PX
        assert _height(page, "li.fleet-frame-row > a") >= MIN_TAP_PX
        click_add(page)
        for selector in (
                "#pair-code", "#pair-owner", 'form.pair-form button[type=submit]'):
            assert _height(page, selector) >= MIN_TAP_PX, selector
        page.goto(server.base_url() + "/users")
        assert _height(page, "a.page-header__action") >= MIN_TAP_PX
        # A phone card has no select: the role changes from the person's menu.
        page.locator("tr.users-row .row-menu__toggle").first.click()
        assert _height(page, "tr.users-row .users-menu__role .row-menu__item") >= MIN_TAP_PX
        page.keyboard.press("Escape")
        page.locator("a.page-header__action").click()
        for selector in (
                "#invite-email", "#invite-role", '#dlg-invite-user button[type=submit]'):
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
        page.locator("li.fleet-frame-row > a[href*='frame=']").first.click()
        page.wait_for_url("**/fleet?frame=*")
        assert page.locator(".fleet-head__title").is_visible()

        page.goto(server.base_url() + "/users")
        page.click("a.page-header__action")
        page.fill("#invite-email", "invited@example.test")
        page.click('#dlg-invite-user button[type=submit]')
        page.locator("#dlg-invitation-failed").wait_for(state="visible")
        assert "invited@example.test" in page.content()
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
        click_add(page)
        page.fill("#pair-code", code)
        page.select_option("#pair-owner", str(seed.user_id))
        page.click('form.pair-form button[type=submit]')
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
        nav = page.locator("nav.sidebar-nav").inner_text()
        assert page.locator("nav.space-switch:visible").inner_text().split() == [
            "Mes", "cadres", "Console"]
        for label in ("Flotte", "Utilisateurs", "Activité"):
            assert label in nav, label
        assert "Lieux" not in nav
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
        for suffix in ("", "display", "flights"):
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
        assert tabs == ["Home", "Flights", "Airlines", "Style", "Location", "Account"], tabs
    finally:
        context.close()


@pytest.mark.parametrize("path", tuple(
    path for path in ADMIN_ONLY_PATHS if path not in legacy_pages.RETIRED_ADMIN_PAGES
) + ("/locations", "/locations/1/edit"))
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

def test_console_pages_ship_no_confirm_and_dialogs_only_where_planned(
        app_server_in_process):
    server = app_server_in_process
    fx.seed_fleet(server.state_dir)
    cookie = fx.admin_cookie(server.state_dir)
    for path in CONSOLE_PATHS:
        status, _headers, body = fx.get(server, cookie, path)
        assert status == 200
        assert "confirm(" not in body, path
        if path not in ("/fleet", "/users"):
            assert "<dialog" not in body, path
        for src in re.findall(r'<script[^>]*\ssrc="([^"]+)"', body):
            script = served_asset(server, src)
            assert "<dialog" not in script and "confirm(" not in script, src


# The opened Audit event is a tinted panel in the approved Audit mockup: the page ink at 5 %
# for its ground and at 80 % for its terms. They are counted as already in use, resolved in the
# theme being checked, because a reference page cannot show an opened event.
_ADD_AUDIT_PANEL_PAINT = (
    "() => { const panel = document.createElement('div');"
    " panel.style.background = 'color-mix(in srgb, var(--color-text) 5%, transparent)';"
    " panel.style.color = 'color-mix(in srgb, var(--color-text) 80%, transparent)';"
    " panel.textContent = 'x'; document.querySelector('main').appendChild(panel); }")


def _resolved_values(page, server, paths, probe=False):
    colours, motion = set(), set()
    for path in paths:
        page.goto(server.base_url() + path)
        page.locator("main").wait_for(state="visible")
        if probe:
            page.evaluate(_ADD_EXISTING_BUTTONS)
            page.evaluate(_ADD_AUDIT_PANEL_PAINT)
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
        conn = fleet_db.connect(server.state_dir)
        try:
            pending_id = fleet_ops.register_frame(
                conn, fx.MAC_NEW, fx.SECRET_HASH, hardware.available_types()[0],
                fx.ACTOR)
        finally:
            conn.close()
        code = _issue_through_byos(server.state_dir, pending_id, monkeypatch)

        wrong = pairing_code.generate_code()
        while wrong == code:
            wrong = pairing_code.generate_code()
        page.goto(server.base_url() + "/fleet")
        click_add(page)
        page.fill("#pair-code", wrong)
        page.click('form.pair-form button[type=submit]')
        first_text = _refusal_text(page)
        assert first_text

        page.goto(server.base_url() + "/fleet")
        other = pairing_code.generate_code()
        while other in (code, wrong):
            other = pairing_code.generate_code()
        click_add(page)
        page.fill("#pair-code", other)
        page.click('form.pair-form button[type=submit]')
        assert _strip_codes(first_text, wrong) == _strip_codes(_refusal_text(page), other)

        page.goto(server.base_url() + "/fleet")
        click_add(page)
        page.fill("#pair-code", code)
        page.select_option("#pair-owner", str(_owner_id(server.state_dir)))
        page.click('form.pair-form button[type=submit]')
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
    # The refusal arrives with the page the POST navigates to: wait for it
    # (and for that document to finish loading) before reading.
    page.locator('[role="alert"], .field-error').first.wait_for(state="attached")
    page.wait_for_function("() => document.readyState === 'complete'")
    return " ".join(page.locator(
        '[role="alert"], .field-error').all_inner_texts())


def _strip_codes(text, code):
    return " ".join(text.replace(code, "").split())
