"""Auth0 sign-in and sign-out in real Chromium. The app is served from
127.0.0.1 while the fake identity provider is advertised as localhost, so
the hop to the provider is genuinely cross-site: the browser applies its
cross-site cookie rules to the redirect chain, which a same-host fake on
another port would hide.

Everything stays on loopback; the shared new_context guard aborts any
other host.
"""
import pytest

from companion import auth

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


def _context(new_context, base_url, theme="auto", width=1280):
    context = new_context(
        viewport={"width": width, "height": 900},
        color_scheme="dark" if theme == "dark" else "light")
    if theme != "auto":
        context.add_cookies([{
            "name": auth.UI_THEME_COOKIE_NAME, "value": theme, "url": base_url}])
    return context


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
    page.wait_for_url(base + "/account")
    assert INVITED_USER in page.locator(".account-identity").inner_text()
    cookies = _session_cookie(context)
    assert len(cookies) == 1
    assert cookies[0]["sameSite"] == "Strict"
    assert cookies[0]["httpOnly"] is True


def test_invited_admin_lands_on_home_with_the_full_nav(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, INVITED_ADMIN, "auth0|admin-1")
    page.wait_for_url(base + "/")
    hrefs = page.eval_on_selector_all(
        ".dashboard-sidebar a", "els => els.map(e => e.getAttribute('href'))")
    assert "/health" in hrefs and "/flights" in hrefs
    assert len(_session_cookie(context)) == 1


def test_sign_out_ends_on_the_fixed_login_page(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(base + "/account")
    page.click(".account-sign-out button")
    page.wait_for_url(base + "/login")
    assert page.locator("a.login-signin").count() == 1
    assert _session_cookie(context) == []
    page.goto(base + "/account")
    assert page.url == base + "/login"
    assert rig.fake.calls_to("/v2/logout")


def test_uninvited_identity_gets_the_refusal_and_no_cookie(rig, new_context):
    base = rig.server.base_url()
    context = _context(new_context, base)
    page = context.new_page()
    _sign_in(page, rig, UNINVITED, "auth0|stranger")
    page.get_by_text("No invitation found").wait_for()
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
    page.get_by_text("No invitation found").wait_for()
    assert _no_overflow(page)

    _sign_in(page, rig, INVITED_USER, "auth0|user-1")
    page.wait_for_url(base + "/account")
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
    page.wait_for_url(base + "/account")
    assert INVITED_USER in page.locator(".account-identity").inner_text()
