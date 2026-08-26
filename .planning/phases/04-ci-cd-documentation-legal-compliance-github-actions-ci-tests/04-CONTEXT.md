# Phase 4: CI/CD, Documentation & Legal Compliance - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Turn the working, tested codebase (Phases 1-3) into a properly shipped open-source project: GitHub Actions CI (tests + lint + coverage, blocking) with a manual-approval-gated deploy to the real OVH VPS, a README, a LICENSE, documented third-party API compliance, and consolidated asset attribution. Project-hygiene/shippability work, orthogonal to the on-device experience Phases 1-3 & 5 build (ROADMAP.md's Phase 4 note).

</domain>

<decisions>
## Implementation Decisions

### Repository & visibility
- **D-01:** This repository has never been pushed to a remote (`git remote -v` is empty). Phase 4's first real prerequisite is creating the GitHub repo.
- **D-02:** Repository will be **public**. Rationale (user): willing to show/share the project.

### Pre-publish history hygiene (real, not theoretical - live-checked)
- **D-03:** No actual secrets (`deploy/inkframe.env`, `firmware/main/secrets.h`) have ever been committed - verified via `git log --all -p` on both paths, clean. This discipline holds and must continue.
- **D-04:** The real VPS's public IP (`<vps-ip>`) and hostname (`<public-host>`) ARE already committed, across `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/phases/02-plane-view-end-to-end-slice/02-05-SUMMARY.md`, `.planning/phases/02-plane-view-end-to-end-slice/02-VERIFICATION.md`, and `deploy/README.md`.
- **D-05 (user decision):** These must NOT be visible once public ("j'aimerais que ces informations sensibles ne soient pas visibles si possible"). Since this repo has **no remote yet and no collaborators**, the clean fix is available: scrub the real IP/hostname from every historical commit (not just HEAD) before the first push to GitHub - either a full history rewrite (`git filter-repo` targeting the literal strings) or squashing local history into a fresh initial commit with the strings redacted first. **Left to planner/research to pick the exact mechanism** - the requirement is that neither the real IP nor the real hostname exist in any commit ever pushed publicly. Live docs should reference the VPS by a placeholder (e.g. `<vps-host>`) or via `deploy/inkframe.env`-style external config, matching the existing "real values never in git" pattern this project already uses for secrets.
- **D-06:** No `.gitignore` exists anywhere in this repo (verified - `ls .gitignore` finds nothing). Must be added before the public push: at minimum `.DS_Store`, Python `__pycache__`/`.venv`, ESP-IDF `firmware/build*/`, and an explicit (belt-and-suspenders, even though discipline has held so far) `deploy/inkframe.env` / `firmware/main/secrets.h` ignore pair.

### CI pipeline (GitHub Actions)
- **D-07:** Runs the existing test harnesses under `server/.venv` - note these are **not pytest**, they're custom `check()`/PASS-FAIL/`EXPECTED_CHECK_COUNT` harnesses invoked as `python3 server/test_*.py`, each exiting 0/1 (see `server/test_render.py`, `server/test_dither.py`, `server/test_poll_loop.py`, `server/test_enrich.py`, `server/test_plane_detection.py`, `server/test_runway_config.py`, `server/test_pipeline_e2e.py`). CI must invoke each one as its own step (or a loop), not assume a pytest collector will find them.
- **D-08:** Dependencies pinned in `server/requirements.txt` (Pillow==12.3.0, requests==2.34.2) - CI installs from this file, doesn't re-derive versions.
- **D-09 (user decision, "Bloquante"):** Lint (tool choice left to planner/research - Ruff is the modern default for this stack) and coverage are **blocking**: the CI run must fail if lint fails, or if coverage regresses below a threshold the plan sets. This is stricter than the researcher's first-instinct "report only" recommendation - the user explicitly chose blocking despite being a solo project.
- **D-10:** Firmware (ESP-IDF/CMake under `firmware/`) is a separate build system from the Python server. Whether Phase 4's CI also builds firmware (Espressif publishes an official `espressif/esp-idf-ci-action` for exactly this) is **Claude's Discretion** - not discussed live, no strong signal either way. Default recommendation: include it if it's low-effort via the official action; otherwise defer to a follow-up.

### Deploy automation
- **D-11 (user decision):** Deploy triggers on merge to `main`, but requires a **manual approval step** before it actually runs against the real VPS - implement via GitHub Environments' required-reviewers protection rule, not a bare `workflow_dispatch` or an unprotected auto-deploy job. Rationale (user, implicit in the choice): this VPS serves a real physical device on the wall; tests passing doesn't guarantee the render pipeline looks right on real glass, so a human checkpoint before every prod push is wanted.
- **D-12:** The deploy job itself should wrap the existing `deploy/deploy.sh` (rsync + service restart) rather than reimplementing its logic in the workflow YAML - that script is already tested/working (see `deploy/README.md`). CI needs the VPS SSH key as a GitHub Actions secret and must never print/log it.

### Legal / licensing
- **D-13 (user decision):** License is **MIT**. Compatible with the already-vendored asset licenses (SIL OFL 1.1 for Inter/Zilla Slab/PT Serif fonts, see `server/assets/fonts/VENDOR.md`; check `server/assets/icons/VENDOR.md` for icon licensing before finalizing the LICENSE file's scope note).
- **D-14 (user decision, from the earlier scope-confirmation question):** "Legal information" scope = (1) LICENSE file, (2) third-party API terms-of-use compliance check/documentation for AeroDataBox (unused - PROJECT.md's D-P... reversed decision to local ADS-B, confirm this is actually true in the shipped code before writing "not used"), PRIM/IDFM (used for the deferred RER view research, confirm current usage status), and the ADS-B aggregators (adsb.fi/airplanes.live - confirm no raw-data-republishing clause is violated by rendering derived departure-board info), (3) consolidated/verified asset attribution - largely already done via `server/assets/fonts/VENDOR.md` and `server/assets/icons/VENDOR.md`, this phase's job is to verify completeness, not redo it.

### Documentation
- **D-15:** README must let a newcomer actually build/deploy from scratch - covers hardware BOM, firmware flash, server setup, and a pointer to `deploy/README.md` for the VPS provisioning flow (not a duplicate of it).
- **D-16 ("architecture" tracking, user-requested):** A pre-existing `.planning/research/ARCHITECTURE.md` exists but is **generic domain research from project inception** (2026-08-04, before any of this was built) - not a description of what's actually shipped. Phase 4 needs a real, current architecture doc/README section describing the actual built system (device firmware state machine, server render pipeline, VPS deployment topology) - the old research doc is a useful reference, not something to just re-publish.

### Claude's Discretion
- Exact lint tool (Ruff recommended) and coverage tool (pytest-cov's coverage.py engine works fine even without using pytest as the runner) - not discussed live.
- Whether firmware CI build is in-scope for this phase or deferred (D-10).
- Exact coverage threshold percentage - the planner should pick a realistic starting baseline from the current suite's actual measured coverage, not an arbitrary round number.
- Git-history-scrub mechanism (filter-repo vs. fresh squashed history) - D-05.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deploy / infrastructure (existing, must not be reimplemented)
- `deploy/README.md` — the real OVH VPS-1 provisioning + deploy flow, provider-agnostic scripts, SSH login-method handling (root vs. passwordless-sudo `ubuntu` user)
- `deploy/deploy.sh` — the repeatable code-push script the CI deploy job must wrap, not replace
- `deploy/provision.sh` — one-time VPS setup, not part of ongoing CI but referenced by README
- `deploy/inkframe.env.example` — template for the real, gitignored production env file; documents the "never commit real secrets" pattern this phase must preserve for `.gitignore` (D-06)

### Test suite (CI must invoke these correctly)
- `server/test_render.py`, `server/test_dither.py`, `server/test_poll_loop.py`, `server/test_enrich.py`, `server/test_plane_detection.py`, `server/test_runway_config.py`, `server/test_pipeline_e2e.py` — custom harnesses, not pytest (D-07)
- `server/requirements.txt` — pinned dependency versions CI installs from

### Asset attribution (verify completeness, don't redo)
- `server/assets/fonts/VENDOR.md` — font provenance (Inter, Zilla Slab, PT Serif), SIL OFL 1.1
- `server/assets/icons/VENDOR.md` — icon/illustration provenance
- `server/assets/icons/illustrations/HANDOFF.md` — per-airline illustration generation record (note: `server/assets/icons/illustrations/VENDOR.md` was flagged as a real gap by the 03-03-PLAN.md reconciliation this session - still doesn't exist)

### Project/requirements context
- `.planning/PROJECT.md` — architecture/stack decisions, including the AeroDataBox-vs-local-ADS-B reversal (verify current status for D-14's compliance check)
- `.planning/REQUIREMENTS.md` — v1/v2 scope boundary
- `.planning/research/ARCHITECTURE.md` — pre-project generic domain research (D-16: reference only, not current-state documentation)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `deploy/deploy.sh` / `deploy/provision.sh`: already-working, tested deploy automation - the CI deploy job should shell out to these, not duplicate their rsync/systemd logic.
- `server/requirements.txt`: authoritative pinned dependency list for CI's Python setup step.

### Established Patterns
- Every `server/test_*.py` follows the same `check(name, fn)` / PASS-FAIL / `EXPECTED_CHECK_COUNT` convention with a final `N/M checks pass` line and a 0/1 exit code - CI's test step(s) should treat each file's own exit code as the pass/fail signal, matching how this session ran them locally (`server/.venv/bin/python3 server/test_X.py`).
- Secrets discipline: real credentials live only in `deploy/inkframe.env` (VPS-local, gitignored by convention though no actual `.gitignore` enforces it yet - D-06) and `firmware/main/secrets.h` (gitignored the same way) - never in the repo. CI's VPS SSH key follows the same never-committed, GitHub-Actions-secret-only pattern.

### Integration Points
- The CI deploy job's target is the real, already-provisioned OVH VPS-1 (`<public-host>`, but see D-05 - this exact string should not end up in the new public history) running `inkframe-byos.service` and `inkframe-poll.timer` under systemd, reverse-proxied by Caddy.

</code_context>

<specifics>
## Specific Ideas

No specific UI/copy requirements - this is infrastructure/documentation work. The concrete decisions above (public repo, manual-approval deploy gate, MIT license, blocking quality/coverage, history scrub before first push) are the specifics.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. (Firmware CI build, D-10, is not deferred to another phase, just left as an in-phase discretion call for the planner.)

</deferred>

---

*Phase: 4-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Context gathered: 2026-08-26*
