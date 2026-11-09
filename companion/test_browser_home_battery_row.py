"""Real-browser checks of the Battery row in Home's Frame group: it is there for a plain user
(not only an administrator) under the screen and quiet-hours rows, in English and French at
360 and 1280 px, in both themes, for the four states (normal with an honest autonomy figure,
low, no reading, probably charging), with a level bar drawn by SVG attributes alone."""
from datetime import datetime, timedelta, timezone

import pytest

from companion import auth, battery, layout
from companion_app_server import session_cookie_for_state_dir
from provisioned_fleet import USER_A_EMAIL, device_dir, provision_fleet
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP,
    VIEWPORT_MIN_SUPPORTED,
    VIEWPORT_PHONE,
    _assert_no_page_overflow,
    _login,
    seed_state_dir,
)
from server import device_config, history_db

pytestmark = pytest.mark.browser

VIEWPORTS = (("1280", VIEWPORT_DESKTOP), ("360", VIEWPORT_MIN_SUPPORTED))


def _mv_for(percent):
    return min(range(3000, 4300), key=lambda mv: abs(battery.percent(mv) - percent))


def _record(conn, when, mv):
    history_db.record_device_health(
        conn, when.isoformat(timespec="seconds"), battery_mv=mv, fw_version="1.0.0",
        boot_reason="wake", rssi="-60")


def _write_scene(state_dir, scene):
    """Write the battery history that tells one of the four stories."""
    now = datetime.now(timezone.utc)
    with history_db.open_db(state_dir) as conn:
        conn.execute("DELETE FROM device_health")
        conn.commit()
        if scene == "none":
            for i in range(12):
                _record(conn, now - timedelta(minutes=2 + 5 * (11 - i)), None)
            return
        if scene == "charging":
            base = _mv_for(55)
            for i in range(12):
                _record(conn, now - timedelta(minutes=2 + 5 * (11 - i)), base - 60 + i * 12)
            for day in range(1, 9):
                _record(conn, now - timedelta(days=day, hours=1), _mv_for(55 + day * 2))
            return
        percent, per_day = {"normal": (69, 3.3), "low": (18, 3.6)}[scene]
        for day in range(8, 0, -1):
            _record(conn, now - timedelta(days=day, hours=1),
                    _mv_for(min(100, percent + per_day * day)))
        for i in range(12):
            _record(conn, now - timedelta(minutes=2 + 5 * (11 - i)), _mv_for(percent))


def _seed_scene(scene):
    def seed(state_dir):
        seed_state_dir(state_dir)
        device_config.save_device_config(
            state_dir, display_enabled=True, quiet_hours_enabled=False, wake_interval_s=300)
        _write_scene(state_dir, scene)
    return seed


EXPECTED = {
    "normal": {
        "en": ("Battery", "69%", None, "battery life ~3 weeks"),
        "fr": ("Batterie", "69 %", None, "autonomie ~3 semaines"),
    },
    "low": {
        "en": ("Battery", "18%", "Low", "battery life ~"),
        "fr": ("Batterie", "18 %", "Faible", "autonomie ~"),
    },
    "charging": {
        "en": ("Battery", "5", "Probably charging", None),
        "fr": ("Batterie", "5", "Probablement en charge", None),
    },
}


def _open_user_home(new_context, make_app_server, scene, lang, viewport, scheme):
    server = make_app_server(seed=_seed_scene(scene), fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.locator(".frame-battery").wait_for(state="visible")
    page.wait_for_function("document.readyState === 'complete'")
    return context, page


def _row_geometry(page):
    return page.evaluate(
        """() => {
            const box = s => { const r = document.querySelector(s).getBoundingClientRect();
                               return {top: r.top, bottom: r.bottom, left: r.left, right: r.right,
                                       width: r.width, height: r.height}; };
            return {row: box('.frame-battery'), group: box('.home-state__switches .group'),
                    quiet: box('.home-switch--quiet'), bar: document.querySelector(
                        '.frame-battery__bar') ? box('.frame-battery__bar') : null,
                    viewport: window.innerWidth};
        }""")


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
@pytest.mark.parametrize("scene", ["normal", "low", "charging"])
def test_battery_row_shows_the_level_word_and_a_bar(
        new_context, make_app_server, scene, viewport_name, viewport, lang, scheme):
    """under the quiet-hours row, the row reads the percentage with its level word (or the
    charging wording) and a bar; the autonomy line appears only while discharging and fits"""
    label, percent, word, autonomy = EXPECTED[scene][lang]
    context, page = _open_user_home(
        new_context, make_app_server, scene, lang, viewport, scheme)
    try:
        text = page.locator(".frame-battery").inner_text()
        assert label in text
        if word is None:
            # The healthy level has no word, and nothing says "normal".
            assert "ormal" not in text
        else:
            assert word in text
        if scene != "charging":
            assert percent in text
        if autonomy is None:
            assert page.locator(".frame-battery__note").count() == 0
        else:
            assert autonomy in page.locator(".frame-battery__note").inner_text()
        if scene == "normal":
            # The percentage and the estimate share one line, the bar below.
            lines = page.evaluate(
                """() => { const r = s => document.querySelector(s).getBoundingClientRect();
                    return {state: r('.frame-battery__state'), note: r('.frame-battery__note'),
                            bar: r('.frame-battery__bar')}; }""")
            assert abs(lines["state"]["top"] - lines["note"]["top"]) < 4
            assert lines["note"]["left"] > lines["state"]["right"]
            assert lines["bar"]["top"] >= lines["state"]["bottom"] - 1
        assert page.locator(".frame-battery__fill").count() == 1
        assert page.locator(".frame-battery[class*='frame-battery--']").count() == 1
        geometry = _row_geometry(page)
        assert geometry["quiet"]["bottom"] <= geometry["row"]["top"] + 1
        assert geometry["row"]["bottom"] <= geometry["group"]["bottom"] + 1
        assert geometry["row"]["right"] <= geometry["viewport"]
        assert geometry["bar"]["height"] <= 6 and geometry["bar"]["width"] > 100
        assert page.evaluate(
            "() => !document.querySelector('.frame-battery [style], .frame-battery[style]')")
        _assert_no_page_overflow(page, "%s/%s/%s" % (scene, viewport_name, lang))
    finally:
        context.close()


def test_the_bar_width_is_the_percentage(new_context, make_app_server):
    """the fill covers the stated share of the track, drawn by attributes alone"""
    context, page = _open_user_home(
        new_context, make_app_server, "normal", "en", VIEWPORT_DESKTOP, "light")
    try:
        widths = page.evaluate(
            """() => ({
                track: document.querySelector('.frame-battery__track').getBoundingClientRect().width,
                fill: document.querySelector('.frame-battery__fill').getBoundingClientRect().width})""")
        assert abs(widths["fill"] / widths["track"] - 0.69) < 0.02
    finally:
        context.close()


@pytest.mark.parametrize("lang,sentence", [
    ("en", "No reading yet"), ("fr", "Aucune mesure pour l’instant")])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
def test_battery_row_without_a_reading_draws_no_bar(
        new_context, make_app_server, viewport_name, viewport, lang, sentence):
    """no reading: the sentence says so, with no bar and no autonomy line"""
    context, page = _open_user_home(
        new_context, make_app_server, "none", lang, viewport, "light")
    try:
        assert sentence in page.locator(".frame-battery").inner_text()
        assert page.locator(".frame-battery__bar").count() == 0
        assert page.locator(".frame-battery__note").count() == 0
        _assert_no_page_overflow(page, "none/%s/%s" % (viewport_name, lang))
    finally:
        context.close()


def test_battery_row_is_there_for_a_plain_user_without_the_dial(new_context, make_app_server):
    """a person who is not an administrator sees the row on their frame's Home, and no dial"""
    def seed(state_dir):
        fleet = provision_fleet(state_dir)
        directory = device_dir(state_dir, fleet.a1)
        device_config.save_device_config(directory, wake_interval_s=300)
        _write_scene(directory, "normal")
        seed.fleet = fleet
    server = make_app_server(seed=seed, fake_providers=True)
    context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
    try:
        base = server.base_url()
        name, value = session_cookie_for_state_dir(server.state_dir, USER_A_EMAIL).split("=", 1)
        context.add_cookies([{
            "name": name, "value": value, "url": base, "httpOnly": True,
            "sameSite": "Strict"}])
        page = context.new_page()
        page.goto(base + "/devices/%s/" % seed.fleet.a1)
        page.locator(".frame-battery").wait_for(state="visible")
        assert "69%" in page.locator(".frame-battery").inner_text()
        assert page.locator(".home-battery").count() == 0
        assert page.locator(".frame-battery__note").count() == 1
    finally:
        context.close()


WORDS = {
    "en": {"online": "Online", "next": "Next refresh in", "banned": ("Up to date", "pdate")},
    "fr": {"online": "En ligne", "next": "Prochain rafraîchissement dans",
           "banned": ("À jour", "mise à jour")},
}


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport", [VIEWPORT_PHONE, VIEWPORT_DESKTOP], ids=["390", "1280"])
def test_the_status_block_reads_as_one_coherent_statement(
        new_context, make_app_server, lang, viewport):
    """The state word is "Online" and the line under it "Next refresh in N min": no "Up to date"
    and no "update" anywhere in the block, the ring's accessible name says refresh too, and the
    frame-name title is larger than the state pill beside it."""
    context, page = _open_user_home(new_context, make_app_server, "normal", lang, viewport, "light")
    try:
        words = WORDS[lang]
        block = page.locator(".home-state").inner_text()
        assert words["online"] in block and words["next"] in block
        for banned in words["banned"]:
            assert banned not in block
        ring = page.locator("[data-cycle-ring]").get_attribute("aria-label")
        assert ("next refresh" if lang == "en" else "prochain rafraîchissement") in ring
        sizes = page.evaluate(
            """() => ({title: parseFloat(getComputedStyle(
                          document.querySelector('main h1')).fontSize),
                       word: parseFloat(getComputedStyle(
                          document.querySelector('.home-state__title')).fontSize)})""")
        assert sizes["title"] > sizes["word"] + 8
    finally:
        context.close()
