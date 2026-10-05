# SkyPane — Phase 1 Battery Discharge Run (DEVICE-05)

This file is the recorded DEVICE-05 verdict for the SkyPane device: whether
it completes many consecutive wake, poll and sleep cycles on battery power
alone, and the measured mAh-per-cycle figure that follows from that run.

## Run Protocol (pre-registered)

Written by Task 1, **before the battery pack was ever connected to the
board** — this is the point of writing it now rather than after the run:
a threshold chosen once the answer is known is not a threshold.

**Method (D-07):** Charge the pack fully, connect it, take the USB cable
out, let the device run its normal wake/poll/sleep cycle completely
untouched, check in on it once a day, and note how long it runs. The user
explicitly rejected an inline USB power meter as unnecessary extra
hardware/technical setup — this run adds no instrumentation beyond what
D-07 specifies.

**Pack rated capacity:** 3000 mAh — transcribed from `hardware/BOM.md`
(`## Required Now`, "LiPo battery pack, 3.7V, JST-PH 2.0mm 2-pin,
protected", Kubii "Batterie 3000mAh Li-Po").

**Server sleep value:** the run is served by `skypane-byos.service` on
the VPS (the same `stub-server/byos_server.py` file the local stub is,
run under systemd — see the observation channel subsection below), whose
sleep is `SKYPANE_SLEEP_S` in `/opt/skypane/skypane.env`, 30 in normal
production operation. This matters mechanically, not just as trivia:
`check-battery`'s nominal poll count is the elapsed span divided by
`--interval-s`, so an interval that does not match what the server
actually returned inflates coverage, shrinks every gap measured in
intervals, and lets a damaged run pass all four gates. The interval is
therefore set on the VPS at the start of the run rather than assumed —
300 remains the pre-registered value for it, so a depletion result
arrives in days rather than months, and the value actually in force is
recorded in `## Measured Inputs` as `interval_s` and is what the checker
is always given, never a remembered constant. The production value
(30) must be restored after the run — a 300-second sleep left in place
leaves the deployed frame refreshing far less often than the server
updates it.

**Validity thresholds this run is judged by** (the exact `check-battery`
defaults, pre-registered here so they cannot be tuned after the fact):

| Threshold | Value | Gate it enforces |
|---|---|---|
| `--min-coverage` | 0.95 | observed polls / nominal polls — catches polls that did not arrive, for any reason |
| `--max-gap-intervals` | 3 | no single gap between consecutive polls may exceed 3 intervals |
| `--min-mv-drop` | 100 mV | drop between the opening and closing millivolt windows — the phantom-USB-power gate |
| `--cutoff-mv` | 3400 mV | with `--expect-depleted`, the last reading must be at or below this to count as a genuine depletion |

**Ceiling:** 21 days. After 21 elapsed days the developer may end the run
even if the device is still alive.

**The exact division being performed, per D-07:** rated capacity (mAh)
÷ counted cycles = milliamp-hours per cycle. The cycle count itself is
reconciled three ways in Task 3 (nominal from elapsed span, observed
polls in the server log, and the device's own NVS boot-counter delta).

**Both possible outcomes are results, and neither is a failure.** A run
that empties the pack inside the 21-day ceiling gives a measured
mAh-per-cycle figure directly. A run still alive at the 21-day ceiling
gives an upper bound on per-cycle consumption and, therefore, a lower
bound on battery life — which is the direction that matters for planning
a wake interval: a bound that overstates consumption is a plan that does
not run out of battery earlier than it promised.

**Physical preconditions this amendment does not touch.** This
amendment moves the observation channel only. Three things about the
pack itself remain exactly as required, performed in 05-01's Task 2:
the pack is fully charged before the run starts, its polarity is
re-checked against `hardware/BOM.md` immediately before connection, and
it must have a confirmed integrated protection circuit — this run
deliberately empties a lithium cell, and an unprotected one taken below
its safe floor is a fire risk on the next recharge, not merely a dead
pack.

### Observation channel

The primary observation channel for this run is `history.db`'s
`device_health` table at `/opt/skypane/state/history.db` on the VPS.
`skypane-poll.timer` runs `poll_cycle.run_once()` every 30 seconds, which
reads Caddy's log via `history_db.read_caddy_battery_log()` and applies
readings via `history_db.apply_caddy_battery_log()`. It tails Caddy's
durable rolled JSON access log (`SKYPANE_CADDY_ACCESS_LOG`,
`/opt/skypane/state/caddy-access.log`) and inserts every `X-Battery-Mv`
reading via `record_device_health()`. This has been running in
production since Phase 6's plan 06-11, and this protocol neither starts
it nor configures it — there is no setup step for the observation
channel at all.

The developer's machine plays no part in the run either way. It is not
the device's peer, nothing on it must stay awake, and it may sleep,
change network, or be closed for the entire run.

Three properties make this the right channel:

**Retention.** `device_health` is keep-forever by design (D-13,
`server/history_db.py:18`) and is never pruned.

**Idempotence.** `record_device_health()` inserts with `INSERT OR
IGNORE` against a `UNIQUE(ts, battery_mv)` constraint, so re-reading an
overlapping range cannot double-count.

**Continuity.** Ingestion runs on the server's own 30-second cadence,
independent of whatever sleep interval the device is on.

The daily record is produced by a two-part pipeline. The remote half
opens the database read-only through Python's standard-library
`sqlite3` module (not the `sqlite3` CLI binary, which is not assumed
present on the VPS) as `sqlite3.connect('file:/opt/skypane/state/history.db?mode=ro',
uri=True)`, sets `PRAGMA busy_timeout=5000`, and prints one JSON object
per row from `SELECT ts, battery_mv, fw_version, boot_reason, rssi FROM
device_health WHERE ts >= ? ORDER BY ts` bounded by the recorded
disconnect time. The read-only URI is there because the 30-second
ingest oneshot is writing to this database continuously and an external
reader must be incapable of corrupting the store or locking out the
writer; the `busy_timeout` matches the discipline `history_db.connect()`
already applies to its own connections.

To survive SSH's two levels of shell parsing — a remote command is
joined and re-parsed by the remote shell, so a `python3 -c` one-liner
carrying quotes and semicolons breaks in ways that are tedious to debug
at the start of a three-week run — the query script is fed to `python3
-` on the remote's stdin via a quoted here-document, with the
disconnect timestamp passed as a positional argument (safe, since an
ISO-8601 timestamp contains no whitespace or shell metacharacters):

```
ssh root@<vps-ip> "python3 - '<since-iso-8601>'" <<'PY'
import json, sqlite3, sys
conn = sqlite3.connect('file:/opt/skypane/state/history.db?mode=ro', uri=True)
conn.execute('PRAGMA busy_timeout=5000')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    'SELECT ts, battery_mv, fw_version, boot_reason, rssi '
    'FROM device_health WHERE ts >= ? ORDER BY ts', (sys.argv[1],))
for row in rows:
    print(json.dumps(dict(row)))
PY
```

The local half pipes that output into `python3 hardware/logtools.py
from-history-db`, redirected over `hardware/logs/battery-run-server.log`.

Regenerating the whole window every time is unconditionally safe on
this channel, so there is no rotation-repair path here and none is
needed — neither of the journald channel's two hazards, an
earliest-entries rotation that silently shortens the window, and
duplicated polls from appending overlapping reads, can occur against a
keep-forever table with a uniqueness constraint on the insert.

**Fallback path.** If `history.db` is ever unavailable — the file
missing, the timer stopped, the ingest pipeline broken — the same
record can be produced by piping `journalctl -u skypane-byos.service
--since '<disconnect time>' -o short-iso --no-pager` over SSH into
`python3 hardware/logtools.py from-journal`. Its two caveats travel
with it, since they apply to it and not to the primary path: journald's
retention window is bounded, so the regenerated file can start later
than the run did, and the repair for that is the committed history of
the log plus `check-battery`'s existing acceptance of several
concatenated log paths. Both converters emit the identical bracketed
format, so `check-battery` and every threshold behave the same
whichever produced the file; the fallback is proven on
`hardware/fixtures/battery-journal.log` exactly as the primary is
proven on `hardware/fixtures/battery-history-db.jsonl`.

## Protocol Amendment

**Date:** 2026-08-27.

This amendment was made before the battery pack was ever connected to
the board and before any measurement existed — no threshold could have
been chosen with the answer already in hand.

**What changed:** the observation channel only. It moves from a stub
server run by hand on a laptop, which required that laptop to stay
awake, on one network address, for up to 21 days, to the production
deployment (`skypane-byos.service`) that already runs the identical
server code, always on.

**What did not change:** the four validity thresholds, the 21-day
ceiling, the exact division being performed, and every physical
handling step for the pack — full charge, polarity re-check, protection
circuit confirmation, and the reading of `boot_count=` off the wake
line before the cable comes out. None of that moves.

## Protocol Amendment

**Date:** 2026-09-02.

This is the second amendment to this protocol. The first (dated
2026-08-27) is recorded above; this one supersedes it only where stated
below. Like the first, it was made before the battery pack was ever
connected to the board and before any measurement existed — no
threshold could have been chosen with the answer already in hand.

**What changed:** the primary observation channel only. It moves from
tailing journald for `skypane-byos.service` to reading `history.db`'s
`device_health` table. The reason is three mechanisms, not a
preference: keep-forever retention against journald's bounded window,
`INSERT OR IGNORE` idempotence against the duplicate-poll hazard, and
continuous 30-second ingestion independent of the device's own poll
cadence — on a pipeline that is already running in production with no
setup step.

**What also changed, as a consequence:** the daily check-in is
downgraded from required to optional. Under journald, a missed check-in
genuinely risked losing the earliest part of the record to rotation, so
the check-in was a data-preservation mechanism. Under a keep-forever
table it preserves nothing, because nothing between check-ins is at
risk. A check-in is now purely for progress visibility and for catching
a stalled run early — never for data preservation — and a run with no
check-ins at all still yields a complete, gateable record.

**What did not change:** the four validity thresholds (0.95 coverage, 3
maximum gap intervals, 100 mV minimum drop, 3400 mV depletion cutoff),
the 21-day ceiling, the exact D-07 division, and every physical
handling step for the pack — full charge, polarity re-check, protection
circuit confirmation, and the reading of `boot_count=` off the wake
line before the cable comes out.

**And, separately and emphatically, `SKYPANE_SLEEP_S` did not change
and neither did the reasoning behind it.** It stays at the
pre-registered 300 for the run and is restored to the production value
afterwards, exactly as the first amendment set out. It is called out
here rather than left implicit because it is the device's own measured
wake cadence, which is the subject of this measurement and the divisor
every coverage and gap figure is computed against, and it has nothing
whatever to do with which channel does the observing. An amendment to
the ingestion path that quietly moved the divisor would invalidate the
run while every gate still reported PASS.

The journald path is retained as a documented fallback rather than
removed: `hardware/logtools.py`'s `from-journal` subcommand, its
fixture and its selftest case all remain in place and passing.

## Daily Check-Ins

*Optional, filled in by Task 2, one row per check-in actually
performed. Each row comes from regenerating
`hardware/logs/battery-run-server.log` via the `from-history-db`
command (or, if the fallback was used, the `journalctl -u
skypane-byos.service | from-journal` pipe over SSH), followed by the
`check-battery --status` daily check-in command. Rows are collected for
visibility rather than for preservation: a missing row for a given
check-in does not invalidate the run, because the record is regenerated
from `device_health` and not accumulated from these rows.*

| Date/time (UTC) | Elapsed | Observed polls | Coverage | Latest mV | Last-poll age | `skypane-byos.service` |
|---|---|---|---|---|---|---|
| 2026-09-02T13:15 | 0.01 day | 9 | 2.30 (transition window, not a validity signal — see note) | 3998 | 319s | active, not restarted since the run began |
| 2026-09-14T06:03 | 11.71 days | 3093 | 0.917 | 3338 | 158s | active throughout, per the VPS-side cloud routine's periodic checks |

*Note on the 2026-09-14T06:03 row: the battery has now crossed below the
pre-registered ~3400 mV depletion cutoff (last reading 3338 mV) while
still polling normally — the run has entered its critical tail. The
device has **not** stopped; Task 3 remains gated on at least an hour of
genuine silence (or the 21-day ceiling, 2026-09-23). Coverage has held
steady at ~0.91-0.92 — persistently below the 0.95 validity threshold
since early in the run, but not worsening, so this reads as a standing
characteristic of the run rather than a developing fault; worth
investigating explicitly in Task 3's write-up before the final verdict
relies on it. A passive cloud routine (6-hourly, tightening to hourly
now that the run is in its tail) independently confirmed the same
crossing via the companion web interface's Health page shortly before
this row was captured.*

*Note on the 2026-09-02T13:15 row's coverage figure: the sample window is
only ~20 minutes and straddles the moment `SKYPANE_SLEEP_S` actually took
effect on the device (a couple of polls at the old ~30-40s cadence before
it settled to the new 300s one), so `nominal` is computed against an
interval the device wasn't fully honouring yet. This is expected and not
a fault; it will wash out as the run continues. Not gated against
`--min-coverage` here - this is a visibility check-in, not the final
Task 2 analysis.*

## Measured Inputs

- `capacity_mah`: 3000
- `interval_s`: 300
- `boot_count_start`: **not confirmed** — the developer did not read the
  `boot_count=` value off the wake line before disconnecting the cable
  this run. Recorded honestly rather than guessed; see `## Cycle Count
  Reconciliation` in the eventual Task 3 write-up, which will need to
  proceed on two independent cycle-count witnesses (nominal from elapsed
  span, and observed polls in `device_health`) instead of three.
- `boot_count_end`: **9337** — read 2026-09-24 off the console
  (`I (756) skypane: wake reason=power-on boot_count=9337`), captured via
  a race-attach script (the port only exists while the device is awake,
  so a plain `firmware/monitor.sh` started after plugging in reliably
  missed the first lines — the same "appears then disappears" timing
  issue `hardware/BRINGUP-LOG.md`'s `## First-Boot Capture` section
  already documents). `wake reason=power-on` confirms a genuine cold
  boot, not a wake from RTC. **Not usable for a delta**, though: this
  counter is cumulative since the device's very first flash, not reset
  per run, and `boot_count_start` (the value immediately before the
  cable was pulled on 2026-09-02) was never captured — see `## Cycle
  Count Reconciliation` below, which proceeds on the two witnesses
  available (nominal from elapsed span, observed polls in
  `device_health`) rather than the three D-07 originally specified. This
  reading does confirm one thing worth recording: the NVS boot counter
  survived a full depletion to 2946 mV intact, with no corruption or
  reset to zero.
- wall-clock disconnect time: 2026-09-02T12:55:00+00:00 (14:55 CEST,
  developer-reported) — corroborated by the server-side record: the last
  charging-plateau reading was 4122 mV at 12:58:13, and the first clearly
  falling reading was 4038 mV at 12:58:50, consistent with the cable
  coming out a few minutes earlier and the drop becoming visible once
  the device was genuinely running off the pack under real load
- timestamp of the last poll: **2026-09-14T21:05:53+00:00** (battery_mv
  2946) — the device did not wake again after this; independently
  confirmed both by direct SSH query and by the passive cloud routine's
  own hourly check, which flagged the stale check-in and notified the
  developer at 2026-09-14T23:14:04Z
- elapsed span: **12.340 days** (1,066,206 s), from
  2026-09-02T12:55:47+00:00 to 2026-09-14T21:05:53+00:00

## Verdict

**Verdict:** MEASURED — 2026-09-15. The pack emptied on its own, 8.66
days inside the 21-day ceiling; this is not a censored run.

Command (re-runnable against the committed log):

```
python3 hardware/logtools.py check-battery hardware/logs/battery-run-server.log \
  --interval-s 300 --capacity-mah 3000 --expect-depleted
```

**mAh per cycle: 0.923. mAh per day: 243.10.**

Five of the six gates pass outright: log/timestamp sanity, minimum
span, maximum gap (no gap exceeds 3 intervals), minimum millivolt drop,
and the depletion cutoff (last reading 2946 mV, well below 3400 mV).
**The coverage gate fails as pre-registered — 0.915, below the 0.95
floor — and this is reported honestly rather than adjusted after the
fact.** The pre-registered thresholds are not renegotiable once the
answer is known (Task 1's whole reason for existing), so this is not
waved through; it is diagnosed instead, immediately below and in
`## Cycle Count Reconciliation`.

**Diagnosis of the coverage shortfall, not a defect in the record.**
The mean interval between consecutive polls across the whole run is
**328.0 s**, not the nominal 300 s `interval_s` — `check-battery`'s
coverage formula (`nominal = elapsed / interval_s`) assumes zero awake
time per cycle, but a real cycle also spends real wall-clock time
associated to Wi-Fi and the HTTP round trip before the *next* sleep
timer starts. The gap distribution is clean, not erratic: 39.8% of the
3,251 inter-poll gaps land at or under 310 s (one interval), 60.1% land
in the 311-610 s band (essentially one interval plus real wake
overhead), only 4 gaps (0.1%) reach a second missed interval, and the
maximum gap across the entire 12.34-day run is 665 s — comfortably
inside the 900 s (3-interval) ceiling. Nothing here looks like dropped
telemetry; it looks like ~28 s of real, consistent per-cycle overhead
that the checker's nominal formula does not model. `--interval-s 300`
is left exactly as pre-registered (D-07's value, not a fitted one) —
the fix, if any, belongs in a future revision of `check-battery`'s
nominal formula, not in this run's inputs.

## Cycle Count Reconciliation

| Witness | Count | Source |
|---|---|---|
| Nominal (elapsed / interval_s) | 3554.02 | `1,066,206 s / 300 s` |
| Observed (server log) | **3252** | `device_health` rows via `from-history-db`; this is what `mAh/cycle` divides by, per D-07 |
| Device NVS boot-counter delta | **not computable** | `boot_count_end=9337` was read 2026-09-24, but `boot_count_start` was never read (Task 2 gap, disclosed above) — the counter is cumulative across the device's whole lifetime, not scoped to this run, so a single endpoint cannot be diffed into a cycle count |

Coverage (observed/nominal) is **0.915** — diagnosed above as real
per-cycle wake overhead inflating the true average interval to ~328 s,
not as lost polls. The headline division uses the **observed** count
(3252), matching D-07's instruction to divide by the actually-counted
cycles rather than a theoretical one. Ordinarily this run would also
reconcile against the device's own boot-counter delta as a third,
independent witness; that check cannot be performed this run because
the opening endpoint was never captured (Task 2's disclosed gap) —
recorded as a real limitation of this specific run, not smoothed over.
The closing endpoint alone (9337) is still worth having: it confirms
the NVS boot counter survived a full depletion to 2946 mV without
corruption or reset, which is itself a small piece of evidence that
the device's flash-backed state is robust across a hard power loss.

## Discharge Trend

Opening window mean: **4009.6 mV**. Closing window mean: **3275.2 mV**.
Drop: **734.4 mV**. Last observed reading: **2946 mV**.

| Timestamp (UTC) | Battery (mV) |
|---|---|
| 2026-09-02 12:55 | 4112 |
| 2026-09-03 09:28 | 4000 |
| 2026-09-04 06:26 | 4000 |
| 2026-09-05 03:36 | 3982 |
| 2026-09-06 00:48 | 3922 |
| 2026-09-06 21:46 | 3892 |
| 2026-09-07 18:56 | 3836 |
| 2026-09-08 16:12 | 3814 |
| 2026-09-09 13:26 | 3784 |
| 2026-09-10 10:32 | 3734 |
| 2026-09-11 07:39 | 3652 |
| 2026-09-12 04:44 | 3556 |
| 2026-09-13 02:04 | 3500 |
| 2026-09-13 23:29 | 3364 |
| 2026-09-14 20:48 | 2960 |
| 2026-09-14 21:05 | 2946 (last) |

The curve bends visibly, in the direction a single-cell LiPo's own
chemistry predicts: nearly flat for the first ~2 days (4112→4000 mV,
then holding near 4000 mV for a full day), a long, gently declining
middle (4000→3500 mV over roughly 10 days, ~50 mV/day), then a real
cliff in the last ~36 hours (3500→2946 mV) — the terminal drop from
2960 to 2946 mV happened inside the final 17 minutes before the device
went silent. The 3000 mAh figure being divided is the pack's *rated*
capacity; a pack that under-delivers against its nameplate, or a
protection circuit that cut off before the cell was truly flat (which
the 2946 mV last reading — above most protection ICs' ~2.5-2.8 V hard
floor — suggests may be the case here), both mean the true energy
consumed per cycle is lower than 0.923 mAh, not higher. The figure
errs toward pessimism, the safe direction for a battery-life plan.

## What This Figure Does Not Cover

**No download, no panel refresh.** The served image never changed
across the whole run, so every one of the 3,252 measured cycles took
the hash-skip path — a wake, a poll, a hash comparison, and back to
sleep, with no 960,000-byte image download and no e-paper blit. A real
deployment that actually refreshes content will cost more energy per
cycle than this figure states; `0.923 mAh/cycle` is a floor, not a
typical value, until a future run or field data adds a real-refresh
component.

**A single-cadence run cannot separate per-wake energy from standing
leakage.** One equation, two unknowns: the 0.923 mAh/cycle figure is
consistent with a wide range of splits between "cost of waking up" and
"cost of fifteen-plus-2/3 minutes of deep sleep between wakes." The
projection band below is deliberately printed as a range rather than a
point estimate for exactly this reason, and it is wide — at 3600 s the
range spans 12.34 to 148.08 days depending entirely on that unresolved
split. This is the single biggest open question a future measurement
should resolve before either buying a bigger pack or committing to a
specific field wake interval (see the follow-up findings below).

**No inline current instrumentation.** This run was performed with
D-07's deliberately simple method — a full charge, a disconnected
cable, and arithmetic — by explicit user decision. Nothing here
resolves the instantaneous deep-sleep current in isolation, which
`01-RESEARCH.md`'s own Common Pitfalls #2 already flagged as
unpredictable from datasheets alone.

Reproduced projection band, for the record (see `## Checker Output`
for the exact command):

```
    300s interval: 12.34-12.34 days
    900s interval: 12.34-37.02 days
   3600s interval: 12.34-148.08 days
```

## Checker Output

```
PASS logs carry timestamps and at least two battery-bearing polls
PASS run spans at least 1 day(s)
FAIL coverage is at least 0.95 - coverage is 0.915 (observed=3252, nominal=3554.0), below 0.95 - the frame losing home Wi-Fi or internet, the server unit restarting, or journald having rotated the earliest entries out of the window being converted are the likely causes
PASS no gap between consecutive polls exceeds 3 interval(s)
PASS millivolt drop between opening and closing windows is at least 100 mV
PASS last observed millivolt reading is at or below the 3400 mV cutoff
battery: 5/6 checks pass
span: 12.340 day(s) (1066206s), from 2026-09-02T12:55:47+00:00 to 2026-09-14T21:05:53+00:00
cycle counts: observed=3252 nominal=3554.02
coverage: 0.915
mAh/day: 243.10
mAh/cycle: 0.923 (dividing by observed poll count = 3252.00 cycles)
battery mV: opening window mean=4009.6 closing window mean=3275.2 drop=734.4 last=2946
projection band (days) for candidate wake intervals - lower bound assumes all drain is standing leakage (life unchanged), upper bound assumes all drain is per-wake (life scales linearly with the interval); a single-cadence run cannot separate the two:
    300s interval: 12.34-12.34 days
    900s interval: 12.34-37.02 days
   3600s interval: 12.34-148.08 days
```

(Exit code 1, from the coverage gate alone — diagnosed under
`## Verdict` above, not a run-invalidating fault.)

## Run Conditions

- **Public host:** the frame was pointed at the OVH VPS's public host
  throughout (`SKYPANE_PUBLIC_HOST` in `deploy/skypane.env.example`'s
  shape; the real value is deliberately never written into this repo).
- **`SKYPANE_SLEEP_S`:** set to 300 at run start (2026-09-02, confirmed
  live on the running process's own command line, not just the config
  file), left in force for the full 12.34-day run, and **restored to
  30 on 2026-09-15** immediately once the run's conclusion was
  confirmed — `skypane-byos.service` restarted cleanly both times, and
  the restored value was likewise confirmed on the running process.
- **`skypane-byos.service` / `skypane-poll.timer`:** both remained
  active for the whole run; the only two restarts of the byos service
  were the two deliberate `SKYPANE_SLEEP_S` changes above (start and
  restore), not faults.
- **`history.db` reachability:** reachable for every check performed
  across the run (dozens of direct SSH queries plus 40+ passive cloud
  routine checks); the `from-journal` fallback was never needed.
- **Coverage anomaly:** the persistent ~0.915-0.922 coverage figure
  present from early in the run through its conclusion — diagnosed
  under `## Verdict` as real per-cycle wake overhead (~328 s true mean
  interval vs. 300 s nominal), not an interruption. No home-network,
  VPS, or internet outage was otherwise observed or reported during
  the run.
- **Charge time:** the pack was connected around 09:47 UTC on
  2026-09-02 (inferred from a `power-on` boot event in `device_health`
  at that time) and reached a stable ~4120 mV charge plateau by
  ~12:34-12:39 UTC the same day — roughly 2h50 to visible plateau, USB
  left connected throughout per the protocol.
- **Pack post-depletion condition:** inspected 2026-09-24 before any
  recharge attempt, per the protocol's own safety requirement — the
  developer confirmed the pack looked and felt normal (no swelling, no
  heat, no smell). Recharge was then started; the exact recharge
  duration was not tracked to the minute (this project's own convention
  only requires the *inspection* to gate the recharge, not a timed
  measurement of it).
- **Post-mortem wake reason:** confirmed `power-on` (the console line
  quoted under `## Measured Inputs`' `boot_count_end` entry), exactly as
  expected for a board with no power at all until reconnection.
- **Clean-recovery-without-reflash confirmation:** confirmed — the
  device reconnected to Wi-Fi and resumed normal polling (subsequent
  wake cycles observed serving `poll ok sleep_s=3600 hash_skip=1`, its
  now-configured production wake interval per Phase 25's web-configurable
  setting) with no reflash of any kind.
- **Anomalies from the check-in table:** none beyond the coverage
  figure already diagnosed above; no restart, outage, or interruption
  was otherwise flagged by either the developer's own checks or the
  passive cloud routine's 40+ automated ones.

## Calibration & Follow-Up Findings

*Not part of the pre-registered D-07 protocol — captured here because
this run is the first real Spectra-6-hardware discharge curve this
project has ever produced, and it bears directly on three things this
project has been carrying as open questions. Each is planted as a seed
(`.planning/seeds/`) rather than acted on inline, so it gets a proper
scoped pass rather than a same-session patch.*

**1. `companion/battery.py` / `server/poll_loop.py`'s battery-percentage
estimate is measurably miscalibrated.** Both modules assume
`BATTERY_FULL_MV = 4200` / `BATTERY_EMPTY_MV = 3300`, linear in
between. This run's own data: the pack's real charge plateau was
**~4122 mV**, never 4200 — so a freshly-charged pack would never read
100% under the current constants (it would read ≈91%). The device kept
polling successfully all the way to **2946 mV**, well past the
assumed "0%" point at 3300 mV — for roughly the final 24 hours of the
run, the estimate would have already been pinned at 0% while the
device was still very much alive. See `SEED-006` for recalibrating both
constants against this run's real curve.

**Outcome (2026-09-23, quick 260923-gaf):** The estimate is now a
piecewise millivolt-to-percent table (14 knots) built from this
section's own Discharge Trend rows. Percent is the share of this run's
runtime still ahead, with the 4000 mV plateau merged at its midpoint
and the 2960/2946 tail merged into a single 0% knot at 2946.
Readings at or above 4112 mV, including the 4122 mV on-charger plateau,
now read 100%, and 2946 mV reads 0%. The rejected alternative was
recalibrating only the two linear endpoints to 4112/2946. It was
rejected because a straight line cannot follow this curve's flat top
and end-of-run cliff: 3500 mV would read about 48% when this run shows
about 15% remained. The companion's chart line is now derived at
3540 mV (20%) and sits above the device's unchanged 3500 mV warning
point (about 15%).

**2. The low-battery warning threshold (`BATTERY_LOW_THRESHOLD_MV = 3500`,
`server/poll_loop.py`) is validated, not miscalibrated.** It would have
first fired on 2026-09-12 at 11:54:42 UTC — **57.2 hours (2.4 days)**
before the device actually went silent. That is a comfortable, honest
lead time; this run gives no reason to change it.

**3. The bigger open question — a bigger battery, or a longer wake
interval? — is not yet answerable, and shouldn't be guessed at.** This
run measured 12.34 days at the 300 s test cadence. The current
production default, `SKYPANE_SLEEP_S = 30` (a development/testing
value, never intended as a real battery-only field cadence), would
extrapolate to roughly a single day of battery life if ever run as-is
on the pack alone — nowhere near viable, and now that Phase 11 made
the wake interval web-configurable, choosing a realistic field value is
a free lever available right now. But the wide projection band
(12.34-148.08 days at 3600 s, depending entirely on the unresolved
per-wake-vs-standing-leakage split noted under `## What This Figure
Does Not Cover`) means a bigger pack is not yet a well-founded
recommendation either way — it could matter enormously or barely at
all. `PROJECT.md` itself defers the solar-charging question "until
real battery life and frame placement are known" — this run is exactly
the trigger that clause was written for, but the honest answer right
now is "known, but not yet precise enough to decide." A second,
shorter discharge run at a different candidate interval (e.g. 3600 s)
would resolve the split and turn both the battery-capacity and the
solar questions into informed decisions instead of guesses.

## Follow-up: BATTERY EMPTY park (quick task 260923-fr4)

This run ended with the panel frozen mid-transition: the device went
silent at **2946 mV**, 17 minutes after the 2960 mV reading immediately
before it, with no indication on the glass that anything was wrong — just
whatever the last successful refresh happened to leave behind.

The server now parks the frame on a deliberate BATTERY EMPTY screen
instead. Thresholds are sourced directly from this run's own table:
`BATTERY_CRITICAL_MV = 3300` (`server/poll_loop.py`) sits with real margin
below the 3500 mV low-battery badge (which this run showed firing 57.2
hours before silence — comfortable, honest lead time) and above the 2960
mV point recorded 17 minutes before the device actually died, leaving
runway to park the frame on a legible screen well before a real pack
would repeat this run's silent freeze. `BATTERY_CRITICAL_RECOVER_MV =
3700` re-arms with a 400 mV buffer once charging resumes.

This is **unverified on glass** until the next real depletion run: no
device has yet reached 3300 mV against this code, so the park's timing,
the screen's legibility at the panel's actual e-ink refresh rate, and the
one-hour parked check-in cadence are all confirmed only by the harnesses
listed in `260923-fr4-SUMMARY.md`, not by a physical device.

## Run 2 Protocol (pre-registered)

Status: CONFIRMED by the owner 2026-10-05, including section 4a (the
reference interval for the continuity gates, confirmed the same day as option
3) and the comparability limitations recorded under "Known limitations
carried to Phase 46".

This section is written before the pack is connected and before any run-two
measurement exists. Nothing below is a result; every number is labelled a
prediction or an input. The cadence (60 s), ceiling (21 days), park-window
rule (D-10), baseline rule (D-07) and restore rule (D-09) were confirmed by
the owner on 2026-10-05. Run one's sections above are unchanged.

**Confirmed values:** cadence 60 s; ceiling 21 days; thresholds 0.95 / 3 /
100 mV / 3400 mV unchanged; same pack and firmware family, firmware frozen
for the whole run; display enabled and no quiet hours; the frame is never
connected to a computer during the study, so `boot_count_start` and
`boot_count_end` are optional (section 9); production wake interval restored
afterwards and
recorded; park-window rule as in section 5; continuity gates judged against
the frozen reference interval of section 4a, not against the bare 60 s.

### 1. Purpose and comparability

Same Kubii 3000 mAh 1S pack, same firmware family and server poll workload
as run one (D-01). Only the effective wake cadence differs. That is what lets
Phase 46 fit per-wake energy against standing deep-sleep consumption from two
runs. The owner chose 60 s because the real field interval is close to 60 s
or even 30 s: the second run should sit in the wake-dominated regime near real
use, not far from it. 30 s is out of scope (the Device setting's minimum is
60 s; lowering it is a production cadence change).

Two comparability caveats, stated now so they are not discovered in Phase 46.
Both come from `hardware/PHASE34-HARDWARE-SESSION.md`, not from run two:

- Run one predates the Phase 34 firmware work (2026-09-25). The no-change
  wake dropped from about 6.3 s to about 1.65 s against the VPS, so the
  per-wake energy of run two's firmware is not guaranteed to equal run one's.
  The fit separates the two runs' energies only if per-wake energy is the
  same in both; the report records the firmware version so Phase 46 can see
  the difference.
- The wake workload is not purely hash-skip. Run one's section above says the
  image never changed, but the Phase 34 session attributes run one's 28 s
  overhead to about 60 % refresh wakes (panel draw about 31.5 s, 37 to 52 s
  awake) and 40 % no-change wakes. The two statements disagree and this
  protocol does not resolve them. The refresh share of run two shifts both the
  real gap and the energy per wake, and `device_health` rows do not record
  it. The gap distribution in the raw export (no-change gaps cluster near
  60 s plus about 2 s, refresh gaps near 60 s plus about 40 s) is the only
  evidence of it; the Results section reports that distribution.

### 2. Cadence (D-04, D-05)

Configured wake interval: **60 s** (the Device setting's minimum, 5x faster
than run one), set through the companion Device wake-interval setting with no
SSH edit. The value actually in force is recorded as `interval_s`, never a
remembered constant.

**Confirming that the device took 60 s, with no cable and no console.** The
device only learns the new value at its next wake, which still happens after
the old interval. The owner therefore saves 60 s on the Device page while the
frame is still on USB power, waits one old interval plus a minute, and then
checks the server history rather than the device: with the run-one read-only
remote query (the same channel as section 12) the poll timestamps after that
point must show a poll-to-poll gap of at least 60 s and not much more than
100 s. The expected range is about 62 s for a wake with no panel refresh and
up to about 100 s for one with a refresh (section 2 below; mean about 88 s).
The discriminator is the shortest gap: with 60 s in force no gap can fall
below 60 s (the sleep alone is 60 s), while the old setting gives gaps near
its own interval plus the same overhead (for a 30 s production interval,
about 32 s for a no-change wake). If a gap is still below 60 s after two old
intervals, or several gaps are near the old interval, the device did not take
the value: check the Device page and wait one more wake; do not unplug until
it shows. What the companion itself shows is weaker evidence and is only a
hint: the Home headline reads "Next update in ..." as a countdown computed
from the saved interval, and the Health battery chart plots each reading with
its time; neither displays the poll-to-poll gap, and the chart's time
resolution at about 88 s was not verified. The server history is the check
of record. The rows from this check lie before `disconnect_time_utc` and are
left out of the run export, which starts at the disconnect.

**The effective cadence is not 60 s.** The firmware starts its sleep timer
after the work, so the poll-to-poll gap is `sleep_s` plus the awake time. Run
one measured a 328.0 s mean gap on a 300 s setting (about 28 s of overhead).
At 60 s the same overhead gives about 88 s; the Phase 34 timings give 62 s if
every wake is a no-change wake and about 100 s if every wake refreshes the
panel. The effective cadence is therefore recorded as the mean poll-to-poll
gap measured from the raw export, and every per-day and per-cycle figure uses
it, never 60 s.

### 3. Ceiling (D-06)

**21 days**, as in run one. A run still alive at the ceiling is a valid bound
result. Under every hypothesis in section 8 the pack is expected to deplete
well inside this ceiling (at most about 12.4 days), so the ceiling is a
safety bound, not an expected end. The ceiling check allows one interval
(60 s) of overshoot, so the owner records `end_time_utc` and bounds the
export with it if the run is ended at the ceiling.

### 4. Thresholds (D-03)

Run one's values, unchanged:

| Flag | Value |
|------|-------|
| `--min-coverage` | 0.95 |
| `--max-gap-intervals` | 3 |
| `--min-mv-drop` | 100 |
| `--cutoff-mv` | 3400 |

A gate that fails is reported as failed and diagnosed, never retuned, as run
one did with coverage. The values are not open. The interval the continuity
gates are measured against is the frozen reference interval of section 4a.

### 4a. Reference interval for the continuity gates - CONFIRMED (2026-10-05)

**The rule (owner-confirmed 2026-10-05, option 3 below).** The continuity
gates (coverage and largest gap) are judged against a *reference interval*,
not against the bare configured 60 s:

> reference interval = the mean poll-to-poll gap over the first 48 hours of
> the run (counted from the first exported row), excluding gaps above 3 times
> the configured interval, rounded half-up to whole seconds.

In effect it is the configured interval plus the wake overhead measured early
in the run. It is written as `reference_interval_s` in
`hardware/logs/battery-run2-params.json` and in the `## Run 2 Start Record`,
in a commit made **before any continuity verdict is computed**. Nothing but
the denominator and the gap unit moves: the thresholds stay exactly 0.95
coverage, 3 intervals for the largest gap, 100 mV and 3400 mV (D-03). The
coverage against the configured 60 s is still reported, as an informational
figure that drives no verdict.

**Frozen before the verdict.** The value is committed, with its source, before
`run-report` is run for the first time on the run's data. The tool cannot see
commit order, so the version-control history is the evidence: the commit that
adds `reference_interval_s` must precede the commit that adds
`hardware/logs/battery-run2-report.json`. The value is never edited after the
verdict exists. If a mistake is found, the run is reported with the value that
was frozen and the mistake is stated.

**How it is computed.** Do not hand-calculate it. With the export of the
first days of the run saved as a file:

    python3 hardware/logtools.py reference-interval <export.jsonl> --interval-s 60

It prints `reference_interval_s: <value>`, the window it read, the number of
gaps used and excluded (above 3 x 60 = 180 s), the unrounded mean and the
sha256 of the export file. It reads only the first 48 hours after the first
row, so later rows cannot change the value. It refuses (exit 2) an export that
covers less than 48 hours, an unordered or empty export, or one that leaves
fewer than 100 usable gaps. Rounding is half-up (88.5 s becomes 89 s).

**Where it is recorded.** In the params file:

| Key | Content |
|---|---|
| `reference_interval_s` | the whole-second value the helper printed (between `interval_s` and 3 x `interval_s`) |
| `reference_interval_source` | required with the value: a short owner-written note, for example the date, who ran the helper and on which export |
| `reference_interval_export_sha256` | optional: the `export_sha256` line the helper printed for the export it read |

and in `## Run 2 Start Record`, as a dated line with the helper's full output.
`run-report` refuses a value outside the bounds, a value without a source and
a source without a value (exit 2). A run judged against `interval_s` alone
leaves all three keys out or null, and `run-report` then behaves exactly as it
did before this rule existed.

**What `run-report` does with it.** Coverage, the largest-gap gate and the
nominal cycle count of the normal-cadence window use the reference interval;
the check names say so ("... (against the 88 s reference interval)"). The
report's `reference_interval` block holds the value, the source, the export
hash, the interval each figure was judged against, the coverage and largest
gap against the configured interval (`informational_vs_configured`, no
verdict), and the normal-window mean gap relative to the frozen value. A
continuity check recomputes the value from the first 48 hours of the export
being reported and FAILs when it differs from the frozen one, so a value
cannot be derived from the whole run or from later data and still pass. The
ceiling check keeps the configured interval.

**Why option 3.** `run-report` computed coverage as `observed polls / (span /
interval_s)`, which is `60 / mean gap`. Run one failed coverage (0.915) for
exactly this reason: 300 / 328. At 60 s the same overhead is a much larger
share of the interval. Measured with the tool on synthetic exports (5 days
each, `interval_s=60`, in a temporary directory):

| Synthetic gap pattern | Mean gap | Coverage vs 60 s | Coverage vs mean gap |
|---|---|---|---|
| constant 62 s (all no-change wakes) | 62.0 s | 0.968 PASS | 1.0 |
| 20 % refresh wakes (62 s / 101 s) | 70.0 s | 0.857 FAIL | 1.0 |
| constant 88 s (run one's overhead) | 88.0 s | 0.682 FAIL | 1.0 |
| 60 % refresh wakes (run one's mix) | 85.6 s | 0.701 FAIL | 1.0 |

Coverage against 60 s passes only if the mean gap is at most 63.2 s, i.e. at
most 3.2 s of overhead. Run one's overhead was 28 s, so the gate would fail
structurally, whatever the pack does, and the failure would carry no
information. The gap gate has the same scaling problem: 3 intervals is 180 s
at 60 s, against 900 s in run one; a 200 s slow wake already fails it.

Options considered:

1. Judge against the configured 60 s unchanged. Fully fixed in advance, but
   the coverage verdict then measures wake overhead, not continuity. Expected
   result: FAIL, uninformative. Rejected.
2. Reference = the mean (or median) gap of the same window. Coverage is about
   1.0 by construction, so the gate checks nothing; the median of a bimodal
   no-change/refresh distribution is also unstable. Rejected.
3. **Reference = configured interval plus overhead measured on an early,
   separate window, frozen before the verdict. CONFIRMED.** A pack-independent
   quantity (cadence) is frozen from data that cannot reveal the outcome
   (depletion time, voltages).

**What it does and does not guard against.** A real outage still fails: a
700 s hiccup is about 8 reference intervals at 88 s, and a run whose observed
polls fall to 80 % of the reference count fails coverage (both are tested on
synthetic data). The rule can mask one thing: a *systematic* slowdown that is
already present in the first 48 hours (for example a poor Wi-Fi link making
every wake longer) becomes part of the reference. The informational coverage
against 60 s, the effective mean gap and the gap distribution stay in the
report for that reason.

**Risk: an unrepresentative first 48 hours.** The refresh share varies with
the departure banks, and 48 hours spans two daily cycles but not a weekly
one. If the normal-window mean gap later differs from the frozen value, the
report states the difference (`normal_window_mean_gap_vs_reference`, printed as
a percentage). A mean gap above the frozen value lowers coverage against it
(coverage is about the frozen value divided by the real mean gap, so a real
mean more than about 5 % above the reference fails the 0.95 gate); a mean gap
below the frozen value raises coverage above 1.0 and cannot fail it. A
failure caused by drift is reported as a FAIL with that diagnosis; the value
is not re-frozen.

### Known limitations carried to Phase 46

Accepted by the owner on 2026-10-05, as known limitations rather than
problems to be removed; Phase 46 must carry both into the two-run model, not
hide them:

1. **Firmware differs between the runs.** Run two uses post-Phase-34
   firmware; run one predates it (section 1, first caveat). Per-wake energy
   is not guaranteed to be equal in the two runs, and the fit separates
   per-wake energy from standing consumption only if it is.
2. **The refresh share of run two is unknown and may differ from run one.**
   The share of panel-refresh wakes is not recorded in `device_health` and
   may differ from run one (section 1, second caveat). No static-image
   workaround is used to control it: the study keeps the normal poll
   workload. The gap distribution in the raw export is the only evidence.
3. **Run two probably has no third cycle-count witness.** The frame stays off
   the computer, so the NVS boot-counter delta is likely `not computable`
   (section 9), as in run one. The cycle count rests on two witnesses, nominal
   from the elapsed span over the reference interval and observed polls, and
   a model fit must not assume a third one exists. The firmware is not
   changed to report it (section 9).

### 5. Park window rule (D-10, confirmed)

The BATTERY EMPTY park at 3300 mV (`park_mv`) changes the real cadence to
hourly. Continuity and coverage are judged on the normal-cadence window,
which ends at the first reading at or below 3300 mV. The full window,
including parked polls, is also reported as informational figures. The
boot-counter witness covers the full run and is compared with the
full-window observed count; nominal is compared with observed on the
normal-cadence window only. Run one had no park, so Phase 46 must compare
like windows.

### 6. Pre-run conditions that would silently override the cadence

- The display is enabled and no quiet-hours or display-off state is active
  during the run: display-off cadence (300 s) outranks the configured
  interval, and the BATTERY EMPTY park (3600 s) outranks both (precedence in
  `server/wake.py`).
- The production wake interval in force before the study is written down as
  `production_interval_before_s`. If the Device setting shows "Uses server
  default", the deployed `SKYPANE_SLEEP_S` (30 in `deploy/skypane.env.example`)
  is in force and is what is recorded; restoring then means clearing the
  field, not typing a number.
- Nothing else on the Device page or the server is changed during the run.

### 7. Baseline (D-07)

Firmware version and server revision are recorded at start. The firmware is
frozen for the run; if firmware changes mid-run the run is invalid and
restarts. The report tool checks that the distinct `fw_version` values in the
export equal the recorded baseline.

### 8. Hypotheses with numeric predictions (predictions, not results)

Inputs from run one: 3252 observed polls, mean gap 328.0 s (about 28 s over
the 300 s setting), 0.923 mAh/cycle, 243.10 mAh/day, 12.34 days, 3000 mAh
rated. Model (a simplification, not fitted here): each cycle costs
`E_wake + P_sleep x gap`; run one's 0.923 mAh splits as `f x 0.923` for the
wake and `(1 - f) x 0.923` for standing consumption over its 328 s gap.

For run two with an effective mean gap `T`:

- charge per cycle = `0.923 x (f + (1 - f) x T / 328)` mAh
- cycles = `3000 / charge per cycle`; span = cycles x `T` / 86400 days

Predictions at the three plausible effective gaps (62 s all no-change, 88 s
run one's overhead, 100 s all refresh):

| Hypothesis | T = 62 s | T = 88 s | T = 100 s |
|---|---|---|---|
| Wake-dominated (`f = 1`): about 3250 cycles whatever the gap | 2.3 days | 3.3 days | 3.8 days |
| Mixed `f = 0.5` | 5470 cycles, 3.9 days | 5130 cycles, 5.2 days | 4980 cycles, 5.8 days |
| Leakage-dominated (`f = 0`): about 243 mAh/day whatever the gap | 12.3 days (about 17200 cycles) | 12.3 days (about 12100 cycles) | 12.3 days (about 10700 cycles) |

Read the 88 s column as the headline: wake-dominated, about 3250 cycles and
about 3.3 days; leakage-dominated, about 12 days. Anything between is a mixed
split, which the formula above gives for any `f`. Every prediction lands
inside the 21-day ceiling. Cycles per day are about 980 at 88 s (about 1390
at 62 s), against about 263 in run one, which scales the boot-counter and row
counts in section 9. The model also assumes per-wake energy equal to run
one's (caveats in section 1); if the firmware or refresh share differs, a
wake-dominated outcome is expected to differ from 3250 cycles and that
difference is itself information for Phase 46, not a protocol failure. The
model is not fitted here; that is Phase 46 (BAT-03).

### 9. Cycle-count reconciliation (D-08)

Three witnesses: nominal from the elapsed span over the reference interval
(`reference_interval_s`, frozen as in section 4a; the configured `interval_s`
is reported beside it), observed
polls in the exported `device_health` rows, and the NVS `boot_count=` delta.

**The third witness is optional.** The owner does not plug the frame into a
computer during the study, and `boot_count=` is only visible on the serial
console. `boot_count_start` and `boot_count_end` are therefore optional
params: when either is missing the tool reports the boot witness as
`not computable: <which> not recorded`, adds no boot check to the continuity
verdict and never estimates the count (the same outcome as run one, which did
not capture `boot_count_start`). The other two witnesses stand: nominal from
the elapsed span over the reference interval, and observed polls in the
server log. A boot count may still be recorded if the owner happens to read
it, never otherwise.

Why the firmware is not changed to report `boot_count` in the poll headers:
that would change the frozen firmware baseline (D-07: a different
`fw_version`, so the run would no longer be on the firmware this protocol
freezes), require flashing
the board over USB from a computer, and need a server change as well, since
`X-Boot-Count` is not among the telemetry headers the history store keeps.
Reconciliation with two witnesses is the accepted cost.

Scale: about 980 to 1390 cycles per day, so a 3 to 12 day run is about 3000
to 17000 rows, against 3252 in run one.

### 10. Physical preconditions (unchanged from run one)

Pack fully charged; polarity re-checked against `hardware/BOM.md` immediately
before connection; protection circuit confirmed; pack inspected before any
recharge after depletion.

**Where USB power is still needed.** Only for charging: (1) charging the pack
fully before the run, with the frame left on USB power until the battery
reading on the server side shows the charge plateau; (2) recharging after the
run, after the required inspection. Neither step needs a computer, and the
frame is never plugged into one during the study. Documented: run one's pack
was charged on the board through the USB-C cable and reached a stable
charge plateau of about 4120 mV (4122 mV on the charger) about 2 h 50 min
after connection, with USB left connected (run one's Run Conditions); that
plateau, seen in the server's battery readings, is the owner's "fully
charged" evidence. Assumed, not verified in this repository: that the board's
charging circuit accepts any USB 5 V source (a wall charger or a power bank),
not only a computer's port. `hardware/BOM.md` only records that the cable
carries data and says nothing about the charge source; run one's source is not
documented. The owner confirms the assumption on the first charge: if the
battery reading does not rise to the plateau on the chosen charger, use
another source before connecting the study.

### 11. Restore production (D-09)

After the run the production wake interval is restored to
`production_interval_before_s` through the Device setting (or by clearing the
field if it was "Uses server default"), and the restored value is recorded as
`production_interval_restored_s`.

### 12. Observation channel (D-03)

history.db `device_health`, read with the run-one read-only remote query
bounded by the disconnect time (and by `end_time_utc` for a ceiling end),
then, once, about 48 hours in, `hardware/logtools.py reference-interval` on
the export so far (section 4a), then `hardware/logtools.py run-report`,
which produces the raw-export hash, separate continuity / voltage-validity / baseline verdicts and the three-way
reconciliation. At 60 s the channel is unchanged: the poll timer ingests the
Caddy log every 30 s regardless of the device cadence, `device_health` is
keep-forever (at most about 30000 rows over 21 days, a few MB), and the
provider calls of the poll loop are on its own 30 s timer, not the device's.

### 13. Results

Results go in a separate `Run 2 Results` section, filled only from the
owner-supplied export. No result is written before then.

## Run 2 Start Record

Recorded 2026-10-05 from values the owner supplied in chat. Each value is
written as given; "owner" means the owner reported it, "looked up on the
owner's delegation" means Claude read it from the named source because the
owner asked for that lookup. Nothing here is a reading, a result or an end
value, and no verdict exists. Raw values live in
`hardware/logs/battery-run2-params.json`.

| Key | Value | Source |
|---|---|---|
| `capacity_mah` | 3000 | `hardware/BOM.md` (rated capacity), as the plan says |
| `interval_s` | 60 | owner: typed 60 in the Device wake-interval setting, saved, and the Device page then showed 60 |
| `production_interval_before_s` | 300 | owner: the production wake interval before the study |
| `production_quiet_hours_before` | enabled, 23:30-06:00 | owner: quiet hours were enabled 23:30-06:00 before the study; to be RESTORED at the end (see below) |
| `disconnect_time_utc` | `2026-10-05T14:08:00Z` | owner said "16h08" (French local time). Conversion by the recorder: Paris time on 2026-10-05, CEST = UTC+2, so 14:08 UTC. Assumes Paris time and today's date; seconds unknown, recorded as :00 |
| `firmware_version` | `fw-v1.0.2` | looked up on the owner's delegation: the owner's screenshot of the companion Update page on 2026-10-05 ("Version en cours: fw-v1.0.2, installée 29 sept. 23:47"); the latest `fw-v*` tag is fw-v1.0.2, so no OTA could have installed another version |
| `server_revision` | `b2b08e9b89183db1fa3c5789f2134b94c311483e` (short `b2b08e9b`) | looked up on the owner's delegation from GitHub Actions: the last commit whose "Deploy to production" job succeeded (run 37310309362, deploy completed 2026-10-05T12:40:51Z) |
| `park_mv` | 3300 | as the plan and Protocol say |
| `ceiling_days` | 21 | the confirmed Protocol |
| `protocol_confirmed_utc` | null | the owner confirmed the protocol on 2026-10-05; the exact time was not captured (time not captured). The params validator requires a timezone-aware timestamp and refuses a date-only string, so the field stays null rather than invent a time |
| `boot_count_start` | null | not captured: no console in this study, as accepted in the Protocol |
| `end_reason`, `boot_count_end`, `production_interval_restored_s`, `production_quiet_hours_restored`, `reference_interval_*` | null | set later: the run has not ended and the 48 h reference-interval freeze has not happened |

**Battery before disconnect.** The owner read 4110 mV at the end of charging
(run one's charge plateau was about 4120 mV). This is the owner-reported
pre-disconnect reading, not a computed value and not part of the export.

**Display and quiet hours.** The display is enabled. Quiet hours were enabled
(23:30-06:00) before the study and the owner disabled them for the study
("désactivé maintenant"), so the Protocol precondition of no quiet hours or
display-off state during the run is met. They must be restored at the end
together with the wake interval: re-enable quiet hours 23:30-06:00 and report
the value shown after save. `production_quiet_hours_before` is not a key
`run-report` reads; `validate_run_params` ignores keys it does not name, so
the params file carries it without changing `run-report` behaviour.

**Deployed server revision.** A deploy attempt for commit `bc1ed565` (the
charging-pill merge) started 2026-10-05T13:54:25Z but its first step "Refuse
to deploy if main has moved on to different shipped code" failed and the
Deploy step was skipped, so nothing was deployed. Main's later commit
`e40bd6fc` (dev-lock bump) has a failed CI run and a skipped deploy. The
deployed server revision at the disconnect time is therefore still
`b2b08e9b`. This was read from GitHub Actions and could not be verified on
the VPS itself (no access).

**Cadence verification (Protocol section 2).** The owner reported, after
checking the server history: "les écarts sont bons, environ 70 s". This is an
owner-reported approximate value, not a computed figure: poll-to-poll gaps of
about 70 s, at or above the 60 s floor and consistent with the expected
62 to 100 s range (the owner's judgement: "les écarts sont bons"). The exact time of the
check and the exact query output were not supplied (not captured).

**Daily check-ins** are optional and visibility-only
(`python3 hardware/logtools.py check-battery <log> --interval-s 60 --capacity-mah 3000 --status`);
the history channel is keep-forever, as in run one.

**TODO for the owner (dated).** About 48 hours after the disconnect, around
2026-10-07T14:08Z: save the export so far to
`hardware/logs/battery-run2-export-48h.jsonl` and run
`python3 hardware/logtools.py reference-interval hardware/logs/battery-run2-export-48h.jsonl --interval-s 60`
(Protocol section 4a). The value is frozen then, in this record and the
params file, before any continuity verdict. Nothing has been computed yet.
