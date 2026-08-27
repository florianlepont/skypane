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
now dictated by its filename rather than chosen freely.

Read this file in full before generating anything. Run these two commands at
any time for the authoritative machine-reported state:

```
server/.venv/bin/python3 server/plane/illustrations.py --targets       # the full 34-file plan
server/.venv/bin/python3 server/plane/illustrations.py --outstanding   # what is still missing right now
```

**Delivery may be incremental.** The outstanding-mode list shrinks as you
deliver batches; the automated test suite and `--validate` stay green
throughout, because `required_filenames()` only enforces files that already
exist on disk plus the pre-Phase-3.1 baseline. Nothing in the target set is
ever silently dropped — whatever remains outstanding when you stop is
recorded by name in `VENDOR.md`.

## Required files (34 total, 8 already vendored)

**Airline primary files (22)**

One unsuffixed file per airline — the carrier's numerically dominant aircraft
type per `03.1-CONTEXT.md`'s D-03 table. An asterisk `*` marks a file already
vendored from Phase 3 — do not regenerate these.

```
air-france.png            *  already vendored
iberia-airlines.png       *  already vendored
tap-portugal.png          *  already vendored
air-algerie.png           *  already vendored
ccm-airlines.png          *  already vendored — see Naming rules, do NOT rename
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
europe-airpost.png           see Naming rules — this is "ASL Airlines France"
tunisair.png
pegasus-airlines.png
chalair-aviation.png
twin-jet.png
corsairfly.png                see Naming rules — this is "Corsair International"
```

**Airline secondary-variant files (4)**

One `{airline-slug}-{shape-slug}.png` file per mixed-fleet airline whose
minority type is common enough at Orly to warrant its own illustration
(P-04). All four are new.

```
ccm-airlines-atr72.png        Air Corsica's ATR72-600 (mixed fleet with the A320 primary)
transavia-france-a320.png     Transavia's A320neo/A321neo (fleet-transition secondary, D-05)
royal-air-maroc-embraer.png   Royal Air Maroc's Embraer E190 (minority alongside the B737 primary)
air-caraibes-a330.png         Air Caraïbes' A330-300/200 (minority alongside the A350 primary)
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

A filename is derived from the literal `airline_name` string the route API
(`adsbdb`, via `server/plane/enrich.py`'s `lookup_route()`) actually
resolves, run through `illustrations.py`'s `normalise_airline_key()` slug
function — **never** from the carrier's current public brand name, and never
hand-typed.

This matters because `adsbdb`'s crowdsourced database sometimes still
resolves an airline's pre-rebrand legal/trading name years after a real
rebrand. **`ccm-airlines.png` must never be renamed to `air-corsica.png`,
even though CCM Airlines rebranded to Air Corsica in 2013.**
`03.1-LIVE-RESOLUTION.md`'s Step B re-confirmed this live this session: the
real, currently-flying callsign `CCM21AW` still resolves via `adsbdb` to
`"CCM Airlines"`, verbatim, not `"Air Corsica"`. **Consequence of renaming
it:** every real Air Corsica flight would silently stop matching Tier 2 of
`select_illustration()`'s lookup and fall through to a lower fallback tier
(a neutral shape or the universal fallback) — with no error anywhere in the
system, no log line, no failing test. The file would still exist on disk,
still pass `--validate`, and simply never be selected again.

Phase 3.1's own live resolution (`03.1-LIVE-RESOLUTION.md`, Step C) found
two more airlines with exactly this pattern, which is why they are filed
under older names rather than D-03's current-brand labels:

- **`europe-airpost.png`** — D-03 lists this airline as "ASL Airlines
  France," but `adsbdb` resolves its real, currently-flying callsigns
  (`FPO701`, `FPO458`, radio callsign `FRENCH POST`) to `"Europe Airpost"`,
  ASL's pre-2016-rebrand name. Do not name this file
  `asl-airlines-france.png`.
- **`corsairfly.png`** — D-03 lists this airline as "Corsair International,"
  but `adsbdb`'s airline endpoint (ICAO `CRL`) resolves to `"Corsairfly"`, a
  genuine prior brand name confirmed via `fr.wikipedia.org`'s own infobox.
  Do not name this file `corsair-international.png`.

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

## Coverage caveat — what remains excluded and why

Illustration selection depends transitively on `adsbdb`'s crowdsourced
callsign-to-airline coverage. `03.1-LIVE-RESOLUTION.md` re-verified this
phase's coverage boundary live:

- **easyJet (`EZY`, UK AOC) resolves and gets a file (`easyjet.png`).** This
  is new since Phase 3 — the UK-AOC prefix was re-confirmed live this
  session (`EZY63GN` → `"easyJet"`).
- **easyJet Europe (`EJU`, Austrian AOC) remains a confirmed, deliberate
  miss (P-03)** — `airline_name` is never available for those flights no
  matter how good an illustration exists, so no file is requested for it.
- **KM Malta Airlines (`KMM`) remains excluded**, unchanged from Phase 3 —
  same confirmed-miss status.
- **Amelia International is excluded from this target set.**
  `03.1-LIVE-RESOLUTION.md` marks it `[UNRESOLVED]`: neither the guessed
  candidate ICAO code (`AMB`) nor a code corroborated by two independent
  external sources (`AEH`, per airhex.com and French Wikipedia) resolves to
  Amelia in `adsbdb` — a real, live flight under the `AEH` code was
  confirmed this session to actually belong to a different airline
  (Aviaexpress, Hungary). Generating art for `AEH` would silently
  misattribute Amelia's brand identity to that airline's real flights. Can
  be added later with zero code change once a real Amelia flight is caught
  and cross-checked.
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

### 5. `ccm-airlines.png` (already vendored — do NOT rename, see Naming rules)
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

### 17. `europe-airpost.png` (this is "ASL Airlines France" — see Naming rules, do NOT name this file `asl-airlines-france.png`)
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

### 22. `corsairfly.png` (this is "Corsair International" — see Naming rules, do NOT name this file `corsair-international.png`)
```
Side-profile editorial illustration of an Airbus A330-900neo (Corsair
International's single-type widebody fleet) in Corsair livery — white
fuselage, distinctive red/blue tail with the Corsair brand mark. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 23. `ccm-airlines-atr72.png` (secondary variant — Air Corsica's ATR72-600)
```
Side-profile editorial illustration of an ATR 72-600 turboprop in Air
Corsica (CCM Airlines) livery — matching `ccm-airlines.png`'s blue/white
brand colours and Corsican Moor's Head tail emblem, on the turboprop
airframe instead of the A320. nose pointing LEFT. Transparent background
(PNG with real alpha channel) — no ground, no sky, no shadow, nothing
behind the aircraft. Clean flat illustration style, crisp hard edges,
vintage aviation poster plate.
```

### 24. `transavia-france-a320.png` (secondary variant — Transavia's fleet-transition A320neo, D-05)
```
Side-profile editorial illustration of an Airbus A320neo in Transavia
France livery — matching `transavia-france.png`'s dark green tail and green
cheatline, on the A320neo airframe instead of the 737-800. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 25. `royal-air-maroc-embraer.png` (secondary variant — Royal Air Maroc's minority Embraer E190)
```
Side-profile editorial illustration of an Embraer E190 in Royal Air Maroc
livery — matching `royal-air-maroc.png`'s red tail and five-pointed-star
emblem, on the regional-jet airframe instead of the 737. nose pointing
LEFT. Transparent background (PNG with real alpha channel) — no ground, no
sky, no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 26. `air-caraibes-a330.png` (secondary variant — Air Caraïbes' minority A330-300)
```
Side-profile editorial illustration of an Airbus A330-300 in Air Caraïbes
livery — matching `air-caraibes.png`'s tropical-flower tail design, on the
A330 airframe instead of the A350. nose pointing LEFT.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft. Clean flat illustration style,
crisp hard edges, vintage aviation poster plate.
```

### 27. `generic-a320.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A320-family-shaped
narrow-body commercial jet — NO airline identity, no livery colours, no
tail markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 28. `generic-b737.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Boeing-737-family-shaped
narrow-body commercial jet — NO airline identity, no livery colours, no
tail markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 29. `generic-atr72.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic ATR-72-shaped turboprop
airliner — NO airline identity, no livery colours, no tail markings, no
logo shapes of any kind. Neutral brushed-metal/grey tones only. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 30. `generic-beechcraft1900d.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Beechcraft-1900D-shaped
small twin turboprop commuter aircraft — NO airline identity, no livery
colours, no tail markings, no logo shapes of any kind. Neutral brushed-
metal/grey tones only. nose pointing LEFT. Transparent background (PNG
with real alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft. Clean flat illustration style, crisp hard edges, vintage aviation
poster plate.
```

### 31. `generic-embraer.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Embraer-E-Jet-shaped
regional jet — NO airline identity, no livery colours, no tail markings, no
logo shapes of any kind. Neutral brushed-metal/grey tones only. nose
pointing LEFT. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft. Clean flat
illustration style, crisp hard edges, vintage aviation poster plate.
```

### 32. `generic-a330.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A330-family-shaped
widebody commercial jet — NO airline identity, no livery colours, no tail
markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 33. `generic-a350.png` (D-07 neutral shape fallback — NO airline identity)
```
Side-profile editorial illustration of a generic Airbus-A350-family-shaped
widebody commercial jet — NO airline identity, no livery colours, no tail
markings, no logo shapes of any kind. Neutral brushed-metal/grey tones
only. nose pointing LEFT. Transparent background (PNG with real alpha
channel) — no ground, no sky, no shadow, nothing behind the aircraft. Clean
flat illustration style, crisp hard edges, vintage aviation poster plate.
```

### 34. `generic-fallback.png` (already vendored — D-08 universal fallback, unchanged)
```
Side-profile editorial illustration of a generic narrow-body commercial jet
airliner (no specific airline identity) in neutral brushed-metal/grey tones
only — no livery colours, no logos, no tail markings, no airline branding
of any kind. nose pointing LEFT. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the aircraft.
Clean flat illustration style, crisp hard edges, vintage aviation poster
plate.
```
