"""Real-browser checks of the theme and language segmented switches in the sidebar and the
mobile menu: in both languages and from 320px up to the desktop sidebar, no segment's label
overflows its own box and neighbouring labels never intersect. A deliberately oversized label
is clipped inside its own segment, so a future longer translation cannot collide either."""
import pytest

from companion import auth
from companion.test_browser_ux_helpers import _login

pytestmark = pytest.mark.browser



@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


WIDTHS = (320, 360, 390, 768, 960, 1024, 1280)

_MEASURE = """oversize => {
    const forms = [...document.querySelectorAll('.theme-form')].filter(f => f.offsetParent);
    return forms.map(form => {
        const buttons = [...form.querySelectorAll('.theme-option')];
        if (oversize) buttons[0].textContent = 'Automatiquement systeme';
        return buttons.map(b => {
            const range = document.createRange();
            range.selectNodeContents(b);
            const text = range.getBoundingClientRect();
            const box = b.getBoundingClientRect();
            return {label: b.textContent, scroll: b.scrollWidth, client: b.clientWidth,
                    text: {left: text.left, right: text.right},
                    box: {left: box.left, right: box.right},
                    clipped: getComputedStyle(b).overflow === 'hidden'};
        });
    });
}"""


def _open(new_context, base_url, lang, width, scheme):
    context = new_context(viewport={"width": width, "height": 800}, color_scheme=scheme)
    context.add_cookies([{"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + "/")
    toggle = page.locator('[aria-controls="mobile-nav"]').first
    if toggle.count() and toggle.is_visible():
        toggle.click()
        page.locator(".mobile-nav--open .theme-form").first.wait_for(state="visible")
    else:
        page.locator(".dashboard-sidebar .theme-form").first.wait_for(state="visible")
    return context, page


def _assert_isolated(forms, label, oversize):
    assert len(forms) >= 2, label
    for segments in forms:
        for seg in segments:
            where = "%s %r" % (label, seg["label"])
            assert seg["text"]["left"] >= seg["box"]["left"] - 1, where
            if oversize:
                assert seg["clipped"], where
            else:
                assert seg["scroll"] <= seg["client"], where
            assert seg["text"]["right"] <= seg["box"]["right"] + 1 or seg["clipped"], where
        for left, right in zip(segments, segments[1:]):
            assert left["box"]["right"] <= right["box"]["left"] + 1, label
            if not (left["clipped"] and right["clipped"]):
                continue
            assert left["text"]["right"] <= right["text"]["left"] + 1, label


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["fr", "en"])
@pytest.mark.parametrize("width", WIDTHS)
def test_no_segment_label_overflows_or_touches_its_neighbour(
        new_context, server, lang, width, scheme):
    """every theme and language segment's text fits inside its own box (scrollWidth <=
    clientWidth) and adjacent segments' text boxes do not intersect"""
    context, page = _open(new_context, server.base_url(), lang, width, scheme)
    try:
        _assert_isolated(page.evaluate(_MEASURE, False), "%s/%s/%d" % (lang, scheme, width), False)
        labels = [f for f in page.evaluate(_MEASURE, False) if len(f) == 3][0]
        expected = ["Auto", "Clair", "Sombre"] if lang == "fr" else ["Auto", "Light", "Dark"]
        assert [s["label"] for s in labels] == expected
    finally:
        context.close()


@pytest.mark.parametrize("width", (320, 1280))
def test_an_oversized_label_is_clipped_inside_its_own_segment(
        new_context, server, width):
    """a label far wider than its segment is clipped by that segment instead of painting over
    the next one"""
    context, page = _open(new_context, server.base_url(), "en", width, "dark")
    try:
        forms = page.evaluate(_MEASURE, True)
        for segments in forms:
            first, second = segments[0], segments[1]
            assert first["clipped"]
            assert first["box"]["right"] <= second["box"]["left"] + 1
    finally:
        context.close()


def test_the_auto_segment_keeps_an_explicit_accessible_name(new_context, server):
    """the abbreviated Auto label carries the full meaning as its accessible name in French
    and English, starting with the visible text"""
    for lang, name in (("fr", "Auto (suit le système)"), ("en", "Auto (follows the system)")):
        context, page = _open(new_context, server.base_url(), lang, 1280, "light")
        try:
            button = page.locator('.theme-form button[value="auto"]:visible').first
            assert button.get_attribute("aria-label") == name
        finally:
            context.close()
