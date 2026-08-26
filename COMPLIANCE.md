# Third-Party Data Source Compliance

This document states, per third-party data source this project actually
reaches (or was researched and deliberately did **not** end up reaching),
what its published terms require and what this repository does about it.
It uses the same per-source shape `server/assets/fonts/VENDOR.md` and
`server/assets/icons/VENDOR.md` already establish for vendored assets:
source, upstream link, the date the terms were checked, what the terms
require, and a verdict.

Five sources are covered, not the three originally scoped by D-14 —
`server/plane/enrich.py` reaches a fourth aggregator in production
(adsbdb.com) that predates this document, and leaving it out would make
this document incomplete on the day it ships.

Every behavioural claim below (request cadence, caching, what is and is
not republished) is grounded in the file that implements it, named
explicitly, so a reader can check the code rather than trust this
document.

---

## adsb.fi

- **Used in shipped code:** Yes — secondary ADS-B aggregator, queried by
  `server/plane/detect.py` (provider key `adsbfi`, endpoint
  `https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}`).
- **Upstream:** https://adsb.fi
- **Terms checked:** 2026-08-26 (fetched directly during this phase's
  research).
- **What the terms require:** adsb.fi's own README states that a user of
  their data "must cite adsb.fi and include a link to our home page."
- **Verdict — citation, in full, satisfying the requirement:**

  > This project uses real-time ADS-B aircraft position data from
  > [adsb.fi](https://adsb.fi) as a secondary aggregator source.

  The same citation also appears in `README.md`'s Data Sources section,
  where a visitor actually reads it — this document alone would satisfy
  the letter of the requirement but not its intent, since almost nobody
  reads a repository's compliance document before its README.
- **Status:** requirement met, citation present in two places.

## airplanes.live

- **Used in shipped code:** Yes — primary ADS-B aggregator, queried first
  by `server/plane/detect.py` (provider key `airplaneslive`, endpoint
  `https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}`).
- **Upstream:** https://airplanes.live (attribution/redistribution terms
  documented at `https://airplanes.live/api-guide/`).
- **Terms checked:** attempted 2026-08-26 — the `/api-guide/` page
  returned **HTTP 403** on two independent automated fetch attempts this
  phase's research session made, and again on a third attempt made
  during this plan's execution. This looks like bot-detection rather than
  a real access restriction, but it means the exact terms text has not
  been read by this project, only characterized by secondary sources
  (multiple search results describing the API as "educational and
  non-commercial purposes only," 1 req/s rate limit on the
  ADSB-One-compatible endpoint).
- **What the terms require:** **unconfirmed.** No terms are quoted here
  because none have actually been read — quoting unread terms would be
  worse than stating plainly that they haven't been read.
- **Verdict — open item, with a named route to closure:**
  - In the interim, this project extends the same courtesy attribution
    given to adsb.fi — see `README.md`'s Data Sources section — and
    labels it explicitly as a good-faith attribution pending confirmation
    of the actual requirement, not a claim that this satisfies a
    confirmed term.
  - Route to closure: a manual read of `https://airplanes.live/api-guide/`
    in a real browser (automated fetch is blocked), and/or the reply to a
    clarification email the developer has already sent to airplanes.live
    about commercial-use terms. Either one should resolve this item;
    revisit and update this section once either lands.
- **Status: OPEN.** This is the one source in this document whose terms
  status is unconfirmed.

## adsbdb.com

- **Used in shipped code:** Yes — callsign/airline/route enrichment,
  queried by `server/plane/enrich.py`'s `lookup_route()` /
  `default_transport()` against `https://api.adsbdb.com/v0/callsign/{callsign}`.
- **Upstream:** https://www.adsbdb.com
- **Terms checked:** 2026-08-26 — adsbdb is documented (in
  `server/plane/enrich.py`'s own module docstring, informed by
  02-RESEARCH.md) as a free, unauthenticated, crowdsourced service with no
  documented rate limit.
- **What the terms require:** no explicit attribution or redistribution
  clause was found published for this API; it is treated as an
  unauthenticated public lookup service, used only to enrich data this
  project already holds (a callsign it detected itself), not to
  republish adsbdb's own dataset.
- **Request pattern:** one lookup per newly-seen callsign only. Both hits
  and misses are cached persistently (`enrich.py`'s `lookup_route()`,
  keyed by normalised callsign, capped at `CACHE_MAX_ENTRIES = 300` and
  bounded by `trim_cache()`) — a callsign already seen is never
  re-queried, which is the behaviour that keeps request volume low
  (02-RESEARCH.md: tens to low hundreds of enrichment calls/day for this
  airport's traffic, live-verified at a 52.6% real-world hit rate).
- **Verdict:** used within the bounds of what a free, unauthenticated,
  crowdsourced lookup service reasonably expects — low request volume,
  no redistribution of its dataset, self-identifying `User-Agent` string
  (`enrich.py`'s `USER_AGENT` constant) naming this project and pointing
  back at `server/README.md`.
- **Status:** requirement (none explicit) met; no open item.

## PRIM / Île-de-France Mobilités

- **Used in shipped code:** **No.** This project's v1 ships a single
  plane-only view; the RER (Orly-Ville) view PRIM was researched for is
  explicitly deferred to v2 (`.planning/REQUIREMENTS.md`, RER-01/02/03,
  "Deferred 2026-08-11 — user-requested scope reduction so v1 ships
  single-view (plane-only)").
- **Verification:** a case-insensitive grep for `prim`, `iledefrance`, and
  the platform's own naming across every `.py` file under `server/` and
  `stub-server/` returns zero matches (run 2026-08-26, this session:
  `grep -rniE 'prim|iledefrance|aerodatabox' server/ stub-server/ --include='*.py'`
  — no output, confirming none of the three names appear anywhere in
  shipped code, PRIM included).
- **Verdict:** PRIM/IDFM's terms (including its CGU republication clause,
  which could not be independently fetched during research — two
  candidate URLs also returned 403) are genuinely immaterial to this v1
  repository, because nothing in shipped code calls the platform.
- **Status:** not used, terms not applicable to v1. **Must be revisited
  when v2 planning starts** — do not assume this "not applicable"
  determination still holds once RER-01/02/03 are picked back up; PRIM's
  SIRI Lite quota figures are themselves only community-sourced as of
  this writing (see `.planning/STATE.md` Blockers/Concerns) and should be
  re-verified against the live PRIM account dashboard at that time.

## AeroDataBox

- **Used in shipped code:** **No.** Early planning considered AeroDataBox
  (Airport FIDS, schedule-based) as the flight-data source; this was
  reversed during scoping in favour of the local geofenced ADS-B
  aggregation approach `server/plane/detect.py` actually implements (see
  `.planning/PROJECT.md`'s Alternatives Considered / What NOT to Use —
  local ADS-B receiver/aggregators chosen over public
  flight-data/schedule APIs).
- **Verification:** same grep as the PRIM entry above
  (`grep -rniE 'prim|iledefrance|aerodatabox' server/ stub-server/ --include='*.py'`)
  returns zero matches for `aerodatabox`.
- **Verdict:** no AeroDataBox API key was ever provisioned, and no request
  to any AeroDataBox endpoint is ever made by shipped code. Its terms are
  not applicable.
- **Status:** not used, no open item.

---

## Runtime behaviour vs. the aggregators' constraints

- **Poll cadence:** `server/poll_loop.py` runs on a 30-second cadence
  (`server/README.md`'s "Poll cadence" section), issuing at most one
  aggregator call per cycle per provider it tries. Both aggregators
  document a 1 request/second limit; `server/plane/detect.py`'s
  `MIN_SECONDS_BETWEEN_CALLS = 1.1` additionally throttles the fallback
  call to the second provider within a single poll cycle, so even a
  poll that tries both providers stays comfortably inside their stated
  limit.
- **No raw aggregator data is republished.** What this project serves to
  the device is a rendered panel image (`server/plane/render.py`)
  derived from a single selected flight
  (`server/plane/detect.py`'s `select_runway3_aircraft()`) — not the
  aggregators' JSON responses, and not a bulk feed or dataset built from
  their data.
- **Enrichment load is minimized by caching.** `server/plane/enrich.py`'s
  persistent hit-and-miss cache (`lookup_route()`, `trim_cache()`) means
  a given callsign is queried against adsbdb at most once for the
  lifetime of the cache, not once per poll cycle.

## Status table

| Source | Used in shipped code | Terms status | Open action |
|---|---|---|---|
| adsb.fi | Yes | Confirmed (direct fetch) | None — citation present in this document and `README.md` |
| airplanes.live | Yes | **Unconfirmed** (403 on automated fetch) | **OPEN** — manual browser read of `/api-guide/`, and/or pending clarification email reply |
| adsbdb.com | Yes | Confirmed (no explicit terms published; used within reasonable bounds) | None |
| PRIM / Île-de-France Mobilités | No | Not applicable (unused in v1) | Revisit at v2 planning, when RER-01/02/03 are picked back up |
| AeroDataBox | No | Not applicable (unused) | None |

Exactly one row above is marked open: **airplanes.live**.
