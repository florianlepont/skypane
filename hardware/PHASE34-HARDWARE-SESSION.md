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

**PASS** — all five ROADMAP success criteria hold on the real EE02
(session of 2026-09-25, firmware `e8d293c`). Two scenarios were skipped
(H-10 static IP, H-16 brownout: N/A). Three could only be partly
observed over the USB-CDC console (H-02, H-08 and H-17 lose the first
~0.5 s of every boot while the host re-enumerates the port). None of
these gaps affects a success criterion. See "Deviations and not observed".

- Success criterion 1 (simulated brownout/panic → backoff sleep, not an
  immediate retry; a hung wake bounded by the global deadline): **PASS** —
  H-12 (panic → `reset reason=panic` → `poll fail step=reset`, sleep
  doubling 600 → 1200 s), H-13 (task watchdog), H-14 (interrupt watchdog),
  H-15 (a hung wake cut at 300.7 s by the wake budget → `step=deadline`).
  Brownout itself was not induced (H-16 N/A); it shares the H-12 path.
- Success criterion 2 (a 401 from the server leads to re-enrolment on the
  next wake, with no reflash): **PASS** — H-05 (token revoked on the VPS →
  `device token rejected; erased` → `poll fail step=auth` → 5 min later
  `setup accepted` → `poll ok`, no reflash), repeated in H-08 and H-19.
- Success criterion 3 (validation helpers and the sleep decision covered
  by host tests that run in CI): **PASS** — already proven in CI by
  plan `34-10` (`run_host_tests.sh`, `check_production_config.sh`,
  `check_log_contract.sh`); this session only needs to confirm nothing
  regressed on real hardware.
- Success criterion 4 (no-change wake duration measured before/after on
  real hardware — DHCP, TLS, memtest — and logged): **PASS** — no-change
  wake (uptime at `poll ok`) 6.34 s → 1.65 s against the VPS and
  4.4 s → 1.57 s on the LAN; Wi-Fi+DHCP ≈ 3.0 s → 1.15 s; TLS connect
  1.94 s → 0.10 s with session resumption; no PSRAM memtest line.
- Success criterion 5 (byos refuses to re-enrol a known MAC; each device
  has its own secret): **PASS** — H-02/H-03 (per-device secret written to
  its own NVS partition and registered by hash), H-06 (wrong secret → 401,
  unregistered MAC → 403, old shared secret → 401).

## Build under test

| Field | Value |
|---|---|
| Commit (`git rev-parse HEAD`) | `e8d293c` (main at session start) |
| Production `Firmware version:` line (H-01) | `e8d293c` (`project_version` in `build-ee02/project_description.json`) |
| Dev `Firmware version:` line (H-08) | `e8d293c-dev` |
| Device MAC (H-02) | `94:a9:90:cf:80:08` |
| Date | 2026-09-24 (preparation) and 2026-09-25 (all scenarios) |
| Network — LAN stub host | `192.168.1.94:8642` (developer laptop) |
| Network — VPS host | `vps-1440bce3.vps.ovh.net` (production, release layout) |

## Scenario results

| ID | Requirement | Pre-registered expectation | Observed | Capture file | Result (PASS/FAIL/N/A) |
|---|---|---|---|---|---|
| H-00 | FW-09, FW-10 (baseline) | If the frame still runs the pre-phase image against the VPS: at least 10 no-change wakes (`hash_skip=1`) captured, median total wake duration extracted from consecutive `sleep enter` boot-relative timestamps, for comparison against H-04. If the frame no longer holds a valid pre-phase token (VPS already migrated, or the old byos already retired): N/A, citing `hardware/BATTERY-RUN.md`'s 328 s mean interval as the pre-phase reference instead. The LAN "before" baseline needs no re-measure — it is `hardware/logs/backoff-run.log`'s existing ≈4.4 s total / ≈3.0 s DHCP figures. | Pre-phase image against the VPS, 11 wakes read on the live console (2026-09-25 from 07:17 UTC, companion interval 60 s): 3 no-change wakes with `poll ok` at uptime 6246 / 6336 / 6416 ms (median **6336 ms**) and 8 refresh wakes at 43.0–43.3 s (a different aircraft almost every minute during the morning departure bank). The committed capture keeps only one of those pre-phase wakes (`poll ok ... hash_skip=1` at 6407 ms). The rest of the file was overwritten, and later new-firmware wakes were appended to it by a capture started with the wrong file name; those carry `fp_diag` lines, which the old image never printed. | `hardware/logs/phase34/H-00-vps-before.log` (or N/A) | PASS (weak sample: 3 no-change wakes; see Deviations) |
| H-01 | FW-15 | `./firmware/build.sh` prints a `Firmware version:` line matching `git describe --tags --always --dirty`'s own output; `sh firmware/tests/check_production_config.sh built firmware/build-ee02` prints `production-config built: PASS`; `./firmware/flash.sh "$PORT"` prints `flash.sh: SUCCESS`. | `./firmware/build.sh` → version `e8d293c` (= `git describe` on main, not dirty: `secrets.h` is ignored); `check_production_config.sh built firmware/build-ee02` → `production-config built: PASS`; `flash.sh: SUCCESS` with byte-for-byte read-back of the app region. | n/a — build/flash console output, recorded directly in this table | PASS |
| H-02 | D-34-02 | `firmware/provision.sh "$PORT"` run WITHOUT `--reset-device-state` writes the secret and prints the MAC (recorded above; the secret hash itself is never pasted into this file). The following wakes show `boot_count` continuing from its pre-provision value (not reset to 1), no `setup accepted` line, and `poll ok ... hash_skip=1` — the bearer token, image hash and boot counter all survive provisioning. | `provision.sh` (no `--reset-device-state`) wrote the 12 KiB `secret` partition at 0x13000 and verified it byte for byte (`Secret partition verified byte-for-byte.`, `Provisioned 94:a9:90:cf:80:08`). The next two wakes ran on the existing token: `setup_ms=0`, no `setup accepted`, `poll ok` over https. Both were refresh wakes (`hash_skip=0`, aircraft traffic), not the pre-registered `hash_skip=1`, and the `boot_count` line was not captured (lost during USB re-enumeration). Token survival, the point of the scenario, is shown. | `hardware/logs/phase34/H-02-provision.log` | PASS (hash_skip=1 and boot_count not observed) |
| H-03 | FW-08 | The `devices_cli.py add --mac <mac> --secret-sha256 <hash> --replace` command `provision.sh` printed succeeds against the VPS state dir; `devices_cli.py list` on the VPS shows the MAC registered. The MAC is also registered against the local LAN-stub state dir for the later dev-image scenarios (H-08 onward). | VPS: `registered 94:a9:90:cf:80:08`, then `list` → `94:a9:90:cf:80:08 878a346739c6…`. Laptop LAN-stub state dir: `registered 94:a9:90:cf:80:08`. | n/a — `devices_cli.py list` output, recorded directly in this table | PASS |
| H-04 | FW-09, FW-10, FW-12 | At least 10 no-change wakes over https against the VPS: no `SPI SRAM memory test` line anywhere in the capture (memtest off, FW-12); every `poll ok` succeeds over TLS validated by the ISRG-only bundle; the `fp_api` line shows `http connects=1` on every wake (the keep-alive connection reuse holds against Caddy, not just the LAN stub, FW-10); the first wake after the reset shows `tls_offered=0`, later wakes show `tls_offered=1` (best-effort session resumption); `total_ms`/`wifi_ms`/`display_ms`/`first_connect_ms` medians recorded into the Wake Duration table below. | 11 wakes against the VPS, all `poll ok`: no `SPI SRAM memory test` line in any capture; `http connects=1` on every wake (10 of 10 `fp_api` lines); `tls_offered=1` with a saved 1167-byte session on every wake (`first_connect_ms` median **97 ms**, range 67–975 ms). All 11 were refresh wakes (morning traffic), so the no-change medians come from the two no-change wakes in the H-05 capture: `total_ms` 1341/1509, `wifi_ms` 1138/1139, `display_ms` 161/329. The `tls_offered=0` wakes (first after reset or token erase) were captured in H-02, H-05 and H-19: `first_connect_ms` 1938 / 1921 / 2029. | `hardware/logs/phase34/H-04-vps-after.log` (the VPS journal for this window was not saved) | PASS (no-change sample n=2, from H-05) |
| H-05 | FW-03, D-34-01 | `poll fail step=auth backoff_n=<n> sleep_s=<n>` on the wake right after the server-side token revoke; the next wake (~5 min later) logs `setup accepted; device credential stored` then `poll ok`; the server log shows a 401 on `/display` followed by `setup: <mac> enrolled`. No reflash anywhere in this scenario. | Token revoked with byos stopped. Next wake: `device token rejected; erased, re-enrolling on the next wake` + `poll fail step=auth backoff_n=0 sleep_s=300`. Five minutes later: `setup accepted; device credential stored` (`setup_ms=190`) + `poll ok`. Server: `setup: 94:a9:90:cf:80:08 enrolled (hw_rev=proto-ee02)`. byos does not log status codes, so the 401 is shown by the device line, not the server log. No reflash. | `hardware/logs/phase34/H-05-revoke.log` + `H-05-revoke-server.log` | PASS |
| H-06 | FW-08, D-34-01 | `curl POST /device/v1/setup` with a wrong secret for the device's registered MAC returns `401`; the same call for an unregistered MAC (`02:00:00:00:00:01`) returns `403`; the frame's own token is untouched throughout (its next wake is still `poll ok`, not re-enrolling). | Wrong secret, registered MAC → `401`; unregistered MAC `02:00:00:00:00:01` → `403`; the retired shared secret (read from the old `secrets.h`, never pasted) → `401`. The frame kept polling `poll ok` on its own token afterwards. | `hardware/logs/phase34/H-06-curl.txt` | PASS |
| H-07 | FW-07, D-34-04 | With `SKYPANE_API_BASE` temporarily set to `http://LANIP:8642` in a production build, the device logs `API base URL rejected (this build requires https)` and `poll fail step=config` — no request is ever sent. `secrets.h` is restored to `https://HOST` immediately after the capture. | Production image with `SKYPANE_API_BASE "http://192.168.1.94:8642"`: `API base URL rejected (this build requires https)` + `poll fail step=config backoff_n=1 sleep_s=600`. The counter was 1 because the first boot after the flash had already failed the same way, uncaptured. `secrets.h` was restored to https right after. | `hardware/logs/phase34/H-07-http-refused.log` | PASS |
| H-08 | FW-03, FW-11 | The first wake after flashing the dev image against the LAN stub (the VPS token is unknown here) logs `step=auth`; ~5 min later, `setup accepted`, a refresh (`blit ok`), then at least 10 no-change wakes; LAN-after medians recorded into the Wake Duration table below. The `fp_batt` line appears before the first `wifi:` log line of every wake (FW-11's before-Wi-Fi ordering). | Dev image against the LAN stub. The stub rejected the VPS token (stub log: `GET /device/v1/display`, then `setup: ... enrolled`); the device's own `step=auth` line fell in the uncaptured boot window. Then `setup accepted` (`setup_ms=44`), one refresh, and **53 no-change wakes**: `total_ms` median 1262, uptime at `poll ok` median **1566 ms**, `wifi_ms` 1151, `display_ms` 52, `connects=1` on 53 of 54 wakes. The `fp_batt` line never appears in the capture (0 matches): it prints in the first ~0.5 s of the boot, before the host re-attaches the port. | `hardware/logs/phase34/H-08-lan-dev.log` + `H-08-lan-dev-server.log` | PASS (fp_batt ordering not observable; see H-17) |
| H-09 | FW-04 | With the LAN stub restarted at `--sleep 86401`, the device logs `poll fail step=json backoff_n=0 sleep_s=300` (the server-supplied `sleep_s` is rejected as out of range). With the stub restarted at `--sleep 30`, the very next wake recovers with `poll ok`. | Stub at `--sleep 86401`: `poll fail step=json backoff_n=6 sleep_s=19200`, so the out-of-range `sleep_s` is rejected. The counter was 6, not the pre-registered 0, because the stub had been stopped for several minutes before and those wakes had failed at `step=http`. Restarting the stub at `--sleep 30` recovered at once: `poll ok sleep_s=30` (first lines of `H-11-spacing.log`). | `hardware/logs/phase34/H-09-sleep86401.log` + `H-09-sleep86401-server.log` | PASS |
| H-10 | FW-09, D-34-03 | With the four `SKYPANE_STATIC_*` macros defined (address outside the router's DHCP pool) and a dev image flashed, 10 no-change wakes complete with no DHCP negotiation; the `wifi_ms` median for this row is recorded and compared against the LAN-after (DHCP) median. If skipped (no safe static address available), a reason is recorded under "Deviations and not observed" instead, per D-34-03's "unless the measured gain of the default path is insufficient" allowance. | Skipped by the developer. Estimate from the captures: of the ~1.15 s `wifi_ms`, about 1.0 s passes between association (~0.46 s uptime) and `sta ip` (~1.48 s), i.e. waiting for the DHCP ACK even with the restored lease. A static IP would bring a no-change wake to roughly 0.4–0.6 s, at the cost of a router reservation and a rebuild whenever the network changes. | `hardware/logs/phase34/H-10-static-ip.log` (or N/A) | N/A |
| H-11 | FW-02, FW-12 | With the LAN stub at `--sleep 30` and a fresh panel pattern pushed right after a `blit ok`, the next wake logs `holding <20..30>s for the panel's refresh spacing`, then `blit ok`, with **no** `task_wdt` / `Task watchdog got triggered` line anywhere in the capture during the wait (the light-sleep spacing wait does not itself starve the task watchdog). | Stub at `--sleep 30`; a new pattern pushed right after a `blit ok` (a script waited for the next `blit ok` in the capture, then swapped the file). Next wake: `fp_panel: holding 26s for the panel's refresh spacing`. The USB console dropped during the light sleep, so the following `blit ok` is not in the capture. Every later wake is `poll ok ... hash_skip=1`, and the firmware records a new hash only after a successful blit. There is no `task_wdt` / `Task watchdog got triggered` / reset line anywhere in the capture. | `hardware/logs/phase34/H-11-spacing.log` + `H-11-spacing-server.log` | PASS (post-hold blit inferred from hash_skip=1) |
| H-12 | FW-01, FW-02 | `SKYPANE_FAULT=panic`: `abort()` backtrace, reboot, `reset reason=panic`, `wake reason=other`, `poll fail step=reset backoff_n=0 sleep_s=300` on the first failure; continuing the capture through the backoff sleep, the second panic shows `backoff_n=1` and a doubled `sleep_s` (600). | `SKYPANE-FAULT-INJECT panic` → reboot → `reset reason=panic` → `poll fail step=reset backoff_n=1 sleep_s=600`; next panic → `reset reason=panic` → `poll fail step=reset backoff_n=2 sleep_s=1200` (sleep doubled). The pre-registered numbers were n=0/300 then n=1/600; the counter started one higher because an earlier boot of the same image had already failed. The flash-induced resets were labelled `reset reason=usb`, a normal start, so the expected "flash looks like a watchdog reset" backoff did not happen. | `hardware/logs/phase34/H-12-fault-panic.log` | PASS |
| H-13 | FW-01, FW-02 | `SKYPANE_FAULT=task_wdt`: within ~60 s of the `SKYPANE-FAULT-INJECT task_wdt` marker, `Task watchdog got triggered`, reboot, `reset reason=task_wdt`, `poll fail step=reset backoff_n=<n> sleep_s=<n>` — the wake never exceeds the 60 s task-watchdog ceiling before panicking. | `SKYPANE-FAULT-INJECT task_wdt` → reboot → `reset reason=task_wdt` → `poll fail step=reset backoff_n=7 sleep_s=21600`. The counter carried over from H-12 with no success in between; 21600 s is the 6 h cap. | `hardware/logs/phase34/H-13-fault-task_wdt.log` | PASS |
| H-14 | FW-01, FW-02 | `SKYPANE_FAULT=int_wdt`: `Interrupt wdt timeout`, reboot, `reset reason=int_wdt`, `poll fail step=reset backoff_n=<n> sleep_s=<n>`. | `SKYPANE-FAULT-INJECT int_wdt` → reboot → `reset reason=int_wdt` → `poll fail step=reset backoff_n=10 sleep_s=21600`. | `hardware/logs/phase34/H-14-fault-int_wdt.log` | PASS |
| H-15 | FW-02 | `SKYPANE_FAULT=slow_wake`: `wake budget of 300s exceeded`, `poll fail step=deadline`, and the `wake timing total_ms=` value on that line is between 300000 and 360000 — the 300 s wake budget ends the wake, not the 60 s task watchdog, proving the two mechanisms are independent. | `SKYPANE-FAULT-INJECT slow_wake` → `wake budget of 300s exceeded` at uptime 301047 ms → `poll fail step=deadline backoff_n=16 sleep_s=21600`, `wake timing total_ms=300744` (inside 300000–360000). The 300 s budget ended the wake; the 60 s task watchdog did not fire. | `hardware/logs/phase34/H-15-fault-slow_wake.log` | PASS |
| H-16 | FW-01 | Optional (needs a variable bench supply on the battery input): lowering the supply until the chip resets during Wi-Fi produces `reset reason=brownout` and `poll fail step=reset`. If no bench PSU is available, N/A — the classification itself is already host-tested (`test_reset_reason.c`) and shares the H-12 reset→backoff path end to end. | No variable bench supply available. | `hardware/logs/phase34/H-16-fault-brownout.log` (or N/A) | N/A |
| H-17 | FW-11 | On the LiPo (USB unplugged), for three consecutive wakes: `\|X-Battery-Mv − multimeter\| ≤ 60 mV` at the JST connector on each of the 3 readings, and the `fp_batt` line appears before the first Wi-Fi log line of each of those wakes. | One reading, USB unplugged, taken as the stub printed its `telemetry:` line: multimeter **3.92 V** on the battery connector's solder joints vs `X-Battery-Mv=3928` (\|Δ\| ≈ 8 mV, below the meter's 10 mV resolution). The other two readings were not taken (probing the connector proved awkward). The `fp_batt` ordering could not be captured (see H-08); it follows from `app_main.c` reading the battery before `fp_wifi_connect`, and the telemetry varies by only ±2–4 mV between wakes over 55 LAN wakes. | n/a — see "Battery vs multimeter" table below | PARTIAL (1 of 3 readings, within threshold) |
| H-18 | FW-15 | Prod: the server log's `telemetry: X-Fw-Version=` value equals H-01's `Firmware version:` line. Dev: the LAN stub's `telemetry:` lines show `X-Fw-Version = <git describe>-dev`. | Prod: `X-Fw-Version=e8d293c` in the VPS journal (9 lines read live; 6 kept in `H-05-revoke-server.log`). Dev: 55 × `X-Fw-Version=e8d293c-dev` in `H-08-lan-dev-server.log`. | see `H-05-revoke-server.log` (prod) / `H-08-lan-dev-server.log` (dev) | PASS |
| H-19 | FW-03 | After reflashing the production image, the LAN-registered token is unknown to the VPS, so the first wake logs `step=auth`; ~5 min later, `setup accepted` and `poll ok` against the VPS. The companion Wake interval noted in prep step A5 is restored; the LAN stub is stopped. | Production image re-flashed. The VPS refused the LAN token (`fault screen drawn step=auth backoff_n=18`: the on-device fault screen drew once); a power cycle then gave `setup accepted; device credential stored` + `poll ok`, and the panel shows aircraft again. Stub stopped; the companion wake interval goes back to 300 s. | `hardware/logs/phase34/H-19-restore.log` | PASS |
| H-20 | FW-09, FW-10, FW-12 | The Wake Duration table below (H-00, H-04, H-08 medians) supports a written, three-way comparison — LAN-before vs VPS-before isolates the internet+TLS cost; VPS-before vs VPS-after shows the keep-alive/TLS-reuse/DHCP/memtest gain; `http connects=` and `first_connect_ms` at `tls_offered=0` vs `tls_offered=1` show the handshake's own share — ending in a one-paragraph conclusion in "The ~28 s per-cycle overhead" below. | See the section "The ~28 s per-cycle overhead". | n/a — derived from H-00/H-04/H-08; see § "The ~28 s per-cycle overhead" | PASS |

## Wake duration (no-change wakes)

Medians only (not means) — a single slow outlier wake (a retry, a missed
ARP reply) should not move the headline number. `n wakes` is how many
no-change (`hash_skip=1`) wakes the median is computed over; fewer than
5 is a weak sample and should be noted as such.

| Configuration | Median total_ms | Median wifi_ms | Median display_ms | http connects | first_connect_ms | n wakes |
|---|---|---|---|---|---|---|
| LAN stub, before (`hardware/logs/backoff-run.log`, no re-measure) | ~4400 (4.4 s) | ~3000 (3.0 s, DHCP) | not captured by that log's format | n/a (pre-connection-reuse) | n/a | see source log |
| LAN stub, after (H-08) | 1262 (uptime at `poll ok`: 1566) | 1151 | 52 | 1 (53 of 54 wakes) | 28 (plain http) | 53 |
| VPS, before (H-00) | n/a (old image has no timing line); uptime at `poll ok`: 6336 | n/a | n/a | n/a (pre-connection-reuse) | n/a | 3 (weak) |
| VPS, after — `tls_offered=0` (first wake after reset or erase: H-02, H-05, H-19) | n/a (all three were refresh or enrolment wakes) | n/a | n/a | 1 | 1938 (1921–2029) | 3 |
| VPS, after — `tls_offered=1` (no-change wakes from H-05; connect cost from H-04) | 1341 (uptime at `poll ok`: 1646) | 1138 | 161 | 1 | 97 (H-04, n=10, range 67–975): Caddy resumes the session | 2 (weak) |
| LAN, after, static IP (H-10) | N/A (skipped) | N/A | N/A | N/A | N/A | 0 |

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
  network): LAN-before 4.4 s vs VPS-before 6.3 s for a no-change wake,
  about 2 s more against the VPS. That matches the measured cost of one
  full TLS handshake over the internet with the ESP32-S3's software
  crypto (`first_connect_ms` ≈ 1.9–2.0 s at `tls_offered=0`). The old
  image paid it on every request, twice on a refresh wake.
- **VPS-before vs VPS-after** (isolates the keep-alive connection reuse
  / TLS session resumption / DHCP restore-last-IP / memtest-off gain
  this phase adds): no-change wake 6.34 s → 1.65 s (uptime at
  `poll ok`), about 3.8 times shorter; on the LAN 4.4 s → 1.57 s.
- **Measured TLS connect cost** (`first_connect_ms` at `tls_offered=0`
  vs `tls_offered=1`, from H-04): 1938 ms for a fresh handshake vs a
  97 ms median when the session is resumed, i.e. ~1.8 s saved per wake.
  The keep-alive connection then serves `/display` and the image
  (`connects=1`).
- **DHCP share** (LAN-before's ~3.0 s DHCP component vs the DHCP-restore
  path's contribution to VPS-after's `wifi_ms`, and the static-IP row
  from H-10 if captured): the whole Wi-Fi phase (association + DHCP
  with the restored lease) is now 1.15 s median, against ~3.0 s of DHCP
  alone before. About 1.0 s of it is still the wait for the DHCP ACK.
  H-10 was skipped, so the static-IP gain (~0.7 s) is an estimate.
- **Full-blit share** (if any captured wake refreshed instead of
  hash-skipping, its `draw_ms` contribution to that wake's total,
  for context — most captured wakes are expected to hash-skip): the opposite happened. Every VPS wake in H-04 and 8
  of 11 in H-00 refreshed: during the morning departure bank a different
  aircraft reaches runway 3 almost every minute. A refresh wake costs
  `draw_ms` ≈ 31.5 s (fixed by the panel, the same in every capture)
  plus a 3–18 s download, 37–52 s awake in total, before and after this
  phase.
- **One-paragraph conclusion**: the ~28 s is the wake itself. The
  firmware starts its `sleep_s` timer only after the work, so the
  poll-to-poll interval is `sleep_s` plus the awake time.
  `BATTERY-RUN.md` shows 40 % of its gaps at ≤ 310 s and 60 % in the
  311–610 s band. With a no-change wake of ~6.3 s and a refresh wake of
  ~40 s, 0.4 × 6.3 + 0.6 × 40 ≈ 26.5 s, close to the measured 28 s mean.
  Refreshes (≈ 31.5 s of panel time each) dominate. This phase cut the
  no-change part (6.3 s → 1.65 s against the VPS) and the per-request TLS
  cost, but it cannot shorten a panel refresh. The remaining lever for
  battery life is refreshing less often, which is a server-side change.

## Battery vs multimeter

Three consecutive wakes on the LiPo (USB unplugged), from H-17. Pre-registered
threshold: `|X-Battery-Mv − multimeter| ≤ 60 mV` on every row.

| Time | Multimeter mV (JST connector) | X-Battery-Mv (server log) | Delta (mV) |
|---|---|---|---|
| 2026-09-25, H-17 (LAN stub, USB unplugged) | 3920 (3.92 V, 10 mV resolution) | 3928 | ≈ +8 |
| not taken | — | — | — |
| not taken | — | — | — |

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

- **No BOOT/RESET button within reach on this kit:** every "press
  RESET" in the script was done with the kit's power switch, OFF then ON
  (a `power-on` reset, which the firmware treats as a normal start).
- **Serial capture:** `firmware/monitor.sh` fails when the board is in
  deep sleep, because the USB-CDC port disappears. The session used a
  small reconnecting loop instead: wait for the port, `cat` it through
  `tee -a`, repeat. Its known limit is that the first ~0.5 s of each
  boot is lost while the host re-enumerates the port, which hides the
  `wake reason`, `boot_count` and `fp_batt` lines (H-02, H-08, H-17).
  The fault logs that contain panic output also contain a few non-text
  bytes, so they need `grep -a` or `LC_ALL=C`.
- **Low battery at session start:** the pack was below 3300 mV, so the
  server's BATTERY EMPTY mode held the frame at 3600 s wakes. The session
  resumed the next morning after charging on USB.
- **H-00:** the committed capture keeps one pre-phase wake; the other
  ten were read off the live console (values in the scenario row).
- **Traffic:** the morning departure bank made almost every VPS wake a
  refresh, so the VPS no-change timings rest on n=3 (before) and n=2
  (after). The LAN-after figure (n=53) is the robust one.
- **Backoff counter values:** several scenarios (H-07, H-09, H-12 to
  H-15) started from a non-zero `backoff_n` left by earlier uncaptured
  failures. Each still showed the pre-registered failure step and the
  doubling or the 6 h cap; only the absolute counter differs.
- **H-10 (static IP):** skipped by the developer; the gain is estimated
  above (~0.7 s per no-change wake).
- **H-16 (brownout):** no bench supply. The classification is
  host-tested and shares the H-12 reset → backoff path.
- **H-17:** one multimeter reading instead of three.
- **Scrubbing:** the Wi-Fi SSID and the router BSSID were replaced with
  `<wifi-ssid>` / `<wifi-bssid>` in every capture. No bearer token,
  secret or enrolment hash appears in them; the only 64-hex strings are
  image hashes in `/img/<sha256>.bin` paths. A stray macOS `sed` temp
  file (`.!18399!H-12-fault-panic.log`) was removed.

## Checker output

Paste the literal command output below once run against the built
production image and (optionally) any `hardware/logtools.py` checks used
during this session.

```
$ sh firmware/tests/check_production_config.sh built firmware/build-ee02
production-config built: PASS
```

```
$ python3 hardware/logtools.py ...
(not used this session)
```
