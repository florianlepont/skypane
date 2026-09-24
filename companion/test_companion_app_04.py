"""Part 04a of the `companion/test_companion_app.py` migration chain
(33-17-PLAN.md): ledger rows 178-222 (fragment `33-ledger/companion__
test_companion_app.md`) — the JS gate/motion budget style.css contracts,
login-card.js's public-route/ES5/route-agreement/no-inline-script/reveal-
toggle checks, the login POST/GET flows (wrong password, right password,
deep-link return, open-redirect rejection, the renamed no-such-route
next value, the dedicated login_shell(), the clean/error/lockout card
renders), the document-language regression guard, the six authenticated
NAV_TABS headings, the retired /preview / legacy-route redirects, the
/config 404, the unscoped and scope-rejected /settings saves, the
rebuilt Home page, the three /quick/* routes (display, quiet-hours, led)
including their return_to whitelist and fetch/204 negotiation, the
scoped Display/Device settings split, and the Cache-Control/CSP headers
on an authenticated response.

`companion/test_companion_app_04b.py` continues from ledger row 223
(the redirect hardening headers) through row 266 (the LAST anchor, the
real-PNG illustration upload round trip).

Renamed from the original slice (33-MIGRATION-RULES.md section 0/2): the
GET /login?next=<unrecognised-route> check below now uses next=/no-such-
route — same behaviour (neither is a real NAV_TABS member, so both take
the "no hidden next field" branch), never a literal string a
`os.makedirs` production code path could turn into a real directory
create attempt.

Every test that only reads (a GET, or a POST that is rejected before any
handler runs) shares one module-scoped, already-logged-in `app04_server`
— nothing in this module's own shared-server tests ever changes
persisted device config, gallery/illustration state or history, so the
Home-page and Display/Device-split checks always see the same fresh
install their original harness saw at that point in its run. Every test
that actually WRITES device config, quick-toggle flags, or drives the
process-global login throttle to a lockout gets its own fresh,
function-scoped server via `make_app_server` (33-MIGRATION-RULES.md
section 2's POST-implies-function-scoped rule) — never the shared one.
"""
import re
import urllib.parse

import pytest

import companion.i18n as i18n_module
import companion.layout as layout
from companion import auth
from companion.pages import config_page
from companion_app_server import (
    TEST_PASSWORD, http_request, login, served_asset, served_stylesheet)
from companion_markup import css_rules, rules_with_selector
from server import device_config

import companion.app as app_module

# --- 23-01-PLAN.md Task 2 (D3/CFG-32): the motion budget's own pinned
# counts, ported verbatim from the legacy harness (row 179) — see
# companion/test_companion_app.py's own historical comment for why each
# number is what it is; that reasoning is plan history, not behaviour,
# and is not repeated here.
_EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 2
_EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS = 1

_ANIMATION_VALUE_KEYWORDS = frozenset((
    "var", "none", "infinite", "normal", "reverse", "alternate", "alternate-reverse",
    "forwards", "backwards", "both", "running", "paused", "auto",
    "linear", "ease", "ease-in", "ease-out", "ease-in-out",
    "step-start", "step-end", "steps", "cubic-bezier",
    "jump-start", "jump-end", "jump-none", "jump-both", "start", "end",
    "inherit", "initial", "unset", "revert", "revert-layer",
))


def _without_reduced_motion_blocks(css_source):
    """`css_source` with every `@media (prefers-reduced-motion: ...)`
    block (query and body) removed, by brace matching rather than by
    regex. F-01-sanctioned exception (33-16-SUMMARY.md's own precedent):
    distinguishing "how many `@keyframes` blocks share a name" and
    "which animation duration is a bare literal" needs the RAW served
    text, not `companion_markup.css_rules()`'s per-declaration view —
    the check still never reads a file from disk, only the SERVED,
    comment-stripped stylesheet.
    """
    out = ""
    pos = 0
    for match in re.finditer(r"@media[^{]*prefers-reduced-motion", css_source):
        if match.start() < pos:
            continue
        open_brace = css_source.find("{", match.start())
        if open_brace < 0:
            continue
        depth = 0
        index = open_brace
        while index < len(css_source):
            if css_source[index] == "{":
                depth += 1
            elif css_source[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        out += css_source[pos:match.start()]
        pos = index + 1
    return out + css_source[pos:]


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
    with scripts blocked (CFG-46/D-09, 25-01-PLAN.md Task 4)"""
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
    because this stylesheet's comments quote every token the check counts (D3/CFG-32,
    23-01-PLAN.md Task 2)"""
    stripped = re.sub(r"/\*.*?\*/", "", served_css, flags=re.DOTALL)

    names = re.findall(r"@keyframes\s+([A-Za-z_-][\w-]*)", stripped)
    seen = []
    for name in names:
        assert name not in seen, (
            "@keyframes %r is defined %d times in the served stylesheet — the motion budget is "
            "ONE shared definition per animation" % (name, names.count(name)))
        seen.append(name)

    reduce_blocks = re.findall(r"@media[^{]*prefers-reduced-motion\s*:\s*reduce", stripped)
    assert len(reduce_blocks) == _EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS, (
        "the served stylesheet carries %d live `@media (prefers-reduced-motion: reduce)` "
        "block(s), expected %d" % (len(reduce_blocks), _EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS))
    no_pref_blocks = re.findall(
        r"@media[^{]*prefers-reduced-motion\s*:\s*no-preference", stripped)
    assert len(no_pref_blocks) == _EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, (
        "the served stylesheet carries %d live `@media (prefers-reduced-motion: "
        "no-preference)` wrapper(s), expected %d"
        % (len(no_pref_blocks), _EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS))

    live = _without_reduced_motion_blocks(stripped)
    for match in re.finditer(r"(?<![\w-])(animation(?:-name|-duration)?)\s*:([^;}]*)", live):
        prop, value = match.group(1), match.group(2).strip()
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
        assert banned not in live, (
            "the served stylesheet declares %r — Chromium-only and Baseline limited, use "
            "grid-template-rows: 0fr -> 1fr instead" % (banned,))


# ==========================================================================
# login-card.js: public route, ES5-safety, route/src agreement, the
# no-inline-script page contract, the server-rendered reveal toggle
# ==========================================================================


def test_login_card_script_public(app04_server):
    """GET /static/login-card.js succeeds without a session and returns a shared-cacheable
    JavaScript content type"""
    status, headers, body = http_request(app04_server.base_url() + "/static/login-card.js")
    assert status == 200, "expected 200, got %d" % status
    assert "text/javascript" in headers.get("Content-Type", ""), (
        "expected a text/javascript content type, got %r" % headers.get("Content-Type", ""))
    assert body, "expected a non-empty script body"
    assert "max-age=300" in headers.get("Cache-Control", ""), (
        "expected Cache-Control max-age=300, got %r" % headers.get("Cache-Control", ""))


def test_login_card_script_es5_safe_and_no_html_write(app04_server):
    """login-card.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/
    outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), carries the reveal contract
    (addEventListener/querySelector/getAttribute/data-login-reveal/aria-pressed/the class-at-
    load modifier) and duplicates no server-side throttling constant (X3, T-22-46/T-22-49)"""
    src = served_asset(app04_server, "/static/login-card.js")
    assert src.count('"use strict"') == 1, (
        "expected exactly one \"use strict\", got %d" % src.count('"use strict"'))
    for token in (
            "let ", "const ", "=>", "`", "innerHTML", "outerHTML", "insertAdjacentHTML",
            "document.write", "eval(", "fetch(", "XMLHttpRequest"):
        assert token not in src, "login-card.js must not contain %r" % token
    for token in (
            "addEventListener", "querySelector", "getAttribute", "data-login-reveal",
            "aria-pressed", "login-form__field--with-toggle"):
        assert token in src, "expected %r in login-card.js" % token
    for leaked in ("LOGIN_FAILURE_LIMIT", "LOGIN_LOCKOUT_S"):
        assert leaked not in src, (
            "login-card.js must not duplicate %r — the countdown is presentational over server "
            "state, never a second throttle" % leaked)


def test_login_card_script_route_src_agree():
    """layout.LOGIN_CARD_SCRIPT_SRC equals companion.app.LOGIN_CARD_SCRIPT_ROUTE"""
    assert layout.LOGIN_CARD_SCRIPT_SRC == app_module.LOGIN_CARD_SCRIPT_ROUTE, (
        "login-card script route drift: %r vs %r"
        % (layout.LOGIN_CARD_SCRIPT_SRC, app_module.LOGIN_CARD_SCRIPT_ROUTE))


def test_login_page_emits_exactly_one_script_tag(app04_server):
    """a rendered login page contains exactly ONE <script occurrence, the deferred
    LOGIN_CARD_SCRIPT_SRC tag, with no inline script and no nonce — login_shell() emitted zero
    script tags before this plan (X3, 22-13-PLAN.md Task 2)"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert text.count("<script") == 1, (
        "expected exactly one <script occurrence on the login page, got %d"
        % text.count("<script"))
    expected_tag = '<script src="%s" defer></script>' % layout.LOGIN_CARD_SCRIPT_SRC
    assert expected_tag in text, "expected %r on the login page" % expected_tag
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", text):
        pytest.fail("expected no inline <script> without a src, found %r" % match.group(0))
    assert "unsafe-inline" not in text and "nonce-" not in text, (
        "no nonce or unsafe-inline may appear on the login page")


def test_login_reveal_toggle_is_server_hidden_and_named(app04_server):
    """the server-rendered show-password toggle carries the hidden attribute, type="button",
    aria-pressed="false", both translated accessible names and .copy-btn's own icon-only
    geometry — and the field's padding modifier is NOT server-rendered (X3, the no-JS floor by
    construction)"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    toggle_at = text.find("data-login-reveal")
    assert toggle_at != -1, "expected the show-password toggle in the login card"
    tag_open = text.rindex("<button", 0, toggle_at)
    tag = text[tag_open:text.index(">", toggle_at) + 1]
    assert " hidden " in tag, (
        "the show-password toggle must server-render with the hidden attribute, got %r" % tag)
    assert 'type="button"' in tag, "the toggle must be type=\"button\", never a submit"
    assert 'aria-pressed="false"' in tag, "the toggle must server-render aria-pressed=\"false\""
    for needed in ('data-show-label="Show password"', 'data-hide-label="Hide password"'):
        assert needed in tag, "expected %r on the toggle" % needed
    for english in ("Show password", "Hide password"):
        assert i18n_module.t_lang(english, "fr") != english, (
            "%r has no French catalogue entry" % english)
    assert 'class="copy-btn login-reveal"' in tag, (
        "the toggle must carry .copy-btn as its first class so the 22x22 box, the 44x44 "
        "::before hit area and the 14px glyph box are reused verbatim, got %r" % tag)
    assert "login-form__field--with-toggle" not in text, (
        "the field's padding modifier must be added at load by login-card.js, never "
        "server-rendered — a scripts-blocked page shows no toggle and so must reserve no room "
        "for one")


# ==========================================================================
# login: wrong password, right password, deep-link return, open-redirect
# rejection, the renamed no-such-route next value, the dedicated shell
# ==========================================================================


def test_login_wrong_password(app04_server):
    """a login POST with the wrong password re-renders the form with the exact copy and sets no
    cookie"""
    status, headers, body = http_request(
        app04_server.base_url() + "/login", method="POST",
        data=("password=not-the-real-password").encode())
    assert status == 401, "expected 401 for a wrong password, got %d" % status
    assert b"Incorrect password. Try again." in body, (
        "expected the exact login-failure copy in the response body")
    assert "Set-Cookie" not in headers, "expected no Set-Cookie header on a failed login"


def test_login_correct_password(app04_server):
    """a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict
    and redirects to / (Home)"""
    status, headers, _ = http_request(
        app04_server.base_url() + "/login", method="POST",
        data=("password=%s" % TEST_PASSWORD).encode())
    assert status == 303, "expected a 303 redirect on successful login, got %d" % status
    assert headers.get("Location") == "/", (
        "expected a redirect to / (Home), got %r" % headers.get("Location"))
    set_cookie = headers.get("Set-Cookie", "")
    for needle in ("HttpOnly", "Secure", "SameSite=Strict"):
        assert needle in set_cookie, (
            "missing %r in the session cookie header: %r" % (needle, set_cookie))


def test_deep_link_return_round_trip(make_app_server):
    """an unauthenticated GET /health redirects with ?next=%2Fhealth, and logging in with that
    next value returns the user to /health, not /settings"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    status, headers, _ = http_request(base + "/health")
    assert status == 303, "expected 303 for GET /health, got %d" % status
    assert headers.get("Location") == "/login?next=%2Fhealth", (
        "expected Location /login?next=%%2Fhealth, got %r" % headers.get("Location"))
    status, headers, _ = http_request(
        base + "/login", method="POST",
        data=urllib.parse.urlencode({"password": TEST_PASSWORD, "next": "/health"}).encode())
    assert status == 303, "expected 303 on login POST, got %d" % status
    assert headers.get("Location") == "/health", (
        "expected Location /health after login with next=/health, got %r" % headers.get("Location"))


@pytest.mark.parametrize("crafted_next", ["https://evil.example", "//evil.example"])
def test_open_redirect_rejected(make_app_server, crafted_next):
    """a login POST with the correct password and next=%r redirects to the / (Home) fallback,
    never to the crafted value (T-06.6.2-12)"""
    server = make_app_server(fake_providers=True)
    status, headers, _ = http_request(
        server.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode({"password": TEST_PASSWORD, "next": crafted_next}).encode())
    assert status == 303, "expected 303 on login POST, got %d" % status
    location = headers.get("Location", "")
    assert location == "/", "expected the safe / (Home) fallback, got %r" % location
    assert "evil.example" not in location, "the crafted next value leaked into the redirect Location"


def test_login_get_with_unrecognised_next_carries_no_hidden_field(app04_server):
    """GET /login?next=/no-such-route (not a real NAV_TABS member) renders the plain login form
    with no hidden next input"""
    status, _headers, body = http_request(
        app04_server.base_url() + "/login?next=/no-such-route")
    assert status == 200, "expected 200, got %d" % status
    assert b'name="next"' not in body, (
        "an unrecognised ?next= value must not render a hidden next field — "
        "_validated_next_route() must be applied on the GET path too, not only the POST path")


def test_login_page_uses_dedicated_login_shell(app04_server):
    """GET /login (no session) is rendered by the dedicated login_shell(), not page_shell() —
    no sidebar/mobile-nav markup, autocomplete present"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert '<html lang="en"' in text, "expected <html lang=\"en\" in the login page"
    assert 'autocomplete="current-password"' in text, (
        "expected autocomplete=\"current-password\" on the password field")
    for absent in ("sidebar-nav", "dashboard-shell", "site-nav-toggle"):
        assert absent not in text, (
            "the login page must render layout.login_shell(), not page_shell() — found %r in "
            "the response body" % absent)


def test_login_clean_render_carries_no_error_association(app04_server, served_css):
    """GET /login with no error renders the stacked card (a .login-form with a
    .login-form__input and a bare page-title brand mark, no glyph, no sprite) and carries
    NEITHER aria-invalid NOR aria-describedby — never aria-invalid="false" — with style.css
    carrying the field/primary/error-border rules it had none of before (X3, 22-13-PLAN.md
    Task 1)"""
    status, _headers, body = http_request(app04_server.base_url() + "/login")
    assert status == 200, "expected 200, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert "aria-invalid" not in text, (
        "a clean login render must carry no aria-invalid at all, found one in the response body")
    assert "aria-describedby" not in text, (
        "a clean login render must carry no aria-describedby — there is no message for it to "
        "point at")
    assert 'id="login-error"' not in text, "a clean login render must render no message element"
    for needed in ('class="login-form"', 'class="login-form__input"'):
        assert needed in text, "expected %r in the login card markup" % needed
    assert '<h1 class="page-title">SkyPane</h1>' in text, (
        "expected the bare page-title brand mark with no glyph beside it")
    assert "<svg" not in text and "icon-defs" not in text, (
        "the login card must add no icon/brand glyph — login_shell() deliberately emits no "
        "ICON_DEFS_HTML sprite")
    for selector in (
            ".login-form__input", '.login-form__input[aria-invalid="true"]',
            '.login-card button[type="submit"]'):
        assert rules_with_selector(served_css, selector), (
            "expected a rule for selector %r in the served stylesheet" % selector)


def test_login_error_render_is_programmatically_associated(app04_server):
    """a wrong-password login render carries aria-invalid="true", aria-describedby="login-error"
    and a role="alert" message in the existing .field-error text-label treatment, rendered
    between the field and the primary (X3, 22-UI-SPEC.md §5 contract 5)"""
    status, _headers, body = http_request(
        app04_server.base_url() + "/login", method="POST",
        data=b"password=still-not-the-real-password")
    assert status == 401, "expected 401 for a wrong password, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert 'aria-invalid="false"' not in text, (
        "aria-invalid=\"false\" must never be emitted on this card")
    for needed in (
            'aria-invalid="true"', 'aria-describedby="login-error"',
            '<p id="login-error" class="field-error text-label" role="alert">'):
        assert needed in text, "expected %r in the error render" % needed
    field_at = text.index('class="login-form__input"')
    message_at = text.index('id="login-error"')
    submit_at = text.index('<button type="submit">')
    assert field_at < message_at < submit_at, (
        "expected field -> message -> primary in document order, got offsets %d / %d / %d"
        % (field_at, message_at, submit_at))
    assert '<p class="text-body" role="alert">' not in text, (
        "the old bare text-body alert paragraph must be gone — one error voice on this card")


def test_login_lockout_render_shares_the_one_error_voice(make_app_server):
    """a locked-out login render puts the server-computed lockout sentence in the SAME
    .field-error text-label role=alert treatment under the field, with aria-describedby but
    deliberately no aria-invalid (X3, one error voice)"""
    server = make_app_server(fake_providers=True)
    base = server.base_url()
    for _attempt in range(auth.LOGIN_FAILURE_LIMIT):
        http_request(base + "/login", method="POST", data=b"password=wrong")
    status, _headers, body = http_request(
        base + "/login", method="POST", data=("password=%s" % TEST_PASSWORD).encode())
    assert status == 429, "expected 429 once the throttle has locked out, got %d" % status
    text = body.decode("utf-8", errors="replace")
    assert '<p id="login-error" class="field-error text-label" role="alert">' in text, (
        "the lockout sentence must render in the SAME .field-error text-label treatment as the "
        "wrong-password message")
    assert 'aria-describedby="login-error"' in text, "expected aria-describedby on the locked-out field"
    assert "aria-invalid" not in text, (
        "the lockout branch must carry no aria-invalid — the typed value is not what is wrong, "
        "the form is locked")
    assert "Too many attempts" in text, "expected the server-computed lockout sentence"
    assert text.count("data-lockout-seconds=") == 1, (
        "expected exactly one server-produced countdown seed in the rendered page, got %d"
        % text.count("data-lockout-seconds="))
    seed = re.search(r'data-lockout-seconds="(\d+)"', text)
    assert seed and int(seed.group(1)) > 0, (
        "expected a positive server-computed seed, got %r" % (seed.group(1) if seed else None))
    assert int(seed.group(1)) <= auth.LOGIN_LOCKOUT_S, (
        "the seed must be the server's own seconds_remaining() figure, never longer than the "
        "window itself")
    for needed in ('data-lockout-template="', 'data-lockout-token="'):
        assert needed in text, "expected %r on the locked-out form" % needed
    assert "LOGIN_FAILURE_LIMIT" not in text and str(auth.LOGIN_FAILURE_LIMIT) + '"' not in text, (
        "no throttling constant may be rendered into the page")
    field_tag = text[text.index("<input type=\"password\""):]
    field_tag = field_tag[:field_tag.index(">") + 1]
    assert " disabled" in field_tag, (
        "the password field must be natively disabled during a lockout, got %r" % field_tag)
    assert '<button type="submit" disabled>' in text, (
        "the primary must be natively disabled during a lockout, in the existing "
        "button:disabled treatment")


def test_both_shells_agree_on_document_language():
    """page_shell() and login_shell() both emit lang="en" (D-01/UXA-09 language-policy
    regression guard)"""
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
    """authenticated GET /preview (the retired Preview page route) redirects to /flights (D-22,
    retargeted by phase 18)"""
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
    """authenticated GET /config (the retired settings path) returns 404 — D-26 declines a
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
    flash banner, and persists nothing on disk (D-07/A-25)"""
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
    assert "banner--flash" not in body_text, (
        "expected no top-of-page flash banner on a field-level rejection (D-07)")
    after = device_config.load_device_config(server.state_dir)
    assert after == before, "expected nothing to be persisted on a rejected save, got %r (was %r)" % (after, before)


# ==========================================================================
# Phase 18: Home page, quick actions, scoped settings saves
# ==========================================================================


def test_home_page_renders_widgets(app04_server, session_cookie):
    """authenticated GET / renders the rebuilt Home page (D-01/D-04/D-05) with the Frame strip's
    two switch forms, three stat-tile elements, the picture/recent-flights row, and the
    recent-flights list under the grouped Advanced navigation, carrying none of the retired
    Quick-actions card or Poll form"""
    status, _headers, body = http_request(app04_server.base_url() + "/", cookie=session_cookie)
    assert status == 200, "expected 200 for GET /, got %d" % status
    text = body.decode("utf-8", errors="replace")
    for needle in (
            '<h1 class="page-title">Home</h1>',
            'class="frame-strip stat-tile stat-tile--accent"',
            'class="dashboard-grid home-status-grid"',
            'class="home-columns home-picture-row"',
            "Recent flights", 'href="/flights"',
            'class="nav-group nav-group--advanced"'):
        assert needle in text, "expected %r in the Home page" % needle
    assert 'class="preview-frame"' in text or "Nothing rendered yet." in text, (
        "expected either the preview-frame figure or its empty state on Home")
    assert 'action="%s"' % app_module.QUICK_DISPLAY_ROUTE in text, (
        "expected the Frame strip's Screen switch form on Home (D-01)")
    assert 'action="%s"' % app_module.QUICK_QUIET_HOURS_ROUTE in text, (
        "expected the Frame strip's Quiet hours switch form on Home (D-01)")
    for absent in (
            "Quick actions", "On the frame now", "status-card__rows", "home-hero",
            'action="%s"' % app_module.POLL_ROUTE):
        assert absent not in text, (
            "expected %r to be absent from the rebuilt Home page (D-04)" % absent)


def test_quick_display_toggle_round_trip(make_app_server):
    """POST /quick/display with state=off then state=on flips display_enabled on disk and
    redirects to Display (D-16) with the matching flash; a crafted state value redirects with
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
    redirects to Display (D-16) with the matching flash, and never touches display_enabled"""
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
    """21-04-PLAN.md Task 1 (D-01/R-02/T-21-12): return_to=/ redirects to Home, return_to=/display
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
    invalid-state early return honours return_to too (D-01/R-02)"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    _quick_toggle_return_to_check(
        server, session_cookie, app_module.QUICK_DISPLAY_ROUTE, app_module.FLASH_KEY_DISPLAY_ON)


def test_quick_quiet_hours_honours_return_to(make_app_server):
    """POST /quick/quiet-hours honours return_to (/ or /display), falls back to Display for a
    hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the
    invalid-state early return honours return_to too (D-01/R-02)"""
    server = make_app_server(fake_providers=True)
    session_cookie = login(server)
    _quick_toggle_return_to_check(
        server, session_cookie, app_module.QUICK_QUIET_HOURS_ROUTE, app_module.FLASH_KEY_QUIET_ON)


def test_quick_routes_answer_204_for_a_fetch_and_303_for_a_form(make_app_server):
    """POST /quick/display and POST /quick/quiet-hours answer a form post with exactly today's
    303-and-flash and a request carrying the fetch header with a 204, empty body and no Location
    — the same write either way, and a crafted state value is never a 204 (D2/CFG-36, T-23-26,
    23-07-PLAN.md Task 1)"""
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
    all (D2/CFG-36, T-23-23/T-23-24/T-23-25, 23-07-PLAN.md Task 2)"""
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
    """GET /display and GET /device split the settings groups per companion/screens.py (20-07
    moved Runway/Calendar/the rules editor to Display, D-10/D-11), each carrying its hidden
    scope/return_to fields and the screen-type caption; Manual refresh lives on Device only"""
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
        assert "Screen: Plane frame" in text, "expected the %s page to name its screen type" % scope
    assert "Manual refresh" in device_text, "expected the Device page to carry Manual refresh"
    rules_panel_marker = 'data-usage="rules"'
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
