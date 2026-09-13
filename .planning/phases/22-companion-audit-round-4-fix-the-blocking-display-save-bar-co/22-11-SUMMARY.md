---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 11
subsystem: ui
tags: [airlines, lightbox, paris-local-time, css-grid, filter-bar, i18n-fr, playwright]

requires:
  - phase: 22-06
    provides: "layout.local_clock_text()/concise_timestamp_html() as D-05 left them — the one visible-time formatter this plan's dialog text is derived from"
  - phase: 22-09
    provides: ".filter-bar__meta, the shared count+Clear group this plan adopts verbatim; .calendar-disconnect-btn's Flights picture-control call site"
  - phase: 22-10
    provides: "the ..._SINGULAR sibling convention for plural copy (Calendar status detail)"
provides:
  - "B5: the resolve dialog reads in Paris local time, byte-identical to the no-JS path, with Save and Close on one action row"
  - "X7: a normal-case Change pictures toggle, a visible Editing badge, a per-card Replace picture control, two cards per row at 390px, and the manual count as a filter control"
  - "B11: Airlines' count and Clear share one line at 390px via the shared group"
  - "CFG-29's Airlines half: the manual-resolution plural pair gains singular forms"
  - ".calendar-disconnect-btn's SECOND consumer — the fact 22-16's §4 edit must record alongside 22-09's Flights call site"
affects: [22-12, 22-15, 22-16]

tech-stack:
  added: []
  patterns:
    - "A data attribute carrying formatted text is derived from the no-JS path's OWN formatter call with its tags stripped, never composed a second time"
    - "A second trigger for the shared lightbox carries the full fifteen-attribute vocabulary from one interpolation, never a subset"
    - "A lifted submit is re-attached to its form by the native form= attribute; the scriptless path keeps its own in-form submit"

key-files:
  created: []
  modified:
    - companion/pages/airlines_page.py
    - companion/static/panel-lookup.js
    - companion/static/style.css
    - companion/i18n_fr/airlines.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py
    - companion/test_status_pages.py

key-decisions:
  - "The dialog's timestamp text is _seen_attribute_text(): layout.concise_timestamp_html()'s own output with its <span> stripped — literally the same call the no-JS path makes, so the two cannot drift"
  - "The dialog's Save is lifted out of its form into .lightbox__actions and re-attached by form=; panel-lookup.js mirrors the form's own hidden state rather than repeating the mode test"
  - "The per-card Replace control carries the full data-view-panel vocabulary from one shared interpolation, because panel-lookup.js's attr || \"\" idiom would blank the dialog on a subset"
  - "The manual-resolution count wears .airline-card__chip verbatim; .manual-summary's copied [data-filter-clear] property list is deleted, leaving only a hover"
  - "Four checks in test_status_pages.py were retargeted in place and narrowed, not loosened — one of them had a premise that was already false before this plan"

patterns-established:
  - "Tag-stripping one markup-producing formatter is how a data attribute and a rendered <dd> stay byte-identical"
  - "A card-scoped placement rule (.airline-card .calendar-disconnect-btn) adds margin/width only, so the component keeps exactly one base rule for every consumer"

requirements-completed: [CFG-28, CFG-30]

duration: 96min
completed: 2026-09-13
---

# Phase 22 Plan 11: Airlines (B5 / X7 / B11) Summary

**The resolve dialog now reads "9 Sep 17:49 (3d ago)" instead of "2026-09-09T15:49:27+00:00", edit mode visibly changes every card, and the Airlines page at 390px fell from the audit's 5800px to a measured 2594px.**

## Performance

- **Duration:** ~96 min
- **Tasks:** 3 of 3
- **Files modified:** 7
- **Harness deltas:** view-pages 136 -> 143, browser-ux 9 -> 11, status-pages 252 (4 checks retargeted in place, no count change)

## Accomplishments

- **B5/D-05.** `data-view-panel-first-seen`/`-last-seen` carry formatted Europe/Paris text produced by `_seen_attribute_text()`, which strips the tags off the no-JS path's own `layout.concise_timestamp_html()` call. The JS path's attribute value and the no-JS path's rendered `<dd>` text are asserted byte-for-byte equal, and a seeded render of the whole page carries **zero** ISO-8601 timestamps. `panel-lookup.js` gained no date code — it is now pinned free of `new Date(`, `Date.now`, `toISOString`, `toLocale*`, `getHours`, `getMinutes`, `getTime` and `Intl.DateTimeFormat`.
- **B5 (action row).** Save and Close share one `.lightbox__actions` row, quiet Close left and primary right. The Save is lifted out of `.lightbox__resolve-name` and re-attached with `form="manual-resolve-form-dialog"`; the no-JS fallback keeps its submit inside its own form.
- **X7.** Normal-case toggle and caption, an `Editing` `.banner__pill` badge, one `.calendar-disconnect-btn` "Replace picture" control per card in edit mode, a fixed two-column grid below 960px, and the manual-resolution count moved into the filter bar as a chip-voiced control.
- **B11.** Airlines adopts `.filter-bar__meta` verbatim; measured equal tops at 390px.
- **CFG-29's Airlines half.** `MANUAL_SUMMARY_TEMPLATE_SINGULAR` and `MANUAL_SUMMARY_TEMPLATE_NONE_SINGULAR`, each with its own French entry.

## Task Commits

1. **Task 1: the resolve dialog reads in Paris local time, on one action row** — `5e09fa3` (fix)
2. **Task 2: editing mode becomes visible, and the grid fits a phone** — `6c1ed78` (feat)
3. **Task 3: adopt the shared filter group so Clear stays on its line** — `81d9701` (fix)
4. **Plan close (docs)** — the tip commit carrying this SUMMARY, STATE.md, ROADMAP.md and REQUIREMENTS.md (a hash cannot be self-cited inside its own content)

## Acceptance criteria — every one run literally

| Criterion | Result |
|---|---|
| T1: a rendered resolve dialog contains zero ISO-8601-shaped strings | PASS — `re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", rendered)` returns `[]` for both the gallery and the resolve-fallback render |
| T1: the JS path's attribute value equals the no-JS path's rendered text for the same row | PASS — both `"9 Sep 17:49 (3d ago)"`; asserted with `==`, not by shape |
| T1: `grep -cE "new Date\(\|toISOString\|getHours\|getMinutes" companion/static/panel-lookup.js` outputs `0` | PASS — `0` |
| T1: `test_view_pages.py` M/M at its new pin; `test_i18n.py` exits 0 | PASS — 139/139 at the Task-1 pin; i18n exit 0 |
| T1: `ruff check .` clean | PASS |
| T2: toggle label normal case, and `grep -v '^ *[*/]' style.css \| grep -c "\.btn--"` outputs `0` | PASS — `0` |
| T2: an edit-mode render carries the badge and one Replace control per card; a normal render carries neither | PASS — 1 badge, 27 controls / 27 cards; 0 and 0 out of edit mode |
| T2: the browser check reports exactly two cards per row at 390px | PASS — after a correction; see Deviations |
| T2: `grep -c "^\.calendar-disconnect-btn {" style.css` outputs `1` | PASS — `1` |
| T2: `test_view_pages.py` M/M at its new pin; `test_i18n.py` exits 0 | PASS — 143/143; i18n exit 0 |
| T3: at 390px Airlines' count and Clear report equal bounding-box tops | PASS — measured in a real browser |
| T3: `grep -c "^\.filter-bar__meta" style.css` outputs `1` | PASS — `1` |
| T3: `grep -c '@supports selector(:has(\*)) {' style.css` outputs `1` | PASS — `1` |
| T3: `run-all-tests.sh` shows no new failure and coverage stays >= 83 | PASS — the same five failing check NAMES as the baseline; TOTAL coverage 93% (`fail_under = 83`) |
| T3: `ruff check .` clean | PASS |

**No acceptance criterion evaluated differently from how the plan predicted its outcome.** Two criteria needed the test I wrote to be corrected before they could be evaluated honestly — recorded under Deviations, not here, because in both cases the criterion was right and my first measurement was wrong.

## Targets

| Target | Stated | Measured | Verdict |
|---|---|---|---|
| Cards per row at 390px | exactly 2 | 2 in both grids (curated and the gap strip) | met |
| Card width at 390px | "about 159px" | **159.0px** in the main grid, 142px in the narrower gap strip | met |
| Airlines page height at 390px | "roughly halving" the audit's 5800px | **2594px** (a 55% reduction) | met, with margin |
| Count and Clear tops at 390px | equal | equal | met |

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] The `panel-lookup.js` ES5-safety guard rejected a backtick in my own comment**

- **Found during:** Task 1
- **Issue:** `test_companion_app.py`'s ES5-safety guard greps the WHOLE source of `panel-lookup.js` for a backtick, comments included. A `` `.lightbox__actions` `` in a code comment I added failed it (companion-app 258/261 instead of 259/261).
- **Fix:** The comment quotes the class name without backticks.
- **Files modified:** `companion/static/panel-lookup.js`
- **Commit:** `5e09fa3`

**2. [Rule 3 - Blocking] Four checks in `companion/test_status_pages.py` — a file this plan does not list in `files_modified` — had their premises changed by this plan's own work**

Retargeted in place and **narrowed**, never loosened. The file is not named in this plan's `files_modified`, but it is also not named in `<files_owned>`'s exclusion list, this plan is its wave's only agent, and D-09's regression floor cannot hold otherwise.

- **`_06_6_4_1_1_03_mobile_button_override_block_and_source_order`** — *its stated premise was already false before this plan.* The check described "**the** file's `@media (max-width: 959.98px)` block" and read `css_source.index(marker)` — the **first** such block. `style.css` has carried **five** such blocks for some time; the assertion only ever worked because the mobile `button` override happened to be the earliest. This plan's `.illustration-grid` two-column rule sits earlier in the file, which silently retargeted the assertion onto an unrelated block. Now every sub-960px block is scanned, **exactly one** must declare the bare `button { height: 36px; font-size: 14px; }` rule (two would be a real ambiguity), and *that* block must follow the base rule in source order. Strictly stronger.
- **`_replace_form_action_matches_trigger_attribute_membership`** — expected 27 `data-view-panel-replace-action` attributes, got 54, because an edit-mode card now carries two triggers for the same dialog. Retargeted to `2 x len(target_airline_names())` **plus** a new per-airline pairing assertion (each action must appear exactly twice) **plus** a new assertion that a non-edit render carries exactly one per airline. The old bare total could not have caught a card gaining a third trigger; the new one can.
- **`_manual_summary_line_replaces_retired_management_table_copy`** — the control's class attribute is now `class="airline-card__chip manual-summary"`. Retargeted onto the new composed shape (so dropping the chip voice would fail) and **extended** with a new assertion that the control renders *inside* the filter bar, which is the half of X7 a class-name check cannot see.
- **`_lightbox_and_gap_card_style_contract`'s Component Inventory expectations** — `.manual-summary {`'s base rule is gone (its body was a byte-for-byte copy of `.filter-bar [data-filter-clear]`'s property list, i.e. the 12px bare link the audit rejected). The expectation is **inverted rather than deleted**: the base rule must now be *absent*, so a future plan cannot quietly reinstate the fork; `.manual-summary:hover` must deepen to the chip's own 12% wash and no newly-invented strength; and `.airline-card__chip`'s own label-voice declarations are now pinned, because they are the control's whole treatment.

- **Files modified:** `companion/test_status_pages.py`
- **Commit:** `6c1ed78`
- **Result:** `status-pages` returned to its exact baseline, 251/252, with the single `anomaly_active()` root-sandbox failure and nothing else.

### Corrections to my own new tests, before they could evaluate a criterion

**3. The first "two cards per row" browser check measured the wrong thing.** It pooled `.illustration-grid .airline-card` boxes from **both** grids on the page — the curated grid and the gap strip's narrower `.illustration-grid--gap` — into one top-keyed histogram, and reported "row 0 held 1" for the single gap card. The criterion was correct; my measurement merged two independent layouts. Rewritten to measure each grid on its own. Recording it because the first failure looked like a CSS defect and was not.

## Exceptions added or removed

**None added. None removed.** No test exception, allowance or tolerance was introduced by this plan. The four `test_status_pages.py` edits are retargets of existing assertions onto changed premises, each strictly narrower than what it replaced; every one of them still fails on a drift.

## Requirements ticked

| ID | Action | Reasoning |
|---|---|---|
| **CFG-28** | **Ticked complete** | Served by exactly two plans in the whole phase (`grep -l CFG-28 *-PLAN.md` returns 22-06 and 22-11, and no other plan's `requirements:` names it). 22-06 landed the battery/tooltip half; this plan landed the resolve-dialog half, which was the only remaining clause. The "raw ISO only behind a copy control" clause holds on Airlines by assertion: the whole rendered page carries zero ISO-8601 strings. |
| **CFG-30** | **Traceability row updated only, left unchecked** | Served by nine plans (22-03, 22-04, 22-07, 22-09, 22-10, 22-11, 22-12, 22-13, 22-14). X7 is landed in full and B11's Airlines third is landed; Health's third is 22-12's, and B12/B13/B16/X3/X8 remain. |
| **CFG-29** | **NOT ticked; traceability row updated only** | As instructed: the Airlines plural pair landed here, but `health_page.py`'s plurals are 22-12's, and the requirement is not met until both land. |

## Notes for plan 22-16 (the design-system sweep)

1. **§4's X7 row must name BOTH new `.calendar-disconnect-btn` call sites, not one.** This plan is that component's **second** consumer (the Airlines per-card "Replace picture" control). 22-09 added a **third** — the Flights picture control at its own new call site, recorded in 22-09-SUMMARY.md. `references/control-density.md`'s prediction that it was "the pattern to reuse the next time this app needs a small, deliberately de-emphasized secondary action" is now confirmed **twice over**, and it is still not a `.btn` family: `grep -c "^\.calendar-disconnect-btn {"` returns `1`, and `.btn--` returns `0`.

2. **`.calendar-disconnect-btn` gained a card-scoped placement rule**, `.airline-card .calendar-disconnect-btn { display: block; width: 100%; margin-top: var(--space-sm); }`. It declares placement only — no size, colour, border or radius — so the single base rule remains the one definition of that component's geometry. Worth stating in the skill as the reuse discipline, since it is what kept the base rule singular.

3. **A new touch-target register entry is needed, and I did not make it.** The manual-resolution filter control is now a `<button>` wearing `.airline-card__chip`, i.e. **20px high**. UI-SPEC §2's X7 row prescribes "reusing the `.airline-card__chip` label voice", which I followed verbatim; but a 20px interactive control is below the 30/36px register and far below 44px. It *replaces* a 12px bare underlined link with no declared box at all, so this is strictly an improvement and not a regression — but `references/control-density.md`'s register has no entry for it either way, and 22-16 should add one (as a stated, justified exception, or by re-examining the height). Flagging rather than silently changing the prescribed treatment.

4. **`.banner__pill` gained a consumer** (the Airlines "Editing" state badge on the page header), reused verbatim with no modifier. If §4 enumerates that class's consumers anywhere, the count changes.

5. **`.page-header__screen` is doing two jobs and now needs two rules.** On the Device page it is a label-voice *caption* (`<p class="page-header__screen text-label">`), where its `text-transform: uppercase` is correct. On Airlines it is a *wrapper `<div>`* around the toggle and its caption, which is how the uppercase leaked onto a button (X7's own defect). The fix is `text-transform: none` on `.airlines-edit-toggle` plus `.page-header__screen .section-caption { text-transform: none; }` — the descendant selector cannot reach Device's usage, where the class is on the element itself. The underlying class-doing-two-jobs is untouched and is worth a note.

6. **`.resolve-context` stopped rendering on browser defaults.** Its Phase 13 comment said "This file declares no `dl`/`dt`/`dd` rule of its own anywhere". That is no longer true: the audit's "hand-indented `<dl>`" was the UA's `dd { margin-inline-start: 40px }`, and the list is now a two-column grid with a scoped `.resolve-context dt, .resolve-context dd { margin: 0 }`. Health's own definition list is untouched and still on defaults.

## Notes for plan 22-12 (Health)

- `.filter-bar__meta` is adopted here **verbatim** with no per-page variant. It fitted this page's filter bar without one; nothing differs. Health is the third and last adopter.
- Once Health adopts it, `.filter-bar__count { margin-left: auto }` (the standalone declaration 22-09 kept because "Airlines and Health still render a bare count with no wrapper") has **no remaining consumer** and becomes dead. It is inert inside the group, so I left it — but 22-12 is the plan that can honestly retire it.
- **CFG-29 is one plan away.** The Airlines plural pair is done; `health_page.py`'s is the last.

## Notes for plan 22-15 (CSS/JS defects)

- **T6 is visible on the Airlines cards and I left it alone**, as instructed. `.airline-card:hover, .airline-card:focus-within` sets `border-color: transparent` while the resting card carries a 1px hairline, and 22-10's own B9 browser check already records the selected-card 2px-vs-1px shift as T6/22-15's. Nothing in this plan touched `.airline-card`'s border.
- The new `.lightbox__actions` row deliberately declares **no** `height`, `min-height` or `border-radius`: per 22-UI-SPEC.md §4's C4, Close and Save read as two *separate objects* on a shared row, so they are centre-aligned and each keeps its own registered geometry. A future plan "tidying" them to a shared height would be reversing C4, not completing it. The view-pages check asserts the absence of those three declarations.

## Confirmation requested by the plan

**`panel-lookup.js` performs no date math anywhere — confirmed from source, read in full (382 lines before this plan, 393 after).** Its only interaction with the two timestamp values is `getAttribute("data-view-panel-first-seen") || ""` at what is now line 227 and `contextFirstSeen.textContent = firstSeen;` at line 240 (and the identical pair for `last-seen`). There is no `Date` constructor, no `Date.now`, no `toISOString`, no `toLocale*`, no `getHours`/`getMinutes`/`getTime` and no `Intl.DateTimeFormat` in the file — asserted by a new source scan, not only by reading. The one behavioural line added to the file this plan is a visibility mirror (`resolveSubmit.hidden = resolveNameForm.hidden;`), which repeats no mode test and parses nothing.

## Harness pins — old and new

| Harness | Before | After | Why |
|---|---|---|---|
| `companion/test_view_pages.py` | 136 | **143** | +3 (Task 1: Paris-local attribute equality, the no-date-math source scan, the one action row) and +4 (Task 2: normal-case toggle, badge + per-card control, the filter-bar chip with its singular plural, the fixed two-column template). Re-derived by **running** the harness at each step (139/139, then 143/143). |
| `companion/test_browser_ux.py` | 9 | **11** | +1 (Task 2: two cards per row at 390px, equal columns, page under 3200px) and +1 (Task 3: Airlines' count and Clear tops). Re-derived by **running** the harness (10/10, then 11/11). |
| `companion/test_status_pages.py` | 252 | **252** | Four checks retargeted in place; no count change. |
| `companion/test_config_page.py` | 232 | **232** | Untouched; the `:has()` gate unmoved (`grep -c` returns 1). |
| `companion/test_i18n.py` | 24 | **24** | Untouched; the five new French entries pass the widened scanner. |
| `companion/test_companion_app.py` | 261 | **261** | Untouched. |

## Regression floor

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` reports the **same five failing check NAMES** as the pre-plan baseline, not merely the same number of failing files:

1. `add_entry()` returns ADD_FAILED ... read-only (WR-11)
2. `delete_entry()` returns False ... read-only (WR-11)
3. `POST /airlines/resolve` ... `manual_save_failed` ... read-only (WR-11)
4. `POST /airlines/manual-resolutions/{prefix}/delete` ... `manual_delete_failed` ... read-only (WR-11)
5. `anomaly_active()` ... expected False for a non-existent state_dir path

All five are the documented root-sandbox artefacts (uid 0 cannot trip a read-only directory). Pass counts are at baseline in every harness: `manual_resolutions` 21/23, `companion-app` 259/261, `status-pages` 251/252. Coverage TOTAL **93%** against `fail_under = 83`.

## Threat model

| Threat ID | Disposition | How it landed |
|---|---|---|
| T-22-38 | mitigated | `_seen_attribute_text()`'s return value crosses `escape_html()` at its attribute interpolation site, exactly as the raw value did. The formatter never raises (`concise_timestamp_html()` degrades on an unparseable input) and never emits markup into the attribute — its `<span>` is stripped before escaping. |
| T-22-39 | mitigated | The per-card Replace control opens the same shared dialog and the same already-authorised replace/upload form. `_lightbox_html()`'s own `edit_mode` gate on the replace and delete forms is untouched, and the routes those forms post to are unchanged. Only the affordance's position changed. |
| T-22-40 | mitigated | `panel-lookup.js` copies verbatim into `textContent` and parses nothing; the value it copies was escaped server-side. Pinned by the no-date-math source scan, which also asserts the two values reach `textContent` unmodified. |
| T-22-41 | accepted | The manual-resolution filter control is still a read-side filter over rows the page already renders — the move into the filter bar changed its position and its class, not its behaviour, and `list-filter.js` needed no change at all. |
| T-22-SC | n/a | Zero packages installed in any ecosystem. |

## Known stubs

None. No hardcoded empty value, placeholder string or unwired component was introduced. `_seen_attribute_text()` returns `""` for a falsy timestamp, which is the pre-existing empty-attribute state every other optional `data-view-panel-*` value already uses, not a stub.

## Self-Check: PASSED

- `companion/pages/airlines_page.py` — FOUND
- `companion/static/panel-lookup.js` — FOUND
- `companion/static/style.css` — FOUND
- `companion/i18n_fr/airlines.py` — FOUND
- `companion/test_view_pages.py` — FOUND
- `companion/test_browser_ux.py` — FOUND
- `companion/test_status_pages.py` — FOUND
- commit `5e09fa3` — FOUND
- commit `6c1ed78` — FOUND
- commit `81d9701` — FOUND
