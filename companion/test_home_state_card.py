"""The status header on Home: the wording of each state, the two
native POST controls, their persisted effect and flash, and the precedence
of the battery-empty hold and the display switch. Everything is asserted on
served markup (a direct render for the state matrix, a real server for the
POST round trips)."""
import re
import urllib.parse
from datetime import datetime, timedelta

import pytest

import companion.battery as battery
import companion.layout as layout
import companion.prefs as prefs
import companion.wake as wake
from companion import auth
from companion.pages import home_page
from companion_app_server import http_request, login
from server import device_config, history_db

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
    start = rendered.index('<section class="home-state"')
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


def _switch(card, action):
    """The `role="switch"` button inside the form posting to `action`."""
    match = re.search(r'<button[^>]*role="switch"[^>]*>', _form(card, action))
    assert match is not None, "no switch button in the form to %s" % action
    return match.group(0)


def _checked(card, action):
    return re.search(r'aria-checked="(true|false)"', _switch(card, action)).group(1)


def test_screen_on_state_wording_and_both_switches(tmp_path):
    """the default state reads "Screen on", names the next update and the cadence, and offers
    two native POST switches that are checked, each posting the opposite state"""
    card = _render(tmp_path, cfg={"quiet_hours_enabled": True})
    assert "Screen on" in card
    assert "Next update ≈" in card and "data-relative-countdown" in card
    assert "Updates about every 15 min" in card
    assert "wakes about every" not in card
    assert "23:00 – 07:00" in card
    assert _checked(card, "/quick/display") == "true"
    assert _checked(card, "/quick/quiet-hours") == "true"
    for action in ("/quick/display", "/quick/quiet-hours"):
        form = _form(card, action)
        assert 'name="state" value="off"' in form and 'name="return_to" value="/"' in form


def test_switches_are_named_and_described_for_assistive_tech(tmp_path):
    """each switch is a labelled control: aria-labelledby points at the visible row label and
    aria-describedby at the visible On/Off word, and the row carries no JS-optimistic region"""
    card = _render(tmp_path)
    for action, slug, label in (("/quick/display", "screen", "Screen"),
                                ("/quick/quiet-hours", "quiet", "Quiet hours")):
        button = _switch(card, action)
        assert 'aria-labelledby="home-switch-%s-label"' % slug in button
        assert 'aria-describedby="home-switch-%s-state"' % slug in button
        assert re.search(r'id="home-switch-%s-label">%s</span>' % (slug, label), card)
        assert 'id="home-switch-%s-state"' % slug in card
    assert "data-quick-region" not in card


def test_screen_off_state_flips_the_screen_switch(tmp_path):
    """display_enabled=false reads "Screen off", the screen switch is unchecked and posts
    state=on; the cadence sentence quotes the screen-off interval, not the configured one"""
    card = _render(tmp_path, cfg={"display_enabled": False})
    assert "Screen off" in card and "Screen on" not in card
    assert _checked(card, "/quick/display") == "false"
    assert 'name="state" value="on"' in _form(card, "/quick/display")
    off_minutes = device_config.DISPLAY_OFF_SLEEP_S // 60
    assert "about every %d min" % off_minutes in card


def test_quiet_hours_state_names_the_end_time_and_the_window(tmp_path):
    """inside the quiet window the headline reads "until HH:MM" and the switch is checked; with
    the schedule disabled the same clock reads "Screen on", the switch is unchecked and the
    window stays visible beside it"""
    window = {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"}
    card = _render(tmp_path, cfg=window)
    assert "Quiet hours — the screen rests until 23:59" in card
    assert _checked(card, "/quick/quiet-hours") == "true"
    assert "00:00 – 23:59" in card
    window["quiet_hours_enabled"] = False
    card = _render(tmp_path, cfg=window)
    assert "Screen on" in card and "rests until" not in card
    assert _checked(card, "/quick/quiet-hours") == "false"
    assert "00:00 – 23:59" in card
    assert 'name="state" value="on"' in _form(card, "/quick/quiet-hours")


def test_battery_empty_hold_outranks_the_display_switch(tmp_path):
    """a battery-critical hold beats display_enabled=false in both the state wording and the
    cadence sentence, exactly as wake.effective_wake_interval_s() orders them"""
    card = _render(tmp_path, cfg={"display_enabled": False}, battery_critical=True)
    assert "Battery very low" in card and "Screen off" not in card
    hold = wake.effective_wake_interval_s({"display_enabled": False}, battery_critical=True)
    assert hold == device_config.BATTERY_CRITICAL_SLEEP_S
    assert "about every %d h" % (hold // 3600) in card or "about every %d min" % (hold // 60) in card


def test_without_a_check_in_there_is_no_next_update_but_the_switches_remain(tmp_path):
    """no check-in: no invented next-update line, the cadence sentence and both switches stay"""
    card = _render(tmp_path, last_checkin_ts=None)
    assert "Next update" not in card and "home-state__next" not in card
    assert "does not refresh continuously" in card
    assert "/quick/display" in card and "/quick/quiet-hours" in card


def test_french_status_header(tmp_path):
    """the header reads in French: hidden heading, state, cadence, switch labels and state words"""
    card = _render(tmp_path, lang="fr", cfg={"quiet_hours_enabled": True})
    for text in ("État du cadre", "Écran allumé", "Prochaine mise à jour ≈",
                 "Mise à jour environ toutes les 15 min",
                 "il ne se rafraîchit donc pas en continu", "Heures calmes", "Écran",
                 "Allumé", "Commandes du cadre"):
        assert text in card, text
    assert "Screen on" not in card and ">Quiet hours<" not in card


def _seed_battery(tmp_path, mv):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_device_health(
            conn, NOW, battery_mv=mv, fw_version="1.0.0", boot_reason="wake", rssi="-60")


@pytest.mark.parametrize("mv,level,state_word,health", [
    (4000, "ok", None, "ok"),
    (3600, "low", "Low", "warn"),
    (3381, "low", "Low", "ok"),
    (3500, "critical", "Very low", "error"),
])
def test_battery_block_level_word_and_accessible_name(tmp_path, mv, level, state_word, health):
    """the battery block is one named image ("Battery about N%"), shows the percentage, and for a
    low or critical level also says so in words so colour is never the only signal"""
    _seed_battery(tmp_path, mv)
    ctx = _ctx(tmp_path)
    ctx["health_state"]["battery_state"] = health
    percent = battery.battery_percent(mv)
    prefs.set_request_prefs(lang="en")
    card = _card(home_page.render(ctx))
    assert 'class="home-battery home-battery--%s"' % level in card
    assert 'role="img" aria-label="Battery about ≈ %d%%' % percent in card
    assert '<span class="home-battery__value">%d%%</span>' % percent in card
    assert 'class="home-battery__glyph"' in card
    assert ("home-battery__state" in card) == (state_word is not None)
    if state_word:
        assert ">%s</span>" % state_word in card and "%s" % state_word.lower() in card


def test_battery_block_without_a_reading_is_words_only(tmp_path):
    """no stored reading: a words-only block, no invented glyph or percentage"""
    card = _render(tmp_path)
    assert "home-battery--none" in card and "No reading yet" in card
    assert "home-battery__glyph" not in card and "role=\"img\"" not in card


def test_battery_block_in_french(tmp_path):
    """the battery name, label and level word read in French"""
    _seed_battery(tmp_path, 3381)
    ctx = _ctx(tmp_path)
    prefs.set_request_prefs(lang="fr")
    try:
        card = _card(home_page.render(ctx))
    finally:
        prefs.set_request_prefs(lang="en")
    assert 'aria-label="Batterie à environ ≈ 8%, faible"' in card
    assert ">Batterie</span>" in card and ">Faible</span>" in card


def test_cadence_is_one_short_line_with_the_reason_in_a_native_disclosure(tmp_path):
    """the cadence reads as a short muted summary; the reason sits in the same <details>, which
    needs no script, and neither the long sentence nor the interval clause remains"""
    card = _render(tmp_path)
    match = re.search(r"<details[^>]*home-state__cadence[^>]*><summary>(.*?)</summary><p>(.*?)</p>",
                      card, re.S)
    assert match is not None, "no cadence disclosure"
    assert match.group(1) == "Updates about every 15 min"
    assert "does not refresh continuously" in match.group(2)
    assert "To save its battery, the frame sleeps between updates and wakes" not in card
    card = _render(tmp_path, lang="fr")
    assert "<summary>Mise à jour environ toutes les 15 min</summary>" in card


def _late_ctx(tmp_path, minutes_since_checkin):
    """The default 900 s interval: the expected wake is 15 min after the check-in and the frame
    counts as late 30 min after that, long overdue past 45 min after it."""
    checkin = datetime.fromisoformat(NOW) - timedelta(minutes=minutes_since_checkin)
    return _render(tmp_path, last_checkin_ts=checkin.isoformat())


def test_a_short_delay_keeps_the_neutral_next_update_wording(tmp_path):
    """a few minutes past the expected wake is normal: the usual next-update line, green dot, no
    overdue wording and no Health link"""
    card = _late_ctx(tmp_path, 20)
    assert "Next update ≈" in card and "Update overdue" not in card
    assert "dot--ok" in card and "dot--warn" not in card and 'href="/health"' not in card


@pytest.mark.parametrize("lang,text", [
    ("en", "Update overdue · expected at <span"),
    ("fr", "Mise à jour en retard · attendue à <span"),
])
def test_overdue_frame_says_so_without_the_amber_dot_or_countdown(tmp_path, lang, text):
    """past the grace window the line names the expected time as overdue, drops the countdown,
    and stays neutral (green dot, no Health link) until the delay is long"""
    card = _render(
        tmp_path, lang=lang,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(minutes=50)).isoformat())
    assert text in card
    assert "Expected since" not in card and "Attendu depuis" not in card
    assert "data-relative-countdown" not in card
    assert "dot--ok" in card and "dot--warn" not in card and 'href="/health"' not in card


@pytest.mark.parametrize("lang,link", [("en", "See Health"), ("fr", "Voir la santé")])
def test_long_overdue_turns_the_dot_amber_and_links_to_health(tmp_path, lang, link):
    """more than three intervals past the expected wake: amber dot and one link to Health"""
    card = _render(
        tmp_path, lang=lang,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(minutes=90)).isoformat())
    assert "dot--warn" in card and "dot--ok" not in card
    assert re.findall(r'<a [^>]*href="/health"[^>]*>%s</a>' % link, card)


def test_overdue_date_appears_only_when_not_today(tmp_path):
    """an expected time on an earlier day carries its date, one on the same day does not"""
    same_day = _render(
        tmp_path, last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(minutes=50)).isoformat())
    assert re.search(r"expected at <span class=\"time-value\">\d\d:\d\d</span>", same_day)
    earlier = _render(
        tmp_path, last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(days=3)).isoformat())
    assert re.search(r"expected at <span class=\"time-value\">\d+ \w+\.? \d\d:\d\d</span>", earlier)


def test_a_quiet_hours_hold_is_never_overdue(tmp_path):
    """the quiet-hours hold keeps its own wording however long since the last check-in"""
    window = {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"}
    card = _render(
        tmp_path, cfg=window,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(days=2)).isoformat())
    assert "Update overdue" not in card and 'href="/health"' not in card and "dot--warn" not in card


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
        assert _checked(card, action) == ("true" if expected else "false")


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
