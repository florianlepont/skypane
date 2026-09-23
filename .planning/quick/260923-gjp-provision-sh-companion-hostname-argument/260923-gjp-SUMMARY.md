---
quick_id: 260923-gjp
status: complete
date: 2026-09-23
---

# Quick 260923-gjp — SUMMARY

## Context

Earlier the same day, the production companion moved from
`config-92-222-92-167.nip.io` to `skypane.algernon.ovh` (A record → 92.222.92.167).
The developer made the change by hand on the VPS: the second site block of
`/etc/caddy/Caddyfile`, a Caddy reload, and `SKYPANE_COMPANION_HOST` in
`/opt/skypane/skypane.env`. It was verified from outside: new host 303 → login,
Let's Encrypt certificate for `skypane.algernon.ovh` valid until 2026-12-22,
old nip.io host no longer served, device host unchanged. No GitHub change was
needed. The deploy workflow reaches the VPS by SSH target secret, the
`production` environment has no URL, and `deploy.sh` never touches the Caddyfile
or `skypane.env`.

## What changed

- `deploy/provision.sh`: new optional second argument, `companion-host`, which
  defaults to `config-<public-host>` (unchanged behaviour). Each substitution is
  now anchored to its own site-block line (`^config-203-0-113-10\.nip\.io {` and
  `^203-0-113-10\.nip\.io {`). Before, an unanchored first-match-per-line sed also
  rewrote the placeholder inside comments. Hostnames that are not
  `[A-Za-z0-9.-]` are refused before being interpolated into sed. A
  companion-host without a public-host is refused.
- `deploy/README.md`: new step 5 (choosing the companion hostname, A-record-only
  DNS advice), both provisioning examples show the optional argument, the
  production invocation is written out, there is a "change the companion
  hostname later" procedure, and the verification `curl` uses `<companion-host>`.
- `deploy/skypane.env.example`, `deploy/Caddyfile`: comments say the companion
  name is `config-<public-host>` only by default.

## Verification

- `bash -n` and `shellcheck deploy/provision.sh`: clean.
- The substitution was run in isolation against `deploy/Caddyfile` in three
  cases: no args (placeholders kept), public host only (`config-<host>` on the
  companion line), and both hosts (`skypane.algernon.ovh` on the companion
  line). The two site-block lines were correct each time, and every
  non-site-block line was byte-identical to the source.
- Hostname regex: `good.host-1.fr` accepted; `bad/host` and `x;rm` rejected.
- The only test that reads a changed file (`companion/test_companion_app.py`
  reading `skypane.env.example` for `SKYPANE_COMPANION_INSECURE_COOKIES`) is
  unaffected, because only a comment changed.
- Not exercised: a real `provision.sh` run as root on a fresh VPS.
