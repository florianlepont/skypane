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
| `air-algerie.png` | Air Algérie | Boeing 737-800 | 1774×887 | `9c519bca126c416715893bd672b41340a3f8617e5fc9205fe4c87a73bcb141e6` |
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
| `easyjet.png` | easyJet | Airbus A320neo | 1774×887 | `79f3295f07367da9187fae7ad9eaa7bfe73781ff3f3b0d57a02486e6b2bc12ad` |
| `wizz-air.png` | Wizz Air | Airbus A321neo | 2103×748 | `0b5cc7a13751c811076b7638fd473e30d7911a2f88a632bc6434bb037d59f164` |
| `volotea.png` | Volotea | Airbus A320 | 1774×887 | `c6d7b4a47cdc03165982f3582129d68b13dd8f34c199c9ec92eb4e57a7ca7e01` |
| `ita-airways.png` | ITA Airways | Airbus A321neo | 2138×735 | `27840fae3041edd404f2b109026eca42e2319ef0709a140fb1a83dcb7df8d568` |
| `air-europa.png` | Air Europa | Boeing 737-800 | 1672×941 | `5cf3fd251f28ae55634f4681cdb857082c6d0a83988c309807922ec6a3384068` |
| `royal-air-maroc.png` | Royal Air Maroc | Boeing 737 MAX 8 | 1774×887 | `462775d3534dad7fce8733ac6888c783a221c9aa73bcc602e7ccc80afdbc99ba` |
| `lot-polish-airlines.png` | LOT Polish Airlines | Embraer E195 | 1994×789 | `8f972d953b1fcd0407e83661b18c07f64266f2dc18d75b67e78fbf91fd53da45` |
| `air-caraibes.png` | Air Caraïbes | Airbus A350-900 | 2135×736 | `e0e4679ddc236206e446669a970d29c527f88687e8a522c05758edf7b921dc98` |
| `french-bee.png` | French Bee | Airbus A350-900 | 2073×758 | `6b7209d25f09076067665fd0729b9b8f43851738aab942a7b1e23506891927f7` |
| `asl-airlines-france.png` (renamed from `europe-airpost.png`, 260827-kih) | ASL Airlines France (adsbdb still resolves the pre-2015-rebrand name "Europe Airpost" — see Naming rules) | Boeing 737-800 | 1672×941 | `09d7fe175aff73c8b98eb6f99400fce81a502a99d45d22ca59aff3ef1c34701d` |
| `tunisair.png` | Tunisair | Airbus A320neo | 1672×941 | `d837b45ae6b9caa506cbda3994ae14166afcfe2b8d32bfa2f44ae89f88443a80` |
| `pegasus-airlines.png` | Pegasus Airlines | Airbus A321neo | 1672×941 | `b973d7eb11d77d4f8f4e2a683007ee90e5e371d796eb7891c9b569cb5808f07c` |
| `chalair-aviation.png` | Chalair Aviation | ATR 72 | 1774×887 | `7554aabfbb89b4d9f0e47a523da02050367e686e9073bf7852d8b56776f4335b` |
| `twin-jet.png` | Twin Jet | Beechcraft 1900D | 1774×887 | `073ae62ffbb389cf9a354e8a3215006f0a708d2f38050df038f4ee61531f7529` |
| `corsair.png` (renamed from `corsairfly.png`, 260827-kih) | Corsair (adsbdb still resolves the prior-brand name "Corsairfly" — see Naming rules) | Airbus A330-900neo | 1672×941 | `0cab4949fe62f79eb9a7275a76ab0c703eefaedc0a393ef492f97d3aa6a5baf2` |

**Airline secondary-variant files (3) — mixed-fleet minority types, P-04:**

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `air-corsica-atr72.png` (renamed from `ccm-airlines-atr72.png`, 260827-kih) | Air Corsica (adsbdb still resolves the pre-2013-rebrand name "CCM Airlines" — see Naming rules) | ATR 72-600 | 1881×836 | `ee422917de57506d77420b491eee6971a841620a10dc60cf138bc3d6f2fb86e8` |
| `transavia-france-a320.png` | Transavia France | Airbus A320neo | 2080×756 | `0b38cd60da537c2d86a1371d9469b0ae282a64c9b674540ea9babcf78c5b62c1` |
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
| `generic-a320.png` | *(none — D-07 neutral shape fallback)* | A320-family shape | 1672×941 | `bb4e2aefe0fdb337b77eda1713a20308ba024992ee6f5c330249ccc09bd5d2bf` |
| `generic-b737.png` | *(none — D-07 neutral shape fallback)* | B737-family shape | 1672×941 | `f4fb6c57b2834afd2cc15d92496f9c8a6d0f16cbc4bff8d4abeef88167b35bad` |
| `generic-atr72.png` | *(none — D-07 neutral shape fallback)* | ATR 72 shape | 1774×887 | `1dd0a7ea19381f440ff55f39776d08a65933ea1c10a1e4759f27bdd6d1c3943d` |
| `generic-beechcraft1900d.png` | *(none — D-07 neutral shape fallback)* | Beechcraft 1900D shape | 1920×819 | `388c14cfb9cb064c97ed0c61206b86ac7e13aa203bfe1d8e2eccfe8f4f70dc14` |
| `generic-embraer.png` | *(none — D-07 neutral shape fallback)* | Embraer E-Jet shape | 2172×724 | `ba78794a0d37200291b53b8f2f7cdc7f8d1ca0949aab0a6e4da5f2b26b7f6723` |
| `generic-a330.png` | *(none — D-07 neutral shape fallback)* | A330-family shape | 1672×941 | `9668b91ff52283ad44d514eb74e528991dadb0792749923ca6968d019386a0e7` |
| `generic-a350.png` | *(none — D-07 neutral shape fallback)* | A350-family shape | 1774×887 | `459fa39fa8df935cd01480aebcec2e7e83c9f6a9f1904e8b23d427130263c9eb` |

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
**`royal-air-maroc-embraer.png`** (Royal Air Maroc's minority Embraer E190
secondary variant, P-04) was the one file left outstanding from this batch;
it was delivered in the 2026-08-27 follow-up batch documented below, by a
parallel session running the same day. Nothing in the Phase 3.1 target set
was silently dropped.

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

**No PNG artwork was generated by this task.** Both files awaited an
external developer-side generation batch per D-09 — since delivered by a
parallel session the same day; see the digest tables above and the
follow-up batch note below. `--outstanding` is the authoritative current
state at any given moment.

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
  live flight to actually belong to Aviaexpress (Hungary), not Amelia. The
  speculatively-generated `_unresolved/amelia-international.png` this
  exclusion produced has since been removed from disk (2026-08-27, by the
  same parallel session that delivered the real `amelia.png`/
  `amelia-embraer.png` art) — it is no longer present and no longer listed
  in the `_unresolved/` table above.
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
`amelia.png`, `royal-air-maroc-embraer.png`, `amelia-embraer.png`. See
"Quick task 260827-lgt" below for the current project-wide total of 8
outstanding files.

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

**Two new targets, initially flagged moderate-confidence on livery detail
pending generation (see `HANDOFF.md` prompts #25/#30) — since delivered and
corrected against a real reference photo; see the digest table and the
"Amelia A320 correction" note below for the actual, verified livery:**

| Filename | Airline | Aircraft type | Livery (moderate confidence at spec time) |
|---|---|---|---|
| `amelia.png` | Amelia | Airbus A320 | Originally specified as white fuselage, blue tail, lowercase "amelia" wordmark — corrected post-delivery, see below |
| `amelia-embraer.png` | Amelia | Embraer E145 | Same livery, on the regional-jet airframe (Amelia's real Orly-relevant Pau service type, per `03.1-CONTEXT.md` D-03) |

**KM Malta Airlines and TUIfly Belgium (quick task `260827-jz6`) are
untouched by this session (QT-kih-D-07) — see the Naming rules section of
`HANDOFF.md` for why the correction seam was deliberately NOT extended to
`JAF` this session, even though it could trivially cover the same failure
mode.**

**No PNG artwork was generated by this task.** Both Amelia files awaited an
external developer-side generation batch per D-09 — since delivered by a
parallel session the same day; see the "Follow-up aircraft batch" digest
table and the "Amelia A320 correction" note below.

### Quick task 260827-lgt (2026-08-27) — two new targets with art, one carrier deliberately sharing existing art

Target count: **38 → 41** (`server/plane/illustrations.py --targets` now
lists 41 lines: two new primaries, Air France Hop and KlasJet, plus one
new secondary, Air France Hop's ATR72 variant). Outstanding count:
**5 → 8**. Full current project-wide outstanding list (8, in `--targets`
order): `km-malta-airlines.png`, `tuifly-belgium.png`, `amelia.png`,
`air-france-hop.png`, `klasjet.png`, `royal-air-maroc-embraer.png`,
`amelia-embraer.png`, `air-france-hop-atr72.png`.

**Three new outstanding targets, none generated by this task:**

| Filename | Airline | Aircraft type | Livery | Confidence |
|---|---|---|---|---|
| `air-france-hop.png` | Air France Hop | Embraer E190 | Post-2019 Air France mainline white/blue scheme, small `HOP` titling — NOT the pre-2019 standalone HOP! livery | MEDIUM confidence on the Embraer-primary/ATR72-secondary fleet split (QT-lgt-D-04), not on the livery itself |
| `air-france-hop-atr72.png` | Air France Hop | ATR 72-600 | Same Air France regional livery as the primary, on the turboprop airframe | Same MEDIUM-confidence split as the primary |
| `klasjet.png` | KlasJet | Boeing 737-800 | White fuselage, abstract light-blue/yellow tail design | LOWER confidence than every other row in this table — livery not independently photo-verified, and the 737-800-vs-BBJ airframe choice is an open question for the developer at generation time (QT-lgt-D-08) |

**Live-curl evidence (2026-08-27, this session):**

- `curl https://api.adsbdb.com/v0/callsign/HOP4001` → a populated 200
  result, a real route (Nantes–Lyon), `airline.name` = `"Air France Hop"`.
  This is the first carrier this project has added where `adsbdb`'s own
  resolution is already correct and current — see the HOP row in
  `enrich._ICAO_AIRLINE_PREFIXES` for the full record. No
  `_AIRLINE_NAME_CORRECTIONS` row exists or is needed for `HOP`
  (QT-lgt-D-07).
- `curl https://api.adsbdb.com/v0/callsign/WMT3001` → a populated 200
  result, `airline.name` = `"Wizz Air Malta"` (a real, currently-flying
  Wizz Air Malta callsign, confirmed live this session). This is **not** a
  misattribution to correct — it is a correct, more-specific answer than
  this project's deliberately-chosen parent-brand key `"Wizz Air"`
  (QT-lgt-D-01/D-07), the same accepted-divergence class as `JAF`/TUIfly
  Belgium (QT-jz6-D-02). No `_AIRLINE_NAME_CORRECTIONS` row exists or is
  needed for `WMT`.
- `KLJ` (KlasJet): **never live-confirmed** this session or the planning
  session that preceded it — approximately 25 `adsbdb` queries across
  plausible flight-number ranges (including a synthetic `KLJ123` probe
  used only as this session's test callsign) all returned `"unknown
  callsign"`. KlasJet is a Lithuanian ACMI/wet-lease and VIP charter
  operator; wet-lease flights typically broadcast the contracting
  airline's callsign rather than their own, so a real `KLJ`-prefixed
  callsign may rarely or never appear at Orly. Included anyway, by
  explicit developer choice, with this uncertainty on record
  (QT-lgt-D-06).

**Wizz Air Malta (`WMT`) recorded as a non-outstanding item — a
deliberate reuse, not an omission.** `WMT` gets its own new row in
`enrich._ICAO_AIRLINE_PREFIXES`, mapping to the existing `"Wizz Air"`
target (already vendored, already digest-recorded above under the Phase
3.1 batch table) — the same brand-consolidation precedent the shipped
`EJU` → `"easyJet"` row already establishes. This adds **zero** files to
the artwork backlog: no new target, no new filename, no new sha256/
dimensions row. `wizz-air.png`'s existing digest row is unchanged.
QT-lgt-D-02: Wizz Air UK (`WUK`) is explicitly out of scope, was never
researched this session, and must not be added as tidy-up.

**No PNG artwork was generated by this task.** All three new files
(`air-france-hop.png`, `air-france-hop-atr72.png`, `klasjet.png`) awaited an
external developer-side generation batch per D-09 — since delivered by a
parallel session the same day; see the "Follow-up aircraft batch" digest
table below.

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
