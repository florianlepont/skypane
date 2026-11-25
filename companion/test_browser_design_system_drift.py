"""Real-browser drift check between the design system and the served site.

`companion/testdata/design_system_tokens.json` records the numbers the design-system skill
states: colour tokens in Light and Dark, radii, spacing steps, type sizes, motion tokens, the
44px target and the 4.5:1 contrast of the stated pairs. Each test loads the served site in a
browser and compares what the browser computes with that manifest, so a token changed in the
stylesheet without the manifest (and the skill) fails here.

The known limit: the manifest is a hand-copied transcript of the skill. These tests prove the
served site equals the manifest; that the manifest equals the skill is checked by review only.

A value is compared in its computed form: both the token and the manifest value are assigned to
a probe element and the browser's own serialisation is compared, so `#F1F3F6`, `rgb(...)` and
`rgba(...)` spellings cannot cause a false mismatch, and an undefined token (which falls back to
the inherited or initial value) can never equal a manifest value.
"""
import contextlib
import copy
import json
import os

import pytest

import skypane_contrast_check
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _login,
    _set_ui_theme,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

# Home (a personal page with the tab bar and the glass shell) and the admin Components page
# (the living catalogue of every control).
ROUTES = ("/", "/components")

# Tokens that an area stylesheet, not the shared one, supplies in Auto-dark: the Location sheet
# loads on its own page only.
AUTO_DARK_NOT_ON_EVERY_PAGE = ("--color-map-ground",)

# Resolves each check through a probe element and returns the browser's own serialisation of the
# token and of the manifest value. `unset` is the value an undefined token falls back to, so a
# manifest value equal to it, or a token that is missing, cannot pass.
_RESOLVE = """checks => {
  const host = document.createElement('div');
  host.style.cssText = 'color: rgb(1, 2, 3); letter-spacing: 7.77px;';
  document.body.appendChild(host);
  const prop = {color: 'color', length: 'letterSpacing', time: 'transitionDuration',
                easing: 'transitionTimingFunction'};
  const resolve = (name, value) => {
    const el = document.createElement('span');
    el.style[name] = value;
    host.appendChild(el);
    const out = getComputedStyle(el)[name];
    el.remove();
    return out;
  };
  const out = checks.map(c => {
    if (c.kind === 'raw') {
      const actual = getComputedStyle(document.documentElement).getPropertyValue(c.token).trim();
      return {token: c.token, expected: c.expected, actual: actual, problem: null};
    }
    const name = prop[c.kind];
    const expected = resolve(name, c.expected);
    const unset = resolve(name, 'unset');
    return {token: c.token, expected: expected,
            actual: resolve(name, 'var(' + c.token + ')'),
            problem: expected === unset ? 'the manifest value does not parse' : null};
  });
  host.remove();
  return out;
}"""

# The composited colour of `fg` painted over `bg` for each pair, as hex strings: a canvas pixel,
# so a translucent colour (secondary ink is the text colour at 70%) is measured as drawn.
_PAIR_PIXELS = """pairs => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const colour = (token) => {
    const el = document.createElement('span');
    el.style.color = 'var(' + token + ')';
    host.appendChild(el);
    const out = getComputedStyle(el).color;
    el.remove();
    return out;
  };
  const hex = (d) => '#' + [d[0], d[1], d[2]].map(v => v.toString(16).padStart(2, '0')).join('');
  const ctx = document.createElement('canvas').getContext('2d', {willReadFrequently: true});
  const out = pairs.map(p => {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = colour(p.bg); ctx.fillRect(0, 0, 1, 1);
    const bg = hex(ctx.getImageData(0, 0, 1, 1).data);
    ctx.fillStyle = colour(p.fg); ctx.fillRect(0, 0, 1, 1);
    return {name: p.name, fg: hex(ctx.getImageData(0, 0, 1, 1).data), bg: bg};
  });
  host.remove();
  return out;
}"""

# Visible elements of each selector: their height, and whether an accessible name exists.
_TARGETS = """args => {
  const visible = (el) => el.getClientRects().length > 0 &&
    getComputedStyle(el).visibility !== 'hidden';
  const named = (el) => !!((el.getAttribute('aria-label') || '').trim() ||
    (el.getAttribute('aria-labelledby') || '').trim() ||
    (el.textContent || '').trim() || (el.getAttribute('title') || '').trim());
  const sample = (sel) => Array.from(document.querySelectorAll(sel)).filter(visible);
  const heights = {};
  for (const sel of args.selectors) {
    heights[sel] = sample(sel).map(el => ({
      height: el.getBoundingClientRect().height, label: el.className || el.tagName}));
  }
  const unnamed = [];
  for (const sel of args.named) {
    for (const el of sample(sel)) { if (!named(el)) unnamed.push(sel + ' ' + (el.className || '')); }
  }
  return {heights: heights, unnamed: unnamed,
          scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth};
}"""


def _manifest_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "testdata",
                        "design_system_tokens.json")


@pytest.fixture(scope="module")
def manifest():
    with open(_manifest_path(), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """One read-only seeded server shared by every check in this module."""
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


@contextlib.contextmanager
def _page_at(new_context, server, route, viewport, theme=None, **context_kwargs):
    """A signed-in page on `route`, loaded, in an explicit theme when `theme` is given."""
    context = new_context(viewport=viewport, **context_kwargs)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
        if theme is not None:
            _set_ui_theme(page, theme)
        yield page
    finally:
        context.close()


def _checks(kind, tokens):
    return [{"kind": kind, "token": token, "expected": value} for token, value in tokens.items()]


def _colour_checks(manifest, theme, skip=()):
    return _checks("color", {token: value for token, value in manifest["colors"][theme].items()
                             if token not in skip})


def _scale_checks(manifest, theme):
    """Radii, spacing, type, tab-bar geometry, motion tokens and the raw-valued tokens."""
    raw = dict(manifest["raw"]["any"], **manifest["raw"][theme])
    return (_checks("length", manifest["lengths"]) + _checks("time", manifest["times"])
            + _checks("easing", manifest["easings"]) + _checks("raw", raw))


def _mismatches(page, checks):
    """The checks the served page does not satisfy, each with the token and both values."""
    results = page.evaluate(_RESOLVE, checks)
    assert len(results) == len(checks)
    return [r for r in results if r["problem"] or r["actual"] != r["expected"]]


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("route", ROUTES)
def test_served_colour_tokens_equal_the_manifest(new_context, server, manifest, route, theme):
    with _page_at(new_context, server, route, VIEWPORT_MIN_SUPPORTED, theme=theme) as page:
        assert _mismatches(page, _colour_checks(manifest, theme)) == []


def test_auto_dark_serves_the_dark_colour_tokens(new_context, server, manifest):
    with _page_at(new_context, server, "/", VIEWPORT_MIN_SUPPORTED, color_scheme="dark") as page:
        assert page.evaluate("() => document.documentElement.hasAttribute('data-ui-theme')") is False
        checks = _colour_checks(manifest, "dark", skip=AUTO_DARK_NOT_ON_EVERY_PAGE)
        assert _mismatches(page, checks) == []


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("route", ROUTES)
def test_served_scale_tokens_equal_the_manifest(new_context, server, manifest, route, theme):
    with _page_at(new_context, server, route, VIEWPORT_MIN_SUPPORTED, theme=theme) as page:
        assert _mismatches(page, _scale_checks(manifest, theme)) == []


@pytest.mark.parametrize("viewport", (VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP),
                         ids=("phone", "desktop"))
def test_the_page_title_size_follows_the_manifest_per_viewport(
        new_context, server, manifest, viewport):
    width = str(viewport["width"])
    expected = {token: sizes[width]
                for token, sizes in manifest["responsive_lengths"].items()}
    with _page_at(new_context, server, "/components", viewport) as page:
        assert _mismatches(page, _checks("length", expected)) == []


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_stated_pairs_reach_the_contrast_floor(new_context, server, manifest, theme):
    pairs = manifest["contrast"]["pairs"]
    floor = manifest["contrast"]["floor"]
    with _page_at(new_context, server, "/", VIEWPORT_MIN_SUPPORTED, theme=theme) as page:
        painted = page.evaluate(_PAIR_PIXELS, pairs)
    assert len(painted) == len(pairs)
    for pair in painted:
        ratio = skypane_contrast_check.contrast_ratio(pair["fg"], pair["bg"])
        assert ratio >= floor, (theme, pair["name"], pair, round(ratio, 2))


@pytest.mark.parametrize("route", ROUTES)
def test_sampled_controls_are_44px_named_and_fit_360px(new_context, server, manifest, route):
    targets = manifest["targets"]
    width = targets["min_viewport_width"]
    viewport = {"width": width, "height": VIEWPORT_MIN_SUPPORTED["height"]}
    arguments = {"selectors": targets["selectors"], "named": targets["named_icon_selectors"]}
    with _page_at(new_context, server, route, viewport) as page:
        found = page.evaluate(_TARGETS, arguments)
    small = [(sel, item) for sel, items in found["heights"].items() for item in items
             if item["height"] < targets["min_px"]]
    assert small == [], "controls under %dpx at %dpx wide" % (targets["min_px"], width)
    assert found["unnamed"] == []
    assert found["scrollWidth"] <= found["clientWidth"], found
    sampled = {sel: len(items) for sel, items in found["heights"].items()}
    assert sum(sampled.values()) > 0, "no control was sampled, the check would pass vacuously"


def test_a_changed_manifest_value_is_reported(new_context, server, manifest):
    """The negative case: a manifest that disagrees with the site yields a mismatch naming the
    token, and so do an undefined token and a value the browser cannot parse."""
    drifted = copy.deepcopy(manifest)
    drifted["colors"]["light"]["--color-canvas"] = "#F1F3F7"
    drifted["lengths"]["--radius-card"] = "21px"
    drifted["times"]["--motion-fast"] = "181ms"
    drifted["colors"]["light"]["--color-not-a-token"] = "#123456"
    drifted["lengths"]["--space-not-a-token"] = "4px"
    drifted["colors"]["light"]["--color-text"] = "not a colour"
    with _page_at(new_context, server, "/", VIEWPORT_MIN_SUPPORTED, theme="light") as page:
        found = (_mismatches(page, _colour_checks(drifted, "light"))
                 + _mismatches(page, _scale_checks(drifted, "light")))
        intact = _mismatches(page, _colour_checks(manifest, "light"))
    assert sorted(r["token"] for r in found) == sorted((
        "--color-canvas", "--radius-card", "--motion-fast", "--color-not-a-token",
        "--space-not-a-token", "--color-text"))
    assert intact == []
    unparsable = [r for r in found if r["problem"]]
    assert [r["token"] for r in unparsable] == ["--color-text"]


def test_a_contrast_pair_below_the_floor_is_reported(new_context, server, manifest):
    """The contrast check fails when a pair is too weak: the Light canvas against itself."""
    weak = [{"name": "canvas on canvas", "fg": "--color-canvas", "bg": "--color-canvas"}]
    with _page_at(new_context, server, "/", VIEWPORT_MIN_SUPPORTED, theme="light") as page:
        painted = page.evaluate(_PAIR_PIXELS, weak)
    ratio = skypane_contrast_check.contrast_ratio(painted[0]["fg"], painted[0]["bg"])
    assert ratio < manifest["contrast"]["floor"]
