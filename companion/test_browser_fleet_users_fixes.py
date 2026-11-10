"""Real-browser checks of the Fleet and Users fixes: the Users Active switch acts in place
(no page load, scroll and focus kept), the rename page's Save bar appears only on a change
and saves, a typed wake interval is not snapped by the slider, and the System view is one
column with counts at the right edge. Every read waits for a settled page first."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login)
from server import device_config, fleet_db

pytestmark = pytest.mark.browser

_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _page(new_context, server, path, viewport, lang="en", who="admin", theme=None):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport, **({"color_scheme": theme} if theme else {}))
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    if who == "admin":
        _login(page, server.base_url())
    else:
        name, value = fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL).split("=", 1)
        context.add_cookies([{
            "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
            "sameSite": "Strict"}])
    page.goto(server.base_url() + path.replace("{owned}", seed.owned_id).replace(
        "{live}", seed.live_id))
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page, seed


def _disabled(server, user_id):
    conn = fleet_db.connect(server.state_dir)
    try:
        return conn.execute(
            "SELECT disabled FROM users WHERE id = ?", (user_id,)).fetchone()[0]
    finally:
        conn.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_active_switch_acts_in_place_without_reloading_the_page(
        new_context, app_server_in_process, viewport, lang):
    server = app_server_in_process
    context, page, seed = _page(new_context, server, "/users", viewport, lang)
    try:
        row = "#user-%d" % seed.user_id
        switch = page.locator(row + " button.switch")
        switch.scroll_into_view_if_needed()
        page.wait_for_function(_OWNS_CENTRE, arg=row + " button.switch", timeout=10000)
        page.evaluate("() => { window.__same_document = true; }")
        switch.click()
        page.wait_for_function(
            "sel => document.querySelector(sel).getAttribute('aria-checked') === 'false'"
            " && !document.querySelector(sel).closest('tr').hasAttribute('data-pending')",
            arg=row + " button.switch", timeout=10000)
        # Same document (no navigation), the status mark follows, and the server agrees.
        assert page.evaluate("() => window.__same_document === true")
        assert page.locator(row + " .users-pill--disabled").is_visible()
        assert page.locator(row + " .users-status .users-pill:visible").count() == 1
        assert _disabled(server, seed.user_id) == 1
        switch.click()
        page.wait_for_function(
            "sel => document.querySelector(sel).getAttribute('aria-checked') === 'true'"
            " && !document.querySelector(sel).closest('tr').hasAttribute('data-pending')",
            arg=row + " button.switch", timeout=10000)
        assert page.evaluate("() => window.__same_document === true")
        assert page.locator(row + " .users-pill--disabled").is_hidden()
        assert _disabled(server, seed.user_id) == 0
        assert not _assert_no_page_overflow(page, "users-switch", viewport["width"])
    finally:
        context.close()


def test_the_signed_in_administrators_row_offers_no_delete(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _page(new_context, server, "/users", VIEWPORT_DESKTOP)
    try:
        assert page.locator("#user-%d summary.row-menu__toggle" % seed.admin_id).count() == 0
        other = page.locator("#user-%d" % seed.user_id)
        other.locator("summary.row-menu__toggle").click()
        assert other.locator(".row-menu__item", has_text="Delete user").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_rename_page_shows_the_cancel_and_save_bar_and_saves_the_name(
        new_context, app_server_in_process, viewport, lang):
    server = app_server_in_process
    context, page, seed = _page(
        new_context, server, "/devices/{owned}/frame/name", viewport, lang, who="owner")
    try:
        field = page.locator("#frame-name")
        page.wait_for_function(_OWNS_CENTRE, arg="#frame-name", timeout=10000)
        assert field.input_value() == "Kitchen"
        bar = page.locator(".dirty-bar")
        page.wait_for_function(
            "() => !document.querySelector('.dirty-bar').hidden", timeout=10000)
        field.fill("Living room")
        assert not _assert_no_page_overflow(page, "rename", viewport["width"])
        save = bar.locator("button.dirty-bar__save")
        assert save.bounding_box()["height"] >= 44 - 0.5
        save.click()
        page.wait_for_url("**/account**")
        conn = fleet_db.connect(server.state_dir)
        try:
            assert fleet_db.get_device(conn, seed.owned_id)["name"] == "Living room"
        finally:
            conn.close()
        page.wait_for_function(_SETTLED, timeout=15000)
        assert "Living room" in page.locator("main").inner_text()
    finally:
        context.close()


def test_cancel_on_the_rename_page_leaves_the_name_unchanged_and_goes_back(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _page(
        new_context, server, "/devices/{owned}/frame/name", VIEWPORT_DESKTOP, who="owner")
    try:
        page.locator("#frame-name").fill("Changed")
        page.locator(".dirty-bar a.dirty-bar__cancel").click()
        page.wait_for_url("**/account**")
        conn = fleet_db.connect(server.state_dir)
        try:
            assert fleet_db.get_device(conn, seed.owned_id)["name"] == "Kitchen"
        finally:
            conn.close()
    finally:
        context.close()


def test_an_invalid_name_shows_the_field_error_in_place(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _page(
        new_context, server, "/devices/{owned}/frame/name", VIEWPORT_DESKTOP, who="owner")
    try:
        page.locator("#frame-name").fill("x" * 41)
        page.locator("#frame-name").evaluate("e => e.removeAttribute('maxlength')")
        page.locator("#frame-name").fill("x" * 41)
        page.locator(".dirty-bar button.dirty-bar__save").click()
        page.wait_for_selector("#frame-name-error", timeout=10000)
        assert "1 to 40" in page.locator("#frame-name-error").inner_text()
        assert page.locator("#frame-name").get_attribute("aria-invalid") == "true"
    finally:
        context.close()


def test_a_typed_wake_interval_keeps_the_slider_where_it_was_typed(
        new_context, app_server_in_process):
    server = app_server_in_process
    device_config.save_device_config(server.state_dir, wake_interval_s=600)
    context, page, _seed = _page(
        new_context, server, "/fleet?frame={live}&tab=settings", VIEWPORT_DESKTOP)
    try:
        page.locator("#wake-interval-s").scroll_into_view_if_needed()
        page.wait_for_function(_OWNS_CENTRE, arg="#wake-interval-s", timeout=10000)
        page.locator("#wake-interval-s").fill("700")
        page.wait_for_function(
            "() => document.querySelector('.wake-slider__input').value === '700'", timeout=10000)
        assert page.locator("#wake-interval-s").input_value() == "700"
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_system_view_is_one_column_with_no_overflow(
        new_context, app_server_in_process, viewport):
    context, page, _seed = _page(new_context, app_server_in_process, "/fleet?view=system", viewport)
    try:
        assert not _assert_no_page_overflow(page, "system", viewport["width"])
        lefts = page.evaluate(
            "() => [...document.querySelectorAll('.system-topic')]"
            ".map(e => Math.round(e.getBoundingClientRect().left))")
        assert len(lefts) >= 2 and len(set(lefts)) == 1, lefts
        widest = page.evaluate(
            "() => Math.max(...[...document.querySelectorAll('.system-topic')]"
            ".map(e => e.getBoundingClientRect().width))")
        assert widest <= 800.5
    finally:
        context.close()
