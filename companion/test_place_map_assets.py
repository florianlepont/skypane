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
    "/", "/display", "/flights", "/airlines", "/fleet", "/credits")


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


def _route_of(url):
    """The route part of a versioned asset URL (the `?v=` token dropped)."""
    return url.split("?", 1)[0] if url else url


def _script_srcs(doc):
    return [_route_of(node.attrs.get("src")) for node in doc.select("script[src]")]


def test_the_detection_page_links_the_library_stylesheet_after_the_shared_one(server):
    hrefs = [_route_of(n.attrs.get("href")) for n in _page(server, "/detection").select(
        'link[rel="stylesheet"]')]
    assert hrefs == ["/static/style.css", "/static/style-place.css", LEAFLET_CSS]


def test_the_starter_is_deferred_and_names_the_library_before_the_glue(server):
    doc = _page(server, "/detection")
    srcs = _script_srcs(doc)
    assert layout.PLACE_START_SCRIPT_SRC in srcs
    assert LEAFLET_JS not in srcs and PLACE_MAP_JS not in srcs
    for node in doc.select("script[src]"):
        if _route_of(node.attrs.get("src")) == layout.PLACE_START_SCRIPT_SRC:
            assert "defer" in node.attrs
    attrs = doc.select("#place-map")[0].attrs
    assert _route_of(attrs["data-leaflet-src"]) == LEAFLET_JS
    assert _route_of(attrs["data-map-src"]) == PLACE_MAP_JS
    assert list(attrs).index("data-leaflet-src") < list(attrs).index("data-map-src")


@pytest.mark.parametrize("route", OTHER_ROUTES)
def test_no_other_page_links_the_map_files(server, route):
    doc = _page(server, route)
    assert LEAFLET_JS not in _script_srcs(doc)
    assert PLACE_MAP_JS not in _script_srcs(doc)
    hrefs = [_route_of(n.attrs.get("href")) for n in doc.select('link[rel="stylesheet"]')]
    assert hrefs[0] == "/static/style.css" and LEAFLET_CSS not in hrefs


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


def test_the_notice_container_is_in_the_panel_and_starts_hidden(server):
    doc = _page(server, "/detection")
    notice = doc.select("#place-notice")[0]
    assert "hidden" in notice.attrs
    assert doc.select(".place-panel #place-notice")


def test_the_container_carries_the_search_limits_and_the_position_words(server):
    attrs = _page(server, "/detection").select("#place-map")[0].attrs
    assert (attrs["data-search-min"], attrs["data-search-max"], attrs["data-search-lock-ms"]) == (
        "3", "120", "1500")
    assert attrs["data-t-locate-timeout"] == (
        "Finding your position took too long. Try again, or search a place.")
    assert attrs["data-t-nearest"] == "Nearest airport: %s, %d km. Follow its runway?"
    assert attrs["data-t-follow"] == "Follow %s"


def test_the_page_links_only_the_starter_and_the_map_names_the_scripts_it_starts(server):
    doc = _page(server, "/detection")
    linked = [n.attrs["src"].split("?", 1)[0] for n in doc.select("script[src]")]
    assert layout.PLACE_START_SCRIPT_SRC in linked
    for late in (layout.LEAFLET_SCRIPT_SRC, layout.PLACE_SEARCH_SCRIPT_SRC,
                 layout.PLACE_MAP_SCRIPT_SRC, layout.PLACE_CARD_SCRIPT_SRC,
                 layout.PLACE_AIRPORT_LIST_SCRIPT_SRC):
        assert late not in linked
    attrs = doc.select("#place-map")[0].attrs
    named = [attrs["data-%s-src" % name].split("?", 1)[0]
             for name in ("leaflet", "search", "map", "card", "airports")]
    assert named == [
        layout.LEAFLET_SCRIPT_SRC, layout.PLACE_SEARCH_SCRIPT_SRC, layout.PLACE_MAP_SCRIPT_SRC,
        layout.PLACE_CARD_SCRIPT_SRC, layout.PLACE_AIRPORT_LIST_SCRIPT_SRC]
    assert all("?v=" in attrs["data-%s-src" % name] for name in ("leaflet", "map", "airports"))


def test_the_position_words_are_french_on_the_french_page(server):
    attrs = _page(server, "/detection", lang="fr").select("#place-map")[0].attrs
    assert attrs["data-t-locating"] == "Recherche de votre position…"
    assert attrs["data-t-follow"] == "Suivre %s"
    assert attrs["data-t-search-failed"].startswith("La recherche n’est pas disponible")


def test_the_search_form_limits_the_typed_text_to_the_script_limit(server):
    doc = _page(server, "/detection")
    assert doc.select("#place-search")[0].attrs["maxlength"] == "120"
    assert doc.select(".place-float #place-results")
    assert doc.select(".place-panel #place-nearest")
