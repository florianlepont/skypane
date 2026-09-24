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
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import app as companion_app
from companion import frame_state
from companion.layout import escape_html
from companion.pages import config_page
from companion_app_server import get, http_request, login
from server import device_config, history_db
from server.plane import calendar_rules


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


def _caption_word_count_text(fragment):
    """THE ONE COUNTING RULE this whole floor applies: strip tags, unescape HTML entities,
    collapse internal whitespace, then strip a single leading em dash and its following space -
    layout.section_intro_html()'s own intro sentences legitimately open with '- ', and that
    leading mark is not a WORD by any reading of 'at most 12 words'.
    """
    stripped = re.sub(r"<[^>]*>", "", fragment)
    text = html.unescape(stripped).strip()
    if text.startswith("— "):
        text = text[2:]
    return re.sub(r"\s+", " ", text).strip()


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
            _caption_word_count_text(i18n.t_lang(text, lang))
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
                text = _caption_word_count_text(fragment)
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
                text = _caption_word_count_text(fragment)
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
