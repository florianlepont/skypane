# Area: Secrets, backups, logs, databases (access and integrity) and data-source terms

## Scope read

- `scripts/exposure_scan.py` (tree and history modes), the earlier private-repository inventory, `SECURITY.md`, `COMPLIANCE.md`.
- `deploy/` units (`skypane-*.service`, backup service and timer), `deploy/provision.sh`, `deploy/Caddyfile`, `deploy/skypane.env.example`, `deploy/README.md`, `deploy/runner/README.md`, `deploy/backup/` (snapshot script, forced-command gate, key installer).
- `.github/workflows/*.yml` (secret names and `permissions:` blocks only).
- `firmware/SIGNING.md`.
- `server/history_db.py`, `server/fleet_db.py`, `server/state_store.py`, `server/atomic_io.py`, `server/plane/detect.py`.
- `companion/auth0_management.py`, `companion/export_api.py`, the HTTP log hooks of the companion and the device server.
- Logging call sites in `server`, `stub-server` and `companion` (tracked files only).

## Method

Code and configuration reading only. No request to the production host, no production file opened. Scan output was written outside the repository and is not reproduced here; only counts per class are recorded. Existing local tests for the scan tool, the backup job, the backup gate, the key installer and the atomic writer were run.

## Checks performed

- [x] Full history available locally (a shallow clone was completed first), then the tree scan and the history scan were run.
- [x] Every scan hit classified: documented allow-list item from the earlier inventory, test fixture or placeholder, or unexplained.
- [x] Rotation procedure and smallest working scope written for each secret and token class.
- [x] Documented scope of each token compared with the calls the code makes.
- [x] Backup content, destination, permissions, retention, restore test and integrity check read.
- [x] Logging call classes and the web server access logs checked for credentials, headers, bodies, addresses and locations.
- [x] Database file modes, writers, journal and integrity settings, atomic JSON writes read (structure left to Phase 67).
- [x] Data-source terms compared with the code (provider list, opt-in provider, request spacing, user agent, key handling).

### Scan counts per class

| Class | Tree rows | History rows | Allow-list item | Fixture or placeholder | Unexplained |
|-------|-----------|--------------|-----------------|------------------------|-------------|
| Secret-shaped assignment | 15 | 24 | 0 | 24 (names of environment variables, UI attribute names, test fixture values built from readable words) | 0 |
| Literal bearer text | 1 | 1 | 1 (prose in a planning note, decided earlier) | 0 | 0 |
| Private-key, cloud-key, forge-token and chat-token classes | 0 | 0 | 0 | 0 | 0 |
| E-mail address (non-noreply) | 108 | 280 | 0 | 108 / 280 (reserved test domains, project-owned invalid domain, a public provider contact in the compliance document) | 0 |
| Public IPv4 literal | 24 | 42 | 0 | 24 / 42 (version-like numbers, test addresses, hardware notes, planning notes) | 0 |

Notes: the tree counts match the earlier inventory except for three more address rows in newly added test files. The history counts are higher than the earlier shallow run because the full history is now visible; the additional rows are the same kinds of items. A maintainer contact address appears in commit author metadata and in a few planning notes; the earlier inventory already decided to leave it and the repository is to become private.

## Rotation and scopes

No value, key fragment or hash prefix is recorded. "Location" is a place name only.

| Class | Location | Readable by | Smallest working scope | Rotation, generic steps | What breaks during rotation |
|-------|----------|-------------|------------------------|-------------------------|-----------------------------|
| Sign-in application credential (Auth0 web application) | Server environment file, root-only mode | Root, and the service user through the unit's environment | Authorization code flow with PKCE, exact callback and logout URLs, sign-ups disabled | Rotate the client credential in the tenant dashboard, edit the one line in the environment file, restart the companion | Sign-in fails between the dashboard change and the restart; existing local sessions are unaffected |
| Invitation (machine-to-machine) credential | Same environment file | Same | Exactly two Management API permissions, `create:users` and `create:user_tickets` | Rotate in the dashboard, edit the file, restart the companion. Revoke by deleting the application or its authorization | Invitations report "not configured" until restarted; sign-in is unaffected |
| Per-device enrolment secret | Held in the device flash; only its SHA-256 is stored on the server (registry file and fleet database, mode 0600 / group-restricted) | Device owner of the hardware; server stores the hash only | One secret per device, compared in constant time | Register a new hash for the MAC with the CLI, re-flash or re-provision the device with the new secret, then revoke its issued token (stop the device server first) | The device cannot enrol until re-provisioned; its existing token keeps working until revoked |
| Device bearer token | Server state (issued at enrolment) | Service user | One token per device | Revoke with the CLI; the device re-enrols with its secret on the next wake | One wake cycle without a refreshed image |
| Firmware signing key | Owner's encrypted vault only, never in the repository or a workflow | Owner | Used only on the owner's machine by the signing script; the public key is committed | Sign a transition release with the old key, ship it, then sign later releases with the new key. If the old key is lost first, recovery needs a USB flash of a factory image | Devices only accept images signed by the key in the running app; a missed transition forces USB recovery |
| Deploy SSH key, pinned host key and target (repository secrets) | Repository secrets | Any workflow on any branch of the repository (documented limit of the plan tier) | A dedicated key used only by the deploy workflow; restrict the key's `authorized_keys` line on the host (forced command, no forwarding) as far as the deploy script allows | Generate a new key pair, replace the `authorized_keys` line on the host, update the repository secret, update the pinned host key if the host key changed | Deploys fail until the secret and the host line match; the laptop break-glass route stays available |
| Self-hosted runner registration token | Keychain entry on the owner's Mac | Owner | Fine-grained, single-repository, Administration read and write only (needed to register runners); short expiry | Create a new token, replace the Keychain entry, delete the old token on the forge | None while the loop re-reads the Keychain each iteration |
| Backup pull key | Owner's Mac (private key), VPS forced-command line (public key) | Owner | One ed25519 key, forced command with three verbs, restricted options | Generate a new pair, re-run the key installer with the new public key (replaces the single line), update the LaunchAgent path | Off-box pull pauses until both sides match; the freshness warning appears after three days |
| Read-only export token | Server environment file; network secret in the reading environment | Root; the reading environment | Minimum 32 characters, read-only routes, constant-time compare, throttled | Generate a new value, edit the file, restart the companion, update the network secret. Revoke by deleting the line | The export reader gets 401 until both sides match |
| Calendar feed address | Per-device state file, mode 0600 | Service user | One secret URL per device | Create a new feed address at the calendar provider, save it in the companion | Calendar highlighting pauses until saved |
| Language-model API key (optional airline suggestions) | Server environment file | Root, service user | A key limited to the one model endpoint and a spend cap on the provider side | Create a new key, edit the file, restart, delete the old key | Suggestions disabled until restarted |
| Forge tokens in workflows | Per-run workflow token | The run | Every workflow declares `contents: read` only; the deploy workflow uses the run token to list check runs and download releases, both read operations | None needed (per-run) | None |
| Data-source keys | None in use (no key for the ADS-B or route sources) | Not applicable | Not applicable | Not applicable | Not applicable |

### Token scope delta (documented versus used)

| Token | Documented scope | Calls found in code or workflows | Delta |
|-------|------------------|----------------------------------|-------|
| Invitation credential | `create:users`, `create:user_tickets` | One user creation call and one password-change ticket call, plus the token request for the Management audience | None; no unused scope |
| Workflow tokens | `contents: read` in all five workflows | Release listing and download, check-run listing, checkout | None; the release workflow publishes nothing with the run token |
| Runner registration token | Administration read and write | Runner registration only | Broad by nature (the forge offers no narrower repository scope); see item S-1 |

## Backups

- **Included:** a consistent online copy of the two SQLite databases (backup API, integrity check run on the copy), the per-device JSON state, device tokens, enrolment registry (hashes), the calendar feed secrets, uploaded artwork, the last rendered panels, and per-device directories. Regenerable files are excluded; an unlisted file is logged as drift rather than silently included. The environment file is not included.
- **Destination and permissions:** archives directory owned by the service user, group-readable only by the dedicated pull user, setgid, mode 2750; unit runs with a closed network, strict file system protection and `UMask=0027`.
- **Transport:** pulled, not pushed. A dedicated user outside the service group authenticates with one key restricted to a forced command with three exact verbs; each fetched archive is verified against its checksum on the Mac.
- **Retention:** 14 archives on the host; 30 newest plus one per month for 12 months on the Mac.
- **Restore:** documented, with a rehearsal procedure into a scratch directory; the backup job, gate and key installer have local tests (run, all passing). No production restore was run.
- **Content sensitivity:** archives contain device tokens, enrolment hashes, calendar feed addresses, e-mail addresses in the fleet database and rendered panels; user photos are not part of the include list.

## Logs

- Companion and device server request hooks log method and path only, never headers, cookies, bodies or query strings.
- The Management client and the language-model client do not log, and read their credentials only from the environment.
- The web server console log of the companion host drops the sign-in code, state and provider error query keys. Its default header redaction covers cookies and authorization headers. The other query keys used by the companion (frame selector, flash key, width, time filter) carry no credential.
- The device host writes a durable JSON access log (client address, path, selected telemetry headers) bounded to 10 MiB times 5 files, mode 660 for the service group.
- Logging call classes reviewed: none writes a token, enrolment secret, cookie, authorization header or request body. Device MAC addresses appear in journald in enrolment lines.

## Databases (access and integrity only)

- Fleet database: created mode 0600, foreign keys on, write-ahead log, busy timeout, schema newer than the code is refused, read-only open path for viewers.
- History database: write-ahead log, busy timeout, read-only open (`mode=ro`) for readers; created under the service umask (0640, service group).
- Per-device JSON and registries: written by a same-directory temporary file, fsync, then atomic rename; secrets written with mode 0600 set before any byte is written.
- Writers: the poll job, device server and companion, all as the same service user; no other account can write.
- Structure, indexes and migrations: Phase 67.

## Data-source terms

- Default provider order is the two ADS-B aggregators named in the compliance document; the third aggregator is reachable only by an explicit provider choice and is documented as opt-in only.
- Per-provider request spacing is enforced in code; the user agent names the project and carries no personal data.
- Citation and credits are present in the README and the public credits page as the compliance document states.
- The one provider whose terms forbid operational use is not reached by shipped code.
- The only provider key in use is the optional language-model key; none for flight data.

## Result

medium/low recorded

## Medium and low items

| ID | Category | Location | Recommendation | Severity |
|----|----------|----------|----------------|----------|
| S-1 | Credential breadth | Runner registration token (runner README) | Keep the token short-lived and in the Keychain only; revisit an organization-level runner group if more repositories appear | Low |
| S-2 | Credential exposure to branch workflows | Deploy secrets as repository secrets (deploy README, `deploy.yml`) | Keep the dedicated key; restrict its `authorized_keys` line with options on the host; when the plan allows, move the secrets to a protected environment with required reviewers | Medium |
| S-3 | Backup at rest | Archives on the host and the Mac copy | State and test the Mac volume encryption requirement; consider encrypting archives to a public key before the pull so a lost disk does not expose tokens and e-mail addresses | Medium |
| S-4 | Personal data in logs | Device-host access log (client address kept for up to five rolled files) and device MAC lines in journald | Document the retention in the privacy notes before wider rollout; consider shortening the rolled-file count | Low |
| S-5 | Integrity monitoring | History database has no scheduled integrity check; only the backup copy is checked | Run a quick integrity check in the health view or nightly and surface a failure | Low |
| S-6 | Operator output | Device CLI prints a short prefix of a stored hash | Print nothing or the full MAC only; the prefix is not needed | Low |
| S-7 | Personal data in history | Maintainer contact address in commit metadata and a few planning notes | Already decided in the earlier inventory; revisit if the repository ever becomes public again | Low |

## Follow-ups for next milestones

- Move deploy secrets to a reviewer-gated environment when the hosting plan permits (S-2).
- Decide the at-rest encryption policy for off-box backups (S-3).
- Re-run the history scan on a full mirror after the repository becomes private and after any history change.
