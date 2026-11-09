"""Served-markup checks of the third audit's visual fixes: the sheet and the
pages are read through their render functions or over HTTP, never from source."""
import re

import companion.test_view_pages_helpers as vp
import fleet_console_support as fx
from companion.pages import history_page
from companion_app_server import http_request

NAV_TAB = re.compile(r'<nav class="tab-bar"')


def test_sorted_by_airline_each_run_of_flights_is_named_by_its_airline(tmp_path):
    """sorted by airline the phone list has one group per airline, named by it, instead of
    one group titled with the sort's own name"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-09-21T10:00:00+00:00", "hex": "a1", "callsign": "AFR1", "airline": "Air France"},
        {"ts": "2026-09-21T09:00:00+00:00", "hex": "a2", "callsign": "EZY1", "airline": "easyJet"},
        {"ts": "2026-09-21T08:00:00+00:00", "hex": "a3", "callsign": "AFR2", "airline": "Air France"},
    ])
    rendered = history_page.render(vp.history_ctx(
        tmp_path, history_query={"sort": "airline"}))
    labels = re.findall(r'<h2 class="section-label"[^>]*>([^<]*)</h2>', rendered) or re.findall(
        r'class="section-label[^"]*"[^>]*>([^<]*)<', rendered)
    assert "Air France" in labels and "easyJet" in labels, labels
    assert "Airline" not in labels, labels


def test_french_names_a_special_look_one_way():
    """the French catalogue says allure for a special look everywhere: no string still reads
    look spécial or looks spéciaux"""
    from companion import i18n_fr
    stale = {i: text for i, text in i18n_fr.BY_ID.items()
             if re.search(r"looks? sp\u00e9ciaux?", text, re.I)}
    assert not stale, stale


def test_an_error_page_keeps_the_tab_bar_for_a_signed_in_user(make_app_server):
    """a user refused an administrator page, and the public credits page, still show the
    user's tab bar instead of a dead end"""
    server = make_app_server(seed=fx.seed_fleet)
    cookie = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    for path, status in (("/fleet", 404), ("/credits", 200)):
        got, _headers, body = http_request(server.url(path), cookie=cookie)
        assert got == status, path
        assert NAV_TAB.search(body.decode()), path
        assert "tab-bar__link" in body.decode(), path


def test_the_not_found_copy_uses_typographic_apostrophes(make_app_server):
    server = make_app_server(seed=fx.seed_fleet)
    cookie = fx.user_cookie(server.state_dir, fx.OWNER_EMAIL)
    _status, _headers, body = http_request(server.url("/fleet"), cookie=cookie)
    text = body.decode()
    assert "doesn’t exist" in text and "doesn't" not in text


def test_the_calendar_connect_page_is_one_card_titled_for_the_task(make_app_server):
    server = make_app_server(seed=fx.seed_fleet, fake_providers=True)
    cookie = fx.admin_cookie(server.state_dir)
    _status, _headers, body = http_request(
        server.url("/display/calendar/connect"), cookie=cookie)
    text = body.decode()
    assert "Connect a calendar" in text
    assert "form-page__preview" not in text and "look-frame__image" not in text


def _login_card(lang, **kwargs):
    from companion import login_page, prefs
    prefs.set_request_prefs(lang=lang)
    try:
        return login_page.render_login_page("auto", auth0_enabled=True, **kwargs)
    finally:
        prefs.set_request_prefs(lang="en")


def test_the_sign_in_card_explains_an_expired_session_in_both_languages():
    plain = _login_card("en")
    assert "Your session expired" not in plain
    assert "Your session expired" in _login_card("en", expired=True)
    assert "Votre session a expiré" in _login_card("fr", expired=True)
    # Edits made before the session ended are not kept, and the card says so.
    assert "had not saved were not kept" in _login_card("en", expired=True)
    assert "non enregistrées n’ont pas été conservées" in _login_card("fr", expired=True)
    from companion import login_page
    # A sign-in error keeps its own notice: the expiry never replaces it.
    error = login_page.sign_in_error_page("expired", "auto", auth0_enabled=True)
    assert "Sign-in took too long" in error and "Your session expired" not in error


import pytest  # noqa: E402


@pytest.mark.parametrize("candidate,kept", [
    ("/account", True), ("/users", True), ("/fleet?frame=d_0123abcd&tab=access", True),
    ("/devices/d_0123abcd/flights", True), ("/devices/d_0123abcd/display/special-looks/new", True),
    ("/devices/d_0123abcd/", True), ("/devices/d_0123abcd", True), ("/flights?sort=airline", True),
    ("/login", False), ("/logout", False), ("/static/style.css", False), ("/settings", False),
    ("/gallery/x.png", False), ("/devices/d_0123abcd/gallery/x.png", False),
    ("/devices/d_0123abcd/fleet", False), ("/devices/../account", False),
    ("//evil.example", False), ("https://evil.example/", False), ("/\\evil.example", False),
    ("/account#frag", False), ("/account?x=\r\n", False), ("javascript:alert(1)", False),
    ("/devices/d_0123abcd/account", False), ("/account/../users", False),
])
def test_sign_in_next_keeps_every_page_route_and_nothing_else(candidate, kept):
    from companion import next_route
    got = next_route.validated_next_route(candidate, set())
    assert (got == candidate) is kept, (candidate, got)


def test_a_signed_out_visit_is_sent_to_sign_in_with_its_page_and_an_expiry_mark():
    from companion import next_route
    assert next_route.login_redirect("/users", False) == "/login?next=%2Fusers"
    assert next_route.login_redirect("/users", True) == "/login?next=%2Fusers&expired=1"
    assert next_route.login_redirect("/nope", True) == "/login?expired=1"
    assert next_route.login_redirect("/nope", False) == "/login"
    assert next_route.login_redirect(
        "/devices/d_0123abcd/flights?q=a", False) == (
            "/login?next=%2Fdevices%2Fd_0123abcd%2Fflights%3Fq%3Da")


def _look_images(view):
    import re
    from companion.pages import config_page
    rendered = config_page.render(
        {"device_config": {"theme": "blue"}}, scope=config_page.SCOPE_DISPLAY, view=view)
    return re.findall(r'<img class="look-frame__image"[^>]*>', rendered), rendered


@pytest.mark.parametrize("view,eager_index", [("departures", 0), ("arrivals", 1)])
def test_the_hidden_look_panel_loads_its_picture_lazily_and_the_visible_one_does_not(
        view, eager_index):
    images, _rendered = _look_images(view)
    assert len(images) == 2
    for index, tag in enumerate(images):
        assert ('loading="lazy"' in tag) is (index != eager_index), tag


def test_the_small_look_pictures_are_only_for_a_page_without_a_script():
    import re
    _images, rendered = _look_images("departures")
    bare = re.sub(r"<noscript>.*?</noscript>", "", rendered, flags=re.S)
    assert "look-pick__preview" not in bare
    assert rendered.count('<noscript><img class="look-pick__preview"') >= 10


@pytest.mark.parametrize("path", [
    "/frame-preview/blue.png?state=departing&size=small",
    "/theme-preview/blue.png?state=departing",
    "/illustration/air-france.png",
])
def test_cacheable_images_carry_an_etag_and_answer_a_matching_one_with_a_304(make_app_server, path):
    server = make_app_server(seed=fx.seed_fleet)
    cookie = fx.admin_cookie(server.state_dir)
    status, headers, body = http_request(server.url(path), cookie=cookie)
    assert status == 200 and body, path
    etag = headers["ETag"]
    assert etag.startswith('"') and "max-age" in headers["Cache-Control"]
    assert headers["Cache-Control"].startswith("private")
    again, again_headers, again_body = http_request(
        server.url(path), cookie=cookie, extra_headers={"If-None-Match": etag})
    assert again == 304 and again_body == b""
    assert again_headers["ETag"] == etag and "max-age" in again_headers["Cache-Control"]
    other, _headers, other_body = http_request(
        server.url(path), cookie=cookie, extra_headers={"If-None-Match": '"different"'})
    assert other == 200 and other_body == body


def test_an_uncacheable_response_never_gets_a_validator(make_app_server):
    server = make_app_server(seed=fx.seed_fleet)
    cookie = fx.admin_cookie(server.state_dir)
    _status, headers, _body = http_request(server.url("/account"), cookie=cookie)
    assert "ETag" not in headers


def test_an_owner_and_an_administrator_see_a_rename_row_on_the_frame_page_and_a_co_manager_does_not(
        make_app_server):
    from server import fleet_db

    def seed(state_dir):
        seeded = fx.seed_fleet(state_dir)
        conn = fleet_db.connect(state_dir)
        try:
            fleet_db.add_co_manager(conn, seeded.owned_id, seeded.user_id, seeded.owner_id)
        finally:
            conn.close()
    server = make_app_server(seed=seed)
    owned = None
    conn = fleet_db.connect(server.state_dir)
    try:
        owned = fleet_db.get_device_by_mac(conn, fx.MAC_OWNED)["id"]
    finally:
        conn.close()
    link = 'href="/devices/%s/frame/name"' % owned
    for cookie, expected in (
            (fx.user_cookie(server.state_dir, fx.OWNER_EMAIL), True),
            (fx.admin_cookie(server.state_dir), True),
            (fx.user_cookie(server.state_dir, fx.USER_EMAIL), False)):
        status, _headers, body = http_request(
            server.url("/devices/%s/" % owned), cookie=cookie)
        assert status == 200
        assert (link in body.decode()) is expected, (cookie, expected)
