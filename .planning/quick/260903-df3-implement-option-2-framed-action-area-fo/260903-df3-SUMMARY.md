---
phase: quick-260903-df3
plan: 01
subsystem: ui
tags: [css, svg-sprite, file-input, dark-mode, color-mix]

# Dependency graph
requires:
  - phase: quick-260903-btu
    provides: the shared per-page lightbox replace form (LIGHTBOX_REPLACE_FORM_CLASS, REPLACE_LABEL_TEXT/REPLACE_BUTTON_TEXT/REPLACE_INPUT_ID) this quick task restyles
provides:
  - "icon-upload" glyph in the shared SVG sprite (companion/layout.py)
  - LIGHTBOX_REPLACE_ZONE_CLASS / REPLACE_HINT_CLASS / REPLACE_ICON_CLASS constants and REPLACE_HINT_TEXT copy (companion/pages/airlines_page.py)
  - "Option 2 — Framed action area" dashed-border, tinted, centred replace zone (companion/static/style.css), including the app's first `::file-selector-button` rule
affects: [companion airlines-page, sketch-findings-skypane design-system reference]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "::file-selector-button styling scoped to one zone selector, restating base button geometry since the pseudo-element does not inherit it"
    - "Resting-state color-mix toward --color-text over a themed base fill (rather than a flat token value) as the fix for a fill that visually collapses into its own container's tint in one theme but not the other"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/pages/airlines_page.py
    - companion/static/style.css
    - companion/test_companion_app.py
    - companion/test_status_pages.py
    - companion/test_view_pages.py

key-decisions:
  - "Dropped the .lightbox__replace hairline divider (border-top) rather than keeping it alongside the new dashed frame — confirmed correct by real-browser check, no double-framing."
  - "Neutralised the native file input's own inherited box (secondary fill + border) so the picker button inside it stays legible against three nested same-colour boxes — confirmed correct by real-browser check."
  - "Fixed a dark-mode-only defect found during Task 3's real-browser verification: the file-picker button's resting background (flat --color-secondary) nearly matched the zone's own diluted-toward-dominant tint in dark mode, because --color-dominant is darker than --color-secondary in the dark palette (the reverse of light mode). Mixed the resting fill 4% toward --color-text instead (the same idiom the base quiet button already uses), lighter than the existing 7% hover mix."

requirements-completed: [REQ-260903-df3-UI]

coverage:
  - id: D1
    description: "icon-upload glyph added to the shared SVG sprite (layout.ICON_IDS grows from fourteen to fifteen, matching <symbol>)"
    requirement: "REQ-260903-df3-UI"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_icon_sprite_integrity"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py#_page_shell_emits_sprite_once_no_inline_styles"
        status: pass
    human_judgment: false
  - id: D2
    description: "Airlines lightbox replace control restyled as a framed dashed-edge action zone (icon -> bold label -> hint -> file picker -> Upload button), form's own class/attributes and panel-lookup.js untouched"
    requirement: "REQ-260903-df3-UI"
    verification:
      - kind: unit
        ref: "companion/test_status_pages.py#_replace_zone_markup_and_styling_contract"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#_replace_zone_icon_comes_from_the_shared_sprite"
        status: pass
      - kind: unit
        ref: "companion/test_status_pages.py#_replace_form_file_input_id_is_unique_and_labelled"
        status: pass
      - kind: unit
        ref: "companion/test_view_pages.py#_history_lightbox_carries_zero_replace_markup"
        status: pass
    human_judgment: false
  - id: D3
    description: "Real-browser visual and functional verification of the framed zone in light and dark mode, including a real upload and a real rejection"
    verification:
      - kind: manual_procedural
        ref: "Task 3 checkpoint — real browser session against http://127.0.0.1:8643/airlines, both themes, plus a real 1400x400 transparent-PNG upload and a real opaque-PNG rejection"
        status: pass
    human_judgment: true
    rationale: "CSS rendering (especially ::file-selector-button cross-browser behaviour and colour-mix visual separation) requires a human eye against a real browser; no pixel-level automated coverage exists in this stdlib-only repo."

# Metrics
duration: 45min
completed: 2026-09-03
status: complete
---

# Quick Task 260903-df3: Framed Action Area for the Airlines Replace Control Summary

**Restyled the Airlines lightbox's native file-input replace control into a dashed-border, tinted "framed action area" (icon → bold label → hint → picker → Upload), fixing a dark-mode-only picker-button contrast defect found during real-browser verification.**

## Performance

- **Duration:** 45 min
- **Tasks:** 3 (2 auto tasks + 1 real-browser checkpoint)
- **Files modified:** 6 (companion/layout.py, companion/pages/airlines_page.py, companion/static/style.css, companion/test_companion_app.py, companion/test_status_pages.py, companion/test_view_pages.py)

## Accomplishments
- Added `icon-upload` to the shared SVG sprite (`companion/layout.py`), consumed only through `layout.icon_html()` — no hand-rolled glyph markup in the page module.
- Restyled `_lightbox_replace_form_html()`'s markup: a new `.lightbox__replace-zone` wrapper containing the icon, the existing label (now a 14px-semibold heading), a new forward-looking requirements hint (`REPLACE_HINT_TEXT`), the unchanged native file input, and the unchanged Upload submit button — the form's own opening tag, `method`, `enctype` and `action=""` stayed byte-identical throughout.
- Wrote the framed zone's CSS: dashed `--color-border` edge, `--radius-control` corners, a `color-mix()`-tinted `--color-secondary`/`--color-dominant` background, and this codebase's first `::file-selector-button` rule (scoped to this zone only), restating the app's quiet-button geometry so the browser's own picker button reads as an integrated control.
- Fixed a dark-mode-only defect the real-browser checkpoint caught: the picker button's resting fill nearly matched its own containing zone's tint in dark mode (both landed near `--color-secondary`, since `--color-dominant` is darker than `--color-secondary` in the dark palette). Mixed the resting fill 4% toward `--color-text` instead of using it flat, confirmed by computing the resulting RGB separation (roughly 4x wider gap in dark mode; light mode's separation stayed subtle but slightly increased).
- Extended four pre-existing `test_status_pages.py` checks in place, added two new ones (sprite provenance, zone markup/styling contract), and fixed one real-HTTP substring-count check that the new same-prefixed class names broke as a side effect. Tightened two `test_view_pages.py` checks (exact-selector style.css guard, extended History's zero-replace-markup absence list).

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the upload glyph to the shared SVG sprite** - `65e8ec4` (feat)
2. **Task 2: Build the framed action zone (markup + CSS) and update the checks that pin this form's shape** - `31b4815` (feat)
3. **Task 3 follow-up: dark-mode picker-button contrast fix (found during the real-browser checkpoint)** - `d42d72b` (fix)

_Note: Task 3 itself (the real-browser checkpoint) produced no code commit of its own — the `fix` commit above is the one round-trip it required before approval._

## Files Created/Modified
- `companion/layout.py` - `icon-upload` appended to `ICON_IDS`, matching `<symbol>` appended to `ICON_DEFS_HTML`
- `companion/pages/airlines_page.py` - `LIGHTBOX_REPLACE_ZONE_CLASS`/`REPLACE_HINT_CLASS`/`REPLACE_ICON_CLASS`/`REPLACE_HINT_TEXT` constants; `_lightbox_replace_form_html()` rewritten to emit the nested zone markup
- `companion/static/style.css` - `.lightbox__replace` demoted to a thin layout wrapper; new `.lightbox__replace-zone`/`-hint`/`-icon` rules; the app's first `::file-selector-button` rule plus its `:hover`; dark-mode contrast fix on the resting fill
- `companion/test_companion_app.py` - sprite-integrity/page-shell checks moved from fourteen to fifteen `<symbol>` members
- `companion/test_status_pages.py` - four pre-existing replace-form checks extended in place, two new checks added, one real-HTTP check's substring-count logic fixed, `EXPECTED_CHECK_COUNT` 124 → 126
- `companion/test_view_pages.py` - style.css guard tightened to an exact selector, History's zero-replace-markup absence list extended to the three new class constants; `EXPECTED_CHECK_COUNT` unchanged at 47

## Decisions Made
- Dropped the old `.lightbox__replace` hairline divider (`border-top`) rather than keeping it alongside the new dashed frame, since a hairline 16px above a dashed box reads as double-fencing — confirmed correct in the real-browser check (no double-framing observed, the divider's absence was not missed).
- Neutralised the native file input's own inherited secondary-fill/bordered box so the restyled picker button stays legible inside the tinted zone (otherwise three nested boxes of the same colour) — confirmed correct in the real-browser check.
- Fixed the file-picker button's resting-fill colour-mix strategy (mix toward `--color-text`, not a flat `--color-secondary` value) after the real-browser checkpoint surfaced a dark-mode-only contrast collapse against the zone's own tint — see Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed a real-HTTP check broken by the new same-prefixed class names**
- **Found during:** Task 2, running `./scripts/run-all-tests.sh`
- **Issue:** `test_status_pages.py`'s real end-to-end HTTP check counted bare occurrences of `airlines_page.LIGHTBOX_REPLACE_FORM_CLASS` ("lightbox__replace") in the served `/airlines` response body, expecting exactly one. That literal is now also a prefix of the three new class names (`lightbox__replace-zone`, `lightbox__replace-hint`, `lightbox__replace-icon`), so the raw substring count jumped from 1 to 4 — not a real regression, a stale assertion technique.
- **Fix:** Switched the count to `'class="%s"' % LIGHTBOX_REPLACE_FORM_CLASS` (the same trailing-quote technique already used elsewhere in this file for the identical ambiguity) so only the `<form class="...">` attribute value itself is counted.
- **Files modified:** companion/test_status_pages.py
- **Verification:** `./scripts/run-all-tests.sh` → PASS, all 16 harnesses green
- **Committed in:** `31b4815` (Task 2 commit)

**2. [Rule 1 - Bug, found at Task 3's real-browser checkpoint] Dark-mode picker-button contrast collapse**
- **Found during:** Task 3, the real-browser visual check (dark mode)
- **Issue:** The `::file-selector-button`'s resting background (`var(--color-secondary)` flat) nearly matched the containing `.lightbox__replace-zone`'s own tint in dark mode — `--color-dominant` (#151922) is darker than `--color-secondary` (#1C222D) in the dark palette, the opposite of light mode, so the zone's `color-mix(--color-secondary 55%, --color-dominant)` tint landed almost on top of the button's own plain-secondary fill. The button read as barely-visible text with no perceptible shape, defeating the exact goal Option 2 was picked for.
- **Fix:** Changed the resting fill to `color-mix(in srgb, var(--color-text) 4%, var(--color-secondary))` (with the plain-value WR-02 fallback line first), the same resting-wash idiom the base quiet `button` rule already uses, at a lighter percentage than the existing 7% hover mix so hover still reads as a step up.
- **Files modified:** companion/static/style.css
- **Verification:** Re-ran `./scripts/run-all-tests.sh` → PASS. Computed the resulting RGB separation directly: dark-mode gap between button and zone widens from ~3-5 points (old) to ~12-13 points (new, roughly 4x); light mode's gap stays subtle but slightly widens too (harmless, matching the coordinator's prediction).
- **Committed in:** `d42d72b` (follow-up commit, since Task 2 had already landed)

---

**Total deviations:** 2 auto-fixed (1 pre-existing-check bug exposed by the new class names, 1 dark-mode contrast bug found at the real-browser checkpoint)
**Impact on plan:** Both fixes were necessary for the plan's own stated success criteria (`./scripts/run-all-tests.sh` green; the checkpoint approved in both light and dark mode). No scope creep — neither touched the hairline-divider or input-box-neutralization judgement calls, both of which were confirmed correct as shipped.

## Issues Encountered
None beyond the two auto-fixed items above.

## Checkpoint Verdict (Task 3, recorded verbatim from the coordinator's real-browser session)

> Real-browser verification done against http://127.0.0.1:8643 (the running local companion service), both light and dark, plus a real upload and a real rejection. Verdict: approved with one confirmed fix required before finalizing.
>
> WHAT PASSED:
> - Light mode matches the approved mockup exactly: one framed dashed box (no double-framing, the dropped hairline divider is not missed), glyph → bold "Replace this illustration" label → muted "Transparent PNG, at least 1200px wide, landscape." hint → restyled file-picker → accent Upload button, all centered/stacked correctly.
> - Real upload round-trip works: constructed a real 1400x400 transparent-PNG File via an in-page `<canvas>.toBlob()`, assigned it to the native file input via DataTransfer, clicked the real Upload submit button — got "Illustration replaced — will apply on the frame's next scheduled refresh." and Iberia's card visibly updated to the new artwork. Confirmed the form's action attribute correctly retargets per clicked card (read "/illustration/iberia-airlines.png" before submit).
> - Real rejection still works: submitted a fully-opaque 1400x400 PNG through the same restyled form — got "Couldn't use that image — upload a transparent PNG that's at least 1200 pixels wide and landscape (wider than tall)." and Iberia's artwork was correctly left untouched. Hint copy and rejection copy still describe the same rule.
> - Cleaned up both test overrides afterward (deleted /tmp/skypane-prod-state/illustration_overrides/iberia-airlines.png) — Iberia is back to its real vendored artwork, confirmed by a fresh page load.
>
> CONFIRMED DEFECT — dark mode only: the `::file-selector-button` and the `.lightbox__replace-zone` it sits inside are nearly the same color in dark mode, so the picker button reads as barely-visible text with no perceptible button shape (unlike light mode, where it reads as a clear pill).
>
> [Fix applied per the coordinator's suggested direction — mix the button's resting background toward `--color-text` rather than using `--color-secondary` flat — see Deviations item 2 above for the exact value chosen and its verification.]
>
> Do not touch the hairline-divider-removal or input-box-neutralization judgement calls — both were confirmed fine as shipped, no reversion needed there.

**Final status: approved**, with the dark-mode picker-button contrast fix as the one round-trip this checkpoint required.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The Airlines illustration-replace control now reads as an integrated, on-brand action zone in both themes, with the native file-picker button legibly separated from its containing frame in dark mode.
- No blockers. The local verification service (`./scripts/run-local-verify.sh`, state_dir `/tmp/skypane-prod-state`) is still running on port 8643 in case a follow-up spot-check is wanted; safe to stop at any time.

---
*Phase: quick-260903-df3*
*Completed: 2026-09-03*

## Self-Check: PASSED

All modified files confirmed present on disk (companion/layout.py, companion/pages/airlines_page.py, companion/static/style.css, companion/test_companion_app.py, companion/test_status_pages.py, companion/test_view_pages.py, this SUMMARY.md). All three task commits confirmed present in git history (65e8ec4, 31b4815, d42d72b). `./scripts/run-all-tests.sh` PASS with all 16 harnesses green, 92% coverage.
