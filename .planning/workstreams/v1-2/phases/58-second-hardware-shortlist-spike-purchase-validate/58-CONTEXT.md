# Phase 58: Second Hardware (Shortlist, Spike, Purchase, Validate) - Context

**Gathered:** 2026-11-01
**Status:** Ready for planning (part 1 only)

<domain>
## Phase Boundary

A second hardware type is chosen on evidence and proven on a real unit. Requirements: HW2-01, HW2-02. Depends on Phases 49, 50, 56 (closed).

**This session covers part 1 only:** a documented, costed shortlist and a time-boxed ESP-IDF panel-driver spike. It stops after the spike with a decision for the owner. Part 2 (evaluation unit: cable flash, real OTA, signing bench, native layout, battery sample, new battery model) is planned but NOT executed, and is blocked until the owner's explicit written agreement to buy, given in the conversation.

Out of scope: any purchase, order call or payment; flashing the live frame; any production deploy; existing Phase 47 files in `hardware/` (`FIELD-VALIDATION*.md`, `logtools.py`, `BATTERY-MODEL.md`, `PACK-ACCEPTANCE.md`, `logs/`, `BOM.md`). The Phase 48 freeze test `stub-server/test_phase47_freeze.py` stays green.

</domain>

<decisions>
## Implementation Decisions

### Owner-fixed (task brief)
- **D-01:** Colour is kept. Common versioned image format (Phase 50) carries size and palette in its header. Native 800x480 landscape render already exists server-side (Phase 56).
- **D-02:** Known candidates, all 7.3" E Ink Spectra 6, 800x480: Seeed XIAO ePaper 7.3" kit (EE04), Seeed reTerminal E1002, Good Display GDEP073E01 (bare panel), Waveshare 7.3" HAT (E), Waveshare ESP32-S3-PhotoPainter. Prices, stock, VAT, France delivery and ESP-IDF drivers are unverified and must be reconfirmed on the product pages.
- **D-03:** The new battery type's model is rebuilt in part 2 from a real measurement; no number is invented now.
- **D-04:** The signing bench procedure of `firmware/SIGNING.md` is planned explicitly in part 2 and must pass on the evaluation unit before it takes any fleet role; Phase 57 does not start before.

### Cost ceiling (owner choice)
- **D-05:** Target total for the complete device (panel + board, plus battery and cable, delivered to France, TTC) is **at most 100 EUR TTC**. The project ceiling (300 EUR) and the current kit (~143 EUR HT) remain context. Shortlist entries report their full landed cost against this target and flag any that exceed it.

### Selection criterion (owner choice)
- **D-06:** Lowest cost ranks first. Port ease, battery and enclosure are reported but do not outrank cost. Consequence to state in the shortlist: a bare panel needs a driver board and a driver written, so the spike must price that extra work and risk honestly.

### Spike scope (owner choice)
- **D-07:** Time box is **1 day**, no hardware in hand: read the manufacturer driver sources, compile a trial driver in the `espressif/idf:v5.3.1` container (`firmware/build.sh`), run the host tests. Verdict per candidate: controller identified, init and refresh sequence found, pin map known, build passes. Failure if the controller is unknown or the init sequence cannot be found. Nothing is flashed anywhere.
- **D-08:** Product pages are opened and read (not only web search); each fact is dated with its URL, and what could not be confirmed is listed.

### Part 2 preparation (owner choice)
- **D-09:** A separate plan for part 2 is written in full, marked blocked on the owner's written purchase agreement.

### Claude's Discretion
- Document layout, file names (new files only), spike harness structure, test choices.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 58 section, Phase 49 precondition note)
- `.planning/workstreams/v1-2/REQUIREMENTS.md` (HW2-01, HW2-02)
- `.planning/workstreams/v1-2/phases/56-per-hardware-rendering-battery-profiles-health-and-credits/56-CONTEXT.md` (EE04 slot, landscape layout family)
- `.planning/workstreams/v1-2/phases/50-common-image-format/50-CONTEXT.md` (image container)
- `firmware/SIGNING.md`, `firmware/VENDOR.md`, `firmware/build.sh`, `firmware/sdkconfig.defaults`, `firmware/sdkconfig.ee02.defaults`
- `firmware/main/panel.c`, `firmware/main/panel.h`, `firmware/main/epd13in3e.c`, `firmware/main/Kconfig.projbuild`
- `hardware/BOM.md` (read only, current kit pricing and budget method)
- `CLAUDE.md` conventions (English comments, no plan/phase IDs in comments)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `firmware/main/panel.c` already isolates the panel behind `fp_panel_draw`, `epd_init`, `epd_blit`, `epd_sleep`; a second driver can plug in behind the same interface.
- Per-board overlays (`sdkconfig.ee02.defaults`) carry pins and hardware revision.
- Server side: hardware profiles and landscape layout from Phase 56; container header carries size and palette from Phase 50.

### Established Patterns
- The existing driver is specific to the 13.3" dual-controller (master/slave) panel; the 7.3" panels use a single controller, so the driver is not shared.
- Firmware host tests: `firmware/tests/run_host_tests.sh`.

### Integration Points
- Firmware image reader and OTA wiring for the container belong to Phase 57, not here.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- Enclosure design for the new unit; solar. (Not this phase.)

</deferred>
