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
import time

import pytest

import companion.auth as auth
import companion.layout as layout

TEST_PASSWORD = "companion-test-password-please-ignore"


@pytest.fixture(autouse=True)
def _password_configured(monkeypatch):
    """Every Section 1/2 check in this module runs with
    `auth.PASSWORD_ENV_VAR` set to `TEST_PASSWORD` — mirrors the legacy
    harness's own `main()` setup, which wrapped every check() call in
    exactly this env var assignment/restore.
    """
    monkeypatch.setenv(auth.PASSWORD_ENV_VAR, TEST_PASSWORD)


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
