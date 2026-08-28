---
phase: 07-final-on-glass-verification
plan: 01
subsystem: ui
tags: [pillow, e-ink, spectra-6, dithering, palette-calibration, pt-serif]

requires:
  - phase: 03-visual-polish-on-real-glass
    provides: PT Serif Regular typography, flat single-color state background, per-airline dithered illustrations, two-flight poster composition (as shipped, superseding this plan's original drafted assumptions)
  - phase: 02-plane-view-end-to-end-slice
    provides: base 02-UI-SPEC.md Colour contract, render.py CLI foundation
provides:
  - Reproducible render CLI forcing flags (--airline, --city, --calibration-preview) for on-glass verification without hand-built Python snippets
  - First-ever real-glass validation of the Phase 3 shipped design (typography, bezel, state distinction, composition, wordmark detail, forced states, long-name stress)
  - Re-tuned PALETTE_RGB Blue/Green triples, developer-approved against real Spectra 6 ink (D-21's monitor-only values superseded)
  - dither.dithered_state_background() — visually lightens a fixed physical ink via Floyd-Steinberg dithering toward White, replacing the flat single-index background fill at render time
  - render._paint_text_backing() — clean undithered backing plate behind every text run, fixing a legibility regression the dithered background introduced
  - hardware/BRINGUP-LOG.md Phase 7 on-glass findings entry
affects: [any future phase touching server/panel_format.py PALETTE_RGB, server/plane/dither.py, server/plane/render.py's background/text-drawing path, or device_config.py THEMES]

tech-stack:
  added: []
  patterns:
    - "Dedicated 2-color quantization palette per dithering call, not the full 6-color palette, when the source colors being dithered can land close together in RGB space (dither.dithered_state_background())"
    - "Paint a flat backing plate behind text before drawing it whenever the surrounding field is dithered/textured, to keep text legible against a non-flat background (render._paint_text_backing())"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/panel_format.py
    - server/plane/dither.py
    - server/test_render.py
    - server/test_poll_loop.py
    - .planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md
    - hardware/BRINGUP-LOG.md
    - server/device_config.py

key-decisions:
  - "Blue/Green PALETTE_RGB triples re-tuned twice against real Spectra 6 glass (D-21's values were monitor-only-confirmed and read too dark/saturated in reality) — a live, developer-approved Rule 4 architectural deviation from this plan's own written acceptance criteria, which assumed Blue/Green would stay untouched"
  - "State background changed from a flat single-index fill to a Floyd-Steinberg-dithered blend toward White (dither.dithered_state_background()), because a flat fill at full-panel coverage reads darker than the same ink in a calibration swatch (simultaneous contrast), and no software value can change a fixed physical e-ink color — a second live, developer-approved Rule 4 deviation"
  - "Text-backing-plate fix (render._paint_text_backing()) applied as a direct Rule 1/3 bug-style correction in response to the dithered background's White speckle hurting text legibility — not a new design decision, a regression fix for the prior deviation"
  - "Yellow and Red left unchanged — both confirmed 'close enough, no change' on real glass, per this plan's original (still-accurate) acceptance criterion"
  - "PT Serif Regular confirmed legible at every typographic role including the previous-card's 16px/12px-floor text — no font-weight swap to PTSerif-Bold.ttf needed"

patterns-established:
  - "When re-tuning a locked color decision (D-21) live against real hardware, treat the developer's real-time direction as Rule 4 architectural approval and document the plan's own now-stale acceptance criteria as superseded rather than trying to satisfy them literally"

requirements-completed: [PLANE-01, PLANE-02]

coverage:
  - id: D1
    description: "render.py CLI gains --airline/--city/--calibration-preview forcing flags so every on-glass verification step is one copy-pasteable command"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "server/test_render.py — new flag coverage (EXPECTED_CHECK_COUNT raised, Task 1 commit 0cc4ae1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "02-UI-SPEC.md Colour contract carries an explicit Illustration-Zone Exception subsection describing the legality-plus-dominance guard rail, with no collateral edits elsewhere in the file"
    requirement: "PLANE-01"
    verification:
      - kind: unit
        ref: "grep checks against .planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md (Task 1 acceptance criteria)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full on-glass verification battery (steps A-H): calibration mismatch directions, PT Serif Regular legibility per role, bezel clipping, state distinction, two-flight composition, wordmark detail, forced departure/arrival, long-name stress, desk-distance judgment — all judged against real Spectra 6 glass"
    requirement: "PLANE-02"
    verification: []
    human_judgment: true
    rationale: "Subjective visual/legibility judgments against physical e-ink hardware; already conducted and reported verbatim by the developer during Task 2's live session (this SUMMARY records the outcome, not a proposal to re-verify)"
  - id: D4
    description: "PALETTE_RGB Blue/Green re-tuned and Yellow/Red confirmed unchanged, both states still pass _assert_legal_palette() after tuning"
    requirement: "PLANE-02"
    verification:
      - kind: unit
        ref: "server/test_render.py, server/test_dither.py, server/test_illustrations.py, server/test_pipeline_e2e.py, server/test_enrich.py, server/test_runway_config.py, server/test_plane_detection.py — all 0 exit"
        status: pass
      - kind: manual_procedural
        ref: "heredoc script: build_canvas() for departing/arriving with a real flight+route, _assert_legal_palette() does not raise for either state"
        status: pass
    human_judgment: false
  - id: D5
    description: "hardware/BRINGUP-LOG.md records the D-13 calibration method, final palette triples, every on-glass finding, and the desk-not-wall-mounted caveat"
    requirement: "PLANE-02"
    verification:
      - kind: manual_procedural
        ref: "hardware/BRINGUP-LOG.md 'Phase 7 On-Glass Verification' entry, grep checks in Task 3 acceptance criteria (02-05 distinction, desk/wall-mount caveat)"
        status: pass
    human_judgment: false

duration: 73min
completed: 2026-08-28
status: complete
---

# Phase 7 Plan 1: Final On-Glass Verification Summary

**Real Spectra 6 glass verification closed out the whole project's hardware-sign-off backlog — and, live during the session, re-tuned Blue/Green's D-21-locked palette values and replaced the flat state background with a dithered lighten-toward-White blend, both developer-approved deviations from this plan's own written scope.**

## Performance

- **Duration:** 73 min (Task 1 commit 0cc4ae1 at 13:37:09 UTC through this Task 3 completion)
- **Started:** 2026-08-28T13:37:09Z
- **Completed:** 2026-08-28T14:50:27Z (approx, Task 3 dispatch)
- **Tasks:** 3 (Task 1: CLI flags + UI-SPEC addendum; Task 2: on-glass verification checkpoint; Task 3: apply tuning + record findings)
- **Files modified:** 8 (`server/plane/render.py`, `server/panel_format.py`, `server/plane/dither.py`, `server/test_render.py`, `server/test_poll_loop.py`, `.planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md`, `hardware/BRINGUP-LOG.md`, `server/device_config.py`)

## Accomplishments

- Added `--airline`, `--city`, `--calibration-preview` CLI flags to `server/plane/render.py`, making every on-glass verification step a single reproducible command (Task 1, commit `0cc4ae1`)
- Amended `02-UI-SPEC.md`'s Colour section with an Illustration-Zone Exception subsection describing the shipped legality-plus-dominance guard rail (Task 1, commit `0cc4ae1`)
- Ran the full on-glass verification battery (steps A-H) against the live production panel — checkpoint approved by the developer (Task 2, commits `c23f7d8` state-tracking, `332544b`/`52b823d`/`18163e4`/`2bee807` live-session code changes)
- Re-tuned Blue/Green `PALETTE_RGB` values across two developer-approved passes to match real ink (commits `332544b`, `52b823d`)
- Replaced the flat state-background fill with a Floyd-Steinberg-dithered lighten-toward-White blend (`dither.dithered_state_background()`) to counter simultaneous-contrast darkening at full-panel coverage (commit `18163e4`)
- Fixed a text-legibility regression the dithered background introduced by painting a clean backing plate behind every text run (`render._paint_text_backing()`, commit `2bee807`)
- Recorded the full Phase 7 on-glass findings, calibration method, and every carried-forward open item in `hardware/BRINGUP-LOG.md`'s `## Panel Observations` section (this dispatch)
- Updated `server/device_config.py`'s stale THEMES comment to reflect that Phase 7 did in fact confirm the "sky" theme's Blue/Green hues against real glass, pointing at the new `PALETTE_RGB` values and the BRINGUP-LOG entry (this dispatch)
- Re-ran the full server test suite (7 targeted modules + `scripts/run-all-tests.sh` project-wide) — all green, 90% coverage
- Confirmed `_assert_legal_palette()` still passes for both departing and arriving states via a direct heredoc script

## Task Commits

1. **Task 1: Amend 02-UI-SPEC.md and add CLI forcing flags** - `0cc4ae1` (feat)
2. **Task 2: On-glass verification battery (checkpoint)** - state-tracking `c23f7d8`; live-session code changes made in-session and committed as `332544b` (fix: darken Blue/Green), `52b823d` (fix: darken further), `18163e4` (feat: dithered background), `2bee807` (fix: text backing plate)
3. **Task 3: Apply tuned values and record findings** - `<this dispatch's commit hash, see below>` (docs)

**Plan metadata:** committed together with Task 3 per this dispatch's instructions (no separate final metadata commit issued by this executor — STATE.md/ROADMAP.md updates are owned by the orchestrator)

## Files Created/Modified

- `server/plane/render.py` - Added `--airline`/`--city`/`--calibration-preview` flags (Task 1); `_paint_text_backing()` and its threading through `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()`, and `_build_active_canvas()`'s call to `dither.dithered_state_background()` (Task 2 live session)
- `server/panel_format.py` - `PALETTE_RGB`'s Blue/Green triples re-tuned twice; Yellow/Red left unchanged; comment block extended with the Phase 7 rationale
- `server/plane/dither.py` - New `dithered_state_background(bg_idx, lighten_fraction=0.4)` function, with a dedicated 2-color quantization palette to avoid the wrong-ink-selection bug found mid-session
- `server/test_render.py` - New flag coverage, `EXPECTED_CHECK_COUNT` raised
- `server/test_poll_loop.py` - `_DEFAULT_CONFIG_DIGEST` re-pinned twice (palette+dithering change, then text-backing-plate change), both documented in the file's own comments
- `.planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md` - New Illustration-Zone Exception subsection
- `hardware/BRINGUP-LOG.md` - New dated Phase 7 "On-Glass Verification" entry under `## Panel Observations` (this dispatch)
- `server/device_config.py` - THEMES comment updated to reflect real-glass confirmation happened and point at the new palette values (this dispatch)

## Decisions Made

- **Blue/Green re-tuning (Rule 4, developer-approved live).** D-21 had only ever been confirmed against monitor mockups. This session was the first real-glass check, and the developer directed two rounds of darkening based on direct observation of the physical panel plus a real photo of the six-band calibration swatch. This is an explicit deviation from this plan's own written acceptance criteria ("confirm specifically that the Blue and Green triples are unchanged") — see the Deviations section below for the full account.
- **Dithered background instead of flat fill (Rule 4, developer-approved live).** A flat single-index fill reads darker at full-panel coverage than the same ink in a thin calibration band (simultaneous contrast). Since Spectra 6 only has six fixed physical inks, dithering a blend toward White is the only way to visually lighten a fixed ink. Implemented as `dither.dithered_state_background()`, called from `_build_active_canvas()` in place of `panel_format.new_canvas(bg_idx)`.
- **Text-backing-plate fix (Rule 1/3, direct bug fix).** The dithered background introduced a real legibility regression (White speckle behind white-ink text). This is treated as a bug fix reacting to the prior deviation's side effect, not a new design choice.
- **Yellow/Red left unchanged.** Both confirmed "close enough, no change" on real glass — matches this plan's original acceptance criteria exactly, no deviation.
- **PT Serif Regular confirmed legible everywhere, no font-weight swap needed.** Developer reported "tout est parfait" across every typographic role including the previous-card's 12px floor text.

## Deviations from Plan

### Auto-fixed / Architectural Issues

**1. [Rule 4 - Architectural, developer-approved live] Blue/Green PALETTE_RGB re-tuned, contradicting this plan's own stale acceptance criterion**
- **Found during:** Task 2's live on-glass session
- **Issue:** This plan's Task 3 text explicitly instructs "Do not touch Blue or Green... Confirm specifically that the Blue and Green triples are unchanged from (110, 180, 225)/(140, 195, 130)." That instruction assumed D-21's monitor-only confirmation was still valid on real glass. It was not: the developer reported, with a real photo of the six-band calibration panel as evidence, that both inks read "beaucoup plus terne et sombre" (much duller/darker) on real ink than the on-screen preview.
- **Fix:** Two darkening passes, each re-confirmed against the real panel by the developer: Blue (110,180,225) → (70,125,185) → **(45,95,155)**; Green (140,195,130) → (80,140,95) → **(50,105,65)**. Second pass confirmed "c'est parfait."
- **Files modified:** `server/panel_format.py`
- **Verification:** `server/plane/render.py --calibration-preview` re-run and re-confirmed against the physical panel after each pass; full test suite re-run and green after each change.
- **Committed in:** `332544b`, `52b823d`
- **Why this is documented as a deviation rather than a plan violation:** The developer gave real-time, explicit direction at each step to darken further, after being shown the actual on-glass mismatch. This is a Rule 4 architectural decision made live with the person who owns the decision, not an autonomous choice to override a locked value. The plan's own stale acceptance criterion (based on an assumption that turned out false — D-21 had never actually been checked on real glass) is superseded by this developer-approved outcome, and `hardware/BRINGUP-LOG.md` records the full rationale for anyone reading this later.

**2. [Rule 4 - Architectural, developer-approved live] Flat state background replaced with a dithered lighten-toward-White blend**
- **Found during:** Task 2's live on-glass session
- **Issue:** Independently of the calibration-swatch mismatch above, the developer found the flat single-index background field reads even darker again at full-panel coverage — a large solid field of dark ink reads darker than a thin swatch of the same ink (simultaneous contrast). No software RGB value can change a fixed physical e-ink color, so lightening the visual result requires dithering a blend toward White instead.
- **Fix:** Added `dither.dithered_state_background(bg_idx, lighten_fraction=0.4)`: builds a flat RGB blend of `bg_idx`'s own color lightened 40% toward White, then Floyd-Steinberg-dithers it against a dedicated 2-color palette (`{bg_idx's RGB, White}` only — not the full 6-color palette). A real bug was caught and fixed within this same iteration: quantizing against the full 6-color palette occasionally picked the wrong ink (Blue for a lightened-Green target) once Blue and Green were both darkened close together in RGB space by deviation #1 above; the dedicated 2-entry palette makes that impossible regardless of how any other ink is tuned. `_build_active_canvas()` in `render.py` now calls this instead of `panel_format.new_canvas(bg_idx)`.
- **Files modified:** `server/plane/dither.py`, `server/plane/render.py`
- **Verification:** Developer confirmed both departing (blue) and arriving (green) fields "parfait" after this change; full test suite re-run and green; `test_poll_loop.py`'s pinned config digest re-pinned to match.
- **Committed in:** `18163e4`
- **Why this is documented as a deviation:** This is architecturally significant — it changes how the state background is rendered at all, not a value tweak. The developer directed this live, having just seen the real problem on glass, and confirmed the result before moving on. Carried forward per this plan's own Rule 4-style widened-scope note (2026-08-26): "small font-weight, font-size, or geometry correction... applied directly." This particular fix goes slightly beyond a "small" correction in mechanism (a new function, not a constant tweak) but stays within the same spirit — a bounded, immediately-necessary fix to make the already-shipped design work on real hardware, not a new feature or redesign.

**3. [Rule 1/3 - Direct bug fix] Text-backing-plate added after the dithered background hurt text legibility**
- **Found during:** Task 2's live on-glass session, immediately after deviation #2 above
- **Issue:** The dithered background's scattered White speckle landed directly behind white-ink text, specifically flagged by the developer for the top-left state label and the previous-flight card's text.
- **Fix:** Added `_paint_text_backing()` in `render.py`: paints a small flat `bg_idx` rectangle (4px pad) behind every text bbox before drawing it, keeping a clean undithered backdrop for text while the surrounding field stays lighter. Threaded a new `bg_idx` parameter through `draw_top_labels()`, `draw_main_text_block()`, `draw_previous_text_block()`, and their three call sites.
- **Files modified:** `server/plane/render.py`
- **Verification:** Developer confirmed "parfait" on both departing and arriving after this fix; full test suite re-run and green; `test_poll_loop.py`'s pinned config digest re-pinned a second time to match.
- **Committed in:** `2bee807`
- **Why Rule 1/3 not Rule 4:** This is a direct, targeted fix reacting to a real legibility regression the prior deviation introduced — it doesn't change the design's intent, just protects text readability against a texture that was newly introduced. It follows the shared fix-inline → verify → continue pattern rather than requiring a fresh architectural decision.

**4. [Rule 3 - blocking, documented pattern] `test_poll_loop.py`'s pinned config digest re-pinned twice**
- **Found during:** Task 2's live session, after both the palette+dithering change and the text-backing-plate change
- **Issue:** `_DEFAULT_CONFIG_DIGEST` pins the exact sha256 of a default-config panel.bin render; any pixel-level render change invalidates the pin.
- **Fix:** Re-pinned twice, following the exact same "computed locally, may need one more re-pin from CI's own output" pattern already established in this file for the prior D-26-outline-removal re-pin. Both re-pins are documented in the file's own comments as expected consequences of the deliberate render changes above, not regressions.
- **Files modified:** `server/test_poll_loop.py`
- **Verification:** Full suite green after each re-pin.
- **Committed in:** `18163e4` (first re-pin), `2bee807` (second re-pin)

---

**Total deviations:** 4 (2 Rule 4 architectural, developer-approved live; 1 Rule 1/3 direct bug fix; 1 Rule 3 blocking/expected pattern)
**Impact on plan:** All four were necessary responses to real, first-time-ever real-glass findings — none were autonomous scope creep. The two Rule 4 items directly contradict this plan's own stale, monitor-only-informed acceptance criteria; both are documented here rather than silently satisfied, per this dispatch's explicit instruction.

## Issues Encountered

None beyond the deviations documented above — all were resolved within the same on-glass session with developer confirmation at each step.

## Carried-Forward Open Items (do NOT mark resolved — STATE.md/ROADMAP.md must inherit these)

1. **A-02-02-01's real +200 ft/min departure threshold remains unvalidated against real sensor data.** Only the visual DEPARTING path was closed this session (confirmed blue-toned + `DEPARTING` label on a forced synthetic render). The next time `journalctl -u skypane-poll` shows a real `confirmed_state=departing`, the triggering vertical-rate values should be recorded.
2. **The wall-mounted re-check of ROADMAP criteria 1 and 4 remains open (D-03).** This session's desk-distance composition judgment was confirmed "parfait," but the frame is still on a desk, not wall-mounted. This is an explicit, non-blocking caveat per D-03 — not a tracked follow-up task unless the developer asks for one.
3. **Documentation-drift observation (not a blocker): `inkframe-*` vs `skypane-*` naming in this plan's own Task 2 example commands.** The actual production systemd units are `skypane-poll.timer`/`skypane-byos.service`/`skypane-companion.service` under `/opt/skypane/...` (project renamed InkFrame → SkyPane, VPS mid-migration when this plan's text was drafted). Every command actually run this session used the real `skypane-*` names; the plan file's own stale `inkframe-*` example commands were left as-is per this dispatch's explicit instruction (not this task's job to fix).
4. **`03-03-PLAN.md`'s two documentation gaps are already resolved, not open.** Verified this dispatch: `server/test_illustrations.py` (789 lines) and `server/assets/icons/illustrations/VENDOR.md` (484 lines) both exist and are substantive — created in a later phase after `03-03-PLAN.md`'s own Reconciliation Note flagged them as missing. Correcting the stale carry-forward per this dispatch's explicit instruction: **do not** carry these two forward as open items; they are closed.

No genuinely structural redesign need (new font family, new illustration asset, or a materially different composition) was surfaced this session — every on-glass finding was resolved with a bounded correction (palette tuning, a new dithering function, a text-backing-plate fix), none required deferring to a future phase's redesign.

## User Setup Required

None - no external service configuration required. All changes are code, palette constants, and documentation.

## Next Phase Readiness

- This phase's entire hardware-verification backlog is closed: PT Serif Regular legibility, bezel clipping, state distinction, two-flight composition, wordmark detail, forced departure/arrival (visual path), long-name stress, and desk-distance composition judgment have all been confirmed against real Spectra 6 glass.
- The frame is left on live detection (`skypane-poll.timer` confirmed `active` with a real poll cycle in the journal after restart, not just an enabled-but-idle unit).
- Three items remain genuinely open and should carry into STATE.md/ROADMAP.md as described above: the real +200 ft/min threshold validation, the wall-mounted re-check, and the naming-drift documentation observation.
- No blockers for closing this phase.

---
*Phase: 07-final-on-glass-verification*
*Completed: 2026-08-28*
