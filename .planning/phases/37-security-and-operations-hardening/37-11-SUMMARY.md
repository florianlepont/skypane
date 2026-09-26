---
phase: 37-security-and-operations-hardening
plan: 11
subsystem: infra
tags: [byos, systemd, loopback, ip-filter, secrets, production, checkpoint]
requires:
  - phase: 36-state-integrity-and-device-protocol
    provides: byos request hardening and content-addressed images (byos_server.py as rebuilt on)
  - phase: 34-firmware-resilience-power-security-cleanup (plan 34-03)
    provides: per-device enrolment registry; shared byos secret retired, no --secret in the unit
  - phase: 37-security-and-operations-hardening (Plans 37-03, 37-09)
    provides: hardened units, offline score gate, release layout in production
provides:
  - "byos listens on loopback only (--bind 127.0.0.1) behind IPAddressDeny=any/IPAddressAllow=localhost"
  - "No secret in byos argv or environment, proven by test and live"
  - "Old in-place code directories removed from the VPS"
key-files:
  created:
    - stub-server/test_byos_bind_secret.py
  modified:
    - stub-server/byos_server.py
    - stub-server/VENDOR.md
    - deploy/skypane-byos.service
    - deploy/tests/test_units.py
    - deploy/README.md
    - ARCHITECTURE.md
    - .planning/phases/37-security-and-operations-hardening/37-SEC-BASELINE.md
requirements-completed: [SEC-06, SEC-07]
completed: 2026-09-26
---

# Plan 37-11 summary: byos loopback-only, no secret in ps (CP-11, CP-7)

Code shipped in PR #143 (merge `34bc038`), deployed through the
reviewer-gated CI job.

## Gates
- Phase 36 complete on main (PR #142). All seven 36 plans have a SUMMARY.
- Phase 34 plan 34-03 merged: `def load_registry` is in `byos_server.py`, and
  the unit has no `--secret`.
- byos makes no outbound connections (no urllib/requests/http.client/
  socket.create_connection), so `IPAddressDeny=any` is safe.

## Task 1: `--bind` (TDD)
- RED: `stub-server/test_byos_bind_secret.py` failed with `unrecognized
  arguments: --bind 127.0.0.1`. It reuses the registry harness from
  `test_devices_registry.py`, loaded by path because of `--import-mode=importlib`.
- GREEN: `--bind` defaults to `0.0.0.0`. The server is built with
  `(args.bind, args.port)`, and the startup line prints `bind:port`. The retired
  `--secret`, the registry helpers and the setup branch were not touched, and
  nothing reads a secret from the environment.
- The test covers four things:
  - With `--bind 127.0.0.1`, the only LISTEN socket in `/proc/net/tcp{,6}` is
    `0100007F`. Without the flag it is `00000000`.
  - `/proc/<pid>/cmdline` and `environ` hold no `--secret`, no
    `SKYPANE_BYOS_SECRET` and no secret value. The child is started with that
    variable removed from its environment.
  - Registry enrolment on the loopback-bound server returns 200 and a token
    with the right secret, and 401 with a wrong one.
- `VENDOR.md` records this as local modification 10.

## Task 2: unit, tests, docs
- `skypane-byos.service`: `--bind 127.0.0.1`, `IPAddressDeny=any`,
  `IPAddressAllow=localhost`, and a rewritten header comment. Still no `--secret`.
- `deploy/tests/test_units.py` checks:
  - the loopback bind, the IP filter and `EnvironmentFile`;
  - that neither `--secret` nor `SKYPANE_BYOS_SECRET` appears in the unit;
  - that `skypane.env.example` has no `SKYPANE_BYOS_SECRET=` assignment.
- The companion and poll units still carry no IP filter.
- Offline score for byos: 1.5 → **1.3 OK**.
- `deploy/README.md`: the "Known vendored behaviour: binds 0.0.0.0" section
  is replaced by "byos listens on loopback only". `ARCHITECTURE.md`'s
  topology bullet is updated to match.

## CP-11 (2026-09-26, developer on the VPS)
Full record in `37-SEC-BASELINE.md` → "Wave B (CP-11)".
- **Env file:** it still held a stale `SKYPANE_BYOS_SECRET=` line from before
  Phase 34 (count 1). The line was deleted with `sed -i`, without printing
  it. After the deletion the count is 0, the file is still `root:root 600`,
  and byos restarted `active`.
- **`pgrep`:** `--bind 127.0.0.1`, no `--secret`, no secret value.
- **`ss`:** `127.0.0.1:8642` only.
- **Public check:** a public GET of `/device/v1/display` without a token
  returns 401.
- **Online score:** 1.3 OK.
- **Frame:** the new byos process served a fresh
  `GET /img/<sha>.bin` at 12:30:40 UTC, at the frame's 300 s wake.

## CP-7 (2026-09-26)
- `current` → `releases/34bc03844ab2918f22fc4d4118d5a683f6e01d8c`.
- Run on the VPS, `grep` of the installed `skypane-*.service` for the old
  directories returned exit 1. The code paths in
  `systemctl cat skypane-byos skypane-companion skypane-poll` are only
  `/opt/skypane/current/` and `/opt/skypane/venv/`.
- `server/`, `stub-server/`, `companion/` and `config/` were removed.
- `sudo ls /opt/skypane` shows `current releases skypane.env state venv`.
- byos, companion, poll.timer, caddy and backup.timer are all `active`.
- Poll cycles after the removal finish with `Deactivated successfully`.

## Deviations and notes
- The plan's parse-default check is proven by behaviour (a server started
  without `--bind` listens on `0.0.0.0`), not by a parser unit test. This
  keeps the `byos_server.py` diff to the parser line, the server construction
  and the print, as the acceptance criteria require.
- Two checkpoint mistakes were caught during CP-7, and neither affected
  production:
  - **The first "grep-exit=1" came from the Mac.** It ran on the Mac after the
    SSH session had closed. zsh found no `skypane-*.service` to match, so
    grep never ran and the 1 proved nothing. The check was re-run on the VPS
    inside single quotes, together with `systemctl cat`.
  - **`ls /opt/skypane` needs sudo.** The directory is not readable by `ubuntu`.
- Out of scope, reported to the developer: the VPS reports "System restart
  required" and 32 pending package updates.
