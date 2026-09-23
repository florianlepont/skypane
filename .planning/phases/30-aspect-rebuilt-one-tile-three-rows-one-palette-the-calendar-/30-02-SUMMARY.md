---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 02
subsystem: ui
tags: [config-page, theme-picker, css-swatch, html-templating, i18n]

requires:
  - phase: 30-01
    provides: "Playwright + Chromium usable from server/.venv/bin/python3, the genuine pre-change CFG-86 baseline"
provides:
  - "_palette_swatch_html(theme_id, extra_class=\"\") — the app's first CSS-drawn, non-photographic themed swatch, reading only departing_index/band_index from the live registry"
  - "_palette_chip_html(field_name, theme_id, selected, radio_form_id=None) — one palette entry (hidden radio + swatch + caption), no <img>, no photo route call"
  - "_palette_grid_html(field_name, selected_theme_id, radio_form_id=None, leading_html=\"\", labelled_by=\"\") — the wrapping 18-entry palette grid, THEME_IDS order, no id of its own"
  - "_usage_row_summary_html(usage, theme_id, meta_text=None) — the closed-row <summary>, row label + meta joined via ASPECT_ROW_SUMMARY_TEMPLATE"
  - "ASPECT_ROWS_GROUP_NAME / ASPECT_ROW_SUMMARY_TEMPLATE module constants"
affects: [30-03, 30-04, 30-05, 30-06, 30-07, 30-08]

tech-stack:
  added: []
  patterns:
    - "A CSS-drawn swatch reads ONLY the two registry keys its rule needs (departing_index, band_index) — never dithered/band_dithered/ink_index/weight — so sketch-vs-registry transcription drift becomes structurally moot rather than something to remember."
    - "When a plan's own inline verify script asserts a naive substring count that collides with a locked BEM-style class name (palette-swatch vs palette-swatch__band sharing a string prefix), the fix is a collision-free count (an attribute unique to the outer element), not a renamed class — the class name is the spec's contract, the count is the check's implementation detail."
    - "Retarget a pre-existing invariant check in place when a plan's own design deliberately adds a second instance of what the check assumed was singular (_theme_chip_grid_html + _palette_chip_html both legitimately emit data-preview-src) — allow-list the exact expected set rather than loosening the assertion to `>= 1`, so a genuine third accidental fork is still caught."

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/test_config_page.py

key-decisions:
  - "Task 1's own mandated mutation-test revert step (`git checkout-index -f`) restores from the INDEX, not just undoes the last edit — since nothing was staged yet at that point, it wiped the entire Task 1 addition, not just the mutation. Recovered by re-applying the correct code from the read-back file state, then re-verified green before proceeding. For Task 2's own mutation tests, staged the correct code first (`git add`) so the same revert command was safe (restores to the staged, correct version, not HEAD)."
  - "The plan's own Task 2 inline verify script's `g.count(\"palette-swatch\") == len(THEME_IDS)` assertion is a genuine bug in the plan text, not in the implementation: `.swatch__band`'s locked class name (`palette-swatch__band`, required verbatim by Task 1's own spec) shares the `palette-swatch` string prefix, so every banded chip's swatch contributes 2 occurrences, not 1 (23 vs 18, confirmed by running it). Verified the SAME property with a collision-free count instead (`aria-hidden=\"true\" style=\"background:\"`, unique to the outer swatch wrapper) and documented this as a Rule-1 fix rather than silently patching the plan text."
  - "Retargeted one pre-existing check (`_the_departures_grid_is_the_one_renderer_presented_as_a_strip`) in place: its \"exactly ONE function emits a chip <label> with data-preview-src\" guard now allow-lists exactly the two functions 30-UI-SPEC.md's own Structural Contract names as deliberate (`_theme_chip_grid_html`, `_palette_chip_html`), preserving the guard's real property (catch an ACCIDENTAL third fork) instead of loosening it to `>= 1`."
  - "`_usage_row_summary_html()`'s em-dash join is computed from `ASPECT_ROW_SUMMARY_TEMPLATE` (\"%s — %s\") exactly once per call, then sliced back into a `usage-row__name` prefix and a `usage-row__meta` suffix — so the dash has one source even though it renders inside a different, differently-styled element than the row label, per 30-UI-SPEC.md's Typography table (16px semibold name vs 14px muted meta)."

patterns-established:
  - "Aspect palette constants live beside FRAME_COLOURS_ROW_LABELS, not scattered — ASPECT_ROWS_GROUP_NAME/ASPECT_ROW_SUMMARY_TEMPLATE follow the existing 'one constants neighbourhood per feature' convention this file already keeps."

requirements-completed: [CFG-85]

coverage:
  - id: D1
    description: "_palette_swatch_html() draws the registry-derived 5-of-18 band / 13-of-18 solid split (never a hardcoded count), a plain theme as one solid <span> with no dither opacity, and space-joins extra_class onto its class attribute"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_palette_swatch_html_matches_the_live_registry_band_facts"
        status: pass
      - kind: other
        ref: "mutation test: dropped the `band_index != departing_index` half of the guard condition — check FAILed with 'expected exactly the registry-derived banded themes [...] to carry a palette-swatch__band child, got [..., band_blue_field, band_red_field]', then reverted"
        status: pass
    human_judgment: false
  - id: D2
    description: "_palette_chip_html()/_palette_grid_html() render one chip per registered theme in THEME_IDS order, zero <img>, data-preview-src (D-24) and form=\"settings-form\" on every chip, exactly one selected check glyph, leading_html before the chips, no id of its own"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_palette_grid_html_renders_one_chip_per_registered_theme_in_order_no_photo"
        status: pass
      - kind: other
        ref: "mutation test 1: renamed the label's data-preview-src attribute away — check FAILed with 'expected data-preview-src on all 18 chip <label>s ..., got 0', then reverted"
        status: pass
      - kind: other
        ref: "mutation test 2: re-sorted the THEME_IDS loop with sorted() — check FAILed with 'expected one radio per THEME_IDS entry IN REGISTRY ORDER, got [band_black, band_blue, ...]' (alphabetical, not registry order), then reverted"
        status: pass
    human_judgment: false
  - id: D3
    description: "_usage_row_summary_html() renders a well-formed <summary> joining the translated row label and meta text via ASPECT_ROW_SUMMARY_TEMPLATE's single em-dash source, and renders no swatch element at all when theme_id is None (the rules row)"
    requirement: CFG-85
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_usage_row_summary_html_joins_row_label_and_meta_with_one_em_dash_source"
        status: pass
    human_judgment: false
  - id: D4
    description: "Nothing calls the four new renderers yet — the rendered /display page is byte-identical to the pre-plan tree, and the only two functions this plan's own diff touches are pure-addition hunks (the new constants block, the new function block), never _frame_colours_card_html/calendar_group/_theme_chip_grid_html/render()"
    requirement: CFG-85
    verification:
      - kind: other
        ref: "diff of /display rendered before (detached worktree at SHA 0ede20d) vs after (this plan's HEAD) — empty diff, confirmed via `diff /tmp/rendered_before_30_02.html /tmp/rendered_after_30_02.html` exit 0"
        status: pass
      - kind: other
        ref: "git diff -U0 companion/pages/config_page.py | grep -c '^@@' — 2 hunks, both pure additions (constants block at old line 248, new function block at old line 1657)"
        status: pass
    human_judgment: false

duration: 28min
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 02: Palette Renderers (Interface-First) Summary

**Built the four new Aspect palette-rendering primitives — the app's first CSS-drawn, non-photographic theme swatch plus its chip/grid/row-summary wrappers — as pure, non-vacuously-tested functions that nothing calls yet, proving both registry facts (5-of-18 band themes, `band_blue_field`/`band_red_field` solid) and byte-for-byte rendered-page identity before any merge work begins.**

## Performance

- **Duration:** ~28 min
- **Started:** 2026-09-22T13:38:00Z (approx, immediately following 30-01's own completion timestamp)
- **Completed:** 2026-09-22T14:06:00Z
- **Tasks:** 2/2
- **Files modified:** 2 (`companion/pages/config_page.py`, `companion/test_config_page.py`)

## Accomplishments

- `_palette_swatch_html(theme_id, extra_class="")` — one outer `<span class="palette-swatch">` filled with `_palette_hex(departing_index)`, plus an optional `<span class="palette-swatch__band">` child, emitted iff `band_index` is present AND differs from `departing_index`. Proven against the LIVE registry: exactly 5 of 18 themes (`band_blue`, `band_blue_light`, `band_green_light`, `band_red`, `band_black`) carry the band child; the other 13 (11 plain + `band_blue_field` + `band_red_field`, whose `departing_index == band_index`) draw solid. Reads only `departing_index`/`band_index` — never `dithered`, `band_dithered`, `ink_index`, or `weight` — which makes both sketch-transcription corrections named in the plan's `<registry_facts_derived_live>` moot by construction.
- `_palette_chip_html()` / `_palette_grid_html()` — the 18-entry palette grid mirroring `_theme_chip_grid_html()`'s hidden-radio idiom but dropping the `<img>`, the two `.theme-chip__dot` spans, and the swatch legend. Every chip carries `data-preview-src` (D-24, the attribute `theme-preview.js` reads) and `form="settings-form"`; zero `<img>` anywhere; chips render in `device_config.THEME_IDS` registry order; `leading_html` (for `_same_as_departures_chip_html()`'s future output) interpolates before the chips; the grid emits no `id` of its own (avoiding the `_theme_carousel_html()`-class multi-call-site collision trap).
- `_usage_row_summary_html()` — the closed accordion row's `<summary>`, joining the translated row label and meta text (theme name, or the Rules row's explicit rule-count/empty-state text) through one shared format constant, `ASPECT_ROW_SUMMARY_TEMPLATE = "%s — %s"`, computed once per call and sliced into differently-styled `usage-row__name`/`usage-row__meta` spans.
- `ASPECT_ROWS_GROUP_NAME = "aspect-rows"` and `ASPECT_ROW_SUMMARY_TEMPLATE` added beside `FRAME_COLOURS_ROW_LABELS`; both confirmed to need no French catalogue entry (`test_i18n.py`'s completeness scan excludes the first as a lowercase-hyphenated identifier and the second as letterless once its `%s` specs are stripped).
- Confirmed empirically, not just by code-reading: the rendered `/display` page is byte-identical before and after this plan (diffed against a detached worktree at the pre-plan SHA — empty diff), and `git diff` on `config_page.py` shows exactly two pure-addition hunks.

## Task Commits

1. **Task 1: `_palette_swatch_html()` — one swatch renderer, three size tiers** — `bb94924` (feat)
2. **Task 2: `_palette_chip_html()`, `_palette_grid_html()`, `_usage_row_summary_html()`** — `13e653b` (feat)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `companion/pages/config_page.py` — adds `_palette_swatch_html()`, `_palette_chip_html()`, `_palette_grid_html()`, `_usage_row_summary_html()`, `ASPECT_ROWS_GROUP_NAME`, `ASPECT_ROW_SUMMARY_TEMPLATE`. Two pure-addition hunks; `_frame_colours_card_html()`, `calendar_group()`, `_theme_chip_grid_html()`, and `render()` are byte-identical.
- `companion/test_config_page.py` — three new checks (one per renderer group), `EXPECTED_CHECK_COUNT` re-derived twice by running (274 → 275 → 277), and one pre-existing check retargeted in place (see Decisions).

## Decisions Made

See `key-decisions` in the frontmatter above for the four substantive ones (mutation-test revert scope, the plan's own inline-verify-script bug, the retargeted pre-existing check, and the em-dash single-source construction).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Task 1's mutation-test revert command wiped the whole task addition, not just the mutation**
- **Found during:** Task 1's mandated mutation test
- **Issue:** The plan instructs `git checkout-index -f -- companion/pages/config_page.py` to revert the mutation. Run before anything was staged, this restored the file from the git INDEX — which still held the pre-Task-1 committed content — deleting `_palette_swatch_html()` entirely, not just undoing the one-line mutation.
- **Fix:** Re-applied the correct (non-mutated) Task 1 implementation from the same text used originally, re-ran the harness and inline verify script to confirm green, then proceeded. For Task 2's two mutation tests, staged the correct code first (`git add`) so the identical revert command restored to the staged, correct version rather than HEAD — the safe order the plan's own instruction implicitly assumes but doesn't state.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_config_page.py` green at 275/275 after Task 1's recovery, 277/277 after Task 2.
- **Committed in:** `bb94924`, `13e653b` (the recovery is folded into each task's own single commit — no separate "fix the fix" commit was needed since the mutation was never itself committed)

**2. [Rule 1 - Bug] The plan's own Task 2 `<verify>` inline script asserts a substring count that structurally cannot pass**
- **Found during:** Task 2's `<verify>` step
- **Issue:** `assert g.count("palette-swatch") == len(dc.THEME_IDS)` double-counts every banded chip, because the band child's class name — `palette-swatch__band`, locked verbatim by Task 1's own spec and by 30-UI-SPEC.md's Structural/Markup Contract — shares the `"palette-swatch"` string prefix. Running the literal script produced 23, not 18 (5 extra, exactly the 5 banded themes).
- **Fix:** Verified the same underlying property (one swatch per chip) with a collision-free count instead: `g.count('aria-hidden="true" style="background:')`, an attribute-value pair unique to the outer swatch wrapper (the band child never carries `aria-hidden`). Also added `g.count('class="palette-swatch palette-chip__swatch"') == len(THEME_IDS)` as a second, independent confirmation. The committed check in `companion/test_config_page.py` uses this collision-free form directly, not the plan's literal substring count.
- **Files modified:** none (the fix is in how the check counts, not in `config_page.py`'s markup — the markup matches the plan's own locked spec exactly)
- **Verification:** ad-hoc script re-run with the corrected count — `OK`; committed check green at 277/277.
- **Committed in:** `13e653b`

**3. [Rule 1 - Bug] A pre-existing check's "exactly one renderer" invariant is now stale by the plan's own explicit design**
- **Found during:** Task 2, first full `companion/test_config_page.py` run after adding `_palette_chip_html()`
- **Issue:** `_the_departures_grid_is_the_one_renderer_presented_as_a_strip` (25-06-PLAN.md/27-07-PLAN.md) source-scans `config_page.py` and asserts exactly one function emits a chip `<label>` carrying `data-preview-src`, guarding against an accidental second chip renderer forking from `_theme_chip_grid_html()`. 30-UI-SPEC.md's own Structural Contract explicitly requires a SECOND, DELIBERATE renderer (`_palette_chip_html()` — "This palette chip is NOT `_theme_chip_grid_html()`'s existing chip... a new, second, smaller renderer"), so the scan now (correctly) found two and failed.
- **Fix:** Retargeted the check in place — the allow-list is now exactly `["_theme_chip_grid_html", "_palette_chip_html"]` rather than a single name, preserving the check's real property (no THIRD, accidental fork) instead of loosening it to "at least one." Updated the check's own docstring/failure message to state the two deliberate names explicitly.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `companion/test_config_page.py` green at 277/277; the check still fails if the scan finds a third emitter (unverified by direct mutation in this plan, but the allow-list comparison structurally cannot pass a third name).
- **Committed in:** `13e653b`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — bugs in the mutation-test revert procedure and in two pre-existing checks, one from the plan text and one from a stale prior-plan invariant)
**Impact on plan:** All three were necessary to get to a genuinely green, non-vacuous state; none changed the shipped markup contract from what 30-UI-SPEC.md/30-02-PLAN.md locked. No scope creep — `_frame_colours_card_html()`, `calendar_group()`, `_theme_chip_grid_html()`, and `render()` are all byte-identical to before this plan.

## Issues Encountered

**`companion/test_browser_ux.py` flaked on a re-run.** The full `scripts/run-all-tests.sh` run showed `test_browser_ux.py` FAIL (91/96), listing 5 failures — the 3 already documented as a pre-existing floor in 30-01-SUMMARY.md, plus 2 new-looking ones (`net::ERR_CONNECTION_RESET` navigating to `/health`, and a `<time data-relative>` freshness readout that read the identical clock value twice within its 2.2s assertion window). A direct standalone re-run of `companion/test_browser_ux.py` reproduced exactly the 3 documented pre-existing failures (93/96) with neither of the other two recurring — confirming those two were environmental flakes (a dropped local connection and a timing race under concurrent JOBS=10 load), not a regression from this plan's changes. This plan's own diff never touches health-page or freshness-timing code, and its four new functions are called by nothing, so there is no code path connecting this plan's change to either flake. Not fixed (out of scope, unrelated code); documented here per the deviation rules' scope boundary.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Four new palette renderers (`_palette_swatch_html`, `_palette_chip_html`, `_palette_grid_html`, `_usage_row_summary_html`) plus `ASPECT_ROWS_GROUP_NAME`/`ASPECT_ROW_SUMMARY_TEMPLATE` are ready for the merge plan (`_aspect_card_html()`) to call — none are called by anything yet, and the rendered `/display` page is proven byte-identical to before this plan.
- The registry facts this plan pinned (5-of-18 band, `band_blue_field`/`band_red_field` solid, 18/18 `departing_index == arriving_index`) are now proven by a running check against the live registry, not by a transcription — the next plan can build the four accordion rows on top of these without re-deriving them.
- `companion/test_config_page.py` is green at `EXPECTED_CHECK_COUNT = 277`; `companion/test_companion_app.py` is unchanged at `317/317`; `companion/test_i18n.py` is green at `24/24`.
- The known pre-existing `test_browser_ux.py` floor (3 FAILs: leave-guard-armed-before-commit, fallback-Save-click-timeout, wake-interval-echo — all in Display/Device save-bar and validation-echo behavior, unrelated to Aspect) carries forward unchanged from 30-01; this plan's own re-runs reconfirmed it at 93/96 with no new, reproducible failures.

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-02-SUMMARY.md`
- FOUND: commit `bb94924` in `git log --oneline --all`
- FOUND: commit `13e653b` in `git log --oneline --all`
