"""The admin console's shell: route aggregation, navigation derived from the
route table, the section sub-nav, the Releases entry and the page shell
method."""
import hashlib
import re

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, console_flash, console_routes, i18n, layout, prefs, routes
from companion_app_server import http_request, http_request_full, set_cookie_headers
from server import fleet_db, fleet_sessions


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    prefs.set_request_principal(None)
    yield
    prefs.set_request_principal(None)


def _dummy_get(path, access=routes.ADMIN_ONLY):
    return routes.Route("GET", routes.Exact(path), lambda h, m: None, access)


def test_the_aggregator_holds_the_pairing_routes_and_nav_follows_them():
    served_routes = {
        (route.method, route.matcher.path) for route in console_routes.ROUTES
        if isinstance(route.matcher, routes.Exact)}
    assert {
        ("GET", console_routes.FLEET_ROUTE),
        ("POST", console_routes.FLEET_REGISTER_ROUTE),
        ("POST", console_routes.FLEET_PAIR_ROUTE),
        ("GET", console_routes.USERS_ROUTE),
        ("POST", console_routes.USERS_INVITE_ROUTE),
        ("GET", console_routes.AUDIT_ROUTE),
        ("GET", console_routes.LOCATIONS_ROUTE),
        ("POST", console_routes.LOCATIONS_ADD_ROUTE)} <= served_routes
    assert [entry[1] for entry in console_routes.available_nav_entries()] == [
        "/fleet", "/users", "/locations", "/audit", "/update"]


def test_nav_entries_follow_the_route_table(monkeypatch):
    extra = tuple(
        _dummy_get(path) for path in (
            console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE,
            console_routes.AUDIT_ROUTE))
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + extra)
    keys = [entry[0] for entry in console_routes.available_nav_entries()]
    assert keys == ["fleet", "users", "locations", "audit", "releases"]


def test_section_subnav_is_links_with_the_current_page_marked(monkeypatch):
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (
        _dummy_get(console_routes.FLEET_ROUTE), _dummy_get(console_routes.USERS_ROUTE)))
    markup = console_routes.section_subnav_html(console_routes.USERS_ROUTE)
    links = re.findall(r'<a class="([^"]*)" href="([^"]+)"([^>]*)>', markup)
    assert [href for _cls, href, _rest in links] == [
        "/fleet", "/users", "/locations", "/audit", "/update"]
    current = [href for cls, href, rest in links if "aria-current" in rest]
    assert current == ["/users"]
    assert "Fleet" in markup and "Releases" in markup


def test_section_subnav_is_empty_without_any_page(monkeypatch):
    monkeypatch.setattr(routes, "ROUTES", tuple(
        r for r in routes.ROUTES if not (
            isinstance(r.matcher, routes.Exact)
            and r.matcher.path in (
                "/update", console_routes.AUDIT_ROUTE, console_routes.FLEET_ROUTE,
                console_routes.USERS_ROUTE))))
    assert console_routes.section_subnav_html("/update") == ""


def test_console_french_labels_are_translated():
    expected = {
        console_routes.ADMINISTRATION_LABEL: "Administration",
        console_routes.FLEET_LABEL: "Cadres",
        console_routes.USERS_LABEL: "Utilisateurs",
        console_routes.AUDIT_LABEL: "Journal d’audit",
        console_routes.RELEASES_LABEL: "Versions",
    }
    for label, french in expected.items():
        assert i18n.t_lang(label, "fr") == french
    assert i18n.t_lang(console_routes.SECTION_NAV_LABEL, "fr") != str(
        console_routes.SECTION_NAV_LABEL)


# --- served pages ------------------------------------------------------------

CONSOLE_PAGES = (
    console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE,
    console_routes.LOCATIONS_ROUTE, console_routes.AUDIT_ROUTE)
FLASH_TITLE = i18n.Message("shelltest.title", "Done {name}")


def _console_get(path):
    return routes.Route(
        "GET", routes.Exact(path),
        lambda h, m: h._console_page(path, None, "<p>console body</p>"),
        routes.ADMIN_ONLY)


@pytest.fixture
def served(app_server_in_process, monkeypatch):
    """A real server with the four console GET pages answered by stand-in
    bodies (ahead of any real page, so the shell is tested on its own) and
    one session cookie per caller."""
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    monkeypatch.setattr(
        routes, "ROUTES", tuple(_console_get(p) for p in CONSOLE_PAGES) + routes.ROUTES)
    cookies = {}
    conn = fleet_db.connect(server.state_dir)
    try:
        for name, user_id in (("admin", seeded.admin_id), ("owner", seeded.owner_id)):
            token = "tok-" + name
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                principal="user", now=app._now())
            cookies[name] = "sp_session=" + token
    finally:
        conn.close()
    console_flash.register_flash("shell_test", "success", FLASH_TITLE, None)
    yield server, cookies
    console_flash._REGISTRY.pop("shell_test", None)


def _get(server, cookie, path, headers=None):
    status, _h, body = http_request(
        server.url(path), cookie=cookie, extra_headers=headers)
    return status, body.decode("utf-8")


def _sidebar(markup):
    start = markup.index('<nav class="sidebar-nav"')
    return markup[start:markup.index("</nav>", start)]


def _tab_bar(markup):
    start = markup.index('<nav class="tab-bar"')
    return markup[start:markup.index("</nav>", start)]


def _hrefs(markup):
    return re.findall(r'<a class="[^"]*" href="([^"]+)"', markup)


def test_admin_sidebar_lists_the_administration_group_in_order(served):
    server, cookies = served
    status, page = _get(server, cookies["admin"], "/fleet")
    assert status == 200
    sidebar = _sidebar(page)
    assert "Administration" in sidebar
    group = sidebar[sidebar.index('<div class="nav-group"><span'):]
    assert _hrefs(group) == ["/fleet", "/users", "/locations", "/audit", "/update"]
    assert re.search(r'href="/update">Releases<', group)


def test_the_group_lists_only_the_pages_that_exist(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_sessions.create_session(
            conn, hashlib.sha256(b"tok-a").hexdigest(), user_id=seeded.admin_id,
            principal="user", now=app._now())
    finally:
        conn.close()
    status, page = _get(server, "sp_session=tok-a", "/update")
    assert status == 200
    sidebar = _sidebar(page)
    group = sidebar[sidebar.index('<div class="nav-group"><span'):]
    assert _hrefs(group) == ["/fleet", "/users", "/locations", "/audit", "/update"]


def test_a_user_sees_no_administration_navigation_and_no_console_page(served):
    server, cookies = served
    status, account = _get(server, cookies["owner"], "/account")
    assert status == 200
    for needle in ("Administration", "/fleet", "/users", "/audit", "Releases"):
        assert needle not in account
    refused = _get(server, cookies["owner"], "/fleet")
    unknown = _get(server, cookies["owner"], "/no-such-page-anywhere")
    assert refused == unknown and refused[0] == 404


def test_the_admin_tab_takes_the_airlines_slot_when_fleet_exists(served):
    server, cookies = served
    _status, page = _get(server, cookies["admin"], "/users")
    bar = _tab_bar(page)
    cells = bar.split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == ["/", "/display", "/flights", "/fleet"]
    sheet = bar.split('<div class="tab-bar__more-panel">')[1]
    assert _hrefs(sheet)[0] == "/airlines"
    assert "Admin" in cells
    assert 'aria-current="page"' in cells.split('href="/fleet"')[1].split("</a>")[0]


def test_the_phone_bar_gains_the_admin_tab_once_the_fleet_page_exists(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_sessions.create_session(
            conn, hashlib.sha256(b"tok-b").hexdigest(), user_id=seeded.admin_id,
            principal="user", now=app._now())
    finally:
        conn.close()
    _status, page = _get(server, "sp_session=tok-b", "/")
    cells = _tab_bar(page).split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == ["/", "/display", "/flights", "/fleet"]


def test_every_console_page_shows_the_sub_nav_with_the_current_page_selected(served):
    server, cookies = served
    for path in CONSOLE_PAGES:
        _status, page = _get(server, cookies["admin"], path)
        nav = re.search(r'<nav class="filter-bar__chips section-subnav".*?</nav>', page, re.S)
        assert nav, path
        chips = nav.group(0)
        assert _hrefs(chips) == [*CONSOLE_PAGES, "/update"], path
        current = re.findall(r'href="([^"]+)" aria-current="page"', chips)
        assert current == [path], path
        for label in ("Fleet", "Users", "Locations", "Audit log", "Releases"):
            assert label in chips


def test_the_sub_nav_is_in_french_when_the_language_is_french(served):
    server, cookies = served
    _status, page = _get(
        server, cookies["admin"], "/fleet", headers={"Accept-Language": "fr"})
    chips = re.search(r'<nav class="filter-bar__chips section-subnav".*?</nav>', page, re.S)
    assert chips
    for label in ("Cadres", "Utilisateurs", "Lieux", "Journal d’audit", "Versions"):
        assert label in chips.group(0)


def _main(markup):
    return re.search(r"<main.*?</main>", markup, re.S).group(0)


def test_update_for_an_admin_differs_only_by_the_sub_nav_row(
        served, monkeypatch):
    server, cookies = served
    _status, with_chips = _get(server, cookies["admin"], "/update")
    chip_row = re.search(
        r'<nav class="filter-bar__chips section-subnav".*?</nav>', with_chips, re.S)
    assert chip_row
    monkeypatch.setattr(console_routes, "available_nav_entries", lambda: [])
    _status, without_chips = _get(server, cookies["admin"], "/update")
    assert _main(with_chips).replace(chip_row.group(0), "") == _main(without_chips)


def test_update_is_the_unknown_path_404_for_a_user(served):
    server, cookies = served
    assert _get(server, cookies["owner"], "/update") == _get(
        server, cookies["owner"], "/no-such-page-anywhere")


def test_console_pages_are_not_frame_tabs():
    tab_routes = {route for route, _label in layout.NAV_TABS}
    assert not tab_routes & set(CONSOLE_PAGES)


def test_a_console_page_shows_its_flash_once_and_clears_the_cookie(served):
    server, cookies = served
    queued = console_flash.queue_flash("shell_test", name="Kitchen")
    pair = queued.split(";", 1)[0]
    status, headers, body = http_request_full(
        server.url("/fleet"), cookie=cookies["admin"] + "; " + pair)
    assert status == 200
    assert "Done Kitchen" in body.decode("utf-8")
    cleared = [c for c in set_cookie_headers(headers) if c.startswith("sp_flash=")]
    assert cleared and "Max-Age=0" in cleared[0]
    _status, again = _get(server, cookies["admin"], "/fleet")
    assert "Done Kitchen" not in again


def test_a_tampered_flash_cookie_shows_nothing_on_a_console_page(served):
    server, cookies = served
    status, page = _get(server, cookies["admin"] + "; sp_flash=bm90LWpzb24", "/audit")
    assert status == 200
    assert "toast--" not in page.split("console body")[0].split("<main")[1]


def test_the_console_page_title_comes_from_the_registry(served):
    server, cookies = served
    _status, page = _get(server, cookies["admin"], "/audit")
    assert re.search(r"<title>[^<]*Audit log", page)
    _status, french = _get(
        server, cookies["admin"], "/audit", headers={"Accept-Language": "fr"})
    assert re.search(r"<title>[^<]*Journal d’audit", french)
