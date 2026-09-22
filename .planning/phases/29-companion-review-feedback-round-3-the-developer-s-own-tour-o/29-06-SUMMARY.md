---
phase: 29-companion-review-feedback-round-3-the-developer-s-own-tour-o
plan: 06
subsystem: ui
tags: [i18n, editorial-floor, health-page, airlines-page, companion, site-wide-check]

requires:
  - phase: 29-05
    provides: "config_page.ASPECT_CAPTION_EXEMPTIONS (the 4-tuple naming Display's Aspect
      captions Phase 30 owns) and the render-level word-count floor pattern this plan
      generalises to all six routes."
provides:
  - "État's battery-trend heading becomes a short, fixed, window-derived
    'Battery · 3 months' / 'Batterie · 3 mois' — the precision
    _battery_trend_caption() computes moves into a sibling caption <p>"
  - "État's check-in card shows one visible sentence (CHECK_IN_CAPTION_OBSERVED);
    every other clause (cadence/empty/not-proof) moves, byte-identical, into a
    <details class='readings-disclosure'>"
  - "État's registry read-only note is split the same way: a 5-word visible
    sentence plus its instruction moved into a matching disclosure"
  - "Compagnies' six over-length captions (GAP_STRIP_BODY, UPLOAD_PREVIEW_CAPTION_TEXT,
    RESOLVE_CAPTION_TEMPLATE, NAME_HINT_TEXT, STEP_B_CAPTION, MANUAL_DELETE_CAPTION)
    shortened to at most 12 words in both languages; MANUAL_SUPERSEDED_NOTE_TEMPLATE
    left unchanged with an argued exemption"
  - "One HTTP-level check in test_companion_app.py measuring every .section-caption
    element on all six authenticated routes, in both languages, over a real
    ThreadingHTTPServer subprocess — CAPTION_FLOOR_EXEMPTIONS, three anti-vacuity
    floors, the site-wide once-per-page apply-timing region invariant"
affects: []

tech-stack:
  added: []
  patterns:
    - "A heading-then-sibling-caption composition (<h2> plus a following
      <p class='text-label section-caption'>) replaces an inline
      <h2><span> caption for any card whose heading previously carried its
      own qualification text"
    - "A moved-clause disclosure: when a caption is reduced to one visible
      sentence, every other clause it used to carry moves verbatim into a
      <details class='readings-disclosure'> immediately after it, rather
      than being cut — proven by a dedicated presence/case check"
    - "Site-wide render-level floor checks duplicate the counting-rule
      helper from the plan that originated it (when that helper is a
      nested, non-importable function) and prove agreement by extracting
      the real source via ast and running both copies on a fixture string"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/pages/airlines_page.py
    - companion/i18n_fr/health.py
    - companion/i18n_fr/airlines.py
    - companion/test_status_pages.py
    - companion/test_companion_app.py
    - companion/test_view_pages.py

key-decisions:
  - "CAPTION_FLOOR_EXEMPTIONS = config_page.ASPECT_CAPTION_EXEMPTIONS, with NO further
    members added. The one candidate the plan anticipated (layout.empty_state()'s
    compact body, composing 'empty-state__body text-label section-caption') never
    needs a text-based exemption entry: it already fails the strict
    {'text-label','section-caption'} subset check _measured_section_captions() uses
    (the identical mechanism that already excludes config_page.py's wake-gauge
    readouts, per 29-05-SUMMARY.md), so it never enters the measured set at all."
  - "test_config_page.py's own _caption_word_count_text is a function nested inside
    main(), not a module-level importable symbol. Rather than re-type the counting
    rule from memory (risking drift), test_companion_app.py duplicates it verbatim
    AND extracts the real source text via ast.get_source_segment(), execs it in
    isolation, and asserts both copies agree on a fixture string before trusting
    either — decision stated explicitly per the plan's own environment note."
  - "MANUAL_SUPERSEDED_NOTE_TEMPLATE is exempt from the floor by ARGUMENT, not by
    exemption-list membership: it renders only as .lightbox__manual-note (a value
    written client-side into an always-empty static <p>), never composes
    .section-caption anywhere in airlines_page.py, and is a status message naming a
    real conflict state — the same 'status/error message, not a caption' distinction
    plan 29-05 draws for computed readouts."
  - "The once-per-page apply-timing relationship is asserted SITE-WIDE as a region
    invariant (zero matches ever render outside the Frame strip's own markup slice;
    at least one match proven to fire inside it), matching plan 29-05's own decision
    — Home's Frame strip (home_page.py's own frame_strip_html() call) legitimately
    carries the sentence twice via its own switch cells, the same shape Display/
    Device already have."
  - "Two French translations that exceeded 12 words on their own — health_page.py's
    CHECK_IN_CAPTION_OBSERVED (pre-existing, untouched by Task 2's own restructuring)
    and SERVER_DATA_SECTION_DESCRIPTION (English already exactly at the 12-word
    floor; French costs one extra token from the real non-breaking space before its
    colon) — were found and fixed only because Task 3's own bilingual, render-level
    check exists; RESEARCH.md's English-only offender table could not have seen
    either, matching 29-05's own precedent finding."

requirements-completed: [CFG-79, CFG-84]

coverage:
  - id: D1
    description: "Battery-trend heading becomes short and fixed ('Battery · N months',
      interpolated from BATTERY_TREND_WINDOW_DAYS), with its precision moved into a
      sibling caption; all three _battery_trend_caption() branches still render"
    requirement: CFG-84
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#the battery-trend heading carries ONLY its short fixed text..."
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#the battery-trend heading's rendered text equals i18n.t_lang(...)..."
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#all three _battery_trend_caption() branches..."
        status: pass
    human_judgment: false
  - id: D2
    description: "État's check-in caption keeps every honesty clause, moved (not cut)
      into a disclosure, across all four observed/cadence-known cases"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#for all four check-in-card cases (observed x cadence-known)..."
        status: pass
    human_judgment: false
  - id: D3
    description: "État's read-only note and Compagnies' six over-length captions
      shortened to at most 12 words in both languages; MANUAL_SUPERSEDED_NOTE_TEMPLATE
      exempt with its reason recorded at the constant"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#the site-wide editorial floor (CFG-79)..."
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#the read-only note is reworded to name Airlines..."
        status: pass
    human_judgment: false
  - id: D4
    description: "One HTTP-level check measures every caption on all six authenticated
      routes in both languages, with CAPTION_FLOOR_EXEMPTIONS reachable, three
      anti-vacuity floors, and the site-wide apply-timing region invariant"
    requirement: CFG-79
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#the site-wide editorial floor (CFG-79)..."
        status: pass
    human_judgment: false

duration: ~3h
completed: 2026-09-22
status: complete
---

# Phase 29 Plan 06: Battery heading, État's moved clauses, and the site-wide editorial floor Summary

**État's battery-trend heading collapses to a fixed "Battery · 3 months" with its precision in a sibling caption; the check-in card and read-only note split into one visible sentence plus a moved-clause disclosure; Compagnies' six over-length captions are cut to 12 words; and one HTTP-level check now measures every caption on all six authenticated routes in both languages — a check that itself caught two French translations RESEARCH.md's English-only table could never have seen.**

## Performance

- **Tasks:** 3/3 completed
- **Files modified:** 7 (`companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/i18n_fr/health.py`, `companion/i18n_fr/airlines.py`, `companion/test_status_pages.py`, `companion/test_companion_app.py`, `companion/test_view_pages.py`)

## Accomplishments

- `BATTERY_SECTION_HEADING` ("Battery trend") is superseded by `BATTERY_SECTION_HEADING_TEMPLATE` ("Battery · %d months"), interpolated with `BATTERY_TREND_WINDOW_DAYS // 30` — never a typed "3" — so the heading can never drift from the window the chart actually plots. `_battery_trend_section_html()`'s `<h2>` now carries only that short text; the precision `_battery_trend_caption()` computes moves into a sibling `<p class="text-label section-caption">`.
- État's check-in card (`_check_in_regularity_section_html()`) now shows exactly one visible sentence (`CHECK_IN_CAPTION_OBSERVED`); the cadence/empty/not-proof clauses it used to join into one ~50-word paragraph move, byte-identical, into a `<details class="readings-disclosure">` immediately after it. The registry's read-only note is split the same way (`_READ_ONLY_NOTE` / `_READ_ONLY_NOTE_DETAIL`).
- Compagnies' six over-length captions (`GAP_STRIP_BODY`, `UPLOAD_PREVIEW_CAPTION_TEXT`, `RESOLVE_CAPTION_TEMPLATE`, `NAME_HINT_TEXT`, `STEP_B_CAPTION`, `MANUAL_DELETE_CAPTION`) are cut to at most 12 words in both languages; `MANUAL_SUPERSEDED_NOTE_TEMPLATE` is left unchanged with a comment arguing its exemption (a status message, not editorial prose, and structurally excluded from the floor's own selector).
- One new check in `companion/test_companion_app.py` measures every non-exempt `.section-caption` element on all six authenticated routes (Home, Display, Flights, Airlines, Health, Device), in both languages, over a real subprocess server — `CAPTION_FLOOR_EXEMPTIONS` imports `config_page.ASPECT_CAPTION_EXEMPTIONS` rather than re-listing it, three anti-vacuity floors guard against a narrowed selector, and the once-per-page apply-timing relationship is asserted site-wide as a region invariant.
- That new check found and fixed two French-only floor violations neither Task 1 nor Task 2's own checks measured: `CHECK_IN_CAPTION_OBSERVED`'s pre-existing French translation (17 words) and `SERVER_DATA_SECTION_DESCRIPTION`'s French translation (15 words, inflated by the real non-breaking space before its colon) — both shortened to 12.

## Task Commits

1. **Task 1: État's battery-trend heading becomes short, with its precision in a sibling caption** - `60a7051` (feat)
2. **Task 2: the editorial floor on État and Compagnies, with every honesty clause moved rather than cut** - `1d0f437` (feat)
3. **Task 3: the site-wide floor — every authenticated route, both languages, over a real server, mutation-proven** - `843b082` (feat)

_This SUMMARY and the tracking-file updates land in the closing `docs(29-06)` commit that follows this file — the LAST plan of Phase 29._

## Files Created/Modified

- `companion/pages/health_page.py` — `BATTERY_SECTION_HEADING_TEMPLATE` added (`BATTERY_SECTION_HEADING` superseded, deleted); `_battery_trend_section_html()`'s `<h2>`+inline-span becomes `<h2>` plus a sibling caption `<p>`; the SVG aria-label call site (`battery_sparkline_svg()`) retargeted onto the same template; `CHECK_IN_CAPTION_*` constants' comments extended to record the move; `_check_in_regularity_section_html()` restructured into one visible caption plus a moved-clause disclosure; `_READ_ONLY_NOTE`/`_READ_ONLY_NOTE_DETAIL` split; `_registry_section()`'s header now emits both plus a disclosure.
- `companion/pages/airlines_page.py` — six caption constants shortened (`GAP_STRIP_BODY`, `UPLOAD_PREVIEW_CAPTION_TEXT`, `RESOLVE_CAPTION_TEMPLATE`, `NAME_HINT_TEXT`, `STEP_B_CAPTION`, `MANUAL_DELETE_CAPTION`); `MANUAL_SUPERSEDED_NOTE_TEMPLATE` gains an exemption-argument comment, unchanged in wording.
- `companion/i18n_fr/health.py` — French twins for every changed English constant; the dead `"Battery trend"` catalogue entry deleted outright; `CHECK_IN_CAPTION_OBSERVED`'s and `SERVER_DATA_SECTION_DESCRIPTION`'s French translations shortened (Task 3's own fixes, see Deviations).
- `companion/i18n_fr/airlines.py` — French twins for the six shortened Compagnies constants.
- `companion/test_status_pages.py` — battery heading/caption structure, order and both-language-relationship checks added; all three `_battery_trend_caption()` branches asserted inside the sibling caption; the four-case check-in moved-clause check added; several existing checks retargeted in place (see Deviations/Retargets below); `EXPECTED_CHECK_COUNT` 312 → 315 (Task 1: +3) → 316 (Task 2: +1).
- `companion/test_companion_app.py` — `CAPTION_FLOOR_EXEMPTIONS` module constant added; the site-wide editorial floor check added (one `check()` call implementing route-list parity, the bilingual length floor, the exemption reachability/skip-count proof, three anti-vacuity floors, and the site-wide apply-timing region invariant); `EXPECTED_CHECK_COUNT` 316 → 317.
- `companion/test_view_pages.py` — one existing check retargeted (see Deviations: outside this plan's `files_modified` list, justified).

## Old-count → new-count table (naive whitespace split, after `%` substitution, leading em dash stripped)

| Constant | Old EN | New EN | Old FR | New FR | i18n_fr module |
|---|---|---|---|---|---|
| `health_page.CHECK_IN_CAPTION_OBSERVED` | 11 (unchanged) | 11 | 17 (pre-existing, Task 3 fix) | 12 | `health.py` |
| `health_page._READ_ONLY_NOTE` | 25 | 5 | 25 | 7 | `health.py` |
| `health_page._READ_ONLY_NOTE_DETAIL` (new, moved body) | — | 19 (disclosure body, not measured) | — | 19 | `health.py` |
| `health_page.SERVER_DATA_SECTION_DESCRIPTION` | 12 (unchanged, already at floor) | 12 | 15 (pre-existing, Task 3 fix) | 12 | `health.py` |
| `airlines_page.GAP_STRIP_BODY` | 15 | 8 | 17 | 8 | `airlines.py` |
| `airlines_page.UPLOAD_PREVIEW_CAPTION_TEXT` | 14 | 8 | 14 | 8 | `airlines.py` |
| `airlines_page.RESOLVE_CAPTION_TEMPLATE` | 15 | 10 | 15 | 10 | `airlines.py` |
| `airlines_page.NAME_HINT_TEXT` | 23 | 6 | 23 | 7 | `airlines.py` |
| `airlines_page.STEP_B_CAPTION` | 15 | 9 | 15 | 10 | `airlines.py` |
| `airlines_page.MANUAL_DELETE_CAPTION` | 13 | 12 | 15 | 11 | `airlines.py` |
| `airlines_page.MANUAL_SUPERSEDED_NOTE_TEMPLATE` | unchanged, exempt by argument | unchanged | unchanged, exempt by argument | unchanged | (no change) |

Not touched by Task 2 (measured, already ≤12): none of Compagnies' remaining captions exceeded the floor besides the six above.

**A word on `SERVER_DATA_SECTION_DESCRIPTION`:** its English source is already exactly at the 12-word floor (unchanged by this plan) — only its French translation needed shortening, because French's real non-breaking space before `:` (D-09's own typographic rule) costs one extra whitespace-split token English's bare colon does not. This is a genuine property of the naive counting rule stated once in the plan's own `<environment>` note, not a bug in the check.

## Harness before/after (all re-derived by RUNNING)

| Harness | Before | After |
|---|---|---|
| `companion/test_status_pages.py` | 312/312 | 316/316 (+3 Task 1, +1 Task 2) |
| `companion/test_i18n.py` | 24/24 | 24/24 |
| `companion/test_companion_app.py` | 316/316 | 317/317 (+1 Task 3) |
| `companion/test_view_pages.py` | 168/168 | 168/168 (one check retargeted in place, no count change) |
| `companion/test_config_page.py` | 274/274 | 274/274 (untouched; plan 29-05's own floor check still passes unchanged) |
| `scripts/run-all-tests.sh` (full suite) | — | `Result: PASS`, coverage 93%, `companion/test_browser_ux.py` reported SKIPPED (playwright not installed), never as a pass |

## Measured per-route caption counts (English; French renders the identical structure) behind the anti-vacuity floors

| Route | Measured `.section-caption` count | Pinned minimum |
|---|---|---|
| `/` (Home) | 2 | 1 |
| `/display` | 15 | 13 |
| `/flights` | 0 (genuinely empty on a fresh, unseeded state — not a narrowed-selector artefact) | 0 |
| `/airlines` | 2 | 1 |
| `/health` | 4 | 3 |
| `/device` | 8 | 6 |

Site-wide total across both languages: 2+2 + 15+15 + 0+0 + 2+2 + 4+4 + 8+8 = **62**, pinned minimum **55**.

## Exemption-list judgement calls

- **`CAPTION_FLOOR_EXEMPTIONS` = `config_page.ASPECT_CAPTION_EXEMPTIONS`, no further members.** The one candidate the plan anticipated — `layout.empty_state()`'s compact body, composing `"empty-state__body text-label section-caption"` — never needed a text-based entry: it already fails `_measured_section_captions()`'s own strict `{"text-label","section-caption"}` subset check (its extra `empty-state__body` token disqualifies it), the identical mechanism plan 29-05 uses to exclude `config_page.py`'s wake-gauge readouts. It never enters the measured set at all, so the exemption's own reachability proof (`skip_count == len(CAPTION_FLOOR_EXEMPTIONS)`, exactly 4 per language) needed no adjustment.
- **`MANUAL_SUPERSEDED_NOTE_TEMPLATE` is exempt by argument, not by exemption-list membership.** It renders only as `.lightbox__manual-note` (a value computed server-side but written into the DOM client-side by `panel-lookup.js`, into an always-empty static `<p>`) and never composes `.section-caption` anywhere in `airlines_page.py` — confirmed by grep. A comment at the constant argues why long is correct here: it is a status message naming a real conflict state (which airline a prefix now resolves to, and that a manual name was superseded), not a description of a control.

## Decision: plan 29-05's counting helper — DUPLICATED, with a proven-agreement check

`test_config_page.py`'s `_caption_word_count_text` is a function nested inside its `main()`, not a module-level importable symbol — confirmed by inspection (it has no top-level `def`, only a `def` inside `main()`'s body). Since it cannot be imported without executing `test_config_page.py`'s entire check suite, `test_companion_app.py`'s new check:

1. Duplicates the exact same three-line rule verbatim (strip tags, unescape entities, strip a single leading em dash, collapse whitespace).
2. Extracts the REAL, current source of `test_config_page.py`'s own `_caption_word_count_text` via `ast.parse()` + `ast.get_source_segment()` (never re-typed from memory), `exec()`s it in an isolated namespace, and runs both copies against a real fixture string (`'  — Hello   "World"&#x27;s <b>caption</b>  '`), asserting byte-identical output before trusting either.

This means a future edit to test_config_page.py's own rule that this file's duplicate doesn't mirror fails loudly, at the very top of the new check, rather than silently measuring the site with two disagreeing rules.

## Retargeted checks (existing properties, still pinned, adapted to the new structure)

**Task 1 (battery heading):**

| Check | What changed |
|---|---|
| `_quick_260902_gjj_muted_captions_compose_section_caption` | The heading's own trailing `<span>` this check located is gone; it now locates the sibling caption `<p>` immediately after `</h2>` instead. |
| `_battery_section_keeps_everything_after_the_move` | `>%s<` search retargeted from `BATTERY_SECTION_HEADING` onto the computed `_battery_section_heading()` text. |
| `_two_tier_hierarchy_carried_by_layout_not_type` / `_nested_card_heading_rhythm_end_to_end` | `headings_to_check` lists retargeted onto `_battery_section_heading()`; the rhythm check's own `allowed` tuple gains `'<p class="text-label section-caption">'` as a fourth member (the new sibling caption's own composition, matching the same pattern Settings-page cards already use directly under their own `<h2>`, per `.section-caption`'s own style.css comment — no CSS edit accompanies this plan). |
| `_prose_table_opts_out_alone` / `_desc_column_muted_end_to_end` | Anchor lookups retargeted onto `_battery_section_heading()`. |
| `_health_page_renders_in_french` | The permanently-dead `"Battery trend"` absence-needle (no source produces it any more) retargeted onto the ENGLISH form of the real, currently-rendered heading — a check that would actually catch a broken French translation. |
| `_health_page_renders_byte_identical_in_english` | `BATTERY_SECTION_HEADING` retargeted onto `_battery_section_heading()`. |
| `_quick_260902_v2v_uir_03_07_12_13_fixes` (UIR-12 half) | The old "space before its em dash" assertion (pinning the retired inline span's own markup) retargeted onto: the sibling caption follows `</h2>` immediately, and its own text carries no leading em dash (the dash was markup this function used to add, never part of the caption's own text). |

**Task 2 (État/Compagnies):**

| Check | What changed |
|---|---|
| `_read_only_note_reworded_to_point_at_airlines_not_the_runbook` | Retargeted from one 25-word equality assertion into two: `_READ_ONLY_NOTE` equals the short visible sentence, `_READ_ONLY_NOTE_DETAIL` equals the moved instruction, both proven present in the render (the detail inside its own disclosure marker). |

**Outside `files_modified` (deviation, see below):**

| Check (file) | What changed |
|---|---|
| `_airlines_full_seeded_render_french_end_to_end` (`companion/test_view_pages.py`) | The hand-typed French needle for `GAP_STRIP_BODY` (now permanently stale after the 15→8 word shortening) retargeted onto `i18n_fr_airlines.CATALOG[airlines_page.GAP_STRIP_BODY]` — the module's own current translation, never a literal that can silently go stale on the next edit. |

## Mutation Proofs (all 7, real failure messages quoted verbatim)

### Task 1 — Mutation A (span back inside `<h2>`)

Reverted the sibling-`<p>` structure to the retired inline `<span>`:
```
FAIL the battery-trend heading carries ONLY its short fixed text (no inline precision
span), immediately followed by a sibling <p class="text-label section-caption">
carrying _battery_trend_caption()'s own text, itself followed by the chart/table
body — index(h2) < index(caption) < index(body) (29-06-PLAN.md Task 1, CFG-84) -
expected the fixed heading marker '<h2 class="text-heading">Battery · 3 months</h2>',
got none
```
(Four other checks failed alongside it, all correctly detecting the reverted structure.) Reverted with `git checkout-index -f -- companion/pages/health_page.py` after staging the correct version.

### Task 1 — Mutation B (hardcoded "3" + `BATTERY_TREND_WINDOW_DAYS` changed to 60)

```
FAIL the battery-trend heading's rendered text equals i18n.t_lang(BATTERY_SECTION_
HEADING_TEMPLATE, lang) % (BATTERY_TREND_WINDOW_DAYS // 30) in both English and
French — a relationship against the real constants, not a typed literal
(29-06-PLAN.md Task 1, CFG-84) - en: expected the heading to equal
i18n.t_lang(BATTERY_SECTION_HEADING_TEMPLATE, lang) % (BATTERY_TREND_WINDOW_DAYS //
30) == 'Battery · 2 months', marker '<h2 class="text-heading">Battery · 2
months</h2>' not found
```
Proves the check pins the RELATIONSHIP (heading text must equal the constant-derived value), not a fixed string — the heading still said "3 months" (hardcoded) while the window changed to 60 days (2 months), and the check caught the mismatch. Reverted with `git checkout-index -f -- companion/pages/health_page.py`.

### Task 2 — deleted `CHECK_IN_CAPTION_NOT_PROOF`'s disclosure append

```
FAIL for all four check-in-card cases (observed x cadence-known), the visible
caption carries EXACTLY CHECK_IN_CAPTION_OBSERVED and every other clause that case
renders moves, byte-identical, into the card's own <details class="readings-
disclosure"> — 'moved, not cut' proven as a relationship, case and clause named on
failure (29-06-PLAN.md Task 2, CFG-79) - observed, cadence known: expected clause
'A day with no record is not proof the frame did not wake: a log rotation this
server missed leaves exactly the same gap.' inside the disclosure — missing (the
'moved, not cut' guarantee is broken)
```
(The pre-existing `CLAUSE 3` check from 24-07-PLAN.md also failed alongside it, both correctly detecting the missing clause.) Reverted with `git checkout-index -f -- companion/pages/health_page.py`.

### Task 3 — Mutation A (a deliberately long caption on an unedited route)

Appended a 13-word second sentence to `airlines_page.NAME_HINT_TEXT` (a Compagnies caption Task 3 itself did not touch, on `/airlines`):
```
FAIL the site-wide editorial floor (CFG-79): ... - /airlines/en: a non-exempt
section-caption renders 19 word(s) (max 12): 'Start typing — pick a suggestion.
MUTATION A this sentence has exactly thirteen words appended right here today now.'
```
Reverted with `git checkout HEAD -- companion/pages/airlines_page.py`.

### Task 3 — Mutation B (French-only long value)

Lengthened only the French translation of `NAME_HINT_TEXT`, leaving English untouched:
```
FAIL the site-wide editorial floor (CFG-79): ... - /airlines/fr: a non-exempt
section-caption renders 21 word(s) (max 12): 'Commencez à taper — choisissez une
suggestion. MUTATION B cette phrase française contient bien plus de douze mots au
total ici.'
```
Fails on the `fr` pass ONLY — proving the `<html lang>` assertion and the `sp_ui_lang` cookie threading actually select the French render rather than silently re-measuring English. Reverted with `git checkout HEAD -- companion/i18n_fr/airlines.py`.

### Task 3 — Mutation C (the exemption list cannot grow silently)

Appended an unrelated string to `CAPTION_FLOOR_EXEMPTIONS`:
```
FAIL the site-wide editorial floor (CFG-79): ... - en: expected exactly 5 CAPTION_
FLOOR_EXEMPTIONS skip(s) across the whole site, got 4 — either the exemption is
unreachable or it silently swallowed a caption it should not have
```
Reverted with `git checkout-index -f -- companion/test_companion_app.py`.

### Task 3 — Mutation D (the once-per-page rule)

Replaced `CHECK_IN_CAPTION_OBSERVED` with the bare apply-timing sentence (`frame_state.DELAY_UNKNOWN`'s own text), rendered under the Health check-in card — outside any Frame strip:
```
FAIL the site-wide editorial floor (CFG-79): ... - the apply-timing sentence
rendered outside the Frame strip's own slice — CFG-79 confines it to exactly one
place per page: /health/en at offset 13319 ('Applies the next time the frame wakes
up.'): 'Applies the next time the frame wakes up.'; /health/fr at offset 13564
('S'applique au prochain réveil du cadre.'): 'S'applique au prochain réveil du
cadre.'
```
Caught in BOTH languages, at the correct offset, naming the route. Reverted with `git checkout-index -f -- companion/pages/health_page.py`.

## Control result

With the correct source in place, the site-wide check PASSES against Display's four Aspect captions exactly as they are today — `git diff --stat 3286263 HEAD -- companion/pages/config_page.py` is empty, and `CALENDAR_URL_HINT` (22 words) does not fail the check; it is skipped via `CAPTION_FLOOR_EXEMPTIONS`. Confirmed by the full clean run: `companion-app: 317/317 checks pass`.

## Requirement coverage across all six 29-*-PLAN.md files (phase-closing check)

```
29-01-PLAN.md: requirements: [CFG-81]
29-02-PLAN.md: requirements: [CFG-82]
29-03-PLAN.md: requirements: [CFG-83]
29-04-PLAN.md: requirements: [CFG-80]
29-05-PLAN.md: requirements: [CFG-79]
29-06-PLAN.md: requirements: [CFG-79, CFG-84]
```

CFG-79 through CFG-84 each appear at least once across the six plans (CFG-79 doubly, in 29-05 and 29-06, since it is the same requirement completed in two waves — Display/Device's floor, then État/Compagnies/site-wide).

## Decisions Made

See `key-decisions` in the frontmatter above (CAPTION_FLOOR_EXEMPTIONS scope, the counting-helper duplication-and-proof, MANUAL_SUPERSEDED_NOTE_TEMPLATE's argued exemption, the site-wide apply-timing region invariant, and the two French-only floor violations Task 3's own check found and fixed).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two French translations exceeded 12 words on their own, surfaced only by Task 3's own bilingual, render-level check**

- **Found during:** Task 3, while building and verifying the site-wide floor check against a real render of every route.
- **Issue:** `health_page.CHECK_IN_CAPTION_OBSERVED`'s French translation ("Chaque case correspond à un jour de régularité observée des relevés, du plus ancien au plus récent.") was 17 words — a PRE-EXISTING violation from before this plan, never touched by Task 2's own restructuring (Task 2 only moved OTHER clauses out of the caption; it never edited this clause's own translation). Separately, `health_page.SERVER_DATA_SECTION_DESCRIPTION`'s French translation was 15 words, even though its English source is already exactly at the 12-word floor — French's real non-breaking space before its colon (D-09's own typographic rule) costs one extra whitespace-split token English's bare colon does not.
- **Fix:** Shortened `CHECK_IN_CAPTION_OBSERVED`'s French translation (17 → 12 words: "Chaque case représente un jour observé, du plus ancien au plus récent."). Shortened `SERVER_DATA_SECTION_DESCRIPTION`'s French translation (15 → 12 words: "— le pipeline ADS-B et la résolution des trajets : données fiables ?"), trading "sont-elles fraîches et" for a shorter question form that preserves "route resolution" (résolution des trajets).
- **Files modified:** `companion/i18n_fr/health.py`.
- **Verification:** `companion/test_companion_app.py`'s new site-wide floor check passes at 0 over-length matches in both languages on all six routes; `companion/test_i18n.py` stayed 24/24.
- **Committed in:** `843b082` (Task 3's own commit).

**2. [Rule 1 - Bug] test_view_pages.py's hand-typed French `GAP_STRIP_BODY` needle went stale**

- **Found during:** Task 2, on the first full `companion/test_view_pages.py` run after `GAP_STRIP_BODY` was shortened from 15 to 8 words.
- **Issue:** `_airlines_full_seeded_render_french_end_to_end` asserted the OLD French translation ("Le cadre a vu ces indicatifs mais ne connaît pas la compagnie") was present in a French render — a literal that no longer matches the shortened translation, so the check failed even though the actual French translation was correct and complete.
- **Fix:** Retargeted the needle onto `i18n_fr_airlines.CATALOG[airlines_page.GAP_STRIP_BODY]` — the module's own current translation, symbolically, so a future edit to this string cannot silently go stale here again.
- **Files modified:** `companion/test_view_pages.py` — outside this plan's own `files_modified` list (`companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/i18n_fr/health.py`, `companion/i18n_fr/airlines.py`, `companion/test_status_pages.py`, `companion/test_companion_app.py`). Justified: the literal this check pinned was a direct, unavoidable casualty of Task 2's own GAP_STRIP_BODY shortening; leaving it broken would have left a real regression in the test suite this plan touched.
- **Verification:** `companion/test_view_pages.py` 168/168, unchanged count (retargeted in place, no check added or removed).
- **Committed in:** `1d0f437` (Task 2's own commit).

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bug fixes; one a genuine pre-existing/newly-surfaced French floor violation, one a direct casualty of this plan's own shortening).
**Impact on plan:** Both necessary for correctness — CFG-79 requires the floor to hold "in both languages" across the whole site, and a broken test needle is a regression in the harness this plan is responsible for leaving green. No unrelated scope creep: no constant outside this plan's own touched set, or the one directly-broken test needle, was changed.

## Issues Encountered

**Per-task commit reconstruction.** Health_page.py, i18n_fr/health.py, and test_status_pages.py each carry BOTH Task 1 and Task 2 edits in non-overlapping regions of the same files. To produce one commit per task (per the executor's task-commit protocol) rather than one combined commit, each file's diff against the pre-plan baseline was split by hunk (Task 1's hunks applied and committed first; Task 2's hunks applied and committed second), with `EXPECTED_CHECK_COUNT`'s own comment block split into two sequential assignments (315, then 316) to match. Both intermediate states were independently re-run to green (315/315 after Task 1 alone, 316/316 after Task 1+2) before committing, and the final reconstructed files were byte-diffed against the originally-authored full-plan version to confirm no content was lost or altered in the split.

## Self-Check

- FOUND: commit `60a7051`
- FOUND: commit `1d0f437`
- FOUND: commit `843b082`
- FOUND: `companion/pages/health_page.py`
- FOUND: `companion/pages/airlines_page.py`
- FOUND: `companion/i18n_fr/health.py`
- FOUND: `companion/i18n_fr/airlines.py`
- FOUND: `companion/test_status_pages.py`
- FOUND: `companion/test_companion_app.py`
- FOUND: `companion/test_view_pages.py`

## Self-Check: PASSED
