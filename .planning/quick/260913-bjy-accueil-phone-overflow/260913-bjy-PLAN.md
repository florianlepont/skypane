---
phase: quick/260913-bjy
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/static/style.css
  - companion/test_view_pages.py
  - companion/test_browser_ux.py
autonomous: true
requirements: []          # Decision-point-tracked quick task, the precedent every 06.x/quick plan
                          # in this repo follows. Traceability is via `decisions` below.
closes: B11               # 22-AUDIT.md's "no horizontal scrollbar at 390px", closed on Vols (22-09),
                          # Compagnies (22-11) and Etat (22-12). Accueil is the fourth surface, and
                          # the one nobody re-measured after 22-07 put the time on one line.

decisions:
  - D-01  # The cause is `.recent-flight__time`'s percentage max-width, not `white-space: nowrap` and
          # not the age element. DELETE the clamp; keep 22-07's one-line intent verbatim.
  - D-02  # Do NOT add a wrapping flex container. Measured first, rejected on the measurement: the
          # `auto` track always grows to max-content before the neighbouring minmax(0, 1fr) track
          # yields, so flex-wrap never engages at any width and would ship inert.
  - D-03  # Retarget test_view_pages.py's B18 nowrap check onto `justify-self: end` (unique in the
          # file) — it currently anchors its block lookup on the very literal being deleted.
  - D-04  # The new browser check is general on Accueil (every element against the viewport, every
          # .recent-flights descendant against its own row box), not one selector, and runs in BOTH
          # languages at BOTH 390px and 1280px.

must_haves:
  truths:
    - "At a 390px viewport, on Accueil, document.documentElement.scrollWidth <= 390 in BOTH languages"
    - "No element on Accueil paints right of the viewport at 390px, in both languages"
    - "No .recent-flights descendant paints outside its own .recent-flight row box, at 390px AND 1280px, in both languages — the desktop half scrollWidth alone cannot see"
    - "22-07's one-line intent is preserved: white-space: nowrap stays, the markup is untouched, the clock/sep/age composition is unchanged"
    - "The new browser check is proven non-vacuous by reverting the CSS fix and watching only it go red"
    - "EXPECTED_CHECK_COUNT re-derived by RUNNING the harness, never by arithmetic"
    - "companion/static/style.css still carries zero stray comment terminators"
    - "No test exception is added anywhere; scripts/run-all-tests.sh matches the documented sandbox baseline"
  artifacts:
    - "companion/static/style.css — the percentage max-width deleted from .recent-flight__time, with the measurement that condemned it recorded in the rule's own comment"
    - "companion/test_view_pages.py — the B18 nowrap check retargeted onto a locator that survives the deletion"
    - "companion/test_browser_ux.py — one new check, +1, and a re-derived EXPECTED_CHECK_COUNT"
  key_links:
    - ".recent-flight's third `auto` track -> .recent-flight__time's percentage max-width — the track resolves to the item's max-content, so the percentage resolves against the very content it was meant to bound. This is the whole defect; if a percentage max-width ever returns to this rule it returns with it"
---

<objective>
Close B11 on Accueil, the fourth and last surface: at a 390px viewport the Home page's
`document.documentElement.scrollWidth` is 411px (FR) / 408px (EN) against a 390px client
width, in both themes, and the five « Vols récents » rows show their relative age clipped
at the right edge of the screen.

Fix it at the cause in `companion/static/style.css`, retarget the one existing check whose
block locator is the literal being deleted, and add the browser-harness measurement that
would have caught this class on Accueil at any point in the last nine plans.
</objective>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md
@.claude/skills/sketch-findings-skypane/references/data-density.md
@companion/static/style.css
@companion/pages/home_page.py
@companion/test_browser_ux.py
</context>

<measurement>
Reproduced before changing anything, with a real Chromium tab against a real
`companion/app.py` subprocess, at six widths x two languages x two themes:

  lang  vp     doc.scrollWidth   .recent-flight   .recent-flight__time   .time-value__age
  EN    390    408 (cw 390)      41..349 (308)    261..349 (88)          348..408 (60)
  FR    390    411 (cw 390)      41..349 (308)    256..349 (93)          346..411 (65)
  FR   1280   1280 (cw 1280)    899..1191 (292)  1098..1191 (93)       1188..1253 (65)

The user's diagnosis is confirmed exactly. Two things it did not say:

1. `.recent-flight__time`'s `clientWidth` is 88px (EN) / 93px (FR) while its own
   `scrollWidth` is 147px / 155px — at EVERY width from 320px to 1440px, unchanged.
   88/147 = 0.6 and 93/155 = 0.6 exactly. The box is clamped to 60% of ITS OWN content.
2. The spill is therefore NOT phone-only. At 960px and 1280px the age still paints
   outside `.recent-flight`'s right edge (1253 against a row ending at 1191) — it just
   stays inside the wider viewport, so no scrollbar appears and no one saw it.

Mechanism: `.recent-flight` is `grid-template-columns: 40px minmax(0, 1fr) auto`. The time
sits in the third, content-sized `auto` track, so that track resolves to the item's own
max-content width. A percentage max-width on the item then resolves against that
content-derived track width — clamping the box to 60% of exactly the content it was meant
to bound, and guaranteeing a 40%-of-the-line overflow unconditionally. Under
`white-space: nowrap` nothing can reflow into the smaller box, so the overflow is painted.
The declaration is a lie to the layout engine: reserve 88px, paint 147px.
</measurement>

<tasks>

<task type="auto">
  <name>Task 1: Delete the clamp, retarget the check that anchors on it, and pin Accueil with a browser measurement</name>

  <action>
  1. `companion/static/style.css`, `.recent-flight__time`'s own rule: delete the percentage
     max-width. Keep `text-align: right`, `justify-self: end` and `white-space: nowrap`
     exactly as they are — 22-07's one-line intent is preserved, not reverted. Extend the
     rule's existing B18 comment with the measurement above and with D-02's rejected
     alternative. Do NOT write `*` followed by `/` anywhere inside that comment, and do not
     write the deleted declaration's literal text into it.
  2. `companion/test_view_pages.py`, `_recent_flight_time_nowrap_in_css()`: its comment
     explains that it anchors on the deleted literal because the bare selector text also
     matches the shared colour-only rule. Retarget the anchor onto `justify-self: end`
     (verified unique in the stylesheet) and correct the comment to match.
  3. `companion/test_browser_ux.py`: one new check, in both languages, at 390px and 1280px —
     `documentElement.scrollWidth <= viewport width`; no element paints right of the
     viewport; no `.recent-flights` descendant paints outside its own `.recent-flight` box.
     Name the offending class list in every failure message.
  4. Re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness.
  5. Mutation-test: restore the deleted declaration, confirm the new check FAILS and names
     the overflow, remove it again, confirm it passes. Report both pass counts.
  </action>

  <verify>
  `./scripts/run-all-tests.sh` matches the documented sandbox baseline of exactly 5 failing
  checks (4 x WR-11 read-only, 1 x `anomaly_active()`), with `browser-ux` at 23/23,
  `companion-app` 270/272, `status-pages` 267/268, `manual_resolutions` 21/23.
  </verify>

  <done>
  Accueil does not scroll sideways at 390px in either language, the age sits inside its card
  at every measured width, and a check exists that goes red if either stops being true.
  </done>
</task>

</tasks>

<hard_constraints>
- No new design-system literal. The fix is a DELETION; no token, size or breakpoint is added.
- Never add a test exception. The suite carries none (22-15 deleted the last one).
- `companion/static/style.css` must keep zero stray comment terminators.
- No new user-facing string, so no new French catalogue entry — CFG-29/CFG-30 must not regress.
- Do NOT touch ROADMAP.md. Update STATE.md's "Quick Tasks Completed" table only.
</hard_constraints>
