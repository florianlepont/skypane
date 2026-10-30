---
phase: 50
slug: common-image-format
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-30
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Derived from `50-RESEARCH.md` "Validation Architecture". The BYOS imports the canonical encoder (CONTEXT D-18 amended), so the research's duplicate-pin test is replaced by the import itself.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 (xdist, cov); C host tests via `cc` and `assert.h` |
| **Config file** | `pyproject.toml`; `firmware/tests/run_host_tests.sh` |
| **Quick run command** | `server/.venv/bin/python -m pytest server/test_image_container.py stub-server/test_image_negotiation.py stub-server/test_phase47_freeze.py -x --cov-fail-under=0` and `./firmware/tests/run_host_tests.sh` |
| **Full suite command** | `./scripts/run-all-tests.sh` (coverage floor 93) |
| **Estimated runtime** | ~120 seconds |

## Sampling Rate

- **After every task commit:** quick command for the touched side, `python3 scripts/check_comment_history.py check`, `python3 scripts/check_function_size.py check --max 80 server stub-server`
- **After every plan wave:** full suite, `./firmware/tests/run_host_tests.sh`, `ruff check .`, `mypy`
- **Before `/gsd-verify-work`:** full suite green, freeze test green
- **Max feedback latency:** 150 seconds

## Per-Task Verification Map

| Requirement | Behavior | Test Type | Automated Command | File Exists | Status |
|-------------|----------|-----------|-------------------|-------------|--------|
| IMG-01 | Encoder equals golden bytes; decoder accepts valid, rejects each class | unit | `pytest server/test_image_container.py` | ❌ W0 | ⬜ pending |
| IMG-02 | No header / junk header: raw 960,000 bytes, same hash as pre-change reference | integration | `pytest stub-server/test_image_negotiation.py -k legacy` | ❌ W0 | ⬜ pending |
| IMG-02 | `X-Img-Fmt: 1`: container served, hash over container, fetchable, no new JSON key, no state change | integration | `pytest stub-server/test_image_negotiation.py -k announce` | ❌ W0 | ⬜ pending |
| IMG-02 | Phase 48 freeze stays green | integration | `pytest stub-server/test_phase47_freeze.py` | ✅ | ⬜ pending |
| IMG-03 | C reader returns the manifest code for every fixture, accepts legacy, CRC-32 matches `zlib.crc32` | host C | `./firmware/tests/run_host_tests.sh` | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] Reference constants captured from the unmodified `byos_server.py` before any handler edit
- [ ] `server/image_container.py` (+ mypy list entries), `server/test_image_container.py`, `stub-server/test_image_negotiation.py`
- [ ] `firmware/main/image_container.[ch]`, `firmware/tests/test_image_container.c`, fixtures + manifest + generator
- [ ] `docs/IMAGE-FORMAT.md`, `firmware/VENDOR.md` entry

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ESP-IDF 5.3.1 container build still compiles with the new C file | IMG-03 | Needs the Docker build image | `firmware/build.sh` (or the firmware CI `build` job) |

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] Sampling continuity maintained
- [ ] `nyquist_compliant: true` set once the map is complete

**Approval:** pending
