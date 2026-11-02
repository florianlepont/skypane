"""Real-browser checks of the Co-managers card on a frame's Home page and the
Account "Shared" mark: layout, tap targets and wrapping at the smallest phone
width in both languages and themes, the native Leave confirmation with scripts
blocked, the add, remove and leave flows, and the card surviving a live Home
refresh."""
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

CARD = 'section[aria-labelledby="home-co-managers"]'
FLASH = '.toast-region--flash .toast[role="status"]'
FLASH_ANY = ".toast-region--flash .toast"
LANGS = ("en", "fr")


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


def _height(page, selector):
    return page.locator(selector).first.bounding_box()["height"]


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


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_card_stays_inside_the_page_with_long_addresses(
        new_context, rig, lang, theme):
    context, page = _open(new_context, rig, "owner", lang=lang, theme=theme)
    try:
        assert page.evaluate("document.documentElement.scrollWidth") == 360
        assert _no_sideways_scroll(page)
        card = page.locator(CARD)
        assert card.is_visible()
        assert card.evaluate(_CONTAINMENT_JS) == []
        owner_email = page.locator(CARD + " .co-manager__email", has_text=LONG_OWNER)
        assert owner_email.bounding_box()["height"] > 30, "the long address wraps"
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_add_and_remove_controls_meet_the_tap_target_and_stack(
        new_context, rig, lang):
    context, page = _open(new_context, rig, "owner", lang=lang)
    try:
        field = CARD + " #co-manager-email"
        submit = CARD + ' form[action$="/co-managers/add"] button[type="submit"]'
        assert page.locator(field).is_visible() and page.locator(submit).is_visible()
        assert _height(page, field) >= MIN_TAP_PX
        assert _height(page, submit) >= MIN_TAP_PX
        field_box = page.locator(field).bounding_box()
        submit_box = page.locator(submit).bounding_box()
        assert submit_box["y"] >= field_box["y"] + field_box["height"] - SUBPIXEL
        remove = page.locator(CARD + " form.co-manager__remove").first
        who = page.locator(CARD + " .co-manager__who").nth(1)
        assert remove.bounding_box()["y"] >= (
            who.bounding_box()["y"] + who.bounding_box()["height"] - SUBPIXEL)
        gap = remove.bounding_box()["y"] - (
            who.bounding_box()["y"] + who.bounding_box()["height"])
        token = page.evaluate(
            "parseFloat(getComputedStyle(document.documentElement)"
            ".getPropertyValue('--space-sm'))")
        assert abs(gap - token) <= SUBPIXEL
        if lang == "en":
            assert page.get_by_role(
                "button", name="Remove %s from this frame" % LONG_CO).count() == 1
        assert _no_sideways_scroll(page)
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_a_co_manager_sees_a_read_only_card_with_a_native_leave(
        new_context, rig, lang):
    context, page = _open(new_context, rig, "co", lang=lang)
    try:
        assert page.locator(CARD + ' form[action$="/co-managers/add"]').count() == 0
        assert page.locator(CARD + " form.co-manager__remove").count() == 0
        you_row = page.locator(CARD + " li.data-card", has_text=LONG_CO)
        assert you_row.locator(".banner__pill").count() == 1
        if lang == "en":
            assert you_row.locator(".banner__pill").text_content() == "You"
        details = page.locator(CARD + " details.fleet-confirm")
        summary = details.locator("summary")
        assert details.get_attribute("open") is None
        assert summary.bounding_box()["height"] >= MIN_TAP_PX
        summary.click()
        assert details.get_attribute("open") is not None
        submit = details.locator('button[type="submit"]')
        keep = details.locator("a.text-link")
        assert submit.is_visible() and keep.is_visible()
        assert submit.bounding_box()["height"] >= MIN_TAP_PX
        assert details.locator("p.text-body").is_visible()
        # Document order is visual order: the consequence, Leave, then Stay.
        assert details.evaluate(
            "d => { const p = d.querySelector('p'), b = d.querySelector('button'),"
            " a = d.querySelector('a');"
            " const f = Node.DOCUMENT_POSITION_FOLLOWING;"
            " return !!(p.compareDocumentPosition(b) & f) && !!(b.compareDocumentPosition(a) & f); }")
        boxes = [e.bounding_box() for e in (
            details.locator("p.text-body"), submit, keep)]
        assert boxes[0]["y"] <= boxes[1]["y"] <= boxes[2]["y"] + MIN_TAP_PX
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def test_an_admin_sees_the_select_without_widening_the_page(new_context, rig):
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.add_user(
            conn, "an.invited.person.with.a.very.long.address.x@example.test", "user")
    finally:
        conn.close()
    context, page = _open(new_context, rig, "admin")
    try:
        select = page.locator(CARD + " select#co-manager-person")
        assert select.is_visible()
        assert select.bounding_box()["height"] >= MIN_TAP_PX
        box = select.bounding_box()
        assert box["x"] >= 0 and box["x"] + box["width"] <= 360 + SUBPIXEL
        assert _no_sideways_scroll(page)
        assert page.locator(CARD).evaluate(_CONTAINMENT_JS) == []
    finally:
        context.close()


def test_the_card_works_with_scripts_blocked(new_context, rig):
    context, page = _open(
        new_context, rig, "co", java_script_enabled=False)
    try:
        details = page.locator(CARD + " details.fleet-confirm")
        assert details.count() == 1
        details.locator("summary").click()
        assert details.get_attribute("open") is not None
        assert details.locator('button[type="submit"]').is_visible()
        page.locator("main").wait_for(state="visible")
        # Leaving still works with no script at all.
        details.locator('button[type="submit"]').click()
        page.wait_for_url("**/account**")
        assert page.locator(FLASH).count() == 1
    finally:
        context.close()


def test_the_owner_forms_are_present_with_scripts_blocked(new_context, rig):
    context, page = _open(
        new_context, rig, "owner", java_script_enabled=False)
    try:
        assert page.locator(CARD + ' form[action$="/co-managers/add"]').count() == 1
        assert page.locator(CARD + ' form[action$="/co-managers/remove"]').count() == 1
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


# --- flows -----------------------------------------------------------------


def test_leaving_lands_on_account_with_the_toast_and_the_frame_gone(
        new_context, rig):
    context, page = _open(new_context, rig, "co")
    try:
        page.locator(CARD + " details.fleet-confirm summary").click()
        page.locator(CARD + ' details.fleet-confirm button[type="submit"]').click()
        page.wait_for_url("**/account**")
        toast = page.locator(FLASH)
        toast.wait_for(state="visible")
        assert "You left the frame" in toast.inner_text()
        assert page.get_by_text("Kitchen").count() == 0
        assert LONG_CO not in rig.members()
        response = page.goto(rig.url())
        assert response.status == 404
    finally:
        context.close()


def test_staying_keeps_the_user_on_the_frame_and_the_membership(
        new_context, rig):
    context, page = _open(new_context, rig, "co")
    try:
        page.locator(CARD + " details.fleet-confirm summary").click()
        page.locator(CARD + " details.fleet-confirm a.text-link").click()
        page.wait_for_load_state()
        assert "/account" not in page.url
        assert page.locator(CARD).is_visible()
        assert LONG_CO in rig.members()
    finally:
        context.close()


def test_the_owner_adds_an_invited_address_and_a_refusal_leaves_no_trace(
        new_context, rig):
    context, page = _open(new_context, rig, "owner")
    try:
        page.locator(CARD + " #co-manager-email").fill(INVITED)
        page.locator(CARD + ' form[action$="/co-managers/add"] button').click()
        page.locator(FLASH).wait_for(state="visible")
        assert "Co-manager added" in page.locator(FLASH).inner_text()
        assert page.locator(CARD + " li.data-card", has_text=INVITED).count() == 1
        assert INVITED in rig.members()

        page.locator(CARD + " #co-manager-email").fill(UNKNOWN)
        page.locator(CARD + ' form[action$="/co-managers/add"] button').click()
        page.locator(FLASH_ANY).wait_for(state="visible")
        assert page.locator(FLASH_ANY).count() == 1
        assert "can't be added" in page.locator(FLASH_ANY).inner_text()
        assert page.locator(CARD + " #co-manager-email").input_value() == ""
        assert UNKNOWN not in page.url
        assert UNKNOWN not in page.content()
        assert UNKNOWN not in rig.members()
    finally:
        context.close()


def test_the_owner_removes_a_co_manager(new_context, rig):
    context, page = _open(new_context, rig, "owner")
    try:
        page.get_by_role(
            "button", name="Remove %s from this frame" % LONG_CO).click()
        page.locator(FLASH).wait_for(state="visible")
        assert "Co-manager removed" in page.locator(FLASH).inner_text()
        assert page.locator(CARD + " li.data-card", has_text=LONG_CO).count() == 0
        assert rig.members() == []
    finally:
        context.close()


# --- live refresh ----------------------------------------------------------

_MARKER = '<p id="refresh-marker">refreshed</p>'
_REFRESH_TICK_MS = 65000


def _rewrite_refresh(page):
    """Answer the page's own freshness fetches with the real document plus a
    marker inside `.home-facts`, so the swap has a region that really changes."""
    def handler(route):
        request = route.request
        if request.headers.get("x-requested-with") != "freshness":
            route.continue_()
            return
        headers = {k: v for k, v in request.headers.items() if k != "if-none-match"}
        response = route.fetch(headers=headers)
        body = response.text().replace(
            '<div class="home-facts">', '<div class="home-facts">' + _MARKER, 1)
        route.fulfill(response=response, body=body)
    page.route("**/devices/**", handler)


def test_a_home_refresh_leaves_the_card_and_its_typed_text_alone(
        new_context, rig):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([rig.cookie("owner")])
    page = context.new_page()
    try:
        _rewrite_refresh(page)
        page.clock.install()
        page.goto(rig.url())
        page.locator(CARD).wait_for(state="visible")
        field = page.locator(CARD + " #co-manager-email")
        field.fill("half.typed@exam")
        page.locator(CARD).evaluate("el => { el.dataset.sentinel = 'same-node'; }")
        # A focused field makes the refresh stand down, so move on first.
        page.evaluate("document.activeElement && document.activeElement.blur()")
        assert page.locator("#refresh-marker").count() == 0
        page.clock.run_for(_REFRESH_TICK_MS)
        page.locator("#refresh-marker").wait_for(state="attached")
        assert page.locator(CARD).get_attribute("data-sentinel") == "same-node"
        assert field.input_value() == "half.typed@exam"
    finally:
        context.close()


def test_a_home_refresh_keeps_an_open_leave_confirmation_open(
        new_context, rig):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([rig.cookie("co")])
    page = context.new_page()
    try:
        _rewrite_refresh(page)
        page.clock.install()
        page.goto(rig.url())
        details = page.locator(CARD + " details.fleet-confirm")
        details.locator("summary").click()
        page.evaluate("document.activeElement && document.activeElement.blur()")
        page.locator(CARD).evaluate("el => { el.dataset.sentinel = 'same-node'; }")
        page.clock.run_for(_REFRESH_TICK_MS)
        page.locator("#refresh-marker").wait_for(state="attached")
        assert page.locator(CARD).get_attribute("data-sentinel") == "same-node"
        assert details.get_attribute("open") is not None
    finally:
        context.close()
