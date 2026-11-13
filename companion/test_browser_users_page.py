"""Real-browser flows of the Users table: invite in a few actions, a duplicate
email refused with the dialog reopened, a role change that asks before it
saves, the Active switch, unlink and Delete user in the "..." menu, the guard sentences,
keyboard use of the menu, the no-script controls, and table and card geometry
at 360 and 1280px in both languages and both themes."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.pages import users_page
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


ROLE_DIALOG = "dialog#dlg-role-user-%d"
DIALOG_SHOWN = (
    "sel => { const d = document.querySelector(sel);"
    " if (!d || !d.open) return false; const r = d.getBoundingClientRect();"
    " return r.width > 0 && r.height > 0 && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity); }")


def _change_role(page, seed, email, role):
    """Changes the row's select and waits for the confirmation it lands on."""
    dialog = ROLE_DIALOG % seed.owner_id
    row = _row(page, email)
    assert row.locator(".users-role-save").count() == 0
    row.locator("select[name=role]").select_option(role)
    page.wait_for_function("() => document.readyState === 'complete'")
    page.wait_for_function(DIALOG_SHOWN, arg=dialog, timeout=10000)
    return dialog


@pytest.mark.parametrize("viewport", [VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED])
def test_a_changed_role_is_saved_only_after_its_confirmation(
        new_context, app_server_in_process, viewport):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=viewport)
    try:
        _settled(page)
        dialog = _change_role(page, seed, fx.OWNER_EMAIL, "admin")  # 1
        assert _user(server, seed.owner_id)[0] == "user"
        text = page.locator(dialog).inner_text()
        assert "Make this person an administrator?" in text and fx.OWNER_EMAIL in text
        # Enter must not grant the rights: the way out holds the focus.
        page.wait_for_function(
            "sel => document.activeElement === document.querySelector(sel + ' .modal__dismiss')",
            arg=dialog, timeout=5000)
        for control in (dialog + " button[type=submit]", dialog + " .modal__dismiss"):
            box = page.locator(control).bounding_box()
            assert box["height"] >= 44 and box["width"] >= 44, (control, box)
        page.locator(dialog + " button[type=submit]").click()  # 2
        _wait_db(page, server, seed.owner_id, 0, "admin")
        page.wait_for_url("**/users")
        _settled(page)
        assert _row(page, fx.OWNER_EMAIL).locator("select").input_value() == "admin"
        assert "Role saved" in page.locator('[role="status"]').first.inner_text()
    finally:
        context.close()


def test_backing_out_of_the_role_confirmation_changes_nothing(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        _settled(page)
        dialog = _change_role(page, seed, fx.OWNER_EMAIL, "admin")
        page.locator(dialog + " .modal__dismiss").click()
        page.wait_for_function(
            "sel => { const d = document.querySelector(sel); return !d || !d.open; }",
            arg=dialog, timeout=5000)
        # The address no longer asks: a reload shows the plain page.
        page.wait_for_function("() => location.pathname + location.search === '/users'")
        page.reload()
        _settled(page)
        assert page.locator(dialog).count() == 0
        assert _user(server, seed.owner_id)[0] == "user"
        assert _row(page, fx.OWNER_EMAIL).locator("select").input_value() == "user"
        assert _sql(server, "SELECT COUNT(*) FROM audit_log WHERE action = 'user.role'") == [(0,)]
    finally:
        context.close()


@pytest.mark.parametrize("how", ["escape", "keep"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_closing_the_role_confirmation_returns_the_focus_to_that_roles_select(
        new_context, app_server_in_process, how, lang):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=VIEWPORT_MIN_SUPPORTED, lang=lang)
    try:
        _settled(page)
        dialog = _change_role(page, seed, fx.OWNER_EMAIL, "admin")
        if how == "escape":
            page.keyboard.press("Escape")
        else:
            page.locator(dialog + " .modal__dismiss").click()
        page.wait_for_function(
            "id => !document.querySelector('dialog[open]')"
            " && document.activeElement && document.activeElement.id === id",
            arg="role-%d" % seed.owner_id, timeout=5000)
        assert page.locator("#role-%d" % seed.owner_id).input_value() == "user"
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


@pytest.mark.parametrize("lang,disabled,enabled", [
    ("en", "User disabled", "User enabled"),
    ("fr", "Utilisateur désactivé", "Utilisateur activé"),
])
def test_the_active_switch_confirms_each_change_with_a_toast(
        new_context, app_server_in_process, lang, disabled, enabled):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, lang=lang)
    try:
        _settled(page)
        switch = "#user-%d button[role=switch]" % seed.owner_id
        toast = "[data-quick-toast] .toast"
        page.locator(switch).click()
        page.wait_for_function(
            "([s, t]) => { const e = document.querySelector(s);"
            " return !!e && e.textContent.indexOf(t) >= 0 && e.textContent.indexOf(%r) >= 0; }" %
            fx.OWNER_EMAIL, arg=[toast, disabled], timeout=10000)
        assert "toast--success" in page.locator(toast).get_attribute("class")
        page.locator(switch).click()
        page.wait_for_function(
            "([s, t]) => { const e = document.querySelector(s);"
            " return !!e && e.textContent.indexOf(t) >= 0; }",
            arg=[toast, enabled], timeout=10000)
        assert page.locator(toast).count() == 1
        _wait_db(page, server, seed.owner_id, 1, 0)
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
        plain = _row(page, fx.USER_EMAIL)
        assert plain.locator("details.row-menu").count() == 1
        assert plain.locator("form.users-menu__form").count() == 0
        assert plain.locator("a.row-menu__item").count() == 1
        row = _row(page, fx.OWNER_EMAIL)
        row.locator("summary").click()
        item = row.get_by_role("button", name="Reset sign-in")
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
        confirm = page.locator("#dlg-role-user-%d" % seed.owner_id)
        confirm.wait_for(state="visible")
        assert _user(server, seed.owner_id)[0] == "user"
        confirm.locator("button[type=submit]").click()
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
        # A long address never runs into the next column: a phone card wraps it, the table
        # keeps it on one line that ends in an ellipsis. Its title is the whole address.
        wide = viewport["width"] >= 1272
        if wide:
            assert email.evaluate("e => getComputedStyle(e).textOverflow") == "ellipsis"
            assert email.evaluate("e => e.scrollWidth > e.clientWidth")
            assert email.evaluate(
                "e => e.getBoundingClientRect().right"
                " <= e.closest('.users-cell').getBoundingClientRect().right + 0.5")
        else:
            assert email.evaluate("e => getComputedStyle(e).overflowWrap") == "anywhere"
            assert email.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        assert email.get_attribute("title") == LONG_EMAIL
        assert _row(page, LONG_EMAIL).evaluate("e => e.scrollWidth <= e.clientWidth + 1")
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


_BOXES = (
    "() => { const box = s => { const r = document.querySelector(s).getBoundingClientRect();"
    " return {l: r.left, r: r.right, t: r.top, b: r.bottom}; };"
    " return {title: box('h1.page-title'), button: box('a.page-header__action'),"
    " main: box('main')}; }")


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("width", (360, 390, 1280))
def test_the_invite_button_never_overlaps_the_title(
        new_context, app_server_in_process, width, lang):
    """on a phone the invite action is a full-width button under the title; on desktop it
    shares the title's row; the title and the button never overlap"""
    viewport = {"width": width, "height": 844}
    context, page, _seed = _open(new_context, app_server_in_process, viewport, lang)
    try:
        _settled(page)
        boxes = page.evaluate(_BOXES)
        title, button = boxes["title"], boxes["button"]
        overlap = (title["l"] < button["r"] and button["l"] < title["r"]
                   and title["t"] < button["b"] and button["t"] < title["b"])
        assert not overlap, (width, lang, boxes)
        if width < 700:
            assert button["t"] >= title["b"], (width, lang, boxes)
            assert button["r"] - button["l"] >= boxes["main"]["r"] - boxes["main"]["l"] - 2 * 24
        else:
            assert button["l"] >= title["r"] - 1, (width, lang, boxes)
            assert button["t"] < title["b"], (width, lang, boxes)
        assert button["b"] - button["t"] >= 44
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_row_menu_keeps_every_item_on_one_line_inside_the_screen(
        new_context, app_server_in_process, viewport, lang):
    """each item of the "..." menu is one line tall (never wrapped), the panel is as wide as its
    longest label and sits inside the viewport, on a phone card and in the desktop table"""
    context, page, _seed = _open(new_context, app_server_in_process, viewport, lang=lang)
    try:
        _settled(page)
        row = _row(page, fx.USER_EMAIL) if page.locator("tr.users-row", has_text=fx.USER_EMAIL).count() \
            else page.locator("tr.users-row").nth(1)
        row.locator("summary").click()
        page.wait_for_function(
            "() => { const p = document.querySelector('details.row-menu[open] .row-menu__panel');"
            " return !!p && p.getBoundingClientRect().width > 0; }", timeout=10000)
        report = page.evaluate("""() => {
            const panel = document.querySelector('details.row-menu[open] .row-menu__panel');
            const box = panel.getBoundingClientRect();
            const items = [...panel.querySelectorAll('.row-menu__item')].map(item => {
                const r = item.getBoundingClientRect();
                const range = document.createRange();
                range.selectNodeContents(item);
                return {height: r.height, lines: range.getClientRects().length,
                        overflow: item.scrollWidth - item.clientWidth};
            });
            return {items, left: box.left, right: box.right, vw: document.documentElement.clientWidth};
        }""")
        assert report["items"], report
        for item in report["items"]:
            assert item["lines"] == 1 and item["height"] < 60 and item["overflow"] <= 1, report
        assert report["left"] >= -0.5 and report["right"] <= report["vw"] + 0.5, report
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_users_list_is_one_surface_with_its_count_above_it(
        new_context, app_server_in_process, viewport):
    """the section around the list has no surface of its own (no background, border or shadow),
    and the count line sits wholly above the table or the first card instead of on an edge"""
    context, page, _seed = _open(new_context, app_server_in_process, viewport)
    try:
        _settled(page)
        report = page.evaluate("""() => {
            const section = document.querySelector('.users-section');
            const style = getComputedStyle(section);
            const count = document.querySelector('.entity-count').getBoundingClientRect();
            const first = document.querySelector('.users-table .users-row').getBoundingClientRect();
            const table = document.querySelector('.users-table').getBoundingClientRect();
            return {bg: style.backgroundColor, border: style.borderTopWidth, shadow: style.boxShadow,
                    countBottom: count.bottom, tableTop: table.top, firstTop: first.top};
        }""")
        assert report["bg"] in ("rgba(0, 0, 0, 0)", "transparent"), report
        assert report["border"] == "0px" and report["shadow"] == "none", report
        assert report["countBottom"] <= report["tableTop"] + 0.5, report
        assert report["countBottom"] <= report["firstTop"] + 0.5, report
    finally:
        context.close()


# --- an error no handler expected ---------------------------------------------

ERROR_WORDS = {"en": ("Something went wrong", "Back to Home"),
               "fr": ("Un problème est survenu", "Retour à l’accueil")}


def _boom(*_args, **_kwargs):
    raise RuntimeError("not for the page")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_an_unexpected_error_shows_the_app_s_own_page_with_a_way_back(
        new_context, app_server_in_process, monkeypatch, lang, scheme):
    """The browser shows the app's page, not its own "this page isn't working": at 360px, in
    both languages and themes, with the navigation and a 44px link that leads back."""
    server = app_server_in_process
    context, page, _seed = _open(
        new_context, server, viewport=VIEWPORT_MIN_SUPPORTED, lang=lang, scheme=scheme)
    try:
        _settled(page)
        monkeypatch.setattr(users_page, "render", _boom)
        response = page.goto(server.base_url() + "/users")
        assert response.status == 500
        assert page.url.startswith(server.base_url())
        _set_ui_theme(page, scheme)
        back = "a.error-home-button"
        _settled(page, back)
        title, label = ERROR_WORDS[lang]
        assert page.locator("h1").inner_text().strip() == title
        assert page.locator(back).inner_text().strip() == label
        assert page.locator(".tab-bar").is_visible()
        _assert_hit_target(page, back, "500 page")
        assert not _assert_no_page_overflow(page, "500 page", 360)
        monkeypatch.undo()
        page.locator(back).click()
        page.wait_for_function("() => location.pathname === '/'")
    finally:
        monkeypatch.undo()
        context.close()
