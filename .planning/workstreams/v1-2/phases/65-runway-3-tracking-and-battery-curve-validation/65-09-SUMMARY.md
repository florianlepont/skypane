---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 09
subsystem: tracking-validation
tags: [trk-02, scratch-fleet, airports, smoke-cycle]
requires: ["65-08"]
provides:
  - "Owner's airport choice recorded as D-11 (LFRS, LFLL, LFPG)"
  - "Scratch fleet of nine simulated devices with computed geometry and zones"
  - "One-cycle smoke result and live-frame status comparison"
affects: [65-10, 65-11, 65-12]
key-files:
  created:
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-TRACKING-MULTI-SETUP.md
  modified:
    - .planning/workstreams/v1-2/phases/65-runway-3-tracking-and-battery-curve-validation/65-CONTEXT.md
decisions:
  - "D-11: three airports (Nantes LFRS simple case, Lyon LFLL and Paris-Charles de Gaulle LFPG stress cases), one session each, at least 3 arrivals and 3 departures per runway or airport, in that order"
requirements: [TRK-02]
status: complete
completed: 2026-11-15
---

# Phase 65 Plan 09: Multi-airport setup Summary

The owner chose Nantes, Lyon and Roissy; a scratch fleet of nine simulated devices (Orly 06/24 and 02/20 plus every runway of the three airports) exists outside the repository, a one-cycle smoke run polled each new airport in its own zone, and the live frame's `device` object is unchanged.

## Owner decision

D-11 added to 65-CONTEXT.md, quoted in 65-TRACKING-MULTI-SETUP.md. It replaced the plan's short list and decision checkpoint, because the owner named the airports in chat.

## Devices (scratch root `/tmp/claude-0/-home-user-skypane/e7b2962d-137b-5976-bbb9-b2fc84099ae6/scratchpad/p65_09/root`)

| Id | Name | Airport and runway | Legacy or display id |
|----|------|--------------------|----------------------|
| d_563098f4 | ORY-0624 | LFPO 06/24 | 06-24 |
| d_a08d342a | ORY-0220 | LFPO 02/20 | 02-20 |
| d_cd843e41 | NTE-0321 | LFRS 03/21 | LFRS:03/21 |
| d_fbcee383 | LYS-17L | LFLL 17L/35R | LFLL:17L/35R |
| d_255a9754 | LYS-17R | LFLL 17R/35L | LFLL:17R/35L |
| d_8213849d | CDG-08L | LFPG 08L/26R | LFPG:08L/26R |
| d_f7b8d7e9 | CDG-08R | LFPG 08R/26L | LFPG:08R/26L |
| d_ecf8e497 | CDG-09L | LFPG 09L/27R | LFPG:09L/27R |
| d_b06bb65a | CDG-09R | LFPG 09R/27L | LFPG:09R/27L |

Geometry: Lyon runway spacing 349 m, Roissy pairs 387 m and 384 m (pairs 3 km or more apart), corridors almost touching in every parallel pair. Every zone is radius 5.0 NM centred on the airport reference point (Orly's frozen legacy centre 48.7233, 2.3794).

## Smoke cycle

- Full root with fake fetcher (no network): 9 ok, 1 held (the root's live row), 4 zones, 4 fetches, Orly devices share one.
- Live, on a separate scratch root with one device per new airport: ok=3 held=1 zones=3 requests=6 (adsb.fi and adsb.lol each answered for all three zones, no failures), no aircraft in any corridor at 22:02Z.

## Live-frame comparison

One read-only GET of `/api/export/status`: `device` object equals `data/status_baseline_trk02.json`.

## Deviations from Plan

**1. [Owner decision] Short list and checkpoint replaced by D-11.** Task 1's candidate table was reduced to the geometry of the chosen airports and the checkpoint resolved by the owner's chat message. One simulated device per runway of Lyon and Roissy instead of one per airport (same zone, no extra request).

**2. [Request cap] Live smoke on a separate three-device root.** The full root has four zones, so a live cycle on it would have made four zone fetches; the owner allowed about three. The four-zone planning was verified with a fake fetcher and the live smoke ran on a root with the three new airports only.

No source file changed. No code added, so ruff and the guard scripts had nothing new to check.

## Known Stubs

None.

## Self-Check: PASSED
