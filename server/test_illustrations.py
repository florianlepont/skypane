#!/usr/bin/env python3
"""Contract tests for server/plane/illustrations.py's per-airline
illustration selection module.

Covers normalise_airline_key(), select_illustration() (including its
never-raises guarantee and its "None only when even the fallback is
missing" degradation), validate_illustration_file()'s rejection
categories, the target/required/outstanding filename contracts, the
per-airline variant table, and the override-resolution layer
(resolved_illustration_path(), select_illustration()'s state_dir
parameter, set_override_state_dir()). Tests against the real,
already-vendored files under server/assets/icons/illustrations/ where
they are stable and pass --validate, rather than synthetic fixtures -
malformed fixtures are still built programmatically in tmp_path since no
broken binary should ever be committed to the repo.
"""
import hashlib
import os
import re
import sys

import pytest
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.plane.illustrations as ill  # noqa: E402


def _make_fixture_png(path, size=(1400, 700), colour=(10, 20, 30, 200)):
    Image.new("RGBA", size, colour).save(path, format="PNG")


def _touch_override_file(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"not a real png - path-existence fixture only")


@pytest.fixture(autouse=True)
def _reset_override_state_dir():
    """Every check that touches set_override_state_dir() resets it
    explicitly, but this belt-and-braces autouse fixture guarantees no
    leftover process-default override dir survives into an unrelated
    test even if a future edit drops that discipline.
    """
    yield
    ill.set_override_state_dir(None)


# --- normalise_airline_key() -----------------------------------------------

def test_normalise_airline_key_air_algerie():
    """normalise_airline_key('Air Algérie') == 'air-algerie'"""
    got = ill.normalise_airline_key("Air Algérie")
    assert got == "air-algerie", "got %r, expected 'air-algerie'" % (got,)


def test_normalise_airline_key_air_corsica():
    """normalise_airline_key('Air Corsica') == 'air-corsica'"""
    got = ill.normalise_airline_key("Air Corsica")
    assert got == "air-corsica", "got %r, expected 'air-corsica'" % (got,)


def test_normalise_airline_key_falsy_and_non_string_returns_none():
    """normalise_airline_key('') / (None) / (42) all return None without raising"""
    for value in ("", None, 42):
        got = ill.normalise_airline_key(value)
        assert got is None, "normalise_airline_key(%r) returned %r, expected None" % (value, got)


# --- classify_aircraft_type() / SHAPE_SLUGS ---------------------------------

def test_classify_aircraft_type_all_seven_buckets():
    """classify_aircraft_type() maps real designators onto all seven SHAPE_SLUGS"""
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
        assert got == expected, "classify_aircraft_type(%r) returned %r, expected %r" % (designator, got, expected)
    covered = set(designator_to_expected.values())
    assert covered == set(ill.SHAPE_SLUGS), "test table covers %r, missing %r" % (
        covered, set(ill.SHAPE_SLUGS) - covered,
    )


def test_classify_aircraft_type_normalizes_case_and_whitespace():
    """classify_aircraft_type() normalizes lowercase and leading/trailing whitespace"""
    for value in (" a20n ", "a20n", "A20N", "  A20N", "a20n  "):
        got = ill.classify_aircraft_type(value)
        assert got == "a320", "classify_aircraft_type(%r) returned %r, expected 'a320'" % (value, got)


def test_classify_aircraft_type_unknown_designator_is_none():
    """classify_aircraft_type() returns None for an unrecognized designator"""
    for value in ("ZZZZ", "XYZ9", "UNKNOWN"):
        got = ill.classify_aircraft_type(value)
        assert got is None, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)


def test_classify_aircraft_type_falsy_and_non_string_returns_none():
    """classify_aircraft_type() returns None for falsy and non-string inputs (None, '', 0, 42, [], {}) without raising"""
    for value in (None, "", 0, 42, [], {}):
        got = ill.classify_aircraft_type(value)
        assert got is None, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)


def test_classify_aircraft_type_hostile_inputs_never_raise():
    """classify_aircraft_type() returns None (never raises) for hostile path-separator/parent-dir inputs (T-03.1-03-01)"""
    hostile = ("../../etc/passwd", "..\\..\\windows", "a/b/c", "..", "/etc/passwd")
    for value in hostile:
        got = ill.classify_aircraft_type(value)
        assert got is None, "classify_aircraft_type(%r) returned %r, expected None" % (value, got)


def test_type_shape_buckets_contract():
    """every _TYPE_SHAPE_BUCKETS value is a member of SHAPE_SLUGS and every key is uppercase ASCII 3-4 chars"""
    bad_values = [v for v in ill._TYPE_SHAPE_BUCKETS.values() if v not in ill.SHAPE_SLUGS]
    assert not bad_values, "_TYPE_SHAPE_BUCKETS contains values not in SHAPE_SLUGS: %r" % (bad_values,)
    key_re = re.compile(r"^[A-Z0-9]{3,4}$")
    bad_keys = [k for k in ill._TYPE_SHAPE_BUCKETS if not key_re.match(k)]
    assert not bad_keys, "_TYPE_SHAPE_BUCKETS contains keys not uppercase-ASCII 3-4 chars: %r" % (bad_keys,)


# --- select_illustration() against the real vendored set -------------------

def test_select_illustration_real_air_france():
    """select_illustration({'airline_name': 'Air France'}) returns the real air-france.png path"""
    path = ill.select_illustration({"airline_name": "Air France"})
    assert path is not None and os.path.isfile(path) and os.path.basename(path) == "air-france.png", (
        "select_illustration(Air France) returned %r" % (path,)
    )


def test_select_illustration_real_vueling():
    """select_illustration({'airline_name': 'Vueling Airlines'}) returns the real vueling-airlines.png path"""
    path = ill.select_illustration({"airline_name": "Vueling Airlines"})
    assert path is not None and os.path.isfile(path) and os.path.basename(path) == "vueling-airlines.png", (
        "select_illustration(Vueling Airlines) returned %r" % (path,)
    )


def test_select_illustration_unknown_airline_falls_back():
    """select_illustration() with an unknown airline returns the generic fallback path"""
    path = ill.select_illustration({"airline_name": "Nonexistent Air"})
    fallback = ill.generic_fallback_path()
    assert path == fallback, "unknown airline returned %r, expected the fallback path %r" % (path, fallback)


def test_select_illustration_none_route_falls_back():
    """select_illustration(None) returns the generic fallback path"""
    path = ill.select_illustration(None)
    fallback = ill.generic_fallback_path()
    assert path == fallback, "select_illustration(None) returned %r, expected the fallback path %r" % (path, fallback)


def test_select_illustration_route_missing_airline_name_falls_back():
    """select_illustration() with a route lacking airline_name returns the generic fallback path"""
    path = ill.select_illustration({})
    fallback = ill.generic_fallback_path()
    assert path == fallback, "select_illustration({}) returned %r, expected the fallback path %r" % (path, fallback)


def test_select_illustration_route_non_string_airline_name_falls_back():
    """select_illustration() with a non-string airline_name returns the generic fallback path"""
    path = ill.select_illustration({"airline_name": 123})
    fallback = ill.generic_fallback_path()
    assert path == fallback, "select_illustration(airline_name=123) returned %r, expected the fallback path %r" % (
        path, fallback,
    )


def test_select_illustration_never_raises_malformed_battery():
    """select_illustration() never raises across a battery of malformed inputs"""
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


def test_select_illustration_returns_none_only_when_fallback_missing(tmp_path, monkeypatch):
    """select_illustration() returns None only when even the generic fallback file is absent"""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(empty_dir))
    got = ill.select_illustration({"airline_name": "Air France"})
    assert got is None, "with no files present at all, select_illustration() returned %r, expected None" % (got,)


# --- select_illustration() four-tier fallback -----------------------------

def test_select_illustration_tier1_airline_and_shape_match(tmp_path, monkeypatch):
    """select_illustration() Tier 1 returns the airline-and-shape file when it exists"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / "acme-air.png")
    _make_fixture_png(tmp_path / "acme-air-a320.png")
    path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
    assert path is not None and os.path.basename(path) == "acme-air-a320.png", (
        "Tier 1 returned %r, expected acme-air-a320.png" % (path,)
    )


def test_select_illustration_tier2_airline_only_when_shape_absent(tmp_path, monkeypatch):
    """select_illustration() Tier 2 returns the airline-only file when the shape file is absent"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / "acme-air.png")
    path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
    assert path is not None and os.path.basename(path) == "acme-air.png", (
        "Tier 2 (D-06) returned %r, expected acme-air.png" % (path,)
    )


def test_select_illustration_tier2_wins_over_tier3(tmp_path, monkeypatch):
    """select_illustration() Tier 2 wins over Tier 3 when both an airline file and a matching generic-shape file exist"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / "acme-air.png")
    _make_fixture_png(tmp_path / "generic-a320.png")
    path = ill.select_illustration({"airline_name": "Acme Air"}, "A320")
    assert path is not None and os.path.basename(path) == "acme-air.png", (
        "Tier 2 should win over Tier 3, got %r" % (path,)
    )


def test_select_illustration_tier3_neutral_shape_for_unrecognized_airline(tmp_path, monkeypatch):
    """select_illustration() Tier 3 returns the neutral shape file for an unrecognized airline with a known shape"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / "generic-a320.png")
    path = ill.select_illustration({"airline_name": "Unknown Air"}, "A320")
    assert path is not None and os.path.basename(path) == "generic-a320.png", (
        "Tier 3 (D-07) returned %r, expected generic-a320.png" % (path,)
    )


def test_select_illustration_tier3_applies_when_route_is_none(tmp_path, monkeypatch):
    """select_illustration() Tier 3 also applies when route is None but a type is supplied"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / "generic-a320.png")
    path = ill.select_illustration(None, "A320")
    assert path is not None and os.path.basename(path) == "generic-a320.png", (
        "Tier 3 with route=None returned %r, expected generic-a320.png" % (path,)
    )


def test_select_illustration_tier4_universal_fallback_when_neither_resolves(tmp_path, monkeypatch):
    """select_illustration() Tier 4 returns the universal fallback when neither key resolves"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / ill.GENERIC_FALLBACK_FILENAME)
    path = ill.select_illustration({"airline_name": "Unknown Air"}, "ZZZZ")
    assert path is not None and os.path.basename(path) == ill.GENERIC_FALLBACK_FILENAME, (
        "Tier 4 (D-08) returned %r, expected %r" % (path, ill.GENERIC_FALLBACK_FILENAME)
    )


def test_select_illustration_tier4_when_shape_classifies_but_no_generic_file(tmp_path, monkeypatch):
    """select_illustration() Tier 4 also returns when the shape classifies but no generic-{shape}.png file exists"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / ill.GENERIC_FALLBACK_FILENAME)
    path = ill.select_illustration({"airline_name": "Unknown Air"}, "A320")
    assert path is not None and os.path.basename(path) == ill.GENERIC_FALLBACK_FILENAME, (
        "Tier 4 returned %r, expected the universal fallback (no generic-a320.png present)" % (path,)
    )


def test_select_illustration_hostile_battery_never_raises_and_stays_confined(tmp_path, monkeypatch):
    """select_illustration() never raises for a hostile aircraft_type x malformed-route matrix, and no returned path escapes ILLUSTRATION_DIR (T-03.1-03-01)"""
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(tmp_path))
    _make_fixture_png(tmp_path / ill.GENERIC_FALLBACK_FILENAME)
    hostile_types = (
        "../../etc/passwd", "..\\..\\windows", "/etc/passwd", "..",
        "a" * 5000, None, 123, [], {}, object(),
    )
    malformed_routes = (
        None, {}, {"airline_name": None}, {"airline_name": 123}, "not-a-dict",
        42, ["a", "list"], {"airline_name": "../../etc/passwd"},
    )
    fixture_dir_real = os.path.realpath(str(tmp_path))
    for aircraft_type in hostile_types:
        for route in malformed_routes:
            got = ill.select_illustration(route, aircraft_type)  # must not raise
            if got is not None:
                got_real = os.path.realpath(got)
                assert os.path.commonpath([got_real, fixture_dir_real]) == fixture_dir_real, (
                    "select_illustration(%r, %r) returned a path outside ILLUSTRATION_DIR: %r" % (
                        route, aircraft_type, got,
                    )
                )


# --- illustration_path_for_key() boundary -----------------------------------

def test_illustration_path_for_key_rejects_separator():
    """illustration_path_for_key() rejects any key containing a path separator or parent-dir segment"""
    for bad_key in ("../../etc/passwd", "sub/dir", "a\\b", ".."):
        got = ill.illustration_path_for_key(bad_key)
        assert got is None, "illustration_path_for_key(%r) returned %r, expected None" % (bad_key, got)


def test_generic_fallback_path_points_at_real_file():
    """generic_fallback_path() points at the real, vendored generic-fallback.png"""
    path = ill.generic_fallback_path()
    assert os.path.isfile(path) and os.path.basename(path) == "generic-fallback.png", (
        "generic_fallback_path() returned %r, which is not a real generic-fallback.png file" % (path,)
    )


# --- validate_illustration_file() rejection categories ----------------------

def _rgba(w, h, alpha=200):
    return Image.new("RGBA", (w, h), (10, 20, 30, alpha))


def test_validate_illustration_file_rejects_non_png(tmp_path):
    """validate_illustration_file() rejects a non-PNG file with a distinct message"""
    non_png_path = tmp_path / "not-really-a-png.png"
    Image.new("RGB", (1400, 700), (0, 0, 0)).save(non_png_path, format="JPEG")
    problems = ill.validate_illustration_file(str(non_png_path))
    assert problems and any("not a PNG" in p for p in problems), (
        "problems=%r, expected a 'not a PNG' message" % (problems,)
    )


def test_validate_illustration_file_rejects_no_alpha(tmp_path):
    """validate_illustration_file() rejects a PNG with no alpha channel with a distinct message"""
    no_alpha_path = tmp_path / "no-alpha.png"
    Image.new("RGB", (1400, 700), (0, 0, 0)).save(no_alpha_path, format="PNG")
    problems = ill.validate_illustration_file(str(no_alpha_path))
    assert problems and any("alpha" in p for p in problems), (
        "problems=%r, expected an alpha-channel message" % (problems,)
    )


def test_validate_illustration_file_rejects_opaque_alpha(tmp_path):
    """validate_illustration_file() rejects a PNG whose alpha channel is fully opaque with a distinct message"""
    opaque_alpha_path = tmp_path / "opaque-alpha.png"
    _rgba(1400, 700, alpha=255).save(opaque_alpha_path, format="PNG")
    problems = ill.validate_illustration_file(str(opaque_alpha_path))
    assert problems and any("opaque" in p for p in problems), (
        "problems=%r, expected a fully-opaque-alpha message" % (problems,)
    )


def test_validate_illustration_file_rejects_narrow_width(tmp_path):
    """validate_illustration_file() rejects a PNG narrower than the minimum width with a distinct message"""
    narrow_path = tmp_path / "narrow.png"
    _rgba(800, 400, alpha=180).save(narrow_path, format="PNG")
    problems = ill.validate_illustration_file(str(narrow_path))
    assert problems and any("width" in p and "minimum" in p for p in problems), (
        "problems=%r, expected a below-minimum-width message" % (problems,)
    )


def test_validate_illustration_file_rejects_portrait(tmp_path):
    """validate_illustration_file() rejects a portrait PNG with a distinct message"""
    portrait_path = tmp_path / "portrait.png"
    _rgba(1200, 1600, alpha=180).save(portrait_path, format="PNG")
    problems = ill.validate_illustration_file(str(portrait_path))
    assert problems and any("landscape" in p for p in problems), (
        "problems=%r, expected a not-landscape message" % (problems,)
    )


def test_validate_illustration_file_rejects_oversized_pixel_count(tmp_path, monkeypatch):
    """validate_illustration_file() rejects a PNG whose pixel count exceeds the cap with a distinct message"""
    oversized_path = tmp_path / "oversized.png"
    monkeypatch.setattr(ill, "ILLUSTRATION_MAX_PIXELS", 1_000_000)
    _rgba(2000, 1000, alpha=180).save(oversized_path, format="PNG")  # 2M pixels > the 1M test cap
    problems = ill.validate_illustration_file(str(oversized_path))
    assert problems and any("exceeds" in p for p in problems), (
        "problems=%r, expected a pixel-count-exceeds-cap message" % (problems,)
    )


def test_validate_illustration_file_accepts_real_vendored_file():
    """validate_illustration_file() accepts the real, vendored air-france.png with zero problems"""
    real_path = ill.illustration_path_for_key("air-france")
    problems = ill.validate_illustration_file(real_path)
    assert not problems, "real vendored air-france.png failed validation: %r" % (problems,)


# --- required_filenames() / whole-set integration ---------------------------

def test_required_filenames_contract():
    """required_filenames() contains generic-fallback.png and every entry matches ^[a-z0-9-]+\\.png$"""
    names = ill.required_filenames()
    assert ill.GENERIC_FALLBACK_FILENAME in names, (
        "required_filenames() %r does not contain %r" % (names, ill.GENERIC_FALLBACK_FILENAME)
    )
    pattern = re.compile(r"^[a-z0-9-]+\.png$")
    bad = [n for n in names if not pattern.match(n)]
    assert not bad, "required_filenames() contains entries not matching ^[a-z0-9-]+\\.png$: %r" % (bad,)


def test_all_required_files_pass_validation():
    """every file in required_filenames() exists in the vendored set and passes validate_illustration_file()"""
    problems_by_file = {}
    for name in ill.required_filenames():
        path = os.path.join(ill.ILLUSTRATION_DIR, name)
        problems = ill.validate_illustration_file(path)
        if problems:
            problems_by_file[name] = problems
    assert not problems_by_file, "the following required files fail validation: %r" % (problems_by_file,)


# --- target_filenames() / required_filenames() / outstanding_filenames() ---

def test_targets_contain_all_generic_shapes_and_fallback():
    """target_filenames() contains one generic-{shape}.png per SHAPE_SLUGS plus the universal fallback, all matching ^[a-z0-9-]+\\.png$"""
    targets = ill.target_filenames()
    expected_generics = set("generic-%s.png" % shape for shape in ill.SHAPE_SLUGS)
    expected_generics.add(ill.GENERIC_FALLBACK_FILENAME)
    missing = expected_generics - set(targets)
    assert not missing, "target_filenames() is missing generic entries: %r" % (missing,)
    pattern = re.compile(r"^[a-z0-9-]+\.png$")
    bad = [n for n in targets if not pattern.match(n)]
    assert not bad, "target_filenames() contains entries not matching ^[a-z0-9-]+\\.png$: %r" % (bad,)


def test_targets_have_no_duplicates():
    """target_filenames() has no duplicate entries"""
    targets = ill.target_filenames()
    dupes = sorted({n for n in targets if targets.count(n) > 1})
    assert not dupes, "target_filenames() has duplicate entries: %r" % (dupes,)


def test_every_vendored_png_is_a_target():
    """every currently-vendored .png in ILLUSTRATION_DIR is a member of target_filenames() (widening the expected set did not orphan an existing asset)"""
    targets = set(ill.target_filenames())
    vendored = [f for f in os.listdir(ill.ILLUSTRATION_DIR) if f.endswith(".png")]
    orphaned = [f for f in vendored if f not in targets]
    assert not orphaned, "vendored .png files not present in target_filenames(): %r" % (orphaned,)


def test_required_is_subset_of_targets_and_keeps_baseline():
    """required_filenames() is a subset of target_filenames() and still contains every baseline file"""
    required = ill.required_filenames()
    targets = set(ill.target_filenames())
    not_in_targets = [n for n in required if n not in targets]
    assert not not_in_targets, "required_filenames() contains entries missing from target_filenames(): %r" % (
        not_in_targets,
    )
    baseline = set()
    for _callsign, airline_name in ill._LIVE_RESOLVED_AIRLINES:
        key = ill.normalise_airline_key(airline_name)
        if key:
            baseline.add(key + ".png")
    baseline.add(ill.GENERIC_FALLBACK_FILENAME)
    missing_baseline = baseline - set(required)
    assert not missing_baseline, "required_filenames() is missing baseline entries: %r" % (missing_baseline,)


def test_outstanding_is_targets_minus_on_disk():
    """outstanding_filenames() is exactly target_filenames() minus the on-disk set, in target order"""
    targets = ill.target_filenames()
    on_disk = set(f for f in os.listdir(ill.ILLUSTRATION_DIR) if f.endswith(".png"))
    expected_outstanding = [n for n in targets if n not in on_disk]
    got = ill.outstanding_filenames()
    assert got == expected_outstanding, "outstanding_filenames() = %r, expected %r" % (got, expected_outstanding)
    on_disk_in_outstanding = [n for n in got if n in on_disk]
    assert not on_disk_in_outstanding, "outstanding_filenames() contains files that exist on disk: %r" % (
        on_disk_in_outstanding,
    )


def test_p04_secondary_variants_and_primaries_present():
    """the four P-04 secondary variants appear in target_filenames() with the expected exact names, alongside their unsuffixed primaries"""
    targets = set(ill.target_filenames())
    expected_pairs = [
        ("air-corsica.png", "air-corsica-atr72.png"),
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
    assert not missing, "target_filenames() is missing P-04 primary/secondary entries: %r" % (missing,)


def test_target_airline_names_carries_current_brand_not_stale_names():
    """target_airline_names() contains the current-brand 'ASL Airlines France'/'Corsair'/'Air Corsica' strings, not the stale adsbdb-resolved names they replace"""
    names = ill.target_airline_names()
    for expected in ("ASL Airlines France", "Corsair", "Air Corsica"):
        assert expected in names, "target_airline_names() is missing the current-brand name %r: %r" % (expected, names)
    for stale in ("Europe Airpost", "Corsairfly", "CCM Airlines"):
        assert stale not in names, (
            "target_airline_names() must not contain the stale adsbdb-resolved string %r in place of the "
            "current-brand name" % (stale,)
        )


def test_km_malta_and_tuifly_belgium_targets_present():
    """target_airline_names()/target_filenames() carry 'KM Malta Airlines'/'TUIfly Belgium' and their derived filenames, and never 'Air Malta' or 'Jetairfly' (drift guard)"""
    names = ill.target_airline_names()
    for expected in ("KM Malta Airlines", "TUIfly Belgium"):
        assert expected in names, "target_airline_names() is missing %r: %r" % (expected, names)
    for stale in ("Air Malta", "Jetairfly"):
        assert stale not in names, "target_airline_names() must not contain %r" % (stale,)
    filenames = ill.target_filenames()
    for expected_file in ("km-malta-airlines.png", "tuifly-belgium.png"):
        assert expected_file in filenames, "target_filenames() is missing %r: not present" % (expected_file,)


def test_amelia_targets_present_and_total_is_52():
    """target_filenames() contains 'amelia.png'/'amelia-embraer.png' (delivered on disk) and totals 52 entries"""
    targets = ill.target_filenames()
    for expected_file in ("amelia.png", "amelia-embraer.png"):
        assert expected_file in targets, "target_filenames() is missing %r: not present" % (expected_file,)
        assert os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, expected_file)), (
            "%r is a target but missing on disk - expected it to be delivered" % (expected_file,)
        )
    assert len(targets) == 52, "target_filenames() has %d entries, expected 52" % (len(targets),)


def test_renamed_files_exist_superseded_names_do_not():
    """the four renamed illustration files (air-corsica/air-corsica-atr72/asl-airlines-france/corsair) exist on disk; the four superseded filenames they replace do not"""
    renamed = ("air-corsica.png", "air-corsica-atr72.png", "asl-airlines-france.png", "corsair.png")
    superseded = ("ccm-airlines.png", "ccm-airlines-atr72.png", "europe-airpost.png", "corsairfly.png")
    missing = [f for f in renamed if not os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, f))]
    assert not missing, "renamed file(s) missing on disk: %r" % (missing,)
    still_present = [f for f in superseded if os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, f))]
    assert not still_present, "superseded filename(s) still present on disk: %r" % (still_present,)


def test_lgt_targets_present_and_wizz_reuse_guard_holds():
    """target_airline_names()/target_filenames() carry 'Air France Hop'/'KlasJet' (with 'Air France'/'Wizz Air' still present as distinct names) and the three new filenames (delivered on disk); the Wizz Air Malta reuse guard holds - no Malta-specific Wizz entry exists in either list"""
    names = ill.target_airline_names()
    for expected in ("Air France Hop", "KlasJet", "Air France", "Wizz Air"):
        assert expected in names, "target_airline_names() is missing %r: %r" % (expected, names)

    filenames = ill.target_filenames()
    new_files = ("air-france-hop.png", "air-france-hop-atr72.png", "klasjet.png")
    for expected_file in new_files:
        assert expected_file in filenames, "target_filenames() is missing %r: not present" % (expected_file,)
        assert os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, expected_file)), (
            "%r is a target but missing on disk - expected it to be delivered" % (expected_file,)
        )

    # Reuse guard: no member of either list, other than the exact
    # "Wizz Air" name / wizz-air.png filename, may start with the Wizz
    # brand token.
    wizz_names = [n for n in names if n.lower().startswith("wizz")]
    assert wizz_names == ["Wizz Air"], (
        "target_airline_names() must contain exactly one Wizz-brand entry, 'Wizz Air': got %r" % (wizz_names,)
    )
    wizz_files = [f for f in filenames if f.startswith("wizz")]
    assert wizz_files == ["wizz-air.png"], (
        "target_filenames() must contain exactly one Wizz-brand entry, 'wizz-air.png': got %r" % (wizz_files,)
    )


# --- target_variants_by_airline() ------------------------------------------

def test_variants_by_airline_matches_names_order_and_count():
    """target_variants_by_airline() returns 36 pairs in the same order as target_airline_names()"""
    pairs = ill.target_variants_by_airline()
    assert len(pairs) == 36, "target_variants_by_airline() returned %d pairs, expected 36" % (len(pairs),)
    got_names = [name for name, _shapes in pairs]
    expected_names = ill.target_airline_names()
    assert got_names == expected_names, "target_variants_by_airline() names %r != target_airline_names() %r" % (
        got_names, expected_names,
    )


def test_variants_air_caraibes_three_shapes_in_order():
    """target_variants_by_airline()'s Air Caraïbes pair carries exactly ['a330', 'a350-1000', 'atr72'], in order"""
    pairs = dict(ill.target_variants_by_airline())
    got = pairs.get("Air Caraïbes")
    assert got == ["a330", "a350-1000", "atr72"], "Air Caraïbes shapes %r != expected %r" % (
        got, ["a330", "a350-1000", "atr72"],
    )


def test_variants_air_france_empty_list_not_none():
    """target_variants_by_airline()'s Air France pair (a single None-shape entry) carries an empty list, not [None]"""
    pairs = dict(ill.target_variants_by_airline())
    got = pairs.get("Air France")
    assert got == [], "Air France shapes %r, expected an empty list (not a list holding None)" % (got,)


def test_variants_no_none_and_a350_1000_survives():
    """no target_variants_by_airline() shape list contains None, and 'a350-1000' survives (not dropped by a SHAPE_SLUGS membership test)"""
    pairs = ill.target_variants_by_airline()
    for name, shapes in pairs:
        assert None not in shapes, "airline %r's shape list contains None: %r" % (name, shapes)
    all_shapes = [shape for _name, shapes in pairs for shape in shapes]
    assert "a350-1000" in all_shapes, (
        "'a350-1000' is missing from target_variants_by_airline()'s flattened shapes: %r" % (all_shapes,)
    )


def test_variants_derived_from_targets_no_second_table(monkeypatch):
    """target_variants_by_airline() reflects _ILLUSTRATION_TARGETS directly, with no separate hardcoded table"""
    fake_targets = [
        ("Acme Air", None, "note"),
        ("Acme Air", "a320", "note"),
        ("Acme Air", "a350-1000", "note"),
        ("Zephyr Jet", None, "note"),
    ]
    monkeypatch.setattr(ill, "_ILLUSTRATION_TARGETS", fake_targets)
    got = ill.target_variants_by_airline()
    expected = [("Acme Air", ["a320", "a350-1000"]), ("Zephyr Jet", [])]
    assert got == expected, (
        "target_variants_by_airline() did not reflect a monkeypatched _ILLUSTRATION_TARGETS: "
        "got %r, expected %r" % (got, expected)
    )


# --- override resolution layer ---------------------------------------------

def test_resolved_path_override_vs_vendored(tmp_path):
    """resolved_illustration_path() returns the override path when it exists, and the vendored path when it does not"""
    vendored = ill.illustration_path_for_key("air-france")
    assert vendored is not None and os.path.isfile(vendored), "expected the real vendored air-france.png to exist as a baseline"
    got = ill.resolved_illustration_path("air-france", str(tmp_path))
    assert got == vendored, (
        "with no override present, resolved_illustration_path() returned %r, expected the vendored path %r" % (
            got, vendored,
        )
    )
    override_path = tmp_path / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "air-france.png"
    _touch_override_file(str(override_path))
    got = ill.resolved_illustration_path("air-france", str(tmp_path))
    assert got == str(override_path), (
        "with an override present, resolved_illustration_path() returned %r, expected the override path %r" % (
            got, override_path,
        )
    )


def test_select_illustration_state_dir_override_vs_no_state_dir(tmp_path):
    """select_illustration(..., state_dir=tmp) returns the override path when one exists for that key; the same call with no state_dir still returns the vendored path"""
    vendored = ill.illustration_path_for_key("air-france")
    override_path = tmp_path / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "air-france.png"
    _touch_override_file(str(override_path))
    with_state_dir = ill.select_illustration({"airline_name": "Air France"}, state_dir=str(tmp_path))
    without_state_dir = ill.select_illustration({"airline_name": "Air France"})
    assert with_state_dir == str(override_path), (
        "select_illustration(..., state_dir=tmp) returned %r, expected the override path %r" % (
            with_state_dir, override_path,
        )
    )
    assert without_state_dir == vendored, (
        "select_illustration() with no state_dir returned %r, expected the vendored path %r" % (
            without_state_dir, vendored,
        )
    )
    assert with_state_dir != without_state_dir, (
        "the two calls must be provably different values, got the same path %r for both" % (with_state_dir,)
    )


def test_tier1_override_precedence_and_tier_isolation(tmp_path, monkeypatch):
    """select_illustration() Tier 1 override wins over the vendored Tier 1 file; an override for the bare Tier 2 airline key does not displace a vendored Tier 1 file - tier precedence is unchanged, only the per-tier source changes"""
    fixture_dir = tmp_path / "vendored"
    fixture_dir.mkdir()
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(fixture_dir))
    _make_fixture_png(fixture_dir / "acme-air-a320.png")

    # An override for the Tier 1 key (airline-shape) wins over the
    # vendored Tier 1 file.
    tier1_override = state_dir / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "acme-air-a320.png"
    _touch_override_file(str(tier1_override))
    path = ill.select_illustration({"airline_name": "Acme Air"}, "A320", state_dir=str(state_dir))
    assert path == str(tier1_override), "Tier 1 override did not win: got %r, expected %r" % (path, tier1_override)

    # An override for the bare airline (Tier 2) key must NOT displace the
    # vendored Tier 1 file - tier precedence is unchanged, only the
    # per-tier source changes.
    os.remove(tier1_override)
    tier2_override = state_dir / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "acme-air.png"
    _touch_override_file(str(tier2_override))
    path = ill.select_illustration({"airline_name": "Acme Air"}, "A320", state_dir=str(state_dir))
    vendored_tier1 = str(fixture_dir / "acme-air-a320.png")
    assert path == vendored_tier1, (
        "a Tier 2 override must not displace the vendored Tier 1 file: got %r, expected %r" % (path, vendored_tier1)
    )


def test_override_hostile_key_confinement(tmp_path, monkeypatch):
    """override_path_for_key() returns None for a battery of hostile keys, and select_illustration() with a state_dir never returns a path outside ILLUSTRATION_DIR or the override directory, across a hostile aircraft_type x malformed-route matrix (T-v26-01-01)"""
    fixture_dir = tmp_path / "vendored"
    fixture_dir.mkdir()
    state_dir = tmp_path / "state"
    monkeypatch.setattr(ill, "ILLUSTRATION_DIR", str(fixture_dir))
    _make_fixture_png(fixture_dir / ill.GENERIC_FALLBACK_FILENAME)

    hostile_keys = ("../../etc/passwd", "..\\..\\windows", "a/b/c", "..", "/etc/passwd")
    for bad_key in hostile_keys:
        got = ill.override_path_for_key(bad_key, str(state_dir))
        assert got is None, "override_path_for_key(%r) returned %r, expected None" % (bad_key, got)

    hostile_types = (
        "../../etc/passwd", "..\\..\\windows", "/etc/passwd", "..",
        "a" * 5000, None, 123, [], {}, object(),
    )
    malformed_routes = (
        None, {}, {"airline_name": None}, {"airline_name": 123}, "not-a-dict",
        42, ["a", "list"], {"airline_name": "../../etc/passwd"},
    )
    fixture_dir_real = os.path.realpath(str(fixture_dir))
    override_dir_real = os.path.realpath(str(state_dir / ill.ILLUSTRATION_OVERRIDE_DIRNAME))
    for aircraft_type in hostile_types:
        for route in malformed_routes:
            got = ill.select_illustration(route, aircraft_type, state_dir=str(state_dir))  # must not raise
            if got is not None:
                got_real = os.path.realpath(got)
                in_vendored = os.path.commonpath([got_real, fixture_dir_real]) == fixture_dir_real
                in_override = os.path.commonpath([got_real, override_dir_real]) == override_dir_real
                assert in_vendored or in_override, (
                    "select_illustration(%r, %r, state_dir=...) returned a path outside both ILLUSTRATION_DIR "
                    "and the override dir: %r" % (route, aircraft_type, got)
                )


def test_vendored_file_immutable_after_override_resolution(tmp_path):
    """the vendored file's bytes are unchanged after a battery of override resolution calls"""
    vendored = ill.illustration_path_for_key("air-france")
    with open(vendored, "rb") as f:
        before = hashlib.sha256(f.read()).hexdigest()
    override_path = tmp_path / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "air-france.png"
    _touch_override_file(str(override_path))
    ill.resolved_illustration_path("air-france", str(tmp_path))
    ill.select_illustration({"airline_name": "Air France"}, state_dir=str(tmp_path))
    ill.select_illustration({"airline_name": "Air France"})
    with open(vendored, "rb") as f:
        after = hashlib.sha256(f.read()).hexdigest()
    assert before == after, (
        "vendored air-france.png bytes changed after override resolution calls (before=%s after=%s)" % (
            before, after,
        )
    )


def test_set_override_state_dir_round_trip(tmp_path):
    """set_override_state_dir() round trip: setting it makes a bare select_illustration() call pick up the override; resetting to None restores the vendored path, and the reset is guaranteed by a finally block"""
    override_path = tmp_path / ill.ILLUSTRATION_OVERRIDE_DIRNAME / "air-france.png"
    _touch_override_file(str(override_path))
    vendored = ill.illustration_path_for_key("air-france")

    ill.set_override_state_dir(str(tmp_path))
    got_with_default = ill.select_illustration({"airline_name": "Air France"})
    assert got_with_default == str(override_path), (
        "after set_override_state_dir(tmp), a bare select_illustration() call returned %r, expected the "
        "override path %r" % (got_with_default, override_path)
    )

    ill.set_override_state_dir(None)
    got_after_reset = ill.select_illustration({"airline_name": "Air France"})
    assert got_after_reset == vendored, (
        "after set_override_state_dir(None), select_illustration() returned %r, expected the vendored path %r "
        "- the reset did not take effect" % (got_after_reset, vendored)
    )


# --- Nine [DEVELOPER-OBSERVED] targets, delivered on arrival --------------

_V9C_NEW_FILENAMES = (
    "qatar-amiri-flight.png",
    "royal-jordanian.png",
    "saudi-royal-aviation.png",
    "saudia.png",
    "south-korea-government.png",
    "la-compagnie.png",
    "gendarmerie-nationale.png",
    "iraqi-government.png",
    "french-air-force.png",
)


def test_v9c_nine_new_targets_present_and_tenth_excluded():
    """target_filenames() contains all nine new filenames (delivered on disk), 'French Air Force' is a target_airline_names() member, and the deferred tenth file 'saudi-special-flight.png' is neither a target nor present on disk"""
    filenames = ill.target_filenames()
    for expected_file in _V9C_NEW_FILENAMES:
        assert expected_file in filenames, "target_filenames() is missing %r: not present" % (expected_file,)
        assert os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, expected_file)), (
            "%r is a target but missing on disk - expected it to be delivered" % (expected_file,)
        )
    names = ill.target_airline_names()
    assert "French Air Force" in names, "target_airline_names() is missing 'French Air Force': %r" % (names,)
    # The tenth delivered file (unresolved operator mismatch) is neither
    # a target nor present on disk.
    assert "saudi-special-flight.png" not in filenames, (
        "'saudi-special-flight.png' must never be a target (QT-v9c-D-06)"
    )
    assert not os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, "saudi-special-flight.png")), (
        "'saudi-special-flight.png' must never be copied into the illustration directory (QT-v9c-D-06)"
    )


def test_every_airline_has_an_unsuffixed_primary_file_on_disk():
    """every airline in target_variants_by_airline() has an unsuffixed {slug}.png primary that is both a target_filenames() member and present on disk - protects the companion gallery card contract (airlines_page.py builds every card's <img src> from the primary key alone)"""
    # companion/pages/airlines_page.py's _airline_card_html() builds every
    # gallery card's <img src> from the PRIMARY key alone
    # (illustrations.normalise_airline_key(airline_name) + '.png'),
    # unconditionally - it never consults the shapes list for the image. A
    # shape-only target (no unsuffixed primary file) would therefore
    # render a 404 image in the companion gallery.
    for name, _shapes in ill.target_variants_by_airline():
        key = ill.normalise_airline_key(name)
        primary_filename = "%s.png" % key
        assert primary_filename in ill.target_filenames(), (
            "airline %r has no unsuffixed primary %r in target_filenames()" % (name, primary_filename)
        )
        assert os.path.isfile(os.path.join(ill.ILLUSTRATION_DIR, primary_filename)), (
            "airline %r's unsuffixed primary %r is a target but missing on disk" % (name, primary_filename)
        )

