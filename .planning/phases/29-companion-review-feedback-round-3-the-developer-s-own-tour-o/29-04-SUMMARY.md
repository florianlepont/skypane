---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 04
subsystem: ui
tags: [css-grid, aria, i18n, ecmascript-5, intl-api, mutation-testing]

requires:
  - phase: 27-companion-review-feedback
    provides: "the quiet-hours dial, B14's normalised-time twin, and CFG-62's surfaces-agree browser check"
  - phase: 28-companion-review-feedback-round-2
    provides: "CFG-73's fix to the dial's minute-vs-HHMM readout bug — not reopened by this plan"
provides:
  - "Quiet hours reads as one card: dial, readout, a segmented preset row with short labels, then Start/End on one line"
  - "The B14 twin defaults to visible and is hidden only on a strict, conservative 24h determination"
  - "Three runnable server-side proofs (scripts-blocked visibility, gated hide path, four-surfaces agreement) plus a blind browser-level addition"
affects: [30-display-aspect-rebuild]

tech-stack:
  added: []
  patterns:
    - "Segmented control with no selected state, for momentary-action button rows (vs. a persistent-choice segmented control)"
    - "A .js-gate-opposite visibility mechanism: server-visible by default, hidden by script only on a positive, strict determination — the inverse direction from .js-gate, used when the fallback must survive both no-JS and script failure"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/static/value-controls.js
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_browser_ux.py

key-decisions:
  - "Presets keep NO selected/active state — they are momentary actions that write into the time fields, not a persistent choice, so this segmented control reserves no new accent"
  - "Start/End render as a two-column CSS grid at the card's own width, collapsing to one column below 480px — the native <input type=\"time\"> already carries a hard `min-width: 9rem` (144px) floor, and 2×144px cannot fit inside the ~280px inner card width the 360px contract floor provides, so two reference devices (360px, 390px) still see the stacked layout"
  - "The twin's hide condition is strict `hour12 === false` only — undefined, missing Intl, or any other value is treated as uncertain and leaves the twin visible, per RESEARCH.md's A1 caveat"
  - "The browser-level preset-click assertion (CFG-80's twin-visibility half) was folded into the EXISTING test_browser_ux.py check rather than registered as a new check(), so its EXPECTED_CHECK_COUNT does not move for an assertion this worktree has never executed"

requirements-completed: [CFG-80]

coverage:
  - id: D1
    description: "Quiet hours renders as one object: dial, readout, segmented presets with short labels, then Start/End on one line (>=480px) or stacked (<480px)"
    requirement: "CFG-80"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_every_class_the_quiet_hours_card_emits_has_a_real_selector"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_the_ring_is_an_addition_and_the_four_controls_are_untouched (order check)"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_both_time_fields_and_twins_sit_inside_the_times_row_with_their_own_error_slot"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_the_three_preset_buttons_render_short_labels_with_no_colon_in_both_languages"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_the_times_row_rule_declares_exactly_two_grid_tracks"
        status: pass
    human_judgment: false
  - id: D2
    description: "The normalised-time twin is served visible and hidden only on a strict positive 24h determination"
    requirement: "CFG-80"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_check_a_the_twin_is_visible_in_the_served_markup_in_both_languages"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_check_b_the_hide_path_is_gated_on_one_strict_condition"
        status: pass
      - kind: automated_ui
        ref: "companion/test_browser_ux.py#_the_arc_the_handles_and_the_caption_agree_after_an_interaction (twin-visibility assertion, written blind)"
        status: unknown
    human_judgment: true
    rationale: "The browser-level twin-visibility assertion was written without ever being executed (playwright is not installed in this worktree; test_browser_ux.py reports SKIPPED). A real-device confirmation on a forced-12h-locale browser (e.g. macOS/iOS set to a US region) is a named, outstanding human follow-up per RESEARCH.md's A1 caveat — a false negative there would reopen the exact defect B14 exists to prevent."
  - id: D3
    description: "The four server-rendered quiet-hours surfaces (arc, handles, readout, both time fields) still agree, including across a midnight wrap and a rejected-save echo"
    requirement: "CFG-80"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_check_c_the_four_server_rendered_surfaces_agree"
        status: pass
    human_judgment: false

duration: 90min
completed: 2026-09-21
status: complete
---

# Phase 29 Plan 04: Quiet hours as one visual object Summary

**Quiet hours collapses from four independently-legible surfaces to one card — a segmented preset control with no selected state and bare labels, Start/End on one CSS-grid row, and B14's normalised-time twin now hidden only on a strict `Intl.DateTimeFormat` 24h determination that a real 12h-locale browser has not yet confirmed.**

## Performance

- **Duration:** ~90 min
- **Completed:** 2026-09-21T21:25:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Task 1 (CFG-80): the three quiet-hours presets became a segmented control (`.quiet-preset-row`, bordered-container-plus-borderless-segment idiom, deliberately no selected state) with bare labels — Night/Day/Always on, Nuit/Journée/Toujours actif — replacing hour-bearing ones ("Night (23:00–07:00)"). Start and End now render inside one `.quiet-times-row` two-column grid, immediately after the presets, so dial → readout → presets → times-row reads as one object. 10-UI-SPEC.md's "each on its own full-width line" clause is marked SUPERSEDED in writing, in place, in `quiet_hours_group()`'s own docstring — the original sentence is kept verbatim per this file's convention, and the control ORDER is explicitly unchanged.
- Task 2 (CFG-80): `_normalised_time_html()`'s span gained a stable hook attribute (`QUIET_NORMALISED_TIME_ATTR = "data-normalised-time"`) with **no change to its default visibility** — it still renders visible, server-side, exactly as B14 shipped it. `value-controls.js` gained its first load-time pass, hiding every hook-carrying span only when `Intl.DateTimeFormat(undefined, {hour: "numeric"}).resolvedOptions().hour12` is strictly `false`; any missing API or any other value (including `undefined`) leaves the twin visible. The wake-interval unit sibling shares `.field-inline-value` but carries no hook, and is proven unaffected.
- Task 3 (CFG-80): three runnable checks prove what a browser is not needed for — the twin renders visible in the served HTML (Check A), the script's hide path is gated on exactly one strict branch (Check B), and the four server-rendered surfaces (arc, handles, readout, both fields) still agree, including across a midnight wrap and a rejected-save echo (Check C). `test_browser_ux.py`'s existing arc/handles/caption agreement check gained a fifth, blind assertion (twin visibility vs. the browser's resolved hour cycle after a preset click) folded into the same `check()` call rather than a new one.

## Task Commits

1. **Task 1: Segmented presets + one times row** — `cf1bb93` (feat)
2. **Task 2: Twin hidden only on positive 24h determination** — `afbef83` (feat)
3. **Task 3: Prove the twin's states and the four surfaces agreeing** — `230a552` (test)

**Plan metadata:** committed together with this SUMMARY, STATE.md and ROADMAP.md updates (see final commit hash in the executor's completion report).

## Files Created/Modified

- `companion/pages/config_page.py` — `QUIET_PRESET_ROW_CLASS`/`QUIET_TIMES_ROW_CLASS`/`QUIET_NORMALISED_TIME_ATTR` constants; shortened preset label constants; `quiet_hours_group()`'s markup/docstring restructured; `_normalised_time_html()`'s hook attribute + docstring paragraph
- `companion/static/style.css` — `.quiet-preset-row` (segmented control, no selected state), `.quiet-times-row` (two-column grid, 480px collapse), `.field-inline-value[hidden]` guard; three stale `.runway-row`-second-consumer comments corrected in place
- `companion/static/value-controls.js` — `NORMALISED_TIME_ATTR` constant + the file's first load-time pass, ES5-safe, wrapped in try/catch
- `companion/i18n_fr/display.py` — "Nuit"/"Journée"/"Toujours actif" replacing the three retired templated/pre-baked keys
- `companion/test_config_page.py` — 7 new checks (270 then 273, both re-derived by running); EXPECTED_CHECK_COUNT updated twice
- `companion/test_browser_ux.py` — one assertion added to the existing arc/handles/caption agreement check (written blind, never executed here)

## Decisions Made

- **No selected state on the preset segmented control.** These three buttons write a value into the time fields; they are not a persistent choice, so nothing needs to stay visually "current" — this also means zero new accent consumers and no change to `style.css`'s header-comment accent-reservation list.
- **The times-row two-column layout collapses below 480px, not below 360px.** `.config-form input[type="time"] { min-width: 9rem }` (144px) is a hard, pre-existing floor. At the 360px contract floor the card's own inner content width is 280px (360 − 2×24 page padding − 2×16 card padding); two 144px inputs plus even an 8px gap already need 296px, 16px more than what's available, before either field's label text or twin has taken any width. This is a real, computed constraint from numbers already on record in `style.css`, not a live-browser measurement (none was available in this worktree — no playwright, no headless browser). **Both of the app's own reference devices (360px, 390px) therefore still see the ORIGINAL stacked layout**; the "one line" outcome CFG-80 asks for is real starting at ≥480px (tablets/desktop). This is disclosed honestly here rather than claimed as achieved at every width — see "Known limitations" below.
- **The twin's hide direction is server-visible, script-hidden — the opposite of `.js-gate`.** `.js-gate` hides by default and reveals under `.js`, which would delete the twin for a scripts-blocked or failed-script visitor — precisely the audience B14 exists to protect. The new mechanism defaults visible and is hidden only by a strict, conservative positive determination.
- **`test_browser_ux.py`'s twin-visibility assertion was folded into the EXISTING check(), not registered as a new one.** The plan explicitly forbids moving `EXPECTED_CHECK_COUNT` for an assertion nobody in this worktree can execute (playwright absent); folding it in keeps the pinned count meaningful.

## Deviations from Plan

**1. [Rule 1 — bug in my own earlier test edit] Check A's forbidden-attribute scan initially false-failed on `aria-hidden`.**
- **Found during:** Task 3, writing Check A.
- **Issue:** a plain substring test for `"hidden"` inside the twin's own opening tag matched `aria-hidden="true"` — an attribute B14 REQUIRES the twin to carry — making the check fail on a correct render.
- **Fix:** boundary-anchored the scan (`(?<![-\w])hidden(?![-\w])`) so `aria-hidden` is not mistaken for the forbidden `hidden` attribute, and restructured the check to find open tags with a looser regex first (so a mutation inserting `hidden` between other attributes is still caught by name, rather than silently making the two-span count come back zero).
- **Files modified:** `companion/test_config_page.py` (same task, before commit).
- **Commit:** `230a552`.

**2. [Rule 1 — bug in my own earlier test edit] Check B's vacuity floor was miscalibrated for this specific file.**
- **Found during:** Task 3, writing Check B.
- **Issue:** a naive `>50%` comment-stripped-length floor failed against `value-controls.js`'s own real prose density (measured: 32% of the raw file remains after stripping comments, because its header alone runs past a hundred lines).
- **Fix:** widened the floor to a `[5%, 95%]` band — still catches a mangled strip in either direction (ate real code, or stripped nothing) without rejecting this file's genuinely comment-heavy style. Also switched the hook-literal vacuity count from the raw string literal (which this file's own convention emits only ONCE, in a `var NAME = "literal"` declaration) to the constant NAME (`NORMALISED_TIME_ATTR`, which legitimately appears twice — declaration + selector read).
- **Files modified:** `companion/test_config_page.py` (same task, before commit).
- **Commit:** `230a552`.

**3. [Rule 1 — bug in the planned mutation shape] Mutation C's first attempt crashed the whole render pipeline instead of producing a decodable disagreement.**
- **Found during:** Task 3's mutation proof for Check C.
- **Issue:** feeding `quiet_dial_readout_html()` raw minute-of-day strings at its CALL SITE (as the plan's literal wording suggests) crashes with `TypeError: %d format: a real number is required, not NoneType`, because the function's own CFG-73-era fix internally re-parses `start_hm`/`end_hm` via `quiet_window_minute_of_day()` for the `data-value-readout-base` attribute — a minute-shaped string is not valid HH:MM, so that internal call returns `None` and the `%d` format crashes. This broke essentially every other test in the file that renders the card at all, not just Check C.
- **Fix:** mutated the function's own DISPLAY substitution instead (the two `escape_html(start_hm)`/`escape_html(end_hm)` calls that produce the readout's visible endpoint text), leaving the internal `quiet_window_minute_of_day(start_hm)` call — which needs a real HH:MM string — untouched. This reproduces the ACTUAL historical shape of Phase 28's regression (the skill file's own words: "the readout regressing to raw minutes with a permanently blank duration") without crashing, and Check C failed cleanly with the disagreeing set printed (see Mutation Proofs below).
- **Files modified:** none surviving — `companion/pages/config_page.py` was mutated and reverted via `git checkout-index -f` within the same task, before commit.
- **Commit:** n/a (mutation-only, reverted before `230a552`).

**4. [Rule 1 — stale comments left by Task 1's own class rename] Three `.runway-row` comments referencing the preset row as a "second consumer" went stale the moment the preset row moved to `.quiet-preset-row`.**
- **Found during:** Task 1, immediately after moving the preset row off `.runway-row`.
- **Issue:** `style.css` carried three separate comments (the `.runway-row` rule's own header, the `.runway-card` B9 comment, and the 359.98px fallback comment) all asserting `.runway-row` had a second consumer (the preset row) that had to keep wrapping. That consumer no longer exists.
- **Fix:** all three comments corrected in place, each explaining what changed and why the surrounding conclusion (fix B9 on the card, not the row; the fallback still leaves `.runway-row`'s own wrapping unchanged) is unaffected.
- **Files modified:** `companion/static/style.css`.
- **Commit:** `cf1bb93`.

---

**Total deviations:** 4 auto-fixed (3 test-authoring bugs caught and fixed before commit via mutation-proving; 1 stale-comment correction in code this task was already editing).
**Impact on plan:** None of these change what ships to the visitor — all four are corrections to the plan's own verification apparatus or to documentation, made before any commit, and each is now covered by a passing, mutation-proven check.

## Known Limitations (disclosed, not silently assumed away)

1. **The two-column Start/End row does not engage at the app's own two reference-device widths (360px, 390px).** See "Decisions Made" above for the arithmetic. `quiet_hours_group()`'s CFG-80 docstring paragraph and this SUMMARY are the record of this trade-off; the developer may want to revisit the twin's own width contribution (e.g., stacking it below the input inside its own column) in a follow-up if a true side-by-side layout is wanted at the 360px floor.
2. **The 24h-detection mechanism's real-device confirmation is outstanding.** RESEARCH.md's own assumption A1 flags `Intl.DateTimeFormat(...).resolvedOptions().hour12` as a LOW-confidence mechanism, with no precedent anywhere in this codebase. The implementation is conservative by construction (strict `=== false`, every uncertain case defaults to visible), and Check B pins that strictness in the shipped script. **What remains unverified:** whether a real browser whose OS region forces a 12h clock (a macOS or iOS device set to a US region) actually resolves `hour12` as anything other than the strict `false` this mechanism requires to hide the twin. Task 3's own `<human-check>` names this exact confirmation:
   - On a 12h-locale browser (e.g. macOS/iOS set to United States), open `/display` and confirm each quiet-hours time field shows its 24h twin BESIDE it — the twin must NOT be hidden there.
   - On a French/European-locale browser, confirm the twin IS hidden and the native field alone reads e.g. `23:00`.
   - With JavaScript disabled entirely, confirm the twin is visible in both locales.
   - Click each preset and confirm the dial arc, the caption, both fields and (where visible) both twins all move together.
   - **Report any case where the twin vanished while the native field was still painting AM/PM** — that is the false negative RESEARCH.md's A1 warns about, and it would reopen the mechanism.
3. **`test_browser_ux.py`'s own twin-visibility assertion was written blind.** Playwright is not installed in this worktree; the file reports SKIPPED (confirmed via `scripts/run-all-tests.sh`, both directly and through the full-suite run below), never a pass. The assertion added there (comparing each twin's live `.hidden` DOM property to the browser's own resolved `hour12` after a preset click, in both themes) has never executed anywhere.

## Mutation Proofs (5 total, real failure messages quoted verbatim)

**Task 1 — Mutation 1 (order check): swapped the preset row and the times row in the return expression.**
```
FAIL the ring is an ADDITION: ... - exception: ValueError('substring not found')
FAIL every class quiet_hours_group() emits — including the new .quiet-preset-row/.quiet-times-row wrappers — resolves to a real selector in style.css ... - quiet_hours_group() emits the class '<div', which has no selector in style.css — it paints nothing at all
FAIL both <input type="time"> elements, both B14 twins and each field's own error paragraph all fall inside the .quiet-times-row container's own slice of the markup ... - expected the times-row wrapper to render
```
Reverted via `git checkout-index -f -- companion/pages/config_page.py` after staging the correct version.

**Task 1 — Mutation 2 (no-colon-in-labels check): restored one hour-bearing label.**
```
FAIL the three preset buttons render the short labels Night/Day/Always on and Nuit/Journée/Toujours actif, and NO preset label contains a ':' in either language ... - en: expected preset labels ('Night', 'Day', 'Always on'), got ['Night (23:00–07:00)', 'Day', 'Always on']
```
Reverted via `git checkout-index -f -- companion/pages/config_page.py`.

**Task 3 — Mutation A: added `hidden` to `_normalised_time_html()`'s emitted span.**
```
FAIL Check A — the scripts-blocked state, proven from the served markup ... - en: the twin's own tag carries hidden=: '<span class="text-label field-inline-value" data-normalised-time hidden aria-hidden="true">'
```
Reverted via `git checkout-index -f -- companion/pages/config_page.py`.

**Task 3 — Mutation B: relaxed the script's strict `=== false` to a truthiness test (`!resolved.hour12`).**
```
FAIL Check B — the hide path is gated, and gated on one thing only ... - the assignment's own nearest enclosing branch condition is 'if (resolved && !resolved.hour12)' — not a strict `hour12 === false` comparison, not a truthiness test, not `!= true`, not a negation of a truthy read
```
Reverted via `git checkout-index -f -- companion/static/value-controls.js`.

**Task 3 — Mutation C: made `quiet_dial_readout_html()`'s own visible text substitute raw minute-of-day numbers instead of the HH:MM pair (the exact shape of Phase 28's CFG-73 regression — "the readout regressing to raw minutes").**
```
FAIL Check C — the four surfaces still agree, at the render level ... - '23:00'/'07:00' (errors=None, submitted=None): the four surfaces disagree: {'arc': (1380, 420), 'handles': (1380, 420), 'readout': None, 'fields': (1380, 420)}
```
(Two other pre-existing checks also failed as expected collateral from this shared-code mutation — the readout's own "AT REST byte-identical" and D-07 echo contracts — confirming the mutation genuinely reached production code, not merely Check C's own decoder.) Reverted via `git checkout-index -f -- companion/pages/config_page.py`.

## Harness Before/After Table (every count re-derived by running)

| Harness | Before this plan | After Task 1 | After Task 2 | After Task 3 (final) |
|---|---|---|---|---|
| `companion/test_config_page.py` | 266/266 | 270/270 | 270/270 | **273/273** |
| `companion/test_i18n.py` | 24/24 | 24/24 (after i18n_fr edit) | 24/24 | 24/24 |
| `companion/test_companion_app.py` | 316/316 | 316/316 | 316/316 | 316/316 |
| `companion/test_view_pages.py` | 168/168 | — | — | 168/168 (unchanged) |
| `companion/test_status_pages.py` | 312/312 | — | — | 312/312 (unchanged) |
| `companion/test_browser_ux.py` | SKIP (no playwright) | — | — | SKIP (no playwright) — confirmed via direct run and via `scripts/run-all-tests.sh` |

Full suite: `PYTHON=server/.venv/bin/python scripts/run-all-tests.sh` — **PASS**, all 22 harnesses green, `companion/test_browser_ux.py`'s own printed line reads `SKIP companion/test_browser_ux.py — playwright not installed`, never a pass claim.

Other verification commands, literal output:
```
$ ls companion/static/*.js | wc -l
17
$ git diff -U0 companion/static/style.css | grep '^+' | grep -cE '^\+\s*--[a-z]'
0
$ git diff --stat companion/static/nav-dropdown.js companion/static/dirty-state.js
(empty — no diff)
```

## The SUPERSEDED Note (10-UI-SPEC.md's full-width-line clause)

`quiet_hours_group()`'s docstring now carries, immediately after the original locked-order paragraph (kept verbatim, not deleted):

> 29-04-PLAN.md Task 1 (CFG-80) SUPERSEDES the "each on its own full-width line" clause above FOR START AND END SPECIFICALLY — the sentence above is kept verbatim rather than deleted, per this file's own SUPERSEDED-in-place convention, but it no longer describes what ships. Four surfaces stacked full-width (the dial, the presets, Start, End) is what made this card read as four separate controls for one value rather than one control — the developer's own "pas très joli ce composant" on the quiet-hours screenshot (29-CONTEXT.md). Start and End now render side by side, as one visual unit with the dial, inside a new `QUIET_TIMES_ROW_CLASS`-wrapped two-column grid. THE ORDER IS UNCHANGED: presets still precede Start, Start still precedes End, in document order inside that row — this is a LAYOUT change, not a reordering, and the ring's own placement argument two paragraphs below (25-04-PLAN.md Task 2) is untouched by it.

## Issues Encountered

None beyond the four deviations already documented above — all caught and fixed before any commit via this task's own mutation-proving discipline.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 29's four requirements (CFG-79/CFG-81/CFG-82/CFG-83/CFG-84 minus this plan's CFG-80) are tracked in sibling plans; this plan's own CFG-80 is now complete.
- **Outstanding human follow-up, carried forward rather than silently closed:** the real-device 12h-locale confirmation named in "Known Limitations" above. Recommend running Task 3's own `<human-check>` steps before considering CFG-80 fully closed, and installing playwright in a CI-capable environment before trusting the blind `test_browser_ux.py` addition.
- No blockers for subsequent plans in this phase.

---
*Phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o*
*Completed: 2026-09-21*

## Self-Check: PASSED

- FOUND: commit cf1bb93 (Task 1)
- FOUND: commit afbef83 (Task 2)
- FOUND: commit 230a552 (Task 3)
- FOUND: companion/pages/config_page.py
- FOUND: companion/static/value-controls.js
- FOUND: companion/static/style.css
- FOUND: companion/i18n_fr/display.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_browser_ux.py
- FOUND: this SUMMARY.md at its expected path
