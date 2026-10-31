---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
plan: 09
subsystem: render
tags: [landscape, dispatch, cli, preview]
requires: ["56-01", "56-02", "56-08"]
provides:
  - layout.build_canvas(..., profile=None) dispatch with theme fallback
  - render CLI --hardware KEY
key-files:
  modified:
    - server/plane/render/layout.py
    - server/plane/render/cli.py
  created:
    - server/test_render_profile_dispatch.py
requirements: [HWR-01]
metrics:
  tasks: 2 of 3 (task 3 is the owner checkpoint, pending)
  completed: 2026-10-30
---

# Phase 56 Plan 09: Profile dispatch and --hardware preview Summary

`build_canvas` takes an optional `profile`; `None` runs the untouched legacy path. A profile normalises the theme with `themes.theme_or_default(theme_id, profile.inks)` (nothing stored is rewritten) and a landscape profile renders through `landscape.build_landscape_canvas` at the profile's own size. The render CLI gained `--hardware KEY`.

## Commits
- 40858913: build_canvas profile dispatch and theme fallback, dispatch tests
- 3dae2659: --hardware option and CLI tests

## Owner preview command (checkpoint)
Run from the repo root; previews already generated in
/tmp/claude-0/-home-user-skypane/c6b95eb7-2f02-507a-815f-b91c0a4ad599/scratchpad/previews/

```
R="env SKYPANE_SIM_HARDWARE=1 server/.venv/bin/python3 -m server.plane.render --hardware sim-landscape-800x480"
$R --state departing --callsign AF1380 --preview departing.png
$R --state arriving --callsign TO16VB --previous-callsign VY1234 --previous-hex 4a1b02 --preview arriving-previous.png
$R --state departing --callsign AF1380 --theme band_blue --preview band-theme.png
$R --state empty --preview empty.png
$R --state battery_empty --preview battery-empty.png
```

## Notes
- render_panel was not changed: it packs through the portrait wire size and is only used by the legacy path.
- mypy list not extended: the portrait render modules are not in it, so the landscape ones were left out too.
- Golden manifest untouched; golden and Phase 47 freeze tests pass after each task.
- The first full-suite run showed 18 companion browser-page failures that did not reproduce on two reruns (6126 passed, 566 skipped); unrelated to render code.

## Deviations from Plan
None.

## Self-Check: PASSED
