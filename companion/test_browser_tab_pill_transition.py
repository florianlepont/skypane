"""Real-browser check that the tab bar's pill glides on every page change.

A cross-document view transition glides the pill only when an element carrying the pill's
view-transition name exists in BOTH the old and the new page at the new page's first frame. The
sliding element is created by a deferred script, so on the new page the name must already sit on
the server-rendered active pill until the script takes over. The check reads the transition's own
animations on the new page's reveal: the pill's group must animate (old, new and group)."""
import re

import pytest

from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED, _login, seed_state_dir

pytestmark = pytest.mark.browser

REVEAL_PROBE = """
window.addEventListener('pagereveal', (event) => {
  if (!event.viewTransition) { sessionStorage.setItem('pill-probe', 'no-transition'); return; }
  event.viewTransition.ready.then(() => {
    const pseudos = document.documentElement.getAnimations({subtree: true})
      .filter((a) => a.effect && a.effect.pseudoElement
        && a.effect.pseudoElement.indexOf('skypane-tab-slider') > -1)
      .map((a) => a.effect.pseudoElement.split('(')[0]);
    sessionStorage.setItem('pill-probe', JSON.stringify(pseudos));
  }, () => sessionStorage.setItem('pill-probe', 'transition-skipped'));
});
"""


def _settled(page):
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    page.wait_for_function("() => !!document.querySelector('.tab-bar--slider')", timeout=15000)
    page.wait_for_function(
        "() => { const e = document.querySelector('.tab-bar__link--active');"
        " const r = e.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return hit === e || e.contains(hit); }", timeout=15000)


def test_the_pill_glides_on_every_tab_change(new_context, make_app_server):
    # The Location tab is left out: its page loads map tiles from a host a test never reaches.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    context.add_init_script(REVEAL_PROBE)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        _settled(page)
        seen = []
        for _round in range(6):
            href = page.evaluate(
                "() => { const links = [...document.querySelectorAll("
                "'a.tab-bar__link:not(.tab-bar__link--active)')];"
                " const hrefs = links.map((l) => l.getAttribute('href')).filter((h) => !h.endsWith('/detection'));"
                " return hrefs[Math.floor(Math.random() * hrefs.length)]; }")
            assert href, (page.url, seen)
            page.evaluate("() => sessionStorage.removeItem('pill-probe')")
            with page.expect_navigation():
                page.click('.tab-bar__link[href="%s"]' % href)
            _settled(page)
            page.wait_for_function(
                "() => sessionStorage.getItem('pill-probe') !== null", timeout=15000)
            probe = page.evaluate("() => sessionStorage.getItem('pill-probe')")
            seen.append((href, probe))
            assert probe.startswith("["), (href, probe)
            for part in ("::view-transition-group", "::view-transition-old", "::view-transition-new"):
                assert part in probe, (href, probe)
        assert len(seen) == 6
    finally:
        context.close()


_TRACK = """
() => { const slider = document.querySelector('.tab-bar__slider');
  const t0 = performance.now();
  const tick = () => { const r = slider.getBoundingClientRect();
    window.skypaneTrack(Math.round(performance.now() - t0), r.left + r.width / 2);
    if (performance.now() - t0 < 1500) requestAnimationFrame(tick); };
  requestAnimationFrame(tick); }"""


@pytest.mark.parametrize("target,travel", [("/display", 1), ("/", -1)], ids=["forward", "back"])
def test_the_pill_never_overshoots_the_tapped_cell_while_the_page_is_late(
        new_context, make_app_server, target, travel):
    """A slow page leaves the old page frozen under the tapped tab: the pill glides straight to
    that tab and waits there, never swinging past it onto the next cell"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    samples = []
    context.expose_function("skypaneTrack", lambda t, x: samples.append((t, x)))
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + ("/" if travel > 0 else "/display"))
        _settled(page)
        held = []
        page.route(
            re.compile(r"^https?://[^/]+" + re.escape(target) + r"(\?.*)?$"),
            lambda route: held.append(route))
        link = page.locator('.tab-bar__link[href$="%s"]' % target).first
        box = link.bounding_box()
        goal = box["x"] + box["width"] / 2
        page.evaluate(_TRACK)
        link.click(no_wait_after=True)
        page.wait_for_timeout(1700)
        xs = [x for _t, x in samples]
        assert len(xs) > 10, len(xs)
        past = [(x - goal) * travel for x in xs]
        assert max(past) <= 2, ("the pill went past the tapped cell", max(past), goal, xs[::6])
        assert abs(xs[-1] - goal) <= 2, ("the pill is not on the tapped cell", xs[-1], goal)
        for route in held:
            route.abort()
    finally:
        context.close()
