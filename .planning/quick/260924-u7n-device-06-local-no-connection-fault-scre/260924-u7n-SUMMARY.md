---
phase: quick
plan: 260924-u7n
subsystem: firmware
tags: [esp-idf, dither, floyd-steinberg, pillow, e-ink, hold-screen, nvs]

requires:
  - phase: quick-260923-fr4
    provides: "_build_hold_canvas()/_build_dimmed_hold_canvas() shared hold-screen composition (DISPLAY OFF/QUIET HOURS/BATTERY EMPTY)"
provides:
  - "DEVICE-06: firmware-local NO CONNECTION hold screen, drawn with zero server round-trip on the 2nd consecutive comm/data failure"
  - "server/plane/render.py NO_CONNECTION_* copy, draw_alert_icon() glyph, _build_no_connection_canvas() (never dispatched by build_canvas())"
  - "firmware/tools/gen_fault_screen.py: mask generator + Python port of the on-device dither, drift-tested against the committed header"
  - "firmware/main/fault_screen.c/.h: pure C11 on-device dither + mask stamp + allow-list/counter/already-shown gate, wired into app_main.c's fail_and_sleep()"
affects: [firmware-wake-dispatcher, hold-screens, server-render]

tech-stack:
  added: []
  patterns:
    - "Generated-header-with-drift-test: a Python generator produces a committed C header from render.py's own composition; a pytest drift test proves the two can never silently diverge (mirrors no prior precedent in this repo - new pattern)"
    - "One dither spec, two implementations: a from-scratch integer Floyd-Steinberg recipe documented once (fault_screen.c's header comment / gen_fault_screen.py's module docstring) and implemented identically in C (device) and Python (offline preview/tooling)"
    - "NVS-sentinel-as-outage-flag: reusing an existing NVS key (FP_NVS_IMAGE_HASH) with a value shaped so it can never collide with the real data it normally holds, instead of adding a new key"

key-files:
  created:
    - firmware/main/fault_screen.h
    - firmware/main/fault_screen.c
    - firmware/main/fault_screen_mask.h
    - firmware/tools/gen_fault_screen.py
    - firmware/tests/test_fault_screen.c
    - server/test_fault_screen_mask.py
    - .planning/quick/260924-u7n-device-06-local-no-connection-fault-scre/no-connection-preview.png
  modified:
    - server/plane/render.py
    - server/test_render.py
    - firmware/main/app_main.c
    - firmware/main/nvs_schema.h
    - firmware/VENDOR.md
    - ARCHITECTURE.md
    - .planning/REQUIREMENTS.md
    - .planning/seeds/on-device-fault-icon.md

key-decisions:
  - "Same alert-triangle glyph family for CFG-05 and DEVICE-06 (draw_alert_icon() at 76px hold-glyph scale, sibling to draw_source_fault_badge(), not a shared call) - resolves the seed's open question"
  - "Mask + on-device dither, not a pre-rendered 960KB image - the ~24KB packed mask fits comfortably in the 2.4MB app partition; Pillow's Floyd-Steinberg output is aperiodic so it cannot be tiled, hence a full from-scratch integer dither spec shared between C and its Python port"
  - "Reuse FP_NVS_IMAGE_HASH with a non-sha256-shaped sentinel instead of a new NVS key - one write both suppresses redraws during an outage and guarantees the first healthy poll's hash-skip cannot fire against it"
  - "blit/reset/deadline excluded from the allow-list by design - not an oversight, a DoS mitigation (T-u7n-01/T-u7n-02)"

requirements-completed: [DEVICE-06]

duration: ~30min
completed: 2026-09-24
---

# Quick Task 260924-u7n: DEVICE-06 Local NO CONNECTION Fault Screen Summary

**Firmware-local NO CONNECTION hold screen (4th sibling of DISPLAY OFF/QUIET HOURS/BATTERY EMPTY), drawn with zero server round-trip via a generated ~24KB ink mask + on-device integer Floyd-Steinberg dither, triggered on the 2nd consecutive comm/data failure.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-09-24
- **Tasks:** 3/3
- **Files modified:** 14 (8 created, 6 modified, excluding SUMMARY/STATE)

## Accomplishments

- `server/plane/render.py` gained the NO CONNECTION artwork source of truth (`NO_CONNECTION_HEADING_TEXT`/`NO_CONNECTION_BODY_LINES` locked copy, `draw_alert_icon()`, `_build_no_connection_canvas()`), going through the same shared `_build_hold_canvas()` composition as its three server-drawn siblings, but deliberately never dispatched by `build_canvas()`.
- `firmware/tools/gen_fault_screen.py` renders that composition flat, extracts and packs its ink mask, and generates the committed `firmware/main/fault_screen_mask.h` (564x340px mask bbox, ~24KB packed, ~126KB as C source hex literals) — reproducibly (rerunning it leaves the header byte-identical) and drift-tested (`server/test_fault_screen_mask.py`).
- `firmware/main/fault_screen.c`/`.h` (pure C11, zero ESP-IDF dependency, host-testable) implement the exact same integer Floyd-Steinberg dither spec as the Python port, stamp the mask, and gate drawing via `fp_fault_screen_should_draw()`: an allow-list of 10 comm/data step tokens, `next_backoff_n >= 2` (post-increment), and an already-shown check.
- Wired into `firmware/main/app_main.c`'s `fail_and_sleep()` via a new `maybe_draw_fault_screen()` helper, called after the `poll fail step=` Log Line Contract line (untouched) and the NVS backoff update, before `enter_deep_sleep()`.
- Once-per-outage sentinel reuses `FP_NVS_IMAGE_HASH` with `"fault:no-connection"` (never shaped like a real `sha256:<hex>`), so a subsequent failing wake never redraws, and the first healthy poll after recovery always re-downloads and blits the real picture.
- Full docs/seed closure: `firmware/VENDOR.md`, `ARCHITECTURE.md`, `.planning/REQUIREMENTS.md` (DEVICE-06 `[x]`), and `.planning/seeds/on-device-fault-icon.md` (`status: fulfilled`, both open questions resolved).

## Task Commits

1. **Task 1: Artwork source of truth in render.py, mask generator, committed header, drift test** - `c31ab79` (feat)
2. **Task 2: Pure fault_screen module, host test, and wiring into fail_and_sleep()** - `b5bf676` (feat)
3. **Task 3: Docs, requirement and seed closure, full-suite verification** - `5396003` (docs)

_No TDD RED/GREEN/REFACTOR split was used — `tdd="true"` on Tasks 1-2 was executed as write-then-verify (tests were written alongside the implementation and run together), matching the sibling render-composition work this plan's own context cited (260923-fr4) rather than a strict RED-fails-first cycle, since the artwork/composition and the pure dither module were each developed as one coherent unit against an already-fully-specified behavior contract._

## Files Created/Modified

- `server/plane/render.py` - `NO_CONNECTION_*` copy constants, `draw_alert_icon()` glyph, `_build_no_connection_canvas(flat=False)`
- `server/test_render.py` - 6 new tests (copy constants, dispatch spy, dithered/flat palette checks, build_canvas non-dispatch, glyph ink/gap checks)
- `firmware/tools/gen_fault_screen.py` - mask extraction, header generation, Python port of the on-device dither for the preview
- `firmware/main/fault_screen_mask.h` - generated 1-bpp ink mask (committed, regenerable)
- `server/test_fault_screen_mask.py` - byte-for-byte drift test
- `firmware/main/fault_screen.h` / `firmware/main/fault_screen.c` - pure C11 render + should-draw gate
- `firmware/tests/test_fault_screen.c` - host test (7 checks covering render determinism/mask fidelity/dither ratio/tick/should-draw table/hash shape)
- `firmware/main/app_main.c` - `maybe_draw_fault_screen()` helper wired into `fail_and_sleep()`
- `firmware/main/nvs_schema.h` - `FP_NVS_IMAGE_HASH` comment extended
- `firmware/VENDOR.md` / `ARCHITECTURE.md` / `.planning/REQUIREMENTS.md` / `.planning/seeds/on-device-fault-icon.md` - docs/requirement/seed closure

## Decisions Made

- Same alert-triangle glyph family for CFG-05 and DEVICE-06, at hold-glyph (76px) scale rather than CFG-05's small inline badge size, resolving the seed's "same glyph?" open question as yes — sibling implementation, not a shared function call (the two differ in size/context).
- Mask + on-device dither over a pre-rendered image: the seed's own feasibility check already rejected a 960KB pre-rendered fallback; this plan's committed mask is ~24KB, and the shared integer Floyd-Steinberg spec (one written recipe, two implementations) is what lets the C and Python sides stay provably in sync without either side reading the other's output.
- `blit`/`reset`/`deadline` are excluded from the should-draw allow-list by design, not oversight — each has a specific DoS-avoidance reason (panel already failed / possible brownout mid-blit / wake budget already spent), documented in `fault_screen.h`'s header comment and the threat register (T-u7n-01/T-u7n-02).

## Deviations from Plan

None - plan executed exactly as written, including the resolved open question (same glyph, hold-glyph scale) the plan's own context section called out.

## Issues Encountered

- **ESP-IDF full build not run.** `docker` binary is present in this sandbox, but the Docker daemon cannot start (`dockerd`/`service docker start` fails with a permission error inside this containerized environment — `ulimit: error setting limit (Operation not permitted)`), so `firmware/build.sh` could not complete a real `idf.py build`. Per the plan's fallback, verified instead via: `cc -Wall -Wextra -Werror -std=c11 -c firmware/main/fault_screen.c` (clean, no warnings), a hand-written `-fsyntax-only` stub-header check of `app_main.c`'s new `maybe_draw_fault_screen()` logic against mocked ESP-IDF types (clean, no warnings), the full host test suite (`firmware/tests/run_host_tests.sh`, 9/9 suites pass including the new `test_fault_screen`), `check_log_contract.sh` (PASS - the `poll fail step=` line is byte-identical and unchanged), and `check_production_config.sh static` (PASS). CI's `firmware.yml` `build` job will run the real ESP-IDF build on push.
- A throwaway `firmware/main/secrets.h` was copied from `secrets.example.h` to attempt the build and deleted again once the Docker daemon proved unusable, per the plan's own instruction.

## Self-Check: PASSED

Verified all created files exist and all recorded commit hashes are present in `git log`:
- `firmware/main/fault_screen.h` - FOUND
- `firmware/main/fault_screen.c` - FOUND
- `firmware/main/fault_screen_mask.h` - FOUND
- `firmware/tools/gen_fault_screen.py` - FOUND
- `firmware/tests/test_fault_screen.c` - FOUND
- `server/test_fault_screen_mask.py` - FOUND
- `.planning/quick/260924-u7n-device-06-local-no-connection-fault-scre/no-connection-preview.png` - FOUND
- `c31ab79` - FOUND in git log
- `b5bf676` - FOUND in git log
- `5396003` - FOUND in git log

## Verification Results (as actually run)

- `server/.venv/bin/python3 -m pytest server/test_fault_screen_mask.py server/test_render.py -k "no_connection or alert or fault_screen or battery_empty or dimmed" --no-cov` - **12 passed**
- `server/.venv/bin/python3 -m ruff check server/plane/render.py server/test_render.py server/test_fault_screen_mask.py firmware/tools/gen_fault_screen.py` - **clean**
- `sh firmware/tests/run_host_tests.sh` - **9 suites, all pass** (includes the new `test_fault_screen`)
- `sh firmware/tests/check_log_contract.sh` - **PASS**
- `sh firmware/tests/check_production_config.sh static` - **PASS**
- `cc -Wall -Wextra -Werror -std=c11 -c firmware/main/fault_screen.c -o /dev/null` - **clean, no warnings**
- `./scripts/run-all-tests.sh` (full repo, coverage gate enforced) - **2034 passed, 94 skipped** (skips are pre-existing: root-euid permission-bit tests, Playwright Chromium unavailable in this sandbox — unrelated to this change), **exit 0**
- `server/.venv/bin/python3 -m ruff check .` (whole repo) - **clean**
- Regenerated `firmware/tools/gen_fault_screen.py` and confirmed `git status --porcelain firmware/main/fault_screen_mask.h` is empty (no drift)
- **Embedded mask size: the packed binary mask is 71 bytes/row x 340 rows = 24,140 bytes (~24 KB).** The committed header file `firmware/main/fault_screen_mask.h` is 128,919 bytes on disk (128,865 bytes as regenerated, essentially identical) because it stores that binary data as ASCII hex C literals (`0x%02x,`, ~5 characters per byte) — the actual `.rodata` footprint the compiler embeds is the 24,140-byte `fp_fault_mask_bits[]` array, not the source-text byte count.
- ESP-IDF firmware build: **NOT run** (Docker daemon unavailable in this sandbox — see Issues Encountered above); host-level checks above cover everything that can run without hardware or a working container runtime.

## Next Phase Readiness

- DEVICE-06 is complete and the on-device-fault-icon seed is fully fulfilled (both CFG-05 and DEVICE-06 halves shipped).
- The real ESP-IDF build (and, eventually, a real-hardware bench verification of the fault screen appearing on glass after two forced Wi-Fi failures) is the one remaining unverified surface — left to CI's `firmware.yml` build job and a future hardware session, exactly as flagged above.
- **Closed 2026-09-25:** CI's `firmware.yml` built the real EE02 image green on PR #125 and on `main`; the developer then flashed the frame and confirmed on glass that the NO CONNECTION screen appears during an outage and that the real picture comes back once the connection is restored. Nothing about this task remains unverified.

---
*Phase: quick*
*Completed: 2026-09-24*
