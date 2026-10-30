# Phase 50: Common Image Format - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

One versioned image container (width, height, palette, length, checksum in a fixed header) that any hardware type can carry, introduced without changing what existing frames receive. Delivers: a written spec with golden fixtures (IMG-01), server-side negotiation so only a frame that announces support gets the container while every other frame gets today's raw 960,000-byte image byte for byte (IMG-02), and a host-tested C reference reader that validates before touching a display buffer and still accepts the legacy raw format (IMG-03).

Not in this phase: publishing or flashing firmware (Phase 57), wiring the reader into the live download path, per-device images (Phase 51), per-hardware rendering (Phase 56), any production deploy.

</domain>

<decisions>
## Implementation Decisions

Decisions below marked "owner" were fixed by the project owner in the phase brief. The rest were delegated to Claude on 2026-10-30 ("je te laisse tout choisir") and follow the milestone research defaults.

### Owner-fixed (not to be reopened)
- **D-01 (owner):** Common, versioned container; header carries width, height, palette, payload length and checksum.
- **D-02 (owner):** A frame that does not announce support receives its current raw 960,000-byte image byte for byte; only an announcing frame receives the container.
- **D-03 (owner):** The reference reader rejects bad magic, version, length or panel dimensions before touching a display buffer, and always accepts the legacy raw format. It is a host-tested firmware reader.
- **D-04 (owner):** Firmware stays in the ESP-IDF 5.3.1 build image; nothing is published or flashed in this phase.
- **D-05 (owner):** Nothing may change what the live frame receives, its state, its registry or its BYOS responses. The Phase 48 freeze test stays green. No production deploy.

### Announce signal (delegated)
- **D-06:** The frame announces support with an explicit request header `X-Img-Fmt: <n>` (highest container version it reads) on the display poll. The server never requires it. Absent, empty, malformed, zero or unknown values all mean legacy raw. The server picks the highest version it supports that is not above the announced one.
- **D-07:** The announcement is per request only. It is not persisted in device state, the registry or the fleet database, so the legacy frame's recorded state cannot change.

### Header layout (delegated)
- **D-08:** Fixed 24-byte little-endian header, every field naturally aligned: magic `SPIM` (4), version u8, header_len u8, flags u16, width u16, height u16, pixel_format u8, palette_id u8, reserved u16 (must be 0), payload_len u32, crc32 u32. This settles the open 21-vs-24-byte inconsistency in the research.
- **D-09:** v1 values: version 1; header_len 24 (a reader skips `header_len - 24` extra bytes of a future minor extension but never reads past the buffer); pixel_format 1 = packed 4 bpp, high nibble first; palette_id 1 = Spectra 6 controller nibble codes (0 black, 1 white, 2 yellow, 3 red, 5 blue, 6 green). Palette is an id into a registry held in server and firmware constants, not RGB inside each image.
- **D-10:** flags bit 0 is reserved for future compression and must be 0 in v1; a reader rejects any unknown flag bit. No compression in v1.
- **D-11:** payload_len must equal `ceil(width*height*bpp/8)` and the whole body length must equal `header_len + payload_len`. crc32 is `zlib.crc32` of the payload only (cheap integrity check on top of the SHA-256 of the whole file that the device already verifies).

### Reader scope (delegated)
- **D-12:** The reader is a new pure C module with no ESP-IDF dependency under `firmware/main/`, with a host test discovered by the existing `firmware/tests/run_host_tests.sh` naming convention. It takes the received bytes and the panel width/height and returns a validated view (payload pointer, length, palette id) or a distinct error code; it never receives or writes a display buffer, so validation precedes any buffer access by construction.
- **D-13:** The reader accepts a body of exactly `width*height/2` bytes with no `SPIM` magic as legacy raw (960,000 for 1200x1600). A body that starts with `SPIM` is never treated as legacy.
- **D-14:** The reader is not wired into `api_client.c`'s download path in this phase. Wiring, together with the build and OTA, belongs to Phase 57, so the firmware that ships to the live frame is untouched here.
- **D-15:** The server-side decoder (Python) and the C reader are tested against the same committed golden fixtures (valid v1, legacy raw, and one fixture per rejection class).

### Hash, URL and cut-over (delegated)
- **D-16:** The advertised `image_hash` and the content-addressed `/img/<sha256>.bin` path keep their meaning: SHA-256 over the exact bytes served, header included. A format change for a frame therefore changes its hash, costing that frame one extra full refresh once, accepted.
- **D-17:** Canonical server artifact stays the pixel buffer; the container is a per-response encoding. The legacy path is not refactored: the code that serves a non-announcing frame is behaviour-preserving, proven by a byte-for-byte regression test of the display response and the served image against pre-change output.
- **D-18 (amended after research):** Negotiation lives in the BYOS (`stub-server/byos_server.py`). Research found the BYOS already imports `server` modules, so the container encoder is a single module in `server/` imported by the BYOS rather than duplicated; no drift test is needed. If the import turns out to be unusable at deploy time, fall back to a duplicated encoder pinned by a behaviour test.
- **D-19:** An announced version above the server's maximum gets the server's highest supported version; non-numeric, empty, zero or oversized (more than 3 digits) values get legacy raw.
- **D-20:** Payload length is `ceil(width*height/2)` (identical to `width*height/2` for even pixel counts).
- **D-21:** The written spec lives in a new `docs/IMAGE-FORMAT.md` (the upstream protocol doc was never vendored), referenced from `stub-server/README.md`.

### Claude's Discretion
- Module and test names, error-code naming, fixture file layout, and where the written spec lives (alongside the existing protocol documentation), provided the spec states D-08 to D-13 exactly.
- Whether the dual-served image files for an announcing frame share the `IMG_KEEP` pruning window (default: yes).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and requirements
- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 50 goal and success criteria
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — IMG-01, IMG-02, IMG-03
- `.planning/workstreams/v1-2/STATE.md` — workstream state; edit only Phase 50 lines

### Research
- `.planning/workstreams/v1-2/research/STACK.md` — "Image format (common, versioned)" section (header table; layout superseded by D-08)
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md` §4.4 — negotiation, hash and cut-over
- `.planning/workstreams/v1-2/research/PITFALLS.md` C12 — breaking deployed frames; golden fixtures, validation order, ordering with OTA
- `.planning/workstreams/v1-2/research/SUMMARY.md` — decisions 9 and 10

### Prior phases
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md` — freeze test and fleet constraints
- `.planning/workstreams/v1-2/phases/49-per-hardware-ota-registry/` — registry rules that must not be touched

### Code
- `server/panel_format.py` — current raw format, nibble codes, 960,000 constants
- `stub-server/byos_server.py` — display poll, `_publish_image`, `/img/<sha>.bin`
- `stub-server/make_test_panel.py` — duplicated wire-format constants (PROTOCOL.md is tiebreaker)
- `firmware/main/api_client.c`, `firmware/main/api_client.h` — `FP_IMAGE_BYTES` gate and hash check (read-only this phase)
- `firmware/tests/run_host_tests.sh` — host test discovery convention
- `CLAUDE.md` (`.claude/CLAUDE.md`) — conventions: stdlib + Pillow + requests, comment-history guard, 80-line function gate, ruff, mypy

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/panel_format.py`: legacy raw encoder and palette codes; becomes the legacy encoder the container wraps.
- `firmware/tests/run_host_tests.sh`: auto-discovers `test_<name>.c` against `main/<name>.c`, with `HOST_TEST_DEPS` for extras.
- Existing BYOS content-addressed image publishing and pruning.

### Established Patterns
- BYOS duplicates helpers instead of importing `server/` (drift guarded by tests).
- Behaviour-over-source tests; golden binary fixtures.
- Per-request headers (`X-Fw-Version`, `X-Battery-Mv`) parsed leniently, malformed treated as absent.

### Integration Points
- Display handler in `byos_server.py` (image read, size gate, digest, publish, JSON reply) is the only server touch point.
- Firmware reader is standalone and not linked into the production build in this phase.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the owner-fixed decisions; open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

- Wiring the reader into the download path and shipping it by OTA — Phase 57.
- Per-device image selection through the format layer — Phase 51.
- Non-Spectra palettes and non-1200x1600 geometry rendering — Phases 56 and 58 (palette registry already extensible by id).
- Compression — only if wake-energy data shows download dominates.

</deferred>

---

*Phase: 50-Common Image Format*
*Context gathered: 2026-10-30*
