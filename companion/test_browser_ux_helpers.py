#!/usr/bin/env python3
"""companion/test_browser_ux_helpers.py — shared constants and helpers
for companion/test_browser_ux.py and its split-off sibling harnesses
(31-01-PLAN.md Task 2).

Holds the module-level preamble relocated verbatim out of
companion/test_browser_ux.py's own lines 998-3632 (viewport constants,
seed_state_dir(), the login/save/theme/keyboard/upload/geometry probe
helpers, the quiet-hours arc decoders, and _markup_inventory()) plus
_handle_sel(), promoted from a main()-local def because it is called
both from a block a sibling harness moves out of test_browser_ux.py and
from a check that stays in test_browser_ux.py forever.

Deliberately named with a `test_` prefix so pyproject.toml's existing
`companion/test_*.py` coverage-omit glob already covers this file with
no config edit (RESEARCH.md Pitfall 3).

This is NOT a harness: it has no EXPECTED_CHECK_COUNT, no check()
closure, no main(), and must never be added to
scripts/run_all_tests.py's HARNESSES list — it has no entry point and
no check counter of its own; it exists only to be imported.
"""
import contextlib
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from companion import layout  # noqa: E402
from companion.test_companion_app import TEST_PASSWORD  # noqa: E402
from companion.pages import config_page  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import colour_rules, manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

VIEW_TRANSITION_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")
VIEW_TRANSITION_NAMES = {
    "skypane-sidebar": VIEW_TRANSITION_ROUTES,
    "skypane-title": VIEW_TRANSITION_ROUTES,
    "skypane-picture": ("/",),
}

# --- The viewport sizes this file measures at (23-02-PLAN.md Task 1) ---
# One named set replacing the inline {"width": ..., "height": ...} dicts
# this file repeated at nine call sites. 360 is here because it is the
# MINIMUM SUPPORTED VIEWPORT (developer decision 2026-09-13, recorded in
# .claude/skills/sketch-findings-skypane/SKILL.md) and until now nothing
# in this file could name it — the assertions were a mix of 320 and 390.
#
# 320 STAYS a measured width even though the contract floor is 360, and
# that is deliberate, not an oversight for a later reader to tidy away.
# SKILL.md states both of the floor's non-licences in as many words: it
# "does not license shipping something broken at 360 px", and it "does
# not mean deleting the 320 px assertions that already exist in
# companion/test_browser_ux.py. They pass today, they cost nothing, and
# they catch real defects. Keep them." The narrow rung below is that
# sentence, executable.
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 900}
# Out of contract since 2026-09-13, still measured — see above.
VIEWPORT_WIDTH_NARROW = 320
VIEWPORT_WIDTH_TABLET = 768
# The two width ladders, for the checks that build one context per width
# rather than one fixed-size context. Derived from the three sizes above
# so a width has exactly one definition in this file.
VIEWPORT_WIDTHS_RESPONSIVE = (
    VIEWPORT_MIN_SUPPORTED["width"], VIEWPORT_PHONE["width"],
    VIEWPORT_DESKTOP["width"])
VIEWPORT_WIDTHS_ALL = (
    VIEWPORT_WIDTH_NARROW, VIEWPORT_MIN_SUPPORTED["width"],
    VIEWPORT_PHONE["width"], VIEWPORT_WIDTH_TABLET,
    VIEWPORT_DESKTOP["width"])

# Fixed, deterministic — never datetime.now(). 06:00 UTC so the 17h runway
# window (06:00-23:00) and a 23:00-07:00 quiet-hours window share no
# overlap with each other by construction, keeping the two concerns
# independent in the seeded fixture.
SEED_BASE_TS = datetime(2026, 8, 1, 6, 0, 0, tzinfo=timezone.utc)


def seed_state_dir(state_dir, base_ts=SEED_BASE_TS):
    """Write 22-AUDIT.md's own methodology fixture into a fresh temp
    state directory, through the same modules companion/app.py and
    server/poll_loop.py use to write this data themselves — see this
    file's own module docstring for the full rationale and the one
    deliberate deviation (battery cadence).
    """
    runway_ids = device_config.RUNWAY_IDS
    theme_ids = device_config.THEME_IDS

    with history_db.open_db(state_dir) as conn:
        # 36 runway events over 17h.
        step = timedelta(hours=17) / 36
        for i in range(36):
            ts = base_ts + step * i
            history_db.record_runway_event(
                conn,
                ts=ts.isoformat(),
                hex="39%04x" % (0x9000 + i),
                callsign="AFR%03d" % (100 + i),
                aircraft_type="A320",
                confirmed_state="confirmed",
                corroborated=(i % 3 != 0),
                route_source="adsb" if i % 2 == 0 else "schedule",
                airline="Air France",
                origin="LFPO",
                destination="LFPG",
                tracked_runway=runway_ids[i % len(runway_ids)],
            )

        # ~40 days of battery readings, one reading per day (see the
        # module docstring's cadence note).
        for day in range(40, 0, -1):
            ts = base_ts - timedelta(days=day)
            history_db.record_device_health(
                conn, ts.isoformat(), battery_mv=4200 - day * 3,
                fw_version="1.0.0", boot_reason="wake", rssi="-60")

    device_config.save_device_config(
        state_dir, theme=theme_ids[0], tracked_runway=runway_ids[0],
        wake_interval_s=300, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00",
        display_enabled=True,
    )

    now_iso = base_ts.isoformat()

    # 2 unresolved prefixes — same registry shape
    # companion/test_status_pages.py's own _seed_unresolved_prefixes()
    # helper writes, through the identical save_poll_state() call.
    poll_loop.save_poll_state(state_dir, {"unresolved_prefixes": {
        "TVF": {
            "count": 5, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "TVF123",
        },
        "EZY": {
            "count": 2, "first_seen": now_iso, "last_seen": now_iso,
            "example_callsign": "EZY456",
        },
    }})

    # 1 manual resolution.
    manual_resolutions.add_entry(state_dir, "RYR", "Ryanair", now=now_iso)

    # 2 colour rules.
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_PREFIX, "AFR", theme_ids[0], now=now_iso)
    colour_rules.add_rule(
        state_dir, colour_rules.RULE_KIND_CALLSIGN, "EZY456", theme_ids[-1], now=now_iso)

    # 3 gallery renders, archived through poll_loop's own writer — never a
    # hand-written PNG dropped straight into the gallery directory, so the
    # on-disk filename/format contract can never drift from what a real
    # poll cycle produces.
    from PIL import Image
    # 23-10-PLAN.md Task 3 (D3/CFG-32): 600x800, not the 8x8 stand-in
    # this fixture used to write. The size is not decoration — Home's own
    # <img> declares width="600" height="800", and an 8x8 render makes
    # the loaded image's aspect ratio 1:1 against the 3:4 the markup
    # promises. A skeleton whose box differs from its image's box IS the
    # layout shift it was added to prevent, so the one fixture in this
    # repository that a browser measures that shift against cannot be the
    # one fixture whose proportions are wrong. 600x800 is the markup's
    # own declared size and the real 1200x1600 panel render's own ratio.
    canvas = Image.new("RGB", (600, 800), "white")
    for i in range(3):
        render_ts = (base_ts + timedelta(minutes=i)).isoformat()
        poll_loop._save_to_gallery(state_dir, canvas, render_ts)


def _login(page, base_url):
    """Drive the real login form through the UI (never a bare HTTP POST —
    this file exists specifically to exercise the browser), and wait for
    the post-login redirect to land.
    """
    page.goto(base_url + "/login")
    page.fill("#password", TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@contextlib.contextmanager
def _no_js_page(browser, base_url, route, viewport=None, sign_in=True,
                cookies=None):
    """A scripts-blocked browser context, signed in, landed on `route`.

    The one place in this file that blocks scripts. Three checks each
    spelled this sequence out by hand (Health, the two settings pages,
    and the login card), and 23-RESEARCH.md's Wave 0 gap list names five
    more controls that each need one; a transcribed sequence is a
    sequence that can be transcribed WRONG, and a scripts-blocked proof
    that quietly ran with scripts enabled would pass while proving
    nothing. Keeping the flag to a single call site is what makes that
    failure mode unavailable rather than merely unlikely.

    `sign_in=False` exists for the login card, whose whole subject is the
    unauthenticated page: it asserts what /login renders with scripts
    blocked and THEN signs in as its last act. That is not a weaker use
    of the helper, it is the only honest one for a check about signing
    in.

    `viewport` is optional and defaults to the Playwright default the
    three converted checks already ran under, so converting them changes
    nothing at all. Pass VIEWPORT_MIN_SUPPORTED to measure a
    scripts-blocked control at the 360px contract floor.

    `cookies` is applied to the context BEFORE the sign-in navigation,
    which is the only order that works for a cookie the first rendered
    document already has to honour — the UI-language cookie being the
    live case. It exists because 23-05's freshness check needed exactly
    that and, lacking it, opened this file's SECOND
    `java_script_enabled=False` context by hand, quietly undoing the one
    property the paragraph above claims. 25-02 added the parameter and
    converted that check back rather than let the claim stay untrue.

    `context.close()` runs in a finally, the discipline every check in
    this file already follows by hand.
    """
    extra = {} if viewport is None else {"viewport": viewport}
    context = browser.new_context(java_script_enabled=False, **extra)
    try:
        if cookies:
            context.add_cookies(cookies)
        page = context.new_page()
        if sign_in:
            page.goto(base_url + "/login")
            page.fill("#password", TEST_PASSWORD)
            page.click('button[type="submit"]')
            page.wait_for_load_state("load")
        page.goto(base_url + route)
        yield page
    finally:
        context.close()


def _click_control(page, selector):
    """Click a checkbox/radio input through the browser's own native
    .click() method (JS-level, not Playwright's mouse-coordinate click).

    Every checkbox/radio this file's checks click below is visually
    hidden (config_page.py's own selectable-card idiom: a
    visually-hidden native input wrapped in a full-card <label>), via
    `clip-path: inset(50%)` (companion/static/style.css's own
    .visually-hidden rule) — which clips the element's paintable AND
    hit-testable area to nothing. A coordinate-based click (Playwright's
    own `locator.click()`, even with `force=True`) dispatches at that
    point and can silently land on whatever the browser's hit-test
    resolves to there instead (confirmed live: it left the target
    control unchecked with no error). `element.click()` is the DOM's own
    "activation behaviour" algorithm — it runs regardless of paint/hit-
    test visibility and is what every real assistive-technology/keyboard
    activation path already relies on for this exact selectable-card
    pattern, so it is the correct thing to call here, not a workaround.
    """
    page.eval_on_selector(selector, "el => el.click()")


def _guard_armed(page):
    """T1: whether dirty-state.js's beforeunload guard is currently
    armed, tested by constructing a real, cancelable `beforeunload`
    Event object in-page and dispatching it directly on window, then
    reading `defaultPrevented` — never by trying to trigger an actual
    navigation and observe a native "leave site?" dialog, which
    Chromium suppresses/auto-resolves under Playwright and which
    Playwright's own `dialog` event does not reliably surface for
    beforeunload specifically. Dispatching the Event directly still
    exercises dirty-state.js's own real listener (the one registered via
    `window.addEventListener("beforeunload", ...)`) with no change to
    that file — this is a black-box behavioural probe, not an internal
    read of the private `suppressGuard` variable.
    """
    return page.evaluate(
        "() => { var e = new Event('beforeunload', {cancelable: true}); "
        "window.dispatchEvent(e); return e.defaultPrevented; }")


# --- 28-10-PLAN.md (CFG-77/CFG-78): the restored dirty bar's own wait
# helpers, replacing the retired auto-save status region's
# (27-04-PLAN.md's `_SAVE_STATUS_SEL`/`_save_status_text()`/
# `_wait_for_save_status()`/`_wait_for_saved()`/`_wait_for_saving()`,
# all deleted outright by this plan — [data-save-status] no longer
# exists, 28-08-PLAN.md Task 1).
#
# The idiom carries forward unchanged from the 27-04 block comment this
# one replaces: the bar's own words are read off its OWN data-dirty-*
# attributes (D-06's idiom, restated by companion/static/dirty-state.js's
# own header) rather than hardcoded here in English, so a check works
# unchanged whichever shipped language the page is in.
def _wait_for_bar(page, timeout=5000):
    """Waits, via wait_for_function (never a sleep), for [data-dirty-bar]
    to LOSE its `hidden` attribute — the bar revealing itself the moment
    dirty-state.js's own updateBar() has recorded at least one real
    difference from the page's load-time snapshot (countDifferences() >
    0). Resolves on the real DOM condition, never a guessed instant.
    """
    page.wait_for_function(
        "() => {"
        " var el = document.querySelector('[data-dirty-bar]');"
        " return !!el && !el.hidden;}",
        timeout=timeout)


def _wait_for_bar_hidden(page, timeout=5000):
    """The inverse of `_wait_for_bar()`. The restored model has a HIDDEN
    state that genuinely matters — a fresh script-enabled load, the
    moment after Annuler, the moment after Save's own navigation lands —
    and the auto-save suite this replaces had no equivalent state at
    all, so this helper is genuinely NEW rather than a rename of a
    retired one.
    """
    page.wait_for_function(
        "() => {"
        " var el = document.querySelector('[data-dirty-bar]');"
        " return !!el && el.hidden;}",
        timeout=timeout)


def _bar_text(page):
    """Reads `[data-dirty-count]`'s own textContent — the bar's section-
    naming copy, in whatever language the page is in.
    """
    return page.eval_on_selector("[data-dirty-count]", "el => el.textContent")


def _save_via_bar(page, timeout=5000):
    """Clicks the bar's own Save (the relocated, AST-provably-
    unconditional `[data-static-save-fallback]` native submit,
    `form="settings-form"`-attached) and waits for the REAL navigation
    it causes — never a same-page DOM update. A successful save 303-
    redirects to the scoped page's own GET route
    (`_settings_saved_redirect()`); a rejected save re-renders the SAME
    page directly at 200, carrying the user's own submission and each
    offending field's inline error (`_handle_settings_post()`). Either
    way the browser navigates.

    THIS IS THE SINGLE BIGGEST BEHAVIOURAL DIFFERENCE from the retired
    `_wait_for_saved()`: that helper waited for a WORD to appear in a
    region on the SAME page; this one waits for the page to actually go
    away and come back. Any DOM handle or read captured BEFORE this call
    is STALE the instant it returns — re-query by selector afterwards,
    never reuse a reference taken before the click.
    """
    with page.expect_navigation(timeout=timeout):
        page.click("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)


def _commit_field(page, selector):
    """Fires the real `change` event dirty-state.js's own document-level
    listener is waiting for — MEASURED necessary, not decorative:
    Playwright's own `locator.fill()` dispatches `input` only (its
    documented contract), never `change`, so a field filled and left
    there stays UNCOMMITTED by this app's own D-04 definition (change,
    not input, is what auto-save listens for). Real keyboard typing
    followed by a real Tab/blur also produces a genuine `change` and
    does not need this helper — this one is for the `.fill()` shape,
    the same shape value-controls.js's own notify() dispatches for a
    drag/keyboard interaction on a custom control.
    """
    page.eval_on_selector(
        selector, "el => el.dispatchEvent(new Event('change', {bubbles: true}))")


# --- 24-02-PLAN.md (CFG-45): the three shared measurement helpers the
# four drawing plans (24-04..24-08) each need, added BEFORE the drawings
# rather than after them. Helpers only: this plan registers no check of
# its own and EXPECTED_CHECK_COUNT is unchanged at 54.
#
# Why they are here at all. Until this block, this file — the only
# harness in the repository that renders anything — had never once
# switched theme: `grep -c data-ui-theme companion/test_browser_ux.py`
# was 0 across twenty-three phases, so every dark-mode claim this project
# has made rested on READING style.css rather than on rendering it. The
# single most predictable defect in a set of server-rendered SVG drawings
# is one that is correct in light mode and invisible in dark, and no
# source scan can see it: the markup can be structurally perfect and
# still paint wrong once the cascade, `currentColor` and a theme token
# have had their say.

# The explicit themes this harness can drive, derived from the app's own
# vocabulary (layout.UI_THEME_CHOICES) rather than restated as literals,
# so a call site reads as the thing it means and a renamed choice fails
# here instead of silently measuring nothing.
#
# "auto" is excluded ON PURPOSE and is not an oversight: style.css's own
# header comment (the CFG-09 theme-resolution paragraph) states that
# `data-ui-theme="auto"` intentionally has no override rule of its own,
# so the media query keeps governing and the resolved theme becomes
# whatever the host OS says. That is precisely the one thing a
# measurement must not depend on, so asking for it is an error rather
# than a third mode.
UI_THEME_AUTO = "auto"
UI_THEMES_EXPLICIT = tuple(
    t for t in layout.UI_THEME_CHOICES if t != UI_THEME_AUTO)

# Set an explicit theme, sample the paint it produces, and leave the page
# on the requested one. Every read below goes through getComputedStyle,
# which is a forced style flush: the browser must resolve every pending
# recalculation before it can answer, so THE READ IS THE WAIT. There is
# no sleep, no timeout and no transitionend listener anywhere in this
# helper, for the same reason 23-02 recorded when it put the disclosure
# sweep under reduced motion — a timing wait is a flakiness generator on
# the slowest file in the suite, and an intermittently red check is worse
# than no check.
#
# `document.body` is the witness because style.css's own `body` rule is
# where both inverting tokens are actually SPENT (`background:
# var(--color-canvas)`, `color: var(--color-text)`), so this reads real
# paint rather than a custom property's declared text — a
# getPropertyValue('--color-canvas') would return the token's literal
# string even if nothing on the page ever used it.
_THEME_PROBE = (
    "args => {"
    "  const html = document.documentElement;"
    "  const sampled = {};"
    "  const read = () => {"
    "    const s = getComputedStyle(document.body);"
    "    return {canvas: s.backgroundColor, text: s.color,"
    "            attr: html.getAttribute('data-ui-theme')};"
    "  };"
    "  args.themes.forEach(t => {"
    "    html.setAttribute('data-ui-theme', t);"
    "    sampled[t] = read();"
    "  });"
    "  html.setAttribute('data-ui-theme', args.settle);"
    "  return {sampled: sampled, settled: read()};"
    "}")


def _set_ui_theme(page, theme):
    """Put an already-loaded `page` into an explicitly named theme and
    return the resolved paint that theme produces. The first thing in
    this harness that has ever measured dark mode.

    Returns {"theme", "canvas", "text"} — `canvas` and `text` are the
    browser's own resolved `background-color`/`color` on <body>, in
    Chromium's `rgb(r, g, b)` form, ready to be compared between themes
    or recorded in a SUMMARY.

    THE EXPLICIT ATTRIBUTE, NOT `emulate_media`. The next reader's
    instinct will be `context.new_context(color_scheme="dark")` or
    `page.emulate_media(color_scheme="dark")`, and that is the weaker
    test here. `html[data-ui-theme="light"|"dark"]` is what this app's
    OWN theme picker sets (companion/app.py's theme form ->
    layout.page_shell()'s <html> attribute), and style.css declares those
    two blocks specifically so they TAKE PRECEDENCE over
    prefers-color-scheme. Driving the OS preference would exercise a
    path the app deliberately lets the user override, and would leave the
    measurement at the mercy of the host's own setting; driving the
    attribute exercises the path a real visitor takes and is
    deterministic. Both halves matter, which is why this comment states
    both.

    IT MUST KEEP WORKING WITH SCRIPTS BLOCKED. "renders correctly in dark
    mode with scripts blocked" is the combination most likely to be
    wrong, so it is the one the drawing plans have to be able to ask
    about. Measured on this tree: a context built with
    `java_script_enabled=False` (which is what `_no_js_page()` composes)
    still answers `page.evaluate` — Playwright's evaluation runs through
    the debugging protocol rather than through the page's own script
    execution, and CSS cascade/recalculation is not gated on scripts at
    all. Light and dark resolved to the identical pair of values with
    scripts on and with scripts blocked.

    THE HELPER VERIFIES THE PAGE REALLY REPAINTED, and that is the whole
    point of it rather than a nicety. A helper that set the attribute and
    returned would let every later dark-mode assertion pass VACUOUSLY:
    if the override rule were renamed, dropped, or outranked, both themes
    would resolve to the same paint and a "these two differ" check
    downstream would be comparing a value to itself. So this helper
    samples BOTH explicit themes on every call and refuses to return
    unless the two genuinely differ in BOTH inverting tokens. It is
    deliberately not a literal-value assertion: hardcoding #F7F4EF /
    #0C0F14 here would duplicate style.css into a harness and would start
    failing on a palette change that is not a defect. What is asserted is
    the PROPERTY the two override blocks exist to produce.
    """
    if theme not in UI_THEMES_EXPLICIT:
        raise AssertionError(
            "_set_ui_theme: %r is not one of this app's explicit themes %r. "
            "%r is excluded on purpose — it declares no override rule of its "
            "own (style.css's CFG-09 theme-resolution comment), so it "
            "resolves to whatever the host OS prefers, which is the one "
            "thing a measurement must not depend on."
            % (theme, UI_THEMES_EXPLICIT, UI_THEME_AUTO))

    seen = page.evaluate(
        _THEME_PROBE,
        {"themes": list(UI_THEMES_EXPLICIT), "settle": theme})
    sampled = seen["sampled"]
    missing = [t for t in UI_THEMES_EXPLICIT if t not in sampled]
    if missing:
        raise AssertionError(
            "_set_ui_theme: the probe returned no sample for %r — with none, "
            "this helper measures nothing" % (missing,))

    first, second = UI_THEMES_EXPLICIT[0], UI_THEMES_EXPLICIT[1]
    for token in ("canvas", "text"):
        if sampled[first][token] == sampled[second][token]:
            raise AssertionError(
                "_set_ui_theme: setting html[data-ui-theme] did not repaint "
                "the page — %s resolved to %r in BOTH %r and %r, so the "
                "explicit CFG-09 override is not reaching <body> and every "
                "dark-mode assertion built on this helper would be comparing "
                "a value to itself (style.css's html[data-ui-theme=\"%s\"] / "
                "html[data-ui-theme=\"%s\"] blocks)"
                % (token, sampled[first][token], first, second, first, second))

    settled = seen["settled"]
    if settled["attr"] != theme:
        raise AssertionError(
            "_set_ui_theme: asked for %r, the document element reports %r "
            "after the switch" % (theme, settled["attr"]))
    if (settled["canvas"], settled["text"]) != (
            sampled[theme]["canvas"], sampled[theme]["text"]):
        raise AssertionError(
            "_set_ui_theme: the page did not settle on the theme it was "
            "asked for — %r sampled %r but the page came to rest on %r"
            % (theme, sampled[theme], settled))

    return {"theme": theme, "canvas": settled["canvas"],
            "text": settled["text"]}


# The values Chromium computes for the SVG paint properties when NOTHING
# in the cascade reaches the element — the SVG initial values (`fill:
# black`, `stroke: none`). This pair is the signature of the exact defect
# the drawing plans exist to catch: a shape that inherited no colour and
# painted the SVG default instead of a theme token.
#
# `rgb(0, 0, 0)` is a usable sentinel on THIS app specifically, and that
# is a measured fact rather than an assumption: neither theme's
# --color-text is pure black (light #17191F -> rgb(23, 25, 31), dark
# #F1F3F6 -> rgb(241, 243, 246)), so a shape meant to be painted by a
# token can never legitimately land on it.
SVG_DEFAULT_PAINT = {"fill": "rgb(0, 0, 0)", "stroke": "none"}

_PAINT_PROBE = (
    "args => {"
    "  const el = document.querySelector(args.selector);"
    "  if (!el) return null;"
    "  const s = getComputedStyle(el);"
    "  const out = {};"
    "  args.props.forEach(p => { out[p] = s.getPropertyValue(p); });"
    "  return out;"
    "}")


def _computed_paint(page, selector, props=("fill", "stroke", "color")):
    """Read the RESOLVED paint the browser computed for the first element
    matching `selector` — never the attribute, never the class.

    Returns {"selector", <prop>: value, ..., "svg_default": (props,)}.

    WHAT THIS BUYS OVER A SOURCE SCAN, which is the only reason it is
    worth the browser it costs. A scan of the rendered markup can see
    that a `<line>` carries `class="sparkline-line"`; it cannot see what
    that class RESOLVES to. getComputedStyle has already run the cascade,
    resolved `currentColor` against the inherited `color`, and
    substituted the theme's custom property — so this is the only thing
    in the repository that can tell a shape painted by a token from a
    shape painted by the SVG default. Measured live on
    `.sparkline-line`, whose rule is `stroke: currentColor`: light
    resolves stroke to rgb(23, 25, 31), dark to rgb(241, 243, 246), and
    the same element with its class removed resolves to stroke `none`
    with fill `rgb(0, 0, 0)`. No source scan distinguishes those three.

    `svg_default` names, for the caller, every requested property whose
    resolved value is indistinguishable from that property's SVG initial
    value — so four plans do not each have to recognise the defect for
    themselves and then each get the sentinel slightly different. Read it
    for what it says: INDISTINGUISHABLE FROM THE INITIAL VALUE. A shape
    that legitimately declares `stroke: none` (a fill-only shape) reports
    `stroke` here too, which is correct and not a false positive — a
    caller asserting "this must be token-painted" should assert on the
    property it expects to carry the token, and `.sparkline-line`'s own
    `fill: none` is exactly why this helper reports properties rather
    than a single verdict.

    Raises rather than returning a sentinel when the selector matches
    nothing. This file's checks guard against measuring an empty page
    everywhere they can ("with none, this check measures nothing"), and a
    returned `None` is a guard each of four call sites has to REMEMBER;
    an exception is one they cannot forget, and `check()` above turns it
    into a named FAIL rather than a swallowed pass.
    """
    props = tuple(props)
    seen = page.evaluate(
        _PAINT_PROBE, {"selector": selector, "props": list(props)})
    if seen is None:
        raise AssertionError(
            "_computed_paint: no element matched %r on %s — with none, this "
            "measures nothing" % (selector, page.url))
    out = {"selector": selector}
    defaulted = []
    for prop in props:
        value = seen.get(prop)
        out[prop] = value
        if prop in SVG_DEFAULT_PAINT and value == SVG_DEFAULT_PAINT[prop]:
            defaulted.append(prop)
    out["svg_default"] = tuple(defaulted)
    return out


# WHICH BOX MEANS "THE PAGE". `document.documentElement`, matching the
# two page-level overflow checks this file already carries
# (`_home_paints_nothing_outside_the_viewport_or_its_cards` and
# `_every_disclosure_on_every_page_opens_without_overflow`, both of which
# compare documentElement.scrollWidth against the viewport) — a third
# convention in the same file is how three checks come to disagree about
# what "the page" means.
#
# Measured before choosing, not assumed: at 360/390/1280 on Health with
# every disclosure open, `document.body` and `document.documentElement`
# report the SAME pair of numbers, clean (360/360) and with a 2000px
# element appended to <body> (2000/360). body's own `overflow-x: hidden`
# (style.css's body rule, UXA-01's guaranteed fix) does NOT clip its own
# scrollWidth, because CSS propagates a body overflow to the viewport
# when <html>'s is `visible` and leaves body's own used value `visible`.
# So the two boxes agree today and the choice is settled by consistency
# with the file's existing checks rather than by a measured difference.
#
# THE DELIBERATELY-SCROLLABLE WRAP IS NOT A PAGE OVERFLOW, and this
# helper gets that right by construction rather than by a special case:
# 260913-cz6 recorded that a `.data-table-wrap` overflowing its own box
# leaves documentElement.scrollWidth EXACTLY unmoved, and that was
# re-measured here — a 2000px element appended INSIDE a
# `.data-table-wrap` takes that wrap from 278 to 2000 while the document
# stays at 360/360 and this helper reports clean. `_health_tables_fit_
# their_wraps_with_every_disclosure_open` is the check that owns the
# wrap-level question; this helper must not contradict it, and does not.
#
# The escaped-element list is DIAGNOSTIC ONLY and is never an independent
# failure condition. CFG-45's wording is "no horizontal scrollbar on the
# page body", so that — and only that — is what this helper asserts; a
# helper that quietly also failed on content escaping an
# `overflow: hidden` card would be doing more than its name says to four
# calling plans. Naming what escaped is still what makes the failure
# actionable, so it rides along in the message.
_PAGE_OVERFLOW_PROBE = (
    "() => {"
    "  const vw = document.documentElement.clientWidth;"
    "  const escaped = [];"
    "  document.querySelectorAll('*').forEach(el => {"
    "    const r = el.getBoundingClientRect();"
    "    if (r.width > 0 && r.right > vw + 0.5)"
    "      escaped.push(el.className.toString().trim() || el.tagName);"
    "  });"
    "  return {sw: document.documentElement.scrollWidth,"
    "          cw: vw,"
    "          escaped: [...new Set(escaped)].slice(0, 12)};"
    "}")


# 24-04-PLAN.md Task 4: the ring's own INK, in viewBox user units.
# getBBox() reports the shape's geometry box and deliberately EXCLUDES
# the stroke, so the resolved stroke-width is read alongside it and half
# of it added on every side here, in the open — that half-stroke is the
# whole property under test, and hiding it inside a getBBox() option
# dictionary would also mean assuming that dictionary is supported.
_RING_INK_PROBE = (
    "args => {"
    "  const svg = document.querySelector(args.selector);"
    "  if (!svg) return null;"
    "  const vb = svg.viewBox.baseVal;"
    "  const shapes = [];"
    "  svg.querySelectorAll('circle, path, rect, line').forEach(el => {"
    "    const b = el.getBBox();"
    "    const w = parseFloat(getComputedStyle(el).strokeWidth) || 0;"
    "    shapes.push({cls: el.getAttribute('class'), strokeWidth: w,"
    "                 inked: [b.x - w / 2, b.y - w / 2,"
    "                         b.x + b.width + w / 2, b.y + b.height + w / 2]});"
    "  });"
    "  return {viewBox: [vb.width, vb.height], shapes: shapes};"
    "}")

# Each Home status tile's own box, the height its CONTENT actually needs
# (the union of its children's rects, which `.dashboard-grid`'s stretch
# cannot inflate), and whether it holds a ring.
_TILE_CONTENT_PROBE = (
    "() => [...document.querySelectorAll('.home-status-grid .stat-tile')].map(t => {"
    "  const r = t.getBoundingClientRect();"
    "  let min = Infinity, max = -Infinity;"
    "  [...t.children].forEach(c => {"
    "    const k = c.getBoundingClientRect();"
    "    min = Math.min(min, k.top); max = Math.max(max, k.bottom);"
    "  });"
    "  return {height: r.height, contentH: max - min,"
    "          hasRing: t.querySelectorAll('.drawing-ring-value').length};"
    "})")


def _assert_no_page_overflow(page, where, expected_width=None):
    """Whether the page itself scrolls horizontally. Returns "" when it
    does not, and a finished failure sentence naming BOTH measurements
    when it does — the `_assert_clean` idiom this file already uses for
    exactly this job, so a caller writes `msg = ...; if msg: return
    False, msg` and every drawing plan's overflow failure reads the same.

    `where` names the surface being measured and nothing else — a route
    or page name ("Home", "/health in fr"). The width is appended by this
    helper from its own measurement, matching the existing checks'
    "%s scrolls sideways at %dpx" wording, so a caller that folds the
    width into `where` gets it twice.

    `expected_width` is optional and, when given, asserts the measurement
    was really taken at the viewport the caller believes it built — the
    same "expected the measurement to be taken at %dpx" guard both
    existing overflow checks spell out by hand, so a context that
    silently came up at another size cannot produce a green measurement.

    The comparison is documentElement.scrollWidth against
    documentElement.clientWidth, strictly greater, no tolerance. The two
    existing page-level checks compare against the width they REQUESTED
    because they have one in scope; a helper handed only a page does not,
    and clientWidth is the same number in every measurement this file has
    ever taken (360/360, 390/390, 1280/1280 — re-measured on this tree).
    It is also the viewport's own content box, which is the box a
    horizontal scrollbar would appear for, and the number both existing
    checks already print beside scrollWidth in their own messages.
    """
    seen = page.evaluate(_PAGE_OVERFLOW_PROBE)
    if expected_width is not None and seen["cw"] != expected_width:
        return (
            "%s: expected the measurement to be taken at %dpx, the document "
            "reports a client width of %d"
            % (where, expected_width, seen["cw"]))
    if seen["sw"] > seen["cw"]:
        return (
            "%s scrolls sideways at %dpx: documentElement.scrollWidth %d "
            "against a client width of %d, painted past the right edge by "
            "%r (CFG-45's page-body floor)"
            % (where, seen["cw"], seen["sw"], seen["cw"], seen["escaped"]))
    return ""


# --- 25-02-PLAN.md (CFG-52): the four control-contract helpers the five
# control plans (25-03..25-07) each need, written ONCE, before any of the
# five controls exists. Helpers only: this plan registers no check of its
# own and EXPECTED_CHECK_COUNT is unchanged at 65.
#
# Why they are here at all, and why the FIRST of them is the one that
# matters. Phase 25 replaces five bare fields with richer controls, and
# every one of them owes the same four proofs: it is operable with
# scripts blocked, it is operable from the keyboard with no pointer at
# all, its hit target survives the 360px floor, and it is legible in both
# themes. Written out five times by hand, that is five chances to
# transcribe a sequence WRONG — which is the exact argument
# `_no_js_page()`'s own docstring already makes about the flag it owns.
#
# THE NO-JS PROOF FOR A CONTROL IS NOT "IT RENDERS". A control can render
# perfectly with scripts blocked and save nothing whatsoever: Phase 22
# found exactly that (a fallback Save that was rendered and had a
# zero-size box), and a phase that replaces five inputs can ship it five
# times over. So the first helper below operates the control, submits the
# real form it belongs to, reloads, and reads the value back FROM DISK.
# Reading it back from the reloaded DOM alone would still pass against a
# server that echoed the submission straight back without storing it, and
# stopping at "the page navigated" would pass against a control that
# saves nothing at all.


# ---------------------------------------------------------------------
# 1. Operate, submit, PERSIST — with scripts blocked.
# ---------------------------------------------------------------------

# Locate every form control posting under one `name`, set it by the
# browser's OWN mechanism, and report what happened — never a
# Playwright coordinate interaction.
#
# The kind is dispatched on the control's own `type`, so a call site says
# what it means ("this field must end up holding this value") and the
# helper picks `el.click()` for a radio/checkbox and a `.value`
# assignment for everything else. `_click_control()`'s docstring is the
# precedent and its reasoning carries verbatim: the radios this phase's
# controls are built over are `clip-path: inset(50%)` visually-hidden,
# which clips their hit-testable area to nothing, so a coordinate click
# lands on whatever the hit-test resolves to instead. The DOM's own
# activation behaviour is what every keyboard/assistive path already
# uses for this pattern and is what works here.
#
# Controls are collected by comparing `.name` rather than through a
# `[name="..."]` attribute selector, so a field name needing CSS escaping
# can never turn a real subject into a silent zero-match.
_OPERATE_PROBE = (
    "args => {"
    "  const all = [...document.querySelectorAll('input, select, textarea')]"
    "    .filter(e => e.name === args.field);"
    "  if (!all.length) return {error: 'no-control',"
    "    names: [...new Set([...document.querySelectorAll("
    "      'input, select, textarea')].map(e => e.name).filter(Boolean))]};"
    "  const kind = (all[0].type || '').toLowerCase();"
    "  let target;"
    "  if (kind === 'radio' || kind === 'checkbox') {"
    "    target = all.find(e => e.value === args.value);"
    "    if (!target) return {error: 'no-option',"
    "      options: all.map(e => e.value), kind: kind};"
    "    if (!target.checked) target.click();"
    "  } else {"
    "    target = all[0];"
    "    target.value = args.value;"
    "  }"
    "  const held = (kind === 'radio' || kind === 'checkbox')"
    "    ? ((all.find(e => e.checked) || {}).value === undefined ? null"
    "       : all.find(e => e.checked).value)"
    "    : target.value;"
    "  const form = target.form;"
    "  if (!form) return {error: 'no-form', kind: kind, held: held};"
    "  const invalid = [...form.elements]"
    "    .filter(e => e.willValidate && !e.checkValidity())"
    "    .map(e => (e.name || e.id || e.tagName) + ': ' + e.validationMessage);"
    "  const submits = [...document.querySelectorAll("
    "      'button, input[type=submit], input[type=image]')]"
    "    .filter(b => b.form === form"
    "      && (b.type || '').toLowerCase() === 'submit' && !b.disabled);"
    "  const visible = submits.filter(b => b.getClientRects().length);"
    "  return {kind: kind, held: held, invalid: invalid,"
    "          action: form.getAttribute('action'),"
    "          submits: submits.length, visible: visible.length};"
    "}")

# The submission itself, re-resolving the form from the same field name
# so nothing has to be carried across the two evaluations.
#
# A VISIBLE submit button is preferred over `form.requestSubmit()`, and
# that preference is the point rather than an implementation detail: the
# button a scripts-blocked visitor can actually press is the always-
# rendered fallback Save, and Phase 22's P0 was precisely that button
# being rendered with a zero-size box. Going through it means this helper
# exercises the control AND the one affordance that submits it. `click()`
# is the DOM's activation behaviour, so it carries the submitter's own
# name/value (which several of this app's forms post) and still runs
# native constraint validation — `form.submit()` would skip both, and is
# deliberately not used anywhere here.
_SUBMIT_PROBE = (
    "args => {"
    "  const all = [...document.querySelectorAll('input, select, textarea')]"
    "    .filter(e => e.name === args.field);"
    "  const form = all.length && all[0].form;"
    "  if (!form) return 'no-form';"
    "  const submits = [...document.querySelectorAll("
    "      'button, input[type=submit], input[type=image]')]"
    "    .filter(b => b.form === form"
    "      && (b.type || '').toLowerCase() === 'submit' && !b.disabled);"
    "  const chosen = submits.filter(b => b.getClientRects().length)[0]"
    "    || submits[0];"
    "  if (chosen) { chosen.click(); return 'submitter'; }"
    "  form.requestSubmit();"
    "  return 'requestSubmit';"
    "}")

_READ_FIELD_PROBE = (
    "args => {"
    "  const all = [...document.querySelectorAll('input, select, textarea')]"
    "    .filter(e => e.name === args.field);"
    "  if (!all.length) return null;"
    "  const kind = (all[0].type || '').toLowerCase();"
    "  if (kind === 'radio' || kind === 'checkbox') {"
    "    const on = all.find(e => e.checked);"
    "    return on ? on.value : '';"
    "  }"
    "  return all[0].value;"
    "}")


def _persist_without_js(browser, base_url, route, field, value, read_back,
                        viewport=None, restore=True, shows_back=True,
                        cookies=None):
    """Operate a native control with scripts blocked, submit the real
    form it belongs to, reload the route, and prove the value SURVIVED —
    on disk, not merely on the page.

    Returns {"field", "set", "held", "reloaded", "stored", "before",
    "submitted_via", "restored"} on success. RAISES AssertionError on
    every failure, `_set_ui_theme()`'s shape and for its reason: a helper
    that returned a verdict string would hand five calling plans a guard
    each of them has to REMEMBER, and `check()` turns a raised
    AssertionError into a named FAIL that nobody can forget.

    THE ASSERTION IS ON THE RELOADED, RE-READ VALUE — NEVER THE POSTED
    ONE, and that is the entire reason this helper exists rather than the
    three-line sequence it replaces. Three weaker sequences all pass
    against a broken control:
      * "the input is present with scripts blocked" passes against a
        control that saves nothing — the Phase 22 defect exactly;
      * "the page navigated after submit" passes against a POST the
        server rejected on validation and redirected straight back from;
      * "the reloaded page shows the value" passes against a server that
        echoes a rejected submission back into the field (which
        `wake_interval_group()` deliberately DOES, by design, for D-07).
    So the verdict is `read_back()` — a caller-supplied reader that goes
    to the real state directory through the app's own loader. The
    reloaded DOM is measured too, and reported, but it is corroboration.

    `read_back` is a zero-argument callable returning the stored value;
    it is compared as text (`str()`), because a field posts "300" and
    `device_config` stores `300`, and a helper that failed on that would
    only teach its callers to pre-stringify.

    `shows_back=True` (the default) additionally corroborates that the
    reloaded page SHOWS the saved value back, which is what makes a
    setting visible to the visitor who made it. It is a parameter rather
    than an always-on clause because this app has a deliberate,
    documented exception: `notifications_topic_url` is write-only by
    design (T-20-12 — never echoed, never masked, in any state), so it
    stores correctly and renders empty forever. Measured on this tree:
    with the default it raises on that field and with `shows_back=False`
    it passes, which is the right answer in both cases. The DISK read is
    never optional — it is the verdict.

    `restore=True` (the default) puts the setting back the way it found
    it as this helper's LAST act, through the identical operate-submit
    sequence — never a direct write to the state directory, which would
    be a second way of changing settings living in a harness. The
    fixture is shared by every check in this file and a helper that left
    a real setting changed would be a test that edits its own
    neighbours' subject (T-25-02-A).

    `cookies` is a straight passthrough to `_no_js_page()`'s own
    parameter, added by 25-03 for one reason: D-09's floor has to hold in
    BOTH shipped languages, and the UI language is a cookie the FIRST
    rendered document already has to honour. A passthrough rather than a
    second sequence — this helper's whole value is that the five control
    plans measure saving the same way, and a plan that needed a cookie
    and hand-rolled its own operate-submit-reload would have re-opened
    exactly the transcription risk `_no_js_page()` exists to close. It
    reaches the restore pass too, so a French-language measurement puts
    the setting back through the French page.

    It runs entirely inside `_no_js_page()` and opens no context of its
    own — the one scripts-blocked call site in this file stays one.
    """
    before = read_back()
    result = _persist_once(
        browser, base_url, route, field, value, read_back, viewport,
        shows_back, cookies)
    result["before"] = before
    result["restored"] = None
    if restore and before is not None and str(before) != str(value):
        back = _persist_once(
            browser, base_url, route, field, str(before), read_back, viewport,
            shows_back, cookies)
        result["restored"] = back["stored"]
    return result


def _upload_without_js(browser, base_url, route, input_selector, submit_selector,
                       source_path, read_back, serve_path, viewport=None,
                       cookies=None):
    """`_persist_without_js()`'s FILE-INPUT VARIANT, added by 25-07 and
    stated as a variant rather than smuggled in as a second sequence.

    WHY A VARIANT AT ALL, since the whole point of 25-02's helper is that
    five control plans measure saving the same way. `_persist_without_js()`
    operates its control by ASSIGNING TO `.value` through `_OPERATE_PROBE`,
    and `<input type="file">` is the one native control in this app whose
    `.value` a script may not write — that restriction is the browser's,
    not this app's, and no amount of parameterising gets around it. The
    file is put in through the browser's own file-chooser plumbing
    (`page.set_input_files()`, which is CDP's `DOM.setFileInputFiles` and
    works perfectly well with scripts blocked) and the form is submitted
    by clicking its real submit button.

    EVERYTHING ELSE IS 25-02'S DISCIPLINE, DELIBERATELY UNCHANGED:

      * It runs entirely inside `_no_js_page()` and opens no context of
        its own, so this file's one scripts-blocked call site stays one.
      * THE VERDICT IS READ BACK FROM DISK, never from the page. A POST
        the server rejected on validation redirects straight back to a
        page that looks exactly like success — this app even has a named
        flash key for it (`illustration_rejected`) — so "the browser
        navigated" proves nothing at all.
      * It additionally fetches `serve_path` BY NAVIGATING TO IT and
        reading the navigation response's own body, and returns those
        bytes too. For an upload that is the clause that matters and it
        has no counterpart in the field case: an illustration that is
        stored but not SERVED is a setting nobody can see, and D19's
        whole promise is a picture on a card.

        BY NAVIGATION, AND NOT THROUGH `page.request`, WHICH WAS
        MEASURED WRONG HERE. `page.request` is documented as sharing the
        browser context's cookie jar; on this tree's Playwright it does
        not send `sp_session`, so an authenticated fetch through it
        follows the redirect to /login and comes back **200 with a
        1493-byte HTML page**. A check asserting "200" on that would
        have passed against the login screen. A navigation carries the
        session cookie and reports the route's real status, so that is
        what this helper uses.

    Returns {"before_len", "landed", "stored", "stored_len",
    "served_status", "served", "served_len", "gate"}. RAISES
    AssertionError on every failure, `_persist_without_js()`'s shape and
    for its reason.

    `read_back` is a zero-argument callable returning the stored BYTES,
    or None when nothing is stored — a caller-supplied reader going to
    the real state directory, exactly as in the field case.
    """
    before = read_back()
    with _no_js_page(browser, base_url, route, viewport=viewport,
                     cookies=cookies) as page:
        found = page.locator(input_selector).count()
        if found != 1:
            raise AssertionError(
                "_upload_without_js: %r matches %d element(s) on %s with scripts blocked — the "
                "file input must be rendered UNCONDITIONALLY, and with none this helper measures "
                "nothing" % (input_selector, found, route))
        page.set_input_files(input_selector, source_path)
        with page.expect_navigation():
            page.click(submit_selector)
        landed = page.url
        served = page.goto(base_url + serve_path)
        result = {
            "before_len": None if before is None else len(before),
            "landed": landed,
            "served_status": served.status,
            "served": served.body(),
        }
    result["served_len"] = len(result["served"])
    stored = read_back()
    if stored is None:
        raise AssertionError(
            "_upload_without_js: nothing was stored after a scripts-blocked upload of %r through "
            "%r on %s — the browser navigated to %r, which is exactly what a REJECTED upload "
            "looks like from outside. A control that renders without scripts and stores nothing "
            "is the D-09 defect this helper exists to catch"
            % (source_path, input_selector, route, result["landed"]))
    if result["served_status"] != 200:
        raise AssertionError(
            "_upload_without_js: %r stored %d bytes but %s answers %d — an illustration that is "
            "saved and not served is a picture nobody can see"
            % (source_path, len(stored), serve_path, result["served_status"]))
    result["stored"] = stored
    result["stored_len"] = len(stored)
    return result


def _persist_once(browser, base_url, route, field, value, read_back, viewport,
                  shows_back, cookies=None):
    """One operate-submit-reload-verify pass. Split out only so
    `_persist_without_js()`'s restore step is the SAME sequence as its
    measurement rather than a second, hand-written one.
    """
    with _no_js_page(browser, base_url, route, viewport=viewport,
                     cookies=cookies) as page:
        seen = page.evaluate(_OPERATE_PROBE, {"field": field, "value": value})
        error = seen.get("error")
        if error == "no-control":
            raise AssertionError(
                "_persist_without_js: no form control posts under name %r on "
                "%s with scripts blocked — with none, this helper measures "
                "nothing. The names that page does post are %r"
                % (field, route, seen["names"]))
        if error == "no-option":
            raise AssertionError(
                "_persist_without_js: the %r group on %s has no option with "
                "value %r; its options are %r"
                % (field, route, value, seen["options"]))
        if error == "no-form":
            raise AssertionError(
                "_persist_without_js: the %r control on %s belongs to no "
                "<form>, so with scripts blocked there is nothing that can "
                "post it at all" % (field, route))
        if str(seen["held"]) != str(value):
            raise AssertionError(
                "_persist_without_js: the browser refused to put %r into %r "
                "on %s — it holds %r after the native set, so the submission "
                "below would have measured the wrong value"
                % (value, field, route, seen["held"]))
        if seen["invalid"]:
            raise AssertionError(
                "_persist_without_js: %r cannot be submitted with %r in %r — "
                "native constraint validation rejects %r, and a browser "
                "silently refuses to submit an invalid form rather than "
                "reporting an error"
                % (seen["action"], value, field, seen["invalid"]))
        if not seen["submits"]:
            raise AssertionError(
                "_persist_without_js: the form posting %r on %s renders no "
                "enabled submit control at all, so a visitor with scripts "
                "blocked has no way to save it (D-09)" % (field, route))

        with page.expect_navigation():
            via = page.evaluate(_SUBMIT_PROBE, {"field": field})

        # A genuine second GET, not page.reload() — the redirect the save
        # lands on is not necessarily the route under test, and what the
        # next visitor sees is this route fetched fresh.
        page.goto(base_url + route)
        reloaded = page.evaluate(_READ_FIELD_PROBE, {"field": field})

    stored = read_back()
    if stored is None or str(stored) != str(value):
        raise AssertionError(
            "_persist_without_js: %r did NOT persist with scripts blocked — "
            "it was set to %r and submitted (via the %s), and the stored "
            "value still reads back as %r (the reloaded page shows %r). A "
            "control that renders without scripts and saves nothing is the "
            "D-09 defect this helper exists to catch"
            % (field, value, via, stored, reloaded))
    if shows_back and (reloaded is None or str(reloaded) != str(value)):
        raise AssertionError(
            "_persist_without_js: %r stored %r but the reloaded %s does not "
            "show it back — the field reads %r with scripts blocked, so the "
            "saved setting is invisible to the visitor who made it"
            % (field, stored, route, reloaded))
    return {"field": field, "set": value, "held": seen["held"],
            "submitted_via": via, "visible_submits": seen["visible"],
            "reloaded": reloaded, "stored": stored}


# ---------------------------------------------------------------------
# 2. Keyboard-only operation, with the pointer-free claim MEASURED.
# ---------------------------------------------------------------------

# Arm a capture-phase recorder for every pointer-ish event on the
# document, then (separately) read it back and then prove it was alive.
#
# WHY A RECORDER AT ALL, when this helper simply does not call a pointer
# API. Because "I did not click" is a statement about the harness, and
# the property under test is a statement about the CONTROL: that a
# keyboard-only visitor can operate it. A helper that merely avoided
# clicking would still pass against a control reachable only by mouse,
# because it would never notice that the value it read had been changed
# by something other than the keys it pressed. The recorder turns "no
# pointer was involved" from the harness's promise into the page's own
# measurement.
# A `click` IS NOT A POINTER EVENT, AND THIS DISTINCTION IS NOT
# PEDANTRY — IT IS MEASURED ON THIS TREE AND IT DECIDES WHETHER THIS
# HELPER IS USABLE AT ALL. Pressing ArrowDown inside a native radiogroup
# moves the selection and, as part of the selected radio's ACTIVATION
# BEHAVIOUR, fires a real `click` event on it. The first version of this
# recorder logged `click` unconditionally, and it duly reported that the
# existing runway radiogroup — the single behaviour D16's runway map and
# D5's carousel both inherit for free — "was driven with ['ArrowDown']
# and 1 pointer event(s) fired ... ['click:INPUT']". That verdict is
# wrong, and a helper that returns it would have taught this phase to
# stop using the keyboard behaviour it is built on.
#
# The discriminator is the event's own provenance, not its name.
# UI Events gives a pointer-driven `click` a `detail` of at least 1 (the
# click count) and a `pointerType` of "mouse"/"pen"/"touch"; a click
# synthesized by keyboard activation or by `el.click()` carries
# `detail === 0` and an empty `pointerType`. So `click`/`dblclick`/
# `contextmenu` are logged ONLY when they carry that provenance, and
# every genuinely pointer-only event (pointer*/mouse*/touch*) is logged
# unconditionally. Verified in both directions below: a real
# `locator.click()` is caught, and a keyboard ArrowDown is not.
_POINTER_RECORDER_ARM = (
    "() => {"
    "  window.__skypanePointerLog = [];"
    "  if (!window.__skypanePointerArmed) {"
    "    const always = ['pointerdown','pointerup','pointermove',"
    "      'mousedown','mouseup','mousemove','touchstart','touchend'];"
    "    const onlyIfPointerDriven = ['click','dblclick','contextmenu'];"
    "    const log = (t, e) => window.__skypanePointerLog.push("
    "      t + ':' + (e.target && (e.target.id || e.target.tagName))"
    "      + '(detail=' + e.detail + ',pointerType=' + (e.pointerType || '')"
    "      + ')');"
    "    always.forEach(t => document.addEventListener("
    "      t, e => log(t, e), true));"
    "    onlyIfPointerDriven.forEach(t => document.addEventListener(t, e => {"
    "      if (e.detail > 0 || (e.pointerType && e.pointerType !== ''))"
    "        log(t, e);"
    "    }, true));"
    "    window.__skypanePointerArmed = true;"
    "  }"
    "  return true;"
    "}")

_POINTER_RECORDER_READ = "() => (window.__skypanePointerLog || []).slice()"

# The recorder's OWN proof of life, dispatched only AFTER the measurement
# above has been taken, so it can never pollute what it verifies.
_POINTER_RECORDER_SELFTEST = (
    "args => {"
    "  const el = document.querySelector(args.selector) || document.body;"
    "  el.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true}));"
    "  const n = (window.__skypanePointerLog || []).length;"
    "  window.__skypanePointerLog = [];"
    "  return n;"
    "}")

_FOCUS_PROBE = (
    "args => {"
    "  const el = document.querySelector(args.selector);"
    "  if (!el) return {error: 'no-element'};"
    "  el.focus();"
    "  const a = document.activeElement;"
    "  return {focused: !!a && (a === el || el.contains(a)),"
    "          active: a ? (a.id || a.getAttribute('value') || a.tagName) : null};"
    "}")

_KEYBOARD_RESULT_PROBE = (
    "args => {"
    "  const el = document.querySelector(args.selector);"
    "  const a = document.activeElement;"
    "  const name = el && el.name;"
    "  let group = null;"
    "  if (name) {"
    "    const on = [...document.querySelectorAll('input, select, textarea')]"
    "      .filter(e => e.name === name)"
    "      .find(e => (e.type === 'radio' || e.type === 'checkbox')"
    "                 ? e.checked : true);"
    "    group = on ? on.value : null;"
    "  }"
    "  return {value: el ? el.value : null,"
    "          checked: el ? !!el.checked : null,"
    "          group: group,"
    "          active: a ? (a.id || a.getAttribute('value') || a.tagName) : null,"
    "          activeIsInside: !!a && !!el && (a === el || el.contains(a)),"
    "          activeName: a ? a.name || null : null,"
    "          activeValue: a ? a.getAttribute('value') : null};"
    "}")


def _operate_with_keyboard(page, selector, keys):
    """Drive a control with the keyboard ALONE and report what it did,
    having measured that not one pointer event fired while doing it.

    Returns {"selector", "keys", "value", "checked", "group", "active",
    "pointer_events", "recorder_proved"}. Raises AssertionError when the
    element cannot be focused, when a pointer event DID fire, or when the
    recorder could not prove itself (below).

    FOCUS IS TAKEN WITH `el.focus()`, NOT A CLICK. That is the DOM's own
    focusing method — no pointer event of any kind is generated by it —
    and it is the same reasoning `_click_control()` records for using the
    element's own API instead of a coordinate interaction.

    THE KEYS ARE PRESSED THROUGH `page.keyboard`, NOT DISPATCHED AS
    SYNTHETIC KeyboardEvents, and this is load-bearing rather than
    stylistic: the single most important keyboard behaviour this phase
    depends on — arrow keys moving the selection inside a native
    radiogroup, which is what D16's runway map and D5's carousel both
    inherit for free — is implemented by the browser's own default action
    and runs only for TRUSTED events. A `dispatchEvent(new
    KeyboardEvent('keydown', {key: 'ArrowDown'}))` is untrusted, moves
    nothing, and would make this helper report that a perfectly good
    radiogroup is not keyboard-operable.

    THE RECORDER PROVES ITSELF, IN THIS ORDER: arm, measure (must be
    empty), then dispatch one synthetic pointer event and confirm the
    recorder caught it (must not be empty). Without that last step the
    pointer-free claim would be vacuous in exactly the case where it is
    easiest to get wrong — a context where the listener never ran at all
    would report "zero pointer events" forever.

    MEASURED ON THIS TREE, AND THE REASON THIS HELPER REFUSES TO RUN
    WITH SCRIPTS BLOCKED: in a `java_script_enabled=False` context,
    listeners registered through `page.evaluate` are installed (the array
    is really there and really readable afterwards) but NEVER FIRE — a
    Tab walk moves focus and an `el.click()` still activates, and the log
    stays empty regardless. `getComputedStyle` and CSS recalculation are
    not gated on scripts, which is why `_set_ui_theme()` works there, but
    listener callbacks are. So in that context the recorder's self-test
    fails and this helper raises rather than returning a green
    pointer-free verdict it cannot back up. Keyboard operation of a
    control that needs no script is proven by
    `_persist_without_js()` instead; this helper's subject is the
    enhanced control, which has scripts by definition.
    """
    page.evaluate(_POINTER_RECORDER_ARM)

    focus = page.evaluate(_FOCUS_PROBE, {"selector": selector})
    if focus.get("error") == "no-element":
        raise AssertionError(
            "_operate_with_keyboard: no element matched %r on %s — with none, "
            "this helper measures nothing" % (selector, page.url))
    if not focus["focused"]:
        raise AssertionError(
            "_operate_with_keyboard: %r did not take focus from el.focus() — "
            "the document element in focus is %r. A control a keyboard user "
            "cannot focus is a control they cannot operate, whatever a mouse "
            "can do with it" % (selector, focus["active"]))

    for key in keys:
        page.keyboard.press(key)

    seen = page.evaluate(_KEYBOARD_RESULT_PROBE, {"selector": selector})
    fired = page.evaluate(_POINTER_RECORDER_READ)
    proved = page.evaluate(
        _POINTER_RECORDER_SELFTEST, {"selector": selector})

    if fired:
        raise AssertionError(
            "_operate_with_keyboard: %r was driven with %r and %d pointer "
            "event(s) fired during the sequence — %r. A keyboard proof that "
            "a pointer took part proves nothing about a keyboard-only "
            "visitor" % (selector, list(keys), len(fired), fired))
    if not proved:
        raise AssertionError(
            "_operate_with_keyboard: the pointer recorder never fired for its "
            "own synthetic pointerdown on %r, so the 'zero pointer events' "
            "result above measured nothing. Listeners do not run in a "
            "scripts-blocked context; use _persist_without_js() there"
            % (selector,))

    return {"selector": selector, "keys": list(keys),
            "value": seen["value"], "checked": seen["checked"],
            "group": seen["group"], "active": seen["active"],
            "active_is_inside": seen["activeIsInside"],
            "active_name": seen["activeName"],
            "active_value": seen["activeValue"],
            "pointer_events": fired, "recorder_proved": proved}


# ---------------------------------------------------------------------
# 3. The hit area the browser really hit-tests, at a real viewport.
# ---------------------------------------------------------------------

# The established touch-target floor, in both axes
# (.claude/skills/sketch-findings-skypane/references/control-density.md,
# and the same 44 the `.copy-btn`/`.row-toggle` ::before synthesis and
# the global `input, select` rule are both built to reach). Named once
# here so five control plans do not each retype it.
MIN_HIT_TARGET_PX = 44

# Measure the visual box, confirm the centre is genuinely reachable, then
# find how far past each edge the browser still resolves a hit to this
# element.
#
# THE TECHNIQUE, RECORDED HERE BECAUSE A LATER READER WILL OTHERWISE
# "SIMPLIFY" IT BACK INTO A WRONG MEASUREMENT. `getBoundingClientRect()`
# alone is not the hit area, in either direction:
#   * it UNDERSTATES a synthesized target. `.copy-btn` is a 22x22 box
#     whose `::before` carries `inset: -11px`, making the real target
#     44x44. A pseudo-element has no box of its own in the DOM and no
#     rect to read; the only thing that knows about it is the hit-test.
#   * it OVERSTATES an occluded one. A perfectly-sized rectangle covered
#     by a sticky bar, an overlay or a later-painted sibling is a control
#     nobody can press, and its rect says 44x44 regardless.
# `document.elementFromPoint()` answers both, because it IS the browser's
# hit-test: it returns the element that would receive a pointer
# interaction at a point, pseudo-elements resolving to their generating
# element. So the centre is probed first (occlusion), and then each edge
# is pushed outwards by binary search for as long as the hit still
# resolves to this element or a descendant of it (synthesis).
#
# Reading `getComputedStyle(el, '::before')`'s insets instead — which one
# existing check in this file does by hand — measures the DECLARATION,
# not the hit test. It cannot see an occluder, it cannot see a
# `pointer-events: none` on the pseudo-element, and it has to know in
# advance which pseudo-element to ask about.
#
# The search is bounded by `max` and monotonic by construction (an inset
# hit area is a rectangle), and it reports `clipped` when a probe left
# the viewport — at which point the measurement is a floor, not the
# answer, and a caller comparing it against 44 is still safe because a
# clipped measurement can only be too SMALL.
_HIT_AREA_PROBE = (
    "args => {"
    "  const el = document.querySelector(args.selector);"
    "  if (!el) return {error: 'no-element'};"
    "  el.scrollIntoView({block: 'center', inline: 'center'});"
    "  const r = el.getBoundingClientRect();"
    "  if (!r.width || !r.height)"
    "    return {error: 'no-box', visual: [r.width, r.height]};"
    "  const owns = n => !!n && (n === el || el.contains(n));"
    "  const vw = document.documentElement.clientWidth;"
    "  const vh = document.documentElement.clientHeight;"
    "  const inView = (x, y) => x >= 0 && y >= 0 && x < vw && y < vh;"
    "  const cx = Math.floor(r.left + r.width / 2) + 0.5;"
    "  const cy = Math.floor(r.top + r.height / 2) + 0.5;"
    "  if (!inView(cx, cy))"
    "    return {error: 'off-screen', visual: [r.width, r.height]};"
    "  const at = document.elementFromPoint(cx, cy);"
    "  if (!owns(at))"
    "    return {error: 'occluded', visual: [r.width, r.height],"
    "            by: at ? (at.className.toString().trim() || at.tagName)"
    "                   : null};"
    "  let clipped = false;"
    "  const ownsAt = (x, y) =>"
    "    inView(x, y) && owns(document.elementFromPoint(x, y));"
    "  const reach = (dx, dy, span) => {"
    "    const limit = Math.ceil(span / 2) + args.max;"
    "    let lo = 0, hi = limit + 1;"
    "    if (ownsAt(cx + dx * hi, cy + dy * hi)) return hi;"
    "    while (hi - lo > 1) {"
    "      const mid = (lo + hi) >> 1;"
    "      if (ownsAt(cx + dx * mid, cy + dy * mid)) lo = mid; else hi = mid;"
    "    }"
    "    if (!inView(cx + dx * (lo + 1), cy + dy * (lo + 1))) clipped = true;"
    "    return lo;"
    "  };"
    "  const left = reach(-1, 0, r.width), right = reach(1, 0, r.width);"
    "  const up = reach(0, -1, r.height), down = reach(0, 1, r.height);"
    "  return {visual: [r.width, r.height],"
    "          reach: [left, right, up, down],"
    "          hit: [left + right + 1, up + down + 1],"
    "          clipped: clipped,"
    "          viewport: [vw, vh]};"
    "}")


def _hit_area(page, selector, max_expand=64):
    """The element's VISUAL box and the box the browser actually
    hit-tests to it, both axes, at whatever viewport `page` is at.

    Returns {"selector", "visual": (w, h), "hit": (w, h), "reach":
    (left, right, up, down), "clipped", "viewport"}. Raises
    AssertionError when the selector matches nothing, when the element
    has no box at all, or when its own centre point hit-tests to
    something else — an occluded control, which is the failure a
    rectangle measurement is blind to.

    Read the module comment above this function before changing it: the
    `elementFromPoint` probing is the whole measurement, and
    `getBoundingClientRect()` on its own would report `.copy-btn` as
    22x22 when its real target is 44x44.

    THE SEARCH COUNTS WHOLE PIXELS, OUTWARDS FROM THE CENTRE, SAMPLED AT
    THEIR CENTRES, AND THE ANSWER IS A PIXEL COUNT. Both halves of that
    were arrived at by measuring rather than by taste:
      * A FRACTIONAL binary search inflates every answer by about a
        pixel, because `elementFromPoint` resolves to the pixel grid — a
        312.0-wide <h1> reported 312.97. On a 44px floor a systematic
        +1 is the difference between passing a 43px target and failing
        it, so the search is over integers.
      * Each pixel is sampled at its own CENTRE (x + 0.5), which asks
        the unambiguous question "does THIS pixel route a pointer to the
        control?" rather than the ambiguous one about a box edge.
    THE ANSWER CAN EXCEED THE CSS BOX BY ABOUT A PIXEL PER AXIS, and that
    is the browser rather than this probe: a box whose edges land off the
    pixel grid has its hit region snapped outwards, so the row toggle's
    22x22 visual box and -11px `::before` inset measure 45x45 rather than
    44x44, and a 96x44 `<input>` measures 97x45. Those pixels really do
    route a pointer to the control — a click at them lands on it — so the
    number is the truth about this rendering and not an error to be
    corrected away. It does mean a floor comparison is permissive by up
    to a pixel: a control measuring exactly 44 here could be 43 in CSS.
    Do not trust the last pixel of this measurement; do trust the
    difference between 22 and 44, which is what it exists to tell apart.

    Probing outward FROM THE CENTRE (rather than inward from each edge)
    is what makes the search monotonic without having to guess a starting
    point that is definitely inside the box.

    THE ELEMENT IS SCROLLED TO THE CENTRE OF THE VIEWPORT FIRST, and that
    is a correctness measure rather than a convenience. A hit-test is
    meaningless off-screen, and — measured here — `#wake-interval-s` at
    360px reports its centre hit-testing to `tab-bar__pill`, the fixed
    bottom tab bar, purely because of where the page happened to be
    scrolled. An occlusion verdict that depends on scroll position is an
    intermittently-red check, which is worse than no check. After
    centring, an `occluded` result means a real overlay rather than a
    scroll accident.

    `max_expand` bounds the outward search. 64 is comfortably past the
    44px floor and past the 11px-per-side synthesis this app uses, and
    keeps a control that happens to sit inside a large clickable parent
    from reporting that parent's size — the search stops at this element,
    but only because `owns()` requires the hit to BE this element or a
    descendant, never an ancestor.
    """
    seen = page.evaluate(
        _HIT_AREA_PROBE, {"selector": selector, "max": max_expand})
    error = seen.get("error")
    if error == "no-element":
        raise AssertionError(
            "_hit_area: no element matched %r on %s — with none, this "
            "measures nothing" % (selector, page.url))
    if error == "no-box":
        raise AssertionError(
            "_hit_area: %r renders with a zero-size box %r, so there is no "
            "hit area to measure at all — the Phase 22 P0 shape exactly (a "
            "control rendered and unpressable)" % (selector, seen["visual"]))
    if error == "off-screen":
        raise AssertionError(
            "_hit_area: %r's centre lies outside the viewport, so the browser "
            "cannot be asked what it hit-tests there. Scroll it into view "
            "before measuring" % (selector,))
    if error == "occluded":
        raise AssertionError(
            "_hit_area: %r measures %r but its own centre point hit-tests to "
            "%r instead — the control is not reachable by pointer where it "
            "is drawn, and a bounding-box measurement would have reported it "
            "as fine. Three causes measured on this tree, all of which leave "
            "the rect intact: something painted over it; a collapsed "
            "disclosure (`max-height: 0; overflow: hidden` clips the paint "
            "and keeps the boxes); and `pointer-events: none` at rest (the "
            "Flights copy buttons, revealed on `tr:hover`/`tr:focus-within`) "
            "— for that last one, put the control into the state it is meant "
            "to be pressed in before measuring"
            % (selector, seen["visual"], seen["by"]))
    return {"selector": selector,
            "visual": tuple(seen["visual"]), "hit": tuple(seen["hit"]),
            "reach": tuple(seen["reach"]), "clipped": seen["clipped"],
            "viewport": tuple(seen["viewport"])}


# 25-07-PLAN.md Task 3 (CFG-51/D19): a REAL, TRUSTED file drop.
#
# WHY CDP AND NOT page.dispatch_event(). panel-lookup.js's drop handler
# refuses an event whose `isTrusted` is false — 25-01's value-controls.js
# closes the same exposure for its own control — and every drop a page
# script can construct is untrusted by definition. The obvious harness
# recipe (build a DataTransfer in the page, dispatch a synthetic "drop")
# therefore measures the refusal and nothing else.
#
# Chromium's DevTools protocol dispatches drag events through the same
# input pipeline a real pointer uses, with a `files` list the browser
# turns into genuine File objects. Measured on this tree: the handler
# sees `isTrusted: true` and `dataTransfer.files.length === 1`. So the
# guard stays, AND the gesture is measured end to end — which is the
# only combination that proves both.
#
# The drag-over state is sampled BETWEEN dragOver and drop, i.e. while
# the browser is genuinely in the state, rather than at a guessed
# instant after a sleep. An intermittently-red check is worse than none.
def _drop_files(page, selector, paths):
    """Dispatch a trusted file drop of `paths` onto `selector`'s centre.

    Returns {"active_during_drag", "active_after_drop", "paint_during_drag",
    "paint_at_rest"} — the attribute the stylesheet keys its drag state
    on, sampled on both sides of the drop, plus the resolved paint in
    each state so "the state is visible" is a measurement rather than a
    class name.
    """
    box = page.locator(selector).bounding_box()
    if not box or not box["height"]:
        raise AssertionError(
            "_drop_files: %r has no box on %s, so there is nowhere to drop — a drop target that "
            "is not drawn is not a drop target" % (selector, page.url))
    x = box["x"] + box["width"] / 2
    y = box["y"] + box["height"] / 2
    data = {"items": [], "files": list(paths), "dragOperationsMask": 1}
    client = page.context.new_cdp_session(page)
    seen = {"paint_at_rest": _drop_zone_paint(page, selector)}
    for kind in ("dragEnter", "dragOver"):
        client.send("Input.dispatchDragEvent",
                    {"type": kind, "x": x, "y": y, "data": data})
    seen["active_during_drag"] = page.locator(selector).get_attribute(
        "data-upload-drop-active") is not None
    seen["paint_during_drag"] = _drop_zone_paint(page, selector)
    client.send("Input.dispatchDragEvent",
                {"type": "drop", "x": x, "y": y, "data": data})
    seen["active_after_drop"] = page.locator(selector).get_attribute(
        "data-upload-drop-active") is not None
    return seen


def _drop_zone_paint(page, selector):
    """The zone's own resolved background plus its preview frame's
    resolved border, as the browser computed them — never the class."""
    return page.evaluate(
        "sel => { const z = document.querySelector(sel);"
        "  const p = z.querySelector('.upload-drop__preview');"
        "  const zs = getComputedStyle(z), ps = getComputedStyle(p);"
        "  return {background: zs.backgroundColor,"
        "          borderStyle: ps.borderTopStyle,"
        "          borderColor: ps.borderTopColor}; }", selector)


def _await_upload_zone(page, selector):
    """Wait for a gated drop zone to become genuinely visible, and when
    it does not, say WHY rather than reporting a rectangle.

    A zone can be invisible for four unrelated reasons that a bare
    `wait_for_selector` timeout cannot tell apart: the `.js` gate never
    opened (nav-dropdown.js did not run), the shared dialog never opened
    (no matching resolve trigger), panel-lookup.js hid the upload zone
    because the card's mode is not `needs-artwork`, or the element is
    genuinely absent. Each one has a different fix, so each one gets
    named here.
    """
    try:
        page.wait_for_selector(selector, state="visible", timeout=10000)
        return
    except Exception:
        pass
    seen = page.evaluate(
        "sel => { const d = document.getElementById('panel-lookup-dialog');"
        "  const z = document.querySelector(sel);"
        "  const zone = z ? z.closest('.resolve-upload-zone') : null;"
        "  return {htmlClass: document.documentElement.className,"
        "          dialogOpen: d ? d.open : null,"
        "          zoneHidden: zone ? zone.hidden : null,"
        "          gateDisplay: z ? getComputedStyle(z).display : null,"
        "          resolvePrefixes: [...document.querySelectorAll("
        "            '[data-view-panel-resolve-prefix]')].map(e =>"
        "              e.getAttribute('data-view-panel-resolve-prefix') + ':' +"
        "              e.getAttribute('data-view-panel-mode'))"
        "            .filter(s => !s.startsWith(':'))}; }", selector)
    raise AssertionError(
        "_await_upload_zone: %r never became visible on %s — %r"
        % (selector, page.url, seen))


def _upload_zone_state(page, selector):
    """Everything about one drop zone a check ever wants to assert."""
    return page.evaluate(
        "sel => { const z = document.querySelector(sel);"
        "  const i = document.getElementById(z.getAttribute('data-upload-drop-input'));"
        "  const im = z.querySelector('.upload-drop__image');"
        "  const pv = z.querySelector('.upload-drop__preview').getBoundingClientRect();"
        "  return {files: i.files ? i.files.length : -1,"
        "          name: i.files && i.files[0] ? i.files[0].name : null,"
        "          size: i.files && i.files[0] ? i.files[0].size : null,"
        "          message: z.querySelector('.upload-drop__message').textContent,"
        "          imageHidden: im.hidden,"
        "          imageScheme: (im.getAttribute('src') || '').split(':')[0],"
        "          natural: [im.naturalWidth, im.naturalHeight],"
        "          preview: [pv.width, pv.height],"
        "          action: i.form.getAttribute('action')}; }", selector)


def _assert_hit_target(page, selector, where, minimum=MIN_HIT_TARGET_PX):
    """`_hit_area()` plus the floor, so five control plans do not each
    retype the comparison and get the axis or the number slightly
    different. Returns the measurement; raises when either axis is under
    `minimum`.
    """
    seen = _hit_area(page, selector)
    w, h = seen["hit"]
    if w < minimum or h < minimum:
        raise AssertionError(
            "%s: %r's hit area measures %dx%d at %dpx, under the %dpx floor "
            "in %s (its visual box is %.1fx%.1f and it reaches %r pixels "
            "left/right/up/down of its own centre)"
            % (where, selector, w, h, seen["viewport"][0], minimum,
               "both axes" if (w < minimum and h < minimum)
               else ("the x axis" if w < minimum else "the y axis"),
               seen["visual"][0], seen["visual"][1], seen["reach"]))
    return seen


# ---------------------------------------------------------------------
# 4. The `.js` gate, asserted in BOTH directions.
# ---------------------------------------------------------------------

# The tabbable-candidate vocabulary, in one place. `[tabindex]` is
# included and then filtered on its resolved value rather than matched as
# `[tabindex="-1"]` in the selector, because a programmatically-set
# `el.tabIndex = -1` leaves no attribute to match.
_FOCUSABLE_CANDIDATE_SELECTOR = (
    "a[href], area[href], button, input, select, textarea, summary, "
    "iframe, object, embed, audio[controls], video[controls], "
    "[tabindex], [contenteditable]")

_GATE_BOX_PROBE = (
    "args => {"
    "  const els = [...document.querySelectorAll(args.selector)];"
    "  if (!els.length) return {error: 'no-element'};"
    "  const boxes = els.map(e => {"
    "    const r = e.getBoundingClientRect();"
    "    return [r.width, r.height];"
    "  });"
    "  const candidates = els.reduce((n, e) =>"
    "    n + e.querySelectorAll(args.focusable).length"
    "      + (e.matches(args.focusable) ? 1 : 0), 0);"
    "  return {boxes: boxes, count: els.length, candidates: candidates,"
    "          tabbable: document.querySelectorAll(args.focusable).length};"
    "}")

# Where focus currently is, and whether it is inside the gated wrapper.
# Read after every single Tab press, because a `focusin` recorder — the
# obvious optimisation — does not fire at all in a scripts-blocked
# context, which is the only context this walk is ever taken in.
# The walk's own cycle detector MARKS THE ELEMENT rather than comparing a
# name, because names collide: the first version stopped after 24 of a
# page's 44 tab stops, having decided it had come back round when two
# different controls merely shared a class string. A mark is identity,
# and a walk that stops early is a walk that never reaches the stops it
# was looking for.
_ACTIVE_PROBE = (
    "args => {"
    "  const a = document.activeElement;"
    "  if (!a || a === document.body)"
    "    return {where: null, inside: false, seen: false};"
    "  const seen = a.hasAttribute('data-skypane-tab-seen');"
    "  a.setAttribute('data-skypane-tab-seen', '');"
    "  const inside = [...document.querySelectorAll(args.selector)]"
    "    .some(e => e === a || e.contains(a));"
    "  return {where: (a.id || a.name || a.className.toString().trim()"
    "                  || a.tagName), inside: inside, seen: seen};"
    "}")


def _assert_js_gate(browser, base_url, route, selector, viewport=None,
                    prepare=None, arm=None, tab_budget=None):
    """Prove a `.js`-gated wrapper in BOTH directions: it occupies no
    space and holds nothing a keyboard can reach when scripts are
    blocked, AND it occupies space when they are not.

    Returns {"blocked": {...}, "enabled": {...}}; raises AssertionError
    on either direction.

    BOTH DIRECTIONS, BECAUSE ONLY ONE OF THEM IS THE DEFECT PEOPLE
    REMEMBER. Asserting only the blocked half passes perfectly against a
    gate that is stuck shut and never reveals anything at all — a control
    that is invisible to everybody rather than to nobody. Asserting only
    the enabled half is the defect 25-RESEARCH.md's finding 2 names: an
    affordance that renders and does nothing without its script. A gate
    is a two-state thing and a one-state assertion is half a check.

    "HOLDS NOTHING FOCUSABLE" IS THE CLAUSE THAT MATTERS, AND IT IS
    ASSERTED BY WALKING THE TAB ORDER RATHER THAN BY READING THE
    COMPUTED `display`. `display: none` does remove its subtree from the
    tab order, so a computed-style read agrees with the tab walk TODAY —
    and would keep agreeing, wrongly, the moment somebody refactors the
    rule to `visibility: hidden` on the wrapper with an inner override,
    or to `opacity: 0`, both of which leave a keyboard visitor able to
    Tab into a control that does nothing. The property under test is
    reachability, so reachability is what is measured.

    The walk is skipped, and `candidates: 0` recorded instead, when the
    wrapper contains no focusable candidate in the first place — that is
    not a short cut around the assertion, it is the assertion already
    answered: a wrapper with nothing focusable in it cannot put anything
    in the tab order. The walk runs exactly when it can find something,
    which is the case it exists for.

    TWO HOOKS, AND THE DIFFERENCE BETWEEN THEM IS THE POINT.

    `prepare` runs on BOTH pages, right after the route loads and before
    anything is measured, and it is for putting the subject into the
    state it is meant to be judged in — opening the disclosure the gated
    wrapper lives inside, or (as 25-02 used it) rendering a wrapper that
    carries the gate class at all, so the STYLESHEET's rule can be
    measured in a real browser before any page renders one. Whatever it
    does, it must do to both pages identically, or the two directions
    stop being the same measurement taken twice.

    `arm` runs on the scripts-ENABLED page only, after `prepare`, and it
    is for the state change that does the revealing. A plain `.js` gate
    needs none (the class is on <html> from the first script statement),
    but the same two-state shape covers a wrapper revealed by a script's
    own logic — `.dirty-bar`, revealed by dirty-state.js only once the
    form is dirty, is the live precedent and one of the two subjects this
    helper was demonstrated against.

    `tab_budget` bounds the walk; it defaults to the page's own count of
    focusable candidates plus two, so it is derived from the document
    rather than guessed, and a page that grows a control does not
    silently start walking too few steps.
    """
    probe_args = {"selector": selector,
                  "focusable": _FOCUSABLE_CANDIDATE_SELECTOR}
    with _no_js_page(browser, base_url, route, viewport=viewport) as page:
        if prepare is not None:
            prepare(page)
        seen = page.evaluate(_GATE_BOX_PROBE, probe_args)
        if seen.get("error"):
            raise AssertionError(
                "_assert_js_gate: no element matched %r on %s with scripts "
                "blocked — the gated wrapper must be RENDERED and merely "
                "collapsed, so with none this helper measures nothing"
                % (selector, route))
        painted = [box for box in seen["boxes"] if box[1] > 0]
        if painted:
            raise AssertionError(
                "_assert_js_gate: %r occupies space with scripts blocked on "
                "%s — %r of the %d wrapper(s) measured %r. The gate must hide "
                "by default and REVEAL under .js, never the reverse, which "
                "shows a dead affordance permanently when a script fails to "
                "run (D-09)"
                % (selector, route, len(painted), seen["count"], painted))

        reached = None
        steps = 0
        if seen["candidates"]:
            budget = tab_budget or (seen["tabbable"] + 2)
            for steps in range(1, budget + 1):
                page.keyboard.press("Tab")
                at = page.evaluate(_ACTIVE_PROBE, probe_args)
                if at["inside"]:
                    reached = at["where"]
                    break
                if at["seen"]:
                    break  # the tab order has cycled; every stop was seen
        if reached is not None:
            raise AssertionError(
                "_assert_js_gate: %r on %s collapses to zero height with "
                "scripts blocked but a keyboard visitor still tabs INTO it — "
                "%r took focus after %d Tab presses. A gate that hides by "
                "`visibility`/opacity rather than `display: none` leaves "
                "exactly this focusable ghost, operating nothing"
                % (selector, route, reached, steps))
        blocked = {"boxes": seen["boxes"], "candidates": seen["candidates"],
                   "tab_steps": steps, "tabbable_on_page": seen["tabbable"]}

    extra = {} if viewport is None else {"viewport": viewport}
    context = browser.new_context(**extra)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + route)
        page.wait_for_load_state("load")
        if prepare is not None:
            prepare(page)
        if arm is not None:
            arm(page)
        seen = page.evaluate(_GATE_BOX_PROBE, probe_args)
        if seen.get("error"):
            raise AssertionError(
                "_assert_js_gate: no element matched %r on %s with scripts "
                "ENABLED" % (selector, route))
        revealed = [box for box in seen["boxes"] if box[1] > 0]
        if not revealed:
            raise AssertionError(
                "_assert_js_gate: %r never reveals on %s — every one of the "
                "%d wrapper(s) still measures zero height WITH scripts "
                "running (%r). A gate asserted in the blocked direction "
                "alone passes against exactly this: an affordance hidden "
                "from everybody"
                % (selector, route, seen["count"], seen["boxes"]))
        enabled = {"boxes": seen["boxes"], "revealed": len(revealed),
                   "candidates": seen["candidates"]}
    finally:
        context.close()

    return {"blocked": blocked, "enabled": enabled}


# ---------------------------------------------------------------------
# 5. Both themes, and the page-overflow floor — both already owned.
# ---------------------------------------------------------------------

def _in_both_themes(page):
    """Yield `_set_ui_theme(page, t)`'s measurement for each of this
    app's explicit themes, in order, so "assert this in both themes" is
    one `for` line at a control plan's call site.

    THIS IS COMPOSITION, NOT A SECOND THEME MECHANISM. 24-02 owns the
    theme switch and every one of its guarantees lives in
    `_set_ui_theme()` — the explicit `data-ui-theme` attribute rather
    than `emulate_media`, the both-themes sampling, and the refusal to
    return unless `--color-canvas` and `--color-text` genuinely differ
    between them. This generator adds a loop and nothing else. A control
    plan that reached for `context.new_context(color_scheme="dark")`
    instead would be building the second theme switch this project keeps
    paying for.

    The page is left on the LAST theme yielded, which is
    `UI_THEMES_EXPLICIT`'s last entry — a caller that cares should call
    `_set_ui_theme()` again itself rather than depend on that order.
    """
    for theme in UI_THEMES_EXPLICIT:
        yield _set_ui_theme(page, theme)


# THE 360px BODY-OVERFLOW MEASUREMENT IS `_assert_no_page_overflow()`
# ABOVE, AND THIS PLAN ADDS NOTHING BESIDE IT. 24-02 already exposed it
# as one call taking a page and a name, already settled which box means
# "the page" (documentElement, matching the two page-level checks this
# file carried before it), already established that a deliberately
# scrollable `.data-table-wrap` is not a page overflow, and already
# carries the optional `expected_width` guard that proves the
# measurement was taken at the viewport the caller believes it built.
# Every control plan in this phase calls it as:
#
#     msg = _assert_no_page_overflow(
#         page, "the dial on /device", VIEWPORT_MIN_SUPPORTED["width"])
#     if msg:
#         return False, msg
#
# A second overflow helper would be a third convention in one file about
# what "the page" means, which is how three checks come to disagree.


# ---------------------------------------------------------------------
# 6. Display's own rendered page HEIGHT — 25-06-PLAN.md Task 1 (CFG-50).
# ---------------------------------------------------------------------
#
# WHY A HARNESS HELPER AND NOT A NUMBER IN A SUMMARY. D5 is the one item
# in this phase whose success criterion is a MEASUREMENT rather than a
# behaviour: 22-AUDIT.md's X6 row set a page-height target that 22-10
# then recorded as "NOT met and cannot be by density alone — folding the
# grid behind the big preview is D5". A before-number typed into a
# document by hand, after the change, is not a before-number; a before-
# number produced by the same instrument that later produces the after-
# number is. So the measurement is a registered check, taken before any
# markup in this plan existed, and re-run afterwards by the identical
# code path.
#
# IT DELIBERATELY ASSERTS NO TARGET. The number it reports is the
# verdict, and 25-06 Task 4 states plainly whether the target is met.
# What it DOES assert is that the instrument is pointed at the right
# thing, which is the only way a recorded height means anything at all:
#   * the measurement was taken at the width the caller asked for (a
#     context that silently came up at another size reports a height for
#     a layout nobody asked about);
#   * the document really is the authenticated Display page and not the
#     login card it redirects to when the session is missing — asserted
#     by the Frame colours card's own heading id AND by the departures
#     radiogroup's full THEME_IDS-sized population, because "a page
#     rendered" is exactly the vacuous version of this;
#   * the page is genuinely taller than the viewport, so the number is a
#     document height rather than a viewport height wearing one.
#
# `scrollHeight` on documentElement, not `body`: `body` can be shorter
# than the document when a child escapes it, and documentElement is the
# same box `_assert_no_page_overflow()` already settled on for the
# horizontal axis. One convention per file.
_DISPLAY_HEIGHT_PROBE = (
    "args => ({"
    "  height: document.documentElement.scrollHeight,"
    "  clientWidth: document.documentElement.clientWidth,"
    "  clientHeight: document.documentElement.clientHeight,"
    "  scrollWidth: document.documentElement.scrollWidth,"
    "  heading: !!document.getElementById(args.headingId),"
    "  themeRadios: document.querySelectorAll("
    "    'input[name=\"theme\"]').length,"
    "})")


def _display_page_height(browser, base_url, viewport):
    """Display's full rendered document height at `viewport`, with the
    instrument proved to be pointed at Display.

    Returns the probe's own dict (height, clientWidth, clientHeight,
    scrollWidth, heading, themeRadios). Raises AssertionError when the
    measurement cannot be trusted — `_set_ui_theme()`'s shape and for
    its reason: a helper returning a verdict string hands every caller a
    guard it has to remember, and `check()` turns a raised
    AssertionError into a named FAIL nobody can forget.

    Scripts are ENABLED here, deliberately. The height a visitor sees is
    the height of the page their browser actually renders, and on
    Display that includes `theme-preview.js` collapsing three of the
    four usage panels at load — a scripts-blocked measurement would
    report a page nobody with a default browser ever sees, and would
    move for reasons that have nothing to do with this plan.
    """
    context = browser.new_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        seen = page.evaluate(
            _DISPLAY_HEIGHT_PROBE,
            {"headingId": config_page.FRAME_COLOURS_HEADING_ID})
    finally:
        context.close()
    if seen["clientWidth"] != viewport["width"]:
        raise AssertionError(
            "_display_page_height: asked for a %dpx viewport, the document "
            "reports a client width of %d — the height below would be a "
            "measurement of a layout nobody asked for"
            % (viewport["width"], seen["clientWidth"]))
    if not seen["heading"]:
        raise AssertionError(
            "_display_page_height: the document at %dpx carries no Frame "
            "colours heading — this is not the authenticated Display page "
            "(a missing session redirects to the login card, which renders "
            "perfectly and is a quarter of the height)" % (viewport["width"],))
    expected_radios = len(device_config.THEME_IDS)
    if seen["themeRadios"] != expected_radios:
        raise AssertionError(
            "_display_page_height: the Display page at %dpx posts %d radios "
            "named 'theme', expected %d — a height measured against a "
            "different number of chips is not comparable with the one this "
            "plan recorded before it started"
            % (viewport["width"], seen["themeRadios"], expected_radios))
    if seen["height"] <= seen["clientHeight"]:
        raise AssertionError(
            "_display_page_height: the document reports a scrollHeight of %d "
            "against a client height of %d — Display is not shorter than a "
            "phone viewport, so this is a viewport height wearing a document "
            "height's name" % (seen["height"], seen["clientHeight"]))
    return seen


# ---------------------------------------------------------------------
# 7. AGREEMENT — the RELATIONSHIP between surfaces, which is the thing
#    D17 shipped broken while every one of its own checks passed.
# ---------------------------------------------------------------------
#
# The quiet-hours dial shipped with three correct checks and one live
# defect. The arc was asserted correct SERVER-SIDE for the saved value.
# The handles were asserted TO MOVE. The value was asserted TO PERSIST
# to disk. All three pass, today, against a page on which the fields
# read 08:00/18:00, both handles sit at 8 and 18, and the arc still
# draws 23:00 -> 07:00 under a caption that still reads "23:00 -> 07:00
# - 8 h". Nothing asserted that the arc AGREES with the handles after
# an interaction, and that unmeasured relationship is the whole defect.
#
# So the shape below is deliberately NOT "one check per surface". One
# check per surface is precisely the shape that shipped this: each of
# them can be individually, permanently right while the page as a whole
# lies. The subject here is the SET of decoded values, and the assertion
# is that it has exactly one member.
#
# Two further clauses, and they are the vacuity answers rather than
# decoration. Without "equals what the interaction REQUESTED" this
# passes perfectly against a page that froze all four surfaces together
# at their old value — four surfaces agreeing on the wrong thing is
# still agreement. Without "DIFFERS from what was there before" it
# passes against an interaction that did nothing at all, which is the
# easiest way in the world to make every surface agree.


def _canonical_surface_value(value):
    """One canonical, hashable, comparable form for a decoded surface
    value, so `(1380, 420)` and `[1380, 420]` are the SAME reading
    rather than two members of a set.

    This exists because the set is the whole assertion below, and a set
    that counts a tuple and a list as two members would report a
    disagreement between two surfaces that agree — a false FAIL is as
    bad here as a false PASS, and worse for trust. Raises on anything
    that cannot be made hashable rather than falling back to `repr()`,
    which would make every unhashable value agree with itself and with
    nothing else by accident.
    """
    if isinstance(value, (list, tuple)):
        return tuple(_canonical_surface_value(item) for item in value)
    try:
        hash(value)
    except TypeError:
        raise AssertionError(
            "_assert_surfaces_agree: a decoder returned %r, which cannot be "
            "compared or put in a set — a surface decoder must return a "
            "number, a string, or a tuple of them" % (value,))
    return value


def _surface_reading_report(decoded):
    """Every surface and what it decoded to, in the order the caller
    listed them — never only the mismatching pair.

    The two-value message is the tempting one and it is the wrong one:
    the shipped defect reads "the fields and the handles agree on
    08:00-18:00 while the arc and the caption both still say
    23:00-07:00", and that sentence is only available to a reader who
    is shown all four. A message naming one pair would have sent the
    next reader looking at the wrong half.
    """
    return "; ".join("%s -> %r" % (label, value) for label, value in decoded.items())


def _assert_surfaces_agree(page, surfaces, requested, before, where):
    """Decode N rendered surfaces into ONE canonical value and assert
    they agree, that the agreed value is the one the interaction
    REQUESTED, and that it DIFFERS from the pre-interaction value.

    `surfaces` is an ordered mapping of a surface LABEL to a
    zero-argument callable returning that surface's decoded value — a
    mapping rather than a fixed pair of arguments, because the number of
    surfaces describing one value is a property of the control and not
    of this helper, and a two-argument version would have to be
    hand-unrolled (and mis-unrolled) at every call site with three or
    four.

    Returns the `{label: decoded}` mapping on success, so a caller can
    report the numbers it agreed on. RAISES AssertionError on every
    failure, `_persist_without_js()`'s shape and for its reason: a
    helper returning a verdict string hands every caller a guard it has
    to remember, and `check()` turns a raised AssertionError into a
    named FAIL nobody can forget.

    THREE SEPARATE ASSERTIONS WITH THREE SEPARATE MESSAGES, deliberately
    not collapsed into one boolean, because they fail for three
    unrelated reasons and a reader needs to know which:
      1. the surfaces DISAGREE — some part of the page did not follow;
      2. they agree on the WRONG value — the page froze together, or the
         interaction was applied and then overwritten;
      3. they agree on the value that was already there — nothing
         happened at all, and a one-boolean version of this helper would
         have called that a pass.
    A single `all(...)` over the three would report "agreement failed"
    for a frozen page, which is both true and useless.

    `page` is taken and used: every message names the document the
    reading came off, because these surfaces are decoded on a live page
    that a preceding step navigated, and a reading taken on the wrong
    route is the one failure whose message would otherwise be a puzzle.

    This helper drives NO state change of its own (T-27-01-A). It reads
    what the caller's interaction already did, which is what lets it
    compose with `_persist_without_js()` rather than wrap it.
    """
    decoded = {}
    for label, decoder in surfaces.items():
        decoded[label] = decoder()
    if len(decoded) < 2:
        raise AssertionError(
            "_assert_surfaces_agree: %s was given %d surface(s) (%s) on %s — "
            "agreement between fewer than two surfaces is not a relationship, "
            "and a one-surface call is the endpoint check this helper exists "
            "to replace"
            % (where, len(decoded), _surface_reading_report(decoded), page.url))

    canonical = {label: _canonical_surface_value(value)
                 for label, value in decoded.items()}
    distinct = set(canonical.values())
    if len(distinct) != 1:
        raise AssertionError(
            "_assert_surfaces_agree: %s — the %d surfaces describing this "
            "value DISAGREE on %s. They read: %s. The interaction asked for "
            "%r. A surface that did not follow is a surface that is now "
            "lying to the visitor about a value the page beside it shows "
            "correctly"
            % (where, len(canonical), page.url,
               _surface_reading_report(decoded), requested))

    agreed = next(iter(distinct))
    if agreed != _canonical_surface_value(requested):
        raise AssertionError(
            "_assert_surfaces_agree: %s — all %d surfaces on %s agree on %r, "
            "but the interaction asked for %r. They read: %s. Agreement on "
            "the wrong value is what a page that froze every surface "
            "together looks like from outside, which is why agreement alone "
            "is not the assertion"
            % (where, len(canonical), page.url, agreed, requested,
               _surface_reading_report(decoded)))

    if agreed == _canonical_surface_value(before):
        raise AssertionError(
            "_assert_surfaces_agree: %s — all %d surfaces on %s agree on %r, "
            "which is exactly what was there BEFORE the interaction. They "
            "read: %s. The interaction changed nothing, so this reading "
            "proves nothing: a no-op is the cheapest way to make every "
            "surface on a page agree"
            % (where, len(canonical), page.url, agreed,
               _surface_reading_report(decoded)))
    return decoded


# ---------------------------------------------------------------------
# 8. The arc as a NUMBER — resolved geometry, read back out of the
#    browser (27-01-PLAN.md Task 2).
# ---------------------------------------------------------------------
#
# Until now the quiet-hours arc was only checkable as SERVER-RENDERED
# HTML, and that is precisely the blind spot D17 shipped through: the
# server-rendered attribute was right for the saved value on every page
# load, and stayed right, and stayed on the screen, while the handles
# and the fields moved away from it. A check that can only read the
# declared attribute cannot see that defect at all. So what is read
# here is the RESOLVED value — what the browser actually painted, after
# script ran and after any `.js`-scoped stylesheet rule overrode the
# presentation attribute (which a CSS declaration of any specificity
# does, as `quiet_dial_svg()`'s own docstring records).
#
# MEASURED ON THIS TREE, and these are the numbers the decoder below is
# built against rather than guessed at. On /display with the seeded
# 23:00-07:00 window the arc reports:
#     attribute   stroke-dasharray="163.3628 326.7256"
#     resolved    stroke-dasharray: 163.363px, 326.726px
#     attribute   transform="rotate(255.0000 88 88)"
#     resolved    transform: matrix(-0.258819, -0.965926, 0.965926,
#                                   -0.258819, 25.7746, 195.778)
# Three facts follow, all of them load-bearing:
#   * the resolved dash is COMMA-separated, unit-suffixed and rounded to
#     three decimals where the attribute carries four — so it is parsed
#     as "the numbers in this string", never string-compared against
#     what the server emitted;
#   * the resolved `transform` is a MATRIX, not the rotate() that was
#     written, so the angle comes back through atan2 rather than off the
#     attribute (`rotate` as its own resolved property is "none" here);
#   * the resolved dash is in SVG USER UNITS, the same units
#     QUIET_DIAL_RADIUS is in. That is why this decoder does NOT go
#     through getBoundingClientRect and needs no correction for a
#     `scale()` in force: a box measurement would need one (and
#     `clientWidth` rounds to an integer, which can fail a perfectly
#     correct drawing), while a resolved dash length is already in the
#     coordinate system the emitter's own arithmetic used.
#
# The unit this file canonicalises a quiet window into is the
# MINUTE-OF-DAY, and it is not a choice made here: the two handles
# already publish `aria-valuenow="1380"` / `"420"`, so minutes are the
# unit three of the four surfaces speak natively. A decoder returning
# fractions would make the agreement helper compare 0.9583333 against
# whatever a caption parsed to, and invent a tolerance to hide the
# difference.

_QUIET_ARC_SELECTOR = "." + config_page.QUIET_DIAL_ARC_CLASS
# The emitter's OWN quarter-turn correction, read rather than retyped as
# -90: this decoder must undo exactly the rotation quiet_dial_svg()
# applied, and a second copy of that number is a second thing to change
# and a second thing to forget. It is private by name because nothing
# outside that module had a reason to read it until a check needed to
# INVERT it, which is a new reason rather than a licence to copy it.
_QUIET_ARC_TWELVE_OCLOCK_DEG = config_page._QUIET_DIAL_TWELVE_OCLOCK_DEG
MINUTES_PER_DAY = 24 * 60

# Any signed decimal, in any of the forms a resolved CSS value can put
# one in. Deliberately tolerant about separators and units, because the
# separator and the unit are the browser's business and the NUMBERS are
# this decoder's.
_GEOMETRY_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")
_GEOMETRY_MATRIX_RE = re.compile(r"^matrix\(([^)]*)\)$")

_RESOLVED_PROPERTY_PROBE = (
    "args => {"
    "  let els;"
    "  try {"
    "    els = [...document.querySelectorAll(args.selector)];"
    "  } catch (e) {"
    "    return {error: 'bad-selector', detail: String(e)};"
    "  }"
    "  if (els.length !== 1) return {error: 'count', count: els.length};"
    "  const cs = getComputedStyle(els[0]);"
    "  return {value: cs.getPropertyValue(args.property)};"
    "}")


def _resolved_property(page, selector, property_name, where):
    """The RESOLVED value of one property — custom or standard — on the
    one element `selector` matches, as a trimmed string.

    Raises AssertionError naming the selector, the property and the
    document when the selector matches anything other than exactly one
    element, or when the resolved value is empty. NEVER returns a
    default, and that refusal is the point rather than tidiness: a
    reader that answered "" or 0 for an arc that is not on the page
    would let `_assert_surfaces_agree()` pass on a document with no arc
    at all — every surface agreeing because one of them is silently
    absent is the exact vacuity this phase exists to refuse.

    Custom properties and standard ones go through the SAME call
    (`getPropertyValue` serves both), because after 27-02 the arc's
    geometry lives in both places at once: the pair of custom properties
    published on the shared ancestor, and the resolved presentation
    properties on the circle they drive. Two readers would have made
    "the ancestor says one thing and the circle paints another" a
    comparison nobody wrote.

    EXACTLY ONE ELEMENT, not `.first`. A selector that matches two arcs
    has an ambiguous answer, and a reader that quietly took the first
    would report a number that is right about half a page.
    """
    seen = page.evaluate(
        _RESOLVED_PROPERTY_PROBE,
        {"selector": selector, "property": property_name})
    if seen.get("error") == "bad-selector":
        raise AssertionError(
            "_resolved_property: %s — %r is not a selector the browser will "
            "accept (%s). An instrument that cannot be aimed measures nothing"
            % (where, selector, seen["detail"]))
    if seen.get("error") == "count":
        raise AssertionError(
            "_resolved_property: %s — %r matches %d element(s) on %s, and the "
            "resolved value of %r is only defined for exactly one. A decoder "
            "that defaulted here would make an ABSENT arc agree with every "
            "other surface on the page"
            % (where, selector, seen["count"], page.url, property_name))
    value = (seen.get("value") or "").strip()
    if not value:
        raise AssertionError(
            "_resolved_property: %s — %r resolves to nothing at all on %r on "
            "%s. Read as absent rather than as a default, because a default "
            "here is a number nobody measured"
            % (where, property_name, selector, page.url))
    return value


def _fraction_to_minute(fraction):
    """A fraction of a day to a minute-of-day, wrapped into [0, 1440).

    Rounded to the nearest minute ON PURPOSE and stated here rather than
    buried: the resolved dash comes back at three decimals where the
    server emitted four, so a fraction decoded off the paint is within
    about a thousandth of a minute of the one the server computed and
    will never be bit-identical to it. The minute is the unit the
    handles already publish, so rounding to it is canonicalisation, not
    a tolerance that hides a disagreement — a surface that is a whole
    minute out still reads as a different number here.
    """
    return int(round(fraction * MINUTES_PER_DAY)) % MINUTES_PER_DAY


def _quiet_arc_minutes(page, where, selector=_QUIET_ARC_SELECTOR,
                       radius=None):
    """The quiet-hours arc, read back off what the browser PAINTED, as
    a canonical `(start_minute, end_minute)` pair of ints.

    Inverts `draw.unit_circle_dash_array()`'s own arithmetic — the drawn
    dash over the full circumference is the sweep fraction — and
    `quiet_dial_svg()`'s quarter-turn correction: the circle's dash
    origin is three o'clock and the drawing rotates by minus ninety
    degrees plus the window's own start.

    `radius` defaults to `config_page.QUIET_DIAL_RADIUS`, the SAME
    constant the emitter divides by, rather than a number retyped here.
    A retyped 78 would go on agreeing with a stale drawing for exactly
    as long as nobody changed the dial's size, and then disagree with
    the whole page at once.

    Raises AssertionError, naming what was read, when either property is
    missing, when the transform is not a 2-D matrix, or when neither
    parses as a number. It never returns a default — see
    `_resolved_property()` for why that matters more than it looks.

    IT DOES NOT WAIT FOR ANYTHING. Sampling at the right instant is the
    CALLER's job and must be done by hooking the event the browser
    actually emits (this file has lost two checks to a guessed instant:
    one read an interpolation frame, one sampled two rAF after a click
    and failed CI on a correct build). A decoder that slept would hide
    that decision inside an instrument.
    """
    if radius is None:
        radius = config_page.QUIET_DIAL_RADIUS
    dash = _resolved_property(page, selector, "stroke-dasharray", where)
    transform = _resolved_property(page, selector, "transform", where)

    lengths = [float(n) for n in _GEOMETRY_NUMBER_RE.findall(dash)]
    if len(lengths) < 2:
        raise AssertionError(
            "_quiet_arc_minutes: %s — %r resolves stroke-dasharray to %r, "
            "which carries %d number(s); a dashed arc needs the drawn length "
            "and the gap" % (where, selector, dash, len(lengths)))
    circumference = 2 * math.pi * radius
    if circumference <= 0:
        raise AssertionError(
            "_quiet_arc_minutes: %s — the dial radius read from config_page "
            "is %r, which has no circumference to divide by"
            % (where, radius))
    sweep_fraction = lengths[0] / circumference

    matrix = _GEOMETRY_MATRIX_RE.match(transform)
    if not matrix:
        raise AssertionError(
            "_quiet_arc_minutes: %s — %r resolves transform to %r, which is "
            "not the 2-D matrix a rotate() resolves to. The arc's start angle "
            "cannot be recovered from it, and guessing one would be a number "
            "nobody measured" % (where, selector, transform))
    parts = [float(n) for n in _GEOMETRY_NUMBER_RE.findall(matrix.group(1))]
    if len(parts) != 6:
        raise AssertionError(
            "_quiet_arc_minutes: %s — %r resolves transform to %r, which "
            "carries %d component(s) rather than a 2-D matrix's six"
            % (where, selector, transform, len(parts)))
    angle_deg = math.degrees(math.atan2(parts[1], parts[0]))
    # Undo quiet_dial_svg()'s own twelve-o'clock correction, then wrap.
    start_fraction = ((angle_deg - _QUIET_ARC_TWELVE_OCLOCK_DEG) % 360.0) / 360.0

    start_minute = _fraction_to_minute(start_fraction)
    end_minute = (start_minute + _fraction_to_minute(sweep_fraction)) % MINUTES_PER_DAY
    return (start_minute, end_minute)


# 31-01-PLAN.md Task 2: promoted from a main()-local def (pre-edit line
# 11466) to module level because it is called BOTH from the quiet-hours
# dial block plan 03 moves out of this file AND from the settings
# dirty-bar audit that stays behind permanently — the same
# main()-local-but-needed-in-two-places coupling shape RESEARCH.md
# documented for _quiet_arc_minutes above, which is why the two
# promotions sit next to each other.
def _handle_sel(field):
    return '[data-value-field="%s"] [data-value-handle]' % field


def _fraction_pair_minutes(page, selector, start_property, sweep_property,
                           where):
    """The quiet window as `(start_minute, end_minute)`, decoded from a
    START fraction and a SWEEP fraction published as custom properties
    on `selector` — the shared ancestor, not the circle.

    This is the second place the arc's geometry lives after 27-02: the
    script publishes the pair on the ancestor and the stylesheet draws
    the circle from it. Reading BOTH ends of that chain with the same
    canonical output is what lets `_assert_surfaces_agree()` catch "the
    ancestor was updated and the paint did not follow", which is D17 one
    layer down and would otherwise be nobody's check.

    THE SECOND PROPERTY IS THE SWEEP, not the end, and that is a
    contract rather than a convenience: a wrapping window is exactly
    where an end fraction and a sweep fraction stop being the same
    arithmetic (23:00 to 07:00 is end 0.2917, sweep 0.3333, and a
    reader that mixed them up would report 07:00 to 07:00 and call it
    agreement). If 27-02 publishes an end fraction instead, the
    conversion belongs at the emitter, where the wrap decision already
    lives in `quiet_window_span()`.

    Raises through `_resolved_property()` when either property is
    absent, and on its own when either does not parse.
    """
    fractions = []
    for name in (start_property, sweep_property):
        raw = _resolved_property(page, selector, name, where)
        numbers = _GEOMETRY_NUMBER_RE.findall(raw)
        if not numbers:
            raise AssertionError(
                "_fraction_pair_minutes: %s — %r resolves %s to %r on %s, "
                "which carries no number at all. A fraction that cannot be "
                "read is not a fraction of zero"
                % (where, selector, name, raw, page.url))
        fractions.append(float(numbers[0]))
    start_minute = _fraction_to_minute(fractions[0])
    end_minute = (start_minute + _fraction_to_minute(fractions[1])) % MINUTES_PER_DAY
    return (start_minute, end_minute)


# 28-03-PLAN.md Task 3 (CFG-73 Bug A) — SUPERSEDED. Kept below, legible,
# because it documents the real design this task inverts on purpose, not
# by accident:
#
#     "Any run of digits, for the caption's own text — 27-02-PLAN.md
#     Task 3's own design (see quiet_dial_readout_html()'s docstring):
#     the two endpoint spans substitute value-controls.js's
#     paintReadouts() raw, UNCONVERTED value — the same minute-of-day
#     number the handles publish as aria-valuenow, not an "HH:MM"
#     string, because paintReadouts()'s own substitution is a bare
#     number and this app writes no clock-formatting copy into that
#     seam. So the LIVE caption (after any interaction) reads like
#     "480 -> 1080 . ", and this decoder reads it exactly that way,
#     through the same minute-of-day unit the other three surfaces
#     already speak - no HH:MM parsing, no second unit, no tolerance."
#
# THAT WAS THE BUG, DOCUMENTED HERE AS CORRECT BEHAVIOUR. 28-03-PLAN.md
# Task 1/2 (CFG-73 Bug A) gave both endpoint spans a real HH:MM codec and
# the duration span a live, worded duration, so the LIVE caption now
# reads "08:00 -> 18:00 . 8h" — the SAME FORM the server emits at load.
# `_CAPTION_NUMBER_RE`'s old bare-digit-run approach, re-applied to that
# string, would misparse "08:00" into the digit runs "08"/"00" and
# silently report (8, 0) instead of (480, 1080) — precisely how this
# regression shipped and survived a phase undetected: a decoder that
# read the bug's own output as ground truth. `_CAPTION_TOKEN_RE` below
# matches "HH:MM" tokens instead of bare digit runs.
_CAPTION_TOKEN_RE = re.compile(r"(\d{1,2}):(\d{2})")
_QUIET_READOUT_SELECTOR = "." + config_page.QUIET_DIAL_READOUT_CLASS


def _quiet_caption_minutes(page, where, selector=None):
    """The quiet-hours caption, read back off what the browser is
    CURRENTLY SHOWING, as a canonical `(start_minute, end_minute)` pair
    of ints — the fourth and last surface `_assert_surfaces_agree()`
    checks.

    Reads `textContent` (not `inner_text()`): the paragraph is
    `aria-hidden="true"` and its own two endpoint spans are ordinary
    elements with no visibility trick played on them, but `textContent`
    is unambiguous about picking up every character in document order
    regardless of layout, which is what a decoder that must never
    silently read stale/absent text needs.

    28-03-PLAN.md Task 3 (CFG-73 Bug A): THE FIRST TWO "HH:MM" TOKENS ARE
    THE PAIR, taken in document order (start span, then end span) — the
    same order `quiet_dial_readout_html()` emits them in and the same
    order `quiet_dial_handles_html()` emits its own two wrappers in, and
    the SAME "HH:MM -> HH:MM . <duration>" FORM the server emits at
    load: both endpoints are painted through `numberToField()`'s own
    zero-padded clock codec after ANY interaction now (28-03's own
    Bug A fix), not the bare minute-of-day number this decoder used to
    (mis)read as ground truth. The duration segment's own wording (e.g.
    "8h"/"8 h") contains no "HH:MM"-shaped substring, so it never
    contributes a false third pair member.

    Raises AssertionError, with the caption's ACTUAL text quoted, when
    fewer than two "HH:MM" tokens are present — a decoder that silently
    returns a plausible-looking pair from unparseable text is exactly
    how the original bug survived a phase undetected, and this one does
    not repeat that mistake.
    """
    if selector is None:
        selector = _QUIET_READOUT_SELECTOR
    text = page.locator(selector).text_content()
    if text is None:
        raise AssertionError(
            "_quiet_caption_minutes: %s — %r has no text content at all on %s"
            % (where, selector, page.url))
    tokens = _CAPTION_TOKEN_RE.findall(text)
    if len(tokens) < 2:
        raise AssertionError(
            "_quiet_caption_minutes: %s — the caption %r on %s carries %d \"HH:MM\" token(s), "
            "fewer than the two endpoints a pair needs" % (where, text, page.url, len(tokens)))

    def _token_to_minute(token):
        hours, minutes = token
        return (int(hours) * 60 + int(minutes)) % MINUTES_PER_DAY

    return (_token_to_minute(tokens[0]), _token_to_minute(tokens[1]))


# 28-03-PLAN.md Task 3 (CFG-73 Bug A): the duration span's own selector —
# it carries VALUE_CONTROL_READOUT_BASE_ATTR (data-value-readout-base)
# and neither endpoint span does, so this is unique WITHIN the quiet-dial
# readout paragraph without inventing a class the stylesheet never uses.
_QUIET_DURATION_SELECTOR = "%s [%s]" % (
    _QUIET_READOUT_SELECTOR, layout.VALUE_CONTROL_READOUT_BASE_ATTR)


def _quiet_caption_shape(text):
    """`text`'s STRUCTURE, never its value: every "HH:MM" token becomes
    the literal placeholder "HH:MM" and every remaining digit becomes
    "#", so two captions naming different times/durations but sharing
    the same separators, spacing and token order compare equal, while a
    caption whose FORM actually changed (a dropped separator, a missing
    duration, a reordered pair) does not.

    28-03-PLAN.md Task 3 (CFG-73 Bug A)'s own contract: the caption must
    keep the SAME FORM the server emits at load after every interaction
    kind — this is "the same form" made comparable without pinning the
    one reference string, which would only ever be true for one value.
    """
    shaped = _CAPTION_TOKEN_RE.sub("HH:MM", text)
    return re.sub(r"\d+", "#", shaped)


def _quiet_duration_span_text(page, where):
    """The duration span's own CURRENTLY DISPLAYED text — the third
    child of the readout paragraph — read the same `textContent` way
    `_quiet_caption_minutes()` reads the whole caption.
    """
    text = page.locator(_QUIET_DURATION_SELECTOR).text_content()
    if text is None:
        raise AssertionError(
            "_quiet_duration_span_text: %s — %r has no text content at all on %s"
            % (where, _QUIET_DURATION_SELECTOR, page.url))
    return text


def _expected_quiet_duration_text(page, requested, where):
    """The duration text `page`'s OWN duration span SHOULD show for the
    `requested` (start_minute, end_minute) pair — computed as the
    WRAPPED difference between the two ends (matching
    `quiet_window_span()`'s own "always forward from start" contract),
    bucketed with `layout._age_bucket()`'s own boundaries, and worded
    with whichever of `layout.DURATION_ATTRS` the PAGE ITSELF carries —
    read off the duration span's own attribute, never hardcoded as
    "h"/"min"/"heure", so this check cannot desync from the catalogue
    the server actually shipped.
    """
    start_minute, end_minute = requested
    minutes = (end_minute - start_minute) % MINUTES_PER_DAY
    quantity, unit = layout._age_bucket(minutes * 60)
    index = {"s": 0, "m": 1, "h": 2, "d": 3}[unit]
    attr = layout.DURATION_ATTRS[index]
    wording = page.get_attribute(_QUIET_DURATION_SELECTOR, attr)
    if not wording:
        raise AssertionError(
            "_expected_quiet_duration_text: %s — the duration span on %s carries no usable %r"
            % (where, page.url, attr))
    mark = layout.RELATIVE_QUANTITY_MARK
    return wording.replace(mark, str(quantity), 1) if mark in wording else wording


# ---------------------------------------------------------------------
# 9. "Shorter, and still refusing" — ONE read, two facts
#    (27-01-PLAN.md Task 3).
# ---------------------------------------------------------------------
#
# 27-06 cuts three regions of explanatory copy. Two of them sit directly
# on top of this app's loudest honesty rule: the battery gauge prints an
# absolute days figure ONLY when this frame's own observed history
# supports one, and prints no figure at all otherwise —
# `wake_battery_observed_text()`'s docstring, `wake_gauges_html()` and
# `value-controls.js`'s header all say so in as many words. A shorter
# sentence that starts naming a number is not a cut, it is a REGRESSION
# wearing a cut's clothes.
#
# So "it got shorter" and "it still refuses to claim a figure" are
# asserted about ONE read of ONE rendering, and that is structural
# rather than tidy. Asserted separately they can be satisfied by two
# different page states — a cut proven on a page with a falling battery
# series and a refusal proven on a page without one — and the pair would
# report success about a rendering that never existed. The read happens
# once; both assertions are made against that string.
#
# Whitespace is normalised to single spaces before anything is counted,
# because the rendered textContent carries the markup's own indentation
# and newlines, and a baseline that moved when a template was re-wrapped
# would be a baseline about formatting rather than about copy.

_REGION_TEXT_PROBE = (
    "args => {"
    "  let els;"
    "  try {"
    "    els = [...document.querySelectorAll(args.selector)];"
    "  } catch (e) {"
    "    return {error: 'bad-selector', detail: String(e)};"
    "  }"
    "  if (!els.length) return {error: 'no-element'};"
    "  return {count: els.length,"
    "          text: els.map(e => e.textContent).join(' ')};"
    "}")

_REGION_WHITESPACE_RE = re.compile(r"\s+")


def _region_text(page, selector, where):
    """Every element `selector` matches, read ONCE, joined in document
    order and whitespace-normalised.

    Joined rather than restricted to one element because two of 27-06's
    three regions are genuinely plural — `wake_gauges_html()` emits the
    two gauges as two sibling `<p>`s, and a helper that measured only
    the first would report a card half cut. Raises when nothing matches:
    a region that is not on the page has no length to compare, and zero
    is the shortest possible string, so a defaulting version of this
    would call a DELETED region a successful cut.
    """
    seen = page.evaluate(_REGION_TEXT_PROBE, {"selector": selector})
    if seen.get("error") == "bad-selector":
        raise AssertionError(
            "_region_text: %s — %r is not a selector the browser will accept "
            "(%s)" % (where, selector, seen["detail"]))
    if seen.get("error") == "no-element":
        raise AssertionError(
            "_region_text: %s — %r matches nothing on %s. A region that is "
            "absent is not a region that was shortened, and zero is the "
            "shortest length there is" % (where, selector, page.url))
    text = _REGION_WHITESPACE_RE.sub(" ", seen["text"]).strip()
    return {"selector": selector, "elements": seen["count"],
            "text": text, "chars": len(text)}


def _assert_shorter_and_still_refuses(page, selector, baseline_chars,
                                      forbidden, where):
    """One region, read once; two assertions against that single read:
    it is strictly SHORTER than `baseline_chars`, and `forbidden` does
    not match it.

    Returns `_region_text()`'s measurement so a caller can report the
    number it measured. Raises AssertionError with two distinct
    messages, because the two failures mean opposite things: the first
    says the cut never happened, the second says the cut went through
    something that was holding a refusal up.

    `baseline_chars` is a number 27-01 MEASURED on the pre-cut tree and
    recorded, never a round number chosen because it looked about right.
    STRICTLY less than, not "at most": a cut that changed nothing is
    exactly the claim this is here to refuse.

    `forbidden` is a regex (a string or a compiled pattern) describing
    the claim the shortened copy still must not make — for the battery
    gauge, the shape of an absolute days figure. It is searched against
    the same normalised string the length was taken from.
    """
    seen = _region_text(page, selector, where)
    pattern = re.compile(forbidden) if isinstance(forbidden, str) else forbidden
    if seen["chars"] >= baseline_chars:
        raise AssertionError(
            "_assert_shorter_and_still_refuses: %s — %r renders %d character(s) "
            "across %d element(s) on %s, against a recorded baseline of %d. "
            "The copy was not cut. It reads %r"
            % (where, selector, seen["chars"], seen["elements"], page.url,
               baseline_chars, seen["text"]))
    found = pattern.search(seen["text"])
    if found:
        raise AssertionError(
            "_assert_shorter_and_still_refuses: %s — %r did get shorter (%d "
            "character(s), under the %d baseline) but now matches %r at %r. "
            "A shorter sentence that starts claiming a figure this frame's "
            "own history cannot support is a regression, not a cut. The whole "
            "region reads %r"
            % (where, selector, seen["chars"], baseline_chars,
               pattern.pattern, found.group(0), seen["text"]))
    return seen


_MARKUP_INVENTORY_PROBE = (
    "args => {"
    "  const out = {};"
    "  for (const label of Object.keys(args.shapes)) {"
    "    try {"
    "      out[label] = document.querySelectorAll(args.shapes[label]).length;"
    "    } catch (e) {"
    "      return {error: 'bad-selector', label: label,"
    "              selector: args.shapes[label], detail: String(e)};"
    "    }"
    "  }"
    "  return {counts: out};"
    "}")


def _markup_inventory(page, shapes):
    """How many elements each named markup shape has on this page, as
    `{label: count}`.

    IT ASSERTS NOTHING ABOUT THE SUBJECT, on purpose. 27-06 has to pick
    one title form over another, and the count that decision rests on
    must be DERIVED BY RUNNING rather than copied out of a research
    document's grep — 27-RESEARCH.md §3 states its own 8/3/2 split is
    provisional precisely because a regex matches a formatting
    convention and not a grammar. A helper that also asserted the count
    would be a helper nobody could use to find out what the count is.
    Zero is a legitimate answer and is returned as one.
    """
    seen = page.evaluate(_MARKUP_INVENTORY_PROBE, {"shapes": dict(shapes)})
    if seen.get("error") == "bad-selector":
        raise AssertionError(
            "_markup_inventory: %r (for %r) is not a selector the browser "
            "will accept on %s (%s). An instrument that cannot be aimed "
            "counts nothing"
            % (seen["selector"], seen["label"], page.url, seen["detail"]))
    return seen["counts"]
