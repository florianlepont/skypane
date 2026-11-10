"""Real-browser checks of the one glass tier and the grouped-list components: rows are at
least 44px (54px) tall with a visible focus ring, long values truncate with an ellipsis, the
value text reads over the glass in both themes, the audited surfaces carry the glass token
instead of the legacy beige fill, Home is a hero plus two or three groups that lay out at 360,
390 and 1440px in English and French, and the Console Fleet State rows never overlap."""
from datetime import datetime, timedelta, timezone

import pytest

import companion.test_view_pages_helpers as vp
from companion import auth
from companion.test_browser_ux_helpers import _assert_no_page_overflow, _login, _set_ui_theme
from provisioned_fleet import device_dir, mark_checked_in, provision_fleet
from server import device_config, history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", {"width": 360, "height": 800}), ("390", {"width": 390, "height": 844}),
             ("1440", {"width": 1440, "height": 900}))
THEMES = ("light", "dark")
FINITE_ANIMATIONS_DONE = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => (a.effect && a.effect.getComputedTiming().iterations === Infinity)"
    " || a.playState !== 'running')")


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    def seed(state_dir):
        vp.seed_home_tile_variety(state_dir)
        # The look-seg audit needs the classic look picker, not the giant layouts' pairing picker.
        device_config.save_device_config(state_dir, layout="classic")

    return module_app_server_factory(seed=seed, fake_providers=True)


def _open(new_context, server, path, viewport, lang, scheme):
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    for host in ("https://tile.openstreetmap.org/**", "https://nominatim.openstreetmap.org/**"):
        context.route(host, lambda route: route.fulfill(status=204, body=""))
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(FINITE_ANIMATIONS_DONE, timeout=10000)
    _set_ui_theme(page, scheme)
    return context, page


_ROWS = """() => [...document.querySelectorAll('.group > .row')].filter(r => r.checkVisibility())
  .map(r => { const b = r.getBoundingClientRect(); const m = r.querySelector('.row__main');
    const mb = m.getBoundingClientRect();
    return {h: b.height, mh: mb.height, label: r.textContent.trim().slice(0, 30)}; })"""


def _home(new_context, server, viewport, lang, scheme):
    return _open(new_context, server, "/", viewport, lang, scheme)


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("vp_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_home_is_a_hero_over_a_few_groups_and_fits(new_context, server, vp_name, viewport, lang, scheme):
    context, page = _home(new_context, server, viewport, lang, scheme)
    try:
        where = "home/%s/%s/%s" % (vp_name, lang, scheme)
        assert not _assert_no_page_overflow(page, where, viewport["width"])
        geometry = page.evaluate(
            """() => {
                const hero = document.querySelector('.hero').getBoundingClientRect();
                const groups = [...document.querySelectorAll('main .group')]
                    .map(g => g.getBoundingClientRect());
                const status = getComputedStyle(document.querySelector('.hero h1'));
                return {hero: [hero.top, hero.bottom], groups: groups.map(g => [g.top, g.bottom]),
                        nested: document.querySelectorAll('.group .group').length,
                        size: parseFloat(status.fontSize), weight: status.fontWeight,
                        cards: document.querySelectorAll('main .page-section').length};
            }""")
        assert 2 <= len(geometry["groups"]) <= 3, geometry
        assert geometry["nested"] == 0 and geometry["cards"] == 0, geometry
        assert all(g[0] >= geometry["hero"][1] - 1 for g in geometry["groups"]), geometry
        # The hero's title is the frame name: 24px under 380px, 28px on a phone, 48px beyond.
        assert 24 <= geometry["size"] <= 48 and geometry["weight"] == "700", geometry
        for row in page.evaluate(_ROWS):
            assert row["h"] >= 54 - 0.5 and row["mh"] >= 44, (where, row)
    finally:
        context.close()


def test_a_row_shows_a_focus_ring_and_a_long_value_truncates(new_context, server):
    context, page = _home(new_context, server, VIEWPORTS[0][1], "en", "light")
    try:
        link = page.locator(".group a.row__main").first
        link.focus()
        page.keyboard.press("Tab")
        page.keyboard.press("Shift+Tab")
        page.wait_for_function(
            "() => document.activeElement && document.activeElement.matches('.row__main')"
            " && getComputedStyle(document.activeElement).outlineStyle !== 'none'"
            " && parseFloat(getComputedStyle(document.activeElement).outlineWidth) >= 2")
        value = page.evaluate(
            """() => { const v = document.createElement('span'); v.className = 'row__value';
              v.textContent = 'x'.repeat(200); document.querySelector('.group .row__main')
                  .appendChild(v); const s = getComputedStyle(v); const r = v.getBoundingClientRect();
              return {ellipsis: s.textOverflow, nowrap: s.whiteSpace, w: r.width,
                      vw: innerWidth, sw: document.documentElement.scrollWidth}; }""")
        assert value["ellipsis"] == "ellipsis" and value["nowrap"] == "nowrap", value
        assert value["w"] <= value["vw"] * 0.5 + 1 and value["sw"] <= value["vw"], value
    finally:
        context.close()


_VALUE_CONTRAST = """() => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = css => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data; return [d[0], d[1], d[2], d[3] / 255]; };
  const lum = c => { const [r, g, b] = c.map(v => { v /= 255;
    return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const root = getComputedStyle(document.documentElement);
  const hex = n => root.getPropertyValue(n).trim().match(/[0-9a-f]{2}/gi).map(h => parseInt(h, 16));
  const glass = rgba(root.getPropertyValue('--glass-bg').trim());
  const out = [];
  for (const stop of ['--sky-top', '--sky-mid', '--sky-bottom']) {
    const sky = hex(stop);
    const bg = [0, 1, 2].map(i => glass[3] * glass[i] + (1 - glass[3]) * sky[i]);
    for (const v of document.querySelectorAll('.group .row__value, .group .row__detail')) {
      const ink = rgba(getComputedStyle(v).color);
      const over = [0, 1, 2].map(i => ink[3] * ink[i] + (1 - ink[3]) * bg[i]);
      const [hi, lo] = [lum(over), lum(bg)].sort((x, y) => y - x);
      out.push((hi + 0.05) / (lo + 0.05));
    }
  }
  return out; }"""


@pytest.mark.parametrize("scheme", THEMES)
def test_row_value_text_reads_over_the_glass(new_context, server, scheme):
    context, page = _home(new_context, server, VIEWPORTS[1][1], "en", scheme)
    try:
        page.wait_for_function(FINITE_ANIMATIONS_DONE)
        ratios = page.evaluate(_VALUE_CONTRAST)
        assert ratios, "no row value or detail on Home"
        assert min(ratios) >= 4.5, (scheme, min(ratios))
    finally:
        context.close()


_SURFACES = """(glass) => { const bad = [];
  for (const sel of ['.space-switch', '.filter-bar__chips', '.personalisation-nav',
      '.look-seg', '.place-modes', '.tab-bar__more-panel', '.users-table',
      '.dashboard-main > .data-table-wrap']) {
    for (const el of document.querySelectorAll(sel)) {
      if (!el.checkVisibility()) continue;
      const bg = getComputedStyle(el).backgroundColor;
      if (bg !== glass) bad.push(sel + ' ' + bg);
    } } return bad; }"""
# The Location card over the map is deliberately not on this list: it is opaque so its text stays
# legible over the map (checked in test_browser_round8_fixes.py).
_PAGES = (("/display", "look-seg"), ("/flights", "filter-bar__chips"),
          ("/detection", "place-modes"), ("/users", "users-table"))


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("path,present", _PAGES, ids=[p[0].strip("/") for p in _PAGES])
def test_audited_surfaces_use_the_glass_token_not_the_beige_fill(
        new_context, server, path, present, scheme):
    context, page = _open(new_context, server, path, VIEWPORTS[2][1], "en", scheme)
    try:
        glass = page.evaluate(
            """() => { const p = document.createElement('div');
              p.style.background = 'var(--glass-bg)'; document.body.appendChild(p);
              const c = getComputedStyle(p).backgroundColor; p.remove(); return c; }""")
        assert glass.startswith("rgba(") or glass.startswith("color("), glass
        assert page.evaluate(_SURFACES, glass) == []
        assert page.locator("." + present).count() >= 1, "the audited %s is not on %s" % (present, path)
        assert page.evaluate(
            "() => [...document.querySelectorAll('main *')].filter(e => e.checkVisibility()"
            " && getComputedStyle(e).textTransform === 'uppercase').length") == 0
    finally:
        context.close()


_STATE_ROWS = """() => [...document.querySelectorAll('.fleet-block .health-row__summary')]
  .filter(s => s.checkVisibility()).map(s => {
    const r = sel => s.querySelector(sel).getBoundingClientRect();
    const name = r('.health-row__name'), verdict = r('.health-row__verdict'),
          value = r('.health-row__value');
    const hit = (a, b) => a.left < b.right - 0.5 && b.left < a.right - 0.5
        && a.top < b.bottom - 0.5 && b.top < a.bottom - 0.5;
    return {overlap: hit(name, value) || hit(verdict, value) || hit(name, verdict),
            verdictW: verdict.width, rowW: s.getBoundingClientRect().width,
            valueW: value.width, beside: value.left >= verdict.right - 0.5}; })"""


@pytest.fixture(scope="module")
def fleet_server(module_app_server_factory):
    def seed(state_dir):
        fleet = provision_fleet(state_dir)
        mark_checked_in(state_dir, fleet.a1)
        stale = (datetime.now(timezone.utc) - timedelta(days=97)).isoformat()
        with history_db.open_db(device_dir(state_dir, fleet.a1)) as conn:
            history_db.record_device_health(
                conn, stale, battery_mv=4197, fw_version="1.0.0", boot_reason="wake", rssi="-60")
        seed.fleet = fleet
    server = module_app_server_factory(seed=seed, fake_providers=True)
    server.frame_id = seed.fleet.a1
    return server


@pytest.mark.parametrize("scheme", THEMES)
@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("width", (360, 1000, 1280, 1440))
def test_fleet_state_rows_never_overlap(new_context, fleet_server, width, lang, scheme):
    context, page = _open(
        new_context, fleet_server, "/fleet?frame=%s" % fleet_server.frame_id,
        {"width": width, "height": 900}, lang, scheme)
    try:
        page.locator(".fleet-block .health-row__summary").first.wait_for(state="visible")
        rows = page.evaluate(_STATE_ROWS)
        assert rows, "the State block shows no health row"
        for row in rows:
            assert not row["overlap"], (width, lang, row)
            assert row["verdictW"] >= 100, (width, lang, row)
            if row["beside"]:
                assert row["valueW"] <= row["rowW"] * 0.5 + 1, (width, lang, row)
        assert not _assert_no_page_overflow(page, "fleet/%d" % width, width)
    finally:
        context.close()
