"""Real-browser checks that every page with something to save shows the SAME floating Cancel and
Save bar: the same width, height and distance from the bottom of the viewport, the same position
across the pages of one viewport, the same structure (a message, then Cancel, then Save, 44px
targets) and the same words, at 390 and 1280 px, in both languages and both themes. The numbers
are read off the rendered pages; the pages are measured one after the other in one browser
context so the comparison is between pages, never against a hard-coded size."""
import pytest

from co_manager_browser_support import SUBPIXEL
from companion import auth, layout
from companion.test_browser_ux_helpers import _login, seed_state_dir
from companion_app_server import TEST_ADMIN_EMAIL, session_cookie_for_state_dir
from place_map_support import Hosts
from server import device_config, device_dirs, fleet_db, hardware
from server.plane import colour_rules

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
DESKTOP = {"width": 1280, "height": 800}
BAR = ".dirty-bar"
WORDS = {"en": ("Cancel", "Save"), "fr": ("Annuler", "Enregistrer")}
UNSAVED = {"en": "Unsaved changes", "fr": "Modifications non enregistrées"}
_SETTLED = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "a => !a.effect || a.effect.getTiming().iterations === Infinity || a.playState !== 'running')")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")
_MEASURE = """() => {
  const rect = sel => { const r = document.querySelector(sel).getBoundingClientRect();
    return {left: r.left, right: r.right, top: r.top, bottom: r.bottom,
            width: r.width, height: r.height}; };
  const bar = document.querySelector('.dirty-bar');
  const kids = Array.from(bar.children).map(el => el.className.split(' ').find(c => c.startsWith('dirty-bar__')));
  const box = rect('.dirty-bar');
  return {
    width: box.width, height: box.height, left: box.left, right: box.right,
    fromBottom: window.innerHeight - box.bottom,
    cancel: rect('.dirty-bar__cancel'), save: rect('.dirty-bar__save'),
    message: rect('.dirty-bar__message'),
    order: kids,
    messageText: document.querySelector('.dirty-bar__message').textContent.trim(),
    cancelText: document.querySelector('.dirty-bar__cancel').textContent.trim(),
    saveText: document.querySelector('.dirty-bar__save').textContent.trim(),
    role: bar.getAttribute('role'), label: bar.getAttribute('aria-label'),
    scrollW: document.documentElement.scrollWidth, clientW: document.documentElement.clientWidth,
  };
}"""


def _seed(state_dir):
    """The administrator owns the live frame (named, in France) and one location; the display
    pages have a look, a special look to edit and a runway detection to change."""
    seed_state_dir(state_dir)
    session_cookie_for_state_dir(state_dir)
    conn = fleet_db.connect(state_dir)
    try:
        owner = fleet_db.get_user_by_email(conn, TEST_ADMIN_EMAIL)["id"]
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:04", "d" * 64, hardware.LEGACY_KEY, owner,
            name="Live frame", state_path=device_dirs.LIVE_STATE_PATH)
        fleet_db.add_location(conn, "Home", 48.8566, 2.3522, "Europe/Paris", owner_user_id=owner)
    finally:
        conn.close()
    device_config.save_device_config(
        state_dir, theme="band_red_field",
        detection={"mode": "runway", "airport": "LFPG", "runway": "08L/26R"})
    colour_rules.add_rule(state_dir, "prefix", "TVF", "white")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _pick_look(page):
    page.locator(".look-dot:has(input:not(:checked):not(:disabled)):visible").first.click()


def _pick_arrivals_look(page):
    page.locator("input[name='theme_arriving'][value='white']").evaluate("el => el.click()")


def _pick_mode(page):
    page.click("label:has(#place-mode-area)")


def _type_key(page):
    page.locator("[name=rule_key]").fill("AFR")


def _pick_other_card(page):
    page.locator("label.look-pick__card:has(input:not(:checked))").first.click()


def _type_calendar_url(page):
    page.locator("#calendar-connect-url").fill("https://calendar.example/feed.ics")


def _change_wake(page):
    page.locator("#wake-interval-s").fill("900")


def _fleet_route(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        frame = conn.execute("SELECT id FROM devices LIMIT 1").fetchone()[0]
    finally:
        conn.close()
    return "/fleet?tab=settings&frame=%s" % frame


# name, route (a callable of the server for the fleet page), element to wait for, edit to make.
PAGES = [
    ("departures", layout.DISPLAY_ROUTE, ".look-dot", _pick_look),
    ("arrivals", layout.DISPLAY_ARRIVALS_ROUTE, ".look-dot", _pick_arrivals_look),
    ("special-look-new", layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE, "label.look-pick__card", _type_key),
    ("special-look-edit", layout.DISPLAY_SPECIAL_LOOK_EDIT_ROUTE + "?rule_key=TVF",
     "label.look-pick__card", _pick_other_card),
    ("calendar-connect", layout.DISPLAY_CALENDAR_CONNECT_ROUTE, "#calendar-connect-url",
     _type_calendar_url),
    ("location", "/detection", "#place-mode-area", _pick_mode),
    ("fleet", _fleet_route, "#wake-interval-s", _change_wake),
]


def _open(new_context, server, viewport, lang, scheme, name, route, ready, edit):
    context = new_context(viewport=viewport, color_scheme=scheme)
    Hosts(context)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + (route(server) if callable(route) else route))
    page.locator(ready).first.wait_for(state="attached", timeout=15000)
    page.wait_for_function(_SETTLED, timeout=20000)
    if name == "location":
        page.wait_for_function(
            "() => document.documentElement.classList.contains('map-ready')", timeout=15000)
    if edit is not None:
        edit(page)
    page.locator(BAR).wait_for(state="visible", timeout=10000)
    page.wait_for_function(_SETTLED, timeout=20000)
    for selector in (BAR + " .dirty-bar__save", BAR + " .dirty-bar__cancel"):
        page.wait_for_function(_OWNS_CENTRE, arg=selector, timeout=10000)
    return context, page


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [PHONE, DESKTOP], ids=["390", "1280"])
def test_every_page_shows_the_same_save_bar(new_context, server, viewport, lang, scheme):
    measured = {}
    for name, route, ready, edit in PAGES:
        context, page = _open(new_context, server, viewport, lang, scheme, name, route, ready, edit)
        try:
            measured[name] = page.evaluate(_MEASURE)
        finally:
            context.close()
    reference = measured["fleet"]
    cancel, save = WORDS[lang]
    for name, m in measured.items():
        where = "%s at %dpx (%s, %s)" % (name, viewport["width"], lang, scheme)
        assert m["order"][0] == "dirty-bar__message" and m["order"][1:] == [
            "dirty-bar__cancel", "dirty-bar__save"], (where, m["order"])
        assert (m["cancelText"], m["saveText"]) == (cancel, save), where
        assert m["role"] == "region" and m["label"], where
        assert m["cancel"]["right"] <= m["save"]["left"] + SUBPIXEL, where
        for button in ("cancel", "save"):
            assert m[button]["height"] >= 44 - SUBPIXEL and m[button]["width"] >= 44, (where, button)
        assert m["scrollW"] <= m["clientW"], where
        if name == "location" or "special" not in name and name != "calendar-connect":
            assert m["messageText"] == UNSAVED[lang], (where, m["messageText"])
        # The Location page on a phone draws the same bar as the actions of its compact card, at
        # the card's top right, not as a strip of its own.
        compact = name == "location" and viewport["width"] < 960
        for key in ("width", "height", "left", "right", "fromBottom"):
            if compact:
                break
            assert abs(m[key] - reference[key]) <= SUBPIXEL, (
                where, key, m[key], "differs from the fleet page's", reference[key])
        if compact:
            assert m["height"] >= 44 - SUBPIXEL and m["right"] <= viewport["width"], (where, m)
        for key in ("width", "height"):
            for button in ("cancel", "save"):
                assert abs(m[button][key] - reference[button][key]) <= SUBPIXEL or key == "width", (
                    where, button, key)
    if viewport["width"] < 960:
        bar_width = reference["width"]
        assert abs(bar_width - (viewport["width"] - 32)) <= SUBPIXEL, reference
    else:
        # Docked to the main column, not centred on the window: the sidebar is to its left.
        assert reference["left"] > 240, reference


# Whether the bar had a box the moment the parser added it (before any deferred script ran)
# and on every frame after that, until the test reads the list.
_WATCH_BAR = """
window.__bar = {parsed: null, frames: []};
new MutationObserver((records, observer) => {
  const bar = document.querySelector('.dirty-bar');
  if (!bar) { return; }
  observer.disconnect();
  window.__bar.parsed = bar.getClientRects().length > 0;
  const step = () => {
    window.__bar.frames.push(bar.getClientRects().length > 0);
    if (!window.__bar.stop) { requestAnimationFrame(step); }
  };
  requestAnimationFrame(step);
}).observe(document, {childList: true, subtree: true});
"""
# The pages whose bar appears only once something changed.
_REVEALING = [page for page in PAGES if page[0] in (
    "departures", "arrivals", "special-look-new", "calendar-connect", "fleet")]


@pytest.mark.parametrize("name,route,ready,edit", _REVEALING, ids=[p[0] for p in _REVEALING])
def test_the_save_bar_is_out_of_the_page_until_something_changes(
        new_context, server, name, route, ready, edit):
    """With scripts on, the bar has no box from the moment it is parsed to the end of the page
    opening (it never flashes at the bottom of the screen); the first change brings it in."""
    context = new_context(viewport=PHONE)
    Hosts(context)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    try:
        page = context.new_page()
        _login(page, server.base_url())
        context.add_init_script(_WATCH_BAR)
        page.goto(server.base_url() + (route(server) if callable(route) else route))
        page.locator(ready).first.wait_for(state="attached", timeout=15000)
        page.wait_for_function(_SETTLED, timeout=20000)
        page.wait_for_function("() => window.__bar.frames.length > 5", timeout=10000)
        seen = page.evaluate("() => { window.__bar.stop = true; return window.__bar; }")
        assert seen["parsed"] is False, name
        assert not any(seen["frames"]), (name, seen["frames"])
        assert page.locator(BAR).is_hidden()
        edit(page)
        page.locator(BAR).wait_for(state="visible", timeout=10000)
    finally:
        context.close()


def test_without_scripts_the_save_bar_is_in_the_page(new_context, server):
    """A visitor without scripts has no other way to save: the bar is shown as rendered."""
    context = new_context(viewport=PHONE, java_script_enabled=False)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.DISPLAY_ROUTE)
        page.locator(BAR).wait_for(state="visible", timeout=10000)
        box = page.locator(BAR + " .dirty-bar__save").bounding_box()
        assert box and box["height"] >= 44
    finally:
        context.close()
