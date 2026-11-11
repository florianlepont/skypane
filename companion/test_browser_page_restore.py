"""A page the browser restores from its back/forward cache is checked against the session before
it is shown: hidden at once, revealed only when the server confirms the same session, otherwise
sent to sign-in with the expired notice. The cacheable header is only served to a browser that
ran the check script, and only for an ordinary page navigation."""
import urllib.parse

import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login, seed_state_dir

pytestmark = pytest.mark.browser

CHECK_ROUTE = "/session/check"
PERSISTED = "() => window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))"
NOT_PERSISTED = "() => window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: false}))"
HIDDEN = "() => document.documentElement.style.visibility === 'hidden'"
SHOWN = "() => document.documentElement.style.visibility === ''"
SIGN_OUT = """async () => {
    const token = document.querySelector('input[name="csrf_token"]').value;
    const response = await fetch('/logout', {
        method: 'POST', credentials: 'same-origin', redirect: 'manual',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'csrf_token=' + encodeURIComponent(token)});
    return response.status || response.type;
}"""


@pytest.fixture
def server(make_app_server):
    return make_app_server(seed=seed_state_dir, fake_providers=True)


def _signed_in_page(new_context, server, path="/flights"):
    context = new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.wait_for_function("() => document.readyState === 'complete'")
    return context, page


def _hold_checks(page):
    """Park every session check until the test releases it; returns the parked routes."""
    held = []
    page.route("**" + CHECK_ROUTE, lambda route: held.append(route))
    return held


def _wait_held(page, held):
    page.wait_for_function(HIDDEN)
    deadline_polls = 0
    while not held and deadline_polls < 200:
        page.wait_for_timeout(25)
        deadline_polls += 1
    assert held, "the session check was never sent"


def test_a_restored_page_is_hidden_until_the_server_confirms_its_session(new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        held = _hold_checks(page)
        page.evaluate(PERSISTED)
        _wait_held(page, held)
        assert page.evaluate(HIDDEN)
        held[0].continue_()
        page.wait_for_function(SHOWN)
        assert page.url.endswith("/flights")
    finally:
        context.close()


def test_a_page_that_was_not_restored_is_left_alone(new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        seen = []
        page.on("request", lambda request: seen.append(request.url))
        page.evaluate(NOT_PERSISTED)
        page.wait_for_timeout(300)
        assert page.evaluate(SHOWN)
        assert not [url for url in seen if CHECK_ROUTE in url]
    finally:
        context.close()


def test_a_restored_page_after_sign_out_stays_hidden_and_leads_to_sign_in(new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        page.evaluate(SIGN_OUT)
        assert auth.SESSION_COOKIE_NAME not in {c["name"] for c in context.cookies()}
        held = _hold_checks(page)
        page.evaluate(PERSISTED)
        _wait_held(page, held)
        assert page.evaluate(HIDDEN)
        held[0].continue_()
        page.wait_for_url("**/login?**")
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)
        assert query["expired"] == ["1"]
        assert query["next"] == ["/flights"]
    finally:
        context.close()


def test_a_restored_page_of_another_session_is_refused(new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        page.evaluate(
            "() => { document.querySelector('input[name=\"csrf_token\"]').value = 'not-this-session'; }")
        page.evaluate(PERSISTED)
        page.wait_for_url(lambda url: not url.endswith("/flights"))
        assert urllib.parse.urlsplit(page.url).path != "/flights"
    finally:
        context.close()


def test_back_after_sign_out_reaches_sign_in_not_the_private_page(new_context, server):
    """The history entry is loaded again (a stale copy is never replayed): a request goes out and
    the answer is the sign-in page."""
    context, page = _signed_in_page(new_context, server)
    try:
        page.goto(server.base_url() + "/flights")
        page.goto(server.base_url() + "/display")
        page.wait_for_function("() => document.readyState === 'complete'")
        page.evaluate(SIGN_OUT)
        assert auth.SESSION_COOKIE_NAME not in {c["name"] for c in context.cookies()}
        requested = []
        page.on("request", lambda request: requested.append(request.url))
        page.go_back()
        page.wait_for_url("**/login?**")
        assert any(url.split("?")[0].endswith("/flights") for url in requested)
        assert urllib.parse.parse_qs(urllib.parse.urlsplit(page.url).query)["next"] == ["/flights"]
        assert page.locator(".tab-bar, .sidebar-nav").count() == 0
    finally:
        context.close()


def test_pages_are_cacheable_for_the_back_cache_only_after_the_script_ran(new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        url = server.base_url() + "/flights"
        page.wait_for_function(
            "() => document.cookie.split('; ').indexOf('sp_restore=1') !== -1")
        plain = context.request.get(url)
        assert plain.headers["cache-control"] == "private, no-cache"
        assert plain.headers["vary"] == "Cookie"
        prefetch = context.request.get(url, headers={"X-Requested-With": "prefetch"})
        assert prefetch.headers["cache-control"] == "private, max-age=10"
        tick = context.request.get(url, headers={"X-Requested-With": "freshness"})
        assert tick.headers["cache-control"] == "no-store"
        missing = context.request.get(server.base_url() + "/no-such-page")
        assert missing.headers["cache-control"] == "no-store"
        check = context.request.post(
            server.base_url() + CHECK_ROUTE, form={"csrf_token": "wrong"})
        assert check.status == 403
        assert check.headers["cache-control"] == "no-store"
    finally:
        context.close()


def test_a_browser_that_never_ran_the_script_gets_no_store(new_context, server):
    context = new_context(java_script_enabled=False)
    page = context.new_page()
    try:
        _login(page, server.base_url())
        response = context.request.get(server.base_url() + "/flights")
        assert response.status == 200
        assert response.headers["cache-control"] == "no-store"
        assert "vary" not in response.headers
        anonymous = context.request.post(server.base_url() + CHECK_ROUTE, form={})
        assert anonymous.status != 204
    finally:
        context.close()


def test_the_session_check_answers_204_to_the_pages_own_token_and_never_caches(
        new_context, server):
    context, page = _signed_in_page(new_context, server)
    try:
        token = page.evaluate("() => document.querySelector('input[name=\"csrf_token\"]').value")
        ok = context.request.post(server.base_url() + CHECK_ROUTE, form={"csrf_token": token})
        assert ok.status == 204
        assert ok.headers["cache-control"] == "no-store"
    finally:
        context.close()
