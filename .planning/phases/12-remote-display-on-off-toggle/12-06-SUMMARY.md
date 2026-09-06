---
phase: 12-remote-display-on-off-toggle
plan: 06
subsystem: ui
tags: [e-ink, spectra6, on-glass, render, dither, hold-screens, operator-loop]

# Dependency graph
requires:
  - phase: 12-remote-display-on-off-toggle
    provides: plans 12-01..12-05 — the display_enabled field, the display-off render state, the 300s sleep pin, the poll-loop hold latch, the Settings toggle
  - phase: 10-scheduled-quiet-hours
    provides: the quiet-hours hold screen and gate this session reworked and exercised alongside
provides:
  - The blocking on-glass verdict on Phase 12's new render state, in the developer's own words
  - The real operator loop walked end to end on the deployed frame with measured latencies
  - A redesign of all three hold screens on glass — the dimmed composition (DISPLAY OFF, QUIET HOURS) and its white variant (empty state) — through one shared routine
  - The Phase 12 entry in hardware/BRINGUP-LOG.md
affects: [any future hold screen, quiet-hours, empty-state, panel-typography, 10-UI-SPEC amendments]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_build_hold_canvas(): one composition for every hold screen — glyph, tracked Bold label, short rule, body — with the field (dimmed or white) as the parameter that says which kind of screen it is"
    - "Panel glyphs drawn from primitives (power ring, filled crescent traced from two discs, runway strip) — no vendored assets, nothing to attribute"
    - "Authored body lines (X_BODY_LINES) joined into the locked X_BODY_TEXT, wrapped per sentence — semantic breaks without breaking locked-copy assertions"
    - "On-glass design iteration: sketch candidates with render.py's own primitives, push each through _assert_legal_palette() before showing any, then force to the panel and wait for the journal's GET /img/<digest> line"

key-files:
  created:
    - hardware/BRINGUP-LOG.md (Phase 12 section)
  modified:
    - server/plane/render.py
    - server/test_render.py
    - .planning/phases/12-remote-display-on-off-toggle/12-CONTEXT.md
    - .planning/phases/12-remote-display-on-off-toggle/12-UI-SPEC.md
    - .planning/phases/10-scheduled-quiet-hours/10-UI-SPEC.md

key-decisions:
  - "D-03 revised on glass: the 'same shape as quiet hours' default is superseded; the off screen is a dimmed composition (Black dithered toward White, white ink) — by the developer's choice on the panel, not through the UI-SPEC's escalation ladder"
  - "Hold screens are a system: dark = the frame is resting on purpose (DISPLAY OFF, QUIET HOURS), white = the frame is working (empty state, flight boards); the two dark screens differ by glyph"
  - "Power ring on DISPLAY OFF, crescent on QUIET HOURS: the night-register glyph goes on the curfew screen, so it does not pull the off screen toward it"
  - "Bold for labels on dithered fields (thin white strokes drown in dither); Regular body at 40px confirmed legible on glass"
  - "Fail-closed tests retargeted, never relaxed: 120 (quiet packed panel Black-dominant), 129 (display-off field dominant), 64 (tracked empty heading reconstructed glyph-by-glyph)"
  - "One locked-copy change, made on glass: EMPTY_BODY_TEXT becomes 'No aircraft detected yet. The display updates the moment one is.' (the Phase 2 em dash retired)"

patterns-established:
  - "Forced-panel verification waits on the byos journal's GET /img/<digest>.bin for that render's own digest — never on the clock"
  - "A design change made on glass is recorded in three places the same day: the phase's CONTEXT decision, its UI-SPEC (SUPERSEDED block kept as record), and any other phase's UI-SPEC whose screen it touched"

requirements-completed: []  # unmapped phase (SEED-004); traced against 12-CONTEXT.md D-01 / D-02 / D-03 / D-05 / D-07

coverage:
  - id: D1
    description: "DISPLAY OFF judged on the real Spectra 6 panel, side by side with QUIET HOURS and the empty state, and validated in its final (dimmed) form"
    verification: []
    human_judgment: true
    rationale: "Screen previews mis-call contrast and dither on this panel (Phase 7, Phase 9 findings); only real ink settles legibility and distinguishability"
  - id: D2
    description: "The operator loop walked end to end on the deployed frame: off from Settings → dark within ~3 min → silent hold (93 check-ins, 0 fetches, 7 h 52 min) → back on within ~5 min 20 s"
    verification:
      - kind: other
        ref: "journalctl -u skypane-poll / -u skypane-byos, 2026-09-05 21:32 → 2026-09-06 05:33 UTC (timeline in hardware/BRINGUP-LOG.md)"
        status: pass
    human_judgment: true
    rationale: "Latencies are journal timestamps; whether the returned board is right is the developer's call on the glass"
  - id: D3
    description: "Frame left on live detection with the display enabled and the poll timer running (step F)"
    verification:
      - kind: other
        ref: "device_config.json display_enabled=true; systemctl is-active skypane-poll.timer; poll_loop cycles at 05:27:51/05:28:21/05:28:50"
        status: pass
    human_judgment: false
---

# Plan 12-06 — Blocking on-glass verification: summary

**Status: complete.** All five must-have truths hold; the developer's verdicts are recorded verbatim in `hardware/BRINGUP-LOG.md`'s Phase 12 section, which is the artifact of record. This file is the plan-level account.

## What happened

The plan expected to put 12-02's screen on the panel, capture a verdict, and apply "whatever bounded correction the glass calls for". The glass called for more than a bounded correction, and the session followed the developer rather than the plan's expectation:

1. **12-02's screen went up as shipped** (flat White, 72px Bold heading, the quiet-hours shape). The developer liked it and asked for a line break after "page." and a glyph above the heading. Both applied; the glyph choice (power ring, not the moon "sleep" suggests) was put to the developer explicitly, with the reasoning that a moon would pull the off screen toward the curfew screen.
2. **The developer asked for more elegance.** Five compositions were sketched with `render.py`'s own primitives, each pushed through `_assert_legal_palette()` before being shown, and the developer chose a blend of two: editorial typography (tracked Bold label, short rule, body) on a dimmed field (the Grey theme's dithered Black, white ink), keeping the power ring. Validated on glass on all three points named in advance — the field reads as an even grey, Regular white body holds at 40px, the Bold-class marks are crisp.
3. **QUIET HOURS was reworked in the same direction** at the developer's request, with a filled crescent as its mark, through one shared routine. Validated.
4. **The empty state followed**, on the same composition's white variant with a runway glyph, plus two copy adjustments from the glass: the body breaks before "The display", and the Phase 2 em dash was retired — the session's only locked-copy change, accepted from the preview by the developer's explicit choice.
5. **Steps C and D ran as planned.** Indicators approved on the dimmed screen. The operator loop ran overnight by accident of the hour and became the strongest evidence in the phase: 93 silent check-ins at a 304 s cadence, 0 image fetches, 920 server hold cycles without a repaint; off latency ≈ 3 min 07 s, on latency ≈ 5 min 20 s at the worst phase alignment.
6. **Step F** left the frame on live detection, display enabled, timer running, showing a real Iberia departure.

## Deviations from the plan

- **Scope: the glass redesigned three screens, not one.** The plan scoped "a bounded correction per the escalation ladder"; the developer, reading the screens in sequence on the panel, asked for a redesign of DISPLAY OFF and then for QUIET HOURS and the empty state to match. Done in session because the glass — the expensive, scheduled resource — was live, and recorded as a deliberate revision of 12-CONTEXT.md D-03 in the CONTEXT, in 12-UI-SPEC.md (original section kept, marked SUPERSEDED), and in 10-UI-SPEC.md (post-approval amendment). The distinguishability item the UI-SPEC flagged was thereby resolved by construction — dark versus white — rather than through the escalation ladder.
- **Step E (the quiet-hours overlap) was skipped**, and the plan asks for that to be said plainly rather than omitted. `quiet_hours_enabled` was `false` throughout, so the overnight hold — long as it was — never ran the two mechanisms together. The D-05/D-07 overlap therefore has no on-glass evidence; see Findings.
- **Files modified beyond the plan's list:** 12-CONTEXT.md, 12-UI-SPEC.md, 10-UI-SPEC.md (records of the design revision); `server/plane/render.py` and `server/test_render.py` were in the list but changed far more than a correction — see commits `4885206`, `84f3a62`, `ab4a3ec`, `24e2ef3`.
- **Production was updated by copying `render.py` over SSH** for steps A–C, because the pipeline deploys only from `main`. Production equals `HEAD` for that file, but a clean redeploy after the PR merges is owed.

## Findings for the developer

- **No code defects.** Every correction was design, copy, or test-targeting.
- **D-05's sleep axis did not run live.** `quiet_hours_enabled` was `false` overnight, so the max(300, remaining) composition — the one thing this phase's design was most careful about — has only its tests and their executed negative control as evidence. Worth a deliberate overlap night if it ever matters.
- **The 300 s pin did not change the cadence here** because `SKYPANE_SLEEP_S` was already 300; it held it. On a device with a longer wake interval the pin is what makes the return fast; that case is covered by 12-03's tests, not by this session.
- **Test infrastructure note:** `EXPECTED_CHECK_COUNT` stayed at 134 across the render harness changes because every retarget replaced a check rather than adding one.

## Verification

- `scripts/run-all-tests.sh`-level harnesses touched: render 134/134, panel-preview 11/11, poll-loop 60/60 (the documented macOS `panel.bin` digest NOTE present, unrelated); ruff clean.
- On-glass: developer verdicts verbatim in `hardware/BRINGUP-LOG.md`.
- Journal evidence for step D quoted with timestamps in the same entry.
