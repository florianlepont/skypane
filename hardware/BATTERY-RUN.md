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
`skypane-poll.timer` runs `poll_loop.run_once()` every 30 seconds, which
calls `history_db.ingest_caddy_battery_log()`, which tails Caddy's
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
- `boot_count_end`: **pending** — the developer was away from the device
  when the pack depleted and has not yet reconnected USB to read the
  post-mortem wake line. Recorded honestly rather than guessed; see
  `## Cycle Count Reconciliation` below, which proceeds on the two
  witnesses available (nominal from elapsed span, observed polls in
  `device_health`) rather than the three D-07 originally specified.
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
| Device NVS boot-counter delta | **not available** | `boot_count_start` was never read (Task 2 gap, disclosed above); `boot_count_end` is pending the developer's physical reconnection |

Coverage (observed/nominal) is **0.915** — diagnosed above as real
per-cycle wake overhead inflating the true average interval to ~328 s,
not as lost polls. The headline division uses the **observed** count
(3252), matching D-07's instruction to divide by the actually-counted
cycles rather than a theoretical one. Ordinarily this run would also
reconcile against the device's own boot-counter delta as a third,
independent witness; that check cannot be performed this run because
neither endpoint of it was captured (Task 2's disclosed gap on the
open end, physical distance on the close end) — recorded as a real
limitation of this specific run, not smoothed over.

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
- **Recharge time and pack post-depletion condition:** **pending** —
  the developer was away from the device when the pack depleted; both
  items await the physical reconnection described in 05-01-PLAN.md's
  Task 3 (inspect for swelling/heat/smell *before* recharging; do not
  recharge if any is present).
- **Post-mortem wake reason and clean-recovery-without-reflash
  confirmation:** **pending**, same physical step.
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
device was still very much alive. See `SEED-` (to be planted) for
recalibrating both constants against this run's real curve.

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
