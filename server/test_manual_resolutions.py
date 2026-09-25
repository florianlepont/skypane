#!/usr/bin/env python3
"""Contract tests for server/plane/manual_resolutions.py - the
manual-resolution registry.

Every fixture is `tmp_path` (pytest-owned, never a shared/real state dir).
The two read-only-parent-directory checks are skipped under euid 0
(`@requires_non_root`) - root ignores read-only directory permission
bits, so the write those checks expect to fail would silently succeed
instead, asserting the wrong thing rather than testing anything real.
"""
import json
import os
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# pyproject.toml's pythonpath puts test-support/ on sys.path for a normal
# pytest run; the legacy-runner bridge at the bottom of this file
# (`python3 server/test_manual_resolutions.py`) never reads that config,
# so the same directory is added here too.
_TEST_SUPPORT_DIR = os.path.join(REPO_ROOT, "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

from skypane_test_support import requires_non_root  # noqa: E402

import server.plane.illustrations as illustrations  # noqa: E402
import server.plane.manual_resolutions as m  # noqa: E402


def test_missing_state_dir_returns_empty_dict_without_raising():
    """load_manual_resolutions() on a nonexistent state dir returns {} without raising."""
    result = m.load_manual_resolutions("/nonexistent/skypane-mr-dir")
    assert result == {}, "expected {}, got %r" % (result,)


def test_invalid_json_returns_empty_dict(tmp_path):
    """load_manual_resolutions() on a file containing invalid JSON returns {}."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        fh.write("not json")
    result = m.load_manual_resolutions(tmp_path)
    assert result == {}, "expected {}, got %r" % (result,)


def test_non_dict_top_level_returns_empty_dict(tmp_path):
    """load_manual_resolutions() on a JSON list (non-dict top level) returns {}."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump([1, 2, 3], fh)
    result = m.load_manual_resolutions(tmp_path)
    assert result == {}, "expected {}, got %r" % (result,)


def test_non_dict_entry_value_dropped(tmp_path):
    """load_manual_resolutions() drops an entry whose value is not a dict."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump({"AAA": 5}, fh)
    result = m.load_manual_resolutions(tmp_path)
    assert result == {}, "expected {}, got %r" % (result,)


def test_lowercase_key_normalised_on_read_and_round_trips(tmp_path):
    """load_manual_resolutions() normalises a lowercase key to uppercase and round-trips a valid entry."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump({"aaa": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"}}, fh)
    result = m.load_manual_resolutions(tmp_path)
    expected = {"AAA": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"}}
    assert result == expected, "expected %r, got %r" % (expected, result)


def test_malformed_keys_dropped(tmp_path, tmp_path_factory):
    """load_manual_resolutions() drops a path-traversal-shaped key and a 4-letter key."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump({"../x": {"airline_name": "Volotea", "created_at": "t"}}, fh)
    result_traversal = m.load_manual_resolutions(tmp_path)
    assert result_traversal == {}, "traversal-shaped key: expected {}, got %r" % (result_traversal,)

    tmp2 = tmp_path_factory.mktemp("mr-4letter")
    with open(m.manual_resolutions_path(tmp2), "w") as fh:
        json.dump({"AAAA": {"airline_name": "Volotea", "created_at": "t"}}, fh)
    result_4letter = m.load_manual_resolutions(tmp2)
    assert result_4letter == {}, "4-letter key: expected {}, got %r" % (result_4letter,)


def test_reserved_name_dropped_on_read(tmp_path):
    """load_manual_resolutions() drops a hand-edited entry whose airline_name slugs to a reserved key."""
    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump({"AAA": {"airline_name": "Generic Fallback", "created_at": "t"}}, fh)
    result = m.load_manual_resolutions(tmp_path)
    assert result == {}, "expected {}, got %r" % (result,)


def test_add_entry_round_trips_with_non_empty_created_at(tmp_path):
    """add_entry() returns ADD_OK and round-trips through load_manual_resolutions() with a non-empty created_at."""
    result = m.add_entry(tmp_path, "AAA", "Volotea")
    assert result == m.ADD_OK, "add_entry() returned %r, expected ADD_OK" % (result,)
    registry = m.load_manual_resolutions(tmp_path)
    entry = registry.get("AAA")
    assert entry is not None, "AAA missing from registry after add_entry(): %r" % (registry,)
    assert entry.get("airline_name") == "Volotea", "airline_name %r != 'Volotea'" % (entry.get("airline_name"),)
    assert entry.get("created_at"), "created_at is falsy: %r" % (entry.get("created_at"),)


def test_add_entry_rejects_2letter_prefix(tmp_path):
    """add_entry() rejects a 2-letter prefix with ADD_REJECTED_PREFIX."""
    result = m.add_entry(tmp_path, "aa", "X")
    assert result == m.ADD_REJECTED_PREFIX, "expected ADD_REJECTED_PREFIX, got %r" % (result,)


def test_add_entry_rejects_whitespace_only_name(tmp_path):
    """add_entry() rejects a whitespace-only name with ADD_REJECTED_NAME_EMPTY."""
    result = m.add_entry(tmp_path, "AAA", "   ")
    assert result == m.ADD_REJECTED_NAME_EMPTY, "expected ADD_REJECTED_NAME_EMPTY, got %r" % (result,)


def test_add_entry_rejects_101char_name(tmp_path):
    """add_entry() rejects a 101-char name with ADD_REJECTED_NAME_TOO_LONG."""
    result = m.add_entry(tmp_path, "AAA", "x" * 101)
    assert result == m.ADD_REJECTED_NAME_TOO_LONG, "expected ADD_REJECTED_NAME_TOO_LONG, got %r" % (result,)


def test_add_entry_rejects_reserved_names(tmp_path, tmp_path_factory):
    """add_entry() rejects 'Generic Fallback' and 'Generic A320' with ADD_REJECTED_NAME_RESERVED."""
    result_fallback = m.add_entry(tmp_path, "AAA", "Generic Fallback")
    tmp2 = tmp_path_factory.mktemp("mr-reserved")
    result_shape = m.add_entry(tmp2, "AAA", "Generic A320")
    assert result_fallback == m.ADD_REJECTED_NAME_RESERVED, (
        "'Generic Fallback': expected ADD_REJECTED_NAME_RESERVED, got %r" % (result_fallback,)
    )
    assert result_shape == m.ADD_REJECTED_NAME_RESERVED, (
        "'Generic A320': expected ADD_REJECTED_NAME_RESERVED, got %r" % (result_shape,)
    )


def test_add_entry_rejects_new_prefix_at_cap_but_allows_overwrite(tmp_path):
    """add_entry() rejects a new prefix at MANUAL_RESOLUTION_MAX_ENTRIES (ADD_REJECTED_FULL) but allows overwriting an existing one."""
    prefixes = []
    count = 0
    for a in string.ascii_uppercase:
        for b in string.ascii_uppercase:
            if count >= m.MANUAL_RESOLUTION_MAX_ENTRIES:
                break
            prefixes.append("Z" + a + b)
            count += 1
        if count >= m.MANUAL_RESOLUTION_MAX_ENTRIES:
            break
    assert len(prefixes) == m.MANUAL_RESOLUTION_MAX_ENTRIES, (
        "test setup failure: only generated %d distinct prefixes" % (len(prefixes),)
    )
    for i, pfx in enumerate(prefixes):
        result = m.add_entry(tmp_path, pfx, "Airline %d" % i)
        assert result == m.ADD_OK, "filling the cap: add_entry(%r, ...) returned %r" % (pfx, result)
    new_result = m.add_entry(tmp_path, "AAA", "One Too Many")
    assert new_result == m.ADD_REJECTED_FULL, (
        "expected ADD_REJECTED_FULL for a new prefix at the cap, got %r" % (new_result,)
    )
    overwrite_result = m.add_entry(tmp_path, prefixes[0], "Renamed Airline")
    assert overwrite_result == m.ADD_OK, (
        "expected ADD_OK re-adding an existing prefix at the cap, got %r" % (overwrite_result,)
    )


def test_delete_entry_returns_true_once_then_false(tmp_path):
    """delete_entry() returns True once then False on a repeated call, without raising."""
    m.add_entry(tmp_path, "AAA", "Volotea")
    first = m.delete_entry(tmp_path, "AAA")
    second = m.delete_entry(tmp_path, "AAA")
    assert first is True, "first delete_entry() call returned %r, expected True" % (first,)
    assert second is False, "second delete_entry() call returned %r, expected False" % (second,)


def test_state_dir_cache_round_trips_and_clears_on_reset(tmp_path):
    """set_manual_registry_state_dir()/airline_name_for_prefix() cache round-trips and clears on reset to None."""
    m.add_entry(tmp_path, "AAA", "Volotea")
    m.set_manual_registry_state_dir(tmp_path)
    cached = m.airline_name_for_prefix("AAA")
    m.set_manual_registry_state_dir(None)
    after_reset = m.airline_name_for_prefix("AAA")
    assert cached == "Volotea", "expected 'Volotea' from the cache, got %r" % (cached,)
    assert after_reset is None, "expected None after set_manual_registry_state_dir(None), got %r" % (after_reset,)


def test_entry_rows_sorted_and_skips_malformed_entry():
    """entry_rows() returns (prefix, airline_name, created_at) tuples sorted by prefix, skipping a malformed entry."""
    registry = {
        "BBB": {"airline_name": "Bravo Air", "created_at": "t2"},
        "AAA": {"airline_name": "Alpha Air", "created_at": "t1"},
        "CCC": "not a dict",
    }
    rows = m.entry_rows(registry)
    expected = [("AAA", "Alpha Air", "t1"), ("BBB", "Bravo Air", "t2")]
    assert rows == expected, "expected %r, got %r" % (expected, rows)


def test_delete_entry_leaves_override_png_untouched(tmp_path):
    """delete_entry() leaves the override PNG on disk untouched, pinned to illustrations.override_path_for_key()."""
    override_dir = illustrations.override_dir_for_state_dir(tmp_path)
    os.makedirs(override_dir, exist_ok=True)
    override_path = illustrations.override_path_for_key("volotea", tmp_path)
    with open(override_path, "wb") as fh:
        fh.write(b"not a real png, this test never decodes it")
    m.add_entry(tmp_path, "VOE", "Volotea")
    m.delete_entry(tmp_path, "VOE")
    still_there = os.path.isfile(override_path)
    registry_after = m.load_manual_resolutions(tmp_path)
    assert still_there, "override PNG at %r was deleted by delete_entry() - violates D-08" % (override_path,)
    assert "VOE" not in registry_after, (
        "VOE entry still present in registry after delete_entry(): %r" % (registry_after,)
    )


def test_no_stray_tmp_file_after_successful_add(tmp_path):
    """no manual_resolutions.json.tmp file remains after a successful add_entry() (atomicity proof)."""
    result = m.add_entry(tmp_path, "AAA", "Volotea")
    assert result == m.ADD_OK, "setup failure: add_entry() returned %r" % (result,)
    stray = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert not stray, "stray .tmp file(s) left behind after a successful add_entry(): %r" % (stray,)


def test_concurrent_add_entry_calls_lose_no_updates(tmp_path):
    """20 concurrent add_entry() calls for 20 distinct prefixes (ThreadingHTTPServer's real concurrency shape) all persist durably with no lost update and no stray .tmp file left behind."""
    import threading

    prefixes = ["AA%s" % chr(ord("A") + i) for i in range(20)]
    errors = []

    def _worker(pfx):
        try:
            result = m.add_entry(tmp_path, pfx, "Airline %s" % pfx)
            if result != m.ADD_OK:
                errors.append((pfx, result))
        except Exception as exc:  # never let a worker's exception vanish silently
            errors.append((pfx, repr(exc)))

    threads = [threading.Thread(target=_worker, args=(pfx,)) for pfx in prefixes]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, "worker error(s)/rejection(s): %r" % (errors,)

    registry = m.load_manual_resolutions(tmp_path)
    missing = [pfx for pfx in prefixes if pfx not in registry]
    assert not missing, (
        "WR-02: lost update(s) - missing prefixes after concurrent add_entry() calls: %r "
        "(registry has %d/%d entries)" % (missing, len(registry), len(prefixes))
    )

    stray = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
    assert not stray, "stray .tmp file(s) left behind after concurrent writes: %r" % (stray,)


def test_load_prints_drop_count_for_rejected_and_capped_entries(tmp_path, tmp_path_factory):
    """load_manual_resolutions() prints a one-line drop-count message whenever it silently rejects an entry or truncates at the cap (naming the real count in both cases) and prints nothing when nothing is dropped."""
    import contextlib
    import io

    with open(m.manual_resolutions_path(tmp_path), "w") as fh:
        json.dump({
            "AAA": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"},
            "BBB": "not a dict",
        }, fh)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = m.load_manual_resolutions(tmp_path)
    expected = {"AAA": {"airline_name": "Volotea", "created_at": "2026-01-01T00:00:00+00:00"}}
    assert result == expected, "expected the valid entry alone to survive, got %r" % (result,)
    assert "1 entry" in buf.getvalue(), (
        "expected a drop-count message naming 1 dropped entry, got %r" % (buf.getvalue(),)
    )

    tmp_clean = tmp_path_factory.mktemp("mr-clean")
    with open(m.manual_resolutions_path(tmp_clean), "w") as fh:
        json.dump({"AAA": {"airline_name": "Volotea", "created_at": "t"}}, fh)
    buf_clean = io.StringIO()
    with contextlib.redirect_stdout(buf_clean):
        m.load_manual_resolutions(tmp_clean)
    assert not buf_clean.getvalue(), (
        "expected no drop-count message when nothing is dropped, got %r" % (buf_clean.getvalue(),)
    )

    tmp_cap = tmp_path_factory.mktemp("mr-cap")
    over_cap_by = 5
    oversized = {}
    count = 0
    total = m.MANUAL_RESOLUTION_MAX_ENTRIES + over_cap_by
    for a in string.ascii_uppercase:
        for b in string.ascii_uppercase:
            if count >= total:
                break
            oversized["Z" + a + b] = {"airline_name": "Airline %d" % count, "created_at": "t"}
            count += 1
        if count >= total:
            break
    with open(m.manual_resolutions_path(tmp_cap), "w") as fh:
        json.dump(oversized, fh)
    buf_cap = io.StringIO()
    with contextlib.redirect_stdout(buf_cap):
        result_cap = m.load_manual_resolutions(tmp_cap)
    assert len(result_cap) == m.MANUAL_RESOLUTION_MAX_ENTRIES, (
        "expected exactly the cap's worth of surviving entries, got %d" % (len(result_cap),)
    )
    assert ("%d entry" % over_cap_by) in buf_cap.getvalue(), (
        "expected the drop-count message to name the %d over-cap entries, got %r" % (over_cap_by, buf_cap.getvalue())
    )


@requires_non_root
def test_add_entry_on_uncreatable_state_dir_returns_failed(tmp_path):
    """add_entry() returns ADD_FAILED (never raises) when its state dir cannot be created because the parent directory is read-only."""
    os.chmod(tmp_path, 0o500)
    try:
        result = m.add_entry(tmp_path / "state", "ABC", "Test Air")
    finally:
        os.chmod(tmp_path, 0o700)
    assert result == m.ADD_FAILED, "expected ADD_FAILED for an uncreatable state dir, got %r" % (result,)


@requires_non_root
def test_delete_entry_on_unwritable_state_dir_returns_false(tmp_path):
    """delete_entry() returns False (never raises) when the state dir goes read-only mid-write, and the existing entry survives untouched since the write never happened."""
    add_result = m.add_entry(tmp_path, "ABC", "Test Air")
    assert add_result == m.ADD_OK, "setup failure: add_entry() returned %r" % (add_result,)
    os.chmod(tmp_path, 0o500)
    try:
        result = m.delete_entry(tmp_path, "ABC")
    finally:
        os.chmod(tmp_path, 0o700)
    assert result is False, "expected False (never raises) when the state dir is read-only, got %r" % (result,)
    registry = m.load_manual_resolutions(tmp_path)
    assert "ABC" in registry, "expected the ABC entry to survive a failed delete_entry() write untouched"


def test_add_entry_rejects_hostile_input_sweep(tmp_path):
    """add_entry() rejects every name in the hostile-input sweep, leaving the registry empty."""
    hostile_names = [
        "../../etc/passwd", "a/b", "..\\..\\x", "", "   ", None, 42,
        "x" * 400, "Generic Fallback", "generic-a320",
    ]
    for name in hostile_names:
        result = m.add_entry(tmp_path, "AAA", name)
        assert isinstance(result, str) and result.startswith("rejected"), (
            "add_entry(tmp, 'AAA', %r) returned %r, expected some ADD_REJECTED_* value" % (name, result)
        )
    registry_after = m.load_manual_resolutions(tmp_path)
    assert registry_after == {}, "registry not empty after the hostile-input sweep: %r" % (registry_after,)

