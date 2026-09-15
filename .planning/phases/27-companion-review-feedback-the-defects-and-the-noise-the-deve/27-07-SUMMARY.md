---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 07
subsystem: ui
tags: [companion, config-page, carousel, css-has, i18n, playwright]

requires:
  - phase: 25-06 (D5's theme carousel)
    provides: "_theme_carousel_html(), the departures-only scroll-snap strip, and the 4276→3743 px Display height measurement at 390px this plan's own prediction starts from"
  - phase: 27-05 (runway map removal)
    provides: "the retired schematic map and the runway cards' post-removal dimensions (90×138/89×136/88×136)"
  - phase: 27-06 (copy cuts)
    provides: "the shortened wake-interval/gauge/quiet-hours regions (137/168/121 chars, down from 220/254/188)"
provides:
  - "_theme_carousel_html(grid_html, strip_id) — the id is now a required argument, not a shared module default, closing the duplicate-id/wrong-pager-target trap by construction"
  - "three carousels (departures, arrivals, calendar) sharing one helper, one CSS class set, and the file's one @supports selector(:has(*)) block — no new rule, no fourth block"
  - "the disclosure ('Voir tous les thèmes'/'See all themes') rendering LAST in the wrapper, below the strip, with style.css reaching the grid via a :has() rule scoped per .theme-carousel instance instead of a forward adjacent-sibling selector"
  - "the swatch legend ('Departures & arrivals') asserting a relationship against the registry instead of a literal, self-correcting if a future theme ever gives departures/arrivals different inks"
  - "a predicted Display height (≈3446–3496 px, midpoint ≈3471 px, at 390px) stated with its arithmetic before 27-09 measures the real number"
affects: [27-09]

tech-stack:
  added: []
  patterns:
    - "per-instance :has() scoping — .theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip — for a control that needs its own [open]-state-driven layout change wired to a sibling it no longer immediately precedes in the DOM, without opening a second @supports block"
    - "seed-through-the-validated-API rather than raw JSON for a scripts-blocked save proof on a field whose valid value set includes None (theme_arriving), since the shared _persist_once() helper's own stored-is-None guard cannot distinguish 'never saved' from 'deliberately cleared'"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_browser_ux.py

key-decisions:
  - "_theme_carousel_html()'s new strip_id parameter has NO default — a shared/optional id would have left the trap merely untested rather than structurally closed"
  - "the disclosure moves to render LAST (grid, pagers, dots, disclosure) so 'Voir tous les thèmes' reads as a way OUT below the strip, and the CSS mechanism that lays the grid out on [open] becomes a :has() rule scoped per-carousel rather than a forward adjacent-sibling selector"
  - "only arrivals and calendar fold into the carousel (three total, not four) — the rule-add form's grid stays out, PROVISIONAL, because it lives inside the deferred 'règles par vol' view"
  - "the swatch legend ('Departures & arrivals') is checked as a registry RELATIONSHIP (label count == distinct colour count per theme), never the literal string"
  - "the Display height prediction states plainly that 2600px is NOT expected to be reached — the carousel extension itself saves ≈0px on the scripted measurement because theme-preview.js already collapses non-selected usage panels at load"

patterns-established:
  - "a helper that must never collide across instances takes its collision-prone id as a required argument, and the mutation-test for that fix simulates the collision directly (two copies of the same carousel's output on one page) rather than trusting the argument's presence alone"

requirements-completed: []

duration: ~2h
completed: 2026-09-15
---

# Phase 27 Plan 07: Extend the theme carousel to arrivals and calendar; move "Voir tous les thèmes" below the strip Summary

**`_theme_carousel_html()` now takes a required per-usage `strip_id` (closing the shared-id/wrong-pager-target trap by construction), wraps departures/arrivals/calendar in one shared `:has()`-scoped mechanism instead of three, moves the "Voir tous les thèmes" disclosure below the strip, and the swatch legend ("Departures & arrivals") is checked against the registry as a relationship rather than a literal.**

## Performance

- **Duration:** ~2h
- **Tasks:** 3 automated tasks (config_page.py/style.css/test_config_page.py/test_browser_ux.py) + 1 documentation-only task (this height prediction)
- **Files modified:** 5 (config_page.py, style.css, i18n_fr/display.py, test_config_page.py, test_browser_ux.py)

## Accomplishments

- The one-id-per-carousel fix: `_theme_carousel_html(grid_html, strip_id)` takes `strip_id` as a **required** argument — no shared default — so a second (or third) call to the helper cannot render a duplicate `id` even by omission.
- Arrivals and calendar now fold into the same scroll-snap carousel departures already had, each with its own id (`THEME_CAROUSEL_STRIP_ID_ARRIVALS`/`_CALENDAR`, derived from the existing `COLOUR_USAGE_*` constants). Three carousels, three distinct ids, zero duplicates — proved by a page-wide id-uniqueness check.
- "Voir tous les thèmes" now renders **below** the strip (last in the wrapper: grid, pagers, dots, disclosure), which is a one-line reorder of the shared helper's own format string — correcting all three carousels at once, not three separate edits.
- The mechanism that lays the grid out on `<details open>` moved from a forward adjacent-sibling CSS selector (which broke once the disclosure trailed the grid) to a `:has()` rule scoped to each `.theme-carousel` wrapper — one rule, inside the file's existing single `@supports selector(:has(*))` block, that happens to also give each carousel instance independent toggle behaviour for free.
- The swatch legend stopped promising a distinction the registry doesn't carry ("Departures · Arrivals" → "Departures & arrivals" / "Départs et arrivées"), with a check that computes its expected label count from the registry at check time.
- A Display height prediction is recorded below, with its arithmetic, before 27-09 measures the real number — and it says plainly that 2600px is not expected to be reached.

## Task Commits

1. **Task 1: The helper takes a per-usage id, and the disclosure moves below** - `4ef584b` (feat)
2. **Task 2: Arrivals and calendar fold the same way, and still save with scripts blocked** - `0d2e595` (feat)
3. **Task 3: The legend stops naming a distinction the registry does not carry** - `6ad823f` (fix)

Task 4 (the height prediction) produced no code changes — its entire deliverable is the prediction section below, per its own instruction not to measure in this plan. No commit was made for it individually; it lands in this plan's own metadata commit.

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified

- `companion/pages/config_page.py` — `_theme_carousel_html()` takes a required `strip_id`; return order reordered (grid, pagers, dots, disclosure); departures/arrivals/calendar call sites each build one Python name used for both the grid's own `id=` and the carousel's `strip_id` argument; `THEME_CAROUSEL_STRIP_ID_ARRIVALS`/`_CALENDAR` added; the rule-add form's grid carries a recorded, greppable non-conversion comment; `THEME_CHIP_SWATCH_LEGEND` changed to "Departures & arrivals"
- `companion/static/style.css` — the old `.theme-carousel__all[open] + .theme-chip-grid--strip` adjacent-sibling rule replaced by `.theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip` inside the file's one `@supports selector(:has(*))` block; `.theme-carousel__all` gains `margin-top` (it is now the last child, not the first)
- `companion/i18n_fr/display.py` — the French sibling for the new legend copy ("Départs et arrivées")
- `companion/test_config_page.py` — the departures-only markup check generalised to all three strips; the disclosure-order/CSS-rule assertions inverted and re-anchored (a `\n`-anchored selector lookup was needed once the `:has()` rule's own compound selector started shadowing the base rule's literal); a new page-wide no-duplicate-id check (mutation-tested); a new registry-relationship check for the swatch legend (mutation-tested); `EXPECTED_CHECK_COUNT` 261→262→263
- `companion/test_browser_ux.py` — a generalised `_CAROUSEL_INSTANCE_PROBE`/`_TOGGLE_OWN_DISCLOSURE` pair (per-instance-scoped, unlike the shared `_STRIP_PROBE`); the arrivals grid's own scripts-blocked save proof; a per-instance disclosure-toggle-independence proof; a keyboard-keeps-the-chip-in-view proof generalised to arrivals/calendar; `EXPECTED_CHECK_COUNT` 83→86

## Decisions Made

**1. The id-uniqueness fix, and why it had to be structural, not tested.** `THEME_CAROUSEL_STRIP_ID` was a single module-level literal read directly by both pagers' `aria-controls` builders inside `_theme_carousel_html()`. Calling the function a second time (for arrivals) without changing anything else would have rendered two elements sharing one `id` — invalid HTML — and left every pager on the page driving only the first strip, silently, since `aria-controls`/`getElementById` resolve to the first DOM match with no error of any kind. The fix makes `strip_id` a **required** parameter with no shared default: there is no code path left where two carousels can agree to share an id by omission, because the helper simply cannot be called without one. Each call site (departures, arrivals, calendar) builds the id **once** as a Python name and reads that same name twice — for the grid's own `id=` attribute and for the carousel wrapper's `strip_id` argument — rather than two literals that could drift apart.

**The mutation that proves it, quoted.** Two copies of the departures carousel's own output were rendered into one page (`departures_carousel + theme_error_html + departures_carousel`, a one-line change reverted immediately after). The new id-uniqueness check failed with:

> `id='theme-carousel-strip' appears 2 times on the rendered Display page — every id-based lookup (aria-controls, a <label for=>, aria-labelledby, document.getElementById) resolves to the FIRST match silently, so a duplicate id is not a cosmetic defect: whichever control names 'theme-carousel-strip' second is driving or describing the FIRST one instead of itself`

Reverted with `git checkout-index -f --`, `__pycache__` cleared, full suite re-confirmed green (262/262 at that point) before committing Task 1 for real.

**2. "Voir tous les thèmes" below the strip — one shared-helper edit, not three call-site patches.** `_theme_carousel_html(grid_html, strip_id)` returns `'<div class="theme-carousel">%s%s%s%s</div>' % (grid_html, pagers_html, dots_html, disclosure_html)` — disclosure moved from first to last in that one format string. Because departures/arrivals/calendar all route through this one function, the reorder is correct for all three the moment it lands; there was never a second or third call site to touch for this half of the plan. The only knock-on effect was the CSS mechanism that makes the disclosure's `[open]` state lay the grid out fully: the old rule was a forward adjacent-sibling selector (`.theme-carousel__all[open] + .theme-chip-grid--strip`), which requires the disclosure to *precede* the grid — no longer true once it trails the grid, pagers and dots. The replacement, `.theme-carousel:has(.theme-carousel__all[open]) .theme-chip-grid--strip`, is scoped to the shared `.theme-carousel` ancestor instead of a sibling relationship, so it works regardless of DOM order **and** — because the match is scoped to one wrapper — gives each of the three carousel instances independent toggle behaviour as a direct consequence, which is exactly standing constraint 3's requirement. It joins the file's one existing `@supports selector(:has(*))` block rather than opening a second one, per that block's own pinned-count convention; a browser without `:has()` support keeps the strip scrolling in its one-row form even with the disclosure open, which the disclosure's own body copy already discloses ("They are all in the strip either way — it scrolls").

**3. Keyboard navigation and both-theme verification, per carousel instance.** `_arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed` (new, `test_browser_ux.py`) generalises 25-06/27-04's departures-only "the selected chip stays inside the strip" proof to arrivals and calendar: one and six `ArrowDown`s each, measuring the focused chip's box against its OWN strip's `getBoundingClientRect()`, with zero pointer events. One wrinkle not present for departures: `theme-preview.js` collapses every usage panel except the checked `colour_usage` radio's (departures, by default), so arrivals/calendar's own radiogroups are `display:none` and cannot take focus until their usage row is clicked first — exactly what a real visitor switching to "Arrivals"/"Calendar flights" would do. `colour_usage` itself is never submitted (no `form=` attribute), so this is pure client state needing no restore. `_each_carousels_own_disclosure_toggles_only_its_own_strip` (new) opens each of the three disclosures in turn and confirms the OPENED carousel's own strip reads `flex-wrap: wrap` while both siblings stay `nowrap` — the direct browser-level proof that the `:has()` scoping from Decision 2 actually holds per instance, not merely that its selector text looks right. Both themes: every markup-level check (`test_config_page.py`) runs `_frame_colours_card_html()` fixture-driven, unaffected by `_set_ui_theme()`; the departures-carousel-specific paint-floor check (`_the_carousel_meets_its_floors_at_360px_in_both_themes`, pre-existing, unedited) already asserts both themes for the shared `.theme-chip`/`.theme-carousel__pager`/`.theme-carousel__all` paint, which arrivals/calendar's identical CSS rules inherit with no theme-specific branch of their own to re-verify.

**4. The height measurement — actual before/after, 2600px explicitly not expected.** See the dedicated section below.

## Task 4: The Display height prediction (stated before 27-09 measures)

**Baseline:** 3743 px at 390 px (25-06, measured — `_displays_page_height_is_recorded_at_both_phone_widths`, `test_browser_ux.py`).

**This plan's own carousel extension: ≈0 px on the scripted measurement.** `theme-preview.js` collapses every usage panel except the one matching the checked `colour_usage` radio (departures, by default) **at load** — before this plan, arrivals and calendar's grids were already not contributing their full height to a scripted page, because they render inside `frame-colours__usage-panel--collapsed` (`display: none`) the instant the script runs. Folding them into scroll-snap strips changes how much height they *would* occupy if visible (no-JS reader, or after a panel switch), not whether they are visible on the default scripted load. **This directly contradicts 27-RESEARCH.md's own prediction** of "three times the departures saving" — the correction is the point of this plan's own objective statement, and is restated here because it is what makes the arithmetic below honest rather than hopeful.

**27-05 (runway map removal): ≈ −63 px.** `references/control-density.md`'s own measured figures: the three runway cards went from 90×201/89×197/88×197 to 90×138/89×136/88×136 (63/61/61 px shorter per card). The three cards sit in a row (`.runway-row`), so the row's own height — and therefore the page's — drops by roughly the **largest** single card's reduction (≈63 px), not the sum of all three; `references/settings-page-patterns.md`'s own account independently describes this as "roughly the map's own 64px drawing plus its margin" (singular, not tripled), corroborating the row-not-stack reading.

**27-06 (text cuts): ESTIMATED at −40 to −90 px (midpoint −65 px), and this is the weakest term in this arithmetic — stated plainly rather than hidden.** 27-06's own SUMMARY records only character-count reductions (wake-interval caption 220→137, the two wake gauges combined 254→168, Quiet hours paragraph 188→121 — 236 fewer characters total), never a pixel figure; no `_display_page_height()` re-run exists for that plan. Extrapolating from character count at this column's typical wrap width (≈390 px viewport, a card content column roughly 340 px wide) suggests each region lost on the order of one to two wrapped lines; taking a conservative per-line estimate, the three regions together plausibly saved somewhere in a 40–90 px band. This is an ESTIMATE, explicitly not a measurement, and is recorded as a range for exactly that reason.

**27-04 (the save bar and the fallback button): ≈ −144 px (English; ≈ −110 px French).** The dirty save bar was `position: fixed` and never occupied document-flow height itself, but the page reserved space so it would never cover content: `.dirty-ready .page-content { padding-bottom: 144px; }` (English) / 110px (French) at the phone breakpoint (`references/settings-page-patterns.md`). 27-04 retired the dirty bar outright, and `style.css`'s own historical comment confirms the reservation rule was deleted as dead code once `.dirty-ready` was no longer written by any script. Since `.dirty-ready` was added at script-init time (confirming the bar's own root elements exist), not gated on an actual unsaved edit, this padding was live and part of the 3743 px baseline measured in 25-06 — its removal is a real, documented subtraction, not a guess.

**Sum, as a range with a midpoint (English, 390 px):**

```
3743                       (25-06 baseline)
−   0   this plan's carousel extension (mechanism: already-collapsed panels)
−  63   27-05 runway map removal (measured, one row's height)
− 40..90 (mid 65)  27-06 text cuts (ESTIMATED from char-count deltas)
− 144   27-04 dead .dirty-ready padding-bottom removal (documented)
──────────────────────────────────────────────
≈ 3446 .. 3496, midpoint ≈ 3471
```

**Is 2600 px expected to be reached? No.** Even the low end of this range (3446 px) sits 846 px over X6's 2600 px target. 25-06's own SUMMARY already recorded that what remains after the carousel is "not a grid — it is four more cards and the Frame strip above them," and this plan removes zero of those four cards. A prediction that promised 2600 px here would have been the same defect this plan's own objective statement calls out in 27-RESEARCH.md's mispredicted "three times the saving": arithmetic that is wrong about the mechanism, stated with confidence anyway. 27-09 measures the real number against this stated, falsifiable range.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `_theme_chip_grid_html--strip` selector collision in `test_config_page.py`'s existing checks, caused by Task 1's own CSS change**
- **Found during:** Task 1
- **Issue:** Moving the disclosure→grid layout mechanism into a compound `.theme-carousel:has(...) .theme-chip-grid--strip { ... }` selector inside the file's `@supports` block introduced a SECOND textual occurrence of the substring `.theme-chip-grid--strip {` earlier in `style.css` than the real base rule's own declaration. Two existing checks located that base rule by `source.index(".theme-chip-grid--strip {")`, which — after the change — resolved to the compound `:has()` selector instead (declaring `flex-wrap: wrap`, not `nowrap`), and read its body instead of the real rule's.
- **Fix:** anchored the lookup with a leading `"\n"` and no indentation (`"\n.theme-chip-grid--strip {"`), which only the real, unindented, top-level rule satisfies — the `:has()` block's own copy is 2-space indented, matching this file's established indentation convention for rules inside `@supports`.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** the affected check (`_the_carousel_dots_are_real_colours_and_the_strip_rules_are_declared`) passes; full suite re-run green (262/262 at the time)
- **Committed in:** `4ef584b` (Task 1 commit)

**2. [Rule 1 - Bug] The disclosure-order and CSS-rule assertions in `_the_full_grid_sits_behind_a_native_details_and_the_pagers_behind_the_gate` were testing the OLD, now-incorrect behaviour**
- **Found during:** Task 1
- **Issue:** The pre-existing check asserted `disclosure.start() > strip_at` would FAIL (i.e., required the disclosure to precede the strip) and looked up the old adjacent-sibling CSS selector — both now describe behaviour Task 1 deliberately inverted.
- **Fix:** inverted the ordering assertion (disclosure must now render AFTER the strip) and updated the CSS-rule dictionary entry to the new `:has()`-scoped selector; generalised the whole check from a single page-wide match to three per-usage-panel-scoped segments in Task 2 (see below), which incidentally also delivers Task 2's "each pager's target resolves inside its own carousel" relationship requirement.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** check passes in both Task 1 (single carousel) and Task 2 (three carousels) states
- **Committed in:** `4ef584b` (Task 1), further generalised in `0d2e595` (Task 2)

**3. [Rule 3 - Blocking] Task 2's own code changes broke two more pre-existing `test_config_page.py` checks not listed in Task 2's own `<files>` tag**
- **Found during:** Task 2
- **Issue:** `_the_departures_grid_is_the_one_renderer_presented_as_a_strip` asserted exactly ONE `.theme-chip-grid--strip` on the page and that arrivals/calendar were NOT converted — both became false the moment arrivals/calendar were wrapped. `_calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order` matched the calendar grid's opening `<div>` tag by an exact class-list/attribute string that no longer matched once the calendar grid gained the strip modifier and an id. Neither check was in Task 2's own `<files>` list (only `config_page.py`, `style.css`, `test_browser_ux.py`), but leaving them broken would have failed `companion/test_config_page.py`'s own required-green verification.
- **Fix:** generalised the first check to assert three strips (with per-field radio counts, since arrivals/calendar each carry a leading "Same as departures" chip departures does not) instead of one; updated the second check's regex to expect the new class list and id.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** full `test_config_page.py` suite green (262/262) after the fix
- **Committed in:** `0d2e595` (Task 2 commit)

**4. [Rule 1 - Bug] Arrivals' theme radiogroup could not take keyboard focus in the new generalised keyboard-in-view check**
- **Found during:** writing `_arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed` (Task 2)
- **Issue:** `theme-preview.js` collapses every usage panel except the one matching the checked `colour_usage` radio (departures by default) at load — a `display:none` panel's radios cannot take focus, so `_operate_with_keyboard()` raised `did not take focus from el.focus()` for the arrivals field.
- **Fix:** the check now clicks the corresponding `colour_usage` radio (`input[name="colour_usage"][value="arrivals"/"calendar"]`) first, un-collapsing that panel — exactly what a real visitor switching usage would do. `colour_usage` is never submitted, so this needs no restore.
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** full run 86/86, this check passing specifically
- **Committed in:** `0d2e595` (Task 2 commit)

**5. [Rule 3 - Blocking] `_persist_once()`'s own "stored is None" save-floor guard would have raised against a CORRECT restore-to-None outcome for `theme_arriving`**
- **Found during:** writing the arrivals scripts-blocked save proof (Task 2)
- **Issue:** `theme_arriving`'s valid value set includes `None` ("Same as departures"), but `_persist_once()` treats `stored is None` unconditionally as "the control saved nothing" (the D-09 defect it exists to catch) — it cannot distinguish that from a deliberate restore-to-unset. Starting the check from a `None` `theme_arriving` (the harness's real default, since no prior check had set it) would have made `_persist_without_js()`'s own built-in restore leg raise against a correct result.
- **Fix:** the check seeds `theme_arriving` to a known, concrete theme id via the validated `device_config.save_device_config()` API (never a raw file write) before running, and restores it to its true original state (via `CLEAR_THEME_ARRIVING` if it started unset, or the real value otherwise) as its own last act in a `finally` block — not relying on `_persist_without_js()`'s default restore path for this specific field.
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** the check passes; theme_arriving's on-disk state confirmed restored to its true original after the check runs
- **Committed in:** `0d2e595` (Task 2 commit)

---

**Total deviations:** 5 auto-fixed (3 Rule 1 — bugs in pre-existing tests exposed by this plan's own structural changes, 2 Rule 3 — blocking issues that would have failed required-green verification).
**Impact on plan:** All five were necessary consequences of extending a page-wide-unique-selector assumption (one carousel) to a three-instance one; none represent scope creep beyond what Task 1/2's own stated risk ("the trap") already anticipated. No architectural changes, no Rule 4 escalation.

## Issues Encountered

None beyond the deviations above — no blockers reached checkpoint status, no auth gates, no package installs.

## Known Stubs

None. Every markup path this plan touches (departures/arrivals/calendar carousels, the swatch legend) renders real, wired data from `device_config.THEMES`/`device_config.THEME_IDS`; nothing is hardcoded to an empty placeholder.

## Threat Flags

None. Every threat this plan's own `<threat_model>` named (T-27-07-A duplicate ids, T-27-07-B no-JS trap, T-27-07-C stale legend literal) is the SAME surface the plan's own tasks mitigate — no new network endpoint, auth path, file access pattern, or schema change was introduced.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 27-09 (the closing plan) can now: (1) run the real `_display_page_height()` measurement at 390px/360px and report it against this plan's stated ≈3446–3496 px range rather than a vague expectation; (2) tick CFG-68/CFG-70/CFG-71 in `.planning/REQUIREMENTS.md`/`STATE.md`/`ROADMAP.md` — deliberately left untouched by this plan per its own standing constraint 13.
- `<human-check>` from this plan's own `<verification>` section is not executable by this agent and remains open for 27-09 or the developer: on a real phone at 360px and a desktop, in both themes and both languages — page all three colour strips, confirm each pager moves its own strip and not another's, confirm "Voir tous les thèmes" now reads as a way out BELOW the strip, and confirm the one-swatch legend still says what the chip is showing.
- The rule-add form's grid remains PROVISIONALLY unconverted; folding it in is one more call to `_theme_carousel_html()` with one more id, deferred pending the "règles par vol" view's own redesign conversation.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

- Commits `4ef584b`, `0d2e595`, `6ad823f` all found in `git log --oneline --all`.
- `companion/pages/config_page.py`, `companion/static/style.css`, `companion/i18n_fr/display.py`, `companion/test_config_page.py`, `companion/test_browser_ux.py` all found on disk.
- `companion/test_config_page.py`: 263/263 checks pass (`EXPECTED_CHECK_COUNT = 263`, re-derived by running).
- `companion/test_browser_ux.py`: 86/86 checks pass (`EXPECTED_CHECK_COUNT = 86`, re-derived by running).
- `companion/test_i18n.py`: 24/24 checks pass.
- `ruff check .`: all checks passed.
- `style.css`: 4 `@keyframes` (grep -c '^@keyframes'), 1 brace-anchored `@supports selector(:has(*)) {`, `/*`/`*/` counts balanced (483/483).
- `PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh`: exactly 5 failing checks, confirmed BY NAME — the sandbox baseline (2× WR-11 in `companion/test_companion_app.py`, 2× WR-11 in `server/test_manual_resolutions.py`, 1× `anomaly_active()` in `companion/test_status_pages.py`). No sixth failure.
