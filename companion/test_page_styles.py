"""Each page links the core stylesheet and the area sheets of its own family, in that order; a
page the map does not name links every area sheet, so it never lacks a rule."""
import pytest

from companion import page_styles, static_files
from companion.test_browser_ux_helpers import seed_state_dir
from companion_app_server import get, login
from companion_markup import parse_html


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir)


def _sheets(server, route):
    cookie = login(server)
    status, _headers, body = get(server, route, cookie=cookie)
    assert status == 200, route
    doc = parse_html(body.decode("utf-8"))
    return [n.attrs["href"].split("?", 1)[0] for n in doc.select('link[rel="stylesheet"]')]


@pytest.mark.parametrize("route,sheets", [
    ("/", ["home"]),
    ("/flights", ["c-lists", "flights"]),
    ("/airlines", ["c-lists", "airlines"]),
    ("/airlines/manage", ["c-lists", "airlines"]),
    ("/display", ["c-console", "c-lists", "display"]),
    ("/display/special-looks", ["c-console", "c-lists", "display"]),
    ("/account", ["c-console", "c-lists", "admin"]),
    ("/users", ["c-console", "c-lists", "admin"]),
    ("/fleet", ["c-console", "c-lists", "display", "admin"]),
])
def test_a_page_links_the_core_sheet_its_component_sheets_and_its_own_area(server, route, sheets):
    assert _sheets(server, route) == ["/static/style.css"] + [
        "/static/style-%s.css" % name for name in sheets]


def test_the_home_page_links_no_component_sheet(server):
    assert not [href for href in _sheets(server, "/") if "/style-c-" in href]


def test_a_device_scoped_path_links_the_same_sheets():
    assert page_styles.areas_for("/devices/d_1234/flights") == ("c-lists", "flights")
    assert page_styles.areas_for("/devices/d_1234") == ("home",)


def test_an_unnamed_path_links_every_area_sheet():
    assert page_styles.areas_for("/components") == static_files.AREA_STYLE_NAMES
    assert page_styles.areas_for("/no/such/page") == static_files.AREA_STYLE_NAMES


def test_every_area_sheet_is_served_as_versioned_css(server):
    cookie = login(server)
    for route in static_files.AREA_STYLE_ROUTES:
        status, headers, body = get(server, route, cookie=cookie)
        assert status == 200 and headers["Content-Type"].startswith("text/css") and body
        assert static_files.asset_version(route)


def test_no_request_path_links_no_area_sheet():
    assert page_styles.areas_for("") == ()
    assert page_styles.area_hrefs("") == ()


def test_an_error_page_for_a_known_page_path_links_the_core_sheet_only(server):
    cookie = login(server)
    status, _headers, body = get(server, "/no-such-page-anywhere", cookie=cookie)
    assert status == 404
    doc = parse_html(body.decode("utf-8"))
    assert [n.attrs["href"].split("?", 1)[0] for n in doc.select('link[rel="stylesheet"]')] == [
        "/static/style.css"]
