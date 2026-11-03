"""Real-browser checks of the My frames card on Account: an owner adds a
co-manager through Manage access (the dialog reopens), a co-manager leaves
through Leave frame and lands on a valid page, owned frames offer Manage
access while shared ones offer Leave, geometry and tap targets at 360 and
1280px in both languages and themes, the same flows through plain hash links
with scripts blocked, and no administrator vocabulary on a user's page."""
import re

import pytest

from co_manager_browser_support import (
    INVITED, LONG_CO, LONG_OWNER, MIN_TAP_PX, SUBPIXEL, Rig, _no_sideways_scroll, _open)
from companion.test_browser_ux_helpers import UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED

pytestmark = pytest.mark.browser

LANGS = ("en", "fr")
VIEWPORTS = (VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900})
LABELS = {
    "en": {"manage": "Manage access", "leave": "Leave frame", "add": "Add co-manager",
           "confirm": "Leave this frame", "stay": "Stay on this frame"},
    "fr": {"manage": "Gérer l’accès", "leave": "Quitter le cadre",
           "add": "Ajouter un co-gestionnaire", "confirm": "Quitter ce cadre",
           "stay": "Rester sur ce cadre"},
}
# Words an ordinary user's page must never carry.
ADMIN_WORDS = re.compile(r"\b(Admin\w*|Console|Fleet|Releases?|Device)\b", re.IGNORECASE)


class AccountRig(Rig):
    def __init__(self, server):
        super().__init__(server)
        self.slug = self.seed.owned_id.lower().replace("_", "-")
        self.access = "#dlg-access-" + self.slug
        self.leave = "#dlg-leave-" + self.slug
        self.email = "#co-manager-%s-email" % self.slug

    def row(self, page):
        return page.locator("li.entity-row", has_text="Kitchen")


@pytest.fixture
def arig(app_server_in_process):
    return AccountRig(app_server_in_process)


def _open_account(new_context, rig, who, lang="en", theme=None,
                  viewport=VIEWPORT_MIN_SUPPORTED, query="", **context_kwargs):
    return _open(
        new_context, rig, who, path="/account" + query, lang=lang, theme=theme,
        viewport=viewport, **context_kwargs)


def _wait_focus_on(page, selector):
    page.wait_for_function(
        "(sel) => document.activeElement === document.querySelector(sel)", arg=selector)


def test_an_owner_adds_a_co_manager_from_account_and_the_dialog_reopens(
        new_context, arig):
    context, page = _open_account(new_context, arig, "owner")
    try:
        arig.row(page).get_by_role("link", name="Manage access").click()
        page.locator(arig.access + "[open]").wait_for(state="visible")
        page.fill(arig.email, INVITED)
        page.locator(arig.access + ' form[action$="/co-managers/add"] button').click()
        page.wait_for_url("**/account?access=*")
        page.locator(arig.access + "[open]").wait_for(state="visible")
        assert INVITED in arig.members()
        assert page.locator(
            arig.access + " li.data-card", has_text=INVITED).count() == 1
        toast = page.locator('.toast-region--flash .toast[role="status"]')
        toast.wait_for(state="visible")
        assert "Co-manager added" in toast.inner_text()
        page.locator(arig.access + " a.modal__dismiss").click()
        page.wait_for_function(
            "(sel) => !document.querySelector(sel).open", arg=arig.access)
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def test_an_owner_removes_a_co_manager_from_account(new_context, arig):
    context, page = _open_account(
        new_context, arig, "owner", query="?access=" + arig.seed.owned_id)
    try:
        page.locator(arig.access + "[open]").wait_for(state="visible")
        page.get_by_role("button", name="Remove %s from this frame" % LONG_CO).click()
        page.wait_for_url("**/account?access=*")
        page.locator(arig.access + "[open]").wait_for(state="visible")
        assert arig.members() == []
    finally:
        context.close()


def test_a_co_manager_leaves_and_lands_on_a_valid_account_page(new_context, arig):
    context, page = _open_account(new_context, arig, "co")
    try:
        row = arig.row(page)
        assert row.get_by_role("link", name="Manage access").count() == 0
        row.get_by_role("link", name="Leave frame").click()
        page.locator(arig.leave + "[open]").wait_for(state="visible")
        _wait_focus_on(page, arig.leave + " a.modal__dismiss")
        page.locator(arig.leave + ' button[type="submit"]').click()
        page.wait_for_url("**/account?flash=*")
        assert page.locator("h1").inner_text() == "Account"
        toast = page.locator('.toast-region--flash .toast[role="status"]')
        toast.wait_for(state="visible")
        assert "You left the frame" in toast.inner_text()
        assert page.locator("li.entity-row", has_text="Kitchen").count() == 0
        assert page.locator(".empty-state__heading").inner_text() == (
            "Your frames will appear here")
        assert arig.members() == []
    finally:
        context.close()


def test_stay_on_this_frame_closes_the_leave_dialog_and_keeps_access(
        new_context, arig):
    context, page = _open_account(new_context, arig, "co")
    try:
        arig.row(page).get_by_role("link", name="Leave frame").click()
        page.locator(arig.leave + "[open]").wait_for(state="visible")
        page.locator(arig.leave + " a.modal__dismiss").click()
        page.wait_for_function("(sel) => !document.querySelector(sel).open", arg=arig.leave)
        assert LONG_CO in arig.members()
    finally:
        context.close()


def test_escape_closes_the_leave_dialog_and_returns_focus_to_its_action(
        new_context, arig):
    context, page = _open_account(new_context, arig, "co")
    try:
        action = arig.row(page).get_by_role("link", name="Leave frame")
        action.click()
        page.locator(arig.leave + "[open]").wait_for(state="visible")
        page.keyboard.press("Escape")
        page.wait_for_function("(sel) => !document.querySelector(sel).open", arg=arig.leave)
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.hasAttribute('data-modal-open')")
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("who", ["owner", "co"])
def test_the_card_and_its_dialog_fit_and_meet_the_tap_targets(
        new_context, arig, who, lang, theme, viewport):
    labels = LABELS[lang]
    context, page = _open_account(
        new_context, arig, who, lang=lang, theme=theme, viewport=viewport)
    try:
        assert _no_sideways_scroll(page)
        row = arig.row(page)
        action = row.locator("a[data-modal-open]")
        assert action.inner_text() == labels["manage" if who == "owner" else "leave"]
        assert action.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL
        assert action.bounding_box()["width"] >= MIN_TAP_PX - SUBPIXEL
        assert row.locator("a.entity-row__title").bounding_box()["height"] > 0
        assert row.locator('.entity-row__dot [role="img"]').count() == 1
        card_box = page.locator('[aria-labelledby="account-frames"]').bounding_box()
        assert card_box["x"] >= -SUBPIXEL
        assert card_box["x"] + card_box["width"] <= viewport["width"] + SUBPIXEL
        action.click()
        dialog = page.locator(arig.access if who == "owner" else arig.leave)
        dialog.wait_for(state="visible")
        box = dialog.bounding_box()
        assert box["x"] >= -SUBPIXEL and box["x"] + box["width"] <= viewport["width"] + SUBPIXEL
        assert dialog.evaluate("d => d.scrollWidth <= d.clientWidth + 1")
        assert _no_sideways_scroll(page)
        selectors = ["a.modal__dismiss", "a.modal__close"]
        selectors += (
            ['form[action$="/co-managers/add"] button[type="submit"]',
             "form.co-manager__remove button"] if who == "owner"
            else ['button[type="submit"]'])
        for selector in selectors:
            target = dialog.locator(selector).first
            assert target.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL, selector
            assert target.bounding_box()["width"] >= MIN_TAP_PX - SUBPIXEL, selector
        if who == "owner" and viewport["width"] == 360:
            long_owner = dialog.locator(".co-manager__email", has_text=LONG_OWNER)
            assert long_owner.bounding_box()["height"] > 30, "the long address wraps"
        if who == "co":
            assert dialog.locator('button[type="submit"]').inner_text() == labels["confirm"]
            assert dialog.locator("a.modal__dismiss").inner_text() == labels["stay"]
    finally:
        context.close()


@pytest.mark.parametrize("who", ["owner", "co"])
def test_a_users_account_carries_no_administrator_vocabulary(new_context, arig, who):
    context, page = _open_account(new_context, arig, who)
    try:
        visible = page.locator("body").inner_text()
        assert not ADMIN_WORDS.search(visible), ADMIN_WORDS.search(visible).group(0)
        nav = page.locator("nav").all_inner_texts()
        assert not ADMIN_WORDS.search(" ".join(nav))
    finally:
        context.close()


def test_the_owner_flow_works_through_hash_links_with_scripts_blocked(
        new_context, arig):
    context, page = _open_account(new_context, arig, "owner", java_script_enabled=False)
    try:
        arig.row(page).locator('a[href="%s"]' % arig.access).click()
        assert page.locator(arig.access).is_visible()
        page.fill(arig.email, INVITED)
        page.locator(arig.access + ' form[action$="/co-managers/add"] button').click()
        page.wait_for_url("**/account?access=*")
        assert INVITED in arig.members()
        assert page.locator(arig.access).is_visible()
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def test_the_leave_flow_works_through_hash_links_with_scripts_blocked(
        new_context, arig):
    context, page = _open_account(new_context, arig, "co", java_script_enabled=False)
    try:
        arig.row(page).locator('a[href="%s"]' % arig.leave).click()
        assert page.locator(arig.leave).is_visible()
        page.locator(arig.leave + ' button[type="submit"]').click()
        page.wait_for_url("**/account?flash=*")
        assert page.locator("li.entity-row", has_text="Kitchen").count() == 0
        assert arig.members() == []
    finally:
        context.close()
