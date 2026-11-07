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
    if (text.left < own.left - 1 || text.right > own.right + 1) {
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
        self.person = "#access-inline-%s-person" % self.slug
        self.email = "#access-inline-%s-email" % self.slug


@pytest.fixture
def frig(app_server_in_process):
    return FleetRig(app_server_in_process)


def _open_fleet(new_context, rig, who="admin", lang="en", theme=None,
                viewport=VIEWPORT_MIN_SUPPORTED, query="", **context_kwargs):
    query = query or "?tab=access&frame=" + rig.seed.owned_id
    return _open(
        new_context, rig, who, path="/fleet" + query, lang=lang, theme=theme,
        viewport=viewport, **context_kwargs)


_ADD_BUTTON = 'form[action$="/co-managers/add"] button'


def test_an_admin_adds_a_co_manager_in_two_actions_inline(new_context, frig):
    context, page = _open_fleet(new_context, frig)
    try:
        page.select_option(frig.person, label=INVITED)  # 1
        assert page.locator("dialog[open]").count() == 0
        page.locator(frig.section + " " + _ADD_BUTTON).click()  # 2
        page.wait_for_url("**/fleet?frame=*")
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
        page.locator(frig.section + " " + _ADD_BUTTON).wait_for(state="visible")
        # The admin picker only offers eligible people, so force an unknown
        # address through the select the way a stale page would.
        page.evaluate(
            "(sel) => { const s = document.querySelector(sel);"
            " const o = document.createElement('option'); o.value = %r;"
            " o.textContent = 'x'; s.appendChild(o); s.value = %r; }"
            % (UNKNOWN, UNKNOWN), frig.person)
        page.locator(frig.section + " " + _ADD_BUTTON).click()
        page.wait_for_url("**/fleet?frame=*")
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
            assert owner_email.bounding_box()["height"] > 30, "the long address wraps"
        for selector in (
                frig.person, 'form[action$="/co-managers/add"] button[type="submit"]',
                "form.co-manager__remove button"):
            target = section.locator(selector).first
            assert target.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL, selector
            assert target.bounding_box()["width"] >= MIN_TAP_PX - SUBPIXEL, selector
    finally:
        context.close()


def test_the_section_works_with_scripts_blocked(new_context, frig):
    context, page = _open_fleet(new_context, frig, java_script_enabled=False)
    try:
        assert page.locator(frig.section + " " + _ADD_BUTTON).is_visible()
        page.select_option(frig.person, label=INVITED)
        page.locator(frig.section + " " + _ADD_BUTTON).click()
        page.wait_for_url("**/fleet?frame=*")
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


