"""Every empty-state block outside the filter empty state uses the compact scale: an
Emphasis-sized heading and a label-sized body, never the 22 px serif heading form."""
import pytest

import companion_app_server
import companion_markup
from companion import auth
from companion import layout
from companion.test_device_helpers import get, start_fleet_app

PAGES = ("/", "/health", "/audit", "/update", "/flights", "/account")
# The Location page has no empty state of its own: the map is its empty canvas. Its airport list's
# "nothing matches" state is the one left to measure.
FILTERED_PAGES = ("/detection?q=zzzzqqq",)


def _empty_states(html):
    root = companion_markup.parse_html(html)
    main = root.select_one("main")
    assert main is not None
    return main.select(".empty-state")


def _assert_compact_or_filter(blocks, where):
    for block in blocks:
        classes = block.attrs.get("class", "").split()
        if "empty-state--filter" in classes:
            continue
        heading = block.select_one(".empty-state__heading")
        assert "empty-state--compact" in classes, "%s: large empty state %s" % (where, classes)
        assert "text-body" in heading.attrs["class"].split(), where
        assert "text-heading" not in heading.attrs["class"].split(), where
        assert "text-label" in block.select_one(".empty-state__body").attrs["class"].split()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("path", PAGES + FILTERED_PAGES)
def test_empty_pages_use_the_compact_scale(make_app_server, path, lang):
    server = make_app_server()
    cookie = "%s; %s=%s" % (companion_app_server.login(server), auth.UI_LANG_COOKIE_NAME, lang)
    code, _, body = companion_app_server.get(server, path, cookie=cookie)
    assert code == 200
    blocks = _empty_states(body.decode("utf-8"))
    assert blocks or path == "/health", "%s shows no empty state to measure" % path
    _assert_compact_or_filter(blocks, path)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_locations_page_a_refused_submission_shows_is_compact(make_app_server, lang):
    server = make_app_server()
    cookie = "%s; %s=%s" % (companion_app_server.login(server), auth.UI_LANG_COOKIE_NAME, lang)
    code, _, body = companion_app_server.http_request(
        server.url("/locations/add"), "POST", cookie=cookie,
        data=companion_app_server.with_csrf(cookie, {"name": " "}))
    assert code == 400
    blocks = _empty_states(body.decode("utf-8"))
    assert blocks, "the refused page shows no empty state to measure"
    _assert_compact_or_filter(blocks, "/locations (refused submission)")


def test_health_coverage_gaps_empty_state_is_compact(make_app_server):
    server = make_app_server()
    cookie = companion_app_server.login(server)
    _, _, body = companion_app_server.get(server, "/health", cookie=cookie)
    html = body.decode("utf-8")
    section = companion_markup.parse_html(html).select_one("#unresolved-prefixes")
    blocks = section.select(".empty-state")
    assert blocks
    _assert_compact_or_filter(blocks, "coverage gaps")


def test_a_frame_that_never_checked_in_gets_the_compact_health_empty_state(make_app_server):
    app = start_fleet_app(make_app_server)
    device = app.fleet.dev_a
    _, _, html = get(app, "/devices/%s/health" % device.id)
    assert "This frame has not checked in yet" in html
    blocks = _empty_states(html)
    assert blocks
    _assert_compact_or_filter(blocks, "device health")


def test_the_audit_filter_empty_state_keeps_its_form(make_app_server):
    server = make_app_server()
    cookie = companion_app_server.login(server)
    _, _, body = companion_app_server.get(
        server, "/audit?category=pairing", cookie=cookie)
    html = body.decode("utf-8")
    blocks = _empty_states(html)
    assert len(blocks) == 1
    assert "empty-state--filter" in blocks[0].attrs["class"].split()
    assert "empty-state--compact" not in blocks[0].attrs["class"].split()


def test_a_data_table_without_rows_falls_back_to_the_compact_empty_state():
    blocks = _empty_states_of(layout.data_table(["A", "B"], []))
    assert len(blocks) == 1
    _assert_compact_or_filter(blocks, "data table fallback")


def test_a_device_history_page_without_flights_is_compact(make_app_server):
    app = start_fleet_app(make_app_server)
    _, _, html = get(app, "/devices/%s/flights" % app.fleet.dev_a.id)
    blocks = _empty_states(html)
    assert blocks
    _assert_compact_or_filter(blocks, "device history")


def _empty_states_of(fragment):
    return companion_markup.parse_html(fragment).select(".empty-state")
