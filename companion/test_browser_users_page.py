"""Real-browser flows of the Users table: invite in a few actions, a duplicate
email refused with the dialog reopened, a role that saves as soon as it
changes, the Active switch, unlink from the "..." menu, the guard sentences,
keyboard use of the menu, the no-script controls, and table and card geometry
at 360 and 1280px in both languages and both themes."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme)
from server import fleet_db

pytestmark = pytest.mark.browser

INVITE = "#dlg-invite-user"
LONG_EMAIL = "a" * 46 + "@example.test"

_ACTIVE_IN = (
    "d => d.contains(document.activeElement)"
    " || document.activeElement === document.body")
_FIT = "d => ({sw: d.scrollWidth, cw: d.clientWidth})"
_OWNS_CENTRE = (
    "s => { const e = document.querySelector(s); if (!e) return false;"
    " const r = e.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return hit === e || e.contains(hit); }")


def _settled(page, selector="a.page-header__action"):
    """Wait out the page-change transition: the document is complete and a
    known control owns its own centre."""
    page.wait_for_function("() => document.readyState === 'complete'")
    page.wait_for_function(_OWNS_CENTRE, arg=selector, timeout=10000)


def _body_text(page):
    return page.locator("body").inner_text()


def _row(page, email):
    return page.locator("tr.users-row", has_text=email)


def _wait_db(page, server, user_id, index, value):
    for _ in range(100):
        if _user(server, user_id)[index] == value:
            return
        page.wait_for_timeout(50)
    raise AssertionError("user %d column %d never became %r" % (user_id, index, value))


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", scheme="light"):
    seed = fx.seed_users(server.state_dir)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/users")
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


def _sql(server, sql, args=()):
    conn = fleet_db.connect(server.state_dir)
    try:
        rows = [tuple(row) for row in conn.execute(sql, args)]
        conn.commit()
        return rows
    finally:
        conn.close()


def _user(server, user_id):
    return _sql(
        server, "SELECT role, disabled, iss FROM users WHERE id = ?", (user_id,))[0]


def test_invite_in_three_actions_with_role_defaulting_to_user(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server)
    try:
        page.locator("a.page-header__action").click()  # 1
        assert page.locator(INVITE).evaluate("d => d.open")
        assert page.input_value("#invite-role") == "user"
        page.keyboard.type("new.person@example.test")  # 2: focus starts on the email
        page.locator(INVITE + " button[type=submit]").click()  # 3
        page.wait_for_url("**/users")
        page.locator('[role="status"], [role="alert"]').first.wait_for()
        assert "Tell new.person@example.test to sign in with this address." in _body_text(page)
        row = _sql(server, "SELECT role, iss FROM users WHERE email = ?",
                   ("new.person@example.test",))[0]
        assert row == ("user", None)
        assert _row(page, "new.person@example.test").locator(
            ".banner__pill", has_text="Invited").count() == 1
    finally:
        context.close()


def test_a_duplicate_email_reopens_the_dialog_with_a_field_error(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed = _open(new_context, server)
    try:
        page.locator("a.page-header__action").click()
        page.fill("#invite-email", fx.USER_EMAIL)
        page.locator(INVITE + " button[type=submit]").click()
        page.locator(INVITE + ".is-modal[open]").wait_for(state="visible")
        assert page.input_value("#invite-email") == fx.USER_EMAIL
        assert page.locator("#invite-email").get_attribute("aria-invalid") == "true"
        assert "That email is already invited." in page.locator(INVITE).inner_text()
        assert page.evaluate(_ACTIVE_IN, page.locator(INVITE).element_handle())
    finally:
        context.close()


def test_change_a_role_saves_as_soon_as_the_select_changes(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _settled(page)
        row = _row(page, fx.OWNER_EMAIL)
        assert row.locator(".users-role-save").count() == 0
        row.locator("select[name=role]").select_option("admin")  # 1
        _wait_db(page, server, seed.owner_id, 0, "admin")
        page.wait_for_url("**/users")
        _settled(page)
        assert _row(page, fx.OWNER_EMAIL).locator("select").input_value() == "admin"
        assert "Role saved" in page.locator('[role="status"]').first.inner_text()
    finally:
        context.close()


def test_the_active_switch_deactivates_then_reactivates_a_user(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _settled(page)
        switch = "#user-%d button[role=switch]" % seed.owner_id
        assert page.locator(switch).get_attribute("aria-checked") == "true"
        page.locator(switch).click()
        _wait_db(page, server, seed.owner_id, 1, 1)
        _settled(page)
        assert page.locator(switch).get_attribute("aria-checked") == "false"
        assert _row(page, fx.OWNER_EMAIL).locator(
            ".banner__pill", has_text="Disabled").count() == 1
        page.locator(switch).click()
        _wait_db(page, server, seed.owner_id, 1, 0)
        _settled(page)
        assert page.locator(switch).get_attribute("aria-checked") == "true"
    finally:
        context.close()


def test_unlink_an_identity_from_the_overflow_menu_only_when_one_is_linked(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _sql(server, "UPDATE users SET iss = 'https://t.example.test/', sub = 's' "
                     "WHERE id = ?", (seed.owner_id,))
        page.reload()
        _settled(page)
        assert _row(page, fx.USER_EMAIL).locator("details.row-menu").count() == 0
        row = _row(page, fx.OWNER_EMAIL)
        row.locator("summary").click()
        item = row.get_by_role("button", name="Unlink identity")
        item.wait_for(state="visible")
        item.click()
        _wait_db(page, server, seed.owner_id, 2, None)
    finally:
        context.close()


def test_the_overflow_menu_works_from_the_keyboard(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _sql(server, "UPDATE users SET iss = 'https://t.example.test/', sub = 's' "
                     "WHERE id = ?", (seed.owner_id,))
        page.reload()
        _settled(page)
        summary = _row(page, fx.OWNER_EMAIL).locator("summary")
        summary.focus()
        page.keyboard.press("Enter")
        page.wait_for_function(
            "() => !!document.querySelector('details.row-menu[open]')")
        page.keyboard.press("Tab")
        page.wait_for_function(
            "() => document.activeElement.classList.contains('row-menu__item')")
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('details.row-menu[open]')"
            " && document.activeElement.tagName === 'SUMMARY'")
    finally:
        context.close()


def test_guard_sentences_replace_the_role_select_and_lock_the_switch(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _settled(page)
        own = _row(page, fx.ADMIN_EMAIL)
        assert "This is you." in own.inner_text()
        assert own.locator("select").count() == 0
        assert own.locator("button[role=switch]").is_disabled()
        assert "The last active administrator" not in own.inner_text()
        _sql(server, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.admin2_id,))
        page.reload()
        _settled(page)
        own = _row(page, fx.ADMIN_EMAIL)
        assert "The last active administrator cannot be changed." in own.inner_text()
        assert _row(page, fx.SECOND_ADMIN_EMAIL).locator(
            "button[role=switch]").get_attribute("aria-checked") == "false"
    finally:
        context.close()


def test_invite_and_row_controls_work_without_script(new_context, app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    with _no_js_page(new_context, server.base_url(), "/users",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        assert not page.locator(INVITE).is_visible()
        page.locator("a.page-header__action").click()
        assert page.locator(INVITE).is_visible()
        page.fill("#invite-email", "nojs@example.test")
        page.locator(INVITE + " button[type=submit]").click()
        page.wait_for_url("**/users")
        assert _sql(server, "SELECT COUNT(*) FROM users WHERE email = 'nojs@example.test'") == [(1,)]
        row = _row(page, fx.OWNER_EMAIL)
        row.locator("select[name=role]").select_option("admin")
        row.locator(".users-role-save").click()
        _wait_db(page, server, seed.owner_id, 0, "admin")
        page.wait_for_url("**/users")
        _row(page, fx.OWNER_EMAIL).locator("button[role=switch]").click()
        _wait_db(page, server, seed.owner_id, 1, 1)


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_table_and_cards_fit_and_every_control_is_44px(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport, lang, scheme)
    _sql(server, "UPDATE users SET email = ? WHERE email = ?", (LONG_EMAIL, fx.USER_EMAIL))
    _sql(server, "UPDATE users SET iss = 'https://t.example.test/', sub = 's' "
                 "WHERE id = ?", (seed.owner_id,))
    page.reload()
    where = "users/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        _settled(page)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        email = _row(page, LONG_EMAIL).locator(".users-email")
        assert email.evaluate("e => getComputedStyle(e).fontFamily").lower().count("mono") == 0
        assert email.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        assert _row(page, LONG_EMAIL).evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        wide = viewport["width"] >= 1120
        assert page.locator("thead").is_visible() == wide
        owner = "#user-%d" % seed.owner_id
        for control in (
                "a.page-header__action", owner + " select",
                owner + " button[role=switch]", owner + " summary"):
            _assert_hit_target(page, control, where)
        page.locator(owner + " summary").click()
        _assert_hit_target(page, owner + " .row-menu__item", where)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        page.keyboard.press("Escape")
        page.locator("a.page-header__action").click()
        dialog = page.locator(INVITE)
        assert dialog.evaluate("d => d.open"), where
        fit = dialog.evaluate(_FIT)
        assert fit["sw"] <= fit["cw"], (where, fit)
        for control in ("#invite-email", "#invite-role", "button[type=submit]",
                        "a.modal__dismiss", "a.modal__close"):
            _assert_hit_target(page, "%s %s" % (INVITE, control), where)
        page.keyboard.press("Escape")
        assert not dialog.evaluate("d => d.open")
    finally:
        context.close()
