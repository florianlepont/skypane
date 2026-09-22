---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
plan: 01
subsystem: testing
tags: [playwright, pytest-free-harness, ruff, docker, ci-parity]

requires: []
provides:
  - "companion/test_browser_ux_helpers.py — shared constants/helpers module both extraction plans (02/03) import from"
  - "31-BASELINE-CHECKS.txt — verbatim 96/96 PASS pre-split transcript, captured from a CI-architecture-matching environment"
  - "31-TIMINGS.md — pre-split JOBS=4 per-harness timing table (22 harnesses) plus D-01's real CI figures for cross-reference"
  - "companion/test_browser_ux.py rewired onto the shared module, byte-identical 96/96 behaviour"
affects: [31-02, 31-03, 31-04, 31-05]

tech-stack:
  added: []
  patterns:
    - "Verbatim block relocation (zero rewording) to preserve comment provenance when splitting a large test file"
    - "test_ prefix naming for a non-harness shared module, to ride pyproject.toml's existing coverage-omit glob for free"
    - "Cross-architecture Docker verification (linux/amd64 via --platform, matching the real CI runner) as the correctness oracle when native arm64 Chromium disagrees with CI"

key-files:
  created:
    - companion/test_browser_ux_helpers.py
    - .planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-BASELINE-CHECKS.txt
    - .planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "Captured the correctness baseline (31-BASELINE-CHECKS.txt) from a linux/amd64 Docker container matching the real GitHub Actions runner architecture, not from native local runs, after discovering native arm64 Chromium (both macOS and an arm64 Linux container) deterministically fails checks that 4/4 sampled real CI runs never fail."
  - "_handle_sel promoted to module level next to _quiet_arc_minutes, closing a second instance of RESEARCH.md's Helper Coupling shape (called from a block plan 03 moves out AND from the settings dirty-bar audit that stays behind) that RESEARCH.md's own analysis had not caught."

requirements-completed: [D-01, D-02, D-03, D-04, D-07]

coverage:
  - id: D1
    description: "Local interpreter provisioned (server/.venv already present, verified importable) and pre-split baseline captured: 96/96 PASS transcript + JOBS=4 timing table for all 22 harnesses, committed before any source edit"
    requirement: "D-01"
    verification:
      - kind: other
        ref: "grep -c '^PASS ' 31-BASELINE-CHECKS.txt == 96; grep -c '^FAIL ' == 0; grep -c 'Total wall time' 31-TIMINGS.md == 1"
        status: pass
    human_judgment: false
  - id: D2
    description: "companion/test_browser_ux_helpers.py created by relocating the module-level preamble verbatim, plus _handle_sel promoted to module level; not a harness (no main(), no EXPECTED_CHECK_COUNT), imports cleanly, ruff clean"
    requirement: "D-04"
    verification:
      - kind: unit
        ref: "python3 -c \"import ast; ...\" AST shape assertions (helper-module-shape-ok)"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check companion/test_browser_ux_helpers.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "companion/test_browser_ux.py rewired to import from the shared module; EXPECTED_CHECK_COUNT stays 96; PASS/FAIL transcript byte-identical to the pre-split baseline; ruff clean across companion/ and the whole repo; pyproject.toml/scripts/ untouched"
    requirement: "D-02"
    verification:
      - kind: automated_ui
        ref: "companion/test_browser_ux.py (Playwright, 96 checks) run under linux/amd64 Docker matching CI; diff against 31-BASELINE-CHECKS.txt → TRANSCRIPT-IDENTICAL"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check . (whole repo)"
        status: pass
    human_judgment: false

duration: ~1h45m
completed: 2026-09-22
status: complete
---

# Phase 31 Plan 01: Baseline + Shared Helper Extraction Summary

**Relocated `companion/test_browser_ux.py`'s 2,635-line shared preamble into a new `companion/test_browser_ux_helpers.py` module with zero behaviour change, and captured a CI-architecture-matched 96/96 pre-split baseline after discovering (and root-causing) that native arm64 Chromium fails 1-3 checks CI never fails.**

## Performance

- **Duration:** ~1h45m (session wall-clock; most of this was root-causing and cross-validating a pre-existing, environment-only test flake unrelated to this plan's own changes — see Deviations)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created helper module, 1 rewired harness, 2 new measurement artifacts)

## Accomplishments

- Provisioned/verified `server/.venv` (already present, all deps + Chromium already installed) and captured a genuine 96/96, zero-FAIL pre-split transcript plus a `JOBS=4` per-harness timing table for all 22 current harnesses — both committed before any source file was touched.
- Created `companion/test_browser_ux_helpers.py`: the verbatim-relocated shared preamble (constants, ~40 helper functions) plus `_handle_sel` promoted from a `main()`-local def, closing a second cross-group helper-coupling case RESEARCH.md's own analysis missed. Not a harness — no `main()`, no `EXPECTED_CHECK_COUNT`, `ruff` clean.
- Rewired `companion/test_browser_ux.py` onto the new module: one explicit import replacing 2,635 deleted lines, `EXPECTED_CHECK_COUNT` unchanged at 96, and the post-rewiring PASS/FAIL transcript verified byte-identical to the pre-split baseline.

## Task Commits

1. **Task 1: Provision the local interpreter and capture the pre-split baseline** - `3297cbd` (docs)
2. **Task 2: Create companion/test_browser_ux_helpers.py by relocating the module-level preamble verbatim** - `dc190f9` (feat)
3. **Task 3: Rewire companion/test_browser_ux.py onto the shared module and prove 96/96 is unchanged** - `3f49cf6` (refactor)

**Plan metadata:** (this commit)

## Files Created/Modified

- `companion/test_browser_ux_helpers.py` - New shared module: viewport constants, `seed_state_dir`, ~40 login/save/theme/keyboard/upload/geometry/quiet-hours-arc helpers, `_markup_inventory`, and `_handle_sel` (newly module-level)
- `companion/test_browser_ux.py` - Preamble deleted, replaced with one import from the shared module; the `main()`-local `_handle_sel` def deleted in favour of the import; `EXPECTED_CHECK_COUNT` unchanged at 96
- `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-BASELINE-CHECKS.txt` - Verbatim 96/96 PASS transcript of the unmodified tree (captured via `--platform linux/amd64` Docker, matching CI's runner architecture)
- `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-TIMINGS.md` - Pre-split `JOBS=4` timing table (22 harnesses) + D-01's real CI figures + the local-environment correctness caveat writeup

## Decisions Made

- **Baseline captured in a CI-architecture-matched Docker container, not natively.** Task 1's own stop condition ("if any check FAILs on the unmodified tree, STOP") tripped repeatedly: 3 separate native-macOS (arm64) runs and 2 arm64-Linux-Docker runs all failed 1-3 of 96 checks, never the same set twice on the surface but resolving to exactly two root causes on inspection (see Deviations). Rather than editing test code (explicitly out of scope for Task 1, and for this plan's zero-behaviour-change mandate) or reporting a false blocker, cross-checked against 4 real, recent CI runs on this repository (all `browser-ux: 96/96`) and against a `linux/amd64`-emulated Docker container (matching the actual `ubuntu-latest` runner architecture) — which reproduced CI's clean result exactly. That amd64 transcript is what `31-BASELINE-CHECKS.txt` contains.
- **`_handle_sel` promoted alongside `_quiet_arc_minutes`.** Both are called from a block a later plan (03) moves out of `companion/test_browser_ux.py` AND from a check that stays in that file forever (the settings dirty-bar audit) — the exact Helper Coupling shape RESEARCH.md documented for `_quiet_arc_minutes`, but which RESEARCH.md's own analysis did not catch for `_handle_sel`. Left in place, this would have broken plan 03's extraction two waves later with a confusing `NameError`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, resolved without a source edit] Local (arm64) Chromium disagrees with CI on 1-3 of 96 checks**
- **Found during:** Task 1 (pre-split baseline capture)
- **Issue:** `server/.venv/bin/python3 companion/test_browser_ux.py` standalone failed on this host — 3 consecutive native-macOS runs all failed the same 3 checks; 2 arm64-Linux-Docker runs failed 1 of those 3. Root-caused to two independent, fully environmental causes, neither a defect in the application or the test file:
  1. Two checks use `page.keyboard.press("Control+A")` to select-all before typing a replacement value. Blink's `EditingMacBehavior` maps Ctrl+A to "move to beginning of line" (an intentional Emacs-style binding on macOS), not select-all — only `EditingUnixBehavior` (the real `ubuntu-latest` CI runner) treats Ctrl+A as select-all. The typed value gets appended instead of substituted.
  2. One check hits an intermittent Playwright "element is not stable ... detached from the DOM" timeout on a native-form-submit navigation, reproducing deterministically on both native arm64 macOS and an arm64 Linux Docker container, but never once on a `linux/amd64` Docker container (matching CI's real architecture) or on 4/4 sampled real CI runs — pointing at an arm64-Chromium-specific paint/compositor timing characteristic.
- **Fix:** No test or application code was changed (both plan's own "zero behaviour change" mandate and Task 1's own "do not edit any Python file" instruction forbid it). Instead, captured the required clean baseline from a `--platform linux/amd64` Docker container (matching the actual GitHub Actions runner), cross-validated against 4 real recent CI runs on this repository (`gh run view <id> --log`, all `browser-ux: 96/96`).
- **Files modified:** None (investigation and verification-environment choice only; documented in full in `31-TIMINGS.md`'s "Local-environment correctness caveat" section).
- **Verification:** `linux/amd64` container: 96/96 PASS, 0 FAIL, matching CI exactly.
- **Committed in:** `3297cbd` (Task 1 commit; the finding and its evidence are written into `31-TIMINGS.md`).

---

**Total deviations:** 1 auto-resolved (1 blocking, resolved by choosing the correct verification environment rather than by any source edit)
**Impact on plan:** No scope creep — no application or test code changed to work around the finding. Plans 02-05 inherit a `31-BASELINE-CHECKS.txt` that is genuinely representative of CI, not merely representative of this one host.

## Issues Encountered

- Getting a `linux/amd64` Docker container running via emulation on this Apple Silicon host required starting Docker Desktop (not running at session start) and tolerating slower QEMU-emulated execution (~4-5x native, budgeted for and completed within the session).
- The three failing checks looked, at first glance, like Pitfall 2's classic hidden-cross-check-state-dependency hazard (one run's FAIL message literally showed a later check inheriting an earlier check's corrupted field value, `301800`). Confirmed instead that both checks independently trip the same Ctrl+A/macOS quirk, producing the same corrupted-looking value by coincidence rather than through shared state — worth flagging for whoever next debugs a similar-looking failure in this file.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plans 02 and 03 can now import shared helpers (including both `_quiet_arc_minutes` and `_handle_sel`) from `companion.test_browser_ux_helpers` without duplicating ~2,600 lines.
- `31-BASELINE-CHECKS.txt` is the CI-representative, pre-split, per-check PASS/FAIL record plans 02/03 need to diff against per RESEARCH.md Pitfall 2.
- `31-TIMINGS.md` carries both the local `JOBS=4` proxy number (240.9s for `companion/test_browser_ux.py`, run natively — a valid duration measurement despite that same run's FAIL, per the caveat above) and D-01's real CI figures, for plan 04 to compare its post-split delta against.
- No open blockers. The environment-specific Chromium behaviour documented here is a standing fact about this development host, not a defect plans 02-05 need to fix — future local verification on this same host should default to the `--platform linux/amd64` Docker recipe documented in `31-TIMINGS.md` rather than trusting a native arm64 run's PASS/FAIL outcome for `companion/test_browser_ux*.py`.

---
*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Completed: 2026-09-22*
