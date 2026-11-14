# Phase 57: Combined Legacy-Frame Firmware Release - Context

**Gathered:** 2026-11-14
**Status:** Ready for planning

<domain>
## Phase Boundary

One signed OTA release gives the live frame every firmware change the fleet
needs: the common image-container reader (announced to the server), a hardware
header, and recovery after repeated 401. Requirement OTA-04.

This phase prepares, builds (CI) and documents the release. It does NOT publish,
schedule or flash it to the live frame: no `publish_release`, no production
registry import, no companion schedule, no `fw-v*` tag pushed, no merge to main.

</domain>

<decisions>
## Implementation Decisions

### Rollout gate
- **D-01:** The owner-set lock of 2026-10-31 stays. Publication waits for the
  `firmware/SIGNING.md` bench procedure on a non-live unit. The owner has no
  spare board, so the unit is the Seeed EE04 of Phase 58 (not yet arrived).
  Phase 57 prepares everything; publication is a later owner gesture.
- **D-02:** No cable flash is needed. The live frame already verifies signatures
  (cable-flashed once with signed fw-v1.0.0 on 2026-09-29; signed OTA to
  fw-v1.0.1; wrong-key, tampered and unsigned images refused and crash rollback
  seen on the real frame, see `hardware/BRINGUP-LOG.md`). The release must be
  signed with the same key as fw-v1.0.x. Not yet seen on a device: an image
  that boots but cannot reach the server (this phase's risk) rolling back.
- **D-03:** Base is `main` / fw-v1.0.4 (in service, installed by OTA per the
  owner; install date not yet given; read it with `firmware_cli list`).

### 401 recovery
- **D-04:** After repeated 401 the frame shows nothing new: it keeps its last
  image and retries with growing spacing. No new on-device screen. The existing
  token-erase and re-enrol on the next wake stays.

### Hardware header
- **D-05:** The frame sends a new hardware-type request header (none exists
  today). Name and format are for the planner, additive to the protocol.
- **D-06:** On a contradiction between the header and the type stored in the
  fleet database, the server refuses only firmware offers and the new container.
  The legacy raw image is still served, so the frame stays reachable. A frame
  that sends no header (current firmware) is served exactly as today.

### Sequencing with Phase 47.1 / 47.2
- **D-07:** Everything ships in one combined version. The 47.1 reference
  measurement is taken on the combined version. If the 14-day window already
  started on fw-v1.0.4, installing the combined version restarts it. Phase 47.2
  will need its own later firmware release.

### Container failure fallback
- **D-08:** If the new container fails validation, the frame remembers the failure
  (sticky flag), stops announcing the format on later wakes and so receives the
  raw image again. It keeps its last image meanwhile.
- **D-09:** To honour D-04, the "NO CONNECTION" fault screen drawn on the second
  consecutive `auth` / `enrol` failure is removed from the allow-list; those
  failures keep the last image.

### Claude's Discretion
- Header name, backoff schedule, host-test design, release instructions layout.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 57) - goal, precondition, criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` - OTA-04
- `.planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/55-HANDOFF.md` - 401 recovery left for this phase
- `.planning/workstreams/v1-2/phases/62-plane-screen-redesign/62-VERIFICATION.md` - regenerated status-screen masks
- `docs/IMAGE-FORMAT.md` - container spec, `X-Img-Fmt` announcement
- `firmware/SIGNING.md` - signing, bench procedure, rollback
- `firmware/main/image_container.[ch]`, `firmware/tests/test_image_container.c`
- `firmware/main/api_client.c` (401 handling), `firmware/main/state_machine.c`, `firmware/main/backoff.c`
- `firmware/tests/test_ota_policy.c`, `firmware/tests/run_host_tests.sh`
- `hardware/BRINGUP-LOG.md` - OTA/signature tests on the real frame (2026-09-29)
- `stub-server/byos_server.py` (hardware type lookup, OTA offers)
- `.planning/ROADMAP.md` (Phase 47.1, 47.2), `stub-server/test_phase47_freeze.py` (must stay green)

</canonical_refs>

<code_context>
## Existing Code Insights

- `imgc_parse` exists with host tests but is called by no firmware code.
- 401 on `/device/v1/display` already erases the device token (re-enrol next wake).
- No hardware-type header in the firmware today.
- Do not touch Phase 47/47.1 files or `hardware/`; wake interval and existing
  protocol unchanged.

</code_context>

<specifics>
No specific requirements beyond the decisions above.
</specifics>

<deferred>
## Deferred Ideas
- On-device "frame not recognised" screen (declined).
- Phase 47.2 wake-energy reduction: separate later release.
</deferred>
