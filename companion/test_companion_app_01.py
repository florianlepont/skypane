"""Part 01 of the `companion/test_companion_app.py` migration chain
(33-14-PLAN.md): the original harness's `check()` calls #1-#50, covering
`companion/auth.py`'s password/session-token/cookie/login-throttle
contract (Section 1) and `companion/layout.py`'s escaping/page-shell/
nav/component-builder contract (Section 2), plus five checks that used
to read `companion/static/style.css` from disk and now fetch it from a
running `companion/app.py` (`module_app_server_factory` +
`served_stylesheet()`), asserting on `companion_markup.css_rules()`/
`declarations_for()`/`rules_with_selector()` instead.

Every Section 1/2 check calls `companion.auth`/`companion.layout`'s own
functions directly, in-process — none of this half of the slice needs a
running `companion/app.py` server. Two checks pulled forward out of
order (33-MIGRATION-RULES.md's rubric T, WR-11's own root-unsafe
`os.chmod` pair from the still-legacy manual-resolution section, original
lines ~10315-10412) are ported at the end of this module with
`@requires_non_root`, so the legacy harness runs green as root from this
plan onward (32-REVIEW.md IN-05).
"""
import hashlib
import hmac
import html
import os
import re
import time
import urllib.parse

import pytest

import companion.auth as auth
import companion.layout as layout
import companion.test_companion_app_helpers as cah
from companion_app_server import http_request, login, served_stylesheet
from companion_markup import css_rules, declarations_for, rules_with_selector
from server.plane import manual_resolutions
from skypane_test_support import requires_non_root

TEST_PASSWORD = "companion-test-password-please-ignore"


@pytest.fixture(autouse=True)
def _password_configured(monkeypatch):
    """Every Section 1/2 check in this module runs with
    `auth.PASSWORD_ENV_VAR` set to `TEST_PASSWORD` — mirrors the legacy
    harness's own `main()` setup, which wrapped every check() call in
    exactly this env var assignment/restore.
    """
    monkeypatch.setenv(auth.PASSWORD_ENV_VAR, TEST_PASSWORD)


@pytest.fixture(scope="module")
def served_css(module_app_server_factory):
    """The stylesheet `companion/app.py` actually serves — the 5 checks
    at the end of this module that used to read `companion/static/
    style.css` from disk instead fetch it once, read-only, from a
    running server.
    """
    server = module_app_server_factory(fake_providers=True)
    return served_stylesheet(server)


def _sign_with_secret(payload, secret):
    """Hand-build an "expiry.signature" token signed with an arbitrary
    secret — used to construct forged/malformed tokens that never go
    through auth.issue_session_token(). Local to this module: no other
    part of the companion_app chain calls it.
    """
    signature = hmac.new(
        secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (payload, signature)


# ==========================================================================
# Section 1: companion/auth.py
# ==========================================================================


def test_password_ok_correct_and_wrong():
    """password_ok() accepts the correct password and rejects a wrong one"""
    assert auth.password_ok(TEST_PASSWORD)
    assert not auth.password_ok("definitely-the-wrong-password")


def test_password_ok_unconfigured_fails_closed(monkeypatch):
    """password_ok() raises AuthNotConfigured when the password env var is unset"""
    monkeypatch.delenv(auth.PASSWORD_ENV_VAR, raising=False)
    with pytest.raises(auth.AuthNotConfigured):
        auth.password_ok("anything")


def test_issue_and_verify_round_trip():
    """verify_session_token(issue_session_token()) is True"""
    token = auth.issue_session_token()
    assert auth.verify_session_token(token)


def test_verify_rejects_five_malformed_inputs():
    """verify_session_token() returns False for five malformed inputs without raising"""
    cases = {
        "empty string": "",
        "no separator": "nodotshere",
        "non-integer expiry": _sign_with_secret("not-a-number", TEST_PASSWORD),
        "different-secret signature": _sign_with_secret(
            str(int(time.time()) + 3600), "a-completely-different-secret"),
        "expiry in the past": _sign_with_secret(
            str(int(time.time()) - 100), TEST_PASSWORD),
    }
    for label, value in cases.items():
        assert auth.verify_session_token(value) is False, (
            "expected False for %s (%r)" % (label, value))


def test_verify_rejects_flipped_signature():
    """flipping a single hex character of a valid signature invalidates the token"""
    token = auth.issue_session_token()
    expiry, signature = token.split(".", 1)
    flipped_char = "0" if signature[0] != "0" else "1"
    flipped_signature = flipped_char + signature[1:]
    flipped_token = "%s.%s" % (expiry, flipped_signature)
    assert auth.verify_session_token(flipped_token) is False


def test_session_cookie_header_carries_security_flags():
    """session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path"""
    header = auth.session_set_cookie_header(auth.issue_session_token())
    for needle in ("HttpOnly", "Secure", "SameSite=Strict", "Path=/"):
        assert needle in header, "missing %r in session cookie header: %r" % (needle, header)


def test_insecure_cookies_flag_drops_secure_but_keeps_other_flags(monkeypatch):
    """SKYPANE_COMPANION_INSECURE_COOKIES=1 drops Secure from both cookie builders while
    HttpOnly/SameSite=Strict/Path survive (A-34/D-17)"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "1")
    session_header = auth.session_set_cookie_header(auth.issue_session_token())
    logout_header = auth.logout_set_cookie_header()
    for header in (session_header, logout_header):
        assert "Secure" not in header, "expected Secure to be absent, got %r" % (header,)
        for needle in ("HttpOnly", "SameSite=Strict", "Path=/"):
            assert needle in header, "missing %r in %r" % (needle, header)


def test_insecure_cookies_flag_fails_closed_on_other_values(monkeypatch):
    """SKYPANE_COMPANION_INSECURE_COOKIES="true" fails closed - Secure stays on (A-34/D-17)"""
    monkeypatch.setenv(auth.INSECURE_COOKIES_ENV_VAR, "true")
    header = auth.session_set_cookie_header(auth.issue_session_token())
    assert "Secure" in header, "expected Secure to remain on for a non-'1' value, got %r" % (header,)


def test_env_example_documents_insecure_cookies_flag():
    """deploy/skypane.env.example documents SKYPANE_COMPANION_INSECURE_COOKIES (A-34/D-17)"""
    env_example_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deploy", "skypane.env.example")
    with open(env_example_path, "r") as fh:
        contents = fh.read()
    assert auth.INSECURE_COOKIES_ENV_VAR in contents, (
        "expected %r to be documented in deploy/skypane.env.example"
        % (auth.INSECURE_COOKIES_ENV_VAR,))


def test_logout_cookie_expires_immediately():
    """logout_set_cookie_header() expires the cookie immediately"""
    header = auth.logout_set_cookie_header()
    assert "Max-Age=0" in header, "expected Max-Age=0 in the logout cookie header: %r" % (header,)


def test_parse_cookies_multi_and_malformed():
    """parse_cookies() returns each cookie by name and never raises on a bad header"""
    parsed = auth.parse_cookies(
        "%s=abc123; %s=dark" % (auth.SESSION_COOKIE_NAME, auth.UI_THEME_COOKIE_NAME))
    assert parsed.get(auth.SESSION_COOKIE_NAME) == "abc123"
    assert parsed.get(auth.UI_THEME_COOKIE_NAME) == "dark"
    assert auth.parse_cookies(None) == {}
    assert auth.parse_cookies("\x00\x01\x02 not a cookie") == {}


def test_login_throttle_allows_locks_and_resets():
    """LoginThrottle allows attempts up to its limit, locks out, then resets on success"""
    throttle = auth.LoginThrottle(limit=3, lockout_s=60)
    for _ in range(2):
        assert not throttle.locked_out()
        throttle.record_failure()
    throttle.record_failure()  # the 3rd failure reaches the limit
    assert throttle.locked_out()
    assert throttle.seconds_remaining() > 0
    throttle.record_success()
    assert not throttle.locked_out()


def test_login_throttle_self_releases_with_zero_length_window():
    """LoginThrottle with a zero-length window releases itself and a post-window failure
    starts a fresh count (A-32/D-15)"""
    # A-32/D-15: with lockout_s=0 the window elapses immediately, so no
    # real sleep is needed to exercise "a lockout releases itself." The
    # regression this pins: a naive fix that only checks the failure
    # count (not the elapsed window) would re-arm the lockout on this
    # 4th failure instead of starting a fresh count.
    throttle = auth.LoginThrottle(limit=3, lockout_s=0)
    for _ in range(3):
        throttle.record_failure()
    assert not throttle.locked_out()
    throttle.record_failure()
    assert not throttle.locked_out(), (
        "one post-window failure should count as 1 of 3 toward a fresh lockout, "
        "not immediately re-arm it")


def test_login_throttle_self_releases_with_real_window():
    """LoginThrottle with a real lockout_s releases itself once the window elapses and a
    post-window failure starts a fresh count (A-32/D-15)"""
    # Same property as above, but with a real non-zero lockout_s, proven
    # by rewinding _locked_until into the past — there is no clock
    # injection point on LoginThrottle.
    throttle = auth.LoginThrottle(limit=3, lockout_s=60)
    for _ in range(3):
        throttle.record_failure()
    assert throttle.locked_out()
    throttle._locked_until = time.time() - 1  # simulate the window elapsing
    assert not throttle.locked_out()
    throttle.record_failure()
    assert not throttle.locked_out(), (
        "one post-window failure should count as 1 of 3 toward a fresh lockout, "
        "not immediately re-arm it")


def test_forged_token_different_secret_rejected():
    """a forged token signed with a different secret is rejected"""
    forged = _sign_with_secret(
        str(int(time.time()) + 3600), "attacker-controlled-secret")
    assert auth.verify_session_token(forged) is False


def test_hand_built_expired_token_rejected():
    """a hand-built token expired by one second is rejected despite a correct signature"""
    expiry = str(int(time.time()) - 1)
    token = _sign_with_secret(expiry, TEST_PASSWORD)
    assert auth.verify_session_token(token) is False


def test_tokens_signed_with_derived_key_not_raw_password():
    """issued tokens verify within this process, but a raw-password-keyed signature (the old
    scheme) does not - the signing key is genuinely derived (A-33/D-16)"""
    # A-33/D-16: two tokens issued in this process both verify - the
    # derived signing key is stable within a process.
    token_a = auth.issue_session_token()
    token_b = auth.issue_session_token()
    assert auth.verify_session_token(token_a)
    assert auth.verify_session_token(token_b)
    # But a signature computed with the OLD scheme (the raw shared
    # password as the HMAC key, no per-process salt) must NOT verify -
    # that is the actual behaviour being fixed.
    expiry = str(int(time.time()) + 3600)
    raw_password_token = _sign_with_secret(expiry, TEST_PASSWORD)
    assert auth.verify_session_token(raw_password_token) is False, (
        "a signature computed with the raw password (the pre-D-16 scheme) must not "
        "verify - the signing key must be genuinely derived")


def test_revoke_then_is_revoked_round_trip():
    """revoke(token) then is_revoked(token) is True, a never-issued token is False, and a
    malformed token passed to revoke() raises nothing (A-33/D-16)"""
    token = auth.issue_session_token()
    # A different token string, not a second real session (which
    # issue_session_token()'s nanosecond-resolution expiry already makes
    # vanishingly unlikely to collide with `token` anyway) - is_revoked()
    # only ever does a plain membership test.
    never_issued = token + "0"
    assert not auth.is_revoked(token)
    auth.revoke(token)
    assert auth.is_revoked(token)
    assert not auth.is_revoked(never_issued), (
        "revoking one token must not affect a different, never-revoked token")
    auth.revoke("not-a-valid-token-shape")
    auth.revoke(None)
    auth.revoke("")


def test_revoked_token_pruned_once_it_expires():
    """a revoked token is pruned out of the revocation set once its own expiry passes
    (A-33/D-16, T-19-14: the set stays bounded)"""
    # revoke() stores (token -> expiry); once that expiry has passed, the
    # NEXT revoke()/is_revoked() call must prune the entry out of
    # auth._REVOKED, keeping the set bounded rather than growing for the
    # lifetime of the process (T-19-14).
    token = auth.issue_session_token()
    auth.revoke(token)
    assert token in auth._REVOKED, "expected revoke() to store a not-yet-expired token"
    auth._REVOKED[token] = 0  # simulate its expiry having already passed
    assert not auth.is_revoked(token), "expected an expired revoked entry to report False, not True"
    assert token not in auth._REVOKED, (
        "expected is_revoked() to prune the now-expired entry out of _REVOKED")


def test_auth_not_configured_message_omits_password(monkeypatch):
    """AuthNotConfigured's message never contains the configured password value"""
    monkeypatch.delenv(auth.PASSWORD_ENV_VAR, raising=False)
    with pytest.raises(auth.AuthNotConfigured) as excinfo:
        auth.configured_password()
    assert TEST_PASSWORD not in str(excinfo.value), (
        "the exception text must never contain the password value")


# ==========================================================================
# Section 2: companion/layout.py
# ==========================================================================


def test_escape_html_all_special_chars():
    """escape_html() escapes all five HTML-special characters"""
    hostile = "<script>&\"'</script>"
    escaped = layout.escape_html(hostile)
    # '&' legitimately survives *as the start of an entity* (e.g. "&amp;",
    # "&lt;") - compare against the stdlib's own reference escaping
    # instead of a naive per-character containment check, which would
    # false-positive on "&amp;" containing "&".
    expected = html.escape(hostile, quote=True)
    assert escaped == expected
    for literal_special_char in ("<", ">", '"', "'"):
        assert literal_special_char not in escaped, (
            "unescaped %r survived in %r" % (literal_special_char, escaped))


def test_escape_html_non_string_inputs():
    """escape_html() coerces None to an empty string and non-strings to their string form"""
    assert layout.escape_html(None) == ""
    assert layout.escape_html(42) == "42"


def test_page_shell_document_shape():
    """page_shell() renders one document with lang/viewport/stylesheet/title/a nav link for
    every NAV_TABS route"""
    rendered = layout.page_shell(title="Health", active="health", body="<p>x</p>")
    assert rendered.count("<html") == 1
    assert 'lang="en"' in rendered
    assert "width=device-width" in rendered
    assert "/static/style.css" in rendered
    assert layout.SITE_TITLE in rendered
    missing = [
        route for route, _ in layout.NAV_TABS
        if ('href="%s"' % route) not in rendered]
    assert not missing, "missing nav link hrefs: %r" % (missing,)


def test_page_shell_marks_only_the_active_sub960_nav_link():
    """the sub-960px nav link matching `active` carries a distinguishing class and
    aria-current, the others carry neither (retargeted from the retired dropdown nav onto
    the tab bar, 22-14-PLAN.md Task 2)"""
    rendered = layout.page_shell(
        title="Health", active="health", body="",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    nav_start = rendered.find('<nav class="tab-bar"')
    nav_end = rendered.find("</nav>", nav_start)
    tab_bar_html = rendered[nav_start:nav_end]
    for route, _ in layout.NAV_TABS:
        slug = route.lstrip("/")
        href_needle = 'href="%s"' % route
        href_index = tab_bar_html.find(href_needle)
        assert href_index != -1, "missing tab-bar link for %r" % route
        tag_start = tab_bar_html.rfind("<a", 0, href_index)
        tag_end = tab_bar_html.find(">", href_index)
        tag = tab_bar_html[tag_start:tag_end]
        is_active_class_present = (
            "tab-bar__link--active" in tag or "mobile-nav__link--active" in tag)
        has_aria_current = 'aria-current="page"' in tag
        if slug == "health":
            assert is_active_class_present, (
                "expected the active link (%r) to carry the active class" % route)
            assert has_aria_current, (
                "expected the active link (%r) to carry aria-current" % route)
        else:
            assert not is_active_class_present, (
                "expected a non-active link (%r) to not carry the active class" % route)
            assert not has_aria_current, (
                "expected a non-active link (%r) to not carry aria-current" % route)


# --- 06.6.4.1.1-04 (D-17): flash banner moves below page_header() ---


def test_flash_banner_spliced_below_page_header_marker_never_leaks():
    """page_shell() splices the flash banner in directly below page_header()'s title, and
    FLASH_SLOT_MARKER never reaches the rendered document"""
    body = layout.page_header("Title") + "<p>body content</p>"
    no_flash = layout.page_shell(title="X", active="settings", body=body)
    flash_markup = layout.flash_banner("Saved")
    with_flash = layout.page_shell(
        title="X", active="settings", body=body, flash=flash_markup)
    assert layout.FLASH_SLOT_MARKER not in no_flash
    assert layout.FLASH_SLOT_MARKER not in with_flash
    assert "banner--flash" not in no_flash
    assert with_flash.index("banner--flash") > with_flash.index("page-header"), (
        "expected the flash banner to render after the page header, not before it")
    assert with_flash.replace(flash_markup, "", 1) == no_flash, (
        "expected the flash-present and flash-absent documents to differ only by the "
        "spliced-in banner")


def test_flash_banner_fallback_slot_when_body_has_no_marker():
    """page_shell() still renders the flash banner in its original slot for a body with no
    FLASH_SLOT_MARKER (the pre-page_header() fallback path)"""
    # login/404-style bodies never call page_header(), so they carry no
    # FLASH_SLOT_MARKER - the flash banner must keep rendering in its
    # original before-body slot rather than silently vanishing.
    bare_body = "<p>bare content, no page_header()</p>"
    flash_markup = layout.flash_banner("Saved")
    rendered = layout.page_shell(
        title="X", active="settings", body=bare_body, flash=flash_markup)
    assert "banner--flash" in rendered, "expected the flash banner in the fallback (before-body) slot"
    assert layout.FLASH_SLOT_MARKER not in rendered
    assert rendered.index("banner--flash") < rendered.index("bare content"), (
        "expected the fallback flash banner to render before the marker-less body")


def test_anomaly_banner_unaffected_by_the_flash_slot_move():
    """an anomaly banner (banner=) is unaffected by the flash-slot move and still renders in
    its existing pre-body slot"""
    body = layout.page_header("Title") + "<p>body content</p>"
    rendered = layout.page_shell(
        title="X", active="settings", body=body, banner=layout.anomaly_banner("Uh oh"))
    assert "banner--anomaly" in rendered
    assert "banner--flash" not in rendered
    assert rendered.index("banner--anomaly") < rendered.index("page-header"), (
        "expected the anomaly banner to keep rendering before the page header")


def test_theme_resolution():
    """page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto"""
    rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="dark")
    assert 'data-ui-theme="dark"' in rendered
    assert layout.ui_theme_from_cookie({}) == "auto"
    unrecognised = {layout.UI_THEME_COOKIE_NAME: "not-a-real-theme"}
    assert layout.ui_theme_from_cookie(unrecognised) == "auto"


def test_status_dot_states():
    """status_dot() encodes the state as a fixed class, escapes the label, falls back to warn"""
    ok_markup = layout.status_dot("ok", "All good")
    assert "dot--ok" in ok_markup and "All good" in ok_markup
    unknown_markup = layout.status_dot("not-a-real-state", "<b>hi</b>")
    assert "dot--warn" in unknown_markup, "expected an unrecognised state to fall back to the warn class"
    assert "<b>" not in unknown_markup, "expected the label to be escaped"


def test_data_table_escapes_and_empty_state():
    """data_table() escapes every header/cell and emits the empty-state block for zero rows"""
    table_markup = layout.data_table(["Name", "<x>"], [["<b>a</b>", "1"]])
    assert "<b>a</b>" not in table_markup and "<x>" not in table_markup
    empty_markup = layout.data_table(["Name"], [])
    assert "<table" not in empty_markup, "expected the empty-state block instead of a <table> for zero rows"


def test_data_table_wrapped_for_horizontal_scroll():
    """data_table() wraps its <table> in a horizontally-scrollable container"""
    # 2026-08-28 mobile-cropping fix: a wide table (History's timestamp/
    # callsign/hex/airline/type columns, Airlines' unresolved-prefix
    # table) must scroll horizontally on a phone viewport instead of
    # overflowing past it uncropped.
    table_markup = layout.data_table(["A", "B"], [["1", "2"]])
    assert '<div class="data-table-wrap">' in table_markup


def test_sidebar_nav_renders_all_tabs_with_one_active():
    """sidebar_nav() renders every NAV_TABS link with exactly one active"""
    markup = layout.sidebar_nav("flights")
    assert 'aria-label="Primary navigation"' in markup
    for route, label in layout.NAV_TABS:
        assert route in markup and label in markup
    assert markup.count("sidebar-link--active") == 1


def test_sidebar_nav_escapes_hostile_active():
    """sidebar_nav() matches no tab and stays script-free for a hostile active value"""
    markup = layout.sidebar_nav("<script>alert(1)</script>")
    assert "<script>" not in markup
    assert markup.count("sidebar-link--active") == 0


def test_nav_tabs_shrunk_to_four_settled_order():
    """layout.NAV_TABS holds exactly 6 entries, in order home/display/flights/airlines/health/device"""
    # 06.6.4.1-08 (D-22): NAV_TABS shrinks from five entries to four -
    # Preview is retired, its whole content absorbed into History
    # (06.6.4.1-05). Order matters: every nav renderer walks NAV_TABS in
    # this exact order. Phase 18: six tabs in two groups - the everyday
    # four, then the two under the "Advanced" label - flattened in that
    # order.
    assert len(layout.NAV_TABS) == 6
    expected_routes = ("/", "/display", "/flights", "/airlines", "/health", "/device")
    actual_routes = tuple(route for route, _ in layout.NAV_TABS)
    assert actual_routes == expected_routes


def test_sidebar_and_tab_bar_render_exactly_six_links_one_active_each():
    """a rendered authenticated page contains exactly six sidebar nav links and exactly six
    tab-bar links, with exactly one marked active in each, and the hamburger dropdown holds
    zero destination links (retargeted from the dropdown onto the tab bar, 22-14-PLAN.md
    Task 2)"""
    # RETARGETED IN PLACE, STRICTLY NARROWER (22-14-PLAN.md Task 2,
    # X9/D-10): the sub-960px half counted the dropdown's six links; the
    # dropdown now holds preferences and the tab bar holds destinations.
    # The count and the exactly-one-active assertion are unchanged; what
    # they are counted over moved.
    sidebar_markup = layout.sidebar_nav("flights")
    sidebar_link_count = sidebar_markup.count('<a class="sidebar-link')
    assert sidebar_link_count == 6
    assert sidebar_markup.count("sidebar-link--active") == 1

    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    bar_link_count = (
        bar.count('<a class="tab-bar__link')
        + bar.count('<a class="mobile-nav__link'))
    assert bar_link_count == 6
    assert bar.count("tab-bar__link--active") == 1

    # And the dropdown now holds ZERO destination links - this is the
    # ~420px page shove X9 measured, removed.
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    assert panel.count('<a class="mobile-nav__link') == 0, (
        "expected the dropdown panel to hold no destination links at all")
    assert "mobile-nav__nav" not in panel, (
        "expected the dropdown's own navigation landmark to be removed, not emptied")
    for route, _label in layout.NAV_TABS:
        if route == layout.HOME_ROUTE:
            # The state reminder is still a link to Home on a non-Home
            # page - that is nav_status_html()'s own contract, not a
            # destination menu entry.
            continue
        assert ('href="%s"' % route) not in panel, (
            "expected no destination href (%r) left in the dropdown panel" % route)


def test_eye_glyph_survives_nav_shrink():
    """the eye glyph (icon-nav-preview) is still a whitelist member and icon_html() returns
    non-empty markup for it, even though its nav-slug mapping was removed"""
    # 06.6.4.1-08 (D-22): "icon-nav-preview" (the eye glyph) stays in the
    # ICON_IDS whitelist even though NAV_ICON_IDS no longer maps a
    # "preview" slug to it - companion/pages/history_page.py's View-panel
    # trigger is its sole remaining consumer.
    assert "icon-nav-preview" in layout.ICON_IDS
    markup = layout.icon_html("icon-nav-preview")
    assert markup and "<svg" in markup


def test_stat_tile_status_classes_caption_escape_and_content_passthrough():
    """stat_tile() maps status to a fixed class with an accent fallback, escapes the caption,
    and passes content_html through unmodified"""
    for status, expected_class in (
        ("ok", "stat-tile--ok"),
        ("warn", "stat-tile--warn"),
        ("error", "stat-tile--error"),
    ):
        markup = layout.stat_tile("c", "x", status)
        assert expected_class in markup, "expected %r to map to %r" % (status, expected_class)
    assert "stat-tile--accent" in layout.stat_tile("c", "x")
    assert "stat-tile--accent" in layout.stat_tile("c", "x", "not-a-real-state")
    assert "<b>" not in layout.stat_tile("<b>hi</b>", "x"), "expected the caption to be escaped"
    dot_markup = layout.status_dot("ok", "All good")
    tile_markup = layout.stat_tile("Device", dot_markup, "ok")
    assert "dot--ok" in tile_markup, "expected content_html to reach the output unmodified"


def test_card_status_class_whitelist_and_empty_fallback():
    """card_status_class() maps status to base_class + a fixed suffix for the three whitelisted
    states, and falls back to the empty string (not an accent class) for None or an
    unrecognised status — the divergence from stat_tile()'s own fallback (quick task
    260902-gjj, ISSUE 2)"""
    # quick task 260902-gjj (ISSUE 2): card_status_class()'s own
    # contract, following stat_tile()'s check above in shape - the three
    # whitelisted mappings, and the empty string (not an accent fallback
    # class) for both None and an unrecognised status, per that
    # function's own documented divergence from stat_tile()'s accent
    # fallback.
    for status, expected_class in (
        ("ok", "page-section--ok"),
        ("warn", "page-section--warn"),
        ("error", "page-section--error"),
    ):
        got = layout.card_status_class("page-section", status)
        assert got == expected_class, "expected %r to map to %r, got %r" % (status, expected_class, got)
    assert layout.card_status_class("page-section", None) == ""
    assert layout.card_status_class("page-section", "not-a-real-state") == ""
    assert layout.card_status_class("battery-trend-section", "ok") == "battery-trend-section--ok", (
        "expected base_class to be reused verbatim in the modifier's own prefix")


def test_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme():
    """page_shell() wraps header+sidebar+main in .dashboard-shell with both nav landmarks
    (sidebar + tab bar, and exactly one when there is no tab bar) and both theme-form copies
    present"""
    rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
    for needle in (
        '<div class="dashboard-shell">',
        '<aside class="dashboard-sidebar">',
        '<main class="page-content dashboard-main" id="main-content" tabindex="-1">',
    ):
        assert needle in rendered, "expected %r in the rendered shell" % needle
    # 06.6.1-05: two nav landmarks now exist - sidebar_nav() and the
    # hamburger dropdown's _mobile_nav_html() - deliberately sharing the
    # same "Primary navigation" aria-label; CSS alone decides which is
    # visible at a given width, so both are always in the DOM.
    #
    # RETARGETED IN PLACE, STRICTLY NARROWER (22-14-PLAN.md Task 2,
    # X9/D-10): the sub-960px landmark moved from the dropdown to the
    # bottom tab bar, so the PAIR is now sidebar + tab bar and the count
    # is asserted on a render that has a tab bar. A page with no device
    # config (the 404) carries exactly ONE landmark, never an empty
    # second one.
    with_bar = layout.page_shell(
        title="Health", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    assert with_bar.count('aria-label="Primary navigation"') == 2, (
        "expected exactly two Primary navigation landmarks (sidebar + tab bar)")
    assert rendered.count('aria-label="Primary navigation"') == 1, (
        "a page with no device config renders no tab bar, so it must expose exactly one "
        "navigation landmark - never an empty second one")
    assert rendered.count('id="%s"' % layout.MOBILE_NAV_ID) == 1, "expected exactly one dropdown panel"
    assert rendered.count('action="/ui-theme"') == 2, "expected both theme-form copies posting to /ui-theme"


def test_page_shell_skip_link_target_is_focusable():
    """page_shell()'s skip link target carries tabindex="-1" so it actually receives focus"""
    # CR-01: the skip link's href="#main-content" target must itself be
    # focusable (tabindex="-1") or activating the link scrolls the
    # viewport without moving keyboard focus, per the HTML
    # fragment-navigation focusing steps (WCAG SCR28/G1).
    rendered = layout.page_shell(title="Health", active="health", body="<p>b</p>")
    assert '<a class="skip-link" href="#main-content">Skip to content</a>' in rendered
    assert 'id="main-content" tabindex="-1"' in rendered


def test_page_shell_escapes_hostile_body():
    """page_shell()'s output contains no unescaped script tag for an escaped hostile body"""
    escaped_hostile_body = layout.escape_html("<script>alert(1)</script>")
    rendered = layout.page_shell(title="Health", active="health", body=escaped_hostile_body)
    assert "<script>" not in rendered


# --- 06.6.1-04 Task 1: icon sprite, whitelisted builder, stat_tile() icon slot ---


def test_icon_sprite_integrity():
    """layout.ICON_IDS has exactly twenty-three unique members, each a symbol id in
    ICON_DEFS_HTML and vice versa"""
    # 06.6.3: the whitelist grew from ten to fourteen members
    # (icon-check/icon-copy/icon-refresh/icon-search, D-05/D-23/D-12/
    # D-20). quick task 260903-df3 grew it again, fourteen to fifteen
    # (icon-upload, the Airlines lightbox replace zone's glyph).
    # 22-14-PLAN.md Task 1 (X9/D-10) grows it from twenty-one to
    # twenty-two (icon-more, the bottom tab bar's "More" cell).
    # 28-01-PLAN.md (CFG-76) grows it again, 22 -> 23 (icon-gear,
    # #site-nav-toggle's new glyph).
    assert len(layout.ICON_IDS) == 23
    assert len(set(layout.ICON_IDS)) == 23, "expected ICON_IDS to have no duplicates"
    symbol_ids = re.findall(r'<symbol[^>]*id="([^"]+)"', layout.ICON_DEFS_HTML)
    assert sorted(symbol_ids) == sorted(layout.ICON_IDS), (
        "sprite symbol ids %r do not match ICON_IDS %r" % (symbol_ids, layout.ICON_IDS))
    assert layout.ICON_DEFS_HTML.count("<symbol") == 23
    assert 'stroke="currentColor"' in layout.ICON_DEFS_HTML
    assert 'fill="#' not in layout.ICON_DEFS_HTML, "a hard-coded hex fill would defeat the per-status tint"


def test_icon_html_whitelist_enforcement():
    """icon_html() returns markup for every whitelisted id and '' for an unknown/empty/None/
    hostile id"""
    for icon_id in layout.ICON_IDS:
        out = layout.icon_html(icon_id)
        assert out and "<use" in out, "expected non-empty <use markup for %r, got %r" % (icon_id, out)
    for bad in ("not-an-icon", "", None):
        assert layout.icon_html(bad) == ""
    hostile = '"><script>alert(1)</script>'
    assert layout.icon_html(hostile) == ""
    assert hostile not in layout.icon_html(hostile), "a hostile id string must never reach icon_html()'s output"


def test_stat_tile_backcompat_and_icon_slot():
    """stat_tile() is byte-identical with icon omitted and places a valid icon before the
    caption text"""
    default_call = layout.stat_tile("c", "x")
    explicit_none = layout.stat_tile("c", "x", None)
    assert default_call == explicit_none
    assert "<svg" not in default_call, "expected no <svg when icon is omitted"
    valid_icon = layout.ICON_IDS[0]
    with_icon = layout.stat_tile("Cap", "<p>y</p>", "ok", icon=valid_icon)
    assert with_icon.count("<svg") == 1, "expected exactly one <svg when a valid icon is supplied"
    assert layout.STAT_TILE_ICON_CLASS in with_icon, "expected the tint class on the tile's icon"
    assert "stat-tile--ok" in with_icon, "expected the status class to still be present"
    assert with_icon.index("<svg") < with_icon.index("Cap"), (
        "expected the icon markup to precede the caption text")


def test_page_shell_emits_sprite_once_no_inline_styles():
    """page_shell() emits exactly one sprite (one <defs, twenty-three <symbol) before
    dashboard-shell, no inline styles"""
    doc = layout.page_shell(title="T", active="health", body="<p>b</p>")
    assert doc.count("<defs") == 1
    # 22-14-PLAN.md Task 1 (X9/D-10): twenty-one -> twenty-two
    # (icon-more). 28-01-PLAN.md (CFG-76): 22 -> 23 (icon-gear).
    assert doc.count("<symbol") == 23
    assert doc.index("icon-defs") < doc.index("dashboard-shell"), (
        "expected the sprite to precede the dashboard-shell div")
    assert ' style="' not in doc, "page_shell() must emit no inline styles"


# --- heading-color-consistency debug session -------------------------
#
# D-03's serif-headings contract used to be an allow-list in a style.css
# comment. These checks make the contract executable in both directions
# — every heading role IS serif, and no dense/tabular role IS NOT — over
# the stylesheet companion/app.py actually serves, via companion_markup's
# structural CSS parser rather than a raw-text/comment search.


def test_heading_roles_share_one_serif_rule_with_named_nested_exception(served_css):
    """every heading role (h1/h2/h3/legend/.text-heading) shares one serif rule except the
    one named, asserted nested card-title sans exception (D-09), and `legend` does not
    override its weight"""
    # The single rule that grants the serif family: h1/h2/h3/legend/
    # .text-heading all resolve font-family/font-weight through
    # declarations_for()'s own "last rule wins, same at-rule context"
    # merge, which mirrors the browser's real cascade for same-
    # specificity selectors. `legend` also carries its own DEDICATED
    # rule later in the file (font-size/padding only) — if that rule
    # ever restated font-weight, declarations_for()'s merge would surface
    # the override here, which is exactly the D-09/CR-adjacent regression
    # this check exists to catch (both selectors are bare `legend`,
    # (0,0,1) specificity, so the later rule wins at equal specificity).
    for selector in ("h1", "h2", "h3", "legend", ".text-heading"):
        declarations = declarations_for(served_css, selector)
        assert declarations.get("font-family") == "var(--font-serif)", (
            "expected %r to resolve font-family to var(--font-serif), got %r"
            % (selector, declarations.get("font-family")))
        assert declarations.get("font-weight") == "var(--weight-regular)", (
            "expected %r to resolve font-weight to var(--weight-regular) — a later "
            "same-specificity rule may be overriding it, got %r"
            % (selector, declarations.get("font-weight")))
    # 06.6.4.1.1-04 Task 2 (D-09): the shared rule above grants serif to
    # every heading role, and there is exactly one documented, asserted
    # exception - the nested card-title selector ("Battery trend",
    # "Unresolved prefixes", "Resolution statistics"), deliberately
    # demoted to the sans --font-ui voice at 16px semibold.
    nested = declarations_for(served_css, ".page-section--nested > h2")
    assert nested.get("font-family") == "var(--font-ui)", (
        "expected the nested card-title exception to resolve font-family to var(--font-ui) "
        "(D-09's sans override)")


def test_serif_never_reaches_dense_or_tabular_content(served_css):
    """--font-serif never reaches table, body, mono, nav-link or stat-tile-caption rules
    (D-03's headings-only boundary; D-13 retired the caption's own former serif exception)"""
    # D-03's other half: serif is headings-only. Body, tables, form
    # controls, nav links and mono content stay on --font-ui. Guards
    # against the rejected "serif partout" option creeping back in one
    # rule at a time. `.stat-tile__caption` (D-13) was this file's one
    # named Label-role serif exception until D-13 retired it in favour of
    # the unified sans 12px label voice - it is listed here now so that
    # retirement cannot silently reverse without a deliberate edit to
    # this check.
    forbidden_selectors = (
        ".data-table", ".cell-primary", ".cell-secondary", ".mono", ".text-body",
        ".sidebar-link", ".mobile-nav__link", ".stat-tile__caption")
    for selector in forbidden_selectors:
        for rule in rules_with_selector(served_css, selector):
            for _prop, value in rule.declarations:
                assert "--font-serif" not in value, (
                    "%s applies --font-serif; serif is a headings-only treatment (D-03), "
                    "never dense/tabular content" % selector)


def test_mobile_nav_link_and_sidebar_link_geometries_stay_diverged(served_css):
    """mobile dropdown nav link keeps its restored 44px/Body-size tap target while the desktop
    sidebar link stays at its D-05 32px/Label-size compaction (260902-qkm)"""
    # 260902-qkm: D-05 (06.6.4-04) reached .mobile-nav__link by mistake -
    # the mobile dropdown is the phone's only nav, with no desktop
    # compactness argument to trade against, while .sidebar-link is
    # structurally desktop-only (hidden below 960px). The two renderings
    # are deliberately different sizes and neither may drift into the
    # other.
    mobile = declarations_for(served_css, ".mobile-nav__link")
    assert mobile.get("min-height") == "44px", (
        ".mobile-nav__link lost its restored min-height: 44px tap target (260902-qkm)")
    assert mobile.get("font-size") == "var(--font-body-size)", (
        ".mobile-nav__link's font size drifted off var(--font-body-size) (260902-qkm)")

    sidebar = declarations_for(served_css, ".sidebar-link")
    assert sidebar.get("height") == "32px", (
        ".sidebar-link's D-05 32px desktop compaction was reverted - it is structurally "
        "desktop-only and should stay compact, unlike the mobile dropdown link")
    assert sidebar.get("font-size") == "var(--font-label-size)", (
        ".sidebar-link's font size drifted off var(--font-label-size)")


def test_icon_classes_styled_in_served_stylesheet(served_css):
    """the icon/icon-defs/STAT_TILE_ICON_CLASS class names all appear in companion/static/
    style.css"""
    rules = css_rules(served_css)
    all_selectors = " ".join(sel for rule in rules for sel in rule.selectors)
    for cls in ("icon-defs", "icon", layout.STAT_TILE_ICON_CLASS):
        assert cls in all_selectors, "expected class %r to be styled in the served stylesheet" % cls


def test_exactly_one_error_signal_colour_token(served_css):
    """there is exactly one error-signal colour token (--color-status-error), no
    --color-destructive duplicate"""
    # --color-destructive and --color-status-error held identical values
    # in all four token blocks while being used interchangeably for one
    # concept, so "change the error colour" silently meant "change two
    # tokens in four places". The duplicate is gone; this keeps it gone.
    for rule in css_rules(served_css):
        for prop, value in rule.declarations:
            assert prop != "--color-destructive" and "--color-destructive" not in value, (
                "--color-destructive is back; it duplicated --color-status-error exactly and "
                "is the reason the two could drift. Use --color-status-error")


# ==========================================================================
# Out-of-order pull (33-MIGRATION-RULES.md rubric T): the two root-unsafe
# WR-11 os.chmod checks from the still-legacy manual-resolution section
# (original lines ~10315-10412), so companion/test_companion_app.py runs
# green as root from this plan onward (32-REVIEW.md IN-05).
# ==========================================================================


@requires_non_root
def test_resolve_post_redirects_manual_save_failed_when_state_dir_is_read_only(make_app_server):
    """POST /airlines/resolve redirects with the manual_save_failed flash key (never a
    dropped connection) when add_entry() cannot write because the state dir is read-only —
    the exact failure mode CR-01 fixed, exercised end to end (WR-11)"""
    # WR-11: FLASH_KEY_MANUAL_SAVE_FAILED was added specifically because
    # add_entry() can return ADD_FAILED on an unwritable state dir - CR-01
    # fixed the bug that made that path raise instead (a dropped
    # connection, no flash at all); this proves the flash key itself is
    # actually reached end to end.
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    cah.seed_unresolved_prefixes(server.state_dir, {
        "FLD": {
            "count": 1, "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-01T00:00:00+00:00", "example_callsign": "FLD100",
        },
    })

    os.chmod(server.state_dir, 0o500)
    try:
        resolve_data = urllib.parse.urlencode(
            {"prefix": "FLD", "airline_name": "Unwritable Air"}).encode()
        status, headers, _ = http_request(
            server.base_url() + "/airlines/resolve", method="POST", data=resolve_data,
            cookie=cookie)
    finally:
        os.chmod(server.state_dir, 0o700)

    assert status == 303, "expected a 303 redirect even on a write failure, got %d" % status
    location = headers.get("Location", "")
    assert "flash=manual_save_failed" in location, (
        "expected the manual_save_failed flash key when add_entry() fails to write, got %r"
        % location)
    assert "resolve=FLD" in location, (
        "expected the redirect to carry resolve=FLD so the operator lands back on the form, "
        "got %r" % location)
    registry_after = manual_resolutions.load_manual_resolutions(server.state_dir)
    assert "FLD" not in registry_after, "expected nothing persisted after a failed write"


@requires_non_root
def test_delete_post_redirects_manual_delete_failed_when_state_dir_is_read_only(make_app_server):
    """POST /airlines/manual-resolutions/{prefix}/delete redirects with the
    manual_delete_failed flash key, leaving the entry in place, when delete_entry() cannot
    write because the state dir is read-only (WR-11)"""
    # WR-11's mirror case: FLASH_KEY_MANUAL_DELETE_FAILED for
    # delete_entry() returning False after a genuine write failure
    # (never for an already-absent prefix, which is a silent no-op by
    # design).
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    add_result = manual_resolutions.add_entry(server.state_dir, "DLF", "Undeletable Air")
    assert add_result == manual_resolutions.ADD_OK, (
        "test setup failure: add_entry() returned %r" % (add_result,))

    os.chmod(server.state_dir, 0o500)
    try:
        status, headers, _ = http_request(
            server.base_url() + "/airlines/manual-resolutions/DLF/delete", method="POST",
            cookie=cookie)
    finally:
        os.chmod(server.state_dir, 0o700)

    assert status == 303, "expected a 303 redirect even on a write failure, got %d" % status
    location = headers.get("Location", "")
    assert "flash=manual_delete_failed" in location, (
        "expected the manual_delete_failed flash key when delete_entry() fails to write, "
        "got %r" % location)
    registry_after = manual_resolutions.load_manual_resolutions(server.state_dir)
    assert "DLF" in registry_after, "expected the entry to survive a failed delete_entry() write"
