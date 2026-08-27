# Phase 5: Battery Life & Low-Battery Indicator - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning

<domain>
## Phase Boundary

This context covers the phase's **second plan** (05-02, not yet planned): the low-battery indicator itself (DEVICE-04) — "User can see a low-battery indicator on the frame when the battery is running low." It does not touch 05-01, which is already executed for Task 1 (check-battery checker + pre-registered protocol) and has Tasks 2-3 (the real multi-day discharge run and its verdict) deliberately deferred to later, independently of this plan.

This plan delivers, end-to-end: a real battery-voltage reading on the device (replacing the current hardcoded `X-Battery-Mv: 0`), that value reaching the server, a threshold decision, and a visual indicator rendered on the panel when the battery is low. It does not cover the multi-day discharge run itself (05-01 Tasks 2-3) — the threshold locked here is a reasoned estimate, explicitly expected to be revisited once that real data exists.

</domain>

<decisions>
## Implementation Decisions

### Threshold and trigger policy
- **D-01:** Lock a concrete threshold now rather than leaving it a placeholder: **3500 mV**. This sits with real margin above `hardware/logtools.py`'s existing `--cutoff-mv 3400` convention (used with `--expect-depleted` in 05-01's protocol to mean "genuinely depleted"), so the warning fires with days of runway left, not at the edge of the protection circuit's cutoff. Trivially adjustable to a tuned value once 05-01 Tasks 2-3 produce a real discharge curve for this exact pack — do not block this plan on that data.
- **D-02:** Trigger is based on **raw millivolts**, not a derived percentage. No real discharge curve exists yet for this pack (that's what 05-01 Tasks 2-3 will produce), so a percentage would be fabricated precision. A direct mV comparison, consistent with how `check-battery`/`hardware/logtools.py` already reasons about this pack, is honest about what's actually known.

### Firmware scope — real ADC bring-up is in scope now
- **D-03:** This plan includes the real hardware bring-up, not just server-side plumbing against a fake value. `firmware/main/api_client.c`'s `telemetry_headers()` currently sends `X-Battery-Mv: "0"` unconditionally (see its own comment: *"no ADC/fuel-gauge driver is wired up this phase"* — that line is this plan). **Correction (2026-08-27, after the user explicitly ruled out any soldering or added components — "il n'y a absolument pas question pour moi de faire de la soudure ou de mettre des résistances"):** this is not from-scratch hardware work. The EE02 driver board (the actual carrier board this device uses, not the bare XIAO module) already has a factory-populated battery-voltage divider wired to `A0 (GPIO1)`, enabled via `D5 (GPIO6)` — documented on Seeed's own EE0x wiki, no soldering or external components involved. Scope: enable the existing circuit, read it via ESP-IDF's `esp_adc` API, and verify the reported mV looks like a real battery voltage on the already-flashed device — same `checkpoint:human-verify` discipline Phase 1's bring-up used (see `hardware/BRINGUP-LOG.md`), but a flash-and-observe check, not a pre-soldering continuity check. Without this, the indicator can never receive a real value.

### Visual treatment — icon, not text; new zone, not the state label
- **D-04 (supersedes 03-CONTEXT.md's D-12):** The indicator is a **battery icon glyph**, not text — a simple outline (body + terminal nub, partial fill showing a low level), White/Ivory, matching the size validated in this session's sketch (`battery_icon_sketch.png` / `battery_icon_zoom.png` variant "A sized like B" — a moderate ~72×34px reference size, scaled proportionally by the planner against whatever exact geometry the plan lands on). **Color is White/Ivory, not Yellow** — the user explicitly did not want Yellow for this despite 03-CONTEXT.md's D-12 reserving it for exactly this purpose. That reservation is now moot; Yellow remains free for any future use.
  - **Flagged explicitly:** every other element on this poster (state label, tag, both flight text blocks) is pure text — this is the poster's first and only icon. A deliberate, confirmed exception to the project's established "ambient art, not gadget" text-only visual language (see `REQUIREMENTS.md`'s Out of Scope table banning status LEDs/icons/badges elsewhere), not an oversight.
- **D-05:** The indicator gets its **own dedicated zone**, not a reuse of the existing `DEPARTING`/`ARRIVING` state label (top-left) or the `ORY · RWY 3` tag (top-right). Positioned **bottom-left** — the one area with no existing element in the locked two-flight layout (`03-CONTEXT.md` D-26/D-27: main illustration/text centered-upper, previous-flight card bottom-right). Visually balances the previous-flight card on the opposite side.
- **D-06:** The zone is **conditionally rendered** — present only when the battery is actually low, invisible/absent otherwise. Same principle already established for the previous-flight card (`03-CONTEXT.md` D-25: an element exists visually only when it has real information to show). The poster stays pixel-identical to today whenever the battery is fine.

### State-color interaction
- **D-07:** The existing Blue (`departing`) / Green (`arriving`) state background is **completely unaffected** by a low-battery warning — confirmed explicitly after a brief course-correction during discussion. The departing/arriving signal must never be lost or ambiguous because of a battery warning; the two signals coexist independently (state = background color, battery = the new bottom-left icon).

### Claude's Discretion
- Exact final pixel position/size of the battery icon within "bottom-left, moderate size" (the sketch is a size/placement reference, not a pixel-locked spec) — left to planning/implementation, ideally validated against a real preview render the way Phase 3's D-20/D-21/D-22 were, before committing.
- Exact battery-glyph line weight, corner style, and fill-level rendering (e.g. whether the icon always shows the same near-empty fill or reflects the actual mV reading proportionally) — left to implementation; a single fixed "low" glyph (not a live gauge) satisfies DEVICE-04's plain wording ("see a low-battery indicator") without overbuilding.
- Hysteresis/debounce on the threshold crossing (avoiding a flicker if a reading lands right at 3500 mV across consecutive polls) — not raised by the user, but cheap and standard practice; implement a small buffer (e.g. re-arm only after a materially higher reading) rather than a bare `<` comparison on every poll.
- How the mV value threads from the HTTP header through `poll_loop.py`/`poll_state.json` into `render.py`'s active-canvas builder — an internal plumbing decision, no user-facing behavior implication.
- Exact GPIO/ADC approach on the XIAO ESP32-S3 Plus (voltage divider ratio, `esp_adc` calibration) — a real research question for the phase researcher; no existing documentation in this repo answers it yet.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase's own prior work
- `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` and `05-01-SUMMARY.md` — the pre-registered protocol and `check-battery` checker this plan's threshold (D-01/D-02) stays consistent with
- `hardware/BATTERY-RUN.md` — the run protocol, thresholds table (`--cutoff-mv 3400`), and ceiling this plan's D-01 threshold sits above
- `hardware/logtools.py` — `check-battery`'s actual implementation (`BATTERY_MV_RE`, the depleted-cutoff logic D-01/D-02 reuse the convention of)

### Firmware (D-03)
- `firmware/main/api_client.c` — `telemetry_headers()`, the exact hardcoded `X-Battery-Mv: "0"` line and its comment naming this phase/requirement as the reason
- `firmware/VENDOR.md` — documents the same placeholder and the upstream telemetry-header contract (all four headers sent unconditionally)
- `hardware/BRINGUP-LOG.md` — the Phase 1 hardware bring-up precedent (device connection, verification pattern) this plan's ADC bring-up should follow
- `stub-server/byos_server.py` (~line 93) — already parses/accepts the `X-Battery-Mv` header; confirms the wire contract exists server-side, only the real device-side value is missing

### Locked visual layout this plan must fit into without disturbing (D-04/D-05/D-06/D-07)
- `.planning/phases/03-visual-polish-on-real-glass/03-CONTEXT.md` — D-12 (Yellow reservation, now superseded by this phase's D-04), D-25/D-26/D-27 (the exact locked two-flight poster layout: frame inset, top labels, main/previous illustration+text positions and sizes)
- `server/plane/render.py` — `MARGIN`, `SAFE_BOX`, `STATE_BACKGROUND`, `STATE_INK`, font constants (`PT_SERIF_REGULAR` etc.), and wherever `_build_active_canvas()` (or equivalent) composes the final panel — the integration point for the new icon-drawing branch
- `server/panel_format.py` — `PALETTE_RGB`/`IDX_WHITE` (the icon's color), `WIDTH`/`HEIGHT` (1200×1600)

### Project planning docs
- `.planning/REQUIREMENTS.md` — DEVICE-04 (this plan's target requirement) and the Out of Scope table (status LEDs/icons/badges ban — D-04 is a deliberate, confirmed exception)
- `.planning/ROADMAP.md` — Phase 5 section, "a second plan to build the low-battery indicator UI itself is still TBD"

### Session sketches (visual reference, not repo files)
- `/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-reprise-travail-a8e93d/ab4e4da0-830e-42de-b756-1514fbf40997/scratchpad/battery_icon_sketch.png` and `battery_icon_zoom.png` — three icon-style mockups (A/B/C) rendered against the real palette/fonts/layout; user chose "A's icon-only style, sized like B." Session-scratchpad paths, not part of the repo — re-derive from D-04/D-05's written description if these files are no longer present when this phase is actually planned/executed.

[No other external specs/ADRs exist for this phase.]

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `hardware/logtools.py`'s `BATTERY_MV_RE` and depleted-cutoff logic — the existing convention for reasoning about this pack's voltage, D-01/D-02 stay consistent with it rather than inventing a new threshold philosophy
- `stub-server/byos_server.py`'s existing `X-Battery-Mv` header handling — the wire format is already accepted server-side in the stub; the production `server/` code needs the equivalent read-and-store step

### Established Patterns
- Real preview renders before committing to visual decisions (Phase 3's D-20/D-21/D-22 precedent, reused directly in this session via `battery_icon_sketch.png`) — the planner/executor should generate a real render preview of the final icon placement before treating it as final, same discipline
- Conditional-element rendering (D-25's previous-flight-card pattern: an element exists only when it has real information) — D-06 reuses this exact precedent rather than inventing a new one
- `checkpoint:human-verify` for real-hardware confirmation (Phase 1's bring-up pattern) — D-03's ADC verification should use the same gate, not a self-reported "looks right"

### Integration Points
- `firmware/main/api_client.c`'s `telemetry_headers()` — where the real ADC read replaces the hardcoded `"0"` literal
- Wherever `poll_loop.py` currently reads/stores per-request telemetry (the `X-Battery-Mv` header is already received by the stub; the production server needs the same extraction, then persistence into `poll_state.json` alongside the existing flight/route state)
- `render.py`'s active-canvas builder — where the new conditional battery-icon draw call branches in, alongside the existing silhouette/text draw calls

</code_context>

<specifics>
## Specific Ideas

- The user asked for a visual sketch mid-discussion rather than deciding from a text description alone — three icon-style/size variants were rendered against the real 1200×1600 canvas, Blue background, PT Serif fonts, and existing layout elements (state label, tag, main/previous flight placeholders) so the choice was made against something close to the real thing, not an abstraction. Final choice: icon-only (no "LOW" text), sized like the middle ("B") variant.
- The user's own correction mid-discussion: "tu me parles de texte alors que je pensais à un icône batterie tout simplement" — the icon direction was a deliberate correction of an initial text-based framing, not an afterthought.

</specifics>

<deferred>
## Deferred Ideas

- **A live/proportional battery gauge** (icon fill reflecting the actual mV reading, or a percentage/days-remaining readout) was not requested — DEVICE-04's plain wording ("see a low-battery indicator") is satisfied by a single fixed low-battery glyph. Noted here so a future richer battery UI (e.g. a companion web interface health view — see `REQUIREMENTS.md`'s CFG-03, already seeded 2026-08-27) doesn't get accidentally folded into this plan.
- **Exact tuned threshold from real discharge data** — D-01's 3500 mV is a reasoned estimate, not derived from this pack's actual measured curve (that's 05-01 Tasks 2-3's job, still pending). Revisit once that data exists; this is a one-line constant change, not a replan.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 05-Battery Life & Low-Battery Indicator (this context covers the low-battery-indicator plan specifically)*
*Context gathered: 2026-08-27*
