---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
verified: 2026-10-31T00:00:00Z
status: human_needed
score: 3/3 roadmap success criteria verified in code (D-01..D-21 cross-checked); real-panel and in-browser items pending
overrides_applied: 0
human_verification:
  - test: "Power a real provisioned, registered-but-unclaimed frame and read the pairing screen"
    expected: "XXXX-XXXX code is legible at normal viewing distance, bilingual text readable, red header band (160,32,32) looks acceptable on the Spectra 6 panel; frame redraws only on code rotation"
    why_human: "Physical panel; the image is only verified as bytes in tests"
  - test: "Dry run on a spare frame: register, pair, retire, re-activate, pair again"
    expected: "Retired frame shows the retired screen and sleeps 24 h; re-activation shows a fresh code; claimed frame is owned by the chosen user"
    why_human: "Needs real firmware, Wi-Fi and the production-like byos"
  - test: "Run companion browser suites where Chromium is installed (CI)"
    expected: "test_browser_console.py, test_browser_fleet_page.py, test_browser_audit_page.py pass (360 px layout, 44 px targets, both themes, French, scripts blocked)"
    why_human: "Chromium is absent in this verification sandbox: 25 browser tests were SKIPPED locally (they fail, not skip, in CI per project policy). The HTTP-level equivalents ran and passed."
  - test: "Deploy dry-run on the VPS (activate.sh prints 'upgrade fleet.db schema 2 -> 3') and restore of a schema 3 backup"
    expected: "Migration applies, Health shows no fleet fault"
    why_human: "No production deploy is allowed in this phase (D-02)"
---

# Phase 55: Frame Pairing, Admin Console and Reduced User View - Verification

**Goal:** Admins can add frames to users and manage the whole fleet; ordinary users manage only their own frames with a simpler view.
**Verified at:** HEAD 68796be6 (branch milestone/v1.2-phase-55-pairing-admin, origin/main merged)
**Re-verification:** No, initial verification.

## Roadmap success criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Admin pairs a frame with a short on-panel code: single-use, expiring, atomic claim, audited | VERIFIED | `server/pairing_code.py` (30-symbol alphabet, 8 chars, `secrets.choice`, salted SHA-256, `hmac.compare_digest` over all rows, no early exit); `server/fleet_ops.py::claim_pairing_code` runs match, owner check, DELETE pending, `add_device`, dir provisioning and `audit_append` in one `fleet_db.transaction` (BEGIN IMMEDIATE); `stub-server/byos_server.py::_pending_panel/_issue_pairing_code` renders the code onto the panel and stores only a hash; `companion/console_pairing.py::handle_pair` is wired to a Route (ADMIN_ONLY, csrf=True). |
| 2 | Console shows every device with owner, hardware, last seen, battery, firmware; manages users, reassign/retire, releases | VERIFIED | `companion/pages/fleet_page.py` (columns Last seen / Battery / Firmware, live + pending + retired rows); `console_lifecycle.py` (reassign, retire, reactivate, all ADMIN_ONLY, csrf); `console_users.py` (invite, role, disable/enable, unlink, last-admin and self guards in `fleet_db`); `/update` page ADMIN_ONLY; audit and locations pages exist. |
| 3 | Ordinary user sees only own frames, fewer options, no fleet/release controls | VERIFIED | `device_scope.load_devices_for` filters by owner for USER; `/device` (wake/LED) and `/update*` routes and LED/wake POSTs are ADMIN_ONLY; page routes are OWNER_DEVICE; `companion/test_user_view_http.py` proves 404 byte-identical to unknown path and that a crafted settings POST cannot change admin-only keys. |

## Owner decisions D-01..D-21 cross-checked against code

| D | Result | Evidence |
|---|--------|----------|
| D-01/D-03 | OK | No diff vs merge-base 029cfe39 in `firmware/`, `hardware/`, `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`. Frame still reads the same six display keys (`_pending_response`). |
| D-02 | OK | No secrets or real codes found; tests use fake Auth0 and the socket guard. No deploy performed. |
| D-04 | OK | Matrix covers anonymous/user/admin only. |
| D-05 | OK | `companion/access.py` has no Phase 55 semantic change to `authorized_device_id` (handoff claim "no diff" confirmed against it being listed in changed files only for the matrix: the gate is in `app.py::_effective_access`). |
| D-06 | OK | `pending_devices` table in `_migrate_v3`; `devices` row created only on claim; BYOS registry/tokens read pending (`pending_registry_view`, `pending_tokens_by_mac`, `_pending_context`). |
| D-07 | OK | `register_frame` accepts only a 64-hex SHA-256 (`_SHA256_RE`); console form field is the hash; hash never echoed on error; CLI `register-pending` exists. |
| D-08 | OK | Pending display returns a rendered panel, `_served_image` negotiates format, `PENDING_SLEEP_S = 300`; live frame takes a different context path. |
| D-09 | OK | `ALPHABET` has 30 symbols, none of 0 1 I L O U (checked by script); `XXXX-XXXX` via `format_code`; case-insensitive normalisation with O/I/L folding. |
| D-10 | OK | `CODE_TTL_S = 1800`, `PENDING_SLEEP_S = 300`; a live unexpired code is never re-issued, a new one is issued at the next wake after expiry. |
| D-11 | OK | Atomic claim as above; `ClaimRefused("pairing code not accepted")` is raised for malformed (dummy-code scan), wrong, expired and already-claimed alike. Race covered by `server/test_fleet_ops.py` two-thread test (passed). |
| D-12 | OK | `handle_pair` checks `SESSION_THROTTLE` and `GLOBAL_THROTTLE` before touching the DB, advances both on refusal; `record_claim_failure` stores only a reason enum, never the guess. |
| D-13 | OK | `reassign_frame` wipes and re-provisions inside the transaction for non-live frames (config, history, gallery, location, name), keeps MAC/secret/token; live frame (`state_path "."`) changes owner only. |
| D-14 | OK | `retire_frame` refuses the live frame (audited `denied`), `park_retired` keeps the token and previous owner/state path, retired screen at `RETIRED_SLEEP_S = 86400`; `reactivate_frame` wipes the previous directory and returns to pending; hard delete is CLI-only. |
| D-15 | OK | Fleet, Users, Audit, Releases, Locations pages and routes exist; last-admin and self-disable guards in `fleet_db`. |
| D-16/D-17 | OK | See criterion 3; reduced Health covered by `test_health_fleet_status.py` (passed). |
| D-18 | OK | `locations.owner_user_id` added NULL-able; `USER_LOCATION_LIMIT = 10` enforced in `console_locations.py`. |
| D-19 | OK | `audit_log` with BEFORE UPDATE and BEFORE DELETE triggers raising ABORT; no FK on actor; `audit_append` has no code/secret parameter; read-only audit page. |
| D-20 | OK | `CSRF_ROUTE_KEYS` is exactly six existing routes (rule delete, calendar disconnect, manual delete, rename reset, update install, update cancel); every new admin/pairing/location POST sets `csrf=True`; token is `sha256("csrf-v1:" + session)` so no schema change; `test_csrf.py` passed. |
| D-21 | OK | One migration `_migrate_v3` (ALTER ADD COLUMN nullable plus two CREATE TABLE); `SCHEMA_VERSION = 3`; backup test covers the new tables and triggers (`deploy/tests/test_backup.py` passed). Rollback caveat documented in 55-HANDOFF.md section D.2 and deploy README. |

## Requirements coverage

| Requirement | Plans | Status | Evidence |
|-------------|-------|--------|----------|
| AUTH-04 | 55-02..07, 10, 14 (frontmatter) | SATISFIED in code | Criterion 1. |
| AUTH-05 | 55-01, 08..14 (frontmatter) | SATISFIED in code | Criteria 2 and 3. |

Both IDs appear in REQUIREMENTS.md (lines 50-51, traceability table 117-118, currently "Pending", an orchestrator-owned status update). No ORPHANED requirements: REQUIREMENTS.md maps only AUTH-04 and AUTH-05 to Phase 55.

## Behavioural spot-checks

| Check | Command | Result |
|-------|---------|--------|
| Phase 55 core, pairing, byos, freeze, CSRF, matrix, user view, console pages (15 files) | `pytest ... -n 4 --no-cov` | 1342 passed |
| Backup, browser console, browser fleet, health fleet status | `pytest ...` | 43 passed, 25 skipped (Chromium not installed) |
| Alphabet property | python one-liner | length 30, no 0/1/I/L/O/U |
| Phase 47 freeze files and `firmware/`, `hardware/` unmodified | `git diff --stat 029cfe39 HEAD -- ...` | empty |
| Debt markers (TBD/FIXME/XXX) in phase source files | grep | none |

The orchestrator reports the full suite at 7656 passed at HEAD; not re-run here.

## 55-HANDOFF.md claims vs reality

- Delivered-items list, test names and file names checked: all exist and the cited server, stub-server and companion tests pass.
- "`companion/access.py` has no diff": not independently re-diffed beyond the matrix of changed files; the ownership gate lives in `app.py::_effective_access` as stated.
- D.17 "branch has not been rebased onto origin/main" is stale: HEAD now includes the main merge (68796be6, merge-base 029cfe39). Cosmetic, no action beyond updating the sentence.
- Section C states nothing was deployed or done by the owner; consistent with the repository.

## Anti-patterns

None blocking. Minor, already disclosed in the hand-off: reuse of a slightly inaccurate calendar-field error string (D.15); in-memory throttles reset on restart (D.4).

## Gaps

None at code level. Status is `human_needed` solely for the items in the frontmatter: real-panel pairing screen and red band, spare-frame lifecycle dry run, browser suites that could not run in this sandbox, and the production deploy and backup-restore dry run.

_Verifier: Claude (gsd-verifier)_
