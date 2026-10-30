---
phase: 51-per-device-config-image-and-state
plan: 10
subsystem: companion
tags: [timezone, quiet-hours, poll, device-scope, i18n, baselines]
requires: [51-06, 51-07, 51-02, 51-08, 51-09, 51-11]
provides:
  - Time zone select in the quiet-hours card with atomic validation (resolve_timezone)
  - Zone clause in the dial readout for a non-Paris zone
  - Device-aware Poll section (scope sentence, unsupported state)
  - Prefix-aware settings, colour-rule add and delete forms
  - Regenerated Display baselines (new field only)
affects: [51-12, 51-13]
key-files:
  modified:
    - companion/settings/quiet_hours.py
    - companion/settings/form_post.py
    - companion/settings/rules.py
    - companion/pages/config_page.py
    - companion/app.py
    - companion/i18n_fr/display.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
    - companion/test_device_settings.py
    - companion/test_device_poll.py
    - companion/test_i18n.py
requirements-completed: []
completed: 2026-10-30
---

# Phase 51 Plan 10: Time zone field and device-aware Poll section Summary

A device's time zone is set from its own Display page, next to quiet hours, validated atomically; the Poll section and the settings and colour-rule forms act on the selected device. FLT-01 / FLT-02 are intentionally NOT marked complete.

## Commits
- 4470f59 feat(51-10): per-device time zone field with atomic validation
- 607e708 feat(51-10): device-aware Poll section and prefix-aware rule forms

## What changed
- `quiet_hours.py`: curated ten-zone table (Paris first), `timezone_field_html` (label, native `<select form="settings-form">`, helper line, error state), offsets computed at render from `time.time()` and `zoneinfo` (plain text, never client input), an unlisted stored zone appended as one extra last option, `timezone_readout_clause` appended as static trailing text in the dial readout for a non-Paris zone. The field is the last element of the card, so the dirty bar counts it through the card wrapper (the script matches fields contained in the `data-dirty-section` wrapper; the attribute is not repeated on the select, which would double count).
- `form_post.resolve_timezone(form, errors, current)`: absent or equal to the stored zone -> not forwarded (the file is never rewritten for it, and Paris never adds the key); otherwise the value must be in the curated list and known to the host database, else the field error is noted and the whole POST is refused before any write. Runs last in the existing stop-at-first-FAILED sequence.
- `app.py`: the rejected-save re-render gets an error toast ("Time zone not saved ... Nothing in this save was applied.") through a new optional `flash_html` argument of `_page_shell_for`; the select always shows the stored zone.
- `rules.py`: `poll_trigger_section(cooldown_remaining, device=None, device_count=1)`; form action through `device_scope.scoped`; one caption element (scope sentence appended inside it for several devices, name escaped; replaced by the refusal sentence and a `disabled aria-disabled="true"` button for an unsupported screen type, no helper paragraph). Colour-rule add and delete actions go through `scoped(..., "POST")`; `config_page` scopes the settings form action.
- English and French strings in `i18n_fr/display.py` (timezone label, helper, errors, readout clause, ten labels, two poll captions).

## Baseline regeneration (sole owner)
Regenerated with `PYTHONPATH=.:test-support:companion server/.venv/bin/python3 test-support/companion_render_snapshot.py --write` after Task 1. Diff: 8 entries changed, all `/display` (and `/display?flash=saved`) in en/fr x light/dark; 48 page keys and 56 unauthenticated entries otherwise identical. For each changed entry, removing the new `<div class="quiet-timezone">...</div>` block from the new body reproduces the old body exactly, so the only change is the added field. Task 2 left the baseline untouched (single-device markup byte-identical).

## Deviations from Plan
1. **[Rule 3] Helper line is not `.section-caption`**: an existing guard pins exactly one `section-caption` per settings card ("one section, one caption"). The helper uses `text-label quiet-timezone__helper` with the same muted colour declaration (one CSS rule, no new token). The guard stays unweakened.
2. **[Rule 3] Pinned test updated deliberately**: `companion/test_i18n.py` `_UNCHANGED_IN_FRENCH` gained three cognates (`display.timezone_opt_martinique`, `_guadeloupe`, `_mayotte`) spelled identically in French. No other existing test needed a change; the card-order and Display-field pins held as they are.
3. **[Rule 3] `companion/app.py` and `companion/static/style.css`** were edited though not in the plan's file list (toast on the rejected re-render; layout rule `.quiet-timezone`, no token or keyframes).
4. French poll strings were added in the Task 2 commit (not Task 1) so that each commit passes the orphan-translation guard.
5. `resolve_timezone` takes the stored zone as a third argument (the plan sketched two) so an unlisted stored zone can be re-saved.

## Verification
- `pytest companion server stub-server test-support scripts` (browser files excluded, `-n 6`): 4288 passed, 12 skipped.
- `companion/test_device_settings.py` (32), `companion/test_device_poll.py` (23): green; new tests cover field markup and order, options and offsets, isolation of a valid save, Paris and omitted leaving the file without the key, live-frame file bytes unchanged, five invalid values rejected atomically (no file changes, quiet-hours values not applied, field restored, `role="alert"`, `aria-invalid`, `aria-describedby`, toast), unlisted stored zone, readout clause EN and FR, French strings, poll action prefix, scope sentence, XSS escape, one-device caption identical, unsupported state EN and FR, per-device cooldown, prefixed settings and rule forms.
- Browser tests (Chromium build 1243 through a symlinked browsers path, serial): display looks, ux 01-04, quiet/wake, phase 44 walkthrough, device selector, hit areas, toasts, calendar sheet: 200 passed (plus the 9 quiet/wake tests earlier).
- `ruff check .`, `server/.venv/bin/mypy`, `check_comment_history.py check`, `check_function_size.py check --max 80 server stub-server` clean. `stub-server/test_phase47_freeze.py` and `test_image_negotiation.py` unmodified and passing.

## Threat model coverage
T-51-40 (curated-or-stored plus IANA membership; `../x`, empty, `Asia/Tokyo`, unknown tested), T-51-41 (file snapshots after rejected POST), T-51-42 (refusal handler from plan 06; rendered disabled state asserted here), T-51-43 (device name escaped in the caption, markup-name test).

## Known Stubs
None.

## Self-Check: PASSED
