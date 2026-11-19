---
phase: 68-console-and-companion-visual-improvements
plan: 23
subsystem: companion
tags: [airlines, editor, rarity, detail-sheet, render-baseline]
requires: ["68-22", "68-06", "68-08", "68-14"]
provides:
  - "Airlines known by name only as read-only rows with an Artwork button and a filter chip (D-15)"
  - "Rarity as a filled pill on every seen Airlines card (R04) and a detail sheet without inner scroll with a round opaque Close at the top (R05)"
affects: ["68-24"]
key-files:
  created:
    - companion/pages/airline_known_rows.py
    - companion/test_airline_known_rows.py
    - server/test_enrich_known_names.py
  modified:
    - server/plane/enrich.py
    - companion/pages/airline_rows.py
    - companion/pages/airline_table.py
    - companion/pages/airlines_page.py
    - companion/pages/airline_collection_page.py
    - companion/static/style-airlines.css
    - companion/i18n_fr/airlines.py
    - companion/testdata/render_baseline.json
decisions:
  - "The Suggestion tag and the round check button of the unidentified rows are not built: their data source is undecided."
  - "The cross at the top is the only Close of the Airlines detail sheet (approved header); the foot Close strip is hidden."
metrics:
  completed: 2026-11-19
---

# Phase 68 Plan 23: Known-by-name rows, rarity pill and detail sheet Summary

D-15, R04 and R05 built to the approved mockups; no new route, no change to `routes.py` or `airline_actions.py`.

## Phase 64 ownership and open pull requests

This plan touches files Phase 64 owns (all merged): `companion/pages/airlines_page.py` (+2 lines, 1286 to 1288; limit 1500), `companion/pages/airline_table.py`, `companion/i18n_fr/airlines.py`. The GitHub MCP tools were not available to this executor, so the open pull request re-check for `airlines_page.py`, `airline_table.py` and `i18n_fr/airlines.py` could NOT be done here; the orchestrator must run it before merging.

## What was built

- `server/plane/enrich.py`: `names_without_artwork()` returns a fresh sorted tuple of `(prefix, name)`; table and lookups untouched.
- `companion/pages/airline_known_rows.py`: block "Known by name only · N" with one read-only row per airline (name, prefix in mono, "Artwork" button with plus icon, accessible name "Add the first artwork for X"). The button is the existing add-artwork trigger (`_type_trigger_html`), so the shared dialog and the existing upload route are reused. An airline with artwork or whose prefix was named by hand leaves the block.
- Chip "Known by name only" / "Connues par leur nom" with its count, in the mockup order (All, Unidentified, Known by name only, No artwork, Seen, Not seen yet); chips still scroll on one line on a phone.
- Airlines cards: filled pill with dot and word (Regular neutral, Occasional green, Rare violet) at the same place on every seen card; dark tints stronger than light so text keeps 4.5:1.
- Detail sheet: picture, name, pill, then three facts (Seen, Last seen, Aircraft) in one card, as the mockup; no explanatory sentence, no first seen, no callsigns, no per-type rarity tags (the mockup lacks them). `scrollHeight <= clientHeight` at 360x740 and 1280x800 in EN and FR.

## Design-system divergences

- Close icon button is round (50 %, like every other `modal__close`) while the mockup draws a 14 px rounded square; it is opaque (`--color-dominant`) with a 1 px border and 44 px.
- Known-by-name button uses the system `btn--secondary` (grey fill) at 44 px; the mockup draws a white outlined 40 px button.
- The mockup lists the known names in an invented order (Turkish, KLM, FedEx, Finnair); the build sorts by name and lists all six real names (Emirates, FedEx Express, Finnair, KLM Royal Dutch Airlines, Korean Air, Turkish Airlines).
- Rarity pill tint is a token-driven mix (`--rarity-tint`) rather than the mockup's fixed hex fills, to keep the existing rarity tokens and 4.5:1 contrast.
- Sheet grid uses `display: contents` on the shared modal head/body because `ui_modal` is not edited here; the foot Close strip is hidden (the head cross remains focusable and named "Close" / "Fermer").
- Known-by-name rows reuse the unidentified-table layout classes (`airlines-table--gaps`) for table display rules.

## Open owner decisions

1. Suggestion tag and check button on unidentified rows (mockup shows them; how suggestions are produced, local designator list or AI service, is undecided): NOT built; unidentified rows keep the existing "Name it" dialog.
2. An airline that gains artwork (upload) leaves the known block but has no row in the main table (the table lists curated and manually named airlines only); decide whether such airlines should be promoted to the table.
3. Two mockup variants of the Airlines sheet Close exist (text button and cross); the approved header says cross, so the cross was built.

## Deviations from Plan

- [Rule 1] `companion/test_airline_editor.py::test_a_hand_named_airline_keeps_its_row...` split the page on the first `</table>`; the new block adds a table before the editor table, so it now reads the part after the last `</table>`. Intent unchanged.
- Existing collection tests were rewritten to the approved sheet (3 facts, pill, cross); orphan French ids (`collection_rarity_sentence`, `collection_fact_first`, `collection_fact_rarity`, `collection_fact_callsigns`) removed with their English constants. `banner__pill` was already absent from the page (no hand-built pill markup).
- The New pill keeps its 20 px height so it stays clear of the picture.
- [Rule 1] The Artwork button would have 404ed on upload: `post_actions._illustration_filenames` only allowed curated, manual and renamed keys. It now also allows the six keys of the airlines known by name only (same route, same membership check, no new route). `test_illustration_filenames_union_contract` and the 05b membership test were extended accordingly; an upload round trip is tested in `companion/test_airline_known_rows.py`.
- Rarity tint tokens (`--rarity-tint`) and one page-opening stagger rule (known block opens one step after the gaps table) were added to `companion/static/style.css`, so the baseline diff is not limited to `/airlines`: every captured page carries the stylesheet hash (68 lines changed, hashes only apart from the airlines pages). Motion-token and chip tests were extended (six chips, 1 px tolerance on the last scrolled chip, `test_companion_app_04` stagger list).
- Existing tests updated for the sixth chip and six extra rows: `test_browser_airline_table`, `test_browser_flights_cards`, `test_status_pages_05b`, `test_view_pages_03`, `test_browser_overhaul_sweep` (proper names), `test_companion_app_02`, `test_companion_app_04`.

## Commits

- 789d1fc1 feat(68-23): known by name only rows
- a3a4bafc feat(68-23): rarity pill and detail sheet
- 095be613 fix(68-23): upload allow-list, tokens, wave tests
- final commit: baseline regeneration, test alignment, SUMMARY and ROADMAP row (25/36)

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p23/`: `mock_editor_*`, `mock_fla_*` (every mock figure, phone and desktop, EN and FR, light and dark), `before_*`, `after_*` for `editor`, `airlines`, `airlinesheet` (ph 390 and dk 1280, EN and FR, light and dark, full page), and side-by-side `cmp_cards_ph_fr_dark.png`, `cmp_sheet_ph_en_light.png`, `cmp_sheet_ph_fr_dark.png`, `cmp_editor_ph_fr_light.png`.

## Tests

Full suite once at the end with `SKYPANE_REQUIRE_BROWSER=1` and `server/.venv/bin/python`: 15853 passed, 10 failed, 8 skipped. Failures: the known pre-existing set (`test_sign_in_surfaces` 2, `test_config_page_03`, `test_config_page_05`, `test_companion_app_01` 2, `test_sky_contrast` glass) plus three caused by this plan and fixed afterwards (`test_companion_app_02` union contract, `test_companion_app_04` motion tokens, both re-run green) and `test_browser_ux_02` live preview crossfade (passes alone, unrelated flake). Ruff, mypy, function size, comment history pass; `companion/app.py` 1490 lines; `airlines_page.py` 1288 lines.
