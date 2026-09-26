#!/usr/bin/env python3
"""Shared constants and helpers for the companion browser tests: viewport sizes, seed_state_dir(),
login/save/theme/keyboard/upload/geometry probes, quiet-hours arc decoders, and markup helpers.
Holds no tests (`__test__ = False`); this module exists only to be imported.

Every helper that opens a browser context takes a `make_context` factory instead of calling
`browser.new_context()` directly, so callers pass conftest's guarded `new_context` fixture, which
installs the loopback-only route guard.
"""
import contextlib
import math
import os
import re
import sys
from datetime import datetime, timedelta, timezone

__test__ = False

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Mirrors companion/conftest.py's own bootstrap, so a direct import of this module outside
# pytest still finds test-support (companion_app_server, for TEST_PASSWORD).
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from companion import layout  # noqa: E402
from companion.pages import config_page  # noqa: E402
from companion_app_server import TEST_PASSWORD  # noqa: E402
from server import device_config, history_db  # noqa: E402
from server.plane import colour_rules, manual_resolutions  # noqa: E402
import server.poll_loop as poll_loop  # noqa: E402

VIEW_TRANSITION_ROUTES = ("/", "/display", "/flights", "/airlines", "/health", "/device")
VIEW_TRANSITION_NAMES = {
    "skypane-sidebar": VIEW_TRANSITION_ROUTES,
    "skypane-title": VIEW_TRANSITION_ROUTES,
    "skypane-picture": ("/",),
}

# Named viewport sizes, replacing the inline {"width": ..., "height": ...} dicts this file used
# to repeat at each call site. 360 is the minimum supported viewport; 320 is below that contract
# floor but stays a measured width because the existing narrow-width assertions still pass and
# catch real defects.
VIEWPORT_MIN_SUPPORTED = {"width": 360, "height": 844}
VIEWPORT_PHONE = {"width": 390, "height": 844}
VIEWPORT_DESKTOP = {"width": 1280, "height": 900}
# Below the 360px contract floor, still measured — see above.
VIEWPORT_WIDTH_NARROW = 320
VIEWPORT_WIDTH_TABLET = 768
# The two width ladders, for checks that build one context per width rather than one fixed-size
# context. Derived from the three sizes above so a width has exactly one definition in this file.
VIEWPORT_WIDTHS_RESPONSIVE = (
    VIEWPORT_MIN_SUPPORTED["width"], VIEWPORT_PHONE["width"],
    VIEWPORT_DESKTOP["width"])
VIEWPORT_WIDTHS_ALL = (
    VIEWPORT_WIDTH_NARROW, VIEWPORT_MIN_SUPPORTED["width"],
    VIEWPORT_PHONE["width"], VIEWPORT_WIDTH_TABLET,
    VIEWPORT_DESKTOP["width"])

# Fixed, deterministic — never datetime.now(). 06:00 UTC so the 17h runway window (06:00-23:00)
# and the 23:00-07:00 quiet-hours window share no overlap, keeping the two concerns independent.
SEED_BASE_TS = datetime(2026, 8, 1, 6, 0, 0, tzinfo=timezone.utc)


def seed_state_dir(state_dir, base_ts=SEED_BASE_TS):
    """Write a fixture into a fresh temp state directory, through the same modules
    companion/app.py and server/poll_loop.py use to write this data themselves.
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

        # ~40 days of battery readings, one reading per day.
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

    # 2 unresolved prefixes, same registry shape companion/test_status_pages.py's own
    # _seed_unresolved_prefixes() helper writes, through the identical save_poll_state() call.
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

    # 3 gallery renders, archived through poll_loop's own writer so the on-disk filename/format
    # contract can never drift from what a real poll cycle produces.
    from PIL import Image
    # 600x800 matches Home's <img width="600" height="800">, so a layout-shift check comparing
    # the skeleton box to the loaded image's box is comparing against the real aspect ratio.
    canvas = Image.new("RGB", (600, 800), "white")
    for i in range(3):
        render_ts = (base_ts + timedelta(minutes=i)).isoformat()
        poll_loop._save_to_gallery(state_dir, canvas, render_ts)


def _login(page, base_url):
    """Drive the real login form through the UI and wait for the post-login redirect to land."""
    page.goto(base_url + "/login")
    page.fill("#password", TEST_PASSWORD)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


@contextlib.contextmanager
def _no_js_page(make_context, base_url, route, viewport=None, sign_in=True,
                cookies=None):
    """A scripts-blocked browser context, signed in, landed on `route`.

    `make_context` must be the guarded `new_context` fixture, never a bare `browser` object, so
    every scripts-blocked context in this file goes through the one loopback-guarded call site.
    `sign_in=False` is for the login card itself, which inspects the unauthenticated page before
    signing in as its last step. `cookies` is applied before the sign-in navigation, the only
    order under which the first rendered document (e.g. a UI-language cookie) already honours it.
    """
    extra = {} if viewport is None else {"viewport": viewport}
    context = make_context(java_script_enabled=False, **extra)
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
    """Click a checkbox/radio input through the DOM's native .click(), not Playwright's
    coordinate-based click.

    The selectable-card idiom hides these inputs with `clip-path: inset(50%)`, clipping both
    paint and hit-testing to nothing, so a coordinate click can silently land elsewhere and leave
    the control unchecked with no error. `element.click()` runs the DOM's activation behaviour
    regardless of hit-test visibility, matching how assistive tech and keyboard activation
    already reach this pattern.
    """
    page.eval_on_selector(selector, "el => el.click()")


def _guard_armed(page):
    """Whether dirty-state.js's beforeunload guard is currently armed.

    Dispatches a real, cancelable `beforeunload` Event in-page and reads `defaultPrevented`,
    rather than triggering an actual navigation: Chromium suppresses/auto-resolves the native
    "leave site?" dialog under Playwright, and `dialog` events do not reliably surface for
    beforeunload. Dispatching the Event still exercises dirty-state.js's real listener.
    """
    return page.evaluate(
        "() => { var e = new Event('beforeunload', {cancelable: true}); "
        "window.dispatchEvent(e); return e.defaultPrevented; }")


# The dirty bar's own wait helpers. The bar's words are read off its own data-dirty-*
# attributes, restated by companion/static/dirty-state.js's own header, rather than hardcoded
# here in English, so a check works unchanged whichever shipped language the page is in.
def _wait_for_bar(page, timeout=5000):
    """Waits, via wait_for_function rather than a sleep, for [data-dirty-bar] to lose its
    `hidden` attribute — the bar revealing itself once dirty-state.js's updateBar() has
    recorded at least one real difference from the page's load-time snapshot.
    """
    page.wait_for_function(
        "() => {"
        " var el = document.querySelector('[data-dirty-bar]');"
        " return !!el && !el.hidden;}",
        timeout=timeout)


def _wait_for_bar_hidden(page, timeout=5000):
    """The inverse of `_wait_for_bar()`: waits for the bar to be hidden again, e.g. after a
    fresh script-enabled load, after Annuler, or after Save's navigation lands.
    """
    page.wait_for_function(
        "() => {"
        " var el = document.querySelector('[data-dirty-bar]');"
        " return !!el && el.hidden;}",
        timeout=timeout)


def _bar_text(page):
    """Reads `[data-dirty-count]`'s textContent — the bar's section-naming copy, in whatever
    language the page is in.
    """
    return page.eval_on_selector("[data-dirty-count]", "el => el.textContent")


def _save_via_bar(page, timeout=5000):
    """Clicks the bar's own Save (`[data-static-save-fallback]`, `form="settings-form"`) and
    waits for the real navigation it causes, never a same-page DOM update: a successful save
    redirects to the scoped page's GET route, a rejected one re-renders the same page at 200
    with inline errors. Either way the browser navigates, so any DOM handle captured before this
    call is stale the instant it returns — re-query by selector afterwards.
    """
    # Wait for the click target's own visibility on its own clock, before
    # expect_navigation()'s clock starts, so an actionability poll here cannot eat the
    # navigation wait's budget too.
    page.wait_for_selector("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR, state="visible")
    with page.expect_navigation(timeout=timeout):
        page.click("[%s]" % config_page.STATIC_SAVE_FALLBACK_ATTR)


def _commit_field(page, selector):
    """Fires the real `change` event dirty-state.js's document-level listener waits for.
    `locator.fill()` dispatches `input` only, never `change`, so a field filled and left there
    stays uncommitted; real keyboard typing followed by Tab/blur produces a genuine `change` and
    does not need this helper.
    """
    page.eval_on_selector(
        selector, "el => el.dispatchEvent(new Event('change', {bubbles: true}))")


# Shared measurement helpers for the drawing checks. Helpers only: this block registers no
# test of its own. They exist because the single most predictable defect in a server-rendered
# SVG drawing is one that is correct in light mode and invisible in dark, and no static scan
# can see it — the markup can be structurally perfect and still paint wrong once the cascade,
# `currentColor` and a theme token have had their say.

# The explicit themes this harness can drive, derived from the app's own vocabulary
# (layout.UI_THEME_CHOICES) so a renamed choice fails here instead of silently measuring
# nothing. "auto" is excluded on purpose: style.css declares no override rule for
# `data-ui-theme="auto"`, so it resolves to whatever the host OS prefers, which is the one
# thing a measurement must not depend on.
UI_THEME_AUTO = "auto"
UI_THEMES_EXPLICIT = tuple(
    t for t in layout.UI_THEME_CHOICES if t != UI_THEME_AUTO)

# Set an explicit theme, sample the paint it produces, and leave the page on the requested one.
# Every read goes through getComputedStyle, a forced style flush that resolves every pending
# recalculation before answering, so the read itself is the wait — no sleep or timeout needed.
# `document.body` is the witness because style.css's `body` rule is where both inverting tokens
# are actually spent, so this reads real paint rather than a custom property's declared text.
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
    """Put an already-loaded `page` into an explicitly named theme and return the resolved
    paint: {"theme", "canvas", "text"}.

    Sets `html[data-ui-theme]` rather than `emulate_media`/`color_scheme`: that is what the
    app's own theme picker sets, and style.css's override blocks take precedence over
    `prefers-color-scheme`. Works with scripts blocked too, since `page.evaluate` runs outside
    page script execution and the CSS cascade is not scripts-gated. Samples both themes and
    raises unless they genuinely differ, so a dropped override rule cannot pass vacuously.
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


# The SVG initial values (`fill: black`, `stroke: none`) Chromium computes when nothing in the
# cascade reaches an element — the signature of a shape that inherited no colour and painted
# the SVG default instead of a theme token. `rgb(0, 0, 0)` is a safe sentinel here because
# neither theme's --color-text resolves to pure black, so a token-painted shape can never
# legitimately land on it.
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
    """Read the resolved paint the browser computed for the first element matching `selector`
    — never the attribute, never the class. Returns {"selector", <prop>: value, ...,
    "svg_default": (props,)}.

    getComputedStyle has already run the cascade and resolved `currentColor`/custom properties,
    so this is the only way to tell a shape painted by a theme token from one painted by the SVG
    default; a source scan of the markup cannot see what a class resolves to. `svg_default`
    names every requested property indistinguishable from its SVG initial value — a shape that
    legitimately declares `stroke: none` reports it too, which is correct, not a false positive.
    Raises rather than returning a sentinel when nothing matches, so an empty-page measurement
    cannot be silently forgotten by a call site.
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


# `document.documentElement`, matching this file's other page-level overflow checks (they
# compare documentElement.scrollWidth against the viewport, and both boxes report the same
# number here). A `.data-table-wrap` overflowing its own box leaves scrollWidth unmoved, so this
# helper does not double-count wrap-level overflow; the escaped-element list is diagnostic only,
# never an independent failure condition.
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


# The ring's own ink extent, in viewBox user units. getBBox() excludes the stroke, so the
# resolved stroke-width is read alongside it and half of it added on every side here, in the
# open, since that half-stroke is the property under test.
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
    """Whether the page itself scrolls horizontally. Returns "" when it does not, and a
    failure sentence naming both measurements when it does, matching this file's
    `_assert_clean` idiom.

    `where` names the surface being measured; the width is appended by this helper, so folding
    the width into `where` too would duplicate it. `expected_width`, when given, asserts the
    measurement was taken at the viewport the caller believes it built.

    Compares documentElement.scrollWidth against its own clientWidth, strictly greater, no
    tolerance: clientWidth is the viewport's own content box, the box a scrollbar would appear
    for, rather than the width the caller requested.
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


# Four control-contract helpers shared by the richer form controls: each one is operable with
# scripts blocked, operable from the keyboard with no pointer, keeps a hit target at the 360px
# floor, and stays legible in both themes. A no-js proof is not "it renders" — a control can
# render perfectly with scripts blocked and save nothing, so the first helper below operates
# the control, submits its real form, reloads, and reads the value back from disk.

# 1. Operate, submit, persist — with scripts blocked.

# Locates every form control posting under one `name`, sets it via the browser's own mechanism
# (never a Playwright coordinate interaction — see `_click_control()`'s docstring for why a
# coordinate click can miss a visually-hidden radio), and reports what happened. Controls are
# collected by comparing `.name` rather than a `[name="..."]` selector, so a field name needing
# CSS escaping cannot silently zero-match.
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

# The submission itself, re-resolving the form from the same field name so nothing has to be
# carried across the two evaluations. A visible submit button is preferred over
# `form.requestSubmit()`, since that is the affordance a scripts-blocked visitor can actually
# press; `click()` carries the submitter's name/value and runs native constraint validation,
# which `form.submit()` would skip.
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


def _persist_without_js(make_context, base_url, route, field, value, read_back,
                        viewport=None, restore=True, shows_back=True,
                        cookies=None):
    """Operate a native control with scripts blocked, submit its form, reload the route, and
    prove the value survived on disk, not merely on the page.

    Returns {"field", "set", "held", "reloaded", "stored", "before", "submitted_via",
    "restored"}; raises AssertionError on failure rather than returning a verdict string.

    The verdict is `read_back()`, a caller-supplied reader of the real state directory, compared
    as text — the reloaded DOM is corroboration only, since a rejected submission can echo back
    into the field. `shows_back=False` opts out of that DOM corroboration for write-only fields
    like `notifications_topic_url`. `restore=True` (default) puts the setting back via the same
    sequence as its last act; `cookies` passes through to `_no_js_page()` for language-cookie
    coverage. Runs entirely inside `_no_js_page()`, keeping this file's one scripts-blocked call
    site to one.
    """
    before = read_back()
    result = _persist_once(
        make_context, base_url, route, field, value, read_back, viewport,
        shows_back, cookies)
    result["before"] = before
    result["restored"] = None
    if restore and before is not None and str(before) != str(value):
        back = _persist_once(
            make_context, base_url, route, field, str(before), read_back, viewport,
            shows_back, cookies)
        result["restored"] = back["stored"]
    return result


def _upload_without_js(make_context, base_url, route, input_selector, submit_selector,
                       source_path, read_back, serve_path, viewport=None,
                       cookies=None):
    """`_persist_without_js()`'s file-input variant: `<input type="file">` is the one native
    control whose `.value` a script may not write, so the file goes in through
    `page.set_input_files()` (CDP's `DOM.setFileInputFiles`, works with scripts blocked) and the
    form is submitted via its real submit button.

    Otherwise the same discipline: runs entirely inside `_no_js_page()`; the verdict is read
    back from disk, never from the page, since a rejected upload can redirect back to a page
    that looks like success. It additionally fetches `serve_path` by navigating to it (never
    `page.request`, which does not carry the session cookie on this tree's Playwright and would
    silently hit the login redirect), so a stored-but-not-served illustration is caught too.

    Returns {"before_len", "landed", "stored", "stored_len", "served_status", "served",
    "served_len", "gate"}; raises AssertionError on failure. `read_back` is a zero-argument
    callable returning the stored bytes or None, reading the real state directory.
    """
    before = read_back()
    with _no_js_page(make_context, base_url, route, viewport=viewport,
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


def _persist_once(make_context, base_url, route, field, value, read_back, viewport,
                  shows_back, cookies=None):
    """One operate-submit-reload-verify pass, split out so `_persist_without_js()`'s restore
    step is the same sequence as its measurement rather than a second, hand-written one.
    """
    with _no_js_page(make_context, base_url, route, viewport=viewport,
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

        # A genuine second GET, not page.reload(): the save's redirect target is not
        # necessarily the route under test, and this fetches it fresh.
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


# 2. Keyboard-only operation, with the pointer-free claim measured.

# Arms a capture-phase recorder for every pointer-ish event on the document, so "no pointer was
# involved" is a measurement of the page rather than merely a promise that the harness itself
# avoided calling a pointer API.
#
# A native radiogroup's ArrowDown activation behaviour fires a real `click` event on the
# selected radio, so `click` cannot simply be logged unconditionally without misreporting
# genuine keyboard operation as pointer-driven. The discriminator is provenance, not the event
# name: a pointer-driven `click` carries `detail >= 1` and a `pointerType`; a click synthesized
# by keyboard activation or `el.click()` carries `detail === 0` and no `pointerType`. So
# `click`/`dblclick`/`contextmenu` are logged only with that provenance, while genuinely
# pointer-only events (pointer*/mouse*/touch*) are logged unconditionally.
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

# The recorder's own proof of life, dispatched only after the measurement above has been
# taken, so it can never pollute what it verifies.
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
    """Drive a control with the keyboard alone and report what it did, having measured that
    not one pointer event fired while doing it.

    Returns {"selector", "keys", "value", "checked", "group", "active", "pointer_events",
    "recorder_proved"}; raises AssertionError when the element cannot be focused, a pointer
    event did fire, or the recorder could not prove itself.

    Focus is taken with `el.focus()`, never a click, matching `_click_control()`'s reasoning for
    using the element's own API. Keys are pressed through `page.keyboard`, not dispatched as
    synthetic KeyboardEvents: a native radiogroup's arrow-key selection is the browser's own
    default action and only runs for trusted events, so a synthetic dispatch would misreport a
    working radiogroup as not keyboard-operable. The recorder proves itself by dispatching one
    synthetic pointer event after measuring and confirming it was caught, so a listener that
    never ran cannot report a vacuous "zero pointer events". This helper refuses to run with
    scripts blocked: listeners installed via `page.evaluate` never fire in a
    `java_script_enabled=False` context, so its self-test would fail; scripts-blocked keyboard
    operation is proven by `_persist_without_js()` instead.
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


# 3. The hit area the browser really hit-tests, at a real viewport.

# The established touch-target floor, in both axes. Named once here so five control plans do
# not each retype it.
MIN_HIT_TARGET_PX = 44

# Measures the visual box, confirms the centre is genuinely reachable, then finds how far past
# each edge the browser still resolves a hit to this element. `getBoundingClientRect()` alone
# understates a synthesized target (a pseudo-element's `inset` has no box of its own to read)
# and overstates an occluded one (its rect is unchanged by a sticky bar or overlay covering it).
# `document.elementFromPoint()` is the browser's real hit-test and answers both: the centre is
# probed first (occlusion), then each edge is pushed outward by binary search for as long as the
# hit still resolves to this element or a descendant (synthesis). Bounded by `max` and monotonic
# by construction; reports `clipped` when a probe left the viewport, at which point the
# measurement is a floor, safe for a caller comparing against 44 since a clipped result can only
# be too small.
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
    """The element's visual box and the box the browser actually hit-tests to it, both axes,
    at whatever viewport `page` is at.

    Returns {"selector", "visual": (w, h), "hit": (w, h), "reach": (left, right, up, down),
    "clipped", "viewport"}; raises AssertionError when the selector matches nothing, the
    element has no box, or its own centre hit-tests to something else (an occluded control,
    invisible to a rectangle measurement). See the module comment above `_HIT_AREA_PROBE` for
    why `elementFromPoint` is used instead of `getBoundingClientRect()` alone.

    The search counts whole pixels outward from the centre, each sampled at its own centre
    (x + 0.5): a fractional binary search inflates every answer by about a pixel, which matters
    at a 44px floor. The answer can therefore exceed the CSS box by about a pixel per axis when
    an edge lands off the pixel grid and the hit region snaps outward — that is real browser
    behaviour, not an artefact, so a floor comparison here is permissive by up to a pixel.
    The element is scrolled to the viewport centre first, since an occlusion verdict that
    depends on scroll position would be intermittently red. `max_expand` bounds the outward
    search past the 44px floor without reporting a large clickable parent's size, since `owns()`
    requires the hit to be this element or a descendant, never an ancestor.
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


# A real, trusted file drop. The drop handler refuses an event whose `isTrusted` is false, and
# every drop a page script can construct is untrusted by definition, so a synthetic
# `dispatchEvent("drop")` would only measure the refusal. Chromium's DevTools protocol
# dispatches drag events through the same input pipeline a real pointer uses, with a `files`
# list the browser turns into genuine File objects, so the guard stays intact and the gesture is
# measured end to end. The drag-over state is sampled between dragOver and drop, while the
# browser is genuinely in that state, rather than at a guessed instant after a sleep.
def _drop_files(page, selector, paths):
    """Dispatch a trusted file drop of `paths` onto `selector`'s centre.

    Returns {"active_during_drag", "active_after_drop", "paint_during_drag", "paint_at_rest"}:
    the drag-state attribute sampled on both sides of the drop, plus the resolved paint in each
    state, so "the state is visible" is a measurement rather than a class name.
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
    """`_hit_area()` plus the floor comparison, so callers do not each retype it. Returns the
    measurement; raises when either axis is under `minimum`.
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


# 4. The `.js` gate, asserted in both directions.

# The tabbable-candidate vocabulary, in one place. `[tabindex]` is included and filtered on its
# resolved value rather than matched as `[tabindex="-1"]` in the selector, because a
# programmatically-set `el.tabIndex = -1` leaves no attribute to match.
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

# Where focus currently is, and whether it is inside the gated wrapper. Read after every Tab
# press, since a `focusin` recorder does not fire in the scripts-blocked context this walk runs
# in. The cycle detector marks the element itself rather than comparing a name, because two
# different controls can share a class string and a name comparison stopped the walk early.
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


def _assert_js_gate(make_context, base_url, route, selector, viewport=None,
                    prepare=None, arm=None, tab_budget=None):
    """Prove a `.js`-gated wrapper in both directions: it occupies no space and holds nothing
    a keyboard can reach when scripts are blocked, and it occupies space when they are not.

    Returns {"blocked": {...}, "enabled": {...}}; raises AssertionError on either direction.
    Both directions matter: asserting only the blocked half passes against a gate stuck shut
    forever, and asserting only the enabled half passes against an affordance that renders and
    does nothing without its script.

    "Holds nothing focusable" is asserted by walking the tab order rather than reading the
    computed `display`, since a gate hidden via `visibility`/`opacity` instead of `display: none`
    still removes nothing from the tab order — the property under test is reachability, so
    reachability is what is measured. The walk is skipped, with `candidates: 0` recorded, when
    the wrapper has no focusable candidate at all, since that already answers the assertion.

    `prepare` runs on both pages, right after the route loads, to put the subject into the state
    it is meant to be judged in; it must do the same thing to both pages or the two directions
    stop being the same measurement taken twice. `arm` runs on the scripts-enabled page only,
    after `prepare`, for the state change that does the revealing (a plain `.js` gate needs
    none; a script-revealed wrapper like `.dirty-bar` does). `tab_budget` defaults to the page's
    own count of focusable candidates plus two, so a page that grows a control is not silently
    under-walked.
    """
    probe_args = {"selector": selector,
                  "focusable": _FOCUSABLE_CANDIDATE_SELECTOR}
    with _no_js_page(make_context, base_url, route, viewport=viewport) as page:
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
    context = make_context(**extra)
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


# 5. Both themes, and the page-overflow floor — both already owned.

def _in_both_themes(page):
    """Yield `_set_ui_theme(page, t)`'s measurement for each of this app's explicit themes, in
    order, so "assert this in both themes" is one `for` line at a call site. Adds only the loop
    on top of `_set_ui_theme()`'s own guarantees; not a second theme mechanism. Leaves the page
    on the last theme yielded — a caller that cares should call `_set_ui_theme()` again itself.
    """
    for theme in UI_THEMES_EXPLICIT:
        yield _set_ui_theme(page, theme)


# The 360px body-overflow measurement is `_assert_no_page_overflow()` above; every control
# plan in this phase calls it directly. A second overflow helper would be a third convention in
# one file about what "the page" means, which is how checks come to disagree.


# 6. Display's own rendered page height.
#
# A harness helper rather than a number typed into a document by hand, so the before-number and
# the after-number come from the same instrument. It deliberately asserts no target — the number
# it reports is the verdict — but does assert that the instrument is pointed at the right thing:
# the measurement was taken at the requested width, the document is really the authenticated
# Display page (not its login redirect), and the page is genuinely taller than the viewport.
# `scrollHeight` on documentElement, not `body`, since `body` can be shorter than the document
# when a child escapes it — the same box `_assert_no_page_overflow()` uses for the horizontal axis.
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


def _display_page_height(make_context, base_url, viewport):
    """Display's full rendered document height at `viewport`, with the instrument proved to be
    pointed at Display.

    Returns the probe's own dict (height, clientWidth, clientHeight, scrollWidth, heading,
    themeRadios); raises AssertionError when the measurement cannot be trusted.

    Scripts are enabled here, deliberately: the height a visitor sees includes
    `theme-preview.js` collapsing panels at load, so a scripts-blocked measurement would report
    a page nobody with a default browser ever sees.
    """
    context = make_context(viewport=viewport)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        seen = page.evaluate(
            _DISPLAY_HEIGHT_PROBE,
            # The theme-radio guard below still holds unchanged: the departures palette
            # renders exactly `len(device_config.THEME_IDS)` radios named `theme`, the same
            # count the retired chip grid always rendered.
            {"headingId": config_page.ASPECT_HEADING_ID})
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
            "_display_page_height: the document at %dpx carries no Aspect "
            "heading — this is not the authenticated Display page "
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


# 7. Agreement — the relationship between surfaces, not just each surface on its own.
#
# A control can ship with each surface individually, permanently correct (the arc correct
# server-side, the handles asserted to move, the value asserted to persist) while the page as a
# whole disagrees with itself, e.g. an interaction that moved the handles without moving the
# arc. So the shape below is deliberately not "one check per surface": the subject is the set of
# decoded values, asserted to have exactly one member. Two further clauses close the vacuity
# gaps: without "equals what the interaction requested", four frozen surfaces agreeing on the
# old value would still pass; without "differs from what was there before", an interaction that
# did nothing at all would too.


def _canonical_surface_value(value):
    """One canonical, hashable, comparable form for a decoded surface value, so `(1380, 420)`
    and `[1380, 420]` are the same reading rather than two members of a set. Raises on anything
    that cannot be made hashable, rather than falling back to `repr()`, which would make every
    unhashable value agree with itself and nothing else by accident.
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
    """Every surface and what it decoded to, in the order the caller listed them — never only
    the mismatching pair, since a reader needs to see all of them to tell which surface is the
    one that did not follow.
    """
    return "; ".join("%s -> %r" % (label, value) for label, value in decoded.items())


def _assert_surfaces_agree(page, surfaces, requested, before, where):
    """Decode N rendered surfaces into one canonical value and assert they agree, that the
    agreed value is the one the interaction requested, and that it differs from the
    pre-interaction value.

    `surfaces` is an ordered mapping of a surface label to a zero-argument callable returning
    that surface's decoded value, since the number of surfaces describing one value is a
    property of the control, not of this helper. Returns the `{label: decoded}` mapping on
    success; raises AssertionError on failure.

    Three separate assertions with three separate messages, not collapsed into one boolean,
    because they fail for three unrelated reasons a reader needs told apart: the surfaces
    disagree, they agree on the wrong value (the page froze together), or they agree on the
    value that was already there (nothing happened). This helper drives no state change of its
    own — it reads what the caller's interaction already did, which is what lets it compose
    with `_persist_without_js()` rather than wrap it.
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


# 8. The arc as a number — resolved geometry, read back out of the browser.
#
# The declared SVG attribute can stay correct for the saved value while the handles and fields
# move away from it, so what is read here is the resolved value: what the browser actually
# painted after script ran and any `.js`-scoped stylesheet rule overrode the presentation
# attribute. Measured on this tree, the resolved `stroke-dasharray` is comma-separated,
# unit-suffixed and rounded to three decimals (parsed as numbers, never string-compared), and
# the resolved `transform` is a matrix rather than the `rotate()` that was written, so the angle
# is recovered via atan2. The resolved dash is in SVG user units — the same units
# QUIET_DIAL_RADIUS is in — so this decoder skips getBoundingClientRect and needs no `scale()`
# correction. The canonical unit is minute-of-day, matching what the handles already publish via
# `aria-valuenow`, so the agreement helper never has to invent a tolerance between two rounding
# schemes.

_QUIET_ARC_SELECTOR = "." + config_page.QUIET_DIAL_ARC_CLASS
# The emitter's own quarter-turn correction, read rather than retyped as -90, so this decoder
# stays in sync with quiet_dial_svg()'s own rotation.
_QUIET_ARC_TWELVE_OCLOCK_DEG = config_page._QUIET_DIAL_TWELVE_OCLOCK_DEG
MINUTES_PER_DAY = 24 * 60

# Any signed decimal, in any of the forms a resolved CSS value can put one in. Deliberately
# tolerant about separators and units, since those are the browser's business, not this
# decoder's.
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
    """The resolved value of one property — custom or standard — on the one element `selector`
    matches, as a trimmed string.

    Raises AssertionError naming the selector, property and document when the selector matches
    anything other than exactly one element, or when the resolved value is empty. Never returns
    a default: a reader that answered "" or 0 for an absent arc would let
    `_assert_surfaces_agree()` pass on a document missing the arc entirely. Requires exactly one
    element, not `.first`, since a selector matching two arcs has an ambiguous answer.
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

    Rounded to the nearest minute on purpose: the resolved dash comes back at three decimals
    where the server emitted four, so a paint-decoded fraction is never bit-identical to the
    server's. Minutes are the unit the handles already publish, so rounding to it is
    canonicalisation, not a tolerance — a surface a whole minute out still reads differently.
    """
    return int(round(fraction * MINUTES_PER_DAY)) % MINUTES_PER_DAY


def _quiet_arc_minutes(page, where, selector=_QUIET_ARC_SELECTOR,
                       radius=None):
    """The quiet-hours arc, read back off what the browser painted, as a canonical
    `(start_minute, end_minute)` pair of ints.

    Inverts `draw.unit_circle_dash_array()`'s arithmetic (drawn dash over full circumference is
    the sweep fraction) and `quiet_dial_svg()`'s quarter-turn correction. `radius` defaults to
    `config_page.QUIET_DIAL_RADIUS`, the same constant the emitter divides by, rather than a
    number retyped here that could silently go stale.

    Raises AssertionError, naming what was read, when either property is missing, the transform
    is not a 2-D matrix, or neither parses as a number; never returns a default.

    Does not wait for anything — sampling at the right instant is the caller's job, done by
    hooking the event the browser actually emits, since this file has lost checks to a guessed
    instant before.
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


# Module-level because it is shared by both the quiet-hours dial checks and the settings
# dirty-bar audit.
def _handle_sel(field):
    return '[data-value-field="%s"] [data-value-handle]' % field


def _fraction_pair_minutes(page, selector, start_property, sweep_property,
                           where):
    """The quiet window as `(start_minute, end_minute)`, decoded from a start fraction and a
    sweep fraction published as custom properties on `selector` — the shared ancestor, not the
    circle. Reading both ends of that chain with the same canonical output is what lets
    `_assert_surfaces_agree()` catch "the ancestor was updated and the paint did not follow".

    The second property is the sweep, not the end — a contract, not a convenience: for a
    wrapping window an end fraction and a sweep fraction diverge (23:00-07:00 is end 0.2917,
    sweep 0.3333), and mixing them up would silently report 07:00-07:00 as agreement.

    Raises through `_resolved_property()` when either property is absent, and on its own when
    either does not parse.
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


# The live caption reads "08:00 -> 18:00 . 8h", the same form the server emits at load: both
# endpoint spans are painted through a zero-padded HH:MM codec after any interaction. Matching
# "HH:MM" tokens rather than bare digit runs matters because a bare-digit-run parse would
# misparse "08:00" into "08"/"00" and silently report the wrong pair.
_CAPTION_TOKEN_RE = re.compile(r"(\d{1,2}):(\d{2})")
_QUIET_READOUT_SELECTOR = "." + config_page.QUIET_DIAL_READOUT_CLASS


def _quiet_caption_minutes(page, where, selector=None):
    """The quiet-hours caption, read back off what the browser is currently showing, as a
    canonical `(start_minute, end_minute)` pair of ints — the fourth surface
    `_assert_surfaces_agree()` checks.

    Reads `textContent`, not `inner_text()`: the paragraph is `aria-hidden="true"`, and
    `textContent` unambiguously picks up every character in document order regardless of
    layout. The first two "HH:MM" tokens are the pair, in document order (start span, then end
    span); the duration segment's wording (e.g. "8h") contains no "HH:MM"-shaped substring, so
    it never contributes a false third member.

    Raises AssertionError, with the caption's actual text quoted, when fewer than two "HH:MM"
    tokens are present, rather than silently returning a plausible-looking pair from
    unparseable text.
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


# The duration span's own selector — it carries VALUE_CONTROL_READOUT_BASE_ATTR and neither
# endpoint span does, so this is unique within the readout paragraph without a new class.
_QUIET_DURATION_SELECTOR = "%s [%s]" % (
    _QUIET_READOUT_SELECTOR, layout.VALUE_CONTROL_READOUT_BASE_ATTR)


def _quiet_caption_shape(text):
    """`text`'s structure, never its value: every "HH:MM" token becomes the literal placeholder
    "HH:MM" and every remaining digit becomes "#", so two captions naming different
    times/durations but sharing the same separators, spacing and token order compare equal,
    while a caption whose form actually changed (dropped separator, missing duration,
    reordered pair) does not.
    """
    shaped = _CAPTION_TOKEN_RE.sub("HH:MM", text)
    return re.sub(r"\d+", "#", shaped)


def _quiet_duration_span_text(page, where):
    """The duration span's own currently displayed text, read the same `textContent` way
    `_quiet_caption_minutes()` reads the whole caption.
    """
    text = page.locator(_QUIET_DURATION_SELECTOR).text_content()
    if text is None:
        raise AssertionError(
            "_quiet_duration_span_text: %s — %r has no text content at all on %s"
            % (where, _QUIET_DURATION_SELECTOR, page.url))
    return text


def _expected_quiet_duration_text(page, requested, where):
    """The duration text `page`'s own duration span should show for the `requested`
    (start_minute, end_minute) pair: the wrapped difference between the two ends, bucketed with
    `layout._age_bucket()`, and worded with whichever `layout.DURATION_ATTRS` the page itself
    carries — read off the span's own attribute, never hardcoded, so this check cannot desync
    from the catalogue the server actually shipped.
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


# 9. "Shorter, and still refusing" — one read, two facts.
#
# The battery gauge prints an absolute days figure only when this frame's own observed history
# supports one; a shorter sentence that starts naming a number is a regression, not a cut. So
# "it got shorter" and "it still refuses to claim a figure" are asserted about one read of one
# rendering: asserted separately, a cut proven on one page state and a refusal proven on another
# would report success about a rendering that never existed. Whitespace is normalised to single
# spaces before counting, since the rendered textContent carries the markup's own indentation
# and a baseline should be about copy, not formatting.

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
    """Every element `selector` matches, read once, joined in document order and
    whitespace-normalised.

    Joined rather than restricted to one element because some regions are genuinely plural
    (`wake_gauges_html()` emits two gauges as two sibling `<p>`s), so measuring only the first
    would report a card half cut. Raises when nothing matches, rather than defaulting to zero
    length, since that would call a deleted region a successful cut.
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
    """One region, read once; two assertions against that single read: it is strictly shorter
    than `baseline_chars`, and `forbidden` does not match it.

    Returns `_region_text()`'s measurement. Raises AssertionError with two distinct messages,
    since the two failures mean opposite things: the first says the cut never happened, the
    second says the cut went through something that was holding a refusal up.

    `baseline_chars` must be strictly greater than the measurement, not "at most", since a cut
    that changed nothing is exactly the claim this refuses. `forbidden` is a regex describing
    the claim the shortened copy still must not make, searched against the same normalised
    string the length was taken from.
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
    """How many elements each named markup shape has on this page, as `{label: count}`.

    Asserts nothing about the subject, on purpose: it exists to derive a count by running
    against the real page rather than by grepping markup by hand. Zero is a legitimate answer
    and is returned as one.
    """
    seen = page.evaluate(_MARKUP_INVENTORY_PROBE, {"shapes": dict(shapes)})
    if seen.get("error") == "bad-selector":
        raise AssertionError(
            "_markup_inventory: %r (for %r) is not a selector the browser "
            "will accept on %s (%s). An instrument that cannot be aimed "
            "counts nothing"
            % (seen["selector"], seen["label"], page.url, seen["detail"]))
    return seen["counts"]
