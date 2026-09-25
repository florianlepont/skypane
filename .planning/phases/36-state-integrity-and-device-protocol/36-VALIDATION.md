---
phase: 36
slug: state-integrity-and-device-protocol
status: draft
nyquist_compliant: false
wave_0_complete: false
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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30 s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
