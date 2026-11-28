# SPDX-License-Identifier: AGPL-3.0-only
"""The one shared "animations have settled" wait for real-browser tests.

A page-wide wait for `document.getAnimations()` to be empty hangs or flakes as
soon as an unrelated looping animation (a Home pulse, a spinner) is alive.
Every wait here ignores infinite animations and a finished or paused one, so
only a finite animation that is still running holds a test back. A target
scoped wait looks only at the animations of one element and its subtree.
"""

import time

# True when an animation is over, paused, has no effect, or never ends.
_SETTLED_ANIMATION = (
    "a => !a.effect || a.playState !== 'running'"
    " || !Number.isFinite(a.effect.getComputedTiming().endTime)")

# Expression form, for composing into a larger wait: no finite animation is
# running anywhere in the document.
DONE_EXPR = "document.getAnimations().every(" + _SETTLED_ANIMATION + ")"

# The same as a function.
ANIMATIONS_DONE = "() => " + DONE_EXPR

# The document finished loading and no finite animation is running.
SETTLED = (
    "() => document.readyState === 'complete'"
    " && " + DONE_EXPR)

# The same, except that animations inside a toast (its entrance and the 6 or 12 s dwell timer that
# runs until it hides itself) do not count. A toast is a fixed overlay, so waiting for it to go
# says nothing about the page under it; a test that needs the toast gone says so itself.
SETTLED_APART_FROM_TOASTS = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => (" + _SETTLED_ANIMATION + ")(a)"
    " || !!(a.effect && a.effect.target && a.effect.target.closest"
    " && a.effect.target.closest('.toast')))")

# Argument: a CSS selector. The element exists and no finite animation runs on
# it, its pseudo-elements or its descendants.
TARGET_SETTLED = (
    "(sel) => { const el = document.querySelector(sel); return !!el"
    " && el.getAnimations({subtree: true}).every(" + _SETTLED_ANIMATION + "); }")

# Argument: an element. The same check for an element handle.
ELEMENT_SETTLED = (
    "(el) => el.getAnimations({subtree: true}).every(" + _SETTLED_ANIMATION + ")")


def wait_settled(page, target=None, timeout=10000):
    """Wait until no finite animation runs: document-wide, or only on the
    element matching the CSS selector `target` and its subtree."""
    if target is None:
        page.wait_for_function(SETTLED, timeout=timeout)
    else:
        page.wait_for_function(TARGET_SETTLED, arg=target, timeout=timeout)


def wait_for_expression(page, expression, arg=None, timeout=10000, scripts=True):
    """Wait until the JavaScript function `expression` returns true in the page.

    `page.wait_for_function` re-checks its predicate from a page timer or an
    animation-frame callback. In a context created with `java_script_enabled=False`
    neither ever fires (the predicate is evaluated once, at the call, and the wait
    then runs until its timeout), so a page that is not yet settled at that single
    check can never be seen to settle. With `scripts=False` the check is repeated
    from here instead: every poll is a fresh `page.evaluate`, which still runs.
    """
    if scripts:
        page.wait_for_function(expression, arg=arg, timeout=timeout)
        return
    deadline = time.monotonic() + timeout / 1000
    while not page.evaluate(expression, arg):
        if time.monotonic() >= deadline:
            raise AssertionError(
                "still false after %d ms without scripts: %s" % (timeout, expression))
        page.wait_for_timeout(50)
