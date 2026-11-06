"""Real-browser checks of the Manage access sheet on a phone (opened from
Account), the small drawn frame picture in the frame popover and the Account
rows, and the Owner / Co-manager marks of the Account page."""
import pytest

from co_manager_browser_support import (
    INVITED, LONG_CO, MIN_TAP_PX, SUBPIXEL, Rig, _no_sideways_scroll, _open)
from companion.test_browser_ux_helpers import _SETTLE_PROBE, UI_THEMES_EXPLICIT

pytestmark = pytest.mark.browser

LANGS = ("en", "fr")
PHONES = ({"width": 390, "height": 844}, {"width": 360, "height": 640})
ACCESS_TITLE = {"en": "Manage access", "fr": "Gérer l’accès"}


class SheetRig(Rig):
    def __init__(self, server):
        super().__init__(server)
        slug = self.seed.owned_id.lower().replace("_", "-")
        self.dialog = "#dlg-access-" + slug
        self.opener = 'a[href="%s"]' % self.dialog


@pytest.fixture
def srig(app_server_in_process):
    return SheetRig(app_server_in_process)


def _open_sheet(new_context, rig, lang, theme, viewport):
    context, page = _open(
        new_context, rig, "owner", path="/account", lang=lang, theme=theme, viewport=viewport)
    page.wait_for_function("document.readyState === 'complete'")
    page.locator(rig.opener).click()
    page.locator(rig.dialog + "[open]").wait_for(state="visible")
    page.evaluate(_SETTLE_PROBE, rig.dialog + " .modal__title")
    return context, page


_SHEET_JS = """
(sel) => {
  const d = document.querySelector(sel);
  const box = d.getBoundingClientRect();
  const title = d.querySelector('.modal__title').getBoundingClientRect();
  const radius = parseFloat(getComputedStyle(d).borderTopLeftRadius);
  const problems = [];
  if (title.top < box.top + radius - 0.5) problems.push('title under the rounded edge');
  if (box.top < 0 || box.bottom > innerHeight + 0.5) problems.push('sheet outside the viewport');
  if (box.left < -0.5 || box.right > innerWidth + 0.5) problems.push('sheet outside sideways');
  if (d.scrollWidth > d.clientWidth + 1) problems.push('sheet scrolls sideways');
  d.querySelectorAll('.modal__body *').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width && (r.left < box.left - 1 || r.right > box.right + 1)) {
      problems.push('overflows sideways: ' + el.className);
    }
  });
  const controls = [
    '.modal__close', '.co-manager__remove-btn', '.row__form input[type=email]',
    '.row__form button[type=submit]', '.modal__dismiss'];
  controls.forEach((c) => {
    const el = d.querySelector(c);
    el.scrollIntoView({block: 'nearest'});
    const r = el.getBoundingClientRect();
    if (r.height < 43 || r.width < 43) problems.push('small target: ' + c);
    if (r.top < box.top - 1 || r.bottom > box.bottom + 1 || r.bottom > innerHeight + 1) {
      problems.push('not reachable: ' + c);
    }
  });
  return problems;
}
"""


@pytest.mark.parametrize("viewport", PHONES, ids=("390x844", "360x640"))
@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_access_sheet_clears_its_corners_fits_and_keeps_every_control_reachable(
        new_context, srig, viewport, lang, theme):
    context, page = _open_sheet(new_context, srig, lang, theme, viewport)
    try:
        assert page.locator(srig.dialog + " .modal__title").inner_text() == ACCESS_TITLE[lang]
        assert page.evaluate(_SHEET_JS, srig.dialog) == []
        assert _no_sideways_scroll(page)
        # One surface: the sheet holds a single group and no card inside it.
        assert page.locator(srig.dialog + " ul.group").count() == 1
        assert page.locator(srig.dialog + " .data-card").count() == 0
        # Remove is a quiet text button in the danger colour.
        remove = page.locator(srig.dialog + " .co-manager__remove-btn")
        assert remove.evaluate(
            "b => { const s = getComputedStyle(b); return s.borderTopWidth === '0px' &&"
            " s.backgroundColor === 'rgba(0, 0, 0, 0)'; }")
        assert remove.bounding_box()["height"] >= MIN_TAP_PX - SUBPIXEL
        # Done closes the sheet and focus goes back to the link that opened it.
        page.locator(srig.dialog + " a.modal__dismiss").click()
        page.wait_for_function("(s) => !document.querySelector(s).open", arg=srig.dialog)
        page.wait_for_function(
            "(s) => document.activeElement === document.querySelector(s)", arg=srig.opener)
    finally:
        context.close()


@pytest.mark.parametrize("viewport,lang,theme", [
    (PHONES[0], "en", "light"), (PHONES[1], "fr", "dark")], ids=("390-en", "360-fr"))
def test_adding_and_removing_a_co_manager_work_in_the_sheet_and_focus_returns(
        new_context, srig, viewport, lang, theme):
    context, page = _open_sheet(new_context, srig, lang, theme, viewport)
    try:
        page.fill(srig.dialog + " input[type=email]", INVITED)
        page.locator(srig.dialog + " .row__form button[type=submit]").click()
        page.wait_for_url("**/account?access=*")
        page.locator(srig.dialog + "[open]").wait_for(state="visible")
        assert INVITED in srig.members()
        assert page.locator(srig.dialog + " .co-manager__email", has_text=INVITED).count() == 1
        page.locator(srig.dialog + " .co-manager__remove-btn").first.click()
        page.wait_for_url("**/account?access=*")
        page.locator(srig.dialog + "[open]").wait_for(state="visible")
        assert LONG_CO not in srig.members() and INVITED in srig.members()
        assert page.locator(srig.dialog + " .co-manager__email", has_text=LONG_CO).count() == 0
        page.locator(srig.dialog + " a.modal__dismiss").click()
        page.wait_for_function("(s) => !document.querySelector(s).open", arg=srig.dialog)
    finally:
        context.close()


_PIC_JS = """
(sel) => {
  const el = document.querySelector(sel);
  const r = {width: el.offsetWidth, height: el.offsetHeight};
  const s = getComputedStyle(el);
  return {ratio: r.width / r.height, w: r.width, h: r.height,
          radius: parseFloat(s.borderTopLeftRadius),
          bezel: parseFloat(s.paddingLeft) + parseFloat(s.borderLeftWidth),
          screen: getComputedStyle(el.firstElementChild).backgroundColor};
}
"""


@pytest.mark.parametrize("width", (360, 390, 1440))
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_drawn_frame_is_a_small_portrait_frame_in_the_popover_and_on_account(
        new_context, srig, width, theme):
    viewport = {"width": width, "height": 844}
    context, page = _open(
        new_context, srig, "owner", path="/devices/%s/" % srig.seed.owned_id, theme=theme,
        viewport=viewport)
    try:
        page.locator("summary.frame-menu__button").click()
        page.locator(".frame-row__pic").first.wait_for(state="visible")
        pics = {"popover": page.evaluate(_PIC_JS, ".frame-row__pic")}
        page.goto(srig.url("/account"))
        page.locator(".account-frame__pic").first.wait_for(state="visible")
        pics["account"] = page.evaluate(_PIC_JS, ".account-frame__pic")
        for where, pic in pics.items():
            assert 0.65 <= pic["ratio"] <= 0.8, (where, pic)
            assert pic["radius"] <= 8, (where, pic)
            assert 2 <= pic["bezel"] <= 6, (where, pic)
            assert pic["h"] <= 56 and pic["w"] >= 24, (where, pic)
    finally:
        context.close()


@pytest.mark.parametrize("lang,owner_mark,co_mark,co_line", [
    ("en", "Owner", "Co-manager", "Co-manager of 1 frame"),
    ("fr", "Propriétaire", "Co-gestionnaire", "Co-gestionnaire de 1 cadre")])
def test_account_marks_each_frame_owner_or_co_manager_without_overflow(
        new_context, srig, lang, owner_mark, co_mark, co_line):
    for who, mark, line in (("co", co_mark, co_line), ("owner", owner_mark, None)):
        context, page = _open(new_context, srig, who, path="/account", lang=lang)
        try:
            row = page.locator("li.account-frame", has_text="Kitchen")
            assert row.locator(".account-frame__role").inner_text() == mark
            role = page.locator(
                '[aria-labelledby="account-identity"] li.row',
                has_text="Role" if lang == "en" else "Rôle")
            if line:
                assert line in role.inner_text()
            else:
                assert "Co-manager" not in role.inner_text()
                assert "Co-gestionnaire" not in role.inner_text()
            assert _no_sideways_scroll(page)
        finally:
            context.close()
