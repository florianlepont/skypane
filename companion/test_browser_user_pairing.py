"""Real-browser checks of a user adding their own frame: the empty state a
person with no frame sees, the Add a frame entries (Account link, last tile
of the frame strip), the code page and its refusal, success landing on the
new frame's Home, geometry and tap targets at 360 and 1280px in both
languages and themes, and the same flow with scripts blocked."""
import re

import pytest

import fleet_console_support as fx
from frame_menu_support import open_menu
from co_manager_browser_support import MIN_TAP_PX, _no_sideways_scroll
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _set_ui_theme
from server import fleet_db, hardware

pytestmark = pytest.mark.browser

VIEWPORTS = (VIEWPORT_MIN_SUPPORTED, {"width": 1280, "height": 900})
HOME_URL = re.compile(r".*/devices/[^/?]+/(\?.*)?$")
TEXT = {
    "en": {"add": "Add your frame", "title": "Add a frame", "refused": "Code not recognised",
           "empty": "Your frames will appear here", "toast": "Frame added"},
    "fr": {"add": "Ajouter votre cadre", "title": "Ajouter un cadre",
           "refused": "Code non reconnu", "empty": "Vos cadres apparaîtront ici",
           "toast": "Cadre ajouté"},
}


def _open(new_context, server, email, path, lang="en", theme=None,
          viewport=VIEWPORT_MIN_SUPPORTED, **context_kwargs):
    context = new_context(viewport=viewport, **context_kwargs)
    pair = fx.user_cookie(server.state_dir, email)
    name, value = pair.split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'")
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _owns_the_centre(page, selector):
    page.wait_for_function(
        "(sel) => { const e = document.querySelector(sel); if (!e) return false;"
        " const r = e.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.x + r.width / 2, r.y + r.height / 2);"
        " return hit === e || e.contains(hit); }", arg=selector)


def _height(page, selector):
    # Rounded to 0.01px: layout float noise can read 43.99998 for a 44px box.
    return round(page.locator(selector).first.bounding_box()["height"], 2)


@pytest.fixture
def seeded(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    fx.issue_code(server.state_dir, seed.pending_id)
    return server, seed


def _device(server):
    conn = fleet_db.connect(server.state_dir)
    try:
        return fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
    finally:
        conn.close()


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=["360", "1280"])
def test_the_empty_state_offers_one_44px_primary_action_that_fits(
        new_context, seeded, viewport, lang, theme):
    server, _seed = seeded
    context, page = _open(
        new_context, server, fx.USER_EMAIL, "/account", lang, theme, viewport)
    try:
        text = TEXT[lang]
        assert text["empty"] in page.locator("main").inner_text()
        primary = page.locator("a.pair-link--primary")
        assert primary.count() == 1 and primary.inner_text() == text["add"]
        _owns_the_centre(page, "a.pair-link--primary")
        assert _height(page, "a.pair-link--primary") >= MIN_TAP_PX
        assert _no_sideways_scroll(page)
    finally:
        context.close()


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _rgb(css_colour):
    return tuple(float(n) for n in re.findall(r"[\d.]+", css_colour)[:3])


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_add_your_frame_button_text_is_readable_on_its_fill(
        new_context, seeded, lang, theme):
    server, _seed = seeded
    context, page = _open(new_context, server, fx.USER_EMAIL, "/account", lang, theme)
    try:
        selector = "a.pair-link--primary"
        _owns_the_centre(page, selector)
        page.wait_for_function(
            "(sel) => { const s = getComputedStyle(document.querySelector(sel));"
            " return s.color !== s.backgroundColor"
            " && document.getAnimations().length === 0; }", arg=selector)
        colours = page.eval_on_selector(
            selector, "e => { const s = getComputedStyle(e);"
            " return [s.color, s.backgroundColor]; }")
        lighter, darker = sorted((_luminance(_rgb(c)) for c in colours), reverse=True)
        assert (lighter + 0.05) / (darker + 0.05) >= 4.5, (lang, theme, colours)
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_user_pairs_a_frame_from_the_empty_state_and_lands_on_its_home(
        new_context, seeded, lang):
    server, seed = seeded
    context, page = _open(new_context, server, fx.USER_EMAIL, "/account", lang)
    try:
        text = TEXT[lang]
        page.locator("a.pair-link--primary").click()
        page.wait_for_url("**/pair-frame")
        page.locator("#pair-code").wait_for(state="visible")
        page.wait_for_function("() => document.readyState === 'complete'")
        assert page.locator("main h1").inner_text() == text["title"]
        assert page.locator("form.pair-form [name=owner_user_id], .pair-form select").count() == 0
        for selector in ("#pair-code", ".pair-form button[type=submit]", "a.pair-form__cancel"):
            assert _height(page, selector) >= MIN_TAP_PX, selector
        assert _no_sideways_scroll(page)
        page.fill("#pair-code", "kkkk-2222")
        page.locator(".pair-form button[type=submit]").click()
        page.locator(".pair-form .field-error").wait_for(state="visible")
        assert page.locator(".pair-form .toast").count() == 0
        assert page.locator(".pair-form .field-error").count() == 1
        assert text["refused"] in page.locator(".pair-form").inner_text()
        # Post/Redirect/Get: the refusal is its own page (a reload re-sends nothing), the
        # typed code is back in the field from a short-lived cookie and never in the address.
        assert page.url.endswith("/pair-frame?refused=1")
        assert page.input_value("#pair-code") == "KKKK-2222"
        assert "KKKK" not in page.url
        # It comes back once: the cookie is gone, so the next showing starts empty.
        assert [c for c in context.cookies() if c["name"] == "sp_pair_code"] == []
        # A reload shows a plain form: the error went with the code it blamed.
        page.reload()
        page.wait_for_function("() => document.readyState === 'complete'")
        page.locator("#pair-code").wait_for(state="visible")
        assert page.locator(".pair-form .field-error").count() == 0
        assert page.input_value("#pair-code") == ""
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator(".pair-form button[type=submit]").click()
        page.wait_for_url(HOME_URL)
        device = _device(server)
        assert device["owner_user_id"] == seed.user_id
        assert "/devices/%s/" % device["id"] in page.url
        page.locator('.toast-region--flash .toast, [role=status]').first.wait_for(
            state="visible")
        assert text["toast"] in page.locator("body").inner_text()
    finally:
        context.close()


def test_the_frame_popover_ends_with_an_add_a_frame_row_for_a_user(new_context, seeded):
    server, seed = seeded
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.add_device(
            conn, "aa:bb:cc:00:00:07", fx.SECRET_HASH, hardware.LEGACY_KEY,
            seed.owner_id, name="Garage", state_path="auto")
    finally:
        conn.close()
    context, page = _open(
        new_context, server, fx.OWNER_EMAIL, "/")
    try:
        open_menu(page)
        tiles = page.locator("ul.frame-menu__list > li")
        last = tiles.last.locator("a")
        assert last.get_attribute("href") == "/pair-frame"
        assert last.get_attribute("class").split() == ["frame-row", "frame-row--add"]
        _owns_the_centre(page, "ul.frame-menu__list > li:last-child a")
        assert _height(page, "ul.frame-menu__list > li:last-child a") >= 52
        last.click()
        page.wait_for_url("**/pair-frame")
        assert page.locator("main h1").inner_text() == "Add a frame"
    finally:
        context.close()


def test_the_flow_works_with_scripts_blocked(new_context, seeded):
    server, seed = seeded
    context, page = _open(
        new_context, server, fx.USER_EMAIL, "/account", java_script_enabled=False)
    try:
        page.locator("a.pair-link--primary").click()
        page.wait_for_url("**/pair-frame")
        page.fill("#pair-code", fx.FAKE_CODE)
        page.locator(".pair-form button[type=submit]").click()
        page.wait_for_url(HOME_URL)
        assert _device(server)["owner_user_id"] == seed.user_id
    finally:
        context.close()


@pytest.mark.parametrize("scripts", [True, False])
def test_a_refused_code_is_kept_so_only_the_typo_is_corrected(new_context, seeded, scripts):
    server, seed = seeded
    context, page = _open(
        new_context, server, fx.USER_EMAIL, "/pair-frame", java_script_enabled=scripts)
    try:
        wrong = fx.FAKE_CODE[:-1] + ("2" if fx.FAKE_CODE[-1] != "2" else "3")
        page.fill("#pair-code", wrong)
        page.locator(".pair-form button[type=submit]").click()
        page.locator(".pair-form .field-error").wait_for(state="visible")
        assert page.input_value("#pair-code") == wrong
        assert wrong not in page.url
        # Correcting the last symbol is all it takes.
        page.fill("#pair-code", page.input_value("#pair-code")[:-1] + fx.FAKE_CODE[-1])
        page.locator(".pair-form button[type=submit]").click()
        page.wait_for_url(HOME_URL)
        assert _device(server)["owner_user_id"] == seed.user_id
    finally:
        context.close()


def test_the_fleet_page_header_has_no_add_a_frame_button(new_context, seeded):
    server, _seed = seeded
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        pair = fx.admin_cookie(server.state_dir)
        name, value = pair.split("=", 1)
        context.add_cookies([{
            "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
            "sameSite": "Strict"}])
        page = context.new_page()
        page.goto(server.base_url() + "/fleet")
        page.locator("main").wait_for(state="visible")
        assert page.locator(".page-header a.page-header__action").count() == 0
        assert page.locator("a.frame-row--add").count() == 1
    finally:
        context.close()
