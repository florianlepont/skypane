# Phase 44 Companion Walkthrough

**Status:** Awaiting owner verification. Automated evidence is complete; no
owner approval has been recorded. Every "Implemented" disposition below means
implemented and covered by automated tests, not yet visually accepted.

## Fixture / revision

- **Initial run:** 2026-09-30 at `2a080fd1` (before any production change).
- **Final rerun:** 2026-10-03 on the Phase 44 working tree (base `0d05a73a`
  plus the retired-test cleanup in the closing commit).
- **Browser:** Playwright headless Chromium, `SKYPANE_REQUIRE_BROWSER=1`.
- **Focused command:** `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh -- companion/test_browser_phase44_walkthrough.py`
- **Fixture provenance:** `seed_state_dir()` creates production-shaped history,
  configuration, gallery, manual-resolution, and health data through storage
  APIs. `_seed_two_releases()` creates Update state through the firmware
  registry API. The intentional-sleep state is isolated with an all-day
  quiet-hours window and no unresolved prefixes.

## Coverage matrix (final rerun)

| Route | English | French | 1280 px | 390 px | 360 px |
| --- | --- | --- | --- | --- | --- |
| Home (`/`) | pass | pass | pass | pass | pass |
| Display (`/display`) | pass | pass | pass | pass | pass |
| Flights (`/flights`) | pass | pass | pass | pass | pass |
| Airlines (`/airlines`) | pass | pass | pass | pass | pass |
| Health (`/health`) | pass | pass | pass | pass | pass |
| Device (`/device`) | pass | pass | pass | pass | pass |
| Update (`/update`) | pass | pass | pass | pass | pass |

Every matrix case uses the real login form and verifies served language,
primary content, active navigation, and the absence of horizontal overflow.

## Automated observations (W-xx)

| ID | Route | Language | Viewport | Observed result | Disposition | Owning plan | Regression |
| --- | --- | --- | --- | --- | --- | --- | --- |
| W-01 | All authenticated routes | EN, FR | 1280, 390, 360 | Primary heading, active navigation marker, no document overflow. | **keep** (rerun green after all polish) | 44-01, rerun 44-12 | `test_authenticated_route_matrix_has_primary_content_and_no_page_overflow` (42 cases) |
| W-02 | Display | EN, FR | 360 | Keyboard focus reaches a native runway control; setting persists with served confirmation. | **keep** | 44-01, 44-04, 44-05 | `test_display_setting_saves_and_reports_a_keyboard_focusable_control` |
| W-03 | Flights, Airlines | EN | 390 | Native disclosure opens from the keyboard. | **keep** (Flights disclosures were removed by 44-06; the sweep keeps the shared tab-bar disclosure) | 44-06, 44-07 | `test_data_review_disclosures_open_from_the_keyboard` |
| W-04 | Health | EN | 1280 | Warning and intentional scheduled-sleep fixtures render as separate review states. | **keep**; wording and unidentified-airline severity fixed in 44-08 | 44-08 | `test_health_warning_and_intentional_sleep_are_seeded_as_separate_review_states` |
| W-05 | Update | EN, FR | 1280, 390, 360 | Populated Update route reachable, localised, no overflow. | **keep**; hierarchy and bench filtering fixed in 44-11 | 44-11 | route matrix plus `test_browser_update.py` |

## Owner feedback dispositions

Disposition vocabulary: **fix now** (implemented in Phase 44, automated test
passes, awaiting owner visual check), **defer** (explicit, not shipped),
**keep** (unchanged on purpose).

### Direction and cross-page principles

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Direction B "The frame signal" for the General/Home page | fix now (implemented, awaiting owner visual check) | 44-03 | `test_home_prioritises_the_frame_signal_and_keeps_its_actions_usable` |
| Remove page-description slogans on every page | fix now | 44-03, 44-04, 44-06, 44-07, 44-08, 44-10 | per-page served-page tests |
| Navigation labels: rename Home to General, Device to Advanced features, Status/Updates names | **defer** (Navigation labels stay unchanged until the owner chooses names) | none | Open decision |
| Airlines metadata editor (edit flight or airline information) | **defer** (a new metadata editor needs an owner-selected capability) | none | Open decision; 44-07 only clarifies the existing "Delete my name" control |
| Battery policy, pack, cadence policy | defer | Phase 46 | n/a |

### Navigation

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Remove "screen on" / "quiet hours enabled" text from navigation | fix now | 44-02 | `test_browser_ux_02.py` |
| Repair dark-theme control overflow at narrow widths | fix now | 44-02 | all theme choices fit and operate at 360/390 px, EN and FR |
| Compact shared freshness indicator in the bottom navigation | **defer** (per-page freshness lines were removed; a hidden refresh marker keeps live updates working; no shared indicator was built) | 44-06 marker only | Open decision |

### Home

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Merge duplicated screen/quiet-hours cards; no repeated "on"; no next-wake note outside configuration | fix now (cards removed from Home) | 44-03 | Home served and browser tests |
| Explain the update cadence in plain language near next-update state | **defer** (the next-update state no longer appears on Home; no cadence explanation was added) | none | Open decision |
| Battery visible in normal operation; connection and flight-data tiles replaced by contextual warning only when needed, linking to Health | fix now | 44-03 | `test_home_health_action_is_reserved_for_actionable_state` |
| Move daily activity band to Health | fix now | adcd4218, verified in 44-09 | exactly one `.day-band`, on Health |
| Latest frame and recent flights prioritised | fix now | 44-03 | image first on desktop and phone |
| Modern Home proposal for desktop and mobile | fix now | 44-03 | Direction B |

### Display

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Remove "Screen: aircraft frame", slogans, repeated "Appearance" title, repeated on/off and quiet-hours tiles | fix now | 44-04 | `test_config_page_05.py` EN and FR |
| Repair truncated preview | fix now (containment enforced and tested; not visibly clipped in the seeded fixture) | 44-05 | preview containment browser test |
| Swatches accurately distinguish light and non-light variants | fix now | 44-05 | swatch distinction browser test |
| Single appearance model (departures, arrivals, calendar, per-flight rules) | fix now | 44-04 | served hierarchy tests |
| Rename "What it watches" to Runway; remove duplicate label and next-wake text | fix now | 44-04 | served tests |
| Rename on/off timing section to Quiet hours; friendlier time selector | fix now | 44-04, 44-05 | quiet-hours presets and native time fields browser test |

### Flights

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Remove freshness line, "last 50 aircraft" text, callsign/hex hint | fix now | 44-06 | served tests |
| Remove corroboration column | fix now | 44-06 | served tests |
| Remove expanded technical detail (hex, full timestamp, runway) | fix now | 44-06 | served tests |
| Picture action directly on each row | fix now | 44-06 | direct "View picture" browser tests |

### Airlines

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| One consistent aircraft-type rule; every known type discoverable (both Transavia types) | fix now | 44-07 | native selector served and browser tests |
| Remove "<airline> illustration" label | fix now | 44-07 | served tests |
| Self-evident framed crop area instead of explanatory sentence | fix now | 44-07 | drop frame test |
| Explain or remove the "replaced" badge | fix now (replaced by "Your artwork shown instead" / "Built-in name used instead of yours") | 44-07 | served tests |
| Clarify delete control purpose | fix now ("Delete my name" with consequence text) | 44-07 | served tests |
| Path to edit flight or airline information | **defer** (see Airlines metadata editor above) | none | Open decision |
| Separate source data from owner changes; discoverable actions | fix now | 44-07 | "From SkyPane" / "Your changes" rows |

### Health

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Remove freshness line and combined description; remove physical-frame subtitle; plain explanation by last connection | fix now | 44-08 | `test_health_signals.py`, served tests |
| Unidentified airline is informational, not a warning | fix now | 44-08 | health signal tests |
| Constrain wide desktop cards | fix now | 44-09 | readable-width browser test at 1280 px |
| Remove "three months" label; percentage/voltage switch | fix now | 44-09 | unit switch browser test (pointer, Enter, Space, touch) |
| Lighter "view the 20 readings" control; remove battery-details toggle | fix now | 44-08, 44-09 | muted disclosure test |
| One understandable last-aircraft status | fix now | 44-08 | served tests |
| Compact info icon with hover/focus help for source comparison | fix now | 44-08 | accessible information control |
| Remove repeated "Resolve opens Airlines" text | fix now | 44-08 | served tests |
| Healthy result stronger than secondary text | fix now | 44-09 | verdict hierarchy browser test |
| Plainer replacement for "Our ability to identify flights" | fix now (exact wording is an owner check) | 44-08 | served tests |

### Device

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Rename Device to Advanced features | **defer** (Navigation labels decision) | none | Open decision |
| Remove screen type, next-wake status, page description | fix now | 44-10 | `test_config_page_05.py` |
| Rename to "Wake interval"; remove five-minute claim, battery-history note, repeated cadence text | fix now | 44-10 | served EN and FR tests |
| Rename frame-light section "Diagnostic LED" with concise explanation | fix now | 44-10 | served tests |
| Direct "Refresh now" action with truthful confirmation | fix now | 44-10 | flash wording test |

### Update

| Owner item | Disposition | Plan | Evidence |
| --- | --- | --- | --- |
| Single installed-version summary without competing repeats | fix now | 44-11 | one-summary, one-timestamp tests |
| Remove bench/test builds from installable list | fix now | 44-11 | `test_browser_update.py`, `test_update_page.py` |
| Clear version label or icon per release; approachable hierarchy | fix now | 44-11 | browser test at 1280/390/360 px |

## Retired-contract test cleanup (44-12)

Phase 44 left skipped tests for retired Home, Display, Flights and Health
contracts. They were deleted (not re-skipped); the delivered behaviour is
covered by the Direction B, Display, Flights, Health and Update tests listed
above. Dead Home code with no remaining caller was removed with them
(status-tile and hero helpers, their copy constants and orphaned French
entries).

## Open decisions for the owner

1. Navigation labels (General, Status, Advanced features, Updates).
2. A new Airlines metadata editor.
3. A shared freshness indicator in the bottom navigation.
4. A plain-language update-cadence explanation (no longer shown on Home).
5. The shared Frame strip component, `companion/static/quick-switch.js` and
   the `/quick/display` route are no longer rendered by any page. They were
   left in place; remove or revive is an owner decision.
