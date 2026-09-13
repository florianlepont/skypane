---
phase: quick/260913-eab
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/test_browser_ux.py
autonomous: true
requirements: []          # Decision-point-tracked quick task, the precedent every 06.x/quick plan
                          # in this repo follows. Traceability is via `decisions` below.
closes: disclosure-state  # The measurement gap itself, not one more instance of it: a collapsed
                          # <details> has its contents not laid out at all, so every sweep in this
                          # repo measured pages in their DEFAULT state and everything asleep inside
                          # a disclosure was invisible BY CONSTRUCTION.

decisions:
  - D-01  # ONE general check, not one per disclosure. It opens every <details> on every page, so
          # it covers the 47 that exist today AND any added later with no edit to this file. That
          # generality is the entire point of the task, not a bonus on top of it.
  - D-02  # TWO assertions, because either alone is blind to half the class. (a) the page never
          # scrolls sideways; (b) no element whose computed overflow-x is auto/scroll has content
          # wider than its own box. (b) is what catches the readings-table defect: the WRAP scrolls
          # while documentElement.scrollWidth stays exactly 390, closed AND open.
  - D-03  # overflow: hidden is DELIBERATELY excluded from (b). text-overflow: ellipsis makes
          # scrollWidth > clientWidth by design on every truncated cell in the app — flagging it
          # would be noise, and noise is how a check gets an exception added to it.
  - D-04  # Anti-rot is per-page, not global: each page asserts a minimum disclosure count AND that
          # at least one was CLOSED before being forced. Without the second half the check
          # degenerates into an ordinary default-state sweep and silently stops adding anything.
  - D-05  # The login page is measured but carries NO count assertion — it renders no nav and so has
          # zero <details>. Its own "this measured something" guard is the password field. Asserting
          # a non-zero count there would assert a falsehood.
  - D-06  # 360px is measured alongside the brief's 390/1280 — it is the minimum supported viewport
          # (developer decision 2026-09-13) and both fixes of that day were 360px-driven. Measured
          # clean BEFORE being added, never assumed, at a cost of ~2.8s.

must_haves:
  truths:
    - "Every <details> on every page opens with no page-level and no container-level overflow, at 360/390/1280px in both languages"
    - "The check fails, rather than passes, if a selector change leaves it measuring nothing"
    - "The check catches the readings-table defect UNAIDED, with 260913-cz6's own check deleted"
    - "EXPECTED_CHECK_COUNT re-derived by RUNNING the harness, never by arithmetic"
    - "The check's own runtime is measured and reported, not estimated"
    - "No overflow found is fixed — a new defect is a finding for the developer, not a drive-by fix"
    - "No test exception is added anywhere; scripts/run-all-tests.sh matches the documented sandbox baseline"
  artifacts:
    - "companion/test_browser_ux.py — one new check, +1, and a re-derived EXPECTED_CHECK_COUNT"
  key_links:
    - "A collapsed <details> is not laid out -> nothing inside it has a width, a position, or anything to measure -> every sweep to date, including a 24-combination visual pass, was structurally blind to it. The fix is not another per-selector check; it is opening every disclosure before measuring."
---

<objective>
Exactly one disclosure in the app is pinned today: État's readings table, by name, by the
check 260913-cz6 added. Replace that with the general form — one check that forces every
`<details>` on every page open and asserts nothing overflows — so the disclosures that
exist now and any added later are covered by construction rather than by enumeration.
</objective>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md
@companion/test_browser_ux.py
@companion/static/style.css
</context>

<measurement>
Surveyed before writing anything, with a real Chromium tab against a real
`companion/app.py` subprocess, every `<details>` forced open, at 320/360/390/768/1280 x
two languages. Counts re-derived by running, never carried from the brief:

  page       route       <details>  kinds
  Accueil    /            1         nav
  Affichage  /display     3         nav + 2 "how it works"
  Vols       /flights    37         nav + 36 row cards
  Compagnies /airlines    1         nav
  État       /health      4         nav + readings + 2 data cards
  Appareil   /device      1         nav
  Connexion  /login       0         (renders no nav)

The brief's five-page table is confirmed exactly (1/37/3/1/4 = 46). Its `~83` total is
NOT: `/preview` and `/settings` are 303 redirects (to `/flights` and `/display`), so the
"panel-preview page" in that figure is `/flights` counted a second time. The real total
is 47, and 36 of those are one component repeated per row — five distinct kinds.

All 47 are CLOSED by default on every page (closedBefore == n everywhere), so forcing them
open is doing real work on every page, not decorating a sweep that already covered them.

Overflow with everything open: CLEAN at all five widths in both languages — no page scrolls
sideways, nothing lays out right of the viewport, no scroll container's content exceeds its
box. The brief's "all currently clean" holds, including at the 360px contract floor.
</measurement>

<tasks>

<task type="auto">
  <name>Task 1: One check that opens every disclosure on every page and asserts nothing overflows</name>

  <action>
  1. `companion/test_browser_ux.py`: one new check. For each of 360/390/1280px x {en, fr}:
     measure `/login` FIRST in a fresh context (after `_login()` it is a 303 to `/`), then
     the six authenticated pages. On each, force every `<details>` open, then assert
     (a) `documentElement.scrollWidth <= viewport` and nothing lays out right of it, and
     (b) no element with computed `overflow-x: auto|scroll` has `scrollWidth > clientWidth`.
     Report the scroll-container diagnostic BEFORE the viewport one — when a container
     overflows, every descendant's rect escapes too, and a list of tag names points at
     nothing.
  2. Anti-rot: per page, assert a minimum `<details>` count and that at least one was CLOSED
     before being forced. `/login` is exempt from the count (it has none) and guards on its
     password field instead.
  3. Re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness.
  4. Mutation-test: restore `min-width: max-content` on `table.data-table--readings`, confirm
     the new check goes red; then DELETE 260913-cz6's own check and confirm the new one still
     goes red unaided. Report both counts. Restore, confirm green.
  5. Measure the check's own runtime against the pristine harness and report it.
  </action>

  <verify>
  `./scripts/run-all-tests.sh` matches the documented sandbox baseline of exactly 5 failing
  checks (4 x WR-11 read-only, 1 x `anomaly_active()`).
  </verify>

  <done>
  Every disclosure in the app is measured open, at three widths in two languages; the check
  cannot pass by measuring nothing; and it catches the readings-table defect on its own.
  </done>
</task>

</tasks>

<hard_constraints>
- Do NOT fix any overflow found. The survey says all are clean; if that turns out false, STOP
  and report it with measurements. A new defect here is a finding, not a drive-by fix.
- Never add a test exception. The suite carries none.
- `companion/static/style.css` must keep zero stray comment terminators (the mutation touches
  it only transiently and is reverted byte-identically).
- Do NOT touch ROADMAP.md. Update STATE.md's "Quick Tasks Completed" table only.
</hard_constraints>
