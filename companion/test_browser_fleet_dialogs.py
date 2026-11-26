"""Real-browser flows of the Fleet dialogs and of the Add a frame page they lead
to: pair a frame in four actions, refuse a wrong code with the page shown
again, retire in two actions (the one
confirmation dialog), reassign from the owner row's button with one confirmation, re-activate; initial focus, Tab containment, Esc and focus return; and
the same forms through plain hash links with scripts blocked. Dialog geometry
holds at 360 and 1280px, in English and French, in both themes."""
import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_hit_target,
    _assert_no_page_overflow, _login, _no_js_page, _set_ui_theme)
from server import fleet_db

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44

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
    """The Fleet page with the Kitchen frame selected (its Access section holds
    Reassign and Retire; the list of frames holds Add a frame)."""
    seed = _seed(server)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=access&frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    _set_ui_theme(page, scheme)
    return context, page, seed


_RETIRE_LINK = "a.fleet-retire__link"
_ADD_BUTTON = ".fleet-add-button"


def click_add(page):
    """Choose Add a frame in the list of frames (a phone shows the list on /fleet only);
    it leads to the Add a frame page."""
    if not page.locator(_ADD_BUTTON).is_visible():
        page.goto(page.url.split("/fleet")[0] + "/fleet")
        page.locator(_ADD_BUTTON).wait_for(state="visible")
    page.locator(_ADD_BUTTON).click()


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
        click_add(page)  # 1
        page.wait_for_url("**/pair-frame")
        # Focus starts on the code field; wait for it so the keystrokes cannot start before it.
        page.wait_for_function("() => document.activeElement && document.activeElement.id === 'pair-code'")
        page.keyboard.type(fx.FAKE_CODE)  # 2
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)  # 3
        page.locator("form.pair-form button[type=submit]").click()  # 4
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
        assert page.locator(
            ".fleet-list a[href='/fleet?frame=%s']" % device["id"]).count() == 1
    finally:
        context.close()


def test_a_wrong_code_shows_the_page_again_with_the_typed_value_and_owner(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed_rows = _open(new_context, server)
    try:
        click_add(page)
        page.fill("#pair-code", "kkkk-2222")
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        page.locator("form.pair-form button[type=submit]").click()
        page.wait_for_url("**/pair-frame?refused=1*")
        assert page.input_value("#pair-code") == "KKKK-2222"
        assert page.locator("#pair-code").get_attribute("aria-invalid") == "true"
        assert "Code not recognised" in page.locator("form.pair-form").inner_text()
        assert page.locator("#pair-owner option:checked").inner_text().startswith(
            fx.OWNER_EMAIL)
    finally:
        context.close()


def test_an_owner_who_became_unavailable_is_a_field_error(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, _seed_rows = _open(new_context, server)
    try:
        click_add(page)
        page.fill("#pair-code", fx.FAKE_CODE)
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        conn = fleet_db.connect(server.state_dir)
        try:
            fleet_db.set_user_disabled(conn, fx.OWNER_EMAIL, True)
        finally:
            conn.close()
        page.locator("form.pair-form button[type=submit]").click()
        page.locator("#pair-owner[aria-invalid=true]").wait_for(state="visible")
        assert "That user is no longer available." in page.locator(
            "form.pair-form").inner_text()
    finally:
        context.close()


def test_retire_in_two_actions_with_focus_on_the_dismiss_control(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = page.locator("#dlg-retire-%s" % _slug(seed.owned_id))
        page.locator(_RETIRE_LINK).click()  # 1
        assert dialog.evaluate("d => d.open")
        assert page.evaluate(_ACTIVE) == "Keep frame"
        # The confirmation is the only dialog open.
        assert page.locator("dialog[open]").count() == 1
        dialog.locator("button[type=submit]").click()  # 2
        page.wait_for_url("**/fleet")
        assert _device(server, seed.owned_id) is None
        page.wait_for_function(
            "() => document.querySelector('#fleet-list-retired').textContent"
            ".trim().endsWith('2')", timeout=10000)
    finally:
        context.close()


def test_escape_closes_the_retire_confirmation_and_returns_focus_to_its_link(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog = page.locator("#dlg-retire-%s" % _slug(seed.owned_id))
        page.locator(_RETIRE_LINK).click()
        page.keyboard.press("Escape")
        assert not dialog.evaluate("d => d.open")
        # Focus goes back to the link when the dialog's close event fires, which can land a
        # frame after Escape returns.
        page.wait_for_function(
            "() => document.activeElement.classList.contains('fleet-retire__link')",
            timeout=5000)
        assert _device(server, seed.owned_id) is not None
    finally:
        context.close()


def test_tab_stays_inside_the_dialog_and_escape_returns_focus_to_the_trigger(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        dialog_id = "#dlg-retire-%s" % _slug(seed.owned_id)
        page.locator(_RETIRE_LINK).click()
        handle = page.locator(dialog_id).element_handle()
        for _ in range(12):
            page.keyboard.press("Tab")
            assert page.evaluate(_ACTIVE_IN, handle)
        for _ in range(12):
            page.keyboard.press("Shift+Tab")
            assert page.evaluate(_ACTIVE_IN, handle)
        page.keyboard.press("Escape")
        assert not page.locator(dialog_id).evaluate("d => d.open")
        page.wait_for_function(
            "() => document.activeElement.classList.contains('fleet-retire__link')",
            timeout=5000)
    finally:
        context.close()


def test_reassign_is_a_button_beside_the_owner_with_one_confirmation(
        new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        owner_row = page.locator(".fleet-block--access li.row", has_text=fx.OWNER_EMAIL).first
        button = owner_row.locator("a.row-action")
        assert button.inner_text() == "Reassign"
        assert button.bounding_box()["height"] >= MIN_TAP_PX - 0.5
        # No form with a wide select stays in the Access section.
        assert page.locator(".fleet-block--access select").count() == 0
        button.click()  # 1
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        page.wait_for_function("d => d.open", arg=dialog.element_handle(), timeout=10000)
        dialog.locator("select").select_option(label=fx.ADMIN_EMAIL + " (admin)")  # 2
        dialog.locator("button[type=submit]").click()  # 3
        page.wait_for_url("**/fleet?frame=%s&tab=access" % seed.owned_id)
        assert _device(server, seed.owned_id)["owner_user_id"] == seed.admin_id
    finally:
        context.close()


_PHONE = {"width": 390, "height": 844}
_REASSIGN_LABELS = {"en": ("Reassign", "Cancel"), "fr": ("Réattribuer", "Annuler")}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_reassign_sheet_is_short_with_a_cancel_button(
        lang, new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=_PHONE, lang=lang)
    try:
        submit_label, cancel_label = _REASSIGN_LABELS[lang]
        page.locator(".fleet-block--access li.row", has_text=fx.OWNER_EMAIL).first.locator(
            "a.row-action").click()
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        page.wait_for_function("d => d.open", arg=dialog.element_handle(), timeout=10000)
        assert dialog.locator("select").count() == 1
        assert dialog.locator("button[type=submit]").inner_text() == submit_label
        cancel = dialog.locator("a.modal__dismiss")
        assert cancel.inner_text() == cancel_label
        assert cancel.bounding_box()["height"] >= MIN_TAP_PX - 0.5
        text = dialog.inner_text()
        assert "XIAO" not in text and "Spectra" not in text
        assert seed.owned_id not in text
        assert dialog.locator(".modal__subtitle").count() == 0
        cancel.click()
        assert not dialog.evaluate("d => d.open")
        assert _device(server, seed.owned_id)["owner_user_id"] == seed.owner_id
    finally:
        context.close()


def test_a_long_owner_address_wraps_inside_the_reassign_sheet(
        new_context, app_server_in_process):
    """An unbreakable address in the effects list must not widen the sheet
    (it would scroll sideways and hide the left padding)."""
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=_PHONE)
    try:
        page.locator(".fleet-block--access li.row", has_text=fx.OWNER_EMAIL).first.locator(
            "a.row-action").click()
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        page.wait_for_function("d => d.open", arg=dialog.element_handle(), timeout=10000)
        dialog.evaluate(
            "d => { d.querySelector('.modal__effect span').textContent ="
            " 'owner.with.a.very.long.address.that.never.breaks.anywhere@example.test'; }")
        fit = dialog.evaluate(_FIT)
        assert fit["sw"] <= fit["cw"]
        box = dialog.locator("select").bounding_box()
        sheet = dialog.bounding_box()
        assert box["x"] >= sheet["x"] + 8
        assert box["x"] + box["width"] <= sheet["x"] + sheet["width"] - 8
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_reassign_confirm_waits_for_an_owner_and_lists_two_effects(
        lang, new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=_PHONE, lang=lang)
    try:
        page.locator(".fleet-block--access li.row", has_text=fx.OWNER_EMAIL).first.locator(
            "a.row-action").click()
        dialog = page.locator("#dlg-reassign-%s" % _slug(seed.owned_id))
        page.wait_for_function("d => d.open", arg=dialog.element_handle(), timeout=10000)
        submit = dialog.locator("button[type=submit]")
        hint = dialog.locator("[data-gate-hint]")
        assert submit.is_disabled() and hint.is_visible()
        assert submit.get_attribute("aria-disabled") == "true"
        assert dialog.locator(".modal__effects li").count() == 2
        dialog.locator("select").select_option(index=1)
        assert submit.is_enabled() and not hint.is_visible()
        dialog.locator("select").select_option(index=0)
        assert submit.is_disabled() and hint.is_visible()
        dialog.locator("a.modal__dismiss").click()
        assert _device(server, seed.owned_id)["owner_user_id"] == seed.owner_id
    finally:
        context.close()


def test_reactivate_from_the_retired_frames_page(new_context, app_server_in_process):
    server = app_server_in_process
    context, page, seed = _open(new_context, server)
    try:
        page.locator(".fleet-list a[href='/fleet?frame=%s']" % seed.retired_id).click()
        page.locator(".fleet-other a.fleet-action-button").click()
        dialog = page.locator("#dlg-reactivate-%s" % _slug(seed.retired_id))
        assert dialog.evaluate("d => d.open")
        assert page.evaluate(_ACTIVE) == "Keep retired"
        dialog.locator("button[type=submit]").click()
        page.wait_for_url("**/fleet")
        assert "Attic" not in page.locator(".fleet-list").inner_text()
    finally:
        context.close()


_REACTIVATED = {
    "en": ("Frame re-activated", "Press Reset on the frame", "up to 24 hours from now"),
    "fr": ("Cadre réactivé", "appuyez sur Reset", "24\u00a0h au plus"),
}
_GAPS = """d => {
  const box = s => d.querySelector(s).getBoundingClientRect();
  const sub = box('.modal__subtitle'), q = box('.modal__question'),
        more = box('.modal__more');
  return {above: q.top - sub.bottom, below: more.top - q.bottom, margin: getComputedStyle(
    d.querySelector('.modal__question')).marginTop};
}"""


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP],
                         ids=["360", "1280"])
def test_the_reactivation_question_sits_close_and_the_confirmation_explains_the_wake(
        new_context, app_server_in_process, viewport, lang):
    server = app_server_in_process
    context, page, seed = _open(new_context, server, viewport=viewport, lang=lang)
    try:
        page.goto(server.base_url() + "/fleet?frame=" + seed.retired_id)
        page.locator("main").wait_for(state="visible")
        page.locator(".fleet-other a.fleet-action-button").click()
        dialog = page.locator("#dlg-reactivate-%s" % _slug(seed.retired_id))
        assert dialog.evaluate("d => d.open")
        animation_settle.wait_settled(page, "#dlg-reactivate-%s" % _slug(seed.retired_id))
        gaps = dialog.evaluate(_GAPS)
        assert gaps["margin"] == "0px"
        assert 0 <= gaps["above"] <= 12 and 0 <= gaps["below"] <= 28, gaps
        for selector in ("button[type=submit]", "a.modal__dismiss"):
            _assert_hit_target(page, "#dlg-reactivate-%s %s" % (_slug(seed.retired_id), selector),
                               "the re-activation dialog")
        fit = dialog.evaluate(_FIT)
        assert fit["sw"] <= fit["cw"]
        dialog.locator("button[type=submit]").click()
        toast = page.locator(".toast").first
        toast.wait_for(state="visible")
        text = toast.inner_text()
        for part in _REACTIVATED[lang]:
            assert part in text, (part, text)
        box = toast.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        assert _assert_no_page_overflow(page, "Fleet after re-activation") == ""
    finally:
        context.close()


def test_the_add_button_leads_to_the_page_that_pairs_without_script(
        new_context, app_server_in_process):
    server = app_server_in_process
    seed = _seed(server)
    with _no_js_page(new_context, server.base_url(), "/fleet",
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        page.locator(_ADD_BUTTON).click()
        page.wait_for_url("**/pair-frame")
        page.fill("#pair-code", fx.FAKE_CODE)
        page.select_option("#pair-owner", label=fx.OWNER_EMAIL)
        page.locator("form.pair-form button[type=submit]").click()
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
    with _no_js_page(new_context, server.base_url(),
                     "/fleet?tab=access&frame=" + seed.owned_id,
                     viewport=VIEWPORT_MIN_SUPPORTED) as page:
        dialog_id = "#dlg-retire-%s" % _slug(seed.owned_id)
        page.locator(_RETIRE_LINK).click()
        assert page.locator(dialog_id).is_visible()
        page.locator(dialog_id + " a.modal__dismiss").click()
        assert not page.locator(dialog_id).is_visible()
        assert _device(server, seed.owned_id) is not None
        page.locator(_RETIRE_LINK).click()
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
        for dialog_id, controls in (
                ("dlg-retire-%s" % _slug(seed.owned_id), (
                    "button[type=submit]", "a.modal__dismiss", "a.modal__close")),):
            if not page.locator(_RETIRE_LINK).is_visible():
                page.goto(server.base_url() + "/fleet?tab=access&frame=" + seed.owned_id)
            page.locator(_RETIRE_LINK).click()
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
        page.goto(server.base_url() + "/fleet")
        click_add(page)
        page.wait_for_url("**/pair-frame")
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        for control in (
                "#pair-code", "#pair-owner", "form.pair-form button[type=submit]",
                "a.pair-form__cancel"):
            _assert_hit_target(page, control, where)
    finally:
        context.close()
