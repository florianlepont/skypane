#!/usr/bin/env python3
"""Contract harness for server/device_config.py (the theme + tracked-runway
registry and its validated, atomic JSON side-file) and server/history_db.py
(the SQLite history store behind CFG-03's health trend, CFG-06's flight
log, CFG-08's resolution statistics, and the Caddy access-log battery
tailer).

Stdlib-only. Exits 0 only when every check below passes.

Usage:
    server/.venv/bin/python3 server/test_config_history.py
"""
import json
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# 260902-l0b: +1 (_daily_battery_averages_groups_excludes_and_bounds_correctly)
# 10-01: +5 (quiet-hours registry fields: hostile-defaults, save round-trip,
# save-rejects-invalid-start, save-rejects-non-bool-enabled,
# normalise_quiet_hours_time hostile-shape rejection)
# 10-01: +4 (DST-safe window arithmetic: wrap-midnight/DST anchors,
# same-day/zero-width window, quiet_hours_status() enabled-gate + verified
# value, quiet_hours_status() hostile now_epoch never-raise)
# 11-01: +5 (wake_interval_s registry field: normalise bounds + bool
# gotcha, hostile-on-disk-value degradation, save round-trip, save-rejects
# out-of-bounds/bool with byte-identical-on-rejection, carry-forward)
# 12-01: +4 (display_enabled registry field: normalise bool-only gotcha,
# hostile-on-disk-value fail-open degradation, save round-trip +
# carry-forward, save-rejects-non-bool with byte-identical-on-rejection)
EXPECTED_CHECK_COUNT = 49


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


def main():
    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:  # never let an exception be swallowed into a pass
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        if ok:
            print("PASS %s" % name)
        else:
            print("FAIL %s - %s" % (name, reason))

    try:
        import server.device_config as device_config
    except ImportError as exc:
        print("FAIL import server.device_config - %r" % (exc,))
        print("config-history: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    import server.panel_format as panel_format

    # --- device_config.py -------------------------------------------------

    def _missing_state_dir_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            missing = os.path.join(tmpdir, "does-not-exist")
            config = device_config.load_device_config(missing)
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                return False, "expected defaults, got %r" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() on a missing state directory returns the documented defaults", _missing_state_dir_yields_defaults)

    def _malformed_file_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            for bad_content in ('["not", "a", "dict"]', "{truncated", "null"):
                path = device_config.device_config_path(tmpdir)
                with open(path, "w") as fh:
                    fh.write(bad_content)
                config = device_config.load_device_config(tmpdir)
                if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                    return False, "content %r produced %r, expected defaults" % (bad_content, config)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() on a JSON array, a truncated document, or a non-dict returns defaults instead of raising", _malformed_file_yields_defaults)

    def _hostile_values_yield_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            path = device_config.device_config_path(tmpdir)
            with open(path, "w") as fh:
                fh.write('{"theme": "../../etc/passwd", "tracked_runway": 7}')
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                return False, "hostile input produced %r, expected defaults for both keys" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() replaces an unrecognised theme/runway value with the default rather than passing it through", _hostile_values_yield_defaults)

    def _save_then_load_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="black", tracked_runway="02-20")
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "black", "tracked_runway": "02-20", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                return False, "round-trip produced %r" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("save_device_config() followed by load_device_config() round-trips the saved theme and tracked_runway", _save_then_load_round_trips)

    def _unknown_theme_rejected_without_touching_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            raised = False
            try:
                device_config.save_device_config(tmpdir, theme="nope")
            except ValueError:
                raised = True
            if not raised:
                return False, "save_device_config() with an unknown theme did not raise ValueError"
            path = device_config.device_config_path(tmpdir)
            if os.path.exists(path):
                return False, "a rejected save left a device_config.json file behind"
            if os.path.exists(path + ".tmp"):
                return False, "a rejected save left a .tmp file behind"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("save_device_config() with an unknown theme id raises ValueError and leaves the state directory file-free", _unknown_theme_rejected_without_touching_file)

    def _no_tmp_survives_a_successful_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="black", tracked_runway="3")
            if os.path.exists(device_config.device_config_path(tmpdir) + ".tmp"):
                return False, "a .tmp file survived a successful save"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("no .tmp file remains in the state directory after a successful save", _no_tmp_survives_a_successful_save)

    def _hostile_hand_edit_after_a_real_save_still_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="black", tracked_runway="02-20")
            path = device_config.device_config_path(tmpdir)
            with open(path, "w") as fh:
                fh.write('{"theme": "black/../x", "tracked_runway": "3; DROP TABLE"}')
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                return False, "hand-edited hostile file produced %r, expected defaults for both keys" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a legitimately saved config, hand-edited on disk to hostile values, still yields defaults from load_device_config()",
        _hostile_hand_edit_after_a_real_save_still_yields_defaults,
    )

    def _normalise_led_enabled_only_accepts_real_bools():
        for hostile in ("true", 0, 1, None, ["x"]):
            got = device_config.normalise_led_enabled(hostile)
            if got is not device_config.DEFAULT_LED_ENABLED:
                return False, "normalise_led_enabled(%r) returned %r, expected DEFAULT_LED_ENABLED" % (hostile, got)
        if device_config.normalise_led_enabled(True) is not True:
            return False, "normalise_led_enabled(True) did not return True"
        if device_config.normalise_led_enabled(False) is not False:
            return False, "normalise_led_enabled(False) did not return False"
        return True, ""

    check(
        "normalise_led_enabled() returns the value only for real bools and degrades a string, int 0, int 1, None, and a list to DEFAULT_LED_ENABLED",
        _normalise_led_enabled_only_accepts_real_bools,
    )

    def _save_led_enabled_false_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, led_enabled=False)
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": False, "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "wake_interval_s": None, "display_enabled": True}:
                return False, "round-trip produced %r" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(led_enabled=False) round-trips through load_device_config() as False, with theme/tracked_runway still at their defaults",
        _save_led_enabled_false_round_trips,
    )

    def _hand_written_hostile_led_enabled_yields_default():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            path = device_config.device_config_path(tmpdir)
            with open(path, "w") as fh:
                fh.write('{"led_enabled": "off"}')
            config = device_config.load_device_config(tmpdir)
            if config["led_enabled"] is not True:
                return False, "hostile string led_enabled produced %r, expected DEFAULT_LED_ENABLED" % (config["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a hand-written device_config.json whose led_enabled is a hostile string yields DEFAULT_LED_ENABLED from load_device_config()",
        _hand_written_hostile_led_enabled_yields_default,
    )

    def _save_led_enabled_off_rejected_without_touching_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                return False, "save_device_config(led_enabled='off') did not raise ValueError"
            with open(path, "rb") as fh:
                after = fh.read()
            if before != after:
                return False, "a rejected led_enabled write changed a pre-existing file's bytes"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(led_enabled='off') raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical",
        _save_led_enabled_off_rejected_without_touching_file,
    )

    def _theme_only_save_carries_led_enabled_false_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, led_enabled=False)
            device_config.save_device_config(tmpdir, theme="black")
            config = device_config.load_device_config(tmpdir)
            if config["led_enabled"] is not False:
                return False, "a theme-only save did not carry a previously-saved led_enabled=False forward, got %r" % (config["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a subsequent theme-only save_device_config(theme='black') carries a previously-saved led_enabled=False forward unchanged",
        _theme_only_save_carries_led_enabled_false_forward,
    )

    def _theme_registry_shape_is_correct():
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
                return False, "theme %r has keys %r, expected exactly %r" % (theme_id, set(entry), want_keys)
            for key in ("departing_index", "arriving_index", "ink_index"):
                if entry[key] not in valid_indices:
                    return False, "theme %r key %r has value %r, not a real panel_format.IDX_* index" % (theme_id, key, entry[key])
            if not isinstance(entry["label"], str) or not entry["label"]:
                return False, "theme %r label %r is not a non-empty string" % (theme_id, entry["label"])
            if not isinstance(entry["dithered"], bool):
                return False, "theme %r dithered %r is not a bool" % (theme_id, entry["dithered"])
            if entry["weight"] not in ("regular", "bold"):
                return False, "theme %r weight %r is not 'regular' or 'bold'" % (theme_id, entry["weight"])
            if is_band:
                if entry["band_index"] not in valid_indices:
                    return False, "band theme %r band_index %r is not a real panel_format.IDX_* index" % (theme_id, entry["band_index"])
                if not isinstance(entry["band_dithered"], bool):
                    return False, "band theme %r band_dithered %r is not a bool" % (theme_id, entry["band_dithered"])
        return True, ""

    check(
        "every THEMES entry carries exactly its contract keys (6 for non-band, 8 for band), real panel_format.IDX_* index values, a non-empty label, a bool dithered flag, a regular/bold weight, and (band entries only) a real band_index plus a bool band_dithered",
        _theme_registry_shape_is_correct,
    )

    def _every_theme_is_single_colour():
        # Phase 8 08-06 on-glass session: "sky" (the old two-tone
        # Blue-departing/Green-arriving pairing) was retired outright -
        # every registered theme is now single-colour, with no two-tone
        # exception left to carve out.
        for theme_id, entry in device_config.THEMES.items():
            if entry["departing_index"] != entry["arriving_index"]:
                return False, "theme %r is not single-colour: departing_index=%r arriving_index=%r" % (
                    theme_id, entry["departing_index"], entry["arriving_index"],
                )
        if "sky" in device_config.THEMES:
            return False, "the retired 'sky' two-tone theme is still present in THEMES"
        return True, ""

    check(
        "every registered theme is single-colour (departing_index == arriving_index); the retired two-tone 'sky' theme is gone",
        _every_theme_is_single_colour,
    )

    def _ink_contrast_pairing_is_correct():
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
            return False, "expected mapping covers %r, THEMES actually has %r" % (set(expected), set(device_config.THEMES))
        for theme_id, (bg, ink) in expected.items():
            entry = device_config.THEMES[theme_id]
            if entry["departing_index"] != bg or entry["ink_index"] != ink:
                return False, "theme %r expected background %r / ink %r, got background %r / ink %r" % (
                    theme_id, bg, ink, entry["departing_index"], entry["ink_index"],
                )
        return True, ""

    check(
        "every one of the 18 registered themes carries the exact background/ink pairing expected, pinned as an explicit id-to-(background,ink) mapping",
        _ink_contrast_pairing_is_correct,
    )

    def _dithered_and_weight_contract_is_correct():
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
            return False, "expected mapping covers %r, THEMES actually has %r" % (set(expected), set(device_config.THEMES))
        for theme_id, (dithered, weight) in expected.items():
            entry = device_config.THEMES[theme_id]
            if entry["dithered"] != dithered or entry["weight"] != weight:
                return False, "theme %r expected dithered=%r weight=%r, got dithered=%r weight=%r" % (
                    theme_id, dithered, weight, entry["dithered"], entry["weight"],
                )
        return True, ""

    check(
        "every registered theme's base-canvas dithered/weight pair matches the on-glass-confirmed values, including Yellow Light's Regular exception, the 5 White-base band themes, and the 2 tinted-field band themes' blue_light/red_light-derived values",
        _dithered_and_weight_contract_is_correct,
    )

    def _default_theme_and_labels_are_correct():
        if device_config.DEFAULT_THEME_ID != "white":
            return False, "DEFAULT_THEME_ID is %r, expected 'white'" % (device_config.DEFAULT_THEME_ID,)
        if device_config.DEFAULT_THEME_ID not in device_config.THEMES:
            return False, "DEFAULT_THEME_ID %r is not a member of THEMES" % (device_config.DEFAULT_THEME_ID,)
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
            return False, "expected label mapping covers %r, THEMES actually has %r" % (set(expected_labels), set(device_config.THEMES))
        for theme_id, label in expected_labels.items():
            got = device_config.theme_label(theme_id)
            if got != label:
                return False, "theme_label(%r) returned %r, expected %r" % (theme_id, got, label)
        return True, ""

    check(
        "DEFAULT_THEME_ID is 'white' and a THEMES member; theme_label() returns the exact plain label for all 18 ids",
        _default_theme_and_labels_are_correct,
    )

    def _theme_is_band_matches_registry_band_ids():
        expected_band_ids = {tid for tid, entry in device_config.THEMES.items() if "band_index" in entry}
        for theme_id in device_config.THEMES:
            got = device_config.theme_is_band(theme_id)
            want = theme_id in expected_band_ids
            if got != want:
                return False, "theme_is_band(%r) returned %r, expected %r" % (theme_id, got, want)
        if expected_band_ids != {
            "band_blue", "band_blue_light", "band_green_light", "band_red", "band_black",
            "band_blue_field", "band_red_field",
        }:
            return False, "registry's own band ids are %r, expected the 7 band ids" % (expected_band_ids,)
        return True, ""

    check(
        "theme_is_band() returns True for exactly the ids device_config.THEMES itself marks as band entries (band_index present) and False for every other registered id",
        _theme_is_band_matches_registry_band_ids,
    )

    def _theme_band_index_matches_registry_or_none():
        for theme_id, entry in device_config.THEMES.items():
            got = device_config.theme_band_index(theme_id)
            want = entry.get("band_index")
            if got != want:
                return False, "theme_band_index(%r) returned %r, expected %r" % (theme_id, got, want)
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
                return False, "theme_band_index(%r) expected %r, got %r" % (theme_id, idx, device_config.theme_band_index(theme_id))
        return True, ""

    check(
        "theme_band_index() returns THEMES's own band_index for every band id (the exact spike-confirmed IDX_* per colour) and None for every non-band id",
        _theme_band_index_matches_registry_or_none,
    )

    def _theme_band_dithered_matches_registry_or_false():
        for theme_id, entry in device_config.THEMES.items():
            got = device_config.theme_band_dithered(theme_id)
            want = entry.get("band_dithered", False)
            if got != want:
                return False, "theme_band_dithered(%r) returned %r, expected %r" % (theme_id, got, want)
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
                return False, "theme_band_dithered(%r) expected %r, got %r" % (theme_id, dithered, device_config.theme_band_dithered(theme_id))
        return True, ""

    check(
        "theme_band_dithered() returns THEMES's own band_dithered for every band id and False for every non-band id",
        _theme_band_dithered_matches_registry_or_false,
    )

    def _tinted_field_band_themes_are_tone_on_tone():
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
                return False, "theme %r is not tone-on-tone: band_index=%r departing_index=%r arriving_index=%r" % (
                    field_id, entry["band_index"], entry["departing_index"], entry["arriving_index"],
                )
            if entry["dithered"] is not True:
                return False, "theme %r expected dithered=True, got %r" % (field_id, entry["dithered"])
            if entry["band_dithered"] is not False:
                return False, "theme %r expected band_dithered=False, got %r" % (field_id, entry["band_dithered"])
            for key in ("departing_index", "arriving_index", "ink_index", "dithered", "weight"):
                if entry[key] != sibling[key]:
                    return False, "theme %r key %r is %r, expected to match its tinted-field sibling %r's own %r" % (
                        field_id, key, entry[key], sibling_id, sibling[key],
                    )
        return True, ""

    check(
        "band_blue_field/band_red_field are genuinely tone-on-tone (band_index equals departing_index equals arriving_index), dithered=True/band_dithered=False, and their base-canvas quadruple matches their tinted-field sibling's (blue_light/red_light) own registry row, read live rather than hardcoded",
        _tinted_field_band_themes_are_tone_on_tone,
    )

    def _hostile_quiet_hours_values_yield_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                    return False, "hostile quiet-hours input produced %r=%r, expected %r" % (key, config[key], want)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "load_device_config() replaces hostile quiet_hours_enabled/quiet_hours_start/quiet_hours_end values with their documented defaults",
        _hostile_quiet_hours_values_yield_defaults,
    )

    def _save_quiet_hours_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(
                tmpdir, quiet_hours_enabled=True, quiet_hours_start="22:30", quiet_hours_end="06:15")
            config = device_config.load_device_config(tmpdir)
            if config != {
                "theme": "white", "tracked_runway": "3", "led_enabled": True,
                "quiet_hours_enabled": True, "quiet_hours_start": "22:30", "quiet_hours_end": "06:15",
                "wake_interval_s": None, "display_enabled": True,
            }:
                return False, "round-trip produced %r" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(quiet_hours_enabled=True, quiet_hours_start='22:30', quiet_hours_end='06:15') round-trips through load_device_config() with theme/tracked_runway/led_enabled still at their prior (default) values",
        _save_quiet_hours_round_trips,
    )

    def _save_quiet_hours_start_invalid_rejected_without_touching_file():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                return False, "save_device_config(quiet_hours_start='24:00') did not raise ValueError"
            with open(path, "rb") as fh:
                after = fh.read()
            if before != after:
                return False, "a rejected quiet_hours_start write changed a pre-existing file's bytes"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(quiet_hours_start='24:00') raises ValueError and leaves a pre-existing, legitimately-saved file byte-identical",
        _save_quiet_hours_start_invalid_rejected_without_touching_file,
    )

    def _save_quiet_hours_enabled_non_bool_rejected():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            raised = False
            try:
                device_config.save_device_config(tmpdir, quiet_hours_enabled="on")
            except ValueError:
                raised = True
            if not raised:
                return False, "save_device_config(quiet_hours_enabled='on') did not raise ValueError"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(quiet_hours_enabled='on') raises ValueError",
        _save_quiet_hours_enabled_non_bool_rejected,
    )

    def _normalise_quiet_hours_time_rejects_every_hostile_shape():
        default = "23:00"
        for hostile in ("7:00", "07:60", "24:00", "", None, 7, "07:00\n"):
            got = device_config.normalise_quiet_hours_time(hostile, default)
            if got != default:
                return False, "normalise_quiet_hours_time(%r, %r) returned %r, expected the supplied default" % (hostile, default, got)
        return True, ""

    check(
        "normalise_quiet_hours_time() rejects an unpadded hour, an out-of-range minute, midnight-as-24:00, an empty string, None, an int, and a trailing newline - returning the supplied default for each",
        _normalise_quiet_hours_time_rejects_every_hostile_shape,
    )

    def _wrap_midnight_window_returns_verified_dst_values():
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
                return False, "seconds_until_quiet_hours_end(epoch=%r, %r, %r) returned %r, expected %r" % (
                    epoch, start_hm, end_hm, got, expected,
                )
        return True, ""

    check(
        "seconds_until_quiet_hours_end() returns the verified wrap-midnight/DST anchors: 28000 mid-window, None just past end, 23400 across spring-forward (1h less than naive), 30600 across autumn fall-back (1h more than naive)",
        _wrap_midnight_window_returns_verified_dst_values,
    )

    def _same_day_window_and_zero_width_window():
        from datetime import datetime, timezone

        # 2023-11-14 13:30/12:30 Paris (CET, UTC+1) for a same-day 13:00-14:00 window.
        at_1330 = datetime(2023, 11, 14, 12, 30, 0, tzinfo=timezone.utc)
        at_1230 = datetime(2023, 11, 14, 11, 30, 0, tzinfo=timezone.utc)
        got_active = device_config.seconds_until_quiet_hours_end(at_1330, "13:00", "14:00")
        if got_active != 1800:
            return False, "same-day window at 13:30 Paris returned %r, expected 1800" % (got_active,)
        got_inactive = device_config.seconds_until_quiet_hours_end(at_1230, "13:00", "14:00")
        if got_inactive is not None:
            return False, "same-day window at 12:30 Paris returned %r, expected None" % (got_inactive,)
        got_zero_width = device_config.seconds_until_quiet_hours_end(at_1330, "13:00", "13:00")
        if got_zero_width is not None:
            return False, "start_hm == end_hm returned %r, expected None (a zero-width window is never active)" % (got_zero_width,)
        return True, ""

    check(
        "seconds_until_quiet_hours_end() handles a same-day (non-wrapping) window correctly and returns None for a zero-width start_hm == end_hm window",
        _same_day_window_and_zero_width_window,
    )

    def _quiet_hours_status_enabled_gate_and_verified_value():
        base_config = {"quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}
        got_disabled = device_config.quiet_hours_status(base_config, 1700000000.0)
        if got_disabled != (None, None):
            return False, "quiet_hours_status() with quiet_hours_enabled=False returned %r, expected (None, None)" % (got_disabled,)
        enabled_config = dict(base_config, quiet_hours_enabled=True)
        got_enabled = device_config.quiet_hours_status(enabled_config, 1700000000.0)
        if got_enabled != (28000, "07:00"):
            return False, "quiet_hours_status() for an enabled 23:00-07:00 config at epoch 1700000000.0 returned %r, expected (28000, '07:00')" % (got_enabled,)
        return True, ""

    check(
        "quiet_hours_status() returns (None, None) when quiet_hours_enabled is False, and (28000, '07:00') for an enabled 23:00-07:00 config at the verified anchor epoch",
        _quiet_hours_status_enabled_gate_and_verified_value,
    )

    def _quiet_hours_status_never_raises_for_hostile_now_epoch():
        config = {"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}
        for hostile in ("nope", None, float("nan"), 1e30):
            got = device_config.quiet_hours_status(config, hostile)
            if got != (None, None):
                return False, "quiet_hours_status(config, %r) returned %r, expected (None, None)" % (hostile, got)
        return True, ""

    check(
        "quiet_hours_status() returns (None, None) and never raises for a non-numeric string, None, NaN, or an absurdly large now_epoch",
        _quiet_hours_status_never_raises_for_hostile_now_epoch,
    )

    def _normalise_wake_interval_s_bounds_and_bool_gotcha():
        for hostile in (True, False, "120", 120.0, 59, 3601, 0, -1, None, []):
            got = device_config.normalise_wake_interval_s(hostile)
            if got is not None:
                return False, "normalise_wake_interval_s(%r) returned %r, expected None" % (hostile, got)
        for accepted in (60, 3600, 120):
            got = device_config.normalise_wake_interval_s(accepted)
            if got != accepted:
                return False, "normalise_wake_interval_s(%r) returned %r, expected it unchanged" % (accepted, got)
        return True, ""

    check(
        "normalise_wake_interval_s() returns None for True, False (the bool-is-an-int gotcha), a numeric string, a float, and every out-of-[60, 3600] int, and returns 60/3600/120 unchanged",
        _normalise_wake_interval_s_bounds_and_bool_gotcha,
    )

    def _hand_written_hostile_wake_interval_s_yields_none():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                    return False, "%s produced wake_interval_s=%r, expected None" % (label, config["wake_interval_s"])
            with open(path, "w") as fh:
                fh.write('{"wake_interval_s": 120}')
            config = device_config.load_device_config(tmpdir)
            if config["wake_interval_s"] != 120:
                return False, "an in-range wake_interval_s=120 produced %r, expected 120" % (config["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "load_device_config() degrades a hand-written hostile wake_interval_s (JSON true, a numeric string, a float, or the below-minimum 30) to None, and lets an in-range 120 survive unchanged",
        _hand_written_hostile_wake_interval_s_yields_none,
    )

    def _save_wake_interval_s_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, wake_interval_s=120)
            config = device_config.load_device_config(tmpdir)
            if config != {
                "theme": "white", "tracked_runway": "3", "led_enabled": True,
                "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
                "wake_interval_s": 120, "display_enabled": True,
            }:
                return False, "round-trip produced %r" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(wake_interval_s=120) round-trips through load_device_config() as 120, with theme/tracked_runway/led_enabled and all three quiet-hours fields still at their prior (default) values",
        _save_wake_interval_s_round_trips,
    )

    def _save_wake_interval_s_rejects_out_of_bounds_and_bools():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                    return False, "save_device_config(wake_interval_s=%r) did not raise ValueError" % (hostile,)
                with open(path, "rb") as fh:
                    after = fh.read()
                if before != after:
                    return False, "save_device_config(wake_interval_s=%r) changed a pre-existing file's bytes" % (hostile,)
            for boundary in (60, 3600):
                device_config.save_device_config(tmpdir, wake_interval_s=boundary)
                config = device_config.load_device_config(tmpdir)
                if config["wake_interval_s"] != boundary:
                    return False, "save_device_config(wake_interval_s=%r) did not round-trip as %r, got %r" % (
                        boundary, boundary, config["wake_interval_s"],
                    )
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config() rejects wake_interval_s=59, 3601, True, False, '120', and 120.0 with ValueError, leaves a pre-existing, legitimately-saved file byte-identical across every rejection, and accepts the inclusive bounds 60 and 3600",
        _save_wake_interval_s_rejects_out_of_bounds_and_bools,
    )

    def _wake_interval_s_carries_forward_on_unrelated_save():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, wake_interval_s=120)
            device_config.save_device_config(tmpdir, theme="black")
            config = device_config.load_device_config(tmpdir)
            if config["wake_interval_s"] != 120:
                return False, "a theme-only save did not carry a previously-saved wake_interval_s=120 forward, got %r" % (config["wake_interval_s"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a subsequent theme-only save_device_config(theme='black') carries a previously-saved wake_interval_s=120 forward unchanged",
        _wake_interval_s_carries_forward_on_unrelated_save,
    )

    def _normalise_display_enabled_only_accepts_real_bools():
        # 12-01: the bool-is-an-int gotcha from the other direction -
        # isinstance(0, bool) is False, so a JSON 0 is not a valid off value
        # and must degrade to the fail-open DEFAULT_DISPLAY_ENABLED (D-09).
        for hostile in (0, 1, "true", "on", "", None, [], {}, 1.0):
            got = device_config.normalise_display_enabled(hostile)
            if got is not device_config.DEFAULT_DISPLAY_ENABLED:
                return False, "normalise_display_enabled(%r) returned %r, expected DEFAULT_DISPLAY_ENABLED" % (hostile, got)
        if device_config.normalise_display_enabled(True) is not True:
            return False, "normalise_display_enabled(True) did not return True"
        if device_config.normalise_display_enabled(False) is not False:
            return False, "normalise_display_enabled(False) did not return False"
        return True, ""

    check(
        "normalise_display_enabled() degrades int 0, int 1, 'true', 'on', an empty string, None, an empty list, and an empty dict to DEFAULT_DISPLAY_ENABLED, and returns both real booleans unchanged",
        _normalise_display_enabled_only_accepts_real_bools,
    )

    def _hand_written_hostile_display_enabled_yields_true_but_false_survives():
        # 12-01/D-09: a corrupted or hand-edited config must never be the
        # reason a frame goes dark - every hostile on-disk shape degrades to
        # True, while a legitimate False survives untouched.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                    return False, "%s produced display_enabled=%r, expected True (fail-open, D-09)" % (label, config["display_enabled"])
            with open(path, "w") as fh:
                fh.write('{"display_enabled": false}')
            config = device_config.load_device_config(tmpdir)
            if config["display_enabled"] is not False:
                return False, "a hand-written display_enabled=false produced %r, expected it to survive as False" % (config["display_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "load_device_config() degrades a hand-written hostile display_enabled (0, \"false\", null, or a non-dict document) to True so a corrupted config can never darken the frame (D-09), while a legitimate display_enabled=false survives as False",
        _hand_written_hostile_display_enabled_yields_true_but_false_survives,
    )

    def _save_display_enabled_false_round_trips_and_carries_forward():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, display_enabled=False)
            config = device_config.load_device_config(tmpdir)
            if config != {
                "theme": "white", "tracked_runway": "3", "led_enabled": True,
                "quiet_hours_enabled": False, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
                "wake_interval_s": None, "display_enabled": False,
            }:
                return False, "round-trip produced %r" % (config,)
            device_config.save_device_config(tmpdir, theme="black")
            config = device_config.load_device_config(tmpdir)
            if config["display_enabled"] is not False:
                return False, "a theme-only save did not carry a previously-saved display_enabled=False forward, got %r" % (config["display_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config(display_enabled=False) round-trips through load_device_config() as False with all seven other fields still at their prior (default) values, and a subsequent theme-only save carries display_enabled=False forward unchanged",
        _save_display_enabled_false_round_trips_and_carries_forward,
    )

    def _save_display_enabled_rejects_non_bool_and_leaves_file_byte_identical():
        # display_enabled=None is deliberately NOT a rejection case - None
        # means carry forward, matching every other field's contract.
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                    return False, "save_device_config(display_enabled=%r) did not raise ValueError" % (hostile,)
                with open(path, "rb") as fh:
                    after = fh.read()
                if before != after:
                    return False, "save_device_config(display_enabled=%r) changed a pre-existing file's bytes" % (hostile,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "save_device_config() rejects display_enabled='on', 0, 1, 'false', and [] with ValueError and leaves a pre-existing, legitimately-saved file byte-identical across every rejection (display_enabled=None is not a rejection case - it means carry forward)",
        _save_display_enabled_rejects_non_bool_and_leaves_file_byte_identical,
    )

    # --- history_db.py ------------------------------------------------------

    try:
        import server.history_db as history_db
    except ImportError as exc:
        print("FAIL import server.history_db - %r" % (exc,))
        passed_so_far = sum(1 for _, ok in results if ok)
        print("config-history: %d/%d checks pass" % (passed_so_far, EXPECTED_CHECK_COUNT))
        return 1

    def _connect_creates_db_with_wal_and_tables():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            conn = history_db.connect(tmpdir)
            try:
                if not os.path.exists(history_db.history_db_path(tmpdir)):
                    return False, "history.db was not created"
                mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
                if str(mode).lower() != "wal":
                    return False, "journal_mode is %r, expected wal" % (mode,)
                timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
                if timeout_ms != 5000:
                    return False, "busy_timeout is %r, expected 5000" % (timeout_ms,)
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
                for expected in ("runway_events", "device_health", "meta"):
                    if expected not in tables:
                        return False, "table %r missing, found %r" % (expected, tables)
            finally:
                conn.close()
            conn2 = history_db.connect(tmpdir)  # calling connect() twice must not raise
            conn2.close()
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("connect() creates history.db, sets WAL + busy_timeout, creates all three tables, and is idempotent", _connect_creates_db_with_wal_and_tables)

    def _record_and_recent_runway_events():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(conn, ts="2026-08-27T10:00:00+00:00", hex="aaaaaa", callsign="FLIGHT1")
                history_db.record_runway_event(conn, ts="2026-08-27T10:01:00+00:00", hex="bbbbbb", callsign="FLIGHT2")
                history_db.record_runway_event(conn, ts="2026-08-27T10:02:00+00:00", hex="cccccc", callsign="FLIGHT3")
                rows = history_db.recent_runway_events(conn, limit=2)
            hexes = [row["hex"] for row in rows]
            if hexes != ["cccccc", "bbbbbb"]:
                return False, "expected newest-first ['cccccc', 'bbbbbb'], got %r" % (hexes,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("record_runway_event() inserts one row; recent_runway_events(limit=2) returns the two newest, newest first", _record_and_recent_runway_events)

    def _route_source_counts_buckets_correctly():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                for i, source in enumerate(["fresh_hit", "cache_hit", "cache_hit", "miss"]):
                    history_db.record_runway_event(conn, ts="2026-08-27T10:0%d:00+00:00" % i, hex="h%d" % i, route_source=source)
                counts = history_db.route_source_counts(conn, since="2026-08-27T10:00:00+00:00")
            expected = {"fresh_hit": 1, "cache_hit": 2, "miss": 1}
            if counts != expected:
                return False, "expected %r, got %r" % (expected, counts)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("route_source_counts(since=...) returns fresh_hit/cache_hit/miss with counts 1/2/1", _route_source_counts_buckets_correctly)

    def _corroboration_counts_keeps_none_distinct_from_false():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(conn, ts="2026-08-27T11:00:00+00:00", hex="h0", corroborated=True)
                history_db.record_runway_event(conn, ts="2026-08-27T11:01:00+00:00", hex="h1", corroborated=None)
                history_db.record_runway_event(conn, ts="2026-08-27T11:02:00+00:00", hex="h2", corroborated=False)
                counts = history_db.corroboration_counts(conn, since="2026-08-27T11:00:00+00:00")
            expected = {"True": 1, "None": 1, "False": 1}
            if counts != expected:
                return False, "expected %r, got %r" % (expected, counts)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("corroboration_counts(since=...) buckets True/None/False separately, never collapsing None into False", _corroboration_counts_keeps_none_distinct_from_false)

    def _corroborated_unknown_is_readable_back_distinctly():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(conn, ts="2026-08-27T12:00:00+00:00", hex="unk0", corroborated=None)
                history_db.record_runway_event(conn, ts="2026-08-27T12:01:00+00:00", hex="unk1", corroborated=False)
                rows = history_db.recent_runway_events(conn, limit=2)
            by_hex = {row["hex"]: row["corroborated"] for row in rows}
            if by_hex.get("unk0") != "None":
                return False, "corroborated=None was not readable back as the unknown value, got %r" % (by_hex.get("unk0"),)
            if by_hex.get("unk1") != "False":
                return False, "corroborated=False was not readable back as the false value, got %r" % (by_hex.get("unk1"),)
            if by_hex.get("unk0") == by_hex.get("unk1"):
                return False, "the unknown and false corroboration values were not stored distinctly"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a runway_events row written with corroborated unknown is readable back as the unknown value, distinct from false",
        _corroborated_unknown_is_readable_back_distinctly,
    )

    def _hostile_callsign_round_trips_byte_identically():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            hostile_callsign = """<script>alert('x')</script>' OR '1'='1"""
            with history_db.open_db(tmpdir) as conn:
                history_db.record_runway_event(conn, ts="2026-08-27T13:00:00+00:00", hex="hostile1", callsign=hostile_callsign, airline="O'Brien's \"Air\"")
                rows = history_db.recent_runway_events(conn, limit=1)
            if not rows or rows[0]["callsign"] != hostile_callsign:
                return False, "callsign round-tripped as %r, expected byte-identical %r" % (rows[0]["callsign"] if rows else None, hostile_callsign)
            if rows[0]["airline"] != "O'Brien's \"Air\"":
                return False, "airline round-tripped as %r" % (rows[0]["airline"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a callsign containing an HTML angle bracket and a SQL quote round-trips byte-identically through recent_runway_events()",
        _hostile_callsign_round_trips_byte_identically,
    )

    def _meta_get_set_overwrites_not_duplicates():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                if history_db.get_meta(conn, "absent") is not None:
                    return False, "get_meta() on an absent key did not return None"
                history_db.set_meta(conn, "k", "v")
                if history_db.get_meta(conn, "k") != "v":
                    return False, "get_meta() after set_meta() did not return the stored value"
                history_db.set_meta(conn, "k", "v2")
                if history_db.get_meta(conn, "k") != "v2":
                    return False, "a second set_meta() on the same key did not overwrite"
                count = conn.execute("SELECT COUNT(*) FROM meta WHERE key = ?", ("k",)).fetchone()[0]
                if count != 1:
                    return False, "expected exactly one meta row for key 'k', found %d" % (count,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("set_meta()/get_meta() round-trip, absent key reads None, a second set_meta() overwrites rather than duplicating", _meta_get_set_overwrites_not_duplicates)

    def _ingest_caddy_battery_log_is_idempotent():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
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
                return False, "first ingest inserted %d rows, expected 2" % (first_count,)
            if len(rows_after_first) != 2:
                return False, "expected 2 device_health rows after first ingest, found %d" % (len(rows_after_first),)
            if second_count != 0:
                return False, "second ingest over an unchanged file inserted %d rows, expected 0" % (second_count,)
            if len(rows_after_second) != 2:
                return False, "row count changed after a no-op second ingest: %d" % (len(rows_after_second),)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("ingest_caddy_battery_log() inserts exactly 2 rows from a mixed fixture, and 0 more on an unchanged re-run", _ingest_caddy_battery_log_is_idempotent)

    def _daily_battery_averages_groups_excludes_and_bounds_correctly():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            with history_db.open_db(tmpdir) as conn:
                if history_db.daily_battery_averages(conn) != []:
                    return False, "an empty database must return an empty list"

                # Three consecutive days, three readings each, unambiguous means.
                day_dates = ["2026-09-02", "2026-09-01", "2026-08-31"]
                day_values = [[4000, 4100, 4200], [4001, 4101, 4201], [4002, 4102, 4202]]
                for day_date, values in zip(day_dates, day_values):
                    for hour, mv in zip((2, 14, 23), values):
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
                return False, "expected exactly 3 day buckets inside the window, got %r" % (bounded,)
            days = [row["ts"] for row in bounded]
            if days != ["2026-09-02", "2026-09-01", "2026-08-31"]:
                return False, "expected newest-first UTC calendar days, got %r" % (days,)
            for row, expected_mean in zip(bounded, (4100, 4101, 4102)):
                if not isinstance(row["battery_mv"], int) or isinstance(row["battery_mv"], bool):
                    return False, "battery_mv must be a real int: %r" % (row,)
                if row["battery_mv"] != expected_mean:
                    return False, "daily mean wrong: %r expected %d" % (row, expected_mean)
                if row["reading_count"] != 3:
                    return False, "reading_count must be the contributing reading count: %r" % (row,)
            plotted = [row["battery_mv"] for row in bounded]
            if 9999 in plotted:
                return False, "an unparseable-timestamp row must not form a bucket"
            if 1234 in plotted:
                return False, "a row older than the cutoff must be excluded"
            if None in [row["ts"] for row in bounded]:
                return False, "no NULL day bucket may survive"
            if len(unbounded) != 4 or unbounded[-1]["battery_mv"] != 1234:
                return False, "since=None must return every day including the out-of-window one, got %r" % (unbounded,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "daily_battery_averages() groups by UTC calendar day, rounds the mean, orders newest-first, "
        "honours since=, and excludes NULL-battery and unparseable-timestamp rows (260902-l0b)",
        _daily_battery_averages_groups_excludes_and_bounds_correctly,
    )

    def _all_sql_uses_placeholders_not_string_formatting():
        src_path = os.path.join(REPO_ROOT, "server", "history_db.py")
        with open(src_path) as fh:
            src = fh.read()
        if re.search(r'execute\([^)]*%s.*%', src):
            return False, "found a %-formatted string passed to execute()"
        if 'execute(f"' in src or "execute(f'" in src:
            return False, "found an f-string passed to execute()"
        return True, ""

    check("every history_db.py execute() call uses ? placeholders, never %-formatting or an f-string", _all_sql_uses_placeholders_not_string_formatting)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("config-history: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
