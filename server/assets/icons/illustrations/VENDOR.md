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
- **Generation date:** 2026-08-26.
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

All eight files are native RGBA PNGs, all at least 1200px wide, and all
pass `server/.venv/bin/python3 server/plane/illustrations.py --validate`
as of this record (sha256 digests below computed directly against the
files currently vendored in this directory, `shasum -a 256 <file>`).

| Filename | Airline served | Aircraft type | Dimensions (px) | sha256 |
|---|---|---|---|---|
| `air-france.png` | Air France | Airbus A320 | 2008×783 | `eeeeb53cb687b6f2ab054984fcb7f4910c781be7641e2215ada947ad340a96d4` |
| `iberia-airlines.png` | Iberia Airlines | Airbus A320 | 2170×725 | `9873a243c6c75b65a5417b77486659fa94b72b8a8d193f3e94a2af4b624c7339` |
| `tap-portugal.png` | TAP Portugal | Airbus A321neo | 2084×755 | `5eff5068b7f0a40a052f339f0ce4dc0425a42ca1c0e0a5412f7e53393470d7ac` |
| `air-algerie.png` | Air Algérie | Boeing 737-800 | 2073×758 | `e3e38c8685dd63cf5c6698178d2264e6a320ccddcb66b897aa72a6327c0de996` |
| `ccm-airlines.png` | CCM Airlines (Air Corsica) | Airbus A320 | 1735×906 | `21abe6cf667e955f4274b50ab9bbf489d743e5599f1f451ebf3a14547e32d6d4` |
| `vueling-airlines.png` | Vueling Airlines | Airbus A320 | 2135×736 | `4d590607c5a4b51ff4d1be8b36f0625f3d8ae6cc2bc7c82a29dce793af6e885c` |
| `transavia-france.png` | Transavia France | Boeing 737-800 | 2078×757 | `a793210007eedaeb950e09f42459967e337dbc4c411d9bc41380e4a3c72cc933` |
| `generic-fallback.png` | *(none — the D-08 uncovered-airline / enrichment-failure fallback)* | unspecified, AI-generated (unbranded generic narrow-body jet, no airline identity per the prompt) | 2054×766 | `1e09d2ce8c251c861d4ec0bff4d76044228ae69b9b718a6fc49ac9f8a63fb11f` |

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

None — all eight files are used exactly as generated and handed off; no
post-processing, cropping, or recompression was applied by this project
beyond what the generation tool itself produced. `server/assets/icons/VENDOR.md`
records that TAP and Air Algérie were regenerated once each, before
hand-off, after a visual check found an opaque vignette in earlier
drafts — the digests above are for the final, delivered, `--validate`-passing
versions only; no earlier draft is vendored or recoverable from this repo.

## Coverage note

Per `HANDOFF.md` and `server/plane/illustrations.py`'s module docstring:
no easyJet (`EJU`) or KM Malta (`KMM`) file exists or was requested —
`adsbdb` never resolves an `airline_name` for either carrier, so a file
for them would never be selectable by `select_illustration()`. This
directory intentionally has no such files.
