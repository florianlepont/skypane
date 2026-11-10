---
phase: quick-261110-sle
plan: 01
type: execute
autonomous: true
---

# Quick 261110-sle: the special look editor uses the large look cards

Owner decision 2026-11-10 (workstream v1-2, branch design/plane-screen-exploration): the
special look editor (new and edit) chooses its look with the same large look cards as the
Departures, Arrivals and Calendar views. The big left-hand preview and its caption column are
removed; the selected card is the preview.

## Tasks

1. `companion/settings/rules.py`, `layout_picker.py`: single-column form (Applies to summary,
   Look section of cards, then the bar). Giant layouts keep the five pairing cards; the classic
   layout shows one card per offered theme (`theme_group_html`). Cards use the layout-aware
   preview routes. Drop the preview column, caption and the look target attributes.
2. `style.css`, `theme-preview.js`: remove the preview/caption rules and the script's handling of
   the three-choice picker on the form; keep suggestion chips and everything the other pages use.
3. i18n: drop the unused "Matching flights will look like this." string.
4. Tests: update served-HTML and browser tests, regenerate the render baseline.
