"""Part 04b of the `companion/test_companion_app.py` migration chain
(33-17-PLAN.md): ledger rows 223-266 (fragment `33-ledger/companion__
test_companion_app.md`) — the LAST anchor of part 04.

Continues `companion/test_companion_app_04.py` (rows 178-222) with: the
redirect/static-CSS hardening headers, the session-gated POST /ui-theme
and POST /logout, the POST /ui-lang round trip and its no-session gate,
the retired POST /ui-mode's unknown-route 404, D-03 language resolution
(Accept-Language, the sp_ui_lang cookie precedence), the nav toggle's
gear glyph and translated aria-label, the wake-interval environment
pre-fill/floor, the login ?next= round trip for a real NAV_TABS member,
two cross-module route/nav standing-contract guards, the logout/replay/
GET-logout/post-logout-tab cluster, the 404 page-header/health-dot leak
guard, the retired /preview.png route, gallery path-traversal rejection
with a canary file, the illustration image route (real key/unknown key/
traversal/unauthenticated redirect, two isolated manual-resolution-key
checks), the theme-preview image route (real key/unknown key/traversal/
unauthenticated redirect, and the stateful ?live=1 cache/fallback
branch), and — the LAST anchor — the real-PNG illustration upload round
trip over a real HTTP POST.

Every check that ends a session (logout), needs its own subprocess
environment (the wake-interval pre-fill/floor checks), or writes an
override file into `illustration_overrides/` gets its own fresh,
function-scoped `make_app_server` server (33-MIGRATION-RULES.md section
2) — the manual-resolution-key checks and the upload round trip
deliberately never share the module's read-only server, mirroring the
original harness's own isolated `Harness()` instances for the same
reason (D-03's exact-one-file assertion on the shared state dir belongs
to 33-18/part 05, downstream of this plan's own LAST anchor, and is
never exercised here — the isolation is kept anyway, matching the
plan's own hotspot instruction). Every other check here only reads (or
writes a local fixture file directly into the shared server's own state
dir, never through a mutating HTTP POST) and shares one module-scoped,
already-logged-in server.
"""
import os
import re
import urllib.parse

import pytest

import companion.i18n as i18n_module
import companion.layout as layout
import companion.test_companion_app_helpers as cah
from companion import auth
from companion import theme_preview
from companion_app_server import http_request, login
from companion_markup import parse_html
from server import device_config, history_db
from server.plane import manual_resolutions

import companion.app as app_module
from companion.pages import health_page

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IMAGE_BYTES = 960000  # server/panel_format.py's IMAGE_BYTES, duplicated as a
# plain literal so this module never has to import Pillow (or
# server.panel_format) itself — mirrors the legacy harness's own
# documented precedent for this exact duplication.

_VENDORED_ILLUSTRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "server", "assets", "icons", "illustrations")


@pytest.fixture(scope="module")
def app04b_server(module_app_server_factory):
    """One module-scoped `companion/app.py` server shared by every check in this module that
    only reads, or writes a local fixture file directly into the server's own state dir (never
    through a mutating HTTP POST, and never ending the shared session). See the module
    docstring for which checks get their own dedicated server instead.
    """
    return module_app_server_factory(fake_providers=True)


@pytest.fixture(scope="module")
def session_cookie(app04b_server):
    """One shared login for every authenticated-but-read-only check below."""
    return login(app04b_server)


@pytest.fixture(scope="module")
def seeded_stale_pipeline_run(app04b_server):
    """Seeds a stale `META_LAST_PIPELINE_RUN` once — `health_page.overall_severity()` resolves
    this to "error", giving the two 404/health-dot checks below the same non-"ok" state to test
    the authenticated/unauthenticated split against.
    """
    with history_db.open_db(app04b_server.state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_PIPELINE_RUN,
            _ago_iso(health_page.STALE_PIPELINE_ERROR_S + 60))
    return None


def _ago_iso(seconds):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat(
        timespec="seconds")


# ==========================================================================
# hardening headers on a redirect and on the static CSS response
# ==========================================================================


def test_redirect_carries_four_hardening_headers(app04b_server):
    """a 303 redirect response (the unauthenticated bounce to /login) carries all four
    hardening headers, including the CSP — before this plan redirect() sent none of them"""
    status, headers, _ = http_request(app04b_server.base_url() + "/display")
    assert status == 303, "expected a 303 redirect, got %d" % status
    for header_name in (
            "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy",
            "Content-Security-Policy"):
        assert header_name in headers, "expected %r on a 303 redirect response" % header_name


def test_static_css_response_carries_csp(app04b_server):
    """the static CSS response (the send_bytes() path) also carries the CSP header"""
    status, headers, _ = http_request(app04b_server.base_url() + "/static/style.css")
    assert status == 200, "expected 200, got %d" % status
    assert "Content-Security-Policy" in headers, (
        "expected the CSP header on the static CSS response too")


# ==========================================================================
# session-gated POST /ui-theme and POST /logout; POST /ui-lang round
# trip and its own no-session gate; the retired POST /ui-mode
# ==========================================================================


def test_ui_theme_post_without_session_redirects_to_login(app04b_server):
    """POST /ui-theme with no session cookie redirects to /login and does not set a ui_theme
    cookie (T-19-04: an unauthenticated caller cannot set another visitor's UI theme)"""
    status, headers, _ = http_request(
        app04b_server.base_url() + "/ui-theme", method="POST", data=b"ui_theme=dark")
    assert status == 303 and headers.get("Location") == "/login", (
        "expected an unauthenticated POST /ui-theme to redirect to /login, got %d/%r"
        % (status, headers.get("Location")))
    set_cookie = headers.get("Set-Cookie", "")
    assert auth.UI_THEME_COOKIE_NAME not in set_cookie, (
        "expected no ui_theme Set-Cookie header on an unauthenticated POST /ui-theme, got %r"
        % set_cookie)


def test_logout_post_without_session_redirects_to_login(app04b_server):
    """POST /logout with no session cookie redirects to /login (T-19-04: gating a logout costs
    a signed-out caller nothing)"""
    status, headers, _ = http_request(app04b_server.base_url() + "/logout", method="POST")
    assert status == 303 and headers.get("Location") == "/login", (
        "expected an unauthenticated POST /logout to redirect to /login, got %d/%r"
        % (status, headers.get("Location")))


def test_ui_lang_post_round_trip(app04b_server, session_cookie):
    """POST /ui-lang with ui_lang=fr/en sets the sp_ui_lang cookie (HttpOnly, SameSite=Strict)
    and redirects to the referring tab; ui_lang=de sets no cookie"""
    base = app04b_server.base_url()
    for submitted, expect_cookie in (("fr", True), ("en", True), ("de", False)):
        status, headers, _ = http_request(
            base + "/ui-lang", method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode({"ui_lang": submitted}).encode())
        assert status == 303, "expected 303 for ui_lang=%s, got %d" % (submitted, status)
        assert headers.get("Location") == "/", (
            "expected a redirect to the referring tab (default /), got %r" % headers.get("Location"))
        set_cookie = headers.get("Set-Cookie", "")
        if expect_cookie:
            assert "%s=%s" % (auth.UI_LANG_COOKIE_NAME, submitted) in set_cookie, (
                "expected %s=%s in %r" % (auth.UI_LANG_COOKIE_NAME, submitted, set_cookie))
            for needle in ("HttpOnly", "SameSite=Strict"):
                assert needle in set_cookie, (
                    "expected %r in the sp_ui_lang cookie header: %r" % (needle, set_cookie))
        else:
            assert auth.UI_LANG_COOKIE_NAME not in set_cookie, (
                "expected no sp_ui_lang Set-Cookie header for an unrecognised ui_lang=%s, got %r"
                % (submitted, set_cookie))


def test_ui_lang_post_without_session_redirects_to_login(app04b_server):
    """POST /ui-lang with no session cookie redirects to /login and does not set a sp_ui_lang
    cookie (T-20-01)"""
    status, headers, _ = http_request(
        app04b_server.base_url() + "/ui-lang", method="POST", data=b"ui_lang=fr")
    assert status == 303 and headers.get("Location") == "/login", (
        "expected an unauthenticated POST /ui-lang to redirect to /login, got %d/%r"
        % (status, headers.get("Location")))
    set_cookie = headers.get("Set-Cookie", "")
    assert auth.UI_LANG_COOKIE_NAME not in set_cookie, (
        "expected no sp_ui_lang Set-Cookie header on an unauthenticated POST /ui-lang, got %r"
        % set_cookie)


def test_post_to_the_deleted_display_mode_route_with_session_now_404s(app04b_server, session_cookie):
    """POST /ui-mode with a valid session now takes the unknown-route 404 path (D-17, the
    route/handler/dispatch line are deleted together)"""
    status, headers, _ = http_request(
        app04b_server.base_url() + "/ui-mode", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"value": "simple"}).encode())
    assert status == 404, (
        "expected a valid-session POST /ui-mode to take the unknown-route 404 path now that the "
        "route is deleted (D-17/T-21-01), got %d" % status)
    set_cookie = headers.get("Set-Cookie", "")
    assert "sp_ui_mode" not in set_cookie, (
        "expected no sp_ui_mode Set-Cookie header — the cookie name is never written by any "
        "code path any more, got %r" % set_cookie)


# ==========================================================================
# D-03: language resolution from cookie / Accept-Language
# ==========================================================================


def test_accept_language_resolves_html_lang_with_no_cookie(app04b_server, session_cookie):
    """a cookie-free GET (session cookie only, no sp_ui_lang) with Accept-Language:
    fr-FR,fr;q=0.9 renders <html lang="fr"; with Accept-Language: en-GB renders
    <html lang="en" (D-03)"""
    base = app04b_server.base_url()
    status, _headers, body = http_request(
        base + "/", cookie=session_cookie, extra_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
    assert status == 200, "expected 200, got %d" % status
    assert b'<html lang="fr"' in body, "expected <html lang=\"fr\" with Accept-Language: fr-FR,fr;q=0.9"
    status, _headers, body = http_request(
        base + "/", cookie=session_cookie, extra_headers={"Accept-Language": "en-GB"})
    assert status == 200, "expected 200, got %d" % status
    assert b'<html lang="en"' in body, "expected <html lang=\"en\" with Accept-Language: en-GB"


def test_ui_lang_cookie_beats_accept_language(app04b_server, session_cookie):
    """the sp_ui_lang cookie beats Accept-Language when both are present (D-03)"""
    from companion_app_server import cookie_value
    base = app04b_server.base_url()
    status, headers, _ = http_request(
        base + "/ui-lang", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"ui_lang": "en"}).encode())
    lang_cookie = cookie_value(headers)
    assert status == 303 and lang_cookie, (
        "expected a 303 with a sp_ui_lang Set-Cookie, got %d/%r" % (status, headers.get("Set-Cookie")))
    combined_cookie = "%s; %s" % (session_cookie, lang_cookie)
    status, _headers, body = http_request(
        base + "/", cookie=combined_cookie, extra_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
    assert status == 200, "expected 200, got %d" % status
    assert b'<html lang="en"' in body, (
        "expected the sp_ui_lang=en cookie to beat a French Accept-Language header, got a body "
        "without <html lang=\"en\"")


# ==========================================================================
# 28-01-PLAN.md (CFG-76): the mobile toggle's gear glyph and its label
# ==========================================================================


def test_the_nav_toggle_wears_the_gear_and_opens_the_same_panel(app04b_server, session_cookie):
    """#site-nav-toggle renders icon-gear (never icon-hamburger), its aria-label is
    NAV_TOGGLE_LABEL translated through i18n's real per-request path in both EN and FR, and the
    panel it opens still holds the language/theme switches and Sign out with zero
    page-navigation links (CFG-76)"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    toggle_start = doc.index('id="%s"' % layout.NAV_TOGGLE_ID)
    toggle_end = doc.index("</button>", toggle_start) + len("</button>")
    toggle_markup = doc[toggle_start:toggle_end]
    assert "icon-gear" in toggle_markup, (
        "expected #site-nav-toggle's markup to reference icon-gear, got %r" % toggle_markup)
    assert toggle_markup.count("icon-hamburger") == 0, (
        "expected zero icon-hamburger references in #site-nav-toggle, got %d"
        % toggle_markup.count("icon-hamburger"))

    expected_en = i18n_module.t_lang(layout.NAV_TOGGLE_LABEL, "en")
    expected_fr = i18n_module.t_lang(layout.NAV_TOGGLE_LABEL, "fr")
    assert expected_fr != layout.NAV_TOGGLE_LABEL, (
        "expected a real French translation for NAV_TOGGLE_LABEL, got the English source back "
        "unchanged")
    base = app04b_server.base_url()
    status, _headers, body = http_request(
        base + "/", cookie=session_cookie, extra_headers={"Accept-Language": "en-GB"})
    assert status == 200, "expected 200 for the English-language GET, got %d" % status
    en_needle = ('aria-label="%s"' % layout.escape_html(expected_en)).encode("utf-8")
    assert en_needle in body, "expected the EN toggle aria-label %r in the rendered body" % en_needle
    status, _headers, body = http_request(
        base + "/", cookie=session_cookie, extra_headers={"Accept-Language": "fr-FR,fr;q=0.9"})
    assert status == 200, "expected 200 for the French-language GET, got %d" % status
    fr_needle = ('aria-label="%s"' % layout.escape_html(expected_fr)).encode("utf-8")
    assert fr_needle in body, "expected the FR toggle aria-label %r in the rendered body" % fr_needle

    doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    for needle, name in (
            ('action="/ui-lang"', "the language switch"),
            ('action="/ui-theme"', "the theme switch"),
            ('action="/logout"', "Sign out")):
        assert needle in panel, "expected %s inside the dropdown" % name
    assert "<a href" not in panel, (
        "expected zero page-navigation <a href> links in the dropdown, found one")


# ==========================================================================
# 11-04 / wake-interval environment pre-fill and its below-floor case
# ==========================================================================


def test_wake_interval_env_prefill_and_on_disk_precedence(make_app_server):
    """authenticated GET /device pre-fills Wake interval with SKYPANE_SLEEP_S=900 when nothing
    is stored, and a stored wake_interval_s=120 always wins over that environment value"""
    server = make_app_server(fake_providers=True, env_overrides={app_module.SLEEP_ENV_VAR: "900"})
    cookie = login(server)
    base = server.base_url()

    status, _headers, body = http_request(base + "/device", cookie=cookie)
    assert status == 200, "expected 200 for the env-only pre-fill case, got %d" % status
    assert re.search(rb'name="wake_interval_s"[^>]*value="900"', body), (
        "expected the Wake interval input to carry value=\"900\" pre-filled from "
        "SKYPANE_SLEEP_S=900 with nothing stored")

    device_config.save_device_config(server.state_dir, wake_interval_s=120)
    status, _headers, body = http_request(base + "/device", cookie=cookie)
    assert status == 200, "expected 200 after storing wake_interval_s=120, got %d" % status
    assert re.search(rb'name="wake_interval_s"[^>]*value="120"', body), (
        "expected the stored wake_interval_s=120 to win over the SKYPANE_SLEEP_S=900 "
        "environment pre-fill")
    assert not re.search(rb'name="wake_interval_s"[^>]*value="900"', body), (
        "expected the environment value 900 to no longer appear once a value is stored on disk")


def test_wake_interval_below_floor_env_degrades_to_placeholder(make_app_server):
    """authenticated GET /device degrades a below-floor SKYPANE_SLEEP_S=30 (the shipped
    deploy/skypane.env.example value) to the placeholder empty state, never a value attribute
    the form could not submit"""
    from companion.pages import config_page
    server = make_app_server(fake_providers=True, env_overrides={app_module.SLEEP_ENV_VAR: "30"})
    cookie = login(server)
    status, _headers, body = http_request(server.base_url() + "/device", cookie=cookie)
    assert status == 200, "expected 200, got %d" % status
    assert b'name="wake_interval_s"' in body, "expected the Wake interval input to still be present"
    assert not re.search(rb'name="wake_interval_s"[^>]*\bvalue="', body), (
        "expected no value attribute on the Wake interval input for a below-floor "
        "SKYPANE_SLEEP_S=30 — it must not render a number the form could not submit")
    assert config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT.encode() in body, (
        "expected the placeholder text for a below-floor environment value")


def test_login_get_with_settings_next_carries_hidden_field(app04b_server):
    """GET /login?next=/display (a real NAV_TABS member) renders a hidden next field carrying
    /display, surviving the round trip"""
    status, _headers, body = http_request(app04b_server.base_url() + "/login?next=/display")
    assert status == 200, "expected 200, got %d" % status
    assert b'name="next" value="/display"' in body, (
        "expected the recognised /display ?next= value to survive the round trip as a rendered "
        "hidden field")


# ==========================================================================
# route/nav cross-module standing-contract guards (pure in-process)
# ==========================================================================


def test_settings_route_and_icon_map_cross_module_contract():
    """app.SETTINGS_ROUTE and config_page.SETTINGS_ROUTE agree, NAV_TABS opens with HOME_ROUTE,
    and NAV_ICON_IDS' keys equal the nav route slugs one-to-one"""
    from companion.pages import config_page
    assert app_module.SETTINGS_ROUTE == config_page.SETTINGS_ROUTE, (
        "expected app.SETTINGS_ROUTE == config_page.SETTINGS_ROUTE")
    assert layout.NAV_TABS[0][0] == layout.HOME_ROUTE and app_module.HOME_ROUTE == layout.HOME_ROUTE, (
        "expected NAV_TABS[0][0] and app.HOME_ROUTE to both be layout.HOME_ROUTE")
    nav_slugs = {layout.nav_slug(route) for route, _ in layout.NAV_TABS}
    assert set(layout.NAV_ICON_IDS) == nav_slugs, (
        "expected NAV_ICON_IDS' keys to equal the set of nav route slugs, got %r vs %r"
        % (set(layout.NAV_ICON_IDS), nav_slugs))


def test_nav_page_titles_icon_route_standing_contract_guard():
    """the nav tuple, the page-titles dict, and the slug-to-icon map all agree in size and key
    set, and the settings page module's own route constant is the nav tuple's first route — a
    standing guard against silent drift when the route set changes again"""
    nav_routes = [route for route, _ in layout.NAV_TABS]
    nav_slugs = {layout.nav_slug(route) for route in nav_routes}
    page_title_keys = set(app_module._PAGE_TITLES)
    assert page_title_keys == set(nav_routes), (
        "expected _PAGE_TITLES' keys to equal the set of NAV_TABS routes, got %r vs %r"
        % (page_title_keys, set(nav_routes)))
    assert len(app_module._PAGE_TITLES) == len(layout.NAV_TABS), (
        "expected _PAGE_TITLES and NAV_TABS to have the same length, got %d vs %d"
        % (len(app_module._PAGE_TITLES), len(layout.NAV_TABS)))
    icon_slugs = set(layout.NAV_ICON_IDS)
    assert icon_slugs == nav_slugs, (
        "expected NAV_ICON_IDS' keys to equal the set of NAV_TABS slugs one-to-one, got %r vs %r"
        % (icon_slugs, nav_slugs))
    assert layout.NAV_TABS[0][0] == layout.HOME_ROUTE, (
        "expected NAV_TABS' first route to be HOME_ROUTE, got %r" % (layout.NAV_TABS[0][0],))


# ==========================================================================
# logout clears the cookie; a replayed or absent cookie is refused
# afterward (238-241 consolidated: one dedicated session, one atomic
# sequence — logging out on the module's shared session would break
# every other shared-session check in this module)
# ==========================================================================


def test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward(make_app_server):
    """POST /logout clears the session cookie (Max-Age=0); replaying the exact session cookie
    after Sign out is rejected (A-33: revoked server-side, not just cleared client-side); GET
    /logout no longer accepts the request (404, D-11 closes the GET-triggered logout hole); and
    a tab request after logout with no cookie presented is refused again"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session_cookie = login(server)

    # A GET with this exact session_cookie succeeds before logout runs.
    status, _headers, _body = http_request(base + "/display", cookie=session_cookie)
    assert status == 200, "expected the fresh session to reach /display before logout, got %d" % status

    status, headers, _ = http_request(base + "/logout", method="POST", cookie=session_cookie)
    assert status == 303, "expected a 303 redirect on logout, got %d" % status
    set_cookie = headers.get("Set-Cookie", "")
    assert "Max-Age=0" in set_cookie, (
        "expected the logout cookie header to carry Max-Age=0, got %r" % set_cookie)

    status, headers, _ = http_request(base + "/display", cookie=session_cookie)
    assert status == 303 and headers.get("Location") == "/login?next=%2Fdisplay", (
        "expected the logged-out session cookie to be rejected with a redirect to "
        "/login?next=%%2Fdisplay, got %d/%r" % (status, headers.get("Location")))

    status, _headers, _body = http_request(base + "/logout", cookie=session_cookie)
    assert status == 404, "expected GET /logout to 404 (D-11), got %d" % status

    status, headers, _ = http_request(base + "/display")
    assert status == 303 and headers.get("Location") == "/login?next=%2Fdisplay", (
        "expected a redirect to /login?next=%%2Fdisplay for a post-logout request, got %d/%r"
        % (status, headers.get("Location")))


# ==========================================================================
# 404: shared page_header(), the Health nav dot gated on auth
# ==========================================================================


def test_unknown_path_404(app04b_server):
    """an unknown path returns 404 with the exact 'Page not found.' copy"""
    status, _headers, body = http_request(app04b_server.base_url() + "/this-route-does-not-exist")
    assert status == 404, "expected 404, got %d" % status
    assert b"Page not found." in body, "expected the exact 404 copy in the response body"


def test_authenticated_404_uses_page_header_and_shows_health_dot(
        app04b_server, session_cookie, seeded_stale_pipeline_run):
    """an authenticated 404 opens with the shared page_header() (page-title, not text-heading)
    and shows the Health nav dot when state is seeded error"""
    status, _headers, body = http_request(
        app04b_server.base_url() + "/this-route-does-not-exist-uir16", cookie=session_cookie)
    assert status == 404, "expected 404, got %d" % status
    assert b'<h1 class="page-title">' in body, (
        "expected the shared page_header() heading (<h1 class=\"page-title\">), the 30px serif "
        "role every other authenticated page opens with")
    assert b'<h1 class="text-heading">' not in body, (
        "expected the old text-heading 404 heading to be gone")
    assert b"dot--error" in body, (
        "expected the Health nav dot (dot--error) to render for an authenticated caller under "
        "seeded error state")


def test_unauthenticated_404_never_leaks_health_state(app04b_server, seeded_stale_pipeline_run):
    """an UNAUTHENTICATED 404 renders no health-dot markup under the same seeded error state —
    the leak guard for the two pre-auth call sites (_serve_stylesheet, _serve_script_file)"""
    status, _headers, body = http_request(
        app04b_server.base_url() + "/this-route-does-not-exist-uir16-unauth")
    assert status == 404, "expected 404, got %d" % status
    assert b"dot--error" not in body and b"dot--warn" not in body, (
        "expected NO health-dot markup for an unauthenticated 404, even under the same seeded "
        "error state — this is the leak guard")


# ==========================================================================
# preview.png: retired route, 404s even with a real panel present
# ==========================================================================


def test_preview_png_404_even_with_real_panel(app04b_server, session_cookie):
    """authenticated GET /preview.png returns 404 with the exact 'Page not found.' copy even
    with a real 960,000-byte panel.bin present — the route is gone, not empty"""
    with open(os.path.join(app04b_server.state_dir, "panel.bin"), "wb") as fh:
        fh.write(b"\x11" * IMAGE_BYTES)
    status, _headers, body = http_request(
        app04b_server.base_url() + "/preview.png", cookie=session_cookie)
    assert status == 404, (
        "expected 404 for the retired route even with a real panel present, got %d" % status)
    assert b"Page not found." in body, "expected the exact 404 copy in the response body"


# ==========================================================================
# gallery path-traversal rejection, with a canary file one level up
# ==========================================================================


def test_gallery_response_is_never_shared_cacheable(app04b_server, session_cookie):
    """an authenticated gallery image is never advertised as storable by a shared/intermediary
    cache (WR-02)"""
    gallery_dir = os.path.join(app04b_server.state_dir, "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    gallery_filename = "260829-0rl-cache-control-fixture.png"
    gallery_path = os.path.join(gallery_dir, gallery_filename)
    with open(gallery_path, "wb") as fh:
        fh.write(PNG_SIGNATURE + b"not-a-real-panel-just-a-fixture")
    status, headers, _body = http_request(
        app04b_server.base_url() + "/gallery/" + gallery_filename, cookie=session_cookie)
    assert status == 200, (
        "expected 200 for a gallery fixture written to %r, got %d (a 404 here means the "
        "fixture landed in the wrong directory, not that the caching header is wrong)"
        % (gallery_path, status))
    cache_control = headers.get("Cache-Control", "")
    directives = [part.strip() for part in cache_control.split(",")]
    assert "public" not in directives, (
        "an authenticated gallery image must never be advertised as storable by a shared cache "
        "— got Cache-Control: %r" % cache_control)
    assert "private" in directives, (
        "expected the non-shared (private) Cache-Control scope on an authenticated gallery "
        "response, got %r" % cache_control)
    assert "max-age=3600" in directives, (
        "expected a 3600-second max-age on the gallery response, got %r" % cache_control)


def test_gallery_traversal_and_canary_never_leaks(app04b_server, session_cookie):
    """a gallery request with parent-directory segments, an absolute path, or a null byte all
    return 404, and the canary file placed one level above the gallery directory never appears
    in any traversal response"""
    gallery_dir = os.path.join(app04b_server.state_dir, "gallery")
    os.makedirs(gallery_dir, exist_ok=True)
    canary_marker = "TOP-SECRET-CANARY-MARKER-DO-NOT-SERVE"
    with open(os.path.join(app04b_server.state_dir, "canary.txt"), "w") as fh:
        fh.write(canary_marker)

    traversal_payloads = (
        ("parent-directory segments", "../canary.txt"),
        ("an absolute path", os.path.join(app04b_server.state_dir, "canary.txt")),
        ("a null byte", "canary.txt\x00.png"),
    )
    base = app04b_server.base_url()
    for label, payload in traversal_payloads:
        encoded = urllib.parse.quote(payload, safe="")
        status, _headers, body = http_request(base + "/gallery/" + encoded, cookie=session_cookie)
        assert status == 404, "expected 404 for %s (%r), got %d" % (label, payload, status)
        assert canary_marker.encode() not in body, (
            "the canary file's content leaked into a traversal response body for %s" % label)


# ==========================================================================
# illustration image route (D-15, 06.6.4.1-02)
# ==========================================================================


def test_illustration_real_key_returns_png(app04b_server, session_cookie):
    """an authenticated GET /illustration/air-france.png returns 200, image/png, and a
    non-empty body"""
    status, headers, body = http_request(
        app04b_server.base_url() + "/illustration/air-france.png", cookie=session_cookie)
    assert status == 200, "expected 200 for a real illustration key, got %d" % status
    assert headers.get("Content-Type") == "image/png", (
        "expected Content-Type image/png, got %r" % headers.get("Content-Type"))
    assert body, "expected a non-empty response body"


def test_illustration_unknown_key_404(app04b_server, session_cookie):
    """an authenticated GET for an illustration key not in the membership set returns 404"""
    status, _headers, _body = http_request(
        app04b_server.base_url() + "/illustration/not-a-real-airline.png", cookie=session_cookie)
    assert status == 404, "expected 404 for a key not in the membership set, got %d" % status


def test_illustration_traversal_key_404(app04b_server, session_cookie):
    """authenticated GET requests for adversarial illustration paths (path traversal) all
    return 404 with no file content"""
    adversarial_paths = [
        "/illustration/..%2F..%2Fetc%2Fpasswd.png",
        "/illustration/../../../etc/passwd.png",
        "/illustration/style.png",
    ]
    base = app04b_server.base_url()
    for adversarial_path in adversarial_paths:
        status, _headers, body = http_request(base + adversarial_path, cookie=session_cookie)
        assert status == 404, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)
        assert not (body and b"root:" in body), (
            "adversarial path %r returned file content" % (adversarial_path,))


def test_illustration_unauthenticated_redirects_to_login(app04b_server):
    """an unauthenticated GET /illustration/air-france.png redirects to /login, never returns
    image bytes"""
    status, headers, body = http_request(
        app04b_server.base_url() + "/illustration/air-france.png")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "/login" in location, "expected a redirect to /login, got %r" % location
    assert not body.startswith(PNG_SIGNATURE), (
        "unauthenticated request must never return image bytes")


# --- widened membership set: manual-resolution keys (phase 13 plan
# 13-06 Task 1, D-09). Both checks below get their own isolated,
# function-scoped server rather than the module's shared one: they
# write real files into illustration_overrides/, matching the plan's
# own hotspot instruction. ---


def test_illustration_manual_key_read_path_states(make_app_server):
    """GET /illustration/{key}.png for a manual key: 404 with no registry entry, 404 with an
    entry but no override file, and 200/image/png once both exist"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)
    manual_prefix = "SWK"
    manual_name = "Skyward Air"
    manual_key = manual_resolutions.illustration_key_for_name(manual_name)

    status, _headers, _body = http_request(
        base + "/illustration/%s.png" % manual_key, cookie=session)
    assert status == 404, "expected 404 with no manual entry registered, got %d" % status

    add_result = manual_resolutions.add_entry(server.state_dir, manual_prefix, manual_name)
    assert add_result == manual_resolutions.ADD_OK, (
        "expected add_entry() to succeed for a fresh entry, got %r" % (add_result,))
    status, _headers, _body = http_request(
        base + "/illustration/%s.png" % manual_key, cookie=session)
    assert status == 404, (
        "expected 404 for a registered manual key with no override file yet — a member of the "
        "set with no bytes is a 404, indistinguishable from a non-member, got %d" % status)

    override_dir = os.path.join(server.state_dir, "illustration_overrides")
    os.makedirs(override_dir, exist_ok=True)
    with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
        seed_bytes = fh.read()
    with open(os.path.join(override_dir, manual_key + ".png"), "wb") as fh:
        fh.write(seed_bytes)
    status, headers, body = http_request(
        base + "/illustration/%s.png" % manual_key, cookie=session)
    assert status == 200, (
        "expected 200 once both the manual entry and the override file exist, got %d" % status)
    assert headers.get("Content-Type") == "image/png", (
        "expected Content-Type image/png, got %r" % headers.get("Content-Type"))
    assert body, "expected a non-empty response body"


def test_illustration_manual_key_post_unregistered_then_registered(make_app_server):
    """Pitfall 3's warning sign made executable: POST /illustration/{key}.png for a manual key
    that was never registered returns 404 and writes nothing to the override directory; once the
    key is registered via add_entry(), the identical POST succeeds"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    session = login(server)
    manual_prefix = "BWX"
    manual_name = "Boreal Wings"
    manual_key = manual_resolutions.illustration_key_for_name(manual_name)
    with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
        payload_bytes = fh.read()
    body, content_type = cah.encode_multipart(payload_bytes, filename="x.png")
    override_dir = os.path.join(server.state_dir, "illustration_overrides")
    override_path = os.path.join(override_dir, manual_key + ".png")
    before_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []

    status, _headers, _body = http_request(
        base + "/illustration/%s.png" % manual_key, method="POST", data=body,
        cookie=session, content_type=content_type)
    assert status == 404, "expected 404 for a never-registered manual key, got %d" % status
    after_entries = sorted(os.listdir(override_dir)) if os.path.isdir(override_dir) else []
    assert after_entries == before_entries, (
        "expected the override directory to gain nothing from a single-request upload of an "
        "unregistered key (Pitfall 3), before=%r after=%r" % (before_entries, after_entries))

    add_result = manual_resolutions.add_entry(server.state_dir, manual_prefix, manual_name)
    assert add_result == manual_resolutions.ADD_OK, (
        "expected add_entry() to succeed for a fresh entry, got %r" % (add_result,))
    status, headers, _body = http_request(
        base + "/illustration/%s.png" % manual_key, method="POST", data=body,
        cookie=session, content_type=content_type)
    assert status == 303, "expected a 303 redirect once the key is registered, got %d" % status
    assert os.path.isfile(override_path), "expected the override file to now exist at %r" % (override_path,)


# ==========================================================================
# theme preview image route (06.6.4.1.1-01 Task 2)
# ==========================================================================


def test_theme_preview_real_key_returns_png_for_every_theme(app04b_server, session_cookie):
    """an authenticated GET /theme-preview/{id}.png returns 200, image/png, and a real PNG body
    for every id in device_config.THEME_IDS — no theme is unreachable"""
    base = app04b_server.base_url()
    for theme_id in device_config.THEME_IDS:
        status, headers, body = http_request(
            base + "/theme-preview/%s.png" % theme_id, cookie=session_cookie)
        assert status == 200, "theme %r: expected 200, got %d" % (theme_id, status)
        assert headers.get("Content-Type") == "image/png", (
            "theme %r: expected Content-Type image/png, got %r" % (theme_id, headers.get("Content-Type")))
        assert body.startswith(PNG_SIGNATURE), "theme %r: expected a real PNG body" % (theme_id,)


def test_theme_preview_unknown_key_404(app04b_server, session_cookie):
    """an authenticated GET for a theme id not in the membership set returns the same 404 page
    an unknown runway/illustration id produces"""
    status, _headers, body = http_request(
        app04b_server.base_url() + "/theme-preview/not-a-theme.png", cookie=session_cookie)
    assert status == 404, "expected 404 for a theme id not in the membership set, got %d" % status
    assert b"Page not found." in body, "expected the exact 404 copy in the response body"


def test_theme_preview_traversal_key_404(app04b_server, session_cookie):
    """authenticated GET requests for adversarial theme-preview paths (path traversal) all
    return 404 with no file content"""
    adversarial_paths = [
        "/theme-preview/..%2F..%2Fetc%2Fpasswd.png",
        "/theme-preview/../../../etc/passwd.png",
        "/theme-preview/style.png",
    ]
    base = app04b_server.base_url()
    for adversarial_path in adversarial_paths:
        status, _headers, body = http_request(base + adversarial_path, cookie=session_cookie)
        assert status == 404, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)
        assert not (body and b"root:" in body), (
            "adversarial path %r returned file content" % (adversarial_path,))


def test_theme_preview_unauthenticated_redirects_to_login(app04b_server):
    """an unauthenticated GET /theme-preview/white.png redirects to /login, never returns image
    bytes"""
    status, headers, body = http_request(app04b_server.base_url() + "/theme-preview/white.png")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "/login" in location, "expected a redirect to /login, got %r" % location
    assert not body.startswith(PNG_SIGNATURE), "unauthenticated request must never return image bytes"


# --- 20-08-PLAN.md Task 2 (D-23): the ?live=1 route branch. One
# consolidated, atomic test over its own dedicated server: each step
# depends on the previous step's own mutation (no runway_events row,
# then one, then a newer one), which the original harness expressed as
# five checks sharing one mutable harness in a fixed order — exactly
# the ordering this module's shared read-only server must never carry
# (33-MIGRATION-RULES.md section 2's "no test may depend on another
# test having run first" rule), so the whole sequence is one test
# instead. ---


def test_theme_preview_live_branch_cache_and_fallback_behaviour(make_app_server):
    """GET /theme-preview/white.png?live=1 with no runway_events row at all still returns
    200/image/png (the sample-scene fallback, D-23); with a seeded runway_events row it returns
    200/image/png, and a second request for the same latest event is served from the cache
    without growing the cache directory (D-23/Pitfall 7); inserting a NEWER runway_events row
    changes both the served live-preview bytes and the cache file it comes from; GET
    /theme-preview/nope.png?live=1 returns the same 404 an unknown theme id always returns; and
    ?live=0 / a missing ?live query both serve the sample variant, never the live one, even with
    a runway_events row present"""
    import glob

    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    base = server.base_url()

    def theme_cache_dir(theme_id_glob="*"):
        return glob.glob(os.path.join(
            server.state_dir, theme_preview.THEME_PREVIEW_CACHE_DIRNAME, "%s*.png" % theme_id_glob))

    # No runway_events row exists yet — the "fresh install" case D-23
    # must fall back to the sample scene for.
    status, headers, body = http_request(
        base + "/theme-preview/white.png?live=1", cookie=session_cookie)
    assert status == 200, "expected 200 with no runway_events row, got %d" % status
    assert headers.get("Content-Type") == "image/png", (
        "expected image/png, got %r" % headers.get("Content-Type"))
    assert body.startswith(PNG_SIGNATURE), "expected a real PNG body"

    with history_db.open_db(server.state_dir) as conn:
        history_db.record_runway_event(
            conn, hex="3946a1", callsign="AFR1380", confirmed_state="departing",
            airline="Air France", origin="ORY", destination="TLS")
    status, headers, body = http_request(
        base + "/theme-preview/white.png?live=1", cookie=session_cookie)
    assert status == 200, "expected 200 with a seeded runway_events row, got %d" % status
    assert headers.get("Content-Type") == "image/png", (
        "expected image/png, got %r" % headers.get("Content-Type"))
    assert body.startswith(PNG_SIGNATURE), "expected a real PNG body"
    before = theme_cache_dir("white-")
    status2, _headers2, body2 = http_request(
        base + "/theme-preview/white.png?live=1", cookie=session_cookie)
    after = theme_cache_dir("white-")
    assert status2 == 200 and body2 == body, (
        "expected the second request to serve the identical cached bytes")
    assert len(after) == len(before), (
        "expected the cache file count to stay at %d for a repeat request of the same latest "
        "event, got %d" % (len(before), len(after)))

    before = set(theme_cache_dir("white-"))
    status, _headers, first_body = http_request(
        base + "/theme-preview/white.png?live=1", cookie=session_cookie)
    assert status == 200, "expected 200 before seeding a newer event, got %d" % status
    with history_db.open_db(server.state_dir) as conn:
        history_db.record_runway_event(
            conn, hex="3466ab", callsign="VLG9999", confirmed_state="arriving",
            airline="Vueling Airlines", origin="BCN", destination="ORY")
    status2, _headers2, second_body = http_request(
        base + "/theme-preview/white.png?live=1", cookie=session_cookie)
    assert status2 == 200, "expected 200 after seeding a newer event, got %d" % status2
    after = set(theme_cache_dir("white-"))
    assert len(after) > len(before), (
        "expected a newer runway_events row to add a new cache file, not reuse one")
    assert second_body != first_body, (
        "expected a newer runway_events row to change the served bytes")

    status, _headers, body = http_request(
        base + "/theme-preview/nope.png?live=1", cookie=session_cookie)
    assert status == 404, "expected 404 for an unknown theme id with ?live=1, got %d" % status
    assert b"Page not found." in body, "expected the exact 404 copy in the response body"

    status_zero, _headers_zero, body_zero = http_request(
        base + "/theme-preview/blue.png?live=0", cookie=session_cookie)
    status_missing, _headers_missing, body_missing = http_request(
        base + "/theme-preview/blue.png", cookie=session_cookie)
    assert status_zero == 200 and status_missing == 200, (
        "expected 200 for both ?live=0 and a missing query")
    sample_only = theme_preview.cached_preview_bytes(server.state_dir, "blue")
    assert body_zero == sample_only and body_missing == sample_only, (
        "expected ?live=0 and a missing query to both serve the sample variant, not the live one")


# ==========================================================================
# 260902-v26 Task 3: the live upload round trip, against this real
# running companion/app.py subprocess (D-01/D-02/D-03) — the LAST
# anchor of part 04.
# ==========================================================================


def test_illustration_upload_round_trip_replaces_served_bytes(make_app_server):
    """uploading a real PNG over real HTTP to a real companion/app.py subprocess changes what
    GET /illustration/air-france.png serves, even with a traversal-shaped declared filename in
    the part header"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    base = server.base_url()

    with open(os.path.join(_VENDORED_ILLUSTRATIONS_DIR, "vueling-airlines.png"), "rb") as fh:
        vueling_bytes = fh.read()

    pre_status, _pre_headers, pre_body = http_request(
        base + "/illustration/air-france.png", cookie=session_cookie)
    assert pre_status == 200, "expected 200 for the pre-upload GET, got %d" % pre_status

    # A traversal-shaped declared filename in the part header: the same
    # request that proves the happy path also proves the filename is
    # never read (T-v26-02-01).
    body, content_type = cah.encode_multipart(
        vueling_bytes, filename="../../../etc/passwd", field_name="illustration")
    status, headers, _resp_body = http_request(
        base + "/illustration/air-france.png", method="POST", data=body,
        cookie=session_cookie, content_type=content_type)
    assert status == 303, "expected a 303 redirect after a valid upload, got %d" % status
    location = headers.get("Location", "")
    assert "/airlines" in location, "expected the redirect Location to point at /airlines, got %r" % location
    assert ("flash=%s" % app_module.FLASH_KEY_ILLUSTRATION_REPLACED) in location, (
        "expected the success flash key in the redirect, got %r" % location)

    post_status, _post_headers, post_body = http_request(
        base + "/illustration/air-france.png", cookie=session_cookie)
    assert post_status == 200, "expected 200 for the post-upload GET, got %d" % post_status
    assert post_body.startswith(PNG_SIGNATURE), (
        "expected the post-upload body to start with the PNG signature")
    assert post_body != pre_body, "expected the served bytes to change after a successful upload"


# ==========================================================================
# Home's recent-flights detail line over a real HTTP round trip: the
# direction word is appended only for a departing or arriving row; any
# other stored confirmed_state (or none at all) leaves the line as
# airline and route alone, with no dangling separator.
# ==========================================================================


def test_home_recent_flights_detail_names_a_direction_only_when_known(make_app_server):
    """GET / lists each recorded runway event under Recent flights with an "<airline> · <route>"
    detail line that ends in "Departing" or "Arriving" for those two states, and carries no
    direction part (and no trailing separator) for any other stored state or none at all"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    with history_db.open_db(server.state_dir) as conn:
        for callsign, state, destination in (
                ("AFR1001", "departing", "TLS"),
                ("AFR1002", "arriving", "NCE"),
                ("AFR1003", "confirmed", "LYS"),
                ("AFR1004", None, "BOD")):
            history_db.record_runway_event(
                conn, hex=callsign.lower(), callsign=callsign, confirmed_state=state,
                airline="Air France", origin="ORY", destination=destination)

    status, _headers, body = http_request(server.base_url() + "/", cookie=session_cookie)
    assert status == 200, "expected 200 for GET /, got %d" % status
    details = {}
    for item in parse_html(body.decode("utf-8")).select("li.recent-flight"):
        callsign = item.select_one(".recent-flight__callsign").text()
        details[callsign] = item.select_one(".recent-flight__detail").text()

    assert details == {
        "AFR1001": "Air France · ORY → TLS · Departing",
        "AFR1002": "Air France · ORY → NCE · Arriving",
        "AFR1003": "Air France · ORY → LYS",
        "AFR1004": "Air France · ORY → BOD",
    }, "unexpected Recent flights detail lines: %r" % (details,)
