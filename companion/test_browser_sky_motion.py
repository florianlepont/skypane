"""Real-browser checks of the background and motion foundations: Light is one pale sky and Dark
one ink gradient whatever the local hour (there is no time-of-day sky and no data-sky
attribute), text stays readable over every stop and through the glass, the gradient is painted
on the root element itself without causing overflow, reduced motion zeroes the card entrance,
the entrance ends in the plain layout state, and the glass surfaces blur where the browser
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


LIGHT_STOPS = ["#E7EEF7", "#F1F3F6", "#EDF1F6"]
DARK_STOPS = ["#12151D", "#161A24", "#1A1F2B"]


@pytest.mark.parametrize("hour", (0, 6, 12, 18, 22))
def test_light_is_one_pale_sky_at_any_hour_and_text_stays_readable(
        new_context, make_app_server, hour):
    page = _open(new_context, make_app_server, hour, color_scheme="light")
    page.evaluate(_SET_THEME, "light")
    read = page.evaluate(_READ_SKY)
    assert read["sky"] is None, read
    assert [stop.upper() for stop in read["stops"]] == LIGHT_STOPS, (hour, read)
    assert read["accent"].upper() == "#1F2430"
    for stop in read["stops"]:
        for ink in (read["text"], read["accent"]):
            assert contrast_ratio(ink, stop) >= WCAG_AA_NORMAL_TEXT, (hour, stop, ink)
            glass = _hex_over(read["glass"], stop)
            assert contrast_ratio(ink, glass) >= WCAG_AA_NORMAL_TEXT, (hour, stop, ink, glass)


@pytest.mark.parametrize("hour", (6, 12, 22))
def test_dark_is_one_ink_gradient_at_any_hour(new_context, make_app_server, hour):
    """explicit Dark, and Auto on a dark system, show the same ink background at any hour"""
    explicit = _open(new_context, make_app_server, hour, color_scheme="light")
    explicit.evaluate(_SET_THEME, "dark")
    explicit_read = explicit.evaluate(_READ_SKY)
    auto = _open(new_context, make_app_server, hour, color_scheme="dark")
    auto.evaluate(_SET_THEME, "auto")
    auto_read = auto.evaluate(_READ_SKY)
    for read in (explicit_read, auto_read):
        assert [stop.upper() for stop in read["stops"]] == DARK_STOPS, (hour, read)
        assert read["accent"].upper() == "#F2EFE9"
        for stop in read["stops"]:
            glass = _hex_over(read["glass"], stop)
            for ink in (read["text"], read["accent"]):
                assert contrast_ratio(ink, stop) >= WCAG_AA_NORMAL_TEXT
                assert contrast_ratio(ink, glass) >= WCAG_AA_NORMAL_TEXT


def test_the_background_is_identical_with_and_without_script(new_context, make_app_server):
    """no script is needed for the background and there is no first-paint colour swap"""
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    context = new_context(viewport=VIEWPORT_DESKTOP, color_scheme="light", java_script_enabled=False)
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + "/")
    page.evaluate(_SET_THEME, "light")
    assert [stop.upper() for stop in page.evaluate(_READ_SKY)["stops"]] == LIGHT_STOPS


@pytest.mark.parametrize("viewport", (VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED),
                         ids=("1280", "360"))
def test_the_background_sits_on_the_root_and_causes_no_overflow(
        new_context, make_app_server, viewport):
    page = _open(new_context, make_app_server, 12, viewport=viewport)
    root = page.evaluate(
        """() => {
            const style = getComputedStyle(document.documentElement);
            const before = getComputedStyle(document.documentElement, '::before');
            return {image: style.backgroundImage, attachment: style.backgroundAttachment,
                    colour: style.backgroundColor, beforeContent: before.content};
        }""")
    assert root["image"].startswith("linear-gradient") and root["attachment"] == "scroll"
    assert root["colour"] != "rgba(0, 0, 0, 0)", "the canvas colour itself carries the sky"
    assert root["beforeContent"] in ("none", "normal"), "no fixed sky layer remains"
    assert not _assert_no_page_overflow(page, "sky/%s" % viewport["width"], viewport["width"])


def _section_motion(page):
    return page.evaluate(
        """() => Array.from(document.querySelectorAll('.dashboard-main .page-section, .dashboard-main .group-block')).map(el => {
            const style = getComputedStyle(el);
            return {duration: style.animationDuration, delay: style.animationDelay,
                    name: style.animationName};
        })""")


def test_cards_enter_in_a_short_stagger_and_end_in_their_layout_state(
        new_context, make_app_server):
    page = _open(new_context, make_app_server, 12)
    motion = _section_motion(page)
    assert len(motion) >= 2
    # A whole-pixel rise and a smooth fade, two finite animations of one duration.
    assert {item["name"] for item in motion} == {"skypane-reveal, skypane-reveal-fade"}
    assert {item["duration"] for item in motion} == {"0.4s, 0.4s"}
    # Home's facts row and hero (neither a section nor a group) come first, each a step after
    # the one before, so the groups start three steps in.
    assert [item["delay"] for item in motion[:2]] == ["0.18s", "0.24s"]
    page.wait_for_timeout(1200)
    settled = page.evaluate(
        """() => Array.from(document.querySelectorAll('.dashboard-main .page-section, .dashboard-main .group-block')).map(el => {
            const style = getComputedStyle(el);
            return {transform: style.transform, opacity: style.opacity,
                    running: el.getAnimations().length};
        })""")
    for item in settled:
        assert item == {"transform": "none", "opacity": "1", "running": 0}, item


def test_reduced_motion_zeroes_the_entrance(new_context, make_app_server):
    page = _open(new_context, make_app_server, 12, reduced_motion="reduce")
    for item in _section_motion(page):
        durations = [float(part.rstrip("s")) for part in item["duration"].split(", ")]
        assert max(durations) <= 0.0001 and set(item["delay"].split(", ")) == {"0s"}, item
    page.wait_for_timeout(100)
    opacity = page.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-main .group-block')).opacity")
    assert opacity == "1"


def test_glass_surfaces_blur_where_the_browser_supports_it(new_context, make_app_server):
    desktop = _open(new_context, make_app_server, 12)
    assert desktop.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-sidebar')).backdropFilter"
    ) == "blur(22px) saturate(1.65)"
    background = desktop.evaluate(
        "() => getComputedStyle(document.querySelector('.dashboard-sidebar')).backgroundColor")
    assert background.startswith("rgba(") and not background.endswith(", 1)")
    phone = _open(new_context, make_app_server, 12, viewport=VIEWPORT_MIN_SUPPORTED)
    # The tab bar is not glass: opaque, so nothing is blurred behind it.
    assert phone.evaluate(
        "() => getComputedStyle(document.querySelector('.tab-bar'), '::before').backdropFilter"
    ) == "none"
