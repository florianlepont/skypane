# Phase 68: Route sources sizing (D-26 comparison card, D-27 directory status)

Written 2026-11-18 for the owner's decision (D-31). Everything below is read from the code and the Phase 65 measurement; a number that could not be measured is marked **unknown**. No production code was changed.

## 1. What exists today

- **Lookup order** (`server/plane/enrich.py`, `_resolve_route_unrenamed`): the VRS standing data is asked first (`_vrs_route`, one file per callsign); adsbdb (`_lookup`) is asked only when VRS gives no leg at the watched airports. So adsbdb is never asked for a callsign VRS answered.
- **Outcome returned**: `resolve_route()` returns one of `fresh_hit`, `cache_hit`, `airline_only`, `manual`, `miss`. A VRS hit and an adsbdb hit both come back as `fresh_hit` or `cache_hit`: the directory that answered is not in the return value, not in `runway_events.route_source`, and not shown anywhere.
- **Cache**: VRS answers are cached under `vrs:<key>` in the device's `enrichment_cache` (hit 30 days, miss or unusable file 1 day); adsbdb under the callsign (same TTLs). adsbdb answers are also shared between devices through `SharedRouteTransport` (`server/plane/shared_route_cache.py`, one file in the state root). VRS has **no** shared cache: two devices that see the same new callsign each fetch the VRS file.
- **Failures leave no trace**: a transport exception, 429, 5xx or other non-404 4xx returns `None` without writing the cache and without counting anything (`_lookup`, `_vrs_lookup`). The next cycle simply asks again.
- **History database** (`server/history_db.py`): `runway_events.route_source` (TEXT), `poll_cycles`, `device_health`, `meta`, `wake_epochs`. There is **no `user_version`**: the schema is `CREATE TABLE IF NOT EXISTS` plus guarded `ALTER TABLE ADD COLUMN` (`_add_missing_runway_event_columns`, `_add_missing_wake_columns`). A new table or a new nullable column needs no migration step and survives a restore of an older backup (it is created empty on the next connect). The 68-12 plan text speaks of a `user_version` bump and a backfill: neither applies here.
- **Health page** (`companion/pages/health_page.py`, `companion/health_sections.py`): "Data sources" compares adsb.fi and adsb.lol (corroboration counts); "Flight identification" shows `route_source_counts` over 14 days (fresh, cache, airline only, manual, other). Nothing about adsbdb or VRS by name.
- **Poll budget**: `skypane-poll.timer` fires a oneshot every 30 s. One lookup is bounded by 8 s total plus a 5 s read timeout, so 13 s worst case per request (comment in `enrich.py`). A oneshot that is still running delays the next one.
- **Callers**: `poll_cycle.py` calls `resolve_route` in two places: `_enrich_current_flight` (the aircraft being shown) and `_unshown_route` (each aircraft dropped unseen). Any extra lookup applies to both.

## 2. Measured and unknown numbers

| Number | Value | Source |
|---|---|---|
| Flights where adsbdb and VRS both answered with different airport lists | 9 of 148 (VRS right in 7, adsbdb in 6, same leg at the watched airport in 4) | `65-ROUTE-SOURCES-MEASURE.md`, 2026-11-17 evening |
| Flights with no route from adsbdb alone / VRS alone / VRS then adsbdb | 22 / 7 / 1 of 148 | same |
| Evening-peak flight rate | about 18 flights per hour per airport (148 callsigned flights, 2 h, 4 airports) | same, derived |
| New callsigns per day at one frame (the lookup rate) | **unknown**: the live history database is not available here, and repeat callsigns (daily rotations) hit the 30-day cache | to measure on the VPS: `SELECT COUNT(DISTINCT callsign) FROM runway_events WHERE ts >= date('now','-7 day')` |
| Share of adsbdb requests that already happen today | **unknown**: adsbdb is now only the fallback, about 5 % of callsigned flights get no VRS route (7 of 148) plus the legs VRS lacks | to measure from the new counters |
| Latency of one lookup in normal conditions | **unknown** (only the 13 s bound is in the code) | to measure from the new counters (add a duration) |

Upper bound for the extra requests of option 1: at most one adsbdb request per distinct new callsign, since the 30-day hit and 1-day miss caches apply. That puts adsbdb back to the volume it had before VRS went first (one request per new callsign, 80 % found), not above it.

## 3. Option 1: comparison card (D-26)

What the owner sees: per recent aircraft, "same route", "only VRS", "only adsbdb", or "they differ" with both routes.

Server work:
- **Record which directory answered**: free. `_resolve_route_unrenamed` already knows which branch returned; expose it (a `directory` value from `resolve_route`, or a side-channel list). New nullable column `runway_events.route_directory` (`vrs` / `adsbdb` / `none`).
- **Record the other directory's answer**: not free. When VRS answered, adsbdb has to be asked too (the code never does), through the existing `_lookup` and `SharedRouteTransport` so devices share it. Store the other directory's leg in a second nullable column (`route_other` as `ORY-TLS` text) plus a verdict column (`route_compare`: `same`, `differ`, `only_vrs`, `only_adsbdb`, `neither`, NULL unknown).
- **Extra requests**: one adsbdb request per new callsign that VRS answered; none for cached callsigns. Also one for each dropped aircraft (`_unshown_route`). Volume per day: **unknown** (see section 2), bounded by the distinct new callsigns.
- **Poll cycle impact**: the request is serial in the oneshot: up to 13 s worst case more, and a VRS-hit cycle today makes 0 adsbdb calls. To keep the output and timing of the cycle unchanged the comparison must run after the panel is decided and written, with a lower timeout (for example 3 s, one attempt, no retry), and a failure must only leave the comparison NULL. Even so a slow adsbdb delays the next 30 s timer tick; a stricter form moves the comparison out of the poll path (a separate timer that fills in `route_compare` for rows whose compare is NULL). That is a second systemd unit (the deploy lists six): more work, no risk to the frame.
- **Terms**: adsbdb publishes no terms (`COMPLIANCE.md`: "used within reasonable bounds"); one request per new callsign is the volume it already had before PR #468. VRS is CC0 static files, unchanged. `COMPLIANCE.md` (adsbdb and VRS entries) must be updated.
- **History database**: two or three nullable columns added with the guarded `ALTER TABLE` pattern; no backfill is possible (the other directory's past answer is gone); old rows show "unknown" in the card. The export column lists (`_RUNWAY_EVENT_COLUMNS`, `history_db.py` line 706 area, `companion/test_export_debug_routes.py`) change.
- **Companion**: new card on Health (and a per-flight line on Flights, optional); route-source counts gain a directory split.

Files touched: `server/plane/enrich.py`, `server/poll_cycle.py`, `server/history_db.py`, `server/plane/shared_route_cache.py` (maybe), `companion/pages/health_page.py`, `companion/health_sections.py`, new `companion/pages/route_sources_card.py`, `companion/static/style-admin.css`, `companion/i18n_fr/health.py`, `COMPLIANCE.md`.
Phase 64-owned companion files touched: `health_page.py`, `health_sections.py`, `i18n_fr/health.py`.
Tests to add: `server/test_enrich.py`/`test_vrs_routes.py` (directory and compare outcome, timeout and failure leave NULL), `server/test_history_db*` (new columns, old database upgraded), a poll-cycle test that the output hash is unchanged with the compare on and with adsbdb timing out, `companion/test_health_route_sources.py`, a browser test (`test_browser_health_route_sources.py`), a French-fit check, export test update.
Risk to the live frame: medium for the inline form (adds a serial request to the 30 s oneshot), none for the separate-timer form (but a new unit).
Size: large (about 3 server files, 4 companion files, 6 test files, one deploy unit if separate).

## 4. Option 2: directory status (D-27)

What the owner sees: per directory (adsbdb, VRS): reachable or not, time of the last answer, share of failed lookups and share that found a route over the last 24 h.

Server work:
- **New counters**: a new table `route_lookup_stats` (`hour` TEXT, `directory` TEXT, `attempts`, `failures`, `found`, `not_found`, `last_answer_ts`, `last_failure_ts`; primary key `(hour, directory)`), created with `CREATE TABLE IF NOT EXISTS` in `init_schema`, upserted by the poll cycle. One row per directory per hour: about 48 rows a day, pruned like `prune_poll_cycles` (14 days, about 700 rows, a few tens of kilobytes). Restore: an older backup without the table gets it created empty; the card shows "no data yet" until lookups happen.
- **Where it is written**: the lookups happen in `enrich._lookup` and `_vrs_lookup`, which have no database access and return only `(route, from_cache)`. The outcome of each real network attempt (found, 404 or unusable, transient failure, time taken) has to leave them: a small `lookup_log` list passed into `resolve_route`, then written by `_record_history` inside the existing `write_batch`, in its own savepoint like the other optional writes (a counter fault must not stop the core commit). That changes the `resolve_route` signature (two call sites in `poll_cycle.py`, tests in `test_enrich.py` and `test_vrs_routes.py`). Cache hits are not attempts and are not counted.
- **Per device or fleet**: the status of a public service is the same for every device, but each device writes its own `history.db`. Per-device counters mean a fleet of several frames shows several partial views (adsbdb answers shared across devices are served from the shared file without a network call, so they must not count as attempts). Decision needed at build time; the cheapest is per device, counted where the real transport is called.
- **Honest limit**: adsbdb is only asked when VRS misses, so on a quiet frame its sample is thin (about 5 % of flights by the 2026-11-17 measure) and "reachable, last answer 3 h ago" may be simply "not asked since". The card must show the number of attempts beside the percentages, or it will say "healthy" on one lookup. Option 1 would raise the adsbdb sample to every new callsign.
- **Extra requests**: none. No new request, only counting. Poll cycle: one more upsert of at most two rows per cycle with lookups, inside the existing transaction; none on cycles that made no network lookup.
- **Terms**: nothing changes.
- **Companion**: a "Route directories" card on Health with empty, healthy and degraded states.

Files touched: `server/plane/enrich.py`, `server/poll_cycle.py`, `server/history_db.py`, `companion/pages/health_page.py`, `companion/health_sections.py`, new `companion/pages/route_sources_card.py`, `companion/static/style-admin.css`, `companion/i18n_fr/health.py`.
Phase 64-owned companion files touched: `health_page.py`, `health_sections.py`, `i18n_fr/health.py`.
Tests to add: counter upsert and prune, a transient failure counted and not cached, a savepoint fault not blocking the event row, hour roll-over, health card rendering in the three states, browser and French-fit tests.
Risk to the live frame: low (no new request; a guarded write; the displayed output cannot change).
Size: medium (3 server files, 3 companion files, 4 test files).

## 5. Option 3: reduced forms

**3a. Status plus "who answered" (recommended reduced form).** Option 2 in full, plus the free half of option 1: record which directory answered (`route_directory` column, no extra request) and show it in the recent flights list and in the route counts ("VRS", "adsbdb (VRS had none)", "none"). No same/differ verdict, no second request. It answers "which directory gave this route" and "are they healthy", and leaves the comparison as the one-off measurement already in `65-ROUTE-SOURCES-MEASURE.md` (9 of 148 differ).
Files touched: those of option 2, plus one nullable column in `history_db.py` and the Flights row. Request cost: none. Risk: low. Size: medium plus a small part.

**3b. Status only.** Option 2 alone (the plan's `status-only`). Cheapest, no new column.

**3c. Comparison only where the first directory missed**, the form named in the plan: it is empty by construction. Where VRS missed and adsbdb answered there is nothing to compare, only "only adsbdb", which 3a already gives for free. A real comparison needs the second request on VRS hits, so it cannot be cheaper than option 1; the only cheaper variants of that are a cap on requests per hour or the separate-timer form above, both still option 1 work.

## 6. Comparison

| | Extra requests | New storage | Touches poll path | Risk to frame | Size |
|---|---|---|---|---|---|
| Option 1 (card, D-26) | about 1 adsbdb per new callsign VRS answered (rate unknown) | 2 to 3 nullable columns | yes (inline), or a new timer | medium inline, none with timer | large |
| Option 2 (status, D-27) | none | 1 table, about 48 rows a day | counters write only | low | medium |
| Option 3a (status + who answered) | none | 1 table + 1 column | counters + column | low | medium |
| Option 1 + 2 (both, as asked) | as option 1 | as both | as option 1 | as option 1 | large plus |

## 7. Recommendation

Build **option 3a** (status plus who answered), no second request. It gives the owner both things asked in spirit (see the directory that answered, see whether each directory is healthy) at no extra load on adsbdb and no risk to the 30 s cycle. Keep the same/differ comparison for later: it needs a second request per new callsign or a separate timer, and the 2026-11-17 measure already says the two directories mostly agree (differ on 9 of 148, VRS better, and VRS now goes first). Revisit if the status shows VRS failing often.

OWNER-DECISION: (to be completed at the checkpoint with the date, the chosen option, the time window and exactly which of D-26 and D-27 plan 31 builds)
