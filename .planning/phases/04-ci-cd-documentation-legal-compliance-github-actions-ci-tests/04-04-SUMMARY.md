---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
plan: 04
subsystem: infra
tags: [github-actions, ci-cd, actionlint, ruff, coverage, ssh-agent, esp-idf, docker]

requires:
  - phase: 04-02
    provides: scripts/run-all-tests.sh (canonical 9-harness runner), pyproject.toml (Ruff ruleset + coverage threshold), server/requirements-dev.txt
  - phase: 04-03
    provides: scripts/check-attribution.sh (attribution audit)
provides:
  - .github/workflows/ci.yml — blocking test job (lint, 9 harnesses, coverage threshold, attribution check) on every push and pull request
  - .github/workflows/ci.yml — human-gated deploy job wrapping deploy/deploy.sh, gated by a green pipeline + push-to-main + a named GitHub Environment
  - .github/workflows/firmware.yml — path-restricted firmware build wrapping firmware/build.sh directly (no marketplace action)
affects: [04-06]

tech-stack:
  added: [actionlint (local validation only, not a CI dependency), webfactory/ssh-agent@v0.9.1, actions/checkout@v4, actions/setup-python@v5]
  patterns: ["single CI workflow file with sequential needs: jobs instead of cross-workflow dependencies", "wrap existing scripts from YAML rather than reimplementing their logic", "secret-supplied host key instead of ssh-keyscan"]

key-files:
  created:
    - .github/workflows/ci.yml
    - .github/workflows/firmware.yml
  modified: []

key-decisions:
  - "One ci.yml file with two needs:-linked jobs, not the two-file split 04-RESEARCH.md sketched — a job cannot depend on a job in a different workflow file; only workflow_run crosses that boundary and it has documented pitfalls the research itself flagged."
  - "D-10 (firmware CI, discretionary): included, built directly on firmware/build.sh rather than the espressif/esp-idf-ci-action marketplace action — the script already pins the toolchain image and the two-file sdkconfig invocation, so CI builds with the identical command used locally and 04-RESEARCH.md's Assumption A2 (unverified marketplace-action parameter mapping) never arises."
  - "Host key for the deploy job comes from a dedicated secret (DEPLOY_HOST_KEY) written straight into known_hosts, not from ssh-keyscan at deploy time — scanning is trust-on-first-use on every single run and was an explicit hardening over 04-RESEARCH.md's Pattern 2 skeleton."
  - "Three separate secrets referenced (DEPLOY_SSH_PRIVATE_KEY, DEPLOY_HOST_KEY, DEPLOY_SSH_TARGET) rather than one value sliced apart in a run step, so each is independently masked in logs."

requirements-completed: [D-07, D-08, D-09, D-10, D-11, D-12]

coverage:
  - id: D1
    description: "ci.yml test job runs blocking lint, all 9 harnesses via scripts/run-all-tests.sh, the coverage threshold, and scripts/check-attribution.sh on every push and pull request"
    requirement: "D-07, D-08, D-09"
    verification:
      - kind: other
        ref: "actionlint .github/workflows/ci.yml (schema/expression/shell validation)"
        status: pass
      - kind: other
        ref: "grep-based structural verification: invokes scripts/run-all-tests.sh and scripts/check-attribution.sh, installs both requirements files, no test filename, no threshold number, no continue-on-error, no mutable action ref"
        status: pass
      - kind: other
        ref: "./scripts/run-all-tests.sh (local dry run of the exact command the workflow calls) — 9/9 harnesses pass, coverage 79% >= 75% threshold"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check . (local dry run of the exact command the workflow calls)"
        status: pass
    human_judgment: true
    rationale: "This workflow cannot be observed running green on GitHub's own infrastructure until plan 04-06 pushes the repository and creates the Actions-enabled remote — local actionlint + grep verification + reproducing every command locally is the strongest evidence obtainable this session, but a real triggered run is the only full proof. Carried forward explicitly as a verification gap."
  - id: D2
    description: "ci.yml deploy job is gated behind the test job succeeding, a push-to-main-only condition (never pull_request), and a named production GitHub Environment; it invokes deploy/deploy.sh unchanged with no rsync/systemctl duplicated in YAML"
    requirement: "D-11, D-12"
    verification:
      - kind: other
        ref: "actionlint .github/workflows/ci.yml (whole file, both jobs)"
        status: pass
      - kind: other
        ref: "grep-based verification: needs:, environment:, github.event_name == 'push' condition present; no rsync/systemctl; no ssh-keyscan; >=3 distinct secrets.* references; no dotted-quad/hostname literal"
        status: pass
    human_judgment: true
    rationale: "The approval pause itself (D-11) only becomes observable once plan 04-06 creates the 'production' GitHub Environment with a required reviewer attached and a real push triggers the job — that live pause-and-approve behavior needs a human watching the Actions tab, which is explicitly plan 04-06's acceptance criterion, not this plan's."
  - id: D3
    description: "firmware.yml builds the EE02 firmware image in CI via firmware/build.sh directly (same containerised toolchain invocation used locally), path-restricted to firmware/** changes"
    requirement: "D-10"
    verification:
      - kind: other
        ref: "actionlint .github/workflows/firmware.yml"
        status: pass
      - kind: other
        ref: "grep-based verification: invokes firmware/build.sh, creates secrets.h from secrets.example.h, paths: restriction present, no espressif/idf: image reference or SDKCONFIG_DEFAULTS flag in YAML, no mutable action ref"
        status: pass
      - kind: other
        ref: "git status --porcelain clean after workflow authoring — firmware/main/secrets.h (pre-existing, real, gitignored) untouched by this plan"
        status: pass
    human_judgment: true
    rationale: "The actual containerised build (docker run espressif/idf:v5.3.1 idf.py build) was not executed in this sandbox session — it requires pulling a multi-GB toolchain image, which is disproportionate to validate locally when firmware/build.sh's Docker invocation was already proven working in Phase 1 hardware bring-up and this workflow adds no new invocation logic. A real CI run (plan 04-06) is the first true end-to-end proof."

duration: 12min
completed: 2026-08-26
status: complete
---

# Phase 04 Plan 04: CI/CD Workflows Summary

**Two GitHub Actions workflows — a single ci.yml with a blocking lint/test/coverage/attribution job feeding a human-gated deploy job, plus a path-restricted firmware.yml that wraps firmware/build.sh directly instead of a marketplace action — turning every locally-verified D-07 through D-12 guarantee into an automated one.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-26T19:27:00Z
- **Completed:** 2026-08-26T19:39:03Z
- **Tasks:** 3
- **Files modified:** 2 (both new)

## Accomplishments
- `.github/workflows/ci.yml` test job: checkout, pinned Python 3.12, venv install from `server/requirements.txt` then `server/requirements-dev.txt`, blocking `ruff check .` (rule set lives in `pyproject.toml`, not restated), `scripts/run-all-tests.sh` (all 9 harnesses + coverage threshold), `scripts/check-attribution.sh` — triggered on pushes to `main` and every pull request.
- `.github/workflows/ci.yml` deploy job: depends on the test job, restricted to `push` events on `main` (the pull-request trigger cannot reach it — confirmed by the `if:` condition and by `actionlint`), declares `environment: { name: production }` so GitHub pauses for a required reviewer once plan 04-06 attaches one, loads the SSH key via `webfactory/ssh-agent@v0.9.1`, writes the expected host key from a secret into `known_hosts` (no `ssh-keyscan`), then runs `deploy/deploy.sh "${{ secrets.DEPLOY_SSH_TARGET }}"` — the only deploy action, no rsync/systemctl duplicated.
- `.github/workflows/firmware.yml`: path-restricted to `firmware/**` and its own file, copies `firmware/main/secrets.example.h` to `firmware/main/secrets.h` (compile-only placeholders) then runs `./firmware/build.sh` unchanged, asserting `firmware/build-ee02/inkframe.bin` exists afterward.
- Both files validated clean under `actionlint`; the exact commands the workflow calls (`ruff check .`, `scripts/run-all-tests.sh`) were also run locally and passed (9/9 harnesses, 79% coverage against a 75% threshold).

## Task Commits

1. **Task 1: CI workflow — blocking lint, tests, coverage, and attribution** - `c046c16` (feat)
2. **Task 2: Deploy job — human-gated, secret-driven, wrapping deploy.sh unchanged** - `64d7e26` (feat)
3. **Task 3: Firmware build workflow** - `598c9e2` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `.github/workflows/ci.yml` - Two-job workflow: blocking test job (lint/9-harness-suite/coverage/attribution) + human-gated deploy job wrapping `deploy/deploy.sh`
- `.github/workflows/firmware.yml` - Path-restricted firmware build wrapping `firmware/build.sh` directly

## Repository Secrets Plan 04-06 Must Create

Exact names referenced in `.github/workflows/ci.yml`'s deploy job — none of their values exist anywhere in either workflow file:

| Secret name | Purpose |
|---|---|
| `DEPLOY_SSH_PRIVATE_KEY` | The VPS deployment SSH private key, loaded into an agent by `webfactory/ssh-agent` |
| `DEPLOY_HOST_KEY` | The expected production host's SSH public key line(s), written into `known_hosts` (replaces host-key scanning) |
| `DEPLOY_SSH_TARGET` | The full SSH target string (`user@host`) passed as `deploy/deploy.sh`'s one positional argument |

## Decisions Made

- **Single `ci.yml` file with `needs:`-linked jobs**, not the two-file `ci.yml`/`deploy.yml` split 04-RESEARCH.md's "Recommended Project Structure" sketched. Planner finding W3 established live during planning that a job cannot declare `needs:` on a job in a *different* workflow file — the only cross-workflow mechanism is `workflow_run`, which the research itself flags as carrying well-known pitfalls. 04-RESEARCH.md's own "Full CI workflow skeleton" code example already uses the one-file, ordinary-dependency shape — that skeleton, not the prose structure section above it, is what this plan builds from.
- **Firmware CI (D-10, discretionary) included, built on `firmware/build.sh` directly** rather than `espressif/esp-idf-ci-action`. The script already pins `espressif/idf:v5.3.1` and already passes the two-file `SDKCONFIG_DEFAULTS` invocation that 04-RESEARCH.md's Assumption A2 flagged as the marketplace action's unverified parameter-mapping risk. Invoking the script means CI and local builds are byte-for-byte the same command; the open question about parameter mapping never arises.
- **Host key from a secret, not `ssh-keyscan`.** 04-RESEARCH.md's Pattern 2 skeleton uses `ssh-keyscan -H "${{ secrets.VPS_HOST }}"` at deploy time — accepted here as a real security downgrade (trust-on-first-use on every single run, silently trusting an impostor host). Deliberately substituted a dedicated `DEPLOY_HOST_KEY` secret written straight into `known_hosts` instead, per the plan's explicit instruction.
- **Three separate secrets, not one value sliced apart.** Each of `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_SSH_TARGET` is masked independently in Actions logs; a substring derived from a combined secret would not be.
- **Pull-request trigger confirmed unable to reach the deploy job.** The job's `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` condition is the sole gate on this; `actionlint` validates the expression syntax, and the grep-based verification independently confirms both the condition text and the absence of any `pull_request`-triggered path into the job.

## Deviations from Plan

None - plan executed exactly as written. The two structural choices above (one-file structure, `firmware/build.sh` over the marketplace action) were already directed by the plan's own `<planner_findings>` (W3, W4) and `<important_context>` — not deviations from the plan, but the plan's own resolved decisions being implemented as specified.

## Issues Encountered

None. `actionlint` (pre-installed at `/opt/homebrew/bin/actionlint`, confirmed per planner finding W1) validated both files cleanly on the first pass for every task; no rework was needed.

## Verification Gap Carried Forward

Per the plan's own framing ("Neither runs on real infrastructure until plan 04-06 pushes the repository"): this workflow cannot be observed running on GitHub's actual Actions infrastructure — including whether the `production` Environment's approval pause is really enforced, whether the firmware Docker build genuinely succeeds on a hosted runner, and whether the deploy job's SSH connection to the real VPS succeeds — until plan 04-06 creates the GitHub repository, pushes this code, configures the three secrets above, and creates the `production` Environment with a required reviewer. This plan's verification is the strongest evidence obtainable pre-push: `actionlint` schema/expression/shell validation, structural grep checks against every acceptance criterion, and local reproduction of the exact commands the workflow invokes (lint, full test suite). Plan 04-06 owns closing this gap with a real triggered run.

## User Setup Required

None from this plan directly. Plan 04-06 will need to create three repository secrets (`DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_SSH_TARGET`, table above) and a `production` GitHub Environment with a required reviewer attached — both are plan 04-06's explicit scope, not this plan's.

## Next Phase Readiness

- `.github/workflows/ci.yml` and `.github/workflows/firmware.yml` are complete, `actionlint`-clean, and contain no host-identifying or credential literal — safe to publish as-is once plan 04-01's repository history scrub is live on GitHub.
- Plan 04-06 has a precise, named list of secrets and one Environment to create before the deploy gate becomes real; the workflow YAML side of that gate is fully wired and just needs the repository-side configuration.
- No blockers for 04-05 (README/ARCHITECTURE docs) — no file overlap with this plan's outputs.

---
*Phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Completed: 2026-08-26*

## Self-Check: PASSED

All created files and task commits verified present on disk / in git log.
