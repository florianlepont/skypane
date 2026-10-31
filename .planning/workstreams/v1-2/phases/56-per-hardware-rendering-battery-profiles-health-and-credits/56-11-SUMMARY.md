---
phase: 56
plan: 11
subsystem: companion
tags: [themes, hardware-profile, display-page]
requires: [56-02, 56-07]
provides: [profile-filtered theme picker]
key-files:
  modified: [companion/settings/look.py]
  created: [companion/test_theme_picker_profile.py]
metrics:
  tasks: 1
  completed: 2026-10-30
---

# Phase 56 Plan 11: Theme picker filtered by profile inks Summary

The Display page theme pickers now offer only `themes_for_inks(profile_for(device).inks)`; unsupported combinations render as the existing disabled gap cells with REASON_NO_THEME.

## What changed
- `companion/settings/look.py`: `offered_theme_ids(device=None)` (request device, never raises); `_cells`, `resolve`, `gap_reason`, `look_table_html`, `look_model_json` take an optional `theme_ids` (default: whole registry for the pure helpers, the request device's offered set for the table and script model). A combination the registry has but the profile omits reports REASON_NO_THEME. Plain-paper option is omitted if not offered.
- `form_post` validation untouched: stored/posted ids validate against the full registry.
- No new strings, so no i18n changes (existing REASON_NO_THEME is bilingual).
- Commit: ebc7c91e.

## Verification
- companion suite: 3596 passed, 561 skipped (browser tests skip: no Chromium here); render_baseline unchanged (legacy HTML equal).
- ruff on touched files, comment-history, mypy, function-size pass.
- Repo-wide `ruff check companion server` reports 1 error in a concurrent plan's file (56-08 test, unused `test_unknown_state_rejected`); out of scope.

## Deviations
None. Note: the registry has 18 themes, not 16 as the plan text says; the tests do not hard-code a count.

## Notes
Theme previews still show the portrait sample (out of scope). The script model now carries only offered cells so the look sheet disables unsupported combinations with the same reason.

## Self-Check: PASSED
