"""Behaviour tests for the two administrator spaces, Console and My views:
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


def test_admin_my_views_sidebar_follows_the_spec():
    _as_admin()
    sidebar = layout.sidebar_nav("home", health_alert="warn", device_config={})
    prefix = "/devices/abc123"
    assert _hrefs(sidebar) == [
        "/fleet", prefix + "/", prefix + "/display", prefix + "/flights",
        prefix + "/airlines", prefix + "/health", prefix + "/device", "/account"]
    assert sidebar.index('class="space-switch') < sidebar.index('href="%s/"' % prefix)
    assert ">Console<" in sidebar
    assert "Advanced" in sidebar and "Administration" not in sidebar
    assert "/update" not in sidebar and "Admin<" not in sidebar
    assert sidebar.count("nav-notification") == 1


def test_admin_console_sidebar_follows_the_spec():
    _as_admin()
    sidebar = layout.sidebar_nav("users", device_config={})
    assert re.findall(r'<a class="[^"]*" href="([^"]+)"', sidebar) == [
        "/", "/fleet", "/users", "/audit", "/update", "/account"]
    assert ">My views<" in sidebar and ">Administration<" in sidebar
    assert sidebar.count("sidebar-link--active") == 1
    assert 'href="/users" aria-current="page"' in sidebar
    assert "Advanced" not in sidebar


def test_admin_bars_follow_the_spec():
    _as_admin()
    console = ui_nav._tab_bar_html("fleet", health_alert="warn", device_config={"a": 1})
    cells = console.split('<details class="tab-bar__more">')[0]
    assert _hrefs(cells) == ["/fleet", "/users", "/audit"]
    assert ">Audit<" in cells and "Audit log" not in console
    sheet = console.split('<div class="tab-bar__more-panel">')[1]
    assert re.findall(r'href="([^"]+)"', sheet) == ["/update", "/", "/account"]
    assert "nav-notification" not in console

    mine = ui_nav._tab_bar_html("home", health_alert="warn", device_config={"a": 1})
    cells = mine.split('<details class="tab-bar__more">')[0]
    prefix = "/devices/abc123"
    assert _hrefs(cells) == [
        prefix + "/", prefix + "/display", prefix + "/flights", prefix + "/health"]
    health_cell = cells[cells.index('href="%s/health"' % prefix):]
    assert "nav-notification" in health_cell
    summary = mine[mine.index("<summary"):mine.index("</summary>")]
    assert "nav-notification" not in summary
    sheet = mine.split('<div class="tab-bar__more-panel">')[1]
    assert re.findall(r'href="([^"]+)"', sheet) == [
        prefix + "/airlines", prefix + "/device", "/account", "/fleet"]
    assert "Admin<" not in mine


def test_the_space_follows_the_page_and_never_a_non_admin():
    _as_admin()
    for slug in ("fleet", "users", "audit", "update"):
        assert ui_nav.current_space(slug) == ui_nav.CONSOLE_SPACE
    for slug in ("home", "display", "flights", "airlines", "health", "device", "account"):
        assert ui_nav.current_space(slug) == ui_nav.MY_VIEWS_SPACE
    assert "space-switch" in ui_nav.space_switch_html("fleet")
    prefs.set_request_principal("user", "user")
    assert ui_nav.current_space("fleet") is None
    assert ui_nav.space_switch_html("fleet") == ""
    prefs.set_request_principal(None)
    assert ui_nav.space_switch_html("fleet") == ""


def test_space_switch_labels_name_the_destination_in_both_languages():
    _as_admin()
    english = ui_nav.space_switch_html("fleet")
    assert ">My views<" in english and 'aria-label="Switch to your own views"' in english
    assert 'href="/"' in english
    assert ">Console<" in ui_nav.space_switch_html("home")
    prefs.set_request_prefs(lang="fr")
    assert ">Mes vues<" in ui_nav.space_switch_html("fleet")
    assert "Passer à la console d’administration" in ui_nav.space_switch_html("home")
