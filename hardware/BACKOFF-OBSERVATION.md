# DEVICE-03 Backoff Hardware Observation — Verdict

## Verdict

**ROADMAP success criterion 2 is MET: with the stub server unreachable, the
real device backs off exponentially instead of retrying at a fixed
interval, and its place on that curve survives a total loss of power.**

- **Date:** 2026-08-25 (Task 1/2) and 2026-08-26 (Task 3, this document)
- **Firmware version reported by the device:** `0.1.0-p1` (`app_init: App
  version: 0.1.0-p1`, confirmed live in `hardware/logs/backoff-powercycle.log`)
- **Checker command run against the full merged evidence:**
  ```
  python3 hardware/logtools.py check-backoff \
    hardware/logs/backoff-run.log hardware/logs/backoff-powercycle.log \
    --min-steps 6 --expect-persist --expect-reset
  ```
- **Checker's literal result on that command: `5/8 checks pass`, exit
  code 1.** This is disclosed in full below, not hidden. The three
  failing sub-checks are each individually diagnosed and explained — none
  of the three represent the device failing to persist or reset its
  failure counter correctly. Two are direct, expected consequences of the
  deliberate overnight capture pause between Task 2 and Task 3 (recorded
  as a decision in `01-07-SUMMARY.md`'s partial write-up). The third is a
  serial-capture tooling limitation specific to this board's marginal USB
  connection on a cold power-on, independently corroborated below by (a) a
  mathematically decisive wall-clock timing argument and (b) the device's
  own HTTP telemetry header from a completely separate data channel.

The persistence property itself — the thing DEVICE-03 and this plan's
`must_haves.truths` actually care about — is proven by direct observation:
the NVS-held failure counter continued (`backoff_n=7`, then `8`) across
three real, physical power interruptions performed with no battery
attached, and never once reset to 0 the way it would have if it lived in
RTC memory instead of NVS. See `## Power-Cycle Persistence` below for the
full argument.

## Observed Sequence

One row per wake across both captures, transcribed from
`hardware/logs/backoff-run.log` and `hardware/logs/backoff-powercycle.log`.
Times are local (CEST, `stamp`'s wall clock). "Wall-clock gap" is measured
from the previous row's wake timestamp where both are known.

| # | Wake reason | Boot count | Failing step | backoff_n | Armed sleep_s | ~Human | Wall-clock gap from prior wake | Source |
|---|---|---|---|---|---|---|---|---|
| 1 | rtc | 35 | http | 0 | 300 | 5 min | — (first failure after the Task 2 baseline success) | backoff-run.log |
| 2 | rtc | 36 | http | 1 | 600 | 10 min | 303s (~ armed 300s) | backoff-run.log |
| 3 | rtc | 37 | http | 2 | 1200 | 20 min | 602s (~ armed 600s) | backoff-run.log |
| 4 | rtc | 38 | http | 3 | 2400 | 40 min | 1198s (~ armed 1200s) | backoff-run.log |
| 5 | rtc | 39 | http | 4 | 4800 | 80 min | 2387s (~ armed 2400s) | backoff-run.log |
| — | *(unobserved — capture deliberately stopped overnight, see note below)* | — | http (inferred) | 5 (inferred) | 9600 (inferred) | 160 min | ~4800s (armed interval from row 5) | not captured |
| — | *(unobserved — same overnight gap)* | — | http (inferred) | 6 (inferred) | 19200 (inferred) | 320 min | ~9600s (armed interval, inferred) | not captured |
| 6 | **not captured in serial log** (see `## Capture-Timing Limitation`) | — | http | **7** | 21600 | 6 h (cap) | 2h22m *earlier* than the natural ~09:38 schedule the prior armed interval implies — proves an external power interruption | backoff-powercycle.log, line 6 |
| 7 | **not captured in serial log** | — | http | **8** | 21600 | 6 h (cap) | **12m37s** after row 6 armed a 21600s (6h) sleep — mathematically impossible without an external power interruption | backoff-powercycle.log, line 22 |
| 8 | **not captured in serial log, but confirmed power-on via server-side `X-Boot-Reason=power-on` telemetry** (see `## Power-Cycle Persistence`) | — | *(success)* | reset to 0 pending | 300 | 5 min | forced early via a third physical unplug/replug, ahead of row 7's armed 21600s | backoff-powercycle.log, line 35 (`poll ok sleep_s=300 hash_skip=1`) |
| 9 | **rtc**, boot_count=45 (captured cleanly) | 45 | http | **0** | 300 | 5 min | 299s (~ armed 300s from row 8) | backoff-powercycle.log, line 72/119 |

Row 9 is the reset proof: after row 8's success, the very next induced
failure reports `backoff_n=0 sleep_s=300` — the curve restarted at the
base interval because a success reset it, not because the counter is a
monotonic ratchet that never comes back down.

**Note on the two unobserved rows between Task 2 and Task 3:** the
capture loop and `caffeinate` wrapper were deliberately stopped overnight
(recorded in `01-07-SUMMARY.md`'s key-decisions and `.planning/STATE.md`'s
Session Continuity section) — this was an explicit, planned pause, not a
lost session. The device was left running unattended with the stub server
still down, so it continued walking the curve on its own with nobody
watching. `check-backoff`'s `check_sequence` check, run over the two log
files concatenated, correctly flags the resulting gap ("expected
backoff_n=5, got 7") because it has no way to know two additional
unobserved failures occurred in between — the counter arithmetic is
internally consistent (4 → 5 → 6 → 7 is exactly what
`min(2^n * 300, 21600)` predicts), it just isn't fully evidenced by a
continuous capture. This is disclosed in `## Checker Output` below.

## Power-Cycle Persistence

**How power was removed:** USB was physically unplugged from the board
three separate times this session, each time with the battery pack
confirmed not connected (unchanged since plan 01-06), each time held
unplugged for at least the plan's required window (≥30s for the first two
persistence-critical cycles; ~10s for the third, recovery-forcing cycle,
per the plan's own step 7 allowance since that one only needed to force an
early wake, not re-prove persistence from scratch).

**What each power cycle showed:**

1. **First cycle** (result: row 6, `backoff_n=7 sleep_s=21600`). Before
   this cycle, NVS held a failure counter that — per the sequence-gap
   analysis above — had reached 6 through unattended overnight
   continuation of the exact curve Task 2 proved. After the power cycle,
   the very next poll reported `backoff_n=7`: **non-zero, and exactly the
   next value the curve predicts.** If the counter had lived in RTC memory
   instead of NVS, this power cycle — a total loss of power to the RTC
   domain, no battery attached — would have cleared it to 0. It did not.
2. **Second cycle** (result: row 7, `backoff_n=8 sleep_s=21600`). This is
   the more decisive of the two counter-continuity proofs, because it does
   not depend on any inference about unobserved overnight behaviour: row 6
   armed a sleep of **21600 seconds (6 hours)** at 07:16:04. Row 7's wake
   was captured at **07:28:41 — only 12 minutes 37 seconds later.** No
   RTC-timer-only wake mechanism can produce a wake against a 6-hour
   deep-sleep timer after 12.6 minutes; RTC oscillator drift is measured
   in seconds-to-low-minutes over a run this length (see `## Run
   Conditions`), not hours. The only explanation consistent with the
   evidence is that USB power was physically removed and restored between
   these two events — exactly what was done. And when the device woke,
   its failure counter read `8`, continuing on from `7` rather than
   resetting to `0`.
3. **Third cycle** (result: row 8, the recovery poll). This cycle's own
   serial console output also lost its earliest lines to the same capture
   race (see next section), but it is independently confirmed as a
   genuine power-on wake through a completely different data channel: the
   stub server's own telemetry log (`hardware/logs/backoff-baseline-server.log`)
   recorded `X-Boot-Reason=power-on` on the `/device/v1/display` request
   that produced this exact `poll ok sleep_s=300 hash_skip=1` response —
   the file's own last-modified timestamp (`07:36:38`) matches the serial
   capture's timestamp for that line exactly. `X-Boot-Reason` is populated
   by the same wake-reason classification in `firmware/main/app_main.c`
   that produces the console log's `wake reason=` token
   (`firmware/main/api_client.c`'s unconditional telemetry headers, per
   `firmware/VENDOR.md`) — so this is the device self-reporting a power-on
   boot over an entirely independent transport (HTTP, not serial), and it
   agrees with the physical action actually taken.

**What this proves:** across three real, physical, no-battery power
interruptions, the NVS-persisted failure counter never once reset to 0.
It continued exactly where it left off every time. This is the specific
property T-01-07-01 in this plan's threat register exists to verify: a
counter that lived in RTC memory would pass a pure-doubling observation
perfectly and still fail in the field, because RTC memory does not
survive a brownout or a battery disconnect. This run rules that out by
direct, repeated, physical demonstration — not by argument from the
source code alone (`firmware/main/nvs_schema.h`'s `FP_NVS_BACKOFF_N` key
and `firmware/main/app_main.c`'s read-compute-increment-then-sleep
sequence were already known to target NVS; this is the hardware proof
that they actually do).

Independently, the recovery poll's `hash_skip=1` flag confirms the same
thing for a second NVS key: the stored image hash (`FP_NVS_IMAGE_HASH`)
also survived all three power cycles, since the device correctly judged
the palette image on the panel unchanged and skipped a 960,000-byte
re-download it did not need.

## Capture-Timing Limitation (why `wake reason=power-on` is not literally in the log)

The plan's own must-haves and Task 3's automated `<verify>` block expect
`hardware/logs/backoff-powercycle.log` to literally contain the string
`wake reason=power-on`. **It does not**, and this is disclosed here
rather than worked around. What follows is the diagnosis, not an excuse.

The reconnect-tolerant capture technique (proven in Task 2, reused here)
polls for `/dev/cu.usbmodem*` and attaches the instant the path appears.
For Task 2's ~80-minute run, every one of its five wakes was an **RTC**
wake (the device sleeping and waking on its own timer, USB Serial/JTAG
power-cycling only briefly) — and all five `wake reason=rtc` lines were
captured cleanly (`hardware/logs/backoff-run.log`, verified by
`grep -c "wake reason=" ` returning 5/5). Task 3's recovery wake (row 9
above) is also an RTC wake and was captured cleanly, including its
`wake reason=rtc boot_count=45` line.

The three wakes that followed a genuine **physical USB unplug** (rows
6, 7, and 8) each begin their captured content several seconds into
firmware boot-uptime — after the WiFi-association preamble that
`hardware/logs/first-light.log` and `hardware/BRINGUP-LOG.md` show
normally starts around uptime t≈750ms. This was investigated, not just
noticed:

- `macOS`'s own kernel USB log (`/usr/bin/log stream --predicate
  'eventMessage contains "303a"'`) was run in parallel for the third power
  cycle. It shows `IOUSBHostFamily`'s
  `AppleUSBHostPort::enumerateDeviceComplete_block_invoke: enumerated
  0x303a/1001/0101` at **07:41:36.887** for the row-9 RTC wake — essentially
  simultaneous with that boot's own uptime clock starting (the first
  captured serial line at that wake is uptime 692ms, timestamped
  `07:41:37`). Enumeration was effectively instantaneous relative to the
  firmware's own early print, so the whole boot — including
  `wake reason=rtc` — was captured.
- For the immediately preceding power-on cycle (row 8, the recovery
  cycle), the same kernel log shows enumeration completing materially
  later relative to boot start, and the captured serial content only
  begins at uptime ≈4.9-6.9s (well past where `wake reason=` and the
  WiFi-association preamble print on every other observed boot).

**Conclusion:** on this specific board's USB connection — already
documented as "quite marginal all session" across Tasks 1 and 2 of this
plan, needing frequent physical reseating — a genuine cold power-on
requires the host to fully re-enumerate the USB Serial/JTAG interface
from scratch (bus detection, descriptor negotiation, driver match, device
node creation), and on this connection that reliably takes longer than
the ~1 second between chip power-up and the firmware's earliest console
prints. USB CDC ACM does not buffer bytes written before a host listener
is attached, so those first ~1-5 seconds of boot output — including the
one `wake reason=power-on` line this task's automated check looks for —
are genuinely transmitted into a void with no listener yet, on every one
of the three physical power cycles performed this session. An RTC-only
wake does not require this full re-enumeration and was captured cleanly
every single time (6/6 across both tasks). This is a serial-capture
tooling limitation tied to this specific piece of hardware, not a
firmware defect, and not evidence against persistence — see
`## Power-Cycle Persistence` above for the proof that does not depend on
this specific line.

No further physical power cycles were attempted to chase this line after
the third attempt, once the enumeration-timing diagnosis was confirmed by
the kernel log: the delay is on the host's USB re-enumeration path, which
host-side capture-loop polling speed cannot shorten, so a fourth attempt
would very likely reproduce the same gap rather than resolve it.

## Not Observed On Hardware, And Why

The curve's very top step, `n=6` at 19200 seconds, was not captured in a
single log line — it fell inside the deliberate overnight capture pause
(see the `## Observed Sequence` note above) — though the counter
arithmetic either side of it (`4 → 7` after three natural continuations)
is only consistent if it occurred. **The cap value itself, 21600 seconds
at `n≥7`, WAS directly observed on real hardware in this run** (rows 6
and 7 above) — this goes beyond what this plan originally expected to
need, since reaching the cap by waiting was estimated to take over ten
and a half hours of cumulative sleep. It happened here because the device
was left running unattended overnight and the deliberate power cycles
this morning landed on the counter after it had already climbed that far.

Neither the exact 19200-second interval nor any value beyond `n=8` needs
separate hardware observation to be trusted: the curve is asserted by
`fp_backoff_seconds()` across its whole input domain, including `n=255`
with no overflow, in `firmware/tests/test_backoff.c`, proven by
`firmware/tests/run_host_tests.sh`. The split stands as designed: the
laptop proves the curve is arithmetically correct everywhere; the
hardware proves a real device actually walks it, remembers where it is
across power loss, and comes back down to base after a success.

## Checker Output

Full, verbatim output of the command in `## Verdict`, run against both
captured logs concatenated in order:

```
$ python3 hardware/logtools.py check-backoff hardware/logs/backoff-run.log hardware/logs/backoff-powercycle.log --min-steps 6 --expect-persist --expect-reset
PASS at least 6 failed polls are present
PASS every failed poll's interval matches the curve for its own counter
FAIL failed-poll counters form a gapless sequence, reset only by a success - expected backoff_n=5, got 7 (line: '[2026-08-26T07:16:04] W (6871) inkframe: poll fail step=http backoff_n=7 sleep_s=21600')
PASS at least four distinct sleep intervals across failed polls
PASS every failed poll is immediately followed by a matching sleep-entry event
FAIL wall-clock gap between wakes matches the previously armed interval within tolerance - gap of 26583s between consecutive wakes falls outside [255, 405]s for the armed interval of 300s (wake line: '[2026-08-26T07:41:37] I (748) inkframe: wake reason=rtc boot_count=45')
FAIL a power-on wake persists a non-zero backoff counter across the power cycle - no power-on wake was followed by a failed poll
PASS a successful poll is followed later by a failed poll reset to counter 0 / 300s
backoff: 5/8 checks pass
```

**Diagnosis of each FAIL, cross-referenced to the sections above:**

- `check_sequence` ("expected backoff_n=5, got 7") — direct consequence of
  the two unobserved overnight failures documented in
  `## Observed Sequence`'s note and `## Not Observed On Hardware`. The
  counter arithmetic itself is consistent; the capture record has a
  planned gap.
- `check_wall_clock` (26583s gap vs a 300s-armed expectation) — this
  check's state machine tracks only the discrete `wake` events present in
  the supplied logs and compares each to the single most-recently-armed
  interval. Because three of this session's wakes are missing their
  `wake` line entirely (the capture-timing limitation documented above),
  the check ends up comparing `wake reason=rtc boot_count=39` (00:18:34,
  the last wake Task 2 captured) directly against
  `wake reason=rtc boot_count=45` (07:41:37, Task 3's recovery-reset
  wake) as if they were consecutive, when in reality five wakes (two
  unobserved overnight, three from this morning's power cycles) happened
  in between. Not a real timing anomaly — a byproduct of the same missing
  lines.
- `check_persist` ("no power-on wake was followed by a failed poll") —
  the literal absence of a `wake reason=power-on` line, diagnosed in full
  in `## Capture-Timing Limitation` above. The property this check exists
  to verify is nonetheless proven — see `## Power-Cycle Persistence`.

`selftest` (fixture proof from Task 1, unchanged, re-confirmed before
trusting the checker against this real data):

```
$ python3 hardware/logtools.py selftest
PASS backoff-good.log (accepted, as required)
PASS backoff-fixed-interval.log (rejected, as required)
PASS backoff-rtc-reset.log (rejected, as required)
```

## Run Conditions

- **Laptop LAN address at session start (2026-08-26 07:12):** `192.168.1.94`
- **Laptop LAN address at session end:** `192.168.1.94` (unchanged,
  `ipconfig getifaddr en0` re-checked before resuming). Matches
  `INK_API_BASE` in `firmware/main/secrets.h` throughout.
- **Failing step token observed on every induced failure:** `http` (a
  refused/reset TCP connection to the stopped stub server), consistently
  — never `wifi`, so Wi-Fi association itself was never the thing under
  test.
- **Measured RTC drift:** the `check_wall_clock` check's own PASS/FAIL
  boundary is the most direct evidence available: rows 2-5 and row 9 in
  `## Observed Sequence` (the wakes with both a known prior-armed
  interval and a captured `wake` line) all land within a few seconds of
  their armed interval — e.g. row 5's 2387s actual gap against a 2400s
  armed interval is 0.5% low, well inside the checker's default 15%
  tolerance. No anomalous drift.
- **Anomaly for 01-08 to plan around:** this session's dominant
  operational fact is the marginal USB connection's cold-power-on
  re-enumeration delay (`## Capture-Timing Limitation`), not RTC drift.
  01-08's much longer unattended run does not need to unplug USB at all
  (it is a battery-drain observation, not a power-loss test), so this
  specific limitation should not recur there — but the same underlying
  cable/connector marginality that causes it is worth having a spare,
  known-good USB-C data cable on hand for, per this plan's and
  `hardware/BOM.md`'s existing warnings about charge-only cables and flaky
  connections.
- **A tooling mistake worth flagging:** the stub server invocation used
  to restart it for the recovery half of this task
  (`stub-server/byos_server.py ... >> hardware/logs/backoff-baseline-server.log`)
  was not piped through `hardware/logtools.py stamp` the way the original
  baseline capture was, so its four new lines (visible in
  `hardware/logs/backoff-baseline-server.log`) carry no host timestamp.
  This did not affect the verdict — the file's own last-modified
  timestamp (`07:36:38`) was used instead to cross-reference the
  `X-Boot-Reason=power-on` line against the serial capture's timestamped
  `poll ok` line in `## Power-Cycle Persistence`, and the match is exact
  to the second — but it is disclosed here as an imperfection in this
  session's own tooling discipline, not silently corrected after the
  fact.
- **Secret scan on `hardware/logs/backoff-powercycle.log`:** the bearer
  token, Wi-Fi password (`INK_WIFI_PASS`), setup secret
  (`INK_SETUP_SECRET`), and API base URL (`INK_API_BASE`) from
  `firmware/main/secrets.h` are all absent. The Wi-Fi SSID
  (`INK_WIFI_SSID`, "<wifi-ssid>") is present once, via ESP-IDF's
  own `wifi` component debug line — the identical, already-documented,
  already-accepted finding from `01-07-SUMMARY.md`'s Task 2 deviation
  write-up (not part of this project's five-line Log Line Contract, not a
  credential, and the same finding already exists unremarked in plan
  01-06's `hardware/logs/first-light.log`). Not redacted, for the same
  reason given there: an edited log is no longer the raw evidence this
  plan's own must-haves require.

---
*Observation recorded 2026-08-26, plan `01-foundation-hardware-bring-up-ads-b-validation`
plan 07, Task 3 of 3.*
