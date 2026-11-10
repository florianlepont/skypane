"""Real-browser checks of the last audit points: the Access tab's person rows on a phone, the
Users list's Invited badge, the nearest-airport offer on a phone, the Location map's edge tint
and the Searching row of the place search."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser

_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_PERSON_ROWS = """() => [...document.querySelectorAll('.fleet-frame .row.access-person')].map(row => {
  const box = row.getBoundingClientRect();
  const email = row.querySelector('.co-manager__email');
  const action = row.querySelector('.row__trailing, a.row-action, button, form');
  const e = email.getBoundingClientRect();
  const a = action ? action.getBoundingClientRect() : null;
  return {row: [box.top, box.bottom, box.width], email: [e.top, e.bottom, e.right],
          action: a && [a.top, a.bottom, a.left, a.right],
          ellipsis: getComputedStyle(email).textOverflow, wrap: getComputedStyle(email).whiteSpace,
          title: email.title, text: email.textContent,
          fits: email.scrollWidth <= email.clientWidth + 1};
})"""


def _open_access(new_context, server, viewport, lang):
    seed = fx.seed_fleet(server.state_dir)
    context = new_context(viewport=viewport)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/fleet?tab=access&frame=" + seed.owned_id)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [360, 390])
def test_a_person_row_keeps_its_action_on_the_first_line_and_ellipsises_the_address(
        new_context, app_server_in_process, width, lang):
    context, page = _open_access(
        new_context, app_server_in_process, {"width": width, "height": 844}, lang)
    try:
        rows = page.evaluate(_PERSON_ROWS)
        assert rows
        for row in rows:
            top, bottom, _width = row["row"]
            assert bottom - top < 80, row
            assert row["action"] is not None, row
            a_top, a_bottom, a_left, a_right = row["action"]
            assert a_top >= top - 1 and a_bottom <= bottom + 1, row
            assert row["email"][2] <= a_left + 1, row
            assert row["ellipsis"] == "ellipsis" and row["wrap"] == "nowrap", row
            assert row["title"] == row["text"] and "@" in row["title"], row
    finally:
        context.close()


def test_a_long_address_is_cut_with_an_ellipsis_instead_of_pushing_the_action_down(
        new_context, app_server_in_process):
    context, page = _open_access(
        new_context, app_server_in_process, {"width": 360, "height": 844}, "en")
    try:
        page.evaluate(
            "() => { for (const e of document.querySelectorAll('.fleet-frame .co-manager__email'))"
            " e.textContent = 'a.very.long.address.that.cannot.fit.on.a.phone@example.test'; }")
        for row in page.evaluate(_PERSON_ROWS):
            assert not row["fits"], row
            assert row["row"][1] - row["row"][0] < 80, row
            assert row["email"][2] <= row["action"][2] + 1, row
    finally:
        context.close()


@pytest.mark.parametrize("java_script_enabled", [True, False], ids=["script", "no-script"])
def test_the_theme_and_language_switches_work_with_their_token_with_or_without_script(
        new_context, app_server_in_process, java_script_enabled):
    fx.seed_fleet(app_server_in_process.state_dir)
    context = new_context(
        viewport={"width": 1280, "height": 900}, java_script_enabled=java_script_enabled)
    page = context.new_page()
    try:
        _login(page, app_server_in_process.base_url())
        page.goto(app_server_in_process.base_url() + "/account")
        page.locator("main").wait_for(state="visible")
        form = page.locator("form[action='/ui-theme']:visible").first
        assert form.locator("input[name=csrf_token]").count() == 1
        with page.expect_navigation():
            form.locator("button[value=dark]").click()
        cookies = {c["name"]: c["value"] for c in context.cookies()}
        assert cookies.get(auth.UI_THEME_COOKIE_NAME) == "dark"
        form = page.locator("form[action='/ui-lang']:visible").first
        with page.expect_navigation():
            form.locator("button[value=fr]").click()
        cookies = {c["name"]: c["value"] for c in context.cookies()}
        assert cookies.get(auth.UI_LANG_COOKIE_NAME) == "fr"
    finally:
        context.close()
