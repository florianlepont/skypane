#!/usr/bin/env python3
"""Contract tests for server/plane/colour_rules.py - the phase 15
per-flight colour-rule registry and D-13 resolver
(15-VALIDATION.md Wave 0 item 1).

Because colour_rules.py keeps a process-global cache, every resolver test
primes it explicitly with set_colour_rules_state_dir() and resets it
unconditionally afterwards (via try/finally), so test order can never leak
state between tests.
"""
import json
import os
import string
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.device_config as device_config  # noqa: E402
import server.plane.colour_rules as c  # noqa: E402


def _empty_registry():
    return {k: {} for k in c.RULE_KINDS}


def test_missing_state_dir_returns_empty_registry_shape():
    """load_colour_rules() on a nonexistent state dir returns the empty registry shape without raising."""
    result = c.load_colour_rules("/nonexistent/skypane-cr-dir")
    assert result == _empty_registry(), "expected the empty registry shape, got %r" % (result,)


def test_invalid_json_returns_empty_registry_shape(tmp_path):
    """load_colour_rules() on a file containing invalid JSON returns the empty registry shape."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        fh.write("not json")
    result = c.load_colour_rules(tmp_path)
    assert result == _empty_registry(), "expected the empty registry shape, got %r" % (result,)


def test_non_dict_top_level_returns_empty_registry_shape(tmp_path):
    """load_colour_rules() on a JSON list (non-dict top level) returns the empty registry shape."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        json.dump([1, 2, 3], fh)
    result = c.load_colour_rules(tmp_path)
    assert result == _empty_registry(), "expected the empty registry shape, got %r" % (result,)


def test_non_dict_kind_value_returns_empty_registry_shape(tmp_path):
    """load_colour_rules() on {'callsign': 5} (non-dict kind value) returns the empty registry shape."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        json.dump({"callsign": 5}, fh)
    result = c.load_colour_rules(tmp_path)
    assert result == _empty_registry(), "expected the empty registry shape, got %r" % (result,)


def test_lowercase_callsign_key_normalised_on_read_and_round_trips(tmp_path):
    """load_colour_rules() normalises a lowercase callsign key to uppercase and round-trips a valid entry."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        json.dump({"callsign": {"afr1234": {"theme_id": "white", "created_at": "2026-01-01T00:00:00+00:00"}}}, fh)
    result = c.load_colour_rules(tmp_path)
    expected = {"AFR1234": {"theme_id": "white", "created_at": "2026-01-01T00:00:00+00:00"}}
    assert result["callsign"] == expected, "expected %r, got %r" % (expected, result["callsign"])


def test_lowercase_hex_key_normalised_on_read(tmp_path):
    """load_colour_rules() normalises a lowercase hex key to uppercase on read."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        json.dump({"hex": {"39de4a": {"theme_id": "white", "created_at": "t"}}}, fh)
    result = c.load_colour_rules(tmp_path)
    assert "39DE4A" in result["hex"], "expected key '39DE4A' in %r" % (result["hex"],)


def test_malformed_entries_dropped_on_read(tmp_path, tmp_path_factory):
    """load_colour_rules() drops a path-traversal-shaped callsign key, a 4-letter prefix, a non-hex hex key, and an unregistered theme_id."""
    with open(c.colour_rules_path(tmp_path), "w") as fh:
        json.dump({"callsign": {"../x": {"theme_id": "white", "created_at": "t"}}}, fh)
    result_traversal = c.load_colour_rules(tmp_path)
    assert result_traversal == _empty_registry(), (
        "traversal-shaped callsign key: expected empty registry, got %r" % (result_traversal,)
    )

    tmp2 = tmp_path_factory.mktemp("cr-4letter")
    with open(c.colour_rules_path(tmp2), "w") as fh:
        json.dump({"prefix": {"AFRX": {"theme_id": "white", "created_at": "t"}}}, fh)
    result_4letter = c.load_colour_rules(tmp2)
    assert result_4letter == _empty_registry(), (
        "4-letter prefix key: expected empty registry, got %r" % (result_4letter,)
    )

    tmp3 = tmp_path_factory.mktemp("cr-badhex")
    with open(c.colour_rules_path(tmp3), "w") as fh:
        json.dump({"hex": {"ZZZZZZ": {"theme_id": "white", "created_at": "t"}}}, fh)
    result_bad_hex = c.load_colour_rules(tmp3)
    assert result_bad_hex == _empty_registry(), (
        "non-hex hex key: expected empty registry, got %r" % (result_bad_hex,)
    )

    tmp4 = tmp_path_factory.mktemp("cr-badtheme")
    with open(c.colour_rules_path(tmp4), "w") as fh:
        json.dump({"callsign": {"AFR1234": {"theme_id": "chartreuse", "created_at": "t"}}}, fh)
    result_bad_theme = c.load_colour_rules(tmp4)
    assert result_bad_theme == _empty_registry(), (
        "unregistered theme_id: expected empty registry, got %r" % (result_bad_theme,)
    )


def test_add_rule_round_trips_with_non_empty_created_at(tmp_path):
    """add_rule() returns ADD_OK_NEW and round-trips through load_colour_rules() with a non-empty created_at."""
    result = c.add_rule(tmp_path, "callsign", "afr1234", "white")
    assert result == c.ADD_OK_NEW, "add_rule() returned %r, expected ADD_OK_NEW" % (result,)
    registry = c.load_colour_rules(tmp_path)
    entry = registry["callsign"].get("AFR1234")
    assert entry is not None, "AFR1234 missing from registry after add_rule(): %r" % (registry,)
    assert entry.get("theme_id") == "white", "theme_id %r != 'white'" % (entry.get("theme_id"),)
    assert entry.get("created_at"), "created_at is falsy: %r" % (entry.get("created_at"),)


def test_add_rule_rejects_unrecognised_kind(tmp_path):
    """add_rule() rejects an unrecognised kind with ADD_REJECTED_KIND."""
    result = c.add_rule(tmp_path, "airframe", "AFR1234", "white")
    assert result == c.ADD_REJECTED_KIND, "expected ADD_REJECTED_KIND, got %r" % (result,)


def test_add_rule_rejects_bad_key(tmp_path, tmp_path_factory):
    """add_rule() rejects a 4-letter prefix and a 5-character hex value with ADD_REJECTED_KEY."""
    prefix_result = c.add_rule(tmp_path, "prefix", "AFRX", "white")
    assert prefix_result == c.ADD_REJECTED_KEY, "4-letter prefix: expected ADD_REJECTED_KEY, got %r" % (prefix_result,)
    tmp2 = tmp_path_factory.mktemp("cr-badkey")
    hex_result = c.add_rule(tmp2, "hex", "39DE4", "white")
    assert hex_result == c.ADD_REJECTED_KEY, "5-char hex: expected ADD_REJECTED_KEY, got %r" % (hex_result,)


def test_add_rule_rejects_unregistered_theme(tmp_path):
    """add_rule() rejects an unregistered theme id with ADD_REJECTED_THEME."""
    result = c.add_rule(tmp_path, "callsign", "AFR1234", "chartreuse")
    assert result == c.ADD_REJECTED_THEME, "expected ADD_REJECTED_THEME, got %r" % (result,)


def test_delete_rule_returns_true_once_then_false(tmp_path):
    """delete_rule() returns True once then False on a repeated call, without raising."""
    c.add_rule(tmp_path, "callsign", "AFR1234", "white")
    first = c.delete_rule(tmp_path, "callsign", "AFR1234")
    second = c.delete_rule(tmp_path, "callsign", "AFR1234")
    assert first is True, "first delete_rule() call returned %r, expected True" % (first,)
    assert second is False, "second delete_rule() call returned %r, expected False" % (second,)


def test_rule_rows_ordered_and_skips_malformed_entry():
    """rule_rows() returns (kind, value, theme_id, created_at) tuples ordered by kind then value, skipping a malformed entry."""
    registry = {
        "callsign": {"AFR1234": {"theme_id": "white", "created_at": "t1"}},
        "hex": {"39DE4A": {"theme_id": "blue", "created_at": "t2"}, "AAAAAA": "not a dict"},
        "prefix": {"AFR": {"theme_id": "red", "created_at": "t3"}},
    }
    rows = c.rule_rows(registry)
    expected = [
        ("callsign", "AFR1234", "white", "t1"),
        ("hex", "39DE4A", "blue", "t2"),
        ("prefix", "AFR", "red", "t3"),
    ]
    assert rows == expected, "expected %r, got %r" % (expected, rows)


def test_cache_reset_to_none_falls_through_to_base_theme():
    """set_colour_rules_state_dir(None) clears the cache and resolve_effective_theme_id() falls through to the base theme."""
    try:
        c.set_colour_rules_state_dir(None)
        result = c.resolve_effective_theme_id(
            "departing", {"callsign": "AFR1234", "hex": "39de4a"}, {"theme": "white", "theme_arriving": None})
    finally:
        c.set_colour_rules_state_dir(None)
    assert result == "white", "expected 'white', got %r" % (result,)


def test_hostile_input_sweep_rejected_write_and_read(tmp_path, tmp_path_factory):
    """add_rule() rejects every hostile value in the sweep (write-side) and load_colour_rules() drops the same shapes written directly to disk (read-side), for all three kinds (T-15-01)."""
    hostile_by_kind = {
        "callsign": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "AFR123456"],
        "hex": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "39DE4", "39DE4Z"],
        "prefix": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "AFRX", "AF"],
    }
    for kind, hostile_values in hostile_by_kind.items():
        for value in hostile_values:
            result = c.add_rule(tmp_path, kind, value, "white")
            assert isinstance(result, str) and result.startswith("rejected"), (
                "add_rule(tmp, %r, %r, 'white') returned %r, expected some ADD_REJECTED_* value" % (kind, value, result)
            )
    registry_after = c.load_colour_rules(tmp_path)
    assert registry_after == _empty_registry(), (
        "registry not empty after the write-side hostile-input sweep: %r" % (registry_after,)
    )

    # Read-side: write the hostile string shapes directly to disk (only the
    # string-typed ones make valid JSON dict keys) and confirm they are all
    # dropped on read too.
    tmp2 = tmp_path_factory.mktemp("cr-hostile-read")
    hostile_string_keys = {
        "callsign": ["../x", "a/b", "a\\b", "", "   ", "x" * 400, "AFR123456"],
        "hex": ["../x", "a/b", "a\\b", "", "   ", "39DE4", "39DE4Z"],
        "prefix": ["../x", "a/b", "a\\b", "", "   ", "AFRX", "AF"],
    }
    on_disk = {}
    for kind, keys in hostile_string_keys.items():
        on_disk[kind] = {key: {"theme_id": "white", "created_at": "t"} for key in keys}
    with open(c.colour_rules_path(tmp2), "w") as fh:
        json.dump(on_disk, fh)
    registry_from_disk = c.load_colour_rules(tmp2)
    assert registry_from_disk == _empty_registry(), (
        "registry not empty after the read-side hostile-input sweep: %r" % (registry_from_disk,)
    )


def test_add_rule_distinguishes_new_from_replaced_and_enforces_cap(tmp_path, tmp_path_factory):
    """add_rule() distinguishes ADD_OK_NEW from ADD_OK_REPLACED (a replace is not growth) and enforces COLOUR_RULE_MAX_ENTRIES only against new keys (D-09)."""
    first = c.add_rule(tmp_path, "callsign", "AFR1234", "white")
    assert first == c.ADD_OK_NEW, "first add_rule() returned %r, expected ADD_OK_NEW" % (first,)
    second = c.add_rule(tmp_path, "callsign", "AFR1234", "black")
    assert second == c.ADD_OK_REPLACED, "second add_rule() (same key) returned %r, expected ADD_OK_REPLACED" % (second,)
    registry = c.load_colour_rules(tmp_path)
    assert registry["callsign"]["AFR1234"]["theme_id"] == "black", (
        "expected the replaced theme_id 'black', got %r" % (registry["callsign"]["AFR1234"]["theme_id"],)
    )
    total_entries = sum(len(registry[k]) for k in c.RULE_KINDS)
    assert total_entries == 1, "expected exactly 1 entry after a replace (not growth), got %d" % (total_entries,)

    tmp2 = tmp_path_factory.mktemp("cr-cap")
    prefixes = []
    for a in string.ascii_uppercase:
        for b in string.ascii_uppercase:
            if len(prefixes) >= c.COLOUR_RULE_MAX_ENTRIES:
                break
            prefixes.append("Z" + a + b)
        if len(prefixes) >= c.COLOUR_RULE_MAX_ENTRIES:
            break
    assert len(prefixes) == c.COLOUR_RULE_MAX_ENTRIES, (
        "test setup failure: only generated %d distinct prefixes" % (len(prefixes),)
    )
    for pfx in prefixes:
        result = c.add_rule(tmp2, "prefix", pfx, "white")
        assert result == c.ADD_OK_NEW, "filling the cap: add_rule(%r, ...) returned %r" % (pfx, result)
    new_result = c.add_rule(tmp2, "prefix", "AAA", "white")
    assert new_result == c.ADD_REJECTED_FULL, (
        "expected ADD_REJECTED_FULL for a new prefix at the cap, got %r" % (new_result,)
    )
    overwrite_result = c.add_rule(tmp2, "prefix", prefixes[0], "black")
    assert overwrite_result == c.ADD_OK_REPLACED, (
        "expected ADD_OK_REPLACED re-adding an existing prefix at the cap, got %r" % (overwrite_result,)
    )


def test_no_stray_tmp_file_after_add_and_delete(tmp_path):
    """no colour_rules.json.tmp file remains after a successful add_rule() or delete_rule() (atomicity proof)."""
    add_result = c.add_rule(tmp_path, "callsign", "AFR1234", "white")
    assert add_result == c.ADD_OK_NEW, "setup failure: add_rule() returned %r" % (add_result,)
    stray_after_add = [f for f in os.listdir(tmp_path) if ".tmp" in f]
    assert not stray_after_add, (
        "stray .tmp file(s) left behind after a successful add_rule(): %r" % (stray_after_add,)
    )
    delete_result = c.delete_rule(tmp_path, "callsign", "AFR1234")
    assert delete_result is True, "setup failure: delete_rule() returned %r" % (delete_result,)
    stray_after_delete = [f for f in os.listdir(tmp_path) if ".tmp" in f]
    assert not stray_after_delete, (
        "stray .tmp file(s) left behind after a successful delete_rule(): %r" % (stray_after_delete,)
    )


def test_concurrent_add_rule_calls_lose_no_updates(tmp_path):
    """20 concurrent add_rule() calls for 20 distinct prefixes (ThreadingHTTPServer's real concurrency shape) all persist durably with no lost update and no stray .tmp file left behind (T-15-02)."""
    values = ["AA%s" % chr(ord("A") + i) for i in range(20)]
    errors = []

    def _worker(value):
        try:
            result = c.add_rule(tmp_path, "prefix", value, "white")
            if result != c.ADD_OK_NEW:
                errors.append((value, result))
        except Exception as exc:  # never let a worker's exception vanish silently
            errors.append((value, repr(exc)))

    threads = [threading.Thread(target=_worker, args=(value,)) for value in values]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, "worker error(s)/rejection(s): %r" % (errors,)

    registry = c.load_colour_rules(tmp_path)
    missing = [value for value in values if value not in registry["prefix"]]
    assert not missing, "lost update(s) - missing prefixes after concurrent add_rule() calls: %r" % (missing,)

    stray = [f for f in os.listdir(tmp_path) if ".tmp" in f]
    assert not stray, "stray .tmp file(s) left behind after concurrent writes: %r" % (stray,)


def _resolver_with(tmp_path_factory, state_dir_registry, state, flight, device_cfg, calendar_theme_id=None):
    try:
        if state_dir_registry is None:
            c.set_colour_rules_state_dir(None)
        else:
            tmp = tmp_path_factory.mktemp("cr-resolver")
            for kind, value, theme_id in state_dir_registry:
                add_result = c.add_rule(tmp, kind, value, theme_id)
                assert add_result in (c.ADD_OK_NEW, c.ADD_OK_REPLACED), (
                    "setup failure: add_rule(%r, %r, %r, %r) returned %r" % (tmp, kind, value, theme_id, add_result)
                )
            c.set_colour_rules_state_dir(tmp)
        return c.resolve_effective_theme_id(state, flight, device_cfg, calendar_theme_id=calendar_theme_id)
    finally:
        c.set_colour_rules_state_dir(None)


FLIGHT_AFR = {"callsign": "AFR1234", "hex": "39de4a"}


def test_resolver_row1_no_rule_no_override_arriving(tmp_path_factory):
    """resolver truth table row 1: no rule, theme_arriving is None, state 'arriving' -> base theme."""
    result = _resolver_with(tmp_path_factory, None, "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": None})
    assert result == "white", "row 1: expected 'white', got %r" % (result,)


def test_resolver_row2_no_rule_override_arriving(tmp_path_factory):
    """resolver truth table row 2: no rule, theme_arriving set, state 'arriving' -> the override."""
    result = _resolver_with(tmp_path_factory, None, "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"})
    assert result == "blue", "row 2: expected 'blue', got %r" % (result,)


def test_resolver_row3_no_rule_override_departing(tmp_path_factory):
    """resolver truth table row 3: no rule, theme_arriving set, state 'departing' -> base theme."""
    result = _resolver_with(tmp_path_factory, None, "departing", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"})
    assert result == "white", "row 3: expected 'white', got %r" % (result,)


def test_resolver_row4_prefix_rule_no_override(tmp_path_factory):
    """resolver truth table row 4: a matching prefix rule, no override -> the rule's theme."""
    result = _resolver_with(tmp_path_factory, [("prefix", "AFR", "red")], "departing", FLIGHT_AFR, {"theme": "white"})
    assert result == "red", "row 4: expected 'red', got %r" % (result,)


def test_resolver_row5_hex_beats_prefix(tmp_path_factory):
    """resolver truth table row 5: a matching hex rule and a matching prefix rule -> the hex rule's theme."""
    result = _resolver_with(
        tmp_path_factory, [("hex", "39DE4A", "green"), ("prefix", "AFR", "red")], "departing", FLIGHT_AFR, {"theme": "white"})
    assert result == "green", "row 5: expected 'green', got %r" % (result,)


def test_resolver_row6_callsign_beats_hex(tmp_path_factory):
    """resolver truth table row 6: a matching callsign rule and a matching hex rule -> the callsign rule's theme."""
    result = _resolver_with(
        tmp_path_factory, [("callsign", "AFR1234", "blue"), ("hex", "39DE4A", "green")], "departing", FLIGHT_AFR, {"theme": "white"})
    assert result == "blue", "row 6: expected 'blue', got %r" % (result,)


def test_resolver_row7_rule_beats_override(tmp_path_factory):
    """resolver truth table row 7: a matching rule of any kind AND theme_arriving set with state 'arriving' -> the rule's theme (a rule beats the override, D-09)."""
    result = _resolver_with(
        tmp_path_factory, [("prefix", "AFR", "red")], "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"})
    assert result == "red", "row 7: expected 'red', got %r" % (result,)


def test_resolver_never_raises_on_defensive_inputs():
    """resolve_effective_theme_id() never raises for flight=None/{}/non-dict, a None callsign/hex, or a device_cfg with no theme_arriving key, falling through to the base theme."""
    c.set_colour_rules_state_dir(None)
    cases = [
        (None, {"theme": "white"}),
        ({}, {"theme": "white"}),
        ("not a dict", {"theme": "white"}),
        ({"callsign": None, "hex": None}, {"theme": "white"}),
        (FLIGHT_AFR, {"theme": "white"}),  # no theme_arriving key at all
    ]
    for flight, device_cfg in cases:
        result = c.resolve_effective_theme_id("arriving", flight, device_cfg)
        assert result == "white", "flight=%r, device_cfg=%r: expected 'white', got %r" % (flight, device_cfg, result)


def test_resolver_ignores_tampered_cache_theme_id(tmp_path):
    """resolve_effective_theme_id() ignores a cached entry whose theme_id is not a member of device_config.THEMES rather than returning it (T-15-05)."""
    try:
        add_result = c.add_rule(tmp_path, "callsign", "AFR1234", "white")
        assert add_result == c.ADD_OK_NEW, "setup failure: add_rule() returned %r" % (add_result,)
        c.set_colour_rules_state_dir(tmp_path)
        c._cached_rules["callsign"]["AFR1234"]["theme_id"] = "not-a-real-theme"
        result = c.resolve_effective_theme_id("departing", {"callsign": "AFR1234"}, {"theme": "black"})
        assert result == "black", (
            "expected the tampered entry to be ignored and fall through to 'black', got %r" % (result,)
        )
        assert "not-a-real-theme" not in device_config.THEMES, (
            "test setup invalid: 'not-a-real-theme' is somehow a real theme id"
        )
    finally:
        c.set_colour_rules_state_dir(None)


# --- Plan 16-06: D-02's calendar_theme_id precedence -----------------------

CAL_THEME = "band_red_field"  # distinct from any theme used in the truth table rows above
RULE_THEME_FOR_PRECEDENCE = "red"
if CAL_THEME not in device_config.THEMES or CAL_THEME == RULE_THEME_FOR_PRECEDENCE:
    raise AssertionError("test setup invalid: CAL_THEME must be a real, distinct theme id")


def test_calendar_beats_exact_callsign_rule(tmp_path_factory):
    """resolve_effective_theme_id() D-02: a calendar_theme_id beats even a matching exact-callsign rule (the accepted consequence)."""
    result = _resolver_with(
        tmp_path_factory,
        [("callsign", "AFR1234", RULE_THEME_FOR_PRECEDENCE)], "departing", FLIGHT_AFR,
        {"theme": "white"}, calendar_theme_id=CAL_THEME)
    assert result == CAL_THEME, (
        "D-02's accepted consequence is that a calendar match beats even an exact-callsign rule; "
        "expected %r, got %r" % (CAL_THEME, result)
    )


def test_calendar_beats_hex_rule(tmp_path_factory):
    """resolve_effective_theme_id() D-02: a calendar_theme_id beats a matching hex rule."""
    result = _resolver_with(
        tmp_path_factory,
        [("hex", "39DE4A", RULE_THEME_FOR_PRECEDENCE)], "departing", FLIGHT_AFR,
        {"theme": "white"}, calendar_theme_id=CAL_THEME)
    assert result == CAL_THEME, "expected the calendar value to beat a matching hex rule, got %r" % (result,)


def test_calendar_beats_prefix_rule(tmp_path_factory):
    """resolve_effective_theme_id() D-02: a calendar_theme_id beats a matching prefix rule."""
    result = _resolver_with(
        tmp_path_factory,
        [("prefix", "AFR", RULE_THEME_FOR_PRECEDENCE)], "departing", FLIGHT_AFR,
        {"theme": "white"}, calendar_theme_id=CAL_THEME)
    assert result == CAL_THEME, "expected the calendar value to beat a matching prefix rule, got %r" % (result,)


def test_calendar_beats_arrivals_override(tmp_path_factory):
    """resolve_effective_theme_id() D-02: a calendar_theme_id beats the arrivals override (theme_arriving) on an arriving state."""
    result = _resolver_with(
        tmp_path_factory,
        None, "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": RULE_THEME_FOR_PRECEDENCE},
        calendar_theme_id=CAL_THEME)
    assert result == CAL_THEME, "expected the calendar value to beat the arrivals override, got %r" % (result,)


def test_backward_compatible_three_positional_call(tmp_path_factory):
    """resolve_effective_theme_id() is byte-for-byte identical whether calendar_theme_id is omitted or passed explicitly as None, across a matrix of rule/override configurations."""
    matrix = [
        (None, "departing", FLIGHT_AFR, {"theme": "white"}),
        (None, "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"}),
        (None, "departing", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"}),
        ([("prefix", "AFR", "red")], "departing", FLIGHT_AFR, {"theme": "white"}),
        ([("hex", "39DE4A", "green"), ("prefix", "AFR", "red")], "departing", FLIGHT_AFR, {"theme": "white"}),
        ([("callsign", "AFR1234", "blue"), ("hex", "39DE4A", "green")], "departing", FLIGHT_AFR, {"theme": "white"}),
        ([("prefix", "AFR", "red")], "arriving", FLIGHT_AFR, {"theme": "white", "theme_arriving": "blue"}),
    ]
    for state_dir_registry, state, flight, device_cfg in matrix:
        three_arg = _resolver_with(tmp_path_factory, state_dir_registry, state, flight, device_cfg)
        four_arg_none = _resolver_with(tmp_path_factory, state_dir_registry, state, flight, device_cfg, calendar_theme_id=None)
        assert three_arg == four_arg_none, (
            "state_dir_registry=%r state=%r: three-arg result %r != four-arg (calendar_theme_id=None) result %r" % (
                state_dir_registry, state, three_arg, four_arg_none)
        )


def test_tampered_calendar_theme_id_ignored(tmp_path):
    """resolve_effective_theme_id() ignores a calendar_theme_id that is not a member of device_config.THEMES, falling through to the matching rule rather than returning it or the base theme (T-16-TAMPER)."""
    try:
        add_result = c.add_rule(tmp_path, "callsign", "AFR1234", RULE_THEME_FOR_PRECEDENCE)
        assert add_result == c.ADD_OK_NEW, "setup failure: add_rule() returned %r" % (add_result,)
        c.set_colour_rules_state_dir(tmp_path)
        for bad in ("not-a-real-theme", "", 1, True, {}, []):
            result = c.resolve_effective_theme_id(
                "departing", FLIGHT_AFR, {"theme": "white"}, calendar_theme_id=bad)
            assert result == RULE_THEME_FOR_PRECEDENCE, (
                "calendar_theme_id=%r: expected fall-through to the rule's theme %r, got %r" % (
                    bad, RULE_THEME_FOR_PRECEDENCE, result)
            )
    finally:
        c.set_colour_rules_state_dir(None)

