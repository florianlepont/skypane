#!/usr/bin/env python3
"""Contract tests for server/plane/enrich.py's adsbdb.com enrichment client
(D-02, D-P2-05).

The module under test itself imports `requests`, but every outbound HTTP
call in this file is replaced with an injected fake transport (a callable
returning `(status_code, json_body)`, matching `lookup_route`'s injectable
`transport` parameter) - no test here makes a live network call, and no
test needs the `fake_providers` fixture, since none of these checks ever
exercises `enrich.default_transport()` itself (the real `requests.get`
wrapper).
"""
import copy
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.plane.enrich as enrich  # noqa: E402
import server.plane.illustrations as illustrations  # noqa: E402
from server.plane import manual_resolutions  # noqa: E402


def load_fixture(name):
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        return json.load(fh)


def make_transport(status_code, body, raise_exc=None, calls=None):
    """Build a fake transport matching lookup_route's injectable
    `transport(callsign, timeout)` contract - returns the fixed
    (status_code, body) pair (or raises `raise_exc`, simulating a
    connection error) and, if `calls` is provided, records every callsign
    it was invoked with so tests can assert on cache/normalisation
    behaviour without a live network call.
    """
    def transport(callsign, timeout=None):
        if calls is not None:
            calls.append(callsign)
        if raise_exc is not None:
            raise raise_exc
        return status_code, body
    return transport


@pytest.fixture
def hit_body():
    return load_fixture("adsbdb_hit_TVF16VB.json")


@pytest.fixture
def miss_fixture():
    # real recorded adsbdb miss (fixtures/README.md): {"http_status": 404,
    # "body": {"response": "unknown callsign"}} - EJU84YF is a confirmed
    # real 404, not an invented/hypothetical miss.
    return load_fixture("adsbdb_miss_EJU84YF.json")


@pytest.fixture
def aia_hit_body():
    return load_fixture("adsbdb_hit_AIA6412.json")["body"]


@pytest.fixture(autouse=True)
def _reset_manual_registry_state_dir():
    """Every check that touches manual_resolutions.set_manual_registry_state_dir()
    resets it in its own try/finally, but this belt-and-braces autouse
    fixture guarantees no leftover state dir survives into an unrelated
    test even if a future edit drops that discipline (MR-4 independence).
    """
    yield
    manual_resolutions.set_manual_registry_state_dir(None)


def test_hit_fixture_normalises(hit_body):
    """replaying the real recorded adsbdb hit (TVF16VB) yields the normalised route."""
    cache = {}
    route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    assert route is not None, "expected a resolved route, got None"
    assert route.get("airline_name") == "Transavia France", (
        "airline_name %r != 'Transavia France'" % (route.get("airline_name"),)
    )
    assert route.get("origin_iata") == "ORY" and route.get("origin_city") == "Paris", (
        "origin mismatch: %r" % (route,)
    )
    assert route.get("destination_iata") == "PMI" and route.get("destination_city") == "Palma de Mallorca", (
        "destination mismatch (sentence-case city expected 'Palma de Mallorca'): %r" % (route,)
    )


def test_real_recorded_miss_yields_none(miss_fixture):
    """replaying the real recorded adsbdb miss (EJU84YF, a genuine captured 404 - see fixtures/README.md) yields None."""
    cache = {}
    route = enrich.lookup_route(
        "EJU84YF", cache,
        transport=make_transport(miss_fixture["http_status"], miss_fixture["body"]),
    )
    assert route is None, "expected None for the real recorded adsbdb miss (EJU84YF), got %r" % (route,)


def test_500_yields_none():
    """a 500 response yields None without raising."""
    cache = {}
    route = enrich.lookup_route("AAA111", cache, transport=make_transport(500, {"error": "server error"}))
    assert route is None, "expected None for a 500 response, got %r" % (route,)


def test_connection_error_yields_none():
    """a connection error (transport raises) yields None without raising."""
    cache = {}
    route = enrich.lookup_route(
        "BBB222", cache,
        transport=make_transport(None, None, raise_exc=OSError("simulated connection failure")),
    )
    assert route is None, "expected None for a connection error, got %r" % (route,)


def test_non_json_body_yields_none():
    """a 200 response with a non-JSON body yields None without raising."""
    cache = {}
    route = enrich.lookup_route("CCC333", cache, transport=make_transport(200, None))
    assert route is None, "expected None for a non-JSON (unparseable) body, got %r" % (route,)


def test_missing_response_key_yields_none():
    """a 200 body missing the 'response' key yields None."""
    cache = {}
    route = enrich.lookup_route("DDD444", cache, transport=make_transport(200, {"unexpected": True}))
    assert route is None, "expected None when the 'response' key is missing, got %r" % (route,)


def test_missing_flightroute_key_yields_none():
    """a 200 body missing the 'flightroute' key yields None."""
    cache = {}
    route = enrich.lookup_route("EEE555", cache, transport=make_transport(200, {"response": {}}))
    assert route is None, "expected None when the 'flightroute' key is missing, got %r" % (route,)


def test_half_resolved_route_yields_none(hit_body):
    """a structurally incomplete 200 body (missing/non-string municipality) yields None - UI-SPEC has no partial state."""
    broken = copy.deepcopy(hit_body)
    broken["response"]["flightroute"]["destination"]["municipality"] = None
    cache = {}
    route = enrich.lookup_route("FFF666", cache, transport=make_transport(200, broken))
    assert route is None, (
        "a route missing destination.municipality must yield None (no partial route), got %r" % (route,)
    )


def test_hit_is_cached(hit_body):
    """two consecutive lookups for the same callsign invoke the transport exactly once (cached hit)."""
    cache = {}
    calls = []
    transport = make_transport(200, hit_body, calls=calls)
    first = enrich.lookup_route("TVF16VB", cache, transport=transport)
    second = enrich.lookup_route("TVF16VB", cache, transport=transport)
    assert len(calls) == 1, "expected exactly 1 transport call across two lookups, got %d" % len(calls)
    assert first == second, "cached lookup returned a different result than the fresh lookup"


def test_miss_is_cached(miss_fixture):
    """a cached miss (a callsign that returned 404) is never re-queried on a later lookup."""
    cache = {}
    calls = []
    transport = make_transport(miss_fixture["http_status"], miss_fixture["body"], calls=calls)
    first = enrich.lookup_route("EJU84YF", cache, transport=transport)
    second = enrich.lookup_route("EJU84YF", cache, transport=transport)
    assert len(calls) == 1, (
        "a cached miss must not be re-queried on a later lookup - expected 1 transport call, got %d" % len(calls)
    )
    assert first is None and second is None, "expected both lookups to yield None for a cached miss"


def test_cache_round_trips_through_json(hit_body, miss_fixture):
    """the cache round-trips through json.dumps/json.loads and still honours both a cached hit and a cached miss."""
    cache = {}
    enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    enrich.lookup_route("EJU84YF", cache, transport=make_transport(miss_fixture["http_status"], miss_fixture["body"]))
    try:
        reloaded = json.loads(json.dumps(cache))
    except (TypeError, ValueError) as exc:
        pytest.fail("cache is not JSON-serialisable: %r" % (exc,))

    def _explode(*_args, **_kwargs):
        raise AssertionError("transport must not be called - both callsigns are already cached")

    hit_again = enrich.lookup_route("TVF16VB", reloaded, transport=_explode)
    miss_again = enrich.lookup_route("EJU84YF", reloaded, transport=_explode)
    assert hit_again is not None and hit_again.get("airline_name") == "Transavia France", (
        "round-tripped cache did not preserve the cached hit"
    )
    assert miss_again is None, "round-tripped cache did not preserve the cached miss"


def test_normalisation_shares_one_cache_entry_and_request(hit_body):
    """callsigns are normalised (stripped, upper-cased) before both the cache key and the request URL are built."""
    cache = {}
    calls = []
    transport = make_transport(200, hit_body, calls=calls)
    first = enrich.lookup_route("TVF16VB ", cache, transport=transport)
    second = enrich.lookup_route(" tvf16vb", cache, transport=transport)
    assert len(calls) == 1, (
        "expected exactly 1 transport call for two differently-cased/whitespace-padded variants, got %d" % len(calls)
    )
    assert calls[0] == "TVF16VB", (
        "expected the transport to receive the normalised callsign 'TVF16VB', got %r" % (calls[0],)
    )
    assert first == second, "differently-cased/whitespace-padded callsigns did not resolve to the same cached result"


def test_sentence_case_lowercases_interior_particles():
    """to_sentence_case_city lower-cases interior connective particles but capitalises the first word and all other words."""
    cases = {
        "Palma De Mallorca": "Palma de Mallorca",
        "Paris": "Paris",
        "Los Angeles": "Los Angeles",  # "Los" is not a lowered particle
        "De Soto": "De Soto",  # particle is the FIRST word - stays capitalised
    }
    for raw, expected in cases.items():
        got = enrich.to_sentence_case_city(raw)
        assert got == expected, "to_sentence_case_city(%r) = %r, expected %r" % (raw, got, expected)


def test_primary_city_name_reduces_compound_municipality():
    """_primary_city_name() reduces a '/'-separated compound municipality name to its first segment, unchanged when there is no '/'."""
    # Phase 9 09-04 on-glass finding: OurAirports/adsbdb list every commune
    # an airport serves "/"-separated in its own municipality field
    # (confirmed live against api.adsbdb.com - Toulon-Hyeres Airport's real
    # municipality is "Toulon/Hyeres/Le Palyvestre", serving Orly) - no
    # panel text role has room for the full compound name.
    cases = {
        "Toulon/Hyeres/Le Palyvestre": "Toulon",
        "Toulouse/Blagnac": "Toulouse",
        "Paris": "Paris",  # no "/" - passes through unchanged
    }
    for raw, expected in cases.items():
        got = enrich._primary_city_name(raw)
        assert got == expected, "_primary_city_name(%r) = %r, expected %r" % (raw, got, expected)


def test_parse_route_applies_primary_city_name_to_both_cities(hit_body):
    """_parse_route() applies _primary_city_name() to both origin_city and destination_city, not just one (D-09-style, Phase 9 09-04)."""
    compound = copy.deepcopy(hit_body)
    compound["response"]["flightroute"]["origin"]["municipality"] = "Toulon/Hyeres/Le Palyvestre"
    compound["response"]["flightroute"]["destination"]["municipality"] = "Bordeaux/Merignac"
    route = enrich._parse_route(compound)
    assert route is not None, "_parse_route() returned None for a valid fixture with compound municipality names"
    assert route.get("origin_city") == "Toulon", "origin_city = %r, expected 'Toulon'" % (route.get("origin_city"),)
    assert route.get("destination_city") == "Bordeaux", (
        "destination_city = %r, expected 'Bordeaux'" % (route.get("destination_city"),)
    )


def test_unsafe_callsign_never_queried(hit_body):
    """a callsign containing non-alphanumeric characters is rejected before the outbound request is built (T-02-04-02)."""
    cache = {}
    calls = []
    transport = make_transport(200, hit_body, calls=calls)
    route = enrich.lookup_route("TVF/16;VB?x=1", cache, transport=transport)
    assert route is None, "expected None for a non-alphanumeric callsign shape"
    assert not calls, (
        "a hostile callsign shape must never reach the outbound transport - it was called with %r" % (calls,)
    )


def test_city_for_state_picks_correct_end(hit_body):
    """city_for_state() returns the destination city for departing and the origin city for arriving."""
    cache = {}
    route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    assert enrich.city_for_state(route, "departing") == "Palma de Mallorca", "departing should read the destination city"
    assert enrich.city_for_state(route, "arriving") == "Paris", "arriving should read the origin city"
    assert enrich.city_for_state(None, "departing") is None, "city_for_state(None, ...) must return None"


def test_normalise_callsign_edge_cases():
    """normalise_callsign strips and upper-cases, returning None for anything empty or non-string."""
    assert enrich.normalise_callsign(" tvf16vb ") == "TVF16VB", "expected stripped/upper-cased result"
    assert enrich.normalise_callsign("") is None, "expected None for an empty string"
    assert enrich.normalise_callsign(None) is None, "expected None for a non-string input"


# --- Quick task 260827-hyy: airline_from_callsign() / airline_only_route()
# / resolve_route() - the ICAO-prefix fallback layered above the adsbdb
# miss (D-01/D-02/D-03/D-04/D-05). ---------------------------------------


def test_airline_from_callsign_tvf():
    """airline_from_callsign('TVF16VB') returns 'Transavia France'."""
    # TVF is the plan's headline case: Transavia France's stable ICAO
    # prefix, resolved with zero network call.
    got = enrich.airline_from_callsign("TVF16VB")
    assert got == "Transavia France", "airline_from_callsign('TVF16VB') = %r, expected 'Transavia France'" % (got,)


def test_airline_from_callsign_normalises():
    """airline_from_callsign(' tvf16vb ') normalises through normalise_callsign() before the prefix lookup."""
    got = enrich.airline_from_callsign(" tvf16vb ")
    assert got == "Transavia France", "airline_from_callsign(' tvf16vb ') = %r, expected 'Transavia France'" % (got,)


def test_airline_from_callsign_never_raises_battery():
    """airline_from_callsign() returns None (never raises) for an unknown prefix, a bare 3-letter string, empty string, None, an int, and a path-separator payload."""
    # One check covering the whole battery, matching the original
    # harness's single PASS/FAIL line for this internal loop.
    for case in ["ZZZ1234", "TVF", "", None, 42, "TVF/16VB"]:
        got = enrich.airline_from_callsign(case)
        assert got is None, "airline_from_callsign(%r) = %r, expected None" % (case, got)


def test_airline_only_route_shape_and_none_handling(hit_body):
    """airline_only_route('Transavia France') carries _parse_route()'s exact key set, airline_name set and the other four keys None; airline_only_route(None) returns None."""
    cache = {}
    full_route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    assert full_route is not None, "setup failure: expected the real hit fixture to resolve a full route"
    expected_keys = set(full_route.keys())
    got = enrich.airline_only_route("Transavia France")
    assert got is not None, "airline_only_route('Transavia France') returned None, expected a dict"
    assert set(got.keys()) == expected_keys, (
        "airline_only_route() key set %r != _parse_route()'s real key set %r" % (set(got.keys()), expected_keys)
    )
    assert got.get("airline_name") == "Transavia France", (
        "airline_only_route() airline_name = %r, expected 'Transavia France'" % (got.get("airline_name"),)
    )
    for key in expected_keys - {"airline_name"}:
        assert got.get(key) is None, "airline_only_route() key %r = %r, expected None" % (key, got.get(key))
    assert enrich.airline_only_route(None) is None, "airline_only_route(None) should return None"


def test_resolve_route_airline_only_on_real_miss(miss_fixture):
    """resolve_route('EJU84YF', ...) on the real recorded adsbdb miss yields an 'easyJet' airline-only route with source 'airline_only', identically on a second call, with exactly one transport invocation."""
    cache = {}
    calls = []
    transport = make_transport(miss_fixture["http_status"], miss_fixture["body"], calls=calls)
    route1, source1 = enrich.resolve_route("EJU84YF", cache, transport=transport)
    route2, source2 = enrich.resolve_route("EJU84YF", cache, transport=transport)
    assert source1 == "airline_only" and source2 == "airline_only", (
        "expected source 'airline_only' on both calls, got %r then %r" % (source1, source2)
    )
    assert route1 is not None and route1.get("airline_name") == "easyJet", (
        "expected an airline-only route with airline_name 'easyJet', got %r" % (route1,)
    )
    assert route2 == route1, (
        "second resolve_route() call returned a different route than the first: %r vs %r" % (route2, route1)
    )
    assert len(calls) == 1, (
        "expected the transport to be invoked exactly once (the miss is cached), got %d calls" % len(calls)
    )


def test_resolve_route_fresh_then_cache_hit(hit_body):
    """resolve_route('TVF16VB', ...) classifies fresh_hit on the first call and cache_hit on the second."""
    cache = {}
    route1, source1 = enrich.resolve_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    assert source1 == "fresh_hit", "expected source 'fresh_hit' on the first call, got %r" % (source1,)
    route2, source2 = enrich.resolve_route("TVF16VB", cache, transport=make_transport(200, hit_body))
    assert source2 == "cache_hit", "expected source 'cache_hit' on the second call, got %r" % (source2,)
    assert route1 == route2, "fresh_hit and cache_hit calls returned different routes: %r vs %r" % (route1, route2)


def test_resolve_route_unknown_prefix_is_miss():
    """resolve_route() on a miss whose callsign prefix is absent from the table returns (None, 'miss')."""
    cache = {}
    route, source = enrich.resolve_route(
        "ZZZ1234", cache, transport=make_transport(404, {"response": "unknown callsign"}),
    )
    assert route is None and source == "miss", (
        "expected (None, 'miss') for an unknown-prefix miss, got (%r, %r)" % (route, source)
    )


def test_prefix_table_values_are_a_subset_of_illustration_targets():
    """every value in enrich._ICAO_AIRLINE_PREFIXES is a member of illustrations.target_airline_names() (D-07 drift guard)."""
    prefix_values = set(enrich._ICAO_AIRLINE_PREFIXES.values())
    target_names = set(illustrations.target_airline_names())
    missing = prefix_values - target_names
    assert not missing, "prefix table produces airline name(s) with no illustration target: %r" % (sorted(missing),)


def test_prefix_table_keys_are_three_uppercase_letters():
    """every key of enrich._ICAO_AIRLINE_PREFIXES is exactly 3 uppercase A-Z characters."""
    bad = [
        k for k in enrich._ICAO_AIRLINE_PREFIXES
        if not (isinstance(k, str) and len(k) == 3 and k.isalpha() and k == k.upper())
    ]
    assert not bad, "prefix table has key(s) that are not exactly 3 uppercase A-Z letters: %r" % (bad,)


def test_airline_from_callsign_km_malta():
    """airline_from_callsign('KMM466') returns 'KM Malta Airlines' (260827-jz6, real curled callsign)."""
    got = enrich.airline_from_callsign("KMM466")
    assert got == "KM Malta Airlines", "airline_from_callsign('KMM466') = %r, expected 'KM Malta Airlines'" % (got,)


def test_airline_from_callsign_tuifly_belgium():
    """airline_from_callsign('JAF7521') returns 'TUIfly Belgium' (260827-jz6, real curled callsign, QT-jz6-D-02 override)."""
    got = enrich.airline_from_callsign("JAF7521")
    assert got == "TUIfly Belgium", "airline_from_callsign('JAF7521') = %r, expected 'TUIfly Belgium'" % (got,)


# --- Quick task 260827-kih: enrich.correct_airline_name() /
# apply_airline_name_correction() - the single prefix-scoped correction
# seam applied inside lookup_route(). ---------------------------------


def test_correct_airline_name_aia_to_amelia():
    """correct_airline_name('AIA6412', 'Avies') returns 'Amelia' (260827-kih)."""
    # The headline case: adsbdb's real recorded AIA6412 response attributes
    # the AIA prefix to "Avies" (a different, defunct Estonian carrier) -
    # correct_airline_name() corrects it to "Amelia".
    got = enrich.correct_airline_name("AIA6412", "Avies")
    assert got == "Amelia", "correct_airline_name('AIA6412', 'Avies') = %r, expected 'Amelia'" % (got,)


def test_correct_airline_name_is_prefix_scoped():
    """correct_airline_name('ZZZ1234', 'Avies') returns 'Avies' unchanged - a different prefix carrying the same string is never rewritten (QT-kih-D-01)."""
    got = enrich.correct_airline_name("ZZZ1234", "Avies")
    assert got == "Avies", (
        "correct_airline_name('ZZZ1234', 'Avies') = %r, expected 'Avies' unchanged (prefix-scoped, "
        "not a global replace)" % (got,)
    )


def test_resolve_route_corrects_aia_fresh_then_cached(aia_hit_body):
    """resolve_route('AIA6412', ...) corrects the real recorded AIA/Avies misattribution to 'Amelia' on both a fresh_hit and a cache_hit, while the cache entry itself keeps the raw upstream string (QT-kih-D-02)."""
    cache = {}
    calls = []
    transport = make_transport(200, aia_hit_body, calls=calls)
    route1, source1 = enrich.resolve_route("AIA6412", cache, transport=transport)
    assert route1 is not None and route1.get("airline_name") == "Amelia" and source1 == "fresh_hit", (
        "expected a fresh_hit route with airline_name 'Amelia', got (%r, %r)" % (route1, source1)
    )
    route2, source2 = enrich.resolve_route("AIA6412", cache, transport=transport)
    assert route2 is not None and route2.get("airline_name") == "Amelia" and source2 == "cache_hit", (
        "expected a cache_hit route with airline_name 'Amelia', got (%r, %r)" % (route2, source2)
    )
    assert len(calls) == 1, "expected exactly 1 transport call across both resolve_route() calls, got %d" % len(calls)
    cached_entry = cache.get("AIA6412")
    assert isinstance(cached_entry, dict) and cached_entry.get("airline_name") == "Avies", (
        "the cache entry itself must still hold the raw upstream string 'Avies', got %r" % (cached_entry,)
    )


def test_airline_from_callsign_aia_amelia():
    """airline_from_callsign('AIA6412') returns 'Amelia' (260827-kih, zero network call)."""
    got = enrich.airline_from_callsign("AIA6412")
    assert got == "Amelia", "airline_from_callsign('AIA6412') = %r, expected 'Amelia'" % (got,)


def test_correction_table_agrees_with_prefix_table_and_targets():
    """every _AIRLINE_NAME_CORRECTIONS row agrees with _ICAO_AIRLINE_PREFIXES and its corrected value is a target_airline_names() member (QT-kih-D-03 cross-table invariant)."""
    target_names = set(illustrations.target_airline_names())
    for (prefix, _stale), corrected in enrich._AIRLINE_NAME_CORRECTIONS.items():
        prefix_value = enrich._ICAO_AIRLINE_PREFIXES.get(prefix)
        assert prefix_value == corrected, (
            "_AIRLINE_NAME_CORRECTIONS[(%r, ...)] = %r but _ICAO_AIRLINE_PREFIXES[%r] = %r - the two "
            "tables must agree" % (prefix, corrected, prefix, prefix_value)
        )
        assert corrected in target_names, (
            "corrected value %r is not a member of illustrations.target_airline_names()" % (corrected,)
        )


def test_correction_seam_never_raises_battery():
    """correct_airline_name()/apply_airline_name_correction() never raise for a hostile callsign x airline_name/route battery (None, int, empty string, bare prefix, path-separator payload, non-dict route, a route whose .get() raises), and never return a value derived from the arguments other than the unchanged airline_name (T-kih-01)."""
    # Hostile/malformed callsigns: None, an int, an empty string, a bare
    # 3-letter string with no flight suffix, and a path-separator payload -
    # none of these can ever reach _AIRLINE_NAME_CORRECTIONS, so
    # correct_airline_name() must return airline_name unchanged for every
    # one of them, and never raise.
    hostile_callsigns = (None, 42, "", "AIA", "AIA/6412")
    for callsign in hostile_callsigns:
        for airline_name in (None, 42, "", "Avies"):
            got = enrich.correct_airline_name(callsign, airline_name)
            assert got is airline_name, (
                "correct_airline_name(%r, %r) = %r - a hostile/malformed callsign must never change the "
                "airline_name it was handed" % (callsign, airline_name, got)
            )

    class _ExplodingRoute(dict):
        def get(self, *_args, **_kwargs):
            raise RuntimeError("simulated .get() failure")

    malformed_routes = (None, {}, "not-a-dict", 42, ["a", "list"], _ExplodingRoute())
    for callsign in hostile_callsigns:
        for route in malformed_routes:
            got = enrich.apply_airline_name_correction(callsign, route)
            if not isinstance(route, dict) or isinstance(route, _ExplodingRoute):
                assert got is route, (
                    "apply_airline_name_correction(%r, %r) should return the non-dict route unchanged, "
                    "got %r" % (callsign, route, got)
                )


# --- Quick task 260827-kih Task 2: the three stale-brand corrections
# (FPO/CRL/CCM) applied through the same seam. ------------------------


def _stubbed_hit_body(airline_name):
    return {
        "response": {
            "flightroute": {
                "airline": {"name": airline_name},
                "origin": {"iata_code": "ORY", "municipality": "Paris"},
                "destination": {"iata_code": "XXX", "municipality": "Somewhere"},
            }
        }
    }


def test_correct_airline_name_three_stale_brand_pairs():
    """correct_airline_name() maps FPO/Europe Airpost -> ASL Airlines France, CRL/Corsairfly -> Corsair, CCM/CCM Airlines -> Air Corsica (260827-kih)."""
    cases = [
        ("FPO701", "Europe Airpost", "ASL Airlines France"),
        ("CRL8025", "Corsairfly", "Corsair"),
        ("CCM21AW", "CCM Airlines", "Air Corsica"),
    ]
    for callsign, stale, expected in cases:
        got = enrich.correct_airline_name(callsign, stale)
        assert got == expected, "correct_airline_name(%r, %r) = %r, expected %r" % (callsign, stale, got, expected)


def test_resolve_route_and_selection_for_three_stale_brand_carriers():
    """resolve_route() corrects all three stale-brand carriers under their own prefix and leaves the same string untouched under an unrelated prefix; the corrected Air Corsica route selects the renamed air-corsica.png/air-corsica-atr72.png files (260827-kih)."""
    cases = [
        ("FPO701", "Europe Airpost", "ASL Airlines France"),
        ("CRL8025", "Corsairfly", "Corsair"),
        ("CCM21AW", "CCM Airlines", "Air Corsica"),
    ]
    for callsign, stale, expected in cases:
        cache = {}
        body = _stubbed_hit_body(stale)
        route, source = enrich.resolve_route(callsign, cache, transport=make_transport(200, body))
        assert route is not None and route.get("airline_name") == expected and source == "fresh_hit", (
            "resolve_route(%r, ...) = (%r, %r), expected airline_name %r, source 'fresh_hit'" % (
                callsign, route, source, expected,
            )
        )

    # Negative case: the same upstream string, served under an UNRELATED
    # prefix, must come back untouched - the correction is keyed on the
    # (prefix, string) pair, never on the string alone.
    cache = {}
    unrelated_body = _stubbed_hit_body("CCM Airlines")
    route, source = enrich.resolve_route("ZZZ9999", cache, transport=make_transport(200, unrelated_body))
    assert route is not None and route.get("airline_name") == "CCM Airlines", (
        "resolve_route('ZZZ9999', ...) with airline_name 'CCM Airlines' under an unrelated prefix must come "
        "back untouched, got %r" % (route,)
    )

    ccm_route = enrich.airline_only_route("Air Corsica")
    primary = illustrations.select_illustration(ccm_route, "A320")
    assert primary is not None and os.path.basename(primary) == "air-corsica.png", (
        "select_illustration(Air Corsica route, 'A320') = %r, expected air-corsica.png" % (primary,)
    )
    secondary = illustrations.select_illustration(ccm_route, "AT72")
    assert secondary is not None and os.path.basename(secondary) == "air-corsica-atr72.png", (
        "select_illustration(Air Corsica route, 'AT72') = %r, expected air-corsica-atr72.png" % (secondary,)
    )


# --- Quick task 260827-lgt: HOP! Air France, Wizz Air Malta, KlasJet -
# three new prefix-table rows, cross-checked against the official Paris
# Aeroport Orly airline list. ------------------------------------


def test_airline_from_callsign_hop_air_france():
    """airline_from_callsign('HOP4001') returns 'Air France Hop' (260827-lgt, real curled callsign)."""
    got = enrich.airline_from_callsign("HOP4001")
    assert got == "Air France Hop", "airline_from_callsign('HOP4001') = %r, expected 'Air France Hop'" % (got,)


def test_airline_from_callsign_wizz_air_malta():
    """airline_from_callsign('WMT3001') returns 'Wizz Air' (260827-lgt, real curled callsign WMT3001; adsbdb itself resolves 'Wizz Air Malta', QT-lgt-D-01 deliberate brand consolidation)."""
    got = enrich.airline_from_callsign("WMT3001")
    assert got == "Wizz Air", "airline_from_callsign('WMT3001') = %r, expected 'Wizz Air'" % (got,)


def test_airline_from_callsign_klasjet():
    """airline_from_callsign('KLJ123') returns 'KlasJet' (260827-lgt, KLJ123 is a SYNTHETIC shape-valid callsign - no real KLJ callsign was ever live-confirmed, QT-lgt-D-06)."""
    got = enrich.airline_from_callsign("KLJ123")
    assert got == "KlasJet", "airline_from_callsign('KLJ123') = %r, expected 'KlasJet'" % (got,)


def test_no_correction_row_for_new_lgt_prefixes():
    """no _AIRLINE_NAME_CORRECTIONS row exists whose prefix element is HOP, WMT or KLJ (QT-lgt-D-07 guard)."""
    bad = [k for k in enrich._AIRLINE_NAME_CORRECTIONS if k[0] in ("HOP", "WMT", "KLJ")]
    assert not bad, "unexpected _AIRLINE_NAME_CORRECTIONS row(s) for HOP/WMT/KLJ: %r" % (bad,)


# --- Quick task 260827-oz9: note_unresolved_prefix()/
# trim_unresolved_prefixes() - a pure, bounded, hostile-input-proof
# unrecognized-ICAO-prefix recorder layered on top of resolve_route()'s
# existing "miss" classification. -------------------------------------


def test_note_unresolved_prefix_first_sighting():
    """note_unresolved_prefix() on a first sighting records a well-formed entry (count 1, both timestamps set)."""
    reg = {}
    prefix = enrich.note_unresolved_prefix("ZZQ1234", reg, now="T1")
    assert prefix == "ZZQ", "note_unresolved_prefix('ZZQ1234', {}, now='T1') = %r, expected 'ZZQ'" % (prefix,)
    assert list(reg) == ["ZZQ"], "expected exactly one registry key 'ZZQ', got %r" % (list(reg),)
    entry = reg["ZZQ"]
    assert entry.get("count") == 1, "first-sighting count = %r, expected 1" % (entry.get("count"),)
    assert entry.get("first_seen") == "T1" and entry.get("last_seen") == "T1", (
        "first-sighting timestamps = %r, expected both 'T1'" % (entry,)
    )
    assert entry.get("example_callsign") == "ZZQ1234", (
        "first-sighting example_callsign = %r, expected 'ZZQ1234'" % (entry.get("example_callsign"),)
    )


def test_note_unresolved_prefix_second_sighting_updates_in_place():
    """note_unresolved_prefix() on a second sighting increments count, updates last_seen/example_callsign, and never moves first_seen."""
    reg = {}
    enrich.note_unresolved_prefix("ZZQ1234", reg, now="T1")
    prefix = enrich.note_unresolved_prefix("ZZQ5678", reg, now="T2")
    assert prefix == "ZZQ", "second sighting returned %r, expected 'ZZQ'" % (prefix,)
    assert list(reg) == ["ZZQ"], "expected still exactly one registry key 'ZZQ', got %r" % (list(reg),)
    entry = reg["ZZQ"]
    assert entry.get("count") == 2, "second-sighting count = %r, expected 2" % (entry.get("count"),)
    assert entry.get("first_seen") == "T1", (
        "first_seen moved on the second sighting: %r, expected still 'T1'" % (entry.get("first_seen"),)
    )
    assert entry.get("last_seen") == "T2", "last_seen = %r, expected 'T2'" % (entry.get("last_seen"),)
    assert entry.get("example_callsign") == "ZZQ5678", (
        "example_callsign = %r, expected the second callsign 'ZZQ5678' (QT-oz9-D-05)" % (entry.get("example_callsign"),)
    )


def test_note_unresolved_prefix_never_records_a_covered_prefix():
    """note_unresolved_prefix() returns None and records nothing for every single prefix already present in _ICAO_AIRLINE_PREFIXES (full-table invariant, not sampled)."""
    reg = {}
    for prefix in enrich._ICAO_AIRLINE_PREFIXES:
        got = enrich.note_unresolved_prefix(prefix + "1234", reg, now="T")
        assert got is None, (
            "note_unresolved_prefix() recorded a prefix already covered by _ICAO_AIRLINE_PREFIXES: %r -> %r" % (
                prefix, got,
            )
        )
    assert not reg, "registry should still be empty after every covered prefix, got %r" % (reg,)


def test_note_unresolved_prefix_hostile_input_battery():
    """note_unresolved_prefix() never records and never raises for None/int/empty/whitespace/bare-prefix/lowercase/path-separator/dot-dot/digit-in-prefix/non-dict-registry input, rebuilds a malformed pre-existing entry, and bounds the stored example for a 900-character legitimate-shape callsign."""
    reg = {}
    hostile = (None, 123, "", "   ", "ZZQ", "zzq", "ZZQ/../x", "ZZ11234", True, [], {})
    for bad in hostile:
        got = enrich.note_unresolved_prefix(bad, reg, now="T")
        assert got is None, "note_unresolved_prefix(%r, ...) = %r, expected None" % (bad, got)
    assert not reg, "hostile input reached the registry: %r" % (reg,)

    got = enrich.note_unresolved_prefix("ZZQ1234", "not-a-dict", now="T")
    assert got is None, "note_unresolved_prefix(..., 'not-a-dict', ...) = %r, expected None" % (got,)

    rebuilt = enrich.note_unresolved_prefix("ZZQ1234", {"ZZQ": "corrupt"}, now="T")
    assert rebuilt == "ZZQ", "a malformed pre-existing entry must be rebuilt fresh, not raise; got %r" % (rebuilt,)

    long_callsign = "ZZQ" + "A" * 900
    got = enrich.note_unresolved_prefix(long_callsign, reg, now="T")
    assert got == "ZZQ", "a legitimate-shape 900-character callsign should be recorded, got %r" % (got,)
    (key,) = reg
    assert re.match(r"^[A-Z]{3}$", key), "stored key is not a bare 3-letter prefix: %r" % (key,)
    example = reg[key]["example_callsign"]
    assert len(example) <= enrich.UNRESOLVED_EXAMPLE_MAX_LEN, (
        "example_callsign is unbounded (%d chars) for a spoofed long callsign" % len(example)
    )


def test_trim_unresolved_prefixes_favours_recurrence():
    """trim_unresolved_prefixes() evicts lowest-count-then-oldest-last-seen, so a recurring prefix survives a flood of one-off arrivals and the newer one-off wins the tie-break (QT-oz9-D-04)."""
    reg = {}
    for _ in range(5):
        enrich.note_unresolved_prefix("AAA1", reg, now="2020-01-01T00:00:00+00:00")
    enrich.note_unresolved_prefix("BBB1", reg, now="2026-01-01T00:00:00+00:00")
    enrich.note_unresolved_prefix("CCC1", reg, now="2025-01-01T00:00:00+00:00")
    enrich.trim_unresolved_prefixes(reg, max_entries=2)
    assert len(reg) == 2, "expected registry length 2 after trim, got %d: %r" % (len(reg), reg)
    assert "AAA" in reg, (
        "the recurring entry (AAA, count 5) was evicted - insertion-order eviction destroys exactly what "
        "this feature is for (QT-oz9-D-04)"
    )
    assert "BBB" in reg and "CCC" not in reg, (
        "tie-break among count-1 entries must keep the newer last_seen (BBB), got %r" % (sorted(reg),)
    )


def test_note_unresolved_prefix_agrees_with_resolve_route():
    """note_unresolved_prefix() records exactly the callsigns resolve_route() classifies 'miss' and none it classifies 'airline_only', on the same real production condition (an adsbdb 404)."""
    transport_404 = make_transport(404, {"response": "unknown callsign"})
    cache = {}
    reg = {}
    route1, source1 = enrich.resolve_route("ZZQ1234", cache, transport=transport_404)
    assert source1 == "miss" and route1 is None, (
        "expected ('miss', None) for an uncovered prefix, got (%r, %r)" % (route1, source1)
    )
    assert enrich.note_unresolved_prefix("ZZQ1234", reg, now="T") == "ZZQ", (
        "the recorder must record the callsign resolve_route() classified 'miss'"
    )

    route2, source2 = enrich.resolve_route("AFR1234", cache, transport=transport_404)
    assert source2 == "airline_only", (
        "expected 'airline_only' for a covered prefix under an adsbdb miss, got %r" % (source2,)
    )
    assert enrich.note_unresolved_prefix("AFR1234", reg, now="T") is None, (
        "the recorder must not record a callsign resolve_route() classified 'airline_only'"
    )
    assert list(reg) == ["ZZQ"], "expected only 'ZZQ' in the registry, got %r" % (list(reg),)


# --- Phase 8 plan 08-02 (D-09): callsign_iata threaded through
# _parse_route()/_route_from_entry()/airline_only_route(). This field is
# adsbdb's IATA-formatted flight identifier (e.g. "AF1234") - reliable for
# legacy/full-service carriers, where the ICAO and IATA callsigns denote
# the same real published flight number, and not reliably meaningful for
# rotating-callsign carriers (see
# .planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md) - these
# tests pin its presence/optionality/persistence, not its universal
# correctness. ---------------------------------------------------------


def test_callsign_iata_parsed_from_real_hits(hit_body, aia_hit_body):
    """_parse_route() reads callsign_iata from two real fixtures (TVF16VB -> 'TO16VB', AIA6412 -> 'U36412') (D-09)."""
    # Two distinct real fixtures, not one, so a hardcoded value could not
    # pass by accident.
    route_tvf = enrich._parse_route(hit_body)
    assert route_tvf is not None and route_tvf.get("callsign_iata") == "TO16VB", (
        "TVF16VB fixture: callsign_iata = %r, expected 'TO16VB'" % (
            route_tvf.get("callsign_iata") if route_tvf else None,
        )
    )
    route_aia = enrich._parse_route(aia_hit_body)
    assert route_aia is not None and route_aia.get("callsign_iata") == "U36412", (
        "AIA6412 fixture: callsign_iata = %r, expected 'U36412'" % (
            route_aia.get("callsign_iata") if route_aia else None,
        )
    )


def test_callsign_iata_optional_never_route_fatal(hit_body):
    """callsign_iata is optional and never route-fatal: absent/empty/whitespace/non-string values all still resolve a full route with callsign_iata degraded to None (D-09, T-08-02-01/T-08-02-02)."""
    absent = copy.deepcopy(hit_body)
    del absent["response"]["flightroute"]["callsign_iata"]
    route = enrich._parse_route(absent)
    assert route is not None, "a body with callsign_iata absent must still resolve a full route, got None"
    assert route.get("callsign_iata") is None, (
        "callsign_iata absent from the body should parse to None, got %r" % (route.get("callsign_iata"),)
    )

    for hostile in ("", "   ", 42, [], {}):
        body = copy.deepcopy(hit_body)
        body["response"]["flightroute"]["callsign_iata"] = hostile
        route = enrich._parse_route(body)
        assert route is not None, "a hostile callsign_iata value %r must still resolve a full route, got None" % (hostile,)
        assert route.get("callsign_iata") is None, (
            "hostile callsign_iata value %r should degrade to None, got %r" % (hostile, route.get("callsign_iata"))
        )


def test_callsign_iata_cache_round_trip_parity(hit_body, aia_hit_body):
    """a callsign resolved twice, the second time with no transport available, agrees on callsign_iata both on the plain hit path (TVF16VB) and the airline-name-correction path (AIA6412, Avies->Amelia) - proving both _route_from_entry() and apply_airline_name_correction()'s shallow copy preserve the field (D-09)."""
    cache = {}
    transport = make_transport(200, hit_body)
    first = enrich.lookup_route("TVF16VB", cache, transport=transport)
    second = enrich.lookup_route("TVF16VB", cache, transport=None)
    assert (
        first is not None and second is not None
        and first.get("callsign_iata") == second.get("callsign_iata") == "TO16VB"
    ), (
        "plain hit: fresh vs cache-only callsign_iata mismatch: %r vs %r" % (
            first.get("callsign_iata") if first else None, second.get("callsign_iata") if second else None,
        )
    )

    cache2 = {}
    aia_transport = make_transport(200, aia_hit_body)
    corrected_fresh = enrich.resolve_route("AIA6412", cache2, transport=aia_transport)[0]
    corrected_cached = enrich.resolve_route("AIA6412", cache2, transport=None)[0]
    assert corrected_fresh is not None and corrected_fresh.get("airline_name") == "Amelia", (
        "expected the AIA6412 correction seam to still apply on the fresh call, got %r" % (corrected_fresh,)
    )
    assert corrected_cached is not None and corrected_cached.get("airline_name") == "Amelia", (
        "expected the AIA6412 correction seam to still apply on the cache-only call, got %r" % (corrected_cached,)
    )
    assert (
        corrected_fresh.get("callsign_iata") == corrected_cached.get("callsign_iata") == "U36412"
    ), (
        "correction-seam path: fresh vs cache-only callsign_iata mismatch: %r vs %r" % (
            corrected_fresh.get("callsign_iata"), corrected_cached.get("callsign_iata"),
        )
    )


def test_shape_parity_across_all_three_builders(hit_body):
    """_parse_route(), _route_from_entry() and airline_only_route() all agree on one key set, derived from a real _parse_route() result rather than hardcoded (D-09)."""
    parsed = enrich._parse_route(hit_body)
    assert parsed is not None, "setup failure: expected the real TVF16VB fixture to resolve a full route"
    expected_keys = set(parsed.keys())

    cache_entry = dict(parsed)
    cache_entry["found"] = True
    from_entry = enrich._route_from_entry(cache_entry)
    assert set(from_entry.keys()) == expected_keys, (
        "_route_from_entry() key set %r != _parse_route()'s key set %r" % (set(from_entry.keys()), expected_keys)
    )

    airline_only = enrich.airline_only_route("Any Airline")
    assert set(airline_only.keys()) == expected_keys, (
        "airline_only_route() key set %r != _parse_route()'s key set %r" % (set(airline_only.keys()), expected_keys)
    )


def test_raw_icao_callsign_never_smuggled_in(hit_body):
    """_parse_route()'s returned dict has no 'callsign'/'callsign_icao' key and no value equal to the raw ICAO callsign string - the raw callsign is structurally absent, not just unused by the renderer (D-08)."""
    route = enrich._parse_route(hit_body)
    assert route is not None, "setup failure: expected the real TVF16VB fixture to resolve a full route"
    assert "callsign" not in route and "callsign_icao" not in route, (
        "_parse_route()'s returned dict must never carry a 'callsign' or 'callsign_icao' key (D-08): %r" % (
            sorted(route),
        )
    )
    raw_icao_callsign = hit_body["response"]["flightroute"]["callsign_icao"]
    for key, value in route.items():
        assert value != raw_icao_callsign, (
            "route key %r == the raw ICAO callsign %r - D-08 forbids it reaching the route dict" % (
                key, raw_icao_callsign,
            )
        )


# --- Phase 13 plan 13-03 (D-01/D-06): airline_source_from_callsign()/
# static_airline_name_for_prefix() - the provenance-aware seam
# airline_from_callsign() now wraps, and the manual-resolution registry's
# entry point into enrich.py. --------------------------------------------


def test_airline_source_from_callsign_static_path_parity():
    """airline_source_from_callsign() returns ('<name>', 'static') for a known static prefix, (None, None) for an unknown one, and (None, None) for the full 260827-hyy hostile-input battery, with no registry configured."""
    got = enrich.airline_source_from_callsign("TVF16VB")
    assert got == ("Transavia France", "static"), (
        "airline_source_from_callsign('TVF16VB') = %r, expected ('Transavia France', 'static')" % (got,)
    )
    got = enrich.airline_source_from_callsign("ZZZ1234")
    assert got == (None, None), "airline_source_from_callsign('ZZZ1234') = %r, expected (None, None)" % (got,)
    for case in ["ZZZ1234", "TVF", "", None, 42, "TVF/16VB"]:
        got = enrich.airline_source_from_callsign(case)
        assert got == (None, None), "airline_source_from_callsign(%r) = %r, expected (None, None)" % (case, got)


def test_airline_source_from_callsign_manual_path(tmp_path):
    """after manual_resolutions.set_manual_registry_state_dir(tmp) with a ZZZ->'Zephyr Air' entry, airline_source_from_callsign('ZZZ1234') returns ('Zephyr Air', 'manual') and airline_from_callsign() returns 'Zephyr Air'; clearing the state dir restores (None, None)."""
    result = manual_resolutions.add_entry(tmp_path, "ZZZ", "Zephyr Air")
    assert result == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)
    got = enrich.airline_source_from_callsign("ZZZ1234")
    assert got == ("Zephyr Air", "manual"), (
        "airline_source_from_callsign('ZZZ1234') = %r, expected ('Zephyr Air', 'manual')" % (got,)
    )
    assert enrich.airline_from_callsign("ZZZ1234") == "Zephyr Air", (
        "airline_from_callsign('ZZZ1234') = %r, expected 'Zephyr Air'" % (enrich.airline_from_callsign("ZZZ1234"),)
    )
    manual_resolutions.set_manual_registry_state_dir(None)
    got = enrich.airline_source_from_callsign("ZZZ1234")
    assert got == (None, None), (
        "after clearing the state dir, airline_source_from_callsign('ZZZ1234') = %r, expected (None, None)" % (got,)
    )


def test_d06_collision_and_static_airline_name_for_prefix(tmp_path):
    """a manual entry for a prefix already in the static table is never consulted (D-06): airline_source_from_callsign() still reports the static name and source 'static'; static_airline_name_for_prefix() returns the static name for that prefix, None for a manual-only prefix, and handles non-string/wrong-length input without raising."""
    result = manual_resolutions.add_entry(tmp_path, "TVF", "Some Operator Typo")
    assert result == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)
    got = enrich.airline_source_from_callsign("TVF16VB")
    assert got == ("Transavia France", "static"), (
        "D-06 violated: airline_source_from_callsign('TVF16VB') with a colliding manual entry = %r, "
        "expected ('Transavia France', 'static')" % (got,)
    )
    assert enrich.static_airline_name_for_prefix("TVF") == "Transavia France", (
        "static_airline_name_for_prefix('TVF') = %r, expected 'Transavia France'" % (
            enrich.static_airline_name_for_prefix("TVF"),
        )
    )

    result2 = manual_resolutions.add_entry(tmp_path, "ZZZ", "Zephyr Air")
    assert result2 == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result2,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)
    assert enrich.static_airline_name_for_prefix("ZZZ") is None, (
        "static_airline_name_for_prefix('ZZZ') should ignore the manual-only entry, got %r" % (
            enrich.static_airline_name_for_prefix("ZZZ"),
        )
    )

    for hostile in (None, 42, "af", "AFRX", ""):
        got = enrich.static_airline_name_for_prefix(hostile)
        assert got is None, "static_airline_name_for_prefix(%r) = %r, expected None" % (hostile, got)


# --- Phase 13 plan 13-03 Task 2 (D-02): resolve_route()'s fifth "manual"
# source. --------------------------------------------------


def test_resolve_route_manual_source(tmp_path):
    """resolve_route() with a manual entry for a prefix absent from the static table and an adsbdb miss returns source 'manual' and an airline-only route whose airline_name is the operator's name and whose other five keys are None."""
    result = manual_resolutions.add_entry(tmp_path, "ZZZ", "Zephyr Air")
    assert result == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)
    cache = {}
    transport = make_transport(404, {"response": "unknown callsign"})
    route, source = enrich.resolve_route("ZZZ1234", cache, transport=transport)
    assert source == "manual", "expected source 'manual', got %r" % (source,)
    assert route is not None and route.get("airline_name") == "Zephyr Air", (
        "expected an airline-only route with airline_name 'Zephyr Air', got %r" % (route,)
    )
    for key in route:
        if key != "airline_name":
            assert route[key] is None, "expected route key %r to be None, got %r" % (key, route[key])


def test_resolve_route_static_and_adsbdb_precedence_over_manual(hit_body, tmp_path):
    """a manual entry for a static-table prefix still yields 'airline_only' under an adsbdb miss (D-06), and adsbdb still wins by construction ('fresh_hit') even when a manual entry exists for that prefix."""
    result = manual_resolutions.add_entry(tmp_path, "TVF", "Some Operator Typo")
    assert result == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)

    cache = {}
    miss_transport = make_transport(404, {"response": "unknown callsign"})
    route, source = enrich.resolve_route("TVF16VB", cache, transport=miss_transport)
    assert source == "airline_only" and route is not None and route.get("airline_name") == "Transavia France", (
        "D-06 violated: expected ('Transavia France', 'airline_only') for a static-table prefix with a "
        "colliding manual entry under an adsbdb miss, got (%r, %r)" % (route, source)
    )

    cache2 = {}
    route2, source2 = enrich.resolve_route("TVF16VB", cache2, transport=make_transport(200, hit_body))
    assert source2 == "fresh_hit", "expected source 'fresh_hit' even with a manual entry present, got %r" % (source2,)


# --- Phase 13 plan 13-03 Task 3 (D-14): clear_resolved_unresolved_prefix()
# - note_unresolved_prefix()'s structural inverse. ---------------------


def test_clear_resolved_unresolved_prefix_happy_path_and_idempotence(tmp_path):
    """clear_resolved_unresolved_prefix() removes a manually-resolved prefix's entry and returns the prefix, a second call returns None, and a still-unresolved prefix's entry survives byte-identical (D-14)."""
    result = manual_resolutions.add_entry(tmp_path, "ZZZ", "Zephyr Air")
    assert result == manual_resolutions.ADD_OK, "setup failure: add_entry() = %r, expected ADD_OK" % (result,)
    manual_resolutions.set_manual_registry_state_dir(tmp_path)

    still_unresolved_entry = {
        "count": 3,
        "first_seen": "T1",
        "last_seen": "T3",
        "example_callsign": "YYY9999",
    }
    registry = {
        "ZZZ": {
            "count": 2,
            "first_seen": "T1",
            "last_seen": "T2",
            "example_callsign": "ZZZ1234",
        },
        "YYY": dict(still_unresolved_entry),
    }

    got = enrich.clear_resolved_unresolved_prefix("ZZZ1234", registry)
    assert got == "ZZZ", "expected 'ZZZ' removed and returned, got %r" % (got,)
    assert "ZZZ" not in registry, "expected the 'ZZZ' entry to be removed from the registry, still present: %r" % (registry,)
    assert registry.get("YYY") == still_unresolved_entry, (
        "the still-unresolved 'YYY' entry must survive byte-identical, got %r" % (registry.get("YYY"),)
    )

    got2 = enrich.clear_resolved_unresolved_prefix("ZZZ1234", registry)
    assert got2 is None, "second call should return None (already cleared), got %r" % (got2,)
    assert registry.get("YYY") == still_unresolved_entry, (
        "the still-unresolved 'YYY' entry must survive the second call too, got %r" % (registry.get("YYY"),)
    )


def test_clear_resolved_unresolved_prefix_hostile_input_sweep():
    """clear_resolved_unresolved_prefix() returns None and mutates nothing for a non-dict registry, None, an int, an empty string, a bare 3-letter callsign, and a path-separator payload - one check covering the whole hostile-input sweep."""
    seeded = {
        "AFR": {
            "count": 1,
            "first_seen": "T1",
            "last_seen": "T1",
            "example_callsign": "AFR1234",
        },
    }
    original = copy.deepcopy(seeded)
    hostile = (None, 42, "", "ZZ", "ZZZ", "../x")
    for bad in hostile:
        got = enrich.clear_resolved_unresolved_prefix(bad, seeded)
        assert got is None, "clear_resolved_unresolved_prefix(%r, ...) = %r, expected None" % (bad, got)
        assert seeded == original, "hostile input %r mutated the registry: %r" % (bad, seeded)

    got = enrich.clear_resolved_unresolved_prefix("AFR1234", "not-a-dict")
    assert got is None, "clear_resolved_unresolved_prefix('AFR1234', 'not-a-dict') = %r, expected None" % (got,)


def test_v9c_eleven_new_prefixes_and_djt_correction_and_exclusions():
    """the eleven 260921-v9c prefixes each resolve through airline_from_callsign() to their exact expected name (including TFV60HA and KAF001 as actually observed), the DJT correction seam rewrites 'Denver Jet' to 'La Compagnie' via correct_airline_name(), and DEF/QEM both resolve to None (QT-v9c-D-06 guard)."""
    want = {
        "CAJ": "Air Caraïbes",
        "DJT": "La Compagnie",
        "QAF": "Qatar Amiri Flight",
        "KAF": "South Korea Government",
        "RJA": "Royal Jordanian",
        "CTM": "French Air Force",
        "SRA": "Saudi Royal Aviation",
        "SVA": "Saudia",
        "TFV": "Transavia France",
        "FGN": "Gendarmerie Nationale",
        "IPF": "Iraqi Government",
    }
    for prefix, expected in want.items():
        got = enrich.airline_from_callsign("%s101" % prefix)
        assert got == expected, "airline_from_callsign('%s101') = %r, expected %r" % (prefix, got, expected)

    got_tfv = enrich.airline_from_callsign("TFV60HA")
    assert got_tfv == "Transavia France", "airline_from_callsign('TFV60HA') = %r, expected 'Transavia France'" % (got_tfv,)

    got_kaf = enrich.airline_from_callsign("KAF001")
    assert got_kaf == "South Korea Government", (
        "airline_from_callsign('KAF001') = %r, expected 'South Korea Government'" % (got_kaf,)
    )

    got_correction = enrich.correct_airline_name("DJT9001", "Denver Jet")
    assert got_correction == "La Compagnie", (
        "correct_airline_name('DJT9001', 'Denver Jet') = %r, expected 'La Compagnie'" % (got_correction,)
    )

    got_def = enrich.airline_from_callsign("DEF123")
    assert got_def is None, "airline_from_callsign('DEF123') = %r, expected None (QT-v9c-D-06 guard)" % (got_def,)
    got_qem = enrich.airline_from_callsign("QEM123")
    assert got_qem is None, "airline_from_callsign('QEM123') = %r, expected None (QT-v9c-D-06 guard)" % (got_qem,)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
