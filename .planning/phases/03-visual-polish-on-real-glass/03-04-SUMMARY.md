---
phase: 03-visual-polish-on-real-glass
plan: 04
subsystem: rendering
tags: [pillow, error-handling, defense-in-depth, e-ink, illustrations]

# Dependency graph
requires:
  - phase: 03-visual-polish-on-real-glass
    provides: "03-03's two-flight poster composition (_build_active_canvas, D-25/D-26) and 03-VERIFICATION.md's gap findings"
provides:
  - "_illustration_over_pixel_cap(path) - header-only oversized-PNG rejection in the render path"
  - "_load_illustration_safely(path, target_w) - never-raises illustration loader with a candidate degradation ladder (path -> generic fallback -> None)"
  - "Both _build_active_canvas() illustration call sites wired through the guarded loader"
affects: [06-final-on-glass-verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Header-first Pillow guard (Image.open().size before .convert()/.load()) reused from illustrations.validate_illustration_file() rather than redefining a cap"
    - "Candidate-ladder degradation (real path -> generic_fallback_path() -> None) with a stderr diagnostic per skipped candidate"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/test_render.py

key-decisions:
  - "Reused illustrations.ILLUSTRATION_MAX_PIXELS and illustrations.generic_fallback_path() rather than restating the constant or duplicating the fallback path, so the render path and the offline --validate CLI can never drift apart"
  - "Diagnostics for a skipped candidate go to sys.stderr only (one line per candidate, path + reason), matching poll_loop.py's existing failure-logging discipline - accepted as low-severity information disclosure (T-03-04-03) since no image bytes or secrets are printed"

patterns-established:
  - "Never-raises Pillow loader pattern: header-check first (lazy Image.open().size), then decode inside try/except, exhausting a fixed candidate ladder before returning None"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "A corrupt (byte-garbage) illustration file degrades to generic-fallback.png instead of raising out of render_panel()"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py#a corrupt (byte-garbage) illustration file degrades to the generic fallback instead of raising out of render_panel()"
        status: pass
    human_judgment: false
  - id: D2
    description: "An oversized (valid, decodable) illustration is rejected on its PNG header before any pixel data is decoded"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py#an oversized illustration is rejected on its PNG header, before any pixel data is decoded"
        status: pass
    human_judgment: false
  - id: D3
    description: "When both the selected illustration and the generic fallback are undecodable, the render skips the illustration entirely and still returns a valid 960,000-byte panel"
    verification:
      - kind: unit
        ref: "server/test_render.py#when the selected illustration and the generic fallback are both undecodable, the render skips the illustration and still returns a valid panel"
        status: pass
    human_judgment: false
  - id: D4
    description: "Full 9-harness suite, illustrations.py's own 42/42 checks, and ruff stay green - no regression to the seven already-verified Phase 3 must-haves"
    verification:
      - kind: unit
        ref: "bash scripts/run-all-tests.sh"
        status: pass
    human_judgment: false

# Metrics
duration: ~20min
completed: 2026-08-27
status: complete
---

# Phase 03 Plan 04: Guard the render path against a corrupt or oversized illustration Summary

**Closed 03-VERIFICATION.md's single Phase 3 gap: `render.py` now has a never-raises `_load_illustration_safely()` loader (header-only pixel cap + generic-fallback degradation) wired into both D-25/D-26 illustration call sites, so a corrupt or oversized vendored PNG degrades to `generic-fallback.png` instead of crashing `render_panel()` and freezing every subsequent poll cycle.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 2
- **Files modified:** 2 (`server/plane/render.py`, `server/test_render.py`)

## Accomplishments

- Added `_illustration_over_pixel_cap(path)` - reads only the PNG header (`Image.open().size`, no decode) and rejects anything over `illustrations.ILLUSTRATION_MAX_PIXELS` (40M pixels), reusing the shared constant rather than restating it
- Added `_load_illustration_safely(path, target_w)` - a never-raises loader that tries `path`, then `illustrations.generic_fallback_path()`, then gives up and returns `None`, printing one diagnostic line per skipped candidate to `sys.stderr`
- Rewired both illustration call sites in `_build_active_canvas()` (main card and previous card) through the guarded loader; `_build_active_canvas()`'s own source now contains zero direct `_resize_illustration` calls
- Added three regression checks (36-38) to `server/test_render.py` that feed a real byte-garbage `.png` and a real, genuinely-decodable oversized PNG through the actual `render_panel()` code path

## Task Commits

Each task was committed atomically:

1. **Task 1: Regression checks (RED)** - `96e4a4d` (test) - added checks 36-38, `_write_garbage_png()`/`_write_oversized_png()` fixtures, `_forced_illustration()` context manager; raised `EXPECTED_CHECK_COUNT` 35 -> 38
2. **Task 2: Guard the live render path (GREEN)** - `4efbe5e` (fix) - `_illustration_over_pixel_cap()`, `_load_illustration_safely()`, both call sites rewired

**Plan metadata:** committed separately after this summary (docs: complete plan)

## RED Evidence (Task 1, against the pre-fix render.py)

```
FAIL a corrupt (byte-garbage) illustration file degrades to the generic fallback instead of raising out of render_panel() - exception: UnidentifiedImageError("cannot identify image file '/var/folders/.../tmpnjqcp8mi.png'")
FAIL an oversized illustration is rejected on its PNG header, before any pixel data is decoded - an oversized illustration file did not degrade to a byte-identical generic-fallback panel
FAIL when the selected illustration and the generic fallback are both undecodable, the render skips the illustration and still returns a valid panel - exception: UnidentifiedImageError("cannot identify image file '/var/folders/.../tmpqhcj48t_.png'")
render: 35/38 checks pass
```

Exactly 3 `FAIL` / 35 `PASS`, as required - two failures surface the exact `PIL.UnidentifiedImageError` class 03-VERIFICATION.md reproduced live; the third (oversized) fails as a byte mismatch, proving a bare try/except could not have satisfied it.

## GREEN Evidence (Task 2, after the fix)

```
render: 38/38 checks pass
```

## Live Repro Confirmation

The exact repro shape from 03-VERIFICATION.md's Behavioral Spot-Checks (a byte-garbage `.png` forced through `select_illustration()`) now degrades instead of crashing:

```
render: skipping illustration /var/folders/.../tmpy_zcw_r9.png - header unreadable (UnidentifiedImageError)
960000
```

`render_panel()` returns exactly `960000` bytes and prints exactly one illustration-related diagnostic line to stderr - both required by the plan's acceptance criteria.

## Files Created/Modified

- `server/plane/render.py` - added `_illustration_over_pixel_cap()` and `_load_illustration_safely()`; rewired both `_build_active_canvas()` illustration call sites
- `server/test_render.py` - added `_write_garbage_png()`, `_write_oversized_png()`, `_forced_illustration()`, and checks 36-38; `EXPECTED_CHECK_COUNT` 35 -> 38

## Decisions Made

- Reused `illustrations.ILLUSTRATION_MAX_PIXELS` and `illustrations.generic_fallback_path()` directly rather than duplicating either, so the render path and the offline `--validate` CLI can never drift apart (per the plan's explicit constraint)
- Kept the degradation diagnostic to a single `sys.stderr` line per rejected candidate (path + reason only, no image bytes) - matches `poll_loop.py`'s existing failure-logging pattern and satisfies T-03-04-03's accepted disposition

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria were verified command-for-command against the plan text.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification Run (in order, per plan)

1. `server/.venv/bin/python3 server/test_render.py` - exit 0, `render: 38/38 checks pass`
2. `server/.venv/bin/python3 server/test_illustrations.py` - exit 0, `illustrations: 42/42 checks pass` (confirms `illustrations.py` untouched)
3. `bash scripts/run-all-tests.sh` - exit 0, all nine harnesses reporting, 79% coverage (floor 75%)
4. `server/.venv/bin/python3 -m ruff check .` - no findings
5. `git status --porcelain server/plane/illustrations.py server/poll_loop.py` - empty (neither file modified)
6. 03-VERIFICATION.md's two `NOT_WIRED` Key Link rows are now closed by inspection: `_build_active_canvas()` -> decode error handling is wired via `_load_illustration_safely()`; the render path now enforces `ILLUSTRATION_MAX_PIXELS` via `_illustration_over_pixel_cap()`

**03-VERIFICATION.md gaps #1 and #2, and both `NOT_WIRED` key links, are closed. Phase 3 can be re-verified at 8/8 must-haves.**

## Next Phase Readiness

- Phase 3 (visual-polish-on-real-glass) is now fully closed at the code level - all must-haves this plan targeted are verified passing.
- No blockers introduced. The next planned phase-level work (Phase 5 battery-life run, Phase 6 final on-glass verification) is unaffected by this change.

---
*Phase: 03-visual-polish-on-real-glass*
*Completed: 2026-08-27*

## Self-Check: PASSED

- FOUND: server/plane/render.py
- FOUND: server/test_render.py
- FOUND: .planning/phases/03-visual-polish-on-real-glass/03-04-SUMMARY.md
- FOUND: 96e4a4d (test commit)
- FOUND: 4efbe5e (fix commit)
