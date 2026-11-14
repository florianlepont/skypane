---
phase: 57
slug: combined-legacy-frame-firmware-release
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-14
---

# Phase 57 - Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Firmware framework | plain C asserts, `cc -std=c11`, `./firmware/tests/run_host_tests.sh` |
| Server framework | pytest + xdist (`./scripts/run-all-tests.sh`) |
| Firmware CI | `.github/workflows/firmware.yml` (host tests, production config, log contract, build, built-config, size, key guard) |
| Quick run | `./firmware/tests/run_host_tests.sh`; `python3 -m pytest stub-server/test_hw_claim.py stub-server/test_image_negotiation.py stub-server/test_phase47_freeze.py -q` |
| Full run | `./scripts/run-all-tests.sh` plus `firmware.yml` on the new code draft PR |
| Not runnable locally | ESP-IDF compile (no Docker daemon), possibly pytest; CI is the substitute |

## Sampling Rate

- After each task: `./firmware/tests/run_host_tests.sh` (firmware tasks) or the three stub-server files above (server tasks).
- After each wave: full `./scripts/run-all-tests.sh`.
- Phase gate: `firmware.yml` green on the draft PR (run URL recorded) and all suites green. Bench items are owner-gated and stay "not run".

## Per-Task Verification Map

| Task | Plan | Wave | Behaviour | Test type | Automated command | Status |
|------|------|------|-----------|-----------|-------------------|--------|
| 57-01-01 | 01 | 1 | Table CRC equals bitwise reference and zlib vector; framed bodies parse | host unit | `./firmware/tests/run_host_tests.sh` (test_image_container) | pending |
| 57-01-02 | 01 | 1 | Body length window, hw type grammar, announce and latch predicates (latch only for a fully received rejected body; partial, timeout and zero-byte rows are false) | host unit | `./firmware/tests/run_host_tests.sh` (test_validate) | pending |
| 57-01-03 | 01 | 1 | auth/enrol never draw; backoff grows to 6 h and resets | host unit | `./firmware/tests/run_host_tests.sh` (test_fault_screen, test_sleep_decision) | pending |
| 57-02-01 | 02 | 1 | Claim match, contradiction, absent, malformed; raw vs container; once-only resolution | server integration | `python3 -m pytest stub-server/test_hw_claim.py stub-server/test_image_negotiation.py stub-server/test_phase47_freeze.py stub-server/test_ota_offer.py -q -x` | pending |
| 57-02-02 | 02 | 1 | mypy, full stub-server regression, coverage floor | static + integration | `python3 -m mypy && python3 -m pytest stub-server -q -n auto` | pending |
| 57-03-01 | 03 | 2 | Download gate, headers, Kconfig key present | host + static | `./firmware/tests/run_host_tests.sh && bash firmware/tests/check_production_config.sh static` | pending |
| 57-03-02 | 03 | 2 | Parse before draw, latch on parse failure or complete rejected body only, buffer freed on every path, log contract, panel diff | CI guard | `bash firmware/tests/check_log_contract.sh && bash firmware/tests/check_panel_diff.sh` | pending |
| 57-03-03 | 03 | 2 | Kconfig default equals server LEGACY_KEY; size within slot | CI guard | `bash firmware/tests/check_hw_type_key.sh`; `firmware.yml` size step | pending |
| 57-04-01 | 04 | 3 | Docs as built, comment-history clean | static | `python3 scripts/check_comment_history.py check` | pending |
| 57-04-02 | 04 | 3 | Release instructions present with unticked preconditions | static | grep acceptance in plan | pending |
| 57-05-01 | 05 | 3 | Bench checklist unticked | static | grep acceptance in plan | pending |
| 57-06-01 | 06 | 4 | Full local regression, frozen files untouched, no tag | regression | host tests + `git tag --list 'fw-v*'` | pending |
| 57-06-02 | 06 | 4 | Compile, built config, size on the draft PR | CI | `gh pr checks` (firmware.yml pass, URL recorded) | pending |

## Roadmap Criteria Coverage

| Criterion | Covered by |
|-----------|-----------|
| 1 One release bundles reader, hardware header, 401 recovery; published only after Phase 47 and bench | 57-01, 57-03 (bundle, CI build); 57-04, 57-05 (gates, manual) |
| 2 Wakes on cadence, correct image, container only after announcing | 57-02 (server tests, freeze), 57-03 (headers); cadence on device is bench item B3 |
| 3 Failed update stays on previous firmware | `test_ota_policy.c` (existing classification); bench B2 (manual) |

## Wave 0 Requirements

- [ ] `stub-server/test_hw_claim.py` (created in 57-02 before implementation)
- [ ] New cases in test_image_container.c, test_validate.c, test_fault_screen.c, test_sleep_decision.c (57-01)
- [ ] `firmware/tests/check_hw_type_key.sh` (57-03)

## Manual-Only Verifications (owner, EE04 unit, never ticked by an agent)

| Behaviour | Why manual | Source |
|-----------|-----------|--------|
| SIGNING.md bench table | needs a non-live unit | 57-BENCH-CHECKLIST.md B1 |
| Unconfirmed-trial rollback across deep sleep | bootloader behaviour on hardware | B2 |
| Container wake, hash-skip, crc_ms, wake time | needs panel and monitor | B3, B8 |
| 401 loop and sticky fallback on device | needs device | B6, B7 |

## Validation Sign-Off

- [ ] Every task has an automated verify
- [ ] No three consecutive tasks without automated verify
- [ ] `firmware.yml` run URL recorded in 57-VERIFICATION.md
- [ ] Bench items remain unticked until the owner runs them
