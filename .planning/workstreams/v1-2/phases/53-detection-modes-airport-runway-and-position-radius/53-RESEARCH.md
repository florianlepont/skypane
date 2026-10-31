# Phase 53: Detection Modes (Airport/Runway and Position/Radius) - Research

**Researched:** 2026-10-31
**Domain:** Pure-Python geometry on a committed OurAirports catalogue, per-device zone resolution in the Phase 52 fleet cycle, stdlib companion page
**Confidence:** HIGH on measurements and code seams (all re-run on the repo and the 2026-10-31 dump), MEDIUM on the three policy numbers marked `[ASSUMED]` (parallel threshold, half-width floor, France box)

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Two per-device detection modes: (1) airport + runway from a committed catalogue built from OurAirports; (2) aircraft around the device's position. The catalogue is produced by a reproducible, committed script and never downloaded at run time.
- **D-02:** Reuse the Phase 52 zone mechanism and budget; adsb.fi stays at 1 req/s in total and is cited. OurAirports is already on the credits page (`companion/credits.json`, public domain, courtesy credit): verified.
- **D-03:** No production deploy; code, tests and CI only.
- **D-04:** Include every French aerodrome runway row from OurAirports (`LF*` and overseas rows present in the dump) with both thresholds and `closed=0`. Measured on the 2026-10-31 dump: 548 `LF*` rows, 288 with both thresholds, 11 closed. Rows without both thresholds are absent. Real designators kept (e.g. `08L/26R`).
- **D-05:** A catalogue runway is the full pair, both directions (departures and arrivals either way), like Orly 3 (07/25) today.
- **D-06:** Image tag for runway mode uses the IATA code when the airport has one, else the ICAO ident, then the real designator (e.g. `CDG · 08L/26R`). Legacy Orly ids keep their exact current tag text.
- **D-07:** The corridor half-width is `min(500 m, half the distance to the nearest parallel runway of the same airport)`; the default 500 m, 2500 m extension, 30 deg axis tolerance and 75 m ground half-width are unchanged. Orly keeps exactly 500 m. Tests cover LFPG (08L/26R vs 08R/26L, 09L/27R vs 09R/27L) and at least one other parallel-runway airport.
- **D-08 (owner chose switching):** The live Orly frame moves onto the generic catalogue logic in this phase, with one condition kept from the owner's standing constraint: its observable behaviour (selected aircraft, tag text, image, interval) must not change. This holds only if the replay of recorded Orly traffic through the new logic gives decisions strictly identical to the hand-tuned runway-3 geofence, and `test_phase47_freeze.py` stays green. If the replay is not identical, the switch is not made and the frame stays on the existing geofence; the owner is told. The legacy `tracked_runway` ids (`3`, `06-24`, `02-20`) stay valid and map to the catalogue's LFPO rows (expand-only).
- **D-09:** Nothing is deployed; the switch ships in code with the deploy decision left to the owner.
- **D-10:** The centre is the device's location (Phase 48 `locations`: name, latitude, longitude, timezone) plus a radius stored with the device. No free-form coordinates.
- **D-11:** Shown aircraft: airborne only, altitude at or below 10,000 ft, lowest first (existing selection ordering). Radius bounds 2 to 15 NM.
- **D-12:** Coordinates sent to third parties are rounded to 2 decimals (about 1 km); the zone centre received by Phase 52 is the rounded position, so neighbours share zones naturally. Runway mode does not round (public airport coordinates).
- **D-13:** Country bounds: a bounding box around metropolitan France including Corsica; positions outside are refused with a clear message, in the setting form and again server side.
- **D-14:** A new dedicated page for detection settings, not the existing Runway card. It is a new route and must be added to the route x role x owner matrix (default-deny, per-device protected route of Phases 51/54); wrong role or other owner's device answers 404.
- **D-15:** Airport selection by a search field (ICAO, IATA, name, city) filtering the committed catalogue, then one card per runway with the real designator and orientation. The form works without JavaScript. All strings bilingual in `companion/i18n_fr/`; load `Skill("sketch-findings-skypane")` before any interface work.

### Claude's Discretion
Catalogue JSON shape and script name, module names, storage keys in `device_config.json`, how legacy ids map, how replay fixtures are recorded, plan split, empty-state texts, exact orientation display.

### Deferred Ideas (OUT OF SCOPE)
Free-form coordinates per device; single-direction runway following; IATA-less aerodrome naming refinements; overseas bounds for position mode.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | A device can be set to an airport and runway chosen from a committed France catalogue built from OurAirports (rows without both thresholds dropped), with real designators. | Section 1 (dump measurements, build pipeline and validations), Section 6 (storage), Section 7 (page). 340 runways / 272 airports pass the proposed filters. |
| DET-02 | Recorded Orly traffic replayed through the new runway logic gives the same decisions as the hand-tuned runway-3 geofence; at least one parallel-runway airport is tested. | Sections 2, 3, 4: thresholds are bit-identical after 6-decimal rounding; the legacy bbox must be carried as an override or identity fails (measured); LFPG/LFMN/LFML/LFBO/LFLL half-widths computed. |
| DET-03 | A device can be set to show aircraft around a position within a bounded radius inside France, and coordinates sent to third parties are rounded. | Section 5 (zone, selection, rounding choke point, France box), Section 6 (zone key interaction), Section 10 (open questions on level-flight labelling). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs and commit messages are in English; companion UI stays bilingual (`companion/i18n_fr/`).
- Comments say what and why only; **no plan, ticket, decision, review or phase IDs in comments** (`scripts/check_comment_history.py check` enforces it in CI; patterns include `D-NN`, `Phase NN`, `CFG-NN`, `.planning/`).
- Stack is stdlib + Pillow + requests only (`server/requirements.txt`, hash-locked). **No new dependency.** Production Python is 3.14; the local venv is 3.13.
- Tests: pytest + xdist + cov (`./scripts/run-all-tests.sh`, coverage floor 93), pytest-socket non-loopback guard, behaviour-over-source rule for companion tests (never read `.planning/` or production `.py/.js/.css/.html` as text), ruff, mypy (module list in `[tool.mypy] files`), function-size gate (max 80 lines over `server stub-server`; companion has the same ceiling through `companion/test_structure_guards.py`), companion browser tests on Playwright.
- GSD workflow: no direct repo edits outside a GSD command. Phase 47 files and `hardware/` untouched; `stub-server/test_phase47_freeze.py` must stay green.
- UI work must load `Skill("sketch-findings-skypane")` first (read; key points in Section 7).

## Summary

The generic runway logic is already in `server/plane/detect.py`: `runway_axis`, `corridor_params`, `filter_in_geofence`, `runway_candidates`, `select_from_provider_results` all consume a **geofence-shaped dict**. The lowest-risk design is therefore to **generate a geofence-shaped document per device** (from the committed catalogue for runway mode, from the device location for position mode) and feed it to the same pure functions, so legacy and generic paths differ only in the *data*. The data, not the code, is what the replay must prove identical.

Three measured facts shape the plan. (1) OurAirports LFPO rows, rounded to 6 decimals, reproduce the hand-tuned thresholds of `adsb-test/runway3.json` **bit for bit** (the raw CSV values carry float32 noise: 273 of 361 in-scope rows have more than 6 decimals, up to 20). (2) A purely generic bounding box does **not** reproduce the hand-tuned bbox: the legacy bbox clips the corridor corners, and a sweep of 963,603 grid cells found 13,232 differing decisions (first difference at only 40 m cross-track, at the far corridor tip). So strict identity (D-08) needs the Orly ids to carry the legacy `bbox`/`center`/`radius_nm`/`alt_ceiling_ft` as a frozen override, with the generic derivation used for every other runway. (3) The D-07 rule collapses to `0` m for two collinear duplicate rows at LFPK, and `detect.corridor_params` silently replaces a non-positive half-width by the 500 m default, so a floor is mandatory (proposed 50 m, owner to confirm).

Position mode needs one new pure candidate function (circle, airborne, <= 10,000 ft) plus a dispatch in `runway_candidates`; ordering (`selection_sort_key`), cross-provider corroboration and normalisation are reused. The fleet cycle needs a **per-device resolver** and, more importantly, `poll_cycle.detect_flight` must stop reading the shared geofence path and resolve the device's own spec (today `run_device` passes the same `geofence_path` to every device, so a per-device zone alone would fetch the right zone and then select against the Orly geofence). The new page is `ADMIN_ONLY`-consistent with how `tracked_runway` is treated today (recommended, see Open Questions), adds two matrix rows, bumps a hard-coded route count, and requires regenerating the committed render baseline.

**Primary recommendation:** Build `server/airports.py` (stdlib leaf: catalogue loader) + `scripts/build_airports.py` (offline, committed raw subset, sha256 pin) + `server/detection.py` (pure `spec_for(device_cfg)` producing zone + geofence-shaped doc + display ids), keep legacy Orly ids on the generic path via a frozen compat override guarded by an env/constant kill switch, and prove D-08 with an exhaustive sweep plus the 14 recorded records before anything else is built on top.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Catalogue build (CSV to JSON) | Dev-time script (`scripts/`) | Committed data (`server/data/`) | Never at run time (D-01); CI rebuilds and diffs from the committed raw subset |
| Catalogue load and lookup | API/Backend (stdlib leaf `server/airports.py`) | Companion (search) | Immutable, 63 KB, `lru_cache`d per process |
| Corridor half-width (parallel rule) | Build time (stored per runway) | Backend (reads value) | Computed once offline; runtime stays data-driven and testable |
| Detection spec (zone + geofence doc) | Backend (`server/detection.py`) | Fleet cycle, poll cycle | One function shared by the resolver and by `poll_cycle`, so they cannot disagree |
| Zone fetch and budget | Backend (`zone_fetch`, ledger) | - | Unchanged; zone key is the exact `(lat, lon, radius)` triple |
| Candidate gating | Backend (`detect.py` pure functions) | - | Runway: existing corridor gates; position: new circle/altitude gate |
| Coordinate rounding | Backend, at spec construction | Test guard on provider URLs | Single choke point before any `Zone` exists |
| Tag / empty heading text | Backend render (`style.runway_tag_text`) | `detection` display ids | Panel copy stays English and locked |
| Settings page, search, validation | Frontend server (companion handler) | Backend validation module | Server-rendered, no-JS forms; validation re-run server side |
| Per-device settings storage | `device_config.json` (per device dir) | `fleet.db` `locations` (centre only) | Expand-only; preferences stay in the JSON document |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`csv`, `json`, `math`, `hashlib`, `functools.lru_cache`, `argparse`) | 3.14 prod / 3.13 local | Build script, loader, geometry | Project rule: stdlib + Pillow + requests only |
| Existing `server/plane/detect.py` functions | repo | Corridor and track gates, selection, corroboration | Already per-runway and parameterised by a geofence dict |

### Supporting
None. **No package is added, so there is no new `pip`/`npm` install and nothing to run slopcheck on.**

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Geofence-shaped dict per device | Rewrite `detect` around a new `Detection` class | Rewrite risks the hard-won false-positive fixes (ground gate, hex tie-break); dict reuse keeps the replay meaningful |
| Catalogue JSON | SQLite table in `fleet.db` | JSON is diffable, reviewable in a PR and needs no migration; the previous release ignores it |
| Raw CSV subset committed | Download in CI | CI must stay offline-deterministic (pytest-socket guard); a nightly-changing source breaks reproducibility |

**Installation:** none.

**Version verification:** not applicable (no packages). Data snapshot, not a version: see Section 1.

## Package Legitimacy Audit

No external packages are recommended; the section is intentionally empty. Packages removed due to slopcheck [SLOP]: none. Packages flagged [SUS]: none. The OurAirports CSV is *data*, pinned by sha256 (Section 1).

## Architecture Patterns

### System Architecture Diagram

```
 dev time (manual, reviewed in a PR)
   OurAirports airports.csv + runways.csv (full dump, nightly)
        | scripts/build_airports.py --refresh   (filters French scope, writes subset + SOURCE pin)
        v
   scripts/data/ourairports-fr-{airports,runways}.csv   (committed raw subset, ~127 KB)
        | scripts/build_airports.py                    (offline, deterministic, validations, parallel rule)
        v
   server/data/airports_fr.json                         (committed catalogue, ~63 KB)

 every 30 s (systemd oneshot)
   poll_loop -> run_fleet
     load_fleet(fleet.db) -> runnable_devices (7-day skip, live exempt)
     per device: device_config.load_device_config(state_dir)
        -> detection.spec_for(cfg, location)  ----+--> legacy id (3 / 06-24 / 02-20) ? frozen compat doc
                                                  +--> runway mode ? airports.json row -> geofence doc
                                                  +--> position mode ? rounded centre, radius -> doc
        -> (Zone, geofence doc)   [resolver]      invalid/corrupt config -> legacy Orly "3" (fail-safe)
     plan_zones: hold? skip : group by Zone.key  (exact pair, Phase 52 D-12)
     per zone (live first, oldest-served next): zone_fetch.fetch_zone  (ledger: 1 req / 1.1 s)
        raw lists per provider (adsb.fi, adsb.lol)
     per device in zone: poll_cycle.run_once(zone_fetch=..., ...)
        detect_flight: spec_for(ctx.device_cfg)  [NOT the shared geofence path]
          runway mode  -> runway_candidates (corridor + track + ground gate)
          position mode-> position_candidates (circle, airborne, <= 10,000 ft)
          select_from_provider_results (candidate-set intersection, hex tie-break)
        -> infer state -> enrich (adsbdb: callsign only) -> render(tag/heading from display id)
```

### Recommended Project Structure
```
scripts/
├── build_airports.py                  # CLI: build (offline) and --refresh (filter a full dump)
└── data/
    ├── ourairports-fr-airports.csv    # committed raw subset (577 airports)
    ├── ourairports-fr-runways.csv     # committed raw subset (747 rows)
    └── ourairports-source.json        # snapshot date, URLs, sha256 of full + subset files, licence text
server/
├── airports.py                        # stdlib leaf: load_catalogue(), find(), search(); typed (mypy list)
├── detection.py                       # pure: spec_for(), bounds, rounding, display ids; typed
└── data/airports_fr.json              # committed catalogue
companion/
├── pages/detection_page.py            # render() + handle_post()
├── i18n_fr/detection.py               # French strings (area "detection")
└── test_detection_page.py             # HTTP behaviour tests
```
`server/device_config.py` stays a leaf (docstring: stdlib + `atomic_io`, `device_policy`, `themes` only). Validation that needs the catalogue lives in `server/detection.py`; `device_config` stores and normalises *shape* only, and `detection` validates *meaning*.

### Pattern 1: Geofence-shaped document per device
**What:** `spec_for(device_cfg, location)` returns a frozen record `(zone, geofence_doc, display_id, mode)`. `geofence_doc` has exactly the keys `detect.py` reads (listed in Section 3).
**When to use:** the resolver and `poll_cycle.detect_flight` both call it, so the zone fetched is the zone selected from.
**Example:**
```python
# Shape only; names are the planner's choice.
doc = {
    "center": {"lat": 48.7233, "lon": 2.3794},   # runway mode: ARP rounded to 4 dp, or the frozen legacy centre
    "radius_nm": 5.0,
    "bbox": {"lat_min": ..., "lat_max": ..., "lon_min": ..., "lon_max": ...},
    "alt_ceiling_ft": 3000,
    "runways": {display_id: {
        "runway": {"thresholds": [{"lat": ..., "lon": ...}, {"lat": ..., "lon": ...}]},
        "corridor": {"half_width_m": 500.0, "extension_m": 2500, "axis_tolerance_deg": 30},
    }},
}
# Source: server/plane/detect.py runway_axis / corridor_params / filter_in_geofence
```

### Pattern 2: Display id as the single string render and history already carry
`ctx.tracked_runway_id` flows into `render.build_canvas(runway_id=...)`, `runway_events.tracked_runway` (TEXT) and `cycle_result`. Keep it a string: legacy ids unchanged (`"3"`, `"06-24"`, `"02-20"`), runway mode `"LFPG:08L/26R"`, position mode `"position:5"`. `style.runway_tag_text` / `empty_heading_text` currently call `normalise_runway_id`, which **degrades any unknown id to Orly "3"**, so they must learn the new ids (delegate to `detection`), otherwise a CDG device would render `ORY · RWY 3`.

### Anti-Patterns to Avoid
- **Computing the bbox generically for the Orly ids** (breaks strict identity, measured below).
- **Letting a missing runway key reach `detect`**: `_effective_runway_id` falls back to `"3"`, whose block is absent from a generated doc, so `runway_axis` returns `None` and `filter_in_geofence` degrades to **bbox-only** selection. The generator must always populate `runways[display_id]`, and a test must assert `detect._effective_runway_id(doc, id) == id` for every catalogue runway.
- **Storing a half-width of 0 or negative**: `_positive()` silently substitutes 500.
- **Reading catalogue meaning inside `device_config.py`** (leaf-module rule).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Corridor/track/ground gating for catalogue runways | A second gate implementation | `detect.filter_in_geofence` on a generated doc | The false-positive fixes (pavement gate, hex tie-break, intersection corroboration) are encoded and fixture-tested |
| One-aircraft selection and corroboration | New ordering for position mode | `selection_sort_key`, `select_from_provider_results`, `_normalise_selection` | D-11 says "existing selection ordering"; same `hex` tie-break keeps feeds consistent |
| Zone sharing | New grouping | `fleet_zones.Zone.key` exact pair | Phase 52 D-12; quantisation is explicitly refused |
| Atomic per-device config write | New file format | `device_config.save_device_config` (flock + atomic_write) | Concurrency and rollback behaviour already tested |
| CSV parsing | Hand-split lines | stdlib `csv` with `newline=''` | Names contain commas and quotes (190 non-ASCII names in the subset) |
| i18n | Inline French | `i18n.msg(id, english)` + `companion/i18n_fr/detection.py` | `test_i18n` enforces id shape and French completeness |
| Search | JS filtering | Server-side substring match behind a GET form | Required to work without JavaScript (D-15) |

**Key insight:** the correctness risk of this phase is in *data* (thresholds, bbox, half-width, zone), not in algorithms. Every algorithm already exists and is fixture-tested; reuse it and test the data.

## Common Pitfalls

### Pitfall 1: Generic bbox changes Orly decisions
**What goes wrong:** deriving the bbox from the corridor rectangle (the natural generic choice) differs from the hand-tuned `lat 48.712..48.734, lon 2.325..2.435`. Measured: generic bbox is `lat 48.70904..48.73776, lon 2.32397..2.43669`; over a 963,603-cell sweep (positions x tracks 74.4/254.4 x airborne/ground), **13,232 cells differ**; the smallest cross-track offset of a corridor point outside the legacy bbox is **40 m, at along-track 5815 m (the far corridor tip)**. The 14 recorded fixture records do not expose it (0 differences for ids 3, 06-24, 02-20), which is exactly why a fixture-only replay would wrongly pass.
**Why it happens:** the legacy bbox contains the corridor centreline (ends sit 8-12 m inside the box edge) but clips the lateral corners.
**How to avoid:** Orly ids carry a frozen `bbox`, `center`, `radius_nm`, `alt_ceiling_ft` taken from `runway3.json` (drift-checked by a test), and the replay includes the exhaustive sweep. Generic runways use the corridor-rectangle bbox (no clipping).
**Warning signs:** a replay that only uses committed fixtures; a bbox derived "from thresholds plus margin" for the Orly ids.

### Pitfall 2: Raw CSV coordinates are float32 noise
**What goes wrong:** `48.719398498535156` vs the legacy `48.719398`; bearings differ in the 5th decimal (74.4085 vs 74.4100) and lengths by 1 cm, enough to flip a boundary decision in a sweep.
**How to avoid:** round all stored coordinates to **6 decimals** at build time (0.11 m). This makes LFPO 07/25, 06/24 and 02/20 thresholds equal the legacy values exactly (verified for 07/25; the 06/24 and 02/20 CSV values round to the legacy 6-decimal numbers as well).

### Pitfall 3: Half-width of 0 widens to 500
Two LFPK rows (`09/27` vs `09C/27C`, 0-3 m apart, collinear duplicates) yield `min(500, 0/2) = 0`; `corridor_params` falls back to 500. Apply a floor (Section 2) and make the build fail on any stored value `<= 0`.

### Pitfall 4: Shared geofence path in `run_device`
`fleet_cycle._FleetRun.run_device` passes `geofence=self.geofence_path` to every device and `poll_cycle.detect_flight` runs `detect.load_geofence(ctx.geofence)`. A per-device resolver alone would fetch the right zone and then gate against Orly. `detect_flight` and `_fetch_standalone` must use `detection.spec_for(ctx.device_cfg, ...)`; the `geofence` argument remains only as the legacy-document path for Orly.

### Pitfall 5: `ZoneGroup.geofence` is the first device's
`plan_zones` stores the first device's geofence in the group. Two devices in one airport zone but on different runways share a zone (good) and must **not** share the geofence. Keep the group's geofence unused for selection (it is today) and add a test with two devices, same airport, different runways.

### Pitfall 6: `type = "closed"` in the dump, not `closed_airport`
The data dictionary says `closed_airport`; the 2026-10-31 dump uses `closed` (13,650 rows). Seven French airports of type `closed` (old air bases such as FR-1238) still have runway rows with `closed=0`. Filter on both spellings.

### Pitfall 7: Non-ICAO idents and non-standard designators
`FR-0158`, `GF-0001`, `NC-0006` are internal ids; `LFNC 16G/34G` (glider grass) and `LFPG 08H/26H` (442 m grass) fail the designator pattern; one row is water (`FR-0182`). See the filter below.

### Pitfall 8: Position-mode state label for level traffic
`runway_config.infer_from_flight` keeps the vertical-rate deadband (+-200 fpm). A first-ever level aircraft renders the **empty** screen, and a later level aircraft inherits the previous label. For a runway this is correct; for "aircraft around a position" cruising traffic is common. See Open Question 3.

### Pitfall 9: Hard-coded counts and committed baselines
`companion/test_route_table.py` asserts `len(owner) == 24`; `_GATED_ROUTES` indexes the committed `companion/testdata/render_baseline.json` by `"METHOD path"`. Adding routes without regenerating it (`python test-support/companion_render_snapshot.py --write`) fails `test_every_gated_route_redirects_an_anonymous_request` with a `KeyError`.

### Pitfall 10: Rollback hazard of the previous release
`load_device_config` returns only registry keys and `save_device_config` rewrites the file from them, so an **old-release save drops the new `detection` key**. The previous release still *runs* (it ignores the key and reads `tracked_runway`), which is the expand-only bar, but a rollback followed by any companion save silently resets a catalogue/position device to its legacy runway. Document it in the plan; do not engineer around it.

## 1. OurAirports: licence, columns, French coverage, data quality

**Licence [CITED: ourairports.com/data, fetched 2026-10-31]:** "All data is released to the Public Domain, and comes with no guarantee of accuracy or fitness for use." Attribution is requested, not required. The CSV dump is regenerated nightly. Column semantics [CITED: ourairports.com/help/data-dictionary.html]: `*_heading_degT` is **true**, `*_displaced_threshold_ft` is the displaced length, `length_ft` is the "full runway surface (including displaced thresholds, overrun areas, etc)", `lighted`/`closed` are 1/0, `surface` is **not** a controlled vocabulary, every row is "a runway, helipad, or waterway".

**Snapshot used here (untrusted data, read with `python3 -I`):** `airports.csv` 12,754,691 bytes, sha256 `6c600b7821829c2bd672c97b0c1e25b51a12e1e281fbd6fb1b698156b17d6acb`; `runways.csv` 3,972,528 bytes, sha256 `64103ae9a363538774f43c9b7b510962ac8f1d89ec976be2c91829622d6edd67`; 86,322 airports, 48,388 runway rows. [VERIFIED: local measurement]

**Scope funnel (measured):**

| Step | Rows |
|------|-----:|
| Runway rows, whole world | 48,388 |
| French territories (`iso_country` in FR, GF, GP, MQ, RE, YT, PM, BL, MF, PF, NC, WF, TF) or `LF*` ident (excl. CN `LFQ`) | 747 |
| Airport ident shaped like a code, `^[A-Z]{4}$` (drops internal ids `FR-0158`, `GF-0001`, `NC-0006` ...) | 617 |
| Both threshold coordinate pairs present | 346 |
| `closed = 0` | 342 |
| Airport type small / medium / large (drops `closed`, `heliport`, `seaplane_base`, `balloonport`) | 342 |
| Both designators match `^(0[1-9]\|[12]\d\|3[0-6])[LRC]?$` (drops `LFNC 16G/34G`, `LFPG 08H/26H`) | 340 |
| Not `WATER` | 340 |
| Add `LF50`, `LF51` (non-ICAO local codes but `LF*`, so in scope per D-04; widen the ident pattern to `^[A-Z]{2}[A-Z0-9]{2}$`) | 342 |
| Geometry validations below (drops `NTGY 18/36`, `TFFA 09/27`) | **340** |

Result: about **340 runways at 272 airports** (283 `LF*` runways, 57 overseas after geometry validation: NT 31, NW 10, TF 7, SO 5, FM 4, NL 2 before the two rejects). This reconciles with D-04 (`LF*`: 548 rows, 288 with both thresholds, 3 of those closed, 285 open, minus the two non-standard designators = 283). The catalogue serialises to about 63 KB compact JSON (274 airports before geometry rejects); 55 airports have more than one runway; 173 of 272 have an IATA code (so 99 tags use the ICAO ident, D-06); 14 have an empty municipality; no duplicate IATA within the catalogue.

**Overseas prefixes confirmed present:** TFFR (Pointe-a-Pitre), TFFF (Fort-de-France), FMEE (Reunion), FMCZ (Mayotte), NWWW (Noumea), NTAA (Tahiti), SOCA (Cayenne), NLWW (Wallis). They sit under non-FR `iso_country` values, so the filter must be the territory set above, not `iso_country == 'FR'` (which only holds metropolitan `LF*` plus the `FR-nnnn` internal ids).

**LFPO rows (as stored):** `02/20` 7874 ft x 197 ft CON, hdg 18/198; `06/24` 11975 x 148 ASP, hdg 62/242, `le_displaced` blank, he 984 ft; `07/25` 10892 x 148 CON, hdg 74/254, he displaced 1427 ft; all `closed=0`. LFPO is `ORY`, ARP 48.729499, 2.358963, type `large_airport`. LFPG has `08L/26R`, `08R/26L`, `09L/27R`, `09R/27L` and the `08H/26H` grass row.

**Data-quality traps measured, and the validations the build script must run (hard = row dropped and listed in a committed exclusion report; warn = logged, row kept):**

| Trap | Measured | Rule |
|------|----------|------|
| Float32 noise in coordinates | 273 of 361 rows have > 6 decimals (max 20) | Round to 6 decimals before any computation |
| Missing thresholds | LFxx: 260 of 548 rows | Hard drop (D-04) |
| `closed = 1` | 3 of 288 LF both-threshold rows (11 of 548 overall) | Hard drop |
| Airport type `closed` (not `closed_airport`) | 7 French airports with open runway rows | Hard drop on both spellings |
| Swapped / wrong thresholds | `NTGY 18/36`: bearing 218.1 vs designator 180 (38 deg); `TFFA 09/27`: 67.4 vs 90 (23 deg) | Hard drop when designator-vs-bearing deviation > 20 deg |
| Non-reciprocal pair | 0 found | Hard fail unless `|number(le)-number(he)| = 18` |
| Zero or tiny length | min computed length 230 m (`FR-1014`, already filtered); none < 100 m after filter | Hard fail < 100 m |
| `le_ident` number > `he_ident` number | `LFDH 36/18` | Normalise: sort the pair ascending, swap thresholds with it; display `18/36` |
| `heading_degT` missing | 33 of 361 | Ignore the column; always compute the bearing from the rounded thresholds |
| `heading_degT` wrong | `NTGV 01/19` says 197 (reciprocal) while geometry gives 17.4 | Ignore; warn if deviation > 10 deg (15 rows exceed 2 deg, p95 1.9 deg) |
| `length_ft` vs computed length | `LFCH 07R/25L` 1284 m stated vs 748 m computed; `TFFA`, `FMEP`, `LFDH`, `LFEC` also > 25 % | Warn only (stated length includes overruns / displacement; the corridor uses the threshold geometry) |
| Displaced thresholds | 100 le and 112 he rows | Ignore: `length_ft` and coordinates already describe the surface the project used for Orly (`runway3.json` thresholds are the CSV `*_latitude_deg`); do not subtract displacement |
| Suffix letters | `L`, `R`, `C` appear in 55 rows; `G`, `H` appear in 2 rows | Pattern above; `L/R/C` kept in the real designator |
| Surfaces | ASP, CON, GRASS/GRS, PAVED, UNK, TURF, WATER ... 17 spellings | Do not filter on surface except `WATER`; store nothing derived from it |
| Duplicate idents | none in scope | Hard fail on a duplicate `(ident, designator)` |
| Collinear duplicate rows | `LFPK 09/27` and `09C/27C` (0-3 m apart) | Detect; parallel rule floor (Section 2); warn |
| Non-ASCII names | 112-190 | Store UTF-8, `ensure_ascii=False`; panel text uses ICAO/IATA only, never the name |

The build also asserts the coordinate sanity (latitude/longitude finite and inside the territory's broad range), writes `half_width_m > 0` per runway, and asserts that every airport's runway corridors fit inside the 5 NM zone (measured maximum needed radius 3.66 NM at LFPG; median 1.82 NM; none above 5 NM).

**Pinning and reproducibility (recommended):**
- Commit a **filtered raw subset** (airports that own at least one in-scope runway row: 577 rows / 60 KB; all 747 runway rows / 67 KB; original column order, `\n` line endings) plus `scripts/data/ourairports-source.json` holding: download date (2026-10-31), the two URLs (`https://davidmegginson.github.io/ourairports-data/{airports,runways}.csv`, mirror cited by the milestone STACK research), sha256 and size of the **full** files, sha256 of the two **subset** files, the licence sentence and the data-dictionary URL.
- `scripts/build_airports.py` (default mode) reads only the committed subset and writes `server/data/airports_fr.json` deterministically (sorted keys, fixed separators, no timestamps). `--refresh <dir with full dump>` filters a fresh download into the subset and rewrites the source file; it is the only mode that sees the full dump and is never run in CI.
- A test rebuilds in a temp dir and requires byte equality with the committed JSON, and checks the subset sha256 against the source file. A snapshot refresh is then a visible diff on three files.
- Raw data read by `python3 -I` or by a script outside the data directory (untrusted-data rule); reject files over a size cap and any row whose `id` or numeric fields do not parse.

## 2. Parallel runways and the narrow corridor

**Definition (recommended):** two runways of the same airport are *parallel neighbours* when their axes differ by at most **5 deg** (mod 180) and the **minimum distance between their centreline segments, each extended by the 2500 m corridor extension at both ends**, is `d`. Half-width = `max(FLOOR, min(500, d / 2))`; no neighbour means 500 exactly. Extended segments (not infinite lines) mean a staggered pair that never shares an approach path does not shrink the other.

**Why 5 deg and not larger (measured):** parallel pairs in the dump deviate 0.0-4.5 deg; the next pair is `LFXA 01/19-02/20` at 7.1 deg, then **`LFPO 06/24-07/25` at 12.6 deg**. With a 15 deg threshold, Orly 07/25 would shrink to **479.8 m** (extended 06/24 lies 960 m away), breaking D-07 and D-08; and `FMEE 12/30-14/32` (14.4 deg, crossing, distance 0) would shrink to 0. At 5 deg the Orly runways are all 500.0. A regression test must assert LFPO `07/25` half-width `== 500.0` *and* that the parallel threshold stays below the LFPO 06/24 deviation. Number of runways shrunk: 73 of 361 at 5 deg, 75 at 10 deg, 78 at 15 deg.

**Results with the rule, floor aside (measured, extended-segment distance):**

| Airport | Pair | Distance d | Half-width |
|---------|------|-----------:|-----------:|
| LFPG | 08L/26R vs 08R/26L | 386 m | 193 m |
| LFPG | 09L/27R vs 09R/27L | 384 m | 192 m |
| LFPG | 08H/26H (nearest parallel 09R/27L) | 805 m | 403 m (500 not reached; row likely excluded by the designator filter) |
| LFPO | none parallel (06/24 at 12.6 deg) | - | 500.0 on 02/20, 06/24, 07/25 |
| LFMN | 04L/22R vs 04R/22L | 303 / 302 m | 151 m |
| LFML | 13L/31R vs 13R/31L | 305 / 290 m | 152 / 145 m |
| LFBO | 14L/32R vs 14R/32L | 296 / 294 m | 148 / 147 m |
| LFLL | 17L/35R vs 17R/35L | 349 m | 174 / 175 m |
| LFPB | no parallel pair | - | 500 on 03/21, 07/25, 09/27 |
| LFMT | 12L/30R vs 12R/30L | 1117 m | 500 |

Of 361 runways before the final filter, 75 have a half-width below 500 (T = 10 deg); values: 44 below 75 m, 60 below 150 m. All sub-75 m cases are light-aviation airfields with paved + grass or twin strips (LFGI 50 m, LFXU 51 m, LFQF 40 m, LFNA 53 m, LFHV 60 m, LFCH 71 m, LFGB 72 m, LFLU 72-150 m, LFNC 54 m) plus the LFPK collinear duplicates (0 m, 120 m, 274 m).

**Floor (recommended, needs owner confirmation, `[ASSUMED]`):** `FLOOR = 50 m`, because the largest measured real runway-3 airborne offset is 31 m and the pavement-gate analysis recorded about 8.5 m of position error beyond the pavement. Below roughly 100 m of spacing the two runways cannot be separated by position anyway; the floor only prevents a degenerate or silently-widened corridor. Also set `ground_half_width_m = min(75, half_width_m)` so the pavement gate never exceeds the airborne corridor (Orly keeps 75). Both values are stored per runway in the catalogue so the runtime stays data-driven; Orly entries store `500.0`/default.

**Required tests (D-07):** LFPG 08L/26R vs 08R/26L and 09L/27R vs 09R/27L: an on-axis aircraft on one runway is selected for that runway's device and rejected for the neighbour's (cross-track 386 m against a 193 m half-width), plus one non-Paris case (LFMN or LFBO, ~150 m), plus the LFPK/LFGI floor cases, plus LFPO unchanged at exactly 500.0.

## 3. Mapping the existing runway-3 geofence onto a catalogue entry

**Thresholds [VERIFIED: ran `detect.runway_axis` on both]:** OurAirports LFPO `07/25` rounded to 6 decimals equals `runway3.json` `runways["3"].runway.thresholds` exactly: `(48.719398, 2.358590)` and `(48.727402, 2.402070)`. Bearing 74.4085 deg, length 3315.04 m. Unrounded CSV values give bearing 74.4100 and length 3315.02 m, so the rounding is required, not cosmetic. The `06/24` and `02/20` CSV values round to the legacy numbers as well.

**Every geofence field consumed (grep of `detect.py`, `poll_cycle.py`, `fleet_cycle.py`, `fleet_zones.py`):**

| Field | Consumer | Generic source |
|-------|----------|----------------|
| `bbox.lat_min/lat_max/lon_min/lon_max` | `filter_in_geofence` pre-filter | Corridor-rectangle bbox for generic runways; **frozen legacy numbers for Orly ids** |
| `alt_ceiling_ft` | `filter_in_geofence` (`below_ceiling`) | 3000 for runway mode (same as legacy); 10,000 for position mode |
| `center.lat/lon`, `radius_nm` | `_fetch_providers`, `zone_from_geofence`, `poll_cycle._fetch_standalone` | Runway mode: airport reference point rounded to 4 dp, radius 5.0; Orly ids: frozen `(48.7233, 2.3794, 5)` so the zone key stays `'48.7233\|2.3794\|5.0'` |
| `runways[id].runway.thresholds[2]` | `runway_axis` | Catalogue, 6 dp |
| `runways[id].corridor.half_width_m / extension_m / axis_tolerance_deg / ground_half_width_m` | `corridor_params` | Catalogue `half_width_m`; constants 2500 / 30 / 75 |
| `runways` keys | `runway_ids`, `_effective_runway_id` | Must contain the display id |
| flat `runway` / `corridor` | fallback only (`runway_block`) | Not generated; generic docs must never reach this branch |

Not consumed by decisions: `center.source`, `bbox.source`, `correction_*`, `runway.local_designation`, `runway.width_m`, `neighbouring_runways`, `runways_source`.

**Derived fields the generic logic computes:** axis (origin, unit vector, length, bearing) from rounded thresholds; bbox = bounding box of the four corridor corners `(-ext, L+ext) x (-hw, +hw)` in local metres converted back with the same `_M_PER_DEG_LAT` and `lon_scale` arithmetic as `detect`; centre = airport reference point; radius = 5.0 NM (assert every corridor corner is within it).

**What "identical" means numerically (D-08):** *the boolean `runway_candidates` result and the normalised selection dict (every key except `seen_pos`) are equal, for every record, for ids `3`, `06-24`, `02-20`, in single-provider and two-provider (intersection) cases.* No tolerance is needed because the Orly documents carry the same numbers; any inequality is a failure. Recommended mapping: **all three legacy ids carry the legacy bbox/centre/radius/ceiling override** (the legacy geofence applied the runway-3 bbox to all three ids, so the legacy behaviour for 06-24 and 02-20 is clipped by that bbox; for example the 02/20 northern threshold at lat 48.738 is outside `lat_max 48.734`). Strict identity is then provable for all three. Catalogue selections of the *same* LFPO runways made on the new page should resolve to the legacy ids (Section 6), so there is one representation.

## 4. Replay design for DET-02

**Recorded Orly traffic in the repo [VERIFIED]:** `adsb-test/samples/*.jsonl` is gitignored and not on disk. Committed: `server/fixtures/geofence_*.json` (14 records across multi_aircraft 4, on_ground 2, runway3_arrival_347288 1, taxiway_masking 2, wrong_runway_39de4a 1, pavement_pair two provider blocks, empty 0) and `track_arrival_440cb1.json` (3 track points). Two multi_aircraft records are explicitly synthetic. `adsb-test/RUNWAY-GATE-VERIFICATION.md` summarises 480 polls / 95 selections but the raw lines are not committed. Fixtures are therefore a *small* corpus; do not describe the replay as "recorded traffic proves it" without the sweep.

**Design (one new test module, e.g. `server/test_orly_replay.py`):**
1. **Legacy path:** `detect.load_geofence()` (the file) with `runway_id` in `3, 06-24, 02-20`.
2. **Generic path:** `detection.spec_for({"tracked_runway": id}, ...)` document built from the committed catalogue plus the frozen override.
3. **Corpus A (recorded):** all committed fixtures, including the two-provider pavement-pair file through `select_from_provider_results` with both orderings; the 3 track points.
4. **Corpus B (deterministic sweep, no randomness):** lattice over lat/lon spanning the generic corridor bbox +- 1e-3 (e.g. 201 x 401 cells), x tracks `{axis, axis+180, axis+29, axis+31, 0, missing}`, x altitude `{450, 2999, 3000, 3001, "ground", None}`; assert equal `runway_candidates` booleans and equal selection dicts. Keep runtime under a few seconds by sampling (the exploratory 963,603-cell run took tens of seconds; use a coarser grid plus a dense band near the bbox edge).
5. **Differential evidence test (documents why the override exists):** build the same document with the generic bbox and assert that *at least one* sweep cell differs. If a future change makes them equal the override can be dropped; until then this test explains the code.
6. **Drift checks:** the frozen override equals `runway3.json` byte for byte (bbox, centre, radius, ceiling); the catalogue's LFPO `07/25` thresholds equal `runways["3"]` thresholds; `half_width_m` for LFPO runways is exactly `500.0`.
7. **Zone key test:** the generic Orly spec's `Zone.key` equals the legacy resolver's key, so Phase 52 zone sharing and ledger `zone_last_served` are unchanged.
8. **Pipeline-level check:** run `poll_cycle.run_once` twice on the same synthetic snapshot (legacy file vs generic spec, via the kill switch) and compare image hash, `cycle_result` fields and poll_state keys; `test_phase47_freeze.py` covers the served image hash and wake fields separately and must be run unchanged.

**Risk if thresholds differ slightly:** a 1e-5 deg shift moves the bearing by ~0.001 deg and the length by cm; combined with the 30 deg / 500 m / 75 m gates this almost never flips a decision, which is exactly why a fixture-only replay can pass vacuously. The sweep with a dense band at each gate edge (cross-track 499/500/501 m, along-track -2500/-2499, ground 75 m margin) is the check that has teeth.

**Reversible switch (D-08/D-09):** `detection.spec_for` takes the legacy document through one function `legacy_orly_spec(geofence_path)`; a single module constant plus env var (for example `SKYPANE_LEGACY_ORLY_GEOFENCE=1`) forces legacy ids back onto `detect.load_geofence`. The test suite runs the replay both ways. If the replay ever fails, the constant defaults to legacy and the owner is told (D-08).

## 5. Position mode

**Spec:** centre = the device location (`locations.latitude/longitude`, read from `fleet.db` through `devices.location_id`) rounded with `round(x, 2)` (normalise `-0.0`); radius = integer NM in `[2, 15]` (integers only so near neighbours really share `Zone.key`; the key uses `repr`, and `repr(round(x, 2))` is always the short two-decimal form). `Zone(lat, lon, radius)` is built from the *rounded* values; the unrounded coordinate never exists past the spec constructor. Query URL example: `.../lat/48.86/lon/2.35/dist/5`.

**Selection:** new pure `detect.position_candidates(aircraft, geofence)`: record has numeric `lat/lon`, haversine (or the same local-metres arithmetic) distance to the rounded centre `<= radius_nm * 1852`, `alt_baro` numeric (not the `"ground"` string, not `None`), `0 <= alt_baro <= 10000`. Then `selection_sort_key` (lowest altitude, hex), `_normalise_selection`, and the existing candidate-set intersection. Dispatch from `runway_candidates` on `geofence.get("detection_mode")` (default runway) so `select_from_provider_results` and `poll_cycle` need no signature change. Airborne-only means on-ground records and records without altitude never qualify (the `below_ceiling = False for unknown` rule already points the right way).

**Country bounds (D-13), proposed numbers `[ASSUMED]`:** latitude `41.30 .. 51.15`, longitude `-5.20 .. 9.60`. Evidence from the dump: metropolitan airports with runways span lat 41.50185 (LFKF Figari) .. 50.962101 (LFAC), lon -5.06358 (LFEC) .. 9.48373 (LFKB Bastia). Real extremes (Corsica south, Dunkirk, Ushant, Cap Corse) are covered with a small margin. The box necessarily includes slivers of Spain, Italy, Switzerland, Belgium, Germany and the sea; it is a coarse guard, not a border test, and the 15 NM radius may reach beyond it. Validate the **rounded** coordinates, in the form handler *and* in `spec_for` (a stored location later edited out of France must not poll). Message: "This frame's location is outside metropolitan France; choose a location inside France." Refusal in `spec_for` returns the legacy fail-safe spec plus a flag; do not raise into the cycle.

**What the image shows (render currently depends on the Orly tag):** `style.runway_tag_text(runway_id)` and `empty_heading_text(runway_id)` index the three-entry `RUNWAYS` registry after `normalise_runway_id`; layout code assumes the tag contains `" · "` (`draw_top_labels` partitions it into airport code and runway part for band themes, producing `"DEPARTING FROM <code>"` / `"ARRIVING TO <code>"`; `_assert_within_canvas` raises if the tag is too wide). Proposed panel copy (English, locked, never localised):
- Runway mode: tag `"<IATA or ICAO> · <designator>"` (D-06), e.g. `CDG · 08L/26R`, `LFNC · 16/34`; empty heading `"Watching Runway <designator>"` (matches the existing pattern). Legacy ids keep `ORY · RWY 3`, `ORY · RWY 06/24`, `ORY · RWY 02/20` and the existing headings byte for byte.
- Position mode: tag `"NEARBY · <R> NM"` (never the location name: user text of arbitrary length would break the canvas assertion); empty heading `"Watching Within <R> NM"`. Band themes would read "DEPARTING FROM NEARBY": acceptable but awkward; see Open Question 3 for the alternative of a direction-word-free label.
- Maximum tag length to test: an ICAO-ident fallback such as `LF50 · 08L/26R` (14 characters), the same order as the existing `ORY · RWY 06/24` (15).
Render takes only a `runway_id` string, so the change is inside `style.runway_tag_text`/`empty_heading_text` (delegate to `detection` for non-registry ids). The landscape renderer reuses the same two functions (`landscape_card._draw_top_row`, `landscape_hold.build_empty_canvas`), so one change covers both layout families.

**Where coordinates could leak, and the guard:**
- `detect.query_provider` builds `https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}` and the adsb.lol equivalent from the zone numbers only; `zone_fetch.fetch_zone` documents "Coordinates are sent exactly as given". The single choke point is therefore zone construction.
- Exceptions: `requests` connection errors embed the request path; `_query_one` prints `type(exc).__name__: exc` to stderr/journal. With rounded zones the logged path is rounded too, but add a test that no log line contains an unrounded coordinate.
- **adsbdb receives the callsign only** (`ADSBDB_URL = https://api.adsbdb.com/v0/callsign/{callsign}`; no latitude/longitude anywhere in `enrich.py`). [VERIFIED: grep]
- `request_ledger.json` stores `zone_last_served` under `Zone.key` (rounded for position zones, local file, not third party). `runway_events` stores the *aircraft* position, not the device's.
- Guard test: patch `http_fetch.bounded_get` (or use the fake provider transport used by `test_zone_fetch.py`), run a position-mode device with location `48.85661, 2.35222`, and assert every captured URL contains `48.86` and `2.35` and no other coordinate substring. Add a second assertion that two devices at `48.8566` and `48.8601` produce one zone and one fetch.
- Runway mode does not round (D-12): airport coordinates are public.

## 6. Per-device storage, migration, resolver, caching, zone sharing

**Current behaviour [VERIFIED: read `server/device_config.py`]:** `load_device_config` returns exactly 11 registry keys, each normalised (`normalise_runway_id` maps anything unknown to `"3"`); `save_device_config` validates, merges over `current` and rewrites; a key absent from the registry is **dropped on the next save**, not preserved. `timezone` is the precedent for expand-only: it is written only when it differs from the default, so an unchanged device's file bytes never change. `stub-server/test_phase47_freeze.py` lists `device_config.json` in `LEGACY_IDENTITY_FILES` and compares replay output before/after migration.

**Recommended keys (additive):**
- No new key for legacy-equivalent selections. Selecting LFPO `07/25`, `06/24` or `02/20` stores `tracked_runway` `"3"`, `"06-24"`, `"02-20"` and **omits** `detection`. The live frame's file stays byte-identical and the previous release reads it natively.
- Any other selection stores one object, `"detection": {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}` or `{"mode": "position", "radius_nm": 5}`; `tracked_runway` is left as is (default `"3"`), which is what the previous release will read.
- Loader: `detection` is returned as a normalised object or `None`; anything malformed, unknown airport/runway or out-of-range radius normalises to `None` (legacy Orly), never raises (same rule as every other key). `save_device_config(detection=...)` follows the existing three-state idiom: `None` carries forward, a sentinel clears (needed when the user goes back to a legacy runway), an object sets. Meaning (airport exists, runway exists, radius bounds) is validated by `detection.validate(...)`, called by the page handler before saving and by `spec_for` before using; `device_config` validates only shape (leaf rule).
- Position centre is **not** stored in the JSON: it is the device's location row. A device in position mode with no location, or a location outside the France box, resolves to the legacy fail-safe spec and surfaces a banner on the page. `spec_for` needs the location passed in (resolver reads `fleet.db` read-only; `poll_cycle` reads it through the same helper or receives it from the fleet cycle).
- ARCHITECTURE.md sketched DB columns (`detection_mode`, `airport_icao`, `runway_id`, `radius_nm`) with the JSON overlay; CONTEXT leaves storage to discretion and the previous-release rule favours JSON (no schema migration). Keep it in JSON.

**Resolver change (`server/fleet_cycle.py`):** replace `geofence_resolver(path)` (one cached `(Zone, doc)` for all devices) by a resolver that, per device, reads `device_config.load_device_config(device.state_dir)` and calls `detection.spec_for`. Keep `geofence_resolver` as the legacy-document loader used for the Orly spec and for existing tests (`test_default_resolver_*` assert its shape, including `OSError` on a missing file). Exceptions already map to `unzoned` (live frame then runs a standalone fetch; others are skipped with `no_zone`), so the new resolver must raise only `OSError/ValueError/KeyError/TypeError`. Cache: the catalogue via `lru_cache` (immutable); the legacy document via the existing per-run cache; do not cache device configs across devices.

**`poll_cycle` change:** `CycleContext.geofence` stays a path (legacy document) but `detect_flight` and `_fetch_standalone` obtain the document from `detection.spec_for(ctx.device_cfg, location)`; the snapshot-injection branch (`ctx.snapshot is not None`) uses the same document. Everything downstream already consumes `ctx.tracked_runway_id` as an opaque string.

**Zone key and sharing (Phase 52 D-12):** exact `(lat, lon, radius)`. Runway mode: all runways of an airport share one zone (`ARP rounded 4 dp`, 5.0 NM), so CDG devices on different runways cost one request set. Orly legacy ids keep `(48.7233, 2.3794, 5.0)`. A device that selects LFPO `07/25` on the page resolves to the legacy id, hence the same key. Position mode: `(round(lat,2), round(lon,2), integer radius)`; two nearby devices with the same radius share. A runway zone and a position zone never coincide by accident except when the numbers are identical, which is harmless (same upstream data, different local gating, per-device selection). The group's stored geofence is unused for selection (Pitfall 5).

## 7. Companion: route, access, page, guards

**Route declaration (`companion/routes.py`):** add `DETECTION_ROUTE = "/detection"` and two `Route` entries (`GET`, `POST`) built with `Exact`, plus the keys in `_PAGE_AND_IMAGE_KEYS` / `_ACTION_KEYS` so they also resolve under `/devices/<id>/...` (`_DEVICE_SCOPED_KEYS`; the comment "13 GET and 14 POST" must be updated). Handler: `lambda h, m: h._render_tab(DETECTION_ROUTE, detection_page.render, m.device)` and `h._handle_detection_post(m.device)` in `companion/app.py` or `post_actions.py` (follow `_handle_settings_post`: sanitised form, `page_context(device)`, 200 re-render with field errors, `303` to the scoped page with a flash on success). Search and airport pick use GET query parameters only (`?q=`, `?airport=`), so no state is changed by GET.

**Access (`companion/access.py`):** `ADMIN_ONLY` today for `/device`, `/update`, `/quick/led`, and `user_view.ADMIN_ONLY_SETTING_FIELDS` already makes `tracked_runway` admin-only. Recommended: `ADMIN_ONLY` for GET and POST (un-prefixed form acts on the live frame, admin only; prefixed form also admin-only), widening to `OWNER_DEVICE` later is a one-line change plus matrix row once the reduced user view (Phase 55) decides what an ordinary owner may change. D-14's wording ("wrong role or other owner's device answers 404") is satisfied by both. See Open Question 1.

**Matrix and route-table tests that must change:**
- `companion/test_access_matrix.py`: add `("GET", "/detection"): ADMIN_ONLY` and `("POST", "/detection"): ADMIN_ONLY` to `ROUTE_POLICY` (the completeness test names a missing route), and both to `DEVICE_SCOPED`. The HTTP layer then proves anonymous -> login redirect, owner/other -> 404, admin -> reaches the handler, for the un-prefixed and the `/devices/<id>` forms, and malformed ids.
- `companion/test_route_table.py`: `len(owner) == 24` counts `OWNER_DEVICE` routes only, so it changes only if the route is `OWNER_DEVICE` (then 26); `test_owner_device_routes_are_exactly_the_user_reachable_frame_routes` asserts the exact `admin_device_only` set `{DEVICE_ROUTE, QUICK_LED_ROUTE}`, which must gain the two new routes if they are `ADMIN_ONLY`. Also `test_every_other_route_is_admin_only_or_an_owner_device_route` already accepts both.
- Regenerate `companion/testdata/render_baseline.json` (`python test-support/companion_render_snapshot.py --write`); `test_every_gated_route_redirects_an_anonymous_request` indexes it by `"METHOD path"`. Review the diff: only the new keys (and the Display page if the Runway card changes) may differ. Add `_SAMPLE_MIDDLE` entries only for `PrefixSuffix` routes (none here).

**Page design (read `Skill("sketch-findings-skypane")` and `references/settings-page-patterns.md`, `control-density.md`, `accessibility-contrast.md` before building):**
- Reuse existing card vocabulary rather than inventing CSS: `.page-section` / `.theme-status` cards with `[data-dirty-section]` headings (`text-heading`, 22 px serif), `.section-caption`, selectable `.runway-card` radio cards (the whole `<label>` is the hit target around a `visually-hidden` radio, selected state `runway-card--selected`, `CURRENT_BADGE_ATTR`), `.filter-bar__field` for the search input (32 px field with `min-height: 0`), `.toast` for flash/errors (`ui_components.toast_html()`), `empty_state()` (compact variant inside tiles), `layout.page_header`. Design for 360 px minimum width; no new accent uses; 44 px touch targets for the submit buttons; no-JS floor means every control works as a plain form (the existing `.js [data-static-save-fallback]` convention hides only the *duplicate* Save when JS runs).
- No-JS flow: (1) `GET /detection` shows the current setting summary, a `<form method="get">` search field (name `q`) and, for position mode, the radius control. (2) `GET /detection?q=cdg` lists matches (cap at about 20, case- and accent-insensitive substring over ICAO, IATA, name, municipality; sort exact-code matches first) as links to `?airport=LFPG`. (3) `GET /detection?airport=LFPG` renders one card per runway: real designator, both orientations (e.g. `085° / 265° true`, length in m), radio `name=runway`, a hidden `airport` field and a submit button. (4) `POST /detection` with `mode=runway|position`. The existing `list-filter.js` may be used as progressive enhancement but must not be required.
- Position card: shows the assigned location's name and the *rounded* coordinates that will be sent ("sent to the data providers as 48.86, 2.35"), a number input for the radius (min 2, max 15, step 1) and the France-box error. `fleet_db.set_device_location_checked` already exists; there is **no companion UI to create or assign locations** (`LOCATIONS_ROUTE` is only a placeholder in `ui_nav`; creation is `stub-server/fleet_cli.py`). Minimal viable: a `<select>` of existing locations (`fleet_db.list_locations_for`) on the position card that calls `set_device_location_checked`, plus an empty state "No location assigned" otherwise. Open Question 2.
- Entry points: a link/summary on the Display page (the Runway card currently shows only the three Orly radio cards; a device in catalogue or position mode must not show a legacy radio group that appears to select `3`, otherwise a Display save would post `tracked_runway=3`). Recommended: keep the legacy card only when the device is on a legacy id and add a "Change airport, runway or position" link; for other modes replace the card with the summary link. `form_post.resolve_runway` already treats an absent field as carry-forward.
- Strings: `i18n.msg("detection.<slug>", "English")` at module level; French in new `companion/i18n_fr/detection.py` (`MESSAGES = {...}`; the package auto-merges modules and raises on duplicate ids; `test_i18n` requires every registry id to have French and the id shape `<area>.<slug>` with `area` an existing module name). Panel copy (tag, heading) is *not* i18n.
- Server-side validation on POST (the form is never trusted): airport and runway must exist in the catalogue; radius integer in 2..15; position requires a location inside the France box after rounding; unknown `mode` rejected; all-or-nothing, errors re-rendered at 200 with field errors like `config_page`.

**CI guards a new page must satisfy:**
- `companion/test_suite_guards.py`: new tests may not read `.planning/`, production source text, use `inspect/ast`, write outside `tmp_path`, import other test modules (use `*_helpers.py`), or regex the stylesheet. Assert served HTML via the in-process app server fixtures (`companion/conftest.py`, `test-support/companion_app_server.py`, `access_matrix_support.py`).
- `companion/test_structure_guards.py`: no companion production file over 1500 lines, no function over 80 code lines. The search/render builders must be split (list results, runway cards, position card, summary).
- mypy: add `server/airports.py`, `server/detection.py` (and any typed module) to `[tool.mypy] files` in `pyproject.toml`; no PEP 695 syntax.
- Function-size gate (`scripts/check_function_size.py check --max 80 server stub-server`) covers `server/` new modules; `scripts/build_airports.py` is outside those roots but keep functions small anyway.
- Comment-history guard: no `D-nn`, `Phase nn`, `DET-nn` (`DET` is not in the allowlisted prefix list, but `D-08`, `Phase 53`, `.planning/` are flagged), no plan ids in docstrings.
- Coverage floor 93 % over `server stub-server companion deploy/backup`; new code must be covered by the tests below (the browser tests contribute through subprocess coverage).
- Playwright browser test (optional but valuable, `@pytest.mark.browser`, a missing browser fails CI): search without JS, radio selection, 360 px layout.

## 8. Credits and COMPLIANCE

- **`companion/credits.json`:** OurAirports present (`"licence": "Public domain"`, `"citation_required": false`, EN "Open airport data used to name airports. Credited as a courtesy."). `companion/credits_page.py` `REQUIRED_IDS = ("adsbfi", "adsblol", "adsbdb", "ourairports")`; `companion/test_credits_page.py::test_shipped_file_lists_the_four_sources` pins the list. **The description is now inaccurate** (the data places and orients runways, not just names airports): update EN and FR descriptions together (FR lives in the same JSON `description.fr`).
- **`COMPLIANCE.md` has no OurAirports section** (grep of `COMPLIANCE.md`, `README.md`, `NOTICE`, `server/README.md` finds none; only `credits.json` and `adsb-test/runway3.json` cite it). The task statement and ARCHITECTURE/FEATURES assume otherwise; this is a gap to close. Add a `## OurAirports` section in the file's existing per-source shape (Used in shipped code, Upstream, Terms checked 2026-10-31 with the quoted sentence, What the terms require, Verdict, Credits) stating: build-time only, committed snapshot with date and sha256, never fetched at run time, no attribution required, credited as a courtesy; and a row in the Status table; update the intro line that counts sources ("Six sources are covered").
- **Drift check:** none exists between `credits.json` and `COMPLIANCE.md` (no `.py` references `COMPLIANCE`). Recommended small behavioural test (docs are `.md`, not guarded source): every `name` in the shipped credits sources has a `## <name>` heading in `COMPLIANCE.md` (currently `adsb.fi`, `adsb.lol`, `adsbdb` vs heading `adsbdb.com`, `OurAirports`; the adsbdb name differs, so map by `id` or match on a substring). Also add a build-time sentence to `COMPLIANCE.md`'s "Runtime behaviour" list: the catalogue is not a runtime dependency.
- **Request budget statement** in `COMPLIANCE.md` ("Fleet-wide ADS-B request budget") needs one added bullet: position-mode zones are queried with coordinates rounded to two decimals (about 1 km), which also reduces what is sent to adsb.fi/adsb.lol; runway zones use public airport coordinates.

## 9. Code Examples

```python
# Source: server/plane/detect.py (existing, reused unchanged for runway mode)
candidates = detect.runway_candidates(aircraft, doc, runway_id=display_id)
flight = detect.select_from_provider_results(
    fetched.results, doc, runway_id=display_id,
    diagnostics=diagnostics, queried=fetched.queried, failed=fetched.failed)
```

```python
# Rounding choke point (shape; names are the planner's)
def position_zone(lat: float, lon: float, radius_nm: int) -> fleet_zones.Zone:
    clat, clon = round(lat, 2) + 0.0, round(lon, 2) + 0.0   # + 0.0 turns -0.0 into 0.0
    if not (FR_LAT_MIN <= clat <= FR_LAT_MAX and FR_LON_MIN <= clon <= FR_LON_MAX):
        raise ValueError("position outside metropolitan France")
    if not (RADIUS_MIN_NM <= radius_nm <= RADIUS_MAX_NM):
        raise ValueError("radius out of bounds")
    return fleet_zones.Zone(clat, clon, float(radius_nm))
```

```python
# Parallel rule at build time (shape)
def half_width_m(runway, same_airport, ext=2500.0, tol_deg=5.0, floor=50.0, default=500.0):
    gaps = [segment_gap_m(runway, other, ext) for other in same_airport
            if other is not runway and axis_deviation_deg(runway, other) <= tol_deg]
    return default if not gaps else max(floor, min(default, min(gaps) / 2.0))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One hand-tuned geofence file, runway id selects a block | Catalogue-generated geofence documents per device | This phase | Data replaces code branches; Orly keeps a frozen override |
| One resolver for all devices (`geofence_resolver`) | Per-device resolver reading `device_config.json` | This phase | `ZoneGroup.geofence` stops being authoritative |
| `RUNWAYS` registry (3 ids) drives tag text | Display ids resolved via `detection` | This phase | `normalise_runway_id` must not be applied to non-registry ids |

**Deprecated/outdated:** adsb.fi `api/v2` is "deprecated but working" (milestone STACK research); a v3 migration is out of scope here and must not be mixed into this phase's replay (it changes the array key silently).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Parallel threshold of 5 deg (axis deviation) and extended-segment distance as the metric | 2 | If the owner prefers 10 deg: 2 more runways shrink; Orly unaffected (12.6 deg), but any value >= 13 deg breaks Orly identity |
| A2 | Half-width floor 50 m and `ground_half_width_m = min(75, half_width)` | 2 | Floor deviates from the literal D-07 formula for about 25 light-aviation runways; owner should confirm. Without a floor two rows get 0 and silently widen to 500 |
| A3 | France box lat 41.30..51.15, lon -5.20..9.60 | 5 | Too small refuses a valid address (Corsica/Ushant tips); too large admits parts of neighbouring countries; derived from dump airports, not from an official outline |
| A4 | Position tag `NEARBY · <R> NM` and heading `Watching Within <R> NM` | 5 | Cosmetic; band themes read "DEPARTING FROM NEARBY" |
| A5 | New route is `ADMIN_ONLY` (consistent with admin-only `tracked_runway`) | 7 | If the owner expects ordinary owners to use it now, switch to `OWNER_DEVICE`, update the matrix rows and `len(owner)` |
| A6 | Catalogue scope: ICAO-like idents in French territories, designators `NN[LRC]`, drop `closed`-type airports and water | 1 | Differs slightly from "every row" in D-04 (excludes 2 non-standard-designator rows, internal `FR-nnnn` ids); owner told |
| A7 | The live Orly frame is configured on tracked runway `"3"` (production `device_config.json` is not in the repo) | 3 | If it were `06-24` or `02-20`, the all-three-ids override already preserves identity |
| A8 | Catalogue is about 63 KB and the committed raw subset about 127 KB | 1 | Size estimates from a prototype; harmless if off |
| A9 | Local venv is Python 3.13 while production is 3.14 | Environment | Tests run on 3.13 locally; avoid 3.14-only syntax in new code |

## Open Questions

1. **Who may use the Detection page now: admin only, or owners too?**
   - Known: `tracked_runway` is in `user_view.ADMIN_ONLY_SETTING_FIELDS`; Phase 54 left per-device routes admin-only until Phase 55's reduced view; D-14 only requires 404 for wrong role or other owner.
   - Unclear: whether the owner wants plain users to change airport/position in this phase.
   - Recommendation: `ADMIN_ONLY` (fail closed, one-line widening later). Flag to owner.
2. **Locations: how does a device get one?**
   - Known: `locations` and `devices.location_id` exist, `fleet_db.set_device_location_checked` exists, creation is only `stub-server/fleet_cli.py`, the live frame was migrated with a location.
   - Unclear: whether position mode must be able to assign/create a location from the companion in this phase.
   - Recommendation: select-from-existing on the position card (admin sees all, owner only own); creation stays CLI until Phase 55.
3. **How is level traffic labelled in position mode?**
   - Known: states are only DEPARTING/ARRIVING with a +-200 fpm deadband and hold-last-state; first-ever level aircraft renders the empty screen.
   - Unclear: whether showing "DEPARTING" for a level cruiser is acceptable; adding a third state touches themes and golden renders.
   - Recommendation: keep the existing inference for this phase (zero render diff), document the limitation, and let the owner decide a "NEARBY" state later.
4. **Floor on the parallel half-width (A2) and the two excluded non-standard rows (A6).** Recommendation as stated; confirm with the owner when reporting.
5. **Display-page Runway card:** keep for legacy devices and replace by a summary link for other modes (recommended), or replace for all? Affects `test_config_page_*` and browser tests.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv (`server/.venv`) | all tests | yes | 3.13.18 (prod 3.14) | - |
| pytest, ruff, mypy in venv | CI gates | yes | present | - |
| Playwright Chromium | browser tests | not checked in this session (no `~/.cache/ms-playwright`) | - | CI installs it; `SKYPANE_REQUIRE_BROWSER=1` fails instead of skipping |
| OurAirports dump | build script `--refresh` only | yes (local copy, sha256 above) | 2026-10-31 snapshot | Committed raw subset; CI never downloads |
| Outbound HTTPS | none at run time | - | - | pytest-socket blocks non-loopback by design |

**Missing dependencies with no fallback:** none. **Missing with fallback:** browser (CI provides).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 + xdist + cov + pytest-socket, pytest-playwright for `@pytest.mark.browser` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, importlib mode, `--disable-socket` with loopback allowed) |
| Quick run command | `server/.venv/bin/python -m pytest server/test_airports_catalogue.py server/test_detection_spec.py server/test_orly_replay.py -x -q --cov-fail-under=0` |
| Full suite command | `./scripts/run-all-tests.sh` (CI command; coverage floor 93) |
| Other gates | `server/.venv/bin/ruff check .`; `server/.venv/bin/mypy`; `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`; `server/.venv/bin/python scripts/check_comment_history.py check`; `server/.venv/bin/python -m pytest stub-server/test_phase47_freeze.py -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DET-01 | Build is reproducible: subset sha256 matches source file; rebuilding gives byte-identical `airports_fr.json` | unit | `pytest server/test_airports_catalogue.py -k reproducible` | Wave 0 |
| DET-01 | Rows without both thresholds / `closed=1` / type `closed` / non-standard designators absent; LFPO has 02/20, 06/24, 07/25 with legacy thresholds; designators real (`08L/26R`) | unit | `pytest server/test_airports_catalogue.py -k "absent or designator or lfpo"` | Wave 0 |
| DET-01 | Build validations: float rounding, reciprocal pair, designator-vs-bearing > 20 deg dropped, exclusion report equals committed list | unit | `pytest server/test_airports_catalogue.py -k validation` | Wave 0 |
| DET-01 | Device config round-trip: set airport/runway, legacy ids store no `detection` key, malformed value normalises to legacy, legacy file bytes unchanged | unit | `pytest server/test_runway_config.py server/test_detection_spec.py -k config` | Wave 0 (extend existing) |
| DET-01 | Fleet resolver per device; same-airport different-runway devices share one zone; selection uses own runway | integration | `pytest server/test_fleet_cycle.py -k "detection or zone"` | Wave 0 (extend) |
| DET-01 | Page: search works with no JS (GET), runway cards, POST validation, 404 for other roles/devices | HTTP | `pytest companion/test_detection_page.py` | Wave 0 |
| DET-01 | Tag text `CDG · 08L/26R`, ICAO fallback, legacy tags byte-identical; render fits canvas (portrait + landscape) | unit | `pytest server/test_render.py server/test_render_landscape_card.py -k tag` | extend |
| DET-02 | Replay: recorded fixtures + exhaustive sweep give identical candidates and selections for ids 3, 06-24, 02-20, both providers | unit | `pytest server/test_orly_replay.py` | Wave 0 |
| DET-02 | Override is the legacy bbox/centre/radius/ceiling (drift vs `runway3.json`); generic bbox differs on at least one cell (evidence) | unit | `pytest server/test_orly_replay.py -k "drift or evidence"` | Wave 0 |
| DET-02 | Zone key of Orly spec equals legacy `48.7233\|2.3794\|5.0`; kill switch returns legacy path | unit | `pytest server/test_orly_replay.py -k "zone_key or kill_switch"` | Wave 0 |
| DET-02 | Parallel airports: LFPG pairs (193/192 m), LFMN or LFBO (~150 m), LFPO exactly 500.0, floor cases LFPK/LFGI | unit | `pytest server/test_airports_catalogue.py server/test_plane_detection.py -k parallel` | Wave 0 |
| DET-02 | Live frame invariants: image hash, wake interval, poll-state keys unchanged | integration | `pytest stub-server/test_phase47_freeze.py` | exists |
| DET-03 | Position gate: radius edge, ceiling edge (10,000 / 10,001), ground and altitude-missing rejected, lowest first, hex tie-break, corroboration | unit | `pytest server/test_plane_detection.py -k position` | extend |
| DET-03 | Bounds: radius 2..15 integer, France box on rounded coordinates, form and server side | unit + HTTP | `pytest server/test_detection_spec.py companion/test_detection_page.py -k bounds` | Wave 0 |
| DET-03 | Rounding: provider URLs contain only 2-decimal coordinates; logs too; neighbours (48.8566 / 48.8601) share one zone and one fetch; adsbdb URL has no coordinates | integration | `pytest server/test_zone_fetch.py server/test_detection_spec.py -k round` | extend |
| All | Route x role x owner matrix includes `/detection` GET and POST; baseline regenerated | HTTP | `pytest companion/test_access_matrix.py companion/test_route_table.py companion/test_render_baseline.py` | extend |
| All | i18n completeness, credits shipped file text, COMPLIANCE heading per credit source | unit | `pytest companion/test_i18n.py companion/test_credits_page.py` | extend |

### Sampling Rate
- **Per task commit:** the quick command above plus `ruff check` on touched files.
- **Per wave merge:** `./scripts/run-all-tests.sh -- companion server stub-server` for the touched areas, then ruff, mypy, function-size, comment-history, `test_phase47_freeze.py`.
- **Phase gate:** full `./scripts/run-all-tests.sh` green (coverage >= 93) with `SKYPANE_REQUIRE_BROWSER=1` before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `server/test_airports_catalogue.py`, `server/test_detection_spec.py`, `server/test_orly_replay.py`, `companion/test_detection_page.py` (new files)
- [ ] `scripts/data/*` raw subset + source pin and `server/data/airports_fr.json` (needed before any test above can run)
- [ ] A deterministic sweep helper in `test-support/` (shared by the replay and parallel tests) if reuse is wanted
- [ ] Regenerated `companion/testdata/render_baseline.json`
- [ ] No new framework install

## Security Domain

### Applicable ASVS Categories (level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (route inherits the Phase 54 session gate) | `access.decide` default-deny |
| V3 Session Management | no | existing cookie/session code |
| V4 Access Control | yes | `Route` with explicit `Access`, ownership gate on prefix id, 404 for wrong role/owner, matrix test rows |
| V5 Input Validation | yes | Server-side allow-list validation: airport and runway looked up in the catalogue (never interpolated), radius integer 2..15, `mode` enum, France box on rounded values, `q` length-capped and HTML-escaped on output |
| V6 Cryptography | no | none |
| V8/V9 Data protection / communications | yes (privacy) | Device position never leaves the server unrounded; adsbdb gets callsign only |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Crafted `runway`/`airport` posted to select a non-catalogue geometry | Tampering | Re-validate against the committed catalogue on POST; never accept thresholds or ids as geometry from the client |
| Reflected XSS through `q` or airport names (non-ASCII, quotes) | Tampering | `escape_html` on every output; names come from our own JSON; existing guards scan served HTML |
| Cross-site POST changing a device's detection | Tampering | Existing Origin / Sec-Fetch-Site gate runs before `routes.match()` for every POST |
| Request-budget exhaustion through many distinct position zones (M12) | DoS | Integer radius and 2-dp centre bound the number of distinct zones; Phase 52 capacity (25 s start deadline, oldest-served-first) already caps fetches; consider a per-user device cap in Phase 55 |
| Home position disclosure to third parties | Information disclosure | Single rounding choke point, URL/log guard test, runway mode excluded by design |
| Tainted CSV in the dump (hostile row) | Tampering | Build reads only the committed subset; strict numeric parsing, size cap, fail-closed validations, `python3 -I` when touching a fresh download |
| Malformed generated geofence silently widening to bbox-only | Elevation of gate | Test `_effective_runway_id(doc, id) == id` for every runway; build fails on non-positive half-width |

## Sources

### Primary (HIGH confidence)
- Repository code read in this session: `server/plane/detect.py`, `adsb-test/runway3.json`, `server/device_config.py`, `server/fleet_cycle.py`, `server/fleet_zones.py`, `server/zone_fetch.py`, `server/poll_cycle.py`, `server/plane/render/{style,layout,hold_screens,landscape*}.py`, `server/plane/runway_config.py`, `server/plane/enrich.py`, `server/fleet_db.py`, `companion/{routes,access,user_view,page_context,ui_nav,credits_page}.py`, `companion/pages/config_page.py`, `companion/settings/runway_led.py`, `companion/test_{access_matrix,route_table,suite_guards,structure_guards,i18n}.py`, `stub-server/test_phase47_freeze.py`, `pyproject.toml`, `.github/workflows/ci.yml`, `COMPLIANCE.md`, `companion/credits.json`.
- Measurements: OurAirports snapshot 2026-10-31 (sha256 above) read with `python3 -I`; scratch scripts in the session scratchpad; replay and sweep run with `server/.venv/bin/python` against the real `detect` module.
- [OurAirports data page](https://ourairports.com/data/) fetched 2026-10-31: public domain, no guarantee, nightly update.
- [OurAirports data dictionary](https://ourairports.com/help/data-dictionary.html) fetched 2026-10-31: column semantics.

### Secondary (MEDIUM confidence)
- `.planning/workstreams/v1-2/research/{STACK,ARCHITECTURE,PITFALLS}.md` (C17, M12; the mirror URL and the earlier `min(500, 0.45 x spacing)` suggestion, superseded by D-07).

### Tertiary (LOW confidence)
- None used for decisions. The France bounding box edges beyond the dump (A3) come from general geographic knowledge and should be re-checked by the owner or against an official outline.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new packages; everything is stdlib or existing).
- Architecture: HIGH (every integration point read in code; the shared-geofence-path landmine and the bbox-identity finding were reproduced).
- Catalogue numbers: HIGH (measured on the real dump); policy numbers A1-A3: MEDIUM.
- Pitfalls: HIGH for items 1-5, 9 (reproduced or read in code); MEDIUM for 8 and 10 (behavioural judgement).

**Research date:** 2026-10-31
**Valid until:** 2026-11-30 for code seams (Phases 54-56 edit companion files concurrently); the OurAirports counts are tied to the pinned snapshot and do not expire.
