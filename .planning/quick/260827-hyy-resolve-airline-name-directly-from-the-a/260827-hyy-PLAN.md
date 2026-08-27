---
phase: 03.1-procedural-per-airline-livery-rendering
plan: 260827-hyy
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - server/plane/enrich.py
  - server/plane/illustrations.py
  - server/plane/render.py
  - server/poll_loop.py
  - server/test_enrich.py
  - server/test_illustrations.py
  - server/test_render.py
  - README.md
  - ARCHITECTURE.md
autonomous: true
requirements: [PLANE-01, PLANE-02]

must_haves:
  truths:
    - "A real Transavia France detection whose callsign adsbdb cannot resolve (the ~90% case measured at 2/20) now shows `Transavia France` in the caption and renders `transavia-france.png`, instead of `Route unavailable` and `generic-fallback.png`."
    - "The same holds for `EJU` (easyJet Europe), the other permanently-unresolvable prefix this project's own code documents — it now reaches `easyjet.png`."
    - "The destination is still shown as genuinely unknown: line 1 stays the bare callsign, and no origin/destination city is ever fabricated from the prefix."
    - "`Route unavailable` still appears, but now means strictly `neither adsbdb nor the callsign prefix resolved an airline` — it is not shown when the airline is known."
    - "The airline-name strings the prefix table produces are the same strings `illustrations.py` already selects on — a rename or removal in `_ILLUSTRATION_TARGETS` that is not mirrored in the prefix table fails the test suite."
    - "`adsbdb`'s own response parsing is unchanged: a structurally incomplete 200 is still a whole-lookup miss, and the enrichment cache still never re-queries a callsign."
    - "The whole change adds zero network calls: the prefix resolution is a pure lookup against a static, in-repo table."
    - "`scripts/run-all-tests.sh`, `ruff check .` and `scripts/check-attribution.sh` are all green, and README's stated check total equals the harnesses' real sum."
  artifacts:
    - server/plane/enrich.py
    - server/plane/illustrations.py
    - server/plane/render.py
    - server/poll_loop.py
    - server/test_enrich.py
    - server/test_illustrations.py
    - server/test_render.py
  key_links:
    - "`server/poll_loop.py:218` is the ONLY production call site of `enrich.lookup_route()`. If the new resolution seam is added to `enrich.py` but this line is not switched to it, every claim in this plan is false in production while every unit test still passes. This is the single load-bearing wire."
    - "`illustrations.select_illustration()` reads `route['airline_name']` and nothing else about the airline. Handing it an airline-only route dict with the four route fields set to `None` is therefore sufficient to recover the correct illustration with zero change to `illustrations.py`'s selection logic — but only if the dict carries the exact same five keys `_parse_route()` produces."
    - "`render._flight_line1_text()` calls `enrich.city_for_state(route, state)` and falls back to the bare callsign when it returns falsy. The airline-only dict's `None` city values are what keep line 1 honest. If those keys were omitted rather than set to `None`, `.get()` still returns `None` — but `_route_from_entry()`/`city_for_state()` contract clarity depends on the shape being identical, so the shape is constructed in one place (`airline_only_route()`) and nowhere else."
    - "README.md line 94 states a total check count. This branch is ALREADY stale there (it says 119; the merged runway3 debug work pushed the real sum to 167 without updating it). Task 3 recomputes it from the harnesses themselves rather than incrementing the stale number."
---

<objective>
`server/plane/enrich.py`'s adsbdb lookup is all-or-nothing: unless adsbdb resolves airline **and** origin **and** destination, the whole result is a miss and the panel falls to `Route unavailable` + `generic-fallback.png`. For carriers with per-tail rotating callsigns — measured at 2/20 = 10% for Transavia France, the carrier that dominates this specific rooftop's traffic — that throws away the airline identity on ~90% of detections, even though the airline was never a function of adsbdb in the first place: it is carried directly in the callsign's ICAO 3-letter prefix (`TVF` = Transavia France), which is stable, standardised reference data.

This plan resolves the airline from that prefix as an independent fallback source, layered **above** the adsbdb miss rather than replacing it, so the correct airline name and the correct illustration survive a route miss.

Purpose: on the carriers the user actually sees most, the frame stops saying "I know nothing" when it in fact knows who is flying.
Output: a static, evidence-sourced ICAO-prefix table in `enrich.py`; a single new resolution seam wired into `poll_loop.py`; a new, concretely-specified intermediate caption state; regression coverage in three existing harnesses; reconciled docs.

**Explicitly out of scope** (deferred, see `.planning/seeds/aerodatabox-destination-lookup-rotating-callsigns.md`): recovering the actual **destination** for these carriers. That needs a live same-day schedule source and is not attempted here. No new API, no new dependency, no new network call.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/todos/pending/airline-name-from-callsign-prefix.md
@.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md
@.planning/phases/03.1-procedural-per-airline-livery-rendering/03.1-LIVE-RESOLUTION.md
@server/plane/enrich.py
@server/plane/illustrations.py
@server/plane/render.py
@server/poll_loop.py
@server/test_enrich.py
@server/fixtures/README.md
</context>

<design_decisions>

These are locked. They exist because the todo file explicitly asks for a concrete answer on two of them (the name table's source, and the render state), and because the orchestrator's constraints forbid inventing a parallel airline list.

## D-01 — The prefix table is sourced from `03.1-LIVE-RESOLUTION.md`, not from model knowledge

`.planning/phases/03.1-procedural-per-airline-livery-rendering/03.1-LIVE-RESOLUTION.md` contains a table titled **"Resolved airline names (full D-03 table, 24 airlines)"** whose columns are exactly what is needed: the ICAO probe code used (`Airline endpoint VLG`, `Callsign TVF16VB`, `Verified Finding #3 (WZZ8025 HIT)`, …) and the **verbatim** resolved `airline_name` string. That file is live evidence captured against the real API and is the authority for this table. Do not substitute training-knowledge ICAO codes for any row it covers.

The 23 entries, with the in-repo evidence that pins each prefix:

| Prefix | `airline_name` (verbatim) | Evidence in `03.1-LIVE-RESOLUTION.md` |
|---|---|---|
| `AFR` | `Air France` | callsign `AFR56XX` |
| `CCM` | `CCM Airlines` | callsign `CCM21AW` |
| `VLG` | `Vueling Airlines` | airline endpoint `VLG` |
| `IBE` | `Iberia Airlines` | airline endpoint `IBE` |
| `TAP` | `TAP Portugal` | airline endpoint `TAP` |
| `TVF` | `Transavia France` | callsign `TVF16VB` |
| `EZY` | `easyJet` | callsign `EZY63GN` |
| `EJU` | `easyJet` | **see D-02 — the one entry not from that table** |
| `WZZ` | `Wizz Air` | cited callsign `WZZ8025` |
| `VOE` | `Volotea` | cited callsign `VOE8KA` |
| `ITY` | `ITA Airways` | cited callsign `ITY1830` |
| `AEA` | `Air Europa` | cited callsign `AEA075` |
| `DAH` | `Air Algerie` | airline endpoint `DAH` |
| `FPO` | `Europe Airpost` | callsigns `FPO701`/`FPO458` |
| `RAM` | `Royal Air Maroc` | cited callsign `RAM754` |
| `TAR` | `Tunisair` | airline endpoint `TAR` |
| `PGT` | `Pegasus Airlines` | callsign `PGT80PT` |
| `LOT` | `LOT Polish Airlines` | cited callsign `LOT331` |
| `CLG` | `Chalair Aviation` | airline endpoint `CLG` |
| `TJT` | `Twin Jet` | callsign `TJT352A` |
| `FWI` | `Air Caraïbes` | cited callsign `FWI701` |
| `CRL` | `Corsairfly` | airline endpoint `CRL` |
| `FBU` | `French Bee` | cited callsign `FBU701` |

Note the three rename traps are honoured by construction, because the values are copied from the resolved column: `CCM Airlines` (not "Air Corsica"), `Europe Airpost` (not "ASL Airlines France"), `Corsairfly` (not "Corsair International"). Copy these strings; do not retype them from the brand names.

**Deliberately absent:** Amelia International and La Compagnie. `03.1-LIVE-RESOLUTION.md` marks both `[UNRESOLVED]` (`AEH` resolves to a different real airline, `DJT` to an unrelated US operator), and `_ILLUSTRATION_TARGETS` excludes both for the same reason. Adding a guessed code for either would put a wrong airline name on the glass — the exact failure this table is supposed to prevent.

## D-02 — `EJU` maps to the same `easyJet` key as `EZY`

This is the one entry not in the live-resolution table, and it is a deliberate brand-level (not AOC-level) mapping. Rationale: `EJU` is easyJet's Austrian AOC, flying the same brand and the same livery as the UK-AOC `EZY`; the project already vendors exactly one asset for the brand (`easyjet.png`); and `EJU` is documented in `illustrations.py`'s own module docstring and in 03.1-RESEARCH's P-03 as a **confirmed permanent adsbdb miss**, so this prefix can never contradict a live lookup — adsbdb never returns anything for it. Give this row its own inline comment in the table naming it as the brand-level exception, so a later reader does not mistake it for an evidence-sourced row.

## D-03 — The airline-only route dict carries the exact five `_parse_route()` keys, four of them `None`

```
{"airline_name": <name>, "origin_iata": None, "origin_city": None,
 "destination_iata": None, "destination_city": None}
```

Constructed in exactly one place (`airline_only_route()`), never inline. This is what makes every downstream consumer work unchanged: `city_for_state()` returns `None`, `_flight_line1_text()` falls to the bare callsign, `_flight_line2_text()` finds an airline, `select_illustration()` finds an airline key.

## D-04 — `lookup_route()` and `_parse_route()` are NOT loosened

A structurally incomplete adsbdb 200 remains a whole-lookup miss, and the hit/miss cache keeps its current never-re-query behaviour. The new fallback is a **separate source with different provenance** stacked above the miss, not a relaxation of adsbdb parsing. adsbdb's half-resolved payloads are untrustworthy crowdsourced data; an ICAO designator prefix is standardised reference data. Different trust, different mechanism, no coupling.

## D-05 — One new seam: `enrich.resolve_route(callsign, cache, transport=None, timeout=...) -> (route, source)`

`source` is one of `"fresh_hit"`, `"cache_hit"`, `"airline_only"`, `"miss"`. The first three-way classification currently living inline in `poll_loop.py` (the `was_cached` / `route_source` block) moves into this function with its meaning preserved exactly — `"cache_hit"` still means the cache spared a request **and** returned a usable route, and a cached miss is still not a cache hit. `"airline_only"` is the new fourth category. This gives `journalctl -u skypane-poll` a directly greppable signal that the fallback fired on real traffic.

## D-06 — The render/caption intermediate state (the decision the todo asks for)

| adsbdb | prefix | Line 1 | Line 2 | Illustration |
|---|---|---|---|---|
| hit | — | `{callsign} to\|from {city}` | `{airline} · {type}` | airline art |
| miss | **hit** | `{callsign}` (bare) | `{airline} · {type}` | **airline art** |
| miss | miss | `{callsign}` (bare) | `Route unavailable` | generic fallback |

Concretely, the middle row turns today's `TVF16VB` / `Route unavailable` / `generic-fallback.png` into `TVF16VB` / `Transavia France · 737-800` / `transavia-france.png`.

**Line 1 deliberately stays the bare callsign.** Line 1 *is* the route line under D-26; a bare callsign there already reads as "no route known", it is the exact typographic state Phase 2 verified on real glass, and it introduces no new string and no new width risk into the hero line ahead of Phase 6's on-glass sign-off. The newly-recovered fact belongs on the airline line, which is where a reader already looks for it.

**`ROUTE_FALLBACK_TEXT` is not renamed and not reworded.** Its meaning narrows honestly: it now fires only when neither source resolved anything.

**Rejected alternative:** `"{callsign} · destination unknown"` on line 1. It puts a second negative string on a glanceable panel where the absence is already legible, and lengthens the hero line enough to risk `fit_text_size()` shrinking it on long callsigns.

**Consequence — and this is the point:** `render.py`'s and `illustrations.py`'s selection/caption logic need **no functional change** to produce this table. They already do the right thing when handed a D-03-shaped dict. The work in those files is (a) proving it with regression checks, (b) correcting the docstrings that currently assert the opposite, (c) a manual-QA preview flag so Phase 6 can put the new state on real glass.

## D-07 — Drift guard, not a parallel list

`illustrations.py` gains `target_airline_names()`, derived from `_ILLUSTRATION_TARGETS`. `test_enrich.py` asserts every value of the prefix table is a member of it. That is the enforced mechanism behind the "must not drift out of sync" constraint: rename or drop an illustration target without mirroring it in the prefix table and the suite goes red. The table is not imported into `enrich.py` at runtime — `illustrations.py` pulls in Pillow, and the enrichment client stays free of that import.

## D-08 — No new fixtures are invented

Both adsbdb fixtures needed already exist and are real captures documented in `server/fixtures/README.md`: `adsbdb_hit_TVF16VB.json` (a real hit) and `adsbdb_miss_EJU84YF.json` (a real recorded 404 — and `EJU84YF` is both the callsign Phase 2 used for its live on-glass fallback QA **and** a prefix this table now resolves, making it the ideal before/after regression subject). `geofence_multi_aircraft.json`'s real winner is `TVF23WV`, a real Transavia record carrying a real-shaped `B738` type.

</design_decisions>

<source_coverage_audit>

| Source | Item | Covered by |
|---|---|---|
| TODO | Static ICAO-code → airline-name table, keyed on the callsign's first 3 letters | Task 1 (D-01) |
| TODO | Decouple `select_illustration()`'s airline input from a full adsbdb hit | Task 1 + Task 2 (D-03/D-05/D-06) |
| TODO | Fall back to prefix-derived airline instead of the generic `Route unavailable` state | Task 2 (D-06) |
| TODO | Show only destination/origin as genuinely unknown | Task 2 (D-06, line 1 unchanged) |
| TODO | Care around stale-brand names (Europe Airpost / Corsairfly) — real ICAO→current-resolved-name mapping | Task 1 (D-01 table sourced from resolved column; D-07 drift guard) |
| TODO | Decide the UI text for "airline known, destination unknown" | D-06 (locked above) |
| TODO | Not a Transavia-specific patch — all rotating-callsign carriers | Task 1 (23 prefixes, whole D-03 carrier set) |
| CONSTRAINT | Do NOT implement the AeroDataBox destination seed | `<objective>` out-of-scope clause; no schedule API touched |
| CONSTRAINT | Reuse illustration selection keys, no parallel list | Task 1 (D-07) |
| CONSTRAINT | Concrete render-state decision, not vague | D-06 table |
| CONSTRAINT | Suite + ruff stay green, regression coverage in existing harnesses, `check(name, fn)` style, real data preferred | Tasks 1-3 (D-08, all three harnesses, Task 3 gate) |
| NOTE | Airline identity is independent of any per-flight schedule lookup | D-04 (independent source, not a loosening) |

No unplanned items.

</source_coverage_audit>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Prefix-to-airline resolution in enrich.py, with a drift guard against the illustration keys</name>
  <files>server/plane/enrich.py, server/plane/illustrations.py, server/test_enrich.py, server/test_illustrations.py</files>
  <behavior>
    New checks in `server/test_enrich.py` (write them first; the module-level `EXPECTED_CHECK_COUNT` must end up equal to the real number of `check(...)` calls):
    - `airline_from_callsign("TVF16VB")` returns `"Transavia France"`.
    - `airline_from_callsign(" tvf16vb ")` returns the same string — normalisation goes through the existing `normalise_callsign()`.
    - `airline_from_callsign` returns `None` for an unknown prefix (`"ZZZ1234"`), for a bare 3-letter string with no flight suffix, for `""`, for `None`, for an int, and for a callsign containing a path separator — and raises for none of them.
    - `airline_only_route("Transavia France")` returns a dict whose key set is exactly the key set `_parse_route()` produces on the real `adsbdb_hit_TVF16VB.json` fixture, with `airline_name` set and the other four values `None`. `airline_only_route(None)` returns `None`.
    - `resolve_route("EJU84YF", {}, transport=<fake replaying the real adsbdb_miss_EJU84YF.json 404>)` returns a route whose `airline_name` is `"easyJet"` and a source of `"airline_only"`; a second call with the same cache returns the same route and the same source, and the fake transport records exactly one invocation (the miss is cached; the prefix resolution is recomputed from the static table, not re-queried).
    - `resolve_route("TVF16VB", {}, transport=<fake replaying adsbdb_hit_TVF16VB.json>)` returns the full route with source `"fresh_hit"`; a second call with the same cache returns source `"cache_hit"`.
    - `resolve_route` on a miss whose prefix is not in the table returns `(None, "miss")`.
    - Drift guard: every value of the prefix table is a member of `illustrations.target_airline_names()`.
    - Shape guard: every key of the prefix table is exactly three characters, all uppercase A-Z.
    New check in `server/test_illustrations.py`: `target_airline_names()` contains the resolved strings `"Europe Airpost"`, `"Corsairfly"` and `"CCM Airlines"`, and does not contain the current-brand labels those three replace.
  </behavior>
  <action>
Add to `server/plane/illustrations.py` a small public helper `target_airline_names()` returning the distinct `resolved_airline_name` values of `_ILLUSTRATION_TARGETS`, order-preserving and de-duplicated. It is derived from that list, never a second hardcoded list. Correct the module docstring's now-false claim that the confirmed-miss prefixes will always render the generic fallback: with this plan shipped, a confirmed route miss no longer implies a lost airline identity, and the docstring should point the reader at `enrich.airline_from_callsign()` for the prefix path while leaving the historical hit-rate measurements intact.

Add to `server/plane/enrich.py`:
  - `_ICAO_AIRLINE_PREFIXES`, the 23-entry static mapping from D-01's table. Copy each value verbatim from the resolved column of `03.1-LIVE-RESOLUTION.md`'s 24-airline table; annotate each row with its evidence token, and give the `EJU` row its own comment naming it as D-02's brand-level exception. State in a table-level comment that Amelia International and La Compagnie are deliberately absent because `03.1-LIVE-RESOLUTION.md` marks both unresolved, mirroring `_ILLUSTRATION_TARGETS`.
  - `airline_from_callsign(callsign)`: normalise via the existing `normalise_callsign()`, require the result to be alphanumeric-only, at least four characters, with its first three characters in A-Z, then return `_ICAO_AIRLINE_PREFIXES.get(prefix)`. Mirror `classify_aircraft_type()`'s security property explicitly in the docstring: the only strings this function can ever return are the fixed table values or `None`, never anything derived from its argument. Never raises. Pure, no I/O, no network.
  - `airline_only_route(airline_name)`: D-03's dict, the sole construction site for that shape; returns `None` for a falsy or non-string name.
  - `resolve_route(callsign, cache, transport=None, timeout=DEFAULT_TIMEOUT)`: D-05's seam. Compute `was_cached` from the normalised callsign before calling `lookup_route()`, delegate to `lookup_route()` unchanged, and classify: a route plus `was_cached` gives `"cache_hit"`, a route without it gives `"fresh_hit"`, and on `None` try `airline_from_callsign()` — a name gives `(airline_only_route(name), "airline_only")`, no name gives `(None, "miss")`. Never raises.

Leave `lookup_route()`, `_parse_route()`, `_cache_get()`, `_route_from_entry()`, `city_for_state()` and `trim_cache()` functionally untouched (D-04). Update the `enrich.py` module docstring to describe the two-source resolution the module now offers and to say plainly that the prefix source adds no network call and no cache entry of its own.

Write the harness checks before the implementation, following each harness's existing `check(name, fn)` runner style, its fixture-loading helper, and its `make_transport(...)` fake — no live network call anywhere, and no new fixture file (D-08).
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_enrich.py &amp;&amp; server/.venv/bin/python3 server/test_illustrations.py &amp;&amp; server/.venv/bin/python3 -c "from server.plane import enrich, illustrations; t=set(illustrations.target_airline_names()); assert set(enrich._ICAO_AIRLINE_PREFIXES.values()) &lt;= t; assert enrich.airline_from_callsign('TVF16VB')=='Transavia France'; assert enrich.airline_from_callsign('EJU84YF')=='easyJet'; assert enrich.airline_from_callsign('ZZZ1234') is None; print('OK')" &amp;&amp; ruff check .</automated>
  </verify>
  <done>Both harnesses exit 0 and print a passing `N/N` line whose N equals their own `EXPECTED_CHECK_COUNT`; the drift guard, the `TVF`/`EJU` resolutions and the unknown-prefix rejection all hold against the real modules; ruff is clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Wire the seam into the poll cycle and pin the intermediate caption state</name>
  <files>server/poll_loop.py, server/plane/render.py, server/test_render.py</files>
  <behavior>
    New checks in `server/test_render.py` (written first, `EXPECTED_CHECK_COUNT` updated to the real count), using the harness's existing `_TextSpy` and its established fixture-derived expectations:
    - Given the airline-only route for `"easyJet"` (built via `enrich.airline_only_route`) and a flight with callsign `EJU84YF` and no aircraft type, a departing `build_canvas` draws the bare callsign as line 1 and `easyJet` as line 2, and `ROUTE_FALLBACK_TEXT` appears among no text draw at all.
    - Given the airline-only route for `"Transavia France"` and a flight carrying `B738`, line 2 is `Transavia France · 737-800` — the same `{airline} · {label}` composition a full hit produces — while line 1 is still the bare callsign, with no `to`/`from` clause and no city.
    - `illustrations.select_illustration(enrich.airline_only_route("Transavia France"), "B738")` resolves to a path whose basename is `transavia-france.png` — the airline's own art, not the generic fallback. This is the check that proves the todo's actual goal.
  </behavior>
  <action>
In `server/poll_loop.py`, replace the inline `was_cached` computation, the `lookup_route()` call and the three-way `route_source` classification with a single call to `enrich.resolve_route(flight.get("callsign"), cache)` unpacked into `route, route_source`. Update the surrounding comment: the classification is now four categories, and the fourth means adsbdb had no route but the callsign's ICAO prefix identified the carrier. Everything else in that block — the `trim_cache` call, writing the cache back into `poll_state`, the `render_panel(...)` invocation, the persisted `last_route`/`previous_route` keys — stays exactly as it is. Confirm the log line's `route_source=%s` placeholder now carries the new token on the fallback path; no new field is added to the log line and nothing derived from the adsbdb response body is ever logged.

In `server/plane/render.py`:
  - Correct the docstrings that currently assert a half-resolved route never reaches the renderer. `_flight_line1_text()`'s docstring should describe D-06's middle row: a route may now legitimately arrive carrying an airline and no cities, in which case line 1 stays the bare callsign because the cities really are unknown. `_flight_line2_text()`'s docstring should say that its fallback text now fires only when neither enrichment source produced an airline. `build_canvas()`/`render_panel()`'s parameter docs should name both producers of the `route` argument.
  - Add a manual-QA-only CLI flag that previews D-06's middle row, alongside the existing route-suppressing flag, so Phase 6 can put this state on real glass. It builds both the main and the previous card's route through `enrich.airline_only_route(...)` using the module's existing sample airline names, and takes precedence over the route-suppressing flag when both are given. Document the precedence in the flag's own help text.
  - Make no change to `_flight_line1_text()`'s, `_flight_line2_text()`'s or `select_illustration()`'s selection logic (D-06): they already produce the specified behaviour and the new checks exist to prove it.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_render.py &amp;&amp; server/.venv/bin/python3 server/test_poll_loop.py &amp;&amp; server/.venv/bin/python3 server/test_pipeline_e2e.py &amp;&amp; test "$(grep -c 'enrich\.resolve_route(' server/poll_loop.py)" -ge 1 &amp;&amp; test "$(grep -c 'airline_only' server/poll_loop.py)" -ge 1 &amp;&amp; ruff check .</automated>
  </verify>
  <done>The render harness exits 0 with its updated `N/N` count including the three new checks; the poll-loop and end-to-end harnesses still exit 0 unchanged; `poll_loop.py` calls the new seam and carries the new source token; ruff is clean.</done>
</task>

<task type="auto">
  <name>Task 3: Reconcile the documents that describe the old behaviour, and gate the whole suite</name>
  <files>ARCHITECTURE.md, README.md, .planning/todos/pending/airline-name-from-callsign-prefix.md</files>
  <action>
In `ARCHITECTURE.md`, update the Enrichment paragraph and the ASCII data-flow diagram's enrichment line. The measured ~52.6% adsbdb hit rate is still true and stays; what changes is the consequence — a route miss no longer implies an unidentified airline, because the callsign's ICAO prefix resolves the carrier from a static in-repo table with no additional network call, and the caption falls all the way to its unavailable state only when both sources come up empty. Describe D-06's three-row outcome table in prose. Do not retro-edit the historical measurement or the note that the miss path is a designed first-class state — it still is; it just has one more rung above it now.

In `README.md`, recompute the stated total check count. Do not increment the number currently there: this branch is already stale on that line because the merged runway3 debug work added checks without updating it, so compute the real sum of every harness's `EXPECTED_CHECK_COUNT` and write that. Mention nothing else — this change adds no dependency, no data source and no attribution obligation, so the Data Sources section is untouched.

Move `.planning/todos/pending/airline-name-from-callsign-prefix.md` into `.planning/todos/done/` (creating that directory if it does not exist), leaving its content unedited — it is the record of what was asked for, and the summary is where the outcome is recorded. Leave `.planning/seeds/aerodatabox-destination-lookup-rotating-callsigns.md` exactly where it is; the destination half remains genuinely open.

Then run the full gate.
  </action>
  <verify>
    <automated>scripts/run-all-tests.sh &amp;&amp; ruff check . &amp;&amp; scripts/check-attribution.sh &amp;&amp; TOTAL=$(grep -h '^EXPECTED_CHECK_COUNT' server/test_*.py stub-server/test_*.py | awk '{s+=$3} END {print s}') &amp;&amp; test "$(grep -c "$TOTAL checks total" README.md)" -ge 1 &amp;&amp; test ! -e .planning/todos/pending/airline-name-from-callsign-prefix.md &amp;&amp; test -e .planning/todos/done/airline-name-from-callsign-prefix.md</automated>
  </verify>
  <done>All 9 harnesses pass under `scripts/run-all-tests.sh` with the coverage floor met, ruff and the attribution check are clean, README's stated total equals the harnesses' computed sum, and the todo has moved to done.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| ADS-B aggregator → `detect.py` → `enrich.py` | The `callsign` string is attacker-influenceable third-party input and is the sole input to the new resolution path |
| `enrich.py` → `illustrations.py` → filesystem | The resolved `airline_name` becomes a filesystem path component via `normalise_airline_key()` |
| `enrich.py` → `poll_loop.py` stdout | The new source token is written to the systemd journal |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-hyy-01 | Tampering | `enrich.airline_from_callsign()` → `illustrations.illustration_path_for_key()` | medium | mitigate | The function can only ever return a value taken from the fixed `_ICAO_AIRLINE_PREFIXES` table or `None` — never a value derived from its argument, exactly the property `classify_aircraft_type()` established under T-03.1-03-01. A hostile callsign therefore cannot reach path construction. Enforced by the alphanumeric/length/A-Z prefix gate before lookup, and by a harness check feeding it a path-separator payload. |
| T-hyy-02 | Denial of Service | `poll_loop.run_once()` enrichment block | medium | mitigate | `airline_from_callsign()`, `airline_only_route()` and `resolve_route()` all inherit the module's never-raises contract; a lookup problem must never abort a poll cycle. Pinned by the non-string/`None`/int/empty battery in Task 1's behaviour block. |
| T-hyy-03 | Spoofing | Displayed airline identity | low | mitigate | A wrong prefix would put a wrong carrier on the glass. Mitigated by sourcing every row from `03.1-LIVE-RESOLUTION.md`'s live-captured resolutions rather than model recall, and by excluding the two airlines that file marks unresolved. |
| T-hyy-04 | Information disclosure | journal log line | low | accept | The new `route_source` value is one of four fixed literal tokens; no callsign-derived or response-derived data is added to the log line, so T-02-04-05's original constraint is unchanged. |
| T-hyy-SC | Tampering | supply chain | n/a | accept | This plan installs no package from any package manager and adds no dependency — the prefix table is static in-repo data. No legitimacy gate applies. |
</threat_model>

<verification>
1. `scripts/run-all-tests.sh` — all 9 harnesses green, coverage floor met.
2. `ruff check .` — clean.
3. `scripts/check-attribution.sh` — clean (unchanged; no asset touched).
4. A real recorded adsbdb miss (`adsbdb_miss_EJU84YF.json`, a genuine 404) now yields an airline name and the airline's own illustration instead of the generic fallback — proven hermetically, without a network call.
5. A prefix-table value that no longer exists among the illustration targets fails the suite (drift guard).
6. `server/poll_loop.py` calls the new seam, so the production path — not just the unit tests — carries the fix.
</verification>

<success_criteria>
- On a rotating-callsign carrier's route miss, the panel shows the airline name and the airline's illustration; the destination is left honestly unknown, with line 1 the bare callsign.
- `Route unavailable` now appears only when both enrichment sources come up empty.
- adsbdb parsing, the hit/miss cache and its never-re-query behaviour are unchanged.
- Zero new network calls, dependencies or fixtures.
- Suite, ruff and attribution all green; README's check total matches reality.
- The AeroDataBox destination seed remains untouched and still deferred.
</success_criteria>

<output>
Create `.planning/quick/260827-hyy-resolve-airline-name-directly-from-the-a/260827-hyy-SUMMARY.md` when done.
</output>
