"""Real-browser check that Flights and Airlines draw the same filter: one controls form followed
by exactly one status count line in the same place, with the same look, 44px targets and an
accessible search name, in English and French, Light and Dark, at 360 and 1280 px; and that the
count keeps following the search live on both pages."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import (
    UI_THEMES_EXPLICIT,
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    _set_ui_theme,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

VIEWPORTS = (("360", VIEWPORT_MIN_SUPPORTED), ("1280", VIEWPORT_DESKTOP))
PAGES = ("/flights", "/airlines")

_PROBE = """() => {
  const form = document.querySelector('form.filter-bar.filter-controls');
  const count = form.nextElementSibling;
  const style = getComputedStyle(count);
  const chips = form.querySelector('.filter-chips, [role=group], .segmented') || form;
  const search = form.querySelector('input[type=search], input[type=text]');
  const field = search.getBoundingClientRect();
  const label = search.getAttribute('aria-label')
    || (search.labels && search.labels.length ? search.labels[0].textContent : '');
  const formBox = form.getBoundingClientRect();
  const countBox = count.getBoundingClientRect();
  return {
    rowChildren: [...form.querySelector('.filter-controls__row').children].map(c => c.tagName),
    formChildren: [...form.children].map(
      c => (c.className || c.tagName).replace(/\s*js-gate/, '')),
    countTag: count.tagName, countClass: count.className,
    countRole: count.getAttribute('role'),
    countAttr: count.hasAttribute('data-filter-count'),
    countElements: document.querySelectorAll('[data-filter-count]').length,
    entityCounts: document.querySelectorAll('.entity-count, .filter-bar__count').length,
    fontSize: style.fontSize, color: style.color, margin: style.margin,
    gap: Math.round(countBox.top - formBox.bottom),
    fieldHeight: field.height, label: label.trim(),
    chipsBackground: getComputedStyle(chips).backgroundColor,
  };
}"""


def _open(new_context, base_url, viewport, path, lang="en", theme="light"):
    context = new_context(viewport=viewport)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + path)
    page.locator("form.filter-bar.filter-controls").wait_for(state="visible")
    _set_ui_theme(page, theme)
    return context, page


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("label,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_flights_and_airlines_draw_one_filter(
        new_context, make_app_server, label, viewport, theme, lang):
    server = make_app_server(seed=seed_state_dir)
    probes = {}
    for path in PAGES:
        context, page = _open(new_context, server.base_url(), viewport, path, lang, theme)
        try:
            probes[path] = page.evaluate(_PROBE)
            assert not _assert_no_page_overflow(page, path, viewport["width"])
        finally:
            context.close()
    flights, airlines = probes["/flights"], probes["/airlines"]
    for probe in probes.values():
        assert probe["countTag"] == "P" and probe["countClass"] == "filter-count"
        assert probe["countRole"] == "status" and probe["countAttr"]
        assert probe["countElements"] == 1 and probe["entityCounts"] == 0
        assert probe["fieldHeight"] >= 44 and probe["label"]
        assert abs(probe["gap"]) <= 8
    for key in ("rowChildren", "formChildren", "fontSize", "color", "margin",
                "fieldHeight", "chipsBackground"):
        assert flights[key] == airlines[key], key


@pytest.mark.parametrize("path", PAGES)
def test_the_count_follows_the_search_live(new_context, make_app_server, path):
    server = make_app_server(seed=seed_state_dir)
    context, page = _open(new_context, server.base_url(), VIEWPORT_MIN_SUPPORTED, path)
    try:
        count = page.locator("[data-filter-count]")
        before = count.inner_text()
        page.locator("form.filter-controls input[type=search], form.filter-controls input[type=text]"
                     ).first.fill("zzzz-no-match")
        page.wait_for_function(
            "(was) => document.querySelector('[data-filter-count]').textContent !== was",
            arg=before, timeout=10000)
        assert page.locator("[data-filter-count]").count() == 1
        assert page.locator("p.filter-count[role=status]").count() == 1
    finally:
        context.close()


def test_the_users_caption_keeps_its_own_class(new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir)
    context, page = _open_users(new_context, server.base_url())
    try:
        assert page.locator(".entity-count").count() >= 1
    finally:
        context.close()


def _open_users(new_context, base_url):
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + "/users")
    page.locator("main").wait_for(state="visible")
    return context, page
