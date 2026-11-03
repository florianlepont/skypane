"""Real-browser flows of the Fleet dialogs: pair a frame in four actions,
refuse a wrong code with the dialog reopened, retire in three, reassign in
four, re-activate; initial focus, Tab containment, Esc and focus return; and
the same forms through plain hash links with scripts blocked. Dialog geometry
holds at 360 and 1280px, in English and French, in both themes."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme)
from server import fleet_db

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44
ADD = "#dlg-add-frame"

_ACTIVE = "() => document.activeElement.textContent.trim()"
# Tab past the last control may leave the document for the browser's own
# chrome (the active element is then the body); it never reaches the page behind.
_ACTIVE_IN = (
    "d => d.contains(document.activeElement)"
    " || document.activeElement === document.body")
_FIT = "d => ({sw: d.scrollWidth, cw: d.clientWidth})"


def _slug(frame_id):
    return frame_id.lower().replace("_", "-")


def _seed(server):
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    return seed


def _open(new_context, server, viewport=VIEWPORT_DESKTOP, lang="en", scheme="light"):
    seed = _seed(server)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet")
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


def _row(page, name):
    return page.locator("li.entity-row", has=page.locator("text=%s" % name)).first


def _open_menu_item(page, name, label):
    """Two actions: the row's menu button, then the named item."""
    row = _row(page, name)
    row.locator("summary.row-menu__toggle").click()
    row.locator("a.row-menu__item", has_text=label).click()


def _device(server, device_id):
    conn = fleet_db.connect(server.state_dir)
    try:
        return fleet_db.get_device(conn, device_id)
    finally:
        conn.close()


def test_pair_a_frame_in_four_actions(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        page.locator("a.page-header__action").click()  # 1
        dialog = page.locator(ADD)
        assert dialog.evaluate("d => d.open")
        page.keyboard.type(fx.FAKE_CODE)  # 2: focus starts on the code field
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)  # 3
        dialog.locator("button[type=submit]").click()  # 4
        page.wait_for_url("**/fleet")
        page.locator(".toast, [role=status], [role=alert]").first.wait_for()
        assert "Frame paired" in page.locator("main").inner_text() + page.locator(
            "body").inner_text()
        conn = fleet_db.connect(server.state_dir)
        try:
            device = fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
        finally:
            conn.close()
        assert device is not None and device["owner_user_id"] == seed.owner_id
        assert page.locator("a.entity-row__title[href='/devices/%s/']" % device["id"]).count() == 1
    finally:
        context.close()


def test_a_wrong_code_reopens_the_dialog_with_the_typed_value(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed_rows = _open(new_context, server)
    try:
        page.locator("a.page-header__action").click()
        page.fill("#pair-code", "kkkk-2222")
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        page.locator(ADD + " button[type=submit]").click()
        page.locator(ADD + ".is-modal[open]").wait_for(state="visible")
        assert page.input_value("#pair-code") == "KKKK-2222"
        assert page.locator("#pair-code").get_attribute("aria-invalid") == "true"
        assert "Code not recognised" in page.locator(ADD).inner_text()
        assert page.evaluate(_ACTIVE_IN, page.locator(ADD).element_handle())
        page.keyboard.press("Escape")
        assert not page.locator(ADD).evaluate("d => d.open")
    finally:
        context.close()


def test_missing_owner_reopens_the_dialog_with_a_field_error(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed_rows = _open(new_context, server)
    try:
        page.locator("a.page-header__action").click()
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator(ADD + " button[type=submit]").click()
        page.locator(ADD + ".is-modal[open]").wait_for(state="visible")
        assert page.locator("#pair-owner").get_attribute("aria-invalid") == "true"
        assert "Choose an owner." in page.locator(ADD).inner_text()
    finally:
        context.close()


def test_retire_in_three_actions_with_focus_on_the_dismiss_control(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = page.locator("#dlg-retire-%s" % _slug(seed.owned_id))
        _open_menu_item(page, "Kitchen", "Retire")  # 1, 2
        assert dialog.evaluate("d => d.open")
        assert page.evaluate(_ACTIVE) == "Keep frame"
        dialog.locator("button[type=submit]").click()  # 3
        page.wait_for_url("**/fleet")
        assert _device(server, seed.owned_id) is None
        assert page.locator("details.fleet-retired > summary").inner_text().endswith("(2)")
    finally:
        context.close()


def test_escape_closes_a_confirm_and_returns_focus_to_the_row_menu_button(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = page.locator("#dlg-retire-%s" % _slug(seed.owned_id))
        _open_menu_item(page, "Kitchen", "Retire")
        page.keyboard.press("Escape")
        assert not dialog.evaluate("d => d.open")
        # Focus goes back to the menu button when the dialog's close event
        # fires, which can land a frame after Escape returns.
        page.wait_for_function(
            "() => document.activeElement.classList.contains('row-menu__toggle')",
            timeout=5000)
        assert _device(server, seed.owned_id) is not None
    finally:
        context.close()


def test_tab_stays_inside_the_dialog_and_escape_returns_focus_to_the_trigger(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed_rows = _open(new_context, server)
    try:
        trigger = page.locator("a.page-header__action")
        trigger.click()
        handle = page.locator(ADD).element_handle()
        for _ in range(12):
            page.keyboard.press("Tab")
            assert page.evaluate(_ACTIVE_IN, handle)
        for _ in range(12):
            page.keyboard.press("Shift+Tab")
            assert page.evaluate(_ACTIVE_IN, handle)
        page.keyboard.press("Escape")
        assert not page.locator(ADD).evaluate("d => d.open")
        page.wait_for_function(
            "() => document.activeElement.classList.contains('page-header__action')",
            timeout=5000)
    finally:
        context.close()


def test_keep_current_owner_dismisses_without_changing_anything(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _open_menu_item(page, "Kitchen", "Reassign")
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        assert dialog.evaluate("d => d.open")
        dialog.locator("a.modal__dismiss").click()
        assert not dialog.evaluate("d => d.open")
        assert _device(server, seed.owned_id)["owner_user_id"] == seed.owner_id
    finally:
        context.close()


def test_reassign_in_four_actions(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        _open_menu_item(page, "Kitchen", "Reassign")  # 1, 2
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        dialog.locator("select").select_option(label=fx.ADMIN_EMAIL + " (admin)")  # 3
        dialog.locator("button[type=submit]").click()  # 4
        page.wait_for_url("**/fleet")
        assert _device(server, seed.owned_id)["owner_user_id"] == seed.admin_id
    finally:
        context.close()


def test_reactivate_from_the_retired_group(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        page.locator("details.fleet-retired > summary").click()
        _open_menu_item(page, "Attic", "Re-activate")
        dialog = page.locator("#dlg-reactivate-%s" % _slug(seed.retired_id))
        assert dialog.evaluate("d => d.open")
        assert page.evaluate(_ACTIVE) == "Keep retired"
        dialog.locator("button[type=submit]").click()
        page.wait_for_url("**/fleet")
        assert page.locator("details.fleet-retired").count() == 0
    finally:
        context.close()


def test_the_add_dialog_pairs_through_the_hash_link_without_script(
        new_context, app_server_in_process):
    server = app_server_in_process
    seed = _seed(server)
    with _no_js_page(new_context, server.base_url(), "/fleet",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        assert not page.locator(ADD).is_visible()
        page.locator("a.page-header__action").click()
        dialog = page.locator(ADD)
        assert dialog.is_visible()
        page.fill("#pair-code", fx.FAKE_CODE)
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        dialog.locator("button[type=submit]").click()
        page.wait_for_url("**/fleet")
        conn = fleet_db.connect(server.state_dir)
        try:
            device = fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
        finally:
            conn.close()
        assert device is not None and device["owner_user_id"] == seed.owner_id


def test_the_no_script_dismiss_link_returns_to_the_page_and_retire_posts(
        new_context, app_server_in_process):
    server = app_server_in_process
    seed = _seed(server)
    with _no_js_page(new_context, server.base_url(), "/fleet",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        dialog_id = "#dlg-retire-%s" % _slug(seed.owned_id)
        row = _row(page, "Kitchen")
        row.locator("summary.row-menu__toggle").click()
        row.locator("a.row-menu__item", has_text="Retire").click()
        assert page.locator(dialog_id).is_visible()
        page.locator(dialog_id + " a.modal__dismiss").click()
        assert not page.locator(dialog_id).is_visible()
        assert _device(server, seed.owned_id) is not None
        row = _row(page, "Kitchen")
        row.locator("summary.row-menu__toggle").click()
        row.locator("a.row-menu__item", has_text="Retire").click()
        page.locator(dialog_id + " button[type=submit]").click()
        page.wait_for_url("**/fleet")
        assert _device(server, seed.owned_id) is None


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_dialogs_fit_and_every_control_is_44px(
        new_context, app_server_in_process, viewport, lang, scheme):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport, lang, scheme)
    where = "dialogs/%d/%s/%s" % (viewport["width"], lang, scheme)
    try:
        for opener, dialog_id, controls in (
                ("a.page-header__action", "dlg-add-frame", (
                    "#pair-code", "#pair-owner", "button[type=submit]",
                    "a.modal__dismiss", "a.modal__close")),
                (None, "dlg-reassign-%s" % _slug(seed.owned_id), (
                    "select", "button[type=submit]", "a.modal__dismiss",
                    "a.modal__close")),
                (None, "dlg-retire-%s" % _slug(seed.owned_id), (
                    "button[type=submit]", "a.modal__dismiss", "a.modal__close"))):
            if opener:
                page.locator(opener).click()
            else:
                row = page.locator("li.entity-row", has=page.locator("text=Kitchen")).first
                row.locator("summary.row-menu__toggle").click()
                href = "#" + dialog_id
                row.locator("a.row-menu__item[href='%s']" % href).click()
            dialog = page.locator("#" + dialog_id)
            assert dialog.evaluate("d => d.open"), where
            fit = dialog.evaluate(_FIT)
            assert fit["sw"] <= fit["cw"], (where, dialog_id, fit)
            assert not _assert_no_page_overflow(page, where, viewport["width"])
            for control in controls:
                _assert_hit_target(page, "#%s %s" % (dialog_id, control), where)
            title = dialog.locator("h2").evaluate("e => getComputedStyle(e).fontFamily")
            assert "mono" not in title.lower()
            page.keyboard.press("Escape")
            assert not dialog.evaluate("d => d.open")
    finally:
        context.close()
