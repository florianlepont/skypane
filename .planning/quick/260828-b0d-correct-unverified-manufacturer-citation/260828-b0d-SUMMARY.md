---
phase: 05-low-battery-indicator
plan: 260828-b0d
subsystem: firmware,docs
tags: [kconfig, panel-guard, poll-loop, documentation-correction, provenance]

requires:
  - phase: 05-low-battery-indicator
    provides: FP_MIN_REFRESH_SPACING_S / FP_MAX_GUARD_WAIT_S Kconfig options and panel_guard.h, already shipped
provides:
  - Corrected, checkable provenance for the 60s panel-refresh floor and the 90s guard ceiling
affects: [firmware-docs, server-docs, DEVICE-03]

tech-stack:
  added: []
  patterns:
    - "Comment-only correction pattern: pin a pre-computed digest of a file's non-comment/non-declaration content before editing prose, so a review can prove zero behavioural drift"

key-files:
  created: []
  modified:
    - firmware/main/Kconfig.projbuild
    - firmware/main/panel_guard.h
    - server/poll_loop.py

key-decisions:
  - "Named the real panel component (Good Display GDEP133C02, identified by cross-matching resolution/active-area/weight/connector spec against Seeed SKU E-6569) as the citation target, replacing an unnamed vendor claim that could not be verified"
  - "Stated the datasheet's actual refresh-frequency guidance (minimum 24h between refreshes, against ghosting/image sticking) rather than silently deleting the reasoning chain, since deleting the claim while keeping the framing would have preserved a false implication"
  - "Reframed 60s/90s as this project's own engineering margin against the measured ~31.5s redraw and battery cost, not a vendor-mandated wear threshold - the numbers themselves did not change"

requirements-completed: [DEVICE-03]

coverage:
  - id: D1
    description: "FP_MIN_REFRESH_SPACING_S's Kconfig help text rewritten around the verified GDEP133C02 datasheet finding and this project's own engineering-margin rationale; declarations/ranges/defaults byte-identical"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "plan-pinned structural digest check (88 lines, sha256 39195fe0...) + sh firmware/tests/run_host_tests.sh"
        status: pass
    human_judgment: false
  - id: D2
    description: "panel_guard.h's module docstring and the fp_panel_guard_after_sleep closing clause rewritten to match the same finding; enum and all three function prototypes byte-identical"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "plan-pinned comment-stripped payload digest check (sha256 ea4c5d27...) + sh firmware/tests/run_host_tests.sh"
        status: pass
    human_judgment: false
  - id: D3
    description: "server/poll_loop.py's MAX_STALENESS_S comment loses its vendor-corroboration citation; constant, derivation and every other pacing value unchanged"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "plan-pinned non-comment content digest check (491 lines, sha256 f83ccdc5...) + server/test_poll_loop.py (22/22) + ruff check"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-28
status: complete
---

# Quick Task 260828-b0d: Correct Unverified Manufacturer Citation Summary

**Removed an unverifiable panel-vendor citation (once-per-day update recommendation, 150s reliability-interval envelope) from three comment bodies and replaced it with the real, checkable datasheet finding for the Good Display GDEP133C02 - the opposite-direction 24-hour minimum-refresh guidance - while proving by digest that zero executable content moved.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 3 completed
- **Files modified:** 3

## Accomplishments

- `firmware/main/Kconfig.projbuild`'s `FP_MIN_REFRESH_SPACING_S` help text no longer attributes an unverifiable once-per-day recommendation or a 150s "tested envelope" to the panel vendor. It now names the real component (Good Display GDEP133C02, identified by cross-matching against Seeed SKU E-6569), states plainly what the datasheet does and does not document about refresh frequency (no max rate, no cycle-count rating; a 24-hour *minimum* against ghosting/image sticking - the opposite direction), draws the honesty boundary explicitly ("absence in the document consulted" is not "unlimited refresh life"), and reframes 60s as this project's own conservative engineering margin against the measured ~31.5s redraw and the battery it spends. Closed with a durable source note (document name, section/item numbers, retrieval date).
- `firmware/main/panel_guard.h`'s module docstring tells the same corrected story in short form, pointing at `CONFIG_FP_MIN_REFRESH_SPACING_S` for the full reasoning rather than duplicating it. The one downstream clause that restated the same wear premise (`fp_panel_guard_after_sleep`'s closing justification) was reworded to cite the real cost (redraw churn and battery) it actually guards against; the argument itself (timer-wake-only crediting the full interval) is unchanged.
- `server/poll_loop.py`'s `MAX_STALENESS_S` comment lost its three-line "Corroborating coincidence" sentence that cited the now-retracted claim via a cross-reference into the Kconfig help text. The real derivation (2m30s as the never-drop-a-flight vs. never-show-stale tradeoff point) was never dependent on that citation and is untouched.
- Every correction is backed by a pre-recorded digest of that file's non-comment/non-declaration content, computed before the edit: zero drift in any Kconfig default/range, the `panel_guard.h` enum and all three function prototypes, or any `poll_loop.py` constant/import/function body.

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite FP_MIN_REFRESH_SPACING_S's help text** - `065eec5` (docs)
2. **Task 2: Bring panel_guard.h's docstring into line with the same finding** - `503e701` (docs)
3. **Task 3: Drop the vendor-corroboration citation from poll_loop.py** - `161cacc` (docs)

_No plan-metadata commit yet - STATE.md/ROADMAP.md/REQUIREMENTS.md updates and this SUMMARY.md are committed separately by the orchestrator per the constraints of this session._

## Files Created/Modified

- `firmware/main/Kconfig.projbuild` - `FP_MIN_REFRESH_SPACING_S` help body rewritten (3 lettered points + source note); every declaration/range/default byte-identical (structural digest verified, 88 lines)
- `firmware/main/panel_guard.h` - module docstring rewritten; `fp_panel_guard_after_sleep` closing clause reworded; enum and all three prototypes byte-identical (comment-stripped digest verified)
- `server/poll_loop.py` - `MAX_STALENESS_S`'s trailing corroboration sentence (3 lines) deleted; all code/constants byte-identical (non-comment digest verified, 491 lines)

## Decisions Made

- Named the real panel component (Good Display GDEP133C02) rather than leaving the citation anonymous, per the plan's `<datasheet_findings>` - this is what makes the correction checkable rather than a repeat of the original failure.
- Kept the numeric values (60, 90, 150 as `MAX_STALENESS_S`) unchanged throughout; only the stated justification for the 60s/90s figures changed, from an unverifiable vendor threshold to this project's own measured engineering margin.
- Deleted `poll_loop.py`'s cross-reference into the Kconfig help text along with the claim it pointed at, rather than leaving a pointer into text that no longer supports it (avoids the dangling-citation failure mode called out in the plan's threat model, T-B0D-04).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - verification-script bug in own draft] Two required literal substrings initially split across a line break, failing the plan's `grep -qF` checks**
- **Found during:** Task 1 and Task 2 verification runs
- **Issue:** The first draft of `Kconfig.projbuild`'s help text wrapped "engineering margin" across two lines, and the first draft of `panel_guard.h`'s docstring wrapped "image sticking" across two lines - both required literals for the plan's fixed-string greps (`grep -qF 'engineering margin'`, `grep -qF 'image sticking'`), which fail on a substring split by a newline.
- **Fix:** Reworded each passage so the two-word phrase sits on one line, without changing any of the surrounding meaning or the three lettered points' content.
- **Files modified:** `firmware/main/Kconfig.projbuild`, `firmware/main/panel_guard.h`
- **Verification:** Re-ran each task's full `<verify><automated>` command; all conditions passed, including the previously-failing `grep -qF` checks.
- **Committed in:** `065eec5` (Kconfig), `503e701` (panel_guard.h) - each fix is part of that task's single commit, not a separate one.

---

**Total deviations:** 2 auto-fixed (both Rule 1, both pre-commit draft corrections to satisfy the plan's own verification greps - no scope creep, no behavioural change).
**Impact on plan:** None on scope or intent; both fixes were caught by the plan's own automated verification before committing, exactly as the digest/grep scaffolding is designed to catch.

## Issues Encountered

`bash scripts/check-attribution.sh` fails when invoked with `sh` (POSIX sh does not support the script's `<(...)` process substitution) but passes cleanly under `bash` - a pre-existing environment quirk unrelated to this plan's changes, noted here rather than "fixed" since the plan's own verification commands invoke it correctly and it was not touched.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The 60s/90s panel-pacing constants and their documentation now rest entirely on claims this project can substantiate. No further action needed; Phase 05's device/server slices (05-02, 05-03) are unaffected - this task touched only comment prose in files those plans also touch, and all three plans' respective digests/tests confirm no collision.

---
*Quick task: 260828-b0d-correct-unverified-manufacturer-citation*
*Completed: 2026-08-28*

## Self-Check: PASSED

All 3 modified files and the SUMMARY.md itself verified present on disk; all 3 task commit hashes (`065eec5`, `503e701`, `161cacc`) verified present in `git log --oneline --all`.
