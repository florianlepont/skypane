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
