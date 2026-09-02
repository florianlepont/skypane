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
- `boot_count_end`: *filled in by Task 3, after the run ends*
- wall-clock disconnect time: 2026-09-02T12:55:00+00:00 (14:55 CEST,
  developer-reported) — corroborated by the server-side record: the last
  charging-plateau reading was 4122 mV at 12:58:13, and the first clearly
  falling reading was 4038 mV at 12:58:50, consistent with the cable
  coming out a few minutes earlier and the drop becoming visible once
  the device was genuinely running off the pack under real load
- timestamp of the last poll so far: 2026-09-02T13:15:19+00:00 (run still
  in progress — this is not the final value, see `## Verdict`)
- elapsed span so far: ~20 minutes (run still in progress)

## Verdict

*Filled in by Task 3: `**Verdict:** MEASURED` or `**Verdict:** CENSORED`,
the date, the exact `check-battery` command with its real argument
values, and the headline mAh-per-cycle and mAh-per-day figures.*

## Cycle Count Reconciliation

*Filled in by Task 3: the nominal, observed and device boot-counter-delta
cycle counts, the coverage figure, and which count the headline division
used.*

## Discharge Trend

*Filled in by Task 3: the opening/closing millivolt window means, the
drop, the last observed value, and a short table sampling the millivolts
across the run.*

## What This Figure Does Not Cover

*Filled in by Task 3: the hash-skip-only nature of the measured cycles
(no download, no panel refresh), the single-cadence projection-band
limitation, and the absence of any inline current instrumentation.*

## Checker Output

*Filled in by Task 3: the full, verbatim output of the final
`check-battery` analysis run, including the summary line and the
projection band.*

## Run Conditions

*Filled in by Task 3: the public host the frame was pointed at, the
`SKYPANE_SLEEP_S` in force during the run and the value restored
afterwards, whether `skypane-byos.service` stayed active throughout and
whether it restarted, whether `history.db` was reachable throughout and
whether the journald fallback was needed at any point (and, only if the
fallback was used, whether journald retention covered the whole
window), any home-network or internet outage noticed, charge/recharge
times, the pack's post-depletion physical condition, and any
interruption or anomaly from the check-in table.*
