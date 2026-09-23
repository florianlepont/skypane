# Phase 34 Hardware Session — Results

This document is the results template for plan `34-11`, the phase's one
hardware session on the real EE02. Every expectation below was written
before the session (by plan `34-10`), against the code as merged at the
commit recorded under "Build under test" — the developer fills in
"Observed" and "Result" as the script runs, never edits "Pre-registered
expectation" to match what happened. A scenario that does not match its
expectation is a **FAIL**, recorded honestly, not a discrepancy to
explain away — see `hardware/BACKOFF-OBSERVATION.md` for the standard
this project holds itself to when a result is partial.

Scenario IDs (`H-00`..`H-20`) match plan `34-11-PLAN.md`'s script exactly;
each ID there is the source of truth for the commands themselves. This
document only records outcomes.

## Verdict

**PENDING** — filled in only after every scenario below has a result.

- Success criterion 1 (simulated brownout/panic → backoff sleep, not an
  immediate retry; a hung wake bounded by the global deadline): **PENDING**
- Success criterion 2 (a 401 from the server leads to re-enrolment on the
  next wake, with no reflash): **PENDING**
- Success criterion 3 (validation helpers and the sleep decision covered
  by host tests that run in CI): **PENDING** — already proven in CI by
  plan `34-10` (`run_host_tests.sh`, `check_production_config.sh`,
  `check_log_contract.sh`); this session only needs to confirm nothing
  regressed on real hardware.
- Success criterion 4 (no-change wake duration measured before/after on
  real hardware — DHCP, TLS, memtest — and logged): **PENDING**
- Success criterion 5 (byos refuses to re-enrol a known MAC; each device
  has its own secret): **PENDING**

## Build under test

| Field | Value |
|---|---|
| Commit (`git rev-parse HEAD`) | PENDING |
| Production `Firmware version:` line (H-01) | PENDING |
| Dev `Firmware version:` line (H-08) | PENDING |
| Device MAC (H-02) | PENDING |
| Date | PENDING |
| Network — LAN stub host | PENDING (this laptop's `LANIP`) |
| Network — VPS host | `<public-host>` (fill in the real `HOST` used this session) |

## Scenario results

| ID | Requirement | Pre-registered expectation | Observed | Capture file | Result (PASS/FAIL/N/A) |
|---|---|---|---|---|---|
| H-00 | FW-09, FW-10 (baseline) | If the frame still runs the pre-phase image against the VPS: at least 10 no-change wakes (`hash_skip=1`) captured, median total wake duration extracted from consecutive `sleep enter` boot-relative timestamps, for comparison against H-04. If the frame no longer holds a valid pre-phase token (VPS already migrated, or the old byos already retired): N/A, citing `hardware/BATTERY-RUN.md`'s 328 s mean interval as the pre-phase reference instead. The LAN "before" baseline needs no re-measure — it is `hardware/logs/backoff-run.log`'s existing ≈4.4 s total / ≈3.0 s DHCP figures. | PENDING | `hardware/logs/phase34/H-00-vps-before.log` (or N/A) | PENDING |
| H-01 | FW-15 | `./firmware/build.sh` prints a `Firmware version:` line matching `git describe --tags --always --dirty`'s own output; `sh firmware/tests/check_production_config.sh built firmware/build-ee02` prints `production-config built: PASS`; `./firmware/flash.sh "$PORT"` prints `flash.sh: SUCCESS`. | PENDING | n/a — build/flash console output, recorded directly in this table | PENDING |
| H-02 | D-34-02 | `firmware/provision.sh "$PORT"` run WITHOUT `--reset-device-state` writes the secret and prints the MAC (recorded above; the secret hash itself is never pasted into this file). The following wakes show `boot_count` continuing from its pre-provision value (not reset to 1), no `setup accepted` line, and `poll ok ... hash_skip=1` — the bearer token, image hash and boot counter all survive provisioning. | PENDING | `hardware/logs/phase34/H-02-provision.log` | PENDING |
| H-03 | FW-08 | The `devices_cli.py add --mac <mac> --secret-sha256 <hash> --replace` command `provision.sh` printed succeeds against the VPS state dir; `devices_cli.py list` on the VPS shows the MAC registered. The MAC is also registered against the local LAN-stub state dir for the later dev-image scenarios (H-08 onward). | PENDING | n/a — `devices_cli.py list` output, recorded directly in this table | PENDING |
| H-04 | FW-09, FW-10, FW-12 | At least 10 no-change wakes over https against the VPS: no `SPI SRAM memory test` line anywhere in the capture (memtest off, FW-12); every `poll ok` succeeds over TLS validated by the ISRG-only bundle; the `fp_api` line shows `http connects=1` on every wake (the keep-alive connection reuse holds against Caddy, not just the LAN stub, FW-10); the first wake after the reset shows `tls_offered=0`, later wakes show `tls_offered=1` (best-effort session resumption); `total_ms`/`wifi_ms`/`display_ms`/`first_connect_ms` medians recorded into the Wake Duration table below. | PENDING | `hardware/logs/phase34/H-04-vps-after.log` + `H-04-vps-after-server.log` | PENDING |
| H-05 | FW-03, D-34-01 | `poll fail step=auth backoff_n=<n> sleep_s=<n>` on the wake right after the server-side token revoke; the next wake (~5 min later) logs `setup accepted; device credential stored` then `poll ok`; the server log shows a 401 on `/display` followed by `setup: <mac> enrolled`. No reflash anywhere in this scenario. | PENDING | `hardware/logs/phase34/H-05-revoke.log` + `H-05-revoke-server.log` | PENDING |
| H-06 | FW-08, D-34-01 | `curl POST /device/v1/setup` with a wrong secret for the device's registered MAC returns `401`; the same call for an unregistered MAC (`02:00:00:00:00:01`) returns `403`; the frame's own token is untouched throughout (its next wake is still `poll ok`, not re-enrolling). | PENDING | `hardware/logs/phase34/H-06-curl.txt` | PENDING |
| H-07 | FW-07, D-34-04 | With `SKYPANE_API_BASE` temporarily set to `http://LANIP:8642` in a production build, the device logs `API base URL rejected (this build requires https)` and `poll fail step=config` — no request is ever sent. `secrets.h` is restored to `https://HOST` immediately after the capture. | PENDING | `hardware/logs/phase34/H-07-http-refused.log` | PENDING |
| H-08 | FW-03, FW-11 | The first wake after flashing the dev image against the LAN stub (the VPS token is unknown here) logs `step=auth`; ~5 min later, `setup accepted`, a refresh (`blit ok`), then at least 10 no-change wakes; LAN-after medians recorded into the Wake Duration table below. The `fp_batt` line appears before the first `wifi:` log line of every wake (FW-11's before-Wi-Fi ordering). | PENDING | `hardware/logs/phase34/H-08-lan-dev.log` + `H-08-lan-dev-server.log` | PENDING |
| H-09 | FW-04 | With the LAN stub restarted at `--sleep 86401`, the device logs `poll fail step=json backoff_n=0 sleep_s=300` (the server-supplied `sleep_s` is rejected as out of range). With the stub restarted at `--sleep 30`, the very next wake recovers with `poll ok`. | PENDING | `hardware/logs/phase34/H-09-sleep86401.log` + `H-09-sleep86401-server.log` | PENDING |
| H-10 | FW-09, D-34-03 | With the four `SKYPANE_STATIC_*` macros defined (address outside the router's DHCP pool) and a dev image flashed, 10 no-change wakes complete with no DHCP negotiation; the `wifi_ms` median for this row is recorded and compared against the LAN-after (DHCP) median. If skipped (no safe static address available), a reason is recorded under "Deviations and not observed" instead, per D-34-03's "unless the measured gain of the default path is insufficient" allowance. | PENDING | `hardware/logs/phase34/H-10-static-ip.log` (or N/A) | PENDING |
| H-11 | FW-02, FW-12 | With the LAN stub at `--sleep 30` and a fresh panel pattern pushed right after a `blit ok`, the next wake logs `holding <20..30>s for the panel's refresh spacing`, then `blit ok`, with **no** `task_wdt` / `Task watchdog got triggered` line anywhere in the capture during the wait (the light-sleep spacing wait does not itself starve the task watchdog). | PENDING | `hardware/logs/phase34/H-11-spacing.log` + `H-11-spacing-server.log` | PENDING |
| H-12 | FW-01, FW-02 | `SKYPANE_FAULT=panic`: `abort()` backtrace, reboot, `reset reason=panic`, `wake reason=other`, `poll fail step=reset backoff_n=0 sleep_s=300` on the first failure; continuing the capture through the backoff sleep, the second panic shows `backoff_n=1` and a doubled `sleep_s` (600). | PENDING | `hardware/logs/phase34/H-12-fault-panic.log` | PENDING |
| H-13 | FW-01, FW-02 | `SKYPANE_FAULT=task_wdt`: within ~60 s of the `SKYPANE-FAULT-INJECT task_wdt` marker, `Task watchdog got triggered`, reboot, `reset reason=task_wdt`, `poll fail step=reset backoff_n=<n> sleep_s=<n>` — the wake never exceeds the 60 s task-watchdog ceiling before panicking. | PENDING | `hardware/logs/phase34/H-13-fault-task_wdt.log` | PENDING |
| H-14 | FW-01, FW-02 | `SKYPANE_FAULT=int_wdt`: `Interrupt wdt timeout`, reboot, `reset reason=int_wdt`, `poll fail step=reset backoff_n=<n> sleep_s=<n>`. | PENDING | `hardware/logs/phase34/H-14-fault-int_wdt.log` | PENDING |
| H-15 | FW-02 | `SKYPANE_FAULT=slow_wake`: `wake budget of 300s exceeded`, `poll fail step=deadline`, and the `wake timing total_ms=` value on that line is between 300000 and 360000 — the 300 s wake budget ends the wake, not the 60 s task watchdog, proving the two mechanisms are independent. | PENDING | `hardware/logs/phase34/H-15-fault-slow_wake.log` | PENDING |
| H-16 | FW-01 | Optional (needs a variable bench supply on the battery input): lowering the supply until the chip resets during Wi-Fi produces `reset reason=brownout` and `poll fail step=reset`. If no bench PSU is available, N/A — the classification itself is already host-tested (`test_reset_reason.c`) and shares the H-12 reset→backoff path end to end. | PENDING | `hardware/logs/phase34/H-16-fault-brownout.log` (or N/A) | PENDING |
| H-17 | FW-11 | On the LiPo (USB unplugged), for three consecutive wakes: `\|X-Battery-Mv − multimeter\| ≤ 60 mV` at the JST connector on each of the 3 readings, and the `fp_batt` line appears before the first Wi-Fi log line of each of those wakes. | PENDING | n/a — see "Battery vs multimeter" table below | PENDING |
| H-18 | FW-15 | Prod: the server log's `telemetry: X-Fw-Version=` value equals H-01's `Firmware version:` line. Dev: the LAN stub's `telemetry:` lines show `X-Fw-Version = <git describe>-dev`. | PENDING | see `H-04-vps-after-server.log` (prod) / `H-08-lan-dev-server.log` (dev) | PENDING |
| H-19 | FW-03 | After reflashing the production image, the LAN-registered token is unknown to the VPS, so the first wake logs `step=auth`; ~5 min later, `setup accepted` and `poll ok` against the VPS. The companion Wake interval noted in prep step A5 is restored; the LAN stub is stopped. | PENDING | `hardware/logs/phase34/H-19-restore.log` | PENDING |
| H-20 | FW-09, FW-10, FW-12 | The Wake Duration table below (H-00, H-04, H-08 medians) supports a written, three-way comparison — LAN-before vs VPS-before isolates the internet+TLS cost; VPS-before vs VPS-after shows the keep-alive/TLS-reuse/DHCP/memtest gain; `http connects=` and `first_connect_ms` at `tls_offered=0` vs `tls_offered=1` show the handshake's own share — ending in a one-paragraph conclusion in "The ~28 s per-cycle overhead" below. | PENDING | n/a — derived from H-00/H-04/H-08; see § "The ~28 s per-cycle overhead" | PENDING |

## Wake duration (no-change wakes)

Medians only (not means) — a single slow outlier wake (a retry, a missed
ARP reply) should not move the headline number. `n wakes` is how many
no-change (`hash_skip=1`) wakes the median is computed over; fewer than
5 is a weak sample and should be noted as such.

| Configuration | Median total_ms | Median wifi_ms | Median display_ms | http connects | first_connect_ms | n wakes |
|---|---|---|---|---|---|---|
| LAN stub, before (`hardware/logs/backoff-run.log`, no re-measure) | ~4400 (4.4 s) | ~3000 (3.0 s, DHCP) | not captured by that log's format | n/a (pre-connection-reuse) | n/a | see source log |
| LAN stub, after (H-08) | PENDING | PENDING (pre-registered: < 3000) | PENDING | PENDING (pre-registered: 1) | PENDING | PENDING |
| VPS, before (H-00) | PENDING or N/A | PENDING or N/A | PENDING or N/A | n/a (pre-connection-reuse) | n/a | PENDING or N/A |
| VPS, after — `tls_offered=0` (H-04, first wake after reset) | PENDING | PENDING | PENDING | PENDING (pre-registered: 1) | PENDING | PENDING |
| VPS, after — `tls_offered=1` (H-04, later wakes) | PENDING | PENDING | PENDING | PENDING (pre-registered: 1) | PENDING (pre-registered: lower than `tls_offered=0`, if Caddy resumes — either outcome is recorded, resumption is best effort) | PENDING |
| LAN, after, static IP (H-10, if not skipped) | PENDING | PENDING (pre-registered: below the DHCP LAN-after median) | PENDING | PENDING | PENDING | PENDING |

Pre-registered expectations for this table: LAN-after median `wifi_ms`
below 3000 ms; VPS-after `http connects=1` on every no-change wake;
`tls_offered=1` wakes show a lower `first_connect_ms` than `tls_offered=0`
wakes only if Caddy actually resumes the offered session — either
outcome (resumed or not) is recorded here, since resumption is
best-effort by design (`tls_session.c`'s own doc comment).

## The ~28 s per-cycle overhead

`hardware/BATTERY-RUN.md` (lines ~325-350) measured a mean inter-poll
interval of ~328 s against a nominal 300 s `sleep_s` — about 28 s of
real, consistent per-cycle overhead the checker's nominal coverage
formula does not model. This section explains that number from the
Wake Duration table above, filled in after H-00/H-04/H-08 are captured.

- **LAN-before vs VPS-before** (isolates the internet + TLS handshake
  cost the LAN stub never paid, since it is plain http on the same
  network): PENDING
- **VPS-before vs VPS-after** (isolates the keep-alive connection reuse
  / TLS session resumption / DHCP restore-last-IP / memtest-off gain
  this phase adds): PENDING
- **Measured TLS connect cost** (`first_connect_ms` at `tls_offered=0`
  vs `tls_offered=1`, from H-04): PENDING
- **DHCP share** (LAN-before's ~3.0 s DHCP component vs the DHCP-restore
  path's contribution to VPS-after's `wifi_ms`, and the static-IP row
  from H-10 if captured): PENDING
- **Full-blit share** (if any captured wake refreshed instead of
  hash-skipping, its `draw_ms` contribution to that wake's total,
  for context — most captured wakes are expected to hash-skip): PENDING
- **One-paragraph conclusion**: PENDING

## Battery vs multimeter

Three consecutive wakes on the LiPo (USB unplugged), from H-17. Pre-registered
threshold: `|X-Battery-Mv − multimeter| ≤ 60 mV` on every row.

| Time | Multimeter mV (JST connector) | X-Battery-Mv (server log) | Delta (mV) |
|---|---|---|---|
| PENDING | PENDING | PENDING | PENDING |
| PENDING | PENDING | PENDING | PENDING |
| PENDING | PENDING | PENDING | PENDING |

## Deviations and not observed

Free text — filled in only if something in the script above could not be
run as written, or ran differently than expected. Prompts:

- **Brownout (H-16):** if no variable bench PSU was available, record
  that here (this is expected in most home setups — the scenario is
  optional for exactly this reason); the classification path itself is
  already covered by `test_reset_reason.c` and by H-12's reset→backoff
  path on the same `fail_and_sleep("reset")` exit.
- **Static IP (H-10):** if skipped because no address outside the
  router's DHCP pool could be safely chosen, record that here — D-34-03
  makes the static-IP fallback optional precisely for this case.
- **Anything else that failed or was skipped:** record the scenario ID,
  what was attempted, what happened instead, and whether it blocks a
  ROADMAP success criterion or is a lower-severity gap for a follow-up
  plan.

PENDING — nothing recorded yet.

## Checker output

Paste the literal command output below once run against the built
production image and (optionally) any `hardware/logtools.py` checks used
during this session.

```
$ sh firmware/tests/check_production_config.sh built firmware/build-ee02
PENDING
```

```
$ python3 hardware/logtools.py ...
PENDING (only if used this session)
```
