"""Part 05 of the `companion/test_config_page.py` migration chain
(33-13-PLAN.md), THE CHAIN'S CLOSING PLAN: the original harness's
`check()` calls #229-#276 (the last of the file) — the retired
delay-wording guard, the settings-pages editorial floor, the live
authenticated `companion/app.py` HTTP round trips (save confirmation,
PRG redirect + flash cleanup, the retired LED route, the runway-image
route's session/path-traversal guards, the calendar secret never
reaching the served bytes), the Notifications group, the live theme
preview, the Aspect card's swatch legend and "Current" badge, several
cross-file DOM-contract guards between `config_page.py` and
`companion/static/style.css`/`value-controls.js`, the two wake-interval
gauges (D18's honesty contract) and the gated range/readout seam that
steers them, and the closing structural proofs (one radio set per
theme field, no duplicate id, the no-JS save floor emitted
unconditionally).

Every in-process check calls `companion.pages.config_page`'s own
functions directly against a `tmp_path`-backed state directory. The
checks that need a live `companion/app.py` HTTP round trip use
`companion/conftest.py`'s `make_app_server` (function-scoped: several of
them POST and mutate state, so each gets its own fresh server rather
than sharing one — TST-10). The checks that used to read
`companion/static/style.css` or `value-controls.js` off disk instead
fetch them from a running server and assert on `companion_markup`'s
parsed CSS structure (`declarations_for()`/`css_rules()`) or the served
JS text with its comments stripped (never a raw file on disk, TST-12) —
per 33-FOLLOWUPS.md F-01, no CSS assertion in this module reads the
served stylesheet as raw text.

Two checks that used to open `companion/pages/config_page.py` from disk
and walk its syntax tree with `ast`/`tokenize` (banned outright by guard
G2) are rewritten as behaviour: the "no second days-remaining
computation" guard becomes a `monkeypatch` proof that
`wake_battery_observed_text()` reads `companion.battery`'s own function
through the QUALIFIED module reference on every call (a `not hasattr()`
check plus a patched-function round trip — the same technique rubric S
recommends for "retired symbol gone"), and the "no-JS save floor is
unconditional" guard becomes a purely render-level proof across every
scope AND every extra keyword shape `render()` accepts, which is a
wider behavioural net than the retired source-tree scan on its own
established.

This is the config-page chain's LAST plan: `companion/test_config_page.py`
is deleted outright once this module lands (`git rm`), and the ledger
fragment's `33-ledger-check.py` run drops `--allow-pending` to confirm
zero rows remain pending.
"""
import html
import os
import re
from pathlib import Path

import pytest

import companion.i18n as i18n
import companion.i18n_fr as i18n_fr
import companion.layout as layout
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import app as companion_app
from companion import battery, frame_state
from companion.layout import escape_html
from companion.pages import config_page
from companion_app_server import get, http_request, login, served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for
from server import device_config, history_db
from server.plane import calendar_rules


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk
    (TST-12)."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def value_controls_js(app):
    """companion/static/value-controls.js's served text, fetched over
    HTTP instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/value-controls.js")


# ======================================================================
# 29-05-PLAN.md Task 3 (CFG-79/D-04): the retired delay wordings, and the
# settings-pages editorial floor.
# ======================================================================

def test_retired_delay_wordings_are_absent_from_the_rendered_settings_pages():
    """none of the three retired delay wordings ('Takes effect within about 5 minutes',
    'Applies on the next scheduled poll, which may now be hours away', 'Saved - will apply on
    the frame's next scheduled refresh') appears anywhere on the RENDERED Display/Device pages,
    in either language (D-04)

    Rewritten from the retired whole-repo source-text scan (grepping every non-test .py file
    under companion/ and server/, banned by TST-12) into a rendered-page absence check: the three
    literal wordings never appear in what config_page.render() actually produces, for both
    scopes that can carry an apply-timing sentence at all (Display, via the Frame strip; Device,
    via the same strip), in both languages. What replaced these three sentences -
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
# fixture through this exact selector, 30-05-PLAN.md Task 3 (CFG-85).
_FLOOR_MIN_MEASURED = {"display": 10, "device": 6}
_FLOOR_EXPECTED_SKIPS = {"display": len(config_page.ASPECT_CAPTION_EXEMPTIONS), "device": 0}


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
    whitespace-split words in both languages; ASPECT_CAPTION_EXEMPTIONS is skipped exactly 4
    times on /display and exactly 0 times on /device (proving the exemption reachable and not
    silently over-broad); and the apply-timing sentence - read from frame_state.py's own
    DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN constants - never renders outside the Frame strip's own
    markup slice, proven to actually fire inside it at least once so the assertion is not
    vacuous (CFG-79, 29-05-PLAN.md Task 3)"""
    exempt_by_lang = {
        lang: {
            cp.caption_word_count_text(i18n.t_lang(text, lang))
            for text in config_page.ASPECT_CAPTION_EXEMPTIONS
        }
        for lang in ("en", "fr")
    }
    apply_timing_templates = (
        frame_state.DELAY_DUE, frame_state.DELAY_HELD, frame_state.DELAY_UNKNOWN)

    any_inside_strip = False
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

            strip_start = rendered.find(
                '<div class="frame-strip stat-tile stat-tile--accent"')
            strip_end = (
                rendered.find('<form class="config-form"', strip_start)
                if strip_start != -1 else -1)
            outside_matches = []
            for start, _end, fragment in captions:
                text = cp.caption_word_count_text(fragment)
                for template in apply_timing_templates:
                    translated = i18n.t_lang(template, lang)
                    if "%s" in translated:
                        pattern = re.escape(translated).replace(re.escape("%s"), r".+?")
                    else:
                        pattern = re.escape(translated)
                    if not re.search(pattern, text):
                        continue
                    if strip_start != -1 and strip_start <= start < strip_end:
                        any_inside_strip = True
                    else:
                        outside_matches.append(
                            "%s/%s at offset %d (%r): %r"
                            % (page_name, lang, start, text[:80], text))
                    break
            assert not outside_matches, (
                "the apply-timing sentence rendered outside the Frame strip's own slice: %s"
                % ("; ".join(outside_matches),))
    assert any_inside_strip, (
        "the apply-timing relationship never matched INSIDE the Frame strip either - this "
        "assertion is vacuous unless it is proven to fire on the strip's own, untouched "
        "markup at least once")


# ======================================================================
# Section 2: live HTTP round trips against a real companion/app.py.
# ======================================================================

def test_save_round_trip_shows_confirmation_and_new_selection(make_app_server):
    """a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway
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
    and flash-cleanup.js's deferred script tag (quick task 260903-peo, UIR-19)"""
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
    follow-up GET renders the control in that same off state (retargeted in place from
    absent-means-False by 23-07-PLAN.md Task 2)"""
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
    clears it back to None via theme_arriving='', over the real HTTP path (15-VALIDATION.md
    row 11, the Settings-form half; D-06/D-09, retargeted from the retired arrivals-override
    checkbox)"""
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
    """an authenticated POST to the retired /config-led route returns 404 (D-05)"""
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
# Section 3 (T-16-SECRET, D-14/R-10): the calendar secret never reaches
# the SERVED HTTP bytes.
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
    response body (T-16-SECRET, real HTTP round trip, extended by 21-07-PLAN.md Task 2 for the
    new masked-URL line, D-14/R-10)"""
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
    javascript: URI) renders no calendar-masked-url line at all and raises nothing (D-14/R-10,
    _masked_calendar_url()'s own fail-soft, never-fabricate contract)"""
    state_dir = str(tmp_path)
    assert calendar_rules.save_calendar_url(state_dir, hostile) is not None
    ctx = dict(
        cp.CALENDAR_BASE_CTX, calendar_configured=True,
        calendar_last_synced_at=None, state_dir=state_dir)
    rendered = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
    assert "calendar-masked-url" not in rendered, (
        "hostile value %r: expected no calendar-masked-url line at all" % (hostile,))


# ======================================================================
# Section 4 (D-12/A-30): radiogroups and aria-describedby/labelledby.
# ======================================================================

_TASK3_BASE_CTX = {
    "device_config": {"theme": "white", "tracked_runway": "3", "led_enabled": True},
    "poll_cooldown_remaining": 0,
}


def test_display_scope_has_three_radiogroups_device_has_none():
    """the Display scope renders at least three role="radiogroup" elements (Theme's departures
    and arrivals chip grids, plus the Runway row) and the Device scope renders none (D-12/A-30,
    retargeted by 20-07-PLAN.md Task 1/D-10)"""
    display_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DISPLAY)
    device_rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
    display_count = display_rendered.count('role="radiogroup"')
    assert display_count >= 3, (
        "expected at least three role=\"radiogroup\" occurrences on the Display scope, got %d"
        % display_count)
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
    or aria-labelledby (D-12/A-30)"""
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
    error, never one overwriting another, and no error id at all when there is no error
    (D-12/A-30; retargeted in place from the retired checkbox by 23-07-PLAN.md Task 2)"""
    rendered = config_page.render(
        _TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE,
        errors={"led_enabled": "msg"}, submitted={})
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
# Section 5 (D-26/D-28): the Notifications group.
# ======================================================================

def test_notifications_group_status_row_configured_vs_not_and_write_only_url():
    """notifications_group()'s status row reads 'Not configured' with no URL stored and
    'Configured' with one, the topic-URL input never carries a value attribute in either state,
    and no substring of a seeded URL appears anywhere in the rendered page (T-20-12)"""
    rendered_unconfigured = config_page.render(
        {"device_config": {}, "poll_cooldown_remaining": 0}, scope=config_page.SCOPE_DEVICE)
    assert config_page.NOTIFICATIONS_SECTION_HEADING in rendered_unconfigured
    assert config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT in rendered_unconfigured
    assert config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT not in rendered_unconfigured

    seeded_url = "https://ntfy.sh/skypane-secret-token-xyz"
    rendered_configured = config_page.render(
        {
            "device_config": {
                "notifications": {
                    "topic_url": seeded_url, "battery_low": True,
                    "frame_silent": False, "lang": "en"}},
            "poll_cooldown_remaining": 0,
        },
        scope=config_page.SCOPE_DEVICE)
    assert config_page.NOTIFICATIONS_STATUS_CONFIGURED_VERDICT in rendered_configured
    assert config_page.NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT not in rendered_configured
    assert seeded_url not in rendered_configured and "secret-token-xyz" not in rendered_configured
    for rendered in (rendered_unconfigured, rendered_configured):
        match = re.search(r'<input[^>]*name="notifications_topic_url"[^>]*>', rendered)
        assert match, "expected the notifications_topic_url input to render"
        assert "value=" not in match.group(0), "expected no value attribute on the write-only topic-URL input"


def test_notifications_checkboxes_reflect_stored_state():
    """notifications_group()'s two checkboxes reflect the stored battery_low/frame_silent
    booleans"""
    rendered = config_page.render(
        {
            "device_config": {
                "notifications": {
                    "topic_url": "https://ntfy.sh/x", "battery_low": False,
                    "frame_silent": True, "lang": "fr"}},
            "poll_cooldown_remaining": 0,
        },
        scope=config_page.SCOPE_DEVICE)
    battery_match = re.search(r'<input type="checkbox" name="notifications_battery"[^>]*>', rendered)
    silent_match = re.search(r'<input type="checkbox" name="notifications_silent"[^>]*>', rendered)
    assert battery_match and silent_match, "expected both notifications checkboxes to render"
    assert " checked" not in battery_match.group(0), "expected notifications_battery unchecked when stored False"
    assert " checked" in silent_match.group(0), "expected notifications_silent checked when stored True"


def test_notifications_group_has_no_lang_selector():
    """the Device page contains no notifications_lang control anywhere (D-28: lang travels
    silently, never through a <select>)"""
    rendered = config_page.render(_TASK3_BASE_CTX, scope=config_page.SCOPE_DEVICE)
    assert "notifications_lang" not in rendered


def test_handle_post_notifications_round_trip_writes_lang_from_ctx(tmp_path):
    """handle_post() with scope=device, a topic URL and both checkboxes persists the whole
    notifications group and writes lang from ctx['lang'] (D-26/D-28)"""
    ctx = {"state_dir": str(tmp_path), "lang": "fr"}
    flash_key = config_page.handle_post(
        {
            "scope": config_page.SCOPE_DEVICE,
            "notifications_topic_url": "https://ntfy.sh/skypane-abc123",
            "notifications_battery": config_page.NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
            "notifications_silent": config_page.NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(str(tmp_path))["notifications"]
    expected = {
        "topic_url": "https://ntfy.sh/skypane-abc123",
        "battery_low": True, "frame_silent": True, "lang": "fr"}
    assert on_disk == expected


def test_handle_post_empty_notifications_url_leaves_stored_url_intact(tmp_path):
    """handle_post() with an empty notifications_topic_url leaves the previously stored URL
    unchanged (D-26: empty means 'leave unchanged', never 'clear it')"""
    ctx = {"state_dir": str(tmp_path)}
    device_config.save_device_config(
        str(tmp_path), notifications={
            "topic_url": "https://ntfy.sh/skypane-seeded",
            "battery_low": True, "frame_silent": True, "lang": "en"})
    flash_key = config_page.handle_post(
        {"scope": config_page.SCOPE_DEVICE, "notifications_topic_url": ""}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(str(tmp_path))["notifications"]
    assert on_disk["topic_url"] == "https://ntfy.sh/skypane-seeded", (
        "expected the stored URL to survive an empty submission, got %r" % (on_disk["topic_url"],))
    assert on_disk["battery_low"] is False and on_disk["frame_silent"] is False, (
        "expected both checkboxes to resolve absent-means-False")


# ======================================================================
# Section 6 (D-22..D-24): the live theme preview.
# ======================================================================

def test_aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions():
    """a Display render contains exactly one .theme-live-preview.aspect-card__preview figure
    whose <img> src ends in the saved theme's ?live=1 URL, carries loading="eager" and explicit
    width/height, positioned ABOVE the first accordion row (D-22..D-24, 30-05-PLAN.md Task 2,
    replacing the retired
    _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions)"""
    rendered = config_page.render(
        {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
        scope=config_page.SCOPE_DISPLAY)
    figure_needle = 'class="theme-live-preview aspect-card__preview"'
    assert rendered.count(figure_needle) == 1, (
        "expected exactly one .theme-live-preview.aspect-card__preview figure, got %d"
        % rendered.count(figure_needle))
    figure_pos = rendered.index(figure_needle)
    first_row_pos = rendered.index('name="%s"' % config_page.ASPECT_ROWS_GROUP_NAME)
    assert figure_pos < first_row_pos, "expected the live preview figure ABOVE the first accordion row"
    match = re.search(r'<img class="theme-live-preview__image"[^>]*>', rendered)
    assert match, "expected the live preview's own <img> element"
    tag = match.group(0)
    assert 'src="%sblue.png?live=1"' % config_page.THEME_PREVIEW_ROUTE_PREFIX in tag
    assert 'loading="eager"' in tag
    assert 'width="%d"' % config_page.THEME_LIVE_PREVIEW_WIDTH in tag
    assert 'height="%d"' % config_page.THEME_LIVE_PREVIEW_HEIGHT in tag


def test_every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy():
    """every chip's own <label> carries a data-preview-src ending in .png?live=1, while each
    chip's own <img> keeps loading="lazy" and the fixed, non-live src (D-24)"""
    rendered = config_page.render(
        {"device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0},
        scope=config_page.SCOPE_DISPLAY)
    labels = re.findall(r'<label class="theme-chip[^>]*data-preview-src="([^"]+)"', rendered)
    assert len(labels) >= len(device_config.THEME_IDS), (
        "expected at least one data-preview-src per registered theme, got %d" % len(labels))
    for src in labels:
        assert src.endswith(".png?live=1"), "expected every data-preview-src to end in .png?live=1, got %r" % (src,)
    chip_images = re.findall(r'<img class="theme-chip__preview"[^>]*>', rendered)
    assert chip_images, "expected at least one chip <img>"
    for tag in chip_images:
        assert 'loading="lazy"' in tag, 'expected every chip <img> to keep loading="lazy"'
        assert "?live=1" not in tag, "expected the chip's own <img> src to stay the fixed, non-live preview"


def test_live_preview_caption_names_seeded_callsign_and_falls_back_to_sample(tmp_path):
    """the live preview's caption names the seeded event's callsign, and falls back to the
    sample-flight wording with no events (D-24)"""
    state_dir = str(tmp_path)
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2", callsign="AFR1380")
    with_event = config_page.render(
        {
            "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
            "state_dir": state_dir,
        },
        scope=config_page.SCOPE_DISPLAY)
    expected_caption = (
        config_page.THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE % "AFR1380")
    assert escape_html(expected_caption) in with_event, "expected the caption to name the seeded event's callsign"

    without_event = config_page.render(
        {
            "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
            "state_dir": None,
        },
        scope=config_page.SCOPE_DISPLAY)
    assert escape_html(config_page.THEME_LIVE_PREVIEW_CAPTION_SAMPLE) in without_event, (
        "expected the sample-flight caption with no events/no state_dir")


def test_french_display_render_shows_live_preview_caption_with_flight(tmp_path):
    """a French Display render's live preview shows the "Aperçu avec votre dernier vol"
    caption followed by the seeded event's callsign (D-24/D-05)"""
    state_dir = str(tmp_path)
    with history_db.open_db(state_dir) as conn:
        history_db.record_runway_event(
            conn, ts="2026-09-07T09:00:00+00:00", hex="3944F2", callsign="AFR1380")
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = config_page.render(
            {
                "device_config": {"theme": "blue"}, "poll_cooldown_remaining": 0,
                "state_dir": state_dir,
            },
            scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "Aperçu avec votre dernier vol : AFR1380" in rendered, (
        "expected the French live-preview caption naming the seeded callsign")


# --- 22-10-PLAN.md Task 1 (X6, T10, T12, C1) ----------------------

def test_display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend():
    """Display renders exactly one .theme-chip-grid (the rule-add form's own compact grid,
    unaffected by CFG-85), followed by exactly one swatch legend in .text-label section-caption's
    own declaration set outside the radiogroup, and exactly 3 .palette grids
    (departures/arrivals/calendar) carrying no legend at all (22-10-PLAN.md Task 1, updated by
    30-05-PLAN.md Task 3 for CFG-85's accordion rebuild)"""
    rendered = config_page.render({
        "device_config": {"theme": "white", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
    }, scope=config_page.SCOPE_DISPLAY)

    grid_classes = re.findall(r'<div class="(theme-chip-grid[^"]*)"', rendered)
    assert len(grid_classes) == 1, (
        "expected exactly one .theme-chip-grid on Display, got %d" % len(grid_classes))
    assert "theme-chip-grid--compact" in grid_classes[0]

    theme_count = len(device_config.THEME_IDS)
    chip_classes = re.findall(r'<label class="(theme-chip[^"]*)"', rendered)
    assert len(chip_classes) == theme_count, (
        "expected %d .theme-chip labels, got %d" % (theme_count, len(chip_classes)))
    for cls in chip_classes:
        assert "theme-chip--compact" in cls, "expected every remaining chip to carry the compact modifier, got %r" % (cls,)

    palette_count = rendered.count('class="palette" role="radiogroup"')
    assert palette_count == 3, "expected exactly 3 .palette grids, got %d" % palette_count
    palette_chip_count = rendered.count('class="palette-chip"')
    expected_palette_chips = theme_count * 3
    assert palette_chip_count == expected_palette_chips, (
        "expected %d .palette-chip entries, got %d" % (expected_palette_chips, palette_chip_count))

    legend = escape_html(config_page.THEME_CHIP_SWATCH_LEGEND)
    assert rendered.count(legend) == 1, (
        "expected the swatch legend exactly once, got %d" % rendered.count(legend))
    legend_html = '<p class="text-label section-caption">%s</p>' % legend
    assert legend_html in rendered
    assert ("</label></div>" + legend_html) in rendered, (
        "expected the legend to render as a sibling AFTER the grid, not inside it")


def test_the_swatch_legend_names_as_many_things_as_the_registry_carries():
    """the chip swatch legend names exactly as many things as the registry gives EVERY theme -
    computed from _palette_hex(departing_index)/_palette_hex(arriving_index) at check time,
    never a restated literal, so a future theme that DOES give departures and arrivals different
    inks would make this check demand two labels on its own (CFG-70, 27-07-PLAN.md Task 3)"""
    legend = config_page.THEME_CHIP_SWATCH_LEGEND
    labels = [part.strip() for part in legend.split("·") if part.strip()]
    label_count = len(labels)
    for theme_id in device_config.THEME_IDS:
        theme = device_config.THEMES[theme_id]
        colours = {
            config_page._palette_hex(theme["departing_index"]),
            config_page._palette_hex(theme["arriving_index"]),
        }
        expected = len(colours)
        assert label_count == expected, (
            "theme=%r: the registry gives this theme %d distinct swatch colour(s) but the "
            "shared legend %r names %d label(s)"
            % (theme_id, expected, legend, label_count))


def test_the_current_badge_reads_a_server_rendered_translated_attribute():
    """the 'Current' badge's text is server-rendered as a translated data-current-label attribute
    on exactly the --selected chip/card (never on any other), and the French render carries the
    French text (T10/B16, 22-10-PLAN.md Task 1)"""
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
# 30-07-PLAN.md Task 3 (T12/C1): structural CSS checks over the SERVED
# stylesheet (33-FOLLOWUPS.md F-01: declarations_for()/css_rules(),
# never a raw index/substring scan).
# ------------------------------------------------------------------

def test_segmented_control_resets_label_margin_and_panel_legend_retired(served_css):
    """the rule-kind segmented control (config_page.py's 'Match by' <div class="theme-form">,
    unaffected by CFG-85) keeps its own global label-margin reset and 28px row height (T12), and
    .frame-colours__panel-legend is confirmed retired outright rather than repointed - the usage
    panels and their <legend> elements are gone, the rule-add form's own segmented control never
    had a <legend> to begin with, and this genuinely NARROWS the serif boundary's own documented
    non-serif-exception set by one (C1, 30-07-PLAN.md Task 3)"""
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
    """the rules add-form renders as one left-aligned, centre-aligned flex ROW (X6/C4) - the
    flex-direction: column it never reset, not an auto margin, is what pushed 'Add rule' to the
    far right (22-10-PLAN.md Task 1)"""
    decls = declarations_for(served_css, ".rule-add-form--inline")
    assert decls.get("flex-direction") == "row", (
        "'.rule-add-form--inline' must reset .rule-add-form's own flex-direction: column, got %r"
        % (decls,))
    assert decls.get("align-items") == "center", (
        "'.rule-add-form--inline' must centre-align its four separate controls (C4), got %r"
        % (decls,))
    joined = " ".join(decls.values())
    assert "flex-end" not in joined, "'.rule-add-form--inline' must not keep the flex-end cross-axis alignment"
    assert decls.get("margin-left") != "auto", "'.rule-add-form--inline' must declare no auto left margin"


# --- 22-10-PLAN.md Task 2 (B9, B14, B15, B7/C3) -------------------

_TASK2_BASE_CTX = {
    "device_config": {
        "display_enabled": True, "quiet_hours_enabled": True,
        "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
    },
    "poll_cooldown_remaining": 0,
}


def test_each_time_input_carries_the_site_language_and_a_visible_24h_sibling():
    """each <input type="time"> carries the site language and a visible sibling showing the
    normalised 24h value (never a placeholder, never a title), in both languages (B14,
    22-10-PLAN.md Task 2)"""
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
    B7/C3's active-segment hover restore at the register's own 12% accent wash (22-10-PLAN.md
    Task 2)"""
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

    b15 = declarations_for(css, '.rule-add-form:not(.rule-add-form--inline) > button[type="submit"]')
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


# --- 22-10-PLAN.md Task 3 (B8, B17) -------------------------------

def test_send_a_test_lives_inside_the_notifications_card_via_the_form_idiom():
    """'Send a test' renders inside the Notifications card and reaches its own EMPTY sibling
    <form> through the cross-DOM form= idiom's fifth consumer - no control renders between two
    cards, and the form keeps its own action (B8, 22-10-PLAN.md Task 3)"""
    card = config_page.notifications_group(True, False, False)
    button = '<button type="submit" form="notifications-test">%s</button>' % escape_html(
        config_page.NOTIFICATIONS_TEST_BUTTON_TEXT)
    assert button in card, "expected the test button INSIDE the Notifications card (B8)"
    assert card.rstrip().endswith("</div>"), "expected the card to still close its own wrapper last"

    section = config_page.notifications_test_section()
    expected_form = (
        '<form method="post" action="/settings/notifications/test" '
        'id="notifications-test" class="notifications-test-form"></form>')
    assert section == expected_form, (
        "expected notifications_test_section() to render an EMPTY form carrying the button's "
        "form= id, got %r" % (section,))
    assert "<button" not in section, "the sibling form must hold no control of its own (B8)"

    rendered = config_page.render(_TASK2_BASE_CTX, scope=config_page.SCOPE_DEVICE)
    assert rendered.count('form="notifications-test"') == 1
    assert rendered.count('id="notifications-test"') == 1
    assert "</form><form" in rendered.replace("\n", ""), (
        "expected the empty test form to render immediately after the settings form, with no "
        "orphaned control between the two cards (B8)")
    card_end = rendered.index('id="notifications-test"')
    assert rendered.index('form="notifications-test"') < card_end, (
        "expected the button to render BEFORE the empty form, inside its card")
    assert config_page.NOTIFICATIONS_TEST_ROUTE in rendered


def test_the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input(served_css):
    """the wake-interval field puts its label on its own line above a content-sized input (8ch
    with a 96px minimum, no height declared so the 44px touch-target floor is untouched) with
    the unit as a sibling label (B17, 22-10-PLAN.md Task 3)"""
    rendered = config_page.wake_interval_group(300)
    label = '<label for="%s">%s</label>' % (
        config_page.WAKE_INTERVAL_INPUT_ID, escape_html(config_page.i18n.t("Wake interval (seconds)")))
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
    never reads '1 upcoming flights', in both languages (D-06/B16/CFG-29, 22-10-PLAN.md Task 3 -
    found by 22-08, landed here because this plan owns config_page.py)"""
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


# --- 23-06-PLAN.md Task 2 (D1/CFG-35) -----------------------------

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
    instant (D1/CFG-35, 23-06-PLAN.md Task 2)"""
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
    freshness line above them in the page header - a swap landing on this page's form is the P0
    Phase 22 existed to fix (B1/D1, 23-06-PLAN.md Task 2)"""
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
# 25-05-PLAN.md Task 1 (CFG-49): D18's two gauges, server-rendered.
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
    neither gauge renders without a usable interval, D-07's echo is honoured only where it is
    usable, and the screen-off cadence is stated (CFG-49, 25-05-PLAN.md Task 1)"""
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
    the "#" mark rather than a format artefact and has a French sibling (CFG-49/D-27,
    25-05-PLAN.md Task 1, quick 260923-gaf)

    Rewritten from the retired `_python_identifiers()` tokenize-over-source scan and the
    `ast.parse()` unqualified-import check (both banned outright by guard G2) into a behavioural
    proof: `config_page` never binds `battery_life_estimate` into its own namespace (a `not
    hasattr()` check - the same technique rubric S recommends for "retired symbol gone" - proving
    no unqualified `from companion.battery import battery_life_estimate` ever ran), and patching
    `companion.battery.battery_life_estimate` itself changes what
    `wake_battery_observed_text()` reports, byte for byte - which only holds if `config_page`
    reads the function off the QUALIFIED module object on every call rather than a name bound
    once at import time.
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
        assert template in i18n_fr.CATALOG, "the template %r has no French sibling" % template


# ------------------------------------------------------------------
# 27-06-PLAN.md Task 3 (CFG-67): the three texts, cut against
# 27-01-SUMMARY.md's own recorded baselines (measured 360px, rendered,
# both languages).
# ------------------------------------------------------------------

_DAYS_FIGURE_PATTERN = re.compile(r"≈\s*\d+\s*(?:day|days|jour|jours)\b")


def _html_region_text(fragment):
    stripped = re.sub(r"<[^>]*>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(stripped)).strip()


def test_wake_interval_caption_is_shortened_in_both_languages():
    """the wake-interval caption (#wake-interval-caption) is materially shorter than
    27-01-SUMMARY.md's recorded 220-char baseline in BOTH languages - the mechanism and
    apply-timing sentences are cut, the derived "(next wake ≈ ...)" suffix (a real
    timestamp, not an invented figure) is untouched (CFG-67, 27-06-PLAN.md Task 3)"""
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
    """the two wake gauges (.wake-gauge) are materially shorter than 27-01-SUMMARY.md's recorded
    254-char combined baseline in BOTH languages, and the insufficient-history state still
    prints NO absolute battery figure - asserted about the SAME reading the length is measured
    from, with the forbidden pattern scoped to the days-claim shape itself so it does not
    false-positive on an unrelated ≈-bearing timestamp (D18's honesty contract, CFG-67,
    27-06-PLAN.md Task 3)"""
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
    27-01-SUMMARY.md's recorded 188-char baseline in BOTH languages, and renders as EXACTLY
    QUIET_HOURS_SECTION_CAPTION's own translated text with no delay sentence appended at all any
    more - quiet_hours_group() no longer accepts a delay_sentence keyword (CFG-79, 29-05-PLAN.md
    Task 2, narrowing CFG-67's 27-06-PLAN.md Task 3 cut)"""
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


_GAUGE_ADDITION_CASES = [
    ("saved-in-band", 600, None, ' value="600"', True),
    ("stored-below-floor", 30, None, "", False),
    ("stored-above-ceiling", device_config.WAKE_INTERVAL_MAX_S + 1, None, "", False),
    ("never-set", None, None, "", False),
    ("rejected-save-raw-echo", 600, {"wake_interval_s": "7"}, ' value="7"', False),
    ("rejected-save-echoing-usable-value", 600, {"wake_interval_s": "900"}, ' value="900"', True),
]


@pytest.mark.parametrize(
    "name,current,submitted,value_attr,owes_gauges", _GAUGE_ADDITION_CASES,
    ids=[case[0] for case in _GAUGE_ADDITION_CASES])
def test_the_gauges_are_an_addition_and_the_number_input_is_untouched(
        name, current, submitted, value_attr, owes_gauges):
    """the two gauges are an ADDITION: across five argument shapes (in band, stored below the
    60s floor, stored above the ceiling, never set, and a rejected save's raw echo) the
    <input type="number"> is byte-identical to its pre-plan output - same id, name, min, max and
    placeholder, the value attribute present exactly when the guard admits it and absent
    otherwise (an out-of-range value blocks submission of the ENTIRE form) - with B17's label
    still above it, the unit sibling still immediately after it, the error block still attached,
    and both gauges appended after all of them (CFG-49/D-07/B17, 25-05-PLAN.md Task 1)"""
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
        escape_html(config_page.WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t("Wake interval (seconds)")))
    unit = ('<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
            % escape_html(config_page.WAKE_INTERVAL_UNIT_LABEL))
    assert label in markup and unit in markup, "%s: the B17 label or the unit sibling changed" % name
    assert markup.index(label) < markup.index(element), "%s: the label is no longer ABOVE the control (B17)" % name
    assert markup.index(unit) == markup.index(element) + len(element), (
        "%s: the unit sibling no longer sits immediately after the input" % name)
    gauge_at = markup.find('id="%s"' % config_page.WAKE_GAUGE_FRESHNESS_ID)
    if owes_gauges:
        assert gauge_at != -1, "%s: the gauges did not render" % name
    else:
        assert gauge_at == -1, "%s: a gauge rendered for a value the field itself refuses to show" % name
    if gauge_at != -1:
        assert gauge_at >= markup.index(unit), (
            "%s: a gauge renders BEFORE the control it describes" % name)


def test_the_gauges_error_block_still_attaches_with_the_gauges_after_it():
    """the error block still attaches to the field, with the gauges after it (CFG-49/D-07/B17,
    25-05-PLAN.md Task 1) - the second half of the six-shape check above, split out because it
    exercises a distinct fixture (an `errors` dict) rather than a seventh parametrize case"""
    with_error = config_page.wake_interval_group(
        600, errors={"wake_interval_s": "Enter a whole number of seconds."},
        submitted={"wake_interval_s": "900"}, battery_rows=_FALLING)
    error_block = re.search(r'<p class="field-error[^"]*" id="wake-interval-s-error"', with_error)
    assert error_block, "the field error block no longer renders"
    gauge_at = with_error.find('id="%s"' % config_page.WAKE_GAUGE_BATTERY_ID)
    assert gauge_at != -1, "the gauges did not render beside a rejected save's usable echo"
    assert gauge_at >= error_block.start(), (
        "a gauge renders between the input and its own error message")


# ------------------------------------------------------------------
# 25-05-PLAN.md Task 2 (CFG-49/CFG-52): the gated range, and the seam it
# shares with the one script.
# ------------------------------------------------------------------

def test_the_range_is_gated_nameless_and_bounded_by_device_config():
    """the wake-interval range is NAMELESS (a named one would post a second value for the same
    setting and the last to arrive would win), carries no role="slider" on top of a native
    slider, takes its min/max from server.device_config rather than a literal, steps by exactly
    the minute both gauges speak in, has its own accessible name and describes itself by the two
    gauges, renders ONLY inside 25-01's .js gate and only when there is a saved interval to
    start from, and nothing on the card is a live region (CFG-49/CFG-52/T-25-05-D, 25-05-PLAN.md
    Task 2)"""
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
    assert config_page.WAKE_SLIDER_STEP_S == config_page.WAKE_GAUGE_SECONDS_PER_MINUTE, (
        "the slider steps by %d s while the gauges speak in %d-second minutes"
        % (config_page.WAKE_SLIDER_STEP_S, config_page.WAKE_GAUGE_SECONDS_PER_MINUTE))
    for needed in ('aria-label="%s"' % escape_html(i18n.t(config_page.WAKE_SLIDER_LABEL)),
                   'aria-describedby="%s %s"' % (config_page.WAKE_GAUGE_FRESHNESS_ID,
                                                 config_page.WAKE_GAUGE_BATTERY_ID)):
        assert needed in element, "the range is missing %r - %s" % (needed, element)
    assert i18n.t(config_page.WAKE_SLIDER_LABEL) != i18n.t("Wake interval (seconds)"), (
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
    readout template contains the days wording at all (CFG-49/T-25-05-C, 25-05-PLAN.md Task 2)

    Fetched over HTTP (served_asset()), never opened from disk (TST-12); comments stripped with
    `strip_js_line_and_block_comments()` (preserves string/template literals, unlike
    `companion_markup.strip_js_comments_and_strings()`, which the quoted-literal searches below
    depend on).
    """
    markup = config_page.wake_interval_group(600, battery_rows=_FALLING)
    script = cp.strip_js_line_and_block_comments(value_controls_js)
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


# 30-03-PLAN.md Task 1 (CFG-85) / 27-07-PLAN.md Task 1 (CFG-68): the two
# closing structural proofs over the whole rendered Display page.

def test_the_display_page_carries_exactly_one_radio_set_per_theme_field():
    """the whole rendered Display page carries exactly len(device_config.THEME_IDS) radios
    named 'theme' - ONE set, computed from the registry at check time, re-homed from the
    retiring carousel's own equivalent guard so the page can never show one setting in two
    disagreeing places (CFG-85, 30-03-PLAN.md Task 1)"""
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
    appeared (CFG-68, 27-07-PLAN.md Task 1)"""
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


# --- 27-03-PLAN.md Task 1 (CFG-64) -------------------------------

def test_the_native_submit_is_emitted_unconditionally_on_every_render(tmp_path):
    """the native submit carrying STATIC_SAVE_FALLBACK_ATTR is emitted UNCONDITIONALLY - AND
    every one of the three scopes (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) renders it exactly
    once, across every extra keyword shape render() accepts, so there is no code path, past or
    future, that can omit the no-JS save floor (CFG-64, 27-03-PLAN.md Task 1)

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
        {"errors": {"wake_interval_s": "bad"}, "submitted": {"wake_interval_s": "x"}},
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
