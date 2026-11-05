"""Real-browser checks of the sky-and-motion foundations: the local hour picks the sky
(dawn 05-08, day 08-17, dusk 17-21, night otherwise) in the Light theme, Dark is always the
deep night sky, text stays readable over every sky stop and through the glass, the sky is a
fixed pseudo-element that causes no overflow, reduced motion zeroes the card entrance, the
entrance ends in the plain layout state, and the glass surfaces blur where the browser
supports it."""
import pytest

from skypane_contrast_check import WCAG_AA_NORMAL_TEXT, contrast_ratio
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    _assert_no_page_overflow,
    _login,
    seed_state_dir,
)

pytestmark = pytest.mark.browser

# (local hour, expected sky) around every band edge.
HOUR_BANDS = (
    (0, "night"), (4, "night"), (5, "dawn"), (7, "dawn"), (8, "day"), (12, "day"),
    (16, "day"), (17, "dusk"), (20, "dusk"), (21, "night"), (23, "night"),
)
STOPS = ("--sky-top", "--sky-mid", "--sky-bottom")

_READ_SKY = """() => {
    const style = getComputedStyle(document.documentElement);
    return {
        sky: document.documentElement.getAttribute('data-sky'),
        stops: ['--sky-top', '--sky-mid', '--sky-bottom'].map(n => style.getPropertyValue(n).trim()),
        text: style.getPropertyValue('--color-text').trim(),
        accent: style.getPropertyValue('--color-accent').trim(),
        glass: style.getPropertyValue('--glass-bg').trim(),
    };
}"""

_SET_THEME = "theme => document.documentElement.setAttribute('data-ui-theme', theme)"


def _open(new_context, make_app_server, hour, viewport=VIEWPORT_DESKTOP, route="/", **context_args):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=viewport, **context_args)
    page = context.new_page()
    # The viewer's local hour is the only clock input the sky reads.
    page.add_init_script("Date.prototype.getHours = function () { return %d; };" % hour)
    _login(page, server.base_url())
    page.goto(server.base_url() + route)
    page.wait_for_load_state("load")
    page.locator("main").wait_for(state="visible")
    return page


def _hex_over(rgba, backdrop):
    parts = [float(p) for p in rgba[rgba.index("(") + 1:rgba.index(")")].split(",")]
    red, green, blue, alpha = parts
    back = [int(backdrop[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(
        round(alpha * fg + (1 - alpha) * bg) for fg, bg in zip((red, green, blue), back))


@pytest.mark.parametrize("hour, expected", HOUR_BANDS, ids=["%02dh-%s" % band for band in HOUR_BANDS])
def test_local_hour_picks_the_light_sky_and_text_stays_readable(
        new_context, make_app_server, hour, expected):
    page = _open(new_context, make_app_server, hour, color_scheme="light")
    page.evaluate(_SET_THEME, "light")
    read = page.evaluate(_READ_SKY)
    assert read["sky"] == expected, (hour, read)
    for stop in read["stops"]:
        for ink in (read["text"], read["accent"]):
            assert contrast_ratio(ink, stop) >= WCAG_AA_NORMAL_TEXT, (hour, stop, ink)
            glass = _hex_over(read["glass"], stop)
            assert contrast_ratio(ink, glass) >= WCAG_AA_NORMAL_TEXT, (hour, stop, ink, glass)


def test_the_four_light_skies_paint_four_different_gradients(new_context, make_app_server):
    seen = {}
    for hour, expected in ((6, "dawn"), (12, "day"), (18, "dusk"), (22, "night")):
        page = _open(new_context, make_app_server, hour, color_scheme="light")
        page.evaluate(_SET_THEME, "light")
        seen[expected] = tuple(page.evaluate(_READ_SKY)["stops"])
        page.context.close()
    assert len(set(seen.values())) == 4, seen


@pytest.mark.parametrize("hour", (6, 12, 18, 22))
def test_dark_theme_is_always_the_night_sky(new_context, make_app_server, hour):
    """explicit Dark, and Auto on a dark system, show the same deep sky at any hour"""
    explicit = _open(new_context, make_app_server, hour, color_scheme="light")
    explicit.evaluate(_SET_THEME, "dark")
    explicit_read = explicit.evaluate(_READ_SKY)
    auto = _open(new_context, make_app_server, hour, color_scheme="dark")
    auto.evaluate(_SET_THEME, "auto")
    auto_read = auto.evaluate(_READ_SKY)
    for read in (explicit_read, auto_read):
        assert read["stops"] == ["#0B1026", "#18203F", "#2C2540"], (hour, read)
        for stop in read["stops"]:
            glass = _hex_over(read["glass"], stop)
            for ink in (read["text"], read["accent"]):
                assert contrast_ratio(ink, stop) >= WCAG_AA_NORMAL_TEXT
                assert contrast_ratio(ink, glass) >= WCAG_AA_NORMAL_TEXT


def test_without_script_the_sky_defaults_to_day(new_context, make_app_server):
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme="light", java_script_enabled=False)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/")
    assert page.evaluate("() => document.documentElement.hasAttribute('data-sky')") is False
    page.evaluate(_SET_THEME, "light")
    assert page.evaluate(_READ_SKY)["stops"] == ["#D5E7F6", "#E3EDF5", "#F4F1EA"]


@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED),
                         ids=("1280", "360"))
def test_the_sky_is_fixed_and_causes_no_overflow(new_context, make_app_server, viewport):
    page = _open(new_context, make_app_server, 12, viewport=viewport)
    sky = page.evaluate(
        """() => {
            const style = getComputedStyle(document.documentElement, '::before');
            return {position: style.position, events: style.pointerEvents,
                    image: style.backgroundImage, attachment: style.backgroundAttachment};
        }""")
    assert sky["position"] == "fixed" and sky["events"] == "none"
    assert sky["image"].startswith("linear-gradient") and sky["attachment"] == "scroll"
    assert not _assert_no_page_overflow(page, "sky/%s" % viewport["width"], viewport["width"])


def _section_motion(page):
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.dashboard-main .page-section')).map(el => {
            const style = getComputedStyle(el);
            return {duration: style.animationDuration, delay: style.animationDelay,
                    name: style.animationName};
        })""")


def test_cards_enter_in_a_short_stagger_and_end_in_their_layout_state(
        new_context, make_app_server):
    page = _open(new_context, make_app_server, 12)
    motion = _section_motion(page)
    assert len(motion) >= 2
    assert {item["name"] for item in motion} == {"skypane-reveal"}
    assert {item["duration"] for item in motion} == {"0.4s"}
    assert motion[0]["delay"] == "0s" and motion[1]["delay"] == "0.06s"
    page.wait_for_timeout(1200)
    settled = page.evaluate(
        """() => Array.from(document.querySelectorAll('.dashboard-main .page-section')).map(el => {
            const style = getComputedStyle(el);
            return {transform: style.transform, opacity: style.opacity,
                    running: el.getAnimations().length};
        })""")
    for item in settled:
        assert item == {"transform": "none", "opacity": "1", "running": 0}, item


def test_reduced_motion_zeroes_the_entrance(new_context, make_app_server):
    page = _open(new_context, make_app_server, 12, reduced_motion="reduce")
    for item in _section_motion(page):
        assert float(item["duration"].rstrip("s")) <= 0.0001 and item["delay"] == "0s", item
    page.wait_for_timeout(100)
    opacity = page.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-main .page-section')).opacity")
    assert opacity == "1"


def test_glass_surfaces_blur_where_the_browser_supports_it(new_context, make_app_server):
    desktop = _open(new_context, make_app_server, 12)
    assert desktop.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-sidebar')).backdropFilter"
    ) == "blur(16px)"
    background = desktop.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-sidebar')).backgroundColor")
    assert background.startswith("rgba(") and not background.endswith(", 1)")
    phone = _open(new_context, make_app_server, 12, viewport=VIEWPORT_MIN_SUPPORTED)
    assert phone.evaluate(
        "() => getComputedStyle(document.querySelector('.tab-bar')).backdropFilter"
    ) == "blur(16px)"
