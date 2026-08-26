# Phase 3: Visual Polish on Real Glass - Context

**Gathered:** 2026-08-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Refine the plane view's visual design against real Spectra 6 E-ink output, closing the hardware-verified-legibility items every Phase 2 plan carried forward, AND upgrade the aircraft illustration from a flat generic silhouette to a richer, per-airline generated illustration — now that dithered/photographic rendering is confirmed viable on this exact panel (see D-05 below).

**Scope expanded a second time, 2026-08-26 (post-UI-SPEC-approval):** after the illustration-zone UI-SPEC was drafted and approved, the user directly compared the shipped Phase 2 Revision 2 design against real flightportrait.com product photography (fetched and inspected this session — see D-14/D-15/D-16 below) and asked for full composition/typography realignment, not just the illustration zone. This reopens `02-UI-SPEC.md` Revision 2's background color contract and typography, previously declared locked for this phase. A personal photo as a *user-supplied* background remains out of scope (deferred to v2, `REQUIREMENTS.md` VIS-01) — the background change this phase is a *stock* softer/photographic-toned dithered treatment, not a user-uploadable photo.

This phase does not cover the RER view, physical button, battery indicator, or any new requirement scope beyond PLANE-01/PLANE-02's existing "airline" element.

</domain>

<decisions>
## Implementation Decisions

### A-02-02-01 departure threshold validation
- **D-01:** No real runway-3 departure exists in Phase 1's captured sample data — verified directly this session: 0 readings with `vertical_rate >= +200 ft/min` across all 217 real in-geofence vertical-rate readings in `adsb-test/samples/*.jsonl`; the maximum observed was +48 ft/min (the known EJU84YF flare artefact already used in `server/test_runway_config.py`). A "replay a real captured departure" approach is not possible with existing data.
- **D-02:** Instead, force a **synthetic** departure render (vertical_rate >= +200 injected directly, same technique used in 02-05 Task 3 to force the "Route unavailable" fallback via `server.plane.render.render_panel()`) to visually confirm the DEPARTING state (Blue field, nose-right silhouette) renders correctly on real glass. This validates the *visual* rendering path only — it does **not** validate that +200 ft/min is the right real-world threshold value, since no real sensor data is used. That remains an explicit open item until a genuine runway-3 departure is observed in production (`journalctl -u inkframe-poll` on the VPS showing `confirmed_state=departing`).

### Frame mount status
- **D-03:** The frame is currently on a desk / temporary location, not yet mounted on its final wall spot. Success criteria that depend on "typical wall-viewing distance" and "reads as ambient art on the wall" (ROADMAP criteria 1 and 4) can only be judged provisionally at the desk this phase. Record this caveat explicitly in the plan's verification rather than treating a desk-distance judgment as the final word — a follow-up check once wall-mounted is a legitimate open item, not a blocker to closing this phase.

### Long-caption legibility stress test
- **D-04:** UI-SPEC's flagged risk case — `fit_text_size()`'s shrunk-overflow path for a long city/airline name — has probably not been hit by chance yet (the only real flight rendered so far, DAH1112 from Béjaïa, has short caption text). Force this case deliberately: inject a real flight with a genuinely long city and/or airline name through the production render code path (same forcing technique as D-02 above), push it live, and look at the glass. Don't rely on chance for this specific edge case.

### Aircraft illustration upgrade (the phase's expanded scope)
- **D-05 (unlocking decision):** The user confirmed via **SenseCraft** (Seeed's official companion app for this panel) that a personal photo they sent displayed well on the real hardware. This proves the panel itself renders dithered/photographic content well — the flat, no-anti-aliasing, no-dither rendering rule in `02-UI-SPEC.md` Revision 2 was a deliberate **Phase 2 style choice** (the "poster" look), not a hardware limitation. `02-UI-SPEC.md`'s own rendering-rule note already anticipated this: *"Reserve Floyd-Steinberg dithering... for any future photographic content only."* This phase is that future.
- **D-06:** Given D-05, the aircraft illustration becomes **per-airline**, not a single shared generic shape. Each detected flight renders a dithered illustration specific to its airline (resolved via the existing D-02/02-04 `server/plane/enrich.py` callsign→route lookup, which already returns `airline_name`) — a materially bigger scope than Phase 2's single generic CC0 silhouette. This is deliberate, user-confirmed scope, not accidental creep.
- **D-07:** Per-airline illustrations render **dithered/photo-like** (same rendering family SenseCraft uses to display a real photo well on this panel), not the current flat single-color-fill treatment. This is a genuine style departure from Phase 2's flat "poster" look for the aircraft element specifically — the full-bleed background field and all caption text stay flat/solid as before (unchanged from 02-UI-SPEC.md Revision 2); only the aircraft illustration itself changes rendering treatment.
- **D-08:** Fallback illustration (airlines not covered by the generated set, and the "Route unavailable" enrichment-failure state where the airline is unknown) is a **single dithered generic illustration**, in the same rendered style as the per-airline set (not a return to the old flat-White CC0 silhouette) — for visual consistency across all render outcomes.
- **D-09 (corrected during plan-phase, 2026-08-26):** Illustrations are **AI-generated by the user outside this session** (e.g. ChatGPT, Midjourney), then handed to Claude as image files to process/vendor/integrate. Originally decided as "Claude generates them during the phase," but this environment has no image-generation tool available — verified via `ToolSearch` before spawning the phase researcher, not assumed. The licensing rationale is unchanged: AI-generated art (regardless of who runs the generation) still sidesteps the real trademark/licensing constraint that made Phase 2 reject per-airline art (`02-UI-SPEC.md` Design System: "the only CC0 candidate that reads as a modern commercial jet in profile without per-airline-livery detail"). **Practical consequence for planning:** this phase has a real external dependency — the plan must account for the user supplying illustration files (probably as a `checkpoint:human-verify`-style gate or a `user_setup`-style block, not an autonomous task), with a defined handoff format (file naming, per-airline count, resolution) the planner should specify.
- **D-10:** Mirroring by departing/arriving state (nose-right for departing, nose-left for arriving — `02-UI-SPEC.md` Layout & Composition zone 3) is unchanged and must still apply to every per-airline illustration and the fallback, not just the old generic silhouette.
- **D-11 (post-research decision, 2026-08-26):** Research (`03-RESEARCH.md` Open Question #1) surfaced a genuine fork: 2-color dithering (White + state background, zero risk to the locked `02-UI-SPEC.md` Color contract and its existing tests) vs. full multi-color airline **livery** (matches the user's own "covering" phrasing, but reopens the locked Color contract and breaks 2 existing `server/test_render.py` checks that currently assert no Yellow/Red nibble appears). **User chose full multi-color livery.** This means: `02-UI-SPEC.md`'s Color section needs an explicit addendum (the aircraft-illustration zone gets a documented exception to the "White foreground only" rule in the active states), `_build_active_canvas()`'s "exactly 2 distinct palette indices" guard rail must be widened to allow the illustration's full legal palette usage, and `server/test_render.py`'s existing Yellow/Red reservation checks need updating to scope them to the *background/caption* elements only, not the illustration zone.
- **D-12:** Yellow (reserved for Phase 4's low-battery indicator, still upcoming) is **allowed** in illustrations if a real airline livery uses it — the user judged the illustration zone and a future low-battery indicator are visually/spatially distinct enough that reuse isn't confusing. Note: Red's original reservation (`02-UI-SPEC.md`'s cross-phase note cites "Phase 3's disruption banner (RER-03)") is itself stale — RER-03 was deferred to v2 in the 2026-08-11 scope cut, so Red has no real future consumer in this roadmap at all; Red is effectively free regardless of this phase's illustration work.
- **D-13:** Real Spectra 6 panel RGB reference values (flagged unverified since `02-UI-SPEC.md`'s original draft) **must be resolved this phase**, not deferred — load-bearing now that full-color livery quantization is chosen (per `03-RESEARCH.md` Open Question #2: nominal placeholder RGB values could cause livery midtones to map to visually wrong panel inks even though the wire format stays legal). Source from the Waveshare `EPD_13in3e` reference driver or the T133A01 panel datasheet, per `02-UI-SPEC.md`'s own original open note.

### Full composition realignment with the real flightportrait product (second scope expansion, post-UI-SPEC-approval)

- **D-14 (reference evidence):** This session fetched and inspected real flightportrait.com product photography directly (not just the marketing screenshots used for Phase 2's Revision 1/2 comparisons): `poster-blue.jpg` (a framed poster showing 4 aircraft stacked vertically, each in full photographic livery color, with small serif captions under each) and `print-detail.jpg` (a close-up of the frame corner showing the "FLIGHTPORTRAIT" wordmark in uppercase, widely-tracked serif type). This is concrete visual evidence, not a guess — both images are saved locally this session for reference during planning/UI research. Two structural differences from the current locked design were identified: (1) typography — flightportrait uses a small-caps/uppercase serif with wide tracking, current design uses Inter (sans-serif, Bold); (2) background — flightportrait's poster background is a softer, more photographic sky-blue tone, current design uses a full-bleed saturated flat Blue/Green.
- **D-15 (typography):** Adopt a serif typeface direction, uppercase with wide letter-spacing for labels (matching the wordmark treatment), replacing Inter. Needs a real font choice + license vetted this phase (same OFL-style vendoring discipline as Inter in `02-UI-SPEC.md`'s Design System) — not yet chosen, left to research.
- **D-16 (information hierarchy):** Flight number and destination/origin become **co-equal in visual prominence** (both primary), with airline name and other details subordinate below them — a change from the current design where flight number alone is the single largest hero element (88px Heading) and route/destination is a smaller Body-size line beneath it. The user's own words: "le numéro de vol et la destination sont tout aussi importantes. Viennent ensuite le nom de la compagnie et les autres informations." This is a deliberate middle ground, not a full adoption of flightportrait's much smaller/uniformly-discreet caption style — Ink Frame's real-time single-flight use case (quickly checking the current flight) still needs fast at-a-glance legibility that flightportrait's daily-collection concept doesn't need to the same degree.
- **D-17 (background treatment):** Move from the current full-bleed saturated flat Blue/Green to a softer, more photographic-toned background, dithered using the same Floyd-Steinberg mechanism already verified this session for the illustration zone (`03-RESEARCH.md`) — extended from "one small illustration zone" to "most of the panel." The user explicitly accepted that this reopens the on-glass legibility question already verified once in `02-05-SUMMARY.md` (white text on a saturated flat field was confirmed "clearly legible" there) — a fresh on-glass legibility check against the new busier/softer background is required before this phase can close, using the same `checkpoint:human-verify` pattern already established.
- **D-18 (state signal, Claude's discretion flagged explicitly):** Not yet decided how the departing/arriving Blue-vs-Green state distinction survives a shift away from "one saturated flat color = the whole message" — e.g., a softer/photographic Blue-toned vs. Green-toned background variant, or another non-color-dependent reinforcement beyond the existing silhouette mirroring. Left to research/planning to propose, informed by D-17's constraint that the background is no longer a single flat legal index the way `02-UI-SPEC.md`'s state tables currently assume.

**Practical consequence:** the just-approved `03-UI-SPEC.md` (which explicitly scoped itself as "illustration zone only, everything else including background/typography unchanged from `02-UI-SPEC.md` Revision 2") is now superseded by this decision and needs a substantial revision — not a full from-scratch redesign (spacing geometry, copywriting contract text, and the overall zone layout order stay locked per D-14-18's own scope), but a real Revision 3 covering typography, the background's color/rendering treatment, and the flight-number/destination hierarchy.

### Personal photo background — explicitly OUT of this phase's scope
- Discussed and explicitly deferred to v2, despite D-05's evidence that it's technically viable. The user's own words: keep this phase's scope to the aircraft illustration only. See Deferred Ideas below and `REQUIREMENTS.md`'s new v2 "Personal Photo Background" section (VIS-01).

### Claude's Discretion
- Exact airline coverage list for the generated illustration set — left to research/planning, informed by real airline callsigns already seen in Phase 1 sample data and Phase 2's live enrichment cache (`poll_state.json` on the VPS).
- Exact image-generation tool/approach, prompt design, and post-processing pipeline (posterize/quantize/dither parameters) to get a generated illustration correctly onto the 6-color panel — left to planning/research; the existing Pillow dilate/flood-fill/erode pipeline used to flatten the Phase 2 CC0 silhouette is the closest existing precedent but will need adaptation for dithered (not flat) output.
- Whether the generic dithered fallback illustration is itself airline-neutral art or a dithered re-render of the retired CC0 silhouette shape — left to planning.
- Panel RGB reference values (still unverified per `02-UI-SPEC.md` Design System) — resolve if it becomes load-bearing for the dithering work, otherwise not a blocking item this phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 2 outputs this phase revises
- `.planning/phases/02-plane-view-end-to-end-slice/02-UI-SPEC.md` — the locked Revision 2 design contract (full-bleed state-color background, White foreground, flat no-dither rendering rule, silhouette mirroring by state, legibility flag, Copywriting Contract). **Updated 2026-08-26 (D-14 through D-18):** this phase now also revises the background color/rendering treatment and typography, not just the illustration zone — spacing geometry, the copywriting contract's actual text, and overall zone ordering stay locked; color treatment, typography, and flight-number/destination hierarchy do not.
- Real flightportrait.com product photography, fetched and inspected this session (D-14): `poster-blue.jpg` (framed poster, 4 aircraft in full livery color with small serif captions) and `print-detail.jpg` (frame-corner close-up showing the uppercase tracked-serif wordmark treatment) — saved locally this session at `/private/tmp/claude-501/-Users-florian-Projects-ink-frame/77c51871-756b-4360-a403-e0970ce98e56/scratchpad/flightportrait-poster-blue.jpg` and `flightportrait-print-detail.jpg` for reference during UI research/planning. Note this is a session-scoped scratchpad path, not part of the repo — the UI researcher should re-fetch from flightportrait.com directly if these files are no longer present when this phase is actually planned/executed.
- `.planning/phases/02-plane-view-end-to-end-slice/02-05-SUMMARY.md` — Task 3's on-glass verification evidence (legibility "clearly legible", edges "hard, flat", DAH1112 real-flight cross-check, forced enrichment-fallback technique this phase reuses for D-02/D-04 above)
- `server/plane/render.py` — `render_panel()`, `_build_active_canvas()`, `draw_silhouette()`, `load_binary_mask()`/`paste_mask()` (the flat-fill masking pipeline the new dithered illustration path must either extend or add alongside)
- `server/plane/enrich.py` — `lookup_route()` already resolves `airline_name` per flight; the illustration-selection logic keys off this same field
- `server/plane/runway_config.py` — `CLIMB_THRESHOLD_FPM = 200`, `DESCEND_THRESHOLD_FPM = -200` (A-02-02-01's unvalidated departure side, D-01/D-02 above)
- `server/panel_format.py` — `pack_panel()`, the 6-color palette definition the dithered output must quantize against

### Project planning docs
- `.planning/ROADMAP.md` — Phase 3 section, widened 2026-08-26 (this discussion) with success criterion 5 for the per-airline illustration pipeline; see its "Note on scope" for the full rationale
- `.planning/REQUIREMENTS.md` — PLANE-01/PLANE-02 (airline element this phase enriches visually); new v2 "Personal Photo Background" section (VIS-01, deferred here)
- `.planning/STATE.md` — Blockers/Concerns note on A-02-02-01's real-departure-threshold open item

[No other external specs/ADRs exist for this phase.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/plane/render.py`'s `load_binary_mask()`/`paste_mask()` — the existing flat-fill masking pipeline; a dithered illustration path is new code alongside this, not a replacement of it (the fallback + all caption text still use flat rendering)
- The Pillow dilate/flood-fill/erode cleanup pipeline used to flatten the Phase 2 CC0 silhouette (see STATE.md's Phase 2 decision log) — closest existing precedent for turning a raster asset into panel-legal output, though it targeted flat fills, not dithering; will need real adaptation for a dithered/photo-like target
- `server/plane/enrich.py`'s `lookup_route()` — already returns `airline_name`; no new enrichment call needed to key illustration selection

### Established Patterns
- Vendoring discipline (`stub-server/VENDOR.md`, `firmware/VENDOR.md` style provenance notes) — any generated illustration asset should get the same provenance treatment (generation date, tool/method, prompt if applicable) even though it's AI-generated rather than sourced from a third party
- Forcing a real render via the production code path (not a fabricated image) to validate an otherwise-rare/unobserved state — established in 02-05 Task 3 for the enrichment fallback, reused here for D-02 (departure) and D-04 (long caption)

### Integration Points
- Illustration selection is a new lookup keyed by `airline_name` (from the existing `enrich.lookup_route()` call already in `poll_loop.py`'s `run_once()`) — no new external API call, just a new local asset-selection step in the render path
- `draw_silhouette()` in `render.py` is the integration point where the new dithered-illustration path branches from the current flat-mask path

</code_context>

<specifics>
## Specific Ideas

- The user tested a personal photo via SenseCraft and confirmed it displayed well on the real panel — this is the concrete evidence behind D-05, not a general assumption.
- "Illustration de l'avion et de son covering" (the user's own phrasing) — per-airline illustration including the airline's visual livery/color identity, generated rather than sourced, per D-06/D-09.

</specifics>

<deferred>
## Deferred Ideas

- **Personal photo as the panel's background** — confirmed technically viable (D-05), but the user explicitly chose to keep this phase's scope to the aircraft illustration only. Tracked as `REQUIREMENTS.md`'s new v2 requirement **VIS-01**. Revisit in v2 planning.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 3-Visual Polish on Real Glass*
*Context gathered: 2026-08-26*
