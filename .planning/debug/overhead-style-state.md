---
status: resolved
trigger: "DATA_START Overhead (detection mode 'ma position') style bugs found by the owner. (1) By default overhead is drawn in the white style; to change the style the companion forces choosing departing or arriving, although overhead has neither. (2) In overhead mode, once the style has been changed, the frame shows the arriving style and the word 'arriving' instead of 'overhead'. (3) Question: which city (destination/origin/none) does each layout show for overhead? Giant layout _city treats overhead as departing, so destination is shown. DATA_END"
created: 2026-11-15
updated: 2026-11-15
---

## Current Focus

hypothesis: Resolved. Overhead had no look of its own and the companion only offered Departures and Arrivals pictures; the server render never fell back to arriving.
test: n/a
expecting: n/a
next_action: none
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

root_cause: The companion only offered Departures and Arrivals looks, whose pictures draw DEPARTING and ARRIVING, while a position-mode frame draws a level aircraft as overhead with the Departures look. Editing Arrivals showed an ARRIVING picture and left the real overhead frame on the Departures look (white by default). The server render itself always drew OVERHEAD (symptom 2 not reproducible on the frame).
fix: Owner decision, a frame that tracks a position has ONE look for every aircraft. Companion: its Style page lists a single Look view (departures field `theme`, picture drawn as an overhead aircraft, help sentence saying it applies to every aircraft and that an overhead aircraft shows the city it is flying to) in place of Departures and Arrivals; the Arrivals address opens that view. A runway frame keeps Departures and Arrivals, no Overhead tab. Server: poll_cycle passes single_look for position frames so colour_rules ignores the stored arrivals look (kept on disk). City rule, decided by the owner: destination for overhead in every layout (enrich.city_for_state, render/text.py, giant/compose._city). The intermediate design (a theme_overhead setting, an Overhead tab, greyed-out tabs) was built and removed.
verification: companion/test_position_look.py (served HTML EN/FR, preview images), server/test_detection_pipeline.py, test_colour_rules.py, test_enrich.py, test_giant_compose.py, test_render.py. No browser available: the picker script was not exercised.
files_changed: companion/pages/personalisation_cards.py, companion/settings/theme.py, companion/settings/layout_picker.py, companion/theme_preview.py, companion/i18n_fr/look.py, server/plane/colour_rules.py, server/poll_cycle.py, server/plane/enrich.py, server/plane/render/text.py, server/plane/render/giant/compose.py, tests.
