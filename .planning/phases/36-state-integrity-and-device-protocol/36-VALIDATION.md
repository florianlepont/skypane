---
phase: 36
slug: state-integrity-and-device-protocol
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-09-25
---

# Phase 36 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + pytest-xdist + pytest-cov, pytest-socket (loopback only) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`), `conftest.py` (network/DNS guard, `fake_providers`) |
| **Quick run command** | `server/.venv/bin/python -m pytest -q <plan test files> && server/.venv/bin/ruff check . && server/.venv/bin/python scripts/check_comment_history.py check` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | quick ~5–20 s per plan; full ~2–4 min |

---

## Sampling Rate

- **After every task commit:** the plan's quick command
- **After every plan wave:** `./scripts/run-all-tests.sh`
- **Before `/gsd:verify-work`:** full suite green, coverage gate unchanged or higher
- **Max feedback latency:** 30 s for the quick command

---

## Per-Task Verification Map

Filled in by the planner (one row per task) once plans exist. Requirement → proof mapping is fixed in `36-RESEARCH.md` "Validation Architecture":

| Requirement | Proof (behaviour) | Test type |
|-------------|-------------------|-----------|
| INT-01 | 2 OS processes × 200 locked saves → counter 400, zero exceptions; `/poll-now` with lock held elsewhere → "already running" | integration (multi-process) |
| INT-02 | concurrent writers via `atomic_write` → no exception, complete content, no leftover `*.tmp`, mode preserved; failure leaves old file | unit + multi-process |
| INT-03 | concurrent `save_device_config` threads → no lost field | unit (threads) |
| INT-04 | concurrent cold preview → one file; stale signatures pruned; bounded dir and `lru_cache` | unit |
| INT-05 | byos: `/img/X.bin` after panel swap returns X bytes; unknown/malformed → 404; `img/` ≤ N | integration (byos subprocess) |
| INT-06 | byos: bad/oversized `Content-Length` → 4xx; stalled client dropped after timeout; bad log entries → no 500 | integration (byos subprocess) |
| INT-07 | trickling fake transport stops at the deadline; poll unit has `TimeoutStartSec=90s` | unit + `deploy/tests/test_units.py` |
| INT-08 | 429/5xx/timeout never cached; TTLs honoured with injected clock; LRU order | unit |
| INT-09 | partial last line re-read once complete; bad offset / bad `ts` never raise | unit |
| INT-10 | non-dict / non-list provider bodies and records → cycle completes | unit |
| INT-11 | `main()` failure prints a full traceback, exit 1 | unit |
| INT-12 | `last_synced_at` == injected `now`; save completes during a blocked fetch; changed URL not overwritten | unit (threads) |
| INT-13 | queued detection updates `last_detection` | unit |
| INT-14 | connection goes to the checked address; TLS `server_hostname` is the hostname; private answer refuses | unit (captured socket/ssl calls) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Per-task map (plans 36-01..36-07)

| Task | Plan | Wave | Requirement | Automated command | Status |
|------|------|------|-------------|-------------------|--------|
| 36-01-T1 | 01 | 1 | G-35 gate | gate script in the task (`git ls-tree` / `git show origin/main` / `merge-base`) | ⬜ |
| 36-01-T2 | 01 | 1 | INT-02 | `pytest -q server/test_atomic_io.py -k write` | ⬜ |
| 36-01-T3 | 01 | 1 | INT-01 (lock primitive) | `pytest -q server/test_atomic_io.py` x5 | ⬜ |
| 36-02-T1 | 02 | 1 | G-35 gate | gate script in the task | ⬜ |
| 36-02-T2 | 02 | 1 | INT-07 | `pytest -q server/test_http_fetch.py deploy/tests/test_units.py test-support/test_test_support.py` | ⬜ |
| 36-02-T3 | 02 | 1 | INT-14 | `pytest -q server/test_http_fetch.py` | ⬜ |
| 36-03-T1 | 03 | 2 | INT-02 (byos copy) | `pytest -q stub-server/test_byos_hardening.py stub-server/test_devices_registry.py` | ⬜ |
| 36-03-T2 | 03 | 2 | INT-05 | `pytest -q stub-server/` | ⬜ |
| 36-03-T3 | 03 | 2 | INT-06 | `pytest -q stub-server/` | ⬜ |
| 36-04-T1 | 04 | 2 | INT-03, INT-02 | `pytest -q server/test_state_writers.py server/test_colour_rules.py server/test_manual_resolutions.py` | ⬜ |
| 36-04-T2 | 04 | 2 | INT-04 | `pytest -q companion/test_preview_cache.py companion/test_suite_guards.py` | ⬜ |
| 36-04-T3 | 04 | 2 | INT-02 (backup gate) | `pytest -q deploy/tests/test_backup_gate.py` | ⬜ |
| 36-05-T1 | 05 | 2 | INT-14, INT-07, INT-02 | `pytest -q server/test_calendar_rules.py` | ⬜ |
| 36-05-T2 | 05 | 2 | INT-12 | `pytest -q server/test_calendar_rules.py companion/test_companion_app_05.py -k "calendar or refresh"` | ⬜ |
| 36-05-T3 | 05 | 2 | INT-14, INT-07 | `pytest -q server/test_notify.py server/test_calendar_rules.py` | ⬜ |
| 36-06-T1 | 06 | 2 | INT-10, INT-07 | `pytest -q server/test_plane_detection.py server/test_poll_loop.py` | ⬜ |
| 36-06-T2 | 06 | 2 | INT-08, INT-07 | `pytest -q server/test_enrich.py server/test_render.py server/test_pipeline_e2e.py server/test_poll_loop.py` | ⬜ |
| 36-06-T3 | 06 | 2 | INT-09 | `pytest -q server/test_caddy_tail.py server/test_config_history.py` | ⬜ |
| 36-07-T1 | 07 | 3 | INT-01 | `pytest -q server/test_poll_lock.py server/test_poll_loop.py companion/test_poll_now_lock.py companion/test_companion_app_05.py` | ⬜ |
| 36-07-T2 | 07 | 3 | INT-02, INT-11, INT-13, INT-08 wiring | `pytest -q server/test_poll_loop.py server/test_poll_lock.py` + companion `-k "upload or illustration or poll"` + phase-wide fixed-name `git grep` | ⬜ |

Every task also runs `server/.venv/bin/ruff check .` and `server/.venv/bin/python scripts/check_comment_history.py check`; the last task of each plan runs `./scripts/run-all-tests.sh`.


---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements (pytest, fixtures, byos subprocess harness, companion app-server fixture, `deploy/tests/test_units.py`). New test files are created by the plans that need them.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Production poll unit honours the start timeout | INT-07 | needs systemd on the VPS | after deploy: `systemctl show skypane-poll.service -p TimeoutStartUSec` shows 1min 30s |
| Device still refreshes after a panel change mid-wake | INT-05 | needs the real frame | optional: trigger `/poll-now` twice in quick succession during a wake; frame shows the image it was told about, no `verify` failure in the frame log |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [ ] Feedback latency < 30 s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
