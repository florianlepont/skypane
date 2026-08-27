#!/usr/bin/env python3
"""Contract harness for server/plane/illustrations.py's per-airline
illustration selection module (D-06, D-08, D-09, D-19, PLANE-01/PLANE-02).

Stdlib-only, plus the module under test (server.plane.illustrations, which
transitively imports Pillow) - must be run under server/.venv's
interpreter, not the bare system python3. Exits 0 only when every check
below passes; any failure (or exception - none is ever swallowed into a
pass) exits 1. Matches the same check()/EXPECTED_CHECK_COUNT/main()
convention every sibling server/test_*.py file uses (see
server/test_dither.py, server/test_poll_loop.py) - no pytest.

This file closes the one gap 03-03-PLAN.md's Reconciliation Note
(2026-08-26) recorded against Task 1: server/plane/illustrations.py and
server/assets/icons/illustrations/HANDOFF.md shipped in commit 21c4ed6,
but this test file was never created until now.

Covers every bullet in Task 1's <behavior> block: normalise_airline_key(),
select_illustration() (including its never-raises guarantee and its
"None only when even the fallback is missing" degradation), and
validate_illustration_file()'s rejection categories, each asserted with a
distinct message. Tests against the real, already-vendored files under
server/assets/icons/illustrations/ where they are stable and pass
--validate, rather than synthetic fixtures - malformed fixtures are still
built programmatically in a temp directory since no broken binary should
ever be committed to the repo.
"""
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 28


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
        from server.plane import illustrations as ill
    except ImportError as exc:
        print("FAIL import server.plane.illustrations - %r" % (exc,))
        print("illustrations: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    from PIL import Image

    # --- normalise_airline_key() ---------------------------------------------

    def _key_air_algerie():
        got = ill.normalise_airline_key("Air Algérie")
        if got != "air-algerie":
            return False, "got %r, expected 'air-algerie'" % (got,)
        return True, ""
    check("normalise_airline_key('Air Algérie') == 'air-algerie'", _key_air_algerie)

    def _key_ccm_airlines():
        got = ill.normalise_airline_key("CCM Airlines")
        if got != "ccm-airlines":
            return False, "got %r, expected 'ccm-airlines'" % (got,)
        return True, ""
    check("normalise_airline_key('CCM Airlines') == 'ccm-airlines'", _key_ccm_airlines)

    def _key_falsy_and_non_string_none():
        for value in ("", None, 42):
            got = ill.normalise_airline_key(value)
            if got is not None:
                return False, "normalise_airline_key(%r) returned %r, expected None" % (value, got)
        return True, ""
    check(
        "normalise_airline_key('') / (None) / (42) all return None without raising",
        _key_falsy_and_non_string_none,
    )

    # --- classify_aircraft_type() / SHAPE_SLUGS ------------------------------

    def _classify_all_seven_buckets():
        designator_to_expected = {
            "A20N": "a320", "A321": "a320", "A21N": "a320", "A319": "a320", "A318": "a320",
            "B738": "b737", "B733": "b737", "B38M": "b737",
            "AT76": "atr72", "AT72": "atr72", "AT43": "atr72",
            "BE9L": "beechcraft1900d",
            "E145": "embraer", "E190": "embraer", "E195": "embraer", "E75L": "embraer",
            "A333": "a330", "A339": "a330",
            "A359": "a350", "A35K": "a350",
        }
        for designator, expected in designator_to_expected.items():
            got = ill.classify_aircraft_type(designator)
            if got != expected:
                return False, "classify_aircraft_type(%r) returned %r, expected %r" % (designator, got, expected)
        covered = set(designator_to_expected.values())
        if covered != set(ill.SHAPE_SLUGS):
            return False, "test table covers %r, missing %r" % (covered, set(ill.SHAPE_SLUGS) - covered)
        return True, ""
    check("classify_aircraft_type() maps real designators onto all seven SHAPE_SLUGS", _classify_all_seven_buckets)

    def _classify_normalizes_case_and_whitespace():
        for value in (" a20n ", "a20n", "A20N", "  A20N", "a20n  "):
            got = ill.classify_aircraft_type(value)
            if got != "a320":
                return False, "classify_aircraft_type(%r) returned %r, expected 'a320'" % (value, got)
        return True, ""
    check("classify_aircraft_type() normalizes lowercase and leading/trailing whitespace", _classify_normalizes_case_and_whitespace)

    def _classify_unknown_designator_is_none():
        for value in ("ZZZZ", "XYZ9", "UNKNOWN"):
            got = ill.classify_aircraft_type(value)
            if got is not None:
                return False, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)
        return True, ""
    check("classify_aircraft_type() returns None for an unrecognized designator", _classify_unknown_designator_is_none)

    def _classify_falsy_and_non_string_none():
        for value in (None, "", 0, 42, [], {}):
            got = ill.classify_aircraft_type(value)
            if got is not None:
                return False, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)
        return True, ""
    check(
        "classify_aircraft_type() returns None for falsy and non-string inputs (None, '', 0, 42, [], {}) without raising",
        _classify_falsy_and_non_string_none,
    )

    def _classify_hostile_inputs_never_raise():
        hostile = ("../../etc/passwd", "..\\..\\windows", "a/b/c", "..", "/etc/passwd")
        for value in hostile:
            got = ill.classify_aircraft_type(value)
            if got is not None:
                return False, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)
        return True, ""
    check(
        "classify_aircraft_type() returns None (never raises) for hostile path-separator/parent-dir inputs (T-03.1-03-01)",
        _classify_hostile_inputs_never_raise,
    )

    def _type_shape_buckets_contract():
        bad_values = [v for v in ill._TYPE_SHAPE_BUCKETS.values() if v not in ill.SHAPE_SLUGS]
        if bad_values:
            return False, "_TYPE_SHAPE_BUCKETS contains values not in SHAPE_SLUGS: %r" % (bad_values,)
        key_re = re.compile(r"^[A-Z0-9]{3,4}$")
        bad_keys = [k for k in ill._TYPE_SHAPE_BUCKETS if not key_re.match(k)]
        if bad_keys:
            return False, "_TYPE_SHAPE_BUCKETS contains keys not uppercase-ASCII 3-4 chars: %r" % (bad_keys,)
        return True, ""
    check(
        "every _TYPE_SHAPE_BUCKETS value is a member of SHAPE_SLUGS and every key is uppercase ASCII 3-4 chars",
        _type_shape_buckets_contract,
    )

    # --- select_illustration() against the real vendored set ----------------

    def _select_real_air_france():
        path = ill.select_illustration({"airline_name": "Air France"})
        if path is None or not os.path.isfile(path) or os.path.basename(path) != "air-france.png":
            return False, "select_illustration(Air France) returned %r" % (path,)
        return True, ""
    check("select_illustration({'airline_name': 'Air France'}) returns the real air-france.png path", _select_real_air_france)

    def _select_real_vueling():
        path = ill.select_illustration({"airline_name": "Vueling Airlines"})
        if path is None or not os.path.isfile(path) or os.path.basename(path) != "vueling-airlines.png":
            return False, "select_illustration(Vueling Airlines) returned %r" % (path,)
        return True, ""
    check("select_illustration({'airline_name': 'Vueling Airlines'}) returns the real vueling-airlines.png path", _select_real_vueling)

    def _select_unknown_airline_falls_back():
        path = ill.select_illustration({"airline_name": "Nonexistent Air"})
        fallback = ill.generic_fallback_path()
        if path != fallback:
            return False, "unknown airline returned %r, expected the fallback path %r" % (path, fallback)
        return True, ""
    check("select_illustration() with an unknown airline returns the generic fallback path", _select_unknown_airline_falls_back)

    def _select_none_route_falls_back():
        path = ill.select_illustration(None)
        fallback = ill.generic_fallback_path()
        if path != fallback:
            return False, "select_illustration(None) returned %r, expected the fallback path %r" % (path, fallback)
        return True, ""
    check("select_illustration(None) returns the generic fallback path", _select_none_route_falls_back)

    def _select_route_missing_airline_name_falls_back():
        path = ill.select_illustration({})
        fallback = ill.generic_fallback_path()
        if path != fallback:
            return False, "select_illustration({}) returned %r, expected the fallback path %r" % (path, fallback)
        return True, ""
    check(
        "select_illustration() with a route lacking airline_name returns the generic fallback path",
        _select_route_missing_airline_name_falls_back,
    )

    def _select_route_non_string_airline_name_falls_back():
        path = ill.select_illustration({"airline_name": 123})
        fallback = ill.generic_fallback_path()
        if path != fallback:
            return False, "select_illustration(airline_name=123) returned %r, expected the fallback path %r" % (path, fallback)
        return True, ""
    check(
        "select_illustration() with a non-string airline_name returns the generic fallback path",
        _select_route_non_string_airline_name_falls_back,
    )

    def _select_never_raises():
        malformed = (
            None,
            {},
            {"airline_name": None},
            {"airline_name": 123},
            {"airline_name": "Nonexistent Air"},
            "not-a-dict",
            42,
            ["a", "list"],
        )
        for route in malformed:
            ill.select_illustration(route)  # must not raise for any of these
        return True, ""
    check("select_illustration() never raises across a battery of malformed inputs", _select_never_raises)

    def _select_returns_none_only_when_fallback_missing():
        empty_dir = tempfile.mkdtemp(prefix="skypane-illustrations-empty-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = empty_dir
            got = ill.select_illustration({"airline_name": "Air France"})
            if got is not None:
                return False, "with no files present at all, select_illustration() returned %r, expected None" % (got,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(empty_dir, ignore_errors=True)
    check(
        "select_illustration() returns None only when even the generic fallback file is absent",
        _select_returns_none_only_when_fallback_missing,
    )

    # --- illustration_path_for_key() boundary --------------------------------

    def _path_for_key_rejects_separator():
        for bad_key in ("../../etc/passwd", "sub/dir", "a\\b", ".."):
            got = ill.illustration_path_for_key(bad_key)
            if got is not None:
                return False, "illustration_path_for_key(%r) returned %r, expected None" % (bad_key, got)
        return True, ""
    check(
        "illustration_path_for_key() rejects any key containing a path separator or parent-dir segment",
        _path_for_key_rejects_separator,
    )

    def _generic_fallback_path_points_at_real_file():
        path = ill.generic_fallback_path()
        if not os.path.isfile(path) or os.path.basename(path) != "generic-fallback.png":
            return False, "generic_fallback_path() returned %r, which is not a real generic-fallback.png file" % (path,)
        return True, ""
    check("generic_fallback_path() points at the real, vendored generic-fallback.png", _generic_fallback_path_points_at_real_file)

    # --- validate_illustration_file() rejection categories -------------------

    tmp_dir = tempfile.mkdtemp(prefix="skypane-illustrations-fixtures-")
    try:
        def _rgba(w, h, alpha=200):
            return Image.new("RGBA", (w, h), (10, 20, 30, alpha))

        non_png_path = os.path.join(tmp_dir, "not-really-a-png.png")
        Image.new("RGB", (1400, 700), (0, 0, 0)).save(non_png_path, format="JPEG")

        no_alpha_path = os.path.join(tmp_dir, "no-alpha.png")
        Image.new("RGB", (1400, 700), (0, 0, 0)).save(no_alpha_path, format="PNG")

        opaque_alpha_path = os.path.join(tmp_dir, "opaque-alpha.png")
        _rgba(1400, 700, alpha=255).save(opaque_alpha_path, format="PNG")

        narrow_path = os.path.join(tmp_dir, "narrow.png")
        _rgba(800, 400, alpha=180).save(narrow_path, format="PNG")

        portrait_path = os.path.join(tmp_dir, "portrait.png")
        _rgba(1200, 1600, alpha=180).save(portrait_path, format="PNG")

        def _rejects_non_png():
            problems = ill.validate_illustration_file(non_png_path)
            if not problems or not any("not a PNG" in p for p in problems):
                return False, "problems=%r, expected a 'not a PNG' message" % (problems,)
            return True, ""
        check("validate_illustration_file() rejects a non-PNG file with a distinct message", _rejects_non_png)

        def _rejects_no_alpha():
            problems = ill.validate_illustration_file(no_alpha_path)
            if not problems or not any("alpha" in p for p in problems):
                return False, "problems=%r, expected an alpha-channel message" % (problems,)
            return True, ""
        check("validate_illustration_file() rejects a PNG with no alpha channel with a distinct message", _rejects_no_alpha)

        def _rejects_opaque_alpha():
            problems = ill.validate_illustration_file(opaque_alpha_path)
            if not problems or not any("opaque" in p for p in problems):
                return False, "problems=%r, expected a fully-opaque-alpha message" % (problems,)
            return True, ""
        check(
            "validate_illustration_file() rejects a PNG whose alpha channel is fully opaque with a distinct message",
            _rejects_opaque_alpha,
        )

        def _rejects_narrow_width():
            problems = ill.validate_illustration_file(narrow_path)
            if not problems or not any("width" in p and "minimum" in p for p in problems):
                return False, "problems=%r, expected a below-minimum-width message" % (problems,)
            return True, ""
        check(
            "validate_illustration_file() rejects a PNG narrower than the minimum width with a distinct message",
            _rejects_narrow_width,
        )

        def _rejects_portrait():
            problems = ill.validate_illustration_file(portrait_path)
            if not problems or not any("landscape" in p for p in problems):
                return False, "problems=%r, expected a not-landscape message" % (problems,)
            return True, ""
        check("validate_illustration_file() rejects a portrait PNG with a distinct message", _rejects_portrait)

        def _rejects_oversized_pixel_count():
            original_max = ill.ILLUSTRATION_MAX_PIXELS
            oversized_path = os.path.join(tmp_dir, "oversized.png")
            try:
                ill.ILLUSTRATION_MAX_PIXELS = 1_000_000
                _rgba(2000, 1000, alpha=180).save(oversized_path, format="PNG")  # 2M pixels > the 1M test cap
                problems = ill.validate_illustration_file(oversized_path)
            finally:
                ill.ILLUSTRATION_MAX_PIXELS = original_max
            if not problems or not any("exceeds" in p for p in problems):
                return False, "problems=%r, expected a pixel-count-exceeds-cap message" % (problems,)
            return True, ""
        check(
            "validate_illustration_file() rejects a PNG whose pixel count exceeds the cap with a distinct message",
            _rejects_oversized_pixel_count,
        )

        def _accepts_a_real_vendored_file():
            real_path = ill.illustration_path_for_key("air-france")
            problems = ill.validate_illustration_file(real_path)
            if problems:
                return False, "real vendored air-france.png failed validation: %r" % (problems,)
            return True, ""
        check("validate_illustration_file() accepts the real, vendored air-france.png with zero problems", _accepts_a_real_vendored_file)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # --- required_filenames() / whole-set integration ------------------------

    def _required_filenames_contract():
        names = ill.required_filenames()
        if ill.GENERIC_FALLBACK_FILENAME not in names:
            return False, "required_filenames() %r does not contain %r" % (names, ill.GENERIC_FALLBACK_FILENAME)
        pattern = re.compile(r"^[a-z0-9-]+\.png$")
        bad = [n for n in names if not pattern.match(n)]
        if bad:
            return False, "required_filenames() contains entries not matching ^[a-z0-9-]+\\.png$: %r" % (bad,)
        return True, ""
    check("required_filenames() contains generic-fallback.png and every entry matches ^[a-z0-9-]+\\.png$", _required_filenames_contract)

    def _all_required_files_pass_validation():
        problems_by_file = {}
        for name in ill.required_filenames():
            path = os.path.join(ill.ILLUSTRATION_DIR, name)
            problems = ill.validate_illustration_file(path)
            if problems:
                problems_by_file[name] = problems
        if problems_by_file:
            return False, "the following required files fail validation: %r" % (problems_by_file,)
        return True, ""
    check(
        "every file in required_filenames() exists in the vendored set and passes validate_illustration_file()",
        _all_required_files_pass_validation,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("illustrations: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
