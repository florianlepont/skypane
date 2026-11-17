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
        "/fleet", "/users", "/health", "/device", "/airlines/manage", "/audit", "/update"]


def test_nav_entries_follow_the_route_table(monkeypatch):
    extra = tuple(
        _dummy_get(path) for path in (
            console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE,
            console_routes.AUDIT_ROUTE))
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + extra)
    keys = [entry[0] for entry in console_routes.available_nav_entries()]
    assert keys == [
        "fleet", "users", "health", "device", "editor", "audit", "releases"]


def test_console_french_labels_are_translated():
    expected = {
        console_routes.ADMINISTRATION_LABEL: "Administration",
        console_routes.FLEET_LABEL: "Flotte",
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
    console_routes.AUDIT_ROUTE)
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
    server.frame_prefix = "/devices/%s" % seeded.owner_device
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


def _unscoped(hrefs):
    """`hrefs` with any /devices/<id> frame prefix removed."""
    return [re.sub(r"^/devices/[^/]+(?=/)", "", href) for href in hrefs]


def _console_group(sidebar):
    start = sidebar.index('<div class="nav-group nav-group--console"')
    return sidebar[start:sidebar.index("</div>", start)]


def test_admin_sidebar_lists_the_administration_group_in_order(served):
    server, cookies = served
    status, page = _get(server, cookies["admin"], "/fleet")
    assert status == 200
    sidebar = _sidebar(page)
    assert _unscoped(_hrefs(sidebar)) == [
        "/fleet", "/users", "/airlines/manage", "/audit", "/account"]
    group = _console_group(sidebar)
    assert "Administration" in group
    assert "Releases<" not in sidebar
    aside = page[page.index("<aside"):page.index("</aside>")]
    assert re.search(
        r'class="space-switch__segment" href="/"[^>]*>(<[^>]*>)*My frame<', aside)
    assert "nav-group--frame-tools" not in sidebar


def test_the_console_sidebar_lists_the_console_pages_for_the_frame_in_view(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    server.frame_prefix = "/devices/%s" % seeded.owner_device
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_sessions.create_session(
            conn, hashlib.sha256(b"tok-a").hexdigest(), user_id=seeded.admin_id,
            principal="user", now=app._now())
    finally:
        conn.close()
    status, page = _get(server, "sp_session=tok-a", "/fleet")
    assert status == 200
    sidebar = _sidebar(page)
    assert _hrefs(_console_group(sidebar)) == ["/fleet", "/users"]
    assert _unscoped(_hrefs(sidebar)) == [
        "/fleet", "/users", "/airlines/manage", "/audit", "/account"]


def test_a_user_sees_no_administration_navigation_and_no_console_page(served):
    server, cookies = served
    status, account = _get(server, cookies["owner"], "/account")
    assert status == 200
    for needle in ("Administration", "/fleet", "/users", "/audit", "Releases"):
        assert needle not in account
    refused = _get(server, cookies["owner"], "/fleet")
    unknown = _get(server, cookies["owner"], "/no-such-page-anywhere")
    assert refused == unknown and refused[0] == 404


def test_the_console_bar_has_fleet_users_airlines_audit_and_more_and_the_switch_in_more(served):
    server, cookies = served
    _status, page = _get(server, cookies["admin"], "/users")
    bar = _tab_bar(page)
    cells = bar.split('<details class="tab-bar__more">')[0]
    assert _unscoped(_hrefs(cells)) == ["/fleet", "/users", "/airlines/manage", "/audit"]
    assert "Admin<" not in bar
    assert 'aria-current="page"' in cells.split('href="/users"')[1].split("</a>")[0]
    sheet = bar.split('<div class="tab-bar__more-panel">')[1]
    assert _unscoped(_hrefs(sheet)) == ["/account", "/"]
    health_at = cells.index("/fleet")
    health_cell = cells[health_at:cells.index("</a>", health_at)]
    assert health_cell.count("nav-notification") == bar.count("nav-notification") == 1


def test_my_views_pages_of_an_admin_carry_no_admin_tab(served):
    server, cookies = served
    # The administrator owns no frame, so the personal pages are opened on
    # the owner's frame by its id.
    prefix = server.frame_prefix
    _status, page = _get(server, cookies["admin"], prefix + "/")
    bar = _tab_bar(page)
    cells = bar.split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == [
        prefix + "/", prefix + "/flights", prefix + "/airlines", prefix + "/display",
        prefix + "/detection"]
    sheet = bar.split('<div class="tab-bar__more-panel">')[1]
    assert _hrefs(sheet) == ["/account", "/fleet"]
    assert "Admin<" not in page and "Administration" not in _sidebar(page)


def test_the_switch_is_a_row_of_the_more_panel_for_an_admin_and_absent_for_a_user(served):
    server, cookies = served
    _status, console = _get(server, cookies["admin"], "/fleet")
    header = console[console.index('<header class="site-header"'):console.index("</header>")]
    assert "space-switch" not in header and "<a " not in header.replace(
        'class="brand__link"', "")
    bar = _tab_bar(console)
    assert "tab-bar__link--switch" not in bar
    panel = bar.split('<div class="tab-bar__more-panel">')[1]
    assert re.search(r'<a class="[^"]*tab-bar__space-link" href="/"[^>]*>', panel)
    assert "My frame<" in panel
    _status, mine = _get(server, cookies["admin"], server.frame_prefix + "/")
    mine_bar = _tab_bar(mine)
    assert "tab-bar__link--switch" not in mine_bar
    mine_panel = mine_bar.split('<div class="tab-bar__more-panel">')[1]
    assert re.search(r'<a class="[^"]*tab-bar__space-link" href="/fleet"', mine_panel)
    assert "Console<" in mine_panel
    _status, account = _get(server, cookies["owner"], "/account")
    assert "space-switch" not in account and "tab-bar__space-link" not in account


def test_a_user_still_cannot_open_the_console(served):
    server, cookies = served
    refused = _get(server, cookies["owner"], "/fleet")
    unknown = _get(server, cookies["owner"], "/no-such-page-anywhere")
    assert refused == unknown and refused[0] == 404


def test_no_console_page_renders_a_section_chip_row(served):
    server, cookies = served
    for path in (*CONSOLE_PAGES, "/fleet?view=system"):
        status, page = _get(server, cookies["admin"], path)
        assert status == 200, path
        assert "section-subnav" not in page, path


def test_no_console_page_renders_a_section_chip_row_in_french(served):
    server, cookies = served
    for path in ("/fleet", "/fleet?view=system"):
        status, page = _get(
            server, cookies["admin"], path, headers={"Accept-Language": "fr"})
        assert status == 200, path
        assert "section-subnav" not in page, path


def _main(markup):
    return re.search(r"<main.*?</main>", markup, re.S).group(0)


def test_the_release_pages_of_the_console_are_not_reachable_by_a_user(served):
    server, cookies = served
    unknown = _get(server, cookies["owner"], "/no-such-page-anywhere")
    for path in ("/update/install", "/update/cancel"):
        assert _get(server, cookies["owner"], path) == unknown, path


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
