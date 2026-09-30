---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 04
subsystem: ui
tags: [companion, display, settings, i18n, server-rendered-forms]
requires:
  - phase: 44-01
    provides: Walkthrough evidence and the approved Display information hierarchy.
provides:
  - A single Display appearance flow with base sources before optional flight rules.
  - Reduced Display framing without the duplicated technical state cards.
  - Bilingual served-page regression coverage for the new hierarchy.
affects: [44-05, companion-display, companion-settings]
tech-stack:
  added: []
  patterns: [Server-rendered base-to-override hierarchy with native form associations retained.]
key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/settings/theme.py
    - companion/i18n_fr/display.py
    - companion/test_config_page_05.py
key-decisions:
  - "Remove Display's technical header and frame strip so only the appearance configuration remains."
  - "Present departures, arrivals, and calendar choices before visibly optional per-flight rules."
patterns-established:
  - "Settings hierarchy: base choices precede optional overrides while all existing controls stay tied to the native settings form."
requirements-completed: [CMP-03, CMP-04]
coverage:
  - id: D1
    description: Display renders one bilingual appearance flow without the retired screen and status framing.
    requirement: CMP-03
    verification:
      - kind: unit
        ref: companion/test_config_page_05.py#test_display_uses_one_bilingual_appearance_flow_without_duplicate_framing
        status: pass
    human_judgment: false
  - id: D2
    description: Existing theme, arrival, and calendar controls retain the server-backed settings form association.
    requirement: CMP-04
    verification:
      - kind: unit
        ref: companion/test_config_page_05.py#test_display_uses_one_bilingual_appearance_flow_without_duplicate_framing
        status: pass
    human_judgment: false
metrics:
  duration: 18min
  completed: 2026-09-30
status: complete
---

# Phase 44 Plan 04: Display Information Structure Summary

**Display now leads with one bilingual appearance flow, placing base image choices before optional flight overrides and removing duplicate status framing.**

## Performance

- **Duration:** 18 min
- **Completed:** 2026-09-30
- **Tasks:** 2/2
- **Files modified:** 4

## Accomplishments

- Removed the Display page's technical screen caption, purpose slogan, and duplicate frame status card.
- Reframed the page as “What appears” then “Choose an appearance,” with departure, arrival, and calendar options preceding optional flight rules.
- Kept all existing native controls and their `form="settings-form"` associations intact.
- Added served-page assertions in English and French for the hierarchy, single live preview, retired framing, and native fields.

## Task Commits

1. **Task 1: Replace duplicated Display framing with one appearance model** — `11bf4db0` (feat)
2. **Task 2: Protect the delivered structure and saved-settings path** — `8ffe614e` (test)

## Files Created/Modified

- `companion/pages/config_page.py` — renders the concise Display header, base appearance flow, and non-repeating Runway and Quiet hours cards.
- `companion/settings/theme.py` — labels the appearance choice and optional per-flight override clearly.
- `companion/i18n_fr/display.py` — supplies matching French labels and removes retired Display copy.
- `companion/test_config_page_05.py` — protects the served bilingual hierarchy and adjusted editorial floor.

## Decisions Made

- The page no longer repeats device state or explains its own purpose; the configuration begins directly with what can appear on the frame.
- Per-flight rules remain available but are explicitly optional and follow the three base appearance sources.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

- The broader requested suite was not rerun successfully during this parallel wave. Concurrent navigation work currently leaves orphan French navigation IDs and a `ui_nav._mobile_nav_html()` format-string mismatch that closes served HTTP responses. The focused direct-render checks for this plan pass; rerun the full suite after the navigation change is repaired.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 05 can refine the faithful preview and Quiet hours interaction on top of the completed content hierarchy.

## Self-Check: PASSED

- Confirmed each modified companion file exists and task commits `11bf4db0` and `8ffe614e` are present in git history.
