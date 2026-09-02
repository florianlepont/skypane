---
phase: quick-260902-v2v
plan: 260902-v2v
subsystem: ui
tags: [css, flexbox, health-page, airlines-page, config-page, sentence-case]

# Dependency graph
requires:
  - phase: 06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi
    provides: 06.6.4.1-UI-REVIEW.md's 19-finding audit, including UIR-03 (BLOCKER), UIR-07, UIR-12, UIR-13, UIR-15
provides:
  - "Health anomaly banner no longer overflows a 375px viewport (.banner flex-wrap + .banner__label nowrap + .banner__pill min-width: 0)"
  - "Airlines illustrations render at their true aspect ratio instead of a flat letterboxed 263px box (.airline-card__image height: auto)"
  - "Battery trend heading's em dash carries a leading space in both the DOM text and the raw HTML"
  - "Resolution-statistics Source column no longer wraps at desktop widths (.data-table--prose first-column nowrap)"
  - "All companion UI button copy is sentence case (login submit, both poll-trigger states, no-JS save fallback)"
affects: [sketch-findings-skypane]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "CSS source-order-dependent rules (equal-specificity overrides) get a harness check that pins both the declaration AND its index() position relative to the rule it depends on — .data-table--prose's first-child nowrap rule follows this precedent."

key-files:
  created: []
  modified:
    - companion/static/style.css
    - companion/pages/health_page.py
    - companion/pages/config_page.py
    - companion/app.py
    - companion/test_status_pages.py
    - companion/test_config_page.py
    - companion/test_contrast_check.py

key-decisions:
  - "UIR-12 fixed via a markup space (leading space inside the caption span), not the CSS margin alternative the review also proposed — a CSS margin would leave the accessible name glued for a screen reader, and test_status_pages.py:2416 locates the base .section-caption rule by an index()-based substring search that a new h2 > .section-caption rule placed earlier in the file would collide with."
  - "The .banner__pill / .airline-card__chip declaration-identity comment was rewritten rather than deleted — the two rules still share every other declaration; the comment now names the one deliberate divergence (min-width: 0) instead of asserting a now-false literal identity."
  - "Airlines_page.py's <img width height> attributes were left untouched — height: auto lets aspect-ratio compute the box while the attributes still reserve space for loading=\"lazy\", exactly as the review's own fix note specified."

requirements-completed: [QUICK-260902-v2v]

coverage:
  - id: D1
    description: "UIR-03 (BLOCKER): Health anomaly banner no longer overflows a 375px viewport — .banner wraps, .banner__label prevents the lead phrase from breaking mid-word, .banner__pill can shrink via min-width: 0"
    requirement: QUICK-260902-v2v
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#the four UIR-03/07/12/13 one-line fixes hold together"
        status: pass
      - kind: automated_ui
        ref: "real 375px browser scrollWidth + banner__pill right-edge measurement"
        status: unknown
    human_judgment: true
    rationale: "No browser tool available in this execution; CSS/markup contracts are proven by the harness, but the actual rendered scrollWidth/pill-right-edge numbers at 375px require a real browser measurement, which the orchestrator will perform (see Browser Measurement table below)."
  - id: D2
    description: "UIR-07: Airlines illustrations render at their true aspect ratio (no longer letterboxed to a flat 263px box)"
    requirement: QUICK-260902-v2v
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#the four UIR-03/07/12/13 one-line fixes hold together"
        status: pass
      - kind: automated_ui
        ref: "real browser .airline-card__image / .airline-card getBoundingClientRect() at 375px and 1440px"
        status: unknown
    human_judgment: true
    rationale: "CSS contract (height: auto + surviving aspect-ratio) is proven by the harness; the actual rendered pixel dimensions require a real browser measurement, which the orchestrator will perform."
  - id: D3
    description: "UIR-12: Battery trend heading's em dash carries a leading space in the rendered DOM text and raw HTML"
    requirement: QUICK-260902-v2v
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#the four UIR-03/07/12/13 one-line fixes hold together"
        status: pass
    human_judgment: false
  - id: D4
    description: "UIR-13: Resolution-statistics Source column no longer wraps at desktop widths, with the new rule placed after .data-table--prose in source order"
    requirement: QUICK-260902-v2v
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#the four UIR-03/07/12/13 one-line fixes hold together"
        status: pass
    human_judgment: false
  - id: D5
    description: "UIR-15: all three remaining Title Case button labels are sentence case (login submit, both poll-trigger cooldown branches, no-JS save fallback), every harness assertion pinning the old copy retargeted"
    requirement: QUICK-260902-v2v
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (64/64, unchanged count)"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py (108/108)"
        status: pass
      - kind: unit
        ref: "companion/test_contrast_check.py (36/36)"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-v2v: Ship the five one-line UI fixes from 06.6.4.1-UI-REVIEW Summary

**Five one-line fixes shipped: `.banner`/`.banner__pill`/`.banner__label` fix the 375px Health-banner overflow (the review's only BLOCKER), `.airline-card__image` stops letterboxing illustrations, a markup space fixes the glued Battery-trend em dash, a source-ordered `.data-table--prose` rule stops the Source column wrapping, and the three remaining Title Case buttons are now sentence case.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-09-02T20:29:57Z
- **Completed:** 2026-09-02T20:41:21Z
- **Tasks:** 3 (2 code tasks + 1 measurement/verification task)
- **Files modified:** 7 (`companion/static/style.css`, `companion/pages/health_page.py`, `companion/pages/config_page.py`, `companion/app.py`, `companion/test_status_pages.py`, `companion/test_config_page.py`, `companion/test_contrast_check.py`)

## Accomplishments

- Fixed the Health page's only BLOCKER (UIR-03): `.banner` now wraps at narrow viewports, a new `.banner__label` class keeps the count-and-noun lead phrase from breaking mid-word, and `.banner__pill` gains `min-width: 0` so pills can shrink and wrap instead of forcing the row wider than the viewport.
- Fixed the letterboxed Airlines illustrations (UIR-07): `.airline-card__image` gains `height: auto`, letting its existing `aspect-ratio: 900 / 263` actually apply instead of being overridden by the `<img>` element's own resolved `width`/`height` attributes (which stay in the markup for `loading="lazy"` box reservation).
- Fixed the glued em dash in the Battery trend heading (UIR-12) with a one-character markup fix (a leading space inside the caption span), not the CSS-margin alternative the review also proposed — the CSS route would have left the accessible name glued for a screen reader and collided with an existing index()-based harness check.
- Fixed the wrapping Resolution-statistics Source column (UIR-13) with a new `.data-table--prose th:first-child, .data-table--prose td:first-child { white-space: nowrap; }` rule placed immediately after the base `.data-table--prose` rule, preserving the existing source-order contract a harness check already pins.
- Sentence-cased the three remaining Title Case button labels (UIR-15): the login submit button ("Sign In" -> "Sign in"), both poll-trigger cooldown-branch buttons ("Trigger Poll Now" -> "Trigger poll now"), and the no-JS fallback save button ("Save Settings" -> "Save settings", now matching the dirty bar's own button exactly).
- Added one new regression check in `test_status_pages.py` that pins all four UIR-03/07/12/13 fixes together (CSS declarations, CSS source-order, and rendered-markup contracts) so a partial fix cannot satisfy it; `EXPECTED_CHECK_COUNT` moved 112 -> 113.
- Retargeted every harness assertion pinning the old Title Case button copy (`test_config_page.py`'s 7 assertion sites across presence checks, check descriptions, and a regex whose literal tail baked in the button text; `test_contrast_check.py`'s docstring mention) — no checks added or removed, `test_config_page.py` holds at its unchanged 64/64.

## Task Commits

1. **Task 1: Fix the banner overflow, the letterboxed illustrations, the glued em dash and the wrapping Source column** - `84537c8` (fix)
2. **Task 2: Sentence-case the three Title Case button labels** - `083d8a1` (fix)
3. **Task 3: Measure the fixes in a real browser and record before/after numbers** - this SUMMARY.md (no code commit; see Deviations below for why the browser-measurement half was not performed directly)

## Files Created/Modified

- `companion/static/style.css` - `.banner` flex-wrap, new `.banner__label` rule, `.banner__pill` min-width + corrected head comment, `.airline-card__image` height: auto, `.data-table--prose` first-column nowrap rule, three comment updates naming the retired Title Case button labels
- `companion/pages/health_page.py` - `_anomaly_banner_html()`'s lead span now carries `class="banner__label"` (plus an updated docstring paragraph); `_battery_trend_section_html()`'s caption span opens with a space before its em dash
- `companion/pages/config_page.py` - both `poll_trigger_section()` buttons and `render()`'s no-JS fallback save button are sentence case; module docstring and two in-file comments no longer quote the retired Title Case labels
- `companion/app.py` - the login submit button is sentence case ("Sign in")
- `companion/test_status_pages.py` - one new check pinning all four UIR-03/07/12/13 fixes together; `EXPECTED_CHECK_COUNT` 112 -> 113
- `companion/test_config_page.py` - 7 retargeted assertion/description/regex sites on the sentence-case button copy (no checks added or removed, 64/64 unchanged)
- `companion/test_contrast_check.py` - one docstring quote updated for consistency (not an assertion)

## Decisions Made

- UIR-12 fixed via a markup space rather than a new `h2 > .section-caption` CSS rule: the CSS route would glue the accessible name for a screen reader and would collide with `test_status_pages.py:2416`'s `css_source.index(".section-caption {")` substring search if placed before the base rule.
- `.banner__pill`'s head comment was rewritten (not deleted) to name its one deliberate divergence from `.airline-card__chip` (`min-width: 0`) now that the two rules are no longer declaration-identical — the banner pill lives in a wrapping flex row that must survive 375px, the chip does not.
- `airlines_page.py`'s `<img width height>` attributes were deliberately left untouched; `height: auto` on the CSS side is what makes `aspect-ratio` apply while the attributes still reserve the correct box for `loading="lazy"`.
- Task 3's real-browser measurement step was not performed directly in this execution — see Deviations below. Instead, every CSS/markup contract the browser measurement would exercise was verified two independent ways: the new automated harness check (pass), and a standalone one-shot `python3` render/source-read outside the harness (also pass, shown below).

## Deviations from Plan

### Scope adjustment (orchestrator instruction, not a Rule 1-4 auto-fix)

**1. Task 3's real-browser measurement step was replaced with harness + one-shot verification, per explicit orchestrator constraint**
- **Found during:** Task 3
- **Instruction:** The orchestrator's constraints for this execution explicitly said: "you have no browser tool, so do NOT attempt them and do NOT start a long-running server. Instead: (a) verify the rendered markup with the Python test harness or a one-shot `python3` render of the page functions ... and (b) in SUMMARY.md write the 'Browser measurement' table with the BEFORE numbers from the audit ... and mark the AFTER column 'measured by orchestrator — pending'."
- **What was done instead of the plan's Task 3 browser-driving steps:**
  1. Verified via the new `test_status_pages.py` check (113/113 pass) that: `.banner` declares `flex-wrap: wrap`; `.banner__label` declares `white-space: nowrap` and is the actual class on the anomaly banner's rendered lead span; `.banner__pill` declares `min-width: 0` while keeping `flex: none`; `.airline-card__image` declares `height: auto` alongside its surviving `aspect-ratio: 900 / 263`; the `.data-table--prose` first-column nowrap rule exists after the base rule; the rendered Battery trend heading carries a space before its em dash.
  2. Independently re-verified all six of those same facts with a standalone one-shot `python3` script reading `style.css` directly and calling `health_page.render()` directly (outside the harness this same commit modified) — all six passed (see terminal output captured during this task; not itself part of the diff).
  3. Ran `scripts/run-all-tests.sh` — all 16 harnesses green (see Test Harness Results below).
  4. Did **not** `cp -a /tmp/skypane-prod-state`, did **not** start `companion/app.py`, and did **not** touch `/tmp/skypane-prod-state` in any way — it was never read, copied, or written during this execution.
- **Consequence:** The real 375px `document.documentElement.scrollWidth` / `.banner__pill` right-edge numbers, and the real `.airline-card__image`/`.airline-card` pixel dimensions at 375px and 1440px, are not yet measured. The Browser Measurement table below carries the review's own BEFORE numbers and marks every AFTER cell "measured by orchestrator — pending", exactly as instructed.
- **Files modified:** None (verification-only; no source changes beyond what Task 1 already committed).
- **Verification:** `server/.venv/bin/python3 companion/test_status_pages.py` (113/113), plus the standalone one-shot script described above.

---

**Total deviations:** 1 (orchestrator-scoped adjustment to Task 3's verification method, not a plan-execution bug or gap)
**Impact on plan:** No source-code impact — Tasks 1 and 2 shipped exactly as planned. Task 3's CSS/markup contracts are proven; only the real-browser pixel measurements remain outstanding, to be filled in by the orchestrator.

## Browser Measurement (before/after)

The executor had no browser tool, so the AFTER column was measured by the orchestrating session immediately after Task 2 landed: Playwright (headless Chromium) against the companion running from this branch (`companion/app.py --state-dir <fresh copy of /tmp/skypane-prod-state>`), the same setup and probes the audit used. BEFORE values are the audit's own measurements from `06.6.4.1-UI-REVIEW.md`.

| Measurement | Viewport | Before (from 06.6.4.1-UI-REVIEW.md) | After (this branch, 2026-09-02) |
|---|---|---|---|
| `/health` `document.documentElement.scrollWidth` | 375px | 421 (page wider than the phone) | 360 — no horizontal overflow; the only element past 375 is the Unresolved-prefixes `.data-table` at 377 px inside its own `overflow-x: auto` wrap, pre-existing and tracked as UIR-11 (out of scope here) |
| `/health` every `.banner__pill` `getBoundingClientRect().right` | 375px | second pill at 421, past the banner (351) and the viewport | 268 and 201 — the second pill wrapped onto a second row; banner right edge 336, banner height 70 px (two rows), `.banner__label` 24 px (one line, no mid-phrase break) |
| `/airlines` first `.airline-card__image` width x height | 1440px | 224 x 263 (letterboxed) | 220 x 64 — true 900:263 ratio |
| `/airlines` first `.airline-card` height | 1440px | 317px | 118 px; page height 1,264 px |
| `/airlines` first `.airline-card__image` width x height | 375px | 325 x 263 (audit's mobile probe), card 317 px, page 9,693 px | 294 x 86, card 140 px, page 4,943 px |
| `/health` Resolution-statistics "Fresh lookup"/"Airline only" cell single-line height | 1440px | wrapping to two lines | Fresh lookup 51 px, Cached hit 51, Airline only 51 (single line); "Miss" row 75 px because its *Description* wraps, which is expected |
| `/health` Battery trend `h2` `textContent` (space around em dash) | any | "Battery trend— Last 3 months, daily average" | "Battery trend — Last 3 months, daily average" |
| Button labels rendered on `/settings` and `/login` | any | "Save Settings", "Trigger Poll Now", "Sign In" | "Save settings" (both the dirty bar and the no-JS fallback), "Trigger poll now", "Sign in" |

Screenshots of the after state (gitignored, orchestrator's scratch): `after-health-banner-mobile.png`, `after-airlines-desktop.png`.

**Real-device sign-off (2026-09-02, developer):** the branch was served from the developer's Mac through a `cloudflared` quick tunnel (HTTPS, so the `Secure` session cookie works off-localhost) against a copy of the production state snapshot, and checked on a real phone — Health banner (UIR-03), Airlines cards (UIR-07), the Battery-trend heading (UIR-12) and the sentence-case buttons (UIR-15) all confirmed ("validé"). This closes the `<human-check>` the plan's Task 3 carried; D1 and D2's `automated_ui` verifications above are therefore both measured and human-confirmed.

## Test Harness Results

Full suite via `scripts/run-all-tests.sh` (all 16 canonical harnesses, run at the end of Task 3):

| Harness | Result |
|---|---|
| server/test_config_history.py | config-history: 30/30 |
| server/test_dither.py | dither: 6/6 |
| server/test_enrich.py | enrich: 52/52 |
| server/test_illustrations.py | illustrations: 52/52 |
| server/test_panel_preview.py | panel-preview: 11/11 |
| server/test_pipeline_e2e.py | pipeline-e2e: 6/6 |
| server/test_plane_detection.py | plane-detection: 47/47 |
| server/test_poll_loop.py | poll-loop: 44/44 |
| server/test_render.py | render: 119/119 |
| server/test_runway_config.py | runway-config: 14/14 |
| stub-server/test_poll_cycle.py | poll-cycle: 23/23 |
| companion/test_companion_app.py | companion-app: 108/108 |
| companion/test_config_page.py | config-page: 64/64 (unchanged count, per plan) |
| companion/test_contrast_check.py | contrast-check: 36/36 |
| companion/test_status_pages.py | status-pages: 113/113 (112 + 1 new, per plan) |
| companion/test_view_pages.py | view-pages: 43/43 |

**Overall result: PASS.** Note on `server/test_poll_loop.py`: the plan text anticipated this harness carrying a pre-existing, out-of-scope failure ("not this task's concern... report it if it fails"). In this execution it passed cleanly at 44/44 — there was no pre-existing failure to report at this point in the branch's history. Coverage threshold (pyproject.toml) also passed (92% overall).

## Issues Encountered

One self-inflicted bug during Task 1's TDD RED step: the new harness check's regex for the banner__label lead text (`r">\d+ (warning|error)s?:<"`) initially expected a trailing `<` that the string-slice bound (`rendered[label_open:label_close]`, cut right before `</span>`) never included. Fixed by anchoring the regex on end-of-string (`\Z`) instead of a literal `<`. Caught immediately by the RED-then-GREEN loop; no separate commit needed since it was fixed before the Task 1 commit landed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All five UIR findings (UIR-03 BLOCKER, UIR-07, UIR-12, UIR-13, UIR-15) from `06.6.4.1-UI-REVIEW.md` are shipped and covered by automated regression checks.
- Outstanding: the real-browser pixel measurements in the Browser Measurement table above need to be filled in (by the orchestrator, per its own instruction) to close the loop on UIR-03/UIR-07's visual verification — the CSS/markup contracts are proven, but "does it actually look right at 375px on a real device" per this project's own `feedback_real_device_ui_verification` lesson (computed-style checks alone previously missed a real mobile bug) is not yet confirmed.
- No blockers for other in-flight work; this task touched no files outside the five-finding scope (`git diff --stat` against `main` confirms `companion/pages/airlines_page.py` was not touched, per the plan's own verification criterion).

## Self-Check: PASSED

- FOUND: `companion/static/style.css`
- FOUND: `companion/pages/health_page.py`
- FOUND: `companion/pages/config_page.py`
- FOUND: `companion/app.py`
- FOUND commit `84537c8` (Task 1)
- FOUND commit `083d8a1` (Task 2)
- FOUND `status: complete` in this file's frontmatter

---
*Phase: quick-260902-v2v*
*Completed: 2026-09-02*
