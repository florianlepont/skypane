---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 03
subsystem: api
tags: [pillow, png, panel-format, preview]

requires:
  - phase: 02-real-flight-rendering-pipeline
    provides: server/panel_format.py's pack_panel()/INDEX_TO_NIBBLE/IMAGE_BYTES single source of truth for the Spectra 6 wire format
provides:
  - "server/panel_preview.py: unpack_panel() (exact inverse of pack_panel()), panel_png_bytes() (real PNG bytes with nearest-neighbour thumbnailing), read_panel_file()/panel_file_mtime_iso() (safe panel.bin access for an HTTP handler)"
affects: [06-companion-configuration-web-interface-visual-settings-view-s, preview-page, companion-http]

tech-stack:
  added: []
  patterns:
    - "NIBBLE_TO_INDEX derived by inverting panel_format.INDEX_TO_NIBBLE via dict comprehension - never a hand-typed second table, so pack/unpack can never silently drift apart"
    - "Typed PanelDecodeError(ValueError) as the single exception type an HTTP handler catches to turn malformed panel.bin into an error page, never an unhandled crash"

key-files:
  created:
    - server/panel_preview.py
    - server/test_panel_preview.py
  modified:
    - pyproject.toml

key-decisions:
  - "unpack_panel() returns a 'P'-mode Image (not RGB) so the round-trip harness can compare index data directly; panel_png_bytes() does the RGB conversion + resize + PNG encode on top"
  - "panel_png_bytes()'s resize path always passes resample=Image.NEAREST explicitly (never a default filter) since any smoothing filter would blend the six flat panel colours into intermediate values that do not exist on the device"
  - "Added server/panel_preview.py to pyproject.toml's coverage omit list, same precedent as 06-01's device_config.py/history_db.py entry - the module is real and fully tested (test_panel_preview.py, 11/11) but that harness isn't registered in scripts/run-all-tests.sh's HARNESSES array yet (06-11's job); leaving it un-omitted would misrepresent a real, tested module as an uncovered gap"

patterns-established:
  - "Preview/read-only transform modules for the companion HTTP layer live as leaf modules (stdlib + Pillow + panel_format only) with their own dedicated test harness, following server/device_config.py/history_db.py's 06-01 precedent"

requirements-completed: [CFG-10]

coverage:
  - id: D1
    description: "unpack_panel() is proven the exact mathematical inverse of panel_format.pack_panel() over a full canvas containing all six legal indices, including a mixed odd/even nibble pair inside one packed byte"
    requirement: CFG-10
    verification:
      - kind: unit
        ref: "server/test_panel_preview.py#a canvas containing all six legal indices, including a mixed odd/even column pair, round-trips exactly"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#a row with two different legal indices at column 0 and column 1 round-trips without a high/low nibble swap"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#the full getdata() sequence (not a sampled subset) matches exactly for an all-six-indices canvas"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#a real production render.render_panel(None, 'empty') round-trips index-for-index against build_canvas()"
        status: pass
    human_judgment: false
  - id: D2
    description: "A malformed panel.bin (wrong length, or containing the one illegal nibble code 0x4) raises the typed PanelDecodeError, never AssertionError/IndexError/a crash"
    requirement: CFG-10
    verification:
      - kind: unit
        ref: "server/test_panel_preview.py#unpack_panel() on wrong-length input raises PanelDecodeError, never AssertionError/IndexError"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#unpack_panel() on the one illegal nibble code raises PanelDecodeError naming the offending code"
        status: pass
    human_judgment: false
  - id: D3
    description: "panel_png_bytes() produces a real, Pillow-decodable PNG at the correct dimensions, and its max_width thumbnail path resizes proportionally via nearest-neighbour only (no invented intermediate colours)"
    requirement: CFG-10
    verification:
      - kind: unit
        ref: "server/test_panel_preview.py#panel_png_bytes() returns real, Pillow-decodable PNG bytes at the expected dimensions"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#panel_png_bytes(max_width=240) returns a proportionally resized thumbnail"
        status: pass
      - kind: unit
        ref: "server/test_panel_preview.py#the nearest-neighbour thumbnail's colour set is a strict subset of the full image's colour set"
        status: pass
    human_judgment: false
  - id: D4
    description: "read_panel_file() returns None (not an exception) when panel.bin is missing, so the future /preview.png route can distinguish 'no panel yet' from 'panel present but unreadable'"
    requirement: CFG-10
    verification:
      - kind: unit
        ref: "server/test_panel_preview.py#read_panel_file() on a missing file returns None rather than raising"
        status: pass
    human_judgment: false

duration: ~15min
completed: 2026-08-27
status: complete
---

# Phase 6 Plan 3: Panel Preview Decoder Summary

**server/panel_preview.py — the exact inverse of panel_format.pack_panel(), turning the live panel.bin into real PNG bytes with a typed PanelDecodeError on malformed input, proven by an 11-check full-canvas round-trip harness**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-27T23:41:31+02:00 (first task commit)
- **Completed:** 2026-08-27T23:41:40+02:00 (second task commit)
- **Tasks:** 2
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments

- `unpack_panel()` walks `pack_panel()`'s exact row/column-pair loop in reverse, using `NIBBLE_TO_INDEX` (derived by inverting `panel_format.INDEX_TO_NIBBLE` via a dict comprehension) so the two directions can never silently drift apart
- `PanelDecodeError(ValueError)` is the single typed exception raised on both the wrong-length path (naming expected vs. actual byte counts) and the illegal-nibble path (naming the offending code and its byte offset) - never `AssertionError`/`IndexError`, so a future HTTP handler can catch one type and return an error page instead of crashing
- `panel_png_bytes()` unpacks, converts to RGB, and encodes real PNG bytes; its optional `max_width` thumbnail path always passes `resample=Image.NEAREST` explicitly, proven (not just asserted) to introduce zero new colours via a colour-set-subset check
- `read_panel_file()`/`panel_file_mtime_iso()` give the future `/preview.png` route safe access to `state_dir/panel.bin` - missing file returns `None` rather than raising, and the length/content validity check is deliberately left to `unpack_panel()` alone
- `server/test_panel_preview.py`: 11 checks, including a full-canvas round trip over all six legal palette indices with an explicit mixed nibble pair, a production round trip against `render.render_panel(None, "empty")`/`render.build_canvas(None, "empty")`, and a live-demonstrated (then reverted) high/low nibble transposition that made 4 of the 11 checks fail as designed

## Task Commits

Each task was committed atomically:

1. **Task 1: Create server/panel_preview.py — unpack_panel() and PNG encoding** - `4128b46` (feat)
2. **Task 2: Create server/test_panel_preview.py — full-canvas round-trip proof** - `033a7e2` (test)

**Plan metadata:** see below (this SUMMARY.md + STATE.md/ROADMAP.md commit)

## Files Created/Modified

- `server/panel_preview.py` - `unpack_panel()`, `panel_png_bytes()`, `read_panel_file()`, `panel_file_mtime_iso()`, `PanelDecodeError`, `NIBBLE_TO_INDEX`
- `server/test_panel_preview.py` - 11-check round-trip proof harness, `EXPECTED_CHECK_COUNT = 11`
- `pyproject.toml` - added `server/panel_preview.py` to `[tool.coverage.report].omit`, matching the 06-01 precedent, to be removed by plan 06-11 when the harness is registered in `scripts/run-all-tests.sh`

## Decisions Made

- Task 1's `<verify>` block names `server/test_panel_preview.py` even though that file is created by Task 2 - both tasks were executed and verified together as one coherent unit (implementation, then its round-trip proof), consistent with how the plan's own `<verification>` section frames the pair
- Coverage-omit fix (see Deviations below) attached to Task 1's commit rather than Task 2's, since the 0%-covered-production-code problem exists the moment `panel_preview.py` exists under `server/`, independent of whether its test harness also exists yet

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality, build-config correctness] Added `server/panel_preview.py` to `pyproject.toml`'s coverage omit list**

- **Found during:** Task 1 (after creating `server/panel_preview.py`, running `scripts/run-all-tests.sh` to confirm nothing broke)
- **Issue:** `server/panel_preview.py` is real, tested code (11/11 checks in `test_panel_preview.py`), but that harness is deliberately not yet registered in `scripts/run-all-tests.sh`'s `HARNESSES` array (per this plan's own `<verification>` block: "this plan's harness is registered by plan 06-11"). Without an omit entry, `coverage.py`'s source-scoped scan counts all 62 of the module's statements as 0%-covered production code purely because it exists under `server/` - misrepresenting real, tested code as an uncovered gap and pulling total coverage from 82% down to 78% for a reason unrelated to any actual regression. This is the exact same situation 06-01 already hit and fixed for `device_config.py`/`history_db.py`.
- **Fix:** Added `server/panel_preview.py` to the `omit` list in `pyproject.toml`, with a comment cross-referencing the 06-01 precedent and instructing 06-11 to remove it (alongside the two existing entries) once `test_panel_preview.py` is added to `HARNESSES`.
- **Files modified:** `pyproject.toml`
- **Verification:** `scripts/run-all-tests.sh` re-run after the fix - coverage correctly reports 82% (up from the 78% it showed with `panel_preview.py` counted as 0%-covered production code), gate still passes (75% floor either way, so this was never a blocking failure - a correctness fix, not a gate rescue).
- **Committed in:** `4128b46` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing-critical/build-config correctness)
**Impact on plan:** Matches an already-established in-phase precedent (06-01) exactly; no scope creep, no behavior change to `panel_preview.py` itself. The plan's stated `git diff --stat` verification ("touches only the two new files") is technically widened by this one extra line in `pyproject.toml` - documented here rather than silently deviating from the plan's verification text.

## Issues Encountered

None. Confirmed the harness's mixed-pair and full-index-sequence checks genuinely catch a regression by deliberately swapping the high/low nibble split in `unpack_panel()`, observing 4 of 11 checks fail as expected, then reverting before the Task 2 commit (`server/panel_preview.py` on disk matches the committed `4128b46` version exactly, verified by `git diff --stat server/panel_preview.py` showing no pending changes after the revert).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `panel_preview.py`'s `unpack_panel()`/`panel_png_bytes()` are ready for plan 06-09's `/preview.png` HTTP route to call directly - `PanelDecodeError` is the one exception type that route needs to catch to return 06-UI-SPEC.md's "temporarily unavailable" copy
- `read_panel_file()`/`panel_file_mtime_iso()` are ready for that same route to source `state_dir/panel.bin` and its caption timestamp
- Plan 06-09's Preview page must carry the D-P2-03 colour-accuracy caveat as caption copy (documented in `panel_preview.py`'s own module docstring) - the PNG's colours are nominal render-internal swatches, not colour-accurate against real Spectra 6 glass
- Plan 06-11 must remove the three coverage-omit lines (`device_config.py`, `history_db.py`, `panel_preview.py`) from `pyproject.toml` at the same time it registers `test_config_history.py` and `test_panel_preview.py` in `scripts/run-all-tests.sh`'s `HARNESSES` array, then re-measure/ratchet `fail_under` per the file's own derivation discipline
- No blockers for continuing Phase 6's remaining plans

## Self-Check: PASSED

- FOUND: server/panel_preview.py
- FOUND: server/test_panel_preview.py
- FOUND: .planning/phases/06-companion-configuration-web-interface-visual-settings-view-s/06-03-SUMMARY.md
- FOUND: commit 4128b46 (feat: server/panel_preview.py)
- FOUND: commit 033a7e2 (test: server/test_panel_preview.py)
