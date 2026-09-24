#!/usr/bin/env python3
"""Contract tests for server/device_config.py (the theme + tracked-runway
registry and its validated, atomic JSON side-file) and server/history_db.py
(the SQLite history store behind CFG-03's health trend, CFG-06's flight
log, CFG-08's resolution statistics, and the Caddy access-log battery
tailer), plus server/wake.py's battery-critical-aware wake scheduling
(quick task 260923-fr4), which shares this harness because history_db.py's
own module docstring forbids it from importing device_config, so the
classifier and the battery-critical mirror both live beside
device_staleness_thresholds() in wake.py instead.
"""
import json
import os
import re
import sqlite3
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.device_config as device_config  # noqa: E402
import server.panel_format as panel_format  # noqa: E402
import server.history_db as history_db  # noqa: E402
import server.wake as wake  # noqa: E402

# Three consecutive device_health check-ins 30 minutes apart, shared by the
# check_in_gaps() tests below (CFG-43).
_GAP_T0 = "2026-09-02T10:00:00+00:00"
_GAP_T1 = "2026-09-02T10:30:00+00:00"
_GAP_T2 = "2026-09-02T11:00:00+00:00"


def _caddy_log_line(uri, ts, headers):
    """One Caddy JSON access-log line, per 06-RESEARCH.md Pattern 6's
    assumed shape: the request's header map nests under `request.headers`,
    each value a list of strings.
    """
    entry = {
        "ts": ts,
        "logger": "http.log.access",
        "msg": "handled request",
        "request": {"method": "GET", "uri": uri, "headers": headers},
        "status": 200,
    }
    return json.dumps(entry)


def test_missing_state_dir_yields_defaults(tmp_path):
    """load_device_config() on a missing state directory returns the documented defaults"""
    tmpdir = tmp_path
    missing = os.path.join(tmpdir, "does-not-exist")
    config = device_config.load_device_config(missing)
    if config != {"theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
        pytest.fail("expected defaults, got %r" % (config,))


def test_malformed_file_yields_defaults(tmp_path):
    """load_device_config() on a JSON array, a truncated document, or a non-dict returns defaults instead of raising"""
    tmpdir = tmp_path
    for bad_content in ('["not", "a", "dict"]', "{truncated", "null"):
        path = device_config.device_config_path(tmpdir)
        with open(path, "w") as fh:
            fh.write(bad_content)
        config = device_config.load_device_config(tmpdir)
        if config != {"theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
            pytest.fail("content %r produced %r, expected defaults" % (bad_content, config))


def test_hostile_values_yield_defaults(tmp_path):
    """load_device_config() replaces an unrecognised theme/runway value with the default rather than passing it through"""
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    with open(path, "w") as fh:
        fh.write('{"theme": "../../etc/passwd", "tracked_runway": 7}')
    config = device_config.load_device_config(tmpdir)
    if config != {"theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
        pytest.fail("hostile input produced %r, expected defaults for both keys" % (config,))


def test_save_then_load_round_trips(tmp_path):
    """save_device_config() followed by load_device_config() round-trips the saved theme and tracked_runway"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="02-20")
    config = device_config.load_device_config(tmpdir)
    if config != {"theme": "black", "theme_arriving": None, "tracked_runway": "02-20", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
        pytest.fail("round-trip produced %r" % (config,))


def test_unknown_theme_rejected_without_touching_file(tmp_path):
    """save_device_config() with an unknown theme id raises ValueError and leaves the state directory file-free"""
    tmpdir = tmp_path
    raised = False
    try:
        device_config.save_device_config(tmpdir, theme="nope")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config() with an unknown theme did not raise ValueError")
    path = device_config.device_config_path(tmpdir)
    if os.path.exists(path):
        pytest.fail("a rejected save left a device_config.json file behind")
    if os.path.exists(path + ".tmp"):
        pytest.fail("a rejected save left a .tmp file behind")


def test_no_tmp_survives_a_successful_save(tmp_path):
    """no .tmp file remains in the state directory after a successful save"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3")
    if os.path.exists(device_config.device_config_path(tmpdir) + ".tmp"):
        pytest.fail("a .tmp file survived a successful save")


def test_hostile_hand_edit_after_a_real_save_still_yields_defaults(tmp_path):
    """a legitimately saved config, hand-edited on disk to hostile values, still yields defaults from load_device_config()"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="02-20")
    path = device_config.device_config_path(tmpdir)
    with open(path, "w") as fh:
        fh.write('{"theme": "black/../x", "tracked_runway": "3; DROP TABLE"}')
    config = device_config.load_device_config(tmpdir)
    if config != {"theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
        pytest.fail("hand-edited hostile file produced %r, expected defaults for both keys" % (config,))


def test_normalise_led_enabled_only_accepts_real_bools():
    """normalise_led_enabled() returns the value only for real bools and degrades a string, int 0, int 1, None, and a list to DEFAULT_LED_ENABLED"""
    for hostile in ("true", 0, 1, None, ["x"]):
        got = device_config.normalise_led_enabled(hostile)
        if got is not device_config.DEFAULT_LED_ENABLED:
            pytest.fail("normalise_led_enabled(%r) returned %r, expected DEFAULT_LED_ENABLED" % (hostile, got))
    if device_config.normalise_led_enabled(True) is not True:
        pytest.fail("normalise_led_enabled(True) did not return True")
    if device_config.normalise_led_enabled(False) is not False:
        pytest.fail("normalise_led_enabled(False) did not return False")


def test_save_led_enabled_false_round_trips(tmp_path):
    """save_device_config(led_enabled=False) round-trips through load_device_config() as False, with theme/tracked_runway still at their defaults"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, led_enabled=False)
    config = device_config.load_device_config(tmpdir)
    if config != {"theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": False, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame", "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}}:
        pytest.fail("round-trip produced %r" % (config,))


def test_hand_written_hostile_led_enabled_yields_default(tmp_path):
    """a hand-written device_config.json whose led_enabled is a hostile string yields DEFAULT_LED_ENABLED from load_device_config()"""
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    with open(path, "w") as fh:
        fh.write('{"led_enabled": "off"}')
    config = device_config.load_device_config(tmpdir)
    if config["led_enabled"] is not True:
        pytest.fail("hostile string led_enabled produced %r, expected DEFAULT_LED_ENABLED" % (config["led_enabled"],))


def test_save_led_enabled_off_rejected_without_touching_file(tmp_path):
    """save_device_config(led_enabled='off') raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3", led_enabled=True)
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    raised = False
    try:
        device_config.save_device_config(tmpdir, led_enabled="off")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config(led_enabled='off') did not raise ValueError")
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("a rejected led_enabled write changed a pre-existing file's bytes")


def test_theme_only_save_carries_led_enabled_false_forward(tmp_path):
    """a subsequent theme-only save_device_config(theme='black') carries a previously-saved led_enabled=False forward unchanged"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, led_enabled=False)
    device_config.save_device_config(tmpdir, theme="black")
    config = device_config.load_device_config(tmpdir)
    if config["led_enabled"] is not False:
        pytest.fail("a theme-only save did not carry a previously-saved led_enabled=False forward, got %r" % (config["led_enabled"],))


def test_theme_registry_shape_is_correct():
    """every THEMES entry carries exactly its contract keys (6 for non-band, 8 for band), real panel_format.IDX_* index values, a non-empty label, a bool dithered flag, a regular/bold weight, and (band entries only) a real band_index plus a bool band_dithered"""
    valid_indices = {
        panel_format.IDX_BLACK,
        panel_format.IDX_WHITE,
        panel_format.IDX_YELLOW,
        panel_format.IDX_RED,
        panel_format.IDX_BLUE,
        panel_format.IDX_GREEN,
    }
    expected_keys = {"departing_index", "arriving_index", "ink_index", "label", "dithered", "weight"}
    band_expected_keys = expected_keys | {"band_index", "band_dithered"}
    for theme_id, entry in device_config.THEMES.items():
        is_band = device_config.theme_is_band(theme_id)
        want_keys = band_expected_keys if is_band else expected_keys
        if set(entry) != want_keys:
            pytest.fail("theme %r has keys %r, expected exactly %r" % (theme_id, set(entry), want_keys))
        for key in ("departing_index", "arriving_index", "ink_index"):
            if entry[key] not in valid_indices:
                pytest.fail("theme %r key %r has value %r, not a real panel_format.IDX_* index" % (theme_id, key, entry[key]))
        if not isinstance(entry["label"], str) or not entry["label"]:
            pytest.fail("theme %r label %r is not a non-empty string" % (theme_id, entry["label"]))
        if not isinstance(entry["dithered"], bool):
            pytest.fail("theme %r dithered %r is not a bool" % (theme_id, entry["dithered"]))
        if entry["weight"] not in ("regular", "bold"):
            pytest.fail("theme %r weight %r is not 'regular' or 'bold'" % (theme_id, entry["weight"]))
        if is_band:
            if entry["band_index"] not in valid_indices:
                pytest.fail("band theme %r band_index %r is not a real panel_format.IDX_* index" % (theme_id, entry["band_index"]))
            if not isinstance(entry["band_dithered"], bool):
                pytest.fail("band theme %r band_dithered %r is not a bool" % (theme_id, entry["band_dithered"]))


def test_every_theme_is_single_colour():
    """every registered theme is single-colour (departing_index == arriving_index); the retired two-tone 'sky' theme is gone"""
    # Phase 8 08-06 on-glass session: "sky" (the old two-tone
    # Blue-departing/Green-arriving pairing) was retired outright -
    # every registered theme is now single-colour, with no two-tone
    # exception left to carve out.
    for theme_id, entry in device_config.THEMES.items():
        if entry["departing_index"] != entry["arriving_index"]:
            pytest.fail("theme %r is not single-colour: departing_index=%r arriving_index=%r" % (
                theme_id, entry["departing_index"], entry["arriving_index"],
            ))
    if "sky" in device_config.THEMES:
        pytest.fail("the retired 'sky' two-tone theme is still present in THEMES")


def test_ink_contrast_pairing_is_correct():
    """every one of the 18 registered themes carries the exact background/ink pairing expected, pinned as an explicit id-to-(background,ink) mapping"""
    # Every entry's ink is whichever of Black/White contrasts with its
    # own background - black text on the lighter inks (White/Yellow/
    # Yellow Light), white text everywhere else (08-06: the same
    # contrast logic Phase 8 already established for White/Black/
    # Yellow/Red, now applied uniformly to all 11 registered themes).
    expected = {
        "white": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        "black": (panel_format.IDX_BLACK, panel_format.IDX_WHITE),
        "grey": (panel_format.IDX_BLACK, panel_format.IDX_WHITE),
        "yellow": (panel_format.IDX_YELLOW, panel_format.IDX_BLACK),
        "yellow_light": (panel_format.IDX_YELLOW, panel_format.IDX_BLACK),
        "red": (panel_format.IDX_RED, panel_format.IDX_WHITE),
        "red_light": (panel_format.IDX_RED, panel_format.IDX_WHITE),
        "green": (panel_format.IDX_GREEN, panel_format.IDX_WHITE),
        "green_light": (panel_format.IDX_GREEN, panel_format.IDX_WHITE),
        "blue": (panel_format.IDX_BLUE, panel_format.IDX_WHITE),
        "blue_light": (panel_format.IDX_BLUE, panel_format.IDX_WHITE),
        # Phase 9 (09-01): every band theme keeps the White base
        # canvas/Black ink pairing - the band's own colour is a
        # separate band_index field, never a base-canvas property
        # (spike 003 round 15). NOTE: this uniform White-base/Black-ink
        # claim covers only these 5 Phase 9 band ids - it stops being
        # true of the band family AS A WHOLE the moment the two
        # tone-on-tone `_field` ids below land (quick task 260905-e04).
        "band_blue": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        "band_blue_light": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        "band_green_light": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        "band_red": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        "band_black": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
        # Quick task 260905-e04: these two copy their background/ink
        # pairing from their `_light` tinted-field sibling instead
        # (blue_light/red_light), not from the band family above - see
        # THEMES' own module comment for why (ink_index never colours
        # in-band text).
        "band_blue_field": (panel_format.IDX_BLUE, panel_format.IDX_WHITE),
        "band_red_field": (panel_format.IDX_RED, panel_format.IDX_WHITE),
    }
    if set(expected) != set(device_config.THEMES):
        pytest.fail("expected mapping covers %r, THEMES actually has %r" % (set(expected), set(device_config.THEMES)))
    for theme_id, (bg, ink) in expected.items():
        entry = device_config.THEMES[theme_id]
        if entry["departing_index"] != bg or entry["ink_index"] != ink:
            pytest.fail("theme %r expected background %r / ink %r, got background %r / ink %r" % (
                theme_id, bg, ink, entry["departing_index"], entry["ink_index"],
            ))


def test_dithered_and_weight_contract_is_correct():
    """every registered theme's base-canvas dithered/weight pair matches the on-glass-confirmed values, including Yellow Light's Regular exception, the 5 White-base band themes, and the 2 tinted-field band themes' blue_light/red_light-derived values"""
    # Phase 8 08-06 on-glass session: every "pure" (undithered) colour
    # confirmed Regular; every dithered colour confirmed Bold EXCEPT
    # Yellow Light, the one exception (its dithered field is light/
    # high-luminance enough that Regular stayed legible and was
    # preferred) - see THEMES' own module comment for the full
    # rationale. Pinned explicitly so a future reader cannot assume a
    # blanket "dithered implies Bold" rule from the majority case.
    expected = {
        "white": (False, "regular"),
        "black": (False, "regular"),
        "grey": (True, "bold"),
        "yellow": (False, "regular"),
        "yellow_light": (True, "regular"),
        "red": (False, "regular"),
        "red_light": (True, "bold"),
        "green": (False, "regular"),
        "green_light": (True, "bold"),
        "blue": (False, "regular"),
        "blue_light": (True, "bold"),
        # Phase 9 (09-01): every band theme's own base-canvas
        # dithered/weight pair matches "white"'s exactly (undithered,
        # Regular) - the band's own dithered treatment is a separate
        # band_dithered field, checked by the new accessor checks below.
        # NOTE: this uniform undithered/Regular claim covers only these
        # 5 Phase 9 band ids - the two tone-on-tone `_field` ids below
        # (quick task 260905-e04) instead copy blue_light/red_light's
        # dithered=True/weight="bold" base-canvas pair, since dithering
        # is what produces their tinted field.
        "band_blue": (False, "regular"),
        "band_blue_light": (False, "regular"),
        "band_green_light": (False, "regular"),
        "band_red": (False, "regular"),
        "band_black": (False, "regular"),
        "band_blue_field": (True, "bold"),
        "band_red_field": (True, "bold"),
    }
    if set(expected) != set(device_config.THEMES):
        pytest.fail("expected mapping covers %r, THEMES actually has %r" % (set(expected), set(device_config.THEMES)))
    for theme_id, (dithered, weight) in expected.items():
        entry = device_config.THEMES[theme_id]
        if entry["dithered"] != dithered or entry["weight"] != weight:
            pytest.fail("theme %r expected dithered=%r weight=%r, got dithered=%r weight=%r" % (
                theme_id, dithered, weight, entry["dithered"], entry["weight"],
            ))


def test_default_theme_and_labels_are_correct():
    """DEFAULT_THEME_ID is 'white' and a THEMES member; theme_label() returns the exact plain label for all 18 ids"""
    if device_config.DEFAULT_THEME_ID != "white":
        pytest.fail("DEFAULT_THEME_ID is %r, expected 'white'" % (device_config.DEFAULT_THEME_ID,))
    if device_config.DEFAULT_THEME_ID not in device_config.THEMES:
        pytest.fail("DEFAULT_THEME_ID %r is not a member of THEMES" % (device_config.DEFAULT_THEME_ID,))
    expected_labels = {
        "white": "White", "black": "Black", "grey": "Grey",
        "yellow": "Yellow", "yellow_light": "Yellow Light",
        "red": "Red", "red_light": "Red Light",
        "green": "Green", "green_light": "Green Light",
        "blue": "Blue", "blue_light": "Blue Light",
        "band_blue": "Band Blue", "band_blue_light": "Band Blue Light",
        "band_green_light": "Band Green Light", "band_red": "Band Red",
        "band_black": "Band Black",
        "band_blue_field": "Band Blue Field", "band_red_field": "Band Red Field",
    }
    if set(expected_labels) != set(device_config.THEMES):
        pytest.fail("expected label mapping covers %r, THEMES actually has %r" % (set(expected_labels), set(device_config.THEMES)))
    for theme_id, label in expected_labels.items():
        got = device_config.theme_label(theme_id)
        if got != label:
            pytest.fail("theme_label(%r) returned %r, expected %r" % (theme_id, got, label))


def test_theme_is_band_matches_registry_band_ids():
    """theme_is_band() returns True for exactly the ids device_config.THEMES itself marks as band entries (band_index present) and False for every other registered id"""
    expected_band_ids = {tid for tid, entry in device_config.THEMES.items() if "band_index" in entry}
    for theme_id in device_config.THEMES:
        got = device_config.theme_is_band(theme_id)
        want = theme_id in expected_band_ids
        if got != want:
            pytest.fail("theme_is_band(%r) returned %r, expected %r" % (theme_id, got, want))
    if expected_band_ids != {
        "band_blue", "band_blue_light", "band_green_light", "band_red", "band_black",
        "band_blue_field", "band_red_field",
    }:
        pytest.fail("registry's own band ids are %r, expected the 7 band ids" % (expected_band_ids,))


def test_theme_band_index_matches_registry_or_none():
    """theme_band_index() returns THEMES's own band_index for every band id (the exact spike-confirmed IDX_* per colour) and None for every non-band id"""
    for theme_id, entry in device_config.THEMES.items():
        got = device_config.theme_band_index(theme_id)
        want = entry.get("band_index")
        if got != want:
            pytest.fail("theme_band_index(%r) returned %r, expected %r" % (theme_id, got, want))
    expected = {
        "band_blue": panel_format.IDX_BLUE,
        "band_blue_light": panel_format.IDX_BLUE,
        "band_green_light": panel_format.IDX_GREEN,
        "band_red": panel_format.IDX_RED,
        "band_black": panel_format.IDX_BLACK,
        "band_blue_field": panel_format.IDX_BLUE,
        "band_red_field": panel_format.IDX_RED,
    }
    for theme_id, idx in expected.items():
        if device_config.theme_band_index(theme_id) != idx:
            pytest.fail("theme_band_index(%r) expected %r, got %r" % (theme_id, idx, device_config.theme_band_index(theme_id)))


def test_theme_band_dithered_matches_registry_or_false():
    """theme_band_dithered() returns THEMES's own band_dithered for every band id and False for every non-band id"""
    for theme_id, entry in device_config.THEMES.items():
        got = device_config.theme_band_dithered(theme_id)
        want = entry.get("band_dithered", False)
        if got != want:
            pytest.fail("theme_band_dithered(%r) returned %r, expected %r" % (theme_id, got, want))
    expected = {
        "band_blue": False,
        "band_blue_light": True,
        "band_green_light": True,
        "band_red": False,
        "band_black": False,
        "band_blue_field": False,
        "band_red_field": False,
    }
    for theme_id, dithered in expected.items():
        if device_config.theme_band_dithered(theme_id) != dithered:
            pytest.fail("theme_band_dithered(%r) expected %r, got %r" % (theme_id, dithered, device_config.theme_band_dithered(theme_id)))


def test_tinted_field_band_themes_are_tone_on_tone():
    """band_blue_field/band_red_field are genuinely tone-on-tone (band_index equals departing_index equals arriving_index), dithered=True/band_dithered=False, and their base-canvas quadruple matches their tinted-field sibling's (blue_light/red_light) own registry row, read live rather than hardcoded"""
    # Quick task 260905-e04: pins the actual tone-on-tone contract that
    # makes band_blue_field/band_red_field what they are - no existing
    # check above captures it. Deliberately derives each sibling's
    # expected base-canvas values by READING THEMES["blue_light"]/
    # THEMES["red_light"] rather than hardcoding them, so that if either
    # sibling is ever re-tuned on glass, this check fails loudly instead
    # of silently drifting - forcing a deliberate decision about whether
    # the tinted-field band themes follow suit.
    field_to_sibling = {"band_blue_field": "blue_light", "band_red_field": "red_light"}
    for field_id, sibling_id in field_to_sibling.items():
        entry = device_config.THEMES[field_id]
        sibling = device_config.THEMES[sibling_id]
        if entry["band_index"] != entry["departing_index"] or entry["band_index"] != entry["arriving_index"]:
            pytest.fail("theme %r is not tone-on-tone: band_index=%r departing_index=%r arriving_index=%r" % (
                field_id, entry["band_index"], entry["departing_index"], entry["arriving_index"],
            ))
        if entry["dithered"] is not True:
            pytest.fail("theme %r expected dithered=True, got %r" % (field_id, entry["dithered"]))
        if entry["band_dithered"] is not False:
            pytest.fail("theme %r expected band_dithered=False, got %r" % (field_id, entry["band_dithered"]))
        for key in ("departing_index", "arriving_index", "ink_index", "dithered", "weight"):
            if entry[key] != sibling[key]:
                pytest.fail("theme %r key %r is %r, expected to match its tinted-field sibling %r's own %r" % (
                    field_id, key, entry[key], sibling_id, sibling[key],
                ))


def test_hostile_quiet_hours_values_yield_defaults(tmp_path):
    """load_device_config() replaces hostile quiet_hours_enabled/quiet_hours_start/quiet_hours_end values with their documented defaults"""
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    with open(path, "w") as fh:
        fh.write('{"quiet_hours_enabled": "yes", "quiet_hours_start": "25:99", "quiet_hours_end": 7}')
    config = device_config.load_device_config(tmpdir)
    expected = {
        "quiet_hours_enabled": device_config.DEFAULT_QUIET_HOURS_ENABLED,
        "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
    }
    for key, want in expected.items():
        if config[key] != want:
            pytest.fail("hostile quiet-hours input produced %r=%r, expected %r" % (key, config[key], want))


def test_save_quiet_hours_round_trips(tmp_path):
    """save_device_config(quiet_hours_enabled=True, quiet_hours_start='22:30', quiet_hours_end='06:15') round-trips through load_device_config() with theme/tracked_runway/led_enabled still at their prior (default) values"""
    tmpdir = tmp_path
    device_config.save_device_config(
        tmpdir, quiet_hours_enabled=True, quiet_hours_start="22:30", quiet_hours_end="06:15")
    config = device_config.load_device_config(tmpdir)
    if config != {
        "theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True,
        "quiet_hours_enabled": True, "quiet_hours_start": "22:30", "quiet_hours_end": "06:15",
        "wake_interval_s": None, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame",
        "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"},
    }:
        pytest.fail("round-trip produced %r" % (config,))


def test_save_quiet_hours_start_invalid_rejected_without_touching_file(tmp_path):
    """save_device_config(quiet_hours_start='24:00') raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3")
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    raised = False
    try:
        device_config.save_device_config(tmpdir, quiet_hours_start="24:00")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config(quiet_hours_start='24:00') did not raise ValueError")
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("a rejected quiet_hours_start write changed a pre-existing file's bytes")


def test_save_quiet_hours_enabled_non_bool_rejected(tmp_path):
    """save_device_config(quiet_hours_enabled='on') raises ValueError"""
    tmpdir = tmp_path
    raised = False
    try:
        device_config.save_device_config(tmpdir, quiet_hours_enabled="on")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config(quiet_hours_enabled='on') did not raise ValueError")


def test_normalise_quiet_hours_time_rejects_every_hostile_shape():
    """normalise_quiet_hours_time() rejects an unpadded hour, an out-of-range minute, midnight-as-24:00, an empty string, None, an int, and a trailing newline - returning the supplied default for each"""
    default = "23:00"
    for hostile in ("7:00", "07:60", "24:00", "", None, 7, "07:00\n"):
        got = device_config.normalise_quiet_hours_time(hostile, default)
        if got != default:
            pytest.fail("normalise_quiet_hours_time(%r, %r) returned %r, expected the supplied default" % (hostile, default, got))


def test_wrap_midnight_window_returns_verified_dst_values():
    """seconds_until_quiet_hours_end() returns the verified wrap-midnight/DST anchors: 28000 mid-window, None just past end, 23400 across spring-forward (1h less than naive), 30600 across autumn fall-back (1h more than naive)"""
    from datetime import datetime, timezone

    cases = [
        (1700000000.0, "23:00", "07:00", 28000),  # 2023-11-14T23:13:20+01:00 Paris
        (1700028800.0, "23:00", "07:00", None),  # 07:13:20 Paris, just past end
        (1774737000.0, "23:00", "07:00", 23400),  # spring-forward night
        (1792877400.0, "23:00", "07:00", 30600),  # autumn fall-back night
    ]
    for epoch, start_hm, end_hm, expected in cases:
        now_utc = datetime.fromtimestamp(epoch, timezone.utc)
        got = device_config.seconds_until_quiet_hours_end(now_utc, start_hm, end_hm)
        if got != expected:
            pytest.fail("seconds_until_quiet_hours_end(epoch=%r, %r, %r) returned %r, expected %r" % (
                epoch, start_hm, end_hm, got, expected,
            ))


def test_same_day_window_and_zero_width_window():
    """seconds_until_quiet_hours_end() handles a same-day (non-wrapping) window correctly and returns None for a zero-width start_hm == end_hm window"""
    from datetime import datetime, timezone

    # 2023-11-14 13:30/12:30 Paris (CET, UTC+1) for a same-day 13:00-14:00 window.
    at_1330 = datetime(2023, 11, 14, 12, 30, 0, tzinfo=timezone.utc)
    at_1230 = datetime(2023, 11, 14, 11, 30, 0, tzinfo=timezone.utc)
    got_active = device_config.seconds_until_quiet_hours_end(at_1330, "13:00", "14:00")
    if got_active != 1800:
        pytest.fail("same-day window at 13:30 Paris returned %r, expected 1800" % (got_active,))
    got_inactive = device_config.seconds_until_quiet_hours_end(at_1230, "13:00", "14:00")
    if got_inactive is not None:
        pytest.fail("same-day window at 12:30 Paris returned %r, expected None" % (got_inactive,))
    got_zero_width = device_config.seconds_until_quiet_hours_end(at_1330, "13:00", "13:00")
    if got_zero_width is not None:
        pytest.fail("start_hm == end_hm returned %r, expected None (a zero-width window is never active)" % (got_zero_width,))


def test_quiet_hours_status_enabled_gate_and_verified_value():
    """quiet_hours_status() returns (None, None) when quiet_hours_enabled is False, and (28000, '07:00') for an enabled 23:00-07:00 config at the verified anchor epoch"""
    base_config = {"quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}
    got_disabled = device_config.quiet_hours_status(base_config, 1700000000.0)
    if got_disabled != (None, None):
        pytest.fail("quiet_hours_status() with quiet_hours_enabled=False returned %r, expected (None, None)" % (got_disabled,))
    enabled_config = dict(base_config, quiet_hours_enabled=True)
    got_enabled = device_config.quiet_hours_status(enabled_config, 1700000000.0)
    if got_enabled != (28000, "07:00"):
        pytest.fail("quiet_hours_status() for an enabled 23:00-07:00 config at epoch 1700000000.0 returned %r, expected (28000, '07:00')" % (got_enabled,))


def test_quiet_hours_status_never_raises_for_hostile_now_epoch():
    """quiet_hours_status() returns (None, None) and never raises for a non-numeric string, None, NaN, or an absurdly large now_epoch"""
    config = {"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}
    for hostile in ("nope", None, float("nan"), 1e30):
        got = device_config.quiet_hours_status(config, hostile)
        if got != (None, None):
            pytest.fail("quiet_hours_status(config, %r) returned %r, expected (None, None)" % (hostile, got))


def test_normalise_wake_interval_s_bounds_and_bool_gotcha():
    """normalise_wake_interval_s() returns None for True, False (the bool-is-an-int gotcha), a numeric string, a float, and every out-of-[60, 3600] int, and returns 60/3600/120 unchanged"""
    for hostile in (True, False, "120", 120.0, 59, 3601, 0, -1, None, []):
        got = device_config.normalise_wake_interval_s(hostile)
        if got is not None:
            pytest.fail("normalise_wake_interval_s(%r) returned %r, expected None" % (hostile, got))
    for accepted in (60, 3600, 120):
        got = device_config.normalise_wake_interval_s(accepted)
        if got != accepted:
            pytest.fail("normalise_wake_interval_s(%r) returned %r, expected it unchanged" % (accepted, got))


def test_hand_written_hostile_wake_interval_s_yields_none(tmp_path):
    """load_device_config() degrades a hand-written hostile wake_interval_s (JSON true, a numeric string, a float, or the below-minimum 30) to None, and lets an in-range 120 survive unchanged"""
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    for bad_json, label in (
        ('{"wake_interval_s": true}', "JSON true"),
        ('{"wake_interval_s": "120"}', 'JSON string "120"'),
        ('{"wake_interval_s": 120.5}', "JSON float 120.5"),
        ('{"wake_interval_s": 30}', "below-minimum int 30 (deploy/skypane.env.example's SKYPANE_SLEEP_S)"),
    ):
        with open(path, "w") as fh:
            fh.write(bad_json)
        config = device_config.load_device_config(tmpdir)
        if config["wake_interval_s"] is not None:
            pytest.fail("%s produced wake_interval_s=%r, expected None" % (label, config["wake_interval_s"]))
    with open(path, "w") as fh:
        fh.write('{"wake_interval_s": 120}')
    config = device_config.load_device_config(tmpdir)
    if config["wake_interval_s"] != 120:
        pytest.fail("an in-range wake_interval_s=120 produced %r, expected 120" % (config["wake_interval_s"],))


def test_save_wake_interval_s_round_trips(tmp_path):
    """save_device_config(wake_interval_s=120) round-trips through load_device_config() as 120, with theme/tracked_runway/led_enabled and all three quiet-hours fields still at their prior (default) values"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, wake_interval_s=120)
    config = device_config.load_device_config(tmpdir)
    if config != {
        "theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True,
        "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        "wake_interval_s": 120, "display_enabled": True, "calendar_theme_id": None, "screen_id": "plane-frame",
        "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"},
    }:
        pytest.fail("round-trip produced %r" % (config,))


def test_save_wake_interval_s_rejects_out_of_bounds_and_bools(tmp_path):
    """save_device_config() rejects wake_interval_s=59, 3601, True, False, '120', and 120.0 with ValueError, leaves a pre-existing, legitimately-saved file byte-identical across every rejection, and accepts the inclusive bounds 60 and 3600"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3")
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    for hostile in (59, 3601, True, False, "120", 120.0):
        raised = False
        try:
            device_config.save_device_config(tmpdir, wake_interval_s=hostile)
        except ValueError:
            raised = True
        if not raised:
            pytest.fail("save_device_config(wake_interval_s=%r) did not raise ValueError" % (hostile,))
        with open(path, "rb") as fh:
            after = fh.read()
        if before != after:
            pytest.fail("save_device_config(wake_interval_s=%r) changed a pre-existing file's bytes" % (hostile,))
    for boundary in (60, 3600):
        device_config.save_device_config(tmpdir, wake_interval_s=boundary)
        config = device_config.load_device_config(tmpdir)
        if config["wake_interval_s"] != boundary:
            pytest.fail("save_device_config(wake_interval_s=%r) did not round-trip as %r, got %r" % (
                boundary, boundary, config["wake_interval_s"],
            ))


def test_wake_interval_s_carries_forward_on_unrelated_save(tmp_path):
    """a subsequent theme-only save_device_config(theme='black') carries a previously-saved wake_interval_s=120 forward unchanged"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, wake_interval_s=120)
    device_config.save_device_config(tmpdir, theme="black")
    config = device_config.load_device_config(tmpdir)
    if config["wake_interval_s"] != 120:
        pytest.fail("a theme-only save did not carry a previously-saved wake_interval_s=120 forward, got %r" % (config["wake_interval_s"],))


def test_normalise_theme_arriving_degrades_hostile_values_never_to_default():
    """normalise_theme_arriving() degrades a hostile string, an int, a bool, an empty string, a dict, and None to None - never to DEFAULT_THEME_ID, the wrong-shaped answer normalise_theme_id() would give - and returns a real THEMES member unchanged"""
    for hostile in ("chartreuse", 42, True, "", {"a": 1}, None):
        got = device_config.normalise_theme_arriving(hostile)
        if got is not None:
            pytest.fail("normalise_theme_arriving(%r) returned %r, expected None (never DEFAULT_THEME_ID)" % (hostile, got))
    if device_config.normalise_theme_arriving("white") != "white":
        pytest.fail("normalise_theme_arriving('white') did not return 'white' unchanged")


def test_clear_theme_arriving_sentinel_is_distinct_from_none_and_any_theme_id():
    """CLEAR_THEME_ARRIVING is a distinct object - not None, and neither equal to nor a member of any registered theme id, so it can never collide with a real theme id or with unset"""
    if device_config.CLEAR_THEME_ARRIVING is None:
        pytest.fail("CLEAR_THEME_ARRIVING is None - it must be a distinct sentinel")
    if device_config.CLEAR_THEME_ARRIVING in device_config.THEME_IDS:
        pytest.fail("CLEAR_THEME_ARRIVING collides with a real theme id")
    if device_config.CLEAR_THEME_ARRIVING == "white":
        pytest.fail("CLEAR_THEME_ARRIVING == 'white' - it must never equality-match a theme id")


def test_hand_written_hostile_theme_arriving_yields_none_never_default(tmp_path):
    """load_device_config() degrades a hand-written hostile theme_arriving (an unregistered string, a JSON int, or JSON null) to None, never to DEFAULT_THEME_ID"""
    # The degrade proof (15-VALIDATION.md row 6): a hand-edited on-disk
    # theme_arriving degrades to None on read, matching
    # normalise_theme_arriving()'s own contract, and is a real
    # save-then-hand-edit-then-load round trip against a temp state
    # dir - not a source grep.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    for bad_json, label in (
        ('{"theme_arriving": "chartreuse"}', "an unregistered string"),
        ('{"theme_arriving": 7}', "JSON int 7"),
        ('{"theme_arriving": null}', "JSON null"),
    ):
        with open(path, "w") as fh:
            fh.write(bad_json)
        config = device_config.load_device_config(tmpdir)
        if config["theme_arriving"] is not None:
            pytest.fail("%s produced theme_arriving=%r, expected None" % (label, config["theme_arriving"]))


def test_pre_phase_14_file_has_no_theme_arriving_migration(tmp_path):
    """a device_config.json written before this phase (no theme_arriving key at all) loads every stored key unchanged, resolves theme_arriving to None, and is not rewritten on disk by load_device_config() - no migration"""
    # The no-migration proof (15-VALIDATION.md row 6): a
    # device_config.json written before this phase - one that has never
    # carried theme_arriving at all - round-trips every stored key
    # unchanged, resolves theme_arriving to None, and load_device_config()
    # never rewrites the file to add the new key.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    pre_phase_14_doc = {
        "theme": "blue", "tracked_runway": "06-24", "led_enabled": False,
        "quiet_hours_enabled": True, "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        "wake_interval_s": 300, "display_enabled": False,
    }
    with open(path, "w") as fh:
        json.dump(pre_phase_14_doc, fh)
    with open(path, "rb") as fh:
        before = fh.read()
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] is not None:
        pytest.fail("a file with no theme_arriving key produced %r, expected None" % (config["theme_arriving"],))
    for key, want in pre_phase_14_doc.items():
        if config[key] != want:
            pytest.fail("pre-existing key %r round-tripped as %r, expected %r" % (key, config[key], want))
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("load_device_config() rewrote a pre-Phase-14 file on disk - no migration is permitted")


def test_theme_arriving_three_state_write_contract(tmp_path):
    """save_device_config()'s theme_arriving honours its three-state contract end to end: set, carry-forward-on-omission, CLEAR_THEME_ARRIVING clears to None without disturbing theme, and a non-member value raises ValueError leaving the file byte-identical"""
    # The three-state write proof (15-VALIDATION.md row 6): set,
    # carry-forward-on-omission, CLEAR_THEME_ARRIVING clears to None
    # without disturbing an unrelated key, and a non-member value raises
    # ValueError leaving the file byte-identical - the full D-04/D-05
    # contract in one real save/load sequence against a temp state dir.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)

    device_config.save_device_config(tmpdir, theme_arriving="black")
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] != "black":
        pytest.fail("save_device_config(theme_arriving='black') did not round-trip, got %r" % (config["theme_arriving"],))

    device_config.save_device_config(tmpdir, theme="red")
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] != "black":
        pytest.fail("a theme-only save (theme_arriving omitted) did not carry theme_arriving='black' forward, got %r" % (config["theme_arriving"],))
    if config["theme"] != "red":
        pytest.fail("theme did not update to 'red', got %r" % (config["theme"],))

    device_config.save_device_config(tmpdir, theme_arriving=device_config.CLEAR_THEME_ARRIVING)
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] is not None:
        pytest.fail("save_device_config(theme_arriving=CLEAR_THEME_ARRIVING) did not clear to None, got %r" % (config["theme_arriving"],))
    if config["theme"] != "red":
        pytest.fail("clearing theme_arriving disturbed the unrelated theme key, got %r" % (config["theme"],))

    with open(path, "rb") as fh:
        before = fh.read()
    raised = False
    try:
        device_config.save_device_config(tmpdir, theme_arriving="chartreuse")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config(theme_arriving='chartreuse') did not raise ValueError")
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("a rejected theme_arriving write changed a pre-existing file's bytes")


def test_normalise_display_enabled_only_accepts_real_bools():
    """normalise_display_enabled() degrades int 0, int 1, 'true', 'on', an empty string, None, an empty list, and an empty dict to DEFAULT_DISPLAY_ENABLED, and returns both real booleans unchanged"""
    # 12-01: the bool-is-an-int gotcha from the other direction -
    # isinstance(0, bool) is False, so a JSON 0 is not a valid off value
    # and must degrade to the fail-open DEFAULT_DISPLAY_ENABLED (D-09).
    for hostile in (0, 1, "true", "on", "", None, [], {}, 1.0):
        got = device_config.normalise_display_enabled(hostile)
        if got is not device_config.DEFAULT_DISPLAY_ENABLED:
            pytest.fail("normalise_display_enabled(%r) returned %r, expected DEFAULT_DISPLAY_ENABLED" % (hostile, got))
    if device_config.normalise_display_enabled(True) is not True:
        pytest.fail("normalise_display_enabled(True) did not return True")
    if device_config.normalise_display_enabled(False) is not False:
        pytest.fail("normalise_display_enabled(False) did not return False")


def test_hand_written_hostile_display_enabled_yields_true_but_false_survives(tmp_path):
    """load_device_config() degrades a hand-written hostile display_enabled (0, "false", null, or a non-dict document) to True so a corrupted config can never darken the frame (D-09), while a legitimate display_enabled=false survives as False"""
    # 12-01/D-09: a corrupted or hand-edited config must never be the
    # reason a frame goes dark - every hostile on-disk shape degrades to
    # True, while a legitimate False survives untouched.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    for bad_json, label in (
        ('{"display_enabled": 0}', "JSON int 0"),
        ('{"display_enabled": "false"}', 'JSON string "false"'),
        ('{"display_enabled": null}', "JSON null"),
        ('["not", "a", "dict"]', "a non-dict document"),
    ):
        with open(path, "w") as fh:
            fh.write(bad_json)
        config = device_config.load_device_config(tmpdir)
        if config["display_enabled"] is not True:
            pytest.fail("%s produced display_enabled=%r, expected True (fail-open, D-09)" % (label, config["display_enabled"]))
    with open(path, "w") as fh:
        fh.write('{"display_enabled": false}')
    config = device_config.load_device_config(tmpdir)
    if config["display_enabled"] is not False:
        pytest.fail("a hand-written display_enabled=false produced %r, expected it to survive as False" % (config["display_enabled"],))


def test_save_display_enabled_false_round_trips_and_carries_forward(tmp_path):
    """save_device_config(display_enabled=False) round-trips through load_device_config() as False with all seven other fields still at their prior (default) values, and a subsequent theme-only save carries display_enabled=False forward unchanged"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, display_enabled=False)
    config = device_config.load_device_config(tmpdir)
    if config != {
        "theme": "white", "theme_arriving": None, "tracked_runway": "3", "led_enabled": True,
        "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        "wake_interval_s": None, "display_enabled": False, "calendar_theme_id": None, "screen_id": "plane-frame",
        "notifications": {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"},
    }:
        pytest.fail("round-trip produced %r" % (config,))
    device_config.save_device_config(tmpdir, theme="black")
    config = device_config.load_device_config(tmpdir)
    if config["display_enabled"] is not False:
        pytest.fail("a theme-only save did not carry a previously-saved display_enabled=False forward, got %r" % (config["display_enabled"],))


def test_save_display_enabled_rejects_non_bool_and_leaves_file_byte_identical(tmp_path):
    """save_device_config() rejects display_enabled='on', 0, 1, 'false', and [] with ValueError and leaves a pre-existing, legitimately-saved file byte-identical across every rejection (display_enabled=None is not a rejection case - it means carry forward)"""
    # display_enabled=None is deliberately NOT a rejection case - None
    # means carry forward, matching every other field's contract.
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3", display_enabled=True)
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    for hostile in ("on", 0, 1, "false", []):
        raised = False
        try:
            device_config.save_device_config(tmpdir, display_enabled=hostile)
        except ValueError:
            raised = True
        if not raised:
            pytest.fail("save_device_config(display_enabled=%r) did not raise ValueError" % (hostile,))
        with open(path, "rb") as fh:
            after = fh.read()
        if before != after:
            pytest.fail("save_device_config(display_enabled=%r) changed a pre-existing file's bytes" % (hostile,))


def test_calendar_theme_id_absent_key_defaults_to_none(tmp_path):
    """load_device_config() resolves calendar_theme_id to None both for a missing state dir and for a config saved before this key was ever supplied - a pre-existing deployed config must not break"""
    # A pre-existing deployed config - either no file at all, or one
    # written by a save_device_config() call that never mentions
    # calendar_theme_id - must both resolve to None. A failure here
    # means an already-deployed device_config.json broke.
    tmpdir = tmp_path
    missing = os.path.join(tmpdir, "does-not-exist")
    config = device_config.load_device_config(missing)
    if config["calendar_theme_id"] is not None:
        pytest.fail("a missing state dir produced calendar_theme_id=%r, expected None" % (config["calendar_theme_id"],))

    device_config.save_device_config(tmpdir, theme="black")
    config = device_config.load_device_config(tmpdir)
    if config["calendar_theme_id"] is not None:
        pytest.fail("a saved config that never mentioned calendar_theme_id produced %r, expected None - a pre-existing deployed config would break" % (config["calendar_theme_id"],))


def test_calendar_theme_id_round_trips(tmp_path):
    """save_device_config(calendar_theme_id=<a registered THEME_IDS member>) round-trips through load_device_config() unchanged"""
    tmpdir = tmp_path
    good = device_config.THEME_IDS[-1]
    device_config.save_device_config(tmpdir, calendar_theme_id=good)
    config = device_config.load_device_config(tmpdir)
    if config["calendar_theme_id"] != good:
        pytest.fail("save_device_config(calendar_theme_id=%r) did not round-trip, got %r" % (good, config["calendar_theme_id"]))


def test_hand_written_hostile_calendar_theme_id_yields_none_never_default(tmp_path):
    """load_device_config() degrades a hand-written hostile calendar_theme_id (an unregistered string, the empty string, a JSON int, bool, list, dict, or null) to None, provably never to DEFAULT_THEME_ID (T-16-TAMPER)"""
    # T-16-TAMPER: every hostile on-disk shape degrades to None, and
    # explicitly NOT to DEFAULT_THEME_ID - a future change that copies
    # normalise_theme_id()'s degrade-to-default shape by mistake for
    # this key must fail here.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    for bad_json, label in (
        ('{"calendar_theme_id": "not-a-theme"}', "an unregistered string"),
        ('{"calendar_theme_id": ""}', "an empty string"),
        ('{"calendar_theme_id": 7}', "a JSON int"),
        ('{"calendar_theme_id": true}', "a JSON bool"),
        ('{"calendar_theme_id": ["white"]}', "a JSON list"),
        ('{"calendar_theme_id": {"id": "white"}}', "a JSON dict"),
        ('{"calendar_theme_id": null}', "JSON null"),
    ):
        with open(path, "w") as fh:
            fh.write(bad_json)
        config = device_config.load_device_config(tmpdir)
        if config["calendar_theme_id"] is not None:
            pytest.fail("%s produced calendar_theme_id=%r, expected None" % (label, config["calendar_theme_id"]))
        if config["calendar_theme_id"] == device_config.DEFAULT_THEME_ID:
            pytest.fail("%s degraded to DEFAULT_THEME_ID instead of None" % (label,))


def test_save_calendar_theme_id_rejects_non_member_byte_identical(tmp_path):
    """save_device_config(calendar_theme_id=<non-member>) raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black", tracked_runway="3")
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    raised = False
    try:
        device_config.save_device_config(tmpdir, calendar_theme_id="not-a-theme")
    except ValueError:
        raised = True
    if not raised:
        pytest.fail("save_device_config(calendar_theme_id='not-a-theme') did not raise ValueError")
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("a rejected calendar_theme_id write changed a pre-existing file's bytes")


def test_calendar_theme_id_carries_forward_in_both_directions(tmp_path):
    """a save that supplies only calendar_theme_id leaves theme/theme_arriving/tracked_runway/led_enabled/quiet-hours/wake_interval_s/display_enabled at their stored values, and a save that supplies only theme leaves an already-stored calendar_theme_id intact"""
    tmpdir = tmp_path
    good = device_config.THEME_IDS[-1]

    # A save that supplies only calendar_theme_id leaves every other
    # field at its stored value.
    device_config.save_device_config(
        tmpdir, theme="black", theme_arriving="red", tracked_runway="02-20",
        led_enabled=False, quiet_hours_enabled=True, quiet_hours_start="22:00",
        quiet_hours_end="06:00", wake_interval_s=120, display_enabled=False,
    )
    device_config.save_device_config(tmpdir, calendar_theme_id=good)
    config = device_config.load_device_config(tmpdir)
    if config["calendar_theme_id"] != good:
        pytest.fail("calendar_theme_id did not save, got %r" % (config["calendar_theme_id"],))
    for key, want in (
        ("theme", "black"), ("theme_arriving", "red"), ("tracked_runway", "02-20"),
        ("led_enabled", False), ("quiet_hours_enabled", True), ("quiet_hours_start", "22:00"),
        ("quiet_hours_end", "06:00"), ("wake_interval_s", 120), ("display_enabled", False),
    ):
        if config[key] != want:
            pytest.fail("a calendar_theme_id-only save disturbed %r: got %r, expected %r" % (key, config[key], want))

    # A save that supplies only theme leaves an already-stored
    # calendar_theme_id intact.
    device_config.save_device_config(tmpdir, theme="white")
    config = device_config.load_device_config(tmpdir)
    if config["calendar_theme_id"] != good:
        pytest.fail("a theme-only save did not carry a previously-saved calendar_theme_id forward, got %r" % (config["calendar_theme_id"],))
    if config["theme"] != "white":
        pytest.fail("theme did not update to 'white', got %r" % (config["theme"],))


def test_calendar_theme_id_independent_of_theme_arriving(tmp_path):
    """clearing theme_arriving through CLEAR_THEME_ARRIVING leaves a separately-set calendar_theme_id untouched - the two override keys are not coupled by the shared write path"""
    # The two override keys share the same write path (new_config /
    # save_device_config()) but must not be coupled by it: clearing
    # theme_arriving via its sentinel must never disturb
    # calendar_theme_id, and vice versa is implicitly covered by every
    # other carry-forward check above.
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme_arriving="black", calendar_theme_id="red")
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] != "black" or config["calendar_theme_id"] != "red":
        pytest.fail("initial save did not set both keys, got theme_arriving=%r calendar_theme_id=%r" % (
            config["theme_arriving"], config["calendar_theme_id"],
        ))

    device_config.save_device_config(tmpdir, theme_arriving=device_config.CLEAR_THEME_ARRIVING)
    config = device_config.load_device_config(tmpdir)
    if config["theme_arriving"] is not None:
        pytest.fail("CLEAR_THEME_ARRIVING did not clear theme_arriving, got %r" % (config["theme_arriving"],))
    if config["calendar_theme_id"] != "red":
        pytest.fail("clearing theme_arriving disturbed the unrelated calendar_theme_id, got %r" % (config["calendar_theme_id"],))


def test_normalise_screen_id_degrades_hostile_values_to_default():
    """normalise_screen_id() degrades a hostile/unknown/None/non-string value to DEFAULT_SCREEN_ID and passes a real member through unchanged"""
    for value in ("nope", "../../etc/passwd", 7, None, True, [], {}):
        got = device_config.normalise_screen_id(value)
        if got != device_config.DEFAULT_SCREEN_ID:
            pytest.fail("normalise_screen_id(%r) returned %r, expected %r" % (
                value, got, device_config.DEFAULT_SCREEN_ID))
    if device_config.normalise_screen_id("plane-frame") != "plane-frame":
        pytest.fail("normalise_screen_id() did not pass through a real member unchanged")


def test_save_device_config_rejects_unknown_screen_id_without_touching_file(tmp_path):
    """save_device_config(screen_id='nope') raises ValueError naming SCREEN_IDS and leaves a pre-existing file byte-identical"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black")
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    try:
        device_config.save_device_config(tmpdir, screen_id="nope")
    except ValueError:
        pass
    else:
        pytest.fail("save_device_config(screen_id='nope') did not raise ValueError")
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("a rejected screen_id write disturbed the pre-existing file on disk")


def test_screen_id_absent_from_disk_resolves_to_default_with_no_migration(tmp_path):
    """a device_config.json written with no screen_id key loads with DEFAULT_SCREEN_ID and is never rewritten on read"""
    # The no-migration proof, mirroring theme_arriving's own precedent
    # above: a device_config.json written before D-23 - one that has
    # never carried screen_id at all - resolves that key to
    # DEFAULT_SCREEN_ID and load_device_config() never rewrites the
    # file to add the new key.
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    pre_d23_doc = {
        "theme": "white", "tracked_runway": "3", "led_enabled": True,
        "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
        "wake_interval_s": None, "display_enabled": True,
    }
    with open(path, "w") as fh:
        json.dump(pre_d23_doc, fh)
    with open(path, "rb") as fh:
        before = fh.read()
    config = device_config.load_device_config(tmpdir)
    if config["screen_id"] != device_config.DEFAULT_SCREEN_ID:
        pytest.fail("a file with no screen_id key produced %r, expected %r" % (
            config["screen_id"], device_config.DEFAULT_SCREEN_ID))
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("load_device_config() rewrote a pre-D-23 file on disk - no migration is permitted")


def test_screen_id_registry_agrees_with_companion_screens():
    """device_config.SCREEN_IDS/DEFAULT_SCREEN_ID stay pinned equal to companion.screens's own duplicated-not-imported values"""
    import companion.screens as screens
    if device_config.SCREEN_IDS != screens.SCREEN_IDS:
        pytest.fail("device_config.SCREEN_IDS %r != companion.screens.SCREEN_IDS %r" % (
            device_config.SCREEN_IDS, screens.SCREEN_IDS))
    if device_config.DEFAULT_SCREEN_ID != screens.DEFAULT_SCREEN_ID:
        pytest.fail("device_config.DEFAULT_SCREEN_ID %r != companion.screens.DEFAULT_SCREEN_ID %r" % (
            device_config.DEFAULT_SCREEN_ID, screens.DEFAULT_SCREEN_ID))


def test_notifications_absent_from_disk_resolves_to_default_with_no_migration(tmp_path):
    """a device_config.json written before this phase (no notifications key at all) resolves notifications to DEFAULT_NOTIFICATIONS and is not rewritten on disk by load_device_config() - no migration"""
    tmpdir = tmp_path
    path = device_config.device_config_path(tmpdir)
    pre_phase_20_doc = {
        "theme": "blue", "tracked_runway": "06-24", "led_enabled": False,
        "quiet_hours_enabled": True, "quiet_hours_start": "22:00", "quiet_hours_end": "06:00",
        "wake_interval_s": 300, "display_enabled": False,
    }
    with open(path, "w") as fh:
        json.dump(pre_phase_20_doc, fh)
    with open(path, "rb") as fh:
        before = fh.read()
    config = device_config.load_device_config(tmpdir)
    if config["notifications"] != device_config.DEFAULT_NOTIFICATIONS:
        pytest.fail("a file with no notifications key produced %r, expected DEFAULT_NOTIFICATIONS" % (config["notifications"],))
    with open(path, "rb") as fh:
        after = fh.read()
    if before != after:
        pytest.fail("load_device_config() rewrote a pre-phase-20 file on disk - no migration is permitted")


def test_normalise_notifications_degrades_hostile_shapes_per_field():
    """normalise_notifications() degrades a non-dict value ('x', [], 7, None) to a copy of DEFAULT_NOTIFICATIONS wholesale, and degrades each hostile sub-field ({'lang': 'de'}, or a wrong-typed topic_url/battery_low/frame_silent) independently while a real sibling field survives"""
    for hostile in ("x", [], 7, None):
        got = device_config.normalise_notifications(hostile)
        if got != device_config.DEFAULT_NOTIFICATIONS:
            pytest.fail("normalise_notifications(%r) returned %r, expected a copy of DEFAULT_NOTIFICATIONS wholesale" % (hostile, got))
    got_partial = device_config.normalise_notifications({"lang": "de"})
    if got_partial != {
        "topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en",
    }:
        pytest.fail("normalise_notifications({'lang': 'de'}) returned %r, expected every field at its own default" % (got_partial,))
    got_mixed = device_config.normalise_notifications({
        "topic_url": 7, "battery_low": "yes", "frame_silent": 1, "lang": "fr",
    })
    if got_mixed != {
        "topic_url": None, "battery_low": True, "frame_silent": True, "lang": "fr",
    }:
        pytest.fail("normalise_notifications() with a wrong-typed topic_url/battery_low/frame_silent returned %r - each hostile sub-field must degrade independently, and the real lang='fr' must survive" % (got_mixed,))


def test_save_notifications_round_trips(tmp_path):
    """save_device_config(notifications={...}) round-trips through load_device_config() unchanged, leaving every sibling field at its prior (default) value"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, notifications={
        "topic_url": "https://ntfy.sh/skypane-xyz", "battery_low": False,
        "frame_silent": True, "lang": "fr",
    })
    config = device_config.load_device_config(tmpdir)
    if config["notifications"] != {
        "topic_url": "https://ntfy.sh/skypane-xyz", "battery_low": False,
        "frame_silent": True, "lang": "fr",
    }:
        pytest.fail("round-trip produced %r" % (config["notifications"],))
    if config["theme"] != device_config.DEFAULT_THEME_ID:
        pytest.fail("a notifications-only save disturbed theme, got %r" % (config["theme"],))


def test_save_notifications_rejects_every_malformed_shape(tmp_path):
    """save_device_config() rejects a non-dict notifications value, a non-str topic_url, a non-bool battery_low/frame_silent, and a lang outside ('en', 'fr') with ValueError, leaving a pre-existing, legitimately-saved file byte-identical across every rejection"""
    tmpdir = tmp_path
    device_config.save_device_config(tmpdir, theme="black")
    path = device_config.device_config_path(tmpdir)
    with open(path, "rb") as fh:
        before = fh.read()
    hostile_groups = (
        "not-a-dict",
        {"topic_url": 7, "battery_low": True, "frame_silent": True, "lang": "en"},
        {"topic_url": None, "battery_low": "yes", "frame_silent": True, "lang": "en"},
        {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "de"},
    )
    for hostile in hostile_groups:
        raised = False
        try:
            device_config.save_device_config(tmpdir, notifications=hostile)
        except ValueError:
            raised = True
        if not raised:
            pytest.fail("save_device_config(notifications=%r) did not raise ValueError" % (hostile,))
        with open(path, "rb") as fh:
            after = fh.read()
        if before != after:
            pytest.fail("save_device_config(notifications=%r) changed a pre-existing file's bytes" % (hostile,))


def test_saved_topic_url_never_appears_in_a_rejected_writes_bytes_or_this_modules_own_source():
    """server/device_config.py introduces no print()/logging call for the notifications group, preserving this module's own print-free-by-design contract (T-20-12: a topic_url can never reach a log this module controls)"""
    # T-20-12: this module stores topic_url verbatim in
    # device_config.json (server/notify.py needs the real value to
    # send a push, D-25's own boundary) - there is no separate
    # config-history/audit log in this codebase for ANY field to
    # hook into (confirmed by inspection: no sibling field - theme,
    # led_enabled, the calendar URL in server/plane/calendar_rules.py
    # - writes to any such log either). What IS real and pinned here
    # is device_config.py's own "print-free by design" contract
    # (this module's own top-of-file docstring): adding notifications
    # introduces no new print()/logging call anywhere in this module,
    # so a hostile or legitimate topic_url can never reach a log this
    # module itself controls - the same proof
    # server/test_calendar_rules.py's T-16-SECRET checks pin for the
    # calendar feed URL, applied here by source inspection since this
    # module (unlike calendar_rules.fetch_ics()) has no failure path
    # that logs at all.
    src_path = os.path.join(REPO_ROOT, "server", "device_config.py")
    with open(src_path) as fh:
        src = fh.read()
    if "print(" in src:
        pytest.fail("server/device_config.py must stay print-free by design; found a print( call")
    if re.search(r'\blogging\.', src):
        pytest.fail("server/device_config.py must stay print-free by design; found a logging module call")


def test_connect_creates_db_with_wal_and_tables(tmp_path):
    """connect() creates history.db, sets WAL + busy_timeout, creates all three tables, and is idempotent"""
    tmpdir = tmp_path
    conn = history_db.connect(tmpdir)
    try:
        if not os.path.exists(history_db.history_db_path(tmpdir)):
            pytest.fail("history.db was not created")
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        if str(mode).lower() != "wal":
            pytest.fail("journal_mode is %r, expected wal" % (mode,))
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        if timeout_ms != 5000:
            pytest.fail("busy_timeout is %r, expected 5000" % (timeout_ms,))
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        for expected in ("runway_events", "device_health", "meta"):
            if expected not in tables:
                pytest.fail("table %r missing, found %r" % (expected, tables))
    finally:
        conn.close()
    conn2 = history_db.connect(tmpdir)  # calling connect() twice must not raise
    conn2.close()


def test_record_and_recent_runway_events(tmp_path):
    """record_runway_event() inserts one row; recent_runway_events(limit=2) returns the two newest, newest first"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_runway_event(conn, ts="2026-08-27T10:00:00+00:00", hex="aaaaaa", callsign="FLIGHT1")
        history_db.record_runway_event(conn, ts="2026-08-27T10:01:00+00:00", hex="bbbbbb", callsign="FLIGHT2")
        history_db.record_runway_event(conn, ts="2026-08-27T10:02:00+00:00", hex="cccccc", callsign="FLIGHT3")
        rows = history_db.recent_runway_events(conn, limit=2)
    hexes = [row["hex"] for row in rows]
    if hexes != ["cccccc", "bbbbbb"]:
        pytest.fail("expected newest-first ['cccccc', 'bbbbbb'], got %r" % (hexes,))


def test_route_source_counts_buckets_correctly(tmp_path):
    """route_source_counts(since=...) returns fresh_hit/cache_hit/miss with counts 1/2/1"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        for i, source in enumerate(["fresh_hit", "cache_hit", "cache_hit", "miss"]):
            history_db.record_runway_event(conn, ts="2026-08-27T10:0%d:00+00:00" % i, hex="h%d" % i, route_source=source)
        counts = history_db.route_source_counts(conn, since="2026-08-27T10:00:00+00:00")
    expected = {"fresh_hit": 1, "cache_hit": 2, "miss": 1}
    if counts != expected:
        pytest.fail("expected %r, got %r" % (expected, counts))


def test_corroboration_counts_keeps_none_distinct_from_false(tmp_path):
    """corroboration_counts(since=...) buckets True/None/False separately, never collapsing None into False"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_runway_event(conn, ts="2026-08-27T11:00:00+00:00", hex="h0", corroborated=True)
        history_db.record_runway_event(conn, ts="2026-08-27T11:01:00+00:00", hex="h1", corroborated=None)
        history_db.record_runway_event(conn, ts="2026-08-27T11:02:00+00:00", hex="h2", corroborated=False)
        counts = history_db.corroboration_counts(conn, since="2026-08-27T11:00:00+00:00")
    expected = {"True": 1, "None": 1, "False": 1}
    if counts != expected:
        pytest.fail("expected %r, got %r" % (expected, counts))


def test_corroborated_unknown_is_readable_back_distinctly(tmp_path):
    """a runway_events row written with corroborated unknown is readable back as the unknown value, distinct from false"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_runway_event(conn, ts="2026-08-27T12:00:00+00:00", hex="unk0", corroborated=None)
        history_db.record_runway_event(conn, ts="2026-08-27T12:01:00+00:00", hex="unk1", corroborated=False)
        rows = history_db.recent_runway_events(conn, limit=2)
    by_hex = {row["hex"]: row["corroborated"] for row in rows}
    if by_hex.get("unk0") != "None":
        pytest.fail("corroborated=None was not readable back as the unknown value, got %r" % (by_hex.get("unk0"),))
    if by_hex.get("unk1") != "False":
        pytest.fail("corroborated=False was not readable back as the false value, got %r" % (by_hex.get("unk1"),))
    if by_hex.get("unk0") == by_hex.get("unk1"):
        pytest.fail("the unknown and false corroboration values were not stored distinctly")


def test_hostile_callsign_round_trips_byte_identically(tmp_path):
    """a callsign containing an HTML angle bracket and a SQL quote round-trips byte-identically through recent_runway_events()"""
    tmpdir = tmp_path
    hostile_callsign = """<script>alert('x')</script>' OR '1'='1"""
    with history_db.open_db(tmpdir) as conn:
        history_db.record_runway_event(conn, ts="2026-08-27T13:00:00+00:00", hex="hostile1", callsign=hostile_callsign, airline="O'Brien's \"Air\"")
        rows = history_db.recent_runway_events(conn, limit=1)
    if not rows or rows[0]["callsign"] != hostile_callsign:
        pytest.fail("callsign round-tripped as %r, expected byte-identical %r" % (rows[0]["callsign"] if rows else None, hostile_callsign))
    if rows[0]["airline"] != "O'Brien's \"Air\"":
        pytest.fail("airline round-tripped as %r" % (rows[0]["airline"],))


def test_meta_get_set_overwrites_not_duplicates(tmp_path):
    """set_meta()/get_meta() round-trip, absent key reads None, a second set_meta() overwrites rather than duplicating"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        if history_db.get_meta(conn, "absent") is not None:
            pytest.fail("get_meta() on an absent key did not return None")
        history_db.set_meta(conn, "k", "v")
        if history_db.get_meta(conn, "k") != "v":
            pytest.fail("get_meta() after set_meta() did not return the stored value")
        history_db.set_meta(conn, "k", "v2")
        if history_db.get_meta(conn, "k") != "v2":
            pytest.fail("a second set_meta() on the same key did not overwrite")
        count = conn.execute("SELECT COUNT(*) FROM meta WHERE key = ?", ("k",)).fetchone()[0]
        if count != 1:
            pytest.fail("expected exactly one meta row for key 'k', found %d" % (count,))


def test_ingest_caddy_battery_log_is_idempotent(tmp_path):
    """ingest_caddy_battery_log() inserts exactly 2 rows from a mixed fixture, and 0 more on an unchanged re-run"""
    tmpdir = tmp_path
    log_path = os.path.join(tmpdir, "caddy-access.log")
    lines = [
        _caddy_log_line("/device/v1/display", 1798000000.0, {"X-Battery-Mv": ["3700"], "X-Fw-Version": ["1.0.0"]}),
        _caddy_log_line("/device/v1/display", 1798000030.0, {"X-Battery-Mv": ["3690"]}),
        _caddy_log_line("/img/deadbeef.bin", 1798000010.0, {"X-Battery-Mv": ["9999"]}),
        "not json at all {",
    ]
    with open(log_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    with history_db.open_db(tmpdir) as conn:
        first_count = history_db.ingest_caddy_battery_log(conn, log_path)
        rows_after_first = history_db.recent_device_health(conn, limit=10)
        second_count = history_db.ingest_caddy_battery_log(conn, log_path)
        rows_after_second = history_db.recent_device_health(conn, limit=10)

    if first_count != 2:
        pytest.fail("first ingest inserted %d rows, expected 2" % (first_count,))
    if len(rows_after_first) != 2:
        pytest.fail("expected 2 device_health rows after first ingest, found %d" % (len(rows_after_first),))
    if second_count != 0:
        pytest.fail("second ingest over an unchanged file inserted %d rows, expected 0" % (second_count,))
    if len(rows_after_second) != 2:
        pytest.fail("row count changed after a no-op second ingest: %d" % (len(rows_after_second),))


def test_daily_battery_averages_groups_excludes_and_bounds_correctly(tmp_path):
    """daily_battery_averages() groups by Europe/Paris calendar day, rounds the mean, orders newest-first, honours since=, and excludes NULL-battery and unparseable-timestamp rows (22-06-PLAN.md Task 1)"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        if history_db.daily_battery_averages(conn) != []:
            pytest.fail("an empty database must return an empty list")

        # Three consecutive days, three readings each, all at hours
        # that land on the SAME calendar day in both UTC and
        # Europe/Paris (CEST, UTC+2, in September) so this check
        # isolates grouping/mean/order/exclusion from the DST-
        # spillover behaviour, which gets its own dedicated checks
        # below (22-06-PLAN.md Task 1).
        day_dates = ["2026-09-02", "2026-09-01", "2026-08-31"]
        day_values = [[4000, 4100, 4200], [4001, 4101, 4201], [4002, 4102, 4202]]
        for day_date, values in zip(day_dates, day_values):
            for hour, mv in zip((6, 12, 18), values):
                ts = "%sT%02d:00:00+00:00" % (day_date, hour)
                history_db.record_device_health(conn, ts, battery_mv=mv)
        # Excluded: NULL battery, unparseable ts, and a real reading
        # older than the cutoff (day 0 is 2026-09-02, so 90 days back
        # is 2026-06-04 - put this well before that).
        history_db.record_device_health(conn, "2026-09-02T20:00:00+00:00", battery_mv=None)
        history_db.record_device_health(conn, "not-a-timestamp", battery_mv=9999)
        history_db.record_device_health(conn, "2026-03-01T00:00:00+00:00", battery_mv=1234)

        bounded = history_db.daily_battery_averages(conn, since="2026-06-04T00:00:00+00:00")
        unbounded = history_db.daily_battery_averages(conn)

    if len(bounded) != 3:
        pytest.fail("expected exactly 3 day buckets inside the window, got %r" % (bounded,))
    days = [row["ts"] for row in bounded]
    if days != ["2026-09-02", "2026-09-01", "2026-08-31"]:
        pytest.fail("expected newest-first Europe/Paris calendar days, got %r" % (days,))
    for row, expected_mean in zip(bounded, (4100, 4101, 4102)):
        if not isinstance(row["battery_mv"], int) or isinstance(row["battery_mv"], bool):
            pytest.fail("battery_mv must be a real int: %r" % (row,))
        if row["battery_mv"] != expected_mean:
            pytest.fail("daily mean wrong: %r expected %d" % (row, expected_mean))
        if row["reading_count"] != 3:
            pytest.fail("reading_count must be the contributing reading count: %r" % (row,))
    plotted = [row["battery_mv"] for row in bounded]
    if 9999 in plotted:
        pytest.fail("an unparseable-timestamp row must not form a bucket")
    if 1234 in plotted:
        pytest.fail("a row older than the cutoff must be excluded")
    if None in [row["ts"] for row in bounded]:
        pytest.fail("no NULL day bucket may survive")
    if len(unbounded) != 4 or unbounded[-1]["battery_mv"] != 1234:
        pytest.fail("since=None must return every day including the out-of-window one, got %r" % (unbounded,))


def test_daily_battery_averages_buckets_by_paris_day_not_utc_day(tmp_path):
    """daily_battery_averages(): a 01:30+02:00 reading buckets to its Europe/Paris day, and two same-Paris-day readings on different UTC days form ONE bucket (D-12.3, 22-06-PLAN.md Task 1)"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        # The plan's own example: 01:30 Paris local time (CEST,
        # +02:00) is 23:30 UTC the PREVIOUS day. Under the old
        # date(ts) (UTC) bucketing this landed on 2026-09-01; under
        # Paris-day bucketing it must land on 2026-09-02.
        history_db.record_device_health(conn, "2026-09-02T01:30:00+02:00", battery_mv=4000)
        # A second reading on the SAME Paris day (2026-09-02) but a
        # DIFFERENT UTC day (23:00 Paris local == 21:00 UTC, same
        # UTC day as the first reading's Paris day but a distinct
        # instant) must join the SAME bucket, not form a second one.
        history_db.record_device_health(conn, "2026-09-02T23:00:00+02:00", battery_mv=4200)

        rows = history_db.daily_battery_averages(conn)

    if len(rows) != 1:
        pytest.fail("expected exactly one Paris-day bucket, got %r" % (rows,))
    row = rows[0]
    if row["ts"] != "2026-09-02":
        pytest.fail("01:30+02:00 must bucket to the Paris day 2026-09-02, got %r" % (row,))
    if row["reading_count"] != 2:
        pytest.fail("two same-Paris-day readings must form ONE bucket, got %r" % (row,))
    if row["battery_mv"] != 4100:
        pytest.fail("bucket mean wrong: %r" % (row,))


def test_daily_battery_averages_crosses_the_march_dst_forward_transition(tmp_path):
    """daily_battery_averages() buckets correctly across the CET-to-CEST March transition (the skipped hour), on the Paris day each reading actually fell on (D-12.3)"""
    # The last Sunday of March 2026 is 2026-03-29: clocks jump from
    # 02:00 CET straight to 03:00 CEST, skipping the 02:00-03:00 hour.
    # One reading before the jump (CET, +01:00) and one after it
    # (CEST, +02:00), both on Paris calendar day 2026-03-29 despite
    # landing on different UTC days (2026-03-28 vs 2026-03-29), must
    # bucket together.
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_device_health(conn, "2026-03-29T00:30:00+01:00", battery_mv=3900)  # 2026-03-28T23:30Z
        history_db.record_device_health(conn, "2026-03-29T04:00:00+02:00", battery_mv=4100)  # 2026-03-29T02:00Z

        rows = history_db.daily_battery_averages(conn)

    if len(rows) != 1:
        pytest.fail("expected the March-transition readings in ONE Paris-day bucket, got %r" % (rows,))
    row = rows[0]
    if row["ts"] != "2026-03-29":
        pytest.fail("expected Paris day 2026-03-29, got %r" % (row,))
    if row["reading_count"] != 2:
        pytest.fail("both sides of the skipped hour must contribute, got %r" % (row,))
    if row["battery_mv"] != 4000:
        pytest.fail("bucket mean wrong across the March transition: %r" % (row,))


def test_daily_battery_averages_crosses_the_october_dst_back_transition(tmp_path):
    """daily_battery_averages() buckets correctly across the CEST-to-CET October transition (the repeated hour), counting each instant once on the correct Paris day (D-12.3)"""
    # The last Sunday of October 2026 is 2026-10-25: clocks fall back
    # from 03:00 CEST to 02:00 CET, so 02:00-03:00 local happens
    # TWICE. One reading at 02:30 CEST (+02:00, fold=0) and one at
    # 02:30 CET (+01:00, fold=1) share the same Paris wall-clock
    # reading and calendar day, but are distinct UTC instants an hour
    # apart - the repeated local hour must be counted once (as two
    # readings on the correct day), not split across two days.
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_device_health(conn, "2026-10-25T02:30:00+02:00", battery_mv=4200)  # 2026-10-25T00:30Z
        history_db.record_device_health(conn, "2026-10-25T02:30:00+01:00", battery_mv=4000)  # 2026-10-25T01:30Z
        # A control reading unambiguously later the same Paris day,
        # after the fallback (CET), proves the day boundary itself
        # did not shift.
        history_db.record_device_health(conn, "2026-10-25T10:00:00+01:00", battery_mv=4100)  # 2026-10-25T09:00Z

        rows = history_db.daily_battery_averages(conn)

    if len(rows) != 1:
        pytest.fail("expected the October-transition readings in ONE Paris-day bucket, got %r" % (rows,))
    row = rows[0]
    if row["ts"] != "2026-10-25":
        pytest.fail("expected Paris day 2026-10-25, got %r" % (row,))
    if row["reading_count"] != 3:
        pytest.fail("the repeated local hour's two instants plus the control must all contribute, got %r" % (row,))
    if row["battery_mv"] != 4100:
        pytest.fail("bucket mean wrong across the October transition: %r" % (row,))


def test_check_in_gaps_returns_consecutive_intervals_oldest_first(tmp_path):
    """check_in_gaps() returns the observed intervals between consecutive device_health check-ins, oldest-first, each carrying both timestamps, its length in seconds and its Paris day"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_device_health(conn, _GAP_T0, battery_mv=4200)
        history_db.record_device_health(conn, _GAP_T1, battery_mv=4190)
        history_db.record_device_health(conn, _GAP_T2, battery_mv=4180)
        gaps = history_db.check_in_gaps(conn)
    if len(gaps) != 2:
        pytest.fail("expected exactly two intervals across three check-ins, got %r" % (gaps,))
    if [gap["gap_s"] for gap in gaps] != [1800, 1800]:
        pytest.fail("expected two 1800 s intervals, got %r" % (gaps,))
    if gaps[0]["from_ts"] != _GAP_T0 or gaps[0]["ts"] != _GAP_T1:
        pytest.fail("the first interval must span t0 -> t1 oldest-first, got %r" % (gaps[0],))
    if gaps[1]["from_ts"] != _GAP_T1 or gaps[1]["ts"] != _GAP_T2:
        pytest.fail("the second interval must span t1 -> t2, got %r" % (gaps[1],))
    if [gap["day"] for gap in gaps] != ["2026-09-02", "2026-09-02"]:
        pytest.fail("each interval must carry its Europe/Paris day, got %r" % (gaps,))


def test_check_in_gaps_counts_a_null_battery_row_as_a_real_check_in(tmp_path):
    """check_in_gaps() reads EVERY device_health row, including one whose battery_mv is NULL - a missing X-Battery-Mv header is not a missed wake (CFG-43)"""
    # A device_health row with battery_mv NULL is a REAL check-in whose
    # X-Battery-Mv header was absent or unparseable. Applying the
    # `battery_mv IS NOT NULL` filter daily_battery_averages()
    # legitimately uses would invent a missed wake out of a missing
    # HTTP header - the specific defect this check exists to prevent.
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_device_health(conn, _GAP_T0, battery_mv=4200)
        history_db.record_device_health(conn, _GAP_T1)  # no X-Battery-Mv header
        history_db.record_device_health(conn, _GAP_T2, battery_mv=4180)
        gaps = history_db.check_in_gaps(conn)
    if any(gap["gap_s"] == 3600 for gap in gaps):
        pytest.fail("the NULL-battery check-in was filtered out of the series, merging the two "
            "30-minute intervals into one 3600 s gap that would render as a missed wake "
            "the device never missed: %r" % (gaps,))
    if len(gaps) != 2:
        pytest.fail("expected two intervals across three check-ins, got %r" % (gaps,))
    if [gap["gap_s"] for gap in gaps] != [1800, 1800]:
        pytest.fail("expected two 1800 s intervals, got %r" % (gaps,))


def test_check_in_gaps_reports_an_undatable_span_as_unknown_not_merged(tmp_path):
    """check_in_gaps() reports the spans an undatable ts bounds as UNKNOWN rather than merging them into one false long interval"""
    # `ts` is TEXT NOT NULL but otherwise unvalidated, and
    # tail_caddy_battery_log() stores whatever string sits in a Caddy
    # access-log entry's own `ts` field - so an unparseable value can
    # reach this column. Dropping such a row and moving on would merge
    # the two intervals either side into one long, false interval.
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        history_db.record_device_health(conn, _GAP_T0, battery_mv=4200)
        history_db.record_device_health(conn, "not-a-timestamp", battery_mv=4190)
        history_db.record_device_health(conn, _GAP_T2, battery_mv=4180)
        gaps = history_db.check_in_gaps(conn)
    if any(gap["gap_s"] == 3600 for gap in gaps):
        pytest.fail("the undatable check-in was dropped and the spans either side of it silently "
            "merged into one 3600 s interval - a missed wake that never happened: %r" % (gaps,))
    if len(gaps) != 2:
        pytest.fail("expected two spans around the undatable check-in, got %r" % (gaps,))
    if [gap["gap_s"] for gap in gaps] != [None, None]:
        pytest.fail("both spans bounded by an undatable check-in must be unknown, got %r" % (gaps,))


def test_check_in_gaps_degenerate_windows_return_empty_without_raising(tmp_path):
    """check_in_gaps() returns an empty list - never raising - for an empty table, a single check-in, and a window containing no rows, while an inclusive window still yields its interval"""
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        if history_db.check_in_gaps(conn) != []:
            pytest.fail("an empty device_health table must yield no intervals")
        history_db.record_device_health(conn, _GAP_T0, battery_mv=4200)
        if history_db.check_in_gaps(conn) != []:
            pytest.fail("a single check-in bounds no interval and must yield none")
        history_db.record_device_health(conn, _GAP_T1, battery_mv=4190)
        if history_db.check_in_gaps(conn, since="2099-01-01T00:00:00+00:00") != []:
            pytest.fail("a window containing no rows must yield no intervals")
        if len(history_db.check_in_gaps(conn, since=_GAP_T0)) != 1:
            pytest.fail("a window containing both rows must yield their one interval")


def test_check_in_gaps_docstring_states_what_it_cannot_know():
    """check_in_gaps()'s docstring carries both 'cannot know' caveats - the ingest-missed log range and the UNIQUE(ts, battery_mv) collapse with its 60-second bound - plus why battery_mv is unfiltered"""
    # A future reader who finds this function and not the plan must
    # learn the same limits the plan's caption carries.
    doc = (history_db.check_in_gaps.__doc__ or "")
    low = doc.lower()
    if "cannot know" not in low:
        pytest.fail("the docstring never says what this reader cannot know")
    if "rotat" not in low:
        pytest.fail("the docstring omits the rotation hole (an ingest-missed log range reads as a missed wake)")
    if "unique(ts, battery_mv)" not in low:
        pytest.fail("the docstring omits the UNIQUE(ts, battery_mv) collapse caveat")
    if "60" not in doc:
        pytest.fail("the docstring omits the provable WAKE_INTERVAL_MIN_S = 60 bound on that collapse")
    if "x-battery-mv" not in low:
        pytest.fail("the docstring never says WHY battery_mv is not filtered (the missing-header failure)")


def test_history_db_introduces_no_migration_mechanism():
    """server/history_db.py still contains no ALTER TABLE and no PRAGMA user_version - the whole migration story remains CREATE TABLE IF NOT EXISTS on every connection (CFG-43)"""
    src_path = os.path.join(REPO_ROOT, "server", "history_db.py")
    with open(src_path) as fh:
        src = fh.read()
    if re.search(r"ALTER\s+TABLE", src, re.IGNORECASE):
        pytest.fail("history_db.py grew an ALTER TABLE - this project has no migration mechanism")
    if re.search(r"PRAGMA\s+user_version", src, re.IGNORECASE):
        pytest.fail("history_db.py grew a PRAGMA user_version - this project has no schema version stamp")


def test_classify_check_in_gap_boundaries_on_the_multiplier_path():
    """classify_check_in_gap() is on-cadence below warn_s, late EXACTLY AT warn_s, still late below error_s and missing EXACTLY AT error_s, for a non-default 777 s cadence (CFG-43)"""
    # 777 s is off both the 60/300 round numbers a hand-typed default
    # might resemble and the STALE_WARN_FLOOR_S=300 floor, so the
    # multiplier path - not the floor - is what fires. The boundaries
    # are derived from the shared function, never re-typed here.
    warn_s, error_s = wake.device_staleness_thresholds(777)
    cases = (
        (warn_s - 1, wake.CHECK_IN_ON_CADENCE, "one second BELOW warn_s"),
        (warn_s, wake.CHECK_IN_LATE, "exactly AT warn_s"),
        (error_s - 1, wake.CHECK_IN_LATE, "one second BELOW error_s"),
        (error_s, wake.CHECK_IN_MISSING, "exactly AT error_s"),
    )
    for gap_s, expected, where in cases:
        got = wake.classify_check_in_gap(gap_s, 777)
        if got != expected:
            pytest.fail("at the boundary %s (warn_s=%r, error_s=%r): a %r s gap classified %r, expected %r"
                % (where, warn_s, error_s, gap_s, got, expected))


def test_classify_check_in_gap_none_cadence_uses_the_bare_floors():
    """classify_check_in_gap() with a None cadence degrades to the bare floors rather than refusing to classify - the same degradation device_staleness_thresholds(None) already performs"""
    # A cadence that cannot be determined must still classify - it
    # degrades to the bare floors exactly as device_staleness_
    # thresholds(None) already does, rather than refusing. Interior
    # values only: the boundary discipline is check above's job, so a
    # >= / > mutation fails exactly one check, not two.
    floors = wake.device_staleness_thresholds(None)
    if floors != (wake.STALE_WARN_FLOOR_S, wake.STALE_ERROR_FLOOR_S):
        pytest.fail("device_staleness_thresholds(None) is no longer the bare floors: %r" % (floors,))
    warn_s, error_s = floors
    cases = (
        (warn_s // 2, wake.CHECK_IN_ON_CADENCE),
        ((warn_s + error_s) // 2, wake.CHECK_IN_LATE),
        (error_s * 4, wake.CHECK_IN_MISSING),
    )
    for gap_s, expected in cases:
        got = wake.classify_check_in_gap(gap_s, None)
        if got != expected:
            pytest.fail("a %r s gap against an undetermined cadence classified %r, expected %r "
                "(bare floors %r)" % (gap_s, got, expected, floors))


def test_classify_check_in_gap_reports_an_unknowable_gap_as_unknown():
    """classify_check_in_gap() reports an unknowable gap (None, a non-number, a bool, a negative, NaN) as unknown - never as on-cadence"""
    # check_in_gaps() reports gap_s=None for a span bounded by an
    # undatable timestamp. Classifying that as on-cadence (the naive
    # falsy reading) would claim the device checked in on time during a
    # span whose duration is not knowable at all.
    for gap_s in (None, "1800", -60, True, float("nan")):
        got = wake.classify_check_in_gap(gap_s, 300)
        if got != wake.CHECK_IN_UNKNOWN:
            pytest.fail("gap_s=%r classified %r, expected %r" % (gap_s, got, wake.CHECK_IN_UNKNOWN))


def test_classify_check_in_gap_reuses_the_one_threshold_function():
    """classify_check_in_gap()'s own source derives its thresholds from device_staleness_thresholds(), re-types none of the multipliers or floors, reads no config, and history_db.py holds no second copy"""
    # Read off the COMPILED function, not its source text: co_names is
    # exactly the set of global names the body references, so a prose
    # mention in the docstring cannot pass or fail this, and co_consts
    # catches a re-typing that inlined the literals instead of the
    # names.
    code = wake.classify_check_in_gap.__code__
    names = set(code.co_names)
    if "device_staleness_thresholds" not in names:
        pytest.fail("classify_check_in_gap()'s body never calls device_staleness_thresholds() - it "
            "references %r" % (sorted(names),))
    for name in ("MISSED_WAKES_WARN", "MISSED_WAKES_ERROR", "STALE_WARN_FLOOR_S", "STALE_ERROR_FLOOR_S"):
        if name in names:
            pytest.fail("classify_check_in_gap() re-references %s instead of reusing the shared pair" % (name,))
    inlined = {
        value for value in code.co_consts
        if value in (wake.MISSED_WAKES_WARN, wake.MISSED_WAKES_ERROR,
                     wake.STALE_WARN_FLOOR_S, wake.STALE_ERROR_FLOOR_S)
    }
    if inlined:
        pytest.fail("classify_check_in_gap() inlines the multipliers/floors as literals %r instead of "
            "reusing the shared pair" % (sorted(inlined),))
    if "device_config" in names or "load_device_config" in names:
        pytest.fail("classify_check_in_gap() reads the config itself - the cadence must be an argument so a "
            "caller can state WHICH cadence its drawing was judged against")
    hdb_path = os.path.join(REPO_ROOT, "server", "history_db.py")
    with open(hdb_path) as fh:
        hdb_src = fh.read()
    for name in ("MISSED_WAKES_WARN", "MISSED_WAKES_ERROR", "STALE_WARN_FLOOR_S", "STALE_ERROR_FLOOR_S"):
        if name in hdb_src:
            pytest.fail("server/history_db.py holds a second copy of %s" % (name,))


def test_the_verdict_vocabulary_is_observed_never_honoured():
    """the verdict vocabulary is four distinct observed terms and neither history_db.py nor wake.py uses the words 'honoured' or 'punctual' anywhere (24-RESEARCH.md Risk 1)"""
    # 24-RESEARCH.md Risk 1: the data cannot support the phrase an
    # "honoured-wake rate" names, even with a new column, because a
    # rotation the ingest missed is indistinguishable from a missed
    # wake. A name chosen here is the name every caption inherits.
    verdicts = (
        wake.CHECK_IN_ON_CADENCE, wake.CHECK_IN_LATE,
        wake.CHECK_IN_MISSING, wake.CHECK_IN_UNKNOWN,
    )
    if len(set(verdicts)) != 4:
        pytest.fail("the four verdicts must be four distinct strings, got %r" % (verdicts,))
    for verdict in verdicts:
        if not isinstance(verdict, str) or not verdict:
            pytest.fail("each verdict must be a non-empty string, got %r" % (verdicts,))
    for rel in ("server/history_db.py", "server/wake.py"):
        with open(os.path.join(REPO_ROOT, *rel.split("/"))) as fh:
            body = fh.read().lower()
        for banned in ("honoured", "punctual"):
            if banned in body:
                pytest.fail("%s uses the word %r, which this data cannot support" % (rel, banned))


def test_every_create_table_is_guarded_and_there_are_exactly_four():
    """every CREATE TABLE in history_db.py is guarded by IF NOT EXISTS and there are exactly four - the fourth (wake_epochs) is the whole migration story for this phase"""
    src_path = os.path.join(REPO_ROOT, "server", "history_db.py")
    with open(src_path) as fh:
        src = fh.read()
    guarded = len(re.findall(r"CREATE TABLE IF NOT EXISTS", src))
    total = len(re.findall(r"CREATE TABLE", src))
    if guarded != total:
        pytest.fail("%d of history_db.py's %d CREATE TABLE statements are not guarded by IF NOT EXISTS - "
            "an unguarded one raises on the second connection" % (total - guarded, total))
    if total != 4:
        pytest.fail("expected exactly four CREATE TABLE IF NOT EXISTS statements (runway_events, "
            "device_health, meta, wake_epochs), found %d" % (total,))


def test_an_old_schema_database_gains_wake_epochs_without_losing_a_row(tmp_path):
    """a history.db created BEFORE wake_epochs existed opens cleanly, gains the table from the existing CREATE TABLE IF NOT EXISTS bootstrap, and keeps every pre-existing row intact (no migration needed)"""
    # Hand-seed a database in the PRE-Task-3 shape, bypassing
    # init_schema() entirely so this genuinely models a history.db the
    # old code created and left behind, then open it with the current
    # code.
    tmpdir = tmp_path
    db_path = history_db.history_db_path(tmpdir)
    old = sqlite3.connect(db_path)
    try:
        old.execute(
            "CREATE TABLE device_health (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, "
            "battery_mv INTEGER, fw_version TEXT, boot_reason TEXT, rssi TEXT, "
            "UNIQUE(ts, battery_mv))"
        )
        old.execute(
            "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        old.execute(
            "INSERT INTO device_health (ts, battery_mv, fw_version) VALUES (?, ?, ?)",
            ("2026-09-02T10:00:00+00:00", 4200, "1.2.3"),
        )
        old.execute(
            "INSERT INTO meta (key, value, updated_at) VALUES (?, ?, ?)",
            (history_db.META_CADDY_LOG_OFFSET, "4096", "2026-09-02T10:00:01+00:00"),
        )
        old.commit()
    finally:
        old.close()

    with history_db.open_db(tmpdir) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        if "wake_epochs" not in tables:
            pytest.fail("opening a pre-Task-3 database did not create wake_epochs: %r" % (sorted(tables),))
        rows = history_db.recent_device_health(conn)
        if len(rows) != 1 or rows[0]["battery_mv"] != 4200 or rows[0]["fw_version"] != "1.2.3":
            pytest.fail("the pre-existing device_health row did not survive intact: %r" % (rows,))
        if history_db.get_meta(conn, history_db.META_CADDY_LOG_OFFSET) != "4096":
            pytest.fail("the pre-existing meta row did not survive intact")
        if conn.execute("SELECT COUNT(*) FROM wake_epochs").fetchone()[0] != 0:
            pytest.fail("merely opening a database must not write a wake_epochs row")


def test_record_wake_epoch_writes_only_when_the_interval_changes(tmp_path):
    """record_wake_epoch() inserts only when the effective interval differs from the newest stored row, treating an undeterminable cadence as a distinct value rather than a continuation"""
    # The poll unit is Type=oneshot under a 30 s timer - ~2,880 cycles
    # a day. An unconditional write would add 2,880 rows a day carrying
    # no information at all (Pitfall 1's rule, applied to a fourth
    # table).
    tmpdir = tmp_path
    with history_db.open_db(tmpdir) as conn:
        wrote = [
            history_db.record_wake_epoch(conn, "2026-09-02T10:00:00+00:00", 300),
            history_db.record_wake_epoch(conn, "2026-09-02T10:00:30+00:00", 300),
            history_db.record_wake_epoch(conn, "2026-09-02T10:01:00+00:00", 300),
            history_db.record_wake_epoch(conn, "2026-09-02T10:01:30+00:00", 600),
            history_db.record_wake_epoch(conn, "2026-09-02T10:02:00+00:00", 600),
            # The cadence became undeterminable - a DISTINCT value,
            # not a continuation of 600. Recording it is the honest
            # reading: a later phase must not be told the frame was
            # still on a 600 s cadence when nothing said so.
            history_db.record_wake_epoch(conn, "2026-09-02T10:02:30+00:00", None),
            history_db.record_wake_epoch(conn, "2026-09-02T10:03:00+00:00", None),
        ]
        if wrote != [1, 0, 0, 1, 0, 1, 0]:
            pytest.fail("expected inserts only on a change, got %r" % (wrote,))
        rows = conn.execute(
            "SELECT ts, wake_interval_s FROM wake_epochs ORDER BY id ASC"
        ).fetchall()
    values = [row["wake_interval_s"] for row in rows]
    if values != [300, 600, None]:
        pytest.fail("expected one row per change in order, got %r" % (values,))
    if rows[0]["ts"] != "2026-09-02T10:00:00+00:00" or rows[1]["ts"] != "2026-09-02T10:01:30+00:00":
        pytest.fail("each epoch must carry the instant the new interval took effect, got %r" % ([dict(r) for r in rows],))


def test_nothing_under_companion_reads_the_epoch_table():
    """no file under companion/ so much as mentions wake_epochs - the table accrues data for a later phase and nothing in phase 24 reads it (24-RESEARCH.md Risk 1, Option C)"""
    # 24-RESEARCH.md Risk 1, Option C: if any plan lets a DRAWING read
    # this table, the drawing goes back to being blank until the
    # epochs accrue. No plan in phase 24 may read it.
    offenders = []
    companion_root = os.path.join(REPO_ROOT, "companion")
    for dirpath, dirnames, filenames in os.walk(companion_root):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", ".venv")]
        for filename in filenames:
            if not filename.endswith((".py", ".html", ".css", ".js")):
                continue
            full = os.path.join(dirpath, filename)
            try:
                with open(full) as fh:
                    if "wake_epochs" in fh.read():
                        offenders.append(os.path.relpath(full, REPO_ROOT))
            except OSError:
                continue
    if offenders:
        pytest.fail("wake_epochs is read by %r - it accrues data for a FUTURE phase and nothing in this one "
            "may draw from it" % (offenders,))


def test_all_sql_uses_placeholders_not_string_formatting():
    """every history_db.py execute() call uses ? placeholders, never %-formatting or an f-string"""
    src_path = os.path.join(REPO_ROOT, "server", "history_db.py")
    with open(src_path) as fh:
        src = fh.read()
    if re.search(r'execute\([^)]*%s.*%', src):
        pytest.fail("found a %-formatted string passed to execute()")
    if 'execute(f"' in src or "execute(f'" in src:
        pytest.fail("found an f-string passed to execute()")


def test_effective_wake_interval_s_battery_critical_pins_and_wins():
    """effective_wake_interval_s(cfg, battery_critical=True) pins device_config.BATTERY_CRITICAL_SLEEP_S ahead of every other consideration, including display_enabled=False, and the default False leaves every existing result unchanged"""
    # battery_critical=True pins the parked cadence regardless of every
    # other field, including display_enabled=False, which would
    # otherwise win (12-CONTEXT.md D-01).
    cfg_off = {"display_enabled": False, "wake_interval_s": 600}
    got = wake.effective_wake_interval_s(cfg_off, battery_critical=True)
    if got != device_config.BATTERY_CRITICAL_SLEEP_S:
        pytest.fail("effective_wake_interval_s(display_enabled=False, battery_critical=True) = %r, expected "
            "device_config.BATTERY_CRITICAL_SLEEP_S (%r)" % (got, device_config.BATTERY_CRITICAL_SLEEP_S))
    # The default (False) leaves every existing precedence path
    # unchanged - a representative sample of cfgs, with and without the
    # keyword, must produce identical results.
    samples = [
        None,
        {},
        {"display_enabled": False},
        {"wake_interval_s": 900},
        {"wake_interval_s": -5},
        {"display_enabled": True, "wake_interval_s": 120},
    ]
    for cfg in samples:
        without = wake.effective_wake_interval_s(cfg)
        with_default = wake.effective_wake_interval_s(cfg, battery_critical=False)
        if without != with_default:
            pytest.fail("effective_wake_interval_s(%r) = %r without the keyword but %r with "
                "battery_critical=False - the default must leave every existing result unchanged"
                % (cfg, without, with_default))


def test_read_battery_critical_is_fail_open(tmp_path):
    """read_battery_critical() returns True only for a literal JSON true under BATTERY_CRITICAL_STATE_KEY - a missing file, malformed JSON, a non-dict payload, the string 'true', and the int 1 all return False, and it never raises"""
    tmpdir = tmp_path
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("a missing poll_state.json: expected False")

    path = os.path.join(tmpdir, "poll_state.json")

    def _write_raw(text):
        with open(path, "w") as fh:
            fh.write(text)

    def _write_json(obj):
        with open(path, "w") as fh:
            json.dump(obj, fh)

    _write_raw("{not valid json")
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("malformed JSON: expected False")

    _write_json([1, 2, 3])
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("a JSON list (non-dict payload): expected False")

    _write_json({wake.BATTERY_CRITICAL_STATE_KEY: "true"})
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("a string 'true': expected False (only the literal boolean counts)")

    _write_json({wake.BATTERY_CRITICAL_STATE_KEY: 1})
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("an int 1: expected False (only the literal boolean counts)")

    _write_json({wake.BATTERY_CRITICAL_STATE_KEY: True})
    if wake.read_battery_critical(tmpdir) is not True:
        pytest.fail("a literal JSON true: expected True")

    _write_json({wake.BATTERY_CRITICAL_STATE_KEY: False})
    if wake.read_battery_critical(tmpdir) is not False:
        pytest.fail("a literal JSON false: expected False")


def test_next_wake_status_battery_critical_pins_3600s():
    """next_wake_status(last_checkin, cfg, battery_critical=True) puts the next wake exactly BATTERY_CRITICAL_SLEEP_S (3600 s) after the check-in when no quiet-hours window applies"""
    from datetime import datetime, timedelta

    checkin_iso = "2026-09-23T12:00:00+00:00"
    next_iso, effective_interval_s, _hold_reason = wake.next_wake_status(
        checkin_iso, {"wake_interval_s": 300}, battery_critical=True,
    )
    if effective_interval_s != device_config.BATTERY_CRITICAL_SLEEP_S:
        pytest.fail("next_wake_status(battery_critical=True) effective_interval_s = %r, expected "
            "device_config.BATTERY_CRITICAL_SLEEP_S (%r)"
            % (effective_interval_s, device_config.BATTERY_CRITICAL_SLEEP_S))
    expected_next = (
        datetime.fromisoformat(checkin_iso) + timedelta(seconds=device_config.BATTERY_CRITICAL_SLEEP_S)
    ).isoformat()
    if next_iso != expected_next:
        pytest.fail("next_wake_status(battery_critical=True)'s next_wake_iso = %r, expected %r (check-in + 3600s)"
            % (next_iso, expected_next))

