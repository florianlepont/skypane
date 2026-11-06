"""Real-browser flows of the phone More sheet and the tab bar around it: theme and language set
with one tap inside the sheet (and kept after a reload), Sign out two taps from any page, the
sheet's other rows, French tab labels that never touch at 360px, and the administrator's Account
page carrying a single Sign out control and a neutral space switch."""
import pytest
from companion_app_server import session_cookie_for_state_dir
from skypane_two_device_fleet import OWNER_EMAIL

from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE
from companion.test_device_helpers import start_fleet_app

pytestmark = pytest.mark.browser

_SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

_MORE_OWNS_CENTRE = """() => {
  const e = document.querySelector('.tab-bar__more > summary'); if (!e) return false;
  const r = e.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return hit === e || e.contains(hit); }"""

_LABELS = """() => [...document.querySelectorAll('.tab-bar__label')].map((el) => {
  const range = document.createRange(); range.selectNodeContents(el);
  const box = range.getBoundingClientRect();
  return {text: el.textContent, left: box.left, right: box.right,
          clipped: el.scrollWidth > el.clientWidth + 0.5,
          size: parseFloat(getComputedStyle(el).fontSize)}; })"""


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    holder = start_fleet_app(module_app_server_factory)
    holder.cookie = session_cookie_for_state_dir(holder.server.state_dir, OWNER_EMAIL)
    return holder


def _open(new_context, app, path, viewport, lang="en", scheme="light", bar=True, cookie=None,
          **context_args):
    context = new_context(viewport=viewport, color_scheme=scheme, **context_args)
    base = app.server.base_url()
    name, value = (cookie or app.cookie).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    if bar:
        page.locator(".tab-bar").wait_for(state="visible")
    else:
        page.locator("main").wait_for(state="visible")
    if context_args.get("java_script_enabled", True):
        _settle(page, bar)
    return context, page


def _settle(page, bar=True):
    page.wait_for_function(_SETTLED)
    if bar:
        page.wait_for_function(_MORE_OWNS_CENTRE, timeout=10000)


def _home(app):
    return "/devices/%s/" % app.fleet.live.id


def _open_sheet(page):
    if not page.locator(".tab-bar__more").evaluate("el => el.open"):
        page.locator(".tab-bar__more > summary").click()
    page.locator(".tab-bar__more-panel").wait_for(state="visible")


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_theme_is_one_tap_in_the_sheet_and_survives_a_reload(new_context, app, viewport):
    context, page = _open(new_context, app, _home(app), viewport)
    try:
        for choice in ("dark", "light"):
            _open_sheet(page)
            page.locator(
                ".tab-bar__more-panel button[name=ui_theme][value=%s]" % choice).click()
            page.wait_for_function(
                "t => document.documentElement.getAttribute('data-ui-theme') === t", arg=choice)
            _settle(page)
            page.reload()
            _settle(page)
            assert page.evaluate(
                "() => document.documentElement.getAttribute('data-ui-theme')") == choice
            _open_sheet(page)
            pressed = page.locator(
                ".tab-bar__more-panel button[name=ui_theme][aria-pressed=true]")
            assert pressed.get_attribute("value") == choice
    finally:
        context.close()


@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_language_is_one_tap_in_the_sheet_and_survives_a_reload(new_context, app, viewport):
    context, page = _open(new_context, app, _home(app), viewport, lang="en")
    try:
        _open_sheet(page)
        page.locator(".tab-bar__more-panel button[name=ui_lang][value=fr]").click()
        page.wait_for_function("() => document.documentElement.lang === 'fr'")
        _settle(page)
        assert page.locator(".tab-bar__more > summary .tab-bar__label").inner_text() == "Plus"
        page.reload()
        _settle(page)
        assert page.evaluate("() => document.documentElement.lang") == "fr"
        _open_sheet(page)
        assert page.locator(
            ".tab-bar__more-panel button[name=ui_lang][aria-pressed=true]"
        ).get_attribute("value") == "fr"
        assert page.locator(".tab-bar__pref-label").first.inner_text() == "Thème"
        page.locator(".tab-bar__more-panel button[name=ui_lang][value=en]").click()
        page.wait_for_function("() => document.documentElement.lang === 'en'")
    finally:
        context.close()


def test_the_sheet_works_with_scripts_blocked(new_context, app):
    context, page = _open(
        new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, java_script_enabled=False)
    try:
        page.locator(".tab-bar__more > summary").click()
        page.locator(".tab-bar__more-panel button[name=ui_theme][value=dark]").click()
        page.wait_for_selector("html[data-ui-theme=dark]")
        assert page.locator("html").get_attribute("data-ui-theme") == "dark"
    finally:
        context.close()


def test_sign_out_is_two_taps_from_a_page(new_context, app):
    # Signing out ends the session, so this test signs in with a session of its own.
    own_session = session_cookie_for_state_dir(app.server.state_dir, OWNER_EMAIL)
    context, page = _open(
        new_context, app, _home(app), VIEWPORT_MIN_SUPPORTED, cookie=own_session)
    # The sign-in provider's own logout address is answered here, never fetched.
    context.route(
        "https://tenant.example.test/**",
        lambda route: route.fulfill(status=200, content_type="text/html", body="<p>out</p>"))
    try:
        _open_sheet(page)
        box = page.locator(".tab-bar__sign-out button").bounding_box()
        assert box["height"] >= 44
        with page.expect_request(
                lambda request: request.method == "POST" and request.url.endswith("/logout")):
            page.locator(".tab-bar__sign-out button").click()
        page.wait_for_function("() => location.hostname === 'tenant.example.test'")
    finally:
        context.close()


def test_the_sheet_holds_the_other_rows_and_the_account_row_names_the_person(
        new_context, app):
    context, page = _open(new_context, app, "/fleet", VIEWPORT_MIN_SUPPORTED)
    try:
        _open_sheet(page)
        links = page.locator(".tab-bar__more-panel a")
        assert [links.nth(i).inner_text() for i in range(links.count())] == [
            "Audit log", "Account"]
        shown = page.locator(".tab-bar__account").evaluate(
            "el => getComputedStyle(el, '::after').content")
        assert OWNER_EMAIL in shown
        for selector in (".tab-bar__more-panel a", ".tab-bar__sign-out button",
                         ".tab-bar__more-panel .theme-option"):
            for index in range(page.locator(selector).count()):
                assert page.locator(selector).nth(index).bounding_box()["height"] >= 44
        panel = page.locator(".tab-bar__more-panel").bounding_box()
        bar = page.locator(".tab-bar").bounding_box()
        assert panel["x"] >= 0 and panel["x"] + panel["width"] <= VIEWPORT_MIN_SUPPORTED["width"]
        assert panel["y"] + panel["height"] <= bar["y"] and panel["y"] >= 0
    finally:
        context.close()


@pytest.mark.parametrize("path", ["/users", "/fleet", "/audit"])
@pytest.mark.parametrize("lang", ["fr", "en"])
def test_tab_labels_are_twelve_pixels_whole_and_never_touch_at_360(
        new_context, app, path, lang):
    context, page = _open(new_context, app, path, VIEWPORT_MIN_SUPPORTED, lang=lang)
    try:
        labels = page.evaluate(_LABELS)
        assert len(labels) == 5
        for label in labels:
            assert label["size"] == 12 and not label["clipped"], label
        for left, right in zip(labels, labels[1:]):
            assert right["left"] - left["right"] >= 4, (left["text"], right["text"])
        cells = page.evaluate(
            "() => [...document.querySelectorAll('.tab-bar > *')]"
            ".map((c) => c.getBoundingClientRect().toJSON())")
        assert all(c["width"] >= 44 and c["height"] >= 44 for c in cells)
        widths = [c["width"] for c in cells]
        assert max(widths) - min(widths) <= 8, widths
    finally:
        context.close()


def test_the_admin_first_cell_has_the_shape_of_the_other_cells(new_context, app):
    context, page = _open(new_context, app, "/users", VIEWPORT_MIN_SUPPORTED, lang="fr")
    try:
        boxes = page.evaluate(
            "() => [...document.querySelectorAll('.tab-bar > *')]"
            ".map((c) => c.getBoundingClientRect().toJSON())")
        first, others = boxes[0], boxes[1:]
        assert first["height"] == others[0]["height"]
        assert abs(first["width"] - sum(o["width"] for o in others) / len(others)) <= 8
    finally:
        context.close()


@pytest.mark.parametrize("viewport,name", [
    ({"width": 1280, "height": 900}, "desktop"), (VIEWPORT_MIN_SUPPORTED, "phone")])
def test_the_admin_account_page_has_one_sign_out_and_a_neutral_space_switch(
        new_context, app, viewport, name):
    context, page = _open(new_context, app, "/account", viewport, bar=name == "phone")
    try:
        shown = page.evaluate(
            """() => [...document.querySelectorAll("form[action='/logout'] button")]
                .filter((b) => b.checkVisibility()).length""")
        assert shown == 1
        if name == "phone":
            assert page.locator(".tab-bar__sign-out").count() == 0
        assert page.locator(".space-switch__segment--current").count() == 0
        assert page.locator("[aria-current=page]").count() >= 1
    finally:
        context.close()


def test_other_pages_keep_their_sign_out_in_the_sidebar_and_the_sheet(new_context, app):
    context, page = _open(
        new_context, app, "/fleet", {"width": 1280, "height": 900}, bar=False)
    try:
        assert page.locator(".sidebar-footer form[action='/logout']").count() == 1
        assert page.locator(".tab-bar__sign-out").count() == 1
        assert page.locator(".sidebar-footer .logout-form button").evaluate(
            "el => el.checkVisibility()")
    finally:
        context.close()
