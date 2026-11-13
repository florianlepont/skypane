"""The two-segment Console / My frame switch as served: only an administrator
gets it, it sits in two places (phone strip and sidebar top), the current
space is marked by aria-current and a check glyph, and both segments are
fixed-destination GET links."""
import hashlib
import re

import pytest

from access_matrix_support import seed_matrix_fleet
from companion import app, auth
from companion_app_server import http_request
from server import fleet_db, fleet_sessions


@pytest.fixture
def served(app_server_in_process):
    server = app_server_in_process
    seeded = seed_matrix_fleet(server.state_dir)
    server.prefix = "/devices/%s" % seeded.owner_device
    cookies = {}
    conn = fleet_db.connect(server.state_dir)
    try:
        for name, user_id in (("admin", seeded.admin_id), ("owner", seeded.owner_id)):
            token = "tok-switch-" + name
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=user_id,
                principal="user", now=app._now())
            cookies[name] = "sp_session=" + token
    finally:
        conn.close()
    server.cookies = cookies
    return server


def _get(server, path, who=None, lang="en"):
    cookie = "%s=%s" % (auth.UI_LANG_COOKIE_NAME, lang)
    if who:
        cookie = "%s; %s" % (server.cookies[who], cookie)
    status, _headers, body = http_request(server.url(path), cookie=cookie)
    return status, body.decode("utf-8")


def _switches(markup):
    return re.findall(r'<nav class="space-switch"[^>]*>.*?</nav>', markup, re.S)


def _segments(switch):
    return re.findall(
        r'<a class="(space-switch__segment[^"]*)" href="([^"]+)" aria-label="([^"]+)"([^>]*)>'
        r"(.*?)</a>", switch, re.S)


def _label(segment_inner):
    return re.sub(r"<[^>]+>", "", re.sub(r"<svg.*?</svg>", "", segment_inner, flags=re.S)).strip()


@pytest.mark.parametrize("path_of,current", [
    (lambda s: "/fleet", "Console"),
    (lambda s: s.prefix + "/", "My frame"),
    (lambda s: s.prefix + "/flights", "My frame"),
    (lambda s: "/users", "Console"),
])
def test_an_administrator_sees_both_segments_and_the_current_one_is_marked(
        served, path_of, current):
    status, markup = _get(served, path_of(served), "admin")
    assert status == 200
    switches = _switches(markup)
    # The sidebar copy only: a phone gets the tab bar's leading cell instead.
    assert len(switches) == 1
    assert 'aria-label="Space"' in switches[0]
    segments = _segments(switches[0])
    assert [_label(inner) for _c, _h, _a, _x, inner in segments] == ["Console", "My frame"]
    assert [href for _c, href, _a, _x, _i in segments] == ["/fleet", "/"]
    for css, _href, _aria, attrs, inner in segments:
        is_current = _label(inner) == current
        assert ("aria-current=\"page\"" in attrs) is is_current
        assert ("space-switch__segment--current" in css) is is_current
        assert ("icon-check" in inner) is is_current
    assert "icon-shield" in segments[0][4]


def test_the_switch_labels_and_names_are_french_in_french(served):
    _status, markup = _get(served, "/fleet", "admin", "fr")
    switch = _switches(markup)[0]
    assert 'aria-label="Espace"' in switch
    segments = _segments(switch)
    assert [_label(inner) for _c, _h, _a, _x, inner in segments] == ["Console", "Mon cadre"]
    assert segments[1][2] == "Passer aux pages de votre cadre"


def test_the_phone_switch_is_a_more_panel_row_and_the_sidebar_keeps_its_own(served):
    _status, markup = _get(served, "/fleet", "admin")
    assert "space-strip" not in markup
    header = markup[markup.index("<header"):markup.index("</header>")]
    assert "space-switch" not in header
    bar = markup[markup.index('<nav class="tab-bar"'):]
    assert "tab-bar__link--switch" not in bar
    panel = bar[bar.index('<div class="tab-bar__more-panel">'):]
    row = panel[panel.index("tab-bar__space-link"):]
    row = row[:row.index("</a>")]
    assert 'href="/"' in row and (">Mon cadre<" in row or ">My frame<" in row)
    sidebar = markup[markup.index("<aside"):markup.index("</aside>")]
    assert sidebar.index('class="space-switch"') < sidebar.index('class="sidebar-nav"')


def test_the_old_header_text_link_is_gone(served):
    _status, markup = _get(served, "/fleet", "admin")
    assert "space-switch--header" not in markup
    assert "space-switch--sidebar" not in markup


def test_a_user_and_a_signed_out_page_never_get_the_switch(served):
    for path in ("/", "/flights", "/account"):
        status, markup = _get(served, served.prefix + path if path != "/account" else path, "owner")
        assert status == 200
        assert "space-switch" not in markup
    for lang in ("en", "fr"):
        _status, markup = _get(served, "/login", None, lang)
        assert "space-switch" not in markup
        assert "tab-bar__link--switch" not in markup


def test_a_user_cannot_open_the_console_the_switch_points_to(served):
    status, markup = _get(served, "/fleet", "owner")
    assert status == 404
    assert "space-switch" not in markup
