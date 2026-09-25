# Phase 33 Migration Ledger

## Purpose

Every pre-migration check of the 9 companion harnesses ends up in this ledger mapped to a real
pytest node id (`ported`), or `deleted` with a stated reason. Together with Phase 32's 769
server-side checks, this covers all 2018 pre-migration checks the 2026-09-23 audit measured
(`.planning/audits/2026-09-23-code-audit.md`, TST-15). The live baseline capture measured 1250,
not the audit's own 2018 − 769 = 1249 arithmetic — `33-BASELINE/INDEX.md`'s Notes section
traces the +1 to a specific commit (`17d5bc7`, plan 32-11) that landed a new check after the
audit's baseline was taken.

Nothing in this file is hand-edited above the `<!-- fragments -->` marker below by anyone other
than 33-01 (this scaffold) — everything from the marker down is regenerated verbatim by
`33-ledger-check.py --assemble` (run once, by 33-33), which also refreshes the Summary table
and grand totals from the 9 fragments' current state.

## Format

Each fragment lives at `33-ledger/<key>.md`, one per harness, with the header
`# Ledger: <harness>`, a `Baseline:` line naming the transcript and its check count, then a
table:

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |

Disposition is one of `ported`, `deleted`, `pending`. A `|` inside a label is escaped as `\|`.
A `ported` target is the full pytest node id (`companion/test_status_pages_03.py::test_x`, or
`...::test_y[id]` for a parametrised test — browser node ids carry pytest-playwright's
`[chromium]` suffix exactly as `pytest --collect-only -q` prints it). A `deleted` target is the
reason, in the form `<rubric code>: <why there is no behaviour / what covers it now>`.

## Staged-migration rule

The 9 companion harnesses migrate across 28 plans (33-04..33-31), several plans per large
harness. The legacy harness stays on disk, still detected by
`test-support/skypane_test_support.py` (one of the 9 `ORIGINAL_COMPANION_HARNESSES`, still
containing a line starting `EXPECTED_CHECK_COUNT`), until its chain's LAST plan deletes it. A
fragment's `pending` row count must always equal that shrunk legacy harness's own single
authoritative `EXPECTED_CHECK_COUNT = <remaining>` line — every check is always accounted for
as either still-legacy (`pending`) or already-ported/deleted, never both, never neither.
`33-ledger-check.py <harness> --allow-pending` enforces this; the chain's final plan drops
`--allow-pending` once the legacy file is `git rm`'d and every row is `ported` or `deleted`.

## TST-12 classification rubric

Every check migrated out of a legacy harness gets exactly ONE of these codes (full detail:
`33-MIGRATION-RULES.md` section 3):

| Code | What the legacy check does | Disposition |
|------|---------------------------|-------------|
| B | Calls a production function or makes an HTTP request, and asserts on its output | `ported`: only the plumbing changes |
| D | Regex or substring test over rendered HTML | `ported`: parsed-DOM assertion, or a plain substring test for user-visible rendered text |
| C | Opens `companion/static/style.css` (or any CSS) from disk, or slices CSS text | `ported`: fetch via `served_stylesheet(server)` and assert on `css_rules`/`declarations_for`, or a browser computed-style assertion. A check on a CSS COMMENT is `deleted` |
| J | Opens a served JS asset as text | `ported`: fetch over HTTP, `strip_js_comments_and_strings`, assert the delivery contract. A check on a JS COMMENT is `deleted` |
| S | Opens a production `.py`/`.html` source file, or introspects production code via `inspect`/`ast`/`tokenize` | Rewrite as an observable-consequence behaviour test where one exists; otherwise `deleted` |
| P | Opens `.planning/...` or a UI-SPEC file | Rewrite against a literal copied into the test when the spec pins user-visible copy; otherwise `deleted` |
| R | Self-referential: opens the test file itself (e.g. `_ASPECT_REPIN_LEDGER`) | `deleted`: plan-history bookkeeping, no behaviour |
| S/T | Root-unsafe (`os.chmod`, or a literal host path production code may `mkdir`) | `ported` with `@requires_non_root` and/or a `tmp_path` absent path |

## Status table

| Harness | Baseline (pre-migration) | Owning plans |
| --- | ---: | --- |
| `companion/test_contrast_check.py` | 49 | 33-04 |
| `companion/test_i18n.py` | 24 | 33-04 |
| `companion/test_view_pages.py` | 169 | 33-05..33-08 |
| `companion/test_config_page.py` | 276 | 33-09..33-13 |
| `companion/test_companion_app.py` | 320 | 33-14..33-18 |
| `companion/test_browser_ux_health_drawings.py` | 11 | 33-19 |
| `companion/test_browser_ux_quiet_wake.py` | 9 | 33-20 |
| `companion/test_browser_ux.py` | 75 | 33-21..33-24 |
| `companion/test_status_pages.py` | 317 | 33-25..33-31 |

Grand total: 1250 pre-migration checks across 9 harnesses (`33-BASELINE/INDEX.md`).

## Verification

```bash
server/.venv/bin/python3 .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger-check.py --allow-pending --all
```

Every plan from 33-04 onward runs this (or the single-harness form) after flipping its slice's
rows, and the chain's final plan for each harness runs it without `--allow-pending`. 33-33 runs
`33-ledger-check.py --assemble` once every fragment has zero pending rows, which requires this
same command to exit 0 with zero pending rows across all 9 harnesses first.

<!-- fragments -->

## Summary

| Harness | Baseline | Addendum | Ported | Deleted | Fragment |
| --- | ---: | ---: | ---: | ---: | --- |
| companion/test_contrast_check.py | 49 | 0 | 49 | 0 | `33-ledger/companion__test_contrast_check.md` |
| companion/test_i18n.py | 24 | 0 | 20 | 4 | `33-ledger/companion__test_i18n.md` |
| companion/test_view_pages.py | 169 | 0 | 169 | 0 | `33-ledger/companion__test_view_pages.md` |
| companion/test_config_page.py | 276 | 0 | 274 | 2 | `33-ledger/companion__test_config_page.md` |
| companion/test_companion_app.py | 320 | 0 | 319 | 1 | `33-ledger/companion__test_companion_app.md` |
| companion/test_status_pages.py | 317 | 0 | 313 | 4 | `33-ledger/companion__test_status_pages.md` |
| companion/test_browser_ux_health_drawings.py | 11 | 0 | 11 | 0 | `33-ledger/companion__test_browser_ux_health_drawings.md` |
| companion/test_browser_ux_quiet_wake.py | 9 | 0 | 9 | 0 | `33-ledger/companion__test_browser_ux_quiet_wake.md` |
| companion/test_browser_ux.py | 75 | 0 | 74 | 1 | `33-ledger/companion__test_browser_ux.md` |

Grand totals: 1250 baseline checks, 0 addendum checks, 1238 ported, 12 deleted.

## companion/test_contrast_check.py

# Ledger: companion/test_contrast_check.py

Baseline: `companion__test_contrast_check.txt`, 49 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | contrast_ratio('#E8622C', '#FBF9F6') reproduces the audit's published 3.22 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#E8622C-#FBF9F6] |
| 2 | contrast_ratio('#E8622C', '#F3EEE7') reproduces the audit's published 2.93 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#E8622C-#F3EEE7] |
| 3 | contrast_ratio('#D2521F', '#FBF9F6') reproduces the audit's published 4.02 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#D2521F-#FBF9F6] |
| 4 | contrast_ratio('#FF8A5C', '#0D0F14') reproduces the audit's published 8.25 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#FF8A5C-#0D0F14] |
| 5 | contrast_ratio('B13F16', 'FFFFFF') reproduces the audit's published 5.85 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[B13F16-FFFFFF] |
| 6 | contrast_ratio('#B13F16', '#F7F4EF') reproduces the audit's published 5.33 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#B13F16-#F7F4EF] |
| 7 | contrast_ratio('#B13F16', '#EEE8DE') reproduces the audit's published 4.80 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#B13F16-#EEE8DE] |
| 8 | contrast_ratio('#FF9B73', '#0C0F14') reproduces the audit's published 9.31 | ported | companion/test_contrast_check.py::test_contrast_ratio_reproduces_a_known_value[#FF9B73-#0C0F14] |
| 9 | light: accent text/link on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-accent text/link on canvas] |
| 10 | light: accent on primary surface / active nav meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-accent on primary surface / active nav] |
| 11 | light: accent on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-accent on secondary/sidebar surface] |
| 12 | light: primary-button label on accent fill meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-primary-button label on accent fill] |
| 13 | light: body text on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-body text on canvas] |
| 14 | light: body text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-body text on card surface] |
| 15 | dark: accent text/link on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-accent text/link on canvas] |
| 16 | dark: accent on primary surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-accent on primary surface] |
| 17 | dark: accent on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-accent on secondary/sidebar surface] |
| 18 | dark: primary-button label on accent fill meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-primary-button label on accent fill] |
| 19 | dark: body text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-body text on card surface] |
| 20 | light: muted detail text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_muted_detail_text_on_card_surface_meets_wcag_aa_normal_text[light] |
| 21 | dark: muted detail text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_muted_detail_text_on_card_surface_meets_wcag_aa_normal_text[dark] |
| 22 | light: body text on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[light-body text on secondary/sidebar surface] |
| 23 | dark: body text on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_live_token_pair_meets_wcag_aa_normal_text[dark-body text on secondary/sidebar surface] |
| 24 | light: --color-accent is perceptually separated from --color-status-ok (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[ok-light] |
| 25 | light: --color-accent is perceptually separated from --color-status-warn (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[warn-light] |
| 26 | light: --color-accent is perceptually separated from --color-status-error (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[error-light] |
| 27 | dark: --color-accent is perceptually separated from --color-status-ok (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[ok-dark] |
| 28 | dark: --color-accent is perceptually separated from --color-status-warn (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[warn-dark] |
| 29 | dark: --color-accent is perceptually separated from --color-status-error (dE76 >= 28) | ported | companion/test_contrast_check.py::test_accent_is_perceptually_separated_from_status[error-dark] |
| 30 | light: --color-status-ok and --color-status-warn are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[ok-warn-light] |
| 31 | light: --color-status-ok and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[ok-error-light] |
| 32 | light: --color-status-warn and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[warn-error-light] |
| 33 | dark: --color-status-ok and --color-status-warn are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[ok-warn-dark] |
| 34 | dark: --color-status-ok and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[ok-error-dark] |
| 35 | dark: --color-status-warn and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | ported | companion/test_contrast_check.py::test_status_colours_are_perceptually_separated_from_each_other[warn-error-dark] |
| 36 | light: --color-accent and --color-status-error are hue-separated (>= 24 deg) | ported | companion/test_contrast_check.py::test_accent_and_error_are_hue_separated[light] |
| 37 | dark: --color-accent and --color-status-error are hue-separated (>= 24 deg) | ported | companion/test_contrast_check.py::test_accent_and_error_are_hue_separated[dark] |
| 38 | light: the dE76 floor rejects the superseded error colour #DC2626 (guard against a decorative threshold) | ported | companion/test_contrast_check.py::test_perceptual_distance_floor_rejects_the_superseded_error_colour[light-#DC2626] |
| 39 | light: the hue floor rejects the superseded error colour #DC2626 (guard against a decorative threshold) | ported | companion/test_contrast_check.py::test_hue_floor_rejects_the_superseded_error_colour[light-#DC2626] |
| 40 | dark: the dE76 floor rejects the superseded error colour #F87171 (guard against a decorative threshold) | ported | companion/test_contrast_check.py::test_perceptual_distance_floor_rejects_the_superseded_error_colour[dark-#F87171] |
| 41 | dark: the hue floor rejects the superseded error colour #F87171 (guard against a decorative threshold) | ported | companion/test_contrast_check.py::test_hue_floor_rejects_the_superseded_error_colour[dark-#F87171] |
| 42 | light: --color-status-error meets WCAG AA UI-component contrast (>= 3:1) on every light surface | ported | companion/test_contrast_check.py::test_status_error_meets_ui_component_contrast_on_every_surface[light] |
| 43 | dark: --color-status-error meets WCAG AA UI-component contrast (>= 3:1) on every dark surface | ported | companion/test_contrast_check.py::test_status_error_meets_ui_component_contrast_on_every_surface[dark] |
| 44 | hue_separation() takes the shorter arc, including across the 0/360 wrap point | ported | companion/test_contrast_check.py::test_hue_separation_takes_the_shorter_arc_across_the_wrap_point |
| 45 | dark: warn-coloured headline on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | ported | companion/test_contrast_check.py::test_warn_coloured_headline_on_card_surface_meets_contrast_in_dark_mode |
| 46 | light: warn-coloured headline on card surface correctly falls below WCAG AA normal-text contrast, confirming style.css's non-colour status-warn fallback is required | ported | companion/test_contrast_check.py::test_warn_coloured_headline_on_card_surface_correctly_fails_contrast_in_light_mode |
| 47 | the status-warn-on-card pair is present in contrast_check.STATUS_WARN_ON_CARD_PAIRS for both themes | ported | companion/test_contrast_check.py::test_status_warn_on_card_pair_is_present_for_both_themes |
| 48 | light: the login field's error border (--color-status-error) meets WCAG AA UI-component contrast (>= 3:1) against BOTH colours adjacent to it — the field's own fill and the login card's surface | ported | companion/test_contrast_check.py::test_login_field_error_border_meets_contrast_against_adjacent_colours[light] |
| 49 | dark: the login field's error border (--color-status-error) meets WCAG AA UI-component contrast (>= 3:1) against BOTH colours adjacent to it — the field's own fill and the login card's surface | ported | companion/test_contrast_check.py::test_login_field_error_border_meets_contrast_against_adjacent_colours[dark] |

### Part 01 (plan 33-04)

- Rubric codes: 8× B (formula fidelity, hard-coded historical fixtures), 1× B (hue-wrap formula
  fidelity), 15× C (live text-on-surface pairs — now fetched via `served_stylesheet()` +
  `custom_properties()`/`declarations_for()` instead of hard-coded hex literals duplicating the
  stylesheet's own `:root` values), 12× C (accent-vs-status / status-vs-status perceptual and hue
  separation, same live-token treatment), 4× C (the superseded-colour discrimination guards — the
  *current* accent token is fetched live, the *historical* superseded value stays a literal since
  it names a colour that no longer exists anywhere in the stylesheet), 3× B (`STATUS_WARN_ON_CARD_PAIRS`
  is a Python constant already imported from `companion/contrast_check.py`, not source text — ported
  unchanged), 2× C (the login field's error-border pairs, same live-token treatment).
- 0 deleted. All 49 baseline checks ported.
- New module: `companion/test_contrast_check.py` (rewritten in place).

## companion/test_i18n.py

# Ledger: companion/test_i18n.py

Baseline: `companion__test_i18n.txt`, 24 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | t_lang('Home', 'fr') == 'Accueil' | ported | companion/test_i18n.py::test_t_lang_fr_translates_a_known_key |
| 2 | t_lang('Home', 'en') == 'Home' | ported | companion/test_i18n.py::test_t_lang_en_returns_the_english_source |
| 3 | t_lang() degrades a missing key to the English source unchanged | ported | companion/test_i18n.py::test_t_lang_degrades_a_missing_key_to_the_english_source_unchanged |
| 4 | t() follows prefs.set_request_prefs(lang='fr') and back | ported | companion/test_i18n.py::test_t_follows_set_request_prefs_and_back |
| 5 | prefs.set_request_prefs(lang='de') resolves to 'en' | ported | companion/test_i18n.py::test_prefs_unknown_lang_degrades_to_en |
| 6 | i18n_fr.CATALOG contains every key defined in common.py | ported | companion/test_i18n.py::test_catalog_contains_every_key_defined_in_common |
| 7 | i18n_fr.CATALOG contains every key defined in nav.py | ported | companion/test_i18n.py::test_catalog_contains_every_key_defined_in_nav |
| 8 | every CATALOG value is a str and differs from its English key | ported | companion/test_i18n.py::test_every_catalog_value_is_str_and_differs_from_its_english_key |
| 9 | companion/i18n.py and companion/prefs.py import neither companion.pages nor server | ported | companion/test_i18n.py::test_i18n_and_prefs_import_neither_pages_nor_server |
| 10 | D-08 Check 1: every scanned page-module string is a companion.i18n_fr.CATALOG key (ast-based, source-only scan) | deleted | S: asserted source text (an ast-based scan of the D-05 page-module set for i18n.t()-call/dict/constant string literals lacking a French catalogue entry); no behaviour a rendered page or an imported object can prove the same way — covered instead by the catalogue's own key-set/placeholder/non-empty self-consistency checks (test_every_catalog_value_is_non_empty, test_catalog_placeholders_match_between_key_and_value, test_t_lang_round_trips_every_catalog_key) and the real French page renders below, which are the direct behavioural proof of translation coverage |
| 11 | D-08 Check 2: every companion.i18n_fr.CATALOG key is produced by the D-05 module scan, server/notify.py's own bodies, or a documented exception | deleted | S: asserted source text (the inverse ast-based scan, proving no CATALOG key is orphaned relative to the same page-module scan); no behaviour test can observe "this string is never read from source" without reading source — covered by the same catalogue self-consistency checks and real French page renders as row 10 |
| 12 | D-08 Check 3: Home renders in French (GET /, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Home] |
| 13 | D-08 Check 3: Display renders in French (GET /display, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Display] |
| 14 | D-08 Check 3: Device renders in French (GET /device, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Device] |
| 15 | D-08 Check 3: Flights renders in French (GET /flights, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Flights] |
| 16 | D-08 Check 3: Airlines renders in French (GET /airlines, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Airlines] |
| 17 | D-08 Check 3: Health renders in French (GET /health, lang=fr) | ported | companion/test_i18n.py::test_authenticated_page_renders_in_french[Health] |
| 18 | D-08 Check 3: the login page renders in French | ported | companion/test_i18n.py::test_login_page_renders_in_french |
| 19 | D-08 Check 3: the 404 page renders in French | ported | companion/test_i18n.py::test_404_page_renders_in_french |
| 20 | D-08 Check 3: the calendar-disconnect confirmation page renders in French | ported | companion/test_i18n.py::test_calendar_disconnect_confirm_page_renders_in_french |
| 21 | D-08 Check 4 (D-09): every CATALOG value uses the typographic apostrophe, never a straight quote | ported | companion/test_i18n.py::test_every_catalog_value_uses_the_typographic_apostrophe |
| 22 | D-08 Check 4 (D-09): every CATALOG value uses U+00A0 (not a plain space) before ':'/';'/'?'/'!' | ported | companion/test_i18n.py::test_every_catalog_value_uses_nbsp_before_punctuation |
| 23 | D-08 Check 5: every literal title=/alt=/aria-label=/placeholder= attribute value scanned from the D-05 module set is a companion.i18n_fr.CATALOG key (ast-based, source-only scan; a dynamically-filled attribute is proven by Check 1's own i18n.t() call-argument tracing instead) | deleted | S: asserted source text (an ast-based scan of the D-05 module set's own string constants for a literal title=/alt=/aria-label=/placeholder= attribute value); same reasoning as rows 10/11 — covered by the real French page renders below, which parse (via a real HTTP response) the actual rendered attribute values a browser would see |
| 24 | D-08 Check 6: every genuine English fallback literal scanned from companion/static/*.js (var ALL_CAPS = "..."; ... \|\| "...") is a companion.i18n_fr.CATALOG key (regex-based, boundary stated in this file's own header comment and above _scan_all_js_files_for_fallback_literals()) | deleted | S: asserted source text (a regex scan of companion/static/*.js for a hard-coded English fallback literal); no behaviour surface exists without reading JS source text as a string — covered by the catalogue's own self-consistency checks and the real French page renders, which are the only way this project proves what a JS-rendered fallback actually displays |

### Part 01 (plan 33-04)

- Rubric codes: 5× B (t_lang/t/prefs round-trip and fallback, direct calls into `companion.i18n`/
  `companion.prefs`), 3× B (catalogue completeness/value-shape checks against the imported
  `i18n_fr.CATALOG`/sibling-module `CATALOG` dicts), 1× S (the import-boundary check — rewritten
  from a line-by-line source grep of `i18n.py`/`prefs.py` into a fresh-interpreter subprocess
  proving `companion.pages`/`server` never enter `sys.modules`), 9× B (the real French page/login/
  404/calendar-disconnect-confirm renders, now over `companion_app_server.InProcessAppServer` +
  `http_request`/`login` instead of `companion.test_companion_app._InProcessHarness`), 2× B (the
  two D-09 typographic checks, already over the imported `CATALOG` dict, no source-text read),
  4× S (the ast/regex completeness, dead-translation, attribute-literal and JS-fallback scans —
  deleted; each read a production `.py`/`.js` file as source text with no way to observe the same
  property behaviourally).
- 4 deleted (rows 10, 11, 23, 24), all reason S. 20 ported. 0 pending.
- 3 new tests beyond the 24-row baseline (not tracked as ledger rows — new coverage, not a
  1:1 port): `test_every_catalog_value_is_non_empty`, `test_catalog_placeholders_match_between_key_and_value`,
  `test_t_lang_round_trips_every_catalog_key` — together they are what replaces the deleted
  ast-based completeness/dead-translation scans' catalogue-shape guarantee.
- New module: `companion/test_i18n.py` (rewritten in place). No longer imports
  `companion.test_companion_app` — its render checks use a module-scoped
  `companion_app_server.InProcessAppServer` fixture built locally in this file.

## companion/test_view_pages.py

# Ledger: companion/test_view_pages.py

Baseline: `companion__test_view_pages.txt`, 169 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | an empty database renders the flight-history empty-state copy and no <table | ported | companion/test_view_pages_01.py::test_empty_database_renders_empty_state_no_table |
| 2 | three seeded runway events render one row each, newest first | ported | companion/test_view_pages_01.py::test_three_events_render_newest_first |
| 3 | a known aircraft-type designator renders its friendly label (case-insensitive) | ported | companion/test_view_pages_01.py::test_known_aircraft_type_friendly_label |
| 4 | an aircraft type absent from the display-label table renders the raw designator, not an empty cell | ported | companion/test_view_pages_01.py::test_unknown_aircraft_type_raw_designator |
| 5 | a row with no airline and no route renders the same fallback wording server.plane.render.py uses (read from the module) | ported | companion/test_view_pages_01.py::test_no_airline_no_route_matches_render_fallback |
| 6 | timestamp, callsign and hex columns carry monospace CSS classes | ported | companion/test_view_pages_01.py::test_mono_columns_present |
| 7 | a callsign containing angle brackets renders escaped | ported | companion/test_view_pages_01.py::test_hostile_callsign_escaped |
| 8 | a state directory that cannot hold a database renders the health-unavailable copy without raising | ported | companion/test_view_pages_01.py::test_unreadable_db_degrades_without_raising |
| 9 | companion/pages/history_page.py never imports the stdlib html module directly | ported | companion/test_view_pages_01.py::test_history_page_never_imports_html_module_directly |
| 10 | companion/pages/history_page.py never redefines _TYPE_DISPLAY_LABELS locally | ported | companion/test_view_pages_01.py::test_history_page_never_redefines_type_display_labels_locally |
| 11 | History opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_view_pages_01.py::test_history_opens_with_shared_page_header |
| 12 | History's flight table gains the .data-table-wrap horizontal-scroll wrapper Airlines/Health already have, without disturbing the Corroboration status dot | ported | companion/test_view_pages_01.py::test_history_table_wrapped_for_horizontal_scroll_dot_survives |
| 13 | History renders exactly the 5 data headers in history_page._HEADERS plus a sixth, visually-hidden 'Details' toggle-column header, all in order, with no standalone Hex/Airline/Runway/Type/Callsign/Timestamp column (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_six_columns_named_and_ordered |
| 14 | the runway value the dropped desktop Runway column used to show survives in the <tr title="..."> attribute and, unchanged, in the mobile card's More details (A-36/D-19) | ported | companion/test_view_pages_01.py::test_runway_survives_in_row_title_and_mobile_details |
| 15 | the .data-table-wrap scroller is focusable (tabindex="0") and carries a non-empty aria-label naming what it scrolls (A-36/D-19) | ported | companion/test_view_pages_01.py::test_scroller_focusable_and_named |
| 16 | the desktop When cell shows a local clock primary line plus a STACKED relative-age secondary line, with no title attribute carrying the full ISO string any more (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_desktop_when_cell_clock_primary_relative_age_secondary |
| 17 | the Flight cell's callsign and its airline/aircraft-type secondary line both appear inside the same <td>, and the hex value is not visible in the desktop table (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_merged_flight_cell_carries_callsign_airline_and_type |
| 18 | the merged Callsign/Hex and Type/Airline cells stay on one line - no <br>, no block-level child | ported | companion/test_view_pages_01.py::test_merged_cells_stay_one_line |
| 19 | hostile values in both merged cells (Callsign/Hex, Type/Airline) render escaped | ported | companion/test_view_pages_01.py::test_merged_cell_hostile_values_escaped |
| 20 | history_page's CELL_PRIMARY_CLASS/CELL_SECONDARY_CLASS/CELL_SEPARATOR_CLASS all appear in style.css and in the rendered page | ported | companion/test_view_pages_01.py::test_merged_cell_classes_agree_with_stylesheet |
| 21 | History's Timestamp column/mobile primary line read through layout.concise_timestamp_html(), format_event_row() degrades gracefully with one argument or a missing timestamp, and render() falls back when ctx carries no 'now' key | ported | companion/test_view_pages_01.py::test_timestamp_column_absolute_and_relative |
| 22 | History's Timestamp cells carry layout.concise_timestamp_html()'s new <time data-relative> element through data_table()'s raw_columns — as real markup, never double-escaped — with its text and its instant both intact (23-03, D14/CFG-34) | ported | companion/test_view_pages_01.py::test_history_timestamps_carry_a_relative_time_element |
| 23 | history_page._CORROBORATION_LABELS agrees with health_page._CORROBORATION_ROWS on status key-by-key and on visible label for True/False; History's shortened 'None' label is the documented short form and its _CORROBORATION_TITLES tooltip equals Health's own full label exactly; the single-source 'None' state is pinned by name on each side (History 'ok', Health the neutral 'off'), is never a failure in either table, and carries a visible label distinct from 'Both agree' (quick task 260902-w4t UIR-04, retargeted by 22-12-PLAN.md Task 1's X8) | ported | companion/test_view_pages_01.py::test_corroboration_copy_agrees_with_health_page |
| 24 | layout.status_dot()'s 2-arg output is unchanged, an explicit title=None is byte-identical to omitting it, and a truthy title renders as an escaped title attribute (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_status_dot_title_backward_compatible_and_escaped |
| 25 | layout.status_dot()'s visually_hide_label keyword defaults to False with a byte-identical return value, and True adds the visually-hidden class to the label span while leaving its text/title unchanged (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_status_dot_visually_hide_label_defaults_false_byte_identical |
| 26 | a 'None' (single-source) row's Corroboration cell shows the short visible label with the long form only in a title attribute, in both the desktop and mobile renderings (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_corroboration_none_row_shows_short_label_with_tooltip |
| 27 | the desktop Corroboration cell renders the dot only, with the visible word hidden via visually-hidden (not deleted); the mobile card's own Corroboration <dd> still shows the word (21-03-PLAN.md Task 1, D-15/D-16) | ported | companion/test_view_pages_01.py::test_desktop_corroboration_cell_dot_only_no_visible_word |
| 28 | the desktop When and Flight cells each carry exactly one cell-primary span and one cell-secondary span (21-03-PLAN.md Task 1, D-15) | ported | companion/test_view_pages_01.py::test_when_and_flight_cells_each_carry_one_primary_one_secondary |
| 29 | .data-table-wrap declares both background-attachment values (local covers, scroll shadows) and style.css introduces no pointer-events-blocking overlay (quick task 260902-w4t, UIR-04) | ported | companion/test_view_pages_01.py::test_data_table_wrap_scroll_edge_affordance_css |
| 30 | History's filter bar carries exactly one data-filter-input/-count/-clear/-empty marker each | ported | companion/test_view_pages_01.py::test_filter_bar_markers_present_once |
| 31 | History's search filter input carries autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) | ported | companion/test_view_pages_01.py::test_filter_input_carries_safari_autofill_suppression_attributes |
| 32 | History's filter bar carries data-filter-count-template="%d of %d shown" under the default language and the French "%d sur %d affichés" under lang='fr' (D-06) | ported | companion/test_view_pages_01.py::test_filter_count_template_attribute_english_and_french |
| 33 | History's filter count and Clear control render as siblings inside one .filter-bar__meta group whose page-agnostic rule declares flex/centre/nowrap/auto-left-margin, with no page-scoped fork of the converged [data-filter-clear] rule anywhere (B11, 22-09-PLAN.md Task 3 — a regression of Phase 18's A-18) | ported | companion/test_view_pages_01.py::test_filter_bar_count_and_clear_wrap_as_one_group |
| 34 | the Clear control's shared [data-filter-clear] contract holds: History renders the attribute, style.css styles it by attribute, and no class-keyed rule competes | ported | companion/test_view_pages_01.py::test_clear_control_shared_attribute_contract |
| 35 | a real flight's data-filter-text attribute (lowercased escaped callsign+hex) appears on both the desktop <tr> and the mobile <li> | ported | companion/test_view_pages_01.py::test_filter_text_attribute_on_both_representations |
| 36 | the desktop Flight cell contains zero copy buttons (21-03-PLAN.md Task 1, D-15 - they move into the Task 2 detail row instead) | ported | companion/test_view_pages_01.py::test_desktop_flight_cell_carries_no_copy_buttons |
| 37 | each summary row gets exactly one sibling detail row, matched by aria-controls/id, with no hidden attribute and no inline style (the no-JS floor), and every row-toggle starts aria-expanded="false" (21-03-PLAN.md Task 2, D-15/R-12) | ported | companion/test_view_pages_01.py::test_detail_row_pairs_with_summary_row_by_aria_controls_and_id |
| 38 | the rendered Flights table carries zero visible More/Plus/Less/Moins button labels and exactly one icon-only toggle button per row, each carrying a translated aria-label that swaps with its state and names the picture reachable inside (22-09-PLAN.md Task 1, X5) | ported | companion/test_view_pages_02.py::test_row_toggle_is_icon_only_and_named_in_both_languages |
| 39 | in the RENDERED Flights page no <tr> carries aria-expanded and every aria-expanded occurrence sits on a <button> (22-09-PLAN.md Task 1, X5 — the state never moves onto the row element) | ported | companion/test_view_pages_02.py::test_aria_expanded_sits_only_on_buttons_never_on_a_tr |
| 40 | style.css's new .row-toggle rule block reuses .copy-btn's icon-only pattern verbatim (same 22x22 box, same radius, the same ::before inset synthesizing 44x44, the same 14px glyph) and introduces no new size literal; the pointer cursor is keyed only on the class flight-rows.js adds at load (22-09-PLAN.md Task 1, X5) | ported | companion/test_view_pages_02.py::test_row_toggle_css_reuses_the_copy_btn_icon_only_pattern |
| 41 | companion/static/flight-rows.js reads every attribute name history_page.py renders, swaps aria-label instead of a visible label, returns early for an interactive click target (T-22-32) and uses no markup-writing sink; the server still renders every detail row visible with no collapsing class, no hidden and no inline style (22-09-PLAN.md Task 1, X5/D-09) | ported | companion/test_view_pages_02.py::test_flight_rows_js_swaps_the_name_and_delegates_the_row_click |
| 42 | the hex, the raw ISO timestamp and the runway render inside the detail row and NOT in the summary row's own slice (21-03-PLAN.md Task 2, D-15) | ported | companion/test_view_pages_02.py::test_detail_row_carries_hex_iso_runway_not_in_summary_row |
| 43 | a rendered Flights page contains no inline <script> and no on*= handler attribute (21-03-PLAN.md Task 2, D-15/R-12) | ported | companion/test_view_pages_02.py::test_flights_render_has_no_inline_script_or_handler_attribute |
| 44 | style.css's table.data-table--flights padding rule uses var(--space-sm) on both axes, never a literal px value (21-03-PLAN.md Task 3, D-15) | ported | companion/test_view_pages_02.py::test_flights_table_padding_rule_uses_space_sm_token_both_axes |
| 45 | the rendered Flights table's <thead> carries exactly six <th> cells in both en and fr (21-03-PLAN.md Task 3, D-15) | ported | companion/test_view_pages_02.py::test_flights_thead_carries_exactly_six_cells_in_both_languages |
| 46 | the mobile card's details region contains exactly 3 copy buttons (callsign, hex, full timestamp), each immediately followed by its data-copy-feedback sibling | ported | companion/test_view_pages_02.py::test_mobile_details_three_copy_buttons |
| 47 | a Flights render's copy buttons carry data-copied-text="Copied" under the default language and data-copied-text="Copié" under lang='fr' (D-06) | ported | companion/test_view_pages_02.py::test_copy_button_carries_data_copied_text_english_and_french |
| 48 | the desktop copy-button reveal rule lives inside the shared 960px block, is scoped by [data-copy-value] (never the bare .copy-btn class), reveals via opacity + pointer-events (never visibility: hidden or display: none) on both tr:hover and tr:focus-within (quick task 260903-peo, UIR-17) | ported | companion/test_view_pages_02.py::test_desktop_copy_reveal_stylesheet_contract |
| 49 | a real rendered desktop History summary row carries zero copy buttons (21-03-PLAN.md Task 1, D-15) and no picture control at all (22-09-PLAN.md Task 2, X5 — it moved into the detail row), and that control still never carries data-copy-value — the discriminator the desktop reveal rule depends on (quick task 260903-peo, UIR-17) | ported | companion/test_view_pages_02.py::test_desktop_row_copy_buttons_and_eye_button_discriminator |
| 50 | with two differently-named rows, at least two distinct copy-button aria-label values render on the page — the '50 identical names' defect closed (A-37/D-20) | ported | companion/test_view_pages_02.py::test_copy_buttons_no_longer_share_one_aria_label |
| 51 | each row's mobile-card callsign copy button carries an aria-label naming that row's own callsign, not a shared/generic name (A-37/D-20, retargeted off the desktop row by 21-03-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_each_copy_button_aria_label_names_its_own_row |
| 52 | copy-button.js propagates fallbackCopy()'s real document.execCommand(...) result instead of discarding it, and stays ES5-safe/sink-free (A-37/D-20) | ported | companion/test_view_pages_02.py::test_copy_button_script_propagates_execcommand_success |
| 53 | every rendered copy button carries exactly one copy-btn__icon span and one empty copy-btn__label span, and its data-copy-feedback sibling still immediately follows the button (D-20) | ported | companion/test_view_pages_02.py::test_copy_button_markup_carries_icon_and_label_spans |
| 54 | copy-button.js references the copy-btn__label/copy-btn--copied class names and the 1.5s (1500ms) feedback window (D-20) | ported | companion/test_view_pages_02.py::test_copy_button_script_references_label_class_and_1500ms |
| 55 | style.css styles both copy-btn__label and copy-btn--copied (D-20) | ported | companion/test_view_pages_02.py::test_style_css_styles_both_copy_feedback_classes |
| 56 | confirmed_state/tracked_runway presentation labels (Task 1's format_event_row() fixture) also appear correctly through the full render() output | ported | companion/test_view_pages_02.py::test_presentation_labels_in_full_render |
| 57 | a French Flights render translates the tracked_runway cell's registry label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), with no English label leaking in (Polish fix 5, D-05) | ported | companion/test_view_pages_02.py::test_french_render_translates_the_runway_cell_label |
| 58 | with 3 gallery entries and one seeded flight row, the rendered page carries zero <h2, zero page-section, zero gallery-grid/gallery-tile elements and zero occurrences of the retired heading/empty-state text, WHILE the per-row View-panel mechanism (a trigger, exactly one lightbox dialog) and History's own card disclosures survive in the same render | ported | companion/test_view_pages_02.py::test_history_render_gallery_section_absent_with_content |
| 59 | with gallery_entries=[], the same absences hold (the section is gone, not merely emptied) and, as before, zero View-panel triggers and zero lightbox dialogs render | ported | companion/test_view_pages_02.py::test_history_render_gallery_section_absent_when_empty |
| 60 | the rendered picture control is a LABELLED text control carrying the translated "View picture" text and no aria-label, with "View panel near this time" surviving as its title, on both the desktop detail row and the mobile card (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_02.py::test_view_panel_trigger_is_a_labelled_control_with_the_long_form_as_title |
| 61 | the colour caveat sentence appears exactly once in the rendered page, and that single occurrence lies inside the lightbox__note element (the caveat's new, and only, home after the render-gallery section's removal) | ported | companion/test_view_pages_02.py::test_colour_caveat_rehomed_into_lightbox_note |
| 62 | with a real panel.bin on disk and gallery entries seeded, the rendered output contains zero occurrences of /preview.png, preview-frame, preview-image, and the old no-panel caption sentence - a present panel file changes nothing about the markup any more (this check's real subject is quick task 260903-c4o's /preview.png route retirement, not the render-gallery section retired by this task; kept in place rather than dropped) | ported | companion/test_view_pages_02.py::test_render_gallery_no_preview_apparatus_even_with_panel_file |
| 63 | the rendered History page carries no data-stale-banner and no Refresh link — D-18's retired apparatus stays retired — while carrying exactly one data-loaded-at marker, built by layout.freshness_line_html(), because D7/CFG-37 puts this page on the refresh loop and freshness.js returns at its first guard without one (retargeted in place by 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_now_showing_no_preview_freshness_apparatus |
| 64 | history_page._gallery_name_to_iso() reverses a well-formed gallery filename and returns None (never raising) on a missing 'T' separator or a malformed time+offset portion | ported | companion/test_view_pages_02.py::test_gallery_name_to_iso_fixtures |
| 65 | a rendered History page's picture control carries no icon glyph at all and reuses .calendar-disconnect-btn's small-grey-secondary treatment — that component's second consumer, with no .btn family started (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_02.py::test_view_panel_trigger_reuses_the_small_grey_secondary_treatment |
| 66 | nearest_gallery_entry() matches the latest at-or-before entry (inclusive boundary), skips an entry with an unrecoverable filename timestamp, and returns None for an empty entry list, an empty/unparseable row_ts, or when every recoverable entry is strictly after row_ts | ported | companion/test_view_pages_02.py::test_nearest_gallery_entry_behaviour |
| 67 | for three gallery entries and three interleaved rows, each row's desktop and mobile View-panel trigger carries byte-identical, correctly-targeted data-view-panel-src/-caption attributes matching its own nearest gallery entry, and exactly one lightbox dialog is emitted | ported | companion/test_view_pages_02.py::test_view_panel_triggers_per_row_full_render |
| 68 | with an empty gallery entry list, History renders zero View-panel triggers and zero lightbox dialog elements, never a disabled or broken control | ported | companion/test_view_pages_02.py::test_view_panel_empty_gallery_zero_triggers_zero_dialog |
| 69 | the shared, Airlines-only and render-only lightbox token tuples each appear (or, for Airlines-only, are absent from History) exactly where their own classification says they must, across companion/static/panel-lookup.js and both pages' rendered markup | ported | companion/test_view_pages_02.py::test_lightbox_dom_contract_three_file_guard |
| 70 | every airlines_page._VIEW_PANEL_*_ATTR constant's value is classified in exactly one of the three lightbox token tuples, discovered by reflection over dir(airlines_page) rather than a hand-copied name list | ported | companion/test_view_pages_02.py::test_view_panel_attr_constants_all_classified |
| 71 | panel-lookup.js never sets image.src to the empty string anywhere in its comment-stripped source - D-02/RESEARCH.md Pitfall 1's single riskiest line, the exact cross-browser spurious-request bug this phase's imageless-open branch exists to avoid | ported | companion/test_view_pages_02.py::test_panel_lookup_never_sets_image_src_to_empty_string |
| 72 | panel-lookup.js's image.removeAttribute("src") call is nested inside a conditional branch (the src-absent case), never written unconditionally at module scope | ported | companion/test_view_pages_02.py::test_panel_lookup_remove_attribute_src_is_conditional |
| 73 | panel-lookup.js's shared populate-and-open function (openFromTrigger) is defined exactly once and referenced from at least two call sites - the click listener and the load-time auto-open (RESEARCH.md Pitfall 2's mandatory factoring) | ported | companion/test_view_pages_02.py::test_panel_lookup_shared_populate_function_two_call_sites |
| 74 | panel-lookup.js reads location.search exactly once in its own code, at script init, outside openFromTrigger (the one function reachable from a click) and after the click listener is already wired | ported | companion/test_view_pages_02.py::test_panel_lookup_location_search_read_once_outside_click_only_function |
| 75 | every one of the eleven new data-view-panel-* attribute name literals 14-02 added to the vocabulary appears at least once in panel-lookup.js's own source | ported | companion/test_view_pages_02.py::test_panel_lookup_eleven_new_attrs_present_in_source |
| 76 | the mode-governed elements' (resolveNameForm/resolveUploadZone/replaceForm) hidden assignments all occur, textually, before openFromTrigger's own dialog.showModal() call (RESEARCH.md Pitfall 3 - showModal()'s one-time autofocus placement must see the final, already-toggled subtree) | ported | companion/test_view_pages_02.py::test_panel_lookup_mode_hidden_toggles_before_showmodal |
| 77 | panel-lookup.js's evt.preventDefault() appears exactly once, inside the click listener, positioned after the trigger-null-check and before the showModal()-reaching openFromTrigger() call (D-12's <a> interception) | ported | companion/test_view_pages_02.py::test_panel_lookup_prevent_default_once_correctly_positioned |
| 78 | panel-lookup.js still contains exactly one document.getElementById("panel-lookup-dialog") and exactly one document.addEventListener("click", ...) - this plan extended the existing single mechanism rather than adding a second one (D-03's own rejected alternative) | ported | companion/test_view_pages_02.py::test_panel_lookup_single_dialog_lookup_single_click_listener |
| 79 | panel-lookup.js's contextCallsign.textContent is assigned exactly once, gated on the same `count` that gates resolveContext.hidden, so an ordinary illustration's own caption can never be printed under the 'Example callsign' label (quick task 260921-n2n Task 2) | ported | companion/test_view_pages_02.py::test_panel_lookup_context_callsign_write_gated_on_count |
| 80 | airlines_page's LIGHTBOX_DIALOG_ID and its three _VIEW_PANEL_*_ATTR constants each equal history_page's own values (the duplicated-not-imported shared-lightbox contract) | ported | companion/test_view_pages_02.py::test_airlines_lightbox_constants_match_history |
| 81 | a real, seeded history_page.render() call (real gallery entry, real runway event) renders its lightbox dialog exactly once, and carries zero occurrences of airlines_page's replace-form class, replace-action attribute, <form>, file input, enctype, or the framed zone's three class constants (quick task 260903-df3) anywhere (quick task 260903-btu) | ported | companion/test_view_pages_02.py::test_history_lightbox_carries_zero_replace_markup |
| 82 | airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR and airlines_page.LIGHTBOX_REPLACE_FORM_CLASS each appear in companion/static/panel-lookup.js's source and in a real airlines_page.render({}) call, the exact '.lightbox__replace' selector (not merely a substring, which the newer '.lightbox__replace-zone' selector could otherwise satisfy) appears in companion/static/style.css standalone or as the head of the phase-14 three-way group, and neither token appears in a real, seeded history_page.render() call (quick task 260903-btu; these two constants have no history_page counterpart by design and must never join _airlines_lightbox_constants_match_history()'s pairs tuple; pattern retargeted in place by phase 14 plan 14-03 Task 2) | ported | companion/test_view_pages_02.py::test_replace_lightbox_names_appear_in_three_files_never_in_history |
| 83 | airlines_page.render({}) with a literal empty dict still succeeds and its output still contains the gallery grid (quick task 260902-v26's ctx.get("state_dir") tolerance) | ported | companion/test_view_pages_02.py::test_airlines_render_empty_ctx_still_contains_gallery_grid |
| 84 | a render with an eligible gap emits the "Unidentified airlines" strip with its exact heading and sentence after the filter bar and the gallery grid, and the curated artwork grid holds no gap card (D-21/A-38, 19-08-PLAN.md Task 1, order superseded by CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder |
| 85 | a render with no eligible gaps emits no "Unidentified airlines" strip and no empty section (D-21, 19-08-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_airlines_gap_strip_absent_with_no_gaps |
| 86 | on a render with both an eligible gap and at least one curated gallery card, the page's own sections chain title < filter bar < gallery grid < "Unidentified airlines" strip < the lightbox dialog, each literal occurring exactly once (CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox |
| 87 | the reorder does not touch render()'s own no-chrome gate: a render with gap cards but no curated pairs still shows the filter bar, and a render with neither shows no filter bar at all (CFG-82, 29-02-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_no_chrome_gate_survives_the_reorder |
| 88 | the resolve panel's back link renders exactly once, named "← Back to Airlines" and targeting airlines_page.AIRLINES_ROUTE, superseding the Phase 13 Copy Deck's "Back to Health" (D-21, A-38, 19-08-PLAN.md Task 2) | ported | companion/test_view_pages_02.py::test_airlines_resolve_panel_back_link_names_and_targets_airlines |
| 89 | a default airlines_page.render({}) call (no query parameter involved) carries exactly one each of the dialog's replace form, delete form and upload zone — the page-wide editing mode that used to gate replace/delete behind an exact ?edit=1 is deleted (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_default_render_always_has_the_dialogs_forms |
| 90 | a render of a Step-B entry (name saved, no artwork yet) contains exactly two upload zones and two manual-delete forms (the no-JS fallback panel's own copy plus the lightbox's, both unconditional per CFG-81), and exactly one replace form (the dialog's own copy — this no-JS fallback panel has none of its own) (D-19, 21-06-PLAN.md Task 1; retargeted by 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_default_render_step_b_upload_zone_unconditional |
| 91 | a default airlines_page.render({}) call still contains exactly one lightbox__resolve-name form - naming a prefix stays the everyday action (D-22, 19-08-PLAN.md Task 3) | ported | companion/test_view_pages_02.py::test_airlines_default_render_keeps_exactly_one_resolve_name_form |
| 92 | the deleted page-wide editing toggle (its class literal) and the deleted ?edit= query parameter (its literal form) never render again, in either language, whether the query string is absent or carries an arbitrary unrelated value (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_02.py::test_airlines_no_page_wide_editing_mode_survives |
| 93 | a French render of Airlines shows the French page title, filter label and lightbox aria-label, while a real airline name ('Air France') stays untranslated data (D-05, 20-10-PLAN.md Task 2; the toggle-text needle retired by 29-01-PLAN.md/CFG-81) | ported | companion/test_view_pages_02.py::test_airlines_french_render_translates_headings_not_data |
| 94 | a fully-seeded Airlines render under lang='fr' shows the French gap-strip heading/sentence and resolve-panel copy with no English leaking in, the seeded example callsign stays untranslated data, and the identical seeded render under the default language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 2; the toggle-label needle retired by 29-01-PLAN.md/CFG-81) | ported | companion/test_view_pages_02.py::test_airlines_full_seeded_render_french_end_to_end |
| 95 | every key in companion/i18n_fr/airlines.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up (20-10-PLAN.md Task 2) | ported | companion/test_view_pages_02.py::test_airlines_catalog_keys_all_present_in_merged_catalog |
| 96 | the resolve dialog's data-view-panel-first-seen/-last-seen carry FORMATTED Europe/Paris text byte-identical to the no-JS path's own rendered <dd> text for the same row (15:49 UTC reading 17:49), and neither render carries a single ISO-8601 timestamp anywhere (B5/D-05, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_02.py::test_resolve_dialog_seen_attributes_carry_formatted_paris_local_text |
| 97 | companion/static/panel-lookup.js contains no date-parsing or date-formatting API at all (new Date/Date.now/toISOString/toLocale*/getHours/getMinutes/getTime/Intl.DateTimeFormat) and assigns the first-seen/last-seen attribute values straight to textContent — the property that keeps D-05's Paris-local rule enforceable server-side (B5, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_panel_lookup_js_does_no_date_math_of_any_kind |
| 98 | the resolve dialog's Save and Close share ONE .lightbox__actions row — quiet Close first, primary Save second and re-attached to its form by the native form= attribute — while the no-JS fallback keeps its own submit inside its own form, and the row's rule declares flex/centre/space-between with no shared height (C4) and no .btn-- family (B5, 22-11-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_resolve_dialog_save_and_close_share_one_action_row |
| 99 | a normal Airlines render carries no Editing badge and no per-card Replace control anywhere (both deleted outright, CFG-81) — while every airline-card__zoom trigger still carries the SAME full data-view-panel-* vocabulary, its size derived from the module's own _VIEW_PANEL_*_ATTR constants rather than a hardcoded number (29-01-PLAN.md) | ported | companion/test_view_pages_03.py::test_airlines_cards_carry_no_badge_or_per_card_control_but_full_vocabulary |
| 100 | the manual-resolution count renders as a real filter control INSIDE the Airlines filter bar wearing .airline-card__chip's label voice — the 12px bare link and its copied [data-filter-clear] property list are retired, leaving only a hover-additive rule — and one entry reads '1 manual resolution' (FR '1 resolution manuelle') while two read '2 manual resolutions' (X7 + D-06/B16, 22-11-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_airlines_manual_count_is_a_filter_control_in_the_filter_bar |
| 101 | below 960px .illustration-grid takes a FIXED repeat(2, minmax(0, 1fr)) template — two cards per row with a zero column minimum — while the desktop auto-fill idiom above 960px is left untouched (X7, 22-11-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_airlines_grid_is_two_fixed_columns_below_960px |
| 102 | a formatted row with a resolved airline produces a Flight cell (desktop) and a phone card (mobile) carrying neither a one-hop resolve link nor the retired two-hop Health route (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_unresolved_link_absent_for_resolved_airline |
| 103 | a formatted row whose airline is unresolved produces exactly one ONE-HOP resolve anchor in the desktop Flight cell and exactly one on the phone card, both naming the prefix derived from that row's own callsign (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_unresolved_link_present_once_each_for_unresolved_airline |
| 104 | a row whose route is unresolved but whose airline IS resolved produces no unresolved-airline link - the link is keyed on the airline label, not on the route label | ported | companion/test_view_pages_03.py::test_unresolved_link_keyed_on_airline_not_route |
| 105 | a no-airline row renders AIRLINE_FALLBACK_TEXT and ROUTE_FALLBACK_TEXT as two distinct strings in two distinct columns, and the unresolved-link's spacing class is styled in style.css and present in the rendered anchor (quick task 260902-w4t, UIR-05) | ported | companion/test_view_pages_03.py::test_airline_fallback_distinct_from_route_fallback |
| 106 | a callsign-less row's desktop Flight cell is empty with zero copy buttons and no visible hex (21-03-PLAN.md Task 1, D-15); the mobile card still promotes the hex to its primary slot with a no-copy-button 'no callsign' note (D-16); a callsign+hex row is unaffected; a row with neither renders without raising (quick task 260902-w4t, UIR-06) | ported | companion/test_view_pages_03.py::test_hex_only_row_promotes_hex_to_primary |
| 107 | history_page.RESOLVE_LINK_HREF_TEMPLATE is built from airlines_page.AIRLINES_ROUTE and RESOLVE_QUERY_PARAM (never a re-typed literal), the retired two-hop Health constant is gone, and resolve_prefix_for_callsign() derives a prefix only for a callsign the registry writer's own shape gate would accept (22-09-PLAN.md Task 2, X5/T-22-30) | ported | companion/test_view_pages_03.py::test_resolve_link_template_matches_the_airlines_resolve_view |
| 108 | the rendered Flights table carries exactly one day-separator row per EUROPE/PARIS calendar day present in the rows — Today / Yesterday / an absolute date, translated in both languages — and a row whose UTC day differs from its Paris day is grouped by the Paris one (22-09-PLAN.md Task 2, X5/D-05) | ported | companion/test_view_pages_03.py::test_day_separators_group_rows_by_europe_paris_calendar_day |
| 109 | the day separator's absolute label is the day portion of layout.local_clock_text()'s own cross-day output in both languages, history_page.py contains zero strftime calls, paris_day() degrades to None rather than raising, and the separator's CSS rule declares no positioning (22-09-PLAN.md Task 2, X5/D-05/T4) | ported | companion/test_view_pages_03.py::test_day_label_is_the_paris_day_formatters_own_output_and_never_sticky |
| 110 | every rendered Flights row carries a non-empty, unique event identity in BOTH representations, the table and the card list name the same event set, and a newer detection arriving at the top leaves every existing row's identity unchanged — the property the row's position does not have and the whole basis of the new-row highlight (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_every_flights_row_carries_a_stable_event_identity |
| 111 | the rendered Flights page carries exactly one data-loaded-at marker and a witness for every one of its REFRESH_SWAP_SELECTORS_BY_PAGE regions, and no region names the filter input list-filter.js captured at load (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_view_pages_03.py::test_flights_declares_its_refresh_regions_and_never_the_filter_input |
| 112 | the Flights detail row animates open through a grid reveal wrapper inside its own <td> (grid-template-rows 0fr, var(--motion-fast), an @starting-style entry, scoped to the class flight-rows.js adds to <html>), neither interpolate-size nor calc-size() appears, and the collapsed end state is still display: none — the one state that takes a closed row out of both the tab order and the accessibility tree (D3/CFG-32, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_detail_row_height_animates_and_a_closed_row_is_unreachable |
| 113 | the row-toggle chevron transitions TRANSFORM on var(--motion-fast) and adds no per-rule reduced-motion block — the global override already covers a plain transform for free, and the stylesheet's live prefers-reduced-motion count is unmoved at 3 (D3/CFG-32, references/control-density.md:78, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_chevron_turns_and_carries_no_reduced_motion_block_of_its_own |
| 114 | the phone card's own face IS the native disclosure's <summary> — the primary line, the secondary line, the time and 22-09's thumbnail and airline name all inside it, so a tap anywhere opens the card with no script at all — while the one-hop resolve link stays on the card and OUT of the summary, and the disclosure body still holds exactly the three copy buttons (D7/CFG-37, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_phone_cards_own_face_is_its_disclosure_summary |
| 115 | the phone summary card's .history-card__primary line is a two-track CSS grid (minmax(0, 1fr) then auto, no justify-content) with a non-wrapping .history-card__time (white-space: nowrap, no margin-left: auto), and all three primary_value_html branches — callsign, hex-plus-note, empty — produce a child set the grid can place with no third, unclassified top-level child (2026-09-17 audit P1, 29-03-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_history_card_primary_grid_pins_the_timestamp_track |
| 116 | two renders of a 36-row fixture at the SAME ?limit= value produce byte-identical pagination state (standing in for freshness.js's own re-fetch of the unchanged window.location.href), '.flights-more' is a declared swap region, and freshness.js carries exactly one fetch( call targeting window.location.href verbatim — the structural half of the refresh-survival property this harness can prove without a browser (29-RESEARCH.md, 29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_reveal_state_reproduces_from_the_url_alone |
| 117 | the Show-more anchor renders with an href and no onclick/data- attribute and is never a <button> or <form>, and zero companion/static/*.js files mention its 'flights-more' class (scanned-file floor >= 17, printed on failure) — a no-JS control proof, not merely a render (29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_reveal_control_is_a_plain_anchor_no_script_mentions |
| 118 | the Show-more anchor's rendered tag agrees with a REAL CSS selector match (rightmost compound's tag qualifier, if any) — not merely a class-string substring shared between the markup and style.css (CR-01, 29-REVIEW.md) | ported | companion/test_view_pages_03.py::test_flights_reveal_anchor_has_a_matching_css_selector |
| 119 | history_page.flights_limit() clamps all 19 hostile inputs into [15, 50] without raising, render() calls it exactly once and never reads ctx['flights_limit'] directly, companion/app.py performs no arithmetic or comparison on the raw threaded value, and HISTORY_ROW_LIMIT is the literal ceiling flights_limit()'s own source uses (T-29-03-01, T-29-03-02, 29-03-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_render_defers_entirely_to_flights_limit_for_hostile_ctx_values |
| 120 | the filter count animates its ELEMENT and never its number: the template-driven text production is untouched, the text is written before the class is added, the class is removed and re-added across a forced reflow so a second change restarts it, and it fires only when the rendered value actually differs (D7/CFG-37, 23-08-PLAN.md Task 2) | ported | companion/test_view_pages_03.py::test_the_count_animates_without_its_text_production_moving |
| 121 | the phone card's "ORY → JFK Departing" line carries the module's EXISTING cell-inline-sep middle dot between the route and the state, reused rather than reinvented (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_phone_card_route_and_state_carry_the_existing_middle_dot |
| 122 | the raw ISO timestamp appears only inside a data-copy-value attribute, while the visible full timestamp is the Europe/Paris local clock in the .time-value role on both the desktop detail row and the phone card (22-09-PLAN.md Task 2, X5/D-05/C5) | ported | companion/test_view_pages_03.py::test_raw_iso_survives_only_behind_the_copy_control |
| 123 | a phone card carries the airline name and, when real artwork exists for it, the Airlines gallery's own served frame as a thumbnail joining the shared white-backing/hairline/radius rule in a contain-fitted 56px box — and no <img> at all when no artwork file exists (22-09-PLAN.md Task 2, X5) | ported | companion/test_view_pages_03.py::test_phone_cards_carry_the_airline_name_and_artwork_thumbnail |
| 124 | the rendered History page contains no prefix-registry table and no element carrying the registry table's own headers | ported | companion/test_view_pages_03.py::test_no_prefix_registry_duplicated_on_history |
| 125 | a French render of Flights shows the French page title, column headers and filter label, while a seeded callsign stays untranslated data (D-05, 20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_french_render_translates_headings_not_data |
| 126 | a fully-seeded Flights render under lang='fr' shows every new French string (column headers, direction words, the unresolved-airline fallback, the no-callsign note, the disclosure summary and the filter's Clear button) with no English leaking in, the seeded callsign stays untranslated data, and the identical seeded render under the default language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_full_seeded_render_french_end_to_end |
| 127 | every key in companion/i18n_fr/flights.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up (20-10-PLAN.md Task 3) | ported | companion/test_view_pages_03.py::test_flights_catalog_keys_all_present_in_merged_catalog |
| 128 | home_page.render() with seeded flights, a battery reading and a gallery entry renders the hero picture, the battery percentage estimate, escaped recent flights, and the Next-update headline, with .preview-frame before .recent-flight in document order (D-04) | ported | companion/test_view_pages_03.py::test_home_page_render_with_seeded_state |
| 129 | Home's Battery tile draws exactly one ring, inside that tile, whose drawn fraction equals the '≈ NN%' it still prints beside its own millivolt detail and verdict; the ring is SMALLER than Health's yet identical to it in radius-over-box and stroke-over-box, proving one emitter at two sizes rather than two components; the frame verdict still appears exactly once; and a device with no reading draws no ring at all (CFG-40) | ported | companion/test_view_pages_03.py::test_home_battery_ring_is_the_same_drawing_at_a_smaller_size |
| 130 | Home's recent-flight relative age is a <time data-relative> element carrying the ROW's own instant, reading exactly what it reads today in both languages, with C5's .time-value/.cell-inline-sep/.time-value__age split and its parentheses intact (23-03, D14/CFG-34) | ported | companion/test_view_pages_03.py::test_home_recent_flight_age_is_an_element_reading_exactly_as_before |
| 131 | Home's rendered-picture caption carries concise_timestamp_html()'s <time data-relative> element THROUGH its i18n template's own %s — as markup, never double-escaped — with the caption's wording and the age's text unchanged in both languages (23-03, D14/CFG-34) | ported | companion/test_view_pages_03.py::test_home_rendered_caption_carries_the_element_through_the_template |
| 132 | a recent-flight row whose airline resolves to a real illustration file renders exactly one lazily-loaded /illustration/ thumbnail <img>; a null/unrecognised airline AND an airline whose normalised key resolves to no file on disk anywhere (override or vendored) both render the dashed placeholder span with no <img> at all (D-17 fix) | ported | companion/test_view_pages_03.py::test_recent_flight_thumb_resolved_vs_placeholder |
| 133 | the hero's flight one-liner (callsign in .mono, then airline, then the route) appears when the current flight is known and is absent otherwise, and the page reads header -> .frame-strip -> .home-status-grid -> .home-picture-row (.preview-frame before .recent-flight inside it) (D-04) | ported | companion/test_view_pages_03.py::test_hero_figure_precedes_status_card_with_flight_one_liner_when_known |
| 134 | under a French request Home's headings ('Vols récents'/'Voir tous les vols') and a thumbnail's alt text translate while the callsign/airline name stay untranslated data (D-05) | ported | companion/test_view_pages_03.py::test_home_page_french_render_translates_headings_and_alt_text_not_data |
| 135 | a fully-seeded Home render under lang='fr' shows the French page title, section headings, status-row labels and next-update headline with no English string leaking in (while the callsign/airline data stays untranslated), and the identical seeded render under the default language still carries every pre-existing English needle | ported | companion/test_view_pages_04.py::test_home_full_seeded_render_localises_to_french_without_leaking_english |
| 136 | Home's status card, fed a REAL health_page.compute_health_state() result computed under lang='fr', fully localises the Frame/Flight-data rows' timestamps (no English month abbreviation or ' ago' survives) and the Flight-data row's detail is now a single, verdict-free clause — never joined with ' · ', never repeating Health's own verdict wording (Polish fix 2 / 22-07-PLAN.md Task 1 B2 retarget) | ported | companion/test_view_pages_04.py::test_home_status_card_localises_real_health_state_timestamps_under_french |
| 137 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris): Home's Frame tile and the strip render the SAME clock string, and zero warn/error tokens appear anywhere on the page (X2, D-03/CFG-26) | ported | companion/test_view_pages_04.py::test_home_frame_tile_matches_strip_for_the_nightly_held_regression |
| 138 | a late frame flips the strip to 'Expected since'/dot--warn and Home's Frame tile to its own late verdict/stat-tile--warn together, at the same threshold — they cannot disagree because neither computes anything the other does not (X2) | ported | companion/test_view_pages_04.py::test_home_frame_tile_flips_to_late_together_with_the_strip |
| 139 | Home's Flight-data tile renders exactly one verdict (its own DATA_STATE_TEXT) with Health's verdict-free pipeline_detail_html beneath it, never Health's own PIPELINE_STATE_TEXT verdict sentence a second time (B2) | ported | companion/test_view_pages_04.py::test_home_flight_data_tile_one_verdict_verdict_free_detail |
| 140 | a recent-flight row whose stored airline is an alias ("CCM Airlines") renders the SAME display name ("Air Corsica") Flights shows via display_airline_name(), never the raw upstream string (X4) | ported | companion/test_view_pages_04.py::test_home_recent_flights_use_display_airline_name_matching_flights |
| 141 | exactly one element on a rendered Home page is named 'Frame' (the shared strip's own heading) — Home's tile caption is renamed to resolve the X4 collision | ported | companion/test_view_pages_04.py::test_home_exactly_one_element_named_frame |
| 142 | the recent-flight time cell markup carries no monospace class, and reads the clock (.time-value), the existing .cell-inline-sep middle dot and the relative age (.time-value__age) as one line (B18) | ported | companion/test_view_pages_04.py::test_home_recent_flight_time_one_line_no_mono_class |
| 143 | .home-status-grid's own CSS rule declares align-items: stretch (B2) | ported | companion/test_view_pages_04.py::test_home_status_grid_declares_align_items_stretch |
| 144 | .recent-flight__time's own CSS rule declares white-space: nowrap so the clock/age pair can never wrap onto a second line (B18) | ported | companion/test_view_pages_04.py::test_recent_flight_time_declares_white_space_nowrap |
| 145 | the real recent-flight thumbnail joins the shared white-backing/hairline/radius rule and the placeholder's own rule reuses .airline-card__placeholder's exact dashed/canvas-fill values (never a new literal, never sharing that pinned selector), so a missing thumbnail matches the real ones in weight (B18) | ported | companion/test_view_pages_04.py::test_recent_flight_thumbnails_share_the_shipped_treatments |
| 146 | companion/static/style.css still carries exactly one @supports selector(:has(*)) block — this plan opens no second one | ported | companion/test_companion_app_03.py::test_style_css_carries_exactly_one_has_feature_query_block |
| 147 | every key in companion/i18n_fr/home.py's own CATALOG is also a key of the merged companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up | ported | companion/test_view_pages_04.py::test_home_catalog_keys_all_present_in_merged_catalog |
| 148 | a rendered Home page carries no status-card__rows/home-hero markup, quick-action markup only inside .frame-strip (exactly two cells) and nowhere else, exactly three stat-tile elements labelled Frame/Battery/Flight data, and the Frame verdict sentence exactly once (D-04/D-05) | ported | companion/test_view_pages_04.py::test_home_full_render_has_quick_action_only_inside_strip_and_three_tiles |
| 149 | the Frame strip's headline reads 'Next update ≈ HH:MM' for a future next-update, 'Expected since HH:MM' in the warn treatment for a past one, and renders no headline at all when either the check-in or the wake interval is unknown (D-01, moved from the deleted _status_card_html()) | ported | companion/test_view_pages_04.py::test_home_status_card_headline_next_update_or_expected_since |
| 150 | a default Home render always carries the status tiles section's 'See details on Health' link (D-17) | ported | companion/test_view_pages_04.py::test_home_status_card_always_shows_health_link |
| 151 | home_page.render({}) degrades to its empty states without raising, battery.battery_percent() clamps and rejects bad input, and the gallery filename parser round-trips or returns None | ported | companion/test_view_pages_04.py::test_home_page_render_degrades_with_nothing |
| 152 | battery_percent() no longer exists on home_page after moving to companion/battery.py (D-01) | ported | companion/test_view_pages_04.py::test_battery_percent_moved_out_of_home_page |
| 153 | draw.percent_time() is a TIME scale and not the index scale beside it: midnight/midday/the day's final instant land at 0/50/100%, an hour is 1/24 of the band however many other instants are on it (so an outage draws as an outage), a DST day's own length is a parameter rather than a hardcoded 86400, and an instant outside the day is REJECTED rather than clamped onto an edge where it would invent a check-in (CFG-42, T-24-06-A, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_time_scale_places_by_when_not_by_index |
| 154 | the day band renders a wrapping night window (22:00-07:00) as TWO shaded spans covering nine hours, one flush to 00:00 and one flush to 24:00 with midday left clear — never one inverted span that would shade the middle of the day — while a daytime window stays one span and an absent/zero-width/out-of-day/malformed window shades nothing at all (CFG-42, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_night_window_shades_the_night_as_two_spans |
| 155 | the day band collapses marks closer than its own stated minimum spacing and returns EXACTLY how many it hid — 48 marks at a 30-minute cadence with nothing collapsed, a 60-second and a 1-second cadence both bounded by the band's width rather than the row count (T-24-06-C), no two kept marks under the minimum apart, and an unplaceable instant counted too so a caption built from the number can never claim a total the drawing does not reach (T-24-06-B, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_collapses_crowded_marks_and_reports_exactly_how_many |
| 156 | every class the day band emits is one of companion/draw.py's own named constants and is registered in DRAWING_CLASSES (so the stylesheet-resolution guard can see it), the markup carries no colour literal, no url() reference and no inline style, and a band supplied with a label announces itself as a named group rather than being hidden (CFG-39/CFG-42, 24-06-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_day_band_emits_only_registered_classes_and_no_colour |
| 157 | Home's day band draws one mark per check-in at its PARIS clock position, captions the Paris day it shows and states the count as text; a day with no check-ins still renders the band and its frame with a caption naming the day (an absent section would read as an unbuilt feature, an empty band reads as no activity); and with history.db unreadable the page renders with no band at all rather than an empty one claiming no check-ins (CFG-42, T-24-06-D, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_renders_the_day_and_says_what_it_shows |
| 158 | Home's day band shades the CONFIGURED quiet-hours window — the default 23:00-07:00 wrapping night window as two spans covering its eight hours, named in the caption — and with quiet hours disabled shades nothing and says nothing about them, while still drawing the day's check-ins (CFG-42/D-03, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_shades_quiet_hours_only_when_configured |
| 159 | Home's day band buckets check-ins by the PARIS day — a 22:30Z check-in (Paris 00:30 today) is on the band and a 2026-08-27T22:30Z one (Paris 00:30 tomorrow) is not, the mirror of the boundary 24-06-PLAN.md Task 2 named since Paris is never behind UTC — and spans a real 25-hour Paris day so midday lands at 52.00% rather than the 54.17% a hardcoded 86400 would give; it costs render() exactly one history.db read more than the two it made before, measured, and the frame verdict still appears exactly once (CFG-42/D-20, 24-06-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_home_day_band_buckets_by_paris_day_and_costs_one_read |
| 160 | Home's top is ONE composition: a single hero container holds the shared Frame strip (rendered once, unforked), the three status tiles carrying the battery ring, and the day band — the picture row stays outside it, the ring and the band each appear exactly once and both inside the hero, home_page.py carries no ring geometry and no second battery estimate (an unqualified battery_percent( is refused by a boundary regex), and the frame verdict still appears exactly once in BOTH languages (CFG-44, 24-08-PLAN.md Task 1) | ported | companion/test_view_pages_04.py::test_home_top_is_one_composition_holding_the_ring_and_the_band |
| 161 | the hero's battery ring is the same emitter Health's ring is — the two pages' rings carry one class vocabulary, computed from the markup rather than listed; the hero's day band draws three different shapes and not one; every class either of them emits is a constant companion/draw.py itself names; and neither companion/pages/home_page.py nor this check writes any of those strings down, because a literal goes on passing against a forked copy that still uses the old one (CFG-44, 24-08-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_the_heros_ring_is_the_emitter_healths_ring_is |
| 162 | breaking a shared emitter breaks the hero WITH the page it borrowed it from: one class constant inside companion/draw.py's ring emitter is replaced at check time and both Home's hero and Health's readout change, neither keeping the original string (a hero built from its own copy would); the band emitter's own mutation reaches the hero and leaves Health byte-identical, proving the mutation is targeted rather than a global perturbation; and both pages return to their pre-mutation markup (CFG-44, 24-08-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from |
| 163 | wake.next_wake_at_iso()/next_wake_status() return None/(None, None, None) for a falsy/unparseable ts or an unknown interval, last_checkin + wake_interval_s for a screen-on config, last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config (D-13's screen-off rule), and — 22-02-PLAN.md Task 1, D-03/CFG-26 — the quiet-hours-active fixtures: a window opening during the base interval wins over the naive candidate, an enabled-but-nowhere-near-active window changes nothing, an active window beats a 300s screen-off cadence, and the richer accessor carries the same effective interval and hold reason for every fixture above | ported | companion/test_view_pages_04.py::test_wake_next_wake_at_iso_contract |
| 164 | companion.frame_state.resolve_state() resolves due/held/late/unknown from a (next_wake_iso, effective_interval_s, hold_reason, now) tuple with an invisible grace window and a held frame that cannot escalate by elapsed time alone, headline_template()/delay_sentence_template() return the matching three-branch copy constants, and the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris) resolves to STATE_HELD end to end through wake.next_wake_status() (D-03/D-04, 22-02-PLAN.md Task 2, 22-UI-SPEC.md §3.3 binding rule 6) | ported | companion/test_view_pages_04.py::test_frame_state_resolve_state_contract |
| 165 | companion/frame_state.py names no dot--warn class and imports no layout module (view-free, D-03), and each of its six copy constants round-trips through companion.i18n's French catalogue unchanged in English (22-02-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_frame_state_is_view_free_and_localises_its_own_copy |
| 166 | companion/battery.py imports neither companion.pages nor server, preserving its shared, page-independent boundary (D-01) | ported | companion/test_companion_app_03.py::test_battery_module_imports_neither_a_page_module_nor_the_server_package |
| 167 | GET /history returns 200 with its own heading, GET /preview redirects (303) to /history, GET /preview.png now returns 404 (the route is retired), and GET /gallery/{name}.png returns 200 image/png with a real PNG signature — proving the route the per-row View-panel lightbox now links to genuinely serves full-resolution bytes, against a real running service | ported | companion/test_view_pages_04.py::test_history_preview_and_gallery_round_trip_over_http |
| 168 | a real authenticated GET of /airlines renders the dialog's replace, delete and upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark renders identically — against a real running service, proving the removed query parameter has no reader anywhere in the real request path (CFG-81, 29-01-PLAN.md) | ported | companion/test_view_pages_04.py::test_airlines_dialog_forms_render_unconditionally_over_real_http |
| 169 | both <dialog>s arrive through ONE @starting-style entrance on .lightbox[open] — fading and zooming from opacity 0 over var(--motion-fast), reaching History's lightbox and the Airlines gallery's wide variant from a single rule, with `display`/`allow-discrete` deliberately absent so close() ends the dialog outright rather than leaving an invisible click-swallowing sheet over the page (T-23-36), and with ::backdrop unanimated because the global reduced-motion override cannot reach it (D3/CFG-32, 23-10-PLAN.md Task 2) | ported | companion/test_view_pages_04.py::test_both_dialogs_arrive_through_one_starting_style_entrance |


### Part 01 (plan 33-05)

37 checks migrated to `companion/test_view_pages_01.py` (helpers in
`companion/test_view_pages_helpers.py`). Rubric codes: B x 10 (render()
calls and their output, or pure-Python behaviour with no rendering at
all), D x 21 (structural regex-over-rendered-HTML rewritten as
`companion_markup.parse_html()`/`select()`/`find_all()`, several through
the shared `row_block()` helper), C x 4 (checks that opened
`companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `css_rules()`/`declarations_for()`), S x 2
(source-text scans - "never imports html", "never redefines
_TYPE_DISPLAY_LABELS" - rewritten as `getattr()`/`hasattr()` identity
checks with no file read). 0 deleted - every check in this slice had a
direct behavioural or parsed-DOM equivalent. New module:
`companion/test_view_pages_01.py` (37 tests). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 169`
to `EXPECTED_CHECK_COUNT = 132` (132/132 still pass standalone).

### Part 02 (plan 33-06)

59 checks migrated to `companion/test_view_pages_02.py` (helpers added to
`companion/test_view_pages_helpers.py`: `detail_row_block()`,
`table_markup()`, `seed_gallery()`, `seed_unresolved_prefixes()`,
`write_panel_file()`, `strip_js_line_and_block_comments()`). Rubric
codes: D x 33 (structural/substring regex over RENDERED output —
`history_page.render()`/`airlines_page.render()` return values, never a
file opened from disk), J x 14 (checks that opened
`companion/static/panel-lookup.js`, `flight-rows.js` or `copy-button.js`
from disk rewritten over `served_asset()` — the served text is scanned
with the same string/regex assertions as before, since it is now
behaviour, not source; the one check needing an unstripped-of-strings
comment pass, `image.src = ""`, uses the new local
`strip_js_line_and_block_comments()` rather than
`companion_markup.strip_js_comments_and_strings()`, which would also
erase the empty-string literal it looks for), C x 5 (checks that opened
`companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `declarations_for()`, including the two at-rule
checks scoped to `@media (min-width: 960px)`), B x 7 (pure-Python
behaviour with no rendering, or a production function call asserted on
its output — `nearest_gallery_entry()`, `_gallery_name_to_iso()`,
`manual_resolutions.add_entry()`, the `airlines_page`/`history_page`
lightbox-constant-equality and reflection-driven attribute-classification
checks, the merged-i18n-catalogue-key checks). 0 deleted - every check
in this slice had a direct behavioural, served-asset or parsed-structure
equivalent; the one source-text check in the slice (row 40's
"`history_page.py` never renders the script's own clickable marker
class") is rewritten as a `history_page.render()` assertion instead of
an `open()` of `history_page.py`. New module:
`companion/test_view_pages_02.py` (59 tests). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 132`
to `EXPECTED_CHECK_COUNT = 73` (73/73 still pass standalone and through
the shim); the three lightbox token tuples
(`_LIGHTBOX_SHARED_TOKENS`/`_LIGHTBOX_AIRLINES_ONLY_TOKENS`/
`_LIGHTBOX_RENDER_ONLY_TOKENS`), `_NEW_VIEW_PANEL_ATTR_NAMES` and
`_read_panel_lookup_source()` are deleted from the legacy file (only
this slice's checks used them); `_strip_js_comments()` stays (still used
by later, still-legacy sections).

### Part 03 (plan 33-07)

38 checks migrated to `companion/test_view_pages_03.py` — the slice
holding most of this harness's JS-source contracts (panel-lookup.js's
date-math ban, flight-rows.js's live-script class, list-filter.js's
count-animation contract, freshness.js's single fetch() target),
Airlines' resolve-dialog action row and manual-count filter chip
(22-11-PLAN.md), the one-hop unresolved-airline link (22-09-PLAN.md
Task 2), Flights' day separators/row-identity/refresh-regions/detail-
reveal/Show-more contracts (23-08/29-03-PLAN.md), and Home's battery
ring, relative-age elements and French render (22-11/23-03/20-10-PLAN.md).
No new shared helpers were needed beyond what 33-06 already added to
`companion/test_view_pages_helpers.py`; this slice's one module-local
addition is a raw-string `_row_block()` (the summary-row sibling of
`vp.row_block()`'s Node contract, kept module-local like
`test_view_pages_02.py`'s own precedent) and `_all_static_script_routes()`
(enumerates every `companion/app.py` `*_SCRIPT_ROUTE` constant, replacing
a `glob.glob()` over `companion/static/*.js` with a non-hardcoded,
self-updating floor derived from the production module's own registered
route names — TST-12 forbids reading a production source file as text,
not introspecting an already-imported module's public constants).

Rubric codes: B x 25 (render()/production-function calls and their
output, or pure-Python behaviour with no rendering), C x 9 (checks that
opened `companion/static/style.css` from disk rewritten over
`served_stylesheet()` + `css_rules()`/`declarations_for()`/
`rules_with_selector()`, including two at-rule-scoped lookups —
`@media (max-width: 959.98px)` and `@starting-style`), J x 5 (checks
that opened a served JS asset from disk rewritten over `served_asset()`,
one of which — the flight-rows.js live-script-class check — uses the
existing `vp.strip_js_line_and_block_comments()` rather than
`companion_markup.strip_js_comments_and_strings()`, because the class
name it searches for is itself a JS string literal that the toolkit
stripper would erase). 0 checks deleted outright — every check in this
slice had a direct behavioural, served-asset, or parsed-structure
equivalent — but 2 partial S-rubric deletions inside otherwise-ported
checks:

- row 109 (`test_day_label_is_the_paris_day_formatters_own_output_and_never_sticky`):
  the legacy check's `"strftime" not in open(history_page.py).read()`
  clause is dropped. The behavioural equivalence the same check already
  asserts (the day label equals the day PORTION of
  `layout.local_clock_text()`'s own cross-day output) already proves the
  label comes from the shared Paris-local formatter rather than a second
  date-formatting path; the source-text grep added no behaviour beyond
  that comparison.
- row 119 (split into `test_flights_limit_clamps_every_hostile_input_into_bounds`
  parametrized ×19 and `test_flights_render_defers_entirely_to_flights_limit_for_hostile_ctx_values`,
  the ledger's primary target): the legacy check's
  `ast.parse(inspect.getsource(history_page.render))` proof that
  `render()` calls `flights_limit()` exactly once and never reads
  `ctx['flights_limit']` directly, and its `inspect.getsource(app_module)`
  line-count proof that `app.py` performs no arithmetic on the raw
  threaded value, are both dropped (guard G2 bans `inspect`/`ast`
  introspection of production source outright). Replaced by a strictly
  stronger behavioural proof: `render()` is called directly with the
  same 11 hostile `ctx['flights_limit']` values against a 60-row seeded
  fixture, and the rendered card count must equal `flights_limit()`'s
  own clamp for every one of them — if `render()` had any second,
  unvalidated path onto the raw value, the observed count would diverge
  from `flights_limit()`'s clamp for at least one hostile input.

New module: `companion/test_view_pages_03.py` (57 pytest node ids: 37
non-parametrized tests + the 19-way `test_flights_limit_clamps_every_hostile_input_into_bounds`
parametrization, covering the 38 baseline rows above). Legacy
`companion/test_view_pages.py` shrinks from `EXPECTED_CHECK_COUNT = 73`
to `EXPECTED_CHECK_COUNT = 35` (35/35 still pass standalone and through
the shim); the module-local `_row_block()` closure, the module-level
`_strip_js_comments()`/`_detail_row_block()`/`_table_markup()`/
`_seed_unresolved_prefixes()` helpers and the `glob`/`math`/
`server.plane.illustrations`/`server.plane.manual_resolutions`/
`server.poll_loop` imports are deleted from the legacy file (confirmed
by grep to be used exclusively by this slice); two nested functions
further down the still-legacy file (`_home_top_is_one_composition_holding_the_ring_and_the_band`,
`_the_heros_ring_is_the_emitter_healths_ring_is`) had their own
redundant local `import ast`/`import inspect` removed as a Rule 1 fix —
deleting this slice's own top-level `ast.parse(inspect.getsource(...))`
usage (row 119, now replaced above) left those two nested shadow-imports
as the only remaining uses of the module-level `ast`/`inspect` bindings
in file order, which `ruff` (F811) correctly flagged as a
redefinition-of-unused regression once the earlier top-level usage was
gone.

### Part 04 (plan 33-08) — chain closed

35 checks migrated to `companion/test_view_pages_04.py` (33 new pytest
node ids; 2 rows consolidated into pre-existing, identical coverage
already ported by a different harness's own migration —
`companion/test_companion_app_03.py`'s `@supports selector(:has(*))`
count and its `companion.battery` import-boundary check — rather than
duplicated, per 33-MIGRATION-RULES.md section 3). This is the chain's
LAST slice: Home's fully-seeded French render and localised health-state
timestamps, the Frame/Flight-data tile verdict contracts, four CSS-only
checks (one consolidated), the i18n catalogue membership check, Home's
quick-action/headline/health-link/degrade/battery-move contracts,
`companion/draw.py`'s day-band time-scale/night-window/crowding/class
contracts, Home's own day-band integration (Paris-day bucketing,
quiet-hours shading, one extra `history.db` read), the hero composition
(CFG-44), `companion.wake`/`companion.frame_state`'s resolution
contracts, `companion/frame_state.py`'s view-free boundary (one
consolidated), and two real HTTP round trips plus the shared
`@starting-style` lightbox entrance.

Rubric codes: B x 15 (render()/production-function calls and their
output, or pure-Python behaviour with no rendering — the day-band unit
checks, `wake`/`frame_state`'s own contracts, the two real HTTP round
trips), D x 3 (structural checks over rendered/parsed HTML — the hero
composition's containment assertions, the `.lightbox`/`.lightbox--wide`
dialog-class proof via `companion_markup.parse_html().select()`), C x 5
(checks that opened `companion/static/style.css` from disk rewritten
over `served_stylesheet()` + `companion_markup.declarations_for()`/
`rules_with_selector()` — the status-grid/recent-flight-time/thumbnail
checks and the `@starting-style` entrance, the last of which replaces
every substring/regex assertion the legacy check made over raw CSS text
with parsed `Rule.declarations` lookups), S x 4 (source-text scans
rewritten or consolidated): the hero composition's `inspect.getsource()`
forbidden-literal/required-call scan (row 160) and the ring/band
vocabulary check's `ast.parse()` restated-literal scan (row 161) are
each a PARTIAL deletion inside an otherwise-fully-ported check — their
surviving structural/vocabulary assertions stay, and the source-scan
clause is dropped because
`test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_
borrowed_it_from` (row 162) already proves the identical "no forked
copy" property strictly more strongly, by mutation rather than static
analysis (guard G2 bans `inspect`/`ast` over production source outright
regardless). `companion/frame_state.py`'s own "never imports layout"
half (row 165) is rewritten as a subprocess-import + `sys.modules`
check (the same technique `companion/test_companion_app_03.py`'s own
`battery`/`draw` import-boundary checks already established), and its
"never names a CSS dot class" half is rewritten against the module's own
already-imported public string constants. `companion/battery.py`'s
identical "never imports pages or server" check (row 166) is a full S
consolidation: `companion/test_companion_app_03.py` already ports the
exact same claim with the exact same subprocess technique, so the
ledger row points there instead of creating a second copy. 0 checks
fully deleted with no replacement.

New module: `companion/test_view_pages_04.py` (33 pytest node ids).
Legacy `companion/test_view_pages.py` is deleted outright (`git rm`) —
this is the chain's closing plan. `EXPECTED_CHECK_COUNT`/`check()`/
`main()` and every helper/fixture the file owned (`Harness`,
`http_request`, `_NoRedirectHandler`, `_mkstate()`,
`_seed_runway_events()`, `_write_panel_file()`, `_write_gallery_png()`,
`_seed_gallery()`, `_history_ctx()`, `_login()`) leave the tree with it.
`companion/test_view_pages.py` also drops out of
`skypane_test_support.legacy_companion_harnesses()`'s disk-derived set
and `companion/test_legacy_harness_shim.py`'s parametrize list the
moment the file is gone — no hand list needed editing. Baseline total:
169/169 view-pages checks accounted for across all four parts (37 + 59 +
38 + 33 = 167 new pytest node ids across `test_view_pages_01.py`/`_02.py`/
`_03.py`/`_04.py`, plus 2 consolidated into `test_companion_app_03.py`'s
pre-existing identical coverage) — 0 pending.


### Closing sweep (plan 33-32): structural stylesheet checks

Rows 98, 100, 105, 112 and 113 kept their node ids but no longer assert with a regex, `in` test
or str search over the served stylesheet's text (33-FOLLOWUPS.md F-01). Selector presence and
absence go through `css_rules()` / `rules_with_selector()`; row 112's `grid-template-rows: 0fr`
and `@starting-style` probes become one `declarations_for()` read of the reveal wrapper's
`@starting-style` rule; rows 112 and 113 check the banned properties and the three
reduced-motion blocks with `css_rules()` and `at_rule_blocks()`. Two unused text-level rule-body
helpers were deleted from `companion/test_view_pages_03.py`.

## companion/test_config_page.py

# Ledger: companion/test_config_page.py

Baseline: `companion__test_config_page.txt`, 276 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | _ASPECT_REPIN_LEDGER is non-empty, every row is well-formed (all five keys present, 'property' naming an actual property in at least eight words, not a restated selector), no 'retired' name still has a def in this file, every 'owed_by' names one of this phase's own later plans, and any row claiming repayment IN this file (empty owed_by) names a replacement that genuinely has a def here — so a forgotten re-pin is a red build, not a silent coverage loss (CFG-85, 30-03-PLAN.md Task 1) | deleted | R: self-referential CFG-85 aspect-repin bookkeeping; opens test_config_page.py to grep def names; no behaviour |
| 2 | render() emits no <fieldset>/<legend> and no .theme-chip-grid on this legacy SCOPE_ALL render (Theme's card retired outright, D-01/21-05-PLAN.md Task 1 D-06), five theme-status-wrapped groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications — Display's own card retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1), three runway-card labels, and a Save settings submit button | ported | companion/test_config_page_01.py::test_render_emits_no_fieldset_or_legend_five_groups_three_runway_cards_and_save_button |
| 3 | led_group() emits the switch and preserves its class/role/aria-checked attribute sequence in both states, with the retired settings-checkbox label gone (retargeted in place from the checkbox's own sequence by 23-07-PLAN.md Task 2) | ported | companion/test_config_page_01.py::test_led_group_carries_the_switch_and_its_state_attribute_sequence |
| 4 | quiet_hours_group() renders no on/off checkbox at all any more (the Frame strip is the only control left, 22-05-PLAN.md Task 1 X1/D-04/D-12.1), one type="time" input each for Start/End with their current values, no theme-status__row, and no disabled attribute | ported | companion/test_config_page_01.py::test_quiet_hours_group_markup_no_checkbox_and_time_inputs |
| 5 | quiet_hours_group()'s field order is heading, then caption, then Start, then End, in document order — the enable checkbox this order used to include is retired outright (22-05-PLAN.md Task 1, X1/D-04/D-12.1) | ported | companion/test_config_page_01.py::test_quiet_hours_group_field_order_heading_caption_start_end |
| 6 | quiet_hours_group() escapes a crafted current_start value — no raw <script> substring reaches the markup | ported | companion/test_config_page_01.py::test_quiet_hours_group_escapes_crafted_current_values |
| 7 | quiet_hours_group() renders exactly three data-quiet-preset <button type="button"> elements | ported | companion/test_config_page_01.py::test_quiet_hours_group_renders_exactly_three_button_presets |
| 8 | the Night preset's data-preset-start/data-preset-end equal server.device_config's DEFAULT_QUIET_HOURS_START/DEFAULT_QUIET_HOURS_END | ported | companion/test_config_page_01.py::test_quiet_hours_group_night_preset_matches_device_config_defaults |
| 9 | the Work day preset carries data-preset-start="08:00" data-preset-end="18:00" | ported | companion/test_config_page_01.py::test_quiet_hours_group_workday_preset_carries_expected_times |
| 10 | the Always-on preset carries data-preset-enabled="0" and no data-preset-start/data-preset-end attributes | ported | companion/test_config_page_01.py::test_quiet_hours_group_always_on_preset_disables_with_no_time_attrs |
| 11 | the preset button row appears after the section caption and before the first type="time" input (D-14's locked position, retargeted by 22-05-PLAN.md Task 1 now that the checkbox it used to follow is gone) | ported | companion/test_config_page_01.py::test_quiet_hours_group_preset_row_between_caption_and_time_inputs |
| 12 | handle_post() persists a Night-preset-shaped submission (quiet_hours_start/end equal to device_config's own defaults) exactly as it would a hand-typed value - no new server code path (T-19-38) | ported | companion/test_config_page_01.py::test_handle_post_preset_filled_submission_treated_identically_to_hand_typed |
| 13 | render() wires quiet_hours_group() with the saved current values, positioned after Diagnostic LED and before the Save settings button | ported | companion/test_config_page_01.py::test_render_wires_quiet_hours_group_after_led_before_save_button |
| 14 | wake_interval_group(120) emits one .theme-status[data-dirty-section] wrapper, the locked heading/caption, one type="number" input with min/max from device_config and the locked placeholder and a matching value, and none of <fieldset>/<legend>/settings-checkbox | ported | companion/test_config_page_01.py::test_wake_interval_group_markup_in_range_value |
| 15 | wake_interval_group() emits a value attribute only for an in-range, non-bool int (None/True/False/a str/30/59/3601/7200 all emit none; 60/3600/120 each emit theirs) — an out-of-range or wrong-typed value would fail native constraint validation and block the whole form | ported | companion/test_config_page_01.py::test_wake_interval_group_value_attribute_only_for_in_range_non_bool_int |
| 16 | render() places Wake interval last in the locked five-group order, resolves no value attribute when neither source is present, prefers an on-disk wake_interval_s over ctx['wake_interval_env_default'], and falls back to the ctx default when the on-disk value is None | ported | companion/test_config_page_01.py::test_render_places_wake_interval_last_and_resolves_prefill |
| 17 | X1/D-04: no settings render (legacy SCOPE_ALL, Display, Device) carries a display_enabled or quiet_hours_enabled input any more — the Frame strip is the only on/off control for either setting (22-05-PLAN.md Task 1, superseding 12-05-PLAN.md/10-05-PLAN.md's own checkbox markup) | ported | companion/test_config_page_01.py::test_no_page_and_no_scope_renders_a_display_or_quiet_hours_on_off_checkbox |
| 18 | D-09's no-JS floor holds at this plan's own commit: scripts-blocked Display and Device renders each carry a reachable fallback Save button, form="settings-form"-ASSOCIATED with a plain server-rendered form (relocated into the restored .dirty-bar by 28-08-PLAN.md Task 1, CFG-77/CFG-78 — never a literal descendant of the form any more, and native submission is unchanged in substance either way), and a plain (no-JS) POST still round-trips the Quiet hours schedule | ported | companion/test_config_page_01.py::test_no_js_floor_holds_on_display_and_device_after_the_checkbox_removal |
| 19 | handle_post() resolves display_enabled through all three shapes: absent LEAVES the stored value unchanged (D-12.1, retargeted from the pre-22-05 absent-means-False bug), DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key and leaves a pre-existing device_config.json byte-identical | ported | companion/test_config_page_01.py::test_handle_post_display_enabled_three_shapes |
| 20 | REGRESSION GUARD (T-22-16/T-23-25, 22-RESEARCH.md Pitfall 1): a settings save that only changes the theme leaves display_enabled, quiet_hours_enabled AND led_enabled EXACTLY as they were, across all eight starting True/False combinations — extended in place from the two-flag/four-combination version 22-05 landed, never duplicated beside it | ported | companion/test_config_page_01.py::test_handle_post_theme_only_save_never_flips_display_quiet_hours_or_led_off |
| 21 | all four Config settings groups (Theme/Runway/Diagnostic LED/Poll) are named exactly once, all via the shared <h2 class="text-heading"> role, with zero <legend> and zero <fieldset> anywhere on the page (06.6.4.1.1-05, D-01) | ported | companion/test_config_page_01.py::test_every_settings_group_is_named_exactly_once |
| 22 | Settings opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_config_page_01.py::test_render_opens_with_shared_page_header |
| 23 | the settings form keeps the stable config-form class hook the desktop two-column fieldset layout targets | ported | companion/test_config_page_01.py::test_settings_form_carries_config_form_class_hook |
| 24 | the Aspect card's three palettes each render one radio per registered theme, in registry order, each carrying its own registry id/translated label/data-preview-src and form=settings-form, with arrivals/calendar carrying exactly one leading Same-as-departures option and departures exactly zero (D-06, 30-05-PLAN.md Task 1, replacing the retired _frame_colours_card_covers_every_registered_theme_with_own_id_and_label) | ported | companion/test_config_page_01.py::test_aspect_card_covers_every_registered_theme_with_own_id_and_label |
| 25 | the Aspect card rendered with the default theme id marks exactly the White chip selected in the departures palette, and exactly the leading Same-as-departures option selected in the arrivals/calendar palettes, each asserted per group (D-06/D-07, 30-05-PLAN.md Task 1, replacing the retired _frame_colours_card_default_selects_exactly_the_white_departures_option) | ported | companion/test_config_page_01.py::test_aspect_card_default_selects_exactly_the_white_departures_option |
| 26 | runway_fieldset() emits exactly three runway radio inputs | ported | companion/test_config_page_01.py::test_runway_fieldset_exactly_three_radios |
| 27 | runway_fieldset('3') renders three selectable cards, each wrapping a visually-hidden radio, with only the '3' card selected (D-05) | ported | companion/test_config_page_01.py::test_runway_fieldset_cards_visually_hidden_radio_and_selected_class |
| 28 | runway_fieldset('3', images_available=('3', '06-24')) renders an <img> inside exactly those two cards, none in the third (D-05) | ported | companion/test_config_page_01.py::test_runway_fieldset_cards_image_rendering_per_card |
| 29 | _palette_swatch_html() draws exactly the registry-derived 5-of-18 banded themes with a band child, renders a plain theme as one solid <span> with no opacity, and space-joins extra_class onto its class attribute (CFG-85) | ported | companion/test_config_page_01.py::test_palette_swatch_html_matches_the_live_registry_band_facts |
| 30 | _palette_grid_html() renders one chip per registered theme in device_config.THEME_IDS order, zero <img>, data-preview-src and form="settings-form" on every chip, exactly one selected check glyph, leading_html before the chips, and no id attribute of its own (CFG-85) | ported | companion/test_config_page_01.py::test_palette_grid_html_renders_one_chip_per_registered_theme_in_order_no_photo |
| 31 | _usage_row_summary_html() renders a well-formed <summary> joining the translated row label and meta text via ASPECT_ROW_SUMMARY_TEMPLATE's single em-dash source, and renders no swatch at all when theme_id is None (the rules row) (CFG-85) | ported | companion/test_config_page_01.py::test_usage_row_summary_html_joins_row_label_and_meta_with_one_em_dash_source |
| 32 | runway_fieldset() escapes a hostile registry label rather than dropping or interpolating it unescaped (T-25-03-B, narrowed from the retired map's own coverage by 27-05-PLAN.md Task 3, CFG-66) | ported | companion/test_config_page_01.py::test_runway_fieldset_escapes_a_hostile_registry_label |
| 33 | the control's own semantics and the photographs survive the map's removal — the row keeps role="radiogroup" with the same aria-labelledby/aria-describedby ids, current_runway_id=None marks nothing selected and leaves no radio checked, and the three runway photographs still render from the session-gated route and still exist on disk (CFG-66, retitled from CFG-47's retired 25-03-PLAN.md Task 1 check by 27-05-PLAN.md Task 3) | ported | companion/test_config_page_01.py::test_the_controls_semantics_and_the_photographs_survive_the_maps_removal |
| 34 | the quiet window's span goes FORWARD through midnight — 23:00→07:00 is 480 minutes and 07:00→23:00 its 960-minute complement, 00:00→00:01 and 23:59→00:00 are both 1, the drawn sweep is the returned minute count and never a second computation, the span's length is reconstructed from what server.device_config.seconds_until_quiet_hours_end() has left at a shared instant rather than pinned, equal ends is the zero-width window that server's own docstring calls never-active, and every unparseable input returns the render-nothing signal rather than raising or fabricating a zero (CFG-48, 25-04-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_the_quiet_window_wraps_midnight_the_short_way_round |
| 35 | the quiet dial's arc is recomputed from the attributes the SERVER emitted — 23:00→07:00 draws a third of the emitted circle and 07:00→23:00 its two thirds, the dash pattern adds up to that circle's own circumference, and the arc is rotated by a quarter turn plus the window's own start about its own centre (an eight-hour arc drawn from the wrong hour is the same length and a different window); the readout names both times and the duration the same span implies and is aria-hidden; nothing on the card is a role="status"/aria-live region (CFG-52); nothing stored draws no arc and no words while the full-day ring still draws; and a hostile submitted value reaches neither (T-25-04-B) (CFG-48, 25-04-PLAN.md Task 2) | ported | companion/test_config_page_02.py::test_the_ring_draws_the_saved_window_from_the_emitted_attributes |
| 36 | quiet_dial_readout_html() carries data-value-readout-format="clock" on both endpoint spans and a non-empty value for each of the four layout.DURATION_ATTRS on the duration span, in both shipped languages (CFG-73 Bug A, 28-03-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages |
| 37 | the ring is an ADDITION: both native <input type="time"> fields keep their value/required/lang/form attributes and are never disabled, B14's visible 24h sibling still renders beside each, the three presets keep the data attributes dirty-state.js writes through, the one section caption is EXACTLY QUIET_HOURS_SECTION_CAPTION with no appended delay sentence (29-05-PLAN.md Task 2, CFG-79), the card's order is caption → ring → presets → Start → End with the four controls' own order and adjacency untouched and no side-by-side row, and the arc echoes the SUBMITTED window on a rejected save rather than the stored one (B14/D-07/CFG-48, 25-04-PLAN.md Task 2) | ported | companion/test_config_page_02.py::test_the_ring_is_an_addition_and_the_four_controls_are_untouched |
| 38 | every class quiet_hours_group() emits — including the new .quiet-preset-row/.quiet-times-row wrappers — resolves to a real selector in style.css, scanned off the emitted markup rather than a hand-kept list (CFG-80, 29-04-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_every_class_the_quiet_hours_card_emits_has_a_real_selector |
| 39 | both <input type="time"> elements, both B14 twins and each field's own error paragraph all fall inside the .quiet-times-row container's own slice of the markup, across a clean render and a rejected save on either field (CFG-80, 29-04-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_both_time_fields_and_twins_sit_inside_the_times_row_with_their_own_error_slot |
| 40 | the three preset buttons render the short labels Night/Day/Always on and Nuit/Journée/Toujours actif, and NO preset label contains a ':' in either language — the hours are spoken once, by the dial's own readout (CFG-80, 29-04-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_the_three_preset_buttons_render_short_labels_with_no_colon_in_both_languages |
| 41 | style.css's .quiet-times-row rule declares display: grid with a grid-template-columns of exactly two tracks, parsed from the stylesheet itself (CFG-80, 29-04-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_the_times_row_rule_declares_exactly_two_grid_tracks |
| 42 | Check A — the scripts-blocked state, proven from the served markup: rendering /display's quiet-hours card in both languages emits exactly two hook-attribute spans, each rendering the SAME text as its own field's value attribute (a relationship, never a literal), with none carrying hidden/js-gate/style — the served HTML IS what a scripts-blocked reader sees (CFG-80, 29-04-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_check_a_the_twin_is_visible_in_the_served_markup_in_both_languages |
| 43 | Check B — the hide path is gated, and gated on one thing only: exactly one `.hidden = true` assignment on the hook attribute, gated by a strict `hour12 === false` comparison (never a truthiness test), with the Intl/resolvedOptions availability guard preceding it, and a vacuity floor on the comment-stripped source's own length ratio and hook-literal count (CFG-80, 29-04-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_check_b_the_hide_path_is_gated_on_one_strict_condition |
| 44 | Check C — the four surfaces still agree, at the render level: for 23:00→07:00 (midnight-wrapping), 08:00→18:00 (non-wrapping) and a rejected-save echo (09:00→17:00 submitted over a 23:00→07:00 stored value), the arc's presentation attributes, the two handles' aria-valuenow, the readout's endpoint text and both <input type="time"> values all decode to the SAME canonical minute-of-day pair (CFG-80/CFG-62, 29-04-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_check_c_the_four_server_rendered_surfaces_agree |
| 45 | the quiet dial's paint resolves — every class the EMITTED markup carries has a real selector (scanned off the markup, boundary-anchored), every shape carries a class, an explicit fill="none" and a stroke width, the canvas declares its viewBox, its intrinsic size, aria-hidden and focusable, no colour is decided in Python, the day ring/arc/hour labels each paint from a theme token so both themes are correct from one rule, no accent appears anywhere in the component, and no rule declares stroke-width in CSS where it would beat the derived presentation attribute (CFG-48/CFG-52, 25-04-PLAN.md Task 2) | ported | companion/test_config_page_02.py::test_the_dials_paint_resolves_and_decides_nothing_in_python |
| 46 | the quiet dial's two handles are real <button type="button"> sliders INSIDE 25-01's .js gate and nowhere else (every element carrying the wrapper attribute carries the gate class itself, and every element carrying the handle attribute is inside a wrapper); each carries role/aria-valuemin/aria-valuemax/aria-valuenow and an aria-valuetext that is the HH:MM its own input holds rather than a minute count, plus a translated aria-label in both languages; each wrapper carries layout's own steering attributes including the clock codec, is painted at the fraction its input's value implies, and names --value-fraction in all three files it travels through; the aria-valuetext token is not one of the format artefacts the i18n harness scans French renders for; and an end that does not parse gets no handle at all (CFG-48, 25-04-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_the_two_handles_are_gated_and_hold_no_value_of_their_own |
| 47 | the quiet dial's handle rides the ring the emitter drew — the stylesheet's dial width and handle radius equal config_page.QUIET_DIAL_SIZE and QUIET_DIAL_RADIUS, the shared handle rule still follows the shared hit-area rule so the absolute `position` wins at equal specificity, both stacked layers are pointer-transparent while the handle itself is not, the transform reads both custom properties, no z-index re-decides the document-order overlap rule, and the grip paints from theme tokens with no accent (CFG-48/CFG-52, 25-04-PLAN.md Task 3) | ported | companion/test_config_page_02.py::test_the_handle_rides_the_ring_the_emitter_drew |
| 48 | the pair seam publishes both handles onto the shared ancestor (CFG-62, 27-02-PLAN.md Tasks 1-2) — value-controls.js names both data-value-pair* attributes and reuses ancestorWith() rather than a second walker (still exactly 2 'while (node' loops); the .quiet-dial ancestor carries the pair marker (its own value naming the derived sweep property) and all three fractions, computed from the SAME span triple the arc is drawn from; the two handles publish under DIFFERENT, correctly-named properties; the arc's own presentation attributes are untouched real user-unit values (no pathLength, measured to corrupt them); and the .js-scoped override rule reads the three ancestor properties plus the existing --quiet-dial-radius, never a radius literal | ported | companion/test_config_page_02.py::test_the_pair_seam_publishes_both_handles_onto_the_shared_ancestor |
| 49 | render() carries exactly five data-dirty-section elements, in document order Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications (Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 D-06; Calendar's own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/Pitfall 2; Display's own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1) | ported | companion/test_config_page_02.py::test_render_exactly_five_dirty_sections_in_order |
| 50 | runway_fieldset() returns exactly two div pairs - the top-level .theme-status wrapper and the nested .runway-row layout container, not five flat siblings (D-01) | ported | companion/test_config_page_02.py::test_runway_fieldset_returns_single_top_level_div |
| 51 | runway_fieldset() renders RUNWAY_SECTION_CAPTION before .runway-row opens, and no <p element after .runway-row closes (quick task 260901-re6) | ported | companion/test_config_page_02.py::test_runway_row_starts_after_caption_and_nothing_follows_it |
| 52 | render() carries RUNWAY_SECTION_CAPTION exactly once (quick task 260901-re6, narrowed by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired) | ported | companion/test_config_page_02.py::test_runway_section_caption_appears_exactly_once |
| 53 | runway_fieldset()/led_group() each emit exactly one section-caption <p> element, positioned after the group's own naming element and before its control (quick task 260901-re6, merge of origin/main; narrowed by 21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired) | ported | companion/test_config_page_02.py::test_each_group_emits_exactly_one_caption_between_heading_and_control |
| 54 | the bar's Save button is the SAME STATIC_SAVE_FALLBACK_ATTR element CFG-64 pins, relocated inside .dirty-bar with form="settings-form" — never a second button, and the physical <form> itself carries no submit control of its own any more (CFG-77/CFG-78, 28-08-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_the_bar_s_save_button_is_the_same_static_fallback_element_relocated |
| 55 | the restored .dirty-bar renders WITHOUT a hidden attribute on every scope — the no-JS floor is the bar's own visible server-rendered state now, not a separate fallback button (CFG-77/CFG-78, 28-08-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_the_dirty_bar_renders_without_hidden_on_every_scope |
| 56 | no control inside the restored .dirty-bar is inert with scripts blocked (every <button>/<input> resolves to type="submit" or type="reset", each form="settings-form"-associated, none type="button"), and [data-dirty-count]'s server-rendered content makes no claim about unsaved changes existing, in either language (CFG-77/CFG-78, 28-08-PLAN.md Task 1) | ported | companion/test_config_page_02.py::test_nothing_inside_the_bar_is_inert_or_claims_a_dirty_state_that_does_not_exist |
| 57 | the runway, LED, and poll section captions all appear escaped-verbatim exactly once in render()'s output (quick task 260901-re6, quick task 260901-s5o; narrowed by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired) | ported | companion/test_config_page_02.py::test_section_captions_appear_escaped_verbatim_exactly_once |
| 58 | the (non-default) saved runway card is the one marked selected, and this legacy SCOPE_ALL render carries zero .theme-chip--selected modifiers now that theme_fieldset(), Calendar's own chip grid, and the rules add-form's own chip grid are all retired from it (D-06) | ported | companion/test_config_page_02.py::test_current_theme_and_runway_are_selected |
| 59 | poll_trigger_section(0) renders an enabled button | ported | companion/test_config_page_02.py::test_poll_trigger_enabled_at_zero_cooldown |
| 60 | poll_trigger_section(17) renders a disabled button and the remaining-seconds copy | ported | companion/test_config_page_02.py::test_poll_trigger_disabled_with_remaining_seconds |
| 61 | poll_trigger_section() emits POLL_SECTION_CAPTION exactly once on both the enabled and disabled branches, before the poll-trigger form, and render() places it directly under the Poll <h2> heading (quick task 260901-s5o) | ported | companion/test_config_page_02.py::test_poll_section_caption_renders_on_both_branches_under_the_heading |
| 62 | poll_trigger_section() emits zero <script> elements and ships the D-01/UXA-15 data-* attribute contract companion/static/poll-cooldown.js reads instead, on both the disabled and zero-cooldown branches (D-18/A-35, 19-04-PLAN.md) | ported | companion/test_config_page_02.py::test_poll_trigger_live_countdown_seeded_from_server_value |
| 63 | poll_trigger_section(0) ships id="poll-trigger-btn" and a data-submit-pending attribute with zero <script> elements, while poll_trigger_section(30) carries the disabled-branch data-cooldown attribute instead (D-18/A-35, 19-04-PLAN.md) | ported | companion/test_config_page_02.py::test_poll_trigger_zero_cooldown_ships_submit_affordance_script |
| 64 | poll_trigger_section(17) carries no <script substring and ships the countdown's required data attributes; companion/static/poll-cooldown.js's own source contains none of the forbidden HTML-writing/eval/network sinks and does contain strict mode plus the permitted DOM/timer operations (retargeted, D-18/A-35) | ported | companion/test_config_page_02.py::test_poll_cooldown_script_has_no_forbidden_sink |
| 65 | poll_trigger_section(0) carries no <script substring and ships the data-submit-pending attribute; companion/static/poll-cooldown.js's own source contains none of the forbidden HTML-writing/eval/network sinks and attaches a submit listener (retargeted, D-18/A-35, UXA-15) | ported | companion/test_config_page_02.py::test_poll_submit_script_has_no_forbidden_sink |
| 66 | a post with a valid theme and runway writes both and returns the saved flash key | ported | companion/test_config_page_02.py::test_valid_save_writes_both_and_returns_saved_key |
| 67 | a post with a non-member theme writes nothing and returns the save-failure flash key | ported | companion/test_config_page_02.py::test_nonmember_theme_writes_nothing |
| 68 | a post with a non-member runway writes nothing and returns the save-failure flash key | ported | companion/test_config_page_02.py::test_nonmember_runway_writes_nothing |
| 69 | a post with a theme but no runway field carries the existing runway forward unchanged | ported | companion/test_config_page_02.py::test_theme_only_post_carries_runway_forward |
| 70 | a post with a directory-traversal-shaped theme value is rejected by the membership test | ported | companion/test_config_page_02.py::test_path_traversal_theme_rejected |
| 71 | a post with a SQL-fragment-shaped theme value is rejected by the membership test | ported | companion/test_config_page_02.py::test_sql_fragment_theme_rejected |
| 72 | a save that raises OSError returns the save-failure flash key rather than propagating | ported | companion/test_config_page_02.py::test_save_oserror_returns_failure_key_not_raise |
| 73 | handle_post({}, ctx) - the shape a browser sends when nothing is checked and nothing is selected - LEAVES the stored led_enabled unchanged in both directions and returns the saved flash key (retargeted in place from absent-means-False by 23-07-PLAN.md Task 2) | ported | companion/test_config_page_02.py::test_handle_post_empty_form_leaves_led_unchanged[led-was-on] |
| 74 | handle_post({"led_enabled": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True | ported | companion/test_config_page_02.py::test_handle_post_led_checkbox_value_persists_led_true |
| 75 | handle_post({"led_enabled": "<crafted>"}, ctx) returns the save-failed flash key and leaves device_config.json byte-identical | ported | companion/test_config_page_02.py::test_handle_post_crafted_led_value_rejected_byte_identical |
| 76 | handle_post({"theme": "<not a registered theme>", "led_enabled": LED_CHECKBOX_VALUE}, ctx) returns save-failed and leaves the file byte-identical (an invalid theme rejects the LED half too) | ported | companion/test_config_page_02.py::test_handle_post_invalid_theme_rejects_led_half_too |
| 77 | handle_post({"tracked_runway": <a real runway id>, "led_enabled": LED_CHECKBOX_VALUE}, ctx) persists both in one call and returns the saved flash key | ported | companion/test_config_page_02.py::test_handle_post_valid_runway_and_led_persist_together_one_call |
| 78 | handle_post with quiet_hours_enabled=QUIET_HOURS_CHECKBOX_VALUE and both times persists all three quiet-hours fields and returns the saved flash key | ported | companion/test_config_page_02.py::test_handle_post_quiet_hours_checkbox_on_persists_all_three |
| 79 | handle_post with quiet_hours_enabled absent but both times submitted persists quiet_hours_enabled False and the edited times (a user can pre-configure a window before enabling it) | ported | companion/test_config_page_02.py::test_handle_post_quiet_hours_checkbox_absent_still_persists_times |
| 80 | handle_post({"quiet_hours_start": "24:00"}, ctx) against a legitimately-saved config returns the save-failed flash key and leaves device_config.json byte-identical | ported | companion/test_config_page_02.py::test_handle_post_malformed_quiet_hours_time_rejected_byte_identical |
| 81 | handle_post({"quiet_hours_enabled": "yes"}, ctx) returns the save-failed flash key, matching the LED field's own third shape | ported | companion/test_config_page_02.py::test_handle_post_crafted_quiet_hours_checkbox_value_rejected |
| 82 | a post with a valid theme AND a malformed quiet_hours_end returns save-failed and persists neither — the theme on disk is unchanged (all-or-nothing across groups) | ported | companion/test_config_page_02.py::test_handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing |
| 83 | handle_post({"wake_interval_s": "120"}, ctx) explicitly string-to-int converts before persisting, stores the int (not a string) 120, and returns the saved flash key (11-RESEARCH.md Pitfall 1 regression guard) | ported | companion/test_config_page_02.py::test_handle_post_wake_interval_string_converts_to_int_and_persists |
| 84 | handle_post rejects "abc"/"1.5" (handler's int() gate) and "59"/"3601"/"-1" (save_device_config()'s bounded-range check), each returning the save-failed flash key and leaving a pre-existing device_config.json byte-identical | ported | companion/test_config_page_02.py::test_handle_post_wake_interval_rejection_paths_byte_identical[abc-not-an-int] |
| 85 | after a save that stored wake_interval_s 120, a later submission with wake_interval_s as the empty string, and another with the key absent entirely, both return the saved flash key and leave the stored value at 120 (11-RESEARCH.md Open Question 2) | ported | companion/test_config_page_03.py::test_handle_post_wake_interval_empty_or_absent_leaves_unchanged |
| 86 | handle_post(form, ctx) with no errors argument still returns exactly the same flash keys it did before this plan, for both a representative valid save and a representative invalid save | ported | companion/test_config_page_03.py::test_handle_post_no_errors_arg_returns_identical_flash_keys |
| 87 | handle_post(form, ctx, errors=d) fills d with exactly one field-keyed message for each real-user-error case (wake_interval_s non-numeric/out-of-range, quiet_hours_start/quiet_hours_end malformed including empty, and a contradictory calendar_url+calendar_disconnect submission) | ported | companion/test_config_page_03.py::test_handle_post_errors_dict_filled_for_each_real_user_error_field[wake-interval-out-of-range] |
| 88 | handle_post(form, ctx, errors=d) leaves d empty when the save succeeds | ported | companion/test_config_page_03.py::test_handle_post_errors_dict_stays_empty_on_a_valid_save |
| 89 | handle_post({"theme": "white", "quiet_hours_start": ""}, ctx, errors=d) rejects the whole save, writes nothing (the theme must not persist either), and reports the error on quiet_hours_start alone | ported | companion/test_config_page_03.py::test_handle_post_empty_quiet_hours_start_writes_nothing |
| 90 | config_page._QUIET_HOURS_TIME_RE agrees with server.device_config.save_device_config()'s own HH:MM shape gate over the table ""/"7:00"/"07:00"/"24:00"/"abc"/"23:59"/"00:00" | ported | companion/test_config_page_03.py::test_local_quiet_hours_regex_agrees_with_save_device_config |
| 91 | render(ctx) with no new arguments is byte-identical to render(ctx, errors=None, submitted=None) and contains no field-error markup | ported | companion/test_config_page_03.py::test_render_no_new_args_byte_identical_and_no_field_error_markup |
| 92 | render(ctx, errors={"wake_interval_s": "msg"}, submitted={"wake_interval_s": "7"}) renders the message once, echoes value="7" back into the input, and sets aria-invalid plus a matching aria-describedby | ported | companion/test_config_page_03.py::test_render_wake_interval_error_shows_message_value_and_aria |
| 93 | a submitted theme id is rendered as the CHECKED radio even when it differs from the stored theme (D-07 repopulation) | ported | companion/test_config_page_03.py::test_render_submitted_theme_id_checked_even_when_differs_from_stored |
| 94 | both quiet-hours time inputs carry required in the rendered Settings page | ported | companion/test_config_page_03.py::test_render_both_quiet_hours_time_inputs_carry_required |
| 95 | _calendar_connection_html(..., errors={"calendar_url": "msg"}) renders the error message under the field while the write-only field itself still carries no value attribute at all (D-07/T-19-12/D-13, retargeted after _calendar_connection_html()'s retirement, 30-06-PLAN.md Task 3) | ported | companion/test_config_page_03.py::test_calendar_connection_url_error_never_echoes_the_submitted_secret |
| 96 | companion/static/style.css styles .field-error using the existing --color-status-error token (cross-file DOM contract guard) | ported | companion/test_config_page_03.py::test_style_css_styles_field_error |
| 97 | a rejected save still returns FLASH_SAVE_FAILED from handle_post() when no errors dict is passed (the legacy contract is intact) | ported | companion/test_config_page_03.py::test_handle_post_rejected_save_without_errors_arg_still_returns_save_failed |
| 98 | render() emits no action pointing at the retired separate LED form path (D-05) | ported | companion/test_config_page_03.py::test_render_has_no_action_pointing_at_retired_led_route |
| 99 | companion.pages.config_page exposes neither led_fieldset, led_section, nor handle_led_post (all three retired, D-05) | ported | companion/test_config_page_03.py::test_config_page_exposes_no_retired_led_symbols |
| 100 | companion.pages.config_page exposes none of THEME_HELPER_TEXT/THEME_SECTION_DESCRIPTION/RUNWAY_HELPER_TEXT/RUNWAY_SECTION_DESCRIPTION/LED_HELPER_TEXT (all five retired, quick task 260901-re6) | ported | companion/test_config_page_03.py::test_config_page_exposes_no_retired_helper_or_description_symbols |
| 101 | runway_images_available() returns the empty set when the image directory has no files | ported | companion/test_config_page_03.py::test_runway_images_available_empty_dir_yields_empty_set |
| 102 | runway_images_available() returns exactly {'3'} when only runway-3.png exists | ported | companion/test_config_page_03.py::test_runway_images_available_detects_single_present_file |
| 103 | runway_images_available() returns the empty set (does not raise) when image_dir does not exist | ported | companion/test_config_page_03.py::test_runway_images_available_missing_dir_yields_empty_set_no_raise |
| 104 | runway_images_available() ignores files that are not RUNWAY_IDS members, proving it is registry-bounded not directory-listing-bounded | ported | companion/test_config_page_03.py::test_runway_images_available_bounded_by_registry_not_directory_listing |
| 105 | runway_fieldset(images_available={'3'}) emits exactly one <img, for runway 3 only | ported | companion/test_config_page_03.py::test_runway_fieldset_emits_img_only_for_available_runway |
| 106 | runway_fieldset(images_available=set()) renders zero <img tags and all three number/heading labels (D-03 graceful fallback) | ported | companion/test_config_page_03.py::test_runway_fieldset_graceful_fallback_no_images |
| 107 | render() forwards ctx['runway_images'] to runway_fieldset() rather than relying on the parameter default | ported | companion/test_config_page_03.py::test_render_forwards_ctx_runway_images_key |
| 108 | dirty-state.js references DIRTY_SECTION_ATTR again (dirtySectionLabels() restored) but carries neither the retired dirty-ready nor dirty-shown marker, delegates BOTH change AND input at document level gated on e.target.form === form with no surviving form.addEventListener("change"/"input" registration (B1), and contains none of innerHTML/let /const /=>/backtick (CFG-77/CFG-78, 28-08-PLAN.md Task 3) | ported | companion/test_config_page_03.py::test_dirty_state_js_delegates_change_and_input_at_document_level_and_has_no_forbidden_syntax |
| 109 | the live theme preview CROSSFADES rather than cuts: .theme-live-preview__image declares an opacity transition at var(--motion-fast) on its own base rule, a .theme-live-preview__image--swapping class carries the opacity-0 half, theme-preview.js drives that same class literal from transitionend and the image's own load/error (never a timer) while consulting the computed opacity so a swap can never wait on a transition that never runs, and T8's window.SkyPaneLivePreview.refresh() survives (D3/CFG-32, 23-10-PLAN.md Task 2) | ported | companion/test_config_page_03.py::test_live_preview_crossfades_through_one_class_shared_by_css_and_js |
| 110 | dirty-state.js registers a beforeunload listener whose body references countDifferences and sets returnValue/calls preventDefault, and a submit listener clears the guard; contains none of innerHTML/let /const /=>/backtick | ported | companion/test_config_page_03.py::test_dirty_state_js_beforeunload_guard_reuses_count_differences |
| 111 | dirty-state.js references config_page.QUIET_HOURS_PRESET_ATTR's literal value and the three data-preset-* attribute names, and contains none of innerHTML/let /const /=>/backtick | ported | companion/test_config_page_03.py::test_dirty_state_js_references_quiet_preset_attrs |
| 112 | style.css carries NO rule selector referencing STATIC_SAVE_FALLBACK_ATTR any more — the hide rule is retired outright, its button now the restored bar's own visible Save — while the B1/P0 contract and the dated 27-03/28-08 SUPERSEDED paragraphs all survive in writing (CFG-77/CFG-78, 28-08-PLAN.md Task 2) | ported | companion/test_config_page_03.py::test_style_css_carries_no_hide_rule_for_static_save_fallback_attr |
| 113 | style.css carries no live RULE selector for the retired .save-status auto-save status region (comments stripped before scanning) while the comment prose narrating its own retirement survives verbatim — the .save-status half of the orphan-rule clause the STATIC_SAVE_FALLBACK_ATTR check above does not already cover, re-derived on the finished tree rather than pasted from planning time (CFG-78, 28-09-PLAN.md Task 1) | ported | companion/test_config_page_03.py::test_style_css_carries_no_rule_for_the_retired_save_status_region |
| 114 | style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex display), .settings-checkbox input[type="checkbox"] (cleared min-height), and .theme-chip-grid/.theme-chip/.theme-chip--selected/.theme-chip__preview (flex display, card surface + 160px width, accent border, 56px preview band) - the selectors config_page.py's new markup depends on | ported | companion/test_config_page_03.py::test_style_css_carries_theme_status_runway_row_and_settings_checkbox_selectors |
| 115 | every theme chip's <img src> points at THEME_PREVIEW_ROUTE_PREFIX + the theme's own registry id, for every entry in device_config.THEME_IDS (06.6.4.1.1-05) | ported | companion/test_config_page_03.py::test_theme_chip_preview_src_points_at_the_real_route_prefix_for_every_theme |
| 116 | every theme chip carries exactly two .theme-chip__dot swatches whose inline background values equal _palette_hex() computed from that theme's own departing_index/arriving_index (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by 21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired) | ported | companion/test_config_page_03.py::test_theme_chip_swatch_dots_carry_real_palette_hex_values |
| 117 | every theme chip's radio carries class="visually-hidden" (never display:none) and every chip carries a .theme-chip__check glyph with visually-hidden "Selected" text, present on all chips regardless of selection (06.6.4.1.1-05, retargeted onto _theme_chip_grid_html() directly by 21-05-PLAN.md Task 1 D-06 once theme_fieldset() is retired) | ported | companion/test_config_page_03.py::test_theme_chip_radio_hidden_and_check_glyph_present_on_every_chip |
| 118 | the arrivals row carries a leading Same-as-departures option submitting the empty string (class="leading-option", form=settings-form), and no checkbox-based override control exists anywhere on the page (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired _frame_colours_arrivals_grid_carries_leading_chip_no_checkbox) | ported | companion/test_config_page_03.py::test_aspect_arrivals_row_carries_leading_option_no_checkbox |
| 119 | a stored theme_arriving override pre-selects the OVERRIDE (not Same-as-departures, not the departures theme) in the arrivals row, names the override's own label in the row's summary meta, and leaves the calendar row's own Same-as-departures state unaffected in the same render (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired _frame_colours_arrivals_override_preselects_the_override_not_same_as_departures) | ported | companion/test_config_page_03.py::test_aspect_arrivals_override_preselects_the_override_not_same_as_departures |
| 120 | handle_post with a valid theme_arriving id persists it, with no checkbox field involved (D-06/D-09, retargeted from the retired arrivals-override checkbox) | ported | companion/test_config_page_03.py::test_handle_post_theme_arriving_valid_id_persists_chosen_id |
| 121 | handle_post with theme_arriving='' clears a previously-set override back to None (D-06/D-09, retargeted from the retired arrivals-override checkbox's own absence) | ported | companion/test_config_page_03.py::test_handle_post_theme_arriving_empty_string_clears_previous_override |
| 122 | handle_post with calendar_theme_id='' saves and reads back as None, mirroring theme_arriving's own empty-string clear signal (D-06/D-09) | ported | companion/test_config_page_03.py::test_handle_post_calendar_theme_id_empty_string_saves_as_none |
| 123 | handle_post still rejects a crafted non-member theme_arriving/calendar_theme_id value (a plain invalid id, a bare space, a near-miss uppercase/trailing-space variant) and writes nothing — the empty-string exemption does not widen the gate to anything else (D-09/Pitfall 1) | ported | companion/test_config_page_03.py::test_handle_post_crafted_non_member_theme_and_calendar_values_still_rejected[theme_arriving-invalid-id] |
| 124 | handle_post with a non-member theme_arriving (a plain invalid id, a path-traversal-shaped payload, and a SQL-shaped payload) rejects the whole submission and writes nothing — '' is explicitly exempted from this rejection (D-09) | ported | companion/test_config_page_03.py::test_handle_post_nonmember_theme_arriving_rejected[plain-invalid-id] |
| 125 | a post carrying only theme_arriving still carries the existing theme/runway forward unchanged (retargeted from the retired arrivals-override checkbox, D-09) | ported | companion/test_config_page_03.py::test_handle_post_theme_arriving_partial_post_still_carries_other_fields |
| 126 | the clearable contract (15-VALIDATION.md row 7): a save with a chosen arrivals theme persists it, then a save with theme_arriving='' clears it back to None while every other setting survives unchanged (D-06/D-09, retargeted from the retired arrivals-override checkbox's own absence) | ported | companion/test_config_page_03.py::test_theme_arriving_clearable_contract_full_round_trip |
| 127 | the rendered Settings page contains no <fieldset> and no <legend>, and exactly five data-dirty-section groups (Runway/Diagnostic LED/Quiet hours/Wake interval/Notifications — Theme's own entry retired along with theme_fieldset(), 21-05-PLAN.md Task 1 D-06; Calendar's own entry retired from this legacy scope by 21-07-PLAN.md Task 1 D-13/Pitfall 2; Display's own entry retired outright by 22-05-PLAN.md Task 1 X1/D-04/D-12.1) | ported | companion/test_config_page_03.py::test_settings_page_has_zero_fieldsets_and_five_dirty_sections |
| 128 | both .runway-card--selected and .theme-chip--selected .theme-chip__body carry a 12%-accent background wash (color-mix), matching .theme-form .theme-option--active's established active-state idiom, added alongside (not replacing) their check glyph and their now-constant 1px border, whose 2px accent signal moved to an inset ring (06.6.4.1.1-06, retargeted by 22-15-PLAN.md Task 1 for T6) | ported | companion/test_config_page_03.py::test_selected_runway_card_and_theme_chip_carry_a_background_wash |
| 129 | the strong selected-card treatment (border, wash, check glyph, and a D-03a hover restore) is keyed to live :has(input:checked) state inside one @supports selector(:has(*)) block, for both .theme-chip and .runway-card, with every pre-existing --selected fallback rule surviving verbatim (quick task 260904-bbi) — and, since 23-10-PLAN.md Task 1 (D3/CFG-32), selection ANSWERS: a fast transition naming the transform, the border colour, the shadow and the wash is declared on each selectable surface's BASE rule, the live rules and their --selected fallbacks carry the SAME scale, saved-but-not-live clears it, and the ONE feature-query block declares no transition at all — asserted together so moving one inside fails once | ported | companion/test_config_page_03.py::test_strong_selected_treatment_is_keyed_to_the_live_checked_radio |
| 130 | the destructive Disconnect control keeps its secondary, element-qualified specificity AND its source-order relationship against button[type="submit"] (T2/T15, re-proven as a RELATIONSHIP rather than a bare presence check, since the recorded defect was a rule whose every declaration was dead for a phase and a half), and the selected-chip mechanism is re-keyed from the retired 'input:checked + .frame-colours__row' sibling selector to .palette-chip:has(input:checked) inside the file's one @supports selector(:has(*)) block, carrying the accent border, inset ring, 12%% wash and check-glyph declarations (T6, 30-07-PLAN.md Task 3) | ported | companion/test_config_page_03.py::test_destructive_disconnect_is_secondary_and_selection_is_free_and_focusable_after_the_accordion_rebuild |
| 131 | style.css carries neither retired Calendar-card fusion selector (.page-section:has(+ .calendar-disconnect-form), .calendar-disconnect-form) anywhere (D-13/R-08/Pitfall 2) | ported | companion/test_config_page_03.py::test_calendar_fusion_css_retired_from_the_stylesheet |
| 132 | the saved-but-no-longer-live --selected card degrades to an accent-free dashed 70%-muted ring with its wash/check glyph cleared and a "Current" ::after tag whose text is read from the server-rendered, translated data-current-label attribute (exactly 2 occurrences site-wide, zero hard-coded English declarations, zero French copy in the stylesheet), reusing the established muted-text strength rather than inventing a new one (quick task 260904-bbi; retargeted by 22-10-PLAN.md Task 1, T10) | ported | companion/test_config_page_03.py::test_saved_but_unchecked_card_degrades_to_a_quiet_current_marker |
| 133 | style.css declares .section-caption (70% muted color-mix) AND the restored .dirty-bar — fixed-positioned at both breakpoints, its [hidden] override and its Cancel button's own quiet-wash override all present (CFG-77/CFG-78, 28-08-PLAN.md Task 2) | ported | companion/test_config_page_03.py::test_style_css_carries_section_caption_and_the_restored_dirty_bar_rules |
| 134 | the @keyframes skypane-bar-arrive block — kept deliberately orphaned by 27-04 specifically so a future restoration would not need to move the file's pinned @keyframes count — is REFERENCED again by the restored .dirty-bar base rule's own animation: declaration, reused rather than reinvented (CFG-77/CFG-78, 28-08-PLAN.md Task 2) | ported | companion/test_config_page_03.py::test_skypane_bar_arrive_keyframes_is_referenced_again_by_the_restored_bar |
| 135 | dirty-state.js contains no hardcoded occurrence of "Theme", "Runway", or "Diagnostic LED" (labels come from the DOM) | ported | companion/test_config_page_03.py::test_dirty_state_js_has_no_hardcoded_section_names |
| 136 | dirty-state.js is network-free and poll-free again (no fetch(/XMLHttpRequest/setInterval/requestAnimationFrame anywhere) with exactly ONE setTimeout in the whole file — a literal setTimeout(fn, 0) sitting INSIDE the form's own reset-event handler, never cancelling that event's own default action — and the file's header states both the standing constraint AND this one named exception in the same breath (CFG-77/CFG-78, 28-08-PLAN.md Task 3) | ported | companion/test_config_page_03.py::test_dirty_state_js_is_network_free_again_with_one_named_timer_exception |
| 137 | the Aspect card's full shape, as a relationship rather than a list of endpoints: one card after the Look section intro, its four accordion rows' data-usage values in COLOUR_USAGES' own locked order, exactly one row open (departures), only the last row secondary, exactly one .palette grid per theme row and none in the rules row, zero occurrences of any retired mechanism's markup, and no section-caption paragraph immediately after the heading (CFG-85, 30-05-PLAN.md Task 1, replacing the retired _frame_colours_card_full_shape_checklist) | ported | companion/test_config_page_03.py::test_aspect_card_full_shape_checklist |
| 138 | render() places the Aspect card, holding the rules row, after the settings </form> and before the Calendar card, with every theme/theme_arriving/calendar_theme_id radio still carrying form=settings-form (Phase 15 D-10, replacing the retired _rules_section_renders_inside_frame_colours_after_form) | ported | companion/test_config_page_03.py::test_rules_row_renders_inside_aspect_after_form |
| 139 | the rules section renders the empty state with no rules, and the empty state is replaced by the .rule-list once a rule exists (D-15c/d, retargeted from the retired cards-then-table shape) | ported | companion/test_config_page_03.py::test_rules_section_empty_state_then_list_once_a_rule_exists |
| 140 | a seeded set of rules of every kind renders most-specific first (callsign, then hex, then prefix), alphabetically within each kind (D-15c) | ported | companion/test_config_page_03.py::test_rules_list_orders_most_specific_first_then_alphabetically |
| 141 | every rules-editor copy string — heading, caption, field labels, kind labels/titles, empty-state heading/body, and the How-rules-combine disclosure — appears escaped-verbatim, matching 20-UI-SPEC.md's Copywriting Contract byte for byte (30-05-PLAN.md Task 3, replacing the retired _rules_copy_appears_escaped_verbatim) | ported | companion/test_config_page_03.py::test_aspect_rules_copy_appears_escaped_verbatim |
| 142 | the rules row label equals 21-UI-SPEC.md's locked "Per-flight rules" text exactly, and its empty-state meta reads FRAME_COLOURS_RULES_EMPTY_META's real value, never ROADMAP's own paraphrase (D-06/D-07, 30-05-PLAN.md Task 2, replacing the retired _frame_colours_rules_row_label_locked_verbatim) | ported | companion/test_config_page_03.py::test_aspect_rules_row_label_locked_verbatim |
| 143 | the Flight-colours section carries no <select>, and its add form's three rule_kind radios carry the three kind ids and the three technical titles, exactly one checked by default (D-15b) | ported | companion/test_config_page_03.py::test_rules_no_select_and_three_named_radios_one_checked |
| 144 | a rendered rule row carries a .banner__pill kind badge with the plain-language word, a computed _palette_hex() swatch dot, and a data-confirm Remove form (D-15c) | ported | companion/test_config_page_03.py::test_rules_row_carries_pill_badge_and_confirmed_remove_form |
| 145 | the empty state is muted sans copy in .empty-state-plain and carries no <h*> heading element, never the serif empty_state() heading (D-15d) | ported | companion/test_config_page_03.py::test_rules_empty_state_carries_no_heading_element |
| 146 | up to five suggestion chips render with data-kind/data-value from recent runway events, and none render when there are no events (D-15e) | ported | companion/test_config_page_04.py::test_rules_suggestion_chips_present_with_data_and_absent_with_no_events |
| 147 | a plain Display render always carries the full 'How rules combine' and Calendar 'How it works' <details> disclosures, never a collapsed one-sentence variant (D-17) | ported | companion/test_config_page_04.py::test_plain_render_carries_both_disclosures_in_full_never_collapsed |
| 148 | the rules panel, inside the Frame colours card, carries no data-dirty-section attribute of its own — the card's OWN outer wrapper carries the one attribute for all four usages, exactly like the Poll section carries none | ported | companion/test_config_page_04.py::test_rules_section_carries_no_dirty_section_attr |
| 149 | a French Display render of the Frame colours card's rules row/panel shows 'Règles par vol' and 'Ajouter la règle' (D-05, retargeted from the retired Flight-colours heading) | ported | companion/test_config_page_04.py::test_rules_french_render_shows_french_row_label_and_button |
| 150 | with no calendar configured, render() emits the 'Not connected' verdict with an empty detail (D-14b) | ported | companion/test_config_page_04.py::test_calendar_status_not_configured_is_exclusive |
| 151 | with a calendar configured and no fetch attempt recorded yet, render() emits the 'Connected' verdict with an empty detail (D-14b) | ported | companion/test_config_page_04.py::test_calendar_status_configured_pending_is_exclusive |
| 152 | with a calendar configured, an attempt recorded, and no usable sync, render() emits the mapped 'The feed could not be read' detail — never an exception's own text (D-14b/T-20-30) | ported | companion/test_config_page_04.py::test_calendar_status_configured_fetch_failed_is_exclusive |
| 153 | with a calendar configured and a last_synced_at present, render() emits the 'Connected' verdict with a detail carrying the entry count and a relative-age fragment, never a bare ISO string (D-14b) | ported | companion/test_config_page_04.py::test_calendar_status_configured_synced_is_exclusive_with_relative_age |
| 154 | with a calendar configured and a last_synced_at that is present but unparseable, the empty detail is used rather than a fabricated time (D-14b) | ported | companion/test_config_page_04.py::test_calendar_status_unparseable_synced_falls_back_to_no_detail |
| 155 | the status detail template, the fetch-failed sentence, the Connect button text, and the Replace-URL disclosure summary are each a contiguous substring of 20-UI-SPEC.md, so a paraphrase fails rather than merely looking different (D-14a..c) | ported | companion/test_config_page_04.py::test_calendar_copy_fidelity_locked_to_the_phase_20_wording |
| 156 | the merged card's own two new short button-text constants (the connected-state Replace button, the small grey Disconnect button) are each a contiguous substring of 21-UI-SPEC.md (D-13/D-14) | ported | companion/test_config_page_04.py::test_calendar_merged_button_copy_locked_to_the_phase_21_wording |
| 157 | the Calendar card's copy carries none of the phase's banned affirmative real-time-awareness or crew-role vocabulary, while still carrying the mandated negated 'does not track' construction verbatim | ported | companion/test_config_page_04.py::test_calendar_forbidden_vocabulary_absent |
| 158 | with the calendar secret file holding a URL carrying a distinctive token, render() emits the masked host + ellipsis fragment but never the token, the path segment, the query-parameter name, or the whole raw URL (T-16-SECRET, extended by 21-07-PLAN.md Task 2 for the new masked-URL line, D-14/R-10) | ported | companion/test_config_page_04.py::test_calendar_secret_never_reaches_render_function |
| 159 | a populated calendar registry (real-shaped routes/airline codes) never surfaces any airport code or airline code, while the status row's own entry count DOES appear (D-14b; 16-UI-SPEC.md D-01's code-isolation half carried forward, its count-prohibition half retired) | ported | companion/test_config_page_04.py::test_calendar_no_preview_no_count_in_rendered_page |
| 160 | with both a populated calendar registry and one hand-added colour rule, the rendered rules list shows exactly the manual rule and no calendar-sourced row (16-VALIDATION.md registry row, D-01) | ported | companion/test_config_page_04.py::test_calendar_d01_registry_entries_never_appear_in_rules_list |
| 161 | the calendar row's palette carries one leading Same-as-departures option plus exactly one entry per registered theme, in registry order, with no id attribute of its own (D-06/D-09, 30-05-PLAN.md Task 1, replacing the retired _calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order) | ported | companion/test_config_page_04.py::test_aspect_calendar_row_palette_populated_in_order |
| 162 | with a saved calendar_theme_id, that chip's radio carries checked and no other calendar_theme_id radio (including the leading 'Same as departures' chip) does (D-06/D-09) | ported | companion/test_config_page_04.py::test_calendar_theme_chip_grid_saved_value_is_checked |
| 163 | with no saved calendar_theme_id, only the leading 'Same as departures' chip is checked — never the chip matching the currently-selected base theme (D-06/D-09, replacing the retired pre-D-09 default-to-base-theme behaviour) | ported | companion/test_config_page_04.py::test_calendar_theme_chip_grid_same_as_departures_checked_when_unset |
| 164 | handle_post with a valid calendar_theme_id persists it and carries every other field forward | ported | companion/test_config_page_04.py::test_handle_post_calendar_theme_id_valid_persists_and_carries_forward |
| 165 | handle_post with a non-member calendar_theme_id (a plain invalid id, a path-traversal-shaped payload, and a SQL-shaped payload) rejects the whole submission and writes nothing — '' is explicitly exempted from this rejection (D-09) | ported | companion/test_config_page_04.py::test_handle_post_calendar_theme_id_adversarial_rejected[invalid-id] |
| 166 | handle_post with no calendar_theme_id field at all leaves an already-saved value untouched | ported | companion/test_config_page_04.py::test_handle_post_calendar_theme_id_absent_leaves_unchanged |
| 167 | the write-only calendar_url field renders in the merged _calendar_connection_html()'s own markup for both the connected and not-connected states and never carries a value attribute (D-13/D-14, retargeted after calendar_connect_section()'s retirement) | ported | companion/test_config_page_04.py::test_calendar_connect_field_never_carries_value_in_either_state |
| 168 | the merged _calendar_connection_html() wraps its connect form in <details class=calendar-url-disclosure> 'Replace the feed URL' only when configured, and renders it unwrapped, posting to CALENDAR_CONNECT_ROUTE, when not (D-13/D-14, retargeted after calendar_connect_section()'s retirement) | ported | companion/test_config_page_04.py::test_calendar_connect_wraps_in_details_only_when_configured |
| 169 | the merged _calendar_connection_html(), called directly rather than through render(), never emits the token, host, path segment, query-parameter name, or whole URL of a configured calendar, even though it now also renders the connect/replace form and the disconnect button (T-17-SECRET, retargeted after calendar_connect_section()'s retirement) | ported | companion/test_config_page_04.py::test_calendar_containment_at_the_renderer_five_needles |
| 170 | _calendar_connection_html() renders no calendar_disconnect checkbox in any of its four states (D-08/A-26: disconnecting is now its own standalone form, not an in-form checkbox) | ported | companion/test_config_page_04.py::test_calendar_disconnect_checkbox_never_appears_in_calendar_connection |
| 171 | the merged _calendar_connection_html() renders its disconnect form only when the calendar is connected or drifted, posting to CALENDAR_DISCONNECT_ROUTE with a hidden, empty, data-confirm-field-carrying confirm field, alongside a visible small Disconnect button cross-submitting via form= (D-08/A-26/D-14, retargeted after calendar_disconnect_section()'s retirement) | ported | companion/test_config_page_04.py::test_calendar_disconnect_form_appears_only_when_expected |
| 172 | Display's Look supersection carries exactly ONE data-dirty-section card (named 'Aspect'), in both the connected and not-connected states — down from the two ('Aspect'/'Calendar') it carried before the calendar's connection block folded into the Aspect card's own Calendar row (CFG-85, replacing the retired data-dirty-section="Calendar" count check, whose own property this merge changes rather than merely relocates) | ported | companion/test_config_page_04.py::test_look_supersection_carries_exactly_one_dirty_section_named_aspect |
| 173 | the merged _calendar_connection_html()'s own return value (the card plus its data-only disconnect-form sibling) never nests one <form> inside another, in any of its four distinguishable states (D-13/Pitfall 2) | ported | companion/test_config_page_04.py::test_calendar_connection_never_nests_a_form_inside_another_in_either_state |
| 174 | the calendar connection block renders inside the Calendar row, after that row's own palette, after the settings form's own closing tag and the Aspect card's own heading, still under the Aspect card's own dirty-section tracking attribute — with the Disconnect button inside the row and the disconnect form OUTSIDE the card, the button's form= naming that exact sibling (CFG-85, replacing the retired _calendar_placement_after_display_form_close_with_dirty_attr) | ported | companion/test_config_page_04.py::test_calendar_connection_placement_inside_aspect_after_display_form_close_with_dirty_attr |
| 175 | the calendar row renders no inline event-handler attribute and no <script> tag, and every calendar_theme_id radio in its palette cross-submits into the settings form via form=settings-form (CFG-85, replacing the retired calendar-card no-inline-JS/chip-grid cross-submits check) | ported | companion/test_config_page_04.py::test_calendar_row_no_inline_js_and_palette_cross_submits_form |
| 176 | calendar_disconnect_confirm_page() renders a form posting to CALENDAR_DISCONNECT_ROUTE with the confirm field pre-set to the accepted value, plus a plain cancel link to Display (D-08/A-26, retargeted from Device by 20-07-PLAN.md Task 1/D-11) | ported | companion/test_config_page_04.py::test_calendar_disconnect_confirm_page_posts_back_with_confirm_preset |
| 177 | on the Display scope, the calendar disconnect form's opening tag appears after the settings form's own closing tag — it is a sibling, never a descendant (D-08/A-26, retargeted from Device by 20-07-PLAN.md Task 1/D-11, and again by 21-07-PLAN.md Task 1/D-14 for the id-first attribute order) | ported | companion/test_config_page_04.py::test_calendar_disconnect_form_is_not_inside_settings_form_on_display_scope |
| 178 | on the Display scope, the calendar connect/replace form's own <form> opening tag renders immediately after the Calendar row and strictly before the Runway card's own radio input, never after the whole page's groups (Polish fix 4, D-14c) | ported | companion/test_config_page_04.py::test_calendar_connect_form_appears_before_the_runway_card_on_display_scope |
| 179 | the disconnect form is absent when the calendar is neither configured nor drifted, and absent from the Device scope, which never renders the Calendar group at all (D-08/A-26, retargeted from Display by 20-07-PLAN.md Task 1/D-11) | ported | companion/test_config_page_04.py::test_calendar_disconnect_form_absent_when_not_configured_or_on_device_scope |
| 180 | with the stored calendar link's permissions drifted, render() emits the 'Not connected' verdict with the drift detail sentence — the drift branch, checked before 'not configured', still wins (D-02 ordering, D-14b) | ported | companion/test_config_page_04.py::test_calendar_status_drift_is_exclusive_and_precedes_not_configured |
| 181 | the permission-drift status string names the remedy (paste the feed URL again) and names no path separator, filename, or part of a URL (D-02, 17-CONTEXT.md prohibitions) | ported | companion/test_config_page_04.py::test_calendar_status_drift_names_remedy_and_nothing_forbidden |
| 182 | the single most important check in this plan (D-07): a form that changes an unrelated setting and carries an empty calendar_url field with no checkbox, submitted twice in a row via handle_post(), leaves a configured calendar and its fetched entries completely untouched | ported | companion/test_config_page_04.py::test_handle_post_empty_calendar_field_with_no_checkbox_is_a_no_op_across_two_unrelated_saves |
| 183 | handle_post with the disconnect checkbox at its expected value succeeds, disconnects the calendar, and empties its fetched-entries registry (D-04) | ported | companion/test_config_page_04.py::test_handle_post_disconnect_clears_url_and_registry |
| 184 | handle_post with a different non-empty URL stores the new URL and clears the previous calendar's fetched-entries registry (D-05) | ported | companion/test_config_page_04.py::test_handle_post_replace_url_stores_new_value_and_clears_registry |
| 185 | handle_post with a non-empty URL together with the disconnect checkbox, plus a changed unrelated setting, rejects the whole save - neither the calendar nor the unrelated setting is written (D-07 contradiction, all-or-nothing) | ported | companion/test_config_page_04.py::test_handle_post_contradiction_rejects_whole_save_including_unrelated_field |
| 186 | handle_post with a crafted calendar_disconnect value rejects the whole save - neither the calendar nor the unrelated setting is written | ported | companion/test_config_page_04.py::test_handle_post_crafted_disconnect_value_rejects_whole_save |
| 187 | handle_post with a calendar_url longer than CALENDAR_URL_MAX_LEN rejects the whole save - neither the calendar nor the unrelated setting is written | ported | companion/test_config_page_04.py::test_handle_post_overlength_url_rejects_whole_save |
| 188 | scope_groups() renders the display/device pages from companion/screens.py's per-screen declaration — disjoint, together equal to the legacy single page — and unknown screen ids fall back to the default screen | ported | companion/test_config_page_04b.py::test_scope_groups_follow_the_screen_registry |
| 189 | config_page.led_group() renders exactly ONE control for the setting — a server-rendered role=switch whose aria-checked is the stored value in both directions, named by the setting, described by its state span AND the group's own caption, attached across the DOM to its own /quick/led form — and no input[name="led_enabled"] checkbox survives beside it (D2/CFG-36, X1/D-04, 23-07-PLAN.md Task 2) | ported | companion/test_config_page_04b.py::test_the_led_group_renders_one_switch_and_no_surviving_checkbox |
| 190 | config_page.quick_led_form_html() is an EMPTY form carrying its own method/action/id, the D-04 handshake attribute and the two hidden fields with the posted state inverted from the stored one — and render() places it as a SIBLING of the settings form on the Device scope and not at all on Display (D2/CFG-36, 23-07-PLAN.md Task 2) | ported | companion/test_config_page_04b.py::test_the_quick_led_form_is_a_sibling_of_the_settings_form |
| 191 | scope_groups(SCOPE_DISPLAY) contains Runway and Calendar, and scope_groups(SCOPE_DEVICE) contains neither (D-10/D-11) | ported | companion/test_config_page_04b.py::test_display_scope_carries_runway_and_calendar_device_carries_neither |
| 192 | the Display scope renders exactly three section-intro headings, in the locked Look/What it watches/When it is on order, and the Device scope renders exactly three of its own, in the locked When it wakes/How it tells you/When you can't wait order (D-12, retargeted by 28-04-PLAN.md Task 1/CFG-72 from 'the Device scope renders none') | ported | companion/test_config_page_04b.py::test_display_render_carries_three_section_intros_in_locked_order |
| 193 | every grouped card the Display scope renders under one of its three supersections carries a --nested modifier class — down to 3 occurrences (Aspect's page-section--nested, Runway's and Quiet hours' theme-status--nested) now that the Calendar card's own separate page-section--nested wrapper is retired (D-12, CFG-85) | ported | companion/test_config_page_04b.py::test_every_grouped_card_under_a_display_supersection_carries_nested_class |
| 194 | the Display scope's rendered <h2> order is exactly Look, Aspect, What it watches, Runway, When it is on, Quiet hours — the separate Calendar heading this order used to also name is retired outright now that its connection block folds into the Aspect card's own Calendar row — and every calendar_theme_id radio still carries a form="settings-form" attribute (CFG-85, replacing the retired _display_h2_order_matches_d12_after_calendar_placement_fix) | ported | companion/test_config_page_04b.py::test_display_h2_order_matches_the_merged_aspect_card_placement |
| 195 | the title-form inventory, re-run after the calendar merge: both settings routes' h2.text-heading instances count and classify as 6 settings-card titles (form A, 3 on Device + 3 on Display, down from 4 now that Calendar's own separate heading is retired) + 3 supersection intros (form B) + 2 unrelated headings, with the counts re-derived by RUNNING rather than restated as the pre-merge 8/4/3/1 literal, and the two label vocabularies still never overlapping (CFG-85, replacing the retired _title_form_inventory_classifies_every_h2_text_heading_on_both_routes) | ported | companion/test_config_page_04b.py::test_title_form_inventory_classifies_every_h2_text_heading_on_both_routes_after_the_merge |
| 196 | none of the settings-card builder functions (_aspect_card_html/runway_fieldset/led_group/quiet_hours_group/wake_interval_group/notifications_group — one fewer than before the merge, since _aspect_card_html now covers what _frame_colours_card_html and the calendar card's own former builder function used to split between them) ever calls layout.section_intro_html() for their own heading — the losing form (a card title produced through the supersection-intro shape) is ZERO, enforced at the source level, its allowlist length checked against the real builder-name set rather than a literal (CFG-85, replacing the retired-and-relanded _no_card_builder_function_ever_calls_section_intro_html) | deleted | S: asserted source text (ast.parse over config_page.py, walking for section_intro_html call sites); the rendered classification this AST check protects is already exhaustively covered by row 195's title-form inventory test (counts of data-dirty-section vs section-intro headings, form A/B/unclassified); no behaviour beyond what render() output already proves |
| 197 | the cheap structural guard, NOT the real proof (that is test_browser_ux.py's cross-page getComputedStyle comparator): the Device scope's rendered output wraps all four of its settings cards with the --nested modifier (three theme-status--nested, one page-section--nested) and carries zero unmodified settings-card wrappers of either base class (CFG-72, 28-04-PLAN.md Task 2) | ported | companion/test_config_page_04b.py::test_device_scope_wraps_all_four_settings_cards_with_the_nested_modifier |
| 198 | a Display render contains exactly one action="/quick/display" form and one action="/quick/quiet-hours" form (D-19) | ported | companion/test_config_page_04b.py::test_display_render_carries_exactly_two_quick_action_forms |
| 199 | neither instant-switch form is a descendant of <form id=settings-form> — both render in the shared Frame strip, before the settings form even opens (D-01/D-02/Pitfall 1) | ported | companion/test_config_page_04b.py::test_quick_action_forms_are_not_descendants_of_settings_form |
| 200 | the rendered Display page contains no <form> nested inside another <form> anywhere (D-19/Pitfall 1, the required structural fix) | ported | companion/test_config_page_04b.py::test_display_render_carries_no_form_nested_inside_a_form |
| 201 | a Display render carries exactly one .quick-action--on/--off pair per switch, both inside .frame-strip (D-01/D-02) | ported | companion/test_config_page_04b.py::test_display_render_has_exactly_one_quick_action_pair_inside_the_strip |
| 202 | the Quiet hours card carries no quick-action markup any more — its switch moved into the shared Frame strip (D-01/D-02); the Screen on/off card this check used to also cover is retired outright by 22-05-PLAN.md Task 1 (X1/D-04/D-12.1) | ported | companion/test_config_page_04b.py::test_schedule_cards_carry_no_quick_action_markup |
| 203 | both instant-switch forms on Display carry a return_to hidden input whose value is the Display route (R-02) | ported | companion/test_config_page_04b.py::test_quick_action_forms_carry_return_to_the_display_route |
| 204 | the Frame strip renders immediately after the page header and before the first section-intro on Display (D-02) | ported | companion/test_config_page_04b.py::test_frame_strip_renders_after_header_before_first_section_intro |
| 205 | the two remaining scheduled inputs (quiet_hours_start, quiet_hours_end) carry form="settings-form" via the SETTINGS_FORM_ID constant (D-19), and neither display_enabled nor quiet_hours_enabled renders on the Display page any more (22-05-PLAN.md Task 1, X1/D-04/D-12.1) | ported | companion/test_config_page_04b.py::test_two_scheduled_inputs_carry_form_settings_form |
| 206 | the shared "Applies the next time the frame wakes up." sentence appears exactly twice on the Display page — once per Frame-strip instant switch, and no longer a third time under the Quiet hours card's own caption now that CFG-79 confines it to one place per page (29-05-PLAN.md Task 2; widened to three by 22-05-PLAN.md Task 2 D-04, narrowed back here) | ported | companion/test_config_page_04b.py::test_applies_next_wake_sentence_appears_exactly_twice |
| 207 | a POST through handle_post() with the same field set as before the Task 2 restructure still produces the same saved config (D-13/T-20-26) | ported | companion/test_config_page_04b.py::test_handle_post_same_field_set_after_restructure_saves_the_same_config |
| 208 | a French Display render (prefs.set_request_prefs(lang='fr')) carries the three supersection headings, the purpose sentence and the instant-switch sentence in French, and none of their English counterparts (D-05) | ported | companion/test_config_page_04b.py::test_french_display_render_carries_french_headings_no_english |
| 209 | a French Display render translates the default theme name ('White' -> 'Blanc') and default runway label ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), and both scopes' screen caption translates 'Plane frame' -> 'Cadre avion', while the theme/runway ids stay untranslated attribute values (Polish fix 5, D-05) | ported | companion/test_config_page_04b.py::test_french_display_and_device_render_translate_registry_labels |
| 210 | an English (default) Display render still contains every pre-existing English string this file's own checks assert, updated for CFG-85's rebuild (both the former Frame colours card's and the calendar connection block's own caption constants dropped, ASPECT_HEADING gained, everything else kept) — t() never touches the default-language render (D-05, 30-05-PLAN.md Task 2/30-06-PLAN.md Task 3, replacing the retired _english_display_render_still_carries_every_pinned_english_string) | ported | companion/test_config_page_04b.py::test_aspect_display_render_still_carries_every_pinned_english_string |
| 211 | the Device render contains no edit-artwork markup and no ?edit=1 link, in either language (D-36) | ported | companion/test_config_page_04b.py::test_device_render_carries_no_edit_artwork_markup_in_either_language |
| 212 | every key of companion/i18n_fr/display.py is a key of the merged companion.i18n_fr.CATALOG (the auto-merge package actually picked this module up) | ported | companion/test_config_page_04b.py::test_every_display_catalogue_key_is_a_key_of_the_merged_catalog |
| 213 | submitted_scope() and submitted_return_route() are strict allowlists: unknown scopes degrade to the legacy all-scope and any non-member return_to falls back to /display | ported | companion/test_config_page_04b.py::test_submitted_scope_and_return_route_are_allowlisted |
| 214 | render(scope=display/device) carries the matching hidden fields and only its own groups, including locating the rules row (inside the Aspect card) by its own data-usage attribute; the legacy render(ctx) carries no scope field; a hostile scope never reaches the markup (30-05-PLAN.md Task 2, replacing the retired _scoped_render_carries_hidden_fields_and_omits_other_groups) | ported | companion/test_config_page_04b.py::test_aspect_scoped_render_carries_hidden_fields_and_omits_other_groups |
| 215 | handle_post() treats a checkbox absent from an out-of-scope group as 'leave unchanged' (a Display save never flips the LED, a Device save never flips the screen or quiet hours), leaves display_enabled/quiet_hours_enabled/led_enabled unchanged even in-scope and on the legacy unscoped form while still honouring an explicit value, and a scoped submission without the Calendar group always carries the calendar forward (D-12.1, 22-05-PLAN.md Task 1; the led_enabled half retargeted in place from absent-means-False by 23-07-PLAN.md Task 2) | ported | companion/test_config_page_04b.py::test_handle_post_scope_carries_out_of_scope_checkboxes_forward |
| 216 | _screen_selector_html() returns the empty string for the real single-member screens registry | ported | companion/test_config_page_04b.py::test_screen_selector_empty_for_the_real_single_member_registry |
| 217 | _screen_selector_html() emits exactly one <select name="screen_id"> with one <option> per registered screen type, the current one selected, and a non-empty accessible name once a second screen type is registered | ported | companion/test_config_page_04b.py::test_screen_selector_renders_for_a_multi_member_registry |
| 218 | render() at Display and Device scope contains no <select name="screen_id"> today (a single-member registry has no real choice to offer) | ported | companion/test_config_page_04b.py::test_render_carries_no_screen_selector_today |
| 219 | handle_post() rejects a crafted screen_id with FLASH_SAVE_FAILED, notes a field error, and writes nothing (all-or-nothing) | ported | companion/test_config_page_04b.py::test_handle_post_rejects_a_crafted_screen_id |
| 220 | a valid screen_id round-trips through save_device_config() | ported | companion/test_config_page_04b.py::test_valid_screen_id_round_trips |
| 221 | _screen_selector_html() renders the screen_id field-level error message exactly once when errors carries one | ported | companion/test_config_page_04b.py::test_screen_selector_renders_the_field_error_message |
| 222 | neither the Display nor the Device scope renders an Edit-artwork link or markup any more — the link and its builder are deleted outright (D-36) | ported | companion/test_config_page_04b.py::test_neither_scope_renders_an_edit_artwork_link |
| 223 | _with_next_wake() returns the caption byte-identical for a falsy clock and appends '(next wake ≈ HH:MM)' when the clock is known | ported | companion/test_config_page_04b.py::test_with_next_wake_helper_contract |
| 224 | each of Runway/LED/Wake-interval's own caption gains the '(next wake ≈ HH:MM)' suffix when the value is known, and is byte-identical to its own constant when it is not (D-13; narrowed by 21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired, and by 22-05-PLAN.md Task 1 X1/D-04/D-12.1 once Quiet hours' own caption moves to its own computed delay sentence instead — the Frame colours card's own caption never gains this suffix either) | ported | companion/test_config_page_04b.py::test_affected_captions_gain_the_suffix_only_when_known |
| 225 | the Device page header carries a 'Next wake ≈ HH:MM' line when the value is known and none at all when it is not (D-13's 'Home and Device show' wording) | ported | companion/test_config_page_04b.py::test_device_header_shows_next_wake_line_when_known |
| 226 | with a due result, the Frame strip carries the DUE delay sentence exactly twice (once per switch cell), the Quiet hours card's own caption carries NO delay sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the DUE delay sentence naming the same computed time, unaffected by the caption change (D-04) | ported | companion/test_config_page_04b.py::test_quiet_hours_caption_and_flash_agree_on_the_due_branch |
| 227 | with a held result (the nightly regression fixture), the Frame strip carries the HELD delay sentence exactly twice (once per switch cell), the Quiet hours card's own caption carries NO delay sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the HELD delay sentence naming the window's own end, never the generic due wording (D-04, 22-UI-SPEC.md §3.3 binding rule 6) | ported | companion/test_config_page_04b.py::test_quiet_hours_caption_and_flash_agree_on_the_held_branch |
| 228 | with no check-in at all, the Frame strip carries the UNKNOWN delay sentence exactly twice (once per switch cell), the Quiet hours card's own caption carries NO delay sentence any more (29-05-PLAN.md Task 2, CFG-79), and the post-save flash still reads the UNKNOWN delay sentence, which names no time (D-04) | ported | companion/test_config_page_04b.py::test_quiet_hours_caption_and_flash_agree_on_the_unknown_branch |
| 229 | none of the three retired delay wordings ('Takes effect within about 5 minutes', 'Applies on the next scheduled poll, which may now be hours away', 'Saved — will apply on the frame's next scheduled refresh') appears anywhere under companion/ or server/, excluding this repository's own test_*.py harnesses (D-04) | ported | companion/test_config_page_05.py::test_retired_delay_wordings_are_absent_from_the_rendered_settings_pages |
| 230 | the settings-pages editorial floor, measured on the RENDERED page (never a source scan): every non-exempt .section-caption element on /display and /device is at most 12 whitespace-split words in both languages; ASPECT_CAPTION_EXEMPTIONS is skipped exactly 4 times on /display and exactly 0 times on /device (proving the exemption reachable and not silently over-broad); and the apply-timing sentence — read from frame_state.py's own DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN constants — never renders outside the Frame strip's own markup slice, proven to actually fire inside it at least once so the assertion is not vacuous (CFG-79, 29-05-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_settings_pages_editorial_floor_render_level_both_languages |
| 231 | a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway selected | ported | companion/test_config_page_05.py::test_save_round_trip_shows_confirmation_and_new_selection |
| 232 | a real HTTP save round trip keeps the server-side PRG redirect exactly SETTINGS_ROUTE?flash=saved, and the rendered redirect target carries BOTH the flash banner and flash-cleanup.js's deferred script tag (quick task 260903-peo, UIR-19) | ported | companion/test_config_page_05.py::test_settings_save_redirect_carries_flash_banner_and_cleanup_script |
| 233 | a live authenticated POST /settings with an empty body 303-redirects to /settings?flash=saved, LEAVES the stored led_enabled exactly as it was, and a follow-up GET renders the control in that same off state (retargeted in place from absent-means-False by 23-07-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_settings_post_empty_body_leaves_led_unchanged_and_renders_unchecked |
| 234 | a raw, URL-encoded no-JS POST to SETTINGS_ROUTE sets theme_arriving to a real id and clears it back to None via theme_arriving='', over the real HTTP path (15-VALIDATION.md row 11, the Settings-form half; D-06/D-09, retargeted from the retired arrivals-override checkbox) | ported | companion/test_config_page_05.py::test_settings_form_raw_post_no_js_sets_and_clears_theme_arriving |
| 235 | an unauthenticated POST /settings redirects to /login and writes nothing | ported | companion/test_config_page_05.py::test_settings_post_unauthenticated_redirects_to_login_and_writes_nothing |
| 236 | an authenticated POST to the retired /config-led route returns 404 (D-05) | ported | companion/test_config_page_05.py::test_led_route_retired_returns_404 |
| 237 | an unauthenticated GET /runway-image/3.png redirects to /login | ported | companion/test_config_page_05.py::test_runway_image_route_requires_session |
| 238 | a session-authenticated GET /runway-image/3.png returns the branch matching real on-disk state (never 500) | ported | companion/test_config_page_05.py::test_runway_image_route_honest_present_or_absent |
| 239 | session-authenticated GET requests for three adversarial runway-image paths all return 404, never 200/500 | ported | companion/test_config_page_05.py::test_runway_image_route_path_traversal_rejected[url-encoded-traversal] |
| 240 | with a calendar configured via its secret file to a URL carrying a distinctive token, a real authenticated HTTP GET of the Settings page serves the masked host + ellipsis fragment but never the token, the path segment, the query-parameter name, or the whole raw URL in the response body (T-16-SECRET, real HTTP round trip, extended by 21-07-PLAN.md Task 2 for the new masked-URL line, D-14/R-10) | ported | companion/test_config_page_05.py::test_calendar_secret_never_reaches_served_http_bytes |
| 241 | a hostile or unparseable stored calendar URL ('not a url', the empty string, a javascript: URI) renders no calendar-masked-url line at all and raises nothing (D-14/R-10, _masked_calendar_url()'s own fail-soft, never-fabricate contract) | ported | companion/test_config_page_05.py::test_calendar_hostile_stored_url_renders_no_masked_line[unparseable] |
| 242 | the Display scope renders at least three role="radiogroup" elements (Theme's departures and arrivals chip grids, plus the Runway row) and the Device scope renders none (D-12/A-30, retargeted by 20-07-PLAN.md Task 1/D-10) | ported | companion/test_config_page_05.py::test_display_scope_has_three_radiogroups_device_has_none |
| 243 | every aria-labelledby and aria-describedby value render() emits, at every scope, resolves to an id the same output actually carries, and no element emits an empty aria-describedby or aria-labelledby (D-12/A-30) | ported | companion/test_config_page_05.py::test_every_aria_reference_resolves_and_none_is_empty[all] |
| 244 | a control carrying both a hint and an error (led_enabled's switch, rendered with an errors dict) has its state, hint and error ids in its aria-describedby, hint still before error, never one overwriting another, and no error id at all when there is no error (D-12/A-30; retargeted in place from the retired checkbox by 23-07-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_control_with_both_hint_and_error_carries_both_ids_in_order |
| 245 | notifications_group()'s status row reads 'Not configured' with no URL stored and 'Configured' with one, the topic-URL input never carries a value attribute in either state, and no substring of a seeded URL appears anywhere in the rendered page (T-20-12) | ported | companion/test_config_page_05.py::test_notifications_group_status_row_configured_vs_not_and_write_only_url |
| 246 | notifications_group()'s two checkboxes reflect the stored battery_low/frame_silent booleans | ported | companion/test_config_page_05.py::test_notifications_checkboxes_reflect_stored_state |
| 247 | the Device page contains no notifications_lang control anywhere (D-28: lang travels silently, never through a <select>) | ported | companion/test_config_page_05.py::test_notifications_group_has_no_lang_selector |
| 248 | handle_post() with scope=device, a topic URL and both checkboxes persists the whole notifications group and writes lang from ctx['lang'] (D-26/D-28) | ported | companion/test_config_page_05.py::test_handle_post_notifications_round_trip_writes_lang_from_ctx |
| 249 | handle_post() with an empty notifications_topic_url leaves the previously stored URL unchanged (D-26: empty means 'leave unchanged', never 'clear it') | ported | companion/test_config_page_05.py::test_handle_post_empty_notifications_url_leaves_stored_url_intact |
| 250 | a Display render contains exactly one .theme-live-preview.aspect-card__preview figure whose <img> src ends in the saved theme's ?live=1 URL, carries loading="eager" and explicit width/height, positioned ABOVE the first accordion row (D-22..D-24, 30-05-PLAN.md Task 2, replacing the retired _display_render_has_exactly_one_live_preview_figure_eager_with_dimensions) | ported | companion/test_config_page_05.py::test_aspect_display_render_has_exactly_one_live_preview_figure_eager_with_dimensions |
| 251 | every chip's own <label> carries a data-preview-src ending in .png?live=1, while each chip's own <img> keeps loading="lazy" and the fixed, non-live src (D-24) | ported | companion/test_config_page_05.py::test_every_chip_carries_data_preview_src_ending_in_live_1_chips_stay_lazy |
| 252 | the live preview's caption names the seeded event's callsign, and falls back to the sample-flight wording with no events (D-24) | ported | companion/test_config_page_05.py::test_live_preview_caption_names_seeded_callsign_and_falls_back_to_sample |
| 253 | a French Display render's live preview shows ‘Aperçu avec votre dernier vol : ’ followed by the seeded event's callsign (D-24/D-05) | ported | companion/test_config_page_05.py::test_french_display_render_shows_live_preview_caption_with_flight |
| 254 | Display renders exactly one .theme-chip-grid (the rule-add form's own compact grid, unaffected by CFG-85), followed by exactly one swatch legend in .text-label section-caption's own declaration set outside the radiogroup, and exactly 3 .palette grids (departures/arrivals/calendar) carrying no legend at all (22-10-PLAN.md Task 1, updated by 30-05-PLAN.md Task 3 for CFG-85's accordion rebuild) | ported | companion/test_config_page_05.py::test_display_renders_one_compact_chip_grid_and_three_palettes_with_one_swatch_legend |
| 255 | the chip swatch legend names exactly as many things as the registry gives EVERY theme — computed from _palette_hex(departing_index)/_palette_hex(arriving_index) at check time, never a restated literal, so a future theme that DOES give departures and arrivals different inks would make this check demand two labels on its own (CFG-70, 27-07-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_the_swatch_legend_names_as_many_things_as_the_registry_carries |
| 256 | the 'Current' badge's text is server-rendered as a translated data-current-label attribute on exactly the --selected chip/card (never on any other), and the French render carries the French text (T10/B16, 22-10-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_current_badge_reads_a_server_rendered_translated_attribute |
| 257 | the rule-kind segmented control (config_page.py's 'Match by' <div class="theme-form">, unaffected by CFG-85) keeps its own global label-margin reset and 28px row height (T12), and .frame-colours__panel-legend is confirmed retired outright rather than repointed — the usage panels and their <legend> elements are gone, the rule-add form's own segmented control never had a <legend> to begin with, and this genuinely NARROWS the serif boundary's own documented non-serif-exception set by one (C1, 30-07-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_segmented_control_resets_label_margin_and_panel_legend_retired |
| 258 | the rules add-form renders as one left-aligned, centre-aligned flex ROW (X6/C4) - the flex-direction: column it never reset, not an auto margin, is what pushed 'Add rule' to the far right (22-10-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_rules_add_form_is_one_left_aligned_centre_aligned_row |
| 259 | each <input type="time"> carries the site language and a visible sibling showing the normalised 24h value (never a placeholder, never a title), in both languages (B14, 22-10-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_each_time_input_carries_the_site_language_and_a_visible_24h_sibling |
| 260 | style.css carries B9's zero-basis runway card (with .runway-row still wrapping for its second consumer), B15's content-width left-aligned calendar button with its accent kept, and B7/C3's active-segment hover restore at the register's own 12% accent wash (22-10-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_style_css_carries_b9_b15_and_b7_geometry_rules |
| 261 | 'Send a test' renders inside the Notifications card and reaches its own EMPTY sibling <form> through the cross-DOM form= idiom's fifth consumer - no control renders between two cards, and the form keeps its own action (B8, 22-10-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_send_a_test_lives_inside_the_notifications_card_via_the_form_idiom |
| 262 | the wake-interval field puts its label on its own line above a content-sized input (8ch with a 96px minimum, no height declared so the 44px touch-target floor is untouched) with the unit as a sibling label (B17, 22-10-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_the_wake_interval_field_has_a_label_above_it_and_a_content_sized_input |
| 263 | the Calendar status detail has a singular form, so a feed holding exactly one flight never reads '1 upcoming flights', in both languages (D-06/B16/CFG-29, 22-10-PLAN.md Task 3 — found by 22-08, landed here because this plan owns config_page.py) | ported | companion/test_config_page_05.py::test_the_calendar_status_detail_has_a_singular_form |
| 264 | the Display scope renders layout.freshness_line_html()'s own output verbatim with exactly one data-loaded-at and one data-refresh-pill, declares its own swap regions, carries its page key on <body>, and renders no freshness marker at all when the caller has no render instant (D1/CFG-35, 23-06-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_the_display_scope_refreshes_itself_from_the_same_builder |
| 265 | no Display swap region names a form, a dirty marker or a save control, and the settings form, its cross-DOM form= attachment and the fallback Save all still render with the freshness line above them in the page header — a swap landing on this page's form is the P0 Phase 22 existed to fix (B1/D1, 23-06-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_the_display_form_is_untouched_by_the_refresh_loop |
| 266 | the freshness gauge states a BOUND ("at most", rounded UP) naming the same whole minutes the interval implies at the band's minimum, its maximum and in between; the battery gauge prints an absolute figure ONLY when companion/battery.py's own estimate supports one — recomputed from the estimator, singular and plural both — and renders the NAMED "not enough history yet" sentence with no number at all for a rising, a one-day and an empty series; neither gauge renders without a usable interval, D-07's echo is honoured only where it is usable, and the screen-off cadence is stated (CFG-49, 25-05-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_two_gauges_claim_exactly_what_the_data_supports |
| 267 | no days-remaining arithmetic exists anywhere under companion/pages/ — every one of days_remaining/mv_per_day/observed_span_days/the two millivolt endpoints/the SEED-006 BATTERY_DISCHARGE_CURVE table appears only as a read of the estimator's own returned dict, comments and docstrings stripped first — the estimate is called QUALIFIED off companion.battery, and every quantity template this card adds carries the "#" mark rather than a format artefact and has a French sibling (CFG-49/D-27, 25-05-PLAN.md Task 1, quick 260923-gaf) | ported | companion/test_config_page_05.py::test_wake_battery_text_reads_the_estimate_through_the_qualified_battery_module |
| 268 | the wake-interval caption (#wake-interval-caption) is materially shorter than 27-01-SUMMARY.md's recorded 220-char baseline in BOTH languages — the mechanism and apply-timing sentences are cut, the derived "(next wake ≈ ...)" suffix (a real timestamp, not an invented figure) is untouched (CFG-67, 27-06-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_wake_interval_caption_is_shortened_in_both_languages |
| 269 | the two wake gauges (.wake-gauge) are materially shorter than 27-01-SUMMARY.md's recorded 254-char combined baseline in BOTH languages, and the insufficient-history state still prints NO absolute battery figure — asserted about the SAME reading the length is measured from, with the forbidden pattern scoped to the days-claim shape itself so it does not false-positive on an unrelated ≈-bearing timestamp (D18's honesty contract, CFG-67, 27-06-PLAN.md Task 3) | ported | companion/test_config_page_05.py::test_wake_gauges_are_shortened_and_battery_refusal_survives_in_both_languages |
| 270 | the Quiet hours paragraph (#quiet-hours-caption) is materially shorter than 27-01-SUMMARY.md's recorded 188-char baseline in BOTH languages, and renders as EXACTLY QUIET_HOURS_SECTION_CAPTION's own translated text with no delay sentence appended at all any more — quiet_hours_group() no longer accepts a delay_sentence keyword (CFG-79, 29-05-PLAN.md Task 2, narrowing CFG-67's 27-06-PLAN.md Task 3 cut) | ported | companion/test_config_page_05.py::test_quiet_hours_caption_is_shortened_and_carries_no_delay_sentence |
| 271 | the two gauges are an ADDITION: across five argument shapes (in band, stored below the 60s floor, stored above the ceiling, never set, and a rejected save's raw echo) the <input type="number"> is byte-identical to its pre-plan output — same id, name, min, max and placeholder, the value attribute present exactly when the guard admits it and absent otherwise (an out-of-range value blocks submission of the ENTIRE form) — with B17's label still above it, the unit sibling still immediately after it, the error block still attached, and both gauges appended after all of them (CFG-49/D-07/B17, 25-05-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_gauges_are_an_addition_and_the_number_input_is_untouched[saved-in-band] |
| 272 | the wake-interval range is NAMELESS (a named one would post a second value for the same setting and the last to arrive would win), carries no role="slider" on top of a native slider, takes its min/max from server.device_config rather than a literal, steps by exactly the minute both gauges speak in, has its own accessible name and describes itself by the two gauges, renders ONLY inside 25-01's .js gate and only when there is a saved interval to start from, and nothing on the card is a live region (CFG-49/CFG-52/T-25-05-D, 25-05-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_the_range_is_gated_nameless_and_bounded_by_device_config |
| 273 | the readout seam is pinned from BOTH sides: every attribute this card emits is named in companion/static/value-controls.js and vice versa, every readout describes the field the form actually posts, the script takes the same CEILING the server does (a floor would print a bound that is false), all three gesture listeners stand aside for a wrapper holding a native mirror (without which preventDefault cancels the thumb drag), the relative clause's base is the saved interval so it renders EMPTY until something else is proposed, and no readout template contains the days wording at all — so a script that only substitutes into templates cannot invent a figure the server declined to state (CFG-49/T-25-05-C, 25-05-PLAN.md Task 2) | ported | companion/test_config_page_05.py::test_the_readout_seam_this_card_declares_is_the_one_the_script_reads |
| 274 | the whole rendered Display page carries exactly len(device_config.THEME_IDS) radios named 'theme' — ONE set, computed from the registry at check time, re-homed from the retiring carousel's own equivalent guard so the page can never show one setting in two disagreeing places (CFG-85, 30-03-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_display_page_carries_exactly_one_radio_set_per_theme_field |
| 275 | the rendered Display page carries no duplicate id anywhere — asserted as page-wide id uniqueness (THE property the THEME_CAROUSEL_STRIP_ID trap violates), never as 'the carousel ids I expect differ', with a failure message naming the duplicated id and how many times it appeared (CFG-68, 27-07-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_rendered_settings_page_carries_no_duplicate_id |
| 276 | the native submit carrying STATIC_SAVE_FALLBACK_ATTR is emitted UNCONDITIONALLY — render() has exactly one return statement, it is never nested inside a branch, and the attribute reaches it as a bare name rather than through a ternary — AND every one of the three scopes (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE) renders it exactly once, so there is no code path, past or future, that can omit the no-JS save floor (CFG-64, 27-03-PLAN.md Task 1) | ported | companion/test_config_page_05.py::test_the_native_submit_is_emitted_unconditionally_on_every_render |

### Part 01 (plan 33-09)

Rows 1-33 flipped. 1 deleted (row 1, R: the self-referential aspect-repin ledger guard —
opened `test_config_page.py`'s own source to grep def names, no application behaviour). 32
ported to `companion/test_config_page_01.py` (4 B — `handle_post()` persistence/regression
checks with no primary markup-shape assertion; 28 D — `render()`/`led_group()`/
`quiet_hours_group()`/`wake_interval_group()`/`runway_fieldset()`/`_palette_swatch_html()`/
`_palette_grid_html()`/`_usage_row_summary_html()` markup-shape/attribute/position checks over
the returned HTML string). New module: `companion/test_config_page_01.py` (32 tests). The
`_ASPECT_REPIN_LEDGER` tuple and its history comments are deleted from the legacy harness in
this plan's own commit (33-MIGRATION-RULES.md section 1's chain-first duty), along with the
`EXPECTED_CHECK_COUNT` history collapsed to one line (`EXPECTED_CHECK_COUNT = 243`, matching
this fragment's 243 remaining pending rows).

### Part 02 (plan 33-10)

Rows 34-84 (51 checks): the quiet-window arithmetic and the quiet-hours dial (span/arc/
readout/handles/pair seam), the remaining `render()`/`runway_fieldset()`/dirty-bar markup
checks, `poll_trigger_section()`'s data-attribute contract plus `poll-cooldown.js`'s sink
safety, and `handle_post()`'s theme/runway/LED/quiet-hours/wake-interval validation paths —
all `ported` to `companion/test_config_page_02.py`. Rubric codes: 20 B, 22 D, 4 C (rows 38,
41, 45, 47 — `style.css` fetched via `served_stylesheet()` and read structurally with
`companion_markup.css_rules()`/`declarations_for()` instead of opened from disk), 5 J (rows
43, 46, 48, 64, 65 — `value-controls.js`/`poll-cooldown.js` fetched via `served_asset()`
instead of opened from disk). No deletions.

Two rows split into more than one pytest node id when their boundary sets were parametrized
with ids (33-10-PLAN.md's own instruction): row 73 also produced
`test_handle_post_empty_form_leaves_led_unchanged[led-was-off]` (the row above points at
`[led-was-on]`, the primary id); row 84 also produced
`test_handle_post_wake_interval_rejection_paths_byte_identical[1-5-not-an-int]`,
`[59-below-floor]`, `[3601-above-ceiling]` and `[negative-1-below-zero]` (the row above
points at `[abc-not-an-int]`, the primary id).

`EXPECTED_CHECK_COUNT` shrunk to `192` (243 - 51), matching this fragment's 192 remaining
pending rows (parts 03-05).

### Part 03 (plan 33-11)

Rows 85-145 (61 checks): `handle_post()`'s field-level `errors` dict (19-07-PLAN.md), the
retired LED-route/helper-symbol guards, runway-image detection and `runway_fieldset()` image
emission, cross-file DOM-contract guards between `config_page.py` and its two static assets
(`dirty-state.js`, `style.css`), the theme-chip grid's markup/selection-state contract
(including the live `:has(input:checked)` treatment and its saved-but-unchecked "Current"
badge), the arrivals/calendar theme override's clearable contract, and the Aspect card's own
accordion shape and its per-flight rules editor markup — all `ported` to
`companion/test_config_page_03.py`. No deletions.

Rubric codes: 22 B (`handle_post()`/`render()` persistence and retired-symbol checks with no
primary markup-shape assertion), 1 T (row 103 — the does-not-exist `image_dir` check now uses a
never-created `tmp_path` subpath rather than `tempfile.mkdtemp()` + `shutil.rmtree()`), 21 D
(`render()`/`runway_fieldset()`/`_theme_chip_grid_html()`/Aspect-card markup-shape/attribute/
position checks over the returned HTML string), 11 C (rows 96, 112, 113, 114, 128, 129, 130,
131, 132, 133, 134 — `style.css` fetched via `served_stylesheet()` and read structurally
where the fact is a plain "selector X declares Y" (rows 96, 114 via
`companion_markup.declarations_for()`) or as a selector-absence relationship over
`companion_markup.css_rules()` (rows 112, 113 — this plan's own named hotspot: no rule
selector anywhere references `STATIC_SAVE_FALLBACK_ATTR` / the retired `.save-status` class),
with the remaining C rows (128-134) kept as index/regex scans over the served (never disk-read)
stylesheet text, following 33-10's own precedent, since they assert source-order/specificity/
brace-nesting relationships a flat selector→declaration lookup does not simplify), 5 J (rows
108, 110, 111, 135, 136 — `dirty-state.js` fetched via `served_asset()` instead of opened from
disk), 1 mixed C+J (row 109 — both `style.css` and `theme-preview.js` fetched via
`served_stylesheet()`/`served_asset()`; the JS half is comment-stripped with a NEW
`companion/test_config_page_helpers.py::strip_js_line_and_block_comments()` helper rather than
`companion_markup.strip_js_comments_and_strings()`, which would erase the quoted `"load"`/
`"error"` string-literal tokens the check searches for).

Three rows split into more than one pytest node id when their case tables were parametrized
with ids (33-11-PLAN.md's own instruction, following 33-10's precedent): row 87 produced the
six `test_handle_post_errors_dict_filled_for_each_real_user_error_field[...]` ids; row 123
produced the six `test_handle_post_crafted_non_member_theme_and_calendar_values_still_rejected
[...]` ids; row 124 produced the three `test_handle_post_nonmember_theme_arriving_rejected[...]`
ids. Each row above points at the primary (first) id; the SUMMARY lists the rest.

Two Aspect-card helpers this and later parts (04/05) both need —
`_ASPECT_RETIRED_MARKUP_TOKENS` / `_aspect_usage_row_bounds()` (still used by not-yet-migrated
checks below row 145) and `_rules_row_segment()` (same) — stay in the legacy harness's
`main()` (relocated earlier in source order, ahead of the now-removed migrated checks, with no
behaviour change: they are pure function/constant definitions with no execution-order side
effect). This plan's own copies (`ASPECT_RETIRED_MARKUP_TOKENS` / `aspect_usage_row_bounds()` /
`rules_row_segment()`) are added to `companion/test_config_page_helpers.py` instead, so parts
04/05 import rather than re-derive them.

`EXPECTED_CHECK_COUNT` shrunk to `131` (192 - 61), matching this fragment's 131 remaining
pending rows (parts 04-05).


### Part 04 (plan 33-12)

Rows 146-228 (83 baseline checks): 79 B (calls a production function - render()/handle_post()/
led_group()/quick_led_form_html()/calendar_disconnect_confirm_page()/_calendar_connection_html()/
_screen_selector_html()/scope_groups()/submitted_scope()/submitted_return_route() - and asserts
on real output), 2 P (rows 155-156, this plan's own named audit hotspot - see below), 1 T (row
190's own real-Device-render sibling-of-settings-form proof, using `tmp_path` rather than
`tempfile.mkdtemp()`), 1 S (row 196, deleted). Zero C/D/J/R codes in this slice - no check here
opened a stylesheet or a served JS asset.

Rows 155/156 (the audit's own named hotspot: the reads of the phase 20/21 companion-suggestions
specification documents out of the repository's planning history) are REWRITTEN, not deleted:
the four/two locked copy constants (`CALENDAR_STATUS_DETAIL_TEMPLATE`,
`CALENDAR_STATUS_FETCH_FAILED_DETAIL`, `CALENDAR_CONNECT_BUTTON_TEXT`,
`CALENDAR_REPLACE_URL_SUMMARY`, `CALENDAR_REPLACE_BUTTON_TEXT`, `CALENDAR_DISCONNECT_BUTTON_TEXT`)
are pinned as literal Python strings inside
`companion/test_config_page_04.py::test_calendar_copy_fidelity_locked_to_the_phase_20_wording`
and `::test_calendar_merged_button_copy_locked_to_the_phase_21_wording`, asserted equal to
`config_page.py`'s own live constants, and asserted to actually reach a real `render()` call -
no test in this repository opens a file under `.planning/` any more for this check.
`.github/workflows/ci.yml` still lists the two phase 20/21 specification paths in its
path-filter allowlist only because of these two now-retired reads; 33-32 removes them.

Row 165 (the adversarial `calendar_theme_id` rejection loop) is converted to
`@pytest.mark.parametrize` with three readable ids (`invalid-id`, `path-traversal-shaped`,
`sql-shaped`), following 33-10/33-11's own precedent - each case gets its own `tmp_path`,
independent of the others. This row points at the primary (`invalid-id`) node id; the SUMMARY
lists the other two.

New modules: `companion/test_config_page_04.py` (rows 146-187, the rules-editor suggestion
chips/disclosures and the whole Calendar card contract) and `companion/test_config_page_04b.py`
(rows 188-228, the screen registry, the LED single-switch contract, the Display/Device
supersection structure, the D-19 instant-switch restructure, i18n copy, scope-aware
render()/handle_post(), the conditional screen selector, and the next-wake caption suffix/the
one computed Quiet-hours delay sentence). `companion/test_config_page_helpers.py` gains
`CALENDAR_BASE_CTX`, the render() context part 05 (33-13) also needs.

The legacy harness's own `_ASPECT_RETIRED_MARKUP_TOKENS`/`_aspect_usage_row_bounds()`/
`_rules_row_segment()` closures (relocated by 33-11 for this part's own use) are now removed
outright from `main()` - no check pending in part 05 (rows 229+) calls them, confirmed by
grepping the remaining legacy source. `_CALENDAR_BASE_CTX`/`_TASK2_BASE_CTX` (the two render()
base contexts part 05's own remaining checks still call by name) stay, unmodified, relocated to
sit beside `_read_static()` in `main()`'s shared setup area.

`EXPECTED_CHECK_COUNT` shrunk to `48` (131 - 83), matching this fragment's 48 remaining pending
rows (part 05, plan 33-13).

### Part 05 (plan 33-13) — chain closed

Rows 229-276 (the last 48 baseline checks): the retired delay-wording guard and the settings-
pages editorial floor (D-04/CFG-79), the live authenticated `companion/app.py` HTTP round trips
(save confirmation, PRG redirect + flash cleanup, the empty-body `led_enabled` no-op, the
`theme_arriving` raw-POST set/clear, the unauthenticated POST, the retired `/config-led` route,
the runway-image route's session/path-traversal guards, the calendar secret never reaching the
served bytes), the aria-describedby/labelledby contract (D-12/A-30), the Notifications group
(D-26/D-28), the live theme preview (D-22..D-24), the Aspect card's swatch legend and "Current"
badge, the rule-kind segmented control and the retired `.frame-colours__panel-legend` (T12/C1),
the rules add-form geometry (X6/C4), the wake-interval field's B17 layout and B9/B15/B7 style.css
geometry, the Notifications "Send a test" cross-DOM form idiom (B8), the Calendar status detail's
singular form (CFG-29), the Display scope's freshness-line refresh loop (D1/CFG-35), D18's two
wake-interval gauges and the gated range/readout seam that steers them (CFG-49/CFG-52), and the
closing structural proofs (one radio set per theme field CFG-85, no duplicate id CFG-68, the
no-JS save floor unconditional on every render() call CFG-64) — all `ported` to
`companion/test_config_page_05.py`. No deletions.

Rubric codes: 32 B/D (calls a production function or `render()`/`handle_post()` and asserts
markup-shape/attribute/position over the returned HTML string, or a real HTTP round trip via
`make_app_server`), 3 C (rows 257, 258, 260 — `style.css` fetched via `served_stylesheet()` and
read structurally with `companion_markup.declarations_for()`/`css_rules()`, never a raw
index/substring scan over served text, per 33-FOLLOWUPS.md F-01), 1 J (row 273 —
`value-controls.js` fetched via `served_asset()`, comments stripped with
`companion/test_config_page_helpers.py::strip_js_line_and_block_comments()` — preserves the
quoted string literals the check searches for, unlike `companion_markup.strip_js_comments_and_
strings()`), 1 rewritten D (row 229 — the legacy whole-repo source-text grep for three retired
wordings is rewritten as "the retired string is absent from the rendered Display/Device page,
both scopes, both languages"), 2 S (rows 267, 276 — see below).

Rows 267 and 276 each opened `companion/pages/config_page.py` from disk and walked its syntax
tree with `ast.parse()`/`tokenize` (banned outright by guard G2). Both are rewritten as
behaviour rather than deleted, since each protects a real, still-checkable property: row 267
becomes `test_wake_battery_text_reads_the_estimate_through_the_qualified_battery_module`, a
`monkeypatch` proof that `config_page` never binds `battery_life_estimate` into its own
namespace (`not hasattr()`, the same technique rubric S recommends for "retired symbol gone")
and that patching `companion.battery.battery_life_estimate` itself changes what
`wake_battery_observed_text()` reports — provable only if `config_page` reads the function off
the qualified module object on every call. Row 276 becomes
`test_the_native_submit_is_emitted_unconditionally_on_every_render`, calling `render()` across
every scope AND every extra keyword shape it accepts (`errors`/`submitted`, both, neither) and
asserting the fallback appears exactly once on each — a wider behavioural net than the retired
single-return-statement source proof, which said nothing about any other, unexercised code path.

Row 271's six-shape table is `@pytest.mark.parametrize`d with explicit ids (following 33-10's
precedent); this row's target points at the primary (`saved-in-band`) id, the SUMMARY lists the
other five. Row 271's own trailing clause ("the error block still attached, and both gauges
appended after all of them") is additionally proven by a SEPARATE test,
`companion/test_config_page_05.py::test_the_gauges_error_block_still_attaches_with_the_gauges_
after_it` (a distinct fixture — an `errors` dict — rather than a seventh parametrize case;
33-MIGRATION-RULES.md section 3: "when one old check splits into several tests, the ledger row
points at the primary node id and the SUMMARY lists the others"). Rows 239, 241 and 243 are each
`@pytest.mark.parametrize`d over their own case tables the same way; each row points at its
primary id (`url-encoded-traversal`, `unparseable`, `all` respectively).

`companion/test_config_page.py` is deleted outright (`git rm`) in this plan's own commit: every
one of its 276 baseline checks is now accounted for (274 ported to new node ids across
`companion/test_config_page_01.py`..`_05.py`, 2 deleted with a stated reason — row 1's
self-referential `_ASPECT_REPIN_LEDGER` guard, row 196's redundant AST scan). `33-ledger-check.py
companion/test_config_page.py` **WITHOUT** `--allow-pending` confirms **276/276 baseline checks
mapped, 0 pending**. `skypane_test_support.legacy_companion_harnesses()`'s disk-derived set and
`companion/test_legacy_harness_shim.py`'s parametrize list both drop the file automatically —
the config-page migration chain (33-09 through this plan) is CLOSED.


### Closing sweep (plan 33-32): structural stylesheet checks

Rows 47 and 112-113, 128-134 kept their node ids but no longer assert with a regex, `in` test
or str search over the served stylesheet's text (33-FOLLOWUPS.md F-01). They parse it with
`companion_markup` instead: `declarations_for()` in a named at-rule context replaces every
fixed-width text window and `index()` slice, `rule_indices()` replaces the `str.index()`
source-order comparisons (rows 47, 130), and `at_rule_blocks()` counts the one
`@supports selector(:has(*))` block and the one `@keyframes skypane-bar-arrive` block (rows 129,
130, 134). Rows 112 and 113 drop only their sub-clauses that asserted stylesheet COMMENTS (the
superseded-contract prose, the dated paragraphs, the "still mentioned in prose" probes):
C: asserted a stylesheet comment; no rendered behaviour. Both rows stay `ported`: the selector
checks that carry their behaviour are unchanged.

## companion/test_companion_app.py

# Ledger: companion/test_companion_app.py

Baseline: `companion__test_companion_app.txt`, 320 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | password_ok() accepts the correct password and rejects a wrong one | ported | companion/test_companion_app_01.py::test_password_ok_correct_and_wrong |
| 2 | password_ok() raises AuthNotConfigured when the password env var is unset | ported | companion/test_companion_app_01.py::test_password_ok_unconfigured_fails_closed |
| 3 | verify_session_token(issue_session_token()) is True | ported | companion/test_companion_app_01.py::test_issue_and_verify_round_trip |
| 4 | verify_session_token() returns False for five malformed inputs without raising | ported | companion/test_companion_app_01.py::test_verify_rejects_five_malformed_inputs |
| 5 | flipping a single hex character of a valid signature invalidates the token | ported | companion/test_companion_app_01.py::test_verify_rejects_flipped_signature |
| 6 | session_set_cookie_header() carries HttpOnly/Secure/SameSite=Strict/Path | ported | companion/test_companion_app_01.py::test_session_cookie_header_carries_security_flags |
| 7 | SKYPANE_COMPANION_INSECURE_COOKIES=1 drops Secure from both cookie builders while HttpOnly/SameSite=Strict/Path survive (A-34/D-17) | ported | companion/test_companion_app_01.py::test_insecure_cookies_flag_drops_secure_but_keeps_other_flags |
| 8 | SKYPANE_COMPANION_INSECURE_COOKIES="true" fails closed - Secure stays on (A-34/D-17) | ported | companion/test_companion_app_01.py::test_insecure_cookies_flag_fails_closed_on_other_values |
| 9 | deploy/skypane.env.example documents SKYPANE_COMPANION_INSECURE_COOKIES (A-34/D-17) | ported | companion/test_companion_app_01.py::test_env_example_documents_insecure_cookies_flag |
| 10 | logout_set_cookie_header() expires the cookie immediately | ported | companion/test_companion_app_01.py::test_logout_cookie_expires_immediately |
| 11 | parse_cookies() returns each cookie by name and never raises on a bad header | ported | companion/test_companion_app_01.py::test_parse_cookies_multi_and_malformed |
| 12 | LoginThrottle allows attempts up to its limit, locks out, then resets on success | ported | companion/test_companion_app_01.py::test_login_throttle_allows_locks_and_resets |
| 13 | LoginThrottle with a zero-length window releases itself and a post-window failure starts a fresh count (A-32/D-15) | ported | companion/test_companion_app_01.py::test_login_throttle_self_releases_with_zero_length_window |
| 14 | LoginThrottle with a real lockout_s releases itself once the window elapses and a post-window failure starts a fresh count (A-32/D-15) | ported | companion/test_companion_app_01.py::test_login_throttle_self_releases_with_real_window |
| 15 | a forged token signed with a different secret is rejected | ported | companion/test_companion_app_01.py::test_forged_token_different_secret_rejected |
| 16 | a hand-built token expired by one second is rejected despite a correct signature | ported | companion/test_companion_app_01.py::test_hand_built_expired_token_rejected |
| 17 | issued tokens verify within this process, but a raw-password-keyed signature (the old scheme) does not - the signing key is genuinely derived (A-33/D-16) | ported | companion/test_companion_app_01.py::test_tokens_signed_with_derived_key_not_raw_password |
| 18 | revoke(token) then is_revoked(token) is True, a never-issued token is False, and a malformed token passed to revoke() raises nothing (A-33/D-16) | ported | companion/test_companion_app_01.py::test_revoke_then_is_revoked_round_trip |
| 19 | a revoked token is pruned out of the revocation set once its own expiry passes (A-33/D-16, T-19-14: the set stays bounded) | ported | companion/test_companion_app_01.py::test_revoked_token_pruned_once_it_expires |
| 20 | AuthNotConfigured's message never contains the configured password value | ported | companion/test_companion_app_01.py::test_auth_not_configured_message_omits_password |
| 21 | escape_html() escapes all five HTML-special characters | ported | companion/test_companion_app_01.py::test_escape_html_all_special_chars |
| 22 | escape_html() coerces None to an empty string and non-strings to their string form | ported | companion/test_companion_app_01.py::test_escape_html_non_string_inputs |
| 23 | page_shell() renders one document with lang/viewport/stylesheet/title/a nav link for every NAV_TABS route | ported | companion/test_companion_app_01.py::test_page_shell_document_shape |
| 24 | the sub-960px nav link matching `active` carries a distinguishing class and aria-current, the others carry neither (retargeted from the retired dropdown nav onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_01.py::test_page_shell_marks_only_the_active_sub960_nav_link |
| 25 | page_shell() splices the flash banner in directly below page_header()'s title, and FLASH_SLOT_MARKER never reaches the rendered document | ported | companion/test_companion_app_01.py::test_flash_banner_spliced_below_page_header_marker_never_leaks |
| 26 | page_shell() still renders the flash banner in its original slot for a body with no FLASH_SLOT_MARKER (the pre-page_header() fallback path) | ported | companion/test_companion_app_01.py::test_flash_banner_fallback_slot_when_body_has_no_marker |
| 27 | an anomaly banner (banner=) is unaffected by the flash-slot move and still renders in its existing pre-body slot | ported | companion/test_companion_app_01.py::test_anomaly_banner_unaffected_by_the_flash_slot_move |
| 28 | page_shell() reflects the supplied UI theme; ui_theme_from_cookie() falls back to auto | ported | companion/test_companion_app_01.py::test_theme_resolution |
| 29 | status_dot() encodes the state as a fixed class, escapes the label, falls back to warn | ported | companion/test_companion_app_01.py::test_status_dot_states |
| 30 | data_table() escapes every header/cell and emits the empty-state block for zero rows | ported | companion/test_companion_app_01.py::test_data_table_escapes_and_empty_state |
| 31 | data_table() wraps its <table> in a horizontally-scrollable container | ported | companion/test_companion_app_01.py::test_data_table_wrapped_for_horizontal_scroll |
| 32 | sidebar_nav() renders every NAV_TABS link with exactly one active | ported | companion/test_companion_app_01.py::test_sidebar_nav_renders_all_tabs_with_one_active |
| 33 | sidebar_nav() matches no tab and stays script-free for a hostile active value | ported | companion/test_companion_app_01.py::test_sidebar_nav_escapes_hostile_active |
| 34 | layout.NAV_TABS holds exactly 6 entries, in order home/display/flights/airlines/health/device | ported | companion/test_companion_app_01.py::test_nav_tabs_shrunk_to_four_settled_order |
| 35 | a rendered authenticated page contains exactly six sidebar nav links and exactly six tab-bar links, with exactly one marked active in each, and the hamburger dropdown holds zero destination links (retargeted from the dropdown onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_01.py::test_sidebar_and_tab_bar_render_exactly_six_links_one_active_each |
| 36 | the eye glyph (icon-nav-preview) is still a whitelist member and icon_html() returns non-empty markup for it, even though its nav-slug mapping was removed | ported | companion/test_companion_app_01.py::test_eye_glyph_survives_nav_shrink |
| 37 | stat_tile() maps status to a fixed class with an accent fallback, escapes the caption, and passes content_html through unmodified | ported | companion/test_companion_app_01.py::test_stat_tile_status_classes_caption_escape_and_content_passthrough |
| 38 | card_status_class() maps status to base_class + a fixed suffix for the three whitelisted states, and falls back to the empty string (not an accent class) for None or an unrecognised status — the divergence from stat_tile()'s own fallback (quick task 260902-gjj, ISSUE 2) | ported | companion/test_companion_app_01.py::test_card_status_class_whitelist_and_empty_fallback |
| 39 | page_shell() wraps header+sidebar+main in .dashboard-shell with both nav landmarks (sidebar + tab bar, and exactly one when there is no tab bar) and both theme-form copies present | ported | companion/test_companion_app_01.py::test_page_shell_renders_dashboard_shell_with_sidebar_and_dropdown_theme |
| 40 | page_shell()'s skip link target carries tabindex="-1" so it actually receives focus | ported | companion/test_companion_app_01.py::test_page_shell_skip_link_target_is_focusable |
| 41 | page_shell()'s output contains no unescaped script tag for an escaped hostile body | ported | companion/test_companion_app_01.py::test_page_shell_escapes_hostile_body |
| 42 | layout.ICON_IDS has exactly twenty-three unique members, each a symbol id in ICON_DEFS_HTML and vice versa | ported | companion/test_companion_app_01.py::test_icon_sprite_integrity |
| 43 | icon_html() returns markup for every whitelisted id and '' for an unknown/empty/None/hostile id | ported | companion/test_companion_app_01.py::test_icon_html_whitelist_enforcement |
| 44 | stat_tile() is byte-identical with icon omitted and places a valid icon before the caption text | ported | companion/test_companion_app_01.py::test_stat_tile_backcompat_and_icon_slot |
| 45 | page_shell() emits exactly one sprite (one <defs, twenty-three <symbol) before dashboard-shell, no inline styles | ported | companion/test_companion_app_01.py::test_page_shell_emits_sprite_once_no_inline_styles |
| 46 | the icon/icon-defs/STAT_TILE_ICON_CLASS class names all appear in companion/static/style.css | ported | companion/test_companion_app_01.py::test_icon_classes_styled_in_served_stylesheet |
| 47 | every heading role (h1/h2/h3/legend/.text-heading) shares one serif rule except the one named, asserted nested card-title sans exception (D-09), and `legend` does not override its weight | ported | companion/test_companion_app_01.py::test_heading_roles_share_one_serif_rule_with_named_nested_exception |
| 48 | --font-serif never reaches table, body, mono, nav-link or stat-tile-caption rules (D-03's headings-only boundary; D-13 retired the caption's own former serif exception) | ported | companion/test_companion_app_01.py::test_serif_never_reaches_dense_or_tabular_content |
| 49 | mobile dropdown nav link keeps its restored 44px/Body-size tap target while the desktop sidebar link stays at its D-05 32px/Label-size compaction (260902-qkm) | ported | companion/test_companion_app_01.py::test_mobile_nav_link_and_sidebar_link_geometries_stay_diverged |
| 50 | there is exactly one error-signal colour token (--color-status-error), no --color-destructive duplicate | ported | companion/test_companion_app_01.py::test_exactly_one_error_signal_colour_token |
| 51 | the Health notification dot appears inside the Health sidebar link and on the tab bar's More summary — one per nav renderer — when health_alert='error', nowhere when None/omitted, and never on another link (retargeted from the dropdown, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_health_nav_notification_dot_appears_in_sidebar_and_tab_bar |
| 52 | input.visually-hidden/select.visually-hidden clears the 44px touch-target floor off hidden form controls, and the global input/select rule still declares both 44px minimums for every other field | ported | companion/test_companion_app_02.py::test_hidden_form_control_floor_and_global_floor_both_survive |
| 53 | layout.page_shell(..., health_alert='warn') also renders the notification dot, using dot--warn rather than dot--error | ported | companion/test_companion_app_02.py::test_health_nav_notification_dot_warn_severity |
| 54 | nav-dropdown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval) — standing constraints on the file | ported | companion/test_companion_app_02.py::test_nav_dropdown_script_es5_safe_and_side_effect_free |
| 55 | the hamburger toggle carries type=button/id/aria-expanded=false/aria-controls and the fixed accessible label (never a close-verb variant), and the panel never renders open | ported | companion/test_companion_app_02.py::test_toggle_aria_contract_and_fixed_label |
| 56 | the dropdown panel holds the state reminder, then the language and theme switches and Sign out, in that order — and zero destination links (retargeted in place from the retired six-link menu, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_dropdown_contents_and_order |
| 57 | companion.app.NAV_SCRIPT_ROUTE, layout's nav DOM-contract literals, nav-dropdown.js and style.css all agree with each other and with a rendered document | ported | companion/test_companion_app_02.py::test_three_file_nav_dom_contract_guard |
| 58 | with JavaScript disabled the dropdown panel stays unclipped in the DOM (the collapsed look is a CSS max-height constraint, not a hidden attribute or display:none), every nav link stays reachable in the tab bar with its Advanced group behind a native <details> needing no script, and the server-rendered <html> tag carries no .js marker class (retargeted onto the tab bar, 22-14-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_dropdown_survives_with_javascript_disabled |
| 59 | nav-dropdown.js adds the .js marker class before its dropdown element lookup and implements the hidden-attribute/transitionend/reduced-motion state machine, matched by style.css's .js-scoped clipping rules | ported | companion/test_companion_app_02.py::test_nav_dropdown_js_progressive_enhancement_state_machine |
| 60 | the bottom tab bar renders five cells fed by the ONE shared _nav_links() iteration — its destinations equal the sidebar's in NAV_TABS order, the four everyday routes are tab links and the Advanced group is a native <details> sheet, exactly one aria-current="page" sits on the real link (never on the <summary>), the More summary wears the active pill on an Advanced page, it carries the shared Primary-navigation landmark name, and the whole bar carries no script hook (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_companion_app_02.py::test_tab_bar_is_five_cells_from_the_one_shared_nav_iteration |
| 61 | the tab bar renders from the authenticated shell only and only with a device config — never on the login shell, never on the 404 — and the <body> clearance marker appears exactly when the bar does (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_companion_app_02.py::test_tab_bar_is_absent_from_the_login_shell_and_the_404 |
| 62 | parse_single_uploaded_file() returns the payload for a well-formed single-part body, even when the part header declares a traversal-shaped filename (never read) | ported | companion/test_companion_app_02.py::test_parser_happy_path_ignores_traversal_filename |
| 63 | parse_single_uploaded_file() returns None for a two-part body — this route accepts exactly one file part and nothing else | ported | companion/test_companion_app_02.py::test_parser_two_parts_returns_none |
| 64 | parse_single_uploaded_file() returns None for a non-multipart media type | ported | companion/test_companion_app_02.py::test_parser_urlencoded_media_type_returns_none |
| 65 | parse_single_uploaded_file() returns None when the boundary parameter is missing | ported | companion/test_companion_app_02.py::test_parser_missing_boundary_returns_none |
| 66 | parse_single_uploaded_file() returns None for an empty body | ported | companion/test_companion_app_02.py::test_parser_empty_body_returns_none |
| 67 | parse_single_uploaded_file() returns None when the part has no header/body separator | ported | companion/test_companion_app_02.py::test_parser_missing_header_body_separator_returns_none |
| 68 | parse_single_uploaded_file() returns None for a None content_type | ported | companion/test_companion_app_02.py::test_parser_none_content_type_returns_none |
| 69 | parse_single_uploaded_file() returns None for an empty file part payload | ported | companion/test_companion_app_02.py::test_parser_empty_payload_returns_none |
| 70 | env_wake_interval_default() covers its whole input space (unset, empty, non-numeric, whitespace-padded, in-range and out-of-range including deploy/skypane.env.example's shipped below-floor SKYPANE_SLEEP_S=30) and never raises | ported | companion/test_companion_app_02.py::test_env_wake_interval_default_full_input_space |
| 71 | page_context() threads wake_interval_env_default from the real environment read: 900 when SKYPANE_SLEEP_S=900, and always present (never conditionally omitted) as None when unset | ported | companion/test_companion_app_02.py::test_page_context_threads_wake_interval_env_default |
| 72 | preview_png_bytes() returns a 320x120 PNG for every id in device_config.THEME_IDS | ported | companion/test_companion_app_02.py::test_theme_preview_bytes_open_as_320x120_rgb_png_for_every_theme |
| 73 | the 18 themes' previews have pairwise-distinct mean RGB at the crop/size used (proves the crop box discriminates themes, D-07) | ported | companion/test_companion_app_02.py::test_theme_preview_means_pairwise_distinct |
| 74 | THEME_PREVIEW_CROP_BOX keeps THEME_PREVIEW_SIZE's exact 8:3 ratio and cuts no ink band at either edge - every caption glyph is outside it and the main illustration band is inside it whole, measured against a real render (B6, 22-10-PLAN.md Task 2) | ported | companion/test_companion_app_02.py::test_theme_preview_crop_keeps_8_3_and_excludes_every_caption_glyph |
| 75 | preview_png_bytes() returns byte-identical output across two calls for the same theme (the scene is fixed, D-06 — nothing time- or data-dependent leaks in) | ported | companion/test_companion_app_02.py::test_theme_preview_bytes_stable_across_calls |
| 76 | cache_path() returns None for a traversal-shaped id, an unknown id, and a falsy state_dir (boundary guard, T-v26-01-01 discipline) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_rejects_unsafe_and_falsy_inputs |
| 77 | cached_preview_bytes() on a cold state dir creates the cache file and returns the same bytes preview_png_bytes() would | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_cold_cache_creates_file |
| 78 | a second cached_preview_bytes() call for the same theme is served from the file on disk, not re-rendered | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_second_call_serves_from_disk |
| 79 | preview_signature() changes when THEME_PREVIEW_CACHE_VERSION changes (the manual escape hatch for a render-geometry change the signature can't otherwise see) | ported | companion/test_companion_app_02.py::test_theme_preview_signature_changes_with_cache_version |
| 80 | cache_path() with no event returns a stable, deterministic filename that differs from the same theme's live-event filename (which contains the event id) — the existing 2-argument call site (the chip grid) keeps working unmodified, D-23 | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_no_event_is_stable_and_distinct_from_live |
| 81 | cache_path() gives two different event ids two different paths, and the same event id twice the same path (D-23/Pitfall 7) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_distinct_event_ids_distinct_paths |
| 82 | cache_path() degrades a non-integer or hostile event id to the same sample path as no event at all, never reaching the filename (T-20-14) | ported | companion/test_companion_app_02.py::test_theme_preview_cache_path_hostile_event_id_degrades_to_sample |
| 83 | preview_png_bytes(theme_id, live_event=row) returns a well-formed PNG for a full runway_events row and for a row missing half its fields (partial rows never raise, D-23) | ported | companion/test_companion_app_02.py::test_theme_preview_png_bytes_live_event_full_and_partial_row |
| 84 | cached_preview_bytes() with no live_event still creates the cache file and returns exactly what preview_png_bytes(theme_id) returns, unchanged by this task (D-23) | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_no_event_unchanged |
| 85 | cached_preview_bytes() keys its cache on the live event's row id: a repeat request for the SAME event serves the on-disk file unchanged (no re-render), and a NEWER event is a cache miss rather than the stale first render (D-23/Pitfall 7) | ported | companion/test_companion_app_02.py::test_theme_preview_cached_bytes_live_event_keyed_by_id |
| 86 | _illustration_filenames() is the per-request union of the static target set and server-persisted manual keys: None and an empty state dir both equal the static set exactly, a seeded manual entry adds exactly one filename, and an entry whose stored name yields no usable key contributes nothing (D-09) | ported | companion/test_companion_app_02.py::test_illustration_filenames_union_contract |
| 87 | every FLASH_KEY_MANUAL_* constant is a FLASH_MESSAGES/FLASH_ROLES key; the six UI-SPEC deck strings resolve byte for byte through _resolve_flash_text(), an unknown key still resolves to None, and no FLASH_MESSAGES value carries a runtime placeholder except the cooldown, rule_replaced, calendar_connected and calendar_connect_ok keys (Phase 15 D-10 widened this in place, not loosened; Phase 17 plan 04 and 20-09-PLAN.md Task 2 each widen it again for the same reason) | ported | companion/test_companion_app_02.py::test_flash_manual_keys_complete_and_byte_identical |
| 88 | page_context() on a request carrying ?resolve=XYZ returns that raw value under resolve_prefix and a dict under manual_resolutions reflecting a seeded entry; every key companion/pages/__init__.py documents is actually present in ctx | ported | companion/test_companion_app_02.py::test_page_context_supplies_resolve_prefix_and_manual_resolutions |
| 89 | the battery millivolt constants are defined in exactly one companion module (companion/battery.py) plus server/poll_loop.py's documented private copy, no other module defines a second battery_percent()/battery_fraction(), and no module outside those two names either endpoint pair together — the legacy linear 4200/3300 pair or the SEED-006 curve's own 4112/2946 pair — with comments and docstrings stripped first, so the prose that explains the rule can neither satisfy nor break it (CFG-39, T-24-03, quick 260923-gaf) | deleted | S: asserted source text via a tokenize scan across every companion/server *.py file for a duplicate battery constant/function definition (banned, guard G2); the real failure mode this guards against — the two homes disagreeing about a percentage for the same reading — is covered behaviourally by row 91 (test_battery_estimate_parity_between_companion_and_server) |
| 90 | companion.battery.BATTERY_DISCHARGE_CURVE is strictly increasing in both columns, runs 0..100, every knot round-trips through battery_percent(), the end-knot clamps are exact, the SEED-006 anchor values hold, NaN is refused, and LOW_BATTERY_DISPLAY_MV is 3540 and sits strictly between the sparkline's fixed range and above BATTERY_LOW_THRESHOLD_MV (SEED-006, quick 260923-gaf) | ported | companion/test_companion_app_02.py::test_battery_discharge_curve_is_well_formed |
| 91 | companion.battery and server.poll_loop's independently-maintained battery-percentage copies (D-27) agree on their curve table, their FULL/EMPTY endpoints, and their output for every integer millivolt value from 2800 to 4400, a few non-integer floats, and a hostile input set — a drift here is exactly T-gaf-02 (SEED-006, quick 260923-gaf) | ported | companion/test_companion_app_02.py::test_battery_estimate_parity_between_companion_and_server |
| 92 | no string literal in companion/draw.py or any companion/pages/*.py module carries a colour value into emitted SVG markup — docstrings excluded, so a paragraph explaining the rule cannot break the scan (CFG-39 contract rule 3) | ported | companion/test_companion_app_02.py::test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route |
| 93 | every <rect>/<circle>/<line>/<path>/<polygon>/<polyline>/<ellipse> emitted by companion/draw.py or a page module carries a class attribute or an explicit fill/stroke — a shape with neither paints SVG-default black and is invisible in one of the two themes (CFG-39 contract rule 4) | ported | companion/test_companion_app_02.py::test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route |
| 94 | every class name companion/draw.py can emit (DRAWING_CLASSES, its own constants) resolves to at least one selector in companion/static/style.css, matched on a selector boundary so `.drawing-axis` is not reported as resolved by `.drawing-axis-label` (CFG-39) | ported | companion/test_companion_app_02.py::test_every_drawing_class_resolves_in_the_served_stylesheet |
| 95 | companion/draw.py imports no page module, nothing from the server package and not companion/layout.py — read off the module's abstract syntax tree, which carries no comment and no docstring at all, so the paragraph stating the rule cannot satisfy it and a dotted module name survives intact (CFG-39) | ported | companion/test_companion_app_02.py::test_draw_module_imports_no_page_and_no_server |
| 96 | every companion/draw.py emitter returns complete markup with no script tag, no external reference and no inline style, and refuses an attribute carrying one — the no-JS floor (D-09) is why this phase server-renders its SVG | ported | companion/test_companion_app_02.py::test_draw_module_emits_no_script_and_no_external_reference |
| 97 | companion/draw.py escapes every interpolated value through its one escape() helper — all five dangerous characters, in element content and in attribute values alike, with no 'this value is always safe' exception (T-24-01) | ported | companion/test_companion_app_02.py::test_draw_module_escapes_every_interpolated_value |
| 98 | companion/draw.py's scales clamp into their caller-supplied FIXED domain and pin at exactly the floor and ceiling positions, usable_pairs() drops a row's label with the row itself, and no helper raises on None/a bool/a negative/a string/a NaN (T-24-04, D-04/A-22) | ported | companion/test_companion_app_02.py::test_draw_module_scales_clamp_and_never_raise |
| 99 | draw.ring_gauge() is ONE size-parameterised emitter whose size moves the radius AND the stroke width (never a CSS-only small variant), draws no value arc at all at 0 and a complete dash-free circle at 1, draws half its own emitted circumference at 0.5, gives every arc an explicit fill route and a class with no colour literal, carries a viewBox plus intrinsic width/height and aria-hidden, and never raises (CFG-40, T-24-04-A) | ported | companion/test_companion_app_02.py::test_ring_gauge_is_one_emitter_whose_size_drives_the_geometry |
| 100 | unauthenticated GET / redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[home] |
| 101 | unauthenticated GET /display redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[display] |
| 102 | unauthenticated GET /flights redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[flights] |
| 103 | unauthenticated GET /airlines redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[airlines] |
| 104 | unauthenticated GET /health redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[health] |
| 105 | unauthenticated GET /device redirects to /login carrying that route as ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_nav_tab_redirects_to_login_with_next[device] |
| 106 | unauthenticated GET /settings (a retired page route) redirects to /login without ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_retired_page_route_redirects_to_login_without_next[settings] |
| 107 | unauthenticated GET /history (a retired page route) redirects to /login without ?next= | ported | companion/test_companion_app_02.py::test_unauth_get_retired_page_route_redirects_to_login_without_next[history] |
| 108 | unauthenticated GET /preview (the retired Preview page's redirect source) redirects to /login without page content (D-22 removed it from NAV_TABS, so no ?next= is carried — it lands on /login, not /history, proving the redirect branch keeps its own session gate) | ported | companion/test_companion_app_02.py::test_unauth_get_preview_redirects_to_login_without_next |
| 109 | unauthenticated GET /preview.png now returns 404 (not a 303 to /login) — the route's session-gated branch is gone, so the request falls through to do_GET's deliberately ungated unknown-path handler | ported | companion/test_companion_app_02.py::test_preview_png_unauth_404_not_login_redirect |
| 110 | unauthenticated GET of a gallery image route redirects to /login without page content (not a NAV_TABS route, so no ?next= is carried) | ported | companion/test_companion_app_02.py::test_unauth_get_gallery_image_redirects_to_login_without_next |
| 111 | unauthenticated POST /settings redirects to /login (the write route is not a tab, so no ?next=) | ported | companion/test_companion_app_02.py::test_unauth_post_settings_redirects_to_login_without_next |
| 112 | unauthenticated POST /poll-now redirects to /login without page content (not a NAV_TABS route, so no ?next= is carried) | ported | companion/test_companion_app_02.py::test_unauth_post_poll_now_redirects_to_login_without_next |
| 113 | GET /static/style.css succeeds without a session, returns a CSS content type, and stays shared-cacheable (public, max-age=300) — this route is a deliberate D-02 gate exemption with no per-user content | ported | companion/test_companion_app_02.py::test_stylesheet_public |
| 114 | GET /static/battery-trend.js succeeds without a session and returns a JavaScript content type | ported | companion/test_companion_app_02.py::test_battery_trend_script_public |
| 115 | GET /static/nav-dropdown.js succeeds without a session, returns a JavaScript content type, and serves the real file | ported | companion/test_companion_app_02.py::test_nav_dropdown_script_public |
| 116 | GET /static/dirty-state.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[dirty-state.js] |
| 117 | GET /static/list-filter.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[list-filter.js] |
| 118 | GET /static/copy-button.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[copy-button.js] |
| 119 | GET /static/freshness.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_02.py::test_static_script_public_and_cacheable[freshness.js] |
| 120 | companion.app.py's 4 new *_SCRIPT_ROUTE constants equal companion/layout.py's 4 new *_SCRIPT_SRC constants, and page_shell() emits a <script> tag for each | ported | companion/test_companion_app_02.py::test_four_new_static_routes_dom_contract_guard |
| 121 | copy-button.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), reads its on-success feedback text from each button's own data-copied-text attribute, and the removed hardcoded "Copied" literal survives only as the one documented fallback (D-06) | ported | companion/test_companion_app_02.py::test_copy_button_script_es5_safe_reads_data_copied_text |
| 122 | dirty-state.js stays ES5-safe (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR), contains NO fetch( any more, reads all seven of the bar's own data-dirty-* attributes, and each restored hardcoded literal survives only as its own documented fallback (CFG-77/CFG-78, 28-08-PLAN.md Task 3) | ported | companion/test_companion_app_02.py::test_dirty_state_script_es5_safe_reads_seven_dirty_bar_attributes |
| 123 | dirty-state.js animates the restored bar's own count element and never its word: exactly one text write site, gated on the text having genuinely changed, written before the class is added, spending the stylesheet's existing .is-fading-in rule through a remove/reflow/re-add with no interval/rAF anywhere — so the role="status" bar announces each change once and never a partial word (CFG-77/CFG-78, 28-08-PLAN.md Task 3; retargets 27-04-PLAN.md Task 2's own status-region version back onto the count element, restoring 23-09-PLAN.md Task 1/D3/CFG-32's original subject) | ported | companion/test_companion_app_03.py::test_dirty_state_animates_the_bars_own_count_element_and_never_its_word |
| 124 | freshness.js stays ES5-safe and keeps the standing HTML-writing-sink ban (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/location.reload/XHR), while fetch(/setTimeout/setInterval are its own single, deliberate, reviewed exception to the sibling scripts' ban list (D-02) — and it actually uses the safe DOMParser/replaceChild/credentials-scoped mechanism this exception was granted for, not merely permitted to | ported | companion/test_companion_app_03.py::test_freshness_script_es5_safe_with_one_reviewed_sink_exception |
| 125 | freshness.js contains no URL-taking navigation form (an assignment to location.href, or a call to location.assign/location.replace/window.open) while still reading window.location.href as its fetch argument — the fetch target can never be influenced by injected markup (19-09-PLAN.md Task 3, D-02/T-19-33) | ported | companion/test_companion_app_03.py::test_freshness_script_no_url_taking_navigation_form |
| 126 | GET /static/panel-lookup.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_panel_lookup_script_public |
| 127 | panel-lookup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval), and never decides whether to open the dialog from viewport dimensions or device orientation (no matchMedia/innerWidth) — that gate is CSS-only, on the Airlines trigger's own rule (quick task 260902-tli) | ported | companion/test_companion_app_03.py::test_panel_lookup_script_es5_safe_and_no_html_write |
| 128 | panel-lookup.js's drop handling names NO canvas API and no object URL, assigns the dropped file to the form's own <input type="file"> through exactly one `new DataTransfer()` (so dropped and picked bytes travel one path, with one size cap and one parser), routes BOTH the drop and the picker through exactly one shared uploadRefusal() called exactly twice, consults it BEFORE assigning, and refuses an untrusted drop event (CFG-51/D19, 25-07-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_panel_lookup_drop_handling_writes_the_forms_own_input_and_no_canvas |
| 129 | the mandatory three-element guard appears exactly once and never mentions the optional replace-form lookup on its own line, that lookup's first occurrence in the source comes after the guard's, it appears exactly once, and the action-attribute setAttribute write appears exactly 3 times (replace/resolve-upload/delete, phase 14 plan 14-05) — pinning the single line that keeps History's lightbox alive (quick task 260903-btu) | ported | companion/test_companion_app_03.py::test_panel_lookup_optional_replace_lookup_stays_outside_mandatory_guard |
| 130 | layout.PANEL_LOOKUP_SCRIPT_SRC equals companion.app.PANEL_LOOKUP_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_panel_lookup_script_route_src_agree |
| 131 | GET /static/flash-cleanup.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_public |
| 132 | flash-cleanup.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/fetch/XHR/timers/innerHTML/document.write/eval), and uses history.replaceState with location.search/location.pathname to strip a consumed ?flash= param (quick task 260903-peo, UIR-19) | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_es5_safe_and_no_html_write |
| 133 | layout.FLASH_CLEANUP_SCRIPT_SRC equals companion.app.FLASH_CLEANUP_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_flash_cleanup_script_route_src_agree |
| 134 | GET /static/poll-cooldown.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_public |
| 135 | poll-cooldown.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), and carries both the D-01 countdown (textContent/removeAttribute/setInterval/clearInterval) and the UXA-15 disable-on-submit affordance (addEventListener) | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_es5_safe_and_no_html_write |
| 136 | layout.POLL_COOLDOWN_SCRIPT_SRC equals companion.app.POLL_COOLDOWN_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_poll_cooldown_script_route_src_agree |
| 137 | GET /static/confirm-submit.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_confirm_submit_script_public |
| 138 | confirm-submit.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/location.assign/location.replace), and carries the native confirm() step (addEventListener/preventDefault/confirm() all present) (D-08/A-26) | ported | companion/test_companion_app_03.py::test_confirm_submit_script_es5_safe_and_no_html_write |
| 139 | layout.CONFIRM_SUBMIT_SCRIPT_SRC equals companion.app.CONFIRM_SUBMIT_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_confirm_submit_script_route_src_agree |
| 140 | GET /static/theme-preview.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_theme_preview_script_public |
| 141 | theme-preview.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers/a page-wide single-grid lookup), and carries the row->chip src-swap contract (addEventListener/querySelector/getAttribute/data-preview-src/data-usage all present) (D-08/D-12/R-11, extended by 21-05-PLAN.md Task 3 from D-22..D-24's own original single-grid version) | ported | companion/test_companion_app_03.py::test_theme_preview_script_es5_safe_and_no_html_write |
| 142 | layout.THEME_PREVIEW_SCRIPT_SRC equals companion.app.THEME_PREVIEW_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_theme_preview_script_route_src_agree |
| 143 | a rendered authenticated page contains exactly one theme-preview.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_theme_preview_script_tag_exactly_once_and_no_bare_inline_script |
| 144 | GET /static/flight-rows.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_flight_rows_script_public |
| 145 | flight-rows.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/timers), and carries the detail-row toggle contract (addEventListener/querySelectorAll/data-row-toggle/flight-detail-row--collapsed/aria-expanded/aria-controls all present) (D-15/R-12) | ported | companion/test_companion_app_03.py::test_flight_rows_script_es5_safe_and_no_html_write |
| 146 | layout.FLIGHT_ROWS_SCRIPT_SRC equals companion.app.FLIGHT_ROWS_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_flight_rows_script_route_src_agree |
| 147 | a rendered authenticated page contains exactly one flight-rows.js <script> tag and no inline <script> without a src (D-15/R-12) | ported | companion/test_companion_app_03.py::test_flight_rows_script_tag_exactly_once_and_no_bare_inline_script |
| 148 | a real GET of /static/flight-rows.js returns 200 with data-row-toggle and flight-detail-row--collapsed present, and none of innerHTML/document.write/=>/ let / const  (21-03-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_real_get_flight_rows_route_serves_expected_body |
| 149 | a rendered authenticated page contains exactly fifteen deferred <script src= tags before the closing body tag, including panel-lookup.js, flash-cleanup.js, poll-cooldown.js, confirm-submit.js, theme-preview.js, flight-rows.js, submit-guard.js, relative-time.js, quick-switch.js and value-controls.js — and NOT login-card.js, which login_shell() alone emits, nor submit-guard.js/relative-time.js/quick-switch.js/value-controls.js on that login shell, which still emits exactly one (retargeted in place by 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_fifteen_deferred_scripts_before_closing_body |
| 150 | a real GET of /static/submit-guard.js returns 200 with an ES5-safe, sink-free body that delegates a submit listener and disables the submitting control from a ZERO-DELAY TIMER (so the browser has already built the form data set, which is what keeps the named theme/language submit buttons working), stands down when another listener cancelled the submission, skips the control poll-cooldown.js already owns, writes no label at all, reuses the ONE existing button:disabled rule still ordered after button:active, and changes no CSP (T14, 22-15-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_submit_guard_script_serves_shared_disable_on_submit_guard |
| 151 | GET /static/relative-time.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_relative_time_script_public |
| 152 | relative-time.js stays ES5-safe and side-effect-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR/setTimeout), carries the ticker contract (setInterval+clearInterval, visibilitychange+document.hidden, textContent, data-relative, querySelectorAll, getAttribute) and no verdict vocabulary at all (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_script_es5_safe_and_no_html_write |
| 153 | layout.RELATIVE_TIME_SCRIPT_SRC equals companion.app.RELATIVE_TIME_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_relative_time_script_route_src_agree |
| 154 | a rendered authenticated page contains exactly one relative-time.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_relative_time_script_tag_exactly_once_and_no_bare_inline_script |
| 155 | a real GET of /static/relative-time.js returns 200 with the served ticker body — the data-relative hook present, the visibility gate present, and none of innerHTML/document.write/=>/ let / const  (23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_relative_time_route_serves_the_ticker |
| 156 | relative-time.js's BUCKET_BOUNDARIES equals layout._age_bucket()'s own three boundaries, in order, with each number appearing exactly once in the script's code and the array actually read (23-RESEARCH.md Pitfall 4, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_ladder_mirrors_layouts_own_boundaries |
| 157 | every one of relative-time.js's nine wordings, filled with the quantity layout._age_bucket() picks, EQUALS relative_age_text()/relative_future_text()'s own output for every bucket in both languages; the waiting phrase is translated; and every attribute name reaches both the rendered <body> and the script that reads it (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_wordings_equal_the_ladders_own_output |
| 158 | every one of layout.DURATION_ATTRS' four wordings, filled with the quantity layout._age_bucket() picks, EQUALS layout.duration_text()'s own output for every bucket in both languages, and every attribute name reaches value-controls.js (CFG-73 Bug A, 28-03-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_duration_wordings_equal_the_ladders_own_output |
| 159 | layout.relative_time_html(countdown=True) marks the element, keeps the future form while the instant is ahead, reads the translated waiting wording once it has passed — never an age and never a warn/error/alert token — and the default rendering is byte-identical to the element 23-03 shipped (D14/CFG-34, 23-05-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_relative_time_html_countdown_keyword_is_marked_and_neutral |
| 160 | GET /static/quick-switch.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_quick_switch_script_public |
| 161 | quick-switch.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR/setInterval and no URL-taking navigation), carries the optimistic-switch contract (aria-checked, preventDefault, stopPropagation, textContent, credentials same-origin, redirect manual, X-Requested-With, encodeURIComponent) and reaches its rollback from BOTH terminal branches through the ES3-safe bracket form (D2/CFG-36, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_quick_switch_script_es5_safe_and_no_html_write |
| 162 | layout.QUICK_SWITCH_SCRIPT_SRC equals companion.app.QUICK_SWITCH_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_quick_switch_script_route_src_agree |
| 163 | a rendered authenticated page contains exactly one quick-switch.js <script> tag and no inline <script> without a src (D-32) | ported | companion/test_companion_app_03.py::test_quick_switch_script_tag_exactly_once_and_no_bare_inline_script |
| 164 | a real GET of /static/quick-switch.js returns 200 with the served optimistic-switch body — layout.REFRESH_PENDING_ATTR and layout.QUICK_SWITCH_FAILED_ATTR both named, and none of innerHTML/document.write/=>/ let / const  (23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_quick_switch_route_serves_the_optimistic_switch |
| 165 | quick-switch.js's PENDING_ATTR, freshness.js's PENDING_ATTR and layout.REFRESH_PENDING_ATTR are the same attribute name — the setter, the skip and the Python that defines it, pinned in one place so a rename on any one side fails rather than silently disabling the D1-races-D2 rule (T-23-26, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_quick_switch_pending_marker_is_layouts_own_name |
| 166 | GET /static/value-controls.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_03.py::test_value_controls_script_public |
| 167 | value-controls.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/XHR/fetch/timer and no URL-taking navigation), carries the steering contract (preventDefault, getAttribute, dispatchEvent, aria-valuenow, aria-valuetext, parseFloat and the three Math clamps) and NEVER holds the value — exactly one `.value` assignment, inside the one write helper, reached by exactly two callers (the native input the form posts, and the nameless MIRROR written only from inside paint(), strictly downstream of a read off that field), and at least one read of `field.value` back (CFG-46, 25-01-PLAN.md Task 1; the mirror clause 25-05-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_value_controls_script_es5_safe_and_never_holds_the_value |
| 168 | layout.VALUE_CONTROLS_SCRIPT_SRC equals companion.app.VALUE_CONTROLS_SCRIPT_ROUTE | ported | companion/test_companion_app_03.py::test_value_controls_script_route_src_agree |
| 169 | a rendered authenticated page contains exactly one value-controls.js <script> tag and no inline <script> without a src (D-32, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_value_controls_script_tag_exactly_once_and_no_bare_inline_script |
| 170 | a real GET of /static/value-controls.js returns 200 with the served steering body — all FIFTEEN of layout's VALUE_CONTROL_* seam attributes named, and none of innerHTML/insertAdjacentHTML/document.write/eval/=>/ let / const /backtick (CFG-46, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_real_get_value_controls_route_serves_the_registration_seam |
| 171 | value-controls.js wakes the save bar through the ONE public surface — a bubbling event constructed identically in both its branches, whose name is dirty-state.js's own delegated document-level listener, pinned from both sides together with that listener's e.target.form filter, because a control that changes a value without waking the save bar silently loses the user's edit (CFG-46, 25-01-PLAN.md Task 1) | ported | companion/test_companion_app_03.py::test_value_controls_wakes_the_save_bar_through_dirty_states_own_listener |
| 172 | companion/static/style.css's `.js` gate hides by default (`.js-gate { display: none }` — out of the layout AND out of the tab order, never visibility or opacity) and reveals under `.js`, and no gate rule anywhere runs the reverse direction, which flashes a dead control on every load and shows it permanently when a script fails (D-09/CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_js_gate_hides_by_default_and_reveals_under_js |
| 173 | the shared control vocabulary reuses references/control-density.md's RELOCATED hit-area values VERBATIM from `.copy-btn` (every geometry declaration equal, the same ::before inset, and 44px recomputed from the declared box plus inset rather than restated), `.value-control`/`.value-control__handle` both carry `touch-action: none` so a touch drag is not claimed by the browser's own panning gesture, and not one added rule introduces a colour literal (CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_control_vocabulary_reuses_the_registered_hit_area_verbatim |
| 174 | companion/static/style.css still carries exactly ONE @supports selector(:has(*)) block, counted on COMMENT-STRIPPED source and on the opening brace — the raw five-line grep counts the four paragraphs that explain the rule (CFG-46, 25-01-PLAN.md Task 2) | ported | companion/test_companion_app_03.py::test_style_css_carries_exactly_one_has_feature_query_block |
| 175 | companion.battery.battery_life_estimate() is TOTAL over six series shapes (empty, one row, two flat rows, falling, RISING, and a newest row with a None reading) and never states a figure the data cannot support: a charged device's rising slope returns days_remaining=None rather than a negative or infinite lifetime, a flat series returns None, a series at or below the curve's bottom knot floors at zero, a series above the curve's top knot with falling millivolts but no measurable state-of-charge drop reports FALLING with days_remaining=None, the 'no reading' and 'not enough history' states are DIFFERENT named values, the falling series' figure is recomputed in STATE-OF-CHARGE space via battery_fraction() (SEED-006, quick 260923-gaf) rather than by millivolt extrapolation, and the relative cadence factor is available in all six shapes and doubles exactly when the proposed cadence doubles (CFG-49, 25-01-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_battery_life_estimate_is_total_and_never_claims_what_it_cannot |
| 176 | companion/battery.py imports nothing from companion.pages and nothing from the server package — an ast scan of the real module, not its docstring's claim (D-27/CFG-49, 25-01-PLAN.md Task 3) | ported | companion/test_companion_app_03.py::test_battery_module_imports_neither_a_page_module_nor_the_server_package |
| 177 | every control in _NO_JS_CONTROL_REGISTRY holds its value in a native <input>/<select> the server renders unconditionally, associated with the form that posts it, with EVERY element carrying its wrapper attribute also carrying the .js-gate class — and the machine that judges that is proven non-vacuous against four fixtures built from real group-builder output: one correct control it must accept, and three it must reject (a field name nothing renders, a wrapper rendered outside the gate, and a value held by a div instead of a native input) (CFG-46/D-09, 25-01-PLAN.md Task 4) | ported | companion/test_companion_app_03.py::test_no_js_control_contract_holds_for_every_registered_control |
| 178 | layout.JS_GATE_CLASS resolves to a real selector in companion/static/style.css on a SELECTOR BOUNDARY — the class a page module writes and the rule that hides it pinned as one name, because a rename on either side alone renders a script-only affordance permanently with scripts blocked (CFG-46/D-09, 25-01-PLAN.md Task 4) | ported | companion/test_companion_app_04.py::test_js_gate_class_resolves_to_a_real_selector_on_a_boundary |
| 179 | companion/static/style.css honours the phase's motion budget: every @keyframes name is defined exactly once, every animation reference resolves to a block in the same file, every animation duration comes from a var(--motion-*) token rather than a bare literal, the live prefers-reduced-motion reduce/no-preference block counts equal EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS/EXPECTED_REDUCED_MOTION_NO_PREFERENCE_BLOCKS, and neither interpolate-size nor calc-size() appears — all measured on COMMENT-STRIPPED source, because this stylesheet's comments quote every token the check counts (D3/CFG-32, 23-01-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_style_css_honours_the_motion_budget |
| 180 | GET /static/login-card.js succeeds without a session and returns a shared-cacheable JavaScript content type | ported | companion/test_companion_app_04.py::test_login_card_script_public |
| 181 | login-card.js stays ES5-safe and sink-free (no let/const/arrow/backtick/innerHTML/outerHTML/insertAdjacentHTML/document.write/eval/fetch/XHR), carries the reveal contract (addEventListener/querySelector/getAttribute/data-login-reveal/aria-pressed/the class-at-load modifier) and duplicates no server-side throttling constant (X3, T-22-46/T-22-49) | ported | companion/test_companion_app_04.py::test_login_card_script_es5_safe_and_no_html_write |
| 182 | layout.LOGIN_CARD_SCRIPT_SRC equals companion.app.LOGIN_CARD_SCRIPT_ROUTE | ported | companion/test_companion_app_04.py::test_login_card_script_route_src_agree |
| 183 | a rendered login page contains exactly ONE <script occurrence, the deferred LOGIN_CARD_SCRIPT_SRC tag, with no inline script and no nonce — login_shell() emitted zero script tags before this plan (X3, 22-13-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_login_page_emits_exactly_one_script_tag |
| 184 | the server-rendered show-password toggle carries the hidden attribute, type="button", aria-pressed="false", both translated accessible names and .copy-btn's own icon-only geometry — and the field's padding modifier is NOT server-rendered (X3, the no-JS floor by construction) | ported | companion/test_companion_app_04.py::test_login_reveal_toggle_is_server_hidden_and_named |
| 185 | a login POST with the wrong password re-renders the form with the exact copy and sets no cookie | ported | companion/test_companion_app_04.py::test_login_wrong_password |
| 186 | a login POST with the right password sets a cookie with HttpOnly/Secure/SameSite=Strict and redirects to / (Home) | ported | companion/test_companion_app_04.py::test_login_correct_password |
| 187 | an unauthenticated GET /health redirects with ?next=%2Fhealth, and logging in with that next value returns the user to /health, not /settings | ported | companion/test_companion_app_04.py::test_deep_link_return_round_trip |
| 188 | a login POST with the correct password and next='https://evil.example' redirects to the / (Home) fallback, never to the crafted value (T-06.6.2-12) | ported | companion/test_companion_app_04.py::test_open_redirect_rejected[https://evil.example] |
| 189 | a login POST with the correct password and next='//evil.example' redirects to the / (Home) fallback, never to the crafted value (T-06.6.2-12) | ported | companion/test_companion_app_04.py::test_open_redirect_rejected[//evil.example] |
| 190 | GET /login?next=/nonexistent-route (not a real NAV_TABS member) renders the plain login form with no hidden next input | ported | companion/test_companion_app_04.py::test_login_get_with_unrecognised_next_carries_no_hidden_field |
| 191 | GET /login (no session) is rendered by the dedicated login_shell(), not page_shell() — no sidebar/mobile-nav markup, autocomplete present | ported | companion/test_companion_app_04.py::test_login_page_uses_dedicated_login_shell |
| 192 | GET /login with no error renders the stacked card (a .login-form with a .login-form__input and a bare page-title brand mark, no glyph, no sprite) and carries NEITHER aria-invalid NOR aria-describedby — never aria-invalid="false" — with style.css carrying the field/primary/error-border rules it had none of before (X3, 22-13-PLAN.md Task 1) | ported | companion/test_companion_app_04.py::test_login_clean_render_carries_no_error_association |
| 193 | a wrong-password login render carries aria-invalid="true", aria-describedby="login-error" and a role="alert" message in the existing .field-error text-label treatment, rendered between the field and the primary (X3, 22-UI-SPEC.md §5 contract 5) | ported | companion/test_companion_app_04.py::test_login_error_render_is_programmatically_associated |
| 194 | a locked-out login render puts the server-computed lockout sentence in the SAME .field-error text-label role=alert treatment under the field, with aria-describedby but deliberately no aria-invalid (X3, one error voice) | ported | companion/test_companion_app_04.py::test_login_lockout_render_shares_the_one_error_voice |
| 195 | page_shell() and login_shell() both emit lang="en" (D-01/UXA-09 language-policy regression guard) | ported | companion/test_companion_app_04.py::test_both_shells_agree_on_document_language |
| 196 | authenticated GET / returns 200 and contains its own 'Home' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/-Home] |
| 197 | authenticated GET /display returns 200 and contains its own 'Display' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/display-Display] |
| 198 | authenticated GET /flights returns 200 and contains its own 'Flights' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/flights-Flights] |
| 199 | authenticated GET /airlines returns 200 and contains its own 'Airlines' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/airlines-Airlines] |
| 200 | authenticated GET /health returns 200 and contains its own 'Health' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/health-Health] |
| 201 | authenticated GET /device returns 200 and contains its own 'Device' heading | ported | companion/test_companion_app_04.py::test_authenticated_tab_returns_200_with_its_own_heading[/device-Device] |
| 202 | authenticated GET /preview (the retired Preview page route) redirects to /flights (D-22, retargeted by phase 18) | ported | companion/test_companion_app_04.py::test_preview_redirects_to_flights |
| 203 | authenticated GET /settings (a pre-phase-18 page route) redirects to /display with a fixed literal target | ported | companion/test_companion_app_04.py::test_legacy_page_route_redirects_with_a_fixed_literal_target[/settings-/display] |
| 204 | authenticated GET /history (a pre-phase-18 page route) redirects to /flights with a fixed literal target | ported | companion/test_companion_app_04.py::test_legacy_page_route_redirects_with_a_fixed_literal_target[/history-/flights] |
| 205 | authenticated GET /preview carrying an arbitrary query string (including a next=-shaped and an https://evil.example-shaped value) still redirects to the identical /flights location — no request value influences the target | ported | companion/test_companion_app_04.py::test_preview_redirect_ignores_query_string |
| 206 | authenticated GET /config (the retired settings path) returns 404 — D-26 declines a redirect since this is a fresh URL at inception, not a deprecated bookmark | ported | companion/test_companion_app_04.py::test_old_settings_path_404s_authenticated |
| 207 | an authenticated POST /settings redirects to /display (the default return page) carrying a flash query | ported | companion/test_companion_app_04.py::test_settings_post_redirects_to_display_with_flash |
| 208 | a POST /settings with a valid theme change and an empty quiet_hours_start returns 200, shows the newly-picked theme still selected, shows the quiet-hours field error, carries no flash banner, and persists nothing on disk (D-07/A-25) | ported | companion/test_companion_app_04.py::test_rejected_settings_save_rerenders_200_with_input_and_error_persists_nothing |
| 209 | authenticated GET / renders the rebuilt Home page (D-01/D-04/D-05) with the Frame strip's two switch forms, three stat-tile elements, the picture/recent-flights row, and the recent-flights list under the grouped Advanced navigation, carrying none of the retired Quick-actions card or Poll form | ported | companion/test_companion_app_04.py::test_home_page_renders_widgets |
| 210 | POST /quick/display with state=off then state=on flips display_enabled on disk and redirects to Display (D-16) with the matching flash; a crafted state value redirects with quick_failed and writes nothing | ported | companion/test_companion_app_04.py::test_quick_display_toggle_round_trip |
| 211 | POST /quick/quiet-hours with state=on then state=off flips quiet_hours_enabled on disk, redirects to Display (D-16) with the matching flash, and never touches display_enabled | ported | companion/test_companion_app_04.py::test_quick_quiet_hours_toggle_round_trip |
| 212 | POST /quick/display honours return_to (/ or /display), falls back to Display for a hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the invalid-state early return honours return_to too (D-01/R-02) | ported | companion/test_companion_app_04.py::test_quick_display_honours_return_to |
| 213 | POST /quick/quiet-hours honours return_to (/ or /display), falls back to Display for a hostile value (https://evil.example/, //evil.example, /flights) or an absent field, and the invalid-state early return honours return_to too (D-01/R-02) | ported | companion/test_companion_app_04.py::test_quick_quiet_hours_honours_return_to |
| 214 | POST /quick/display and POST /quick/quiet-hours answer a form post with exactly today's 303-and-flash and a request carrying the fetch header with a 204, empty body and no Location — the same write either way, and a crafted state value is never a 204 (D2/CFG-36, T-23-26, 23-07-PLAN.md Task 1) | ported | companion/test_companion_app_04.py::test_quick_routes_answer_204_for_a_fetch_and_303_for_a_form |
| 215 | POST /quick/led stores one explicit led_enabled keyword and carries every other flag forward, redirects to /device with its own flash for a form post, answers 204 with an empty body for a fetch, redirects with the generic failure flash and writes nothing for a crafted state, falls back to /device for every non-member return_to, and is not reachable by GET at all (D2/CFG-36, T-23-23/T-23-24/T-23-25, 23-07-PLAN.md Task 2) | ported | companion/test_companion_app_04.py::test_quick_led_route_saves_redirects_and_negotiates |
| 216 | unauthenticated POST /quick/led redirects to /login without page content | ported | companion/test_companion_app_04.py::test_unauth_post_quick_led_redirects_to_login |
| 217 | unauthenticated POST /quick/display redirects to /login without page content | ported | companion/test_companion_app_04.py::test_unauth_post_quick_display_redirects_to_login |
| 218 | a scoped POST /settings (scope=display / scope=device) persists only its own page's groups, carries the other page's checkbox state forward instead of flipping it off, redirects to the page it came from, and never honours a crafted return_to | ported | companion/test_companion_app_04.py::test_scoped_settings_save_carries_other_page_forward |
| 219 | GET /display and GET /device split the settings groups per companion/screens.py (20-07 moved Runway/Calendar/the rules editor to Display, D-10/D-11), each carrying its hidden scope/return_to fields and the screen-type caption; Manual refresh lives on Device only | ported | companion/test_companion_app_04.py::test_display_and_device_pages_split_the_groups |
| 220 | every HTML response (an authenticated page and the login page alike) carries Cache-Control: no-store, so the back button and shared caches never replay a page after sign-out | ported | companion/test_companion_app_04.py::test_html_pages_are_no_store |
| 221 | an authenticated HTML response carries a Content-Security-Policy header equal (string equality, not substring) to companion.app.CONTENT_SECURITY_POLICY | ported | companion/test_companion_app_04.py::test_authenticated_html_carries_exact_csp |
| 222 | the CSP's script-src directive is 'self' with no 'unsafe-inline' anywhere in it (Task 1 removed the app's last two inline <script> elements, so no exception is needed) | ported | companion/test_companion_app_04.py::test_csp_script_src_strict_no_unsafe_inline |
| 223 | a 303 redirect response (the unauthenticated bounce to /login) carries all four hardening headers, including the CSP — before this plan redirect() sent none of them | ported | companion/test_companion_app_04b.py::test_redirect_carries_four_hardening_headers |
| 224 | the static CSS response (the send_bytes() path) also carries the CSP header | ported | companion/test_companion_app_04b.py::test_static_css_response_carries_csp |
| 225 | POST /ui-theme with no session cookie redirects to /login and does not set a ui_theme cookie (T-19-04: an unauthenticated caller cannot set another visitor's UI theme) | ported | companion/test_companion_app_04b.py::test_ui_theme_post_without_session_redirects_to_login |
| 226 | POST /logout with no session cookie redirects to /login (T-19-04: gating a logout costs a signed-out caller nothing) | ported | companion/test_companion_app_04b.py::test_logout_post_without_session_redirects_to_login |
| 227 | POST /ui-lang with ui_lang=fr/en sets the sp_ui_lang cookie (HttpOnly, SameSite=Strict) and redirects to the referring tab; ui_lang=de sets no cookie | ported | companion/test_companion_app_04b.py::test_ui_lang_post_round_trip |
| 228 | POST /ui-lang with no session cookie redirects to /login and does not set a sp_ui_lang cookie (T-20-01) | ported | companion/test_companion_app_04b.py::test_ui_lang_post_without_session_redirects_to_login |
| 229 | POST /ui-mode with a valid session now takes the unknown-route 404 path (D-17, the route/handler/dispatch line are deleted together) | ported | companion/test_companion_app_04b.py::test_post_to_the_deleted_display_mode_route_with_session_now_404s |
| 230 | a cookie-free GET (session cookie only, no sp_ui_lang) with Accept-Language: fr-FR,fr;q=0.9 renders <html lang="fr"; with Accept-Language: en-GB renders <html lang="en" (D-03) | ported | companion/test_companion_app_04b.py::test_accept_language_resolves_html_lang_with_no_cookie |
| 231 | the sp_ui_lang cookie beats Accept-Language when both are present (D-03) | ported | companion/test_companion_app_04b.py::test_ui_lang_cookie_beats_accept_language |
| 232 | #site-nav-toggle renders icon-gear (never icon-hamburger), its aria-label is NAV_TOGGLE_LABEL translated through i18n's real per-request path in both EN and FR, and the panel it opens still holds the language/theme switches and Sign out with zero page-navigation links (CFG-76) | ported | companion/test_companion_app_04b.py::test_the_nav_toggle_wears_the_gear_and_opens_the_same_panel |
| 233 | authenticated GET /device pre-fills Wake interval with SKYPANE_SLEEP_S=900 when nothing is stored, and a stored wake_interval_s=120 always wins over that environment value | ported | companion/test_companion_app_04b.py::test_wake_interval_env_prefill_and_on_disk_precedence |
| 234 | authenticated GET /device degrades a below-floor SKYPANE_SLEEP_S=30 (the shipped deploy/skypane.env.example value) to the placeholder empty state, never a value attribute the form could not submit | ported | companion/test_companion_app_04b.py::test_wake_interval_below_floor_env_degrades_to_placeholder |
| 235 | GET /login?next=/display (a real NAV_TABS member) renders a hidden next field carrying /display, surviving the round trip | ported | companion/test_companion_app_04b.py::test_login_get_with_settings_next_carries_hidden_field |
| 236 | app.SETTINGS_ROUTE and config_page.SETTINGS_ROUTE agree, NAV_TABS opens with HOME_ROUTE, and NAV_ICON_IDS' keys equal the nav route slugs one-to-one | ported | companion/test_companion_app_04b.py::test_settings_route_and_icon_map_cross_module_contract |
| 237 | the nav tuple, the page-titles dict, and the slug-to-icon map all agree in size and key set, and the settings page module's own route constant is the nav tuple's first route — a standing guard against silent drift when the route set changes again | ported | companion/test_companion_app_04b.py::test_nav_page_titles_icon_route_standing_contract_guard |
| 238 | POST /logout clears the session cookie (Max-Age=0) | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 239 | replaying the exact session cookie after Sign out is rejected (A-33: revoked server-side, not just cleared client-side) | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 240 | GET /logout no longer accepts the request (404) — D-11 closes the GET-triggered logout hole | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 241 | a tab request after logout (no cookie presented) is refused again | ported | companion/test_companion_app_04b.py::test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward |
| 242 | an unknown path returns 404 with the exact 'Page not found.' copy | ported | companion/test_companion_app_04b.py::test_unknown_path_404 |
| 243 | an authenticated 404 opens with the shared page_header() (page-title, not text-heading) and shows the Health nav dot when state is seeded error | ported | companion/test_companion_app_04b.py::test_authenticated_404_uses_page_header_and_shows_health_dot |
| 244 | an UNAUTHENTICATED 404 renders no health-dot markup under the same seeded error state — the leak guard for the two pre-auth call sites (_serve_stylesheet, _serve_script_file) | ported | companion/test_companion_app_04b.py::test_unauthenticated_404_never_leaks_health_state |
| 245 | authenticated GET /preview.png returns 404 with the exact 'Page not found.' copy even with a real 960,000-byte panel.bin present — the route is gone, not empty | ported | companion/test_companion_app_04b.py::test_preview_png_404_even_with_real_panel |
| 246 | an authenticated gallery image is never advertised as storable by a shared/intermediary cache (WR-02) | ported | companion/test_companion_app_04b.py::test_gallery_response_is_never_shared_cacheable |
| 247 | a gallery request with parent-directory segments returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 248 | a gallery request with an absolute path returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 249 | a gallery request with a null byte returns 404 | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 250 | the canary file placed one level above the gallery directory never appears in any traversal response | ported | companion/test_companion_app_04b.py::test_gallery_traversal_and_canary_never_leaks |
| 251 | an authenticated GET /illustration/air-france.png returns 200, image/png, and a non-empty body | ported | companion/test_companion_app_04b.py::test_illustration_real_key_returns_png |
| 252 | an authenticated GET for an illustration key not in the membership set returns 404 | ported | companion/test_companion_app_04b.py::test_illustration_unknown_key_404 |
| 253 | authenticated GET requests for adversarial illustration paths (path traversal) all return 404 with no file content | ported | companion/test_companion_app_04b.py::test_illustration_traversal_key_404 |
| 254 | an unauthenticated GET /illustration/air-france.png redirects to /login, never returns image bytes | ported | companion/test_companion_app_04b.py::test_illustration_unauthenticated_redirects_to_login |
| 255 | GET /illustration/{key}.png for a manual key: 404 with no registry entry, 404 with an entry but no override file, and 200/image/png once both exist | ported | companion/test_companion_app_04b.py::test_illustration_manual_key_read_path_states |
| 256 | Pitfall 3's warning sign made executable: POST /illustration/{key}.png for a manual key that was never registered returns 404 and writes nothing to the override directory; once the key is registered via add_entry(), the identical POST succeeds | ported | companion/test_companion_app_04b.py::test_illustration_manual_key_post_unregistered_then_registered |
| 257 | an authenticated GET /theme-preview/{id}.png returns 200, image/png, and a real PNG body for every id in device_config.THEME_IDS — no theme is unreachable | ported | companion/test_companion_app_04b.py::test_theme_preview_real_key_returns_png_for_every_theme |
| 258 | an authenticated GET for a theme id not in the membership set returns the same 404 page an unknown runway/illustration id produces | ported | companion/test_companion_app_04b.py::test_theme_preview_unknown_key_404 |
| 259 | authenticated GET requests for adversarial theme-preview paths (path traversal) all return 404 with no file content | ported | companion/test_companion_app_04b.py::test_theme_preview_traversal_key_404 |
| 260 | an unauthenticated GET /theme-preview/white.png redirects to /login, never returns image bytes | ported | companion/test_companion_app_04b.py::test_theme_preview_unauthenticated_redirects_to_login |
| 261 | GET /theme-preview/white.png?live=1 with no runway_events row at all still returns 200/image/png (the sample-scene fallback, D-23) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 262 | GET /theme-preview/white.png?live=1 with a seeded runway_events row returns 200/image/png, and a second request for the same latest event is served from the cache without growing the cache directory (D-23/Pitfall 7) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 263 | inserting a NEWER runway_events row changes both the served live-preview bytes and the cache file it comes from — a newer flight is a cache miss, never a stale hit served forever (D-23/Pitfall 7) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 264 | GET /theme-preview/nope.png?live=1 returns the same 404 an unknown theme id always returns — the membership test still runs before any query is even parsed | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 265 | ?live=0 and a missing ?live query both serve the sample variant, never the live one, even with a runway_events row present (D-23) | ported | companion/test_companion_app_04b.py::test_theme_preview_live_branch_cache_and_fallback_behaviour |
| 266 | uploading a real PNG over real HTTP to a real companion/app.py subprocess changes what GET /illustration/air-france.png serves, even with a traversal-shaped declared filename in the part header | ported | companion/test_companion_app_04b.py::test_illustration_upload_round_trip_replaces_served_bytes |
| 267 | the overridden air-france render and the vueling-airlines render (the same source image) come out of the identical illustration_normalize pipeline (D-03) | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 268 | the upload was written to {state_dir}/illustration_overrides/air-france.png, and nothing else was created in that directory | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 269 | the vendored server/assets/icons/illustrations/air-france.png file is provably byte-identical (hash, size, and mtime) after a successful upload | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 270 | select_illustration() given the harness's own state_dir resolves Air France to the override the real route just wrote; with no state_dir it still resolves to the vendored file | ported | companion/test_companion_app_05.py::test_illustration_override_effects_after_a_real_upload |
| 271 | POSTing a non-image payload is rejected with the rejection flash key and writes no override file | ported | companion/test_companion_app_05.py::test_illustration_non_image_upload_is_rejected |
| 272 | POSTing a body over MAX_ILLUSTRATION_UPLOAD_BYTES is rejected, writes no override file, and the drain leaves the service healthy for the next request | ported | companion/test_companion_app_05.py::test_illustration_oversized_upload_is_rejected_and_connection_stays_healthy |
| 273 | POSTing a valid payload to a key outside the membership set, and to three traversal-shaped paths, all 404 and write nothing to the override directory | ported | companion/test_companion_app_05.py::test_illustration_post_unknown_and_traversal_keys_returns_404 |
| 274 | an unauthenticated POST /illustration/tunisair.png redirects to /login and writes no override file | ported | companion/test_companion_app_05.py::test_illustration_unauthenticated_post_redirects_to_login_and_writes_nothing |
| 275 | unauthenticated POSTs to /airlines/resolve and /airlines/manual-resolutions/{prefix}/delete both redirect to /login and write no manual_resolutions.json — the state dir is unchanged, not only the status code | ported | companion/test_companion_app_05.py::test_manual_resolve_and_delete_routes_require_auth_and_write_nothing |
| 276 | POST /airlines/resolve re-validates the prefix against the live unresolved-prefix registry on write (D-11): a well-shaped but unregistered prefix writes nothing and gets the stale flash; the identical POST succeeds once the prefix is a live registry member | ported | companion/test_companion_app_05.py::test_manual_resolve_post_revalidates_prefix_against_live_registry |
| 277 | each add_entry() rejection reaches its own distinct flash key and persists nothing (empty/too-long/reserved names, and the registry cap); the D-03 branch: a brand-new name redirects with resolve= (Step B offered) while a name already covered by existing artwork redirects without it | ported | companion/test_companion_app_05.py::test_manual_resolve_post_rejection_mapping_and_d03_branch |
| 278 | POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry, leaves the override PNG on disk (D-08), and redirects to /airlines with no flash; a second identical POST is a no-op that also redirects without an error flash; a malformed prefix 404s without touching the registry | ported | companion/test_companion_app_05.py::test_manual_resolution_delete_route_full_contract |
| 279 | POST /airlines/resolve redirects with the manual_save_failed flash key (never a dropped connection) when add_entry() cannot write because the state dir is read-only — the exact failure mode CR-01 fixed, exercised end to end (WR-11) - expected the manual_save_failed flash key when add_entry() fails to write, got '/airlines?resolve=FLD&flash=manual_resolved' | ported | companion/test_companion_app_01.py::test_resolve_post_redirects_manual_save_failed_when_state_dir_is_read_only |
| 280 | POST /airlines/manual-resolutions/{prefix}/delete redirects with the manual_delete_failed flash key, leaving the entry in place, when delete_entry() cannot write because the state dir is read-only (WR-11) - expected the manual_delete_failed flash key when delete_entry() fails to write, got '/airlines' | ported | companion/test_companion_app_01.py::test_delete_post_redirects_manual_delete_failed_when_state_dir_is_read_only |
| 281 | unauthenticated POSTs to /settings/rules/add and /settings/rules/{kind}/{value}/delete both redirect to /login and write no colour_rules.json — the state dir is unchanged, not only the status code | ported | companion/test_companion_app_05.py::test_rules_routes_require_auth_and_write_nothing |
| 282 | the rules add form and each delete form sit outside <form id=SETTINGS_FORM_ID> (D-10): neither carries the settings form's id nor a form= attribute pointing at it, and a rule add followed by an unrelated settings-form save leaves both the rule and every device-config setting intact (15-VALIDATION.md row 10) | ported | companion/test_companion_app_05.py::test_rules_add_and_delete_forms_sit_outside_settings_form |
| 283 | raw URL-encoded no-JS POSTs to the rules add route (15-VALIDATION.md row 11): a first add flashes rule_added, a second add for the same key (case-insensitive input) flashes rule_replaced and echoes the normalised key back, and the registry holds exactly one entry with the second theme | ported | companion/test_companion_app_05.py::test_rules_add_route_no_js_added_then_replaced |
| 284 | the rules add route's rejection paths: a malformed value for the selected kind flashes rule_key_invalid and writes nothing; a crafted kind and a crafted theme id each flash the generic rule_save_failed and write nothing; filling the registry to its cap and adding one more flashes rule_registry_full without persisting the at-cap entry | ported | companion/test_companion_app_05.py::test_rules_add_route_rejection_paths |
| 285 | POST /settings/rules/{kind}/{value}/delete removes the registry entry and flashes rule_deleted; a second identical delete of an already-absent entry is a no-op that redirects with no flash; a malformed kind segment and a malformed value segment each 404 without touching an unrelated existing entry | ported | companion/test_companion_app_05.py::test_rules_delete_route_full_contract |
| 286 | a rule written directly to state_dir between two GETs of the Settings page appears in the second render — proving page_context() reads colour_rules fresh per request rather than through any process-scoped cache | ported | companion/test_companion_app_05.py::test_rules_page_context_reads_fresh_per_request |
| 287 | a first poll trigger redirects with the poll_triggered flash key | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 288 | the first poll trigger's run_once() was served by the fake ADS-B providers (adsbfi and adsblol called, no live network) | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 289 | an immediate second poll trigger redirects with the poll_cooldown flash key | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 290 | a fresh second-opener session is refused by the same cooldown (server-global, not per-session) | ported | companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence |
| 291 | a genuine poll-trigger failure redirects with the distinct poll_failed flash key, never save_failed | ported | companion/test_companion_app_05.py::test_poll_trigger_failure_uses_distinct_flash_key |
| 292 | two genuinely overlapping POST /poll-now requests: exactly one gets the poll_already_running flash key, proving the server-side _POLL_LOCK serializes execution | ported | companion/test_companion_app_05.py::test_poll_now_concurrent_requests_serialize_on_the_lock |
| 293 | saving a calendar feed with three in-window flights performs exactly one refresh call and the rendered banner names the plural flight count (D-06) | ported | companion/test_companion_app_05.py::test_calendar_connect_reports_plural_count |
| 294 | saving a calendar feed with exactly one in-window flight pins the singular form ('1 flight', never '1 flights') | ported | companion/test_companion_app_05.py::test_calendar_connect_reports_singular_count |
| 295 | a syntactically valid feed with nothing in the frame's window reports success with a 0 count, distinguishable from a failure | ported | companion/test_companion_app_05.py::test_calendar_connect_zero_entries_still_succeeds |
| 296 | a failing fetch redirects with the single generic failure flash key, renders the exact failure copy, and the URL is saved regardless (D-06) | ported | companion/test_companion_app_05.py::test_calendar_sync_failure_reports_generic_message_and_still_saves |
| 297 | T-17-FLASH: a raised error whose message embeds the full URL never surfaces the token, path segment, query-parameter name, or whole URL in the Location header or any served response body — the served Settings page legitimately shows the masked host + ellipsis once connected (D-14/R-10, extended by 21-07-PLAN.md Task 2) | ported | companion/test_companion_app_05.py::test_calendar_sync_failure_never_leaks_the_url |
| 298 | checking the disconnect box redirects with the disconnected flash key, and the calendar's previously-fetched flights are actually erased from disk (D-04) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_reports_deletion_and_erases_entries |
| 299 | a bare authenticated POST /settings/calendar/disconnect with no confirm field returns 200 with the confirmation copy and leaves the calendar connected (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_bare_post_renders_confirmation_and_touches_nothing |
| 300 | an authenticated POST /settings/calendar/disconnect with confirm=maybe renders the confirmation page rather than disconnecting anything (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_confirm_maybe_renders_confirmation_and_touches_nothing |
| 301 | an authenticated POST /settings/calendar/disconnect with confirm=yes 303-redirects with the disconnected flash key and actually disconnects the calendar (D-08/A-26) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_confirm_yes_disconnects |
| 302 | an unauthenticated POST /settings/calendar/disconnect (even with confirm=yes) redirects to /login and writes nothing (D-08/A-26, T-19-41) | ported | companion/test_companion_app_05.py::test_calendar_disconnect_route_unauthenticated_redirects_to_login |
| 303 | a valid POST /settings/calendar/connect 303-redirects to Display with the calendar_connect_ok flash key, persists the URL, triggers exactly one registry refresh, and leaves quiet_hours_enabled/display_enabled exactly as they were (D-14c, T-20-11 pinned regression) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_valid_url_persists_syncs_once_and_leaves_other_settings_alone |
| 304 | an empty calendar_url on POST /settings/calendar/connect 303-redirects with the calendar_connect_invalid flash key and persists nothing (D-14c) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_invalid_url_rejects_and_persists_nothing |
| 305 | an unauthenticated POST /settings/calendar/connect redirects to /login and writes nothing (D-14c, T-20-10) | ported | companion/test_companion_app_05.py::test_calendar_connect_route_unauthenticated_redirects_to_login |
| 306 | an unauthenticated POST /settings/notifications/test redirects to /login (D-26, T-20-10) | ported | companion/test_companion_app_05.py::test_notifications_test_route_unauthenticated_redirects_to_login |
| 307 | with no stored topic URL, POST /settings/notifications/test redirects with the notifications_test_failed flash key and never calls notify.send_notification() (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_unconfigured_flashes_failure_and_never_calls_sender |
| 308 | with a stored topic URL, POST /settings/notifications/test calls notify.send_notification() exactly once with the stored URL and redirects with the notifications_test_ok flash key (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_configured_calls_sender_once_and_flashes_success |
| 309 | a sender returning False redirects with the notifications_test_failed flash key (D-26) | ported | companion/test_companion_app_05.py::test_notifications_test_route_sender_returning_false_flashes_failure |
| 310 | a POST /settings/notifications/test carrying its own topic_url field is ignored in favour of the stored one — the field is never read from the request body (T-20-13) | ported | companion/test_companion_app_05.py::test_notifications_test_route_ignores_a_submitted_topic_url_field |
| 311 | a save-triggered sync against a calendar with a 60s-old last_attempt_at still fetches and reports success, and refresh_calendar_registry() is called with min_interval_s=0 explicitly - not omitted, which a call-shape spy is the only thing that can actually distinguish here, since config_page.handle_post()'s own save_calendar_url() (17-01) already resets last_attempt_at to None on every set before this handler's own refresh call runs | ported | companion/test_companion_app_05.py::test_calendar_sync_bypasses_the_throttle_via_min_interval_zero |
| 312 | server/poll_loop.py's own refresh_calendar_registry() call shape (no min_interval_s override) still honours the standard throttle against the identical seeded state - the bypass is scoped to the new call site alone | ported | companion/test_companion_app_05.py::test_poll_modules_own_refresh_call_site_still_throttles |
| 313 | a save arriving while the poll lock is already held redirects with the deferred flash key, performs no fetch, and still saves the URL (D-09) | ported | companion/test_companion_app_05.py::test_calendar_sync_lock_contention_is_honest |
| 314 | after a save whose immediate fetch fails, the poll lock is still free - one failure never wedges a later manual poll trigger | ported | companion/test_companion_app_05.py::test_calendar_sync_lock_is_released_after_a_failed_sync |
| 315 | a settings save that changes only the theme, against an already-connected calendar, redirects with the ordinary saved key, performs no fetch, and leaves the calendar and its fetched entries untouched | ported | companion/test_companion_app_05.py::test_unrelated_settings_save_never_reaches_the_refresh_call |
| 316 | a calendar save immediately followed by a manual poll trigger does not hit the poll cooldown - the two mechanisms are independent | ported | companion/test_companion_app_05.py::test_calendar_save_does_not_touch_the_manual_poll_cooldown |
| 317 | no *.py module or *.js static script anywhere under companion/ (test_*.py harnesses excluded) reintroduces any part of the deleted simple/full display-mode switch (D-17) — six modules' worth of removal, pinned by one mechanical scan | ported | companion/test_companion_app_05.py::test_no_companion_module_redefines_the_retired_display_mode_switch |
| 318 | every companion.app.FLASH_MESSAGES template and every _PAGE_TITLES value, plus the 404's and login shell's own <title> literals, round-trip to French under i18n.t_lang(..., 'fr') and to their original English text under i18n.t_lang(..., 'en') | ported | companion/test_companion_app_05.py::test_flash_and_title_strings_round_trip_to_french_and_back |
| 319 | the nav landmark's aria-label ("Primary navigation") and the theme picker's three segment labels ("Auto"/"Light"/"Dark") round-trip to French under i18n.t_lang(..., 'fr') and to their original English text under i18n.t_lang(..., 'en') (D-06/B16) | ported | companion/test_companion_app_05.py::test_nav_and_theme_labels_round_trip_to_french_and_back |
| 320 | the site-wide editorial floor (CFG-79): every non-exempt .section-caption element on all six authenticated routes, in both English and French, over a real running server, is at most 12 whitespace-split words; the route list is proven equal to test_browser_ux.py's own VIEW_TRANSITION_ROUTES; CAPTION_FLOOR_EXEMPTIONS (config_page.ASPECT_CAPTION_EXEMPTIONS, imported not re-listed) is skipped exactly its own length per language across the whole site; per-route and site-wide caption-count minimums guard against a narrowed selector passing vacuously; and the apply-timing sentence (read from frame_state.py's own DELAY_DUE/DELAY_HELD/DELAY_UNKNOWN constants) never renders outside the Frame strip's own markup slice, proven to fire inside it at least once (29-06-PLAN.md Task 3) | ported | companion/test_companion_app_05.py::test_site_wide_editorial_floor_all_six_routes_both_languages |


### Part 01 (plan 33-14)

Rows 1-50 (part 01, original `check()` calls #1-#50) plus the two out-of-order
WR-11 rows (279-280, pulled forward per 33-MIGRATION-RULES.md rubric T) are
`ported` to `companion/test_companion_app_01.py`.

Rubric codes: 46 B (calls `companion.auth`/`companion.layout` directly and
asserts on the return value/HTTP outcome), 4 C (rows 46-49 fetch the served
stylesheet via `served_stylesheet()` and assert on `companion_markup.
css_rules()`/`declarations_for()`/`rules_with_selector()` instead of reading
`companion/static/style.css` from disk; row 50 asserts on `css_rules()`
directly). No deletions in this slice.

New modules: `companion/test_companion_app_01.py` (52 tests: 50 ported checks
plus the 2 WR-11 checks share this same part-01 module rather than a
separate file), `companion/test_companion_app_helpers.py` (calendar-
transport fakes, public-hostname fake, poll-state seeding helper — not yet
consumed by part 01's own tests except the WR-11 pair's seeding helper;
front-loaded for 33-15..33-18's calendar-sync and manual-resolution
sections).

### Part 02 (plan 33-15)

Rows 51-122 (part 02, original `check()` calls #51-#113 by the plan's own
source-line count — the loop-generated route checks each own a distinct
ledger row per iteration, which is why the ledger's own row range is 72
long rather than 63) are `ported` to `companion/test_companion_app_02.py`,
except row 89 which is `deleted`.

Rubric codes: 58 B (calls a production function/module directly, or makes
an HTTP request against a real `companion/app.py` server, and asserts on
the outcome), 3 C (rows 52, 94 fetch the served stylesheet and assert on
`companion_markup.declarations_for()`/`css_rules()`; row 51 also reads the
served stylesheet for two substring checks), 5 J (rows 54, 59 fetch
`nav-dropdown.js` via `served_asset()`; row 57 fetches both `nav-dropdown.js`
and the served stylesheet; rows 121-122 fetch `copy-button.js`/
`dirty-state.js`), 1 S rewritten as a subprocess-import check (row 95:
`companion/draw.py`'s import graph is now proven by importing it fresh in a
child process and asserting on `sys.modules`, per 33-MIGRATION-RULES.md's
own rubric-S technique, instead of `ast.parse()`-ing its source), 2 S
consolidated into one narrower behaviour test (rows 92-93: both point at
`test_draw_emitters_carry_no_colour_literal_and_every_shape_has_a_fill_route`,
which proves the same two properties — no colour literal, every shape
carries a fill route — over `companion/draw.py`'s own emitter output rather
than scanning every string literal in `companion/draw.py` **and every
`companion/pages/*.py` module** via `tokenize`; the narrower scope is a
deliberate reduction, recorded in this plan's SUMMARY), 1 deletion.

Row 89 (`_battery_estimate_has_exactly_one_home`) is `deleted`: it scanned
every `companion`/`server` `*.py` file's tokens (via `tokenize`, banned by
guard G2) for a second definition of the battery millivolt constants/
percentage functions — a structural anti-duplication guard with no directly
observable HTTP/DOM consequence of its own. The actual failure mode it
exists to prevent — `companion.battery` and `server.poll_loop`'s two
independently-maintained copies disagreeing about a percentage for the same
reading — is fully covered behaviourally by row 91
(`test_battery_estimate_parity_between_companion_and_server`), which this
plan also ports unchanged.

RESEARCH assumption A3 (row 87's flash-deck check): does `_resolve_flash_
text()` ever create a directory for a missing `state_dir`? No — reading
`companion/app.py`'s source directly (not as a test assertion, as part of
this plan's own investigation), the function only ever *reads* `state_dir`
(via `poll_cooldown_remaining()`'s `history_db.open_db()` and `calendar_
rules.load_calendar_registry()`), and only for two OTHER flash keys
(`FLASH_KEY_POLL_COOLDOWN` and `FLASH_KEY_CALENDAR_CONNECTED`/`FLASH_KEY_
CALENDAR_CONNECT_OK`) neither of which the six `FLASH_KEY_MANUAL_*` deck
keys or an unknown key ever reach (the per-key branch returns before either
is called). `companion/test_companion_app_02.py::test_flash_manual_keys_
complete_and_byte_identical` proves this by measurement: it asserts a
`tmp_path` absent subpath still does not exist after every
`_resolve_flash_text()` call in the test.

New module: `companion/test_companion_app_02.py` (70 tests: two of part
02's original 72 ledger rows, 92-93, consolidated into one test; six of the
72 rows are covered by two parametrized tests carrying more than one
original row each — rows 100-105 by `test_unauth_get_nav_tab_redirects_
to_login_with_next` (6 parametrize ids), rows 106-107 by `test_unauth_get_
retired_page_route_redirects_to_login_without_next` (2 ids), and rows
116-119 by `test_static_script_public_and_cacheable` (4 ids)).
`companion/test_companion_app_helpers.py` gains `encode_multipart()` (the
legacy harness's own `_encode_multipart()`, renamed without its leading
underscore — it is still used by several still-legacy checks later in
`companion/test_companion_app.py`, so the ORIGINAL definition stays there
too; this plan's own multipart-parser checks call the shared helpers-module
copy instead).

`companion/test_companion_app.py`'s Section 3 (`companion/app.py`) keeps
three pieces of shared plumbing that sat textually inside this plan's own
slice but are called by name from several still-legacy checks further down
`main()`: the main()-level `import companion.app as app_module`, and the
two closure factories `_unauth_redirects_to_login()`/`_static_script_
public()`. These are explicitly NOT "closures only this plan's checks
used" (33-MIGRATION-RULES.md section 1) and were restored verbatim after
the shrink; see this plan's SUMMARY.

### Part 03 (plan 33-16)

55 rows (123-177), all `ported`. Rubric-code split: 9 B (public-route
checks, layout/app.py route-constant agreements, the pure-Python battery
and countdown-wording checks), 27 J (served-JS ES5-safe/sink-free
contracts and served-body assertions, fetched via `served_asset()` — never
a disk read), 6 D (rendered-page `<script>`-tag-count and DOM-contract
checks, plus the `_NO_JS_CONTROL_REGISTRY` contract, which renders and
parses real markup), 3 C (the `.js` gate, the shared control vocabulary
and the `@supports selector(:has(*))` block count, all read off
`served_stylesheet()` and — except the last — parsed structurally via
`companion_markup.css_rules()`/`declarations_for()`), and 2 S (rewritten
rather than ported as-is; see below). No rows are `deleted`: every
original check's real behaviour survives, once, in the new module.

Two S-rubric rewrites, both because the original check read production
source with a technique guard G2 bans:

- Row 156 (`relative-time.js's BUCKET_BOUNDARIES equals layout.
  _age_bucket()'s own three boundaries...`) used to call `inspect.
  getsource(layout._age_bucket)` and regex the three numeric literals out
  of the returned source text. `test_relative_time_ladder_mirrors_layouts_
  own_boundaries` instead DISCOVERS those same three boundaries
  behaviourally: `_age_bucket_boundaries()` bisects over `layout.
  _age_bucket()`'s own return value (which unit — s/m/h/d — a given input
  maps to), since the function is monotonic. The boundaries are exactly as
  observable this way, and the check never reads a line of Python source.
- Row 176 (`companion/battery.py imports nothing from companion.pages and
  nothing from the server package...`) used `ast.parse()` over `companion/
  battery.py`'s own source and walked the tree for `Import`/`ImportFrom`
  nodes. `test_battery_module_imports_neither_a_page_module_nor_the_
  server_package` instead imports `companion.battery` fresh in a
  subprocess (`child_env()`, `cwd=REPO_ROOT`) and asserts the banned module
  names are absent from `sys.modules` — the exact technique
  33-15-PLAN.md's `test_draw_module_imports_no_page_and_no_server`
  established for the identical shape of check.

One check (row 150, the real GET of `/static/submit-guard.js`) used to
open BOTH `companion/static/style.css` and `companion/app.py` from disk.
The CSS half (button:disabled ordered after button:active) is now read
structurally off `css_rules(served_css)` — a source-order-preserving list,
so "AFTER" is an index comparison rather than a text-offset one. The CSP
half is now a real HTTP response header read (`GET /login`'s own
`Content-Security-Policy` header), additionally cross-checked against
`companion.app.CONTENT_SECURITY_POLICY` — strictly stronger than reading
the Python literal that builds the header, since it proves the header is
actually SENT, not merely defined.

One check (row 174, the `@supports selector(:has(*))` block count) is
kept as a documented exception to "parse structurally": distinguishing a
second, identically-nested feature-query block from the rules already
inside today's one block needs block-POSITION information no
`companion_markup.css_rules()` caller can recover (the parser records
each rule's at-rule PRELUDE TEXT, not where that prelude started in the
file). `test_style_css_carries_exactly_one_has_feature_query_block` keeps
a comment-stripped regex count, but over the SERVED (HTTP-fetched)
stylesheet — never a disk read — per F-01's own sanctioned carve-out for a
property genuinely inexpressible over `css_rules()`/`declarations_for()`.

New module: `companion/test_companion_app_03.py` (55 tests, one per
ledger row — no consolidation and no parametrization in this part).
`companion/test_companion_app_helpers.py` gains `strip_js_line_and_block_
comments()` (the same comment-preserving-strings JS helper `companion/
test_view_pages_helpers.py`/`companion/test_config_page_helpers.py`
already carry for their own chains — used by row 156's boundary-count
check).

`companion/test_companion_app.py` shrunk: `EXPECTED_CHECK_COUNT` 196 ->
141; part 03's 55 checks and their private closures removed from
`main()`. The module-level `_NO_JS_CONTROL_REGISTRY` tuple (and its
documenting comment block) is also removed — it was exclusively read by
this part's own last check, and nothing else in the file or the wider
codebase imports it by name. `_static_script_public()` — textually
adjacent to this part's slice but still called by `/static/login-card.js`'s
own still-legacy check further down `main()` — was confirmed present
(never touched) by re-running `ruff check` on the shrunk file (0 F821
undefined-name errors) before committing.

### Part 04 (plan 33-17)

89 rows (178-266), all `ported`, into two new modules:
`companion/test_companion_app_04.py` (rows 178-222, 45 tests) and
`companion/test_companion_app_04b.py` (rows 223-266, 34 tests — three
stateful/sequential check clusters consolidated into one atomic test
each, see below). Rubric-code split (one dominant code per row, since
several rows mix an HTTP/status assertion with a markup substring):
70 B (HTTP status/header/cookie/on-disk-config assertions — the large
majority: every login POST/GET flow, every NAV_TABS/redirect/settings/
quick-toggle/illustration/theme-preview check that reads a response's
status, headers or `device_config.load_device_config()`), 15 D (rendered-
HTML substring/structure assertions — the login card's markup, the split
Display/Device settings groups, the rebuilt Home page, the D-03 language-
resolution/nav-toggle-gear checks, the two 404 page-header/health-dot
checks), 3 C (`layout.JS_GATE_CLASS`'s selector-boundary check and the
motion budget, both read via `css_rules()`/regex over `served_stylesheet()`
rather than a disk read; the login-page clean-render check's three CSS-
rule-existence assertions, via `rules_with_selector()`), and 1 J
(login-card.js's ES5-safe/sink-free contract, via `served_asset()`). No
rows are `deleted`: every original check's real behaviour survives.

No S-rubric rewrites in this part — no check here used `inspect`/`ast`/
`tokenize` over production source. The one rename named in the plan's own
hotspot section: row 190 (`GET /login?next=/nonexistent-route...`) now
uses `next=/no-such-route` — behaviour unchanged (neither is a real
NAV_TABS member, so both take the "no hidden next field" branch), and the
new module carries no `/nonexistent` literal anywhere, including its own
docstring (`grep -cE "/nonexistent|open\(|tempfile"` on
`test_companion_app_04.py` is 0).

Three stateful/sequential clusters are consolidated (several old checks
map to one new node id, 33-MIGRATION-RULES.md section 3): rows 238-241
(logout clears the cookie; a replayed cookie is rejected; GET /logout
404s; a post-logout tab request with no cookie is refused) all land on
`test_logout_clears_cookie_and_a_replayed_or_absent_cookie_is_refused_afterward`,
since running them against the module's shared read-only server would
end that server's one shared session for every other test. Rows 247-250
(three gallery path-traversal payloads plus the canary-never-leaks check)
land on `test_gallery_traversal_and_canary_never_leaks`. Rows 261-265 (the
`?live=1` sample-fallback/cache-reuse/newer-event/unknown-theme/zero-or-
missing-query sequence) land on
`test_theme_preview_live_branch_cache_and_fallback_behaviour`, since each
step's assertion depends on the previous step's own mutation (no
`runway_events` row, then one, then a newer one) — the exact ordering
xdist gives no test the right to assume.

The upload round trip (row 266, the LAST anchor) and the two manual-
resolution-key checks (rows 255-256) each get their own fresh, function-
scoped `make_app_server(fake_providers=True)` server rather than the
module's shared one, per the plan's own hotspot note — they write real
files into `illustration_overrides/`.

`companion/test_companion_app.py` shrunk further: `EXPECTED_CHECK_COUNT`
141 -> 52; part 04's 89 checks, their private closures, and the now-
unused `_theme_cache_dir()` helper are removed from `main()`. The first
of the section's two logins (`session_cookie = _login(harness)`,
originally at the top of the authenticated block) is also removed as
dead code — every check that used to sit between it and the "re-
authenticate" login further down is gone, so nothing reads that first
session any more before the second login overwrites the same variable;
the second login's own comment is updated to say so, since it is now the
section's only login rather than a re-authentication. The illustration-
upload check's own setup (the pre-upload GET, the multipart POST, and
populating `_illustration_pre_upload_render`) stays as bare, un-checked
setup code — confirmed still read directly, by name, by the next still-
legacy check (`_illustration_override_uses_same_normalization_pipeline`,
row 267, 33-18/part 05's own territory) and by three more checks after it
that need the override file the upload just wrote. The stale-pipeline-run
seed and the `gallery/` directory `os.makedirs()` (both migrated-away
rows' own setup) are removed outright — confirmed by grep that no
still-legacy check past row 266 reads either. Re-verified: the shrunk
harness runs 52/52 standalone and through
`companion/test_legacy_harness_shim.py -k companion_app`, and `ruff
check` on the shrunk file is clean (0 F821 undefined-name errors).

### Part 05 (plan 33-18) — chain closed

Rows 267-320 (52 baseline checks, the LAST anchor of the whole
companion_app chain) ported into `companion/test_companion_app_05.py`'s
47 native pytest node ids — 52 `ported`, 0 `deleted`:

- **Illustration override effects (rows 267-270, consolidated into ONE
  node id):** the four checks all read state produced by the SAME real
  upload (never each other's mutations), matching 33-17-SUMMARY.md's own
  consolidation precedent for a fixed-order setup shared across several
  old checks — the normalization-pipeline identity, the exact-one-file
  write, the byte-identical vendored original, and
  `select_illustration()`'s override/vendored resolution.
- **Illustration upload rejection paths (rows 271-274):** non-image
  payload, oversized payload, unknown/traversal keys, unauthenticated
  POST — four independent node ids, each its own fresh
  `make_app_server`.
- **Manual-resolution routes (rows 275-278):** auth gate, live-registry
  revalidation, the four rejection-flash/D-03-branch/cap-fill checks
  consolidated as the legacy `main()` already grouped them, and the
  delete route's full contract.
- **Colour-rules routes (rows 281-286):** auth gate, form placement
  outside `SETTINGS_FORM_ID`, add/replace, the rejection paths plus
  registry cap, delete, and the fresh-per-request read.
- **Poll-trigger cooldown sequence (rows 287-290, consolidated into ONE
  node id):** first trigger + its fake-provider call-log proof,
  immediate cooldown, and a fresh second-opener session refused by the
  same server-global cooldown — the three steps share one mutable
  server in a fixed order, exactly 33-17-SUMMARY.md's own consolidation
  rule.
- **The `--geofence` hotspot (row 291, T-33-18-01):** the poll-trigger
  failure check now passes `make_app_server(extra_args=["--geofence",
  str(tmp_path / "absent" / "no-such-geofence.json")])` instead of the
  legacy literal `/nonexistent/no-such-geofence.json` string — the same
  startup-failure behaviour, no literal host path guard G6 would flag.
- **Concurrent `/poll-now` lock proof (row 292).**
- **Calendar save-triggered sync family (rows 293-316):** every check
  that used to build its own `_InProcessHarness()` now takes
  `companion/conftest.py`'s `app_server_in_process` fixture directly —
  connect/disconnect reporting, the dedicated disconnect/connect routes'
  full auth/confirm contracts, the notifications "send a test" route,
  the throttle-bypass spy, lock contention/release, and the two
  independence proofs (an unrelated save never reaches the refresh call;
  a calendar save never touches the manual poll cooldown). Row 312 (the
  poll_loop-side throttle control) needed no server at all and no longer
  uses `tempfile.TemporaryDirectory()` (guard G6): it takes pytest's own
  `tmp_path` fixture instead.
- **The retired display-mode-switch removal (row 317, rubric S):** the
  legacy check walked every `*.py`/`*.js` file under `companion/` for
  seven retired tokens as raw text. Rewritten as a `not hasattr()`
  battery across every `companion.*` module the removal touched
  (`app`, `auth`, `layout`, `prefs`, and every `companion.pages` module)
  — confirmed by grepping the WHOLE repo before writing the rewrite that
  none of the identifier-shaped tokens (`simple_mode`, `MODE_CHOICES`,
  `DEFAULT_MODE`, `_MODE_CTX`, `UI_MODE_COOKIE_NAME`, `MODE_ROUTE`,
  `sp_ui_mode`) remain anywhere in production code; the two
  non-identifier tokens (the `/ui-mode` route, the `sp_ui_mode` cookie
  name) are behavioural claims already covered by
  `test_companion_app_04b.py`'s own 404/Accept-Language tests, named in
  this test's own docstring.
- **i18n round trips (rows 318-319).**
- **The site-wide editorial floor (row 320, the LAST anchor, rubric S
  for its own cross-file counting-rule check, split into TWO node
  ids):** `test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy`
  proves this module's own `_caption_word_count_text()` duplicate agrees
  with `companion.test_config_page_05`'s own copy across four fixtures,
  by a plain `import companion.test_config_page_05` and calling both
  functions directly — never the legacy check's disk-read + `ast.parse`
  + `ast.get_source_segment()` + `exec()` extraction (guard G2 bans
  `ast`/`tokenize`/`inspect`/`linecache` outright; 33-13-PLAN.md closed
  the config_page chain, and this plan's own sequential-execution brief
  required the cross-check be migrated as calling behaviour, never a
  source read). `test_site_wide_editorial_floor_all_six_routes_both_
  languages` carries the rest of the original check unchanged: the
  route-list parity check reads `companion.test_browser_ux_helpers.
  VIEW_TRANSITION_ROUTES` via a plain import (never the legacy check's
  own `ast.parse()` of that file's source), then fetches all six routes
  in both languages over a real server and re-applies every counting/
  exemption/anti-vacuity floor unchanged. The ledger row points at this
  primary node id; the split-off cross-check test is the second.

Rubric-code split across this part's 52 baseline rows: 44 B (HTTP
round-trip/module-call checks), 6 D (markup/regex-over-rendered-HTML
checks: the rules-form-placement check and the five sub-checks inside
the editorial floor's own measurement loop), 1 S rewritten as a
`not hasattr()` battery (row 317), 1 S rewritten as calling behaviour
(row 320's cross-check), 0 C, 0 J, 0 P, 0 R, 0 T, 0 deleted.

**Chain closed.** `companion/test_companion_app.py` deleted outright
(`git rm`): all 320 baseline checks are accounted for (319 `ported`
across `companion/test_companion_app_01.py`..`_05.py`, 1 `deleted` —
row 89, from an earlier plan in this chain — 0 `pending`).
`33-ledger-check.py companion/test_companion_app.py` **WITHOUT**
`--allow-pending` confirms 320/320.


### Closing sweep (plan 33-32): structural stylesheet checks

Rows 51, 52, 57, 59, 174 and 179 kept their node ids but no longer assert with a regex, `in`
test or str search over the served stylesheet's text (33-FOLLOWUPS.md F-01). "Class X is
styled" is now a selector match over `css_rules()`; the `.js .mobile-nav` rules and the
`input.visually-hidden` floor-clearing rule are read with `declarations_for()`; row 174 counts
`@supports selector(:has(*))` with `companion_markup.at_rule_blocks()`; row 179 counts
`@keyframes` and reduced-motion `@media` blocks with `at_rule_blocks()` and checks every
animation declaration outside those blocks through `css_rules()`, which retires the
module's own brace-matching text helper.

### Closing sweep (plan 33-32): one shared counting rule

Row 320's secondary node id
`test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy` imported the sibling
test module `companion.test_config_page_05` to compare two copies of the editorial floor's
counting rule. The rule now lives once, as `caption_word_count_text()` in
`companion/test_config_page_helpers.py`, and both modules import it, so the agreement check
became a tautology. It is replaced by
`companion/test_companion_app_05.py::test_caption_word_count_text_strips_markup_entities_and_one_leading_dash`
(parametrised over the same four fixtures, with pinned expected outputs). Row 320 still points
at its primary node id, `test_site_wide_editorial_floor_all_six_routes_both_languages`, which is
unchanged. Guard rule G12 now forbids a test module importing another test module.

## companion/test_status_pages.py

# Ledger: companion/test_status_pages.py

Baseline: `companion__test_status_pages.txt`, 317 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | render() shows two distinct, separately-labelled freshness signals | ported | companion/test_status_pages_01.py::test_render_shows_two_distinct_freshness_labels |
| 2 | staleness_status() returns ok/warn/error at the right boundaries, warn for a never-seen signal | ported | companion/test_status_pages_01.py::test_staleness_status_boundaries |
| 3 | wake.device_staleness_thresholds() floors at (300, 1200), multiplies at a 5-minute cadence, and falls back to the floors for None (19-05-PLAN.md D-05/A-23) | ported | companion/test_status_pages_01.py::test_device_staleness_thresholds_floors_and_multipliers |
| 4 | wake.device_staleness_thresholds() guarantees warn_s < error_s for every input | ported | companion/test_status_pages_01.py::test_device_staleness_thresholds_warn_always_under_error |
| 5 | wake.env_sleep_s() reads SKYPANE_SLEEP_S unclamped (no [60, 3600] range check) and degrades to None for unset/empty/non-numeric/non-positive values | ported | companion/test_status_pages_01.py::test_env_sleep_s_reads_unclamped_and_degrades |
| 6 | wake.effective_wake_interval_s() prefers the screen-off cadence, otherwise a configured wake_interval_s, and degrades to None for a missing config | ported | companion/test_status_pages_01.py::test_effective_wake_interval_s_precedence |
| 7 | companion/wake.py's source never mentions the pages package or app.py | ported | companion/test_status_pages_01.py::test_wake_module_never_imports_pages_or_app |
| 8 | layout.absolute_and_relative() covers every documented case: ordering, Z-suffix parsing, default/explicit fallback, unparseable-timestamp degradation, missing now_ts | ported | companion/test_status_pages_01.py::test_layout_absolute_and_relative_covers_every_documented_case |
| 9 | health_page's private timestamp helpers are gone (a move, not a copy) and the Device row still renders the absolute-plus-relative format, now as a parenthesised <time data-relative> element | ported | companion/test_status_pages_01.py::test_health_page_timestamp_helpers_promoted_not_duplicated |
| 10 | a stale device and a fresh pipeline read as independent per-tile modifiers (error vs ok) on their own wrappers, not a blended verdict, with only the dots that legitimately remain still healthy | ported | companion/test_status_pages_01.py::test_independent_thresholds_one_warn_one_ok |
| 11 | the Device and Pipeline tiles carry their freshness label exactly once (caption only) plus exactly one Emphasis-role verdict and exactly one muted detail slot holding the mono timestamp, with zero stat-tile__value and no leftover dot-label (quick task 260901-tsa finding C, retargeted by 22-12-PLAN.md Task 1's X8 anatomy) | ported | companion/test_status_pages_01.py::test_device_pipeline_tiles_have_no_duplicated_label |
| 12 | zero battery rows render the good-news empty state and no sparkline | ported | companion/test_status_pages_01.py::test_battery_empty_state_no_sparkline |
| 13 | Health's battery section draws exactly one ring whose drawn fraction — recovered from its own emitted radius and dash array — equals the percentage the readout beside it PRINTS; the <h2> still carries no glyph, battery_sparkline_svg()'s own output carries no ring class, and a device with no reading renders no ring at all rather than an empty one (CFG-40) | ported | companion/test_status_pages_01.py::test_battery_ring_agrees_with_its_own_readout |
| 14 | three battery rows render the full trend (not just the latest value) and exactly one <svg> with exactly n - 1 trend-line segments (260902-ep7: retargeted from the retired single-<polyline> marker) | ported | companion/test_status_pages_01.py::test_battery_trend_shows_all_readings_and_one_sparkline |
| 15 | Battery Trend's Timestamp column shows the D-09 concise format (full ISO demoted to title), matching the Device/pipeline rows, and _battery_section() stays single-argument | ported | companion/test_status_pages_01.py::test_battery_trend_timestamps_show_concise_format |
| 16 | the readings table is collapsed behind a closed-by-default disclosure, and the chart precedes it (D-08) | ported | companion/test_status_pages_01.py::test_battery_readings_collapsed_behind_closed_disclosure_after_chart |
| 17 | the Battery trend heading shows the default 3-month window framing on an empty render (260902-l0b, retargeted from the retired D-10 'Latest 20 readings' label) | ported | companion/test_status_pages_01.py::test_battery_trend_heading_shows_d10_window_label |
| 18 | a multi-day seeded render plots the three DAILY AVERAGES (never any raw reading value) as points, keeps every raw reading visible in the disclosure table, and names the 3-month window (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_chart_plots_daily_averages_not_raw_readings |
| 19 | a same-day (fewer than two calendar days) seeded render still produces a chart and a readout, captioned honestly as readings rather than the 3-month window — the day-1 regression guard (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_chart_falls_back_to_raw_series_on_day_one |
| 20 | the Battery trend caption is mode-honest across three renders — empty (3-month default), multi-day (3-month, daily average), and same-day (readings count) (260902-l0b) | ported | companion/test_status_pages_01.py::test_battery_caption_is_mode_honest_across_renders |
| 21 | the anomaly banner names the real failing category (a disagreement), not only the generic fallback text (UXA-06) | ported | companion/test_status_pages_01.py::test_anomaly_banner_names_real_categories_not_generic_only |
| 22 | _anomaly_category_text() lower-cases ordinary mid-sentence phrases but never a leading acronym (no 'aDS-B') | ported | companion/test_status_pages_01.py::test_anomaly_categories_never_lowercase_a_leading_acronym |
| 23 | _anomaly_category_labels() returns one period-stripped label per anomaly, distinct from collect_anomalies()'s own full literal sentences (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_category_labels_are_pill_text_not_full_sentences |
| 24 | _anomaly_banner_html() reproduces layout.anomaly_banner()'s exact severity-to-class/role mapping, and carries one banner__pill per anomaly plus the accessible ANOMALY_BANNER_TEXT tail (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_banner_html_matches_layout_anomaly_banner_severity_mapping |
| 25 | a two-anomaly fixture renders exactly two banner__pill elements inside one banner element on the real page (D-07) | ported | companion/test_status_pages_01.py::test_anomaly_banner_renders_one_pill_per_anomaly_on_the_page |
| 26 | Corroboration's three rows stay compact (dot/label/count only) and their explanations move into a closed-by-default disclosure (D-08) | ported | companion/test_status_pages_01.py::test_corroboration_rows_compact_explanations_in_closed_disclosure |
| 27 | _corroboration_section()'s second return value (the disagreement flag) is unchanged by the D-08 disclosure rewrite | ported | companion/test_status_pages_01.py::test_corroboration_section_disagreement_flag_unchanged |
| 28 | no corroboration row's explanation leaks a bare decision-ID parenthetical (UXA-05) | ported | companion/test_status_pages_01.py::test_corroboration_copy_has_no_decision_id_leak |
| 29 | the Device check-in and ADS-B pipeline rows render via the D-09 concise timestamp format | ported | companion/test_status_pages_01.py::test_device_and_pipeline_rows_use_concise_timestamp_format |
| 30 | Health's D-12 reversal: a live data-loaded-at timestamp survives, page_header() is called exactly once, and the retired stale-view banner marker/copy and manual Refresh-link class are gone from both the rendered page and the module itself (260902-chc) | ported | companion/test_status_pages_01.py::test_health_pill_reversal_guard |
| 31 | Battery trend renders a healthy status-coloured card border on a normal trend, in place of the retired status_dot() badge (D-01 reversal, quick task 260902-gjj) | ported | companion/test_status_pages_01.py::test_battery_section_healthy_card_border_on_normal_trend |
| 32 | an empty/single-reading battery trend renders an ok badge and no anomaly banner (Assumption A1 regression guard) | ported | companion/test_status_pages_01.py::test_battery_empty_history_ok_badge_no_anomaly_banner |
| 33 | a real battery drop drives both the card's own error border (retargeted from the retired badge, quick task 260902-gjj) and the banner; the detail copy is no longer rendered | ported | companion/test_status_pages_01.py::test_battery_drop_drives_badge_and_banner_detail_copy_not_rendered |
| 34 | an unhealthy fixture renders the anomaly banner with zero <ul/<li list markup inside its own element slice (retargeted from a page-wide ban by quick task 260903-ghy, to stop it colliding with a legitimate .data-cards list elsewhere on the page) | ported | companion/test_status_pages_01.py::test_anomaly_detail_list_markup_is_gone |
| 35 | with all four D-14 signals unhealthy, none of collect_anomalies()'s four item strings is rendered | ported | companion/test_status_pages_01.py::test_none_of_the_four_anomaly_item_strings_render |
| 36 | battery_sparkline_svg() emits no url(, <image, or <script — no external reference at all | ported | companion/test_status_pages_01.py::test_sparkline_has_no_external_reference |
| 37 | battery_sparkline_svg() emits per-point interactive hit targets with data-mv/data-ts/<title>, in chronological order, with roving tabindex on the latest point only | ported | companion/test_status_pages_01.py::test_sparkline_svg_has_per_point_interactive_markup |
| 38 | battery_sparkline_svg() emits exactly four aria-hidden axis-label text nodes carrying the FIXED SPARKLINE_Y_MIN_MV/SPARKLINE_Y_MAX_MV values (not the fixture's own real min/max), with every prior no-external-reference guarantee intact (D-09, retargeted by 19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_axis_labels_present_with_fixed_range |
| 39 | battery_sparkline_svg() draws a flat series (every value identical) at one consistent y level, never pinned to the canvas edge by a collapsed min==max range (19-05-PLAN.md Task 2/D-04, A-22) | ported | companion/test_status_pages_02.py::test_sparkline_flat_series_draws_flat_not_pinned_to_bottom |
| 40 | battery_sparkline_svg() draws a small (15mV) wiggle as a small y movement, well under a tenth of the fixed range's full excursion — not a cliff spanning the whole canvas (19-05-PLAN.md Task 2/D-04, A-22) | ported | companion/test_status_pages_02.py::test_sparkline_small_wiggle_stays_small_not_a_cliff |
| 41 | battery_sparkline_svg() clamps out-of-range values (2500mV, 4500mV) to the canvas edge rather than escaping it or rescaling the fixed axis labels (19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_out_of_range_values_clamp_not_rescale |
| 42 | _sparkline_dense_threshold() derives a different threshold for different canvas widths, proving the density rule is width-derived rather than a typed constant (19-05-PLAN.md Task 2/D-04) | ported | companion/test_status_pages_02.py::test_sparkline_dense_threshold_is_width_derived |
| 43 | battery_sparkline_svg()'s <svg> carries no viewBox/preserveAspectRatio (no scale factor exists), every cx/cy is a percentage inside [0, 100] with strictly increasing chronological marker x-positions, marker/hit-target radii stay the unchanged absolute 3/8, and style.css declares the canvas height exactly once for this selector and never inside a @media block (quick task 260902-ep7 BUG 4, rewritten in place from 260902-dng's retired scale-bound mechanism) | ported | companion/test_status_pages_02.py::test_sparkline_scale_bounded_at_one_across_real_container_widths |
| 44 | battery_sparkline_svg() fills an area under the trend line from a NESTED viewBox'd <svg> (percentages are illegal in a points list) whose vertices land on the exact coordinates the chart's own marks did, closed at the axis minimum rather than the canvas edge, painted before the line, in currentColor at a translucent fill-opacity, with the outer canvas still carrying no viewBox, no url(/image/script reference, no colour literal, no rule of its own for the layer, and nothing at all below two points (CFG-41/CFG-45, 24-05-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_sparkline_area_sits_under_the_line_in_its_own_nested_viewbox |
| 45 | the battery chart marks the newest PLOTTED point (never the newest raw row, which may carry no battery_mv at all) with its own non-dot class at a named radius that fits the canvas's vertical inset, last in document order, carrying the same timestamp its hit target does, leaving the roving-tabindex path byte-identical, and surviving the density rule that suppresses cosmetic dots (CFG-41, 24-05-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_sparkline_marks_the_newest_plotted_point_not_the_newest_row |
| 46 | the chart's low-battery threshold is a full-width rect placed by the same sparkline_point_y() the readings are, its value READ from companion/battery.py and never re-typed, labelled by meaning in a non-aria-hidden <span> outside the canvas in both languages, painted with the status-warn token the legend's own swatch shares, and absent entirely — line and label — when the value falls outside the chart's fixed range (CFG-41, T-24-05-A/B, 24-05-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_sparkline_low_battery_threshold_is_read_from_battery_py_and_labelled |
| 47 | draw.cell_class() maps the classifier's four verdicts to four DISTINCT classes, all of them in DRAWING_CLASSES, and falls to the no-observation class for anything else — so a bucket with no observation can never emit the on-cadence or the missing class — and regularity_grid() raises rather than emitting a cell with no <title> (CFG-43, T-24-07-A, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_has_four_states_and_never_conflates_them |
| 48 | the regularity grid sizes its cells DOWN from the measured 278px card width at the 360px floor: grid_columns() returns the most columns whose cells still clear the 24px minimum and one more column would not, a narrower card reduces the columns rather than the cells, every cell is square, inside the viewBox, spread across every column and row with exactly CELL_GAP_PX of clear ground, and no colour literal is emitted (CFG-43, CFG-45, T-24-07-D, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_cells_are_sized_from_the_360px_floor |
| 49 | the regularity grid's element count is bounded by its own geometry and never by the caller's window — at capacity it keeps the NEWEST buckets, reports exactly how many it dropped, and paints none of the dropped verdicts — while one cell still draws one full-size cell and no cells draw nothing (CFG-43, T-24-07-D, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_regularity_grid_is_bounded_and_keeps_the_newest_buckets |
| 50 | draw.CELL_STATE_CLASSES is keyed on EXACTLY wake.classify_check_in_gap()'s own four CHECK_IN_* values — the one coupling a stdlib-only geometry module cannot express as an import (CFG-43, 24-07-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_draw_cell_vocabulary_is_the_classifiers_own |
| 51 | CLAUSE 1 — Health's regularity caption says what the grid SHOWS: one cell is one day of OBSERVED check-in regularity (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_says_what_the_grid_shows |
| 52 | CLAUSE 2 — Health's regularity caption names the cadence the grid was judged against, by its value and in this app's own duration form, and says that cadence is the one configured NOW rather than the one in force on an earlier day (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_names_the_cadence_it_judged_against_and_says_it_is_todays |
| 53 | CLAUSE 3 — Health's regularity caption says a day with no record is NOT proof the frame did not wake, naming the log rotation that leaves the same gap (CFG-43, T-24-07-A, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_caption_says_a_gap_is_not_proof_of_a_missed_wake |
| 54 | with a config yielding no cadence at all, Health's regularity caption says the grid is judged against the fallback staleness floors and does NOT name a configured value (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_with_no_determinable_cadence_the_caption_names_the_floors |
| 55 | every cell's verdict equals wake.classify_check_in_gap()'s own output for that day's longest observed gap — computed in this check from the classifier, never hard-coded — every unobserved day carries the no-observation class, and the page's own regularity builders call the classifier while referencing no threshold constant and containing no interval arithmetic of their own (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_every_cell_verdict_is_the_classifiers_own_output |
| 56 | with no observations at all the regularity section still renders — a full grid of no-observation cells, none of them on-cadence or missing, under its own caption saying there is nothing recorded yet (CFG-43, T-24-07-A, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_with_no_observations_the_section_still_renders_its_grid |
| 57 | the rendered Health page contains neither 'honoured' nor 'punctual' (nor 'punctualité') in EITHER language while carrying the full grid in both, and the section heading has a real French sibling rather than an English string inside a French page (CFG-43, 24-07-PLAN.md Task 2) | ported | companion/test_status_pages_02.py::test_the_rendered_page_never_claims_punctuality_in_either_language |
| 58 | for all four check-in-card cases (observed x cadence-known), the visible caption carries EXACTLY CHECK_IN_CAPTION_OBSERVED and every other clause that case renders moves, byte-identical, into the card's own <details class="readings-disclosure"> — 'moved, not cut' proven as a relationship, case and clause named on failure (29-06-PLAN.md Task 2, CFG-79) | ported | companion/test_status_pages_02.py::test_check_in_disclosure_moved_clauses_render_across_all_four_cases[observed, cadence known] |
| 59 | battery_sparkline_svg() draws real axis chrome — at least one full-height vertical axis <rect>, at least one full-width horizontal axis <rect>, and at least two tick <rect> elements, all carrying SPARKLINE_AXIS_CLASS and aria-hidden="true" on their own tags (quick task 260902-ep7 BUG 4) | ported | companion/test_status_pages_02.py::test_sparkline_axis_chrome_present |
| 60 | battery_sparkline_svg(daily=True) renders day-plus-month date endpoint labels ('31 Aug'/'2 Sep'), never the clock-format labels a day string would otherwise silently print (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_daily_mode_shows_date_endpoints_not_clock |
| 61 | each daily chart point's data-when names its day, says it is a daily average, and gives the singular/plural-correct contributing reading count (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_daily_point_label_names_day_and_average_count |
| 62 | the density rule suppresses cosmetic dots only at/above the derived threshold (every hit target still reachable, at the reduced radius), survives untouched just below it, and a below-threshold non-daily call stays byte-for-byte what it is today (260902-l0b) | ported | companion/test_status_pages_02.py::test_sparkline_density_rule_suppresses_dots_only_above_threshold |
| 63 | the battery readout's initial markup equals the humanised (value, when) pair the latest reading's own helper builds, split across its value/detail spans, and the retired placeholder prompt no longer appears (D-09, quick task 260901-uzi finding 3) | ported | companion/test_status_pages_02.py::test_battery_readout_seeded_with_latest_reading_not_placeholder |
| 64 | _battery_reading_parts()'s value text leads with a '≈ NN%' estimate ahead of the exact millivolt figure, for a numeric reading battery.battery_percent() can estimate (D-01/A-19) | ported | companion/test_status_pages_02.py::test_battery_reading_parts_value_carries_the_percentage_estimate |
| 65 | _battery_reading_parts()'s value text stays a bare millivolt figure, with no ≈ marker, when battery.battery_percent() cannot estimate the reading (D-01/A-19) | ported | companion/test_status_pages_02.py::test_battery_reading_parts_value_has_no_estimate_when_percent_is_none |
| 66 | _axis_clock_label() renders Europe/Paris local time, not the unconverted UTC clock (D-05, B4): 22:30 UTC in September prints '00:30', not '22:30' | ported | companion/test_status_pages_02.py::test_axis_clock_label_is_paris_local_not_utc |
| 67 | _axis_day_label() names the Europe/Paris calendar day an instant falls on, not its UTC day (D-05, D-12.3) | ported | companion/test_status_pages_02.py::test_axis_day_label_names_the_paris_day |
| 68 | a sparkline point's <title>, aria-label and data-when carry the SAME string — one formatted value, never three independently-derived ones (D-05, B4) | ported | companion/test_status_pages_02.py::test_sparkline_point_title_aria_data_when_are_one_string |
| 69 | a seeded Health page renders zero occurrences of the literal ' UTC' in either English or French (D-05, B4) | ported | companion/test_status_pages_02.py::test_health_page_has_zero_utc_literal_in_either_language |
| 70 | battery-trend.js contains no client-side date parsing or formatting (new Date(), toISOString, getHours, getMinutes), sets title to the pre-formatted 'when' text rather than the raw ts, and its fallback no longer shows a raw ISO string (D-05, B4) | ported | companion/test_status_pages_02.py::test_battery_trend_js_has_no_client_side_date_math |
| 71 | concise_timestamp_html()'s title is a full Europe/Paris local timestamp ('D Mon HH:MM'), never the raw ISO string and never a 'UTC' suffix (D-05, B4) | ported | companion/test_status_pages_02.py::test_concise_timestamp_html_title_is_a_full_local_timestamp_not_raw_iso |
| 72 | a seeded health_page.render() call's battery-readout__value span carries both the '≈' estimate and the ' mV' millivolt figure (D-01/A-19) | ported | companion/test_status_pages_02.py::test_seeded_render_shows_both_the_estimate_and_the_millivolt_figure |
| 73 | the Device tile's widget-verdict paragraph matches DEVICE_STATE_TEXT at each of the three severities a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_device_tile_verdict_matches_state_at_each_severity[ok] |
| 74 | the Pipeline tile's widget-verdict paragraph matches PIPELINE_STATE_TEXT at each of the three severities a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_pipeline_tile_verdict_matches_state_at_each_severity[ok] |
| 75 | the Corroboration tile's widget-verdict paragraph matches CORROBORATION_STATE_TEXT for both the agreement and disagreement states a real health_page.render() call can produce (D-03/A-21) | ported | companion/test_status_pages_02.py::test_corroboration_tile_verdict_matches_disagreement_state[agree] |
| 76 | the Resolution-rate tile deliberately carries no widget-verdict paragraph (D-03/A-21) | ported | companion/test_status_pages_02.py::test_resolution_rate_tile_carries_no_verdict |
| 77 | every .stat-tile on a rendered Health page — seeded and on a fresh install alike — carries exactly one label, exactly one Emphasis-role element, exactly one muted detail slot, in that fixed order, and no 22px serif heading anywhere inside it (X8/C1, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_one_tile_anatomy_across_every_health_tile[seeded] |
| 78 | Health's 'Only one saw it' corroboration row renders the neutral dot--off with its own distinct visible dot-label while 'Both agree' keeps dot--ok — in both languages, and never a warn dot — so the two states are readable with colour vision entirely absent (X8 / 22-UI-SPEC.md §5 contract 4, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_only_one_saw_it_is_neutral_and_still_distinct[en-Both agree-Only one saw it] |
| 79 | layout.empty_state()'s two-argument output is byte-identical to its pre-compact form (proven against the literal markup AND against data_table()'s own real no-rows caller), an explicit compact=False matches it, and compact=True renders its own modifier plus the 16px sans / 14px muted pair through the empty state's own class names, still escaped (C1/T-22-44, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_empty_state_default_form_is_byte_identical_and_compact_is_opt_in |
| 80 | on a fresh install Health's two IN-TILE empty states (Corroboration, Resolution rate) use the compact form while its two full-width card empty states (Battery trend, Unresolved prefixes) keep the default 22px serif one (C1/X8, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_health_in_tile_empty_states_are_compact_and_card_ones_are_not |
| 81 | the Resolution-rate tile's detail line has a singular form, so a window holding exactly one detection never reads '1 events' / '1 événements', in both languages, and both templates carry their own French catalogue entry (D-06/B16/CFG-29, 22-12-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_resolution_detail_line_has_a_singular_form[total=1-en] |
| 82 | DEVICE_STATE_TEXT has exactly ok/warn/error/off (widened by 22-04-PLAN.md Task 3 for the frame's own held state), PIPELINE_STATE_TEXT has exactly ok/warn/error/off (B2, 22-03-PLAN.md Task 1) and CORROBORATION_STATE_TEXT has exactly ok/warn (it has no error state) (D-03/A-21) | ported | companion/test_status_pages_02.py::test_state_text_dicts_have_expected_key_sets |
| 83 | a genuinely never-ran pipeline (no META_LAST_PIPELINE_RUN, no META_LAST_DETECTION) renders the neutral verdict with the existing dot--off class, zero dot--warn, zero battery-fallback text, no second detail line, and no anomaly banner when the device is healthy (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_pipeline_never_ran_renders_neutral_no_warn_no_banner |
| 84 | the same never-ran pipeline tile reads in French — 'Aucune détection pour l’instant.', dot--off, zero dot--warn, zero French battery-fallback text (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_pipeline_never_ran_renders_neutral_in_french |
| 85 | compute_health_state()'s pipeline_detail_html key, for a never-ran pipeline, is the bare PIPELINE_NEVER_RAN_DETAIL_TEXT sentence — no widget-verdict class, no PIPELINE_STATE_TEXT verdict text — embedded once inside pipeline_html (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_02.py::test_compute_health_state_carries_pipeline_detail_html_never_ran |
| 86 | compute_health_state()'s pipeline_detail_html key, once the pipeline has run at least once, is verdict-free and embedded once inside pipeline_html, mirroring device_detail_html (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_03.py::test_compute_health_state_carries_pipeline_detail_html_has_run |
| 87 | collect_anomalies()/overall_severity() treat pipeline_state='off' (never ran) exactly like 'ok' — never an anomaly, never a warn — while a genuinely stale pipeline_state still is (B2, 22-03-PLAN.md Task 1) | ported | companion/test_status_pages_03.py::test_collect_anomalies_and_overall_severity_treat_pipeline_off_as_healthy |
| 88 | battery_sparkline_svg() still returns '' for fewer than two numeric readings, and the page emits neither a readout element nor a chart script tag (D-09 regression guard) | ported | companion/test_status_pages_03.py::test_single_reading_still_no_chart_no_readout_no_script |
| 89 | a chart-bearing page emits exactly one scoped <script src> and zero inline event-handler attributes | ported | companion/test_status_pages_03.py::test_page_allows_exactly_one_scoped_script_no_inline_handlers |
| 90 | the empty-history battery path stays script-free — no <script, no <svg, no readout element | ported | companion/test_status_pages_03.py::test_empty_battery_history_stays_script_free |
| 91 | a hostile timestamp reaching data-ts/<title> is escaped, never interpolated raw | ported | companion/test_status_pages_03.py::test_hostile_timestamp_is_escaped_in_chart_markup |
| 92 | the Python/CSS/JS three-file contract (route + DOM literals) is guarded against silent drift | ported | companion/test_status_pages_03.py::test_cross_file_contract_drift_guard |
| 93 | a large consecutive-reading drop flags a battery warning (demoted from error, D-05); a gentle monotonic decline does not | ported | companion/test_status_pages_03.py::test_battery_drop_flags_anomaly_gentle_decline_does_not |
| 94 | overall_severity()'s widened 6-input precedence table: source_fault wins outright, error states win next, then warn states/disagreement_warn/coverage_state=='warn', with the 4-argument call staying byte-for-byte backward compatible (19-05-PLAN.md Task 3/D-05) | ported | companion/test_status_pages_03.py::test_overall_severity_widened_precedence_table |
| 95 | overall_severity()'s plan-cited acceptance triple: ('ok', 'error', 'warn') (19-05-PLAN.md Task 3) | ported | companion/test_status_pages_03.py::test_overall_severity_acceptance_criteria_literal |
| 96 | compute_health_state() folds an active source_fault_raw alone into error severity, a non-empty registry alone into warn severity, and stays ok when both are clear (19-05-PLAN.md Task 3/D-05) | ported | companion/test_status_pages_03.py::test_source_fault_alone_produces_error_registry_alone_produces_warn |
| 97 | collect_anomalies()'s two new items (source_fault, coverage_state) appear only when their own input is unhealthy, and a fully healthy 4-argument call still returns none (19-05-PLAN.md Task 3) | ported | companion/test_status_pages_03.py::test_collect_anomalies_two_new_items |
| 98 | a device last seen 400 seconds ago is 'warn' at a 30s wake cadence but 'ok' at a 3600s cadence, pinned from both directions through the real compute_health_state() pipeline (19-05-PLAN.md Task 3/D-05, A-23) | ported | companion/test_status_pages_03.py::test_device_staleness_pinned_from_both_directions_by_cadence |
| 99 | corroboration counts made only of the unknown state produce no error status class | ported | companion/test_status_pages_03.py::test_corroboration_unknown_only_no_error_or_warn |
| 100 | a fully-healthy fixture renders no anomaly banner at all | ported | companion/test_status_pages_03.py::test_no_anomaly_banner_when_all_healthy |
| 101 | a stale ADS-B pipeline shows the anomaly banner copy exactly once | ported | companion/test_status_pages_03.py::test_stale_pipeline_shows_banner_exactly_once |
| 102 | a state directory that cannot hold a database renders the health-unavailable copy without raising | ported | companion/test_status_pages_03.py::test_unreadable_database_degrades_without_raising |
| 103 | with the source-fault meta key set, the CFG-05 landing explanation appears | ported | companion/test_status_pages_03.py::test_source_fault_set_shows_landing_explanation |
| 104 | with the source-fault meta key unset, the CFG-05 landing explanation is absent | ported | companion/test_status_pages_03.py::test_source_fault_unset_hides_landing_explanation |
| 105 | companion/pages/health_page.py never imports the stdlib html module directly | ported | companion/test_status_pages_03.py::test_health_page_never_imports_html_module |
| 106 | Health opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_status_pages_03.py::test_health_page_opens_with_shared_page_header |
| 107 | Health's .page-header carries a one-sentence purpose after the auto-refresh pill (quick task 260901-tsa, finding A; retargeted in place by 260902-chc) | ported | companion/test_status_pages_03.py::test_health_page_purpose_sentence_present_after_refresh |
| 108 | Health's body is two id-anchored sections (Screen, then Server & data), and the old 'Overview' heading is gone (D-10) | ported | companion/test_status_pages_03.py::test_health_page_two_id_anchored_sections_correct_order_no_overview |
| 109 | each of Health's two section headings is paired, in its own baseline-aligned .section-intro wrapper, with its own muted description (quick task 260901-tsa, finding B) | ported | companion/test_status_pages_03.py::test_health_page_section_intros_pair_heading_with_description |
| 110 | the Screen section's dashboard-grid holds exactly one tile, the Server & data dashboard-grid holds exactly three, the two migrated cards render as nested page-section elements outside both, and the source-fault block never carries that modifier (D-11/finding E, quick task 260901-uzi finding 4) | ported | companion/test_status_pages_03.py::test_server_data_grid_holds_three_tiles_migrated_cards_outside_grid |
| 111 | the Resolution-rate tile renders the resolved percentage and the window/event-count line for a seeded fixture, and the no-stats empty state for an empty one (D-10/D-11) | ported | companion/test_status_pages_03.py::test_resolution_rate_tile_renders_percentage_and_window |
| 112 | the migrated Unresolved-prefixes card keeps its filter bar, read-only note, and non-button Clear control (D-12) | ported | companion/test_status_pages_03.py::test_registry_card_keeps_filter_bar_note_and_non_button_clear |
| 113 | the read-only note is reworded to name Airlines as the resolution surface, no longer points at the manual runbook (phase 13 D-10), no longer says 'prefix' in either half (19-06-PLAN.md Task 3, D-06), and (29-06-PLAN.md Task 2, CFG-79) is now split into a short visible sentence plus its moved instruction inside a readings-disclosure | ported | companion/test_status_pages_03.py::test_read_only_note_reworded_to_point_at_airlines_not_the_runbook |
| 114 | _SOURCE_ROWS has a fifth 'manual' entry, resolution_stats() folds a seeded 'manual' route_source count into the total and a labelled row, and render() shows a 'Manual' row (phase 13 D-02) | ported | companion/test_status_pages_03.py::test_source_rows_gains_fifth_manual_entry |
| 115 | resolution_stats() counts a NULL and an unrecognised route_source into one 'Other' bucket, the total equals every row in the window, and render() shows the 'Other' row (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_stats_counts_unknown_route_source_as_other |
| 116 | resolution_stats() with only known route_source values renders exactly the five _SOURCE_ROWS rows and no 'Other' row — byte-identical to before this task (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_stats_known_sources_alone_gain_no_other_row |
| 117 | the empty 'How well we name flights' section is entirely absent from the rendered page in both English and French — never a heading over an empty body (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_stats_section_absent_when_empty_both_languages |
| 118 | with 36 seeded rows (30 known, 6 with a NULL route_source) the resolution-rate tile shows a non-zero count for all 36, never the empty-state copy (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_resolution_rate_tile_shows_36_rows_never_no_events |
| 119 | _NO_STATS_HEADING is an unformatted %d template with no hard-coded window literal, and interpolates RESOLUTION_WINDOW_DAYS at its one call site (B3, 22-03-PLAN.md Task 2) | ported | companion/test_status_pages_03.py::test_no_stats_heading_derives_from_window_constant_not_hard_coded |
| 120 | the registry's per-row Resolve link is paired identically (href/aria-label) across the desktop table and mobile card, with distinct visible text per representation, and a hostile prefix renders fully escaped in both (phase 13 D-10, T-13-05) | ported | companion/test_status_pages_03.py::test_registry_resolve_link_pairs_desktop_and_mobile_and_escapes_hostile_input |
| 121 | companion/pages/health_page.py still contains zero HTML form elements and exactly one '<button' literal (the pre-existing D-16 docstring mention only) — Health still gains no state-changing (form-submitting) control (phase 13 D-10, T-13-13; retargeted in place by 21-02-PLAN.md Task 1, D-18) | ported | companion/test_status_pages_03.py::test_health_still_has_no_form_and_no_button_in_any_state[normal] |
| 122 | the battery heading's sibling caption <p> (retargeted from the retired trailing <span>, 29-06-PLAN.md Task 1/CFG-84) and the Unresolved-prefixes read-only note both compose section-caption with their existing sizing class, and style.css's .section-caption still declares exactly one property at the file's single 70% muted strength (quick task 260902-gjj, ISSUE 1) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_muted_captions_compose_section_caption |
| 123 | corrupting only the database leaves the registry card rendering while the stats card degrades, and vice versa (D-11) | ported | companion/test_status_pages_03.py::test_migrated_cards_have_independent_failure_isolation |
| 124 | _read_health_inputs() carries exactly nine keys — device_config and registry_rows now join it for severity's sake (19-05-PLAN.md Task 3/D-05) — while the stats read alone stays a separate call in render() (D-11) | ported | companion/test_status_pages_03.py::test_read_health_inputs_keeps_stats_separate |
| 125 | the battery-trend section keeps its own status modifier (retargeted from the retired badge, quick task 260902-gjj), readout, and single script tag after moving out of the grid | ported | companion/test_status_pages_03.py::test_battery_section_keeps_everything_after_the_move |
| 126 | the battery-trend heading carries ONLY its short fixed text (no inline precision span), immediately followed by a sibling <p class="text-label section-caption"> carrying _battery_trend_caption()'s own text, itself followed by the chart/table body — index(h2) < index(caption) < index(body) (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_heading_is_short_and_precision_lives_in_a_sibling_caption |
| 127 | the battery-trend heading's rendered text equals i18n.t_lang(BATTERY_SECTION_HEADING_TEMPLATE, lang) % (BATTERY_TREND_WINDOW_DAYS // 30) in both English and French — a relationship against the real constants, not a typed literal (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_heading_equals_template_times_window_in_both_languages |
| 128 | all three _battery_trend_caption() branches (usable daily series, no rows at all, sub-two-day raw series) render their own exact text inside the sibling caption <p>, never inside the heading (29-06-PLAN.md Task 1, CFG-84) | ported | companion/test_status_pages_03.py::test_battery_trend_caption_all_three_branches_render_in_sibling_caption |
| 129 | the battery readout precedes the chart and the script tag inside the battery-trend section, carries its single expected class plus role="status" plus both value/detail spans, and battery-trend.js still looks it up by id (quick task 260901-tsa finding D, retargeted by quick task 260901-uzi finding 3) | ported | companion/test_status_pages_03.py::test_battery_readout_precedes_chart_class_list_and_live_region |
| 130 | health_page.BATTERY_SECTION_CLASS is guarded against silent drift from companion/static/style.css | ported | companion/test_status_pages_03.py::test_battery_section_class_is_styled_in_stylesheet |
| 131 | the battery-trend and Unresolved-prefixes cards each carry the status modifier layout.card_status_class() derives from battery_status()/coverage_status()'s own real return value on the same rows, the Resolution-statistics card carries none, and style.css declares all three doubled-form status rules for both card components (quick task 260902-gjj, ISSUE 2) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_card_status_borders_render_correct_modifiers |
| 132 | every card-status modifier selector (battery-trend-section, page-section, and — quick task 260902-gjj Task 3 — stat-tile) sits after that component's own :hover/:focus-within rule in style.css's source order, so the status border survives hover and keyboard focus rather than losing to the hover shorthand | ported | companion/test_status_pages_03.py::test_card_status_modifiers_survive_hover_source_order |
| 133 | the battery-trend and Unresolved-prefixes cards render no dot-label anywhere inside their own boundaries, the Corroboration tile's three dots survive untouched (proving the removal is scoped, not global), and BATTERY_STATUS_LABEL/_battery_badge_block are both gone via hasattr, never a source grep (quick task 260902-gjj, ISSUE 2) | ported | companion/test_status_pages_03.py::test_quick_260902_gjj_dot_removal_scoped_not_global |
| 134 | style.css's .section-intro / .section-intro > p / .stat-tile__value .mono / .battery-readout rules each carry their load-bearing declaration, and .mono precedes .battery-readout in source order (quick task 260901-tsa) | ported | companion/test_status_pages_03.py::test_quick_260901_tsa_css_dom_contract_guard |
| 135 | style.css's .dashboard-grid declares an explicit cross-axis stretch (the UXA-06 reversal) and no longer declares start, and .dashboard-shell's own separate start-aligned declaration (D-21's sticky sidebar) is the file's only remaining one (quick task 260901-uzi finding 1) | ported | companion/test_status_pages_03.py::test_dashboard_grid_stretches_same_row_tiles |
| 136 | style.css's .data-table th declares a symmetric, non-zero vertical padding via the two-value shorthand (quick task 260902-dng bug 2, closes 260901-uzi Finding 5 candidate (a)) | ported | companion/test_status_pages_03.py::test_data_table_th_has_symmetric_nonzero_padding |
| 137 | exactly the two migrated cards carry page-section--nested (located by their own heading constants), the source-fault block never carries it even when it renders, both .section-intro headings are untouched, and style.css's nested-heading rule — promoted by 06.6.4.1.1 D-09's deliberate second reversal — declares the sans family, the Body size (16px) and the semibold weight explicitly (plus its retained 260902-bl2 bottom margin), sitting below a .text-heading section-heading tier confirmed still 22px/regular at the token level too (quick task 260901-uzi finding 4, Check 2; reverted by quick task 260902-iag; re-promoted by 06.6.4.1.1 plan 02 Task 2) | ported | companion/test_status_pages_03.py::test_nested_heading_tier_promoted_to_sans_semibold_emphasis_role |
| 138 | style.css's .stat-tile__caption converges on the one unified 12px uppercase label voice (D-13) — sans family, 12px size, semibold weight, uppercase transform and 0.06em tracking all declared explicitly, with no serif token named anywhere in its rule body — while .stat-tile__value keeps its own untouched D-09 Emphasis-role size/weight, the nested card title stays on its own D-09-second-reversal sans-semibold Body-size declarations, the shared h1/h2/h3/legend/.text-heading serif rule keeps its regular weight, and the token table reads 14/16/22px (supersedes quick task 260902-dng Task 3's semibold promotion and quick task 260902-iag Task 2's reversal of it — 06.6.4.1.1 plan 02 Task 3) | ported | companion/test_status_pages_03.py::test_stat_tile_caption_joins_the_unified_label_voice |
| 139 | Health's two-tier hierarchy (D-10 section headings vs. the cards nested inside them) still reads apart with no font-size or font-weight distinction between the tiers: every level-2 heading (Battery trend, Unresolved prefixes, Resolution statistics) sits inside a bordered card <section>, both level-1 headings (Screen, Server & data) sit inside the plain .section-intro row with no card class, a .dashboard-grid always intervenes between a level-1 heading and the first level-2 card in its own section, and the four spacing tiers that now carry the distinction stay strictly ordered against their real :root token values — in both the empty and seeded state (quick task 260902-iag Task 3) | ported | companion/test_status_pages_03.py::test_two_tier_hierarchy_carried_by_layout_not_type |
| 140 | all three nested Health cards (Battery trend, Unresolved prefixes, Resolution statistics) show one heading-to-content rhythm in both the empty and seeded state — the element after </h2> is either rhythm-governed p.text-body or a member of the verified no-top-margin allowlist — and style.css's demotion rule/prose rhythm rule carry the sketch's two margin values in the right source order (quick task 260902-bl2 Task 3, Check 2) | ported | companion/test_status_pages_04.py::test_nested_card_heading_rhythm_holds_for_every_allowed_element |
| 141 | exactly the Resolution-statistics table carries data-table--prose, neither the battery readings table nor the unresolved-prefix registry table does, and style.css's .data-table--prose sits after .data-table with the shared max-content floor still intact on the base rule (quick task 260901-uzi finding 2, Check 3) | ported | companion/test_status_pages_04.py::test_resolution_statistics_table_is_the_only_data_table_prose |
| 142 | the Description column is the only muted column end to end — markup (exactly len(_SOURCE_ROWS) desc cells, all inside Resolution-statistics), builder (data_table()'s desc_columns contract: inert default, byte-identical mono-only output, additive-only desc-only output, both-roles joining mono first) and stylesheet (.data-table td.desc's 70% muted colour, no min-width, no opacity, no muted token anywhere in the file) (quick task 260902-bl2 Task 3, Check 1) | ported | companion/test_status_pages_04.py::test_description_column_is_the_only_muted_column |
| 143 | the Resolution-statistics table has a complete mobile .data-cards representation — one item per _SOURCE_ROWS entry, every label/full-gloss/count present, positioned before its unchanged desktop table (quick task 260903-ghy Task 1, Check A / UIR-10) | ported | companion/test_status_pages_04.py::test_stats_cards_list_is_complete_and_precedes_the_table |
| 144 | the .data-cards mobile toggle contract exists at both breakpoints, .data-card__label mirrors .data-table th's label tier by value, .data-table-wrap's scroll-edge shadow is untouched, and the three literal selectors this harness indexes by elsewhere are all still present (quick task 260903-ghy Task 1, Check B) | ported | companion/test_status_pages_04.py::test_data_cards_toggle_contract_and_untouched_rules |
| 145 | the registry's mobile .data-cards representation is exactly paired with its table by (data-filter-text, data-filter-group), carries concise_timestamp_html()'s own First/Last seen markup exactly once each while the desktop table carries the stacked cell built from the same two formatters over the same now (retargeted by 22-12-PLAN.md Task 2's B12), positioned between the filter bar and the table wrap, and every column (prefix, count, both timestamps, example callsign) is reachable in the card slice (quick task 260903-ghy Task 2, Check C / UIR-11) | ported | companion/test_status_pages_04.py::test_registry_mobile_cards_paired_with_the_desktop_table |
| 146 | the unresolved-prefix table fits by the two levers headless measurement selected — the Flights stacked-cell precedent scoped to its own data-table--registry modifier (the base no-crop floor kept), plus two shortened French headers with the retired long forms gone and the English sources untouched — and never by a 1100px card fallback (B12, 22-12-PLAN.md Task 2) | ported | companion/test_status_pages_04.py::test_registry_table_fits_by_stacked_cells_and_short_french_headers |
| 147 | no card chrome renders for an empty registry (filter bar and .data-cards both absent, empty_state() present instead); both migrated tables together render exactly two .data-cards lists; History and Airlines carry zero occurrences of the new card class names (quick task 260903-ghy Task 2, Check D) | ported | companion/test_status_pages_04.py::test_no_chrome_for_empty_registry_and_no_cross_page_leak |
| 148 | the battery readout carries its id, role="status", both value/detail spans and a humanised visible detail with the machine-precise ISO only in the tooltip, every chart hit target carries data-when, and battery-trend.js's shipped source still reads that attribute, both span classes, and the readout's id literal (quick task 260901-uzi finding 3, Check 4) | ported | companion/test_status_pages_04.py::test_humanised_battery_readout_end_to_end |
| 149 | style.css's .mono reach-through covers both .stat-tile__value and .battery-readout in one rule, and .battery-readout__detail carries the Label size, the regular weight and the file's existing 70% muted strength (quick task 260901-uzi finding 3, Check 5) | ported | companion/test_status_pages_04.py::test_readout_typographic_split_stylesheet_guard |
| 150 | anomaly_active() and the anomaly banner's presence agree in both directions, across healthy and unhealthy fixtures | ported | companion/test_status_pages_04.py::test_anomaly_active_agrees_with_the_banner_both_directions |
| 151 | anomaly_active() runs on every page render and must never raise — missing/empty/file/corrupt-db inputs all degrade safely - expected False for a non-existent state_dir path | ported | companion/test_status_pages_01.py::test_anomaly_active_never_raises_on_hostile_inputs |
| 152 | battery and corroboration section-builder markup (dot, table, svg) survives the stat-tile reframe untouched | ported | companion/test_status_pages_04.py::test_section_builder_markup_survives_the_stat_tile_reframe |
| 153 | Health's three Health-signal icons are tile-only (device, pipeline, corroboration, all whitelisted and tile-tinted) and no Health <h2> — empty or seeded render — carries a glyph any more; health_page.ICON_BATTERY is gone from the module namespace (quick task 260902-j8w) | ported | companion/test_status_pages_04.py::test_health_tile_icons_are_tile_only_and_no_heading_carries_a_glyph |
| 154 | the D-12 reversal (260902-chc) is written down at both prose sites it touches — freshness.js's own header and D-12's own CONTEXT.md entry — each carrying the house SUPERSEDED token and naming this quick task, with D-12's original wording intact | deleted | P: asserted plan-history prose in a freshness.js header comment and in a .planning CONTEXT.md; no behaviour |
| 155 | freshness.js's shipped source carries the loop's own contract — a named interval constant inside the 30-60s band, both halves of pause (setInterval+clearInterval) and visibility (visibilitychange+document.hidden), the double-start guard, and (19-09-PLAN.md, D-02) the retired reload form gone entirely while fetch(/DOMParser/replaceChild/importNode are now required present as this file's own reviewed exception to the forbidden-sink/no-URL-taking-navigation-form/ES5-safe-subset disciplines, which otherwise still hold unchanged | ported | companion/test_status_pages_04.py::test_freshness_js_carries_the_refresh_loop_contract |
| 156 | the auto-refresh pill's markup contract (marker attribute, inline element, hidden-by-default, live data-loaded-at exactly once page-wide, the pill-copy constant's own value, inside .page-header, preceding the purpose sentence) holds on a real render both seeded and on a fresh state directory with no readings at all — proven unconditional, not coupled to the battery chart's own render branch | ported | companion/test_status_pages_04.py::test_auto_refresh_pill_markup_contract_holds_seeded_and_fresh |
| 157 | style.css's .refresh-pill / .refresh-pill[hidden] / pill-scoped icon rules each carry their load-bearing declaration — the [hidden] override hides by visibility with no display value at all — .banner__pill still precedes .refresh-pill in source order, and the pill is taken out of .page-header's block flow entirely via a .page-header-scoped absolute-position rule rather than kept in flow with a reserved line box (260902-ep7) | ported | companion/test_status_pages_04.py::test_refresh_pill_stylesheet_contract |
| 158 | the pipeline tile's new second line renders META_LAST_DETECTION's timestamp byte-identically to concise_timestamp_html(), reusing the existing muted text-label/section-caption tier — never battery-readout__detail, whose class name would collide with the BATTERY_READOUT_ID absence guards (quick task 260903-peo, UIR-14) | ported | companion/test_status_pages_04.py::test_pipeline_tile_second_line_renders_last_detection_timestamp |
| 159 | the pipeline tile's second line renders its honest no-reading-yet fallback when META_LAST_DETECTION is absent, never an empty element or a dangling label (quick task 260903-peo, UIR-14) | ported | companion/test_status_pages_04.py::test_pipeline_tile_second_line_falls_back_honestly_when_no_detection |
| 160 | Health's header renders an honest 'Updated HH:MM' clock — server-rendered as the text of a <time data-relative> element, never the ladder's zero bucket, so the value is true with scripts blocked and live with them (23-06-PLAN.md) — (no relative-age suffix, the full Europe/Paris local timestamp — never the raw ISO — in the clock span's title, retargeted by 22-16 for D-05/CFG-28) beside the unchanged hidden refresh pill and NO Pause/Resume toggle (zero data-refresh-toggle/data-pause-text/data-resume-text, zero <button>), all inside one block-level .page-header__freshness wrapper that is the .page-header's next child right after the <h1>, in prefix/clock/pill source order (21-02-PLAN.md Task 1, D-18; supersedes 19-09-PLAN.md Task 1's Pause/Resume-toggle contract, itself superseding quick task 260903-peo/UIR-18's 'Live — refreshed (Ns ago)' contract) | ported | companion/test_status_pages_04.py::test_health_header_renders_the_persistent_freshness_note |
| 161 | the four UIR-03/07/12/13 one-line fixes hold together: .banner wraps with a nowrap .banner__label rendered on the anomaly banner's lead span, .banner__pill gains min-width: 0 while keeping flex: none and its source position before .refresh-pill, .airline-card__image gains height: auto alongside its surviving aspect-ratio, the .data-table--prose first-column nowrap rule exists after the base rule, and the rendered Battery trend heading's sibling caption follows immediately with no leading em dash of its own (UIR-12, retargeted by 29-06-PLAN.md Task 1/CFG-84; quick task 260902-v2v) | ported | companion/test_status_pages_04.py::test_uir_03_07_12_13_one_line_fixes_hold_together |
| 162 | the two-role spacing split holds as a pair: .dashboard-grid's margin-bottom equals .page-section's own same-section card-to-card value (var(--space-lg)), while .battery-trend-section's section-transition margin-bottom stays the larger, untouched var(--space-2xl) (260902-ep7 BUG 2) | ported | companion/test_status_pages_04.py::test_dashboard_grid_and_battery_trend_section_keep_their_two_role_spacing_split |
| 163 | the desktop-padding/mobile-density pair holds together: .page-section, .theme-status and .battery-trend-section all still declare padding: var(--space-md) in their own base rules, and one shared rule inside the @media (min-width: 960px) block raises all three to padding: var(--space-lg) (06.6.4.1.1-03 D-15) | ported | companion/test_status_pages_04.py::test_desktop_padding_and_mobile_density_pair_holds_together |
| 164 | the bare summary rule declares var(--color-accent), and style.css's own exhaustive accent-reservation list explicitly names the summary's label text (not just its ::marker) — the broadening is recorded, not silent (260902-ep7 BUG 3) | ported | companion/test_status_pages_04.py::test_bare_summary_rule_declares_the_accent_colour |
| 165 | the interaction-skip guard's cross-file contract: a fixture rich enough to actually render a disclosure, a filter input and a chart hit target, and freshness.js's shipped source still checks for a focused INPUT/SUMMARY and health_page.SPARKLINE_HIT_CLASS's own literal value but no longer checks for an open <details> at all (19-09-PLAN.md, D-02: a targeted swap never touches one, so the silent-suspension clause is gone, not merely unused) — this guard's failure mode is silence, so this check is the only thing that would notice a drift | ported | companion/test_status_pages_04.py::test_interaction_skip_guard_cross_file_contract |
| 166 | every layout.REFRESH_SWAP_SELECTORS_BY_PAGE entry, on every page key, appears verbatim in freshness.js, and freshness.js never carries a .sparkline-hit selector literal, a [data-filter-input] reference, or a details[...] selector — the three regions Pitfall 5 names as fatal to swap (19-09-PLAN.md Task 3, generalised in place from the one-tuple form by 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_swap_selectors_pinned_both_directions |
| 167 | the swap registry has ONE definition site (health_page.REFRESH_SWAP_SELECTORS resolves from layout.REFRESH_SWAP_SELECTORS_BY_PAGE and is that same object, with Health's five regions in their existing order, and no second tuple literal survives in health_page.py) and ONE key set (the script's registry keys equal the Python's, in both directions), with every selector appearing exactly once per registry entry in the script's comment-stripped code and the registry actually read (D1/CFG-35, 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_swap_registry_has_one_definition_site_and_one_key_set |
| 168 | the swap registry is selected by a page key the SERVER renders on <body> — present for every registry key and for a page with no entry at all — and freshness.js reads that attribute and resolves it with an own-property test, so an unknown key is a no-op rather than an inherited Object property (D1/CFG-35, 23-06-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_page_key_is_server_rendered_and_gates_the_loop |
| 169 | freshness.js knows three things it must not repaint: swapNodes() keeps 22-15's unchanged-region and focused-region skips and gains a per-region pending skip, and tick() stands the whole cycle down while dirty-state.js's own window.SkyPaneDirtyState.hasUncommittedEdits() reports unsaved edits — with the interval, ladder, ceiling, in-flight guard and redirect:manual all untouched (D1/CFG-35, 23-06-PLAN.md Task 1; retargeted from the retired save bar by 27-04-PLAN.md, CFG-63) | ported | companion/test_status_pages_04.py::test_freshness_loop_knows_three_things_it_must_not_repaint |
| 170 | Flights' swap registry entry covers the phone card list, the desktop table, the live count and the freshness line, EXCLUDES every element list-filter.js captures once at load (the input, Clear, the empty state and the set hooks), nests no entry inside another, is keyed by nav_slug()'s own value, and the registry's own comment states the exclusion's reason (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_flights_swap_registry_entry_covers_and_excludes_the_right_regions |
| 171 | freshness.js's new-row highlight is a DIFF over server-rendered row identity: its two cross-file literals equal layout.REFRESH_ROW_ID_ATTR/REFRESH_NEW_ROW_CLASS, the known set is populated from the page as first rendered rather than empty, the diff runs from applySwap() and from nowhere else, resolves the set with an own-property test, applies one class through classList and never removes it, and writes no markup (D7/CFG-37, 23-08-PLAN.md Task 1) | ported | companion/test_status_pages_04.py::test_freshness_new_row_highlight_is_a_diff_never_a_first_paint |
| 172 | Health's and Home's freshness lines are layout.freshness_line_html()'s own output verbatim — ONE definition site, the markup gone from health_page.py entirely — each page renders exactly one data-loaded-at and one data-refresh-pill, and the builder emits the dot, the prefix, the clock element and the pill in that order with exactly one <time data-relative> (D1/CFG-35, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_freshness_line_has_one_builder_and_three_call_sites |
| 173 | Home declares the four regions that actually change between polls (the strip, the status tiles, the picture, the recent-flights list) plus its freshness line, every literal in every one of its selectors appears in the rendered page, and the Display scope declares exactly the strip and the freshness line — everything else there is a form (D1/CFG-35, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_home_declares_the_regions_it_actually_renders |
| 174 | the Frame strip's next-update cell carries a marked <time data-relative-countdown> over companion/wake.py's OWN resolved instant, reading the ladder's future form, beside a state word that stays frame_state.resolve_state()'s — and no script in companion/static names a state or a headline template at all (D1/D-03/CFG-26, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_strip_countdown_formats_and_never_decides |
| 175 | the refreshed picture fades through a named keyframes block spending var(--motion-fast) with no bare literal, the class is applied only after freshness.js compares the image's own src (a fade on every swap would flash the page every 45s for no information), and the server renders it never (D1+D3/CFG-32, 23-06-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_23_06_the_picture_fades_only_when_the_picture_changed |
| 176 | layout.stat_tile()'s new caption_title parameter is byte-identical to the pre-existing output when omitted, None, or '' (19-06-PLAN.md Task 1, D-06) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_byte_identical_when_unused |
| 177 | layout.stat_tile()'s caption_title renders as a title attribute on the caption <p> element, and nowhere else (19-06-PLAN.md Task 1, D-06) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_renders_as_tooltip_on_caption_only |
| 178 | layout.stat_tile()'s caption_title is escaped through escape_html(), matching every other attribute value this module emits (19-06-PLAN.md Task 1, D-06/T-19-08) | ported | companion/test_status_pages_05.py::test_stat_tile_caption_title_is_escaped |
| 179 | Health's stat tiles and corroboration rows read in plain language: 'Corroboration', 'Single-source (uncorroborated)' and 'pipeline last ran' are all absent from visible text, and the Pipeline/Corroboration/Resolution-rate tiles' caption elements each carry a title attribute equal to their matching technical constant (19-06-PLAN.md Task 2, D-06) | ported | companion/test_status_pages_05.py::test_health_tiles_and_rows_read_in_plain_language |
| 180 | a full Health render with a non-empty unresolved registry and stats rows (every branch rendered) contains no 'adsbdb' and no CFG-\d requirement id outside a title attribute (19-06-PLAN.md Task 3, D-06/T-19-24) | ported | companion/test_status_pages_05.py::test_health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id |
| 181 | all 52 vendored illustrations normalize to the exact same pixel dimensions (illustration_normalize.ILLUSTRATION_TARGET_SIZE) | ported | companion/test_status_pages_05.py::test_all_illustrations_normalize_to_identical_pixel_dimensions[air-algerie.png] |
| 182 | all 52 vendored illustrations normalize and serve well under 65536 bytes per file, the UIR-08 weight fix — a regression that got the dimensions right but left the served bytes unchanged would defeat this check | ported | companion/test_status_pages_05.py::test_all_illustrations_serve_well_under_the_byte_ceiling[air-algerie.png] |
| 183 | all 52 vendored illustrations normalize with their painted content centred within 1px on both axes and never clipped | ported | companion/test_status_pages_05.py::test_all_illustrations_are_centred_and_unclipped[air-algerie.png] |
| 184 | a source image whose opaque bbox is None (nothing painted) falls back to the source image instead of raising, and still normalizes to the target output size | ported | companion/test_status_pages_05.py::test_none_opaque_bbox_falls_back_to_source_image_without_raising |
| 185 | no module anywhere under companion/ defines its own alpha-threshold constant — the threshold is only ever imported from server.plane.render | deleted | S: asserted source text (a companion-wide scan for a second ALPHA_THRESHOLD constant definition); no behavior beyond what this module's own centred/unclipped-bbox checks already prove by calling server.plane.render._opaque_bbox() directly |
| 186 | page_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and <html lang="en" otherwise (D-03) | ported | companion/test_status_pages_05.py::test_page_shell_html_lang_follows_prefs |
| 187 | login_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and <html lang="en" otherwise (D-03) | ported | companion/test_status_pages_05.py::test_login_shell_html_lang_follows_prefs |
| 188 | a rendered shell contains exactly two aria-labelled theme-form forms per footer copy, actions /ui-lang, /ui-theme in that document order, and zero /ui-mode forms (D-02/D-17, 21-UI-SPEC.md §G) | ported | companion/test_status_pages_05.py::test_shell_has_two_ordered_theme_forms_each_with_aria_label |
| 189 | under lang='fr' the nav reads Accueil/Affichage/Vols/Compagnies/Avancé/État/Appareil (D-09) | ported | companion/test_status_pages_05.py::test_french_shell_nav_reads_the_locked_french_labels |
| 190 | the Advanced group (Health, Device) and the nav status dot always render, in both the sidebar and the bottom tab bar, on a plain request (D-17; retargeted from the dropdown by 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_05.py::test_advanced_group_always_renders_in_both_nav_copies |
| 191 | the sidebar and the mobile dropdown each contain exactly one .nav-status link, with no <form> or <button> inside it, sitting after the brand and before the primary nav list in document order (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_appears_once_in_each_nav_copy_after_the_brand |
| 192 | nav_status_html()'s two dots follow all four Screen/Quiet-hours on/off combinations (dot--ok for on, dot--off for off) (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_dot_classes_follow_the_four_on_off_combinations |
| 193 | under lang='fr' the reminder reads 'Écran allumé' and 'Heures calmes désactivées' — fully French, never 'Heures calmes off' (R-04) | ported | companion/test_status_pages_05.py::test_french_nav_status_reads_ecran_allume_heures_calmes_desactivees |
| 194 | nav_status_html(None) and nav_status_html({}) both return '', and page_shell(..., device_config=None) — the default, used by login/404/error pages — renders no .nav-status at all (D-03) | ported | companion/test_status_pages_05.py::test_nav_status_html_none_or_falsy_device_config_renders_nothing |
| 195 | login_shell() — which never takes a device_config parameter — carries no .nav-status markup, unchanged by this task (D-03) | ported | companion/test_status_pages_05.py::test_login_shell_carries_no_nav_status_and_is_unchanged |
| 196 | status_row('Frame', 'Checking in normally', 'Last check-in 2m ago', 'ok') carries status-row--ok, dot--ok, all three texts and exactly one status-row__label (D-21) | ported | companion/test_status_pages_05.py::test_status_row_renders_dot_label_verdict_detail |
| 197 | status_row('', ..., 'warn') omits the status-row__label span entirely, not merely its text (D-21, 20-UI-SPEC.md Section Anatomy A) | ported | companion/test_status_pages_05.py::test_status_row_empty_label_omits_the_label_span |
| 198 | status_row(..., state='nonsense') falls back to the default dot class and emits no status-row--nonsense class (T-20-18) | ported | companion/test_status_pages_05.py::test_status_row_unrecognised_state_falls_back_safely |
| 199 | status_row() with a hostile <script>-shaped verdict/detail comes back escaped, never raw markup (T-20-03) | ported | companion/test_status_pages_05.py::test_status_row_escapes_hostile_verdict_and_detail |
| 200 | layout.section_intro_html() emits the byte-identical markup health_page.py's own former private _section_intro_html() rendered before the promotion (20-UI-SPEC.md Section Anatomy C) | ported | companion/test_status_pages_05.py::test_section_intro_html_is_byte_identical_to_the_promoted_markup |
| 201 | layout.section_intro_html() escapes a hostile section_id argument, never writing it raw into the id="..." attribute (WR-03, 20-REVIEW.md) | ported | companion/test_status_pages_05.py::test_section_intro_html_escapes_hostile_section_id |
| 202 | health_page no longer defines its own _section_intro_html — layout.section_intro_html is the one definition | ported | companion/test_status_pages_05.py::test_health_page_no_longer_defines_section_intro_html |
| 203 | _device_timestamp_only() emits no widget-verdict class and no DEVICE_STATE_TEXT value, while _device_section() still carries exactly one (D-17) | ported | companion/test_status_pages_05.py::test_device_timestamp_only_carries_no_verdict_text |
| 204 | compute_health_state()'s returned dict carries a device_detail_html key holding the verdict-free fragment also embedded (once) inside device_html (D-17) | ported | companion/test_status_pages_05.py::test_compute_health_state_carries_device_detail_html |
| 205 | under lang='fr', relative_age_text(30) reads 'à l’instant' and relative_age_text(90000) reads 'il y a 1\u00a0j' (D-07) | ported | companion/test_status_pages_05.py::test_relative_age_text_french_seconds_bucket_reads_a_linstant |
| 206 | under lang='en' (the default), relative_age_text()'s English output is byte-for-byte unchanged — '30s ago'/'1d ago' (D-07) | ported | companion/test_status_pages_05.py::test_relative_age_text_english_unchanged_under_default_lang |
| 207 | local_clock_text() on a September timestamp reads 'sept.' under fr and 'Sep' under en, with an identical HH:MM in both (D-07) | ported | companion/test_status_pages_05.py::test_local_clock_text_french_month_abbreviation |
| 208 | relative_age_text()'s positional signature (age_seconds first) is untouched — lang is a trailing keyword only | ported | companion/test_status_pages_05.py::test_relative_age_text_first_positional_argument_is_age_seconds |
| 209 | layout.relative_time_html() renders a <time datetime=... data-relative> element whose own text EQUALS layout.relative_age_text()'s output for all four buckets in BOTH languages, and whose instant names the same moment that text describes (23-03, D14) | ported | companion/test_status_pages_05b.py::test_relative_time_html_wraps_the_one_ladder_in_both_languages |
| 210 | layout.relative_time_html() degrades to escaped plain text — never a raise, never a <time> element carrying an empty or invented instant — for a falsy, None, unparseable or mismatched timestamp (23-03) | ported | companion/test_status_pages_05b.py::test_relative_time_html_degrades_without_an_invented_instant |
| 211 | layout.relative_future_text() reads the SAME s/m/h/d bucket boundaries the past ladder reads (asserted at and around all three), is never negative, is never the past form, and clamps an already-elapsed instant to the zero bucket, in both languages (23-03) | ported | companion/test_status_pages_05b.py::test_future_form_shares_the_past_ladders_own_buckets |
| 212 | layout.relative_time_html() reads a FUTURE instant through the future form and a past one through the past form — one function, both directions, bounded and non-negative one second either side of now, in both languages (23-03, for 23-06's countdown) | ported | companion/test_status_pages_05b.py::test_relative_time_html_reads_a_future_instant_forwards |
| 213 | layout.concise_timestamp_html()'s parenthesised relative half is now a <time data-relative> element, its text unchanged, with its outer mono span, its title, its absolute-first ordering and its no-raw-ISO rule all untouched (23-03, D-09/D-05) | ported | companion/test_status_pages_05b.py::test_concise_timestamp_htmls_relative_half_is_now_an_element |
| 214 | health_page.render() under lang='fr' carries the French page title and at least three other French strings, and none of a short list of English source strings with distinct French forms (D-05) | ported | companion/test_status_pages_05b.py::test_health_page_renders_in_french |
| 215 | health_page.render() under lang='en' (the default) is byte-for-byte unchanged for a seeded state — pinned representative substrings (D-05) | ported | companion/test_status_pages_05b.py::test_health_page_renders_byte_identical_in_english |
| 216 | compute_health_state()'s device_html/device_detail_html/pipeline_html fields (and health_page.render()'s own page) fully localise their timestamps under lang='fr' — no English month abbreviation or ' ago' survives — proving the request-language ContextVar is resolved at the correct point relative to when this state is computed (Polish fix 2) | ported | companion/test_status_pages_05b.py::test_health_page_device_and_pipeline_timestamps_fully_localise_under_french |
| 217 | every key of companion/i18n_fr/health.py's own CATALOG is a non-empty str mapping to a non-empty str | ported | companion/test_status_pages_05b.py::test_health_catalog_every_key_and_value_is_a_nonempty_str |
| 218 | Airlines opens with the shared layout.page_header() component, not a bare <h1> | ported | companion/test_status_pages_05b.py::test_airlines_page_opens_with_shared_page_header |
| 219 | the gallery renders exactly one .airline-card per illustrations.target_airline_names() entry (36 against today's data) | ported | companion/test_status_pages_05b.py::test_gallery_renders_one_card_per_target_airline |
| 220 | every rendered card image source, with the route prefix stripped, is a member of illustrations.target_filenames() — every rendered URL provably passes the route's own membership test | ported | companion/test_status_pages_05b.py::test_every_card_image_source_passes_route_membership_test |
| 221 | the Air Caraïbes card renders exactly three chips (A330, A350-1000, ATR72) — the A350-1000 shape-slug-validation trap is not fallen into | ported | companion/test_status_pages_05b.py::test_air_caraibes_card_has_three_upper_cased_chips_including_a350_1000 |
| 222 | an airline with no variant entries (Air France) renders no .airline-card__chips container at all | ported | companion/test_status_pages_05b.py::test_primary_only_airline_renders_no_chips_container |
| 223 | variant_chip_label() upper-cases every alphanumeric type code verbatim and word-cases the Embraer/Beechcraft manufacturer forms | ported | companion/test_status_pages_05b.py::test_variant_chip_label_covers_both_domains |
| 224 | airlines_page.ILLUSTRATION_ROUTE_PREFIX equals app.ILLUSTRATION_IMAGE_ROUTE_PREFIX (the duplicated-not-imported route-prefix contract) | ported | companion/test_status_pages_05b.py::test_illustration_route_prefix_matches_app_constant |
| 225 | every rendered card image carries width/height attributes matching illustration_normalize.ILLUSTRATION_TARGET_WIDTH/HEIGHT exactly | ported | companion/test_status_pages_05b.py::test_every_card_image_carries_matching_intrinsic_dimensions |
| 226 | the gallery filter bar carries exactly one each of data-filter-input/-count/-clear/-empty | ported | companion/test_status_pages_05b.py::test_gallery_filter_bar_carries_all_four_contract_markers_exactly_once |
| 227 | the gallery filter bar's Clear control is a real <button type="button"> (D-16 retired) | ported | companion/test_status_pages_05b.py::test_gallery_filter_clear_control_is_a_real_button |
| 228 | the gallery filter label's for attribute equals the search input's id, and that id is the hyphen-free value quick task 260921-p2w Task 1 pins (superseding the now-stale 06.6.4.1-UI-SPEC.md §7.2 row) | ported | companion/test_status_pages_05b.py::test_gallery_filter_label_for_matches_input_id |
| 229 | Compagnies' gallery filter input and Health's registry filter input both carry autocomplete=off/spellcheck=false/autocapitalize=characters (Safari contact-autofill suppression) | ported | companion/test_status_pages_05b.py::test_compagnies_and_health_filter_inputs_carry_safari_autofill_suppression_attributes |
| 230 | every <input type="search"> this app can render, across companion/pages/*.py and companion/app.py (an ast-based source scan excluding docstrings, 3 occurrences found at plan time — history_page.py, airlines_page.py, health_page.py, one builder each), carries autocomplete=off/spellcheck=false/autocapitalize=characters — a fourth filter bar added later cannot reintroduce the Safari contact-autofill defect with nothing to catch it (quick task 260921-n2n Task 4) | ported | companion/test_status_pages_05b.py::test_every_rendered_search_input_carries_safari_autofill_suppression_attributes |
| 231 | no *_FILTER_INPUT_ID constant value and no hardcoded <input type="search"> id literal, across companion/pages/*.py and companion/app.py (enumerated from disk, 3 constants found at plan time, a >= 3 vacuity floor so deleting the constants cannot make this pass trivially), contains a hyphen — the documented WebKit/Safari trigger that offers the user's own Contacts phone numbers on a name-less type="search" field even with autocomplete="off" set (quick task 260921-p2w Task 2, closing the gap Task 1's three hand-fixed values left open) | ported | companion/test_status_pages_05b.py::test_no_filter_input_id_anywhere_in_the_app_contains_a_hyphen |
| 232 | the gallery filter bar's count text and empty-state body both name the real (36) card total | ported | companion/test_status_pages_05b.py::test_gallery_filter_count_and_empty_body_name_the_real_total |
| 233 | every card carries a data-filter-text equal to its own lower-cased airline name, and the set of data-filter-group values has the same size as the card count | ported | companion/test_status_pages_05b.py::test_every_card_carries_distinct_filter_text_and_group |
| 234 | companion/pages/airlines_page.py imports no history-database module and no sqlite module (D-17 non-goal: no detection-history cross-reference), and imports poll_loop exactly the way phase 13's D-11 membership test deliberately supersedes the OLDER half of that same non-goal | ported | companion/test_status_pages_05b.py::test_airlines_page_imports_no_history_db_or_sqlite_but_does_import_poll_loop |
| 235 | the rendered Airlines gallery contains none of the migrated unresolved-prefix registry or resolution-statistics table column headers (D-13 non-goal) | ported | companion/test_status_pages_05b.py::test_airlines_page_no_longer_renders_registry_or_stats_headers |
| 236 | the rendered Health page still contains both migrated header sets — the content moved, it was not lost | ported | companion/test_status_pages_05b.py::test_health_page_still_renders_both_migrated_header_sets |
| 237 | importing companion.pages.airlines_page raises no error, and the module exposes none of the deleted diagnostics symbols | ported | companion/test_status_pages_05b.py::test_airlines_page_module_exposes_no_deleted_diagnostics_symbol |
| 238 | every card wraps its image in exactly one .airline-card__zoom button whose data-view-panel-src is byte-identical to that same card's <img src>, whose data-view-panel-caption equals CARD_IMAGE_ALT_TEMPLATE %% name, and whose aria-label equals ZOOM_LABEL_TEMPLATE %% name | ported | companion/test_status_pages_05b.py::test_airline_card_zoom_button_attrs_match_expected |
| 239 | the shared lightbox dialog is emitted exactly once, carries both the lightbox and lightbox--wide classes plus all three lightbox__* elements and the close attribute, and its note element renders empty (LIGHTBOX_NOTE is deliberately '' after two rounds of live developer feedback rejected both the original and the reworded copy; the element still exists for panel-lookup.js's shared guard clause) — quick task 260902-tli | ported | companion/test_status_pages_05b.py::test_lightbox_dialog_renders_once_wide_with_own_note_text |
| 240 | .airline-card__zoom neutralizes the base button rule's height/padding/border/background and declares the zoom cursor, and declares no pointer-events property anywhere — the retired orientation gate (a misreading of the developer's original request, corrected on the same live test) must not silently return | ported | companion/test_status_pages_05b.py::test_airline_card_zoom_stylesheet_contract |
| 241 | the mobile-only button override exists as the file's @media (max-width: 959.98px) block, declares a bare `button` rule with height: 36px and font-size: 14px, sits AFTER the base `button` rule in source order (the mechanism that lets it win at equal specificity), and the base rule's own desktop values (height: 30px, font-size: 13px) are untouched (06.6.4.1.1-03 D-18b) | ported | companion/test_status_pages_05b.py::test_mobile_button_override_block_and_source_order |
| 242 | .lightbox--wide's max-width equals illustration_normalize.ILLUSTRATION_TARGET_WIDTH — a future change to the normalized frame size cannot silently leave the dialog capped at a stale width | ported | companion/test_status_pages_05b.py::test_lightbox_wide_max_width_matches_illustration_target_width |
| 243 | exactly one lightbox replace form is rendered, and every card's zoom trigger carries a data-view-panel-replace-action attribute (one per illustrations.target_airline_names() entry) whose value, with the route prefix stripped, is a member of illustrations.target_filenames() — mirroring the existing image-source membership check | ported | companion/test_status_pages_05b.py::test_replace_form_action_matches_trigger_attribute_membership |
| 244 | the single lightbox replace form declares method="post", enctype="multipart/form-data" — a missing enctype would silently send the file as a filename string, a real failure mode, not a formality — and a literally present action="" placeholder for panel-lookup.js to overwrite | ported | companion/test_status_pages_05b.py::test_replace_form_declares_post_multipart_enctype_and_present_action |
| 245 | the whole rendered page carries exactly one <input type="file"> whose id equals airlines_page.REPLACE_INPUT_ID and is the target of a label's for attribute, and both the label and the file input live inside the framed zone wrapper (quick task 260903-df3) — the accessibility contract the move from per-card to shared must not lose | ported | companion/test_status_pages_06.py::test_replace_form_file_input_id_is_unique_and_labelled |
| 246 | render() with no effective state_dir produces no cache-busting query string anywhere; with a state_dir whose override directory holds Air France's override file, exactly one URL is busted, keyed on that file's own mtime, identically in both the <img src> and the zoom trigger's data-view-panel-src, every other card's URL stays unbusted, and Air France's own data-view-panel-replace-action stays the UN-busted URL while no replace-action value anywhere carries a cache buster | ported | companion/test_status_pages_06.py::test_cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override |
| 247 | a hostile airline name reaching the rendered page is escaped, never interpolated raw, including in its own data-view-panel-replace-action attribute; the now-airline-agnostic replace form's own markup (REPLACE_LABEL_TEXT and REPLACE_HINT_TEXT, quick task 260903-df3) carries no trace of the hostile name at all (extends T-06.6.4.1-05's existing discipline) | ported | companion/test_status_pages_06.py::test_replace_control_escapes_hostile_airline_name |
| 248 | the lightbox replace form's own markup offers no restoring or resetting of the original image (D-04, explicitly out of scope) - checked both within the form's own markup and as a membership test over this feature's surviving copy constants (REPLACE_LABEL_TEXT/REPLACE_BUTTON_TEXT/REPLACE_HINT_TEXT) | ported | companion/test_status_pages_06.py::test_replace_form_contains_no_revert_or_reset_control |
| 249 | the retired per-card replace disclosure left no dead markup (a real render() call), no dead stylesheet rule (companion/static/style.css read from disk), and no dead module surface (_replace_control_html/REPLACE_SUMMARY_TEMPLATE/REPLACE_LABEL_TEMPLATE) behind | ported | companion/test_status_pages_06.py::test_replace_control_retired_from_every_surface |
| 250 | the framed zone's upload glyph comes from layout.ICON_DEFS_HTML via layout.icon_html() — 'icon-upload' is a member of ICON_IDS, the rendered page carries exactly one matching <use> reference, companion/pages/airlines_page.py's own source contains no hand-written glyph-element token, and REPLACE_ICON_CLASS appears in the rendered icon's class attribute | ported | companion/test_status_pages_06.py::test_replace_zone_icon_comes_from_the_shared_sprite |
| 251 | exactly one .lightbox__replace-zone <div> is rendered, nested inside the single lightbox replace form; within it, the icon, label, hint, file input and Upload button appear in that order; the hint element's text equals REPLACE_HINT_TEXT; and companion/static/style.css (read from disk) contains LIGHTBOX_REPLACE_ZONE_CLASS, REPLACE_HINT_CLASS, REPLACE_ICON_CLASS and a '::file-selector-button' rule | ported | companion/test_status_pages_06.py::test_replace_zone_markup_and_styling_contract |
| 252 | all three upload-form renderings (the no-JS fallback's, the dialog's copy, and the lightbox replace form) keep their <input type="file" ... accept="image/png" required>, their single bare <button type="submit">, their hint paragraph, their method/enctype/action and exactly one <form> byte-identical to their pre-25-07 output — each now also carrying its own id and, as the form's LAST child after the submit button, a drop zone naming the very input it writes into (CFG-51/D19, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_upload_forms_native_controls_are_unchanged_by_the_drop_zone |
| 253 | on a Step-B edit-mode Airlines render (the fallback panel's upload form, the dialog's copy and the replace form all at once) every emitted id is document-unique, every one of the three elements carrying data-upload-drop also carries layout.JS_GATE_CLASS ON ITSELF (boundary-anchored, so data-upload-drop-input cannot satisfy it), and with those three <section> subtrees excised the rest of the document contains zero preview, image, note, message, input-hook or --upload-preview-ratio markup (CFG-51/D-09, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_drop_zone_ids_are_unique_and_no_drop_markup_escapes_the_js_gate |
| 254 | the framing preview reserves companion/illustration_normalize.py's OWN output frame (read from ILLUSTRATION_TARGET_SIZE, never a retyped ratio) through an inline --upload-preview-ratio that style.css reads with NO fallback value; every .upload-drop class and the [data-upload-drop-active] state resolve to real selectors on a selector boundary; and not one .upload-drop rule uses :hover, declares a colour literal or introduces animation (CFG-51/CFG-52, 25-07-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_preview_box_reserves_illustration_normalize_s_own_frame |
| 255 | _gap_rows_for_grid() thresholds at >= GAP_BLOCK_THRESHOLD (3), sorts eligible rows (-count, prefix), caps at GAP_BLOCK_CAP (12), and reports the exact overflow count for the rest (D-05/D-06) | ported | companion/test_status_pages_06.py::test_gap_block_threshold_sort_cap_and_overflow |
| 256 | _gap_card_html() renders the whole card as a real <a class="airline-card" href="/airlines?resolve={prefix}"> trigger with zero <img> tags and no nested .airline-card__zoom button, carrying every data-view-panel-* attribute UI-SPEC's Gap-card markup shape names, non-empty where that snippet shows a value (D-01/D-02/D-12) | ported | companion/test_status_pages_06.py::test_gap_card_markup_shape_and_attribute_vocabulary |
| 257 | a gap card's data-filter-group value is always a string-prefixed "gap{index}" (never a bare integer) and never collides, as a bare string, with any curated card's own data-filter-group value on the same render (RESEARCH.md Pitfall 4, T-14-17) | ported | companion/test_status_pages_06.py::test_gap_card_filter_group_never_collides_with_curated_integer_groups |
| 258 | _gap_overflow_html() returns the empty string when the cap does not bite, and otherwise the exact templated line naming the overflow count, with <a href="/health"> wrapping only MANUAL_OVERFLOW_LINK_TEXT and the trailing period sitting outside the anchor (D-07) | ported | companion/test_status_pages_06.py::test_gap_overflow_html_renders_only_when_the_cap_bites |
| 259 | an example_callsign containing '<', '>', '&' and '"' reaching a gap card renders fully escaped, both in data-view-panel-caption and in the visible callsign paragraph, exactly once per interpolation site (T-06.6.4.1-05, T-14-16) | ported | companion/test_status_pages_06.py::test_gap_card_escapes_hostile_example_callsign |
| 260 | _airline_card_html(index, airline_name, shapes, state_dir, manual_info=None) renders byte-identically to the default-omitted call, and a plain curated card with no manual history still wraps a real <button> (never an <a>), with mode="art" and every manual/resolve-prefix attribute empty (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_manual_info_none_matches_todays_plain_card_and_keeps_button |
| 261 | an active manual_info triple renders the real <a href> trigger, the correct mode/heading/upload-action for both the has-artwork and needs-artwork cases, the delete-action attribute from _manual_delete_action(), an empty manual-note, and the 'Resolved by hand' chip (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_active_manual_states_render_expected_attributes_and_chip |
| 262 | a needs-artwork manual card's first-seen/last-seen/count attributes are populated from unresolved_row_for_prefix() only when a live gap still exists for that prefix, fall back to empty once D-14 clears it, and stay empty on an art-mode card regardless of manual_info (14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_needs_artwork_sighting_context_conditional_on_live_gap |
| 263 | a superseded card never shows the operator's own orphaned upload: data-view-panel-src points at the built-in Air France illustration key (never a key derived from the entry's own stored name), the Superseded chip renders, and the manual-note interpolates the prefix, the built-in name, AND the operator's own originally-stored name (not the built-in name a second time) (D-10, 14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_airline_card_html_superseded_shows_built_in_state_never_operator_upload |
| 264 | render()'s grid-injection step adds exactly one card for a genuinely novel active manual airline name not already among the curated pairs, and adds none for a superseded entry or for an active entry whose name is already curated (D-08, UI-SPEC's Grid injection, 14-06-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_render_grid_injection_adds_exactly_one_novel_card_and_none_for_superseded_or_curated |
| 265 | the resolve section renders all four server-derived states and only the right controls in each: absent-from-registry (stale sentence, no form at all), seeded-gap-no-entry (Step A heading, name input, no file input), seeded-gap-with-artless-entry (Step B heading naming the stored airline, upload form action ending /{key}.png, a file input), and seeded-gap-with-resolved-entry (the already-resolved sentence, no file input) — D-03/D-11 | ported | companion/test_status_pages_06.py::test_resolve_section_four_states_render_correctly |
| 266 | Step A's rendered datalist carries exactly len(illustrations.target_airline_names()) (36 against today's data) <option> elements, the datalist's id matches the name input's list attribute, every airline name appears as an escaped <option value=...> exactly once (D-13), and the shared _resolve_name_form_html() output also carries an empty <p class="lightbox__resolve-scope"></p> for panel-lookup.js to write into on open (14-06-PLAN.md external gap-closure) | ported | companion/test_status_pages_06.py::test_resolve_section_datalist_contract |
| 267 | a stored airline name and example callsign both containing an angle bracket, a double quote and an ampersand render fully escaped everywhere they appear (including inside an attribute value), and a resolve_prefix differing from the stored registry key only in case or surrounding whitespace normalises to the identical prefix and renders the identical resolve section (WR-04/D-12) | ported | companion/test_status_pages_06.py::test_resolve_section_escapes_hostile_values_and_distrusts_query_string |
| 268 | CR-02: once D-14 clears a resolved prefix from the live gap registry, the resolve section still reaches Step B for a manual entry with no artwork yet (heading, file input, Skip link, no sighting-context <dl>), still reaches the already-resolved state once artwork exists under the re-added name (D-07's delete-and-re-add path), and still renders the stale sentence only once neither a live gap nor a manual entry exists for the prefix | ported | companion/test_status_pages_06.py::test_resolve_section_step_b_reachable_after_gap_cleared |
| 269 | the page's own top-to-bottom order is filter-bar, then illustration-grid, then the shared dialog's opening tag, then its closing tag, then (last) the resolve section's own back-link text — proving UI-SPEC's new page composition (resolve section moved to the bottom, behind the shared dialog) shipped for real | ported | companion/test_status_pages_06.py::test_page_composition_order_matches_ui_spec |
| 270 | with an empty manual-resolutions registry, render() emits no .manual-summary element and none of the retired management table's own copy; with two entries seeded (one superseded, one active), .manual-summary renders exactly once with text matching MANUAL_SUMMARY_TEMPLATE's total/superseded count (D-11, 14-06-PLAN.md Task 2 item 1) | ported | companion/test_status_pages_06.py::test_manual_summary_line_replaces_retired_management_table_copy |
| 271 | the retired D-06 supersession machinery's own symbols (SUPERSEDED_MARKER_TITLE, SUPERSEDED_CAPTION, SUPERSEDED_STATUS_CLASS) are gone, and the Superseded chip itself still renders end to end via render() — the card-level attribute/note contract is Task 1's own check's job, not re-tested here (14-06-PLAN.md Task 2 item 2) | ported | companion/test_status_pages_06.py::test_manual_section_supersession_symbols_retired_and_chip_still_renders |
| 272 | importing companion.pages.airlines_page raises no error, and the module exposes none of the six retired management-table rendering functions or eight now-orphaned copy/class constants (14-06-PLAN.md Task 2 item 3) | ported | companion/test_status_pages_06.py::test_retired_management_table_symbols_are_gone |
| 273 | _seed_manual_resolutions() seeds through manual_resolutions.add_entry() alone; both seeded airline names render on the Airlines page, and _manual_resolution_rows() reports superseded=True for exactly the static-table prefix (AFR) and False for the novel one (XQZ) (phase 14 plan 14-01 Task 3) | ported | companion/test_status_pages_06.py::test_manual_section_seed_helper_end_to_end |
| 274 | health_page.RESOLVE_LINK_HREF_TEMPLATE equals the template derived from airlines_page.AIRLINES_ROUTE and airlines_page.RESOLVE_QUERY_PARAM — the cross-module equality check airlines_page.py's own comment already claims exists (WR-06) | ported | companion/test_status_pages_06.py::test_health_resolve_link_template_matches_airlines_route_constants |
| 275 | the D-09 amendment's permanent regression proof: rendering ?resolve={prefix} for a prefix with a manual entry produces exactly one _manual_delete_form_html() output inside the shared dialog (action="") and exactly one inside the no-JS fallback section (the real delete action) — one shared function, two call sites (14-06-PLAN.md Task 2 item 4) | ported | companion/test_status_pages_06.py::test_manual_delete_form_renders_in_both_dialog_and_no_js_fallback |
| 276 | companion/static/list-filter.js gains an optional, guarded [data-filter-set] lookup whose click handler sets the filter input's value from the clicked element's own attribute and calls the file's one existing applyFilter() — the file still has exactly one [data-filter-text] query, stays ES5-safe, and introduces no network call or timer (phase 14 plan 14-03 Task 1, RESEARCH.md Pitfall 5, D-11's summary-line mechanism) | ported | companion/test_status_pages_06.py::test_list_filter_js_gains_data_filter_set_hook |
| 277 | style.css declares the new/extended selectors UI-SPEC's Component Inventory enumerates (a.airline-card, .airline-card__placeholder, .lightbox__heading:empty, .lightbox__manual-note:empty) with their exact declaration values, .manual-summary's own base rule is GONE with only its hover surviving on the chip's own 12% wash (X7, 22-11-PLAN.md Task 2 — the copied [data-filter-clear] property list is replaced by reuse of .airline-card__chip, whose label-voice declarations are pinned here instead), .airline-card__placeholder's aspect-ratio string-equals .airline-card__image's, .lightbox__replace's selector is extended to a three-way group with .lightbox__resolve-name/.lightbox__delete in exactly one declaration block (never duplicated), the header accent-reservation list mentions none of the new selectors, none of the new/extended rule bodies declares a new custom property, and .manual-resolution__status--superseded is gone now that plan 14-06 has retired it (phase 14 plan 14-03 Task 2, retargeted in place by 14-06 Task 2) | ported | companion/test_status_pages_06.py::test_phase14_task2_new_css_selectors_exhaustive |
| 278 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris): the Frame strip renders the held copy with the neutral dot--off and zero warn/error tokens anywhere, including no 'Expected since'/'Attendu depuis' (X2, D-03/CFG-26) | ported | companion/test_status_pages_06.py::test_frame_strip_nightly_regression_held_is_neutral_never_warn |
| 279 | a due result renders byte-identical copy and classes whether 'now' is before next_wake or up to 2x the effective interval past it — the grace window is invisible (22-UI-SPEC.md §3.3 rule 3) — with the countdown present in both renderings, marked, pointed at the same instant, and neither rendering carrying a warn/late/overdue token anywhere (retargeted in place by 23-06-PLAN.md Task 2, which added the one element in that cell that is a function of `now` by construction) | ported | companion/test_status_pages_06.py::test_frame_strip_due_is_identical_inside_and_outside_the_grace_window |
| 280 | a late result renders the warn dot and 'Expected since HH:MM', with the headline's own text-colour class staying the plain status-card__headline--warn hook (never a status colour as text, 22-UI-SPEC.md §3.3 rule 2) | ported | companion/test_status_pages_06.py::test_frame_strip_late_result_carries_warn_dot_and_plain_text_colour_class |
| 281 | with a parked frame (ctx['battery_critical']=True), wake_interval_s 300 and a 20-minute-old check-in, the frame strip does NOT show the late state - the identical setup without the park does (quick task 260923-fr4) | ported | companion/test_status_pages_06.py::test_frame_strip_parked_suppresses_late_state |
| 282 | the Frame strip renders no update headline and claims no state when there is no check-in recorded at all (frame_state.STATE_UNKNOWN) | ported | companion/test_status_pages_06.py::test_frame_strip_no_checkin_renders_no_update_cell_and_claims_no_state |
| 283 | all three Frame-strip cells share one wrapper and one three-row internal grid (identical row-class lists), while only the two switch cells' outer wrapper keeps the quick-action--on/off control-state left edge (B13) | ported | companion/test_status_pages_06.py::test_frame_strip_three_cells_share_one_row_structure_switch_cells_keep_left_edge |
| 284 | a rendered Frame strip contains exactly 2 occurrences of the literal attribute data-quick-switch, one on each strip switch form (D-04 handshake with plan 22-05) | ported | companion/test_status_pages_06.py::test_frame_strip_both_switch_forms_carry_data_quick_switch_exactly_twice |
| 285 | companion/layout.py no longer computes an age_seconds(next_wake...) >= 0 warn trigger — the strip consumes frame_state.resolve_state(), it never re-derives lateness (CFG-26) | deleted | S: asserted source text (companion/layout.py grepped for a retired age_seconds(next_wake...) re-derivation); redundant with the frame-strip behaviour checks in this module (rows 278-284), which already prove every late/due/parked/grace-window scenario against frame_state.resolve_state()'s own output |
| 286 | the .frame-strip__cells block declares align-items: stretch and zero align-items: center (B13) — a block-scoped check, since a line-wise grep pipe would already read 0 on the unmodified file (the selector and declaration sit on different lines) and pass vacuously | ported | companion/test_status_pages_06.py::test_frame_strip_cells_stretch_not_center |
| 287 | the .frame-strip__cell button quiet-button rule (C2) appears at a later line than button[type="submit"], carries no !important and no id selector, and reuses the base quiet wash (4.5%/9%) verbatim — never a new wash value (T-22-13) | ported | companion/test_status_pages_06.py::test_frame_strip_cell_button_quiet_rule_after_submit_no_important_no_id |
| 288 | the .stat-tile hover/focus-within block declares zero border-color: transparent and both border-inline-color and border-block-end-color (T9: the top status/accent rail survives hover), and the whole reveal is :not(.frame-strip)-scoped so the strip never lifts | ported | companion/test_status_pages_06.py::test_stat_tile_hover_three_edge_frame_strip_excluded |
| 289 | the Phase 21 .frame-strip__cell--update .status-card__headline heading-size override is gone — the line returns to its own 16px semibold Emphasis base (C6) | ported | companion/test_status_pages_06.py::test_frame_strip_update_headline_no_heading_size_override |
| 290 | the one .time-value role (C5) declares --font-ui and tabular-nums, with a --primary modifier stepping up to body-size + semibold — no new token, no new family, no new size | ported | companion/test_status_pages_06.py::test_time_value_role_defined_once |
| 291 | the style.css header comment's accent-reservation list is edited to record C2's delta (the Frame strip's two switch buttons are no longer accent-filled) — the arithmetic is written into the comment, not merely asserted (22-UI-SPEC.md §1) | deleted | C: asserted a stylesheet comment (the header's own accent-reservation-list prose recording the C2 delta); no rendered behaviour |
| 292 | the tab bar is display:none until the 959.98px boundary, then fixed to the viewport bottom at 56px plus the safe-area inset on the nav surface with a top hairline, the resting overlay shadow and NO border radius (it is edge-anchored); its cells are `flex: 1 1 0`; its active state reuses the app's one 12%-accent-wash pill idiom byte-for-byte with a :not()-scoped hover placed after it; its label is 11px regular with no label voice; and .has-tab-bar clears the bar at the page foot (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_06.py::test_tab_bar_css_geometry_surface_and_active_idiom |
| 293 | the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured 6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82, 29-02-PLAN.md) | ported | companion/test_status_pages_07.py::test_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit |
| 294 | the More sheet opens upward from the fixed bar (absolute, bottom: 100%, right: 0) on the nav surface with the overlay shadow, reuses .mobile-nav__link's 44px/16px geometry rather than restating it, leaves .mobile-nav's in-flow flex-basis push-down untouched, and the stylesheet itself records why this absolute positioning is not a reversal of the rejected-overlay verdict (X9/D-10, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_tab_bar_more_sheet_opens_upward_and_reuses_the_dropdown_row |
| 295 | under lang='fr' every tab-bar label reads French — Accueil / Affichage / Vols / Compagnies / Plus, with État and Appareil inside the More sheet — and the landmark name is 'Navigation principale' (B16/CFG-29, 22-14-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_french_tab_bar_labels_and_landmark |
| 296 | the nav state reminder renders as a <span> with no href on Home, announcing ONLY the state, and stays an <a href="/" > with its destination-naming label everywhere else — in both nav copies, each with its two nowrap segments (B10/D-04, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_nav_status_is_a_span_on_home_and_a_link_everywhere_else |
| 297 | exactly ONE open-state max-height governs the dropdown (320px, pinned against a measured 165px of reduced French content at 390px — both the 420px and 640px values are gone, not re-tuned), the dropdown's dead nav selectors are deleted while .mobile-nav__link survives for the tab bar's sheet, and .nav-status is a wrapping flex row of nowrap segments whose hover underline is anchor-scoped (T11/B10, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule |
| 298 | companion/static/style.css carries zero stray comment terminators and ends outside a comment — the structural guard for a real parse-error class that drops whole rules while leaving the source text a string-comparison harness reads as correct (22-14-PLAN.md Task 2, Rule 1) | ported | companion/test_status_pages_07.py::test_style_css_carries_no_stray_comment_terminator |
| 299 | every <details> carries an explicit summary::before chevron that rotates on [open] through a child combinator — including the bottom tab bar's More summary, where it is taken out of flow so a marker cannot narrow the cell, and with its own inverted rotation because that sheet opens upward — with the prefers-reduced-motion block count unchanged at two; and no .data-table-wrap th rule survives to claim sticky positioning a wrapper with no height could never provide (T3/T4, 22-15-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_every_disclosure_has_a_marker_and_no_header_claims_to_stick |
| 300 | freshness.js no longer stops dead on a failure: stopLoop() survives only as its definition and its two deliberate background-tab teardowns, a bounded exponential ladder starting AT the normal cadence (so a failing server sees a strictly decreasing rate) replaces it, a success resets the backoff, an in-flight guard stops two fetches racing, the swap skips unchanged regions and any region holding focus, the state badge is .banner__pill with the NEUTRAL .dot--off and no warn token anywhere in the file, style.css carries the .banner__pill[hidden] display guard the badge depends on, and both strings render onto <body> in both languages matching the script's own English fallbacks byte for byte (T13, 22-15-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_refresh_loop_retries_with_backoff_and_says_so_neutrally |
| 301 | style.css declares .resolve-context[hidden] { display: none; } after the base rule — without it, an author display declaration beats the UA [hidden] rule and every ordinary illustration's resolve-context block renders empty instead of hidden (quick task 260921-n2n Task 2) | ported | companion/test_status_pages_07.py::test_resolve_context_hidden_guard_present_after_base_rule |
| 302 | style.css's .flight-detail-row__grid margin-bottom is at least 2x .copy-btn::before's own inset magnitude — CFG-70's measured 22px hit-target floor made executable rather than a comment; this is the check that would have failed had this quick task's own source data's 'reduce to var(--space-md)' suggestion been taken (quick task 260921-n2n Task 5) | ported | companion/test_status_pages_07.py::test_flight_detail_row_grid_margin_never_shrinks_below_cfg70_floor |
| 303 | the hamburger toggle's accessible name describes the preferences panel it now opens ("Account and preferences" / "Compte et préférences"), and the retired "Open menu" translation is deleted rather than orphaned (X9/D-10/B16, 22-14-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_nav_toggle_label_now_describes_the_preferences_panel |
| 304 | the save bar's own sub-960px geometry and its z-index: 30 at both breakpoints are RESTORED — the .dirty-ready marker class is not (this restoration's own clearance mechanism is :has(.dirty-bar), which works with scripts blocked) — while the tab bar's own stacking value (20) and its own content clearance are unmoved (D-10/T7, 22-14-PLAN.md Task 3; retired by 27-04-PLAN.md/CFG-63, restored by 28-08-PLAN.md Task 3/CFG-77/CFG-78) | ported | companion/test_status_pages_07.py::test_save_bar_geometry_is_restored_and_the_tab_bar_stacking_survives |
| 305 | the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris), pinned as ONE named check: the strip renders the held copy with the neutral dot, Health's Frame tile renders the SAME clock time, the nav notification dot is unlit, and the rendered Health HTML carries zero warn/error dots, zero warn tile/headline modifiers and neither 'Expected since' nor 'Attendu depuis' (X2, D-03/CFG-26) | ported | companion/test_status_pages_07.py::test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn |
| 306 | inside the grace window with no hold, the tile reports the normal ('ok') state and the strip reports the due copy — they agree (22-UI-SPEC.md §3.3 rule 3) | ported | companion/test_status_pages_07.py::test_health_inside_grace_window_tile_and_strip_agree_normal |
| 307 | past the grace window with no hold, both the tile ('warn') and the strip ('Expected since') report late, and the nav notification dot lights | ported | companion/test_status_pages_07.py::test_health_past_grace_window_both_report_late_dot_lights |
| 308 | a frame whose (non-held) next wake has passed and whose own grace has since elapsed is reported late by both the tile and the strip — held cannot suppress lateness forever | ported | companion/test_status_pages_07.py::test_health_held_window_ended_and_grace_elapsed_both_report_late |
| 309 | companion/static/style.css's own dot--* class-name occurrence count is unchanged by this plan (9 before, 9 after) — this plan adds no dot class | ported | companion/test_status_pages_07.py::test_dot_modifier_classes_are_exactly_four_no_new_class_added |
| 310 | the quiet cell's caption link is present on BOTH Home's and Display's own real render() output, with the IDENTICAL href on both — asserted as one check whose failure names the page missing the link or the two hrefs when they differ, never two separate per-page checks (CFG-69, D-23, 27-08-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_the_quiet_schedule_link_is_one_write_site_reaching_both_pages |
| 311 | layout.frame_strip_html() renders exactly two role=switch controls whose aria-checked is the SAVED value in both directions, named by the setting through aria-labelledby and described by the state span, over the unchanged <form>/state/return_to/data-quick-switch the server already acts on — with the retired action wording gone, both state wordings present with exactly one hidden, and one pending-marker region per switch (D2/CFG-36, X1/D-04, 23-07-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_the_strip_renders_two_server_rendered_switches |
| 312 | the optimistic switch's failure copy is the app's own generic flash sentence, translated on <body> in both languages and carrying no status code, URL or server internal, and the shell renders exactly one EMPTY assertive live region for it — a transient toast, never a permanent banner (D2/CFG-36, V7/T-23-27, 23-07-PLAN.md Task 1) | ported | companion/test_status_pages_07.py::test_the_failure_toast_is_transient_translated_and_carries_no_internal |
| 313 | Health's freshness line carries exactly one neutral, aria-hidden live dot — the app's own off dot with no status or accent token and no breathing class at render time, because the motion belongs to the loop that knows whether it is listening (D22, 23-05-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_health_freshness_line_carries_a_neutral_live_dot |
| 314 | Health's freshness line is a <time data-relative> over the same instant data-loaded-at carries whose SERVER text is the clock — never the ladder's zero bucket, which is the frozen age A-20 removed — with the absolute timestamp still in the element's tooltip, exactly one data-loaded-at and one data-refresh-pill page-wide, and the wrapper still a swap target (D22's remainder, 23-05-PLAN.md Task 2; the no-JS half retargeted in place by 23-06-PLAN.md) | ported | companion/test_status_pages_07.py::test_health_freshness_clock_is_a_ticking_age_over_the_loaded_at_instant |
| 315 | freshness.js DERIVES the breathing class from its own interval handle and state badge in one function, called from exactly the four places its state already changes, carries no status vocabulary, leaves 22-15's retry ladder/ceiling/in-flight guard/targeted swap untouched, and agrees with both the Python hook and the CSS rule (T-23-15, 23-05-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_freshness_js_breathes_only_from_the_loops_own_state |
| 316 | GET /health, GET /airlines and GET /history all return 200 with their own page heading against a real running service, /health's real HTTP response body carries the page purpose, both section descriptions, no duplicated freshness label, the auto-refresh pill (hidden) and zero stale-banner markers, the nested modifier twice, the prose modifier once, both readout spans, no raw ISO in the readout's own slice, and the desc-class cells at their expected count after the Resolution-statistics heading, /airlines' real HTTP response body carries zero occurrences of the retired per-card replace class, exactly one lightbox replace form and one action="" and one file input, and at least one un-busted replace-action trigger attribute, /history's real HTTP response body carries zero occurrences of the replace-form class, replace-action attribute, enctype or file input (quick task 260903-btu Task 5a), and the real served stylesheet (STYLE_ROUTE) carries the description-column rule, the demotion rule's new bottom margin and the prose rhythm rule's selector, and the real served freshness script (FRESHNESS_SCRIPT_ROUTE) carries the interval constant, the visibility-change listener, the [data-loaded-at]/[data-refresh-pill] attribute hooks, carries zero occurrences of the deleted data-pause-text/wireToggle pause-branch hooks (D-18), and every health_page.REFRESH_SWAP_SELECTORS entry verbatim (quick task 260901-tsa; extended in place by quick task 260901-uzi finding 1/2/3/4, quick task 260902-bl2 Task 3, quick task 260902-chc, quick task 260903-btu Task 5a, 19-09-PLAN.md Task 3, and 21-02-PLAN.md Task 2) | ported | companion/test_status_pages_07.py::test_both_tabs_ok_end_to_end |
| 317 | GET /illustration/{key}.png against a real running service serves normalized bytes that differ from the raw vendored file and decode to illustration_normalize.ILLUSTRATION_TARGET_SIZE, and an unknown key still 404s | ported | companion/test_status_pages_07.py::test_illustration_route_serves_normalized_bytes_end_to_end |


### Part 01 (plan 33-25)

Rows 1-37 (part 01, original `check()` calls #1-#37) plus one out-of-order
row (151, `anomaly_active()`'s root-unsafe degrade-safely check, pulled forward
per 33-MIGRATION-RULES.md rubric T) are `ported` to
`companion/test_status_pages_01.py`.

Rubric codes: 34 B/D (calls `companion.pages.health_page`/`companion.wake`/
`companion.layout` directly and asserts on the return value or the rendered
HTML — battery ring/chart/hit-target checks parse the SVG structurally via
`companion_markup.parse_html()` instead of regex over the raw string), 1 S
(row 7, `companion/wake.py`'s import boundary — rewritten as a `child_env()`
subprocess `sys.modules` probe instead of a source grep), 1 T (row 151, the
pulled-forward `anomaly_active()` check — every "missing state_dir" input now
uses a `tmp_path` subpath instead of a fixed absolute path outside the repo
production code could create as root, closing T-33-25-01 and the status-pages
half of 32-REVIEW.md IN-05). No deletions in this slice.

New module: `companion/test_status_pages_01.py` (38 tests: 37 ported part-01
checks plus the 1 pulled-forward `anomaly_active()` check).
`companion/test_status_pages_helpers.py` is new too (seeding helpers this
part barely uses beyond `seed_device_health`/`seed_meta`/`seed_runway_events`
and `stat_tile_slices` — front-loaded for 33-26..33-31's later sections, same
precedent as 33-14's `test_companion_app_helpers.py`).

### Part 02 (plan 33-26)

Rows 38-85 (part 02, original `check()` calls #38-#85) are `ported` to
`companion/test_status_pages_02.py`.

Rubric codes: 44 B/D (calls `companion.pages.health_page`/`companion.draw`/
`companion.wake`/`companion.layout` directly and asserts on the return value
or the rendered SVG/HTML, in the legacy harness's own substring/regex style
per 33-25's precedent), 3 C (rows 43, 44, 46 — `.battery-trend-section
svg:not(.icon)`, `.sparkline-area`/`.sparkline__area` and
`.sparkline-threshold`/`.sparkline-swatch` raw `style.css` reads, rewritten
against a served stylesheet via `companion_markup.declarations_for()`/
`rules_with_selector()`/`css_rules()`), 1 J (row 70, `battery-trend.js`'s raw
disk read, rewritten as a `served_asset()` fetch). No deletions in this
slice; two partial S-rubric trims inside otherwise-ported checks (not
counted as separate rows — the check's remaining assertions are still
`ported`):

- Row 46 dropped `open(health_page.__file__).read()`'s "the millivolt
  threshold is never re-typed into health_page.py's own source" assertion
  (no observable rendered consequence — the check's remaining assertions,
  that the threshold's VALUE and placement come from `companion/battery.py`,
  are unaffected).
- Row 55 dropped `inspect.getsource(fn)`'s sweep for forbidden interval-
  arithmetic tokens (banned outright by `test_suite_guards.py`'s G2 rule,
  same precedent as 33-25's `_battery_section()` arity fix; the check's own
  `fn.__code__.co_names` reuse sweep, not a source-text read, is kept).

Seven old checks (rows 58, 73, 74, 75, 77, 78, 81) each contained a
per-case/per-severity loop and became `@pytest.mark.parametrize` tests per
this plan's own Task 1 instruction; the ledger row for each points at its
PRIMARY parametrized node id, with the sibling ids listed in the plan's
SUMMARY (33-MIGRATION-RULES.md section 3, "one old check splits into
several tests"):

- Row 58: primary `test_check_in_disclosure_moved_clauses_render_across_all_four_cases[observed, cadence known]`; siblings `[observed, cadence unknown]`, `[not observed, cadence known]`, `[not observed, cadence unknown]`.
- Row 73: primary `test_device_tile_verdict_matches_state_at_each_severity[ok]`; siblings `[warn]`, `[error]`.
- Row 74: primary `test_pipeline_tile_verdict_matches_state_at_each_severity[ok]`; siblings `[warn]`, `[error]`.
- Row 75: primary `test_corroboration_tile_verdict_matches_disagreement_state[agree]`; sibling `[disagree]`.
- Row 77: primary `test_one_tile_anatomy_across_every_health_tile[seeded]`; sibling `[fresh]`.
- Row 78: primary `test_only_one_saw_it_is_neutral_and_still_distinct[en-Both agree-Only one saw it]`; sibling `[fr-Les deux concordent-Une seule l'a vu]`.
- Row 81: primary `test_resolution_detail_line_has_a_singular_form[total=1-en]`; siblings `[total=1-fr]`, `[total=2-en]`, `[total=2-fr]`, plus the trailing French-catalogue-entry assertion split into its own
  `test_resolution_detail_templates_have_french_catalogue_entries`.

New module: `companion/test_status_pages_02.py` (62 pytest node ids
covering the 48 baseline rows in this slice: 41 rows ported 1:1 to a single
node id, 7 rows ported to a parametrized test totalling 20 node ids across
them, plus 1 extra split-off test — 41 + 20 + 1 = 62). A `_module_server`/
`css_text`/`battery_trend_js` module-scoped read-only server fixture set is
new in this module, for the 3 C/J-rubric checks above — no test in this
part mutates server state, so a shared read-only server is safe
(33-MIGRATION-RULES.md section 2).

### Part 03 (plan 33-27)

Rows 86-139 (part 03, original `check()` calls #86-#139) are `ported` to
`companion/test_status_pages_03.py`.

Rubric codes: 43 B/D (calls `companion.pages.health_page`/`companion.layout`/
`companion.i18n`/`companion.prefs`/`companion.wake` directly and asserts on
the return value or the rendered HTML, in the legacy harness's own
substring/regex-over-rendered-markup style per 33-25/33-26 precedent), 9 C
(rows 122, 130, 131, 132, 134, 135, 136, 137, 138 — the `.section-caption`/
`BATTERY_SECTION_CLASS`/doubled-form-status/hover-source-order/`.section-
intro`+`.stat-tile__value .mono`+`.battery-readout`/`.dashboard-grid`/
`.data-table th`/nested-heading-tier/`.stat-tile__caption` raw `style.css`
reads, all rewritten against the served stylesheet via
`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`/
`custom_properties()` — never a regex/substring probe over the served text,
per 33-FOLLOWUPS.md F-01), 1 J (row 92, `battery-trend.js`'s raw disk read,
rewritten as a `served_asset()` fetch), 1 S (row 105, the `health_page.py`
"never imports the stdlib html module" grep, rewritten as `not hasattr(
health_page, "html")` — a bare `import html` binds the name directly into
the module's own namespace, so this is a real behavioural proof).

One `deleted`-free but fully rewritten S-rubric row, and the plan's own
named hotspot: row 121 (the legacy "companion/pages/health_page.py still
contains zero HTML form elements and exactly one '<button' literal" check)
read `health_page.py`'s own source text, where the "one `<button`" was a
docstring mention, never rendered markup. `ported`, not `deleted`, because
the check DOES have observable rendered consequences — rewritten as
`test_health_still_has_no_form_and_no_button_in_any_state`, parametrized
over four seeded Health render states (`normal`, `anomaly`, `source_fault`,
`empty`): each is rendered, parsed with `companion_markup.parse_html()`,
and asserted to contain zero `<form>` and zero `<button>` elements —
`health_page.render()` returns a content fragment only, with no shared nav
chrome, so the true rendered contract carries none of the legacy check's
"exactly one" exception at all. Per 33-MIGRATION-RULES.md section 3 ("one
old check splits into several tests"), the ledger row points at the primary
parametrized node id, with the sibling ids listed here:

- Row 121: primary `test_health_still_has_no_form_and_no_button_in_any_state[normal]`; siblings `[anomaly]`, `[empty]`, `[source_fault]`.

New module additions: `companion/test_status_pages_03.py` extends part 02's
module-split convention with 57 pytest node ids covering the 54 baseline
rows in this slice (53 rows ported 1:1 to a single node id, 1 row ported to
a 4-case parametrized test — 53 + 4 = 57). Reuses part 02's exact
`_module_server`/`css_text`/`battery_trend_js` module-scoped read-only
server fixtures (no test in this part mutates server state either) — no new
fixture family was needed for this slice's 9 CSS checks.

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 231` to `EXPECTED_CHECK_COUNT = 177` (231 - 54);
part 03's 54 checks and their own closures are removed from `main()`.
`_battery_section_heading()`/`_tile_slice_by_caption()`/`_stat_tile_slices()`
(module-scope helpers this part used, alongside still-pending later
sections) are left in place — `_battery_section_heading()` is still called
by pending rows well past this slice's boundary (confirmed live: the
shrunk harness runs 177/177 green standalone).

### Part 04 (plan 33-28)

Rows 140-171 (part 04, original `check()` calls #140-#171, minus row 151
which 33-25 already pulled forward) are `ported` to
`companion/test_status_pages_04.py`, except row 154 which is `deleted`.

Rubric codes: 20 B/D (rows 140-141 partial structural halves aside, mostly
calls `companion.pages.health_page`/`companion.layout`/`companion.i18n_fr.
health` directly and asserts on the return value or the rendered HTML, in
the legacy harness's own substring/regex-over-rendered-markup style per
33-25/33-26/33-27 precedent), 9 C (rows 140 partial, 141 partial, 142
partial, 144, 146 partial, 149, 157, 161 partial, 162, 163, 164 partial —
the nested-card heading/prose rhythm rules, the `data-table--prose`/
`.data-table td.desc` pair, the `.data-cards` toggle contract, the
`.data-table--registry` stacked-cell selectors, `.mono`/`.battery-readout__
detail`, the `.refresh-pill` family, the UIR-03/07/12/13 rule set, the
`.dashboard-grid`/`.battery-trend-section` spacing pair, the desktop-
padding/mobile-density pair, and the bare `summary` rule — all rewritten
against the served stylesheet via `companion_markup.css_rules()`/
`declarations_for()`/`rules_with_selector()`, never a regex/substring probe
over the served text, per 33-FOLLOWUPS.md F-01), 8 J (rows 148, 155, 165,
166, 167 partial, 168 partial, 169 partial, 171 — `battery-trend.js`/
`freshness.js` fetched via `served_asset()` instead of a raw disk read;
several of these need the file's own quoted string literals intact, so
they strip comments with this chain's own new
`strip_js_line_and_block_comments()` helper rather than
`companion_markup.strip_js_comments_and_strings()`, which erases string
literals too), 2 S (rows 167 and 170, each a partial drop — see below), 1
P/J deletion (row 154).

Row 154 (the legacy "the D-12 reversal (260902-chc) is written down at both
prose sites it touches ..." check) is `deleted`, reason: `P: asserted
plan-history prose in a freshness.js header comment and in a .planning
CONTEXT.md; no behaviour` — it opened `companion/static/freshness.js` for a
quick-task identifier and the house "SUPERSEDED" token, and separately
opened a phase context document under the planning tree for the same pair
beside the original decision's wording. No rendered or served behaviour
sat behind either assertion.

Two rows are `ported` with one clause of their original legacy check
dropped in place, rather than carried forward verbatim (TST-12 rubric S):

- Row 167 (the swap registry's one-definition-site/one-key-set check) used
  to grep `companion/pages/health_page.py`'s own source for the literal
  `"REFRESH_SWAP_SELECTORS = ("` (to prove no second tuple is defined
  there) and for the bare substring `"REFRESH_SWAP_SELECTORS"` (to prove
  the name still exists). The first is dropped as redundant: the identity
  check right beside it (`health_page.REFRESH_SWAP_SELECTORS is registry[
  layout.REFRESH_PAGE_HEALTH]`) already fails if a second tuple literal
  shadowed the import, since Python never interns two distinct tuple
  literals defined in different modules as the same object. The second
  becomes `hasattr(health_page, "REFRESH_SWAP_SELECTORS")`, a direct
  behavioural equivalent.
- Row 170 (Flights joining the swap loop) used to grep
  `companion/layout.py`'s own source for a comment paragraph explaining,
  in prose, why the filter-input elements are excluded from Flights' swap
  regions. Dropped: a served page or script cannot disagree with a
  comment's wording, and the check's structural half (which elements
  Flights' registry entry names, and which it excludes) is unchanged and
  fully ported.

New module: `companion/test_status_pages_04.py` (30 pytest node ids
covering the 31 non-deleted baseline rows in this slice: 30 rows ported
1:1 to a single node id — one fewer node id than rows because none of this
part's checks needed splitting). Reuses part 02/03's exact
`_module_server`/`css_text`/`battery_trend_js` module-scoped read-only
server fixtures, plus a new `freshness_js` fixture of the same shape (no
test in this part mutates server state, so a shared read-only server
stays safe per 33-MIGRATION-RULES.md section 2).

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 177` to `EXPECTED_CHECK_COUNT = 146` (177 - 31);
part 04's 31 checks and the one closure only they used
(`_js_code_without_comments()`) are removed from `main()`. This part's
own slice contains the audit's `.planning`/ticket-ID evidence sites (the
deleted row 154): after this plan, no status-pages check reads a
`.planning/` file, and `grep -c '"\.planning"' companion/test_status_
pages.py` is 0.

### Part 05 (plan 33-29)

72 rows `ported` (73 baseline rows minus 1 `deleted`), one row `deleted`.
Three rows (181-183, the 52-vendored-illustration checks) each map to a
single primary parametrized node id — `[air-algerie.png]`, the first
sorted vendored filename — out of 52 ids each: `pytest --collect-only`
confirms all 156 instances collect; the SUMMARY lists the other 51 ids
per row.

- Row 185 (`no module anywhere under companion/ defines its own
  alpha-threshold constant`) is `deleted` (TST-12 rubric S): a companion-
  package-wide grep for a second `ALPHA_THRESHOLD` assignment, with no
  behaviour beyond what rows 183's own centred/unclipped-bbox checks
  already prove by calling `server.plane.render._opaque_bbox()` directly
  — a stray, unused constant elsewhere in the package would never change
  what those checks observe.
- Row 172 (the freshness-line check) is `ported` with two source-text
  sub-clauses dropped in place (rubric S): its own grep of `companion/
  pages/health_page.py`/`companion/layout.py` for the literal
  `class="page-header__freshness` substring is redundant with the SAME
  check's rendered-equality proof (`built in rendered` against `layout.
  freshness_line_html()`'s own output, for both Health and Home) —  a
  second, unused definition of that markup could exist in health_page.py
  and never be observed unless it were actually rendered, which the
  equality check already rules out.
- Row 208 (`relative_age_text()`'s positional signature) is `ported` with
  its `inspect.getsource()` call (rubric S) rewritten as a behaviour
  proof: a positional call in the pinned order (`age_seconds`, `lang`)
  compared against the same call spelled out with both keyword names — a
  signature that quietly swapped the two would satisfy the keyword call
  but not the positional one.
- Row 174 (the strip countdown) and row 175 (the picture fade) are
  `ported` with their `companion/static/*.js` source scans (rubric J)
  rewritten to fetch every served script through `companion/app.py`'s own
  `*_SCRIPT_ROUTE` registry (enumerated from the live module's attributes,
  never a `companion/static` directory listing) and strip only comments
  with this chain's `strip_js_line_and_block_comments()`. Row 175's
  stylesheet half goes through `companion_markup.keyframes()`/
  `declarations_for()` against the served stylesheet instead of a disk
  read (33-FOLLOWUPS.md F-01).
- Rows 230 and 231 (the Safari autofill-suppression sweep and the
  hyphen-free-filter-id sweep) are `ported` with their `ast`-based
  module-wide source scans (rubric S) rewritten to rendered-page
  behaviour: every `<input type="search">` this app renders today —
  Compagnies' gallery filter, Health's registry filter (seeded so it
  appears) and Flights' history filter — is parsed structurally
  (`companion_markup.parse_html()`) and checked for the three suppression
  attributes and a hyphen-free id; row 231's `*_FILTER_INPUT_ID` half is
  ported as a direct check of the three real production constants (never
  source text). Guard G2 bans `ast`/`inspect` introspection of production
  source in this suite, so the legacy checks' forward guard against a
  hypothetical FOURTH filter bar not covered by these three renders is a
  known, narrower scope than the static analysis provided — there is no
  forward-guarding mechanism available under TST-12 that does not itself
  read production source as text.
- Row 234 (`airlines_page.py` imports no history-database/sqlite module)
  is `ported`, rewritten from a source grep to a runtime check of
  `airlines_page`'s own module namespace (`vars(airlines_page)`): which
  name IS bound there is a fact about `airlines_page.py`'s own import
  statements. Deliberately NOT a `sys.modules`-membership check (33-25's
  own `test_wake_module_never_imports_pages_or_app()` pattern): `poll_
  loop`, which this module is required to import, itself imports
  `sqlite3`/`server.history_db`, so `sys.modules` would carry both
  regardless of what `airlines_page.py`'s own source says.
- Every CSS check in this part (rows 240-242, the zoom stylesheet
  contract, the mobile button override's source order, and the lightbox's
  max-width) fetches the stylesheet `companion/app.py` actually serves and
  asserts on it structurally via `companion_markup.css_rules()`/
  `declarations_for()`/`rules_with_selector()` (33-FOLLOWUPS.md F-01).

New modules: `companion/test_status_pages_05.py` (37 baseline rows,
checks #172-#208, 190 pytest node ids — the three 52-illustration checks
each parametrized per vendored file so xdist spreads them) and
`companion/test_status_pages_05b.py` (36 baseline rows, checks #209-#244,
36 pytest node ids — no splitting needed in this half).

`companion/test_status_pages.py` (the legacy harness) shrinks from
`EXPECTED_CHECK_COUNT = 146` to `EXPECTED_CHECK_COUNT = 73` (146 - 73);
part 05's 73 checks and the closures only they used are removed from
`main()`.

### Part 06 (plan 33-30)

Rows 245-292 (part 06, original `check()` calls #245-#292, 48 checks) are
flipped: 46 `ported` to `companion/test_status_pages_06.py`, 2 `deleted`.

Rubric codes: 40 B/D (calls `companion.pages.airlines_page`/`companion.
pages.health_page`/`companion.layout` directly, or renders a real page and
asserts on the returned/rendered HTML — the legacy harness's own substring/
regex style over rendered markup, per 33-25's precedent, since TST-12 only
bans reading production SOURCE files, not asserting on a page's own
rendered HTTP/in-process output), 6 C (rows 249, 251, 254, 277, 286-290's
seven style.css checks collapse to six ported rows since two share one
check each: `.frame-strip__cells`/`.frame-strip__cell button`/`.stat-tile:
not(.frame-strip):hover`/`.frame-strip__cell--update .status-card__
headline`/`.time-value`/`.tab-bar`, all rewritten against a served
stylesheet via `companion_markup.css_rules()`/`declarations_for()`/
`rules_with_selector()`, iterating parsed `Rule.selectors`/`Rule.
declarations` rather than a regex/substring probe over the raw served
text), 1 J (row 276, `list-filter.js`'s raw disk read, rewritten as a
`served_asset()` fetch through `strip_js_line_and_block_comments()`), 1 S
(row 271, the retired D-06 supersession machinery's own symbols, rewritten
as `not hasattr(airlines_page, name)`). 2 deletions: row 285 (S — a
`companion/layout.py` source grep for a retired `age_seconds(next_wake...)`
re-derivation, redundant with the frame-strip behaviour checks this same
part already carries), row 291 (C — a served-stylesheet header COMMENT
assertion, no rendered behaviour per guard G1).

Two more rows keep their ported status but drop one now-redundant
source-text sub-clause each, noted in the new module's own docstring and
at each test's own docstring (not counted as separate deletions — the
check's remaining assertions are still `ported`): row 250 (a `companion/
pages/airlines_page.py` source scan for a hand-written glyph token,
redundant with the rendered `<use>` count/class assertions kept) and row
257 (a source scan for the `'data-filter-group="gap%d"'` format-string
literal, redundant with the rendered-attribute regex match kept).

New module: `companion/test_status_pages_06.py` (46 pytest node ids, one
per ported row — no row in this slice needed parametrization or a
one-to-many split). A `_module_server`/`css_text` module-scoped read-only
server fixture pair is new in this module, for the 6 C-rubric checks and
the 1 J-rubric check above — no test in this module mutates that server's
state, so every CSS/JS-reading test shares it safely under xdist.

`companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT`
dropped from 73 to 25; part 06's 48 checks removed from `main()`. Four
closures/constants (`_frame_strip_ctx`, `_css_source`, `_block`,
`_TAB_BAR_BANNER`) that used to sit beside their own first use inside part
06's checks are relocated (not deleted), right after the check() closure
definition, because later, not-yet-migrated checks (part 07) still call
them.

### Part 07 (plan 33-31) — chain closed

Rows 293-317 (part 07, original `check()` calls #293-#317, the LAST 25
checks in the file) are flipped: all 25 `ported` to `companion/
test_status_pages_07.py`, 0 `deleted`.

Rubric codes: 12 B/D (renders a real page — `layout.page_shell()`/
`layout.frame_strip_html()`/`health_page.render()`/`health_page.
compute_health_state()`/`home_page.render()`/`config_page.render()` — and
asserts on the returned/rendered HTML, per 33-25's precedent), 9 C (rows
293, 294, 297, 298, 299, 301, 302, 304, 309's nine style.css checks,
rewritten against a served stylesheet via `companion_markup.css_rules()`/
`declarations_for()`/`rules_with_selector()`, iterating parsed `Rule.
selectors`/`Rule.declarations` rather than a regex/substring probe over
the raw served text), 2 J (rows 300 and 315, `freshness.js`'s two raw
disk reads, rewritten as `served_asset()` fetches through this chain's
`strip_js_line_and_block_comments()`), 2 B/end-to-end (rows 316-317, a
real `companion/app.py` subprocess via `make_app_server`, logged in
through `companion_app_server.login()`). 0 deletions — every one of the
final 25 checks maps onto observable behaviour with no source-text read
needed.

Two rows keep their `ported` status but replace a legacy sub-clause that
had no structural equivalent, noted in the new module's own docstring and
at each test's own docstring (not counted as separate deletions, per the
same precedent 33-30 set for rows 250/257):
- Row 299 drops the legacy check's own
  `css_source.count("@media (prefers-reduced-motion: reduce)") != 2`
  literal count (`css_rules()` records each rule's ENCLOSING at-rule
  context, not a raw count of top-level at-rule block occurrences in the
  source — there is no structural equivalent for "exactly N block
  occurrences"). The replacement asserts the two SPECIFIC things that
  count actually protected: the one global `*, *::before, *::after`
  override exists under that media query, the one `.js .mobile-nav`
  opt-out exists under it too, and `summary::before` (this task's own
  subject) carries no THIRD, redundant per-rule override under the same
  at-rule.
- Row 309 drops the legacy check's own `css_source.count("dot--") != 9`
  literal count. Of the raw served text's 9 substring occurrences, 5 are
  prose inside COMMENTS (guard G1 already rules out comment text as a
  source of behaviour) and only 4 are real selectors. The replacement
  asserts the actual invariant the comment-polluted count stood in for:
  exactly four `.dot--*` modifier classes exist (ok/warn/error/off) and
  no fifth has been added — a stronger, comment-immune version of the
  same acceptance criterion.

Row 298 (the stray-comment-terminator structural guard) is `ported`
scanning the SERVED stylesheet's raw character stream rather than
`css_rules()`'s parsed structure: the defect it guards against (an
unterminated `/* */` comment silently swallowing the next rule) is
exactly the shape a real CSS parser cannot see through either, so no
`css_rules()`-based rewrite is possible without losing the property under
test. It still never reads the file from disk — only the bytes
`companion/app.py`'s STYLE_ROUTE actually serves, fetched over HTTP.

Rows 316-317 (the file's final two checks, a real running-service
end-to-end round trip) move from the legacy harness's own local `Harness`/
`http_request`/`_NoRedirectHandler` to `companion/conftest.py`'s
`make_app_server` fixture and `test-support/companion_app_server.py`'s
`login()`/`get()`. Row 316's STYLE_ROUTE assertions (previously a
substring probe over the raw served CSS text) are rewritten structurally
against `companion_markup.rules_with_selector()`/`declarations_for()`
over that SAME real subprocess's own served bytes (33-FOLLOWUPS.md F-01);
its FRESHNESS_SCRIPT_ROUTE assertions stay a comment-stripped served-text
scan (JS delivery contracts are the named exception in this chain's own
convention), fetched fresh from the running service and passed through
`strip_js_line_and_block_comments()` rather than left raw.

New module: `companion/test_status_pages_07.py` (25 pytest node ids, one
per ported row — no row in this slice needed parametrization or a
one-to-many split). Reuses this chain's `_module_server`/`css_text`
module-scoped read-only server fixture pair (33-26) for the 9 C-rubric
checks, adds a `freshness_js` module-scoped fixture for the 2 J-rubric
checks, and uses `companion/conftest.py`'s function-scoped
`make_app_server` fixture (never the module-scoped one) for the two
end-to-end checks, since they seed real per-test fixture state and log in.

**Chain closed.** `companion/test_status_pages.py` — the LAST legacy
companion harness — is deleted outright (`git rm`), after confirming no
importer remains anywhere in the repo (grepped imports, `open(`/`ast`/
`Path(`/string mentions across companion, test-support, conftest, the
shim, and every other test module — only prose comments and the frozen
`ORIGINAL_COMPANION_HARNESSES` history tuple in `test-support/
skypane_test_support.py` survive, used only to bound a guard's own
exemption set, never opened). All 317 of this harness's baseline checks
are now accounted for (313 ported, 4 deleted — rows 285/291 from part 06
plus 2 earlier deletions from prior parts — 0 pending).
`33-ledger-check.py companion/test_status_pages.py` **WITHOUT**
`--allow-pending` confirms **317/317 baseline checks mapped, 0 pending**.

`skypane_test_support.legacy_companion_harnesses()` now returns `()` —
the disk-derived legacy set is EMPTY, since every companion harness chain
(33-04, 33-08, 33-13, 33-18, 33-20, 33-24, and now this one) has finished.
`companion/test_legacy_harness_shim.py`'s own parametrize list collapses
to an empty set, which pytest reports as a clean SKIP
("got empty parameter set for (harness)"), never an error or a failure —
confirmed by running the shim module directly.

## companion/test_browser_ux_health_drawings.py

# Ledger: companion/test_browser_ux_health_drawings.py

Baseline: `companion__test_browser_ux_health_drawings.txt`, 11 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | the battery ring's value arc resolves to a real theme token on BOTH pages in BOTH themes — never the SVG default fill or stroke, never the same paint as its own track, and never the same value in light and dark (CFG-40, 24-02's theme and computed-paint helpers) | ported | companion/test_browser_ux_health_drawings.py::test_the_ring_paints_a_theme_token_in_both_themes[chromium-Home] |
| 2 | the battery ring's viewBox contains its own STROKED geometry on both pages — each arc's browser-reported bounding box, expanded by half its resolved stroke width on every side, lies inside the box the emitter declared (CFG-45, contract rule 5) | ported | companion/test_browser_ux_health_drawings.py::test_the_rings_viewbox_contains_its_own_stroked_geometry[chromium-Home] |
| 3 | at the 360px floor the ring costs nothing it must not: neither page's body scrolls sideways, Home's Battery tile stays exactly as tall as the Frame tile beside it (measured against a neighbour, because 'all three equal' is false at 360px and vacuous at 1280px), and both rings still render — and still paint a dark-mode token — with scripts blocked through _no_js_page() (CFG-45, D-09) | ported | companion/test_browser_ux_health_drawings.py::test_the_ring_costs_no_width_no_height_and_no_script[chromium] |
| 4 | the battery chart's area, line, mark and threshold each resolve to a real theme token in BOTH themes — never the SVG default, the area/line/mark sharing one currentColor ink while the threshold deliberately does not, the legend's swatch equal to the drawn threshold, and the area's COMPOSITE over the card clearing a 1.20:1 floor so it is visible and not merely painted (CFG-41/CFG-45, 24-05-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_charts_area_mark_and_threshold_paint_real_tokens_in_both_themes[chromium] |
| 5 | at the 360px floor the battery chart's additions cost nothing they must not: the page body does not scroll sideways in EITHER language, the threshold's legend overlaps none of the four axis labels and stays inside its card at the 10px micro-label tier, its swatch measures a real 12x1 box (which an inline <span> could not), the canvas keeps its share of the grid rather than being squeezed by a legend that claimed the Y-label column, the mark's edge-hung ink stays inside the card, and the area, mark, threshold and legend all still render — and still paint dark-mode tokens — with scripts blocked (CFG-45, D-09, 24-05-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_chart_costs_no_width_at_360_in_either_language_and_needs_no_script[chromium] |
| 6 | the day band's frame, shaded span and check-in marks each resolve to a real theme token in BOTH themes and never the SVG default, all three move when the theme does, the span clears a 1.15:1 floor against the band's own surface (they are one token at two strengths, so 'not the default' says nothing about whether they can be told apart), the frame clears 1.05:1 against its card so an empty day is not literally nothing, and a mark crossing the span — which is where a night's check-ins land, and the fixture is asserted to produce one — clears 4.5:1 over it (CFG-42, 24-06-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_day_bands_frame_span_and_marks_paint_real_tokens_in_both_themes[chromium] |
| 7 | at the 360px floor the day band is a real drawing in BOTH languages: the page body does not scroll sideways, every mark renders at least the 2px draw.py declares (a mark emitted in absolute pixels into a CSS-sized canvas has nothing in the markup guaranteeing it survives to paint), every mark and span stays inside the canvas, the minimum mark spacing re-derived from the canvas's MEASURED width still buys the 4px its comment claims, the three hour labels sit at the band's own left edge, midpoint and right edge, the canvas is the same width in both languages, and the whole band plus its two shaded spans still render and still paint dark-mode tokens with scripts blocked (CFG-42, D-09, 24-06-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_day_band_is_a_real_drawing_at_360px_in_both_languages_without_script[chromium] |
| 8 | all FOUR of the regularity grid's cell states paint a real theme token in BOTH themes and never the SVG default, all four move when the theme does, each key swatch composites to exactly the colour of the cell it explains (one `color` declaration, an SVG fill and an HTML background), the three verdicts clear WCAG AA's 3:1 non-text bar against their card while the no-observation state clears its own lower, deliberate 1.25:1 floor, and every one of the six pairs stays past the app's own MIN_SIGNAL_PERCEPTUAL_DISTANCE — four states that read as three in dark mode is a defect no source scan can see (CFG-43, CFG-45, 24-07-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_grids_four_states_stay_four_states_in_both_themes[chromium] |
| 9 | the regularity grid is a real drawing at the 360px floor in BOTH languages: the page body does not scroll sideways, a Health card's content box still measures the width draw.CARD_DRAWING_WIDTH_PX records, all 30 cells render as one square at or above the 24px floor the bucket count is supposed to come down for, every cell inks inside the viewBox, the wrapper is exactly as wide as the canvas so the two date labels sit on the first and last columns, the four key swatches keep their declared 12px box inside the card, the geometry is identical in both languages, the whole grid still paints dark-mode tokens with scripts blocked, and at 1280px and 320px the wrapper and the canvas still agree with no page overflow and no stretched cell (CFG-43, CFG-45, D-09, T-24-07-D, 24-07-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_grid_is_a_real_drawing_at_360px_in_both_languages_without_script[chromium] |
| 10 | at the 360px floor D4's hero STACKS rather than shrinks, in both languages: its three parts share one column with exactly the 16px one --space-md declares between them and 24px below the group (bound tighter than it is separated, asserted as equalities because a 40px gap is what parts keeping their own margins render and passes every 'at least'), the battery ring still renders at the 36px home_page.BATTERY_RING_SIZE declares and the day band's canvas at the 278px draw.py's mark spacing was derived from, all five seeded check-ins still draw, the page body does not scroll sideways, the hero is the same width in both languages, and the ring and the band paint real inverting tokens in BOTH themes through selectors scoped INSIDE the hero (CFG-44, CFG-45, 24-08-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_hero_stacks_at_360px_with_its_parts_at_the_size_their_own_plans_chose[chromium] |
| 11 | the hero's grouping is the same composition at 360px and at 1280px — one column with the same 16px inside and 24px below at both, no page overflow at either — while the three status tiles inside it stack at the floor and share one row on the desktop, so the stack is a FLOOR behaviour rather than the only one; the band gets MORE room as the viewport grows, never less; every one of Home's declared refresh-swap selectors still matches a real element through the browser's own selector engine (a stale one stops the live refresh silently); and with scripts blocked the hero's children keep their lefts, widths and gaps and both drawings keep their boxes (CFG-44, CFG-45, D-09, 24-08-PLAN.md Task 3) | ported | companion/test_browser_ux_health_drawings.py::test_the_heros_grouping_holds_at_both_widths_and_owes_nothing_to_a_script[chromium] |

### Part 01 (plan 33-19)

- 11 B/D checks ported, 0 deletions.
- New module: `companion/test_browser_ux_health_drawings.py` (rewritten in place, 13 pytest-playwright node ids — rows 1 and 2 each split into `[chromium-Home]`/`[chromium-Health]` parametrized variants over the two drawing pages, since each page's assertion is fully independent; the ledger row points at each check's first (Home) id).

## companion/test_browser_ux_quiet_wake.py

# Ledger: companion/test_browser_ux_quiet_wake.py

Baseline: `companion__test_browser_ux_quiet_wake.txt`, 9 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | the quiet window still SAVES with scripts blocked through the dial — both ends set natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way, at 360px and in BOTH shipped languages; the gated handle layer has zero height and no keyboard can reach into it with scripts blocked while it occupies space with them; and the server-drawn ARC, the readout, both time inputs, B14's two 24h siblings and the three presets are all present on the scripts-blocked page, asserted after the save so none of them can stand in for it (D-09/CFG-48, 25-04-PLAN.md Task 4) | ported | companion/test_browser_ux_quiet_wake.py::test_the_quiet_window_still_saves_with_scripts_blocked_through_the_dial[chromium] |
| 2 | dragging a quiet-hours handle changes its own native <input type="time">, moves the announcement ON THE HANDLE rather than on the wrapper, REVEALS the bar and PERSISTS to disk once Enregistrer is clicked; one ArrowRight moves exactly one stated step and End/Home reach 23:59 and 00:00 with zero pointer events fired and the recorder proving itself; and a preset click moves BOTH handles, which is what proves the two native inputs are the one source of truth (the arc/caption AGREEMENT claim this check used to also carry is superseded by _the_arc_the_handles_and_the_caption_agree_after_an_interaction(), CFG-71, 27-02-PLAN.md Task 4) (CFG-48, 25-04-PLAN.md Task 4; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78) | ported | companion/test_browser_ux_quiet_wake.py::test_dragging_and_keying_a_quiet_hours_handle_reach_disk[chromium] |
| 3 | THE arc/handles/caption agreement check (CFG-62/CFG-71/D-32, 27-02-PLAN.md Task 4): in BOTH themes, after dragging the end handle to reach the developer's own recorded window (08:00→18:00) AND, in the same check, after pressing a preset (23:00→07:00, the wrap through midnight) from wherever the drag left it, all FOUR surfaces — the two native <input type="time"> fields, the two handles' aria-valuenow, the arc's RESOLVED geometry (read back through getComputedStyle, not the static attribute), and the caption's own text — decode to the SAME canonical (start_minute, end_minute) pair, which equals what the interaction requested and differs from what was there before; AND, after the same preset click, each B14 twin's own live .hidden property matches this browser's resolved hour12 (CFG-80, 29-04-PLAN.md Task 3, folded into this existing check rather than a new one so EXPECTED_CHECK_COUNT does not move for an assertion this worktree has never run); separately, with scripts blocked, the arc still carries both presentation attributes and they still decode to whatever window is actually saved on disk — under auto-save that is the preset's own commit, read fresh rather than assumed (27-04-PLAN.md Task 4, CFG-63) | ported | companion/test_browser_ux_quiet_wake.py::test_the_arc_the_handles_and_the_caption_agree_after_an_interaction[chromium] |
| 4 | the dial caption keeps the SAME FORM the server emits at load after EACH of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 Bug A, 28-03-PLAN.md Task 3): after every one, the caption's two "HH:MM" tokens decode to what the interaction requested, its duration segment is NON-EMPTY and equals the wrapped-difference computation worded from the page's own layout.DURATION_ATTRS (never a hardcoded unit literal), and the whole caption's structural shape (separators, spacing, token order) matches the server-rendered reference captured before any interaction — in BOTH shipped languages, with the preset step crossing midnight | ported | companion/test_browser_ux_quiet_wake.py::test_the_dial_caption_keeps_its_form_after_every_interaction_kind[chromium] |
| 5 | the quiet dial meets its floors at 360px — BOTH handles clear the 44px touch target by real hit-testing in THEIR OWN container with the window's ends far apart AND close together, with the overlapping case measured and its document-order z-rule confirmed (the end handle grabbable, the start handle still focusable); the drawing measures its emitter's own declared size by getBoundingClientRect rather than clientWidth, computes display:block, is centred in its card and captioned by a centred readout with no top margin; the four anchor hours each sit on their own axis; the page does not scroll sideways; and the paint is a FLOOR not a ceiling — the day and the window are different colours, the labels that orient it are weaker than it is, the grip has an edge, and every one of the five differs between the two themes (CFG-48/CFG-52, 25-04-PLAN.md Task 4) | ported | companion/test_browser_ux_quiet_wake.py::test_the_dial_meets_its_floors_at_360px_in_both_themes[chromium] |
| 6 | THE handle-stays-on-its-ring check (CFG-73 Bug B, 28-02-PLAN.md Task 2): holding the quiet-hours start handle down with no drag samples its resolved distance from the dial's own centre at least 10 times across at least 400ms — long enough to cover the measured 90-150ms collapse — and asserts EVERY sample stays within a stated tolerance of the dial's own --quiet-dial-radius (read from rendered geometry, never hardcoded), naming the worst sample's distance and index on failure; the control's reported value is asserted IDENTICAL before mouse.down() and after mouse.up() (a press is not a drag); a final post-release sample is asserted on the ring too, with the source recording that this is the ONE state the pre-fix code already got right and therefore not sufficient alone; and the whole check runs in BOTH themes at the 360px floor | ported | companion/test_browser_ux_quiet_wake.py::test_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press[chromium] |
| 7 | the wake interval still SAVES with scripts blocked beside the slider — typed natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way, at 360px and in BOTH shipped languages; the gated range has zero height and no keyboard can reach into it with scripts blocked while it occupies space with them; both gauges are MEASURED (not counted) present on the scripts-blocked page, asserted after the save so neither can stand in for it; and the out-of-range trap is re-proven end to end — with 30 s on disk the number input carries NO value attribute, no range and no gauge render at all, and the whole Settings form still saves a corrected value (D-09/CFG-49/T-25-05-B, 25-05-PLAN.md Task 3) | ported | companion/test_browser_ux_quiet_wake.py::test_the_wake_interval_still_saves_with_scripts_blocked_through_the_slider[chromium] |
| 8 | dragging the wake-interval range moves the native <input type="number"> the form posts, moves BOTH gauge sentences with it, REVEALS the bar and PERSISTS to disk once Enregistrer is clicked — with the script's own wording asserted EQUAL to the server's for the same two cadences, so the script provably carries no copy of its own; one ArrowRight moves exactly one stated step and End/Home reach device_config's own ceiling and floor with zero pointer events fired and the recorder proving itself; typing into the number input moves the range back; and at no position — dragged, keyed, at the floor or at the ceiling — does the battery gauge produce a days figure from this fixture's RISING series (CFG-49/CFG-52/T-25-05-C, 25-05-PLAN.md Task 3; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78) | ported | companion/test_browser_ux_quiet_wake.py::test_dragging_and_keying_the_wake_range_reach_disk[chromium] |
| 9 | the wake-interval slider meets its floors at 360px — its hit area clears the 44px target by real hit-testing in ITS OWN container (never inherited from a class), it measures wider than the number input it steers and no wider than the card holding it by getBoundingClientRect rather than clientWidth, its wrapper keeps a real top margin off the field's own row, the Device page does not scroll sideways at that width (its own baseline, not the Display page's), and the paint is a FLOOR not a ceiling: both gauge sentences and the control's own accent and surface all differ between the two themes and neither sentence is painted in the canvas colour (CFG-49/CFG-52, 25-05-PLAN.md Task 3) | ported | companion/test_browser_ux_quiet_wake.py::test_the_wake_slider_meets_its_floors_at_360px_in_both_themes[chromium] |


### Part 01 (plan 33-20)

- Rubric codes: 9 B (all nine checks call a production function or drive the
  real UI through the guarded fixtures and assert on their output/on-disk
  effect; no source-text, CSS-comment or `.planning/` reads existed in this
  harness to reclassify).
- New module: `companion/test_browser_ux_quiet_wake.py` (rewritten in place;
  no new file — this is a single-plan browser harness per 33-MIGRATION-
  RULES.md section 1). `main()`, `check()`, `EXPECTED_CHECK_COUNT`,
  `sync_playwright()` and the `LegacyHarness` import are gone; the file
  leaves the disk-derived legacy set.

## companion/test_browser_ux.py

# Ledger: companion/test_browser_ux.py

Baseline: `companion__test_browser_ux.txt`, 75 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | _ASPECT_REPIN_LEDGER is non-empty, every row is well-formed (all five keys present, 'property' naming an actual property in at least eight words, not a restated selector), no 'retired' name still has a def in this file, every 'owed_by' names one of this phase's own later plans, and any row claiming repayment IN this file (empty owed_by) names a replacement that genuinely has a def here — so a forgotten re-pin is a red build, not a silent coverage loss (CFG-85, 30-03-PLAN.md Task 3) | deleted | R: self-referential CFG-85 aspect-repin bookkeeping; opens test_browser_ux.py to grep def names; no behaviour |
| 2 | a Flights detail row expands and collapses from an icon-only toggle with no visible text, a >=44x44 synthesized hit area and an accessible name that swaps with the state, flipping aria-expanded and toggling the row aria-controls resolves to; and a click on a non-interactive cell of the same row expands it, while a click on the toggle itself toggles exactly once (22-09-PLAN.md Task 1, X5/T-22-32) | ported | companion/test_browser_ux_01.py::test_flights_detail_row_expands_and_collapses[chromium] |
| 3 | the Quiet hours caption's schedule link clears the 44px hit-target floor by real hit-testing in its own frame-strip cell, in both themes, at the 360px floor, on both Home and Display, with neither page gaining horizontal scroll from the addition (CFG-69, 27-08-PLAN.md Task 2) | ported | companion/test_browser_ux_01.py::test_the_quiet_schedule_link_meets_the_hit_target_floor_at_360px[chromium] |
| 4 | every icon control in the .copy-btn/.row-toggle family resolves to the 44px hit-target floor in its OWN container, by real hit-testing rather than a declared value: .row-toggle and the desktop Flights detail row's three .copy-btn (hex/timestamp/callsign, each hovered/focused to clear the opacity-at-rest reveal) at 960px, and the mobile <details> card's own three .copy-btn at the 360px floor — both in both themes, ONE check for the whole family sharing .copy-btn's values (CFG-70, 27-08-PLAN.md Task 3) | ported | companion/test_browser_ux_01.py::test_copy_btn_and_row_toggle_resolve_to_the_floor_in_their_own_containers[chromium] |
| 5 | at 390px on Flights the filter count and the Clear control report the same bounding-box top — Clear never drops alone onto its own line (B11, 22-09-PLAN.md Task 3, a regression of Phase 18's A-18) | ported | companion/test_browser_ux_01.py::test_flights_filter_count_and_clear_share_one_line_at_390px[chromium] |
| 6 | at 390px every Airlines illustration grid renders exactly two cards per row (never the one-per-row auto-fill collapse that made the page 5800px tall), with each row's two columns equal within 1px, the main grid's cards near the 159px the contract predicts, and the whole page under 3800px (X7, 22-11-PLAN.md Task 2, ceiling recalibrated by quick task 260921-v9c for the 27->36 airline count) | ported | companion/test_browser_ux_01.py::test_airlines_grid_renders_two_cards_per_row_at_390px[chromium] |
| 7 | at 390px on Airlines the filter count and the Clear control report the same bounding-box top, both inside the one shared .filter-bar__meta group plan 22-09 introduced — adopted verbatim, no per-page variant (B11, 22-11-PLAN.md Task 3, the second of the three filtered pages) | ported | companion/test_browser_ux_01.py::test_airlines_filter_count_and_clear_share_one_line_at_390px[chromium] |
| 8 | at 1280px in BOTH languages Health's unresolved-prefix table reports scrollWidth === clientWidth on its .data-table-wrap, the Resolve column sits inside that wrap's own box (reachable with no horizontal scrolling) and no header is clipped — the French table measured 1026px against an 830px wrap before the stacked cells and the shortened headers (B12, 22-12-PLAN.md Task 2) | ported | companion/test_browser_ux_01.py::test_health_registry_table_fits_1280px[chromium-en] |
| 9 | at 390px on Health the filter count and the Clear control report the same bounding-box top, both inside the one shared .filter-bar__meta group — the third and last of the three filtered pages — and the page header's Updated clock carries .time-value, never .mono (B11/C5, 22-12-PLAN.md Task 3) | ported | companion/test_browser_ux_01.py::test_health_filter_count_and_clear_share_one_line_at_390px[chromium] |
| 10 | with scripts blocked Health renders in full — all four tiles with their label/verdict/detail slots each exactly once, the registry filter bar and Clear, the unresolved-prefix rows, and a per-row Resolve action that actually navigates to the Airlines resolve surface (D-09's floor asserted at this plan's own commit, 22-12-PLAN.md Task 3) | ported | companion/test_browser_ux_01.py::test_the_no_js_floor_holds_for_health[chromium] |
| 11 | Display: a theme chip, a runway card and a quiet-hours time field each commit via change, REVEAL the bar, and PERSIST to DISK once Enregistrer is clicked (form=-attached radio and time-input field kinds — the Enable-display checkbox this check also covered is retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78) | ported | companion/test_browser_ux_01.py::test_display_reveal_and_persist_across_all_field_kinds[chromium] |
| 12 | Device: the wake-interval field commits via change, REVEALS the bar, and PERSISTS to DISK once Enregistrer is clicked, proving the two scopes stay in step (B1) — witnessed by the wake-interval field since the Diagnostic LED stopped being a Save-governed control (retargeted in place by 23-07-PLAN.md Task 2, D2/CFG-36; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78) | ported | companion/test_browser_ux_01.py::test_device_reveal_and_persist_stays_in_step_with_display[chromium] |
| 13 | the bar (the single [data-static-save-fallback] Save affordance, relocated inside it, never a second button) is server-rendered VISIBLE — the no-JS floor — and hides IMMEDIATELY once script proves itself live; an edit REVEALS it again, naming the changed section via [data-dirty-count]; and clicking its own Save persists to disk through a real navigation — the INVERSE of 27-03-PLAN.md Task 2 (CFG-64) and 27-04-PLAN.md Task 4 (CFG-63)'s own retired polarity, which this check's former name asserted (D-01/CFG-64/CFG-77/CFG-78, retargeted onto the restored bar by 28-10-PLAN.md Task 2) | ported | companion/test_browser_ux_01.py::test_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves[chromium] |
| 14 | the leave-guard stays armed for a field that has been edited but never fired change (the bar already visible and already naming the section, the restored model's no-silent-phase clause — strictly more than the retired save-status region ever asserted); the guard STAYS ARMED, not disarmed, the instant change commits the edit, because a committed-but-unsaved change is exactly what the restored guard exists to warn about; and Annuler is the guard's own exit, disarming it and hiding the bar (the re-arm-after-Cancel clause is 28-11-PLAN.md's own check, not duplicated here) (D-10, <restored_guard_semantics>, retargeted from the retired auto-save's own inverted disarm-on-commit contract by 28-10-PLAN.md Task 2, CFG-77/CFG-78; 27-04-PLAN.md Task 4, CFG-63) | ported | companion/test_browser_ux_01.py::test_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit[chromium] |
| 15 | the leave-guard's re-arm-after-Cancel clause — CFG-77's own 'does not disarm the leave-guard permanently... kept exactly where CFG-63's own carve-out already put it' — has executable coverage for the first time: fresh load (disarmed) -> edit (armed) -> Annuler (disarmed) -> a NEW edit (RE-ARMED, the clause nothing else in this phase proves, and exactly the defect a Cancel handler that sets suppressGuard=true once and never clears it reproduces) -> a second Annuler (disarmed again, so a one-shot re-arm cannot pass); reuses the existing _guard_armed() beforeunload probe throughout — never a second one (CFG-77, 28-11-PLAN.md Task 3; complements 28-10-PLAN.md Task 2's own armed-on-typed-edit/stays-armed-through-commit/disarmed-by-Cancel check, which deliberately stops short of this clause) | ported | companion/test_browser_ux_01.py::test_the_leave_guard_re_arms_after_a_new_edit_following_cancel[chromium] |
| 16 | activating a Frame strip switch with unsaved Display edits present applies over fetch WITHOUT navigating, leaves the leave-guard ARMED for the edit still in the form and the switch still pressable, and raises no dialog, while a plain nav-link navigation with the same unsaved edit still raises one (22-05-PLAN.md Task 3, D-04; retargeted in place by 23-07-PLAN.md Task 1, which is what took the navigation away) | ported | companion/test_browser_ux_01.py::test_strip_switch_applies_without_the_leave_guard_while_other_navigation_still_warns[chromium] |
| 17 | at 390px the three runway cards report one shared line (equal tops), equal heights, and BOTH their border-excluded and their outer widths equal within 1px at a border total of exactly 2.0 each - 22-10's stated T6 allowance for the selected card's 2px border is deleted, closed by 22-15-PLAN.md Task 1 - and each still clears 44x44 - never a 2 + 1 orphan (B9, 22-10-PLAN.md Task 2) - with the transform neutralised for the read and EXACTLY ONE card proven to carry 23-10's selection scale | ported | companion/test_browser_ux_01.py::test_three_runway_cards_share_one_line_at_390px[chromium] |
| 18 | at 390px selecting a palette chip ANSWERS - the chip's border-colour changes to the accent, an inset accent ring (box-shadow) appears, and the .palette-chip__name wash changes - while its own LAYOUT box (offsetWidth/Height/Left/Top), the grid's own box and EVERY chip's position inside it are plain-equal before and after, so T6 cannot recur through the selection signal (D3/CFG-32, 23-10-PLAN.md Task 1; re-pointed to .palette-chip and narrowed off the scale/transition clauses 30-07-PLAN.md deliberately did not add, by 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_01.py::test_selecting_a_theme_chip_answers_and_moves_no_layout_box[chromium] |
| 19 | both <dialog>s FADE AND ZOOM in — measured mid-flight, two frames after the trigger, on History and on the Airlines gallery — settle fully opaque at their own scale, and on close() reach display:none with a zero-area box and a viewport-centre hit test that lands OUTSIDE them, with no settle wait at all, so an invisible click-swallowing sheet cannot hide behind one (D3/CFG-32, T-23-36, 23-10-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_both_dialogs_fade_in_and_leave_nothing_behind[chromium-history] |
| 20 | the live theme preview CROSSFADES - proven by the opacity transition the browser CREATES on the preview image, caught as a transitionrun event rather than sampled at a guessed instant, because every other assertion here is satisfied by the cut this plan replaces - and settles on the theme that was actually selected, fully opaque rather than stuck mid-fade, driven entirely by theme-preview.js's OWN delegated listener with no save and no dirty-state.js involvement at all (D3/CFG-32, T-23-38, 23-10-PLAN.md Task 2; the Cancel half retired by 27-04-PLAN.md Task 2, CFG-63; re-pointed to details.usage-row/.palette-chip by 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_02.py::test_the_live_preview_crossfade_settles_correct_through_its_own_listener[chromium] |
| 21 | Home's frame picture and a theme chip's preview band each reserve their FINAL box before their image arrives — the real request is HELD, the real box is measured unloaded (and asserted to be a real box, not a collapsed one, with a skeleton painted in it), the request is let through, and the box after the decoded image lands is plain-equal to the box before it, at the 360px contract floor and at 1280px (D3/CFG-32, T-23-39, 23-10-PLAN.md Task 3) | ported | companion/test_browser_ux_02.py::test_images_hold_their_place_before_they_arrive[chromium] |
| 22 | at 390px and at 1280px the login card's field and primary are stacked, the same width, filling the card's content column, both 44px tall, sharing one radius and separated by the one 16px token — never a 225x44 field beside a 68x30 button, and never glued at a 0px gap (X3, 22-13-PLAN.md Task 3) | ported | companion/test_browser_ux_02.py::test_login_card_stacks_at_both_widths[chromium] |
| 23 | the show-password toggle reveals ITSELF at load (the hidden attribute is removed, not overridden), swaps aria-pressed and its translated accessible name with the state, keeps .copy-btn's synthesized 44x44 hit area — and with scripts blocked it never appears, reserves no gutter, and the form still signs in (X3/D-09, 22-13-PLAN.md Task 3) | ported | companion/test_browser_ux_02.py::test_show_password_toggle_reveals_itself_and_swaps_its_name[chromium] |
| 24 | a locked-out login page ticks down from the server's own seed, with both controls natively disabled, and re-enables them by itself at zero with no reload — the message cleared and its aria-describedby dropped with it (X3, 22-13-PLAN.md Task 3) | ported | companion/test_browser_ux_02.py::test_a_locked_out_login_page_ticks_down_and_re_enables_the_form[chromium] |
| 25 | in French the two nav-status segments each report exactly ONE client rect at both the 240px sidebar and 390px — the line breaks between them, never mid-phrase — the reminder stays within 48px, the reduced dropdown opens by at most 220px, and on Home the reminder is a <span> with no href whose announced name is the visible state and names no destination (B10/X9/D-04, 22-14-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_nav_status_segments_never_break_mid_phrase_in_french[chromium] |
| 26 | the mobile nav opens and closes leaving the hidden property and aria-expanded consistent on both paths — a descendant's transitionend never hides an open panel, and a close with no transition applies hidden synchronously rather than waiting for an event that never arrives (T5/D-02, 22-14-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_mobile_nav_close_leaves_hidden_and_aria_expanded_consistent[chromium] |
| 27 | the restored bar — genuinely position: fixed at both breakpoints, the INVERSE of this check's own retired position: fixed/sticky refusal — never intersects the ONE other fixed element each breakpoint has (the tab bar under 960px, the sticky sidebar column at and above it) and never covers the page's own last in-flow element, measured via resolved getBoundingClientRect()es (never a CSS property value) at 390x844 and 1280x900, in BOTH shipped languages (the longer French copy is what makes the bar wrap to two lines) — the scripts-blocked variant of the last-in-flow clause is 28-08-PLAN.md Task 2's own acceptance criterion, verified LIVE by that plan rather than by an automated check in this file, named here rather than assumed covered (CFG-31, 27-04-PLAN.md D-04/CFG-63; retargeted onto the restored bar by 28-10-PLAN.md Task 3, CFG-77/CFG-78; retired the fixed save-bar-vs-tab-bar geometry D-10/T7, 22-14-PLAN.md Task 3, this check now measures again) | ported | companion/test_browser_ux_02.py::test_the_dirty_bar_never_overlaps_the_tab_bar_sidebar_or_the_pages_last_element[chromium-390x844-en] |
| 28 | when Health's refresh endpoint starts failing the loop does NOT stop: it schedules a backed-off retry and shows a visible NEUTRAL .dot--off badge carrying no warn token while the 'Updating' pill stands down, and when the endpoint recovers the next attempt succeeds and the badge goes away and computes display: none through the .banner__pill[hidden] guard (T13, 22-15-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_refresh_loop_shows_a_neutral_pill_on_failure_and_clears_on_recovery[chromium] |
| 29 | Home paints nothing outside the viewport and nothing outside its own recent-flight rows, measured in BOTH languages at 390px and at 1280px: documentElement.scrollWidth never exceeds the viewport, no element's right edge clears it, and no row's content escapes its own box (B11's fourth and last surface, quick task 260913-bjy) | ported | companion/test_browser_ux_02.py::test_home_paints_nothing_outside_the_viewport_or_its_cards[chromium-390-en] |
| 30 | no recent-flight callsign is ever starved by the time column - its box is never narrower than its own text at 320, 360, 390, 768 or 1280px in EITHER language, Home still never scrolls sideways at any of them, and at 768px the callsign and the time still share one line (quick task 260913-dgh) | ported | companion/test_browser_ux_02.py::test_recent_flight_callsigns_are_never_starved[chromium-320-fr] |
| 31 | Health's tables each fit inside their own .data-table-wrap at 390px in BOTH languages with EVERY <details> on the page forced open — the readings table is reachable only through a closed-by-default disclosure, and its wrap scrolls while documentElement.scrollWidth never moves, so no page-level assertion can see it (B12's cause on its third table, quick task 260913-cz6) | ported | companion/test_browser_ux_02.py::test_health_tables_fit_their_wraps_with_every_disclosure_open[chromium-en] |
| 32 | EVERY <details> on EVERY page opens without overflowing anything — all six authenticated pages plus the login page, at 360px, 390px and 1280px, in BOTH languages, with every disclosure on the page forced open: documentElement.scrollWidth never exceeds the viewport, nothing paints right of it, and no scroll container's content is wider than its own box (the readings-table class, which no page-level assertion can see). Each page asserts a minimum disclosure count and that at least one was closed beforehand, so a selector change makes this fail rather than silently measure nothing (quick task 260913-eab) | ported | companion/test_browser_ux_02.py::test_every_disclosure_on_every_page_opens_without_overflow[chromium-360-en] |
| 33 | every view-transition name the served stylesheet declares resolves to AT MOST one element on each of the six authenticated routes, counted from the COMPUTED value on every element of the real document — the sidebar and the page title on all six, Home's frame picture on Home only, and the declared set itself pinned so a dropped declaration fails rather than emptying the measurement. A name matching twice (two navigation landmarks share every authenticated DOM, and a bare `nav` selector reaches both) makes the browser drop the whole transition with no error anywhere, and no source scan can see it (D10/CFG-33, 23-04-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_view_transition_names_are_unique_on_every_route[chromium] |
| 34 | the cross-document view transition is genuinely OPT-OUT: its at-rule is the only one in the CSSOM, declares navigation: auto, and is nested inside a media rule whose own conditionText — read off the at-rule's parent, never from a bare matchMedia() call, which would pass with the at-rule unwrapped — evaluates FALSE in a reduced_motion='reduce' context and TRUE in a default one, so a visitor who asked for less motion never has the transition set up at all rather than having one set up and run fast (D3+D10/CFG-33, 23-04-PLAN.md Task 2) | ported | companion/test_browser_ux_02.py::test_the_view_transition_is_off_under_reduced_motion[chromium-reduced-motion] |
| 35 | the Health freshness line's <time data-relative> text ADVANCES within ~2s in a real visible tab, starting from text the server already rendered, ending on something that is no longer the server's own clock (the enhancement really did take over), carrying no raw quantity placeholder, and leaving the prefix and pill beside it untouched (D14/CFG-34, 23-05-PLAN.md Task 3; the clock-to-age half added by 23-06-PLAN.md) | ported | companion/test_browser_ux_02.py::test_the_relative_age_ticks_in_a_real_tab[chromium] |
| 36 | a page reporting itself hidden runs no ticker work at all — its age is byte-identical across ~2s, against a control proving the same age DOES move while visible — and on becoming visible again it is repainted immediately rather than after waiting out an interval (T-23-14, 23-05-PLAN.md Task 3; the visibility mechanism and its limits are stated in this check's own comment) | ported | companion/test_browser_ux_02.py::test_a_hidden_tab_does_no_work_and_catches_up_on_return[chromium] |
| 37 | with scripts blocked at 360px, in BOTH languages, the freshness line still renders exactly one <time data-relative> carrying the server's own CLOCK — derived from the element's own datetime, never the ladder's zero bucket and never any age, because nothing there can advance one — and it does NOT change over ~2s, which is what separates an intact no-JS floor from an enhancement that quietly took over (CFG-38, 23-05-PLAN.md Task 3; the frozen-zero half reversed by 23-06-PLAN.md) | ported | companion/test_browser_ux_02.py::test_the_relative_age_is_server_rendered_and_static_without_scripts[chromium-en] |
| 38 | a countdown whose instant has already passed reads the server's own translated waiting wording in BOTH languages, never an age, gains the breathing class and no warn/error/alert class at all, and that class resolves to the one animation the stylesheet defines (D14/CFG-34, 23-05-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_an_expired_countdown_reads_waiting_and_never_a_warning[chromium] |
| 39 | a Home refresh swaps the regions that changed while leaving the one holding keyboard focus untouched — asserted on NODE IDENTITY through a JS expando, not on a selector match, because a replaced node matching the same selector is exactly the defect — against a control proving another region really was swapped in the same cycle (D1/CFG-35, 23-06-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_swap_leaves_the_region_holding_focus_alone[chromium] |
| 40 | a region containing a [data-pending] element survives a refresh untouched, by node identity, while another region on the same page is swapped in the same cycle — the reconciliation rule plan 23-07 sets its marker for, proven before it has a marker to set (T-23-21, 23-06-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_swap_leaves_a_pending_region_alone[chromium] |
| 41 | a Display page with a typed-but-uncommitted edit issues ZERO requests when the same trigger that fetched on the clean page fires — counted as REQUESTS, not inferred from the DOM, because a page that fetched and then declined to swap is a different and worse behaviour — against a control proving the clean page does fetch (T-23-20/T-23-21, 23-06-PLAN.md Task 3; retargeted from the retired save bar's own gate by 27-04-PLAN.md Task 4, CFG-63) | ported | companion/test_browser_ux_03.py::test_a_dirty_settings_form_stands_the_whole_cycle_down[chromium] |
| 42 | a tab reporting itself hidden issues ZERO requests on ALL THREE pages that now run the loop — counted as requests, each against a control proving the same page and the same trigger DO fetch while visible — which is the number D-12 was written to protect and the reason three pages polling is acceptable at all (T-23-20, 23-06-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_hidden_tab_issues_zero_requests_on_all_three_pages[chromium] |
| 43 | the frame picture fades in when a NEW render arrives and does NOT animate when the same picture is swapped back in — both phases in one check, against a control proving a swap happened at all, with the class proven to resolve to the stylesheet's own fade-in block (D1+D3, 23-06-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_the_picture_fades_only_when_the_picture_changed[chromium] |
| 44 | with scripts blocked at 360px, in BOTH languages, a Display setting still saves through the fallback Save and persists to disk, with the freshness line this plan added rendering beside it — the one assertion here that would catch the Phase 22 P0 recurring (B1/CFG-38, 23-06-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_display_still_saves_with_scripts_blocked_at_360px[chromium] |
| 45 | a switch flips its aria-checked BEFORE the server answers — proven against a held request that has genuinely been issued and genuinely has no answer, with the stored value still unchanged at that instant — marks exactly one region pending while in flight, and on a 204 keeps the flip and clears the marker (D2/CFG-36, 23-07-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_switch_flips_before_the_server_answers[chromium] |
| 46 | a switch rolls its aria-checked back, clears its pending marker, leaves the stored value alone and announces the TRANSLATED generic failure in a visible toast — on a 500 AND on a network-level failure, in English and in French, each against a control phase proving the same switch DOES flip and does NOT announce on a working request (D2/CFG-36, T-23-26/T-23-27, 23-07-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_switch_rolls_back_and_announces_on_both_failure_branches[chromium] |
| 47 | a Home refresh landing while a flip is unconfirmed leaves the Frame strip untouched — by NODE IDENTITY and by the optimistic aria-checked surviving — against one control proving another region really was swapped in the same cycle and a second proving the same changed strip IS replaced once the marker has cleared, with focus deliberately moved off the strip so the focus skip cannot be what satisfies it (D1+D2, T-23-26, 23-07-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_refresh_landing_mid_flip_does_not_repaint_the_switch[chromium] |
| 48 | with scripts blocked at 360px, in BOTH languages, all THREE switches render with the server's own aria-checked, clear the 44px touch floor in both axes, submit their real form and PERSIST to disk — the assertion that would catch a control that renders and silently does nothing (D2/CFG-36, CFG-38, 23-07-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_all_three_switches_still_post_with_scripts_blocked_at_360px[chromium] |
| 49 | a detection recorded while the Flights page is open arrives at the top of the live list on the next refresh and is the ONLY thing highlighted — in both the table and the phone card list — while a row that was already there is not, nothing at all is highlighted on first load, and a refresh that brings nothing new announces nothing; the class resolves to the stylesheet's own single-run arrival animation on --motion-slow (D7/CFG-37, 23-08-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_new_detection_is_highlighted_and_an_existing_row_is_not[chromium] |
| 50 | a refresh neither unfolds the Flights table nor closes the row you opened: with focus deliberately blurred off the toggle (so the loop's focus skip cannot be what passes this) and a new detection renumbering every row below it, exactly the row that was opened is still open — by EVENT identity, not by position — and exactly one toggle still announces it (D7/CFG-37, 23-08-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_refresh_neither_unfolds_the_table_nor_closes_what_you_opened[chromium] |
| 51 | a refresh never interrupts the filter and never undoes it: with the caret in the box the loop issues ZERO requests (counted, against a control proving the same trigger does fetch with focus moved off), and the swap that then happens leaves the typed query applied — same visible rows, same live count, same input value — because the server renders the list unfiltered (D7/CFG-37, 23-08-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_refresh_never_interrupts_or_undoes_the_filter[chromium] |
| 52 | a COLLAPSED Flights detail row lets none of its own controls take focus — the deliberate display:none end state, asked as the keyboard question directly — against a control phase proving the same controls ARE reachable once the row is open, and the opening really animates grid-template-rows on a grid wrapper at --motion-fast (D3/CFG-32, T-23-32, 23-08-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_collapsed_detail_row_cannot_be_reached_by_keyboard[chromium] |
| 53 | a phone card at 360px opens from a tap on its own face away from every control, through the native disclosure it already contained, with its summary box covering the whole card and no control nested inside it — and it does the same with SCRIPTS BLOCKED, where no detail row is collapsed and the live-script class the height animation is keyed on is absent (D7/CFG-37, CFG-38, 23-08-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_a_phone_card_opens_from_a_tap_anywhere_with_and_without_scripts[chromium] |
| 54 | [data-dirty-count] ARRIVES rather than appearing, and stays silent for anything that is not a genuine change: clicking an ALREADY-CHECKED radio writes nothing (the surviving control-phase idea from the retired save-status region — MEASURED live to fire no native change at all, never reaching updateBar()); a REAL change writes the section's own name EXACTLY ONCE, read off the bar's own data-* attributes never hardcoded in English, and carries the changed-value class; and changing to a SECOND, DIFFERENT theme inside the identical data-dirty-section wrapper — a real change that resolves to the textually IDENTICAL label — writes nothing further, which is setCountText()'s own changed-text gate genuinely exercised (a same-value re-click, tried first, never reaches the listener at all and so cannot prove the gate) — a new phase this check gains over its retired predecessor (D3/CFG-32, 23-09-PLAN.md Task 3; retargeted from the retired save-status region onto the restored bar by 28-10-PLAN.md Task 2, CFG-77/CFG-78) | ported | companion/test_browser_ux_03.py::test_the_dirty_count_arrives_and_moves_only_when_the_word_does[chromium] |
| 55 | the bar's own Save persists EVERY field to disk, never only the touched one: reading the FULL on-disk config before and after a single-field (tracked_runway) save, in both languages, and asserting the two dicts differ in EXACTLY the one key touched — a STRONGER surface than the retired request-body capture, since a server that posts the whole form but only writes the touched key would still pass that check and fail this one (T-27-04-D, CFG-36's own hazard; retargeted from the request body onto disk by 28-10-PLAN.md Task 3, CFG-77/CFG-78; 27-04-PLAN.md Task 4, CFG-63; supersedes the retired Save-button relabel check, T14's deferred label, 23-09-PLAN.md Task 3/D3/CFG-32) | ported | companion/test_browser_ux_03.py::test_the_bars_save_persists_every_field_never_only_the_touched_one[chromium] |
| 56 | with scripts blocked at 360px, in BOTH languages, the fallback Save is VISIBLE with a real box and still saves to disk — B1's floor re-asserted after the bar and both its former liveness markers are retired outright (B1/CFG-38, 23-09-PLAN.md Task 3; retargeted by 27-04-PLAN.md Task 4, CFG-63) | ported | companion/test_browser_ux_03.py::test_with_no_script_the_fallback_save_is_the_only_way[chromium] |
| 57 | CFG-66: the map is gone, the radios and the photographs are not — asserted as ONE relationship rather than three separate facts: zero .runway-map elements resolve on /display, exactly RUNWAY_IDS' own count of tracked_runway radios and of .runway-card__image photographs still resolve, the runway row does not scroll the page sideways at 360px, and every runway card clears the 44px hit-target floor in ITS OWN container at 360px in BOTH themes — measured, not assumed, now that the map strip no longer provides the box (CFG-66/D-32/T-27-05-B, retiring CFG-47's three checks named in 27-05-SUMMARY.md) | ported | companion/test_browser_ux_03.py::test_the_map_is_gone_the_radios_and_photographs_remain_and_meet_their_floor[chromium] |
| 58 | Display's full rendered document height is recorded at 390px and at 360px by one instrument — proved to be pointed at the authenticated Display page (its Aspect heading AND a full THEME_IDS-sized departures radiogroup, never merely 'a page rendered'), at the width the caller asked for, and taller than the viewport — asserting NO target, because the number IS the criterion and 25-06 states in its own SUMMARY whether it is met, and no cross-width relationship either, because the obvious one (narrower cannot be shorter) was MEASURED FALSE on this page before the plan changed anything (CFG-50, 25-06-PLAN.md Task 1) | ported | companion/test_browser_ux_03.py::test_displays_page_height_is_recorded_at_both_phone_widths[chromium] |
| 59 | the theme still SAVES with scripts blocked, at 360px and in BOTH shipped languages — operated natively by field name, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way (CFG-50/D-09/CFG-85, 25-06-PLAN.md Task 4, narrowed by 30-03-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_the_theme_still_saves_with_scripts_blocked[chromium] |
| 60 | the arrivals grid still SAVES with scripts blocked, at 360px and in BOTH shipped languages — operated natively by field name, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way (seeded through the validated save_device_config() API rather than a raw file write, since theme_arriving's own None state would otherwise defeat the shared helper's stored-is-None save-floor guard) (CFG-68/CFG-85, 27-07-PLAN.md Task 2, narrowed by 30-03-PLAN.md Task 3) | ported | companion/test_browser_ux_03.py::test_arrivals_still_saves_with_scripts_blocked[chromium] |
| 61 | arrow-keying the departures palette's native radiogroup (no click at all) still moves the checked selection, and the live preview still follows it via theme-preview.js's own delegated change listener, settled fully opaque - the one property _keying_the_strip_selects_scrolls_into_view_and_moves_the_preview proved that survives a static wrapping grid with no strip/scroll/pager to key through (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_03.py::test_keying_the_palette_moves_the_preview[chromium] |
| 62 | hovering or keyboard-focusing an unchecked palette chip previews that chip's own theme in the ONE live preview, writing NO radio's checked state and NO value on disk; moving the pointer/focus away reverts the preview to the checked chip's own src; hovering straight from chip A to chip B never passes through the checked selection's own src in between (observed via a live MutationObserver on the preview's src attribute), settling on B; and the value on disk is unchanged start to finish - the genuinely new interaction this phase adds, with no existing hover/focus precedent to re-key (30-RESEARCH.md Pitfall 4, _ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 1+2, CFG-85) | ported | companion/test_browser_ux_03.py::test_the_preview_follows_hover_and_focus_and_selects_nothing[chromium] |
| 63 | with scripts blocked, in BOTH languages, at 360px: all 4 usage rows carry their own <summary>; every registry theme's radio (theme/theme_arriving/calendar_theme_id/rule_theme_id) is present in the DOM at full registry size regardless of which row is open; a REAL pointer click on a closed row's own <summary> opens it and closes the previously-open sibling (the native grouped <details name="aspect-rows"> mechanism); and a palette selection made INSIDE the row the visitor just opened themselves reaches disk, read back via device_config.load_device_config(), with the restore leg putting the old value back - CFG-85's own "every row open" wording is unachievable alongside the grouped, mutually-exclusive accordion the developer already approved, and this check's own comment states that discrepancy plainly rather than narrowing the claim (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_04.py::test_the_accordion_is_operable_and_saves_with_scripts_blocked[chromium] |
| 64 | 30-UI-SPEC.md's Touch Targets table, MEASURED (never declared) in each control's own container, in both UI themes, at the 360px contract floor: the open row's first and last .palette-chip, the usage-row's own <summary>, the arrivals row's leading "Same as departures" option, and the nested rule-add disclosure's own <summary> all clear 44px; the palette grid never scrolls horizontally, the page itself never overflows sideways, and the swatch paints visibly distinct from its own surrounding chip surface in both themes (_ASPECT_REPIN_LEDGER, 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_04.py::test_the_palette_meets_its_floors_at_360px_in_both_themes[chromium] |
| 65 | the no-JS floor still SAVES TO DISK after the gate simplifies to the plain .js rule (CFG-64) — tracked_runway operated natively, submitted through the real form, re-read FROM DISK after a fresh GET, in BOTH shipped languages, at 360px, restored as the last act (the same field and mutation 25-03's own M20 recorded) — and the data-static-save-fallback submit is present and VISIBLE on that scripts-blocked page AFTER the save, so a rendering can never stand in for it (CFG-64, 27-03-PLAN.md Task 3) | ported | companion/test_browser_ux_04.py::test_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies[chromium] |
| 66 | the bar's own settle contract: changing a field REVEALS the bar, names the changed section, updates the field's own DOM value, and leaves DISK UNTOUCHED (the bar means unsaved, stronger than anything the retired check asserted); clicking Enregistrer causes a real navigation; and after it lands the field, the bar (now HIDDEN) and disk all agree on the requested value — three surfaces, on different surfaces than before (CFG-63/CFG-71/CFG-77/CFG-78, 27-04-PLAN.md Task 4; retargeted onto the restored bar by 28-10-PLAN.md Task 2, which also retires the CFG-63 'no save button visible' clause this check used to assert) | ported | companion/test_browser_ux_04.py::test_the_bar_settles_the_field_disk_agree_and_the_bar_hides[chromium] |
| 67 | a value the server's own validation rejects (wake_interval_s below its floor) re-renders the SAME page with the field's OWN inline error, programmatically associated via aria-describedby and naming the field; echoes the user's rejected input back into the field rather than the on-disk value (D-07's echo rule); leaves disk UNCHANGED; and raises NO .quick-toast at all on this path — the explicit negative that keeps this failure surface and quick-switch.js's own toast from merging (CFG-63/CFG-71, 27-04-PLAN.md Task 4; retargeted from the toast onto the native inline-error path by 28-10-PLAN.md Task 3, CFG-77/CFG-78) | ported | companion/test_browser_ux_04.py::test_a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched[chromium] |
| 68 | the bar's own [data-dirty-count] names which section(s) actually changed, built from the bar's own data-dirty-* attributes plus each section wrapper's own label — never hardcoded English/French, never merely 'the bar is visible' or 'the text is non-empty': a single changed Runway field reads exactly that wrapper's own label plus the changed-suffix, and a second, different-section change (Quiet hours) reads the two-item join with Runway BEFORE Quiet hours in BOTH click orders — the reversed-order pass is what proves DOCUMENT order rather than click order, since dirtySectionLabels() walks the document and Runway's own wrapper precedes Quiet hours' on Display regardless of which the visitor touches first; run in both site languages (CFG-77, 28-11-PLAN.md Task 1) | ported | companion/test_browser_ux_04.py::test_section_naming_reflects_the_fields_actually_changed_in_document_order[chromium] |
| 69 | a real Annuler click restores every surface, read off the RESULTING DOM: the theme chip's checked state is back to the original, the live preview <img>'s resolved src is back to the ORIGINALLY-selected theme's own (never the discarded one) — proving window.SkyPaneLivePreview.refresh() actually ran, since form.reset() fires no change event — and the quiet-hours dial's decoded arc and its handles' aria-valuenow are back to the pre-edit window, proving 28-08's own explicit deferred repaint of value-controls.js's repaintAll() landed; both edits are confirmed to have actually MOVED both surfaces before Cancel is ever clicked, and every post-Cancel read waits for 28-08's setTimeout(fn, 0) deferred tick rather than reading synchronously after the click; asserting that refresh()/repaintAll() was CALLED is explicitly not acceptable and this check never does — the dial-repaints-for-free claim CONTEXT.md made is false by specification (already refuted in writing by 28-08) and this check does not re-litigate it (CFG-77, 28-11-PLAN.md Task 2; re-pointed to .palette-chip by 30-08-PLAN.md Task 2, CFG-85) | ported | companion/test_browser_ux_04.py::test_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom[chromium] |
| 70 | THE real proof, not a grep: ONE probe renders BOTH settings pages (Display and Device) in one session, addresses every settings-card title by STRUCTURAL POSITION rather than by class name, reads its getComputedStyle font-size/font-weight/font-family, and asserts the combined set across both pages has cardinality 1 — CFG-72's literal wording. Fails naming the empty side if either page contributes zero titles; every Device title must be one of the four named cards (Diagnostic LED, Wake interval, Notifications, Manual refresh) and the Poll card's own title specifically must be among them — proving the probe's reach extends to the one .page-section card, not just the three .theme-status ones — while a genuinely SMALLER set (one Device card removed from `builders`) still passes, proving the comparator is not secretly counting; the failure message names the offending page, the offending title's text and BOTH triples. Supersection intro headings (.section-intro > h2) are excluded structurally, deliberately — a different, generically-worded tier (27-06-PLAN.md Task 1, SKILL.md's three-rung heading ladder), not an inconsistency this check should assert away. Both themes exercised via _set_ui_theme(), at the 360px floor (CFG-72, 28-04-PLAN.md Task 2) | ported | companion/test_browser_ux_04.py::test_a_settings_card_title_renders_identically_on_both_settings_pages[chromium] |
| 71 | exactly ONE submit-shaped control on the whole settings page resolves its own .form.id to config_page.SETTINGS_FORM_ID, on both /display and /device, in both site languages — resolved via the browser's OWN .form property, never a count of <button occurrences in the HTML string and never a hand-maintained allow-list; covers input[type=submit], button[type=submit] AND a bare <button> with no type attribute (the HTML default IS submit); the bar's native type="reset" Cancel is deliberately excluded (form-associated but not submit-shaped, and it saves nothing); the one settings-form control must carry data-static-save-fallback and be a descendant of [data-dirty-bar]; the failure message NAMES every collected control as a tagName/type/form-id/text tuple so a regression says WHICH control drifted; and the complement is asserted too — calendar/rules/notifications-test/quick-LED/quick-switch controls, whichever this scope renders, each resolve to a NON-settings-form id (CFG-78, 28-09-PLAN.md Task 1) | ported | companion/test_browser_ux_04.py::test_exactly_one_submit_shaped_control_resolves_to_the_settings_form[chromium] |
| 72 | the runway radios' cross-tree form="settings-form" wiring drives the SAME bar-appears -> Enregistrer -> persisted-to-disk path every natively-nested control does — closing the path CFG-74(c) named before it was superseded, now against the real POST instead of the retired fetch: selecting a runway radio (rendered OUTSIDE the settings form) reveals the bar naming exactly its own Runway/Piste label, a real Enregistrer navigation writes tracked_runway to disk, and a reload shows the radio reflecting the saved value — both site languages (CFG-74(c)/CFG-78, 28-09-PLAN.md Task 1) | ported | companion/test_browser_ux_04.py::test_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end[chromium] |
| 73 | with scripts blocked at 360px, an artwork file chosen through the native <input type="file"> and submitted through the fallback panel's own form is STORED (read back off the real state directory, never off the page — a rejected upload redirects to a page that looks like success) and SERVED back by the illustration route as an image at illustration_normalize.ILLUSTRATION_TARGET_SIZE; and the drop zone beside it measures zero height and holds zero focusable descendants with scripts blocked while occupying a real box with them on (CFG-51/D-09, 25-07-PLAN.md Task 3) | ported | companion/test_browser_ux_04.py::test_artwork_uploads_and_is_served_with_scripts_blocked[chromium] |
| 74 | the SAME source file stored byte-identically whether it was PICKED or DROPPED (with the stored file deleted between the two uploads, so a drop that never reached the server could not pass on the picked file left behind), the preview decoding to the source's own 1200x300 through a data: URL (a blob: one is blocked by this app's own CSP); and the FLOOR measured against the INPUT rather than against a message — zero files, a wrong type, several at once and an oversized file each assign nothing, each say something, and each say something different, while a synthetic drop changes nothing at all and the drag-over state is sampled visible BETWEEN dragOver and drop (CFG-51/D19, 25-07-PLAN.md Task 3) | ported | companion/test_browser_ux_04.py::test_dropped_and_picked_files_are_stored_identically[chromium] |
| 75 | the artwork drop zone clears the 44px target by real hit-testing in ITS OWN container at 360px, the Airlines page does not scroll sideways there, the preview box reserves illustration_normalize.py's own aspect ratio (by getBoundingClientRect, never clientWidth) BEFORE any image exists with the <img> still hidden, and the paint is a FLOOR not a ceiling: the hint text is never the canvas colour, the preview frame is never its own fill, and the whole zone paints differently in the two themes (CFG-51/CFG-52, 25-07-PLAN.md Task 3) | ported | companion/test_browser_ux_04.py::test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes[chromium] |

### Part 01 (plan 33-21)

- Rows 1-18 flipped: 1 `deleted` (rubric code R, the self-referential
  coverage-gap ledger guard), 17 `ported`.
- New module: `companion/test_browser_ux_01.py` (18 collected node ids —
  row 8's check parametrizes over `en`/`fr` since neither language
  compares against the other, so it counts as one ledger row pointing at
  two node ids).
- 13 of the 17 ported checks share one module-scoped, read-only seeded
  server; the 4 that persist a real setting through the UI (Display/
  Device reveal-and-persist, the bar's hide/reveal/save cycle, the Frame
  strip switch) each get their own function-scoped server.

### Part 02 (plan 33-22)

- Rows 19-37 flipped: 19 `ported`, 0 `deleted`.
- New module: `companion/test_browser_ux_02.py` (43 collected node ids —
  7 rows parametrize over independent iterations with no cross-comparison,
  each row pointing at its primary node id, the rest named here):
  - row 19 (both dialogs): `[chromium-history]` / `[chromium-airlines]`.
  - row 27 (dirty bar clearance): `[chromium-390x844-en]` /
    `[chromium-390x844-fr]` / `[chromium-1280x900-en]` /
    `[chromium-1280x900-fr]`.
  - row 29 (Home overflow): `[chromium-390-en]` / `[chromium-390-fr]` /
    `[chromium-1280-en]` / `[chromium-1280-fr]`.
  - row 30 (recent-flight starvation): 10 combos over
    `VIEWPORT_WIDTHS_ALL` (320/360/390/768/1280) x (`fr`/`en`), primary
    `[chromium-320-fr]`.
  - row 31 (Health disclosure-gated tables): `[chromium-en]` /
    `[chromium-fr]`.
  - row 32 (every disclosure on every page): 6 combos over
    `VIEWPORT_WIDTHS_RESPONSIVE` (360/390/1280) x (`en`/`fr`), primary
    `[chromium-360-en]`.
  - row 34 (view-transition reduced-motion opt-out): `[chromium-reduced-
    motion]` / `[chromium-no-preference]`.
  - row 37 (no-JS freshness floor): `[chromium-en]` / `[chromium-fr]`.
- 18 of the 19 ported checks share one module-scoped, read-only seeded
  server; the login-lockout check (row 24) drives the process-global
  LoginThrottle to its own limit and gets its own function-scoped
  `make_app_server`, so it cannot lock out any other check sharing a
  server in this module.


### Part 03 (plan 33-23)

- New module: `companion/test_browser_ux_03.py`, 25 checks (rows 38-62),
  all `ported`, 0 `deleted` — every check in this slice already asserted
  behaviour (real HTTP requests counted through `page.on("request", ...)`,
  DOM state read live, or disk state read through `device_config`/
  `history_db`), so no rubric-C/S/P/R deletion applied to any row.
- 14 read-only checks (rows 38-43, 51-54, 57-58, 61-62) share one
  module-scoped, read-only seeded `server` fixture. 11 checks that
  persist a real setting or write a new database row get their own
  function-scoped `make_app_server` server: the Display/fallback-Save/
  theme/arrivals scripts-blocked saves (rows 44, 56, 59, 60), all four
  Frame-strip switch checks (rows 45-48), the bar's own every-field save
  (row 55), and the two Flights checks that write a new `runway_events`
  row directly through `history_db.record_runway_event()` (rows 49-50).
- None of the 25 checks were parametrized: each one either drives a
  single named interaction/procedure or an internal loop whose own final
  assertion compares values ACROSS iterations (both languages must agree
  on the translated failure copy, both scripts-blocked switches persist
  to the SAME field, the height recorded at two widths is one
  instrument's own two readings) — splitting any of these into
  independent parametrized cases would need one parametrized run to
  re-derive data another run depends on, which 33-MIGRATION-RULES.md
  section 2 forbids under xdist.
- The two Frame-strip request-holding checks (rows 45, 47) and the D1
  swap-rule checks (rows 39-40, 43) share module-level helpers local to
  this file only (`_force_refresh`, `_count_document_requests`, `_mark`/
  `_marked`/`_dirty_the_region`, `_hold_fetch`/`_fetch_was_issued`/
  `_release_fetch`/`_switch_state`, `_record_a_new_detection`/`_row_ids`/
  `_highlighted`) — grepped whole-file before this plan started; no later
  part of this chain calls any of them, so they were not promoted into
  `companion/test_browser_ux_helpers.py`.
- `THEME_PREVIEW_SEL = ".theme-live-preview__image"` is defined in BOTH
  this new module and the still-legacy `companion/test_browser_ux.py`:
  part 04's own remaining checks (rows 63-75) still read it, so the
  legacy file keeps its own copy rather than losing the definition when
  this plan's checks were cut from `main()`.
- The shrunk legacy harness's `EXPECTED_CHECK_COUNT` moved from 38 to 13
  (rows 63-75 remain); five now-unused imports (`i18n`, `layout`,
  `history_page`, `history_db`, `VIEWPORT_DESKTOP`, `VIEWPORT_PHONE`,
  `_display_page_height` — only this slice's own checks used them) were
  removed from the legacy file in the same commit.

### Part 04 (plan 33-24) — CHAIN CLOSED

- Rows 63-75 flipped: 13 `ported`, 0 `deleted` — every check in this
  final slice already asserted real behaviour (a disk read through
  `device_config`/`illustrations`, a live DOM/computed-style read, a real
  HTTP navigation, or a byte comparison of a stored file), so no
  rubric-C/S/P/R deletion applied to any row. **75/75 baseline checks now
  accounted for (74 `ported`, 1 `deleted`, 0 `pending`).**
- New module: `companion/test_browser_ux_04.py` (13 collected node ids,
  none parametrized — every check drives a single named
  interaction/procedure or an internal loop whose own final assertion
  compares values ACROSS iterations, the same reasoning 33-23 already
  applied to its own 25 checks).
- 6 read-only checks (rows 64, 67, 68, 69, 70, 71) share one
  module-scoped, read-only seeded `server` fixture. 5 checks that persist
  a real setting each get their own function-scoped `make_app_server`:
  the scripts-blocked accordion save (63), the no-JS `tracked_runway`
  floor (65), the bar's own settle-and-hide save (66), and the runway
  cross-tree save (72). The artwork drop-zone family (73-75) needs a
  DIFFERENT seed (a `needs-artwork` manual resolution entry
  `seed_state_dir()` never creates on its own): the two checks that
  actually upload a file (73, 74) each get a fresh function-scoped server
  and their own `tmp_path` fixture files (never `tempfile.mkdtemp()`);
  the one check that only measures the zone at rest (75) shares a
  second, dedicated module-scoped `artwork_server` fixture built from the
  same seed.
- `companion/test_browser_ux.py` is DELETED OUTRIGHT (`git rm`): its
  `EXPECTED_CHECK_COUNT`, `check()`/`main()`, `Harness` alias and every
  remaining helper leave the tree with it. Grepped the whole repo
  (imports, `open(`/`ast`/`Path(` references, string mentions in
  test-support, conftest, the shim, and other tests) before deleting:
  every remaining reference to the filename is prose in a comment or
  docstring (13 hits across `companion/pages/config_page.py`,
  `companion/draw.py`, `companion/test_status_pages.py`,
  `companion/test_config_page_02.py`, `companion/test_config_page_04b.py`,
  and the two sibling browser modules' own module docstrings), plus the
  frozen `ORIGINAL_COMPANION_HARNESSES` history tuple in
  `test-support/skypane_test_support.py` (used only by that module's own
  `legacy_companion_harnesses()`, which derives its answer from disk —
  no hand-edited list needed updating).
- Full browser suite (`health_drawings`, `quiet_wake`, `browser_ux_01`
  through `_04`, `browser_policy`), `SKYPANE_REQUIRE_BROWSER=1`, real
  Chromium, `-n auto`: **128 passed, 0 skipped, 0 failed, in 101.03s**
  wall time — against the 202s serial baseline this plan's own
  `must_haves` named.
- `companion_app_server.LegacyHarness` (the class `test_browser_ux.py`
  imported as `Harness`) now has exactly ONE remaining consumer in the
  whole repo: `companion/test_app_server_fixture.py`'s own
  `test_legacy_harness_still_matches_original_behaviour`, a meta-test
  whose own docstring states its purpose as keeping `LegacyHarness`
  compatible "while a still-legacy script harness" exists elsewhere.
  `companion/test_status_pages.py` (the one companion harness still
  legacy after this plan) uses its OWN local `Harness` class, never
  `LegacyHarness` — confirmed by grep, zero `LegacyHarness`/
  `companion_app_server` references in that file. For the closing plan
  (33-32, per this chain's own note in 33-24-PLAN.md): once
  `test_status_pages.py`'s own chain closes too, `LegacyHarness` and its
  one remaining meta-test consumer can both retire together.


## Closing parity

Assembled by `33-ledger-check.py --assemble` on 2026-09-25 (plan 33-33), after
`33-ledger-check.py --all` exited 0 with 0 pending rows in all 9 fragments. The
assembler printed `phase33_total=1250`.

### Per harness

| Harness | Baseline | Addendum (commits) | Ported | Deleted |
| --- | ---: | --- | ---: | ---: |
| `companion/test_contrast_check.py` | 49 | 0 | 49 | 0 |
| `companion/test_i18n.py` | 24 | 0 | 20 | 4 |
| `companion/test_view_pages.py` | 169 | 0 | 169 | 0 |
| `companion/test_config_page.py` | 276 | 0 | 274 | 2 |
| `companion/test_companion_app.py` | 320 | 0 | 319 | 1 |
| `companion/test_status_pages.py` | 317 | 0 | 313 | 4 |
| `companion/test_browser_ux_health_drawings.py` | 11 | 0 | 11 | 0 |
| `companion/test_browser_ux_quiet_wake.py` | 9 | 0 | 9 | 0 |
| `companion/test_browser_ux.py` | 75 | 0 | 74 | 1 |
| **Total** | **1250** | **0** | **1238** | **12** |

There are no `33-BASELINE/*.addendum.txt` files, so there are no addendum checks. The Phase 37
companion tests that landed during this phase (`test_login_throttle.py`,
`test_post_origin.py`) were written natively in pytest and need no ledger row (33-CONTEXT.md,
"Coordination with Phase 37").

### Deleted rows by rubric code

| Code | Count | Rows |
| --- | ---: | --- |
| B | 0 | |
| D | 0 | |
| C | 1 | status_pages 291 (a stylesheet header comment) |
| J | 0 | |
| S | 8 | i18n 10, 11, 23, 24; config_page 196; status_pages 89, 185, 285 (source-text scans with no observable behaviour; each names the behaviour test that now covers the concern) |
| P | 1 | status_pages 154 (plan-history prose in a JS header and a `.planning` CONTEXT.md) |
| R | 2 | config_page 1, browser_ux 1 (`_ASPECT_REPIN_LEDGER` self-referential bookkeeping) |
| T | 0 | |
| **Total** | **12** | |

Every deleted row's reason starts with a rubric code. The plan's check (grep the rows whose
disposition cell is `deleted`, then count those whose next cell does not start with
`B|D|C|J|S|P|R|T:`) prints 0.

### Arithmetic against the audit's 2018

- Phase 32 ledger (server + stub-server): **769** (`32-MIGRATION-LEDGER.md`, "Grand totals: 769
  baseline checks, 769 ported, 0 deleted").
- Phase 33 baseline: **1250** (`33-BASELINE/INDEX.md`, captured at `3655cc9`).
- 769 + 1250 = **2019**, compared with the audit's **2018** (`.planning/audits/2026-09-23-code-audit.md`,
  measured at `2808f8a`). Difference: **+1**.
- The +1 is commit **`17d5bc7`** (Phase 32 continuation, plan 32-11 Task 1, TST-03). It added
  exactly one `check(...)` to `companion/test_companion_app.py`: "the first poll trigger's
  run_once() was served by the fake ADS-B providers (adsbfi and adsblol called, no live
  network)". It raised that file's effective `EXPECTED_CHECK_COUNT` from 319 to 320 after the
  audit had measured its baseline.
- Verified against git on 2026-09-25:
  - `git log --oneline 2808f8a..3655cc9 -- 'companion/test_*.py'` lists only `320a642` and
    `17d5bc7`.
  - `git show 17d5bc7 -- companion/test_companion_app.py` adds one `check(` and the line
    `EXPECTED_CHECK_COUNT = 320`.
  - The last effective `EXPECTED_CHECK_COUNT` of each of the 9 harnesses at `2808f8a` (audit)
    vs `3655cc9` (capture) is 49/49, 24/24, 169/169, 276/276, **319/320**, 317/317, 11/11, 9/9
    and 75/75. The audit-time companion sum is 1249, and 769 + 1249 = 2018 exactly.
- So all 2018 audit checks are accounted for, plus 1 "added after audit baseline" check
  (`17d5bc7`, companion_app row 288, ported as
  `companion/test_companion_app_05.py::test_poll_trigger_cooldown_sequence`). There are 0
  Phase 37 addendum checks.

### Node ids

- **1238** ported rows map to **1219** distinct pytest node ids. Some legacy checks were merged
  into one test, and parametrised ids count individually.
- `comm -23` of those 1219 ids against `pytest --collect-only -q` (run 2026-09-25) is empty, so
  every ported target is a live, collected test.
- Collected on 2026-09-25: **2593** tests in the whole suite, **1669** under `companion/`, and
  **126** of those are `[chromium]` browser tests.

## CI evidence

The green run is GitHub Actions CI run `36091447937` on PR #127. It checked head `667f6e6`, job "Lint, test, coverage, attribution", on Ubuntu with CPython 3.14.7 and running as a non-root user. In the run:

- The pytest summary line is `================ 2598 passed, 73 warnings in 324.25s (0:05:24) =================`.
- No test was skipped. The summary has no skipped count and the log has no `SKIPPED` line. Because the runner is non-root, the 5 `requires_non_root` tests ran too.
- **127** `[chromium]` browser tests passed. That is the number collected at this commit, and every one of them passed on the runner:
  - `SKYPANE_REQUIRE_BROWSER=1` is set;
  - the Chromium headless shell was installed by the "Download the Chromium headless shell" step;
  - the log lists the slowest `[chromium]` calls among the passed tests.
- The coverage summary is `TOTAL 9839 651 93%`, which is `Required test coverage of 93.0% reached. Total coverage: 93.38%`. That matches the 93.35% measured before the migration and the 93.38% non-root measurement in 33-33.
