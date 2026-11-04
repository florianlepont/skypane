# Phase 61 — batch 3 (owner validation feedback)

Source of truth: `61-OWNER-VALIDATION.md` (D27–D30, W6–W17). Mockups live in
the session scratchpad `sketches/` directory; executors read them from the
path given in their prompt. Plans run sequentially on one branch; each ends
green (ruff, mypy, targeted tests, render baseline regenerated, comment
history guard) and is committed on its own.

| Plan | Scope | Owner refs |
|------|-------|-----------|
| 61-36 | Account page and navigation chrome: remove language/theme switches from the sidebar (kept on Account, redesigned as labelled preference rows), Account icon becomes a person | W13, W14, W15 |
| 61-37 | Frame switcher becomes a strip of frame tiles (picture, name, status dot, last-seen word, active outlined, "Add a screen" tile); replaces the dropdown on phone and desktop | D30, W17 |
| 61-38 | Quiet-hours dialog redesigned as sketch C (preset cards, Start/End tiles) | D27 |
| 61-39 | Personalisation: animated secondary navigation, one page per entry, Look page shows the picker as main view | D29, W10 |
| 61-40 | Airline collection: sort/filter bar integrated (auto-submit select, no clipped Apply button, no-script fallback keeps a button), rarity colours on rare airlines and aircraft | W11, W12 |
| 61-42 | Console Fleet: tile strip + frame detail view + System tile, replaces Fleet, Status, Version, Device tabs | D31, W18 |
| 61-41 | Location page rebuilt as sketch V1 (full-screen map, mode switch, bottom sheet / floating left card, derived coordinates and time zone, no-script form kept) | D28 |

Constraints: unchanged from earlier plans (phase-47 files and `hardware/`
untouched, expand-only, no deploy, EN/FR strings in `companion/i18n_fr/`,
360 px, 44 px targets, both themes, behaviour tests, app.py line ceiling).
