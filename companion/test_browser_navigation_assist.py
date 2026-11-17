"""Real-browser checks of the three navigation helpers: the opening splash plays at every
opening of the site (a new tab) and not on in-app navigation, the destinations behind the
navigation links are warmed on idle and on intent without ever touching a route with side
effects, and a request refused because the session ended shows a message and leads to the
sign-in page keeping the page, while the sign-in refuses anything but a known same-site
destination; the quiet-hours dialog shows the saved window when it opens again."""
import time
from urllib.parse import urlsplit

import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_PHONE,
    _login,
    seed_state_dir,
)
from server import device_config

pytestmark = pytest.mark.browser

SPLASH_ON = (
    "() => !!document.documentElement && document.documentElement.classList.contains('splash-on')")
SPLASH_DONE = "() => !!window.skypaneSplash && window.skypaneSplash.state === 'done'"
SCREEN_BUTTON = 'form[action="/quick/display"] button[role="switch"]'


def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=False)


@pytest.fixture
def server(make_app_server):
    return make_app_server(seed=_seed, fake_providers=True)


def _wait_until(page, predicate, timeout_s=12.0):
    """Polls through the page's own wait so its events are delivered meanwhile."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        page.wait_for_timeout(100)
    return predicate()


def _home(new_context, server, **context_args):
    context = new_context(**context_args)
    page = context.new_page()
    _login(page, server.base_url())
    return context, page


def _record_prefetches(page):
    seen = {"requests": [], "active": 0, "peak": 0}

    def on_request(request):
        if request.headers.get("x-requested-with") == "prefetch":
            seen["requests"].append((request.method, urlsplit(request.url).path))
            seen["active"] += 1
            seen["peak"] = max(seen["peak"], seen["active"])

    def on_done(request):
        if request.headers.get("x-requested-with") == "prefetch":
            seen["active"] -= 1

    page.on("request", on_request)
    page.on("requestfinished", on_done)
    page.on("requestfailed", on_done)
    return seen


def test_the_splash_plays_at_each_opening_and_not_on_in_app_navigation(new_context, server):
    """a second tab (a new opening of the site) plays the splash although the first one already
    did; moving between pages inside a tab does not"""
    context, page = _home(new_context, server, splash=True, viewport=VIEWPORT_PHONE)
    try:
        page.goto(server.base_url() + layout.HOME_ROUTE, wait_until="commit")
        page.wait_for_function(SPLASH_ON, timeout=5000)
        page.wait_for_function(SPLASH_DONE, timeout=6000)
        page.goto(server.base_url() + "/flights")
        page.wait_for_function("() => document.readyState === 'complete'")
        assert page.evaluate(SPLASH_ON) is False
        second = context.new_page()
        second.goto(server.base_url() + layout.HOME_ROUTE, wait_until="commit")
        second.wait_for_function(SPLASH_ON, timeout=5000)
        second.wait_for_function(SPLASH_DONE, timeout=6000)
        assert second.evaluate(
            "() => document.querySelectorAll('[inert]').length") == 0
    finally:
        context.close()


def test_idle_warms_only_the_two_likeliest_destinations(new_context, server):
    """after load only the two pages likeliest to be opened next (from Home: Flights and
    Personalisation) are fetched with GET and the prefetch header, never the current page, the
    bare root, the heavier pages or a route with side effects, two at a time at most"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        seen = _record_prefetches(page)
        page.goto(server.base_url() + layout.HOME_ROUTE)
        hrefs = page.evaluate(
            "() => Array.from(document.querySelectorAll('.tab-bar a[href]'))"
            ".map((a) => new URL(a.href).pathname)")
        expected = {h for h in hrefs if h in (layout.FLIGHTS_ROUTE, layout.DISPLAY_ROUTE)}
        assert expected
        assert _wait_until(
            page, lambda: expected <= {path for _, path in seen["requests"]}), seen["requests"]
        # Let any further (unwanted) idle request show up before counting.
        page.wait_for_timeout(1500)
        assert {path for _, path in seen["requests"]} == expected, seen["requests"]
        assert {method for method, _ in seen["requests"]} == {"GET"}
        assert layout.HOME_ROUTE not in {path for _, path in seen["requests"]}
        assert not [p for _, p in seen["requests"] if p.startswith(("/logout", "/quick", "/login"))]
        assert seen["peak"] <= 2
    finally:
        context.close()


def _idle_requests(page, seen, expected):
    """Waits past the idle delay (a marker timer started by the page itself) and returns the
    warm-up requests seen since the list was last emptied."""
    page.evaluate(
        "() => { window.__idlePassed = false;"
        " setTimeout(() => { window.__idlePassed = true; }, 4500); }")
    if expected:
        _wait_until(page, lambda: len(seen["requests"]) >= expected)
    page.wait_for_function("() => window.__idlePassed === true", timeout=15000)
    return list(seen["requests"])


def test_idle_warming_runs_on_a_new_page_view_only_not_on_back_forward_or_reload(
        new_context, server):
    """a page the visitor opens warms its two likeliest destinations; the same page reached again
    by Back, by Forward or by a reload does not ask for them a second time, while a tap on a link
    there is still warmed at once"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        seen = _record_prefetches(page)
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        assert len(_idle_requests(page, seen, 2)) == 2
        page.goto(server.base_url() + "/account")
        page.wait_for_function("() => document.readyState === 'complete'")
        assert len(_idle_requests(page, seen, 3)) >= 3, "a new page view warms its own"
        del seen["requests"][:]
        page.go_back()
        page.wait_for_function("() => document.readyState === 'complete'")
        assert _idle_requests(page, seen, 0) == [], "Back warmed pages again"
        page.go_forward()
        page.wait_for_function("() => document.readyState === 'complete'")
        assert _idle_requests(page, seen, 0) == [], "Forward warmed pages again"
        page.reload()
        page.wait_for_function("() => document.readyState === 'complete'")
        assert _idle_requests(page, seen, 0) == [], "a reload warmed pages again"
        # Intent still warms: a hover-less phone sends touchstart on the link.
        link = page.locator('.tab-bar a[href$="/flights"]').first
        link.dispatch_event("touchstart")
        _wait_until(page, lambda: any(path.endswith("/flights") for _m, path in seen["requests"]))
    finally:
        context.close()


def test_intent_warms_a_link_at_once_and_side_effect_routes_are_never_warmed(
        new_context, server):
    """a touch or a hover on a link warms its page before the idle pass; a link to the sign-out
    route or a quick switch is ignored whatever the gesture"""
    context, page = _home(new_context, server, viewport=VIEWPORT_DESKTOP)
    try:
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        seen = _record_prefetches(page)
        page.evaluate(
            "() => { const bar = document.querySelector('.tab-bar') || document.querySelector("
            "'.sidebar-nav'); for (const href of ['/logout', '/quick/display', "
            "'https://example.com/x', '/flights?sort=x']) { const a = document.createElement('a');"
            " a.href = href; a.textContent = 'x'; a.dataset.injected = '1'; bar.appendChild(a); } }")
        for index in range(4):
            page.evaluate(
                "(i) => document.querySelectorAll('[data-injected]')[i]"
                ".dispatchEvent(new Event('touchstart', {bubbles: true}))", index)
        page.locator(".sidebar-nav a[href$='/flights'], .tab-bar a[href$='/flights']").first \
            .dispatch_event("touchstart")
        assert _wait_until(page, lambda: ("GET", "/flights") in seen["requests"])
        assert not [p for _, p in seen["requests"]
                    if p in ("/logout", "/quick/display") or p.endswith("/x")]
        assert all(p == "/flights" for _, p in seen["requests"])
    finally:
        context.close()


def test_save_data_stops_the_warming(new_context, server):
    context = new_context(viewport=VIEWPORT_PHONE)
    context.add_init_script(
        "Object.defineProperty(navigator, 'connection', "
        "{value: {saveData: true, effectiveType: '4g'}});")
    page = context.new_page()
    try:
        _login(page, server.base_url())
        seen = _record_prefetches(page)
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        page.wait_for_timeout(4500)
        page.locator(".tab-bar a[href$='/flights']").first.dispatch_event("touchstart")
        page.wait_for_timeout(500)
        assert seen["requests"] == []
    finally:
        context.close()


def test_prefetch_answers_are_privately_cacheable_and_other_answers_never(
        new_context, server):
    """only the script's prefetch GET gets a short private cache window keyed by the cookie; a
    plain page load, the freshness tick and a response that sets a cookie stay no-store"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    try:
        url = server.base_url() + "/flights"
        warmed = context.request.get(url, headers={"X-Requested-With": "prefetch"})
        assert warmed.status == 200
        assert warmed.headers["cache-control"] == "private, max-age=10"
        assert warmed.headers["vary"] == "Cookie"
        plain = context.request.get(url)
        assert plain.headers["cache-control"] == "no-store"
        assert "vary" not in plain.headers
        tick = context.request.get(url, headers={"X-Requested-With": "freshness"})
        assert tick.headers["cache-control"] == "no-store"
        missing = context.request.get(
            server.base_url() + "/no-such-page", headers={"X-Requested-With": "prefetch"})
        assert missing.headers["cache-control"] == "no-store"
    finally:
        context.close()


def test_a_change_rewrites_the_marker_cookie_that_keys_the_warmed_pages(new_context, server):
    context, page = _home(new_context, server, viewport=VIEWPORT_DESKTOP)
    try:
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        assert "sp_mut" not in page.evaluate("() => document.cookie")
        page.locator(SCREEN_BUTTON).click()
        page.wait_for_function(
            "() => !document.querySelector('[data-quick-region][data-pending]')", timeout=15000)
        page.wait_for_function("() => document.cookie.indexOf('sp_mut=') !== -1")
    finally:
        context.close()


@pytest.mark.parametrize("lang,message", [
    ("en", "Session expired"),
    ("fr", "Session expirée"),
])
def test_an_expired_session_says_so_and_leads_to_sign_in_keeping_the_page(
        new_context, server, lang, message):
    """pressing a switch after the session ended shows the message and then opens the sign-in
    page with the current page as the validated next destination, marked as an expiry"""
    context, page = _home(new_context, server, viewport=VIEWPORT_PHONE)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    try:
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        context.clear_cookies(name=auth.SESSION_COOKIE_NAME)
        page.locator(SCREEN_BUTTON).click()
        page.wait_for_function(
            "m => (document.querySelector('[data-quick-toast]') || {textContent: ''})"
            ".textContent.indexOf(m) !== -1", arg=message, timeout=10000)
        page.wait_for_url("**/login?next=*", timeout=10000)
        assert urlsplit(page.url).path == "/login"
        assert urlsplit(page.url).query == "next=%2F&expired=1"
    finally:
        context.close()


def test_sign_in_keeps_a_known_page_with_its_query_and_refuses_everything_else(
        new_context, server):
    """an unauthenticated request is sent to /login with the page and a plain query kept; a
    hostile or unknown address is dropped from the redirect and from the sign-in card"""
    context = new_context()
    try:
        base = server.base_url()
        kept = context.request.get(base + "/flights?sort=airline", max_redirects=0)
        assert kept.headers["location"] == "/login?next=%2Fflights%3Fsort%3Dairline"
        plain = context.request.get(base + "/flights?q=a;b", max_redirects=0)
        assert plain.headers["location"] in ("/login", "/login?next=%2Fflights")
        for hostile in ("//evil.example", "https://evil.example/", "/\\evil.example",
                        "/flights?x=1#frag", "/flights?x=%0d%0aSet-Cookie:a=b", "/unknown"):
            page = context.request.get(
                base + "/login", params={"next": hostile}, max_redirects=0)
            assert page.status == 200
            assert "evil.example" not in page.text()
            assert "Set-Cookie:a" not in page.text()
    finally:
        context.close()


def test_quiet_hours_dialog_shows_the_saved_window_when_it_opens_again(new_context, server):
    context, page = _home(new_context, server, viewport=VIEWPORT_DESKTOP)
    try:
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function("() => document.readyState === 'complete'")
        opener = page.locator("a.home-switch__window")
        field = "#quiet-window-start"
        opener.click()
        page.wait_for_function(
            "() => !!document.querySelector('dialog[open]')")
        saved = page.evaluate("(s) => document.querySelector(s).value", field)
        page.evaluate(
            "(s) => { const f = document.querySelector(s); f.value = '01:00';"
            " f.dispatchEvent(new Event('input', {bubbles: true})); }", field)
        page.keyboard.press("Escape")
        page.wait_for_function("() => !document.querySelector('dialog[open]')")
        opener.click()
        page.wait_for_function("() => !!document.querySelector('dialog[open]')")
        assert page.evaluate("(s) => document.querySelector(s).value", field) == saved
        assert saved != "01:00"
    finally:
        context.close()
