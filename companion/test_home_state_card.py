"""The merged frame-state card on Home: the wording of each state, the two
native POST controls, their persisted effect and flash, and the precedence
of the battery-empty hold and the display switch. Everything is asserted on
served markup (a direct render for the state matrix, a real server for the
POST round trips)."""
import re
import urllib.parse

import pytest

import companion.layout as layout
import companion.prefs as prefs
import companion.wake as wake
from companion import auth
from companion.pages import home_page
from companion_app_server import http_request, login
from server import device_config

NOW = "2026-08-27T12:00:00+00:00"
CHECKIN = "2026-08-27T11:55:00+00:00"


def _ctx(tmp_path, cfg=None, battery_critical=False, last_checkin_ts=CHECKIN):
    base = {"wake_interval_s": 900, "display_enabled": True}
    base.update(cfg or {})
    return {
        "state_dir": str(tmp_path), "now": NOW, "gallery_entries": [],
        "last_checkin_ts": last_checkin_ts, "device_config": base,
        "battery_critical": battery_critical,
        "health_state": {"device_state": "ok", "pipeline_state": "ok", "battery_state": "ok"},
    }


def _card(rendered):
    start = rendered.index('<section class="page-section home-section home-state"')
    return rendered[start:rendered.index("</section>", start)]


def _render(tmp_path, lang="en", **kwargs):
    prefs.set_request_prefs(lang=lang)
    try:
        return _card(home_page.render(_ctx(tmp_path, **kwargs)))
    finally:
        prefs.set_request_prefs(lang="en")


def _form(card, action):
    match = re.search(
        r'<form method="post" action="%s"[^>]*>(.*?)</form>' % re.escape(action), card, re.S)
    assert match is not None, "no POST form to %s" % action
    return match.group(1)


def test_screen_on_state_wording_and_both_controls(tmp_path):
    """the default state reads "Screen on", names the next update and the cadence, and offers
    to turn the screen off and the quiet hours off, each as a native POST form"""
    card = _render(tmp_path, cfg={"quiet_hours_enabled": True})
    assert "Screen on" in card
    assert "Next update ≈" in card and "data-relative-countdown" in card
    assert "wakes about every 15 min, so it does not refresh continuously" in card
    assert "Quiet hours are on, 23:00 to 07:00" in card
    screen = _form(card, "/quick/display")
    assert 'name="state" value="off"' in screen and 'name="return_to" value="/"' in screen
    assert "Turn screen off" in screen
    quiet = _form(card, "/quick/quiet-hours")
    assert 'name="state" value="off"' in quiet and "Turn quiet hours off" in quiet


def test_screen_off_state_offers_to_turn_it_on(tmp_path):
    """display_enabled=false reads "Screen off" and the screen form posts state=on; the cadence
    sentence quotes the screen-off interval, not the configured one"""
    card = _render(tmp_path, cfg={"display_enabled": False})
    assert "Screen off" in card and "Screen on" not in card
    screen = _form(card, "/quick/display")
    assert 'name="state" value="on"' in screen and "Turn screen on" in screen
    off_minutes = device_config.DISPLAY_OFF_SLEEP_S // 60
    assert "about every %d min" % off_minutes in card


def test_quiet_hours_state_names_the_end_time_and_offers_resume(tmp_path):
    """inside the quiet window the headline reads "until HH:MM" and the control turns quiet
    hours off; with the schedule disabled the same clock reads "Screen on" and the control
    turns it on"""
    window = {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"}
    card = _render(tmp_path, cfg=window)
    assert "Quiet hours — the screen rests until 23:59" in card
    assert "Turn quiet hours off" in _form(card, "/quick/quiet-hours")
    window["quiet_hours_enabled"] = False
    card = _render(tmp_path, cfg=window)
    assert "Screen on" in card and "rests until" not in card
    assert "Quiet hours are turned off" in card
    quiet = _form(card, "/quick/quiet-hours")
    assert 'name="state" value="on"' in quiet and "Turn quiet hours on" in quiet


def test_battery_empty_hold_outranks_the_display_switch(tmp_path):
    """a battery-critical hold beats display_enabled=false in both the state wording and the
    cadence sentence, exactly as wake.effective_wake_interval_s() orders them"""
    card = _render(tmp_path, cfg={"display_enabled": False}, battery_critical=True)
    assert "Battery very low" in card and "Screen off" not in card
    hold = wake.effective_wake_interval_s({"display_enabled": False}, battery_critical=True)
    assert hold == device_config.BATTERY_CRITICAL_SLEEP_S
    assert "about every %d h" % (hold // 3600) in card or "about every %d min" % (hold // 60) in card


def test_without_a_check_in_there_is_no_next_update_but_the_controls_remain(tmp_path):
    """no check-in: no invented next-update line, the cadence sentence and both forms stay"""
    card = _render(tmp_path, last_checkin_ts=None)
    assert "Next update" not in card and "home-state__next" not in card
    assert "does not refresh continuously" in card
    assert "/quick/display" in card and "/quick/quiet-hours" in card


def test_french_state_card(tmp_path):
    """the card reads in French: heading, state, cadence, quiet schedule and both buttons"""
    card = _render(tmp_path, lang="fr", cfg={"quiet_hours_enabled": True})
    for text in ("État du cadre", "Écran allumé", "Prochaine mise à jour ≈",
                 "il ne se rafraîchit donc pas en continu", "Les heures calmes sont activées",
                 "Éteindre l’écran", "Désactiver les heures calmes"):
        assert text in card, text
    assert "Screen on" not in card and "Turn screen off" not in card


def _lang_cookie(cookie, lang):
    return "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)


@pytest.mark.parametrize("action,field,flash_off,flash_on,text_off,text_on", [
    ("/quick/display", "display_enabled", "display_off", "display_on",
     "Screen switched off", "Screen switched on"),
    ("/quick/quiet-hours", "quiet_hours_enabled", "quiet_off", "quiet_on",
     "Quiet hours turned off", "Quiet hours turned on"),
])
def test_post_round_trip_persists_flashes_and_returns_to_home(
        make_app_server, action, field, flash_off, flash_on, text_off, text_on):
    """posting the Home form's own fields persists the flip, redirects to Home with the
    matching flash key, Home then shows that flash text and the opposite button; no JS header
    is involved, so this is exactly the scripts-blocked path"""
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    device_config.save_device_config(server.state_dir, quiet_hours_enabled=True)
    for state, flash, text, expected in (
            ("off", flash_off, text_off, False), ("on", flash_on, text_on, True)):
        body = urllib.parse.urlencode(
            {layout.QUICK_STATE_FIELD: state, "return_to": layout.HOME_ROUTE}).encode()
        status, headers, _ = http_request(
            server.base_url() + action, method="POST", cookie=cookie, data=body)
        assert status == 303
        assert headers.get("Location") == "/?flash=%s" % flash
        assert device_config.load_device_config(server.state_dir)[field] is expected
        status, _headers, page = http_request(
            server.base_url() + headers["Location"], cookie=cookie)
        html = page.decode("utf-8")
        assert status == 200 and text in html
        card = _card(html)
        assert 'name="state" value="%s"' % ("on" if state == "off" else "off") in _form(card, action)


def test_home_page_flash_is_translated(make_app_server):
    """the confirmation flash after a Home action reads in French for a French reader"""
    server = make_app_server(fake_providers=True)
    cookie = _lang_cookie(login(server), "fr")
    status, _headers, page = http_request(
        server.base_url() + "/?flash=display_off", cookie=cookie)
    assert status == 200 and "Écran éteint" in page.decode("utf-8")


def test_a_rejected_state_value_changes_nothing(make_app_server):
    """a crafted state value redirects back to Home with the failure flash and writes nothing"""
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    before = device_config.load_device_config(server.state_dir)
    body = urllib.parse.urlencode({"state": "toggle", "return_to": "/"}).encode()
    status, headers, _ = http_request(
        server.base_url() + "/quick/display", method="POST", cookie=cookie, data=body)
    assert status == 303 and headers.get("Location") == "/?flash=quick_failed"
    assert device_config.load_device_config(server.state_dir) == before
