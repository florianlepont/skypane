---
status: awaiting_owner_decision
trigger: "DATA_START Overhead (detection mode 'ma position') style bugs found by the owner. (1) By default overhead is drawn in the white style; to change the style the companion forces choosing departing or arriving, although overhead has neither. (2) In overhead mode, once the style has been changed, the frame shows the arriving style and the word 'arriving' instead of 'overhead'. (3) Question: which city (destination/origin/none) does each layout show for overhead? Giant layout _city treats overhead as departing, so destination is shown. DATA_END"
created: 2026-11-15
updated: 2026-11-15
---

## Current Focus

hypothesis: Confirmed in part. Overhead has no look setting of its own: it silently follows the Departures look (device_config "theme"), and the companion only offers Departures and Arrivals pictures, which render DEPARTING / ARRIVING. The server render does NOT fall back to arriving (disproved).
test: Add an independent Overhead look (theme_overhead, "Same as departures" by default) end to end.
expecting: Overhead look choosable on its own view; overhead frame drawn with it and labelled OVERHEAD.
next_action: owner decides the overhead city rule (item 3); then align giant/compose._city and classic text.flight_line1 and write the rule in the Overhead view help
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
- Overhead view shown only on position-mode frames (runway frames never draw overhead); the /display/overhead address itself always answers.
- Done: overhead style choosable without departing/arriving; overhead frame shows "overhead" with chosen style; city rule written in UI help/docs if not obvious; behavioural tests.

## Eliminated

- hypothesis: render falls back to the arriving label/theme for overhead once a custom style is saved.
  evidence: poll_cycle.run_once in position mode with a level aircraft, before and after saving theme / theme_arriving / both, fresh and after a descending held state, promoted and held branches: render_state is always "overhead"; effective theme is the base "theme" (theme_arriving never applies). Every layout x every hardware profile renders overhead as an image distinct from both arriving and departing (OVERHEAD label drawn).
  timestamp: 2026-11-15

## Evidence

- timestamp: 2026-11-15
  checked: server/plane/colour_rules.resolve_effective_theme_id, server/themes.theme_background_index
  found: overhead resolves calendar -> rules -> device_cfg["theme"]; theme_arriving only for state == "arriving"; background index for overhead = departing index.
  implication: overhead follows the Departures look; no separate setting exists.
- timestamp: 2026-11-15
  checked: companion/settings/theme.py, layout_picker.py, pages/personalisation_cards.py, theme_preview.FRAME_PREVIEW_STATES
  found: only Departures/Arrivals views and pictures; FRAME_PREVIEW_STATES = (departing, arriving); no detection-mode awareness.
  implication: symptom 1 confirmed; symptom 2 is what the companion shows (ARRIVING picture when the Arrivals look is changed), while the real overhead frame stays on the Departures look (white by default).
- timestamp: 2026-11-15
  checked: scratch repro of poll_cycle (position mode, rate 0) with theme changes
  found: ('overhead', 'blue') after theme=blue; ('overhead', 'white') after theme_arriving=red.
  implication: symptom 2 not reproducible on the frame itself.
- timestamp: 2026-11-15
  checked: per-layout city audit (route origin Barcelona, destination Lyon, all layouts x all profiles)
  found: classic (portrait and landscape card) shows no city for overhead (enrich.city_for_state returns None; line 1 omitted when an airline is known). Giant layouts a, b, c, a_diagonal (portrait and landscape) letter the destination city (giant/compose._city maps overhead to departing).
  implication: item 3 inconsistent across layouts; owner decision needed.

## Resolution

root_cause: The overhead state had no look setting of its own. colour_rules.resolve_effective_theme_id fell through to the Departures look ("theme"), theme_arriving applied to arriving only, and the companion offered only Departures and Arrivals views whose pictures render DEPARTING / ARRIVING. So changing "the style" meant editing one of those two; editing Arrivals showed an ARRIVING picture and left the real overhead frame on the Departures look (white by default). The server render itself always drew OVERHEAD (symptom 2 not reproducible on the frame).
fix: New per-frame setting theme_overhead (device_config, stored only when set, CLEAR_THEME_OVERHEAD sentinel, None = same as departures so nothing changes for existing frames). colour_rules applies it for state "overhead" only (after calendar and rules, like the arrivals override). Companion gets an Overhead view (/display/overhead) on position-mode frames: classic look picker and giant pairing cards, "Same as departures" default, help text, overhead frame preview state, EN/FR strings.
verification: Reproduction script now shows ('overhead', theme_overhead). New tests server/test_device_config_overhead.py, two pipeline tests in server/test_detection_pipeline.py, companion/test_personalisation_overhead.py (served HTML + rendered preview images). Item 3 (city) left unchanged pending owner decision.
files_changed: server/device_config.py, server/plane/colour_rules.py, companion/theme_preview.py, companion/settings/theme.py, companion/settings/layout_picker.py, companion/settings/form_post.py, companion/pages/personalisation_cards.py, companion/pages/config_page.py, companion/routes.py, companion/ui_base.py, companion/layout.py, companion/static/style-display.css, companion/i18n_fr/display.py, companion/i18n_fr/look.py, tests.
