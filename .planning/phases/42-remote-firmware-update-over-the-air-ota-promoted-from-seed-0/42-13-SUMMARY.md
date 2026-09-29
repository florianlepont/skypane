---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 13
subsystem: firmware
tags: [ota, firmware, c, esp-idf, rollback, wake-loop]

# Dependency graph
requires:
  - phase: 42-02
    provides: "ota_policy.c/.h's pure OTA decisions (fp_ota_decide,
      fp_ota_should_confirm, fp_ota_boot_classify) this plan's
      state_machine.c/app_main.c call, never re-derive"
  - phase: 42-04
    provides: "updating_screen.c/.h's fp_updating_screen_render,
      FP_UPDATING_SCREEN_BYTES/HASH, drawn by this plan's new
      draw_updating_screen() helper"
  - phase: 42-08
    provides: "ota.c/.h's fp_ota_apply/fp_ota_boot_check/
      fp_ota_confirm_if_pending/fp_ota_mark_try/fp_ota_record_result
      and api_client.c's parsed fp_display_t.fw offer, which this
      plan wires into the wake loop's call sites"
provides:
  - "state_machine.c: an OTA branch between the LED preference and the
    hash-skip, so an offer lands even on a wake where the picture is
    unchanged — skip/refuse continue the normal poll, start draws the
    UPDATING screen and either esp_restart()s into the trial image or
    fails through the single failure exit with step token 'ota'"
  - "app_main.c: fp_ota_boot_check() as early as NVS is usable (before
    the reset-reason failure exit) and fp_ota_confirm_if_pending() as
    the last call before the healthy path's enter_deep_sleep() — the
    rollback-safety ordering this whole phase exists to get right"
  - "wake_deadline.h: FP_WAKE_STAGE_OTA_S / FP_WAKE_OTA_WORST_CASE_S,
    a second wake_guard.c _Static_assert gating the configured budget
    against both the normal and the OTA worst case at compile time"
  - "VENDOR.md: every firmware change of the whole phase recorded, the
    ota Log Line Contract token and its six new diagnostic lines
    documented, the stale pre-OTA rollback/CA-bundle operational notes
    replaced"
affects: ["42-16 (hardware session proves confirm/rollback on real
  glass)", "any later Phase 42 plan touching state_machine.c or
  app_main.c"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "OTA decision call sites live in state_machine.c/app_main.c, but
      every actual decision is a call into ota.c/ota_policy.c — this
      plan is wiring only, matching the pattern plan 08's own SUMMARY
      established"
    - "draw_updating_screen() in state_machine.c mirrors app_main.c's
      maybe_draw_fault_screen(): radio down before the panel, a PSRAM
      buffer, the shared hold-screen renderer, a sentinel hash written
      whatever the draw result"

key-files:
  created: []
  modified:
    - firmware/main/state_machine.c
    - firmware/main/state_machine.h
    - firmware/main/app_main.c
    - firmware/main/wake_deadline.h
    - firmware/main/wake_guard.c
    - firmware/tests/test_wake_deadline.c
    - firmware/VENDOR.md

key-decisions:
  - "FP_WAKE_OTA_WORST_CASE_S is an alternative worst case to
    FP_WAKE_WORST_CASE_S, not additive to it — an OTA wake never also
    downloads and blits the normal display image, so both macros are
    gated by their own _Static_assert against the same configured
    budget rather than summed into one bound"
  - "The OTA branch sits after the LED preference and before the
    hash-skip in fp_poll_once(), matching the plan's own interface
    contract and upstream's precedent (42-RESEARCH.md Pattern 2): an
    offer must land even on a wake where the picture is unchanged"
  - "draw_updating_screen() writes FP_UPDATING_SCREEN_HASH to
    FP_NVS_IMAGE_HASH unconditionally — drawn, deferred by the panel
    guard, or skipped for no PSRAM — so the next successful poll
    always redraws the current mode's picture rather than treating a
    half-drawn UPDATING screen as already on glass"
  - "fp_ota_boot_check() runs before the reset-reason abnormal-reset
    failure exit, not after: a crash on a trial image must be
    classified even on the wake that routes straight to a failure
    sleep without ever reaching fp_poll_once()"
  - "fp_ota_confirm_if_pending() is the last call before
    enter_deep_sleep(plan.sleep_s) on the healthy path only — every
    failure exit (fail_and_sleep, the deadline/reset/json exits) never
    reaches it, matching the confirm rule's own contract"

requirements-completed: []  # OTA-02/03/06/07's device-side wiring is
                            # fully delivered by this plan, but their
                            # hardware-proof half (signed install,
                            # forced-crash rollback — OTA-12) is still
                            # shared with plan 42-16's hardware session,
                            # so REQUIREMENTS.md is left Pending per
                            # this phase's established convention (see
                            # 42-01/42-03/42-08's precedent).

coverage:
  - id: D1
    description: "The device marks a trial image valid after the
      first successful poll and before that same wake's deep sleep,
      never on a later wake; a failed poll, crash or watchdog reset on
      the trial image leaves it unconfirmed so the bootloader rolls
      back"
    requirement: "OTA-03"
    verification:
      - kind: other
        ref: "awk ordering check: fp_ota_confirm_if_pending(); is the
          last call before enter_deep_sleep(plan.sleep_s) in
          app_main.c (d-c==1); grep -c 'fp_ota_confirm_if_pending();'
          firmware/main/app_main.c == 1"
        status: pass
    human_judgment: true
    rationale: "The ordering is proven by source-order gates here; the
      actual rollback behaviour on a real crash/watchdog reset is
      proven on hardware in a later plan (42-16), not host-testable."
  - id: D2
    description: "An offer is applied before the image hash-skip, so
      it lands even on a wake where the picture is unchanged"
    requirement: "OTA-02"
    verification:
      - kind: other
        ref: "awk ordering check: disp.fw.present precedes the
          FP_NVS_IMAGE_HASH, last_hash hash-skip read in
          state_machine.c"
        status: pass
    human_judgment: false
  - id: D3
    description: "When an update starts the UPDATING screen is drawn
      in every mode, the radio is down during the blit, and the
      image-hash sentinel forces the next successful poll to redraw"
    requirement: "OTA-07"
    verification:
      - kind: other
        ref: "draw_updating_screen() in state_machine.c: fp_api_release
          ()/fp_wifi_stop() before fp_panel_draw(), FP_NVS_IMAGE_HASH
          set to FP_UPDATING_SCREEN_HASH unconditionally; no
          quiet-hours/display-off gate exists on this call path"
        status: pass
    human_judgment: false
  - id: D4
    description: "The device refuses to start below its own battery-
      low level and reports deferred-battery without drawing or
      downloading"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "firmware/tests/test_ota_policy.c#decide_cases (plan
          42-02's fp_ota_decide, called by state_machine.c before any
          draw or download)"
        status: pass
    human_judgment: false
  - id: D5
    description: "A failed download, size, hash, image/signature or
      floor check ends the wake through the single failure exit with
      step token ota, counting toward normal backoff; a successful
      switch restarts (not deep sleep) into the trial image"
    requirement: "OTA-02"
    verification:
      - kind: other
        ref: "grep -c 'esp_restart' firmware/main/state_machine.c >=1;
          grep -c 'esp_deep_sleep_start(' firmware/main/state_machine.c
          == 0; sh firmware/tests/check_log_contract.sh (ota token
          documented and extracted)"
        status: pass
    human_judgment: false
  - id: D6
    description: "The wake budget covers the worst-case OTA wake,
      enforced at compile time"
    requirement: "OTA-02"
    verification:
      - kind: unit
        ref: "firmware/tests/test_wake_deadline.c#ota_worst_case_macro_matches_its_own_stacked_stage_budgets"
        status: pass
      - kind: integration
        ref: "bash firmware/build.sh (real espressif/idf:v5.3.1
          container build; wake_guard.c's second _Static_assert
          compiles clean against the real CONFIG_SKYPANE_WAKE_BUDGET_S
          / CONFIG_FP_MAX_GUARD_WAIT_S)"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 13: Wire OTA into the wake loop (confirm-before-sleep) Summary

**state_machine.c applies an offer before the hash-skip (battery/floor refusal, UPDATING screen, download, restart, or fail with backoff) and app_main.c classifies a boot outcome as early as NVS is usable and confirms a trial image as the very last call before its first healthy deep sleep — the phase's highest-risk ordering, source-order-gated and proven by a real container build.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-28
- **Tasks:** 3 (1 TDD, 2 direct)
- **Files modified:** 7

## Accomplishments

- `firmware/main/wake_deadline.h` gains `FP_WAKE_STAGE_OTA_S` (90 s,
  a conservative esp_https_ota download budget) and
  `FP_WAKE_OTA_WORST_CASE_S(guard_wait_s)` — an alternative worst case
  to `FP_WAKE_WORST_CASE_S`, never additive to it, stacking Wi-Fi,
  SNTP, setup, display, the panel-guard wait, the UPDATING-screen
  blit, a second Wi-Fi join after the trial reboot, and the OTA
  download itself (325 s at the default guard wait). `wake_guard.c`
  gains a second `_Static_assert` gating the configured 360 s budget
  against both worst cases, proven with a TDD RED/GREEN cycle in
  `test_wake_deadline.c`.
- `state_machine.c`'s `fp_poll_once()` now decides on an offered
  release (`fp_ota_decide`) between the LED preference and the hash-
  skip, so an offer lands even on a wake where the picture is
  unchanged: same-version and a battery/floor refusal (recorded, not a
  failure) continue the normal poll; a start marks the trial version,
  draws the on-device UPDATING screen through a new
  `draw_updating_screen()` helper (radio down before the panel, the
  image-hash sentinel written whatever the draw result), reconnects
  Wi-Fi, and calls `fp_ota_apply()` — success logs and `esp_restart()`s
  straight into the trial image (never deep sleep), failure records
  the result and ends the wake through the single failure exit with
  step token `ota`.
- `app_main.c` calls `fp_ota_boot_check()` as early as NVS is usable,
  before the reset-reason abnormal-reset failure exit, so a crash-
  induced rollback is classified even on a wake that never reaches
  `fp_poll_once()`. `fp_ota_confirm_if_pending()` is the last call
  before the healthy path's `enter_deep_sleep(plan.sleep_s)` — proven
  by an `awk` source-order gate, not merely a comment.
- A real `espressif/idf:v5.3.1` container build (`bash
  firmware/build.sh`) compiled and linked the whole tree with the new
  wiring; `firmware/tests/check_production_config.sh built
  firmware/build-ee02` confirmed the resolved signed-app/rollback
  Kconfig chain (from plan 42-03) still ships correctly.
- `firmware/VENDOR.md` now records every firmware change of the whole
  phase: the `ota` Log Line Contract token and its six new diagnostic
  lines, `ota.c`/`ota.h`/`ota_policy.c`/`ota_policy.h` provenance rows,
  updated `api_client.c/.h`/`nvs_schema.h`/`state_machine.c`/
  `app_main.c` rows, and the stale pre-OTA "rollback disabled"/"no OTA
  path for the CA bundle" operational notes replaced with the current
  signed-update/confirm/rollback behaviour.

## Task Commits

Each task was committed atomically:

1. **Task 1: OTA wake budget and compile-time assertion** (TDD):
   - `c030a464` (test) RED — failing/non-compiling assertions for `FP_WAKE_OTA_WORST_CASE_S`
   - `9be48494` (feat) GREEN — the macro, the second `_Static_assert`, all 13 host suites pass
2. **Task 2: OTA branch in the state machine and confirm-before-sleep in app_main** - `d782a8d1` (feat)
3. **Task 3: VENDOR.md record and Log Line Contract token** - `be485224` (docs)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `firmware/main/wake_deadline.h` - `FP_WAKE_STAGE_OTA_S`, `FP_WAKE_OTA_WORST_CASE_S`
- `firmware/main/wake_guard.c` - second `_Static_assert` against the OTA worst case
- `firmware/tests/test_wake_deadline.c` - the new macro's host-test coverage
- `firmware/main/state_machine.c` - the OTA branch and `draw_updating_screen()`
- `firmware/main/state_machine.h` - header comment reworded (see Deviations)
- `firmware/main/app_main.c` - `fp_ota_boot_check()` / `fp_ota_confirm_if_pending()` call sites
- `firmware/VENDOR.md` - Log Line Contract, Vendored Files, Original To This Repository, Operational notes

## Decisions Made

See `key-decisions` in the frontmatter above — the worst-case macro is
an alternative, not additive; the OTA branch sits before the hash-skip;
the UPDATING-screen hash sentinel is written unconditionally; the boot
check runs before the reset-reason exit; the confirm call runs only on
the healthy path's last line before deep sleep.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded `state_machine.h`'s header comment, now inaccurate**
- **Found during:** Task 2, immediately after wiring the OTA branch into `state_machine.c`
- **Issue:** `state_machine.h`'s file comment claimed upstream's "OTA evaluation... branch[es] — none of which is compiled into this project" — literally false once this plan's OTA branch lands. `state_machine.h` is not in this plan's `files_modified` list.
- **Fix:** Reworded the comment to describe the OTA branch as now compiled, pointing at `ota.c`/`ota_policy.c` as the actual decision owners
- **Files modified:** `firmware/main/state_machine.h`
- **Verification:** Read-through; the comment no longer contradicts the code it sits above
- **Committed in:** `d782a8d1`

**2. [Rule 1 - Bug] Two decision-ID citations in a new comment**
- **Found during:** Task 2, pre-commit `check_comment_history.py check`
- **Issue:** A new comment in `state_machine.c`'s OTA branch cited "D-12/D-11" — forbidden by the project's comment-history rule
- **Fix:** Reworded to describe the rationale (battery/floor refusals are not failures) without the decision IDs
- **Files modified:** `firmware/main/state_machine.c`
- **Verification:** `server/.venv/bin/python3 scripts/check_comment_history.py check` exits clean
- **Committed in:** `d782a8d1`

**3. [Rule 1 - Bug] Duplicate grep match on the acceptance criterion's own literal**
- **Found during:** Task 1, verifying `grep -c 'FP_WAKE_OTA_WORST_CASE_S' firmware/main/wake_guard.c` is 1
- **Issue:** The `_Static_assert`'s explanatory comment repeated the macro name literally, making the count 2
- **Fix:** Reworded the comment to reference the macro's home file without repeating its name
- **Files modified:** `firmware/main/wake_guard.c`
- **Verification:** `grep -c` returns 1; host tests still pass
- **Committed in:** `9be48494`

**4. [Rule 2 - Missing Critical] Two stale VENDOR.md claims contradicted the code plan 42-03 already shipped**
- **Found during:** Task 3, reading the current file before editing
- **Issue:** `sdkconfig.defaults`'s row still said "app rollback disabled (no OTA path exists to use it)" and the Operational notes still said "there is no OTA path to push an updated CA bundle" and "App rollback stays disabled... until this project implements OTA" — all three false since plan 42-03 already flipped rollback on and added the signed-app Kconfig chain, and this plan now wires the confirm/rollback machinery those settings gate
- **Fix:** Rewrote all three to describe current behaviour (rollback on, signed updates, the CA bundle now ships through a normal signed release) and removed the now-inaccurate "OTA firmware update — not yet built" line from Deliberately Not Vendored
- **Files modified:** `firmware/VENDOR.md`
- **Verification:** `grep -c 'CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n' firmware/VENDOR.md` is 0; read-through
- **Committed in:** `be485224`

---

**Total deviations:** 4 auto-fixed (1 file-outside-scope comment fix, 1 comment-history bug, 1 acceptance-criterion self-inflicted grep collision, 1 missing-critical docs accuracy fix)
**Impact on plan:** All four were necessary for correctness (an accurate VENDOR.md is this plan's own Task 3 deliverable) or to satisfy the plan's own acceptance criteria. No scope creep beyond what each fix required.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The device-side OTA flow (offer decision, UPDATING screen, download/
  verify/switch, restart, boot classification, confirm-before-sleep)
  is now fully wired end to end in firmware, with every ordering
  invariant gated by a host test, a compile-time assert, or a source-
  order grep/awk check in this plan's own acceptance criteria.
- `REQUIREMENTS.md` intentionally left untouched: OTA-02/03/06/07's
  device-side wiring is complete, but they are shared with plan
  42-16's hardware session (OTA-12's signed-install/rollback proof),
  so `requirements mark-complete` was not called — matching this
  phase's established convention.
- Real behaviour (signed install, unsigned/tampered rejection, forced-
  crash rollback, factory recovery) remains proven on hardware in a
  later plan (42-16), per this plan's own `<verification>` note.
- No blockers for the next plan in this phase.

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 7 modified files verified present on disk; all 4 task commit
hashes (`c030a464`, `9be48494`, `d782a8d1`, `be485224`) verified in
`git log --oneline --all`.
