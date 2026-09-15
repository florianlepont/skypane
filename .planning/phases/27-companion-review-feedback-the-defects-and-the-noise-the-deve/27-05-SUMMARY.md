---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 05
subsystem: ui
tags: [css, playwright, accessibility, regression-testing, requirements-ledger]

# Dependency graph
requires:
  - phase: 27-04
    provides: file ownership of companion/pages/config_page.py, companion/static/style.css, companion/test_browser_ux.py, companion/test_config_page.py
provides:
  - D16's schematic runway map fully removed from production code (config_page.py, style.css) and from its own standing checks (both harnesses), with the three native radios and three photographs untouched
  - CFG-47 retirement ledger reverified against the post-removal tree; CFG-66/CFG-71 requirement rows left unticked per this phase's closing-plan convention
  - the design system (sketch-findings-skypane skill) superseded in writing wherever it described the now-retired drawing
affects: [27-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "map-inside-a-mixed-check triage: when a single pre-existing check bundles a map-only assertion with a still-relevant control/security assertion, mutate the check in place (drop the map clause, rename, keep the rest) rather than deleting the whole check or leaving it broken"
    - "relationship check replaces three narrower ones: one browser check now asserts absence of the drawing AND presence of the control AND presence of the photographs as a single fact, per this phase's D-32 convention"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_config_page.py
    - companion/test_browser_ux.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md

key-decisions:
  - "The decision that mattered most: two of the five pre-existing map checks (test_browser_ux.py's scripts-blocked-save check, test_config_page.py's escaping check and its presentation-and-photographs check) bundled a map-only assertion together with a still-load-bearing control/security assertion in the SAME check function. Rather than deleting these checks wholesale (which would have silently dropped the radios' arrow-key/paint corroboration or the photographs'/radiogroup's own proof) or leaving them broken (they'd fail on AttributeError once the map symbols were gone), each was mutated in place: the map-only clause removed, the check renamed to describe what it now actually asserts, the rest kept verbatim in substance. This is the 'mutate what you keep, don't remove what you should mutate' standing constraint applied to test code, not just production code."
  - "The pre-existing radios' scripts-blocked save-to-disk proof that had to survive unedited was NOT the map-era check (_the_runway_still_saves_with_scripts_blocked_through_the_map, which also asserted the map's own presence and was removed with it) — it was a separate, already-independent CFG-64 check from 27-03 (_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies), whose own docstring already says 'Unlike 25-03's own check, which corroborates with the runway MAP's presence, this one asserts the SUBMIT itself.' That check is confirmed unedited by this plan's diff."
  - "The runway card's touch-target floor is re-measured, not assumed, now that the map strip no longer provides the box: 90x138 / 89x136 / 88x136 at 360px in both themes — within a pixel of 25-02's own pre-map baseline (88x138), confirming the map's removal returns the card to substantially its pre-map shape rather than shrinking it below the floor."

patterns-established:
  - "Design-system supersession discipline extended to test-harness comments: when a plan mutates a pre-existing check in place (not a wholesale removal), the mutation is documented as a comment inside the check itself, naming the old check name, what was dropped, and what survives — mirroring the SUPERSEDED-in-writing convention this codebase already uses in style.css and REQUIREMENTS.md."

requirements-completed: [CFG-66, CFG-71]

# Metrics
duration: ~55min
completed: 2026-09-15
---

# Phase 27 Plan 05: Remove D16's schematic runway map, retire CFG-47 Summary

**Deleted `runway_map_svg()`/`runway_bearing_deg()`/nine `RUNWAY_MAP_*` constants and all seven `runway-map` CSS rules; removed 3 map-only checks per harness, mutated 2 mixed checks in place to keep their non-map assertions, and added one relationship check replacing the three removed browser checks — the three native radios and three `runway-*.png` photographs are unchanged throughout.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-15T10:37:47Z
- **Tasks:** 4
- **Files modified:** 7 (4 code/test files, 3 design-system reference files)

## Accomplishments

- D16's schematic Orly runway map is gone from production code: `runway_map_svg()`, `runway_bearing_deg()`, the nine `RUNWAY_MAP_*` constants, and all seven `runway-map`/`runway-map__*` CSS rules (the base block plus both live/fallback rules inside the one `@supports selector(:has(*))` block).
- The three native `tracked_runway` radios and the three `runway-*.png` photographs (with `RUNWAY-IMAGES.md`, their session-gated route, and their slot in each card) are byte-for-byte unaffected in markup shape — confirmed by both the mutated `test_config_page.py` checks and the new `test_browser_ux.py` relationship check.
- Every map-only check is named and removed; every check that bundled a map assertion with a still-relevant one is mutated in place rather than deleted or left broken; the one check that was always independent of the map (CFG-64's scripts-blocked save-to-disk proof) is confirmed unedited.
- `EXPECTED_CHECK_COUNT` re-derived by running for both harnesses: `test_config_page.py` 259 → 256, `test_browser_ux.py` 85 → 83.
- CFG-47's three retirement ledger records reverified consistent with the tree this plan produced; nothing deleted, the `[x]` intact.
- The `sketch-findings-skypane` design-system skill superseded in writing (not deleted) wherever it described the now-retired drawing.
- Full suite (`scripts/run-all-tests.sh`) run to completion: exactly the 5 sandbox-baseline failures, verified by name.

## Task Commits

Each task was committed atomically:

1. **Task 2: The map comes out of the page and the stylesheet** - `42b0274` (feat)
2. **Task 3: The map's checks come out; the control's proof stays and still passes** - `65f22c7` (test)
3. **Task 4: Verify CFG-47's retirement record; supersede the design system** - `d051313` (docs)

Task 1 (the OUT/STAYS inventory) produced no file changes of its own — see "OUT and STAYS, named" below for its deliverable, folded into this SUMMARY as the plan specifies. No separate commit exists for it.

**Plan metadata:** (pending — this SUMMARY commit itself)

## Files Created/Modified

- `companion/pages/config_page.py` - `runway_map_svg()`/`runway_bearing_deg()`/nine `RUNWAY_MAP_*` constants removed; the card markup's `<svg>` call dropped; two stale comments cross-referencing the removed function corrected
- `companion/static/style.css` - all seven `runway-map`/`runway-map__*` rules removed; structural counts unmoved
- `companion/test_config_page.py` - 3 map-only checks removed wholesale, 2 mixed checks mutated in place, `EXPECTED_CHECK_COUNT` 259→256
- `companion/test_browser_ux.py` - 3 map-only checks removed wholesale (plus their two now-unused helpers), 1 new relationship check added, `EXPECTED_CHECK_COUNT` 85→83
- `.claude/skills/sketch-findings-skypane/SKILL.md` - Controls contract paragraph and its zero-script bullet superseded in writing
- `.claude/skills/sketch-findings-skypane/references/control-density.md` - runway-radios hit-target register entry superseded with re-measured figures
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` - Display page-height table flagged as a pre-removal snapshot

## OUT and STAYS, named (Task 1's inventory)

Derived by running both harnesses before any deletion, then re-confirmed by reading every `runway` hit in full (not by trusting 27-RESEARCH.md's provisional figures). The research's line-count figures were consistent with what was measured (7 stylesheet occurrences confirmed by grep; the "45 lines" figure was a rough shorthand for "3 checks totalling roughly that many lines" and undercounted the two additional harness checks that turned out to be *mixed* rather than pure — see below).

**OUT — removed wholesale, subject is the map itself:**

`companion/test_config_page.py`:
1. `_runway_map_is_drawn_from_the_registry_never_a_typed_list` (CFG-47, 25-03-PLAN.md Task 1) — map-registry-following behavior; its incidental radio-count/visually-hidden/form assertions are redundant with `_runway_fieldset_exactly_three_radios`/`_runway_fieldset_cards_visually_hidden_radio_and_selected_class`, both untouched, both still present.
2. `_runway_strip_bearings_come_from_the_designators` (T-25-03-D) — pure bearing-derivation math, no control/photo content.
3. `_runway_map_paint_resolves_and_joins_the_one_feature_query` (CFG-47/CFG-52) — pure CSS/paint/feature-query assertions.

`companion/test_browser_ux.py`:
4. `_the_runway_still_saves_with_scripts_blocked_through_the_map` — its persistence half duplicated CFG-64's own independent check (see STAYS below); its trailing clause asserted the map's own presence on the scripts-blocked page.
5. `_keyboard_only_selection_survived_the_map` — arrow-key navigation was tested only as "did the map break it," and its live-state assertions read `.runway-map__strip--this` paint directly.
6. `_the_map_meets_its_floors_at_360px_in_both_themes` — map drawing fit, paint-as-a-floor and transition-is-real assertions; its hit-target measurement logic was reused (not discarded) in the new replacement check.

Plus the `_runway_ids()`/`_SETTLE_STRIPS` helpers (browser_ux) and the `_MAP_STRIP_ATTR` constant (config_page), each used only by the checks above.

**MUTATED IN PLACE — map assertion dropped, non-map subject kept and renamed** (`test_config_page.py`):

7. `_runway_map_paints_through_classes_and_announces_nothing_twice` → `_runway_fieldset_escapes_a_hostile_registry_label`. Dropped: the map `<svg>`'s own colour-literal ban, shape-paint-route requirement, `aria-hidden`/`focusable` and size-route assertions, and the `runway_map_svg("h")` escaping sub-check. Kept: `runway_fieldset()`'s own hostile-registry-label escaping proof (T-25-03-B) — the only escaping check for runway labels anywhere in the suite, and still a live threat surface now that the label renders without the map.
8. `_the_map_changed_the_presentation_and_not_the_control` → `_the_controls_semantics_and_the_photographs_survive_the_map_s_removal`. Dropped: the `RUNWAY_MAP_THIS_STRIP_CLASS` own-strip-survives-`current_runway_id=None` assertion. Kept: `role="radiogroup"`/`aria-labelledby`/`aria-describedby` presence, `current_runway_id=None` marking nothing selected, and all four photograph assertions (`images_available=()` renders no `<img>`, the full set renders one `<img>` per runway, the session-gated route prefix, and the three PNGs' on-disk existence).

**STAYS, byte-identical (confirmed by `git diff` showing no edit, and by name):**

- `_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies` (CFG-64, `companion/test_browser_ux.py`, from 27-03-PLAN.md Task 3) — **this is the radios' own scripts-blocked save-to-disk proof the plan required to survive unedited.** Its own docstring already states the distinction: *"Unlike 25-03's own check, which corroborates with the runway MAP's presence, this one asserts the SUBMIT itself."* Quoted PASS line from the final run:

  > `PASS the no-JS floor still SAVES TO DISK after the gate simplifies to the plain .js rule (CFG-64) — tracked_runway operated natively, submitted through the real form, re-read FROM DISK after a fresh GET, in BOTH shipped languages, at 360px, restored as the last act (the same field and mutation 25-03's own M20 recorded) — and the data-static-save-fallback submit is present and VISIBLE on that scripts-blocked page AFTER the save, so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3)`

- Every other `runway`-touching check in both harnesses (`_runway_fieldset_exactly_three_radios`, `_runway_fieldset_cards_visually_hidden_radio_and_selected_class`, `_runway_fieldset_cards_image_rendering_per_card`, `_runway_row_starts_after_caption_and_nothing_follows_it`, `_runway_fieldset_graceful_fallback_no_images`, and every ctx-fixture use of `tracked_runway="3"`/`"06-24"` across the file) — none of these reference `RUNWAY_MAP_*`/`runway_map_svg`/`runway_bearing_deg` and none needed any edit.

**Predicted counts (Task 1) vs. actual (Task 3, re-derived by running):** predicted config-page 259 − 3 (checks 1–3) = 256, actual 256 (matched — checks 7–8 were mutations, not additions/removals, so no further delta). Predicted browser-ux 85 − 3 (checks 4–6) + 1 (new relationship check) = 83, actual 83 (matched).

## Decisions Made

See `key-decisions` in frontmatter. In prose: the mixed-check triage (mutate in place rather than delete-or-leave-broken) was the single decision with the most leverage in this plan — it is what let the plan remove the map's own assertions without silently dropping the escaping proof or the radiogroup/photograph proof that happened to live in the same function.

## The layout proof at 360px after deletion

`_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor` (new, `companion/test_browser_ux.py`) measures each `.runway-card`'s hit target in its own container, in both themes, at the 360px contract floor, now that the map strip no longer provides the box:

```
default theme card 1 (3):     hit=(90, 138)  visual=(89.07, 137.72)
default theme card 2 (06-24): hit=(89, 136)  visual=(87.34, 135.02)
default theme card 3 (02-20): hit=(88, 136)  visual=(87.33, 135.02)
theme=light — identical to default (the app's own default theme)
theme=dark  — identical figures (hit area is layout-only, not paint-dependent)
```

Every measurement clears the 44px floor by a wide margin. These figures sit within a pixel of 25-02's own pre-map baseline (88×138, `references/control-density.md`), confirming the map's removal returns the card to substantially its pre-map shape rather than leaving empty space or shrinking below the floor — the exact defect T-27-05-B named as a risk. The runway row also does not scroll the page sideways at 360px (`_assert_no_page_overflow`, asserted in the same check).

## Confirmation: the radios' scripts-blocked save-to-disk proof still passes, quoted

Run standalone (`companion/test_browser_ux.py`, 83/83) and inside the full suite (`scripts/run-all-tests.sh`):

> `PASS the no-JS floor still SAVES TO DISK after the gate simplifies to the plain .js rule (CFG-64) — tracked_runway operated natively, submitted through the real form, re-read FROM DISK after a fresh GET, in BOTH shipped languages, at 360px, restored as the last act (the same field and mutation 25-03's own M20 recorded) — and the data-static-save-fallback submit is present and VISIBLE on that scripts-blocked page AFTER the save, so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3)`

`git diff` confirms zero edits to this check's function or its `check()` call across every commit in this plan.

## Mutation testing, quoted

New check `_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor`, both mutations applied and reverted via `git checkout-index -f --` against a staged index (never `git checkout --`), `__pycache__` cleared after each cycle:

**Mutation 1 — re-add a `runway-map` class to one card:**
> `FAIL CFG-66: ... - expected ZERO .runway-map elements on /display after CFG-66's removal, found 3 — the drawing is supposed to be gone`

**Mutation 2 — delete one radio (drop the first card's `<input>` entirely):**
> `FAIL CFG-66: ... - expected 3 tracked_runway radios, found 2 — the map coming out must not take the control it was wrapped around with it`

Both mutations fail on the correct clause (the map's own presence; the control's own count), naming the specific discrepancy rather than failing opaquely.

## CFG-47's ledger entry, re-verified intact

All three records quoted and confirmed consistent with the tree this plan produced (none required amendment — they were written prospectively at planning time and match exactly):

1. **Ticked row** (`.planning/REQUIREMENTS.md` L73): `[x]` present, `**RETIRED (Phase 27, 2026-09-14).**` — states the map is removed, the radios return to being the control, the photographs stay served, and the tick stays because the work was really done.
2. **Traceability row** (L209): historical account of what 25-03 measured, ending `**RETIRED 2026-09-14 (Phase 27).**` — `"The successor is CFG-66, which removes the drawing, names every check that comes out with it, and keeps the radios' scripts-blocked save-to-disk proof."` — exactly what this plan did.
3. **D16 section** (L588–590): `**RETIRED 2026-09-14 by Phase 27 (CFG-66).**` — kept as "a true account of what 25-03 built and measured."

`grep -c 'RETIRED' .planning/REQUIREMENTS.md` → 3. `git diff --stat .planning/REQUIREMENTS.md .planning/STATE.md .planning/ROADMAP.md` → empty (none touched by this plan, per standing constraint 11 — the ticking mechanism for CFG-66/CFG-71 belongs to 27-09).

## Re-derived counts, obtained by running (both lower than they entered)

| Harness | Entered this plan | Left this plan | Verified |
|---|---|---|---|
| `companion/test_config_page.py` | 259 | **256** | 256/256, standalone run |
| `companion/test_browser_ux.py` | 85 | **83** | 83/83, standalone run (twice, once before and once after mutation-test revert) |

## Sandbox baseline reconfirmed

`PYTHON=/home/user/skypane/server/.venv/bin/python3 bash scripts/run-all-tests.sh` → exactly the 5 baseline failures, verified by name:

1. `test_companion_app.py`: *"POST /airlines/resolve redirects with the manual_save_failed flash key..."* (WR-11)
2. `test_companion_app.py`: *"POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key..."* (WR-11)
3. `server/test_manual_resolutions.py`: *"add_entry() returns ADD_FAILED..."* (WR-11)
4. `server/test_manual_resolutions.py`: *"delete_entry() returns False..."* (WR-11)
5. `test_status_pages.py`: *"anomaly_active() runs on every page render..."*

One earlier full-suite run also reported `test_browser_ux.py` failing under 4-way parallel load; re-run isolated (83/83 clean) and re-run inside the full suite a second time (clean, exactly the 5 baseline failures) — consistent with resource contention among concurrent Chromium instances under `JOBS=4`, not a real regression. No sixth failure in either full-suite run.

`ruff check .` on every touched Python file: clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — bug] Two stale comments in `config_page.py` cross-referenced the removed `runway_map_svg()`/`RUNWAY_MAP_*`**
- **Found during:** Task 2
- **Issue:** the `draw` import's own comment attributed the import solely to the runway map (now gone, though `draw` is still used by the quiet-hours dial); a paragraph in `quiet_hours_group()`'s docstring explained its own `aria-hidden`/`focusable` choice by pointing at `runway_map_svg() above`, which no longer exists at that position.
- **Fix:** both rewritten to state their own reasoning directly, without pointing at removed code.
- **Files modified:** `companion/pages/config_page.py`
- **Committed in:** `42b0274` (Task 2 commit)

**2. [Rule 2 — missing critical functionality, design-system accuracy] Three entries in the `sketch-findings-skypane` skill described the now-retired map as current**
- **Found during:** Task 4, per standing constraint 12
- **Issue:** `SKILL.md`'s "Controls" contract paragraph, `control-density.md`'s runway-radios hit-target register entry, and `settings-page-patterns.md`'s Display page-height table all described or measured a control that no longer exists in that shape, without a design-system reader having any way to know the account was stale.
- **Fix:** superseded in writing (kept verbatim, dated paragraph appended), matching this codebase's standing "SUPERSEDED, not withdrawn" discipline (the same style 27-03's own `style.css` comment amendment used). The hit-target entry's replacement figures were freshly measured, not estimated.
- **Files modified:** `.claude/skills/sketch-findings-skypane/SKILL.md`, `.claude/skills/sketch-findings-skypane/references/control-density.md`, `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md`
- **Committed in:** `d051313` (Task 4 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing-critical/design-system accuracy).
**Impact on plan:** Both auto-fixes are corrections to accuracy of surrounding documentation caused directly by this plan's own removal; neither touches unrelated code or rebuilds any control.

## Issues Encountered

An initial commit accidentally combined Task 2's and Task 3's files because both had been staged together earlier (as a safety net before running mutation tests, so a `git checkout-index -f --` revert had a known-good staged baseline to restore from). Caught immediately after the commit via `git show --name-only`; fixed with `git reset --soft HEAD~1` (no changes lost, nothing pushed) followed by two separate commits with the correct file sets. No destructive operation was used.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CFG-66/CFG-71 remain unticked in `.planning/REQUIREMENTS.md`, ready for 27-09 (the closing plan) to tick per this phase's established convention.
- No new script, no new route; the deferred-script pin is untouched at 15 (this plan removed markup, CSS and checks only).
- No blockers for 27-09 or any later wave-5-dependent plan.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

All 8 claimed files found on disk (7 modified files, this SUMMARY itself). All 3 task commit hashes (`42b0274`, `65f22c7`, `d051313`) found in `git log --oneline --all`.
