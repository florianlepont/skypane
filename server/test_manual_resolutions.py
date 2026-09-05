#!/usr/bin/env python3
"""Contract harness for server/plane/manual_resolutions.py - the phase 13
manual-resolution registry (D-01/D-05/D-08/D-13, 13-VALIDATION.md Wave 0
item 1).

Stdlib-only, plus the module under test (server.plane.manual_resolutions)
and its own dependency (server.plane.illustrations). Every fixture is a
`tempfile.TemporaryDirectory()`, never a shared/real state dir. Exits 0
only when every check below passes; any failure (or exception - none is
ever swallowed into a pass) exits 1.

Usage:
    server/.venv/bin/python3 server/test_manual_resolutions.py
"""
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Initial value for this file, introduced by phase 13 plan 01. Re-derived
# by RUNNING the harness (not by arithmetic), per this repo's own
# documented discipline (see the ledger comment above
# companion/test_status_pages.py's own EXPECTED_CHECK_COUNT).
EXPECTED_CHECK_COUNT = 19


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
        import server.plane.manual_resolutions as m
    except ImportError as exc:
        print("FAIL import server.plane.manual_resolutions - %r" % (exc,))
        print("manual_resolutions: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    try:
        import server.plane.illustrations as illustrations
    except ImportError as exc:
        print("FAIL import server.plane.illustrations - %r" % (exc,))
        print("manual_resolutions: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    # 1. Missing state dir degrades to {}, never raises.
    def _missing_state_dir():
        result = m.load_manual_resolutions("/nonexistent/skypane-mr-dir")
        if result != {}:
            return False, "expected {}, got %r" % (result,)
        return True, ""
    check("load_manual_resolutions() on a nonexistent state dir returns {} without raising", _missing_state_dir)

    # 2. Non-JSON file content degrades to {}.
    def _not_json():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                fh.write("not json")
            result = m.load_manual_resolutions(tmp)
        if result != {}:
            return False, "expected {}, got %r" % (result,)
        return True, ""
    check("load_manual_resolutions() on a file containing invalid JSON returns {}", _not_json)

    # 3. A JSON list (non-dict top level) degrades to {}.
    def _non_dict_top_level():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                json.dump([1, 2, 3], fh)
            result = m.load_manual_resolutions(tmp)
        if result != {}:
            return False, "expected {}, got %r" % (result,)
        return True, ""
    check("load_manual_resolutions() on a JSON list (non-dict top level) returns {}", _non_dict_top_level)

    # 4. An entry whose value is not a dict is dropped.
    def _non_dict_entry_value():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                json.dump({"AAA": 5}, fh)
            result = m.load_manual_resolutions(tmp)
        if result != {}:
            return False, "expected {}, got %r" % (result,)
        return True, ""
    check("load_manual_resolutions() drops an entry whose value is not a dict", _non_dict_entry_value)

    # 5. A lowercase key is normalised to uppercase on read, and a valid
    #    entry round-trips.
    def _lowercase_key_normalised_on_read():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                json.dump({"aaa": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"}}, fh)
            result = m.load_manual_resolutions(tmp)
        expected = {"AAA": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"}}
        if result != expected:
            return False, "expected %r, got %r" % (expected, result)
        return True, ""
    check("load_manual_resolutions() normalises a lowercase key to uppercase and round-trips a valid entry", _lowercase_key_normalised_on_read)

    # 6. A path-traversal-shaped key and a 4-letter key are both dropped.
    def _malformed_keys_dropped():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                json.dump({"../x": {"airline_name": "Volotea", "created_at": "t"}}, fh)
            result_traversal = m.load_manual_resolutions(tmp)
        with tempfile.TemporaryDirectory() as tmp2:
            with open(m.manual_resolutions_path(tmp2), "w") as fh:
                json.dump({"AAAA": {"airline_name": "Volotea", "created_at": "t"}}, fh)
            result_4letter = m.load_manual_resolutions(tmp2)
        if result_traversal != {}:
            return False, "traversal-shaped key: expected {}, got %r" % (result_traversal,)
        if result_4letter != {}:
            return False, "4-letter key: expected {}, got %r" % (result_4letter,)
        return True, ""
    check("load_manual_resolutions() drops a path-traversal-shaped key and a 4-letter key", _malformed_keys_dropped)

    # 7. An entry whose airline_name slugs to a reserved key is dropped on
    #    read too (defence in depth against a hand-edited file).
    def _reserved_name_dropped_on_read():
        with tempfile.TemporaryDirectory() as tmp:
            with open(m.manual_resolutions_path(tmp), "w") as fh:
                json.dump({"AAA": {"airline_name": "Generic Fallback", "created_at": "t"}}, fh)
            result = m.load_manual_resolutions(tmp)
        if result != {}:
            return False, "expected {}, got %r" % (result,)
        return True, ""
    check("load_manual_resolutions() drops a hand-edited entry whose airline_name slugs to a reserved key", _reserved_name_dropped_on_read)

    # 8. add_entry() round-trips through load_manual_resolutions() with a
    #    non-empty created_at.
    def _add_entry_round_trip():
        with tempfile.TemporaryDirectory() as tmp:
            result = m.add_entry(tmp, "AAA", "Volotea")
            if result != m.ADD_OK:
                return False, "add_entry() returned %r, expected ADD_OK" % (result,)
            registry = m.load_manual_resolutions(tmp)
            entry = registry.get("AAA")
            if entry is None:
                return False, "AAA missing from registry after add_entry(): %r" % (registry,)
            if entry.get("airline_name") != "Volotea":
                return False, "airline_name %r != 'Volotea'" % (entry.get("airline_name"),)
            if not entry.get("created_at"):
                return False, "created_at is falsy: %r" % (entry.get("created_at"),)
        return True, ""
    check("add_entry() returns ADD_OK and round-trips through load_manual_resolutions() with a non-empty created_at", _add_entry_round_trip)

    # 9. add_entry() rejects a malformed prefix.
    def _add_entry_rejects_bad_prefix():
        with tempfile.TemporaryDirectory() as tmp:
            result = m.add_entry(tmp, "aa", "X")
        if result != m.ADD_REJECTED_PREFIX:
            return False, "expected ADD_REJECTED_PREFIX, got %r" % (result,)
        return True, ""
    check("add_entry() rejects a 2-letter prefix with ADD_REJECTED_PREFIX", _add_entry_rejects_bad_prefix)

    # 10. add_entry() rejects an empty (whitespace-only) name.
    def _add_entry_rejects_empty_name():
        with tempfile.TemporaryDirectory() as tmp:
            result = m.add_entry(tmp, "AAA", "   ")
        if result != m.ADD_REJECTED_NAME_EMPTY:
            return False, "expected ADD_REJECTED_NAME_EMPTY, got %r" % (result,)
        return True, ""
    check("add_entry() rejects a whitespace-only name with ADD_REJECTED_NAME_EMPTY", _add_entry_rejects_empty_name)

    # 11. add_entry() rejects an over-length name.
    def _add_entry_rejects_too_long_name():
        with tempfile.TemporaryDirectory() as tmp:
            result = m.add_entry(tmp, "AAA", "x" * 101)
        if result != m.ADD_REJECTED_NAME_TOO_LONG:
            return False, "expected ADD_REJECTED_NAME_TOO_LONG, got %r" % (result,)
        return True, ""
    check("add_entry() rejects a 101-char name with ADD_REJECTED_NAME_TOO_LONG", _add_entry_rejects_too_long_name)

    # 12. add_entry() rejects both reserved-slug shapes.
    def _add_entry_rejects_reserved_names():
        with tempfile.TemporaryDirectory() as tmp:
            result_fallback = m.add_entry(tmp, "AAA", "Generic Fallback")
        with tempfile.TemporaryDirectory() as tmp2:
            result_shape = m.add_entry(tmp2, "AAA", "Generic A320")
        if result_fallback != m.ADD_REJECTED_NAME_RESERVED:
            return False, "'Generic Fallback': expected ADD_REJECTED_NAME_RESERVED, got %r" % (result_fallback,)
        if result_shape != m.ADD_REJECTED_NAME_RESERVED:
            return False, "'Generic A320': expected ADD_REJECTED_NAME_RESERVED, got %r" % (result_shape,)
        return True, ""
    check("add_entry() rejects 'Generic Fallback' and 'Generic A320' with ADD_REJECTED_NAME_RESERVED", _add_entry_rejects_reserved_names)

    # 13. Filling the registry to the cap then adding a NEW prefix is
    #     rejected; re-adding an EXISTING prefix at the cap still succeeds
    #     (an overwrite is not growth).
    def _cap_enforcement():
        with tempfile.TemporaryDirectory() as tmp:
            prefixes = []
            import string
            count = 0
            for a in string.ascii_uppercase:
                for b in string.ascii_uppercase:
                    if count >= m.MANUAL_RESOLUTION_MAX_ENTRIES:
                        break
                    prefixes.append("Z" + a + b)
                    count += 1
                if count >= m.MANUAL_RESOLUTION_MAX_ENTRIES:
                    break
            if len(prefixes) != m.MANUAL_RESOLUTION_MAX_ENTRIES:
                return False, "test setup failure: only generated %d distinct prefixes" % (len(prefixes),)
            for i, pfx in enumerate(prefixes):
                result = m.add_entry(tmp, pfx, "Airline %d" % i)
                if result != m.ADD_OK:
                    return False, "filling the cap: add_entry(%r, ...) returned %r" % (pfx, result)
            new_result = m.add_entry(tmp, "AAA", "One Too Many")
            if new_result != m.ADD_REJECTED_FULL:
                return False, "expected ADD_REJECTED_FULL for a new prefix at the cap, got %r" % (new_result,)
            overwrite_result = m.add_entry(tmp, prefixes[0], "Renamed Airline")
            if overwrite_result != m.ADD_OK:
                return False, "expected ADD_OK re-adding an existing prefix at the cap, got %r" % (overwrite_result,)
        return True, ""
    check("add_entry() rejects a new prefix at MANUAL_RESOLUTION_MAX_ENTRIES (ADD_REJECTED_FULL) but allows overwriting an existing one", _cap_enforcement)

    # 14. delete_entry() removes an entry and returns True; a second call
    #     on the same prefix returns False without raising.
    def _delete_entry_idempotent():
        with tempfile.TemporaryDirectory() as tmp:
            m.add_entry(tmp, "AAA", "Volotea")
            first = m.delete_entry(tmp, "AAA")
            second = m.delete_entry(tmp, "AAA")
        if first is not True:
            return False, "first delete_entry() call returned %r, expected True" % (first,)
        if second is not False:
            return False, "second delete_entry() call returned %r, expected False" % (second,)
        return True, ""
    check("delete_entry() returns True once then False on a repeated call, without raising", _delete_entry_idempotent)

    # 15. set_manual_registry_state_dir()/airline_name_for_prefix() cache
    #     round trip, and resetting to None clears the cache.
    def _cache_round_trip():
        with tempfile.TemporaryDirectory() as tmp:
            m.add_entry(tmp, "AAA", "Volotea")
            m.set_manual_registry_state_dir(tmp)
            cached = m.airline_name_for_prefix("AAA")
            m.set_manual_registry_state_dir(None)
            after_reset = m.airline_name_for_prefix("AAA")
        if cached != "Volotea":
            return False, "expected 'Volotea' from the cache, got %r" % (cached,)
        if after_reset is not None:
            return False, "expected None after set_manual_registry_state_dir(None), got %r" % (after_reset,)
        return True, ""
    check("set_manual_registry_state_dir()/airline_name_for_prefix() cache round-trips and clears on reset to None", _cache_round_trip)

    # 16. entry_rows() sorts by prefix ascending and skips a malformed
    #     entry.
    def _entry_rows_sorted_and_defensive():
        registry = {
            "BBB": {"airline_name": "Bravo Air", "created_at": "t2"},
            "AAA": {"airline_name": "Alpha Air", "created_at": "t1"},
            "CCC": "not a dict",
        }
        rows = m.entry_rows(registry)
        expected = [("AAA", "Alpha Air", "t1"), ("BBB", "Bravo Air", "t2")]
        if rows != expected:
            return False, "expected %r, got %r" % (expected, rows)
        return True, ""
    check("entry_rows() returns (prefix, airline_name, created_at) tuples sorted by prefix, skipping a malformed entry", _entry_rows_sorted_and_defensive)

    # 17. D-08 proof: delete_entry() never touches the override image file
    #     on disk. The override path is built with the real path builder
    #     (override_path_for_key()), not a hand-typed string, so this test
    #     is pinned to the real contract rather than a guess about its
    #     shape.
    def _delete_entry_never_touches_override_file():
        with tempfile.TemporaryDirectory() as tmp:
            override_dir = illustrations.override_dir_for_state_dir(tmp)
            os.makedirs(override_dir, exist_ok=True)
            override_path = illustrations.override_path_for_key("volotea", tmp)
            with open(override_path, "wb") as fh:
                fh.write(b"not a real png, this test never decodes it")
            m.add_entry(tmp, "VOE", "Volotea")
            m.delete_entry(tmp, "VOE")
            still_there = os.path.isfile(override_path)
            registry_after = m.load_manual_resolutions(tmp)
        if not still_there:
            return False, "override PNG at %r was deleted by delete_entry() - violates D-08" % (override_path,)
        if "VOE" in registry_after:
            return False, "VOE entry still present in registry after delete_entry(): %r" % (registry_after,)
        return True, ""
    check("delete_entry() leaves the override PNG on disk untouched (D-08), pinned to illustrations.override_path_for_key()", _delete_entry_never_touches_override_file)

    # 18. Atomicity proof: after a successful add_entry(), no stray
    #     manual_resolutions.json.tmp file remains in the state dir.
    def _no_stray_tmp_file_after_add():
        with tempfile.TemporaryDirectory() as tmp:
            result = m.add_entry(tmp, "AAA", "Volotea")
            if result != m.ADD_OK:
                return False, "setup failure: add_entry() returned %r" % (result,)
            stray = [f for f in os.listdir(tmp) if f.endswith(".tmp")]
        if stray:
            return False, "stray .tmp file(s) left behind after a successful add_entry(): %r" % (stray,)
        return True, ""
    check("no manual_resolutions.json.tmp file remains after a successful add_entry() (atomicity proof)", _no_stray_tmp_file_after_add)

    # 19. Hostile-input sweep: every one of these must be rejected by
    #     add_entry() with some ADD_REJECTED_* value, and the registry must
    #     remain empty afterwards. One check covering the whole list, not
    #     one per item.
    def _hostile_input_sweep():
        hostile_names = [
            "../../etc/passwd", "a/b", "..\\..\\x", "", "   ", None, 42,
            "x" * 400, "Generic Fallback", "generic-a320",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for name in hostile_names:
                result = m.add_entry(tmp, "AAA", name)
                if not isinstance(result, str) or not result.startswith("rejected"):
                    return False, "add_entry(tmp, 'AAA', %r) returned %r, expected some ADD_REJECTED_* value" % (name, result)
            registry_after = m.load_manual_resolutions(tmp)
        if registry_after != {}:
            return False, "registry not empty after the hostile-input sweep: %r" % (registry_after,)
        return True, ""
    check("add_entry() rejects every name in the hostile-input sweep, leaving the registry empty", _hostile_input_sweep)

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("manual_resolutions: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
