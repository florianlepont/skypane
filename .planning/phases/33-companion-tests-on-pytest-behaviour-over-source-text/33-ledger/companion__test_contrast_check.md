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
