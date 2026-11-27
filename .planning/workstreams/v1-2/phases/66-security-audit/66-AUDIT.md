# SkyPane Security Audit (Phase 66)

Requirement: SEC-AUD-01. Audited on 2026-11-27, branch `phase-66-security-audit`.

This document is written for a public repository. It records what was checked, how, and the result, for every area of the platform. It holds no secret value, no host or address, and no step that could be used against a running system.

## Summary

- **Scope:** the whole platform: sign-in and sessions, roles and default-deny access, the device protocol and enrolment secrets, firmware signing, update and rollback, companion input handling, the server and deploy pipeline, dependencies, backups, logs, the privacy rule for photos, data-source terms, and the databases (access and integrity only).
- **Method:** one reviewer (Claude), reading code and configuration and running the existing local test suites. Five section files hold the detail: `sections/01-signin-sessions-roles.md` to `sections/05-secrets-backups-logs-data.md`.
- **Limits:** read-only. No request was sent to the production host (no scan, no fuzzing, no login attempt, no passive probe). No deploy and no workflow run was made from the audit. Browser tests and the firmware host tests were not run locally and rely on CI. No outside reviewer took part; an outside penetration test is listed below as a follow-up. Legal and regulatory review (SEED-015) and the structural review of the databases (Phase 67) are out of scope.
- **Severity scale:** critical, high, medium, low, informational, as defined in `66-AUDIT-PROTOCOL.md`.

### Result at a glance

| Severity | Count | State |
|----------|-------|-------|
| Critical | 0 | No critical finding |
| High | 0 | No high finding |
| Medium | 3 (D-1, S-2, S-3) | D-1 and S-2 fixed and deployed (2026-11-27); S-3 fix merged, owner-side Mac step pending (see "Medium items") |
| Low | 21 | Recorded as recommendations |
| Informational | 2 | Recorded |

D-1 and S-2 are the same weakness seen from two areas (deploy approval), so there are two distinct medium topics.

No high or critical finding exists, so there is nothing held back and the deploy-confirmation step for such items does not apply. Nothing in this document describes an undeployed high-severity weakness.

## Success criteria

| # | Criterion | Status |
|---|-----------|--------|
| 1 | A written audit records what was checked, how, and the result, for each area | Met: the chapters below and the five section files |
| 2 | Each finding has a severity; every high one is fixed and tested or accepted in writing | Met: no high or critical finding. Every finding carries a severity |
| 3 | Fixes keep the golden hashes, the freeze test and the live frame's release path, and are deployed through the gated pipeline | Met for the deploy fix: pull requests #627 and #629 are merged, the owner-side settings are done, and one manual deploy through the gated workflow paused for approval and succeeded (2026-11-27). The backup fix (#628) is merged; its Mac-side setting is the one open owner step. Both changes touch only the deploy workflow, its tests, the backup pull script and the deploy README |
| 4 | Secrets checked, rotation steps written, token scopes smallest that work | Met: see "Secrets and rotation". No unexplained hit in the tree or the full history |
| 5 | Remaining risks and follow-ups for the next two milestones are listed | Met: see "Remaining risks and follow-ups" |

## Area chapters

Each chapter gives what was checked, how, and the Result. The Result value is the same set in every section file (`no finding` or `medium/low recorded`); the item tables below say which items exist.

### 1. Sign-in and sessions

- **What:** the authorization-code flow with PKCE, state and nonce handling, ID-token claim validation, redirect targets after sign-in, cookie attributes, session lifetime, rotation and logout, the rate limit on sign-in starts, the management credential.
- **How:** code reading and the existing non-browser tests for these modules (2624 passed locally).
- **Result:** medium/low recorded (A-01, low).

### 2. Roles and default-deny access

- **What:** the route x role x owner matrix, owner-only routes, co-manager grants, device scope, role and disabled state read from the local database on every request, CSRF gating.
- **How:** code reading; the access matrix test enumerates the registered route table and fails on a route without a policy row, so default-deny is proven by test. No test had to be added.
- **Result:** medium/low recorded (A-01 is the only item of the sign-in and access chapters).

### 3. Device protocol and enrolment secrets

- **What:** device authentication per endpoint, enrolment secret storage and comparison, device token lifecycle, frame pairing codes and their lockouts, request size and timeout limits, path handling, error messages.
- **How:** code reading; freeze and golden render suites (115 passed), device and pairing selection (456 passed, 1 skipped), unmodified.
- **Result:** medium/low recorded (DP-1, DP-2, DP-3, DP-4, DP-6, DP-8).

### 4. Firmware signing, update and rollback

- **What:** the signature on release images, the update path on the device, the registry and its release rules, the release workflows, the trial-boot and rollback behaviour.
- **How:** code and document reading; firmware, publish-script and certificate selection (283 passed). Firmware host tests rely on CI. No key file was opened.
- **Result:** medium/low recorded (DP-5, DP-7).

### 5. Companion input handling

- **What:** 124 registered routes (42 POST) all behind the anti-forgery token, request size limits, the upload path, path handling, output escaping, response headers, redirect targets, data access, error pages, the export API.
- **How:** code reading, route table inspection (no server started), targeted tests (262 passed, 1 skipped). Browser tests rely on CI.
- **Result:** medium/low recorded (C-01, C-02, C-03, C-04).

### 6. Server and deploy pipeline

- **What:** the six systemd units and their sandbox options, the reverse-proxy template, provisioning, the five workflows (permissions, triggers, pinned actions, secret handling), the manual production deploy workflow, release download, the Mac runner kit.
- **How:** configuration and document reading only. No real environment file was opened; no workflow was run.
- **Result:** medium/low recorded (D-1, D-2, D-3, D-5, D-6).

### 7. Dependencies and pinned hashes

- **What:** both lock files carry hashes for every entry, installs require hashes, no VCS or URL dependency, the firmware build container is pinned by tag.
- **How:** script check of the lock files and reading of the CI and activation steps. A known-vulnerability check was not run: no offline-capable tool was available and nothing was installed for the audit.
- **Result:** medium/low recorded (D-3, D-4).

### 8. Backups and their content

- **What:** content, destination, permissions, transport, retention and restore. The archive includes both databases (online copy with integrity check), per-device state, device tokens, enrolment hashes, calendar feed secrets, artwork and rendered panels. User photos are not part of it; the environment file is not included. The off-host copy is pulled by a restricted key, and each archive is checksum-verified on the receiving machine.
- **How:** code and unit reading, local tests of the backup job, gate and key installer (passing). No production restore was run.
- **Result:** medium/low recorded (S-3).

### 9. Logs and what they leak

- **What:** companion and device-server request hooks log method and path only, never headers, cookies, bodies or query strings; the reverse proxy drops the sign-in query keys from its log; no logging call site writes a token, secret, cookie or authorization header.
- **How:** review of every logging call class and of the log configuration.
- **Result:** medium/low recorded (S-4, DP-3, DP-4).

### 10. The administrator never sees users' photos

- **What:** photo mode is not built, so no user photo is stored or served today. Per-device image routes serve server-rendered images and follow the shared rule that an administrator reaches any existing device; the export API carries no image; the backup holds no user photo.
- **How:** reading of the routes, export API and backup include list.
- **Result:** medium/low recorded. The rule needs its own access kind, storage location and test when photos are built (v1.4); see follow-ups.

### 11. Data-source terms

- **What:** the default provider order, per-provider request spacing, the opt-in provider, the user agent, credits, and the provider whose terms forbid operational use (not reached by shipped code). No flight-data key is in use.
- **How:** comparison of the compliance document with the code.
- **Result:** no finding.

### 12. Databases (access and integrity only)

- **What:** file modes, writers, journal settings, read-only open paths, schema-newer-than-code refusal, atomic JSON writes.
- **How:** code reading. Structure, indexes and migrations belong to Phase 67.
- **Result:** medium/low recorded (S-5).

## Medium items

| ID | Area | Recommendation | State |
|----|------|----------------|-------|
| D-1, S-2 | Deploy approval: the deploy secrets are repository-level, so any workflow on any branch can read them, and the typed confirmation is an accident guard only | Bind the deploy job to a protected `production` environment with a required reviewer; move the secrets there | Fixed and deployed: #627 merged, secrets moved to the protected environment with a required reviewer and a `main` branch rule, repository-level copies deleted, the previous deploy key revoked on the host, one gated deploy succeeded (tests listed in the ledger) |
| S-3 | Backups at rest: the off-box copy lives on a Mac volume whose encryption was neither stated nor checked | State and test the disk-encryption requirement; consider encrypting archives before the pull | Fix merged, Mac-side owner step pending: #628 adds an opt-in disk-encryption check to the pull and documents the requirement. Encrypting archives before the pull stays a follow-up |

Neither fix is merged or deployed. They are recorded as proposed, not as fixed. Details and the owner-side steps are in `66-FIX-LEDGER.md` and under "Owner actions".

## Low and informational items

| ID | Category | Recommendation | Decision |
|----|----------|----------------|----------|
| A-01 | Hardening (anti-forgery value stable per session) | Consider a per-session random value if forms render in less trusted contexts | Recorded for a later milestone |
| DP-1 | Information exposure (registration state) | Same answer for unregistered address and wrong secret | Recorded |
| DP-2 | Credential storage (device token stored in clear) | Store a hash, with a transition for issued tokens | Recorded |
| DP-3 | Log integrity (device-supplied log text) | Escape control characters, cap length | Recorded |
| DP-4 | Information exposure (image links are capability links, path logged) | Log the route class only, or document it; ties to photo privacy | Recorded, carried to v1.4 |
| DP-5 | Update policy (software-only anti-rollback) | Raise the floor in any security release; write the rule into the update policy | Recorded, carried to the update policy |
| DP-6 | Availability hardening (enrolment attempts) | Rate limit at the reverse proxy | Recorded |
| DP-7 | CI hardening (checkout credentials) | Do not persist credentials in the chain-check checkout | Recorded |
| DP-8 | Observation (advertised image host from the request) | Use a configured public host | Recorded (informational) |
| C-01 | Documentation drift (comments about tokens) | Update the comments | Recorded |
| C-02 | Hardening (inline styles allowed by the content policy) | Move to classes so the allowance can go | Recorded |
| C-03 | Resource limits (decode pixel ceiling) | Lower the ceiling | Recorded |
| C-04 | Defence in depth (no Origin and no fetch-site header accepted) | None required; keep covered by tests | Recorded (informational) |
| D-2 | Supply chain (no checksum check between release download and transfer) | Verify the published checksums in the workflow | Recorded |
| D-3 | Supply chain (images pinned by tag, not digest) | Pin by digest | Recorded |
| D-4 | Dependency hygiene (no known-vulnerability check) | Scheduled check over the lock files in CI | Recorded, follow-up |
| D-5 | Hardening (companion unit has no IP filter) | Restrict outbound destinations at the firewall | Recorded |
| D-6 | Hardening (no request body limit at the proxy) | Add one | Recorded |
| S-1 | Credential breadth (runner registration token) | Short-lived, Keychain only; revisit with more repositories | Recorded |
| S-4 | Personal data in logs (client address and MAC retention) | Document retention; consider fewer rolled files | Recorded |
| S-5 | Integrity monitoring (no scheduled check of the history database) | Quick integrity check in the health view or nightly | Recorded |
| S-6 | Operator output (short hash prefix printed by a CLI) | Print nothing or the full MAC | Recorded |
| S-7 | Personal data in history (maintainer contact in commit metadata and notes) | Already decided in the earlier inventory; revisit if the repository stays public | Recorded |

## Secrets and rotation

### Secrets check

The scan tool (`scripts/exposure_scan.py`) was run over the working tree and over the full history (after completing a shallow clone). Output was kept outside the repository, and only counts are recorded.

| Class | Tree rows | History rows | Unexplained |
|-------|-----------|--------------|-------------|
| Secret-shaped assignment | 15 | 24 | 0 (names of variables, UI attributes, fixtures built from readable words) |
| Literal bearer text | 1 | 1 | 0 (prose in a planning note, decided earlier) |
| Private-key, cloud-key, forge-token, chat-token classes | 0 | 0 | 0 |
| E-mail address (non-noreply) | 108 | 280 | 0 (reserved test domains, placeholders, a public provider contact in the compliance document, the maintainer contact) |
| Public IPv4 literal | 24 | 42 | 0 (version-like numbers, test and documentation addresses) |

Conclusion: no secret in the repository or its history. The only personal data kept is the maintainer contact in commit metadata and a few planning notes (S-7).

### Personal-data locations (file and line only)

Not values. Where a maintainer or provider contact appears in tracked files:

- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-UAT.md`, lines 26 and 28
- `.planning/workstreams/v1-2/phases/64-second-hardware-in-production-build-release-deploy-and-parit/64-WALKTHROUGH.md`, line 25
- `COMPLIANCE.md`, line 278 (a public provider contact, not personal data of the maintainer)

Commit author metadata also carries the maintainer contact. All other e-mail rows are reserved test domains or placeholders in tests, scripts and notes. Line numbers refer to the tree at the time of the audit.

### Rotation steps and smallest scopes

Each class has a generic rotation procedure and a smallest working scope in `sections/05-secrets-backups-logs-data.md` (table "Rotation and scopes"): the sign-in application credential, the invitation (machine-to-machine) credential, the per-device enrolment secret, the device bearer token, the firmware signing key, the deploy SSH key with its pinned host key and target, the runner registration token, the backup pull key, the read-only export token, the calendar feed address, the optional language-model key, and per-run workflow tokens. Summary of the generic order for every credential held in the server environment file: create the new value at the provider, edit the one line in the file, restart the affected service, delete the old value at the provider.

Scope check, documented versus used:

- the invitation credential has exactly the two permissions it uses, no unused scope;
- all five workflows declare `contents: read` only, and the calls they make are read operations;
- the runner registration token is broad by nature (the forge offers no narrower scope for runner registration), recorded as S-1.

## Remaining risks and follow-ups

For the next milestones:

1. **Photo privacy (v1.4).** Per-device routes admit the administrator for any frame today. Stored user photos need their own access kind that excludes the administrator, a storage location outside what the administrator-facing routes and the export read, an explicit decision on whether photos enter the backup, and a behaviour test that the administrator cannot fetch another user's photo. Review image link exposure and logging (DP-4) at the same time.
2. **Wi-Fi setup.** The setup flow will handle the home network password and the first enrolment secret; it needs its own threat check (transport, where secrets are held, how a lost device is revoked).
3. **Update policy, including anti-rollback.** Decide floor raising for security releases (DP-5), how a lost or compromised signing key is handled in the field, and whether to enable hardware secure boot and flash encryption (intentionally off today).
4. **Outside penetration test before any commercial launch.** This audit is a single-reviewer, read-only review; it did not test the live system.
5. **Auth0 tenant self sign-up check.** The sign-in design relies on invitation only; confirm in the tenant settings that self sign-up is disabled (not visible from code).
6. **Known-vulnerability check in CI** over the lock files (D-4); it was not run in this audit.
7. **Encrypted off-box backups.** Decide the at-rest policy beyond the opt-in disk-encryption check (S-3), for instance encrypting archives to a public key before the pull.
8. **Deploy approval model.** Complete the owner-side steps of the environment gate (D-1, S-2); revisit before any additional person gets repository write access.
9. **Structural database review:** Phase 67. **Legal and regulatory review:** SEED-015, out of scope here.
10. **Repository history scan:** re-run on a full mirror after the repository becomes private and after any history change (the repository is public until the planned switch).
11. Open low items above stay as recommendations; none blocks a release.

## Owner actions

1. Done (2026-11-27): #627 merged, secrets in the `production` environment with a required reviewer, repository-level copies deleted, old deploy key revoked, one gated deploy succeeded.
2. Open: #628 is merged; turn disk encryption on for the Mac that holds the backup copy, add the opt-in setting to the Mac backup configuration, and run the pull once.
3. Confirm in the Auth0 tenant that self sign-up is disabled.
4. Decide which low items to schedule, and the at-rest policy for backups (S-3 follow-up).
5. Plan an outside penetration test before any commercial launch.
6. Approve this document while the repository is public (final checkpoint of the plan).
