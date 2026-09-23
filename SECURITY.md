# Security Policy

SkyPane is a one-person hobby project. There is no bug bounty, but
security reports are welcome and taken seriously.

## Reporting a vulnerability

Please **do not open a public issue**. Use GitHub's private reporting
instead: go to the repository's **Security** tab and click **Report a
vulnerability**. Only the maintainer can see the report.

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
in gitignored files (`deploy/skypane.env`, `firmware/main/secrets.h`) and
in GitHub Actions secrets; the tracked `*.example` files hold
placeholders. If you ever spot something that looks like a real secret,
please report it as above.
