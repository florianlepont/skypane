---
phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
plan: 05
subsystem: testing
tags: [pillow, pytest-style-harness, ci, sha256-digest, ruff, systemd]

# Dependency graph
requires:
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 03
    provides: "PT Serif Bold weight switch and removed text-backing-plate, one of the four pixel-moving causes reconciled in the digest re-pin"
  - phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue
    plan: 04
    provides: "PREVIOUS_TEXT_LEFT_OFFSET_PX=20 (D-12) and the four-tier content ladder, both of which this plan's checks depend on"
provides:
  - "server.test_render's D-12 spot-check across six deliberately diverse airline illustrations (narrowbody x2, turboprop, small twin, regional jet, widebody), backed by a new _TextBBoxSpy helper"
  - "server.test_poll_loop._DEFAULT_CONFIG_DIGEST re-pinned from a real CI run (ce9235f6...), with a fourth dated standing-rule comment entry"
  - "server.plane.render's forced-panel restart reminder and its own comment corrected from a pre-rename unit name to the real skypane-poll.timer"
  - "A 12-file visual sweep (/tmp/08-05-sweep/) of the six sampled illustrations, tier 1 and tier 3, for plan 08-06's shortlist"
affects: [08-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_TextBBoxSpy: monkeypatches ImageDraw.ImageDraw.textbbox to capture its RETURN VALUE (not just the call), so a check can read the actual measured bbox a text run received without re-deriving fit_text_size()'s font-fitting logic independently"

key-files:
  created: []
  modified:
    - server/test_render.py
    - server/test_poll_loop.py
    - server/plane/render.py
    - .planning/spikes/001-panel-theme-colours/explore.py

key-decisions:
  - "Sample of six airline names chosen for genuine airframe diversity, each confirmed via illustrations.py's own _ILLUSTRATION_TARGETS/_TYPE_SHAPE_BUCKETS tables (not guessed) and verified live against select_illustration(): Air France -> air-france.png (narrowbody, A320/B737 baseline), Vueling Airlines -> vueling-airlines.png (narrowbody, A320 family), Chalair Aviation -> chalair-aviation.png (turboprop, ATR72), Twin Jet -> twin-jet.png (small twin turboprop, Beechcraft 1900D), LOT Polish Airlines -> lot-polish-airlines.png (regional jet, Embraer E-Jet family), Air Caraïbes -> air-caraibes.png (widebody, A350 family primary)"
  - "The permanent safe-box check reads real measured bboxes via a new _TextBBoxSpy (monkeypatching ImageDraw.textbbox's return value) rather than re-deriving fit_text_size()'s font logic independently - a re-derivation would go stale the moment that logic changes"
  - "The deliberate overflow demonstration needed PREVIOUS_TEXT_LEFT_OFFSET_PX=870-900, not the plan's suggested 400 - at 400 the anchor still sits ~13px inside the safe box for every sampled route/text combination tried; 900 was used for a comfortably negative margin. This also proved the new check catches a real overflow BEFORE production's own _assert_within_canvas() would (which only guards the full 1200-wide canvas, not the 64px SAFE_BOX inset)"
  - "A pre-existing, unrelated ruff lint failure (.planning/spikes/001-panel-theme-colours/explore.py, two unused PIL imports, last touched by a prior spike-001 commit) was fixed as a narrow Rule 3 exception to the scope boundary against fixing pre-existing/unrelated issues - CI's lint step gates the test-suite step entirely, and Task 2 explicitly requires a real CI round trip. Fixed in its own separate, clearly-labeled commit so it is trivially distinguishable from the plan's three tasks."
  - "A GitHub PR (#22) was opened against main purely as a CI trigger vehicle (this repo's workflow only runs on push-to-main or pull_request, and the working branch had no open PR), then closed without merging once CI confirmed green - the branch's four commits are the actual deliverable, not the PR"

patterns-established:
  - "_TextBBoxSpy: capture ImageDraw.textbbox()'s return value the same way _TextSpy captures .text()'s arguments - lets a check assert on real measured geometry without re-implementing font-fitting logic"

requirements-completed: [D-12]

coverage:
  - id: D1
    description: "The previous card's 20px optical offset holds its shared-anchor and safe-box invariants across six airline illustrations with deliberately different airframe silhouettes, not just the single Air France/Vueling pair D-12 was tuned against (08-CONTEXT.md D-12's own caveat)"
    requirement: "D-12"
    verification:
      - kind: unit
        ref: "server/test_render.py#_previous_card_optical_offset_holds_across_diverse_illustration_sample"
        status: pass
    human_judgment: false
  - id: D2
    description: "The pinned panel.bin digest guard is restored to a working regression detector reflecting the panel this phase actually produces, read verbatim from a real CI run rather than recomputed locally"
    verification:
      - kind: integration
        ref: "server/test_poll_loop.py#_default_config_byte_identity (CI: github.com/florianlepont/skypane/actions/runs/33384640381, PASS)"
        status: pass
    human_judgment: false
  - id: D3
    description: "The whole 15-harness suite passes under the configured coverage threshold in CI - the authoritative platform - with the sole local (macOS) exception being the documented, pre-existing, out-of-scope cross-platform digest mismatch"
    verification:
      - kind: other
        ref: "scripts/run-all-tests.sh via GitHub Actions ubuntu-latest, run 33384640381: 15/15 harnesses green, 90% coverage, Result: PASS"
        status: pass
    human_judgment: false
  - id: D4
    description: "The forced-panel restart reminder names the real systemd unit (skypane-poll.timer) the deployed host actually runs, closing the naming-drift item carried forward from 07-01-SUMMARY.md"
    verification:
      - kind: unit
        ref: "server/test_render.py#_synthetic_reminder_printed_when_override_combined_with_out"
        status: pass
      - kind: other
        ref: "grep -c inkframe server/plane/render.py == 0"
        status: pass
    human_judgment: false
  - id: D5
    description: "Whether the six-illustration sample and the fourth theme's re-pinned pixels genuinely look right on real Spectra 6 glass - not resolvable by any automated check in this plan"
    verification: []
    human_judgment: true
    rationale: "The 12-file visual sweep (/tmp/08-05-sweep/) is screen-only and does not satisfy D-13 - plan 08-06's blocking on-glass session is the gate for this, and this plan's own summary hands it the shortlist of files to look at."

# Metrics
duration: ~27min
completed: 2026-08-31
status: complete
---

# Phase 8 Plan 05: Suite reconciliation - D-12 spot-check, digest re-pin, restart reminder fix Summary

**Closed all three loose ends this phase's rendering changes left open: D-12's 20px offset validated across six deliberately different airframes via a real CI round trip, the panel.bin digest re-pinned from that same CI run to a green 15-harness suite, and the forced-panel restart reminder corrected to name the systemd unit the deployed host actually runs.**

## Performance

- **Duration:** ~27min (10:35:16Z - 11:01:53Z)
- **Started:** 2026-08-31T10:35:16Z
- **Completed:** 2026-08-31T11:01:53Z
- **Tasks:** 3 (plus one out-of-scope-but-necessary lint fix, see Deviations)
- **Files modified:** 4

## Accomplishments

- **Task 1 (D-12 spot-check):** Added a permanent, parameterised check to `server/test_render.py` spanning six airline illustrations with genuinely different airframe silhouettes - narrowbody x2 (Air France, Vueling Airlines), turboprop (Chalair Aviation), small twin turboprop (Twin Jet), regional jet (LOT Polish Airlines), and widebody (Air Caraïbes) - each name's resolution to its exact vendored file confirmed against `illustrations.py`'s own tables before hardcoding, not guessed. The check proves both previous-card lines share one anchor x (`content[2] - PREVIOUS_TEXT_LEFT_OFFSET_PX`, written against the constant) and that neither line's bbox crosses `SAFE_BOX`'s left edge - a genuinely new, stricter invariant than production's own `_assert_within_canvas()`, which only guards against falling off the full 1200px canvas. A new `_TextBBoxSpy` helper (mirrors `_TextSpy`'s monkeypatch-and-restore shape, applied to `ImageDraw.textbbox()`'s return value) makes this possible without re-deriving font-fitting logic. `EXPECTED_CHECK_COUNT` raised 97->98. `git diff server/plane/render.py` was empty for this task, confirmed. A 12-file visual sweep (6 airlines x tier-1/tier-3) was generated directly via `render.build_canvas()` (the same production path the CLI itself uses) into `/tmp/08-05-sweep/`, since the CLI's `--airline` flag only overrides the main card's route, not the previous card's.
- **Task 3 (restart reminder):** `server/plane/render.py`'s forced-panel reminder previously named `inkframe-poll.timer`, a pre-rename unit that does not exist on the deployed host - worse, a legacy unit under that exact old name was found running and failing on the VPS during Phase 7 and had to be stopped and disabled (`.planning/STATE.md`), so the stale name was actively misleading, not merely outdated. Corrected to `skypane-poll.timer`, cross-checked against `deploy/skypane-poll.timer`/`deploy/skypane-poll.service`. Every other service/path/interpreter string in the module (the manual-QA docstring's `server/.venv/bin/python3` commands) was checked against the deploy directory and confirmed already correct - those are local dev commands, not deployed-host paths. `server/test_render.py`'s pre-existing reminder check, which literally asserted the old unit name, was updated in place (no new check needed).
- **Task 2 (digest re-pin):** Established the true starting state first (`scripts/run-all-tests.sh`, 14/15 harnesses green locally, the digest the sole expected failure), then pushed the branch, opened PR #22 purely to trigger GitHub Actions CI (this repo's workflow only runs on push-to-main or `pull_request`), and read the real digest verbatim from CI's own FAIL output rather than recomputing locally - the standing rule's own documented caveat (this Mac and CI's Linux container produce different digests for identical code) held again. Re-pinned `_DEFAULT_CONFIG_DIGEST` to `ce9235f6ceaf2fc4563f5eae7ee63f51bb962bc68fb67860682e315e4b8e8479`, added a fourth dated standing-rule comment entry naming all four causes of this phase's pixel movement (White default theme, PT Serif Bold + `PREVIOUS_LINE2_FONT` growth, removed backing-plate, four-tier content ladder + D-12 offset). Pushed again; CI confirmed **full green**: 15/15 harnesses, 90% coverage, `Result: PASS`. Locally (macOS) the harness still shows the known cross-platform mismatch against the newly-pinned CI value - documented as expected, not a regression. PR #22 closed without merging once CI confirmed the re-pin.

## Task Commits

Each task was committed atomically:

1. **Task 1: Spot-check the previous card's 20px optical offset across a diverse illustration sample** - `9e53353` (test)
2. **[Deviation, Rule 3] Remove unused PIL imports blocking CI lint gate** - `606d7f9` (fix)
3. **Task 3: Point the forced-panel restart reminder at the systemd unit that actually exists** - `d7c6355` (fix)
4. **Task 2: Re-pin the panel.bin digest from CI and bring the full 15-harness suite green** - `fa3b345` (test)

_Tasks committed out of their numeric order (1, 3, then 2) because Task 2's real CI round trip needed Task 3's changes already committed and pushed, and the lint-blocking deviation had to land before any push could reach the test-suite step at all._

## Files Created/Modified

- `server/test_render.py` - new `_TextBBoxSpy` class; new `OFFSET_SPREAD_AIRLINES` sample + `_previous_card_optical_offset_holds_across_diverse_illustration_sample()` check (98th check, `EXPECTED_CHECK_COUNT` 97->98); existing reminder check's literal `inkframe-poll.timer` string corrected to `skypane-poll.timer`
- `server/plane/render.py` - forced-panel reminder string and its comment corrected from the pre-rename unit name to `skypane-poll.timer`; no other pre-rename strings found in the module
- `server/test_poll_loop.py` - `_DEFAULT_CONFIG_DIGEST` re-pinned; fourth dated standing-rule comment entry added
- `.planning/spikes/001-panel-theme-colours/explore.py` - two unused PIL imports (`Image`, `ImageFont`) removed (pre-existing, unrelated to this plan, fixed only to unblock CI's lint gate - see Deviations)

## Decisions Made

- The six-airline sample and each airframe classification are recorded in the `key-decisions` frontmatter field above, cross-checked against `illustrations.py`'s live `select_illustration()` behavior before being hardcoded into the test.
- The deliberate overflow demonstration needed a much larger offset (870-900) than the plan's suggested "try 400" - at 400 the anchor margin against `SAFE_BOX`'s left edge was still ~13-73px positive across every route/text combination tried; 900 produced a comfortably negative margin (-26px) while production's own `_assert_within_canvas()` still passed (bbox left edge still >= 0), proving the new check catches a real, narrower-than-canvas overflow production code does not.
- The pre-existing, unrelated ruff lint failure in a spike script was fixed as a documented Rule 3 exception to the scope boundary (see Deviations below) rather than deferred, because CI's lint step gates the test-suite step entirely and Task 2 explicitly required a real CI round trip - not merely "CI reachable in principle."
- PR #22 was opened solely as a CI-trigger vehicle (this repo's `ci.yml` only runs on push-to-main or `pull_request`, and the working branch had no upstream PR) and closed without merging once CI confirmed green - it carries no code the four commits on `claude/amelioration-rendu-tableau-bcd0ce` don't already have.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking, scope-boundary exception] Removed two unused PIL imports blocking CI's lint gate**

- **Found during:** Task 2, first CI push attempt
- **Issue:** `.planning/spikes/001-panel-theme-colours/explore.py` (last touched by an unrelated prior spike-001 commit, `97e3519`) imported `PIL.Image` and `PIL.ImageFont` without using either - `ruff check .` flagged both as F401 and CI's lint step failed before the test-suite step ever ran, which meant no digest could be read from CI's output at all. This is exactly the kind of "pre-existing warning in an unrelated file" the scope boundary instructs to defer rather than fix - but deferring it would have made Task 2's explicit, plan-mandated real-CI-round-trip requirement impossible to satisfy in this session.
- **Fix:** Confirmed both imports were unused anywhere else in the file (`grep`), then ran `ruff check --fix` scoped to that single file only. Verified `ruff check .` (repo-wide) passes clean afterward.
- **Files modified:** `.planning/spikes/001-panel-theme-colours/explore.py`
- **Verification:** `ruff check .` exits 0 repo-wide; the change is a pure dead-import removal with zero behavioral surface (confirmed via grep before removing).
- **Committed in:** `606d7f9`, its own separate commit (not folded into any of the three tasks' commits) so it is trivially distinguishable and revertible on its own.

---

**Total deviations:** 1 auto-fixed (Rule 3, scope-boundary exception documented above)
**Impact on plan:** Necessary and narrowly scoped - a two-import removal in a throwaway documentation script, with zero behavioral change, that was the sole blocker preventing Task 2's mandated real CI round trip. No scope creep beyond this.

## Issues Encountered

None beyond the documented deviation above. The CI round trip itself worked exactly as the standing rule in `server/test_poll_loop.py` predicts: the locally-computed macOS digest (`29d0d120773a68a4762b1258dcb8f723b70861cca9e6a75edc6491f1a39ee17e`) differed from CI's Linux-computed digest (`ce9235f6ceaf2fc4563f5eae7ee63f51bb962bc68fb67860682e315e4b8e8479`) for byte-identical code - confirming, for the fourth time in this file's own history, that this is a real font-rendering environment difference and not something a local recomputation could ever correctly substitute for.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The full 15-harness suite is green in CI (the authoritative platform) at 90% coverage - plan 08-06's on-glass session can proceed against a suite that actually detects regressions again, not a permanently-red digest check everyone has learned to ignore.
- D-12's 20px optical offset is validated across a genuinely diverse six-file sample (narrowbody x2, turboprop, small twin, regional jet, widebody): right-padding spread across the sample is 5-12px (7px delta) - **no outlier found**; both the shared-anchor and safe-box invariants held for every sampled file. Nothing needs re-tuning before the on-glass session.
- A 12-file visual sweep is ready at `/tmp/08-05-sweep/` (`air-france-tier1.png`/`-tier3.png`, `vueling-airlines-tier1.png`/`-tier3.png`, `chalair-aviation-tier1.png`/`-tier3.png`, `twin-jet-tier1.png`/`-tier3.png`, `lot-polish-airlines-tier1.png`/`-tier3.png`, `air-caraibes-tier1.png`/`-tier3.png`) - plan 08-06's shortlist for which illustrations are worth spending a panel refresh on, in addition to the four verbatim CLI commands `08-04-SUMMARY.md` already recorded.
- The render CLI's own printed output (`--help`, the module docstring, and the forced-panel restart reminder) is now trustworthy - an operator running plan 08-06's session can copy-paste the reminder's unit name directly instead of having to know it's stale, closing the open item `07-01-SUMMARY.md` carried forward.
- None of this phase's rendering changes (White default theme, PT Serif Bold, removed backing-plate, four-tier content ladder, D-12 offset) have been seen on real Spectra 6 glass yet - screen-confirmed only, via this plan's own sweep and the prior three plans' preview PNGs. Plan 08-06's blocking on-glass session is where that check finally happens, closing out Phase 8.

---
*Phase: 08-panel-theme-rework-white-default-theme-black-yellow-red-blue*
*Completed: 2026-08-31*

## Self-Check: PASSED

All four modified files (`server/test_render.py`, `server/plane/render.py`, `server/test_poll_loop.py`, `.planning/spikes/001-panel-theme-colours/explore.py`) confirmed present on disk; all four commit hashes (`9e53353`, `606d7f9`, `d7c6355`, `fa3b345`) confirmed in `git log`.
