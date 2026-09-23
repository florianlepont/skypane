---
phase: 37
slug: security-and-operations-hardening
status: planned
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-23
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `37-RESEARCH.md` § Validation Architecture. The per-task map is
> finalised by the planner (task IDs) and the plan checker.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (+ xdist, cov) as delivered by Phase 32 (TST-01); Playwright for browser checks |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` (Phase 32; re-read at execution) |
| **Quick run command** | `server/.venv/bin/python -m pytest -x -q <test files touched>` |
| **Full suite command** | `./scripts/run-all-tests.sh` (pytest wrapper after Phase 32/33) |
| **Extra CI gates** | `shellcheck deploy/*.sh deploy/backup/**/*.sh`; `systemd-analyze security --offline=true --threshold=20 deploy/<unit>` per unit |
| **Estimated runtime** | quick < 30 s; full suite per Phase 32 baseline |

---

## Sampling Rate

- **After every task commit:** quick run command on the files touched + `ruff check .`
- **After every plan wave:** full suite + shellcheck + offline systemd-analyze
- **Before `/gsd:verify-work`:** full suite green; every VPS/GitHub/Mac checkpoint (CP-1..CP-11 in RESEARCH.md) signed off
- **Max feedback latency:** 30 seconds (quick command)

---

## Requirement → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEC-01 | IP A locked does not lock IP B; the table is capped; XFF is trusted only from loopback, right-most entry | unit + integration | `pytest -q -k "throttle or client_ip"` (e.g. `companion/test_login_throttle.py`) | ❌ Wave 0 |
| SEC-01 | Legacy throttle checks ported to the keyed API | unit | same file | ❌ (rewrite `test_companion_app.py:1720-1786` checks) |
| SEC-02 | Both rendered site blocks carry HSTS | unit | `pytest -q deploy/tests/test_caddyfile.py` | ❌ Wave 0 |
| SEC-02 | Header live on both hosts | manual/probe | activate.sh probe + `curl -sI https://<host>/ \| grep -i strict-transport` | VPS checkpoint |
| SEC-03 | Cross-origin / `same-site` / `null` Origin POST → 403 on every route incl. login; same-origin and header-less → unchanged | integration | `pytest -q companion/test_post_origin.py` | ❌ Wave 0 |
| SEC-03 | Real browser cross-origin form post rejected; same-origin UI still works | browser | `pytest -q -k origin companion/test_browser_*` | ❌ Wave 0 |
| SEC-04 | Snapshot has a consistent db (integrity ok) under a concurrent writer; include list honoured; retention 14; files 0640 | unit (tmp dirs) | `pytest -q deploy/tests/test_backup.py` | ❌ Wave 0 |
| SEC-04 | Gate: only `list`/`get`/`ack`; rejects path traversal, bad names, extra args; ack writes the marker | unit (subprocess, env `SSH_ORIGINAL_COMMAND`) | `pytest -q deploy/tests/test_backup_gate.py` | ❌ Wave 0 |
| SEC-04 | Mac script: pulls missing archives, verifies sha, retention, acks newest (fake `ssh` on PATH → gate) | integration | `pytest -q deploy/tests/test_mac_pull.py` + `shellcheck --shell=sh` | ❌ Wave 0 |
| SEC-04 | Health line: never → alert; > 3 days → alert; fresh → ok; unset env → hidden; FR string | unit (render) | `pytest -q -k offbox` | ❌ Wave 0 |
| SEC-04 | Restore rehearsal | manual-only | Mac checkpoint | — |
| SEC-05 | Happy path swaps `current`, installs units, daemon-reload, probes; failure (inactive unit / bad HTTP code) swaps back and exits ≠ 0; no-previous case; prune keeps 5 and never current/prev | integration (fake root + stubs) | `pytest -q deploy/tests/test_activate.py` | ❌ Wave 0 |
| SEC-05 | Caddyfile render: anchored substitution, rejects bad hostnames, never sources the env | unit | `pytest -q deploy/tests/test_caddyfile.py` | ❌ Wave 0 |
| SEC-05 | Real cutover + a deliberately failing deploy | manual-only | VPS checkpoint | — |
| SEC-06 | Units carry the directive set; offline score ≤ 2.0 | unit + CI | `pytest -q deploy/tests/test_units.py`; `systemd-analyze security --offline=true --threshold=20 deploy/<unit>` | ❌ Wave 0 |
| SEC-06 | Online before/after scores; services work under the sandbox | manual-only | VPS checkpoint | — |
| SEC-06/07 (Wave B) | byos `--bind 127.0.0.1` bound to loopback only; no shared secret (retired by Phase 34 FW-08), none in argv or env; no `--secret` in the unit | integration | `pytest -q stub-server/test_byos_bind_secret.py` | ❌ Wave B |
| SEC-07 | No `${{ secrets.* }}` inside any `run:` of ci.yml | unit (YAML text parse) | `pytest -q deploy/tests/test_ci_secrets.py` | ❌ Wave 0 |
| SEC-07 | Env file `root:root 600`; `pgrep -af byos_server` shows no secret | manual-only | VPS checkpoint | — |
| SEC-08 | Drop-in content; provision step validates with `sshd -t` before reload (stub `sshd`) | unit | `pytest -q deploy/tests/test_provision_ssh.py` | ❌ Wave 0 |
| SEC-08 | Live values and second-session login | manual-only | VPS checkpoint | — |

*Status of each row is tracked per task in the plans' `<verify>` blocks.*

---

## Wave 0 Requirements

- [ ] Phase 32 merged (pytest, `conftest.py`, socket guard allowing loopback, companion server fixture from Phase 33 if available; otherwise a local fixture spawning `companion/app.py` on a free port)
- [ ] `deploy/tests/conftest.py` (or Phase 32's equivalent): a fake-root fixture and PATH stubs for `systemctl`, `curl`, `caddy`, `runuser`, `journalctl`, `sshd`, `ssh`
- [ ] pytest `testpaths` includes `deploy/`
- [ ] CI steps for shellcheck and `systemd-analyze security --offline=true --threshold=20` (add to the `test` job without touching concurrency, D-13)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HSTS header live on both hosts | SEC-02 | needs production TLS | RESEARCH.md CP-4 |
| Restore from an off-box copy | SEC-04 | runs on the developer's Mac against real data | RESEARCH.md CP-10 |
| launchd pull + freshness line fresh | SEC-04 | Mac + VPS | RESEARCH.md CP-8, CP-9 |
| Cutover and deliberately failing deploy | SEC-05 | production VPS | RESEARCH.md CP-4, CP-5 |
| Online `systemd-analyze security` before/after; services run under sandbox | SEC-06 | production VPS | RESEARCH.md CP-1, CP-6 |
| Env file `root:root 600`; no secret in `ps` | SEC-07 | production VPS | RESEARCH.md CP-3, CP-11 |
| `sshd -T` values; second-session login; root refused | SEC-08 | production VPS | RESEARCH.md CP-3 |
| byos loopback only, frame still fetches | SEC-06/07 Wave B | production VPS + device | RESEARCH.md CP-11 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
