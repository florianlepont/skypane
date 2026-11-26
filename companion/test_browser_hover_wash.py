"""Real-browser checks of the hover wash (`--color-control-wash`): the fill under a hovered row
button is visible in Dark on the surfaces the buttons really sit on (read from painted pixels, not
from a mockup colour), the Light value stays exactly as it was, text on a hovered control keeps at
least 4.5:1, the focus ring does not depend on hover, a hover never changes a control's box, and
under reduced motion no animation runs. Four theme contexts: explicit Light, explicit Dark, Auto
with a dark scheme, Auto with a light scheme."""
import io

import animation_settle
import fleet_console_support as fx
import pytest
from PIL import Image

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import _assert_no_page_overflow, _login, seed_state_dir
from companion_app_server import session_cookie_for_state_dir
from server import history_db

pytestmark = pytest.mark.browser

LIGHT_WASH = "rgba(23,25,31,0.045)"
DARK_WASH = "rgba(241,243,246,0.08)"
# The Light hover step on a white card, 245 against 255, is the reference: Dark must show at least
# as much, and stay a hint rather than a boundary.
LIGHT_STEP = 1.08
HINT_CEILING = 1.5
AIR_FRANCE = "#airline-air-france"

CONSUMERS = (
    ("users", "tr.users-row .row-menu__toggle", None),
    ("users-open", "tr.users-row details[open] .row-menu__item", None),
    ("airlines", "label.airlines-act--icon >> visible=true", None),
    ("collection", ".collection-sort__option", ".collection-sort__option .collection-sort__row"),
)
COLOUR = """el => { const c = document.createElement('canvas'); c.width = c.height = 1;
  const x = c.getContext('2d', {willReadFrequently: true}); x.fillStyle = '#000';
  x.fillStyle = getComputedStyle(el).color; x.fillRect(0, 0, 1, 1);
  const d = x.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; }"""


def _airline_seed(state_dir):
    from datetime import datetime, timedelta, timezone
    seed_airline_editor(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, code in enumerate(("A320", "A20N", "A333")):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(hours=index + 1)).isoformat(), hex="hw%04d" % index,
                callsign="AFR9%02d" % index, aircraft_type=code, confirmed_state="departing",
                airline="Air France")


@pytest.fixture(scope="module")
def users_server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_users)


@pytest.fixture(scope="module")
def airlines_server(module_app_server_factory):
    return module_app_server_factory(seed=_airline_seed, fake_providers=True)


@pytest.fixture(scope="module")
def collection_server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir)


def _context(new_context, server, scheme, lang="en", width=390, admin=False):
    context = new_context(
        viewport={"width": width, "height": 844}, color_scheme=scheme, reduced_motion="reduce")
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    if admin:
        name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
        context.add_cookies([{
            "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
            "sameSite": "Strict"}])
    return context


def _open(new_context, server, scheme, path, lang="en", width=390):
    context = _context(new_context, server, scheme, lang, width, admin=path == "/users")
    page = context.new_page()
    if path != "/users":
        _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    return context, page


def _prepare(page, name):
    if name == "users-open":
        page.locator("tr.users-row .row-menu__toggle").first.click()
    elif name == "airlines":
        chevron = page.locator(AIR_FRANCE + " .airlines-expand > summary")
        chevron.scroll_into_view_if_needed()
        chevron.click()
        page.locator(AIR_FRANCE + " .airlines-subrow").first.wait_for(state="visible")
    elif name == "collection":
        page.locator(".collection-sort > summary").click()
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)


def _pixel(page, box):
    png = page.screenshot(clip={
        "x": box["x"] + box["width"] * 0.5, "y": box["y"] + 3, "width": 1, "height": 1})
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((0, 0))


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _ratio(one, two):
    high, low = sorted((_luminance(one), _luminance(two)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _wash(page):
    return page.evaluate(
        "() => getComputedStyle(document.documentElement).getPropertyValue('--color-control-wash')"
    ).replace(" ", "")


@pytest.mark.parametrize("scheme,attribute,expected", (
    ("light", None, LIGHT_WASH), ("dark", None, DARK_WASH),
    ("dark", "light", LIGHT_WASH), ("light", "dark", DARK_WASH)),
    ids=("auto-light", "auto-dark", "explicit-light", "explicit-dark"))
def test_the_token_resolves_per_theme_context_and_light_is_unchanged(
        new_context, users_server, scheme, attribute, expected):
    context, page = _open(new_context, users_server, scheme, "/users")
    try:
        if attribute:
            page.evaluate("a => document.documentElement.setAttribute('data-ui-theme', a)", attribute)
        assert _wash(page) == expected
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("name,hover,measured", CONSUMERS, ids=[c[0] for c in CONSUMERS])
def test_the_hover_fill_shows_on_the_real_surface_and_text_stays_readable(
        new_context, users_server, airlines_server, collection_server, name, hover, measured, theme):
    server, path = {
        "users": (users_server, "/users"), "users-open": (users_server, "/users"),
        "airlines": (airlines_server, "/airlines/manage"),
        "collection": (collection_server, "/airlines")}[name]
    context, page = _open(new_context, server, theme, path)
    try:
        _prepare(page, name)
        target = page.locator(hover).first
        shown = page.locator(measured or hover).first
        target.evaluate("e => e.scrollIntoView({block: 'center'})")
        page.mouse.move(2, 2)
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        box = shown.bounding_box()
        resting = _pixel(page, box)
        target.hover(force=True)
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        hovered = _pixel(page, box)
        step = _ratio(resting, hovered)
        assert LIGHT_STEP <= step < HINT_CEILING, (name, theme, resting, hovered, step)
        red, green, blue, alpha = target.evaluate(COLOUR)
        ink = tuple(alpha * c + (1 - alpha) * b for c, b in zip((red, green, blue), hovered))
        assert _ratio(ink, hovered) >= 4.5, (name, theme, ink, hovered)
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_the_focus_ring_is_the_same_hovered_or_not(new_context, users_server, theme):
    context, page = _open(new_context, users_server, theme, "/users")
    try:
        toggle = page.locator("tr.users-row .row-menu__toggle").first
        ring = """el => { const s = getComputedStyle(el);
          return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.outlineOffset]; }"""
        page.mouse.move(2, 2)
        toggle.evaluate("e => e.focus({focusVisible: true})")
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        plain = toggle.evaluate(ring)
        toggle.hover(force=True)
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        assert toggle.evaluate(ring) == plain
        assert plain[0] != "none"
    finally:
        context.close()


@pytest.mark.parametrize("theme", ("light", "dark"))
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("name,path", (("users", "/users"), ("airlines", "/airlines/manage")))
def test_at_360px_a_hover_changes_no_box_and_nothing_scrolls_sideways(
        new_context, users_server, airlines_server, name, path, lang, theme):
    server = users_server if name == "users" else airlines_server
    context, page = _open(new_context, server, theme, path, lang, width=360)
    try:
        _prepare(page, name)
        assert not _assert_no_page_overflow(page, name, 360)
        target = page.locator(
            "tr.users-row .row-menu__toggle" if name == "users"
            else "label.airlines-act--icon >> visible=true").first
        target.evaluate("e => e.scrollIntoView({block: 'center'})")
        page.mouse.move(2, 2)
        before = target.bounding_box()
        target.hover(force=True)
        page.wait_for_function(animation_settle.SETTLED, timeout=15000)
        after = target.bounding_box()
        assert before == after and before["width"] >= 44 - 0.5 and before["height"] >= 44 - 0.5
        assert page.evaluate(
            "() => document.getAnimations().filter(a => a.playState === 'running').length") == 0
    finally:
        context.close()
