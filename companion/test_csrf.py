"""Per-session anti-forgery token: derivation, dispatcher check and ordering,
form field emitter, and the existing protected routes."""
import hashlib
import re
import urllib.parse

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, auth, console_routes, prefs, routes, ui_components
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


# --- the existing protected routes ---------------------------------------

from companion.pages import airlines_page, config_page, update_page  # noqa: E402
from companion_app_server import csrf_token_of, login, with_csrf, with_csrf_part  # noqa: E402
import companion.test_companion_app_helpers as cah  # noqa: E402
from server import device_config, firmware_registry  # noqa: E402
from server.plane import (  # noqa: E402
    calendar_rules, colour_rules, manual_resolutions, name_overrides)

RULE_DELETE = "%scallsign/ZZR9999%s" % (
    config_page.RULES_DELETE_ROUTE_PREFIX, config_page.RULES_DELETE_ROUTE_SUFFIX)
MANUAL_DELETE = "%sABC%s" % (
    airlines_page.MANUAL_DELETE_ROUTE_PREFIX, airlines_page.MANUAL_DELETE_ROUTE_SUFFIX)
CALENDAR_URL = "https://csrf.example/feed.ics?token=CSRFTOKEN"


@pytest.fixture
def live(app_server_in_process):
    server = app_server_in_process
    state = server.state_dir
    colour_rules.add_rule(state, "callsign", "ZZR9999", "grey")
    manual_resolutions.add_entry(state, "ABC", "Abc Air", now="2026-01-01T00:00:00+00:00")
    name_overrides.set_names(state, ["AFR"], "Renamed Air")
    calendar_rules.save_calendar_url(state, CALENDAR_URL)
    return server


def _state_of(server):
    state = server.state_dir
    return (
        colour_rules.load_colour_rules(state),
        manual_resolutions.load_manual_resolutions(state),
        name_overrides.load_name_overrides(state),
        calendar_rules.calendar_is_configured(state),
        firmware_registry.load_registry(state)["schedule"],
        device_config.load_device_config(state),
    )


def _raw_post(server, path, cookie, fields):
    return http_request(
        server.url(path), method="POST", cookie=cookie,
        data=urllib.parse.urlencode(fields).encode(),
        extra_headers={"Origin": server.base_url()})


PROTECTED = (
    (RULE_DELETE, {}),
    (config_page.CALENDAR_DISCONNECT_ROUTE, {"confirm": "yes"}),
    (MANUAL_DELETE, {}),
    (airlines_page.RENAME_RESET_ROUTE, {"airline": "Air France"}),
    (airlines_page.ARTWORK_DELETE_ROUTE, {"key": "air-france"}),
    (airlines_page.DEFAULT_TYPE_ROUTE, {"airline_key": "air-france", "type": "A320"}),
    (update_page.INSTALL_ROUTE, {"version": "9.9.9", "confirm": "yes"}),
    (update_page.CANCEL_ROUTE, {}),
    (config_page.SETTINGS_ROUTE, {
        "scope": "display", "return_to": "/display", "theme": "blue"}),
    ("/quick/display", {"state": "off", "return_to": "/display"}),
    ("/quick/quiet-hours", {"state": "on", "return_to": "/display"}),
    ("/quick/led", {"state": "off", "return_to": "/device"}),
    ("/ui-theme", {"ui_theme": "dark"}),
    ("/ui-lang", {"ui_lang": "fr"}),
    (config_page.RULES_ADD_ROUTE, {
        "rule_kind": "callsign", "rule_key": "ZZN1234", "rule_theme_id": "black"}),
    (config_page.CALENDAR_CONNECT_ROUTE, {"calendar_url": ""}),
    (airlines_page.RESOLVE_ROUTE, {"prefix": "QQQ", "airline_name": "Quux Air"}),
    (airlines_page.RENAME_ROUTE, {"airline": "Air France", "airline_name": "AF Test"}),
)


@pytest.mark.parametrize("path,fields", PROTECTED, ids=[p for p, _f in PROTECTED])
def test_each_protected_route_refuses_a_tokenless_post_and_changes_nothing(live, path, fields):
    cookie = login(live)
    before = _state_of(live)
    status, _h, body = _raw_post(live, path, cookie, fields)
    assert status == 403 and b"This page expired" in body
    assert _state_of(live) == before
    status, _h, _b = http_request(
        live.url(path), method="POST", cookie=cookie, data=with_csrf(cookie, fields),
        extra_headers={"Origin": live.base_url()})
    assert status == 303


def test_a_token_from_another_session_is_refused(live):
    first, second = login(live), login(live)
    assert first != second
    foreign = with_csrf(first, {})
    before = _state_of(live)
    status, _h, _b = http_request(
        live.url(RULE_DELETE), method="POST", cookie=second, data=foreign,
        extra_headers={"Origin": live.base_url()})
    assert status == 403 and _state_of(live) == before


def _form_tokens(page_html, action_fragment):
    forms = re.findall(
        r'(<form[^>]*>)(.*?)</form>', page_html, re.S)
    return [
        re.findall(r'name="csrf_token" value="([0-9a-f]{64})"', inner)
        for opening, inner in forms if action_fragment in opening]


@pytest.mark.parametrize("page,action", (
    ("/display/special-looks", RULE_DELETE),
    ("/display/calendar/connect", config_page.CALENDAR_DISCONNECT_ROUTE),
    ("/airlines/manage", airlines_page.RENAME_RESET_ROUTE),
    ("/airlines/manage", airlines_page.LIGHTBOX_DELETE_CLASS),
    ("/", "/quick/display"),
    ("/", "/quick/quiet-hours"),
    ("/fleet?tab=settings", "/quick/led"),
    ("/display", 'action="/settings"'),
    ("/display/calendar-look", 'action="/settings"'),
    ("/account", 'action="/ui-theme"'),
    ("/account", 'action="/ui-lang"'),
    ("/account", 'action="/logout"'),
    ("/display/calendar/connect", config_page.CALENDAR_CONNECT_ROUTE),
    ("/display/special-looks/new", config_page.RULES_ADD_ROUTE),
    ("/airlines/manage", airlines_page.RENAME_ROUTE),
))
def test_served_forms_carry_the_requesting_sessions_token(live, page, action):
    cookie = login(live)
    expected = auth.csrf_token(_token_of(cookie))
    status, _h, body = http_request(live.url(page), cookie=cookie)
    assert status == 200
    found = _form_tokens(body.decode("utf-8"), action)
    assert found, "no form posting to %s on %s" % (action, page)
    assert all(tokens == [expected] for tokens in found)


def test_the_served_upload_forms_carry_the_token_in_a_field_never_in_the_address(live):
    cookie = login(live)
    expected = auth.csrf_token(_token_of(cookie))
    status, _h, body = http_request(live.url("/airlines/manage"), cookie=cookie)
    page = body.decode("utf-8")
    assert status == 200
    actions = re.findall(r'action="(/illustration/[^"]*)"', page)
    actions += re.findall(r'data-view-panel-upload-action="(/[^"]*)"', page)
    assert actions
    assert [a for a in actions if "csrf_token" in a or expected in a] == []
    assert expected not in "".join(actions)
    forms = re.findall(r'<form[^>]*multipart/form-data[^>]*>.*?</form>', page, re.S)
    assert forms
    for form in forms:
        assert form.count('name="csrf_token" value="%s"' % expected) == 1, form[:200]
        assert form.index('name="csrf_token"') < form.index('type="file"')


def test_logout_needs_the_token_and_ends_the_session_with_it(live):
    cookie = login(live)
    status, _h, body = _raw_post(live, "/logout", cookie, {})
    assert status == 403 and b"This page expired" in body
    assert http_request(live.url("/account"), cookie=cookie)[0] == 200
    status, _h, _b = http_request(
        live.url("/logout"), method="POST", cookie=cookie, data=with_csrf(cookie),
        extra_headers={"Origin": live.base_url()})
    assert status in (200, 303)
    assert http_request(live.url("/account"), cookie=cookie)[0] == 303


def _upload(live, url, cookie, body, content_type):
    return http_request(
        url, method="POST", cookie=cookie, data=body, content_type=content_type,
        extra_headers={"Origin": live.base_url()})


def test_an_illustration_upload_carries_its_token_as_a_leading_text_part(live):
    cookie = login(live)
    body, content_type = cah.encode_multipart(b"not an image", field_name="image")
    url = live.url("/illustration/air-france.png")
    status, _h, page = _upload(live, url, cookie, body, content_type)
    assert status == 403 and b"This page expired" in page
    good = with_csrf_part(cookie, body, content_type)
    assert _upload(live, url, cookie, *good)[0] == 303
    foreign = with_csrf_part(login(live), body, content_type)
    assert _upload(live, url, cookie, *foreign)[0] == 403


def test_a_token_left_in_the_old_address_is_ignored_and_the_upload_refused(live):
    cookie = login(live)
    body, content_type = cah.encode_multipart(b"not an image", field_name="image")
    url = live.url("/illustration/air-france.png?csrf_token=" + csrf_token_of(cookie))
    status, _h, page = _upload(live, url, cookie, body, content_type)
    assert status == 403 and b"This page expired" in page


def test_the_upload_token_part_is_strict(live):
    cookie = login(live)
    url = live.url("/illustration/air-france.png")
    body, content_type = cah.encode_multipart(b"not an image", field_name="image")
    boundary = content_type.split("boundary=")[1].encode()
    token = csrf_token_of(cookie).encode()
    head = b"--" + boundary + b"\r\n"
    text = b'Content-Disposition: form-data; name="csrf_token"\r\n\r\n'
    cases = {
        "token after the file": body[: body.rindex(b"--" + boundary + b"--")]
        + head + text + token + b"\r\n--" + boundary + b"--\r\n",
        "token with a filename": head + b'Content-Disposition: form-data; name="csrf_token";'
        b' filename="t"\r\n\r\n' + token + b"\r\n" + body,
        "wrong field name": head + b'Content-Disposition: form-data; name="other"\r\n\r\n'
        + token + b"\r\n" + body,
        "token twice": head + text + token + b"\r\n" + head + text + token + b"\r\n" + body,
        "oversized token": head + text + token * 3 + b"\r\n" + body,
        "token with odd characters": head + text + b"../../x\r\n" + body,
    }
    # A second token part passes the check (the first is good) but is not
    # an upload: the body is refused after it, with the generic message.
    twice = cases.pop("token twice")
    for name, payload in cases.items():
        status = _upload(live, url, cookie, payload, content_type)[0]
        assert status == 403, name
    status, headers, _b = _upload(live, url, cookie, twice, content_type)
    assert status == 303 and "flash=illustration_rejected" in headers["Location"]


def test_an_oversized_upload_with_a_good_token_is_still_told_it_is_too_large(live):
    cookie = login(live)
    big = b"\x00" * (app.MAX_ILLUSTRATION_UPLOAD_BYTES + 4096)
    good = with_csrf_part(cookie, *cah.encode_multipart(big, field_name="image"))
    status, headers, _b = _upload(
        live, live.url("/illustration/air-france.png"), cookie, *good)
    assert status == 303 and "illustration_too_large" in headers.get("Location", "")
    bad = cah.encode_multipart(big, field_name="image")
    assert _upload(live, live.url("/illustration/air-france.png"), cookie, *bad)[0] == 403


def test_only_the_known_routes_and_the_console_posts_are_flagged():
    flagged = {
        (route.method, route.matcher) for route in routes.ROUTES if route.csrf}
    console_posts = {
        (route.method, route.matcher) for route in console_routes.ROUTES if route.csrf}
    co_manager_posts = {
        ("POST", routes.Exact(path)) for path in (
            "/co-managers/add", "/co-managers/remove", "/co-managers/leave",
            "/frame/remove", "/frame/name")}
    quiet_window_post = {("POST", routes.Exact(routes.QUICK_QUIET_HOURS_WINDOW_ROUTE))}
    pair_frame_post = {("POST", routes.Exact("/pair-frame"))}
    airline_posts = {
        ("POST", routes.Exact(routes.airlines_page.ARTWORK_DELETE_ROUTE)),
        ("POST", routes.Exact(routes.airlines_page.DEFAULT_TYPE_ROUTE))}
    assert len(routes.CSRF_ROUTE_KEYS) == 20
    assert flagged == (
        set(routes.CSRF_ROUTE_KEYS) | console_posts | co_manager_posts | quiet_window_post
        | pair_frame_post | airline_posts)
    assert all(method == "POST" for method, _matcher in console_posts)
