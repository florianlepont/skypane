# server/assets/icons/illustrations — Vendor Provenance

This directory's top-level summary already lives in
`server/assets/icons/VENDOR.md` (generation date, tool, prompt recipe, and
the per-airline aircraft-type table). This file is the missing per-file
provenance record 03-03-PLAN.md's Task 2 specified — sha256 digest,
pixel dimensions, which airline each file serves, and the licensing
rationale for the set as a whole — closed retroactively in this session
per the plan's Reconciliation Note (2026-08-26): the files themselves,
`HANDOFF.md`, and `server/plane/illustrations.py` all shipped earlier
(commit `21c4ed6` for the module/hand-off spec, `0e4e0ca`/`e52602e` for
the vendored PNGs), but this `VENDOR.md` was never written until now.

## Provenance summary

- **Origin:** AI-generated originals, not third-party-sourced or
  per-airline-licensed brand art.
- **Generation date:** 2026-08-26 (original 8-file Phase 3 baseline).
- **Tool:** OpenAI built-in image generation (`gpt-image`), generated as
  transparent RGBA PNG cutouts and visually inspected after generation.
- **Prompt recipe:** polished modern aviation-poster illustration with
  crisp ink-like contours, clean coloured body planes, and restrained
  blue-grey graphic shadows; one aircraft, landscape framing, nose
  pointing **left**, authentic carrier livery colours, and a genuinely
  transparent RGBA background with no ground, sky, vignette, halo,
  scenery, or extra aircraft. `generic-fallback.png` additionally
  prohibits all airline identities, logos, and livery colours. See
  `HANDOFF.md` in this directory for the full per-file prompt text that
  was handed to the developer.
- **Generation date (Phase 3.1 batch):** 2026-08-27.
- **Tool (Phase 3.1 batch):** AI image generation per `HANDOFF.md`'s
  per-file prompts (developer-side, external to this environment — D-09,
  same as the 2026-08-26 baseline entry above). The prompts were used
  verbatim from `HANDOFF.md`; no separate per-file prompt-tool name beyond
  that discipline was recorded for this batch. Every delivered file passed
  `server/plane/illustrations.py --validate` and the developer confirmed,
  by eye, nose-left orientation and filename-matches-aircraft-type for
  each one (Task 2's blocking human gate) before this record was written.
  This was an explicitly **partial, named** delivery — see "Phase 3.1
  coverage" below for what shipped and what remains.
- **Licensing rationale (D-09):** these are original, AI-generated
  illustrations, not copied or scraped airline brand assets. AI
  generation sidesteps the per-airline trademark/licensing constraint
  that made Phase 2 reject real per-airline art and settle for a single
  CC0 generic silhouette instead (see `server/assets/icons/VENDOR.md`'s
  `aircraft-silhouette.svg` entry for that earlier decision). This is the
  developer's own generation output, produced through a commercial image
  tool under that tool's own usage terms — it has **not** been
  independently rights-cleared or reviewed by counsel; it is treated as
  acceptable for this hobby project's scope on the same basis Phase 2
  already accepted for the CC0 silhouette, not as a stronger legal
  guarantee than that.
- **Nose orientation:** `ILLUSTRATION_SOURCE_NOSE = "left"` is the
  set-wide convention (`server/plane/illustrations.py`). Verified by eye,
  per file, at hand-off time (Task 2's blocking checkpoint) — no code
  check exists for this (03-RESEARCH.md Pitfall 4). D-24 later dropped
  state-based mirroring entirely, so every file now renders nose-left in
  both departing and arriving states; the verification-by-eye discipline
  at vendor time is unchanged by that.
- **No-text waiver (D-23):** the "no readable text/wordmarks/registration
  codes" requirement `HANDOFF.md` originally hardened was waived at the
  developer's request on 2026-08-26. The files below may retain real
  carrier wordmarks and fuselage titles. This waiver is only safe because
  D-24 (same date) dropped mirroring — with no `Image.FLIP_LEFT_RIGHT`
  call anywhere in the render path, fuselage text never runs backwards in
  either state. The two decisions are load-bearing on each other; see
  03-03-PLAN.md's Reconciliation Note for the full cross-reference.

## Per-file digests

All eight Phase-3-baseline files are native RGBA PNGs, all at least
1200px wide, and all pass
`server/.venv/bin/python3 server/plane/illustrations.py --validate`
as of this record (sha256 digests below computed directly against the
files currently vendored in this directory, `shasum -a 256 <file>`).

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `air-france.png` | Air France | Airbus A320 | 2008×783 | `eeeeb53cb687b6f2ab054984fcb7f4910c781be7641e2215ada947ad340a96d4` |
| `iberia-airlines.png` | Iberia Airlines | Airbus A320 | 2170×725 | `9873a243c6c75b65a5417b77486659fa94b72b8a8d193f3e94a2af4b624c7339` |
| `tap-portugal.png` | TAP Portugal | Airbus A321neo | 2073×758 | `984fa5682f53b82a35f2f974ce604e07d1b5810bc1cc8cf08c03648293f81164` |
| `air-algerie.png` | Air Algérie | Boeing 737-800 | 2073×758 | `e3e38c8685dd63cf5c6698178d2264e6a320ccddcb66b897aa72a6327c0de996` |
| `ccm-airlines.png` | CCM Airlines (Air Corsica) | Airbus A320 | 1735×906 | `21abe6cf667e955f4274b50ab9bbf489d743e5599f1f451ebf3a14547e32d6d4` |
| `vueling-airlines.png` | Vueling Airlines | Airbus A320neo | 1916×821 | `331ed5c7cfa763c48e7209ed3dfa61c989b387f1b12d5fa48470b297fd12322a` |
| `transavia-france.png` | Transavia France | Boeing 737-800 | 2078×757 | `a793210007eedaeb950e09f42459967e337dbc4c411d9bc41380e4a3c72cc933` |
| `generic-fallback.png` | *(none — the D-08 uncovered-airline / enrichment-failure fallback)* | unspecified, AI-generated (unbranded generic narrow-body jet, no airline identity per the prompt) | 2054×766 | `1e09d2ce8c251c861d4ec0bff4d76044228ae69b9b718a6fc49ac9f8a63fb11f` |

### Phase 3.1 batch (2026-08-27, 25 files)

All 25 files below are native RGBA PNGs, all at least 1200px wide, and all
pass `server/.venv/bin/python3 server/plane/illustrations.py --validate`
as of this record (sha256 digests computed directly against the files
currently vendored in this directory, `shasum -a 256 <file>`; pixel
dimensions read via Pillow `Image.open(path).size`).

**Airline primary files (15) — the carrier's numerically dominant type:**

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `easyjet.png` | easyJet | Airbus A320neo | 1774×887 | `0c7fbfb7cb54980549eb31a9755745ec31b1dc64ad7a5c32bb645fbd984a1e2d` |
| `wizz-air.png` | Wizz Air | Airbus A321neo | 2072×759 | `6a964206e077f4a0c591310471893121ef3753c35c32f11ba0bc158b24aeb68d` |
| `volotea.png` | Volotea | Airbus A320 | 2053×766 | `600f5aad2b67ed8d3dcde1b94a3ac303bd6542562a665849ce88e6be8425f351` |
| `ita-airways.png` | ITA Airways | Airbus A321neo | 2172×724 | `0e0ade845ac994d5d0f1d9ea399482b6969e48eba20c440477b90c6637a3cc00` |
| `air-europa.png` | Air Europa | Boeing 737-800 | 1997×788 | `62b00637e4e98174c2505abb4d39bc885cbc81c1a28d35661d15db6e9496134b` |
| `royal-air-maroc.png` | Royal Air Maroc | Boeing 737 MAX 8 | 2048×768 | `5f91c708f20a24f8998040ec0c28affa22478022699bbb41fee0714a44b20149` |
| `lot-polish-airlines.png` | LOT Polish Airlines | Embraer E195 | 2172×724 | `7c258442bcab8cd80e3903eccf13d171f06dd8dec6dcfc917ee56c61a6f8b844` |
| `air-caraibes.png` | Air Caraïbes | Airbus A350-900 | 2172×724 | `fdd7c38784ebd7b73fb8c1412f64fcd123a15290044bb4235ec0db1a39baaef1` |
| `french-bee.png` | French Bee | Airbus A350-900 | 2048×768 | `30180fb1a3ac75280a12b8263223feb246fe4f53fd5db44e60eb7df322f711a1` |
| `europe-airpost.png` | Europe Airpost (adsbdb-resolved pre-2016-rebrand name for ASL Airlines France — see Naming rules) | Boeing 737-800 | 1967×799 | `e768d1977d89ed59ad56238e534c267634ebe504c5af55e1cb0c96beeb66eecc` |
| `tunisair.png` | Tunisair | Airbus A320neo | 1962×801 | `45da829a1889e11ce9a41878ac779c92278422c9873c0d1a067f51bedb9506a9` |
| `pegasus-airlines.png` | Pegasus Airlines | Airbus A321neo | 2087×754 | `b1b1172a6dc8e1b379206b9dbecf58564b84b2842f3b55ae5fbf7eacb31e8c33` |
| `chalair-aviation.png` | Chalair Aviation | ATR 72 | 2068×760 | `7526a7feba31bad21a7016af5b6f2e19d3438cd5f6edd13c1a91e917f42fcfd4` |
| `twin-jet.png` | Twin Jet | Beechcraft 1900D | 1926×816 | `1cca1686cce71aeec6adce4b5b8cebaa1ddd324af8682f8738b7095cc1ccca70` |
| `corsairfly.png` | Corsairfly (adsbdb-resolved prior-brand name for Corsair International — see Naming rules) | Airbus A330-900neo | 2172×724 | `80b5fdb68038195611282f8a1612cdd187f88ae506a32fc6d3230b8261dbe68c` |

**Airline secondary-variant files (3) — mixed-fleet minority types, P-04:**

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `ccm-airlines-atr72.png` | CCM Airlines (Air Corsica) | ATR 72-600 | 1881×836 | `ee422917de57506d77420b491eee6971a841620a10dc60cf138bc3d6f2fb86e8` |
| `transavia-france-a320.png` | Transavia France | Airbus A320neo | 1774×887 | `bca0bd1f345e9a8f8e223f371765e88eecc4db1fe44af055a32535d28bcc9aa8` |
| `air-caraibes-a330.png` | Air Caraïbes | Airbus A330-300 | 1991×789 | `71a1e71069599c931421859cdb5c3110274b7d00668d08c0d8c6d9e26b101ffd` |

`royal-air-maroc-embraer.png` was delivered in the 2026-08-27 follow-up
batch documented below.

**Neutral shape fallbacks (7, D-07 tier) — serve no specific carrier:**

Every file in this group carries no airline identity, no livery colours, no
tail markings and no logo shapes — neutral brushed-metal/grey tones only, per
`HANDOFF.md`'s Requirements table. `Airline served` is intentionally "none"
for all seven.

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `generic-a320.png` | *(none — D-07 neutral shape fallback)* | A320-family shape | 2048×768 | `d64c370f80604732d429ec3c3978961e09b5e72df6112256e3ab42a3981ea898` |
| `generic-b737.png` | *(none — D-07 neutral shape fallback)* | B737-family shape | 2103×748 | `c5da4e6ad0eff8ac846be7c67becee434f22335ad176f9b1e26f52eab88d99c0` |
| `generic-atr72.png` | *(none — D-07 neutral shape fallback)* | ATR 72 shape | 2048×768 | `fceda76659d5c65137ca67c4fb62ffae91e867e040343a21bd9aaa4269c9c6ff` |
| `generic-beechcraft1900d.png` | *(none — D-07 neutral shape fallback)* | Beechcraft 1900D shape | 1870×841 | `96b36bd7c0fba610a49e4e5d8e3e92dfc2907deebf2d727b3dd1500cf049c74c` |
| `generic-embraer.png` | *(none — D-07 neutral shape fallback)* | Embraer E-Jet shape | 2172×724 | `4554ad60f6390d54f8c80504adcabbace04aefa508f1a04aa681fac6d4a61e6f` |
| `generic-a330.png` | *(none — D-07 neutral shape fallback)* | A330-family shape | 2172×724 | `11ec3c888fa12247a93708c91688c8a1eccfcd4859392de65173c825c52b5be1` |
| `generic-a350.png` | *(none — D-07 neutral shape fallback)* | A350-family shape | 2172×724 | `b39ac32f818397a8f3745591fc6fa03725674dd1e54d5f1e12aa1f561d8639ac` |

### `_unresolved/` — generated but NOT selection targets (not shipped assets)

These two files exist on disk (required here only so
`scripts/check-attribution.sh` — which recurses — passes; they are invisible
to `server/plane/illustrations.py --validate`, which does a non-recursive
directory listing) but correspond to **no `(airline, shape)` combination any
code path can ever select**. A future reader must not mistake these for
shipped, reachable art.

| Filename | Why it is not a target | Dimensions (px) | sha256 |
|---|---|---|---|
| `_unresolved/la-compagnie.png` | Same situation as Amelia International. `03.1-LIVE-RESOLUTION.md` Step C marks La Compagnie `[UNRESOLVED]`: its real-world ICAO code (`DJT`) is independently confirmed via Wikipedia, but `adsbdb`'s own database resolves that exact code to an unrelated US airline ("Denver Jet"), and no real La Compagnie callsign was available this session to determine what a genuine flight actually returns. Kept for future reference only; same remediation path as Amelia. | 2048×768 | `b3acb6f628bae81c29c7cce6796b72880e2b19277cf692b284a3b8487192f4f9` |
| `_unresolved/air-caraibes-atr72-unused.png` | Superseded draft retained only for historical reference. A separately audited `air-caraibes-atr72.png` is now a canonical target. | 2172×724 | `f7a682ae42c45a351949797eb2f62cb2eb51537cc2320a2e7189390e1843f8d3` |

The aircraft-type column mirrors `server/assets/icons/VENDOR.md`'s
existing "Selected aircraft types" list, cross-checked against
`HANDOFF.md`'s "Suggested generation prompts" section, which names one
type per airline (Air France A320, Iberia A320, TAP A321neo, Air Algérie
737-800, CCM/Air Corsica A320, Vueling A320). `transavia-france.png` was
added later (commit `e52602e`, outside the original seven `HANDOFF.md`
prompts) and its type is recorded per `server/assets/icons/VENDOR.md`'s
summary rather than a `HANDOFF.md` prompt, since no prompt text for it
exists in that file.

## Local modifications

None for the Phase 3 baseline eight — all are used exactly as generated and
handed off; no post-processing, cropping, or recompression was applied by
this project beyond what the generation tool itself produced.
`server/assets/icons/VENDOR.md` records that TAP and Air Algérie were
regenerated once each, before hand-off, after a visual check found an
opaque vignette in earlier drafts — the digests above are for the final,
delivered, `--validate`-passing versions only; no earlier draft is vendored
or recoverable from this repo. None of the 25 Phase 3.1 files were
post-processed either — each was delivered, validated, and eye-confirmed
(nose-left, type-matches-filename) exactly as generated.

**Post-delivery accuracy correction (2026-08-27, same Phase 3.1 session):**
during interactive review, the developer's image tool had also regenerated
`tap-portugal.png` and `vueling-airlines.png` unprompted (both already had
delivered, validated Phase-3-baseline files). Side-by-side comparison found
both baseline files depicted **outdated liveries** — TAP's old red-cheatline
scheme (superseded by TAP's current geometric wordmark livery) and
Vueling's old solid-yellow-fuselage scheme (superseded by Vueling's current
white-fuselage `vueling.com` livery). The developer confirmed both
regenerated files as more accurate and approved the swap; the digests table
above reflects the replacement files. A third regeneration, Air Algérie,
was compared the same way and found **less** accurate than the existing
baseline (simplified tail logo, missing the real Algerian flag
crescent-and-star tail colours) — the developer kept the original
`air-algerie.png`, unchanged. The superseded TAP and Vueling originals are
not vendored anywhere in this repo; they exist only in git history at
commit `e0193e8` and earlier.

## Coverage note

**Phase 3 wording (superseded by the live re-check below):** the original
2026-08-26 record stated that no easyJet or KM Malta file existed because
`adsbdb` never resolved an `airline_name` for either carrier.
`03.1-LIVE-RESOLUTION.md` re-verified this live during Phase 3.1 and found
a more precise picture — easyJet actually operates under **two** AOC
prefixes, and only one of them resolves:

- **easyJet (`EZY`, UK AOC) resolves and gets a file (`easyjet.png`).**
  Re-confirmed live this phase (`EZY63GN` → `"easyJet"`, exact match). This
  is new coverage since Phase 3.
- **easyJet Europe (`EJU`, Austrian AOC) remains a confirmed, deliberate
  miss (P-03)** — `airline_name` is never available for those flights no
  matter how good an illustration exists, so no file is requested for it.
  This directory intentionally has no `easyjet-europe.png` or similar.
- **KM Malta Airlines (`KMM`) was excluded from the original live-resolution
  snapshot**, but explicit user-requested art coverage was added in the
  follow-up batch below. Live route resolution remains a separate enrichment
  concern.

## Phase 3.1 coverage

**Target:** 34 files total (8 already vendored from the Phase 3 baseline,
including `generic-fallback.png`, plus 26 new Phase 3.1 targets — see
`server/plane/illustrations.py`'s `target_filenames()` for the
authoritative enumeration; `HANDOFF.md`'s "Required files" section lists
the same 34 by name).
**Delivered in the original batch:** 25 of the then-26 outstanding targets.
The missing `royal-air-maroc-embraer.png` was delivered in the follow-up
batch below. `--outstanding` is the authoritative current state.

**D-03 airlines excluded from the target set (not "outstanding" — excluded
by design, per `03.1-LIVE-RESOLUTION.md`):**

- **La Compagnie** — `[UNRESOLVED]`. Its real-world ICAO code (`DJT`) is
  independently confirmed via Wikipedia, but `adsbdb`'s own database
  resolves that exact code to an unrelated US airline ("Denver Jet"), and
  no real La Compagnie callsign was available this session to determine
  what a genuine flight actually returns. See
  `_unresolved/la-compagnie.png` above for the disposition of the art
  generated for this excluded carrier.

The La Compagnie exclusion can be added to `_ILLUSTRATION_TARGETS` later
once a real callsign confirms its true selection-key string. Amelia is now
present as explicit user-requested product coverage; its live resolution
key remains a separate enrichment audit.

## Additional Air Caraïbes variants (2026-08-27)

These two native-RGBA variants were delivered during the preceding livery
audit and are now registered as exact selection targets.

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `air-caraibes-a350-1000.png` | Air Caraïbes | Airbus A350-1000 | 2117×743 | `1cba6996aaf0101444bad48a401b3ddecc27a181690e5db1ba71f0009e24f478` |
| `air-caraibes-atr72.png` | Air Caraïbes | ATR 72 | 2172×724 | `f7a682ae42c45a351949797eb2f62cb2eb51537cc2320a2e7189390e1843f8d3` |

## Follow-up aircraft batch (2026-08-27)

Generated with OpenAI's built-in image-generation tool as native RGBA PNGs,
using the same nose-left, horizontal side-profile and transparent-background
convention as the existing set. Liveries were checked against current
operator imagery before generation. In particular, the earlier
`_unresolved/amelia-international.png` was rejected because it depicted Air
Caraïbes rather than Amelia; it was removed instead of promoted.

| Filename | Airline served | Aircraft type / livery status | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `km-malta-airlines.png` | KM Malta Airlines | Airbus A320neo, post-2023 | 2017×780 | `57317df5cbb460889afd1358be7579f45d5f3742abfb594b222f7715f55bd38f` |
| `tuifly-belgium.png` | TUIfly Belgium | Boeing 737 MAX 8 | 2001×786 | `71605dfeee854ba4c296b242d31831a3fcee12d86d15d848dacb2b395d7390ea` |
| `amelia.png` | Amelia | Airbus A320, white tail with low emerald fuselage ribbons | 2084×754 | `58598c69094b4a77c79a61f588343c5159d38cce474b59f3fb431e4723f5cdd4` |
| `amelia-embraer.png` | Amelia | Embraer E145, verified white/dark-green livery | 2067×761 | `284e4947fe2f1b30c51ddd0bc9b6af6489ba3bd92f526800260435f65141aa53` |
| `air-france-hop.png` | Air France HOP | Embraer E190, post-2019 | 2135×737 | `20eb212ce74e744e7972a248d107a9cacae7b4003652f1d53a783861d8c1c995` |
| `air-france-hop-atr72.png` | Air France HOP | ATR 72-600, historical HOP! livery | 2056×765 | `6994215f6b85048f084cdf1900a86ad826f38cdecba569a92d9f6f8db69e3121` |
| `klasjet.png` | KlasJet | Boeing 737-800, current minimalist ACMI appearance | 2073×758 | `628557ff3171001d9dfd6b847f9c5471da9c6b6657b1006edc0d40d54a5e5f20` |
| `royal-air-maroc-embraer.png` | Royal Air Maroc | Embraer E190 | 1971×798 | `91079825f60d821e26cd787f95547934a5fc077f54bcb189f9a23a0f08161cd2` |

No post-processing, cropping, alpha replacement or background removal was
applied: the accepted files are the generator's native outputs. Each file
was checked for RGBA mode, transparent corners, non-opaque alpha, minimum
width, landscape framing, nose-left orientation, horizontal attitude and
aircraft-type/livery match.

**Amelia A320 correction:** after the first delivery, a user-supplied photo
of F-HDSJ showed that the initial illustration overextended the green graphic
onto the vertical tail and enlarged the wordmark. `amelia.png` was regenerated
with the real aircraft's plain white tail, modest uppercase `AMELIA` title and
two low emerald ribbons. A first correction draft that painted a checkerboard
was rejected as opaque RGB and never vendored; the accepted replacement is
native RGBA with transparent corners.
