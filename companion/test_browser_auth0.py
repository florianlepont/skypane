"""Auth0 sign-in and sign-out in real Chromium. The app is served from
127.0.0.1 while the fake identity provider is advertised as localhost, so
the hop to the provider is genuinely cross-site: the browser applies its
cross-site cookie rules to the redirect chain, which a same-host fake on
another port would hide.

Everything stays on loopback; the shared new_context guard aborts any
other host.
"""
import re

import pytest

from companion import auth, oidc, sign_in

pytestmark = pytest.mark.browser

INVITED_USER = "invited.user@example.test"
INVITED_ADMIN = "invited.admin@example.test"
UNINVITED = "stranger@example.test"
_WIDTH = 360


@pytest.fixture
def rig(auth0_rig):
    """The in-process app wired to a fake provider that is advertised as
    `localhost:<port>` (a different site from the app's 127.0.0.1) while
    still listening on loopback.
    """
    domain = "localhost:%d" % auth0_rig.fake.port
    auth0_rig.server.apply_env({
        "SKYPANE_AUTH0_DOMAIN": domain,
        "SKYPANE_LEGACY_PASSWORD_LOGIN": "0",
    })
    auth0_rig.fake.set_knob("issuer_host", domain)
    auth0_rig.invite(INVITED_USER, "user")
    auth0_rig.invite(INVITED_ADMIN, "admin")
    return auth0_rig


def _context(new_context, base_url, theme="auto", width=1280, lang=None):
    context = new_context(
        viewport={"width": width, "height": 900},
        color_scheme="dark" if theme == "dark" else "light")
    if theme != "auto":
        context.add_cookies([{
            "name": auth.UI_THEME_COOKIE_NAME, "value": theme, "url": base_url}])
    if lang:
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    return context


def _landing_url(base, route):
    """Matches the landing route with or without the welcome token."""
    return re.compile("^%s(\\?flash=welcome\\w*)?$" % re.escape(base + route))


def _session_cookie(context):
    return [c for c in context.cookies() if c["name"] == auth.SESSION_COOKIE_NAME]


def _sign_in(page, rig, email, sub):
    base = rig.server.base_url()
    rig.fake.next_login(sub=sub, email=email)
    page.goto(base + "/login")
    page.click("a.login-signin")


def test_invited_user_lands_on_account_signed_in(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(_landing_url(base, "/account"))
    assert INVITED_USER in page.locator(".account-identity").inner_text()
    cookies = _session_cookie(context)
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Strict"
    assert cookies[0]["httpOnly"] is True


def test_invited_admin_lands_on_the_fleet_page_with_the_console_nav(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, INVITED_ADMIN, "auth0|admin-1")
    page.wait_for_url(_landing_url(base, "/fleet"))
    hrefs = page.eval_on_selector_all(
        ".dashboard-sidebar a", "els => els.map(e => e.getAttribute('href'))")
    assert "/users" in hrefs and "/audit" in hrefs and "/fleet" in hrefs
    assert not any(href.endswith(("/health", "/update", "/device")) for href in hrefs)
    assert len(_session_cookie(context)) == 1


def test_sign_out_ends_on_the_fixed_login_page(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(_landing_url(base, "/account"))
    page.click(".logout-form button:visible")
    page.wait_for_url(base + "/login")
    assert page.locator("a.login-signin").count() == 1
    assert _session_cookie(context) == []
    page.goto(base + "/account")
    # The sign-in page keeps the page asked for (and no expiry mark: no session ended).
    assert page.url == base + "/login?next=%2Faccount"
    assert rig.fake.calls_to("/v2/logout")


def test_uninvited_identity_gets_the_refusal_and_no_cookie(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, UNINVITED, "auth0|stranger")
    page.get_by_text("This account can't sign in").wait_for()
    assert _session_cookie(context) == []
    assert rig.session_count() == 0


def _no_overflow(page):
    return page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_login_refusal_and_account_fit_at_360px(rig, new_context, theme):
    base = rig.server.base_url()
    context = _context(new_context, base, theme=theme, width=_WIDTH)
    page = context.new_page()

    page.goto(base + "/login")
    assert _no_overflow(page)
    link = page.locator("a.login-signin")
    box = link.bounding_box()
    assert box["height"] >= 44
    card = page.evaluate("""() => {
        const el = document.querySelector('.login-card');
        const s = getComputedStyle(el);
        return el.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
    }""")
    assert box["width"] >= card - 1

    _sign_in(page, rig, UNINVITED, "auth0|stranger")
    page.get_by_text("This account can't sign in").wait_for()
    assert _no_overflow(page)

    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(_landing_url(base, "/account"))
    assert _no_overflow(page)
    assert page.locator(".account-sign-out button").is_visible()


def test_sign_in_started_from_another_site_still_lands_signed_in(rig, new_context):
    """The sign-in begins from a page on a different site (a link followed
    from elsewhere), so the whole redirect chain carries a cross-site
    initiator; the session must still be usable on the landing page.
    """
    base = rig.server.base_url()
    other = "http://localhost:%d" % rig.fake.port
    context = _context(new_context, base)
    page = context.new_page()
    page.route(other + "/elsewhere", lambda route: route.fulfill(
        content_type="text/html",
        body='<a id="go" href="%s/login/auth0">go</a>' % base))
    rig.fake.next_login(sub="auth0|user-1", email=INVITED_USER)
    page.goto(other + "/elsewhere")
    page.click("#go")
    page.wait_for_url(_landing_url(base, "/account"))
    assert INVITED_USER in page.locator(".account-identity").inner_text()


# --- messages and first arrival -------------------------------------------

_WELCOME = "Welcome to SkyPane"


def _geometry_ok(page, selectors):
    # Measure only once the stylesheet has applied: every linked sheet is loaded and each
    # control's computed min-height is its styled value (an unstyled link measures 17px).
    page.wait_for_function(
        "(sels) => document.readyState === 'complete'"
        " && [...document.querySelectorAll('link[rel~=stylesheet]')].every((l) => l.sheet)"
        " && sels.every((s) => { const el = document.querySelector(s);"
        "   return !!el && parseFloat(getComputedStyle(el).minHeight) >= 44; })",
        arg=selectors, timeout=15000)
    assert page.evaluate(
        "() => document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    for selector in selectors:
        box = page.locator(selector).bounding_box()
        assert box["height"] >= 44, selector


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_unverified_email_shows_the_confirm_page_with_a_retry(rig, new_context, theme):
    base = rig.server.base_url()
    context = _context(new_context, base, theme=theme, width=_WIDTH)
    page = context.new_page()
    rig.fake.next_login(sub="auth0|new", email=INVITED_USER, email_verified=False)
    page.goto(base + "/login")
    page.click("a.login-signin")
    page.get_by_text("Confirm your email address").wait_for()
    assert page.locator("a.login-signin").inner_text() == "Sign in again"
    assert "Ask the administrator to resend it." in page.locator(".login-card").inner_text()
    _geometry_ok(page, ["a.login-signin"])
    assert _session_cookie(context) == []
    assert rig.session_count() == 0


def test_uninvited_page_offers_another_account_and_the_way_back(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base, width=_WIDTH)
    page = context.new_page()
    _sign_in(page, rig, UNINVITED, "auth0|stranger")
    page.get_by_text("This account can't sign in").wait_for()
    other = page.locator("a.login-signin")
    assert other.inner_text() == "Use another account"
    assert other.get_attribute("href") == "/login/auth0?prompt=login"
    _geometry_ok(page, ["a.login-signin", "a.login-card__link"])
    page.click("a.login-card__link")
    page.wait_for_url(base + "/login")
    assert "First visit?" in page.locator(".login-card").inner_text()


def test_use_another_account_asks_the_provider_to_show_its_form(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, UNINVITED, "auth0|stranger")
    page.get_by_text("This account can't sign in").wait_for()
    rig.fake.next_login(sub="auth0|user-1", email=INVITED_USER)
    page.click("a.login-signin")
    page.wait_for_url(_landing_url(base, "/account"))
    assert _session_cookie(context)


def test_first_sign_in_shows_one_welcome_and_the_second_none(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base, width=_WIDTH)
    page = context.new_page()
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(_landing_url(base, "/account"))
    page.get_by_text(_WELCOME).wait_for()
    assert page.get_by_text(_WELCOME).count() == 1
    assert "Add your frame with the code shown on its screen" in page.locator(".toast").inner_text()
    page.click(".logout-form button:visible")
    page.wait_for_url(base + "/login")
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(base + "/account")
    assert page.get_by_text(_WELCOME).count() == 0


def test_the_welcome_is_translated(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base, lang="fr")
    page = context.new_page()
    _sign_in(page, rig, INVITED_ADMIN, "auth0|admin-1")
    page.wait_for_url(_landing_url(base, "/fleet"))
    page.get_by_text("Bienvenue sur SkyPane").wait_for()
    assert page.get_by_text("Bienvenue sur SkyPane").count() == 1


def test_a_cancelled_sign_in_is_calm_and_offers_sign_in(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base, width=_WIDTH)
    page = context.new_page()
    rig.fake.set_knob("redirect_error", "access_denied")
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.get_by_text("Sign-in was cancelled").wait_for()
    assert "toast--info" in page.locator(".toast--docked").get_attribute("class")
    _geometry_ok(page, ["a.login-signin"])
    assert page.locator("a.login-signin").inner_text() == "Sign in"


def test_a_throttled_start_names_the_wait_and_offers_sign_in(rig, new_context, monkeypatch):
    base = rig.server.base_url()
    monkeypatch.setattr(sign_in, "START_THROTTLE", oidc.StartThrottle(limit=0))
    context = _context(new_context, base, width=_WIDTH)
    page = context.new_page()
    page.goto(base + "/login")
    page.click("a.login-signin")
    page.get_by_text("Too many attempts").wait_for()
    assert "toast--warning" in page.locator(".toast--docked").get_attribute("class")
    _geometry_ok(page, ["a.login-signin"])
