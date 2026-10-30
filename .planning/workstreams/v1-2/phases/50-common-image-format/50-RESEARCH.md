# Phase 50: Common Image Format - Research

**Researched:** 2026-10-30
**Domain:** Versioned binary image container; header negotiation in a stdlib BYOS server; pure-C validating reader with host tests
**Confidence:** HIGH (all findings come from reading this repository; nothing depends on an external library)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01 (owner):** Common, versioned container; header carries width, height, palette, payload length and checksum.
- **D-02 (owner):** A frame that does not announce support receives its current raw 960,000-byte image byte for byte; only an announcing frame receives the container.
- **D-03 (owner):** The reference reader rejects bad magic, version, length or panel dimensions before touching a display buffer, and always accepts the legacy raw format. It is a host-tested firmware reader.
- **D-04 (owner):** Firmware stays in the ESP-IDF 5.3.1 build image; nothing is published or flashed in this phase.
- **D-05 (owner):** Nothing may change what the live frame receives, its state, its registry or its BYOS responses. The Phase 48 freeze test stays green. No production deploy.
- **D-06:** The frame announces support with an explicit request header `X-Img-Fmt: <n>` (highest container version it reads) on the display poll. The server never requires it. Absent, empty, malformed, zero or unknown values all mean legacy raw. The server picks the highest version it supports that is not above the announced one.
- **D-07:** The announcement is per request only. It is not persisted in device state, the registry or the fleet database, so the legacy frame's recorded state cannot change.
- **D-08:** Fixed 24-byte little-endian header, every field naturally aligned: magic `SPIM` (4), version u8, header_len u8, flags u16, width u16, height u16, pixel_format u8, palette_id u8, reserved u16 (must be 0), payload_len u32, crc32 u32.
- **D-09:** v1 values: version 1; header_len 24 (a reader skips `header_len - 24` extra bytes of a future minor extension but never reads past the buffer); pixel_format 1 = packed 4 bpp, high nibble first; palette_id 1 = Spectra 6 controller nibble codes (0 black, 1 white, 2 yellow, 3 red, 5 blue, 6 green). Palette is an id into a registry held in server and firmware constants, not RGB inside each image.
- **D-10:** flags bit 0 is reserved for future compression and must be 0 in v1; a reader rejects any unknown flag bit. No compression in v1.
- **D-11:** payload_len must equal `ceil(width*height*bpp/8)` and the whole body length must equal `header_len + payload_len`. crc32 is `zlib.crc32` of the payload only.
- **D-12:** The reader is a new pure C module with no ESP-IDF dependency under `firmware/main/`, with a host test discovered by the existing `firmware/tests/run_host_tests.sh` naming convention. It takes the received bytes and the panel width/height and returns a validated view (payload pointer, length, palette id) or a distinct error code; it never receives or writes a display buffer.
- **D-13:** The reader accepts a body of exactly `width*height/2` bytes with no `SPIM` magic as legacy raw (960,000 for 1200x1600). A body that starts with `SPIM` is never treated as legacy.
- **D-14:** The reader is not wired into `api_client.c`'s download path in this phase. Wiring, build and OTA belong to Phase 57.
- **D-15:** The server-side decoder (Python) and the C reader are tested against the same committed golden fixtures (valid v1, legacy raw, and one fixture per rejection class).
- **D-16:** The advertised `image_hash` and the content-addressed `/img/<sha256>.bin` path keep their meaning: SHA-256 over the exact bytes served, header included. A format change for a frame changes its hash (one extra full refresh once, accepted).
- **D-17:** Canonical server artifact stays the pixel buffer; the container is a per-response encoding. The legacy path is not refactored: it is behaviour-preserving, proven by a byte-for-byte regression test of the display response and the served image against pre-change output.
- **D-18:** Negotiation lives in the BYOS (`stub-server/byos_server.py`, stdlib only). The container encode/decode helpers follow the duplicate-and-pin pattern, with a test that fails if the two copies drift.

### Claude's Discretion
- Module and test names, error-code naming, fixture file layout, and where the written spec lives (alongside the existing protocol documentation), provided the spec states D-08 to D-13 exactly.
- Whether the dual-served image files for an announcing frame share the `IMG_KEEP` pruning window (default: yes).

### Deferred Ideas (OUT OF SCOPE)
- Wiring the reader into the download path and shipping it by OTA (Phase 57).
- Per-device image selection through the format layer (Phase 51).
- Non-Spectra palettes and non-1200x1600 geometry rendering (Phases 56 and 58).
- Compression.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| IMG-01 | Common versioned format whose header carries width, height and palette, specified with golden fixtures | Header table and `struct` format below; spec location finding (no in-repo protocol doc exists); small golden fixtures plus a deterministic full-size case; Python + C both read the same fixture directory |
| IMG-02 | Server serves new format only to announcing frames; existing frames keep byte-identical raw image | Display-handler insertion point (single branch after the size gate), strict header parser, byte-identity test design, freeze-test interaction, `do_GET` size headroom |
| IMG-03 | Firmware reader validates magic, version, length, panel dimensions before touching the display buffer, accepts legacy | New `firmware/main/image_container.[ch]`, validation order, overflow-safe arithmetic, host test via `run_host_tests.sh`, CMake `SRC_DIRS` caveat |
</phase_requirements>

## Summary

The phase is small and self-contained: one new Python module with encode/decode, one narrow branch in the BYOS display handler, one new pure-C module with a host test, a spec document, and a directory of small golden fixtures read by both languages. Every integration point already exists and has an established test pattern in the repo (the `FrameServer` subprocess harness, the Phase 48 freeze test, `run_host_tests.sh` auto-discovery).

Three findings the planner must act on, none of which contradict a locked decision:

1. **There is no in-repo protocol document.** Code comments cite `docs/PROTOCOL.md` section 1 to 3, but that file is the upstream flightportrait doc and was never vendored (`docs/` holds only `panel-preview.png`; `git log` shows no deletion). The spec therefore needs a new file. Recommend `docs/IMAGE-FORMAT.md`, and a one-line pointer from `stub-server/README.md`. Do not create `docs/PROTOCOL.md`.
2. **`firmware/main/CMakeLists.txt` uses `SRC_DIRS "."`**, so any new `.c` file in `firmware/main/` is compiled into the production firmware automatically. D-12 and D-14 are still satisfiable (nothing calls the module, so it is not linked in practice, and nothing is built or flashed this phase), but the "firmware untouched" claim is not literally true for the build. The module must compile cleanly under the IDF toolchain and the CI `build` job will exercise that.
3. **D-18's premise is partly out of date.** `byos_server.py` already does `from server import device_policy, firmware_registry, fleet_db, hardware, state_store` (line 83). Only `panel_format` constants (`IMAGE_BYTES`) are duplicated. Duplicate-and-pin is still workable and is what D-18 locks; see Open Question 1 for the cheaper alternative the owner may prefer.

**Primary recommendation:** Add `server/image_container.py` (typed, canonical, added to the mypy list), a ~30-line duplicated encoder in the BYOS gated by a strict `parse_img_fmt()`, `firmware/main/image_container.[ch]` plus `firmware/tests/test_image_container.c`, and `docs/IMAGE-FORMAT.md`. Drive Python and C from one `firmware/tests/fixtures/image_container/` directory. Add no new keys to the display JSON and no new state writes.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Announce container support (`X-Img-Fmt`) | Device (firmware, later phase) | — | Only the device knows what it can parse; this phase only defines the header |
| Negotiation and per-response encoding | API / Backend (BYOS) | — | Server picks version per request; canonical artifact stays the pixel buffer |
| Container encode/decode reference | API / Backend (`server/`) | BYOS duplicate | Pure functions; spec reference implementation |
| Container validation before display | Device (C reader) | — | Must precede any display-buffer access; host-tested only here |
| Content-addressed storage and hash | API / Backend (BYOS `img/`) | — | Hash is over served bytes; `/img` stays unauthenticated and content-addressed |
| Legacy compatibility | API / Backend | Device | Server serves raw to non-announcers; reader accepts raw by length |

## Standard Stack

No new dependencies. Python stdlib only for the container (`struct`, `zlib`, `hashlib`); C11 with `<stdint.h>`, `<stddef.h>`, no libc beyond that.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `struct` (stdlib) | Python 3.13 locally, 3.14 on VPS | Pack/unpack the 24-byte header with `"<4sBBHHHBBHII"` | `struct.calcsize` of that format is 24 [VERIFIED: ran `struct.calcsize` in this session]. Little-endian `<` means no padding, matching an ESP32-S3 C struct |
| `zlib.crc32` (stdlib) | — | Payload checksum (D-11) | Locked decision |
| `hashlib.sha256` (stdlib) | — | `image_hash` over served bytes (D-16) | Already used at `byos_server.py:1241` |
| C11, `cc` | system cc (`/usr/bin/cc`, gcc and clang present) | Reader and host test | `run_host_tests.sh` compiles with `cc -Wall -Wextra -std=c11` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Own bitwise CRC-32 in C | `esp_rom_crc32_le` | ESP-ROM call breaks the "no ESP-IDF dependency" rule (D-12). Write a table-free reflected CRC-32 (poly `0xEDB88320`, init and xorout `0xFFFFFFFF`); verify against the Python fixtures |
| STACK.md struct string `<4sBBHHHBBBBII` | D-08 layout | STACK.md's layout is superseded by D-08 (u16 flags, u16 reserved). Correct format is `<4sBBHHHBBHII` |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed by this phase. Nothing to audit; slopcheck not needed.

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
Frame poll: GET /device/v1/display  (+ optional X-Img-Fmt: n)
        |
        v
  bearer_ok? --no--> 401 (unchanged)
        |
        v
  read self.args.image (raw 960000 B pixel buffer) --size gate--> 503 (unchanged)
        |
        v
  parse_img_fmt(header) ----> None (absent/empty/malformed/0/unknown)  -> served = image (raw)
        |                       |
        |                       +-> n >= 1 -> version = min(n, SUPPORTED_MAX)
        |                                     served = encode_container(image, ...)
        v
  digest = sha256(served)  -> _publish_image(state_dir, digest, served)  -> img/<digest>.bin
        |
        v
  JSON reply: image_url=/img/<digest>.bin, image_hash=sha256:<digest>, sleep_s, firmware, ...
  (same keys as today; NO new key; no state write for X-Img-Fmt)
        |
        v
  Frame: GET /img/<digest>.bin  -> served bytes
        |
        v   (Phase 57 wiring, not this phase)
  C reader: image_container_parse(body, len, panel_w, panel_h) -> view or error code
        (container: validate header -> lengths -> dims -> crc; legacy: len == w*h/2)
        |
        v
  caller copies view.payload into the display buffer
```

### Recommended Project Structure
```
docs/IMAGE-FORMAT.md                         # the written spec (IMG-01)
server/image_container.py                    # canonical encode/decode, typed, in mypy list
stub-server/byos_server.py                   # parse_img_fmt + duplicated encode, one branch in do_GET
firmware/main/image_container.h/.c           # pure C reader (IMG-03)
firmware/tests/test_image_container.c        # host test, auto-discovered
firmware/tests/fixtures/image_container/     # golden *.bin + manifest (shared by C and Python)
server/test_image_container.py               # decoder/encoder vs fixtures, rejection classes
stub-server/test_image_negotiation.py        # FrameServer: legacy byte identity, announce, junk values
stub-server/test_image_container_pin.py      # BYOS copy vs server copy drift pin
```

Fixture location: put fixtures where both suites can reach them. The C test needs a path; `run_host_tests.sh` compiles to a temp dir and runs the binary with the caller's cwd, so the C test cannot rely on a relative path. Two workable options: (a) C test takes the fixture directory from `argv[1]` or an env var that the script passes, requiring a small additive change to `run_host_tests.sh`; (b) embed the fixtures as C byte arrays generated from the `.bin` files and verified against them by a Python test. Option (b) needs no script change but duplicates data. Recommended: (a), with the script exporting `FIXTURE_DIR="${SCRIPT_DIR}/fixtures"` before running each binary (one line, `set -u` safe), and the test failing loudly if the variable is unset or a file is unreadable (so a missing fixture is never a silent pass). [ASSUMED: that adding an exported variable to `run_host_tests.sh` is acceptable; it is additive and does not change discovery.]

### Header layout (D-08, byte offsets verified by arithmetic)

| Offset | Size | Field | v1 value |
|--------|------|-------|----------|
| 0 | 4 | magic | `53 50 49 4D` ("SPIM") |
| 4 | 1 | version | 1 |
| 5 | 1 | header_len | 24 |
| 6 | 2 | flags | 0 (bit 0 reserved for compression; any set bit rejected) |
| 8 | 2 | width | 1200 |
| 10 | 2 | height | 1600 |
| 12 | 1 | pixel_format | 1 |
| 13 | 1 | palette_id | 1 |
| 14 | 2 | reserved | 0 (nonzero rejected) |
| 16 | 4 | payload_len | 960000 |
| 20 | 4 | crc32 | `zlib.crc32(payload)` |

Python: `struct.pack("<4sBBHHHBBHII", b"SPIM", 1, 24, 0, w, h, 1, 1, 0, plen, crc)`.

### Pattern 1: Reader validation order (no buffer access before success)
**What:** Validate in this order and return a distinct code at each step: null/short input; magic; (if magic matches) header_len >= 24 and header_len <= len; version; flags; reserved; pixel_format and palette_id known; width/height equal the panel's; payload_len equals `ceil(w*h*4/8)` computed in 64-bit; `len == header_len + payload_len` computed in 64-bit; CRC-32 over the payload. Only then fill the view. If the magic does not match, take the legacy branch: accept iff `len == (uint64_t)w*h/2` (with the odd-pixel caveat in Pitfalls), otherwise return a bad-magic or bad-length code.
**When to use:** always; this is the D-03 contract.
**Example:**
```c
typedef enum {
    IMGC_OK = 0, IMGC_LEGACY_OK, IMGC_ERR_ARG, IMGC_ERR_TRUNCATED,
    IMGC_ERR_MAGIC, IMGC_ERR_HEADER_LEN, IMGC_ERR_VERSION, IMGC_ERR_FLAGS,
    IMGC_ERR_RESERVED, IMGC_ERR_FORMAT, IMGC_ERR_PALETTE, IMGC_ERR_DIMENSIONS,
    IMGC_ERR_LENGTH, IMGC_ERR_CRC,
} imgc_status_t;

typedef struct { const uint8_t *payload; uint32_t payload_len; uint8_t palette_id; bool legacy; } imgc_view_t;

imgc_status_t imgc_parse(const uint8_t *body, size_t len,
                         uint16_t panel_w, uint16_t panel_h, imgc_view_t *out);
```
Names are discretionary (CONTEXT). Zero `*out` on every failure so a caller that ignores the status cannot use a stale pointer. Use `memcpy`/byte shifts for field reads, not a packed-struct cast, so alignment and endianness never matter on the host.

### Pattern 2: Strict, lenient-failing header parse in the BYOS
Follow `parse_battery_mv` (`byos_server.py:716`): `isinstance(raw, str)`, length 1 to 3, every char in `"0123456789"` (so no sign, space or Unicode digits; `str.isdigit` accepts non-ASCII digits and must not be used), then `int`. `0` and any value below the lowest supported version means legacy. Cap by the server's highest supported version (`min(n, SUPPORTED_MAX)`). Never raise, never log the raw value.

### Pattern 3: Single insertion in the display handler
Today (`byos_server.py:1234-1245`): read file, `len(image) != IMAGE_BYTES` gate, `digest = sha256(image)`, `_publish_image(..., image)`. Insert exactly one line between the gate and the digest: `served = image if version is None else encode_container(image, version)`, then use `served` for the digest and the publish, in place of `image`. For a non-announcing frame `served is image`, so the digest, the published file and the response are the same bytes as before. `_publish_image`, `_prune_images`, the `/img/<sha>.bin` route and `_atomic_write` need no change: they are content-addressed over arbitrary bytes, and `_IMG_NAME_RE` matches any 64-hex name.

`Handler.do_GET` is currently 63 code lines against a gate of 80 (`scripts/check_function_size.py report`). The new code must stay within about 15 lines or move into a helper (for example `_select_served_image(self, image)`), otherwise CI's `check --max 80 server stub-server` fails.

### Anti-Patterns to Avoid
- **Refactoring the legacy path.** D-17 forbids it. Do not move the existing digest/publish code into a shared helper; branch around it.
- **Persisting the announcement.** No write of `X-Img-Fmt` to `byos_state.json`, `device_report.json`, `battery_state.json`, `devices.json` or fleet.db (D-07). The freeze test `test_telemetry_headers_reach_exactly_the_frozen_places` only probes the headers in `PROBE_HEADERS`; add `X-Img-Fmt` to the new negotiation test's own probe of effects instead of editing the freeze file.
- **Adding a JSON key to the display reply** (for example `image_format`). The freeze list pins the exact key set (`display_response_keys`); the container is self-identifying by magic. Adding a key for announcing frames only would pass the freeze test but widens the wire contract for no benefit.
- **Importing the C reader into `api_client.c` or listing it in a header the production code includes.** D-14.
- **Fixtures only in one language.** D-15 requires both readers to consume the same files.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Header pack/unpack in Python | Manual byte slicing | `struct` with `"<4sBBHHHBBHII"` | One format string is the spec |
| CRC-32 in Python | A table | `zlib.crc32` | Locked by D-11 |
| Atomic image publish | New writer | Existing `_publish_image` / `_atomic_write` | Already fsync + replace + prune |
| Header leniency | New parsing style | `parse_battery_mv` shape | Consistent, fuzz-safe |
| Test harness | New server launcher | `test-support/skypane_frame_server.py` `FrameServer` | Boots real byos with state dir, loopback only |
| Seeded live-like state | Hand-built dirs | `test-support/skypane_live_state.py` `seed_live_like_state` | Used by the freeze test |

**Key insight:** CRC-32 in C is the one thing that has no library on the host and must not use ESP-ROM; it is 10 lines, and the golden fixtures are the proof it matches `zlib.crc32` (include a fixture with a known multi-byte payload, plus the well-known check value `crc32(b"123456789") == 0xCBF43926`).

## Runtime State Inventory

Not a rename or migration phase. Omitted deliberately. The relevant "do not touch" inventory for D-05: the live frame's `devices.json`, `byos_state.json`, `device_config.json`, `firmware/registry.json`, `firmware/device_report.json`, `battery_state.json`, `panel.bin` and `img/` contents are all read-only inputs to this phase's tests; tests use `tmp_path` state dirs only.

## Common Pitfalls

### Pitfall 1: A new C file is compiled into production firmware
**What goes wrong:** `firmware/main/CMakeLists.txt` is `SRC_DIRS "."`, so `image_container.c` is built into the image. A warning-as-error or a symbol clash would break the CI `build` job; the binary changes (object added, though unreferenced code is normally dropped by `--gc-sections`).
**How to avoid:** Keep the module free of libc beyond `<stdint.h>/<stddef.h>/<stdbool.h>`/`memcpy`, prefix all symbols (`imgc_`), build with the same warning flags as the host test, and run `firmware/build.sh` (needs Docker, which is present at `/usr/bin/docker`) or at least let CI's `build` job prove it. State in the plan that the shipped binary is not flashed or published and that Phase 57 owns linking it. Do not edit `CMakeLists.txt`.
**Warning signs:** CI `build` job fails on a warning in the new file; link map shows `imgc_` symbols (it should not).

### Pitfall 2: Integer overflow in length arithmetic
**What goes wrong:** `width*height` with `uint16_t` operands promotes to `int` (65535*65535 overflows 32-bit signed); `header_len + payload_len` with `uint32_t` can wrap so an attacker-sized `payload_len` appears valid.
**How to avoid:** Cast to `uint64_t` before multiplying and adding; compare `len` as `uint64_t`; reject `payload_len > len - header_len` before any pointer arithmetic. Include fixtures or in-test crafted buffers with `payload_len = 0xFFFFFFFF` and `header_len` past the buffer.

### Pitfall 3: Odd pixel counts and "legacy = w*h/2"
**What goes wrong:** D-13 says legacy length is `width*height/2` and D-11 uses `ceil`. For an odd `w*h` they disagree by one byte.
**How to avoid:** For v1 the only shipped geometry is 1200x1600 (even). State in the spec that legacy length is `ceil(w*h/2)`, which equals `w*h/2` whenever the pixel count is even, and test an odd-count case (for example 3x3, 5 bytes, padding nibble 0) so the two never diverge. Pad nibble must be 0, and the reader does not check it (the CRC covers it).

### Pitfall 4: Legacy/container ambiguity
**What goes wrong:** A reader sniffing by length alone could mistake a container for legacy or vice versa.
**Why it cannot collide in v1:** A legal legacy image uses only nibble codes 0,1,2,3,5,6. `SPIM` begins `0x53 0x50 0x49 0x4D`, and `0x49` and `0x4D` contain nibbles 4 and 0xD, which are never legal codes, so no valid legacy image starts with `SPIM`. [VERIFIED: nibble set from `server/panel_format.py` constants BLACK..GREEN]. Also, a container is `24 + 960000` bytes, never 960000, so length differs. The reader rule (magic first, never legacy if magic present) is correct and needs no extra heuristics.

### Pitfall 5: Download buffer and length gate (Phase 57 hand-off, not this phase)
**What goes wrong:** `api_client.c` gates on `got == FP_IMAGE_BYTES` (lines 648-749) and the download buffer is exactly `FP_IMAGE_BYTES` (`state_machine.c:267`). A container body is 24 bytes longer, so wiring needs a larger buffer or header-first streaming, plus hashing over the full body (D-16). Record this in the spec's "adoption notes" and in the Phase 57 handoff; do not change `api_client.*` here (D-14).

### Pitfall 6: Pruning interplay once a container frame exists
**What goes wrong:** `IMG_KEEP = 8` is global. Announcing and legacy frames publish different digests for the same picture, so the store holds up to two files per picture. With one live frame plus tests this is harmless; with many announcing frames it halves the window (this is the already-noted global-store problem solved in Phase 51).
**How to avoid:** Default per CONTEXT: shared window. Add a test that an announcing poll followed by a legacy poll leaves both URLs fetchable.

### Pitfall 7: Existing tests that assume raw 960000 body for any poll
**What goes wrong:** Tests reusing `FrameServer.display` with extra headers are unaffected unless they send `X-Img-Fmt`, which none do. Low risk, but a "junk value" test must assert the body is still exactly 960000 bytes.

### Pitfall 8: Comment-history guard and function-size gate
**How to avoid:** No plan/phase/decision IDs (D-xx, IMG-xx, "Phase 50") in code comments, docstrings, or test docstrings; they live in git and `.planning/`. `python3 scripts/check_comment_history.py check` currently exits 0, so any new violation is a regression. Keep functions under 80 code lines (`do_GET` headroom above). Note the C tests also should not cite IDs.

## Code Examples

### Python canonical encode/decode (sketch)
```python
# server/image_container.py - typed; add to pyproject [tool.mypy] files and overrides.
import struct
import zlib

MAGIC = b"SPIM"
HEADER_FORMAT = "<4sBBHHHBBHII"
HEADER_LEN = struct.calcsize(HEADER_FORMAT)  # 24
VERSION_1 = 1
PIXEL_FORMAT_NIBBLE = 1
PALETTE_SPECTRA6 = 1


def encode_container(pixels: bytes, width: int, height: int, *, version: int = VERSION_1) -> bytes:
    payload_len = (width * height + 1) // 2
    if len(pixels) != payload_len:
        raise ValueError("pixels length does not match width*height")
    header = struct.pack(HEADER_FORMAT, MAGIC, version, HEADER_LEN, 0, width, height,
                         PIXEL_FORMAT_NIBBLE, PALETTE_SPECTRA6, 0, payload_len,
                         zlib.crc32(pixels))
    return header + pixels
```
`decode_container(body, panel_w, panel_h)` mirrors the C reader and raises `ValueError` whose text starts with the failing field name (the convention in `server/firmware_image.py`). The Python decoder and the C reader must return the same rejection class for every fixture; keep a shared manifest (`manifest.json`: file name, expected class name, expected width/height/palette) read by both tests.

### Golden fixture set (small, committed)
Keep committed fixtures tiny so the repo does not grow by megabytes: use a small panel (for example 8x4, 16 byte payload) for every class, passing the panel size explicitly to the reader.
- `valid_v1_8x4.bin`, `legacy_8x4.bin` (16 raw bytes, no magic)
- Rejections: `bad_magic`, `bad_version` (2), `bad_header_len_short` (<24), `bad_header_len_past_buffer`, `bad_flags` (bit 0), `bad_flags_unknown_bit`, `bad_reserved`, `bad_pixel_format`, `bad_palette`, `bad_dimensions` (valid container for another size), `bad_payload_len`, `bad_total_length_short`, `bad_total_length_long`, `bad_crc`, `truncated_header`, `empty`.
- `valid_v1_extended_header_8x4.bin`: header_len 28, four extra bytes, proving the skip rule (D-09).
- Full-size case without a 960 KB file: a deterministic generated pattern (for example byte `i*7 & 0xFF` masked to legal nibbles) whose container CRC and SHA-256 are committed as constants in the manifest; the Python test regenerates it and compares, and the C test regenerates the same pattern in a loop, wraps it in a header built by the test, and checks the legacy length gate at exactly 960,000 and the container at 960,024. This covers the real 1200x1600 sizes at zero repo cost.
Generate the fixtures with a small script that the test also uses to assert the committed bytes still equal the generator's output, so the fixtures cannot silently rot (behaviour-over-source: the assertion is on bytes, not source text). There is precedent for committed binary and text fixtures (`server/fixtures/`, `hardware/fixtures/`), but none for binary golden images; a README next to the fixtures should state how they were produced.

### Byte-identity regression for the legacy path (IMG-02, D-17)
Existing coverage: `test_phase47_freeze.py` proves the response keys and values and that `image_hash_is_sha256_of_served_image`, and replays a poll across the fleet migration. It compares code against itself across a migration, not against pre-change output. Add, in `stub-server/test_image_negotiation.py`:
1. Seed a state dir, write a deterministic 960,000-byte `panel.bin`, poll with no `X-Img-Fmt` and with `POLL_HEADERS`; assert the body fetched from `image_url` equals the file bytes exactly, `image_hash == "sha256:" + sha256(file)`, and the JSON key set equals `FREEZE["display_response_keys"]["keys"]`.
2. Capture the pre-change reference once, before editing `byos_server.py` (task ordering matters): the normalised display response and the SHA-256 of the served bytes for that deterministic panel, committed as a constant in the test. This is the "against pre-change output" proof. Do it as the first task so the constant comes from unmodified code.
3. Parametrise junk values (`""`, `"0"`, `"-1"`, `"01x"`, `" 1"`, `"1 "`, `"+1"`, `"١"` (non-ASCII digit), `"999"`, 100-character string, `"1,2"`, `"abc"`): the assertion for the non-supported-looking ones is raw 960,000 bytes and the same hash as the no-header poll. `"999"` is a special case: per D-06 "unknown" means legacy, but the server also picks the highest supported version not above the announced one. 999 is above, so the rule yields the highest supported (1) and the frame receives a container. Resolve this explicitly (Open Question 2) and test whichever is chosen.
4. Announce `"1"`: body length 960,024, starts with `SPIM`, `decode_container` accepts it, payload equals the panel bytes, `image_hash` equals SHA-256 of the container, and the file is fetchable at `image_url`.
5. After announcing and legacy polls on one state dir, assert `byos_state.json`, `devices.json`, `device_config.json`, `battery_state.json` and `firmware/device_report.json` hashes are identical to a baseline poll without the header (D-07 effect check, in the style of `probe_effects` in the freeze test).

### How the duplicated-helper pattern is guarded today
Two styles exist. Newer code imports the shared object and asserts identity (`test_poll_cycle.py` ~line 290: `assert byos_module._HHMM_RE is device_policy.HHMM_RE`). Genuinely duplicated constants (`IMAGE_BYTES` in `byos_server.py:85`, `make_test_panel.py`, `panel_format.py`) rely on equality asserts and the doc-as-tiebreaker comment; the byte-for-byte source-text drift guard was replaced by behaviour checks. For D-18 use a behaviour pin: load the BYOS module with the same `load_byos_module()` helper (importlib, as `test_poll_cycle.py`'s `byos_module` fixture and `test_phase47_freeze.py` do), then assert (a) its constants (`MAGIC`, `HEADER_LEN`, supported versions, palette id) equal `server.image_container`'s, and (b) for every fixture and a randomised set of dimensions and payloads, `byos_module.<encode>(...) == server.image_container.encode_container(...)`. This follows the repo's behaviour-over-source rule; do not assert on source text (the `companion/test_suite_guards.py` rule applies to companion tests, but the repo convention is the same).

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Headerless raw 960,000 bytes | Versioned `SPIM` container, negotiated | This phase | Raw stays for non-announcers |
| STACK.md 21/24-byte layout with u8 flags | D-08 24-byte layout with u16 flags and u16 reserved | CONTEXT 2026-10-30 | Use D-08 only |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Adding an exported `FIXTURE_DIR` to `run_host_tests.sh` is acceptable (additive, discovery unchanged) | Project structure | Low; alternative is embedding fixtures as C arrays |
| A2 | `docs/IMAGE-FORMAT.md` is an acceptable home for the spec given no in-repo protocol doc exists | Summary | Low; CONTEXT says "alongside existing protocol documentation" which does not exist, owner may prefer `stub-server/README.md` |
| A3 | The IDF build for the CI `build` job compiles an unreferenced `image_container.c` without new warnings-as-errors | Pitfall 1 | Medium; unverified because Docker build was not run in this session |
| A4 | Bitwise CRC-32 over ~960 KB is cheap enough on ESP32-S3 for Phase 57 | Key insight | Low here (not wired); Phase 57 should measure or use a 1 KB table |

## Open Questions

1. **D-18 versus importing.**
   - What we know: `byos_server.py` already imports `server.device_policy`, `firmware_registry`, `fleet_db`, `hardware`, `state_store`; the VPS deploy therefore already ships `server/` next to `stub-server/`. D-18 says the BYOS "duplicates rather than imports" `server/` helpers, which is only true for a few constants.
   - What's unclear: whether the owner wants the duplicate anyway.
   - Recommendation: honour D-18 as locked (duplicate the ~25-line encoder, add the behaviour pin). Flag to the owner that a plain `from server import image_container` would remove the drift risk and the pin test. Low cost to switch if approved before planning.
2. **Announced version above what the server supports (e.g. `X-Img-Fmt: 2` or `999`).** D-06 says "unknown values all mean legacy raw" and also "server picks the highest version it supports that is not above the announced one". Read together, announced values above the server's maximum should yield the server's highest (a v2-capable frame can read v1), while garbage (non-digits) yields legacy. That is the interpretation in this research; if instead "unknown" meant "greater than SUPPORTED_MAX", a future firmware announcing 2 would be stuck on raw until the server upgrades, which is backwards. Confirm in planning; the test in section Code Examples item 3 pins the choice.
3. **Hash/cut-over for the live frame.** Out of scope (no firmware wiring), but the spec should say a frame switching format sees one hash change and one extra refresh (D-16).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `cc` (gcc/clang) | Firmware host tests | yes | `/usr/bin/cc` | — |
| python3 | Server tests | yes | 3.13.17 (VPS runs 3.14) | — |
| `server/.venv` with pytest, ruff, mypy | Test, lint, type gates | yes (5 of pytest/ruff/mypy-related binaries present) | — | — |
| Docker | Optional `firmware/build.sh` compile check | yes | `/usr/bin/docker` | CI `build` job |

No blocking gaps. Network is not needed (the pytest-socket guard allows loopback only; `FrameServer` uses loopback).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 with xdist and cov; C host tests via `cc` and `assert.h` |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`); `firmware/tests/run_host_tests.sh` |
| Quick run command | `server/.venv/bin/python -m pytest server/test_image_container.py stub-server/test_image_negotiation.py stub-server/test_image_container_pin.py stub-server/test_phase47_freeze.py -x --cov-fail-under=0` and `./firmware/tests/run_host_tests.sh` |
| Full suite command | `./scripts/run-all-tests.sh` (coverage floor 93) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| IMG-01 | Encoder output equals committed golden bytes; decoder accepts valid, rejects every class with the manifest's class | unit | `pytest server/test_image_container.py` | Wave 0 |
| IMG-01 | Spec states D-08 to D-13 values; spec offsets equal `struct` layout | unit (parses the served doc text only for its field table, or asserts via the constants; keep behaviour-first) | `pytest server/test_image_container.py::test_header_layout` | Wave 0 |
| IMG-02 | No header and junk headers give raw 960,000 bytes, same hash as pre-change reference | integration (FrameServer) | `pytest stub-server/test_image_negotiation.py -k legacy` | Wave 0 |
| IMG-02 | `X-Img-Fmt: 1` gives container, hash over container, file fetchable, no new JSON key, no state-file change | integration | `pytest stub-server/test_image_negotiation.py -k announce` | Wave 0 |
| IMG-02 | Phase 48 freeze still green | integration | `pytest stub-server/test_phase47_freeze.py` | exists |
| IMG-02 | BYOS copy equals canonical copy | unit | `pytest stub-server/test_image_container_pin.py` | Wave 0 |
| IMG-03 | C reader returns the manifest's code for every fixture, accepts legacy, never reads past buffer | host C test | `./firmware/tests/run_host_tests.sh` | Wave 0 |
| IMG-03 | CRC-32 implementation matches `zlib.crc32` (check value `0xCBF43926`) | host C test | same | Wave 0 |

Also run sanitizers once during development: `cc -fsanitize=address,undefined -std=c11 ...` on the test, with fixtures placed in exactly-sized heap buffers, to catch over-reads (the plain script does not use sanitizers; optionally add a second invocation with `CC` override, which the script already honours).

### Sampling Rate
- **Per task commit:** the quick command for the touched side, plus `python3 scripts/check_comment_history.py check` and `python3 scripts/check_function_size.py check --max 80 server stub-server`.
- **Per wave merge:** `./scripts/run-all-tests.sh`, `./firmware/tests/run_host_tests.sh`, `ruff check .`, `mypy` (from `pyproject.toml`).
- **Phase gate:** full suite green, firmware workflow green (`host-tests` and `build` jobs), freeze test green.

### Wave 0 Gaps
- [ ] `server/image_container.py` and its entry in both `[tool.mypy] files` and the strict-override `module` list (`server.image_container`)
- [ ] `server/test_image_container.py`, `stub-server/test_image_negotiation.py`, `stub-server/test_image_container_pin.py`
- [ ] `firmware/main/image_container.[ch]`, `firmware/tests/test_image_container.c`, fixtures directory with manifest and generator
- [ ] Capture pre-change reference constants from unmodified `byos_server.py` before the handler edit
- [ ] A short entry in `firmware/VENDOR.md` "Original To This Repository" for the new files (the file is the provenance record; no script enforces it, but every other original file is listed)

CI wiring: `firmware.yml` triggers on `firmware/**` and runs `./firmware/tests/run_host_tests.sh`, so the new C test runs there with no workflow change. Fixtures under `firmware/tests/fixtures/` are also within that path filter. The Python side runs in `ci.yml` through `run-all-tests.sh`; check `ci.yml`'s path filters include `firmware/tests/fixtures/**` if the Python tests read them from there (a fixture-only change should still trigger Python CI). [ASSUMED: ci.yml path filters were not inspected in full.]

Coverage: the coverage source is `server`, `stub-server`, `companion`, `deploy/backup`; the new module and the new BYOS branch are exercised by the subprocess tests (`patch = ["subprocess"]`), so the 93 floor should not move. A new always-covered module with all rejection classes tested will raise it slightly; the floor ratchets only upward by explicit edit, which is not required here.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (unchanged; bearer gate precedes everything) | existing `bearer_ok` |
| V3 Session Management | no | — |
| V4 Access Control | no | `/img` stays unauthenticated and content-addressed (unchanged) |
| V5 Input Validation | yes | Strict ASCII-digit parse of `X-Img-Fmt`; length-bounded; reader validates every header field and uses 64-bit arithmetic |
| V6 Cryptography | no new crypto | SHA-256 over served bytes (existing); CRC-32 is integrity against corruption only, not authenticity, and the spec must say so |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hostile or corrupted body overruns the display buffer | Tampering | Validate-then-view reader; reader never receives the display buffer; 64-bit length checks; exact total length equality |
| Integer overflow in length fields | Tampering | `uint64_t` arithmetic; reject `payload_len > len - header_len` first |
| `header_len` pointing past the buffer | Tampering | Reject `header_len < 24` or `> len` before skipping |
| Header injection or junk `X-Img-Fmt` causing 500 or state write | Denial / Tampering | Parser never raises; no persistence; test with junk matrix |
| Decompression bomb (future) | Denial | Flag bit 0 rejected in v1 |
| Cache poisoning of content-addressed store | Tampering | Digest computed by the server from the bytes it serves; unchanged |

## Sources

### Primary (HIGH confidence, read in this session)
- `stub-server/byos_server.py` (display handler 1215-1292, `/img` route 1293-1306, `_publish_image`/`_prune_images` 659-710, `parse_battery_mv` 716, imports line 83)
- `server/panel_format.py`, `server/hardware.py` (palette/image_format fields), `server/firmware_image.py` (error-text convention)
- `firmware/main/CMakeLists.txt` (`SRC_DIRS "."`), `firmware/main/api_client.h/.c` (`FP_IMAGE_BYTES` gate), `firmware/tests/run_host_tests.sh`, `firmware/tests/test_panel_guard.c`, `.github/workflows/firmware.yml`
- `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`, `stub-server/test_poll_cycle.py`, `test-support/skypane_frame_server.py`
- `pyproject.toml`, `scripts/run-all-tests.sh`, `scripts/check_function_size.py` (`report` output), `scripts/check_comment_history.py` (exit 0)
- `.planning/workstreams/v1-2/research/{STACK,ARCHITECTURE,PITFALLS}.md`, `phases/50-common-image-format/50-CONTEXT.md`

### Secondary / Tertiary
- None. No external sources were needed.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH, stdlib and system cc only
- Architecture: HIGH, single insertion point read directly
- Pitfalls: HIGH for repo-specific ones (CMake glob, function-size headroom, spec location); MEDIUM for A3 (IDF build not run)

**Research date:** 2026-10-30
**Valid until:** 2026-11-30 (stable; revisit if `byos_server.py` display handler changes in Phase 51)

## Project Constraints (from CLAUDE.md)
- Server code is Python stdlib + Pillow + requests only; the container module uses only stdlib.
- Code, comments, docs and commits in English; no plan, ticket, decision, review or phase IDs in comments (`scripts/check_comment_history.py check`, currently passing).
- Functions at most 80 code lines over `server`/`stub-server` (`Handler.do_GET` at 63).
- Tests assert behaviour (served bytes, running server), never source text or `.planning/`.
- New typed server modules go on the mypy list in `pyproject.toml`.
- Coverage gate at the measured floor (93); ruff clean.
- Firmware: ESP-IDF 5.3.1 in the `espressif/idf:v5.3.1` container; Apache-2.0 headers on new C files (match the SPDX header of existing files).
- No production deploy; GSD workflow entry (`/gsd-execute-phase`) before file edits.
