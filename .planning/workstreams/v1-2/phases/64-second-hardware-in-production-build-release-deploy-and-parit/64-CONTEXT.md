# Phase 64: Second Hardware in Production - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the second hardware type (`seeed-ee04-7in3-spectra6`, 800x480) a supported
production product next to the live frame (`xiao-ee02-13in3-spectra6`): CI build,
typed signed release, typed deploy import, a production switch of its own, OTA
reconcile, companion parity, measured firmware assumptions, documents, and an
owner-validated walk-through. Scope is fixed by ROADMAP.md "Phase 64" (HW2-03..05)
and `64-AUDIT.md`. Not in scope: 90/180 degree turn, photo mode, battery numbers
beyond Phase 58's measurements.

</domain>

<decisions>
## Implementation Decisions

### Production gate
- **D-01:** The second type is exposed by a dedicated switch of its own (a new
  environment variable, separate from `SKYPANE_SIM_HARDWARE`). The two simulated
  types stay hidden in production. The profile's `gated` flag is not flipped in code.
  The switch ships closed (off).
- **D-02:** The switch is turned on in production only after the owner's written
  confirmation. Never lifted by the agent. The tests that pin the gate off are changed
  on purpose, with a comment saying why.

### Release ordering (Phase 57 vs Phase 64)
- **D-03:** The first signed image of the second type is published AFTER the Phase 57
  release. Phase 57 is `human_needed` (bench B1-B9 not done, no release published).
- **D-04:** `.github/workflows/firmware-release.yml` is not edited while Phase 57 is in
  progress. All planning for that file goes in the last wave, gated on Phase 57's
  release being published. Everything else (CI build, server, companion, docs,
  provision.sh) can proceed first. A release carrying only live-frame assets must still
  import; the live frame's release path and signed image stay unchanged.

### provision.sh guard
- **D-05:** The live-frame guard in `firmware/provision.sh` is typed, like
  `flash-second.sh`: read the chip MAC, refuse the live frame's MAC or type, and require
  the MAC typed back at an interactive prompt. Not a port-only check.

### Owner-validated steps (no real unit yet)
- **D-06:** Phase 58 still waits on the physical EE04 unit. Success criteria 5, 7 and 9
  (real signed OTA on a second-type frame, measured wake/refresh/pin values, companion
  walk-through in English and French) are planned as owner-validated steps, never faked.
  Battery profile stays provisional until Phase 58 measures it.

### Claude's Discretion
- Name of the new switch, wave split, plan sizing, test layout, reconcile and
  `import-dir` implementation details, battery-curve call-site refactor.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` "Phase 64" - goal, 9 success criteria, must-not-break list
- `.planning/workstreams/v1-2/phases/64-second-hardware-in-production-build-release-deploy-and-parit/64-AUDIT.md` - gaps 1-7, partials, firmware risks
- `.planning/workstreams/v1-2/phases/57-combined-legacy-frame-firmware-release/57-VERIFICATION.md`, `57-RELEASE-INSTRUCTIONS.md` - Phase 57 state and release gate
- `.github/workflows/firmware-release.yml`, `.github/workflows/ci.yml` (478-490), `.github/workflows/firmware.yml`
- `server/hardware.py` (gate, `available_types`), `server/firmware_cli.py` (127-131, 203-220), `server/fleet_cycle.py` (`reconcile_firmware=device.is_live`)
- `scripts/fw_release_manifest.py`, `firmware/check_production_config.sh`, `firmware/provision.sh`, `firmware/flash-second.sh`, `firmware/SIGNING.md`
- `companion/theme_preview.py`, `companion/preview_images.py`, `server/plane/render/landscape_hold.py`
- `deploy/README.md` (474-490), `hardware/SECOND-HARDWARE*.md`
- `stub-server/test_phase47_freeze.py` - must not break

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/fw_release_manifest.py` is already type-aware; `server/firmware_cli.py` already reads `release-<key>.json` + `skypane-<key>-<tag>.bin`.
- `flash-second.sh` guard is the model for `provision.sh`.
- Phase 58 identity proof (section-level identity of the legacy production image).

### Established Patterns
- Per-type registries and offers; typed asset names; hardware profile drives render, battery thresholds, previews.

### Integration Points
- `available_types` gate, `fleet_cycle` reconcile, `import-dir`, ci.yml deploy download, companion `battery.battery_percent` call sites.

</code_context>

<specifics>
## Specific Ideas

Owner wants short answers in French; written artefacts in English. Draft PRs only; the owner approves deploys.

</specifics>

<deferred>
## Deferred Ideas

- 90/180 degree turn and photo mode (seed for v1.3).
- Update page install/cancel per device instead of per type (limit shared with several live frames).

</deferred>

---

*Phase: 64-second-hardware-in-production*
*Context gathered: 2026-11-14*
