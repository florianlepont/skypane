---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 16
subsystem: design-system
tags: [design-system, documentation, skill, phase-closure, accessibility, i18n-time]
requires: [22-01, 22-02, 22-03, 22-04, 22-05, 22-06, 22-07, 22-08, 22-09, 22-10, 22-11, 22-12, 22-13, 22-14, 22-15]
provides:
  - "sketch-findings-skypane updated in step with everything Phase 22 shipped — all twenty 22-UI-SPEC.md §4 rows applied across seven skill files"
  - "two recorded reversals marked SUPERSEDED in place with their reasoning: the icon-only pattern for .row-toggle (X5) and .dirty-bar's no-z-index paragraph (T7)"
  - "three stale load-bearing numbers corrected at source: the :has() block count (one), the floating-overlay shadow exception count (four), the compact-chip usage sentence"
  - "CFG-28's last unmet clause closed — Health's page-header clock title is a Paris-local full timestamp, 19-09's pin retargeted in place"
  - "style.css's accent arithmetic corrected at the false premise 22-15 found"
  - "a line-by-line coverage record for every one of 22-AUDIT.md's 49 findings"
affects: [phase-23]
tech-stack:
  added: []
  patterns:
    - "supersede in place with a stated reason; never delete a recorded verdict"
    - "verify a number against the live code before writing it into a reference file"
key-files:
  created:
    - .planning/phases/22-companion-audit-round-4-fix-the-blocking-display-save-bar-co/22-16-SUMMARY.md
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/visual-direction-typography.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/mobile-navigation.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
    - .claude/skills/sketch-findings-skypane/references/data-density.md
    - .claude/skills/sketch-findings-skypane/references/accessibility-contrast.md
    - companion/pages/health_page.py
    - companion/test_status_pages.py
    - companion/static/style.css
    - .planning/REQUIREMENTS.md
decisions:
  - "Two §4 rows were WRONG against the shipped code and were corrected rather than applied mechanically: T6 covers three selectable surfaces plus both dashed markers (not two) and needs .theme-chip's box-shadow: inherit overlay; .dot--off has four consumers, not three"
  - "X6's prescribed legend copy (Background · Ink) mis-names the swatches; the shipped Departures · Arrivals is recorded with the reason the code contradicts the spec"
  - "The 20px .airline-card__chip interactive control gets a NAMED, justified register exception with an honest statement that 20px is below the AA 24px floor as a bounding box, and a stated disposition — not a silent pass"
  - "CFG-28 and the style.css header-comment correction were executed despite falling outside the plan's own files_owned, on the user's explicit instruction; both are documented as deviations"
metrics:
  duration: "~35 min"
  completed: 2026-09-13
---

# Phase 22 Plan 16: The `sketch-findings-skypane` Design-System Sweep and Phase Closure Summary

The design system now describes the app that exists: twenty §4 rows applied across seven skill files, two recorded rejections reversed with their reasoning preserved in place, three stale load-bearing numbers corrected at source, CFG-28's last raw-ISO tooltip converted, and a line-by-line coverage record for all 49 audit findings.

## What Shipped

### Task 1 — the type ladder and the density register (`3ea4354`)

`SKILL.md`, `references/visual-direction-typography.md`, `references/control-density.md`.

Eight SKILL.md rows, two typography rows, eight control-density rows. The three that needed the most care:

- **The `.row-toggle` reversal (X5).** The Phase 21 entry is kept **verbatim, quoted inside the SUPERSEDED entry**, so a later reader can still see what was rejected and on what ground — then the ground is dismantled explicitly: the rejection rested on exactly one fact ("unlike `.copy-btn`, the row-toggle carries visible text"), and X5 removed that text. `.row-toggle` moves from the **traded-away** category to the **relocated** one (22×22 visual box, `::before` inset -11px, real 44×44 hit area — every value `.copy-btn`'s own). Recorded alongside: it had **no CSS rule at all** before this phase, so a new rule block was created rather than an existing one edited — which is precisely why the Phase 21 register entry described a geometry no selector actually declared. The checker's note is folded in: the accessible name must **advertise the picture reachable inside** ("Show flight details and picture"), because an icon-only control whose name understates its contents is the same defect class the conversion was meant to fix, moved from the visual layer to the accessibility layer.
- **`.calendar-disconnect-btn` (X7).** **Both** new call sites named — Airlines' per-card Replace (22-11) and Flights' picture control (22-09) — three in total with Config's Disconnect. Plus the two things a future reader will otherwise undo: the base selector is now element-qualified (`button.calendar-disconnect-btn`, `(0,1,1)` against `button[type="submit"]`'s `(0,1,1)`, decided by source order) and simplifying it back to the bare class silently restores T2; and the Airlines call site's `.airline-card .calendar-disconnect-btn` declares **placement only**, which is the discipline that kept the base rule singular.
- **The floating-overlay enumeration.** Corrected from two to **four** in one edit, with the reason stated: it was already stale by one before this phase (`.mobile-nav` has carried an unconditional resting shadow since 06.6.1 and `references/mobile-navigation.md` has said so the whole time), so a fourth was not appended to a wrong total. Corrected in `SKILL.md` and `visual-direction-typography.md` in the same pass so the two cannot disagree.

### Task 2 — navigation, settings patterns, and the number that misled the spec (`073c87d`)

`references/mobile-navigation.md`, `references/settings-page-patterns.md`, `references/data-density.md`.

- **The bottom tab bar as a THIRD rendering**, all three still fed by the one `_nav_links()` iteration, with the measured geometry, the native-`<details>` More sheet, the out-of-flow **inverted** chevron and its reason, the dropdown's reduction to a preferences panel, the renamed toggle label, the single measured `max-height` (320px, content 165px FR) and the measured remaining push (189px, from ~420px).
- **The two rejected nav verdicts are UNCHANGED and UNREVERSED**, verified by diff, with a new note recording *why they did not need touching*: bottom tabs were chosen specifically so neither had to be reopened. A second note distinguishes the More sheet's upward `position: absolute` from the rejected overlay — that verdict is about the **primary** nav's push-versus-overlay behaviour on a component that must be able to push content; the sheet is a two-item secondary panel anchored to an already-fixed bar that pushes nothing and never could.
- **The `:has()` count corrected at source, and verified before writing.** `grep -c '@supports selector(:has(*)) {' companion/static/style.css` → **1**, block at `style.css:2341`, asserted by **two** independent checks in `companion/test_config_page.py` (each `count(...) != 1`, each additionally pinning its own rules inside that block). The correction records *why* it matters: this exact stale line is what an earlier draft of this phase's own UI spec copied instead of checking the code, and it produced a checker BLOCK.
- **T7's two entries superseded in place** through the paragraph's own escape clause, with the stated reason (the save bar is the active task, the tab bar is ambient chrome, the blocked save was the P0), the new sub-960px bottom offset and both measured content clearances. The "What to Avoid" twin is struck through rather than removed, keeping the part of its rule that still holds.
- **T4's sticky-header entry SUPERSEDED** with the honest reason — the wrap has no height, so it could **never** engage; the declaration was inert from the day it shipped — and its never-live-validated `--color-canvas` note recorded as **moot, not deferred**.
- The day-separator half-sentence, and Health's registry table as the stacked-cell exception's **second measured consumer**, with the do-not-generalise warning left verbatim.

### Task 3 — the two closing items beyond §4 (`f0694c7`)

- **CFG-28.** Health's page-header clock rendered `title="<raw UTC ISO>"`, failing two of D-05/CFG-28's clauses (a `title` is a tooltip, and this one sits behind no copy control). Converted via this module's own `_full_local_timestamp_text()` — a **fourth caller of an existing helper**, not a second date path, degrading identically on an unparseable value. **19-09's pin was retargeted in place**, not deleted: the same named check now asserts the title equals the helper's output and that the raw ISO does not survive verbatim. `data-loaded-at` still carries the machine-readable instant `freshness.js` actually reads.
- **`style.css`'s header comment (C2's row).** The accent arithmetic claimed 06.6.4.1-04 had already removed the Disconnect accent fill "as a specificity BUG fix". That was false when written and stayed false for eleven more plans. Corrected in place: the **count is unchanged** (the accidental fill was never a deliberate list entry), but both genuine losses land in this phase — 22-04's Frame-strip repaint and 22-15's T2 fix. Both harness-pinned phrases are untouched.

### Task 4 — the closing sweep (this commit)

One dated `SKILL.md` phase entry, the `Current as of` line moved to Phase 22, and — closing three notes 22-15 addressed to this sweep that §4 does not route anywhere — T15's and T3's accessibility contracts in `references/accessibility-contrast.md`, and T14's deferred disable-on-submit rule in `references/control-density.md`'s "What to Avoid".

## The §4 rows found wrong against the code

Applied as corrected, never mechanically. Each is recorded in the skill with the discrepancy stated.

| Row | What §4 says | What the code says | What I wrote |
|---|---|---|---|
| **T6** | the border conversion covers the selected-card treatment | **three** selectable surfaces — `.theme-chip`, `.runway-card`, `input:checked + .frame-colours__row` — **plus both dashed saved-state markers**, and `.theme-chip` needs a `::before` overlay with `box-shadow: inherit` because an inset ring paints beneath a full-bleed child image | all three surfaces, both markers, both moved `:hover` restore rules, and the overlay recorded as **the general rule for any future selectable card with an edge-to-edge child** |
| **X6** | legend copy `Background · Ink` / `Fond · Encre` | the two swatches are the **departing and arriving inks**; shipped copy is `Departures · Arrivals` / `Départs · Arrivées` | the shipped copy with the reason, so the skill does not preserve a string the code deliberately contradicts |
| **X7** | `.calendar-disconnect-btn` gains **a** second consumer | **two** new call sites (22-11's Replace, 22-09's picture control) | both named, plus the element qualifier and the placement-only discipline |
| **X2/X8/T13** | `.dot--off` gains **three** consumers | **four** — the fourth (`_pipeline_section()`'s never-ran branch, 22-03) predates all three and shares the identical rule; `layout._STATUS_DOT_CLASSES` is a **four-entry map** | all four, the shared rule, and an explicit note that §4 said three |
| **Gate** | the surviving `:has()` block is at `style.css:2081`, asserted by `test_config_page.py:3760` | block at `style.css:2341`; the assertions are at `test_config_page.py:4002` and `:4232` (T15 added the second) | the **count** as the durable fact, the block named by identity ("the live-selection-state one"), the line number flagged as drift-prone, and an instruction to re-grep rather than quote |
| **X9 (Cards)** | the count goes from two to four | it was already stale by one *before* this phase | the count and the list corrected in one edit, in two files, with the pre-existing staleness stated |

**One gap §4 has no row for at all**, flagged by 22-11 rather than deviated on silently: the new Airlines filter control is a **20px** `<button>` wearing `.airline-card__chip`, below the 30/36px register. Recorded as a **named exception with an honest measurement** — 20px is below the WCAG 2.5.8 **AA** 24px floor as a bounding box, not only the AAA one; 2.5.8's spacing exception may cover it but was **not measured** and must not be assumed — plus a stated disposition (relocate the hit area with a `::before`, the pattern this file already owns, before adding a second interactive consumer) and a "What to Avoid" entry.

## The two reversals, and the three corrected numbers

**Reversals (both SUPERSEDED in place with their reasoning, neither deleted):**

1. **The icon-only pattern for `.row-toggle`** — reversed because X5 dissolved the rejection's own stated ground. A "What to Avoid" entry now blocks a re-reversal that cites the old argument: it requires a new one.
2. **`.dirty-bar`'s "No `z-index`, and why"** — reversed by its own escape clause, used exactly as written, with the stated reason recorded. Its "What to Avoid" twin is struck through, not removed, keeping the surviving half of its rule.

**Verdicts deliberately NOT reversed:** the full-screen overlay and the backdrop drawer. Confirmed unchanged by diff (`git diff` shows neither line among the removals; the one apparent match is a context line).

**Three stale numbers corrected:** the `:has()` block count (**one**, verified live), the floating-overlay shadow exception count (**four**, corrected in both files that carried it), the compact-chip usage sentence (no longer exhaustive — `.theme-chip--compact` is now Display's only chip density).

## The audit ledger — all 49 findings

### B1–B18

| # | Closed by | Verified by |
|---|---|---|
| B1 | 22-01 | `test_config_page.py` delegation/fallback-gate checks + `test_browser_ux.py` save round-trip with scripts on **and** blocked |
| B2 | 22-03 (Health), 22-07 (Home) | `test_status_pages.py` neutral-state checks; Home's verdict-free `pipeline_detail_html` |
| B3 | 22-03 | `resolution_stats()` counting every row, empty section omitted, 30-day window named |
| B4 | 22-06 | `test_status_pages.py` — no raw ISO in the readout slice; the daily buckets group by Paris days |
| B5 | 22-11 | whole rendered Airlines page carries zero ISO-8601 strings; `panel-lookup.js` pinned free of every date API |
| B6 | 22-10 | crop re-measured; `test_config_page.py` |
| B7 | 22-10 | explicit `:hover` rule on the segmented control (the `:not()`-scoped half had already shipped in 260902-qkm; only the active-segment restore was new) |
| B8 | 22-10 | "Send a test" inside the card via `form=` |
| B9 | 22-10 | `test_browser_ux.py` — cards measured 96.7–98.7px at 390px, closed on `.runway-card` (`flex: 1 1 0; min-width: 0`), **not** `.runway-row`, which is shared with the quiet-hours preset row |
| B10 | 22-14 | measured 207 × 47px sidebar / 28px at 390px, one client rect per segment, FR |
| B11 | 22-09 (Flights), 22-11 (Airlines), 22-12 (Health) | `test_browser_ux.py` equal bounding-box tops on all three |
| B12 | 22-12 | headless measurement, FR at 1280px; registry table's stacked cells |
| B13 | 22-04 | one `.frame-strip__cell`, `align-items: stretch`, one three-row internal grid |
| B14 | 22-10 | normalised 24h value beside the native time fields |
| B15 | 22-10 | "Connect calendar" content-width, left-aligned |
| B16 | 22-08 | `test_i18n.py` 24/24, widened to `app.py`, attribute literals and JS fallbacks |
| B17 | 22-10 | Device fields share one left edge; number input sized for its content |
| B18 | 22-07 | one-line recent-flight time; `display_airline_name()` shared with Flights |

### X1–X9

| # | Closed by | Verified by |
|---|---|---|
| X1 | 22-05 | one control per setting; `_handle_post_theme_only_save_never_flips_display_or_quiet_hours_off()` across four seeded starting states |
| X2 | 22-02 (+ consumers 22-04/22-05/22-07) | the nightly-regression check pinned as one named scenario; grace window |
| X3 | 22-13 | measured 278 × 44 / 296 × 44, shared radius; error state gated through `WCAG_AA_UI_COMPONENT` |
| X4 | 22-07 | Home ordering and naming |
| X5 | 22-09 | `test_browser_ux.py` icon-only toggle, ≥44×44 synthesized hit area, name swap |
| X6 | 22-10 | density half only — the page-height target is **not met and cannot be by density alone**; the remaining half is D5/Phase 23 |
| X7 | 22-11 | normal-case toggle, per-card control, two cards per row at 390px |
| X8 | 22-12 | one tile anatomy over every `.stat-tile`; "Only one saw it" neutral with distinct visible text |
| X9 | 22-14 | bottom tab bar (D-10), 78 × 56px cells, push cut to a measured 189px, `<details>` works with scripts blocked |

### C1–C6

| # | Closed by | Verified by |
|---|---|---|
| C1 | 22-10 (legend), 22-12 (compact `empty_state()`) | the override on the class, bare `legend` still in the shared serif selector, both pinned |
| C2 | 22-04 (rule), **22-16** (the header comment's false premise) | `test_status_pages.py`'s header-comment check, both pinned phrases intact |
| C3 | 22-10 | explicit selected-and-hovered rule |
| C4 | 22-13 + 22-11 applied it; **22-16** recorded it | the lightbox action row asserts the **absence** of `height`/`min-height`/`border-radius` |
| C5 | 22-04 (role), 22-06/22-09/22-12 (adoption) | `.time-value` declared once with `tabular-nums`, `--primary` modifier |
| C6 | 22-04 | the Phase 21 heading-size override asserted gone |

### T1–T16

| # | Closed by | Verified by |
|---|---|---|
| T1 | 22-01 | the leave-guard re-arms after Cancel |
| T2 | 22-15 | `button.calendar-disconnect-btn` at `(0,1,1)`, source order decides |
| T3 | 22-15 | explicit `summary::before`; reduced-motion block count unchanged at two |
| T4 | 22-15 | the false sticky claim removed outright |
| T5 | 22-14 | `transitionend` filtered on target **and** `max-height`; close decided by computed style, never a timer |
| T6 | 22-15 | measured 98.67 vs 96.66px at 390px; 22-10's temporary border allowance **deleted** |
| T7 | 22-14 | measured clearances; one `z-index: 30` across both breakpoints |
| T8 | 22-01 | Cancel restores the live preview |
| T9 | 22-04 | the hover block declares zero `border-color: transparent` and both logical properties, `:not(.frame-strip)`-scoped |
| T10 | 22-10 (shipped), 22-14 (made to render) | `attr(data-current-label)`; the badge had **not** been rendering since 22-10 because of a stray comment terminator — it is done **now** |
| T11 | 22-14 | one `max-height`, 320px against a measured 165px |
| T12 | 22-10 | the global `label` margin reset inside the segmented control |
| T13 | 22-15 | `test_browser_ux.py` — backed-off retry behind a neutral `.dot--off` badge, recovery clears it |
| T14 | 22-15 | `test_browser_ux.py` — a second Save click produces no second POST; named submit buttons still work |
| T15 | 22-15 | focus ring using the global floor's own values inside the one feature-query block; `summary` added to that floor |
| T16 | — | **OPTIONAL by D-08; none taken.** Not a gap |

## Findings recorded for gap closure (not fixed here — this plan owns no code path they touch)

1. **X6's page-height target is not met** and cannot be by chip density alone; the remaining half is D5, Phase 23. (22-10)
2. **B17 vs Phase 18's placeholder width.** B17 narrows the wake-interval field to 96px, so the locked "Uses server default" placeholder truncates again whenever no interval is stored. B17 is the later, narrower decision and wins, but the trade is real; if the empty state should be readable, the information belongs in the section caption — a copy change no plan owns. (22-10)
3. **The day separator's absolute form is abbreviated** (`26 Aug` / `26 août`), not the spec's `%-d %B`. A full-month label belongs in `layout.py` as a second exposed table, never a second date path in `history_page.py`. (22-09)
4. **The 20px `.airline-card__chip` interactive control** — recorded as a named register exception with a stated disposition; the hit-area relocation itself is not taken here. (22-11)
5. **`.page-header__screen` is doing two jobs** (a label-voice caption on Device, a wrapper `<div>` on Airlines). The descendant-selector fix holds; the underlying class-doing-two-jobs is untouched. (22-11)
6. **`.stat-tile__value .mono` is a genuinely half-dead reach-through rule** — no `.mono` descendant survives inside a `.stat-tile__value` anywhere, but its `.battery-readout` half is live and two checks pin the shared selector by literal. A T16-style dead-selector pass would take it. (22-12)
7. **22-13's own plan frontmatter carried an inaccurate `must_haves` claim** ("the app has none today" for a `.login-card` stylesheet rule — `.login-shell`/`.login-card` rules have existed since 06.6.2-07). Recorded; the plan file itself is not rewritten after the fact.
8. **`STATE.md` is structurally degraded** — two frontmatter blocks and two `## Current Position` sections, both stale — so `gsd-sdk query state.advance-plan` cannot parse it and errored. Pre-existing and long-documented in the file's own history; updated by hand per that precedent. Worth a dedicated repair.

## The phase-wide invariants, confirmed explicitly

| Invariant | Evidence |
|---|---|
| **No-JS floor** | `test_browser_ux.py`, scripts blocked: Health renders in full with all four tiles and its filter bar; **both settings pages render and stay usable and a Display save round-trips**; the show-password toggle reveals itself at load rather than sitting dead |
| **No new runtime dependency** | `grep -c playwright server/requirements.txt` → **0**. The file is two lines: `Pillow==12.3.0`, `requests==2.34.2` |
| **No vendored library** | `companion/static/` holds 14 hand-written ES5 scripts, one stylesheet, three PNGs and one markdown note — nothing third-party |
| **CSP unchanged** | `grep -v "^ *#" companion/app.py \| grep -cE "script-src[^;]*(unsafe-inline\|nonce-)"` → **0**; `grep -c "script-src 'self';" companion/app.py` → **1** |
| **Zero new tokens or colour literals** | diffed `style.css` against the phase's own starting commit (`e6f1efd`): zero added `--*:` declarations; every added occurrence of an existing hex is a **measurement citation inside a comment** |

## Regression floor

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` → **exactly the documented sandbox baseline, by NAME and by per-harness count**, unchanged from the pre-plan run:

| Harness | Result | Failing checks |
|---|---|---|
| `server/test_manual_resolutions.py` | 21/23 | `add_entry()` / `delete_entry()` read-only (WR-11) |
| `companion/test_companion_app.py` | 270/272 | the two POST-route read-only cases (WR-11) |
| `companion/test_status_pages.py` | 267/268 | `anomaly_active()` non-existent `state_dir` |
| `companion/test_browser_ux.py` | **22/22** | — |
| `companion/test_config_page.py` | 233/233 | — |
| `companion/test_view_pages.py` | 143/143 | — |
| `companion/test_i18n.py` | 24/24 | — |
| `companion/test_contrast_check.py` | 43/43 | — |

All five failures are the documented root-sandbox artefacts (uid 0 cannot trip a read-only directory); all pass in CI. **Coverage 93%** against a floor of 83. `ruff check .` clean.

**The browser harness RAN, it did not skip.** Evidence: `companion/test_browser_ux.py` invoked directly exits **0** and prints `browser-ux: 22/22 checks pass` with **zero** occurrences of any skip marker in its output, and each line is a real measurement against a live Chromium (`getBoundingClientRect` tops, computed `display`, page heights, a real POST count).

**No `EXPECTED_CHECK_COUNT` was derived by arithmetic.** `test_status_pages.py`'s count is **unchanged at 268** because 19-09's check was **retargeted in place**, not added — re-derived by running the harness and reading its printed total (267/268, the one documented failure).

**Mutation test on the one new assertion.** Reverting `health_page.py`'s render to the raw ISO produced **exactly one** additional failure — the retargeted check, by name — and reverting it back restored 267/268.

## Deviations from Plan

### Deliberate departures, each on explicit user instruction

**1. [Rule 4 → user-authorised] Three code files were edited, which this plan's `<files_owned>` forbids.**
The plan states "No file under `companion/`, `server/` or `scripts/` is this plan's to change." The user's execution instruction overrode that on two specific, named items and assigned both to this plan by name:
- `companion/pages/health_page.py` + `companion/test_status_pages.py` — **CFG-28**, which the requirement's own traceability row had already assigned here ("Assigned to 22-16's closing sweep"), precisely because closing it means deliberately re-targeting another plan's pin.
- `companion/static/style.css`'s **header comment** — C2's row, which 22-15 explicitly left standing as "22-16's to own" after finding its premise false.

The restriction's stated purpose (threat `T-22-62`) is that a last-wave edit must not bypass the wave's own verification. It did not: the full suite was re-run after the change, the retargeted check was mutation-tested, and both harness-pinned phrases in the header comment were verified intact. No code defect *discovered during the sweep* was fixed here — findings 1–8 above are all recorded rather than repaired.

**2. [Rule 2 — missing critical functionality] A seventh skill file was edited.**
`references/accessibility-contrast.md` is not in the plan's `files_modified`, and §4 routes no row to it. But 22-15's notes 3 and 8 address **T3** and **T15** to this sweep directly, and both are accessibility *contracts* that belong nowhere else: `summary` joining the focus-visible floor, the selected-card focus ring inside the one feature-query block, the restored disclosure marker as a **restoration of an already-reserved** accent use (not a new consumer), and the reduced-motion rule that needs no per-rule block. Leaving them unwritten would have left the accessibility reference contradicting shipped code — the exact failure mode D-08 exists to prevent. Same reasoning for 22-15's note 12 (**T14**'s deferred disable-on-submit rule), added to `control-density.md`'s "What to Avoid" because that is where a future guard will be written.

**3. [Rule 1 — doc bug] `REQUIREMENTS.md`'s CFG-25 traceability row said "Planned (22-01..22-16)" beside an already-ticked checkbox.**
It described the phase's span, not the requirement's. `grep -l CFG-25 *-PLAN.md` returns 22-01 alone. Corrected to "Complete (22-01)" with the reason.

### Auto-fixed issues

**None.** No bug, missing functionality or blocker was found in this plan's own work.

### Acceptance criteria that did not evaluate as predicted

**None.** Every criterion in all three tasks returned exactly what the plan stated, including the three explanatory sub-values Task 3's CSP criterion predicts:

| Criterion | Predicted | Actual |
|---|---|---|
| `grep -c playwright server/requirements.txt` | `0` | `0` |
| `grep -v "^ *#" app.py \| grep -cE "script-src[^;]*(unsafe-inline\|nonce-)"` | `0` | `0` |
| `grep -c "script-src 'self';" app.py` | `1` | `1` |
| bare `unsafe-inline` count (stated as context) | `3` | `3` |
| unfiltered scoped form (stated as context) | `1` | `1` |
| `grep -c '@supports selector(:has(*)) {' style.css` | `1` | `1` |
| Task 1's three-grep chain | all non-zero | `14`, `10`, `1` |
| Task 2's four-grep chain | all non-zero | `2`, `10`, `8`, `1` |
| `run-all-tests.sh` | documented failures only, coverage ≥ 83 | 5 documented failures, coverage 93 |

**One self-inflicted trip was avoided rather than hit.** Six earlier plans hit criteria tripped by their own new prose. This plan writes a great deal of prose *about* the exact strings other criteria count — `@supports selector(:has(*)) {`, `unsafe-inline`, `position: sticky`, `SUPERSEDED`. Two guards applied deliberately:
- Every such discussion lives in `.claude/skills/`, which **no** grep-shaped criterion in this phase scopes to. The one criterion that greps a code file for a phrase I also discuss (`@supports selector(:has(*)) {`) scopes to `companion/static/style.css`, which I did not add that string to.
- The `style.css` header-comment edit adds no occurrence of either harness-pinned phrase and removes none — verified by `grep -c` on the header slice before committing (`1` and `1`).
- **No `*/` was written inside any CSS comment.** The structural guard pinning `companion/static/style.css` at zero stray comment terminators passes; that guard exists because 22-10 appended a note after a block comment's closing marker and silently dropped T10's badge in every browser for four plans, and this plan's only CSS edit is a comment expansion — exactly the defect class it guards.

### Exceptions added or removed

**None added, none found standing.** 22-15 deleted 22-10's T6 border allowance as designed, and I re-checked: the suite carries **no temporary allowance at all**. Nothing in this plan required one — the one new assertion is strictly narrower than the one it replaced (it adds a raw-ISO-absence clause on top of a positive match).

## Requirements — the final state of CFG-25..CFG-31

| Req | Final state | Reasoning |
|---|---|---|
| **CFG-25** | **Complete** (unchanged; traceability prose corrected) | `grep -l CFG-25 *-PLAN.md` → 22-01 alone, which landed B1 in full plus D-02's browser harness. Its row said "Planned (22-01..22-16)" beside an `[x]` checkbox; that described the phase's span, not the requirement's, and is now corrected |
| **CFG-26** | **Complete** (unchanged) | 22-02 (the one next-wake truth with its grace window), consumed by 22-04, 22-05 and 22-07 |
| **CFG-27** | **Complete** (unchanged) | 22-05, pinned by a four-starting-combination theme-only-save check that reads the on-disk result |
| **CFG-28** | **RE-TICKED by this plan** | The last unmet clause was Health's page-header clock `title`. It now carries the full Paris-local timestamp via `_full_local_timestamp_text()`; 19-09's pin is retargeted in place and mutation-tested; the raw ISO is asserted not to survive verbatim. Every clause holds: the battery readout and chart (22-06), every tooltip (22-06 + this plan), the resolve dialog (22-11), raw ISO only behind a copy control |
| **CFG-29** | **Complete** (unchanged, not regressed) | `test_i18n.py` 24/24. This plan added **zero** user-facing strings — every edit is a skill file, a code comment, a docstring-adjacent comment or a test message, none of which the scanner's catalogue covers or should |
| **CFG-30** | **Complete** (unchanged, not regressed) | Nine plans, last of them 22-14. No page module was edited here except `health_page.py`'s one `title` value, which changes no visible text |
| **CFG-31** | **TICKED by this plan** | `grep -l CFG-31 *-PLAN.md` returns seven plans and 22-16 is the last. T1–T15 all landed before it; T16 is optional and none was taken. What remained was D-08's own framing — the skill is the authority and must be updated in step — and all twenty §4 rows are now applied across seven skill files, with the three UI-checker notes folded in, every supersession marked in place with a stated reason, nothing deleted (verified by diff), two reversals argued, three stale numbers corrected and two §4 rows corrected against the code |

## Human verification (phase-level UAT)

Pulled from every plan's own deferred `<human-check>` plus `22-VALIDATION.md`'s manual-only table. None of these is machine-checkable, and none blocks this plan.

1. **The pixel-measurement table re-walked at 1280px and 390px, in both themes and both languages**, against the audit's own seeded state directory — the audit's measurements are the acceptance target and only a human eye closes them as a set.
2. **The segmented control's hover legibility after a click reload** (B7/C3) — the defect only appears with the pointer still resting on the segment the reload lands under.
3. **The bottom tab bar on a real iPhone and a real Android handset** — safe-area inset, the upward More sheet, and the 78 × 56px cells under a real thumb. Explicitly out of scope for any plan (22-UI-SPEC.md §6).
4. **The "within about 5 minutes" claim checked against the firmware**, not against the server's own model of it.
5. **One real overnight quiet-hours window**, watching the frame's held state and the nightly false-alarm regression X2 closed.
6. From 22-09: with scripts blocked, every Flights detail row visible and no row showing a pointer cursor; with scripts on, tapping a row anywhere but a control expands it.
7. From 22-07: three equal-height tiles on a 390px phone, a one-line recent-flight time, and matching airline names between Home and Flights.
8. From 22-13: sign in with a wrong password and read the error; block scripts and confirm no dead toggle. *(Both halves are additionally covered by machine checks.)*

## Threat Flags

**None.** This plan introduced no network endpoint, no auth path, no file-access pattern and no schema change. The one code-behaviour change — Health's clock `title` — moves a value from a raw UTC instant to a Paris-local rendering of the same instant in a human-facing tooltip; it exposes strictly less precision than before, and the machine-readable `data-loaded-at` is unchanged.

## Self-Check: PASSED

- `.claude/skills/sketch-findings-skypane/SKILL.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/visual-direction-typography.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/control-density.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/mobile-navigation.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/data-density.md` — FOUND
- `.claude/skills/sketch-findings-skypane/references/accessibility-contrast.md` — FOUND
- `companion/pages/health_page.py` — FOUND
- `companion/test_status_pages.py` — FOUND
- `companion/static/style.css` — FOUND
- Commit `3ea4354` — FOUND
- Commit `073c87d` — FOUND
- Commit `f0694c7` — FOUND
- The closing docs commit is this one; its hash is not self-citable
