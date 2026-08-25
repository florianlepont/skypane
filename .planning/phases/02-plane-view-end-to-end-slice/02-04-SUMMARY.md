---
phase: 02-plane-view-end-to-end-slice
plan: 04
subsystem: api
tags: [python, adsbdb, requests, pillow, enrichment, cache]

requires:
  - phase: 02-plane-view-end-to-end-slice
    plan: 03
    provides: server/plane/render.py's build_canvas()/render_panel(), STATE_BACKGROUND/STATE_INK, draw_silhouette()/draw_state_label(), FLIGHT_NUMBER_TOP_Y zone stacking, and server/poll_loop.py's run_once()/load_poll_state()/save_poll_state() atomic-write plumbing
provides:
  - server/plane/enrich.py - adsbdb.com callsign->route enrichment client (D-02, D-P2-05): normalise_callsign(), lookup_route() with a persistent JSON-serialisable hit/miss cache, city_for_state(), to_sentence_case_city(), trim_cache()
  - server/poll_loop.py's run_once() wired to enrich.lookup_route(), persisting the cache in poll_state.json's enrichment_cache field across the systemd-oneshot process boundary, logging cache_hit/fresh_hit/miss (never the raw response body)
  - server/plane/render.py's draw_route_line()/draw_airline_line() (UI-SPEC zones 7/9) and fit_text_size() overflow shrinking, with build_canvas()/render_panel() gaining a route= keyword argument and the CLI gaining --no-route
affects: [02-05-deploy-hardware-verify]

tech-stack:
  added: []
  patterns:
    - "Airline-line top Y computed from fixed font-metric constants only (_route_line_reserved_height(), a pure function of LABEL_FONT/BODY_FONT sizes), never from a rendered route line's measured bbox - guarantees the enrichment-miss fallback caption lands at the exact same absolute position as a resolved-route render's airline line, with no doubled gap"
    - "Cache stores both hits and misses as {'found': bool, ...} JSON-serialisable records so a rotating low-cost callsign that will always miss is never re-queried against an undocumented rate limit"
    - "route_source three-way classification (cache_hit / fresh_hit / miss) logged per poll cycle - callsign + outcome only, never the raw adsbdb response body (T-02-04-05)"

key-files:
  created:
    - server/plane/enrich.py
  modified:
    - server/poll_loop.py
    - server/plane/render.py

key-decisions:
  - "Wired render.py's zones 7/9 support (draw_route_line/draw_airline_line, the route= kwarg on build_canvas/render_panel) inside this same session even though Task 2's own <files> list only named enrich.py/poll_loop.py - Task 2's own wiring (poll_loop.py passing route= into render.render_panel()) is inert without render.py accepting that kwarg, and Task 2's automated verify block runs test_pipeline_e2e.py, which exercises that exact call path. Commits still stayed atomic per task: Task 2's commit touches only enrich.py/poll_loop.py, Task 3's commit touches only render.py."
  - "Fixed a route_source labelling bug discovered while manually verifying the cache-persistence acceptance criterion: the original poll_loop.py classified any cached callsign as 'cache_hit', including a cached *miss* (route=None). Reclassified to three mutually exclusive categories - cache_hit (cached AND resolved), fresh_hit (freshly queried AND resolved), miss (route is None, whether cached or fresh) - matching the plan's exact wording ('cache hit, a fresh hit, or a miss')."
  - "Deferred requirements.mark-complete for PLANE-01/PLANE-02, continuing the pattern established in 02-01/02-02/02-03's summaries: this plan closes the informational gap (airline + destination/origin now render), but 02-05's hardware-verified White-on-saturated-Blue/Green legibility QA checkpoint is still outstanding before the requirement text is fully true on real glass."

patterns-established:
  - "fit_text_size(font_path, initial_size, text, max_width, min_size=MIN_CAPTION_FONT_SIZE, tracking=0) as the one shared overflow-shrink helper - steps a font down in small increments until text fits, floored at a named constant, never clips/wraps/overflows the safe box"

requirements-completed: []

coverage:
  - id: D1
    description: "server/plane/enrich.py resolves airline name + origin/destination city+IATA from a real callsign via api.adsbdb.com, with a persistent JSON-serialisable hit/miss cache (never re-queries a cached callsign) and a graceful None on every failure mode (404, 5xx, connection error, non-JSON body, structurally incomplete 200)"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_enrich.py (16/16 checks: real recorded hit/miss fixtures, hostile responses, cache hit/miss persistence, callsign normalisation, sentence-case city conversion, T-02-04-02 unsafe-callsign rejection, city_for_state())"
        status: pass
      - kind: manual_procedural
        ref: "live single lookup: TVF16VB -> {'airline_name': 'Transavia France', 'origin_iata': 'ORY', 'origin_city': 'Paris', 'destination_iata': 'PMI', 'destination_city': 'Palma de Mallorca'}; EJU84YF -> None"
        status: pass
    human_judgment: false
  - id: D2
    description: "poll_loop.py's run_once() persists the enrichment cache in poll_state.json's enrichment_cache field across process invocations - a callsign detected on two consecutive run_once() calls triggers exactly one outbound adsbdb request"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: manual_procedural
        ref: "two run_once() calls against the same injected multi-aircraft fixture with a spied default_transport: 1 outbound call recorded, poll_state.json's enrichment_cache holds exactly 1 entry, second call logged route_source=cache_hit"
        status: pass
      - kind: e2e
        ref: "server/test_pipeline_e2e.py (5/5 checks - run_once() through the real byos_server.py device protocol, now exercising the live enrichment call path)"
        status: pass
    human_judgment: false
  - id: D3
    description: "server/plane/render.py renders UI-SPEC zones 7 (route line: TO/FROM prefix + sentence-case city) and 9 (airline line) for a resolved route, and the exact 'Route unavailable' fallback - at the identical airline-line y-offset as the resolved-route case, no doubled gap - on an enrichment miss; overflowing city/airline names shrink to fit rather than clip"
    requirement: "PLANE-01, PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py (25/25 checks, raised from 19 - route/airline line content, TO/FROM prefix, fallback text and position parity, silhouette/label/flight-number persistence on a miss, two-palette-index guard on both branches)"
        status: pass
      - kind: manual_procedural
        ref: "two rendered/eyeballed preview PNGs (--state arriving with a resolved route, --state departing --no-route) plus a 50+ character synthetic city/airline name confirmed to shrink within the 1072x1472 safe box without clipping"
        status: pass
    human_judgment: true
    rationale: "White-on-saturated-Blue/Green legibility of the shrunk overflow text and the visual balance of the route/airline caption block remain unverified on real Spectra 6 hardware - carried forward to 02-05's hardware QA checkpoint alongside the phase's other outstanding hardware-legibility items."

duration: 45min
completed: 2026-08-11
status: complete
---

# Phase 2 Plan 4: Route and Airline Enrichment Summary

**adsbdb.com callsign-to-route enrichment client with a persistent poll_state.json cache, wired into poll_loop.py and rendered as UI-SPEC's route/airline caption lines with a fallback layout that never doubles up a gap on a miss.**

## Performance

- **Duration:** ~45 min (resumed session - a prior executor run was interrupted mid-Task-2 by a provider session-limit error; this session picked up from the already-committed Task 1 and an uncommitted, correctly-implemented `server/plane/enrich.py` work-in-progress)
- **Tasks:** 3 (Task 1 already committed by the interrupted prior session)
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments
- Verified the interrupted session's uncommitted `server/plane/enrich.py` against `server/test_enrich.py`'s full 16-check contract (real recorded hit/miss fixtures, hostile-response handling, cache hit/miss persistence, callsign normalisation, sentence-case city conversion, T-02-04-02's unsafe-callsign URL-injection guard, `city_for_state()`) - it passed 16/16 with no changes needed, confirming it correctly implemented D-02/D-P2-05
- Wired `enrich.lookup_route()` into `poll_loop.py`'s `run_once()`, persisting the callsign-keyed hit/miss cache in `poll_state.json`'s new `enrichment_cache` field across the systemd-oneshot process boundary (D-P2-02), with `route_source` logging (`cache_hit`/`fresh_hit`/`miss`) that never logs the raw adsbdb response body (T-02-04-05)
- Live-verified this session's real-world adsbdb coverage snapshot: `TVF16VB` resolves (Transavia France, ORY -> PMI, sentence-cased to "Palma de Mallorca"), `EJU84YF` returns `None` (a real 404) - both outcomes match N-02-04-01's 52.6% hit-rate figure
- Implemented `server/plane/render.py`'s zones 7 (route line: uppercase tracked TO/FROM prefix + sentence-case city, centred as one composite line) and 9 (airline line, or the exact "Route unavailable" fallback), with the airline line's Y position computed from fixed font-metric constants only - never from a rendered route line's bbox - so the fallback sits at exactly the same absolute position as the resolved-route case, with no doubled gap
- Added `fit_text_size()` as the shared overflow-shrink helper, floored at `MIN_CAPTION_FONT_SIZE` (28pt), and confirmed a synthetic 50+ character city/airline name shrinks to fit the 1072x1472 safe box without clipping
- Rendered and eyeballed two preview PNGs (`--state arriving` with a resolved route showing "FROM Paris" / "Air France"; `--state departing --no-route` showing "Route unavailable" with no visible gap above it) against UI-SPEC zones 5-9

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 - failing enrichment harness driven by a real hit and a real recorded miss** - `b14bf05` (test) - committed by the interrupted prior session
2. **Task 2: adsbdb enrichment client with a persistent callsign cache and a graceful miss path (D-02, D-P2-05)** - `2efb7d4` (feat)
3. **Task 3: Render the route line and airline line, with the exact UI-SPEC fallback layout** - `051b786` (feat)

## Files Created/Modified
- `server/plane/enrich.py` - `ADSBDB_URL`, `USER_AGENT`, `DEFAULT_TIMEOUT`, `CACHE_MAX_ENTRIES`, `normalise_callsign()`, `lookup_route()`, `city_for_state()`, `to_sentence_case_city()`, `default_transport()`, `trim_cache()`
- `server/poll_loop.py` - `run_once()` now resolves the enrichment cache from `poll_state.json`, calls `enrich.lookup_route()`, passes `route=` into `render.render_panel()`, persists the trimmed cache back, and logs `route_source`
- `server/plane/render.py` - `ROUTE_PREFIX_DEPARTING`, `ROUTE_PREFIX_ARRIVING`, `ROUTE_FALLBACK_TEXT`, `MIN_CAPTION_FONT_SIZE`, `draw_route_line()`, `draw_airline_line()`, `fit_text_size()`, `_route_line_reserved_height()`; `build_canvas()`/`render_panel()` gain a `route=` keyword argument; CLI gains `--no-route`

## Decisions Made
- Implemented render.py's Task 3 zones-7/9 support within this same session before formally committing Task 2, since Task 2's own poll_loop.py wiring (passing `route=` into `render.render_panel()`) is inert without render.py accepting that kwarg, and Task 2's automated verify block runs `test_pipeline_e2e.py`, which exercises that exact call path end-to-end. Commit granularity still matches the plan exactly: the Task 2 commit (`2efb7d4`) touches only `enrich.py`/`poll_loop.py`; the Task 3 commit (`051b786`) touches only `render.py`.
- Airline line's Y position is a pure function of `LABEL_FONT`/`BODY_FONT` metrics (`_route_line_reserved_height()`), computed identically whether or not the route line actually draws - this is what makes "positioned where the airline line normally sits, not one gap lower" (UI-SPEC's Copywriting Contract) an invariant rather than something that could drift between the hit and miss code paths.
- Continued the pattern from 02-01/02-02/02-03's summaries of deferring `requirements.mark-complete` for PLANE-01/PLANE-02: this plan closes the informational gap (airline + destination/origin now render on the poster), but 02-05's hardware-verified legibility QA checkpoint is still outstanding.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a route_source log-classification bug in poll_loop.py**
- **Found during:** Task 2 (manually verifying the "second run_once() call performs no outbound enrichment request" acceptance criterion)
- **Issue:** The original classification logic labelled any cached callsign as `route_source="cache_hit"`, including a cached **miss** (`route=None`) - so a rotating low-cost callsign that had already 404'd would be logged as a "cache hit" on its second poll cycle, which is misleading (it correctly avoided a re-query, but it did not resolve a route).
- **Fix:** Reclassified to three mutually exclusive categories matching the plan's exact wording ("cache hit, a fresh hit, or a miss"): `cache_hit` only when the callsign was cached *and* resolved a route; `fresh_hit` when freshly queried *and* resolved; `miss` whenever `route is None`, regardless of whether the miss itself was cached or fresh.
- **Files modified:** `server/poll_loop.py`
- **Verification:** Manually re-ran two `run_once()` calls against a callsign with a real resolved route (`TVF16VB`) with a spied transport - first call logged `route_source=fresh_hit`, second logged `route_source=cache_hit`, exactly 1 outbound transport call recorded across both. All five `server/test_*.py` harnesses and `stub-server/test_poll_cycle.py` remain green.
- **Committed in:** `2efb7d4` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 logging-classification bug)
**Impact on plan:** The fix corrects diagnostic logging only - no change to cache behaviour, rendered output, or any test-asserted contract. No scope creep.

## Issues Encountered
- `server/test_pipeline_e2e.py` (an existing harness from 02-01, unmodified by this plan) now makes a genuine live outbound call to `api.adsbdb.com` as a side effect of exercising `poll_loop.run_once()`'s new enrichment path - its injected aircraft fixture (`TVF23WV`) happened to be a real adsbdb miss in this session's live run, which the test tolerates correctly (a miss still renders and packs a valid panel). This introduces a new external-network dependency to what was previously a fully fixture-driven end-to-end test; flagged here for visibility rather than fixed, since modifying `test_pipeline_e2e.py` itself was out of scope for both of this plan's tasks (`<files>` didn't list it), and the plan's own verification strategy leans on live-verified adsbdb behaviour throughout this phase (N-02-04-01).
- The interrupted prior session's `server/plane/enrich.py` needed no corrections at all - a genuinely useful confirmation that Rule-1/2/3-style "verify before trusting" caution paid off without costing rework this time.

## User Setup Required
None - adsbdb.com requires no API key or account (free, unauthenticated service).

## Next Phase Readiness
- PLANE-01/PLANE-02 are now informationally complete end-to-end: flight number (02-01/02-02), silhouette + state colour/label (02-02/02-03), and airline + destination/origin (this plan) all render together from a single poll cycle, with a designed-not-bolted-on fallback for the common (52.6%) adsbdb-miss case.
- All five `server/test_*.py` harnesses (6+14+16+25+5 = 66 checks) and `stub-server/test_poll_cycle.py` (15/15) are green with no regressions.
- Carried forward to 02-05's hardware QA checklist (alongside A-02-02-01's departure-side deadband and 02-03's silhouette-legibility items): confirm on real Spectra 6 glass that (1) the route/airline caption block reads clearly at viewing distance under White-on-saturated-Blue/Green, (2) `fit_text_size()`'s shrunk-overflow text stays legible rather than merely fitting the safe box, and (3) deliberately trigger a real adsbdb miss on real traffic to observe the "Route unavailable" fallback on real glass, per N-02-04-01's explicit warning that a QA pass showing only Air France/Iberia-class flights has not exercised this feature.
- No blockers.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: 2026-08-11*

## Self-Check: PASSED

All 3 modified/created files verified present on disk (`server/plane/enrich.py`, `server/poll_loop.py`, `server/plane/render.py`); all 3 commits (`b14bf05`, `2efb7d4`, `051b786`) verified present in git history. Independently re-ran all five `server/test_*.py` harnesses (6+5+14+25+16 = 66/66 checks) plus `stub-server/test_poll_cycle.py` (15/15) after this executor session was interrupted by a provider session-limit error immediately before this file's commit — all green, no regressions. (Self-check performed by the orchestrator closing out an interrupted executor run per the safe-resume recovery path — the executor itself never reached this step.)
