"""Behaviour tests for the two administrator spaces, Console and the personal space:
which bar, sidebar and More sheet each page gets, the space switch, and that
the space follows the page and the principal role and nothing else.
"""
import re

import pytest

import companion.device_scope as device_scope
import companion.layout as layout
import companion.prefs as prefs
from companion import ui_nav

FRAME = device_scope.Device(
    id="abc123", name="Kitchen", hardware_type="x", state_path="devices/abc123",
    state_dir="", is_live=False)


@pytest.fixture(autouse=True)
def _reset_state():
    prefs.set_request_principal(None)
    prefs.set_request_prefs(lang="en")
    device_scope.set_request_scope(None, ())
    yield
    prefs.set_request_principal(None)
    prefs.set_request_prefs(lang="en")
    device_scope.set_request_scope(None, ())


def _hrefs(markup):
    return re.findall(r'<a class="[^"]*" href="([^"]+)"', markup)


def _as_admin():
    prefs.set_request_principal("admin", "admin")
    device_scope.set_request_scope(FRAME, [FRAME])


def test_admin_personal_sidebar_follows_the_spec():
    _as_admin()
    sidebar = layout.sidebar_nav("home", health_alert="warn", device_config={})
    prefix = "/devices/abc123"
    assert _hrefs(sidebar) == [
        prefix + "/", prefix + "/flights", prefix + "/detection",
        prefix + "/display", prefix + "/airlines", "/account"]
    # The switch is its own landmark above the sidebar navigation, never inside it.
    assert "space-switch" not in sidebar
    switch = ui_nav.space_switch_html("home")
    assert _hrefs(switch.replace("space-switch__segment", "x")) == ["/fleet", "/"]
    assert "Advanced" not in sidebar and "Administration" not in sidebar
    for route in ("/update", "/health", "/device"):
        assert 'href="%s"' % route not in sidebar
        assert 'href="%s%s"' % (prefix, route) not in sidebar
    assert sidebar.count("nav-notification") == 0


def test_admin_console_sidebar_follows_the_spec():
    _as_admin()
    sidebar = layout.sidebar_nav("users", health_alert="error", device_config={})
    assert _hrefs(sidebar) == [
        "/fleet", "/users", "/airlines/manage", "/audit", "/account"]
    assert "space-switch" not in sidebar and ">Administration<" in sidebar
    assert ">Frame tools<" not in sidebar and "Advanced" not in sidebar
    assert sidebar.count("sidebar-link--active") == 1
    assert 'href="/users" aria-current="page"' in sidebar
    assert sidebar.count("nav-notification") == 1
    fleet = sidebar[sidebar.index('href="/fleet"'):]
    assert "nav-notification" in fleet[:fleet.index("</a>")]


def test_admin_bars_follow_the_spec():
    _as_admin()
    prefix = "/devices/abc123"
    console = ui_nav._tab_bar_html("fleet", health_alert="warn", device_config={"a": 1})
    cells = console.split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == ["/fleet", "/users", "/airlines/manage", "/audit"]
    assert "Audit" in console and "Admin<" not in console and "tab-bar__link--switch" not in console
    sheet = console.split('<div class="tab-bar__more-panel">')[1]
    assert re.findall(r'<a [^>]*href="([^"]+)"', sheet) == ["/account", "/"]
    fleet_cell = cells[cells.index('href="/fleet"'):]
    assert "nav-notification" in fleet_cell[:fleet_cell.index("</a>")]
    summary = console[console.index("<summary"):console.index("</summary>")]
    assert "nav-notification" not in summary

    mine = ui_nav._tab_bar_html("home", health_alert="warn", device_config={"a": 1})
    cells = mine.split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == [
        prefix + "/", prefix + "/flights", prefix + "/airlines", prefix + "/display",
        prefix + "/detection"]
    assert "nav-notification" not in mine and "tab-bar__link--switch" not in mine
    sheet = mine.split('<div class="tab-bar__more-panel">')[1]
    assert re.findall(r'<a [^>]*href="([^"]+)"', sheet) == ["/account", "/fleet"]
    assert "Admin<" not in mine


def test_the_space_follows_the_page_and_never_a_non_admin():
    _as_admin()
    for slug in ("fleet", "users", "audit", "update", "health", "device", "airlines/manage"):
        assert ui_nav.current_space(slug) == ui_nav.CONSOLE_SPACE
    for slug in ("home", "flights", "detection", "display", "airlines", "account"):
        assert ui_nav.current_space(slug) == ui_nav.PERSONAL_SPACE
    assert "space-switch" in ui_nav.space_switch_html("fleet")
    prefs.set_request_principal("user", "user")
    assert ui_nav.current_space("fleet") is None
    assert ui_nav.space_switch_html("fleet") == ""
    prefs.set_request_principal(None)
    assert ui_nav.space_switch_html("fleet") == ""


def test_space_switch_labels_name_the_destination_in_both_languages():
    _as_admin()
    english = ui_nav.space_switch_html("fleet")
    assert ">My frame<" in english
    assert 'aria-label="Switch to your own frame pages"' in english
    assert 'href="/"' in english
    assert ">Console<" in ui_nav.space_switch_html("home")
    prefs.set_request_prefs(lang="fr")
    assert ">Mon cadre<" in ui_nav.space_switch_html("fleet")
    assert "Passer à la console d’administration" in ui_nav.space_switch_html("home")


def test_a_page_in_no_tab_selects_no_cell_on_an_error_page():
    _as_admin()
    def summary(html):
        return html[html.index("<summary"):html.index(">", html.index("<summary"))]

    error = ui_nav._tab_bar_html("", device_config={"a": 1}, no_tab=True)
    assert "tab-bar__link--active" not in error
    # Credits and the catalogue keep More as the cell that carries the pill.
    credits = ui_nav._tab_bar_html("", device_config={"a": 1})
    assert "tab-bar__link--active" in summary(credits)
    # The Account page is in More, so there More is selected even on an error flag.
    account = ui_nav._tab_bar_html("account", device_config={"a": 1}, no_tab=True)
    assert "tab-bar__link--active" in summary(account)


def test_an_administrator_without_a_frame_in_scope_still_gets_a_bar_of_destinations():
    prefs.set_request_principal("admin", "admin")
    device_scope.set_request_scope(None, ())
    bar = ui_nav._tab_bar_html("", device_config=None, no_tab=True)
    cells = bar.split('<details class="tab-bar__more')[0]
    assert _hrefs(cells) == ["/fleet", "/users", "/airlines/manage", "/audit"]
    assert "tab-bar__link--active" not in bar
    assert "tab-bar__more--alone" not in bar
