---
phase: 67-project-and-code-optimisation
plan: 13
subsystem: server
tags: [module-move, shims, firmware]
requirements: [QUAL-01]
key-files:
  created:
    - server/firmware/__init__.py
    - server/test_module_shims_firmware.py
  modified:
    - server/firmware/cli.py (moved from server/firmware_cli.py)
    - server/firmware/image.py (moved from server/firmware_image.py)
    - server/firmware/registry.py (moved from server/firmware_registry.py)
    - server/firmware_cli.py
    - server/firmware_image.py
    - server/firmware_registry.py
    - pyproject.toml
decisions:
  - Package name `server.firmware` kept (no collision: the repo-root `firmware/` holds C only and the package is always addressed as `server.firmware`).
  - Old flat names are sys.modules alias shims, with a TYPE_CHECKING-only star import so mypy still sees the moved names.
---

# Phase 67 Plan 13: Firmware package move Summary

firmware_cli, firmware_image and firmware_registry now live in `server/firmware/` (cli, image, registry); the old flat names are `sys.modules` alias shims, so every importer, `monkeypatch`/`mock.patch` site and `python3 -m server.firmware_cli` keeps working unchanged.

## Tasks

1. Shim identity tests first (`old is new`, patch through alias, repo-root bootstrap, `-m` smoke and import from a foreign cwd), then `git mv`, one extra dirname level in `cli._repo_root` and `image._REPO_ROOT`, shims. `registry` has no `__file__` bootstrap.
2. pyproject.toml: mypy file and strict-module entries for firmware_image replaced by `server/firmware/image.py` / `server.firmware.image` (path substitution only).

## Deviations

- [Rule 3 - Blocking] mypy reported `Module has no attribute "apply_reconcile_all"` (and one more) because mypy follows the shim file, not the runtime alias. Fixed with an `if TYPE_CHECKING:` star import inside each shim (never executed at runtime; the runtime alias is `sys.modules[__name__] = module`). No runtime star import exists.
- cli keeps `prog="firmware_cli"` and its log prefixes unchanged (no behaviour change).

## Retained shims

`server/firmware_cli.py`, `server/firmware_image.py`, `server/firmware_registry.py` (all callers, tests, scripts, deploy/activate.sh and docs still use the old names; removal is a later decision).

## Untouched

systemd units, poll_loop.py, fleet_db, history_db, device_config, ARCHITECTURE.md (plan 15), STATE.md, ROADMAP.md.

## Self-Check: PASSED
