"""Real-browser checks of the product names: one simple name per page, the same in the
navigation, the page title and the heading, in English and French, in both themes, at 360 and
1280 px. Fleet/Flotte, Admin, Activity/Activite (the audit page), Software/Logiciel (a frame's
firmware tile) and Last contact/Dernier contact (its connection tile); the older words no
longer label any of them. Nothing overflows sideways."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, _assert_no_page_overflow, _login, _set_ui_theme)

pytestmark = pytest.mark.browser

NAMES = {
    "en": {"fleet": "Fleet", "admin": "Admin", "activity": "Activity",
           "software": "Software", "contact": "Last contact"},
    "fr": {"fleet": "Flotte", "admin": "Admin", "activity": "Activité",
           "software": "Logiciel", "contact": "Dernier contact"},
}
OLD = {
    "en": {"fleet": "Frames", "admin": "Administration", "activity": "Audit log",
           "software": "Firmware", "contact": "Connection"},
    "fr": {"fleet": "Cadres", "admin": "Administration", "activity": "Journal d’audit",
           "software": "Micrologiciel", "contact": "Connexion"},
}
VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))


_SEEDED = {}


def _seed(state_dir):
    _SEEDED["live"] = fx.seed_fleet(state_dir).live_id


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _open(new_context, server, path, viewport, lang, scheme):
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    _set_ui_theme(page, scheme)
    return context, page


def _live_path(_server):
    return "/fleet?frame=%s" % _SEEDED["live"]


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_fleet_list_heading_is_the_navigation_name_and_the_title_begins_with_it(
        new_context, server, name, viewport, lang, scheme):
    context, page = _open(new_context, server, "/fleet", viewport, lang, scheme)
    where = "fleet/%s/%s/%s" % (name, lang, scheme)
    word = NAMES[lang]["fleet"]
    try:
        if viewport["width"] < 960:
            heading = page.locator("main h1:visible").inner_text().strip()
            nav = page.locator(".tab-bar a[aria-current='page']").inner_text().strip()
        else:
            heading = page.locator(".fleet-list__title h2:visible").inner_text().strip()
            nav = page.locator(".sidebar-nav a[aria-current='page']").inner_text().strip()
        assert heading == word, (where, heading)
        assert nav.startswith(word), (where, nav)
        assert page.title().startswith(word), (where, page.title())
        assert OLD[lang]["fleet"] not in page.locator("main").inner_text(), where
        assert not _assert_no_page_overflow(page, where, viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_console_sidebar_says_admin_and_activity(new_context, server, lang, scheme):
    context, page = _open(new_context, server, "/users", VIEWPORT_DESKTOP, lang, scheme)
    where = "sidebar/%s/%s" % (lang, scheme)
    try:
        sidebar = page.locator(".sidebar-nav").inner_text()
        lines = [line.strip() for line in sidebar.splitlines() if line.strip()]
        assert NAMES[lang]["admin"] in lines, (where, lines)
        assert NAMES[lang]["activity"] in lines, (where, lines)
        assert OLD[lang]["admin"] not in sidebar, (where, lines)
        assert OLD[lang]["activity"] not in sidebar, (where, lines)
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_audit_page_is_named_activity_in_its_heading_and_title(
        new_context, server, name, viewport, lang, scheme):
    context, page = _open(new_context, server, "/audit", viewport, lang, scheme)
    where = "audit/%s/%s/%s" % (name, lang, scheme)
    word = NAMES[lang]["activity"]
    try:
        assert page.locator("main h1:visible").inner_text().strip() == word, where
        assert page.title().startswith(word), (where, page.title())
        assert OLD[lang]["activity"] not in page.title(), where
        assert not _assert_no_page_overflow(page, where, viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_frames_tiles_say_software_and_last_contact(
        new_context, server, name, viewport, lang, scheme):
    context, page = _open(new_context, server, _live_path(server), viewport, lang, scheme)
    where = "tiles/%s/%s/%s" % (name, lang, scheme)
    try:
        tiles = page.locator("main .fleet-tile").all_inner_texts()
        text = "\n".join(tiles)
        assert NAMES[lang]["software"] in text, (where, tiles)
        assert NAMES[lang]["contact"] in text, (where, tiles)
        assert OLD[lang]["software"] not in text, (where, tiles)
        assert OLD[lang]["contact"] not in text, (where, tiles)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_components_status_sample_follows_the_connection_tile_name(
        new_context, server, lang):
    context, page = _open(new_context, server, "/components", VIEWPORT_DESKTOP, lang, "light")
    try:
        text = page.locator("main").inner_text()
        assert NAMES[lang]["contact"] in text
    finally:
        context.close()
