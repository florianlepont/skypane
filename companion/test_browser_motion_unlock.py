"""Real-browser checks of the picture dialog and the airline card unlock.

The Flights picture dialog shows the picture alone (no card behind it) in both themes, closes by
Escape and by its button with focus back on the thumbnail. A newly seen airline card flips once
per user (not again on reload), shows flipped under reduced motion and without scripts.

State is always waited for, never read right after an input."""
from datetime import datetime, timedelta, timezone

import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT, VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _login, _no_js_page,
    _set_ui_theme, seed_state_dir,
)
from server import history_db

pytestmark = pytest.mark.browser

DIALOG = "#panel-lookup-dialog"
THUMB = ".history-card__thumb:visible, td [data-view-panel-src]:visible"
NEW_ITEM = ".collection-item[data-unlock]"
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))

@pytest.fixture(scope="module")
def flights_server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


def seed_collection(state_dir):
    """The shared fixture plus TAP Portugal seen a minute ago: the one newly seen airline."""
    seed_state_dir(state_dir)
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            hex="tp0001", callsign="TAP001", aircraft_type="A21N",
            confirmed_state="arriving", airline="TAP Portugal")


def _page(new_context, base_url, path, viewport, reduced=False):
    context = new_context(
        viewport=viewport, reduced_motion="reduce" if reduced else "no-preference")
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + path)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    return context, page


def _open_picture(page):
    page.locator(THUMB).first.wait_for(state="visible")
    page.locator(THUMB).first.click()
    page.wait_for_function(
        "s => { const d = document.querySelector(s); return d.open"
        " && document.getAnimations().every(a => a.playState !== 'running'); }",
        arg=DIALOG, timeout=10000)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_picture_dialog_is_one_opaque_panel_and_close_returns_to_the_thumbnail(
        new_context, flights_server, label, viewport, theme):
    context, page = _page(new_context, flights_server.base_url(), "/flights", viewport)
    try:
        _set_ui_theme(page, theme)
        _open_picture(page)
        look = page.eval_on_selector(DIALOG, """el => {
            const s = getComputedStyle(el);
            const img = getComputedStyle(el.querySelector('img.lightbox__image'));
            return {bg: s.backgroundColor, border: s.borderTopWidth, pad: s.paddingTop,
                    radius: img.borderTopLeftRadius};
        }""")
        # One opaque panel (caption and Close live inside it), never a bare picture.
        assert look["bg"] not in ("rgba(0, 0, 0, 0)", "transparent"), look
        assert look["border"] == "1px" and look["pad"] == "16px", look
        assert look["radius"] == "5px", look
        box = page.eval_on_selector(DIALOG, """el => {
            const d = el.getBoundingClientRect();
            const i = el.querySelector('img.lightbox__image').getBoundingClientRect();
            return {left: i.left - d.left, right: d.right - i.right, top: i.top - d.top};
        }""")
        assert abs(box["top"] - 16) <= 1 and abs(box["left"] - box["right"]) <= 1, box
        for how in ("escape", "button"):
            if how == "escape":
                page.keyboard.press("Escape")
            else:
                page.locator(DIALOG + " [data-view-panel-close]").click()
            page.wait_for_function(
                "s => !document.querySelector(s).open && document.querySelector('.vt-pic') === null"
                " && document.activeElement.hasAttribute('data-view-panel-src')",
                arg=DIALOG, timeout=10000)
            if how == "escape":
                _open_picture(page)
    finally:
        context.close()


def test_the_tab_bar_is_not_a_named_group_while_the_picture_transition_runs(
        new_context, flights_server):
    """a named tab bar would paint above the page snapshot that holds the dialog, covering its
    Close button for the length of the transition: while the transition runs the bar and its
    pill carry no view-transition name, and both get their names back afterwards"""
    context, page = _page(new_context, flights_server.base_url(), "/flights", VIEWPORT_MIN_SUPPORTED)
    try:
        page.evaluate("""() => {
            window.__samples = [];
            const bar = document.querySelector('.tab-bar');
            const slider = document.querySelector('.tab-bar__slider');
            const tick = () => {
                window.__samples.push([
                    document.documentElement.classList.contains('is-picture-transition'),
                    getComputedStyle(bar).viewTransitionName,
                    getComputedStyle(slider).viewTransitionName]);
                requestAnimationFrame(tick);
            };
            tick();
        }""")
        _open_picture(page)
        page.locator(DIALOG + " [data-view-panel-close]").click()
        page.wait_for_function(
            "s => !document.querySelector(s).open && document.querySelector('.vt-pic') === null"
            " && !document.documentElement.classList.contains('is-picture-transition')",
            arg=DIALOG, timeout=10000)
        samples = page.evaluate("() => window.__samples")
        during = [sample for sample in samples if sample[0]]
        assert during, samples[-5:]
        assert all(sample[1:] == ["none", "none"] for sample in during), during
        names = page.evaluate(
            "() => [getComputedStyle(document.querySelector('.tab-bar')).viewTransitionName,"
            " getComputedStyle(document.querySelector('.tab-bar__slider')).viewTransitionName]")
        assert names == ["skypane-tab-bar", "skypane-tab-slider"]
    finally:
        context.close()


def test_the_picture_dialog_keeps_a_focus_trap_and_a_labelled_dialog(new_context, flights_server):
    context, page = _page(new_context, flights_server.base_url(), "/flights", VIEWPORT_DESKTOP)
    try:
        _open_picture(page)
        assert page.get_attribute(DIALOG, "aria-label")
        for _ in range(3):
            page.keyboard.press("Tab")
            page.wait_for_function(
                "s => document.querySelector(s).contains(document.activeElement)",
                arg=DIALOG, timeout=5000)
    finally:
        context.close()


def _wait_flip_settled(page):
    page.wait_for_function(
        "() => document.querySelectorAll('.unlock-spark, .unlock-glint').length === 0",
        timeout=10000)


def test_a_new_airline_card_flips_once_and_not_on_reload(new_context, make_app_server):
    server = make_app_server(seed=seed_collection)
    context, page = _page(new_context, server.base_url(), "/airlines", VIEWPORT_DESKTOP)
    try:
        page.wait_for_function(
            "() => localStorage.length > 0 && Object.keys(localStorage).some("
            "k => k.indexOf('skypane.unlocked.') === 0)", timeout=10000)
        _wait_flip_settled(page)
        page.reload()
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.locator(NEW_ITEM).wait_for(state="visible")
        page.wait_for_timeout(600)
        assert page.locator(".unlock-glint, .unlock-spark").count() == 0
        assert page.eval_on_selector(
            NEW_ITEM + " a.collection-card", "el => el.getAnimations().length") == 0
    finally:
        context.close()


@pytest.mark.parametrize("width", (390, 1280))
def test_the_first_airlines_visit_unlocks_cards_without_any_page_error(
        new_context, make_app_server, width):
    server = make_app_server(seed=seed_collection)
    context = new_context(viewport={"width": width, "height": 844})
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.wait_for_function(
            "() => Object.keys(localStorage).some(k => k.indexOf('skypane.unlocked.') === 0)",
            timeout=10000)
        _wait_flip_settled(page)
        assert errors == []
    finally:
        context.close()


def test_a_new_airline_card_plays_the_flip_first_time(new_context, make_app_server):
    server = make_app_server(seed=seed_collection)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    context.add_init_script("""
        new MutationObserver(() => {
          if (document.querySelector('.unlock-spark')) window.__sparked = true;
        }).observe(document, {childList: true, subtree: true});""")
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        page.wait_for_function("() => window.__sparked === true", timeout=10000)
        _wait_flip_settled(page)
    finally:
        context.close()


OVERRIDE = (
    ":root{--motion-unlock:1234ms;--motion-reveal:777ms;--motion-picture:1500ms;"
    "--motion-spring:cubic-bezier(0.1,0.2,0.3,0.4)}")
OVERRIDE_SCRIPT = """
    document.addEventListener('DOMContentLoaded', () => {
      const style = document.createElement('style');
      style.textContent = %r;
      document.head.appendChild(style);
    });
    window.__timings = [];
    const realAnimate = Element.prototype.animate;
    Element.prototype.animate = function (frames, options) {
      window.__timings.push({cls: String(this.getAttribute('class') || ''),
        duration: options && options.duration, easing: options && options.easing});
      return realAnimate.call(this, frames, options);
    };""" % OVERRIDE


def test_the_unlock_timings_follow_the_motion_tokens(new_context, make_app_server):
    """the flip, the glint and the sparks take their lengths and easing from the page's
    motion tokens, not from numbers of their own"""
    server = make_app_server(seed=seed_collection)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": server.base_url()}])
    context.add_init_script(OVERRIDE_SCRIPT)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        page.goto(server.base_url() + "/airlines")
        page.wait_for_function(
            "() => window.__timings.some(t => t.cls.indexOf('unlock-spark') >= 0)", timeout=10000)
        timings = page.evaluate("() => window.__timings")
        flip = [t for t in timings if "collection-card" in t["cls"]][0]
        assert flip["duration"] == 1234 and flip["easing"] == "cubic-bezier(0.1,0.2,0.3,0.4)", flip
        for part in ("unlock-glint__sweep", "unlock-spark"):
            found = [t for t in timings if part in t["cls"] or part.split("__")[0] in t["cls"]]
            assert found and all(t["duration"] == 777 for t in found), (part, found)
    finally:
        context.close()


def test_the_picture_transition_takes_its_length_from_the_picture_token(
        new_context, flights_server):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": flights_server.base_url()}])
    context.add_init_script(OVERRIDE_SCRIPT)
    page = context.new_page()
    try:
        _login(page, flights_server.base_url())
        page.goto(flights_server.base_url() + "/flights")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        page.evaluate("""() => { window.__vt = [];
            const tick = () => { for (const a of document.getAnimations()) {
              const e = a.effect;
              if (e && e.pseudoElement === '::view-transition-group(skypane-flight-pic)') {
                window.__vt.push(e.getTiming().duration); } }
              requestAnimationFrame(tick); };
            tick(); }""")
        _open_picture(page)
        durations = page.evaluate("() => window.__vt")
        assert durations and set(durations) == {1500}, durations
    finally:
        context.close()


def test_under_reduced_motion_the_new_card_is_shown_flipped_without_animation(
        new_context, make_app_server):
    server = make_app_server(seed=seed_collection)
    context, page = _page(
        new_context, server.base_url(), "/airlines", VIEWPORT_DESKTOP, reduced=True)
    try:
        page.locator(NEW_ITEM).wait_for(state="visible")
        page.wait_for_timeout(600)
        assert page.locator(".unlock-glint, .unlock-spark").count() == 0
        assert page.eval_on_selector(
            NEW_ITEM + " a.collection-card", "el => el.getAnimations().length") == 0
        assert page.eval_on_selector(
            NEW_ITEM + " a.collection-card", "el => getComputedStyle(el).transform") == "none"
    finally:
        context.close()


def test_without_scripts_the_new_card_is_shown_flipped(new_context, make_app_server):
    server = make_app_server(seed=seed_collection)
    with _no_js_page(new_context, server.base_url(), "/airlines") as page:
        page.locator(NEW_ITEM).wait_for(state="visible")
        assert page.eval_on_selector(
            NEW_ITEM + " a.collection-card", "el => getComputedStyle(el).transform") == "none"

