---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 10
subsystem: ui
tags: [i18n, french, airlines-page, flights-page, edit-toggle, simple-mode]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/i18n.py (t()), the companion/i18n_fr/ auto-merging catalogue package, companion/prefs.py (simple_mode()/current_lang()), ctx[\"lang\"]/ctx[\"simple_mode\"]"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-04: the .airlines-edit-toggle CSS rule"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-06/20-07: companion/i18n_fr/home.py and display.py's own catalogue entries this plan reuses (Departing/Arriving, Callsign, Runway) and the health.py entries from 20-03 (Timestamp, Corroboration, Both agree, They disagree, Only one saw it, More details, Clear, %d of %d shown)"
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-07: the Device page's own \"Edit artwork\" link deletion (D-36's Device-page half)"
provides:
  - "companion/pages/airlines_page.py — a \"Change pictures\"/\"Done\" airlines-edit-toggle anchor at the top of the gallery section, gated on ctx[\"simple_mode\"], linking to the phase-19 ?edit=1 gate unchanged (D-36)"
  - "companion/pages/airlines_page.py rendering entirely through i18n.t(); companion/i18n_fr/airlines.py — Airlines' full French catalogue"
  - "companion/pages/history_page.py rendering entirely through i18n.t(); companion/i18n_fr/flights.py — Flights' full French catalogue"
  - "lightbox_caption_text()'s day/month prefix now follows the request language (a D-07 gap this plan closed while already touching that function)"
affects: [20-12-completeness-sweep]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two literal <a> branches (never a runtime-built href) for a two-state toggle whose href itself changes shape (?edit=1 present or absent) — D-36's own explicit instruction, and the only way to satisfy a literal `href=\"...\"` acceptance grep"
    - "Keep a comparison value's SOURCE untranslated (row[\"airline_label\"] stays the raw AIRLINE_FALLBACK_TEXT constant) and translate only at the final render site, whenever a page compares a computed value against one of its own English constants to decide what else to render — translating at the comparison's own source would make the membership test fail under a non-English request"
    - "Promote a bare literal string used across two-plus render sites straight to an inline i18n.t(\"literal\") call rather than a new ALL_CAPS module constant, when a plan's own acceptance criteria pin the file's constant count — same behaviour, no new named binding"
  bare_literal_i18n_calls:
    - i18n.t("Close") — companion/pages/airlines_page.py (_lightbox_html), companion/pages/history_page.py (_lightbox_html)
    - i18n.t("Choose an image") — companion/pages/airlines_page.py (_resolve_upload_form_html)
    - i18n.t("Clear") — both pages' own filter bars
    - i18n.t("%d of %d shown") — both pages' own filter bars
    - i18n.t("Airlines") — companion/pages/airlines_page.py's own page_header() call

key-files:
  created:
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/flights.py
  modified:
    - companion/pages/airlines_page.py
    - companion/pages/history_page.py
    - companion/test_view_pages.py

key-decisions:
  - "The toggle's two <a> variants are two separate literal format strings (one per branch), never one shared template built from AIRLINES_ROUTE/EDIT_QUERY_PARAM at runtime — the plan's own text (\"one anchor with two literal hrefs\") and this file's own acceptance criterion (grep -c 'href=\"/airlines?edit=1\"' == 1, a literal source-text match) both require this."
  - "\"Close\"/\"Choose an image\"/\"Clear\" are inlined as bare i18n.t(\"...\") calls rather than promoted to new ALL_CAPS constants — Task 2's own acceptance criterion pins the file's ALL_CAPS-constant grep count to its value right after Task 1 (58), and these three strings were genuinely bare literals with no existing constant home; inlining satisfies D-05's translation requirement without incrementing that count."
  - "history_page.format_event_row()'s airline_label stays the raw, untranslated AIRLINE_FALLBACK_TEXT constant when the airline can't be resolved — _type_airline_cell() and the mobile card's own dt block each compare row[\"airline_label\"] against that same constant to decide whether to append the unresolved-airline link, and translating airline_label at its own source would make that comparison fail under a French request (the row would carry the FRENCH text, never matching the English constant). Both render sites now translate only the DISPLAYED copy, after the comparison has already run against the untranslated value."
  - "lightbox_caption_text()'s own day/month prefix (built from a bare `layout._MONTH_ABBR` index, with `layout.local_clock_text(parsed, None)` called for the clock portion ONLY, since that helper's own month-abbreviation branch never runs without a `now_parsed`) is retargeted to select `layout._MONTH_ABBR`/`_MONTH_ABBR_FR` itself from `prefs.current_lang()` — the identical membership test `local_clock_text()` applies internally. This is a D-07 gap this plan's own Task 3 sweep uncovered while already rewriting this exact function to translate LIGHTBOX_CAPTION_TEMPLATE; fixing it in the same commit was the smaller, more correct change than leaving a freshly-touched function's date rendering untranslated (Rule 1)."
  - "Airline names, ICAO/IATA codes, callsigns, hex IDs and timestamps stay untranslated data on both pages, verified against real seeded/curated renders in both languages, not merely asserted."

requirements-completed: [CFG-13, CFG-18]

# Metrics
duration: 100min
completed: 2026-09-12
---

# Phase 20 Plan 10: Airlines "Change pictures" toggle, and Airlines/Flights in French Summary

**A styled "Change pictures"/"Done" anchor replaces the deleted Device-page "Edit artwork" link on Airlines (hidden in simple mode, the phase-19 `?edit=1` gate untouched), and both Airlines and Flights now render entirely in French, backed by two new catalogue modules that reuse five sibling modules' entries wherever the exact same English string already has one.**

## Performance

- **Duration:** ~100 min
- **Started:** 2026-09-12 (session start)
- **Completed:** 2026-09-12
- **Tasks:** 3
- **Files modified:** 5 (2 created, 3 modified)

## Accomplishments
- Airlines gains one `airlines-edit-toggle` anchor at the top of the gallery section: "Change pictures" → `/airlines?edit=1` when closed, "Done" → `/airlines` when open, plus an explanatory sentence — gated on `ctx["simple_mode"]` (D-30), with the phase-19 `?edit=1` lightbox-forms gate (D-22) left byte-for-byte unchanged and a pinned check proving the forms still render when simple mode AND edit mode are both on
- Every user-visible string on `companion/pages/airlines_page.py` and `companion/pages/history_page.py` now renders through `i18n.t()` — verified end to end against real seeded/curated state in both languages (the default gallery grid, the coverage-gap strip, every branch of the resolve-an-unidentified-flight flow including the superseded path, and Flights' table/mobile-card/lightbox/filter-bar copy), with airline names, ICAO/IATA codes, callsigns, hex IDs and timestamps confirmed untouched
- Two new catalogue modules (`companion/i18n_fr/airlines.py`, `companion/i18n_fr/flights.py`) supply the ~63 new French strings between them, reusing nav.py/home.py/health.py/display.py's own entries for 20+ exact-string matches rather than redefining them
- Found and fixed a real D-05/D-07 correctness gap while sweeping: `history_page.lightbox_caption_text()`'s own day/month prefix bypassed `layout.local_clock_text()`'s language-aware month table entirely (a bare index into the English-only `layout._MONTH_ABBR`) — now selects the correct table from `prefs.current_lang()`, the same membership test that function applies internally

## Task Commits

1. **Task 1: The "Change pictures"/"Done" toggle on Airlines (D-36)** - `da8c79d` (feat)
2. **Task 2: The Airlines page through t(), with its French catalogue** - `66bac38` (feat)
3. **Task 3: The Flights page through t(), with its French catalogue** - `19a6fb8` (feat)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/pages/airlines_page.py` - `_edit_toggle_html()` (new), every module-level user-visible constant wrapped in `i18n.t()` at its interpolation site (the gallery/gap-strip headings, the filter bar, the card chips, the manual-resolutions summary/overflow line, every resolve-flow branch, every upload/replace form), two bare literals ("Close", "Choose an image") inlined via `i18n.t("...")` rather than promoted to new constants
- `companion/pages/history_page.py` - every module-level user-visible constant wrapped in `i18n.t()` at its interpolation site (headers, filter bar, copy-button accessible names, the View-panel lightbox, the unresolved-airline link, the mobile card's disclosure summary and dt labels), the airline-fallback/no-callsign membership-test fix, `lightbox_caption_text()`'s month-table language fix
- `companion/i18n_fr/airlines.py` (new) - Airlines' full French catalogue (~40 entries: 3 from Task 1, ~37 from Task 2)
- `companion/i18n_fr/flights.py` (new) - Flights' full French catalogue (26 entries)
- `companion/test_view_pages.py` - 11 new checks across the three tasks (5 for the toggle, 3 for Airlines' French sweep, 3 for Flights' French sweep); `EXPECTED_CHECK_COUNT` 92 → 97 → 100 → 103

## Decisions Made
See `key-decisions` in the frontmatter above — the two-literal-anchor toggle shape, the bare-literal-vs-new-constant choice for "Close"/"Choose an image"/"Clear", the airline-fallback comparison-vs-display split, and the `lightbox_caption_text()` month-table fix.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `lightbox_caption_text()`'s day/month prefix never followed the request language**
- **Found during:** Task 3
- **Issue:** `history_page.lightbox_caption_text()` built its own "day month" prefix from a bare index into `layout._MONTH_ABBR` (the English-only table), calling `layout.local_clock_text(parsed, None)` for the clock portion ONLY — that function's own day/month branch never runs when `now_parsed` is `None`, so this call site's own hand-rolled month text was hard-coded English no matter the request language, contradicting D-07 ("dates and numbers follow the language") for the one date this function renders.
- **Fix:** Selects `layout._MONTH_ABBR` vs `layout._MONTH_ABBR_FR` itself from `prefs.current_lang()`, the identical membership test `layout.local_clock_text()` already applies internally for every other date on the site — never a second, independently-derived language rule.
- **Files modified:** `companion/pages/history_page.py`
- **Verification:** a French-language smoke render of the lightbox caption for a non-today gallery entry now shows the French month abbreviation; the English render is byte-identical to before.
- **Committed in:** `19a6fb8` (Task 3 commit)

**2. [Rule 1 - Bug] Translating `airline_label` at its own source broke the unresolved-airline-link membership test under French**
- **Found during:** Task 3 (caught before committing, via a direct smoke test against seeded state in both languages)
- **Issue:** A first pass translated `format_event_row()`'s `airline_label` field directly (via `i18n.t(AIRLINE_FALLBACK_TEXT)` at its own computation site). `_type_airline_cell()` and the mobile card's own dt block both compare `row["airline_label"] == AIRLINE_FALLBACK_TEXT` afterward to decide whether to append the unresolved-airline link — under a French request the row would already carry the FRENCH fallback text, which never equals the English constant, so the link (and its own translated text) would silently stop rendering for every unresolved airline on a French request.
- **Fix:** `airline_label` stays the raw, untranslated `AIRLINE_FALLBACK_TEXT` constant at its source; both render sites now compute `is_unresolved = row["airline_label"] == AIRLINE_FALLBACK_TEXT` FIRST, then translate only the DISPLAYED copy (`i18n.t(row["airline_label"]) if is_unresolved else row["airline_label"]`) before interpolating it — the comparison and the translation can no longer disagree.
- **Files modified:** `companion/pages/history_page.py`
- **Verification:** a French smoke render of a no-airline row shows "Compagnie inconnue" AND the "Voir les préfixes non résolus" link, in both the desktop cell and the mobile card's dt block; the pinned English-language tests (which compare directly against the untranslated constant) are unaffected.
- **Committed in:** `19a6fb8` (Task 3 commit)

**3. [Rule 1 - Bug] Two bare literals ("Close", "Choose an image") had no existing named constant, but Task 2's own acceptance criterion pinned the constant count**
- **Found during:** Task 2
- **Issue:** `_lightbox_html()`'s dismissal button and `_resolve_upload_form_html()`'s upload-zone label were bare `"Close"`/`"Choose an image"` string literals, not ALL_CAPS module constants — the read_first's own "~56 constants" inventory (and Task 2's own acceptance criterion, "the constant count is unchanged from before this task") both assumed every translatable string already had a named home. Promoting them to new constants (as first attempted) incremented the file's own ALL_CAPS-constant grep count, tripping that criterion.
- **Fix:** Both literals are wrapped inline as `i18n.t("Close")`/`i18n.t("Choose an image")` at their call sites, never bound to a new module-level name — identical translated behaviour, zero change to the constant count.
- **Files modified:** `companion/pages/airlines_page.py`
- **Verification:** `grep -cE '^[A-Z][A-Z0-9_]+ *= *[("f]?"' companion/pages/airlines_page.py` reads 58 both immediately after Task 1 and after Task 2's full sweep.
- **Committed in:** `66bac38` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (all Rule 1 — correctness issues surfaced by this plan's own systematic sweep and direct bilingual smoke-testing, not pre-existing regressions)
**Impact on plan:** No scope creep — every fix is a same-effect correction required for this plan's own D-05/D-07 obligations and acceptance criteria to actually hold under a real French request, not a new feature or a different design.

## Issues Encountered

**Two static scripts still carry hard-coded English literals D-06 names, but neither is in this plan's file scope.** `companion/static/list-filter.js`'s own live re-count writes `visibleCount + " of " + totalCount + " shown"` directly in JavaScript (not from a `data-*` attribute) whenever a filter query changes the visible set — this page's own SERVER-rendered initial count (`_filter_bar_html()`'s `count_text`) is translated by this plan, but a live re-filter on either Airlines or Flights will briefly show the English words again until the next full page load. `companion/static/copy-button.js`'s `FEEDBACK_TEXT = "Copied"` is likewise still a hard-coded English literal, unchanged by either page's own translated copy-button *labels* (accessible names), which this plan does translate. 20-CONTEXT.md's own D-06 resolution names only `copy-button.js` and `dirty-state.js` as still carrying such literals; `list-filter.js`'s own "of"/"shown" literal is a second, apparently unlisted instance of the same class of gap. Both files are outside this plan's declared `files_modified` (companion/pages/airlines_page.py, companion/pages/history_page.py, companion/i18n_fr/airlines.py, companion/i18n_fr/flights.py, companion/test_view_pages.py) and are shared static assets several other pages also depend on — flagged here rather than fixed, for whichever later plan (20-12's completeness sweep, or a dedicated D-06 follow-up) owns `companion/static/*.js`.

No other issues — every task's own `<verify>` command passes as specified, and the full local suite (`scripts/run-all-tests.sh`) shows exactly the five pre-existing, documented root-sandbox failures (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`), identical in shape to the pre-plan baseline and confirmed unrelated to this plan's own changes by direct inspection of each failure's own assertion text.

## Known Stubs

None — every render path this plan ships is real, immediately-effective code (the toggle, the two catalogue modules, the two pages' full translation sweep); nothing here is a placeholder awaiting a later plan's markup.

## Threat Flags

None beyond the phase's own `<threat_model>` register. `escape_html()` is applied at every interpolation site exactly as before, including every new `i18n.t(...)` call site — no translated string is ever treated as pre-escaped, matching T-20-03's own mitigation. No new network endpoints, auth paths or schema changes; the artwork upload/replace/delete forms' own routes, validation and session-gating are untouched (T-20-31's own accept disposition holds).

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Airlines and Flights are now fully bilingual, joining Home/Display/Device (20-06/20-07) — every everyday page D-08's completeness harness (20-12) will sweep is done.
- `companion/i18n_fr/airlines.py` and `companion/i18n_fr/flights.py` both merge cleanly into the auto-merging `companion.i18n_fr.CATALOG` (confirmed live, no duplicate-key `ValueError`), and both reuse the five sibling modules' entries wherever the same English source string already existed — no orphaned/duplicate translation anywhere in the merged catalogue.
- `companion/test_view_pages.py` (103/103), `companion/test_i18n.py` (11/11), `companion/test_config_page.py` (194/194) all exit 0. `companion/test_companion_app.py` and `companion/test_status_pages.py` show only the pre-existing, documented root-sandbox FAILs, confirmed unrelated to this plan by direct inspection.
- **Flagged for 20-12 or a dedicated D-06 follow-up:** `companion/static/list-filter.js`'s own "of"/"shown" literal (see Issues Encountered) — a second instance of the class of gap D-06's own resolution named only `copy-button.js`/`dirty-state.js` for.
- No blockers for D-08's completeness harness: every string this plan added has a catalogue entry, and no catalogue entry in either new module is unused (each is read by at least one `i18n.t()` call site in its own page).

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: companion/pages/airlines_page.py
- FOUND: companion/pages/history_page.py
- FOUND: companion/i18n_fr/airlines.py
- FOUND: companion/i18n_fr/flights.py
- FOUND: companion/test_view_pages.py
- FOUND commit: da8c79d (Task 1)
- FOUND commit: 66bac38 (Task 2)
- FOUND commit: 19a6fb8 (Task 3)
