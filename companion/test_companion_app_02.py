"""Part 02 of the `companion/test_companion_app.py` migration chain
(33-15-PLAN.md): the original harness's `check()` calls #51-#122 (by
ledger row — the loop-generated route checks each own a row per
iteration, so the plan's own "63 calls" count of source `check(...)`
call sites undercounts by the 12 rows three of those loops emit).

Covers the rest of `companion/layout.py`'s nav contract (the hamburger
dropdown, the bottom tab bar, the three-file nav DOM-contract guard),
`companion.app.parse_single_uploaded_file()`'s multipart parser,
`env_wake_interval_default()`/`page_context()`'s D-07 wake-interval
threading, the whole of `companion/theme_preview.py` (Sections 2.5/2.5b),
`_illustration_filenames()`'s per-request union (2.6), the
FLASH_KEY_MANUAL_* deck and `page_context()`'s resolve/manual_resolutions
ctx keys (2.7), the CFG-39/CFG-40 drawing contract
(`companion/draw.py`, 2.8), and Section 3's D-02 whole-site auth gate
plus the public static-asset routes, driven against a real
`companion/app.py` subprocess instead of the legacy `Harness`.

Three checks from the original Section 2.8 (`_battery_estimate_has_
exactly_one_home`, `_no_colour_literal_in_emitted_markup`, `_every_
drawn_shape_has_a_fill_route`) read production `.py` source as text
(one of them via `tokenize`, banned by guard G2) to prove a
structural/no-duplication property with no directly observable HTTP/DOM
consequence within this plan's scope — see the ledger fragment's Part 02
note and this plan's SUMMARY for the per-check disposition (one deleted,
two consolidated into a single narrower behaviour test scoped to
`companion/draw.py`'s own emitters).
"""
import json
import os
import re

import pytest
from PIL import Image

import companion.app as app_module
import companion.layout as layout
import companion.test_companion_app_helpers as cah
import companion.theme_preview as theme_preview
from companion_app_server import served_asset, served_stylesheet
from companion_markup import declarations_for
from server import device_config
from server.plane import illustrations as server_illustrations
from server.plane import manual_resolutions
from server.plane import render


@pytest.fixture(scope="module")
def app02_server(module_app_server_factory):
    """One module-scoped, read-only `companion/app.py` server shared by
    every check in this module that needs real HTTP: none of them logs
    in or otherwise mutates server state, matching 33-MIGRATION-RULES.md
    section 2's "read-only GETs may share a module-scoped server"
    guidance.
    """
    return module_app_server_factory(fake_providers=True)


@pytest.fixture(scope="module")
def served_css(app02_server):
    """The stylesheet `companion/app.py` actually serves."""
    return served_stylesheet(app02_server)


# ==========================================================================
# The hamburger dropdown / bottom tab bar (retargeted repeatedly by
# 22-14-PLAN.md Task 2, X9/D-10)
# ==========================================================================


def test_health_nav_notification_dot_appears_in_sidebar_and_tab_bar(served_css):
    """the Health notification dot appears inside the Health sidebar link and on the tab
    bar's More summary — one per nav renderer — when health_alert='error', nowhere when
    None/omitted, and never on another link (retargeted from the dropdown, 22-14-PLAN.md
    Task 2)"""
    dot_device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    on = layout.page_shell(
        title="T", active="health", body="<p>b</p>", health_alert="error",
        device_config=dot_device_cfg)
    off = layout.page_shell(
        title="T", active="health", body="<p>b</p>", health_alert=None,
        device_config=dot_device_cfg)
    default = layout.page_shell(
        title="T", active="health", body="<p>b</p>", device_config=dot_device_cfg)
    assert on.count(layout.NAV_NOTIFICATION_CLASS) == 2, (
        "expected the notification class exactly twice (one per nav renderer) when "
        "health_alert='error'")
    assert on.count(layout.HEALTH_ALERT_SUFFIX_TEXT) == 2, (
        "expected the alert suffix text exactly twice when health_alert='error'")
    assert off.count(layout.NAV_NOTIFICATION_CLASS) == 0, (
        "expected zero notification-class occurrences when health_alert=None")
    assert off.count(layout.HEALTH_ALERT_SUFFIX_TEXT) == 0, (
        "expected zero alert-suffix occurrences when health_alert=None")
    assert default == off, "expected the health_alert flag to default to off"

    side = on[on.index("sidebar-nav"):on.index("</aside>")]
    side_href_index = side.index('href="/health"')
    side_dot_index = side.index(layout.NAV_NOTIFICATION_CLASS)
    side_anchor_close_index = side.index("</a>", side_href_index)
    assert side_href_index < side_dot_index < side_anchor_close_index, (
        "expected the dot to sit inside the Health sidebar link")

    bar_start = on.index('<nav class="tab-bar"')
    bar = on[bar_start:on.index("</nav>", bar_start)]
    summary_start = bar.index("<summary")
    summary_end = bar.index("</summary>", summary_start)
    assert layout.NAV_NOTIFICATION_CLASS in bar[summary_start:summary_end], (
        "expected the dot inside the tab bar's More summary, not hidden inside its "
        "collapsed sheet")
    assert layout.NAV_NOTIFICATION_CLASS not in bar[summary_end:], (
        "expected no second dot inside the More sheet — one per nav renderer")
    assert layout.NAV_NOTIFICATION_CLASS not in bar[:summary_start], (
        "expected no dot on any of the four everyday tabs")

    other_active = layout.page_shell(
        title="T", active="config", body="", health_alert="error",
        device_config=dot_device_cfg)
    assert other_active.count(layout.NAV_NOTIFICATION_CLASS) == 2, (
        "expected exactly two dot occurrences (one per nav renderer) regardless of the "
        "active tab")

    assert layout.NAV_NOTIFICATION_CLASS in served_css, "expected the notification class to be styled"
    assert "visually-hidden" in served_css, "expected the visually-hidden utility class to be styled"


def test_hidden_form_control_floor_and_global_floor_both_survive(served_css):
    """input.visually-hidden/select.visually-hidden clears the 44px touch-target floor off
    hidden form controls, and the global input/select rule still declares both 44px
    minimums for every other field"""
    # quick task 260902-l9w: the runway radio's own utility class
    # (visually-hidden) is inert on an <input> unless the global
    # `input, select` rule's 44px minimums are separately cleared for
    # it — a rule that only asserts the new clearing rule would still
    # pass after someone deleted the global 44px floor site-wide.
    assert "input.visually-hidden" in served_css, (
        "expected an input.visually-hidden (or select.visually-hidden) rule clearing the "
        "global 44px touch-target floor off hidden form controls (the runway radio's own "
        "utility class is otherwise clamped back up to 44x44 by the global input/select "
        "rule below)")
    global_declarations = declarations_for(served_css, "select")
    for declaration, expected in (("min-height", "44px"), ("min-width", "44px")):
        assert global_declarations.get(declaration) == expected, (
            "the global input/select rule no longer declares %s: %s; this is a "
            "deliberate, developer-accepted WCAG 2.5.5 floor for every native field "
            "except the ones explicitly scoped away from it (D-08, the LED checkbox, "
            "and now the hidden runway radio) and must survive byte-identical"
            % (declaration, expected))


def test_health_nav_notification_dot_warn_severity():
    """layout.page_shell(..., health_alert='warn') also renders the notification dot,
    using dot--warn rather than dot--error"""
    warn = layout.page_shell(
        title="T", active="health", body="<p>b</p>", health_alert="warn",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    assert warn.count(layout.NAV_NOTIFICATION_CLASS) == 2, (
        "expected the notification class exactly twice (one per nav renderer) when "
        "health_alert='warn'")
    assert "dot--warn" in warn, "expected dot--warn to appear when health_alert='warn'"
    assert "dot--error" not in warn, "expected no dot--error class anywhere when health_alert='warn'"


def test_nav_dropdown_script_es5_safe_and_side_effect_free(app02_server):
    """nav-dropdown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/
    fetch/XHR/timers/innerHTML/document.write/eval) — standing constraints on the file"""
    src = served_asset(app02_server, "/static/nav-dropdown.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    banned = (
        "let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest",
        "setTimeout", "setInterval", "innerHTML", "document.write", "eval(")
    for token in banned:
        assert token not in src, "nav-dropdown.js must not contain %r" % token
    assert "aria-expanded" in src, "expected the open state to be read from aria-expanded"


def test_toggle_aria_contract_and_fixed_label():
    """the hamburger toggle carries type=button/id/aria-expanded=false/aria-controls and the
    fixed accessible label (never a close-verb variant), and the panel never renders open"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    assert 'type="button"' in doc, "expected the toggle to be type=\"button\""
    assert ('id="%s"' % layout.NAV_TOGGLE_ID) in doc, "expected the toggle id in the document"
    assert 'aria-expanded="false"' in doc, "expected the toggle to render aria-expanded=\"false\""
    assert ('aria-controls="%s"' % layout.MOBILE_NAV_ID) in doc, (
        "expected aria-controls to name the panel id")
    assert layout.NAV_TOGGLE_LABEL in doc, "expected the fixed toggle label in the document"
    assert "Close menu" not in doc, (
        "the toggle's accessible label must never swap to a close verb")
    assert layout.MOBILE_NAV_OPEN_CLASS not in doc, (
        "the panel must never render carrying the open class")


def test_dropdown_contents_and_order():
    """the dropdown panel holds the state reminder, then the language and theme switches and
    Sign out, in that order — and zero destination links (retargeted in place from the
    retired six-link menu, 22-14-PLAN.md Task 2)"""
    doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    for route, _label in layout.NAV_TABS:
        if route == layout.HOME_ROUTE:
            continue
        assert ('href="%s"' % route) not in panel, (
            "expected zero destination links in the dropdown, found %r" % route)
    assert "mobile-nav__link" not in panel, "expected zero dropdown destination links"
    order = []
    for needle, name in (
            ('class="nav-status', "the state reminder"),
            ('action="/ui-lang"', "the language switch"),
            ('action="/ui-theme"', "the theme switch"),
            ('action="/logout"', "Sign out")):
        index = panel.find(needle)
        assert index != -1, "expected %s inside the dropdown" % name
        order.append((index, name))
    assert order == sorted(order), (
        "expected the reminder, then language, theme and Sign out, in that order; got %r"
        % (order,))
    assert panel.count('class="mobile-nav__footer"') == 1, (
        "expected exactly one footer region in the dropdown")


def test_three_file_nav_dom_contract_guard(app02_server, served_css):
    """companion.app.NAV_SCRIPT_ROUTE, layout's nav DOM-contract literals, nav-dropdown.js
    and style.css all agree with each other and with a rendered document"""
    # Replicates the Python/CSS/JS drift guard 06.5-02 established for the
    # battery chart — a menu that never opens on a phone would otherwise
    # ship with every individual file still valid on its own and no
    # automated signal.
    js = served_asset(app02_server, "/static/nav-dropdown.js")
    for literal in (layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID, layout.MOBILE_NAV_OPEN_CLASS):
        assert literal in js, "DOM contract drift: %r is not looked up by nav-dropdown.js" % literal
    for cls in (
            "site-nav-toggle", "mobile-nav", "mobile-nav--open",
            "mobile-nav__link", "tab-bar", "tab-bar__link"):
        assert cls in served_css, "DOM contract drift: %r is not styled in style.css" % cls
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    for literal in (layout.NAV_TOGGLE_ID, layout.MOBILE_NAV_ID):
        assert literal in doc, "DOM contract drift: %r is not rendered" % literal
    assert app_module.NAV_SCRIPT_ROUTE == layout.NAV_DROPDOWN_SCRIPT_SRC, (
        "nav script route drift: %r vs %r"
        % (app_module.NAV_SCRIPT_ROUTE, layout.NAV_DROPDOWN_SCRIPT_SRC))


def test_dropdown_survives_with_javascript_disabled():
    """with JavaScript disabled the dropdown panel stays unclipped in the DOM (the collapsed
    look is a CSS max-height constraint, not a hidden attribute or display:none), every nav
    link stays reachable in the tab bar with its Advanced group behind a native <details>
    needing no script, and the server-rendered <html> tag carries no .js marker class
    (retargeted onto the tab bar, 22-14-PLAN.md Task 2)"""
    doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    assert " hidden" not in panel and 'hidden="' not in panel, (
        "the no-JS floor requires the panel stay in the accessibility tree")
    assert "display:" not in panel, (
        "the no-JS floor requires the panel carry no inline display style")
    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    for route, _label in layout.NAV_TABS:
        assert ('href="%s"' % route) in bar, (
            "missing tab-bar href for %r with JavaScript disabled" % route)
    # A bare `hidden` attribute only — `aria-hidden` on the tab glyphs is
    # correct and must not be caught by this.
    assert not re.search(r"<[^>]*\shidden(?=[\s>=])", bar), (
        "the tab bar must never be hidden by an attribute — its visibility is a media "
        "query only")
    assert "<details class=\"tab-bar__more\">" in bar, (
        "the Advanced group must open natively with scripts blocked, via <details>")
    assert "<script" not in bar and "onclick" not in bar, (
        "the tab bar must need no script to work")
    html_tag_end = doc.index(">", doc.index("<html"))
    html_tag = doc[:html_tag_end]
    assert 'class="js"' not in html_tag and ' js"' not in html_tag and ' js ' not in html_tag, (
        "server-rendered <html> tag must never carry the .js marker class")


def test_nav_dropdown_js_progressive_enhancement_state_machine(app02_server, served_css):
    """nav-dropdown.js adds the .js marker class before its dropdown element lookup and
    implements the hidden-attribute/transitionend/reduced-motion state machine, matched by
    style.css's .js-scoped clipping rules"""
    js = served_asset(app02_server, "/static/nav-dropdown.js")
    marker_idx = js.index('className += " js"')
    toggle_idx = js.index('getElementById("site-nav-toggle")')
    assert marker_idx < toggle_idx, ".js marker class must be added before the dropdown lookup"
    for needle in (
            "panel.hidden = true", "panel.hidden = false",
            "transitionend", "matchMedia", "prefers-reduced-motion"):
        assert needle in js, "nav-dropdown.js is missing %r" % needle
    for needle in (".js .mobile-nav {", ".js .mobile-nav--open {"):
        assert needle in served_css, "style.css is missing %r" % needle


_TAB_BAR_DEVICE_CFG = {"display_enabled": True, "quiet_hours_enabled": False}


def _tab_bar_slice(doc):
    start = doc.index('<nav class="tab-bar"')
    return doc[start:doc.index("</nav>", start) + len("</nav>")]


def test_tab_bar_is_five_cells_from_the_one_shared_nav_iteration():
    """the bottom tab bar renders five cells fed by the ONE shared _nav_links() iteration —
    its destinations equal the sidebar's in NAV_TABS order, the four everyday routes are tab
    links and the Advanced group is a native <details> sheet, exactly one aria-current="page"
    sits on the real link (never on the <summary>), the More summary wears the active pill on
    an Advanced page, it carries the shared Primary-navigation landmark name, and the whole
    bar carries no script hook (X9/D-10, 22-14-PLAN.md Task 1)"""
    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>", device_config=_TAB_BAR_DEVICE_CFG)
    bar = _tab_bar_slice(doc)
    sidebar = layout.sidebar_nav("flights")
    bar_routes = re.findall(r'<a class="[^"]*" href="([^"]+)"', bar)
    sidebar_routes = re.findall(r'<a class="sidebar-link[^"]*" href="([^"]+)"', sidebar)
    assert bar_routes == sidebar_routes, (
        "expected the tab bar's destinations to equal the sidebar's, in order; got %r vs %r"
        % (bar_routes, sidebar_routes))
    assert sidebar_routes == [route for route, _label in layout.NAV_TABS], (
        "expected both renderings to follow NAV_TABS order, got %r" % (sidebar_routes,))

    everyday = [route for route, _label in layout.NAV_GROUPS[0][1]]
    advanced = [route for route, _label in layout.NAV_GROUPS[1][1]]
    tab_links = re.findall(r'<a class="tab-bar__link[^"]*" href="([^"]+)"', bar)
    assert tab_links == everyday, (
        "expected exactly the unlabelled everyday group as tab links, got %r" % (tab_links,))
    assert bar.count("<details class=\"tab-bar__more\">") == 1, "expected exactly one <details> More cell"
    assert bar.count("<summary") == 1, "expected the More cell to be a native <summary>"
    sheet = bar[bar.index('<div class="tab-bar__more-panel">'):]
    sheet_links = re.findall(r'<a class="mobile-nav__link[^"]*" href="([^"]+)"', sheet)
    assert sheet_links == advanced, (
        "expected the More sheet to hold exactly the Advanced group, got %r" % (sheet_links,))

    assert bar.count('aria-current="page"') == 1, (
        "expected exactly one aria-current=\"page\" in the tab bar, got %d"
        % bar.count('aria-current="page"'))
    assert bar.count("tab-bar__link--active") == 1, "expected exactly one active tab"
    active_tag_start = bar.rindex("<a", 0, bar.index('aria-current="page"'))
    assert "tab-bar__link--active" in bar[active_tag_start:bar.index(">", active_tag_start)], (
        "expected the aria-current link to be the active tab")

    advanced_doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>", device_config=_TAB_BAR_DEVICE_CFG)
    advanced_bar = _tab_bar_slice(advanced_doc)
    summary_start = advanced_bar.index("<summary")
    summary_tag = advanced_bar[summary_start:advanced_bar.index(">", summary_start)]
    assert "tab-bar__link--active" in summary_tag, (
        "expected the More summary to wear the active pill on an Advanced page, got %r"
        % (summary_tag,))
    assert 'aria-current="page"' not in summary_tag, (
        "a <summary> is a disclosure control, not the current page — aria-current must "
        "stay on the link")
    assert advanced_bar.count('aria-current="page"') == 1, (
        "expected exactly one aria-current on an Advanced page too")
    assert "tab-bar__link--active" not in advanced_bar[:advanced_bar.index("<details")], (
        "expected none of the four everyday tabs to be active on /health")

    assert 'aria-label="Primary navigation"' in bar, "expected the landmark name on the tab bar"
    for banned in ("onclick", "data-", "<script", "id=\"site-nav-toggle\""):
        assert banned not in bar, "the tab bar must carry no script hook (%r found)" % (banned,)


def test_tab_bar_is_absent_from_the_login_shell_and_the_404():
    """the tab bar renders from the authenticated shell only and only with a device config —
    never on the login shell, never on the 404 — and the <body> clearance marker appears
    exactly when the bar does (X9/D-10, 22-14-PLAN.md Task 1)"""
    login = layout.login_shell("<p>login</p>")
    assert "tab-bar" not in login, "expected no tab bar on the login shell"
    no_ctx = layout.page_shell(title="404", active="", body="<p>x</p>")
    assert "tab-bar" not in no_ctx, (
        "expected no tab bar on a page_shell() render with no device config")
    assert layout.TAB_BAR_BODY_CLASS not in no_ctx, (
        "a page with no bar must reserve no clearance for one — the body marker must be "
        "absent")
    assert layout._tab_bar_html("home", device_config=None) == "", (
        "expected _tab_bar_html(device_config=None) to render nothing")
    assert layout._tab_bar_html("home", device_config={}) == "", (
        "expected _tab_bar_html(device_config={}) to render nothing")
    with_ctx = layout.page_shell(
        title="T", active="home", body="<p>x</p>", device_config=_TAB_BAR_DEVICE_CFG)
    assert ('<body class="%s" ' % layout.TAB_BAR_BODY_CLASS) in with_ctx, (
        "expected the body marker exactly when the bar renders, and first on the tag, so "
        "the page-foot clearance is reserved only where there is a bar to clear")
    for doc, label in ((with_ctx, "a bar page"), (no_ctx, "a no-bar page")):
        for attr in (layout.REFRESH_PAUSED_ATTR, layout.REFRESH_RECONNECTING_ATTR):
            if "<body" in doc:
                assert ('%s="' % attr) in doc, (
                    "expected %r on <body> for %s — freshness.js builds its neutral "
                    "loop-state badge client-side and reads its copy from there (T13)"
                    % (attr, label))
    assert with_ctx.count('<nav class="tab-bar"') == 1, "expected exactly one tab bar per document"


# ==========================================================================
# parse_single_uploaded_file() — stdlib-only, single-part multipart parser
# (quick task 260902-v26 Task 1). Pure in-process checks.
# ==========================================================================

_VALID_UPLOAD_PAYLOAD = b"\x89PNG-fixture-bytes-not-a-real-decodable-png"


def test_parser_happy_path_ignores_traversal_filename():
    """parse_single_uploaded_file() returns the payload for a well-formed single-part body,
    even when the part header declares a traversal-shaped filename (never read)"""
    body, content_type = cah.encode_multipart(
        _VALID_UPLOAD_PAYLOAD, filename="../../../etc/passwd")
    result = app_module.parse_single_uploaded_file(content_type, body)
    assert result == _VALID_UPLOAD_PAYLOAD, (
        "expected the payload back even with a traversal-shaped declared filename, got %r"
        % (result,))


def test_parser_two_parts_returns_none():
    """parse_single_uploaded_file() returns None for a two-part body — this route accepts
    exactly one file part and nothing else"""
    boundary = b"SkyPaneTwoPartBoundary9k2"
    body = (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="a"; filename="a.png"\r\n\r\n'
        b"AAAA\r\n"
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="b"; filename="b.png"\r\n\r\n'
        b"BBBB\r\n"
        b"--" + boundary + b"--\r\n"
    )
    content_type = "multipart/form-data; boundary=%s" % boundary.decode("ascii")
    result = app_module.parse_single_uploaded_file(content_type, body)
    assert result is None, "expected None for a two-part body, got %r" % (result,)


def test_parser_urlencoded_media_type_returns_none():
    """parse_single_uploaded_file() returns None for a non-multipart media type"""
    result = app_module.parse_single_uploaded_file(
        "application/x-www-form-urlencoded", b"field=value")
    assert result is None, "expected None for a non-multipart media type, got %r" % (result,)


def test_parser_missing_boundary_returns_none():
    """parse_single_uploaded_file() returns None when the boundary parameter is missing"""
    body, _content_type = cah.encode_multipart(_VALID_UPLOAD_PAYLOAD)
    result = app_module.parse_single_uploaded_file("multipart/form-data", body)
    assert result is None, "expected None with no boundary parameter, got %r" % (result,)


def test_parser_empty_body_returns_none():
    """parse_single_uploaded_file() returns None for an empty body"""
    result = app_module.parse_single_uploaded_file(
        "multipart/form-data; boundary=anything", b"")
    assert result is None, "expected None for an empty body, got %r" % (result,)


def test_parser_missing_header_body_separator_returns_none():
    """parse_single_uploaded_file() returns None when the part has no header/body separator"""
    boundary = b"SkyPaneNoSepBoundaryF4x"
    body = (
        b"--" + boundary + b"\r\n"
        b"No blank line separates this from anything\r\n"
        b"--" + boundary + b"--\r\n"
    )
    content_type = "multipart/form-data; boundary=%s" % boundary.decode("ascii")
    result = app_module.parse_single_uploaded_file(content_type, body)
    assert result is None, (
        "expected None with no header/body CRLFCRLF separator, got %r" % (result,))


def test_parser_none_content_type_returns_none():
    """parse_single_uploaded_file() returns None for a None content_type"""
    result = app_module.parse_single_uploaded_file(None, b"anything at all")
    assert result is None, "expected None for a None content_type, got %r" % (result,)


def test_parser_empty_payload_returns_none():
    """parse_single_uploaded_file() returns None for an empty file part payload"""
    body, content_type = cah.encode_multipart(b"")
    result = app_module.parse_single_uploaded_file(content_type, body)
    assert result is None, "expected None for an empty file part payload, got %r" % (result,)


# ==========================================================================
# 11-04: env_wake_interval_default() / page_context() threading (D-07's
# SKYPANE_SLEEP_S pre-fill). Pure in-process checks.
# ==========================================================================


def test_env_wake_interval_default_full_input_space(monkeypatch):
    """env_wake_interval_default() covers its whole input space (unset, empty, non-numeric,
    whitespace-padded, in-range and out-of-range including deploy/skypane.env.example's
    shipped below-floor SKYPANE_SLEEP_S=30) and never raises"""
    cases = (
        (None, None),      # unset
        ("", None),
        ("900", 900),
        ("abc", None),
        ("1.5", None),
        ("-1", None),
        ("0", None),
        # deploy/skypane.env.example's shipped value — below the 60s floor
        ("30", None),
        ("59", None),
        ("3601", None),
        ("60", 60),         # inclusive lower bound
        ("3600", 3600),     # inclusive upper bound
        (" 900 ", 900),     # whitespace-padded — int() tolerates it
    )
    for raw, expected in cases:
        if raw is None:
            monkeypatch.delenv(app_module.SLEEP_ENV_VAR, raising=False)
        else:
            monkeypatch.setenv(app_module.SLEEP_ENV_VAR, raw)
        actual = app_module.env_wake_interval_default()
        assert actual == expected, (
            "SKYPANE_SLEEP_S=%r: expected %r, got %r" % (raw, expected, actual))


class _FakePageContextHeaders:
    def get(self, name, default=None):
        return default


class _FakePageContextArgs:
    def __init__(self, state_dir):
        self.state_dir = state_dir


class _FakePageContextHandler:
    """A minimal stand-in for companion.app.Handler carrying only the
    attributes page_context() actually reads (self.path, self.args.
    state_dir, self.headers, self._resolved_ui_theme()) — never
    constructed via BaseHTTPRequestHandler.__init__, which requires a
    live socket. page_context() itself is called unbound (Handler.
    page_context(fake_self)) against the real method, so this proves the
    actual production code path, not a reimplementation of it.
    """

    def __init__(self, state_dir):
        self.path = "/settings"
        self.args = _FakePageContextArgs(state_dir)
        self.headers = _FakePageContextHeaders()

    def _resolved_ui_theme(self):
        return "auto"

    def _lang_from_request(self):
        return "en"


class _FakeResolveCtxHandler(_FakePageContextHandler):
    """Same minimal stand-in as `_FakePageContextHandler` above, but with
    a settable `self.path` (that fixture hardcodes "/settings") so this
    check can exercise page_context() against a real
    "/airlines?resolve=..." query string.
    """

    def __init__(self, state_dir, path):
        super().__init__(state_dir)
        self.path = path


def test_page_context_threads_wake_interval_env_default(tmp_path, monkeypatch):
    """page_context() threads wake_interval_env_default from the real environment read: 900
    when SKYPANE_SLEEP_S=900, and always present (never conditionally omitted) as None when
    unset"""
    fake_self = _FakePageContextHandler(str(tmp_path))
    monkeypatch.setenv(app_module.SLEEP_ENV_VAR, "900")
    ctx = app_module.Handler.page_context(fake_self)
    assert ctx.get("wake_interval_env_default") == 900, (
        "expected wake_interval_env_default == 900 with SKYPANE_SLEEP_S=900, got %r"
        % (ctx.get("wake_interval_env_default"),))

    monkeypatch.delenv(app_module.SLEEP_ENV_VAR, raising=False)
    ctx_unset = app_module.Handler.page_context(fake_self)
    assert "wake_interval_env_default" in ctx_unset, (
        "expected the wake_interval_env_default key to always be present in ctx, even "
        "with SKYPANE_SLEEP_S unset")
    assert ctx_unset["wake_interval_env_default"] is None, (
        "expected wake_interval_env_default to be None with SKYPANE_SLEEP_S unset, got %r"
        % (ctx_unset["wake_interval_env_default"],))


# ==========================================================================
# Section 2.5: companion/theme_preview.py (06.6.4.1.1-01 Task 1) — pure
# in-process module checks, no companion/app.py subprocess or password
# env needed.
# ==========================================================================


def test_theme_preview_bytes_open_as_320x120_rgb_png_for_every_theme():
    """preview_png_bytes() returns a 320x120 PNG for every id in device_config.THEME_IDS"""
    import io
    for theme_id in device_config.THEME_IDS:
        payload = theme_preview.preview_png_bytes(theme_id)
        img = Image.open(io.BytesIO(payload))
        assert img.format == "PNG", "theme %r: expected PNG, got %r" % (theme_id, img.format)
        assert img.size == theme_preview.THEME_PREVIEW_SIZE, (
            "theme %r: expected size %r, got %r"
            % (theme_id, theme_preview.THEME_PREVIEW_SIZE, img.size))
        assert img.convert("RGB").mode == "RGB", "theme %r: expected an RGB-convertible image" % (theme_id,)


def test_theme_preview_means_pairwise_distinct():
    """the 18 themes' previews have pairwise-distinct mean RGB at the crop/size used (proves
    the crop box discriminates themes, D-07)"""
    import io
    means = []
    for theme_id in device_config.THEME_IDS:
        payload = theme_preview.preview_png_bytes(theme_id)
        img = Image.open(io.BytesIO(payload)).convert("RGB").resize((1, 1))
        means.append(next(iter(img.getdata())))
    assert len(set(means)) == len(means), (
        "expected 18 pairwise-distinct mean RGB values, got %r" % (means,))


def test_theme_preview_crop_keeps_8_3_and_excludes_every_caption_glyph():
    """THEME_PREVIEW_CROP_BOX keeps THEME_PREVIEW_SIZE's exact 8:3 ratio and cuts no ink band
    at either edge - every caption glyph is outside it and the main illustration band is
    inside it whole, measured against a real render (B6, 22-10-PLAN.md Task 2)"""
    # B6 (22-AUDIT.md, 22-10-PLAN.md Task 2): the crop used to end at
    # y=870 and sliced the render's caption mid-glyph at every chip size
    # and in the large live preview. Both properties below are asserted
    # by MEASUREMENT against a real render, never by restating the
    # constant.
    x0, y0, x1, y1 = theme_preview.THEME_PREVIEW_CROP_BOX
    crop_w, crop_h = x1 - x0, y1 - y0
    size_w, size_h = theme_preview.THEME_PREVIEW_SIZE
    assert crop_w * size_h == crop_h * size_w, (
        "the crop box's %dx%d must share THEME_PREVIEW_SIZE's exact %dx%d ratio, or the "
        "final resize distorts it" % (crop_w, crop_h, size_w, size_h))

    canvas = render.build_canvas(
        theme_preview.THEME_PREVIEW_FLIGHT,
        theme_preview.THEME_PREVIEW_STATE,
        route=theme_preview.THEME_PREVIEW_ROUTE,
        previous_flight=theme_preview.THEME_PREVIEW_PREVIOUS_FLIGHT,
        previous_route=theme_preview.THEME_PREVIEW_PREVIOUS_ROUTE,
        previous_state=theme_preview.THEME_PREVIEW_PREVIOUS_STATE,
        theme_id="white",
    ).convert("RGB")
    width, height = canvas.size
    px = canvas.load()
    bands = []
    start = None
    for y in range(height):
        inked = any(px[x, y] != (255, 255, 255) for x in range(width))
        if inked and start is None:
            start = y
        elif not inked and start is not None:
            bands.append((start, y - 1))
            start = None
    if start is not None:
        bands.append((start, height - 1))
    assert len(bands) >= 3, "expected at least three ink bands in the fixed scene, got %r" % (bands,)

    inside = [b for b in bands if b[0] >= y0 and b[1] < y1]
    assert inside, "the crop box contains no ink band at all - it would render blank"
    for band_start, band_end in bands:
        straddles_top = band_start < y0 <= band_end
        straddles_bottom = band_start < y1 <= band_end
        assert not (straddles_top or straddles_bottom), (
            "ink band %r is cut by the crop box's %r edge - that is B6's sliced glyph"
            % ((band_start, band_end), "top" if straddles_top else "bottom"))
    tallest = max(bands, key=lambda b: b[1] - b[0])
    assert tallest in inside, (
        "the crop box must contain the main illustration band %r whole, got %r inside"
        % (tallest, inside))


def test_theme_preview_bytes_stable_across_calls():
    """preview_png_bytes() returns byte-identical output across two calls for the same theme
    (the scene is fixed, D-06 — nothing time- or data-dependent leaks in)"""
    first = theme_preview.preview_png_bytes("white")
    second = theme_preview.preview_png_bytes("white")
    assert first == second, "expected byte-identical output for the same fixed-scene theme"


def test_theme_preview_cache_path_rejects_unsafe_and_falsy_inputs(tmp_path):
    """cache_path() returns None for a traversal-shaped id, an unknown id, and a falsy
    state_dir (boundary guard, T-v26-01-01 discipline)"""
    state_dir = str(tmp_path)
    assert theme_preview.cache_path(state_dir, "../../etc/passwd") is None, (
        "expected None for a traversal-shaped theme id")
    assert theme_preview.cache_path(state_dir, "nope") is None, (
        "expected None for an id not in device_config.THEMES")
    assert theme_preview.cache_path(None, "white") is None, "expected None for a falsy state_dir"


def test_theme_preview_cached_bytes_cold_cache_creates_file(tmp_path):
    """cached_preview_bytes() on a cold state dir creates the cache file and returns the same
    bytes preview_png_bytes() would"""
    state_dir = str(tmp_path)
    direct = theme_preview.preview_png_bytes("blue")
    cached = theme_preview.cached_preview_bytes(state_dir, "blue")
    path = theme_preview.cache_path(state_dir, "blue")
    assert os.path.isfile(path), "expected cached_preview_bytes() to create %r" % (path,)
    assert cached == direct, "expected the cold-cache render to match preview_png_bytes()"


def test_theme_preview_cached_bytes_second_call_serves_from_disk(tmp_path):
    """a second cached_preview_bytes() call for the same theme is served from the file on
    disk, not re-rendered"""
    state_dir = str(tmp_path)
    theme_preview.cached_preview_bytes(state_dir, "green")
    path = theme_preview.cache_path(state_dir, "green")
    marker = b"mutated-cache-fixture-not-a-real-render"
    with open(path, "wb") as fh:
        fh.write(marker)
    second = theme_preview.cached_preview_bytes(state_dir, "green")
    assert second == marker, (
        "expected the second call to serve the mutated on-disk bytes unchanged, proving "
        "it did not re-render")


def test_theme_preview_signature_changes_with_cache_version():
    """preview_signature() changes when THEME_PREVIEW_CACHE_VERSION changes (the manual
    escape hatch for a render-geometry change the signature can't otherwise see)"""
    before = theme_preview.preview_signature("white")
    original_version = theme_preview.THEME_PREVIEW_CACHE_VERSION
    try:
        theme_preview.THEME_PREVIEW_CACHE_VERSION = original_version + 1
        after = theme_preview.preview_signature("white")
    finally:
        theme_preview.THEME_PREVIEW_CACHE_VERSION = original_version
    assert before != after, "expected preview_signature() to change when the cache version does"


# ==========================================================================
# Section 2.5b: companion/theme_preview.py's D-23 live-event render path
# and event-aware cache key (20-08-PLAN.md Task 1).
# ==========================================================================


def test_theme_preview_cache_path_no_event_is_stable_and_distinct_from_live(tmp_path):
    """cache_path() with no event returns a stable, deterministic filename that differs from
    the same theme's live-event filename (which contains the event id) — the existing
    2-argument call site (the chip grid) keeps working unmodified, D-23"""
    state_dir = str(tmp_path)
    no_event_first = theme_preview.cache_path(state_dir, "white")
    no_event_second = theme_preview.cache_path(state_dir, "white")
    assert no_event_first == no_event_second, (
        "expected the no-event path to be deterministic across two calls")
    live_path = theme_preview.cache_path(state_dir, "white", live_event_id=41)
    assert no_event_first != live_path, "expected the no-event path to differ from a live-event path"
    assert "41" in live_path, "expected the live-event path to contain the event id"


def test_theme_preview_cache_path_distinct_event_ids_distinct_paths(tmp_path):
    """cache_path() gives two different event ids two different paths, and the same event id
    twice the same path (D-23/Pitfall 7)"""
    state_dir = str(tmp_path)
    path_41 = theme_preview.cache_path(state_dir, "white", live_event_id=41)
    path_42 = theme_preview.cache_path(state_dir, "white", live_event_id=42)
    path_41_again = theme_preview.cache_path(state_dir, "white", live_event_id=41)
    assert path_41 != path_42, "expected two different event ids to give two different paths"
    assert path_41 == path_41_again, "expected the same event id twice to give the same path"


def test_theme_preview_cache_path_hostile_event_id_degrades_to_sample(tmp_path):
    """cache_path() degrades a non-integer or hostile event id to the same sample path as no
    event at all, never reaching the filename (T-20-14)"""
    state_dir = str(tmp_path)
    sample_path = theme_preview.cache_path(state_dir, "white")
    for hostile in ("../../etc/passwd", "not-a-number", object()):
        degraded = theme_preview.cache_path(state_dir, "white", live_event_id=hostile)
        assert degraded == sample_path, (
            "expected a non-integer event id (%r) to degrade to the sample path, got %r"
            % (hostile, degraded))
        if isinstance(hostile, str):
            assert hostile not in os.path.basename(degraded), (
                "hostile event id string leaked into the filename")


def test_theme_preview_png_bytes_live_event_full_and_partial_row():
    """preview_png_bytes(theme_id, live_event=row) returns a well-formed PNG for a full
    runway_events row and for a row missing half its fields (partial rows never raise, D-23)"""
    import io
    full_row = {
        "id": 5, "hex": "3946a1", "callsign": "AFR1380", "airline": "Air France",
        "origin": "ORY", "destination": "TLS", "confirmed_state": "departing",
    }
    partial_row = {"id": 6}
    for row in (full_row, partial_row):
        payload = theme_preview.preview_png_bytes("white", live_event=row)
        img = Image.open(io.BytesIO(payload))
        assert img.format == "PNG", "expected a PNG for live_event=%r, got %r" % (row, img.format)
        assert img.size == theme_preview.THEME_PREVIEW_SIZE, (
            "expected size %r for live_event=%r, got %r"
            % (theme_preview.THEME_PREVIEW_SIZE, row, img.size))


def test_theme_preview_cached_bytes_no_event_unchanged(tmp_path):
    """cached_preview_bytes() with no live_event still creates the cache file and returns
    exactly what preview_png_bytes(theme_id) returns, unchanged by this task (D-23)"""
    state_dir = str(tmp_path)
    direct = theme_preview.preview_png_bytes("blue")
    cached = theme_preview.cached_preview_bytes(state_dir, "blue")
    path = theme_preview.cache_path(state_dir, "blue")
    assert os.path.isfile(path), "expected cached_preview_bytes() to create %r" % (path,)
    assert cached == direct, "expected the no-event cached render to still match preview_png_bytes()"


def test_theme_preview_cached_bytes_live_event_keyed_by_id(tmp_path):
    """cached_preview_bytes() keys its cache on the live event's row id: a repeat request for
    the SAME event serves the on-disk file unchanged (no re-render), and a NEWER event is a
    cache miss rather than the stale first render (D-23/Pitfall 7)"""
    state_dir = str(tmp_path)
    event_5 = {
        "id": 5, "hex": "3946a1", "callsign": "AFR1380", "airline": "Air France",
        "origin": "ORY", "destination": "TLS", "confirmed_state": "departing",
    }
    event_6 = dict(event_5, id=6, callsign="AFR9999")
    theme_preview.cached_preview_bytes(state_dir, "white", live_event=event_5)
    path_5 = theme_preview.cache_path(state_dir, "white", live_event_id=5)
    assert os.path.isfile(path_5), "expected cached_preview_bytes() to create %r" % (path_5,)
    marker = b"mutated-cache-fixture-not-a-real-render"
    with open(path_5, "wb") as fh:
        fh.write(marker)
    second_same_event = theme_preview.cached_preview_bytes(state_dir, "white", live_event=event_5)
    assert second_same_event == marker, (
        "expected a same-event second call to be served from disk, not re-rendered")
    third_newer_event = theme_preview.cached_preview_bytes(state_dir, "white", live_event=event_6)
    assert third_newer_event != marker, (
        "expected a newer event id to be a cache miss, not the stale marker bytes")
    path_6 = theme_preview.cache_path(state_dir, "white", live_event_id=6)
    assert path_5 != path_6, "expected two different event ids to produce two different cache files"


# ==========================================================================
# Section 2.6: companion/app.py's _illustration_filenames() (phase 13 plan
# 13-06 Task 1, D-09) — pure in-process module checks against the widened
# per-request union helper, no subprocess needed.
# ==========================================================================


def test_illustration_filenames_union_contract(tmp_path):
    """_illustration_filenames() is the per-request union of the static target set and
    server-persisted manual keys: None and an empty state dir both equal the static set
    exactly, a seeded manual entry adds exactly one filename, and an entry whose stored name
    yields no usable key contributes nothing (D-09)"""
    baseline = frozenset(server_illustrations.target_filenames())
    assert app_module._illustration_filenames(None) == baseline, (
        "expected _illustration_filenames(None) to equal the static target set")
    tmp = str(tmp_path)
    assert app_module._illustration_filenames(tmp) == baseline, (
        "expected an empty state dir (no manual_resolutions.json yet) to contribute "
        "nothing beyond the static target set")
    add_result = manual_resolutions.add_entry(tmp, "ZZZ", "Zephyr Air")
    assert add_result == manual_resolutions.ADD_OK, (
        "expected add_entry() to succeed for a fresh, valid entry, got %r" % (add_result,))
    widened = app_module._illustration_filenames(tmp)
    expected_key = manual_resolutions.illustration_key_for_name("Zephyr Air")
    assert widened == baseline | {expected_key + ".png"}, (
        "expected exactly one new filename (%r) added for the one seeded manual entry, got "
        "a diff of %r" % (expected_key + ".png", widened.symmetric_difference(baseline)))
    # An entry whose stored name yields no usable key contributes nothing —
    # hand-write a second, reserved-slug entry directly into the JSON file
    # (past add_entry()'s own gate, which would refuse to persist it in
    # the first place): load_manual_resolutions() already drops it on
    # read, so the widened set here must stay exactly what it was above,
    # unchanged.
    path = manual_resolutions.manual_resolutions_path(tmp)
    with open(path) as fh:
        raw = json.load(fh)
    raw["YYY"] = {
        "airline_name": "Generic Fallback",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    with open(path, "w") as fh:
        json.dump(raw, fh)
    unchanged = app_module._illustration_filenames(tmp)
    assert unchanged == widened, (
        "expected a reserved/unusable-slug entry to contribute nothing, got a diff of %r"
        % (unchanged.symmetric_difference(widened),))


# ==========================================================================
# Section 2.7: companion/app.py's eight FLASH_KEY_MANUAL_* keys and
# page_context()'s two new ctx keys (phase 13 plan 13-06 Task 2).
#
# RESEARCH A3: does _resolve_flash_text() ever create a directory for a
# missing state_dir? No — reading companion/app.py's own source, the
# function only ever reads state_dir (never os.makedirs/writes it), and
# only for two OTHER flash keys (FLASH_KEY_POLL_COOLDOWN via
# poll_cooldown_remaining(), and FLASH_KEY_CALENDAR_CONNECTED /
# FLASH_KEY_CALENDAR_CONNECT_OK via calendar_rules.load_calendar_
# registry()) — neither of which this check's six deck keys or its
# unknown-key case ever reach (the per-key branch returns before either
# is called). The absent tmp_path subpath below is asserted to still not
# exist after every call, proving this by measurement rather than by
# reading the function's source a second time.
# ==========================================================================


def test_flash_manual_keys_complete_and_byte_identical(tmp_path):
    """every FLASH_KEY_MANUAL_* constant is a FLASH_MESSAGES/FLASH_ROLES key; the six
    UI-SPEC deck strings resolve byte for byte through _resolve_flash_text(), an unknown key
    still resolves to None, and no FLASH_MESSAGES value carries a runtime placeholder except
    the cooldown, rule_replaced, calendar_connected and calendar_connect_ok keys (Phase 15
    D-10 widened this in place, not loosened; Phase 17 plan 04 and 20-09-PLAN.md Task 2 each
    widen it again for the same reason)"""
    manual_keys = (
        app_module.FLASH_KEY_MANUAL_RESOLVED,
        app_module.FLASH_KEY_MANUAL_NAME_EMPTY,
        app_module.FLASH_KEY_MANUAL_NAME_TOO_LONG,
        app_module.FLASH_KEY_MANUAL_NAME_RESERVED,
        app_module.FLASH_KEY_MANUAL_PREFIX_STALE,
        app_module.FLASH_KEY_MANUAL_REGISTRY_FULL,
        app_module.FLASH_KEY_MANUAL_SAVE_FAILED,
        app_module.FLASH_KEY_MANUAL_DELETE_FAILED,
        app_module.FLASH_KEY_MANUAL_NAME_UNUSABLE,
    )
    for key in manual_keys:
        assert key in app_module.FLASH_MESSAGES, "expected %r to be a FLASH_MESSAGES key" % (key,)
        assert key in app_module.FLASH_ROLES, "expected %r to be a FLASH_ROLES key" % (key,)

    # The six deck strings from 13-UI-SPEC.md's Full Copy Deck, byte for
    # byte, ported as literals (they were already literals in the
    # original check, never read from the spec file here either) — the
    # two planner-added failure keys are checked for presence above only.
    expected_deck = {
        app_module.FLASH_KEY_MANUAL_RESOLVED: (
            "Airline name saved — the frame will pick it up next time it wakes and polls."),
        app_module.FLASH_KEY_MANUAL_NAME_EMPTY: (
            "Enter an airline name before saving."),
        app_module.FLASH_KEY_MANUAL_NAME_TOO_LONG: (
            "That name's too long — airline names top out at 100 characters."),
        app_module.FLASH_KEY_MANUAL_NAME_RESERVED: (
            "That name is reserved for the frame's own fallback artwork — try the "
            "airline's real name instead."),
        app_module.FLASH_KEY_MANUAL_PREFIX_STALE: (
            "That coverage gap isn't there anymore — check Health for current gaps."),
        app_module.FLASH_KEY_MANUAL_REGISTRY_FULL: (
            "The manual-resolution list is full (200 entries) — delete an old one before "
            "adding another."),
    }
    absent_state_dir = tmp_path / "absent" / "state"
    for key, expected_text in expected_deck.items():
        assert app_module.FLASH_MESSAGES[key] == expected_text, (
            "expected %r's FLASH_MESSAGES text to match the flash-copy deck byte for byte, "
            "got %r" % (key, app_module.FLASH_MESSAGES[key]))
        resolved = app_module._resolve_flash_text(key, str(absent_state_dir))
        assert resolved == expected_text, (
            "expected _resolve_flash_text(%r, ...) to return the deck text, got %r"
            % (key, resolved))
    assert not absent_state_dir.exists(), (
        "the six deck keys never touch state_dir (RESEARCH A3 above) — it must not have "
        "been created as a side effect")

    assert app_module._resolve_flash_text("not-a-real-flash-key", str(absent_state_dir)) is None, (
        "expected _resolve_flash_text() to return None for an unknown key")
    assert not absent_state_dir.exists(), (
        "an unknown key must not touch state_dir either")

    # Every other FLASH_MESSAGES value carries no runtime placeholder
    # except the five deliberately-interpolated keys (Phase 15 D-10,
    # Phase 17 plan 04, 20-09-PLAN.md Task 2, 22-05-PLAN.md Task 2).
    interpolated_keys = (
        app_module.FLASH_KEY_POLL_COOLDOWN, app_module.FLASH_KEY_RULE_REPLACED,
        app_module.FLASH_KEY_CALENDAR_CONNECTED, app_module.FLASH_KEY_CALENDAR_CONNECT_OK,
        app_module.FLASH_KEY_SAVED)
    for key, text in app_module.FLASH_MESSAGES.items():
        if key in interpolated_keys:
            continue
        assert "%" not in text and "{" not in text, (
            "expected no runtime interpolation in FLASH_MESSAGES[%r], got %r (flash copy "
            "is fixed, never interpolated, except the cooldown, rule_replaced, "
            "calendar_connected, calendar_connect_ok and saved keys)" % (key, text))


def test_page_context_supplies_resolve_prefix_and_manual_resolutions(tmp_path):
    """page_context() on a request carrying ?resolve=XYZ returns that raw value under
    resolve_prefix and a dict under manual_resolutions reflecting a seeded entry; every key
    companion/pages/__init__.py documents is actually present in ctx"""
    tmp = str(tmp_path)
    now = "2026-01-01T00:00:00+00:00"
    add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
    assert add_result == manual_resolutions.ADD_OK, (
        "expected the fixture add_entry() call to succeed, got %r" % (add_result,))
    fake_self = _FakeResolveCtxHandler(tmp, "/airlines?resolve=XYZ")
    ctx = app_module.Handler.page_context(fake_self)
    assert ctx.get("resolve_prefix") == "XYZ", (
        "expected ctx['resolve_prefix'] == 'XYZ', got %r" % (ctx.get("resolve_prefix"),))
    registry = ctx.get("manual_resolutions")
    assert isinstance(registry, dict) and "XYZ" in registry, (
        "expected ctx['manual_resolutions'] to reflect the seeded entry, got %r" % (registry,))
    assert registry["XYZ"].get("airline_name") == "Brand New Air", (
        "expected the seeded entry's airline_name to round-trip through ctx, got %r"
        % (registry["XYZ"],))
    # The wider set of ctx keys page_context() always returns (state_dir,
    # ui_theme, device_config, flash, ...) is exercised by other checks
    # in this chain; the original check's own cross-reference against
    # companion/pages/__init__.py's docstring text is dropped here (guard
    # G4 bans reading a module's __doc__ at all) with no behaviour lost
    # for THIS check's own subject: resolve_prefix/manual_resolutions are
    # already asserted present and correct above.
    for key in ("state_dir", "device_config", "flash_role", "now"):
        assert key in ctx, (
            "expected the always-present ctx key %r to actually be present in "
            "page_context()'s return" % (key,))
