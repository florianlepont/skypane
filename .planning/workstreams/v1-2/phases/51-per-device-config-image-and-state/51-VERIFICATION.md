---
phase: 51-per-device-config-image-and-state
verified: 2026-10-30T23:00:00Z
status: passed
score: 3/3 roadmap criteria verified; both first-pass gaps closed; 0 open code gaps
re_verification:
  previous_status: gaps_found
  previous_score: 3/3 normal path, 2 medium gaps
  gaps_closed:
    - "BYOS fail-open to the live frame when fleet.db is unavailable (gap 1)"
    - "Second device row sharing the live state path '.' (gap 2)"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
human_verification:
  - test: "Run the 7 owner checks in 51-OWNER-CHECKS.md on a dev machine (selector, switching, per-device poll-now, quiet hours and timezone, never-seen state, live frame unchanged, single-device install)"
    expected: "Each check behaves as written; /devices/d_00000000/ is a 404 page; no cross-device change"
    why_human: "Visual and interaction behaviour. Playwright browser tests are SKIPPED in this environment (566 skips, Chromium not installed), so the selector and layout were not exercised here"
  - test: "Run the browser suite in CI or locally after `playwright install --only-shell chromium` (companion/test_browser_device_selector.py and companion/test_browser_home_state_card.py, whose tolerance was changed after a CI run)"
    expected: "Green"
    why_human: "Cannot launch a browser here"
  - test: "Owner decisions: (1) read the behaviour change of `fleet_cli devices add` (below); (2) before any production deploy of this phase, run `fleet_cli devices add --state-path auto` or hand-create live_frame_macs.json only if devices/ will exist; (3) no deploy until Phase 47 is finished and the owner approves; (4) test with a real second frame when one exists"
    expected: "Owner-side decisions, not code checks"
    why_human: "Decisions and hardware"
---

# Phase 51: Per-Device Config, Image and State, Verification Report

**Phase goal:** Each device has its own config, image, poll state, history and health, so one frame's settings and failures never affect another.
**Verified:** 2026-10-30 (re-verification after gap closure 51-14)
**Status:** human_needed (all code checks pass; only owner-side and browser checks remain)
**Re-verification:** Yes, after commits 0a7fb456, 319b4e45, eefcef58 and the merge of origin/main

## Independent runs (re-verification)

| Check | Result |
|---|---|
| Targeted suites plus backup, fleet_db, fleet_cli, fleet_migrate tests | 1083 passed |
| Full suite `pytest -n auto` | 5902 passed, 566 skipped (browser tests without Chromium, plus 2 environment skips), 0 failed |
| ruff, mypy, function-size gate (653 functions, none over 80), comment-history guard | clean |
| Frozen files: `git diff --stat $(cat 51-BASE-REF.txt) HEAD -- stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py hardware firmware` | empty (unmodified; the base ref predates the main merge, so no phase 47 or 50 file differs) |
| `git status` | clean (no uncommitted files from this verification) |

## Success criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Two simulated devices each get their own image from their own directory; live frame unchanged | VERIFIED | Unchanged from the first pass (token to MAC to fleet.db row to `device_dirs.resolve_state_dir`; `/img/<id>/<sha>.bin`; live keeps `/img/<sha>.bin`); freeze and negotiation tests green and unmodified. The degraded-mode exception is now closed (below) |
| 2 | Owner can poll one device and set its quiet hours and timezone; nothing else changes | VERIFIED | Unchanged: per-directory poll lock and cooldown, settings write only that device's directory |
| 3 | Each device shows its own history and health; no fallback to a shared default | VERIFIED | Companion: unknown id is the 404 page. BYOS: `_context_without_fleet_db` now fails closed, see attack results |

## Attack results on the new design

(a) Can a non-live device still get the live image or state? Probes (throwaway pytest harness in the scratchpad, `FrameServer` with the two-device seed, then damaging fleet.db):

| fleet.db condition | Non-live device | Live frame |
|---|---|---|
| corrupt (garbage bytes) | 503, live `battery_state.json` untouched | 200, own image |
| absent (db, wal, shm deleted) | 503 | 200 |
| truncated to 10 bytes | 503 | 200 |
| empty file | 503 | 200 |
| exclusively locked | request waits for the busy timeout, then follows the same unavailable path (any `sqlite3.Error` is "unavailable"); no leak, only latency | not measured past timeout |
| record `live_frame_macs.json` removed | 503 | refused too (fail closed for everyone) |
| race at first appearance of `devices/` | `fleet_cli devices add --state-path auto` writes the record (merged with existing, atomic write, aborts the add on failure) before `provision_device_dir`, inside the transaction; a crash between them leaves a record and no directory, which is harmless | n/a |

Residual, low: if an operator manually deletes the whole `devices/` directory while fleet.db is also unavailable, the install looks pre-fleet again and every authenticated MAC gets the live frame (observed 200). Requires two operator-level faults and removal of the frames' own directories; recorded as an accepted, documented-by-this-report limit, not a gap.

Residual, operational: an install that already has `devices/` but no record (dev machines only; Phase 51 is not deployed) is refused for every MAC when fleet.db is unavailable, live frame included, until fleet.db is healthy or the next `devices add --state-path auto` writes the record. Fails closed, not leaking.

(b) Live frame served and byte-identical: pre-fleet install (no `devices/`) serves every authenticated MAC the live frame with no `devices/` created (`test_pre_fleet_install_serves_the_live_frame_unchanged`); healthy migrated install resolves the "." row to the live context unchanged (`test_live_unchanged_url_hash_and_keys_with_other_devices`, freeze test); a corrupt fleet.db with the live MAC in the record still serves the live frame (probe above).

(c) `fleet_cli devices add` behaviour change on migrated installs: a device added without `--state-path auto` while a live row exists is now refused (exit 1; the summary says 2, the test asserts 1, cosmetic) before either store is touched; `fleet_db.add_device` also raises for a second ".". Assessment: acceptable and expand-only. The old behaviour created a second frame that silently shared the live frame's state and image, which defeats the phase; no stored data or on-device behaviour changes, the previous release's CLI is untouched on disk, and `fleet_migrate` opts out (`allow_shared_live`) so importing several legacy MACs works as before. The owner must know: (1) adding a replacement MAC for the live frame now needs `devices remove` then `add`, or `set-secret`; (2) three existing tests that registered a second frame without `auto` were adapted (`test_fleet_auth.py`, `test_ota_offer.py`, `test_ota_fleet_regression.py`) rather than removed, and the owner-check document carries a French warning.

(d) `live_frame_macs.json`: new root file, read only by the new BYOS code; the previous release never opens it (it reads named files only). The backup allow-list now includes it, and an actual run of `skypane_backup.py` on a state directory with the file produced an archive containing it. Restore is plain extraction, so it returns. Minor: `deploy/tests/test_backup.py` has no test naming this file (info only).

## Owner constraints D-01..D-20

Re-checked after the changes: live frame byte-for-byte (healthy and pre-fleet paths covered), freeze test unmodified, expand-only (new optional root file, new optional `timezone` key, no schema change from Phase 51), Phase 50 negotiation preserved, no production deploy, nothing in phase 47 files, hardware/ or firmware/, bilingual UI, route annotation hook intact, shared ROADMAP/STATE edits limited to Phase 51 lines (the merge of origin/main brought Phase 54 changes in cleanly).

## Requirements coverage

| Requirement | Status | Evidence |
|---|---|---|
| FLT-01 | SATISFIED | Criteria 1 and 3, both gaps closed. Not ticked here: REQUIREMENTS.md is left for the orchestrator |
| FLT-02 | SATISFIED | Criterion 2. The "or a user" part waits on Phase 54/60 access for the user role |

## Gaps

None open. Info items: browser tests not runnable here (above); backup test does not name the new file; `devices/` deletion residual (above).

## Owner-side items

- Run the 7 checks in `51-OWNER-CHECKS.md` (two simulated frames, dev machine) and the browser suite in CI.
- Read the `devices add` behaviour change above.
- Do not deploy to production until Phase 47 is finished and the owner approves; on a real second frame, add it with `--state-path auto` so the live-MAC record exists before `devices/` does.

## Follow-ups for the Phase 54 auth work (device routes)

1. Ownership hook in `_dispatch_for_device`, after `find_device`, before `route.handler`; use `Access(USER, "device")` and pass `route_match.device_id` as `captured`.
2. `device_scope.Device` has no `owner_user_id`; use `fleet_db.get_device_owner` or add it to `load_devices` and `find_device`.
3. Filter the selector and device list by ownership for non-admins; a non-owned id must give the same 404 as an unknown id.
4. Let `next` after sign-in accept `/devices/<id>/...` once ownership is enforced.
5. Keep the 27-route matrix completeness test aligned as roles open.
6. BYOS endpoints stay token-authenticated, never session-gated; `/img/<id>/<sha>.bin` is content-addressed and public by design.

## What later phases can rely on

- Phase 52: `poll_cycle.run_once(state_dir=<device dir>, reconcile_firmware=False)`, per-device `poll_state.json`, `history.db`, `battery_state.json`, `panel.bin`, `img/`; `device_dirs.resolve_state_dir` as the only path chokepoint; `device_scope.load_devices` to enumerate; exactly one "." live row and `live_frame_macs.json` as the live-MAC record. Shared provider spacing is not built.
- Phase 53: per-device `device_config.json` for per-device airport, runway and position keys (expand-only, omit when default); Display page and POST handler exist.
- Phase 56: BYOS takes width, height and byte count from the hardware profile; `device_scope.poll_supported` refuses poll-now for anything other than 1200x1600 and is the switch to lift.

## Closure

Closed on 2026-10-30 at the owner's explicit instruction. Status moved from `human_needed` to `passed`.

- The browser suite item was satisfied by CI: all checks were green on the merge commit of PR #244, including the Chromium tests.
- The 7 manual checks in `51-OWNER-CHECKS.md` were not run by Claude and are not recorded here as performed. The owner chose to close the phase without waiting for them and can still run them at any time.
- Still open and unchanged: no production deploy until Phase 47 closes and the owner decides; a real second frame must be added with `--state-path auto`.
