"""Real-browser flows of the Users page: invite in a few actions, a duplicate
email refused with the dialog reopened, change a role, disable then enable,
unlink an identity, the guard sentences, focus handling, the no-script hash
links, and dialog and list geometry at 360 and 1280px in both languages and
both themes."""
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


def _manage(page, user_id):
    page.locator("a.entity-row__button[href='#dlg-user-%d']" % user_id).click()
    dialog = page.locator("#dlg-user-%d" % user_id)
    assert dialog.evaluate("d => d.open")
    return dialog


def _body_text(page):
    return page.locator("body").inner_text()


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
        assert page.locator("li.entity-row", has_text="new.person@example.test").locator(
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


def test_change_a_role_from_the_manage_dialog(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = _manage(page, seed.owner_id)  # 1
        dialog.locator("select[name=role]").select_option("admin")  # 2
        dialog.get_by_role("button", name="Save role").click()  # 3
        page.wait_for_url("**/users")
        assert _user(server, seed.owner_id)[0] == "admin"
        assert "Administrator · 0 frames" in page.locator(
            "li.entity-row", has_text=fx.OWNER_EMAIL).inner_text()
    finally:
        context.close()


def test_disable_then_enable_a_user(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = _manage(page, seed.owner_id)
        dialog.get_by_role("button", name="Disable user").click()
        page.wait_for_url("**/users")
        assert _user(server, seed.owner_id)[1] == 1
        assert page.locator("li.entity-row", has_text=fx.OWNER_EMAIL).locator(
            ".banner__pill", has_text="Disabled").count() == 1
        dialog = _manage(page, seed.owner_id)
        assert dialog.get_by_role("button", name="Disable user").count() == 0
        dialog.get_by_role("button", name="Enable user").click()
        page.wait_for_url("**/users")
        assert _user(server, seed.owner_id)[1] == 0
    finally:
        context.close()


def test_unlink_an_identity_only_when_one_is_linked(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _sql(server, "UPDATE users SET iss = 'https://t.example.test/', sub = 's' "
                     "WHERE id = ?", (seed.owner_id,))
        page.reload()
        never = _manage(page, seed.user_id)
        assert never.get_by_role("button", name="Unlink identity").count() == 0
        never.locator("a.modal__dismiss").click()
        dialog = _manage(page, seed.owner_id)
        dialog.get_by_role("button", name="Unlink identity").click()
        page.wait_for_url("**/users")
        assert _user(server, seed.owner_id)[2] is None
    finally:
        context.close()


def test_guard_sentences_replace_the_controls_for_self_and_the_last_admin(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        own = _manage(page, seed.admin_id)
        assert "This is you." in own.inner_text()
        assert own.get_by_role("button", name="Disable user").count() == 0
        assert own.get_by_role("button", name="Save role").count() == 0
        assert "The last active administrator" not in own.inner_text()
        own.locator("a.modal__dismiss").click()
        _sql(server, "UPDATE users SET disabled = 1 WHERE id = ?", (seed.admin2_id,))
        page.reload()
        own = _manage(page, seed.admin_id)
        assert "The last active administrator cannot be changed." in own.inner_text()
        assert own.get_by_role("button", name="Disable user").count() == 0
    finally:
        context.close()


def test_tab_stays_inside_the_dialog_and_escape_returns_focus_to_the_opener(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        button = "a.entity-row__button[href='#dlg-user-%d']" % seed.owner_id
        _manage(page, seed.owner_id)
        handle = page.locator("#dlg-user-%d" % seed.owner_id).element_handle()
        for _ in range(12):
            page.keyboard.press("Tab")
            assert page.evaluate(_ACTIVE_IN, handle)
        page.keyboard.press("Escape")
        assert not page.locator("#dlg-user-%d" % seed.owner_id).evaluate("d => d.open")
        assert page.evaluate(
            "s => document.activeElement === document.querySelector(s)", button)
    finally:
        context.close()


def test_invite_and_manage_work_through_hash_links_without_script(
        new_context, app_server_in_process):
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
        page.locator("a.entity-row__button[href='#dlg-user-%d']" % seed.owner_id).click()
        dialog = page.locator("#dlg-user-%d" % seed.owner_id)
        assert dialog.is_visible()
        dialog.get_by_role("button", name="Disable user").click()
        page.wait_for_url("**/users")
        assert _user(server, seed.owner_id)[1] == 1


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_list_and_dialogs_fit_and_every_control_is_44px(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport, lang, scheme)
    _sql(server, "UPDATE users SET email = ? WHERE email = ?", (LONG_EMAIL, fx.USER_EMAIL))
    page.reload()
    where = "users/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        title = page.locator("li.entity-row", has_text=LONG_EMAIL).locator(
            ".entity-row__title")
        assert title.evaluate("e => getComputedStyle(e).fontFamily").lower().count("mono") == 0
        assert title.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        assert page.locator("li.entity-row", has_text=LONG_EMAIL).evaluate(
            "e => e.scrollWidth <= e.clientWidth + 1")
        for opener, dialog_id, controls in (
                ("a.page-header__action", "dlg-invite-user", (
                    "#invite-email", "#invite-role", "button[type=submit]",
                    "a.modal__dismiss", "a.modal__close")),
                ("a.entity-row__button[href='#dlg-user-%d']" % seed.owner_id,
                 "dlg-user-%d" % seed.owner_id, (
                     "select", "button[type=submit]", "a.modal__dismiss",
                     "a.modal__close"))):
            _assert_hit_target(page, opener, where)
            page.locator(opener).click()
            dialog = page.locator("#" + dialog_id)
            assert dialog.evaluate("d => d.open"), where
            fit = dialog.evaluate(_FIT)
            assert fit["sw"] <= fit["cw"], (where, dialog_id, fit)
            assert not _assert_no_page_overflow(page, where, viewport["width"])
            for control in controls:
                _assert_hit_target(page, "#%s %s" % (dialog_id, control), where)
            page.keyboard.press("Escape")
            assert not dialog.evaluate("d => d.open")
    finally:
        context.close()
