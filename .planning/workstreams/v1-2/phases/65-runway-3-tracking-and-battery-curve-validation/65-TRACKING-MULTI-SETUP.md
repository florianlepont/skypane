# Phase 65: TRK-02 multi-airport setup

**Date:** 2026-11-15 | **Plan:** 65-09 | **Status:** scratch fleet created, smoke cycle done, live frame unchanged

Evidence: geometry computed from `server/data/airports_fr.json` (catalogue snapshot 2026-10-31) with a throw-away script kept in the scratchpad (`p65_09/geom.py`, not committed). Nothing under server/, stub-server/, companion/, deploy/ or firmware/ changed.

## Owner decision (D-11)

Given in chat on 2026-11-15 and recorded as D-11 in 65-CONTEXT.md. Quoted: "three airports instead of two, one simple case and two stress cases: Nantes LFRS (single runway, the simple case), Lyon LFLL (parallel runways, stress 1), Paris-Charles de Gaulle LFPG (four runways, two parallel pairs, stress 2)." One session per airport, at least 3 arrivals and 3 departures per runway or airport, order Nantes, Lyon, Roissy. "At least two other airports" in TRK-02 is still met. Because the owner named the airports, the short list of the plan (Task 1) and the decision checkpoint (Task 2) were not needed; the table below holds the geometry of the three chosen airports and Orly.

The owner picked every runway of LFLL and LFPG; one simulated device per runway so the sessions can show which of two parallel runways the detection chose. All devices of one airport share one zone, so the extra devices cost no extra provider request.

## Geometry (catalogue, computed)

| ICAO | IATA | Name | Runway | Length m | Bearing | Corridor half-width m | Legacy id | Display id | Zone centre | Radius NM | Corridor box (lat min..max, lon min..max) | Owner can watch it on Flightradar24 |
|------|------|------|--------|---------:|--------:|------:|-----------|------------|-------------|----------:|----|----|
| LFRS | NTE | Nantes Atlantique | 03/21 | 2907 | 27.34 | 500.0 | none | LFRS:03/21 | 47.1532, -1.6107 | 5.0 | 47.11959..47.186811, -1.640577..-1.580863 | |
| LFLL | LYS | Lyon Saint-Exupery | 17L/35R | 2670 | 175.14 | 174.3 | none | LFLL:17L/35R | 45.726, 5.0901 | 5.0 | 45.688489..45.757411, 5.08691..5.09974 | |
| LFLL | LYS | Lyon Saint-Exupery | 17R/35L | 4011 | 175.15 | 174.3 | none | LFLL:17R/35L | 45.726, 5.0901 | 5.0 | 45.688191..45.769111, 5.080987..5.095253 | |
| LFPG | CDG | Paris-Charles de Gaulle | 08L/26R | 4209 | 85.28 | 192.2 | none | LFPG:08L/26R | 49.009, 2.5541 | 5.0 | 48.99214..49.002359, 2.51841..2.64451 | |
| LFPG | CDG | Paris-Charles de Gaulle | 08R/26L | 2695 | 85.25 | 192.2 | none | LFPG:08R/26L | 49.009, 2.5541 | 5.0 | 48.989325..48.998476, 2.531332..2.636758 | |
| LFPG | CDG | Paris-Charles de Gaulle | 09L/27R | 2695 | 85.25 | 191.7 | none | LFPG:09L/27R | 49.009, 2.5541 | 5.0 | 49.021129..49.03027, 2.490541..2.596039 | |
| LFPG | CDG | Paris-Charles de Gaulle | 09R/27L | 4192 | 85.25 | 191.7 | none | LFPG:09R/27L | 49.009, 2.5541 | 5.0 | 49.017032..49.027268, 2.478713..2.604637 | |
| LFPO | ORY | Paris-Orly | 06/24 | 3647 | 61.75 | 500.0 | 06-24 | LFPO:06/24 | 48.7233, 2.3794 | 5.0 | 48.712..48.734, 2.325..2.435 (frozen legacy box) | |
| LFPO | ORY | Paris-Orly | 02/20 | 2403 | 18.28 | 500.0 | 02-20 | LFPO:02/20 | 48.7233, 2.3794 | 5.0 | 48.712..48.734, 2.325..2.435 (frozen legacy box) | |

For reference, Orly runway 3 is LFPO 07/25 (3315 m, bearing 74.39, legacy id "3") and is the live frame's runway; it has no scratch device. Corridor extension is `EXTENSION_M` (detection.py) beyond each threshold; zone radius is 5.0 NM for every catalogue runway; altitude ceiling 3000 ft.

Runway centreline spacing (distance of the midpoints across the runway axis, from the thresholds):

| Airport | Pair | Bearing difference | Lateral spacing m | Offset along the axis m |
|---------|------|-------------------:|------------------:|------------------------:|
| LFLL | 17L/35R and 17R/35L | 0.0 | 349 | 667 |
| LFPG | 08L/26R and 08R/26L (south pair) | 0.0 | 387 | 157 |
| LFPG | 09L/27R and 09R/27L (north pair) | 0.0 | 384 | 150 |
| LFPG | south pair to north pair (08L-09L, 08L-09R, 08R-09L, 08R-09R) | 0.0 | 3386, 3002, 3774, 3390 | 2518 to 2824 |
| LFPO | 02/20 and 06/24 | 43.5 | 3001 | 991 |
| LFPO | 07/25 and 02/20 | 56.1 | 47 | 494 |
| LFPO | 07/25 and 06/24 | 12.6 | 1870 | 2457 |

Reading: the corridors of a parallel pair are as wide as the spacing, so they almost touch. Lyon: spacing 349 m against 2 x 174.3 = 348.6 m (gap about 0.4 m). Roissy south pair: 387 m against 2 x 192.2 = 384.4 m (gap about 2.6 m); north pair: 384 m against 2 x 191.7 = 383.4 m (gap about 0.6 m); the two Roissy pairs are 3 km or more apart. Both airports are the stress cases the owner wanted. Nantes has a single runway, so runway confusion cannot occur there.

## Scratch fleet

Scratch root: `/tmp/claude-0/-home-user-skypane/e7b2962d-137b-5976-bbb9-b2fc84099ae6/scratchpad/p65_09/root` (outside the repository, not a production path, carries the `.multisite-scratch` marker). Created with `scripts/multi_site_setup.py` (hardware `sim-ee02-clone`, the simulation flag only inside the runner process). The root also holds a held live row (display off) so it joins no zone.

| Device id | Name | Airport | Runway | Legacy or display id | Zone key | State directory |
|-----------|------|---------|--------|----------------------|----------|-----------------|
| d_563098f4 | ORY-0624 | LFPO | 06/24 | 06-24 | 48.7233\|2.3794\|5.0 | devices/d_563098f4 |
| d_a08d342a | ORY-0220 | LFPO | 02/20 | 02-20 | 48.7233\|2.3794\|5.0 | devices/d_a08d342a |
| d_cd843e41 | NTE-0321 | LFRS | 03/21 | LFRS:03/21 | 47.1532\|-1.6107\|5.0 | devices/d_cd843e41 |
| d_fbcee383 | LYS-17L | LFLL | 17L/35R | LFLL:17L/35R | 45.726\|5.0901\|5.0 | devices/d_fbcee383 |
| d_255a9754 | LYS-17R | LFLL | 17R/35L | LFLL:17R/35L | 45.726\|5.0901\|5.0 | devices/d_255a9754 |
| d_8213849d | CDG-08L | LFPG | 08L/26R | LFPG:08L/26R | 49.009\|2.5541\|5.0 | devices/d_8213849d |
| d_f7b8d7e9 | CDG-08R | LFPG | 08R/26L | LFPG:08R/26L | 49.009\|2.5541\|5.0 | devices/d_f7b8d7e9 |
| d_ecf8e497 | CDG-09L | LFPG | 09L/27R | LFPG:09L/27R | 49.009\|2.5541\|5.0 | devices/d_ecf8e497 |
| d_b06bb65a | CDG-09R | LFPG | 09R/27L | LFPG:09R/27L | 49.009\|2.5541\|5.0 | devices/d_b06bb65a |

Four distinct zones (LFPO shared by two devices, LFLL by two, LFPG by four, LFRS by one).

## Smoke cycle

Request rule for this plan: one cycle, three real zone fetches (the three new airports), nothing more. A zone fetch queries adsb.fi and adsb.lol in turn, so three zones cost six provider requests. Orly is not one of the three, so it was checked without the network.

1. **Planning check on the full root, fake fetcher, no network** (copy of the root, `p65_09/fake_root`): `cycle 1 ... ok=9 held=1 busy=0 failed=0 deferred=0 skipped=0 zones=4 requests=4`. Fetch centres: (45.726, 5.0901, 5.0), (47.1532, -1.6107, 5.0), (48.7233, 2.3794, 5.0), (49.009, 2.5541, 5.0). Each of the nine devices was run with its own state directory and the `sim-ee02-clone` profile; the two Orly devices shared one fetch. The held live row was held, so it cost no request.
2. **Live smoke on a separate scratch root with one device per new airport** (`p65_09/smoke_live`: NTE-0321 d_d4c57bd6, LYS-17L d_a4bc1896, CDG-08L d_fef8b31a), real fetcher, real `run_once`, one cycle at 2026-11-15T22:02:36Z: `ok=3 held=1 busy=0 failed=0 deferred=0 skipped=0 zones=3 requests=6`, 6.8 s wall time. Each device reported its own `tracked_runway` (`LFRS:03/21`, `LFLL:17L/35R`, `LFPG:08L/26R`); the held row is the root's live row.

| Zone | adsb.fi aircraft | adsb.lol aircraft | Failed providers |
|------|-----------------:|------------------:|------------------|
| 47.1532\|-1.6107\|5.0 (LFRS) | 1 | 1 | none |
| 45.726\|5.0901\|5.0 (LFLL) | 2 | 2 | none |
| 49.009\|2.5541\|5.0 (LFPG) | 0 | 0 | none |

Both providers answered in all three zones from this sandbox. All three devices ended with `render_state=empty` (no aircraft in a runway corridor at that moment); no adsbdb lookup was needed. Every device wrote only under its own directory in the smoke root (device_config, history.db, panel.bin, poll_state.json, gallery); the payloads are in `smoke_live/payloads/`. The main root (`root`) was not polled live: the live fetch path will be exercised at the first session. Data from adsb.fi (https://adsb.fi) per COMPLIANCE.md.

## Live frame comparison (T-65-38)

`GET https://skypane.algernon.is/api/export/status` fetched once after the smoke cycle (HTTP 200, no credential stored). The `device` object equals the `device` object of `data/status_baseline_trk02.json` exactly: tracked_runway "3", wake_interval_s 300, display_enabled true, quiet hours 23:30 to 06:00, timezone Europe/Paris. The two documents have the same top-level keys. Result: unchanged.

## Not touched

The live frame, the second frame and production state; no production request other than that single read-only status GET.
