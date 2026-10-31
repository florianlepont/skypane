---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 03
subsystem: pairing
tags: [pairing, eink, pillow, auth]
requires: []
provides:
  - server/pairing_code.py (ALPHABET, generate_code, format_code, normalise_code, new_salt, hash_code, match_candidates, CODE_TTL_S, PENDING_SLEEP_S, RETIRED_SLEEP_S)
  - server/pairing_image.py (render_pairing_image, render_retired_image)
affects: [55-05, 55-07]
tech-stack:
  added: []
  patterns:
    - constant-time scan over every candidate row with a dummy compare when empty
    - byte-deterministic Pillow rendering (fontmode "1", integer layout, scale by min(w/1200, h/1600))
key-files:
  created:
    - server/pairing_code.py
    - server/pairing_image.py
    - server/test_pairing_code.py
    - server/test_pairing_image.py
  modified:
    - pyproject.toml
key-decisions:
  - "Cadence constants live in pairing_code.py, not device_policy.py (frozen wake constants)."
  - "pairing_code is in mypy files and strict overrides; pairing_image only in files."
requirements-completed: [AUTH-04]
duration: ~25min
completed: 2026-10-31
---

# Phase 55 Plan 03: Pairing code and e-ink screens Summary

Pure pairing building blocks: an 8-symbol code (30-symbol alphabet) stored only as a salted SHA-256 and matched in constant time over every row, plus byte-deterministic pairing and retired screens for any hardware profile.

## Tasks and commits

| Task | Commit | Result |
|------|--------|--------|
| 1. pairing_code module | 86d5180 | 7 tests; mypy strict |
| 2. pairing_image module | 5c43591 | 6 tests; cross-process hash and golden retired hash |

## Verification

- `pytest server/test_pairing_code.py server/test_pairing_image.py`: 13 passed
- mypy: no issues in 25 source files; ruff: all checks passed
- function-size gate (max 80): none over; comment-history check: clean
- Screens inspected visually (rendered to PNG outside the repo): layout matches UI-SPEC Surface 8; the footer status fits beside "SkyPane" (1000 of 1040 px).

## Deviations from Plan

- Wrapping: the instruction sentences are wrapped at 1040 px, so each sentence takes two lines at 52 px (the UI-SPEC allows wrapping). The FR block ends about y 1440 as specified.
- The code font steps down to fit 944 px; the legacy code fits after stepping down from 168 px.
- Test 5 asserts the retired screen lacks the code box frame and glyphs and that `render_retired_image` takes only `profile`.
- Otherwise none; no frozen or read-only file was touched.

## Known Stubs

None.

## Threat Flags

None. The code is never formatted into an exception or log; tests use a fixed fake code.

## Self-Check: PASSED
