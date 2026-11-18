# Phase 65: replay of the recorded sessions through the current code (plan 65-12)

Tool: `scripts/multi_site_replay.py` (tests: `scripts/test_multi_site_replay.py`). It rebuilds a scratch fleet with the same simulated devices and feeds the raw provider answers recorded by `multi_site_run.py` through the unchanged fleet cycle, in recorded order, with the clock set to each recorded time (the poll cycle's `now_s()` and the history timestamp, so the display queue pacing is replayed too). Routes come from the recorded adsbdb cache; a callsign not in it is a miss. No network, no live state.

Recorded with the code of the time; replayed with `main` after #457 (G-02) and #458 (H-02, H-01). Rows are matched by aircraft, runway and time to the second; a 30 s shift of one row (the replay's cycle clock differs from the live timer by up to a cycle) is not a change.

## Results

| Session | Rows recorded | Rows replayed | Changed rows | What the change is |
|---|---|---|---|---|
| Nantes morning (before G-02) | 25 | 25 | 7 + 3 shifted | the 8 routes without Nantes are gone (EZS1345 GVA>LRH, EZY9448 BFS>BRS, AFR27EP CFR>LYS, AFR74YT x2 ORY>BIA, VLG964 ATH>BCN, VLG965 ACE>BCN, TVF707 NCE>ORY, RYR6474 MRS>OZZ): the row keeps the airline only. EZY68PA, dropped unseen, now has NTE>LGW (H-01) |
| Nantes evening | 22 | 22 | 0 | none: the session already ran with G-02 |
| Lyon | 40 | 39 | 6 | six aircraft dropped unseen now have a direction and a route (RAM720P, AFR58KE, TAP472C, OCN7DS, DAH1080, HOP82CQ): H-01 |
| Roissy | 97 | 96 | 2 + 1 removed | KAL901 no longer drawn as `departing` after landing (H-02). SAS73C and FDX38, dropped unseen, now have a direction and a route (H-01) |
| Orly 02/20 | 18 | 18 | 0 | none |

Every aircraft found in the recorded session is found in the replay; no aircraft appears or disappears except KAL901's false row.

## Finding H-05 (new, from the replay): a wrong vertical-rate sign in the air still flips the state

- Evidence [observed]: UAE7V (A380) at Roissy, 18:20:26 to 18:21:57 UTC. Altitude 1450, 1325, **1000 ft** with the reported vertical rate -640, -704, then **+608 ft/min** at 1000 ft (the altitude fell 325 ft in 30 s, so the sign is wrong), then on the ground at +608. The replay with the H-02 fix still draws `departing` at 18:21:26, because the aircraft is airborne at that sample (`on_ground` false); H-02 only covers the ground.
- Cause [hypothesis, supported by the altitude]: a bad barometric rate sample near the ground. The first-seen altitude of the aircraft (1450 ft) is 450 ft above its current altitude, so the altitude trend says `arriving` while the rate says `departing`.
- Proposal (needs the owner's agreement, D-04): a held state is not flipped by a vertical rate that the altitude trend since the first sighting contradicts. Test first, from the recorded UAE7V sequence; the KAL901 and take-off tests stay.
- Not started.

## Not replayed
Lyon, Roissy and Orly sessions recorded after the fixes of #458 could only show that the fixes do not move anything else; the morning Nantes session and the Roissy session carry the evidence. The Orly runway 3 traffic (live frame) has no recorded payloads in this repository.
