---
phase: 51-per-device-config-image-and-state
verified: 2026-10-30T21:30:00Z
status: gaps_found
score: 3/3 roadmap criteria verified in the normal path; 2 medium gaps in degraded and operator paths, 0 blockers for the three criteria as tested
re_verification: false
gaps:
  - truth: "No fallback to a shared default device (criterion 3), BYOS side, when fleet.db cannot answer"
    status: partial
    severity: medium
    reason: >
      stub-server/byos_server.py `_device_context` returns `_live_context` for ANY authenticated MAC whenever
      `_fleet_row` is `_FLEET_UNAVAILABLE` (fleet.db absent, not migrated, or in a fault state). Tokens of all
      devices are mirrored in byos_state.json (issue_token writes both stores), so a non-live device's token still
      authenticates from the legacy file. Result: with fleet.db corrupt or unreadable, the second frame is served
      the live frame's image and image_url, its X-Battery-Mv overwrites the live battery_state.json, and the live
      state dir drives its sleep_s. test_legacy_without_fleet_db_every_mac_is_the_live_frame asserts this as intended
      for a legacy install, but it also covers the fault case, which is fail-open rather than fail-closed.
    artifacts:
      - path: "stub-server/byos_server.py"
        issue: "_device_context: `if row is _FLEET_UNAVAILABLE: return _live_context(args, mac)`"
      - path: "stub-server/test_device_fleet.py"
        issue: "test_legacy_without_fleet_db_every_mac_is_the_live_frame enshrines the fallback; no test for a fault (corrupt) fleet.db"
    missing:
      - "Fail closed (503) when fleet.db is unavailable but the install has per-device directories (devices/ present, or the migrated marker or a non-live byos token known); keep the live fallback only for a true pre-fleet install (fleet.db never existed)"
      - "A test with a corrupt fleet.db and a non-live token that expects 503, not the live image"
  - truth: "Each device has its own directory; a second device never shares the live frame's state (FLT-01), operator path"
    status: partial
    severity: medium
    reason: >
      fleet_db.add_device and `fleet_cli devices add` default to state_path "." and nothing enforces a single "."
      row (no unique index, no check). Reproduced: two add_device calls with the default created two rows both with
      state_path ".", so the second frame shares the live frame's config, panel, poll state and history, and is served
      the live image. Using `--state-path auto` is the only safe path and 51-OWNER-CHECKS.md does not tell the owner so.
      companion `load_devices` also overwrites `live` with the last "." row, so only one of the two is listed.
    artifacts:
      - path: "server/fleet_db.py"
        issue: "add_device accepts a second state_path '.'; schema has no uniqueness on it"
      - path: "stub-server/fleet_cli.py"
        issue: "--state-path default is '.'"
    missing:
      - "Reject a second '.' row in add_device (or a partial unique index; expand-only, since production has exactly one '.')"
      - "Make the CLI refuse 'devices add' without --state-path auto once a live row exists, and say so in the owner docs"
deferred: []
human_verification:
  - test: "Run the 7 owner checks in 51-OWNER-CHECKS.md on a dev machine (selector, switching, per-device poll-now, quiet hours and timezone, never-seen state, live frame unchanged, single-device install)"
    expected: "Each check behaves as written; unknown /devices/d_00000000/ gives a 404 page; no cross-device change"
    why_human: "Visual and interaction behaviour. All Playwright browser tests were SKIPPED in this verification environment (Chromium not installed: 566 skips), so the selector, change handler and responsive layout were not exercised here"
  - test: "Run the browser suite in CI (a missing browser fails CI) or locally with `playwright install --only-shell chromium`, especially companion/test_browser_device_selector.py"
    expected: "Green"
    why_human: "Cannot launch a browser here"
  - test: "Owner decision: ship nothing to production until Phase 47 is finished and the owner gives the go-ahead; test with a real second frame when one exists"
    expected: "Owner-side decision, not a code check"
    why_human: "Decision and hardware"
---

# Phase 51: Per-Device Config, Image and State, Verification Report

**Phase goal:** Each device has its own config, image, poll state, history and health, so one frame's settings and failures never affect another.
**Verified:** 2026-10-30
**Status:** gaps_found (two medium gaps; the three roadmap criteria hold in the normal path; owner-side checks also remain)
**Re-verification:** No, initial verification

## Independent test runs

| Check | Command | Result |
|---|---|---|
| Targeted set | `pytest stub-server/test_phase47_freeze.py stub-server/test_image_negotiation.py stub-server/test_device_fleet.py companion/test_device_isolation.py companion/test_access_matrix.py` | 928 passed |
| Full suite | `pytest -n auto` | 5890 passed, 566 skipped (all skips are browser tests without Chromium, plus 2 environment skips) |
| Lint, types, gates | `ruff check .`, `mypy`, `check_function_size.py check --max 80 server stub-server` | clean, clean, 649 functions none over 80 |
| Comment-history guard | `check_comment_history.py check` | no output, exit clean |
| Frozen files | `git diff --stat 17b6564 HEAD -- stub-server/test_phase47_freeze.py hardware firmware .planning/.../47*` | empty (nothing touched) |
| Previous release vs new state | Extracted base-ref `server/` and `stub-server/` with `git archive`, loaded a post-change config (`timezone` key, `devices/` dir present) | Old `load_device_config`, `read_wake_interval_s` and `quiet_hours_sleep_s` read it fine (key ignored) |

Branch note: `origin/main` is 2 commits ahead (Phase 54 real-tenant docs and a flaky-test fix). The only conflict surface is the shared planning files (AUTH-01 lines in REQUIREMENTS.md and STATE.md); the branch's own edits there are Phase 51 lines only (ROADMAP plan list and progress row, STATE position). No code conflict.

## Success criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Two simulated devices each get their own image from their own directory; live frame's files and responses unchanged | VERIFIED (normal path) | `_device_context` resolves token to MAC to fleet.db row to `device_dirs.resolve_state_dir`; non-live image from `devices/<id>/panel.bin` at the profile's size, published under that device's own `img/`, URL `/img/<id>/<sha>.bin`; `_serve_device_image` reads only a non-live row's dir, same 404 for unknown, live id or bad path. Live keeps `/img/<sha>.bin`, root `img/`, root config. `test_device_fleet.py` and `skypane_two_device_fleet` seed two devices; freeze test and image negotiation tests unmodified and green. Image negotiation preserved: `_served_image(X-Img-Fmt, ...)` unchanged; unannounced frame gets raw (test_negotiation_unannounced_device_gets_raw_profile_size). Degraded-mode exception: see gap 1 |
| 2 | Owner can poll one device and set its quiet hours and timezone; no other device changes | VERIFIED | `_handle_poll_now(device)` runs `poll_cycle.run_once(state_dir=device.state_dir, reconcile_firmware=device.is_live)` under a per-directory lock (`poll_lock_for(realpath)`) and a per-device cooldown stored in that device's own history.db; unsupported hardware refused before touching a directory. Settings POST writes only `device.state_dir/device_config.json`; timezone validated against `zoneinfo.available_timezones()` atomically, stored only when it differs from `Europe/Paris`. `companion/test_device_poll.py`, `test_device_settings.py`, `test_device_isolation.py` assert sibling state unchanged |
| 3 | Each device shows its own history and health; no fallback to a shared default | VERIFIED (companion) / PARTIAL (BYOS degraded) | Pages render from `PageContext.state_dir` = the request's device dir; unknown or malformed `/devices/<id>` is the 404 page (`find_device` returns None, no live fallback; `routes.DEVICE_PREFIX_RE` anchored, `\Z`); never-seen and offline states derive from the device's own check-ins; `root_state_dir` is only used for fleet-wide status. BYOS fallback exists only when fleet.db is unavailable: gap 1 |

## Owner constraints D-01..D-20 (spot-verified)

| Constraint | Status | Evidence |
|---|---|---|
| Live frame byte-for-byte (MAC, secret, token, paths, raw image, wake interval) | VERIFIED | Live row `state_path "."` resolves to the root; `_live_context` uses `args.image`, root dir, WIDTH/HEIGHT; freeze test green and untouched |
| `device_config.json` byte identity for default timezone | VERIFIED | `timezone` key written only when != `Europe/Paris` (`device_config.py` lines ~383) |
| Expand-only | VERIFIED | New files only under `devices/`; extra optional key; previous release read the post-change state (run above); no schema bump from Phase 51 (v2 sessions belongs to Phase 54) |
| Path traversal | VERIFIED | `device_dirs.valid_state_path` shape first, then realpath containment under `<root>/devices`, symlinked dir refused; `add_device` accepts only "." or "auto"; device id regex `\Ad_[0-9a-f]{8}\Z`; image routes regex-anchored 64-hex digest; `_serve_image_file` joins only a validated hex digest |
| Backup coverage | VERIFIED | `deploy/backup/skypane_backup.py` walks `devices/<id>/` with an allow-list, WAL-safe history snapshot via sqlite backup API, per-device temp names, refuses symlinks; `deploy/tests/test_backup.py` covers it |
| Phase 50 negotiation preserved | VERIFIED | see criterion 1 |
| No prod deploy, no phase 47 / hardware / firmware edits | VERIFIED | empty diff against the base ref for those paths |
| Companion bilingual EN/FR | VERIFIED | `companion/i18n_fr/display.py` has the timezone label, helper and invalid message; i18n tests green in the full suite |
| Per-device routes annotatable by auth | VERIFIED | `Route.device_scoped` (27 routes), `RouteMatch.device_id`, the single hook point in `_dispatch_for_device`; inventory in `51-DEVICE-SCOPED-ROUTES.md` matches the table (completeness test) |
| Only Phase 51 lines edited in shared ROADMAP/STATE | VERIFIED | `git diff origin/main HEAD` on those files shows only the Phase 51 plan list, progress row and STATE position |

## Requirements coverage

| Requirement | Status | Evidence |
|---|---|---|
| FLT-01 (own config, image, poll state, history, health; BYOS serves own image from own directory) | SATISFIED in the normal path, with gaps 1 and 2 (medium) open | Sections above. Do not tick in REQUIREMENTS.md until the two gaps are closed or the owner accepts them |
| FLT-02 (poll one device, quiet hours and timezone, without affecting others) | SATISFIED | criterion 2. The requirement text says "owner or a user"; user-role access is Phase 54/60 work and device routes are ADMIN_ONLY today (see follow-ups) |

No orphaned Phase 51 requirements in REQUIREMENTS.md.

## Gaps

| # | Severity | Gap |
|---|---|---|
| 1 | Medium | BYOS fails open to the live frame when fleet.db is unavailable (fault or absent): a non-live device with a mirrored legacy token gets the live image, and its battery value overwrites the live `battery_state.json`. Violates "never serves the live image to another device" and "no fallback to a shared default" in the degraded mode, and the existing test cements it |
| 2 | Medium | Nothing prevents a second device row with `state_path "."` (default in `add_device` and in `fleet_cli devices add`); reproduced with two default `add_device` calls. The second frame then shares the live frame's whole state. Owner docs do not warn to pass `--state-path auto` |
| 3 | Low (info) | Browser tests were skipped here (no Chromium), so the selector and layout are unverified by this run. CI is the gate |
| 4 | Low (info) | `51-OWNER-CHECKS.md` is French while the "verifier" appendix is English; harmless. Provider-spacing across devices and per-hardware rendering are explicitly deferred (Phases 52 and 56) |
| 5 | Info | After sign-in, `next` accepts only un-prefixed routes, so an anonymous request for `/devices/<id>/display` lands on the default page (documented in 51-DEVICE-SCOPED-ROUTES.md; Phase 54 follow-up) |

Neither medium gap is a regression of the live frame. Both are cheap to fix.

## Owner-side items

- Run the 7 checks in `51-OWNER-CHECKS.md` on a dev machine (two simulated frames).
- Decide on the two medium gaps (fix now, or accept and document).
- Production go-live only after Phase 47 finishes and with explicit owner approval; no deploy, activate or provision was run.
- Test with a real second frame when one exists.
- Re-merge `origin/main` before opening the PR (planning-file conflict on AUTH-01 lines).

## Follow-ups for the Phase 54 auth work (device routes)

1. Ownership hook: `_dispatch_for_device`, after `find_device` and before `route.handler`. Give routes `Access(USER, "device")` and pass `route_match.device_id` as `captured` to `access.decide()` for a prefixed match (the captured part of a `PrefixSuffix` route is the key, not the device id).
2. `device_scope.Device` has no `owner_user_id`; use `fleet_db.get_device_owner` or add it to `load_devices` and `find_device`.
3. The device selector and device list use `load_devices` unfiltered; filter by ownership before any non-admin sees it. A non-owned id must give the same 404 as an unknown id.
4. The `next` parameter must accept `/devices/<id>/...` once ownership is enforced.
5. Matrix rows for the 27 device-scoped routes exist (`DEVICE_SCOPED` set); keep the completeness test aligned when roles open.
6. BYOS endpoints stay token-authenticated and must not be gated on a session; `/img/<id>/<sha>.bin` is content-addressed and public by design.
7. Close gap 1 before relying on fleet.db availability as a security boundary.

## What later phases can rely on

- Phase 52 (fleet poll cycle): `poll_cycle.run_once(state_dir=<device dir>, reconcile_firmware=False)` already runs one device's cycle against its own directory with its own lock; per-device `poll_state.json`, `history.db`, `battery_state.json`, `panel.bin`, `img/`; `device_dirs.resolve_state_dir` as the only path chokepoint; `device_scope.load_devices` to enumerate. Shared provider spacing is not built.
- Phase 53 (detection modes): per-device `device_config.json` is the place for per-device airport, runway or position settings (add keys expand-only, omit when default); per-device Display page and POST handler exist.
- Phase 56 (per-hardware rendering): BYOS already derives width, height and byte count from `hardware.get_profile(row["hardware_type"])`; poll-now is refused for hardware that is not 1200x1600 (`device_scope.poll_supported`), which is the switch to lift when per-hardware rendering lands; per-device `panel.bin` sized to the profile.
