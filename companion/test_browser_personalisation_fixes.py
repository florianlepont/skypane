"""Real-browser checks of the Personalisation fixes: the Calendar view shows its own content and its
look popover opens fully visible (not clipped by the list) on a desktop and a phone, with the
follows-departures state explained; the Departures and Arrivals pictures carry no caption; the
special look rows give their text the width (the kind badge never breaks inside a word, the two
actions stay reachable); without scripts no dead button is left; switching the kind of a new
special look clears the key typed for the old kind; choosing a background does not move the
controls.

State is always waited for (readiness, hit tests), never read right after an action."""
import pytest

from companion import auth, layout
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _login,
    _no_js_page,
    _set_ui_theme,
    seed_state_dir,
)
from server.plane import colour_rules

pytestmark = pytest.mark.browser

VIEWPORT_WIDE = {"width": 1440, "height": 900}
CALENDAR_ROW = "#calendar-row"
OPENER = CALENDAR_ROW + " summary[data-look-open], " + CALENDAR_ROW + " button.look-frame__open"
SHEET = "[data-look-sheet]"
LONG_RULES = (("prefix", "FGN"), ("prefix", "CTM"), ("callsign", "AFR1234"))

_READY = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "sel => { const el = document.querySelector(sel); if (!el) return false;"
    " const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    seed_state_dir(state_dir)
    for kind, key in LONG_RULES:
        colour_rules.add_rule(state_dir, kind, key, "white")


def _open(new_context, base_url, viewport, route, lang="en", theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    page.wait_for_function(_READY, timeout=15000)
    _set_ui_theme(page, theme)
    return context, page


def _inside(inner, outer, slack=1.0):
    return (inner["x"] >= outer["x"] - slack and inner["y"] >= outer["y"] - slack
            and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + slack
            and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + slack)


def _wait_sheet_visible(page):
    """The popover is open and every corner and the centre of it hit the sheet itself."""
    page.wait_for_function(
        """() => { const s = document.querySelector('[data-look-sheet]');
          if (!s || s.hidden) return false;
          const r = s.getBoundingClientRect();
          if (r.width < 200 || r.height < 150) return false;
          const pts = [[r.left + 8, r.top + 8], [r.right - 8, r.top + 8],
                       [r.left + r.width / 2, r.top + r.height / 2],
                       [r.left + 8, Math.min(r.bottom, innerHeight) - 8]];
          return pts.every(p => { const h = document.elementFromPoint(p[0], p[1]);
                                  return !!h && s.contains(h); }); }""", timeout=10000)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_DESKTOP, VIEWPORT_WIDE, VIEWPORT_PHONE], ids=["1280", "1440", "390"])
def test_the_calendar_view_shows_its_own_content_and_leads_to_its_look_page(
        new_context, make_app_server, viewport, lang, theme):
    """the Calendar view holds the connect row and the calendar look row inside the list card, no
    card of another view and no popover; the row's Change link is a 44px target that opens the
    calendar look page, whose picker sits in the page and, while the look follows departures,
    explains why its choices are off"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), viewport, layout.DISPLAY_CALENDAR_ROUTE, lang, theme)
    try:
        change = page.locator(CALENDAR_ROW + " a.special-row__edit")
        change.wait_for(state="visible")
        assert page.locator("#personalisation-calendar").count() == 1
        assert page.locator("#personalisation-look, .look-card, .look-picker").count() == 0
        assert page.locator(SHEET).count() == 0
        card = page.locator("#personalisation-calendar .special-list").bounding_box()
        for selector in (".calendar-status", CALENDAR_ROW):
            box = page.locator(selector).bounding_box()
            assert _inside(box, card), (selector, box, card)
        page.wait_for_function(_OWNS_CENTRE, arg=CALENDAR_ROW + " a.special-row__edit", timeout=10000)
        box = change.bounding_box()
        assert box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, box
        change.click()
        page.wait_for_url("**" + layout.DISPLAY_CALENDAR_LOOK_ROUTE)
        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
        note = page.locator("[data-look-same-note]")
        assert note.is_visible() and note.inner_text().strip()
        page.locator("[data-look-same]").click()
        page.wait_for_function(
            "() => document.querySelector('[data-look-same-note]').hidden", timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("route", [layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_DESKTOP], ids=["360", "1280"])
def test_the_picture_has_no_caption_under_it(new_context, make_app_server, viewport, lang, route):
    """nothing but the picture sits in the stage: no read-back text under or beside it"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, route, lang)
    try:
        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
        assert page.locator(".look-frame__caption").count() == 0
        assert page.locator(".look-stage").inner_text().strip() == ""
        picture = page.locator(".look-panel:not([hidden]) .look-frame__picture").bounding_box()
        assert picture["width"] >= 150
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_choosing_a_background_does_not_move_the_controls(new_context, make_app_server, lang):
    """the stripe row stays in place whatever background is chosen: the colour and background
    rows keep their height and every row keeps its top"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP, layout.DISPLAY_ROUTE, lang)
    try:
        page.locator(SHEET + "[data-look-inline]").wait_for(state="visible")
        # The last row's own reason may come and go below everything else: only the rows
        # above it (and the tops of all rows) must hold still.
        measure = """() => [...document.querySelectorAll('[data-look-sheet] .look-axis')].map(
            (a, i, all) => { const r = a.getBoundingClientRect();
              return [Math.round(r.top), i < all.length - 1 ? Math.round(r.height) : 0]; })"""
        before = page.evaluate(measure)
        assert len(before) == 3
        for background in ("full", "soft", "paper"):
            page.click(
                '%s .look-seg__option:has(input[data-look-axis="background"][value="%s"])' % (
                    SHEET, background))
            page.wait_for_function(
                "b => document.querySelector('input[data-look-axis=\"background\"][value=\"' + b + '\"]').checked",
                arg=background, timeout=10000)
            assert page.evaluate(measure) == before, background
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("viewport", [VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE], ids=["360", "390"])
def test_a_special_look_row_gives_its_text_the_width(
        new_context, make_app_server, viewport, theme, lang):
    """on a phone the row's text column is at least 120px wide, the kind badge sits on one line
    and no word breaks inside itself, the picture is on the left and the Edit and Remove actions
    are 44px targets inside the row that own their centre"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), viewport, layout.DISPLAY_SPECIAL_LOOKS_ROUTE, lang, theme)
    try:
        page.locator(".rule-row").first.wait_for(state="visible")
        rows = page.locator(".rule-row")
        assert rows.count() >= 3
        for index in range(rows.count()):
            row = rows.nth(index)
            row.scroll_into_view_if_needed()
            text = row.locator(".special-row__text").bounding_box()
            mini = row.locator(".special-row__mini").bounding_box()
            box = row.bounding_box()
            assert text["width"] >= 120, (index, text)
            assert mini["x"] < text["x"] and _inside(text, box) and _inside(mini, box)
            tag = row.locator(".special-row__tag").bounding_box()
            assert tag["height"] <= 32, ("badge wraps", index, tag)
            broken = row.locator(".special-row__text").evaluate("""el => {
              const out = [];
              const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
              while (walker.nextNode()) {
                const node = walker.currentNode; const re = /\\S+/g; let m;
                while ((m = re.exec(node.data))) {
                  const range = document.createRange();
                  range.setStart(node, m.index); range.setEnd(node, m.index + m[0].length);
                  const lines = new Set([...range.getClientRects()].map(r => Math.round(r.top)));
                  if (lines.size > 1) out.push(m[0]);
                }
              }
              return out; }""")
            assert broken == [], ("word broken across lines", index, broken)
            for action in ("a.special-row__edit", "a.special-row__remove"):
                button = row.locator(action).bounding_box()
                assert button["height"] >= 44 - 0.5 and button["width"] >= 44, (action, button)
                assert _inside(button, box), (action, button, box)
                assert button["y"] >= text["y"] + text["height"] - 1, "actions are under the text"
        page.locator(".rule-row a.special-row__edit").first.scroll_into_view_if_needed()
        page.wait_for_function(
            _OWNS_CENTRE, arg=".rule-row a.special-row__edit", timeout=10000)
        page.locator(".rule-row a.special-row__remove").first.scroll_into_view_if_needed()
        page.wait_for_function(
            _OWNS_CENTRE, arg=".rule-row a.special-row__remove", timeout=10000)
    finally:
        context.close()


def test_the_long_airline_names_show_in_full_on_a_phone(new_context, make_app_server):
    """'Gendarmerie Nationale' and 'French Air Force' read as whole words in the row"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, layout.DISPLAY_SPECIAL_LOOKS_ROUTE)
    try:
        page.locator(".rule-row").first.wait_for(state="visible")
        text = page.locator("#personalisation-special-looks").inner_text()
        assert "Gendarmerie Nationale" in text and "French Air Force" in text
    finally:
        context.close()


@pytest.mark.parametrize("route", [layout.DISPLAY_ROUTE, layout.DISPLAY_ARRIVALS_ROUTE])
def test_without_scripts_no_dead_button_is_left_on_the_look_view(new_context, make_app_server, route):
    """with scripts blocked every button the page shows is a real control: the script-only
    openers stay hidden and the native look cards are the way in"""
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), route, viewport=VIEWPORT_PHONE,
                     reduced_motion="reduce") as page:
        page.wait_for_load_state("load")
        page.locator("input[name='theme']").first.wait_for(state="attached")
        openers = page.locator("button[data-look-open]")
        for index in range(openers.count()):
            assert not openers.nth(index).is_visible(), index
        assert page.get_by_role("button", name="Customise look").count() == 0


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_switching_the_kind_of_a_new_special_look_clears_the_key(new_context, make_app_server, lang):
    """a key typed for an airline does not stay in the Value field once the kind becomes Flight"""
    server = make_app_server(seed=_seed)
    context, page = _open(
        new_context, server.base_url(), VIEWPORT_PHONE, layout.DISPLAY_SPECIAL_LOOK_NEW_ROUTE, lang)
    try:
        page.locator(".form-page__card").wait_for(state="visible")
        page.click("label[for='rule-kind-prefix']")
        page.wait_for_function("() => document.getElementById('rule-kind-prefix').checked", timeout=10000)
        page.fill("#rule-key", "AFR")
        assert page.input_value("#rule-key") == "AFR"
        page.click("label[for='rule-kind-callsign']")
        page.wait_for_function("() => document.getElementById('rule-kind-callsign').checked", timeout=10000)
        page.wait_for_function("() => document.getElementById('rule-key').value === ''", timeout=10000)
    finally:
        context.close()
