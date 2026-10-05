---
quick_id: 261003-tq4
slug: home-status-polish
date: 2026-10-03
branch: claude/home-status-polish
key-files:
  modified:
    - companion/pages/home_page.py
    - companion/frame_state.py
    - companion/ui_base.py
    - companion/ui_components.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/look.py
    - companion/i18n_fr/display.py
    - companion/settings/theme.py
    - companion/settings/form.py
    - companion/settings/runway_led.py
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
---

# Quick 261003-tq4: Home status polish (+ Display cleanups, phone titles)

## What shipped

1. **Next-update line.** On time it reads "Next update in 2m" (FR "Prochaine
   mise à jour dans 2 min"): a live countdown, no clock, no approximation
   sign. Overdue and held wordings are unchanged. The shared `home.next_update`
   wording changed everywhere, so the Display frame strip's headline carries
   the same countdown (its duplicate countdown caption is dropped on time).
   The cadence moved into an "i" button (new `icon-info` glyph) with a
   CSS-only tooltip: `aria-describedby` to a `role="tooltip"` element, shown on
   hover and focus-within (a tap focuses the button), 44 px hit area, bubble
   wrapped to the status zone. The old muted `<details>`, `home.cadence` and
   its strings are gone. The card no longer clips (`overflow` removed) so the
   tooltip can extend past it; the switches panel rounds its own corners.
2. **Image caption.** No caption under the latest image; the alt text carries
   the flight line (`home.the_picture_currently_on_the_frame_flight`).
   `home.rendered` and the unused gallery-name parser are removed.
3. **Dot pulse.** A soft halo ring (`::after`, transform and opacity only) on
   the green or amber dot; none for quiet hours / screen off. Period is the new
   documented token `--motion-dot-pulse` (3.2 s), spendable only by
   `.home-state__dot--pulse::after`; the budget test now pins both exceptions.
   Reduced motion sets `animation: none` (computed style verified).
4. **Display.** Removed the look-card sentence and the sample-flight pill
   (ids deleted), and the "(next wake ≈ …)" clause of the Runway caption
   (`_with_next_wake` and its id deleted). The Display page has no latest-frame
   caption in this code; the caption the owner saw is Home's, now gone.
5. **Quiet-hours window link.** On Home the "23:00 – 07:00" is a link to
   `/display#quiet-hours-group-heading` (existing anchor), outside the switch
   button, 44 px target, name "Edit quiet hours (23:00 – 07:00)"; the switch
   keeps its whole-row tap target.
6. **Phone page title.** `page_header(..., tabbed=True)` for Home, Display,
   Flights, Airlines: below 960 px the h1 is visually hidden (still in the
   DOM) and the header's space is reclaimed; Health, Device and Update keep it.

## Deviations

- EN countdown reads "in 2m" (the app's shared relative ladder), not
  "in 2 min"; FR reads "dans 2 min". Changing the EN ladder would touch every
  countdown in the app.
- In the one-interval grace window after the expected wake the line reads
  "Next update waiting…" (the existing neutral countdown wording).
- Without any check-in there is no next-update line, so no info button either.
- Pulse follows the dot's tone: a briefly overdue frame (green dot) still
  pulses green; amber (long overdue, battery hold) pulses gentler.
- Display scope: no latest-frame caption existed (see item 4).

## Verification

Screenshots (not in the repo): `scratchpad/shots-tq4/`. Baseline diff was
inspected token by token: only the intended Home/Display/header changes and the
added sprite symbol. Full suite, ruff, mypy, comment-history and function-size
gates: see the final report.
