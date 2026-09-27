# Phase 38 — efficiency baseline and before/after record

Single record for every before/after value this phase's checkpoints
produce (ROADMAP success criteria 1 and 4: page weight/request time
measured before and after on every route, and poll-cycle wall time
measured before and after with no fixed 1.1s sleep). Instruments first,
per the phase's own "Locked by the ledger" rule: this file's Before
section is committed ahead of any production change EFF-01..EFF-06
makes.

Code state measured: branch `claude/plan-phase-38` at `2b1d7fd` (plan
38-01, instruments only - no production file touched yet).

## Measurement setup

Produced by `scripts/measure_efficiency.py`, the same instrument the
companion test suite uses (`test-support/efficiency_probe.py`), so a
"before" and an "after" run are comparable:

```
server/.venv/bin/python scripts/measure_efficiency.py --label before
```

(defaults: `--repeats 5 --latency 0.25`, matching the research
measurement's own settings).

What is faked: the script installs `skypane_test_support`'s resolver
guard onto `socket.getaddrinfo`/`gethostbyname`/`gethostbyname_ex` for its
whole run (any non-loopback DNS lookup raises), replaces
`server.plane.enrich.default_transport` with a fake returning `(404,
None)`, and replaces `server.plane.detect.query_provider` with an
offline fake - `scripts/measure_efficiency.py` never makes a real
network call. The poll-cycle table additionally routes through
`efficiency_probe.fake_provider_latency()`, which simulates each
provider's ADS-B answer with a configurable latency (`--latency`,
default 0.25s) instead of `query_provider`'s network fake.

Timings (`mean_ms`, `wall_s`) are recorded here for visibility, never
asserted by a test - only counts (connections, `init_schema` runs,
commits, sleeps, `poll_state` writes) are asserted, by each later plan's
own tests.

The companion server runs in-process (`InProcessAppServer`) against a
scratch state directory seeded with `efficiency_probe.seed_history()`
(30 `device_health` rows, 30 `runway_events` rows), removed at exit. The
poll-cycle table runs against a second, separate fresh state directory,
so its seven branches see only each other's persisted `poll_state.json`,
never the companion measurement's history rows.

## Before

Recorded 2026-09-26 (`--label before`, defaults: `--repeats 5 --latency
0.25`), against the unmodified tree (before any of EFF-01..EFF-06's
production changes).

## Measurement

- Label: before
- Commit: 2b1d7fd
- Machine: vm
- Platform: Linux-6.18.44-fc-v37-x86_64-with-glibc2.39
- Python: 3.11.15
- Repeats: 5
- Latency (s): 0.25
- Timestamp (UTC): 2026-09-26T13:07:23Z

## Routes

| route | status | identity_bytes | gzip6_bytes | mean_ms | script_count | sqlite_conns | init_schema | commits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| / | 200 | 22761 | 4368 | 8.55 | 15 | 12.0 | 12.0 | 0.0 |
| /display | 200 | 65867 | 7832 | 8.75 | 15 | 11.0 | 11.0 | 0.0 |
| /device | 200 | 18491 | 4119 | 7.17 | 15 | 10.0 | 10.0 | 0.0 |
| /flights | 200 | 93911 | 5821 | 8.95 | 15 | 10.0 | 10.0 | 0.0 |
| /health | 200 | 41283 | 6650 | 7.31 | 16 | 11.0 | 11.0 | 0.0 |
| /airlines | 200 | 52899 | 6644 | 6.46 | 15 | 9.0 | 9.0 | 0.0 |
| /login | 200 | 1493 | 758 | 1.21 | 1 | 0.0 | 0.0 | 0.0 |
| /static/style.css | 200 | 140426 | 36939 | 1.02 | 0 | 0.0 | 0.0 | 0.0 |
| /static/nav-dropdown.js | 200 | 5387 | 2276 | 0.93 | 0 | 0.0 | 0.0 | 0.0 |
| /static/dirty-state.js | 200 | 14032 | 5012 | 0.92 | 0 | 0.0 | 0.0 | 0.0 |
| /static/list-filter.js | 200 | 5439 | 2230 | 0.88 | 0 | 0.0 | 0.0 | 0.0 |
| /static/copy-button.js | 200 | 5132 | 1944 | 0.87 | 0 | 0.0 | 0.0 | 0.0 |
| /static/freshness.js | 200 | 21982 | 7494 | 1.01 | 0 | 0.0 | 0.0 | 0.0 |
| /static/panel-lookup.js | 200 | 19372 | 6385 | 1.02 | 0 | 0.0 | 0.0 | 0.0 |
| /static/flash-cleanup.js | 200 | 1328 | 753 | 0.93 | 0 | 0.0 | 0.0 | 0.0 |
| /static/poll-cooldown.js | 200 | 2238 | 1022 | 0.95 | 0 | 0.0 | 0.0 | 0.0 |
| /static/confirm-submit.js | 200 | 1534 | 827 | 0.98 | 0 | 0.0 | 0.0 | 0.0 |
| /static/theme-preview.js | 200 | 9127 | 3381 | 1.14 | 0 | 0.0 | 0.0 | 0.0 |
| /static/flight-rows.js | 200 | 7188 | 2776 | 0.92 | 0 | 0.0 | 0.0 | 0.0 |
| /static/submit-guard.js | 200 | 3509 | 1513 | 0.83 | 0 | 0.0 | 0.0 | 0.0 |
| /static/relative-time.js | 200 | 8747 | 3355 | 0.88 | 0 | 0.0 | 0.0 | 0.0 |
| /static/quick-switch.js | 200 | 8433 | 3366 | 0.91 | 0 | 0.0 | 0.0 | 0.0 |
| /static/value-controls.js | 200 | 30120 | 9587 | 0.90 | 0 | 0.0 | 0.0 | 0.0 |
| /static/battery-trend.js | 200 | 5780 | 2199 | 0.91 | 0 | 0.0 | 0.0 | 0.0 |

## First-load weight

| route | first_load_identity_bytes | first_load_gzip6_bytes |
| --- | --- | --- |
| / | 306755 | 93228 |
| /display | 349861 | 96692 |
| /device | 302485 | 92979 |
| /flights | 377905 | 94681 |
| /health | 331057 | 97709 |
| /airlines | 336893 | 95504 |

## Static revalidation

| path | etag | last_modified | cache_control | revalidate_status | revalidate_bytes |
| --- | --- | --- | --- | --- | --- |
| /static/style.css | None | None | public, max-age=300 | 200 | 140426 |
| /static/freshness.js | None | None | public, max-age=300 | 200 | 21982 |

## Freshness tick

| route | freshness_status | freshness_bytes |
| --- | --- | --- |
| / | 200 | 22761 |
| /display | 200 | 65867 |
| /flights | 200 | 93911 |
| /health | 200 | 41283 |

## Poll cycle

| branch | wall_s | sleeps | connections | init_schema | commits | poll_state_writes | poll_state_bytes | state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| empty sky (first) | 1.696 | [1.1] | 3 | 3 | 3 | 1 | 67 | empty |
| empty sky (repeat) | 1.630 | [1.1] | 3 | 3 | 2 | 1 | 67 | empty |
| flight detected | 1.789 | [1.1] | 3 | 3 | 4 | 2 | 2372 | departing |
| same flight again | 1.638 | [1.1] | 3 | 3 | 3 | 2 | 2372 | departing |
| nothing new, flight on screen | 1.606 | [1.1] | 3 | 3 | 2 | 1 | 1186 | departing |
| display_off hold entry | 0.239 | [] | 3 | 3 | 3 | 2 | 2432 | display_off |
| display_off hold repeat | 0.004 | [] | 3 | 3 | 2 | 1 | 1216 | display_off |

Empty-sky wall time at latency 0 (fresh state dir): 1.1688 s

### Cross-check against the research table

`38-RESEARCH.md`'s "Baseline numbers measured during research" table was
measured the same way (mean of 5, `InProcessAppServer`, a 30/30-row
seed), on the same dev container. Every static-asset byte count here
(the 15 shell scripts sum to 143,568 B identity, `style.css` to 140,426
B) matches the research table exactly, since those are deterministic
file bytes independent of seed data. The poll-cycle wall times and the
`/login`/`/airlines`/`/device` route weights also match closely (within
1-2%). The two largest per-route gaps are `/health` identity (41,283 B
here vs. 36,367 B in research, +13.5%) and `/flights` gzip-6 (5,821 B
here vs. 6,536 B in research, -10.9%) - both come from this run's own
seed content (this instrument's `seed_history()` writes a fixed
`fw_version`/`boot_reason`/`rssi` on every row, which the research
throwaway script did not), not from any code change since research. No
value differs from the research table by more than 20%.

## After

Recorded 2026-09-26 (`--label after`, defaults: `--repeats 5 --latency
0.25`), against the tree after all of EFF-01..EFF-06's production changes
(38-02 through 38-12), commit `79e1039`.

## Measurement

- Label: after
- Commit: 79e1039
- Machine: vm
- Platform: Linux-6.18.44-fc-v37-x86_64-with-glibc2.39
- Python: 3.11.15
- Repeats: 5
- Latency (s): 0.25
- Timestamp (UTC): 2026-09-26T21:28:14Z

## Routes

| route | status | identity_bytes | gzip6_bytes | mean_ms | script_count | sqlite_conns | init_schema | commits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| / | 200 | 22327 | 4323 | 4.58 | 6 | 1.0 | 0.0 | 0.0 |
| /display | 200 | 65653 | 7824 | 4.26 | 10 | 1.0 | 0.0 | 0.0 |
| /device | 200 | 18116 | 4062 | 2.71 | 8 | 1.0 | 0.0 | 0.0 |
| /flights | 200 | 93636 | 5798 | 5.51 | 9 | 1.0 | 0.0 | 0.0 |
| /health | 200 | 40901 | 6618 | 5.03 | 8 | 1.0 | 0.0 | 0.0 |
| /airlines | 200 | 52413 | 6565 | 3.44 | 6 | 1.0 | 0.0 | 0.0 |
| /login | 200 | 1493 | 758 | 1.15 | 1 | 0.0 | 0.0 | 0.0 |
| /static/style.css | 200 | 140426 | 36939 | 1.15 | 0 | 0.0 | 0.0 | 0.0 |
| /static/nav-dropdown.js | 200 | 5387 | 2276 | 1.29 | 0 | 0.0 | 0.0 | 0.0 |
| /static/freshness.js | 200 | 25194 | 8536 | 1.12 | 0 | 0.0 | 0.0 | 0.0 |
| /static/flash-cleanup.js | 200 | 1328 | 753 | 1.03 | 0 | 0.0 | 0.0 | 0.0 |
| /static/submit-guard.js | 200 | 3509 | 1513 | 1.06 | 0 | 0.0 | 0.0 | 0.0 |
| /static/relative-time.js | 200 | 8747 | 3355 | 1.04 | 0 | 0.0 | 0.0 | 0.0 |
| /static/quick-switch.js | 200 | 8433 | 3366 | 0.98 | 0 | 0.0 | 0.0 | 0.0 |
| /static/dirty-state.js | 200 | 14032 | 5012 | 1.00 | 0 | 0.0 | 0.0 | 0.0 |
| /static/confirm-submit.js | 200 | 1534 | 827 | 0.97 | 0 | 0.0 | 0.0 | 0.0 |
| /static/theme-preview.js | 200 | 9127 | 3381 | 1.00 | 0 | 0.0 | 0.0 | 0.0 |
| /static/value-controls.js | 200 | 30120 | 9587 | 1.11 | 0 | 0.0 | 0.0 | 0.0 |
| /static/poll-cooldown.js | 200 | 2238 | 1022 | 1.03 | 0 | 0.0 | 0.0 | 0.0 |
| /static/list-filter.js | 200 | 5439 | 2230 | 1.01 | 0 | 0.0 | 0.0 | 0.0 |
| /static/copy-button.js | 200 | 5132 | 1944 | 1.05 | 0 | 0.0 | 0.0 | 0.0 |
| /static/panel-lookup.js | 200 | 19372 | 6385 | 1.06 | 0 | 0.0 | 0.0 | 0.0 |
| /static/flight-rows.js | 200 | 7188 | 2776 | 1.04 | 0 | 0.0 | 0.0 | 0.0 |
| /static/battery-trend.js | 200 | 5780 | 2199 | 0.99 | 0 | 0.0 | 0.0 | 0.0 |

## First-load weight

| route | first_load_identity_bytes | first_load_gzip6_bytes |
| --- | --- | --- |
| / | 215351 | 61061 |
| /display | 313490 | 83369 |
| /device | 232336 | 67885 |
| /flights | 315358 | 72505 |
| /health | 241843 | 66363 |
| /airlines | 236621 | 60016 |

## Static revalidation

| path | etag | last_modified | cache_control | revalidate_status | revalidate_bytes |
| --- | --- | --- | --- | --- | --- |
| /static/style.css | "4170f9417bb7d1d1e877a768257a07ce" | Sat, 26 Sep 2026 12:06:26 GMT | public, no-cache | 304 | 0 |
| /static/freshness.js | "5bda40c9d1f1edb64caf480d4fc8f45b" | Sat, 26 Sep 2026 21:05:24 GMT | public, no-cache | 304 | 0 |

## Freshness tick

| route | freshness_status | freshness_bytes |
| --- | --- | --- |
| / | 304 | 0 |
| /display | 304 | 0 |
| /flights | 304 | 0 |
| /health | 304 | 0 |

## Poll cycle

| branch | wall_s | sleeps | connections | init_schema | commits | poll_state_writes | poll_state_bytes | state |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| empty sky (first) | 0.340 | [] | 1 | 1 | 1 | 1 | 60 | empty |
| empty sky (repeat) | 1.043 | [0.7667574882507324, 0.7668595314025879] | 1 | 0 | 1 | 0 | 0 | empty |
| flight detected | 1.265 | [0.8238120079040527, 0.8239095211029053] | 1 | 0 | 1 | 1 | 1009 | departing |
| same flight again | 0.944 | [0.6590497493743896, 0.65899658203125] | 1 | 0 | 1 | 0 | 0 | departing |
| nothing new, flight on screen | 1.071 | [0.8152492046356201, 0.8152856826782227] | 1 | 0 | 1 | 0 | 0 | departing |
| display_off hold entry | 0.246 | [] | 1 | 0 | 1 | 1 | 1036 | display_off |
| display_off hold repeat | 0.002 | [] | 1 | 0 | 1 | 0 | 0 | display_off |

Empty-sky wall time at latency 0 (fresh state dir): 0.0665 s

## Deltas

### Per tab route (Before -> After)

| route | identity_bytes | first_load_identity_bytes | first_load_gzip6_bytes | script_count | sqlite_conns | mean_ms |
| --- | --- | --- | --- | --- | --- | --- |
| / | 22761 -> 22327 (-1.9%) | 306755 -> 215351 (-29.8%) | 93228 -> 61061 (-34.5%) | 15 -> 6 | 12.0 -> 1.0 | 8.55 -> 4.58 |
| /display | 65867 -> 65653 (-0.3%) | 349861 -> 313490 (-10.4%) | 96692 -> 83369 (-13.8%) | 15 -> 10 | 11.0 -> 1.0 | 8.75 -> 4.26 |
| /device | 18491 -> 18116 (-2.0%) | 302485 -> 232336 (-23.2%) | 92979 -> 67885 (-27.0%) | 15 -> 8 | 10.0 -> 1.0 | 7.17 -> 2.71 |
| /flights | 93911 -> 93636 (-0.3%) | 377905 -> 315358 (-16.6%) | 94681 -> 72505 (-23.4%) | 15 -> 9 | 10.0 -> 1.0 | 8.95 -> 5.51 |
| /health | 41283 -> 40901 (-0.9%) | 331057 -> 241843 (-27.0%) | 97709 -> 66363 (-32.1%) | 16 -> 8 | 11.0 -> 1.0 | 7.31 -> 5.03 |
| /airlines | 52899 -> 52413 (-0.9%) | 336893 -> 236621 (-29.8%) | 95504 -> 60016 (-37.2%) | 15 -> 6 | 9.0 -> 1.0 | 6.46 -> 3.44 |

Every route's `sqlite_conns` drops from 9-12 (one connection per lazily-built
markup piece, the pre-38-08 shape) to exactly 1 (one `connection_scope` for
the whole request, 38-03/38-08); `init_schema`/`commits` drop with it to 0
on a warm process (schema now runs once per process, not once per
connection). `script_count` drops to only the scripts each route's own
`_PAGE_SCRIPTS` tuple names (38-06). `mean_ms` drops on every route (the
connection/schema/script savings above); `identity_bytes`/first-load bytes
drop on every route too (the freshness token adds an `ETag` header and a
`data-refresh-token` body attribute, not markup bulk; the first-load total
folds in `/static/style.css`'s and each named script's own identity bytes,
unchanged file-for-file, so the drop there is entirely the fewer scripts
counted, not smaller files).

### Per poll branch (Before -> After)

| branch | wall_s | sleeps | connections | commits | poll_state_writes |
| --- | --- | --- | --- | --- | --- |
| empty sky (first) | 1.696 -> 0.340 | [1.1] -> [] | 3 -> 1 | 3 -> 1 | 1 -> 1 |
| empty sky (repeat) | 1.630 -> 1.043 | [1.1] -> [0.767, 0.767] | 3 -> 1 | 2 -> 1 | 1 -> 0 |
| flight detected | 1.789 -> 1.265 | [1.1] -> [0.824, 0.824] | 3 -> 1 | 4 -> 1 | 2 -> 1 |
| same flight again | 1.638 -> 0.944 | [1.1] -> [0.659, 0.659] | 3 -> 1 | 3 -> 1 | 2 -> 0 |
| nothing new, flight on screen | 1.606 -> 1.071 | [1.1] -> [0.815, 0.815] | 3 -> 1 | 2 -> 1 | 1 -> 0 |
| display_off hold entry | 0.239 -> 0.246 | [] -> [] | 3 -> 1 | 3 -> 1 | 2 -> 1 |
| display_off hold repeat | 0.004 -> 0.002 | [] -> [] | 3 -> 1 | 2 -> 1 | 1 -> 0 |

Empty-sky wall time at latency 0 (fresh state dir): 1.1688 s -> 0.0665 s
(-94.3%) - the fixed 1.1 s inter-provider sleep is gone; every branch's
`connections` drops from 3 (one per `open_db` call site) to 1
(`connection_scope` around the whole cycle, 38-07); `commits` drops from
2-4 to exactly 1 (`write_batch`, 38-07); a repeat/held cycle whose state is
byte-identical to the last write now records 0 `poll_state_writes` instead
of 1-2 (write-only-if-changed, 38-09). After's `sleeps` entries (0.66-0.82 s,
in pairs) are the two providers' own per-provider minimum-spacing waits at
this run's real, un-patched cadence (38-04/38-11), not the old fixed 1.1 s
sleep between different providers - no entry in any After row equals 1.1.

## Criteria

Quoting the numbers above against ROADMAP's four Phase 38 success criteria:

1. **Page weight and request time measured before/after on every route.**
   Every one of the 6 tab routes plus `/login` and every static asset has a
   Before and an After row in "Routes" and "First-load weight" above (e.g.
   `/`: 306755 -> 215351 first-load identity bytes, -29.8%; 93228 -> 61061
   gzip bytes, -34.5%; 8.55 -> 4.58 ms). Met.
2. **Second page load returns 304s for static files.** After's "Static
   revalidation" table: `/static/style.css` and `/static/freshness.js` both
   show `revalidate_status=304`, `revalidate_bytes=0`, with a real `etag`
   and `cache_control=public, no-cache` (Before: no etag, `max-age=300`,
   `revalidate_status=200`). After's "Freshness tick" table: all four
   refresh routes (`/`, `/display`, `/flights`, `/health`) answer an
   unchanged tick with `304`/`0` bytes. Met.
3. **SQLite connections per page request: 1; per poll cycle: 1.** After's
   "Routes" table: every one of the 6 tab routes shows `sqlite_conns=1.0`
   (Before: 9.0-12.0); `/login` and every static asset stay at 0.0 (no DB
   touched). After's "Poll cycle" table: all seven branches show
   `connections=1` (Before: 3). Met.
4. **Poll cycle wall time measured before/after (no fixed 1.1 s sleep).**
   After's "Poll cycle" table has a Before and After `wall_s` for all seven
   branches (e.g. "flight detected": 1.789 -> 1.265 s); the fresh-state-dir
   latency-0 empty-sky number drops from 1.1688 s to 0.0665 s. No `sleeps`
   entry in any After row equals `1.1` - the five branches that sleep at
   all show the two providers' own real per-provider spacing (0.659-0.824 s,
   in pairs); the two `display_off` hold branches show `[]` in both Before
   and After. Met.

All four ROADMAP success criteria for Phase 38 hold against the After
numbers above.

## Live compression (VPS)

`curl -s -o /dev/null -w '%{size_download}' --compressed -H 'Accept-Encoding: zstd' <url>`
against the production companion host, before and after `deploy/Caddyfile`
gains `encode zstd gzip` in the companion site block.

| when | URL | Accept-Encoding | Content-Encoding | Cache-Control / ETag | size_download | revalidate (`If-None-Match`) |
| --- | --- | --- | --- | --- | --- | --- |
| before (not captured live) | `/static/style.css` | zstd, gzip | none (no `encode` in the site file) | `public, max-age=300`, no ETag | 140,426 (identity, from the in-process Before table) | 200, full body |
| before (not captured live) | `/static/freshness.js` | gzip | none | `public, max-age=300`, no ETag | identity (in-process Before table) | 200, full body |
| after, 2026-09-27 | `https://<companion host>/static/style.css` | zstd, gzip | `zstd` | `public, no-cache`, ETag `"…-zstd"`, `Vary: Accept-Encoding` | 39,361 | 304, 0 bytes |
| after | `/static/freshness.js` | gzip | pending (not run) | pending | pending | pending |
| after | device host `/device/v1/display` | gzip | pending (expected: none) | - | - | - |

The live "before" rows were not captured: by the time the developer ran the
Task 2 commands, the static-cache and Caddy `encode` changes had already been
merged and deployed, so production answered with the new headers. The before
values above are the pre-change behaviour as measured in-process on the
unmodified tree (see `## Before`), which is what the site served before the
deploy. The style.css row shows the whole EFF-01 chain working live: Caddy
compresses the companion response with zstd (140,426 → 39,361 bytes, -72 %),
adds its `-zstd` suffix to the origin's strong ETag, and a revalidation with
that ETag still reaches the origin's 304 path (Caddy strips the suffix from
`If-None-Match`). The freshness.js row and the device-host check (no
`Content-Encoding` on the device protocol) are for the developer to re-run with
the Task 2 commands; they are recorded here when available.
