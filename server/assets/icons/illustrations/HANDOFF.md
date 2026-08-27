# Aircraft Illustration Hand-off Specification (D-09)

This environment has no image-generation tool (verified via ToolSearch, not
assumed, and re-verified in Phase 3.1). The per-airline aircraft illustrations
that give SkyPane's panel its "l'illustration de l'avion et de son covering"
centrepiece must be generated externally (ChatGPT, Midjourney, or an
equivalent AI image tool) and dropped into this directory using **exactly**
the filenames below — they are derived from live-resolved `airline_name`
strings, not guessed, so a misspelled or differently-cased filename will
simply never be selected by the render pipeline.

**Phase 3.1 scaled this hand-off for real per-flight aircraft-type accuracy.**
Phase 3 shipped 8 files, one representative type per covered airline. Phase
3.1 extends that to the full, live-verified 24-airline D-03 table plus 7
neutral shape fallbacks — 34 target files in total, each one's aircraft type
now dictated by its filename rather than chosen freely. Quick task
`260827-jz6` (2026-08-27) added two further carriers, taking the plan from
34 to 36 files. Quick task `260827-kih` (2026-08-27) added Amelia (primary +
Embraer secondary), taking the plan from 36 to **38 files** — see the Naming
rules section below for why three already-vendored files were also renamed
in that same session, with zero effect on the total file count. Quick task
`260827-lgt` (2026-08-27) added two further carriers with art — HOP! Air
France (primary + ATR72 secondary) and KlasJet (primary) — plus one carrier
that deliberately reuses existing art with zero new files (Wizz Air Malta),
taking the plan from 38 to **41 files**.

Read this file in full before generating anything. Run these two commands at
any time for the authoritative machine-reported state:

```
server/.venv/bin/python3 server/plane/illustrations.py --targets       # the full 41-file plan
server/.venv/bin/python3 server/plane/illustrations.py --outstanding   # what is still missing right now
```

**Delivery may be incremental.** The outstanding-mode list shrinks as you
deliver batches; the automated test suite and `--validate` stay green
throughout, because `required_filenames()` only enforces files that already
exist on disk plus the pre-Phase-3.1 baseline. Nothing in the target set is
ever silently dropped — whatever remains outstanding when you stop is
recorded by name in `VENDOR.md`.

## Required files (41 total, 8 already vendored)

**Airline primary files (27)**

One unsuffixed file per airline — the carrier's numerically dominant aircraft
type per `03.1-CONTEXT.md`'s D-03 table. An asterisk `*` marks a file already
vendored from Phase 3 — do not regenerate these.

```
air-france.png            *  already vendored
iberia-airlines.png       *  already vendored
tap-portugal.png          *  already vendored
air-algerie.png           *  already vendored
air-corsica.png           *  already vendored (renamed from ccm-airlines.png, 260827-kih — see Naming rules)
vueling-airlines.png      *  already vendored
transavia-france.png      *  already vendored
easyjet.png
wizz-air.png
volotea.png
ita-airways.png
air-europa.png
royal-air-maroc.png
lot-polish-airlines.png
air-caraibes.png
french-bee.png
asl-airlines-france.png       *  already vendored (renamed from europe-airpost.png, 260827-kih — see Naming rules)
tunisair.png
pegasus-airlines.png
chalair-aviation.png
twin-jet.png
corsair.png                   *  already vendored (renamed from corsairfly.png, 260827-kih — see Naming rules)
km-malta-airlines.png         see Coverage caveat
tuifly-belgium.png            see Naming rules — this is the one approved current-brand override
amelia.png                    see Naming rules and Coverage caveat — new target, 260827-kih
air-france-hop.png            see Coverage caveat — Embraer primary, MEDIUM confidence on the split
klasjet.png                   see Coverage caveat — lower-confidence entry
```

**Airline secondary-variant files (6)**

One `{airline-slug}-{shape-slug}.png` file per mixed-fleet airline whose
minority type is common enough at Orly to warrant its own illustration
(P-04). All five are new except the renamed ATR72 slug.

```
air-corsica-atr72.png         *  already vendored (renamed from ccm-airlines-atr72.png, 260827-kih) — Air Corsica's ATR72-600 (mixed fleet with the A320 primary)
transavia-france-a320.png     Transavia's A320neo/A321neo (fleet-transition secondary, D-05)
royal-air-maroc-embraer.png   Royal Air Maroc's Embraer E190 (minority alongside the B737 primary)
air-caraibes-a330.png         Air Caraïbes' A330-300/200 (minority alongside the A350 primary)
amelia-embraer.png            Amelia's Embraer E145 (minority alongside the A320 primary, 260827-kih)
air-france-hop-atr72.png      Air France Hop's minority ATR turboprop, alongside the Embraer primary (260827-lgt, MEDIUM-confidence split)
```

**Neutral shape fallbacks + universal fallback (8)**

The D-07 tier: shown when the airline itself is unrecognized but the
detected ICAO type classifies to one of the seven D-03 base shapes. All
seven are new. `generic-fallback.png` is the pre-existing D-08 universal
fallback and is already vendored — unchanged, still used only when neither
the airline nor the shape resolves to anything on disk.

```
generic-a320.png
generic-b737.png
generic-atr72.png
generic-beechcraft1900d.png
generic-embraer.png
generic-a330.png
generic-a350.png
generic-fallback.png      *  already vendored — universal fallback, unchanged
```

## Naming rules

**SUPERSEDED (quick task `260827-kih`, 2026-08-27, QT-kih-D-06).** A
filename is now derived from the carrier's **real current name**, run
through `illustrations.py`'s `normalise_airline_key()` slug function. Where
the route API (`adsbdb`) disagrees — because its crowdsourced database
still resolves a pre-rebrand legal/trading name, or because it attributes
an ICAO prefix to a *different*, defunct carrier that once held it —
`server/plane/enrich.py`'s `correct_airline_name()` /
`apply_airline_name_correction()` reconcile the two, applied at the single
seam inside `lookup_route()`, before either the selection key or the
caption text is computed.

**The rule this supersedes, for the record:** through Phase 3.1 and quick
task `260827-hyy`, a filename was derived from the *literal* `airline_name`
string `adsbdb` actually resolved — never from the current public brand
name, and never hand-typed — because no correction mechanism existed and
mirroring `adsbdb` verbatim was the only way to keep
`select_illustration()`'s lookup working. That rule superseded here was
correct given the machinery available then: Phase 3.1 P-01/D-04,
`03.1-LIVE-RESOLUTION.md`'s Step B/C naming verdicts, and quick task
`260827-hyy`'s D-01 all rested on it, on this exact date
(`260827-kih`, 2026-08-27), by the developer's own decision (QT-kih-D-06).
**The hazard the old rule warned about is unchanged and still real** — a
filename and a selection key that drift apart silently lose selection, with
no error anywhere, no log line, no failing test. What changed is that
`enrich.correct_airline_name()` is now the mechanism that keeps them from
drifting, not manual filename discipline alone.

**Three files were renamed accordingly (`git mv`, history preserved,
QT-kih-D-04 — digests carried over verbatim, bytes unchanged):**

- **`ccm-airlines.png` → `air-corsica.png`** (plus its secondary variant,
  `ccm-airlines-atr72.png` → `air-corsica-atr72.png`). `03.1-LIVE-RESOLUTION.md`'s
  Step B confirmed the real, currently-flying callsign `CCM21AW` still
  resolves via `adsbdb` to `"CCM Airlines"`, verbatim — CCM Airlines
  rebranded to Air Corsica in 2013, and `adsbdb` was never updated.
- **`europe-airpost.png` → `asl-airlines-france.png`**. `adsbdb` resolves the
  real, currently-flying callsigns `FPO701`/`FPO458` (radio callsign
  `FRENCH POST`) to `"Europe Airpost"`, ASL's pre-2016-rebrand name.
- **`corsairfly.png` → `corsair.png`**. `adsbdb`'s airline endpoint (ICAO
  `CRL`) resolves to `"Corsairfly"`, a genuine prior brand name confirmed
  via `fr.wikipedia.org`'s own infobox — Corsair reverted from "Corsairfly"
  to "Corsair" ~2012.

Each rename's corresponding `enrich._AIRLINE_NAME_CORRECTIONS` row and
`enrich._ICAO_AIRLINE_PREFIXES` value are what make the renamed file
reachable again through every path (a fresh `adsbdb` hit, a cached `adsbdb`
hit, and the prefix-only fallback) — see `enrich.py` for the full live
evidence behind each correction.

### `tuifly-belgium.png` — the one deliberate exception, deliberately NOT extended

Quick task `260827-jz6` (2026-08-27) introduced the **one deliberate
exception** to the (now-superseded) old naming rule — the opposite
direction from every other entry above at the time. The ICAO prefix is
`JAF`. A real `JAF7521` callsign **does** resolve via `adsbdb`,
live-verified that session (`curl https://api.adsbdb.com/v0/callsign/
JAF7521`), returning the pre-2016 legacy brand name `"Jetairfly"`. The
developer chose the current brand name, `"TUIfly Belgium"`, anyway —
deliberately, with the tradeoff already in hand (QT-jz6-D-02), not as an
oversight.

**Accepted consequence, in selection terms:** a real TUIfly Belgium flight
whose callsign resolves through `adsbdb` renders the legacy string
`"Jetairfly"`, which has no matching illustration file, and falls to Tier 3
(`generic-b737.png`). The same real flight resolved through the
airline-only fallback path (`enrich.airline_from_callsign()`) renders
`"TUIfly Belgium"` and reaches `tuifly-belgium.png` directly. Both paths
correctly identify the real carrier — the divergence is only which of two
correctly-shaped illustrations is shown, never a wrong-carrier claim.

**Quick task `260827-kih` (2026-08-27, QT-kih-D-07) considered extending the
new correction seam to `JAF` too — the seam could trivially cover this exact
same failure mode — and the developer explicitly chose NOT to, this
session.** TUIfly Belgium's entry above is left completely unchanged: no
`("JAF", "Jetairfly")` row exists in `enrich._AIRLINE_NAME_CORRECTIONS`, and
none should be added as tidy-up by a future reader. **This is a recorded
decision, not an inconsistency to "fix."** KM Malta Airlines is unaffected
for a different reason entirely — `adsbdb` has no record of that carrier
under any callsign at all (a confirmed permanent miss, QT-jz6-D-01), so
there is no stale string for a correction to reconcile.

**Suffix rule.** An unsuffixed file (`{airline-slug}.png`) is the carrier's
numerically dominant type — the one most real flights of that airline will
actually show. A shape-suffixed file (`{airline-slug}-{shape-slug}.png`) is
a secondary variant, only generated for airlines with a genuinely mixed
fleet significant enough at Orly to matter (D-03/P-04). One illustration
covers a whole family: ceo, neo, and XLR sub-variants of the same base type
(e.g. A320/A320neo, A321/A321neo/A321XLR) share a single file — do not
generate separate art per sub-variant.

## Requirements — every file, no exceptions

| Property | Requirement |
|---|---|
| **File format** | PNG with a real **alpha** (transparency) channel. The area around the aircraft must be genuinely transparent - never a white or solid-colour background. A generator that "removes the background" by painting it white does **not** satisfy this; the validator (`--validate`) checks for a real alpha channel that is not fully opaque everywhere. |
| **nose orientation** | **nose pointing LEFT in every single file, no exceptions.** This is the one requirement no code can check - it is the panel's single, fixed orientation (D-24 dropped per-state mirroring entirely, so there is no "source" convention flipped per state anymore, just one orientation, always). You must confirm this by eye, per file, before reporting back. |
| **Aspect ratio** | Roughly landscape - wider than tall. |
| **Minimum resolution** | At least **1200px** wide (downscale headroom against the panel's ~900px display cap). |
| **Colour content** | The airline's **real brand livery colours** - not grayscale or tonal art. Ask for the airline's actual identifiable brand colours. The seven neutral shape files and `generic-fallback.png` are the exception: neutral metallic/grey tones, no airline identity, so they cannot read as an accidental impersonation of an uncovered carrier. |
| **Aircraft type (D-19 / Phase 3.1 accuracy upgrade)** | **No longer a free "plausible for that carrier" choice — it is dictated by the filename.** An unsuffixed airline file must show that carrier's numerically dominant type per `03.1-CONTEXT.md`'s D-03 table (see the per-file prompts below for the exact type). A shape-suffixed file must show exactly that shape. This is a correctness requirement now, not a style preference, because `select_illustration()`'s two-key lookup and the caption text (`{airline} · {type}`) both depend on the right art existing under the right name. |
| **Neutral shape files — no airline identity** | The seven `generic-{shape}.png` files must carry **no airline identity, no livery colours, no tail markings, and no logo shapes of any kind** — neutral brushed-metal/grey tones only. These files are shown precisely when the carrier could not be identified (D-07); any brand cue on them would misattribute a real, unidentified flight to a specific airline it may not even be. |
| **No readable text anywhere on the aircraft** | No fuselage titles, no tail wordmarks, no registration codes, no readable lettering of any kind painted on the airframe - color blocks and non-text emblems/logo shapes are fine, but nothing a human reads as words. |

**Project decision (2026-08-26):** this no-text requirement is explicitly
**waived** for the generated airline illustrations at the user's request, and
the waiver applies to this phase's newly generated files too, not only the
original eight. The current files may retain their carrier wordmarks and
markings. This is safe because D-24 (same date) dropped all per-state
mirroring — with no `Image.FLIP_LEFT_RIGHT` call anywhere in the render
path, fuselage text never runs backwards in either state, so the original
concern behind the waived requirement no longer applies. The waiver does
**not** extend to the seven neutral shape files, which must carry no
identity of any kind per the Requirements table row above — that is a
separate, unwaived constraint.

## Coverage caveat — what is excluded and why

Illustration selection depends transitively on `adsbdb`'s crowdsourced
callsign-to-airline coverage. `03.1-LIVE-RESOLUTION.md` re-verified this
phase's coverage boundary live:

- **easyJet (`EZY`, UK AOC) resolves and gets a file (`easyjet.png`).** This
  is new since Phase 3 — the UK-AOC prefix was re-confirmed live this
  session (`EZY63GN` → `"easyJet"`).
- **easyJet Europe (`EJU`, Austrian AOC) shares `easyjet.png` with `EZY` —
  no separate file is requested for it**, because `EJU` and `EZY` are the
  same brand and quick task `260827-hyy`'s
  `enrich.airline_from_callsign()` resolves `EJU` straight to `"easyJet"`
  via the ICAO-prefix table, reaching the existing `easyjet.png` with zero
  new art needed. (Corrected 2026-08-27, quick task `260827-jz6`: the prior
  wording here said no file was requested because the airline name was
  never available for `EJU` — that was true before `260827-hyy` shipped and
  is no longer the reason.)
- **KM Malta Airlines (`KMM`) is now a target (`km-malta-airlines.png`).**
  It is still a confirmed permanent `adsbdb` miss — live-verified
  2026-08-27, `curl https://api.adsbdb.com/v0/callsign/KMM466` returns
  `"unknown callsign"`. The reason that no longer excludes it: quick task
  `260827-hyy`'s `enrich.airline_from_callsign()` resolves the carrier
  straight from the ICAO prefix `KMM`, so an `adsbdb` miss no longer costs
  the airline identity the way it did in Phase 3.
- **TUIfly Belgium (`JAF`) is a new target (`tuifly-belgium.png`),
  added by quick task `260827-jz6`.** Winter Orly↔Morocco charter service.
  See the Naming rules section's "the one deliberate exception" subsection
  above for the full record of its deliberate current-brand-name exception,
  and of quick task `260827-kih`'s decision not to extend the new
  correction seam to cover it.
- **Amelia (`AIA`) is now a target (`amelia.png` primary + `amelia-embraer.png`
  secondary), added by quick task `260827-kih` (2026-08-27).** Through Phase
  3.1, this carrier was excluded as "Amelia International" —
  `03.1-LIVE-RESOLUTION.md` marked it `[UNRESOLVED]` because neither the
  guessed candidate ICAO code (`AMB`) nor a code corroborated by two
  independent external sources (`AEH`, per airhex.com and French Wikipedia)
  resolved to Amelia in `adsbdb` — a real, live flight under the `AEH` code
  was confirmed that session to actually belong to a different airline
  (Aviaexpress, Hungary). Both prior candidate codes turned out to belong to
  other airlines; that exclusion rationale is now **retired**, not merely
  updated: this session live-verified the real ICAO prefix,
  `AIA` (`curl https://api.adsbdb.com/v0/callsign/AIA6412`, 2026-08-27,
  corroborated by Flightradar24's live-tracked flight 8R6412 as callsign
  8R/AIA, plus Airhex, Wikipedia, ERAA and IATA), and discovered a worse
  problem than "unresolved": `adsbdb` *does* return a populated result for
  `AIA`, but attributes it to `"Avies"`, a *different, defunct* Estonian
  carrier (ceased operations 2016) that happened to hold the same ICAO code
  — not a stale label for the same real airline, an actively wrong carrier
  attribution. `enrich.correct_airline_name()` (the same seam that fixes
  Air Corsica/ASL Airlines France/Corsair above) reconciles this on read,
  so Amelia is reachable now precisely because that mechanism exists. Filed
  as **"Amelia"** (the current short name on the official Paris Aéroport
  airline list), not "Amelia International". Primary shows an Airbus A320;
  secondary shows an Embraer E145 (chosen over the E190 because the E145 is
  the type on Amelia's real Orly-relevant Pau service, per
  `03.1-CONTEXT.md`'s D-03 fleet research) — livery detail is **moderate
  confidence**, flagged in its prompt below for eye-check against a real
  photo before generating.
- **Air France Hop (`HOP`) is a new target (`air-france-hop.png` primary +
  `air-france-hop-atr72.png` secondary), added by quick task `260827-lgt`
  (2026-08-27).** This is the **first** carrier this project has added
  where `adsbdb`'s own resolution is already correct and current — cite
  the live evidence: 2026-08-27, `curl https://api.adsbdb.com/v0/callsign/
  HOP4001` returns a real route (Nantes–Lyon) with `airline_name`
  `"Air France Hop"`. It consequently needs **no** correction-seam row,
  unlike Amelia above and unlike the three renamed carriers in the Naming
  rules section. It does not share `air-france.png`: `select_illustration()`
  matches keys exactly, so `"Air France Hop"` and `"Air France"` are two
  independent keys, and the mainline A320 plate does not represent the
  regional fleet. Livery target: the post-2019 Air France mainline
  white/blue scheme with small `HOP` titling — **not** the pre-2019
  standalone brightly-coloured HOP! scheme. The Embraer primary / ATR72
  secondary split (QT-lgt-D-04) is a **MEDIUM-confidence** judgment on
  relative fleet size, not a live-verified count; reversing it is a
  one-token change in `_ILLUSTRATION_TARGETS`, and either way D-06's Tier
  2 means a HOP flight of the non-primary type still gets HOP-branded art.
- **Wizz Air Malta (`WMT`) shares `wizz-air.png` with `WZZ` — no separate
  file is requested**, added by quick task `260827-lgt` (2026-08-27). Place
  this alongside the existing `EJU`/`EZY` easyJet bullet above — that is
  the precedent this row follows exactly. `WMT` is a genuinely separate
  legal entity and AOC (Malta), holding IATA `W4` since its 2022
  reassignment; its fleet (A320/A321neo) and livery are brand-standard
  Wizz Air, visually indistinguishable at this project's flat side-profile
  illustration fidelity, so it gets its own prefix-table row in
  `enrich.py` and **zero** new artwork. Accepted consequence: the caption
  renders `Wizz Air`, not `Wizz Air Malta` — the same accepted consequence
  the `EJU` row already carries. QT-lgt-D-02: **Wizz Air UK (`WUK`) is out
  of scope, was never researched, and must not be added as tidy-up.** Note
  in passing: the Paris Aéroport list's `Wizz Air Hungary Ltd / W4`
  labelling is very likely an airport-side error, since `W4` belongs to
  the Malta AOC today.
- **KlasJet (`KLJ`) is a new target (`klasjet.png`), added by quick task
  `260827-lgt` (2026-08-27), carrying materially lower confidence than
  every other entry in this document.** This bullet must not be read like
  the others. The prefix is corroborated by lookup sources but was
  **never live-confirmed** — roughly 25 `adsbdb` queries across plausible
  flight-number ranges all returned `"unknown callsign"`, which is
  *weaker* evidence than KM Malta's confirmed-negative above, not
  equivalent to it. KlasJet is a Lithuanian ACMI/wet-lease and VIP charter
  operator, and wet-lease flights typically broadcast the **contracting**
  airline's callsign rather than the operator's own, so a real
  `KLJ`-prefixed callsign may rarely or never actually appear in this
  project's detections at Orly. The developer chose to include it anyway,
  with that uncertainty in hand. Remediation pointer: re-verify this row
  first if a `KLJ` flight is ever observed with a surprising caption.
- **La Compagnie is excluded from this target set.**
  `03.1-LIVE-RESOLUTION.md` also marks it `[UNRESOLVED]`: its real-world
  ICAO code (`DJT`) is independently confirmed via Wikipedia, but `adsbdb`'s
  own database resolves that exact code to an unrelated US airline ("Denver
  Jet"), and no real La Compagnie callsign was available this session to
  determine what a genuine flight actually returns. Same remediation path
  as Amelia: re-verify with a real callsign later.

Transavia France (`TVF`, the numerically dominant prefix in raw traffic)
resolves in only 2 of 20 real lookups per Phase 3's live test, so its
illustration — even now split into a primary B737 file and a secondary
A320neo variant — will still rarely display. It remains in the target set
at the user's request, unchanged from Phase 3.

## After generating the files

1. Run `server/.venv/bin/python3 server/plane/illustrations.py --outstanding`
   to see exactly which files are still missing, and drop the new ones into
   this directory (`server/assets/icons/illustrations/`) using **exactly**
   the filenames listed above - no extra suffixes, no capitals, no spaces.
2. Run the validator:
   `server/.venv/bin/python3 server/plane/illustrations.py --validate`
   It exits 0 only when every file present passes. Fix and regenerate
   anything it rejects.
3. Run `server/.venv/bin/python3 server/plane/illustrations.py --outstanding`
   again to confirm what (if anything) remains for a later batch.
4. Open every newly delivered file and confirm **by eye** (no code check
   exists for either of these):
   - the nose points **left** in all of them;
   - the aircraft shown is the type its filename names — a shape-suffixed
     file must show that shape, an unsuffixed airline file must show that
     carrier's dominant type per the per-file prompts below.
5. Report back, for the provenance record (`VENDOR.md`): the generation
   date, the tool used, the prompt if you kept it (or a note that this
   file's prompt below was used verbatim), and the aircraft type you
   actually see in each delivered file (not just the type requested, if the
   two differ).

## Suggested generation prompts (ready to copy-paste)

Each prompt is self-contained — paste one at a time into ChatGPT/Midjourney/
equivalent. nose-left and transparent background are repeated in every
prompt deliberately — do not drop them even if the tool seems to "remember"
context from a prior prompt in the same conversation.

**Common style guidance for all prompts:** clean editorial aircraft-side-
profile illustration (not a photo, not 3D-rendered) — flat, confident shapes
with crisp edges, closer to a vintage aviation poster plate than a
photorealistic render. This matches the poster's overall art direction and
gives the render pipeline's dithering step cleaner colour regions to work
with than a busy photographic texture would. Every file must land on
**landscape orientation, aircraft filling most of the frame, transparent
background (PNG with real alpha channel) — no ground, no sky, no shadow,
nothing behind the aircraft.**

Prompts below are grouped in the same order `--targets` prints them. Files
marked **(already vendored)** need no new art and are shown for reference
only — do not regenerate them.

---

### 1. `air-france.png` (already vendored)
```
Side-profile editorial illustration of an Airbus A320 in Air France livery
— white fuselage, the signature Air France dark blue tail with red/white/
blue winglet accents. nose pointing LEFT. Transparent background (PNG with
real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 2. `iberia-airlines.png` (already vendored)
```
Side-profile editorial illustration of an Airbus A320 in Iberia livery —
white fuselage, red tail with the Iberia bird-in-flight brand mark. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 3. `tap-portugal.png` (already vendored)
```
Side-profile editorial illustration of an Airbus A321neo in TAP Air
Portugal livery — white fuselage, red tail, red cheatline along the
fuselage. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 4. `air-algerie.png` (already vendored)
```
Side-profile editorial illustration of a Boeing 737-800 in Air Algérie
livery — white fuselage, green/white/red tail with the Air Algérie
crescent-and-star emblem. nose pointing LEFT. Transparent background (PNG
with real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 5. `air-corsica.png` (already vendored, renamed from `ccm-airlines.png` — 260827-kih, see Naming rules)
```
Side-profile editorial illustration of an Airbus A320 in Air Corsica
(CCM Airlines) livery — white fuselage, the Corsican Moor's Head emblem on
the tail, blue/white brand colours. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 6. `vueling-airlines.png` (already vendored)
```
Side-profile editorial illustration of an Airbus A320 in Vueling livery —
distinctive bright yellow fuselage with dark grey/black tail. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 7. `transavia-france.png` (already vendored)
```
Side-profile editorial illustration of a Boeing 737-800 in Transavia France
livery — white fuselage, dark green tail, green accent cheatline. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 8. `easyjet.png`
```
Side-profile editorial illustration of an Airbus A320neo in easyJet
livery — white fuselage, distinctive bright orange tail and orange
cheatline along the fuselage. nose pointing LEFT. Transparent background
(PNG with real alpha channel) — no ground, no sky, no shadow, nothing
behind the aircraft. Clean flat illustration style, crisp hard edges,
vintage aviation poster plate.
```

### 9. `wizz-air.png`
```
Side-profile editorial illustration of an Airbus A321neo (Wizz Air's
majority fleet type) in Wizz Air livery — dark charcoal/graphite fuselage,
distinctive magenta/pink tail and cheatline. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 10. `volotea.png`
```
Side-profile editorial illustration of an Airbus A320 in Volotea livery —
white fuselage, purple/magenta tail with the Volotea brand mark rendered as
a shape. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 11. `ita-airways.png`
```
Side-profile editorial illustration of an Airbus A321neo (ITA Airways'
Linate-based type) in ITA Airways livery — white/ivory fuselage, dark blue
tail with the ITA Airways brand mark. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 12. `air-europa.png`
```
Side-profile editorial illustration of a Boeing 737-800 in Air Europa
livery — white fuselage, dark navy tail with the Air Europa brand mark.
nose pointing LEFT. Transparent background (PNG with real alpha channel) —
no ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 13. `royal-air-maroc.png`
```
Side-profile editorial illustration of a Boeing 737 MAX 8 (Royal Air
Maroc's majority fleet type) in Royal Air Maroc livery — white fuselage,
red tail with the Royal Air Maroc five-pointed-star emblem. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 14. `lot-polish-airlines.png`
```
Side-profile editorial illustration of an Embraer E195 in LOT Polish
Airlines livery — white fuselage, dark navy tail with the LOT crane emblem
rendered as a shape. nose pointing LEFT. Transparent background (PNG with
real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 15. `air-caraibes.png`
```
Side-profile editorial illustration of an Airbus A350-900 (Air Caraïbes'
majority Orly-relevant type) in Air Caraïbes livery — white fuselage with a
distinctive colourful tropical-flower tail design in warm reds/oranges/
yellows. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 16. `french-bee.png`
```
Side-profile editorial illustration of an Airbus A350-900 in French Bee
livery — white fuselage, distinctive black/dark tail with a stylized bee
emblem in yellow/black. nose pointing LEFT. Transparent background (PNG
with real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 17. `asl-airlines-france.png` (already vendored, renamed from `europe-airpost.png` — 260827-kih, see Naming rules)
```
Side-profile editorial illustration of a Boeing 737-800 in Europe Airpost
(ASL Airlines France) livery — white/light-grey fuselage, blue tail and
blue cheatline, cargo/freight operator branding. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 18. `tunisair.png`
```
Side-profile editorial illustration of an Airbus A320neo in Tunisair
livery — white fuselage, red tail with the Tunisair brand mark. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 19. `pegasus-airlines.png`
```
Side-profile editorial illustration of an Airbus A321neo (Pegasus'
majority A320-family fleet) in Pegasus Airlines livery — white fuselage,
distinctive yellow tail with the Pegasus flying-horse emblem. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 20. `chalair-aviation.png`
```
Side-profile editorial illustration of an ATR 72 turboprop in Chalair
Aviation livery — white fuselage, dark blue tail with the Chalair brand
mark. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 21. `twin-jet.png`
```
Side-profile editorial illustration of a Beechcraft 1900D small twin
turboprop (18-seat commuter type) in Twin Jet livery — white fuselage, red/
orange tail and cheatline with the Twin Jet brand mark. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 22. `corsair.png` (already vendored, renamed from `corsairfly.png` — 260827-kih, see Naming rules)
```
Side-profile editorial illustration of an Airbus A330-900neo (Corsair
International's single-type widebody fleet) in Corsair livery — white
fuselage, distinctive red/blue tail with the Corsair brand mark. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 23. `km-malta-airlines.png` (this is the post-2023 KM Malta Airlines livery — NOT the superseded Air Malta red-tail scheme)
```
Side-profile editorial illustration of an Airbus A320neo in KM Malta
Airlines livery (the current, post-2023 livery — do not produce the
superseded Air Malta red-tail scheme) — white fuselage, the red two-tone
Maltese Cross emblem on the tail, blue and red accents. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 24. `tuifly-belgium.png` (this is the current TUI livery — NOT the superseded Jetairfly scheme; see Naming rules' approved override above)
```
Side-profile editorial illustration of a Boeing 737 MAX 8 (identifiable by
its distinctive split-tip winglets, not the 737-800) in the current TUI
Group "Dynamic Wave" livery (do not produce the superseded Jetairfly
scheme) — light blue and white fuselage, a blue wave sweep along the body,
red TUI fuselage titles, and a red "smile" logo on the tail. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 25. `amelia.png` (primary — Amelia's Airbus A320, 260827-kih)
```
Side-profile editorial illustration of an Airbus A320 in Amelia livery —
white fuselage, blue tail, lowercase "amelia" wordmark. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.

LIVERY CONFIDENCE NOTE: the white fuselage / blue tail / lowercase
wordmark description above is MODERATE CONFIDENCE — check it against a
real photo of an Amelia aircraft before generating. This carrier was only
added to the target set this session (quick task 260827-kih) after live
ICAO-prefix verification (see the Coverage caveat above); the livery
detail itself has not been independently photo-verified the way this
project's other liveries were, so treat it as a starting point for the
developer's own judgement at generation time, not a confirmed fact.
```

### 26. `air-france-hop.png` (primary — Air France Hop's Embraer E190, 260827-lgt, MEDIUM confidence on primary/secondary split)
```
Side-profile editorial illustration of an Embraer E190 in the post-2019
Air France regional livery — white fuselage, Air France dark-blue tail,
red/white/blue accents, small `HOP` titling. This is the post-2019 Air
France mainline scheme with HOP titling — explicitly NOT the pre-2019
standalone brightly-coloured HOP! livery; do not produce the retired
brand's art. This file is deliberately distinct from `air-france.png`
(the mainline A320) and must show the regional jet. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 27. `klasjet.png` (primary — KlasJet's Boeing 737-800, 260827-lgt, lower-confidence entry)
```
Side-profile editorial illustration of a Boeing 737-800 in KlasJet
livery — white fuselage with an abstract light-blue/yellow tail design.
nose pointing LEFT. Transparent background (PNG with real alpha channel)
— no ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.

LIVERY CONFIDENCE NOTE: the white fuselage / abstract light-blue/yellow
tail description above is LOWER CONFIDENCE than this project's other
entries — check it against a real photo of a KlasJet aircraft before
generating.

OPEN QUESTION FOR THE DEVELOPER TO RESOLVE AT GENERATION TIME
(QT-lgt-D-08): KlasJet's fleet mixes 737-300/500/800 with Boeing Business
Jets (BBJ). A BBJ/VIP-configured airframe would not visually match a
standard 737-800 plate. The 737-800 was chosen here as the most
plausible scheduled-passenger-shaped option, but the developer should
make the final call before generating.
```

### 28. `air-corsica-atr72.png` (already vendored, renamed from `ccm-airlines-atr72.png` — 260827-kih, secondary variant, Air Corsica's ATR72-600)
```
Side-profile editorial illustration of an ATR 72-600 turboprop in Air
Corsica (CCM Airlines) livery — matching `air-corsica.png`'s blue/white
brand colours and Corsican Moor's Head tail emblem, on the turboprop
airframe instead of the A320. nose pointing LEFT. Transparent background
(PNG with real alpha channel) — no ground, no sky, no shadow, nothing
behind the aircraft. Clean flat illustration style, crisp hard edges,
vintage aviation poster plate.
```

### 29. `transavia-france-a320.png` (secondary variant — Transavia's fleet-transition A320neo, D-05)
```
Side-profile editorial illustration of an Airbus A320neo in Transavia
France livery — matching `transavia-france.png`'s dark green tail and green
cheatline, on the A320neo airframe instead of the 737-800. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 30. `royal-air-maroc-embraer.png` (secondary variant — Royal Air Maroc's minority Embraer E190)
```
Side-profile editorial illustration of an Embraer E190 in Royal Air Maroc
livery — matching `royal-air-maroc.png`'s red tail and five-pointed-star
emblem, on the regional-jet airframe instead of the 737. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 31. `air-caraibes-a330.png` (secondary variant — Air Caraïbes' minority A330-300)
```
Side-profile editorial illustration of an Airbus A330-300 in Air Caraïbes
livery — matching `air-caraibes.png`'s tropical-flower tail design, on the
A330 airframe instead of the A350. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 32. `amelia-embraer.png` (secondary variant — Amelia's minority Embraer E145, 260827-kih)
```
Side-profile editorial illustration of an Embraer E145 in Amelia livery —
matching `amelia.png`'s white fuselage and blue tail, on the regional-jet
airframe instead of the A320. nose pointing LEFT. Transparent background
(PNG with real alpha channel) — no ground, no sky, no shadow, nothing
behind the aircraft. Clean flat illustration style, crisp hard edges,
vintage aviation poster plate.

LIVERY CONFIDENCE NOTE: the white fuselage / blue tail / lowercase
wordmark description above is MODERATE CONFIDENCE — check it against a
real photo of an Amelia aircraft before generating, per this project's
established practice for unverified livery detail (see `amelia.png`'s
prompt below for the same note).
```

### 33. `air-france-hop-atr72.png` (secondary variant — Air France Hop's minority ATR 72-600, 260827-lgt, MEDIUM confidence on primary/secondary split)
```
Side-profile editorial illustration of an ATR 72-600 in the same Air
France regional livery, matching `air-france-hop.png`'s colours on the
turboprop airframe instead of the regional jet. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration
style, crisp hard edges, vintage aviation poster plate.
```

### 34. `generic-a320.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A320-family-shaped
narrow-body commercial jet — NO airline identity, no livery colours, no
tail markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 35. `generic-b737.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Boeing-737-family-shaped
narrow-body commercial jet — NO airline identity, no livery colours, no
tail markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 36. `generic-atr72.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic ATR-72-shaped turboprop
airliner — NO airline identity, no livery colours, no tail markings, no
logo shapes of any kind. Neutral brushed-metal/grey tones only. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 37. `generic-beechcraft1900d.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Beechcraft-1900D-shaped
small twin turboprop commuter aircraft — NO airline identity, no livery
colours, no tail markings, no logo shapes of any kind. Neutral brushed-
metal/grey tones only. nose pointing LEFT. Transparent background (PNG
with real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 38. `generic-embraer.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Embraer-E-Jet-shaped
regional jet — NO airline identity, no livery colours, no tail markings, no
logo shapes of any kind. Neutral brushed-metal/grey tones only. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 39. `generic-a330.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A330-family-shaped
widebody commercial jet — NO airline identity, no livery colours, no tail
markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 40. `generic-a350.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A350-family-shaped
widebody commercial jet — NO airline identity, no livery colours, no tail
markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 41. `generic-fallback.png` (already vendored — D-08 universal fallback, unchanged)
```
Side-profile editorial illustration of a generic narrow-body commercial jet
airliner (no specific airline identity) in neutral brushed-metal/grey tones
only — no livery colours, no logos, no tail markings, no airline branding
of any kind. nose pointing LEFT. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the aircraft.
Clean flat illustration style, crisp hard edges, vintage aviation poster
plate.
```
