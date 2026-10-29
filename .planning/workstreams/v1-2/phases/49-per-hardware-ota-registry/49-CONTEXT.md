# Phase 49: Per-Hardware OTA Registry - Context

**Gathered:** 2026-10-29
**Status:** Ready for planning

<domain>
## Phase Boundary

The owner can publish and schedule firmware per hardware type, and no frame can ever be offered a binary built for another type or an older build. Covers OTA-01, OTA-02, OTA-03. Out of scope: the combined legacy-frame firmware release (OTA-04, Phase 57), web upload, Auth0 and roles (Phases 54-55), the second hardware itself (Phase 58).

</domain>

<decisions>
## Implementation Decisions

### Publishing and scheduling (discussed)
- **D-01:** Publishing stays on the current channel: tag, CI build, reviewed deploy, `firmware_cli import-dir` on the VPS. The hardware type is added to the release manifest and to `firmware_cli`. No web upload of binaries in this phase: the companion is still guarded only by the shared password until Phases 54-55.
- **D-02:** Scheduling stays on the companion Update page, extended with a hardware-type choice and an independent schedule per type. With one type in production the page must look and behave as today.

### Downgrades (decided after research)
- **D-03:** The owner can still schedule an older already-published release above the floor for a voluntary rollback. The "lower build number refused" rule (OTA-02) applies when a release is published, per hardware type, and non-bench only. Defaults accepted from research: a second type reuses the repo-wide `fw-v*` tag series; tests use a synthetic image builder rather than a committed real-image fixture.

### Not discussed (planner and researcher resolve within the success criteria)
- Registry shape per hardware type and the migration of `firmware/registry.json` (the live frame's entries keep working unchanged; a `*.pre-fleet` copy is kept before any rewrite).
- How a binary's app descriptor and chip target are checked against the declared type, and the monotonic build number that refuses downgrades.
- The OTA signing decision (OTA-03). Images are already signed today (RSA-3072, no eFuse, see `firmware/SIGNING.md`). The planner must surface the owner's decision (one key or one per type, any one-time cable flash) as an explicit checkpoint, recorded before any second hardware is provisioned. It is not decided here.

### Claude's Discretion
Module and function names, registry document layout, CLI verb names, test layout, plan split and waves.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/workstreams/v1-2/ROADMAP.md` - Phase 49 goal and success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` - OTA-01, OTA-02, OTA-03 (OTA-04 is Phase 57)
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md` - hardware registry (D-05), fleet.db, expand-only migration rule
- `server/hardware.py` - committed hardware profiles and `FirmwareTarget` (idf target, project name, max image bytes)
- `server/firmware_registry.py` - current single registry: publish, schedule, offer, reconcile
- `stub-server/byos_server.py` - OTA offer composition and device report recording
- `firmware/SIGNING.md` - signing configuration and procedure
- `deploy/README.md` - "Firmware releases (OTA)" section
- `.claude/CLAUDE.md` - conventions (English comments, no plan IDs in comments, function-size gate)

</canonical_refs>

<code_context>
## Existing Code Insights

- One registry (`firmware/registry.json`), one schedule and one version floor (`fw-v1.0.0`) for the whole fleet; releases are content-addressed images under `firmware/<sha256>.bin` and are never pruned.
- Releases are tagged `fw-vMAJOR.MINOR.PATCH`; the byos offer is computed by `compute_offer()` from the device's report.
- Hardware types already carry a `FirmwareTarget` in `server/hardware.py`; devices have a server-assigned hardware type in fleet.db.
- A change to the registry file format must not break the live frame's existing entries (expand-only).

</code_context>

<specifics>
## Specific Ideas

- With a single hardware type in production, nothing visible changes for the owner.

</specifics>

<deferred>
## Deferred Ideas

- Direct binary upload from the companion: revisit after Auth0 and roles (Phases 54-55).

</deferred>
