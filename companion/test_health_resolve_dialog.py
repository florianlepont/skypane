"""Health's Resolve links open the shared resolve dialog in place. Served-HTML checks on the
Health and Airlines pages, and route checks against a real server for the return target the
resolve flow carries (an allow-list, never an open redirect) and for the refusals that reopen the
dialog on Health. Nothing here reads production source text.
"""
import re
import urllib.parse

import pytest

import companion.test_status_pages_helpers as shp
from companion import layout
from companion import resolve_dialog
from companion_app_server import http_request, login
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
    pattern = r'<a href="/airlines\?resolve=%s" [^>]*>' % prefix
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
        data=urllib.parse.urlencode(fields).encode())


def _location(headers):
    parts = urllib.parse.urlsplit(headers["Location"])
    return parts.path, urllib.parse.parse_qs(parts.query)


@pytest.fixture
def served(make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    return server, login(server)


def test_every_resolve_row_is_a_trigger_with_the_full_vocabulary_and_keeps_its_link(served):
    """each prefix's table link and its phone-card link carries the whole data-view-panel-*
    vocabulary of an Airlines gap card plus the return target, and still points at the Airlines
    page for a visitor without script"""
    server, session = served
    health = _get(server, session, "/health")
    airlines = _get(server, session, "/airlines")
    gap = re.search(r'<a class="airline-card" href="/airlines\?resolve=QXA"[^>]*>', airlines).group(0)
    gap_attrs = _panel_attrs(gap)
    for prefix in REGISTRY:
        links = _resolve_links(health, prefix)
        assert len(links) == 2, (prefix, links)
        for link in links:
            attrs = _panel_attrs(link)
            assert set(gap_attrs) <= set(attrs), set(gap_attrs) - set(attrs)
            assert attrs["data-view-panel-return"] == "health"
            assert attrs["data-view-panel-mode"] == "gap"
            assert attrs["data-view-panel-resolve-prefix"] == prefix
            assert attrs["data-view-panel-count"] == str(REGISTRY[prefix]["count"])
            assert attrs["data-view-panel-caption"] == REGISTRY[prefix]["example_callsign"]
            assert 'aria-label="Resolve prefix %s"' % prefix in link
    health_tvf = _panel_attrs(_resolve_links(health, "QXA")[0])
    for name in ("caption", "heading", "mode", "scope", "resolve-prefix", "count"):
        key = "data-view-panel-" + name
        assert health_tvf[key] == gap_attrs[key], key


def test_the_dialog_is_on_health_once_with_a_return_field_and_not_on_airlines(served):
    """Health carries one shared dialog whose name form has an empty hidden return field and
    loads panel-lookup.js; the Airlines page's own dialog has no such field"""
    server, session = served
    health = _get(server, session, "/health")
    assert health.count("<dialog") == 1
    assert health.count('name="return"') == 1
    assert '<input type="hidden" name="return" value="">' in health
    assert 'action="/airlines/resolve"' in health
    assert '<script src="%s" defer>' % layout.PANEL_LOOKUP_SCRIPT_SRC in health
    airlines = _get(server, session, "/airlines")
    assert 'name="return"' not in airlines


def test_the_dialog_is_absent_when_the_table_is_empty(make_app_server):
    """with no unresolved prefix there is nothing to open it, so Health renders no dialog"""
    server = make_app_server(fake_providers=True)
    health = _get(server, login(server), "/health")
    assert "<dialog" not in health


@pytest.mark.parametrize("value, route", [
    ("health", "/health"), ("airlines", "/airlines"), ("", "/airlines"), (None, "/airlines"),
    ("Health", "/airlines"), ("/health", "/airlines"), ("//evil.example", "/airlines"),
    ("https://evil.example/", "/airlines"), ("health\r\nX: y", "/airlines"), (["health"], "/airlines"),
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
    assert (status, path) == (303, "/health")
    assert query == {"resolve": ["QXA"], "flash": ["manual_resolved"]}
    page = _get(server, session, "/health?resolve=QXA&flash=manual_resolved")
    assert not _resolve_links(page, "QXA") and _resolve_links(page, "QXB")
    step_b = re.search(r'<a hidden href="/airlines\?resolve=QXA" [^>]*>', page).group(0)
    attrs = _panel_attrs(step_b)
    assert attrs["data-view-panel-mode"] == "needs-artwork"
    assert attrs["data-view-panel-return"] == "health"
    assert attrs["data-view-panel-upload-action"].endswith(".png?return=health")
    assert attrs["data-view-panel-upload-action"].startswith("/illustration/totally-novel-airline")
    assert attrs["data-view-panel-delete-action"].startswith("/airlines/manual-resolutions/QXA")


def test_naming_from_health_with_existing_artwork_returns_to_a_refreshed_health(served):
    """a name that already has artwork finishes the flow: back on Health, the row gone, no
    reopen parameter"""
    server, session = served
    status, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name="Air France",
        **{"return": "health"})
    path, query = _location(headers)
    assert (status, path, query) == (303, "/health", {"flash": ["manual_resolved"]})
    page = _get(server, session, "/health?flash=manual_resolved")
    assert not _resolve_links(page, "QXA") and _resolve_links(page, "QXB")
    assert "hidden href" not in page


@pytest.mark.parametrize("return_value", [
    None, "", "airlines", "elsewhere", "//evil.example", "https://evil.example/health", "/health"])
def test_any_other_return_value_keeps_the_airlines_redirects(served, return_value):
    """no field, an empty one or one outside the allow-list leaves the Airlines flow as it was"""
    server, session = served
    fields = {} if return_value is None else {"return": return_value}
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name="Totally Novel Airline", **fields)
    assert _location(headers) == ("/airlines", {"resolve": ["QXA"], "flash": ["manual_resolved"]})
    _, headers, _ = _post(server, session, "/airlines/resolve", prefix="NOPE", airline_name="X", **fields)
    assert _location(headers) == ("/airlines", {"flash": ["manual_prefix_stale"]})


@pytest.mark.parametrize("name, flash", [
    ("", "manual_name_empty"), ("!!!", "manual_name_unusable"), ("x" * 101, "manual_name_too_long"),
    ("Generic Fallback", "manual_name_reserved")])
def test_a_refused_name_reopens_the_dialog_on_health(served, name, flash):
    """each refusal returns to Health with the prefix to reopen on and its own flash key, and
    writes nothing"""
    server, session = served
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="QXA", airline_name=name, **{"return": "health"})
    assert _location(headers) == ("/health", {"resolve": ["QXA"], "flash": [flash]})
    assert manual_resolutions.load_manual_resolutions(server.state_dir) == {}
    page = _get(server, session, "/health?resolve=QXA&flash=%s" % flash)
    assert _resolve_links(page, "QXA") and "hidden href" not in page


def test_a_stale_prefix_from_health_returns_to_health_with_the_stale_flash(served):
    """a prefix that is no longer unresolved writes nothing and sends the owner back to Health"""
    server, session = served
    _, headers, _ = _post(
        server, session, "/airlines/resolve", prefix="ZZZ", airline_name="Totally Novel Airline",
        **{"return": "health"})
    assert _location(headers) == ("/health", {"flash": ["manual_prefix_stale"]})
    assert manual_resolutions.load_manual_resolutions(server.state_dir) == {}


def test_the_reopen_parameter_only_acts_on_known_prefixes(served):
    """?resolve= on Health adds a step-B trigger only for a prefix just named and still without
    artwork; an unknown value, a live one (its own link opens it) and a markup-shaped one add
    nothing and are never echoed"""
    server, session = served
    for value in ("ZZZ", "QXB", "%22%3E%3Cscript%3E", "", "a" * 40):
        page = _get(server, session, "/health?resolve=" + value)
        assert "hidden href" not in page, value
        assert "<script>" not in page
    _post(server, session, "/airlines/resolve", prefix="QXA", airline_name="Totally Novel Airline")
    assert "hidden href" in _get(server, session, "/health?resolve=QXA")
    assert "hidden href" not in _get(server, session, "/health?resolve=QXB")
    _post(server, session, "/airlines/resolve", prefix="QXB", airline_name="Air France")
    assert "hidden href" not in _get(server, session, "/health?resolve=QXB")


def test_an_upload_started_from_health_returns_to_health(served):
    """the artwork step's return target rides on the upload action: a refused upload lands on
    Health when it says so and on Airlines otherwise"""
    server, session = served
    multipart = "multipart/form-data; boundary=zz"
    for suffix, route in (("?return=health", "/health"), ("?return=evil", "/airlines"), ("", "/airlines")):
        status, headers, _ = http_request(
            server.base_url() + "/illustration/air-france.png" + suffix, method="POST",
            cookie=session, data=b"x", content_type=multipart)
        path, query = _location(headers)
        assert (status, path) == (303, route), suffix
        assert query["flash"] == ["illustration_rejected"]
