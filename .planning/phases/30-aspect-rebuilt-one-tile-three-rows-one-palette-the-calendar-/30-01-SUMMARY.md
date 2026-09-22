---
phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first
plan: 01
subsystem: testing
tags: [playwright, chromium, browser-ux-harness, cfg-86, page-height-measurement]

requires: []
provides:
  - "Playwright 1.62.0 + a downloaded Chromium binary, usable from server/.venv/bin/python3 — companion/test_browser_ux.py now RUNS its 96 checks instead of printing its SKIP line"
  - "30-BASELINE.md: the genuine, same-instrument, pre-change CFG-86 reading (Display document height 3486px at 390px / 3505px at 360px) taken at SHA 606e9819, tree clean"
  - "The three ROADMAP-cited historical figures (3743px/3524px/3556px) plus the harness's own in-code 4276px figure, each explicitly recorded as NOT this phase's baseline"
affects: [30-02, 30-03, 30-04, 30-05, 30-06, 30-07, 30-08]

tech-stack:
  added: []
  patterns:
    - "CFG-86-class measurement-and-report requirements need a same-instrument before/after pair taken by the same code path at two distinct moments — a historical ROADMAP figure from a prior phase's own tree is never a valid substitute for 'before', however recent."

key-files:
  created:
    - .planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-BASELINE.md
  modified: []

key-decisions:
  - "Installed only the already-declared server/requirements-dev.txt pin (playwright==1.62.0) into server/.venv/bin/python3 — the canonical interpreter scripts/run-all-tests.sh execs — rather than the ambient python3, and did not bump or add any dependency version."
  - "Harvested the baseline heights from the existing registered check's own stdout (_displays_page_height_is_recorded_at_both_phone_widths, which calls _display_page_height()) rather than writing a second, parallel measurement script — CFG-86 names 'the registered instrument', and a second measurer would be a second definition of the number."
  - "Recorded, but did not fix, three pre-existing FAILs the full browser-ux run surfaced (leave-guard-armed-before-commit, fallback-Save-click-timeout, wake-interval-echo) — none is caused by this plan's own change (Task 1 installs a dependency; Task 2 only writes a new doc), so per the deviation rules' scope boundary they are logged as a known pre-change baseline rather than auto-fixed."

requirements-completed: [CFG-86]

coverage:
  - id: D1
    description: "Playwright and a Chromium binary are installed into server/.venv/bin/python3 (the canonical interpreter scripts/run-all-tests.sh execs), and companion/test_browser_ux.py genuinely RUNS its checks — proved by the harness's own N/N tally, not by exit code alone, since exit 0 is also what the SKIP path returns"
    requirement: CFG-86
    verification:
      - kind: other
        ref: "server/.venv/bin/python3 -c 'import playwright' (exit 0) && server/.venv/bin/python3 companion/test_browser_ux.py — printed 'browser-ux: 93/96 checks pass', not the SKIP line"
        status: pass
    human_judgment: false
  - id: D2
    description: "30-BASELINE.md records the genuine pre-change Display document height at 390px and 360px, produced by the one registered instrument (_display_page_height(), companion/test_browser_ux.py:2870), with the SHA it was taken at, a clean-tree confirmation, all four superseded historical figures marked explicitly as not-the-baseline, and X6's 2600px target stated once as a target"
    requirement: CFG-86
    verification:
      - kind: other
        ref: "the plan's own Task 2 <automated> verify script (front-matter SHA regex, 390px/360px rows, >=2 distinct measured heights, 'Not the baseline' section, 2600px target, TBD after-placeholder) — printed OK"
        status: pass
    human_judgment: false

# Metrics
duration: 16min
completed: 2026-09-22
status: complete
---

# Phase 30 Plan 01: Wave 0 — Playwright Install + Genuine CFG-86 Baseline Summary

**Installed Playwright 1.62.0 + Chromium into `server/.venv` (the canonical interpreter) and captured the phase's genuine pre-change CFG-86 reading — Display's document height measures 3486px at 390px and 3505px at 360px, at SHA `606e9819dfd806ec992c95836c53307c50a2b11b`, before any Phase 30 markup exists.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-09-22T13:22:00Z (approx, per STATE.md's last-updated timestamp before this plan began)
- **Completed:** 2026-09-22T13:37:47Z
- **Tasks:** 2/2
- **Files modified:** 1 (tracked) — `30-BASELINE.md` created; `server/.venv` environment change is untracked (gitignored)

## Accomplishments

- `server/.venv/bin/python3 -c "import playwright"` now exits 0, and `companion/test_browser_ux.py` prints `browser-ux: 93/96 checks pass` — a real run, not its SKIP line — proving Playwright and a downloaded Chromium binary are both usable from the exact interpreter `scripts/run-all-tests.sh` execs.
- Captured the phase's one genuine, same-instrument "before" CFG-86 reading, quoted verbatim below, and wrote it into `30-BASELINE.md` along with the SHA it was taken at and confirmation the tree was clean at that moment.
- Explicitly recorded the three ROADMAP-cited historical figures (3743px Phase 25, 3524px Phase 27, 3556px 17-09 audit) plus the harness's own in-code fourth figure (4276px) as NOT this phase's baseline, so no later reader in this phase can accidentally compute the delta against the wrong number.

**Both measured heights, quoted verbatim from the harness's own stdout:**

```
[25-06 T1] Display document height at 390px: 3486 px (client 390x844, 18 theme radios)
[25-06 T1] Display document height at 360px: 3505 px (client 360x844, 18 theme radios)
```

## Task Commits

1. **Task 1: Install Playwright and Chromium into the canonical interpreter** — no tracked-file commit (environment-only change to `server/.venv`, which is gitignored per `server/.gitignore`). Verified directly: `import playwright` exits 0; `companion/test_browser_ux.py` prints a `93/96 checks pass` tally (not SKIP).
2. **Task 2: Capture the genuine pre-change CFG-86 reading and record it** — `8a6e7b0` (docs)

**Plan metadata:** this SUMMARY's own commit (docs, made after this file)

## Files Created/Modified

- `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-BASELINE.md` — front matter (`phase`, `taken`, `sha`, `tree_clean`), the measured-readings table, the instrument's provenance and four passed guards, a "Not the baseline" section naming all four superseded historical figures, and an "After (TBD — filled by 30-08)" section stating X6's 2600px target once.
- `server/.venv/` (untracked, gitignored) — `playwright==1.62.0` plus its `greenlet`/`pyee`/`typing-extensions` dependencies installed; Chromium 151.0.7922.34 and Chrome Headless Shell downloaded via `playwright install chromium`.

## Decisions Made

- Installed exactly the already-declared `server/requirements-dev.txt` pin into `server/.venv/bin/python3` — no version was bumped, added, or chosen; this task installed an existing pin per the plan's own instruction and the threat model's T-30-01 disposition (accept, no `[ASSUMED]`/`[SUS]` checkpoint owed).
- Used the harness's own registered check output as the sole source of the two heights, rather than writing a second, parallel measurement script — CFG-86 requires the "registered instrument," and a second measurer would itself be a second, competing definition of the number.
- Left the three pre-existing browser-ux FAILs (see below) unfixed and only documented — they are unrelated to this plan's own change (an environment install and a new doc file touch no application code) and are explicitly out of this plan's scope per the deviation rules' scope boundary.

## Deviations from Plan

None - plan executed exactly as written. Both tasks completed with their `<automated>` verify commands passing and their `<done>` criteria met.

## Issues Encountered

**Three pre-existing browser-ux FAILs surfaced by the first genuine (non-skipped) run of `companion/test_browser_ux.py` — recorded here per Task 1's own `<done>` instruction ("a pre-existing red check must be known before the phase starts changing markup"), not fixed, since none is caused by this plan:**

1. `the leave-guard stays armed for a field that has been edited but never fired change` — `expected the typed value to be held by the field before any commit`.
2. `with scripts blocked at 360px, in BOTH languages, the fallback Save is VISIBLE with a real box and still saves to disk` — `TimeoutError('Locator.click: Timeout 30000ms exceeded... element is not stable... element was detached from the DOM')`.
3. `a value the server's own validation rejects (wake_interval_s below its floor) re-renders the SAME page with the field's OWN inline error... echoes the user's rejected input back into the field` — `expected the field to echo back the user's own rejected input '30', got '301800'`.

These are pre-existing defects in already-shipped Display/Device save-bar and validation-echo behavior, unrelated to Phase 30's aspect-tile work. Full-suite result: `browser-ux: 93/96 checks pass`; every other harness in `scripts/run-all-tests.sh` is unaffected (`companion-app: 317/317`, `config-page: 274/274`, `status-pages: 316/316`, all server/stub-server suites green, coverage 93%). Recorded as this plan's own pre-change full-suite baseline; the phase's downstream plans should treat these three as a known-red floor, not phase damage, unless a later plan's own change touches that surface.

## User Setup Required

None - no external service configuration required. Playwright's Chromium download used Microsoft's own CDN over TLS via `playwright install`, per the threat model's T-30-02 (accept).

## Next Phase Readiness

- Playwright + Chromium are now installed and usable from `server/.venv/bin/python3` for every subsequent Phase 30 plan's browser-level verification.
- The genuine pre-change CFG-86 baseline (3486px @ 390px / 3505px @ 360px, SHA `606e9819`) is recorded and ready for 30-08 to compare its own post-change reading against — using the same registered instrument, never a restated or rounded number.
- `30-BASELINE.md`'s "After" section is deliberately left `TBD — filled by 30-08`; CFG-86 as a whole requirement remains open until that plan records the after-reading and states the delta and whether X6's 2600px target is met.
- The three pre-existing browser-ux FAILs documented above are a known floor for the rest of this phase's plans; any plan whose own change happens to touch that exact surface should re-evaluate whether its change is responsible before assuming it's the same pre-existing issue.

---
*Phase: 30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-absorbed-sketch-first*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `.planning/phases/30-aspect-rebuilt-one-tile-three-rows-one-palette-the-calendar-/30-BASELINE.md`
- FOUND: commit `8a6e7b0` in `git log --oneline --all`
