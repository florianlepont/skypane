---
phase: 03-visual-polish-on-real-glass
plan: 03
subsystem: testing
tags: [pillow, provenance, sha256, contract-testing, e-ink]

# Dependency graph
requires:
  - phase: 03-visual-polish-on-real-glass
    provides: "server/plane/illustrations.py and the vendored 8-file illustration set, both shipped in prior-session commits 21c4ed6/0e4e0ca/e52602e"
provides:
  - "server/test_illustrations.py - a 22-check stdlib contract harness for normalise_airline_key(), select_illustration() and validate_illustration_file(), run against the real vendored files"
  - "server/assets/icons/illustrations/VENDOR.md - per-file sha256/dimensions/airline/aircraft-type provenance table plus the D-09 licensing rationale"
affects: [03-04-hardware-calibration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Malformed-fixture generation in a temp dir for a validator harness (non-PNG via mismatched extension+format, no-alpha, fully-opaque-alpha, narrow-width, portrait, oversized-pixel-count-via-monkeypatched-cap) rather than committing broken binaries - mirrors server/test_dither.py's check()/EXPECTED_CHECK_COUNT convention"

key-files:
  created:
    - server/test_illustrations.py
    - server/assets/icons/illustrations/VENDOR.md
  modified: []

key-decisions:
  - "This session executes NOTHING from 03-03-PLAN.md's Task 3 (dithered compositing, mirroring, spatially-scoped palette exception) - that work is not pending, it was superseded by a later, independently-shipped two-flight poster redesign (commit f8db99a, D-21/D-24/D-25/D-26/D-27) that already has server/plane/render.py and server/test_render.py at 26/26 passing. Touching either file was explicitly out of scope and neither was touched (confirmed via git status and a final test_render.py re-run)."
  - "test_illustrations.py's oversized-pixel-count check monkeypatches ILLUSTRATION_MAX_PIXELS down to 1,000,000 for the duration of one check (restored in a finally block) rather than generating a real ~40M-pixel PNG fixture, to keep the harness fast while still exercising the exact header-read-before-decode code path"
  - "VENDOR.md's per-file digests were computed directly against the files already vendored in server/assets/icons/illustrations/ (shasum -a 256, verified independently of the module's own --validate pass) - this session did not generate, regenerate, or modify any .png in that directory"

patterns-established: []

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "server/test_illustrations.py exists and exercises every bullet in 03-03-PLAN.md Task 1's <behavior> block (normalise_airline_key, select_illustration, validate_illustration_file) against the real vendored illustration set"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_illustrations.py - 22/22 checks pass"
        status: pass
    human_judgment: false
  - id: D2
    description: "server/assets/icons/illustrations/VENDOR.md exists with a per-file sha256/dimensions/airline/aircraft-type table for all 8 vendored PNGs and the D-09 AI-generated-art licensing rationale"
    requirement: "PLANE-02"
    verification:
      - kind: manual_procedural
        ref: "server/assets/icons/illustrations/VENDOR.md reviewed directly against shasum -a 256 output and Pillow-reported dimensions for all 8 files; sha256 values cross-checked in this session's own tool output"
        status: pass
    human_judgment: false

# Metrics
duration: 25min
completed: 2026-08-26
status: complete
---

# Phase 3 Plan 3: Illustration Test Harness + Provenance Record Summary

**Closed the two documentation/testing gaps left open in an already-substantially-shipped plan: a 22-check test_illustrations.py contract harness and a per-file sha256 provenance VENDOR.md for the 8 vendored aircraft illustrations — no illustration-selection logic, render code, or asset files were touched.**

## Performance

- **Duration:** ~25 min
- **Tasks:** 2 (both gap-closure only; Task 3 of the original plan is out of scope, see Deviations)
- **Files modified:** 2 created, 0 modified

## Accomplishments

- `server/test_illustrations.py` created: 22-check stdlib harness (no pytest, matches `server/test_dither.py`'s `check()`/`EXPECTED_CHECK_COUNT` convention) covering `normalise_airline_key()` (Air Algérie/CCM Airlines slugging, `""`/`None`/`42` → `None`), `select_illustration()` (real Air France and Vueling paths resolve correctly; unknown airline, `None` route, missing `airline_name`, non-string `airline_name` all fall back to the generic fallback path; never raises across 8 malformed inputs; returns `None` only when even the fallback file is absent — proven by monkeypatching `ILLUSTRATION_DIR` to an empty temp dir), `illustration_path_for_key()`'s path-separator rejection, and `validate_illustration_file()`'s six distinct rejection categories (non-PNG, no alpha, fully-opaque alpha, below-minimum width, portrait, oversized pixel count) built as programmatic temp-dir fixtures rather than committed broken binaries.
- `server/assets/icons/illustrations/VENDOR.md` created: per-file sha256 digest, pixel dimensions, airline served, and aircraft type for all 8 vendored PNGs (`air-france.png` through `transavia-france.png` plus `generic-fallback.png`), the D-09 AI-generated-art licensing rationale, the nose-left orientation convention and how it was verified, and a cross-reference to the D-23 no-text waiver / D-24 mirroring-dropped interaction already recorded in `03-03-PLAN.md`'s Reconciliation Note.
- Confirmed both hard-constraint smoke tests exit 0: `server/plane/illustrations.py --validate` (all 8 files PASS) and the new `server/test_illustrations.py` (22/22).
- Confirmed `server/plane/render.py` and `server/test_render.py` remain completely untouched (`git status` shows no changes to either; `server/test_render.py` re-run independently at the end of this session still passes 26/26).

## Task Commits

This session performed one atomic commit covering both new artifacts (they are tightly coupled — the VENDOR.md digests were computed against files the test harness also asserts against):

1. **Close 03-03 Task 1/Task 2 gaps** - `0fd8da8` (test) - `server/test_illustrations.py`, `server/assets/icons/illustrations/VENDOR.md`

No separate plan-metadata commit was made in this response; the orchestrator handles STATE.md/ROADMAP.md/REQUIREMENTS.md updates and the final docs commit per its own protocol.

## Files Created/Modified

- `server/test_illustrations.py` - new 22-check contract harness for `server/plane/illustrations.py`
- `server/assets/icons/illustrations/VENDOR.md` - new per-file provenance record (sha256, dimensions, airline, aircraft type, licensing rationale)

## Decisions Made

- Scoped this session strictly to the two gaps named in 03-03-PLAN.md's Reconciliation Note. Did not attempt Task 3 (dithered compositing, state mirroring, spatially-scoped palette exception) as literally written — that design was abandoned mid-session in a prior execution and replaced by the shipped two-flight poster layout (`_resize_illustration()` + `draw_illustration()` in `render.py`, commit `f8db99a`), which is already tested at 26/26 in `server/test_render.py`. Re-implementing the superseded design would have reverted real, shipped, tested work.
- Test fixtures for `validate_illustration_file()`'s rejection paths are built programmatically at runtime in a `tempfile.mkdtemp()` directory and cleaned up in a `finally` block, rather than committing static broken-binary fixtures to the repo — consistent with `server/test_dither.py`'s and `server/test_poll_loop.py`'s existing conventions of building synthetic image fixtures inline.
- Where real vendored files were sufficient to exercise a check meaningfully (e.g. `select_illustration({"airline_name": "Air France"})` resolving the real `air-france.png`), the harness tests against those real files instead of a synthetic stand-in, per this session's explicit scope instruction.

## Deviations from Plan

None in the Rule 1-4 sense — this session's scope was pre-narrowed by the orchestrator to exactly the two artifacts named in the Reconciliation Note, and both were delivered as specified. The larger deviation from the *original* 03-03-PLAN.md (Task 3 being superseded rather than executed) was a prior-session decision already fully documented in the plan's own Reconciliation Note and is not re-litigated or re-applied here; this session's job was narrowly to close the two named documentation/testing gaps, which it did.

## Issues Encountered

None. `server/plane/illustrations.py --validate` passed against the real vendored set on the first run, so no asset regeneration or fix was needed before writing the provenance record.

## User Setup Required

None - no external service configuration required. The illustration files were already hand-supplied and validated in a prior session (Task 2's blocking checkpoint, already resolved).

## Next Phase Readiness

- 03-03's two previously-open gaps (test harness, provenance record) are closed; `server/plane/illustrations.py` now has full test coverage matching its own `<behavior>` contract.
- `server/plane/render.py`/`server/test_render.py` (the actual compositing pipeline, shipped under the superseding two-flight design) remain untouched and still pass 26/26 - no regression risk introduced by this session.
- Phase 3's remaining work is 03-04 (hardware calibration pass) per `.planning/STATE.md`.

---
*Phase: 03-visual-polish-on-real-glass*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: server/test_illustrations.py
- FOUND: server/assets/icons/illustrations/VENDOR.md
- FOUND: .planning/phases/03-visual-polish-on-real-glass/03-03-SUMMARY.md
- FOUND commit: 0fd8da8
- Confirmed via `git status --short` that server/plane/render.py, server/test_render.py, server/plane/dither.py, server/poll_loop.py, server/panel_format.py all show zero changes
