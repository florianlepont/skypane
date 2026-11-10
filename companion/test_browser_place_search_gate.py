"""The typed suggestion and the submitted search share one gate: never two address-search requests
at once, at least a second between two starts, and an Enter on a query already asked (in flight
or answered) sends nothing more. The page's fetch is wrapped to time and overlap each request;
the search host is answered by page.route (nothing reaches the network)."""
import pytest

from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, _login
from place_map_support import SETTLED, Hosts, seed as _seed

pytestmark = pytest.mark.browser

PROBE = """
(() => {
  const real = window.fetch.bind(window);
  window.__search = {starts: [], inflight: 0, maxInflight: 0, aborted: 0};
  window.fetch = (url, options) => {
    if (String(url).indexOf('nominatim') === -1) return real(url, options);
    const log = window.__search;
    log.starts.push({at: performance.now(), q: new URL(url).searchParams.get('q')});
    log.inflight += 1;
    log.maxInflight = Math.max(log.maxInflight, log.inflight);
    return new Promise((resolve, reject) => {
      let over = false;
      const finish = (fn, value) => { if (!over) { over = true; log.inflight -= 1; fn(value); } };
      const signal = options && options.signal;
      if (signal) signal.addEventListener('abort', () => {
        log.aborted += 1;
        finish(reject, new DOMException('aborted', 'AbortError'));
      });
      real(url, options).then((r) => window.setTimeout(() => finish(resolve, r), 700),
        (e) => finish(reject, e));
    });
  };
})();
"""
STATE = "() => window.__search"


READY = "() => document.documentElement.classList.contains('map-ready')"


def _open_probed(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP)
    hosts = Hosts(context)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/detection")
    page.wait_for_function(READY, timeout=15000)
    page.wait_for_function(SETTLED, timeout=10000)
    page.evaluate(PROBE)
    return context, page, hosts


def test_a_suggestion_and_the_enter_that_follows_make_one_request(new_context, make_app_server):
    context, page, hosts = _open_probed(new_context, make_app_server)
    try:
        page.locator("#place-search").press_sequentially("rue de rivoli paris", delay=20)
        page.wait_for_function("() => window.__search.starts.length === 1", timeout=5000)
        page.press("#place-search", "Enter")
        page.wait_for_function(
            "() => document.querySelector('#place-results .place-result__name')", timeout=8000)
        page.wait_for_timeout(1700)
        log = page.evaluate(STATE)
        assert len(log["starts"]) == 1 and log["maxInflight"] == 1, log
    finally:
        context.close()


def test_a_different_submit_replaces_the_suggestion_and_waits_for_the_spacing(
        new_context, make_app_server):
    context, page, hosts = _open_probed(new_context, make_app_server)
    try:
        page.locator("#place-search").press_sequentially("rue de rivoli", delay=20)
        page.wait_for_function("() => window.__search.starts.length === 1", timeout=5000)
        page.fill("#place-search", "avenue des champs elysees paris")
        page.press("#place-search", "Enter")
        page.wait_for_function("() => window.__search.starts.length === 2", timeout=8000)
        page.wait_for_function(
            "() => document.querySelector('#place-results .place-result__name')", timeout=8000)
        log = page.evaluate(STATE)
        assert log["maxInflight"] == 1 and log["aborted"] == 1, log
        gap = log["starts"][1]["at"] - log["starts"][0]["at"]
        assert gap >= 1000, log
        assert log["starts"][1]["q"] == "avenue des champs elysees paris", log
    finally:
        context.close()
