"""Real-browser geometry and contrast checks of the admin Components page, at 360 and 1280 px,
light and dark, English and French: no overflow, labels centred in segmented controls and buttons,
selected against unselected contrast in every segmented control, 44px tap targets, a switch knob
inside its track with distinct on and off colours, and no overlap between siblings."""
import pytest

import fleet_console_support as fx
from companion import auth
from companion_app_server import session_cookie_for_state_dir

pytestmark = pytest.mark.browser

VIEWPORTS = {"360": {"width": 360, "height": 740}, "1280": {"width": 1280, "height": 900}}
SETTLED = """() => document.readyState === 'complete' && document.getAnimations().every(
  (a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)"""

# Page-side helpers: colours go through a 1x1 canvas so any CSS colour syntax (color-mix results
# included) becomes plain RGBA; a background is the stack of translucent layers up to the root.
HELPERS = """
(() => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = (css) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, under) => { const a = top[3]; return [0, 1, 2].map((i) =>
    top[i] * a + under[i] * (1 - a)).concat([1]); };
  const canvasColour = () => rgba(getComputedStyle(document.documentElement)
    .getPropertyValue('--color-canvas') || '#fff');
  const background = (el) => { const layers = []; for (let n = el; n; n = n.parentElement) {
      layers.push(rgba(getComputedStyle(n).backgroundColor)); }
    let out = [255, 255, 255, 1]; if (document.documentElement.dataset.uiTheme === 'dark'
      || matchMedia('(prefers-color-scheme: dark)').matches) { out = canvasColour(); }
    for (let i = layers.length - 1; i >= 0; i--) { out = over(layers[i], out); } return out; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 :
      Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const textColour = (el, bg) => over(rgba(getComputedStyle(el).color), bg);
  const visible = (el) => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !el.closest('[hidden], dialog:not([open])')
      && !el.closest('.visually-hidden'); };
  const centreOffset = (el) => { const range = document.createRange(); range.selectNodeContents(el);
    const t = range.getBoundingClientRect(); const b = el.getBoundingClientRect();
    return [(t.left + t.right) / 2 - (b.left + b.right) / 2, (t.top + t.bottom) / 2 - (b.top + b.bottom) / 2]; };
  window.__c = {rgba, over, background, ratio, textColour, visible, centreOffset};
})();
"""

OVERFLOW = """() => {
  const c = window.__c; const bad = [];
  const doc = document.documentElement;
  if (doc.scrollWidth > doc.clientWidth) bad.push('page scrolls sideways: ' + doc.scrollWidth + ' > ' + doc.clientWidth);
  for (const state of document.querySelectorAll('.components-state')) {
    const box = state.getBoundingClientRect();
    for (const el of state.querySelectorAll('*')) {
      if (!c.visible(el) || el.closest('.data-table-wrap, details[open] > .row-menu__panel, .row-menu__panel')) continue;
      const r = el.getBoundingClientRect();
      if (r.right > box.right + 1 || r.left < box.left - 1) bad.push(el.className + ' ' + Math.round(r.left) + '-' + Math.round(r.right) + ' in ' + Math.round(box.left) + '-' + Math.round(box.right));
    }
  }
  return bad.slice(0, 8);
}"""

SEGMENTS = """() => {
  const c = window.__c; const out = [];
  const tracks = document.querySelectorAll('.components-state .theme-form, .components-state .personalisation-nav, .components-state .filter-bar__chips');
  for (const track of tracks) {
    if (!c.visible(track)) continue;
    const trackBg = c.background(track);
    const selected = track.querySelectorAll('.theme-option--active, input:checked + label, .personalisation-nav__link[aria-current] > span, .filter-chip input:checked + .filter-chip__box, .filter-chip--current .filter-chip__box');
    const idle = track.querySelectorAll('.theme-option:not(.theme-option--active), input:not(:checked) + label, .personalisation-nav__link:not([aria-current]) > span, .filter-chip input:not(:checked) + .filter-chip__box');
    const name = track.className.toString().split(' ')[0];
    if (!selected.length) { out.push([name, 'no selected segment']); continue; }
    for (const el of selected) {
      const bg = c.background(el);
      const labelEl = el.querySelector('.filter-chip__text') || el; const fg = c.textColour(labelEl, bg);
      out.push([name, 'selected', c.ratio(bg, trackBg), c.ratio(fg, bg), c.centreOffset(labelEl), el.getBoundingClientRect().height]);
    }
    for (const el of idle) {
      if (!c.visible(el)) continue;
      const fg = c.textColour(el.querySelector('.filter-chip__text') || el, trackBg);
      out.push([name, 'idle', 0, c.ratio(fg, trackBg), c.centreOffset(el.querySelector('.filter-chip__text') || el), el.getBoundingClientRect().height]);
    }
  }
  return out;
}"""

BUTTONS = """() => {
  const c = window.__c; const out = [];
  for (const el of document.querySelectorAll('.components-state .btn')) {
    if (!c.visible(el) || el.disabled) continue;
    const bg = c.background(el); const fg = c.textColour(el, bg); const r = el.getBoundingClientRect();
    out.push([el.className, r.height, r.width, c.ratio(fg, bg), c.centreOffset(el)]);
  }
  return out;
}"""

TARGETS = """() => {
  const c = window.__c; const bad = [];
  const sel = '.components-state .btn, .components-state .switch, .components-state .theme-option, '
    + '.components-state .theme-form input + label, .components-state .filter-chip, '
    + '.components-state .personalisation-nav__link, .components-state .settings-checkbox, '
    + '.components-state input[type=text], .components-state input[type=number], .components-state input[type=search], '
    + '.components-state summary, .components-state .toast__action, .components-index a';
  for (const el of document.querySelectorAll(sel)) {
    if (!c.visible(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.height < 43.5 || r.width < 43.5) bad.push(el.className + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  }
  return bad;
}"""

SWITCHES = """() => {
  const c = window.__c; const out = [];
  const colours = {};
  for (const sw of document.querySelectorAll('.components-state .switch')) {
    if (!c.visible(sw) || sw.disabled) continue;
    const track = sw.querySelector('.switch__track'); const thumb = sw.querySelector('.switch__thumb');
    const t = track.getBoundingClientRect(); const k = thumb.getBoundingClientRect();
    const state = sw.getAttribute('aria-checked');
    const bg = c.background(track); (colours[state] = colours[state] || []).push(bg);
    out.push({inside: k.left >= t.left - 0.5 && k.right <= t.right + 0.5 && k.top >= t.top - 0.5 && k.bottom <= t.bottom + 0.5,
      state, trackAgainstCard: c.ratio(bg, c.background(sw.parentElement)),
      thumbAgainstTrack: c.ratio(c.background(thumb), bg)});
  }
  const on = colours['true'][0], off = colours['false'][0];
  for (const box of document.querySelectorAll('.components-state .settings-checkbox input[type=checkbox]')) {
    const bg = c.background(box); out.push({form: true, checked: box.checked, bg});
  }
  return {rows: out, distinct: c.ratio(on, off), on, off};
}"""

OVERLAP = """() => {
  const c = window.__c; const bad = [];
  for (const host of document.querySelectorAll('.components-state__sample, .components-state__sample *')) {
    const kids = [...host.children].filter((k) => c.visible(k) && !['absolute', 'fixed'].includes(getComputedStyle(k).position)
      && !k.matches('input.visually-hidden, script, style, dialog'));
    for (let i = 0; i < kids.length; i++) for (let j = i + 1; j < kids.length; j++) {
      const a = kids[i].getBoundingClientRect(), b = kids[j].getBoundingClientRect();
      const w = Math.min(a.right, b.right) - Math.max(a.left, b.left), h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (w > 1.5 && h > 1.5) bad.push(host.className + ': ' + kids[i].className + ' / ' + kids[j].className + ' ' + Math.round(w) + 'x' + Math.round(h));
    }
  }
  return bad.slice(0, 8);
}"""


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_users)


def _open(new_context, server, width, theme, lang):
    context = new_context(viewport=VIEWPORTS[width], color_scheme=theme)
    name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + "/components")
    page.wait_for_function(SETTLED, timeout=10000)
    page.wait_for_function(
        "() => { const e = document.querySelector('.components-state .btn'); if (!e) return false;"
        " const r = e.getBoundingClientRect(); return document.elementFromPoint("
        "r.x + r.width / 2, r.y + r.height / 2) !== document.documentElement; }")
    page.evaluate(HELPERS)
    return context, page


PARAMS = [(w, t, lang) for w in ("360", "1280") for t in ("light", "dark") for lang in ("en", "fr")]


@pytest.fixture(params=PARAMS, ids=["%s-%s-%s" % p for p in PARAMS])
def components(request, new_context, server):
    context, page = _open(new_context, server, *request.param)
    yield page
    context.close()


def test_nothing_overflows_the_page_or_its_card(components):
    assert components.evaluate(OVERFLOW) == []


def test_segmented_controls_centre_their_labels_and_keep_selected_apart(components):
    rows = components.evaluate(SEGMENTS)
    assert len(rows) >= 12, rows
    for name, kind, against_track, text, (dx, dy), height in rows:
        assert kind != "no selected segment", name
        assert abs(dx) <= 1.0 and abs(dy) <= 1.0, (name, kind, dx, dy)
        assert text >= 4.5, (name, kind, "text contrast", text)
        assert height >= 28, (name, kind, height)
        if kind == "selected":
            assert against_track >= 3.0, (name, "selected pill against its track", against_track)


def test_buttons_are_centred_readable_targets(components):
    rows = components.evaluate(BUTTONS)
    assert len(rows) >= 8, rows
    for css, height, width, text, (dx, dy) in rows:
        assert height >= 43.5 and width >= 43.5, (css, height, width)
        assert text >= 4.5, (css, text)
        assert abs(dx) <= 1.0 and abs(dy) <= 1.0, (css, dx, dy)


def test_every_control_is_a_forty_four_pixel_target(components):
    assert components.evaluate(TARGETS) == []


def test_a_switch_knob_stays_inside_its_track_and_on_differs_from_off(components):
    result = components.evaluate(SWITCHES)
    rows = [row for row in result["rows"] if "inside" in row]
    assert len(rows) >= 4
    assert all(row["inside"] for row in rows), rows
    assert result["distinct"] >= 1.5, result
    for row in rows:
        assert row["thumbAgainstTrack"] >= 1.5, row
        if row["state"] == "false":
            assert row["trackAgainstCard"] >= 3.0, row
    form = {row["checked"]: row["bg"] for row in result["rows"] if row.get("form")}
    assert form[True] != form[False]


def test_sibling_elements_do_not_overlap(components):
    assert components.evaluate(OVERLAP) == []


def test_a_dialog_opens_inside_the_viewport_with_forty_four_pixel_actions(components):
    components.locator('a[data-modal-open][href="#components-dialog"]').click()
    components.wait_for_function(
        "() => { const d = document.getElementById('components-dialog'); return d && d.open; }")
    components.wait_for_function(SETTLED)
    box = components.evaluate(
        "() => { const d = document.getElementById('components-dialog').getBoundingClientRect();"
        " const w = document.documentElement.clientWidth; const h = window.innerHeight;"
        " const bad = [...document.querySelectorAll('#components-dialog button, #components-dialog a.modal__dismiss,"
        " #components-dialog input:not([type=hidden])')].filter((e) => { const r = e.getBoundingClientRect();"
        " return r.height < 43.5; }).map((e) => e.className);"
        " return {inside: d.left >= 0 && d.right <= w && d.top >= 0 && d.bottom <= h, bad}; }")
    assert box["inside"], box
    assert box["bad"] == [], box


# --- Pages that use the shared components (the audit's component-driven findings) -----------

@pytest.fixture(scope="module")
def fleet_server(module_app_server_factory):
    return module_app_server_factory(seed=fx.seed_fleet)


def _admin_page(new_context, server, path, lang="fr", width=390):
    context = new_context(viewport={"width": width, "height": 844})
    name, value = session_cookie_for_state_dir(server.state_dir, fx.ADMIN_EMAIL).split("=", 1)
    context.add_cookies([
        {"name": name, "value": value, "url": server.base_url(), "httpOnly": True,
         "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    page.goto(server.base_url() + path)
    page.wait_for_function(SETTLED, timeout=10000)
    return context, page


def test_the_rename_field_fills_its_card_and_the_page_has_a_visible_save(
        new_context, fleet_server):
    context, page = _admin_page(new_context, fleet_server, "/frame/name")
    try:
        geometry = page.evaluate(
            "() => { const i = document.querySelector('#frame-name').getBoundingClientRect();"
            " const c = document.querySelector('.page-section').getBoundingClientRect();"
            " const b = document.querySelector('.dirty-bar .btn--primary');"
            " return {gap: c.right - i.right, left: i.left - c.left, button: b ? b.getBoundingClientRect().height : 0}; }")
        assert abs(geometry["gap"] - geometry["left"]) <= 2, geometry
        assert geometry["button"] >= 43.5, geometry
    finally:
        context.close()


def test_the_wake_interval_field_is_wide_enough_for_its_placeholder(new_context, fleet_server):
    context, page = _admin_page(new_context, fleet_server, "/device")
    try:
        field = page.evaluate(
            "() => { const i = document.querySelector('#wake-interval-s');"
            " const c = document.createElement('canvas').getContext('2d');"
            " const s = getComputedStyle(i); c.font = s.fontSize + ' ' + s.fontFamily;"
            " const pad = parseFloat(s.paddingLeft) + parseFloat(s.paddingRight);"
            " return {width: i.getBoundingClientRect().width - pad, text: c.measureText(i.placeholder).width}; }")
        assert field["width"] >= field["text"], field
    finally:
        context.close()


def test_the_empty_flights_search_keeps_whole_history_chips_and_a_standard_clear(
        new_context, module_app_server_factory):
    import companion.test_view_pages_helpers as vp
    server = module_app_server_factory(seed=vp.seed_flight_card_variety, fake_providers=True)
    context, page = _admin_page(new_context, server, "/flights?q=zzzzqq", lang="en")
    try:
        result = page.evaluate(
            "() => ({counts: [...document.querySelectorAll('.filter-chip__count')].map(e => e.textContent),"
            " clear: document.querySelector('[data-flights-empty] .btn--secondary').getBoundingClientRect().height})")
        assert result["counts"][0] != "0", result
        assert result["clear"] >= 43.5, result
    finally:
        context.close()
