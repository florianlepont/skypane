---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 02
subsystem: ui
tags: [css, specificity, playwright, browser-testing, mutation-testing]

# Dependency graph
requires:
  - phase: 27
    provides: "27-02's quiet-dial cross-surface pair seam (arc/handles/caption agreement), left untouched by this plan"
provides:
  - "The quiet-dial handle's own polar transform survives a full press — a CSS specificity fix (button:not(.value-control__handle):active) rather than a maths fix, since the angle/pointer arithmetic was already correct"
  - "transform removed from .value-control__handle's transition list, so the handle's position tracks --value-fraction instantly instead of lerping through the chord on every value change"
  - "A measured (not assumed) finding: the wake-interval control is a native <input type=\"range\">, not a .value-control__handle consumer — CONTEXT.md/ROADMAP.md's 'apply the identical fix to the wake-interval slider' clause does not apply structurally"
  - "The project's first browser check that SAMPLES a resolved position continuously across a held press, rather than asserting only before/after"
affects: [28-03, 28-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS specificity collision fixed by excluding the narrower, more specific consumer via :not() at the SHARED class level, rather than a counter-declaration or a source-order fight — covers any future consumer of the shared class by construction"
    - "A position derived from a live value is excluded from `transition` on principle, not only for this bug: easing a value's own representation means the control visibly holds a position it does not actually have for the transition's duration"
    - "Browser-level geometry sampling via one page.evaluate() running a requestAnimationFrame loop across a held press, returning the full sample array in one round trip rather than polling from Python (which would widen exactly the frame-timed gaps the bug hides in)"

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/test_browser_ux.py

key-decisions:
  - "Fixed via `button:not(.value-control__handle):active` (the `:not()` option CONTEXT.md itself named) rather than a counter-declaration on `.quiet-dial__handle` — the exclusion is written against the SHARED `.value-control__handle` class, so it protects any future second consumer by construction rather than by a list someone has to maintain"
  - "`transform` removed from `.value-control__handle`'s own transition list (not from the base `button` rule, which every other button still uses) — argued as a correctness-of-representation change: a handle's polar position is a REPRESENTATION OF A VALUE, not an affordance that should ease anywhere"
  - "The wake-interval clause discharged by measurement rather than by writing a matching wake-side CSS change: grepping companion/pages/*.py, companion/layout.py and companion/static/*.js for value-control__handle/VALUE_CONTROL_HANDLE finds exactly ONE consumer (config_page.py:2980, the quiet-dial handle). style.css's own long comment above `.wake-slider__input` (~line 1552) states explicitly the wake-interval control is a native `<input type=\"range\">` and DELIBERATELY does not wear `.value-control` because 'a native range has no such handle to contain'. CONTEXT.md/ROADMAP.md's claim that the wake-interval slider shares '.value-control__handle/button base, same collision' does not hold structurally today — corrected here in writing rather than silently invented around"

requirements-completed: [CFG-73]

# Metrics
duration: 55min
completed: 2026-09-15
---

# Phase 28 Plan 02: Quiet-dial handle collapse (CFG-73 Bug B) Summary

**Fixed the quiet-hours dial handle collapsing to the dial's centre mid-press via a `button:not(.value-control__handle):active` specificity exclusion plus dropping `transform` from the handle's own transition, proven by a new browser check that samples the handle's resolved ring distance ≥10 times across a ≥400ms held press rather than only before/after.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-09-15T19:21Z (approx, first task commit)
- **Completed:** 2026-09-15T20:16Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- `.quiet-dial__handle` (and by construction, every future consumer of `.value-control__handle`) keeps its own polar positioning transform for the full duration of a press — the generic `button:active { transform: translateY(1px); }` rule no longer wholesale-replaces it
- `transform` is no longer a transitioned property on `.value-control__handle`, so its position now tracks `--value-fraction` instantly instead of lerping through the dial's chord toward the centre and back
- The wake-interval clause in CONTEXT.md/ROADMAP.md ("apply the identical fix to the wake-interval slider") was measured rather than assumed, and found not to apply: the wake-interval control is a native `<input type="range">`, confirmed by both a grep of every `.value-control__handle` consumer in the codebase (exactly one: the quiet-dial handle) and style.css's own pre-existing comment stating the design intent
- Shipped the project's first browser check that samples a resolved geometric relationship continuously across a time window (a held press) rather than only at its two endpoints — the exact "assert relationships, not just endpoints" contract this project's own SKILL.md names, applied to a time axis
- Mutation-tested the new check on three axes (selector reverted, transition reverted, sampling reduced to endpoints-only) and quoted every result

## Task Commits

Each task was committed atomically:

1. **Task 1: The handle keeps its own transform while pressed, and stops lerping** - `323b9f2` (fix)
2. **Task 2: THE check — the handle's radius sampled THROUGHOUT a held press** - `085e54b` (test)

_No separate plan-metadata commit yet — see the self-check note below; STATE.md/ROADMAP.md are intentionally not touched by this worktree agent (orchestrator owns them after the wave)._

## Files Created/Modified

- `companion/static/style.css` — `button:active` narrowed to `button:not(.value-control__handle):active` (with an extended comment naming CFG-73, the measured symptom, and the specificity argument); `.value-control__handle` gained its own `transition:` declaration (`background-color`, `border-color`, `color`, `box-shadow` — no `transform`) with a comment arguing the correctness-of-representation reasoning
- `companion/test_browser_ux.py` — new check `_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press()`, `EXPECTED_CHECK_COUNT` 88 → 89 (re-derived by running, 89/89)

## Decisions Made

- **Fix mechanism:** `:not(.value-control__handle)` on the generic `button:active` rule, in place, never moved — its own comment records it must stay before `button:disabled`, and that ordering is unchanged. This is the option CONTEXT.md itself named as the sanctioned fix direction, chosen over a counter-declaration because it fixes the collision at its source and covers any future second consumer of the shared class automatically.
- **Transition mechanism:** dropped `transform` from `.value-control__handle`'s new `transition:` declaration rather than from the base `button` rule — every other button in the app keeps easing its 1px depress; only the handle's own polar position stops lerping, because that position represents a value rather than affording a button press.
- **Wake-interval clause:** discharged by measurement rather than assumption. Evidence: `grep -rn 'value-control__handle\|VALUE_CONTROL_HANDLE' companion/pages/*.py companion/layout.py companion/static/*.js` returns exactly:
  ```
  companion/pages/config_page.py:2980:  '<button type="button" class="value-control__handle control-hit-area %s" %s'
  companion/pages/config_page.py:3003:  escape_html(QUIET_DIAL_HANDLE_CLASS), layout.VALUE_CONTROL_HANDLE_ATTR,
  companion/layout.py:271:VALUE_CONTROL_HANDLE_ATTR = "data-value-handle"
  ```
  One HTML-emitting consumer, and it is the quiet-dial handle. `companion/static/style.css`'s own pre-existing comment above `.wake-slider__input` (~line 1552-1585) states: *"TWO DECLARATIONS, AND THE SHORTNESS OF THIS BLOCK IS THE POINT. The control is a NATIVE `<input type="range">`... IT DELIBERATELY DOES NOT WEAR `.value-control`... A native range has no such handle to contain, and `touch-action: none` on an ancestor of one would be this plan taking a position on a gesture the browser already implements... (Recorded rather than left silent: a later reader will notice the phase's other control uses the shared class and wonder.)"* The wake-interval selectors used throughout `test_browser_ux.py` (`WAKE_SLIDER_SEL = ".wake-slider"`, `WAKE_RANGE_SEL = ".wake-slider__input"`, `WAKE_NUMBER_SEL = 'input[name="wake_interval_s"]'`) confirm no `[data-value-handle]`/`.value-control__handle` selector is ever used for the wake control anywhere in the test suite either.
  **Correction of source-artifact claims:** `28-CONTEXT.md` line 33 states *"Apply the identical fix to the wake-interval slider's handle — same shared `.value-control__handle`/`button` base, same collision, confirmed by the investigating agent as a live risk there too"*, and `ROADMAP.md` lines 1331/1341 restate the same claim ("Same shared base class affects the wake-interval slider's handle too" / "Apply the same handle fix to the wake-interval slider"). This plan's own measurement disagrees: the wake-interval slider is a native range input with no button, no `.value-control__handle`, and no `button:active` collision is structurally possible on it — there is nothing there for `button:not(.value-control__handle):active` to exclude or fail to exclude. Per the plan's own instruction this correction is recorded here in the SUMMARY (a source artifact) rather than silently invented around with a no-op wake-side CSS edit; `28-CONTEXT.md`/`ROADMAP.md` themselves are outside this plan's `files_owned` boundary and are left for the phase owner to reconcile. The requirement's *intent* is satisfied structurally regardless: the fix is declared on the shared `.value-control__handle` class, so the moment any future control (wake-interval or otherwise) grows a real `.value-control__handle` button, it inherits this fix with zero further changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `windowMs` gating measured off the wrong timestamp during check construction**
- **Found during:** Task 2, first full-suite run of the new check
- **Issue:** The sampling loop's `windowMs` gate (`>= 400`) was computed from the LAST sample's own `t` value, but that timestamp is necessarily captured BEFORE the loop's own exit condition is re-tested (sample pushed, one more frame awaited, THEN condition checked) — so the last sample's `t` is always at least one animation frame short of the loop's true elapsed time. This made a structurally-correct 400ms hold fail its own "at least 400ms" self-check (observed: 395.3ms).
- **Fix:** The JS sampler now measures `windowMs = performance.now() - t0` AFTER the `while` loop exits, and the Python side gates on that value instead of `samples[-1]["t"]`.
- **Files modified:** companion/test_browser_ux.py
- **Verification:** Re-ran the full suite; the check passed with the corrected timing measurement.
- **Committed in:** 085e54b (Task 2 commit; fixed before commit, so no separate commit needed)

**2. [Rule 1 - Bug] Redundant `_set_window()` call inside the per-theme loop caused a save-status timeout**
- **Found during:** Task 2, second full-suite run (after fixing deviation #1)
- **Issue:** The check called `_set_window(page, base_url, "23:00", "07:00")` at the top of EACH theme-loop iteration, mirroring the neighbouring drag/preset checks' pattern. But unlike those checks, a plain press-and-hold with no drag changes NOTHING (that is this check's own value-identity clause) — so by the second theme iteration the fields already held exactly "23:00"/"07:00" from the first iteration, and re-submitting the identical values gave dirty-state.js nothing new to save. The save-status region never made a fresh "saved" transition, and `_wait_for_saved()` (a `page.wait_for_function` with a 5000ms timeout) timed out waiting for one that was never coming.
- **Fix:** Moved the single `_set_window(...)` call outside the `for theme in UI_THEMES_EXPLICIT:` loop (set once, before the loop), with a comment explaining why this check's own no-value-change contract makes the neighbouring checks' per-iteration pattern wrong here.
- **Files modified:** companion/test_browser_ux.py
- **Verification:** Re-ran the full suite three consecutive times with no contention from the sibling worktree; 89/89 every time.
- **Committed in:** 085e54b (Task 2 commit; fixed before commit)

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs found and fixed during this plan's own check construction, before the task was committed; neither touched any file outside Task 2's own scope)
**Impact on plan:** Both fixes were necessary for the new check to be correct and non-flaky. No scope creep — both are inside `companion/test_browser_ux.py`, the file Task 2 owns.

## Mutation Testing (Task 2 acceptance criterion)

All three mutations were applied to files already committed at HEAD, run against the full 89-check suite, and reverted before the next mutation. `git status --porcelain` was clean between every step (confirmed via `git checkout-index -f --` for the style.css mutations, and a full pre-mutation backup copy for the test-file mutation since Task 2 was not yet committed when M-C ran).

- **M-A (load-bearing — proves the check can see the original bug at all):** Reverted the Task 1 selector fix (`button:not(.value-control__handle):active` → bare `button:active`). Result: **FAIL**, quoted verbatim:
  > `light: sample #0 (of 25, at 0.0ms into the press) resolved 16.28px from the dial's centre; the ring radius is 78.00px and the stated tolerance is 4.00px — the handle left its ring DURING the press, which is exactly the collapse toward the centre the pre-fix stylesheet produced`

- **M-B (honest finding, not a failure of the plan):** Kept the selector fix, restored `transform` to `.value-control__handle`'s transition list. Result: **still PASSES** (89/89). This is the expected, argued outcome: a plain press-and-hold with no drag never changes `--value-fraction`, so there is nothing for a `transform` transition to animate regardless of whether it is declared — the transition removal is a correctness-of-representation change (a handle must not draw a position the control does not hold, e.g. during a real value change from a drag or keypress), not a defect this particular check — which only holds a static value — can observe.

- **M-C (the phase's own lesson, made executable):** Rewrote the check to discard all mid-press sampling, keeping only a rest-state reading (before any press) and a post-release reading (with natural `page.wait_for_timeout()` latency, no polling), then re-applied M-A's broken selector. Result: **PASSES** (89/89) against the SAME broken stylesheet that M-A correctly caught — demonstrating precisely why an endpoint-only assertion is insufficient: the position is correct at rest and recovers after release, so a before/after check cannot see the mid-press collapse at all. Reverted by restoring `companion/test_browser_ux.py` from a pre-mutation backup copy (the file was not yet committed, so `git checkout-index` was not applicable for this one).

All mutations reverted; `git diff` against the final Task 2 commit shows zero residual changes from any mutation.

## Issues Encountered

CPU contention with the sibling 28-01 worktree (both running Playwright/Chromium-backed test suites in parallel) caused one transient, unrelated check failure (`a Display page with a typed-but-uncommitted edit issues ZERO requests...`) on a single run — confirmed as environmental (a `test_companion_app.py` process from the sibling worktree was observed running concurrently via `ps aux`) rather than caused by this plan's changes, since a subsequent run with no sibling process active passed cleanly and the failure never recurred.

## Next Phase Readiness

- CFG-73 Bug B (handle collapse) is closed. CFG-73 Bug A (the readout's HH:MM format and live duration) remains 28-03's, in different files (`quiet_dial_readout_html()`, `value-controls.js`, `paintReadouts()`, `_quiet_caption_minutes()`) — none of them were touched by this plan.
- 27-02's cross-surface pair seam (`_assert_surfaces_agree`, `_quiet_arc_minutes`, `_quiet_caption_minutes`, `_fraction_pair_minutes`) is confirmed untouched by `git diff`.
- `@keyframes`/`@supports selector(:has(*))`/`prefers-reduced-motion`/`interpolate-size`\`calc-size(` counts in `companion/static/style.css` are unmoved (verified by BEFORE/AFTER grep pairs against the file this plan edits, per the plan's own instruction not to run `companion/test_companion_app.py` since 28-01 owns it this wave):
  - `^@keyframes`: 4 → 4
  - `prefers-reduced-motion`: 8 → 8
  - `@supports selector(:has(*)) {`: 1 → 1
  - `interpolate-size|calc-size\(`: 2 → 2 (pre-existing comment mentions of the banned properties by name, unrelated to and unmoved by this plan's edits)
- `28-CONTEXT.md`/`ROADMAP.md`'s wake-interval claim is corrected here in writing (see Decisions Made above) but the source files themselves are unedited, being outside this plan's `files_owned` boundary — the phase owner (28-07's closing sweep, or whichever plan reconciles CONTEXT.md/ROADMAP.md) should fold this correction in.
- `<human-check>` from the plan's own verification section (press-and-hold on real hardware, drag, ordinary button depress) is not automatable and remains open for end-of-phase human verification per `human_verify_mode: end-of-phase` in `.planning/config.json`.

## Self-Check: PASSED

- `companion/static/style.css` — FOUND (modified, committed at 323b9f2)
- `companion/test_browser_ux.py` — FOUND (modified, committed at 085e54b)
- Commit `323b9f2` — FOUND in `git log --oneline --all`
- Commit `085e54b` — FOUND in `git log --oneline --all`
- `git status --porcelain` clean at time of writing (no mutation residue)

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Completed: 2026-09-15*
