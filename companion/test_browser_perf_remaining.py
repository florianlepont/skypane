"""Real-browser checks of the page-speed work on the Location map and list, the airline
editor, the tab bar's first-paint marker and the phone glass: the tab bar precedes the page
body, the airport list is filled from the map's catalogue, only pins near the screen are
elements, the editor opens an airline's aircraft types on demand and a phone's group
surfaces carry no blur."""
import pytest

from companion import auth, layout
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_PHONE, _login, seed_state_dir)
from place_map_support import Hosts
from server import device_config

pytestmark = pytest.mark.browser

READY = "() => document.documentElement.classList.contains('map-ready')"
TILES_LOADED = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=False)


def test_the_tab_bar_and_its_marker_come_before_the_page_body(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'")
    order = page.evaluate("""() => {
      const marker = document.getElementById('tab-bar-end');
      const main = document.querySelector('main');
      const bar = document.querySelector('nav.tab-bar');
      const expect = document.querySelector('link[rel=expect]');
      return {
        markerBeforeMain: !!(marker.compareDocumentPosition(main) & Node.DOCUMENT_POSITION_FOLLOWING),
        barBeforeMarker: !!(bar.compareDocumentPosition(marker) & Node.DOCUMENT_POSITION_FOLLOWING),
        target: expect && expect.getAttribute('href'),
        fixed: getComputedStyle(bar).position,
        top: bar.getBoundingClientRect().top / window.innerHeight,
        bottom: bar.getBoundingClientRect().bottom <= window.innerHeight};
    }""")
    assert order["markerBeforeMain"] and order["barBeforeMarker"], order
    assert order["target"] == "#tab-bar-end" and order["fixed"] == "fixed", order
    assert order["bottom"] and order["top"] > 0.8, order
    context.close()


def test_the_airport_list_is_filled_from_the_maps_catalogue_and_still_filters(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(
        "() => document.querySelectorAll('li.place-airport').length > 100", timeout=10000)
    state = page.evaluate("""() => {
      const rows = JSON.parse(document.getElementById('place-map').getAttribute('data-airports'));
      const items = [...document.querySelectorAll('ul[data-airport-fill] li.place-airport')];
      const first = items[0].querySelector('a');
      return {catalogue: rows.length, listed: items.length,
        sameOrder: items.every((li, i) => li.querySelector('a').dataset.icao === rows[i][0]),
        count: document.querySelector('[data-filter-count]').textContent,
        href: first.getAttribute('href'), name: first.querySelector('.place-airport__name').textContent,
        folded: items[0].getAttribute('data-filter-text'),
        noscriptLists: document.querySelectorAll('noscript').length > 0};
    }""")
    assert state["listed"] == state["catalogue"] and state["sameOrder"], state
    assert state["count"].startswith("%d of %d" % (state["catalogue"], state["catalogue"])), state
    assert "airport=" in state["href"] and state["href"].endswith("#airport-runways"), state
    assert state["folded"] == state["folded"].lower() and state["name"].lower() in state["folded"]
    page.evaluate(
        "() => { const f = document.getElementById('airport-filter'); f.value = 'orly';"
        " f.dispatchEvent(new Event('input', {bubbles: true})); }")
    page.wait_for_function(
        "() => [...document.querySelectorAll('li.place-airport')].filter(li => !li.hidden)"
        ".length < 10")
    visible = page.evaluate(
        "() => [...document.querySelectorAll('li.place-airport')].filter(li => !li.hidden)"
        ".map(li => li.querySelector('a').dataset.icao)")
    assert "LFPO" in visible, visible
    context.close()


def test_zoomed_in_only_the_pins_near_the_screen_are_elements(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection?mode=runway&airport=LFPO")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(TILES_LOADED, timeout=15000)
    page.wait_for_function(
        "() => document.querySelectorAll('.leaflet-marker-icon').length > 0", timeout=10000)
    near = page.evaluate("() => document.querySelectorAll('.leaflet-marker-icon').length")
    total = page.evaluate(
        "() => JSON.parse(document.getElementById('place-map').getAttribute('data-airports')).length")
    assert 0 < near < total / 4, (near, total)
    followed = page.locator(".place-dot--selected .place-dot__mark[data-icao='LFPO']")
    assert followed.count() == 1
    context.close()


def test_a_phone_group_has_no_blur_and_a_desktop_group_keeps_the_glass(
        new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    seen = {}
    for name, viewport in (("phone", VIEWPORT_PHONE), ("desktop", VIEWPORT_DESKTOP)):
        context = new_context(viewport=viewport)
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        seen[name] = page.evaluate("""() => {
          const el = document.querySelector('.group');
          const probe = document.createElement('div');
          probe.className = 'group';
          document.body.appendChild(probe);
          const s = getComputedStyle(probe);
          const out = {blur: s.backdropFilter || s.webkitBackdropFilter, bg: s.backgroundColor};
          probe.remove();
          return out;
        }""")
        context.close()
    assert seen["phone"]["blur"] == "none", seen
    assert "blur" in seen["desktop"]["blur"], seen
    assert seen["phone"]["bg"] == seen["desktop"]["bg"], seen


@pytest.fixture(scope="module")
def editor_server(module_app_server_factory):
    return module_app_server_factory(seed=seed_airline_editor, fake_providers=True)


def test_the_editor_opens_an_airlines_types_on_demand_and_keeps_them_filterable(
        new_context, editor_server):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": editor_server.base_url()}])
    page = context.new_page()
    _login(page, editor_server.base_url())
    page.goto(editor_server.base_url() + "/airlines/manage")
    page.wait_for_function("() => document.readyState === 'complete'")
    group = 'tbody.airline-group:has(input[value="Transavia France"])'
    page.locator(group).wait_for(state="attached")
    before = page.evaluate(
        "g => ({rows: document.querySelectorAll('.airlines-subrow').length,"
        " pending: document.querySelectorAll('tbody[data-types-src]').length,"
        " templates: document.querySelectorAll('template.airlines-types').length,"
        " own: document.querySelector(g).querySelectorAll('.airlines-subrow').length})", group)
    assert before["rows"] == 0 and before["templates"] == 0 and before["own"] == 0, before
    assert before["pending"] > 0, before
    requested = []
    page.on("request", lambda request: requested.append(request.url) if "types=" in request.url else None)
    page.locator(group + " .airlines-expand > summary").click()
    page.wait_for_function(
        "g => document.querySelector(g).querySelectorAll('.airlines-subrow').length >= 2", arg=group)
    rows = page.locator(group + " .airlines-subrow")
    rows.first.wait_for(state="visible")
    assert rows.first.locator("th").inner_text().startswith("A320")
    assert page.locator(group + "[data-types-src]").count() == 0
    assert len(requested) == 1, requested
    # The filter still finds an airline by the aircraft types it holds.
    page.locator("[data-filter-input]").fill("b738")
    page.wait_for_function(
        "g => !document.querySelector(g).hidden", arg=group)
    context.close()
