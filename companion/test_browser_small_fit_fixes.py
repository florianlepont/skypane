"""Real-browser checks of small fit and target-size defects: a search hint that is not cut,
44px targets on suggestion chips and stand-alone links, a tab bar whose cells line up, focus
that is never left under the floating tab bar, and cards that keep to the page column."""
import pytest

import companion.test_view_pages_helpers as vp
import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE, _assert_no_page_overflow,
    seed_state_dir)

pytestmark = pytest.mark.browser

PHONES = (
    pytest.param(VIEWPORT_MIN_SUPPORTED, id="360"),
    pytest.param(VIEWPORT_PHONE, id="390"))
LANGS = ("en", "fr")

_READY = (
    "() => document.readyState === 'complete' && document.getAnimations().every("
    "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)")


def _seed(state_dir):
    seed_state_dir(state_dir)
    fx.seed_fleet(state_dir)
    vp.seed_runway_events(state_dir, [
        {"ts": ts, "hex": "4c%04x" % index, "callsign": callsign, "airline": airline,
         "origin": origin, "destination": destination, "confirmed_state": state,
         "aircraft_type": "Boeing 737-8K2 (WL)"}
        for index, (callsign, airline, origin, destination, state, ts)
        in enumerate(vp.FLIGHT_CARD_FLIGHTS)])


@pytest.fixture(scope="module")
def rig(module_app_server_factory):
    return module_app_server_factory(seed=_seed, fake_providers=True)


def _admin(new_context, rig, viewport, path, lang="en", **options):
    name, value = fx.admin_cookie(rig.state_dir).split("=", 1)
    base = rig.base_url()
    context = new_context(viewport=viewport, reduced_motion="reduce", **options)
    context.add_cookies([
        {"name": name, "value": value, "url": base, "httpOnly": True, "sameSite": "Strict"},
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base}])
    page = context.new_page()
    page.goto(base + path)
    page.locator("main").wait_for(state="visible")
    page.wait_for_function(_READY, timeout=15000)
    return context, page


# The room a placeholder needs, in the field's own font, against the room the field gives.
_PLACEHOLDER = """(selector) => {
  const field = document.querySelector(selector);
  const style = getComputedStyle(field);
  const ctx = document.createElement('canvas').getContext('2d');
  ctx.font = style.fontWeight + ' ' + style.fontSize + ' ' + style.fontFamily;
  return {text: field.placeholder, needs: ctx.measureText(field.placeholder).width,
          room: field.clientWidth - parseFloat(style.paddingLeft)
            - parseFloat(style.paddingRight)};
}"""


@pytest.mark.parametrize("lang", LANGS)
def test_the_flights_search_hint_is_never_cut(new_context, rig, lang):
    """On a desktop the search field sits in the title row with its hint showing (a phone
    folds it into a button until it is used)."""
    context, page = _admin(new_context, rig, VIEWPORT_DESKTOP, "/flights", lang)
    try:
        hint = page.evaluate(_PLACEHOLDER, "#history_filter_input")
        assert hint["text"] and hint["needs"] <= hint["room"] + 0.5, hint
    finally:
        context.close()


# Whether a point 20px above and below an element's centre still reaches it: a 44px target.
_TARGET = """(selector) => [...document.querySelectorAll(selector)]
  .filter((el) => el.getClientRects().length).map((el) => {
    el.scrollIntoView({block: 'center'});
    const box = el.getBoundingClientRect();
    const x = box.left + box.width / 2, y = box.top + box.height / 2;
    const reaches = (dy) => { const hit = document.elementFromPoint(x, y + dy);
      return hit === el || el.contains(hit); };
    return {text: el.textContent.trim().slice(0, 40), height: box.height,
            reaches: reaches(-20) && reaches(20)};
  })"""


@pytest.mark.parametrize("viewport", PHONES + (pytest.param(VIEWPORT_DESKTOP, id="1280"),))
def test_stand_alone_links_are_44px_targets(new_context, rig, viewport):
    """The way back on Credits and the footer link of the System view answer 20px above and
    below their text."""
    for path, selector in (("/credits", "main p > a"), ("/fleet?view=system", "main a.text-link")):
        context, page = _admin(new_context, rig, viewport, path)
        try:
            # A link inside a folded row is measured with the row open.
            page.evaluate(
                "() => document.querySelectorAll('main details').forEach((d) => { d.open = true; })")
            targets = page.evaluate(_TARGET, selector)
            assert targets, (path, selector)
            assert all(t["reaches"] for t in targets), (path, targets)
        finally:
            context.close()


_CELLS = """() => [...document.querySelectorAll('.tab-bar > a, .tab-bar > details > summary')]
  .filter((el) => el.getClientRects().length).map((el) => {
    const icon = el.querySelector('svg').getBoundingClientRect();
    const label = el.querySelector('.tab-bar__label, span:not(.dot)');
    const box = el.getBoundingClientRect();
    const dot = el.querySelector('.dot');
    return {text: el.textContent.trim(), width: box.width, iconTop: Math.round(icon.top),
            cellBottom: box.bottom,
            dotBottom: dot ? dot.getBoundingClientRect().bottom : null,
            dotTop: dot ? dot.getBoundingClientRect().top : null,
            iconBottom: icon.bottom};
  })"""


@pytest.mark.parametrize("viewport", PHONES)
def test_the_fleet_cell_lines_up_with_its_neighbours(new_context, rig, viewport):
    """The warning dot of the Fleet cell does not push its icon up: every icon of the bar is
    at one height, and the dot sits by the icon, not under the label."""
    context, page = _admin(new_context, rig, viewport, "/fleet")
    try:
        cells = page.evaluate(_CELLS)
        assert len(cells) >= 4, cells
        assert len({c["iconTop"] for c in cells}) == 1, cells
        dotted = [c for c in cells if c["dotBottom"] is not None]
        assert dotted, cells
        for cell in dotted:
            assert cell["dotTop"] < cell["iconBottom"], cell
    finally:
        context.close()


@pytest.mark.parametrize("viewport", PHONES)
def test_a_focused_control_is_scrolled_clear_of_the_tab_bar(new_context, rig, viewport):
    """Tabbing down a long page never leaves the focused control under the floating bar."""
    context, page = _admin(new_context, rig, viewport, "/users")
    try:
        bar_top = page.evaluate(
            "() => document.querySelector('.tab-bar').getBoundingClientRect().top")
        covered = []
        for _stop in range(40):
            page.keyboard.press("Tab")
            box = page.evaluate(
                "() => { const el = document.activeElement;"
                " if (!el || el === document.body || el.closest('.tab-bar')) return null;"
                " const r = el.getBoundingClientRect();"
                " return {name: el.tagName + '.' + el.className, top: r.top, bottom: r.bottom}; }")
            if box and box["bottom"] > bar_top + 0.5 and box["top"] < viewport["height"]:
                covered.append(box)
        assert not covered, (bar_top, covered)
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_a_quiet_hours_preset_keeps_its_padding_on_a_narrow_phone(new_context, rig, lang):
    context, page = _admin(new_context, rig, VIEWPORT_MIN_SUPPORTED, "/", lang)
    try:
        page.locator("[data-modal-open*='quiet'], a[href*='quiet']").first.click()
        page.locator(".quiet-card").first.wait_for(state="visible")
        page.wait_for_function(_READY, timeout=10000)
        cards = page.evaluate(
            "() => [...document.querySelectorAll('.quiet-card')].map((card) => {"
            " const box = card.getBoundingClientRect(); const range = document.createRange();"
            " range.selectNodeContents(card.querySelector('.quiet-card__text'));"
            " return {text: card.textContent.trim(), room: box.right"
            " - range.getBoundingClientRect().right}; })")
        assert cards and all(card["room"] >= 12 for card in cards), cards
    finally:
        context.close()


def test_the_system_cards_fill_the_page_column(new_context, rig):
    context, page = _admin(new_context, rig, VIEWPORT_DESKTOP, "/fleet?view=system")
    try:
        edges = page.evaluate(
            "() => { const right = (s) => Math.round(document.querySelector(s)"
            ".getBoundingClientRect().right);"
            " return {header: right('main > .page-header'), topics: right('.system-topics'),"
            " card: right('.system-topics .group-block')}; }")
        assert edges["topics"] == edges["header"] == edges["card"], edges
        assert not _assert_no_page_overflow(page, "System", 1280)
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
def test_the_tab_bar_of_an_unknown_frame_keeps_cells_of_one_size(new_context, rig, lang):
    """The not-found page of a frame that does not exist shows two cells: the wide one must
    not swallow the bar."""
    context, page = _admin(new_context, rig, VIEWPORT_MIN_SUPPORTED, "/devices/d_nope/", lang)
    try:
        cells = page.evaluate(_CELLS)
        assert cells, "the page has a tab bar"
        widths = [c["width"] for c in cells]
        assert max(widths) <= 120, cells
    finally:
        context.close()


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("viewport", PHONES)
def test_no_audit_chip_is_stretched_across_the_row(new_context, rig, viewport, lang):
    """Chips that wrap onto a second row keep widths close to the first row's."""
    context, page = _admin(new_context, rig, viewport, "/audit", lang)
    try:
        chips = page.evaluate(
            "() => [...document.querySelectorAll('[data-tabs=\"audit\"] a.filter-chip')]"
            ".map((chip) => { const box = chip.getBoundingClientRect();"
            " const text = chip.querySelector('.filter-chip__text').getBoundingClientRect();"
            " return {text: chip.textContent.trim(), width: box.width, slack: box.width"
            " - text.width, height: box.height}; })")
        assert len(chips) >= 6, chips
        assert all(chip["height"] >= 44 for chip in chips), chips
        assert max(chip["slack"] for chip in chips) <= 80, chips
        assert not _assert_no_page_overflow(page, "Audit", viewport["width"])
    finally:
        context.close()


def test_an_airline_without_a_picture_shows_a_plane_not_an_empty_block(new_context, rig):
    context, page = _admin(new_context, rig, VIEWPORT_PHONE, "/airlines")
    try:
        blanks = page.evaluate(
            "() => [...document.querySelectorAll('.collection-card__blank')]"
            ".filter((el) => el.getClientRects().length).map((el) => {"
            " const icon = el.querySelector('svg');"
            " return icon ? icon.getBoundingClientRect().width : 0; })")
        assert blanks and all(width >= 20 for width in blanks), blanks
    finally:
        context.close()


@pytest.mark.parametrize("viewport", PHONES + (pytest.param(VIEWPORT_DESKTOP, id="1280"),))
def test_the_suggestion_chips_of_a_special_look_are_44px_targets(new_context, rig, viewport):
    context, page = _admin(new_context, rig, viewport, "/display/special-looks/new")
    try:
        heights = page.evaluate(
            "() => [...document.querySelectorAll('button.rule-suggestion-chip')]"
            ".filter((el) => el.getClientRects().length)"
            ".map((el) => el.getBoundingClientRect().height)")
        assert heights and min(heights) >= 44, heights
        assert not _assert_no_page_overflow(page, "New special look", viewport["width"])
    finally:
        context.close()
