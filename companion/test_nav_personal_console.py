"""Behaviour tests of the two navigation sets over real in-process requests: the
personal navigation is the same for an administrator and a user looking at the
same frame, and the Console holds Fleet, Users, Health, Device and the airline
editor for the frame in view. Bar cells, More sheet rows and sidebar links are
read from the served HTML in English and French."""
import hashlib
import re

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, auth
from companion_app_server import http_request
from server import fleet_db, fleet_sessions

PERSONAL_PAGES = ("/", "/flights", "/detection", "/display", "/airlines")
ADMIN_WORDS = ("Admin", "Console", "Fleet", "Releases", "Health", "Device", "Update")
ADMIN_WORDS_FR = ("Flotte", "Versions", "État", "Appareil", "Console", "Administration")

PERSONAL_BAR_EN = ["Home", "History", "Location", "Style"]
PERSONAL_BAR_FR = ["Accueil", "Vols", "Lieu", "Style"]
PERSONAL_SIDEBAR_EN = [
    "Home", "Flight history", "Location and detection", "Style",
    "Airlines", "Account"]
PERSONAL_SIDEBAR_FR = [
    "Accueil", "Historique des vols", "Lieu et détection", "Style",
    "Compagnies", "Compte"]
CONSOLE_BAR_EN = ["My frame", "Fleet", "Users", "Editor", "Audit"]
CONSOLE_BAR_FR = ["Mon cadre", "Flotte", "Équipe", "Éditeur", "Journal"]
SWITCH_TO_CONSOLE = {"en": "Console", "fr": "Console"}
CONSOLE_SIDEBAR_EN = ["Fleet", "Users", "Airline editor", "Audit log", "Account"]
CONSOLE_SIDEBAR_FR = [
    "Flotte", "Utilisateurs", "Éditeur de compagnies", "Journal d’audit", "Compte"]


@pytest.fixture
def served(app_server_in_process):
    """A real server with a frame owned by a user, an administrator who owns
    none, and one session cookie per caller."""
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    server.frame_prefix = "/devices/%s" % seeded.owner_device
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
    return server, cookies


def _get(server, cookie, path, lang="en"):
    status, _headers, body = http_request(
        server.url(path), cookie="%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang))
    return status, body.decode("utf-8")


def _nav(markup, opener):
    start = markup.index(opener)
    return markup[start:markup.index("</nav>", start)]


def _anchors(markup):
    """(href, visible text) of every link in `markup`, tags stripped."""
    return [
        (href, re.sub(r"<[^>]+>", "", re.sub(
            r'<span class="visually-hidden">.*?</span>', "", inner)).strip())
        for href, inner in re.findall(r'<a class="[^"]*" href="([^"]+)"[^>]*>(.*?)</a>', markup, re.S)]


def _bar_parts(page):
    bar = _nav(page, '<nav class="tab-bar"')
    cells, sheet = bar.split('<div class="tab-bar__more-panel">')
    return _anchors(cells), _anchors(sheet), bar


def _sidebar_anchors(page):
    return _anchors(_nav(page, '<nav class="sidebar-nav"'))


def _unscoped(anchors):
    return [(re.sub(r"^/devices/[^/]+(?=/)", "", href), text) for href, text in anchors]


@pytest.mark.parametrize("lang,bar_labels,sidebar_labels", [
    ("en", PERSONAL_BAR_EN, PERSONAL_SIDEBAR_EN),
    ("fr", PERSONAL_BAR_FR, PERSONAL_SIDEBAR_FR)])
def test_the_personal_navigation_is_identical_for_an_administrator_and_a_user(
        served, lang, bar_labels, sidebar_labels):
    server, cookies = served
    prefix = server.frame_prefix
    status, user_page = _get(server, cookies["owner"], prefix + "/flights", lang)
    assert status == 200
    status, admin_page = _get(server, cookies["admin"], prefix + "/flights", lang)
    assert status == 200

    user_cells, user_sheet, _bar = _bar_parts(user_page)
    admin_cells, admin_sheet, _bar = _bar_parts(admin_page)
    assert [text for _href, text in user_cells] == bar_labels
    # The administrator's bar differs by the leading space switch cell alone.
    assert admin_cells[1:] == user_cells
    assert admin_cells[0] == ("/fleet", SWITCH_TO_CONSOLE[lang])
    assert [href for href, _text in user_cells] == [
        prefix + route for route in ("/", "/flights", "/detection", "/display")]

    airline_row = (prefix + "/airlines", sidebar_labels[4])
    account_row = ("/account", sidebar_labels[5])
    assert user_sheet == [airline_row, account_row]
    assert admin_sheet == user_sheet

    user_sidebar = _sidebar_anchors(user_page)
    admin_sidebar = _sidebar_anchors(admin_page)
    assert [text for _href, text in user_sidebar] == sidebar_labels
    assert admin_sidebar == user_sidebar


def test_the_personal_navigation_never_links_console_pages_or_locations(served):
    server, cookies = served
    prefix = server.frame_prefix
    for who in ("owner", "admin"):
        for page in PERSONAL_PAGES:
            _status, markup = _get(server, cookies[who], prefix + page)
            hrefs = [href for href, _text in _sidebar_anchors(markup)]
            hrefs += [href for href, _text in _anchors(_nav(markup, '<nav class="tab-bar"'))]
            for href in hrefs:
                path = re.sub(r"^/devices/[^/]+", "", href)
                assert path not in ("/health", "/device", "/update", "/locations",
                                    "/airlines/manage", "/users", "/audit"), (who, page, href)
            assert "nav-notification" not in markup


@pytest.mark.parametrize("lang,bar_labels,sidebar_labels", [
    ("en", CONSOLE_BAR_EN, CONSOLE_SIDEBAR_EN),
    ("fr", CONSOLE_BAR_FR, CONSOLE_SIDEBAR_FR)])
@pytest.mark.parametrize("path", ["/fleet", "/users", "/audit", "/fleet?view=system"])
def test_the_console_navigation_lists_the_console_pages_for_the_frame_in_view(
        served, path, lang, bar_labels, sidebar_labels):
    server, cookies = served
    status, page = _get(server, cookies["admin"], path, lang)
    assert status == 200
    cells, sheet, _bar = _bar_parts(page)
    assert [text for _href, text in cells] == bar_labels
    assert [href for href, _text in _unscoped(cells)] == [
        "/", "/fleet", "/users", "/airlines/manage", "/audit"]
    assert [href for href, _text in _unscoped(sheet)] == ["/account"]
    assert [text for _href, text in sheet] == [sidebar_labels[4]]

    sidebar = _sidebar_anchors(page)
    assert [text for _href, text in sidebar] == sidebar_labels


@pytest.mark.parametrize("page", ["/fleet", "/fleet?view=system", "/airlines/manage"])
def test_console_frame_pages_render_in_the_console_chrome_for_each_frame(served, page):
    server, cookies = served
    paths = (page, server.frame_prefix + page) if page == "/airlines/manage" else (page,)
    for path in paths:
        status, markup = _get(server, cookies["admin"], path)
        assert status == 200, path
        sidebar = _nav(markup, '<nav class="sidebar-nav"')
        assert "Administration" in sidebar and "Frame tools" not in sidebar
        aside = markup[markup.index("<aside"):markup.index("</aside>")]
        assert 'class="space-switch__segment" href="/"' in aside
        assert ">My frame<" in aside
        tools = {
            text: href for href, text in _anchors(sidebar)
            if re.sub(r"^/devices/[^/]+", "", href) in (
                "/health", "/device", "/airlines/manage")}
        # Health and Device are folded into the Fleet view; only the editor stays.
        assert list(tools) == ["Airline editor"]
        # The editor is one global list: its link carries no frame, whichever
        # address the page was opened under.
        assert list(tools.values()) == ["/airlines/manage"]
        active = re.findall(r'sidebar-link--active" href="([^"]+)"', sidebar)
        expected_active = page if page == "/airlines/manage" else "/fleet"
        assert [re.sub(r"^/devices/[^/]+", "", href) for href in active] == [expected_active]


def test_the_airline_editor_and_health_are_not_reachable_from_a_user_navigation(served):
    server, cookies = served
    _status, page = _get(server, cookies["owner"], server.frame_prefix + "/")
    for word in ADMIN_WORDS:
        assert word not in _nav(page, '<nav class="sidebar-nav"')
        assert word not in _nav(page, '<nav class="tab-bar"')
    _status, page = _get(server, cookies["owner"], server.frame_prefix + "/", "fr")
    for word in ADMIN_WORDS_FR:
        assert word not in _nav(page, '<nav class="sidebar-nav"')
        assert word not in _nav(page, '<nav class="tab-bar"')


@pytest.mark.parametrize("who", ["admin", "owner"])
@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_old_space_name_and_group_are_gone_from_every_served_page(served, who, lang):
    server, cookies = served
    pages = [server.frame_prefix + page for page in PERSONAL_PAGES] + ["/account"]
    if who == "admin":
        pages += ["/fleet", "/fleet?view=system", "/users", "/audit", "/airlines/manage"]
    for path in pages:
        _status, markup = _get(server, cookies[who], path, lang)
        for gone in ("My views", "Mes vues", "Advanced", "Avancé"):
            assert gone not in markup, (who, lang, path, gone)


def test_flight_history_is_the_navigation_label_and_the_page_title(served):
    server, cookies = served
    for who in ("admin", "owner"):
        _status, page = _get(server, cookies[who], server.frame_prefix + "/flights")
        labels = [text for _href, text in _sidebar_anchors(page)]
        assert "Flight history" in labels and "Flights" not in labels
        assert "<title>Flight history" in page
        _status, page = _get(server, cookies[who], server.frame_prefix + "/flights", "fr")
        assert "Historique des vols" in [text for _href, text in _sidebar_anchors(page)]
        assert "<title>Historique des vols" in page


def test_a_user_with_no_frame_has_no_bar_and_an_account_only_sidebar(served):
    server, _cookies = served
    token = "tok-frameless"
    conn = fleet_db.connect(server.state_dir)
    try:
        user_id = fleet_db.add_user(conn, "frameless@example.test", "user")
        fleet_sessions.create_session(
            conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
            principal="user", now=app._now())
    finally:
        conn.close()
    _status, page = _get(server, "sp_session=" + token, "/account")
    assert '<nav class="tab-bar"' not in page
    assert [href for href, _text in _sidebar_anchors(page)] == ["/account"]
