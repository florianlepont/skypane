# Phase 65 tracking: live comparison with Flightradar24

Date: 2026-11-15, 15:30 to 15:50 UTC (16:30 to 16:50 in Paris). The owner watched Flightradar24 on ORY runway 3 and named each aircraft, its origin and the touch-down time. The server side is read from `GET /api/export/{status,poll-cycles,flights}` of production. All traffic was arrivals; no departure passed.

Labels: **[observed]** = read from the export or reported by the owner; **[hypothesis]** = interpretation.

| Aircraft | Owner (Flightradar24) | Detected (UTC) | On the frame | Route on the frame | Route (adsbdb) |
|---|---|---|---|---|---|
| DAH1108 | arrival | 15:33:16 | yes | QSF > ORY | correct |
| VLG2VN | arrival, landed on runway 3 | 15:35:51 | no, dropped 15:38:24 | none | not tested |
| TVF18BM | arrival, from Beirut | 15:38:24 | yes | none | adsbdb: unknown callsign |
| EJU69MC | arrival, from Milan | 15:40:28 | no, dropped 15:43:34 | none | adsbdb: CAG > BER (wrong) |
| WMT3840 | arrival, from Rome | 15:44:04 | yes | FCO > ORY | correct |
| AFR97SV | arrival, from Calvi | 15:46:39 | no, dropped 15:49:14 | none | correct (CLY > ORY) |
| TVF42MK | arrival, from Palermo | 15:48:42 | yes (15:49:14) | PMO > ORY | correct |
| TVF90TN | not confirmed by the owner | 15:30:42 | no, dropped 15:33:16 | none | not tested |

Open: the owner wrote "DAH1109 arrived" at 15:35:34 UTC. The server never detected a DAH1109 (not in `poll_cycles` since 12:13 UTC, not in `runway_events`). Either the owner meant DAH1108, or an aircraft was missed. Unresolved.

Totals [observed]: 7 aircraft confirmed on runway 3 by the owner, 7 detected, 0 detections missed (DAH1109 aside). 4 shown, 3 detected and dropped before being drawn. Each drop happened on the first cycle more than 150 s after the aircraft was first seen (153 s, 186 s, 155 s; TVF90TN 154 s). Each aircraft was detected before touching down (detection 30 to 45 s before the touch-down reported by the owner).
