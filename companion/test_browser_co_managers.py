"""Real-browser checks of the Access section on Fleet and the Account
"Shared by" line: the two-action add flow, section geometry and tap targets at
360 and 1280px in both languages and themes, the page returning to the frame after each
change, the same forms with scripts blocked, and Home carrying no co-management."""
import pytest

from co_manager_browser_support import (
    INVITED, LONG_CO, LONG_OWNER, MIN_TAP_PX, SUBPIXEL, UNKNOWN, Rig, _no_sideways_scroll,
    _open)
from companion.test_browser_ux_helpers import UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED
from server import fleet_db

pytestmark = pytest.mark.browser

FLASH = '.toast-region--flash .toast[role="status"]'
LANGS = ("en", "fr")
CONSOLE_TOAST = ".toast"


@pytest.fixture
def rig(app_server_in_process):
    return Rig(app_server_in_process)


_CONTAINMENT_JS = """
(card) => {
  const box = (el) => el.getBoundingClientRect();
  const cardBox = box(card);
  const problems = [];
  if (card.scrollWidth > card.clientWidth + 1) problems.push('card scrolls inside');
  card.querySelectorAll('li.row:has(.co-manager__email)').forEach((row) => {
    const rowBox = box(row);
    if (rowBox.left < cardBox.left - 1 || rowBox.right > cardBox.right + 1) {
      problems.push('row outside card');
    }
    const email = row.querySelector('.co-manager__email');
    const range = document.createRange();
    range.selectNodeContents(email);
    const text = range.getBoundingClientRect();
    const own = box(email);
    // A long address is cut with an ellipsis inside its span, its full value in the title.
    const cut = email.scrollWidth > email.clientWidth + 1;
    const style = getComputedStyle(email);
    if (cut && !(style.textOverflow === 'ellipsis' && style.overflow === 'hidden'
                 && email.title === email.textContent)) {
      problems.push('address text outside its span: ' + email.textContent);
    }
    if (!cut && (text.left < own.left - 1 || text.right > own.right + 1)) {
      problems.push('address text outside its span: ' + email.textContent);
    }
    if (own.right > rowBox.right + 1 || own.left < rowBox.left - 1) {
      problems.push('address span outside its row');
    }
    row.querySelectorAll('button, form').forEach((control) => {
      const b = box(control);
      if (b.right > rowBox.right + 1 || b.left < rowBox.left - 1) {
        problems.push('control outside its row');
      }
    });
  });
  return problems;
}
"""


class FleetRig(Rig):
    """The same fleet seen from Fleet: the owned frame's Access section."""

    def __init__(self, server):
        super().__init__(server)
        self.slug = self.seed.owned_id.lower().replace("_", "-")
        self.section = ".fleet-block--access"
        self.dialog = "#dlg-add-co-manager-%s" % self.slug
        self.person = "%s #co-manager-dialog-%s-person" % (self.dialog, self.slug)
        self.email = "%s #co-manager-dialog-%s-email" % (self.dialog, self.slug)
        self.add_row = self.section + " li.access-add a.row__main"


@pytest.fixture
def frig(app_server_in_process):
    return FleetRig(app_server_in_process)


def _open_fleet(new_context, rig, who="admin", lang="en", theme=None,
                viewport=VIEWPORT_MIN_SUPPORTED, query="", **context_kwargs):
    query = query or "?tab=access&frame=" + rig.seed.owned_id
    return _open(
        new_context, rig, who, path="/fleet" + query, lang=lang, theme=theme,
        viewport=viewport, **context_kwargs)


_ADD_BUTTON = 'form[action$="/co-managers/add"] button[type="submit"]'


def _open_add_dialog(page, frig):
    """One tap on the Add co-manager row opens its dialog."""
    page.locator(frig.add_row).click()
    page.wait_for_function(
        "sel => document.querySelector(sel).open", arg=frig.dialog, timeout=10000)


def test_an_admin_adds_a_co_manager_in_three_actions_through_the_add_row(new_context, frig):
    context, page = _open_fleet(new_context, frig)
    try:
        assert page.locator(frig.section + " select").count() == 0, "no inline picker remains"
        _open_add_dialog(page, frig)  # 1
        page.select_option(frig.person, label=INVITED)  # 2
        page.locator(frig.dialog + " " + _ADD_BUTTON).click()  # 3
        page.wait_for_url("**/fleet?frame=*&tab=access")
        toast = page.locator(CONSOLE_TOAST).first
        toast.wait_for(state="visible")
        assert "Co-manager added" in toast.inner_text()
        assert INVITED in frig.members()
        assert page.locator(
            "section.fleet-block .co-manager__email", has_text=INVITED).count() == 1
    finally:
        context.close()


def test_removing_a_co_manager_updates_the_section(new_context, frig):
    context, page = _open_fleet(new_context, frig)
    try:
        page.locator(frig.section).get_by_role(
            "button", name="Remove %s from this frame" % LONG_CO).click()
        page.wait_for_url("**/fleet?frame=*")
        assert frig.members() == []
        assert page.locator("section.fleet-block .co-manager__email", has_text=LONG_CO).count() == 0
    finally:
        context.close()


def test_a_refused_add_returns_to_the_frame_with_the_error_toast(new_context, frig):
    context, page = _open_fleet(new_context, frig, who="admin", query="?access=" + frig.seed.owned_id)
    try:
        _open_add_dialog(page, frig)
        # The admin picker only offers eligible people, so force an unknown
        # address through the select the way a stale page would.
        page.evaluate(
            "(sel) => { const s = document.querySelector(sel);"
            " const o = document.createElement('option'); o.value = %r;"
            " o.textContent = 'x'; s.appendChild(o); s.value = %r; }"
            % (UNKNOWN, UNKNOWN), frig.person)
        page.locator(frig.dialog + " " + _ADD_BUTTON).click()
        page.wait_for_url("**/fleet?frame=*&tab=access")
        assert "can't be added" in page.locator(CONSOLE_TOAST).first.inner_text()
        assert UNKNOWN not in page.url
        assert UNKNOWN not in frig.members()
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900}])
def test_the_section_fits_and_meets_the_tap_targets(
        new_context, frig, lang, theme, viewport):
    conn = fleet_db.connect(frig.state_dir)
    try:
        fleet_db.add_user(
            conn, "an.invited.person.with.a.very.long.address.x@example.test", "user")
    finally:
        conn.close()
    context, page = _open_fleet(
        new_context, frig, lang=lang, theme=theme, viewport=viewport)
    try:
        section = page.locator(frig.section).first
        box = section.bounding_box()
        assert box["x"] >= -SUBPIXEL and box["x"] + box["width"] <= viewport["width"] + SUBPIXEL
        assert _no_sideways_scroll(page)
        assert section.evaluate(_CONTAINMENT_JS) == []
        owner_email = section.locator(".co-manager__email", has_text=LONG_OWNER)
        if viewport["width"] == 360:
            assert owner_email.bounding_box()["height"] < 30, "the long address is one line"
            assert owner_email.get_attribute("title") == owner_email.inner_text() or (
                LONG_OWNER in owner_email.get_attribute("title"))
        for selector in (
                "li.access-add a.row__main", "a.row-action", "form.co-manager__remove button"):
            target = section.locator(selector).first
            assert target.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL, selector
            assert target.bounding_box()["width"] >= MIN_TAP_PX - SUBPIXEL, selector
        # The owner's row and its Reassign button never overlap: the button stays beside the
        # address on the row's one line, on a narrow screen and on a wide one.
        owner_row = section.locator("li.access-person", has_text=LONG_OWNER).first
        main_box = owner_row.locator(".row__main").bounding_box()
        button_box = owner_row.locator("a.row-action").bounding_box()
        assert button_box["x"] >= main_box["x"] + main_box["width"] - SUBPIXEL
        assert abs(button_box["y"] + button_box["height"] / 2
                   - (main_box["y"] + main_box["height"] / 2)) <= 8
        # The picker lives in the dialog, inside the viewport and with 44px controls.
        _open_add_dialog(page, frig)
        for selector in (frig.person, frig.dialog + " " + _ADD_BUTTON):
            target = page.locator(selector).first
            target_box = target.bounding_box()
            assert target_box["height"] >= MIN_TAP_PX - SUBPIXEL, selector
            assert target_box["x"] >= -SUBPIXEL
            assert target_box["x"] + target_box["width"] <= viewport["width"] + SUBPIXEL, selector
    finally:
        context.close()


def test_the_section_works_with_scripts_blocked(new_context, frig):
    context, page = _open_fleet(new_context, frig, java_script_enabled=False)
    try:
        assert page.locator(frig.add_row).is_visible()
        page.locator(frig.add_row).click()
        page.wait_for_url("**#dlg-add-co-manager-*")
        page.select_option(frig.person, label=INVITED)
        page.locator(frig.dialog + " " + _ADD_BUTTON).click()
        page.wait_for_url("**/fleet?frame=*&tab=access")
        assert INVITED in frig.members()
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def test_home_has_no_co_management_for_an_owner_or_a_co_manager(new_context, frig):
    for who in ("owner", "co"):
        context, page = _open(new_context, frig, who)
        try:
            assert page.get_by_text("Co-managers").count() == 0
            assert page.locator('[aria-labelledby="home-co-managers"]').count() == 0
            assert _no_sideways_scroll(page)
        finally:
            context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_account_shows_the_shared_mark_and_owner_without_overflow(
        new_context, rig, lang):
    context, page = _open(new_context, rig, "co", path="/account", lang=lang)
    try:
        assert _no_sideways_scroll(page)
        owner_line = page.locator(".account-frame__line", has_text=LONG_OWNER)
        assert owner_line.count() == 1 and owner_line.is_visible()
        assert owner_line.evaluate(
            "e => { const r = document.createRange(); r.selectNodeContents(e);"
            " const t = r.getBoundingClientRect(), b = e.getBoundingClientRect();"
            " return t.right <= b.right + 1 && b.right <= document.documentElement.clientWidth; }")
        assert owner_line.inner_text().startswith(
            "Shared by" if lang == "en" else "Partagé par")
    finally:
        context.close()


# --- lists without a desktop table stay visible at every width -------------

LIST_WIDTHS = (1000, 700, 360)
FRAMES_LIST = '[aria-labelledby="account-frames"] ul.group'


@pytest.mark.parametrize("width", LIST_WIDTHS)
def test_the_account_frames_list_is_visible_at_every_width(new_context, rig, width):
    context, page = _open(
        new_context, rig, "owner", path="/account",
        viewport={"width": width, "height": 900})
    try:
        assert page.locator(FRAMES_LIST).is_visible()
        assert page.locator(FRAMES_LIST + " li.account-frame", has_text="Kitchen").is_visible()
    finally:
        context.close()


def test_a_co_manager_sees_the_shared_frame_row_on_desktop(new_context, rig):
    context, page = _open(
        new_context, rig, "co", path="/account",
        viewport={"width": 1000, "height": 900})
    try:
        assert page.locator(FRAMES_LIST).is_visible()
        row = page.locator(FRAMES_LIST + " li.account-frame", has_text="Kitchen")
        assert row.is_visible()
        assert row.get_by_text("Shared by", exact=False).is_visible()
    finally:
        context.close()


