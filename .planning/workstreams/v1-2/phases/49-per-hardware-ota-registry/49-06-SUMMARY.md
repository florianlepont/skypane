---
phase: 49-per-hardware-ota-registry
plan: 06
subsystem: ota
tags: [firmware, cli, import-dir, build-order, check-image]
requires: [49-05]
provides:
  - firmware_cli import-dir visits tags in ascending build order and reads per-type pairs (release-<key>.json + skypane-<key>-<tag>.bin)
  - --hardware-type on import-bench, list and the new check-image verb
  - deploy/README.md "Firmware releases (OTA)" documents per-type publishing
affects: [49-09 manifest generator, 49-10 signing profile]
key-files:
  modified:
    - server/firmware_cli.py
    - server/test_firmware_cli.py
    - deploy/README.md
decisions:
  - "Typed items are reported as 'added <tag> <key>' / errors as '<tag> [<key>]'; legacy output lines are unchanged"
  - "A tag directory holding only typed files skips the legacy pair; a directory with neither still reports the legacy 'release.json missing' error as before"
  - "Unknown --hardware-type is a usage error (exit 2); a validation mismatch in check-image is exit 1"
  - "check-image uses firmware_registry._signing_policy so it can never diverge from the publish-time policy"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01, OTA-02]
---

# Phase 49 Plan 06: Per-type, build-ordered firmware_cli Summary

firmware_cli now publishes per hardware type while the legacy layout and `list` output stay byte-compatible, and import order can no longer trip the monotonic build gate.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 RED tests | be2472f0 | 21 new tests failed first |
| 1 GREEN implementation | 50a33602 | import-dir, import-bench, list, check-image |
| 2 README | 516bf228, a35509af | second commit fixes the check-image example to use the skypane-user wrapper that test_docs.py enforces |

## What changed

- `_import_order` sorts release tags by build number, then non-tags by name (rejected as before).
- Per-type discovery is additive: `release-<key>.json` files are found by name, the key is shape-checked, then checked with `hardware.is_known` and `available_types` (simulated types only when the simulation gate is on) before any path is built; symlinked manifests or images, a manifest `hardware_type` that differs from the key, and the legacy key itself are item errors. Each item is isolated; already registered items never block the deploy.
- `import-bench --hardware-type` replaces the one-line legacy declaration from 49-05; `list` shows plain lines when only the legacy type holds releases, headings otherwise, one type with `--hardware-type`; `check-image` validates with `firmware_image.validate_for_target` and writes nothing.

## Deviations from Plan

None in scope. Only note: `check-image` reads the signing policy through `firmware_registry._signing_policy` (a private name) rather than adding a public alias to a file outside this plan's scope.

## Verification (run)

- pytest server stub-server deploy/tests test-support companion (-n auto --no-cov, SKYPANE_REQUIRE_BROWSER=1, local Playwright browsers): 4518 passed, 8 skipped (root permission bits, openssl backdating).
- server/test_firmware_cli.py, server/test_firmware_registry.py (201 passed) and deploy/tests/test_docs.py (12 passed) run directly.
- ruff check server stub-server deploy test-support companion scripts: pass.
- mypy: no issues in 16 source files.
- check_function_size.py check --max 80 server stub-server: 587 functions, none over.
- check_comment_history.py check: exit 0.
- Not run: the coverage-gated scripts/run-all-tests.sh.

## Known Stubs

None.

## Self-Check: PASSED

Commits be2472f0, 50a33602, 516bf228, a35509af exist; server/firmware_cli.py and this file exist.
