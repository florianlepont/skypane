---
phase: 04
slug: ci-cd-documentation-legal-compliance-github-actions-ci-tests
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-26
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | None — this project's own stdlib `check()`/`EXPECTED_CHECK_COUNT`/`main()` convention, explicitly not pytest |
| **Config file** | none — each `server/test_*.py` / `stub-server/test_poll_cycle.py` is independently executable |
| **Quick run command** | `server/.venv/bin/python3 server/test_render.py` (any single file, run from repo root) |
| **Full suite command** | No single command runs all 9 files today — this phase's own job is to create one (`scripts/run-all-tests.sh` or equivalent), for both CI and local pre-push use |
| **Estimated runtime** | Well under a minute — the suite is fast, no live network calls in any file |

---

## Sampling Rate

- **After every task commit (during this phase's own execution):** run the full 9-file suite locally before any commit that touches CI workflow YAML.
- **After every plan wave:** same full suite, once the new CI workflow exists, via a real push.
- **Before phase close:** the CI workflow going green on a real GitHub push (not a local dry-run) is this phase's own closing acceptance signal.
- **Max feedback latency:** under 60 seconds (the suite has no slow I/O).

---

## Per-Task Verification Map

*Filled in by the planner once tasks are broken out — see 04-RESEARCH.md's "Validation Architecture" and "Security Domain" sections for the raw material (test framework shape, ASVS-relevant threats for the deploy-gate/secrets surface).*

---

## Wave 0 Requirements

- [ ] No `.github/workflows/` directory exists yet — created from scratch by this phase.
- [ ] `ruff`/`coverage` not yet installed in `server/.venv` — first task.
- [ ] No aggregate "run all 9 tests" script exists locally — add one both for CI's own use and so a contributor reading the new README can run the same command CI does.
- [ ] No `.gitignore` exists anywhere in the repo — created by this phase (D-06).

*This phase IS the Wave-0-gap-closing work for CI infrastructure itself — the test content already exists and passes; the gap is purely "nothing runs it automatically yet."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub repo creation, visibility setting, and Environment protection-rule configuration | D-01/D-02/D-11 | GitHub account/org actions have no local-CLI-only equivalent this project uses; `gh` CLI can automate some of this but the human owns the account | Create the repo via `gh repo create` or the web UI, add a `production` Environment with required reviewers, add `VPS_SSH_KEY` as a secret |
| CI workflow actually going green on a real push | D-07/D-09 | A local `act` dry-run is not equivalent to GitHub's real runner environment | Push to a branch, open a PR, confirm the Actions tab shows the workflow passing |
| Manual-approval deploy gate actually blocking until clicked | D-11 | Requires a real GitHub Environment protection rule interaction, not simulable locally | Merge to main, confirm the deploy job pauses awaiting review, approve it, confirm `deploy.sh` ran |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
