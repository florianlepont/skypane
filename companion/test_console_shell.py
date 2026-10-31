"""The admin console's shell: route aggregation, navigation derived from the
route table, the section sub-nav, the Releases entry and the page shell
method."""
import re

import pytest

from companion import console_routes, i18n, prefs, routes


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    prefs.set_request_principal(None)
    yield
    prefs.set_request_principal(None)


def _dummy_get(path, access=routes.ADMIN_ONLY):
    return routes.Route("GET", routes.Exact(path), lambda h, m: None, access)


def test_the_skeleton_aggregator_is_empty_and_only_releases_exists_yet():
    assert console_routes.ROUTES == ()
    assert [entry[1] for entry in console_routes.available_nav_entries()] == ["/update"]


def test_nav_entries_follow_the_route_table(monkeypatch):
    extra = tuple(
        _dummy_get(path) for path in (
            console_routes.FLEET_ROUTE, console_routes.USERS_ROUTE,
            console_routes.AUDIT_ROUTE))
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + extra)
    keys = [entry[0] for entry in console_routes.available_nav_entries()]
    assert keys == ["fleet", "users", "audit", "releases"]


def test_section_subnav_is_links_with_the_current_page_marked(monkeypatch):
    monkeypatch.setattr(routes, "ROUTES", routes.ROUTES + (
        _dummy_get(console_routes.FLEET_ROUTE), _dummy_get(console_routes.USERS_ROUTE)))
    markup = console_routes.section_subnav_html(console_routes.USERS_ROUTE)
    links = re.findall(r'<a class="([^"]*)" href="([^"]+)"([^>]*)>', markup)
    assert [href for _cls, href, _rest in links] == ["/fleet", "/users", "/update"]
    current = [href for cls, href, rest in links if "aria-current" in rest]
    assert current == ["/users"]
    assert "Fleet" in markup and "Releases" in markup


def test_section_subnav_is_empty_without_any_page(monkeypatch):
    monkeypatch.setattr(routes, "ROUTES", tuple(
        r for r in routes.ROUTES if not (
            isinstance(r.matcher, routes.Exact) and r.matcher.path == "/update")))
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
