---
phase: 38
slug: efficiency-companion-poll-cycle-storage
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-26
---

# Phase 38 — Validation Strategy

> This is the phase's validation contract for sampling feedback during execution. The requirement-level test map is in `38-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ pytest-xdist, pytest-cov, pytest-socket, pytest-playwright), configured in `pyproject.toml` |
| **Config file** | `pyproject.toml` (coverage `fail_under` at the measured floor) |
| **Quick run command** | `server/.venv/bin/python -m pytest -n auto -q <the test files the task touched>` + `python3 scripts/check_comment_history.py check` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | ~5–30 s quick; full suite a few minutes |

---

## Sampling Rate

- **After every task commit:** run the quick command on the touched test files.
- **After every plan wave:** run `./scripts/run-all-tests.sh`.
- **Before `/gsd:verify-work`:** the full suite is green in CI (browsers required), and `38-EFF-BASELINE.md` has both the before and the after tables.
- **Max feedback latency:** 60 s.

---

## Per-Requirement Verification Map

| Requirement | Behaviour asserted | Test type | Automated command | Exists |
|-------------|--------------------|-----------|-------------------|--------|
| (instruments) | The probe counts connections, init_schema calls, commits, script tags, bytes, sleeps and `poll_state` writes | unit | `pytest test-support/test_efficiency_probe.py` | ❌ W0 |
| EFF-01 | Static responses carry ETag + Last-Modified + `Cache-Control: no-cache`; a matching `If-None-Match` or `If-Modified-Since` gets a bodiless 304; bytes are read from disk once per process | integration | `pytest companion/test_static_cache.py` | ❌ W0 |
| EFF-01 | Second page load: every static request gets a 304 | browser | `pytest companion/test_static_cache.py -m browser` | ❌ W0 |
| EFF-01 | The rendered companion block has `encode zstd gzip`; the device block does not | unit | `pytest deploy/tests/test_caddyfile.py` | ✅ extend |
| EFF-02 | The script set per route and state is exactly what that page needs; every DOM hook has its script | integration | `pytest companion/test_page_scripts.py` | ❌ W0 |
| EFF-03 | 1 connection per request and per poll cycle; schema once per process; 1 commit per cycle; no transaction open during the ntfy send | integration/unit | `pytest companion/test_request_connections.py server/test_poll_efficiency.py server/test_history_db_scope.py` | ❌ W0 |
| EFF-04 | Non-Health pages build no Health markup; severity from signals equals today's; the freshness token is stable when nothing changed and changes on each input; unchanged → 304 | unit/integration/browser | `pytest companion/test_health_signals.py companion/test_freshness_token.py` | ❌ W0 |
| EFF-05 | ≤1 `poll_state.json` write per cycle, 0 on an unchanged repeat, compact JSON | unit | `pytest server/test_poll_efficiency.py -k poll_state` | ❌ W0 |
| EFF-06 | No 1.1 s sleep between different providers; wall < L + 0.5 s with fake latency L; provider order kept; per-provider spacing kept across back-to-back cycles | unit | `pytest server/test_poll_efficiency.py server/test_plane_detection.py` | ❌ W0 / ✅ extend |

*Status is tracked per plan in each SUMMARY.*

---

## Wave 0 Requirements

- [ ] `test-support/efficiency_probe.py` + `test-support/test_efficiency_probe.py`
- [ ] `scripts/measure_efficiency.py` → the "before" tables committed to `38-EFF-BASELINE.md` **before any production change**

---

## Manual-Only Verifications

| Behavior | Requirement | Why manual | Test instructions |
|----------|-------------|------------|-------------------|
| Caddy compresses companion responses (`Content-Encoding: zstd`/`gzip`) and transferred bytes drop | EFF-01 | There is no caddy binary in CI; only the VPS runs Caddy | On the VPS after deploy: `curl -s -o /dev/null -w '%{size_download} %{content_type}\n' -H 'Accept-Encoding: zstd, gzip' -D - https://<companion host>/static/style.css`, before and after; record the numbers in `38-EFF-BASELINE.md` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
