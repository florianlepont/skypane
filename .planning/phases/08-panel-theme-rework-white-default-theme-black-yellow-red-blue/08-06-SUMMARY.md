---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 06
subsystem: testing
tags: [spectra6, e-ink, on-glass-verification, theme-registry, dithering, ssh, systemd]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 05
    provides: "A green 15-harness suite (CI-verified) and a corrected forced-panel restart reminder, the clean starting point this session's blocking on-glass verification needed"
provides:
  - "Real-glass confirmation (or bounded correction) of every visual/textual change Phase 8 made: the White default, PT Serif Bold-without-a-plate legibility, the four-tier content ladder, and the previous card's 20px nudge"
  - "A theme-conditional 'weight' registry field (regular/bold) replacing the blanket PT Serif Bold, resolving an on-glass 'très agressif' finding"
  - "A theme-conditional 'dithered' registry field, fixing a real bug where a fixed Blue/Green-tuned dither blend was silently applied to every non-white theme, turning flat Black visibly grey"
  - "server.device_config.THEMES widened from 5 to 11 entries — every Spectra 6 ink as both a pure flat theme and a dithered light variant — with Sky retired outright on explicit developer instruction"
  - "Tier 4's fallback text changed from the state word ('Departing'/'Arriving') to a fixed 'Unknown flight' string, on explicit developer instruction given on-glass"
  - "A dated Phase 8 entry in hardware/BRINGUP-LOG.md's Panel Observations section"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-theme presentation properties (dithered: bool, weight: 'regular'|'bold') added to server.device_config.THEMES alongside the existing departing_index/arriving_index/ink_index/label, with matching theme_dithered()/theme_weight() accessors mirroring theme_background_index()/theme_ink_index() - resolves both the flat-vs-dithered background choice and the font-weight choice per theme id, rather than deriving either from bg_idx"
    - "Live on-glass exploration via throwaway SSH-uploaded scripts that monkeypatch render._font/render.PT_SERIF_BOLD/dither.dithered_state_background inside their own process and write directly to /opt/skypane/state/panel.bin, without ever editing the deployed render.py - lets multiple visual candidates be compared on real hardware in one session before any real code change is committed"

key-files:
  created: []
  modified:
    - server/plane/render.py
    - server/device_config.py
    - server/test_render.py
    - server/test_poll_loop.py
    - hardware/BRINGUP-LOG.md

key-decisions:
  - "Font weight decoupled from a single blanket PT Serif Bold into a per-theme registry field: Regular on every flat/undithered theme, Bold on every dithered theme except Yellow Light (the one deliberate exception, Regular). Reopens D-06 with explicit on-glass developer instruction after uniform Bold read 'très agressif', most visibly on White."
  - "Sky (the Blue-departing/Green-arriving two-tone pairing) retired outright, on explicit developer instruction ('Pas de sky, parles de bleu clair, vert clair' / 'thèmes séparés'), once Blue and Green were each independently validated as standalone single-colour themes."
  - "THEMES widened 5->11: white, black, grey, yellow, yellow_light, red, red_light, green, green_light, blue, blue_light - every Spectra 6 ink shown and individually validated on real glass, both flat and dithered, well past D-13's stated minimum of one coloured theme."
  - "Tier 4's fallback text changed from the title-case state word to a fixed 'Unknown flight' string, identical for both states, after the developer noted it duplicated the all-caps DEPARTING/ARRIVING label with no added information - resolved via an explicit choice among options, not a vague request."
  - "The 'Black renders grey' bug's root cause (dither.dithered_state_background()'s fixed 40%-toward-white blend applied unconditionally to every non-white theme) was fixed by making flat-vs-dithered a per-theme registry bool rather than special-casing bg_idx==IDX_WHITE."

requirements-completed: [D-13]

coverage:
  - id: D1
    description: "Every visual/textual change Phase 8 made (White default, Bold-without-a-plate legibility, four-tier content ladder, previous-card nudge, all 11 themes) verified against the real deployed Spectra 6 panel, steps A-H, with corrections applied and re-confirmed on glass where the glass called for it"
    verification: []
    human_judgment: true
    rationale: "This is the developer's own uninstrumented visual judgment of physical ink under real lighting - by design not resolvable by any automated check, which is exactly why D-13 makes this plan a blocking gate."
  - id: D2
    description: "Dated Phase 8 entry in hardware/BRINGUP-LOG.md recording the on-glass findings, the corrections applied, the mounting caveat, and the method's limits, in the developer's own words"
    verification:
      - kind: other
        ref: "grep -c 'Phase 8' hardware/BRINGUP-LOG.md == 3"
        status: pass
      - kind: other
        ref: "grep -c 'wall-mounted|desk' hardware/BRINGUP-LOG.md == 8"
        status: pass
      - kind: other
        ref: "git diff hardware/BRINGUP-LOG.md shows insertions only (161 insertions, 0 deletions)"
        status: pass
      - kind: unit
        ref: "server/test_render.py (99/99)"
        status: pass
      - kind: unit
        ref: "server/test_config_history.py (26/26)"
        status: pass
      - kind: unit
        ref: "server/test_poll_loop.py (42/43, one documented cross-platform digest exception)"
        status: pass
    human_judgment: true
    rationale: "Faithful transcription of the developer's verbatim on-glass report is a judgment call the automated greps above can only partially proxy."

# Metrics
duration: ~3h (across an interactive on-glass session with photo review)
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 06: On-glass verification — White default, Bold legibility, 11-theme registry, content ladder Summary

**Every visual and textual change Phase 8 made was put in front of the real deployed Spectra 6 panel for the first time; two locked decisions were legitimately reopened with explicit developer instruction (font weight, and Sky's retirement in favour of 11 separate pure/light theme pairs), one real bug was caught and fixed live (a fixed Blue/Green dither blend silently applied to every theme, turning flat Black visibly grey), and a third correction (tier 4's fallback text) was added on-glass after step F surfaced it — all re-confirmed on real ink before the phase closed.**

## Performance

- **Duration:** ~3h (interactive on-glass session with live photo review over SSH)
- **Started:** 2026-08-31T11:04:32Z
- **Completed:** 2026-08-31T14:01:23Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- **Step A (White default):** clean white with no cast against the empty state's own white reference; departing/arriving remain distinguishable by label alone despite sharing one background colour.
- **Step B (Bold-without-a-plate legibility — the headline gate):** uniform Bold read "très agressif" on real ink, most visibly on White. Reopened D-06 with explicit developer instruction; resolved via a new per-theme `weight` registry field (Regular on flat themes, Bold on dithered ones, Yellow Light the sole dithered-but-Regular exception). Re-confirmed on glass. Direct answer on the removed plate: not missed ("ah non pas du tout").
- **Step C (Sky):** superseded, not merely re-confirmed — retired outright on explicit developer instruction once Blue and Green existed as standalone themes.
- **Step D (previous card):** "tout est bon" — alignment and caption size confirmed; no outlier illustration flagged (08-05's six-airframe spot-check had already found none).
- **Step E (coloured themes):** all six Spectra 6 inks shown as both pure and dithered-light variants (11 total registry entries) — well past D-13's stated minimum of one. A real bug was caught and fixed: flat Black was rendering visibly grey because the dither blend was applied unconditionally; fixed via a per-theme `dithered` registry bool. Grey, the theme that bug had accidentally produced, was kept as its own independently-liked selectable theme.
- **Step F (content ladder):** all four tiers confirmed, tier 3 separately on the main and previous cards, no raw callsign on any tier. Tier 4's fallback text reopened and changed from the title-case state word to a fixed "Unknown flight" string (developer instruction via explicit choice) after it was found to duplicate the all-caps top-left label.
- **Step G (at-distance composition):** confirmed wall-mounted (not a desk judgment) — reads as ambient art, not a data dump. This closes Phase 7's own carried-forward wall-mounted re-check.
- **Step H (teardown):** poll timer restarted, `is-active` confirmed `active`, and a real post-restart poll cycle observed in the journal with genuine live-detected data.
- Findings recorded in `hardware/BRINGUP-LOG.md`'s `## Panel Observations` section, in the developer's own words, with an honest method note and every correction's before/after/reason.

## Task Commits

Task 1 (on-glass verification, with three bounded/reopened corrections applied and re-confirmed in session):

1. **Font weight — theme-conditional Regular/Bold** - `95d2273` (fix)
2. **Theme registry widened 5→11, Sky retired** - `43380e2` (feat)
3. **Tier 4 fallback text — "Unknown flight"** - `efe0169` (fix)
4. **Digest re-pin from a real CI run** - `ef5b87d` (test)

Task 2 (BRINGUP-LOG.md entry):

5. **Record Phase 8 on-glass findings** - `5c3cc7d` (docs)

**Plan metadata:** this commit (docs: complete plan)

_Note: corrections 1-3 were applied incrementally as each step of the on-glass session surfaced them, batched with 4 (the digest re-pin, deferred until the session's rendering changes were locked, matching plan 08-05's established CI round-trip pattern) once Task 1 closed._

## Files Created/Modified

- `server/plane/render.py` - `_flight_line1_text()`'s tier-4 fallback now returns a fixed `"Unknown flight"` string instead of the title-case state word; theme-conditional `weight` threaded through `draw_top_labels()`/`draw_main_text_block()`/`draw_previous_text_block()` (landed just before this plan, re-confirmed within it)
- `server/device_config.py` - `THEMES` widened to 11 entries (white, black, grey, yellow, yellow_light, red, red_light, green, green_light, blue, blue_light), each carrying `dithered`/`weight` alongside the existing background/ink/label fields; `sky` removed; new `theme_dithered()`/`theme_weight()` accessors
- `server/test_render.py` - tier-4 checks updated for `"Unknown flight"`; theme-iteration checks (`_every_theme_uses_only_its_declared_weight`, the White-vs-others comparison) rewritten to loop `THEME_IDS` dynamically instead of hardcoding `"sky"`
- `server/test_poll_loop.py` - `_DEFAULT_CONFIG_DIGEST` re-pinned (fifth re-pin in this file's history) from a real CI run, with a dated standing-rule comment explaining the three rounds of pixel movement since 08-05's re-pin
- `hardware/BRINGUP-LOG.md` - new dated Phase 8 entry under `## Panel Observations`

## Decisions Made

See `key-decisions` in the frontmatter above. In summary: font weight became a per-theme property instead of a blanket value; Sky was retired in favour of 11 separate single-colour themes; a dithering bug was fixed by making flat-vs-dithered a per-theme property instead of a blanket 40% blend; tier 4's fallback text was changed to avoid duplicating the top-left state label.

## Deviations from Plan

**Scope expansion, explicitly developer-directed, not an auto-fix.** D-13's stated minimum was one coloured theme (black, yellow, or red); the developer chose to widen this live to all six Spectra 6 inks, each as both a pure and a dithered-light variant (11 registry entries total), and to retire Sky entirely in the process. `08-CONTEXT.md`'s own Claude's Discretion bullet explicitly permits widening the coloured-theme check at the developer's call, so this is within the plan's own anticipated scope, not a Rule-based auto-fix — recorded here rather than under "Auto-fixed Issues" because every step was developer-initiated and developer-confirmed in real time, not something the executor decided unilaterally.

**Tier 4's fallback text change is a locked-decision reopening**, explicitly out of the plan's bounded-correction scope ("Changing the content ladder's tier definitions... requires an explicit, recorded decision from the developer"). Obtained via an explicit multiple-choice question during the session (not a vague ask), the developer's choice ("Unknown flight") recorded verbatim, and the change re-rendered and re-confirmed on glass before the step closed — exactly the process the plan requires for this category of change.

### Auto-fixed Issues

None — every correction this session applied was developer-directed and developer-confirmed live, not unilaterally decided.

---

**Total deviations:** 0 auto-fixed. 2 developer-directed scope expansions/reopenings (theme-registry widening, tier-4 text), both following the plan's own explicit process for that category of change.
**Impact on plan:** No scope creep beyond what the developer explicitly asked for and re-confirmed on real ink in the same session.

## Issues Encountered

**A real bug, not a design disagreement:** the flat "Black" theme was rendering visibly grey. Root cause: `dither.dithered_state_background()`'s fixed 40%-toward-white blend, originally tuned for Phase 7's Blue/Green finding, was being applied unconditionally to every non-white theme rather than only to themes meant to be dithered. Caught by the developer directly on real glass ("Mais ton noir n'est pas noir là, il est gris"), fixed by making flat-vs-dithered a per-theme registry property.

**The panel.bin digest needed re-pinning a third time within this phase** (08-05 re-pinned it once; this session's font-weight, theme-registry, and tier-4-text changes moved pixels again). Resolved via the same real-CI-round-trip pattern 08-05 established: pushed the branch, reopened PR #22 to trigger CI, read the digest verbatim from CI's own FAIL output (not recomputed locally, since this Mac and CI's Linux container produce different digests for identical code — a documented, expected difference), re-pinned, closed the PR without merging.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **Phase 8 is complete.** Every change it made — White default, Bold-without-a-plate legibility, the four-tier content ladder, the previous card's nudge, and (well beyond the stated minimum) all 11 registered themes — has been judged against the real panel and recorded.
- **Phase 7's success criterion 7 (ROADMAP.md) is now discharged, and substantially exceeded.** That criterion asked for "2-3 alternate Blue/Green theme variants" for the CFG-01 picker; this phase instead shipped 11 fully separate, individually-validated single-colour themes spanning the entire Spectra 6 palette. The orchestrator should update ROADMAP.md's criterion 7 status accordingly.
- **Phase 7's wall-mounted re-check (D-03) is now closed.** Step G confirmed the frame wall-mounted (not a desk judgment) and reading as ambient art.
- **Carried forward, not closed by this phase:**
  - A-02-02-01's real +200ft/min departure threshold remains unvalidated against real sensor data — every real detection observed across Phase 7 and Phase 8 has still been an arrival.
  - DEVICE-05's unattended multi-day battery discharge run remains deferred to end-of-project.
- The frame is back on live detection: `skypane-poll.timer` is `active`, and a real post-restart poll cycle was observed in the journal.
- `git status --porcelain` is clean; the full local suite passes with only the documented, expected macOS/Linux font-rendering digest exception.

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*

## Self-Check: PASSED

All five modified files (`server/plane/render.py`, `server/device_config.py`, `server/test_render.py`, `server/test_poll_loop.py`, `hardware/BRINGUP-LOG.md`) confirmed present on disk; all five commit hashes (`95d2273`, `43380e2`, `efe0169`, `ef5b87d`, `5c3cc7d`) confirmed in `git log`.
