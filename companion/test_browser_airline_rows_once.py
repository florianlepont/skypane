# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser checks that the Editor's "Missing illustrations" list says the shared "no sighting
yet, pick the type in the dialog" sentence once, above the list, and not once per row: each row that
asks for the type shows one short action label, keeps an accessible name that carries its airline,
stays a 44px target and keeps readable text. English and French, light and dark, at 360 px, and
under reduced motion no animation runs."""
import animation_settle
import pytest

from companion import auth
from companion.test_browser_airline_helpers import seed_airline_editor
from companion.test_browser_ux_helpers import _assert_no_page_overflow, _login
from server import history_db
from server.plane import manual_resolutions

pytestmark = pytest.mark.browser

SECTION = "#airlines-missing"
ASK_ROW = SECTION + " .airlines-missing__item:has([data-view-panel-ask-type])"
SENTENCE = {"en": "No sighting yet", "fr": "Aucun passage observé"}
OLD_LABEL = {"en": "Type to choose", "fr": "Type à choisir"}
ACTION = {"en": "Choose type", "fr": "Choisir le type"}
WIDTH = 360
SIGHTINGS = (("Emirates", "A388", 4), ("Emirates", "B77W", 2), ("Korean Air", "AN24", 1))

# Colours go through a 1x1 canvas so any CSS colour syntax becomes plain RGBA; a background is the
# stack of translucent layers up to the page canvas.
CONTRAST = """
sel => {
  const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', {willReadFrequently: true});
  const rgba = (css) => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1); const d = ctx.getImageData(0, 0, 1, 1).data;
    return [d[0], d[1], d[2], d[3] / 255]; };
  const over = (top, under) => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat([1]);
  const background = (el) => { const layers = [];
    for (let n = el; n; n = n.parentElement) layers.push(rgba(getComputedStyle(n).backgroundColor));
    let out = matchMedia('(prefers-color-scheme: dark)').matches
      ? rgba(getComputedStyle(document.documentElement).getPropertyValue('--color-canvas')) : [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) out = over(layers[i], out);
    return out; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 :
      Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const rows = [...document.querySelectorAll(sel)];
  const texts = [document.querySelector('#airlines-missing > .section-caption'),
    ...rows.map(r => r.querySelector('.airlines-missing__family'))];
  return {heights: rows.map(r => r.getBoundingClientRect().height),
    ratios: texts.map(t => { const bg = background(t);
      return ratio(over(rgba(getComputedStyle(t).color), bg), bg); })};
}
"""


def _seed(state_dir):
    from datetime import datetime, timedelta, timezone
    seed_airline_editor(state_dir)
    manual_resolutions.add_entry(state_dir, "ZPH", "Zephyr Air")
    now = datetime.now(timezone.utc)
    number = 0
    with history_db.open_db(state_dir) as conn:
        for airline, code, count in SIGHTINGS:
            for _ in range(count):
                number += 1
                history_db.record_runway_event(
                    conn, ts=(now - timedelta(hours=number)).isoformat(), hex="ro%04d" % number,
                    callsign="XXX%03d" % number, aircraft_type=code,
                    confirmed_state="departing", airline=airline)


def _open(new_context, server, lang, theme):
    context = new_context(
        viewport={"width": WIDTH, "height": 740}, color_scheme=theme, reduced_motion="reduce")
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/airlines/manage")
    page.wait_for_function(animation_settle.SETTLED, timeout=15000)
    return context, page


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("theme", ("light", "dark"))
def test_the_sentence_is_said_once_above_the_list_and_rows_keep_their_names(
        new_context, make_app_server, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, lang, theme)
    try:
        rows = page.locator(ASK_ROW)
        assert rows.count() >= 2
        text = page.locator(SECTION).inner_text()
        assert text.count(SENTENCE[lang]) == 1
        caption = page.locator(SECTION + " > .section-caption")
        assert caption.count() == 1 and SENTENCE[lang] in caption.inner_text()
        assert page.evaluate(
            "sel => document.querySelector(sel + ' > .section-caption').compareDocumentPosition("
            "document.querySelector(sel + ' .airlines-missing__list')) & Node.DOCUMENT_POSITION_FOLLOWING",
            SECTION)
        for index in range(rows.count()):
            row = rows.nth(index)
            assert SENTENCE[lang] not in row.inner_text()
            assert OLD_LABEL[lang] not in row.inner_text()
            assert row.inner_text().strip() == ACTION[lang]
            name = row.evaluate(
                "li => { let e = li.previousElementSibling; while (!e.classList.contains("
                "'airlines-missing__head')) e = e.previousElementSibling;"
                " return e.querySelector('.airlines-missing__name').textContent; }")
            aria = row.locator("button[aria-label]").first.get_attribute("aria-label")
            assert name in aria
        assert not _assert_no_page_overflow(page, "missing illustrations", WIDTH)
        assert page.evaluate("() => document.getAnimations().filter(a => a.playState === 'running').length") == 0
    finally:
        context.close()


@pytest.mark.parametrize("lang", ("en", "fr"))
@pytest.mark.parametrize("theme", ("light", "dark"))
def test_the_rows_stay_forty_four_pixels_and_the_text_stays_readable(
        new_context, make_app_server, lang, theme):
    server = make_app_server(seed=_seed, fake_providers=True)
    context, page = _open(new_context, server, lang, theme)
    try:
        out = page.evaluate(CONTRAST, ASK_ROW)
        assert out["heights"] and all(h >= 44 - 0.5 for h in out["heights"]), out
        assert min(out["ratios"]) >= 4.5, out
    finally:
        context.close()
