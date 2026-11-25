# SkyPane airline editor: final aircraft shape families (proposal)

Research only. No repository file was modified. Date of research: 2026-11-24.

## 0. How to read this

* A family = one silhouette image slot per airline (`{airline}-{slug}.png`). Slugs are a-z0-9 only.
* Production data: 43 distinct type codes + 50 sightings with no type = 26 537 sightings (the brief says "44 codes"; the 44th is the "no type" bucket, the listed codes sum to 26 487). Percentages below are of 26 537.
* Verification tags per code:
  * **[W]** present in the Wikipedia "List of aircraft type designators" table (fetched; it is a partial copy of ICAO Doc 8643): https://en.wikipedia.org/wiki/List_of_aircraft_type_designators
  * **[E]** Eurocontrol ATC performance DB, fetched: https://learningzone.eurocontrol.int/ilp/customs/ATCPFDB/details.aspx?ICAO=BE9L (only BE9L was confirmed there; EC45 and FA8X returned "no data").
  * **[T]** tar1090-db aircraft database (registry-derived ADS-B DB, downloaded and parsed: https://github.com/wiedehopf/tar1090-db, branch `csv`, `aircraft.csv.gz`; model name = most common description of aircraft carrying that code, with the number of registered airframes). Secondary source, not ICAO itself.
  * **[R]** RocketRoute page, fetched: https://www.rocketroute.com/aircraft/dassault-falcon-8x (FA8X).
  * **[?]** unverified: no fetched source lists it.
* ICAO's own Doc 8643 search/PDF returned HTTP 403 from this environment, so no code is verified straight against the ICAO database. Every one of the 43 production codes is verified [W] or [T] (details in section 6).
* Operator facts used for "France-plausible": Orly airline/destination list (https://en.wikipedia.org/wiki/Paris_Orly_Airport, fetched), Twin Jet fleet = 13 x Beechcraft 1900D (https://en.wikipedia.org/wiki/Twin_Jet, fetched), Air France fleet (https://en.wikipedia.org/wiki/Air_France, fetched: A220-300, A320 family, A330, A350, 777, 787, 777F; Hop/CRJ regional), plus the repo's own French reference lists (phase 65 `reference-lists/*.txt`, `route-sources-*/*_fr24.txt`, live payloads), which add: B77L, B77W, B763, B752, A388, CRJX, PC21, C56X, GL5T, C25A, E295, A318, B733.

## 1. Bugs found in the current mapping (fixes, not new families)

1. **BE9L is mapped to `beechcraft1900d` but is the Beechcraft King Air 90** [E] [T] ("Hawker Beechcraft King Air 90", 1 663 airframes). The Beech 1900 is **B190** [W] ("Beechcraft 1900"), and B190 is the type Twin Jet flies (13 aircraft). B190 is currently unmapped even though it has 79 production sightings (0.30%). Fix: `B190 -> beechcraft1900d`; `BE9L -> kingair`. `_TYPE_DISPLAY_LABELS["BE9L"]` must stop saying "Beechcraft 1900D" (-> "King Air 90"), and add `B190: "Beechcraft 1900D"`.
2. **E135/E145 are in `embraer` (E-Jet) but are a different airframe** (ERJ: T-tail, two rear fuselage engines; E-Jet: wing-mounted engines). E145 = 127 production sightings (0.48%), the 6th most common type. Fix: new `erj145` slot for E135/E145/E45X; `embraer` keeps only E170/E75L/E75S/E190/E195/E290/E295.
3. **E35L = Embraer Legacy 600/650** [W] (Embraer description in [T]: "EMB-135 Legacy"): it is an ERJ-135 airframe sold as a business jet. Put it in `erj145` (same silhouette), not in a business-jet slot.
4. `B731` (737-100) is in the existing bucket but appears in neither [W] nor [T]: unverified, harmless.
5. Missing mapping for 20+ codes already seen in production (B788 B789 BCS1 BCS3 B77x B748 B764 CRJX ...): fixed by the new families below.

## 2. Family table (recommended final list)

Columns: slug | FR label | EN label | status | prod codes / sightings (share of 26 537) | tier.
Tier 1 = needed for 99%+ of production, Tier 2 = airliners plausible at French airports, Tier 3 = business/turboprop/helicopter/GA that a French ADS-B receiver sees, Tier 4 = complete set extras.

| # | slug | FR label | EN label | Status | Prod codes / sightings | Tier |
|---|------|----------|----------|--------|------------------------|------|
| 1 | a320 | Airbus A320 (famille) | Airbus A320 family | EXTENSION (+A19N) | 5 / 14 428 (54.4%) | existing |
| 2 | b737 | Boeing 737 | Boeing 737 | unchanged | 7 / 9 101 (34.3%) | existing |
| 3 | a350 | Airbus A350 | Airbus A350 | unchanged (A35K stays variant slot `a350-1000`) | 2 / 1 039 (3.9%) | existing |
| 4 | a330 | Airbus A330 | Airbus A330 | EXTENSION (+A338) | 3 / 1 031 (3.9%) | existing |
| 5 | atr72 | ATR 42 / 72 | ATR 42 / 72 | unchanged (see question 3) | 3 / 392 (1.5%) | existing |
| 6 | erj145 | Embraer ERJ 135/145 | Embraer ERJ 135/145 | NEW + FIX (split from `embraer`, absorbs E35L) | 2 / 132 (0.50%) | 1 |
| 7 | b787 | Boeing 787 | Boeing 787 | NEW | 2 / 89 (0.34%) | 1 |
| 8 | a220 | Airbus A220 | Airbus A220 | NEW | 2 / 87 (0.33%) | 1 |
| 9 | beechcraft1900d | Beechcraft 1900D | Beechcraft 1900D | FIX (B190 in, BE9L out) | 1 / 79 (0.30%) | existing |
| 10 | embraer | Embraer E-Jet | Embraer E-Jet | FIX (E135/E145 out) | 2 / 64 (0.24%) | existing |
| 11 | b777 | Boeing 777 | Boeing 777 | NEW | 3 / 25 (0.09%) | 1 (4th new) |
| 12 | b747 | Boeing 747 | Boeing 747 | NEW | 1 / 6 (0.02%) | 2 |
| 13 | bizjetlarge | Jet d'affaires gros porteur (Gulfstream / Global) | Large business jet (Gulfstream / Global) | NEW | 3 / 5 (0.02%) | 3 |
| 14 | bizjet | Jet d'affaires (Citation, Learjet, Challenger...) | Business jet (Citation, Learjet, Challenger...) | NEW | 2 / 3 (0.01%) | 3 |
| 15 | falcon | Dassault Falcon | Dassault Falcon | NEW | 1 / 2 (0.01%) | 3 |
| 16 | crj | Bombardier CRJ | Bombardier CRJ | NEW | 1 / 1 | 2 |
| 17 | b767 | Boeing 767 | Boeing 767 | NEW | 1 / 1 | 2 |
| 18 | helicopter | Helicoptere (moyen, bimoteur) | Helicopter (medium twin) | NEW | 1 / 1 (EC45) | 3 |
| 19 | gahigh | Avion leger, aile haute (Cessna) | Light plane, high wing (Cessna) | NEW | 1 / 1 (C172) | 3 |
| 20 | kingair | Beechcraft King Air | Beechcraft King Air | NEW (BE9L moved here) | 0 / 0 | 3 |
| 21 | b757 | Boeing 757 | Boeing 757 | NEW | 0 / 0 | 2 |
| 22 | a380 | Airbus A380 | Airbus A380 | NEW | 0 / 0 | 2 |
| 23 | a300 | Airbus A300 / A310 | Airbus A300 / A310 | NEW | 0 / 0 | 2 |
| 24 | pc12 | Turbopropulseur monomoteur (PC-12, TBM) | Single turboprop (PC-12, TBM) | NEW | 0 / 0 | 3 |
| 25 | a340 | Airbus A340 | Airbus A340 | NEW | 0 / 0 | 4 |
| 26 | dash8 | De Havilland Dash 8 / Q400 | De Havilland Dash 8 / Q400 | NEW | 0 / 0 | 4 |
| 27 | md80 | MD-80 / DC-9 / 717 | MD-80 / DC-9 / 717 | NEW | 0 / 0 | 4 |
| 28 | md11 | MD-11 / DC-10 (trireacteur) | MD-11 / DC-10 (trijet) | NEW | 0 / 0 | 4 |
| 29 | beluga | Airbus Beluga | Airbus Beluga | NEW | 0 / 0 | 4 |
| 30 | caravan | Cessna Caravan | Cessna Caravan | NEW | 0 / 0 | 4 |
| 31 | helilight | Helicoptere leger | Light helicopter | NEW | 0 / 0 | 4 |
| 32 | galow | Avion leger, aile basse | Light plane, low wing | NEW | 0 / 0 | 4 |
| 33 | gatwin | Bimoteur leger | Light twin piston | NEW | 0 / 0 | 4 |
| 34 | a400m | Airbus A400M | Airbus A400M | NEW (military) | 0 / 0 | 4 |
| 35 | c130 | Lockheed C-130 Hercules | Lockheed C-130 Hercules | NEW (military) | 0 / 0 | 4 |

Total = 7 existing slots (+ variant `a350-1000`) + 28 new = 35 families. All 43 production codes are covered by rows 1-11, 13-16, 18, 19 (no code is left over).

## 3. Members of every family (code - model [verification])

**a320** (existing, +A19N): A318 Airbus A318 [W]; A319 A319 [W]; A19N A319neo [W]; A320 A320 [W]; A321 A321 [W]; A20N A320neo [W]; A21N A321neo/LR/XLR [W]. Prod: A20N 6718, A320 6065, A21N 740, A319 606, A321 299. Coarse on purpose: the four sizes share nose, tail and engine position; the length difference (A321 is ~7 m longer than A320) does not read at silhouette size. Optional later: variant slot `a321` using the existing `_TYPE_VARIANT_SLUGS` mechanism (not a new family).

**b737** (unchanged): B731 737-100 [?]; B732 737-200 [W]; B733 737-300 [W]; B734 737-400 [W]; B735 737-500 [W]; B736 737-600 [W]; B737 737-700 [W]; B738 737-800 [W]; B739 737-900 [W]; B37M MAX 7 [W]; B38M MAX 8 [W]; B39M MAX 9 [W]; B3XM MAX 10 [W]. Prod: B738 8378, B38M 703, B737 15, B733 2, B734 1, B739 1, B736 1. Kept merged: NG vs MAX differ by winglet and nacelle shape only. If the owner wants the MAX distinct (703 sightings), do it as variant slot `b737max`, not a family. Classic 737-100..500 (no winglets, low-slung engines) are 3 production sightings: not worth a slot.

**a350** (unchanged): A359 A350-900 [W]; A35K A350-1000 [W] (own variant slot `a350-1000` already). Prod 579 + 460.

**a330** (+A338): A332 A330-200 [W]; A333 A330-300 [W]; A338 A330-800 [W]; A339 A330-900 [W]. Prod: A339 805, A332 134, A333 92. Note A332 also covers the MRTT tanker and freighter; same picture is fine. A337 (Beluga XL) goes to `beluga`.

**atr72** (unchanged): AT43 ATR 42-300 [W]; AT44 ATR 42-400 [T, 4 airframes]; AT45 ATR 42-500 [W]; AT46 ATR 42-600 [W]; AT72 ATR 72-200 [W]; AT73 ATR 72-210 [W]; AT75 ATR 72-500 [W]; AT76 ATR 72-600 [W]. Prod: AT45 299, AT76 50, AT75 43. Note AT45 (an ATR 42, ~5 m shorter fuselage) is 76% of this family's production sightings (Chalair etc.): see question 3.

**erj145** (NEW + FIX): E135 Embraer ERJ-135 / ERJ-140 [W]; E145 ERJ-145 [W]; E45X ERJ-145XR [T, 114 airframes]; E35L Embraer Legacy 600/650 [W] (business jet built on the ERJ-135 airframe, so same silhouette). Prod: E145 127, E35L 5.

**embraer** (FIX, E-Jet): E170 [W]; E75L E175 long wing [W]; E75S E175 short wing [W]; E190 [W]; E195 [W]; E290 E190-E2 [W]; E295 E195-E2 [W]. Prod: E190 40, E195 24. Kept E2 inside E-Jet: same fuselage, E2 has bigger engines and a new wing; split only if E2 becomes common (KL E295 flights AMS-NTE seen in the reference lists).

**beechcraft1900d** (FIX): B190 Beechcraft 1900 [W] (1900D at Twin Jet [Wikipedia Twin Jet]). Prod B190 79. Remove BE9L.

**kingair** (NEW, BE9L moved here): BE9L King Air 90 [E][T]; BE9T King Air F90 [T]; BE10 King Air 100 [T]; BE20 Super King Air 200 [W]; BE30 Super King Air 300 [T]; B350 Super King Air 350 [T]. 0 production. Keep separate from the 1900D: the 1900 is a 19-seat airliner with a long thin fuselage and a distinctive tail fin/strakes; the King Air is a business turboprop. If the owner wants fewer images, `kingair` can be merged into `pc12` (see section 5) at the price of a wrong shape for BE20/B350.

**a220** (NEW): BCS1 A220-100 (Bombardier CS100) [W]; BCS3 A220-300 (CS300) [W]. Prod: BCS3 59, BCS1 28. Air France operates the A220-300 (Wikipedia Air France, fetched).

**b787** (NEW): B788 [W]; B789 [W]; B78X 787-10 [W]. Prod: B788 73, B789 16.

**b777** (NEW): B772 777-200/-200ER [W]; B773 777-300 [W]; B77L 777-200LR / 777-200F [W]; B77W 777-300ER [W]; B778 777-8 [W]; B779 777-9 [W]. Prod: B77W 9, B772 9, B77L 7. One family: all share the same nose/tail/6-wheel main gear; length difference only.

**b747** (NEW): B741 [W]; B742 [W]; B743 [W]; B744 [W]; B748 747-8 [W]; B74R 747SR [W]; B74S 747SP [W]. Prod: B748 6. BLCF (Dreamlifter, bubble fuselage) [W] is not mapped (rare).

**b767** (NEW): B762 [W]; B763 [W]; B764 [W]. Prod: B764 1 (B763 appears in the CDG reference lists).

**b757** (NEW): B752 [W]; B753 [W]. 0 prod (B752 in CDG reference lists).

**a380** (NEW): A388 A380-800 [W]. 0 prod (A388 in the Roissy reference list).

**a300** (NEW): A306 A300-600 [W]; A30B A300B2/B4 [W]; A310 A310 [W]. Coarse: A300 and A310 share nose/fuselage cross-section/tail; mostly freight in Europe now.

**a340** (NEW, tier 4): A342 [W]; A343 [W]; A345 [W]; A346 [W]. Four engines, long thin fuselage; do not fold into `a330` (different silhouette).

**crj** (NEW): CRJ1 CRJ-100 [W]; CRJ2 CRJ-200 [W]; CRJ7 CRJ-700 (Wikipedia prints "Regional Jet 550") [W]; CRJ9 CRJ-900 [W]; CRJX CRJ-1000 [W]. Prod: CRJX 1 (Iberia/Air Nostrum type in the Orly/Nantes reference lists).

**dash8** (tier 4): DH8A DH8B DH8C DH8D [W] (Q400 = DH8D). One family; Q400 is longer but same shape.

**md80** (tier 4): MD81 MD82 MD83 MD87 MD88 MD90 [W]; DC91-DC95 [W]; B712 Boeing 717 [W] (717 is a shortened MD-95, same rear-engine T-tail look). Rare in France.

**md11** (tier 4): MD11 [W]; DC10 [W]; L101 Lockheed L-1011 [W] (same trijet widebody class; L-1011 differs in the S-duct, accept as approximation or leave out).

**beluga** (tier 4): A3ST A300-600ST Beluga [W]; A337 A330-700 BelugaXL [W]. Visually unmistakable; flies to Toulouse-area Airbus sites (operational claim from general knowledge, not verified in this research).

**falcon** (NEW): FA50 Falcon 50 [W]; F900 Falcon 900 [W]; FA7X Falcon 7X [W]; FA8X Falcon 8X [T][R]; FA6X Falcon 6X [W]; F2TH Falcon 2000 [W]; FA10 Falcon 100 [T]; FA20 Falcon 200 [T]. Prod: FA8X 2. Separate because Dassault is French (high share in France) and the trijet layout (S-duct third engine) is distinct; Falcon 2000/6X twins accepted as approximations.

**bizjetlarge** (NEW): GLF4 Gulfstream IV [W]; GLF5 Gulfstream V [W]; GLF6 G650 [W]; GLEX Global Express/6000 [W]; GL5T Global 5000 [W]; GL7T Global 7500/8000 [W]; GA7C Gulfstream G700 [W]; GA5C G500 [T]; GA6C G600 [T]; GLF2 Gulfstream II [T]. Prod: GL7T 2, GL5T 2, GA7C 1. Gulfstream and Bombardier Global are the same silhouette class (long fuselage, swept wing, rear engines, T-tail).

**bizjet** (NEW): everything else with rear engines on a T-tail: Citation C25A CJ2 [W], C25B CJ3 [W], C25C CJ4 [W], C25M M2 [T], C500 [W], C501 [T], C510 Mustang [W], C525 CitationJet [W], C550 [W], C560 [W], C56X Excel [W], C650 [W], C680 Sovereign [W], C68A Latitude [W], C700 Longitude [W], C750 Citation X [W]; Challenger CL30 [W], CL35 [W], CL60 [W]; Embraer E50P Phenom 100 [W], E55P Phenom 300 [W], E545 Praetor 500 [W], E550 Praetor 600 [W]; EA50 Eclipse [W]; HDJT HondaJet [W] (engines over wing, accept approximation); H25B Hawker 800 [W]; LJ35 [W], LJ60 [W], LJ31/LJ40/LJ45/LJ75 [T]; G280 [W], GALX G200 [W], G150 [T]; PRM1 Premier 1 [T]; PC24 Pilatus PC-24 [W]. Prod: C25A 2, C56X 1. One slot is a deliberate coarse choice: these are private/charter aircraft whose silhouettes are near-identical at e-ink size; splitting light vs mid is an optional upgrade (question 6).

**helicopter** (NEW): EC45 Airbus H145/EC145 [T] (also named EC145; designator confirmed by several web results but no fetched primary source); EC35 EC135/H135 [T]; EC55 EC155 [T]; A109 AW109 [T]; A139 AW139 [T]; H160 [T]; AS65 AS365 Dauphin [T]; S76 [T]; B412 [T]; B429 [T]; A169 [T]; A189 [T]; NH90 [T]; AS32 Super Puma [T]; EC25 [T]; BK17 BK117 [T]. Prod: EC45 1. Note: ICAO designators are EC45/EC35, never "H145/H135" (those codes are not in [T]).

**helilight** (tier 4): R22 [T]; R44 [T]; R66 [T]; B06 Bell 206 [T]; B407 [T]; B505 [T]; AS50 AS350 Ecureuil [T]; EC20 EC120 [T]; EC30 EC130 [T]; H500 [T]; G2CA Guimbal Cabri [T].

**gahigh** (NEW): C172 Cessna 172 Skyhawk [T] (27 987 airframes); C150 [T]; C152 [T]; C182 [T]; C206 [T]; C210 [T]; C170 [T]; C177 [T]; C180 [T]. Prod: C172 1. High-wing single piston.

**galow** (tier 4): P28A PA-28 [T]; P28R [T]; PA24 [T]; SR20 [T]; SR22 [T]; S22T [T]; DA40 [T]; DR40 Robin DR-400 [T]; TB20 [T]; M20P [T]; BE35 Bonanza [T].

**gatwin** (tier 4): BE58 Baron [T]; PA34 Seneca [T]; PA44 [T]; DA42 [T]; DA62 [T]; C310 [T]; PA23 [T].

**pc12** (NEW): PC12 Pilatus PC-12 [W]; TBM7 [T]; TBM8 [T]; TBM9 [T]; P46T PA-46-500TP [T]; M600 [T]; SF50 Cirrus Vision Jet is NOT here (V-tail jet; map to `bizjet` or leave unmapped).

**caravan** (tier 4): C208 Cessna 208 Caravan [W]; K100 Daher Kodiak [T]. High wing, fixed gear, distinct from PC-12; merge into `pc12` if the owner accepts a wrong gear/wing picture.

**a400m** (tier 4, military): A400 Airbus A400M Atlas [W].
**c130** (tier 4, military): C130 [W]; C30J C-130J [W]; (C295 [T] and CN35 [W] are shorter twin-turboprop transports and look different; leave unmapped).

### Types deliberately NOT mapped (rare in France, no production sighting, no airline picture value)
Saab 340/2000 (SF34 [W], SB20 [W]), Fokker 50/70/100/F28 (F50 F70 F100 F28 [W]), BAe 146/Avro RJ (B461-463 [W], RJ70 RJ85 RJ1H [W]), Superjet (SU95 [W]), Comac (C919 [W], AJ27 [W]), Dornier 328 (J328 [W], D328 [T]), EMB-120 (E120 [W]), Jetstream (JS31 JS32 JS41 [W]), Short 360 (SH36 [W]), Twin Otter (DHC6 [W]), Antonov/Ilyushin/Tupolev/Yak (A124 AN12 AN26 AN32 IL76 T134 T154 YK40... [W]), 727/707/DC-8, Dreamlifter, Bell/Mil military helicopters, fighters and trainers (PC21 PC9 AJET MIR2 EUFI F16 M346 TEX2 [T], RFAL [?]), tankers (K35R [W]), gliders/balloons/ultralights/drones (GLID, BALL, ULAC, GLIM, DRON). If one is later seen in production, add a family then. If the owner wants a cheap catch-all instead of dropping them, one generic `other` silhouette (twin-engine regional) would be enough.

## 4. Counts for the owner

Production coverage by family, cumulative, in priority order (denominator 26 537; 50 untyped sightings, 0.19%, can never be covered):

| order | family | sightings | cumulative |
|-------|--------|-----------|------------|
| 1 | a320 (exists) | 14 428 | 54.4% |
| 2 | b737 (exists) | 9 101 | 88.7% |
| 3 | a350 (exists) | 1 039 | 92.6% |
| 4 | a330 (exists) | 1 031 | 96.5% |
| 5 | atr72 (exists) | 392 | 98.0% |
| 6 | **erj145 (new)** | 132 | 98.5% |
| 7 | **b787 (new)** | 89 | 98.8% |
| 8 | **a220 (new)** | 87 | 99.1% |
| 9 | beechcraft1900d (exists, fix) | 79 | 99.4% |
| 10 | embraer E-Jet (exists, fix) | 64 | 99.6% |
| 11 | **b777 (new)** | 25 | 99.7% |
| 12 | **b747 (new)** | 6 | 99.76% |
| 13+ | bizjetlarge 5, bizjet 3, falcon 2, helicopter 1, gahigh 1, crj 1, b767 1 | 14 | 99.81% |

* **Minimum useful set = 3 new silhouettes (erj145, b787, a220)**, on top of the 7 existing slots with the BE9L/B190/E145 fixes: 99.1% covered (cumulative through row 8) and 99.6% once the existing beechcraft1900d and embraer families are counted. Adding **b777 (4th new)** gives 99.7%. A strict reading of "99%+": the 3-new set already crosses it (row 8 = 99.1%).
* **Recommended set = tiers 1-3 = 17 new silhouettes**: erj145, b787, a220, b777 (tier 1), b747, b767, b757, a380, a300, crj (tier 2: 6), falcon, bizjetlarge, bizjet, kingair, pc12, helicopter, gahigh (tier 3: 7). Covers every code in production and the airliners/business types plausible at Orly, Roissy, Lyon, Nantes.
* **Complete set = 28 new silhouettes** (the 17 plus 11 tier-4: a340, dash8, md80, md11, beluga, caravan, helilight, galow, gatwin, a400m, c130). That is 35 families total (7 existing + 28 new), plus the existing `a350-1000` variant.
* Optional variants (not families, use `_TYPE_VARIANT_SLUGS`): b737max, a321, atr42, e2. 0 to 4 extra images, only if the owner wants them.
* Silhouette images to draw, priority order: 1 erj145, 2 b787, 3 a220, 4 b777, 5 b747, 6 b767, 7 crj, 8 b757, 9 a380, 10 a300, 11 bizjetlarge, 12 bizjet, 13 falcon, 14 kingair, 15 pc12, 16 helicopter, 17 gahigh, then tier 4 as listed in section 2.

## 5. Why coarse here, separate there

* **Coarse (one image)**: A318-A321 and neo (same planform), 737 classic/NG/MAX (winglets only), 777-200/-300, 787-8/-9/-10, 747 variants, CRJ-100..1000, Dash 8 -100..-400, Citation/Learjet/Phenom/Challenger (private jets, near-identical outline), all light singles by wing position, A300/A310.
* **Separate**: ERJ 135/145 vs E-Jet (engine position), A330 vs A340 (2 vs 4 engines), A350 vs A330 (existing), B190 vs King Air (airliner vs bizjet turboprop), Falcon (trijet, French fleet) vs Gulfstream/Global, PC-12 vs Caravan (low wing/retractable gear vs high wing/fixed gear), helicopters vs light helicopters, A220 vs everything (unique nose/tail), 757/767 (kept apart from 737/787; recognisable lengths and tail), Beluga.
* Rare families kept only in the complete set because a wrong picture is worse than a generic one for a family with zero sightings.

## 6. Verification status of the 43 production codes

All verified. [W] (Wikipedia designator list, fetched): A20N A21N A318 A319 A320 A321 A332 A333 A339 A359 A35K A388 AT45 AT75 AT76 B190 B38M B733 B734 B736 B737 B738 B739 B748 B752 B763 B764 B772 B77L B77W B788 B789 BCS1 BCS3 C25A C56X CRJX E145 E190 E195 E295 E35L E170 GA7C GL5T GL7T. [T] tar1090-db plus another fetched source only: FA8X [T][R]; EC45 [T]; C172 [T]. BE9L [E][T] (not a production code in the data, only in the repo's mapping). Names found: E35L = "Embraer Legacy 600 / Legacy 650" [W] and "EMB-135 Legacy" [T]; B190 = "Beechcraft 1900" [W], "BEECH 1900" [T]; GA7C = "Gulfstream G700" [W]; FA8X = "Dassault Falcon 8X" [T][R]; EC45 = "Airbus Helicopters EC-145 (H145)" [T], C172 = "Cessna 172 Skyhawk" [T].
Not obtained: ICAO Doc 8643 itself (HTTP 403 on icao.int), FlightAware type pages (403), SKYbrary (empty). Treat [T] entries as practically correct (registry-derived) but not ICAO-primary.

## 7. Unresolved questions for the owner

1. **Business jets**: one `bizjet` slot (light + mid Citation/Learjet/Phenom/Challenger/Hawker) or split into light and mid? Are Gulfstream/Global (`bizjetlarge`) and Falcon worth separate images given 0.03% of production combined? (Only 11 sightings in 11 months, but France-specific interest in Falcon.)
2. **Light GA and gliders**: do private light aircraft (C172, PA-28, SR22), balloons, gliders, ultralights, drones belong in an airline editor at all? Recommend `gahigh`/`galow`/`gatwin` only if the editor shows an "operator" (aeroclub). Else leave unmapped and show the airline-less fallback. ADS-B categories GLID/BALL/ULAC/GLIM/DRON (10 000+ airframes each in the DB) should be ignored.
3. **ATR 42 vs ATR 72**: AT45 (an ATR 42-500, 299 sightings) is 76% of the `atr72` family but is a visibly shorter airplane; one image labelled "ATR 72" is wrong for Chalair's ATR 42. Draw an `atr42` variant slot (1 extra image) or accept coarse?
4. **737 MAX**: keep MAX inside `b737` (recommended) or add a `b737max` variant (703 sightings)? Same for A321 (299 + 740 A21N).
5. **Helicopters**: one medium-twin `helicopter` (SAMU/Gendarmerie H145/H135/H160, AW139) and optionally `helilight` (R44/AS350/EC120), or skip? Only 1 production sighting (EC45).
6. **Military**: should A400M, C-130, C-295, CN-235, C-17, PC-21, Alpha Jet, Rafale/Mirage/F-16/Eurofighter, KC-135/A330 MRTT be represented? Many French military aircraft do not broadcast ADS-B or use odd codes (RFAL has no description in [T], unverified). Recommend only `a400m` and `c130`, or none.
7. **Merge rare**: OK to merge `md80` + `md11` into one "ancien" slot, drop `beluga`/`a340`/`a300` to a generic freighter? And is a single generic `other` regional-twin silhouette for all unmapped types (Saab 340, Fokker, BAe 146, Dornier 328, Jetstream, Short 360) acceptable?
8. **Embraer E2** (E290/E295): keep inside `embraer` E-Jet (recommended) or split?
9. **Display labels**: add `_TYPE_DISPLAY_LABELS` entries for every newly mapped code (e.g. BCS1 "A220-100", BCS3 "A220-300", B788 "787-8", B77W "777-300ER", E35L "Legacy 600", EC45 "H145", B190 "Beechcraft 1900D", BE9L "King Air 90") and correct BE9L. Not done here (research only).
10. **Unverified**: B731 (737-100 code) is in neither source; RFAL has no name. EC45/FA8X/C172 rely on [T] (+ [R] for FA8X) not an ICAO-primary page.
