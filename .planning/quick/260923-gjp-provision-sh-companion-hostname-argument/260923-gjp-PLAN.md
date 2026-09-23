---
quick_id: 260923-gjp
slug: provision-sh-companion-hostname-argument
date: 2026-09-23
type: quick
---

# Quick 260923-gjp: provision.sh takes the companion hostname as its own argument

On 2026-09-23 the production companion moved from `config-92-222-92-167.nip.io`
to its own domain, `skypane.algernon.ovh` (A record → 92.222.92.167, hand-edited
in `/etc/caddy/Caddyfile` on the VPS). `deploy/provision.sh` could not express
that: it substitutes one `public-host` into the whole Caddyfile, so the companion
block always became `config-<public-host>`. A re-provision would silently revert
production to a hostname with no DNS record.

## Task

1. `deploy/provision.sh`: accept an optional second argument, `companion-host`.
   Default `config-<public-host>` (the current behaviour). Substitute each host
   only on its own site-block line, companion first, so the device substitution
   cannot rewrite the companion line. Refuse hostnames that are not
   `[A-Za-z0-9.-]`, since they are interpolated into a sed expression.
2. `deploy/README.md`: document the second argument and the production values.
3. `deploy/skypane.env.example` and `deploy/Caddyfile` comments: say that the
   companion hostname can be any name, not only the `config-` prefix.

## Verification

- `bash -n deploy/provision.sh`; shellcheck if available.
- Run the Caddyfile substitution in isolation against `deploy/Caddyfile` for
  (a) no arguments, (b) public host only, (c) both hosts, and (d) an invalid
  hostname. Check the two site-block lines each time and confirm the rest of
  the file is unchanged.
