"""Real-browser check that every phone bottom sheet with a field keeps the focused field, and the
whole sheet, above the on-screen keyboard.

The keyboard is emulated the way a phone behaves: the layout viewport keeps its height while the
visual viewport (what the keyboard leaves visible) shrinks. One test per sheet opens it from its
own address, focuses its first field and measures the field and the sheet against the keyboard's
top edge; closing the keyboard lets the sheet settle back on the bottom edge."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_PHONE, _set_ui_theme
from server import fleet_db

pytestmark = pytest.mark.browser

_FAKE_VISUAL_VIEWPORT = """(() => {
  const listeners = {};
  const vv = {height: window.innerHeight, width: window.innerWidth, offsetTop: 0, offsetLeft: 0,
    scale: 1,
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener() {},
    dispatch(type) { (listeners[type] || []).forEach(fn => fn()); }};
  Object.defineProperty(window, 'visualViewport', {value: vv, configurable: true});
})()"""
_RESIZE = "h => { visualViewport.height = h; visualViewport.dispatch('resize'); }"
_BOX = """sel => { const r = document.querySelector(sel).getBoundingClientRect();
  return {t: r.top, b: r.bottom}; }"""
_FIELD = "input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select"

# (id, persona, page, dialog id, the field to focus: a selector inside the dialog)
SHEETS = (
    ("users-invite", "admin", "/users", "dlg-invite-user", "#invite-email"),
    ("fleet-reassign", "admin", "/fleet?frame={owned}&tab=access", "dlg-reassign-{slug}",
     "select"),
    ("fleet-add-co-manager", "admin", "/fleet?frame={owned}&tab=access",
     "dlg-add-co-manager-{slug}", _FIELD),
    ("account-manage-access", "owner", "/account", "dlg-access-{slug}",
     "input[type=email], select"),
    ("quiet-hours", "admin", "/", "dlg-quiet-hours", "input[type=time]"),
    ("airline-rename", "admin", "/airlines/manage", "rename-airline-0", "input[name=airline_name]"),
)


def _ids(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        owned = conn.execute("SELECT id FROM devices WHERE name = 'Kitchen'").fetchone()["id"]
    finally:
        conn.close()
    return {"owned": owned, "slug": owned.lower().replace("_", "-")}


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_fleet)


@pytest.mark.parametrize("name,persona,path,dialog,field", SHEETS, ids=[s[0] for s in SHEETS])
def test_the_focused_field_of_the_sheet_stays_above_the_on_screen_keyboard(
        new_context, server, name, persona, path, dialog, field):
    ids = _ids(server)
    pair = (fx.admin_cookie if persona == "admin" else fx.user_cookie)(
        server.state_dir, *(() if persona == "admin" else (fx.OWNER_EMAIL,)))
    cookie_name, value = pair.split("=", 1)
    context = new_context(viewport=VIEWPORT_PHONE, color_scheme="light")
    context.add_init_script(_FAKE_VISUAL_VIEWPORT)
    context.add_cookies([
        {"name": cookie_name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    try:
        page = context.new_page()
        dialog_id = dialog.format(**ids)
        sheet = "dialog#" + dialog_id
        page.goto(server.base_url() + path.format(**ids) + "#" + dialog_id)
        page.locator("main").wait_for(state="visible")
        _set_ui_theme(page, "light")
        page.locator(sheet + ".is-modal[open]").wait_for(state="visible")
        page.wait_for_function(
            "() => document.getAnimations().every(a => a.playState !== 'running'"
            " || a.effect.getComputedTiming().iterations === Infinity)")
        height = page.evaluate("() => innerHeight")
        assert page.evaluate(_BOX, sheet)["b"] == pytest.approx(height, abs=1)

        keyboard = round(height * 0.6)
        page.evaluate(_RESIZE, keyboard)
        target = "%s %s" % (sheet, field)
        page.locator(target).first.focus()
        page.wait_for_function(
            "k => document.querySelector('%s').getBoundingClientRect().bottom <= k + 1" % sheet,
            arg=keyboard)
        focused = page.evaluate(
            "sel => { const r = document.activeElement.getBoundingClientRect();"
            " return {t: r.top, b: r.bottom, ok: document.querySelector(sel)"
            ".contains(document.activeElement)}; }", sheet)
        assert focused["ok"], "the focus is not in the sheet"
        box = page.evaluate(_BOX, sheet)
        assert focused["t"] >= 0 and focused["b"] <= keyboard, (focused, keyboard)
        assert box["t"] >= 0 and box["b"] <= keyboard + 1, (box, keyboard)

        page.evaluate(_RESIZE, height)
        page.wait_for_function(
            "h => Math.abs(document.querySelector('%s').getBoundingClientRect().bottom - h) <= 1"
            % sheet, arg=height)
    finally:
        context.close()
