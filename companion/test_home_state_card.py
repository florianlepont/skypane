"""The title block and the pills of Home: the wording of each state, the next
update, the Screen switch with its native POST, the Quiet hours opener, the
battery pill, the persisted effect and flash, and the precedence of the
battery-empty hold and the display switch. Everything is asserted on served
markup (a direct render for the state matrix, a real server for the POST round
trips)."""
import re
from datetime import datetime, timedelta

import pytest

import companion.draw as draw
import companion.layout as layout
import companion.prefs as prefs
import companion.wake as wake
from companion import auth
from companion.pages import home_page, home_state
from companion_app_server import http_request, login, with_csrf
from companion_markup import parse_html
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


def _render(tmp_path, lang="en", **kwargs):
    prefs.set_request_prefs(lang=lang)
    try:
        return home_page.render(_ctx(tmp_path, **kwargs))
    finally:
        prefs.set_request_prefs(lang="en")


def _tree(tmp_path, lang="en", **kwargs):
    return parse_html(_render(tmp_path, lang, **kwargs))


def _title(tree):
    return tree.select_one(".home-state__title").text().strip()


def _next_text(tree):
    found = tree.select(".home-state__next")
    return " ".join(found[0].text().split()) if found else None


def _screen_pill(tree):
    return tree.select_one(".home-pill--switch")


def _switch(tree):
    return tree.select_one('.home-pill--switch button[role="switch"]')


def test_default_state_reads_online_with_a_countdown_and_the_screen_switch_on(tmp_path):
    """the default state reads "Online" (the dot's word), the next update is a live countdown with
    no clock, and the Screen pill's native POST form posts the opposite state"""
    tree = _tree(tmp_path, cfg={"quiet_hours_enabled": True})
    assert _title(tree) == "Online"
    line = tree.select_one(".home-state__next")
    assert "Next refresh" in line.text() and line.select_one("time[data-relative-countdown]")
    assert not line.select(".time-value")
    switch = _switch(tree)
    assert switch.attrs["aria-checked"] == "true"
    form = tree.select_one(".home-pill--switch form")
    assert form.attrs["action"] == "/quick/display"
    assert form.select_one('input[name="state"]').attrs["value"] == "off"
    assert form.select_one('input[name="return_to"]').attrs["value"] == "/"


def test_the_screen_switch_is_named_and_described_and_asks_for_a_refresh(tmp_path):
    """aria-labelledby points at the visible label and aria-describedby at the On/Off word (kept
    for assistive technology only); the pill is a quick-switch region that refreshes the page's state
    regions after a confirmed flip"""
    tree = _tree(tmp_path)
    switch = _switch(tree)
    assert switch.attrs["aria-labelledby"] == "home-switch-screen-label"
    assert switch.attrs["aria-describedby"] == "home-switch-screen-state"
    assert tree.select_one("#home-switch-screen-label").text().strip() == "Screen"
    assert "visually-hidden" in tree.select_one("#home-switch-screen-state").attrs["class"]
    pill = _screen_pill(tree)
    assert "data-quick-region" in pill.attrs and "data-quick-refresh" in pill.attrs
    assert pill.select('button[role="switch"]') and len(pill.select("form")) == 1


def test_screen_off_state_flips_the_screen_switch(tmp_path):
    """display_enabled=false reads "Resting" (the dot's word), the screen switch is unchecked and
    posts state=on; the cadence sentence quotes the screen-off interval, not the configured one"""
    tree = _tree(tmp_path, cfg={"display_enabled": False})
    assert _title(tree) == "Resting"
    assert _switch(tree).attrs["aria-checked"] == "false"
    assert tree.select_one('.home-pill--switch input[name="state"]').attrs["value"] == "on"
    off_minutes = device_config.DISPLAY_OFF_SLEEP_S // 60
    assert "about every %d min" % off_minutes in tree.select_one(".info-tip__bubble").text()


def test_quiet_hours_state_names_the_end_time(tmp_path):
    """inside the quiet window the title reads "Resting" and the next-update line names the wake;
    with the schedule off the same clock reads "Online" """
    window = {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"}
    tree = _tree(tmp_path, cfg=window)
    assert _title(tree) == "Resting"
    assert "quiet hours" in _next_text(tree)
    assert tree.select_one(".home-state").attrs["class"].split()[1] == "home-state--off"
    window["quiet_hours_enabled"] = False
    assert _title(_tree(tmp_path, cfg=window)) == "Online"


@pytest.mark.parametrize("lang,name,text", [
    ("en", "Edit quiet hours (23:30 \u2013 06:00)", "23:30 \u2013 06:00"),
    ("fr", "Modifier les heures calmes (23:30 \u2013 06:00)", "23:30 \u2013 06:00"),
])
def test_quiet_hours_pill_is_a_link_to_the_dialog(tmp_path, lang, name, text):
    """the Quiet hours pill is a hash link that opens the dialog; its accessible name repeats the
    visible window; it holds no switch (the dialog's presets turn the schedule on and off)"""
    tree = _tree(tmp_path, lang=lang, cfg={
        "quiet_hours_enabled": True, "quiet_hours_start": "23:30", "quiet_hours_end": "06:00"})
    link = tree.select_one("a.home-pill--quiet")
    assert link.attrs["href"] == "#dlg-quiet-hours" and "data-modal-open" in link.attrs
    assert link.attrs["aria-label"] == name
    assert link.text().strip() == text and link.select("svg.icon")
    assert not tree.select('form[action="/quick/quiet-hours"]')
    assert tree.select("dialog#dlg-quiet-hours")


def test_quiet_hours_pill_says_off_while_the_schedule_is_off(tmp_path):
    """with the schedule off the pill reads "Quiet hours \u00b7 Off" and the window stays in its name"""
    tree = _tree(tmp_path, cfg={"quiet_hours_enabled": False})
    link = tree.select_one("a.home-pill--quiet")
    assert link.text().strip() == "Quiet hours \u00b7 Off"
    assert link.attrs["aria-label"] == "Edit quiet hours (Quiet hours \u00b7 Off)"


def test_battery_empty_hold_outranks_the_display_switch(tmp_path):
    """a battery-critical hold beats display_enabled=false in both the state wording and the
    cadence sentence, exactly as wake.effective_wake_interval_s() orders them"""
    tree = _tree(tmp_path, cfg={"display_enabled": False}, battery_critical=True)
    assert _title(tree) == "Low battery"
    hold = wake.effective_wake_interval_s({"display_enabled": False}, battery_critical=True)
    assert hold == device_config.BATTERY_CRITICAL_SLEEP_S
    bubble = tree.select_one(".info-tip__bubble").text()
    assert "about every %d h" % (hold // 3600) in bubble or "about every %d min" % (hold // 60) in bubble


def test_without_a_check_in_there_is_no_next_update_but_the_pills_remain(tmp_path):
    """no check-in: no invented next-update line and nothing to explain, every pill stays"""
    tree = _tree(tmp_path, last_checkin_ts=None)
    assert not tree.select(".home-state__next") and not tree.select(".info-tip")
    assert _switch(tree) is not None and tree.select_one("a.home-pill--quiet")
    assert tree.select_one("a.home-pill--place") and tree.select_one(".home-battery-pill")


def test_french_title_block_and_pills(tmp_path):
    """the block reads in French: hidden heading, state, next update, info tooltip, pill labels"""
    tree = _tree(tmp_path, lang="fr", cfg={"quiet_hours_enabled": True})
    assert tree.select_one("#home-frame-state").text().strip() == "État du cadre"
    assert _title(tree) == "En ligne"
    assert "Prochain rafraîchissement" in _next_text(tree)
    info = tree.select_one(".info-tip__button")
    assert info.attrs["aria-label"] == "À propos des mises à jour"
    assert "il se réveille environ toutes les 15 min" in tree.select_one(".info-tip__bubble").text()
    assert tree.select_one("#home-switch-screen-label").text().strip() == "Écran"
    assert tree.select_one("#home-frame-controls").text().strip() == "Commandes du cadre"


def _seed_battery(tmp_path, mv):
    with history_db.open_db(str(tmp_path)) as conn:
        history_db.record_device_health(
            conn, NOW, battery_mv=mv, fw_version="1.0.0", boot_reason="wake", rssi="-60")


@pytest.mark.parametrize("mv,level,word", [
    (4000, "ok", None), (3381, "low", "Low"), (3300, "low", "Low")])
def test_battery_pill_shows_the_charge_and_a_word_for_a_low_level(tmp_path, mv, level, word):
    """the battery pill is one static capsule: the label and the percentage, plus a level word for
    a low reading so colour is never the only signal"""
    _seed_battery(tmp_path, mv)
    pill = _tree(tmp_path).select_one(".home-battery-pill")
    assert "home-battery-pill--%s" % level in pill.attrs["class"]
    text = " ".join(pill.text().split())
    assert text.startswith("Battery ") and "%" in text
    assert ("\u00b7" in text) == (word is not None) and (word is None or word in text)
    assert pill.tag == "span" and "href" not in pill.attrs


def test_battery_pill_without_a_reading_says_so(tmp_path):
    """no stored reading: the pill says so, with no invented percentage"""
    pill = _tree(tmp_path).select_one(".home-battery-pill")
    assert " ".join(pill.text().split()) == "Battery \u00b7 No reading yet"
    assert "%" not in pill.text()


def test_battery_pill_in_french(tmp_path):
    """the label, the percentage and the level word read in French"""
    _seed_battery(tmp_path, 3381)
    pill = _tree(tmp_path, lang="fr").select_one(".home-battery-pill")
    assert " ".join(pill.text().split()) == "Batterie 8 % \u00b7 Faible"


@pytest.mark.parametrize("lang,label,sentence", [
    ("en", "About updates",
     "The frame sleeps between updates to save its battery; it wakes about every 15 min, "
     "so it does not refresh continuously."),
    ("fr", "À propos des mises à jour",
     "Le cadre dort entre deux mises à jour pour économiser sa batterie\u00a0: il se réveille "
     "environ toutes les 15 min, il ne se rafraîchit donc pas en continu."),
])
def test_cadence_is_an_info_button_at_the_end_of_the_next_update_line(tmp_path, lang, label, sentence):
    """the cadence lives behind a focusable "i" button, the last thing in the next-update sentence,
    whose aria-describedby names a role="tooltip" element holding the sentence with the interval"""
    tree = _tree(tmp_path, lang=lang)
    line = tree.select_one(".home-state__next")
    button = line.select_one(".info-tip__button")
    assert button.attrs["aria-label"] == label
    bubble = line.select_one('[role="tooltip"]')
    assert bubble.attrs["id"] == button.attrs["aria-describedby"]
    assert bubble.text().strip() == " ".join(sentence.split())
    sentence_node = line.select_one("span.home-state__sentence")
    assert [c.attrs.get("class") for c in sentence_node.children if not isinstance(c, str)][-1] == "info-tip"
    assert not tree.select("details")


def _late_tree(tmp_path, minutes_since_checkin, **kwargs):
    """The default 900 s interval: the expected wake is 15 min after the check-in and the frame
    counts as late 30 min after that, long overdue past 45 min after it."""
    checkin = datetime.fromisoformat(NOW) - timedelta(minutes=minutes_since_checkin)
    return _tree(tmp_path, last_checkin_ts=checkin.isoformat(), **kwargs)


def test_a_short_delay_keeps_the_neutral_next_update_wording(tmp_path):
    """a few minutes past the expected wake is normal: the usual next-update line, green dot, no
    overdue wording and no Health link"""
    tree = _late_tree(tmp_path, 20)
    assert "Next refresh" in _next_text(tree) and "overdue" not in _next_text(tree)
    assert tree.select_one(".home-state__dot.dot--ok") and not tree.select(".dot--warn")
    assert not tree.select('a[href="/health"]')


def _next_row(next_iso, hold_reason=None):
    return home_state.next_update_html(next_iso, 900, hold_reason, NOW, 900)


@pytest.mark.parametrize("lang,notice,line,word", [
    ("en", "Your frame has not checked in on time.", "Update overdue", "Overdue"),
    ("fr", "Votre cadre ne s\u2019est pas manifesté à l\u2019heure.", "Mise à jour en retard", "En retard"),
])
def test_overdue_frame_says_so_once_with_the_overdue_dot_and_no_countdown(
        tmp_path, lang, notice, line, word):
    """past the grace window the notification explains the delay and the title block keeps only
    the amber Overdue word: no second "Update overdue" line, no countdown, no Health link"""
    page = _render(
        tmp_path, lang=lang,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(minutes=50)).isoformat())
    tree = parse_html(page)
    assert page.count(notice) == 1 and line not in page
    assert not tree.select(".home-state__next")
    assert tree.select_one(".home-state__dot.dot--warn") and not tree.select(".dot--ok")
    assert tree.select_one(".home-state__dot").attrs["aria-label"] == word
    assert not tree.select('a[href="/health"]')


@pytest.mark.parametrize("lang,link", [("en", "See Health"), ("fr", "Voir la santé")])
def test_long_overdue_turns_the_dot_amber_and_links_nowhere(tmp_path, lang, link):
    """well past the expected wake: amber dot, and no link to Health (Health is the
    administrator's Console page)"""
    page = _render(
        tmp_path, lang=lang,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(minutes=90)).isoformat())
    tree = parse_html(page)
    assert tree.select_one(".home-state--warn .dot--warn") and not tree.select(".dot--ok")
    assert "/health" not in page and link not in page


def test_overdue_date_appears_only_when_not_today():
    """an expected time on an earlier day carries its date, one on the same day does not"""
    now = datetime.fromisoformat(NOW)
    same_day = _next_row((now - timedelta(minutes=40)).isoformat())
    assert re.search(r"expected at <span class=\"time-value\">\d\d:\d\d</span>", same_day)
    earlier = _next_row((now - timedelta(days=3)).isoformat())
    assert re.search(r"expected at <span class=\"time-value\">\d+ \w+\.? \d\d:\d\d</span>", earlier)


def test_a_quiet_hours_hold_is_never_overdue(tmp_path):
    """the quiet-hours hold keeps its own wording however long since the last check-in"""
    window = {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"}
    page = _render(
        tmp_path, cfg=window,
        last_checkin_ts=(datetime.fromisoformat(NOW) - timedelta(days=2)).isoformat())
    assert "Update overdue" not in page and 'href="/health"' not in page
    assert "dot--warn" not in page


def _lang_cookie(cookie, lang):
    return "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)


def test_post_round_trip_persists_flashes_and_returns_to_home(make_app_server):
    """posting the Screen pill's own fields persists the flip, redirects to Home with the matching
    flash key, Home then shows that flash text and the opposite button; no JS header is involved,
    so this is exactly the scripts-blocked path"""
    server = make_app_server(fake_providers=True)
    cookie = login(server)
    for state, flash, text, expected in (
            ("off", "display_off", "Screen switched off", False),
            ("on", "display_on", "Screen switched on", True)):
        body = with_csrf(
            cookie, {layout.QUICK_STATE_FIELD: state, "return_to": layout.HOME_ROUTE})
        status, headers, _ = http_request(
            server.base_url() + "/quick/display", method="POST", cookie=cookie, data=body)
        assert status == 303
        assert headers.get("Location") == "/?flash=%s" % flash
        assert device_config.load_device_config(server.state_dir)["display_enabled"] is expected
        status, _headers, page = http_request(
            server.base_url() + headers["Location"], cookie=cookie)
        html = page.decode("utf-8")
        assert status == 200 and text in html
        tree = parse_html(html)
        assert _switch(tree).attrs["aria-checked"] == ("true" if expected else "false")
        assert tree.select_one('.home-pill--switch input[name="state"]').attrs["value"] == (
            "off" if expected else "on")


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
    body = with_csrf(cookie, {"state": "toggle", "return_to": "/"})
    status, headers, _ = http_request(
        server.base_url() + "/quick/display", method="POST", cookie=cookie, data=body)
    assert status == 303 and headers.get("Location") == "/?flash=quick_failed"
    assert device_config.load_device_config(server.state_dir) == before


def _dash(svg, class_name):
    match = re.search(
        r'<circle class="%s"[^>]*stroke-dasharray="([\d.]+) ([\d.]+)"' % class_name, svg)
    return (float(match.group(1)), float(match.group(2))) if match else None


def test_arc_gauge_sweeps_three_quarters_and_fills_by_fraction():
    """the dial's track covers 270 of 360 degrees with its gap centred at the bottom, the value
    ink (dash plus the two half round caps) is the reading's share of the visible track, an
    empty reading draws no value stroke, and every input is clamped rather than raised"""
    full_track, circumference = _dash(draw.arc_gauge(0.5, 132), draw.DRAWING_ARC_TRACK_CLASS)
    assert abs(full_track / circumference - 0.75) < 1e-3
    assert 'transform="rotate(135.00 66.00 66.00)"' in draw.arc_gauge(0.5, 132)
    stroke = float(re.search(r'stroke-width="([\d.]+)"', draw.arc_gauge(0.5, 132)).group(1))
    for fraction in (0.2, 0.5, 0.9, 1.0):
        value, _ = _dash(draw.arc_gauge(fraction, 132), draw.DRAWING_ARC_VALUE_CLASS)
        assert abs((value + stroke) / (full_track + stroke) - fraction) < 1e-3, fraction
    assert _dash(draw.arc_gauge(0.0, 132), draw.DRAWING_ARC_VALUE_CLASS) is None
    assert draw.arc_gauge(1.7, 132) == draw.arc_gauge(1.0, 132)
    assert draw.arc_gauge("x", 132) == draw.arc_gauge(0.0, 132)
    assert 'aria-hidden="true"' in draw.arc_gauge(0.5, 132)
    assert "style" not in draw.arc_gauge(0.5, "big")


@pytest.mark.parametrize("lang,title,cfg,critical,tone", [
    ("en", "Resting", {"display_enabled": False}, False, "off"),
    ("fr", "Au repos", {"display_enabled": False}, False, "off"),
    ("en", "Low battery", {}, True, "warn"),
    ("fr", "Batterie faible", {}, True, "warn"),
])
def test_held_states_read_the_dots_word_and_tint_the_block(tmp_path, lang, title, cfg, critical, tone):
    """a held state shows the dot's own word beside the dot and no sentence under it, and tints the
    block neutral (screen off) or amber (battery hold)"""
    tree = _tree(tmp_path, lang=lang, cfg=cfg, battery_critical=critical)
    assert _title(tree) == title
    assert "home-state--%s" % tone in tree.select_one(".home-state").attrs["class"]
    assert not tree.select(".home-state__detail")


def test_the_block_label_is_a_hidden_heading_and_the_next_line_has_an_icon(tmp_path):
    """the "Frame state" label is the block's visually hidden h2, and the next-update line leads
    with a decorative clock (a warning sign once overdue)"""
    tree = _tree(tmp_path)
    assert tree.select_one("h2.visually-hidden#home-frame-state").text().strip() == "Frame state"
    assert tree.select_one(".home-state__next svg use").attrs["href"] == "#icon-nav-history"
    assert "#icon-warning" in _next_row(
        (datetime.fromisoformat(NOW) - timedelta(minutes=40)).isoformat())


def test_served_home_page_carries_no_inline_style(make_app_server):
    """the Home page served to a signed-in reader has no style attribute anywhere (the CSP
    forbids inline styles) and no battery dial, only the battery pill"""
    def seed(state_dir):
        _seed_battery(state_dir, 3700)
    server = make_app_server(seed=seed, fake_providers=True)
    cookie = login(server)
    status, _headers, page = http_request(server.base_url() + "/", cookie=cookie)
    html = page.decode("utf-8")
    assert status == 200 and 'class="%s"' % draw.DRAWING_ARC_VALUE_CLASS not in html
    assert "home-battery__" not in html and "home-battery-pill" in html
    assert not re.search(r"<[^>]+\sstyle=", html)
