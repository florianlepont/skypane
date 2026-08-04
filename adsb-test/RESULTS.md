# ADS-B Aggregator Viability Results

Recorded verdict for the D-02 local-RTL-SDR-fallback decision (see
`01-CONTEXT.md` D-01 through D-04 and `01-RESEARCH.md` Pitfall 3). This is a
reading of a pre-committed test — the viability threshold in
`analyze_samples.py` was fixed before any real sampling data was read.

## Window Sampled

Two back-to-back windows on the same evening, same geofence
(`adsb-test/runway3.json`'s `bbox`, `alt_ceiling_ft: 3000`), sampled at a
30-second interval per provider:

| Window | UTC start | UTC end | Local start (CEST) | Local end (CEST) | Duration |
|---|---|---|---|---|---|
| 1 | 2026-08-04T17:20:11Z | 2026-08-04T18:20:10Z | 2026-08-04 19:20:11 | 2026-08-04 20:20:10 | ~60 min |
| 2 | 2026-08-04T19:53:40Z | 2026-08-04T20:25:38Z | 2026-08-04 21:53:40 | 2026-08-04 22:25:38 | ~32 min |
| **Combined** | | | | | **~92 min** |

Window 1 was the originally-planned continuous 90-minute run; it was cut
short at ~60 minutes when the executing session hit its usage limit
mid-run. Window 2 was sampled afterward, into the same output directory
(`adsb-test/samples/`), to bring the total real-traffic sampling time above
the plan's 90-minute floor, since `analyze_samples.py` groups records by
the `provider` field each JSONL line carries — not by filename — so
multiple runs into the same directory combine correctly for analysis. Both
windows fall on the same evening's active daytime/evening traffic (Orly is
operational into the evening; only the very early hours are subject to
curfew restrictions), so they are treated as one combined sample for the
verdict below rather than two independent trials.

Raw JSONL files (not committed, gitignored — see `adsb-test/.gitignore`):
- `20260804T172011Z_{adsbfi,airplaneslive}.jsonl` (Window 1)
- `20260804T195340Z_{adsbfi,airplaneslive}.jsonl`
- `20260804T200150Z_{adsbfi,airplaneslive}.jsonl`
- `20260804T200956Z_{adsbfi,airplaneslive}.jsonl`
- `20260804T201807Z_{adsbfi,airplaneslive}.jsonl` (Window 2, in three chunks)

Geofence used: `bbox = {lat_min: 48.712, lat_max: 48.734, lon_min: 2.325, lon_max: 2.435}`, `alt_ceiling_ft = 3000` (see `adsb-test/runway3.json` for full sourcing).

Reproduce the analysis: `python3 adsb-test/analyze_samples.py --dir adsb-test/samples/`

## Per-Provider Metrics

| Provider | Samples | Errors | Distinct hex in bbox | Distinct hex <=3000ft | Distinct hex on-ground | Best-tracked hex | Poll samples | Reconstructed updates | Median update gap (s) | Max update gap (s) | Lowest altitude (ft) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| adsbfi | 145 | 1 | 38 | 38 | 2 | 39de4f | 5 | 3 | 36.2s | 56.7s | 300ft |
| airplaneslive | 144 | 0 | 37 | 37 | 2 | 34134e | 7 | 5 | 22.4s | 69.8s | 225ft |

Overlap: seen by both adsbfi and airplaneslive: 37 hex. Seen only by adsbfi: 1 hex. Seen only by airplaneslive: 0 hex.

Update gaps are reconstructed from each provider's own `seen_pos` field
(seconds since the underlying feed last received a real position report for
that aircraft), not from this sampler's own 30-second polling interval —
otherwise the gap floor would just be whatever `--interval` was set to,
which measures nothing about the feed's own real-time behaviour.

## Viability Verdict

Threshold (fixed in `analyze_samples.py` before any real sampling data was
read): a provider passes when it observes **at least 6 distinct aircraft**
inside the bbox at or below the 3000ft ceiling, **at least 1 aircraft**
carrying the on-ground sentinel, and a **median position-update gap of 15
seconds or less** for its best-tracked aircraft.

### adsbfi
- distinct aircraft <=3000ft: **38** (threshold 6) -> **PASS**
- distinct on-ground aircraft: **2** (threshold 1) -> **PASS**
- median position-update gap for best-tracked aircraft (39de4f, 5 poll samples, 3 reconstructed updates): **36.2s** (threshold <=15.0s) -> **FAIL**
- **Overall: FAIL**

### airplaneslive
- distinct aircraft <=3000ft: **37** (threshold 6) -> **PASS**
- distinct on-ground aircraft: **2** (threshold 1) -> **PASS**
- median position-update gap for best-tracked aircraft (34134e, 7 poll samples, 5 reconstructed updates): **22.4s** (threshold <=15.0s) -> **FAIL**
- **Overall: FAIL**

Both providers clear the coverage conditions (distinct sub-ceiling aircraft,
on-ground detection) comfortably — this is not the "sees nothing near the
ground" failure mode Pitfall 3 warned about. Both fail only the update-
frequency condition: the best-tracked aircraft's reconstructed real-message
gap (36.2s adsbfi, 22.4s airplanes.live) exceeds the 15-second threshold.
Note the "best-tracked" aircraft is selected by which hex this sampler's own
polls saw most often (a proxy for "loitered longest in the geofence"), not
by which hex had the fastest underlying update rate — so this number
reflects the update cadence of whichever aircraft happened to linger in the
box across our polls, which for a fast final-approach/departure segment can
be a handful of position reports over a couple of minutes.

Compared to the first (60-minute) window alone, the additional ~32 minutes
changed the on-ground result from 0/0 to 2/2 for both providers — i.e. the
zero-on-ground reading from the first window alone was a window-size
artifact, not a coverage gap; touchdowns/rollouts on runway 3 are
infrequent enough that 60 minutes wasn't reliably long enough to catch one,
but ~92 minutes was.

## What This Does And Does Not Prove

This measures aggregator coverage **during the two sampled windows above,
at this specific geofence** (Orly runway 3's approach/rollout corridor,
07/25). It shows that, on this particular evening, both adsb.fi and
airplanes.live can and do see aircraft on runway 3 below 3000ft and on the
ground — the coverage question Pitfall 3 raised is answered affirmatively
for this window. It does **not** prove:
- that this coverage holds at other times of day (e.g. late night, when
  Orly's traffic and feeder activity both drop);
- that it holds under a different active-runway configuration (Orly
  rotates which runways are in use; a night with runway 3 not active for
  arrivals/departures would look very different);
- that the update-frequency shortfall observed here is representative
  rather than an artifact of which single aircraft happened to be
  "best-tracked" in each window;
- anything about the two providers' service reliability or terms of
  service over a longer time horizon than this test.

## Recommendation

PENDING - see Task 3
