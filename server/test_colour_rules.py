#!/usr/bin/env python3
"""Contract harness for server/plane/colour_rules.py - the phase 15
per-flight colour-rule registry and D-13 resolver
(15-VALIDATION.md Wave 0 item 1).

Stdlib-only, plus the module under test (server.plane.colour_rules) and
its own dependency (server.device_config). Every fixture is a
tempfile.TemporaryDirectory(), never a shared/real state dir. Exits 0
only when every check below passes; any failure (or exception - none is
ever swallowed into a pass) exits 1.

Because colour_rules.py keeps a process-global cache, every resolver
check primes it explicitly with set_colour_rules_state_dir() and resets
it unconditionally afterwards (via try/finally), so check order can never
leak state between checks.

Usage:
    server/.venv/bin/python3 server/test_colour_rules.py
"""
import json
import os
import string
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Initial value for this file, introduced by phase 15 plan 01. Re-derived
# by RUNNING the harness (not by arithmetic), per this repo's own
# documented discipline (see the ledger comment above
# companion/test_status_pages.py's own EXPECTED_CHECK_COUNT and
# server/test_manual_resolutions.py's own EXPECTED_CHECK_COUNT).
EXPECTED_CHECK_COUNT = 27


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
        import server.plane.colour_rules as c
    except ImportError as exc:
        print("FAIL import server.plane.colour_rules - %r" % (exc,))
        print("colour_rules: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    try:
        import server.device_config as device_config
    except ImportError as exc:
        print("FAIL import server.device_config - %r" % (exc,))
        print("colour_rules: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    def _empty_registry():
        return {k: {} for k in c.RULE_KINDS}

    # 1. Missing state dir degrades to the empty registry shape, never raises.
    def _missing_state_dir():
        result = c.load_colour_rules("/nonexistent/skypane-cr-dir")
        if result != _empty_registry():
            return False, "expected the empty registry shape, got %r" % (result,)
        return True, ""
    check("load_colour_rules() on a nonexistent state dir returns the empty registry shape without raising", _missing_state_dir)

    # 2. Non-JSON file content degrades to the empty registry shape.
    def _not_json():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                fh.write("not json")
            result = c.load_colour_rules(tmp)
        if result != _empty_registry():
            return False, "expected the empty registry shape, got %r" % (result,)
        return True, ""
    check("load_colour_rules() on a file containing invalid JSON returns the empty registry shape", _not_json)

    # 3. A JSON list (non-dict top level) degrades to the empty registry shape.
    def _non_dict_top_level():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                json.dump([1, 2, 3], fh)
            result = c.load_colour_rules(tmp)
        if result != _empty_registry():
            return False, "expected the empty registry shape, got %r" % (result,)
        return True, ""
    check("load_colour_rules() on a JSON list (non-dict top level) returns the empty registry shape", _non_dict_top_level)

    # 4. A kind whose value is not a dict (e.g. {"callsign": 5}) degrades to
    #    the empty registry shape rather than raising.
    def _non_dict_kind_value():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                json.dump({"callsign": 5}, fh)
            result = c.load_colour_rules(tmp)
        if result != _empty_registry():
            return False, "expected the empty registry shape, got %r" % (result,)
        return True, ""
    check("load_colour_rules() on {'callsign': 5} (non-dict kind value) returns the empty registry shape", _non_dict_kind_value)

    # 5. A lowercase callsign key is normalised to uppercase on read, and a
    #    valid entry round-trips.
    def _lowercase_callsign_key_normalised_on_read():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                json.dump({"callsign": {"afr1234": {"theme_id": "white", "created_at": "2026-01-01T00:00:00+00:00"}}}, fh)
            result = c.load_colour_rules(tmp)
        expected = {"AFR1234": {"theme_id": "white", "created_at": "2026-01-01T00:00:00+00:00"}}
        if result["callsign"] != expected:
            return False, "expected %r, got %r" % (expected, result["callsign"])
        return True, ""
    check("load_colour_rules() normalises a lowercase callsign key to uppercase and round-trips a valid entry", _lowercase_callsign_key_normalised_on_read)

    # 6. A lowercase hex key is normalised to uppercase on read.
    def _lowercase_hex_key_normalised_on_read():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                json.dump({"hex": {"39de4a": {"theme_id": "white", "created_at": "t"}}}, fh)
            result = c.load_colour_rules(tmp)
        if "39DE4A" not in result["hex"]:
            return False, "expected key '39DE4A' in %r" % (result["hex"],)
        return True, ""
    check("load_colour_rules() normalises a lowercase hex key to uppercase on read", _lowercase_hex_key_normalised_on_read)

    # 7. Malformed/hostile entries are dropped on read (defence in depth
    #    against a hand-edited file): a path-traversal-shaped callsign key,
    #    a 4-letter prefix, a hex key with a non-hex letter, and a theme_id
    #    not in device_config.THEMES.
    def _malformed_entries_dropped_on_read():
        with tempfile.TemporaryDirectory() as tmp:
            with open(c.colour_rules_path(tmp), "w") as fh:
                json.dump({"callsign": {"../x": {"theme_id": "white", "created_at": "t"}}}, fh)
            result_traversal = c.load_colour_rules(tmp)
        if result_traversal != _empty_registry():
            return False, "traversal-shaped callsign key: expected empty registry, got %r" % (result_traversal,)

        with tempfile.TemporaryDirectory() as tmp2:
            with open(c.colour_rules_path(tmp2), "w") as fh:
                json.dump({"prefix": {"AFRX": {"theme_id": "white", "created_at": "t"}}}, fh)
            result_4letter = c.load_colour_rules(tmp2)
        if result_4letter != _empty_registry():
            return False, "4-letter prefix key: expected empty registry, got %r" % (result_4letter,)

        with tempfile.TemporaryDirectory() as tmp3:
            with open(c.colour_rules_path(tmp3), "w") as fh:
                json.dump({"hex": {"ZZZZZZ": {"theme_id": "white", "created_at": "t"}}}, fh)
            result_bad_hex = c.load_colour_rules(tmp3)
        if result_bad_hex != _empty_registry():
            return False, "non-hex hex key: expected empty registry, got %r" % (result_bad_hex,)

        with tempfile.TemporaryDirectory() as tmp4:
            with open(c.colour_rules_path(tmp4), "w") as fh:
                json.dump({"callsign": {"AFR1234": {"theme_id": "chartreuse", "created_at": "t"}}}, fh)
            result_bad_theme = c.load_colour_rules(tmp4)
        if result_bad_theme != _empty_registry():
            return False, "unregistered theme_id: expected empty registry, got %r" % (result_bad_theme,)

        return True, ""
    check("load_colour_rules() drops a path-traversal-shaped callsign key, a 4-letter prefix, a non-hex hex key, and an unregistered theme_id", _malformed_entries_dropped_on_read)

    # 8. add_rule() returns ADD_OK_NEW and round-trips through
    #    load_colour_rules() with a non-empty created_at.
    def _add_rule_round_trip():
        with tempfile.TemporaryDirectory() as tmp:
            result = c.add_rule(tmp, "callsign", "afr1234", "white")
            if result != c.ADD_OK_NEW:
                return False, "add_rule() returned %r, expected ADD_OK_NEW" % (result,)
            registry = c.load_colour_rules(tmp)
            entry = registry["callsign"].get("AFR1234")
            if entry is None:
                return False, "AFR1234 missing from registry after add_rule(): %r" % (registry,)
            if entry.get("theme_id") != "white":
                return False, "theme_id %r != 'white'" % (entry.get("theme_id"),)
            if not entry.get("created_at"):
                return False, "created_at is falsy: %r" % (entry.get("created_at"),)
        return True, ""
    check("add_rule() returns ADD_OK_NEW and round-trips through load_colour_rules() with a non-empty created_at", _add_rule_round_trip)

    # 9. add_rule() rejects an unrecognised kind with ADD_REJECTED_KIND.
    def _add_rule_rejects_bad_kind():
        with tempfile.TemporaryDirectory() as tmp:
            result = c.add_rule(tmp, "airframe", "AFR1234", "white")
        if result != c.ADD_REJECTED_KIND:
            return False, "expected ADD_REJECTED_KIND, got %r" % (result,)
        return True, ""
    check("add_rule() rejects an unrecognised kind with ADD_REJECTED_KIND", _add_rule_rejects_bad_kind)

    # 10. add_rule() rejects a malformed key for the prefix and hex kinds
    #     with ADD_REJECTED_KEY (a basic sanity sweep; the exhaustive sweep
    #     is check 15 below).
    def _add_rule_rejects_bad_key():
        with tempfile.TemporaryDirectory() as tmp:
            prefix_result = c.add_rule(tmp, "prefix", "AFRX", "white")
        if prefix_result != c.ADD_REJECTED_KEY:
            return False, "4-letter prefix: expected ADD_REJECTED_KEY, got %r" % (prefix_result,)
        with tempfile.TemporaryDirectory() as tmp2:
            hex_result = c.add_rule(tmp2, "hex", "39DE4", "white")
        if hex_result != c.ADD_REJECTED_KEY:
            return False, "5-char hex: expected ADD_REJECTED_KEY, got %r" % (hex_result,)
        return True, ""
    check("add_rule() rejects a 4-letter prefix and a 5-character hex value with ADD_REJECTED_KEY", _add_rule_rejects_bad_key)

    # 11. add_rule() rejects an unregistered theme id with ADD_REJECTED_THEME.
    def _add_rule_rejects_bad_theme():
        with tempfile.TemporaryDirectory() as tmp:
            result = c.add_rule(tmp, "callsign", "AFR1234", "chartreuse")
        if result != c.ADD_REJECTED_THEME:
            return False, "expected ADD_REJECTED_THEME, got %r" % (result,)
        return True, ""
    check("add_rule() rejects an unregistered theme id with ADD_REJECTED_THEME", _add_rule_rejects_bad_theme)

    # 12. delete_rule() removes an entry and returns True; a second call on
    #     the same (kind, value) returns False without raising.
    def _delete_rule_idempotent():
        with tempfile.TemporaryDirectory() as tmp:
            c.add_rule(tmp, "callsign", "AFR1234", "white")
            first = c.delete_rule(tmp, "callsign", "AFR1234")
            second = c.delete_rule(tmp, "callsign", "AFR1234")
        if first is not True:
            return False, "first delete_rule() call returned %r, expected True" % (first,)
        if second is not False:
            return False, "second delete_rule() call returned %r, expected False" % (second,)
        return True, ""
    check("delete_rule() returns True once then False on a repeated call, without raising", _delete_rule_idempotent)

    # 13. rule_rows() orders by kind (RULE_KINDS order) then value ascending,
    #     skipping a malformed entry.
    def _rule_rows_ordered_and_defensive():
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
        if rows != expected:
            return False, "expected %r, got %r" % (expected, rows)
        return True, ""
    check("rule_rows() returns (kind, value, theme_id, created_at) tuples ordered by kind then value, skipping a malformed entry", _rule_rows_ordered_and_defensive)

    # 14. set_colour_rules_state_dir(None) clears the cache; the resolver
    #     then falls through to the base theme.
    def _cache_reset_to_none():
        try:
            c.set_colour_rules_state_dir(None)
            result = c.resolve_effective_theme_id(
                "departing", {"callsign": "AFR1234", "hex": "39de4a"}, {"theme": "white", "theme_arriving": None})
        finally:
            c.set_colour_rules_state_dir(None)
        if result != "white":
            return False, "expected 'white', got %r" % (result,)
        return True, ""
    check("set_colour_rules_state_dir(None) clears the cache and resolve_effective_theme_id() falls through to the base theme", _cache_reset_to_none)

    # 15. T-15-01 hostile-input sweep: every hostile value must be rejected
    #     by add_rule() with some ADD_REJECTED_* value (write-side), and the
    #     same shapes written directly to disk must be dropped by
    #     load_colour_rules() (read-side) — the allowlist re-applied on
    #     every read, not only at write.
    def _hostile_input_sweep():
        hostile_by_kind = {
            "callsign": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "AFR123456"],
            "hex": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "39DE4", "39DE4Z"],
            "prefix": ["../x", "a/b", "a\\b", "", "   ", None, 42, "x" * 400, "AFRX", "AF"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            for kind, hostile_values in hostile_by_kind.items():
                for value in hostile_values:
                    result = c.add_rule(tmp, kind, value, "white")
                    if not isinstance(result, str) or not result.startswith("rejected"):
                        return False, "add_rule(tmp, %r, %r, 'white') returned %r, expected some ADD_REJECTED_* value" % (kind, value, result)
            registry_after = c.load_colour_rules(tmp)
        if registry_after != _empty_registry():
            return False, "registry not empty after the write-side hostile-input sweep: %r" % (registry_after,)

        # Read-side: write the hostile string shapes directly to disk (only
        # the string-typed ones make valid JSON dict keys) and confirm they
        # are all dropped on read too.
        with tempfile.TemporaryDirectory() as tmp2:
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
        if registry_from_disk != _empty_registry():
            return False, "registry not empty after the read-side hostile-input sweep: %r" % (registry_from_disk,)

        return True, ""
    check("add_rule() rejects every hostile value in the sweep (write-side) and load_colour_rules() drops the same shapes written directly to disk (read-side), for all three kinds (T-15-01)", _hostile_input_sweep)

    # 16. D-09 added-versus-replaced: the first add returns ADD_OK_NEW, a
    #     second add for the same (kind, value) returns ADD_OK_REPLACED with
    #     the new theme_id and the entry count unchanged. Separately, filling
    #     the registry to the cap then adding a NEW key is rejected while
    #     re-adding an EXISTING key at the cap still succeeds (a replace is
    #     not growth).
    def _added_versus_replaced_and_cap_enforcement():
        with tempfile.TemporaryDirectory() as tmp:
            first = c.add_rule(tmp, "callsign", "AFR1234", "white")
            if first != c.ADD_OK_NEW:
                return False, "first add_rule() returned %r, expected ADD_OK_NEW" % (first,)
            second = c.add_rule(tmp, "callsign", "AFR1234", "black")
            if second != c.ADD_OK_REPLACED:
                return False, "second add_rule() (same key) returned %r, expected ADD_OK_REPLACED" % (second,)
            registry = c.load_colour_rules(tmp)
            if registry["callsign"]["AFR1234"]["theme_id"] != "black":
                return False, "expected the replaced theme_id 'black', got %r" % (registry["callsign"]["AFR1234"]["theme_id"],)
            total_entries = sum(len(registry[k]) for k in c.RULE_KINDS)
            if total_entries != 1:
                return False, "expected exactly 1 entry after a replace (not growth), got %d" % (total_entries,)

        with tempfile.TemporaryDirectory() as tmp2:
            prefixes = []
            for a in string.ascii_uppercase:
                for b in string.ascii_uppercase:
                    if len(prefixes) >= c.COLOUR_RULE_MAX_ENTRIES:
                        break
                    prefixes.append("Z" + a + b)
                if len(prefixes) >= c.COLOUR_RULE_MAX_ENTRIES:
                    break
            if len(prefixes) != c.COLOUR_RULE_MAX_ENTRIES:
                return False, "test setup failure: only generated %d distinct prefixes" % (len(prefixes),)
            for pfx in prefixes:
                result = c.add_rule(tmp2, "prefix", pfx, "white")
                if result != c.ADD_OK_NEW:
                    return False, "filling the cap: add_rule(%r, ...) returned %r" % (pfx, result)
            new_result = c.add_rule(tmp2, "prefix", "AAA", "white")
            if new_result != c.ADD_REJECTED_FULL:
                return False, "expected ADD_REJECTED_FULL for a new prefix at the cap, got %r" % (new_result,)
            overwrite_result = c.add_rule(tmp2, "prefix", prefixes[0], "black")
            if overwrite_result != c.ADD_OK_REPLACED:
                return False, "expected ADD_OK_REPLACED re-adding an existing prefix at the cap, got %r" % (overwrite_result,)
        return True, ""
    check("add_rule() distinguishes ADD_OK_NEW from ADD_OK_REPLACED (a replace is not growth) and enforces COLOUR_RULE_MAX_ENTRIES only against new keys (D-09)", _added_versus_replaced_and_cap_enforcement)

    # 17. T-15-02 atomicity: after a successful add_rule() and after a
    #     successful delete_rule(), no colour_rules.json*.tmp file remains
    #     in the state dir.
    def _no_stray_tmp_file_after_add_and_delete():
        with tempfile.TemporaryDirectory() as tmp:
            add_result = c.add_rule(tmp, "callsign", "AFR1234", "white")
            if add_result != c.ADD_OK_NEW:
                return False, "setup failure: add_rule() returned %r" % (add_result,)
            stray_after_add = [f for f in os.listdir(tmp) if ".tmp" in f]
            if stray_after_add:
                return False, "stray .tmp file(s) left behind after a successful add_rule(): %r" % (stray_after_add,)
            delete_result = c.delete_rule(tmp, "callsign", "AFR1234")
            if delete_result is not True:
                return False, "setup failure: delete_rule() returned %r" % (delete_result,)
            stray_after_delete = [f for f in os.listdir(tmp) if ".tmp" in f]
            if stray_after_delete:
                return False, "stray .tmp file(s) left behind after a successful delete_rule(): %r" % (stray_after_delete,)
        return True, ""
    check("no colour_rules.json.tmp file remains after a successful add_rule() or delete_rule() (atomicity proof)", _no_stray_tmp_file_after_add_and_delete)

    # 18. T-15-02 concurrency proof: several concurrent add_rule() calls for
    #     distinct keys (companion/app.py's real ThreadingHTTPServer
    #     concurrency shape) must all persist durably under _WRITE_LOCK - no
    #     lost update from an unsynchronised load-modify-write race - which
    #     is only possible because the pid/thread-scoped temp filename lets
    #     concurrent writers never share one temp path.
    def _concurrent_add_rule_calls_lose_no_updates():
        with tempfile.TemporaryDirectory() as tmp:
            values = ["AA%s" % chr(ord("A") + i) for i in range(20)]
            errors = []

            def _worker(value):
                try:
                    result = c.add_rule(tmp, "prefix", value, "white")
                    if result != c.ADD_OK_NEW:
                        errors.append((value, result))
                except Exception as exc:  # never let a worker's exception vanish silently
                    errors.append((value, repr(exc)))

            threads = [threading.Thread(target=_worker, args=(value,)) for value in values]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            if errors:
                return False, "worker error(s)/rejection(s): %r" % (errors,)

            registry = c.load_colour_rules(tmp)
            missing = [value for value in values if value not in registry["prefix"]]
            if missing:
                return False, "lost update(s) - missing prefixes after concurrent add_rule() calls: %r" % (missing,)

            stray = [f for f in os.listdir(tmp) if ".tmp" in f]
            if stray:
                return False, "stray .tmp file(s) left behind after concurrent writes: %r" % (stray,)
        return True, ""
    check(
        "20 concurrent add_rule() calls for 20 distinct prefixes (ThreadingHTTPServer's real concurrency "
        "shape) all persist durably with no lost update and no stray .tmp file left behind (T-15-02)",
        _concurrent_add_rule_calls_lose_no_updates)

    # 19-25. D-13 resolver truth table, all seven rows, each its own check
    #        so a failure names which row broke.
    def _resolver_with(state_dir_registry, state, flight, device_cfg):
        try:
            if state_dir_registry is None:
                c.set_colour_rules_state_dir(None)
            else:
                tmp = tempfile.mkdtemp()
                for kind, value, theme_id in state_dir_registry:
                    add_result = c.add_rule(tmp, kind, value, theme_id)
                    if add_result not in (c.ADD_OK_NEW, c.ADD_OK_REPLACED):
                        raise AssertionError("setup failure: add_rule(%r, %r, %r, %r) returned %r" % (tmp, kind, value, theme_id, add_result))
                c.set_colour_rules_state_dir(tmp)
            return c.resolve_effective_theme_id(state, flight, device_cfg)
        finally:
            c.set_colour_rules_state_dir(None)

    flight_afr = {"callsign": "AFR1234", "hex": "39de4a"}

    def _row1_no_rule_no_override_arriving():
        result = _resolver_with(None, "arriving", flight_afr, {"theme": "white", "theme_arriving": None})
        if result != "white":
            return False, "row 1: expected 'white', got %r" % (result,)
        return True, ""
    check("resolver truth table row 1: no rule, theme_arriving is None, state 'arriving' -> base theme", _row1_no_rule_no_override_arriving)

    def _row2_no_rule_override_arriving():
        result = _resolver_with(None, "arriving", flight_afr, {"theme": "white", "theme_arriving": "blue"})
        if result != "blue":
            return False, "row 2: expected 'blue', got %r" % (result,)
        return True, ""
    check("resolver truth table row 2: no rule, theme_arriving set, state 'arriving' -> the override", _row2_no_rule_override_arriving)

    def _row3_no_rule_override_departing():
        result = _resolver_with(None, "departing", flight_afr, {"theme": "white", "theme_arriving": "blue"})
        if result != "white":
            return False, "row 3: expected 'white', got %r" % (result,)
        return True, ""
    check("resolver truth table row 3: no rule, theme_arriving set, state 'departing' -> base theme", _row3_no_rule_override_departing)

    def _row4_prefix_rule_no_override():
        result = _resolver_with([("prefix", "AFR", "red")], "departing", flight_afr, {"theme": "white"})
        if result != "red":
            return False, "row 4: expected 'red', got %r" % (result,)
        return True, ""
    check("resolver truth table row 4: a matching prefix rule, no override -> the rule's theme", _row4_prefix_rule_no_override)

    def _row5_hex_beats_prefix():
        result = _resolver_with([("hex", "39DE4A", "green"), ("prefix", "AFR", "red")], "departing", flight_afr, {"theme": "white"})
        if result != "green":
            return False, "row 5: expected 'green', got %r" % (result,)
        return True, ""
    check("resolver truth table row 5: a matching hex rule and a matching prefix rule -> the hex rule's theme", _row5_hex_beats_prefix)

    def _row6_callsign_beats_hex():
        result = _resolver_with([("callsign", "AFR1234", "blue"), ("hex", "39DE4A", "green")], "departing", flight_afr, {"theme": "white"})
        if result != "blue":
            return False, "row 6: expected 'blue', got %r" % (result,)
        return True, ""
    check("resolver truth table row 6: a matching callsign rule and a matching hex rule -> the callsign rule's theme", _row6_callsign_beats_hex)

    def _row7_rule_beats_override():
        result = _resolver_with([("prefix", "AFR", "red")], "arriving", flight_afr, {"theme": "white", "theme_arriving": "blue"})
        if result != "red":
            return False, "row 7: expected 'red', got %r" % (result,)
        return True, ""
    check("resolver truth table row 7: a matching rule of any kind AND theme_arriving set with state 'arriving' -> the rule's theme (a rule beats the override, D-09)", _row7_rule_beats_override)

    # 26. The resolver never raises for flight=None/{}, a non-dict flight, a
    #     None callsign/hex, or a device_cfg missing theme_arriving entirely
    #     — it falls through to device_cfg["theme"].
    def _resolver_never_raises_on_defensive_inputs():
        c.set_colour_rules_state_dir(None)
        cases = [
            (None, {"theme": "white"}),
            ({}, {"theme": "white"}),
            ("not a dict", {"theme": "white"}),
            ({"callsign": None, "hex": None}, {"theme": "white"}),
            (flight_afr, {"theme": "white"}),  # no theme_arriving key at all
        ]
        for flight, device_cfg in cases:
            result = c.resolve_effective_theme_id("arriving", flight, device_cfg)
            if result != "white":
                return False, "flight=%r, device_cfg=%r: expected 'white', got %r" % (flight, device_cfg, result)
        return True, ""
    check("resolve_effective_theme_id() never raises for flight=None/{}/non-dict, a None callsign/hex, or a device_cfg with no theme_arriving key, falling through to the base theme", _resolver_never_raises_on_defensive_inputs)

    # 27. T-15-05: a cached entry whose theme_id is not a member of
    #     device_config.THEMES is ignored by the resolver rather than
    #     returned, even though the entry is present in the cache (injected
    #     by writing the file, priming the cache, then mutating the cache
    #     dict directly - simulating a tampered/corrupted cache state a
    #     hand-edited file alone could never round-trip past load_colour_rules()).
    def _tampered_cache_theme_id_ignored():
        try:
            with tempfile.TemporaryDirectory() as tmp:
                add_result = c.add_rule(tmp, "callsign", "AFR1234", "white")
                if add_result != c.ADD_OK_NEW:
                    return False, "setup failure: add_rule() returned %r" % (add_result,)
                c.set_colour_rules_state_dir(tmp)
                c._cached_rules["callsign"]["AFR1234"]["theme_id"] = "not-a-real-theme"
                result = c.resolve_effective_theme_id("departing", {"callsign": "AFR1234"}, {"theme": "black"})
            if result != "black":
                return False, "expected the tampered entry to be ignored and fall through to 'black', got %r" % (result,)
            if "not-a-real-theme" in device_config.THEMES:
                return False, "test setup invalid: 'not-a-real-theme' is somehow a real theme id"
        finally:
            c.set_colour_rules_state_dir(None)
        return True, ""
    check("resolve_effective_theme_id() ignores a cached entry whose theme_id is not a member of device_config.THEMES rather than returning it (T-15-05)", _tampered_cache_theme_id_ignored)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("colour_rules: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
