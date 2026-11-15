---
status: investigating
trigger: "DATA_START Overhead (detection mode 'ma position') style bugs found by the owner. (1) By default overhead is drawn in the white style; to change the style the companion forces choosing departing or arriving, although overhead has neither. (2) In overhead mode, once the style has been changed, the frame shows the arriving style and the word 'arriving' instead of 'overhead'. (3) Question: which city (destination/origin/none) does each layout show for overhead? Giant layout _city treats overhead as departing, so destination is shown. DATA_END"
created: 2026-11-15
updated: 2026-11-15
---

## Current Focus

hypothesis: Per-state theme settings are keyed by departing/arriving only; overhead is mapped to departing in themes lookup and falls through to arriving label/theme in render when a custom style is saved.
test: Reproduce in companion (served HTML of theme picker) and render an overhead frame with a changed style.
expecting: Overhead has no independent setting; render falls back to arriving after style change.
next_action: gather initial evidence — reproduce first, before any fix
reasoning_checkpoint:
tdd_checkpoint:

## Symptoms

expected: |
  1. Companion offers a way to choose the overhead style independently of departing/arriving.
  2. Frame in overhead mode shows the word "overhead" with the chosen style.
  3. City rule for overhead is consistent across layouts and documented.
actual: |
  1. Changing the overhead style requires picking departing or arriving; default is white.
  2. After style change, overhead frame shows arriving style and the word "arriving".
  3. Giant layout shows destination city for overhead (looked up as departing); other layouts not yet audited.
errors: none reported (visual/behavioural)
reproduction: Detection mode "ma position", level aircraft in position (overhead state); change style in companion; render frame.
started: found by chance by the owner; unknown whether it ever worked.

## Scope / constraints

- Files to look at: companion/settings/theme.py, companion/settings/layout_picker.py, server/device_config.py (theme_background_index, theme_ink_index, DEFAULT_THEME_ID), server/themes.py, server/plane/render/style.py, server/plane/render/giant/compose.py (_city), server/plane/render/layout.py, landscape.py, landscape_card.py.
- Reproduce first. Outside Phase 64 work.
- Conventions: English comments with no plan/ticket IDs; EN/FR strings in companion/i18n_fr/; function-size gate (max 80 lines in server/stub-server); tests assert served HTML or rendered image, never source text; legacy render golden hashes must not change unless a bug fix changes them on purpose (state it).
- Item 3 city decision (destination / origin / none for overhead) needs owner input: audit and report per layout, do not change behaviour for it without owner decision.
- Done: overhead style choosable without departing/arriving; overhead frame shows "overhead" with chosen style; city rule written in UI help/docs if not obvious; behavioural tests.

## Eliminated

## Evidence

## Resolution

root_cause:
fix:
verification:
files_changed:
