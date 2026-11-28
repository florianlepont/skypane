# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks that the opening splash fetches, while it plays, every file the other
destinations of the navigation need: the list it is given names each reachable page's own
stylesheets and scripts (it fails if a page's file is missing), it is role-aware (a plain user's
list holds no administrator-only file), and once the splash is over tapping each destination
asks the network for no stylesheet, script or Style picture again."""
import re
from collections import Counter

import pytest

import fleet_console_support as fx
from companion import layout
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login
from companion_app_server import session_cookie_for_state_dir

pytestmark = pytest.mark.browser

SPLASH_DONE = "() => !!window.skypaneSplash && window.skypaneSplash.state === 'done'"
WARM_SETTLED = (
    "() => !!window.skypaneSplash && !!window.skypaneSplash.warm"
    " && window.skypaneSplash.warm.settled === window.skypaneSplash.warm.queued")
NAV_LINKS = (
    ".dashboard-sidebar a[href], .tab-bar a[href], .tab-bar__more-panel a[href]")
PAGE_FILES = """() => {
  const found = [];
  document.querySelectorAll('link[rel=stylesheet][href], script[src]').forEach((n) => {
    found.push(n.getAttribute('href') || n.getAttribute('src'));
  });
  document.querySelectorAll('[data-leaflet-src],[data-search-src],[data-map-src],[data-map-search-src],'
    + '[data-card-src],[data-airports-src]').forEach((n) => {
    for (const a of n.attributes) { if (/^data-.*-src$/.test(a.name)) found.push(a.value); }
  });
  return found.filter((u) => u.startsWith('/static/'));
}"""
PRELOAD = """() => {
  const o = document.querySelector('[data-splash-preload]');
  return o ? o.getAttribute('data-splash-preload').split(' ') : [];
}"""
NAV_HREFS = """(sel) => [...new Set([...document.querySelectorAll(sel)].map((a) => a.getAttribute('href')))]"""
ADMIN_ONLY_FILES = (
    "airline-types.js", "airline-suggest.js", "fleet-anchors.js", "update-question.js",
    "copy-button.js")
SKIPPED = re.compile(r"^/(logout|login|quick)(/|$)")


def _seed(state_dir):
    seed_airline_editor(state_dir)
    fx.seed_fleet(state_dir)


@pytest.fixture
def server(make_app_server):
    return make_app_server(seed=_seed, fake_providers=True)


def _sign_in(context, page, server, who):
    if who == "admin":
        _login(page, server.base_url())
        return
    name, value = session_cookie_for_state_dir(
        server.state_dir, fx.OWNER_EMAIL, role="user").split("=", 1)
    context.add_cookies([{
        "name": name, "value": value, "url": server.base_url(), "httpOnly": True,
        "sameSite": "Strict"}])


CONSOLE_PATHS = ("/fleet", "/users", "/audit", "/airlines/manage", "/update")


def _is_console(path):
    return path.partition("?")[0].endswith(CONSOLE_PATHS)


def _crawl(page, server):
    """({path: its own static files}, {path: its preload list}) for every page reachable
    through the navigation links, starting at the root (the first entry)."""
    pages = {}
    preloads = {}
    todo = ["/"]
    while todo:
        href = todo.pop(0)
        page.goto(server.base_url() + href)
        path = page.url.replace(server.base_url(), "")
        if path in pages:
            continue
        pages[path] = page.evaluate(PAGE_FILES)
        preloads[path] = page.evaluate(PRELOAD)
        for link in page.evaluate(NAV_HREFS, NAV_LINKS):
            if not SKIPPED.match(link) and link not in pages and link not in todo:
                todo.append(link)
    return pages, preloads


def _stripped(url):
    return re.sub(r"^/devices/d_[0-9a-f]{8}", "", url.partition("?")[0])


@pytest.mark.parametrize("who", ["admin", "owner"])
def test_the_preload_list_holds_every_reachable_pages_own_files(
        new_context, server, who, blocked_requests):
    """the list of a space's first page plus its own files cover the stylesheets and scripts
    (the map page's starter-loaded ones included) of every page of that space, with the same
    version tokens the pages use"""
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _sign_in(context, page, server, who)
        pages, preloads = _crawl(page, server)
        assert len(pages) >= (8 if who == "admin" else 4), sorted(pages)
        root = next(iter(pages))
        refs = {"personal": root}
        if who == "admin":
            refs["console"] = next(p for p in pages if _is_console(p))
        for path, files in pages.items():
            ref = refs["console" if who == "admin" and _is_console(path) else "personal"]
            covered = set(preloads[ref]) | set(pages[ref])
            missing = [f for f in files if f not in covered]
            assert not missing, "%s needs %s, absent from the list of %s" % (path, missing, ref)
        assert preloads[root] and all(url.startswith("/") for url in preloads[root])
        # The Location page asks the map tile server by design; nothing else may leave.
        assert all("tile.openstreetmap.org" in url for url in blocked_requests), blocked_requests
        blocked_requests.clear()
    finally:
        context.close()


def _lists(new_context, server, who, path):
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _sign_in(context, page, server, who)
        page.goto(server.base_url() + path)
        return page.evaluate(PRELOAD)
    finally:
        context.close()


def test_the_preload_list_follows_the_space_and_a_user_never_gets_console_files(
        new_context, server):
    """a personal page lists the same files for an administrator and a plain user (none of
    the Console's); the Console's own pages list the Console's scripts"""
    # The Style pictures follow each frame's own settings, so only the files are compared.
    admin_home = [
        _stripped(u) for u in _lists(new_context, server, "admin", "/") if u.startswith("/static/")]
    owner_home = [
        _stripped(u) for u in _lists(new_context, server, "owner", "/") if u.startswith("/static/")]
    assert admin_home and sorted(admin_home) == sorted(owner_home), (
        Counter(admin_home) - Counter(owner_home), Counter(owner_home) - Counter(admin_home))
    for name in ADMIN_ONLY_FILES:
        assert "/static/" + name not in owner_home, name
        assert "/static/" + name not in admin_home, name
    assert "/static/style-flights.css" in owner_home
    console = [_stripped(u) for u in _lists(new_context, server, "admin", "/users")]
    assert "/static/airline-types.js" in console and "/static/fleet-anchors.js" in console


class _AssetRecorder:
    """The static files, Style pictures and the requests that really reached the network,
    by phase."""

    def __init__(self, context, page):
        self.phase = "load"
        self.requests = {}
        cdp = context.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.on("Network.requestWillBeSent", self._sent)
        cdp.on("Network.responseReceived", self._received)
        cdp.on("Network.requestServedFromCache", self._cached)
        cdp.on("Network.loadingFinished", self._finished)
        cdp.on("Network.loadingFailed", self._finished)

    @staticmethod
    def _wanted(url):
        return "/static/" in url or "/frame-preview/" in url

    def _sent(self, event):
        url = event["request"]["url"]
        if self._wanted(url):
            self.requests[event["requestId"]] = {
                "url": url, "phase": self.phase, "cached": False, "finished": False}

    def _cached(self, event):
        if event["requestId"] in self.requests:
            self.requests[event["requestId"]]["cached"] = True

    def _received(self, event):
        entry = self.requests.get(event["requestId"])
        if entry and event["response"].get("fromDiskCache"):
            entry["cached"] = True

    def _finished(self, event):
        if event["requestId"] in self.requests:
            self.requests[event["requestId"]]["finished"] = True

    def pending(self):
        return sum(1 for r in self.requests.values() if not r["finished"])

    def from_network(self, phase):
        return sorted(
            r["url"] for r in self.requests.values() if r["phase"] == phase and not r["cached"])


def _settle(page, recorder, quiet_ms=700, timeout_ms=20000):
    """Waits until every request the page made has finished and none has started for
    `quiet_ms`: the Location page loads its map scripts one after the other, after its first
    paint, so a request can still be in flight (and not yet known to come from the cache)
    long after the load event on a busy machine."""
    waited = quiet = 0
    seen = len(recorder.requests)
    while waited < timeout_ms and quiet < quiet_ms:
        page.wait_for_timeout(50)
        waited += 50
        if recorder.pending() or len(recorder.requests) != seen:
            quiet = 0
            seen = len(recorder.requests)
        else:
            quiet += 50


def test_after_the_splash_no_tab_asks_the_network_for_its_stylesheets_scripts_or_pictures(
        new_context, server):
    """on a fresh session, once the splash has played and its downloads are in, tapping each
    personal destination of the navigation is served from the cache"""
    context = new_context(splash=True, viewport=VIEWPORT_DESKTOP)
    try:
        # The guard's interception makes the browser skip its HTTP cache, which is what this
        # test is about; the pages used here only ask the loopback server (the map tiles
        # are not requested by the pages reached from the sidebar's first view).
        context.unroute_all()
        page = context.new_page()
        _login(page, server.base_url())
        recorder = _AssetRecorder(context, page)
        page.goto(server.base_url() + layout.HOME_ROUTE)
        page.wait_for_function(SPLASH_DONE, timeout=15000)
        page.wait_for_function(WARM_SETTLED, timeout=15000)
        page.wait_for_timeout(500)
        visited = []
        todo = [h for h in page.evaluate(NAV_HREFS, ".dashboard-sidebar a[href]")]
        # The Console is not preloaded from a personal page (its files are listed by its own
        # pages, which play no splash): only the personal destinations are tapped.
        todo = [h for h in todo if h not in ("/fleet",)]
        while todo:
            href = todo.pop(0)
            if SKIPPED.match(href) or href in visited or href == "/":
                continue
            visited.append(href)
            recorder.phase = "tap " + href
            page.locator('.dashboard-sidebar a[href="%s"]:visible' % href).first.click()
            page.wait_for_load_state("load")
            _settle(page, recorder)
            late = recorder.from_network("tap " + href)
            assert late == [], href
        assert len(visited) >= 5, visited
    finally:
        context.close()
