"""What the Location and detection page links and serves for the map: the
library and its stylesheet and the first-party script on this page only, the
words the script shows (in both languages), and no library marker image
request path.
"""
import pytest

from companion import layout
from companion.test_browser_ux_helpers import seed_state_dir
from companion_app_server import get, login
from companion_markup import parse_html

LEAFLET_JS = "/static/vendor/leaflet/leaflet.js"
LEAFLET_CSS = "/static/vendor/leaflet/leaflet.css"
PLACE_MAP_JS = "/static/place-map.js"
OTHER_ROUTES = (
    "/", "/display", "/flights", "/airlines", "/health", "/device", "/credits")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir)


def _page(server, route, lang=None):
    cookie = login(server)
    if lang:
        cookie += "; sp_ui_lang=" + lang
    status, _headers, body = get(server, route, cookie=cookie)
    assert status == 200, route
    return parse_html(body.decode("utf-8"))


def _script_srcs(doc):
    return [node.attrs.get("src") for node in doc.select("script[src]")]


def test_the_detection_page_links_the_library_stylesheet_after_the_shared_one(server):
    hrefs = [n.attrs.get("href") for n in _page(server, "/detection").select(
        'link[rel="stylesheet"]')]
    assert hrefs == ["/static/style.css", LEAFLET_CSS]


def test_the_library_loads_before_the_glue_and_both_are_deferred(server):
    doc = _page(server, "/detection")
    srcs = _script_srcs(doc)
    assert LEAFLET_JS in srcs and PLACE_MAP_JS in srcs
    assert srcs.index(LEAFLET_JS) < srcs.index(PLACE_MAP_JS)
    for node in doc.select("script[src]"):
        if node.attrs.get("src") in (LEAFLET_JS, PLACE_MAP_JS):
            assert "defer" in node.attrs


@pytest.mark.parametrize("route", OTHER_ROUTES)
def test_no_other_page_links_the_map_files(server, route):
    doc = _page(server, route)
    assert LEAFLET_JS not in _script_srcs(doc)
    assert PLACE_MAP_JS not in _script_srcs(doc)
    hrefs = [n.attrs.get("href") for n in doc.select('link[rel="stylesheet"]')]
    assert hrefs == ["/static/style.css"]


def test_the_glue_script_is_served_publicly_as_javascript(server):
    from companion_app_server import http_request
    status, headers, body = http_request(server.base_url() + PLACE_MAP_JS)
    assert status == 200
    assert headers["Content-Type"].split(";")[0] == "text/javascript"
    assert b"tile.openstreetmap.org" in body


def test_the_map_container_hands_the_script_its_words_in_english(server):
    attrs = _page(server, "/detection").select("#place-map")[0].attrs
    assert attrs["data-t-attribution"] == "© OpenStreetMap contributors"
    assert attrs["data-t-pin-placed"] == "Pin placed at %s, %s"
    assert attrs["data-t-tiles-failed"].startswith("The map pictures could not load")
    assert attrs["data-t-zoom-in"] == "Zoom in"


def test_the_map_container_hands_the_script_its_words_in_french(server):
    attrs = _page(server, "/detection", lang="fr").select("#place-map")[0].attrs
    assert attrs["data-t-attribution"] == "© contributeurs d’OpenStreetMap"
    assert attrs["data-t-pin-placed"] == "Repère placé à %s, %s"
    assert attrs["data-t-zoom-out"] == "Dézoomer"


def test_the_pin_glyph_is_in_the_sprite_and_the_whitelist(server):
    assert "icon-pin" in layout.ICON_IDS
    doc = _page(server, "/detection")
    assert doc.select("symbol#icon-pin")


def test_the_notice_container_is_in_the_card_and_starts_hidden(server):
    doc = _page(server, "/detection")
    notice = doc.select("#place-notice")[0]
    assert "hidden" in notice.attrs
    assert doc.select(".place-card--map #place-notice")
