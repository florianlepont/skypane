"""Real-browser checks of the page-speed work: Home's ambient loops rest after a minute
without a touch and wake on a touch, the splash script is fetched only when the splash
plays, scripts and the stylesheet are fetched from versioned long-lived URLs that a warm
page load does not request again, and the pull-to-refresh drag is painted once per frame."""
import pytest

from companion import layout
from companion.test_browser_ux_helpers import VIEWPORT_PHONE, _login, seed_state_dir
from server import device_config

pytestmark = pytest.mark.browser



def _seed(state_dir):
    seed_state_dir(state_dir)
    device_config.save_device_config(
        state_dir, display_enabled=True, quiet_hours_enabled=False)


RUNNING_LOOPS = """() => document.getAnimations().filter((a) => {
  const t = a.effect && a.effect.getComputedTiming();
  return t && t.iterations === Infinity && a.playState === 'running'
    && a.effect.target && a.effect.target.closest(
      '.home-state__dot--pulse, .hero__picture, .hero__glass');
}).length"""


def test_the_ambient_loops_rest_after_a_minute_and_wake_on_a_touch(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    page = context.new_page()
    page.clock.install()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function("() => document.readyState === 'complete'")
    try:
        if not page.evaluate(
                "() => !!document.querySelector('.home-state__dot--pulse, .hero__picture')"):
            pytest.skip("this Home state shows no ambient loop")
        assert page.evaluate("() => document.documentElement.hasAttribute('data-ambient')") is False
        assert page.evaluate(RUNNING_LOOPS) > 0
        page.clock.fast_forward(61000)
        page.wait_for_function(
            "() => document.documentElement.getAttribute('data-ambient') === 'rest'")
        page.wait_for_function(
            "() => !document.getAnimations().some((a) => a.playState === 'running'"
            " && a.effect && a.effect.getComputedTiming().iterations === Infinity"
            " && a.effect.target && a.effect.target.closest("
            "'.home-state__dot--pulse, .hero__picture, .hero__glass'))")
        page.mouse.click(5, 300)
        page.wait_for_function(
            "() => !document.documentElement.hasAttribute('data-ambient')")
        assert page.evaluate(RUNNING_LOOPS) > 0
    finally:
        context.close()


def test_the_page_names_versioned_assets_and_the_browser_gets_long_lived_ones(
        new_context, make_app_server):
    """Every stylesheet and script the page loads is a versioned /static/ URL that the server
    answers as immutable (the guard's request interception turns the browser cache off, so
    the headers are what is checked)."""
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    page = context.new_page()
    _login(page, server.base_url())
    answers = {}
    page.on("response", lambda r: answers.update({r.url: r.headers.get("cache-control")})
            if "/static/" in r.url else None)
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'")
    page.wait_for_function(
        "() => performance.getEntriesByType('resource').filter("
        "(e) => e.name.indexOf('/static/') > -1 && e.responseEnd === 0).length === 0")
    assert any(u.split("?")[0].endswith("/static/style.css") for u in answers), answers
    for url, policy in answers.items():
        if url.endswith((".css", ".js")) or "?v=" in url:
            assert "?v=" in url, url
            assert policy == "public, max-age=31536000, immutable", (url, policy)
    context.close()


def test_the_splash_script_is_fetched_only_when_the_splash_plays(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE)
    page = context.new_page()
    _login(page, server.base_url())
    fetched = []
    page.on("request", lambda r: fetched.append(r.url) if "/static/splash.js" in r.url else None)
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'")
    page.evaluate("() => sessionStorage.setItem('skypane.splash', '1')")
    fetched.clear()
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'")
    assert fetched == []
    assert page.locator('script[src*="splash.js"]').count() == 0
    context.close()


def test_a_pull_drag_is_painted_at_most_once_per_frame(new_context, make_app_server):
    server = make_app_server(seed=_seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_PHONE, has_touch=True)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.FLIGHTS_ROUTE)
    page.wait_for_function("() => document.readyState === 'complete'")
    if not page.locator(".history-cards").count():
        pytest.skip("no flights list to pull")
    writes = page.evaluate("""async () => {
      const list = document.querySelector('.history-cards');
      let count = 0;
      const observer = new MutationObserver((records) => { count += records.length; });
      observer.observe(list, {attributes: true, attributeFilter: ['style']});
      const fire = (type, y) => document.dispatchEvent(new PointerEvent(type, {
        pointerId: 1, isPrimary: true, pointerType: 'touch', clientX: 100, clientY: y,
        bubbles: true, cancelable: true}));
      fire('pointerdown', 100);
      for (let y = 110; y < 190; y += 2) fire('pointermove', y);
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      count += observer.takeRecords().length;
      fire('pointercancel', 190);
      observer.disconnect();
      return count;
    }""")
    assert writes <= 3, writes
    context.close()
