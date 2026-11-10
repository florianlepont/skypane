---
phase: 62-plane-screen-redesign
plan: 11
subsystem: companion-personalisation
tags: [companion, layout, pairing-picker, i18n]
requires: [62-02, 62-10]
provides:
  - Layout view in the Personalisation tab (route /display/layout) with five layout cards and previews
  - five pairing cards replacing the eighteen-theme picker for frames on a giant layout
  - form_post.resolve_layout wired into the settings save
affects: [companion/pages/personalisation_cards.py, companion/pages/config_page.py, companion/settings/look.py]
key-files:
  created:
    - companion/settings/layout_picker.py
    - companion/test_personalisation_layout.py
    - companion/test_browser_personalisation_layout.py
  modified:
    - companion/pages/personalisation_cards.py
    - companion/pages/config_page.py
    - companion/settings/form_post.py
    - companion/settings/look.py
    - companion/i18n_fr/look.py
    - companion/ui_base.py
    - companion/layout.py
    - companion/routes.py
    - companion/static/style.css
decisions:
  - "The pairing filter is a new look.offered_pairing_ids(); offered_theme_ids() is unchanged, so the special-look rule form and the calendar look keep all 18 themes"
  - "Giant layouts render only the shown type's pairing cards (plus a Same as departures radio on Arrivals); no inline sheet, so the picker script stays inactive and the cards work without scripts"
  - "The look views follow the saved layout; the layout itself is saved from its own view"
requirements-completed: [PSR-04, PSR-06]
completed: 2026-11-09
---

# Phase 62 Plan 11: Companion layout view and pairing picker Summary

Owners pick classic, A, B, C or A with the diagonal band per frame from a new Layout view next to the theme, and a frame on a new layout is offered five pairing cards (grey, light blue, light red, light yellow, white) for departures and for the arriving colour, in English and French.

## Phase 61 check

Phase 61 is present on the branch (summaries 61-01 to 61-16 plus the merged round 7 and 8 commits touching `personalisation_cards.py` and `look.py`). The Personalisation tab already had the navigation, `look-pick` cards and inline picker the plan expects, so I adapted to that structure. Nothing was rebased or merged.

## Tasks

1. Layout view, form handling and persistence: new `VIEW_LAYOUT` at `/display/layout` (nav entry after Arrivals, `icon-picture`), `layout_picker.layout_view_html` radio cards using the existing `runway-card look-pick__card` idiom with the plan 10 preview route, `form_post.resolve_layout` (allow-list, value never echoed), `_FIELD_VIEWS["layout"]` so a rejected value redraws the Layout view, the `layout` kwarg saved through the unchanged `save_device_config`. The section carries the dirty-section attribute. No new custom properties or accent consumers; a few plain CSS rules only.
2. Pairing picker and strings: `layout_picker.pairing_view_html` and `look.offered_pairing_ids()`; a stored theme that is not a pairing (green, black, band) shows `pairing_for_theme(...)` checked while the stored value is untouched until a different card is saved. French strings in `companion/i18n_fr/look.py`; browser test written.

Commits: 3c21eb3 and 401cbf6 (see deviation 1), befd857 (existing tests pinned to classic, counts and baseline), 3992ac0 (final short help copy and layout tests).

## Deviations from Plan

**1. [Process] My work in progress was swept into other commits.** Another process committed my working tree as `3c21eb3 wip(62-11)` and again inside `401cbf6 fix(62-01)` (which also changed `server/pairings.py`, not by me). The code is on the branch and verified; the commit boundaries do not match the two tasks. `pairing_for_theme` still maps the green and black themes to grey after that change.

**2. [Rule 1] Existing tests assumed the classic picker.** Default layout is B, so any frame without a stored layout now gets pairing cards. Render contexts and seeds that assert the eighteen-theme picker (`test_personalisation_page.py`, `test_display_looks.py`, `test_config_page_01/03/05`, `test_config_page_helpers.CALENDAR_BASE_CTX`, `test_companion_app_04.py`, the render snapshot seed) now set `layout="classic"`. Counts were updated for the extra view (`test_route_table.py`, `test_device_routes.py`, `test_access_matrix.py`, dirty-section order) and `companion/testdata/render_baseline.json` was regenerated (new nav link, new route). No assertion was weakened.

**3. [Rule 3] `offered_theme_ids()` not made layout-aware.** The research suggested it as the filter point, but it also feeds the special-look rule form and the calendar look, which keep every theme. A separate `offered_pairing_ids()` (same hardware-profile filter) is used for departures and arrivals only.

**4. [Rule 1] Help text shortened.** The editorial-floor test caps a section caption at 12 words; the repaint-timing, pairing and arrival-nudge lines were cut to fit in both languages.

## Verification

- `companion` suite: 6165 passed, 2437 skipped (browser tests and root-permission tests cannot run here).
- New served-HTML tests: `companion/test_personalisation_layout.py` (27) cover save and reload of `a_diagonal`, bogus layout rejected and not echoed, foreign-origin post not saved, another user refused, no other setting changed, five pairing cards per giant layout, arrivals nudge, classic picker unchanged, stored `band_green_light` on layout B shows grey checked and the config file bytes unchanged after a GET, English and French.
- `companion/test_browser_personalisation_layout.py` (picks layout C, saves, reloads, selected; pairing pick on a B frame; English and French) was written but could not be executed here (no Playwright browser). It needs a CI run.
- ruff, mypy list, function-size gate, comment-history guard, `server/test_pairings.py`: clean.

## Known Stubs

None.

## Notes for the owner

- On a giant layout the large live picture and the three-axis inline picker are not shown; the cards (each a small layout-aware preview) are the picker.
- Saving any form from a Departures view on a frame whose stored theme is not a pairing posts the shown (mapped) pairing; the stored theme changes only if the owner saves from that view.

## Self-Check: PASSED
