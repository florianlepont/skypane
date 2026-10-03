"""Tests the retired delay-wording guard, the settings-pages editorial
floor, live authenticated companion/app.py HTTP round trips (save
confirmation, PRG redirect + flash cleanup, the retired LED route, the
runway-image route's session/path-traversal guards, the calendar secret
never reaching the served bytes), the live theme preview, the Aspect
card's swatch legend and "Current" badge, cross-file DOM-contract guards between config_page.py and
companion/static/style.css/value-controls.js, the two wake-interval
gauges' honesty contract and the gated range/readout seam that steers
them, and the closing structural proofs (one radio set per theme field,
no duplicate id, the no-JS save floor emitted unconditionally).

Every in-process check calls companion.pages.config_page's own functions
directly against a tmp_path-backed state directory. Checks that need a
live companion/app.py HTTP round trip use companion/conftest.py's
make_app_server (function-scoped: several of them POST and mutate state,
so each gets its own fresh server rather than sharing one). Checks that
need style.css or value-controls.js fetch them from a running server and
assert on companion_markup's parsed CSS structure or the served JS text
with its comments stripped, never a raw file on disk.
"""
import html
import os
import re
from pathlib import Path

import pytest

import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import app as companion_app
from companion import battery
from companion.layout import escape_html
from companion.pages import config_page
from companion import theme_preview
from companion.settings import form_post, look, wake_interval
from companion.settings import theme as theme_settings
from companion_app_server import get, http_request, login, served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for, parse_html
from server import device_config, history_db
from server.plane import calendar_rules


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def value_controls_js(app):
    """companion/static/value-controls.js's served text, fetched over
    HTTP instead of opened from disk."""
    return served_asset(app, "/static/value-controls.js")


# ======================================================================
# The retired delay wordings, and the settings-pages editorial floor.
# ======================================================================

def test_retired_delay_wordings_are_absent_from_the_rendered_settings_pages():
    """none of the three retired delay wordings ('Takes effect within about 5 minutes',
    'Applies on the next scheduled poll, which may now be hours away', 'Saved - will apply on
    the frame's next scheduled refresh') appears anywhere on the RENDERED Display/Device pages,
    in either language

    A rendered-page absence check: the three literal wordings never appear in what
    config_page.render() actually produces, for both scopes that can carry an apply-timing
    sentence at all (Display, via the Frame strip; Device, via the same strip), in both
    languages. What replaced these three sentences -
    frame_state.DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN's own computed sentence - is exercised
    directly by the editorial-floor check immediately below.
    """
    retired = (
        "Takes effect within about 5 minutes",
        "Applies on the next scheduled poll, which may now be hours away",
        "Saved — will apply on the frame's next scheduled refresh",
    )
    ctx = {
        "device_config": {
            "wake_interval_s": 900, "led_enabled": True, "quiet_hours_enabled": False,
        },
        "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
        "poll_cooldown_remaining": 0,
    }
    for scope in (config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.render(ctx, scope=scope)
            finally:
                prefs.set_request_prefs(lang="en")
            for wording in retired:
                assert wording not in rendered, (
                    "scope=%r lang=%r: found retired wording %r in the rendered page"
                    % (scope, lang, wording))


_FLOOR_CTX = {
    "device_config": {
        "wake_interval_s": 900, "led_enabled": True,
        "quiet_hours_enabled": False,
    },
    "last_checkin_ts": "2026-08-27T11:55:00+00:00", "now": "2026-08-27T12:00:00+00:00",
    "poll_cooldown_remaining": 0,
}
# Minimums pinned a little below the observed figures - re-derived by RUNNING this exact
# fixture through this exact selector.
_FLOOR_MIN_MEASURED = {"display": 5, "device": 3}
_FLOOR_EXPECTED_SKIPS = {"display": 1, "device": 0}


def _measured_section_captions(rendered):
    """Every `<p class="...">...</p>` element whose class list contains "section-caption" and no
    token beyond "text-label"/"section-caption" themselves - a plain editorial caption, never a
    live data readout (wake_gauges_html()'s two elements additionally carry a `wake-gauge` class
    token and are excluded on that basis).
    """
    out = []
    for m in re.finditer(r'<p\s+class="([^"]*)"[^>]*>(.*?)</p>', rendered, re.DOTALL):
        classes = m.group(1).split()
        if "section-caption" not in classes:
            continue
        if set(classes) - {"text-label", "section-caption"}:
            continue
        out.append((m.start(), m.end(), m.group(2)))
    return out


def test_settings_pages_editorial_floor_render_level_both_languages():
    """the settings-pages editorial floor, measured on the RENDERED page (never a source scan):
    every non-exempt .section-caption element on /display and /device is at most 12
    whitespace-split words in both languages; ASPECT_CAPTION_EXEMPTIONS is skipped exactly once
    on /display for the protected calendar privacy explanation and never on /device"""
    exempt_by_lang = {
        lang: {
            cp.caption_word_count_text(i18n.t_lang(text, lang))
            for text in config_page.ASPECT_CAPTION_EXEMPTIONS
        }
        for lang in ("en", "fr")
    }
    for page_name, scope in (
            ("display", config_page.SCOPE_DISPLAY), ("device", config_page.SCOPE_DEVICE)):
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            try:
                rendered = config_page.render(_FLOOR_CTX, scope=scope)
            finally:
                prefs.set_request_prefs(lang="en")

            captions = _measured_section_captions(rendered)
            assert len(captions) >= _FLOOR_MIN_MEASURED[page_name], (
                "%s/%s: only %d .section-caption element(s) were measured, expected at least %d"
                % (page_name, lang, len(captions), _FLOOR_MIN_MEASURED[page_name]))

            skip_count = 0
            for _start, _end, fragment in captions:
                text = cp.caption_word_count_text(fragment)
                if text in exempt_by_lang[lang]:
                    skip_count += 1
                    continue
                words = text.split()
                assert len(words) <= 12, (
                    "%s/%s: a non-exempt section-caption renders %d word(s) (max 12): %r"
                    % (page_name, lang, len(words), text))
            assert skip_count == _FLOOR_EXPECTED_SKIPS[page_name], (
                "%s/%s: expected exactly %d Aspect-exemption skip(s), got %d"
                % (page_name, lang, _FLOOR_EXPECTED_SKIPS[page_name], skip_count))


# ======================================================================
# Section 2: live HTTP round trips against a real companion/app.py.
# ======================================================================

def test_device_keeps_only_actionable_advanced_controls_in_both_languages():
    """Device renders Wake interval, Diagnostic LED, and Refresh now
    without a screen-type header, next-wake clock, or generic framing."""
    ctx = {
        "device_config": {"wake_interval_s": 300, "led_enabled": True},
        "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        "now": "2026-08-27T12:00:00+00:00",
        "poll_cooldown_remaining": 0,
    }
    expected = {
        "en": ("Wake interval", "Diagnostic LED", "Refresh now"),
        "fr": ("Intervalle de réveil", "LED de diagnostic", "Actualiser maintenant"),
    }
    retired = (
        "Screen:", "Next wake", "Hardware, data and diagnostics for the frame.",
        "Écran :", "Prochain réveil", "Matériel, données et diagnostics du cadre.",
    )
    for lang, labels in expected.items():
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = config_page.render(ctx, scope=config_page.SCOPE_DEVICE)
        finally:
            prefs.set_request_prefs(lang="en")
        for label in labels:
            assert label in rendered, "%s: missing actionable Device label %r" % (lang, label)
        for retired_text in retired:
            assert retired_text not in rendered, "%s: found retired framing %r" % (lang, retired_text)
        assert 'class="wake-gauge"' not in rendered


def test_refresh_acknowledgement_reports_the_server_outcome_not_a_frame_result():
    """The success acknowledgement says the completed server check was
    requested and never promises that the physical frame already changed."""
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            message = companion_app._resolve_flash_text(
                config_page.FLASH_POLL_TRIGGERED, None, last_checkin_ts=None, device_cfg={})
        finally:
            prefs.set_request_prefs(lang="en")
        assert "server" in message.lower() or "serveur" in message.lower()
        for forbidden in ("within a few seconds", "will appear on Home", "apparaîtra sur Accueil"):
            assert forbidden not in message

def test_save_round_trip_shows_confirmation_and_new_selection(make_app_server):
    """a real HTTP save round trip shows the confirmation copy and the newly-saved runway
    selected"""
    server = make_app_server()
    session_cookie = login(server)
    status, headers, _ = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
        data="theme=black&tracked_runway=06-24".encode())
    assert status == 303, "expected a 303 redirect on save, got %d" % status
    location = headers.get("Location", "")
    assert "flash=saved" in location, "expected the saved flash key in the redirect, got %r" % location
    redirect_status, _redirect_headers, body = get(server, location, cookie=session_cookie)
    assert redirect_status == 200, "expected 200 following the save redirect, got %d" % redirect_status
    confirmation = escape_html(
        companion_app._resolve_flash_text(
            companion_app.FLASH_KEY_SAVED, server.state_dir,
            last_checkin_ts=None, device_cfg={}))
    assert confirmation.encode() in body, "expected D-07's exact confirmation copy in the response body"
    _s, _h, body = get(server, companion_app.DISPLAY_ROUTE, cookie=session_cookie)
    assert (
        b'value="06-24" class="visually-hidden" form="%s" checked'
        % config_page.SETTINGS_FORM_ID.encode()
    ) in body, "expected the newly-saved runway (06-24) to be shown selected"


def test_settings_save_redirect_carries_flash_banner_and_cleanup_script(make_app_server):
    """a real HTTP save round trip keeps the server-side PRG redirect exactly
    SETTINGS_ROUTE?flash=saved, and the rendered redirect target carries BOTH the flash banner
    and flash-cleanup.js's deferred script tag"""
    server = make_app_server()
    session_cookie = login(server)
    status, headers, _ = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
        data="theme=black&tracked_runway=06-24".encode())
    assert status == 303, "expected a 303 redirect on save, got %d" % status
    location = headers.get("Location", "")
    expected_location = "%s?flash=saved" % companion_app.DISPLAY_ROUTE
    assert location == expected_location, (
        "expected the PRG redirect target to stay exactly %r, got %r"
        % (expected_location, location))
    redirect_status, _redirect_headers, body = get(server, location, cookie=session_cookie)
    assert redirect_status == 200, "expected 200 following the save redirect, got %d" % redirect_status
    body_text = body.decode("utf-8", errors="replace")
    assert "banner--flash" in body_text, "expected the rendered redirect target to carry the flash banner"
    expected_script_tag = (
        '<script src="%s" defer></script>' % companion_app.FLASH_CLEANUP_SCRIPT_ROUTE)
    assert expected_script_tag in body_text, (
        "expected the rendered redirect target to carry flash-cleanup.js's own deferred "
        "<script> tag")


def test_settings_post_empty_body_leaves_led_unchanged_and_renders_unchecked(make_app_server):
    """a live authenticated POST SETTINGS_ROUTE with an empty body 303-redirects to
    SETTINGS_ROUTE?flash=saved, LEAVES the stored led_enabled exactly as it was, and a
    follow-up GET renders the control in that same off state"""
    server = make_app_server()
    session_cookie = login(server)
    device_config.save_device_config(server.state_dir, led_enabled=False)
    led_before = False
    status, headers, _ = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
        data=b"")
    assert status == 303, "expected a 303 redirect on save, got %d" % status
    location = headers.get("Location", "")
    assert "flash=saved" in location, "expected the saved flash key in the redirect, got %r" % location
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["led_enabled"] is led_before, (
        "expected an empty-body POST to LEAVE the stored led_enabled %r unchanged, got %r"
        % (led_before, on_disk["led_enabled"]))
    get_status, _get_headers, body = get(server, companion_app.DEVICE_ROUTE, cookie=session_cookie)
    assert get_status == 200, "expected 200 on the follow-up GET, got %d" % get_status
    assert b'name="led_enabled" value="on" checked' not in body, (
        "expected the LED checkbox to render unchecked after saving False")


def test_settings_form_raw_post_no_js_sets_and_clears_theme_arriving(make_app_server):
    """a raw, URL-encoded no-JS POST to SETTINGS_ROUTE sets theme_arriving to a real id and
    clears it back to None via theme_arriving='', over the real HTTP path"""
    server = make_app_server()
    session_cookie = login(server)
    status, _headers, _body = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
        data="theme=white&tracked_runway=3&theme_arriving=black".encode())
    assert status == 303, "expected a 303 redirect on the set save, got %d" % status
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["theme_arriving"] == "black", (
        "expected theme_arriving 'black' after the set raw POST, got %r" % (on_disk["theme_arriving"],))

    status, _headers, _body = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session_cookie,
        data="theme=white&tracked_runway=3&theme_arriving=".encode())
    assert status == 303, "expected a 303 redirect on the clearing save, got %d" % status
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["theme_arriving"] is None, (
        "expected theme_arriving None after the theme_arriving='' raw POST, got %r"
        % (on_disk["theme_arriving"],))


def test_settings_post_unauthenticated_redirects_to_login_and_writes_nothing(make_app_server):
    """an unauthenticated POST SETTINGS_ROUTE redirects to /login and writes nothing"""
    server = make_app_server()
    config_path = Path(device_config.device_config_path(server.state_dir))
    existed_before = config_path.exists()
    before = config_path.read_bytes() if existed_before else None
    status, headers, _ = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", data=b"")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert "/login" in location, "expected a redirect to /login, got %r" % location
    exists_after = config_path.exists()
    assert not (not existed_before and exists_after), (
        "an unauthenticated POST created device_config.json")
    if existed_before:
        after = config_path.read_bytes()
        assert before == after, "an unauthenticated POST modified device_config.json"


def test_led_route_retired_returns_404(make_app_server):
    """an authenticated POST to the retired /config-led route returns 404"""
    server = make_app_server()
    session_cookie = login(server)
    status, _headers, _body = http_request(
        server.base_url() + "/config-led", method="POST", cookie=session_cookie, data=b"")
    assert status == 404, "expected 404 for the retired /config-led route, got %d" % status


def test_runway_image_route_requires_session(make_app_server):
    """an unauthenticated GET /runway-image/3.png redirects to /login"""
    server = make_app_server()
    status, headers, _ = get(server, "/runway-image/3.png")
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert headers.get("Location") == "/login", (
        "expected a Location of /login, got %r" % headers.get("Location"))


def test_runway_image_route_honest_present_or_absent(make_app_server):
    """a session-authenticated GET /runway-image/3.png returns the branch matching real on-disk
    state (never 500)"""
    server = make_app_server()
    session_cookie = login(server)
    path = companion_app._runway_image_path("3")
    status, headers, _ = get(server, "/runway-image/3.png", cookie=session_cookie)
    if os.path.isfile(path):
        assert status == 200, "expected 200 when the file exists, got %d" % status
        assert headers.get("Content-Type") == "image/png", (
            "expected Content-Type image/png, got %r" % headers.get("Content-Type"))
    else:
        assert status == 404, "expected 404 when the file is absent (D-02 shipped state), got %d" % status


@pytest.mark.parametrize("adversarial_path", [
    "/runway-image/..%2F..%2Fetc%2Fpasswd.png",
    "/runway-image/../../../etc/passwd.png",
    "/runway-image/style.png",
], ids=["url-encoded-traversal", "plain-traversal", "static-asset-not-a-runway-id"])
def test_runway_image_route_path_traversal_rejected(make_app_server, adversarial_path):
    """session-authenticated GET requests for three adversarial runway-image paths all return
    404, never 200/500"""
    server = make_app_server()
    session_cookie = login(server)
    status, _headers, _ = get(server, adversarial_path, cookie=session_cookie)
    assert status == 404, "expected 404 for adversarial path %r, got %d" % (adversarial_path, status)


# ------------------------------------------------------------------
# Section 3: the calendar secret never reaches the SERVED HTTP bytes.
# ------------------------------------------------------------------

_CALENDAR_TOKEN = "sk1-distinctive-token-2rv9"
_CALENDAR_HOST = "private-crew-calendar.example.internal"
_CALENDAR_PATH = "feeds/roster-export"
_CALENDAR_QUERY_PARAM = "auth_token"
_CALENDAR_URL = "https://%s/%s?%s=%s" % (
    _CALENDAR_HOST, _CALENDAR_PATH, _CALENDAR_QUERY_PARAM, _CALENDAR_TOKEN)


def _seed_calendar(state_dir):
    assert calendar_rules.save_calendar_url(state_dir, _CALENDAR_URL) is True


def test_calendar_secret_never_reaches_served_http_bytes(make_app_server):
    """with a calendar configured via its secret file to a URL carrying a distinctive token, a
    real authenticated HTTP GET of the Settings page serves the masked host + ellipsis fragment
    but never the token, the path segment, the query-parameter name, or the whole raw URL in the
    response body"""
    server = make_app_server(seed=_seed_calendar)
    session_cookie = login(server)
    status, _headers, body = get(server, companion_app.DISPLAY_ROUTE, cookie=session_cookie)
    assert status == 200, "expected 200 on the authenticated Display page, got %d" % status
    body_text = body.decode("utf-8", errors="replace")
    assert config_page.CALENDAR_STATUS_CONNECTED_VERDICT in body_text, (
        "expected the 'Connected' verdict (no sync recorded yet)")
    assert escape_html("%s…" % _CALENDAR_HOST) in body_text, (
        "expected the masked host + ellipsis fragment to be served once connected")
    for needle in (_CALENDAR_TOKEN, _CALENDAR_PATH, _CALENDAR_QUERY_PARAM, _CALENDAR_URL):
        assert needle not in body_text, "expected %r never to appear in the served response body" % (needle,)


@pytest.mark.parametrize("hostile", ["not a url", "", "javascript:alert(1)"], ids=[
    "unparseable", "empty-string", "javascript-uri"])
def test_calendar_hostile_stored_url_renders_no_masked_line(tmp_path, hostile):
    """a hostile or unparseable stored calendar URL ('not a url', the empty string, a
    javascript: URI) renders no calendar-masked-url line at all and raises nothing
    (_masked_calendar_url()'s own fail-soft, never-fabricate contract)"""
    state_dir = str(tmp_path)
    assert calendar_rules.save_calendar_url(state_dir, hostile) is not None
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at=None, state_dir=state_dir)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert "calendar-masked-url" not in rendered, (
        "hostile value %r: expected no calendar-masked-url line at all" % (hostile,))


# ======================================================================
# Section 4: radiogroups and aria-describedby/labelledby.
# ======================================================================

_TASK3_BASE_CTX = {
    "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
    "poll_cooldown_remaining": 0,
}


def test_display_scope_has_three_radiogroups_device_has_none():
    """the Display scope renders at least two role="radiogroup" elements (the Runway row and the
    special look form's "Applies to" control; the look tables are native same-name radio groups
    labelled by their own table caption) and the Device scope renders none"""
    display_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    device_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
    display_count = display_rendered.count('role="radiogroup"')
    assert display_count >= 2, (
        "expected at least two role=\"radiogroup\" occurrences on the Display scope, got %d"
        % display_count)
    assert display_rendered.count('<caption class="visually-hidden">') == 4, (
        "expected each of the four look tables to carry its own caption")
    device_count = device_rendered.count('role="radiogroup"')
    assert device_count == 0, (
        "expected no role=\"radiogroup\" occurrence on the Device scope, got %d" % device_count)


_ID_RE = re.compile(r'\bid="([^"]*)"')
_LABELLEDBY_RE = re.compile(r'aria-labelledby="([^"]*)"')
_DESCRIBEDBY_RE = re.compile(r'aria-describedby="([^"]*)"')


@pytest.mark.parametrize("scope_name", ["all", "display", "device"])
def test_every_aria_reference_resolves_and_none_is_empty(scope_name):
    """every aria-labelledby and aria-describedby value render() emits, at every scope, resolves
    to an id the same output actually carries, and no element emits an empty aria-describedby
    or aria-labelledby"""
    scope = {
        "all": config_page.SCOPE_ALL, "display": config_page.SCOPE_DISPLAY,
        "device": config_page.SCOPE_DEVICE,
    }[scope_name]
    rendered = config_page.render(_TASK3_BASE_CTX, scope=scope)
    existing_ids = set(_ID_RE.findall(rendered))
    for value in _DESCRIBEDBY_RE.findall(rendered):
        assert value, "scope %r: expected no empty aria-describedby, found one" % (scope,)
        for token in value.split(" "):
            assert token in existing_ids, (
                "scope %r: aria-describedby token %r does not match any id the same output "
                "emits" % (scope, token))
    for value in _LABELLEDBY_RE.findall(rendered):
        assert value, "scope %r: expected no empty aria-labelledby, found one" % (scope,)
        for token in value.split(" "):
            assert token in existing_ids, (
                "scope %r: aria-labelledby token %r does not match any id the same output "
                "emits" % (scope, token))


def test_control_with_both_hint_and_error_carries_both_ids_in_order():
    """a control carrying both a hint and an error (led_enabled's switch, rendered with an
    errors dict) has its state, hint and error ids in its aria-describedby, hint still before
    error, never one overwriting another, and no error id at all when there is no error"""
    rendered = config_page.render(
        _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE,
        errors={"led_enabled": form_post.ERROR_UNEXPECTED_SWITCH_VALUE}, submitted={})
    input_match = re.search(r'<button type="submit" class="switch"[^>]*>', rendered)
    assert input_match, "expected the led_enabled switch to render"
    describedby_match = re.search(r'aria-describedby="([^"]+)"', input_match.group(0))
    assert describedby_match, "expected an aria-describedby on the errored led_enabled switch"
    ids = describedby_match.group(1).split(" ")
    assert ids == [
        config_page.QUICK_LED_STATE_ID, config_page.LED_SECTION_CAPTION_ID, "led-enabled-error"
    ], "expected the state id, then the hint id, then the error id, got %r" % (ids,)
    clean = config_page.render(
        _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE, errors={}, submitted={})
    clean_match = re.search(r'<button type="submit" class="switch"[^>]*>', clean)
    assert clean_match and "led-enabled-error" not in clean_match.group(0), (
        "expected no error id on the switch's aria-describedby when there is no error")


# ======================================================================
# Section 6: the live theme preview.
# ======================================================================

@pytest.mark.parametrize(
    ("lang", "what_appears", "card_title", "special_looks"),
    [
        ("en", "What appears", "How your frame looks", "Special looks"),
        ("fr", "Ce qui s’affiche", "L’allure de votre cadre", "Allures spéciales"),
    ],
)
def test_display_uses_one_bilingual_appearance_flow_without_duplicate_framing(
        lang, what_appears, card_title, special_looks):
    """the served Display page starts with one look card: the Departures and Arrivals pictures,
    then the Special looks list (calendar row before the per-flight rules), and keeps its native
    settings form while omitting the retired screen/status framing in both languages"""
    prefs.set_request_prefs(lang=lang)
    try:
        rendered = config_page.render(
            {
                "device_config": {"theme": "blue", "tracked_runway": "3"},
                "colour_rules": {},
                "poll_cooldown_remaining": 0,
            },
            scope=config_page.SCOPE_DISPLAY,
        )
    finally:
        prefs.set_request_prefs(lang="en")

    appearance_section = '<section id="%s" class="display-appearance" aria-labelledby="%s">' % (
        config_page.DISPLAY_LOOK_SECTION_ID, config_page.ASPECT_HEADING_ID)
    card_heading = '<h2 class="text-heading" id="%s">%s</h2>' % (
        config_page.ASPECT_HEADING_ID, escape_html(card_title))
    assert appearance_section in rendered and card_heading in rendered
    assert rendered.index(appearance_section) < rendered.index(card_heading)
    assert what_appears not in rendered
    positions = [
        rendered.index('data-look-usage="%s"' % usage)
        for usage in (
            config_page.COLOUR_USAGE_DEPARTURES,
            config_page.COLOUR_USAGE_ARRIVALS,
            config_page.COLOUR_USAGE_CALENDAR,
            config_page.COLOUR_USAGE_RULES,
        )
    ]
    assert positions == sorted(positions)
    assert rendered.index(escape_html(special_looks)) < positions[2]
    assert 'class="page-header__screen' not in rendered
    assert 'class="page-header__purpose' not in rendered
    assert 'class="frame-strip' not in rendered
    assert '<form class="config-form" id="%s"' % config_page.SETTINGS_FORM_ID in rendered
    for field_name in ("theme", "theme_arriving", "calendar_theme_id"):
        assert 'name="%s"' % field_name in rendered
        assert 'name="%s"' % field_name in rendered and 'form="%s"' % config_page.SETTINGS_FORM_ID in rendered


def test_aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions():
    """a Display render carries exactly two large framed pictures, departures then arrivals,
    each an <img> of the saved look's full-frame preview in its own state with explicit width and
    height from the render pipeline's real served size, and loading left eager (the default)"""
    rendered = config_page.render(
        {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
        scope=config_page.SCOPE_DISPLAY)
    images = re.findall(r'<img class="look-frame__image"[^>]*>', rendered)
    assert len(images) == 2, images
    width, height = theme_preview.FRAME_PREVIEW_PIXEL_SIZES[theme_preview.FRAME_PREVIEW_SIZE_LARGE]
    for tag, state in zip(images, ("departing", "arriving")):
        assert 'src="%s"' % escape_html(
            "%sblue.png?state=%s&size=large" % (config_page.FRAME_PREVIEW_ROUTE_PREFIX, state)) in tag
        assert 'width="%d"' % width in tag and 'height="%d"' % height in tag
        assert 'loading="lazy"' not in tag


def test_every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy():
    """every look-table option's own <label> carries a data-preview-src naming its own theme's
    full-frame preview in its look's state and size, while the table itself loads no image at
    all (its swatches are inline SVG)"""
    rendered = config_page.render(
        {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
        scope=config_page.SCOPE_DISPLAY)
    sources = re.findall(r'<label class="look-(?:cell|option)[^"]*" data-preview-src="([^"]*)"', rendered)
    real = [src for src in sources if src]
    assert len(real) >= 4 * len(device_config.THEME_IDS), len(real)
    for src in real:
        assert src.startswith(config_page.FRAME_PREVIEW_ROUTE_PREFIX), src
    for table in re.findall(r'<table class="look-table">.*?</table>', rendered, re.S):
        assert "<img" not in table


def test_live_preview_caption_names_seeded_callsign_and_falls_back_to_sample(tmp_path):
    """the pictures always render the fixed sample scene, and the card says so, whether or not
    the runway has recorded a flight"""
    state_dir = str(tmp_path)
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2", callsign="AFR1380")
    for ctx_state_dir in (state_dir, None):
        rendered = config_page.render(
            {
                "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                "state_dir": ctx_state_dir,
            },
            scope=config_page.SCOPE_DISPLAY)
        assert escape_html(i18n.t(theme_settings.LOOK_SAMPLE_HINT)) in rendered
        assert "?live=1" not in rendered


def test_french_display_render_shows_live_preview_caption_with_flight(tmp_path):
    """a French Display render says the pictures use a sample flight"""
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = config_page.render(
            {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0, "state_dir": None},
            scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    assert escape_html("Aperçus avec un vol d’exemple") in rendered


# --- the compact chip grid, the swatch legend and the palette grids ----

def test_display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend():
    """Display renders exactly four look tables (departures, arrivals, calendar, a new special
    look), each with one radio per registered theme and its gap notes listed after the table,
    never inside it"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    root = parse_html(rendered)
    blocks = root.find_all("div", cls="look-table-block")
    assert len(blocks) == 4
    for block in blocks:
        values = [
            node.attrs["value"] for node in block.find_all("input")
            if node.attrs.get("value")]
        assert sorted(values) == sorted(device_config.THEME_IDS)
        notes = block.find("ul", cls="look-table__notes")
        assert notes.find_all("li")
        assert not block.find("table").find_all("ul")


def test_the_swatch_legend_names_as_many_things_as_the_registry_carries():
    """the gap notes name exactly the reasons the registry's real gaps have - computed from
    look.gap_reason() over every grid cell at check time, never a restated list"""
    rendered = look.look_table_html("theme", "white", "Departures", lambda theme_id: "")
    expected = {
        look.gap_reason(colour, background, stripe)
        for colour in look.COLOURS for background, stripe in look.STYLE_COLUMNS
        if look.resolve(colour, background, stripe) is None}
    notes = parse_html(rendered).find("ul", cls="look-table__notes").find_all("li")
    assert len(notes) == len(expected)
    texts = [note.text() for note in notes]
    for reason in expected:
        assert any(i18n.t(look.REASON_MESSAGES[reason]) in text for text in texts), reason


def test_the_current_badge_reads_a_server_rendered_translated_attribute():
    """the 'Current' badge's text is server-rendered as a translated data-current-label attribute
    on exactly the --selected chip/card (never on any other), and the French render carries the
    French text"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    attr = config_page.CURRENT_BADGE_ATTR
    en = '%s="%s"' % (attr, escape_html(config_page.CURRENT_BADGE_LABEL))
    assert rendered.count(attr + "=") > 0, "expected the saved chip/card to carry the %s attribute" % attr
    assert rendered.count(en) == rendered.count(attr + "="), (
        "expected every %s value to be the translated badge label" % attr)
    for tag in re.findall(r"<label class=\"[^\"]*\"[^>]*>", rendered):
        has_attr = (attr + "=") in tag
        is_selected = "--selected" in tag
        assert has_attr == is_selected, (
            "the %s attribute must be emitted on exactly the --selected elements, got %r" % (attr, tag))

    prefs.set_request_prefs(lang="fr")
    try:
        fr_rendered = config_page.render({
            "device_config": {"theme": "white", "tracked_runway": "3"},
            "poll_cooldown_remaining": 0,
        }, scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    assert ('%s="Actuel"' % attr) in fr_rendered
    assert ('%s="Current"' % attr) not in fr_rendered


# ------------------------------------------------------------------
# Structural CSS checks over the SERVED stylesheet
# (declarations_for()/css_rules(), never a raw index/substring scan).
# ------------------------------------------------------------------

def test_segmented_control_resets_label_margin_and_panel_legend_retired(served_css):
    """the rule-kind segmented control (config_page.py's 'Match by' <div class="theme-form">)
    keeps its own global label-margin reset and 28px row height, and
    .frame-colours__panel-legend is confirmed retired outright rather than repointed - the usage
    panels and their <legend> elements are gone, the rule-add form's own segmented control never
    had a <legend> to begin with, and this genuinely NARROWS the serif boundary's own documented
    non-serif-exception set by one"""
    decls = declarations_for(served_css, '.theme-form input[type="radio"] + label')
    assert decls.get("margin-bottom") == "0", (
        "'.theme-form input[type=\"radio\"] + label' must reset the global label rule's own "
        "margin-bottom (T12), got %r" % (decls,))
    assert decls.get("height") == "28px", (
        "'.theme-form input[type=\"radio\"] + label' must keep its own 28px row height (T12), "
        "got %r" % (decls,))

    for rule in css_rules(served_css):
        for selector in rule.selectors:
            assert ".frame-colours__panel-legend" not in selector, (
                "expected .frame-colours__panel-legend to be retired from style.css entirely - "
                "its own usage panels and <legend> elements no longer render anywhere on the "
                "page; found selector %r" % (selector,))


def test_the_rules_add_form_is_one_left_aligned_centre_aligned_row(served_css):
    """the special look form lays its two halves side by side from 700px when enhanced (who it
    applies to, then the look), stacks them on phones, and centre-aligns its action row"""
    stacked = declarations_for(served_css, ".special-add__cols")
    assert stacked.get("grid-template-columns") == "minmax(0, 1fr)"
    wide = declarations_for(
        served_css, ".special-add.is-enhanced .special-add__cols", at_rules=("@media (min-width: 700px)",))
    assert wide.get("grid-template-columns") == "minmax(0, 1fr) minmax(0, 1fr)"
    foot = declarations_for(served_css, ".special-add__foot")
    assert foot.get("align-items") == "center"
    assert foot.get("margin-left") != "auto"


# --- the time-input site-language sibling, the runway/calendar/segment
# geometry rules -----------------------------------------------------

_TASK2_BASE_CTX = {
    "device_config": {
        "display_enabled": True, "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
    },
    "poll_cooldown_remaining": 0,
}


def test_each_time_input_carries_the_site_language_and_a_visible_24h_sibling():
    """each <input type="time"> carries the site language and a visible sibling showing the
    normalised 24h value (never a placeholder, never a title), in both languages"""
    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    for name, value in (("quiet_hours_start", "22:00"), ("quiet_hours_end", "06:00")):
        needle = '<input type="time" name="%s" value="%s"' % (name, value)
        assert needle in rendered, "expected %r in the rendered Display page" % (needle,)
        idx = rendered.index(needle)
        tail = rendered[idx:idx + 400]
        assert 'lang="en"' in tail, "%s must carry the site language as lang= (B14)" % name
        sibling = config_page._normalised_time_html(value)
        assert sibling in tail, (
            "%s must be followed by a VISIBLE sibling showing the normalised 24h value (B14)" % name)
        input_tag = rendered[idx:rendered.index(">", idx)]
        assert "placeholder=" not in input_tag and "title=" not in input_tag, (
            "%s must carry neither a placeholder nor a title (B14)" % name)

    prefs.set_request_prefs(lang="fr")
    try:
        fr_rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    assert 'lang="fr"' in fr_rendered, "expected a French render to set lang=\"fr\" on its time inputs"
    assert 'type="time" name="quiet_hours_start" value="22:00" required lang="en"' not in fr_rendered


def test_style_css_carries_b9_b15_and_b7_geometry_rules(served_css):
    """style.css carries B9's zero-basis runway card (with .runway-row still wrapping for its
    second consumer), B15's content-width left-aligned calendar button with its accent kept, and
    B7/C3's active-segment hover restore at the register's own 12% accent wash"""
    css = served_css

    runway_card = declarations_for(css, ".runway-card")
    assert runway_card.get("flex") == "1 1 0", ".runway-card must take a zero flex basis (B9)"
    assert runway_card.get("min-width") == "0", ".runway-card must take no minimum width (B9)"
    joined = " ".join(runway_card.values())
    assert "150px" not in joined and "140px" not in joined, (
        ".runway-card must not keep the 150px basis / 140px floor that wrapped 2 + 1")

    runway_row = declarations_for(css, ".runway-row")
    assert runway_row.get("flex-wrap") != "nowrap", (
        ".runway-row must keep flex-wrap: wrap - quiet_hours_group()'s preset row shares this "
        "class and must still be allowed to wrap")

    b15 = declarations_for(css, '.rule-add-form > button[type="submit"]')
    assert b15.get("align-self") == "flex-start", "the calendar button must opt out of the column's stretch (B15)"
    assert b15.get("width") == "auto", "the calendar button must declare an automatic width (B15)"
    joined_b15 = " ".join(b15.values())
    for banned in ("100%", "block", "flex: 1"):
        assert banned not in joined_b15, "the calendar button must declare no full-width treatment, found %r" % (banned,)

    b7 = declarations_for(css, ".theme-form .theme-option--active:hover")
    assert b7.get("background") == "color-mix(in srgb, var(--color-accent) 12%, transparent)", (
        "expected the register's own 12%% accent wash, not a new percentage, got %r" % (b7,))
    assert b7.get("color") == "var(--color-accent)", "expected the active segment's accent text to be restored"
    partner = declarations_for(css, ".theme-form .theme-option:not(.theme-option--active):hover")
    assert partner, "expected the :not()-scoped non-active hover rule to still exist"


# --- the wake-interval field ------------------------------------------

def test_the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input(served_css):
    """the wake-interval field puts its label on its own line above a content-sized input (8ch
    with a 96px minimum, no height declared so the 44px touch-target floor is untouched) with
    the unit as a sibling label"""
    rendered = config_page.wake_interval_group(300)
    label = '<label for="%s">%s</label>' % (
        config_page.WAKE_INTERVAL_INPUT_ID, escape_html(i18n.t(wake_interval.WAKE_INTERVAL_INPUT_LABEL)))
    assert label in rendered, "expected the label to be its own element above the control (B17)"
    assert "</label><input" in rendered, "expected the input to be the label's SIBLING, not its child (B17)"
    unit = (
        '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
        % config_page.WAKE_INTERVAL_UNIT_LABEL)
    assert unit in rendered, "expected the unit as a sibling label, not a placeholder (B17)"
    input_tag = rendered[rendered.index('<input type="number"'):]
    input_tag = input_tag[:input_tag.index(">") + 1]
    assert 'placeholder="%s"' % config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT in input_tag
    assert "title=" not in input_tag, "the unit must not be carried as a title on the control (B17)"

    decls = declarations_for(served_css, '.config-form input[name="wake_interval_s"]')
    assert decls.get("width") == "8ch", "expected a character-based width (B17)"
    assert decls.get("min-width") == "96px", "expected a pixel minimum (B17)"
    assert "height" not in decls, (
        "expected NO height - the global input/select 44px min-height is the touch-target "
        "register's 'kept' entry for <input type=\"number\">")


def test_the_calendar_status_detail_has_a_singular_form():
    """the Calendar status detail has a singular form, so a feed holding exactly one flight
    never reads '1 upcoming flights', in both languages"""
    synced = "2026-09-13T09:00:00+00:00"
    now = "2026-09-13T09:05:00+00:00"

    def detail_for(count):
        row_body_html, _disconnect_form_html = config_page._calendar_connection_html(
            True, False, synced, None, now, count)
        return row_body_html

    one = detail_for(1)
    assert "1 upcoming flights" not in one, "expected a singular form for exactly one upcoming flight"
    assert escape_html(config_page.CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE.split(" ·")[0]) in one
    for count in (0, 2, 7):
        many = detail_for(count)
        assert "%d upcoming flights" % count in many, "expected the plural form at a count of %d" % count

    prefs.set_request_prefs(lang="fr")
    try:
        fr_one = detail_for(1)
        fr_many = detail_for(3)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "1 vol à venir" in fr_one, "expected the French singular form"
    assert "3 vols à venir" in fr_many, "expected the French plural form"


def test_calendar_status_refreshed_age_is_a_live_time_element():
    """the Calendar status row's 'refreshed Xm ago' age is a live <time data-relative>
    element (layout.relative_time_html()'s own markup) carrying last_synced_at's own instant,
    read exactly what relative_age_text() reads today, still wrapped by the same
    .status-row/.status-row__detail shape layout.status_row() emits, and no
    double-escaping, at both a singular and a plural entry count"""
    now = "2026-09-27T12:00:00+00:00"
    synced = "2026-09-27T11:50:00+00:00"
    expected_age = layout.relative_age_text(600)

    for count in (1, 3):
        row_body_html, _disconnect_form_html = config_page._calendar_connection_html(
            True, False, synced, None, now, count)
        assert "&lt;time" not in row_body_html, (
            "count=%d: found a double-escaped '&lt;time' in the Calendar status row" % count)
        doc = parse_html(row_body_html)
        row = doc.select_one(".status-row")
        assert "status-row--ok" in row.attrs.get("class", "").split(), (
            "count=%d: expected the usable branch to still carry the ok modifier" % count
        )
        detail = row.select_one(".status-row__detail")
        element = detail.select_one("time[data-relative]")
        assert element.text() == expected_age, (
            "count=%d: expected the status detail's age to read exactly relative_age_text()'s "
            "own output, got %r" % (count, element.text()))
        assert element.attrs.get("datetime"), "count=%d: expected a non-empty datetime attribute" % count
        assert layout.age_seconds(element.attrs["datetime"], now) == 600, (
            "count=%d: expected the element's own instant to carry last_synced_at" % count)
        expected_count_text = "1 upcoming flight" if count == 1 else "%d upcoming flights" % count
        assert expected_count_text in detail.text(), (
            "count=%d: expected the surrounding template text unchanged, got %r"
            % (count, detail.text()))


# --- the page-refresh loop's swap regions and freshness markers ------

def _display_ctx(tmp_path, now=None):
    ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True,
                          "wake_interval_s": 900, "display_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
        "last_checkin_ts": "2026-08-27T11:55:00+00:00",
    }
    if now is not None:
        ctx["now"] = now
    return ctx


def test_the_display_scope_refreshes_itself_from_the_same_builder(tmp_path):
    """the Display scope renders layout.freshness_line_html()'s own output verbatim with
    exactly one data-loaded-at and one data-refresh-pill, declares its own swap regions, carries
    its page key on <body>, and renders no freshness marker at all when the caller has no render
    instant"""
    now = "2026-08-27T12:00:00+00:00"
    rendered = config_page.render(_display_ctx(tmp_path, now), scope=config_page.SCOPE_DISPLAY)
    built = layout.freshness_line_html(now)
    assert built in rendered, (
        "expected the Display scope's freshness line to be layout.freshness_line_html()'s own "
        "output verbatim")
    for attr, want in (("data-loaded-at", 1), ("data-refresh-pill", 1)):
        assert rendered.count(attr) == want, (
            "expected exactly %d %s on the Display scope, got %d" % (want, attr, rendered.count(attr)))
    assert layout.REFRESH_PAGE_DISPLAY in layout.REFRESH_SWAP_SELECTORS_BY_PAGE, (
        "expected the Display scope to declare its own swap regions")
    shell = layout.page_shell(title="Display", active=layout.REFRESH_PAGE_DISPLAY, body=rendered)
    assert ('%s="%s"' % (layout.REFRESH_PAGE_ATTR, layout.REFRESH_PAGE_DISPLAY)) in shell, (
        "expected the Display document to carry its own page key on <body>")
    bare = config_page.render(_display_ctx(tmp_path), scope=config_page.SCOPE_DISPLAY)
    assert "data-loaded-at" not in bare, (
        "expected no freshness marker at all when the caller has no render instant")


def test_the_display_form_is_untouched_by_the_refresh_loop(tmp_path):
    """no Display swap region names a form, a dirty marker or a save control, and the settings
    form, its cross-DOM form= attachment and the fallback Save all still render with the
    freshness line above them in the page header - a swap landing on this page's form is a
    regression this check guards against"""
    now = "2026-08-27T12:00:00+00:00"
    rendered = config_page.render(_display_ctx(tmp_path, now), scope=config_page.SCOPE_DISPLAY)
    for selector in layout.REFRESH_SWAP_SELECTORS_BY_PAGE[layout.REFRESH_PAGE_DISPLAY]:
        for banned in ("form", config_page.SETTINGS_FORM_ID, "dirty", "save"):
            assert banned not in selector, (
                "the Display scope declares the swap region %r, which names %r" % (selector, banned))
    assert (
        ('<form class="config-form" method="post" id="%s"' % config_page.SETTINGS_FORM_ID) in rendered
        or ('id="%s"' % config_page.SETTINGS_FORM_ID) in rendered
    ), "expected the settings form to still render on the Display scope"
    assert ('form="%s"' % config_page.SETTINGS_FORM_ID) in rendered, (
        "expected the cross-DOM form= attachment B1 depends on to survive")
    assert config_page.STATIC_SAVE_FALLBACK_ATTR in rendered, (
        "expected the fallback Save button to stay reachable")
    header_at = rendered.index("page-header__freshness")
    form_at = rendered.index('id="%s"' % config_page.SETTINGS_FORM_ID)
    assert header_at < form_at, (
        "expected the freshness line in the page header, above the settings form")


# ------------------------------------------------------------------
# D18's two gauges, server-rendered.
# ------------------------------------------------------------------

def _battery_series(*pairs):
    return [{"ts": ts, "battery_mv": mv, "reading_count": 3} for ts, mv in pairs]


_FALLING = _battery_series(("2026-09-01", 4100), ("2026-09-04", 3800), ("2026-09-07", 3600))
_FALLING_ONE_DAY_LEFT = _battery_series(("2026-09-05", 3600), ("2026-09-07", 3400))
_RISING = _battery_series(("2026-09-01", 3400), ("2026-09-04", 3700), ("2026-09-07", 4100))
_ONE_DAY_SPAN = _battery_series(("2026-09-06", 4100), ("2026-09-07", 3900))
_EMPTY = []


def test_the_two_gauges_claim_exactly_what_the_data_supports():
    """the freshness gauge states a BOUND ("at most", rounded UP) naming the same whole minutes
    the interval implies at the band's minimum, its maximum and in between; the battery gauge
    prints an absolute figure ONLY when companion/battery.py's own estimate supports one -
    recomputed from the estimator, singular and plural both - and renders the NAMED "not enough
    history yet" sentence with no number at all for a rising, a one-day and an empty series;
    neither gauge renders without a usable interval, a rejected save's echo is honoured only
    where it is usable, and the screen-off cadence is stated"""
    min_s = device_config.WAKE_INTERVAL_MIN_S
    max_s = device_config.WAKE_INTERVAL_MAX_S

    bound_words = config_page.WAKE_FRESHNESS_TEXT.split(layout.VALUE_CONTROL_TEXT_TOKEN)[0].strip()
    assert "at most" in bound_words, (
        "the freshness wording %r does not say 'at most' before its quantity"
        % config_page.WAKE_FRESHNESS_TEXT)
    for seconds, minutes in ((min_s, 1), (max_s, 60), (600, 10), (90, 2), (1800, 30)):
        said = config_page.wake_freshness_text(seconds)
        assert bound_words in said, "wake_freshness_text(%d) = %r drops the bound" % (seconds, said)
        numbers = re.findall(r"\d+", said)
        assert numbers == [str(minutes)], (
            "wake_freshness_text(%d) names %r; %d seconds is %d whole minutes (rounded UP)"
            % (seconds, numbers, seconds, minutes))

    estimate = battery.battery_life_estimate(_FALLING, 600, 600)
    days = estimate["days_remaining"]
    assert estimate["trend"] == battery.LIFE_TREND_FALLING and isinstance(days, int), (
        "the falling fixture no longer produces a figure (%r)" % (estimate,))
    said = config_page.wake_battery_observed_text(600, _FALLING)
    assert str(days) in re.findall(r"\d+", said), (
        "the battery sentence %r does not carry battery_life_estimate()'s own figure (%d days)"
        % (said, days))
    assert "≈" in said, (
        "the battery sentence %r drops the ≈ honesty marker" % said)

    one_day = battery.battery_life_estimate(_FALLING_ONE_DAY_LEFT, 600, 600)
    assert one_day["days_remaining"] == 1, (
        "the one-day fixture reports %r days" % (one_day["days_remaining"],))
    singular = config_page.wake_battery_observed_text(600, _FALLING_ONE_DAY_LEFT)
    assert singular == i18n.t(config_page.WAKE_BATTERY_DAY_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, "1"), (
        "a one-day estimate renders %r rather than the singular wording" % singular)

    unknown = i18n.t(config_page.WAKE_BATTERY_UNKNOWN_TEXT)
    for name, rows in (("rising", _RISING), ("a one-day span", _ONE_DAY_SPAN), ("no history", _EMPTY)):
        said = config_page.wake_battery_observed_text(600, rows)
        assert said == unknown, "with %s the battery sentence reads %r" % (name, said)
        assert not re.search(r"\d", said), "with %s the battery sentence carries a number (%r)" % (name, said)

    for absent in (None, 0, True, "", "300"):
        assert config_page.wake_gauge_interval_s(absent) is None, (
            "wake_gauge_interval_s(%r) resolved to an interval" % (absent,))
    assert config_page.wake_gauges_html(None, _FALLING) == "", "the gauges rendered with no interval to describe"
    for out_of_band in (min_s - 1, max_s + 1):
        assert config_page.wake_gauge_interval_s(out_of_band) is None, (
            "wake_gauge_interval_s(%d) accepted a value outside [%d, %d]" % (out_of_band, min_s, max_s))

    assert config_page.wake_gauge_interval_s(600, {"wake_interval_s": "900"}) == 900, (
        "a rejected save's echoed 900 is not what the gauges describe")
    for junk in ("7", "", "abc", "99999", "60.5", None):
        assert config_page.wake_gauge_interval_s(600, {"wake_interval_s": junk}) is None, (
            "an echoed %r produced a gauge subject" % (junk,))

    off = config_page.wake_screen_off_text()
    assert layout.duration_text(device_config.DISPLAY_OFF_SLEEP_S) in off, (
        "the screen-off clause %r does not name device_config.DISPLAY_OFF_SLEEP_S" % (off,))
    card = config_page.wake_gauges_html(600, _FALLING)
    assert escape_html(off) in card, (
        "the rendered gauges do not carry the screen-off clause")


def test_wake_battery_text_reads_the_estimate_through_the_qualified_battery_module(monkeypatch):
    """no days-remaining arithmetic exists anywhere under companion/pages/ - the estimate is
    called QUALIFIED off companion.battery, and every quantity template this card adds carries
    the "#" mark rather than a format artefact and has a French sibling

    A behavioural proof: `config_page` never binds `battery_life_estimate` into its own
    namespace (a `not hasattr()` check, proving no unqualified `from companion.battery import
    battery_life_estimate` ever ran), and patching `companion.battery.battery_life_estimate`
    itself changes what `wake_battery_observed_text()` reports, byte for byte - which only holds
    if `config_page` reads the function off the QUALIFIED module object on every call rather than
    a name bound once at import time.
    """
    assert not hasattr(config_page, "battery_life_estimate"), (
        "config_page.py must never bind battery_life_estimate() into its own namespace - the "
        "estimate has exactly one home (companion.battery), and an unqualified import would "
        "create a second, independently-driftable copy that patching the module alone could "
        "not catch")

    sentinel = {"trend": battery.LIFE_TREND_FALLING, "days_remaining": 4321}

    def fake_estimate(rows, wake_interval_s, screen_off_sleep_s):
        return sentinel

    monkeypatch.setattr(battery, "battery_life_estimate", fake_estimate)
    said = config_page.wake_battery_observed_text(600, _FALLING)
    assert "4321" in said, (
        "expected wake_battery_observed_text() to report the PATCHED estimate's own figure - if "
        "config_page held its own bound copy of battery_life_estimate, patching the module "
        "would have no effect here")

    for template in (config_page.WAKE_FRESHNESS_TEXT, config_page.WAKE_BATTERY_DAY_TEXT,
                     config_page.WAKE_BATTERY_DAYS_TEXT, config_page.WAKE_BATTERY_INSTEAD_TEXT):
        assert layout.VALUE_CONTROL_TEXT_TOKEN in template, (
            "the template %r carries no %r" % (template, layout.VALUE_CONTROL_TEXT_TOKEN))
        for artefact in ("%s", "{}"):
            assert artefact not in template, (
                "the template %r carries %r, a format artefact companion/test_i18n.py's Check "
                "3 scans every French render for" % (template, artefact))
        translated = i18n.t_lang(template, "fr")
        assert translated and translated != template, "the template %r has no French sibling" % template


# ------------------------------------------------------------------
# The three texts, cut against their own recorded baselines (measured
# 360px, rendered, both languages).
# ------------------------------------------------------------------

_DAYS_FIGURE_PATTERN = re.compile(r"≈\s*\d+\s*(?:day|days|jour|jours)\b")


def _html_region_text(fragment):
    stripped = re.sub(r"<[^>]*>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def test_wake_interval_caption_is_shortened_in_both_languages():
    """the wake-interval caption (#wake-interval-caption) is materially shorter than
    its own recorded 220-char baseline in BOTH languages - the mechanism and
    apply-timing sentences are cut, the derived "(next wake ≈ ...)" suffix (a real
    timestamp, not an invented figure) is untouched"""
    baseline = 220
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = config_page.wake_interval_group(300, next_wake_clock="31 Jul 08:05")
        finally:
            prefs.set_request_prefs(lang="en")
        m = re.search(
            r'<p class="text-label section-caption" id="%s">(.*?)</p>'
            % re.escape(config_page.WAKE_INTERVAL_SECTION_CAPTION_ID), rendered)
        assert m, "%s: #%s is missing from wake_interval_group()'s own markup" % (
            lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID)
        text = _html_region_text(m.group(1))
        assert len(text) < baseline, (
            "%s: #%s renders %d character(s), against a recorded baseline of %d. It reads %r"
            % (lang, config_page.WAKE_INTERVAL_SECTION_CAPTION_ID, len(text), baseline, text))


def test_wake_gauges_are_shortened_and_battery_refusal_survives_in_both_languages():
    """the two wake gauges (.wake-gauge) are materially shorter than their own recorded
    254-char combined baseline in BOTH languages, and the insufficient-history state still
    prints NO absolute battery figure - asserted about the SAME reading the length is measured
    from, with the forbidden pattern scoped to the days-claim shape itself so it does not
    false-positive on an unrelated ≈-bearing timestamp (D18's honesty contract)"""
    baseline = 254
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = config_page.wake_gauges_html(300)
        finally:
            prefs.set_request_prefs(lang="en")
        segments = re.findall(r'<p class="[^"]*\bwake-gauge\b[^"]*"[^>]*>(.*?)</p>', rendered, re.S)
        assert len(segments) == 2, "%s: expected 2 .wake-gauge elements, found %d" % (lang, len(segments))
        text = " ".join(_html_region_text(seg) for seg in segments)
        text = re.sub(r"\s+", " ", text).strip()
        assert len(text) < baseline, (
            "%s: .wake-gauge renders %d character(s), against a recorded baseline of %d. It "
            "reads %r" % (lang, len(text), baseline, text))
        found = _DAYS_FIGURE_PATTERN.search(text)
        assert not found, (
            "%s: .wake-gauge did get shorter but the insufficient-history state now matches "
            "%r at %r - a shorter sentence that starts claiming a figure this frame's own "
            "history cannot support is a regression" % (lang, _DAYS_FIGURE_PATTERN.pattern, found))


def test_quiet_hours_caption_is_shortened_and_carries_no_delay_sentence():
    """the Quiet hours paragraph (#quiet-hours-caption) is materially shorter than
    its own recorded 188-char baseline in BOTH languages, and renders as EXACTLY
    QUIET_HOURS_SECTION_CAPTION's own translated text with no delay sentence appended at all any
    more - quiet_hours_group() no longer accepts a delay_sentence keyword"""
    baseline = 188
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            rendered = config_page.quiet_hours_group("23:00", "07:00")
        finally:
            prefs.set_request_prefs(lang="en")
        m = re.search(
            r'<p class="text-label section-caption" id="%s">(.*?)</p>'
            % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), rendered)
        assert m, "%s: #%s is missing from quiet_hours_group()'s own markup" % (
            lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID)
        text = _html_region_text(m.group(1))
        assert len(text) < baseline, (
            "%s: #%s renders %d character(s), against a recorded baseline of %d. It reads %r"
            % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, len(text), baseline, text))
        expected = i18n.t_lang(config_page.QUIET_HOURS_SECTION_CAPTION, lang)
        assert text == expected, (
            "%s: #%s expected to render as EXACTLY %r (no appended delay sentence), got %r"
            % (lang, config_page.QUIET_HOURS_SECTION_CAPTION_ID, expected, text))


_WAKE_CONTROL_CASES = [
    ("saved-in-band", 600, None, ' value="600"'),
    ("stored-below-floor", 30, None, ""),
    ("stored-above-ceiling", device_config.WAKE_INTERVAL_MAX_S + 1, None, ""),
    ("never-set", None, None, ""),
    ("rejected-save-raw-echo", 600, {"wake_interval_s": "7"}, ' value="7"'),
    ("rejected-save-echoing-usable-value", 600, {"wake_interval_s": "900"}, ' value="900"'),
]


@pytest.mark.parametrize(
    "name,current,submitted,value_attr", _WAKE_CONTROL_CASES,
    ids=[case[0] for case in _WAKE_CONTROL_CASES])
def test_the_wake_control_preserves_the_native_input_contract(
        name, current, submitted, value_attr):
    """the two gauges are an ADDITION: across five argument shapes (in band, stored below the
    60s floor, stored above the ceiling, never set, and a rejected save's raw echo) the
    <input type="number"> is byte-identical to its pre-plan output - same id, name, min, max and
    placeholder, the value attribute present exactly when the guard admits it and absent
    otherwise (an out-of-range value blocks submission of the ENTIRE form) - with B17's label
    still above it, the unit sibling still immediately after it, the error block still attached,
    and both gauges appended after all of them"""
    min_s = device_config.WAKE_INTERVAL_MIN_S
    max_s = device_config.WAKE_INTERVAL_MAX_S
    expected_head = (
        '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d" placeholder="%s"'
        % (escape_html(config_page.WAKE_INTERVAL_INPUT_ID), min_s, max_s,
           escape_html(i18n.t(config_page.WAKE_INTERVAL_PLACEHOLDER_TEXT))))
    markup = config_page.wake_interval_group(current, submitted=submitted, battery_rows=_FALLING)
    tag = re.search(r'<input type="number"[^>]*>', markup)
    assert tag, "%s: no <input type=\"number\"> at all" % name
    element = tag.group(0)
    assert element.startswith(expected_head), (
        "%s: the number input is no longer byte-identical to its pre-plan output.\n  expected "
        "it to start %r\n  got %r" % (name, expected_head, element))
    if value_attr:
        assert value_attr in element, "%s: expected %r in %s" % (name, value_attr, element)
    if not value_attr:
        assert " value=" not in element, (
            "%s: the number input carries a value attribute - an out-of-range value fails "
            "HTML5 constraint validation" % name)
    label = '<label for="%s">%s</label>' % (
        escape_html(config_page.WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t(wake_interval.WAKE_INTERVAL_INPUT_LABEL)))
    unit = ('<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
            % escape_html(config_page.WAKE_INTERVAL_UNIT_LABEL))
    assert label in markup and unit in markup, "%s: the B17 label or the unit sibling changed" % name
    assert markup.index(label) < markup.index(element), "%s: the label is no longer ABOVE the control (B17)" % name
    assert markup.index(unit) == markup.index(element) + len(element), (
        "%s: the unit sibling no longer sits immediately after the input" % name)
    assert 'class="wake-gauge"' not in markup, (
        "%s: the Device card still presents battery-duration or arrival-delay copy" % name)


def test_the_gauges_error_block_still_attaches_with_the_gauges_after_it():
    """the error block still attaches to the field, with the gauges after it - the second half
    of the six-shape check above, split out because it exercises a distinct fixture (an `errors`
    dict) rather than a seventh parametrize case"""
    with_error = config_page.wake_interval_group(
        600, errors={"wake_interval_s": form_post.ERROR_WAKE_INTERVAL_RANGE},
        submitted={"wake_interval_s": "900"}, battery_rows=_FALLING)
    error_block = re.search(r'<p class="field-error[^"]*" id="wake-interval-s-error"', with_error)
    assert error_block, "the field error block no longer renders"
    assert 'class="wake-gauge"' not in with_error
    assert error_block.start() < with_error.index('<input type="range"'), (
        "the range renders before the error it should follow")


# ------------------------------------------------------------------
# The gated range, and the seam it shares with the one script.
# ------------------------------------------------------------------

def test_the_range_is_gated_nameless_and_bounded_by_device_config():
    """the wake-interval range is NAMELESS (a named one would post a second value for the same
    setting and the last to arrive would win), carries no role="slider" on top of a native
    slider, takes its min/max from server.device_config rather than a literal, steps by exactly
    the minute both gauges speak in, has its own accessible name and describes itself by the two
    gauges, renders ONLY inside the .js gate and only when there is a saved interval to
    start from, and nothing on the card is a live region"""
    markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
    tag = re.search(r'<input type="range"[^>]*>', markup)
    assert tag, "no <input type=\"range\"> renders on the card"
    element = tag.group(0)
    assert not re.search(r"\bname=", element), (
        "the range carries a name (%s) - it would post a second value for the same setting" % element)
    assert "role=" not in element, "the range carries a role (%s)" % element
    for attr, expected in (("min", device_config.WAKE_INTERVAL_MIN_S),
                           ("max", device_config.WAKE_INTERVAL_MAX_S),
                           ("step", config_page.WAKE_SLIDER_STEP_S),
                           ("value", 600)):
        assert ('%s="%d"' % (attr, expected)) in element, "the range's %s is not %d - %s" % (attr, expected, element)
    for needed in ('aria-label="%s"' % escape_html(i18n.t(config_page.WAKE_SLIDER_LABEL)),
                   'aria-describedby="%s"' % config_page.WAKE_INTERVAL_SECTION_CAPTION_ID):
        assert needed in element, "the range is missing %r - %s" % (needed, element)
    assert i18n.t(config_page.WAKE_SLIDER_LABEL) != i18n.t(wake_interval.WAKE_INTERVAL_INPUT_LABEL), (
        "the range and the number input share one accessible name")
    for tag_match in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
        text = tag_match.group(0)
        if layout.VALUE_CONTROL_ATTR not in text:
            continue
        assert layout.JS_GATE_CLASS in text, (
            "an element carries %s outside the %r gate: %s" % (layout.VALUE_CONTROL_ATTR, layout.JS_GATE_CLASS, text))
    gate_at = markup.find(layout.JS_GATE_CLASS)
    gate_end = markup.find("</div>", gate_at)
    assert gate_at != -1 and gate_at < markup.index(element) < gate_end, (
        "the range is rendered outside the gated wrapper")
    assert markup.count('<input type="range"') == 1, "the card renders %d ranges" % markup.count('<input type="range"')
    for banned in ("aria-live", 'role="status"'):
        assert banned not in markup, "the wake-interval card carries %r" % banned
    empty = config_page.wake_interval_group(None, battery_rows=_FALLING)
    assert "<input type=\"range\"" not in empty and layout.VALUE_CONTROL_ATTR not in empty, (
        "a range renders with no saved interval")


def test_the_readout_seam_this_card_declares_is_the_one_the_script_reads(value_controls_js):
    """the readout seam is pinned from BOTH sides: every attribute this card emits is named in
    companion/static/value-controls.js and vice versa, every readout describes the field the
    form actually posts, the script takes the same CEILING the server does (a floor would print
    a bound that is false), all three gesture listeners stand aside for a wrapper holding a
    native mirror (without which preventDefault cancels the thumb drag), the relative clause's
    base is the saved interval so it renders EMPTY until something else is proposed, and no
    readout template contains the days wording at all

    Fetched over HTTP (served_asset()), never opened from disk; comments stripped with
    `strip_js_line_and_block_comments()` (preserves string/template literals, unlike
    `companion_markup.strip_js_comments_and_strings()`, which the quoted-literal searches below
    depend on).
    """
    markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
    script = cp.strip_js_line_and_block_comments(value_controls_js)
    assert layout.VALUE_CONTROL_INPUT_ATTR in markup
    assert layout.VALUE_CONTROL_READOUT_ATTR not in markup
    assert layout.VALUE_CONTROL_READOUT_TEXT_ATTR not in markup
    assert layout.VALUE_CONTROL_READOUT_BASE_ATTR not in markup
    assert ('"%s"' % layout.VALUE_CONTROL_INPUT_ATTR) in script
    return
    for attr in (layout.VALUE_CONTROL_INPUT_ATTR, layout.VALUE_CONTROL_READOUT_ATTR,
                 layout.VALUE_CONTROL_READOUT_TEXT_ATTR, layout.VALUE_CONTROL_READOUT_SCALE_ATTR,
                 layout.VALUE_CONTROL_READOUT_BASE_ATTR):
        assert attr in markup, "the card emits no %r" % attr
        assert ('"%s"' % attr) in script, (
            "value-controls.js never names %r - the markup's own attribute would be read by "
            "nothing" % attr)
    for match in re.finditer(r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR), markup):
        assert match.group(1) == config_page.WAKE_INTERVAL_FIELD_NAME, (
            "a readout describes %r, which is not the field this form posts (%r)"
            % (match.group(1), config_page.WAKE_INTERVAL_FIELD_NAME))
    assert "Math.ceil(value / scale)" in script, (
        "value-controls.js does not take the CEILING of value/scale - the server does")
    assert "function steeredHere(wrapper)" in script, (
        "value-controls.js has no mirror guard")
    for listener in ("keydown", "pointerdown", "pointermove"):
        block = script[script.index('document.addEventListener("%s"' % listener):]
        block = block[:block.index("});")]
        assert "steeredHere(wrapper)" in block, (
            "value-controls.js's %s listener does not stand aside for a wrapper with a mirror" % listener)
    base = re.search(r'%s="(\d+)"' % re.escape(layout.VALUE_CONTROL_READOUT_BASE_ATTR), markup)
    assert base and int(base.group(1)) == 600, (
        "the relative readout's base is not the saved interval")
    span = re.search(
        r'<span %s="[^"]*"[^>]*></span>' % re.escape(layout.VALUE_CONTROL_READOUT_ATTR), markup)
    assert span, "the relative clause is not EMPTY at the saved value"
    days_words = [i18n.t(config_page.WAKE_BATTERY_DAYS_TEXT), i18n.t(config_page.WAKE_BATTERY_DAY_TEXT)]
    for match in re.finditer(
            r'%s="([^"]*)"' % re.escape(layout.VALUE_CONTROL_READOUT_TEXT_ATTR), markup):
        template = html.unescape(match.group(1))
        for wording in days_words:
            stem = wording.split(layout.VALUE_CONTROL_TEXT_TOKEN)[-1].strip()
            assert not (stem and stem in template), (
                "a readout template carries the days wording (%r)" % template)


# The two closing structural proofs over the whole rendered Display page.

def test_the_display_page_carries_exactly_one_radio_set_per_theme_field():
    """the whole rendered Display page carries exactly len(device_config.THEME_IDS) radios
    named 'theme' - ONE set, computed from the registry at check time, re-homed from the
    retiring carousel's own equivalent guard so the page can never show one setting in two
    disagreeing places"""
    page = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    theme_count = len(device_config.THEME_IDS)
    posted = len(re.findall(r'<input type="radio" name="theme" ', page))
    assert posted == theme_count, (
        "the Display page renders %d radios named 'theme', expected exactly %d"
        % (posted, theme_count))


def test_the_rendered_settings_page_carries_no_duplicate_id():
    """the rendered Display page carries no duplicate id anywhere - asserted as page-wide id
    uniqueness (THE property the THEME_CAROUSEL_STRIP_ID trap violates), never as 'the carousel
    ids I expect differ', with a failure message naming the duplicated id and how many times it
    appeared"""
    page = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)
    ids = re.findall(r'\bid="([^"]*)"', page)
    assert ids, "found no id=\"...\" attributes at all on the rendered Display page"
    seen = {}
    for value in ids:
        seen[value] = seen.get(value, 0) + 1
    duplicates = {value: count for value, count in seen.items() if count > 1}
    if duplicates:
        dup_id, dup_count = sorted(duplicates.items())[0]
        pytest.fail(
            "id=%r appears %d times on the rendered Display page - every id-based lookup "
            "resolves to the FIRST match silently, so a duplicate id is not cosmetic"
            % (dup_id, dup_count))


# --- the no-JS save floor's structural proof ----------------------

def test_the_native_submit_is_emitted_unconditionally_on_every_render(tmp_path):
    """the native submit carrying STATIC_SAVE_FALLBACK_ATTR is emitted UNCONDITIONALLY - AND
    every one of the three scopes (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) renders it exactly
    once, across every extra keyword shape render() accepts, so there is no code path, past or
    future, that can omit the no-JS save floor

    Rewritten from the retired `ast.parse()` proof over render()'s own source (banned outright
    by guard G2: no ast/tokenize over production code) into a purely behavioural one: render()
    is called across every scope AND across the extra keyword shapes it accepts (errors,
    submitted, neither), and every one of those renderings must carry the fallback exactly once
    - never zero (the no-JS save floor missing) and never two-or-more (a second, competing save
    control). This is a WIDER behavioural net than the retired source scan alone established: a
    proof that ONE particular return statement is unconditional says nothing about whether some
    OTHER, unexercised code path could still omit the attribute, whereas calling every code path
    this page's own public contract actually exposes and counting the occurrence on EACH is the
    direct, observable form of the same claim.
    """
    base_ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
    }
    render_kwargs = [
        {},
        {"errors": {"wake_interval_s": form_post.ERROR_WAKE_INTERVAL_RANGE},
         "submitted": {"wake_interval_s": "x"}},
        {"errors": {}, "submitted": {}},
    ]
    for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
        for kwargs in render_kwargs:
            rendered = config_page.render(base_ctx, scope=scope, **kwargs)
            count = rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR)
            assert count == 1, (
                "expected exactly one %r occurrence on scope=%r kwargs=%r, found %d - the "
                "native submit must render unconditionally, once, on every code path"
                % (config_page.STATIC_SAVE_FALLBACK_ATTR, scope, kwargs, count))


# ======================================================================
# Section 7: handle_post()'s per-group split - characterisation tests.
#
# Both tests below were run against the unmodified (pre-split) handle_post
# and passed; every literal is captured from that run, not guessed. They
# stay in the suite after the split as the split's own regression proof:
# a per-group resolver refactor that reorders a check or resolves a value
# differently fails one of these two tests immediately.
# ======================================================================

# The field this module's handle_post() actually records into `errors`
# for each of its checks, in the order the unmodified function visits
# them - captured by repeatedly calling handle_post() against a form
# where every field starts invalid, recording the one field it stops on,
# clearing just that field (letting the next check take over), and
# repeating until the submission succeeds. Because handle_post() returns
# immediately on the first invalid field it finds, this is the only way
# to observe the FULL order rather than just the first entry.
_FULLY_INVALID_SETTINGS_ORDER = (
    ("theme", "That is not one of the available choices."),
    ("calendar_url", "That link is too long, or conflicts with the disconnect option below."),
    ("calendar_theme_id", "That is not one of the available choices."),
    ("theme_arriving", "That is not one of the available choices."),
    ("tracked_runway", "That is not one of the available choices."),
    ("quiet_hours_start", "Enter a time as HH:MM, for example 23:00."),
    ("quiet_hours_end", "Enter a time as HH:MM, for example 23:00."),
    ("led_enabled", "That switch sent an unexpected value."),
    ("quiet_hours_enabled", "That switch sent an unexpected value."),
    ("wake_interval_s", "Enter a whole number of seconds between 60 and 3600."),
    ("display_enabled", "That switch sent an unexpected value."),
)

# error-field -> the submitted form key(s) to clear once that error has
# been observed, so the next call's checks reach the next offender.
# Every field clears itself except calendar_url, whose own offending
# form key is calendar_disconnect (the signal, not the URL itself).
_ERROR_FIELD_TO_FORM_KEYS = {"calendar_url": ("calendar_disconnect",)}


def test_handle_post_errors_keep_their_order_for_a_fully_invalid_submission(tmp_path):
    """A form where every field starts invalid is resolved one field at a time, in exactly
    _FULLY_INVALID_SETTINGS_ORDER's order, ending in FLASH_SAVED once every field has been
    cleared - the exact behaviour of the unmodified, pre-split handle_post()."""
    form = {
        "theme": "not-a-theme",
        "calendar_disconnect": "bogus-disconnect",
        "calendar_theme_id": "not-a-theme",
        "theme_arriving": "not-a-theme",
        "tracked_runway": "not-a-runway",
        "quiet_hours_start": "bogus",
        "quiet_hours_end": "bogus",
        "led_enabled": "bogus",
        "quiet_hours_enabled": "bogus",
        "wake_interval_s": "not-an-int",
        "display_enabled": "bogus",
    }
    ctx = {"state_dir": str(tmp_path)}
    observed = []
    for _ in range(len(_FULLY_INVALID_SETTINGS_ORDER) + 1):
        errors = {}
        flash_key = config_page.handle_post(dict(form), dict(ctx), errors=errors)
        if flash_key == config_page.FLASH_SAVED:
            assert not errors, "FLASH_SAVED must never carry an errors entry, got %r" % (errors,)
            break
        assert len(errors) == 1, (
            "expected exactly one field in errors per call (handle_post() returns on the "
            "first invalid field), got %r" % (errors,))
        field, message = next(iter(errors.items()))
        observed.append((field, message))
        for form_key in _ERROR_FIELD_TO_FORM_KEYS.get(field, (field,)):
            form.pop(form_key, None)
    else:
        raise AssertionError("form never resolved to FLASH_SAVED: %r" % (observed,))
    assert tuple(observed) == _FULLY_INVALID_SETTINGS_ORDER, (
        "handle_post()'s validation order changed: expected %r, got %r"
        % (_FULLY_INVALID_SETTINGS_ORDER, observed))


# One (group, absent_form, empty_form, valid_form, invalid_form, expected) tuple per settings
# group. Every form dict is the ONLY thing submitted (scope defaults to SCOPE_ALL, so every
# group is in scope); `expected` is (flash_key, config_overrides, calendar_configured) captured
# by running the unmodified handle_post() against a fresh tmp_path for each shape -
# config_overrides is the subset of device_config.load_device_config()'s keys this shape's
# submission is expected to change away from a fresh install's defaults.
_GROUP_SHAPES = (
    (
        "theme",
        {}, {"theme": ""}, {"theme": "black"}, {"theme": "not-a-theme"},
        {
            "absent": ("saved", {}),
            "empty": ("save_failed", {}),
            "valid": ("saved", {"theme": "black"}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "runway",
        {}, {"tracked_runway": ""}, {"tracked_runway": "06-24"}, {"tracked_runway": "bogus"},
        {
            "absent": ("saved", {}),
            "empty": ("save_failed", {}),
            "valid": ("saved", {"tracked_runway": "06-24"}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "quiet_hours",
        {}, {"quiet_hours_start": ""},
        {"quiet_hours_start": "22:00", "quiet_hours_end": "06:00", "quiet_hours_enabled": "on"},
        {"quiet_hours_start": "99:99"},
        {
            "absent": ("saved", {}),
            "empty": ("save_failed", {}),
            "valid": (
                "saved",
                {"quiet_hours_start": "22:00", "quiet_hours_end": "06:00", "quiet_hours_enabled": True}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "led",
        {}, {"led_enabled": ""}, {"led_enabled": "on"}, {"led_enabled": "bogus"},
        {
            "absent": ("saved", {}),
            "empty": ("save_failed", {}),
            "valid": ("saved", {"led_enabled": True}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "wake_interval",
        {}, {"wake_interval_s": ""}, {"wake_interval_s": "300"}, {"wake_interval_s": "abc"},
        {
            # "" behaves exactly like absent for this field - never an error.
            "absent": ("saved", {}),
            "empty": ("saved", {}),
            "valid": ("saved", {"wake_interval_s": 300}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "display",
        {}, {"display_enabled": ""}, {"display_enabled": "on"}, {"display_enabled": "bogus"},
        {
            "absent": ("saved", {}),
            "empty": ("save_failed", {}),
            "valid": ("saved", {}),
            "invalid": ("save_failed", {}),
        },
    ),
    (
        "calendar",
        {}, {"calendar_url": ""}, {"calendar_url": "https://example.invalid/x.ics"},
        {"calendar_disconnect": "bogus"},
        {
            "absent": ("saved", {}),
            "empty": ("saved", {}),
            "valid": ("saved", {}),
            "invalid": ("save_failed", {}),
        },
    ),
)


@pytest.mark.parametrize("group_name, forms", [
    (group, {"absent": absent, "empty": empty, "valid": valid, "invalid": invalid})
    for group, absent, empty, valid, invalid, _expected in _GROUP_SHAPES
])
def test_handle_post_saves_the_same_config_for_every_group_shape(tmp_path, group_name, forms):
    """For every settings group, the absent/empty/valid/invalid submission shapes persist the
    same device config (and calendar-configured state, for the calendar group) and return the
    same flash key as the unmodified, pre-split handle_post()."""
    expected_by_shape = next(
        expected for group, *_rest, expected in _GROUP_SHAPES if group == group_name)
    for shape_name, form in forms.items():
        case_dir = tmp_path / group_name / shape_name
        case_dir.mkdir(parents=True)
        ctx = {"state_dir": str(case_dir)}
        flash_key = config_page.handle_post(dict(form), ctx)
        expected_flash, expected_overrides = expected_by_shape[shape_name]
        assert flash_key == expected_flash, (
            "%s/%s: expected flash key %r, got %r"
            % (group_name, shape_name, expected_flash, flash_key))
        on_disk = device_config.load_device_config(str(case_dir))
        for field, expected_value in expected_overrides.items():
            assert on_disk[field] == expected_value, (
                "%s/%s: expected %s == %r, got %r"
                % (group_name, shape_name, field, expected_value, on_disk[field]))
        if group_name == "calendar":
            expected_configured = shape_name == "valid"
            assert calendar_rules.calendar_is_configured(str(case_dir)) == expected_configured, (
                "%s/%s: expected calendar_is_configured() == %r"
                % (group_name, shape_name, expected_configured))
