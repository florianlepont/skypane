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

Recorded by the final plan of this phase with the same command.

## Live compression (VPS)

`curl -s -o /dev/null -w '%{size_download}' --compressed -H 'Accept-Encoding: zstd' <url>`
against the production companion host, before and after `deploy/Caddyfile`
gains `encode zstd gzip` in the companion site block.

| when | URL | Accept-Encoding | Content-Encoding | size_download |
| --- | --- | --- | --- | --- |
| (recorded at the phase's final checkpoint) | | | | |

The developer records this table at the final checkpoint (VPS access is
developer-only - see `38-RESEARCH.md`'s Environment Availability table).
