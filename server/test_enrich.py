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

EXPECTED_CHECK_COUNT = 16


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

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("enrich: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    sys.exit(main())
