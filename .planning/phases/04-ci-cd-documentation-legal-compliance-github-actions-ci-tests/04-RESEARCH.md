# Phase 4: CI/CD, Documentation & Legal Compliance - Research

**Researched:** 2026-08-26
**Domain:** GitHub Actions CI/CD for a non-pytest Python test suite, gated VPS deployment, git history rewriting, open-source licensing/legal compliance
**Confidence:** MEDIUM (CI/CD mechanics HIGH; third-party ToS text MEDIUM-LOW, two sources blocked live verification)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Repository & visibility**
- **D-01:** This repository has never been pushed to a remote (`git remote -v` is empty). Phase 4's first real prerequisite is creating the GitHub repo.
- **D-02:** Repository will be **public**. Rationale (user): willing to show/share the project.

**Pre-publish history hygiene (real, not theoretical - live-checked)**
- **D-03:** No actual secrets (`deploy/inkframe.env`, `firmware/main/secrets.h`) have ever been committed - verified via `git log --all -p` on both paths, clean. This discipline holds and must continue.
- **D-04:** The real VPS's public IP (`<vps-ip>`) and hostname (`<public-host>`) ARE already committed, across `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/phases/02-plane-view-end-to-end-slice/02-05-SUMMARY.md`, `.planning/phases/02-plane-view-end-to-end-slice/02-VERIFICATION.md`, and `deploy/README.md`.
- **D-05 (user decision):** These must NOT be visible once public ("j'aimerais que ces informations sensibles ne soient pas visibles si possible"). Since this repo has **no remote yet and no collaborators**, the clean fix is available: scrub the real IP/hostname from every historical commit (not just HEAD) before the first push to GitHub - either a full history rewrite (`git filter-repo` targeting the literal strings) or squashing local history into a fresh initial commit with the strings redacted first. **Left to planner/research to pick the exact mechanism** - the requirement is that neither the real IP nor the real hostname exist in any commit ever pushed publicly. Live docs should reference the VPS by a placeholder (e.g. `<vps-host>`) or via `deploy/inkframe.env`-style external config, matching the existing "real values never in git" pattern this project already uses for secrets.
- **D-06:** No `.gitignore` exists anywhere in this repo (verified - `ls .gitignore` finds nothing). Must be added before the public push: at minimum `.DS_Store`, Python `__pycache__`/`.venv`, ESP-IDF `firmware/build*/`, and an explicit (belt-and-suspenders, even though discipline has held so far) `deploy/inkframe.env` / `firmware/main/secrets.h` ignore pair.

**CI pipeline (GitHub Actions)**
- **D-07:** Runs the existing test harnesses under `server/.venv` - note these are **not pytest**, they're custom `check()`/PASS-FAIL/`EXPECTED_CHECK_COUNT` harnesses invoked as `python3 server/test_*.py`, each exiting 0/1 (see `server/test_render.py`, `server/test_dither.py`, `server/test_poll_loop.py`, `server/test_enrich.py`, `server/test_plane_detection.py`, `server/test_runway_config.py`, `server/test_pipeline_e2e.py`). CI must invoke each one as its own step (or a loop), not assume a pytest collector will find them. **Research correction:** this list is incomplete — `server/test_illustrations.py` and `stub-server/test_poll_cycle.py` also exist and follow the identical convention; see Common Pitfalls Pitfall 1.
- **D-08:** Dependencies pinned in `server/requirements.txt` (Pillow==12.3.0, requests==2.34.2) - CI installs from this file, doesn't re-derive versions.
- **D-09 (user decision, "Bloquante"):** Lint (tool choice left to planner/research - Ruff is the modern default for this stack) and coverage are **blocking**: the CI run must fail if lint fails, or if coverage regresses below a threshold the plan sets. This is stricter than the researcher's first-instinct "report only" recommendation - the user explicitly chose blocking despite being a solo project.
- **D-10:** Firmware (ESP-IDF/CMake under `firmware/`) is a separate build system from the Python server. Whether Phase 4's CI also builds firmware (Espressif publishes an official `espressif/esp-idf-ci-action` for exactly this) is **Claude's Discretion** - not discussed live, no strong signal either way. Default recommendation: include it if it's low-effort via the official action; otherwise defer to a follow-up.

**Deploy automation**
- **D-11 (user decision):** Deploy triggers on merge to `main`, but requires a **manual approval step** before it actually runs against the real VPS - implement via GitHub Environments' required-reviewers protection rule, not a bare `workflow_dispatch` or an unprotected auto-deploy job. Rationale (user, implicit in the choice): this VPS serves a real physical device on the wall; tests passing doesn't guarantee the render pipeline looks right on real glass, so a human checkpoint before every prod push is wanted.
- **D-12:** The deploy job itself should wrap the existing `deploy/deploy.sh` (rsync + service restart) rather than reimplementing its logic in the workflow YAML - that script is already tested/working (see `deploy/README.md`). CI needs the VPS SSH key as a GitHub Actions secret and must never print/log it.

**Legal / licensing**
- **D-13 (user decision):** License is **MIT**. Compatible with the already-vendored asset licenses (SIL OFL 1.1 for Inter/Zilla Slab/PT Serif fonts, see `server/assets/fonts/VENDOR.md`; check `server/assets/icons/VENDOR.md` for icon licensing before finalizing the LICENSE file's scope note).
- **D-14 (user decision, from the earlier scope-confirmation question):** "Legal information" scope = (1) LICENSE file, (2) third-party API terms-of-use compliance check/documentation for AeroDataBox (unused - PROJECT.md's reversed decision to local ADS-B, confirm this is actually true in the shipped code before writing "not used"), PRIM/IDFM (used for the deferred RER view research, confirm current usage status), and the ADS-B aggregators (adsb.fi/airplanes.live - confirm no raw-data-republishing clause is violated by rendering derived departure-board info), (3) consolidated/verified asset attribution - largely already done via `server/assets/fonts/VENDOR.md` and `server/assets/icons/VENDOR.md`, this phase's job is to verify completeness, not redo it.

**Documentation**
- **D-15:** README must let a newcomer actually build/deploy from scratch - covers hardware BOM, firmware flash, server setup, and a pointer to `deploy/README.md` for the VPS provisioning flow (not a duplicate of it).
- **D-16 ("architecture" tracking, user-requested):** A pre-existing `.planning/research/ARCHITECTURE.md` exists but is **generic domain research from project inception** (2026-08-04, before any of this was built) - not a description of what's actually shipped. Phase 4 needs a real, current architecture doc/README section describing the actual built system (device firmware state machine, server render pipeline, VPS deployment topology) - the old research doc is a useful reference, not something to just re-publish.

### Claude's Discretion
- Exact lint tool (Ruff recommended) and coverage tool (pytest-cov's coverage.py engine works fine even without using pytest as the runner) - not discussed live.
- Whether firmware CI build is in-scope for this phase or deferred (D-10).
- Exact coverage threshold percentage - the planner should pick a realistic starting baseline from the current suite's actual measured coverage, not an arbitrary round number.
- Git-history-scrub mechanism (filter-repo vs. fresh squashed history) - D-05.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. (Firmware CI build, D-10, is not deferred to another phase, just left as an in-phase discretion call for the planner.)
</user_constraints>

## Summary

This phase wraps already-working code (Phases 1-3) in the scaffolding a public open-source repo needs: CI, a gated deploy, a license, a README, and a documented legal-compliance check. None of the underlying engineering is new or risky — the test suite already runs cleanly, `deploy/deploy.sh` already works, and the license/attribution story is close to done via existing VENDOR.md files. The real risk in this phase is almost entirely mechanical correctness: getting `git filter-repo` (or a squash) to actually remove the VPS IP/hostname from every one of the repo's 147 commits before the first public push, and correctly wiring GitHub's non-pytest-shaped test suite (9 independently-exiting scripts, not 1 discoverable via a collector) into CI steps that fail loud.

The test suite is explicitly **not pytest** — every `server/test_*.py` and `stub-server/test_poll_cycle.py` is a stdlib `check()`/`EXPECTED_CHECK_COUNT`/`main()` harness that calls `sys.exit(main())` with an honest 0/1 exit code. This means CI doesn't need a pytest collector or `pytest-cov` — it needs N sequential `run:` steps (or a small loop script), each invoked under `server/.venv`'s interpreter (Pillow is a transitive import), and `coverage run --parallel-mode -a` wrapping each invocation so `coverage combine` can produce one aggregate number afterward. Two test files are missing from CONTEXT.md's D-07 enumeration and MUST be added to the plan: `server/test_illustrations.py` (validated to exist, has its own `check()` harness) and `stub-server/test_poll_cycle.py` (a ninth, previously-unlisted harness under a different directory with its own README-documented "no pytest" convention).

For the deploy gate, GitHub Environments + required reviewers is the only native mechanism GitHub offers for "tests run automatically, a human clicks approve, then deploy runs" — no third-party action is needed. The deploy job should invoke `deploy/deploy.sh <ssh-target>` unchanged after `webfactory/ssh-agent` loads the VPS SSH private key from a GitHub secret; `deploy.sh` already does the rsync/pip/systemd-restart work, so the workflow YAML should not reimplement any of it.

The two ADS-B data sources (`airplanes.live`, `adsb.fi`) are the ones actually shipped in code (`server/plane/detect.py`); **PRIM/IDFM is not used anywhere in the shipped v1 code** — RER is deferred to v2 per REQUIREMENTS.md and PROJECT.md, and `AeroDataBox` was explicitly reversed and never implemented. This means D-14's compliance check is straightforward for two of the three named APIs ("not used, no action needed, revisit at v2 planning") and requires real attention for one: `adsb.fi`'s terms (confirmed by direct fetch of their GitHub README) require attribution — "you must cite adsb.fi and include a link to our home page" — and **this attribution does not currently exist anywhere in the codebase or README**. This is a genuine, actionable compliance gap this phase must close, not a theoretical one.

**Primary recommendation:** Use `git filter-repo --replace-text` for the history scrub (safer and more surgical than a squash for a 147-commit repo where commit-by-commit history has real documentation value); wrap the 9 test scripts as sequential `coverage run --parallel-mode -a` steps followed by `coverage combine` + `coverage report --fail-under=<baseline>`; use `astral-sh/ruff-action@v3` for lint; gate `deploy/deploy.sh` behind a GitHub Environment with required reviewers; add `adsb.fi` attribution to the README as the one real, currently-unmet compliance action item; treat PRIM/IDFM as "not applicable this phase" since it ships nowhere in v1 code.

## Architectural Responsibility Map

This phase is infrastructure/documentation, not a multi-tier web app — the standard Browser/API/CDN/DB tiers don't map cleanly. Tiers below are adapted for a CI/CD + legal-compliance phase.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test execution + lint + coverage gate | CI/CD Pipeline (GitHub Actions) | Developer workstation (local pre-push run) | Tests already run locally under `server/.venv`; CI's job is to make that automatic and blocking, not to invent new test logic |
| Deploy automation + approval gate | CI/CD Pipeline (GitHub Actions, Environments) | VPS/Backend (`deploy/deploy.sh`, systemd) | The approval gate is a GitHub-side control; the actual deploy mechanics stay entirely in the existing VPS-facing script — CI must not reimplement rsync/systemd logic |
| Git history scrub (VPS IP/hostname) | Developer workstation (one-time, pre-push) | — | Must happen before the repo ever touches GitHub; not a CI concern, not repeatable infrastructure |
| License + README + architecture doc | Documentation/Legal (repo root) | — | Static content, no runtime component |
| Third-party API ToS compliance | Documentation/Legal (repo root: a COMPLIANCE.md or README section) | API/Backend (`server/plane/detect.py`'s actual request behavior — rate limits, attribution) | The compliance *check* is a doc; the compliance *behavior* (rate limiting, attribution) already lives in the running server code and must be verified to match what's documented |
| Asset attribution (fonts/icons) | Documentation/Legal (VENDOR.md files) | — | Already largely done; this phase verifies completeness, doesn't rebuild it |

## Package Legitimacy Audit

Two new PyPI packages enter this phase's toolchain (`ruff`, `coverage`); GitHub Actions used are third-party marketplace actions, checked separately below.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `ruff` | PyPI | latest release 2026-08-20 (0.16.4); package itself is Astral's flagship linter, multi-year history | not resolvable via the legitimacy checker in this environment (network-restricted) | `github.com/astral-sh/ruff` (confirmed via `docs.astral.sh` redirect) | `SUS` (checker flags "too-new" / "unknown-downloads") | **Approved, false-positive override** — see note below |
| `coverage` | PyPI | latest release 2026-08-06 (7.15.4); `coverage.py` is a foundational, decade-plus-old Python tool (Ned Batchelder) | not resolvable (same network restriction) | `github.com/coveragepy/coveragepy` | `SUS` (same reasons) | **Approved, false-positive override** — see note below |

**False-positive note (both packages):** the legitimacy checker's `too-new`/`unknown-downloads` signals are driven by *latest release publish date* and an unreachable download-stats endpoint in this sandboxed environment, not by package age or legitimacy. Both packages are extremely well-known, high-velocity-release tooling (`ruff` ships new versions weekly; `coverage.py` has existed since the mid-2000s) with official, verifiable source repos. Per protocol, the planner should still add a lightweight `checkpoint:human-verify` before `pip install`-ing either into CI (a one-line "confirm `pip show ruff`/`pip show coverage` after install resolves to the expected PyPI project" check is sufficient — this is not a case requiring deep scrutiny).

**Packages removed due to [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** `ruff`, `coverage` — both overridden to Approved per the false-positive note above; planner still inserts a lightweight verification step per protocol.

**GitHub Actions (marketplace, not PyPI) used by this phase's CI, checked for official-org provenance via WebSearch + repo URL confirmation:**

| Action | Org | Verdict | Note |
|--------|-----|---------|------|
| `actions/checkout` | GitHub official | OK | Standard first step of any workflow |
| `astral-sh/ruff-action` | Astral (Ruff's own maintainer org) | OK | `[ASSUMED]` package-name provenance per protocol (discovered via WebSearch, not Context7) — verify the exact pinned version tag before use |
| `webfactory/ssh-agent` | Third-party, widely used (`marketplace/actions/webfactory-ssh-agent`) | OK, `[ASSUMED]` | Long-established action; still pin to a specific version/SHA, don't float `@master` |
| `espressif/esp-idf-ci-action` | Espressif official (ESP32 vendor) | OK | Only relevant if D-10's firmware-CI discretion is exercised |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `coverage` | 7.15.4 `[VERIFIED: pypi registry — fetched https://pypi.org/pypi/coverage/json directly this session]` | Line-coverage measurement across the 9 non-pytest test scripts | It's the underlying engine `pytest-cov` itself wraps; `coverage run <script>.py` works on any Python entry point, not just pytest-collected tests — exactly matches this project's `check()`-harness shape |
| `ruff` | 0.16.4 `[VERIFIED: pypi registry — fetched https://pypi.org/pypi/ruff/json directly this session]` | Lint (blocking, per D-09) | CLAUDE.md itself already names Ruff as "the modern default for this stack"; single Rust binary, no config required to get useful defaults, fast enough to run on every push without slowing CI |
| `astral-sh/ruff-action` | `@v3` (floating major tag, Astral's own recommended pin) `[ASSUMED — discovered via WebSearch]` | Runs `ruff check` as a CI step | Official action from Ruff's own maintainer org; adds `ruff` to PATH and runs check by default — no separate `pip install ruff` step needed in the lint job |
| `webfactory/ssh-agent` | pin to a released version tag, not `@master` `[ASSUMED — discovered via WebSearch]` | Loads the VPS SSH private key from a GitHub secret into `ssh-agent` for the deploy job | Minimal-footprint: only sets up agent + key, letting `deploy/deploy.sh`'s own `rsync`/`ssh` calls run completely unmodified in the next step — matches D-12's "wrap, don't reimplement" requirement more directly than an all-in-one remote-command action would |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `git filter-repo` | latest (pip-installable or Homebrew `git-filter-repo`) | One-time history rewrite to remove the literal VPS IP/hostname from all 147 existing commits | D-05's mechanism — see Common Pitfalls and the dedicated "History Scrub" pattern below |
| `espressif/esp-idf-ci-action` | `@v1` `[ASSUMED — discovered via WebSearch]` | Optional firmware CI build (D-10, Claude's Discretion) | Only if the planner exercises the "include firmware CI" branch of D-10 — see Architecture Patterns |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `git filter-repo --replace-text` | Squash all 147 commits into one fresh initial commit | Squashing is mechanically simpler (`git checkout --orphan`, one commit, force-push nothing since there's no remote) but **destroys the entire phase-by-phase commit history** this project's SUMMARY.md/STATE.md narrative depends on for traceability — filter-repo preserves every commit's message/date/diff-shape while only touching the literal string, which is strictly better for a repo whose git log is itself a form of documentation |
| `astral-sh/ruff-action` | Manual `pip install ruff && ruff check .` step | The manual form works identically and avoids a third-party action dependency entirely — reasonable substitute if the planner prefers zero non-Astral/non-GitHub actions in the workflow |
| `webfactory/ssh-agent` | `appleboy/ssh-action` (all-in-one remote-command executor) | `appleboy/ssh-action` is better when the workflow needs to run ad hoc remote commands *inline* in YAML; worse here because `deploy/deploy.sh` already encapsulates the multi-step rsync/pip/systemctl sequence locally-invoked over SSH — `ssh-agent` is the better fit since the script, not the Action, drives the SSH session |
| `coverage run --parallel-mode` per-script | `pytest-cov` on a pytest wrapper around the 9 scripts | Retrofitting pytest as a collector would mean writing 9 thin pytest wrapper functions solely to get `pytest-cov`'s reporting — unnecessary indirection when `coverage run` already works directly on each script's own `if __name__ == "__main__"` entry point |

**Installation:**
```bash
# In the CI workflow (or added to a new server/requirements-dev.txt, not server/requirements.txt —
# keep production deps and CI-only tooling separate):
pip install coverage ruff
```

**Version verification:** confirmed directly against PyPI's JSON API this session (`curl -s https://pypi.org/pypi/<pkg>/json`), not from training-data memory — `ruff` 0.16.4 (released 2026-08-20), `coverage` 7.15.4 (released 2026-08-06). Both current as of this research date.

## Architecture Patterns

### System Architecture Diagram

```
Developer pushes to a branch / opens a PR
        │
        ▼
┌─────────────────────────────┐
│  GitHub Actions: CI workflow │  (triggers: push, pull_request)
│  ┌─────────────────────────┐│
│  │ 1. actions/checkout      ││
│  │ 2. setup-python + pip    ││
│  │    install -r            ││
│  │    server/requirements   ││
│  │    .txt + coverage+ruff  ││
│  │ 3. astral-sh/ruff-action ││──► FAIL if lint errors (blocking, D-09)
│  │ 4. 9x: coverage run       ││
│  │    --parallel-mode -a     ││──► FAIL if any script exits 1
│  │    <test_X.py>            ││
│  │ 5. coverage combine       ││
│  │    coverage report        ││
│  │    --fail-under=<N>       ││──► FAIL if coverage regresses (blocking, D-09)
│  └─────────────────────────┘│
└──────────────┬───────────────┘
               │ (all green, AND event == push to main)
               ▼
┌───────────────────────────────────┐
│  GitHub Actions: Deploy job        │
│  environment: production           │──► PAUSES here for required reviewer
│  (required-reviewers protection)   │    (D-11: human clicks Approve)
│  ┌───────────────────────────────┐│
│  │ 1. actions/checkout            ││
│  │ 2. webfactory/ssh-agent        ││  loads SSH_PRIVATE_KEY secret
│  │    (from secrets.VPS_SSH_KEY)  ││
│  │ 3. deploy/deploy.sh            ││  ← existing script, unmodified
│  │    "$SSH_TARGET"                ││
│  └───────────────────────────────┘│
└───────────────┬─────────────────────┘
                │
                ▼
   OVH VPS-1 (real production host)
   rsync server/+stub-server/ → systemd restart
   inkframe-byos.service / inkframe-poll.timer
```

### Recommended Project Structure

```
.github/
└── workflows/
    ├── ci.yml           # lint + test + coverage, runs on push/PR, no environment gate
    └── deploy.yml        # deploy job only, environment: production, needs: ci success on main
.gitignore                # NEW this phase (D-06) — repo-root, not per-subdir
LICENSE                    # NEW this phase (D-13) — MIT
README.md                  # NEW this phase (D-15) — repo root, currently absent
COMPLIANCE.md               # NEW this phase (D-14) — or a README section; documents PRIM/adsb.fi/airplanes.live status
server/
├── requirements.txt        # unchanged — production deps only
└── requirements-dev.txt     # NEW (optional) — coverage, ruff, kept out of production installs
```

**Two workflow files vs. one:** splitting `ci.yml` (always runs, every push/PR) from `deploy.yml` (only runs on push to `main`, gated by the `production` environment) keeps the required-reviewer gate scoped precisely to the deploy job — a single combined workflow with a conditional `environment:` on one job works too, but two files make the "tests are automatic, deploy is human-gated" split visually obvious in the Actions tab, which matches the intent behind D-11.

### Pattern 1: Sequential non-pytest test invocation with coverage

**What:** Each of the 9 `check()`/`EXPECTED_CHECK_COUNT` harnesses gets its own CI step, wrapped in `coverage run --parallel-mode --append`, rather than relying on a test collector to discover them.
**When to use:** Any Python test suite that predates or deliberately avoids pytest, where each file is independently executable and exits 0/1 on its own.
**Example:**
```yaml
# Source: coverage.py docs (https://coverage.readthedocs.io/en/latest/cmd.html#combining-data-files)
# combined with this project's own documented "no pytest" convention
# (server/README.md, stub-server/test_poll_cycle.py docstring)
- name: Run server test suite (coverage-instrumented)
  working-directory: .
  run: |
    set -e
    for f in server/test_dither.py server/test_enrich.py server/test_illustrations.py \
             server/test_pipeline_e2e.py server/test_plane_detection.py \
             server/test_poll_loop.py server/test_render.py server/test_runway_config.py \
             stub-server/test_poll_cycle.py; do
      echo "::group::$f"
      server/.venv/bin/python3 -m coverage run --parallel-mode --append --source=server,stub-server "$f"
      echo "::endgroup::"
    done

- name: Combine coverage and enforce threshold
  run: |
    server/.venv/bin/python3 -m coverage combine
    server/.venv/bin/python3 -m coverage report --fail-under=<BASELINE>  # planner sets from measured baseline
```
Because each `for`-loop iteration runs under `set -e`, any single script's non-zero exit aborts the step immediately with that script's own output already printed — matching the "each file's own exit code is the pass/fail signal" convention CONTEXT.md documents (D-07).

### Pattern 2: GitHub Environment manual-approval deploy gate

**What:** A `production` Environment with Required Reviewers, referenced by `environment:` on the deploy job only.
**When to use:** Exactly D-11's requirement — automatic tests, human-approved deploy, no bare `workflow_dispatch`.
**Example:**
```yaml
# Source: GitHub Docs — Deployments and environments
# (https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
deploy:
  needs: ci                # only runs after the CI workflow/job succeeds
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  runs-on: ubuntu-latest
  environment:
    name: production        # must be created in Settings > Environments first,
                             # with "Required reviewers" checked and the user added
  steps:
    - uses: actions/checkout@v4
    - uses: webfactory/ssh-agent@v0.9.1   # pin an exact tag, don't float
      with:
        ssh-private-key: ${{ secrets.VPS_SSH_KEY }}
    - name: Trust VPS host key
      run: ssh-keyscan -H "${{ secrets.VPS_HOST }}" >> ~/.ssh/known_hosts
    - name: Deploy
      run: deploy/deploy.sh "${{ secrets.VPS_SSH_TARGET }}"
```
Note `VPS_HOST`/`VPS_SSH_TARGET` are **GitHub secrets**, not hardcoded — this is also how the workflow YAML itself avoids ever containing the real IP/hostname (reinforcing D-05's goal beyond just the git-history scrub).

### Pattern 3: git filter-repo history scrub (one-time, pre-push)

**What:** Rewrite every commit in local history to replace the literal VPS IP and hostname with placeholders, before the repo's first push to GitHub.
**When to use:** Exactly D-05's situation — sensitive strings committed, zero remotes, zero collaborators, about to go public.
**Example:**
```bash
# Source: git-filter-repo official docs (github.com/newren/git-filter-repo)
# Run from the repo root. filter-repo requires a "fresh clone" by default as a
# safety rail (it refuses to run on a repo it thinks has unpushed/uncommitted
# state it might destroy) — since this repo has literally never been cloned
# from anywhere, use --force to proceed on the working copy directly, but
# only after confirming `git status --porcelain` is clean and a backup exists.

pip install git-filter-repo   # or: brew install git-filter-repo

cat > /tmp/scrub-expressions.txt <<'EOF'
<vps-ip>==>REDACTED_VPS_IP
<public-host>==>REDACTED_VPS_HOSTNAME
EOF

# ALWAYS work on a throwaway clone, never the only copy of the repo:
git clone /Users/florian/Projects/ink-frame /tmp/ink-frame-scrub-clone
cd /tmp/ink-frame-scrub-clone
git filter-repo --replace-text /tmp/scrub-expressions.txt --force

# Verify zero hits across all history before trusting the result:
git log --all -p | grep -c "<vps-ip>"          # must print 0
git log --all -p | grep -c "vps-1440bce3"            # must print 0

# Only after verification, replace the original working repo's history —
# e.g. by adding the scrubbed clone as a remote and hard-resetting, or by
# simply treating the scrubbed clone as the new canonical repo and pushing
# THAT to GitHub. Never push the unscrubbed original.
```
`filter-repo` (not the legacy, upstream-deprecated `git filter-branch`) is the tool git's own docs recommend for this class of operation — it processes history in a single pass and is materially faster and safer against the classic filter-branch pitfalls (partial rewrites, ref cleanup bugs).

### Anti-Patterns to Avoid
- **BFG Repo-Cleaner for literal string replacement:** BFG is excellent at stripping large blobs/files but its text-replacement mode is coarser and less precisely scoped than `filter-repo --replace-text`'s expressions file — not needed here since there's no large-blob problem, only a string problem.
- **Reimplementing `deploy.sh`'s rsync/systemctl logic in workflow YAML:** D-12 explicitly forbids this; every deploy step should be `deploy/deploy.sh $TARGET`, full stop — any YAML that runs `rsync ...` or `systemctl restart ...` directly is duplicating logic that already exists, tested, and works.
- **A bare `workflow_dispatch` "deploy" workflow as the approval mechanism:** technically requires a human to click "Run workflow," but provides none of GitHub Environments' audit trail, reviewer-list enforcement, or wait-timer features — D-11 explicitly rejects this in favor of Environments.
- **Running `pip install -r server/requirements.txt` as bare `pip install` (not into a venv) on the CI runner:** works by accident on an ephemeral GitHub-hosted runner, but breaks the "must run under `server/.venv`'s interpreter, not the bare system python3" convention this project already documents (server/README.md) — CI should create and activate a venv (or use `setup-python`'s own isolated interpreter) to catch the same class of import errors a contributor would hit locally.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Manual-approval deploy gate | A custom "wait for a Slack/email reply" step, or a `workflow_dispatch`-only deploy trigger | GitHub Environments + Required Reviewers | Native, audited, zero extra infrastructure, exactly matches D-11's requirement |
| Combining coverage across 9 separate script runs | A custom script that greps each run's printed coverage % and averages them | `coverage run --parallel-mode` + `coverage combine` | This is the literal, documented purpose of `--parallel-mode` — averaging printed percentages would silently double-count or under-count shared modules imported by multiple test files |
| Git history secret scrubbing | A custom script that walks `git log`, finds matching commits, and rewrites them by hand | `git filter-repo --replace-text` | filter-repo's single-pass rewrite handles ref updates, reflog, and object-store garbage collection correctly; a hand-rolled version is exactly the kind of "deceptively complex" problem this table exists for — get one edge case wrong (e.g. a merge commit, a tag) and secrets remain recoverable in unreachable-but-present objects |
| SSH key handling in CI | Writing the private key to a file with `echo "${{ secrets.KEY }}" > id_rsa` in a `run:` step | `webfactory/ssh-agent` | The action zeroes the key from disk/`.ssh` after loading it into the agent process and is designed specifically to avoid the private key ever appearing readable in a workspace directory or a debug log |

**Key insight:** every "don't hand-roll" item above already has a mature, purpose-built tool this project (or GitHub itself) already documents using elsewhere in the codebase — the theme of this phase is wrapping existing correct behavior in visible automation, not inventing new mechanisms.

## Common Pitfalls

### Pitfall 1: CONTEXT.md's D-07 test-file list is incomplete
**What goes wrong:** A CI workflow built strictly from D-07's enumerated list (`test_render.py`, `test_dither.py`, `test_poll_loop.py`, `test_enrich.py`, `test_plane_detection.py`, `test_runway_config.py`, `test_pipeline_e2e.py`) silently never runs two real, existing harnesses: `server/test_illustrations.py` (confirmed present, has its own `check()`/`EXPECTED_CHECK_COUNT` convention, referenced in its own docstring as closing a gap flagged by 03-03-PLAN.md) and `stub-server/test_poll_cycle.py` (an entirely separate directory's test, documented in `server/README.md` as "the established project convention," never mentioned anywhere in 04-CONTEXT.md).
**Why it happens:** D-07 was written from a partial `ls server/test_*.py` glance during discuss-phase, before `stub-server/` was cross-checked and before `test_illustrations.py`'s existence was independently re-verified this session.
**How to avoid:** The plan's test-execution task must enumerate all 9 files verified live this session: 8 under `server/` (`test_dither.py`, `test_enrich.py`, `test_illustrations.py`, `test_pipeline_e2e.py`, `test_plane_detection.py`, `test_poll_loop.py`, `test_render.py`, `test_runway_config.py`) plus `stub-server/test_poll_cycle.py`.
**Warning signs:** A coverage report with suspiciously low coverage on `server/plane/illustrations.py` or `stub-server/byos_server.py` despite both having dedicated, currently-passing test files.

### Pitfall 2: `git filter-repo` refuses to run without `--force` on a non-"fresh clone" repo
**What goes wrong:** Running `git filter-repo --replace-text ...` directly in the working repo (not a fresh clone) errors out by design (`Aborting: Refusing to destructively overwrite repo history since this does not look like a fresh clone`), which can look like a broken tool rather than an intentional safety rail.
**Why it happens:** `filter-repo` assumes by default that you're operating on a disposable clone, since history rewriting is irreversible without a backup.
**How to avoid:** Either (a) clone the repo to a scratch directory first and run `filter-repo` there (recommended — see Pattern 3 above), or (b) pass `--force` after confirming a full backup/second copy of the repo exists. Never run it as the very first attempt directly against the only copy of the repo without a backup.
**Warning signs:** The tool's own error message names this exact condition — read it, don't `--force` past it reflexively.

### Pitfall 3: Coverage `--source` scope determines whether the "blocking threshold" number means anything
**What goes wrong:** Running `coverage run` without a `--source=` (or `[run] source =` in a `.coveragerc`) scoped to `server` and `stub-server` will also instrument every third-party package imported transitively (Pillow, requests, cairosvg if still present in the venv) — producing a coverage percentage dominated by library internals rather than this project's own code, making the D-09 blocking threshold meaningless.
**Why it happens:** `coverage.py`'s default behavior measures everything importable unless explicitly scoped.
**How to avoid:** Add `--source=server,stub-server` to every `coverage run` invocation (or centralize it in a `.coveragerc`/`pyproject.toml [tool.coverage.run]` section so it isn't repeated 9 times and can't drift).
**Warning signs:** A coverage report listing dozens of `site-packages/PIL/...` files.

### Pitfall 4: adsb.fi's attribution requirement is real and currently unmet
**What goes wrong:** Treating D-14's compliance check as "confirm no violation, write a paragraph" without actually adding the required citation — leaving the repo in violation of a term the maintainer directly confirmed by fetching adsb.fi's own README this session.
**Why it happens:** The attribution clause is easy to read past ("for personal, non-commercial use only") while missing the separate, explicit "must cite adsb.fi and include a link to our home page" sentence in the same document.
**How to avoid:** Add a visible adsb.fi citation + link to the public-facing README (a "Data sources" or "Acknowledgements" section is the natural spot, alongside the VENDOR.md-style font/icon attributions this project already does well). `airplanes.live`'s equivalent requirement could not be independently confirmed this session (their `/api-guide/` page 403'd on automated fetch) — flag this as an open item requiring a manual read of `https://airplanes.live/api-guide/` in a real browser before closing D-14, and note the pending commercial-use-clarification email mentioned in the phase brief may also update this determination.
**Warning signs:** A README that lists hardware/software credits (fonts, icons) but has no "data sources" section at all.

### Pitfall 5: `deploy/inkframe.env` and `firmware/main/secrets.h` need explicit `.gitignore` entries even though history is clean
**What goes wrong:** D-03 confirms no secrets have ever been committed — but without an actual `.gitignore` (D-06 confirms none exists at the repo root), a future `git add -A` after this phase could commit the real `inkframe.env` or `secrets.h` for the first time, undoing that clean history the moment the repo goes public.
**Why it happens:** The project has relied entirely on developer discipline (never `git add`ing those specific files) rather than tooling enforcement.
**How to avoid:** The new root `.gitignore` (D-06) must explicitly list `deploy/inkframe.env`, `firmware/main/secrets.h`, `.DS_Store`, `**/__pycache__/`, `*.pyc`, `firmware/build*/`, and `server/.venv/` — belt-and-suspenders even though per-subdirectory `.gitignore` files already exist for some of these (`deploy/.gitignore`, `server/.gitignore`, `firmware/.gitignore`) covering their own directories only, not the repo root's own untracked files (e.g. the currently-untracked `.DS_Store`, `.planning/research/.cache/` seen in `git status` this session).
**Warning signs:** `git status --porcelain` showing any of these files as untracked-but-stageable after the `.gitignore` is added — it should show nothing.

## Code Examples

### Full CI workflow skeleton

```yaml
# Source: composed from GitHub Actions docs (docs.github.com/actions),
# coverage.py docs, and this project's own README-documented test convention.
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          python3 -m venv server/.venv
          server/.venv/bin/pip install -r server/requirements.txt
          server/.venv/bin/pip install coverage ruff
      - name: Lint (blocking)
        run: server/.venv/bin/ruff check .
      - name: Run test suite with coverage
        run: |
          set -e
          for f in server/test_dither.py server/test_enrich.py server/test_illustrations.py \
                   server/test_pipeline_e2e.py server/test_plane_detection.py \
                   server/test_poll_loop.py server/test_render.py server/test_runway_config.py \
                   stub-server/test_poll_cycle.py; do
            server/.venv/bin/python3 -m coverage run --parallel-mode --append --source=server,stub-server "$f"
          done
      - name: Coverage report (blocking threshold)
        run: |
          server/.venv/bin/python3 -m coverage combine
          server/.venv/bin/python3 -m coverage report --fail-under=<PLANNER_SETS_FROM_MEASURED_BASELINE>

  deploy:
    needs: test
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    runs-on: ubuntu-latest
    environment:
      name: production
    steps:
      - uses: actions/checkout@v4
      - uses: webfactory/ssh-agent@v0.9.1
        with:
          ssh-private-key: ${{ secrets.VPS_SSH_KEY }}
      - run: ssh-keyscan -H "${{ secrets.VPS_HOST }}" >> ~/.ssh/known_hosts
      - run: deploy/deploy.sh "${{ secrets.VPS_SSH_TARGET }}"
```

### Measuring the real coverage baseline before setting a threshold

```bash
# Source: coverage.py docs — run this locally BEFORE writing the CI
# threshold, per CONTEXT.md's "pick a realistic starting baseline from the
# current suite's actual measured coverage, not an arbitrary round number".
cd /Users/florian/Projects/ink-frame
for f in server/test_dither.py server/test_enrich.py server/test_illustrations.py \
         server/test_pipeline_e2e.py server/test_plane_detection.py \
         server/test_poll_loop.py server/test_render.py server/test_runway_config.py \
         stub-server/test_poll_cycle.py; do
  server/.venv/bin/python3 -m coverage run --parallel-mode --append --source=server,stub-server "$f"
done
server/.venv/bin/python3 -m coverage combine
server/.venv/bin/python3 -m coverage report   # read the TOTAL % — use this as the D-09 threshold's starting point
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `git filter-branch` | `git filter-repo` | filter-branch has carried an official "do not use" warning in git's own docs for years; filter-repo is git's own recommended successor | filter-repo is faster (single-pass), safer by default (fresh-clone requirement), and has a purpose-built `--replace-text` mode exactly matching this phase's need |
| `flake8` + `black` + `isort` (three separate tools) | `ruff` (single tool, Rust-based) | Ruff has been the ecosystem's fast-moving default for several years now | One dependency, one config surface, dramatically faster — CLAUDE.md itself already names Ruff as the modern default for this stack, no need to introduce three older tools |

**Deprecated/outdated:**
- `git filter-branch`: officially superseded by `git filter-repo` for exactly this class of operation (removing sensitive strings from history).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `astral-sh/ruff-action@v3` and `webfactory/ssh-agent` are legitimate, safe-to-use marketplace actions (discovered via WebSearch, not an authoritative registry check — GitHub Actions aren't covered by the npm/PyPI package-legitimacy seam) | Standard Stack, Package Legitimacy Audit | Low — both are extremely widely used, officially-maintained-org actions corroborated across multiple independent search results; still, planner should pin an exact release tag/SHA rather than a floating major version before first use |
| A2 | `espressif/esp-idf-ci-action@v1` works with this project's existing `firmware/sdkconfig.defaults` + `sdkconfig.ee02.defaults` two-file SDKCONFIG_DEFAULTS pattern without extra glue | Architecture Patterns (implied, D-10 discretion) | Medium if D-10 is exercised — `firmware/build.sh` already proves the underlying `espressif/idf:v5.3.1` Docker image works with this exact multi-file sdkconfig setup manually; the Action wraps the same image, but its exact input-parameter mapping to `-DSDKCONFIG_DEFAULTS="a;b"` was not independently verified against `firmware/build.sh`'s specific invocation this session |
| A3 | `airplanes.live`'s exact attribution/redistribution clause matches the "educational, non-commercial" characterization found via secondary sources (their own `/api-guide/` page returned HTTP 403 to automated fetch both times attempted this session) | Common Pitfalls (Pitfall 4), Sources | Medium — if the real terms require attribution similar to adsb.fi's and it's missed, same compliance gap as the adsb.fi finding; low likelihood of a materially different/stricter term given airplanes.live's stated non-commercial community-feeder ethos, but not independently confirmed text |
| A4 | PRIM/IDFM's CGU republication clause (not independently fetched — 403 on two URLs) is immaterial to this phase because PRIM/IDFM is genuinely unused in shipped v1 code | Summary, Common Pitfalls | Low — corroborated independently via PROJECT.md and REQUIREMENTS.md both stating RER/PRIM is deferred to v2 and `server/plane/detect.py`'s only two configured providers are `airplanes.live`/`adsb.fi` (grep-verified this session, zero PRIM references in `server/`) |
| A5 | A realistic coverage `--fail-under` threshold should be set from a locally-measured baseline (not guessed) — the exact percentage number is left to the planner per CONTEXT.md's explicit instruction | Code Examples | Low — this is the CONTEXT.md-directed approach already, flagged here only because the number itself could not be measured in this research session (ruff/coverage aren't yet installed in `server/.venv`) |

## Open Questions

1. **What does airplanes.live's `/api-guide/` page actually say about attribution/redistribution?**
   - What we know: multiple secondary sources describe the API as "educational and non-commercial purposes only," 1 req/s rate limit on the ADSB-One-compatible endpoint.
   - What's unclear: the exact attribution-requirement wording (if any) — the primary source page returned HTTP 403 to both automated fetch attempts this session (likely bot-detection, not a real access restriction).
   - Recommendation: planner should add a checkpoint task to manually open `https://airplanes.live/api-guide/` in a real browser (or wait for the pending commercial-use email reply mentioned in the phase brief, which may include or reference the relevant terms) before finalizing the D-14 compliance document.

2. **Does the firmware CI build (D-10, Claude's Discretion) belong in this phase or a follow-up?**
   - What we know: `espressif/esp-idf-ci-action@v1` exists, is officially maintained, and wraps the same Docker image `firmware/build.sh` already uses locally — low marginal effort to add as a third CI job.
   - What's unclear: whether the two-tier `sdkconfig.defaults`+`sdkconfig.ee02.defaults` pattern needs an extra input parameter on the Action versus `build.sh`'s explicit `-DSDKCONFIG_DEFAULTS="a;b"` flag (not independently verified against the Action's exact parameter schema this session).
   - Recommendation: default to including it (per CONTEXT.md's own stated default), but treat the exact Action-parameter mapping as a task-level detail to confirm live during planning/execution, with `firmware/build.sh`'s already-working invocation as the fallback reference if the Action's own defaults don't line up cleanly.

3. **What coverage threshold should D-09's blocking gate actually enforce?**
   - What we know: CONTEXT.md explicitly wants a measured baseline, not a guessed round number; `coverage`/`ruff` are not yet installed in `server/.venv` as of this research session.
   - What's unclear: the actual percentage, since it requires running the full suite with coverage instrumentation once.
   - Recommendation: planner's first CI-related task should measure this baseline locally (see Code Examples above) before writing the `--fail-under=` value into the workflow YAML.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `git` | History scrub, all git operations | Yes | (repo already at 147 commits) | — |
| `git-filter-repo` | Pattern 3 history scrub | Not yet installed locally (`pip install git-filter-repo` or `brew install git-filter-repo` needed before executing this phase's history-scrub task) | — | none needed — trivial one-time install |
| `python3` (system) | N/A directly — project explicitly requires `server/.venv`'s interpreter, not bare system python3 | Yes (used to create the venv) | — | — |
| `server/.venv` | Running any `server/test_*.py`, coverage, ruff | Yes, already created, has Pillow 12.3.0 + requests 2.34.2 | — | `ruff` and `coverage` not yet installed into it — first CI-related task should add them |
| `gh` (GitHub CLI) | Creating the GitHub repo (D-01's real first prerequisite), configuring Environments/secrets, possibly the first push | Available on this machine `[VERIFIED: command -v gh]` | not version-checked this session | Manual GitHub web UI works identically for repo creation, Environment setup, and secret entry if `gh` proves insufficient for any specific step |
| Docker | Firmware CI build (`espressif/esp-idf-ci-action`, D-10), and already used by `firmware/build.sh` locally | Not checked on GitHub-hosted `ubuntu-latest` runners specifically this session, but Docker is documented as preinstalled on all GitHub-hosted Linux runners `[CITED: docs.github.com — GitHub-hosted runners software specifications]` | — | — |

**Missing dependencies with no fallback:** none — `git-filter-repo` is a trivial one-time pip/brew install, not a blocker.

**Missing dependencies with fallback:** `gh` CLI steps could fall back to the GitHub web UI if any specific `gh` subcommand proves insufficient (unlikely, but noted for completeness).

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | None (stdlib `check()`/`EXPECTED_CHECK_COUNT`/`main()` convention, hand-rolled per this project's own established pattern — explicitly not pytest) |
| Config file | none — each `server/test_*.py` / `stub-server/test_poll_cycle.py` is independently executable |
| Quick run command | `server/.venv/bin/python3 server/test_render.py` (any single file, run from repo root) |
| Full suite command | The 9-file loop shown in Code Examples above — no single existing command runs all 9 today; this phase should add one (a `scripts/run-tests.sh` or Makefile-less shell loop) both for CI and local pre-push use |

### Phase Requirement Map

This phase has no PLANE-*/DEVICE-* requirement IDs of its own (it's infra/documentation work, not a user-facing feature) — CONTEXT.md notes phase requirement IDs are "TBD (derive during discuss-phase)" and were resolved into the D-01 through D-16 decisions instead. The closest analogue to a requirements→test map is: every existing `server/test_*.py`/`stub-server/test_poll_cycle.py` already covers its own module's behavior (PLANE-01/02/03, DEVICE-03) — this phase's job is running them automatically, not writing new ones.

### Sampling Rate
- **Per task commit (during this phase's own execution):** run the full 9-file suite locally before each commit that touches CI workflow YAML, exactly as `server/README.md` already documents.
- **Per wave merge:** same full suite, now via the new CI workflow itself once it exists.
- **Phase gate:** the CI workflow going green on a real push (not just local `act`/dry-run) is this phase's own closing acceptance signal for D-07/D-09.

### Wave 0 Gaps
- [ ] No `.github/workflows/` directory exists yet — this phase creates it from scratch.
- [ ] `ruff`/`coverage` not yet installed in `server/.venv` — first task.
- [ ] No aggregate "run all 9 tests" script exists locally — worth adding as a small `scripts/run-all-tests.sh` both for CI's own use and so a contributor reading the new README can run the same command CI does.

*(This phase IS the Wave-0-gap-closing work for CI infrastructure itself — there is no pre-existing test-framework gap in the traditional sense, since the test *content* already exists and passes; the gap is purely "nothing runs it automatically yet.")*

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | This phase adds no new authentication surface (device bearer-token auth is Phase 1/2's concern, unchanged here) |
| V3 Session Management | No | N/A |
| V4 Access Control | Yes | GitHub Environment required-reviewers protection rule IS the access control for the deploy path — only an approved reviewer can let a deploy proceed |
| V5 Input Validation | No | No new user-facing input surface introduced by CI/CD/docs work |
| V6 Cryptography | Yes (adjacent) | The VPS SSH private key is a cryptographic secret; standard control is GitHub Actions' own encrypted secrets store (`secrets.VPS_SSH_KEY`), never a file committed to the repo or printed in logs — `webfactory/ssh-agent` specifically avoids leaving the key readable on disk |

### Known Threat Patterns for GitHub Actions CI/CD

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|-----------------------|
| Secret leakage via workflow log printing (`echo $SECRET`, `set -x` with secrets in env) | Information Disclosure | GitHub Actions auto-masks recognized secret values in logs, but only if referenced via `secrets.X` — never construct the value by concatenation/interpolation in a way that bypasses masking; never `echo` a secret directly even though it'll be masked, as a defense-in-depth habit |
| Floating/untagged third-party Action references (`uses: some-action@main`) enabling a supply-chain compromise if the upstream repo is compromised | Tampering | Pin every third-party action (`astral-sh/ruff-action`, `webfactory/ssh-agent`) to a specific release tag or, more strongly, a commit SHA — `actions/checkout@v4` and other GitHub-official actions are lower risk but pinning is still good practice |
| Deploy job running on a `pull_request` trigger from a fork, exposing secrets to untrusted PR code | Elevation of Privilege | This phase's `deploy` job is scoped to `push` events on `main` only (`if: github.ref == 'refs/heads/main' && github.event_name == 'push'`), never `pull_request` — forked-PR workflow runs never have access to repo secrets in GitHub's default configuration, and this phase's design doesn't need to change that |
| Committing the real VPS IP/hostname/SSH key to the repo (D-05's exact concern) | Information Disclosure | Git history scrub (Pattern 3) + all live docs referencing the VPS via `<vps-host>` placeholder or GitHub secrets, never the literal string, going forward |

## Sources

### Primary (HIGH confidence)
- Direct `curl https://pypi.org/pypi/<pkg>/json` for `ruff` (0.16.4) and `coverage` (7.15.4) version verification — fetched live this session against the PyPI registry itself.
- Direct `WebFetch` of `github.com/adsbfi/opendata`'s README — adsb.fi's own published terms (personal non-commercial use, rate limits, and the "must cite adsb.fi and include a link" attribution requirement).
- Direct repository/codebase inspection this session: `server/test_*.py`, `stub-server/test_poll_cycle.py`, `deploy/deploy.sh`, `deploy/README.md`, `server/requirements.txt`, `server/plane/detect.py`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`, `.planning/config.json`, `server/assets/fonts/VENDOR.md`, `server/assets/icons/VENDOR.md`, `git log`/`git status`/`git remote -v` on the actual repo.

### Secondary (MEDIUM confidence)
- WebSearch, cross-checked against official/primary domains: `git-filter-repo` official GitHub docs (`github.com/newren/git-filter-repo`), `astral-sh/ruff-action` official repo, `espressif/esp-idf-ci-action` official repo, GitHub Docs on Deployments and Environments (`docs.github.com`), `webfactory/ssh-agent` and `appleboy/ssh-action` marketplace listings, SIL OFL FAQ (`openfontlicense.org`/`choosealicense.com`) on OFL+other-license bundling, coverage.py `--parallel-mode`/`combine` documentation via multiple corroborating sources.

### Tertiary (LOW confidence)
- WebSearch-only, single-source, not independently fetched: `airplanes.live`'s exact `/api-guide/` terms text (page returned HTTP 403 to automated fetch twice — characterization is secondary-source-only, flagged in Open Questions and the Assumptions Log).
- WebSearch-only: PRIM/IDFM's exact CGU republication clause (both candidate URLs returned HTTP 403 to automated fetch — treated as low-priority given PRIM is unused in shipped v1 code, per Assumption A4).

## Metadata

**Confidence breakdown:**
- Standard stack (CI tooling: coverage/ruff/actions): HIGH — versions verified directly against PyPI, mechanics cross-checked across multiple official-source-backed search results
- Architecture (workflow structure, deploy gate, history scrub): HIGH — every pattern is either GitHub's own documented native feature or a well-established, officially-documented git tool
- Third-party API compliance (PRIM/adsb.fi/airplanes.live): MEDIUM overall, LOW for airplanes.live/PRIM specifically — adsb.fi confirmed via direct primary-source fetch; the other two blocked by bot-detection 403s and require manual follow-up before D-14 can be marked fully closed
- Pitfalls: HIGH — every pitfall listed was either directly observed in this session's codebase inspection (missing test files, missing `.gitignore`, adsb.fi's unmet attribution) or is a documented, well-known tool behavior (filter-repo's fresh-clone requirement, coverage's `--source` scoping)

**Research date:** 2026-08-26
**Valid until:** 30 days for the GitHub Actions/CI mechanics (stable, slow-moving surface); 7 days for the `airplanes.live`/PRIM open items specifically, since they depend on a pending external email reply and un-fetched primary sources that should be re-checked before this phase closes
