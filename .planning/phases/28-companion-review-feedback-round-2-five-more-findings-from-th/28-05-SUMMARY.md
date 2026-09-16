---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 05
subsystem: ui
tags: [companion, theme-preview, carousel, intersection-observer, browser-testing, i18n]

# Dependency graph
requires:
  - phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
    provides: "27-07's strip_id-per-instance carousel discipline and the three-carousel _theme_carousel_html() shape this plan extends"
provides:
  - "Per-strip scroll-to-centered-chip live preview tracking in theme-preview.js, reusing the existing applyPreviewSrc() sink"
  - "A mutation-tested browser check proving the preview follows the geometrically centered chip (not merely 'a listener exists') across real scroll, and proving scroll never selects"
affects: [companion-theme-carousel, companion-static-js]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "IntersectionObserver used as an optional cheap trigger, always guarded by window.IntersectionObserver, with the actual 'centered' decision computed by an independent nearest-centre getBoundingClientRect comparison so the observer's own threshold never becomes the definition"
    - "A CSS class + its own dot-selector prefix are always split into two separate JS constants (freshness.js's FADE_IMAGE_CLASS/FADE_IMAGE_SELECTOR idiom) so neither literal alone trips the JS-side i18n fallback-literal scanner"

key-files:
  created: []
  modified:
    - companion/static/theme-preview.js
    - companion/test_browser_ux.py

key-decisions:
  - "No config_page.py change was needed: each carousel strip already carries its own strip_id as its element id plus the theme-chip-grid--strip modifier class (27-07's own per-instance discipline) — an addressable per-instance hook already existed, so the plan's conditional 'add one data attribute' fallback was not exercised."
  - "The dedicated cross-instance isolation clause is caught alongside (not instead of) the per-strip loop's own relationship assertion under mutation M-D, because in this implementation a genuinely shared/keyed-wrong tracker breaks an individual strip's own centered-chip-to-preview relationship first — that per-strip assertion is itself a per-instance isolation proof."

patterns-established:
  - "Preview-follows-scroll pattern: one tracker built per DOM instance inside a loop over a shared modifier-class selector, never a hardcoded id list — the same shape the existing pager wiring already uses."

requirements-completed: [CFG-75]

duration: 44min
completed: 2026-09-16
---

# Phase 28 Plan 5: Theme carousel preview follows scroll Summary

**While scrolling a theme carousel strip, the live preview now follows the geometrically centered chip (a per-strip IntersectionObserver-assisted tracker calling the existing `applyPreviewSrc()` sink), proven across four real intermediate scroll positions per strip in both UI themes, with a mutation-tested browser check that a reload always still shows the SAVED theme, never a scrolled-past one.**

## Performance

- **Duration:** 44 min
- **Started:** 2026-09-16T06:32:50Z (Task 1 commit)
- **Completed:** 2026-09-16T07:16:53Z (fix commit)
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `companion/static/theme-preview.js` gained a per-strip, per-instance scroll-preview tracker: each of the three carousel strips (departures, arrivals, calendar) gets its own tracker built in a loop over `.theme-chip-grid--strip`, computing the geometrically centered chip via nearest-centre `getBoundingClientRect()` arithmetic and calling the existing `applyPreviewSrc()` sink — never touching a radio's checked state or dispatching a `change` event
- A new mutation-tested browser check (`companion/test_browser_ux.py`) proves the preview matches the centered chip across four real intermediate scroll positions per strip, in both UI themes at the 360px floor, and proves scroll never selects (radio-state snapshot, reload shows the SAVED theme) plus one cross-instance isolation clause
- `EXPECTED_CHECK_COUNT` re-derived by running: 91 → 92

## Task Commits

Each task was committed atomically:

1. **Task 1: Per-strip centered-chip tracking, wired to the sink that already exists** - `d548abd` (feat)
2. **Task 2: THE check — the preview matched to the centered chip across real intermediate scroll positions** - `d3d8575` (test)
3. **Fix: split the strip class from its dot-selector prefix** - `e9c4294` (fix, found during Task 2's own full-suite verification)

## Files Created/Modified
- `companion/static/theme-preview.js` - per-strip `makeScrollPreviewTracker()`, `nearestCenteredChip()`, `stripPanelIsCollapsed()`; hoisted `COLLAPSED_PANEL_CLASS` out of `showUsage()` so both share one literal; header comment amended to name this plan and reconfirm the "only DOM writes" contract
- `companion/test_browser_ux.py` - `_scrolling_a_strip_moves_its_own_preview_to_the_centered_chip_and_selects_nothing`, `EXPECTED_CHECK_COUNT` 91 → 92

## Decisions Made
- No `config_page.py` change: each strip's existing `id` (its own `strip_id`) plus the `theme-chip-grid--strip` class already form an addressable per-instance hook — the plan's own conditional "add ONE data attribute" fallback was investigated and found unnecessary.
- IntersectionObserver is used as an optional, guarded cheap trigger; the actual "centered" decision is always the independent nearest-centre computation, so the observer's own threshold configuration is never load-bearing for correctness — matching CONTEXT.md's Claude's-Discretion allowance.
- The dedicated trailing "cross-instance isolation" clause is real and mutation-tested (M-D), but in this implementation a shared/keyed-wrong tracker construction necessarily also breaks the earlier per-strip relationship assertion for the affected strip first (verified twice: the real check fails at the arrivals per-strip clause under M-D, and a standalone diagnostic — not committed, scratch-only — confirmed the same shared-tracker construction also degrades departures' own scroll reliability via duplicate listener/observer registration). The per-strip loop is itself a valid per-instance isolation proof for this reason; the trailing clause remains additional insurance for the narrower "switch away and back, verify no stale leak" scenario.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Split the strip's CSS class from its own dot-selector prefix**
- **Found during:** Task 2's own full-suite verification (`scripts/run-all-tests.sh`)
- **Issue:** `var STRIP_SELECTOR = ".theme-chip-grid--strip";` is a single string literal beginning with `.`. `companion/test_i18n.py`'s D-08 Check 6 (the JS-side fallback-literal scanner) matches any `var ALL_CAPS = "literal"` shape and excludes it only via a hyphenated-lowercase-identifier regex that never matches a leading dot — so this one literal was flagged as needing a `companion.i18n_fr.CATALOG` entry, which is wrong (it is a CSS selector, not user-facing text).
- **Fix:** Followed `freshness.js`'s own established idiom (`FADE_IMAGE_CLASS` / `FADE_IMAGE_SELECTOR`): split into `STRIP_CLASS = "theme-chip-grid--strip"` (no leading dot, matches the scanner's existing hyphenated-identifier exclusion) and `STRIP_SELECTOR = "." + STRIP_CLASS` (string concatenation, invisible to the scanner's literal-only regex).
- **Files modified:** `companion/static/theme-preview.js`
- **Verification:** `companion/test_i18n.py` 23/24 → 24/24; re-ran the full `scripts/run-all-tests.sh` suite, confirming no other files were affected.
- **Committed in:** `e9c4294`

---

**Total deviations:** 1 auto-fixed (1 Rule 1 bug fix)
**Impact on plan:** The fix is a pure refactor of how one constant is constructed — no behavior change to the shipped tracker, no scope creep.

## Issues Encountered
- One transient/flaky failure was observed on a single `companion/test_browser_ux.py` run: `"a Display page with a typed-but-uncommitted edit issues ZERO requests..."` (23-06-PLAN.md Task 3's leave-guard/freshness-swap check) — unrelated to any file this plan touches. Re-ran the full 92-check suite twice more (both clean 92/92) to confirm it was environment flakiness, not a regression.
- Root-user sandbox caveat (pre-existing, not introduced by this plan): `scripts/run-all-tests.sh` reports 3 failing harnesses unrelated to this plan's files — `server/test_manual_resolutions.py` (2 checks) and 2 checks inside `companion/test_companion_app.py` (`WR-11`'s read-only-state-dir reproduction, defeated because the sandbox runs as root, which bypasses filesystem permission checks) and 1 check inside `companion/test_status_pages.py` (`anomaly_active()` against a non-existent state_dir path, same root-permission class). None of these three harnesses touch `theme-preview.js`, `config_page.py`, or `test_browser_ux.py`.

## Verification Evidence

- `companion/test_config_page.py`: 265/265 pass
- `companion/test_companion_app.py`: 314/316 pass (2 known pre-existing root-sandbox failures, unrelated to this plan)
- `companion/test_i18n.py`: 24/24 pass (after the fix commit)
- `companion/test_browser_ux.py`: 92/92 pass (EXPECTED_CHECK_COUNT re-derived by running: 91 → 92), confirmed clean on two separate full runs
- `ruff check .`: clean
- `scripts/run-all-tests.sh`: FAILED harnesses are exactly `server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — the known root-sandbox baseline, by name, unrelated to this plan's files

### Mutation testing (Task 2's check)

All four mutations applied directly to `companion/static/theme-preview.js`, each run in isolation via a temporary `GSD_ONLY_CHECK` filter added to and then removed from `test_browser_ux.py`'s own `check()` closure (never committed), each reverted with `git checkout-index -f --` before the next:

- **M-A (wiring removed entirely):** FAILED at the FIRST intermediate position, as required. Quoted: `"theme='light' usage='departures' scrollLeft=346 (frac=0.2 of maxScroll=1730), expected chip 'yellow_light': expected the preview to read '/theme-preview/yellow_light.png?live=1', it still reads '/theme-preview/white.png?live=1'"`
- **M-B (always apply the FIRST chip's src — the load-bearing mutation):** FAILED. Quoted: `"theme='light' usage='departures' scrollLeft=346 (frac=0.2 of maxScroll=1730), expected chip 'yellow_light': expected the preview to read '/theme-preview/yellow_light.png?live=1', it still reads '/theme-preview/white.png?live=1'"` — distinct from M-A's mechanism (a listener IS attached and DOES fire, it just always picks the wrong chip), proving the check asserts the centered-chip relationship rather than merely that a scroll listener exists.
- **M-C (also set `input.checked = true` on the centered chip):** FAILED, caught specifically by the checked-state snapshot clause. Quoted: `"theme='light' usage='departures': scrolling changed a radio's checked state: {'theme::white': (True, False), 'theme::band_blue_field': (False, True)} — scroll must never select"`
- **M-D (all three strips' trackers keyed to a single shared strip):** FAILED, caught at the per-strip relationship clause for the arrivals strip (whose scroll listener, under this mutation, is attached to departures' own strip instead, so arrivals' scroll never updates its own preview). Quoted: `"theme='light' usage='arrivals' scrollLeft=375 (frac=0.2 of maxScroll=1873), expected chip 'yellow': expected the preview to read '/theme-preview/yellow.png?live=1', it still reads '/theme-preview/black.png?live=1'"`. A standalone (uncommitted, scratch-only) diagnostic further confirmed the same shared-tracker construction also degrades departures' own scroll reliability via redundant duplicate listener/observer registration — the mutation is unambiguously caught, though by the per-strip relationship assertion rather than the dedicated trailing cross-instance clause specifically (see Decisions Made above for why this implementation's structure makes that the natural catch point).
- Every mutation reverted with `git checkout-index -f --`; `git status --porcelain` was clean before each subsequent commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- CFG-75 fully shipped: scroll-follows-centered-chip preview on all three carousels, mutation-tested, with no regression to 27-07's per-instance discipline or the existing crossfade/selection mechanics.
- No blockers for the remaining Phase 28 plans.

## Self-Check: PASSED

- FOUND: companion/static/theme-preview.js
- FOUND: companion/test_browser_ux.py
- FOUND: .planning/phases/28-companion-review-feedback-round-2-five-more-findings-from-th/28-05-SUMMARY.md
- FOUND: d548abd (feat, Task 1)
- FOUND: d3d8575 (test, Task 2)
- FOUND: e9c4294 (fix, i18n scanner deviation)

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Completed: 2026-09-16*
