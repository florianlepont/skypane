"""Companion Update page tests (Phase 42, OTA-08's display half): the nav
entry/icon/French label (Task 1), and the served page itself across every
update state, the rollback banner, the version-history table and both
languages (Task 2).

Nav checks call companion.layout's own renderers directly, in-process,
the same pattern companion/test_companion_app_01.py and
companion/test_companion_app_02.py already use for nav-shape checks —
this is the real production render function's output, never source
text. A couple of checks go through a real running companion/app.py
(companion/conftest.py's module_app_server_factory) for genuine
end-to-end proof.
"""
import re

import companion.auth as auth
import companion.layout as layout
import companion.prefs as prefs
from companion_app_server import get, login

# ==========================================================================
# Task 1: navigation entry, icon and French nav label
# ==========================================================================


def test_advanced_group_lists_health_device_update_in_order():
    """layout.NAV_GROUPS' Advanced group holds Health, Device, Update, in that order"""
    advanced_routes = [route for route, _label in layout.NAV_GROUPS[1][1]]
    assert advanced_routes == [layout.HEALTH_ROUTE, layout.DEVICE_ROUTE, layout.UPDATE_ROUTE]


def test_sidebar_advanced_group_renders_the_update_link():
    """sidebar_nav() renders an Update link inside the Advanced group, after Health and Device"""
    markup = layout.sidebar_nav("flights")
    group_start = markup.index('class="nav-group nav-group--advanced"')
    group = markup[group_start:]
    assert ('href="%s"' % layout.UPDATE_ROUTE) in group
    health_idx = group.index('href="%s"' % layout.HEALTH_ROUTE)
    device_idx = group.index('href="%s"' % layout.DEVICE_ROUTE)
    update_idx = group.index('href="%s"' % layout.UPDATE_ROUTE)
    assert health_idx < device_idx < update_idx, (
        "expected Health, then Device, then Update inside the Advanced group")


def test_tab_bar_more_sheet_lists_exactly_health_device_update():
    """the bottom tab bar's More sheet holds exactly the Advanced group's three links, in order"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>", device_config=device_cfg)
    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    sheet_start = bar.index('<div class="tab-bar__more-panel">')
    sheet = bar[sheet_start:]
    sheet_links = re.findall(r'<a class="mobile-nav__link[^"]*" href="([^"]+)"', sheet)
    advanced_routes = [route for route, _label in layout.NAV_GROUPS[1][1]]
    assert sheet_links == advanced_routes, (
        "expected the More sheet to hold exactly the Advanced group %r, got %r"
        % (advanced_routes, sheet_links))
    # The tab bar still has its existing fixed cells: Update joined the
    # More sheet, it did not become a sixth tab-bar cell.
    everyday_routes = [route for route, _label in layout.NAV_GROUPS[0][1]]
    tab_links = re.findall(r'<a class="tab-bar__link[^"]*" href="([^"]+)"', bar)
    assert tab_links == everyday_routes


def test_update_link_carries_active_state_only_on_the_update_page():
    """the Update link carries the active class and aria-current only when active="update",
    in both the sidebar and the tab bar's More sheet, and only there"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    doc = layout.page_shell(
        title="Update", active="update", body="<p>b</p>", device_config=device_cfg)
    sidebar_start = doc.index('<nav class="sidebar-nav"')
    sidebar = doc[sidebar_start:doc.index("</nav>", sidebar_start)]
    update_tag_start = sidebar.index('href="%s"' % layout.UPDATE_ROUTE)
    tag_start = sidebar.rfind("<a", 0, update_tag_start)
    tag_end = sidebar.index(">", update_tag_start)
    update_tag = sidebar[tag_start:tag_end]
    assert "sidebar-link--active" in update_tag
    assert 'aria-current="page"' in update_tag
    assert sidebar.count("sidebar-link--active") == 1

    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    summary_start = bar.index("<summary")
    summary_tag = bar[summary_start:bar.index(">", summary_start)]
    assert "tab-bar__link--active" in summary_tag, (
        "expected the More summary to wear the active pill on the Update page")
    assert bar.count('aria-current="page"') == 1


def test_header_dropdown_preferences_panel_gains_no_update_link():
    """the hamburger dropdown's preferences panel holds no /update destination link"""
    doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    assert ('href="%s"' % layout.UPDATE_ROUTE) not in panel
    assert "mobile-nav__link" not in panel


def test_french_nav_label_reads_mise_a_jour():
    """under lang="fr" the Update nav label reads "Mise à jour", never the English "Update", in
    both the sidebar and the tab bar's More sheet"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    try:
        prefs.set_request_prefs(lang="fr")
        doc = layout.page_shell(
            title="T", active="flights", body="", device_config=device_cfg)
    finally:
        prefs.set_request_prefs(lang="en")
    assert ">Mise à jour<" in doc
    assert ">Update<" not in doc


def test_icon_sprite_has_icon_nav_update_symbol_and_the_link_uses_it():
    """the served icon sprite carries <symbol id="icon-nav-update"> and the Update link's <svg>
    references it via <use href="#icon-nav-update">"""
    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    assert '<symbol id="icon-nav-update"' in doc
    sidebar_start = doc.index('<nav class="sidebar-nav"')
    sidebar = doc[sidebar_start:doc.index("</nav>", sidebar_start)]
    update_link_start = sidebar.rfind("<a", 0, sidebar.index('href="%s"' % layout.UPDATE_ROUTE))
    update_link_end = sidebar.index("</a>", update_link_start)
    update_link = sidebar[update_link_start:update_link_end]
    assert 'href="#icon-nav-update"' in update_link


def test_update_route_is_the_third_advanced_entry_end_to_end(module_app_server_factory):
    """a real GET /health (already-live route) served by a real companion/app.py shows the
    Advanced group's sidebar as Health, Device, Update, both in English and in French"""
    server = module_app_server_factory()
    cookie = login(server)
    status, _headers, body = get(server, layout.HEALTH_ROUTE, cookie=cookie)
    assert status == 200
    text = body.decode("utf-8")
    group_start = text.index('class="nav-group nav-group--advanced"')
    group = text[group_start:]
    health_idx = group.index('href="%s"' % layout.HEALTH_ROUTE)
    device_idx = group.index('href="%s"' % layout.DEVICE_ROUTE)
    update_idx = group.index('href="%s"' % layout.UPDATE_ROUTE)
    assert health_idx < device_idx < update_idx

    fr_cookie = cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME
    status, _headers, fr_body = get(server, layout.HEALTH_ROUTE, cookie=fr_cookie)
    assert status == 200
    fr_text = fr_body.decode("utf-8")
    assert ">Mise à jour<" in fr_text
