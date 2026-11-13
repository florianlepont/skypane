"""Real-browser check that the tab bar's pill glides on every page change.

A cross-document view transition glides the pill only when an element carrying the pill's
view-transition name exists in BOTH the old and the new page at the new page's first frame. The
sliding element is created by a deferred script, so on the new page the name must already sit on
the server-rendered active pill until the script takes over. The check reads the transition's own
animations on the new page's reveal: the pill's group must animate (old, new and group)."""
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
