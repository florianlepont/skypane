---
phase: quick-260901-s5o
plan: 260901-s5o
subsystem: ui

tags: [companion, settings, css, typography]

requires:
  - phase: quick-260901-re6
    provides: "One merged, muted .section-caption per Settings group (Theme/Runway/Diagnostic LED); save bar moved outside the form, fixed (not sticky) at >=960px"
provides:
  - "The Poll section's own muted .section-caption, matching the other three Settings groups — the page's fourth and last section to get one"
  - "The unified save bar restyled from a flush, square-cornered, upward-shadowed toolbar into a floating, inset, rounded pop-up card at >=960px"
affects: [companion-settings-page, 06.6.4.1-closing-checkpoint]

tech-stack:
  added: []
  patterns:
    - "Computed-once caption_html reused across both branches of a two-branch renderer (poll_trigger_section()), mirroring theme_fieldset()'s existing idiom"
    - "Symmetric inset on a fixed-position box (left += X, right += X) preserving margin: 0 auto centring, with max-width reduced by 2X so a bare min()-clamped cap can't silently cancel the inset above the width where the cap binds"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_config_page.py

key-decisions:
  - "poll_trigger_section() computes caption_html once, before the cooldown branch, and interpolates it as the first element of both return expressions — reusing theme_fieldset()'s computed-once-reused-by-both-branches idiom rather than duplicating the markup template inline in each branch"
  - "No new CSS rule, class, or helper function for the Poll caption: it reuses .text-label + .section-caption verbatim, so style.css has zero diff after Task 1"
  - "The >=960px .dirty-bar's max-width is reduced by twice the inset (calc(min(1440px, 100%) - var(--space-md) * 2)), not left as the bare min(1440px, 100%) copied from .dashboard-main, because for a fixed-position box 100% resolves against the viewport — once the viewport passes ~1712px (240px sidebar + 32px gap + 1440px cap) the cap alone sizes the box, which would otherwise render it flush with the content column on both sides at exactly the widths (e.g. a 16-inch MacBook Pro's 1728px default) where the inset matters most"
  - "The >=960px rule's corner-squaring border-radius: 0 override is deleted outright, not restated at --radius-card, so the base rule's border-radius: var(--radius-card) is the single definition site for this component's radius at every width"
  - "The base rule's first shadow layer switches from a hand-rolled y-negated black-alpha literal to the real --shadow-card-hover token (which already has dark-mode/[data-ui-theme] variants), with a second raw-rgba ambient layer kept as a literal per this file's existing raw-rgba shadow precedent — citing .lightbox as the file's existing precedent for a floating element with a resting (not hover-revealed) shadow"

requirements-completed: [QUICK-260901-s5o]

coverage:
  - id: G1
    description: "The Poll section renders exactly one muted .section-caption sentence, validated copy verbatim, directly under its heading and above the Trigger Poll Now button, on both the enabled and cooldown-disabled branches — so all four Settings sections now read identically"
    requirement: "QUICK-260901-s5o"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_poll_section_caption_renders_on_both_branches_under_the_heading"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_section_captions_appear_escaped_verbatim_exactly_once"
        status: pass
    human_judgment: false
  - id: G2
    description: "At >=960px the save bar renders as a floating rounded pop-up card: inset var(--space-md) from the content column's left/right/bottom edges at every width including above the 1440px cap, --radius-card on all four corners, a full --color-border border, and a surrounding token-based shadow plus one ambient layer — with position: fixed, form= wiring, DOM placement, and sub-960px in-flow behavior unchanged"
    requirement: "QUICK-260901-s5o"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_style_css_carries_section_caption_and_restyled_fixed_dirty_bar"
        status: pass
      - kind: static
        ref: "awk-scoped rule-body grep in the plan's own verify block, confirming all 4 base-rule declarations, 6 >=960px declarations, and the absence of both retired declarations (border-top:, box-shadow: 0 -) and the corner-squaring override"
        status: pass
    human_judgment: true
    human_judgment_note: "Plan marks the >=1712px viewport rendering as an optional-but-recommended human/real-device check, since no source-level assertion can see the actual rendered gap. Not performed this session (see Deviations) — the source-level guard's max-width formula is the load-bearing fix and is directly asserted."

duration: 25min
completed: 2026-09-01
status: complete
---

# Quick Task 260901-s5o: Poll caption + floating save-bar pop-up Summary

**Gave the Poll section the same muted `.section-caption` the other three Settings groups already carry, and restyled the unified save bar at `>=960px` from a flush, square-cornered docked toolbar into a floating, inset, rounded pop-up card — closing the last two deltas between the shipped Settings page and its validated sketch.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-01T20:10:00Z (approx.)
- **Completed:** 2026-09-01T20:40:00Z
- **Tasks:** 2
- **Files modified:** 3 (`companion/pages/config_page.py`, `companion/static/style.css`, `companion/test_config_page.py`)

## Accomplishments

- `POLL_SECTION_CAPTION` added, contiguous with `THEME_SECTION_CAPTION`/`RUNWAY_SECTION_CAPTION`/`LED_SECTION_CAPTION`, carrying the developer-validated copy verbatim: "Manually trigger an immediate poll cycle instead of waiting for the next scheduled one." `poll_trigger_section()` now computes `caption_html` once and emits it first on both its enabled (zero-cooldown) and disabled (non-zero-cooldown) branches, reusing `theme_fieldset()`'s own computed-once idiom — a caption on only one branch would have silently vanished for the whole cooldown window.
- Every Settings section on `/settings` now reads identically: Theme, Runway, Diagnostic LED and Poll each render exactly one muted caption directly under their heading. `companion/static/style.css` shows zero diff for this fix — no new class, rule, or helper function was needed.
- The unified save bar's base `.dirty-bar` rule is now a fully-bordered floating card: a full `border: 1px solid var(--color-border)` replaces the top-only hairline, and `box-shadow: var(--shadow-card-hover), 0 8px 24px rgba(18, 21, 27, 0.10)` replaces the theme-neutral, upward-only, near-invisible-in-dark-mode literal.
- The `>=960px` rule is now inset by `var(--space-md)` on `bottom`/`right`/`left` (the third addend on the existing `240px + var(--space-xl)` offset), with `max-width: calc(min(1440px, 100%) - var(--space-md) * 2)` so the inset stays visible even above the ~1712px width where the 1440px cap alone would otherwise size the box flush with the content column. The corner-squaring `border-radius: 0` override is deleted outright, letting the base rule's `--radius-card` govern at every width.
- `companion/static/dirty-state.js` and `companion/pages/config_page.py` show zero diff for the save-bar fix — it is pure CSS plus its harness retargets.

## Task Commits

Each task was committed atomically:

1. **Task 1: Give the Poll section the caption the other three sections already have** - `3ca1fc3` (feat)
2. **Task 2: Redesign the save bar from a flush toolbar into a floating rounded pop-up** - `437430f` (fix)

**Plan metadata:** commit pending (orchestrator handles the docs commit)

## Files Created/Modified

- `companion/pages/config_page.py` - Added `POLL_SECTION_CAPTION`, the fourth `*_SECTION_CAPTION` constant; `poll_trigger_section()` computes `caption_html` once and emits it first on both branches; shared comment above the constant block and the function's docstring extended to record the two-branch requirement
- `companion/static/style.css` - Base `.dirty-bar` rule: full border, `var(--radius-card)` (now load-bearing at every width), token-based surrounding shadow plus one ambient layer, no top-only hairline, no upward-only literal. `>=960px .dirty-bar` rule: `var(--space-md)` inset on bottom/right/left, reduced `max-width`, corner-squaring override deleted. Both head comments rewritten to describe the floating-card treatment.
- `companion/test_config_page.py` - One new check (`_poll_section_caption_renders_on_both_branches_under_the_heading`, +1); `_section_captions_appear_escaped_verbatim_exactly_once()` widened in place to a fourth constant (no count change); the cross-file CSS guard `_style_css_carries_section_caption_and_restyled_fixed_dirty_bar()` retargeted and extended in place onto the floating-card treatment (no count change); `EXPECTED_CHECK_COUNT` moved from the real on-disk baseline (60) to 61

## Decisions Made

- Computed `poll_trigger_section()`'s `caption_html` once, above the `if cooldown_remaining > 0:` branch, and interpolated it as the first `"%s"` slot of both return expressions — the identical idiom `theme_fieldset()` already established, chosen over inlining the markup template twice.
- Left the reduced `max-width` calc, rather than the plan's non-goal warning against treating it as "redundant with left/right", because for a `position: fixed` box `100%` resolves against the viewport: once the viewport clears ~1712px the `min(1440px, 100%)` cap alone sizes the box, and without the reduction the bar would render exactly `.dashboard-main`'s own width — flush on both sides, the exact treatment this task retires.
- Deleted the >=960px rule's `border-radius: 0` override outright rather than restating `var(--radius-card)` there, so the base rule stays the single definition site for the component's radius at every width, per the plan's explicit instruction.
- Kept every explanatory comment above the selector in both edited `.dirty-bar` rules' head comments, never inside the rule body, so the harness guard's rule-body substring checks for retired declarations (`border-top:`, `box-shadow: 0 -`, `border-radius: 0`) cannot false-fail against a comment mentioning them.

## Deviations from Plan

None - plan executed exactly as written. All auto-fix rules (1-4) were not needed; both tasks' `<action>` instructions were followed directly, and both tasks' automated `<verify>` blocks passed on the first attempt.

The plan's Task 2 human-check (screenshot the save bar at a >=1800px viewport to confirm the visible inset survives the 1440px cap) was not performed this session — it is explicitly marked optional, and the automated verification directly asserts every CSS declaration responsible for that outcome, including the `calc(min(1440px, 100%) - var(--space-md) * 2)` max-width formula itself (see `coverage` G2's `human_judgment_note` above). A throwaway `companion/app.py` instance was started and confirmed to serve `/settings` correctly (login round-trip verified via `curl`), then stopped and its state directory removed, but no browser screenshot was captured.

## Full Suite Result

`scripts/run-all-tests.sh`: all harnesses passed except the known, pre-existing, unrelated `server/test_poll_loop.py` digest mismatch. No coverage-threshold failure (overall 91%, `companion/pages/config_page.py` itself at 100%).

## Next Phase Readiness

Both confirmed Settings-page gaps from 06.6.4.1's continuing closing checkpoint are closed. All four sections on `/settings` (Theme, Runway, Diagnostic LED, Poll) now carry an identical caption treatment, and the unified save bar at `>=960px` reads as the validated sketch's floating pop-up card rather than a docked toolbar. No blockers for closing out 06.6.4.1's checkpoint; a real-device/real-browser visual pass at a >=1712px viewport remains recommended before final sign-off, per the plan's own optional human-check.

---
*Phase: quick-260901-s5o*
*Completed: 2026-09-01*

## Self-Check: PASSED

All modified files verified on disk (`companion/pages/config_page.py`, `companion/static/style.css`, `companion/test_config_page.py`, this SUMMARY.md) and both task commits (`3ca1fc3`, `437430f`) verified in `git log --oneline --all`.
