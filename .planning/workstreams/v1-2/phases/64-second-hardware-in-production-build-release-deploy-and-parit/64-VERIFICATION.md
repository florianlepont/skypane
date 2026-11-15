---
phase: 64-second-hardware-in-production-build-release-deploy-and-parit
verified: 2026-11-15T20:00:00Z
status: human_needed
score: 5/9 criteria fully validated (1, 2, 3, 4, 8); 1 validated with bench evidence for one part (5); 3 open (6, 7, 9)
verdict: verified with open points, not complete
re_verification: false
open_points_owner_action:
  - "Criterion 6: deploy PRs #439, #440, #441 and check the previews and the landscape hold marks on a real frame (not possible from the repository)"
  - "Criterion 7: busy waits, battery sense, ADC enable, LED and keys not measured; wake-stage blit 190 s and budget 700 s still a formula"
  - "Criterion 9: invited user in English, English-language pairing/assign/retire/re-activate/detection cells, console and account battery percentages"
---

# Phase 64: Second Hardware in Production - Verification Report

**Phase goal:** The second hardware type (Seeed EE04, 7.3 inch) is built, released, deployed, updated over the air and managed in production the way the live frame's type is, so the owner can run both kinds of frame side by side.
**Verified:** 2026-11-15 against `origin/main` at `58095df0` (PRs up to #441).
**Verdict:** verified with open points. The phase is NOT complete: criteria 6, 7 and 9 are open. Criteria 5 is validated for the update itself and by bench evidence for the failing-update case.
**Method:** SUMMARY claims were not taken as evidence. Evidence comes from the workflow and script files on `main`, a local test run, the owner's recorded reports in `64-OWNER-VALIDATION.md` and `64-WALKTHROUGH.md`, and `hardware/SECOND-HARDWARE-MEASUREMENTS.md`. Phase 64 plans 14 and 15 (owner checkpoints) have no SUMMARY; their outcome lives in the two owner records.

Note on `64-WALKTHROUGH.md`: on `main` row 13 still reads "open" (not seen on a real frame). The unmerged branch `gsd/phase-64-walkthrough-marks` (commit `48555b89`) records a row 13 fail and Gap 4: in the default giant layout the landscape marks overlapped the last text line (found by rendering with the repo's code, not on a real frame). That defect has since been fixed and merged: PR #440 (marks at the top right, quick `261115-nxj`) and PR #441 (shorter caption, quick `261115-qy5`). The fix is awaiting the owner's deploy and a visual check on a real frame, which is not possible from here: no real-frame render of those holds exists.

## Per-criterion result

| # | Criterion | Status | Evidence / what is missing, who acts |
|---|-----------|--------|--------------------------------------|
| 1 | CI builds the second board in the production profile, built check, size gate | VALIDATED | `.github/workflows/firmware.yml` job `build-second`: `SKYPANE_BOARD=second ./firmware/build.sh`, `check_production_config.sh built firmware/build-second second`, size limit 90 % of the 0x250000 OTA slot. Latest `firmware.yml` runs on main concluded success (2026-11-14, 2026-11-15, checked with `gh run list`). Test `deploy/tests/test_production_config_board.py` exists. |
| 2 | One tag builds, signs, verifies, publishes typed image + manifest; live assets unchanged; live-only release still imports | VALIDATED | `.github/workflows/firmware-release.yml` has typed steps (`--hardware-type seeed-ee04-7in3-spectra6`, `release-seeed-ee04-7in3-spectra6.json`, `skypane-seeed-ee04-7in3-spectra6-<tag>.bin`) next to the unchanged live-frame names. Real run: owner record B shows release `fw-v1.2.0` with all four assets, observed by the agent on GitHub. Live-only import is covered by `server/test_firmware_cli.py` and `deploy/tests/test_release_assets.py` (local run below). |
| 3 | Production deploy fetches/imports typed assets; unknown or unavailable type does not fail activation | VALIDATED | `ci.yml` allow-lists names through `scripts/fw_release_assets.py`; `deploy/activate.sh` forwards the switch only when exactly `1`; `server/firmware_cli.py` prints `skipped <name> [<key>]: hardware type not available here` instead of failing. Real deploy: CI run 43715715341 logged `added fw-v1.2.0 seeed-ee04-7in3-spectra6` (owner record B). The `registry.seeed-ee04-7in3-spectra6.json` file was not seen directly at that point, but it was pasted later (see 5). |
| 4 | Dedicated switch, simulated types stay hidden, lifted only on the owner's written confirmation; gate pin tests changed on purpose | VALIDATED | `server/hardware.py`: `SKYPANE_ENABLE_SECOND_HARDWARE` ("1" only) exposes only the real gated type; `SKYPANE_SIM_HARDWARE` separate. Owner's written confirmation recorded verbatim 2026-11-15 (record A); the owner added the env line by hand ("oui, c'est fait"); the deploy log confirms the switch was read. One field of record A stays `open`: "checked first: no second-type row that should not start being served" was never filled in. |
| 5 | Real signed https OTA on a second-type frame, result recorded in its own registry by the production poll, a failing update keeps the previous firmware | VALIDATED BY BENCH EVIDENCE for the failing-update part; success part VALIDATED on the owner's report | Success: owner record C, firmware fw-v1.2.0 to fw-v1.2.1 on MAC 84:c7:bb:70:b2:7c; owner pasted the byos journal (download 14:53:46, trial 14:54:46, installed 15:00:17) and the registry (`last_outcome` installed fw-v1.2.1, `installed_at` 15:00:20). Failing update: not provoked in production, by the owner's decision (record D); used instead is the Phase 58 bench: wrongly signed `fw-v1.0.7-bench2` rejected on this unit (dev profile, throwaway keys, bench server), unit stayed on `fw-v1.0.6-bench1` (`firmware/SIGNING.md`, "Bench results"), plus automated reconcile tests (`server/test_firmware_reconcile.py`, in the local run). Code: `server/fleet_cycle.py` calls `firmware_registry.apply_reconcile_other_types`, which reconciles every available non-legacy type independently of the live cycle. **Open sub-points:** (a) https not observed directly, only implied (frame provisioned with an https `--api-base`, production image refuses http); (b) the registry file does not show whether the production poll or another cycle wrote the result; (c) no failing update in a production registry. Owner can close (a) and (b) from the journal/`fleet_cli`; (c) is by decision left on bench evidence. |
| 6 | Companion follows the frame's profile: previews with frame shape and crop, landscape hold marks, battery percentages on the frame's own curve | OPEN | Automated: tests for profile-aware previews (`companion/test_theme_preview_profile.py`), curve at call sites (`companion/test_battery_curve_call_sites.py`), landscape hold marks (`server/test_render_landscape_hold.py`, `server/test_giant_status_marks_landscape.py`). Real use: walkthrough row 12 failed (landscape picture in a portrait container, gaps 2 and 3); fixed by PR #439 (quick `261115-m9e`) and merged, but the owner has not re-checked it. Row 13 (hold marks) never seen on a real frame; the defect found by rendering (Gap 4) was fixed by #440/#441 and awaits deploy and a visual check on a real frame, which cannot be done from the repository: the marks are verified by automated tests and rendered images only. Row 14 (account page and console battery percentages) not verified by the owner. The landscape chip crop opinion is pending (and quick `261115-m9e` notes the theme chip is no longer used by any companion page). Owner acts. |
| 7 | 7.3 inch firmware assumptions settled with measured values where a measurement exists | OPEN (partly measured) | Measured on the unit 2026-11-15 (`hardware/SECOND-HARDWARE-MEASUREMENTS.md`): full refresh 25 / 27 / 27 s (five refreshes, stopwatch, dev profile bench build) and flash size 16 MB. Not measured, left provisional: busy waits after init, refresh and power-off (items 2-4), battery sense GPIO and divider, ADC enable pin, LED pin and polarity, KEY0-2 pins (items 6-9), battery discharge profile (item 10; Phase 58 had no valid discharge sample). Plan 64-12 Task 3 (apply measured values) never ran (`64-12-SUMMARY.md` status partial-awaiting-owner): `firmware/main/wake_deadline.h` still carries the blit stage 190 s derived by a formula (`3 * 60 + 10`), the wake budget 700 s is unmeasured, and `FP_MIN_REFRESH_SPACING_S` is not set in `firmware/sdkconfig.second.defaults` (firmware default, not tuned; the measured 27 s is not yet applied or explained there). Battery profile, LED and buttons are provisional by design, moved to production use and Phase 65 (battery curve validation). Owner measures; agent applies afterwards. |
| 8 | Documents describe both boards; `provision.sh` refuses the live frame; no Phase 47/47.1 file touched | VALIDATED, with one stale paragraph | `firmware/tests/check_provision_guard.sh` passes locally (refuses declared live port, refuses live MAC, typed MAC required, dry-run refuses live MAC). The guard works from owner-declared `SKYPANE_LIVE_FRAME_PORT` / `SKYPANE_LIVE_FRAME_MAC` plus the typed MAC, not by detecting the board type (stated in the script header; chip cannot tell). Deploy README documents typed assets, the switch, and the `fleet_cli` environment (fixed in #426 after the owner's finding). No commit since 2026-11-13 touches `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json` or `.planning/phases/47*`; `test_phase47_freeze.py` passes. **Stale text:** `firmware/SIGNING.md` ("Status:" paragraph near line 151) still says the first typed release is unpublished and the workflow does not build the second board, which is false since fw-v1.2.0; a docs fix is needed. |
| 9 | Owner pairs, administers and manages a second-type frame as administrator and invited user, in English and French | OPEN (owner-validated step, partly recorded) | `64-WALKTHROUGH.md` holds the owner's recorded reports. Passed in French as administrator: assign, layout, display off (off screen shown), quiet hours, detection, health, battery, retire (panel shows the retired image), re-activate from the phone. Update (fw-v1.2.1) passed as administrator in English. Invited user (non-admin owner) in French: owner reported "j'ai tout vérifié, tout est bon" for layout, display on/off, quiet hours, detection, health, battery, without detail. Not done or open: **invited user in English** (all U EN cells open); pairing and several actions in English or French not stated; display back on and the redraw at the next wake not reported; desktop re-activation menu fixed by #434 and still to be re-checked after deploy; row 12 and 13 (see criterion 6); row 14 battery percentages on the account page and console not verified. Not marked validated: the record is incomplete. |

## Observable truths vs the roadmap contract

| Group | Result |
|-------|--------|
| Build, release, deploy, switch (1-4) | Achieved in code, CI and one real release and deploy. |
| OTA (5) | One real second-type OTA recorded on the owner's report and logs; failing case on bench evidence only. |
| Companion parity (6), firmware values (7), owner walk-through (9) | Not complete. |
| Documents and guard (8) | Achieved apart from the stale `firmware/SIGNING.md` status paragraph. |

## Behavioural spot-checks and probes

Run in this verification (repository root, `origin/main` `58095df0`):

| Check | Command | Result |
|-------|---------|--------|
| Gate, typed import, reconcile, landscape holds, release assets and manifest, activate, Phase 47 freeze | `pytest server/test_hardware.py server/test_firmware_cli.py server/test_firmware_reconcile.py server/test_render_landscape_hold.py deploy/tests/test_release_assets.py deploy/tests/test_release_manifest.py deploy/tests/test_activate.py stub-server/test_phase47_freeze.py -n 4` | 312 passed |
| Typed provision guard | `sh firmware/tests/check_provision_guard.sh` | all PASS |
| Firmware CI | `gh run list --workflow firmware.yml --branch main` | last three runs success |
| Probes | none declared by this phase | not applicable |

The full suite, C host tests and a firmware build were not re-run here (no Docker); CI results and the owner's records stand for those.

## Open points (honest list)

1. Failing-update case in production: not provoked; Phase 58 bench evidence used (criterion 5).
2. Battery profile, LED pin, buttons, battery sense, ADC enable and the separate panel busy waits are provisional (moved to production use and Phase 65).
3. Wake-stage blit 190 s and wake budget 700 s come from a formula, unmeasured; refresh spacing not tuned; plan 64-12 Task 3 not run.
4. Invited user in English: not checked.
5. Console and account battery percentages: not checked by the owner (battery values provisional anyway).
6. Landscape chip crop: owner's opinion pending (the chip is no longer used by a companion page).
7. Landscape hold marks: verified by automated tests and rendered images only; not on a real frame. Fix #440/#441 awaits the owner's deploy and visual check.
8. Possibly dead type-chooser UI on the Update page: `GET /update` redirects to a frame's Fleet view when a frame of the type exists, and the Fleet view pins the frame's type with no chooser (quick `261115-iy9`); the chooser is reachable only from the standalone render. Whether it is dead code is to be decided, not claimed.
9. The thin serif source-fault caption is hard to read on dithered dark screens (quick `261115-qy5` concern); to judge on a real frame.
10. Smaller record gaps: https channel and the poll that recorded the result not observed directly (criterion 5); "no second-type row that should not start being served" unchecked in record A; `firmware/SIGNING.md` stale status paragraph; the deploy of #430, #434, #439-#441 and the owner's re-check are pending.
11. Walkthrough remarks 4-6 and the retired-frame listing are inputs for `SEED-019` (renumbered SEED-020 in the roadmap split), not Phase 64 failures.

## Ordering

Phase 59 stays last; nothing here changes that. Phase 65 validates the battery curves.

---

_Verified: 2026-11-15_
_Verifier: Claude (gsd-verifier)_
