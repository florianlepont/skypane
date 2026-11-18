"""Real-browser measurement of the frame preview images across Style tab switches: which preview
URLs each tab asks for, how many of those requests reach the network, how many are answered from
the browser cache, and whether the same preview keeps the same URL on another tab."""
import pytest

from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser

TABS = ("/display", "/display/arrivals", "/display/special-looks", "/display/calendar")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


def _is_preview(url):
    return "/frame-preview/" in url or "/theme-preview/" in url


def _visit(page, base_url, route, log, cached):
    """Load `route`, wait until it is quiet, and return what happened to each preview request."""
    log.clear()
    cached.clear()
    page.goto(base_url + route)
    page.wait_for_load_state("networkidle")
    page.evaluate("async () => { for (const i of document.images) { try { await i.decode(); } catch (e) {} } }")
    page.wait_for_load_state("networkidle")
    return {"urls": list(log), "served_from_cache": len(cached),
            "lazy": page.evaluate("[...document.images].filter(i => i.loading === 'lazy').length")}


def _measure(new_context, server, disable_cache):
    context = new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    _login(page, server.base_url())
    if not disable_cache:
        # A routed context bypasses the HTTP cache; the server is loopback, so the guard is lifted
        # for the measurement of the real cache behaviour only.
        context.unroute("**/*")
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    if disable_cache:
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
    cache_headers = []
    page.on("response", lambda r: _is_preview(r.url) and cache_headers.append(
        (r.status, r.headers.get("cache-control"))))
    log = []
    cached = set()
    page.on("request", lambda r: _is_preview(r.url) and log.append(r.url))
    urls = {}
    cdp.on("Network.requestWillBeSent", lambda e: urls.__setitem__(e["requestId"], e["request"]["url"]))
    cdp.on("Network.requestServedFromCache", lambda e: _is_preview(urls.get(e["requestId"], "")) and
           cached.add(e["requestId"]))
    cdp.on("Network.responseReceived", lambda e: e["response"].get("fromDiskCache") and
           _is_preview(e["response"]["url"]) and cached.add(e["requestId"]))
    first = _visit(page, server.base_url(), TABS[0], log, cached)
    results = {TABS[0]: first}
    for route in TABS[1:] + (TABS[0],):
        results[route + "#again" if route in results else route] = _visit(
            page, server.base_url(), route, log, cached)
    context.close()
    return results, cache_headers


def test_preview_requests_per_style_tab_switch(new_context, server):
    """measured behaviour today: every tab keeps one URL per preview, and the browser cache
    answers a repeat visit, or revalidates it, depending on the cache-control header the
    preview route sends"""
    results, headers = _measure(new_context, server, disable_cache=False)
    for route, seen in results.items():
        print("CACHE-ON %-26s preview requests=%d from-cache=%d lazy-images=%d unique-urls=%d" % (
            route, len(seen["urls"]), seen["served_from_cache"], seen["lazy"], len(set(seen["urls"]))))
    print("CACHE-ON response (status, cache-control):", sorted(set(headers)))
    departures_first = set(results["/display"]["urls"])
    departures_again = set(results["/display#again"]["urls"])
    assert departures_first, "the departures tab asks for preview images"
    assert departures_first == departures_again, "a preview keeps the same URL when the tab is revisited"
    assert results["/display#again"]["served_from_cache"] == len(results["/display#again"]["urls"])
    assert all(status == 200 for status, _ in headers)
    assert any("max-age" in (cc or "") for _, cc in headers)


def test_preview_requests_without_browser_cache(new_context, server):
    """with the cache disabled every revisit reaches the network; the gap between this run and
    the cached run shows whether the reload comes from the URL, from revalidation, or from
    lazily loaded images being decoded again"""
    results, _ = _measure(new_context, server, disable_cache=True)
    for route, seen in results.items():
        print("CACHE-OFF %-26s preview requests=%d from-cache=%d" % (
            route, len(seen["urls"]), seen["served_from_cache"]))
    assert len(results["/display#again"]["urls"]) == len(results["/display"]["urls"])
    assert all(seen["served_from_cache"] == 0 for seen in results.values())
