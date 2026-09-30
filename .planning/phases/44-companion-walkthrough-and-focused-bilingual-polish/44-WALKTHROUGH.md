# Phase 44 Companion Walkthrough

**Status:** Awaiting owner review before any production companion change.

## Fixture / revision

- **Run date:** 2026-09-30
- **Revision:** `2a080fd1`
- **Browser:** Playwright Chromium, available locally through the project test runner.
- **Focused command:** `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py`
- **Regression command:** `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py companion/test_browser_ux_01.py companion/test_browser_ux_02.py companion/test_browser_ux_03.py companion/test_browser_ux_04.py companion/test_browser_update.py`
- **Fixture provenance:** `seed_state_dir()` creates production-shaped history,
  configuration, gallery, manual-resolution, and health data through storage
  APIs. `_seed_two_releases()` creates Update state through the firmware
  registry API. The intentional-sleep state is separately isolated with an
  all-day quiet-hours window and no unresolved prefixes.

## Coverage matrix

| Route | English | French | 1280 px | 390 px | 360 px |
| --- | --- | --- | --- | --- | --- |
| Home (`/`) | pass | pass | pass | pass | pass |
| Display (`/display`) | pass | pass | pass | pass | pass |
| Flights (`/flights`) | pass | pass | pass | pass | pass |
| Airlines (`/airlines`) | pass | pass | pass | pass | pass |
| Health (`/health`) | pass | pass | pass | pass | pass |
| Device (`/device`) | pass | pass | pass | pass | pass |
| Update (`/update`) | pass | pass | pass | pass | pass |

Every matrix case used the real login form and verified served language,
primary content, active navigation, and the absence of horizontal overflow.

## Observations

| ID | Route | Language | Viewport | Trigger | Observed result | Impact | Evidence | Disposition | Owning seam | Regression |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| W-01 | All authenticated routes | English, French | 1280, 390, 360 | Log in and navigate to every canonical route. | Each route retained a primary heading, active navigation marker, and no document overflow. | No automatic layout or orientation issue observed. | `test_authenticated_route_matrix_has_primary_content_and_no_page_overflow` (42 cases). | **pending owner review**; no source change authorised. | None selected. | Keep the route-matrix test. |
| W-02 | Display | English, French | 360 | Focus and select a native runway control, then save through the dirty bar. | Keyboard focus reached the control; the setting persisted and a served confirmation rendered. | No automatic feedback or persistence issue observed. | `test_display_setting_saves_and_reports_a_keyboard_focusable_control` (2 cases). | **pending owner review**; no source change authorised. | None selected. | Keep the save-flow test. |
| W-03 | Flights, Airlines | English | 390 | Focus the first native disclosure summary and press Enter. | The disclosure opened by keyboard on both data-review routes. | No automatic keyboard-operability issue observed. | `test_data_review_disclosures_open_from_the_keyboard` (2 cases). | **pending owner review**; no source change authorised. | None selected. | Keep the disclosure test. |
| W-04 | Health | English | 1280 | Load isolated warning and intentional scheduled-sleep fixtures. | Both review states render independently; the scheduled-sleep fixture retains its quiet-hours state without unresolved-prefix warning data. | The owner can judge wording and visual distinction without conflating states. | `test_health_warning_and_intentional_sleep_are_seeded_as_separate_review_states`. | **pending owner review**; the visual and copy judgement belongs to the owner. | None selected. | Keep the separate-fixture test. |
| W-05 | Update | English, French | 1280, 390, 360 | Authenticate and load the release fixture as part of the route matrix. | The populated Update route remained reachable, localised, and free of page overflow. | No automatic candidate for a change was observed. | W-01 plus `_seed_two_releases()` fixture. | **pending owner review**; no source change authorised. | None selected. | Keep the route-matrix test. |

## Owner review gate

This record deliberately selects no `keep`, `fix now`, or `defer` disposition.
Those are the available owner choices after reviewing these journeys and any
observations that automation cannot detect. Every later proposal must state its
expected benefit, smallest existing owning seam, and a targeted regression.
Battery policy remains deferred to Phase 46.

## Results

- Focused walkthrough: **47 passed**.
- Associated browser regression: **168 passed**.
- Production companion files changed: **none**.
