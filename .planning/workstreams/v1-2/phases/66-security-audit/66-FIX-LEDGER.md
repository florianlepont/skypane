# Phase 66 fix ledger

| Area | Change | Branch | PR | Tests | Owner-side steps pending |
|------|--------|--------|----|-------|--------------------------|
| Deploy approval (medium; D-1, S-2) | Harden deploy approval: deploy job bound to the `production` environment | `phase-66-fix-deploy-environment` | #627, #629 (merged) | `deploy/tests/test_deploy_workflow.py::test_deploy_job_is_bound_to_the_production_environment`, `::test_no_job_level_if`; `deploy/tests/test_ci_secrets.py::test_only_the_deploy_workflow_uses_a_deployment_environment` | None: done 2026-11-27 (secrets in the environment, reviewer and `main` branch rule, repo-level copies deleted, previous deploy key revoked, gated deploy succeeded) |
| Backups at rest (medium; S-3) | Protect backups at rest: opt-in disk-encryption check on the Mac pull, requirement documented | `phase-66-fix-backup-at-rest` | #628 (merged) | `deploy/tests/test_mac_pull.py::TestDiskEncryptionGate` (4 tests) | Turn FileVault on, add `REQUIRE_DISK_ENCRYPTION=1` to the Mac backup config, run the pull once |

Status: the deploy approval fix is merged, deployed and closed. The backup fix is merged; the Mac-side setting is the remaining owner step, so that entry is not closed yet.
