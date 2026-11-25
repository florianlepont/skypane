"""Real-browser checks of the battery pill on Home: it is there for a plain user (not only an
administrator) in the pills row, in English and French at 360 and 1280 px, in both themes, for the
four states (normal, low, no reading, probably charging); its text is centred in the capsule, a low
level says so in words and the page never overflows."""
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
    "normal": {"en": ("Battery 69%", None), "fr": ("Batterie 69 %", None)},
    "low": {"en": ("Battery 18%", "Low"), "fr": ("Batterie 18 %", "Faible")},
    "charging": {"en": ("Battery", "Probably charging"), "fr": ("Batterie", "Probablement en charge")},
    "none": {"en": ("Battery \u00b7 No reading yet", None), "fr": ("Batterie \u00b7 Aucune mesure pour l\u2019instant", None)},
}


def _open_user_home(new_context, make_app_server, scene, lang, viewport, scheme):
    server = make_app_server(seed=_seed_scene(scene), fake_providers=True)
    context = new_context(viewport=viewport, color_scheme=scheme)
    context.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": server.base_url()}])
    page = context.new_page()
    _login(page, server.base_url())
    page.goto(server.base_url() + layout.HOME_ROUTE)
    page.locator(".home-battery-pill").wait_for(state="visible")
    page.wait_for_function("document.readyState === 'complete'")
    return context, page


@pytest.mark.parametrize("scheme", ["light", "dark"])
@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("viewport_name,viewport", VIEWPORTS, ids=[v[0] for v in VIEWPORTS])
@pytest.mark.parametrize("scene", ["normal", "low", "charging", "none"])
def test_battery_pill_shows_the_charge_and_a_word_and_fits(
        new_context, make_app_server, scene, viewport_name, viewport, lang, scheme):
    context, page = _open_user_home(new_context, make_app_server, scene, lang, viewport, scheme)
    try:
        pill = page.locator(".home-battery-pill")
        text = " ".join(pill.inner_text().split()).replace("\u00a0", " ")
        lead, word = EXPECTED[scene][lang]
        assert text.startswith(lead.replace("\u00a0", " ")), (scene, text)
        if scene == "normal":
            assert "\u00b7" not in text, text
        if word:
            assert word in text, (scene, text)
        box = pill.bounding_box()
        assert box["height"] >= 44 and box["x"] >= 0 and box["x"] + box["width"] <= viewport["width"]
        offset = page.evaluate(
            """() => { const el = document.querySelector('.home-battery-pill');
              const box = el.getBoundingClientRect();
              const range = document.createRange();
              range.selectNodeContents(el.querySelector('.home-pill__text'));
              const t = range.getBoundingClientRect();
              return (t.top + t.height / 2) - (box.top + box.height / 2); }""")
        assert abs(offset) <= 1.5, offset
        assert page.locator(".home-battery").count() == 0
        failure = _assert_no_page_overflow(page, "home/%s" % scene, viewport["width"])
        assert not failure, failure
    finally:
        context.close()


def test_the_pill_is_there_for_a_plain_user_without_a_dial(new_context, make_app_server):
    """a plain user (not an administrator) sees the battery pill, and no pill ever draws a dial"""
    seed = _user_seed()
    server = make_app_server(seed=seed)
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        pair = session_cookie_for_state_dir(server.state_dir, USER_A_EMAIL)
        name, value = pair.split("=", 1)
        context.add_cookies([{"name": name, "value": value, "url": server.base_url(),
                              "httpOnly": True, "sameSite": "Strict"}])
        page = context.new_page()
        page.goto("%s/devices/%s/" % (server.base_url(), seed.fleet.a1))
        page.locator(".home-battery-pill").wait_for(state="visible")
        assert page.locator(".home-battery-pill svg.drawing").count() == 0
        assert "Battery" in page.locator(".home-battery-pill").inner_text()
    finally:
        context.close()


def _user_seed():
    def seed(state_dir):
        seed.fleet = provision_fleet(state_dir)
        directory = device_dir(state_dir, seed.fleet.a1)
        with history_db.open_db(directory) as conn:
            _record(conn, datetime.now(timezone.utc) - timedelta(minutes=2), _mv_for(70))
    return seed
