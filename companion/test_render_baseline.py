"""Rendered-HTML and unauthenticated-response equality against the
committed baseline (`companion/testdata/render_baseline.json`) — the
"no rendered-output change" proof this behaviour-preserving refactor
phase is verified against, and the route-gate baseline a later plan's
route-table test compares against.

Both tests share `companion_render_snapshot`'s own capture/freeze
machinery with the CLI that generated the committed baseline (never a
second, drifting copy of it here), so generation and verification can
never disagree on what "the same capture" means.
"""
import difflib
import json

import companion_render_snapshot


def _unified_diff(expected_text, actual_text):
    return "".join(difflib.unified_diff(
        expected_text.splitlines(keepends=True),
        actual_text.splitlines(keepends=True),
        fromfile="baseline", tofile="capture", lineterm=""))


def _assert_matches_baseline(expected, actual, kind, to_text):
    """Assert `actual` (a fresh capture) equals `expected` (the committed
    baseline) key for key. Fails on the first differing key only, with a
    unified diff of `to_text()`'s rendering of both sides.
    """
    expected_keys = sorted(expected)
    actual_keys = sorted(actual)
    assert expected_keys == actual_keys, (
        "%s key set changed — only in baseline: %r; only in capture: %r"
        % (kind,
           sorted(set(expected_keys) - set(actual_keys)),
           sorted(set(actual_keys) - set(expected_keys))))
    for key in expected_keys:
        if expected[key] == actual[key]:
            continue
        diff = _unified_diff(to_text(expected[key]), to_text(actual[key]))
        raise AssertionError(
            "%s %r differs from the committed baseline (first differing key):\n%s"
            % (kind, key, diff))


def test_rendered_pages_match_the_baseline():
    baseline = companion_render_snapshot.load_baseline()
    actual = companion_render_snapshot.capture_snapshot()
    _assert_matches_baseline(
        baseline["pages"], actual["pages"], "page",
        lambda entry: "status %s\n%s" % (entry["status"], entry["body"]))


def test_unauthenticated_responses_match_the_baseline():
    baseline = companion_render_snapshot.load_baseline()
    actual = companion_render_snapshot.capture_snapshot()
    _assert_matches_baseline(
        baseline["unauthenticated"], actual["unauthenticated"], "unauthenticated route",
        lambda entry: json.dumps(entry, indent=1, sort_keys=True) + "\n")
