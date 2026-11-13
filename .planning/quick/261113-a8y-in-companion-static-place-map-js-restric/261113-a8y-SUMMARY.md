---
phase: quick-261113-a8y
plan: 01
subsystem: ui
tags: [companion, playwright, css, navigator.standalone, contrast, ios]

requires:
  - phase: debug/map-fills-header-footer
    provides: the ungated lead/tail/scroll-lock/nudge on every phone browser, and the lead-qualified light-palette ink, that this plan narrows
provides:
  - leadUnderStatusBar() in place-map.js gated on navigator.standalone existing (iOS Safari/WebKit only)
  - Browser tests split into an IPHONE subset (lead, no-hand-scroll, nudge) and an other-browser subset (no lead, no scroll lock, window-exact span)
  - Light-palette ink on the brand and the frame button decoupled from .place-lead, applying on every phone browser
  - Render baseline regenerated (style-place.css hash only)
affects: [companion-location-page, companion-ui-contrast]

actuals:
  tokens: 64087
  tasks: 3
  commits: 2
  plan_head_before: a235b1b8eafe79401b7e5c4af86397aac0070d16
  plan_head_after: afb8edadbf071cdc9d60be10ef26c466ef1c635b

tech-stack:
  added: []
  patterns:
    - "navigator.standalone existence (not its false/true value) gates iOS-only browser behaviour"
    - "CSS ink/contrast rules decoupled from a layout-only state class so they apply regardless of that class"

key-files:
  created: []
  modified:
    - companion/static/place-map.js
    - companion/static/style-place.css
    - companion/test_browser_place_document_map.py
    - companion/test_browser_location_full_bleed.py
    - companion/test_browser_place_boot.py
    - companion/test_browser_place_sheet.py
    - companion/testdata/render_baseline.json
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-UI-SPEC.md

key-decisions:
  - "leadUnderStatusBar() returns early only when typeof window.navigator.standalone === \"undefined\" — nothing else in the function changed"
  - "The light-palette ink selectors lost their .place-lead qualifier (ink values unchanged) so every phone browser, not just iOS, gets readable contrast over the map"

requirements-completed: [QUICK-261113-a8y]

coverage:
  - id: D1
    description: "leadUnderStatusBar() gates the lead/tail/scroll-lock/settle-back/nudge on navigator.standalone existing, so only an iPhone Safari tab or Home Screen web app gets them"
    requirement: QUICK-261113-a8y
    verification:
      - kind: e2e
        ref: "companion/test_browser_place_document_map.py::test_the_page_starts_scrolled_past_a_lead_of_map_under_the_status_bar[IPHONE]"
        status: pass
      - kind: e2e
        ref: "companion/test_browser_place_document_map.py::test_a_browser_without_navigator_standalone_gets_no_lead"
        status: pass
      - kind: e2e
        ref: "companion/test_browser_place_document_map.py::test_a_browser_without_navigator_standalone_never_scrolls_or_nudges"
        status: pass
    human_judgment: false
  - id: D2
    description: "The wordmark, frame-button name and logo keep WCAG AA contrast over the bare map in every browser and both themes, independent of the lead"
    requirement: QUICK-261113-a8y
    verification:
      - kind: e2e
        ref: "companion/test_browser_place_document_map.py::test_the_app_bar_reads_on_the_map_in_both_themes[client x theme, 6 cases]"
        status: pass
    human_judgment: false
  - id: D3
    description: "On a real iPhone (Safari tab and Home Screen app) and a real Android Chrome phone, the behaviour matches the spec"
    verification: []
    human_judgment: true
    rationale: "Requires real-device touch/scroll behaviour and the device's own toolbar-hiding animation, which an automated browser cannot reproduce — human_verify_mode is end-of-phase, so this is surfaced here rather than as a mid-plan checkpoint"

duration: 55min
completed: 2026-11-13
status: complete
---

# Phase quick-261113-a8y Plan 01: Scope the status-bar lead to iOS Summary

**Gated place-map.js's status-bar lead on `navigator.standalone` existing (iOS Safari/WebKit only), so Android Chrome and other phone browsers keep their own toolbar-hiding scroll instead of a forced scroll lock; decoupled the light-palette app-bar ink from the lead class so it still reads on every phone.**

## Performance

- **Duration:** 55 min
- **Started:** 2026-11-13 (session start)
- **Completed:** 2026-11-13
- **Tasks:** 3/3 completed
- **Files modified:** 8

## Accomplishments
- `leadUnderStatusBar()` in `companion/static/place-map.js` now returns immediately when `typeof window.navigator.standalone === "undefined"`, so the lead/tail, scroll lock, settle-back and post-splash nudge apply only on an iPhone (a Safari tab or a Home Screen web app); every other phone browser is laid out and scrolls exactly as it would with no lead at all.
- `companion/test_browser_place_document_map.py` tests now split into an `IPHONE` subset (`safari-tab`, `home-screen-app`) that keeps every lead/tail/no-hand-scroll/nudge assertion from commit 16159b85, and two new `other-browser` tests proving no lead, no scroll lock (`overflow` not `hidden`, `scrollRestoration` stays `auto`), and no scroll at all through and past the opening splash.
- The window-exact-span test, and the three other Location browser test files (`test_browser_location_full_bleed.py`, `test_browser_place_boot.py`, `test_browser_place_sheet.py`), are back to their pre-16159b85 no-lead expectations (verified byte-identical to `16159b85^` except for one plan-directed docstring wording).
- `companion/static/style-place.css`'s light-palette ink block (brand + frame-button selectors) lost its `.place-lead` qualifier — same token values, now applying on every phone browser in both themes — and the contrast test (`test_the_app_bar_reads_on_the_map_in_both_themes`) now runs over all three clients, not just an iPhone's.
- Render baseline regenerated; the only change across the whole file is the `style-place.css` cache-busting hash (4 occurrences, confirmed via diff against the pre-plan HEAD).
- `.planning/workstreams/.../61-UI-SPEC.md` records the owner's narrowing decision as a new dated revision paragraph.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate the lead on navigator.standalone existing, and split the browser tests into iPhone and other-browser expectations** - `32c55115` (fix)
2. **Task 2: Keep the light-palette ink on every phone browser, and prove it in the contrast test** - `afb8edad` (fix)
3. **Task 3: Regression over every Location browser test, mutation proofs, lint** - no commit (no file changed; the regression run found nothing this plan broke)

## Files Created/Modified
- `companion/static/place-map.js` - `leadUnderStatusBar()` gated on `navigator.standalone` existing; comments above the function and `LEAD_CLASS` rewritten to describe the iOS-only gate
- `companion/static/style-place.css` - `.place-lead` qualifier dropped from the two light-palette ink selectors; comments above the lead rule and the ink block updated
- `companion/test_browser_place_document_map.py` - `IPHONE` constant added; three existing tests re-parametrized onto it; two new other-browser tests added; nudge-test context setup extracted into `_frames_through_the_splash()`; spanning test asserts the window-exact span; contrast test now runs over all three clients
- `companion/test_browser_location_full_bleed.py` - contrast probe and assertion restored to pre-16159b85 (bg/pos/top/bottom only)
- `companion/test_browser_place_boot.py` - `overflow` field and its "hidden" assertion removed from the page_colours probe; kept the existing `PAGE_OVERFLOW` assertion
- `companion/test_browser_place_sheet.py` - map-box assertion restored to the window-exact `y == 0`, `height == VIEWPORT_PHONE["height"]`
- `companion/testdata/render_baseline.json` - regenerated; only the `style-place.css?v=` hash moved (4 occurrences)
- `.planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-UI-SPEC.md` - one new "Revision (owner decision, 2026-11-13)" paragraph

## Decisions Made
- The gate reads `typeof window.navigator.standalone === "undefined"` rather than any `!== false`/`!== true` check, so a Safari tab (`false`) and a Home Screen web app (`true`) both keep the lead, and only browsers that never define the property lose it.
- The ink block's selector lost its `.place-lead` qualifier instead of adding a second unqualified copy, keeping one rule and one set of token values for every phone, per the plan's explicit instruction.

## Deviations from Plan

None - plan executed exactly as written. The one necessary consequence flagged in the plan's objective (dropping `.place-lead` from the ink selectors) was itself the content of Task 2, not an unplanned deviation.

## Issues Encountered
- The shared `/Users/florian/Projects/skypane/server/.venv` was missing `pytest-xdist`, `pytest-playwright`, `pytest-cov`, `mypy` and others even though `server/requirements-dev.txt` lists them with pinned hashes (the venv had drifted since a prior session). Reinstalled from the existing hash-locked lockfile (`pip install -r server/requirements-dev.txt`) before any test could run; no new or different packages were introduced, only the already-committed lockfile's exact pinned versions.
- Two tests failed only under `-n auto` parallel load (`test_the_floating_parts_keep_their_places_over_the_document_map[chromium-390-light]` and `test_the_phone_map_is_document_content_spanning_the_window[chromium-360-light]`, both `Page.wait_for_function` timeouts in `_open_ready`) but passed immediately when re-run standalone; dismissed as machine-load flakiness, not a plan regression.
- The full 23-file + baseline regression run (Task 3) showed 27 failures: 24 are the known font-serialisation mismatch (`-apple-system, "system-ui", ...` vs `-apple-system, BlinkMacSystemFont, ...`) in `test_browser_foundations.py::test_titles_are_on_the_type_scale_in_the_display_face`, documented in `.planning/debug/resolved/map-fills-header-footer.md` ("24 known font-serialisation cases... also seen on an untouched HEAD"); the other 3 (`test_the_pin_readout_follows_the_pin_in_both_languages`, `test_a_refresh_keeps_every_picture_action_working`, `test_keying_the_palette_moves_the_preview`) are unrelated to the Location page and this plan's files. `test_a_refresh_keeps_every_picture_action_working` was confirmed by swapping in the pre-plan `place-map.js`/`style-place.css` (via `git show a235b1b8:<path>`) and re-running: it still failed under parallel load and passed standalone with both the base and the current files, confirming a pre-existing timing flake, not a regression from this plan. No fix was needed; no file in this list was touched.

## Mutation Proofs (Task 3)

All three mutations turned their target tests red, confirming the new checks are non-vacuous:

- **M1 (ungated, today's-HEAD behaviour):** deleted the early return in `leadUnderStatusBar()`. Ran `-k "without_navigator_standalone or document_content_spanning"` on `test_browser_place_document_map.py` (9 of 9 collected failed) plus full runs of `test_browser_place_sheet.py` and `test_browser_location_full_bleed.py` (5 of 20 failed, all in the two tests this plan restored to no-lead expectations). 14 failures total.
- **M2 (the old tab-only gate):** changed the condition to `window.navigator.standalone !== false`. Ran `-k "home-screen-app"` on the document-map file: all 6 lead/no-hand-scroll/nudge cases for `home-screen-app` failed; the contrast case for `home-screen-app` passed, as the plan anticipated.
- **M3 (ink scoped to the lead again):** restored the `.place-lead` qualifier on the two ink selectors in `style-place.css`. Ran `-k "reads_on_the_map and other-browser and dark"`: failed (worst contrast 1.44 vs the required 4.5).

All three mutations were applied via scratchpad backup/restore and reverted immediately after their check; `git status --porcelain` showed a clean tree (only the untracked quick-task planning directory) after each.

## User Setup Required

None - no external service configuration required.

## Human Verification Required

`human_verify_mode` is `end-of-phase`, so this is recorded here rather than as a mid-plan checkpoint. Owner, on real devices:
- **(a) iPhone, Safari tab and Home Screen app, light and dark theme:** behaviour unchanged from commit `16159b85` — the map sits under the clock, the page does not drag from the sheet.
- **(b) Android Chrome phone, Location page:** scrolling hides and shows the address bar exactly as on any other page, the page never jumps back to a lead, and in the dark theme the SkyPane wordmark and the frame button read clearly over the map.

## Next Phase Readiness
This is a standalone quick task; no next phase depends on it. The companion Location page's status-bar handling is now iOS-scoped and the ink contrast is browser-independent, both verified by an expanded automated test suite with confirmed non-vacuous mutation coverage.

---
*Phase: quick-261113-a8y*
*Completed: 2026-11-13*

## Self-Check: PASSED

All 8 listed files found on disk; both task commits (`32c55115`, `afb8edad`) confirmed as ancestors of HEAD.
