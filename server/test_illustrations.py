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

EXPECTED_CHECK_COUNT = 43


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

    # --- select_illustration() four-tier fallback (Task 2, D-06/D-07/D-08) --

    def _make_fixture_png(path):
        Image.new("RGBA", (1400, 700), (10, 20, 30, 200)).save(path, format="PNG")

    def _tier1_airline_and_shape_match():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, "acme-air.png"))
            _make_fixture_png(os.path.join(fixture_dir, "acme-air-a320.png"))
            path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
            if path is None or os.path.basename(path) != "acme-air-a320.png":
                return False, "Tier 1 returned %r, expected acme-air-a320.png" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check("select_illustration() Tier 1 returns the airline-and-shape file when it exists", _tier1_airline_and_shape_match)

    def _tier2_airline_only_when_shape_absent():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, "acme-air.png"))
            path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
            if path is None or os.path.basename(path) != "acme-air.png":
                return False, "Tier 2 (D-06) returned %r, expected acme-air.png" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check("select_illustration() Tier 2 (D-06) returns the airline-only file when the shape file is absent", _tier2_airline_only_when_shape_absent)

    def _tier2_wins_over_tier3():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, "acme-air.png"))
            _make_fixture_png(os.path.join(fixture_dir, "generic-a320.png"))
            path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
            if path is None or os.path.basename(path) != "acme-air.png":
                return False, "Tier 2 should win over Tier 3, got %r" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check(
        "select_illustration() Tier 2 wins over Tier 3 when both an airline file and a matching generic-shape file exist",
        _tier2_wins_over_tier3,
    )

    def _tier3_neutral_shape_for_unrecognized_airline():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, "generic-a320.png"))
            path = ill.select_illustration({"airline_name": "Unknown Air"}, "A320")
            if path is None or os.path.basename(path) != "generic-a320.png":
                return False, "Tier 3 (D-07) returned %r, expected generic-a320.png" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check(
        "select_illustration() Tier 3 (D-07) returns the neutral shape file for an unrecognized airline with a known shape",
        _tier3_neutral_shape_for_unrecognized_airline,
    )

    def _tier3_applies_when_route_is_none():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, "generic-a320.png"))
            path = ill.select_illustration(None, "A320")
            if path is None or os.path.basename(path) != "generic-a320.png":
                return False, "Tier 3 with route=None returned %r, expected generic-a320.png" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check("select_illustration() Tier 3 also applies when route is None but a type is supplied", _tier3_applies_when_route_is_none)

    def _tier4_universal_fallback_when_neither_resolves():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, ill.GENERIC_FALLBACK_FILENAME))
            path = ill.select_illustration({"airline_name": "Unknown Air"}, "ZZZZ")
            if path is None or os.path.basename(path) != ill.GENERIC_FALLBACK_FILENAME:
                return False, "Tier 4 (D-08) returned %r, expected %r" % (path, ill.GENERIC_FALLBACK_FILENAME)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check(
        "select_illustration() Tier 4 (D-08) returns the universal fallback when neither key resolves",
        _tier4_universal_fallback_when_neither_resolves,
    )

    def _tier4_when_shape_classifies_but_no_generic_file():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, ill.GENERIC_FALLBACK_FILENAME))
            path = ill.select_illustration({"airline_name": "Unknown Air"}, "A320")
            if path is None or os.path.basename(path) != ill.GENERIC_FALLBACK_FILENAME:
                return False, "Tier 4 returned %r, expected the universal fallback (no generic-a320.png present)" % (path,)
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check(
        "select_illustration() Tier 4 also returns when the shape classifies but no generic-{shape}.png file exists",
        _tier4_when_shape_classifies_but_no_generic_file,
    )

    def _select_illustration_hostile_battery_never_raises_and_stays_confined():
        fixture_dir = tempfile.mkdtemp(prefix="skypane-illustrations-tiers-")
        original_dir = ill.ILLUSTRATION_DIR
        try:
            ill.ILLUSTRATION_DIR = fixture_dir
            _make_fixture_png(os.path.join(fixture_dir, ill.GENERIC_FALLBACK_FILENAME))
            hostile_types = (
                "../../etc/passwd", "..\\..\\windows", "/etc/passwd", "..",
                "a" * 5000, None, 123, [], {}, object(),
            )
            malformed_routes = (
                None, {}, {"airline_name": None}, {"airline_name": 123}, "not-a-dict",
                42, ["a", "list"], {"airline_name": "../../etc/passwd"},
            )
            fixture_dir_real = os.path.realpath(fixture_dir)
            for aircraft_type in hostile_types:
                for route in malformed_routes:
                    got = ill.select_illustration(route, aircraft_type)  # must not raise
                    if got is not None:
                        got_real = os.path.realpath(got)
                        if os.path.commonpath([got_real, fixture_dir_real]) != fixture_dir_real:
                            return False, "select_illustration(%r, %r) returned a path outside ILLUSTRATION_DIR: %r" % (
                                route, aircraft_type, got,
                            )
            return True, ""
        finally:
            ill.ILLUSTRATION_DIR = original_dir
            shutil.rmtree(fixture_dir, ignore_errors=True)
    check(
        "select_illustration() never raises for a hostile aircraft_type x malformed-route matrix, "
        "and no returned path escapes ILLUSTRATION_DIR (T-03.1-03-01)",
        _select_illustration_hostile_battery_never_raises_and_stays_confined,
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

    # --- target_filenames() / required_filenames() / outstanding_filenames() -

    def _targets_contain_all_generic_shapes_and_fallback():
        targets = ill.target_filenames()
        expected_generics = set("generic-%s.png" % shape for shape in ill.SHAPE_SLUGS)
        expected_generics.add(ill.GENERIC_FALLBACK_FILENAME)
        missing = expected_generics - set(targets)
        if missing:
            return False, "target_filenames() is missing generic entries: %r" % (missing,)
        pattern = re.compile(r"^[a-z0-9-]+\.png$")
        bad = [n for n in targets if not pattern.match(n)]
        if bad:
            return False, "target_filenames() contains entries not matching ^[a-z0-9-]+\\.png$: %r" % (bad,)
        return True, ""
    check(
        "target_filenames() contains one generic-{shape}.png per SHAPE_SLUGS plus the universal fallback, "
        "all matching ^[a-z0-9-]+\\.png$",
        _targets_contain_all_generic_shapes_and_fallback,
    )

    def _targets_have_no_duplicates():
        targets = ill.target_filenames()
        if len(targets) != len(set(targets)):
            dupes = sorted({n for n in targets if targets.count(n) > 1})
            return False, "target_filenames() has duplicate entries: %r" % (dupes,)
        return True, ""
    check("target_filenames() has no duplicate entries", _targets_have_no_duplicates)

    def _every_vendored_png_is_a_target():
        targets = set(ill.target_filenames())
        vendored = [f for f in os.listdir(ill.ILLUSTRATION_DIR) if f.endswith(".png")]
        orphaned = [f for f in vendored if f not in targets]
        if orphaned:
            return False, "vendored .png files not present in target_filenames(): %r" % (orphaned,)
        return True, ""
    check(
        "every currently-vendored .png in ILLUSTRATION_DIR is a member of target_filenames() "
        "(widening the expected set did not orphan an existing asset)",
        _every_vendored_png_is_a_target,
    )

    def _required_is_subset_of_targets_and_keeps_baseline():
        required = ill.required_filenames()
        targets = set(ill.target_filenames())
        not_in_targets = [n for n in required if n not in targets]
        if not_in_targets:
            return False, "required_filenames() contains entries missing from target_filenames(): %r" % (not_in_targets,)
        baseline = set()
        for _callsign, airline_name in ill._LIVE_RESOLVED_AIRLINES:
            key = ill.normalise_airline_key(airline_name)
            if key:
                baseline.add(key + ".png")
        baseline.add(ill.GENERIC_FALLBACK_FILENAME)
        missing_baseline = baseline - set(required)
        if missing_baseline:
            return False, "required_filenames() is missing baseline entries: %r" % (missing_baseline,)
        return True, ""
    check(
        "required_filenames() is a subset of target_filenames() and still contains every baseline file",
        _required_is_subset_of_targets_and_keeps_baseline,
    )

    def _outstanding_is_targets_minus_on_disk():
        targets = ill.target_filenames()
        on_disk = set(f for f in os.listdir(ill.ILLUSTRATION_DIR) if f.endswith(".png"))
        expected_outstanding = [n for n in targets if n not in on_disk]
        got = ill.outstanding_filenames()
        if got != expected_outstanding:
            return False, "outstanding_filenames() = %r, expected %r" % (got, expected_outstanding)
        on_disk_in_outstanding = [n for n in got if n in on_disk]
        if on_disk_in_outstanding:
            return False, "outstanding_filenames() contains files that exist on disk: %r" % (on_disk_in_outstanding,)
        return True, ""
    check(
        "outstanding_filenames() is exactly target_filenames() minus the on-disk set, in target order",
        _outstanding_is_targets_minus_on_disk,
    )

    def _p04_secondary_variants_and_primaries_present():
        targets = set(ill.target_filenames())
        expected_pairs = [
            ("ccm-airlines.png", "ccm-airlines-atr72.png"),
            ("transavia-france.png", "transavia-france-a320.png"),
            ("royal-air-maroc.png", "royal-air-maroc-embraer.png"),
            ("air-caraibes.png", "air-caraibes-a330.png"),
        ]
        missing = []
        for primary, secondary in expected_pairs:
            if primary not in targets:
                missing.append(primary)
            if secondary not in targets:
                missing.append(secondary)
        if missing:
            return False, "target_filenames() is missing P-04 primary/secondary entries: %r" % (missing,)
        return True, ""
    check(
        "the four P-04 secondary variants appear in target_filenames() with the expected exact names, "
        "alongside their unsuffixed primaries",
        _p04_secondary_variants_and_primaries_present,
    )

    # 43 (quick task 260827-hyy). target_airline_names() carries the
    # resolved (not the current-brand) strings for the three known rename
    # traps - it's what enrich.py's prefix table is checked against, so a
    # regression here would silently let a stale-brand mismatch back in.
    def _target_airline_names_carries_resolved_not_brand_names():
        names = ill.target_airline_names()
        for expected in ("Europe Airpost", "Corsairfly", "CCM Airlines"):
            if expected not in names:
                return False, "target_airline_names() is missing the resolved name %r: %r" % (expected, names)
        for stale_brand in ("ASL Airlines France", "Corsair International", "Air Corsica"):
            if stale_brand in names:
                return False, "target_airline_names() must not contain the current-brand label %r in place of the resolved name" % (stale_brand,)
        return True, ""
    check(
        "target_airline_names() contains the resolved 'Europe Airpost'/'Corsairfly'/'CCM Airlines' strings, "
        "not the current-brand labels they replace",
        _target_airline_names_carries_resolved_not_brand_names,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("illustrations: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
