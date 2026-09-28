---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 04
subsystem: firmware
tags: [ota, pillow, e-ink, floyd-steinberg, hold-screen, codegen]

requires:
  - phase: 12-remote-display-on-off-toggle
    provides: the dimmed hold-screen visual family (_build_dimmed_hold_canvas, DIMMED_* constants) this plan's UPDATING screen joins
  - phase: 36-state-integrity-and-device-protocol
    provides: the on-device NO CONNECTION mask/dither precedent (fault_screen.c, gen_fault_screen.py) this plan generalises
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: the server.plane.render.py -> render/ package split this plan's Task 2 had to re-target
provides:
  - "server/plane/render: UPDATING_* copy constants, draw_updating_icon, _build_updating_canvas (source of truth for the device mask)"
  - "firmware/tools/gen_fault_screen.py --screen {no-connection,updating}: table-driven header/preview generator, no-connection path unchanged"
  - "firmware/main/updating_screen_mask.h: committed, generated ink mask"
  - "firmware/main/hold_screen.c/.h: the one shared on-device dither+mask-stamp renderer (fp_hold_screen_render), used by both NO CONNECTION and UPDATING"
  - "firmware/main/updating_screen.c/.h: fp_updating_screen_render(buf, tick), FP_UPDATING_SCREEN_BYTES, FP_UPDATING_SCREEN_HASH \"ota:updating\" - ready for a later plan to wire into app_main.c"
affects: [42-13, "any later Phase 42 plan touching app_main.c's OTA wake path"]

tech-stack:
  added: []
  patterns:
    - "One on-device dither-and-mask renderer (hold_screen.c) shared by every hold screen drawn entirely on the device, each screen a thin wrapper supplying its own committed fp_hold_mask_t"
    - "Server-side mask source of truth (render/hold_screens.py's flat=True canvas) plus a table-driven generator (gen_fault_screen.py --screen) that can grow more hold screens without duplicating the header/preview machinery"

key-files:
  created:
    - server/test_updating_screen.py
    - server/test_updating_screen_mask.py
    - firmware/main/updating_screen_mask.h
    - firmware/main/hold_screen.c
    - firmware/main/hold_screen.h
    - firmware/main/updating_screen.c
    - firmware/main/updating_screen.h
    - firmware/tests/test_updating_screen.c
    - .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/deferred-items.md
  modified:
    - server/plane/render/style.py
    - server/plane/render/glyphs.py
    - server/plane/render/hold_screens.py
    - server/plane/render/__init__.py
    - firmware/tools/gen_fault_screen.py
    - firmware/main/fault_screen.c
    - firmware/tests/test_fault_screen.c
    - firmware/VENDOR.md

key-decisions:
  - "server/plane/render.py is now a package (server/plane/render/) since Phase 39's ARC split; placed the new UPDATING_* code in the matching modules (style.py/glyphs.py/hold_screens.py) instead of recreating a monolithic render.py"
  - "_build_updating_canvas(flat) calls _build_hold_canvas() directly (not _build_dimmed_hold_canvas(), which has no flat/dithered toggle) - mirrors _build_no_connection_canvas()'s own established precedent for the one other hold screen that needs a flat mode"
  - "draw_updating_icon's arrowheads are drawn strictly inside the 76px ring's own radius (chevron wings at 0.72x radius, tip on the radius itself) rather than projecting outward, keeping the glyph within the same safe-box footprint every sibling hold glyph assumes"
  - "UPDATING's default preview path is the system temp dir, not a .planning/quick/ archive path like NO CONNECTION's historical default - it has no equivalent archived quick-task to live under"

requirements-completed: []

coverage:
  - id: D1
    description: "UPDATING hold-screen composition (heading, body copy, icon) exists in server/plane/render and is provably the source of truth for the committed device mask"
    verification:
      - kind: unit
        ref: "server/test_updating_screen.py#test_updating_copy_constants_match_locked_strings"
        status: pass
      - kind: unit
        ref: "server/test_updating_screen.py#test_updating_dispatches_through_shared_hold_composition"
        status: pass
      - kind: unit
        ref: "server/test_updating_screen_mask.py#test_updating_screen_mask_header_matches_generator_output"
        status: pass
    human_judgment: false
  - id: D2
    description: "One shared on-device renderer (hold_screen.c) draws both NO CONNECTION (byte-identical to before the refactor) and UPDATING, proven by host tests"
    verification:
      - kind: unit
        ref: "firmware/tests/test_fault_screen.c#render_output_matches_golden_digest (sh firmware/tests/run_host_tests.sh)"
        status: pass
      - kind: unit
        ref: "firmware/tests/test_updating_screen.c#updating_output_differs_from_no_connection_output (sh firmware/tests/run_host_tests.sh)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The UPDATING screen's visual composition (glyph, heading, body) actually reads correctly on the frame's own conventions - a real render, not just pixel-count assertions"
    verification: []
    human_judgment: true
    rationale: "No hardware session or preview review is in this plan's scope; the icon's bezier geometry and copy placement were verified only by automated bounding-box/pixel-count tests, not a human looking at the rendered PNG (firmware_equivalent_image / _write_preview exist for exactly this but were not run to a screen this session)."

duration: 1h43m
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 04: UPDATING hold screen (server composition, generated mask, shared device renderer) Summary

**New UPDATING hold screen shares the NO CONNECTION dither-and-mask machinery end to end: one `_build_hold_canvas()`-family composition in `server/plane/render`, one table-driven `gen_fault_screen.py --screen` generator, and one on-device `hold_screen.c` renderer both screens now call.**

## Performance

- **Duration:** 1h43m
- **Started:** 2026-09-28T09:56Z (STATE.md's prior session close)
- **Completed:** 2026-09-28T11:39Z
- **Tasks:** 3 (Task 1 read-only, Tasks 2-3 each one commit)
- **Files modified:** 16 (8 created, 8 modified, across two commits plus one small fix commit)

## Accomplishments
- `server/plane/render`'s UPDATING composition (`UPDATING_HEADING_TEXT`, `UPDATING_BODY_LINES`, `draw_updating_icon`, `_build_updating_canvas`) - the flat variant is the exact source of truth `gen_fault_screen.py --screen updating` extracts
- `firmware/tools/gen_fault_screen.py` generalised to a `--screen {no-connection,updating}` table dispatch; the default (no-connection) path, its header banner, and its committed output are unchanged
- `firmware/main/updating_screen_mask.h` generated and committed
- The on-device dither-and-mask-stamp routine moved out of `fault_screen.c` into a new shared `hold_screen.c`/`hold_screen.h` (`fp_hold_screen_render`), with a single static accumulator-row pair and one `DITHER_TARGET_LEVEL` definition for every hold screen
- `firmware/main/updating_screen.c`/`.h` - `fp_updating_screen_render(buf, tick)`, `FP_UPDATING_SCREEN_BYTES`, `FP_UPDATING_SCREEN_HASH "ota:updating"` - built and host-tested, not yet wired into `app_main.c` (that wiring is explicitly a later plan's job per this plan's own interface contract)
- A golden FNV-1a 64 digest recorded in `test_fault_screen.c` from the pre-refactor render output proves the NO CONNECTION screen's bytes are unchanged after the move

## Task Commits

1. **Task 1: Gate G-41 (Phase 41 complete on main)** - read-only, no commit (all three checks passed: `41-VERIFICATION.md` status passed, 0 unchecked Phase 41 ROADMAP boxes, `origin/main` an ancestor of HEAD)
2. **Task 2: Server composition, generator support and committed mask** - `e546ae30` (feat)
   - **Fix-up:** `98e02b4c` (fix) - dropped decision-ID references from `test_updating_screen.py`'s comments (see Deviations)
3. **Task 3: Shared hold-screen renderer and the device UPDATING screen** - `1f3ed10c` (feat)

**Plan metadata:** pending (this commit)

## Files Created/Modified
- `server/plane/render/style.py` - `UPDATING_HEADING_TEXT`/`UPDATING_BODY_LINES`/`UPDATING_BODY_TEXT` locked copy
- `server/plane/render/glyphs.py` - `draw_updating_icon` (two opposing ~90° arcs, chevron arrowheads inside the ring), `UPDATING_ICON_*` constants
- `server/plane/render/hold_screens.py` - `_build_updating_canvas(flat=False)`
- `server/plane/render/__init__.py` - re-exports the new names
- `server/test_updating_screen.py` - 7 behaviour tests
- `server/test_updating_screen_mask.py` - generator byte-for-byte drift test
- `firmware/tools/gen_fault_screen.py` - `--screen` option, `_SCREENS` table dispatch
- `firmware/main/updating_screen_mask.h` - generated, committed
- `firmware/main/hold_screen.c`/`.h` - the shared renderer
- `firmware/main/fault_screen.c` - now a thin call into `hold_screen.c`
- `firmware/main/updating_screen.c`/`.h` - the UPDATING screen
- `firmware/tests/test_fault_screen.c` - golden digest pin, `HOST_TEST_DEPS: hold_screen.c`
- `firmware/tests/test_updating_screen.c` - new host suite
- `firmware/VENDOR.md` - documents the new/changed original-to-this-repo files
- `.planning/phases/42-.../deferred-items.md` - the one out-of-scope, pre-existing finding below

## Decisions Made
- Placed the new code in `server/plane/render/{style,glyphs,hold_screens}.py` rather than recreating `render.py`, since Phase 39 already split it into a package and every name is still re-exported through `server/plane/render/__init__.py`
- `_build_updating_canvas(flat)` calls `_build_hold_canvas()` directly (mirroring `_build_no_connection_canvas()`), not `_build_dimmed_hold_canvas()`, since the latter has no flat/dithered toggle and the mask generator needs one
- `draw_updating_icon`'s arrowheads stay strictly inside the glyph's own 76px radius so its footprint matches the safe-box assumption every sibling hold glyph (`half = POWER_ICON_DIAMETER_PX // 2`) already relies on
- `UPDATING`'s default preview path is the system temp dir (not a `.planning/quick/` archive path) since there is no equivalent archived quick-task for it

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `server/plane/render.py` no longer exists - it is now a package**
- **Found during:** Task 2, first file read
- **Issue:** The plan's `files_modified` and interface notes target `server/plane/render.py`, but Phase 39's architecture split it into `server/plane/render/` (`style.py`, `glyphs.py`, `text.py`, `layout.py`, `hold_screens.py`, `cli.py`, `__init__.py`) before this plan ran
- **Fix:** Added the UPDATING constants/glyph/canvas-builder to the matching sibling modules and re-exported them through `__init__.py`, exactly matching how `NO_CONNECTION_*`/`draw_alert_icon`/`_build_no_connection_canvas` are already split and re-exported
- **Files modified:** `server/plane/render/style.py`, `glyphs.py`, `hold_screens.py`, `__init__.py`
- **Verification:** `server/test_updating_screen.py` and `server/test_render.py` (157 tests) both pass importing `server.plane.render` exactly as every existing caller does
- **Committed in:** `e546ae30`

**2. [Rule 1 - Bug] `check_comment_history.py` flagged D-14 citations added by this plan's own comments**
- **Found during:** Task 3, pre-commit check (the checker only scans *tracked* files, so it missed these in the Task 2 commit that introduced them)
- **Issue:** New comments in `glyphs.py`, `hold_screens.py`, `style.py` and `test_updating_screen.py` cited "D-14" (the CONTEXT.md decision ID) and a `.planning/`-shaped literal in `gen_fault_screen.py`, both forbidden by this project's comment-history rule
- **Fix:** Reworded every citation to describe the rationale without the ID
- **Files modified:** `server/plane/render/glyphs.py`, `hold_screens.py`, `style.py`, `firmware/tools/gen_fault_screen.py` (fixed in `e546ae30`); `server/test_updating_screen.py` (fixed in a follow-up commit `98e02b4c`, since it was already committed by the time the tracked-files-only scan caught it)
- **Verification:** `server/.venv/bin/python3 scripts/check_comment_history.py check` exits 0
- **Committed in:** `e546ae30`, `98e02b4c`

**3. [Rule 2 - Missing Critical] `firmware/VENDOR.md` not updated for the new/changed original-to-this-repo files**
- **Found during:** Task 3, before committing
- **Issue:** This project's stated convention requires every SkyPane-original firmware file to be listed in `VENDOR.md`; the refactor changed `fault_screen.c`'s description and added four new files with no entry
- **Fix:** Updated the `fault_screen.c` bullet and added `hold_screen.c/.h`, `updating_screen.c/.h`, `updating_screen_mask.h` entries, and updated `gen_fault_screen.py`'s bullet to describe `--screen`
- **Files modified:** `firmware/VENDOR.md`
- **Verification:** Manual read-through against the existing entries' format
- **Committed in:** `1f3ed10c`

---

**Total deviations:** 3 auto-fixed (1 blocking/file-layout, 1 bug/comment-rule, 1 missing-critical/docs)
**Impact on plan:** All three were necessary to land working, rule-compliant code; none changed the plan's actual scope or the UPDATING screen's design.

## Issues Encountered

**`server/test_fault_screen_mask.py` fails in this sandbox - pre-existing on `origin/main`, unrelated to this plan.** The committed `firmware/main/fault_screen_mask.h` is not byte-for-byte reproducible by `gen_fault_screen.py` in this sandbox (`FP_FAULT_MASK_W` generates as `564` vs the committed `565`; nothing else in the 128,919-byte header differs). Proven pre-existing by checking out a clean, unmodified `origin/main` worktree and reproducing the identical mismatch with zero code from this plan involved - almost certainly a cross-platform Pillow/FreeType text-metric difference between whatever machine last regenerated the committed header and this sandbox, not a general rendering break (`server/test_render.py`'s full 149-test suite, including its own NO CONNECTION/ALERT_ICON pixel assertions, passes cleanly here). Not fixed here: regenerating the header would change the committed NO CONNECTION mask's bytes, which this plan's own constraint and files_modified list both forbid. Full writeup and suggested follow-up in `.planning/phases/42-.../deferred-items.md`. The new `updating_screen_mask.h` this plan commits was generated fresh in this same sandbox, so it carries no such drift - `test_updating_screen_mask.py` passes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `fp_updating_screen_render(buf, tick)`, `FP_UPDATING_SCREEN_BYTES` and `FP_UPDATING_SCREEN_HASH` are ready for a later plan (the interface contract names "plan 13") to wire into `app_main.c`'s OTA wake path
- `firmware/main/fault_screen.c` was not moved or renamed - callers (`app_main.c`) compile unchanged
- Blocker/concern: the pre-existing `test_fault_screen_mask.py` sandbox drift above should be checked against whatever environment CI (`firmware.yml`) actually runs in, before it surprises a later plan

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 17 files listed under Files Created/Modified verified present on disk;
all 3 task commit hashes (`e546ae30`, `98e02b4c`, `1f3ed10c`) verified in
`git log --oneline --all`.
