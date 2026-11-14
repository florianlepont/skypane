# Second hardware: battery measurement

Status: **not measured.** This file holds the method and will hold the raw sample
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

## Raw sample

None yet.

## Derived values

None yet. Each value will be listed with its name from `BATTERY_VALUE_NAMES`, the way
it was derived, the date, and whether it is measured or provisional.

## Caveats to keep

- The refresh time of the panel is longer than its datasheet figure in practice, and
  the current depends on temperature. Record the room temperature.
- Any arithmetic done with `hardware/logtools.py` is done read-only, and the method
  is written in this file so that it can be repeated.
