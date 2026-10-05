---
phase: quick
plan: 261003-jmq
subsystem: companion/home
tags: [home, status, overdue, battery, i18n]
key-files:
  modified:
    - companion/frame_state.py
    - companion/ui_base.py
    - companion/ui_components.py
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/i18n_fr/home.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-10-03
---

# Quick 261003-jmq: Home status - late wording and compact battery-first panel

**Overdue now says so ("Update overdue · expected at 08:05"), a long delay turns the dot amber with a Health link, and the panel is shorter with a much larger battery tile.**

## Design

- Late wording lives in the shared `frame_state.HEADLINE_LATE` (and its `ui_base` twin), so
  the Display strip reads the same. FR: "Mise à jour en retard · attendue à HH:MM". The clock
  carries its date only when not today (existing `local_clock_text`).
- States keep their semantics: due until next wake + 2 intervals (the existing grace), then
  overdue (wording, no countdown, green dot, no link). New
  `frame_state.is_long_overdue()`: more than 3 effective intervals past the expected wake
  turns the dot amber and adds "See Health / Voir la santé" to /health. Quiet-hours hold is
  never overdue. Health thresholds and wake policy untouched.
- Cadence: muted `<details>` "Updates about every 5 min" / "Mise à jour environ toutes les
  5 min"; the reason ("To save its battery, ...") is the disclosure body. Native, keyboard and
  no-JS friendly.
- Battery: own bordered tile (label and Low/Very low word on top; 2rem figure and a 72x32
  glyph/level bar below). Role=img accessible name and thresholds unchanged.
- Layout: desktop three zones (status | battery | switches), phones stacked. Screenshots in
  the session scratchpad (`shots2/`), 1280/390/360, light and dark.

## Deviations from Plan

- The brief suggested roughly one interval of tolerance before the overdue wording; the
  existing grace (2 intervals) is kept, as the brief also asked to keep the existing
  due/late semantics.
- FR link text is "Voir la santé" as requested, while the FR nav tab is called "État".
- The Display strip (shared wording) changed with Home; its "Expected since" tests were
  retargeted. Health's own pages do not use this headline.
- When Health already flags a warning, Home may show both the overdue Health link and the
  existing "Something needs attention" row.

## Self-Check: PASSED

Full SKYPANE_REQUIRE_BROWSER=1 run-all-tests: 3570 passed, 8 skipped (root permission-bit skips), run after the baseline regeneration. ruff, mypy, comment-history and function-size gates clean.
