# Route sources: sizing and owner decision (D-26, D-27, D-31)

Date: 2026-11-18. Mockup: `68-MOCKUP-route-sources.html` (built on the approved Health page).

## Where it lives
The Health page of a frame (administrators only), in the Server and data group, after Identification. Files touched when built: `server/history_db.py` (schema), `server/plane/enrich.py` and `server/poll_cycle.py` (writes), `companion/health_sections.py` and `companion/pages/health_page.py` (cards), `companion/i18n_fr/health.py` (French), baselines. Phase 64 companion changes are already on main, so there is no open-PR conflict.

## Levels
| Level | What the owner sees | Server and database change | Extra network requests | Size |
|---|---|---|---|---|
| A. Status (D-27) | Per directory (VRS standing data, adsbdb): reachable or not, last answer, lookups in the last 24 h, share that found a route, share that failed | New table in the history database (one row per lookup that really goes to the network: time, directory, outcome found / none / failed), schema version bump, written from the lookup code; a failed transient lookup is recorded there (today it is not recorded) | None (cache hits are not recorded) | about one plan |
| B. A plus "answered by" | A bar: flights of the last 7 days answered by the first directory or by the fallback | One more recorded value per flight saying which directory answered | None | about one small plan |
| C. B plus comparison per aircraft (D-26) | Agreement share, same / only one / different, last aircraft with both answers | Both answers stored per new callsign | One more request per new callsign (empty answers cached one day, found ones one month); touches the code that chooses the route drawn on the frame, which must not change | two to three plans, the most tests |

Measured on 2026-11-17 (`65-ROUTE-SOURCES-MEASURE.md`): the two directories differ on 9 of 148 flights and VRS is right in 7 of them; the shipped order (VRS first, adsbdb as fallback) gives the right route for 94 % of flights.

## OWNER-DECISION (2026-11-18)
Levels **A and B** are built (status of each directory, and who answered each flight). Level **C** (comparison per aircraft, extra request per new callsign) is **not** built. No extra network request is added; the route chosen for the frame and the golden render hashes do not change; the history database gets a schema bump that must migrate existing frames' databases without loss.
