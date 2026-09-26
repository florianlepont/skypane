---
phase: 42
slug: remote-firmware-update-over-the-air-ota-promoted-from-seed-0
status: planned
nyquist_compliant: true
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

| Task | Plan | Wave | Requirement | Test type | Automated command | Status |
|------|------|------|-------------|-----------|-------------------|--------|
| 42-01-T1 | 01 | 1 | G-41 | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-01-T2 | 01 | 1 | OTA-05, OTA-10 | pytest unit (TDD) | `pytest -q server/test_firmware_registry.py` | pending |
| 42-01-T3 | 01 | 1 | OTA-01, OTA-06 | pytest unit (TDD) | `pytest -q server/test_firmware_registry.py (+ --cov >= 95%)` | pending |
| 42-02-T1 | 02 | 1 | G-41 | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-02-T2 | 02 | 1 | OTA-02 | firmware host test (TDD) | `sh firmware/tests/run_host_tests.sh (test_validate)` | pending |
| 42-02-T3 | 02 | 1 | OTA-03, OTA-05, OTA-06 | firmware host test (TDD) | `sh firmware/tests/run_host_tests.sh (test_ota_policy)` | pending |
| 42-03-T1 | 03 | 1 | G-41 | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-03-T2 | 03 | 1 | OTA-03, OTA-04 | config check + container resolve | `sh firmware/tests/check_production_config.sh static (+ mutation proof)` | pending |
| 42-03-T3 | 03 | 1 | OTA-04, OTA-10 | script check | `SKYPANE_RELEASE_TAG=fw-vbad sh firmware/build.sh exits 2; SIGNING.md greps` | pending |
| 42-04-T1 | 04 | 1 | G-41 | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-04-T2 | 04 | 1 | OTA-07 | pytest unit + generator drift | `pytest -q server/test_updating_screen.py server/test_updating_screen_mask.py server/test_fault_screen_mask.py` | pending |
| 42-04-T3 | 04 | 1 | OTA-07 | firmware host test (TDD, golden digest) | `sh firmware/tests/run_host_tests.sh (test_fault_screen, test_updating_screen)` | pending |
| 42-05-T1 | 05 | 1 | G-41 | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-05-T2 | 05 | 1 | OTA-11 | pytest with generated fixture chains (offline) | `pytest -q deploy/tests/test_cert_chain_check.py` | pending |
| 42-05-T3 | 05 | 1 | OTA-11 | workflow grep + secrets test | `grep triggers; pytest -q deploy/tests/test_ci_secrets.py` | pending |
| 42-06-T1 | 06 | 1 | G-41 + credentials decision | gate | G-41 gate command (git checks on origin/main) | pending |
| 42-06-T2 | 06 | 1 | OTA-10 (enabling) | firmware host test (TDD) + build | `sh firmware/tests/run_host_tests.sh (test_creds); no secrets.h references` | pending |
| 42-06-T3 | 06 | 1 | OTA-10 (enabling) | script dry-run | `provision.sh --dry-run redaction and http refusal` | pending |
| 42-07-T1 | 07 | 2 | OTA-01, OTA-06, OTA-08 | pytest integration (real byos on loopback) | `pytest -q stub-server/test_ota_offer.py stub-server/test_poll_cycle.py` | pending |
| 42-07-T2 | 07 | 2 | OTA-01 | pytest integration | `pytest -q stub-server/test_ota_offer.py` | pending |
| 42-08-T1 | 08 | 2 | OTA-02, OTA-06 | host tests + grep | `sh firmware/tests/run_host_tests.sh; X-Ota-Result greps` | pending |
| 42-08-T2 | 08 | 2 | OTA-02, OTA-03, OTA-05 | container build + log contract + built config | `bash firmware/build.sh && check_production_config.sh built` | pending |
| 42-09-T1 | 09 | 2 | OTA-08 | pytest served HTML | `pytest -q companion/test_update_page.py` | pending |
| 42-09-T2 | 09 | 2 | OTA-08 | pytest served HTML EN/FR | `pytest -q companion/test_update_page.py companion/test_i18n.py` | pending |
| 42-10-T1 | 10 | 2 | OTA-09 | pytest unit | `pytest -q server/test_notify.py` | pending |
| 42-10-T2 | 10 | 2 | OTA-06, OTA-09 | pytest cycle-level | `pytest -q server/test_firmware_reconcile.py server/test_poll_loop.py` | pending |
| 42-11-T1 | 11 | 2 | OTA-10 | pytest with throwaway git repo | `pytest -q deploy/tests/test_release_manifest.py` | pending |
| 42-11-T2 | 11 | 2 | OTA-04, OTA-10 | secrets test (all workflows, mutation-proven) + greps | `pytest -q deploy/tests/test_ci_secrets.py` | pending |
| 42-12-T1 | 12 | 2 | OTA-04 | human-action checkpoint | developer confirms key stored, backup made (no key material to Claude) | pending |
| 42-12-T2 | 12 | 2 | OTA-04 | openssl check | `openssl pkey -pubin ... 3072 bit; no PRIVATE KEY block under firmware/` | pending |
| 42-13-T1 | 13 | 3 | OTA-06 | firmware host test (TDD) | `sh firmware/tests/run_host_tests.sh (test_wake_deadline)` | pending |
| 42-13-T2 | 13 | 3 | OTA-02, OTA-03, OTA-06, OTA-07 | build + source-order gates | `bash firmware/build.sh; awk confirm-before-sleep and OTA-before-hash-skip gates` | pending |
| 42-13-T3 | 13 | 3 | OTA-02 | log contract check | `sh firmware/tests/check_log_contract.sh` | pending |
| 42-14-T1 | 14 | 3 | OTA-08 | pytest plain requests (no JS) | `pytest -q companion/test_update_actions.py companion/test_post_origin.py` | pending |
| 42-14-T2 | 14 | 3 | OTA-08 | pytest-playwright (JS, no-JS, 375/390 px EN/FR) | `SKYPANE_REQUIRE_BROWSER=1 pytest -q companion/test_browser_update.py` | pending |
| 42-15-T1 | 15 | 3 | OTA-10 | pytest unit | `pytest -q server/test_firmware_cli.py` | pending |
| 42-15-T2 | 15 | 3 | OTA-10 | fake-root deploy tests + shellcheck | `pytest -q deploy/tests/test_deploy.py deploy/tests/test_activate.py` | pending |
| 42-15-T3 | 15 | 3 | OTA-10 | deploy suite | `pytest -q deploy/tests` | pending |
| 42-16-T1 | 16 | 4 | OTA-12 | grep of session sheet | `grep H42 rows in hardware/BRINGUP-LOG.md` | pending |
| 42-16-T2 | 16 | 4 | OTA-02, OTA-03, OTA-04, OTA-07, OTA-10, OTA-11, OTA-12 | human-action hardware session | H42-01..H42-12 on the real frame | pending |
| 42-16-T3 | 16 | 4 | OTA-12 | evidence + secret scan | `grep H42-12; efuse-after exists; no bearer token in captures` | pending |

Python commands run as `server/.venv/bin/python -m pytest ...`. Every non-checkpoint task has an automated command; the two human checkpoints (42-12-T1, 42-16-T2) are bracketed by automated tasks, so no three consecutive tasks lack automated feedback.

Requirement to proof mapping (fixed in `42-RESEARCH.md` "Validation Architecture"):

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

Created test-first inside the plans (no separate Wave 0 plan; each TDD task writes its tests before the code):
- [ ] `stub-server/test_ota_offer.py` — OTA-01 (plan 07)
- [ ] `firmware/tests/test_ota_policy.c` (named after `ota_policy.c` for run_host_tests.sh discovery) and the `test_validate.c` extension — OTA-02, OTA-05 (device), OTA-06 (device) (plan 02)
- [ ] `server/test_firmware_registry.py` — OTA-01 (offer gate incl. battery), OTA-05 (server), OTA-06 (server), OTA-10 (registry) (plan 01)
- [ ] `companion/test_update_page.py`, `companion/test_update_actions.py`, `companion/test_browser_update.py` — OTA-08 (plans 09, 14)
- [ ] `deploy/tests/test_cert_chain_check.py` with generated fixture chains — OTA-11 (plan 05)
- [ ] `server/test_notify.py` extension and `server/test_firmware_reconcile.py` — OTA-09, OTA-06 (plan 10)
- [ ] `firmware/tests/test_updating_screen.c`, `server/test_updating_screen.py`, `server/test_updating_screen_mask.py` — OTA-07 (plan 04)
- [ ] `deploy/tests/test_release_manifest.py`, `server/test_firmware_cli.py` — OTA-10 (plans 11, 15)
- [ ] `firmware/tests/test_creds.c` — credentials out of the image (plan 06)

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies (human checkpoints excepted, see map)
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [ ] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
