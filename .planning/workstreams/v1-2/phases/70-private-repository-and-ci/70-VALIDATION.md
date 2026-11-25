---
phase: 70
slug: private-repository-and-ci
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-11-24
---

# Phase 70 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.2.0 + xdist + cov + pytest-playwright 0.10.0 (locked); shell tests with PATH shims for deploy and firmware scripts |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.report] fail_under`) |
| **Quick run command** | `server/.venv/bin/python -m pytest deploy/tests -q` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Estimated runtime** | quick about 30 seconds; full about 20 minutes on the Mac runner (measured in 70-07) |

---

## Sampling Rate

- **After every task commit:** touched test files plus `server/.venv/bin/ruff check .`, `python scripts/check_comment_history.py check`, `python scripts/check_function_size.py check --max 80 server stub-server`, `find deploy -name '*.sh' -print0 | xargs -0 shellcheck` (if present), mypy if modules are added to the `pyproject.toml` list
- **After every plan wave:** `./scripts/run-all-tests.sh`
- **Before `/gsd:verify-work`:** full suite green on CI plus the manual proofs (deploy from main and non-main, test release, runner run, hosted fallback)
- **Max feedback latency:** 60 seconds for the quick command

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 70-01-* | 01 | 1 | PRV-01 | T-70-02 | deploy.yml: `workflow_dispatch` only, no `environment`, secrets only via `env:` | text scan | `pytest deploy/tests/test_ci_secrets.py -q` (repointed to deploy.yml) | exists, repoint | ⬜ pending |
| 70-01-* | 01 | 1 | PRV-01 | — | "Download firmware releases" behaves with a fake `gh` | behaviour | `pytest deploy/tests/test_release_assets.py -q` (`_CI_YML` to deploy.yml) | exists, repoint | ⬜ pending |
| 70-01-* | 01 | 1 | PRV-01 | — | shellcheck step still in ci.yml | text | `pytest deploy/tests/test_install_backup_key.py::test_ci_yml_shellchecks_deploy_scripts -q` | exists | ⬜ pending |
| 70-05-* | 05 | 3 | PRV-01 | T-70-SC | Mac publish script: provenance, SHA256SUMS mismatch refused, off-main tag refused, exactly seven asset names, dry-run publishes nothing | unit with fake `gh`/`docker`/`git` | `pytest deploy/tests/test_fw_publish_signed.py -q` | ❌ W0 | ⬜ pending |
| 70-05-* | 05 | 3 | PRV-01 | — | signed image passes `fw_release_manifest.py --check-only` and the typed asset selector | existing | `pytest deploy/tests/test_release_manifest.py deploy/tests/test_release_assets.py -q` | exists | ⬜ pending |
| 70-02-* | 02 | 2 | PRV-01 | T-70-07 | gate end-to-end: main succeeds, other branch and wrong `confirm_sha` fail at the guard | manual proof | owner dispatches `deploy.yml` (see Manual-Only) | manual | ⬜ pending |
| 70-02b | 02b | — | PRV-01 | T-70-07 | deploy gate verbs and rejections (only if the owner chooses a gate or ticket) | unit | `pytest deploy/tests/test_deploy_gate.py -q` | ❌ W0, conditional | ⬜ pending |
| 70-06-* | 06 | 2 | PRV-02 | T-70-22 | `CI_RUNS_ON` runs-on, sudo steps guarded, fork guard, no `pull_request_target`, setup-python guarded | text scan | `pytest deploy/tests/test_ci_runner.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 70-06-* | 06 | 2 | PRV-02 | T-70-21 | runner launcher never exposes the admin token | unit with shims | `pytest deploy/tests/test_runner_loop.py -q` | ❌ W0 (created in task) | ⬜ pending |
| 70-06-* | 06 | 2 | PRV-02 | — | shard counts consistent | existing | `server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2` | exists | ⬜ pending |
| 70-07-* | 07 | 3 | PRV-02 | T-70-28 | measured minutes, wall-clock, D-07 owner decision recorded | manual measurement | `scripts/ci_run_timing.py jobs <run-id>` (owner's Mac) | exists | ⬜ pending |
| 70-0x-* | 03-04, 08 | — | PRV-03 | T-70-05 | scan script classifies fixtures and never prints a matching value | unit | `pytest scripts/test_exposure_scan.py -q` (synthetic strings built at test time) | ❌ W0 | ⬜ pending |
| 70-10-* | 10 | 6 | PRV-01..03 | T-70-37 | post-switch checklist, 10-row pre-flip gate | manual | items in 70-10 Task 1 and 3 | manual | ⬜ pending |
| all | all | — | must-not-break | — | golden hashes, freeze, signed path | existing | `pytest stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py -q`; `./scripts/run-all-tests.sh` | exists | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `deploy/tests/test_fw_publish_signed.py` — covers the Mac publish script (PRV-01)
- [ ] `scripts/test_exposure_scan.py` — covers the exposure scan script (PRV-03)
- [ ] `deploy/tests/test_deploy_gate.py` — only if the owner chooses a gate (plan 70-02b)
- [ ] Repoint `deploy/tests/test_ci_secrets.py` (step names; `DEPLOY_*` asserts now in `deploy.yml`; assert no `FW_SIGNING_KEY` in any workflow) and `deploy/tests/test_release_assets.py` (`_CI_YML` to `deploy.yml`)
- [ ] Add new typed scripts to the `[tool.mypy]` module list; keep function sizes at or below 80

Docs-pinning tests to keep consistent when rewriting: `deploy/tests/test_docs.py` (README strings, lift-runbook phrase "`ci.yml`" to be updated together with the test), `firmware/SIGNING.md` "## Per-type releases" strings, `companion/test_compliance_credits.py` source headings, `server/test_firmware_partition_bound.py` (90 percent literal in `firmware.yml`).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Deploy from main succeeds; from another branch and with wrong `confirm_sha` fails | PRV-01 | needs real secrets and the VPS, owner-only | 70-02 Task 3 |
| Signed test release end to end (tag, CI artifact, Mac sign and publish, deploy import) | PRV-01 | needs the signing key on the owner's Mac | 70-05 |
| Runner installed; full CI green on the Mac; hosted fallback run | PRV-02 | owner's Mac and token | 70-07 |
| D-07 owner decision recorded | PRV-02 | owner decision | 70-07 Task 0 |
| Post-switch: session push, draft PR, CI logs through the integration; Dependabot; nightly backup; deploy; firmware release dry-run with `gh run download` | PRV-01..03 | needs the private repository | 70-10 Tasks 1 and 3 |
| Free private plan: no branch protection, rulesets, environments, secret scanning or push protection assumed | PRV-01 | platform limit | grep `.github` for `environment:` (70-10 Task 3) |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify (manual checkpoints carry grep checks on evidence files)
- [ ] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s for the quick command
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
