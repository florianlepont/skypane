"""Companion Update page tests: the nav entry/icon/French label, and the
served page itself across every update state, the rollback banner, the
version-history table and both languages.

Nav checks call companion.layout's own renderers directly, in-process,
the same pattern companion/test_companion_app_01.py and
companion/test_companion_app_02.py already use for nav-shape checks —
this is the real production render function's output, never source
text. A couple of checks go through a real running companion/app.py
(companion/conftest.py's module_app_server_factory) for genuine
end-to-end proof.
"""
import hashlib
import json
import os
import re

import companion.auth as auth
import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
from companion.pages import update_page
from companion_app_server import get, login
from server import atomic_io
from server import firmware_registry as fr

_NOW = "2026-09-28T12:00:00+00:00"


def _ctx(now=_NOW):
    # update_page() itself never reads ctx.state_dir -- every fixture in
    # this module builds its `view` from firmware_registry.update_view()
    # directly, never from a real state_dir -- so a placeholder value is
    # enough; the two real-server checks near the bottom get a genuine
    # tmp_path-backed one from module_app_server_factory instead.
    return {"state_dir": "unused-state-dir", "now": now}


def _release(version, notes=None, installed_at=None, bench=False, published_at=_NOW):
    return {
        "version": version, "sha256": version.replace(".", "").ljust(64, "0")[:64],
        "size": 10, "released_at": published_at, "published_at": published_at,
        "commit": "a" * 40, "notes": notes or [], "bench": bench,
        "installed_at": installed_at or [],
    }


def _view(releases=(), schedule=None, last_outcome=None, device_entry=None, now=_NOW):
    """A `firmware_registry.update_view()` result built from hand-written
    registry/device_report dicts through the real pure function -- never
    a hand-built view dict -- so every test below proves update_page.py's
    own rendering against the real, documented view-model shape.
    """
    registry = fr._default_registry()
    registry["releases"] = list(releases)
    registry["schedule"] = schedule
    registry["last_outcome"] = last_outcome
    device_report = fr._default_device_report()
    if device_entry is not None:
        device_report["devices"]["dev1"] = device_entry
    return fr.update_view(registry, device_report, now)


# ==========================================================================
# Task 2: the Update page body (Status and Version history cards)
# ==========================================================================


def test_empty_registry_shows_no_version_reported_and_no_releases_yet():
    """an empty registry/device report renders "No version reported yet" and the Version
    history card's "No releases yet" empty state, no <table"""
    view = _view()
    html = update_page.update_page(_ctx(), view, "")
    assert i18n.t(update_page.NO_VERSION_REPORTED_TEXT) in html
    assert i18n.t(update_page.EMPTY_RELEASES_HEADING_TEXT) in html
    assert i18n.t(update_page.EMPTY_RELEASES_BODY_TEXT) in html
    assert "<table" not in html


def test_releases_render_newest_first_with_install_form_and_installed_column():
    """two releases with the newer one running: the older release's row carries an Install
    form (data-confirm, a hidden version field, no confirm field) and its Installed column
    shows a timestamp; the running release's row carries neither an Install form nor
    "Not installable" """
    releases = [
        _release("fw-v1.0.0", installed_at=[_NOW]),
        _release("fw-v1.1.0"),
    ]
    view = _view(releases=releases, device_entry={
        "fw_version": "fw-v1.1.0", "reported_at": _NOW, "events": []})
    html = update_page.update_page(_ctx(), view, "")
    table_html = html[html.index("<table"):]

    old_idx = table_html.index("fw-v1.0.0")
    new_idx = table_html.index("fw-v1.1.0")
    assert old_idx < new_idx, "expected newest-published-first ordering to still put fw-v1.0.0 first here"

    old_row = table_html[old_idx:new_idx]
    assert update_page.INSTALL_ROUTE in old_row
    assert "data-confirm=" in old_row
    assert '<input type="hidden" name="version" value="fw-v1.0.0">' in old_row
    assert "\"confirm\"" not in old_row, "the row-level Install form must post no confirm field"
    assert "icon-check" in old_row

    new_row = table_html[new_idx:].split("</tr>", 1)[0]
    assert update_page.INSTALL_ROUTE not in new_row
    assert i18n.t(update_page.NOT_INSTALLABLE_TEXT) not in new_row


def test_below_floor_release_shows_not_installable_text_no_form():
    """a release below the version floor renders the plain text "Not installable", never a
    form or a disabled button"""
    registry = fr._default_registry()
    registry["floor_version"] = "fw-v2.0.0"
    registry["releases"] = [_release("fw-v1.0.0")]
    device_report = fr._default_device_report()
    view = fr.update_view(registry, device_report, _NOW)
    html = update_page.update_page(_ctx(), view, "")
    assert i18n.t(update_page.NOT_INSTALLABLE_TEXT) in html
    assert update_page.INSTALL_ROUTE not in html
    row = html[html.index("fw-v1.0.0"):].split("</tr>", 1)[0]
    assert "<button" not in row, "a below-floor row must render plain text, never a button"


_STATE_DOT_CLASSES = {
    "available": "dot--off", "scheduled": "dot--off", "in_progress": "dot--warn",
    "installed": "dot--ok", "failed": "dot--error",
}


def test_each_state_renders_its_word_and_dot_class_with_a_timestamp():
    """each of the five update states renders its own word, the UI contract's dot class, and a
    timestamp element"""
    cases = {
        "available": _view(releases=[_release("fw-v1.0.0")]),
        "scheduled": _view(
            releases=[_release("fw-v1.0.0")],
            schedule={
                "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
                "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
                "failed_at": None, "last_result": None,
            }),
        "in_progress": _view(
            releases=[_release("fw-v1.0.0")],
            schedule={
                "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
                "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
                "failed_at": None, "last_result": None,
            },
            device_entry={
                "fw_version": "fw-v0.9.0", "reported_at": _NOW,
                "events": [{
                    "seq": 1, "at": _NOW, "kind": "offered",
                    "schedule_id": "s1", "token": None, "version": "fw-v1.0.0",
                }],
            }),
        "installed": _view(
            releases=[_release("fw-v1.0.0", installed_at=[_NOW])],
            last_outcome={"kind": "installed", "version": "fw-v1.0.0", "back_on": None, "at": _NOW},
            device_entry={"fw_version": "fw-v1.0.0", "reported_at": _NOW, "events": []}),
        "failed": _view(
            releases=[_release("fw-v1.0.0")],
            schedule={
                "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
                "scheduled_at": _NOW, "state": "failed", "attempts": 3,
                "failed_at": _NOW, "last_result": "fail-hash",
            }),
    }
    for state, view in cases.items():
        assert view["state"] == state, "fixture drifted: expected state %r, computed %r" % (state, view["state"])
        html = update_page.update_page(_ctx(), view, "08:14")
        state_label = i18n.t(update_page.STATE_LABELS[state])
        assert state_label in html, "state %r: missing label %r" % (state, state_label)
        dot_class = _STATE_DOT_CLASSES[state]
        assert dot_class in html, "state %r: missing dot class %r" % (state, dot_class)
        assert "data-relative" in html, "state %r: missing a timestamp element" % (state,)


def test_scheduled_state_shows_next_wake_sentence_and_cancel_form():
    """a scheduled-and-not-yet-offered state shows the "installs at the next wake" sentence and
    a Cancel form posting to /update/cancel with the quiet button class, never the accent
    primary treatment"""
    view = _view(
        releases=[_release("fw-v1.0.0")],
        schedule={
            "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
            "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
            "failed_at": None, "last_result": None,
        })
    assert view["cancellable"] is True
    html = update_page.update_page(_ctx(), view, "08:14")
    assert (i18n.t(update_page.SCHEDULED_SENTENCE_TEMPLATE) % "08:14") in html
    assert 'action="%s"' % update_page.CANCEL_ROUTE in html
    assert 'class="calendar-disconnect-btn"' in html


def test_in_progress_offered_state_shows_no_cancel_form_anywhere():
    """once the device has acknowledged the offer (in progress), no Cancel form renders
    anywhere on the page"""
    view = _view(
        releases=[_release("fw-v1.0.0")],
        schedule={
            "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
            "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
            "failed_at": None, "last_result": None,
        },
        device_entry={
            "fw_version": "fw-v0.9.0", "reported_at": _NOW,
            "events": [{
                "seq": 1, "at": _NOW, "kind": "offered",
                "schedule_id": "s1", "token": None, "version": "fw-v1.0.0",
            }],
        })
    assert view["state"] == "in_progress"
    assert view["cancellable"] is False
    html = update_page.update_page(_ctx(), view, "08:14")
    assert update_page.CANCEL_ROUTE not in html


def test_rollback_outcome_shows_the_warn_alert_banner():
    """a rollback outcome renders the role="alert" warn banner naming both versions"""
    view = _view(
        releases=[_release("fw-v1.3.0", installed_at=[_NOW])],
        last_outcome={
            "kind": "rollback", "version": "fw-v1.4.0", "back_on": "fw-v1.3.0", "at": _NOW},
        device_entry={"fw_version": "fw-v1.3.0", "reported_at": _NOW, "events": []})
    html = update_page.update_page(_ctx(), view, "")
    expected = i18n.t(update_page.ROLLBACK_SENTENCE_TEMPLATE) % ("fw-v1.4.0", "fw-v1.3.0")
    assert expected in html
    banner_start = html.index('role="alert"')
    banner_tag_start = html.rfind("<div", 0, banner_start)
    banner_tag_end = html.index(">", banner_start)
    assert "banner--warn" in html[banner_tag_start:banner_tag_end]


def test_notes_render_as_escaped_text_and_version_tags_are_monospace():
    """an HTML-hostile note renders escaped, and the version tag renders in a monospace cell"""
    hostile = "<script>alert(1)</script>"
    view = _view(releases=[_release("fw-v1.0.0", notes=[hostile])])
    html = update_page.update_page(_ctx(), view, "")
    assert hostile not in html
    assert "&lt;script&gt;" in html
    assert '<td class="mono">fw-v1.0.0</td>' in html


def test_french_render_translates_every_new_string():
    """under lang="fr" every new state/copy string reads in French"""
    view = _view(
        releases=[_release("fw-v1.0.0")],
        schedule={
            "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
            "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
            "failed_at": None, "last_result": None,
        })
    try:
        prefs.set_request_prefs(lang="fr")
        html = update_page.update_page(_ctx(), view, "08:14")
    finally:
        prefs.set_request_prefs(lang="en")
    assert "Planifiée" in html
    assert "Annuler" in html
    assert "Historique des versions" in html
    assert "Installer" in html
    assert "%s" not in html, "expected no leftover, unfilled %%s placeholder"


def _seed_update_state(state_dir):
    """A real, disk-backed registry (via firmware_registry.publish_release/
    schedule_release, never a hand-rolled JSON literal) plus a hand-written
    device_report.json -- byos-owned in production, so this module writes
    it directly rather than through firmware_registry's own API."""
    os.makedirs(str(state_dir), exist_ok=True)
    image_path = os.path.join(str(state_dir), "fixture.bin")
    image_bytes = b"fake-firmware-image-bytes"
    with open(image_path, "wb") as fh:
        fh.write(image_bytes)
    manifest = {
        "version": "fw-v1.0.0", "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
        "notes": ["initial release"],
    }
    fr.publish_release(str(state_dir), manifest, image_path, now=_NOW)
    fr.schedule_release(str(state_dir), "fw-v1.0.0", None, now=_NOW)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {"dev1": {"fw_version": "fw-v0.9.0", "reported_at": _NOW, "events": []}},
    }
    atomic_io.atomic_write(
        fr.device_report_path(str(state_dir)), json.dumps(device_report))


def test_get_update_without_a_session_redirects_to_login(module_app_server_factory):
    """GET /update without a session redirects to login like every other page"""
    server = module_app_server_factory()
    status, headers, _body = get(server, layout.UPDATE_ROUTE)
    assert status == 303
    assert headers.get("Location", "").startswith("/login")


def test_get_update_end_to_end_renders_the_scheduled_state(module_app_server_factory):
    """a real GET /update, seeded through firmware_registry's own write API plus a
    hand-written device_report.json, serves the Scheduled state with a Cancel form"""
    server = module_app_server_factory(seed=_seed_update_state)
    cookie = login(server)
    status, _headers, body = get(server, layout.UPDATE_ROUTE, cookie=cookie)
    assert status == 200
    text = body.decode("utf-8")
    assert i18n.t(update_page.STATE_LABELS["scheduled"]) in text
    assert 'action="%s"' % update_page.CANCEL_ROUTE in text
    assert "fw-v1.0.0" in text

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
