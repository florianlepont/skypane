# Wake energy

Every figure in this document is an energy estimate from voltage and timing, or a duration reported by the device. None is a current measurement. Battery ratings and the voltage-to-charge curve are not measurements either.

## Telemetry contract

The frame reports how long each phase of a wake took. It sends this in one request header, `X-Wake-Stats`, on `GET /device/v1/display`. There is no second request.

### Header grammar

The value is a semicolon-separated `key=value` list that starts with `v=1`, for example `v=1;seq=812;bt=420;wf=1900;att=1;p_seq=811;p_aw=1480;p_rq=310;p_dl=0;p_dr=0;p_sp=0;p_tls=650;p_rd=0;p_out=ok`.

| Key | Meaning | Unit | Bound |
|-----|---------|------|-------|
| v | format version, validated, not stored | none | must be 1 |
| seq | boot counter of this wake (NVS) | count | 0 to 4294967295 |
| bt | app start to Wi-Fi start | ms | 0 to 3600000 |
| wf | Wi-Fi connect plus time sync | ms | 0 to 3600000 |
| att | Wi-Fi attempts | count | 0 to 16 |
| p_seq | boot counter of the previous wake | count | 0 to 4294967295 |
| p_aw | previous wake, total awake time at sleep entry | ms | 0 to 3600000 |
| p_rq | previous wake, display request | ms | 0 to 3600000 |
| p_dl | previous wake, image download | ms | 0 to 3600000 |
| p_dr | previous wake, panel draw | ms | 0 to 3600000 |
| p_sp | SPI transfer inside the draw (timer reads only) | ms | 0 to 3600000 |
| p_tls | previous wake, first TLS connect | ms | 0 to 3600000 |
| p_rd | previous wake redraw: 0 no draw, 1 drawn, 2 deferred | code | 0 to 2 |
| p_out | previous wake outcome: `ok` or the failure step; lowercase letters, digits, hyphen, 1 to 16 characters | token | token |

The `p_` keys describe the previous wake because the device writes them in RTC memory just before deep sleep and sends them on the next wake.

The whole value is at most 192 bytes. The worst case with every field at its bound is 173 bytes. The cap is `WAKE_STATS_MAX_BYTES` in `server/wake_stats.py` and `FP_WAKE_STATS_MAX_LEN` in `firmware/main/wake_telemetry.h`; a check compares the two.

Any violation (unknown key, duplicate key, out-of-range value, bad token, unknown version, oversize) makes the server ignore the whole header and store NULL in every wake column. The battery reading and the other telemetry are still stored.

### Stored columns

Thirteen nullable columns on `device_health`, one row per wake. They are added by a guarded `ALTER TABLE ADD COLUMN` at schema initialisation; a "duplicate column name" error from a concurrent process counts as already migrated.

| Header key | Column | Type |
|------------|--------|------|
| seq | wake_seq | integer |
| bt | boot_ms | integer |
| wf | wifi_ms | integer |
| att | wifi_attempts | integer |
| p_seq | prev_seq | integer |
| p_aw | prev_awake_ms | integer |
| p_rq | prev_request_ms | integer |
| p_dl | prev_download_ms | integer |
| p_dr | prev_draw_ms | integer |
| p_sp | prev_spi_ms | integer |
| p_tls | prev_tls_ms | integer |
| p_rd | prev_redraw | integer |
| p_out | prev_outcome | text |

### Export keys

The read-only battery-history export returns eighteen keys per row: the five existing keys followed by the thirteen column names above. All are always present and null when absent. Before the columns exist (before the first migration after a deploy) the export falls back to the five existing keys and does not fail.

### What NULL means

NULL means unknown, not zero. It appears when the frame sent no header (older firmware), when the header was rejected, or when the wake had no previous record.

### Gap after an OTA

After a successful over-the-air update the firmware restarts without entering deep sleep. The update wake's own record is never written, and RTC memory is reinitialised. The next wake therefore sends no `p_` keys, and its `seq` need not follow the previous row's `seq` by one, because every app start increments the counter. Readers treat a missing `p_` block or a gap in `seq` as unknown wakes, never as an error and never as zeros.

## Model

`hardware/wakemodel.py` estimates what one wake costs from a battery-history export. It reads the export, joins each row's previous-wake fields to the previous wake by sequence number, and classifies every wake from the device-reported fields (never from the time between rows): no-change (`p_rd=0`, outcome `ok`), redraw (`p_rd=1`), deferred (`p_rd=2`), failed (any other outcome with `p_rd=0`) or unknown. A row without a previous-wake block, a block that names another sequence number, and a jump in sequence numbers all make the wakes concerned unknown. They are never guessed and never counted as zeros.

The export is cut into consecutive segments (48 h by default) after the first 24 h are ignored. Each segment gives the charge used, from the fall of the rated-curve charge fraction between two median end points (12 h windows, quiet-hour polls left out, the same curve and quiet-hour test as `logtools.py`), the hours between those end points, and the count of no-change and redraw wakes between them. A segment that starts above 4000 mV (the uncalibrated part of the curve), has fewer than 5 non-quiet polls in an end window, or has more than a quarter of its wakes unknown, deferred or failed, is dropped and reported.

Three unknowns are fitted by exact non-negative least squares:

    charge used (mAh) = standing_mA x hours + no_change_mAh x no-change wakes + redraw_mAh x redraw wakes

None of the three is ever printed negative. A standing draw near zero is a result, not a refusal: it is always printed as an upper bound ("at most N mA, 95 percent upper bound") with the best fit shown only as "may be zero".

### Run

    python3 hardware/wakemodel.py fit EXPORT --capacity-mah N [--out FILE.json]

`--capacity-mah` is the pack rating, not a measurement. Exit code 0 is a fit, 2 is a refusal, 1 is a usage or file error. `--out` writes a deterministic JSON report (sorted keys, no run time, no absolute path).

### Device filter

An export can mix devices (the owner frame has `wake_seq` around 21000 to 22000, a second device is below 1000). `fit` and `rates` take `--seq-min`, `--seq-max`, `--since` and `--until` (ISO 8601; a time without an offset means UTC; `--since` is inclusive, `--until` exclusive). As soon as any of the four is given, a row with no integer `wake_seq` is dropped, because it cannot be placed on a device. Each dropped row is counted once and the output prints "device filter: kept N of M rows; X outside the wake_seq range, Y with null wake_seq, Z outside the time range". A filter that leaves no row is a refusal; a bad time or an inverted range is a usage error (exit 1). Without a filter option nothing changes: same output, same JSON.

### Refusals

The tool refuses, prints the reason and "No wake energy figure is given.", and still prints the device-reported awake-time breakdown (a direct measurement) when:

| Reason | Default limit |
|--------|---------------|
| no row carries per-wake fields | none |
| too few usable segments | at least 6 |
| the redraw share barely varies across segments | spread of at least 0.15 |
| the design is ill-conditioned (hours and wake counts nearly proportional) | scaled condition number at most 100 |
| the redraw wake energy is not resolved above zero | 95 percent range above zero |
| the implied mean current during awake time conflicts with the reported timing | at most 500 mA no-change, 200 mA redraw |

Each reason names what would separate the unknowns. With one check-in interval, hours and wake counts are exactly proportional, so a baseline needs a window at another interval, or a period with a different redraw share. A baseline of at least 14 days at one interval gives six 48 h segments; a second window at another interval is likely needed as well. The limits can be changed with flags, and the output states them.

### Reading the output

The ranges are approximate 95 percent ranges from the unconstrained least-squares covariance and a t table; they ignore curve and capacity error. The implied current is the fitted energy divided by the device-reported mean awake time; it is a plausibility check on the fit, not a measurement. Every output states that the figures are energy estimates from voltage and timing on a rated capacity, not current measurements.

### What was not fittable before

The aggregates of the old-pack runs could not be fitted: a three-parameter solve on them (the researcher's arithmetic on rough inputs) gave negative coefficients, which are not physical. They also carry no per-wake fields, so the tool refuses the committed old-pack export with "no per-wake telemetry in this export".

### Release notes

The firmware release that starts this telemetry carries instrumentation only:

- One new request header, `X-Wake-Stats`, on the existing display request.
- A small record kept in RTC memory across deep sleep (it is not written to flash).
- No behavioural change: the picture, the wake interval, hash-skip, quiet hours, display-off and the battery-critical overrides are untouched.
- No extra request, no extra flash write and no added delay. The panel code gains two timer reads and nothing else.

Not yet established: the firmware has not been compiled for the target in the authoring environment, so the container build in CI must be green before a version is tagged, and the on-target cost of the additions is unmeasured. The first wake after an update has no `p_` keys (see "Gap after an OTA").

Rollback: the previous release stays offerable from the Update page, above the version floor. Scheduling it again is allowed; the refusal of a lower build number applies at publish time only. The frame still refuses any install at or below 3500 mV. The owner steps, in French, are in `hardware/WAKE-ENERGY-FR.md`.

### Fixtures

`hardware/fixtures/wakemodel-synthetic.jsonl` and `wakemodel-collinear.jsonl` are synthetic. The truth values (standing draw, no-change and redraw energy, pack rating) are in the builder in `hardware/test_wakemodel.py`, which also regenerates both fixtures and `wakemodel-synthetic-output.json` byte for byte in a test. `python3 hardware/wakemodel.py selftest` runs the tool on the two fixtures.

The relative mode has three more synthetic fixtures, written by the generator `build_rates_export` in the same test file (its docstring gives the generator rules; the truth is s = 0.05 mV/h, C = 0.01 mV per check, R = 0.06 mV per redraw): `wakemodel-rates-3regime.jsonl` (three regimes at two check intervals, a power-on and a firmware change inside windows a and b), `wakemodel-rates-collinear.jsonl` (one check interval, three redraw cadences, which the tool refuses) and `wakemodel-two-device.jsonl` (the 3-regime rows mixed with a second device and rows without `wake_seq`, for the device filter). A test reproduces each file byte for byte.

## Relative mode

`python3 hardware/wakemodel.py rates` is for the case where `fit` has to refuse: the battery sits above 4000 mV, where the rated curve is uncalibrated, and no rated capacity is trusted. It compares regimes by the slope of the raw voltage. It takes no capacity and uses no curve.

    python3 hardware/wakemodel.py rates EXPORT --window NAME=START,END [--window ...] [--reference NAME] [--out FILE.json]

### What it computes

For each window (a regime held for 24 to 72 h):

- usable hours: UTC hours holding at least 3 polls (`--min-hour-polls`), outside the quiet window and outside the restart exclusion;
- each usable hour is one sample: the median voltage of its polls at the median time of those polls (the median blunts the whole-millivolt quantisation);
- the voltage fall in mV per hour, from an ordinary least-squares line through those samples, with an approximate 95 percent range;
- check wakes and redraw wakes per hour, from the device-reported previous-wake fields. A check is a wake with no panel draw (no-change, deferred or failed), a redraw is a wake that drew. The time base is wall-clock time with the quiet hours included, because the battery drains through them; the quiet window only leaves polls out of the voltage samples. Unknown wakes are counted, printed and left out;
- the median voltage of the usable polls.

A restart (a `boot_reason` other than a timer or button wake, or a change of `fw_version`) excludes `--reset-hours` (3 h by default) after it from that window, and the excluded hours are printed.

With three or more windows the tool solves, by the same exact non-negative least squares as `fit`:

    fall (mV/h) = s + C x checks per hour + R x redraws per hour

`s` is in mV per hour (the standing draw), `C` and `R` are in mV per wake. It also prints R/C and R over the fall of the reference window (the first window unless `--reference` says otherwise), each with an approximate 95 percent range. The ranges propagate the per-window slope errors through the unconstrained least-squares map; with three windows the solve has no spare degrees of freedom, so they ignore model error.

### Refusals

Exit code 0 is a solve, 2 is a refusal (with the reason and the data that would fix it), 1 is a usage or file error. The tool refuses when:

| Reason | Default limit | What fixes it |
|--------|---------------|---------------|
| fewer than three windows | 3 | more regimes, each held 24 to 72 h |
| a window has too few usable hours | at least 24 (`--min-usable-hours`) | hold the regime longer, or fewer restarts |
| the median voltages of the windows are far apart | within 60 mV (`--band-mv`) | windows closer in time or voltage |
| a slope is not resolved (its range is wider than its value) | none | a longer window |
| the design is rank-deficient or ill-conditioned | condition number at most 100 (`--max-condition`) | a window at another check interval |

The 60 mV band keeps the windows on one part of the curve, where a slope in mV per hour means roughly the same thing. It is an option, and the band in force is printed in the Inputs of every output. Consecutive 48 h windows can drift past it as the battery falls; widening it is allowed and is visible in the output.

### What two windows give

With exactly two windows the tool prints both falls, their ratio with an approximate 95 percent range, and says that C, R and the standing draw cannot be separated. It exits 2.

### Windows at one check interval cannot be separated

If every window uses the same check interval, every wake is either a check or a redraw, so checks plus redraws per hour is the same in all windows. The standing draw, the check cost and the redraw cost then cannot be told apart: the three-window solve is rank-deficient and the tool refuses it. What such a schedule supports is each window's slope and the ratio between two windows. Separating the three needs a window at another check interval, for example the 60 s experiment cleared so that the frame wakes every 5 minutes and redraws at every wake.

### Reading the output

Every output states that these are relative voltage-slope comparisons on the rated, uncalibrated top-of-charge region of the curve, in mV per hour, and that they are not mAh and not a current measurement. A slope says which regime drains faster and by what ratio; it does not say how much charge a wake costs.

### The owner's two windows

The owner confirmed two windows, both at a 60 s check interval:

| Window | Regime | Period |
|--------|--------|--------|
| 1 | check 60 s, redraw 5 min | from 2026-11-15T07:55Z, 48 h |
| 2 | check 60 s, redraw 60 min | from about 2026-11-17T08:00Z, 48 h |

A third window is a requirement for separating the three unknowns, not an agreed schedule. If wanted, a window at another check interval (see above) supplies it. An earlier stretch (check 60 s, redraw 15 min, 2026-11-13T17:45Z to 2026-11-15T07:55Z) exists in the export and can be added as a further window at the same check interval; it adds a slope, not separation.

Points to handle in the data: the first hours after the 2026-11-12 charge are relaxation, so windows start later; firmware versions changed on 2026-11-15 at 11:19, 13:33 and 14:51 UTC, and the restart exclusion removes those hours when `fw_version` changes (or pick windows on one version); the second device is filtered out with `--seq-min` and `--seq-max`. Example for window 1 against window 2, once window 2 has run:

    python3 hardware/wakemodel.py rates EXPORT.jsonl \
        --seq-min 20000 --seq-max 30000 \
        --window w1=2026-11-15T07:55Z,2026-11-17T07:55Z \
        --window w2=2026-11-17T08:00Z,2026-11-19T08:00Z

With two windows this exits 2 by design and prints the two falls and their ratio.
