# Phase 70: Private Repository and CI - Context

**Gathered:** 2026-11-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The whole repository becomes private (owner decision of 2026-11-24, firm, not to be reopened). Before the visibility changes, the pipeline is changed so that the production deploy and the firmware signing stay under the owner's explicit control on the GitHub Free plan, the CI fits the plan, and an inventory of what has been public is made and handled. The visibility is flipped LAST, by the owner himself in GitHub settings, only after roadmap success criteria 1 to 3 pass. The live frame, production, the signed release path and its signed image, the golden hashes and `stub-server/test_phase47_freeze.py` must not break.

Not in this phase: another git platform, splitting the repository, legal review of the licences (SEED-015).

</domain>

<decisions>
## Implementation Decisions

### Plan and organisation
- **D-01:** Stay on the GitHub Free plan with the repository on the owner's personal account. No Team plan, no organisation. Reason: the Team plan would not fix the CI minutes (see D-05), and the docs conflict on whether environment approvals work in private repositories on Team (docs say yes, the pricing page says public only), so nothing may rely on it.
- **D-02:** The owner asked whether an organisation can be personal: yes, a one-member organisation is free to create and Team would cost $4 per month for one seat. Recorded as the fallback if the Free-plan design proves unworkable; not built in this phase.

### Production deploy
- **D-03:** The production deploy becomes a workflow the owner starts by hand (`workflow_dispatch`); a merge to `main` no longer deploys. Confirmed by the owner. It must not depend on environment reviewers. Proof on a test run is required before the visibility changes (criterion 1).
- **D-04:** `deploy` must also be reachable from the firmware release path (today `firmware-release.yml` ends with `gh workflow run ci.yml --ref main` after publishing a release). The planner decides how the owner-started deploy imports a new release, keeping the import idempotent and the stale-main check of the current deploy job.

### CI
- **D-05:** The hosted CI cannot fit the Free plan. Measured on run 45337958006 (job times rounded up per minute): 60 billable minutes per full run (static 1, core shards 7+6, browser shards 10+7+9+10+9, aggregate 1), against about 2,000 included Linux minutes per month ($12 of compute at $0.006). Recent rate: 30 runs in 36 hours, so 18,000 to 36,000 minutes per month, 8 to 18 times the quota; overage would be roughly $100 to $200 per month. Team ($18, about 3,000 minutes) would not change this.
- **D-06:** CI runs on a self-hosted runner on the owner's Mac, never on the production server. The runner must be secured (private repository, no fork pull requests, Linux container or ephemeral runs, no production secrets on it, branches pushed by sessions run code on the Mac so the isolation must be stated). GitHub's current docs say self-hosted runners are free; the announced $0.002 per minute charge (from 1 March 2026) is postponed with no date, so it is a watched risk (about $36 to $72 per month at the current rate). Where exactly the runner lives and how the CI behaves when the Mac is off are for research and planning.
- **D-07:** Reduced CI: keep the existing docs-only skip and add path-based job splitting so heavy jobs do not run when no code changed. No test is skipped for a code change, and the browser tests run on every change to code. Measured minutes per run and the monthly total are recorded before and after.

### Firmware signing
- **D-08:** Option C: firmware is signed on the owner's Mac so the private key never leaves it. No signing key in a GitHub secret. The release path of the live frame and its signed image stay unchanged, and the server imports a signed test release. A harmless test release is made first. The current `firmware-signing` environment is retired only after the new path is proven, and only with the owner's explicit confirmation (no secret is rotated or deleted by a session).

### Inventory and visibility
- **D-09:** A written inventory of what has been public is made (secrets in the tree and in git history, personal data, commercial planning notes in `.planning/`); copies already taken stay public. Anything sensitive is handled with the owner (rotated or recorded with his decision). Never print a secret.
- **D-10:** Order is fixed: pipeline changes, then proof of criteria 1 to 3, then the owner flips the visibility himself. After the switch, check that sessions can push branches and open draft pull requests and read CI logs, that the nightly backup, the `gh release download` in the deploy, Dependabot and a firmware release still work.
- **D-11:** On a private Free repository there is no branch protection, no rulesets and no environments, and secret scanning is public-only. The plan must not assume any of them, and the audit in Phase 66 sees the final setup.

### Claude's Discretion
- Exact workflow structure, job and path-filter names, how the runner is installed and updated, the signing script's interface on the Mac, the shape of the inventory document.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and requirements
- `.planning/workstreams/v1-2/ROADMAP.md` — "Phase 70" section: goal, success criteria 1 to 6, must-not-break list
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — PRV-01, PRV-02, PRV-03

### Pipeline and docs to change
- `.github/workflows/ci.yml` — CI jobs, shard counts, `deploy` job with `environment: production`, secrets `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_SSH_TARGET`
- `.github/workflows/firmware-release.yml` — tag-triggered release, `environment: firmware-signing`, `FW_SIGNING_KEY`, final dispatch of ci.yml
- `.github/workflows/firmware.yml`, `.github/workflows/firmware-chain-check.yml` — firmware host tests and chain check
- `.github/dependabot.yml` — Dependabot must keep working
- `firmware/SIGNING.md`, `deploy/README.md`, `COMPLIANCE.md`, `README.md` — to rewrite for the new setup (criterion 6)
- `scripts/ci_shards.py`, `scripts/ci_gates.py`, `scripts/fw_release_assets.py` — shard, gate and release-asset logic the pipeline relies on
- `stub-server/test_phase47_freeze.py` — must not break

### GitHub facts (checked 2026-11-24)
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments — environments in private repositories are Pro/Team only
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments — required reviewers and environment secrets
- https://docs.github.com/en/billing/managing-billing-for-github-actions/about-billing-for-github-actions — included compute per plan
- https://docs.github.com/en/billing/reference/actions-runner-pricing — per-minute rates
- https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions — self-hosted runner charge, postponed

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/ci_shards.py`, `scripts/ci_gates.py`: shard assignment and the JUnit and coverage gates stay as they are on any runner.
- The deploy job's "refuse to deploy if main moved on" step and the idempotent firmware import in `deploy/deploy.sh` and `activate.sh`.

### Established Patterns
- Third-party actions pinned by SHA; least-privilege `permissions: contents: read`; secrets passed through `env:` never interpolated into `run:`.
- Shards run in a matrix: 2 core and 5 browser, plus static and an aggregate job.

### Integration Points
- `firmware-release.yml` dispatches `ci.yml` on `main` after publishing a release: this link changes with D-03 and D-08.
- The deploy job downloads releases with `gh release download` using `github.token`.
- Repository secrets are readable by any workflow on any branch on Free: the planner must consider restricting the deploy SSH key on the server side (forced command, limited path) since no environment protects it.

</code_context>

<specifics>
## Specific Ideas

- The owner wants short answers in French; written artefacts in English.
- A harmless test release proves manual deploy and Mac signing before anything real changes.

</specifics>

<deferred>
## Deferred Ideas

- Team plan with a one-member organisation, if the Free design proves unworkable (D-02).
- Moving the runner to a second small server if the Mac proves unreliable.

</deferred>

---

*Phase: 70-Private Repository and CI*
*Context gathered: 2026-11-24*
