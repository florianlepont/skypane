# Phase 62: Plane Screen Redesign (giant-lettering design) - Research

**Researched:** 2026-11-09
**Domain:** Pillow-based e-ink renderer (Spectra 6 palette-index canvases), per-frame device config, companion Personalisation tab, firmware ink masks
**Confidence:** MEDIUM-HIGH (code facts verified by reading and probing the repo; panel look is screen-render only until the owner checks glass)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Four layouts ship: A (large nose from the right edge, smaller rear half from the left edge below it), B (whole aircraft, centred), C (whole aircraft in its own band under the lettering), and A with the diagonal band. B and A-with-diagonal were mocked with the band; C was not and keeps its own look, which may need rework.
- D-02: The layout is a per-frame setting in the companion's Personalisation tab, next to the theme (`companion/pages/personalisation_cards.py`, `config_page.PERSONALISATION_ROUTES`). Default for a frame that chose nothing: B.
- D-03: The previous-flight card is removed in the new layouts (the old layout keeps it).
- D-04: The 18 themes are replaced, for the new layouts, by five field / lettering pairings: grey / black, light blue / blue, light red / red, light yellow / yellow, white / black. Stored old theme ids convert to the closest pairing.
- D-05: Yellow needs a lighter field (about 75% white) and, for small text, yellow dithered toward black.
- D-06: A landing uses a second colour the owner picks from the pairings (existing "theme when arriving" setting), not a fixed green. Direction is carried by field colour.
- D-07: Per-airline colour rules keep working: a rule resolves to a pairing.
- D-08: Anton (SIL OFL) vendored under `server/assets/fonts/` with licence text and a `VENDOR.md` entry. Flight screens: each line stretched to frame width; status screens natural proportions.
- D-09: Names split into 2-3 lines, never one, never cutting a word where a space or hyphen exists: spaces and hyphens first, then syllables. 100% automatic: no table of manual corrections, no admin editing of splits.
- D-10: Unknown destination, known airline: airline name in the giant lettering.
- D-11: Seven screens get the new look (watching, quiet hours, display off, battery empty, no connection, updating, retired); pairing does not. Generic: no band, no theme colours. Watching white/black ink; others dithered dark field with white ink.
- D-12: Calm layout: 110 px margins, Anton natural proportions, flush left, whole words only, each line sized to fit; production icon (about 120 px) top-left above the small label; small body text bottom-left. Watching "RUNWAY / 3" label "WATCHING"; updating "FIRMWARE / UPDATE" label "INSTALLING"; no connection "NO / CONNECTION".
- D-13: Status screens ship in portrait and landscape; landscape versions are designed in this phase.
- D-14: Masks for "no connection" and "updating" regenerated for the next firmware release (two colours exactly). No OTA pushed, nothing touches the live frame.

### Claude's Discretion
- Exact margins, line spacing, font sizes inside the mock-up ranges; how to redraw icons larger with clean edges; per-aircraft-type crop points for layout A.

### Deferred Ideas (OUT OF SCOPE)
- Real-panel contrast/dither check on glass (planned as an owner validation step inside this phase); redrawing aircraft illustrations if too soft when enlarged. Also out: pairing screen, any OTA push, anything in Phase 47, 47.1 or `hardware/`.
</user_constraints>

<phase_requirements>
## Phase Requirements (proposed; none existed)

| ID | Description | Research Support |
|----|-------------|------------------|
| PSR-01 | Legacy layout and every golden hash (`server/fixtures/golden/legacy_render_baseline.json`) unchanged; new layouts selected only by an explicit layout id | Renderer default `layout=None` = classic; new code paths only behind a layout id |
| PSR-02 | Anton vendored with OFL text and VENDOR.md entry; lettering stretched per line on flight screens | Font section |
| PSR-03 | Automatic 2-3 line destination splitter, deterministic, no table; airline-name fallback when destination unknown | Splitting section |
| PSR-04 | Five pairings; stored theme ids map to the closest pairing; colour rules, arrivals override and calendar theme resolve to a pairing | Theme/pairing section |
| PSR-05 | Four new layouts (A, B, C, A+diagonal) in portrait 1200x1600 and landscape 800x480, previous-flight card removed | Architecture |
| PSR-06 | Per-frame `layout` setting stored, validated, shown in the Personalisation tab (EN/FR) with preview | Companion section |
| PSR-07 | Seven status screens in the calm layout, portrait and landscape; firmware masks for no-connection/updating regenerated without a firmware code change or OTA | Status section |
| PSR-08 | New golden fixtures for new layouts (separate manifest); every output only uses the six legal palette indices | Test section |
| PSR-09 | Owner real-panel check recorded (contrast, dither, stretch distortion, yellow) | Owner section |
</phase_requirements>

## Summary

The renderer is a clean place for a second layout family. Everything flows through `layout.build_canvas()` (`server/plane/render/layout.py:428`), which already dispatches on an optional `profile` (landscape family at lines 459-469, legacy portrait otherwise). Callers pass `theme_id` only; seven `render.build_canvas` call sites in `server/poll_cycle.py` (lines 799, 801, 862, 1210, 1220, 1277, 1285, 1313) plus the companion previews (`companion/theme_preview.py:121`, `:~290`) are the only integration points. A new optional `layout` kwarg (default `None` = classic) keeps every golden case byte-identical, because `server/test_golden_render.py` calls `render_panel(...)` without it.

Colour, per-airline rules, arrivals override and calendar theme all resolve to a THEMES id (`server/plane/colour_rules.py:325-380`). The lowest-risk way to honour D-04/D-07 is to leave THEMES, device_config, colour rules and calendar rules untouched and add a pure mapping `theme id -> pairing` applied only by the new layouts. Use five existing ids as the canonical pairing ids (`white`, `grey`, `blue_light`, `red_light`, `yellow_light`) so every validator (`device_config._validate_theme_fields`, `form_post.resolve_theme`, rule add) keeps working with zero migration. Only a new `layout` key is added to device config, following the `timezone`/`detection` precedent (written only when set; `server/device_config.py:397-440`).

The hard technical items are: (1) lettering with strictly binary masks (soft masks blend palette indices, as `layout._threshold_alpha` documents), including two-tone lettering across the band; (2) the yellow 0.75 field, which breaks `_assert_legal_palette`'s "bg index is dominant" rule; (3) firmware masks: the new calm screens have a mask bounding box about 5x larger than today's, and regenerating forces edits to firmware host tests (not to firmware C code); (4) per-type crop points; (5) the splitter. A prototype splitter was run against about 80 names (see below).

**Primary recommendation:** Add a new render module family (`server/plane/render/giant/*`, new leaf `server/pairings.py` and `server/screen_layouts.py`), thread `layout` through `build_canvas` and `poll_cycle`, store `layout` as an optional device-config key defaulting to classic in stored config (see Conflict C1), and keep all new golden fixtures in a separate manifest.

## Conflicts and flags against locked decisions (do not override; owner/planner must resolve)

- **C1 (D-02 vs "not a pixel changes until the owner chooses").** D-02 says a frame that chose nothing defaults to B, but the phase goal and CONTEXT boundary say the current layout stays until the owner switches, and the live frame must not change at deploy. Recommendation: two separate defaults. The renderer default (`layout=None`) and the stored-config default for an absent key are `classic`. B is the pre-selected option offered in the picker and the value the planner flips `DEFAULT_LAYOUT_ID` to when the owner decides to switch (one constant + a new test). Needs owner confirmation.
- **C2 (D-09 "never one line" vs landscape mock-ups).** The brief's landscape (`landscape-800x480.png`, confirmed by viewing it) uses one stretched line across 800 px; D-09 says 2-3 lines. Recommendation: one line in landscape (validated mock-up), 2-3 in portrait. Needs confirmation. Also 1-3 letter names (Pau, Aix) cannot be split into pieces of at least 2 letters; recommend one line for names of 3 letters or fewer (prototype does this).
- **C3 (D-01 layout C).** C was never mocked with the direction/band and "may need rework". It needs a quick mock (extend `design-exploration/plane-screen/mock_plane_variants.py::v09`) and owner sign-off before its implementation plan, or C ships last and independently.
- **C4 (D-14 vs firmware test files).** "Regenerate masks" cannot be done by generator output alone: `firmware/tests/test_fault_screen.c` pins a golden digest (`FP_FAULT_SCREEN_GOLDEN_DIGEST`, line ~190) and assumes rows 100-299 are outside the mask (line ~87; mask Y is 625 today). Those tests, and the equivalent in `firmware/tests/test_updating_screen.c`, must be edited. No `firmware/main/*.c` change is needed. See Status section.
- **C5 (D-11 "retired").** The retired screen is not in `hold_screens.py`; it is `server/pairing_image.py:88 render_retired_image()` (label `_RETIRED_LABEL`, line 27). Restyle only that path; the pairing screen in the same module must stay byte-identical.
- **C6 (D-09 "spaces and hyphens first").** Interpreted as: if the name has any space/hyphen, split only there (no mid-word cuts); only a single-token name gets syllable cuts. A cost-based mixed approach cuts "Mallorca" in "Palma de Mallorca", which the prototype showed and which breaks D-09.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary | Rationale |
|------------|-------------|-----------|-----------|
| Layout/pairing selection, theme-to-pairing mapping | API/Backend (`server/`, poll cycle) | Companion (UI only) | Resolved at render time by the poll process |
| Rendering canvases (lettering, aircraft, band) | API/Backend (`server/plane/render`) | Companion preview calls same code | Single renderer; companion previews call `build_canvas` |
| Layout setting persistence/validation | Backend (`server/device_config.py`) | Companion form handler | Validation lives in device_config; form_post only gates membership |
| Personalisation picker | Companion (server-rendered HTML) | Browser JS | Existing pattern |
| No-connection/updating screens | Firmware (stamps committed mask) | Backend generates masks offline | Device draws them with no server round trip |
| Fonts/aircraft art | Static assets in repo | - | Vendored |

## Standard Stack

No new runtime dependencies (CLAUDE.md: stdlib + Pillow + requests only). Do not add a hyphenation library (pyphen etc.).

| Item | Version | Purpose |
|------|---------|---------|
| Pillow | 13.0.0 pinned (`server/requirements.in`); sandbox has 12.3.0 | Text masks, resize, paste. The golden manifest records the Pillow version (`test_golden_render.py` `test_manifest_records_the_installed_pillow_version`), so local runs on 12.3.0 may fail that test regardless of this phase [VERIFIED: repo] |
| Anton-Regular.ttf | Google Fonts `ofl/anton`, copyright 2020 The Anton Project Authors | Lettering |

**Anton vendoring facts** [VERIFIED: fetched this session from raw.githubusercontent.com/google/fonts/main/ofl/anton]: `Anton-Regular.ttf` 170,812 bytes, sha256 `a4ba3a92350ebb031da0cb47630ac49eb265082ca1bc0450442f4a83ab947cab`; `OFL.txt` 4,484 bytes, sha256 `ee67e6ee22790b7929f1a3769ca2801d565c64b5a9096942c1adf5596de9c9e4`. This was fetched from the `main` ref, which `server/assets/fonts/VENDOR.md` forbids (it pins a commit SHA per font). The commit SHA could not be resolved (GitHub API refused in this session): the executor must resolve the latest commit touching `ofl/anton` via the GitHub API, re-download from that SHA, re-hash, and record SHA, retrieval date and digests in `VENDOR.md` (follow the Zilla Slab entry format) plus `server/assets/fonts/Anton-OFL.txt`. Keep it byte-for-byte unmodified. Glyph check [VERIFIED: probe]: Latin accents (É È Ç Œ ß ñ) and `’ – - ·` present; Anton has no Cyrillic/Greek/CJK.

## Package Legitimacy Audit

No new packages. Anton is a font file, not a package; its provenance is the pinned google/fonts commit + sha256 (above). slopcheck not applicable.

## Architecture Patterns

### Where the new family plugs in (answers Q1)
```
poll_cycle (ctx.device_cfg["layout"], ctx.effective_theme_id)
   -> render.build_canvas(..., layout=)            layout.py:428
        profile landscape?  -> landscape.build_landscape_canvas(layout=)   landscape.py:15
        layout in NEW_IDS?  -> giant.build_canvas(layout, profile/size, ...)   (new)
        else                -> existing legacy code (unchanged)
giant.*:  pairings.pairing_for_theme(theme_id) -> field + ink + small-text ink
          lettering.split_destination(name) -> lines
          lettering.draw_lines(canvas, lines, box, ink, stretch=True)
          aircraft_halves / whole placement
          optional diagonal band (reuse layout.draw_diagonal_band geometry, style.BAND_*_FRAC)
```
Recommended structure (all new files; nothing existing renamed):
```
server/pairings.py                  # leaf: PAIRINGS, PAIRING_FOR_THEME, pairing_for_theme()
server/screen_layouts.py            # leaf: LAYOUT_IDS, DEFAULT/classic, normalise_layout_id()
server/plane/render/giant/__init__.py   # build_canvas(size, layout, ...) dispatch
server/plane/render/giant/lettering.py  # splitter + stretched line drawing + Anton loader
server/plane/render/giant/aircraft.py   # crop points, halo, placement
server/plane/render/giant/status.py     # calm hold screens (portrait + landscape)
server/test_giant_*.py, server/fixtures/golden/giant_render_baseline.json
```
Hard rules from the code:
- `hold_screens.py` must not import `layout.py` (cycle, `hold_screens.py:1-8`); the new `giant` package must be imported lazily from `build_canvas` like `landscape` is (`layout.py:462-463`).
- Portrait theme fallback `themes.theme_or_default(theme_id, profile.inks)` (`layout.py:460`) runs for profiles; pairings must also check ink availability (all 6 inks on every current profile, `hardware.py:309-310`).
- Landscape dispatch (`landscape.py:15-49`) derives all geometry from `size`; the new family should do the same (fractions of size, as `landscape_common.py`), so portrait and landscape are one code path with two geometry sets. The only landscape profile is the simulated `sim-landscape-800x480` (`hardware.py:205`); no real 800x480 hardware exists until Phase 58.
- The previous-flight card is simply not drawn (do not pass `previous_*` through).
- `quiet_hours`/`display_off`/`battery_empty`/`empty` today ignore theme (`layout.py:470-479`): status screens remain theme-free (D-11). `battery_empty` bytes must stay constant for the parked episode: the new version must be a pure function of nothing (no clock, no args).
- The "overhead" state also reaches the active renderer (`ACTIVE_STATES` in `landscape.py:11`): new layouts need a label and field colour for it (reuse the departing pairing, as `themes.theme_background_index` does).
- Arrival field: `colour_rules.resolve_effective_theme_id` already returns `theme_arriving` for arriving state (`:372-375`), so D-06 needs no new plumbing. If `theme_arriving` is unset, arriving renders as departing (indistinguishable): the new-layout picker should nudge users to pick one (UX, not code).
- Held-branch repaint (`poll_cycle.py:1267`) only re-renders on transitions: changing layout in the companion will not repaint until the next flight/transition, same as theme today. Acceptable; document it in the picker help text (EN/FR).

### Theme, layout and pairing storage (answers Q1)
- `device_config.load_device_config` (`:278-314`) returns a fixed 12-key dict and normalises each value; `_merged_config` (`:397`) writes optional keys only when set. Add `layout` exactly like `timezone`/`detection`: `normalise_layout_id(value)` (unknown -> classic), written only when not classic, `_validate_layout(layout)` raising ValueError, `save_device_config(..., layout=None)` carry-forward. Existing files keep their bytes.
- Tests asserting the exact loaded dict must be updated for the new key: `server/test_config_history.py:58,70,81,90,127,148`, `server/test_runway_config.py:158,229`, `server/test_detection_spec.py`, `companion/test_config_page_02.py`, `server/test_state_writers.py:78`. Budget a task for this; it is mechanical.
- Pairing ids = existing THEMES ids (`white`, `grey`, `blue_light`, `red_light`, `yellow_light`). `PAIRING_FOR_THEME` covers all 18 THEME_IDS (test: `set(PAIRING_FOR_THEME) == set(THEMES)`), proposed (owner-visible, tag as assumption A1): `white`->white; `black`,`grey`,`band_black`->grey; `blue`,`blue_light`,`band_blue*`->blue; `red`,`red_light`,`band_red*`->red; `yellow`,`yellow_light`->yellow; `green`,`green_light`,`band_green_light`->grey (no green pairing exists; neutral so a former green "arrivals" colour does not collide with a chromatic departure colour).
- Never rewrite stored values (themes.py:306-313 "Pure: stored configuration is never rewritten" is the project's convention). Conversion is at render time, so switching layout back and forth is lossless.
- Pairing parameters (from `design-exploration/plane-screen/mock_themes.py:56-83`): field = ink dithered toward white at 0.4 (grey/blue/red), yellow 0.75, white flat; lettering = pairing ink (yellow lettering plain yellow); small text = pairing ink, yellow small text dithered toward black about 45% (`mock_themes.darkened_ink`). With the band: solid ink band, lettering ink off-band and the light field shade inside the band (`mock_diagonal.py:main_colours`). White/black pairing was never rendered with the band: decide (recommend: no band for white/black, show black band with white inner tone; confirm at owner check).

### Companion (answers Q1 last part)
- Views are routes: `personalisation_cards.VIEW_ROUTES` (`personalisation_cards.py:47-55`) -> `config_page.PERSONALISATION_ROUTES` (`config_page.py:323`) -> `routes.py:138` and `app.py:1232`. `_FIELD_VIEWS` (`config_page.py:334`) maps a rejected field to its view; `form_post.resolve_theme` (`form_post.py:111`) and `config_page.py:896-900` are where fields are gated and saved.
- Recommendation: add a "Layout" view (new `VIEW_LAYOUT`, route constant in `companion/layout.py`, nav entry in `_views()` at `personalisation_cards.py:114`) with radio cards using the existing `look-pick__card` / `runway-card` idiom (`companion/settings/theme.py:278-313`), posting field `layout` through a new `form_post.resolve_layout` and `save_device_config(layout=...)`. Section carries `DIRTY_SECTION_ATTR` so the save bar works. The alternative (a card inside Departures) is simpler but the layout is not a departures-only setting.
- The existing Look picker is a three-axis (colour/background/stripe) model derived from all 18 themes (`companion/settings/look.py`, `look_model_json`). For a frame on a new layout, offer five pairing radio cards instead of the three-axis picker (`offered_theme_ids()` at `look.py:146` is the filter point: return the five pairing ids when the frame's saved layout is new). Keep the classic picker unchanged for classic.
- Previews: `theme_preview.frame_preview_png_bytes` (`~:283`) and `preview_png_bytes` (`:121`) call `build_canvas` without layout; cache keys (`frame_preview_signature`, `frame_cache_path` allow-lists) include theme/state/size only. Add `layout` to both signature and path allow-list, and bump `FRAME_PREVIEW_CACHE_VERSION` (currently 1) and `THEME_PREVIEW_CACHE_VERSION`; raise `FRAME_PREVIEW_CACHE_MAX_FILES` (96, sized for 18x2x2) for pairings x layouts. Preview routes validate allow-lists; add `layout` query param to the allow-list there.
- i18n: every user-facing string is bilingual via `i18n.msg("key", "English")` with French in `companion/i18n_fr/look.py` (a mechanical completeness harness exists per the skill). New strings: layout names, help text, pairing names, "repaints at next flight".
- Project skill `sketch-findings-skypane` governs the companion design system (tokens, cards, control density); reuse `.runway-card`/`.look-pick__card`, add no new custom properties or accent consumers (skill's recurring rule). Phase 61 (companion overhaul, plans 61-01..09 have summaries but the ROADMAP box is unchecked) also edits these pages: rebase check before touching `personalisation_cards.py`.

## Don't Hand-Roll

| Problem | Don't build | Use instead |
|---------|-------------|-------------|
| Palette legality | Custom index checks | Extend `layout._assert_legal_palette` (`layout.py:308`) with a "dominant index may be bg or white" parameter |
| Dithered fields | New dither | `dither.dithered_state_background(idx, lighten_fraction, size)` (`dither.py:45`); it has no assert on the fraction, only a docstring ("keep under 0.5"), so 0.75 works as is |
| Dither toward black for yellow small text | New algorithm | Same two-colour quantize recipe as `dithered_state_background` with palette {ink, black}; the mock `darkened_ink` is the reference |
| Diagonal band | New geometry | `layout.draw_diagonal_band` / `style.BAND_*_FRAC` (`layout.py:23`); landscape `landscape_card.band_edges` for 800x480 |
| Aircraft selection/size | New loader | `illustrations.select_illustration`, `layout._load_illustration_safely`, `_opaque_bbox`, `_threshold_alpha` |
| Mask packing for firmware | New tool | `firmware/tools/gen_fault_screen.py` (`_SCREENS` registry) |
| Hyphenation library | pyphen etc. | Not allowed (stdlib only); use the small vowel/digraph rule below |

## Fonts and Pillow feasibility (answers Q4)
- Current loader `text._font((path,size,weight))` caches `ImageFont.truetype` (`text.py:21-26`). Anton needs a new role constant like `style.PT_SERIF_BOLD` (`style.py:41-42`) plus `ANTON_REGULAR` path; small text in the mocks is Inter Bold (vendored, currently unreferenced by active roles, `server/assets/fonts/VENDOR.md` supersession notes). Decision needed (A2): small text in new layouts = Inter Bold (as validated in mocks) vs PT Serif Bold (current). Recommend Inter Bold; the OFL text is already vendored.
- Stretching: render the line at a large size (mock uses 600 px) into an "L" layer, then `Image.resize((box_w, slot_h), LANCZOS)` (`mock_giant_city.py:giant_text`). No Pillow feature beyond `getbbox`/`resize`. Fits the 80-line function gate easily if split: `measure_line`, `render_line_mask`, `stretch_mask`, `paint_mask`.
- **Mask must be binary** before pasting on a "P" canvas, or palette indices blend (`layout.py:194-202`). Threshold the stretched mask at 127 (optionally render 2x and downsample then threshold for cleaner edges). Do not use LANCZOS-resized soft masks directly. Compare threshold vs Floyd-Steinberg edge on glass (owner check).
- Accents: `É` bbox top is far above cap height (probe: bbox top 45 vs 185 for plain caps at 600 px). Measure line height from cap height (`H` bbox), not the line's ink bbox, or accented lines shrink every other letter. Let accents extend above the slot (clip at canvas margin).
- Stroke: at most 1 px added at 600 px (`heavy=1` in `mock_diagonal.py`); `stroke_width` at 600 px renders at most 0.17% of height, so effectively zero after downscale; drop it unless visual check demands it.
- Non-Latin/unsupported glyphs: detect with the font (compare `font.getmask(ch)` to a known-missing glyph) and fall back to NFKD ASCII, else to the airline name. adsbdb municipalities are Latin in practice [ASSUMED].
- Performance: poll is a 30 s systemd oneshot; mock-scale operations (600 px text layers, a few resizes) are sub-second [ASSUMED, measure in plan].

## Automatic city splitting (answers Q7)

Data available: `route["destination_city"]` / `origin_city` via `enrich.city_for_state` (`enrich.py:426`); already reduced to the first "/" segment (`_primary_city_name`, `enrich.py:131`) and sentence-cased via `str.capitalize()` per word (`to_sentence_case_city`, `enrich.py:114`), so hyphenated parts arrive as "Saint-étienne"-style odd case: always `.upper()` for lettering. En/em dashes appear in test fixtures (`test_golden_render.py` LONG_ROUTE): normalise to "-". Unknown destination: `city_for_state` is None/empty -> use `route["airline_name"]` via `text.display_airline_name` (D-10); neither -> keep the existing "Unknown flight" style fallback.

Rule (prototype in the session scratchpad, tested on about 80 names; pure function, deterministic; the planner should re-implement and unit-test it, not import the prototype):
1. Normalise: NFC, collapse whitespace, en/em dash to "-", upper case.
2. Tokens = split on spaces and hyphens (hyphen dropped, the line break replaces it).
3. If 2+ tokens: only word-level partitions into 2 or 3 contiguous lines (never cut inside a word, per D-09 / C6). Choose the partition minimising the worst horizontal stretch distortion: for each line `ln(stretch)` where stretch = (box_w / natural_width_at_cap_height_slot) using real Anton metrics; cost = max |ln stretch|. A line of 2 or fewer letters is rejected unless the whole name is that short (keeps "DE" alone off its own line).
4. If 1 token: syllable cuts into 2 or 3 chunks. Legal cut: both sides at least 2 letters, each side has a vowel (Latin vowel set incl. accented), not inside a protected digraph (CH PH TH GN QU SH CK GH, EAU OU EU AU AI EI OI). Cost as in 3 plus 0.12 per cut. If no legal cut exists, relax the vowel rule (Metz -> ME / TZ). If 3 letters or fewer: one line (C2).
5. Max 3 lines always. Cap the horizontal squeeze (long multi-word names such as "Compagnie Nationale Royale Air Maroc Express" squeeze about -1.0 in log terms): when worst stretch is below a floor (suggest ln 0.6), shrink the block height instead of squeezing further (design parameter; tune on glass).

Prototype outputs (examples, for expected-value tests): Nice -> NI/CE; Lyon -> LY/ON; Marseille -> MARS/EILLE; Toulouse -> TOUL/OUSE; Bordeaux -> BORD/EAUX; Barcelona -> BARC/ELONA; London -> LON/DON; New York -> NEW/YORK; Saint-Etienne -> SAINT/ETIENNE; Clermont-Ferrand -> CLERMONT/FERRAND is not what the cost picked (CLER/MONT/FERRAND came from the unrestricted run; under the strict rule it is two lines CLERMONT/FERRAND); Palma de Mallorca -> PALMA DE/MALLORCA; Villefranche-sur-Saone -> VILLEFRANCHE/SUR/SAONE (squeeze -0.70, shrink-block rule applies); Pau -> PAU. The syllable results are not typographic syllables (MARS/EILLE rather than the hand split MAR/SEI/LLE of the brief): they are balanced-width cuts at legal boundaries, which is what stretching needs. If the owner dislikes MARS/EILLE-style output, tune the cost (prefer 3 lines for 8+ letter single words, as the hand split did) rather than adding a table. Acceptance is a property test over a fixed list of at least 60 names (France, Europe, long, short, accented, hyphenated): 2-3 lines (1 only if at most 3 letters), no line under 2 letters, no word cut when a space/hyphen exists, worst |ln stretch| below a bound, and concatenation of lines (minus separators) equals the normalised input.

## Aircraft illustrations (answers Q5)
- 54 PNGs, 1672-2172 px wide (min enforced 1200, `illustrations.py:56`; actual min seen 1672), nose-left, alpha with a soft shadow band; the paste threshold is alpha > 127 (`layout.py:189`). Opaque content width about 1625-2150 px.
- Layout B at 1120 px wide and the whole-aircraft layouts downscale: no resolution problem. Layout A nose at "2200 px plane width, crop 50%" (`mock_plane_variants.py:vnose_tail`) is an upscale of about 1.0-1.3x for the smallest files (1672): mild softness; fine. Rear half is built from the 1250 px version, a downscale.
- The mock cuts at a fixed 0.5. Measured column heights show 0.5 passes through the wing or engine on many files (turboprops: 0.5 column about 330 px vs fuselage about 180-220). A per-type heuristic works without metadata: take the opaque alpha per column, search the 0.40-0.62 window of content width for the minimum smoothed column height (cuts through bare fuselage). Probe over all 54 files: minimum lands at 0.46-0.62 (mostly at the window's upper edge 0.58-0.62, i.e. behind the wing), with min column height within about 1.15x of the fuselage median. So the heuristic is viable; extend the window to about 0.70 for safety and cache the result per (path, mtime) like `_illustration_cache` (`layout.py:154`). Fallback fixed 0.5. Add a test over every vendored illustration: cut column height at most 1.3x the fuselage median and the cut x within 0.40-0.70. Outliers seen: `gendarmerie-nationale.png` (wide profile at 0.5, 405-538 px columns near the nose, probable large livery elements), `air-corsica.png`; inspect by eye.
- Halo: mock uses `MaxFilter(15)` of alpha as a white halo, then pastes RGBA. In production both halo and aircraft must be hard-thresholded (binary alpha), and the aircraft body is quantised with `dither.dither_to_full_panel_palette` (`dither.py:37`). A white halo over a dithered field costs nothing on index legality but the Floyd-Steinberg quantiser on a large aircraft is the "look on glass" risk the brief lists (item 6); put this in the owner check. `draw_illustration` (`layout.py:282`) already does quantise+threshold; reuse it per half and paint the halo first.
- Cuts must stay off-canvas: nose placed at `x = W - nose_w + overshoot`, rear at `x = -overshoot` (mock uses 30 px); add a test that the cut columns lie outside `[0, W]`.
- Aspect: uploaded override art (`illustrations.override_dir_for_state_dir`) may be any size within the pixel cap; the heuristic must work on it too.

## Dither and palette (answers Q6)
- 6 indices only; fields and lettering are all palette-index operations. Pattern fill technique: build canvas-sized "P" patterns (field pattern, ink flat) and `paste(pattern, (0,0), binary_mask)`; two-tone across the band: `mask_letters & band_mask` takes the field pattern, `mask_letters & ~band_mask` takes ink (`PIL.ImageChops.multiply/invert` on "L" masks). Never an RGB intermediate except for the aircraft, whose result goes through the six-colour quantiser.
- The "0.5 cap" is a docstring only (`dither.py:46-52`); `dithered_state_background(idx, 0.75)` works unchanged [VERIFIED: code + mock uses it]. The real blocker is `layout._assert_legal_palette(canvas, bg_idx)` (`layout.py:329`): `bg_count >= other_max`. For a 0.75 yellow field white pixels outnumber yellow, so the assert fails. Give the new family its own check (legal indices subset, plus "dominant index in {field ink, white}") rather than loosening the legacy function (its tests in `server/test_render.py` pin the message).
- Light-field background pixel counts: 0.4 lighten gives about 60% ink pixels, so grey/blue/red fields keep the ink dominant but the band (solid ink) can change dominance: the new check handles it.
- Low contrast risk: ink lettering on its own 40%-lightened field is the validated look on screen only; expectation that glass is softer is recorded in the brief. This is the main owner check.
- Firmware mask requirement (two exact colours) is unrelated to pairings: status screens only use black dither + white ink.

## Status screens (answers Q3)
Production today: `hold_screens.py` `_build_hold_canvas` (`:152`) with glyphs from `glyphs.py` (icons at 76 px class, constants `RUNWAY_ICON_HEIGHT_PX` etc.); landscape in `landscape_hold.py`. No-connection/updating canvases `_build_no_connection_canvas(flat)` / `_build_updating_canvas(flat)` (`hold_screens.py:93,113`) are pinned by golden cases `flat_no_connection` / `flat_updating` (`test_golden_render.py:135-136`) and by the firmware mask drift tests (`server/test_fault_screen_mask.py`, `server/test_updating_screen_mask.py`, which compare `gen_fault_screen.render_header_text()` to the committed headers).
- Therefore: do not modify those two functions. Add new `giant/status.py` builders; add new `_SCREENS` entries or repoint `flat_canvas_fn` in `firmware/tools/gen_fault_screen.py:_SCREENS` to the new flat builders. The golden cases keep hashing the old functions; the drift tests keep passing against regenerated headers. Keep the generator's dither spec (L=102, 0.4) untouched: the new server-side status field must also be dithered at 0.4 for parity (`hold_screen.c:DITHER_TARGET_LEVEL`).
- Mask size: today 564x340 (fault, `fault_screen_mask.h:12-16`, about 24 KB bits) and about 30 KB for updating. The calm layout's ink bbox spans about 980 px by 1200+ px (icon, label, two Anton lines, body): roughly 150 KB of bits per mask, about 300 KB for both, so about +250 KB flash in a 0x250000 (2.4 MB) OTA slot (`firmware/partitions.csv`) and about 5x text size in the committed header (the generator writes `0x%02x,` per byte: roughly 750 KB per header, vs 129/152 KB today). Current app size margin was not found in the repo docs: `.github/workflows/firmware.yml` builds the image in CI with `firmware/build.sh` and `check_production_config.sh built`, so CI will show whether it fits; the plan must include a size-budget check and this should be reported to the owner. Fallback if tight: shrink the body text out of the mask or lower icon size (the mask must stay one rectangle: `hold_screen.c:41-50`). Changing the mask format (RLE) needs a C change in `hold_screen.c` and is out of scope (Phase 57 owns the next firmware release content).
- Firmware tests to update with the regenerated headers (no C source changes): `firmware/tests/test_fault_screen.c` (golden digest `FP_FAULT_SCREEN_GOLDEN_DIGEST`, rows 100..299 field-purity check must move to a row range outside the new bbox), `firmware/tests/test_updating_screen.c`. Run `firmware/tests/run_host_tests.sh` (host gcc) to recompute the digest.
- Safe vs not: `firmware/` and `hardware/` are different directories. Phase 47/47.1 own `hardware/` and live-frame telemetry (STATE.md lines 43-44, 51); Phase 57 will edit firmware sources (image reader, 401 recovery) but has no plans yet. Safe in this phase: `server/**`, `companion/**`, regenerated `firmware/main/fault_screen_mask.h` and `firmware/main/updating_screen_mask.h`, `firmware/tools/gen_fault_screen.py`, and the two host tests above. Do not touch other `firmware/main/*.c|h`, `firmware/signing/`, `firmware/SIGNING.md`, any `fw-v*` tag, any release workflow. Pushing these to main triggers only `firmware.yml` (build+host tests); the release pipeline needs a `fw-v*` tag, so no OTA reaches a frame. Flag to the owner that the masks sit in main and ship with whatever Phase 57 releases next.
- Landscape status screens (D-13): none designed. The firmware screens are portrait-only (`FP_FAULT_SCREEN_WIDTH/HEIGHT` fixed, fault_screen.c static asserts), so landscape no-connection/updating can only be server-side concepts: the firmware for an 800x480 unit is Phase 58's. Design landscape status as 800x480 layouts derived from fractions (margin about 6.9% of the short side = 33 px, Anton natural proportions, icon about 60 px) and render them server-side; for no-connection/updating just generate previews, no masks.
- Retired: restyle `pairing_image.render_retired_image` only (see C5); the pairing screen and its tests (`server/test_pairing_image.py`) must stay unchanged.
- Icons at 120 px: glyph code draws at 76 px with fixed pixel constants (`glyphs.py` constants re-exported in `render/__init__.py:197-236`). Options: draw glyphs on a supersampled P/L canvas and downscale with a binary threshold (as the mock `icon_mask` does with L + LANCZOS), or add scaled variants of the drawers (`draw_*_icon(draw, cx, top, ink)` signature). Recommend a scale factor parameter in new code, not modifying existing glyph functions (they feed goldens).

## Tests and gates the work must satisfy (answers Q2)
- Golden: `server/test_golden_render.py` builds the case list from generator functions and compares each `render_panel(...)` SHA-256 to `legacy_render_baseline.json`; `test_manifest_case_names_equal_generator_case_names` requires names to match exactly, so do NOT add new cases to `golden_cases()`. Create a sibling `server/test_golden_giant_render.py` + `server/fixtures/golden/giant_render_baseline.json` (same pattern, own `print_manifest`). Include: 4 layouts x 5 pairings x departing/arriving (a representative subset keeps runtime sane: full cross product for one flight, plus long/short/accented/airline-only names on all layouts in one pairing), band on/off, landscape for each, 7 status screens x 2 orientations, and the flat no-connection/updating masks. The legacy suite doubles as PSR-01's proof; add one explicit test that `build_canvas(..., layout=None)` and `layout="classic"` equal the legacy bytes.
- `server/test_render.py` (161 tests) reads many `style` constants and rebinds `text` functions in tests (`text.py:6-10` note): do not rename or delete existing constants; put new constants in new modules.
- `server/test_render_profile_dispatch.py` is the template for dispatch tests (portrait profile equals None path; landscape native size 800x480, 192000 bytes).
- Companion: browser tests use pytest-playwright with shared fixtures (`companion/conftest.py`, `test-support/companion_app_server.py`); existing personalisation tests: `companion/test_browser_personalisation*.py`, `test_personalisation_page.py`, `test_personalisation_special_looks.py`, `test_theme_picker_profile.py`, `test_display_looks.py`, `test_browser_display_looks.py`, `test_config_page_*`. A new view changes counts/nav expectations in several of them. Behaviour-over-source rule: assert served HTML/CSS/JS or browser behaviour, never source text (`companion/test_suite_guards.py`). Browser tests must not skip when Chromium is missing (CI fails).
- Gates: ruff; mypy only for modules listed in `pyproject.toml` `[tool.mypy]` (new leaf modules `server/pairings.py`, `server/screen_layouts.py` are good additions: type-annotated, no Pillow); `scripts/check_function_size.py` (max 80 lines over `server`/`stub-server`; the existing hold builder is a 60-line function: keep new ones small, split pipelines); `scripts/check_comment_history.py` (no plan/phase/decision ids in comments, so reference design rationale, not "D-09" or "Phase 62"); coverage floor via `./scripts/run-all-tests.sh`; pytest-socket loopback-only guard (tests may not fetch the font: vendor it); `server/test_import_boundaries.py` (check new modules' import direction before landing: `server.themes` is leaf; new leaves must import only stdlib + `server.panel_format`); hash-locked requirements untouched.
- The palette legality must be asserted per rendered fixture (new `_assert_giant_palette`).

## Common Pitfalls
1. **Soft masks on P canvases** blend palette index integers into illegal colours. Always threshold text, halo and aircraft alpha. Warning sign: `_assert_legal_palette` failures or stray colours in previews.
2. **Accent height** shrinking whole lines (above). Measure with cap height.
3. **Yellow 0.75 field vs dominance assert** (above).
4. **Golden coupling**: editing `hold_screens._build_*_canvas`, `glyphs.*`, `style` constants, or `layout.py` helper behaviour changes goldens or firmware drift tests. New code, new modules.
5. **Preview cache poisoning**: caches keyed without layout serve the old picture for the new layout. Add layout to signature and bump versions.
6. **device_config exact-dict tests** break on the new key (list above).
7. **Held branch** does not repaint on settings change (existing behaviour).
8. **Header size**: committed mask headers grow about 5x; review diffs are huge, consider noting "generated" in `.gitattributes` if it already exists for the current headers [ASSUMED, check].
9. **Pillow version drift**: lettering/dither goldens depend on Pillow 13.0.0 (production pin); record fixtures under the pinned version in CI, not under the sandbox's 12.3.0.
10. **Single-line stretch distortion** of 3-letter and extreme names is a deliberate trade-off recorded in the brief; keep MAX stretch/squeeze parameters named constants so the owner's glass check can tune them without logic changes.

## Code Examples

Binary-masked lettering paint (pattern fill, safe on "P" canvases):
```python
# letters_mask: "L" stretched Anton line; band_mask: "L" polygon (layout.draw_diagonal_band geometry)
hard = letters_mask.point(lambda p: 255 if p > 127 else 0)
on_band = ImageChops.multiply(hard, band_mask)
off_band = ImageChops.subtract(hard, band_mask)
canvas.paste(field_pattern, (0, 0), on_band)   # light field shade inside the band
canvas.paste(ink_index, (0, 0), off_band)      # integer palette index fill
```
Pairing-aware check replacing `_assert_legal_palette` for the new family:
```python
legal = set(range(6)); used = {v for _c, v in canvas.getcolors()}
assert used <= legal
counts = {v: c for c, v in canvas.getcolors()}
assert max(counts, key=counts.get) in {field_ink_idx, IDX_WHITE}
```
Stretch distortion used by the splitter: `ln((box_w / font.getlength(line)) / (slot_h / cap_height))` with `cap_height = font.getbbox("H")` height at the same size.

## State of the Art
| Old | New | Impact |
|-----|-----|--------|
| 18 themes (flat / dithered / band) | 5 pairings (+ arrival pairing from the same five) | A pure mapping function; stored ids unchanged |
| PT Serif Bold/Regular text at about 20-40 px | Anton giant lettering + Inter Bold small text | New font roles, no change to old roles |
| Hold screens: centred 76 px glyph + tracked label | Calm layout flush left, 120 px icon | New builders; firmware masks regenerated |

## Assumptions Log
| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Mapping of old theme ids to pairings (green* -> grey, black -> grey, bands -> their colour) | Architecture | Owner may want different closest pairing; trivially adjustable table, covered by a coverage test |
| A2 | Small text in new layouts uses Inter Bold (as in the mocks) | Fonts | If PT Serif is wanted, role constants change only |
| A3 | adsbdb destination names are Latin script | Fonts | Non-Latin names fall back to ASCII transliteration or airline name |
| A4 | Lettering render time well under a second per frame | Fonts | Poll cycle budget; measure in plan |
| A5 | Mask flash growth (+250 KB) fits the 2.4 MB OTA slot | Status | Build fails or margin thin; CI build and `check_production_config.sh built` will show; fallback = smaller mask area |
| A6 | White/black pairing gets no diagonal band (never rendered) | Pairings | Owner may want a black band; confirm at mock stage |
| A7 | Committed mask headers may be marked generated in `.gitattributes` | Pitfalls | Cosmetic |

## Open Questions
1. Owner: C1 default (B vs classic until switch), C2 (one line landscape, 3-letter names one line), C3 (layout C design), green/arrival mapping (A1).
2. Is 0.4-lightened field with same-hue ink readable on glass at 2-3 m (brief says expected softer than a monitor)? Only the owner check answers it.
3. Whether the firmware has flash headroom for the larger masks (CI build answers it).
4. Whether the per-type cut heuristic needs a per-shape override for turboprops and `gendarmerie-nationale` (visual review of all 54).

## Environment Availability
| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python 3 / Pillow | render | yes (3.13.18 / 12.3.0) | Production pin Pillow 13.0.0, Python 3.14; goldens need the pinned version |
| `server/.venv` | project commands | present (`bin`, `include` dirs) | use it for tests |
| Docker (`espressif/idf:v5.3.1`) | firmware build | not probed | CI `firmware.yml` builds; host tests need gcc (`firmware/tests/run_host_tests.sh`) |
| GitHub API | resolve Anton commit SHA | no (access not enabled in this session) | Executor resolves it |
| Playwright Chromium | companion browser tests | not probed | CI requires it |

## Validation Architecture
| Property | Value |
|----------|-------|
| Framework | pytest + xdist + cov, pytest-playwright for companion |
| Quick run | `server/.venv/bin/python3 -m pytest server/test_giant_*.py server/test_golden_giant_render.py -x` |
| Full suite | `./scripts/run-all-tests.sh` (+ `firmware/tests/run_host_tests.sh` for mask changes) |

| Req | Behaviour | Type | Command |
|-----|-----------|------|---------|
| PSR-01 | legacy hashes unchanged; `layout=None`/`classic` equals legacy | golden | `pytest server/test_golden_render.py server/test_render_profile_dispatch.py` |
| PSR-02 | Anton loads, OFL text present, VENDOR.md entry present (assert served/vendored files exist and hash matches, not source text) | unit | `pytest server/test_giant_fonts.py` |
| PSR-03 | splitter property tests over a 60+ name list | unit | `pytest server/test_giant_split.py` |
| PSR-04 | every THEME id maps to a pairing; rules/arrival/calendar resolve to a pairing; stored ids not rewritten | unit | `pytest server/test_pairings.py` |
| PSR-05 | layouts render at 1200x1600 and 800x480, legal palette, cuts outside frame, no previous card | golden+unit | `pytest server/test_golden_giant_render.py` |
| PSR-06 | `layout` round-trips through `save_device_config`, absent key keeps file bytes, companion saves and previews it, EN/FR | unit+browser | `pytest server/test_device_config_layout.py companion/test_browser_personalisation_layout.py` |
| PSR-07 | status screens; regenerated headers equal generator output; host C tests pass | unit | `pytest server/test_fault_screen_mask.py server/test_updating_screen_mask.py`, `firmware/tests/run_host_tests.sh` |
| PSR-09 | owner glass check | manual | below |

Wave 0 gaps: new test files above; update the exact-dict config tests; a manifest-print helper for the giant goldens.

## Risks, ordering and suggested waves (answers Q8)
Wave 1 (parallel, no dependencies): (a) vendor Anton + VENDOR.md + OFL; (b) `server/pairings.py` + `server/screen_layouts.py` + tests; (c) splitter module + property tests; (d) device_config `layout` key + exact-dict test updates; (e) crop-point heuristic + test over all 54 PNGs; (f) status-screen mock for landscape and layout C mock (design, no code deps), owner-facing.
Wave 2: lettering renderer (stretched binary lines, two-tone band, new palette check); aircraft placement (A, B) using (e); portrait active-flight canvas for B, A, A+diagonal; dispatch in `build_canvas` and `poll_cycle` threading of `layout`.
Wave 3 (parallel): landscape family for the layouts; calm status screens portrait + landscape + retired; companion Layout view, pairing picker, previews/caches, i18n; layout C after sign-off.
Wave 4: giant golden manifest; firmware mask regeneration + host test updates + CI size check; docs (`docs/`, `server/README.md`, `hardware`-free).
Wave 5 (owner): glass check. Produce a packed `panel.bin` set for each pairing and each of the 4 layouts plus status screens in both orientations using the existing manual-QA CLI (`python -m server.plane.render`, `cli.py` gets `--layout`), serve via the stub/byos on a non-live unit only (the live frame is off limits; Phase 58's unit or none): owner judges contrast of ink on 40%-lightened fields, yellow (0.75 field, dithered small text), binary lettering edges, stretch distortion of 3-4 letter names, aircraft quantiser halo, and 2-3 m legibility. Record in a phase handoff; tune named constants only.
Not doable here: real-glass judgement; yellow ink readability; whether firmware flash fits (needs the build).
Do not touch: `hardware/`, Phase 47/47.1 files, any firmware `.c`/signing/release file, production data; never merge to main (CI deploys).

## Security Domain
Applies lightly. V5 input validation: the layout id is allow-list validated in `device_config` and `form_post` (reject unknown, never echo raw); preview routes allow-list layout/theme/state/size (existing pattern, `theme_preview.py` path components only from allow-lists); route city/airline strings are untrusted network data: only used as glyph text (no path or format-string use), length-bound them before splitting (cap about 80 chars) to avoid pathological layout cost. CSRF/auth: reuse the existing settings form POST (CSRF already covered by `companion/test_csrf.py`). Font and masks are repo assets, no runtime download.

## Sources
- Primary (read in this session): `server/plane/render/{layout,landscape,landscape_common,landscape_card,hold_screens,text,style,__init__}.py`, `server/{device_config,themes,hardware,panel_format}.py`, `server/plane/{dither,colour_rules,illustrations,enrich}.py`, `server/poll_cycle.py`, `server/test_golden_render.py`, `server/test_render_profile_dispatch.py`, `server/test_fault_screen_mask.py`, `companion/pages/personalisation_cards.py`, `companion/settings/{theme,look,form_post}.py`, `companion/theme_preview.py`, `firmware/tools/gen_fault_screen.py`, `firmware/main/hold_screen.c`, `firmware/tests/test_fault_screen.c`, `firmware/partitions.csv`, `design-exploration/plane-screen/*.py`, the design brief and its images.
- Probes this session: Anton glyph/metric checks; column-profile analysis of all 54 illustration PNGs; splitter prototype over about 80 names.
- Fetched: google/fonts `ofl/anton` (font and OFL), main ref only, SHA to be pinned.

## Metadata
**Confidence:** stack HIGH (no new deps, Anton verified); architecture HIGH (call sites verified); splitter MEDIUM (prototype, outputs not visually reviewed); firmware mask impact MEDIUM (size estimate, no build); glass look LOW until the owner check.
**Research date:** 2026-11-09. **Valid until:** about 30 days or until Phase 61 changes the Personalisation pages.
