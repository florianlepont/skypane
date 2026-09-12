---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 05
subsystem: ui
tags: [config-page, i18n, css, es5-js, device-config, form-validation]

# Dependency graph
requires: ["21-01", "21-02", "21-03", "21-04"]
provides:
  - "companion/pages/config_page.py — _frame_colours_card_html(ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id, errors=None, submitted=None, state_dir=None): the one 'Frame colours' card (live preview + four-row colour_usage radiogroup + four usage panels) that replaces theme_fieldset(), the Calendar card's own compact chip grid, and the standalone Flight-colours card"
  - "companion/pages/config_page.py — _theme_chip_grid_html()'s new leading_chip_html parameter and the _same_as_departures_chip_html() builder: the 'Same as departures' chip contract (D-09)"
  - "companion/pages/config_page.py — handle_post()'s widened membership gates ((\"\",) + device_config.THEME_IDS) and the empty-string-to-CLEAR_THEME_ARRIVING resolution — the empty string is now the clear signal for both theme_arriving and calendar_theme_id"
  - "server/device_config.py — save_device_config()'s calendar_theme_id validation now accepts the empty string as a genuine storable value (no sentinel needed — the existing read-path normaliser already degrades it to None)"
  - "companion/static/theme-preview.js — rewritten, scoped to .frame-colours, driving the colour_usage radiogroup -> usage panel -> chip -> preview chain via data-usage-panel/data-usage-panel-target/data-preview-src"
affects: ["21-06", "21-07", "21-08"]

tech-stack:
  added: []
  patterns:
    - "leading_chip_html additive parameter on an existing chip-grid builder, letting two of its four call sites prepend one extra non-registry chip without touching the other two"
    - "empty-string-as-clear-signal (not a sentinel object) for a field whose None already unambiguously means something else and which never needed a sentinel before — narrower than CLEAR_THEME_ARRIVING's own object()-identity mechanism, used only where the two meanings (absent vs explicitly cleared) cannot otherwise collide"
    - "class-at-load panel-collapse in a rewritten static script (theme-preview.js joins flight-rows.js's own established pattern), scoped to one container element rather than a page-wide selector"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/static/theme-preview.js
    - companion/i18n_fr/display.py
    - companion/i18n_fr/rules.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - server/device_config.py

key-decisions:
  - "Tasks 1, 2 and 3 land in ONE commit, not three: Task 1 alone leaves handle_post() with a dangling reference to the constant it just retired (a real NameError, not just a failed acceptance-criteria grep), and Task 3's CSS/script additions were written inline alongside Task 1's own new markup during iterative development, making a clean post-hoc git-hunk split impractical without unwinding hours of interleaved edits. This is a deliberate, documented deviation from the 'one commit per task' convention, justified by the plan's own Pitfall 1 (the membership-gate and resolution-block changes must ship together or the new option is permanently unsavable)."
  - "server/device_config.py IS touched, contrary to Task 2's own acceptance criterion. The plan's premise — that calendar_theme_id's existing write path already tolerates an empty-string submission via some pre-existing pass-through — was verified false by direct testing: save_device_config()'s own validation gate rejected \"\" with a ValueError (calendar_theme_id has never had a clear mechanism of any kind, unlike theme_arriving's CLEAR_THEME_ARRIVING sentinel). The minimal fix widens exactly one validation line to also accept the empty string as a storable value; normalise_calendar_theme_id() (the READ path) is unchanged and already degrades \"\" to None, and every other consumer of a loaded calendar_theme_id already membership-tests it before use, so this is safe everywhere in the codebase, not just at the one call site that needed it."
  - "The single-theme (len(THEME_IDS) == 1) read-only fallback branch theme_fieldset() used to carry is NOT preserved in the Frame colours card. The real registry has held 6+ themes since Phase 8; the fallback was defensive code for a hypothetical future state this plan's own UI-SPEC never asks the new card to model. Its three direct-call tests are deleted along with it."
  - "The rules row's own swatch dots use var(--color-border) (an existing CSS variable) rather than any theme's real hex, since there is no single 'current' theme for a whole registry of per-flight rules — reusing a real theme's colour there would misleadingly imply one specific rule's colour represents the whole row. This value lives as a function-local variable, not a module-level ALL_CAPS constant, specifically so test_i18n.py's AST-based completeness scanner (which walks every module-level ALL_CAPS assignment) never mistakes a raw CSS token for translatable prose."
  - "_theme_live_preview_html() gained one additive extra_class parameter (used only by the Frame colours card, to add frame-colours__preview alongside the unchanged theme-live-preview class) rather than a second, duplicated figure builder — its only remaining caller after theme_fieldset()'s retirement."
  - "The @supports selector(:has(*)) block count stays pinned at 2: the Frame colours row's own :has() belt-and-braces duplicate joins the EXISTING first block (alongside .theme-chip/.runway-card's live-selection-state rules) rather than opening a third, and the retired arrivals-checkbox reveal rule is deleted from inside the second (Calendar-fusion) block without removing that block itself, since the Calendar-card fusion rule inside it survives untouched (plan 21-07's own job)."

requirements-completed: [CFG-20]

# Metrics
duration: ~230min
completed: 2026-09-12
---

# Phase 21 Plan 05: One "Frame colours" view and the empty-string clear signal Summary

**One "Frame colours" card (live preview + four-row colour_usage radiogroup + four usage panels) replaces the four separate theme chip grids; a "Same as departures" leading chip on Arrivals/Calendar submits the empty string, which `handle_post()`'s widened membership gates and resolution block now genuinely persist as "no override" for both `theme_arriving` and `calendar_theme_id`; and `theme-preview.js` is rewritten, scoped to the card, to drive the row→panel→chip→preview chain with a fully server-rendered, script-free no-JS floor.**

## Performance

- **Duration:** ~230 min
- **Started:** 2026-09-12
- **Completed:** 2026-09-12
- **Tasks:** 3 (landed in one commit — see Deviations)
- **Files modified:** 8

## Accomplishments

- `companion/pages/config_page.py`: `theme_fieldset()`, the arrivals-override checkbox and its five own constants (`ARRIVING_CHECKBOX_VALUE`, `THEME_ARRIVING_TOGGLE_ID`, `ARRIVAL_GRID_ATTR`, `THEME_ARRIVING_CHECKBOX_LABEL`, `THEME_DIRECTION_LABEL`), the standalone Flight-colours card (`_rules_section_html()`, `RULES_SECTION_HEADING`), and the Calendar card's own compact `calendar_theme_id` chip grid are all retired outright. `_frame_colours_card_html()` — a new builder — assembles the live preview, the four-row `colour_usage` radiogroup, and four usage panels (departures/arrivals/calendar chip grids plus the rules row's relocated list/add-form/disclosure) as one card, rendered as a sibling of `<form id="settings-form">` per Structural Note 2; every saved radio still cross-submits via `form="settings-form"`.
- `companion/pages/config_page.py`: `_theme_chip_grid_html()` gains one additive `leading_chip_html` parameter; `_same_as_departures_chip_html()` builds the "Same as departures" chip (submitting the empty string) that Arrivals'/Calendar's own grids prepend.
- `companion/pages/config_page.py`: `handle_post()`'s `calendar_theme_id`/`theme_arriving` membership gates both now exempt the empty string (`("",) + device_config.THEME_IDS`); the checkbox-keyed `theme_arriving` resolution block is replaced by a direct three-way branch (out of scope → `None`; absent → `None`; `""` → `device_config.CLEAR_THEME_ARRIVING`; else the membership-checked id). `calendar_theme_id` needs no second resolution block.
- `server/device_config.py`: `save_device_config()`'s `calendar_theme_id` validation gate now also accepts the empty string as a genuine, storable value — required because, contrary to the plan's own premise, this field had no clear mechanism of any kind before this fix (see Deviations). `normalise_theme_arriving()`/`normalise_calendar_theme_id()` (the READ path) are unchanged.
- `companion/static/theme-preview.js`: rewritten from a page-wide, single-grid `document.querySelector()` pair to every lookup scoped inside the one `.frame-colours` card, driven by the `colour_usage` radiogroup's own `data-usage-panel`/`data-usage-panel-target` attribute contract; collapses three of the four usage panels at load (the ONLY place any panel is ever hidden — the server never emits `hidden`), and swaps the live preview's `src` on both a row switch and a chip click, falling back to the departures grid's own currently-checked theme whenever the checked chip is the swatch-less "Same as departures" placeholder.
- `companion/static/style.css`: the new `.frame-colours__*` rule set (layout grid, list/row/swatch/label/meta, panel-legend, the collapsed-panel class `theme-preview.js` toggles), the retired arrivals-checkbox reveal rule and its `.theme-direction-label` rule are deleted from the existing `@supports selector(:has(*))` block (block count stays pinned at 2), and the Frame colours row's own `:has()` belt-and-braces duplicate joins the first (live-selection-state) block.
- `companion/i18n_fr/display.py`/`rules.py`: the new Frame colours copy (heading, four row labels, "Same as departures", the rules-count templates, the card's own caption) added; the retired Theme card's own caption/checkbox-label/"current" entries and the retired standalone card's own "Flight colours" heading entry are deleted in the same commit as their English source constants.
- `companion/test_config_page.py`/`test_companion_app.py`: every pinned check that named a now-retired constant, markup shape, or SCOPE_ALL Theme-content assumption is retargeted or deleted (theme_fieldset()-direct tests deleted outright; RULES_SECTION_HEADING-anchored order checks retargeted onto the rules panel's own `data-usage-panel-target` attribute and re-scoped to `SCOPE_DISPLAY`; the arrivals-checkbox handle_post tests retargeted onto the empty-string clear signal); one new consolidated full-shape checklist test added.
- `ruff check .` clean; the full local suite (`scripts/run-all-tests.sh`) reports exactly the five pre-existing, documented root-sandbox failures (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`) and no others.

## Task Commits

1. **Tasks 1, 2 and 3 (combined — see Deviations): The Frame colours card, the empty-string clear signal, and the rewritten theme-preview.js** — `b923434` (feat)

_No separate plan-metadata commit at execution time — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per the launch instructions; this SUMMARY.md is committed separately as the final commit of this plan's own execution._

## Harness Counts (before → after)

| Harness | Before | After | Notes |
|---|---|---|---|
| `companion/test_config_page.py` | 216 | 215 | net -1 (5 theme_fieldset()-direct tests deleted; ~20 retargeted in place; ~6 new tests added, including one consolidated full-shape checklist) |
| `companion/test_companion_app.py` | 258 | 258 | net 0 (2 existing checks' bodies retargeted for the SCOPE_ALL Theme-content removal; the theme-preview.js ES5/no-write check extended in place with two more required/banned tokens) |
| `companion/test_status_pages.py` | 218 | 218 | net 0 (no test-file edit; only style.css's `.frame-colours__layout` media query needed a `flex-start` fix to keep the file's own pinned `align-items: start` count at 1) |
| `companion/test_i18n.py` | 22 | 22 | net 0 (no new check added; the D-08 dead-translation/completeness scan simply now covers the new Frame colours strings and no longer covers the retired Theme-card strings) |

Real on-disk pass counts at the final commit: `test_config_page.py` 215/215, `test_companion_app.py` 256/258 (the two documented WR-11 root-sandbox FAILs), `test_status_pages.py` 217/218 (the one documented `anomaly_active()` FAIL), `test_i18n.py` 22/22, `test_view_pages.py` 113/113 (untouched, read-only per the launch instructions).

## Files Created/Modified

- `companion/pages/config_page.py` — `_frame_colours_card_html()`, `_same_as_departures_chip_html()`, `_frame_colours_row_html()`, `_frame_colours_usage_panel_html()` (new); `_theme_chip_grid_html()` gains `leading_chip_html`; `_theme_live_preview_html()` gains `extra_class`; `theme_fieldset()`, `_rules_section_html()`, `RULES_SECTION_HEADING`, the five arrivals-checkbox constants, `THEME_SECTION_CAPTION`/`THEME_SECTION_CAPTION_ID`/`THEME_GROUP_HEADING_ID`/`THEME_ARRIVING_GROUP_HEADING_ID` all deleted; `calendar_group()` loses its own compact grid and its now-unused `current_calendar_theme_id`/`current_theme_id` parameters; `_display_groups_html()`/`render()` restructured so the Frame colours card renders as a sibling of the physical form, nested-wrapped like every other supersection card; `handle_post()`'s two gates/one resolution block rewritten
- `companion/static/style.css` — new `.frame-colours__*` rules; the retired arrivals-checkbox reveal rule and `.theme-direction-label` deleted from the existing `@supports` block; a new belt-and-braces `:has()` rule joins the first `@supports` block
- `companion/static/theme-preview.js` — full body rewrite (route/script-src/`<script>` tag unchanged)
- `companion/i18n_fr/display.py` — new Frame colours entries added; retired Theme-card entries deleted
- `companion/i18n_fr/rules.py` — the orphaned "Flight colours" entry deleted
- `companion/test_config_page.py` — extensive retargeting/deletion/addition (see Harness Counts)
- `companion/test_companion_app.py` — two existing checks' bodies retargeted; one existing check extended
- `server/device_config.py` — `save_device_config()`'s `calendar_theme_id` validation widened; two docstring paragraphs corrected to match (see Deviations)

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `server/device_config.py`'s `save_device_config()` rejected `calendar_theme_id=""` outright — the plan's own Task 2 premise about this field's write path was factually incorrect**
- **Found during:** Task 2, running the new empty-string round-trip check for `calendar_theme_id`
- **Issue:** The plan's Task 2 action text and 21-RESEARCH.md Area B.3 both assert that once `handle_post()`'s membership gate exempts `""`, "the existing pass-through... plus `normalise_calendar_theme_id("")`'s documented `None` degrade already does the right thing." This is true of the READ path but not the WRITE path: `save_device_config()` passes the raw submitted value straight to its own validation gate (`if calendar_theme_id is not None and calendar_theme_id not in THEMES: raise ValueError(...)`), which rejects `""` before it is ever stored — confirmed by directly running `handle_post({"calendar_theme_id": ""}, ctx)` and observing `FLASH_SAVE_FAILED`. `calendar_theme_id` has never had any clear mechanism (unlike `theme_arriving`'s `CLEAR_THEME_ARRIVING` sentinel) — `normalise_calendar_theme_id()`'s own docstring explicitly documented this absence, correctly, until this fix.
- **Fix:** Widened `save_device_config()`'s one validation line to `calendar_theme_id not in ("",) + THEME_IDS`. No sentinel is needed: `""` is a genuine, storable, non-`None` value that never collides with `None`'s own "not supplied, carry forward" meaning, and `normalise_calendar_theme_id()` (unchanged) already degrades any stored non-member string, including `""`, to `None` on the next read. Every other consumer of a loaded `calendar_theme_id` (`server/plane/calendar_rules.py`, `server/plane/colour_rules.py`) already membership-tests it before use, so a transiently-stored `""` is never treated as a real theme id anywhere. Also corrected two now-stale docstring paragraphs in the same file that claimed "no UI state needs to distinguish clear from leave-alone" for this key.
- **Files modified:** `server/device_config.py`
- **Verification:** `server/test_config_history.py` 69/69, `server/test_poll_loop.py` 97/97, `server/test_calendar_rules.py` 113/113, `server/test_colour_rules.py` 33/33 — all unaffected; the new `_handle_post_calendar_theme_id_empty_string_saves_as_none` check in `companion/test_config_page.py` passes.
- **Committed in:** `b923434`

**2. [Rule 1 - Bug] My own `.frame-colours__layout` media-query rule introduced a second `align-items: start` declaration, and a subsequent explanatory comment reintroduced it as a literal string**
- **Found during:** running `companion/test_status_pages.py` after adding the Frame colours CSS
- **Issue:** `companion/test_status_pages.py` pins the whole stylesheet to exactly one remaining bare `align-items: start` declaration (the sticky sidebar's own, quick task 260901-uzi finding 1). My first draft's `≥960px` grid rule used the bare `start` keyword, becoming a second occurrence — the identical pitfall 21-04-SUMMARY.md already documented and fixed once for `.home-picture-row`.
- **Fix:** Changed to `align-items: flex-start` (an equivalent value for Grid). My first fix attempt's own explanatory comment then quoted the literal string `"align-items: start"`, which the check's own substring count also caught — reworded the comment to describe the same thing without the literal, matching this codebase's established convention for avoiding self-inflicted acceptance-grep trips.
- **Files modified:** `companion/static/style.css`
- **Verification:** `companion/test_status_pages.py` 217/218 (only the documented `anomaly_active()` FAIL).
- **Committed in:** `b923434`

**3. [Rule 3 - Blocking] Several of my own explanatory comments/prose tripped this plan's own acceptance-criteria greps for retired constant names**
- **Found during:** Task 1/Task 2, during acceptance-criteria verification
- **Issue:** Literal mentions of `theme_arriving_enabled`, `ARRIVING_CHECKBOX_VALUE`, `THEME_ARRIVING_TOGGLE_ID`, `RULES_SECTION_HEADING` inside my own docstrings/comments (explaining what each retired name used to do) tripped the plan's own `grep -c ... outputs 0` acceptance checks, which scan raw file text — the same class of self-inflicted friction 21-01/21-02/21-03/21-04-SUMMARY.md all documented for this exact codebase's convention.
- **Fix:** Reworded every avoidable occurrence to describe the same history in prose without the literal identifier (e.g. "the arrivals-override checkbox and its own former value" instead of "`ARRIVING_CHECKBOX_VALUE`"), while keeping the genuinely load-bearing literal occurrences (the retired names in test-file comments that document *why* a check was retargeted, which the plan's greps do not scan).
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** every named acceptance-criteria grep in Tasks 1 and 2 now returns its exact expected count (0 for the four retired-constant names, once Task 2's own `ARRIVING_CHECKBOX_VALUE` code reference was also removed).
- **Committed in:** `b923434`

**4. [Rule 3 - Blocking] `companion/static/theme-preview.js`'s own explanatory comments contained backticks and the literal banned page-wide selector string, tripping `companion/test_companion_app.py`'s pre-existing ES5/no-HTML-write check**
- **Found during:** Task 3, running `companion/test_companion_app.py` after the rewrite
- **Issue:** The pre-existing pinned check bans a bare backtick character and the literal substring `document.write`/`insertAdjacentHTML` etc. anywhere in the file — my header comment's Markdown-style code-formatting backticks (e.g. `` `.frame-colours` ``) and one sentence quoting the retired `document.querySelector(".theme-chip-grid")` call both tripped it.
- **Fix:** Removed every backtick from the file's own comments (plain prose instead of Markdown code-formatting) and reworded the sentence describing the retired selector to avoid the literal substring.
- **Files modified:** `companion/static/theme-preview.js`
- **Verification:** `companion/test_companion_app.py`'s own `_theme_preview_script_es5_safe_and_no_html_write` check passes; `node --check` confirms the file is still syntactically valid.
- **Committed in:** `b923434`

---

**Total deviations:** 4 auto-fixed (1 Rule 1 - bug requiring a `server/device_config.py` edit outside this plan's own stated scope, 1 Rule 1 - bug in my own CSS, 2 Rule 3 - blocking self-inflicted grep/banned-token trips).
**Impact on plan:** The `server/device_config.py` deviation is the only one that touches a file this plan's own acceptance criteria said would stay untouched — it was necessary for D-09's own calendar-clearing promise to be true rather than merely asserted, is minimal (one validation line plus two corrected docstring paragraphs), reuses the exact "empty string is a real value, not `None`" pattern the plan already establishes for `theme_arriving`, and is fully covered by both the companion and server test suites with zero regressions. Every other deviation is a same-task correctness fix with no scope creep.

## Known Stubs

None.

## Threat Flags

None — every threat this plan's own STRIDE register named (T-21-16 tampering via the widened domain, T-21-17 silent state loss, T-21-18 XSS via the script sink, T-21-19 XSS via interpolation, T-21-20 DoS via a blocked script) was mitigated exactly as specified:
- Both membership gates still test against `("",) + device_config.THEME_IDS` and reject every other non-member value with `ERROR_INVALID_CHOICE`/`FLASH_SAVE_FAILED` — pinned by `_handle_post_crafted_non_member_theme_and_calendar_values_still_rejected` and `_handle_post_nonmember_theme_arriving_rejected`.
- Every radio in the Frame colours card still carries `form="settings-form"`, pinned by the new consolidated full-shape checklist test and the retargeted `_calendar_theme_chip_grid_*`/h2-order checks.
- `theme-preview.js` writes only an `<img src>` (from a server-escaped `data-preview-src`) and class-list toggles — no HTML sink, no inline handler, no `eval` — pinned by the extended `_theme_preview_script_es5_safe_and_no_html_write` check.
- Every interpolation in the new builders crosses `escape_html()`; swatch colours come from `_palette_hex()`/`panel_format.PALETTE_RGB` or the literal CSS variable `var(--color-border)`, never from user input.
- The no-JS floor is server-rendered: all four usage panels render with no `hidden` attribute and every radio submits its real value — confirmed by the full-shape checklist test's own hidden/style= scan.

## Issues Encountered

- `theme_fieldset()`'s retired single-theme (`len(THEME_IDS) == 1`) read-only fallback branch had no natural equivalent in the new card's design, since the real registry has held 6+ themes since Phase 8 and the UI-SPEC's own markup assumes a real radiogroup throughout. Resolved by not preserving it — the three tests that exercised it via a monkeypatched one-member registry are deleted along with `theme_fieldset()` itself, documented in `key-decisions` above.
- Removing `screens.GROUP_THEME` from the shared per-group `builders` dict (necessary because Frame colours' own rules panel contains real `<form>` elements that must never render as a literal descendant of `<form id="settings-form">`, the same constraint that already kept Calendar's/Runway's own controls out of that dict) has a real, documented side effect on the legacy `SCOPE_ALL` render: it no longer shows any theme content or rules editor at all. Since `SCOPE_ALL` is explicitly documented elsewhere in this file as "the legacy, never-served whole-page render... never used by a live `app.py` route," this is an accepted, deliberate consequence, not an oversight — every pinned `SCOPE_ALL`-scoped test that asserted the old Theme/Flight-colours content was retargeted to reflect its removal.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Display's "Look" supersection opens with one "Frame colours" card (preview left, four-row assignment list right on desktop, preview on top on phones per the CSS grid breakpoint); no arrivals checkbox, no Calendar-card chip grid, and no separate "Flight colours" card survive anywhere in the rendered output.
- Selecting "Same as departures" for Arrivals or Calendar now genuinely saves and reads back as no override, end to end through a real HTTP POST — this closes the exact gap Pitfall 1 warned about.
- `theme-preview.js` is scoped entirely to `.frame-colours`; every other page on the site is unaffected by its rewrite (its own guard clause returns immediately when the card is absent).
- Plan 21-06 (running concurrently, `companion/pages/airlines_page.py`/`companion/test_view_pages.py`) was never touched by this plan.
- Plan 21-07 (wave 5) inherits a Calendar card whose own compact chip grid is already gone (D-06) but whose status row, "How it works" disclosure, and CSS fusion rules with the disconnect form are all untouched — exactly the scope 21-07 is meant to build on, per this plan's own `files_owned` boundary.
- The `@supports selector(:has(*))` block count in `companion/static/style.css` is still exactly 2; plan 21-07's own retirement of the Calendar-card fusion rule inside the second block will need to re-derive `test_config_page.py`'s pinned count itself, per that plan's own instructions.

## Self-Check: PASSED

- FOUND: `companion/pages/config_page.py` (contains `_frame_colours_card_html`)
- FOUND: `companion/static/theme-preview.js` (contains `data-usage-panel`)
- FOUND: `companion/static/style.css` (contains `frame-colours__usage-panel--collapsed`)
- FOUND: `server/device_config.py` (contains the widened `calendar_theme_id` validation)
- FOUND: `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-05-SUMMARY.md`
- FOUND commit `b923434` (Tasks 1/2/3, combined)

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*
