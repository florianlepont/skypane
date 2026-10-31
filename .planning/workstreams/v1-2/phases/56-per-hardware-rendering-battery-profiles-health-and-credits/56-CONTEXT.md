# Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

What a frame displays and how its health is judged follow its hardware profile, and data sources are credited.

Requirements: HWR-01, HWR-02. Depends on Phases 48, 50, 51. Final legacy battery numbers need Phase 47 (open, VAL-03 reopened): they are recorded as provisional, never frozen.

Out of scope: second hardware battery model (Phase 58 rebuilds it), firmware (57), fleet poll loop (52), pairing/admin console (55), any production deploy. Phase 47 files and `hardware/` are untouched.

</domain>

<decisions>
## Implementation Decisions

### Owner-fixed
- **D-01:** The live frame's render and responses do not change by one pixel. A golden-image baseline of the legacy render is added and `stub-server/test_phase47_freeze.py` stays green. Expand-only. No production deploy.
- **D-02:** Legacy battery numbers are recorded as **provisional** with provenance, values unchanged. The future second hardware (Seeed EE04 7.3in, 800x480, ~20-25 s full refresh) gets only an empty "to be measured in Phase 58" slot; no number is invented.

### Rendering (owner choice)
- **D-03:** "Native" means a dedicated landscape composition. The profile selects a layout family (portrait = the current composition, untouched; landscape = new). Geometry (width, height, packed size) comes from the profile; the simulated 800x480 type renders landscape natively. The layout family is reusable by the EE04 in Phase 58.

### Themes and palette (owner choice)
- **D-04:** Themes declare the inks they need; a profile exposes only the themes its palette supports. A stored theme that a profile does not offer falls back to the default theme. Stored theme ids and the 16 existing themes stay unchanged on disk.

### Battery provenance (owner choice)
- **D-05:** Provenance lives in the hardware profile, per value (curve, low, low-clear, critical, critical-recover): source, provisional/final status, date. Legacy values are marked provisional pending Phase 47. Thresholds, curve, percent and health views read the device's profile instead of module constants.

### Credits (owner choice)
- **D-06:** A public companion page (reachable without sign-in), bilingual EN/FR, rendered from one data file listing adsb.fi (with link to its home page), adsb.lol, adsbdb and OurAirports. The README/COMPLIANCE credits can reference the same file.

### adsb.fi / adsb.lol contact
- **D-07:** Claude cannot send messages. An English draft message about multi-zone usage is prepared for the owner, its status recorded as "to send" in the phase directory.

### Claude's Discretion
Module names, the golden-image mechanism, plan split and waves, how health views are parametrised, and how the data file is validated.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 56 goal and criteria (edit only Phase 56 lines)
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — HWR-01, HWR-02
- `.planning/workstreams/v1-2/STATE.md` — edit only Phase 56 lines
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md`
- `.planning/workstreams/v1-2/phases/50-common-image-format/50-CONTEXT.md`
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-CONTEXT.md` (D-16: non-1200x1600 poll refused until this phase)
- `server/hardware.py`, `server/panel_format.py`, `server/themes.py`, `server/device_policy.py`
- `server/plane/render/` (layout.py, glyphs.py, hold_screens.py, style.py), `server/poll_cycle.py`
- `companion/battery.py`, `companion/health_signals.py`, `companion/health_sections.py`, `companion/device_scope.py`
- `COMPLIANCE.md`, `docs/IMAGE-FORMAT.md`, `stub-server/test_phase47_freeze.py`
- `.claude/CLAUDE.md`, `.claude/skills/sketch-findings-skypane/`

</canonical_refs>

<code_context>
## Existing Code Insights

- `HardwareProfile` already carries width, height, palette, battery profile; `_LEGACY_BATTERY` is built from `device_policy` constants.
- Render modules import `WIDTH`/`HEIGHT` from `panel_format` as module constants; themes use `IDX_*` Spectra 6 indices.
- Battery constants (`BATTERY_*`, `LOW_BATTERY_DISPLAY_MV`) are read module-wide by `companion/battery.py` and `health_signals.py`.

</code_context>

<specifics>
- Owner is French-speaking and not an engineer: owner-facing instructions in plain French; repo docs in English.
</specifics>

<deferred>
- EE04 battery model and real panel timings — Phase 58.
- Final legacy battery numbers — after Phase 47 closes.
</deferred>
