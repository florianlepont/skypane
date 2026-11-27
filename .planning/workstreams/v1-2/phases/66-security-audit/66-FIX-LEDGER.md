# Phase 66 fix ledger

| Area | Change | Branch | PR | Tests | Owner-side steps pending |
|------|--------|--------|----|-------|--------------------------|
| Deploy approval (medium; D-1, S-2) | Harden deploy approval: deploy job bound to the `production` environment | `phase-66-fix-deploy-environment` | #627 (draft) | `deploy/tests/test_deploy_workflow.py::test_deploy_job_is_bound_to_the_production_environment`, `::test_no_job_level_if`; `deploy/tests/test_ci_secrets.py::test_only_the_deploy_workflow_uses_a_deployment_environment` | Create `production` environment, add the 3 secrets, add required reviewer, delete repo-level copies, test one deploy pauses for approval |
| Backups at rest (medium; S-3) | Protect backups at rest: opt-in disk-encryption check on the Mac pull, requirement documented | `phase-66-fix-backup-at-rest` | #628 (draft) | `deploy/tests/test_mac_pull.py::TestDiskEncryptionGate` (4 tests) | Turn FileVault on, add `REQUIRE_DISK_ENCRYPTION=1` to the Mac backup config, run the pull once |
