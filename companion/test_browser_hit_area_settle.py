#!/usr/bin/env python3
"""Real-browser check that the hit-area helper measures a control only once the animation or
transition carrying it has finished, and is not held up by animations that never will.
"""
import pytest

from companion.test_browser_ux_helpers import _assert_hit_target, _hit_area

pytestmark = pytest.mark.browser

PAGE = """<!doctype html><meta charset=utf-8>
<style>
  body { margin: 0; }
  #sheet { transform: scale(0.5); transition: transform 600ms linear; width: 300px; }
  #sheet.open { transform: none; }
  #go { display: block; width: 200px; height: 60px; box-sizing: border-box; padding: 0; }
  #pulse { width: 10px; height: 10px; animation: blink 400ms linear infinite; }
  @keyframes blink { from { opacity: 1 } to { opacity: .5 } }
</style>
<div id="sheet"><button id="go">Go</button></div>
<div id="pulse"></div>
"""


def _page(new_context):
    context = new_context(viewport={"width": 390, "height": 800})
    page = context.new_page()
    page.set_content(PAGE)
    return context, page


def test_the_measurement_waits_for_an_ancestor_transition_to_land(new_context):
    """a control inside a container that scales in is reported at its settled size, not at the
    shrunken size it has while the transition runs"""
    context, page = _page(new_context)
    try:
        page.evaluate("() => document.getElementById('sheet').classList.add('open')")
        mid_flight = page.evaluate(
            "() => document.getElementById('go').getBoundingClientRect().height")
        assert mid_flight < 59, "the transition must be running for this check to mean anything"
        seen = _assert_hit_target(page, "#go", "settle", minimum=44)
        assert seen["visual"] == (200.0, 60.0), seen
        assert page.evaluate("() => document.getAnimations().filter("
                             "a => a.playState === 'running' && a.transitionProperty).length") == 0
    finally:
        context.close()


def test_an_infinite_animation_does_not_hold_the_measurement_up(new_context):
    """a looping ambient animation elsewhere on the page is not waited for"""
    context, page = _page(new_context)
    try:
        assert _hit_area(page, "#pulse")["visual"] == (10.0, 10.0)
    finally:
        context.close()
