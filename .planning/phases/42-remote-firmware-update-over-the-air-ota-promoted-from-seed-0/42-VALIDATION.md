---
phase: 42
slug: remote-firmware-update-over-the-air-ota-promoted-from-seed-0
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-09-25
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-xdist + pytest-cov, pytest-socket (loopback only), pytest-playwright (companion browser tests); firmware C host tests (`firmware/tests/run_host_tests.sh`, no ESP-IDF) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`), `conftest.py`; `firmware/tests/run_host_tests.sh` (naming-convention discovery) |
| **Quick run command** | `server/.venv/bin/python -m pytest -q <plan test files> && server/.venv/bin/ruff check . && server/.venv/bin/python scripts/check_comment_history.py check`; firmware plans: `bash firmware/tests/run_host_tests.sh` |
| **Full suite command** | `./scripts/run-all-tests.sh` and `bash firmware/tests/run_host_tests.sh && bash firmware/build.sh` |
| **Estimated runtime** | quick ~5–30 s per plan; full Python ~2–4 min; firmware build ~2–5 min in the IDF container |

---

## Sampling Rate

- **After every task commit:** the plan's quick command
- **After every plan wave:** both full suite commands
- **Before `/gsd:verify-work`:** both full suites green, coverage gate unchanged or higher
- **Max feedback latency:** 30 s for the quick command

---

## Per-Task Verification Map

Filled in by the planner (one row per task) once plans exist. The requirement → proof mapping is fixed in `42-RESEARCH.md` "Validation Architecture":

| Requirement | Proof | Type |
|-------------|-------|------|
| OTA-01 | offer composition (pure function) + byos `/device/v1/display` response shape | pytest unit + integration |
| OTA-02 | offer-field validation and size/hash check helper | firmware host test (extends `validate.c` pattern) |
| OTA-03 | "confirm or not" decision logic; real rollback | firmware host test (logic) + hardware session |
| OTA-04 | unsigned / tampered image refused | hardware session only (bootloader-level, no host seam) |
| OTA-05 | floor enforced by server registry and by compiled-in device floor | pytest unit + firmware host test |
| OTA-06 | battery self-refusal, three-attempt counter | firmware host test + pytest unit |
| OTA-07 | "Updating…" screen renders in every mode | firmware host test (+ mask cross-check if a generated mask is used) |
| OTA-08 | Update page states, confirm with and without JS, cancel window, history | pytest (plain requests, no-JS) + pytest-playwright |
| OTA-09 | EN/FR success and failure bodies | pytest unit on `server/notify.py` |
| OTA-10 | release-notes generation and registry write; real tagged release | shell/pytest with fixtures + one real tag |
| OTA-11 | chain check logic against known-good/known-bad fixture chains; real workflow | shell test with fixture certs + workflow run |
| OTA-12 | install, refusal, rollback on forced crash, factory recovery | hardware session, `hardware/BRINGUP-LOG.md` |

---

## Wave 0 Requirements

- [ ] `stub-server/test_ota_offer.py` (or the server-side module the planner picks) — OTA-01
- [ ] `firmware/tests/test_ota_verify.c` — OTA-02, OTA-05 (device), OTA-06 (device)
- [ ] `server/test_firmware_registry.py` — OTA-05 (server), OTA-10 (registry)
- [ ] battery-gate test — OTA-06 (server)
- [ ] `companion/test_update_page.py` — OTA-08
- [ ] fixture certificates + chain-check test — OTA-11
- [ ] extension of the existing notify tests — OTA-09

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Signed update installs on the real frame | OTA-12, OTA-02 | needs real bootloader, flash and Wi-Fi | tag a release, deploy, Install from the companion, watch the next wake |
| Unsigned / tampered image refused | OTA-04, OTA-12 | signature check lives in the bootloader/app image verifier | serve a flipped-byte and an unsigned image, confirm refusal and failure count |
| Forced crash on a trial image rolls back | OTA-03, OTA-12 | rollback is bootloader state | install a test build that aborts before its first successful poll |
| Recovery from `factory` | OTA-12 | needs invalid OTA slots on real flash | erase `otadata` / invalidate both slots, confirm `factory` boots and polls |
| Real tag → signed build → deploy copy | OTA-10 | needs GitHub Actions secrets and the real tag trigger | push a real tag, approve the deploy, check the firmware store on the VPS |
| Chain guard against the production host | OTA-11 | reaches the network | run the workflow once |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
