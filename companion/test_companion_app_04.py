"""Tests the JS gate/motion budget style.css contracts, the login page
(Auth0 link only, no script, POST /login gone, deep-link return,
open-redirect rejection, the dedicated login_shell()), the document-language regression
guard, the six authenticated NAV_TABS headings, the retired /preview
route redirect, the /config 404, the unscoped and scope-rejected
/settings saves, the rebuilt Home page, the three /quick/* routes
(display, quiet-hours, led) including their return_to whitelist and
fetch/204 negotiation, the scoped Display/Device settings split, and
the Cache-Control/CSP headers on an authenticated response.

Every test that only reads (a GET, or a POST that is rejected before any
handler runs) shares one module-scoped, already-logged-in `app04_server`
— nothing in this module's own shared-server tests ever changes
persisted device config, gallery/illustration state or history, so the
Home-page and Display/Device-split checks always see the same fresh
install. Every test that actually WRITES device config, quick-toggle
flags gets
its own fresh, function-scoped server via `make_app_server` — never the
shared one.
"""
import re
import urllib.parse

import pytest

import companion.layout as layout
from companion.pages import config_page
from companion_app_server import (
    http_request, login, served_stylesheet)
from companion_markup import at_rule_blocks, css_rules, custom_properties
from server import device_config

import companion.app as app_module

# --- The motion budget's own pinned counts. ---------------------------
_EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 2
_EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS = 1

# The two motion durations, plus the one documented exception: the
# toast's two dwells (how long a success/info toast and a pending toast
# stay), which are waits, not movement speeds. Each may only drive its
# own armed toast timer hairline.
_MOTION_TOKENS = ("--motion-fast", "--motion-slow")
_MOTION_EXCEPTION_TOKENS = ("--motion-toast-dwell", "--motion-toast-dwell-long")
_MOTION_EXCEPTION_KEYFRAMES = "skypane-toast-dwell"
_MOTION_EXCEPTION_SELECTORS = {
    "--motion-toast-dwell": (".toast[data-toast-armed] .toast__timer",),
    "--motion-toast-dwell-long": (
        '.toast[data-toast-armed][data-toast-autohide="long"] .toast__timer',),
}

# The second documented exception: the period of the soft halo around
# Home's status dot. Only the dot halo rule may spend it.
_DOT_PULSE_TOKEN = "--motion-dot-pulse"
_DOT_PULSE_KEYFRAMES = "skypane-dot-halo"
_DOT_PULSE_SELECTOR = ".home-state__dot--pulse::after"

_ANIMATION_VALUE_KEYWORDS = frozenset((
    "var", "none", "infinite", "normal", "reverse", "alternate", "alternate-reverse",
    "forwards", "backwards", "both", "running", "paused", "auto",
    "linear", "ease", "ease-in", "ease-out", "ease-in-out",
    "step-start", "step-end", "steps", "cubic-bezier",
    "jump-start", "jump-end", "jump-none", "jump-both", "start", "end",
    "inherit", "initial", "unset", "revert", "revert-layer",
))


@pytest.fixture(scope="module")
def app04_server(module_app_server_factory):
    """One module-scoped `companion/app.py` server shared by every read-only check in this
    module — a GET, or a POST rejected before any handler mutates state (the two
    unauthenticated-POST-redirects-to-login checks below). No test in this module that
    persists a device-config/quick-toggle write ever uses this server; see the module
    docstring.
    """
    return module_app_server_factory(fake_providers=True)


@pytest.fixture(scope="module")
def served_css(app04_server):
    """The stylesheet `companion/app.py` actually serves."""
    return served_stylesheet(app04_server)


@pytest.fixture(scope="module")
def session_cookie(app04_server):
    """One shared login for every authenticated-but-read-only check below."""
    return login(app04_server)


# ==========================================================================
# style.css contracts: the .js gate class boundary, the motion budget
# ==========================================================================


def test_js_gate_class_resolves_to_a_real_selector_on_a_boundary(served_css):
    """layout.JS_GATE_CLASS resolves to a real selector in companion/static/style.css on a
    SELECTOR BOUNDARY — the class a page module writes and the rule that hides it pinned as one
    name, because a rename on either side alone renders a script-only affordance permanently
    with scripts blocked"""
    boundary = re.compile(r"\.%s(?![-\w])" % re.escape(layout.JS_GATE_CLASS))
    matched = any(
        boundary.search(selector)
        for rule in css_rules(served_css)
        for selector in rule.selectors
    )
    assert matched, (
        "layout.JS_GATE_CLASS is %r but companion/static/style.css declares no `.%s` selector "
        "on a boundary — the class a page module writes and the rule that hides it are two "
        "halves of one contract" % (layout.JS_GATE_CLASS, layout.JS_GATE_CLASS))


def test_style_css_honours_the_motion_budget(served_css):
    """companion/static/style.css honours the phase's motion budget: every @keyframes name is
    defined exactly once, every animation reference resolves to a block in the same file, every
    animation duration comes from a var(--motion-*) token rather than a bare literal, the live
    prefers-reduced-motion reduce/no-preference block counts equal
    EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS/EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, and
    neither interpolate-size nor calc-size() appears — all measured on COMMENT-STRIPPED source,
    because this stylesheet's comments quote every token the check counts Measured over the parsed served stylesheet (`at_rule_blocks()` for the block counts,
    `css_rules()` for the declarations), so a comment quoting a token never counts.
    """
    blocks = at_rule_blocks(served_css)

    names = [block[len("@keyframes"):].strip() for block in blocks
             if block.startswith("@keyframes ")]
    seen = []
    for name in names:
        assert name not in seen, (
            "@keyframes %r is defined %d times in the served stylesheet — the motion budget is "
            "ONE shared definition per animation" % (name, names.count(name)))
        seen.append(name)

    reduce_blocks = [block for block in blocks if block.startswith("@media")
                     and re.search(r"prefers-reduced-motion\s*:\s*reduce", block)]
    assert len(reduce_blocks) == _EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS, (
        "the served stylesheet carries %d live `@media (prefers-reduced-motion: reduce)` "
        "block(s), expected %d" % (len(reduce_blocks), _EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS))
    no_pref_blocks = [block for block in blocks if block.startswith("@media")
                      and re.search(r"prefers-reduced-motion\s*:\s*no-preference", block)]
    assert len(no_pref_blocks) == _EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, (
        "the served stylesheet carries %d live `@media (prefers-reduced-motion: "
        "no-preference)` wrapper(s), expected %d"
        % (len(no_pref_blocks), _EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS))

    live_rules = [rule for rule in css_rules(served_css)
                  if not any("prefers-reduced-motion" in at_rule for at_rule in rule.at_rules)]
    for rule in live_rules:
        for prop, value in rule.declarations:
            if prop in ("animation", "animation-name"):
                idents = [
                    ident for ident in re.findall(r"(?<![\w-])(-?[A-Za-z_][\w-]*)", value)
                    if ident.lower() not in _ANIMATION_VALUE_KEYWORDS
                ]
                for ident in idents:
                    assert ident in names, (
                        "`%s: %s` names %r, which no @keyframes block in the served stylesheet "
                        "defines" % (prop, value, ident))
                assert idents, "`%s: %s` resolves to no keyframes name at all" % (prop, value)
            if prop in ("animation", "animation-duration"):
                literal = re.search(r"(?<![\w-])\d+(?:\.\d+)?m?s(?![\w-])", value)
                assert not literal and "var(--motion-" in value, (
                    "`%s: %s` takes its duration from %s — every animation duration must come "
                    "from var(--motion-fast) or var(--motion-slow)"
                    % (prop, value,
                       ("the bare literal %r" % literal.group(0)) if literal else "no --motion-* token"))
            for banned in ("interpolate-size", "calc-size("):
                assert banned not in prop and banned not in value, (
                    "the served stylesheet declares %r in %r — Chromium-only and Baseline "
                    "limited, use grid-template-rows: 0fr -> 1fr instead" % (banned, rule.selectors))


def _spenders(served_css, token):
    return [
        (rule.selectors, prop, value)
        for rule in css_rules(served_css)
        for prop, value in rule.declarations
        if "var(%s)" % token in value and not prop.startswith("--")
    ]


def test_motion_tokens_are_two_durations_plus_the_documented_exceptions(served_css):
    """the served :root declares exactly --motion-fast, --motion-slow and the documented
    exceptions (the two toast dwells and the status dot pulse); each exception is spent by
    exactly one live declaration (an armed toast timer hairline's skypane-toast-dwell
    animation, the status dot halo's skypane-dot-halo animation) and nowhere else, not even a
    transition, so none can become a general-purpose motion speed"""
    root = custom_properties(served_css, ":root")
    declared = sorted(name for name in root if name.startswith("--motion-"))
    assert declared == sorted(
        _MOTION_TOKENS + _MOTION_EXCEPTION_TOKENS + (_DOT_PULSE_TOKEN,)), (
        "expected the motion budget's two tokens plus the documented exceptions, got %r"
        % (declared,))
    expected = [
        (token, _MOTION_EXCEPTION_SELECTORS[token], _MOTION_EXCEPTION_KEYFRAMES)
        for token in _MOTION_EXCEPTION_TOKENS
    ] + [(_DOT_PULSE_TOKEN, (_DOT_PULSE_SELECTOR,), _DOT_PULSE_KEYFRAMES)]
    for token, selectors_expected, keyframes in expected:
        spenders = _spenders(served_css, token)
        assert len(spenders) == 1, (
            "expected exactly one declaration spending %s, got %r" % (token, spenders))
        selectors, prop, value = spenders[0]
        assert selectors == selectors_expected, (
            "expected only %r to spend %s, got %r" % (selectors_expected, token, selectors))
        assert prop == "animation" and keyframes in value, (
            "expected %s to drive the %s animation, got `%s: %s`"
            % (token, keyframes, prop, value))


# ==========================================================================
# login page: Auth0 link only, no script, no password control, POST gone
# ==========================================================================


def test_login_card_script_is_gone(app04_server):
    """the retired password-card script is no longer served"""
    status, _headers, _body = http_request(app04_server.base_url() + "/static/login-card.js")
    assert status == 404, "expected 404, got %d" % status


def test_login_page_emits_no_script_tag(app04_server):
    """a rendered login page carries no <script> at all, no inline script and no nonce"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert "<script" not in text, "the login page must carry no script"
    assert "unsafe-inline" not in text and "nonce-" not in text, (
        "no nonce or unsafe-inline may appear on the login page")


def test_login_post_is_not_a_route(app04_server):
    """POST /login answers 404 or 405, sets no cookie, and renders no password error"""
    status, headers, body = http_request(
        app04_server.base_url() + "/login", method="POST", data=b"password=anything",
        extra_headers={"Origin": app04_server.base_url()})
    assert status in (404, 405), "expected 404/405, got %d" % status
    assert "Set-Cookie" not in headers, "expected no Set-Cookie header"
    assert b"Incorrect password" not in body


def test_deep_link_return_is_carried_into_the_sign_in_link(make_app_server):
    """an unauthenticated GET /health redirects with ?next=%2Fhealth, and the login page
    carries that destination on the Auth0 start link"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    status, headers, _ = http_request(base + "/health")
    assert status == 303, "expected 303 for GET /health, got %d" % status
    assert headers.get("Location") == "/login?next=%2Fhealth", (
        "expected Location /login?next=%%2Fhealth, got %r" % headers.get("Location"))
    status, _headers, body = http_request(base + "/login?next=%2Fhealth")
    assert status == 200
    assert b'href="/login/auth0?next=/health"' in body


@pytest.mark.parametrize("crafted_next", ["https://evil.example", "//evil.example"])
def test_open_redirect_is_not_carried_into_the_sign_in_link(make_app_server, crafted_next):
    """a crafted next value never reaches the sign-in link"""
    server = make_app_server(fake_providers=True)
    status, _headers, body = http_request(
        server.base_url() + "/login?next=" + urllib.parse.quote(crafted_next, safe=""))
    assert status == 200
    assert b"evil.example" not in body
    assert b'href="/login/auth0"' in body


def test_login_get_with_unrecognised_next_leaves_the_link_bare(app04_server):
    """GET /login?next=/no-such-route (not a real NAV_TABS member) renders the plain link"""
    # /no-such-route is not a real NAV_TABS member, so it exercises the same
    # unrecognised-value branch as any other, without being a literal a production
    # os.makedirs() path could ever mistake for a real directory to create.
    status, _headers, body = http_request(
        app04_server.base_url() + "/login?next=/no-such-route")
    assert status == 200, "expected 200, got %d" % status
    assert b'href="/login/auth0"' in body, (
        "an unrecognised ?next= value must be dropped before it reaches the sign-in link")


def test_login_page_uses_dedicated_login_shell(app04_server):
    """GET /login (no session) is rendered by the dedicated login_shell(), not page_shell() —
    no sidebar/mobile-nav markup, no password control"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert '<html lang="en"' in text, "expected <html lang=\"en\" in the login page"
    assert 'type="password"' not in text, "the login page must offer no password control"
    for absent in ("sidebar-nav", "dashboard-shell", "site-nav-toggle"):
        assert absent not in text, (
            "the login page must render layout.login_shell(), not page_shell() — found %r in "
            "the response body" % absent)


def test_login_clean_render_is_the_wordmark_and_the_sign_in_link(app04_server):
    """GET /login renders a bare page-title wordmark, one decorative inline brand mark, no
    sprite, and the sign-in link as the card's only control"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert "aria-invalid" not in text and "aria-describedby" not in text
    assert '<h1 class="page-title">SkyPane</h1>' in text, (
        "expected the page-title wordmark to stay live text")
    assert text.count("<svg") == 1 and 'class="logo-mark"' in text and 'aria-hidden="true"' in text, (
        "the login card carries exactly one decorative inline brand mark")
    assert "icon-defs" not in text and "<use" not in text, "no sprite on the login page"
    assert "<input" not in text and "<button" not in text
    assert text.count('class="login-signin"') == 1


def test_both_shells_agree_on_document_language():
    """page_shell() and login_shell() both emit lang="en" """
    page_doc = layout.page_shell(title="Config", active="config", body="<p>x</p>")
    login_doc = layout.login_shell("<p>x</p>")
    assert 'lang="en"' in page_doc, "expected lang=\"en\" in page_shell()'s output"
    assert 'lang="en"' in login_doc, "expected lang=\"en\" in login_shell()'s output"


# ==========================================================================
# authenticated: every NAV_TABS tab, the retired /preview / legacy-route
# redirects, the /config 404, the unscoped/scope-rejected settings saves
# ==========================================================================


@pytest.mark.parametrize(
    "tab_path,heading",
    [("/", "Home"), ("/display", "Display"), ("/flights", "Flights"),
     ("/airlines", "Airlines"), ("/health", "Health"), ("/device", "Device")])
def test_authenticated_tab_returns_200_with_its_own_heading(app04_server, session_cookie, tab_path, heading):
    """authenticated GET %s returns 200 and contains its own %r heading"""
    status, _headers, body = http_request(
        app04_server.base_url() + tab_path, cookie=session_cookie)
    assert status == 200, "expected 200, got %d" % status
    assert heading.encode() in body, "expected the %r heading in the response body" % heading


def test_preview_redirects_to_flights(app04_server, session_cookie):
    """authenticated GET /preview (the retired Preview page route) redirects to /flights"""
    status, headers, body = http_request(
        app04_server.base_url() + "/preview", cookie=session_cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert headers.get("Location") == "/flights", (
        "expected a redirect to /flights exactly, got %r" % headers.get("Location"))
    assert not body, "expected an empty redirect body, got %d bytes of content" % len(body)


@pytest.mark.parametrize("legacy,target", [("/settings", "/display"), ("/history", "/flights")])
def test_legacy_page_route_redirects_with_a_fixed_literal_target(app04_server, session_cookie, legacy, target):
    """authenticated GET %s (a pre-phase-18 page route) redirects to %s with a fixed literal
    target"""
    status, headers, body = http_request(
        app04_server.base_url() + legacy, cookie=session_cookie)
    assert status == 303, "expected a 303 redirect for %s, got %d" % (legacy, status)
    assert headers.get("Location") == target, (
        "expected %s to redirect to %s exactly, got %r" % (legacy, target, headers.get("Location")))
    assert not body, "expected an empty redirect body"


def test_preview_redirect_ignores_query_string(app04_server, session_cookie):
    """authenticated GET /preview carrying an arbitrary query string (including a next=-shaped
    and an https://evil.example-shaped value) still redirects to the identical /flights location
    — no request value influences the target"""
    status, headers, _body = http_request(
        app04_server.base_url() + "/preview?next=/settings&evil=https://evil.example",
        cookie=session_cookie)
    assert status == 303, "expected a 303 redirect, got %d" % status
    assert headers.get("Location") == "/flights", (
        "expected the redirect location to stay /flights regardless of an arbitrary query "
        "string, got %r" % headers.get("Location"))


def test_old_settings_path_404s_authenticated(app04_server, session_cookie):
    """authenticated GET /config (the retired settings path) returns 404 — declines a
    redirect since this is a fresh URL at inception, not a deprecated bookmark"""
    status, _headers, body = http_request(
        app04_server.base_url() + "/config", cookie=session_cookie)
    assert status == 404, "expected 404 for the retired /config path, got %d" % status
    assert b"Page not found." in body, "expected the exact 404 copy in the response body"


def test_settings_post_redirects_to_display_with_flash(make_app_server):
    """an authenticated POST /settings redirects to /display (the default return page) carrying
    a flash query"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    status, headers, _ = http_request(
        server.base_url() + "/settings", method="POST", cookie=session_cookie, data=b"")
    assert status == 303, "expected a 303 redirect, got %d" % status
    location = headers.get("Location", "")
    assert location.startswith("/display?flash="), (
        "expected a redirect to /display?flash=..., got %r" % location)


def test_rejected_settings_save_rerenders_200_with_input_and_error_persists_nothing(make_app_server):
    """a POST /settings with a valid theme change and an empty quiet_hours_start returns 200,
    shows the newly-picked theme still selected, shows the quiet-hours field error, carries no
    flash banner, and persists nothing on disk"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    before = device_config.load_device_config(server.state_dir)
    status, headers, body = http_request(
        server.base_url() + "/settings", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({
            "scope": "display", "return_to": "/display",
            "theme": "black", "tracked_runway": before["tracked_runway"],
            "quiet_hours_start": "",
        }).encode())
    assert status == 200, "expected a 200 re-render on a rejected save, got %d" % status
    assert not headers.get("Location"), (
        "expected no redirect Location header on a rejected save, got %r" % headers.get("Location"))
    body_text = body.decode("utf-8", errors="replace")
    assert 'name="theme" value="black"' in body_text and "checked" in body_text.split(
        'name="theme" value="black"', 1)[1].split(">", 1)[0], (
        "expected the just-picked theme (black) to render checked - nothing discarded")
    assert config_page.ERROR_QUIET_HOURS_TIME_SHAPE in body_text, (
        "expected the quiet_hours_start field-level error message in the response body")
    assert "toast-region--flash" not in body_text, (
        "expected no top-of-page flash toast on a field-level rejection (D-07)")
    after = device_config.load_device_config(server.state_dir)
    assert after == before, "expected nothing to be persisted on a rejected save, got %r (was %r)" % (after, before)


# ==========================================================================
# Home page, quick actions, scoped settings saves.
# ==========================================================================


def test_home_page_renders_widgets(app04_server, session_cookie):
    """authenticated GET / renders the approved frame-signal-first Home page:
    its current image precedes recent flights, then ONE merged frame-state card carrying the
    screen and quiet-hours POST controls, and one compact battery fact, while retired
    configuration, healthy diagnostics, and activity-band dashboard material stay absent."""
    status, _headers, body = http_request(app04_server.base_url() + "/", cookie=session_cookie)
    assert status == 200, "expected 200 for GET /, got %d" % status
    text = body.decode("utf-8", errors="replace")
    for needle in (
            '<h1 class="page-title">Home</h1>',
            'class="home-columns home-picture-row home-signal-grid"',
            'id="home-current-frame"',
            "Recent flights", 'href="/flights"',
            'class="home-battery ',
            'class="nav-group nav-group--advanced"',
            'aria-labelledby="home-frame-state"',
            'action="%s"' % app_module.QUICK_DISPLAY_ROUTE,
            'action="%s"' % app_module.QUICK_QUIET_HOURS_ROUTE,
            "data-loaded-at="):
        assert needle in text, "expected %r in the Home page" % needle
    assert text.count("Frame state") == 1, "expected exactly one merged frame-state card"
    assert 'class="preview-frame"' in text or "Nothing rendered yet." in text, (
        "expected either the preview-frame figure or its empty state on Home")
    for absent in (
            "Your frame at a glance.", "Quick actions", "On the frame now",
            "status-card__rows", "home-hero", 'class="frame-strip',
            'class="dashboard-grid home-status-grid"', 'class="day-band',
            'action="/poll-now"'):
        assert absent not in text, (
            "expected %r to be absent from the rebuilt Home page (D-04)" % absent)


def test_quick_display_toggle_round_trip(make_app_server):
    """POST /quick/display with state=off then state=on flips display_enabled on disk and
    redirects to Display with the matching flash; a crafted state value redirects with
    quick_failed and writes nothing"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    for state, expected_flash, expected_value in (
            ("off", app_module.FLASH_KEY_DISPLAY_OFF, False),
            ("on", app_module.FLASH_KEY_DISPLAY_ON, True)):
        status, headers, _ = http_request(
            server.base_url() + app_module.QUICK_DISPLAY_ROUTE, method="POST",
            cookie=session_cookie, data=urllib.parse.urlencode({"state": state}).encode())
        assert status == 303, "expected 303 for state=%s, got %d" % (state, status)
        assert headers.get("Location") == "/display?flash=%s" % expected_flash, (
            "expected a redirect to /display?flash=%s, got %r"
            % (expected_flash, headers.get("Location")))
        on_disk = device_config.load_device_config(server.state_dir)
        assert on_disk["display_enabled"] is expected_value, (
            "expected display_enabled %r on disk after state=%s, got %r"
            % (expected_value, state, on_disk["display_enabled"]))
    status, headers, _ = http_request(
        server.base_url() + app_module.QUICK_DISPLAY_ROUTE, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "toggle"}).encode())
    assert status == 303 and headers.get("Location") == "/display?flash=%s" % app_module.FLASH_KEY_QUICK_FAILED, (
        "expected a crafted state value to redirect with the quick_failed flash, got %d/%r"
        % (status, headers.get("Location")))
    assert device_config.load_device_config(server.state_dir)["display_enabled"] is True, (
        "expected a rejected quick action to leave display_enabled untouched")


def test_quick_quiet_hours_toggle_round_trip(make_app_server):
    """POST /quick/quiet-hours with state=on then state=off flips quiet_hours_enabled on disk,
    redirects to Display with the matching flash, and never touches display_enabled"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    status, headers, _ = http_request(
        server.base_url() + app_module.QUICK_QUIET_HOURS_ROUTE, method="POST",
        cookie=session_cookie, data=urllib.parse.urlencode({"state": "on"}).encode())
    assert status == 303 and headers.get("Location") == "/display?flash=%s" % app_module.FLASH_KEY_QUIET_ON, (
        "expected a redirect to /display?flash=quiet_on, got %d/%r" % (status, headers.get("Location")))
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["quiet_hours_enabled"] is True, "expected quiet_hours_enabled True on disk"
    assert on_disk["display_enabled"] is True, (
        "expected the quiet-hours toggle to carry display_enabled forward untouched")
    status, headers, _ = http_request(
        server.base_url() + app_module.QUICK_QUIET_HOURS_ROUTE, method="POST",
        cookie=session_cookie, data=urllib.parse.urlencode({"state": "off"}).encode())
    assert headers.get("Location") == "/display?flash=%s" % app_module.FLASH_KEY_QUIET_OFF, (
        "expected a redirect to /display?flash=quiet_off, got %r" % headers.get("Location"))
    assert device_config.load_device_config(server.state_dir)["quiet_hours_enabled"] is False, (
        "expected quiet_hours_enabled False on disk")


def _quick_toggle_return_to_check(server, session_cookie, route, flash_key):
    """ Task 1 : return_to=/ redirects to Home, return_to=/display
    redirects to Display, and a hostile/absent value falls back to Display — never
    string-prefix-matched, never parsed as a URL. Shared by both /quick/display and
    /quick/quiet-hours below, so the two forms' whitelist-then-fallback contract can never
    silently diverge.
    """
    base = server.base_url()
    for return_to, expected_location in (
            ("/", "/?flash=%s" % flash_key),
            ("/display", "/display?flash=%s" % flash_key),
            ("https://evil.example/", "/display?flash=%s" % flash_key),
            ("//evil.example", "/display?flash=%s" % flash_key),
            ("/flights", "/display?flash=%s" % flash_key)):
        status, headers, _ = http_request(
            base + route, method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode({"state": "on", "return_to": return_to}).encode())
        assert status == 303 and headers.get("Location") == expected_location, (
            "return_to=%r: expected 303 to %r, got %d/%r"
            % (return_to, expected_location, status, headers.get("Location")))
    status, headers, _ = http_request(
        base + route, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "off"}).encode())
    expected_off_flash = (
        app_module.FLASH_KEY_DISPLAY_OFF if route == app_module.QUICK_DISPLAY_ROUTE
        else app_module.FLASH_KEY_QUIET_OFF)
    assert status == 303 and headers.get("Location") == "/display?flash=%s" % expected_off_flash, (
        "expected an absent return_to to fall back to Display")
    status, headers, _ = http_request(
        base + route, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "toggle", "return_to": "/"}).encode())
    assert status == 303 and headers.get("Location") == "/?flash=%s" % app_module.FLASH_KEY_QUICK_FAILED, (
        "expected the invalid-state early return to honour return_to=/, got %d/%r"
        % (status, headers.get("Location")))


def test_quick_display_honours_return_to(make_app_server):
    """POST /quick/display honours return_to (/ or /display), falls back to Display for a
    hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the
    invalid-state early return honours return_to too"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    _quick_toggle_return_to_check(
        server, session_cookie, app_module.QUICK_DISPLAY_ROUTE, app_module.FLASH_KEY_DISPLAY_ON)


def test_quick_quiet_hours_honours_return_to(make_app_server):
    """POST /quick/quiet-hours honours return_to (/ or /display), falls back to Display for a
    hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the
    invalid-state early return honours return_to too"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    _quick_toggle_return_to_check(
        server, session_cookie, app_module.QUICK_QUIET_HOURS_ROUTE, app_module.FLASH_KEY_QUIET_ON)


def test_quick_routes_answer_204_for_a_fetch_and_303_for_a_form(make_app_server):
    """POST /quick/display and POST /quick/quiet-hours answer a form post with exactly today's
    303-and-flash and a request carrying the fetch header with a 204, empty body and no Location
    — the same write either way, and a crafted state value is never a 204"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    base = server.base_url()
    for route, state, field, expected_value, flash_key in (
            (app_module.QUICK_DISPLAY_ROUTE, "off", "display_enabled", False,
             app_module.FLASH_KEY_DISPLAY_OFF),
            (app_module.QUICK_QUIET_HOURS_ROUTE, "on", "quiet_hours_enabled", True,
             app_module.FLASH_KEY_QUIET_ON)):
        status, headers, body = http_request(
            base + route, method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode({"state": state, "return_to": "/"}).encode())
        assert status == 303 and headers.get("Location") == "/?flash=%s" % flash_key, (
            "%s: a form POST must still answer 303 to /?flash=%s, got %d/%r"
            % (route, flash_key, status, headers.get("Location")))
        assert device_config.load_device_config(server.state_dir)[field] is expected_value, (
            "%s: expected %s %r on disk after the form post" % (route, field, expected_value))
        status, headers, body = http_request(
            base + route, method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode(
                {"state": "on" if state == "off" else "off", "return_to": "/"}).encode(),
            extra_headers={"X-Requested-With": app_module.QUICK_FETCH_HEADER_VALUE})
        assert status == 204, (
            "%s: a POST identifying itself as a fetch must answer 204, got %d" % (route, status))
        assert not body, "%s: expected an empty 204 body, got %r" % (route, body[:120])
        assert not headers.get("Location"), (
            "%s: a 204 must carry no Location — fetch() follows a same-origin redirect silently "
            "by default, and a redirect read as success is the expired-session hole freshness.js "
            "already documents" % route)
        assert device_config.load_device_config(server.state_dir)[field] is not expected_value, (
            "%s: the 204 branch must still SAVE — content negotiation picks the response shape, "
            "never whether the write happens" % route)
        status, headers, _ = http_request(
            base + route, method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode({"state": "toggle", "return_to": "/"}).encode(),
            extra_headers={"X-Requested-With": app_module.QUICK_FETCH_HEADER_VALUE})
        assert status != 204, (
            "%s: a crafted state value must never answer 204 — the client reads 204 as "
            "confirmation and would leave the switch showing a state the frame is not in" % route)


def test_quick_led_route_saves_redirects_and_negotiates(make_app_server):
    """POST /quick/led stores one explicit led_enabled keyword and carries every other flag
    forward, redirects to /device with its own flash for a form post, answers 204 with an empty
    body for a fetch, redirects with the generic failure flash and writes nothing for a crafted
    state, falls back to /device for every non-member return_to, and is not reachable by GET at
    all"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    base = server.base_url()
    device_config.save_device_config(
        server.state_dir, led_enabled=True, display_enabled=True, quiet_hours_enabled=True)

    status, headers, _ = http_request(
        base + app_module.QUICK_LED_ROUTE, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "off", "return_to": "/device"}).encode())
    assert status == 303 and headers.get("Location") == "/device?flash=%s" % app_module.FLASH_KEY_LED_OFF, (
        "expected a 303 to /device?flash=led_off, got %d/%r" % (status, headers.get("Location")))
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["led_enabled"] is False, "expected led_enabled False on disk, got %r" % (on_disk["led_enabled"],)
    assert on_disk["display_enabled"] is True and on_disk["quiet_hours_enabled"] is True, (
        "expected /quick/led to carry every other flag forward untouched, got %r" % (on_disk,))

    status, headers, body = http_request(
        base + app_module.QUICK_LED_ROUTE, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "on", "return_to": "/device"}).encode(),
        extra_headers={"X-Requested-With": app_module.QUICK_FETCH_HEADER_VALUE})
    assert status == 204 and not body and not headers.get("Location"), (
        "expected an empty 204 with no Location for the fetch shape, got %d/%r/%r"
        % (status, body[:80], headers.get("Location")))
    assert device_config.load_device_config(server.state_dir)["led_enabled"] is True, (
        "expected the 204 branch to still save led_enabled True")

    status, headers, _ = http_request(
        base + app_module.QUICK_LED_ROUTE, method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({"state": "toggle", "return_to": "/device"}).encode())
    assert status == 303 and headers.get("Location") == "/device?flash=%s" % app_module.FLASH_KEY_QUICK_FAILED, (
        "expected a crafted state value to redirect with the generic quick_failed flash, got "
        "%d/%r" % (status, headers.get("Location")))
    assert device_config.load_device_config(server.state_dir)["led_enabled"] is True, (
        "expected a rejected quick action to write nothing")

    for hostile in ("https://evil.example/", "//evil.example", "/flights",
                    "/device/../flights", "/", "/display"):
        status, headers, _ = http_request(
            base + app_module.QUICK_LED_ROUTE, method="POST", cookie=session_cookie,
            data=urllib.parse.urlencode({"state": "on", "return_to": hostile}).encode())
        assert status == 303 and headers.get("Location") == "/device?flash=%s" % app_module.FLASH_KEY_LED_ON, (
            "return_to=%r: expected a fall back to /device, got %d/%r"
            % (hostile, status, headers.get("Location")))

    device_config.save_device_config(server.state_dir, led_enabled=False)
    status, _headers, _body = http_request(
        base + app_module.QUICK_LED_ROUTE + "?state=on", cookie=session_cookie)
    assert status == 404, "expected GET /quick/led to 404, got %d" % status
    assert device_config.load_device_config(server.state_dir)["led_enabled"] is False, (
        "a GET must never write")


def test_unauth_post_quick_led_redirects_to_login(app04_server):
    """unauthenticated POST /quick/led redirects to /login without page content"""
    status, headers, body = http_request(
        app04_server.base_url() + app_module.QUICK_LED_ROUTE, method="POST",
        data=b"state=off")
    assert status == 303, "expected 303, got %d" % status
    assert headers.get("Location") == "/login", (
        "expected a redirect to /login, got %r" % headers.get("Location"))
    assert not body, "expected an empty redirect body, got %d bytes of content" % len(body)


def test_unauth_post_quick_display_redirects_to_login(app04_server):
    """unauthenticated POST /quick/display redirects to /login without page content"""
    status, headers, body = http_request(
        app04_server.base_url() + app_module.QUICK_DISPLAY_ROUTE, method="POST",
        data=b"state=off")
    assert status == 303, "expected 303, got %d" % status
    assert headers.get("Location") == "/login", (
        "expected a redirect to /login, got %r" % headers.get("Location"))
    assert not body, "expected an empty redirect body, got %d bytes of content" % len(body)


def test_scoped_settings_save_carries_other_page_forward(make_app_server):
    """a scoped POST /settings (scope=display / scope=device) persists only its own page's
    groups, carries the other page's checkbox state forward instead of flipping it off,
    redirects to the page it came from, and never honours a crafted return_to"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    base = server.base_url()

    status, _headers, _ = http_request(
        base + "/settings", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({
            "theme": "white", "tracked_runway": "3", "led_enabled": "on",
            "display_enabled": "on"}).encode())
    assert status == 303, "expected 303 on the full save, got %d" % status

    status, headers, _ = http_request(
        base + "/settings", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({
            "scope": "display", "return_to": "/display",
            "theme": "black", "display_enabled": "on"}).encode())
    assert status == 303 and headers.get("Location") == "/display?flash=saved", (
        "expected a 303 to /display?flash=saved, got %d/%r" % (status, headers.get("Location")))
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["theme"] == "black", "expected the Display-page save to persist theme=black"
    assert on_disk["led_enabled"] is True, (
        "expected a Display-page save to leave led_enabled True (out of scope), got %r"
        % (on_disk["led_enabled"],))

    status, headers, _ = http_request(
        base + "/settings", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({
            "scope": "device", "return_to": "/device", "tracked_runway": "06-24"}).encode())
    assert status == 303 and headers.get("Location") == "/device?flash=saved", (
        "expected a 303 to /device?flash=saved, got %d/%r" % (status, headers.get("Location")))
    on_disk = device_config.load_device_config(server.state_dir)
    assert on_disk["tracked_runway"] == "06-24", (
        "expected the Device-page save to persist tracked_runway=06-24")
    assert on_disk["display_enabled"] is True, (
        "expected a Device-page save to leave display_enabled True (out of scope)")
    assert on_disk["led_enabled"] is True, (
        "expected a Device-page save that names no led_enabled to LEAVE it True, got %r — an "
        "unrelated save must never switch the diagnostic LED off (D-12.1, T-23-25)"
        % (on_disk["led_enabled"],))
    assert on_disk["theme"] == "black", "expected the Device-page save to leave the theme untouched"

    status, headers, _ = http_request(
        base + "/settings", method="POST", cookie=session_cookie,
        data=urllib.parse.urlencode({
            "scope": "display", "return_to": "https://evil.example", "theme": "white"}).encode())
    assert headers.get("Location") == "/display?flash=saved", (
        "expected a crafted return_to to fall back to /display, got %r" % headers.get("Location"))


def test_display_and_device_pages_split_the_groups(app04_server, session_cookie):
    """GET /display and GET /device split the settings groups per companion/screens.py each carrying its hidden
    scope/return_to fields; Refresh now lives on Device only."""
    base = app04_server.base_url()
    _s, _h, display_body = http_request(base + "/display", cookie=session_cookie)
    _s, _h, device_body = http_request(base + "/device", cookie=session_cookie)
    display_text = display_body.decode("utf-8", errors="replace")
    device_text = device_body.decode("utf-8", errors="replace")
    assert 'name="theme"' in display_text and 'name="quiet_hours_start"' in display_text, (
        "expected the Display page to carry the theme and quiet-hours schedule groups")
    assert 'name="quiet_hours_enabled"' not in display_text and 'name="display_enabled"' not in display_text, (
        "expected no quiet_hours_enabled/display_enabled checkbox on the Display page")
    assert 'name="tracked_runway"' in display_text, (
        "expected the Display page to carry the runway group (moved from Device, 20-07/D-10)")
    assert 'name="led_enabled"' not in display_text, (
        "expected the Display page NOT to carry the LED group")
    assert 'name="tracked_runway"' not in device_text, (
        "expected the Device page NOT to carry the runway group (moved to Display, 20-07/D-10)")
    assert 'name="wake_interval_s"' in device_text, (
        "expected the Device page to carry the wake-interval group")
    theme_probe = device_text.replace('name="theme_id"', "")
    if 'name="theme" ' in theme_probe or 'name="theme">' in theme_probe:
        pytest.fail("expected the Device page NOT to carry the theme chip grid")
    for text, scope, route in ((display_text, "display", "/display"), (device_text, "device", "/device")):
        assert '<input type="hidden" name="scope" value="%s">' % scope in text, (
            "expected the %s page to carry its hidden scope field" % scope)
        assert '<input type="hidden" name="return_to" value="%s">' % route in text, (
            "expected the %s page to carry its hidden return_to field" % scope)
        assert "Screen: Plane frame" not in text, (
            "expected the retired screen-type caption to stay off the %s page" % scope)
    assert "Refresh now" not in device_text, "expected the Device page to carry no Refresh now action"
    rules_panel_marker = 'data-look-usage="rules"'
    assert rules_panel_marker not in device_text, (
        "expected the Device page NOT to carry the rules editor (moved to Display, 20-07/D-10)")
    assert rules_panel_marker in display_text, (
        "expected the Display page to carry the rules editor (moved from Device, 20-07/D-10)")
    assert "Manual refresh" not in display_text, (
        "expected the Display page NOT to carry Manual refresh")


def test_html_pages_are_no_store(app04_server, session_cookie):
    """every HTML response (an authenticated page and the login page alike) carries
    Cache-Control: no-store, so the back button and shared caches never replay a page after
    sign-out"""
    status, headers, _ = http_request(app04_server.base_url() + "/", cookie=session_cookie)
    assert status == 200, "expected 200, got %d" % status
    assert headers.get("Cache-Control") == "no-store", (
        "expected Cache-Control: no-store on an authenticated HTML page, got %r"
        % headers.get("Cache-Control"))
    _status, headers, _ = http_request(app04_server.base_url() + "/login")
    assert headers.get("Cache-Control") == "no-store", (
        "expected Cache-Control: no-store on the login page, got %r" % headers.get("Cache-Control"))


def test_authenticated_html_carries_exact_csp(app04_server, session_cookie):
    """an authenticated HTML response carries a Content-Security-Policy header equal (string
    equality, not substring) to companion.app.CONTENT_SECURITY_POLICY"""
    status, headers, _ = http_request(app04_server.base_url() + "/", cookie=session_cookie)
    assert status == 200, "expected 200, got %d" % status
    csp = headers.get("Content-Security-Policy")
    assert csp == app_module.CONTENT_SECURITY_POLICY, (
        "expected the CSP header to equal companion.app.CONTENT_SECURITY_POLICY exactly, got "
        "%r vs %r" % (csp, app_module.CONTENT_SECURITY_POLICY))


def test_csp_script_src_strict_no_unsafe_inline():
    """the CSP's script-src directive is 'self' with no 'unsafe-inline' anywhere in it (Task 1
    removed the app's last two inline <script> elements, so no exception is needed)"""
    csp = app_module.CONTENT_SECURITY_POLICY
    assert "script-src 'self'" in csp, "expected script-src 'self' in the CSP, got %r" % csp
    assert "script-src 'self' 'unsafe-inline'" not in csp, (
        "expected script-src to NOT carry 'unsafe-inline', got %r" % csp)
