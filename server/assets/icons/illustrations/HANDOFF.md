# Aircraft Illustration Hand-off Specification (D-09)

This environment has no image-generation tool (verified via ToolSearch, not
assumed). The per-airline aircraft illustrations that give Ink Frame's
panel its "l'illustration de l'avion et de son covering" centrepiece must
be generated externally (ChatGPT, Midjourney, or an equivalent AI image
tool) and dropped into this directory using **exactly** the filenames
below - they are derived from live-resolved `airline_name` strings, not
guessed, so a misspelled or differently-cased filename will simply never
be selected by the render pipeline.

Read this file in full before generating anything. Run
`server/.venv/bin/python3 server/plane/illustrations.py --required` at any
time to reprint the authoritative filename list below.

## Required files (7 total)

```
air-france.png
iberia-airlines.png
tap-portugal.png
air-algerie.png
ccm-airlines.png
vueling-airlines.png
generic-fallback.png
```

Each of the first six corresponds to a carrier whose `airline_name` was
resolved **live** against `api.adsbdb.com` on 2026-08-26 (see
`server/plane/illustrations.py`'s module docstring for the full
callsign-to-name table). `generic-fallback.png` is the single dithered
illustration used for every uncovered airline and for the "Route
unavailable" enrichment-failure state (D-08) - it must never be an
airline-specific design.

## Requirements - every file, no exceptions

| Property | Requirement |
|---|---|
| **File format** | PNG with a real **alpha** (transparency) channel. The area around the aircraft must be genuinely transparent - never a white or solid-colour background. A generator that "removes the background" by painting it white does **not** satisfy this; the validator (`--validate`) checks for a real alpha channel that is not fully opaque everywhere. |
| **Nose orientation** | **Nose pointing LEFT in every single file, no exceptions.** This is the one requirement no code can check - mirroring for the departing/arriving states is applied in code from this single assumption, so one inconsistent file will silently render backwards for that airline only, in both states, and will look like a rendering bug rather than an asset bug. You must confirm this by eye, per file, before reporting back. |
| **Aspect ratio** | Roughly landscape - wider than tall. |
| **Minimum resolution** | At least **1200px** wide (downscale headroom against the panel's ~900px display cap). |
| **Colour content** | The airline's **real brand livery colours** - not grayscale or tonal art. Ask for the airline's actual identifiable brand colours (e.g. Air France's blue/white/red, Vueling's yellow, TAP's red). `generic-fallback.png` is the one exception: neutral metallic/grey tones, no airline identity, so it cannot read as an accidental impersonation of an uncovered carrier. |
| **Aircraft type (D-19)** | Pick a real, plausible, commonly-seen aircraft type for that airline at Orly - not an arbitrary generic jet. Real per-flight type detection is deliberately out of scope for this phase and is a later phase's job (Phase 3.1) - do not try to match the type to any specific flight. |
| **No readable text anywhere on the aircraft** | **No fuselage titles, no tail wordmarks, no registration codes, no readable lettering of any kind painted on the airframe** - color blocks and non-text emblems/logo shapes (e.g. a bird mark, a crescent-and-star, a geometric tail design) are fine, but nothing a human reads as words. This is not a style preference - the code horizontally mirrors this same file to produce the DEPARTING (nose-right) render from the ARRIVING (nose-left) source, and mirrored text is backwards and unreadable in one of the two states. A logo/emblem shape still reads fine mirrored; text does not. Check every file for this specifically - it's easy for an image generator to add a fuselage title without being asked. |

## Coverage caveat - why only 6 airlines, and not easyJet or KM Malta

Illustration selection depends transitively on `adsbdb`'s crowdsourced
callsign-to-airline coverage, which resolved only ~52.6% of this airport's
real traffic in Phase 2's live test. Two carriers seen regularly in raw
ADS-B traffic - **easyJet Europe** (`EJU`) and **KM Malta Airlines**
(`KMM`) - are **confirmed `adsbdb` misses**: `airline_name` is never
available for those flights no matter how good an illustration exists for
them, so an easyJet or KM Malta file would simply never be selectable.
Do not generate art for either. Transavia France (`TVF`, the numerically
dominant prefix in raw traffic) is also deliberately excluded from this
required set - it resolves in only 2 of 20 real lookups, so a Transavia
illustration would rarely display even though Transavia is the most common
carrier actually seen on runway 3.

## After generating the files

1. Drop all 7 files into this directory (`server/assets/icons/illustrations/`)
   using exactly the filenames listed above - no extra suffixes, no
   capitals, no spaces.
2. Run the validator:
   `server/.venv/bin/python3 server/plane/illustrations.py --validate`
   It exits 0 only when every file passes. Fix and regenerate anything it
   rejects.
3. Open every file and confirm **by eye** (no code check exists for either
   of these):
   - the nose points **left** in all of them;
   - **no readable text/wordmarks/registration codes** appear anywhere on
     the aircraft — this matters even if a file was generated before this
     requirement was added to the prompts above; a stray "AIR FRANCE"
     titled along the fuselage will render backwards once code mirrors it
     for the DEPARTING state. If you already generated files before
     reading this, re-check them against this specific point and
     regenerate any that have text on the airframe.
4. Report back, for the provenance record (`VENDOR.md`): the generation
   date, the tool used, the prompt if you kept it, and the aircraft type
   you chose per airline.

## Suggested generation prompts (ready to copy-paste)

Each prompt is self-contained — paste one at a time into ChatGPT/Midjourney/
equivalent. The aircraft type picked per airline is a plausible, commonly-seen
one for that carrier at Orly (D-19) — swap it for another real type from the
same airline's fleet if you prefer, it does not need to match any specific
flight. Nose-left and transparent background are repeated in every prompt
deliberately — do not drop them even if the tool seems to "remember" context
from a prior prompt in the same conversation.

**Common style guidance for all seven:** clean editorial aircraft-side-profile
illustration (not a photo, not 3D-rendered) — flat, confident shapes with
crisp edges, closer to a vintage aviation poster plate than a photorealistic
render. This matches the poster's overall art direction (see D-14 in
`03-CONTEXT.md` if you want the full rationale) and gives the render
pipeline's dithering step cleaner color regions to work with than a busy
photographic texture would.

---

**Critical, repeated in every prompt below:** no readable text anywhere on
the aircraft (no fuselage titles, no tail wordmarks, no registration codes)
— the code mirrors this exact file to produce the opposite state, and
mirrored text is backwards/unreadable. Color blocks and non-text emblem
shapes are fine; words are not.

### 1. `air-france.png`
```
Side-profile editorial illustration of an Airbus A320 in Air France livery
— white fuselage, the signature Air France dark blue tail with red/white/
blue winglet accents. Nose pointing LEFT. NO text, wordmarks, titles, or
registration codes anywhere on the aircraft — colour blocks only, this
file will be mirrored by code and text would end up backwards. Clean flat
illustration style, crisp hard edges, no gradients or photographic
texture, like a vintage aviation poster plate. Landscape orientation,
aircraft filling most of the frame. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft.
```

### 2. `iberia-airlines.png`
```
Side-profile editorial illustration of an Airbus A320 in Iberia livery —
white fuselage, red tail with the Iberia bird-in-flight brand mark
rendered as a shape only (not spelled-out text). Nose pointing LEFT. NO
text, wordmarks, titles, or registration codes anywhere on the aircraft —
this file will be mirrored by code and text would end up backwards. Clean
flat illustration style, crisp hard edges, no gradients or photographic
texture, like a vintage aviation poster plate. Landscape orientation,
aircraft filling most of the frame. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft.
```

### 3. `tap-portugal.png`
```
Side-profile editorial illustration of an Airbus A321neo in TAP Air
Portugal livery — white fuselage, red tail, red cheatline along the
fuselage. Nose pointing LEFT. NO text, wordmarks, titles, or registration
codes anywhere on the aircraft — colour blocks and the tail shape only,
this file will be mirrored by code and text would end up backwards. Clean
flat illustration style, crisp hard edges, no gradients or photographic
texture, like a vintage aviation poster plate. Landscape orientation,
aircraft filling most of the frame. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft.
```

### 4. `air-algerie.png`
```
Side-profile editorial illustration of a Boeing 737-800 in Air Algérie
livery — white fuselage, green/white/red tail with the Air Algérie
crescent-and-star emblem rendered as a shape only (not spelled-out text).
Nose pointing LEFT. NO text, wordmarks, titles, or registration codes
anywhere on the aircraft — this file will be mirrored by code and text
would end up backwards. Clean flat illustration style, crisp hard edges,
no gradients or photographic texture, like a vintage aviation poster
plate. Landscape orientation, aircraft filling most of the frame.
Transparent background (PNG with real alpha channel) — no ground, no sky,
no shadow, nothing behind the aircraft.
```

### 5. `ccm-airlines.png`
```
Side-profile editorial illustration of an Airbus A320 in Air Corsica
(CCM Airlines) livery — white fuselage, the Corsican Moor's Head emblem
on the tail rendered as a shape only (not spelled-out text), blue/white
brand colours. Nose pointing LEFT. NO text, wordmarks, titles, or
registration codes anywhere on the aircraft — this file will be mirrored
by code and text would end up backwards. Clean flat illustration style,
crisp hard edges, no gradients or photographic texture, like a vintage
aviation poster plate. Landscape orientation, aircraft filling most of
the frame. Transparent background (PNG with real alpha channel) — no
ground, no sky, no shadow, nothing behind the aircraft.
```

### 6. `vueling-airlines.png`
```
Side-profile editorial illustration of an Airbus A320 in Vueling livery
— distinctive bright yellow fuselage with dark grey/black tail. Nose
pointing LEFT. NO text, wordmarks, titles, or registration codes anywhere
on the aircraft — colour blocks only (yellow fuselage, dark tail), this
file will be mirrored by code and text would end up backwards. Clean flat
illustration style, crisp hard edges, no gradients or photographic
texture, like a vintage aviation poster plate. Landscape orientation,
aircraft filling most of the frame. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft.
```

### 7. `generic-fallback.png`
```
Side-profile editorial illustration of a generic narrow-body commercial
jet airliner (no specific airline identity) in neutral brushed-metal /
grey tones only — no livery colours, no logos, no tail markings, no
airline branding of any kind. Nose pointing LEFT. NO text, wordmarks,
titles, or registration codes anywhere on the aircraft. Clean flat
illustration style, crisp hard edges, no gradients or photographic
texture, like a vintage aviation poster plate. Landscape orientation,
aircraft filling most of the frame. Transparent background (PNG with real
alpha channel) — no ground, no sky, no shadow, nothing behind the
aircraft.
```
