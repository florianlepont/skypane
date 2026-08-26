# Phase 3: Visual Polish on Real Glass - Research

**Researched:** 2026-08-26 (updated 2026-08-26 following D-11/D-12/D-13: user chose full multi-color livery dithering over the 2-color alternative; updated again 2026-08-26 following D-14 through D-18: the "Full composition realignment" second scope expansion — serif typography, flight-number/destination co-equal hierarchy, and a dithered/photographic-toned background replacing the flat full-bleed field)
**Domain:** Pillow-based indexed-palette raster rendering for a 6-color e-ink panel; full 6-color Floyd-Steinberg dithering against a constrained hardware palette, now extended from a small illustration zone to most of the 1200×1600 canvas; OFL-licensed serif typeface selection for hard-edged e-ink glyph rendering; GSD human-handoff plan patterns
**Confidence:** HIGH on the dithering/compositing mechanics, INCLUDING the full 6-color path AND the full-canvas-scale background path (both locally verified this session against the actual installed Pillow 12.3.0 and the actual `server/panel_format.py` palette — see Standard Stack/Pattern 1 and the new "Full Composition Realignment" section's performance findings); MEDIUM on the serif font recommendation (license and general slab-serif e-ink-legibility reasoning are verified/well-established, but the claim that it visually matches flightportrait's actual wordmark font is `[ASSUMED]` — their font could not be identified with certainty from public sources); LOW on the real Spectra 6 panel RGB values, which are now load-bearing (D-13) and were confirmed **not publicly documented** by any authoritative source checked this session — a hardware-calibration fallback is proposed and is the primary recommendation over any found RGB estimate; LOW-MEDIUM on D-18's state-signal proposal, which is a design recommendation grounded in verified technical constraints, not itself independently hardware-tested this session

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A-02-02-01 departure threshold validation**
- **D-01:** No real runway-3 departure exists in Phase 1's captured sample data — verified directly this session: 0 readings with `vertical_rate >= +200 ft/min` across all 217 real in-geofence vertical-rate readings in `adsb-test/samples/*.jsonl`; the maximum observed was +48 ft/min (the known EJU84YF flare artefact already used in `server/test_runway_config.py`). A "replay a real captured departure" approach is not possible with existing data.
- **D-02:** Instead, force a **synthetic** departure render (vertical_rate >= +200 injected directly, same technique used in 02-05 Task 3 to force the "Route unavailable" fallback via `server.plane.render.render_panel()`) to visually confirm the DEPARTING state (Blue field, nose-right silhouette) renders correctly on real glass. This validates the *visual* rendering path only — it does **not** validate that +200 ft/min is the right real-world threshold value, since no real sensor data is used. That remains an explicit open item until a genuine runway-3 departure is observed in production.

**Frame mount status**
- **D-03:** The frame is currently on a desk / temporary location, not yet mounted on its final wall spot. Success criteria that depend on "typical wall-viewing distance" and "reads as ambient art on the wall" can only be judged provisionally at the desk this phase. Record this caveat explicitly in verification rather than treating a desk-distance judgment as final — a follow-up check once wall-mounted is a legitimate open item, not a blocker.

**Long-caption legibility stress test**
- **D-04:** Force `fit_text_size()`'s shrunk-overflow path deliberately by injecting a real flight with a genuinely long city and/or airline name through the production render code path (same forcing technique as D-02), push it live, and look at the glass.

**Aircraft illustration upgrade (the phase's expanded scope)**
- **D-05 (unlocking decision):** The user confirmed via SenseCraft that a personal photo displayed well on the real hardware, proving the panel renders dithered/photographic content well — the flat, no-dither rendering rule in `02-UI-SPEC.md` Revision 2 was a Phase 2 style choice, not a hardware limitation.
- **D-06:** The aircraft illustration becomes **per-airline**, not a single shared generic shape. Each detected flight renders a dithered illustration specific to its airline, resolved via the existing `server/plane/enrich.py` callsign→route lookup (already returns `airline_name`).
- **D-07:** Per-airline illustrations render **dithered/photo-like**, not the current flat single-color-fill treatment. The full-bleed background field and all caption text stay flat/solid as before (unchanged from `02-UI-SPEC.md` Revision 2); only the aircraft illustration itself changes rendering treatment.
- **D-08:** Fallback illustration (uncovered airlines, and the "Route unavailable" state) is a **single dithered generic illustration**, in the same rendered style as the per-airline set — not a return to the old flat-White CC0 silhouette.
- **D-09 (corrected during plan-phase, 2026-08-26):** Illustrations are **AI-generated by the user outside this session**, then handed to Claude as image files to process/vendor/integrate. This environment has no image-generation tool available. **Practical consequence for planning:** this phase has a real external dependency — the plan must account for the user supplying illustration files (probably as a `checkpoint:human-verify`-style gate or a `user_setup`-style block), with a defined handoff format (file naming, per-airline count, resolution) the planner should specify.
- **D-10:** Mirroring by departing/arriving state (nose-right for departing, nose-left for arriving) is unchanged and must still apply to every per-airline illustration and the fallback.
- **D-11 (post-research decision, 2026-08-26):** Research (`03-RESEARCH.md` Open Question #1) surfaced a genuine fork: 2-color dithering (White + state background, zero risk to the locked `02-UI-SPEC.md` Color contract and its existing tests) vs. full multi-color airline **livery** (matches the user's own "covering" phrasing, but reopens the locked Color contract and breaks 2 existing `server/test_render.py` checks that currently assert no Yellow/Red nibble appears). **User chose full multi-color livery.** This means: `02-UI-SPEC.md`'s Color section needs an explicit addendum (the aircraft-illustration zone gets a documented exception to the "White foreground only" rule in the active states), `_build_active_canvas()`'s "exactly 2 distinct palette indices" guard rail must be widened to allow the illustration's full legal palette usage, and `server/test_render.py`'s existing Yellow/Red reservation checks need updating to scope them to the *background/caption* elements only, not the illustration zone.
- **D-12:** Yellow (reserved for Phase 4's low-battery indicator, still upcoming) is **allowed** in illustrations if a real airline livery uses it — the user judged the illustration zone and a future low-battery indicator are visually/spatially distinct enough that reuse isn't confusing. Note: Red's original reservation (`02-UI-SPEC.md`'s cross-phase note cites "Phase 3's disruption banner (RER-03)") is itself stale — RER-03 was deferred to v2 in the 2026-08-11 scope cut, so Red has no real future consumer in this roadmap at all; Red is effectively free regardless of this phase's illustration work.
- **D-13:** Real Spectra 6 panel RGB reference values (flagged unverified since `02-UI-SPEC.md`'s original draft) **must be resolved this phase**, not deferred — load-bearing now that full-color livery quantization is chosen (per `03-RESEARCH.md` Open Question #2: nominal placeholder RGB values could cause livery midtones to map to visually wrong panel inks even though the wire format stays legal). Source from the Waveshare `EPD_13in3e` reference driver or the T133A01 panel datasheet, per `02-UI-SPEC.md`'s own original open note. **Resolved this session — see "Real Panel RGB Values" below: neither source publishes RGB data; a hardware-calibration fallback is recommended.**

**Full composition realignment with the real flightportrait product (second scope expansion, post-UI-SPEC-approval, this update pass)**
- **D-14 (reference evidence):** Real flightportrait.com product photography inspected directly this session (`poster-blue.jpg`, `print-detail.jpg`, saved to session scratchpad). Two structural differences from the locked design identified: (1) typography — flightportrait uses a small-caps/uppercase serif with wide tracking for its wordmark, current design uses Inter (sans-serif, Bold); (2) background — flightportrait's poster background is a softer, more photographic-toned field, current design uses a full-bleed saturated flat Blue/Green.
- **D-15 (typography):** Adopt a serif typeface direction, uppercase with wide letter-spacing for labels (matching the wordmark treatment), replacing Inter. Needs a real font choice + license vetted this phase (same OFL-style vendoring discipline as Inter in `02-UI-SPEC.md`'s Design System) — not yet chosen, left to research. **Resolved this session — see "Full Composition Realignment" below: Zilla Slab (OFL 1.1) recommended.**
- **D-16 (information hierarchy):** Flight number and destination/origin become co-equal in visual prominence (both primary), with airline name and other details subordinate below them — a change from the current design where flight number alone is the single largest hero element (88px Heading) and route/destination is a smaller Body-size line beneath it. The user's own words: "le numéro de vol et la destination sont tout aussi importantes. Viennent ensuite le nom de la compagnie et les autres informations." This is a deliberate middle ground, not a full adoption of flightportrait's much smaller/uniformly-discreet caption style.
- **D-17 (background treatment):** Move from the current full-bleed saturated flat Blue/Green to a softer, more photographic-toned background, dithered using the same Floyd-Steinberg mechanism already verified for the illustration zone — extended from "one small illustration zone" to "most of the panel." The user explicitly accepted that this reopens the on-glass legibility question already verified once in `02-05-SUMMARY.md` (white text on a saturated flat field was confirmed "clearly legible" there) — a fresh on-glass legibility check against the new busier/softer background is required before this phase can close, using the same `checkpoint:human-verify` pattern already established. **Performance investigated this session — see "Full Composition Realignment" below: negligible render-side cost.**
- **D-18 (state signal, Claude's discretion flagged explicitly):** Not yet decided how the departing/arriving Blue-vs-Green state distinction survives a shift away from "one saturated flat color = the whole message." Left to research/planning to propose, informed by D-17's constraint that the background is no longer a single flat legal index. **Resolved this session — see "Full Composition Realignment" below: three concrete options evaluated, one recommended.**

**Practical consequence:** the just-approved `03-UI-SPEC.md` (which explicitly scoped itself as "illustration zone only, everything else including background/typography unchanged from `02-UI-SPEC.md` Revision 2") is now superseded by D-14 through D-18 and needs a substantial Revision — not a full from-scratch redesign (spacing geometry, copywriting contract text, and the overall zone layout order stay locked), but a real revision covering typography, the background's color/rendering treatment, and the flight-number/destination hierarchy.

### Personal photo background — explicitly OUT of this phase's scope
- Discussed and explicitly deferred to v2 (`REQUIREMENTS.md` VIS-01), despite D-05's evidence it's technically viable.

### Claude's Discretion
- Exact airline coverage list for the generated illustration set — informed by real airline callsigns already seen in Phase 1 sample data and Phase 2's live enrichment cache.
- Exact image-generation tool/approach, prompt design, and post-processing pipeline (posterize/quantize/dither parameters) to get a generated illustration correctly onto the 6-color panel.
- Whether the generic dithered fallback illustration is airline-neutral art or a dithered re-render of the retired CC0 silhouette shape.
- ~~Panel RGB reference values (still unverified) — resolve only if load-bearing for the dithering work.~~ **Superseded by D-13 — no longer discretionary, resolved this session (see below).**

### Deferred Ideas (OUT OF SCOPE)
- **Personal photo as the panel's background** — confirmed technically viable (D-05), but explicitly deferred to v2 (`REQUIREMENTS.md` VIS-01). Do not implement or scope this phase's plan around it.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PLANE-01 | User can see flight number, airline, and destination for the next plane departing from Orly runway 3 | This phase's illustration-selection step keys directly off the `airline_name` field PLANE-01 already requires and 02-04 already renders as caption text — no new enrichment call. See Architecture Patterns "Illustration selection" below. |
| PLANE-02 | User can see flight number, airline, and origin for the next plane landing on runway 3 | Same illustration-selection mechanism applies identically for the arriving state; mirroring-by-state (D-10) is verified safe post-dither regardless of color count (see Common Pitfalls / Code Examples). |
</phase_requirements>

## Summary

This phase's engineering core is narrow and already fully traceable in the existing codebase: `server/plane/render.py`'s `_build_active_canvas()` composites a full-bleed state-color background, a flat White silhouette, and flat White caption text onto a Pillow `"P"`-mode canvas, then asserts (a "guard rail") that exactly 2 distinct palette indices exist before packing. Phase 3 adds a **new, spatially-scoped compositing step** — a full-color dithered per-airline illustration — dropped into the same zone-3 box `draw_silhouette()` already reserves, selected by `route.get("airline_name")` (already resolved by `server/plane/enrich.py`'s `lookup_route()`, already wired into `poll_loop.py`'s `run_once()`).

**D-11 resolved this phase's single most load-bearing open question: the user chose full multi-color airline-livery dithering, not the 2-color (White + state-background) alternative this research originally recommended as the zero-risk default.** This session re-verified the dithering mechanics under the *chosen* path (not just the rejected one): running `Image.quantize(palette=<a genuine 6-entry P-mode image built directly from server/panel_format.py's real PALETTE_RGB>, dither=Image.FLOYDSTEINBERG)` against a synthetic multi-hue test image, using the actual installed Pillow (12.3.0), produced output using **only the 6 legal panel indices** (`[VERIFIED: local execution, Pillow 12.3.0, this session]`) — confirmed by direct `getcolors()` inspection (indices `{0,1,2,3,4,5}`, all legal, zero illegal indices). A genuinely new, favorable finding for the full-color path: because `PALETTE_RGB`'s index order (0=Black…5=Green) already matches `panel_format.py`'s real `IDX_*` constants, **building the quantize target palette directly from `PALETTE_RGB` means the quantized image's local indices already ARE the canvas's real indices — no index-remap step is needed**, unlike the 2-color pattern's throwaway 2-entry palette (which required a `.point()` remap because its local 0/1 numbering had no relationship to the canvas's real constants). This is a materially simpler compositing pattern than the 2-color alternative this research originally proposed.

The direct consequence, worked through in full this session: `_build_active_canvas()`'s "exactly 2 distinct palette indices" guard rail **must** be widened, since a real dithered livery illustration will legitimately paint most or all of the 6 legal colors within its own bounding box. The correct replacement is a **spatially-scoped** guard, not a simple "raise the count ceiling" — everything **outside** the illustration's own bounding box (background field, state label, flight number, route/airline lines, bottom tag) must still contain **only** the state's background index and White, exactly as the locked `02-UI-SPEC.md` Color contract requires for every zone except the illustration. See Architecture Patterns Pattern 1 and Common Pitfalls Pitfall 1 below for the exact verified mechanism and Validation Architecture for the specific `server/test_render.py` line-by-line changes needed.

**Real Spectra 6 panel RGB values (D-13) were actively researched this session and confirmed genuinely unfindable from any authoritative source checked:** the Waveshare `EPD_13in3e` reference driver (`firmware/main/epd13in3e.c`, read in full this session — this project's own vendored port of it) contains **zero RGB/colorimetric data** — it is exclusively SPI register/command sequences (`R_PSR`, `R_CDI`, `R_DRF`, etc.) for driving the panel's dual controller chips; e-ink panels receive color-plane/nibble commands, not RGB values, so there was never RGB data to find in a firmware driver in the first place. Seeed's official industrial datasheet for this exact panel (SKU 100088646, fetched and read in full this session, `[VERIFIED: files.seeedstudio.com/Bazaar/product_pdf/100088646.pdf]`) likewise contains **no colorimetric/RGB specification whatsoever** — only mechanical dimensions, resolution, connector pinout, and a bare "Display Color: Black, White, Yellow, Red, Green and Blue" line. This is a **negative result actively verified**, not an assumption: neither of the two sources D-13/`02-UI-SPEC.md` named publishes RGB reference values, and this is unsurprising — E Ink's actual ink chromaticity is typically NDA'd manufacturer IP, not public datasheet content, for consumer/hobbyist-tier panels. See "Real Panel RGB Values" below for the community-sourced estimate found instead (LOW confidence, explicitly flagged) and the recommended hardware-calibration fallback (the user's own panel is already in hand and bring-up-verified, per `hardware/BRINGUP-LOG.md`).

**Primary recommendation:** Implement per-airline illustrations as full 6-color-palette Floyd-Steinberg-dithered art, spatially confined to the existing zone-3 box, composited via `Image.quantize(palette=<Image built from pf.PALETTE_RGB directly>, dither=Image.FLOYDSTEINBERG)` with **no remap step** (verified simpler than the originally-proposed 2-color pattern), selected by a new `normalise_airline_key(airline_name)` → filename lookup keyed off `enrich.lookup_route()`'s existing `airline_name` field. Widen `_build_active_canvas()`'s guard rail to a spatially-scoped check (full 6-color legal set inside the illustration's own bbox; exactly `{bg_idx, IDX_WHITE}` everywhere else) and update `server/test_render.py`'s two existing Yellow/Red reservation checks to the same spatial scoping (see Validation Architecture). Add a `02-UI-SPEC.md` Color-section addendum documenting the illustration-zone exception (draft text below). Resolve panel RGB via the hardware-calibration fallback, not the unverified community estimate alone — a `checkpoint:human-verify` task gating the illustration hand-off (specifying transparent-PNG format, nose-left source orientation, and the exact filename/count contract) remains necessary before any per-airline rendering code is written against real files, exactly as originally recommended.

**Third pass addendum (D-14 through D-18, this update): the composition realignment is a genuine widening of scope beyond the illustration zone, but it reuses the exact same verified dithering mechanism — nothing about the underlying mechanics changes, only the area it's applied to and what sits on top of it.** This session (1) selected and license-verified a real OFL serif typeface (Zilla Slab) suitable for both the small tracked uppercase labels and the larger co-equal flight-number/destination pairing, explicitly choosing a *slab* serif category to sidestep the thin-hairline e-ink legibility risk generically, rather than picking a high-contrast serif and hoping it holds up; (2) locally re-verified, against the real installed Pillow 12.3.0 and the real `PALETTE_RGB`, that Floyd-Steinberg-dithering a **full 1200×1600 canvas** (not just a small illustration box) costs ~47ms of render-side CPU time — utterly negligible against both the panel's own ~31.5s hardware full-refresh budget (`hardware/BRINGUP-LOG.md`) and any reasonable render-loop latency budget; (3) discovered, by direct local execution, that Pillow's built-in `ImageDraw.text(..., stroke_width=..., stroke_fill=...)` — a plausible-looking built-in "outline text for legibility" mechanism — actually **leaks illegal palette indices** (Yellow, Red) via anti-aliased edge blending even on a flat single-color background, and is therefore the **wrong** tool for keeping caption text legible over a busier dithered background; a flat "quiet-zone" rectangle drawn *before* the region is dithered is the verified-safe alternative (see Pattern 5 and Pitfall 7 below); and (4) evaluated three concrete options for D-18's open state-signal question and recommends Option (a) — two distinct dithered background "moods" (blue-toned vs. green-toned), reinforced by the state label text and existing silhouette mirroring as secondary non-color cues, not a single flat accent patch. **This does not change any of the illustration-zone-specific findings above (Pattern 1-4, Pitfalls 1-6) — those remain fully valid and orthogonal to this expansion; see "Full Composition Realignment" below for the new material.**

## Architectural Responsibility Map

This is not a multi-tier web application — it is a single Python process (`server/`) that renders a raw indexed-palette raster buffer and serves it over HTTPS to a firmware device with no rendering logic of its own. There is no browser, no CDN, no client-side compute. The table below maps this phase's capabilities onto the closest-fit tiers for planner sanity-checking.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Illustration selection (airline_name → filename) | API / Backend (`server/plane/render.py` or a new small module) | — | Pure function of already-resolved enrichment data; no new I/O, no new external call |
| Full 6-color dithered compositing (quantize + paste, no remap needed) | API / Backend (`server/plane/render.py`) | — | Same render pipeline that already produces the packed panel; must run inside `_build_active_canvas()` |
| Illustration asset storage | Database / Storage (filesystem, `server/assets/icons/`) | — | Static vendored files, same convention as the existing silhouette/glyph PNGs; no database exists in this project |
| Synthetic-render forcing (D-02/D-04 test renders) | API / Backend (direct `render_panel()` invocation, bypassing `poll_loop.py`) | — | Already-established pattern from 02-05 Task 3; no new architecture needed |
| Illustration hand-off from user | External (human) | — | Not a code tier at all — a `checkpoint:human-verify`/`user_setup`-style gate, per D-09 |
| Panel RGB calibration (D-13) | External (human, against physical hardware) | API / Backend (`server/panel_format.py`'s `PALETTE_RGB` constant, developer-preview-only) | No code tier can measure real ink color without a colorimeter (unavailable — e-ink displays don't support typical colorimeter probes, per community reports); a documented visual comparison against the real panel is the only feasible verification this project has |
| Serif typography (D-15) | API / Backend (`server/plane/render.py`'s font constants + `server/assets/fonts/`) | — | Same vendored-static-asset pattern already established for Inter — a font swap is a render-pipeline/asset change, not a new tier |
| Full-canvas dithered background compositing (D-17) | API / Backend (`server/plane/render.py`, extending `_build_active_canvas()`) | — | Same render pipeline that already produces the packed panel; verified this session to cost ~47ms extra CPU regardless of area covered — no new architectural tier is needed to absorb the scale-up |
| Departing/arriving state signal once the background isn't flat (D-18) | API / Backend (background-mood selection logic + existing silhouette mirroring/state-label text) | — | Purely a rendering/asset-selection decision inside the same pipeline; no new tier, no new external dependency |
| Fresh on-glass legibility re-verification (D-17's own instruction) | External (human, against physical hardware) | — | Not a code tier — a `checkpoint:human-verify` gate, same precedent as D-02/D-04/D-13's calibration pass |

## Standard Stack

### Core

No new runtime dependencies are needed. `Pillow==12.3.0` (already pinned in `server/requirements.txt`, verified installed via `server/.venv/bin/python3 -c "import PIL; print(PIL.__version__)"` this session — `[VERIFIED: local venv]`) already exposes everything this phase needs: `Image.quantize(palette=..., dither=Image.FLOYDSTEINBERG)`, `Image.transpose(Image.FLIP_LEFT_RIGHT)` for mirroring, and alpha-channel-aware `Image.paste(..., mask=...)` for compositing a non-rectangular illustration onto the canvas. Under the full-color path, `Image.point()` index remapping is **not needed** (see Summary/Pattern 1) — one fewer moving part than originally anticipated.

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Pillow | 12.3.0 (already installed) | Dithered quantization, alpha compositing, mirroring | Already the project's sole imaging dependency (`02-RESEARCH.md`'s Don't Hand-Roll table); `Image.quantize(palette=<Image>)` is the documented, built-in mechanism for "quantize to a palette of another image" — `[CITED: pillow.readthedocs.io/en/stable/reference/Image.html]`, re-verified this session against the real 6-color `PALETTE_RGB` |
| Zilla Slab | 1.501 (Mozilla's release, retrieved via Google Fonts) | Serif typeface for labels + flight-number/destination hero pairing (D-15) | Recommended this update pass — see "Full Composition Realignment" below for the full rationale. `[VERIFIED: web search, SIL OFL 1.1, Mozilla Foundation copyright, weights Light/Regular/Medium/SemiBold/Bold]`. Not a runtime dependency — a static TTF asset vendored the same way Inter already is |

### Supporting

None needed for the dithering/compositing pipeline. No background-removal library, no numpy, no scipy, no colorimeter-driver library (none exists that works with e-ink — see "Real Panel RGB Values" below) — see Don't Hand-Roll below for why an automated background-removal pipeline should specifically be avoided this phase. No new font-rendering library either — `ImageFont.truetype()` (already in use for Inter) loads any TTF including Zilla Slab's, and the existing `draw_tracked_text()` manual-tracking helper (used for the uppercase Label role since Phase 2) is font-agnostic and needs no change.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pillow's built-in `quantize(palette=..., dither=FLOYDSTEINBERG)` | A hand-rolled error-diffusion loop | No reason to hand-roll — Pillow's C implementation is already verified this session to produce exactly the 6 legal indices needed when fed a correctly-constructed 6-entry palette image built directly from `PALETTE_RGB` |
| Requiring transparent-PNG hand-off from the user | Automated background removal (e.g. `rembg`, a segmentation model) | Automated background removal would add a new, heavy dependency (`onnxruntime` or similar) requiring package-legitimacy vetting mid-phase, for a problem the user can trivially avoid by generating images with a transparent background in the first place (most modern AI image tools support this directly) |
| A community-sourced RGB estimate for `PALETTE_RGB` | A physical colorimeter measurement | No colorimeter reading was attempted or is recommended — e-ink displays are widely reported (Pimoroni forum, this session's research) as incompatible with typical consumer colorimeter probes (they require a lit/backlit or reflective-calibrated surface most colorimeters aren't built for); a documented visual side-by-side comparison against the real panel is the practical, achievable-without-new-equipment fallback |
| Zilla Slab (slab serif, uniform stroke weight) | Courier Prime (OFL 1.1, monospaced typewriter serif — closer stylistic match to flightportrait's specific "FLIGHTPORTRAIT" wordmark, which reads as typewriter-esque in the inspected print photo) | Courier Prime is also OFL-licensed and equally free of thin hairlines (typewriter faces have no stroke-width contrast by design), so it is a legitimate alternative for the *small tracked label text only*. It is not recommended for D-16's larger co-equal flight-number/destination pairing, because a monospaced face's fixed per-glyph advance makes long destination city names (already a flagged risk — D-04's stress test) render disproportionately wide compared to a proportional serif at the same point size, increasing how often `fit_text_size()`'s shrink path triggers. Using it would also mean vendoring a second serif family alongside Zilla Slab rather than one — worth it only if the user explicitly wants the closer typewriter-ticket look for labels specifically |
| A high-contrast "display" serif matching a more literal reading of flightportrait's wordmark (e.g. Playfair Display, Freight Display) | — | Explicitly rejected, not just deprioritized: high-contrast serifs have genuinely thin hairline strokes in their thin-to-regular cuts by construction (that contrast is the entire visual character of the category), which is exactly the e-ink legibility risk this research was asked to flag. Even restricting to a Bold/Black cut only reduces, but does not eliminate, stroke-width variation within a single glyph — a slab serif avoids the risk category entirely rather than mitigating it |

**Installation:** none — no new runtime packages. Zilla Slab is a static font asset to download and vendor (see "Full Composition Realignment" below), not an installable package.

**Version verification:** `server/.venv/bin/python3 -c "import PIL; print(PIL.__version__)"` → `12.3.0`, matching `server/requirements.txt`'s pin exactly. `[VERIFIED: local venv, this session]`

## Package Legitimacy Audit

Not applicable to the ecosystem package-legitimacy gate — this phase adds zero new npm/pip/cargo packages. `Pillow==12.3.0` is already vendored/pinned and was legitimacy-audited in Phase 2's research.

**Font asset provenance (not a package, but held to the equivalent bar):** Zilla Slab (D-15's recommendation) is a static font asset, not a registry package, so `gsd-tools query package-legitimacy check` does not apply. Its license and origin were instead verified the same way `02-UI-SPEC.md` originally vendored Inter — via web search cross-referencing multiple independent sources (Font Squirrel, 1001 Fonts, Wikipedia's Zilla Slab article) that consistently report SIL OFL 1.1 licensing under Mozilla Foundation copyright, plus Zilla Slab's presence on Google Fonts (a distribution channel that itself gates for valid open licensing before listing a family) `[VERIFIED: web search, cross-referenced against 3 independent sources this session]`. **This is licensing/provenance verification, not a downloaded-artifact integrity check** — the actual TTF files have not been downloaded or hash-verified this session (no vendoring tool was run); the planner must still perform the real download-and-vendor step (mirroring `server/assets/fonts/VENDOR.md`'s existing discipline for Inter: pinned release/commit, retrieval date, upstream path, licence text) and should treat the specific glyph files as `[ASSUMED]` correct until that vendoring step is actually done and the resulting `VENDOR.md` entry is reviewed.

**Packages removed due to SLOP verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Real Panel RGB Values (D-13)

**Sources checked this session, per D-13's own instruction ("Source from the Waveshare `EPD_13in3e` reference driver or the T133A01 panel datasheet"):**

1. **`firmware/main/epd13in3e.c`** (this project's own vendored port, read in full this session) — its own file header states it is "ported from the Waveshare EPD_13in3e reference driver." Contains only SPI register addresses and command-value byte sequences (`R_PSR=0x00`, `R_CDI=0x50`, `R_DRF=0x12`, etc.) for driving the panel's master/slave controller chips. **No RGB, hex, or colorimetric value of any kind appears anywhere in this file.** `[VERIFIED: local file read, this session]`. This is expected, not a gap in the port: e-ink panel controllers are commanded with color-plane/nibble codes (this project's own `INDEX_TO_NIBBLE` mapping), never RGB values — the actual ink hue is a fixed physical/chemical property of the panel's Microcup pigments, not something firmware specifies.
2. **Seeed's official industrial datasheet for this exact panel** (SKU 100088646, "13.3\" spectra™ 6 E-Ink / ePaper Display... 1200x1600 Pixels"; the T133A01-class panel this project uses per `hardware/BOM.md`), fetched and read in full this session (`files.seeedstudio.com/Bazaar/product_pdf/100088646.pdf`) — contains mechanical dimensions, pixel pitch, connector pinout, and a bare `Display Color: Black, White, Yellow, Red, Green and Blue` specification row. **No RGB/hex/chromaticity value anywhere in the document.** `[VERIFIED: WebFetch + direct PDF read, this session]`.

**Conclusion: genuinely unfindable from either source D-13 named.** This is a confirmed negative result, not an unexplored gap — both documents were located and read in full. Ink chromaticity data for E Ink panels is typically manufacturer-confidential (not published in consumer/hobbyist datasheets), which is consistent with what was and wasn't found here.

**What was found instead (community estimates, explicitly NOT authoritative):**

| Color | Community estimate | Source | Confidence |
|-------|--------------------|--------|------------|
| Red | `#A02020` (160, 32, 32) | Pimoroni community forum, user "mattdm," visual comparison against a calibrated sRGB monitor (not measured with instrumentation) `[ASSUMED — community forum, LOW confidence]` | LOW |
| Yellow | `#F0E050` (240, 224, 80) | Same source | LOW |
| Green | `#608050` (96, 128, 80) | Same source | LOW |
| Blue | `#5080B8` (80, 128, 184) | Same source | LOW |
| Black / White | Treated as close to nominal `(0,0,0)`/`(255,255,255)` by the same source ("reference pure colors") | Same source | LOW |

A second, independent source (`einkframe.com`'s "A Deep Dive into Spectra 6 Color Rendering (Part 1)," a hobbyist blog, `[ASSUMED — blog post, LOW confidence]`) states informally that Spectra 6's red "might only be (180, 40, 30)" against an ideal `(255,0,0)` — directionally consistent with mattdm's `#A02020` (both describe a muted, darkened red relative to a monitor's saturated red), which is weak triangulation between two independent hobbyist sources, not independent verification of exact values. Both sources agree on the general finding relevant to this phase's quantization design: **the real panel's saturated colors (especially Blue and Green) render visibly more muted/desaturated than a monitor's `#0000FF`/`#00FF00` primaries** — `server/panel_format.py`'s current `PALETTE_RGB` uses exactly those unmuted primaries (`D-P2-03`'s deliberate nominal-placeholder choice), so livery source art with saturated blues/greens will likely quantize to *legally correct but not visually matched* panel colors under the current nominal palette.

**Recommendation (this session's resolution of D-13):**

1. **Do not treat the community estimate above as ground truth for this specific panel unit.** It is a different product line entry point (a "Pimoroni Impression" branded product, not confirmed to be the identical T133A01 panel/driver pairing this project uses) and was gathered by eye, not instrumentation.
2. **Primary recommendation: a hardware-calibration fallback**, since the user's actual panel is already bring-up-verified and in hand (`hardware/BRINGUP-LOG.md`'s `## Panel Observations` section already confirmed, 2026-08-25, that "the six colours... render as clean, visually distinct solid bands... with the expected left-to-right order and no cross-band bleed," using the exact same `stub-server/make_test_panel.py --pattern palette` six-band test image this project already has). Extend that existing verification with an explicit RGB-tuning pass:
   - Render `server/plane/render.py`'s `--preview` output (or a small dedicated 6-swatch test image) with the community-estimated values substituted into `PALETTE_RGB`, view it on a normal (non-color-managed-critical) monitor.
   - Compare side-by-side against the real panel showing the existing `make_test_panel.py --pattern palette` six-band image (already flashed and photographed once during 01-06 bring-up).
   - Adjust `PALETTE_RGB`'s Yellow/Red/Blue/Green triples by eye until the preview approximates the real panel's ink hues as closely as a human judgment call allows — explicitly informal, not colorimetrically rigorous, but sufficient given `PALETTE_RGB`'s only two consumers are (a) the developer-preview PNG and (b) nearest-neighbor color assignment across a closed, tiny 6-color set, where "reasonably close" hue positioning is what actually matters for livery-color quantization quality, not exact colorimetric accuracy.
   - Record the final tuned values, the comparison method, and the date in `hardware/BRINGUP-LOG.md`'s `## Panel Observations` section (extending the existing entry, per D-13's own reference to that log) — this keeps the provenance trail in the same place the panel's other physical-hardware observations already live, rather than duplicating it into `03-RESEARCH.md` or code comments alone.
   - This is a `checkpoint:human-verify`-appropriate task (the user must look at the physical panel), reusing the exact task-type precedent already established for this phase's other on-glass verification items (D-02/D-04, illustration hand-off).
3. **Immediate low-risk interim step:** update `PALETTE_RGB`'s Yellow/Red/Blue/Green entries to the community-estimated values above as a documented starting point before the hardware-calibration pass, since they are very likely closer to the real panel than the current pure-primary placeholders (`D-P2-03`) regardless of exact-match uncertainty, and this is a render-internal-only constant change with zero risk to the wire format (per `panel_format.py`'s own existing comment that these values "never cross the wire to the device").
4. **This does not block starting illustration work.** Both the wire-format correctness (verified this session — see Summary/Pattern 1) and illustration-hand-off spec work are fully independent of `PALETTE_RGB`'s exact values; only the *subjective color-matching quality* of a livery illustration's quantized output depends on it. Sequence the calibration pass early enough that it's done before final illustration hand-off files are quantized against production code, but it need not block earlier plan tasks (illustration-selection logic, guard-rail rewrite, UI-SPEC addendum).

## Full Composition Realignment (D-14 through D-18) — Second Scope Expansion

This section is the direct research response to the follow-up prompt for this update pass: a real flightportrait.com product-photography comparison (D-14) led the user to reopen typography, information hierarchy, and background treatment — reopening parts of `02-UI-SPEC.md` Revision 2 and superseding the just-approved `03-UI-SPEC.md` amendment's "illustration zone only" framing. Everything in the illustration-zone research above (Pattern 1-4, Pitfalls 1-6, the airline candidate list, the RGB calibration plan) is unaffected by this expansion and remains valid — this section is additive, not a replacement.

### 1. Serif font selection + license (D-15)

**What was inspected:** `poster-blue.jpg` and `print-detail.jpg` (flightportrait.com product photography, fetched and saved to the session scratchpad by the discuss-phase session, still present and viewed directly this session — `[VERIFIED: direct image inspection this session]`). The "FLIGHTPORTRAIT" wordmark in `print-detail.jpg` is uppercase, evenly (almost monospaced-looking) letter-spaced, with visible slab-like serifs and **no strong thick/thin stroke-width contrast** within a glyph — it reads as a typewriter-adjacent serif, not a high-contrast "display" serif (e.g. not Didot/Bodoni/Playfair-family). The small caption lines under each aircraft in `poster-blue.jpg` (airline/aircraft-type/registration detail lines) also read as a serif, consistent with the wordmark family, at a much smaller size.

**Attempted exact-font identification:** `WebFetch` against flightportrait.com's live marketing site found no `@font-face`/CSS font-family declarations in the fetched HTML (the site's CSS wasn't independently resolvable through the fetch), and — as `02-UI-SPEC.md` Revision 2 already established via its own source-code investigation — the actual poster-rendering component is closed-source and separate from the public GitHub repo, so there is no code to inspect for a font name either. **Conclusion: the exact typeface flightportrait uses could not be identified with certainty from any source checked this session — this is a confirmed negative result (both plausible lookup paths were tried and closed), not an unexplored gap.** Any specific font recommended below is therefore a **stylistic match** based on direct visual inspection of the two product photos, tagged `[ASSUMED]`, not a confirmed identification.

**Recommendation: Zilla Slab (SIL OFL 1.1, Mozilla Foundation), weights SemiBold (600) and Bold (700) only.**

- **License:** `[VERIFIED: web search, cross-referenced against Font Squirrel, 1001 Fonts, and Wikipedia's Zilla Slab article, all independently reporting SIL OFL 1.1 under Mozilla Foundation copyright]`. Zilla Slab is Mozilla's own corporate/wordmark typeface (commissioned during Mozilla's 2016-2017 rebrand, based on Typotheque's Tesla), distributed on Google Fonts — the same OFL-vendoring discipline `02-UI-SPEC.md` already used for Inter applies unchanged: download the static weight TTFs, vendor into `server/assets/fonts/`, add a `VENDOR.md` provenance entry (source, pinned release, retrieval date, license text pointer).
- **Why a slab serif specifically, not a literal wordmark match attempt:** the explicit legibility risk this research was asked to flag is real and general, not specific to any one candidate font — a serif typeface with thin hairline strokes is a known e-ink rendering risk (thin strokes dither/vanish poorly on hard-edged, low-DPI-relative-to-stroke-width displays; this project's own `02-UI-SPEC.md` "Rendering rule" note already establishes that AA'd/thin edges dither into visible halftone noise on this exact panel). Rather than pick a font that stylistically resembles the wordmark and then hope its bold cut is thick enough, this recommendation picks a font **category** (slab serif) that structurally cannot have thin hairlines — a slab serif's defining characteristic is that the serifs themselves are as thick as the letter's main strokes, i.e. near-uniform stroke weight throughout the glyph. This is a stronger, more defensible answer to the stated risk than a closer-looking but structurally riskier high-contrast serif (see Alternatives Considered above for the explicit rejection of that category). Zilla Slab specifically (over other OFL slab serifs) is recommended because: (a) it has an explicit SemiBold cut in addition to Bold, giving the co-equal flight-number/destination pairing (D-16) a slightly less heavy option than jumping straight to Bold everywhere if that reads too dense at 88px+; (b) it is widely deployed (Mozilla's own production typeface, on Google Fonts), meaning the hinting/rendering quality at various sizes is well-exercised, not an obscure/undertested family; (c) its uppercase forms are visually close to the wordmark's blocky, sturdy character observed in `print-detail.jpg`.
- **Which cut for which role:** use **only** SemiBold (600) or Bold (700) — do not vendor or use the Regular (400) or Light (300) cuts anywhere in the render pipeline. Regular/Light cuts on any serif (slab or not) thin out the stroke width in exactly the way the legibility risk describes; restricting to SemiBold/Bold sidesteps the risk entirely rather than requiring per-render-context judgment calls about whether a given cut is "thick enough." Recommended mapping: Bold (700) for the uppercase tracked Label role (state label, route-line prefix, bottom static tag — reusing the existing `draw_tracked_text()` helper unchanged, since it is font-agnostic) and for the flight-number half of D-16's co-equal pairing; SemiBold (600) for the destination/origin half of that pairing (a full explicit hierarchy decision — flight number as the marginally heavier of the two co-equal elements — belongs in the UI-SPEC/planning step, not this research document; this is offered as one reasonable resolution, not a locked answer).
- **Verified-safe rendering mechanism:** the exact same call path already used for Inter — `ImageFont.truetype(path, size)` + `draw.text((x,y), text, font=font, fill=<palette index>)` directly on the `"P"`-mode canvas — is font-agnostic and requires zero code changes to swap fonts (`server/plane/render.py`'s `_font()`/`fit_text_size()`/`draw_tracked_text()` all take a font path as a parameter, never hardcode "Inter"). This generalization is a reasonable extrapolation of Phase 2's own real-glass "hard, flat edges" finding, not itself independently re-verified against Zilla Slab's specific hinting this session — flag as a Wave 0 / legibility-checkpoint item below, not a risk-free assumption.
- **One genuinely new, locally-verified hazard found this session, independent of font choice:** `ImageDraw.text(..., stroke_width=N, stroke_fill=...)` — Pillow's own built-in "outline text" feature, a plausible thing to reach for if a new font or busier background looks less legible than Inter-on-flat-color did — **leaks illegal palette indices via anti-aliased edge blending**, even against a flat single-color background. Verified by direct local execution this session: drawing `"AF1380"` at 88px with `stroke_width=3, stroke_fill=IDX_BLACK` onto a flat `IDX_BLUE` canvas produced indices `{0 (Black), 1 (White), 2 (Yellow), 3 (Red), 4 (Blue)}` — 277 Yellow pixels and 456 Red pixels appeared from nowhere, purely from the stroke rendering's anti-aliased blend being nearest-neighbor-quantized into the small 6-color palette (`[VERIFIED: local execution, Pillow 12.3.0, this session]`). Plain `draw.text(fill=...)` with no stroke, by contrast, produced only the two intended indices (`{1, 4}`), matching Phase 2's real-glass verified behavior exactly. **Do not use `stroke_width`/`stroke_fill` anywhere in this render pipeline for any font**, including as a legibility aid for text sitting over the new dithered background (see the quiet-zone pattern below for the safe alternative). See Pitfall 7.

### 2. Dithered background at full-canvas scale (D-17)

**Performance — locally re-verified this session, not merely assumed to generalize:** the original illustration-zone research verified Floyd-Steinberg dithering mechanics on a small ~zone-3-sized test image; this update pass re-ran the same `Image.quantize(palette=<Image built from pf.PALETTE_RGB>, dither=Image.FLOYDSTEINBERG)` call against a **full 1200×1600 synthetic photographic-toned gradient** (a blue-toned noisy gradient chosen to approximate the "softer, more photographic-toned" background D-17 describes, not a flat fill), executed directly against the real installed Pillow 12.3.0:

```
quantize (full 1200x1600, dither=FS)   took 0.0468 s
quantize (full 1200x1600, dither=NONE) took 0.0022 s   (for comparison)
pack_panel (on the dithered result)    took 0.1576 s
```
`[VERIFIED: local execution, Pillow 12.3.0, server/panel_format.py's real PALETTE_RGB and pack_panel(), this session]`

**Conclusion: full-canvas dithering costs roughly 47ms of quantize time (~150ms total render-side, including packing) — this is negligible against every budget that matters here.** The panel's own hardware full-refresh takes **~31.5 seconds** (`hardware/BRINGUP-LOG.md`'s `## Panel Observations`, measured live twice at 31.54s and 31.54s), i.e. the render-side dithering cost is roughly **0.15% of the hardware refresh time** — not a distinguishable factor in the device's total wake-poll-display-sleep cycle, and no code exists in this project (checked: `grep` on `poll_loop.py`/`render.py` found no render-time budget assertion of any kind) that this change would be at risk of violating. Nothing about applying Floyd-Steinberg dithering to a majority-of-canvas area instead of a small zone changes the underlying mechanism verified in the original illustration-zone research (Pattern 1) — Pillow's `quantize()` cost scales with pixel count, not with any special-casing of "small vs. large" regions, and no new failure mode (illegal indices, palette drift, etc.) was observed at the larger scale; `getcolors()` on the dithered full-canvas test output still returned exactly the 6 legal indices, same as the small-zone test.

**Compositing text/captions over a dithered (not flat) background — a genuinely new problem this expansion introduces:** the current render pipeline (`_build_active_canvas()`) starts from `pf.new_canvas(bg_idx)`, which fills the **entire** canvas with one flat palette index via a single-value `Image.new("P", ...)` call — there is no concept of "paint a dithered region, then draw flat text on top of part of it" anywhere in the existing code. D-17 requires this to become a genuinely different compositing order:

1. Render (or select a vendored) source RGB image approximating the desired "softer, photographic-toned" background mood (blue-toned for departing, green-toned for arriving — see D-18 below).
2. Dither that source image to the panel's 6 legal indices via the already-verified `quantize(palette=<Image from PALETTE_RGB>, dither=Image.FLOYDSTEINBERG)` call, producing the base canvas (replacing today's single-flat-index `new_canvas()` call for the active states specifically — the Empty state's flat White background is unaffected by any of this).
3. **Composite caption text on top.** This is where the stroke-outline hazard above matters: a dithered background under White text loses some of the contrast guarantee the flat-field design had (Phase 2's real-glass "clearly legible" finding was for White-on-flat-saturated-field specifically, and does not transfer automatically — see the legibility re-verification requirement below). The verified-safe technique, following the same principle subtitle/caption text uses in video ("a small solid backing box behind the text"), is a **flat "quiet-zone" rectangle**: `draw.rectangle(box, fill=bg_idx)` drawn in the *state's own dominant index* (e.g. `IDX_BLUE` for departing) directly onto the already-dithered canvas, sized to just the caption text's own bounding box (reusing the existing `_tracked_text_bbox()`/`fit_text_size()` measurement helpers, which already compute exact text bounding boxes for the safe-box assertion), **before** drawing the text itself on top of that flat patch. This keeps every text-bearing pixel using only the two legal indices the Color contract already requires (`{bg_idx, IDX_WHITE}`) — the same spatial-scoping principle D-11's illustration-zone guard rail already established, just inverted (a flat *island* inside a dithered sea, rather than a dithered island inside a flat sea). **This is a locally-groundable extrapolation of an already-verified pattern (Pattern 1's palette/index mechanics, reused unchanged), not a newly-verified end-to-end render** — flag as a Wave 0 implementation/legibility-checkpoint item, not a closed question.
4. An alternative worth naming and explicitly rejecting: relying on the dithered background naturally being "light enough" or "dark enough" in the text's specific region for White text to read without any quiet zone. This is fragile — Floyd-Steinberg dithering intentionally distributes error across neighboring pixels to approximate a source tone, meaning the exact local density of White-vs-colored dither pixels directly under a caption line is not something the render code controls or can guarantee stays consistent as the background "mood" art changes; a flat quiet-zone rectangle is a deterministic guarantee, a "hope the dither pattern cooperates" approach is not. Recommend against it.

### 3. D-18: how does the departing/arriving distinction survive a non-flat background?

Three concrete options were evaluated, informed by what's actually implementable given the verified mechanism above and the real panel/legibility findings already on record (`02-05-SUMMARY.md`'s "clearly legible"/"hard, flat edges" findings were for a flat field; this phase's own panel-RGB findings above establish that Blue/Green render *more muted* on real glass than their nominal placeholder values, per the community estimates in "Real Panel RGB Values"):

| Option | Mechanism | Assessment |
|---|---|---|
| **(a) Two dithered background "moods"** — a blue-toned photographic-feeling background for departing, a green-toned one for arriving, still using the state color as the *dominant* dithered hue but not as one flat legal index | Two source background art assets (or two parameterizations of one generative approach), each dithered the same verified way | **Recommended.** Directly reuses the one mechanism verified this session at full scale with negligible cost; keeps the state signal exactly where flightportrait's own reference photography puts its color signal (the whole field's overall tone, not a badge/accent); requires no new zone/geometry, no new compositing primitive beyond what D-17 already needs regardless of D-18's outcome |
| **(b) Keep a thin flat-color accent element** (a border, a small state-color patch) as an explicit state signal, background goes fully photographic/neutral | A new flat-fill geometric element (e.g. a border stroke or corner patch) drawn in `bg_idx` | Technically simple (a flat rectangle/stroke is the *simplest* possible draw call, reuses `draw.rectangle()` directly), but reintroduces exactly the "same-color badge invisible against its own background" failure mode `02-UI-SPEC.md` Revision 2 already diagnosed and explicitly removed once (`02-UI-SPEC.md`'s "Mode badge removed" note) — a background-color-matching accent patch on a background that's mostly-that-color-anyway has weak self-contrast; a background-color-*mismatching* accent (e.g. a Yellow border) reintroduces an unreserved color into a zone the Color contract otherwise wants clean. Not recommended as the *primary* signal, though it remains available as a secondary reinforcement layered on top of option (a) if on-glass testing shows (a) alone is ambiguous |
| **(c) Rely on non-color cues only** (silhouette mirroring + state label text), treat background as pure mood/texture with no state-dependent color at all | No background color-state logic — one single "photographic" background treatment used for both states | Removes the color signal that D-05 through D-13's entire preceding research thread was built around retaining and reinforcing (D-10's mirroring is explicitly documented as *reinforcing*, not *replacing*, the color signal); also a bigger behavioral change than the CONTEXT.md decisions actually ask for — D-17 says the background changes *treatment* (flat → dithered), not that it stops carrying state information at all. Rejected as the primary approach, though the underlying cues it relies on (mirroring, state label text) remain valid *secondary* reinforcement regardless of which primary option is chosen |

**Recommendation: Option (a), with the non-color cues from option (c) retained as secondary reinforcement (as they already are today) — not option (b)'s accent-patch approach.** This is the option that best satisfies the constraint the CONTEXT.md decision itself states (D-17: "the background is no longer a single flat legal index... the way the state tables currently assume" — implying the state color survives as a *dominant tone*, not that it disappears), reuses the one verified-cheap mechanism this session already confirmed works at full scale, and avoids reopening the exact badge/accent failure mode `02-UI-SPEC.md` Revision 2 already resolved once. **This is a research recommendation for the planner/UI-SPEC-revision step to adopt or override, not itself a locked decision** — D-18 was explicitly left to research/planning by the user, and the final call on exact mood-art parameters (what "blue-toned" vs. "green-toned" concretely means as source art — a gradient? a texture? an abstracted sky/tarmac scene?) is a design question for the UI-SPEC revision, not something this research document should over-specify.

### 4. Legibility re-verification requirement (D-17's own explicit instruction)

**This must be treated as a fresh, separate `checkpoint:human-verify` requirement — not silently covered by the existing "clearly legible" finding.** `02-05-SUMMARY.md`'s Step 4 legibility confirmation ("Clearly legible" — White text against the saturated field; "Hard, flat edges" — no grey halo or dither speckle observed) was explicitly for **White Inter text on a flat, single-index, saturated Blue/Green field with dithering disabled everywhere**. Every one of those specific conditions changes under D-14 through D-18: the font changes (Inter → Zilla Slab, D-15), the background is no longer flat or single-index (D-17), and dithering — previously explicitly absent from every zone except the (then-nonexistent) illustration — now covers most of the panel. **None of these changes are covered by the existing finding, and the user's own CONTEXT.md text says so explicitly** ("The user explicitly accepted that this reopens the on-glass legibility question already verified once in `02-05-SUMMARY.md`... a fresh on-glass legibility check against the new busier/softer background is required before this phase can close"). This is not a new research finding so much as a explicit restatement, for the planner's Wave 0/Validation Architecture, that this checkpoint **must exist as a distinct plan task** using the same established `checkpoint:human-verify` pattern as D-02/D-04/D-13's calibration pass (Pattern 3) — it must not be assumed satisfied by carrying forward the Phase 2 finding, and it must not be silently folded into (and therefore possibly skipped alongside) the illustration-zone-specific `checkpoint:human-verify` items from the first two research passes, since it covers a structurally different set of render elements (background + typography, not the illustration). See Validation Architecture below for the specific Wave 0 gap entry and Phase Requirements → Test Map row this produces.

## Architecture Patterns

### System Architecture Diagram

```
poll_loop.py:run_once()
        │
        ├─ detect.poll_current_aircraft() ──► flight dict (hex, callsign, vertical_rate_fpm, ...)
        │
        ├─ runway_config.infer_from_flight() ──► confirmed_state ("departing"/"arriving"/None)
        │
        ├─ enrich.lookup_route(flight["callsign"], cache) ──► route dict {airline_name, origin_city, destination_city, ...} or None
        │        (existing, unchanged this phase — PLANE-01/02's enrichment call)
        │
        └─ render.render_panel(flight, render_state, route=route)
                 │
                 └─ render.build_canvas() ──► render._build_active_canvas()
                          │
                          ├─ pf.new_canvas(bg_idx)              # full-bleed Blue/Green, UNCHANGED
                          ├─ draw_state_label()                 # flat White text+glyph, UNCHANGED
                          ├─ [NEW] select_illustration(route)    # airline_name → asset path, THIS PHASE
                          ├─ [NEW] draw_dithered_illustration()  # replaces draw_silhouette(); full 6-color
                          │        Floyd-Steinberg composite, no remap needed (D-11, THIS PHASE)
                          ├─ draw flight-number/route/airline captions  # flat White text, UNCHANGED
                          ├─ draw bottom static tag              # flat White text, UNCHANGED
                          └─ guard-rail assertion                # WIDENED + SPATIALLY SCOPED (D-11) —
                                   │                                see Pattern 1 / Common Pitfalls below
                                   └─ pf.pack_panel(canvas) ──► 960,000-byte wire buffer, UNCHANGED
```

### Recommended Project Structure

No new top-level directories. Extend existing locations:

```
server/
├── assets/
│   └── icons/
│       ├── aircraft-silhouette.png     # RETAINED for provenance/fallback-shape reference; no longer the primary render path
│       ├── illustrations/              # NEW — one subdirectory keeps the per-airline set visually separable from the flat glyph/badge assets
│       │   ├── air-france.png
│       │   ├── iberia.png
│       │   ├── ...
│       │   └── generic-fallback.png    # D-08's single dithered generic illustration
│       └── VENDOR.md                   # gains a new "illustrations/" provenance section (AI-generated, not third-party-sourced — see Pattern 3 below)
└── plane/
    └── render.py                       # gains select_illustration()/draw_dithered_illustration(); draw_silhouette() likely retired or kept only as the fallback-shape source
```

### Pattern 1: Full 6-color constrained-palette dithering (the core new mechanism — REVISED under D-11)

**What:** Quantize a source illustration (RGB or grayscale) down to the panel's full 6 legal palette indices using Floyd-Steinberg dithering, by building the quantize target palette **directly from `panel_format.PALETTE_RGB`** — this is the key simplification verified this session. Because `PALETTE_RGB`'s 6 entries are already ordered `[Black, White, Yellow, Red, Blue, Green]`, exactly matching `IDX_BLACK..IDX_GREEN` (0..5), the quantized image's own local palette indices already ARE the canvas's real indices. **No `.point()` remap step is needed** — this is materially simpler than the 2-color pattern this research originally proposed (which required a remap because its throwaway 2-entry palette's local 0/1 numbering had no relationship to the canvas's real constants).

**When to use:** For every per-airline illustration and the D-08 generic fallback, inside `_build_active_canvas()`, replacing (or alongside, if a flat fallback shape is retained for some case) the current `draw_silhouette()` call.

**Example (verified this session against the real `server/panel_format.py` module and a synthetic multi-hue test image — `[VERIFIED: local execution, Pillow 12.3.0]`):**
```python
# Source: verified locally against server/panel_format.py's actual PALETTE_RGB
# this session. Confirmed output: getcolors() returned indices {0,1,2,3,4,5}
# only (all 6 legal indices used on a deliberately hue-rich synthetic test
# image), zero illegal indices, with NO remap step applied.
from PIL import Image
from server import panel_format as pf

def dither_to_full_panel_palette(source_rgb):
    """source_rgb: a Pillow "RGB" source image (the vendored illustration,
    or its transparent-PNG's RGB channels — see Pattern 2 for alpha
    handling). Returns a "P"-mode image whose palette indices are ALREADY
    the canvas's real IDX_BLACK..IDX_GREEN indices (0..5) - safe to
    canvas.paste() directly, no .point() remap required, because the
    quantize target palette below is built from panel_format.PALETTE_RGB
    itself, in the exact same index order the canvas uses.
    """
    # A genuinely 6-entry palette image built straight from the module's
    # real constant - not a throwaway hand-picked palette, and NOT
    # zero-padded to 256 entries (see Common Pitfalls Pitfall 2 - the
    # zero-padding footgun this pattern sidesteps entirely by construction).
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(list(pf.PALETTE_RGB))

    quantized = source_rgb.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)
    # quantized's local indices are already 0=Black,1=White,2=Yellow,
    # 3=Red,4=Blue,5=Green - identical to pf.IDX_BLACK..IDX_GREEN. No
    # remap needed; this is the one genuinely simpler step versus the
    # 2-color pattern originally proposed for this phase.
    return quantized
```

### Pattern 2: Alpha-masked paste for non-rectangular illustration edges

**What:** If the handed-off illustration has a transparent background (recommended — see Don't Hand-Roll), preserve its alpha channel separately from the dithering step and use it as the `mask=` argument to `canvas.paste(quantized_image, box, mask=alpha_mask)` — note the paste target is now the **quantized multi-color image itself**, not a scalar `fill_index` as the old flat-fill `paste_mask()` used; `Image.paste()` supports pasting a full image through a mask, not just a flat color. Do NOT hard-threshold this mask to strictly binary (that's specific to the retired flat-fill pipeline) — a soft alpha edge composited against a dithered region is fine since the dithered content itself is already constrained to the 6 legal indices.

**When to use:** Whenever the source illustration isn't already a clean rectangle (almost certainly true for AI-generated art).

### Pattern 3: The established synthetic-render forcing technique (D-02/D-04)

**What:** Stop the poll timer on the VPS (`systemctl stop inkframe-poll.timer`), invoke `server.plane.render.render_panel(flight_dict, state, route=route_dict)` directly as the service user to produce packed panel bytes, write them to the state directory's `panel.bin` (the same path `poll_loop.write_panel_atomic()` targets), power-cycle or otherwise force the device to wake past its backoff window, verify on glass, then restart the timer (`systemctl start inkframe-poll.timer`).

**Verified precedent:** this is exactly the technique 02-05 Task 3 used to force the `Route unavailable` fallback with `EJU84YF` — `[VERIFIED: 02-05-SUMMARY.md line 118, "the real production render code (`server.plane.render.render_panel(...)`) was invoked directly as the `inkframe` service user"]`.

**Applied to this phase's D-02/D-04:**
- D-02 (synthetic departure): `render_panel({"callsign": "<any>", "hex": "<any>"}, "departing", route=<a real or plausible route dict>)` — note `render_panel()` takes `state` directly as a string, never touching `runway_config.py`'s threshold arithmetic at all. This confirms CONTEXT's own read (D-02) that this technique validates only the *visual* DEPARTING rendering path (Blue field, nose-right illustration), never the real `+200 ft/min` threshold value — that remains unresolved until a real departure is observed via `journalctl -u inkframe-poll`.
- D-04 (long-caption stress test): `render_panel(flight, state, route={"airline_name": "<a genuinely long name>", "origin_city": "<a genuinely long city>", ...})` to force `fit_text_size()`'s shrink path, exactly as 02-04's own manual QA already did once with a synthetic 50+ character name (`02-04-SUMMARY.md` line 96-97) — but that was eyeballed as a PNG preview, never on real glass, which is precisely the gap D-04 closes.

### Pattern 4: `02-UI-SPEC.md` Color-contract addendum (D-11 — draft text for the plan to apply)

**What:** `02-UI-SPEC.md`'s locked Color section (Revision 2, "Reservation language" subsection) currently states Blue/Green is background-only and White is foreground-only in the active states, with no exception. D-11 requires an *explicit*, narrowly-scoped exception, not a silent reinterpretation. Following that document's own established style (per-state color tables + a "Reservation language" subsection), the plan should add this new subsection immediately after the existing "Reservation language" paragraph in `02-UI-SPEC.md`'s Color section:

```markdown
### Illustration-Zone Exception (Phase 3, D-11 — 2026-08-26)

Phase 3 grants the aircraft-illustration zone (zone 3, the region bounded by
`SILHOUETTE_ZONE_TOP`..`+SILHOUETTE_ZONE_HEIGHT` and the illustration's own
rendered bounding box within it) an explicit, narrowly-scoped exception to
the "White is foreground content only" rule above. Within that bounding box
only, a per-airline dithered livery illustration may use the panel's full
6-color legal palette (Black, White, Yellow, Red, Blue, Green) via
Floyd-Steinberg dithering — not just White. Every other foreground element
in the Departing/Arriving states (state label glyph + text, flight-number
caption, route line, airline line, bottom static tag) remains White-only,
and the full-bleed background field remains Blue/Green-only, exactly as
locked above. **This is a spatial exception, not a palette-wide reopening:**
outside the illustration's bounding box, the Departing/Arriving Color
contract tables above apply completely unchanged, and `server/test_render.py`
enforces this spatial boundary directly (see `03-RESEARCH.md`'s Validation
Architecture).

**Cross-phase reservation update (Phase 3, D-12):** Yellow's presence in a
per-airline illustration is explicitly permitted — the illustration zone and
Phase 4's low-battery indicator (a different zone/element entirely) are
visually distinct enough that reuse is not confusing. Red's original
reservation rationale ("Phase 3's disruption banner, RER-03") is stale:
RER-03 was deferred to v2 in the 2026-08-11 scope cut and has no scheduled
consumer in this roadmap, so Red is likewise available for illustration use
without reservation conflict. This paragraph supersedes the "Cross-phase
reservation note" above for the illustration zone specifically; that note is
unchanged for every other zone (Yellow/Red remain unused elsewhere on the
panel).

**Panel-color-accuracy caveat:** the illustration's quantization target
(`server/panel_format.py`'s `PALETTE_RGB`) is a nominal, hardware-calibrated
approximation, not a colorimetrically-measured value — see `03-RESEARCH.md`'s
"Real Panel RGB Values" section for the calibration method and its
limitations. Livery colors are guaranteed *legal* (one of the 6 real panel
inks) but not guaranteed to visually match the source art's intended brand
colors with precision.
```

**When to use:** As an explicit plan task (editing `02-UI-SPEC.md` directly), sequenced before or alongside the guard-rail/test changes — the addendum should exist as a locked, reviewable artifact, not be inferred implicitly from code changes.

### Pattern 5: Full-canvas dithered background with flat "quiet-zone" text compositing (NEW — D-17, this update pass)

**What:** Replace `pf.new_canvas(bg_idx)`'s single-flat-index fill (used today for the Departing/Arriving states) with a three-step composite: (1) dither a full-canvas source background image to the 6 legal indices via the already-verified `quantize(palette=<Image from PALETTE_RGB>, dither=Image.FLOYDSTEINBERG)` call — verified this session to cost ~47ms at full 1200×1600 scale, no different in kind from the illustration-zone case; (2) draw each caption/label element's flat quiet-zone rectangle (`draw.rectangle(box, fill=bg_idx)`) directly onto the dithered canvas, sized from the same bounding-box math `fit_text_size()`/`_tracked_text_bbox()` already compute; (3) draw the text itself (`draw.text(..., fill=IDX_WHITE)`, no `stroke_width`) on top of each quiet zone. The Empty state's flat White background is unaffected — this pattern only applies to the Departing/Arriving states' full-bleed field.

**When to use:** For every text-bearing element (state label, flight-number caption, route/airline lines, bottom static tag) once the background field changes from `new_canvas()`'s flat fill to a dithered background image (D-17).

**Example (the quiet-zone technique — not yet executed end-to-end against real background art this session, but each step is individually verified: dithering mechanics in Pattern 1/this section's performance test, quiet-zone flat-index drawing is a plain `draw.rectangle(fill=<int>)` call already used elsewhere in this codebase for the retired mode badge, per `02-UI-SPEC.md` Revision 1):**
```python
# Source: new code, composing verified building blocks - not itself
# re-executed against a real photographic background image this session.
def _draw_quiet_zone_text(draw, canvas, bbox, text, font, bg_idx, tracking=0):
    """Draw `text` legibly over a dithered (non-flat) region of `canvas`
    by first flattening its own bounding box to bg_idx, then drawing the
    text on top - never via stroke_width (see Pitfall 7, verified this
    session to leak illegal palette indices)."""
    left, top, right, bottom = bbox
    draw.rectangle((left, top, right, bottom), fill=bg_idx)
    draw_tracked_text(draw, (left, top), text, font, IDX_WHITE, tracking=tracking)
```

**When NOT to use:** Any zone whose Color contract requires it to stay dithered/multi-color (the aircraft illustration zone, D-11) — quiet zones are for flat-White-on-dithered-background *text/caption* legibility specifically, not a general "flatten anything hard to read" tool.

### Anti-Patterns to Avoid
- **Zero-padding a quantize target palette to 256 entries with an arbitrary filler color:** under the full-6-color pattern this footgun is naturally sidestepped by construction (Pattern 1 uses `PALETTE_RGB`'s exact 6 entries with no padding at all), but if a planner instead hand-builds a padded palette for any reason, the same risk applies as originally documented: any source pixel matching the filler RGB gets quantized to an illegal/wrong index. Always build the palette image directly from `pf.PALETTE_RGB` with no padding.
- **Reflexively carrying over the (now-superseded) 2-color pattern's mandatory index-remap step:** the full-color pattern verified this session needs **no** `.point()` remap, because `PALETTE_RGB`'s order already matches the canvas's real indices. Adding an unnecessary remap step (or worse, adding a remap keyed to a *different*, hand-picked palette order than `PALETTE_RGB`'s) risks silently scrambling colors — e.g. accidentally swapping Yellow and Red. If a remap step exists in the illustration compositing code, that's a signal something is being built with a non-`PALETTE_RGB`-ordered palette and should be double-checked.
- **Treating the "exactly 2 distinct palette indices" guard rail as either fully removable or a simple raised ceiling:** the correct replacement is a spatially-scoped guard (illustration bbox: up to 6 legal indices; everything else: exactly `{bg_idx, IDX_WHITE}`), not "assert `len(colors) <= 6`" — a bug that leaks Yellow/Red/Black into the flight-number caption or bottom tag would pass a naive raised-ceiling check but violate the locked Color contract everywhere outside the illustration.
- **Automated background removal as a code solution:** no segmentation library exists in this project and adding one (e.g. `rembg`/`onnxruntime`) is disproportionate weight for a problem the hand-off spec can eliminate entirely by requiring transparent-PNG input.
- **Using `ImageDraw.text(..., stroke_width=..., stroke_fill=...)` as a legibility aid over the new dithered background (NEW — D-17, this update pass):** verified this session by direct local execution to leak illegal palette indices (Yellow, Red) via anti-aliased stroke-edge blending, even against a flat single-color background — the opposite of the hard-edged guarantee this render pipeline depends on everywhere outside the illustration zone. Use Pattern 5's flat quiet-zone rectangle instead.
- **Selecting a high-contrast "display" serif for D-15 in pursuit of a closer visual match to flightportrait's wordmark:** thin hairline strokes are a structural property of that font category, not something a bold cut reliably eliminates — pick a slab serif category instead (see "Full Composition Realignment" above), which cannot have thin hairlines by construction.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Reducing a photographic/AI-generated image to the panel's 6 legal colors with dithering | A hand-rolled Floyd-Steinberg error-diffusion loop | `Image.quantize(palette=<Image built from pf.PALETTE_RGB>, dither=Image.FLOYDSTEINBERG)` | Already verified this session to produce exactly the 6-color legal index set needed, with no remap step required; Pillow's C implementation is the whole point of the "Don't Hand-Roll" table Phase 2's own research already established for this project |
| Isolating an illustration's aircraft shape from its background | Flood-fill/dilate/erode cleanup (the technique already used for the flat CC0 silhouette SVG) or a segmentation model | Specify transparent-PNG as the D-09 hand-off contract | The flood-fill pipeline was necessary in Phase 2 because the source was line-art with interior detail to flatten; a photographic AI illustration doesn't need that specific cleanup, and most AI image tools can export directly with alpha transparency, making the problem a spec requirement rather than an engineering one |
| Measuring real panel ink color accurately | A DIY colorimeter reading against the e-ink surface | A documented visual side-by-side calibration against the real panel (see "Real Panel RGB Values") | E-ink displays are reported (community sources, this session) to be incompatible with typical consumer colorimeter probes; visual comparison is the achievable, zero-new-equipment fallback, and the accuracy bar this constant actually needs (nearest-neighbor hue matching across 6 fixed colors) doesn't require instrumentation-grade precision |
| Confirming a real runway-3 departure without live traffic | Simulating one via fabricated ADS-B state injected into `detect.py` | The established `render_panel()` direct-invocation technique (Pattern 3) already used in 02-05 Task 3 | This is the project's own precedent, not a generic library recommendation — reuse it rather than re-deriving a new forcing mechanism |

**Key insight:** every "don't hand-roll" item this phase is really the same principle Phase 2's research already named — Pillow already does everything the render pipeline needs; the only genuinely new problem (dithering into a 6-color hardware palette) is Pillow's stock `quantize()` call, verified this session to just work — and to need *less* extra glue code (no remap) than originally anticipated — when the target palette is built directly from the project's own real palette constant.

## Common Pitfalls

### Pitfall 1: Widening the "exactly 2 palette indices" guard rail without spatially scoping it
**What goes wrong:** A planner reads D-11's instruction to widen the guard rail and simply raises the ceiling (e.g. `assert len(colors) <= 6`), without also asserting that colors *outside* the illustration's bounding box are still exactly `{bg_idx, IDX_WHITE}`. This would silently pass a bug where, say, the flight-number caption accidentally renders in Yellow, or the background field bleeds a stray Black pixel from a botched paste — exactly the class of regression the original 2-color guard rail existed to catch.
**Why it happens:** "Widen the guard rail" is easy to read as "increase the allowed count," which is necessary but not sufficient — the real Color contract requirement (per the new `02-UI-SPEC.md` addendum, Pattern 4) is spatial, not just numeric: only the illustration zone gets the 6-color exception.
**How to avoid:** Implement the guard rail as two checks: (1) the full canvas contains between 2 and 6 distinct indices, all drawn from the 6 legal panel indices (defensive numeric bound); (2) a copy of the canvas with the illustration's own returned bounding box blanked out to `bg_idx` contains **exactly** `{bg_idx, IDX_WHITE}` — this reuses the same crop/mask technique `test_render.py`'s existing silhouette-band checks already use (`_silhouette_band()`), just inverted (blank the zone rather than isolate it) and asserted on rather than measured.
**Warning signs:** A guard-rail assertion that only checks a total color count, with no code path referencing the illustration's own bbox coordinates at all.

### Pitfall 2: Zero-padded quantize target palette silently introducing an out-of-range index
**What goes wrong:** `Image.new("P", (1,1)).putpalette(six_colors + [0,0,0]*250)` (padding the remaining 250 slots with black, the naive pattern) is not the recommended construction under the verified Pattern 1 (which builds the palette from exactly `pf.PALETTE_RGB`'s 6 entries with zero padding) — but if a planner or executor deviates from Pattern 1 and pads anyway, the same underlying risk from the original 2-color research applies: an all-zero filler is itself a valid palette entry that can "win" nearest-neighbor matching for near-black source pixels, potentially routing them to a padded slot rather than the real `IDX_BLACK`.
**Why it happens:** Padding a palette image to 256 entries is a common defensive habit from unrelated Pillow work, but it's actively counterproductive here — `PALETTE_RGB` already has exactly the 6 colors that should ever be selectable, and any padding beyond that reintroduces a footgun this project doesn't need.
**How to avoid:** Follow Pattern 1 exactly: `pal_img.putpalette(list(pf.PALETTE_RGB))` with no concatenation, no padding. Verified this session to produce a valid `quantize()` call with only the 6 legal indices appearing in output.
**Warning signs:** Any code in the illustration pipeline that concatenates `PALETTE_RGB` with additional filler values before calling `putpalette()`.

### Pitfall 3: Assuming the 2-color pattern's index-remap step is still required
**What goes wrong:** An implementer familiar with (or copy-pasting from) the originally-proposed 2-color `dither_to_state_palette()` pattern reflexively adds a `.point()` remap call after `quantize()`, even though the full-color Pattern 1 verified this session needs none — because it builds the quantize palette directly from `PALETTE_RGB` in the canvas's own index order. Adding a spurious/incorrect remap (especially one written against a differently-ordered ad-hoc palette) risks silently scrambling which real color each dithered pixel ends up as.
**Why it happens:** The 2-color and full-color patterns look superficially similar (both call `quantize(palette=..., dither=Image.FLOYDSTEINBERG)`) but differ in whether the target palette's index order matches the canvas's real index order — a detail easy to lose when adapting one pattern from the other.
**How to avoid:** Build the quantize target palette **only** via `Image.new("P", (1,1)).putpalette(list(pf.PALETTE_RGB))` — never a hand-picked or reordered palette — and skip the remap step entirely, per Pattern 1.
**Warning signs:** A `.point()` call anywhere in the new illustration-compositing code path, or a quantize target palette not built directly from `pf.PALETTE_RGB`.

### Pitfall 4: Ambiguous nose orientation across a multi-file illustration set
**What goes wrong:** Unlike the single vendored silhouette (whose `SILHOUETTE_SOURCE_NOSE = "left"` is a single documented constant), a per-airline set generated by the user across multiple external sessions/tools risks inconsistent source orientation — one file's nose left, another's nose right — silently breaking D-10's mirror-by-state contract for whichever files are inconsistent.
**Why it happens:** The user is generating these files externally with no code-side validation of orientation until a human looks at the render.
**How to avoid:** Make source-nose orientation an explicit, single documented requirement in the D-09 hand-off spec (e.g. "every file must be nose-left, matching the retired silhouette's convention") — not a per-file metadata field, since there's no code-side way to detect it automatically. Verify visually as part of the illustration hand-off checkpoint, per file, before wiring any of them into the render path.
**Warning signs:** A departing-state render where the mirrored illustration's nose points the wrong way for one specific airline but not others.

### Pitfall 5: Enrichment misses silently reduce the achievable "per-airline" coverage below what the illustration count suggests
**What goes wrong:** The planner sizes the illustration hand-off around "every airline seen in Phase 1 samples" (38 distinct callsigns, spanning ~10 apparent airlines), but illustration selection is keyed off `route.get("airline_name")` from the *same* `adsbdb` lookup that already only resolves 52.6% of real traffic (`server/plane/enrich.py` docstring, `[VERIFIED: 02-RESEARCH.md line 59]`). Two of the callsign prefixes seen in Phase 1 samples (`EJU`, `KMM`) are *documented adsbdb misses* (`02-RESEARCH.md` line 96: "hexdb.io recovered 2 of 4 sampled adsbdb misses (EJU84YF, KMM466)") — meaning `airline_name` is never available for those flights regardless of how good an illustration exists for them, so they always fall through to the D-08 generic fallback no matter what.
**Why it happens:** It's easy to conflate "airlines seen in ADS-B traffic" with "airlines the illustration-selection logic can actually resolve" — they are not the same set, because selection depends transitively on `adsbdb`'s crowdsourced coverage, not on ADS-B detection alone.
**How to avoid:** Size the illustration hand-off around airlines confirmed (or strongly likely, given `02-RESEARCH.md`'s carrier-class finding) to resolve via `adsbdb`, not around every callsign prefix seen in raw samples. See the concrete candidate list under Open Questions / State of the Art below.
**Warning signs:** The user generates a `KMM` (KM Malta Airlines) or `EJU` (easyJet Europe) illustration expecting it to render, and it never does because the enrichment step upstream of illustration selection was already a miss for that callsign.

### Pitfall 6: The existing silhouette-band "shape actually painted" / "mirroring applied" checks are calibrated for a flat single-color fill, not a full-color dithered one
**What goes wrong:** `test_render.py`'s checks 16-19 (lines 264-331) measure "silhouette actually painted" via `band.histogram()[IDX_WHITE] >= 0.1 * TARGET_W * MAX_H` and detect mirroring via a White-vs-not mask XOR comparison — both hardcode `IDX_WHITE` specifically, which was correct when the silhouette was a flat White fill. Under a full-color dithered illustration, White is just one of up to 6 colors Floyd-Steinberg distributes across the shape based on source tones — a dark-toned livery illustration could legitimately contain very little White, causing this check to under-count or flip a false negative even though the illustration rendered correctly.
**Why it happens:** These checks were written against Phase 2's single-color rendering model and were not touched by this phase's D-11 decision directly (the prompt for this research update named the guard-rail and Yellow/Red reservation checks specifically), but they share the same underlying assumption (single-color foreground) that D-11 just broke.
**How to avoid:** Replace `IDX_WHITE`-specific counting with **non-background-index** counting — i.e. `sum(count for idx, count in band.getcolors() if idx != bg_idx)` instead of `band.histogram()[IDX_WHITE]` — for both "shape painted" and "mirroring differs" checks. This is robust regardless of which of the 6 legal colors a given dithered illustration actually uses, and requires no new geometry constants (the existing `SILHOUETTE_ZONE_TOP`/`SILHOUETTE_ZONE_HEIGHT`/`SILHOUETTE_TARGET_W`/`SILHOUETTE_MAX_H` constants are unaffected by the color-gamut decision — only the color-counting logic inside the checks needs updating).
**Warning signs:** A real per-airline illustration that visually renders correctly on a preview PNG but fails checks 16-19 in CI, or (worse) passes them vacuously because a near-all-White illustration happens to still clear the 10% threshold while a legitimately darker livery would not.

### Pitfall 7: `stroke_width`/`stroke_fill` silently leaking illegal palette indices (NEW — D-17, this update pass)
**What goes wrong:** An implementer reaches for Pillow's built-in `ImageDraw.text(..., stroke_width=N, stroke_fill=...)` as a quick way to add an outline to caption text for extra legibility once the background is no longer a flat, uniformly-contrasting field — a reasonable-looking fix given the new busier background. This introduces genuinely illegal colors (Yellow, Red observed) into what should be a clean two-index `{bg_idx, IDX_WHITE}` region, breaking the exact spatial-scoping guarantee D-11's guard rail (Pitfall 1) and D-11/D-12's Yellow/Red reservation checks (item 2 in the Validation Architecture line-plan below) both depend on — and it does this **even on a flat background**, so it isn't even specific to the dithered-background case; any use of `stroke_width` anywhere in this codebase is unsafe.
**Why it happens:** `stroke_width` is a documented, seemingly-safe Pillow feature; nothing about its name or docstring suggests it produces anti-aliased blending on a palette-mode (`"P"`) image, and the plain (no-stroke) `draw.text()` call this codebase already uses does NOT have this problem (verified clean, `{1, 4}` only) — the failure is specific to the stroke-rendering code path, not text rendering in general, making it an easy trap for anyone who tests plain text first (finds it clean) and then adds a stroke later without re-checking `getcolors()`.
**How to avoid:** Never use `stroke_width`/`stroke_fill` anywhere in `server/plane/render.py`. If a caption needs stronger contrast against its background, use Pattern 5's flat quiet-zone rectangle (drawn via `draw.rectangle(fill=bg_idx)` before the text) instead — verified this session to keep the canvas within the exact two legal indices the Color contract requires.
**Warning signs:** Any `stroke_width=` or `stroke_fill=` argument appearing in a `draw.text()` call anywhere in the render pipeline; a `getcolors()` guard-rail check failing with an unexpected Yellow/Red count outside the illustration zone after a text-rendering change.

### Pitfall 8: Assuming Phase 2's "clearly legible" on-glass finding still applies after D-14 through D-18 (NEW — this update pass)
**What goes wrong:** A planner or executor treats `02-05-SUMMARY.md`'s Step 4 legibility confirmation ("Clearly legible... Hard, flat edges") as still-valid evidence that this phase's on-glass legibility is fine, and skips or downgrades the fresh `checkpoint:human-verify` this expansion requires — because "we already verified legibility on real glass in Phase 2" is technically true, just for a materially different render (Inter, flat single-index background, zero dithering anywhere on the panel) than what D-14 through D-18 now produce (Zilla Slab, dithered majority-of-canvas background, quiet-zone-composited text).
**Why it happens:** The two findings look superficially interchangeable ("we already checked legibility") without noticing that every one of the specific conditions the original finding was scoped to has since changed.
**How to avoid:** Treat this as an explicit, separate Wave 0 gap / plan task (see Validation Architecture below) — do not close it by referencing the Phase 2 finding. The user's own CONTEXT.md text (D-17) already states this requirement explicitly; this pitfall exists to make sure it survives into the plan rather than getting silently assumed away during planning or execution.
**Warning signs:** A plan or SUMMARY that cites `02-05-SUMMARY.md`'s legibility finding as satisfying this phase's legibility requirement, with no new on-glass check against the actual dithered-background/Zilla-Slab render.

## Code Examples

### Real airline candidate list, derived from Phase 1 sample data + Phase 2's live enrichment findings

Extracted this session directly from `adsb-test/samples/*.jsonl` (38 distinct real callsigns across all captured runway-3 traffic) and cross-referenced against `02-RESEARCH.md`'s live `adsbdb` coverage findings — `[VERIFIED: local grep/parse of adsb-test/samples/*.jsonl this session; carrier-hit-rate claims CITED from 02-RESEARCH.md]`. Unaffected by the color-gamut decision — reproduced unchanged from the original research pass:

| Callsign prefix(es) observed | Airline | `adsbdb` coverage (per 02-RESEARCH.md) |
|---|---|---|
| `AFR` | Air France | Hit 100% in Phase 2's live test |
| `IBE` | Iberia | Hit 100% |
| `TAP` | TAP (Air Portugal) | Hit 100% |
| `DAH` | Air Algérie | Hit 100% — this is also the one real flight rendered on glass so far (`DAH1112`/`DAH1008`) |
| `CCM` | CCM Airlines (Air Corsica) | Hit 100% |
| `VLG` | Vueling | Hit 100% |
| `TVF` (13 of 38 observed callsigns — the dominant prefix) | Transavia France | Hit only 2 of 20 in the live test — mostly falls to the generic fallback regardless of illustration availability |
| `VOE` | Volotea | Not explicitly reported hit/miss in 02-RESEARCH.md — unconfirmed, treat as [ASSUMED] |
| `EJU` | easyJet Europe | **Confirmed adsbdb miss** (`EJU84YF`/`EJU67HR`/`EJU96KT` — same callsign already used project-wide as the canonical forced-fallback fixture) — an illustration for this airline would never be selectable under the current enrichment design |
| `KMM` | KM Malta Airlines (ICAO `KMM`, confirmed via web search this session `[VERIFIED: web search, KM Malta Airlines / airhex.com]`) | **Confirmed adsbdb miss** (`KMM466`) — same as above, never selectable |

**Recommendation:** size the hand-off at the **6 confirmed-hit carriers** (Air France, Iberia, TAP, Air Algérie, CCM Airlines/Air Corsica, Vueling) plus **1 generic fallback** (D-08) as the concrete, achievable v1 set — 7 files total. Transavia France is a reasonable 8th if the user wants to cover the numerically dominant prefix despite its low resolve rate; `EJU`/`KMM`-specific illustrations would never render under the current single-provider enrichment design and should not be requested from the user. **Under the full-color livery decision, this list is unchanged, but the hand-off prompt to the user should now explicitly request each airline's real brand livery colors, not tonal/grayscale-appropriate art** (the earlier 2-color research had recommended the opposite framing).

### Airline-name normalization for filename matching

`enrich.py`'s `lookup_route()` returns `airline_name` verbatim from `adsbdb`'s response (e.g. `"Transavia France"`, confirmed via a live lookup this phase in `02-04-SUMMARY.md`). No normalization currently exists in the codebase for this field — a new small helper is needed (unaffected by the color-gamut decision):

```python
# Source: new code, following enrich.py's own normalise_callsign() convention
import re
import unicodedata

def normalise_airline_key(airline_name):
    """'Air Algérie' -> 'air-algerie', 'CCM Airlines' -> 'ccm-airlines'.
    Mirrors enrich.normalise_callsign()'s discipline: deterministic,
    never raises, returns None for anything falsy.
    """
    if not airline_name:
        return None
    ascii_name = unicodedata.normalize("NFKD", airline_name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or None
```

This must be a pure function of `airline_name` only (no live API call), matching `enrich.normalise_callsign()`'s existing discipline of keeping normalization deterministic and side-effect-free.

### Local verification transcript (full 6-color dithering, this session)

```
$ server/.venv/bin/python3 -c "
from PIL import Image
from server import panel_format as pf
pal_img = Image.new('P', (1,1))
pal_img.putpalette(list(pf.PALETTE_RGB))
# ... quantize a synthetic hue-sweep 300x150 RGB test image with dither=Image.FLOYDSTEINBERG ...
"
Palette RGB (index order 0=Black,1=White,2=Yellow,3=Red,4=Blue,5=Green):
0 [0, 0, 0]
1 [255, 255, 255]
2 [255, 255, 0]
3 [255, 0, 0]
4 [0, 0, 255]
5 [0, 255, 0]

Distinct indices used by 6-color FS-dithered quantize: [0, 1, 2, 3, 4, 5]
Counts: [(11735, 0), (3172, 1), (1347, 2), (4942, 3), (13019, 4), (10785, 5)]
Legal index set 0..5: {0, 1, 2, 3, 4, 5}
All indices legal? True
```

`[VERIFIED: local execution, Pillow 12.3.0, server/panel_format.py's real PALETTE_RGB, this session]` — confirms Pattern 1's core claim: a genuinely 6-entry, unpadded palette built from `PALETTE_RGB` produces only legal indices under Floyd-Steinberg dithering, and `pal_img.getpalette()` was separately confirmed to return exactly 18 values (6 RGB triples, no implicit padding to 256) — Pillow does not silently pad a `putpalette()` call itself, which is why the zero-padding pitfall (Pitfall 2) is something a developer has to actively introduce, not something Pillow does by default.

## State of the Art

| Old Approach (Phase 2) | New Approach (Phase 3) | When Changed | Impact |
|--------------------------|------------------------|---------------|--------|
| Single flat-White CC0 silhouette, `dither=Image.NONE`, hard-thresholded binary mask | Per-airline full-6-color dithered illustration (`dither=Image.FLOYDSTEINBERG`), alpha-masked composite, no index remap needed | This phase (D-05 through D-13), unlocked by the SenseCraft real-hardware photo test, color-gamut resolved by D-11 | The aircraft element goes from "one shape, one flat color, generic across all flights" to "airline-specific, full-color livery, selected per detection" — the single biggest visual-fidelity change since Phase 2's Revision 2 full-bleed color-field pivot |
| `02-UI-SPEC.md`'s "Reserve Floyd-Steinberg dithering... for any future photographic content only" | This phase is that "future," now specifically full-color, not the narrower 2-color reading this research originally defaulted to | 2026-08-05 (UI-SPEC Revision 2) → 2026-08-26 (this phase, D-11 resolution) | The rendering-rule note was written prospectively in Phase 2 and is now being exercised for the first time, at the more ambitious end of what it anticipated |
| `_build_active_canvas()`'s whole-canvas "exactly 2 distinct indices" guard rail | A spatially-scoped guard: illustration bbox may use all 6 legal indices, everywhere else stays exactly `{bg_idx, White}` | This phase, D-11 | The Color contract's *intent* (background/caption purity) is preserved exactly; only its *enforcement mechanism* becomes spatial rather than whole-canvas |

**Deprecated/outdated:** `draw_silhouette()`'s flat-fill hard-threshold path is not deleted (it remains the fallback-shape *source* if D-08's generic illustration is chosen to be a dithered re-render of the retired shape, per CONTEXT's Claude's Discretion), but it is no longer the primary render path for the departing/arriving states. The originally-proposed 2-color `dither_to_state_palette()` pattern (with its mandatory index remap) is likewise superseded — retained nowhere in code, documented here only as a rejected alternative (see Common Pitfalls Pitfall 3).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Volotea (`VOE` prefix) `adsbdb` hit/miss status is unconfirmed — treated as unknown coverage | Code Examples / candidate list | If actually a consistent miss (like `EJU`/`KMM`), a Volotea illustration would be wasted hand-off effort; if actually a hit, it's a reasonable 8th/9th candidate the recommendation under-counts |
| A2 | ~~The "2-color dithering keeps the guard rail unchanged" finding generalizes...~~ **RESOLVED — superseded.** D-11 chose full-color livery, not 2-color; this assumption no longer applies to the chosen path. Retained struck through for audit trail only. | Summary / Pattern 1 (original) | N/A — no longer live |
| A3 | The exact `airline_name` string format for TAP, Air Algérie, CCM, and Vueling (needed for the filename-normalization mapping) is inferred from 02-RESEARCH.md's carrier names, not independently re-verified via a fresh live `adsbdb` call this session (only `Transavia France` was directly cited from a documented live lookup) | Code Examples | If the live string differs subtly (e.g. "TAP Air Portugal" vs "TAP Portugal", "Vueling" vs "Vueling Airlines"), the normalization mapping's filename keys would need adjusting — low risk, easily caught by a single live lookup during planning/execution |
| A4 | ~~No panel RGB reference values are needed for correct 2-color dithering...~~ **RESOLVED — inverted.** Under the chosen full-color path, panel RGB values ARE load-bearing for visual (not legal) color-mapping quality. Actively researched this session (see "Real Panel RGB Values"): confirmed unfindable from authoritative sources; a community estimate exists but is `[ASSUMED]`/LOW confidence, and a hardware-calibration fallback is recommended as the actual resolution path. | Real Panel RGB Values | If the calibration pass is skipped and only the unverified community estimate is used, livery colors may map to visually mismatched (though still legal) panel inks — cosmetic risk only, not a functional/wire-format risk |
| A5 | Community-sourced RGB estimates (`#A02020` Red, `#F0E050` Yellow, `#608050` Green, `#5080B8` Blue) are directionally useful (muted vs. monitor primaries) but not confirmed to be from the identical T133A01 panel/driver pairing this project uses — gathered by eye on a differently-branded product (Pimoroni "Impression"), not measured with instrumentation | Real Panel RGB Values | If the underlying panel/ink formulation differs meaningfully between product lines, these estimates could be worse than a neutral guess for this specific hardware — mitigated by treating them as a documented starting point only, superseded by the hardware-calibration pass against the user's actual panel |
| A6 | Zilla Slab is stylistically similar to flightportrait's actual wordmark typeface, based on direct visual inspection of `print-detail.jpg`/`poster-blue.jpg` only — the exact font flightportrait uses could not be identified (no CSS/font-face data found via WebFetch; the poster renderer is closed-source, per `02-UI-SPEC.md`'s own prior investigation) | Full Composition Realignment §1 (Serif font selection) | If the user's real goal was a literal visual match to flightportrait's specific wordmark rather than "a legible serif in the same general character," Zilla Slab may read as a plausible-but-noticeably-different serif once vendored and viewed side by side — low functional risk (license/legibility properties hold regardless), but a real risk to "does this look like flightportrait" satisfaction; recommend the user sanity-check a rendered sample against the reference photos before final sign-off |
| A7 | `Image.quantize(..., dither=Image.FLOYDSTEINBERG)`'s ~47ms full-canvas timing, measured against one synthetic gradient-plus-noise test image this session, generalizes to whatever real "photographic-toned" background art is ultimately used/generated for D-17 | Full Composition Realignment §2 (Dithered background at full-canvas scale) | Low risk — Pillow's quantize cost is a function of pixel count and palette size, not image content complexity in any way that would plausibly push a 1200×1600 image from ~47ms to a timing that matters against a 31.5s hardware refresh budget; flagged for completeness, not because a materially different result is expected |
| A8 | The flat quiet-zone compositing technique (Pattern 5) has not been executed end-to-end against real photographic background art and real caption text on the actual panel this session — each individual building block (dithering mechanics, flat-index `draw.rectangle()`, plain `draw.text()` without stroke) is independently verified, but the full composited result's on-glass legibility is not | Full Composition Realignment §2 / Pattern 5 | If the quiet-zone rectangle's size/positioning is miscalculated (e.g. doesn't fully cover a tracked-text bounding box), a sliver of dithered background could show through behind text, degrading legibility in a way only real-hardware inspection would catch — this is exactly what the required fresh `checkpoint:human-verify` (Pitfall 8) is for |

**If this table is empty:** N/A — see above.

## Open Questions

### Resolved this session

1. ~~**Does D-06/D-07's "richer illustration" mean 2-color dithered tonal art, or literal multi-color airline livery?**~~ **RESOLVED via D-11: full multi-color livery, using Yellow/Red/Black/Blue/Green as needed to match real airline brand colors, not just White + state-background tonal shading.** This is a genuine reopening of `02-UI-SPEC.md`'s locked Color contract, scoped narrowly to the illustration zone (Pattern 4's addendum draft). The originally-recommended 2-color default is not used.

2. ~~**If full 6-color livery dithering is chosen instead, do real Spectra 6 panel RGB values become load-bearing?**~~ **RESOLVED: yes (per D-13), and actively researched this session.** Real panel RGB values are confirmed genuinely unfindable from either source `02-UI-SPEC.md`/D-13 named (the Waveshare `EPD_13in3e` reference driver contains no colorimetric data by design — it's a register-command sequence, not an RGB API; Seeed's own industrial datasheet for this panel likewise publishes no RGB/chromaticity data). See "Real Panel RGB Values" above for the community-estimate finding (LOW confidence) and the recommended hardware-calibration fallback, which is now the primary open *action item* for planning (not an open *research question* — the research is complete; a `checkpoint:human-verify` calibration task is what remains).

### Still open

3. **Exact file-handoff aspect ratio / resolution / format contract for the user**
   - What we know: The existing silhouette's placement constraints are `SILHOUETTE_TARGET_W = 900`, `SILHOUETTE_MAX_H = 260` (`server/plane/render.py` lines 148-149), with the vendored asset's ~2.22:1 aspect ratio meaning the height cap binds first (per `server/assets/icons/VENDOR.md`). Unaffected by the color-gamut decision — this geometry is unchanged by D-11.
   - What's unclear: Whether to ask the user for images pre-cropped to ~2.2:1, or to accept any aspect ratio and let the render code fit-within both caps (same logic `draw_silhouette()` already implements) — the latter is more forgiving of what an AI image tool actually produces.
   - Recommendation: Ask for a *loose* aspect-ratio target (roughly landscape, wider than tall) rather than an exact ratio, and reuse `draw_silhouette()`'s existing fit-within-both-caps sizing logic unchanged — it already handles "whichever cap binds first" correctly and needs no modification for this phase. Specify: PNG format, transparent background (alpha channel), nose-left source orientation (matching the retired silhouette's documented convention so D-10's mirror-by-state logic needs no per-file metadata), a minimum width of roughly 1200px for downscale headroom (comparable to the existing silhouette's 1800px vendored raster width), and — new under D-11 — **request the airline's actual brand/livery colors in the source art**, since the render pipeline will now preserve color information through dithering rather than discarding it.

4. **Whether the "wall-mounted ambient art" success criterion (ROADMAP criterion 4) can be meaningfully closed this phase at all**
   - What we know: D-03 explicitly flags the frame is currently on a desk, not wall-mounted, and instructs recording this as a provisional caveat rather than a blocker. Unaffected by the color-gamut decision.
   - What's unclear: Whether the plan should include a distinct, separately-tracked follow-up verification step for "once wall-mounted," or just note the caveat in the phase's SUMMARY and move on.
   - Recommendation: Follow D-03 literally — record the caveat, don't block phase closure on it, and don't invent a new tracked follow-up task unless the user asks for one during planning.

5. **Who supplies the "softer, more photographic-toned" background source art for D-17's dithering input? (NEW — this update pass, genuinely unresolved by CONTEXT.md)**
   - What we know: D-09 already establishes a precedent for externally-AI-generated art (the per-airline illustrations) with an explicit hand-off spec, because this environment has no image-generation tool (`ToolSearch`-verified absent). D-17's own text says the background should be "softer, more photographic-toned" — this is a description of a *visual quality*, not a specification of *where the source pixels come from*.
   - What's unclear: CONTEXT.md's D-14 through D-18 never states whether the background-mood art is (a) another AI-generated asset the user supplies externally (same D-09 hand-off pattern, extended), or (b) something proceduralized/generated in code (e.g. a Pillow-drawn gradient, a simple radial/linear blend synthesized without any external asset), or (c) a small set of vendored stock/CC0 photographic textures (sky, tarmac, etc.) similar in spirit to the retired CC0 silhouette's sourcing.
   - Recommendation: **Prefer option (b), a code-generated gradient/blend, for the primary path** — it has zero external dependency (no new human hand-off gate to add alongside D-09's existing illustration gate, keeping the phase's already-real external-dependency count at one, not two), it composes trivially with D-18's two-mood recommendation (parameterize the same gradient generator by a blue-toned vs. green-toned color pair), and its dithering-input performance is already verified negligible regardless of exact pixel content (§2 above). Option (a) remains available as a strictly-better-looking upgrade if the user wants to extend the same AI-generation hand-off workflow to the background too, but should not be treated as required — this is a genuinely open scoping question for the planner/UI-SPEC-revision step to resolve with the user, not something this research should force a single answer to.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Pillow | Dithering/quantization/compositing | Yes | 12.3.0 (verified this session) | — |
| Image-generation tool (ChatGPT/Midjourney/etc.) | D-09's illustration source files | External to this environment — user-side only, verified absent via `ToolSearch` per CONTEXT.md D-09 | — | None — this is the phase's core external dependency; the plan must gate on a human hand-off, not attempt to substitute automated generation |
| Real runway-3 departure (live ADS-B traffic) | Fully resolving A-02-02-01's real threshold value (distinct from D-02's synthetic visual validation) | Not yet observed, per STATE.md Blockers/Concerns | — | D-02's synthetic-render forcing technique validates the visual path only; the real threshold question stays open regardless of this phase's outcome |
| Colorimeter / instrumented color-measurement device | D-13's ideal (but infeasible) resolution path | Not available, and reported (community sources) to be generally incompatible with e-ink displays regardless | — | The recommended hardware-calibration fallback (visual side-by-side comparison against the real, already-in-hand panel) — see "Real Panel RGB Values" |
| Physical Spectra 6 panel (bring-up-verified) | D-13's calibration fallback | Yes — arrived and bring-up-verified 2026-08-25 per `hardware/BRINGUP-LOG.md` | — | — |
| Zilla Slab font files | D-15's typography change | Not yet vendored — download-and-vendor is a planner/executor task, not performed this research session (license/provenance only verified, per Package Legitimacy Audit above) | 1.501 (current Google Fonts release, per web search) | — |
| Image-generation tool, if D-17's background art is sourced externally (Open Questions #5, option (a)) | Background-mood source art, only if that option is chosen over the code-generated-gradient default | Same as the illustration-tooling row above — external to this environment, user-side only | — | Recommended default: a code-generated gradient (Open Questions #5, option (b)) needs no external tool at all |

**Missing dependencies with no fallback:**
- Image-generation tooling — this phase cannot generate illustrations autonomously; the plan must include an explicit blocking human hand-off task. (This applies to the per-airline illustrations regardless; it applies to the background art too **only if** Open Questions #5's option (a) is chosen instead of the recommended code-generated default.)

**Missing dependencies with fallback:**
- Real departure traffic — D-02's forcing technique is the accepted fallback for the *visual* rendering validation this phase actually needs to close; the *threshold-value* validation remains a carried-forward open item regardless.
- A colorimeter for D-13 — the hardware-calibration (visual comparison) fallback is accepted and recommended as primary, not a degraded substitute, given the user's own real panel is already available and bring-up-verified.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Stdlib-only custom `check()` harness (no pytest/unittest) — matches every existing `server/test_*.py` file's convention |
| Config file | none — each test file is directly executable |
| Quick run command | `server/.venv/bin/python3 server/test_render.py` |
| Full suite command | `server/.venv/bin/python3 server/test_render.py && server/.venv/bin/python3 server/test_enrich.py && server/.venv/bin/python3 server/test_runway_config.py && server/.venv/bin/python3 server/test_plane_detection.py && server/.venv/bin/python3 server/test_pipeline_e2e.py && server/.venv/bin/python3 stub-server/test_poll_cycle.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PLANE-01/02 | Illustration selection resolves the correct asset for a known airline_name and falls back correctly for an unresolved one | unit | `server/.venv/bin/python3 server/test_render.py` (extend with new checks) | Extend existing file — Wave 0 gap: new `select_illustration()`/`normalise_airline_key()` checks |
| PLANE-01/02 | The dithered illustration composite stays within the illustration's own bounding box; everywhere else on the canvas is still exactly `{bg_idx, White}` (D-11's spatially-scoped guard rail) | unit | `server/.venv/bin/python3 server/test_render.py` (**rewrite** existing checks 12-13, lines 217-242 — currently assert whole-canvas `len(colors) == 2`, no longer true under full-color illustrations) | Exists, needs rewrite — see Wave 0 Gaps below |
| PLANE-01/02 | Yellow/Red may appear inside the illustration zone but never outside it (D-11/D-12's scoped reservation) | unit | `server/.venv/bin/python3 server/test_render.py` (**rewrite** existing checks 10-11, lines 194-215 — currently a whole-buffer nibble-count check with no spatial scoping at all) | Exists, needs rewrite — see Wave 0 Gaps below |
| ROADMAP criterion 5 | Mirroring still applies correctly to the new illustration path (departing=nose-right, arriving=nose-left), robust to a full-color (not just White) dithered shape | unit | `server/.venv/bin/python3 server/test_render.py` (**adjust** existing checks 16-19, lines 264-331 — currently hardcode `IDX_WHITE` for "shape painted"/"mirroring differs" detection; see Common Pitfalls Pitfall 6) | Exists, needs targeted adjustment (not a full rewrite — the underlying `SILHOUETTE_ZONE_*` geometry constants and safe-box logic are unaffected) |
| ROADMAP criteria 1/2/3/4/5 (real-glass legibility, threshold, composition) | On-glass legibility, D-02 synthetic departure, D-04 long-caption stress test, D-13's RGB calibration pass | manual (`checkpoint:human-verify`, unavoidable — real hardware output can't be automated) | N/A — human judgment against real Spectra 6 output, following the established 02-05 Task 3 pattern | N/A |
| ROADMAP criteria 1/4 (NEW — D-17's own explicit instruction, this update pass) | Fresh on-glass legibility check of Zilla Slab text over the new dithered background, specifically distinct from the Phase 2 flat-field finding — see Pitfall 8 | manual (`checkpoint:human-verify`) — cannot be automated, must be a **separate** checkpoint task from the illustration-zone checkpoints, not folded into them (structurally different render elements) | N/A — human judgment against real Spectra 6 output, both Departing (blue-mood) and Arriving (green-mood) states | N/A |

**Exact `server/test_render.py` line-level change plan (this session's answer to "what exactly needs to change"):**

1. **Checks 12-13 (lines 220-242, "pre-pack canvas contains exactly two distinct palette indices"):** Replace the bare `colors = canvas.getcolors(); assert len(colors) == 2` logic with a two-part check: (a) `set(idx for idx, _ in colors)` is a subset of `{IDX_BLACK, IDX_WHITE, IDX_YELLOW, IDX_RED, IDX_BLUE, IDX_GREEN}` and `2 <= len(colors) <= 6`; (b) blank the illustration's own returned bbox to `bg_idx` on a copy of the canvas (`draw.rectangle(illustration_bbox, fill=bg_idx)`) and assert that copy's `getcolors()` indices are exactly `{bg_idx, IDX_WHITE}`. Requires the new `draw_dithered_illustration()` (replacing `draw_silhouette()`) to return its bbox, exactly as `draw_silhouette()` already does today — no new return-value contract needed, just reuse it.
2. **Checks 10-11 (lines 195-215, "no Yellow/Red nibble cross-phase reservation"):** These currently operate on the **packed byte buffer** (`nibble_counts(buf)`), which has no spatial concept at all — a byte-level check cannot distinguish "Yellow in the illustration" from "Yellow in the caption text." Rewrite to operate on the **pre-pack canvas** instead (`render.build_canvas(...)`, matching the existing silhouette-band tests' own pattern), using the same "blank the illustration bbox, then check colors" technique as item 1 above: assert the blanked-canvas copy contains no `IDX_YELLOW`/`IDX_RED`. This correctly asserts "no illegal color outside the illustration zone" rather than "no illegal color anywhere," which is what D-11/D-12 actually require.
3. **Checks 16-19 (lines 264-331, silhouette "shape painted"/"mirroring differs"):** Per Common Pitfalls Pitfall 6, replace `band.histogram()[IDX_WHITE]` and the White-only `_fg_only_bytes()` mask with non-background-index counting: `sum(c for idx, c in band.getcolors() if idx != bg_idx)`. The geometry constants and safe-box overlap checks in this block are unaffected and should not change.
4. **`EXPECTED_CHECK_COUNT = 25` (line 37):** Will need updating once the planner finalizes exactly how many checks the above rewrites + new illustration-selection checks produce — flagged here as a mechanical follow-up, not a design decision this research needs to make.

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 server/test_render.py`
- **Per wave merge:** full suite command above
- **Phase gate:** full suite green, plus the `checkpoint:human-verify` on-glass pass (including D-13's RGB calibration pass), before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `server/test_render.py` — needs new checks for `select_illustration()`/`normalise_airline_key()` (unresolved airline → fallback, known airline → correct file, case/diacritic normalization)
- [ ] `server/test_render.py` — checks 12-13 need rewriting to the spatially-scoped guard-rail logic described above (D-11)
- [ ] `server/test_render.py` — checks 10-11 need rewriting from a whole-buffer nibble check to a spatially-scoped canvas check (D-11/D-12)
- [ ] `server/test_render.py` — checks 16-19 need their `IDX_WHITE`-specific color counting generalized to non-background-index counting (Pitfall 6)
- [ ] `02-UI-SPEC.md` — needs the Illustration-Zone Exception addendum applied (Pattern 4's draft text)
- [ ] `hardware/BRINGUP-LOG.md` — needs a new entry recording D-13's RGB-calibration pass (method, tuned values, date) once performed
- [ ] `server/panel_format.py` — `PALETTE_RGB`'s Yellow/Red/Blue/Green entries should be updated per D-13's recommendation (interim community-estimate values, later refined by the calibration pass)
- [ ] No new test *file* needed — this phase extends `server/test_render.py`, the same file Phase 2's silhouette/route/airline work already extended incrementally
- [ ] `server/assets/fonts/` — Zilla Slab SemiBold + Bold TTFs need to be downloaded and vendored (D-15), with a `VENDOR.md` provenance entry matching Inter's existing discipline (source, pinned release, retrieval date, OFL 1.1 license text pointer) — not performed this research session, license/provenance verification only
- [ ] `server/plane/render.py` — `_build_active_canvas()`'s background construction needs to change from `pf.new_canvas(bg_idx)`'s single flat fill to the dithered-background + quiet-zone-text compositing order (Pattern 5) for the Departing/Arriving states specifically (Empty state unaffected)
- [ ] `server/test_render.py` — no `stroke_width`/`stroke_fill` usage should exist anywhere in the render pipeline (Pitfall 7) — worth an explicit negative-assertion test (e.g. grep-based or a rendered-output color-set check) if the planner wants a regression guard beyond code review
- [ ] `checkpoint:human-verify` — a **new, separate** on-glass legibility pass for Zilla Slab text over the dithered background (both Departing/blue-mood and Arriving/green-mood), distinct from the illustration-zone checkpoints already tracked (Pitfall 8) — must not be silently satisfied by citing `02-05-SUMMARY.md`'s Phase 2 finding
- [ ] `03-UI-SPEC.md` — needs a substantial revision (not from-scratch) covering D-15's typography, D-16's flight-number/destination hierarchy, and D-17's background treatment; the just-approved "illustration zone only" framing is superseded (per CONTEXT.md's own "Practical consequence" note)
- [ ] Open Questions #5 (background source-art provenance) needs an explicit answer during planning/UI-SPEC-revision before background-compositing code is written against real art

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No new auth surface this phase |
| V3 Session Management | No | No new session surface this phase |
| V4 Access Control | No | No new access-control surface this phase |
| V5 Input Validation | Yes | User-supplied illustration image files are untrusted input to a Pillow-based processing pipeline — validate file type/dimensions/mode before processing (Pillow itself raises on malformed image data rather than silently corrupting memory, but a corrupt/oversized file should be handled gracefully, not crash the render pipeline mid-poll-cycle) |
| V6 Cryptography | No | No new cryptographic surface this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A malformed or maliciously-crafted illustration PNG causing Pillow to raise mid-render, crashing a poll cycle | Denial of Service | Vendor illustration files at build/asset time (like the existing silhouette PNG), not at runtime from an untrusted per-request source — this phase's illustrations are static, developer-vendored assets processed once during development, not accepted from any live network input. `poll_loop.py`'s existing "a failed cycle must leave the previously served panel intact" contract (unchanged this phase) already covers the residual risk of a vendored asset regressing. |
| An extremely large source illustration file exhausting memory during dithering | Denial of Service | Same mitigation — these are vendored, developer-reviewed static assets, not runtime-uploaded content; no new attack surface is introduced relative to the existing vendored-asset model Phase 2 already established for the silhouette/glyph PNGs |
| A malformed/oversized background-mood source image (if D-17's art is externally AI-generated per Open Questions #5 option (a)), or a malformed vendored font file (D-15) causing Pillow/`ImageFont.truetype()` to raise mid-render | Denial of Service | Same vendored-static-asset mitigation as above — fonts and (if externally sourced) background art are development-time-only assets processed once and committed, not accepted from any live network input at render/poll time; if Open Questions #5's recommended code-generated-gradient default is used instead, this row is moot entirely (no external file to malform) |

## Sources

### Primary (HIGH confidence)
- `server/plane/render.py` (read in full this session) — `_build_active_canvas()`, `draw_silhouette()`, `paste_mask()`, `load_binary_mask()`, `STATE_BACKGROUND`/`STATE_INK`, `SILHOUETTE_TARGET_W`/`SILHOUETTE_MAX_H`/`SILHOUETTE_SOURCE_NOSE`
- `server/panel_format.py` (read in full this session) — `PALETTE_RGB`, `IDX_*` constants, `new_canvas()`, `pack_panel()`
- `server/plane/enrich.py` (read in full this session) — `lookup_route()`, `airline_name` field, `normalise_callsign()`
- `server/plane/runway_config.py` (read in full this session) — `CLIMB_THRESHOLD_FPM`, `infer_runway_config()`
- `server/poll_loop.py` (read in full this session) — `run_once()`'s enrichment/render call sequence
- `server/test_render.py` (read in full this session, this update pass) — all 25 checks, including the exact lines flagged for rewrite (10-11, 12-13, 16-19)
- `firmware/main/epd13in3e.c` (read in full this session, this update pass) — confirmed the Waveshare EPD_13in3e port contains only SPI register/command values, no RGB/colorimetric data
- `firmware/VENDOR.md` (read this update pass) — confirms `epd13in3e.c`/`.h` are byte-verbatim vendored from the pinned flightportrait commit
- Seeed industrial datasheet for SKU 100088646 (this exact 13.3" Spectra 6 panel), fetched and read in full this update pass (`files.seeedstudio.com/Bazaar/product_pdf/100088646.pdf`) — confirmed no RGB/chromaticity data published
- `hardware/BRINGUP-LOG.md` (read in full this update pass) — `## Panel Observations`, the existing real-hardware six-color-band verification (2026-08-25) this session's calibration-fallback recommendation extends
- Direct local execution against Pillow 12.3.0 and `server/panel_format.py`'s real 6-color `PALETTE_RGB` this update pass — verified full 6-color `Image.quantize(palette=..., dither=Image.FLOYDSTEINBERG)` behavior, confirmed no remap step is needed, and confirmed `putpalette()` does not implicitly pad to 256 entries
- Direct local execution against Pillow 12.3.0 this session (third pass) — full 1200×1600-canvas `Image.quantize(..., dither=Image.FLOYDSTEINBERG)` timing (~47ms), `pack_panel()` timing on the dithered result (~158ms), and the `stroke_width`/`stroke_fill` illegal-index-leak finding (277 Yellow + 456 Red pixels from a stroke-outlined text draw on an otherwise-flat canvas) — all `[VERIFIED: local execution, Pillow 12.3.0, this session]`
- `hardware/BRINGUP-LOG.md`'s `## Panel Observations` full-refresh-duration measurement (31.54s and 31.54s across two independent live captures, this update pass's direct grep/read) — the hardware-side budget the ~47ms render-side dithering cost is compared against
- `flightportrait-print-detail.jpg` and `flightportrait-poster-blue.jpg` (session scratchpad, originally fetched during the `/gsd-discuss-phase` session per `03-CONTEXT.md` D-14, directly viewed/inspected this research session) — the sole visual evidence for the serif-typeface stylistic-match recommendation
- `WebFetch` against `https://flightportrait.com` this session — attempted to locate CSS font-family/`@font-face` declarations; found none in the fetched HTML, a confirmed negative result informing the `[ASSUMED]` tag on the exact-font-match claim
- WebSearch for Zilla Slab license/provenance (Font Squirrel, 1001 Fonts, Wikipedia) — cross-referenced this session, all three independently confirming SIL OFL 1.1 / Mozilla Foundation copyright
- WebSearch for Courier Prime license/provenance (npm `@fontsource`, Google Fonts, Font Squirrel) — confirmed as the rejected-for-hero-pairing alternative (Alternatives Considered)
- `adsb-test/samples/*.jsonl` (parsed in full this session, 38 distinct real callsigns extracted)
- `.planning/phases/02-plane-view-end-to-end-slice/02-05-PLAN.md` and `02-05-SUMMARY.md` (read in full this session) — the `checkpoint:human-verify` task-type precedent and the exact synthetic-render forcing technique already used in production
- `.planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md` (Color section, read in full this update pass) — the exact locked contract text D-11's addendum (Pattern 4) must extend, not silently reinterpret

### Secondary (MEDIUM confidence)
- `.planning/phases/02-plane-view-end-to-end-slice/02-RESEARCH.md` (read relevant sections this session) — carrier-level `adsbdb` hit-rate findings (Air France/Iberia/TAP/Air Algérie/CCM/Vueling all hit; Transavia France 2/20; hexdb.io recovering EJU84YF/KMM466 as adsbdb misses)
- `.planning/phases/02-plane-view-end-to-end-slice/02-04-SUMMARY.md` (read in full this session) — live-verified `TVF16VB` → "Transavia France" airline_name string
- WebSearch for KM Malta Airlines ICAO code confirmation (airhex.com, planefinder.net) — cross-referenced against the codebase's own `KMM466` sample data
- WebSearch for Pillow `Image.quantize()` official documentation (pillow.readthedocs.io) — confirms the `palette=`/`dither=` parameter contract matches this session's local test behavior, including under a 6-entry (not just 2-entry) target palette

### Tertiary (LOW confidence)
- Volotea (`VOE` prefix) `adsbdb` coverage — not explicitly reported hit or miss anywhere in existing project research; flagged `[ASSUMED]` in the Assumptions Log
- TAP/Air Algérie/CCM/Vueling's exact `airline_name` string format — inferred from carrier names in `02-RESEARCH.md`, not independently re-verified via a fresh live lookup this session
- Pimoroni community forum RGB estimates for Spectra 6 colors (user "mattdm," visual comparison, not instrumented) `[ASSUMED — LOW confidence]` — this update pass's best available lead on real panel color, explicitly not treated as authoritative; see "Real Panel RGB Values"
- `einkframe.com` hobbyist blog post on Spectra 6 color gamut/rendering `[ASSUMED — LOW confidence]` — used only for weak directional triangulation ("red is muted vs. monitor red"), not as a value source
- The claim that Zilla Slab visually resembles flightportrait's actual wordmark font `[ASSUMED — LOW confidence]` — based on direct visual inspection of two product photos only, not a confirmed font-identification; see Assumptions Log A6

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, existing Pillow version verified installed and its full 6-color quantize/dither behavior (including the no-remap simplification) verified by direct local execution against the actual codebase this session; the Zilla Slab font addition is MEDIUM (license/provenance verified via web search, but the actual TTF files have not been downloaded/vendored this session)
- Architecture: HIGH on the compositing/dithering mechanics for both the guard-rail redesign and the full-color pattern (locally verified this update pass), AND on full-canvas-scale dithering performance (locally re-verified this third pass, negligible cost); MEDIUM on Pattern 5's quiet-zone text-compositing technique — each building block is independently verified but the full composite has not been executed end-to-end against real background art or real hardware this session; the color-gamut decision itself (formerly Open Question #1) is now RESOLVED (D-11), not an open unknown
- Pitfalls: HIGH — pitfalls 1-3, 6, and 7 were derived from/verified against this session's actual re-execution of the relevant code paths (including the newly-discovered `stroke_width` illegal-index leak, directly reproduced this session); pitfalls 4-5 and 8 are process/scoping pitfalls grounded in direct reading of CONTEXT.md/SUMMARY documents, not runtime-verified claims
- Real panel RGB values: LOW — actively researched this session (not merely assumed), confirmed unfindable from either authoritative source D-13 named; a hardware-calibration fallback is recommended as the load-bearing resolution path, not a found value
- Serif typeface selection (D-15): MEDIUM overall — HIGH confidence on the license (SIL OFL 1.1, cross-referenced against 3 independent sources) and on the general "slab serif avoids thin-hairline e-ink risk" reasoning (a structural/definitional property of the font category, not a per-font judgment call); LOW confidence on the specific claim that Zilla Slab visually matches flightportrait's actual wordmark font (the real font could not be identified — confirmed negative result, not an unexplored gap)
- Dithered-background-at-scale performance (D-17 §2): HIGH — directly re-measured this session against the real installed Pillow and the real `PALETTE_RGB`/`pack_panel()`, at full 1200×1600 canvas scale, compared against the real measured hardware refresh time from `hardware/BRINGUP-LOG.md`
- D-18's state-signal recommendation: LOW-MEDIUM — a reasoned recommendation grounded in verified technical constraints (the badge/accent failure mode `02-UI-SPEC.md` already diagnosed once; the verified-cheap dithering mechanism) and the CONTEXT.md decision's own stated constraint, but not itself independently on-glass tested this session — genuinely a planning-stage design recommendation, not a closed technical finding

**Research date:** 2026-08-26 (original pass); updated 2026-08-26 same day (D-11/D-12/D-13 follow-up); updated again 2026-08-26 same day (D-14 through D-18 "Full Composition Realignment" follow-up)
**Valid until:** 30 days (stable domain — Pillow's API and the project's own locked codebase don't change quickly). The panel-RGB finding specifically should be treated as stale the moment D-13's hardware-calibration pass is actually performed — this document's recommended values are a starting point, not the final calibrated result. The D-17/D-18/Pattern-5 findings specifically should be treated as provisional until the fresh on-glass legibility checkpoint (Pitfall 8) is actually performed against real background art and real Zilla Slab text.
