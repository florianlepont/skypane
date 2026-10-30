---
phase: 49
slug: per-hardware-ota-registry
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-29
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from the Validation Architecture section of 49-RESEARCH.md.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 (+ xdist, cov, pytest-socket loopback guard, pytest-playwright for `companion/test_browser_*`) |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.mypy]`, ruff) |
| **Quick run command** | `server/.venv/bin/python -m pytest server/test_firmware_registry.py server/test_firmware_cli.py server/test_firmware_reconcile.py stub-server/test_ota_offer.py deploy/tests/test_release_manifest.py -q -n0 --no-cov` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Gates** | `ruff check .`, `mypy`, `python3 scripts/check_function_size.py check --max 80 server stub-server`, `python3 scripts/check_comment_history.py check`, `sh firmware/tests/run_host_tests.sh`, `sh firmware/tests/check_production_config.sh static` |
| **Estimated runtime** | ~25 seconds (quick), longer for the full suite |

---

## Sampling Rate

- **After every task commit:** Run the quick run command (plus `ruff check` on touched files)
- **After every plan wave:** Run `./scripts/run-all-tests.sh` plus the function-size and comment-history gates
- **Before `/gsd:verify-work`:** Full suite green, mypy clean, firmware host tests and `check_production_config.sh static` green
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 49-01-01 | 01 | 1 | OTA-02 | T-49-04 | wrong magic, chip id, project name, version, unterminated strings, short signature sector, bad digest rejected; valid and real-shape images accepted | unit | `pytest server/test_firmware_image.py test-support/test_test_support.py -q -n0 --no-cov` | W0 | pending |
| 49-01-02 | 01 | 1 | OTA-02 | T-49-04 | firmware size bound separate from display bound (`max_app_bytes` 0x250000) | unit | `pytest server/test_hardware.py server/test_firmware_image.py -q -n0 --no-cov && mypy` | W0 | pending |
| 49-02-01 | 02 | 1 | OTA-03 | - | decision record section present, no option chosen | doc | `grep -c "Decision record (OTA-03)" firmware/SIGNING.md` | W0 | pending |
| 49-02-02 | 02 | 1 | OTA-03 | - | owner decision gate (checkpoint) | manual | `grep -c "Decision record (OTA-03)" firmware/SIGNING.md` | manual | pending |
| 49-02-03 | 02 | 1 | OTA-03 | - | decision (or deferral) recorded | doc | `! grep -v '^#' firmware/SIGNING.md \| grep -q "PENDING OWNER DECISION"` | W0 | pending |
| 49-03-01 | 03 | 1 | OTA-01, OTA-02 | - | per-type documents, legacy shape untouched, `.pre-fleet` created once | unit | `pytest server/test_firmware_registry.py -q -n0 --no-cov -k "type or pre_fleet or build_number or legacy_shape or registry"` | W0 | pending |
| 49-03-02 | 03 | 1 | OTA-01 | T-49-35 | type-scoped reconcile and update view; unresolved sentinel matches no document | unit | `pytest server/test_firmware_registry.py server/test_firmware_reconcile.py -q -n0 --no-cov && check_function_size` | W0 | pending |
| 49-04-01 | 04 | 2 | OTA-02 | - | server-side fixtures migrated to valid synthetic images | unit | `pytest server/test_firmware_registry.py server/test_firmware_reconcile.py server/test_firmware_cli.py server/test_retired_notifications.py -q -n0 --no-cov` | exists | pending |
| 49-04-02 | 04 | 2 | OTA-02 | - | offer, manifest and companion fixtures migrated | integration | `pytest stub-server/test_ota_offer.py deploy/tests/test_release_manifest.py companion/test_update_page.py companion/test_update_actions.py -q -n0 --no-cov` | exists | pending |
| 49-05-01 | 05 | 3 | OTA-01, OTA-02 | - | wrong chip/project/version/unsigned/oversize rejected before any write; re-import never revalidates; grandfather rule; legacy `max_app_bytes == 0x250000` | unit | `pytest server/test_firmware_registry.py -q -n0 --no-cov -k "publish or grandfather or validation"` | W0 | pending |
| 49-05-02 | 05 | 3 | OTA-02 | - | lower build refused per type, bench exempt, numeric order, rollback via schedule kept | unit | `pytest server/test_firmware_registry.py server/test_firmware_reconcile.py stub-server/test_ota_offer.py -q -n0 --no-cov && check_function_size` | W0 | pending |
| 49-06-01 | 06 | 4 | OTA-01, OTA-02 | - | build-ordered per-type import-dir; re-import idempotent | unit | `pytest server/test_firmware_cli.py -q -n0 --no-cov` | exists | pending |
| 49-06-02 | 06 | 4 | OTA-01 | - | operator docs for per-type publishing | doc | `pytest deploy/tests/test_docs.py -q -n0 --no-cov` | exists | pending |
| 49-07-01 | 07 | 4 | OTA-01 | T-49-19..21, T-49-23 | each frame offered only its own type; fail closed on unknown/disabled/fleet-only; display response and Phase 47 freeze unchanged | integration | `pytest stub-server/test_ota_offer.py stub-server/test_phase47_freeze.py stub-server/test_fleet_auth.py -q -n0 --no-cov -k "hardware or offer or freeze or auth"` | W0 | pending |
| 49-07-02 | 07 | 4 | OTA-01 | T-49-35 | type stamp or unresolved sentinel; multi-document `/fw`; reconcile-all | integration | `pytest stub-server/test_ota_offer.py stub-server/test_phase47_freeze.py stub-server/test_fleet_auth.py server/test_poll_cycle_steps.py server/test_firmware_reconcile.py -q -n0 --no-cov && check_function_size` | W0 | pending |
| 49-08-01 | 08 | 4 | OTA-01 | - | one-type page byte-identical to golden; two-type chooser and POST validation | unit | `pytest companion/test_update_page.py companion/test_update_actions.py -q -n0 --no-cov` | W0 (golden `companion/testdata/update_page_one_type_golden.json`) | pending |
| 49-08-02 | 08 | 4 | OTA-01 | - | EN/FR strings; browser flows with two types | browser | `pytest companion/test_browser_update.py companion/test_update_page.py -q -n0 --no-cov` and i18n coverage tests | exists | pending |
| 49-09-01 | 09 | 4 | OTA-01, OTA-02 | T-49-28 | manifest carries `hardware_type` and `build`; descriptor/type mismatch fails; round-trips through `publish_release`; size bound equals 0x250000 | subprocess | `pytest deploy/tests/test_release_manifest.py -q -n0 --no-cov` | exists, extend | pending |
| 49-09-02 | 09 | 4 | OTA-01, OTA-02 | T-49-27 | release workflow verifies descriptor and signature sector | unit | `pytest deploy/tests/test_ci_secrets.py deploy/tests/test_release_manifest.py -q -n0 --no-cov` and YAML parse | exists | pending |
| 49-10-01 | 10 | 5 | OTA-03 | T-49-29 | PEM modulus reader; key mismatch refused | unit | `pytest server/test_firmware_image.py -q -n0 --no-cov && mypy` | W0 | pending |
| 49-10-02 | 10 | 5 | OTA-03 | T-49-29, T-49-30 | per-type signing policy from the profile; matching option verified hardware-free | unit + C host + shell | `pytest server/test_firmware_image.py server/test_hardware.py server/test_firmware_registry.py deploy/tests/test_release_manifest.py -q -n0 --no-cov && sh firmware/tests/run_host_tests.sh && sh firmware/tests/check_production_config.sh static && mypy` | W0, conditional on decision | pending |
| 49-10-03 | 10 | 5 | OTA-03 | T-49-31 | real device rejects a wrongly signed image and reports `fail-image` | manual bench | `sh firmware/tests/check_production_config.sh static` (config only; behaviour is hardware) | manual | pending |
| 49-11-01 | 11 | 5 | OTA-01, OTA-02 | T-49-34 | real-shape `registry.json` still drives offer/view/schedule; `.pre-fleet` byte-identical; cross-type end-to-end | integration | `pytest stub-server/test_ota_fleet_regression.py -q -n0 --no-cov` | W0 | pending |
| 49-11-02 | 11 | 5 | OTA-01, OTA-02, OTA-03 | - | phase gate | full suite | `./scripts/run-all-tests.sh && ruff check . && mypy && check_function_size && check_comment_history && sh firmware/tests/run_host_tests.sh && sh firmware/tests/check_production_config.sh static` | exists | pending |

*Status: pending · green · red · flaky*

---

## Requirement Coverage

| Req ID | Behavior | Test Type | Automated Command | Plans |
|--------|----------|-----------|-------------------|-------|
| OTA-01 | Two sim types, each scheduled differently, polled through real byos: each offered only its own type's release | integration | `pytest stub-server/test_ota_offer.py -k hardware -q` | 03, 05, 07, 11 |
| OTA-01 | Unknown/absent type, sim key with gate off, fleet.db fault plus MAC not in devices.json: no offer; fault plus MAC in devices.json: legacy offer | integration | same file | 07 |
| OTA-01 | Independent schedules, cancel and reconcile per type | unit | `pytest server/test_firmware_registry.py server/test_firmware_reconcile.py -k type` | 03 |
| OTA-01 | Update page: one type identical to today; two types show chooser; POST validates type | unit + browser | `pytest companion/test_update_page.py companion/test_update_actions.py -q`; `companion/test_browser_update.py` | 08 |
| OTA-02 | Image header, descriptor, signature sector rejections and acceptance | unit | `pytest server/test_firmware_image.py -q` | 01, 05 |
| OTA-02 | Lower build refused, equal+same sha idempotent, equal+different sha refused, bench exempt, per-type independence | unit | `pytest server/test_firmware_registry.py server/test_firmware_cli.py -k build` | 05, 06 |
| OTA-02 | Re-import never re-validates; absent `hardware_type` only for grandfathered | unit | `pytest server/test_firmware_cli.py` | 05, 06 |
| OTA-03 | Policy verdicts for the device decision code | C host test | `sh firmware/tests/run_host_tests.sh` | 10 |
| OTA-03 | Production config chain unchanged and, per decision, extended | shell | `sh firmware/tests/check_production_config.sh static` | 10 |
| OTA-03 | Server accepts an image only if embedded modulus matches the key chosen for its type | unit | `pytest server/test_firmware_image.py -k key` | 10 |
| OTA-03 | Real device rejects a wrongly signed image and reports `fail-image` | manual bench | n/a (hardware) | 10 |
| Criterion 4 | Live-shaped `registry.json` unchanged behaviour; `.pre-fleet` created once | unit | `pytest server/test_firmware_registry.py -k pre_fleet` | 03, 11 |
| Manifest | `fw_release_manifest.py` emits `hardware_type`, `build`; refuses mismatch; round-trips | subprocess | `pytest deploy/tests/test_release_manifest.py -q` | 09 |

---

## Wave 0 Requirements

- [ ] `test-support/` helper building a valid synthetic signed-shape ESP image (plan 01), then migration of the arbitrary-bytes fixtures (plan 04)
- [ ] `server/test_firmware_image.py` (plan 01)
- [ ] `test-support/skypane_legacy_registry.py` legacy-shape registry helper (plan 03)
- [ ] `companion/testdata/update_page_one_type_golden.json` captured before the page changes (plan 08)
- [ ] Behaviour-over-source: tests assert registry files, byos JSON and served HTML, never source text or `.planning/`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A running device accepts a correctly signed OTA image and rejects a wrongly signed one with `fail-image` | OTA-03 (criterion 3) | Needs a bench unit that is not the live frame; no emulator is known to exercise the OTA signature path | Bench procedure in `firmware/SIGNING.md` "Verification status" (plan 49-10 Task 3). An owner deferral leaves criterion 3 unmet and must not be reported as passed. |
| OTA-03 signing option choice | OTA-03 | Owner decision, not made by the planner | Checkpoint in plan 49-02 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s for the quick command
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
