# Quick 261003-dlh Summary

Removed the visible "What appears" / "Ce qui s'affiche" h2 from the Display page. The
`<section id="display-look" class="display-appearance">` stays and is now named by `aria-labelledby`
pointing at the appearance card's own h2 (`aspect-heading`), so the outline is h1 -> h2 (card) -> h2 (Runway)
-> h2 (Quiet hours). The vertical space of the heading is gone.

- Removed `DISPLAY_LOOK_HEADING` and the `display.look` FR entry (unused elsewhere). `DISPLAY_LOOK_SECTION_ID` kept
  (tests use it as a position marker; no JS/CSS/skip-link referenced it).
- Tests: retargeted the bilingual appearance-flow test (section named by the card heading, old heading text
  absent in EN and FR); dropped the browser check of the removed heading's type triple.
- `companion/testdata/render_baseline.json` regenerated; diff inspected: only the four Display bodies, losing the h2.
- Screenshots of /display at 1280 and 390, light/dark, EN/FR in scratchpad/shots3 reviewed.
- Gates: full SKYPANE_REQUIRE_BROWSER=1 run 3570 passed, 8 skipped (root-permission skips); ruff, mypy,
  comment-history, function-size all green.

Deviations: none.
