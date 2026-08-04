# ADS-B Aggregator Validation (Phase 1 spike)

Answers one question, empirically: can a free public ADS-B aggregator see
aircraft at the low-altitude, near-ground segment of Orly runway 3 — not
just cruise-altitude overflights? See `01-CONTEXT.md` (D-01 through D-04)
and `01-RESEARCH.md` (Pitfall 3) for why this is the actual test and not a
reading of general "Paris has dense feeder coverage" claims.

This track is deliberately unwired from the device firmware and the stub
server in `stub-server/`. Nothing here is polled by, or affects, the
wake/poll/backoff loop those tools exercise — it validates groundwork for
`PLANE-03`, which is delivered in Phase 2.

**Per D-03: this directory's findings are the source of truth on the
plane-detection data source. `PROJECT.md` and `REQUIREMENTS.md` still read
as if local ADS-B hardware is primary and the aggregator is a documented
fallback — that framing is only rewritten after `RESULTS.md`'s
`## Recommendation` is filled in, not before.** If you're reading this
before that decision has landed, treat `PROJECT.md`/`REQUIREMENTS.md` as
stale on this specific point.

## The three commands

### 1. `query_aggregator.py` — single live snapshot

```bash
python3 query_aggregator.py --provider both
python3 query_aggregator.py --provider adsbfi --json
```

One-shot query against adsb.fi and/or airplanes.live, geofenced to
`runway3.json`. Prints, per provider, every aircraft currently inside the
runway-3 bounding box, its altitude (or `ON GROUND` if the provider reports
the on-ground sentinel instead of a number), ground speed, and position.
Useful for a quick "is anything even in the box right now" check before
committing to a long sampling run.

Flags: `--provider {adsbfi,airplaneslive,both}` (default `both`),
`--geofence PATH` (default `runway3.json` next to this script),
`--json` (machine-readable output), `--timeout SECONDS` (default 15).

### 2. `sample_window.py` — unattended sampling over a real window

```bash
python3 sample_window.py --minutes 90 --interval 30
```

Repeatedly queries both providers over a time window and appends one JSON
Lines record per sample per provider to `samples/<run-start>_<provider>.jsonl`
(directory is gitignored — see below). Reuses `query_aggregator.py`'s
`query_provider()` and `filter_in_geofence()` directly, so the sampled
geofence is provably the one `query_aggregator.py` reports against. A
transient provider failure is written as an error record rather than
killing the run — a 90-minute window shouldn't die at minute 12.

Flags: `--minutes N` (default 90), `--interval SECONDS` (default 30, far
inside both providers' documented 1 req/sec limit), `--out DIR` (default
`samples/` next to this script), `--geofence PATH`, `--timeout SECONDS`.

### 3. `analyze_samples.py` — turn a run into a verdict

```bash
python3 analyze_samples.py --dir samples/
```

Reads every `*.jsonl` file in `--dir`, computes per-provider metrics
(distinct aircraft seen in the bbox, distinct aircraft at/below the
altitude ceiling, distinct on-ground aircraft, the best-tracked aircraft's
median/max position-update gap, lowest altitude observed, and the
two-provider overlap), and prints a markdown report ending in an explicit
PASS/FAIL against a threshold that is fixed in the script *before* any real
data is read:

- at least 6 distinct aircraft inside the bbox at or below 3000 ft,
- at least 1 aircraft carrying the on-ground sentinel,
- a median position-update gap of 15 seconds or less for the best-tracked
  aircraft.

That report is what gets transcribed into `RESULTS.md` — see below.

## `runway3.json`

The geofence every tool above shares: a `center`/`radius_nm` used as the
query origin, a tightened `bbox` around the runway-3 corridor (not the
whole airport, so an aircraft on a distant taxiway doesn't count), an
`alt_ceiling_ft` of 3000 (below which an aircraft is approaching, rolling
out, or on the ground rather than overflying), and the confirmed `runway`
identity/threshold coordinates. Every geographic claim in the file carries
a `source` field naming exactly where it came from and the date it was
checked — read those before trusting the box.

## Interpreting the verdict

A provider **passes** only if it clears all three threshold conditions
above over the sampled window — not "coverage looked decent" but
specific, pre-committed numbers. `RESULTS.md` records the numbers this
project actually observed, which window they came from, what the resulting
recommendation was, and what — if anything — that recommendation requires
doing next (`## Downstream Actions`, including whether the `D-02` local
RTL-SDR fallback needs to be invoked).

A single sampled window is evidence about *that window*, not a permanent
guarantee — `RESULTS.md`'s `## What This Does And Does Not Prove` section
is explicit about that boundary.

## Raw samples are not committed

`samples/` and `*.jsonl` are gitignored. A real sampling run writes
thousands of position records that don't belong in git history; the
metrics `analyze_samples.py` derives from them — which is what the project
decision actually rests on — are what's committed, in `RESULTS.md`.
