"""Real-browser checks of two hard rules of the design system on the served pages, at 360 and
1280 px in English and French: every visible form field has an accessible name (a visually
hidden `<label for>` counts, as it does for a screen reader), and the stand-alone links of the
Components page are 44px targets."""
import re

import animation_settle
import pytest

import fleet_console_support as fx
from companion import auth
from companion_app_server import session_cookie_for_state_dir
from companion.test_browser_ux_helpers import _assert_hit_target
import companion.test_view_pages_helpers as vp

pytestmark = pytest.mark.browser

VIEWPORTS = {"360": {"width": 360, "height": 800}, "1280": {"width": 1280, "height": 900}}
LANGS = ("en", "fr")
WIDTHS = ("360", "1280")
SETTLED = animation_settle.SETTLED

# Marks every visible text-like field (a field a person can type into or pick a file with);
# radios, checkboxes, hidden inputs and visually hidden fields are not what a person meets.
MARK_FIELDS = """() => {
  let n = 0;
  for (const el of document.querySelectorAll('input, textarea, select')) {
    if (el.matches('[type=hidden], [type=radio], [type=checkbox]')) continue;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    if (r.width < 2 || r.height < 2 || s.visibility === 'hidden') continue;
    if (el.closest('[hidden], dialog:not([open]), .visually-hidden, [inert]')) continue;
    el.setAttribute('data-name-probe', String(n++));
  }
  return n;
}"""

# An aria snapshot line is `- role "name"`: the quoted part is the accessible name Chrome computed.
NAMED = re.compile(r'^- \w+ "[^"]+"')

# page id -> (server fixture, path). The Location page is only complete once its map runs.
PAGES = {
    "flights": ("flights_server", "/flights"),
    "airlines": ("flights_server", "/airlines"),
    "location": ("flights_server", "/detection"),
    "editor": ("flights_server", "/airlines/manage"),
    "components": ("flights_server", "/components"),
    "frame-settings": ("fleet_server", "/fleet?frame={owned}&tab=settings"),
}


@pytest.fixture(scope="module")
def flights_server(module_app_server_factory):
    return module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)


@pytest.fixture(scope="module")
def fleet_server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_fleet)


def _owned_frame_id(server):
    from server import fleet_db
    conn = fleet_db.connect(server.state_dir)
    try:
        return conn.execute("SELECT id FROM devices WHERE name = 'Kitchen'").fetchone()[0]
    finally:
        conn.close()


def _open(new_context, server, path, width, lang):
    context = new_context(viewport=VIEWPORTS[width])
    name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + path)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
@pytest.mark.parametrize("page_id", sorted(PAGES))
def test_every_visible_form_field_has_an_accessible_name(
        request, new_context, page_id, width, lang):
    fixture, path = PAGES[page_id]
    server = request.getfixturevalue(fixture)
    if "{owned}" in path:
        path = path.format(owned=_owned_frame_id(server))
    context, page = _open(new_context, server, path, width, lang)
    try:
        if page_id == "location":
            page.wait_for_function("() => document.documentElement.classList.contains('map-ready')")
        count = page.evaluate(MARK_FIELDS)
        assert count > 0, "no visible form field on %s: the check would measure nothing" % path
        unnamed = []
        for index in range(count):
            field = page.locator('[data-name-probe="%d"]' % index)
            snapshot = field.aria_snapshot().strip()
            if not NAMED.match(snapshot):
                unnamed.append(field.evaluate("el => el.outerHTML.slice(0, 120)"))
        assert not unnamed, unnamed
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("width", WIDTHS)
def test_components_back_to_index_links_are_forty_four_pixel_targets(
        new_context, flights_server, width, lang):
    context, page = _open(new_context, flights_server, "/components", width, lang)
    try:
        slugs = page.evaluate(
            "() => [...document.querySelectorAll('.components-family')].map(f => f.id)")
        assert slugs, "no family on the Components page"
        for slug in slugs:
            _assert_hit_target(
                page, "#%s .components-family__top a" % slug, "Back to the index in %s" % slug)
    finally:
        context.close()
