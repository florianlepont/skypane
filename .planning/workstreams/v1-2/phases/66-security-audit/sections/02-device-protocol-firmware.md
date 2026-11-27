# Area: Device protocol, enrolment, pairing and firmware update

## Scope read

- Device protocol server (`stub-server/byos_server.py`), operator registry CLI.
- Fleet storage and session modules (`server/fleet_db.py`, `server/fleet_sessions.py`), frame operations (`server/fleet_ops.py`), pairing code and pairing image modules, per-device directory resolution (`server/device_dirs.py`).
- Companion pairing-claim routes and their throttles (`companion/console_pairing.py`, `companion/throttle.py`), read for the claim path only.
- Firmware registry (`server/firmware_registry.py`), `firmware/SIGNING.md`, the update and validation sources of the firmware (`firmware/main/ota.c`, `ota_policy.h`, `validate.c`, `api_client.c`), and the two firmware workflows read as documents.
- Note: `server/pairings.py` is the colour pairing of the lettering screen, not the frame pairing flow; it handles no credential.

## Method

Code and configuration reading, plus the existing local tests. No request to any host, no flashing, no device contact, no key file opened (location and mode rules read from documentation only). The pytest-socket plugin is not installed in this environment, so the targeted suites ran with the project's addopts cleared; they use loopback only.

## Checks performed

- [x] Device authentication on each endpoint: bearer token compared with `hmac.compare_digest` against every stored token without early exit; the display and log endpoints refuse a missing or unknown token before any state is touched or written.
- [x] Unknown-MAC and unregistered requests: refusal paths and their response codes (see item DP-1).
- [x] Enrolment secret: 256-bit random token, only a SHA-256 hash stored, constant-time comparison, registry file written with mode 0600 set before first byte.
- [x] Device token generation (`secrets.token_hex(32)`), storage, revocation and replacement (see item DP-2).
- [x] Frame pairing: code from `secrets`, about 39 bits, 30-minute lifetime, stored salted and hashed, constant-time match over all candidates, identical refusal for every failure, claim in one immediate transaction (single winner), per-session and global failure lockouts checked before the database is touched, failed attempts audited without the guess.
- [x] Request size limits (64 KiB body cap, malformed or negative length rejected before read), request timeout on every socket, JSON recursion handled.
- [x] Path handling: every served file route matches a strict hex pattern; per-device directories resolve through `device_dirs` with a real-path containment check; firmware images served only when the digest is a registered release and the file is regular and within the size cap.
- [x] Error responses carry short fixed messages, no internal paths.
- [x] Protocol version and downgrade: single protocol version, firmware enforces https for every server URL in production builds (plain http only behind a development build option).
- [x] Firmware signing: RSA-3072 signature block on every release image, checked on update against the public key embedded in the running image; signing key held only on the owner's machine, never in CI; publish script refuses weak key file mode, unverified provenance or checksum mismatch.
- [x] Update path on the device: TLS with certificate bundle, image descriptor checked (project name, version equals offer, version at or above the compiled-in floor) before writing, size check, SHA-256 read back from the inactive slot, signature verified at the single commit point, battery gate, trial-boot confirmation and bootloader rollback on an unconfirmed image.
- [x] Registry: image offered only from the operator-published, scheduled release of the device's hardware type; manifest, hash, size and type validated before storage; attempt limit per schedule.
- [x] Release workflows: read-only token permissions, pinned action revisions, tag shape and on-main guard, no secret and no signing in CI; the chain-check workflow reads one repository secret through `env:`.
- [x] Freeze test and golden render hashes run, unmodified.

Local tests run (all passed):

- Freeze test and golden render suites: 115 passed.
- Device, enrolment, session, pairing and byos selection over `stub-server` and `server`: 456 passed, 1 skipped.
- Firmware, publish-script and certificate selection over `server` and `scripts`: 283 passed.
- Firmware host tests (C): relies on CI.

## Result

pending consolidation

## Medium and low items

| ID | Category | Location | Recommendation | Severity |
|----|----------|----------|----------------|----------|
| DP-1 | Information exposure (registration state) | enrolment handler in `stub-server/byos_server.py` | Answer an unregistered address and a wrong secret with the same status and body, and keep the distinction in the service log only. | Low |
| DP-2 | Credential storage | device token columns in fleet storage and the legacy state file | Store a hash of the device token at rest, as is already done for enrolment secrets, session tokens and pairing codes; compare hashes. Needs a transition for tokens already issued. | Low |
| DP-3 | Log integrity | device log upload handler in `stub-server/byos_server.py` | Escape control characters and cap length of device-supplied log text before printing to the service log. Only an authenticated device can reach this. | Low |
| DP-4 | Information exposure (log content) | request logging and the unauthenticated image routes in `stub-server/byos_server.py` | Image URLs are capability links (unguessable content hash) and the request path is written to the service log. Either log only the route class or document that service log readers can fetch displayed images. Relevant to the photo-privacy follow-up. | Low |
| DP-5 | Update policy (rollback) | `firmware/main/ota_policy.h`, `firmware/SIGNING.md` | Anti-rollback is software-only: a validly signed older release at or above the compiled-in floor can be installed. Raise the floor in any release that fixes a security weakness; record this rule in the update policy. Already a documented design choice. | Low |
| DP-6 | Availability hardening | enrolment endpoint | No application-side attempt limit on enrolment; brute force is infeasible given the 256-bit secret, but unauthenticated requests write to the log. Add a rate limit at the reverse proxy. | Low |
| DP-7 | CI hardening | `.github/workflows/firmware-chain-check.yml` | Add `persist-credentials: false` to the checkout step, as the release workflow does. Token is read-only, so impact is minimal. | Low |
| DP-8 | Observation | display handler image URL construction | The advertised image host comes from the request Host header. Only an authenticated device reaches this and the device only follows https; consider a configured public host instead. | Informational |

## Follow-ups for next milestones

- Update policy: decide floor-raising and anti-rollback rules for security releases, and how a lost or compromised signing key is handled in the field.
- Outside penetration test before any commercial launch.
- Photo privacy: review image URL exposure (DP-4) together with the photo features.
- Hardware secure boot and flash encryption remain intentionally off; revisit before a commercial launch.
