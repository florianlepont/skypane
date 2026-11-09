---
phase: 62-plane-screen-redesign
plan: 10
subsystem: companion-preview-and-render-cli
tags: [preview, cache, layout, cli]
requires: [62-06]
provides:
  - layout-aware theme and frame previews with layout-keyed caches
  - "--layout option in the render CLI"
affects: [companion/theme_preview.py, companion/preview_images.py, server/plane/render/cli.py]
key-files:
  created:
    - companion/test_theme_preview_layout.py
    - server/test_render_cli_layout.py
  modified:
    - companion/theme_preview.py
    - companion/preview_images.py
    - companion/test_preview_cache.py
    - companion/test_display_looks.py
    - server/plane/render/cli.py
decisions:
  - "layout None means classic in every preview function; the cache file name always carries the layout segment"
  - "an unknown or blank layout query value is a 404 identical to an unknown theme"
requirements-completed: [PSR-06]
duration: ~25 min
completed: 2026-11-09
---

# Phase 62 Plan 10: Layout-aware previews and CLI Summary

Companion previews (chip crop and full frame) render any allow-listed layout with layout-keyed signatures and cache paths, and `python -m server.plane.render --layout <id>` produces packed images per layout.

## Tasks

1. Layout-aware previews and caches - commit ce48c74
   - `theme_preview.layout_key()` is the single allow-list gate (None = classic, known id = itself, else None and refused).
   - Layout is in the preview and frame signatures and in the cache file names; `THEME_PREVIEW_CACHE_VERSION` and `FRAME_PREVIEW_CACHE_VERSION` are now 2; max-file bounds raised to 256 and 480 (18 themes x 5 layouts x states x sizes).
   - `frame_preview_src()` takes an optional layout and adds `&layout=` only when given, so existing URLs are unchanged.
   - Routes read `layout` via `companion/preview_images.py`; blank, unknown or traversal values return the unknown-theme 404.
2. --layout in the render CLI - commit 19feabe
   - `choices=screen_layouts.LAYOUT_IDS`, default classic; argparse exits non-zero listing valid ids.

## Deviations from Plan

**1. [Rule 3 - Blocking] Edited companion/preview_images.py (not in files_modified)**
The layout query parameter is parsed in the route handlers, which live in this module; the plan's "route allow-lists" cannot be met otherwise.

**2. [Rule 1] Updated existing cache tests for the new file name shape and signatures**
`companion/test_preview_cache.py` and `companion/test_display_looks.py` fakes now accept `layout`, and the stale-file names use the `-classic-` segment. No behaviour assertion was weakened.

## Verification

- New tests (22) pass; full `companion` suite: 6110 passed, 2433 skipped (browser tests, root permission tests).
- server/test_render.py, test_render_profile_dispatch.py pass; ruff, mypy list, function-size gate and comment-history guard clean.
- Note: `companion/test_theme_picker_profile.py` raises a circular import (`companion.settings.form`) when it is the first module collected on its own; it passes inside the full companion run. This is in code this plan did not touch and was left alone.

## Known Stubs

None.

## Self-Check: PASSED
