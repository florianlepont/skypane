#!/usr/bin/env python3
"""Computed-style probe for the companion app: a measuring instrument, not a test.

Visits the six NAV_TABS routes plus /login, at two viewport widths and both explicit
UI themes, and serialises every element's resolved `getComputedStyle()` (plus its
`::before`/`::after`) into one JSON document keyed "route|width|theme". Run once
before a CSS edit and once after, the two captures prove the served stylesheet still
paints every page identically -- a byte-for-byte `cmp` of the two files is the check.

Deliberately outside companion/: this is the instrument a CSS change is measured
against, not a behaviour the app owns, so it never appears in
companion/test_suite_guards.py's scanned-file set, and its own filename does not match
pytest's `python_files` pattern so it is never collected as a test module either.
"""
import argparse
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import companion_app_server  # noqa: E402
import companion_render_snapshot  # noqa: E402
import companion.app as companion_app  # noqa: E402
from companion import auth  # noqa: E402

# The six NAV_TABS destinations. /login is captured separately below, in its own
# unauthenticated context -- an authenticated visit to /login redirects straight to
# Home (companion/app.py's own _handle_login_get()), so it can never share a context with
# the six routes above.
ROUTES_AUTHENTICATED = (
    companion_app.HOME_ROUTE,
    companion_app.DISPLAY_ROUTE,
    companion_app.FLIGHTS_ROUTE,
    companion_app.AIRLINES_ROUTE,
    companion_app.HEALTH_ROUTE,
    companion_app.DEVICE_ROUTE,
)
LOGIN_ROUTE = companion_app.LOGIN_ROUTE

VIEWPORT_WIDTHS = (360, 1280)
VIEWPORT_HEIGHT = 900
THEMES = ("light", "dark")

EXPECTED_KEY_COUNT = (len(ROUTES_AUTHENTICATED) + 1) * len(VIEWPORT_WIDTHS) * len(THEMES)

# Runs in the browser: freezes every running CSS animation/transition (see the comment
# above _CAPTURE_JS's freeze step for why), then walks every element in document order,
# its own computed style plus its ::before/::after, as {prop: value} maps built by
# walking the live CSSStyleDeclaration by index -- never a hand-picked property list, so
# a property this file does not name today is still captured tomorrow. Custom properties
# (--*) are excluded: Chromium's indexed CSSStyleDeclaration enumeration lists every
# custom property declared on :root (inherited onto every element in the document), so
# adding, renaming or removing a token would otherwise always show up as a "computed
# style changed" false positive, even though a custom
# property by itself paints nothing; only a var() reference to it can. This mirrors
# companion/test_stylesheet_structure.py's own colour-literal check, which draws the
# identical "a declaration whose property does not start with --" boundary.
#
# A ::before/::after whose resolved `content` is "none" generates no box at all (CSS
# Generated Content: a pseudo-element with no `content` does not exist), so every one of
# its other ~500 properties is unobservable and not worth the walk -- measured at 18.5s
# and 32MB of transfer for one page's full three-way walk against 2.3s and 11MB with this
# short-circuit (companion_render_snapshot's Health page, real seeded data, 1280px).
# Marshalling the result back to Python through Playwright's own object-by-object
# protocol was the dominant cost (45s for that same page): JSON.stringify()-ing the whole
# row list in-page and returning ONE string turns that into a single string transfer.
#
# The freeze step: `prefers-reduced-motion: reduce` (set on the page below) makes
# style.css's global override shrink every animation/transition duration to 0.01ms --
# but an INFINITE animation (the breathing status dot's `skypane-pulse`) does not stop at
# 0.01ms, it just loops every 0.01ms, so two captures a wall-clock instant apart still
# land on two different, both-correct, interpolated opacity values. `document
# .getAnimations()` plus a pause-and-pin (or `.finish()` for a one-shot transition, e.g.
# a just-focused input's box-shadow reveal, which may or may not have settled by the
# time a freshly-navigated page is probed) removes the wall clock from the measurement
# entirely, in the SAME script turn as the capture below -- a separate evaluate() call
# would leave a window for a script-driven transition to start between the two.
_CAPTURE_JS = """
() => {
  document.getAnimations().forEach(a => {
    try {
      a.finish();
    } catch (e) {
      a.pause();
      a.currentTime = 0;
    }
  });
  function serialise(decl) {
    const out = {};
    for (let i = 0; i < decl.length; i++) {
      const prop = decl.item(i);
      if (prop.startsWith('--')) continue;
      out[prop] = decl.getPropertyValue(prop);
    }
    return out;
  }
  function pseudoRow(el, index, pseudo) {
    const decl = getComputedStyle(el, pseudo);
    const style = decl.getPropertyValue('content') === 'none'
      ? {content: 'none'} : serialise(decl);
    return {tag: el.tagName, index: index, pseudo: pseudo, style: style};
  }
  const rows = [];
  document.querySelectorAll('*').forEach((el, index) => {
    rows.push({tag: el.tagName, index: index, pseudo: null,
               style: serialise(getComputedStyle(el))});
    rows.push(pseudoRow(el, index, '::before'));
    rows.push(pseudoRow(el, index, '::after'));
  });
  return JSON.stringify(rows);
}
"""


def _cookie(name, value, base_url):
    # secure=False regardless of what companion/app.py itself would set: this is an
    # injected cookie, not a real Set-Cookie response, and companion/app.py reads
    # theme/session cookies straight off the request's Cookie header (auth.parse_cookies())
    # with no server-side enforcement of the Secure flag, so the flag only matters for
    # whether the BROWSER will resend it -- forcing it off keeps every route reachable
    # over the loopback-only http:// this harness uses.
    return {"name": name, "value": value, "url": base_url, "secure": False}


def snapshot(base_url, cookie):
    """Every element's computed style (see module docstring) for the six NAV_TABS
    routes plus /login, at both VIEWPORT_WIDTHS and both THEMES -- one dict keyed
    "route|width|theme" -> list of {"tag", "index", "pseudo", "style"} rows.

    `cookie` is the "name=value" session-cookie pair `companion_app_server.login()`
    returns; every authenticated route below is visited with it, and /login is always
    visited without it, in its own context.

    Every page is put into `prefers-reduced-motion: reduce` before it navigates.
    style.css's own global reduced-motion override (its ONE `*, *::before, *::after`
    block, see the sketch-findings skill's Motion section) zeroes every animation and
    transition duration under that media query, which is what makes two captures of the
    SAME stylesheet identical: without it, the breathing status dot's infinite opacity
    cycle (`skypane-pulse`) is still running at whatever phase the wall clock happens to
    land on when each capture's JS runs, and two runs a minute apart read two different
    (both correct) interpolated opacity values -- a real animation artefact, not a
    stylesheet defect, but one this determinism proof must not trip over.
    """
    from playwright.sync_api import sync_playwright

    session_name, _, session_value = cookie.partition("=")
    result = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            for width in VIEWPORT_WIDTHS:
                for theme in THEMES:
                    theme_cookie = _cookie(auth.UI_THEME_COOKIE_NAME, theme, base_url)

                    context = browser.new_context(
                        viewport={"width": width, "height": VIEWPORT_HEIGHT})
                    context.add_cookies([
                        _cookie(session_name, session_value, base_url), theme_cookie])
                    page = context.new_page()
                    page.emulate_media(reduced_motion="reduce")
                    for route in ROUTES_AUTHENTICATED:
                        page.goto(base_url + route)
                        rows = json.loads(page.evaluate(_CAPTURE_JS))
                        result["%s|%d|%s" % (route, width, theme)] = rows
                    context.close()

                    login_context = browser.new_context(
                        viewport={"width": width, "height": VIEWPORT_HEIGHT})
                    login_context.add_cookies([theme_cookie])
                    login_page = login_context.new_page()
                    login_page.emulate_media(reduced_motion="reduce")
                    login_page.goto(base_url + LOGIN_ROUTE)
                    rows = json.loads(login_page.evaluate(_CAPTURE_JS))
                    result["%s|%d|%s" % (LOGIN_ROUTE, width, theme)] = rows
                    login_context.close()
        finally:
            browser.close()
    return result


def capture(out_path):
    """Seed a fresh temporary state dir and start a real companion/app.py server against
    it (in-process, not a subprocess -- see below), log in, run snapshot(), and write the
    result to `out_path` as JSON.

    Anchored to companion_render_snapshot.FROZEN_NOW under its own frozen_clock(), the
    SAME mechanism companion/test_render_baseline.py's baseline capture uses: every
    render-time clock read companion/app.py's page-rendering call sites make is pinned to
    the instant seed_snapshot_state() itself seeded "now" as, in this SAME process (an
    InProcessAppServer, not the subprocess-based AppServer, since a monkeypatched module
    attribute has no effect across a process boundary). Without this, at least one served
    page positions a time-of-day marker (a `day_band()` drawing's current-instant mark) at
    the real wall-clock time of day, which is a genuinely different x-position every time
    this script runs -- not a stylesheet difference, but exactly the kind of accidental
    non-determinism this probe's own two-runs-must-match contract cannot tolerate.
    """
    now_iso = companion_render_snapshot.FROZEN_NOW
    with tempfile.TemporaryDirectory() as tmp_dir:
        state_dir = os.path.join(tmp_dir, "state")
        with companion_render_snapshot.frozen_clock(now_iso):
            companion_render_snapshot.seed_snapshot_state(state_dir, now_iso)
            server = companion_app_server.InProcessAppServer(state_dir)
            try:
                cookie = companion_app_server.login(server)
                data = snapshot(server.base_url(), cookie)
            finally:
                server.stop()

    assert len(data) == EXPECTED_KEY_COUNT, (
        "expected %d route|width|theme keys, got %d: %r"
        % (EXPECTED_KEY_COUNT, len(data), sorted(data)))

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, sort_keys=True)
        fh.write("\n")

    for key in sorted(data):
        print("%s: %d captured element/pseudo rows" % (key, len(data[key])))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="path to write the JSON capture to")
    args = parser.parse_args()
    capture(args.out)


if __name__ == "__main__":
    main()
