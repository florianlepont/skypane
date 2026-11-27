# Phase 66: Security Audit - Context

**Gathered:** 2026-11-27
**Status:** Ready for planning

<domain>
## Phase Boundary

One structured security audit of the whole platform (requirement SEC-AUD-01). Output: a written audit per area, fixes for high findings (each small, separate, tested), secrets check with rotation steps, and a list of remaining risks and follow-ups. Not in this phase: legal review (SEED-015), a third-party penetration test, new features, and the structural review of the databases (Phase 67).

</domain>

<decisions>
## Implementation Decisions

### Handling of findings (the repository is PUBLIC until Phase 70.1)
- **D-01:** No unfixed high or critical finding is written in the repository (commits, PR titles and bodies, comments, planning documents, files). Such findings are reported to the owner in the chat only (short, French), fixed, and described in the repository only after the fix is deployed, without secrets or exploit steps that still work.
- **D-02:** Medium and low findings are recorded with category, location and recommendation, with no working exploit recipe. In doubt, keep it out of the repository and tell the owner.
- **D-03:** A secret, token, key or personal data found anywhere: tell the owner file and line, never repeat the value, never commit it.

### Owner decisions of this discuss step
- **D-04:** Audit by Claude only now. An outside reviewer (penetration test) is recommended before any commercial launch and is listed as a follow-up, not scheduled here.
- **D-05:** No test against the live production host beyond the owner's normal use: no scan, no fuzzing, no login attempts, no passive probing. A specific test needs the owner's explicit written confirmation for that test.
- **D-06:** Only medium and low findings may wait for a later milestone (with their recommendation recorded). Every high or critical finding is fixed and tested in this phase, or accepted by the owner in writing with the reason.
- **D-07:** Scope as listed in the roadmap, confirmed unchanged: sign-in and sessions; roles and default-deny (route x role x owner matrix); device protocol and enrolment secrets; firmware signing, update and rollback; companion input handling (uploads, forms, headers, XSS, injection, CSRF, path traversal, file types and sizes); server and deploy pipeline (systemd units, Caddy, `skypane.env`, CI permissions, manual `deploy.yml`, Mac runner kit, `gh release download`); dependencies and pinned hashes; backups and their content; logs and what they leak; the rule that the administrator never sees users' photos; data-source terms with a security angle; databases for access and integrity only.

### Method and fixes
- **D-08:** Read code and configuration; run existing tests; add a test for every fixed finding. Read-only checks only.
- **D-09:** Each fix is a small separate change with a test, deployed through the normal manual deploy approved by the owner. Never approve or run a production deploy from a session.
- **D-10:** Must not break: golden hashes of the legacy render, `stub-server/test_phase47_freeze.py`, the live frame, the access rules of Phases 54, 55 and 60, English and French parity.
- **D-11:** Work on a branch with draft PRs. Check open PRs before touching a file. Playwright browser tests may not run here: rely on CI.
- **D-12:** Owner wants short answers in French; written artefacts in English.

### Claude's Discretion
Audit document layout, order of areas, how areas are split between reviewers, severity scale wording, test design for each fix.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase definition
- `.planning/workstreams/v1-2/ROADMAP.md` section "Phase 66" — goal, scope, success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — SEC-AUD-01
- `.planning/workstreams/v1-2/STATE.md` — current position

### Prerequisites already done
- `.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-INVENTORY.md` — what has been public, secret scan decisions
- `.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-08-SUMMARY.md` — exposure scan tool
- `.planning/workstreams/v1-2/phases/70-private-repository-and-ci/70-CONTEXT.md`, `70-EVIDENCE.md`, `70-POSTFLIP.md` — deploy, signing and CI setup
- `.planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/` — access rules (must not break)
- `.planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/` — access rules (must not break)
- `.planning/workstreams/v1-2/phases/60-device-co-management/` — access rules (must not break)

### Repository documents
- `SECURITY.md`, `COMPLIANCE.md`, `ARCHITECTURE.md`, `deploy/README.md`, `firmware/SIGNING.md`, `firmware/VENDOR.md`, `hardware/BOM.md`
- `scripts/exposure_scan.py` — value-free tree and history scan
- `.github/workflows/` (ci.yml, deploy.yml, firmware.yml, firmware-release.yml, firmware-chain-check.yml)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/exposure_scan.py`: secret scan reusable for the secrets check.
- `companion/test_suite_guards.py`, `companion/conftest.py`, `test-support/companion_app_server.py`: shared fixtures for companion tests of fixed findings.

### Established Patterns
- Tests assert served HTML/CSS/JS or a browser, never source text or `.planning/`; pytest-socket blocks non-loopback traffic.
- Gates: ruff, mypy module list, function-size max 80 lines, comment-history guard (no plan, ticket or phase IDs in comments), coverage floor, hash-locked `server/requirements*.txt`.

### Integration Points
- Companion: `companion/auth.py`, `access.py`, `app.py`, `console_*.py`, `export_api.py`, `auth0_management.py`.
- Device protocol: `stub-server/byos_server.py`, `server/fleet_db.py`, `server/fleet_sessions.py`, `server/pairings.py`, `server/firmware_registry.py`.
- Storage: `server/history_db.py`, `server/state_store.py`, fleet database, per-device JSON state, backup units under `deploy/`.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the roadmap and the rules above.

</specifics>

<deferred>
## Deferred Ideas

- Outside penetration test before any commercial launch (follow-up in the audit).
- Follow-ups for the next milestones: photo privacy, Wi-Fi setup, update policy (listed in the audit's remaining-risks section).
- Structural review of the databases: Phase 67.

</deferred>

---

*Phase: 66-security-audit*
*Context gathered: 2026-11-27*
