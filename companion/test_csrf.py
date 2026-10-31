"""Per-session anti-forgery token: derivation, dispatcher check and ordering,
form field emitter, and the six existing protected routes."""
import hashlib
import urllib.parse

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, auth, prefs, routes, ui_components
from companion_app_server import http_request
from server import fleet_db, fleet_sessions

PROBE_PATH = "/csrf-probe-admin"


def _token_of(cookie):
    return cookie.split("=", 1)[1]


def test_token_is_deterministic_per_session_and_not_the_stored_hash():
    first, second = auth.new_session_token(), auth.new_session_token()
    token = auth.csrf_token(first)
    assert token == auth.csrf_token(first)
    assert token != auth.csrf_token(second)
    assert len(token) == 64 and int(token, 16) >= 0
    assert token != auth.hash_session_token(first)


def test_csrf_ok_accepts_only_the_exact_token():
    first, second = auth.new_session_token(), auth.new_session_token()
    good = auth.csrf_token(first)
    assert auth.csrf_ok(first, good)
    for bad in ("", None, good[:-1], good + "0", auth.csrf_token(second), good.upper()):
        assert not auth.csrf_ok(first, bad)
    assert not auth.csrf_ok("", good)
    assert not auth.csrf_ok(None, good)


def test_csrf_field_emits_one_escaped_hidden_input_or_nothing():
    prefs.set_request_csrf("")
    assert ui_components.csrf_field() == ""
    prefs.set_request_csrf('a"<b')
    html = ui_components.csrf_field()
    prefs.set_request_csrf("")
    assert html.count("<input") == 1
    assert 'name="csrf_token"' in html and 'type="hidden"' in html
    assert 'value="a&quot;&lt;b"' in html


def test_route_still_constructs_with_five_positional_arguments():
    route = routes.Route("GET", routes.Exact("/x"), lambda h, m: None, routes.PUBLIC)
    assert route.csrf is False and route.device_scoped is False


@pytest.fixture
def probe(app_server_in_process, monkeypatch):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    seen = []

    def handler(h, _match):
        seen.append(dict(h.read_form()))
        h.send_html(200, "<p>done</p>")

    route = routes.Route(
        "POST", routes.Exact(PROBE_PATH), handler, routes.ADMIN_ONLY, csrf=True)
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (route,))
    cookies = {}
    conn = fleet_db.connect(server.state_dir)
    try:
        for name, user_id in (
                ("admin", seeded.admin_id), ("admin2", seeded.admin_id),
                ("owner", seeded.owner_id)):
            token = "tok-" + name
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                principal="user", now=app._now())
            cookies[name] = "sp_session=" + token
    finally:
        conn.close()
    return server, seen, cookies


def _post(server, cookie, fields):
    return http_request(
        server.url(PROBE_PATH), method="POST", cookie=cookie,
        data=urllib.parse.urlencode(fields).encode(),
        extra_headers={"Origin": server.base_url()})


def test_a_flagged_route_refuses_a_missing_or_wrong_token(probe):
    server, seen, cookies = probe
    status, _h, body = _post(server, cookies["admin"], {"x": "1"})
    assert status == 403 and seen == []
    assert b"This page expired" in body
    wrong = auth.csrf_token(_token_of(cookies["admin2"]))
    assert _post(server, cookies["admin"], {"csrf_token": wrong})[0] == 403
    assert _post(server, cookies["admin"], {"csrf_token": ""})[0] == 403
    assert seen == []


def test_the_expired_page_is_translated(probe):
    server, _seen, cookies = probe
    status, _h, body = http_request(
        server.url(PROBE_PATH), method="POST", cookie=cookies["admin"],
        data=b"x=1", extra_headers={
            "Origin": server.base_url(), "Accept-Language": "fr"})
    assert status == 403
    assert "Cette page a expiré" in body.decode("utf-8")


def test_a_valid_token_runs_the_handler_and_read_form_sees_the_whole_form(probe):
    server, seen, cookies = probe
    token = auth.csrf_token(_token_of(cookies["admin"]))
    status, _h, _b = _post(server, cookies["admin"], {"csrf_token": token, "x": "1"})
    assert status == 200
    assert seen == [{"csrf_token": token, "x": "1"}]


def test_anonymous_and_denied_roles_never_reach_the_token_check(probe):
    server, seen, cookies = probe
    status, headers, _b = http_request(
        server.url(PROBE_PATH), method="POST", data=b"x=1",
        extra_headers={"Origin": server.base_url()})
    assert status == 303 and headers["Location"].startswith("/login")
    owner_token = auth.csrf_token(_token_of(cookies["owner"]))
    for fields in ({"x": "1"}, {"csrf_token": owner_token}):
        refused = _post(server, cookies["owner"], fields)
        unknown = http_request(
            server.url("/no-such-page-anywhere"), cookie=cookies["owner"])
        assert (refused[0], refused[2]) == (404, unknown[2])
    assert seen == []


def test_the_token_never_leaks_into_headers_urls_or_logs(probe, capsys):
    server, _seen, cookies = probe
    token = auth.csrf_token(_token_of(cookies["admin"]))
    status, headers, body = _post(server, cookies["admin"], {"csrf_token": token})
    assert status == 200
    assert token not in str(headers) and token.encode() not in body
    status, headers, _b = _post(server, cookies["admin"], {"csrf_token": "bad"})
    assert "Location" not in headers and "Set-Cookie" not in headers
    captured = capsys.readouterr()
    assert token not in captured.out + captured.err
    assert _token_of(cookies["admin"]) not in captured.out + captured.err
