# Quick 261003-dlh: remove the Display "What appears" heading

Remove the visible h2 (i18n `display.look`, `DISPLAY_LOOK_HEADING`) above the Display appearance card.
Keep `<section id="display-look" class="display-appearance">` and name it via `aria-labelledby` pointing at
the appearance card's own h2 (`ASPECT_HEADING_ID`), so the outline is h1 -> card h2.
Drop the orphaned i18n entry, retarget tests that asserted the heading, add an absence check in EN and FR,
regenerate `companion/testdata/render_baseline.json` after inspecting the diff, run the full gates.
