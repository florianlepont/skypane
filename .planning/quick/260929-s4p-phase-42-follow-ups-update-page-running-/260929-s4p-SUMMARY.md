---
phase: quick
plan: 260929-s4p
subsystem: companion-update-page, firmware-ota, deploy-docs
tags: [update-page, ota, firmware, docs]
requires: []
provides:
  - "update_view() per-release running and installed_now_at fields"
  - "Update page Running badge, honest Installed column, collapsed release notes"
  - "fp_ota_after_failure(): a failed OTA attempt re-displays the current picture in the same wake"
  - "deploy/README.md firmware_cli list command that works as the ubuntu operator"
affects: [companion/pages/update_page.py, server/firmware_registry.py, firmware/main/state_machine.c]
tech-stack:
  added: []
  patterns:
    - "one _ReleaseRow namedtuple feeds both the desktop table cells and the phone card"
    - "pure decision (fp_ota_after_failure) in ota_policy.c, host-tested, called from state_machine.c"
key-files:
  created: []
  modified:
    - server/firmware_registry.py
    - server/test_firmware_registry.py
    - companion/pages/update_page.py
    - companion/i18n_fr/update.py
    - companion/static/style.css
    - companion/test_update_page.py
    - companion/test_browser_update.py
    - firmware/main/state_machine.c
    - firmware/main/ota_policy.c
    - firmware/main/ota_policy.h
    - firmware/main/wake_deadline.h
    - firmware/main/wake_guard.c
    - firmware/main/Kconfig.projbuild
    - firmware/tests/test_ota_policy.c
    - firmware/tests/test_wake_deadline.c
    - firmware/VENDOR.md
    - deploy/README.md
    - deploy/tests/test_docs.py
decisions:
  - "Task 2 (developer override): after a failed OTA attempt the wake falls through into the normal image path instead of drawing the NO CONNECTION screen"
  - "Default wake budget raised 360 s to 460 s so the failing OTA wake (425 s stacked worst case) still fits"
metrics:
  tasks: 3
  commits: 3
completed: 2026-09-29
status: complete
---

# Quick 260929-s4p: Phase 42 follow-ups from the OTA hardware session

**Update page shows what is running and only that, and a failed OTA attempt now puts the current picture back on the glass in the same wake instead of leaving UPDATING up for the whole backoff.**

## Task 1: Update page (commit 00ccc242)

- `update_view()` gained `running` (the release whose version is the device's `X-Fw-Version`; none when nothing is reported) and `installed_now_at` (the running release's newest OTA install time, only when it is at least as new as every other release's newest install; otherwise None). The per-release loop moved into `_release_views()` to stay under the 80-line function gate.
- The Installed check now means "running". A release installed over the air earlier but no longer running shows `Last installed <time>` / `Dernière installation : <time>` and no check. The real-hardware case (bench installed 15:27, fw-v1.0.0 running after a USB flash) shows the check and badge only on fw-v1.0.0, with no borrowed time.
- Running / En cours badge after the version (same composition as the bench badge), plus a visually-hidden Running label beside the check.
- Notes: a single note of 120 characters or fewer renders in place; otherwise an escaped word-boundary excerpt (ending with an ellipsis) and a closed no-JS `<details class="update-history__notes">` "Show notes" / "Afficher les notes" holding every note. Every note is escaped in `update_page.py` because column 2 is now a raw column (T-s4p-01, covered by a `<script>` note test). One `_ReleaseRow` feeds both the table and the phone card.
- CSS: two small rules scoped under `.update-history__notes` / `-list`, no new colour, token or accent use. Render baseline unchanged.
- Tests: 6 registry unit tests (including the hardware case, rollback, no-report), 13 page tests (EN and FR, both badges on one row, escaping), and a Playwright test at 375x812 and 1280x900 in EN and FR (closed by default, summary at least 44 px and inside the viewport, click reveals all 30 notes, no horizontal overflow, Install visible and enabled). Mutation check: forcing `open` on the details makes the browser test fail.

## Task 2: firmware, as implemented (commit f142461f)

**Developer decision overrides the plan.** The plan drew the NO CONNECTION fault screen after a failed update. That was rejected as meaningless UX ("it makes no sense UX-wise, it means nothing"), and so was any new "update failed" mask. Implemented instead:

After an OTA attempt fails within a wake, `fp_poll_once()` records the result token, clears the try marker (exactly as before) and does not return `FP_POLL_FAILED`. It makes sure Wi-Fi is up (one more join when the OTA-path join was the failure), then falls through into the normal image path. `draw_updating_screen()` always writes the sentinel image hash, so the hash check never skips and the current picture is fetched and redrawn, or deferred by the panel guard as on any healthy wake. If Wi-Fi cannot be brought back, the wake fails with the existing step `ota`; any later failure in the normal path keeps its usual step token.

Why this and not the plan: the viewer sees the real picture again, with no misleading offline state, no new mask/sentinel, and no second code path for drawing.

- The decision is pure and host-tested: `fp_ota_after_failure(radio_up)` in `ota_policy.c` returns continue-poll or fail-wake. Test proven to fail without the fix (a mutation returning fail-wake always trips the first assert; before the function existed the test did not compile).
- Consequences, documented in `VENDOR.md` (the `ota` token bullet, the `state_machine.c` row, a new `ota failed result=<token> continuing poll` diagnostic line, the `ota_policy`/`wake_deadline` bullets): the wake counts as healthy, so there is no failure backoff and attempts arrive at the normal wake cadence (the 300/600/1200 s spacing is gone, intended); the failure is still reported on the next poll and still counts toward MAX_ATTEMPTS. Success paths (switch and restart), trial/confirm logic and the rollback-safety invariant are untouched; a pending trial never reaches this path because `fp_ota_decide()` refuses offers then.
- `fault_screen.c/.h` were not touched (the plan's `fp_fault_screen_should_draw("ota")` change and `fp_wake_has_room_s()` are not built, since nothing uses them).
- Verification: `run_host_tests.sh` (13 suites), `check_log_contract.sh`, the real container build `./firmware/build.sh` (the `_Static_assert`s held), and `check_production_config.sh built firmware/build-ee02` all pass. No flashing, no signing.

## Deviations from Plan

**1. [Developer override] Task 2 approach replaced** (see above).

**2. [Rule 3 - Blocking] Wake budget raised, OTA worst-case stack extended.** Continuing into the picture path after a failed update adds the picture download (30 s) and its blit (70 s) to the OTA stage stack: `FP_WAKE_OTA_WORST_CASE_S(90)` goes 325 to 425 s, which breaks the existing `_Static_assert` against the 360 s budget. The default `CONFIG_SKYPANE_WAKE_BUDGET_S` is raised 360 to 460 s (same precedent as 300 to 360 for the original OTA stages; range and Kconfig help updated). Real timings are far below the stage budgets (OTA about 65 s, image about 3 s, draw about 32 s). The budget is only a ceiling for a hung wake, so a wedged wake can now stay awake up to 100 s longer before being cut off. A new `_Static_assert` records that the panel-guard spacing owed before the second blit (at most `CONFIG_FP_MIN_REFRESH_SPACING_S`) must not outlast the OTA stage that already covers it. The developer may want to revisit the number.

**3. [Rule 1 - Test flip] `test_releases_render_newest_first_with_install_form_and_installed_column`** expected a check mark on a non-running installed row; updated to the new semantics as the plan foresaw.

## Task 3: deploy docs (commit 98e47d2c)

`deploy/README.md`: the `list` example now runs `sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec ... list'` inside the same `ssh ubuntu@<vps-ip> "..."` wrapper, with a sentence on why, plus a note that `<public-host>` (byos: display endpoint, `GET /fw/<sha256>.bin`) differs from `<companion-host>` (Update page). Placeholders only. `deploy/tests/test_docs.py` gained two firmware-section checks (every `server.firmware_cli` command in a code fence has the `cd` inside the skypane shell first; both placeholders present and no `.ovh`); the first fails against the old command. The command shape was proven locally with an empty scratch state dir (exit 0, "no releases published").

## Verification

- Task 1 verify command: 300 passed; function-size, comment-history, ruff, mypy ok; `render_baseline.json` unchanged.
- Final gate `scratchpad/fullcheck.sh`: ruff, comment-history, mypy, function-size, shellcheck all ok; `NEW FAILURES:` followed by nothing (the parallel run's 56 failures and 7 errors all pass on the serial rerun or are the known environment-only set).
- Screenshots (375x812 and 1280x900, EN and FR, each closed and with the notes open; running release with a newest OTA install time, a previously installed release, a 30-note release), in `/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-unidentified-airlines-flights-a4ce95/4840a370-ce78-4678-8f31-9c57b90f640e/scratchpad/`:
  - `update-en-375x812-closed.png`, `update-en-375x812-open.png`
  - `update-en-1280x900-closed.png`, `update-en-1280x900-open.png`
  - `update-fr-375x812-closed.png`, `update-fr-375x812-open.png`
  - `update-fr-1280x900-closed.png`, `update-fr-1280x900-open.png`

## Known Stubs

None.

## Threat Flags

None. T-s4p-01 (notes escaping), T-s4p-02 (display-only badge) and T-s4p-04 (placeholders only, tested) are handled as planned. T-s4p-03 (extra blit on the OTA failure path) now applies to the picture redraw instead of a fault-screen blit: it is gated by the panel guard's spacing/deferral and by the raised, statically asserted wake budget.

## Notes for the orchestrator

- `hardware/BRINGUP-LOG.md` still lists "UPDATING screen stays on the glass after a failed OTA attempt" as a follow-up (a historical session record, left as written).
- Not verified on hardware: no flashing was done. The failed-attempt path (fall-through, retry join, second draw after the UPDATING blit) is covered by host tests for the decision and by a clean container build only.

## Self-Check: PASSED

Commits 00ccc242, f142461f and 98e47d2c exist on `claude/phase-42-followups`; the modified files listed above exist; `git status` shows only this untracked quick-task directory.
