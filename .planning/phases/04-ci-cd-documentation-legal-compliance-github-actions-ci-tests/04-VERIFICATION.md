---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
verified: 2026-08-27T18:10:00Z
status: passed
score: 10/10 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 04: CI/CD, Documentation & Legal Compliance Verification Report

**Phase Goal:** GitHub Actions runs the full test suite (server/test_*.py) and code-quality/coverage checks on every push/PR, with an automated (gated, not silently-triggered) deploy step pushing to the real OVH VPS on merge to main; the repository has a README a newcomer can build/deploy from, a LICENSE, and documented confirmation that PRIM/IDFM's and the ADS-B aggregators' terms of use are actually being honored (no raw-data republishing, rate-limit compliance, attribution where required); asset attribution (fonts, icons, illustrations) is consolidated and verifiably complete via the existing VENDOR.md files.

**Verified:** 2026-08-27T18:10:00Z
**Status:** passed
**Re-verification:** No — initial verification (bookkeeping gap: phase was fully executed and merged but the verify step of the original run never produced this file)

## Verification Method

This was a retroactive verification against **live infrastructure**, not just repo files. All six plans (04-01 through 04-06) had SUMMARY.md files claiming completion. Rather than trust those claims, every claim below was independently re-checked either against the current working tree/git state, or against GitHub's live API (`gh api`, `gh run list`, `gh secret list`) for anything that only a real GitHub-hosted run can prove (workflow execution, environment protection rules, actual gate behavior). Where the SUMMARY documents a specific historical event (e.g., the original push and first proof run on 2026-08-26), that event was treated as credible per this task's instructions, but wherever the same property is still currently observable (repo visibility, environment config, recent CI runs, current file contents), it was independently re-observed rather than taken on the SUMMARY's word — and in several cases the live evidence gathered here is from CI runs that happened *after* Phase 4 closed (the phase has been in continuous production use since), which is stronger evidence than anything the phase's own SUMMARYs could have captured.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GitHub Actions runs the full 9-harness test suite, blocking lint, and a coverage threshold on every push and pull request | ✓ VERIFIED | `.github/workflows/ci.yml` `test` job runs `ruff check .`, `scripts/run-all-tests.sh`, `scripts/check-attribution.sh` on `push: [main]` and `pull_request`. Live evidence: `gh run list` shows 10+ real runs since publication, all `test` jobs `success` except one deliberate throwaway lint-break PR (#1, run 33009562762) which correctly `failure`d at the Lint step and skipped the rest — proving the gate actually blocks. Orchestrator's pre-run of `scripts/run-all-tests.sh` (9/9, 82% coverage) and `ruff check .` (clean) independently reconfirmed the current tree is green. |
| 2 | The deploy job is gated behind a real, enforced human-approval step (GitHub Environment `production`, required reviewer) — not a bare auto-deploy | ✓ VERIFIED (behavioral) | `gh api repos/florianlepont/skypane/environments` shows environment `production` with a `required_reviewers` protection rule (reviewer: `florianlepont`) and `"can_admins_bypass": false` (the 04-06 SUMMARY records a live defect where this flag was initially `true` and was fixed during the phase — the current live config confirms the fix held). Behavioral proof, not just config presence: two push-to-main runs (33010554993, 33010780555, both docs-only commits from 2026-08-26) show `test` succeeding but `Deploy to production` concluding `failure` with an **empty steps array** — i.e., the job was never approved and never ran, exactly the gate-holding behavior D-11 requires. The most recent push-to-main run (33099436394, 2026-08-27, unrelated to this phase's own commits) shows both `test` and `Deploy to production` concluding `success`, proving the gate can also be approved and successfully complete a real deploy. No stuck/pending deployments remain (`gh run list` shows zero non-completed runs). |
| 3 | The deploy job's only action is invoking `deploy/deploy.sh`; no rsync/systemctl logic is reimplemented in YAML, and no credential or host literal appears in the workflow file | ✓ VERIFIED | `.github/workflows/ci.yml`'s `deploy` job: loads `secrets.DEPLOY_SSH_PRIVATE_KEY` via `webfactory/ssh-agent`, writes `secrets.DEPLOY_HOST_KEY` into `known_hosts`, then runs exactly `./deploy/deploy.sh "${{ secrets.DEPLOY_SSH_TARGET }}"` — one step, no other deploy logic. `gh secret list` confirms all three secret names (`DEPLOY_HOST_KEY`, `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_SSH_TARGET`) exist in the repo. No IP/hostname literal found in the workflow file (grep confirmed). |
| 4 | Repository has a README a newcomer can build/deploy from, pointing at (not duplicating) the authoritative sub-docs | ✓ VERIFIED | `README.md` (163 lines) at repo root: honest v1-scope statement, directory map, Hardware/Server/Tests/Firmware/Deployment sections each pointing at `hardware/BOM.md`, `server/README.md`, `scripts/run-all-tests.sh`, `firmware/build.sh`, `deploy/README.md` respectively rather than duplicating them. 04-05-SUMMARY documents every command in it was actually executed and observed working during authoring (venv install, `render.py`, `poll_loop.py --once`, `scripts/run-all-tests.sh`, `ruff check .`, `scripts/check-attribution.sh`). |
| 5 | Repository carries a LICENSE (MIT) with an accurate scope note excluding separately-licensed vendored assets | ✓ VERIFIED | `LICENSE` at repo root: full MIT grant/conditions/disclaimer text, correct copyright holder/year, plus a scope note explicitly excluding `server/assets/fonts/`, `server/assets/icons/plane-*`, and `server/assets/icons/illustrations/`, pointing to each directory's `VENDOR.md`. |
| 6 | No commit reachable from any ref, and no file in the current working tree, contains the real VPS IP/hostname or other sensitive literals (Wi-Fi SSID/BSSID, device MAC, home address) | ✓ VERIFIED | `SCRUB-RECORD.md` documents a `git-filter-repo` rewrite (Categories A+B+C, 154→154 commits preserved) plus a second pass during 04-06 (supplier order numbers). Independently re-checked the **current** working tree: `grep` for dotted-quad IPv4 patterns across tracked `.md/.py/.yml/.sh` files returns only loopback/wildcard addresses, an RFC 5737 documentation-example IP (`203.0.113.10`, used deliberately as a non-real example in `deploy/README.md`'s usage comment), and `<vps-ip>`/`<public-host>` placeholder tokens — no real address. `firmware/main/secrets.h` and `deploy/skypane.env` are not tracked (`git ls-files` empty for both) and are `git check-ignore`-confirmed ignored. |
| 7 | COMPLIANCE.md documents, per third-party data source, whether it's used and what this repo does to honor its terms (no raw-data republishing, rate-limit compliance, attribution where required) | ✓ VERIFIED | `COMPLIANCE.md` (currently covers 6 sources — grown from D-14's original 3 as the codebase evolved post-phase: adsb.fi, adsb.lol, airplanes.live, adsbdb.com, PRIM/IDFM, AeroDataBox) states per-source usage status, terms-checked date, and verdict. A dedicated "Runtime behaviour vs. the aggregators' constraints" section states the poll cadence (30s, ≥1.1s between provider calls, within all providers' 1 req/s limits) and explicitly states no raw aggregator JSON is republished — only a rendered panel image derived from a single selected flight. adsb.fi's cite-and-link requirement is met with real citation text (confirmed present both here and in `README.md`). PRIM/IDFM is correctly documented as unused in v1 (verified by the same grep this document cites), with an explicit "revisit at v2" flag rather than a silently-dropped claim. |
| 8 | Asset attribution (fonts, icons, illustrations) is consolidated and machine-verifiably complete via VENDOR.md files | ✓ VERIFIED | Independently re-ran `./scripts/check-attribution.sh`: `PASS: 60 asset file(s) all attributed in 3 VENDOR.md file(s); 3 font family(ies) all have licence text.` (matches the orchestrator's pre-run result exactly, confirming no drift). All three OFL font families (Inter, Zilla Slab, PT Serif) have vendored `*-OFL.txt` license text on disk. |
| 9 | The repository is actually public on GitHub, and CI has proven itself green on real infrastructure, repeatedly, not just once | ✓ VERIFIED | `gh repo view florianlepont/skypane` → `"visibility":"PUBLIC"`. `gh run list` shows 10+ CI runs across the day-of-publication proof session and multiple days since (through 2026-08-27), the large majority `success`, including runs completely unrelated to Phase 4's own commits — i.e., the pipeline is in ongoing real use, not a one-time demo. |
| 10 | Firmware CI build (D-10, discretionary) is included and functioning | ✓ VERIFIED | `.github/workflows/firmware.yml` is path-restricted to `firmware/**`, copies the placeholder `secrets.example.h`, runs `./firmware/build.sh` unchanged, and asserts `firmware/build-ee02/skypane.bin` exists. `gh run list --workflow=firmware.yml` shows 4 real runs, all `success`, including both `push` and `pull_request` triggers and a non-firmware-path push correctly *not* triggering a run. |

**Score:** 10/10 truths verified (0 present-but-behavior-unverified)

### Requirements Coverage

Per the phase's own note in ROADMAP.md and `04-CONTEXT.md`: this phase has no `PLANE-*`/`DEVICE-*` requirement IDs of its own. Its requirements are the 16 locked decisions `D-01` through `D-16` recorded in `04-CONTEXT.md`, which is the traceability anchor each plan's `requirements:` frontmatter cites. `.planning/REQUIREMENTS.md` deliberately does not carry these IDs (confirmed: no `D-0`/`D-1` matches in that file) — the phase's own requirement map is `04-CONTEXT.md` + the plans' frontmatter, not `REQUIREMENTS.md`.

| Requirement | Source Plan(s) | Description | Status | Evidence |
|---|---|---|---|---|
| D-01 | 04-06 | GitHub repo created | ✓ SATISFIED | `github.com/florianlepont/skypane` exists, `gh repo view` confirms |
| D-02 | 04-06 | Repository is public | ✓ SATISFIED | `gh repo view` → `visibility: PUBLIC` |
| D-03 | 04-01 | No real secrets ever committed | ✓ SATISFIED | `firmware/main/secrets.h`/`deploy/skypane.env` untracked and gitignored |
| D-04 | 04-01 | Real VPS IP/hostname were committed pre-phase | ✓ SATISFIED (historical finding, scrub addressed it) | SCRUB-RECORD.md documents the finding and remediation |
| D-05 | 04-01, 04-06 | Sensitive literals scrubbed from all history before first public push | ✓ SATISFIED | SCRUB-RECORD.md (two passes); current working tree re-checked, no real literal found |
| D-06 | 04-01 | Repo-root `.gitignore` added | ✓ SATISFIED | `.gitignore` exists, covers OS/Python/coverage/ESP-IDF/credential patterns |
| D-07 | 04-02, 04-04 | CI runs all 9 non-pytest harnesses correctly | ✓ SATISFIED | `scripts/run-all-tests.sh` enumerates and runs all 9; `ci.yml` calls it |
| D-08 | 04-02, 04-04 | Dependencies pinned, installed from `requirements.txt` | ✓ SATISFIED | `server/requirements-dev.txt` separate from prod; `ci.yml` installs both |
| D-09 | 04-02, 04-04, 04-06 | Lint and coverage are blocking | ✓ SATISFIED | `ci.yml`'s lint/test steps have no `continue-on-error`; live throwaway-lint-break PR proved the block |
| D-10 | 04-04 | Firmware CI build (discretionary) | ✓ SATISFIED | `firmware.yml`, 4 real green runs |
| D-11 | 04-04, 04-06 | Deploy gated by manual approval via GitHub Environment | ✓ SATISFIED | `production` environment, required reviewer, `can_admins_bypass: false`, live gate-hold + live approved-deploy both observed |
| D-12 | 04-04, 04-06 | Deploy job wraps `deploy.sh`, dedicated CI SSH key | ✓ SATISFIED | Single `run: ./deploy/deploy.sh ...` step; dedicated `DEPLOY_SSH_PRIVATE_KEY` secret, not the developer's personal key (per 04-06-SUMMARY) |
| D-13 | 04-03 | MIT LICENSE | ✓ SATISFIED | `LICENSE` present, correct scope note |
| D-14 | 04-03, 04-05 | Terms-of-use compliance documentation + attribution | ✓ SATISFIED | `COMPLIANCE.md`, adsb.fi citation in both `COMPLIANCE.md` and `README.md` |
| D-15 | 04-05 | README lets a newcomer build/deploy | ✓ SATISFIED | `README.md`, commands verified working per 04-05-SUMMARY |
| D-16 | 04-05 | Current-state ARCHITECTURE.md | ✓ SATISFIED | `ARCHITECTURE.md` (325 lines), grounded in named source files; research doc marked superseded, zero lines deleted |

No orphaned requirements — all 16 D-IDs are claimed by at least one plan's `requirements:` frontmatter and independently verified above.

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `.gitignore` | Repo-root credential/cruft ignore rules | ✓ VERIFIED | Present, covers OS/Python/coverage/ESP-IDF/worktree/credential patterns |
| `SCRUB-RECORD.md` | Audit record of the history scrub | ✓ VERIFIED | Present, documents category/count without restating literals |
| `server/requirements-dev.txt` | Dev-only tooling pins | ✓ VERIFIED | `ruff`, `coverage`, separate from production deps |
| `pyproject.toml` | Ruff + coverage config | ✓ VERIFIED | `[tool.ruff]` select=E4,E7,E9,F; `[tool.coverage]` scoped, `fail_under=75` (current measured 82%, above threshold) |
| `scripts/run-all-tests.sh` | Canonical 9-harness runner | ✓ VERIFIED | Present, executable, self-locating; independently re-run, 9/9 pass |
| `LICENSE` | MIT with asset-scope note | ✓ VERIFIED | Present, correct |
| `COMPLIANCE.md` | Per-source terms documentation | ✓ VERIFIED | Present, 6 sources documented (grown since phase close) |
| `scripts/check-attribution.sh` | Machine-checked attribution gate | ✓ VERIFIED | Present, executable; independently re-run, PASS 60/60 |
| `server/assets/fonts/Inter-OFL.txt` | Closed OFL gap | ✓ VERIFIED | Present on disk |
| `.github/workflows/ci.yml` | Blocking CI + gated deploy | ✓ VERIFIED | Present, structurally correct, live-proven on GitHub |
| `.github/workflows/firmware.yml` | Path-restricted firmware build | ✓ VERIFIED | Present, live-proven on GitHub (4 green runs) |
| `README.md` | Newcomer front door | ✓ VERIFIED | Present, 163 lines, all commands verified working |
| `ARCHITECTURE.md` | Current-state system description | ✓ VERIFIED | Present, 325 lines, grounded in named source files |
| GitHub repository (public) | Live, public repo | ✓ VERIFIED | `github.com/florianlepont/skypane`, PUBLIC |
| GitHub Environment `production` | Required-reviewer gate | ✓ VERIFIED | Exists, `required_reviewers` rule, `can_admins_bypass: false` |
| 3 repository secrets | Deploy key, SSH target, host key | ✓ VERIFIED | `DEPLOY_HOST_KEY`, `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_SSH_TARGET` all present |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `ci.yml` | `scripts/run-all-tests.sh` | `run: ./scripts/run-all-tests.sh` | ✓ WIRED | Confirmed by file content and by live run logs showing all 9 harnesses executing |
| `ci.yml` | `scripts/check-attribution.sh` | `run: ./scripts/check-attribution.sh` | ✓ WIRED | Confirmed by file content and live run log ("PASS: 23..." at time of run, now 60 as assets grew) |
| `ci.yml`'s deploy job `environment:` | GitHub Environment `production` | name match | ✓ WIRED | `environment: { name: production }` in YAML matches the live environment's name exactly; confirmed enforced (gate holds/releases as observed) |
| `ci.yml`'s deploy job | `deploy/deploy.sh` | `run: ./deploy/deploy.sh "${{ secrets.DEPLOY_SSH_TARGET }}"` | ✓ WIRED | Sole deploy action; live run log shows `deploy.sh`'s own rsync/restart output completing with `==> Deploy complete.` (per 04-06-SUMMARY, and the mechanism is unchanged in the current file) |
| `README.md`'s Data Sources section | `COMPLIANCE.md` | markdown link + adsb.fi citation duplicated in both | ✓ WIRED | Confirmed: `grep -qi 'https://adsb.fi'` matches both files |
| `LICENSE`'s asset scope note | `server/assets/**/VENDOR.md` | pointer + `check-attribution.sh` enforcement | ✓ WIRED | Scope note names the three VENDOR.md files; checker enforces completeness live |
| `ARCHITECTURE.md` | `.planning/research/ARCHITECTURE.md` | supersession pointer both directions | ✓ WIRED | Research doc's first lines point at root `ARCHITECTURE.md`; root doc explains the research doc's different nature |

### Anti-Patterns Found

Scanned all phase-created/modified files (`.github/workflows/ci.yml`, `.github/workflows/firmware.yml`, `LICENSE`, `COMPLIANCE.md`, `README.md`, `ARCHITECTURE.md`, `scripts/run-all-tests.sh`, `scripts/check-attribution.sh`, `pyproject.toml`, `server/requirements-dev.txt`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` and empty-implementation patterns.

**None found.** No debt markers, no placeholder returns, no stub patterns in any phase-delivered file.

One informational (not blocking) item: `04-VALIDATION.md` still carries its pre-execution frontmatter (`status: draft`, `nyquist_compliant: false`, `wave_0_complete: false`, `Approval: pending`) — this is the same class of bookkeeping gap this verification run itself was dispatched to close (a document that was never updated after execution finished), not a functional gap in the delivered CI/CD/docs/legal work. Does not affect the phase goal.

### Behavioral Spot-Checks / Probe Execution

This phase's own closing acceptance signal (per `04-VALIDATION.md`'s Sampling Rate section) was explicitly "the CI workflow going green on a real GitHub push (not a local dry-run)." That signal was independently reproduced here via `gh run list`/`gh run view`/`gh api` against the live repository rather than trusted from SUMMARY narration:

| Behavior | Command | Result | Status |
|---|---|---|---|
| CI test job runs and passes on real push | `gh run list -R florianlepont/skypane --limit 10` | 10/10 recent runs' `test` jobs `success` | ✓ PASS |
| CI test job actually blocks on a real failure | inspected run 33009562762 (throwaway lint-break PR) | Lint step `failure`, remaining steps skipped, deploy job `steps: []` | ✓ PASS |
| Deploy gate holds (pauses/declines) when not approved | inspected runs 33010554993, 33010780555 | `test` `success`, `Deploy to production` `failure` with empty steps (never approved) | ✓ PASS |
| Deploy gate releases and deploys after approval | inspected run 33099436394 (most recent push to main) | Both `test` and `Deploy to production` `success` | ✓ PASS |
| Firmware CI builds correctly, path-restricted | `gh run list --workflow=firmware.yml` | 4/4 runs `success`, both `push` and `pull_request` triggers observed | ✓ PASS |
| Attribution checker currently passes | `./scripts/check-attribution.sh` | `PASS: 60 asset file(s)...3 font family(ies)...` | ✓ PASS |
| No stuck/pending deployments remain | `gh run list` filtered to non-`completed` status | `[]` | ✓ PASS |

### Human Verification Required

None. All must-haves resolved to VERIFIED against either the current working tree or live GitHub infrastructure queried directly during this verification pass.

### Gaps Summary

No gaps found. Every observable truth derived from the phase goal, every D-01 through D-16 requirement, every plan-level must-have artifact and key link, and every claim in the six SUMMARY.md files that was independently checkable against the current repository state or live GitHub infrastructure, checked out. The only deviation from a clean bill is a stale `04-VALIDATION.md` frontmatter block (pre-execution status never updated) — informational only, does not block the phase goal, and is the same class of post-execution bookkeeping gap this verification run itself exists to close.

---

_Verified: 2026-08-27T18:10:00Z_
_Verifier: Claude (gsd-verifier)_
