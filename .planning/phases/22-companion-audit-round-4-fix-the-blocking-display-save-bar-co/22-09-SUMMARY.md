---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 09
subsystem: companion-ui
tags: [python, css, vanilla-js, accessibility, i18n, playwright, timezone]

requires:
  - phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
    provides: "22-01's browser harness (the Flights scenario this plan retargets), 22-04's .time-value role, 22-06's Paris-local-time discipline"
provides:
  - "an icon-only .row-toggle with a synthesized 44x44 hit area, a translated state-swapping accessible name, and its first CSS rule block"
  - "a delegated whole-row click in flight-rows.js that returns early for any interactive target"
  - "day-separator rows grouped by Europe/Paris calendar day, labelled from the Paris-day formatter's own output"
  - "a one-hop /airlines?resolve={prefix} link from the Flight cell, replacing the two-hop route through Health"
  - "a labelled picture control inside the detail row, on .calendar-disconnect-btn's small-grey-secondary treatment (its second consumer)"
  - "phone cards carrying the airline name and the artwork thumbnail on the shared white-backing/hairline/radius rule"
  - ".filter-bar__meta — the page-agnostic count+Clear group 22-11 and 22-12 must adopt verbatim"
affects: [22-11, 22-12, 22-16]

tech-stack:
  added: []
  patterns:
    - "an icon-only control reuses .copy-btn's 22x22 box + ::before inset:-11px hit-area synthesis verbatim; the harness proves it by comparing the two rule bodies' own literals rather than re-typing sizes"
    - "a class-at-load marker added by the script itself is the only key for any affordance a scripts-blocked page cannot honour (cursor: pointer)"
    - "derive a calendar-day label from layout.month_abbr()/local_clock_text(), never a second date path in a page module"
    - "wrap a pair of controls that must wrap together in one flex group; nowrap on each sibling does not make them one item"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/static/flight-rows.js
    - companion/static/style.css
    - companion/i18n_fr/flights.py
    - companion/test_view_pages.py
    - companion/test_browser_ux.py
    - .planning/REQUIREMENTS.md

key-decisions:
  - "the row toggle's accessible name is widened past the UI-SPEC's base wording to 'Show/Hide flight details and picture', because Task 2 moves the picture control into that row"
  - "the day separator's absolute form is '26 Aug' / '26 août' (layout.month_abbr()), NOT the UI-SPEC §1 copy table's '%-d %B' / '9 September' — the plan forbids a second date path, and the formatter has no full-month table"
  - "an unresolved row whose callsign yields no valid prefix gets NO link at all, rather than keeping the retired Health fallback: a prefix-keyed resolve view cannot act on a row with no prefix"
  - "the picture control drops its aria-label entirely now that it has a visible label (WCAG 2.5.3 label-in-name); VIEW_PANEL_LABEL survives as its title"
  - ".filter-bar__count keeps its margin-left: auto (inert inside the new group) so Airlines and Health stay right-aligned until 22-11/22-12 adopt the wrapper"

requirements-completed: []

duration: ~2h
completed: 2026-09-13
---

# Phase 22 Plan 09: Flights — day separators, one chevron per row, one hop to act Summary

**Replaces fifty 30px "More" text buttons with one icon-only chevron carrying a real 44x44 hit area and a translated state-swapping name, groups the table by Europe/Paris day, links a flight straight to the airline resolve view, moves the panel picture into the detail row as a labelled control, gives phone cards the airline and its artwork, and closes Phase 18's A-18 a second time with a 390px measurement.**

## Performance

- **Duration:** ~2 h
- **Completed:** 2026-09-13
- **Tasks:** 3 (all `type="auto"`, two `tdd="true"`)
- **Files modified:** 7

## Commits

| Task | Commit | Subject |
|---|---|---|
| 1 | `a71cc93` | feat(22-09): one icon-only chevron per flight row, bigger than the text button it replaces |
| 2 | `11dba24` | feat(22-09): the flights table reads as days, and naming an airline takes one click |
| 3 | `cb5951e` | fix(22-09): the filter count and Clear stop breaking onto two lines at 390px |
| — | `cb1220c` | docs(22-09): complete Flights day-separators/icon-toggle/one-hop plan |

## Accomplishments

### Task 1 — the icon-only toggle

- `.row-toggle` renders a 22x22 box with a 14px chevron glyph and a `::before { inset: -11px }` hit area — 22 + 11 + 11 = 44 in both axes, **measured in a real browser** (`getComputedStyle(el, '::before')` against the element's own rect), not asserted from the CSS. The control that replaced fifty 30px text buttons is bigger, not smaller, than what it replaced.
- It stays a real `<button>` with `aria-expanded`/`aria-controls`. The harness proves no `<tr>` carries `aria-expanded` **in the rendered page** and every occurrence sits on a `<button>` — the plan was right that a source grep cannot gate this (`history_page.py` legitimately carries the string three times).
- Its accessible name is translated, swaps with the state, and names the picture (`Show flight details and picture` / `Afficher les détails du vol et l'image`). `flight-rows.js` now writes `aria-label`, never a text label.
- The whole row is clickable: one listener per summary row, with an early return for `A/BUTTON/INPUT/SELECT/TEXTAREA/LABEL/SUMMARY` (T-22-32). The browser check proves the guard by clicking the toggle itself — an unguarded handler would double-toggle and land back collapsed.
- `cursor: pointer` is keyed only on `flight-row--clickable`, which the script adds at load; the harness asserts the server's own output contains no `cursor` anywhere and no collapsing class.
- The chevron is a **server-rendered aria-hidden glyph**, not a CSS `content:` string (T10's rule) and not `layout.icon_html()` — the sprite carries no chevron symbol and `layout.py` belongs to 22-08 this wave.

### Task 2 — days, one hop, and the picture where it belongs

- Rows group by **Europe/Paris** calendar day. The fixture proves it: a 22:30 UTC row (00:30 Paris the next day) opens its own group, which a UTC grouping would have merged.
- Labels are `Today` / `Yesterday` / an absolute date, translated, composed from `layout.month_abbr()` — and the harness pins the absolute form equal to the day portion of `layout.local_clock_text()`'s own cross-day output, in both languages. `history_page.py` now contains **zero** direct date-formatting calls.
- The separator is a real `<tr><th scope="colgroup" colspan="6">` on `--color-canvas` and declares **no positioning at all**; a check asserts that, so it cannot quietly become the second sticky claim while T4 is removing the first.
- The Flight cell links to `/airlines?resolve={prefix}`, built from the real `airlines_page.AIRLINES_ROUTE`/`RESOLVE_QUERY_PARAM` values (cross-module guard retargeted from the retired Health-anchor one). The prefix is derived through `manual_resolutions.normalise_prefix()` — the same normaliser the resolve view applies at its own boundary — then URL-quoted and escaped (T-22-30).
- The panel picture is a labelled `View picture` / `Voir l'image` control **inside the detail row**, on `.calendar-disconnect-btn`'s treatment. Its `aria-label` is gone (the visible label is the accessible name); `View panel near this time` survives as the `title`.
- The raw ISO appears **only** inside a `data-copy-value` attribute — asserted by stripping every such attribute from the render and searching what is left. The visible timestamp is the Paris local clock in the `.time-value` role, never `mono`.
- Phone cards carry the airline name and, when real artwork exists, the gallery's own served frame in a contain-fitted 56px box joining the shared image rule as a fourth selector. No `<img>` at all when no file exists (home_page.py's own broken-image finding, honoured).
- `"ORY → JFK Departing"` is joined by the module's existing `.cell-inline-sep` middle dot.

### Task 3 — A-18, closed a second time

- `.filter-bar__meta` wraps the count and Clear into one flex item. At 390px both now report **the same `getBoundingClientRect().top`** (320.390625), where before Clear sat on its own line at y=320 with the count at y=287 — verified by temporarily reverting the wrapper and re-measuring, so the new check is known to fail for the right reason.
- The group rule is page-agnostic and carries no page-scoped selector, so 22-11 and 22-12 adopt it by adding the same wrapper element.

## Register consequences for plan 22-16

1. **`.row-toggle` moves category.** From the touch-target register's **traded-away** list (30px base button geometry) to its **relocated** list (a 22px visual box with a synthesized 44x44 hit area). `references/control-density.md`'s recorded **rejection** of the icon-only pattern for this control — "unlike `.copy-btn`, the row-toggle carries visible text" — must be marked **SUPERSEDED in place** with the reason that X5 removed that visible text and so dissolved the rejection's own stated ground. Both register entries change; `.row-toggle` had no CSS rule at all before this plan.
2. **`.calendar-disconnect-btn` gains a second consumer here too.** §4 already names X7's per-card Replace control as the second; the Flights picture control is the **other** new call site, so the skill entry should name both. Still not a `.btn` family.
3. **`.filter-bar__meta` is a new shared component.** Plans **22-11 (Airlines)** and **22-12 (Health)** must add the same wrapper element around their own count and Clear — no per-page variant, and no fork of `.filter-bar [data-filter-clear]`.
4. **`.now-showing__image` / `.preview-frame__image`'s shared rule now has four selectors** (`img.recent-flight__thumb` from 22-07, `img.history-card__thumb` from this plan).

## Deviations from Plan

### Auto-fixed issues

**1. [Rule 1 - Bug] The converged `[data-filter-clear]` rule never undid the UA's `line-height`**

- **Found during:** Task 3, while measuring at 390px.
- **Issue:** The rule's own docstring promises "every declaration below undoes a specific base-button property ... so the button variant and the link variant land on pixel-identical output". `line-height` was not among them: History's `<button>` took the UA's `normal` (14px) while Airlines' `<a>` inherits the body's 1.5 (18px). The two converged controls were 4px apart in height, and History's Clear sat 2px below the count beside it inside the centre-aligned group.
- **Fix:** `line-height: inherit` added to the one shared rule (not a fork). Both variants are now 18px; the count and Clear report identical tops.
- **Files modified:** `companion/static/style.css`
- **Commit:** `cb5951e`

**2. [Rule 1 - Bug] A backtick in a `flight-rows.js` comment tripped that file's ES5-safety guard**

- **Found during:** Task 3's full-suite run. This was a **new failure hiding among the three known root-sandbox failures** — `companion/test_companion_app.py` was at 257/260 rather than its expected 258/260.
- **Issue:** Task 1's new comments used Markdown-style backticks; `test_companion_app.py` (owned by 22-08, not editable here) asserts `flight-rows.js` contains no backtick at all, as a template-literal guard.
- **Fix:** Comments reworded; the file carries zero backticks. No test exception was added.
- **Files modified:** `companion/static/flight-rows.js`
- **Commit:** `cb5951e`

### Deliberate departures from the written spec

**1. The day separator's absolute form is `26 Aug` / `26 août`, not `9 September` / `9 septembre`.**
22-UI-SPEC.md §1's copy table gives `%-d %B` (a full month name). The plan's own `<action>` and `<decisions_covered>` forbid a second date path in this file and require the label to be "the formatter's output" — and `layout`'s only month table is the **abbreviated** one (`month_abbr()`, `_MONTH_ABBR`/`_MONTH_ABBR_FR`). A full-month label would have required either a new twelve-entry table in `history_page.py` or a `layout.py` edit (22-08's file this wave). The abbreviated form is shipped; if the full month is wanted, it belongs in `layout.py` as a second exposed table, not here. **Recorded for 22-16.**

**2. The retired two-hop link has no fallback for a callsign-less row.**
Previously `_unresolved_link_html()` rendered for *every* unresolved-airline row. The resolve view is prefix-keyed, so a row with no callsign (or a malformed one) has nothing to resolve; such rows now render no link rather than a link that could only land on a validation failure. `resolve_prefix_for_callsign()` re-states one gate rather than importing it: `server/plane/enrich.py`'s registry writer requires `[A-Z]{3}[A-Z0-9]+` before recording a prefix, and that regex is private to that module. Documented at the function.

**3. The card's `<details>` "Aircraft" pair lost the airline.**
The airline (and its resolve link) moved onto the card's own face, so the disclosure's Aircraft row now carries the aircraft type alone. This keeps the existing "exactly one resolve anchor per card" invariant intact rather than rendering the link twice.

## Acceptance criteria that did not evaluate as predicted

Two criteria were **literal greps that count prose as well as code**, and both would have failed on correctly-written code:

1. **Task 2: `grep -c "strftime" companion/pages/history_page.py` outputs `0`.** My first draft had zero `strftime` *calls* but three comments explaining that no `strftime` call may live here — the grep returned 3. The comments were reworded to say "a direct date-formatting call" instead. The criterion now returns `0` **and** the module genuinely has no such call; the code was never adjusted to satisfy it, only the prose describing it.
2. **Task 2: `grep -c "position: *sticky"` equals its pre-task value.** Same class: my day-separator rule's comment quoted `position: sticky` while explaining why the rule declares none, taking the count from 4 to 5. Reworded to "sticky-positioning claim", with a note in the CSS stating why the phrase is not quoted. **Pre-task value: 4. Post-task value: 4.**

A third criterion is in genuine tension with the UI-SPEC contract it comes from, and is recorded rather than worked around:

3. **Task 3 / B11: "the count and Clear report equal bounding-box tops" vs. `.filter-bar__meta { align-items: center }`.** Those two are only simultaneously satisfiable when the two items have **equal heights** — with centre alignment and a height mismatch, the tops necessarily differ by half the difference. As shipped they measured 320.39 vs 322.39 (2px = half of the 4px height mismatch). Rather than relax the criterion or abandon the spec's `align-items: center`, the height mismatch itself was repaired as a Rule 1 bug (deviation 1 above) — it was a real, independently-stated defect in the converged Clear rule. The criterion now passes for the right reason, and the tension is recorded here so a future plan restating the B11 contract knows that "equal tops" implicitly requires equal heights.

## Exceptions added or removed

**None added. One string pair retired, not excepted:** `"More"` / `"Less"` (and their French `"Plus"` / `"Moins"`) were **deleted** from `companion/i18n_fr/flights.py` along with the visible labels they translated — not exempted from the dead-translation check. `"View unresolved prefixes"` was likewise deleted with the two-hop route it named. Four new keys ship with French entries: `Show flight details and picture`, `Hide flight details and picture`, `Today`, `Yesterday`, `Name this airline`, `View picture` (six). `"%s illustration"` is reused from `companion/i18n_fr/home.py` rather than redefined — the auto-merge package rejects duplicate keys across siblings.

## Requirements ticked

**None.** `CFG-30` is served by **nine** plans (D-07's B2–B18/X3–X9) and remains open: B11 is fixed on Flights only, with Airlines and Health still to adopt `.filter-bar__meta` in 22-11/22-12. The traceability row was updated in place to record 22-09's share (X5 in full, B11's Flights third) without checking the box. `CFG-29` was not touched — the three plural strings 22-08 left open are still open, and `airlines_page.py`'s `MANUAL_SUMMARY_TEMPLATE` pair belongs to 22-11, not to this plan.

## Harness counts

| Harness | Before | After | Why |
|---|---|---|---|
| `companion/test_view_pages.py` | 126 | **136** | +4 (Task 1), +5 (Task 2), +1 (Task 3). Eight further checks retargeted in place with no count change. |
| `companion/test_browser_ux.py` | 6 | **7** | Task 1 net 0 (the Flights scenario retargeted and extended in place); Task 3 +1 (the 390px measurement). |
| `companion/test_i18n.py` | 24 | 24 | Unchanged; new strings ship with French entries. |
| `companion/test_config_page.py` | 223 | 223 | Unchanged — the `:has()` gate untouched (`@supports selector(:has(*)) {` still exactly 1). |
| `companion/test_status_pages.py` | 251/252 | 251/252 | Unchanged (the known root-sandbox `anomaly_active()` case). |
| `companion/test_companion_app.py` | 258/260 | 258/260 | Unchanged (the two known root-sandbox WR-11 cases). |

Every count was re-derived **by running the harness**, never by arithmetic on the diff. New checks were mutation-tested: reinstating a visible toggle label, moving `aria-expanded` onto the `<tr>`, changing `.row-toggle`'s width, dropping the `aria-label` swap from the JS, grouping by UTC instead of Paris, and leaking the raw ISO back into a visible cell each produced exactly one failure.

## Full-suite result

`PYTHON=server/.venv/bin/python bash scripts/run-all-tests.sh` → **3 failing harnesses, 5 failing checks, all documented root-sandbox cases** and all name-matched:

- `server/test_manual_resolutions.py` — 2 × WR-11 read-only-directory cases (`add_entry`/`delete_entry`)
- `companion/test_companion_app.py` — 2 × WR-11 read-only-directory cases (the two POST routes)
- `companion/test_status_pages.py` — 1 × `anomaly_active()` non-existent-path case

Coverage **93%** (floor 83). `ruff check .` clean.

## Verification

- [x] `companion/test_view_pages.py` → 136/136
- [x] `companion/test_browser_ux.py` → 7/7 (real Chromium, not skipped)
- [x] `companion/test_config_page.py` → 223/223
- [x] `companion/test_i18n.py` → 24/24
- [x] `scripts/run-all-tests.sh` → no new failure, coverage 93 ≥ 83
- [x] `ruff check .` clean
- [ ] `<human-check>` (folded into 22-16): with scripts blocked, every detail row visible and no row shows a pointer cursor; with scripts on, tapping a row anywhere but a control expands it.

## Self-Check: PASSED

All modified files exist on disk; all three task commits (`a71cc93`, `11dba24`, `cb5951e`) are present in `git log`.
