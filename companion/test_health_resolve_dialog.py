"""The System view no longer lists unresolved prefixes or opens a resolve dialog (the Airlines table
resolves them in place). Route checks against a real server for the return target the resolve
flow still accepts (an allow-list, never an open redirect) and for its refusals. Nothing here
reads production source text.
"""
import re
import urllib.parse

import pytest

import companion.test_status_pages_helpers as shp
from companion import resolve_dialog
from companion_app_server import http_request, login, with_csrf, with_csrf_part
from server.plane import manual_resolutions

PANEL_ATTR = re.compile(r'(data-view-panel-[a-z-]+)="([^"]*)"')
SEEN = "2026-01-01T10:00:00+00:00"
REGISTRY = {
    "QXA": {"count": 5, "first_seen": SEEN, "last_seen": SEEN, "example_callsign": "QXA123"},
    "QXB": {"count": 2, "first_seen": SEEN, "last_seen": SEEN, "example_callsign": "QXB456"},
}


def _seed(state_dir):
    shp.seed_unresolved_prefixes(state_dir, REGISTRY)


def _resolve_links(page, prefix):
    pattern = r'<a href="/airlines/manage\?resolve=%s" [^>]*>' % prefix
    return re.findall(pattern, page)


def _panel_attrs(tag):
    return dict(PANEL_ATTR.findall(tag))


def _get(server, session, path):
    status, _, body = http_request(server.base_url() + path, cookie=session)
    assert status == 200, path
    return body.decode()


def _post(server, session, path, **fields):
    return http_request(
        server.base_url() + path, method="POST", cookie=session,
        data=with_csrf(session, fields))


def _location(headers):
    parts = urllib.parse.urlsplit(headers["Location"])
    return parts.path, urllib.parse.parse_qs(parts.query)


@pytest.fixture
def served(make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    return server, login(server)


def test_the_system_view_has_no_unresolved_table_and_no_resolve_dialog(served):
    """unidentified prefixes are resolved in the Airlines table: the System view lists none of
    them and carries no resolve dialog, whatever the registry holds"""
    server, session = served
    health = _get(server, session, "/fleet?view=system")
    for text in ("QXA", "QXB", 'action="/airlines/resolve"', "data-view-panel-src",
                 "unresolved-prefixes", "data-table--registry"):
        assert text not in health, text
    airlines = _get(server, session, "/airlines/manage")
    assert 'name="prefix" value="QXA"' in airlines


@pytest.mark.parametrize("value, route", [
    ("health", "/fleet?view=system"), ("airlines", "/airlines/manage"), ("", "/airlines/manage"), (None, "/airlines/manage"),
    ("Health", "/airlines/manage"), ("/health", "/airlines/manage"), ("//evil.example", "/airlines/manage"),
    ("https://evil.example/", "/airlines/manage"), ("health\r\nX: y", "/airlines/manage"), (["health"], "/airlines/manage"),
])
def test_the_return_target_is_an_allow_list(value, route):
    """only the name 'health' reaches Health; every other value, however shaped, means Airlines"""
    assert resolve_dialog.return_route(value) == route


def test_naming_from_health_without_artwork_returns_to_health_for_step_b(served):
    """a saved name with no artwork yet returns to Health with the prefix to reopen the dialog
    on, and the prefix has left the table"""
    server, session = served
    status, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name="Totally Novel Airline",
        **{"return": "health"})
    path, query = _location(headers)
    assert (status, path) == (303, "/fleet")
    assert query == {"view": ["system"], "resolve": ["QXA"], "flash": ["manual_resolved"]}


def test_naming_from_health_with_existing_artwork_returns_to_health(served):
    """a name that already has artwork finishes the flow: back on Health, no reopen parameter"""
    server, session = served
    status, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name="Air France",
        **{"return": "health"})
    path, query = _location(headers)
    assert (status, path, query) == (
        303, "/fleet", {"view": ["system"], "flash": ["manual_resolved"]})


@pytest.mark.parametrize("return_value", [
    None, "", "airlines", "elsewhere", "//evil.example", "https://evil.example/health", "/health"])
def test_any_other_return_value_keeps_the_airlines_redirects(served, return_value):
    """no field, an empty one or one outside the allow-list leaves the Airlines flow as it was"""
    server, session = served
    fields = {} if return_value is None else {"return": return_value}
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name="Totally Novel Airline", **fields)
    assert _location(headers) == ("/airlines/manage", {"resolve": ["QXA"], "flash": ["manual_resolved"]})
    _, headers, _ = _post(server, session, "/airlines/resolve", prefix="NOPE", airline_name="X", **fields)
    assert _location(headers) == ("/airlines/manage", {"flash": ["manual_prefix_stale"]})


@pytest.mark.parametrize("name, flash", [
    ("", "manual_name_empty"), ("!!!", "manual_name_unusable"), ("x" * 101, "manual_name_too_long"),
    ("Generic Fallback", "manual_name_reserved")])
def test_a_refused_name_from_health_returns_with_its_own_flash(served, name, flash):
    """each refusal returns to Health with the prefix to reopen on and its own flash key, and
    writes nothing"""
    server, session = served
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name=name, **{"return": "health"})
    assert _location(headers) == (
        "/fleet", {"view": ["system"], "resolve": ["QXA"], "flash": [flash]})
    assert manual_resolutions.load_manual_resolutions(server.state_dir) == {}


def test_a_stale_prefix_from_health_returns_to_health_with_the_stale_flash(served):
    """a prefix that is no longer unresolved writes nothing and sends the owner back to Health"""
    server, session = served
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="ZZZ", airline_name="Totally Novel Airline",
        **{"return": "health"})
    assert _location(headers) == (
        "/fleet", {"view": ["system"], "flash": ["manual_prefix_stale"]})
    assert manual_resolutions.load_manual_resolutions(server.state_dir) == {}


def test_the_reopen_parameter_adds_nothing_to_the_system_view(served):
    """?resolve= on the System view is ignored: no step-B trigger, nothing echoed"""
    server, session = served
    _post(server, session, "/airlines/resolve", prefix="QXA", airline_name="Totally Novel Airline")
    for value in ("ZZZ", "QXA", "QXB", "%22%3E%3Cscript%3E", "", "a" * 40):
        page = _get(server, session, "/fleet?view=system&resolve=" + value)
        assert "hidden href" not in page, value
        assert "<script>" not in page


def test_an_upload_started_from_health_returns_to_health(served):
    """the artwork step's return target rides on the upload action: a refused upload lands on
    Health when it says so and on Airlines otherwise"""
    server, session = served
    body, multipart = with_csrf_part(
        session, b"--zz--\r\n", "multipart/form-data; boundary=zz")
    for suffix, route in (("?return=health", "/fleet"), ("?return=evil", "/airlines/manage"), ("", "/airlines/manage")):
        status, headers, _ = http_request(
            server.base_url() + "/illustration/air-france.png" + suffix,
            method="POST",
            cookie=session, data=body, content_type=multipart)
        path, query = _location(headers)
        assert (status, path) == (303, route), suffix
        assert query["flash"] == ["illustration_rejected"]
