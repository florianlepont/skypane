# Third-Party Data Source Compliance

This document states, per third-party data source this project actually
reaches (or was researched and deliberately did **not** end up reaching),
what its published terms require and what this repository does about it.
It uses the same per-source shape `server/assets/fonts/VENDOR.md` and
`server/assets/icons/VENDOR.md` already establish for vendored assets:
source, upstream link, the date the terms were checked, what the terms
require, and a verdict.

Six sources are covered, not the three originally scoped by D-14 —
`server/plane/enrich.py` reaches a fourth aggregator in production
(adsbdb.com) that predates this document, `server/plane/detect.py` gained
a fifth (adsb.lol, 2026-08-27) as a second default ADS-B source, and
leaving either out would make this document incomplete on the day it
ships.

Every behavioural claim below (request cadence, caching, what is and is
not republished) is grounded in the file that implements it, named
explicitly, so a reader can check the code rather than trust this
document.

---

## adsb.fi

- **Used in shipped code:** Yes — the first-queried of two default ADS-B
  aggregators an automated poll queries, via `server/plane/detect.py`
  (provider key `adsbfi`, endpoint
  `https://opendata.adsb.fi/api/v2/lat/{lat}/lon/{lon}/dist/{dist}`).
- **Upstream:** https://adsb.fi
- **Terms checked:** 2026-08-26 (fetched directly during this phase's
  research).
- **What the terms require:** adsb.fi's own README states that a user of
  their data "must cite adsb.fi and include a link to our home page."
- **Verdict — citation, in full, satisfying the requirement:**

  > This project uses real-time ADS-B aircraft position data from
  > [adsb.fi](https://adsb.fi), queried first of two default aggregator
  > sources by every automated poll as of 2026-08-27.

  The same citation sentence also appears in `README.md`'s Data Sources
  section, where a visitor actually reads it — this document alone would
  satisfy the letter of the requirement but not its intent, since almost
  nobody reads a repository's compliance document before its README. Both
  places must agree; if one is ever edited, update the other in the same
  change.
- **Status:** requirement met, citation present in two places.

## adsb.lol

- **Used in shipped code:** Yes — the second default ADS-B aggregator an
  automated poll queries, right after adsb.fi, via `server/plane/detect.py`
  (provider key `adsblol`, endpoint
  `https://api.adsb.lol/v2/point/{lat}/{lon}/{dist}`).
- **Upstream:** https://adsb.lol
- **Terms checked:** 2026-08-27 (both the endpoint and the licence/privacy
  page verified live the same day, during this task's research).
- **What the terms require:** adsb.lol's own licence/privacy page
  publishes its data under **CC0** — no attribution is contractually
  required.
- **Credit-by-choice, not a requirement:** this project credits adsb.lol
  in `README.md`'s Data Sources section anyway, alongside adsb.fi's
  contractually-required citation, so a reader is not left to guess which
  credit is a term and which is a courtesy. Say it plainly here: crediting
  adsb.lol is a house-style consistency choice, not something its CC0
  licence obligates.
- **Sustainability caveat — read this as a real, disclosed risk, not a
  formality:** no API key is required to query adsb.lol today, **but
  adsb.lol's own upstream documentation pre-announces that a
  feeder-contributed API key may become required in future.** That is the
  same volunteer-funding pressure that closed airplanes.live's free tier
  the same day this second source was added — see the airplanes.live
  entry immediately below for the worked example of what happens when
  that pressure resolves against a project like this one.
- **Verdict:** adsb.lol is recorded here as a **known-temporary** second
  source, not a settled permanent guarantee. The code already degrades
  gracefully if it ever starts refusing requests:
  `poll_current_aircraft()` treats an unreachable adsb.lol as a
  single-source, uncorroborated poll rather than suppressing the display —
  proven by `server/test_plane_detection.py` check 27 ("poll_current_
  aircraft (default order): adsb.lol unreachable degrades to
  single-source, not suppressed").
- **Status:** requirement (CC0 credit-by-choice) met; known-temporary,
  watched for a future key requirement, no open action today.

## airplanes.live

- **Used in shipped code:** present in the code, but unreached by the
  default poll path. `server/plane/detect.py` retains the `airplaneslive`
  provider entry (endpoint
  `https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}`) for explicit
  `--provider` use only — by a feeder operator, sponsor, or licensee — and
  it is never queried by an automated poll cycle.
- **Upstream:** https://airplanes.live (attribution/redistribution terms
  documented at `https://airplanes.live/api-guide/`).
- **Terms checked:** attempted 2026-08-26 — the `/api-guide/` page
  returned **HTTP 403** on two independent automated fetch attempts this
  phase's research session made, and again on a third attempt made during
  an earlier plan's execution.
- **The 2026-08-27 reply:** a reply to the clarification email the
  developer had sent airplanes.live about commercial-use terms arrived
  this day. In substance: airplanes.live discontinued its free API tier
  for cost-sustainability reasons, and access is now gated behind one of
  three routes — running an ADS-B feeder, paying for a sponsorship, or
  holding a commercial licence for any revenue-generating use.
- **Live verification, same day:** a GET against the exact endpoint
  template `server/plane/detect.py` uses in production
  (`https://api.airplanes.live/v2/point/{lat}/{lon}/{dist}`) returned
  **HTTP 403**, while the adsb.fi endpoint in the same file returned
  **HTTP 200**.
- **What the terms require:** still not directly read — the `/api-guide/`
  page remains unreachable by automated fetch — but the 2026-08-27 reply
  makes the free-tier access requirement moot for this project's purposes:
  a feeder, a paid sponsorship, and a commercial licence were all
  considered and declined (`.planning/PROJECT.md` Key Decisions).
- **Verdict — resolved:** adsb.fi is promoted to default provider (later
  the same day joined by adsb.lol as a second default source — see the
  adsb.lol entry above); the `airplaneslive` provider entry stays in
  `detect.py` for explicit `--provider` use by a feeder operator, sponsor,
  or licensee, and is not queried by any automated poll. Because shipped
  behaviour no longer reaches the service, its terms are no longer a
  blocker on anything this repository does — and the item that was waiting
  on a clarification-email reply has now received one.
- **Status: resolved (2026-08-27).** No longer an open item — see the
  demotion above.

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
  (`server/README.md`'s "Poll cadence" section). A production cycle now
  issues **two** aggregator requests per 30-second cycle — adsb.fi, then
  adsb.lol, per `DEFAULT_PROVIDER_ORDER` — separated by
  `server/plane/detect.py`'s `MIN_SECONDS_BETWEEN_CALLS = 1.1` second
  sleep. Per provider, that is still one request every 30 seconds, well
  inside either aggregator's documented 1 request/second limit; the
  aggregate (two requests, 1.1s apart, once every 30 seconds) sits
  comfortably inside that ceiling too. An explicit `--provider all`
  invocation additionally reaches a third provider, airplanes.live, adding
  one more 1.1s-spaced request to the same cycle — still well inside the
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
| adsb.fi | Yes — first of two default providers | Confirmed (direct fetch) | None — citation present in this document and `README.md` |
| adsb.lol | Yes — second of two default providers | Confirmed (direct fetch, CC0) | None — known-temporary (future feeder-contributed API key disclosed upstream), watched, not an open action |
| airplanes.live | Present in code, not queried by default | Resolved (2026-08-27 reply + same-day live 403) | None — demoted to explicit `--provider` opt-in only |
| adsbdb.com | Yes | Confirmed (no explicit terms published; used within reasonable bounds) | None |
| PRIM / Île-de-France Mobilités | No | Not applicable (unused in v1) | Revisit at v2 planning, when RER-01/02/03 are picked back up |
| AeroDataBox | No | Not applicable (unused) | None |

No row above is marked open. PRIM's "revisit at v2 planning" note is a
forward-looking reminder, not an outstanding item.
