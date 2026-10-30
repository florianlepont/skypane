---
phase: 50-common-image-format
verified: 2026-10-30T00:00:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Build firmware in the espressif/idf:v5.3.1 container (firmware/build.sh)"
    expected: "Build succeeds. main/CMakeLists.txt uses SRC_DIRS ".", so main/image_container.c is now compiled into the firmware although nothing calls it."
    why_human: "ESP-IDF Docker build cannot run in this sandbox"
  - test: "Run the companion Chromium/Playwright browser tests"
    expected: "Unchanged and green (phase touched nothing under companion/)"
    why_human: "Chromium not available in this sandbox"
---

# Phase 50: Common Image Format Verification Report

**Goal:** Images use one versioned container that any hardware type can carry, introduced without changing what existing frames receive.
**Status:** human_needed (all automated checks pass; two sandbox-only items remain)

## Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Written spec and golden fixtures define the container; encoder and decoder agree (IMG-01) | VERIFIED | docs/IMAGE-FORMAT.md matches server/image_container.py and firmware/main/image_container.c line by line: struct `<4sBBHHHBBHII`, 24 bytes, field offsets, check order, error classes, 64-bit length math, CRC-32 of payload only, legacy rule. 29 fixtures plus manifest.txt and generator committed. server/test_image_container.py passes (69 tests across the two Python files). |
| 2 | Non-announcing frame gets its raw image byte for byte; announcing frame gets the container (IMG-02) | VERIFIED | byos_server.py diff is small: `_served_image()` returns the image object unchanged when `negotiate_version` is None, and the digest and publish only use `served`. Tests pin the legacy body SHA-256 (46d99bcb...) and the full legacy response dict, with junk-header cases (negotiation tests). Announce tests check container bytes, the hash of the served bytes, no new display key, state files unchanged, and use of the shared encoder. All pass. |
| 3 | Reference reader rejects bad magic/version/length/dimensions before touching a display buffer and accepts legacy raw (IMG-03) | VERIFIED | `imgc_parse` takes no display buffer and returns only a view. Checks follow the spec order. It accepts legacy exactly at the panel size and never treats SPIM as legacy. `./firmware/tests/run_host_tests.sh`: "test_image_container: all passed", 14 suites pass. |

**Score:** 3/3

## Spot-Checks and Gates Run

| Check | Result |
|-------|--------|
| `server/.venv/bin/python -m pytest stub-server/test_image_negotiation.py server/test_image_container.py --cov-fail-under=0` | 69 passed |
| `pytest stub-server server/test_fleet*` (includes stub-server/test_phase47_freeze.py, the Phase 48 freeze test) | 346 passed, 1 skipped (root ignores dir permission bits; unrelated) |
| `./firmware/tests/run_host_tests.sh` | 14 suites pass, including test_image_container |
| ruff on server/image_container.py and stub-server | clean |
| mypy | clean (17 source files) |
| scripts/check_function_size.py check --max 80 server stub-server | none over 80 |
| scripts/check_comment_history.py check | exit 0 |
| TBD/FIXME/XXX in phase files | none |

## Scope Checks

- Diff 538ff1b^..HEAD touches nothing under companion/, no auth files, no api_client.*, no CMakeLists.txt, and no deploy, .github, or systemd artifacts. Only non-planning files changed: docs/IMAGE-FORMAT.md, firmware/VENDOR.md, firmware/main/image_container.[ch], firmware/tests/{run_host_tests.sh,test_image_container.c,fixtures}, pyproject.toml (mypy lists only), server/image_container.py, server/test_image_container.py, stub-server/{README.md,byos_server.py,test_image_negotiation.py}.
- Legacy path: no behaviour change for non-announcing frames (same bytes, hash, URL, response keys, state files).

## Requirements Coverage

| Req | Status |
|-----|--------|
| IMG-01 | SATISFIED |
| IMG-02 | SATISFIED |
| IMG-03 | SATISFIED |

## Notes (non-blocking)

- Announcing frames get a different hash (header included), so a frame that switches format sees one extra full refresh. The spec documents this and accepts it.
- The new image_container.c is compiled by the firmware build via `SRC_DIRS "."` but is unreferenced. This is documented in VENDOR.md. Only the ESP-IDF build can confirm it compiles cleanly there.
- The spec's adoption notes (api_client.c buffer and length gate must grow by header_len) are a hand-off to the firmware release phase (57).

## Not Verifiable in This Sandbox

1. ESP-IDF Docker build (see above).
2. Chromium/Playwright companion tests.

## Gaps Summary

No gaps. The phase goal is achieved in code; status is human_needed only because of the two sandbox-limited items.
