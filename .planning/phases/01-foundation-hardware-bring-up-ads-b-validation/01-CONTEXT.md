# Phase 1: Foundation — Hardware Bring-up & ADS-B Validation - Context

**Gathered:** 2026-08-04
**Status:** Ready for planning

<domain>
## Phase Boundary

De-risk the two highest-uncertainty technical unknowns before any user-facing view is built:

1. Whether real-time plane position data for Orly runway 3 can be obtained reliably — starting with a no-hardware aggregator-API test, falling back to a local ADS-B receiver only if needed.
2. Whether the device can run the full wake → HTTPS poll → download → display → deep-sleep → exponential-backoff cycle on battery power, with a real measured mAh-per-cycle figure.

This is a foundation/spike phase — it proves the approach works, it does not ship a user-facing plane or RER view (that's Phase 2/3). No hardware has been purchased yet; the plan must account for ordering lead time.

</domain>

<decisions>
## Implementation Decisions

### Plane-detection validation approach (reopens a prior "pending" decision in PROJECT.md)
- **D-01:** Test an ADS-B aggregator API first (e.g. ADS-B Exchange, adsb.fi, airplanes.live) as the primary candidate data source for runway-3 plane detection — no local hardware, no antenna, no legal ambiguity, near-zero cost/time to test.
- **D-02:** Only fall back to a local RTL-SDR receiver (and, if reception is confirmed viable, a permanent Raspberry Pi + dump1090/readsb setup forwarding to the VPS) if the aggregator API's coverage at runway 3 — specifically near-ground/low-altitude, which is the hardest case for any receiver — proves insufficient.
- **D-03:** This reverses/supersedes PROJECT.md's current framing of the ADS-B aggregator as "documented fallback only" and local ADS-B as primary — Phase 1's validation should test API-first. **Downstream note:** PROJECT.md/REQUIREMENTS.md's "Out of Scope" and "Key Decisions" sections should be updated after Phase 1 validation confirms which path wins (not before — the point of Phase 1 is to find out).
- **D-04:** If the local RTL-SDR/Pi fallback is ever needed, its cost is tracked as a **separate budget line**, not counted against the €300 "display + compute" hardware ceiling defined in PROJECT.md (which was scoped specifically to the frame device itself).

### Firmware bring-up path
- **D-05:** Board hardware stays as originally planned — Seeed XIAO ESP32-S3 Plus + EE02 kit. Confirmed after user asked about the Arduino Nano ESP32 board as an alternative; rejected because the EE02 kit is pre-matched to drive the tricky 13.3" dual-chip Spectra 6 panel, and matches flightportrait's reference hardware for direct driver-code reuse.
- **D-06:** Firmware development goes straight to ESP-IDF — no Arduino-framework prototyping detour. Reasoning: Phase 1's own success criteria (exponential backoff, deep sleep, real battery measurement) need the fine-grained sleep-current control that only ESP-IDF provides; starting in Arduino would mean redoing this work before Phase 1 is actually done.

### Battery measurement method
- **D-07:** Use the simple time-to-depletion method: charge the battery pack fully, let the device run its normal wake/poll/sleep cycle untouched, and note how many days/cycles elapse until it dies or hits low-battery. Divide capacity (mAh) by days-until-dead for an approximate mAh/cycle figure. Chosen explicitly for being achievable with no extra hardware or technical setup — user self-identified as non-technical on hardware.
- **Rejected:** USB inline power meter (more precise, but requires buying/reading an extra gadget — not worth it given the simpler method meets the phase's needs).

### Hardware readiness & stub server hosting
- **D-08:** Nothing has been purchased yet — XIAO ESP32-S3 Plus + EE02 kit, battery pack, and (conditionally) RTL-SDR are all still to be ordered. **The plan must budget for shipping/lead time before any hands-on hardware bring-up work can start**, and should sequence software-only work (stub server, ESP-IDF setup, aggregator API test) ahead of hardware-dependent work where possible.
- **D-09:** The Phase 1 "stub server" runs locally (on the user's own computer/network), not on the real Hetzner VPS. Provisioning the actual VPS is deferred to Phase 2, when the real rendering pipeline is built — avoids paying for/managing a VPS before it's needed.

### Claude's Discretion
- Specific choice of which ADS-B aggregator API to test first (ADS-B Exchange vs. adsb.fi vs. airplanes.live) — left to the researcher/planner to evaluate based on documented coverage quality near Orly and ease of integration.
- Exact wake-interval cadence used during the Phase 1 backoff/battery test — left to the planner.
- Local stub server implementation details (language/framework) — left to the planner, though it should be lightweight given it's throwaway for Phase 1.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Reference architecture
- flightportrait/frame — https://github.com/flightportrait/frame — reference project this build mirrors: wake/poll/backoff device loop, 3-endpoint HTTPS poll protocol (`docs/PROTOCOL.md` in that repo), BLE Security 2 provisioning, SHA-256 verified downloads, reference Python server. Study/fork its display driver and deep-sleep state machine directly.

### Project planning docs (this repo)
- `.planning/PROJECT.md` — current locked constraints (€300 hardware budget scoped to "display + compute", battery-only v1, VPS-not-home-server hosting) and the "Pending" plane-detection decision this phase resolves. Note: its ADS-B framing is now superseded by D-01–D-03 above pending Phase 1 validation results.
- `.planning/REQUIREMENTS.md` — DEVICE-03 (wake/poll/backoff loop) and DEVICE-05 (battery-only) are the two requirements this phase covers.
- `.planning/ROADMAP.md` — Phase 1 success criteria (4 criteria: full wake/poll/download/display/sleep cycle, exponential backoff, ADS-B reception validation, measured mAh/cycle).
- `.claude/CLAUDE.md` — technology stack doc. Note: its "Stack Patterns by Variant" section recommending Arduino-first bring-up is explicitly overridden by D-06 above (straight to ESP-IDF).

[No other external specs/ADRs exist yet — this is a greenfield planning-only repo with no code.]

</canonical_refs>

<code_context>
## Existing Code Insights

No code exists in this repository yet (planning-only — `.planning/` and `.claude/CLAUDE.md` only). No reusable assets, established patterns, or integration points to note. This phase starts from zero.

</code_context>

<specifics>
## Specific Ideas

- User explicitly described themselves as having "very limited hardware technical knowledge" — plans, research output, and execution guidance for this phase should favor simple, low-setup approaches over precise-but-complex ones wherever a simple approach is sufficient (reflected in D-01/D-07 above).
- User's address (<street-address>) borders Orly airport — noted in PROJECT.md as a reason local ADS-B reception was expected to be strong, but this doesn't preclude testing the API-first approach given it's cheaper to validate.

</specifics>

<deferred>
## Deferred Ideas

- Whether to build the permanent local ADS-B receiver pipeline (Raspberry Pi + dump1090/readsb + forwarder to VPS) — deferred until Phase 1 determines whether the aggregator API path is sufficient. If not sufficient, this becomes required setup work, likely still within Phase 1 or spilling into early Phase 2.
- Provisioning the real Hetzner VPS — deferred to Phase 2.
- Updating PROJECT.md/REQUIREMENTS.md's ADS-B framing (currently written as "local ADS-B primary, aggregator API fallback") — should happen once Phase 1's validation produces a result, not before.

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 1-Foundation — Hardware Bring-up & ADS-B Validation*
*Context gathered: 2026-08-04*
