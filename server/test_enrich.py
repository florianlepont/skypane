#!/usr/bin/env python3
"""Contract harness for server/plane/enrich.py's adsbdb.com enrichment
client (D-02, D-P2-05).

Stdlib-only, plus the module under test (server.plane.enrich) - the module
under test itself imports `requests`, but this harness never lets that
import matter: every outbound HTTP call is replaced with an injected fake
transport (a callable returning `(status_code, json_body)`, matching
`lookup_route`'s `transport` parameter), so this harness makes no live
network call anywhere and must pass with the network unavailable. Exits 0
only when every check below passes; any failure (or exception - none is
ever swallowed into a pass) exits 1.

Usage:
    server/.venv/bin/python3 server/test_enrich.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
FIXTURES_DIR = os.path.join(HERE, "fixtures")

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

EXPECTED_CHECK_COUNT = 39


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
        import server.plane.enrich as enrich
    except ImportError as exc:
        # Ordering note: this harness is written and run now, before this
        # slice's enrich.py exists. It must fail - Task 2 turns it green.
        print("FAIL import server.plane.enrich - %r" % (exc,))
        print("enrich: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    # Quick task 260827-hyy's drift guard (checks 24) needs illustrations.py's
    # target_airline_names() - imported here, not at module scope, so a
    # Pillow-import failure is reported the same way as an enrich.py import
    # failure rather than crashing the whole harness before check() exists.
    try:
        import server.plane.illustrations as illustrations
    except ImportError as exc:
        print("FAIL import server.plane.illustrations - %r" % (exc,))
        print("enrich: 0/%d checks pass" % EXPECTED_CHECK_COUNT)
        return 1

    hit_body = load_fixture("adsbdb_hit_TVF16VB.json")
    # real recorded adsbdb miss (fixtures/README.md): {"http_status": 404,
    # "body": {"response": "unknown callsign"}} - EJU84YF is a confirmed
    # real 404, not an invented/hypothetical miss.
    miss_fixture = load_fixture("adsbdb_miss_EJU84YF.json")

    # 1. The real recorded hit fixture normalises correctly, including the
    #    sentence-case city normalisation ("Palma De Mallorca" -> "Palma de
    #    Mallorca").
    def _hit_fixture_normalises():
        cache = {}
        route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        if route is None:
            return False, "expected a resolved route, got None"
        if route.get("airline_name") != "Transavia France":
            return False, "airline_name %r != 'Transavia France'" % (route.get("airline_name"),)
        if route.get("origin_iata") != "ORY" or route.get("origin_city") != "Paris":
            return False, "origin mismatch: %r" % (route,)
        if route.get("destination_iata") != "PMI" or route.get("destination_city") != "Palma de Mallorca":
            return False, "destination mismatch (sentence-case city expected 'Palma de Mallorca'): %r" % (route,)
        return True, ""
    check("replaying the real recorded adsbdb hit (TVF16VB) yields the normalised route", _hit_fixture_normalises)

    # 2. The real recorded miss (a genuine 404) yields None, not an
    #    exception - labelled explicitly so it is never "cleaned up" as a
    #    synthetic edge case (N-02-04-01).
    def _real_recorded_miss_yields_none():
        cache = {}
        route = enrich.lookup_route(
            "EJU84YF", cache,
            transport=make_transport(miss_fixture["http_status"], miss_fixture["body"]),
        )
        if route is not None:
            return False, "expected None for the real recorded adsbdb miss (EJU84YF), got %r" % (route,)
        return True, ""
    check(
        "replaying the real recorded adsbdb miss (EJU84YF, a genuine captured 404 - see fixtures/README.md) yields None",
        _real_recorded_miss_yields_none,
    )

    # 3. A 500 response yields None without raising.
    def _500_yields_none():
        cache = {}
        route = enrich.lookup_route("AAA111", cache, transport=make_transport(500, {"error": "server error"}))
        return (route is None), "expected None for a 500 response, got %r" % (route,)
    check("a 500 response yields None without raising", _500_yields_none)

    # 4. A connection error (the transport raises) yields None without
    #    propagating the exception.
    def _connection_error_yields_none():
        cache = {}
        route = enrich.lookup_route(
            "BBB222", cache,
            transport=make_transport(None, None, raise_exc=OSError("simulated connection failure")),
        )
        return (route is None), "expected None for a connection error, got %r" % (route,)
    check("a connection error (transport raises) yields None without raising", _connection_error_yields_none)

    # 5. A non-JSON body (the transport's own .json() parse failed, so it
    #    reports a 200 with a None body, mirroring default_transport's own
    #    translation) yields None.
    def _non_json_body_yields_none():
        cache = {}
        route = enrich.lookup_route("CCC333", cache, transport=make_transport(200, None))
        return (route is None), "expected None for a non-JSON (unparseable) body, got %r" % (route,)
    check("a 200 response with a non-JSON body yields None without raising", _non_json_body_yields_none)

    # 6. A 200 JSON body missing the top-level "response" key yields None.
    def _missing_response_key_yields_none():
        cache = {}
        route = enrich.lookup_route("DDD444", cache, transport=make_transport(200, {"unexpected": True}))
        return (route is None), "expected None when the 'response' key is missing, got %r" % (route,)
    check("a 200 body missing the 'response' key yields None", _missing_response_key_yields_none)

    # 7. A 200 JSON body missing the "flightroute" key yields None.
    def _missing_flightroute_key_yields_none():
        cache = {}
        route = enrich.lookup_route("EEE555", cache, transport=make_transport(200, {"response": {}}))
        return (route is None), "expected None when the 'flightroute' key is missing, got %r" % (route,)
    check("a 200 body missing the 'flightroute' key yields None", _missing_flightroute_key_yields_none)

    # 8. A structurally incomplete route (missing/non-string municipality)
    #    yields None - UI-SPEC has no partial-route state, so a
    #    half-resolved route must never reach the renderer.
    def _half_resolved_route_yields_none():
        broken = copy.deepcopy(hit_body)
        broken["response"]["flightroute"]["destination"]["municipality"] = None
        cache = {}
        route = enrich.lookup_route("FFF666", cache, transport=make_transport(200, broken))
        return (
            route is None,
            "a route missing destination.municipality must yield None (no partial route), got %r" % (route,),
        )
    check(
        "a structurally incomplete 200 body (missing/non-string municipality) yields None - UI-SPEC has no partial state",
        _half_resolved_route_yields_none,
    )

    # 9. Cache: two consecutive lookups for the same callsign invoke the
    #    transport exactly once (hit case).
    def _hit_is_cached():
        cache = {}
        calls = []
        transport = make_transport(200, hit_body, calls=calls)
        first = enrich.lookup_route("TVF16VB", cache, transport=transport)
        second = enrich.lookup_route("TVF16VB", cache, transport=transport)
        if len(calls) != 1:
            return False, "expected exactly 1 transport call across two lookups, got %d" % len(calls)
        if first != second:
            return False, "cached lookup returned a different result than the fresh lookup"
        return True, ""
    check("two consecutive lookups for the same callsign invoke the transport exactly once (cached hit)", _hit_is_cached)

    # 10. Cache: a cached miss is also honoured - never re-queried. A
    #     rotating low-cost callsign will keep missing forever, so
    #     re-querying it every poll wastes calls against an undocumented
    #     rate limit (02-RESEARCH.md assumption A2).
    def _miss_is_cached():
        cache = {}
        calls = []
        transport = make_transport(miss_fixture["http_status"], miss_fixture["body"], calls=calls)
        first = enrich.lookup_route("EJU84YF", cache, transport=transport)
        second = enrich.lookup_route("EJU84YF", cache, transport=transport)
        if len(calls) != 1:
            return False, "a cached miss must not be re-queried on a later lookup - expected 1 transport call, got %d" % len(calls)
        if first is not None or second is not None:
            return False, "expected both lookups to yield None for a cached miss"
        return True, ""
    check("a cached miss (a callsign that returned 404) is never re-queried on a later lookup", _miss_is_cached)

    # 11. The cache round-trips through a JSON-serialisable structure, so
    #     it can live in poll_state.json (D-P2-02) across process
    #     boundaries.
    def _cache_round_trips_through_json():
        cache = {}
        enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        enrich.lookup_route("EJU84YF", cache, transport=make_transport(miss_fixture["http_status"], miss_fixture["body"]))
        try:
            reloaded = json.loads(json.dumps(cache))
        except (TypeError, ValueError) as exc:
            return False, "cache is not JSON-serialisable: %r" % (exc,)

        def _explode(*_args, **_kwargs):
            raise AssertionError("transport must not be called - both callsigns are already cached")

        hit_again = enrich.lookup_route("TVF16VB", reloaded, transport=_explode)
        miss_again = enrich.lookup_route("EJU84YF", reloaded, transport=_explode)
        if hit_again is None or hit_again.get("airline_name") != "Transavia France":
            return False, "round-tripped cache did not preserve the cached hit"
        if miss_again is not None:
            return False, "round-tripped cache did not preserve the cached miss"
        return True, ""
    check(
        "the cache round-trips through json.dumps/json.loads and still honours both a cached hit and a cached miss",
        _cache_round_trips_through_json,
    )

    # 12. Callsigns are normalised (stripped, upper-cased) before both the
    #     cache key and the request URL are built, so "TVF16VB " and
    #     "tvf16vb" hit the same cache entry and the same request
    #     (02-RESEARCH.md assumption A4 - rules out a self-inflicted
    #     formatting bug).
    def _normalisation_shares_one_cache_entry_and_request():
        cache = {}
        calls = []
        transport = make_transport(200, hit_body, calls=calls)
        first = enrich.lookup_route("TVF16VB ", cache, transport=transport)
        second = enrich.lookup_route(" tvf16vb", cache, transport=transport)
        if len(calls) != 1:
            return False, "expected exactly 1 transport call for two differently-cased/whitespace-padded variants, got %d" % len(calls)
        if calls[0] != "TVF16VB":
            return False, "expected the transport to receive the normalised callsign 'TVF16VB', got %r" % (calls[0],)
        if first != second:
            return False, "differently-cased/whitespace-padded callsigns did not resolve to the same cached result"
        return True, ""
    check(
        "callsigns are normalised (stripped, upper-cased) before both the cache key and the request URL are built",
        _normalisation_shares_one_cache_entry_and_request,
    )

    # 13. City sentence-case normalisation lower-cases interior connective
    #     particles only - the first word and every non-particle word stay
    #     capitalised.
    def _sentence_case_lowercases_interior_particles():
        cases = {
            "Palma De Mallorca": "Palma de Mallorca",
            "Paris": "Paris",
            "Los Angeles": "Los Angeles",  # "Los" is not a lowered particle
            "De Soto": "De Soto",  # particle is the FIRST word - stays capitalised
        }
        for raw, expected in cases.items():
            got = enrich.to_sentence_case_city(raw)
            if got != expected:
                return False, "to_sentence_case_city(%r) = %r, expected %r" % (raw, got, expected)
        return True, ""
    check(
        "to_sentence_case_city lower-cases interior connective particles but capitalises the first word and all other words",
        _sentence_case_lowercases_interior_particles,
    )

    # 14. T-02-04-02: a hostile/malformed callsign shape is rejected before
    #     any transport call, so it can never inject a path segment or
    #     query parameter into the outbound adsbdb URL.
    def _unsafe_callsign_never_queried():
        cache = {}
        calls = []
        transport = make_transport(200, hit_body, calls=calls)
        route = enrich.lookup_route("TVF/16;VB?x=1", cache, transport=transport)
        if route is not None:
            return False, "expected None for a non-alphanumeric callsign shape"
        if calls:
            return False, "a hostile callsign shape must never reach the outbound transport - it was called with %r" % (calls,)
        return True, ""
    check(
        "a callsign containing non-alphanumeric characters is rejected before the outbound request is built (T-02-04-02)",
        _unsafe_callsign_never_queried,
    )

    # 15. city_for_state() picks the correct end of the route per state, so
    #     render.py never has to re-derive which end matters.
    def _city_for_state_picks_correct_end():
        cache = {}
        route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        if enrich.city_for_state(route, "departing") != "Palma de Mallorca":
            return False, "departing should read the destination city"
        if enrich.city_for_state(route, "arriving") != "Paris":
            return False, "arriving should read the origin city"
        if enrich.city_for_state(None, "departing") is not None:
            return False, "city_for_state(None, ...) must return None"
        return True, ""
    check("city_for_state() returns the destination city for departing and the origin city for arriving", _city_for_state_picks_correct_end)

    # 16. normalise_callsign edge cases.
    def _normalise_callsign_edge_cases():
        if enrich.normalise_callsign(" tvf16vb ") != "TVF16VB":
            return False, "expected stripped/upper-cased result"
        if enrich.normalise_callsign("") is not None:
            return False, "expected None for an empty string"
        if enrich.normalise_callsign(None) is not None:
            return False, "expected None for a non-string input"
        return True, ""
    check("normalise_callsign strips and upper-cases, returning None for anything empty or non-string", _normalise_callsign_edge_cases)

    # --- Quick task 260827-hyy: airline_from_callsign() / airline_only_route()
    # / resolve_route() - the ICAO-prefix fallback layered above the adsbdb
    # miss (D-01/D-02/D-03/D-04/D-05). ---------------------------------------

    # 17. TVF is the plan's headline case: Transavia France's stable ICAO
    #     prefix, resolved with zero network call.
    def _airline_from_callsign_tvf():
        got = enrich.airline_from_callsign("TVF16VB")
        if got != "Transavia France":
            return False, "airline_from_callsign('TVF16VB') = %r, expected 'Transavia France'" % (got,)
        return True, ""
    check("airline_from_callsign('TVF16VB') returns 'Transavia France'", _airline_from_callsign_tvf)

    # 18. Normalisation goes through the existing normalise_callsign() -
    #     whitespace/case must not change the result.
    def _airline_from_callsign_normalises():
        got = enrich.airline_from_callsign(" tvf16vb ")
        if got != "Transavia France":
            return False, "airline_from_callsign(' tvf16vb ') = %r, expected 'Transavia France'" % (got,)
        return True, ""
    check("airline_from_callsign(' tvf16vb ') normalises through normalise_callsign() before the prefix lookup", _airline_from_callsign_normalises)

    # 19. The full never-raises battery: an unknown prefix, a bare 3-letter
    #     string with no flight suffix, empty string, None, an int, and a
    #     callsign containing a path separator all yield None and none of
    #     them raise (T-hyy-01/T-hyy-02).
    def _airline_from_callsign_never_raises_battery():
        cases = ["ZZZ1234", "TVF", "", None, 42, "TVF/16VB"]
        for case in cases:
            try:
                got = enrich.airline_from_callsign(case)
            except Exception as exc:
                return False, "airline_from_callsign(%r) raised %r instead of returning None" % (case, exc)
            if got is not None:
                return False, "airline_from_callsign(%r) = %r, expected None" % (case, got)
        return True, ""
    check(
        "airline_from_callsign() returns None (never raises) for an unknown prefix, a bare 3-letter string, "
        "empty string, None, an int, and a path-separator payload",
        _airline_from_callsign_never_raises_battery,
    )

    # 20. airline_only_route() produces the exact D-03 shape: the same key
    #     set _parse_route() produces on the real hit fixture, airline_name
    #     set and the other four keys None. airline_only_route(None) is None.
    def _airline_only_route_shape_and_none_handling():
        cache = {}
        full_route = enrich.lookup_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        if full_route is None:
            return False, "setup failure: expected the real hit fixture to resolve a full route"
        expected_keys = set(full_route.keys())
        got = enrich.airline_only_route("Transavia France")
        if got is None:
            return False, "airline_only_route('Transavia France') returned None, expected a dict"
        if set(got.keys()) != expected_keys:
            return False, "airline_only_route() key set %r != _parse_route()'s real key set %r" % (set(got.keys()), expected_keys)
        if got.get("airline_name") != "Transavia France":
            return False, "airline_only_route() airline_name = %r, expected 'Transavia France'" % (got.get("airline_name"),)
        for key in expected_keys - {"airline_name"}:
            if got.get(key) is not None:
                return False, "airline_only_route() key %r = %r, expected None" % (key, got.get(key))
        if enrich.airline_only_route(None) is not None:
            return False, "airline_only_route(None) should return None"
        return True, ""
    check(
        "airline_only_route('Transavia France') carries _parse_route()'s exact key set, airline_name set and the "
        "other four keys None; airline_only_route(None) returns None",
        _airline_only_route_shape_and_none_handling,
    )

    # 21. resolve_route() on a real recorded miss (EJU84YF, a genuine 404)
    #     falls to the prefix table: airline_only route, source "airline_only".
    #     A second call with the same cache returns the same route/source and
    #     the fake transport is invoked exactly once - the miss is cached, the
    #     prefix resolution is recomputed from the static table each time, not
    #     re-queried.
    def _resolve_route_airline_only_on_real_miss():
        cache = {}
        calls = []
        transport = make_transport(miss_fixture["http_status"], miss_fixture["body"], calls=calls)
        route1, source1 = enrich.resolve_route("EJU84YF", cache, transport=transport)
        route2, source2 = enrich.resolve_route("EJU84YF", cache, transport=transport)
        if source1 != "airline_only" or source2 != "airline_only":
            return False, "expected source 'airline_only' on both calls, got %r then %r" % (source1, source2)
        if route1 is None or route1.get("airline_name") != "easyJet":
            return False, "expected an airline-only route with airline_name 'easyJet', got %r" % (route1,)
        if route2 != route1:
            return False, "second resolve_route() call returned a different route than the first: %r vs %r" % (route2, route1)
        if len(calls) != 1:
            return False, "expected the transport to be invoked exactly once (the miss is cached), got %d calls" % len(calls)
        return True, ""
    check(
        "resolve_route('EJU84YF', ...) on the real recorded adsbdb miss yields an 'easyJet' airline-only route with "
        "source 'airline_only', identically on a second call, with exactly one transport invocation",
        _resolve_route_airline_only_on_real_miss,
    )

    # 22. resolve_route() on a real hit classifies fresh_hit then cache_hit -
    #     the pre-existing three-way classification, unchanged in meaning.
    def _resolve_route_fresh_then_cache_hit():
        cache = {}
        route1, source1 = enrich.resolve_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        if source1 != "fresh_hit":
            return False, "expected source 'fresh_hit' on the first call, got %r" % (source1,)
        route2, source2 = enrich.resolve_route("TVF16VB", cache, transport=make_transport(200, hit_body))
        if source2 != "cache_hit":
            return False, "expected source 'cache_hit' on the second call, got %r" % (source2,)
        if route1 != route2:
            return False, "fresh_hit and cache_hit calls returned different routes: %r vs %r" % (route1, route2)
        return True, ""
    check("resolve_route('TVF16VB', ...) classifies fresh_hit on the first call and cache_hit on the second", _resolve_route_fresh_then_cache_hit)

    # 23. A miss whose callsign prefix is not in the static table at all
    #     returns (None, "miss") - the fourth (and final) fallback rung.
    def _resolve_route_unknown_prefix_is_miss():
        cache = {}
        route, source = enrich.resolve_route(
            "ZZZ1234", cache, transport=make_transport(404, {"response": "unknown callsign"}),
        )
        if route is not None or source != "miss":
            return False, "expected (None, 'miss') for an unknown-prefix miss, got (%r, %r)" % (route, source)
        return True, ""
    check("resolve_route() on a miss whose callsign prefix is absent from the table returns (None, 'miss')", _resolve_route_unknown_prefix_is_miss)

    # 24. Drift guard (D-07): every airline name the static prefix table can
    #     ever produce must already be one of illustrations.py's own target
    #     airline names - a rename/removal there that is not mirrored here
    #     must fail this suite, not degrade silently to a lost illustration.
    def _prefix_table_values_are_a_subset_of_illustration_targets():
        prefix_values = set(enrich._ICAO_AIRLINE_PREFIXES.values())
        target_names = set(illustrations.target_airline_names())
        missing = prefix_values - target_names
        if missing:
            return False, "prefix table produces airline name(s) with no illustration target: %r" % (sorted(missing),)
        return True, ""
    check(
        "every value in enrich._ICAO_AIRLINE_PREFIXES is a member of illustrations.target_airline_names() (D-07 drift guard)",
        _prefix_table_values_are_a_subset_of_illustration_targets,
    )

    # 25. Shape guard: every key of the prefix table is exactly 3 uppercase
    #     A-Z characters - the same shape airline_from_callsign() itself
    #     requires of a prefix before it will ever look one up.
    def _prefix_table_keys_are_three_uppercase_letters():
        bad = [k for k in enrich._ICAO_AIRLINE_PREFIXES if not (isinstance(k, str) and len(k) == 3 and k.isalpha() and k == k.upper())]
        if bad:
            return False, "prefix table has key(s) that are not exactly 3 uppercase A-Z letters: %r" % (bad,)
        return True, ""
    check("every key of enrich._ICAO_AIRLINE_PREFIXES is exactly 3 uppercase A-Z characters", _prefix_table_keys_are_three_uppercase_letters)

    # 26. Quick task 260827-jz6: KM Malta Airlines resolves from the real
    #     callsign this session actually curled (KMM466) against the live
    #     adsbdb endpoint, which returned "unknown callsign" - a confirmed
    #     permanent miss, resolved with zero network call here.
    def _airline_from_callsign_km_malta():
        got = enrich.airline_from_callsign("KMM466")
        if got != "KM Malta Airlines":
            return False, "airline_from_callsign('KMM466') = %r, expected 'KM Malta Airlines'" % (got,)
        return True, ""
    check("airline_from_callsign('KMM466') returns 'KM Malta Airlines' (260827-jz6, real curled callsign)", _airline_from_callsign_km_malta)

    # 27. Quick task 260827-jz6: TUIfly Belgium resolves from the real
    #     callsign this session actually curled (JAF7521) - adsbdb itself
    #     resolves that exact callsign to "Jetairfly" (QT-jz6-D-02), but the
    #     prefix table deliberately carries the current brand name instead.
    def _airline_from_callsign_tuifly_belgium():
        got = enrich.airline_from_callsign("JAF7521")
        if got != "TUIfly Belgium":
            return False, "airline_from_callsign('JAF7521') = %r, expected 'TUIfly Belgium'" % (got,)
        return True, ""
    check("airline_from_callsign('JAF7521') returns 'TUIfly Belgium' (260827-jz6, real curled callsign, QT-jz6-D-02 override)", _airline_from_callsign_tuifly_belgium)

    # --- Quick task 260827-kih: enrich.correct_airline_name() /
    # apply_airline_name_correction() - the single prefix-scoped correction
    # seam applied inside lookup_route(). ---------------------------------

    aia_hit_body = load_fixture("adsbdb_hit_AIA6412.json")["body"]

    # 28. The headline case: adsbdb's real recorded AIA6412 response
    #     attributes the AIA prefix to "Avies" (a different, defunct
    #     Estonian carrier) - correct_airline_name() corrects it to "Amelia".
    def _correct_airline_name_aia_to_amelia():
        got = enrich.correct_airline_name("AIA6412", "Avies")
        if got != "Amelia":
            return False, "correct_airline_name('AIA6412', 'Avies') = %r, expected 'Amelia'" % (got,)
        return True, ""
    check("correct_airline_name('AIA6412', 'Avies') returns 'Amelia' (260827-kih)", _correct_airline_name_aia_to_amelia)

    # 29. The corrected-away string arriving under a DIFFERENT prefix is
    #     never rewritten - the correction is keyed on the (prefix, string)
    #     pair, never on the string alone (QT-kih-D-01).
    def _correct_airline_name_is_prefix_scoped():
        got = enrich.correct_airline_name("ZZZ1234", "Avies")
        if got != "Avies":
            return False, "correct_airline_name('ZZZ1234', 'Avies') = %r, expected 'Avies' unchanged (prefix-scoped, not a global replace)" % (got,)
        return True, ""
    check(
        "correct_airline_name('ZZZ1234', 'Avies') returns 'Avies' unchanged - a different prefix carrying the "
        "same string is never rewritten (QT-kih-D-01)",
        _correct_airline_name_is_prefix_scoped,
    )

    # 30. End to end through resolve_route(): a fresh 200 hit that
    #     misattributes AIA6412 to Avies is corrected to "Amelia" (source
    #     "fresh_hit"); a second call against the same cache is corrected
    #     identically (source "cache_hit"), with exactly one transport call
    #     across both - and the cache entry ITSELF still holds the raw
    #     upstream string "Avies", proving the correction is applied on
    #     read, never on write (QT-kih-D-02).
    def _resolve_route_corrects_aia_fresh_then_cached():
        cache = {}
        calls = []
        transport = make_transport(200, aia_hit_body, calls=calls)
        route1, source1 = enrich.resolve_route("AIA6412", cache, transport=transport)
        if route1 is None or route1.get("airline_name") != "Amelia" or source1 != "fresh_hit":
            return False, "expected a fresh_hit route with airline_name 'Amelia', got (%r, %r)" % (route1, source1)
        route2, source2 = enrich.resolve_route("AIA6412", cache, transport=transport)
        if route2 is None or route2.get("airline_name") != "Amelia" or source2 != "cache_hit":
            return False, "expected a cache_hit route with airline_name 'Amelia', got (%r, %r)" % (route2, source2)
        if len(calls) != 1:
            return False, "expected exactly 1 transport call across both resolve_route() calls, got %d" % len(calls)
        cached_entry = cache.get("AIA6412")
        if not isinstance(cached_entry, dict) or cached_entry.get("airline_name") != "Avies":
            return False, "the cache entry itself must still hold the raw upstream string 'Avies', got %r" % (cached_entry,)
        return True, ""
    check(
        "resolve_route('AIA6412', ...) corrects the real recorded AIA/Avies misattribution to 'Amelia' on both a "
        "fresh_hit and a cache_hit, while the cache entry itself keeps the raw upstream string (QT-kih-D-02)",
        _resolve_route_corrects_aia_fresh_then_cached,
    )

    # 31. airline_from_callsign('AIA6412') resolves 'Amelia' with zero
    #     network call - the prefix-only fallback path already carries the
    #     corrected value by construction (QT-kih-D-03).
    def _airline_from_callsign_aia_amelia():
        got = enrich.airline_from_callsign("AIA6412")
        if got != "Amelia":
            return False, "airline_from_callsign('AIA6412') = %r, expected 'Amelia'" % (got,)
        return True, ""
    check("airline_from_callsign('AIA6412') returns 'Amelia' (260827-kih, zero network call)", _airline_from_callsign_aia_amelia)

    # 32. The cross-table invariant (QT-kih-D-03): for every
    #     (prefix, stale) -> corrected row in _AIRLINE_NAME_CORRECTIONS,
    #     _ICAO_AIRLINE_PREFIXES[prefix] equals the corrected value, and the
    #     corrected value is a member of illustrations.target_airline_names().
    #     Iterates the real table rather than restating its contents, so a
    #     future correction row that forgets to mirror the prefix table
    #     fails this check instead of silently drifting.
    def _correction_table_agrees_with_prefix_table_and_targets():
        target_names = set(illustrations.target_airline_names())
        for (prefix, _stale), corrected in enrich._AIRLINE_NAME_CORRECTIONS.items():
            prefix_value = enrich._ICAO_AIRLINE_PREFIXES.get(prefix)
            if prefix_value != corrected:
                return False, (
                    "_AIRLINE_NAME_CORRECTIONS[(%r, ...)] = %r but _ICAO_AIRLINE_PREFIXES[%r] = %r - the two "
                    "tables must agree" % (prefix, corrected, prefix, prefix_value)
                )
            if corrected not in target_names:
                return False, "corrected value %r is not a member of illustrations.target_airline_names()" % (corrected,)
        return True, ""
    check(
        "every _AIRLINE_NAME_CORRECTIONS row agrees with _ICAO_AIRLINE_PREFIXES and its corrected value is a "
        "target_airline_names() member (QT-kih-D-03 cross-table invariant)",
        _correction_table_agrees_with_prefix_table_and_targets,
    )

    # 33. Never-raises battery for both new functions: None, an int, an
    #     empty string, a bare 3-letter callsign, a path-separator payload,
    #     a non-dict route, and a route whose .get() raises - and neither
    #     function ever returns a value derived from its arguments other
    #     than the unchanged airline_name it was handed (T-kih-01).
    def _correction_seam_never_raises_battery():
        # Hostile/malformed callsigns: None, an int, an empty string, a bare
        # 3-letter string with no flight suffix, and a path-separator
        # payload - none of these can ever reach _AIRLINE_NAME_CORRECTIONS,
        # so correct_airline_name() must return airline_name unchanged for
        # every one of them, and never raise.
        hostile_callsigns = (None, 42, "", "AIA", "AIA/6412")
        for callsign in hostile_callsigns:
            for airline_name in (None, 42, "", "Avies"):
                try:
                    got = enrich.correct_airline_name(callsign, airline_name)
                except Exception as exc:
                    return False, "correct_airline_name(%r, %r) raised %r" % (callsign, airline_name, exc)
                if got is not airline_name:
                    return False, (
                        "correct_airline_name(%r, %r) = %r - a hostile/malformed callsign must never change the "
                        "airline_name it was handed" % (callsign, airline_name, got)
                    )

        class _ExplodingRoute(dict):
            def get(self, *_args, **_kwargs):
                raise RuntimeError("simulated .get() failure")

        malformed_routes = (None, {}, "not-a-dict", 42, ["a", "list"], _ExplodingRoute())
        for callsign in hostile_callsigns:
            for route in malformed_routes:
                try:
                    got = enrich.apply_airline_name_correction(callsign, route)
                except Exception as exc:
                    return False, "apply_airline_name_correction(%r, %r) raised %r" % (callsign, route, exc)
                if not isinstance(route, dict) or isinstance(route, _ExplodingRoute):
                    if got is not route:
                        return False, "apply_airline_name_correction(%r, %r) should return the non-dict route unchanged, got %r" % (callsign, route, got)
        return True, ""
    check(
        "correct_airline_name()/apply_airline_name_correction() never raise for a hostile callsign x airline_name/"
        "route battery (None, int, empty string, bare prefix, path-separator payload, non-dict route, a route "
        "whose .get() raises), and never return a value derived from the arguments other than the unchanged "
        "airline_name (T-kih-01)",
        _correction_seam_never_raises_battery,
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

    # 34. correct_airline_name() maps each of the three (prefix, upstream
    #     string) pairs to its real current name.
    def _correct_airline_name_three_stale_brand_pairs():
        cases = [
            ("FPO701", "Europe Airpost", "ASL Airlines France"),
            ("CRL8025", "Corsairfly", "Corsair"),
            ("CCM21AW", "CCM Airlines", "Air Corsica"),
        ]
        for callsign, stale, expected in cases:
            got = enrich.correct_airline_name(callsign, stale)
            if got != expected:
                return False, "correct_airline_name(%r, %r) = %r, expected %r" % (callsign, stale, got, expected)
        return True, ""
    check(
        "correct_airline_name() maps FPO/Europe Airpost -> ASL Airlines France, CRL/Corsairfly -> Corsair, "
        "CCM/CCM Airlines -> Air Corsica (260827-kih)",
        _correct_airline_name_three_stale_brand_pairs,
    )

    # 35. End-to-end: resolve_route() against a stubbed 200 body carrying
    #     each upstream string under its own prefix returns the corrected
    #     name; the same body served under an unrelated prefix returns the
    #     upstream string untouched (the negative prefix-scoped case).
    #     select_illustration() on the corrected CCM/Air Corsica route
    #     resolves to the renamed primary (A320) and secondary (ATR72)
    #     files - proving the correction lands before illustration
    #     selection, not just in the caption text.
    def _resolve_route_and_selection_for_three_stale_brand_carriers():
        cases = [
            ("FPO701", "Europe Airpost", "ASL Airlines France"),
            ("CRL8025", "Corsairfly", "Corsair"),
            ("CCM21AW", "CCM Airlines", "Air Corsica"),
        ]
        for callsign, stale, expected in cases:
            cache = {}
            body = _stubbed_hit_body(stale)
            route, source = enrich.resolve_route(callsign, cache, transport=make_transport(200, body))
            if route is None or route.get("airline_name") != expected or source != "fresh_hit":
                return False, "resolve_route(%r, ...) = (%r, %r), expected airline_name %r, source 'fresh_hit'" % (
                    callsign, route, source, expected,
                )

        # Negative case: the same upstream string, served under an
        # UNRELATED prefix, must come back untouched - the correction is
        # keyed on the (prefix, string) pair, never on the string alone.
        cache = {}
        unrelated_body = _stubbed_hit_body("CCM Airlines")
        route, source = enrich.resolve_route("ZZZ9999", cache, transport=make_transport(200, unrelated_body))
        if route is None or route.get("airline_name") != "CCM Airlines":
            return False, "resolve_route('ZZZ9999', ...) with airline_name 'CCM Airlines' under an unrelated " \
                "prefix must come back untouched, got %r" % (route,)

        ccm_route = enrich.airline_only_route("Air Corsica")
        primary = illustrations.select_illustration(ccm_route, "A320")
        if primary is None or os.path.basename(primary) != "air-corsica.png":
            return False, "select_illustration(Air Corsica route, 'A320') = %r, expected air-corsica.png" % (primary,)
        secondary = illustrations.select_illustration(ccm_route, "AT72")
        if secondary is None or os.path.basename(secondary) != "air-corsica-atr72.png":
            return False, "select_illustration(Air Corsica route, 'AT72') = %r, expected air-corsica-atr72.png" % (secondary,)
        return True, ""
    check(
        "resolve_route() corrects all three stale-brand carriers under their own prefix and leaves the same "
        "string untouched under an unrelated prefix; the corrected Air Corsica route selects the renamed "
        "air-corsica.png/air-corsica-atr72.png files (260827-kih)",
        _resolve_route_and_selection_for_three_stale_brand_carriers,
    )

    # --- Quick task 260827-lgt: HOP! Air France, Wizz Air Malta, KlasJet -
    # three new prefix-table rows, cross-checked against the official
    # Paris Aeroport Orly airline list. ------------------------------------

    # 36. HOP resolves from the real callsign this session curled
    #     (HOP4001) - adsbdb resolves the exact same string live, so both
    #     the adsbdb-hit path and this prefix-only fallback path agree by
    #     construction (QT-lgt-D-03).
    def _airline_from_callsign_hop_air_france():
        got = enrich.airline_from_callsign("HOP4001")
        if got != "Air France Hop":
            return False, "airline_from_callsign('HOP4001') = %r, expected 'Air France Hop'" % (got,)
        return True, ""
    check("airline_from_callsign('HOP4001') returns 'Air France Hop' (260827-lgt, real curled callsign)", _airline_from_callsign_hop_air_france)

    # 37. WMT resolves to the parent brand name "Wizz Air", deliberately
    #     (QT-lgt-D-01) - real callsign WMT3001 curled live this session
    #     resolves via adsbdb to the more-specific "Wizz Air Malta", but
    #     this prefix-only fallback path intentionally returns the parent
    #     brand instead, the same EJU -> easyJet consolidation precedent.
    def _airline_from_callsign_wizz_air_malta():
        got = enrich.airline_from_callsign("WMT3001")
        if got != "Wizz Air":
            return False, "airline_from_callsign('WMT3001') = %r, expected 'Wizz Air'" % (got,)
        return True, ""
    check("airline_from_callsign('WMT3001') returns 'Wizz Air' (260827-lgt, real curled callsign WMT3001; adsbdb itself resolves 'Wizz Air Malta', QT-lgt-D-01 deliberate brand consolidation)", _airline_from_callsign_wizz_air_malta)

    # 38. KLJ resolves to "KlasJet" from a synthetic, shape-valid callsign
    #     only - no real KLJ callsign could be confirmed live this session
    #     (QT-lgt-D-06, ~25 adsbdb probes all missed). This check proves
    #     only that the table row is wired correctly, not that the prefix
    #     assignment itself is correct.
    def _airline_from_callsign_klasjet():
        got = enrich.airline_from_callsign("KLJ123")
        if got != "KlasJet":
            return False, "airline_from_callsign('KLJ123') = %r, expected 'KlasJet'" % (got,)
        return True, ""
    check("airline_from_callsign('KLJ123') returns 'KlasJet' (260827-lgt, KLJ123 is a SYNTHETIC shape-valid callsign - no real KLJ callsign was ever live-confirmed, QT-lgt-D-06)", _airline_from_callsign_klasjet)

    # 39. QT-lgt-D-07 guard: none of HOP/WMT/KLJ needs a correction row -
    #     HOP because adsbdb is already correct, WMT because a
    #     more-specific adsbdb answer is an accepted divergence not a
    #     misattribution, and KLJ because nothing resolves at all. This
    #     keeps a future reader from "completing the job" by adding
    #     correction rows none of these three actually needs.
    def _no_correction_row_for_new_lgt_prefixes():
        bad = [k for k in enrich._AIRLINE_NAME_CORRECTIONS if k[0] in ("HOP", "WMT", "KLJ")]
        if bad:
            return False, "unexpected _AIRLINE_NAME_CORRECTIONS row(s) for HOP/WMT/KLJ: %r" % (bad,)
        return True, ""
    check(
        "no _AIRLINE_NAME_CORRECTIONS row exists whose prefix element is HOP, WMT or KLJ (QT-lgt-D-07 guard)",
        _no_correction_row_for_new_lgt_prefixes,
    )

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("enrich: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
