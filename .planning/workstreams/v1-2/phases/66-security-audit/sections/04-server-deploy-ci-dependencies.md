# Area: Server, deploy pipeline, CI and dependencies

## Scope read

- Deploy directory: the six systemd units (byos, companion, poll, poll timer, backup, backup timer), the Caddy site template and its renderer, the environment example file, provisioning, SSH hardening, deploy and activate scripts, backup scripts and the forced-command key installer, the Mac runner kit (README, loop script, launchd example, VM definition).
- All five GitHub Actions workflows.
- The server dependency inputs and lock files, the lock script, the firmware build script (container pin) and the firmware import path on the server.

## Method

Code and configuration reading only. No real environment file was opened (the example file and deploy docs were used). No workflow was run, no deployment approved, no request sent to the production host. No dependency was installed and no project data left the machine.

## Checks performed

- [x] Units: run-as user is the unprivileged service user in all six; sandbox options present (no new privileges, strict system protection, private tmp and devices, empty capability set, namespace/realtime/SUID restrictions, syscall filter, write-deny memory mapping, restrictive umask); write paths limited to the state directory (backup: state and archive directory).
- [x] Network posture of units: device-protocol service binds loopback and filters IP traffic to loopback; companion binds loopback, no IP filter because it makes outbound calls; backup unit has no network.
- [x] Environment file handling: documented as root-owned, mode 0600, read by systemd before privilege drop; the example file carries placeholders only; test-only switches are documented as never set in production.
- [x] Caddy: automatic TLS, HSTS, two site blocks proxying to loopback ports, firewall denies the application ports from outside, access log allow-list of telemetry headers, sign-in query keys removed from the companion log. Response security headers are set by the companion application itself.
- [x] Provisioning: directory owners and modes, SSH key-only login and no root login, firewall default deny with SSH, 80 and 443 open.
- [x] Backup: nightly timer, archive and checksum stay on the host, off-host pull goes through a forced-command key with the restrict option.
- [x] Workflows: permissions blocks (read-only token at workflow level everywhere, per-job blocks in the release workflow); triggers (no `pull_request_target`, no `workflow_run`); user-controlled inputs reach scripts through environment variables and are matched against fixed patterns; every third-party action is pinned by commit hash; fork pull requests are kept off self-hosted runners by a job condition; the release workflow holds no signing key and only builds unsigned images; signing and publishing happen on the owner's machine.
- [x] Production deploy workflow: manual trigger only, refuses any ref other than main, requires the tip of main, a matching short hash and a successful CI check, uses a dedicated deploy key and a separately stored host key, runs on a GitHub-hosted runner. It has no environment reviewer gate by design (documented in the workflow and deploy README).
- [x] Release download: releases are fetched with the workflow token, file names are allow-listed, and the server import step enforces the signing policy and records content hashes before anything is offered to a device. No separate checksum check exists between download and transfer.
- [x] Mac runner kit: single-use just-in-time runners, VM without host mounts or forwarded ports, unprivileged job user without sudo, no production secrets in the VM, registration token kept in the system keychain and passed through standard input, documented residual risk.
- [x] Dependencies: every pinned entry in both lock files carries hash lines (verified by script); CI and the server activation script install with required hashes; no VCS or URL dependency; the container image used for firmware builds is pinned by tag.
- [ ] Known-vulnerability check: not run. No offline-capable audit tool is installed and nothing was installed for this audit.

## Result

pending consolidation

## Medium and low items

| ID | Category | Location | Recommendation | Severity |
|----|----------|----------|----------------|----------|
| D-1 | Pipeline access control | production deploy workflow | The deploy secrets are readable by any workflow on any branch of the repository, and the confirmation input is an anti-accident control only. Keep the repository private with no collaborators, and consider a protected deployment environment with a required reviewer once a plan that supports it is in use. | Medium |
| D-2 | Supply chain | deploy step that downloads releases | Verify the published checksum list (or the signature) of each downloaded release asset in the workflow before it is streamed to the host, as defence in depth beside the server-side signature policy. | Low |
| D-3 | Supply chain | firmware build script, runner VM definition | Pin the build container image and the base VM images by digest, not by tag or moving release path. | Low |
| D-4 | Dependency hygiene | CI | Add a scheduled, lock-file based known-vulnerability check (package names and versions only), and record the result. Not run in this audit. | Low |
| D-5 | Hardening | companion unit | The unit has no systemd IP filter because it must make outbound calls. Consider restricting outbound destinations at the firewall level if the set of destinations stays small. | Low |
| D-6 | Hardening | Caddy site template | Consider a request body size limit at the proxy as defence in depth beside the application limits. | Low |

## Follow-ups for next milestones

- Run a known-vulnerability check against the lock files in CI (D-4).
- Revisit the deploy approval model before any additional person gets repository write access (D-1).
