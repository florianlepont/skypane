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

EXPECTED_CHECK_COUNT = 25


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
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True}:
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
                if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True}:
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
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True}:
                return False, "hostile input produced %r, expected defaults for both keys" % (config,)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("load_device_config() replaces an unrecognised theme/runway value with the default rather than passing it through", _hostile_values_yield_defaults)

    def _save_then_load_round_trips():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="02-20")
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "sky", "tracked_runway": "02-20", "led_enabled": True}:
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
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="3")
            if os.path.exists(device_config.device_config_path(tmpdir) + ".tmp"):
                return False, "a .tmp file survived a successful save"
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check("no .tmp file remains in the state directory after a successful save", _no_tmp_survives_a_successful_save)

    def _hostile_hand_edit_after_a_real_save_still_yields_defaults():
        tmpdir = tempfile.mkdtemp(prefix="skypane-config-history-")
        try:
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="02-20")
            path = device_config.device_config_path(tmpdir)
            with open(path, "w") as fh:
                fh.write('{"theme": "sky/../x", "tracked_runway": "3; DROP TABLE"}')
            config = device_config.load_device_config(tmpdir)
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": True}:
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
            if config != {"theme": "white", "tracked_runway": "3", "led_enabled": False}:
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
            device_config.save_device_config(tmpdir, theme="sky", tracked_runway="3", led_enabled=True)
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
            device_config.save_device_config(tmpdir, theme="sky")
            config = device_config.load_device_config(tmpdir)
            if config["led_enabled"] is not False:
                return False, "a theme-only save did not carry a previously-saved led_enabled=False forward, got %r" % (config["led_enabled"],)
            return True, ""
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    check(
        "a subsequent theme-only save_device_config(theme='sky') carries a previously-saved led_enabled=False forward unchanged",
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
        expected_keys = {"departing_index", "arriving_index", "ink_index", "label"}
        for theme_id, entry in device_config.THEMES.items():
            if set(entry) != expected_keys:
                return False, "theme %r has keys %r, expected exactly %r" % (theme_id, set(entry), expected_keys)
            for key in ("departing_index", "arriving_index", "ink_index"):
                if entry[key] not in valid_indices:
                    return False, "theme %r key %r has value %r, not a real panel_format.IDX_* index" % (theme_id, key, entry[key])
            if not isinstance(entry["label"], str) or not entry["label"]:
                return False, "theme %r label %r is not a non-empty string" % (theme_id, entry["label"])
        return True, ""

    check(
        "every THEMES entry carries exactly the four contract keys, real panel_format.IDX_* index values, and a non-empty label",
        _theme_registry_shape_is_correct,
    )

    def _single_colour_contract_for_new_themes_and_sky_differs():
        for theme_id in ("white", "black", "yellow", "red"):
            entry = device_config.THEMES[theme_id]
            if entry["departing_index"] != entry["arriving_index"]:
                return False, "theme %r is not single-colour: departing_index=%r arriving_index=%r" % (
                    theme_id, entry["departing_index"], entry["arriving_index"],
                )
        sky = device_config.THEMES["sky"]
        if sky["departing_index"] == sky["arriving_index"]:
            return False, "sky unexpectedly became single-colour: departing_index=%r arriving_index=%r" % (
                sky["departing_index"], sky["arriving_index"],
            )
        return True, ""

    check(
        "white/black/yellow/red are single-colour (departing_index == arriving_index); sky remains two-tone (they still differ)",
        _single_colour_contract_for_new_themes_and_sky_differs,
    )

    def _ink_contrast_pairing_is_correct():
        expected = {
            "white": (panel_format.IDX_WHITE, panel_format.IDX_BLACK),
            "yellow": (panel_format.IDX_YELLOW, panel_format.IDX_BLACK),
            "black": (panel_format.IDX_BLACK, panel_format.IDX_WHITE),
            "red": (panel_format.IDX_RED, panel_format.IDX_WHITE),
        }
        for theme_id, (bg, ink) in expected.items():
            entry = device_config.THEMES[theme_id]
            if entry["departing_index"] != bg or entry["ink_index"] != ink:
                return False, "theme %r expected background %r / ink %r, got background %r / ink %r" % (
                    theme_id, bg, ink, entry["departing_index"], entry["ink_index"],
                )
        return True, ""

    check(
        "White/Yellow carry black ink and Black/Red carry white ink, pinned as an explicit id-to-(background,ink) mapping",
        _ink_contrast_pairing_is_correct,
    )

    def _default_theme_and_labels_are_correct():
        if device_config.DEFAULT_THEME_ID != "white":
            return False, "DEFAULT_THEME_ID is %r, expected 'white'" % (device_config.DEFAULT_THEME_ID,)
        if device_config.DEFAULT_THEME_ID not in device_config.THEMES:
            return False, "DEFAULT_THEME_ID %r is not a member of THEMES" % (device_config.DEFAULT_THEME_ID,)
        expected_labels = {"white": "White", "black": "Black", "yellow": "Yellow", "red": "Red", "sky": "Sky"}
        for theme_id, label in expected_labels.items():
            got = device_config.theme_label(theme_id)
            if got != label:
                return False, "theme_label(%r) returned %r, expected %r" % (theme_id, got, label)
        if "(default)" in device_config.theme_label("sky"):
            return False, "sky's label still carries the retired '(default)' suffix"
        return True, ""

    check(
        "DEFAULT_THEME_ID is 'white' and a THEMES member; theme_label() returns the exact plain label for all five ids, with Sky's parenthetical suffix gone",
        _default_theme_and_labels_are_correct,
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
