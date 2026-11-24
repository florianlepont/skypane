# Phase 70: Private Repository and CI - Research

**Researched:** 2026-11-24
**Domain:** GitHub Actions on the Free plan (private repo), self-hosted runner on the owner's Mac, manual production deploy, firmware signing off-GitHub, public-exposure inventory
**Confidence:** MEDIUM-HIGH (GitHub billing/environment facts verified in current docs; the Mac hardware, the cloud-session token scopes and a few runner behaviours cannot be verified from this sandbox and are flagged)

## Summary

The three pipeline changes are all feasible on Free with no paid feature, but the research changed several assumptions in CONTEXT.md and the roadmap. The biggest ones: (1) the hosted baseline of 60 min/run was measured on the **public** `ubuntu-latest` (4 vCPU / 16 GB); a private repo gets 2 vCPU / 8 GB, so a hosted fallback run will be slower and cost more than 60 min [CITED: docs.github.com/en/actions/reference/runners/github-hosted-runners]. (2) Path-based job splitting saves almost nothing safely: 22 of the last 52 commits are docs-only (already skipped), of the other 30 only about 2 touch no test-relevant path, and `ci_gates.py` has a hard executed-test floor (12,821) and skipped ceiling (0) plus a whole-suite coverage floor that a skipped group would trip. The self-hosted runner is the only real lever (PRV-02). (3) When a public repo is converted to private on Free, **environment protection rules and environment secrets are ignored and environments cannot be configured** [CITED: docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments]. So the `firmware-signing` key secret and (if they are environment secrets) the `DEPLOY_*` secrets cannot be removed or reached after the flip: every secret action must happen BEFORE the flip. (4) This session's `gh` token is **invalid** (`gh auth status`), yet API reads and CI log downloads work only because the repo is public and anonymous reads succeed. After the flip, sessions need a real token with repo scope; this is the top post-switch risk.

Recommended shape: `ci.yml` loses the `deploy` job and runs on a self-hosted ephemeral Linux runner (Linux VM on the Mac, runner inside the VM, JIT registration from the Mac host) selected through a repo variable so hosted is the fallback. A new `deploy.yml` (`workflow_dispatch` only, no environment, hosted runner, main-only, tip-of-main check, "CI green for this SHA" check) replaces the deploy job. `firmware-release.yml` keeps guard + build (hosted, no secrets), uploads the unsigned images as an artifact and stops; a Mac script downloads, verifies, signs with the local key in the pinned container, verifies against the committed pubkey, generates the manifest and publishes the GitHub Release with the exact same asset names, then (optionally, after a prompt) dispatches `deploy.yml`. A repeatable stdlib scan script plus a written `70-INVENTORY.md` cover PRV-03.

**Primary recommendation:** Build in this order: (1) `deploy.yml` + repoint tests + proof deploy; (2) Mac signing script + CI build-only release + harmless test release `fw-v1.2.2`; (3) runner on the Mac + `CI_RUNS_ON` variable + measurements; (4) inventory script and document with owner decisions; (5) retire `firmware-signing` environment secret (owner act, before the flip); (6) rewrite docs; (7) owner flips visibility; (8) post-switch checklist.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Stay on the GitHub Free plan with the repository on the owner's personal account. No Team plan, no organisation. Reason: the Team plan would not fix the CI minutes (see D-05), and the docs conflict on whether environment approvals work in private repositories on Team (docs say yes, the pricing page says public only), so nothing may rely on it.
- **D-02:** The owner asked whether an organisation can be personal: yes, a one-member organisation is free to create and Team would cost $4 per month for one seat. Recorded as the fallback if the Free-plan design proves unworkable; not built in this phase.
- **D-03:** The production deploy becomes a workflow the owner starts by hand (`workflow_dispatch`); a merge to `main` no longer deploys. Confirmed by the owner. It must not depend on environment reviewers. Proof on a test run is required before the visibility changes (criterion 1).
- **D-04:** `deploy` must also be reachable from the firmware release path (today `firmware-release.yml` ends with `gh workflow run ci.yml --ref main` after publishing a release). The planner decides how the owner-started deploy imports a new release, keeping the import idempotent and the stale-main check of the current deploy job.
- **D-05:** The hosted CI cannot fit the Free plan. Measured on run 45337958006 (job times rounded up per minute): 60 billable minutes per full run (static 1, core shards 7+6, browser shards 10+7+9+10+9, aggregate 1), against about 2,000 included Linux minutes per month ($12 of compute at $0.006). Recent rate: 30 runs in 36 hours, so 18,000 to 36,000 minutes per month, 8 to 18 times the quota; overage would be roughly $100 to $200 per month. Team ($18, about 3,000 minutes) would not change this.
- **D-06:** CI runs on a self-hosted runner on the owner's Mac, never on the production server. The runner must be secured (private repository, no fork pull requests, Linux container or ephemeral runs, no production secrets on it, branches pushed by sessions run code on the Mac so the isolation must be stated). GitHub's current docs say self-hosted runners are free; the announced $0.002 per minute charge (from 1 March 2026) is postponed with no date, so it is a watched risk (about $36 to $72 per month at the current rate). Where exactly the runner lives and how the CI behaves when the Mac is off are for research and planning.
- **D-07:** Reduced CI: keep the existing docs-only skip and add path-based job splitting so heavy jobs do not run when no code changed. No test is skipped for a code change, and the browser tests run on every change to code. Measured minutes per run and the monthly total are recorded before and after.
- **D-08:** Option C: firmware is signed on the owner's Mac so the private key never leaves it. No signing key in a GitHub secret. The release path of the live frame and its signed image stay unchanged, and the server imports a signed test release. A harmless test release is made first. The current `firmware-signing` environment is retired only after the new path is proven, and only with the owner's explicit confirmation (no secret is rotated or deleted by a session).
- **D-09:** A written inventory of what has been public is made (secrets in the tree and in git history, personal data, commercial planning notes in `.planning/`); copies already taken stay public. Anything sensitive is handled with the owner (rotated or recorded with his decision). Never print a secret.
- **D-10:** Order is fixed: pipeline changes, then proof of criteria 1 to 3, then the owner flips the visibility himself. After the switch, check that sessions can push branches and open draft pull requests and read CI logs, that the nightly backup, the `gh release download` in the deploy, Dependabot and a firmware release still work.
- **D-11:** On a private Free repository there is no branch protection, no rulesets and no environments, and secret scanning is public-only. The plan must not assume any of them, and the audit in Phase 66 sees the final setup.

### Claude's Discretion
Exact workflow structure, job and path-filter names, how the runner is installed and updated, the signing script's interface on the Mac, the shape of the inventory document.

### Deferred Ideas (OUT OF SCOPE)
- Team plan with a one-member organisation, if the Free design proves unworkable (D-02).
- Moving the runner to a second small server if the Mac proves unreliable.

Not in this phase: another git platform, splitting the repository, legal review of the licences (SEED-015).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PRV-01 | Repo private; production deploy and firmware signing under the owner's explicit control on Free, proven before the flip | Sections "Manual deploy", "Signing on the Mac", "Server-side deploy-key restriction"; proof procedure; environment-ignored-after-flip fact forces pre-flip secret handling |
| PRV-02 | CI fits private limits, measured minutes before/after, no test skipped, browser tests on every code change | Sections "Self-hosted runner", "Reduced CI by paths" (path split is near-worthless and gate-hostile; runner is the lever); measurement method |
| PRV-03 | What was public is inventoried, sensitive items handled, everything keeps working after the switch | Sections "Inventory", "Post-switch checklist" (token finding, Dependabot, backup, release download) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs and commit messages in English; companion UI strings stay bilingual (not touched here).
- Comments say what and why; **no plan/ticket/decision/review/phase IDs in comments** (enforced by `scripts/check_comment_history.py check` in CI over the whole tracked tree, including workflow YAML comments and shell scripts). Workflow comments must therefore not say "D-03", "Phase 70" or "PRV-01".
- Stack: Python 3.14 stdlib + Pillow + requests for server code; new scripts must be stdlib only. ruff, mypy (module list in `pyproject.toml` `[tool.mypy]`), function-size gate (max 80 lines over `server` and `stub-server` only), shellcheck over `deploy/*.sh` only (extend the `find` if new shell scripts live elsewhere).
- Tests: pytest, behaviour-over-source rule (`companion/test_suite_guards.py`: tests assert served HTML/CSS/JS or a browser, never source text or `.planning/`). Several existing `deploy/tests` already read workflow and doc text; follow their style but do not add new source-text assertions about `.planning/`.
- Action pins by SHA; secrets only through `env:`, never `${{ secrets.* }}` inside `run:` (`deploy/tests/test_ci_secrets.py` scans every workflow file).
- GSD workflow: work enters through `/gsd-*` commands; this document is research only.
- Owner wants short French answers; written artefacts in English.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Gate on who may deploy | GitHub (workflow_dispatch + write access) | Server (SSH forced command, optional signed ticket) | Free has no environments; GitHub secrets are readable from any branch workflow, so the server is the only place that can enforce the owner's control |
| Production deploy execution | Hosted runner (`ubuntu-latest`, minutes) | VPS (`activate.sh`) | A few minutes per manual deploy; must work when the Mac is off |
| CI test execution | Self-hosted Linux runner (Mac VM) | Hosted fallback via repo variable | Only way to stay inside 2,000 min/month |
| Firmware build | Hosted runner (unchanged environment) or Mac VM | - | Build needs no secret; keep release build hosted so the bytes come from a clean GitHub VM |
| Firmware signing | Owner's Mac (key never leaves) | - | D-08 |
| Release publication | Owner's Mac (`gh release create` with owner's credentials) | - | Same asset names so `scripts/fw_release_assets.py` and the server import keep working |
| Firmware import into registry | VPS (`activate.sh` -> `firmware_cli import-dir`) | - | Unchanged |
| Exposure inventory | Owner's machine (full clone, `--mirror`) | Script in repo | This sandbox clone is shallow (52 commits), so history cannot be scanned here |

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| GitHub Actions runner (`actions/runner`, linux-arm64 or linux-x64 tarball) | latest at install; JIT runners self-update | Self-hosted CI runner inside a Linux VM on the Mac | Official; supports `--ephemeral` and JIT config [CITED: docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions] |
| Existing pinned actions (`actions/checkout` 3d3c42e5.. v7.0.1, `setup-python` 6d4fd22b.. v7.1.0, `upload/download-artifact`, `cache`, `webfactory/ssh-agent`) | as pinned in repo | Reuse in `deploy.yml`/`ci.yml` | Already SHA-pinned and reviewed; add no new third-party action |
| `espsecure.py` in `espressif/idf@sha256:55ab243e...2d` (digest used today in firmware-release.yml) | ESP-IDF 5.3.1 | Sign and verify on the Mac | Same bits as today's CI signing |
| `gh` CLI | current | Release publish, artifact download, dispatch | Already used |
| Python stdlib | 3.14 | New scripts: `scripts/ci_changes.py` (only if split kept), `scripts/fw_publish_signed.py`, `scripts/exposure_scan.py` | Project rule: stdlib only |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| Lima/Colima (or Tart, OrbStack machine) Linux VM on the Mac | Isolation for the runner; has its own dockerd so `firmware/build.sh` bind mounts work | Recommended runner host. Disable host folder mounts (Lima mounts `$HOME` by default; OrbStack machines mount the Mac filesystem by default) |
| gitleaks (brew, owner's Mac) | Optional second-opinion history scan with `--redact` | Owner's machine only; tag `[ASSUMED]` until the owner installs and checks `gitleaks --help` for the installed version (flag set changed between 8.16 and 8.26: `--redact` became a percentage) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Runner in a Linux VM | Runner in a Docker container (myoung34 image etc.) | `firmware/build.sh` runs `docker run -v "$SCRIPT_DIR:/project"`; from a container runner this needs a mounted socket and host-path mapping, and the socket is root on the VM. Third-party image adds supply-chain surface. Rejected for firmware builds |
| Linux VM | Native macOS runner | Tests need Linux (`systemd-analyze security`, shellcheck, apt `playwright install --with-deps`, docker for firmware) and PR code would run directly as the owner's macOS user. Rejected |
| Persistent runner | Ephemeral JIT runner | GitHub: "there is no way to guarantee that a self-hosted runner only runs one job"; JIT runners "perform at most one job" but re-used hardware still risks leakage, so also reset the VM workspace [CITED: docs.github.com/en/actions/reference/security/secure-use] |
| Path-split CI | Self-hosted runner only | See "Reduced CI by paths" |

**Installation:** No new Python or npm packages are recommended; slopcheck was therefore not needed. The runner is the official `actions/runner` release tarball (verify its published SHA-256 from the release page at install time).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| (none new) | - | - | - | - | not run: no package is installed by this phase | n/a |
| gitleaks (optional, brew, owner Mac) | Homebrew | multi-year | high | github.com/gitleaks/gitleaks | not run | `[ASSUMED]`; owner verifies the formula source before installing |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
Hash-locked `server/requirements*.txt` stay unchanged. Verified: the existing lock (`x86_64-manylinux_2_28` per `scripts/lock-deps.sh`) also carries hashes for **linux aarch64** wheels: `pip download --only-binary=:all: --platform manylinux_2_28_aarch64 --python-version 3.14 --require-hashes -r server/requirements-dev.txt` succeeded for all packages [VERIFIED: run in this session]. So an Apple-Silicon Linux VM can install the lock unchanged.

## Architecture Patterns

### System Architecture Diagram

```
 session / owner push branch ──► PR (draft) ──► ci.yml (pull_request) ─┐
 merge to main ────────────────► ci.yml (push main)                    │
                                                                       ▼
                         runs-on: fromJSON(vars.CI_RUNS_ON || '"ubuntu-latest"')
                                       │                       │
                      var = ["self-hosted","skypane-ci"]   var unset / "ubuntu-latest"
                                       ▼                       ▼
        Mac host launchd loop ─► JIT config (admin PAT in Keychain, never in VM)
              └► Linux VM (no host mounts) ─► run.sh --jitconfig (1 job) ─► wipe _work, repeat
                                       │
        static ─┬─ tests-core 0..1 ─┬─ tests-browser 0..4 ──► `test` aggregate "Lint, test, coverage, attribution"

 owner (gh workflow run deploy.yml --ref main -f confirm_sha=<7>) ─► deploy.yml (hosted)
     if ref != main ─► fail │ tip-of-main != GITHUB_SHA ─► fail │ CI check-run for SHA not success ─► fail
     └► gh release list/download (github.token, contents: read) ─► deploy.sh ─ssh (restricted key)─► VPS activate.sh
                                                                          └► firmware_cli import-dir (idempotent)

 tag fw-vX.Y.Z ─► firmware-release.yml: guard (tag shape, on main) ─► build both boards (hosted, no secrets)
     └► upload-artifact fw-unsigned-<tag> (+ SHA256SUMS)         [workflow ends; no key, no environment]
 owner's Mac: scripts/fw_publish_signed.py <tag>
     gh run download ─► check run/sha/tag provenance ─► verify SHA256SUMS ─► espsecure sign (pinned digest, --network none)
     ─► verify vs committed pubkey ─► fw_release_manifest.py check/generate ─► gh release create (same asset names)
     ─► prompt ─► gh workflow run deploy.yml --ref main
```

### Recommended Project Structure
```
.github/workflows/ci.yml                # static, tests-core, tests-browser, test; no deploy job
.github/workflows/deploy.yml            # new: workflow_dispatch only
.github/workflows/firmware-release.yml  # guard + build + upload-artifact only
scripts/fw_publish_signed.py            # new: Mac-side verify/sign/publish (stdlib, argument lists to subprocess)
scripts/exposure_scan.py                # new: tree + history scan, reports file/commit/type only
deploy/deploy_gate.py (+ installer)     # optional hardening, mirrors deploy/backup/backup_gate.py
deploy/runner/                          # runner install notes + launcher script for the Mac (not run in CI)
.planning/workstreams/v1-2/phases/70-.../70-INVENTORY.md
```

### Pattern 1: Manual deploy workflow (owner-started, no environment)
**What:** a new `deploy.yml` whose only trigger is `workflow_dispatch`, with no `environment:` key. Moves the current `deploy` job and its three steps verbatim (host key via `env:`, `webfactory/ssh-agent`, "Download firmware releases" step, `deploy.sh`).
**Must-have guards (all fail loudly, never green-skip):**
1. `if: github.ref == 'refs/heads/main'` at job level, because `workflow_dispatch` can target any branch and a branch's own copy of the workflow file would run [CITED: GitHub docs: dispatch runs the workflow file at the selected ref]. Repeat as a first step (`test "$GITHUB_REF" = refs/heads/main`) so it also shows in the log.
2. Tip-of-main equality: dispatch pins `GITHUB_SHA` at the chosen ref's tip at dispatch time; keep the `git ls-remote origin refs/heads/main` comparison from today's step, simplified to strict equality (no "shipped files identical" escape: a manual run is deliberate). Keep the `server stub-server companion adsb-test/runway3.json deploy firmware/signing/skypane-signing-pubkey.pem` path list only if you keep the tolerance.
3. A required input such as `confirm_sha` that must equal the first 7 characters of the tip of main. This is an anti-accident control only; it is NOT an access control (anyone who can dispatch can type it).
4. "CI green for this exact SHA": the deploy can no longer `needs: test`. Add a step that reads the check run named `Lint, test, coverage, attribution` for `$GITHUB_SHA` (`gh api repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA/check-runs`) and fails unless its conclusion is `success`; needs `permissions: checks: read` (plus `contents: read`). Because merges are squash, `main`'s tip SHA has its own push-to-main CI run, so the check exists whenever the push run was not docs-only skipped; a docs-only tip has no check run. Handle that by choosing the check-run lookup commit as the latest `main` commit that ran CI, or fail with a clear message (owner decision: allow an input `ci_sha` defaulting to the tip). Do not silently skip.
5. `concurrency: group: production-deploy, cancel-in-progress: false` unchanged. `timeout-minutes: 30` unchanged.
6. Runner: `ubuntu-latest` (hosted). A deploy is a few minutes (the last measured deploy job rounds to about 1-3 min), well inside the quota, and it must work when the Mac is off.

**Why a separate file:** a dispatch of `ci.yml` would rerun the whole 60-minute suite just to reach the deploy job, and `needs: test` forces that. It also removes the "push or dispatch on main" condition.

**Import of a new release (D-04):** no change to the import. `deploy.sh` ships `firmware-releases/` and `activate.sh` runs idempotent `firmware_cli import-dir`. The only change is the trigger: the Mac publish script ends by printing, and after an explicit `y` running, `gh workflow run deploy.yml --ref main -f confirm_sha=<tip7>`. A firmware-only deploy re-ships the unchanged tip of main; `deploy/tests/test_activate.py::test_same_sha_redeploy_imports_freshly_streamed_firmware` already proves a same-SHA redeploy imports freshly streamed firmware.

### Pattern 2: Server-side restriction of the deploy key (defence in depth)
**Fact base:** repo secrets are readable by "any user with write access" and by workflows on any branch/PR from a same-repo branch [CITED: docs.github.com/en/actions/reference/security/secure-use]. The deploy SSH target is `ubuntu@` with passwordless sudo (`deploy/deploy.sh` header), i.e. root-equivalent. A malicious or prompt-injected session branch that adds a workflow can exfiltrate `DEPLOY_SSH_PRIVATE_KEY`. No GitHub-side control exists on Free, so the control must be on the VPS.

Tiers (planner and owner choose; the baseline is Tier 1):
- **Tier 0 (mandatory, trivial):** a dedicated deploy key pair used only for CI, separate from the owner's login key; revocable by deleting one `authorized_keys` line. Document rotation.
- **Tier 1 (recommended):** `authorized_keys` line `restrict,command="/usr/bin/python3 /usr/local/lib/skypane/deploy_gate.py"` for the deploy key, same pattern as `deploy/backup/backup_gate.py` + `deploy/backup/install-backup-key.sh` (exact-match verbs, no shell, `SSH_ORIGINAL_COMMAND` treated as untrusted, with its own pytest like `deploy/tests/test_backup_gate.py`). Verbs map to what `deploy.sh` does today: `put-code <sha>` (tar on stdin into `/opt/skypane/releases/.incoming-<sha>`), `put-firmware <sha>`, `activate <sha>`; sha validated `^[0-9a-f]{40}$`. `deploy.sh` then needs a "gate mode" (it currently sends free-form `sudo install/rm/tar` and `sudo bash .../activate.sh` strings), and `deploy/tests/test_deploy.py` (fake ssh) must be extended. The deploy login user needs no general sudo, only a narrow sudoers rule for the gate.
- **Tier 2 (the only one that stops malicious code):** Tier 1 still lets any holder of the key ship arbitrary code (the tree's own `activate.sh` runs as root, and the services read `skypane.env`). To make "secrets readable from any branch" harmless, require an owner-made, owner-signed ticket: on the Mac, `ssh-keygen -Y sign -n skypane-deploy` over `sha=<40hex> manifest=<sha256 of a sorted per-file sha256 list of the shipped tree>`; the ticket is passed as a `workflow_dispatch` input; the gate recomputes the manifest over the received tree and verifies against an `allowed_signers` file root-owned on the VPS. Hash the extracted files, not the tar bytes (tar bytes depend on git version). Medium effort; it is the real answer to criterion 1's "explicit act of the owner". Flag to the owner as an option; Phase 66 may take it.
- **Break-glass, no GitHub secret at all:** `deploy/deploy.sh` already runs from a laptop. The owner can deploy from the Mac with a locally held key. Not a replacement for D-03; mention in docs.

`[ASSUMED]` whether the session integration token can dispatch workflows (needs Actions: write). If it can, `workflow_dispatch` is not "the owner alone". Verify post-flip by dispatching `firmware-chain-check.yml` (read-only) from a session, never `deploy.yml`.

### Pattern 3: CI on a self-hosted ephemeral runner with hosted fallback
- `runs-on: ${{ fromJSON(vars.CI_RUNS_ON || '"ubuntu-latest"') }}` in `static`, `tests-core`, `tests-browser`, `test`. Variable unset or `"ubuntu-latest"` = hosted; `["self-hosted","skypane-ci"]` = Mac. `${{ runner.environment }}` (`github-hosted` | `self-hosted`) lets steps branch.
- **Mac off:** a job whose labels match no online runner stays queued; docs say a job queued over 24 hours is failed [CITED: docs.github.com/en/actions/reference/runners/self-hosted-runners]. There is no automatic fallback; the owner flips `CI_RUNS_ON` (document the one-line `gh variable set` and what a hosted run costs, at 2 vCPU, unmeasured but more than 60 min).
- **Registration:** a host-side launchd KeepAlive loop on the Mac generates a JIT config (`POST /repos/{owner}/{repo}/actions/runners/generate-jitconfig`, labels `self-hosted,skypane-ci`) with an admin-scoped fine-grained PAT held in the macOS Keychain and passes it into the VM (`run.sh --jitconfig`). The PAT never enters the VM (the VM runs branch code). One loop per parallel runner (3-4 loops; matrix has 8 jobs; a 8+-core Mac can also just run fewer, longer shards). [CITED: docs.github.com/en/rest/actions/self-hosted-runners] for the endpoint; the launcher script itself is `[ASSUMED]` design.
- **Isolation statement for the docs (D-06):** private repo, personal account with no collaborators, forks off; sessions' branches and Dependabot PRs execute on the Mac VM; the VM has no host mounts, no Docker socket exposed to macOS, no production secret, no deploy key, no signing key; the repo `GITHUB_TOKEN` is `contents: read` (jobs keep `permissions: contents: read`); outbound LAN access from the VM should be blocked where practical (Lima `--network` user-mode). Residual: a malicious branch can burn Mac CPU and reach the internet.
- **Playwright/Python on the VM:** `actions/setup-python` can install 3.14 on linux arm64 for Ubuntu 22.04/24.04/26.04 and darwin arm64 [VERIFIED: actions/python-versions versions-manifest.json, 3.14.10 lists `arm64` linux 22.04, 24.04, 26.04, fetched this session]. Alternative: use the Ubuntu 26.04 VM's distro `python3.14` (same as production). Bake the Playwright OS packages and the Chromium headless shell into the VM image; then skip the apt-cache and `playwright install --with-deps` steps with `if: runner.environment == 'github-hosted'`. Playwright 1.64.1 is pinned in the lock; Linux arm64 Chromium support is `[ASSUMED]`, prove with one browser shard before committing.
- **Architecture risk (owner question):** the lock script targets `x86_64-manylinux_2_28`; the arm64 hashes exist (verified above) but production is x86_64. Tests passing on arm64 do not prove the x86_64 wheels; hosted CI used x86_64. Accept and record, or run an amd64 VM/Rosetta (slower).
- **Cost:** self-hosted usage is free today ("Self-hosted runners" listed as free usage that does not reduce included compute) [CITED: docs.github.com/en/billing/concepts/product-billing/github-actions]; the $0.002/min charge was postponed with no new date ("postponing the announced billing change ... to take time to re-evaluate") [CITED: github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions]. Watched risk; record the date checked. Free includes $12 of compute (about 2,000 standard Linux minutes), 500 MB artifact storage, 10 GB cache [CITED: same billing page]. Dependabot on standard GitHub-hosted runners is free [CITED: same page].
- **Hosted minutes that remain** (estimates from real runs): `firmware-chain-check.yml` daily, about 1 min x 30; `deploy.yml` about 2-3 min per manual deploy; `firmware-release.yml` hosted build about 5 billable min (guard 1 + build 4: job times 10 s and 217 s); `firmware.yml` is NOT in the 60-minute baseline and costs about 6 billable min per run (15 s + 108 s + 126 s -> 1+2+3) at roughly 5 runs/day (100 runs in 22 days) = about 900 min/month, about 45% of the quota by itself. Move `firmware.yml` to the VM runner too (the VM has docker), or keep hosted with the existing path filter and measure.

### Pattern 4: Mac-side signing (option C1, build in CI, sign on the Mac)
**What exists today** (`.github/workflows/firmware-release.yml`, job `release`, environment `firmware-signing`): checkout full history; `SKYPANE_RELEASE_TAG=$tag ./firmware/build.sh` (ee02); `check_production_config.sh built firmware/build-ee02`; `check_log_contract.sh`; second-board build (`SKYPANE_BOARD=second`, `build-second`) and its config check; sign both `skypane.bin` -> `skypane-signed.bin` with `espsecure.py sign_data --version 2` in the digest-pinned container with `--network none` and the key from a 0600 temp file; shred key; `espsecure.py verify_signature --version 2` against `firmware/signing/skypane-signing-pubkey.pem` for both; `scripts/fw_release_manifest.py --check-only` for ee02 (`xiao-ee02-13in3-spectra6`); manifest + notes (`release.json`, `notes.md`); check-only and manifest for `seeed-ee04-7in3-spectra6` -> `release-seeed-ee04-7in3-spectra6.json`; stage assets; `gh release create` with exactly: `skypane-<tag>.bin`, `release.json`, `bootloader-<tag>.bin`, `partition-table-<tag>.bin`, `ota_data_initial-<tag>.bin`, `skypane-seeed-ee04-7in3-spectra6-<tag>.bin`, `release-seeed-ee04-7in3-spectra6.json`, `--title <tag> --notes-file notes.md --verify-tag`; then `gh workflow run ci.yml --ref main`.
**Consumers that pin those names:** `scripts/fw_release_assets.py` (legacy pair `skypane-<tag>.bin` + `release.json`; typed pair `release-<key>.json` + `skypane-<key>-<tag>.bin`), the `Download firmware releases` step (tag regex `^fw-v(0|[1-9][0-9]{0,3})\.(0|...)\.(0|...)$`), `server.firmware_cli import-dir`.

**New split:**
- `firmware-release.yml`: keep `guard` (unchanged); keep build steps and the two `check_production_config.sh built` + `check_log_contract.sh` checks; delete signing, shred, verify, manifest, stage, publish and dispatch steps and `environment:`, `contents: write`, `actions: write`; add a step that writes `SHA256SUMS` for the five files the Mac needs (unsigned `skypane.bin` x2, bootloader, partition-table, ota_data_initial) and `actions/upload-artifact` (`fw-unsigned-<tag>`, `retention-days: 14`, files are not dotfiles). Job permission `contents: read` only. Test pinned today: `test_firmware_release_passes_signing_key_through_env` must be replaced.
- `scripts/fw_publish_signed.py <tag> [--dry-run] [--state-dir DIR]` on the Mac, stdlib, argument lists only. Steps: refuse unless tag shape matches; `git fetch --tags origin`, tag commit is an ancestor of `origin/main`; find the successful `firmware-release.yml` run for that tag (`gh run list --workflow firmware-release.yml --json headSha,conclusion,headBranch,databaseId`), require `headSha == tag commit`; `gh run download <id> -n fw-unsigned-<tag>`; recompute SHA256SUMS; decrypt the key to a RAM-backed path only for the sign step (key custody per `firmware/SIGNING.md` step 4, age/gpg backup), sign both boards in the same pinned container with `--network none`; shred; verify with the committed pubkey; run `scripts/fw_release_manifest.py --check-only` and generation exactly as today (it needs a full checkout at the tag so `commit`, notes and `released_at` come from git); stage the seven names; `--dry-run` stops here and additionally runs `server.firmware_cli import-dir` into a scratch state directory; real mode runs `gh release create ... --verify-tag`; ends with the optional deploy dispatch prompt.
- Keep `docker run ... espressif/idf@sha256:55ab243e...` signing identical so signature blocks are produced by the same code; RSA-PSS signatures are randomised, so two signings of the same bytes differ and that is expected.

**Reproducibility:** `firmware/sdkconfig*.defaults` and `build.sh` contain no `REPRODUCIBLE_BUILD` setting (grep found none), so a rebuild embeds a new timestamp and differs bytewise. Therefore the Mac must sign the exact bytes CI built (handoff), not rebuild. This is why C1 (artifact handoff) is lower risk than C2 (build and sign locally).
**Option C2 (fallback):** build on the Mac in `espressif/idf:v5.3.1` via `firmware/build.sh` (needs the repo at the tag, clean tree) then sign. Simpler trust story but the build host may be arm64 under emulation: whether `espressif/idf` publishes an arm64 manifest could not be checked (Docker Hub anonymous rate limit hit in this session) `[ASSUMED: unknown]`.
**Trust note:** the Mac signs whatever bytes CI produced. Provenance checks above (run is from this repo's workflow on the tag commit, tag is on `main`, SHA256SUMS match) plus the owner reading `notes.md` are the control; document that a malicious branch cannot produce a release because the guard rejects off-main tags and the Mac script re-checks.

**Harmless test release:** nothing reaches the frame until an operator schedules a release in the companion Update page (`deploy/README.md` "Firmware releases (OTA)" item 5; `server/firmware_registry.py` offers only a scheduled release, `compute_offer`). Constraints: `_apply_build_gate` refuses any new non-bench release whose build number is not strictly above the newest published one, and `/opt/skypane/state/firmware/` is never pruned. So a test release cannot be a throwaway low tag; it permanently occupies the next version. Procedure: (1) rehearse with `--dry-run` (full verification + scratch `import-dir`, nothing published); (2) publish the next real patch tag (`fw-v1.2.2`, the first free number after `fw-v1.2.1`) built from the Phase-70 merge commit, so it is a normal, correctly signed, functionally unchanged release; (3) manual `deploy.yml` run imports it; (4) confirm in the companion Update page that it shows as "Available" with no schedule, and that `server.firmware_cli list` shows both types. Owner confirms the number before tagging. The second-board typed pair is only imported when `SKYPANE_ENABLE_SECOND_HARDWARE=1` is set in the VPS env; do not change that switch.

### Pattern 5: Reduced CI by paths (decision: do not split test groups)
Measured/derived facts:
- Current filters (`ci.yml`): workflow-level `paths` on push to main and pull_request: `'**'`, `!**/*.md`, `!.planning/**`, `!.claude/**`, `!LICENSE`, re-including `server/assets/**/VENDOR.md` and `deploy/README.md`.
- Last 52 commits (local shallow clone): 22 docs-only (already skipped), 30 code. Of the 30: companion 14+, deploy-only 3, hardware-only 2, rest mixed. Test files live in `server stub-server companion test-support deploy hardware scripts` (pyproject `testpaths`). Test files reference `firmware/` (28 files), `adsb-test/` (28), `.github` (4), `docs` (1), `hardware` (2); `design-exploration/` is referenced by none. So the only provably inert code path is `design-exploration/**`; "firmware-only PRs skip tests" would be wrong (28 tests read firmware files).
- `scripts/ci_gates.py` fails when executed tests fall under 12,821 or skipped exceed 0, and `[tool.coverage.report] fail_under` is a whole-suite floor (`scripts/run-all-tests.sh`). Skipping any shard group makes the aggregate fail those gates unless they are made conditional, which weakens them. D-07 says no test skipped for a code change.
- Real numbers (run 45337958006 jobs fetched via API, seconds): static 35, core 385/351, browser 554/398/521/544/487, aggregate 32 -> billable 1 + 7 + 6 + 10 + 7 + 9 + 10 + 9 + 1 = 60 (matches D-05). Rate: last 100 CI runs span 2026-11-18 to 2026-11-24, 62 pull_request + 38 push, about 17 runs/day => about 500 runs/month x 60 = about 30,000 min/month plus firmware.yml.
**Recommendation:** keep the docs-only skip exactly as is; add `design-exploration/**` to the ignored list only if the owner wants it (tiny gain); do NOT build a `changes` job that skips shards. Savings come from the runner. If the planner still wants a `changes` job, it must (a) default to run-everything, (b) keep `test` reporting always, (c) accept `skipped` only for jobs the changes output declares skipped, (d) adjust the shard-count and JUnit-floor and coverage-floor steps, and (e) be tested in `test-support/`. Record why it was judged not worth it.
**Double run:** PR run + push-to-main run per merge (62 vs 38 recent). On the Mac it is free; keep both (the push run is the post-merge proof and `deploy.yml`'s "CI green for this SHA" reads it). Skipping it needs a tree-hash lookup of a prior green run; not worth the risk.

### Anti-Patterns to Avoid
- Relying on `environment:` for anything (ignored on private Free). Remove `environment: production` and `environment: firmware-signing` from workflows before the flip.
- Leaving the `FW_SIGNING_KEY` secret or the `firmware-signing` environment in place "inert". After the flip it cannot be reached or deleted from the UI (docs: environments cannot be configured while private). Delete before the flip, after the new path is proven, with the owner's explicit confirmation.
- Assuming `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_SSH_TARGET` are repo-level. The workflow reads `secrets.*` under `environment: production`; if they were created as environment secrets they are ignored after the flip and absent for a no-environment job. The owner must run `gh secret list` and `gh secret list --env production` (this session's proxy blocks those endpoints) and recreate any environment-only secret as a repo secret before the proof run.
- Putting the admin PAT or any secret inside the runner VM.
- A `${{ secrets.* }}` in a `run:` (test_ci_secrets scans every workflow).
- Using `needs:` across workflows; use the check-run lookup.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Secret scanning of history | A new regex engine | `scripts/exposure_scan.py` (small, stdlib, labelled patterns, reports file/commit/type only) AND optionally gitleaks with `--redact` on the owner's machine | Pattern lists drift; gitleaks is maintained; the repo script gives a repeatable no-install baseline |
| RSA/Secure Boot V2 signing | Custom signing | `espsecure.py` in the pinned container | Exactly what the device verifies |
| Release asset selection | New name logic | `scripts/fw_release_assets.py` | Already allow-lists names; reuse unchanged |
| Release manifest/notes | Hand text | `scripts/fw_release_manifest.py` | Validates image vs hardware type and key modulus |
| Runner registration | Long-lived registration token inside the VM | JIT config per job | Single-use credential |
| Forced-command gate | rsync/rrsync allow-list | Pattern of `deploy/backup/backup_gate.py` | Self-auditable, already tested style |
| Deploy approval | Custom "approval" workflow tricks | `workflow_dispatch` + main-only guard + server-side gate | Environments unavailable |

**Key insight:** every control that depends on GitHub secrets being access-controlled fails on Free private; either remove the secret from GitHub (signing key) or enforce on the server (deploy key).

## Runtime State Inventory

(Rename/migration-adjacent: moving secrets and triggers.)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Published GitHub Releases `fw-v1.0.0` ... `fw-v1.2.1` (8 releases, 5-7 assets each); the VPS registry under `/opt/skypane/state/firmware/` already holds them | None for existing; new releases must keep asset names. Verified via API this session |
| Live service config | GitHub repo settings: environments `production`, `firmware-signing`; Dependabot enabled; Actions settings; repo variables (none yet: add `CI_RUNS_ON`) | Owner checks `gh secret list`, `gh secret list --env production`, `gh secret list --env firmware-signing`, `gh variable list` before changes. Create repo-level secrets for the deploy before the proof run. Delete the `firmware-signing` environment secret before the flip (owner act) |
| OS-registered state | Mac: launchd backup pull agent `com.skypane.backup-pull` (exists); new: runner launcher launchd agent(s) and Linux VM autostart | Document; keep the Mac awake (pmset/caffeinate) or accept queueing |
| Secrets/env vars | `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY`, `DEPLOY_SSH_TARGET` (deploy), `PRODUCTION_HOST` (chain check, repo-level read by `secrets.PRODUCTION_HOST`), `FW_SIGNING_KEY` (env `firmware-signing`) | Deploy secrets: confirm level, recreate at repo level if needed. `FW_SIGNING_KEY`: retire with owner confirmation; no session rotates or deletes anything. If a deploy-key gate is chosen, a new deploy key is created and the old one removed from `authorized_keys` by the owner |
| Build artifacts | None carrying an old name; `server/.venv` locks unchanged | None |

Nothing found for stored-data migration: the server data model is unchanged by this phase.

## Inventory of what has been public (PRV-03)

**Method (repeatable):** `scripts/exposure_scan.py` (new, stdlib) runs two modes. Tree mode: tracked files. History mode: stream `git log --all -p` and, for added lines only, classify by labelled pattern; output is a table of `type | file | commit(short) | count`, never the matching text. Run on the owner's machine against `git clone --mirror https://github.com/florianlepont/skypane` after `git fetch origin '+refs/pull/*:refs/pull/*'` so deleted PR branches and PR heads are scanned (this sandbox clone is shallow: `git rev-parse --is-shallow-repository` is true, 52 commits, so a full history scan is impossible here). Include binary-ish text (`--text`). Optional second opinion: gitleaks with `--redact`. A prototype of the patterns was run over the available 52-commit history (nothing printed but counts):
- PEM private key, AWS key, GitHub token, Slack token, `sk-` key, long bearer literal: 0 hits.
- "assigned secret-looking string" pattern: 4 files, 1 commit, all test files (`companion/test_config_page_04.py`, `server/test_calendar_rules.py`, `stub-server/test_fleet_cli.py`, `test-support/companion_render_snapshot.py`), likely fixtures; must be eyeballed by the owner (file + line numbers only).
- Non-noreply e-mail addresses: 37 files, 2 commits (tests, `COMPLIANCE.md`, several `.planning/` files and PNG renders). Needs a per-file owner decision (test fixtures vs real addresses).
- Public-looking IPv4 literals: 86 files (mostly `.planning/`); includes whatever the VPS address mentions are; owner decision: the VPS IP is already public on the internet via DNS, but SSH exposure details in `.planning/` are not.
Full-history numbers are unknown until the owner runs the mirror scan (LOW confidence on history).
- Tracked files whose names look sensitive but are not secrets: `deploy/skypane.env.example`, `firmware/main/enrol_secret.c|h` (code that reads the per-device enrol secret from NVS; the values are in device flash and on the VPS, not in git, to be confirmed by the scan), ISRG roots, `firmware/signing/skypane-signing-pubkey.pem` (public key, fine).
- **Personal data surfaces:** owner's full name in `firmware/SIGNING.md` (decision record) and README; the owner's GitHub login; location/home runway data (`adsb-test/runway3.json`, hardware logs); git author e-mails in commit metadata (cannot be rewritten for copies already taken); `SECURITY.md` and `CONTRIBUTING.md` text assuming public reporting.
- **Commercial planning notes in `.planning/`** (names/areas only; 1,508 tracked files, 71 MB): `.planning/seeds/SEED-015-business-plan-and-go-to-market-feasibility.md`; `.planning/research/` and `.planning/workstreams/v1-2/research/` (`SUMMARY`, `FEATURES`, `PITFALLS`, `STACK`, `ARCHITECTURE`); `.planning/notes/` (35 files, incl. an ops board and design brief); commercial keyword matches cluster in the Phase 68, 61, 62, 56, 64 and 69 directories and 6 seed files. Owner decides per area: leave (repo becomes private), or remove from the tree going forward. History keeps them; copies taken stay public.
- **Other public surfaces (checked via anonymous API this session):** stars 1, forks 0, watchers 1; 8 releases with assets (all signed images, manifests, bootloader/partition binaries); 451 Actions artifacts; 544 PRs and 1 issue-or-PR thread listing beyond PRs (issues API merges PRs; owner reviews the issue text); 1,769 workflow runs with public logs; `has_pages: false`, `has_wiki: false`, discussions off. Anything in logs (hostnames, paths) stays in anyone's cache; the signing public key and release images are public by design.
- **Implication of "copies already taken stay public":** the 1 stargazer, any clone, the Wayback/Software Heritage/search caches and the MIT-licensed history before 2026-09-23 (README: last MIT commit `efafc89`) remain usable under MIT forever. Making the repo private does not revoke that. Rewriting history (`git filter-repo`) would only affect the live repo and breaks every SHA the deploy, tags, and `fw-v*` releases depend on; recommend against, rotate instead.
- **Rotation candidates** to decide with the owner after the scan: anything in the "assigned secret" and e-mail hits proven real; the Auth0 tenant/client ids if any appear; the signing key does not need rotation (never in git; public key is public), unless the owner wants to rotate because it sat in a GitHub environment secret (rotation needs a transition release, `SIGNING.md` "Rotation").
Deliverable: `70-INVENTORY.md` with sections: method, findings table (type/path/commit/disposition), owner decision column, the "copies taken stay public" paragraph, and the repeat command.

## Common Pitfalls

### Pitfall 1: Secrets locked behind environments become unreachable
**What goes wrong:** after the flip, environment secrets are ignored and the environment cannot be edited.
**How to avoid:** do all secret/env work before the flip: repo-level deploy secrets created and proven; `firmware-signing` secret deleted (owner) after the Mac path is proven.
**Warning signs:** deploy job fails on empty `ssh-private-key` after the flip.

### Pitfall 2: Session tokens vs anonymous reads
**What goes wrong:** `gh auth status` in this sandbox says the `GH_TOKEN` is invalid, but `gh api` reads and `actions/runs/<id>/logs` work, because the repo is public. After the flip the same calls return 404.
**How to avoid:** before the flip the owner confirms the cloud-session GitHub integration has a valid token with repo (contents, pull requests) and Actions read scope; test with a session on a throwaway private repo or right after the flip with the checklist below. The session proxy also blocks `collaborators`, `hooks`, `environments`, `actions/secrets` and org-wide search (403 "not permitted through this proxy"), so sessions cannot inspect settings; the owner must.

### Pitfall 3: Hash lock vs runner architecture
**What goes wrong:** an arm64 VM installs from an x86_64-targeted lock. Verified OK for aarch64 manylinux_2_28 (see audit); would fail only for a wheel missing an aarch64 build in a future bump. `scripts/lock-deps.sh` comment says both production and CI are x86_64; update the comment when the runner changes.

### Pitfall 4: Coverage/JUnit floors with partial runs
**What goes wrong:** skipping shards trips `ci_gates.py` floors and `fail_under`. See Pattern 5.

### Pitfall 5: Aggregate check semantics
`test` uses `if: always()` and rejects any non-`success` need, so a skipped job fails it; keep that.

### Pitfall 6: Runner jobs using `sudo`
The browser job runs `sudo cp` into `/var/cache/apt/archives` and `playwright install --with-deps` (apt). On a baked VM image these steps are unnecessary; guard with `runner.environment` rather than deleting, so the hosted fallback still works.

### Pitfall 7: Firmware builds on the runner need dockerd in the same filesystem namespace
`firmware/build.sh` bind-mounts the workspace into `docker run`; keep the runner process and dockerd in the same VM (not container-in-container).

### Pitfall 8: Dependabot
Dependabot update jobs run on hosted standard runners for free; its PRs then trigger `ci.yml`, which now runs on the Mac. If "Dependabot on self-hosted runners" is enabled, update jobs need a runner labelled `dependabot` and queue forever without one; leave that setting off. Dependabot PR workflows get a read-only token and no repo secrets (CI uses none). Security updates (alerts) on private Free: availability of Dependabot alerts on private repos `[ASSUMED]` enabled by default; owner checks Settings -> Advanced Security.

### Pitfall 9: Comment guard on new text
`check_comment_history.py` rejects `D-xx`, `Phase NN`, `NN-NN-PLAN`, `.planning/` and ID prefixes in comments across the whole tracked tree. Do not write them in workflow comments, shell scripts or docstrings.

### Pitfall 10: Tests that read workflow text will break (see Validation Architecture)

## Code Examples

### Runner selection with hosted fallback
```yaml
# Source: GitHub Actions expressions docs (fromJSON, vars context); adapt per job
jobs:
  static:
    runs-on: ${{ fromJSON(vars.CI_RUNS_ON || '"ubuntu-latest"') }}
```
Set with `gh variable set CI_RUNS_ON --body '["self-hosted","skypane-ci"]'`; delete the variable to fall back to hosted.

### deploy.yml skeleton (trigger and guards only)
```yaml
# Source: derived from the current ci.yml deploy job
on:
  workflow_dispatch:
    inputs:
      confirm_sha:
        description: First 7 characters of the tip of main
        required: true
permissions:
  contents: read
  checks: read
jobs:
  deploy:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    concurrency: { group: production-deploy, cancel-in-progress: false }
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - name: Require the confirmation, the tip of main and a green CI run
        env:
          CONFIRM_SHA: ${{ inputs.confirm_sha }}
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          latest="$(git ls-remote origin refs/heads/main | cut -f1)"
          [ "$latest" = "$GITHUB_SHA" ] || { echo "::error::not the tip of main"; exit 1; }
          [ "${GITHUB_SHA:0:7}" = "$CONFIRM_SHA" ] || { echo "::error::confirmation does not match"; exit 1; }
          gh api "repos/$GITHUB_REPOSITORY/commits/$GITHUB_SHA/check-runs" \
            --jq '.check_runs[] | select(.name=="Lint, test, coverage, attribution") | .conclusion' \
            | grep -qx success
      # then the existing ssh-agent, host key, "Download firmware releases" and "Deploy" steps, unchanged
```

### Scan output shape (never prints values)
```
type=pem-private-key  file=path/to/file  commit=abc1234  lines=12
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Environment reviewer approves deploy | Manual `workflow_dispatch` + server gate | Needed because Free private has no environments | `ci.yml` deploy job removed |
| Key in `firmware-signing` environment secret | Key on the Mac only | This phase | `FW_SIGNING_KEY` retired |
| Hosted 4-vCPU public runner | Hosted 2-vCPU private, or free self-hosted | On flip | Hosted fallback slower |
| Self-hosted runner charge $0.002/min from 2026-03-01 | Postponed, no date | Changelog update | Watch risk (about $36-72/month at current rate if enacted) |

**Deprecated/outdated:** `deploy/README.md` text about the reviewer-gated `production` environment and "Run workflow on main, then approve" (also pinned by `test_docs.py` phrases, see below).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The owner's Mac is Apple Silicon and can run a Linux VM 24/7-ish | Runner | Intel Mac: x86_64 VM, simpler; sleeping Mac: queueing |
| A2 | Playwright 1.64.1 Chromium headless shell runs on linux arm64 | Runner | Browser shards fail; run an amd64 VM |
| A3 | `espressif/idf:v5.3.1` has a usable arm64 variant, or emulation works | C2 only | C2 impractical; C1 does not depend on it |
| A4 | Session integration token cannot dispatch workflows (no Actions: write) | Deploy control | Dispatch then not "owner alone"; rely on Tier 1/2 |
| A5 | `DEPLOY_*` secrets may be environment-level | Anti-patterns | Deploy fails post-flip if not recreated at repo level |
| A6 | Dependabot alerts/security updates are on and work on private Free | Pitfall 8 | Owner enables in settings |
| A7 | `gh release download` with `github.token` + `contents: read` works on a private repo | Deploy | Prove in the test deploy; fall back to a PAT secret is NOT preferred |
| A8 | `ubuntu-latest` private hosted runs the suite slower than the 60-min baseline | Summary | Only matters for the fallback; measure once |
| A9 | gitleaks `--redact` available with the installed version | Inventory | Use only the repo script |
| A10 | Runner must be kept updated (GitHub blocks very old runners); JIT runners update on start | Runner | Pin refresh in the launcher |

## Open Questions

1. **Mac model and uptime?** (architecture, VM vs always-on). Recommendation: ask; default to Apple Silicon Linux VM, Mac kept awake while sessions run.
2. **Where do the `DEPLOY_*` and `PRODUCTION_HOST` secrets live (repo vs environment)?** Only the owner can check. Blocks the proof run design.
3. **Does the owner want Tier 2 (signed deploy ticket) now or in Phase 66?** Affects scope of plan(s).
4. **CI-green rule for a docs-only tip of main** (no check run for that SHA): allow `ci_sha` input or require the owner to wait? Recommendation: input `ci_sha` defaulting to the tip, failing clearly if absent.
5. **Which tag number is the test release?** Recommend `fw-v1.2.2`; owner confirms because it is permanent.
6. **Does the session GitHub integration keep working on private repos, and with what scopes?** Unverifiable here.
7. **Should `firmware.yml` (about 900 hosted min/month) move to the VM runner?** Recommend yes.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Owner's Mac, Linux VM tooling (Lima/Colima/Tart/OrbStack) | Runner, signing | not probed (outside sandbox) | - | Hosted via `CI_RUNS_ON` |
| docker (this sandbox) | n/a | present at /usr/bin/docker, Docker Hub anonymous pull limit hit | - | not needed by research |
| gh CLI (this sandbox) | API reads | yes, token invalid (anonymous reads only) | - | owner's machine |
| shellcheck, systemd-analyze (hosted/VM) | static job | hosted yes; VM must install | - | install in VM image |
| gitleaks | optional scan | no | - | `scripts/exposure_scan.py` |
| ruff | lint | yes (`/root/.local/bin/ruff`) | - | - |

**Missing dependencies with no fallback:** none for the plan; Mac-side items are verified at execution by the owner.
**Missing with fallback:** shallow clone here; run the history scan on the owner's full mirror clone.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 + xdist + cov + pytest-playwright 0.10.0 (locked), shell tests for firmware |
| Config file | `/home/user/skypane/pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.report] fail_under`) |
| Quick run command | `server/.venv/bin/python -m pytest deploy/tests -q` |
| Full suite command | `./scripts/run-all-tests.sh` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PRV-01 | deploy workflow has only `workflow_dispatch`, no `environment`, secrets only via `env:`; host key/target through env | text scan (existing style) | `pytest deploy/tests/test_ci_secrets.py -q` (update to read `deploy.yml`) | exists, must be repointed |
| PRV-01 | "Download firmware releases" step still behaves with a fake `gh` | behaviour | `pytest deploy/tests/test_release_assets.py -q` (change `_CI_YML` to `deploy.yml`) | exists, repoint |
| PRV-01 | `ci.yml` shellcheck step still present | text | `pytest deploy/tests/test_install_backup_key.py::test_ci_yml_shellchecks_deploy_scripts -q` | exists |
| PRV-01 | Mac publish script: tag/run/sha provenance, SHA256SUMS mismatch refused, off-main tag refused, exact seven asset names, dry-run publishes nothing | unit, fake `gh`/`docker`/`git` shims (pattern of `test_release_assets.py`) | `pytest deploy/tests/test_fw_publish_signed.py -q` (or `scripts/test_fw_publish_signed.py`) | Wave 0 |
| PRV-01 | A signed image passes `fw_release_manifest.py --check-only` and the typed asset selector | existing | `pytest deploy/tests/test_release_manifest.py deploy/tests/test_release_assets.py -q` | exists |
| PRV-01 | Deploy gate verbs and rejections (if Tier 1) | unit | `pytest deploy/tests/test_deploy_gate.py -q` | Wave 0 (only if Tier 1 chosen) |
| PRV-01 | Gate end-to-end | integration | proof run: owner dispatches `deploy.yml` from main (success), from another branch (fails the guard), wrong `confirm_sha` (fails) | manual |
| PRV-02 | CI aggregate unchanged semantics; shard counts consistent | existing | `server/.venv/bin/python scripts/ci_shards.py check --browser-shards 5 --core-shards 2` | exists |
| PRV-02 | Measured minutes before/after recorded | manual measurement | `scripts/ci_run_timing.py jobs <run-id>` on one Mac run and one hosted-private run | exists (script) |
| PRV-02 | Hosted fallback works | manual | set `CI_RUNS_ON` unset, push a branch, run completes | manual |
| PRV-03 | Scan script classifies fixtures correctly and never prints a matching value | unit | `pytest scripts/test_exposure_scan.py -q` (synthetic strings built at test time, no real-looking secret committed) | Wave 0 |
| PRV-03 | Post-switch checklist | manual | items below | manual |
| must-not-break | golden hashes, freeze, signed path | existing | `pytest stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py -q`; `./scripts/run-all-tests.sh` | exist |

### Sampling Rate
- **Per task commit:** the touched test files plus `server/.venv/bin/ruff check .`, `python scripts/check_comment_history.py check`, `python scripts/check_function_size.py check --max 80 server stub-server`, `find deploy -name '*.sh' -print0 | xargs -0 shellcheck` (if shellcheck present), `mypy` if modules added to `pyproject.toml` list.
- **Per wave merge:** `./scripts/run-all-tests.sh`.
- **Phase gate:** full suite green on CI, plus the manual proofs (deploy from main/non-main, test release, runner runs, fallback), before the owner flips.

### Wave 0 Gaps
- [ ] `deploy/tests/test_fw_publish_signed.py` - covers Mac publish script
- [ ] `scripts/test_exposure_scan.py` - covers scan script
- [ ] `deploy/tests/test_deploy_gate.py` - only if Tier 1
- [ ] Repoint `deploy/tests/test_ci_secrets.py` (deploy step names, `DEPLOY_*` asserts now in `deploy.yml`; `test_firmware_release_passes_signing_key_through_env` removed or inverted: assert no `FW_SIGNING_KEY` in any workflow) and `deploy/tests/test_release_assets.py` (`_CI_YML` -> `deploy.yml`)
- [ ] Add new scripts to the `[tool.mypy]` module list if typed; keep function sizes <= 80 in any new file under `server`/`stub-server` (new scripts are outside that gate but keep them small)

Tests that pin docs and must be kept consistent when rewriting (`deploy/tests/test_docs.py`): README must keep `releases/`, `activate.sh`, `00-skypane.conf`, `PermitRootLogin no`, `SKYPANE_OFFBOX_MARKER`, "Restore" heading, "Rehearsal log", no `root@`, typed-release section strings (`skypane-<key>-<tag>.bin`, `SKYPANE_ENABLE_SECOND_HARDWARE`, "exactly `1`", the "skipped <tag> [<key>]: hardware type not available here" text), the lift runbook phrases ("only by the owner", "written confirmation", `workflow_dispatch`, "`ci.yml`", "no agent", "not yet published", "switch is closed"); and `firmware/SIGNING.md` "## Per-type releases" must keep `skypane-<key>-<tag>.bin`, `release-<key>.json`, "one RSA signing key", `build-ee02`, `build-second`, `check_production_config.sh built`, `firmware-release.yml`. NOTE: the runbook phrase "`ci.yml`" would become wrong (the deploy is now `deploy.yml`); update the runbook and that test together, deliberately. `companion/test_compliance_credits.py` reads `COMPLIANCE.md` sections per credited source: keep source headings. `server/test_firmware_partition_bound.py` reads `firmware.yml` for the 90 percent literal: keep that step when editing `firmware.yml`.

### Post-switch checklist (manual, owner and a session, in this order)
1. Session: clone, create branch, push, open a **draft** PR (GitHub MCP / `gh`), read the CI check status, download job logs (`gh api repos/.../actions/jobs/<id>/logs`), confirm the token is valid (`gh auth status`).
2. A PR run on the self-hosted runner goes green; hosted fallback verified once.
3. Dependabot: trigger "Check for updates" in Insights -> Dependency graph -> Dependabot; confirm a PR opens and its CI runs.
4. Nightly backup: Mac launchd pull still succeeds (uses SSH to the VPS, no GitHub; verified by grep: nothing in `deploy/backup` or `activate.sh` calls GitHub).
5. `deploy.yml`: dispatch from main, `Download firmware releases` lists and downloads with `github.token`, import prints `exists <tag>`, probes pass.
6. Firmware release: tag, CI build-only run uploads the artifact, Mac script verifies/signs/publishes, deploy imports. (Use the next real patch version.)
7. Session dispatch test with `firmware-chain-check.yml` to learn whether sessions can dispatch workflows.
8. Not available on Free private (do not assume): branch protection, rulesets, environments, secret scanning, push protection.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes (CI-to-VPS SSH) | Dedicated deploy key, `restrict,command=` forced command, host key pinned in a secret |
| V3 Session Management | no | - |
| V4 Access Control | yes | `workflow_dispatch` + main-only guard + `confirm_sha`; server gate; optional signed ticket; no environments on Free |
| V5 Input Validation | yes | Tag regexes (`fw-vX.Y.Z`), `fw_release_assets.py` allow-list, `confirm_sha` and SHA regex, gate verbs by exact match |
| V6 Cryptography | yes | `espsecure.py` RSA-3072 Secure Boot V2 signing in the digest-pinned container; `ssh-keygen -Y` for tickets; never hand-roll |
| V14 Config / CI | yes | `permissions: contents: read`, SHA-pinned actions, secrets via `env:` only, ephemeral runner, no secrets in the VM |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Branch workflow reads repo secrets (deploy key) | Information disclosure / Elevation | Server-side forced command; owner-signed ticket; dedicated key |
| Session or Dependabot branch runs code on the owner's Mac | Elevation / Tampering | VM without host mounts, JIT ephemeral, no secrets, read-only token |
| Malicious unsigned build handed to the Mac signer | Tampering | Provenance checks (run on tag commit, tag on main, SHA256SUMS), owner reads notes |
| Signing key exposure on the Mac | Information disclosure | Encrypted backup, decrypt to RAM only, `--network none`, shred, never in repo/VPS/GitHub |
| Tag pushed for off-main commit | Spoofing | `guard` job plus Mac re-check |
| Stale deploy after main moved | Tampering | Tip-of-main equality, `confirm_sha` |
| Secret printed during inventory | Information disclosure | Report type/file/commit only; scan script test asserts no value in output |
| Fork PR on runner | Elevation | Private repo, no collaborators, forks disabled; do not enable fork-PR workflows |
| Post-flip environment secrets ignored | Availability | Move/delete before the flip |

## Sources

### Primary (HIGH confidence)
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments - environments ignored when converting to private; Pro/Team only for private
- https://docs.github.com/en/billing/concepts/product-billing/github-actions - self-hosted runners free, $12 included, Dependabot on standard hosted free, 500 MB artifacts / 10 GB cache
- https://github.blog/changelog/2025-12-16-coming-soon-simpler-pricing-and-a-better-experience-for-github-actions - self-hosted charge postponed
- https://docs.github.com/en/actions/reference/security/secure-use - self-hosted runner warnings, JIT, secrets readable by write access
- https://docs.github.com/en/actions/reference/runners/github-hosted-runners - private ubuntu-latest is 2 vCPU/8 GB, latest = Ubuntu 24.04
- https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json - 3.14.10 on linux arm64 22.04/24.04/26.04 and darwin arm64
- Repo files read: `.github/workflows/*.yml`, `.github/dependabot.yml`, `deploy/deploy.sh`, `deploy/README.md`, `deploy/backup/backup_gate.py`, `deploy/backup/install-backup-key.sh`, `firmware/SIGNING.md`, `scripts/ci_gates.py`, `ci_shards.py`, `ci_run_timing.py`, `fw_release_assets.py`, `server/firmware_registry.py`, `deploy/tests/test_ci_secrets.py`, `test_release_assets.py`, `test_docs.py`
- Anonymous GitHub API calls on the public repo (releases, runs, jobs, stars, forks, artifacts count) and a `pip download --require-hashes` aarch64 check run in this session

### Secondary (MEDIUM confidence)
- https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/managing-dependabot-on-self-hosted-runners - `dependabot` label, queues if no runner
- Search result: queued job with no matching runner fails after 24 hours (docs.github.com/en/actions/reference/runners/self-hosted-runners)
- https://docs.github.com/en/rest/actions/self-hosted-runners - JIT config endpoint (not fetched this session; from search and prior knowledge)

### Tertiary (LOW confidence)
- gitleaks flag behaviour across versions (search only)
- Linux arm64 Chromium under Playwright 1.64.1; `espressif/idf` arm64 availability; session token scopes

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - official pieces verified; Mac-specific runner choices are design, not tested
- Architecture: MEDIUM-HIGH - derived from the actual workflows and tests
- Pitfalls: HIGH for the environment/secret ordering and test pins (documented and read in code); MEDIUM for runner behaviour

**Research date:** 2026-11-24
**Valid until:** 2026-12-24 for GitHub billing and runner facts (the self-hosted charge may change at any time; re-check the changelog before the flip)
