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
| `air-corsica.png` (renamed from `ccm-airlines.png`, 260827-kih) | Air Corsica (adsbdb still resolves the pre-2013-rebrand name "CCM Airlines" - see Naming rules) | Airbus A320 | 1735×906 | `21abe6cf667e955f4274b50ab9bbf489d743e5599f1f451ebf3a14547e32d6d4` |
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
| `asl-airlines-france.png` (renamed from `europe-airpost.png`, 260827-kih) | ASL Airlines France (adsbdb still resolves the pre-2015-rebrand name "Europe Airpost" — see Naming rules) | Boeing 737-800 | 1967×799 | `e768d1977d89ed59ad56238e534c267634ebe504c5af55e1cb0c96beeb66eecc` |
| `tunisair.png` | Tunisair | Airbus A320neo | 1962×801 | `45da829a1889e11ce9a41878ac779c92278422c9873c0d1a067f51bedb9506a9` |
| `pegasus-airlines.png` | Pegasus Airlines | Airbus A321neo | 2087×754 | `b1b1172a6dc8e1b379206b9dbecf58564b84b2842f3b55ae5fbf7eacb31e8c33` |
| `chalair-aviation.png` | Chalair Aviation | ATR 72 | 2068×760 | `7526a7feba31bad21a7016af5b6f2e19d3438cd5f6edd13c1a91e917f42fcfd4` |
| `twin-jet.png` | Twin Jet | Beechcraft 1900D | 1926×816 | `1cca1686cce71aeec6adce4b5b8cebaa1ddd324af8682f8738b7095cc1ccca70` |
| `corsair.png` (renamed from `corsairfly.png`, 260827-kih) | Corsair (adsbdb still resolves the prior-brand name "Corsairfly" — see Naming rules) | Airbus A330-900neo | 2172×724 | `80b5fdb68038195611282f8a1612cdd187f88ae506a32fc6d3230b8261dbe68c` |

**Airline secondary-variant files (3) — mixed-fleet minority types, P-04:**

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `air-corsica-atr72.png` (renamed from `ccm-airlines-atr72.png`, 260827-kih) | Air Corsica (adsbdb still resolves the pre-2013-rebrand name "CCM Airlines" — see Naming rules) | ATR 72-600 | 1881×836 | `ee422917de57506d77420b491eee6971a841620a10dc60cf138bc3d6f2fb86e8` |
| `transavia-france-a320.png` | Transavia France | Airbus A320neo | 1774×887 | `bca0bd1f345e9a8f8e223f371765e88eecc4db1fe44af055a32535d28bcc9aa8` |
| `air-caraibes-a330.png` | Air Caraïbes | Airbus A330-300 | 1991×789 | `71a1e71069599c931421859cdb5c3110274b7d00668d08c0d8c6d9e26b101ffd` |

Note: `royal-air-maroc-embraer.png` (Royal Air Maroc's minority Embraer E190
variant) is target #28 of this tier (per `--targets`' current numbering)
and remains **outstanding** — not yet generated. See the coverage section
below for the exact list delivered.

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

These three files exist on disk (required here only so
`scripts/check-attribution.sh` — which recurses — passes; they are invisible
to `server/plane/illustrations.py --validate`, which does a non-recursive
directory listing) but correspond to **no `(airline, shape)` combination any
code path can ever select**. A future reader must not mistake these for
shipped, reachable art.

| Filename | Why it is not a target | Dimensions (px) | sha256 |
|---|---|---|---|
| `_unresolved/amelia-international.png` | **Status changed by quick task 260827-kih (2026-08-27): Amelia IS now a real selection target** (`amelia.png`/`amelia-embraer.png`, live-verified ICAO prefix `AIA` - see the Naming rules/Coverage caveat sections above and `enrich.py`'s `_AIRLINE_NAME_CORRECTIONS`). This specific file remains a non-selectable holding-directory artifact anyway, for two independent reasons: (1) its filename (`amelia-international.png`) does not match either derived slug (`amelia.png`/`amelia-embraer.png` - the carrier's confirmed name is "Amelia", not "Amelia International"), and (2) its depicted aircraft type was never recorded or eye-verified against either target's requirement (A320 primary / Embraer E145 secondary) at the time it was generated. The developer may promote it to a real target by `git mv`-ing it to the correct filename *after* confirming by eye which type it depicts and that the nose points left, or may simply regenerate fresh art from `HANDOFF.md`'s prompts #25/#30 instead. Original disposition, for the record: generated speculatively under the old, incorrect "Amelia International" name before `03.1-LIVE-RESOLUTION.md` Step C marked that name `[UNRESOLVED]` (neither the guessed candidate ICAO code `AMB`, resolving to a German air-ambulance operator, nor the two-independently-sourced candidate `AEH`, per airhex.com and French Wikipedia, resolved to Amelia in `adsbdb` - a real, live `AEH`-coded flight was confirmed that session to actually belong to Aviaexpress, Hungary). | 2135×736 | `e0e4679ddc236206e446669a970d29c527f88687e8a522c05758edf7b921dc98` |
| `_unresolved/la-compagnie.png` | Same situation as Amelia International. `03.1-LIVE-RESOLUTION.md` Step C marks La Compagnie `[UNRESOLVED]`: its real-world ICAO code (`DJT`) is independently confirmed via Wikipedia, but `adsbdb`'s own database resolves that exact code to an unrelated US airline ("Denver Jet"), and no real La Compagnie callsign was available this session to determine what a genuine flight actually returns. Kept for future reference only; same remediation path as Amelia. | 2048×768 | `b3acb6f628bae81c29c7cce6796b72880e2b19277cf692b284a3b8487192f4f9` |
| `_unresolved/air-caraibes-atr72-unused.png` | Air Caraïbes' ATR72 fleet is explicitly documented in `03.1-CONTEXT.md` D-03 as staying in-Caribbean, not Orly-relevant — `_TYPE_SHAPE_BUCKETS`'s atr72 comment in `illustrations.py` does not list Air Caraïbes among that shape's airlines. There is no `("Air Caraïbes", "atr72")` entry in `_ILLUSTRATION_TARGETS` and none can ever be reached by `select_illustration()`. Kept only in case the shape-bucket granularity changes later. | 2172×724 | `f7a682ae42c45a351949797eb2f62cb2eb51537cc2320a2e7189390e1843f8d3` |

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
- **easyJet Europe (`EJU`, Austrian AOC) shares `easyjet.png` with `EZY` —
  no separate file is requested for it**, because `EJU` and `EZY` are the
  same brand and quick task `260827-hyy`'s `enrich.airline_from_callsign()`
  resolves `EJU` straight to `"easyJet"` via the ICAO-prefix table. This
  directory intentionally has no `easyjet-europe.png` or similar. (Corrected
  2026-08-27, quick task `260827-jz6`: the prior wording said no file was
  requested because the airline name was never available for `EJU` — that
  was true before `260827-hyy` shipped and is no longer the reason.)
- **KM Malta Airlines (`KMM`) is now a target (`km-malta-airlines.png`),
  added by quick task `260827-jz6` (2026-08-27).** It is still a confirmed
  permanent `adsbdb` miss — live-verified this session,
  `curl https://api.adsbdb.com/v0/callsign/KMM466` returns
  `"unknown callsign"`. The reason it is no longer excluded: quick task
  `260827-hyy`'s `enrich.airline_from_callsign()` resolves the carrier
  straight from the ICAO prefix, so an `adsbdb` miss no longer costs the
  airline identity. See the new "Quick task 260827-jz6" subsection below for
  the full record.

## Phase 3.1 coverage

**Target:** 34 files total (8 already vendored from the Phase 3 baseline,
including `generic-fallback.png`, plus 26 new Phase 3.1 targets — see
`server/plane/illustrations.py`'s `target_filenames()` for the
authoritative enumeration; `HANDOFF.md`'s "Required files" section lists
the same 34 by name).
**Delivered this batch:** 25 of the 26 outstanding targets.
**Outstanding from the Phase 3.1 batch:** 1 file —
`royal-air-maroc-embraer.png` (Royal Air Maroc's minority Embraer E190
secondary variant, P-04). Reason: not yet generated. The developer's Task 2
hand-off was an explicitly named partial batch. Real flights of Royal Air
Maroc detected as the B737 shape are unaffected (Tier 2, the
`royal-air-maroc.png` primary file, already covers them); only the rarer
Embraer-shape secondary variant falls through to Tier 3 (`generic-embraer.png`)
or Tier 4 until this file is delivered. Nothing else in the Phase 3.1 target
set is silently dropped. See "Quick task 260827-kih" below for the current
project-wide total of 5 outstanding files (the "Quick task 260827-jz6"
subsection immediately below records the intermediate 3-file total as of
that session).

### Quick task 260827-jz6 (2026-08-27) — two new targets, both outstanding

Target count: **34 → 36** (two new primary targets added). Outstanding
count: **1 → 3**. Neither new file was generated by this task — both await
an external developer-side generation batch per D-09, so neither has a
sha256/dimensions row yet; a digest row is added to the tables above only
once a real file lands on disk and passes `--validate`.

| Filename | Airline | Aircraft type | Livery |
|---|---|---|---|
| `km-malta-airlines.png` | KM Malta Airlines | Airbus A320neo | Post-2023 livery: white fuselage, red two-tone Maltese Cross tail, blue/red accents — not the superseded Air Malta red-tail scheme |
| `tuifly-belgium.png` | TUIfly Belgium | Boeing 737 MAX 8 (split-tip winglets) | Current TUI "Dynamic Wave" livery: light blue/white fuselage, blue wave sweep, red TUI titles, red "smile" tail logo — not the superseded Jetairfly scheme |

Live-curl evidence (2026-08-27, this session):

- `curl https://api.adsbdb.com/v0/callsign/KMM466` → `"unknown callsign"` —
  a confirmed permanent miss. KM Malta Airlines replaced Air Malta (ICAO
  `AMC`, ceased March 2024) and `adsbdb` was never updated for the 2023
  rebrand. Reachable only via `enrich.airline_from_callsign()`'s ICAO-prefix
  path (quick task `260827-hyy`).
- `curl https://api.adsbdb.com/v0/callsign/JAF7521` → resolves, returning
  `"Jetairfly"` (the pre-2016 legacy brand).

**QT-jz6-D-02 (named override, accepted consequence):** the developer chose
`"TUIfly Belgium"` as the current-brand filename despite `adsbdb`'s live
`JAF7521` hit resolving to `"Jetairfly"` — a deliberate exception to the
Europe Airpost/Corsairfly/CCM Airlines stale-brand-mirroring precedent, not
an oversight. Accepted consequence: an `adsbdb`-hit render shows the legacy
`"Jetairfly"` string and falls through to a lower illustration tier
(`generic-b737.png`), while the airline-only fallback render shows
`"TUIfly Belgium"` and reaches `tuifly-belgium.png` directly. Both correctly
identify the real carrier; the divergence is cosmetic, not a wrong-carrier
claim. See `HANDOFF.md`'s Naming rules section for the full record.

**No PNG artwork was generated by this task.** Both files await an external
developer-side generation batch per D-09.

**D-03 airlines excluded from the target set (not "outstanding" — excluded
by design, per `03.1-LIVE-RESOLUTION.md`):**

- **Amelia International** — `[UNRESOLVED]` **through Phase 3.1 only.**
  **Status changed by quick task `260827-kih` (2026-08-27): this carrier IS
  now a real target** (`amelia.png`/`amelia-embraer.png`, filed as
  "Amelia", not "Amelia International" — see the "Quick task 260827-kih"
  subsection immediately below for the full live evidence). At the time
  this exclusion was recorded (Phase 3.1), no adsbdb code could be trusted:
  the guessed candidate (`AMB`) resolved to a wrong airline, and the two
  independently-corroborated candidate (`AEH`) was confirmed via a real
  live flight to actually belong to Aviaexpress (Hungary), not Amelia. See
  `_unresolved/amelia-international.png` above for the disposition of the
  art generated under the old, incorrect exclusion.
- **La Compagnie** — `[UNRESOLVED]`, still excluded. Its real-world ICAO
  code (`DJT`) is independently confirmed via Wikipedia, but `adsbdb`'s own
  database resolves that exact code to an unrelated US airline ("Denver
  Jet"), and no real La Compagnie callsign was available this session to
  determine what a genuine flight actually returns. See
  `_unresolved/la-compagnie.png` above for the disposition of the art
  generated for this excluded carrier. Can be added to
  `_ILLUSTRATION_TARGETS` later with zero other code change, once a real
  callsign confirms the carrier's true selection-key string.

### Quick task 260827-kih (2026-08-27) — Amelia added, three files renamed, correction mechanism introduced

Target count: **36 → 38** (Amelia's primary + Embraer secondary added;
`server/plane/illustrations.py --targets` now lists 38 lines).
Outstanding count: **3 → 5** (both new Amelia files await an external
generation batch per D-09; neither has a sha256/dimensions row yet — added
only once a real file lands on disk and passes `--validate`). Full current
outstanding list (5): `km-malta-airlines.png`, `tuifly-belgium.png`,
`amelia.png`, `royal-air-maroc-embraer.png`, `amelia-embraer.png`.

**Four files renamed with `git mv` (history preserved), digests carried
over verbatim — the bytes did not change, only the path did (QT-kih-D-04):**

| Old name | New name |
|---|---|
| `ccm-airlines.png` | `air-corsica.png` |
| `ccm-airlines-atr72.png` | `air-corsica-atr72.png` |
| `europe-airpost.png` | `asl-airlines-france.png` |
| `corsairfly.png` | `corsair.png` |

**The correction mechanism.** `server/plane/enrich.py` gained a
prefix-scoped correction seam this session: a module-level
`_AIRLINE_NAME_CORRECTIONS` dict, keyed on `(ICAO callsign prefix, the
exact airline_name string adsbdb returns)`, a `correct_airline_name()`
function that consults it, and `apply_airline_name_correction()`, applied
at a single seam inside `lookup_route()` — corrects every adsbdb-sourced
route, fresh or cached, before the caller ever sees it. The cache still
stores adsbdb's raw payload (correction is applied on read, never on
write), so an already-deployed `poll_state.json` starts producing corrected
names on the very next poll, with zero migration. Full detail, including
the machine-checked cross-table invariant that keeps
`_ICAO_AIRLINE_PREFIXES` and `_AIRLINE_NAME_CORRECTIONS` from disagreeing,
lives in `enrich.py` itself and in `test_enrich.py`.

**Live-curl evidence for the new AIA prefix (2026-08-27, this session):**

- `curl https://api.adsbdb.com/v0/callsign/AIA6412` → a populated 200
  result, `airline.name` = `"Avies"`, `airline.country` = `"Estonia"` —
  recorded verbatim in `server/fixtures/adsbdb_hit_AIA6412.json`. Avies is
  a real but *defunct* Estonian carrier (ceased operations 2016) that
  happened to hold the ICAO prefix `AIA` before ceasing; `adsbdb` was never
  updated. This is a **worse failure mode** than the three renames above —
  not a stale label for the same real airline, but an actively wrong
  carrier attribution. The real ICAO prefix `AIA`/Amelia is independently
  corroborated by Flightradar24 (live-tracked flight 8R6412 as callsign
  8R/AIA), Airhex, Wikipedia, ERAA and IATA.

**Two new outstanding targets, both flagged moderate-confidence on
livery detail (see `HANDOFF.md` prompts #25/#30 for the full note):**

| Filename | Airline | Aircraft type | Livery (moderate confidence) |
|---|---|---|---|
| `amelia.png` | Amelia | Airbus A320 | White fuselage, blue tail, lowercase "amelia" wordmark |
| `amelia-embraer.png` | Amelia | Embraer E145 | Same livery, on the regional-jet airframe (Amelia's real Orly-relevant Pau service type, per `03.1-CONTEXT.md` D-03) |

**KM Malta Airlines and TUIfly Belgium (quick task `260827-jz6`) are
untouched by this session (QT-kih-D-07) — see the Naming rules section of
`HANDOFF.md` for why the correction seam was deliberately NOT extended to
`JAF` this session, even though it could trivially cover the same failure
mode.**

**No PNG artwork was generated by this task.** Both Amelia files await an
external developer-side generation batch per D-09.
