---
phase: 62-plane-screen-redesign
plan: 01
subsystem: render
tags: [fonts, anton, pairings, giant-lettering]
requires: []
provides:
  - Anton-Regular.ttf vendored with OFL text and provenance
  - server/pairings.py (PAIRINGS, PAIRING_FOR_THEME, pairing_for_theme)
  - server/plane/render/giant/ package with Anton loader (fonts.py)
affects: [62-02 and later giant-lettering plans]
tech-stack:
  added: [Anton font (OFL 1.1)]
  patterns: [pure read-time theme mapping, cached font loader]
key-files:
  created:
    - server/assets/fonts/Anton-Regular.ttf
    - server/assets/fonts/Anton-OFL.txt
    - server/pairings.py
    - server/test_pairings.py
    - server/plane/render/giant/__init__.py
    - server/plane/render/giant/fonts.py
    - server/test_giant_fonts.py
  modified:
    - server/assets/fonts/VENDOR.md
    - pyproject.toml
key-decisions:
  - "Unknown or missing theme id falls back to the default theme's pairing (white)"
  - "Green, black and band_black themes map to the grey pairing (documented assumed defaults)"
requirements-completed: [PSR-02, PSR-04]
duration: short
completed: 2026-11-09
---

# Phase 62 Plan 01: Giant-lettering foundation Summary

Anton vendored from a pinned google/fonts commit, a pure total theme-to-pairing mapping over all 18 theme ids, and a `giant` render package with a cached Anton loader and glyph-support checks.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 Vendor Anton | 507f13b | Font and OFL copied byte-for-byte; sha256 re-verified before copying; VENDOR.md records commit, upstream path, digests, licence |
| 2 Pairings | d2267ff | 5 pairings keyed by existing THEMES ids; mapping covers set(THEMES); tests; added to mypy list |
| 3 giant package | 1623e06 | `anton(px)`, `cap_height`, `supports`, `ascii_fallback`, `SUPERSAMPLE_PX = 600`; tests include digest-vs-VENDOR.md check |

Pinned source: google/fonts commit `5bb28733cec313b63fbd415b574b5ae35c8aa8b8` (2026-11-08); font sha256 `a4ba3a92...ab947cab`, OFL sha256 `ee67e6ee...c9e4` (full values in VENDOR.md; match the research digests).

## Deviations from Plan

**1. [Rule 3 - Blocking] `server/screen_layouts.py` not added to the mypy `files` list.**
The plan asks for the entry now, but the module is created by plan 62-02 and mypy fails on a missing file. Only `server/pairings.py` was added. Plan 62-02 (or its verifier) must add `"server/screen_layouts.py"` to `[tool.mypy] files` in `pyproject.toml` once the module exists.

**2. VENDOR.md pin provenance.** The pin is the HEAD of a shallow sparse local checkout (resolved from the owner-provided checkout, not via `gh api commits?path=`), as directed by the run instructions. The commit is immutable; whether it is the latest touching `ofl/anton` could not be proven from a shallow clone. This is stated in VENDOR.md.

## Verification

pytest (pairings, giant fonts, import boundaries: 44 passed), ruff, mypy (30 files), `check_function_size.py check --max 80 server stub-server`, `check_comment_history.py check` all pass. No golden fixtures or classic render output touched; no Phase 47/47.1 or hardware/ files touched.

## Known Stubs

None.

## Self-Check: PASSED

All created files exist; commits 507f13b, d2267ff, 1623e06 present.
