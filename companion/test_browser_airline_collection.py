"""Real-browser checks of the Airlines collection (/airlines): at 360 and 1280 px, in English and
French, in both themes, nothing overflows sideways, every card, chip, select, field and button is at
least 44 px high and owns its centre, the progress sits on one line (count, bar, next goal, a compact
earned/total badge pill), the page title has the size of the other pages' titles, the control bar
sticks while the cards scroll, and a card not seen yet is only dimmed. A card opens its read-only
sheet with the focus inside, Escape closes it and returns the focus to the card. With scripts
blocked the chips, sort and field work through the Apply button and a card opens its sheet through
the hash link.

State is always waited for (settled page, owned centres, focus), never read right after an input."""
import re
import time
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _no_js_page,
    _set_ui_theme,
    seed_state_dir,
)
from server import history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
CARD = "a.collection-card"
SEEN_CARD = CARD + ":not(.collection-card--unseen)"
UNSEEN_CARD = CARD + ".collection-card--unseen"
TOTAL_SPOTTED = 3

_SETTLED = (
    "() => document.readyState === 'complete'"
    " && document.getAnimations().every(a => a.effect && a.effect.getTiming().iterations !== Infinity"
    " ? a.playState !== 'running' : true)")
_OWNS_CENTRE = (
    "el => { const r = el.getBoundingClientRect();"
    " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
    " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }")


def _seed(state_dir):
    """The shared fixture (36 Air France flights) plus Iberia three times and TAP Portugal once,
    the last a minute ago so it carries the New pill."""
    seed_state_dir(state_dir)
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        for index, days in enumerate((20, 10, 5)):
            history_db.record_runway_event(
                conn, ts=(now - timedelta(days=days)).isoformat(), hex="ib%04d" % index,
                callsign="IBE%03d" % index, aircraft_type="A320", confirmed_state="departing",
                airline="Iberia Airlines")
        history_db.record_runway_event(
            conn, ts=(now - timedelta(minutes=1)).isoformat(), hex="tp0001", callsign="TAP001",
            aircraft_type="A21N", confirmed_state="arriving", airline="TAP Portugal")


def _wait_owns_centre(page, selector):
    page.locator(selector).first.evaluate("el => el.scrollIntoView({block: 'center'})")
    page.wait_for_function(
        "sel => { const el = document.querySelector(sel); const r = el.getBoundingClientRect();"
        " const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);"
        " return !!hit && (hit === el || el.contains(hit) || hit.contains(el)); }",
        arg=selector, timeout=10000)


def _wait_theme_painted(page):
    """Wait until the colour transition of a theme switch has ended: no running animation and
    the card's colours equal on two successive polls."""
    page.wait_for_function(
        "() => { const s = getComputedStyle(document.querySelector('a.collection-card'));"
        " const key = s.backgroundColor + '|' + s.color + '|' +"
        " getComputedStyle(document.documentElement).backgroundColor;"
        " const same = window.__paintKey === key; window.__paintKey = key;"
        " return same && document.getAnimations().length === 0; }", timeout=10000)


def _open(new_context, base_url, viewport, lang="en", theme="light", query=""):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + "/airlines" + query)
    page.wait_for_function(_SETTLED, timeout=15000)
    page.locator(SEEN_CARD).first.wait_for(state="visible")
    _set_ui_theme(page, theme)
    _wait_theme_painted(page)
    _wait_owns_centre(page, SEEN_CARD)
    return context, page


def _channels(css):
    """(r, g, b, alpha) of a computed colour in rgb() or color(srgb ...) form."""
    numbers = [float(n) for n in re.findall(r"[-\d.]+", css.split("/")[0])]
    alpha = float(css.split("/")[1].strip(" )")) if "/" in css else 1.0
    if css.startswith("rgba(") and len(numbers) == 4:
        alpha = numbers[3]
    if css.startswith("color(srgb"):
        numbers = [n * 255 for n in numbers[:3]]
    return numbers[0], numbers[1], numbers[2], alpha


def _luminance(rgb):
    def part(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * part(rgb[0]) + 0.7152 * part(rgb[1]) + 0.0722 * part(rgb[2])


def _contrast(foreground, background):
    red, green, blue, alpha = _channels(foreground)
    base = _channels(background)
    blended = tuple(alpha * c + (1 - alpha) * b for c, b in zip((red, green, blue), base[:3]))
    lighter, darker = sorted((_luminance(blended), _luminance(base[:3])), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_collection_does_not_overflow_and_its_targets_are_44px(
        new_context, make_app_server, label, viewport, theme, lang):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang, theme=theme)
    try:
        assert not _assert_no_page_overflow(page, "collection", viewport["width"])
        columns = page.eval_on_selector(
            ".collection-grid", "el => getComputedStyle(el).gridTemplateColumns.split(' ').length")
        assert columns == (2 if viewport["width"] < 700 else 3)
        for selector in (
                SEEN_CARD, UNSEEN_CARD, ".filter-chip", ".collection-sort > summary",
                "#collection-filter"):
            _wait_owns_centre(page, selector)
            box = page.locator(selector).first.bounding_box()
            assert box["height"] >= 44 - 0.5 and box["width"] >= 44 - 0.5, (selector, box)
            assert page.locator(selector).first.evaluate(_OWNS_CENTRE), selector
        assert not page.locator(".collection-controls__apply").is_visible()
        _assert_bar_is_one_unclipped_unit(page, viewport["width"])
        _wait_owns_centre(page, ".collection-legend > summary")
        legend_box = page.locator(".collection-legend > summary").bounding_box()
        assert legend_box["height"] >= 44 - 0.5 and legend_box["width"] >= 44 - 0.5
        # The badges are one compact pill, "earned/total", spelled out for assistive technology.
        pill = page.locator(".collection-badges")
        assert pill.count() == 1 and pill.locator("span[aria-hidden]").inner_text() == "1/5"
        assert pill.get_attribute("title")
        spelled = pill.locator(".visually-hidden").inner_text()
        assert "1/5" in spelled and ("Locked" if lang == "en" else "Verrouillé") in spelled
        assert 3 <= page.locator(".collection-progress__bar").bounding_box()["height"] <= 8
        _assert_segments_are_centred(page)
    finally:
        context.close()


def _assert_segments_are_centred(page):
    """Every segment's label and count sit centred in their segment (the owner dislikes
    off-centre labels)."""
    offsets = page.evaluate(
        "() => Array.from(document.querySelectorAll('.filter-chip__box')).map(box => {"
        " const r = box.getBoundingClientRect(); const range = document.createRange();"
        " range.selectNodeContents(box); const t = range.getBoundingClientRect();"
        " return {left: t.left - r.left, right: r.right - t.right,"
        " align: getComputedStyle(box).justifyContent}; })")
    assert offsets
    for offset in offsets:
        assert offset["align"] == "center" and abs(offset["left"] - offset["right"]) <= 2, offsets


def _assert_bar_is_one_unclipped_unit(page, width):
    """Every control of the bar sits inside the form and inside the viewport, the legend button
    ends the row, and on a wide screen the field, the segments and the sort share one row."""
    geometry = page.evaluate(
        "() => { const form = document.querySelector('.collection-controls').getBoundingClientRect();"
        " const box = sel => document.querySelector(sel).getBoundingClientRect();"
        " return {form: [form.left, form.right],"
        " parts: ['#collection-filter', '.collection-sort > summary', '.filter-bar__chips',"
        " '.collection-legend > summary']"
        ".map(sel => [box(sel).left, box(sel).right, box(sel).top]),"
        " visibleCount: !!document.querySelector('.collection-controls__count')}; }")
    for left, right, _top in geometry["parts"]:
        assert left >= geometry["form"][0] - 0.5 and right <= geometry["form"][1] + 0.5, geometry
        assert left >= -0.5 and right <= width + 0.5, geometry
    assert not geometry["visibleCount"], geometry
    if width >= 700:
        tops = [part[2] for part in geometry["parts"]]
        assert max(tops) - min(tops) < 24, geometry


def test_the_progress_line_sits_under_the_title_with_room_to_breathe(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        geometry = page.evaluate(
            "() => { const box = sel => document.querySelector(sel).getBoundingClientRect();"
            " return {title: box('.page-title'), line: box('.collection-progress__headline'),"
            " bar: box('.collection-progress__bar'), badges: box('.collection-badges'),"
            " text: document.querySelector('.collection-progress__headline').textContent,"
            " goal: document.querySelector('.collection-progress__goal').textContent,"
            " goal_box: box('.collection-progress__goal'),"
            " head: box('main .page-header')}; }")
        assert geometry["text"] == "%d of 36 airlines spotted" % TOTAL_SPOTTED
        assert geometry["goal"].endswith(" badge")
        # Count, bar, goal and badge pill share one line, in that order, under the title.
        line = [geometry[name] for name in ("line", "bar", "goal_box", "badges")]
        centres = [box["top"] + box["height"] / 2 for box in line]
        assert max(centres) - min(centres) < 4, geometry
        assert all(a["right"] <= b["left"] + 0.5 for a, b in zip(line, line[1:])), geometry
        assert geometry["line"]["top"] >= geometry["title"]["bottom"] + 8 - 0.5, geometry
        assert geometry["badges"]["top"] >= geometry["title"]["bottom"] + 8 - 0.5, geometry
        assert geometry["head"]["height"] < 140, geometry
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_phone_header_takes_no_more_than_a_third_of_the_screen(
        new_context, make_app_server, lang):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, lang=lang)
    try:
        geometry = page.evaluate(
            "() => { const box = sel => document.querySelector(sel).getBoundingClientRect();"
            " const head = box('main .page-header'); const bar = box('.collection-controls');"
            " const chips = document.querySelector('.filter-bar__chips');"
            " return {head: head.height, headBottom: head.bottom, bar: bar,"
            " title: box('.page-title'), badges: box('.collection-badges'),"
            " chipsScroll: chips.scrollWidth, chipsBox: chips.getBoundingClientRect().height,"
            " chips: Array.from(document.querySelectorAll('.filter-chip'))"
            ".map(c => c.getBoundingClientRect().top),"
            " line1: ['#collection-filter', '.collection-sort > summary', '.collection-legend > summary']"
            ".map(sel => box(sel)), track: box('.filter-bar__chips')}; }")
        assert geometry["head"] <= 740 / 3, geometry
        assert geometry["badges"]["top"] >= geometry["title"]["bottom"] - 0.5
        assert max(geometry["chips"]) - min(geometry["chips"]) < 2, geometry
        # The title is on the shared page-title scale (30px+): the French wording may wrap to a
        # second line, never to a third.
        assert geometry["title"]["height"] < 70, geometry
        assert geometry["chipsBox"] < 64, geometry
        # One compact bar of two lines: the field, the sort button and the legend button share
        # line one (the field takes the free width), the segments are line two.
        line1 = geometry["line1"]
        assert max(box["top"] for box in line1) - min(box["top"] for box in line1) < 1, geometry
        assert line1[0]["width"] > line1[1]["width"] + line1[2]["width"], geometry
        assert geometry["track"]["top"] >= max(box["bottom"] for box in line1) - 0.5, geometry
        # Two lines of 44px controls and their gap, inside the bar's own 8px padding and 1px border.
        assert geometry["bar"]["height"] <= 2 * 44 + 8 + 2 * 8 + 2 + 1, geometry
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_card_opens_its_read_only_sheet_and_escape_returns_to_the_card(
        new_context, make_app_server, label, viewport):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        card = page.locator(SEEN_CARD).first
        target = card.get_attribute("href").lstrip("#")
        card.click()
        page.wait_for_function(
            "id => { const d = document.getElementById(id);"
            " return d.open && d.contains(document.activeElement); }", arg=target, timeout=10000)
        sheet = page.locator("#" + target)
        assert sheet.locator("form, input, button, a[href*='/airlines/']").count() == 0
        assert "Times seen" in sheet.inner_text() and "Rarity" in sheet.inner_text()
        page.keyboard.press("Escape")
        page.wait_for_function(
            "([id, href]) => { const d = document.getElementById(id);"
            " return !d.open && document.activeElement"
            " && document.activeElement.getAttribute('href') === href; }",
            arg=[target, "#" + target], timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_a_dimmed_card_keeps_a_readable_name_and_carries_no_other_text(new_context, make_app_server, theme):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, theme=theme)
    try:
        probe = (
            "sel => { const card = document.querySelector(sel);"
            " const cs = el => getComputedStyle(el);"
            " const picture = card.querySelector('.collection-card__art');"
            " const seenLine = card.querySelector('.collection-card__seen');"
            " return {name: cs(card.querySelector('.collection-card__name')).color,"
            " seen: seenLine ? cs(seenLine).color : null,"
            " background: cs(card).backgroundColor, cardOpacity: cs(card).opacity,"
            " sky: cs(document.documentElement).getPropertyValue('--sky-mid').trim(),"
            " pictureOpacity: cs(picture).opacity, pictureFilter: cs(picture).filter}; }")
        seen = page.evaluate(probe, SEEN_CARD)
        unseen = page.evaluate(probe, UNSEEN_CARD)
        assert unseen["cardOpacity"] == "1" and seen["pictureOpacity"] == "1"
        assert unseen["pictureOpacity"] == "0.45" and "grayscale(1)" in unseen["pictureFilter"]
        assert seen["seen"] and unseen["seen"] is None
        # The card is translucent glass: its text sits on the card fill composited over the
        # sky behind it (measured on the middle stop).
        card_red, card_green, card_blue, card_alpha = _channels(unseen["background"])
        sky = unseen["sky"]
        surface = "rgb(%s)" % ", ".join(
            str(round(card_alpha * fg + (1 - card_alpha) * int(sky[i:i + 2], 16)))
            for fg, i in zip((card_red, card_green, card_blue), (1, 3, 5)))
        assert _contrast(unseen["name"], surface) >= 4.5, (theme, unseen, surface)
        # A card not seen yet is only dimmed: it carries its name and no other text.
        card = page.locator(UNSEEN_CARD).first
        assert card.inner_text().strip() == card.locator(".collection-card__name").inner_text()
    finally:
        context.close()


def _wait_settled(page, timeout=15.0):
    """Wait for _SETTLED by polling it from here. In a scripts-blocked page a
    wait_for_function armed right after a form navigation can stay unresolved
    for its whole timeout even though the predicate is already true (a fresh
    wait issued later resolves at once), so the predicate is evaluated in a loop
    with its own deadline instead."""
    deadline = time.monotonic() + timeout
    while not page.evaluate(_SETTLED):
        assert time.monotonic() < deadline, "the page did not settle"
        time.sleep(0.05)


def test_chips_sort_and_the_field_work_through_apply_without_script(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), "/airlines",
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        _wait_settled(page)
        assert page.locator(CARD).count() > TOTAL_SPOTTED
        apply_box = page.locator(".collection-controls__apply").bounding_box()
        assert apply_box["height"] >= 44 - 0.5 and apply_box["width"] >= 44 - 0.5
        assert apply_box["x"] + apply_box["width"] <= VIEWPORT_MIN_SUPPORTED["width"] + 0.5
        page.locator("label.filter-chip", has_text="Spotted").click()
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        _wait_settled(page)
        assert page.locator(CARD).count() == TOTAL_SPOTTED
        assert page.locator(UNSEEN_CARD).count() == 0
        page.locator(".collection-sort > summary").click()
        page.locator(".collection-sort__option", has_text="A to Z").click()
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        _wait_settled(page)
        names = page.locator(".collection-card__name").all_inner_texts()
        assert names == sorted(names, key=str.casefold)
        page.fill("#collection-filter", "iberia")
        with page.expect_navigation():
            page.locator(".collection-controls__apply").click()
        _wait_settled(page)
        assert page.locator(".collection-card__name").all_inner_texts() == ["Iberia Airlines"]
        assert "q=iberia" in page.url and "sort=az" in page.url and "show=spotted" in page.url


def test_the_sort_and_the_chips_apply_on_change_with_script(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED)
    try:
        summary = page.locator(".collection-sort > summary")
        assert "Most seen" in summary.get_attribute("aria-label")
        summary.click()
        panel = page.locator(".collection-sort__panel")
        panel.wait_for(state="visible")
        assert page.locator(".collection-sort__option").all_inner_texts() == [
            "Most seen", "Rarest", "Latest", "A to Z"]
        ticks = page.evaluate(
            "() => [...document.querySelectorAll('.collection-sort__row .icon')]"
            ".map(i => getComputedStyle(i).visibility)")
        assert ticks == ["visible", "hidden", "hidden", "hidden"], ticks
        page.locator(".collection-sort__option", has_text="A to Z").click()
        page.wait_for_url("**sort=az**", timeout=10000)
        page.wait_for_function(_SETTLED, timeout=15000)
        names = page.locator(".collection-card__name").all_inner_texts()
        assert names == sorted(names, key=str.casefold)
        assert page.locator('.collection-sort input[value="az"]').is_checked()
        page.locator("label.filter-chip", has_text="Spotted").click()
        page.wait_for_url("**show=spotted**", timeout=10000)
        page.wait_for_function(_SETTLED, timeout=15000)
        assert page.locator(CARD).count() == TOTAL_SPOTTED
        assert "sort=az" in page.url
        page.wait_for_function(
            "() => document.querySelector('[data-filter-count]').textContent.includes('3')",
            timeout=10000)
    finally:
        context.close()


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
def test_rare_and_occasional_airlines_and_aircraft_stand_out_by_colour_and_by_word(
        new_context, make_app_server, theme):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, theme=theme)
    try:
        probe = (
            "sel => { const el = document.querySelector(sel); const s = getComputedStyle(el);"
            " let bg = el.closest('.collection-card') || document.body;"
            " return {text: el.textContent.trim(), color: s.color,"
            " border: s.borderTopColor, bg: getComputedStyle(document.documentElement).backgroundColor}; }")
        rare = page.evaluate(probe, ".collection-card--rare .collection-card__rarity--rare")
        occasional = page.evaluate(
            probe, ".collection-card--occasional .collection-card__rarity--occasional")
        regular = page.evaluate(probe, ".collection-card--regular .collection-card__rarity")
        assert rare["text"] == "Rare" and occasional["text"] == "Occasional"
        assert len({rare["color"], occasional["color"], regular["color"]}) == 3
        for word in (rare, occasional):
            assert _contrast(word["color"], word["bg"]) >= 4.5, (theme, word)
        assert not page.locator(".rarity-legend").is_visible()
        page.locator(".collection-legend > summary").click()
        page.locator(".rarity-legend").wait_for(state="visible")
        legend = page.locator(".rarity-legend").inner_text()
        for word in ("Regular", "Occasional", "Rare", "10 or more sightings", "3 to 9 sightings",
                     "Fewer than 3 sightings"):
            assert word in legend
        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => !document.querySelector('.collection-legend').open", timeout=10000)
        page.locator(SEEN_CARD).first.click()
        page.wait_for_function(
            "() => !!document.querySelector('dialog[open] .type-chip')", timeout=10000)
        assert page.locator("dialog[open] .type-chip").count() >= 1
    finally:
        context.close()


def test_a_card_opens_its_sheet_through_the_hash_link_without_script(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), "/airlines",
                     viewport=VIEWPORT_MIN_SUPPORTED, reduced_motion="reduce") as page:
        page.wait_for_function(_SETTLED, timeout=15000)
        card = page.locator(SEEN_CARD).first
        target = card.get_attribute("href").lstrip("#")
        _wait_owns_centre(page, SEEN_CARD)
        card.click()
        page.wait_for_function(
            "id => { const d = document.getElementById(id);"
            " return d && getComputedStyle(d).display !== 'none'"
            " && d.getBoundingClientRect().height > 0; }", arg=target, timeout=10000)
        assert page.locator("#" + target + " a.modal__dismiss").is_visible()


def test_the_text_filter_hides_cards_instantly_with_script(new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        page.fill("#collection-filter", "tap por")
        page.wait_for_function(
            "() => Array.from(document.querySelectorAll('.collection-item'))"
            ".filter(li => !li.hidden).length === 1", timeout=10000)
        assert page.locator(".collection-item:not([hidden]) .collection-card__name").inner_text(
        ) == "TAP Portugal"
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_a_search_with_no_match_shows_the_empty_card_and_clear_brings_the_cards_back(
        new_context, make_app_server, label, viewport, lang):
    """Typing something no airline has leaves a card saying so (not a blank page) with a Clear
    button; Clear empties the field and shows the cards again, the sticky bar still stuck."""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang)
    try:
        card = page.locator("[data-filter-empty]")
        assert not card.is_visible()
        page.fill("#collection-filter", "zzzzq")
        card.wait_for(state="visible")
        assert card.locator(".empty-state__heading").inner_text() == (
            "No matching airlines" if lang == "en" else "Aucune compagnie correspondante")
        assert page.locator(".collection-item:not([hidden])").count() == 0
        clear = card.locator("[data-filter-clear]")
        assert clear.inner_text() == ("Clear" if lang == "en" else "Effacer")
        assert clear.bounding_box()["height"] >= 44 - 0.5
        assert not _assert_no_page_overflow(page, "airline empty", viewport["width"])
        page.wait_for_function(_SETTLED, timeout=15000)
        clear.click()
        page.wait_for_function(
            "() => document.querySelector('#collection-filter').value === ''"
            " && document.querySelector('[data-filter-empty]').hidden", timeout=10000)
        assert page.locator(".collection-item:not([hidden])").count() > 0
        assert page.locator(".collection-controls").evaluate(
            "el => getComputedStyle(el).position") == "sticky"
    finally:
        context.close()


def test_a_server_side_search_with_no_match_shows_the_empty_card_with_a_clear_link(
        new_context, make_app_server):
    """Opening the page with a search nothing matches (the no-script path) shows the same card,
    whose Clear is a plain link back to the whole collection."""
    server = make_app_server(seed=_seed)
    with _no_js_page(new_context, server.base_url(), "/airlines?q=zzzzq") as page:
        card = page.locator("[data-collection-empty]")
        card.wait_for(state="visible")
        assert page.locator(CARD).count() == 0
        card.locator("a").click()
        page.wait_for_url("**/airlines")
        assert page.locator(CARD).count() > 0


def test_the_collection_is_two_taps_from_home_on_a_phone_and_one_on_desktop(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator(".tab-bar__more > summary").click()
        link = page.locator(".tab-bar__more-panel a", has_text="Airlines")
        link.wait_for(state="visible")
        with page.expect_navigation():
            link.click()
        page.wait_for_url("**/airlines")
        assert page.locator(".collection-progress__headline").is_visible()
    finally:
        context.close()
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/")
        page.wait_for_function(_SETTLED, timeout=15000)
        with page.expect_navigation():
            page.locator("nav.sidebar-nav a", has_text="Airlines").click()
        page.wait_for_url("**/airlines")
        assert page.locator(".collection-progress__headline").is_visible()
    finally:
        context.close()


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_detail_sheet_fits_the_screen_with_its_head_and_close_in_reach(
        new_context, make_app_server, label, viewport, lang):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport, lang=lang)
    try:
        page.locator(SEEN_CARD).first.click()
        page.wait_for_function(
            "() => { const d = document.querySelector('dialog.collection-sheet[open]');"
            " return !!d && d.contains(document.activeElement) && d.getBoundingClientRect().height > 0"
            " && document.getAnimations().every(a => a.playState !== 'running'); }", timeout=10000)
        geometry = page.evaluate(
            "() => { const d = document.querySelector('dialog.collection-sheet[open]');"
            " const box = sel => d.querySelector(sel).getBoundingClientRect();"
            " const r = d.getBoundingClientRect();"
            " const facts = Array.from(d.querySelectorAll('.collection-facts > div'))"
            ".filter(f => !f.classList.contains('collection-facts__wide'))"
            ".map(f => f.getBoundingClientRect().top);"
            " return {dialog: [r.top, r.bottom], vh: window.innerHeight,"
            " head: box('.modal__head'), close: box('.modal__close'), dismiss: box('.modal__dismiss'),"
            " art: box('.collection-sheet__art .collection-card__image'),"
            " body: [d.querySelector('.modal__body').scrollHeight,"
            " d.querySelector('.modal__body').clientHeight], facts: facts}; }")
        assert geometry["dialog"][0] >= -0.5 and geometry["dialog"][1] <= geometry["vh"] + 0.5, geometry
        assert geometry["dialog"][1] - geometry["dialog"][0] <= geometry["vh"] * 0.85 + 1, geometry
        for part in ("head", "close", "dismiss"):
            box = geometry[part]
            assert box["top"] >= geometry["dialog"][0] - 0.5, (part, geometry)
            assert box["bottom"] <= geometry["dialog"][1] + 0.5, (part, geometry)
        assert geometry["close"]["height"] >= 44 - 0.5 and geometry["dismiss"]["height"] >= 44 - 0.5
        tops = sorted(geometry["facts"])
        assert all(b - a >= 54 - 0.5 for a, b in zip(tops, tops[1:])), geometry
        if viewport["width"] < 700:
            assert geometry["art"]["height"] <= 80, geometry
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_page_title_has_the_size_of_the_other_pages_titles(
        new_context, make_app_server, label, viewport):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        read = ("() => { const h = document.querySelector('main h1.page-title');"
                " const s = getComputedStyle(h); return [s.fontSize, s.fontWeight, s.lineHeight]; }")
        collection = page.evaluate(read)
        assert page.locator("main h1.page-title").inner_text() == "Airlines"
        page.goto(server.base_url() + "/flights")
        page.wait_for_function(_SETTLED, timeout=15000)
        page.locator("main h1.page-title").wait_for(state="visible")
        assert page.evaluate(read) == collection
    finally:
        context.close()


def test_the_control_bar_sticks_to_the_top_while_the_cards_scroll(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED)
    try:
        page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight / 2)")
        page.wait_for_function("() => window.scrollY > 300", timeout=10000)
        page.wait_for_function(
            "() => { const r = document.querySelector('.collection-controls')"
            ".getBoundingClientRect(); return r.top >= 0 && r.top < 24 && r.height > 60; }",
            timeout=10000)
        page.wait_for_function(
            "() => { const el = document.querySelector('#collection-filter');"
            " const r = el.getBoundingClientRect();"
            " return document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === el; }",
            timeout=10000)
    finally:
        context.close()


def test_the_new_pill_sits_in_the_card_corner_clear_of_the_picture_and_only_a_new_airline_has_one(
        new_context, make_app_server):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP)
    try:
        assert page.locator(".rarity-pill--new").count() == 1
        clear = page.evaluate(
            "() => { const pill = document.querySelector('.rarity-pill--new');"
            " const p = pill.getBoundingClientRect();"
            " const card = pill.closest('.collection-card').getBoundingClientRect();"
            " const img = pill.closest('.collection-card').querySelector('.collection-card__image')"
            ".getBoundingClientRect();"
            " const inCard = p.left >= card.left && p.right <= card.right && p.top >= card.top"
            " && p.bottom <= card.bottom;"
            " const overPicture = p.left < img.right && p.right > img.left"
            " && p.top < img.bottom && p.bottom > img.top;"
            " return inCard && !overPicture; }")
        assert clear
        # Each seen card reads on one line: the count, then the rarity in words.
        assert page.locator(SEEN_CARD + " .collection-card__seen").first.inner_text().count(
            "·") == 1
        assert page.locator(UNSEEN_CARD + " .collection-card__seen").count() == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang,sentence", [
    ("en", "%d of 36 airlines spotted"), ("fr", "%d compagnies repérées sur 36")])
def test_the_progress_sentence_reads_coherently_in_both_languages(
        new_context, make_app_server, lang, sentence):
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), VIEWPORT_DESKTOP, lang=lang)
    try:
        text = page.locator(".collection-progress__headline").inner_text()
        assert text == sentence % TOTAL_SPOTTED, text
        all_chip = page.locator(".filter-chip", has_text="All" if lang == "en" else "Toutes")
        assert all_chip.locator(".filter-chip__count").inner_text() == "36"
    finally:
        context.close()


@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_the_aircraft_picture_sits_inside_the_card_with_room_around_it(
        new_context, make_app_server, label, viewport):
    """the picture is inset from its card: at least 28px of card padding and picture-box padding
    on each side, so it is well under the card's own width"""
    server = make_app_server(seed=_seed)
    context, page = _open(new_context, server.base_url(), viewport)
    try:
        sizes = page.evaluate(
            "() => { const card = document.querySelector('a.collection-card:not(.collection-card--unseen)');"
            " const img = card.querySelector('.collection-card__image').getBoundingClientRect();"
            " const c = card.getBoundingClientRect();"
            " return {gapLeft: img.left - c.left, gapRight: c.right - img.right,"
            "  ratio: img.width / c.width}; }")
        assert sizes["gapLeft"] >= 28 and sizes["gapRight"] >= 28, sizes
        assert sizes["ratio"] <= 0.82, sizes
    finally:
        context.close()
