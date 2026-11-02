---
phase: 60
slug: device-co-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-11-01
---

# Phase 60 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Source: `## Validation Architecture` in 60-RESEARCH.md.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (+ xdist, cov), pytest-playwright 1.64.1; Python 3.13 in `server/.venv` |
| **Config file** | `pyproject.toml` (`testpaths = server, stub-server, companion, test-support, deploy, hardware`; `--strict-markers`; marker `browser`) |
| **Quick run command** | `server/.venv/bin/python3 -m pytest server/test_fleet_schema4.py companion/test_access.py companion/test_access_matrix.py companion/test_co_managers.py -x -q` |
| **Full suite command** | `./scripts/run-all-tests.sh` (CI form; coverage floor included; ruff and mypy are separate CI steps) |
| **Estimated runtime** | ~300 seconds (full suite with browser tests) |

---

## Sampling Rate

- **After every task commit:** Run the quick run command plus the single test file touched
- **After every plan wave:** Run `./scripts/run-all-tests.sh -- companion server stub-server -x` (extra args disable the coverage floor automatically)
- **Before `/gsd:verify-work`:** `./scripts/run-all-tests.sh` green, with `SKYPANE_REQUIRE_BROWSER=1` (Playwright headless shell installed via `playwright install --only-shell chromium`)
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 60-01-01 | 01 | 1 | AUTH-08 | T-60 | v4 creates table; upgrade from v1/v2/v3 keeps rows; re-run is a no-op; concurrent upgraders end at 4; PK rejects duplicates; trigger rejects owner row | unit | `pytest server/test_fleet_schema4.py -x` | ❌ W0 | ⬜ pending |
| 60-01-02 | 01 | 1 | AUTH-08 | — | Existing schema tests relative to `SCHEMA_VERSION` | unit | `pytest server/test_fleet_schema3.py server/test_fleet_db.py -x` | ✅ | ⬜ pending |
| 60-02-01 | 02 | 2 | AUTH-08 | T-60 | reassign deletes co-manager row atomically, others kept, rollback restores; retire/park/remove cascade | unit | `pytest server/test_fleet_ops.py -x` | ✅ | ⬜ pending |
| 60-02-02 | 02 | 2 | AUTH-08 | T-60 | Location rule is device-owner-relative | unit+integration | `pytest server/test_fleet_schema4.py companion/test_console_locations.py -x` | ✅ | ⬜ pending |
| 60-03-01 | 03 | 2 | AUTH-08 | T-60 | Gate allows co-manager on that frame only; owner-only kind refuses; malformed ids make no lookup | unit | `pytest companion/test_access.py -x` | ✅ | ⬜ pending |
| 60-03-02 | 03 | 2 | AUTH-08 | T-60 | Dispatcher passes membership lookup; 404 identical to unknown path | integration | `pytest companion/test_co_manager_gate.py -x` | ❌ W0 | ⬜ pending |
| 60-04-01 | 04 | 3 | AUTH-08 | T-60 | `load_devices_for` lists co-managed frames; schema-3 fails closed to owned frames | unit | `pytest companion/test_device_scope_owner.py -x` | ✅ | ⬜ pending |
| 60-04-02 | 04 | 3 | AUTH-08 | T-60 | Co-manager sees only owner's locations; location writes refused | integration | `pytest companion/test_detection_page.py -x` | ✅ | ⬜ pending |
| 60-04-03 | 04 | 3 | AUTH-08 | T-60 | Co-manager reaches OWNER_DEVICE pages; 404 for admin routes | integration | `pytest companion/test_co_manager_access.py -x` | ❌ W0 | ⬜ pending |
| 60-05-01 | 05 | 3 | AUTH-08 | T-60 | Audit labels and French strings complete | integration | `pytest companion/test_i18n.py -x` | ✅ | ⬜ pending |
| 60-05-02 | 05 | 3 | AUTH-08 | T-60 | Add/remove/leave over HTTP with CSRF, one generic refusal, audit rows | integration | `pytest companion/test_co_managers.py -x` | ❌ W0 | ⬜ pending |
| 60-06-01 | 06 | 4 | AUTH-08 | — | Card markup and CSS, English and French | integration | `pytest companion/test_co_managers_page.py -x` | ❌ W0 | ⬜ pending |
| 60-06-02 | 06 | 4 | AUTH-08 | T-60 | Card variants per role; not rendered for live frame or unreadable db | integration | `pytest companion/test_co_managers_page.py -x` | ❌ W0 | ⬜ pending |
| 60-06-03 | 06 | 4 | AUTH-08 | — | Account marks shared frames; leave toast | integration | `pytest companion/test_account_page.py companion/test_co_managers.py -x` | ✅ | ⬜ pending |
| 60-07-01 | 07 | 4 | AUTH-08 | T-60 | Matrix co-manager column and three new rows | integration | `pytest companion/test_access_matrix.py -x` | ✅ | ⬜ pending |
| 60-07-02 | 07 | 4 | AUTH-08 | T-60 | Live frame poll, legacy files and `devices` row identical with a co-manager | integration | `pytest stub-server/test_co_manager_live_frame.py stub-server/test_phase47_freeze.py -x` | ❌ W0 | ⬜ pending |
| 60-08-01 | 08 | 5 | AUTH-08 | — | No sideways scroll at 360 px, 44 px targets | browser | `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser_co_managers.py -x` | ❌ W0 | ⬜ pending |
| 60-08-02 | 08 | 5 | AUTH-08 | — | Leave flow works without scripts; freshness refresh does not clobber the card | browser | `SKYPANE_REQUIRE_BROWSER=1 pytest companion/test_browser_co_managers.py -x` | ❌ W0 | ⬜ pending |
| 60-09-01 | 09 | 6 | AUTH-08 | — | Whole gate set; backup/restore and activate dry run at schema 4 | static+integration | `./scripts/run-all-tests.sh` and `pytest deploy/tests/test_backup.py deploy/tests/test_activate.py -x` | ✅ | ⬜ pending |
| 60-09-02 | 09 | 6 | AUTH-08 | T-60 | Frozen files untouched; Phase 60 changes present | static | diff guard in plan 09 Task 2 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `server/test_fleet_schema4.py` — migration, constraints, helpers, location rule, reassign/retire/remove cascade
- [ ] `companion/test_co_managers.py` — HTTP behaviour (seeds via `fleet_console_support` plus a membership-row helper; `app_server_in_process`, `fx.user_cookie`/`fx.admin_cookie`, `fx.post`, `fx.audit_rows`)
- [ ] `companion/test_browser_co_managers.py` — follow `test_browser_fleet_page.py` (`new_context`, `_login` from `companion/test_browser_ux_helpers.py`, `VIEWPORT_MIN_SUPPORTED`)
- [ ] `test-support/matrix_rows_co_managers.py` and edits in `companion/test_access_matrix.py`
- [ ] `stub-server/test_co_manager_live_frame.py` — live frame immutability
- [ ] Edit three schema-3 assertions in `server/test_fleet_schema3.py`
- [ ] Optional `fleet_console_support.py` helper to seed a co-manager

Behaviour-over-source rule (`companion/test_suite_guards.py`): tests assert served HTML or browser state, never source text or `.planning/`; no test module imports another test module.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Adding a co-manager leaves the live Orly frame's poll and image unchanged on a real phone | AUTH-08 | Real device and phone; automated proof is `stub-server/test_co_manager_live_frame.py` | Follow 60-HANDOFF.md section E |
| French wording ("co-gestionnaire") reads right | AUTH-08 | Native-speaker judgement | Review the card in French on a phone |
| Rollback behaviour at schema 4 accepted | AUTH-08 | Owner decision | activate.sh dry run per 60-HANDOFF.md section E |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
