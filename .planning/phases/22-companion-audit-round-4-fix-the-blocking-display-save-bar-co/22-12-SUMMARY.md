---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 12
subsystem: ui
tags: [health, stat-tile, empty-state, dot-off, data-table, i18n-fr, filter-bar, time-value, playwright]

requires:
  - phase: 22-03
    provides: "_pipeline_section()'s never-ran branch and its hand-built .dot--off verdict, which this plan's tile anatomy wraps rather than rewrites"
  - phase: 22-04
    provides: ".time-value / .time-value--primary as C5 defined them, and .dot--off's first consumer this phase (the frame's held state)"
  - phase: 22-09
    provides: ".filter-bar__meta, the shared count+Clear group this plan adopts verbatim as its third and last adopter"
  - phase: 22-11
    provides: "the ..._SINGULAR_TEMPLATE sibling convention, and the note naming this plan as the one that could honestly retire .filter-bar__count's margin-left"
provides:
  - "X8: one tile anatomy across all four Health tiles — label, one Emphasis-role element, one muted detail slot, in that fixed order"
  - "X8: 'Only one saw it' on the neutral .dot--off with its visible label intact — .dot--off's SECOND consumer this phase"
  - "layout._STATUS_DOT_CLASSES gains an additive 'off' entry, so status_dot() can render the neutral dot without a hand-rolled copy"
  - "C1: layout.empty_state(heading, body, compact=True), with the default form proven byte-identical against a real existing caller"
  - "B12: the unresolved-prefix table fits 1280px in BOTH languages — 886/1026 before, 830/830 after — decided by headless measurement"
  - "the second consumer of the Flights stacked-cell precedent, scoped to its own data-table--registry modifier"
  - "B11: Health's count and Clear share one line at 390px, closing B11 across all three filtered pages"
  - "C5: the page header's 'Updated HH:MM' on .time-value, the last of the four monospace time treatments on this page"
  - "CFG-29's last clause: the Resolution-rate detail line's singular form"
affects: [22-13, 22-14, 22-15, 22-16]

tech-stack:
  added: []
  patterns:
    - "A tile's detail slot is ONE wrapper element regardless of how many lines it holds, which is what makes 'exactly one detail slot, in third position' machine-checkable"
    - "A compact component variant reaches an existing treatment through its OWN class names, never by borrowing a semantically-named class from another component"
    - "A test that slices a component out of rendered HTML scans balanced tags, never 'up to the next closing tag'"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/layout.py
    - companion/static/style.css
    - companion/i18n_fr/health.py
    - companion/test_status_pages.py
    - companion/test_browser_ux.py
    - companion/test_view_pages.py

key-decisions:
  - "The Emphasis slot is one element per tile but two class names: a verdict word on three tiles, and .stat-tile__value's FIGURE on the Resolution-rate tile, because D-03/A-21 forbids that tile from making a judgement and test_status_pages.py pins the absence of a verdict there"
  - "The compact empty state uses .empty-state__heading/.empty-state__body's own (previously rule-less) class names rather than borrowing .widget-verdict/.widget-detail — borrowing broke the Resolution-rate tile's no-verdict pin on its own empty branch, which is how the decision was found"
  - "Lever 1 (shorter French headers) was measured to be arithmetically incapable of fitting the table on its own; lever 2 (stacked cells) was required, lever 3 (the card fallback) was not"
  - "The mobile cards keep concise_timestamp_html() unchanged; the retired byte-identity between card and row is replaced by the same-formatters property, asserted on both sides"
  - ".filter-bar__count's margin-left: auto is retired with this plan's adoption, exactly as 22-09 scheduled and 22-11 predicted"

patterns-established:
  - "An empty tile occupies the same verdict and detail slots a filled tile does, so the four-slot check needs no empty-state exemption"
  - "A second consumer of a measured local exception (stacked cells) restates the measurement that justified it rather than citing the first consumer's"

requirements-completed: [CFG-29]

duration: 118min
completed: 2026-09-13
---

# Phase 22 Plan 12: Health (X8 / B12 / B11 / C1 / C5) Summary

**All four Health tiles now read label → one bold answer → one muted piece of evidence, "Only one saw it" stopped being painted the same green as "Both agree", and the French unresolved-prefix table fell from a measured 1026px inside an 830px wrap to exactly 830px.**

## Performance

- **Duration:** ~118 min
- **Tasks:** 3 of 3
- **Files modified:** 7
- **Harness deltas:** status-pages 252 → 258, browser-ux 11 → 14; view-pages/config-page/i18n/companion-app/contrast-check all unchanged in count

## Accomplishments

- **X8, one anatomy.** A single `_tile_body(verdict_html, detail_html, link_html="")` builds every tile: `<p class="text-body widget-verdict">` then `<div class="text-label widget-detail">`. The Device and Pipeline timestamps left `.stat-tile__value` — the Emphasis role their verdict already occupied one line above, which *was* the audit's "double bold verdict". The Pipeline tile's second line ("Last aircraft detected") moved inside the one detail slot rather than trailing the tile as a fourth top-level element. The Frame tile's next-wake clock dropped `time-value--primary` (the Emphasis shape) for the base `.time-value` supporting-value shape; the Frame strip's own headline keeps the modifier and is asserted to.
- **X8, the neutral state.** `_CORROBORATION_ROWS`'s `"None"` row and `corroboration_status()` both moved from `"ok"` to `"off"`. `layout._STATUS_DOT_CLASSES` gained an additive `"off": "dot--off"` entry so `status_dot("off", label)` renders the neutral dot plus its normal visible `.dot-label` — all three corroboration rows keep one markup shape. No fifth dot, no third colour: `grep -oE "^\.dot--[a-z]+" | sort -u | wc -l` is **4 before and 4 after**.
- **C1, the compact empty state.** `layout.empty_state(heading, body, compact=True)` renders a 16px sans semibold heading and a 14px body at the file's single 70% muted strength. `.empty-state__heading` and `.empty-state__body` gained the first CSS rules they have ever had, scoped to the compact wrapper. Health's two IN-tile empty states adopt it; its two full-width card empty states keep the default form, and that split is asserted.
- **B12, by measurement.** Headless Chromium, 1280px viewport, `.data-table-wrap` clientWidth 830px. Before: EN **886**, FR **1026**. After stacking the two timestamp cells: EN **830**, FR **900**. After also shortening the two French headers: EN **830**, FR **830**. Resolve column right edge inside the wrap's own box, and no clipped header, in both languages.
- **B11, the third and last.** Health adopts `.filter-bar__meta` verbatim, with its `<a href="#...">` Clear left as-is (D-16 forbids a `<button>` here). `.filter-bar__count { margin-left: auto }` retired — 22-09 kept it with a stated expiry and this adoption is that expiry.
- **C5.** `<span class="mono" data-refresh-clock>` → `<span class="time-value" data-refresh-clock>`.
- **CFG-29's last clause.** `_RESOLUTION_DETAIL_SINGULAR_TEMPLATE` with its own French entry, so a window holding one detection never reads "1 events" / "1 événements".
- **D8/Phase 23 stated, not omitted.** A comment at the chart's assembly in `_battery_section()` names every part of the audit's X8 chart clause (area fill, marked last point, 3.3–4.2 V range, threshold line) and records that all of it is scoped to D8/Phase 23 by 22-CONTEXT.md and 22-UI-SPEC.md §6. The chart is byte-for-byte unchanged.

## Task Commits

1. **Task 1: one tile anatomy, a neutral single-source state, a compact empty state** — `5789877` (fix)
2. **Task 2: the unresolved-prefix table fits 1280px in French, decided by measurement** — `9b64370` (fix)
3. **Task 3: the third filter bar joins the shared group, and the page clock leaves mono** — `f80fcbb` (fix)
4. **Plan close (docs)** — the tip commit carrying this SUMMARY, STATE.md, ROADMAP.md and REQUIREMENTS.md (a hash cannot be self-cited inside its own content)

## Acceptance criteria — every one run literally

| Criterion | Result |
|---|---|
| T1: every tile on a rendered Health page carries exactly one verdict element and the four slots in the fixed order | PASS — asserted over every `.stat-tile` on both a seeded page and a fresh install (4 tiles each), by balanced-tag slice |
| T1: "Only one saw it" renders with the neutral dot and a distinct visible label | PASS — `<span class="dot dot--off"></span><span class="dot-label">Only one saw it</span>` in EN and `Une seule l’a vu` in FR, while "Both agree" keeps `dot--ok` |
| T1: `grep -oE "^\.dot--[a-z]+" companion/static/style.css \| sort -u \| wc -l` equals its pre-task value | PASS — **4** now, **4** at `9f5d7dc` (the pre-plan tip). No fifth dot |
| T1: the default `empty_state()` output is byte-identical to the pre-change output for an existing caller | PASS — asserted against a written-out literal AND against `layout.data_table(["A"], [])`, a real existing caller |
| T1: `test_status_pages.py` M/M at its new pin apart from the documented `anomaly_active()` FAIL; `test_view_pages.py` still M/M | PASS — 256/257 at the Task-1 pin; view-pages 143/143 |
| T1: `ruff check .` clean | PASS |
| T2: the browser check reports `scrollWidth === clientWidth` at 1280 px in both languages | PASS — 830/830 in EN and FR; Resolve column inside the wrap's box; zero clipped headers |
| T2: the measured widths before and after are recorded in the SUMMARY | PASS — see the Targets table below |
| T2: `companion/test_i18n.py` exits 0 with no orphaned French header | PASS — 24/24, exit 0. The two changed values sit on their existing, still-live English keys; no key was added or orphaned |
| T2: `test_status_pages.py` M/M at its new pin apart from the documented `anomaly_active()` FAIL | PASS — 257/258 |
| T2: `ruff check .` clean | PASS |
| T3: at 390 px the Health filter count and Clear report equal bounding-box tops | PASS — measured in a real browser |
| T3: `grep -c "^\.filter-bar__meta" companion/static/style.css` outputs `1` | PASS — `1` |
| T3: the page header's timestamp markup carries no monospace class | PASS — `<span class="time-value" data-refresh-clock title="…">06:03</span>`; also asserted in the browser via `el.className` |
| T3: the no-JS floor check passes at this commit | PASS — with scripts blocked, all four tiles render their label/verdict/detail slots exactly once each, the filter bar and Clear render, the unresolved-prefix rows render, and the visible Resolve link actually navigates to `/airlines?resolve=…` |
| T3: `grep -c '@supports selector(:has(\*)) {' companion/static/style.css` outputs `1` | PASS — `1` |
| T3: `scripts/run-all-tests.sh` shows no new failure and coverage stays at or above 83 | PASS — the same five failing check NAMES as the baseline; TOTAL coverage **93%** |
| T3: `ruff check .` clean | PASS |

**No acceptance criterion evaluated differently from how the plan predicted its outcome.** Two `<read_first>` statements did not match the codebase and are recorded under Deviations rather than here, because neither is a criterion.

## Targets

| Target | Stated | Measured | Verdict |
|---|---|---|---|
| `.data-table-wrap` scrollWidth vs clientWidth at 1280px, FR | equal | **830 / 830** (was 1026 / 830) | met |
| Same, EN | equal, "neither language's headers are clipped" | **830 / 830** (was 886 / 830) | met — and worth naming: **English overflowed too**, by 56px. The audit row named only French |
| Resolve column reachable without horizontal scrolling | reachable | right edge inside the wrap's own box in both languages | met |
| Filter count and Clear tops at 390px | equal | equal | met |
| `.dot--*` rule count | unchanged | 4 → 4 | met |

### The lever decision, as the measurement made it

Per-column ink at 1280px (French, before any change), wrap budget 830px:

| Column | header ink | widest cell ink | column width |
|---|---|---|---|
| Préfixe | 57 | 29 | 88 |
| Nombre | 58 | 9 | 90 |
| Vu pour la première fois | 189 | **251** | 282 |
| Vu pour la dernière fois | 188 | **251** | 282 |
| Exemple d’indicatif | 145 | 58 | 177 |
| Résoudre | 74 | 70 | 106 |

The two timestamp columns were **cell-driven**, not header-driven: 564px of the 830px budget for two of six columns, leaving 266px for four columns whose own cells need 166px of ink plus 124px of padding. **Lever 1 alone could not fit, arithmetically** — that is why the plan's cheapest lever was not the one applied first.

- **Lever 2 applied** — the Flights stacked-cell precedent (`references/data-density.md`), scoped to a new `data-table--registry` modifier. Result: EN 830 (fits), FR 900.
- **Lever 1 then applied** — stacking left the two French headers as the widest thing in their own columns (189px each). `"Vu pour la première fois"` → `"Première fois"`, `"Vu pour la dernière fois"` → `"Dernière fois"` (189 → ~104 ink). Result: FR 830.
- **Lever 3 not applied** — the existing card fallback keeps its own breakpoint; no 1100px rule was introduced, and a check asserts `"1100px"` appears nowhere in the stylesheet.
- **The English sources are deliberately unchanged.** English measured 830/830 after lever 2 alone, so there was nothing to reword there.

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 3 - Blocking] The compact `empty_state()`'s first shape broke a pinned decision from another plan**

- **Found during:** Task 1
- **Issue:** The compact heading/body initially reused `.widget-verdict` / `.widget-detail` — the exact treatments X8's verdict and detail slots wear, which read as the obviously-right reuse. `companion/test_status_pages.py` failed immediately: the Resolution-rate tile is pinned by D-03/A-21 to carry **no** `widget-verdict` anywhere, and that tile's own empty branch is a compact empty state. Borrowing a semantically-named class had quietly made an empty tile claim a judgement the page cannot make.
- **Fix:** `.empty-state__heading` and `.empty-state__body` — until now bare markup hooks with no CSS rule at all — gained two scoped rules under `.empty-state--compact`, so the variant reaches the same 16px-sans-semibold / 14px-muted treatment through its own class names. The check that caught it is untouched and still passes.
- **Files modified:** `companion/layout.py`, `companion/static/style.css`
- **Commit:** `5789877`

**2. [Rule 1 - Bug] Two test helpers sliced a `.stat-tile` "up to the next `</div>`"**

- **Found during:** Task 1
- **Issue:** `_health_page_device_pipeline_tiles_have_no_duplicated_label` and `_tile_slice_by_caption` both located a tile with `rindex('<div class="stat-tile ')` and ended it at the **first** following `</div>`. That was only ever the whole tile because no tile held a nested `<div>`. X8's detail slot is one — so every negative assertion of the form "X is not in this tile" would have silently started reading a prefix of the tile and weakening itself.
- **Fix:** a module-level `_stat_tile_slices()` doing a real balanced `<div>`/`</div>` scan; both helpers delegate to it.
- **Files modified:** `companion/test_status_pages.py`
- **Commit:** `5789877`

### Scope decisions recorded rather than acted on

**3. Health's page-header clock `title` still carries a raw ISO instant, and I left it.** D-05/CFG-28's own wording is "every `title` tooltip carries a local full timestamp; raw ISO survives only behind a copy control", and this `title` is a raw ISO. It is not an oversight and not mine: 19-09-PLAN.md (D-02/A-20) put it there deliberately, and `test_status_pages.py` pins it by name (`"expected the clock span's title to carry the full ISO instant"`). My plan's C5 clause is about the monospace family, which is fixed. Converting it would mean editing a deliberate pin from a plan I do not own, to a requirement another plan has already ticked. **Flagged for 22-16, not changed.**

**4. The Corroboration rows stay at `.text-body` (16px) inside a 14px detail slot.** X8's detail contract is "70% muted", which they now inherit from `.widget-detail`; the size is pre-existing and no plan asked for it to change, so I did not make an unrequested size change. Noted because a reader comparing the four tiles will see it.

## `<read_first>` statements that did not match the codebase

Recorded rather than silently worked around, in the same spirit as the acceptance-criteria discipline:

1. **"`companion/static/style.css`: `.empty-state` and its two child rules"** — `.empty-state__heading` and `.empty-state__body` had **no CSS rules at all**. They were bare BEM markup hooks whose entire treatment came from the co-classed `.text-*` tier. This plan gives them their first two rules (both scoped to the compact variant).
2. **Every line number in `<interfaces>` had drifted**, as that block itself warned (`_device_section` was at :1901, not :1695; `_corroboration_section` at :2494, not :2140; `empty_state()` at :2167, not :1952). Re-derived by name, as instructed.

## Exceptions added or removed

**None added. None removed.** No test exception, allowance or tolerance was introduced. Four checks were **retargeted in place**, each strictly narrower than what it replaced:

| Check | File | Why its premise changed | Why the retarget is narrower |
|---|---|---|---|
| `_health_page_device_pipeline_tiles_have_no_duplicated_label` | `test_status_pages.py` (in `files_modified`) | its "exactly one `stat-tile__value`" was a PROXY for "a real timestamp in the body" — and that class is the Emphasis role, i.e. half of the double bold verdict X8 removes | the proxy is replaced by the thing it stood in for, asserted directly: exactly one Emphasis element, exactly one detail slot, the mono timestamp **inside that slot**, and **zero** `stat-tile__value` so the old shape cannot return. Plus the balanced slice |
| `_health_tile_clock_text` + its caller (the nightly-regression check) | `test_status_pages.py` (in `files_modified`) | the Frame tile's clock moved into the detail slot and dropped `time-value--primary` | the extractor reads the new shape, and the caller now **also** asserts the strip keeps the modifier and Health carries zero of it — a new assertion, not a relaxed one |
| the registry card/table parity check | `test_status_pages.py` (in `files_modified`) | byte-identity between `<tr>` and `.data-card` markup, which stacking the desktop cell deliberately ends | byte-identity was only ever a proxy for "the two cannot disagree about the value". That is now asserted on **both** sides — the card carries `concise_timestamp_html()`'s exact output exactly once, the table carries the exact `local_clock_text()` + `relative_age_text()` outputs that same function composes. The old count could not tell a disagreeing pair from the same wrong value twice |
| `_corroboration_copy_agrees_with_health_page` | **`test_view_pages.py` — NOT in this plan's `files_modified`** | it required the two pages' corroboration STATUS to agree key-by-key for all three keys; Health's "None" is now `"off"` while History's stays `"ok"`, which 22-UI-SPEC.md §5 contract 4 mandates ("Health's own table is unaffected") | "None" is removed from the equality loop and **each page is pinned to its own exact value by name**, which fails on a drift on *either* side where equality would have passed if both drifted together. The "never a failure" invariant is kept for both, and a new assertion was added that Health's two labels differ (colour is never the only signal) |

The `test_view_pages.py` edit is the one file outside `files_modified`. It is also not in `<files_owned>`'s exclusion list, this plan is its wave's only agent, and D-09's regression floor cannot hold otherwise — the same basis 22-11 recorded for its own four.

## Requirements ticked

| ID | Action | Reasoning |
|---|---|---|
| **CFG-29** | **Ticked complete** | `grep -l "CFG-29" *-PLAN.md` in the phase directory returns **only 22-08**, and no other plan's `requirements:` field names it — so the traceability row, not the frontmatter, is what tracks its remaining clauses, and that row said "health_page.py's plurals remain (22-12)". B16's own enumeration was then checked item by item: flash banners and `<title>`s (22-08, pinned by `test_companion_app.py`'s round-trip checks), `aria-label="Primary navigation"` and the Light/Dark segments (pinned in the same file), the CSS `content: "Current"` → `data-*` conversion (22-10's T10), the harness widening to `app.py` + attributes + JS fallbacks (22-08, 24 checks), the battery caption stating the real count rather than `BATTERY_TREND_LIMIT` (`_battery_trend_caption()`, threaded through `render()`), and the **three** plurals B16 names by name — "1 manual resolution" (22-11), "%d upcoming flight(s)" (22-10) and "over the last %d days, %d events" (this plan). Every clause is landed. |
| **CFG-30** | **Traceability row updated only, left unchecked** | Served by nine plans. This plan landed X8 in full, B12 and B11's Health third (which closes B11 across all three filtered pages). B3, B10, B13 and X3 remain with 22-13/22-14. |
| **CFG-31** | **Traceability row updated only, left unchecked** | This plan landed C1's compact `empty_state()` variant and C5's Health adoption. T1–T9, T11, T13–T16 and the `sketch-findings-skypane` update are 22-15/22-16's. |

## Harness pins — old and new

| Harness | Before | After | Why |
|---|---|---|---|
| `companion/test_status_pages.py` | 252 | **258** | +5 (Task 1: the four-slot anatomy over every tile seeded and fresh, the neutral-dot-with-distinct-label check in both languages, the byte-identical default `empty_state()` proven against a real caller, the compact-in-tile / default-in-card split, the singular plural in both languages) and +1 (Task 2: the two levers the measurement selected, and the absence of the third). Re-derived by **running** the harness at each step (256/257, then 257/258). Three checks retargeted in place with no count change. |
| `companion/test_browser_ux.py` | 11 | **14** | +1 (Task 2: `scrollWidth === clientWidth` at 1280px in both languages, Resolve inside the wrap, zero clipped headers) and +2 (Task 3: Health's count/Clear tops and the `.time-value` clock class at 390px; the no-JS floor for Health). Re-derived by **running** the harness (12/12, then 14/14). |
| `companion/test_view_pages.py` | 143 | **143** | One check retargeted in place; no count change. |
| `companion/test_config_page.py` | 232 | **232** | Untouched. |
| `companion/test_i18n.py` | 24 | **24** | Untouched; the two changed French values sit on existing English keys, and the one new key has its own entry. |
| `companion/test_companion_app.py` | 261 | **261** | Untouched — **259/261**, the two documented WR-11 read-only failures and nothing else. No `companion/static/*.js` file was edited by this plan, so the ES5-safety backtick guard was never at risk. |
| `companion/test_contrast_check.py` | 41 | **41** | Untouched. `.widget-detail`'s 70% muted strength is the file's single existing muted value, already shipped and already pinned; no new colour pair was introduced. |

## Regression floor

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` reports the **same five failing check NAMES** as the pre-plan baseline, not merely the same number of failing files:

1. `add_entry()` returns ADD_FAILED … read-only (WR-11) — `server/test_manual_resolutions.py`
2. `delete_entry()` returns False … read-only (WR-11) — `server/test_manual_resolutions.py`
3. `POST /airlines/resolve` … `manual_save_failed` … read-only (WR-11) — `companion/test_companion_app.py`
4. `POST /airlines/manual-resolutions/{prefix}/delete` … `manual_delete_failed` (WR-11) — `companion/test_companion_app.py`
5. `anomaly_active()` … expected False for a non-existent state_dir — `companion/test_status_pages.py`

All five are the documented root-sandbox artefacts (uid 0 cannot trip a read-only directory). Per-harness pass counts: manual-resolutions 21/23, companion-app 259/261, status-pages 257/258 — the counts, not just the file list, match the baseline. TOTAL coverage **93%** (`fail_under = 83`).

## Notes for plan 22-16 (the design-system sweep)

1. **`.dot--off`'s three consumers, for §4's X2/X8/T13 row.** As of this plan, two of the three are landed and one is pending:
   - the **frame's held state** — plan 22-04 (`layout._FRAME_STATE_DOT_CLASSES[STATE_HELD]`, plus `_FRAME_STATE_TO_DEVICE_STATE`'s `"off"`);
   - **Health's "Only one saw it"** — this plan (`health_page._CORROBORATION_ROWS` / `corroboration_status()`, rendered via `layout.status_dot("off", …)`);
   - **T13's paused/reconnecting pill** — plan 22-15, not yet landed.

   There is a **fourth** consumer §4 should probably name, because it predates all three and shares the same rule: `health_page._pipeline_section()`'s genuinely-never-ran branch (22-03, B2) hand-builds `<span class="dot dot--off">`. The shared rule is unchanged — *a neutral, everyday state that is not a problem* — and it is exactly why none of them may use `.dot--warn`. Still **four dot rules total**, still **no new colour**.

2. **`layout._STATUS_DOT_CLASSES` is a four-entry map now, not three.** `status_dot("off", label)` is a supported call. The `_DEFAULT_STATUS_DOT_CLASS` warn fallback for a genuinely unrecognised state is unchanged, and `test_companion_app.py`'s `"not-a-real-state"` check still exercises it. `card_status_class()`'s and `_STAT_TILE_BORDER_CLASSES`' own whitelists are deliberately **not** widened — an "off" tile still falls through to the neutral `stat-tile--accent` border, which is what 22-03 relied on.

3. **`empty_state()` has a compact variant, and `.empty-state__heading` / `.empty-state__body` finally have CSS rules.** Both classes had been markup hooks with zero rules since they were introduced; the two new rules are scoped to `.empty-state--compact` so the full-card form is untouched. If §1's Typography table lists the compact row (it does — "16px sans semibold heading + 14px `.text-label` body"), it is now accurate, with one correction worth making: the body is `.text-label` **composed with `.section-caption`**, because `.text-label` declares no colour of its own.

4. **The Emphasis slot inside a `.stat-tile` has two legitimate class names, by design.** `.widget-verdict` for a state word (Device, Pipeline, Corroboration) and `.stat-tile__value` for a figure (Resolution rate, which D-03/A-21 forbids from making a judgement). A sweep that "converges" these two would reverse D-03/A-21. The invariant that matters and is asserted is **exactly one Emphasis element per tile**, not one class name.

5. **`.stat-tile__value` now has exactly one consumer** (the Resolution-rate figure), and `.stat-tile__value .mono` — the reach-through rule it shares with `.battery-readout .mono` — has **none**: no `.mono` descendant survives inside a `.stat-tile__value` anywhere. The rule is still live and still needed for its `.battery-readout` half, and two checks pin the shared selector by literal, so I left it alone. If 22-16 or a T16 pass tidies dead selectors, this is a genuine half-dead one, and the two pins (`_..._css_dom_contract` and the `.mono` reach-through guard) name it explicitly.

6. **A second table now carries the stacked-cell exception.** `references/data-density.md` currently describes it as the Flights table's own local fix and warns against generalising it. That warning should stay verbatim — but the doc should record that the registry table is the **second** table measured into it, with its own numbers (830px wrap; 886 EN / 1026 FR before), so the exception reads as "applied twice, by measurement, both times" rather than as a rule quietly drifting wider.

7. **Two French catalogue values changed and they are shared.** `"First seen"` and `"Last seen"` are read by `health_page._REGISTRY_HEADERS` **and** `airlines_page.RESOLVE_CONTEXT_LABELS` (the resolve dialog's `<dt>` labels) — one entry, several readers, which is `i18n_fr/health.py`'s own stated contract. The shorter pair renders on both surfaces. If any doc enumerates the dialog's French labels, they are now "Première fois" / "Dernière fois".

8. **A D-05/CFG-28 residue on Health, deliberately left standing.** See Deviation 3: the page header's clock `title` is a raw ISO instant, put there on purpose by 19-09 and pinned by name. CFG-28 is ticked complete; either the requirement's "raw ISO only behind a copy control" clause has a documented exception here, or 19-09's pin needs revisiting. That is a decision for the sweep, not for this plan.

## Notes for plan 22-15 (CSS/JS defects)

- **T6 was not touched.** Nothing in this plan changed any `border` declaration, and the selection-shift is not visible on the surfaces I edited. Left alone, as instructed.
- **`style.css` edits are scoped to rules this plan owns:** `.empty-state--compact` (+ its two child rules) is new; `table.data-table--registry` (two rules) is new; `.filter-bar__count { margin-left: auto }` was deleted. Nothing else in the file was reformatted, reordered or tidied. The `@supports selector(:has(*))` block is still pinned at exactly one and was not moved.
- **`.filter-bar [data-filter-clear]` was not forked.** Health's Clear is still the `<a href="#…">` D-16 requires, still converged on that one rule, and the group wrapper adds no per-page variant.
- **The registry table keeps `.data-table`'s `min-width: max-content` no-crop floor.** Releasing it (what `.data-table--prose` does for the stats table) was the other obvious way to make the table fit, and it was **not** taken — a check asserts no bare `.data-table--registry { … }` rule exists. If a later plan is tempted, note that the floor is what stops the prefix and callsign columns cropping.

## Note for plans 22-13 / 22-14

`companion/pages/health_page.py`'s tile bodies are now all built through `_tile_body()`. If either plan adds or edits a Health tile, use it — the four-slot anatomy is asserted over **every** `.stat-tile` on the page, seeded and empty, so a hand-built tile body will fail rather than drift.

## Self-Check: PASSED

- `companion/pages/health_page.py` FOUND, `companion/layout.py` FOUND, `companion/static/style.css` FOUND, `companion/i18n_fr/health.py` FOUND, `companion/test_status_pages.py` FOUND, `companion/test_browser_ux.py` FOUND, `companion/test_view_pages.py` FOUND
- commits `5789877` FOUND, `9b64370` FOUND, `f80fcbb` FOUND
