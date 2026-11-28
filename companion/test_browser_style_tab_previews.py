# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser check of the frame preview images across Style tab switches: a preview keeps one
content-addressed URL on every tab, the browser is told it never expires (so a tab switch, even
after the short lifetime an unaddressed image has, does not ask the server again), no unchanged
preview reaches the network on a revisit, and a URL that does not carry the current address never
pins an image."""
import re

import pytest

from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser

TABS = ("/display", "/display/arrivals", "/display/special-looks", "/display/calendar")
YEAR = 365 * 24 * 3600


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


def _is_preview(url):
    return "/frame-preview/" in url or "/theme-preview/" in url


def _visit(page, base_url, route, log):
    log["urls"].clear()
    log["network"].clear()
    page.goto(base_url + route)
    page.wait_for_load_state("networkidle")
    page.evaluate("async () => { for (const i of document.images) { try { await i.decode(); } catch (e) {} } }")
    page.wait_for_load_state("networkidle")
    return {"urls": sorted(log["urls"]), "network": sorted(log["network"])}


def _measure(new_context, server):
    context = new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    _login(page, server.base_url())
    # A routed context bypasses the HTTP cache; the server is loopback, so the guard is lifted
    # for the measurement of the real cache behaviour only.
    context.unroute("**/*")
    cdp = context.new_cdp_session(page)
    cdp.send("Network.enable")
    log = {"urls": [], "network": [], "headers": []}
    ids = {}
    page.on("request", lambda r: _is_preview(r.url) and log["urls"].append(r.url))
    page.on("response", lambda r: _is_preview(r.url) and log["headers"].append(
        (r.url, r.status, r.headers.get("cache-control", ""))))
    cdp.on("Network.requestWillBeSent", lambda e: ids.__setitem__(e["requestId"], e["request"]["url"]))
    # A body that came over the network, as opposed to a copy the browser already held.
    cdp.on("Network.loadingFinished", lambda e: _is_preview(ids.get(e["requestId"], "")) and
           e["encodedDataLength"] > 1000 and log["network"].append(ids[e["requestId"]]))
    results = {}
    for index, route in enumerate(TABS + (TABS[0],)):
        results[route if index < len(TABS) else route + "#again"] = _visit(page, server.base_url(), route, log)
    context.close()
    return results, log["headers"]


def test_a_preview_keeps_one_addressed_url_on_every_tab(new_context, server):
    """the same preview has the same URL each time it is shown, and the URL carries its content
    address"""
    results, _ = _measure(new_context, server)
    first, again = results["/display"]["urls"], results["/display#again"]["urls"]
    assert first, "the departures tab asks for preview images"
    assert first == again
    assert all(re.search(r"[?&]v=[0-9a-f]{12}(&|$)", url) for url in first)


def test_preview_responses_are_private_and_never_expire(new_context, server):
    """an addressed preview is cached for a year as immutable and only for this browser; a tab
    switch after the five-minute lifetime the images used to have is answered from that entry"""
    _, headers = _measure(new_context, server)
    assert headers
    for url, status, cache_control in headers:
        assert status == 200, url
        directives = [part.strip() for part in cache_control.split(",")]
        assert "private" in directives and "public" not in directives, url
        assert "immutable" in directives, url
        assert max(int(d.split("=")[1]) for d in directives if d.startswith("max-age=")) >= YEAR, url


def test_a_tab_switch_fetches_no_unchanged_preview(new_context, server):
    """across a pass through every Style tab and back, a preview body crosses the network once, on
    the first tab that shows it, never again"""
    results, _ = _measure(new_context, server)
    seen = set()
    for route, visit in results.items():
        repeated = [url for url in visit["network"] if url in seen]
        assert not repeated, (route, repeated)
        seen.update(visit["network"])
    assert results["/display#again"]["network"] == []
    assert results["/display/calendar"]["network"] == []


def test_a_stale_or_missing_address_never_pins_an_image(new_context, server):
    """only the current address earns the year-long entry: another value, or none, keeps the short
    lifetime, and the current address answers with the same pixels"""
    context = new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/display")
    page.wait_for_load_state("networkidle")
    src = page.evaluate("[...document.images].map(i => i.getAttribute('src')).find(s => /frame-preview/.test(s))")
    assert "&v=" in src
    answers = {}
    for name, url in (
            ("current", src),
            ("stale", re.sub(r"v=[0-9a-f]{12}", "v=000000000000", src)),
            ("none", re.sub(r"&v=[0-9a-f]{12}", "", src))):
        response = context.request.get(server.base_url() + url)
        assert response.status == 200, name
        answers[name] = (response.headers["cache-control"], response.body())
    assert "immutable" in answers["current"][0]
    for name in ("stale", "none"):
        assert answers[name][0] == "private, max-age=300", name
        assert answers[name][1] == answers["current"][1], name
    context.close()


_RECORD_REVEALS = """
window.__revealed = [];
new MutationObserver(records => {
  for (const r of records) {
    if (r.target.tagName === 'IMG' && r.target.classList.contains('is-revealed')) {
      window.__revealed.push(r.target.getAttribute('src'));
    }
  }
}).observe(document, {subtree: true, attributes: true, attributeFilter: ['class']});
"""


def test_a_preview_already_loaded_does_not_fade_in_again_on_a_tab_switch(new_context, server):
    """a picture the browser already holds appears as it is; only one fetched over the network
    fades in, so moving between Style tabs does not make the previews blink"""
    context = new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    _login(page, server.base_url())
    context.unroute("**/*")
    page.add_init_script(_RECORD_REVEALS)
    revealed = {}
    for route in TABS + (TABS[0],):
        page.goto(server.base_url() + route)
        page.wait_for_load_state("networkidle")
        page.evaluate("async () => { for (const i of document.images) { try { await i.decode(); } catch (e) {} } }")
        page.wait_for_timeout(300)
        revealed[route + ("#again" if route in revealed else "")] = page.evaluate("window.__revealed")
    assert revealed["/display"], "pictures fetched for the first time still fade in"
    assert revealed["/display#again"] == []
