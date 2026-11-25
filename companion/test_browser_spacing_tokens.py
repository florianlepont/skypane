"""Real-browser check that the spacing and radius tokens move no pixel.

The stylesheets name the repeated off-scale spacing values (6, 10, 12 and 14px) and radii (8, 10
and 12px) by their pixel value, next to the t-shirt scale. These tests load the served site and
assert what the browser computes:

- the new tokens are declared once, in `:root`, in the served stylesheets (they are theme-free, so
  no theme block repeats them) and resolve to their pixel value in Light and Dark;
- a table of sample elements (chip, pill, menu row, filter-bar chip, home card, list row, toast,
  table cell, dialog) has the padding, margin, gap and radius it had before the literals were
  replaced by tokens, in English and French, in both themes, at 360px with reduced motion;
- radii that no seeded page draws are checked on probe elements wearing the component class;
- every interactive sample is at least 44px tall, the page never scrolls sideways and the text of
  a sample keeps 4.5:1 against its background.
"""
import re

import pytest

import skypane_contrast_check
from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_MIN_SUPPORTED,
    _login,
    _set_ui_theme,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

NEW_SPACING_TOKENS = {"--space-6": "6px", "--space-10": "10px", "--space-12": "12px",
                      "--space-14": "14px"}
NEW_RADIUS_TOKENS = {"--radius-8": "8px", "--radius-10": "10px", "--radius-12": "12px"}
NEW_TOKENS = dict(NEW_SPACING_TOKENS, **NEW_RADIUS_TOKENS)

LANGS = ("en", "fr")
MIN_TARGET_PX = 44
CONTRAST_FLOOR = 4.5

# (route, selector, expected computed values, interactive). The expected values are the ones the
# stylesheets computed when every one of these was still a literal.
SAMPLES = (
    ("/", ".home-pill",
     {"padding": "0px 6px 0px 14px", "gap": "8px", "borderRadius": "32px"}, False),
    ("/", ".home-flight__meta", {"gap": "6px"}, False),
    ("/", ".home-stats__head", {"gap": "12px"}, False),
    ("/", ".home-strip__tiles",
     {"padding": "0px 16px 4px", "gap": "12px", "margin": "0px -16px"}, False),
    ("/flights", ".filter-chip__box",
     {"padding": "0px 14px", "gap": "4px", "borderRadius": "32px"}, True),
    ("/flights", ".filter-bar__search input",
     {"padding": "0px 16px 0px 46px", "borderRadius": "14px"}, True),
    ("/airlines", ".rarity-pill",
     {"padding": "0px 10px", "gap": "6px", "borderRadius": "32px"}, False),
    ("/display", ".refresh-pill",
     {"padding": "0px 8px", "gap": "4px", "borderRadius": "32px"}, False),
    ("/display", ".look-seg__option",
     {"padding": "0px 8px", "gap": "6px", "borderRadius": "14px"}, True),
    ("/display/special-looks", ".special-row__main", {"gap": "8px 14px"}, False),
    ("/display/special-looks", ".special-add__summary",
     {"padding": "0px 16px", "gap": "8px", "borderRadius": "22px"}, True),
    ("/display/calendar", "a.calendar-manage",
     {"padding": "0px 10px", "borderRadius": "22px"}, True),
    ("/display/calendar", ".calendar-status",
     {"padding": "8px 4px 0px", "gap": "12px", "margin": "8px 0px 0px"}, False),
    ("/components", ".row-menu__item", {"padding": "0px 16px"}, True),
    ("/components", ".data-table th", {"padding": "10px 16px"}, False),
    ("/components", ".data-table td", {"padding": "13px 16px"}, False),
    ("/components", ".toast",
     {"padding": "8px 2px 8px 12px", "gap": "12px", "borderRadius": "14px"}, False),
    ("/components", "li.entity-row", {"padding": "16px", "gap": "8px"}, False),
    ("/components", ".theme-form input[type=radio] + label",
     {"padding": "0px 12px", "borderRadius": "14px"}, True),
    ("/components", ".frame-notice__link",
     {"padding": "0px 16px", "gap": "6px", "borderRadius": "14px"}, True),
    ("/components", ".modal--compact .modal__actions", {"padding": "0px 0px 24px", "gap": "10px"},
     False),
    ("/components", "dialog.modal",
     {"padding": "22px 16px 0px", "borderRadius": "28px 28px 0px 0px"}, False),
)

# Components whose radius no seeded page draws: probe elements wearing the class are added to a
# page that links the stylesheet defining it, so the served rule's computed radius is read in the
# browser. A probe with a child tag is the `.parent child` descendant.
RADIUS_PROBES = (
    ("/", "modal__check-box", None, "8px"),
    ("/fleet", "battery-chart__empty", "b", "8px"),
    ("/fleet", "battery-chart__empty", "span", "8px"),
    ("/airlines", "airlines-tip", None, "10px"),
    ("/airlines", "airlines-gap__prefix", None, "10px"),
    ("/airlines", "airlines-thumb", None, "12px"),
    ("/airlines", "airlines-missing__slot", None, "12px"),
)
# Pages that between them link every stylesheet.
SHEET_ROUTES = ("/", "/display", "/flights", "/airlines", "/fleet", "/components")

# The computed values of each sample, with its height, whether it is shown, and the colour of its
# text against the layers painted behind it (translucent layers are composited on the canvas).
_MEASURE = """args => {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = (css) => {
    ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1);
    const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255];
  };
  const over = (top, under) => [0, 1, 2].map(i => top[i] * top[3] + under[i] * (1 - top[3]));
  const hex = (c) => '#' + c.map(v => Math.round(v).toString(16).padStart(2, '0')).join('');
  const root = getComputedStyle(document.documentElement);
  const probe = document.createElement('i');
  probe.style.color = 'var(--color-canvas)';
  document.body.appendChild(probe);
  let ground = rgba(getComputedStyle(probe).color).slice(0, 3);
  probe.remove();
  const out = args.samples.map(s => {
    const el = document.querySelector(s.selector);
    if (!el) return {selector: s.selector, found: false};
    const style = getComputedStyle(el);
    const layers = [];
    for (let n = el; n; n = n.parentElement) layers.push(rgba(getComputedStyle(n).backgroundColor));
    let under = ground;
    for (let i = layers.length - 1; i >= 0; i--) under = over(layers[i], under);
    const text = over(rgba(style.color), under);
    const box = el.getBoundingClientRect();
    const values = {};
    for (const key of Object.keys(s.expected)) values[key] = style[key];
    return {selector: s.selector, found: true, values: values, height: box.height,
            shown: box.width > 0 && box.height > 0, text: hex(text), ground: hex(under)};
  });
  return {samples: out, scrollWidth: document.documentElement.scrollWidth,
          clientWidth: document.documentElement.clientWidth,
          reduced: matchMedia('(prefers-reduced-motion: reduce)').matches};
}"""

_RESOLVE_TOKENS = """tokens => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const out = {};
  for (const [name, kind] of tokens) {
    const el = document.createElement('span');
    if (kind === 'radius') el.style.borderTopLeftRadius = 'var(' + name + ')';
    else el.style.paddingLeft = 'var(' + name + ')';
    host.appendChild(el);
    const style = getComputedStyle(el);
    out[name] = kind === 'radius' ? style.borderTopLeftRadius : style.paddingLeft;
  }
  host.remove();
  return out;
}"""

_STYLESHEETS = """async () => {
  const links = [...document.querySelectorAll('link[rel=stylesheet]')].map(l => l.href);
  return await Promise.all(links.map(async href => ({href: href,
    text: await (await fetch(href)).text()})));
}"""

_RADIUS_PROBE = """probes => {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const out = probes.map(p => {
    const parent = document.createElement('div');
    parent.className = p.parent;
    const el = p.child ? document.createElement(p.child) : parent;
    if (p.child) parent.appendChild(el);
    host.appendChild(parent);
    const radius = getComputedStyle(el).borderTopLeftRadius;
    return {parent: p.parent, child: p.child, radius: radius};
  });
  host.remove();
  return out;
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """One read-only seeded server shared by every check in this module."""
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


def _open(new_context, server, route, lang="en", theme=None, reduced_motion=None):
    """A signed-in 360px page on `route` in `lang`, in an explicit theme when `theme` is given.

    Reduced motion is the default only without a theme: with it the shell's 0.01ms transitions
    still start one, so `_set_ui_theme` would read the colour from before the switch."""
    if reduced_motion is None:
        reduced_motion = "reduce" if theme is None else "no-preference"
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion=reduced_motion)
    page = context.new_page()
    _login(page, server.base_url())
    context.add_cookies([
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page.goto(server.base_url() + route)
    page.wait_for_function("() => document.readyState === 'complete'", timeout=15000)
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _enclosing_selector(css, position):
    """The selector of the innermost rule that holds `position` in the comment-free `css`."""
    stack = []
    header_start = 0
    for index in range(position):
        char = css[index]
        if char == "{":
            stack.append(" ".join(css[header_start:index].split()))
            header_start = index + 1
        elif char in "};":
            if char == "}" and stack:
                stack.pop()
            header_start = index + 1
    return stack[-1] if stack else ""


def test_the_new_tokens_are_declared_once_in_root_and_in_no_theme_block(new_context, server):
    served = {}
    for route in SHEET_ROUTES:
        context, page = _open(new_context, server, route)
        try:
            for sheet in page.evaluate(_STYLESHEETS):
                served[sheet["href"].split("?")[0]] = sheet
        finally:
            context.close()
    sheets = list(served.values())
    assert len(sheets) == 9, sorted(served)
    for token in NEW_TOKENS:
        declared = []
        for sheet in sheets:
            css = _strip_comments(sheet["text"])
            for match in re.finditer(re.escape(token) + r"\s*:", css):
                declared.append((sheet["href"].split("?")[0].rsplit("/", 1)[-1],
                                 _enclosing_selector(css, match.start())))
        assert declared == [("style.css", ":root")], (token, declared)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_new_tokens_resolve_to_their_pixel_value(new_context, server, theme):
    context, page = _open(new_context, server, "/", theme=theme)
    try:
        asked = ([[token, "space"] for token in NEW_SPACING_TOKENS]
                 + [[token, "radius"] for token in NEW_RADIUS_TOKENS])
        assert page.evaluate(_RESOLVE_TOKENS, asked) == NEW_TOKENS
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", LANGS)
def test_sampled_elements_keep_their_padding_margin_gap_and_radius(
        new_context, server, lang, theme):
    for route in sorted({sample[0] for sample in SAMPLES}):
        context, page = _open(new_context, server, route, lang=lang, theme=theme)
        try:
            asked = [{"selector": selector, "expected": expected}
                     for sample_route, selector, expected, _interactive in SAMPLES
                     if sample_route == route]
            found = page.evaluate(_MEASURE, {"samples": asked})
        finally:
            context.close()
        assert found["reduced"] is True, "reduced motion was not emulated"
        assert found["scrollWidth"] <= found["clientWidth"], (route, found)
        wanted = {selector: (expected, interactive)
                  for sample_route, selector, expected, interactive in SAMPLES
                  if sample_route == route}
        for sample in found["samples"]:
            expected, interactive = wanted[sample["selector"]]
            where = (route, sample["selector"], lang, theme)
            assert sample["found"], where
            assert sample["values"] == expected, where
            if interactive:
                assert sample["shown"], where
                assert sample["height"] >= MIN_TARGET_PX - 0.5, (where, sample["height"])


# One sample per page whose text and background the contrast floor is measured on (no colour
# changes here, so the pair is the one the page already had).
TEXT_SAMPLES = (".home-pill", ".filter-bar__search input", ".rarity-pill", ".refresh-pill",
                ".row-menu__item", ".special-add__summary", "a.calendar-manage")


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_the_text_of_one_sample_per_page_keeps_the_contrast_floor(new_context, server, theme):
    checked = 0
    for route in sorted({sample[0] for sample in SAMPLES}):
        context, page = _open(new_context, server, route, theme=theme)
        try:
            asked = [{"selector": selector, "expected": {}}
                     for sample_route, selector, _expected, _interactive in SAMPLES
                     if sample_route == route and selector in TEXT_SAMPLES]
            if not asked:
                continue
            found = page.evaluate(_MEASURE, {"samples": asked})
        finally:
            context.close()
        for sample in found["samples"]:
            assert sample["found"], (route, sample)
            ratio = skypane_contrast_check.contrast_ratio(sample["text"], sample["ground"])
            assert ratio >= CONTRAST_FLOOR, (route, theme, sample, round(ratio, 2))
            checked += 1
    assert checked >= 4


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_radii_no_seeded_page_draws_keep_their_pixel_value(new_context, server, theme):
    found = []
    for route in sorted({probe[0] for probe in RADIUS_PROBES}):
        context, page = _open(new_context, server, route, theme=theme)
        try:
            asked = [{"parent": parent, "child": child}
                     for probe_route, parent, child, _radius in RADIUS_PROBES
                     if probe_route == route]
            found += [(route, item["parent"], item["child"], item["radius"])
                      for item in page.evaluate(_RADIUS_PROBE, asked)]
        finally:
            context.close()
    assert sorted(found, key=str) == sorted(RADIUS_PROBES, key=str)
