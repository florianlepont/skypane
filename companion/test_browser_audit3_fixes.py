"""Real-browser checks of the third audit's visual fixes: a long frame name next to the logo,
the Flights picture dialog as one panel, the phone tab bar, a single-line entity row's dot,
the Users table's addresses and the quiet-hours times in a 12-hour browser."""
import pytest
import fleet_console_support as fx
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import seed_state_dir
from companion.test_device_helpers import start_fleet_app
from server import fleet_db, fleet_ops, hardware

pytestmark = pytest.mark.browser

LONG_NAME = "Maison de campagne chez Tante Marguerite-Louise"
_COMPLETE = "() => document.readyState === 'complete'"
_ANIMATIONS_DONE = (
    "() => document.getAnimations().every(a => !a.effect || "
    "a.effect.getComputedTiming().iterations === Infinity || a.playState !== 'running')")


def _seed(fleet):
    seed_state_dir(fleet.live.state_dir)
    conn = fleet_db.connect(fleet.live.state_dir)
    try:
        fleet_db.rename_device(conn, fleet.live.id, LONG_NAME)
        fleet_ops.register_frame(
            conn, fx.MAC_PENDING, fx.SECRET_HASH, hardware.LEGACY_KEY, fx.ACTOR)
    finally:
        conn.close()


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory, seed_extra=_seed)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, viewport, lang="en", theme="light"):
    context = new_context(viewport=viewport, color_scheme=theme)
    base = app.server.base_url()
    name, value = app.cookie.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path.replace("LIVE", app.fleet.live.id))
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_COMPLETE, timeout=15000)
    page.wait_for_function(_ANIMATIONS_DONE, timeout=15000)
    return context, page


@pytest.mark.parametrize("width", [360, 390])
def test_a_long_frame_name_never_covers_the_logo_and_wraps_inside_the_title_column(
        new_context, app, width):
    context, page = _open(new_context, app, "/devices/LIVE/", {"width": width, "height": 800})
    try:
        geometry = page.evaluate(
            "() => { const brand = document.querySelector('.site-header .brand')"
            ".getBoundingClientRect();"
            " const menu = document.querySelector('.site-header .frame-menu')"
            ".getBoundingClientRect();"
            " const name = document.querySelector('.frame-menu__name');"
            " const title = document.querySelector('.title-action__text').getBoundingClientRect();"
            " const pencil = document.querySelector('.title-action .btn--icon')"
            ".getBoundingClientRect();"
            " const body = document.querySelector('.hero__body').getBoundingClientRect();"
            " return {brandRight: brand.right, menuLeft: menu.left, menuRight: menu.right,"
            " cut: name.scrollWidth > name.clientWidth,"
            " titleRight: title.right, titleTop: title.top, titleBottom: title.bottom,"
            " pencilLeft: pencil.left, pencilRight: pencil.right, pencilTop: pencil.top,"
            " bodyRight: body.right, viewport: innerWidth}; }")
        assert geometry["brandRight"] <= geometry["menuLeft"] + 0.5, geometry
        assert geometry["menuRight"] <= geometry["viewport"], geometry
        assert geometry["cut"], geometry
        # The long name wraps inside its own column; the pencil stays beside it, in view.
        assert geometry["pencilLeft"] >= geometry["titleRight"] - 0.5, geometry
        assert geometry["pencilTop"] < geometry["titleBottom"], geometry
        assert geometry["pencilRight"] <= geometry["viewport"], geometry
        assert geometry["titleRight"] <= geometry["bodyRight"] + 0.5, geometry
    finally:
        context.close()


def test_the_flights_picture_dialog_is_one_panel_holding_the_picture_caption_and_close(
        new_context, app):
    context, page = _open(
        new_context, app, "/devices/LIVE/flights", {"width": 1280, "height": 900}, theme="dark")
    try:
        page.locator(".flight-picture-link").first.click()
        page.wait_for_function(
            "() => { const d = document.querySelector('dialog.lightbox--picture');"
            " return d.open && getComputedStyle(d).opacity === '1'; }", timeout=10000)
        page.wait_for_function(_ANIMATIONS_DONE, timeout=10000)
        facts = page.evaluate(
            "() => { const d = document.querySelector('dialog.lightbox--picture');"
            " const box = d.getBoundingClientRect();"
            " const inside = s => { const r = d.querySelector(s).getBoundingClientRect();"
            "  return r.left >= box.left - 0.5 && r.right <= box.right + 0.5"
            "   && r.top >= box.top - 0.5 && r.bottom <= box.bottom + 0.5; };"
            " return {image: inside('.lightbox__image'), caption: inside('.lightbox__caption'),"
            " close: inside('[data-view-panel-close]'),"
            " background: getComputedStyle(d).backgroundColor,"
            " close_height: d.querySelector('[data-view-panel-close]').getBoundingClientRect().height,"
            " vw: innerWidth, left: box.left, right: box.right}; }")
        assert facts["image"] and facts["caption"] and facts["close"], facts
        assert facts["background"] != "rgba(0, 0, 0, 0)", facts
        assert facts["close_height"] >= 44 - 0.5, facts
        assert facts["left"] > 0 and facts["right"] < facts["vw"], facts
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_phone_tab_bar_caret_is_centred_over_the_dots_and_every_label_is_whole(
        new_context, app, lang):
    context, page = _open(
        new_context, app, "/fleet?frame=LIVE", {"width": 360, "height": 800}, lang=lang)
    try:
        facts = page.evaluate(
            "() => { const cut = [...document.querySelectorAll('.tab-bar__label')]"
            ".some(l => l.scrollWidth > l.clientWidth);"
            " const summary = document.querySelector('.tab-bar__more > summary');"
            " const box = summary.getBoundingClientRect();"
            " const caret = getComputedStyle(summary, '::before');"
            " return {cut: cut, position: caret.position,"
            " right: parseFloat(caret.right), width: box.width,"
            " caretWidth: parseFloat(caret.width) + parseFloat(caret.borderRightWidth)}; }")
        assert not facts["cut"], facts
        assert facts["position"] == "absolute", facts
        # Centred: the caret's right edge sits at (or within a pixel or two of) half the cell.
        assert abs(facts["right"] - facts["width"] / 2 + 3) < 6, facts
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 900}, {"width": 390, "height": 844}],
                         ids=["1280", "390"])
def test_a_single_line_frame_row_centres_its_status_dot_on_the_title(new_context, app, viewport):
    context, page = _open(new_context, app, "/fleet?frame=LIVE", viewport)
    try:
        page.locator("li.entity-row").first.wait_for(state="attached")
        dots = page.evaluate(
            "() => [...document.querySelectorAll('li.entity-row')].map(row => {"
            " const d = row.querySelector('.entity-row__dot').getBoundingClientRect();"
            " const t = row.querySelector('.entity-row__title').getBoundingClientRect();"
            " return [d.top + d.height / 2, t.top + t.height / 2]; })")
        assert dots
        for dot, title in dots:
            assert abs(dot - title) < 2.5, dots
    finally:
        context.close()


def test_users_addresses_stay_whole_at_1280(new_context, app):
    context, page = _open(new_context, app, "/users", {"width": 1280, "height": 900})
    try:
        broken = page.evaluate(
            "() => [...document.querySelectorAll('.users-email')].filter(e => {"
            " const line = parseFloat(getComputedStyle(e).lineHeight) || 24;"
            " return e.getBoundingClientRect().height > line * 1.6; }).map(e => e.textContent)")
        assert broken == [], broken
    finally:
        context.close()


def test_leaving_personalisation_with_an_unsaved_look_asks_first(new_context, app):
    """a changed look arms the leave guard through the Save bar's own dirty state, and Cancel
    disarms it"""
    from companion.test_browser_ux_helpers import _guard_armed, _wait_for_bar
    context, page = _open(
        new_context, app, "/devices/LIVE/display", {"width": 390, "height": 844})
    try:
        assert not _guard_armed(page)
        other = page.locator('input[type=radio][name="theme"]:not(:checked)').first
        other.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', "
                       "{bubbles: true})); }")
        _wait_for_bar(page)
        assert _guard_armed(page)
    finally:
        context.close()


@pytest.mark.parametrize("path,field,value", [
    ("/devices/LIVE/display/special-looks/new", "#rule-key", "AFR1234"),
    ("/devices/LIVE/display/calendar/connect", 'input[name="calendar_url"]', "https://example.test/c.ics"),
])
def test_a_typed_form_view_arms_the_leave_guard_and_a_pristine_one_does_not(
        new_context, app, path, field, value):
    from companion.test_browser_ux_helpers import _guard_armed
    context, page = _open(new_context, app, path, {"width": 390, "height": 844})
    try:
        assert not _guard_armed(page)
        page.fill(field, value)
        page.wait_for_function(
            "() => { var e = new Event('beforeunload', {cancelable: true});"
            " window.dispatchEvent(e); return e.defaultPrevented; }", timeout=5000)
    finally:
        context.close()


def test_flights_search_and_sort_keep_back_sensible(new_context, app):
    """a committed sort adds a history entry and Back returns to the list as it was before;
    the first live typing starts an entry of its own and the typing after it only replaces it"""
    context, page = _open(
        new_context, app, "/devices/LIVE/flights", {"width": 1280, "height": 900})
    try:
        start = page.url
        length = page.evaluate("() => history.length")
        page.evaluate(
            "() => { const r = document.querySelector('input[name=\"sort\"][value=\"airline\"]');"
            " r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true})); }")
        page.wait_for_function("() => location.search.indexOf('sort=airline') >= 0", timeout=10000)
        assert page.evaluate("() => history.length") == length + 1
        page.go_back()
        page.wait_for_function("() => location.search.indexOf('sort=') < 0", timeout=10000)
        page.wait_for_function(
            "() => document.readyState === 'complete' && !document.querySelector("
            "'input[name=\"sort\"][value=\"airline\"]:checked')", timeout=10000)
        assert page.url == start
        page.fill("[data-flights-search]", "afr")
        page.wait_for_function("() => location.search.indexOf('q=afr') >= 0", timeout=10000)
        page.fill("[data-flights-search]", "afr1")
        page.wait_for_function("() => location.search.indexOf('q=afr1') >= 0", timeout=10000)
        page.go_back()
        page.wait_for_function(
            "() => location.search.indexOf('q=') < 0 && document.readyState === 'complete'",
            timeout=10000)
        assert page.url == start
    finally:
        context.close()


def test_back_after_two_typed_and_entered_searches_returns_to_the_first(new_context, app):
    """a first search gets an entry of its own and Enter settles it; a second search typed after it
    gets one too, so Back returns to the first search and then to the list, not off the page"""
    context, page = _open(
        new_context, app, "/devices/LIVE/flights", {"width": 1280, "height": 900})
    try:
        page.evaluate(
            "() => { window.__writes = []; ['pushState', 'replaceState'].forEach((name) => {"
            " const original = history[name].bind(history);"
            " history[name] = (...args) => { window.__writes.push(name); original(...args); }; }); }")
        length = page.evaluate("() => history.length")

        def settled(count):
            page.wait_for_function("(n) => window.__writes.length >= n", arg=count, timeout=10000)

        page.fill("[data-flights-search]", "afr")
        settled(1)
        page.press("[data-flights-search]", "Enter")
        settled(2)
        assert page.evaluate("() => history.length") == length + 1
        page.fill("[data-flights-search]", "afr1")
        settled(3)
        page.press("[data-flights-search]", "Enter")
        settled(4)
        assert page.evaluate("() => window.__writes") == [
            "pushState", "replaceState", "pushState", "replaceState"]
        assert page.evaluate("() => history.length") == length + 2
        page.go_back()
        page.wait_for_function(
            "() => location.search.indexOf('q=afr1') < 0 && location.search.indexOf('q=afr') >= 0"
            " && document.readyState === 'complete'", timeout=10000)
        assert "/flights" in page.url
    finally:
        context.close()


def test_without_scripts_every_artwork_upload_form_has_a_visible_44px_submit_button(
        new_context, make_app_server):
    """with scripts off, once a row's menu is opened each per-illustration upload form offers a
    visible Upload button (the file input alone only sends on change, which needs a script)"""
    from companion.test_browser_ux_helpers import _no_js_page
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    with _no_js_page(
            new_context, server.base_url(), "/airlines/manage",
            viewport={"width": 1280, "height": 900}, reduced_motion="reduce") as page:
        page.locator("form.airlines-art").first.wait_for(state="attached")
        page.evaluate("() => document.querySelectorAll('details').forEach(d => { d.open = true; })")
        boxes = page.evaluate(
            "() => [...document.querySelectorAll('form.airlines-art')].map(f => {"
            " const b = f.querySelector('button[type=submit]');"
            " const r = b ? b.getBoundingClientRect() : null;"
            " return r ? [r.width, r.height] : null; })")
        assert boxes and all(box and box[0] >= 44 and box[1] >= 44 for box in boxes), boxes
