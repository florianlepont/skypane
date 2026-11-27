# Security Policy

SkyPane is a one-person hobby project. There is no bug bounty, but
security reports are welcome and taken seriously.

## Reporting a vulnerability

The repository is private, so there is no public issue tracker. Report
vulnerabilities to the maintainer privately, through the contact on
[github.com/florianlepont](https://github.com/florianlepont), and do not
post details anywhere public.

Include what you found, how to reproduce it, and what an attacker could
do with it. You should get a first answer within a week.

## Scope

In scope:

- the device-protocol server, the poll loop and the renderer (`server/`)
- the companion web app (`companion/`), including its authentication
- the firmware (`firmware/`) and the deployment scripts (`deploy/`)
- anything in this repository that exposes a secret

Out of scope:

- the upstream ADS-B and route data services (adsb.fi, adsb.lol,
  adsbdb.com) — report those to their operators
- the upstream FlightPortrait firmware — report to
  https://github.com/flightportrait/frame, unless the issue is in a part
  SkyPane changed
- denial-of-service by volume against the production server

Please don't test against the production deployment beyond what's needed
to show the issue exists; running the stack locally
(see [README.md](./README.md)) is the better place for that.

## Secrets

No credentials are committed to this repository. Real values live only
in a gitignored file (`deploy/skypane.env`), in repository-level GitHub
Actions secrets (the deploy key, its pinned host key and the deploy target;
the firmware signing key is not held by GitHub),
and — for the device's own Wi-Fi password, API base and enrolment
secret — in its `secret` NVS partition, written directly by
`firmware/provision.sh` over USB and never compiled into a firmware
image; the tracked `*.example` files hold placeholders. If you ever spot
something that looks like a real secret, please report it as above.

## Audit and rotation

The security audit, the rotation steps for each credential, the smallest
token scopes, and the remaining risks and follow-ups are in
`.planning/workstreams/v1-2/phases/66-security-audit/66-AUDIT.md`.
