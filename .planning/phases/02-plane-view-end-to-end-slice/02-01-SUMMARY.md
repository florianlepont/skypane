---
phase: 02-plane-view-end-to-end-slice
plan: 01
subsystem: api
tags: [pillow, requests, ads-b, e-ink, python, protocol]

requires:
  - phase: 01-firmware-and-viability
    provides: adsb-test/query_aggregator.py's provider table + geofence filter pattern, adsb-test/runway3.json, stub-server/byos_server.py (vendored device protocol server), stub-server/make_test_panel.py's byte-packing contract
provides:
  - server/panel_format.py — shared 960,000-byte Spectra 6 wire format + Pillow palette bridge (WIDTH/HEIGHT/nibble codes, INDEX_TO_NIBBLE, new_canvas()/pack_panel())
  - server/plane/detect.py — requests-based aggregator client with the D-P2-01 deterministic multi-aircraft selection rule
  - server/plane/render.py — minimal Pillow "P"-mode poster renderer (empty/departing/arriving states, flight-number caption, bottom static tag)
  - server/poll_loop.py — systemd-timer oneshot entrypoint: detect -> render -> atomic panel.bin/poll_state.json swap
  - server/fixtures/ — six committed real-data fixtures (raw aggregator + adsbdb shapes) with full provenance
  - server/test_plane_detection.py, server/test_pipeline_e2e.py — green stdlib test harnesses
affects: [02-02-runway-config-inference, 02-03-silhouette, 02-04-enrichment-route, 02-05-deploy-hardware-verify]

tech-stack:
  added: [Pillow==12.3.0, requests==2.34.2]
  patterns:
    - "Draw directly on a Pillow \"P\"-mode canvas with integer palette-index fills - never RGB-compose-then-quantize"
    - "Atomic tmp-write-then-os.replace() for every served/persisted file (panel.bin, poll_state.json), mirroring byos_server.py's save_state()"
    - "Committed real-data fixtures (server/fixtures/) with a provenance README, since adsb-test/samples/ is gitignored"

key-files:
  created:
    - server/panel_format.py
    - server/plane/detect.py
    - server/plane/render.py
    - server/poll_loop.py
    - server/requirements.txt
    - server/fixtures/*.json
    - server/assets/fonts/Inter-Regular.ttf
    - server/assets/fonts/Inter-Bold.ttf
    - server/test_plane_detection.py
    - server/test_pipeline_e2e.py
  modified: []

key-decisions:
  - "D-P2-01 selection rule implemented exactly as specified: (effective_altitude_ft, seen_pos_or_infinity, hex) total order, proven deterministic under shuffled input"
  - "airplaneslive kept as primary aggregator provider (per Phase 1's validated result), adsbfi secondary"
  - "poll_loop.py hardcodes state=\"arriving\" for every detected flight - a deliberate, code-commented stub that 02-02 replaces with real D-03 inference"
  - "Deferred marking PLANE-01/02/03 complete in REQUIREMENTS.md - this slice only satisfies the detect->render->serve mechanics, not the full requirement text (airline/route enrichment is 02-04, real state inference is 02-02, hardware-verified legibility is 02-05)"

patterns-established:
  - "server/panel_format.py is the single source of truth for the wire format, deliberately duplicated (not imported) from stub-server/make_test_panel.py to avoid a backwards server/ -> stub-server/ dependency"
  - "Every ImageDraw fill argument is one of panel_format's IDX_* constants - never a bare integer palette index"

requirements-completed: []

coverage:
  - id: D1
    description: "D-P2-01 multi-aircraft selection rule (geofence filter + total order: lowest effective altitude, then seen_pos, then hex) proven deterministic against real captured multi-aircraft and on-ground snapshots"
    requirement: "PLANE-03"
    verification:
      - kind: unit
        ref: "server/test_plane_detection.py (6/6 checks)"
        status: pass
    human_judgment: false
  - id: D2
    description: "End-to-end pipeline: render -> atomic panel.bin swap -> byos_server.py setup/display/download protocol -> SHA-256 verify, plus D-04's unchanged-panel persistence when nothing is detected"
    requirement: "PLANE-03"
    verification:
      - kind: integration
        ref: "server/test_pipeline_e2e.py (5/5 checks)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Minimal poster renderer producing only the six legal Spectra 6 nibble codes across all three states (empty/departing/arriving), with White-on-Blue/Green foreground content per UI-SPEC Revision 2"
    verification:
      - kind: unit
        ref: "server/test_pipeline_e2e.py's legal-nibble check + manual --preview PNG inspection"
        status: pass
    human_judgment: true
    rationale: "02-UI-SPEC.md explicitly flags White-on-saturated-Blue/Green legibility as unverified on real Spectra 6 hardware (no anti-aliasing, no dithering) - only a physical-panel check in plan 02-05 can close this; rendered-byte correctness alone does not prove legibility."

duration: 14min
completed: 2026-08-09
status: complete
---

# Phase 2 Plan 1: Plane View End-to-End Slice Summary

**Real ADS-B detection on Orly runway 3 rendered as a legal 960,000-byte Spectra 6 panel and served through the unmodified Phase 1 device protocol, with a deterministic multi-aircraft tie-break rule and D-04 between-flights persistence.**

## Performance

- **Duration:** 14 min
- **Started:** 2026-08-09T06:58:00Z
- **Completed:** 2026-08-09T07:11:52Z
- **Tasks:** 3 completed
- **Files modified:** 21 created

## Accomplishments
- Ported `adsb-test/query_aggregator.py`'s aggregator client onto `requests`, adding the D-P2-01 deterministic multi-aircraft selection rule (lowest effective altitude -> freshest `seen_pos` -> lexicographic `hex`), proven stable under shuffled input ordering against a real captured two-aircraft-in-bbox snapshot
- Built `server/panel_format.py` as the single source of truth for the 960,000-byte Spectra 6 wire format and the Pillow palette bridge, shared by the renderer and (by convention, not import) `stub-server/make_test_panel.py`
- Implemented a minimal Pillow `"P"`-mode poster renderer (empty/departing/arriving states) that draws directly with integer palette-index fills, satisfying UI-SPEC's anti-aliasing-disabled rule by construction, plus a `draw_tracked_text()` helper for Label-role manual letter-spacing
- Wired `server/poll_loop.py` as the systemd-timer oneshot entrypoint: detect -> render -> atomic `panel.bin`/`poll_state.json` swap, with D-P2-02 cross-cycle state and D-04's "no detection, leave the panel untouched" persistence
- Proved the full chain end-to-end: a real aircraft record flows through detection, rendering, an atomic file swap, and the unmodified `stub-server/byos_server.py` protocol (setup -> bearer token -> display metadata -> download -> SHA-256 verify) with zero firmware changes
- Committed six real-data fixtures (extracted from Phase 1's gitignored raw samples) with full field-level provenance, and vendored Inter Regular/Bold with a VENDOR.md

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 — dependencies, committed real-data fixtures, vendored fonts, and two failing test harnesses** - `9cacc6c` (feat)
2. **Task 2: Detect the one aircraft using runway 3 right now (D-01, D-P2-01)** - `7e901e7` (feat)
3. **Task 3: Render the thinnest real poster and serve it through the real protocol (PLANE-03, D-04, D-P2-02)** - `9378bfa` (feat)

_Note: this plan's tasks carried `tdd="true"` attributes, but the project's own Wave 0 convention (02-VALIDATION.md) front-loads both test harnesses into Task 1 as a single RED commit rather than a per-task test/feat split; Task 2 and Task 3 each turned an already-existing, already-committed failing test green. See "Deviations from Plan" below._

## Files Created/Modified
- `server/panel_format.py` - Shared wire-format constants, Pillow palette bridge, `new_canvas()`/`pack_panel()`
- `server/plane/detect.py` - Aggregator client, geofence filter, D-P2-01 selection rule, live CLI
- `server/plane/render.py` - Empty/departing/arriving state rendering, tracked-text helper, `--preview` CLI
- `server/poll_loop.py` - Detect -> render -> atomic-swap oneshot entrypoint
- `server/requirements.txt`, `server/.gitignore`, `server/README.md` - Project skeleton
- `server/fixtures/*.json` + `server/fixtures/README.md` - Six committed real-data fixtures with provenance
- `server/assets/fonts/Inter-{Regular,Bold}.ttf` + `VENDOR.md` - Vendored Inter (SIL OFL 1.1)
- `server/test_plane_detection.py`, `server/test_pipeline_e2e.py` - Green stdlib test harnesses (6/6, 5/5)

## Decisions Made
- Kept the Task 1 Wave-0 pattern (both test harnesses written and committed together with fixtures/fonts/deps, before any implementation) rather than splitting each task's TDD RED/GREEN into separate commits — this follows 02-VALIDATION.md's explicit, plan-approved convention over the generic per-task TDD flow, since the validation strategy document was itself approved with this structure.
- `server/panel_format.py` duplicates (does not import) `stub-server/make_test_panel.py`'s constants, per 02-PATTERNS.md's explicit planner-discretion call — the `server/` -> `stub-server/` import direction would be backwards.
- Chose not to call `requirements.mark-complete` for PLANE-01/02/03 despite this plan's frontmatter listing all three IDs — see Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking issue] Fixed a module-resolution gap for direct script execution**
- **Found during:** Task 3 (writing `server/plane/render.py` and `server/poll_loop.py`)
- **Issue:** The plan's CLI usage examples run these files directly (`python3 server/plane/render.py ...`, `python3 server/poll_loop.py --once`). Under direct execution, Python puts only the script's own directory on `sys.path`, so the planned `from server import panel_format` / `import server.plane.detect` absolute imports would fail with `ModuleNotFoundError` even though the same imports work fine when the module is loaded as part of the `server` package (e.g. from the test harnesses, which already insert the repo root onto `sys.path`).
- **Fix:** Added a small `sys.path` bootstrap at the top of `render.py` and `poll_loop.py` that inserts the repo root (computed from `__file__`) before the `server.*` imports, so both direct script execution and package-style import work identically.
- **Files modified:** `server/plane/render.py`, `server/poll_loop.py`
- **Verification:** `server/.venv/bin/python3 server/plane/render.py --state arriving --callsign AF1380 --out /tmp/x.bin` and `server/.venv/bin/python3 server/poll_loop.py --once` both run correctly from a bare shell; test harnesses (which import the modules as a package) remain unaffected.
- **Committed in:** `9378bfa` (part of Task 3's commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking issue)
**Impact on plan:** Necessary for the plan's own documented CLI usage to actually work; no scope creep.

### Deliberate scope decision (not a Rule 1-3 auto-fix)

**Skipped `requirements.mark-complete` for PLANE-01/02/03.** This plan's frontmatter lists all three requirement IDs (they're the phase's requirements, distributed across all 5 plans), but PLANE-01/PLANE-02's actual text requires airline name and destination/origin — enrichment (`server/plane/enrich.py`) doesn't exist until plan 02-04, real D-03 departing/arriving inference doesn't exist until 02-02 (this plan hardcodes `"arriving"`), and 02-UI-SPEC.md's own White-on-saturated-colour legibility question is explicitly unverified until 02-05's hardware check. Checking these boxes now would make `.planning/REQUIREMENTS.md` state something not yet true. `REQUIREMENTS.md`'s traceability table is left at `Pending` for all three; the phase-closing plan (02-05) is the correct place to flip them.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required this plan (Hetzner VPS provisioning is deferred to plan 02-05 per 02-CONTEXT.md).

## Next Phase Readiness
- `server/plane/detect.py`'s `select_runway3_aircraft()` and `server/panel_format.py`'s palette bridge are stable APIs plan 02-02 (D-03 inference) and 02-03 (silhouette) build directly on top of.
- `server/plane/render.py` reserves vertical space (via `FLIGHT_NUMBER_TOP_Y`'s zone-stacking constants) for the state label (zone 1) and silhouette (zone 3) so 02-02/02-03 can fill them in without moving the flight-number caption or bottom tag this plan already renders.
- `server/poll_loop.py`'s hardcoded `state="arriving"` is clearly marked in both `render.py`'s docstring and `poll_loop.py`'s inline comment as the exact line 02-02 replaces.
- No blockers. `server/test_plane_detection.py`, `server/test_pipeline_e2e.py`, and `stub-server/test_poll_cycle.py` are all green with no regressions.

---
*Phase: 02-plane-view-end-to-end-slice*
*Completed: 2026-08-09*

## Self-Check: PASSED

All 10 created files verified present on disk; all 3 task commits (`9cacc6c`, `7e901e7`, `9378bfa`) verified present in git history.
