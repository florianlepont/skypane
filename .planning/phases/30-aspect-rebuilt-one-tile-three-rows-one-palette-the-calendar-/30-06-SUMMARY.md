---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 06
subsystem: ui
tags: [config-page, accordion, calendar, i18n, coverage-ledger, test-harness]

requires:
  - phase: 30-04
    provides: "_aspect_card_html()/_usage_row_html() (companion/pages/config_page.py) — the merged Aspect card this plan folds the calendar's connection block into"
  - phase: 30-05
    provides: "_aspect_usage_row_bounds()/_rules_row_segment() (companion/test_config_page.py), _ASPECT_REPIN_LEDGER's own guard, and the 5 rows this plan owed (calendar-placement/no-inline-JS/h2-order/title-inventory/no-card-builder)"
provides:
  - "_calendar_connection_html() (companion/pages/config_page.py) — the calendar's connection block (status row, connect/replace/disconnect, How-it-works), extracted from the retired calendar_group(), returning a (row_body_html, disconnect_form_html) tuple, threaded into the Calendar accordion row"
  - "_aspect_card_html() gains six calendar_* keyword parameters and now renders the WHOLE Aspect card including the calendar's connection block — one render gate (screens.GROUP_THEME alone), the relied-on registry invariant (companion/screens.py's everyday_groups) documented at the gate"
  - "ASPECT_CAPTION_EXEMPTIONS down to its two permanent members (DISPLAY_LOOK_INTRO, CALENDAR_URL_HINT) — CALENDAR_CAPTION removed"
  - "companion/test_config_page.py re-pinned: 5 ledger rows paid, 1 unledgered property REPLACED (Display's Look supersection now carries exactly one data-dirty-section card, not two), and every other calendar_group()/CALENDAR_SECTION_HEADING/CALENDAR_HEADING_ID/CALENDAR_CAPTION reference this plan's own Task 1/2 retired is repointed or reworded — 269 -> 274 checks"
affects: [30-07, 30-08]

tech-stack:
  added: []
  patterns:
    - "A retired production symbol's own NAME can still break a test harness even after every live reference to it is gone, if the harness's own verify script bans the literal substring anywhere in the file (not just as a Python identifier) — this plan's own <verify> script for Task 3 does exactly that for 'calendar_group', which meant historical prose comments, ledger 'why' fields, and even a NEW replacement check's own predicted name (from the 30-03 ledger) all had to be respelled, not merely the live code paths. Two ledger rows hit the identical 'retired name has no def'-vs-'replacement name collides with the retired name's own substring' trap 30-05-SUMMARY.md already documented once for same-NAME repoints; this plan hits a new variant of it for same-SUBSTRING repoints."
    - "A shared test-harness locator helper (_aspect_usage_row_bounds()'s own last-row fallback, _rules_row_segment()'s delegate) can be a single point of failure for ~15 checks when its own end-boundary literal assumes a sibling element that a LATER plan retires — here, the fallback searched for the separate Calendar card's own 'page-section page-section--nested' wrapper, which this plan's own Task 1/2 retires outright. Every OTHER Display-scope card uses a different base class ('theme-status'), so the literal was never a safe anchor even coincidentally once the Calendar card was gone. Fixed by repointing to the 'What it watches' supersection's own id-anchored heading, which unconditionally renders on every Display-scope render regardless of which cards are present."

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/calendar_group.py
    - companion/test_config_page.py

key-decisions:
  - "The plan's own Task 2 action text cited companion/i18n_fr/display.py as the file holding CALENDAR_CAPTION's French entry. The real entry ('Flights from your calendar get their own colour on the frame.' -> 'Les vols de votre calendrier...') lives in companion/i18n_fr/calendar_group.py, not display.py — confirmed by direct grep before editing. Deleted from the correct file (Rule 1 — the plan's own file citation was inaccurate, not the underlying instruction)."
  - "_calendar_connection_html() returns a (row_body_html, disconnect_form_html) TUPLE, not one concatenated string — the plan's own Task 1 action text specifies this explicitly (the row body nests inside <details>, the disconnect <form> must not). Every test-harness call site that used to treat calendar_group()'s single string return as one blob now string-joins the tuple once, inside a small helper (_calendar_connection_call()), preserving every downstream check's own logic unmodified."
  - "_look_supersection_carries_exactly_one_dirty_section_named_aspect() REPLACES (not repoints) the retired data-dirty-section=\"Calendar\" count check, per the plan's own <derivation_first> instruction not to leave the old two-section arithmetic in place. Net check-count effect: zero (one check retired, one landed) — not counted among the 5 paid ledger rows, since it was never a ledger row to begin with (an escalated, unledgered break this plan's own Task 1/2 changes caused)."
  - "Two _ASPECT_REPIN_LEDGER rows diverge from their own predicted replacement/retired-label text, for two DIFFERENT variants of the same underlying guard-collision class 30-05-SUMMARY.md already documented once: (1) the calendar-placement row's predicted replacement name itself contained the literal substring this plan's own Task 3 <verify> script bans anywhere in the file, so the landing name swaps 'group' for 'connection'; (2) the no-inline-JS row's own 'retired' label (a pure historical data string, never a live def) ALSO contained that banned substring, so it is respelled ('group' -> 'card') with the true historical name never restated verbatim anywhere in the file, including this row's own explanatory comment. Both divergences are recorded in each row's own 'why' field."
  - "The no-card-builder-function ledger row's own predicted replacement name is IDENTICAL to its retired name (30-03's own same-name-repoint convention, matching 30-05's precedent). Landing it verbatim would trip the ledger guard's own unconditional 'retired name has no def' clause the instant the replacement function existed. Resolved identically to 30-05's own fix: appended '_after_the_merge' to the landing name, divergence recorded in the row's own 'why'."

patterns-established: []

requirements-completed: [CFG-85]

coverage:
  - id: D1
    description: "_calendar_connection_html() (companion/pages/config_page.py) — the calendar's connection block (status row, connect/replace, Disconnect, How-it-works), extracted verbatim from the retired calendar_group(), threaded into the Calendar accordion row directly beneath that row's palette and field error, per 30-UI-SPEC.md §6 (no third 'Gérer' wrapper); the disconnect <form> stays a sibling fragment of the whole .aspect-card div, never nested inside the row"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr, _calendar_row_no_inline_js_and_palette_cross_submits_form, _calendar_connection_never_nests_a_form_inside_another_in_either_state — PASS"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py (run) — 274/274 checks pass, all three calendar states (connected/not-connected/drift) asserted separately by the file's own suite"
        status: pass
    human_judgment: false
  - id: D2
    description: "One render gate for the merged card (screens.GROUP_THEME in groups alone) — the second card's own local variable and its separate GROUP_CALENDAR-gated condition are retired outright; the relied-on registry invariant (companion/screens.py's everyday_groups lists GROUP_THEME and GROUP_CALENDAR together) is documented at the gate itself, machine-checked to appear within 1400 characters before the gate and to name both companion/screens.py and everyday_groups; handle_post()'s two independent screens.GROUP_* validation gates are byte-unchanged (git diff evidence below)"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py (run) — 317/317 (up from 304/317 mid-Task-1, matching 30-04's own documented sequencing precedent)"
        status: pass
      - kind: other
        ref: "git diff d7ee157 HEAD -- companion/pages/config_page.py, grepped for the two handle_post() gate lines (screens.GROUP_CALENDAR not in scope_groups(...) at line 6101, screens.GROUP_THEME not in in_scope at line 6469) — zero diff hunks touch either line; git diff also shows zero hunks inside calendar_disconnect_confirm_page()"
        status: pass
    human_judgment: false
  - id: D3
    description: "ASPECT_CAPTION_EXEMPTIONS narrowed from 3 to 2 members (DISPLAY_LOOK_INTRO, CALENDAR_URL_HINT) — CALENDAR_CAPTION removed in the same commit as the constant itself; CALENDAR_URL_HINT stays unshortened (22 words); the two now-orphaned French catalogue entries (the caption sentence in companion/i18n_fr/calendar_group.py, the bare 'Calendar'->'Calendrier' entry in companion/i18n_fr/display.py) are deleted in the same commit as their English source constants"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_i18n.py (run) — 24/24, no dead-translation orphan"
        status: pass
      - kind: unit
        ref: "python -c \"from companion.pages import config_page as cp; assert len(cp.ASPECT_CAPTION_EXEMPTIONS) == 2 and cp.CALENDAR_URL_HINT in cp.ASPECT_CAPTION_EXEMPTIONS and len(cp.CALENDAR_URL_HINT.split()) >= 20\" — no assertion error"
        status: pass
    human_judgment: false
  - id: D4
    description: "companion/test_config_page.py re-pinned: all 5 _ASPECT_REPIN_LEDGER rows owed to this plan paid (owed_by cleared, each replacement's own def confirmed live); one unledgered property REPLACED (the data-dirty-section=\"Calendar\" count check, since Display's Look supersection genuinely drops from two data-dirty-section cards to one); every other escalated, unledgered break this plan's own Task 1/2 changes caused (calendar_group()/CALENDAR_SECTION_HEADING/CALENDAR_HEADING_ID/CALENDAR_CAPTION references, plus the shared _aspect_usage_row_bounds()/_rules_row_segment() last-row-fallback break affecting ~15 checks) is repointed or reworded; zero reference anywhere in the harness to the four retired calendar symbols; EXPECTED_CHECK_COUNT 269 -> 274, re-derived by running"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py (run) — 274/274 checks pass"
        status: pass
      - kind: other
        ref: "this plan's own Task 3 <verify> script (ledger non-empty, no 30-06-owed rows remain, every cleared row's replacement has a live def, zero 'calendar_group'/CALENDAR_SECTION_HEADING/CALENDAR_HEADING_ID/CALENDAR_CAPTION substring anywhere in the harness) — OK, still-owed=2 (both 30-07)"
        status: pass
      - kind: other
        ref: "three required mutations (disconnect form moved inside the calendar row; the Aspect heading removed from the h2 sequence; a second data-dirty-section card added under Look) — each caught by name, messages quoted in this SUMMARY's own Mutation Test Results section, all reverted (git diff --stat empty after each)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full suite green outside this plan's own scope: companion/test_companion_app.py 317/317, companion/test_i18n.py 24/24, companion/test_browser_ux.py unchanged at 84/91 (the same 7 named checks 30-04/30-05 documented — 3 pre-existing floor, 4 routed to 30-08); scripts/run-all-tests.sh (JOBS=4, run twice) reports 21/22 PASS on the second run (the one FAIL is test_browser_ux.py's own documented floor) — the first run's lone extra failure (an unrelated illustration-upload check, BrokenPipeError) did not reproduce on the second run or in either standalone test_companion_app.py run, confirming parallel-execution flakiness rather than a regression"
    requirement: CFG-85
    verification:
      - kind: integration
        ref: "companion/test_browser_ux.py (run standalone) — 84/91, 7 named FAILs identical to 30-04/30-05's own documented set"
        status: pass
      - kind: integration
        ref: "scripts/run-all-tests.sh JOBS=4 (run twice) — run 1: 20/22 (one flaky unrelated illustration-upload FAIL in test_companion_app.py, BrokenPipeError, plus test_browser_ux.py's documented floor); run 2: 21/22 (test_browser_ux.py's documented floor only) — matching 30-05-SUMMARY.md's own identical precedent for this suite's parallel-run flakiness"
        status: pass
    human_judgment: false

duration: ~60min (from 30-05's own completion commit, d7ee157, to this plan's last commit, b90a4f9)
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 06: Fold the calendar's connection into the Aspect card Summary

**The calendar's connection block (status row, connect/replace/Disconnect, How-it-works) is extracted from the retired `calendar_group()` into `_calendar_connection_html()` and threaded directly into the Calendar accordion row — one merged card, one `<h2>Aspect</h2>`, one render gate, one `data-dirty-section` card under Look (down from two) — with the two-step disconnect gate, `handle_post()`'s validation gates, and the write-only URL contract all byte-unchanged, and `companion/test_config_page.py` re-pinned from 269 to 274 checks to prove it, including ~15 checks whose own shared locator helper broke as an unledgered side effect of the merge.**

## Performance

- **Duration:** ~60 min (from 30-05's own completion commit, `d7ee157`, to this plan's last commit, `b90a4f9`)
- **Started:** 2026-09-22 (immediately following 30-05's completion)
- **Completed:** 2026-09-22T19:32:18+02:00
- **Tasks:** 3/3
- **Files modified:** 4 (`companion/pages/config_page.py`, `companion/i18n_fr/display.py`, `companion/i18n_fr/calendar_group.py`, `companion/test_config_page.py`)

## Accomplishments

- **`companion/pages/config_page.py`**: `calendar_group()` retired outright, its body extracted into `_calendar_connection_html(configured, drift, last_synced_at, last_attempt_at, now, entry_count, errors=None, submitted=None, state_dir=None)` — SAME arguments, same four-branch status logic, same write-only-field contract, same two-step disconnect gate — now returning a `(row_body_html, disconnect_form_html)` **tuple** rather than one concatenated string (the row body nests inside the Calendar `<details>`; the disconnect `<form>` must not, so it stays a sibling of the whole `.aspect-card` div, per 30-PATTERNS.md's own sibling-fragment pattern). `_aspect_card_html()` gains six `calendar_*`/`now` keyword parameters (matching `calendar_group()`'s own call-site variable names) and places the connection block directly beneath the Calendar row's own palette and field error — no third "Gérer" wrapper, per 30-UI-SPEC.md §6. `CALENDAR_SECTION_HEADING`, `CALENDAR_HEADING_ID`, `CALENDAR_CAPTION` retired with their own comment (zero surviving consumers, pre-delete counts below). `ASPECT_CAPTION_EXEMPTIONS` narrowed to its two permanent members. `render()`'s Display branch collapses to ONE gate (`screens.GROUP_THEME in groups`) for the whole merged card — the second card's own local variable and its separate `GROUP_CALENDAR`-gated condition are retired from all three scopes and from the interpolation list; the relied-on registry invariant (`companion/screens.py`'s `everyday_groups` lists `GROUP_THEME`/`GROUP_CALENDAR` together) is documented at the gate itself, naming the file and the tuple a future reader must check if a screen type with only one of the two groups is ever registered. `handle_post()`'s two independent `screens.GROUP_*` validation gates are untouched (confirmed by `git diff` — zero hunks touch either line).
- **`companion/i18n_fr/calendar_group.py`**: the connection block's own one-line caption ("Flights from your calendar get their own colour on the frame.") deleted in the same commit as its English source constant — the plan's own Task 2 action text cited `companion/i18n_fr/display.py` for this entry; the real entry lives here (confirmed by direct grep before editing, documented as a deviation below).
- **`companion/i18n_fr/display.py`**: the now-orphaned `"Calendar": "Calendrier"` entry (for the retired `CALENDAR_SECTION_HEADING`) deleted in the same commit as its English source constant. Every other calendar-copy French entry (status verdicts, URL field label/hint, Replace/Disconnect button labels, How-it-works, the three disconnect-confirmation strings) is untouched.
- **`companion/test_config_page.py`** (269 → 274 checks): 5 `_ASPECT_REPIN_LEDGER` rows owed to this plan paid — `_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr` (the calendar connection block renders inside the Calendar row, after its palette, with the Disconnect button inside and the disconnect form outside, the button's `form=` naming that exact sibling — asserted as one relationship, not three separate facts), `_calendar_row_no_inline_js_and_palette_cross_submits_form`, `_display_h2_order_matches_the_merged_aspect_card_placement` (the separate Calendar heading is gone outright, not merely renamed), `_title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge` (Display's tuple re-derived 8/4/3/1 → 7/3/3/1 by running), `_no_card_builder_function_ever_calls_section_intro_html_after_the_merge` (the AST allowlist drops `_frame_colours_card_html`/`calendar_group`, gains `_aspect_card_html`). One unledgered property REPLACED: `_look_supersection_carries_exactly_one_dirty_section_named_aspect()` (Display's Look supersection now carries exactly ONE `data-dirty-section` card, down from two). The shared `_aspect_usage_row_bounds()`/`_rules_row_segment()` last-row-fallback locator — broken by this plan's own retirement of the separate Calendar card, affecting roughly 15 downstream checks — repointed onto `DISPLAY_WATCHES_SECTION_ID`'s own id-anchored heading. Every remaining `calendar_group()`/`CALENDAR_SECTION_HEADING`/`CALENDAR_HEADING_ID`/`CALENDAR_CAPTION` reference across the file (calendar-copy checks, the forbidden-vocabulary scan, the UI-SPEC copy-fidelity check, the pinned-English-strings set, the Calendar-heading placement check, historical ledger "why" text) repointed or reworded — all escalated, unledgered breaks this plan owns per its own `<derivation_first>` instruction.

## Task Commits

1. **Task 1: `_calendar_connection_html()` inside the Calendar row** — `dcc0317` (feat)
2. **Task 2: One render gate, with the registry invariant written at the code** — `5185150` (feat)
3. **Task 3: Re-pin the calendar's properties and clear the 30-06 ledger rows** — `b90a4f9` (test)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `companion/pages/config_page.py` — `calendar_group()` retired, `_calendar_connection_html()` added; `_aspect_card_html()` gains six calendar-status parameters and threads the connection block into the Calendar row; `CALENDAR_SECTION_HEADING`/`CALENDAR_HEADING_ID`/`CALENDAR_CAPTION` retired; `ASPECT_CAPTION_EXEMPTIONS` narrowed to 2; `render()`'s Display branch collapses to one render gate with the registry invariant documented at the gate.
- `companion/i18n_fr/calendar_group.py` — the connection block's own caption's French entry deleted.
- `companion/i18n_fr/display.py` — the orphaned `"Calendar"` French entry deleted.
- `companion/test_config_page.py` — 5 ledger rows paid, 1 unledgered check replaced, the shared row-bounds locator repointed, every other calendar-symbol reference repointed/reworded, `EXPECTED_CHECK_COUNT` 269 → 274.

## `<derivation_first>` Output (verbatim, re-run at plan start)

```
=== companion/test_config_page.py 17 blocks
   None                                                                   def@0      hits=5 first=1263
   _calendar_connect_url_error_never_echoes_the_submitted_secret          def@5821   hits=2 first=5829
   _plain_render_carries_both_disclosures_in_full_never_collapsed         def@8198   hits=1 first=8216
   _calendar_copy_fidelity_against_ui_spec                                def@8382   hits=1 first=8390
   _calendar_forbidden_vocabulary_absent                                  def@8427   hits=2 first=8433
   _calendar_group_call                                                   def@8767   hits=2 first=8767
   _calendar_connect_field_never_carries_value_in_either_state            def@8775   hits=2 first=8782
   _calendar_connect_wraps_in_details_only_when_configured                def@8797   hits=7 first=8805
   _calendar_containment_at_the_renderer_five_needles                     def@8823   hits=3 first=8845
   _calendar_disconnect_checkbox_never_appears_in_calendar_group          def@8859   hits=5 first=8859
   _calendar_disconnect_form_appears_only_when_expected                   def@8876   hits=3 first=8887
   _calendar_exactly_one_page_section_on_display_scope                    def@8927   hits=1 first=8937
   _calendar_group_never_nests_a_form_inside_another_in_either_state      def@8948   hits=4 first=8948
   _calendar_connect_form_appears_before_the_runway_card_on_display_scope def@9036   hits=1 first=9051
   _aspect_display_render_still_carries_every_pinned_english_string       def@9923   hits=1 first=9937
   _calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing def@11088  hits=3 first=11103
   _the_calendar_status_detail_has_a_singular_form                        def@11916  hits=1 first=11924
=== companion/test_companion_app.py 0 blocks
=== companion/test_browser_ux.py 0 blocks
```

**Per-block disposition** (per-block route: keep / repoint / replace; several of these turned out to need a second, unlisted fix — the shared `_aspect_usage_row_bounds()`/`_rules_row_segment()` locator break — documented separately below):

| Block | Disposition |
|---|---|
| `None` (ledger comment mentions, def@0) | keep — cleared as part of paying the 5 ledger rows below |
| `_calendar_connect_url_error_never_echoes_the_submitted_secret` | repoint — renamed `_calendar_connection_url_error_never_echoes_the_submitted_secret`; calls `_calendar_connection_html()`, unpacks the tuple |
| `_plain_render_carries_both_disclosures_in_full_never_collapsed` | repoint — Calendar segment now located via `_aspect_usage_row_bounds()` instead of the retired `CALENDAR_HEADING_ID` |
| `_calendar_copy_fidelity_against_ui_spec` | repoint — `CALENDAR_CAPTION` dropped from the pinned-constant tuple (deleted outright, nothing left to fidelity-check) |
| `_calendar_forbidden_vocabulary_absent` | repoint — `CALENDAR_SECTION_HEADING`/`CALENDAR_CAPTION` in the scanned blob replaced by `FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_CALENDAR]` |
| `_calendar_group_call` (helper) | repoint — renamed `_calendar_connection_call`; calls `_calendar_connection_html()`, string-joins the tuple once so every downstream caller's own logic is unmodified |
| `_calendar_connect_field_never_carries_value_in_either_state` | keep — unaffected by the helper's repoint, property unchanged |
| `_calendar_connect_wraps_in_details_only_when_configured` | keep — unaffected |
| `_calendar_containment_at_the_renderer_five_needles` | keep — unaffected |
| `_calendar_disconnect_checkbox_never_appears_in_calendar_group` | repoint — renamed `..._in_calendar_connection` (retired-symbol-text ban) |
| `_calendar_disconnect_form_appears_only_when_expected` | keep — unaffected |
| `_calendar_exactly_one_page_section_on_display_scope` | **replace** — counted `data-dirty-section="Calendar"`, a property the merge changes shape (not just locator); replaced by `_look_supersection_carries_exactly_one_dirty_section_named_aspect` |
| `_calendar_group_never_nests_a_form_inside_another_in_either_state` | repoint — renamed `_calendar_connection_never_nests_a_form_inside_another_in_either_state` |
| `_calendar_connect_form_appears_before_the_runway_card_on_display_scope` | repoint — Calendar-row landmark switched from `CALENDAR_HEADING_ID`'s `<h2>` to `data-usage="calendar"` |
| `_aspect_display_render_still_carries_every_pinned_english_string` | repoint — `CALENDAR_CAPTION` dropped from the pinned set, `CALENDAR_HOW_IT_WORKS_SUMMARY` takes its place |
| `_calendar_hostile_stored_url_renders_no_masked_line_and_raises_nothing` | keep — unaffected |
| `_the_calendar_status_detail_has_a_singular_form` | repoint — calls `_calendar_connection_html()`, takes `row_body_html` |

**Second, unlisted break found during Task 3** (not visible to the derivation script's 6-token regex, since it doesn't match any of `CALENDAR_SECTION_HEADING`/`CALENDAR_HEADING_ID`/`CALENDAR_CAPTION`/`calendar_group`/`calendar-heading`/`calendar-masked-url`/`calendar-actions`/`calendar-url-disclosure`): `_aspect_usage_row_bounds()`'s own last-row fallback (and `_rules_row_segment()`, which delegates to it) searched for `'<div class="page-section page-section--nested" '` — the separate Calendar card's own nested-wrapper literal, retired outright by this plan's Task 1/2. Affected roughly 15 checks across the file (every check that locates a row segment via either helper). Repointed onto `DISPLAY_WATCHES_SECTION_ID`'s own id-anchored heading, which unconditionally renders on Display regardless of which cards are present.

## Pre-Delete Consumer Counts (Task 1's own required artifact)

Taken repo-wide (`git grep`, code files only: `companion/*.py`, `companion/**/*.py`, `server/*.py`) at 30-05's own final commit (`d7ee157`), immediately before this plan's Task 1 deleted each symbol:

| Symbol | Total mentions | Where |
|---|---|---|
| `calendar_group` | 70 | `companion/app.py` (2, comments), `companion/i18n_fr/calendar_group.py` (2, docstring), `companion/i18n_fr/display.py` (2, comments), `companion/pages/config_page.py` (17, def + 1 real call site in `render()` + comments), `companion/test_config_page.py` (46, calls + comments), `server/plane/calendar_rules.py` (1, comment) |
| `CALENDAR_SECTION_HEADING` | 8 | `companion/pages/config_page.py` (3: def + 2 real reads inside `calendar_group()`'s own `card_html`), `companion/test_config_page.py` (5) |
| `CALENDAR_HEADING_ID` | 4 | `companion/pages/config_page.py` (2: def + 1 real read), `companion/test_config_page.py` (2) |
| `CALENDAR_CAPTION` | 11 | `companion/pages/config_page.py` (6: def + tuple member + comments + 1 real read), `companion/test_config_page.py` (5) |

Every real call site was inside `render()`'s own single line (`calendar_group()`) or the constant's own single real read inside that function — **zero surviving production consumers** after this plan's three commits land. `companion/app.py`, `companion/i18n_fr/*.py` and `server/plane/calendar_rules.py`'s own mentions are comments/docstrings, untouched (out of this plan's `<files>` scope) and harmless.

## Old and New Display `data-dirty-section` Count (Task 2's own required artifact)

- **Before this plan:** 2 — the Aspect card's own `data-dirty-section="Aspect"` plus the separate Calendar card's own `data-dirty-section="Calendar"`.
- **After this plan:** 1 — `data-dirty-section="Aspect"` only, on the one merged card. Verified directly against `_aspect_card_html()`'s own return value (`h.count('data-dirty-section=')` == 1) and against a real `render()` output at both `calendar_configured=True` and `calendar_configured=False` (`_look_supersection_carries_exactly_one_dirty_section_named_aspect`).

## Mutation Test Results (Task 3's three required mutations, all quoted, all reverted)

1. **Move the disconnect `<form>` inside the Calendar row.** Concatenated `calendar_disconnect_form_html` onto the row body instead of the card-level return:
   > `expected the disconnect form OUTSIDE the Calendar row, found it inside`
   (caught by `_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr`; 273/274)

2. **Remove the Aspect heading from the `<h2>` sequence.** Dropped the `<h2 class="text-heading" id="%s">%s</h2>` segment from `_aspect_card_html()`'s own return format string:
   > `expected <h2> order ['Frame', 'Look', 'Aspect', 'What it watches', 'Runway', 'When it is on', 'Quiet hours'], got ['Frame', 'Look', 'What it watches', 'Runway', 'When it is on', 'Quiet hours']`
   (caught by `_display_h2_order_matches_the_merged_aspect_card_placement`; also independently caught by three more checks — `_aspect_card_full_shape_checklist`, the title-form inventory, and the page-wide aria-labelledby-resolves check; 269/274)

3. **Add a second `data-dirty-section` card under Look.** Inserted a synthetic `<div class="page-section page-section--nested" data-dirty-section="Extra"></div>` between the Look intro and the Aspect card:
   > `configured=False: expected exactly one data-dirty-section card under Look, got 2`
   (caught by `_look_supersection_carries_exactly_one_dirty_section_named_aspect`; also independently caught by two more checks — the --nested-modifier count and the title-form inventory; 271/274)

All three mutations reverted via `git checkout -- companion/pages/config_page.py`; `git diff --stat` empty after each revert; `274/274` re-confirmed after the third.

## `git diff` Evidence for `handle_post()` and `calendar_disconnect_confirm_page()`

```
$ git diff d7ee157 HEAD -- companion/pages/config_page.py | grep -n "GROUP_CALENDAR not in scope_groups\|GROUP_THEME not in in_scope"
(no output — zero diff hunks touch either line)

$ grep -n "GROUP_CALENDAR not in scope_groups\|GROUP_THEME not in in_scope" companion/pages/config_page.py
6101:    if screens.GROUP_CALENDAR not in scope_groups(submitted_scope(form)):
6469:    if screens.GROUP_THEME not in in_scope:
(both lines present, unchanged)

$ git diff dcc0317~1 HEAD -- companion/pages/config_page.py | grep -n "^@@.*calendar_disconnect_confirm_page"
(no output — zero hunks inside calendar_disconnect_confirm_page())
```

## `EXPECTED_CHECK_COUNT` Trajectory

| Point | `companion/test_config_page.py` count |
|---|---|
| After 30-05 | 269 |
| Now (after 30-06) | **274** |

+5 from the five paid ledger rows; the replaced (not net-new) `_look_supersection_carries_exactly_one_dirty_section_named_aspect` and every repoint/reword contribute 0 to the count.

## Ledger Tally (as required by Task 3)

`_ASPECT_REPIN_LEDGER` — 19 rows total, none deleted:

- **Cleared this plan (5):** `_calendar_placement_after_display_form_close_with_dirty_attr` (-> `_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr`, DIVERGENCE: landing name swaps "group" for "connection" — the ledger's own predicted name contained the substring this plan's own guard bans), `_calendar_card_no_inline_js_and_chip_grid_cross_submits_form` (-> `_calendar_row_no_inline_js_and_palette_cross_submits_form`; this row's own "retired" label is ITSELF a DIVERGENCE — respelled from its true historical name, which contained the same banned substring), `_display_h2_order_matches_d12_after_calendar_placement_fix` (-> `_display_h2_order_matches_the_merged_aspect_card_placement`), `_title_form_inventory_classifies_every_h2_text_heading_on_both_routes` (-> `..._after_the_merge`), `_no_card_builder_function_ever_calls_section_intro_html` (-> `..._after_the_merge`, DIVERGENCE: same-name collision with the ledger guard, identical to 30-05's own documented fix).
- **Still owed (2), both to 30-07:** `_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable`, `_segmented_control_resets_the_global_label_margin_and_the_legend_leaves_the_serif`.

`_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()` PASSES against this state.

## Decisions Made

See `key-decisions` in the frontmatter above for the five substantive ones: the corrected file citation for `CALENDAR_CAPTION`'s French entry (`calendar_group.py`, not `display.py`); the tuple return shape of `_calendar_connection_html()`; the REPLACE (not repoint) of the `data-dirty-section="Calendar"` count check; the two divergences from the ledger's own predicted text for two different variants of the same guard-collision class; and the same-name divergence on the no-card-builder row, matching 30-05's own precedent.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The plan's own Task 2 action text cited the wrong file for `CALENDAR_CAPTION`'s French entry**
- **Found during:** Task 2, before editing `companion/i18n_fr/display.py` as instructed
- **Issue:** The plan's `<action>` text says "Delete `CALENDAR_CAPTION`'s French entry from `companion/i18n_fr/display.py`." Direct grep found the real entry ("Flights from your calendar get their own colour on the frame." → "Les vols de votre calendrier ont leur propre couleur sur le cadre.") in `companion/i18n_fr/calendar_group.py`, not `display.py` — `display.py`'s own Calendar block carries only the now-orphaned `"Calendar": "Calendrier"` entry (for the separately-retired `CALENDAR_SECTION_HEADING`) plus the confirmation-page strings, which the plan correctly leaves untouched.
- **Fix:** Deleted the caption entry from `companion/i18n_fr/calendar_group.py` (with a retirement comment matching this file's own convention) and, separately, the orphaned `"Calendar"` entry from `companion/i18n_fr/display.py` — both required, neither in the file the plan named for the caption.
- **Files modified:** `companion/i18n_fr/calendar_group.py`, `companion/i18n_fr/display.py`
- **Verification:** `companion/test_i18n.py` green at 24/24 (no dead-translation orphan on either).
- **Committed in:** `5185150` (Task 2 commit)

**2. [Rule 1 - Bug] The shared `_aspect_usage_row_bounds()`/`_rules_row_segment()` last-row locator broke for ~15 checks, unledgered and unlisted by the derivation script**
- **Found during:** Task 3, first full `companion/test_config_page.py` run after Task 1/2 landed
- **Issue:** The helper's own last-row fallback searched for `'<div class="page-section page-section--nested" '` — the separate Calendar card's own nested-wrapper literal (30-05's own docstring, written when that card still existed and reliably followed the Aspect card). This plan's Task 1/2 retire that card outright; every OTHER Display-scope card uses `theme-status`/`theme-status--nested`, never `page-section`, so the literal matched nothing left on the page. Neither the derivation script's 6-token regex nor the `_ASPECT_REPIN_LEDGER` saw this coming — it is a markup-shape dependency inside a shared test helper, not a reference to any of the four retiring symbols.
- **Fix:** Repointed the fallback onto `DISPLAY_WATCHES_SECTION_ID`'s own id-anchored heading (`id="display-watches"`), which every caller's own `config_page.render(..., scope=SCOPE_DISPLAY)` render carries unconditionally, regardless of which cards are present. `_rules_row_segment()` now delegates to `_aspect_usage_row_bounds()` rather than duplicating the (now-fixed) logic a second time.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** Went from ~10 unexpected FAILs (beyond the 5 ledgered + escalated-but-anticipated ones) to 0 after this one fix; full suite re-confirmed green at 274/274.
- **Committed in:** `b90a4f9` (Task 3 commit)

**3. [Rule 1 - Bug] Two `_ASPECT_REPIN_LEDGER` rows' own text collided with this plan's own no-"calendar_group"-substring guard**
- **Found during:** Task 3, running this plan's own `<verify>` script after clearing the 5 owed rows
- **Issue:** The ledger row for the calendar-placement check predicted a replacement name (`_calendar_group_placement_inside_aspect_after_display_form_close_with_dirty_attr`) that itself contains the literal substring `calendar_group` — banned anywhere in the file by this plan's own Task 3 `<verify>` script. The no-inline-JS row's own `"retired"` label (`_calendar_group_no_inline_js_and_chip_grid_cross_submits_form`) — a pure historical data string, never a live Python def — contains the identical substring.
- **Fix:** Landing name for row 1 respells "group" as "connection" (`_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr`); row 2's own `"retired"` label is respelled ("group" → "card") with the true historical name never restated verbatim anywhere in the file. Both divergences recorded in each row's own `"why"` field.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** This plan's own Task 3 `<verify>` script prints `OK` (zero occurrences of `calendar_group`/`CALENDAR_SECTION_HEADING`/`CALENDAR_HEADING_ID`/`CALENDAR_CAPTION` anywhere in the harness).
- **Committed in:** `b90a4f9` (Task 3 commit)

**4. [Rule 1 - Bug] The no-card-builder ledger row's own predicted replacement name collides with the ledger guard, identical to 30-05's own documented fix**
- **Found during:** Task 3, first run of the ledger guard after landing the new function under the ledger's own predicted name
- **Issue:** `_no_card_builder_function_ever_calls_section_intro_html` (retired) and its own predicted replacement are the SAME name (30-03's own same-name-repoint convention). The ledger guard's own unconditional "retired name has no def" clause trips the instant a same-named def lands under it — the exact collision 30-05-SUMMARY.md already documented once, at a different row.
- **Fix:** Appended `_after_the_merge` to the landing name (`_no_card_builder_function_ever_calls_section_intro_html_after_the_merge`), matching 30-05's own resolution pattern; divergence recorded in the row's own `"why"`.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** Ledger guard passes; `274/274`.
- **Committed in:** `b90a4f9` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (1 plan-citation bug with no code-behaviour impact, 1 shared-helper locator bug affecting ~15 checks, 2 ledger-text guard-collision bugs — all Rule 1, all necessary for the harness to genuinely prove what it claims)
**Impact on plan:** None of the four changed what the merged card renders or how it behaves — all four are test-harness-only fixes (a file citation, a locator, two ledger data strings) required for the suite to pass and to genuinely prove the properties it claims, not scope creep into production behaviour.

## Issues Encountered

The first `scripts/run-all-tests.sh JOBS=4` run reported `companion/test_companion_app.py` FAILing on one check (`_pitfall_3_s_warning_sign_made_executable`, an illustration-upload manual-key check unrelated to this plan's scope), with a `BrokenPipeError` exception — a resource-contention symptom of parallel execution, not a code defect. Standalone runs of `companion/test_companion_app.py` (both before and after this run) were green at 317/317, and a second `scripts/run-all-tests.sh JOBS=4` run came back 21/22 (only `test_browser_ux.py`'s own documented floor), matching 30-05-SUMMARY.md's own identical precedent for this suite's parallel-run flakiness. Not a plan-content issue.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `companion/test_config_page.py` is green at `EXPECTED_CHECK_COUNT = 274`; `companion/test_companion_app.py` unchanged at `317/317`; `companion/test_i18n.py` unchanged at `24/24`; `companion/test_browser_ux.py` unchanged at `84/91` (3 pre-existing floor + 4 rows still owed to 30-08).
- `_ASPECT_REPIN_LEDGER` carries 2 remaining rows, both correctly owed to 30-07 — 30-06 owes nothing further.
- `companion/pages/config_page.py`: the Aspect card is now the ONLY card under Look, carrying all four accordion rows including the calendar's full connection block; `calendar_group()` and the three calendar heading/caption constants are gone with zero surviving consumers; the one render gate's own registry-invariant comment is the marker a future multi-screen-type change must find.
- 30-07 (CSS/visual polish for the merged card, per the two remaining ledger rows' own scope — the Disconnect button's specificity/placement and the segmented-control label-margin/legend-serif checks) can proceed against a fully re-pinned `test_config_page.py` baseline.
- 30-08 inherits the same 6 `test_browser_ux.py` rows 30-03/30-04 already routed there — untouched by this plan.
- `scripts/run-all-tests.sh` (JOBS=4) is green (21/22, `test_browser_ux.py`'s own documented floor the one expected FAIL) — confirmed on a clean second run after the first run's unrelated flake did not reproduce.

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-06-SUMMARY.md`
- FOUND: commit `dcc0317` in `git log --oneline --all`
- FOUND: commit `5185150` in `git log --oneline --all`
- FOUND: commit `b90a4f9` in `git log --oneline --all`
