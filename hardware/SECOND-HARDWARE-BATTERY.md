# Second hardware: battery measurement

Status: **not measured; Phase 58 closed with the model provisional (2026-11-15).** This file holds the method and will hold the raw sample
and the derived values. No number below is a measurement of a cell. The legacy
frame's measurement files (`BATTERY-MODEL.md`, `BATTERY-RUN.md`, `SLEEP-CURRENT.md`,
`logtools.py`) are read-only for this work and are not rewritten.

## What is needed and why

The server needs, for the evaluation unit's hardware type, the values of
`BATTERY_VALUE_NAMES` in `server/hardware.py` (voltage thresholds, the discharge
curve and the current and refresh figures), each with a source and a date. Today they
are copied from the legacy profile and marked provisional, "not a measurement". They
are replaced only by values taken from a sample described here. A value that was not
measured stays unmeasured, with the reason.

## What the unit has reported so far

With no battery connected, `X-Battery-Mv` read between 3630 and 4180 mV and changed
between wakes. That is a floating sense input, not a cell, and none of it is used.
The sense divider, its enable pin and the pin numbers are inherited from the EE02
board family and have not been checked on an EE04 (`sdkconfig.second.defaults`).

## Method

1. **Hardware.** A 3.7 V single-cell LiPo with a JST 2.0 mm connector of the right
   polarity (check the plug against the silkscreen of the board before connecting).
   The cell the owner intends to use, and its rated capacity, are recorded with the
   sample. The battery switch on the board is ON. A multimeter is needed.
2. **Calibrate the reading.** With the cell connected, read its terminal voltage with
   the multimeter at the battery connector and compare it with the `X-Battery-Mv` of the
   same wake. Do this at three or more voltages across the usable range (charge level
   changes between sessions). Record the pairs. The offset or scale between them is a
   finding in itself, and a divider that does not follow the multimeter is a defect to
   fix before any value is trusted.
3. **Sleep current.** Measure the current while the unit deep-sleeps, with a
   multimeter in series on the battery lead or a power analyser, after the unit has
   settled for a few minutes. Record the instrument, its range and the figure. Remove
   the USB cable for this: it feeds the board.
4. **Refresh current and duration.** Measure the current during a wake that refreshes
   the panel, and time the panel refresh from the first command to the busy line
   release, for a full colour image. Repeat at least three times and record all values.
5. **Wake cadence.** The bench server's `sleep_s` sets the wake interval; record the
   interval used and the wake durations the unit reports.
6. **Discharge segment.** Run the unit on the battery at its normal cadence and record
   `X-Battery-Mv` against time for as long as the owner allows (hours or days; say the
   duration honestly). A short segment gives values marked provisional, never measured.
   Keep the raw lines of the server's telemetry output as the raw sample.
7. **Charging.** Note what the charge indicator shows while USB is connected, and
   whether the unit still wakes on schedule while charging.

## Capture and analysis with the existing tools

No new parser is needed: the firmware already reports the battery reading and its
wake statistics on every poll (`X-Battery-Mv`, `X-Wake-Stats`), the bench server keeps
them in the unit's own `history.db`, and `hardware/logtools.py` already reads that.
It is only run, never edited, and its commands that write an output file default into
`hardware/logs/`, which belongs to the live frame's measurements: use only the commands
below, or give an explicit output path elsewhere.

**The unit must be a claimed device of the bench fleet**, not a pending frame: a pending
frame's readings are not kept in a `history.db`. Claim its code first (see the runbook).

**1. Keep the bench server awake and its output stamped.** The Mac must not sleep and
must stay on the same Wi-Fi for the whole discharge, or the unit shows NO CONNECTION and
the record has a gap.

```bash
cd ~/Projects/skypane
SKYPANE_SIM_HARDWARE=1 caffeinate -i ~/skypane-bench/venv/bin/python3 stub-server/byos_server.py --image ~/skypane-bench/live-placeholder.bin --port 8642 --sleep 300 --state-dir ~/skypane-bench/server-state 2>&1 | python3 hardware/logtools.py stamp | tee -a ~/skypane-bench/battery-run.log
```

The interval (`--sleep`) is the cadence of the run: 300 s matches the live frame's. Note
the interval used with the sample.

**2. Check the stamped log** (read-only, prints a report):

```bash
python3 hardware/logtools.py check-battery ~/skypane-bench/battery-run.log --capacity-mah <rated mAh> --interval-s 300 --cutoff-mv 3400
```

It reports the span, the coverage, the largest gap between polls, the millivolt drop, the
projected life for other intervals, and whether the pack reached the cutoff. The capacity
is the cell's rating, not a measurement. A run of less than a day fails its span check on
purpose: it is not a battery-life result.

**3. The durable record.** The server also stores every poll in the unit's own database,
with the firmware's wake timings. Export it as JSON Lines and convert it to the same
log shape:

```bash
ls ~/skypane-bench/server-state/devices
python3 - ~/skypane-bench/server-state/devices/<d_id>/history.db > ~/skypane-bench/battery-rows.jsonl <<'PY'
import json, sqlite3, sys
conn = sqlite3.connect("file:%s?mode=ro" % sys.argv[1], uri=True)
conn.row_factory = sqlite3.Row
for row in conn.execute("SELECT ts, battery_mv, fw_version, boot_reason, rssi FROM device_health ORDER BY ts"):
    print(json.dumps(dict(row)))
PY
python3 hardware/logtools.py from-history-db ~/skypane-bench/battery-rows.jsonl > ~/skypane-bench/battery-from-history.log
python3 hardware/logtools.py check-battery ~/skypane-bench/battery-from-history.log --capacity-mah <rated mAh> --interval-s 300 --cutoff-mv 3400
```

The device directory changes (a new `d_...`) if the unit is retired and claimed again; use
the one that holds the run. The wake timings (`boot_ms`, `wifi_ms`, `prev_awake_ms`,
`prev_draw_ms`, ...) are in the same table for the refresh and wake-time figures.

The conversion and the check were run against the bench server's own database in a
scratch directory with a few polls: they parse the unit's lines, and the multi-day checks
fail, as they should for so short a run. No real run exists yet.

## Raw sample

None. One discharge run was attempted and gave no valid sample: it started on
2026-11-15 at 09:08 with the USB cable unplugged and a first reading of 4064 mV (low for a
full cell, not checked with a multimeter), on a cell the owner gave as about 3000 mAh from
memory. It was interrupted by USB plugs and by the bench server stopping, and the log was
not kept. The owner closed Phase 58 on 2026-11-15 with the model provisional; battery data
is expected later from production use (Phase 64, Phase 65).

## Derived values

None. Each value will be listed with its name from `BATTERY_VALUE_NAMES`, the way
it was derived, the date, and whether it is measured or provisional.

## Caveats to keep

- The refresh time of the panel is longer than its datasheet figure in practice, and
  the current depends on temperature. Record the room temperature.
- Any arithmetic done with `hardware/logtools.py` is done read-only, and the method
  is written in this file so that it can be repeated.
