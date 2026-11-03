"""Real-browser checks of the Manage access dialog on Fleet and the Account
"Shared" mark: the four-action add flow, dialog geometry and tap targets at
360 and 1280px in both languages and themes, the dialog reopening after each
change, the same forms through plain hash links with scripts blocked, and
Home carrying no co-management."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_MIN_SUPPORTED, _set_ui_theme)
from server import fleet_db

pytestmark = pytest.mark.browser

MIN_TAP_PX = 44
SUBPIXEL = 1.0

LONG_OWNER = "owner.with.a.very.long.address.x@example.test"
LONG_CO = "co.manager.with.a.very.long.address@example.test"
INVITED = "invited.person@example.test"
UNKNOWN = "nobody.knows.me@example.test"
SECOND_CO = "second.co@example.test"

FLASH = '.toast-region--flash .toast[role="status"]'
LANGS = ("en", "fr")
CONSOLE_TOAST = ".toast"


class Rig:
    """A seeded fleet whose Orly-less "Kitchen" frame is owned by a user with a
    long address and co-managed by another one."""

    def __init__(self, server):
        self.server = server
        self.state_dir = server.state_dir
        self.seed = fx.seed_fleet(self.state_dir)
        conn = fleet_db.connect(self.state_dir)
        try:
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (LONG_OWNER, self.seed.owner_id))
            conn.commit()
            self.co_id = fleet_db.add_user(conn, LONG_CO, "user")
            fleet_db.add_co_manager(conn, self.seed.owned_id, self.co_id, None)
            fleet_db.add_user(conn, INVITED, "user")
        finally:
            conn.close()
        self.path = "/devices/%s/" % self.seed.owned_id

    def url(self, path=None):
        return self.server.base_url() + (path or self.path)

    def cookie(self, who):
        email = {"owner": LONG_OWNER, "co": LONG_CO}.get(who)
        if who == "admin":
            pair = fx.admin_cookie(self.state_dir)
        else:
            pair = fx.user_cookie(self.state_dir, email=email)
        name, value = pair.split("=", 1)
        return {"name": name, "value": value, "url": self.server.base_url(),
                "httpOnly": True, "sameSite": "Strict"}

    def members(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return sorted(
                row["email"] for row in conn.execute(
                    "SELECT u.email FROM device_co_managers c JOIN users u "
                    "ON u.id = c.user_id WHERE c.device_id = ?",
                    (self.seed.owned_id,)))
        finally:
            conn.close()


@pytest.fixture
def rig(app_server_in_process):
    return Rig(app_server_in_process)


def _open(new_context, rig, who, path=None, lang="en", theme=None,
          viewport=VIEWPORT_MIN_SUPPORTED, **context_kwargs):
    context = new_context(viewport=viewport, **context_kwargs)
    context.add_cookies([
        rig.cookie(who),
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": rig.server.base_url()}])
    page = context.new_page()
    page.goto(rig.url(path))
    page.locator("main").wait_for(state="visible")
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _no_sideways_scroll(page):
    return page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth")


_CONTAINMENT_JS = """
(card) => {
  const box = (el) => el.getBoundingClientRect();
  const cardBox = box(card);
  const problems = [];
  if (card.scrollWidth > card.clientWidth + 1) problems.push('card scrolls inside');
  card.querySelectorAll('li.data-card').forEach((row) => {
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
    """The same fleet seen from Fleet: the owned frame's dialog."""

    def __init__(self, server):
        super().__init__(server)
        self.slug = self.seed.owned_id.lower().replace("_", "-")
        self.dialog = "#dlg-access-" + self.slug
        self.person = "#co-manager-%s-person" % self.slug
        self.email = "#co-manager-%s-email" % self.slug


@pytest.fixture
def frig(app_server_in_process):
    return FleetRig(app_server_in_process)


def _open_fleet(new_context, rig, who="admin", lang="en", theme=None,
                viewport=VIEWPORT_MIN_SUPPORTED, query="", **context_kwargs):
    return _open(
        new_context, rig, who, path="/fleet" + query, lang=lang, theme=theme,
        viewport=viewport, **context_kwargs)


def _open_dialog(page, rig):
    """Two actions: the frame's row menu, then its Manage access item."""
    row = page.locator("li.entity-row", has_text="Kitchen")
    row.locator("summary.row-menu__toggle").click()
    row.locator("a.row-menu__item", has_text=_MANAGE_LABEL[page.evaluate(
        "document.documentElement.lang")]).click()
    page.locator(rig.dialog + "[open]").wait_for(state="visible")


_MANAGE_LABEL = {"en": "Manage access", "fr": "Gérer l"}


def test_an_admin_adds_a_co_manager_in_four_actions_and_the_dialog_reopens(
        new_context, frig):
    context, page = _open_fleet(new_context, frig)
    try:
        _open_dialog(page, frig)  # actions 1 and 2
        page.select_option(frig.person, label=INVITED)  # 3
        page.locator(frig.dialog + ' form[action$="/co-managers/add"] button').click()  # 4
        page.wait_for_url("**/fleet?access=*")
        page.locator(frig.dialog + "[open]").wait_for(state="visible")
        assert INVITED in frig.members()
        assert page.locator(
            frig.dialog + " li.data-card", has_text=INVITED).count() == 1
        toast = page.locator(CONSOLE_TOAST).first
        toast.wait_for(state="visible")
        assert "Co-manager added" in toast.inner_text()
    finally:
        context.close()


def test_removing_works_and_done_closes_the_dialog(new_context, frig):
    context, page = _open_fleet(new_context, frig)
    try:
        _open_dialog(page, frig)
        page.get_by_role(
            "button", name="Remove %s from this frame" % LONG_CO).click()
        page.wait_for_url("**/fleet?access=*")
        page.locator(frig.dialog + "[open]").wait_for(state="visible")
        assert frig.members() == []
        assert page.locator(frig.dialog + " li.data-card", has_text=LONG_CO).count() == 0
        page.locator(frig.dialog + " a.modal__dismiss").click()
        assert not page.locator(frig.dialog).evaluate("d => d.open")
    finally:
        context.close()


def test_a_refused_add_reopens_the_dialog_with_the_error_toast(new_context, frig):
    context, page = _open_fleet(new_context, frig, who="admin", query="?access=" + frig.seed.owned_id)
    try:
        page.locator(frig.dialog + "[open]").wait_for(state="visible")
        # The admin picker only offers eligible people, so force an unknown
        # address through the select the way a stale page would.
        page.evaluate(
            "(sel) => { const s = document.querySelector(sel);"
            " const o = document.createElement('option'); o.value = %r;"
            " o.textContent = 'x'; s.appendChild(o); s.value = %r; }"
            % (UNKNOWN, UNKNOWN), frig.person)
        page.locator(frig.dialog + ' form[action$="/co-managers/add"] button').click()
        page.wait_for_url("**/fleet?access=*")
        page.locator(frig.dialog + "[open]").wait_for(state="visible")
        assert "can't be added" in page.locator(CONSOLE_TOAST).first.inner_text()
        assert UNKNOWN not in page.url
        assert UNKNOWN not in frig.members()
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900}])
def test_the_dialog_fits_and_meets_the_tap_targets(
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
        _open_dialog(page, frig)
        dialog = page.locator(frig.dialog)
        box = dialog.bounding_box()
        assert box["x"] >= -SUBPIXEL and box["x"] + box["width"] <= viewport["width"] + SUBPIXEL
        assert dialog.evaluate("d => d.scrollWidth <= d.clientWidth + 1")
        assert _no_sideways_scroll(page)
        assert dialog.evaluate(_CONTAINMENT_JS) == []
        owner_email = dialog.locator(".co-manager__email", has_text=LONG_OWNER)
        if viewport["width"] == 360:
            assert owner_email.bounding_box()["height"] > 30, "the long address wraps"
        for selector in (
                frig.person, 'form[action$="/co-managers/add"] button[type="submit"]',
                "form.co-manager__remove button", "a.modal__dismiss", "a.modal__close"):
            target = dialog.locator(selector).first
            assert target.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL, selector
            assert target.bounding_box()["width"] >= MIN_TAP_PX - SUBPIXEL, selector
    finally:
        context.close()


def test_the_dialog_works_through_hash_links_with_scripts_blocked(
        new_context, frig):
    context, page = _open_fleet(new_context, frig, java_script_enabled=False)
    try:
        page.locator("li.entity-row", has_text="Kitchen").locator(
            "summary.row-menu__toggle").click()
        page.locator(
            'a.row-menu__item[href="%s"]' % ("#dlg-access-" + frig.slug)).click()
        assert page.locator(frig.dialog).is_visible()
        page.select_option(frig.person, label=INVITED)
        page.locator(frig.dialog + ' form[action$="/co-managers/add"] button').click()
        page.wait_for_url("**/fleet?access=*")
        assert INVITED in frig.members()
        assert page.locator(frig.dialog).is_visible()
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
        assert page.get_by_text(LONG_OWNER).count() == 1
        owner_line = page.locator(".co-manager__email", has_text=LONG_OWNER)
        assert owner_line.is_visible()
        assert owner_line.evaluate(
            "e => { const r = document.createRange(); r.selectNodeContents(e);"
            " const t = r.getBoundingClientRect(), b = e.getBoundingClientRect();"
            " return t.right <= b.right + 1 && b.right <= document.documentElement.clientWidth; }")
        if lang == "en":
            assert page.get_by_text("Shared", exact=True).count() >= 1
    finally:
        context.close()


# --- lists without a desktop table stay visible at every width -------------

LIST_WIDTHS = (1000, 700, 360)
FRAMES_LIST = '[aria-labelledby="account-frames"] ul.data-cards'


@pytest.mark.parametrize("width", LIST_WIDTHS)
def test_the_account_frames_list_is_visible_at_every_width(new_context, rig, width):
    context, page = _open(
        new_context, rig, "owner", path="/account",
        viewport={"width": width, "height": 900})
    try:
        assert page.locator(FRAMES_LIST).is_visible()
        assert page.locator(FRAMES_LIST + " li.data-card", has_text="Kitchen").is_visible()
    finally:
        context.close()


def test_a_co_manager_sees_the_shared_frame_row_on_desktop(new_context, rig):
    context, page = _open(
        new_context, rig, "co", path="/account",
        viewport={"width": 1000, "height": 900})
    try:
        assert page.locator(FRAMES_LIST).is_visible()
        row = page.locator(FRAMES_LIST + " li.data-card", has_text="Kitchen")
        assert row.is_visible()
        assert row.get_by_text("Shared", exact=True).is_visible()
    finally:
        context.close()


