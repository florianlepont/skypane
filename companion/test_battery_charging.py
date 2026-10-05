"""The estimated "probably charging" status: the pure estimate over per-wake
battery readings (calibrated on the discharge run's real readings and the one
real unplug), and the pill it drives on Home's battery dial and Health's
Battery row, asserted on served markup in both languages."""
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

import companion.battery as battery
import companion.health_signals as health_signals
import companion.layout as layout
import companion.prefs as prefs
from companion.pages import health_page, home_page
from server import device_config, history_db

NOW = datetime(2026, 8, 27, 12, 0, 0, tzinfo=timezone.utc)
LIKELY = battery.CHARGE_LIKELY
NOT = battery.CHARGE_NOT_CHARGING
UNKNOWN = battery.CHARGE_UNKNOWN

RUN_LOG = Path(__file__).resolve().parents[1] / "hardware" / "logs" / "battery-run-server.log"

# Real consecutive readings (mV) from the discharge run that look most like
# a rise without being one: the panel refresh sags the voltage and the next
# wake recovers it.
REAL_SAG_RECOVER = [3500, 3490, 3450, 3490, 3468, 3484, 3478, 3470, 3490, 3488, 3406, 3504]
REAL_LARGEST_SHIFT = [3490, 3504, 3490, 3556, 3490, 3484, 3484, 3476, 3484, 3490, 3544, 3548]
REAL_CLOSEST_RAMP = [3506, 3528, 3500, 3496, 3540, 3518, 3500, 3562, 3570, 3554, 3544, 3528]
# The real unplug: four readings on USB, then the first on battery.
REAL_ON_USB = [4112, 4122, 4126, 4122]
REAL_AFTER_UNPLUG = 4038


def _rows(mvs, spacing_s=300, last_age_s=10, now=NOW):
    """Chronological `device_health`-shaped rows ending `last_age_s` before `now`."""
    last = now - timedelta(seconds=last_age_s)
    count = len(mvs)
    return [
        {"ts": (last - timedelta(seconds=spacing_s * (count - 1 - i))).isoformat(),
         "battery_mv": mv}
        for i, mv in enumerate(mvs)]


def _estimate(mvs, interval_s=300, **kwargs):
    spacing_s = kwargs.pop("spacing_s", interval_s)
    return battery.charging_estimate(
        _rows(mvs, spacing_s=spacing_s, **kwargs), NOW, interval_s)


def _real_discharge():
    readings = []
    for line in RUN_LOG.read_text().splitlines():
        match = re.search(r"X-Battery-Mv=(\d+)", line)
        if match:
            readings.append(int(match.group(1)))
    return readings[len(REAL_ON_USB):]


# --- the estimate -------------------------------------------------------


def test_steady_discharge_is_not_charging():
    """a steady slow fall is not charging"""
    assert _estimate([4000 - 3 * i for i in range(12)]) == NOT


def test_noisy_flat_readings_are_not_charging():
    """readings jittering around one level are not charging, whatever the seed"""
    for seed in range(50):
        rng = random.Random(seed)
        assert _estimate([3800 + rng.randint(-10, 10) for _ in range(12)]) == NOT


@pytest.mark.parametrize("series", [REAL_SAG_RECOVER, REAL_LARGEST_SHIFT, REAL_CLOSEST_RAMP])
def test_real_refresh_sag_and_recover_is_not_charging(series):
    """the real windows of the discharge run that come closest to a rise (a refresh sag followed
    by a ~100 mV recovery, the largest 3-vs-3 shift, the closest ramp) do not read as charging"""
    assert _estimate(series) == NOT
    assert _estimate(series[-6:]) == NOT


def test_the_real_discharge_run_never_reads_as_charging():
    """across every window of the 3248 real discharge readings, at the run's own cadence and at
    slower ones (every 2nd, 5th and 12th reading), the estimate never fires"""
    readings = _real_discharge()
    assert len(readings) > 3000
    for stride in (1, 2, 5, 12):
        for offset in range(stride):
            series = readings[offset::stride]
            for end in range(3, len(series) + 1):
                window = series[max(0, end - battery.CHARGE_RAMP_WINDOW_WAKES):end]
                assert not battery._charge_trend_says_charging(window), (stride, offset, end)


def test_a_clear_rising_ramp_is_charging():
    """a constant rise of 12 mV per wake reads as charging"""
    assert _estimate([3700 + 12 * i for i in range(12)]) == LIKELY


def test_a_plug_in_level_shift_is_detected_within_two_wakes():
    """an 84 mV step up (the size of the real unplug step, reversed) reads as charging on the
    second reading after it, not the first"""
    level = [3800] * 10
    assert _estimate(level + [3884]) == NOT
    assert _estimate(level + [3884, 3886]) == LIKELY
    assert _estimate(level + [3884, 3886, 3882, 3888]) == LIKELY


def test_a_plateau_at_the_usb_level_is_charging():
    """three readings at the level the frame showed on USB (4112-4126 mV) read as charging, even
    with no rise inside the window"""
    assert _estimate(REAL_ON_USB[:3]) == LIKELY
    assert _estimate([4100] * 12) == LIKELY
    assert _estimate([4088] * 12) == NOT


def test_the_real_unplug_ends_the_estimate_on_the_first_reading():
    """4122 mV on USB then 4038 mV after the cable came out: charging on the last USB reading,
    not charging from the first battery reading on, and it stays that way"""
    assert _estimate(REAL_ON_USB) == LIKELY
    after = REAL_ON_USB + [REAL_AFTER_UNPLUG]
    assert _estimate(after) == NOT
    for extra in range(1, 12):
        assert _estimate(after + [4040, 4036, 4020, 3998, 4020, 4018, 4010, 4010, 4024, 4020,
                                  4018][:extra]) == NOT


def test_unplugging_from_a_ramp_ends_the_estimate_on_the_first_reading():
    """a rising charge that stops with an 84 mV step down reads as not charging at once"""
    ramp = [3700 + 12 * i for i in range(12)]
    assert _estimate(ramp) == LIKELY
    assert _estimate(ramp + [ramp[-1] - 84]) == NOT


def test_a_stale_latest_reading_shows_nothing():
    """freshness is 2 wakes + 60 s: exactly at the limit still counts, one second past it, or a
    timestamp from the future, is unknown"""
    ramp = [3700 + 12 * i for i in range(12)]
    limit = 2 * 300 + 60
    assert _estimate(ramp, last_age_s=limit) == LIKELY
    assert _estimate(ramp, last_age_s=limit + 1) == UNKNOWN
    assert _estimate(ramp, last_age_s=-60) == LIKELY
    assert _estimate(ramp, last_age_s=-61) == UNKNOWN
    assert _estimate(ramp, last_age_s=86400) == UNKNOWN


def test_too_few_readings_is_unknown():
    """fewer than three usable readings, or no rows at all, is unknown"""
    assert _estimate([]) == UNKNOWN
    assert _estimate([4120]) == UNKNOWN
    assert _estimate([4120, 4122]) == UNKNOWN
    assert battery.charging_estimate(None, NOW, 300) == UNKNOWN
    assert _estimate([4120, 4122, 4124]) == LIKELY


def test_row_order_does_not_change_the_answer():
    """rows are sorted by time, never trusted: newest-first (as the history query returns them)
    and shuffled rows give the same answer, and a falling series reversed is not a rise"""
    rising = _rows([3700 + 12 * i for i in range(12)])
    falling = _rows([4000 - 12 * i for i in range(12)])
    shuffled = list(rising)
    random.Random(3).shuffle(shuffled)
    for rows in (rising, list(reversed(rising)), shuffled):
        assert battery.charging_estimate(rows, NOW, 300) == LIKELY
    for rows in (falling, list(reversed(falling))):
        assert battery.charging_estimate(rows, NOW, 300) == NOT


def test_bad_rows_are_ignored_and_never_raise():
    """rows that are not dicts, or carry a bad timestamp or a bool, text, NaN, infinite, zero or
    negative voltage are skipped; junk alone is unknown and a real ramp among junk still reads"""
    junk = [
        None, "x", 5, [], {}, {"ts": None, "battery_mv": 4100},
        {"ts": "not a time", "battery_mv": 4100}, {"ts": 17, "battery_mv": 4100},
        {"ts": NOW.isoformat(), "battery_mv": True},
        {"ts": NOW.isoformat(), "battery_mv": "4100"},
        {"ts": NOW.isoformat(), "battery_mv": float("nan")},
        {"ts": NOW.isoformat(), "battery_mv": float("inf")},
        {"ts": NOW.isoformat(), "battery_mv": 0},
        {"ts": NOW.isoformat(), "battery_mv": -4100},
        {"ts": NOW.isoformat(), "battery_mv": None},
    ]
    assert battery.charging_estimate(junk, NOW, 300) == UNKNOWN
    ramp = _rows([3700 + 12 * i for i in range(12)])
    assert battery.charging_estimate(junk + ramp, NOW, 300) == LIKELY


@pytest.mark.parametrize("bad_interval", [None, 0, -300, True, float("nan"), float("inf"), "300", 10 ** 9])
def test_a_bad_cadence_is_unknown(bad_interval):
    """freshness cannot be judged without a usable cadence, so the answer is unknown"""
    rows = _rows([3700 + 12 * i for i in range(12)])
    assert battery.charging_estimate(rows, NOW, bad_interval) == UNKNOWN


@pytest.mark.parametrize("bad_now", [None, "", "yesterday", 5, True])
def test_a_bad_now_is_unknown(bad_now):
    """an unusable `now` is unknown"""
    assert battery.charging_estimate(
        _rows([3700 + 12 * i for i in range(12)]), bad_now, 300) == UNKNOWN


def test_now_may_be_an_iso_string_or_a_naive_utc_datetime():
    """`now` and row timestamps parse as ISO strings with Z, offsets, or naive UTC"""
    ramp =_rows([3700 + 12 * i for i in range(12)])
    assert battery.charging_estimate(ramp, NOW.isoformat(), 300) == LIKELY
    assert battery.charging_estimate(ramp, NOW.replace(tzinfo=None), 300) == LIKELY
    assert battery.charging_estimate(
        ramp, NOW.astimezone(timezone(timedelta(hours=2))).isoformat(), 300) == LIKELY
    assert battery.charging_estimate(ramp, "2026-08-27T12:00:00Z", 300) == LIKELY


@pytest.mark.parametrize("interval_s", [60, 300, 3600])
def test_the_window_counts_wakes_so_every_cadence_reads_alike(interval_s):
    """at 60 s, 300 s and 3600 s: a plug-in step, a plateau and a falling battery read the same,
    a reading one wake late still counts and one four wakes late does not"""
    plug = [3800] * 10 + [3884, 3886]
    assert _estimate(plug, interval_s=interval_s) == LIKELY
    assert _estimate(REAL_ON_USB[:3], interval_s=interval_s) == LIKELY
    assert _estimate([4000 - 2 * i for i in range(12)], interval_s=interval_s) == NOT
    assert _estimate(plug, interval_s=interval_s, last_age_s=interval_s) == LIKELY
    assert _estimate(plug, interval_s=interval_s, last_age_s=4 * interval_s) == UNKNOWN


def test_a_gentle_ramp_is_only_seen_once_it_rises_fast_enough_per_wake():
    """the ramp rule needs about 7.5 mV per wake: 10 mV per wake is detected, 3 mV per wake is
    not (a documented limit of an estimate counted in wakes, not in seconds)"""
    assert _estimate([3800 + 10 * i for i in range(12)]) == LIKELY
    assert _estimate([3800 + 3 * i for i in range(12)]) == NOT


def test_the_observed_unplug_step_is_not_a_battery_warning():
    """the real 4122 -> 4038 mV unplug (84 mV) stays under the Battery row's 100 mV drop
    threshold, and so does every step of the real discharge run"""
    assert health_signals.battery_status(
        [{"battery_mv": REAL_AFTER_UNPLUG}, {"battery_mv": 4122}]) == "ok"
    series = REAL_ON_USB + [REAL_AFTER_UNPLUG] + _real_discharge()
    assert health_signals.battery_status(
        [{"battery_mv": mv} for mv in reversed(series)]) == "ok"


# --- the pill on the pages ----------------------------------------------

CHARGING_MVS = [3700 + 12 * i for i in range(12)]
DISCHARGING_MVS = [4000 - 3 * i for i in range(12)]


def _seed(state_dir, mvs, last_age_s=10, spacing_s=300, interval_s=300):
    """Readings ending `last_age_s` ago in real time (the pages read the clock),
    plus the device's wake interval."""
    now = datetime.now(timezone.utc)
    with history_db.open_db(str(state_dir)) as conn:
        for row in _rows(mvs, spacing_s=spacing_s, last_age_s=last_age_s, now=now):
            history_db.record_device_health(conn, row["ts"], battery_mv=row["battery_mv"])
    device_config.save_device_config(str(state_dir), wake_interval_s=interval_s)
    return now


def _home(state_dir, now, lang="en", cfg=None):
    ctx = {
        "state_dir": str(state_dir), "now": now.isoformat(), "gallery_entries": [],
        "last_checkin_ts": now.isoformat(),
        "device_config": {"wake_interval_s": 300, "display_enabled": True} if cfg is None else cfg,
        "battery_critical": False,
        "health_state": {"device_state": "ok", "pipeline_state": "ok", "battery_state": "ok"},
    }
    prefs.set_request_prefs(lang=lang)
    try:
        page = home_page.render(ctx)
    finally:
        prefs.set_request_prefs(lang="en")
    start = page.index('<section class="home-state ')
    return page[start:page.index("</section>", start)]


def _health(state_dir, now, lang="en"):
    prefs.set_request_prefs(lang=lang)
    try:
        return health_page.render({"state_dir": str(state_dir), "now": now.isoformat()})
    finally:
        prefs.set_request_prefs(lang="en")


def _battery_row_summary(page):
    match = re.search(r'<details[^>]*id="health-row-battery".*?</summary>', page, re.S)
    assert match, "no Battery row"
    return match.group(0)


WORDS = {
    "en": ("Probably charging",
           "The voltage is rising: the frame is probably plugged in"),
    "fr": ("Probablement en charge",
           "La tension monte : le cadre est probablement branché"),
}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_home_shows_the_hedged_pill_when_the_trend_says_charging(tmp_path, lang):
    """Home's battery dial carries the bolt pill with the hedged wording and its explanation, and
    the dial's accessible name says it too; the fact is never worded as "charging" outright"""
    now = _seed(tmp_path, CHARGING_MVS)
    card = _home(tmp_path, now, lang)
    words, title = WORDS[lang]
    assert re.search(
        r'<span class="charging-pill home-battery__charging" title="%s">'
        r'<svg[^>]*><use href="#icon-bolt"></use></svg>'
        r'<span class="charging-pill__text">%s</span></span>' % (re.escape(title), words), card)
    assert re.search(r'class="home-battery[^"]*" role="img" aria-label="[^"]*%s"' % words.lower(), card)
    assert "En charge<" not in card and ">Charging<" not in card


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_health_shows_the_hedged_pill_in_the_battery_row(tmp_path, lang):
    """Health's Battery row value carries the same pill, in the row summary, once"""
    now = _seed(tmp_path, CHARGING_MVS)
    page = _health(tmp_path, now, lang)
    words, title = WORDS[lang]
    summary = _battery_row_summary(page)
    assert summary.count("charging-pill ") == 1
    assert re.search(
        r'<span class="charging-pill health-row__charging" title="%s">'
        r'<svg[^>]*><use href="#icon-bolt"></use></svg>'
        r'<span class="charging-pill__text">%s</span></span>' % (re.escape(title), words), summary)
    assert page.count("charging-pill ") == 1


@pytest.mark.parametrize("case", ["discharging", "stale", "too-few", "no-cadence"])
def test_no_pill_unless_the_estimate_says_charging(tmp_path, monkeypatch, case):
    """a falling battery, a stale reading, fewer than three readings, and an undetermined wake
    cadence all render neither pill, on Home and on Health"""
    monkeypatch.delenv("SKYPANE_SLEEP_S", raising=False)
    if case == "discharging":
        now = _seed(tmp_path, DISCHARGING_MVS)
    elif case == "stale":
        now = _seed(tmp_path, CHARGING_MVS, last_age_s=2 * 300 + 61)
    elif case == "too-few":
        now = _seed(tmp_path, CHARGING_MVS[-2:])
    else:
        now = _seed(tmp_path, CHARGING_MVS)
        (tmp_path / device_config.DEVICE_CONFIG_FILENAME).unlink()
    assert "charging-pill" not in _home(
        tmp_path, now, cfg={"display_enabled": True} if case == "no-cadence" else None)
    page = _health(tmp_path, now)
    assert "charging-pill" not in page
    assert "Probably charging" not in page


def test_the_pill_follows_the_effective_cadence(tmp_path):
    """a reading 12 minutes old is stale at a 5 minute cadence but still fresh at an hourly one"""
    now = _seed(tmp_path, CHARGING_MVS, last_age_s=720, spacing_s=3600, interval_s=3600)
    assert "charging-pill" in _health(tmp_path, now)


def test_the_pill_vanishes_the_wake_after_an_unplug(tmp_path):
    """the page that follows the first on-battery reading shows no pill"""
    now = _seed(tmp_path, CHARGING_MVS + [CHARGING_MVS[-1] - 84])
    assert "charging-pill" not in _home(tmp_path, now)
    assert "charging-pill" not in _health(tmp_path, now)


def test_the_bolt_icon_is_in_the_shared_sprite_and_the_whitelist():
    """the bolt is a whitelisted icon id with its symbol in the sprite every page carries"""
    assert "icon-bolt" in layout.ICON_IDS
    assert '<symbol id="icon-bolt"' in layout.ICON_DEFS_HTML
    assert layout.icon_html("icon-bolt")
