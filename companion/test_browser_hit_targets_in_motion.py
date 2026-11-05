"""Hit targets keep their 44px while a card is still arriving.

The cards enter with a finite fade and rise. A control inside an arriving card
must answer to at least 44px at every moment of that entrance, not only once it
has settled: the sweep of every reworked page is frozen mid-entrance at several
points of the animation timeline and every control is measured twice, by its
box (buttons, fields, summaries and the two action links) and by how far the
browser routes a pointer to it (every link, button, field, summary and label).
"""
import pytest

from companion.test_browser_overhaul_sweep import (
    _TARGETS, CASES, VIEWPORTS, _open, _seed, _target_scopes)

pytestmark = pytest.mark.browser

# Progress points of the entrance timeline where the page is frozen. Odd
# fractions on purpose: a rise that moves by a fraction of a pixel shows up there.
PHASES = (0.13, 0.37, 0.61, 0.83)

_FREEZE_AT = """
(fraction) => {
  for (const animation of document.getAnimations()) {
    const timing = animation.effect && animation.effect.getComputedTiming();
    if (!timing || timing.iterations === Infinity) continue;
    animation.pause();
    animation.currentTime = timing.delay + fraction * timing.duration;
  }
  return document.getAnimations().filter((a) => a.playState === 'paused').length;
}
"""

_BOX_HEIGHTS = """
(scopes) => {
  const sel = 'a.calendar-manage, a.login-signin, button, select, summary, '
    + 'input:not([type=hidden]):not([type=radio]):not([type=checkbox]):not([type=file])';
  const found = new Set();
  scopes.forEach((s) => document.querySelectorAll(s + ' :is(' + sel + '), ' + s + ':is(' + sel + ')')
    .forEach((e) => found.add(e)));
  const bad = [];
  for (const el of found) {
    if (!el.checkVisibility() || el.closest('dialog, .visually-hidden')) continue;
    if (el.matches('.skip-link, .brand__link') || el.closest('.dashboard-sidebar')) continue;
    if (getComputedStyle(el).display === 'inline') continue;
    const height = Math.round(el.getBoundingClientRect().height * 100) / 100;
    if (height < 44) bad.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]
      + ' ' + height);
  }
  return bad;
}
"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


@pytest.mark.parametrize("viewport", VIEWPORTS)
@pytest.mark.parametrize("persona,path,dialog", [c for c in CASES if c.values[2] is None])
def test_controls_keep_44px_at_every_point_of_the_entrance(
        new_context, server, persona, path, dialog, viewport):
    context, page = _open(new_context, server, persona, path, dialog, viewport, "fr", "dark")
    try:
        # Reload so the entrance restarts, then freeze it at each phase.
        page.reload(wait_until="commit")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        scopes = _target_scopes(dialog, viewport)
        problems = []
        for fraction in PHASES:
            page.evaluate(_FREEZE_AT, fraction)
            problems += ["%s: %s" % (fraction, p) for p in page.evaluate(_BOX_HEIGHTS, scopes)]
            problems += ["%s: %s" % (fraction, p) for p in page.evaluate(_TARGETS, scopes)]
        assert not problems, (path, viewport["width"], problems)
    finally:
        context.close()
