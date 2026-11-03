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
