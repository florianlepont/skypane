---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 12
subsystem: ui
tags: [i18n, ast, playwright, simple-mode, design-system, audit]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    provides: "20-01: companion/i18n.py/prefs.py/i18n_fr package; 20-03/20-06/20-07/20-09/20-10/20-11: every page rewritten through i18n.t() with its own French catalogue module; the polish commits (thumbnails, health-state language resolution, the Calendar connect placement, registry-label translation)"
provides:
  - "companion/test_i18n.py's ast-based D-08 completeness/dead-translation scanner over the D-05 module set (never importing scanned source, T-20-33), a French render of every page over a real service (Check 3), and D-09's two mechanical copy checks (Check 4)"
  - "companion/test_companion_app.py's 16 end-to-end simple-mode checks (D-30/D-31) over real HTTP"
  - "the design-system skill's record of the status-row primitive, the compact chip, the native-radio segmented control, Display's three supersections, the instant-switch slot, the fused Calendar card, the .rule-row list, and the nav-footer's three switches (D-34)"
  - "18-AUDIT.md marking S-01/S-03/S-05/S-06 fixed (D-35)"
affects: []

tech-stack:
  added: []
  patterns:
    - "call-site-driven i18n completeness scanning: resolve every i18n.t()/t_lang() argument back to a literal via source-order constant folding, for-loop/zip/tuple-unpack position tracing, and .get() fallback resolution — never a blind sweep of every module-level string, which would demand translations for CSS-class dicts and month-abbreviation tables that never reach a translation call"
    - "two-tier exclusion rules: a broad lowercase-identifier/uppercase-code/route filter for a name-convention guess (rule a: direct constants), a narrower hyphenated-only filter for a proven dict-value (rule b), and no identifier filter at all for a value already proven to reach a real t() call (rule c) — the same bare word can be an identifier in one context and real content in another, and only the call-site-traced case has already answered which"

key-files:
  created: []
  modified:
    - companion/test_i18n.py
    - companion/test_companion_app.py
    - companion/layout.py
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/flights.py
    - companion/i18n_fr/home.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/control-density.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
    - .planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md

key-decisions:
  - "The AST scanner's ALL_CAPS name pattern was broadened to permit one or more leading underscores (this codebase's own 'private module constant' convention, e.g. health_page._CORROBORATION_ROWS) — the plan's own literal text named only public ALL_CAPS names, but a large share of this codebase's real translatable content lives in leading-underscore lookup tables, discovered by running the scanner against real source rather than guessing."
  - "companion/app.py was deliberately kept OUT of the AST-scan target set (matching the plan's own D-05 interface, which names only pages/*.py + layout.py + auth.py) even though its own login/404 copy IS real, alive translation — handled instead as a short, documented, named exception list for Check 2, since scanning app.py wholesale pulled in dozens of never-wired flash-message strings and ARIA-role dict values that would have produced false completeness failures."
  - "Rule (b) (dict-value scanning) is gated on proof the dict is actually referenced inside an i18n.t()/t_lang() call (directly, or as a .get() object feeding a tuple-unpack) rather than scanning every ALL_CAPS/leading-underscore dict blindly — this is what keeps CSS-class-lookup dicts (_STATUS_DOT_CLASSES, NAV_ICON_IDS, _AGE_UNIT_SUFFIX_FR) out of the produced set without a per-dict opt-out list."
  - "Fixed two real, pre-existing D-05 gaps the scanner's own Check 1 found on its first run: companion/layout.py's hamburger-toggle aria-label and the nav Health-dot's visually-hidden suffix had never been wrapped in i18n.t() at their own render sites, in any prior plan — both now translate correctly (companion/i18n_fr/nav.py)."
  - "Closed a real D-09 gap Check 4 found on its first run: companion/i18n_fr/home.py's own 'Stale — the server may be down' French value used a plain space instead of U+00A0 before ';' — fixed in place."
  - "Removed 14 catalogue entries from companion/i18n_fr/display.py that the Calendar-card and Flight-colours rebuilds (20-09-PLAN.md) superseded and left behind, confirmed genuinely unreachable by grepping companion/pages/config_page.py for each string before removing it — 20-09-SUMMARY.md's own 'Next Phase Readiness' note had already flagged this cleanup as this plan's to do."
  - "The FR/EN headless sweep paired viewport x theme x language into two profiles (light+French, dark+English) rather than a full cross product, to land on exactly 24 renders (6 pages x 2 viewports x 2 profiles) while still exercising every one of the four named axis values at least once — matching the plan's own stated total."

requirements-completed: [CFG-13, CFG-18]

# Metrics
duration: 65min
completed: 2026-09-12
---

# Phase 20 Plan 12: D-08 completeness harness, simple-mode coverage, the FR/EN sweep, and the phase close Summary

**A mechanical ast-based scanner in `companion/test_i18n.py` that proves every page-module string has a French translation and every translation is actually used, 16 new end-to-end simple-mode checks over real HTTP, a 24-render FR/EN Playwright sweep finding one already-known overflow, and the design-system skill/audit-ledger updates that close out phase 20.**

## Performance

- **Duration:** ~65 min
- **Started:** 2026-09-12T02:51:00Z (approx.)
- **Completed:** 2026-09-12T03:53:00Z
- **Tasks:** 3
- **Files modified:** 11

## Accomplishments
- `companion/test_i18n.py` gained an `ast`-based scanner (never importing the scanned source, T-20-33) that resolves every real `i18n.t()`/`i18n.t_lang()` argument in the D-05 module set back to a literal — direct constants, `for`-loop/`zip()`/tuple-unpack position tracing, `NAME[<int>]` and `.get(key, default)` resolution, plus source-order constant folding for `"a" + OTHER`/`TEMPLATE % (...)` — and enforces two invariants: every such string is a `companion.i18n_fr.CATALOG` key (Check 1), and every `CATALOG` key is produced by that same scan or a short, explicitly documented exception (Check 2). Both failure modes were observed directly (a scratch deletion, a scratch bogus key), not assumed.
- Check 3 renders Home, Display, Device, Flights, Airlines, Health, the login page, the 404 page and the calendar-disconnect confirmation page against a real running service under `lang=fr`, asserting each carries its own French copy with no stray `%s`/`%d`/`{}` artefact. Check 4 is D-09's mechanical half (the typographic apostrophe, the non-breaking space before `:;?!`).
- Fixed two real D-05 gaps and one real D-09 gap the harness's own first run found (layout.py's hamburger label and nav Health-dot suffix had never been wrapped in `i18n.t()`; one home.py French value used a plain space instead of U+00A0), added two genuinely missing catalogue entries, and removed 14 catalogue entries the Calendar/Flight-colours rebuild had superseded and left behind.
- `companion/test_companion_app.py` gained 16 checks driving a real signed-in session with `sp_ui_mode=simple`: the nav's Advanced-group/health-link/device-link/status-dot omission on four tabs while the three nav-footer switches stay present; Home's Health link and Airlines' "Change pictures" button both hidden; Display's two disclosures collapsing to one sentence each; Display's own six everyday groups, `/health`/`/device`'s continued reachability, and Flights/Airlines' full content all confirmed unchanged; the mode surviving three sequential requests; and the exact mirror of every toggled behaviour under `sp_ui_mode=full`.
- Ran the FR/EN headless sweep via the Playwright CLI already present in this environment: 24 renders (6 pages x 2 viewports x light+French/dark+English) found zero CSP violations, zero inline scripts, and exactly one horizontal-overflow cell — the Health page at 390x844 in French, already flagged and being fixed by this wave's own orchestrator polish commits, outside this worktree's file boundary.
- Updated the design-system skill (SKILL.md + two reference files) to describe the status-row primitive, the compact theme chip, the native-radio segmented control, Display's three supersections, the instant-switch slot, the fused Calendar card, the `.rule-row` list, and the nav-footer's three switches — and 18-AUDIT.md now marks S-01/S-03/S-05/S-06 fixed (phase 20), matching S-02/S-04's exact wording.

## Task Commits

1. **Task 1: D-08 completeness/dead-translation harness (companion/test_i18n.py)** - `63960bd` (feat)
2. **Task 2: simple-mode end-to-end coverage (companion/test_companion_app.py) + FR/EN sweep + D-09 catalogue read** - `68b78df` (test)
3. **Task 3: design-system skill update (D-34) and audit record (D-35)** - `ca3c04c` (docs)

_No separate plan-metadata commit — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per this plan's execution instructions._

## Files Created/Modified
- `companion/test_i18n.py` - the full `ast`-based scanner (constant folding, container/binding resolution, five named exclusion rules), Checks 1-4, `EXPECTED_CHECK_COUNT` 11 → 24
- `companion/test_companion_app.py` - Section 5 (16 new checks, simple/full mode over real HTTP), `EXPECTED_CHECK_COUNT` 251 → 267
- `companion/layout.py` - `NAV_TOGGLE_LABEL`/`HEALTH_ALERT_SUFFIX_TEXT` now wrapped in `i18n.t()` at their own render sites
- `companion/i18n_fr/nav.py` - "Open menu" / " — attention needed" added
- `companion/i18n_fr/display.py` - "That link is too long." / "Work day (08:00–18:00)" added; 14 superseded Calendar/Flight-colours entries removed
- `companion/i18n_fr/flights.py` - COLOUR_CAVEAT's own standalone catalogue entry added
- `companion/i18n_fr/home.py` - one French value's plain space before ";" corrected to U+00A0
- `.claude/skills/sketch-findings-skypane/SKILL.md` - "Current as of" moved to phase 20, label voice's seventh member, status-row/Home-hero/nav-footer paragraphs, `.theme-status--nested` note, Folded-In Work entry
- `.claude/skills/sketch-findings-skypane/references/control-density.md` - compact chip and native-radio segmented control entries
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` - Display supersections, instant-switch slot, fused Calendar card, `.rule-row` list
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` - S-01/S-03/S-05/S-06 → fixed (phase 20)

## Decisions Made
See `key-decisions` in the frontmatter above — the broadened ALL_CAPS-with-leading-underscore name pattern, keeping `companion/app.py` out of the scan target set in favour of a documented exception list, gating dict-value scanning on proof of a real `i18n.t()` reference, the two real D-05/D-09 gaps the harness found and fixed, the 14-entry catalogue cleanup, and the paired-profile sweep design.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `companion/layout.py`'s hamburger toggle label and nav Health-dot suffix were never wrapped in `i18n.t()`**
- **Found during:** Task 1, the scanner's own first real run
- **Issue:** `NAV_TOGGLE_LABEL` ("Open menu") and `HEALTH_ALERT_SUFFIX_TEXT` (" — attention needed") were both interpolated via bare `escape_html(CONSTANT)` at their render sites — real, always-visible strings (a hamburger button's accessible name; assistive text appended to the Health nav label) that had silently stayed English-only under every French request since the constants were introduced, undetected because no prior plan's own render check happened to assert their translated text.
- **Fix:** Wrapped both in `i18n.t()` at their one render site each; added both to `companion/i18n_fr/nav.py`.
- **Files modified:** `companion/layout.py`, `companion/i18n_fr/nav.py`
- **Verification:** `companion/test_i18n.py` Check 1 (24/24 overall); a live French render of the sidebar/mobile nav shows "Ouvrir le menu" and " — attention requise".
- **Committed in:** `63960bd` (Task 1 commit)

**2. [Rule 1 - Bug] One French catalogue value used a plain space instead of U+00A0 before ";"**
- **Found during:** Task 1, Check 4's own first real run
- **Issue:** `companion/i18n_fr/home.py`'s "Stale — the server may be down" French value ("Le serveur conserve une copie de chaque image envoyée au cadre ; la plus récente apparaîtra ici.") had a regular ASCII space before ";" — a D-09 violation no prior plan's own review caught, since no check ever asserted the exact character.
- **Fix:** Replaced the space with U+00A0 in place.
- **Files modified:** `companion/i18n_fr/home.py`
- **Verification:** `companion/test_i18n.py` Check 4 (24/24 overall)
- **Committed in:** `63960bd` (Task 1 commit)

**3. [Rule 3 - Blocking] Removed 14 superseded catalogue entries and added 2 missing ones in `companion/i18n_fr/display.py`, outside this plan's own file scope**
- **Found during:** Task 1, Check 2's own first real run
- **Issue:** `companion/i18n_fr/display.py` is not in this plan's declared `files_modified` list, but Check 2 (a hard requirement of this task) genuinely failed against it: 14 entries left behind by 20-09-PLAN.md's Calendar/Flight-colours rebuild (the old one-piece Calendar status sentences, the old "Per-flight colour rules" heading and its disclosure body, the old rules-table "Kind"/"Key"/"Added" headers, etc. — every one confirmed unreachable by grepping `companion/pages/config_page.py` before removing it) and 2 genuinely missing entries (the Notifications URL field's own shorter error, the workday quiet-hours preset's pre-baked label) were both real, mechanical consequences of Check 2's own pass/fail contract, which this plan's own Task 1 cannot satisfy without touching the file that owns them.
- **Fix:** Removed the 14 confirmed-dead entries (documented in the module's own docstring), added the 2 missing ones.
- **Files modified:** `companion/i18n_fr/display.py`
- **Verification:** `companion/test_i18n.py` Check 2 (24/24 overall)
- **Committed in:** `63960bd` (Task 1 commit)
- **Boundary note:** 20-09-SUMMARY.md's own "Next Phase Readiness" section had already flagged this exact cleanup as work for 20-12, so this is expected, scheduled work rather than an out-of-scope surprise.

**4. [Rule 2 - Missing critical] Added `COLOUR_CAVEAT`'s own standalone catalogue entry**
- **Found during:** Task 1, Check 1's own first real run
- **Issue:** `history_page.COLOUR_CAVEAT` is a real, reusable sentence (per its own defining comment) that is currently only ever consumed by concatenation into `LIGHTBOX_NOTE` (which already has its own combined catalogue entry) — Check 1's own literal rule (every scanned constant needs its own key) required a standalone entry too, so a future direct use of the constant is covered without a second translation pass.
- **Fix:** Added the entry to `companion/i18n_fr/flights.py`.
- **Files modified:** `companion/i18n_fr/flights.py`
- **Verification:** `companion/test_i18n.py` Check 1 (24/24 overall)
- **Committed in:** `63960bd` (Task 1 commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing-critical addition, 1 Rule 3 blocking cleanup crossing a nominal file-ownership boundary)
**Impact on plan:** No scope creep — every fix is a direct, mechanical consequence of this plan's own Check 1/Check 2 pass/fail contract, discovered by running the harness this plan itself builds, not a new feature or a different design. Three of the four touch `companion/i18n_fr/display.py`, which 20-09-SUMMARY.md had already scheduled for this plan.

## Issues Encountered

**The AST scanner needed substantially more resolution logic than the plan's own literal `<action>` text described**, discovered by running it against real source rather than trusting the plan's own claim that "every user-visible string ... is an ALL_CAPS module constant or a value in an ALL_CAPS dict." In practice: many real strings live in leading-underscore "private" module constants (health_page.py's `_CORROBORATION_ROWS`, history_page.py's `_HEADERS`), many are bare literals passed directly to `i18n.t()` with no constant at all (`i18n.t("Close")`), and several tuple-of-tuples/dict-of-tuples tables are only ever read via a `for`/`zip()` loop or a `.get(key, DEFAULT)` fallback rather than a plain `NAME` reference. The scanner documented in `companion/test_i18n.py`'s own header comment covers all of these via call-site tracing rather than a blind sweep — validated by actually deleting/adding a scratch catalogue entry and observing the exact failure text, not merely by inspection.

**`companion/app.py` genuinely renders real, alive translations (the login/404 pages) that this plan's own D-05 scan-target interface (`pages/*.py`, `layout.py`, `auth.py`) does not name.** Rather than widen the scan to the whole of `app.py` (which pulled in dozens of never-wired `FLASH_MESSAGES` strings, ARIA-role dict values and argparse `--help` text as false "missing" entries — flash-message translation has no wiring anywhere in this codebase, a pre-existing gap 20-11-SUMMARY.md already documents), those eight specific strings are a short, named, documented exception list in Check 2, exercised directly by Check 3's own login/404 render checks.

**No other issues** — every task's own `<verify>` command passed as specified, and the full local suite (`scripts/run-all-tests.sh`) shows exactly the five pre-existing, documented root-sandbox failures (2 in `server/test_manual_resolutions.py`, 2 in `companion/test_companion_app.py`, 1 in `companion/test_status_pages.py`), identical to `main` and unrelated to this plan's own changes.

## Known Stubs

None — every check, catalogue entry and skill update this plan ships is real and immediately effective; nothing here is a placeholder awaiting a later plan.

## Threat Flags

None beyond this phase's own `<threat_model>` register — all four of its dispositions are pinned exactly as planned: T-20-16 (simple mode is presentation, not access control) by the `/health`/`/device` 200-under-simple-mode checks; T-20-32 (the sweep's own scratch state and screenshots) by the clean `git status --porcelain` this plan's own Task 2 confirmed after the sweep; T-20-33 (the scanner never imports scanned source) by `companion/test_i18n.py`'s own header comment and its exclusive use of `ast.parse()`; T-20-SC (zero packages installed) — the Playwright CLI and Chromium binary already present in this environment were used as-is.

## FR/EN Headless Sweep Matrix (Task 2, D-18)

Ran via `/opt/node22/bin/node` against `playwright-core` (already present in `node_modules`) driving `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, against a copy of the seeded scratch-directory state (never the original), targeting the companion service on a free local port. The sweep script, its JSON output, the state copy and the server log are scratch-directory artifacts only — `git status --porcelain` after the sweep shows no new untracked file outside `.planning/`.

| Page | Viewport | Theme | Lang | Status | `<html lang>` | Overflow | Inline scripts | CSP violation | Console errors |
|---|---|---|---|---|---|---|---|---|---|
| Home | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Display | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Device | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Flights | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Airlines | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Health | 1280x900 | light | fr | 200 | fr | no | 0 | no | 0 |
| Home | 390x844 | light | fr | 200 | fr | no | 0 | no | 0 |
| Display | 390x844 | light | fr | 200 | fr | no | 0 | no | 0 |
| Device | 390x844 | light | fr | 200 | fr | no | 0 | no | 0 |
| Flights | 390x844 | light | fr | 200 | fr | no | 0 | no | 0 |
| Airlines | 390x844 | light | fr | 200 | fr | no | 0 | no | 0 |
| **Health** | **390x844** | **light** | **fr** | 200 | fr | **YES** | 0 | no | 0 |
| Home | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Display | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Device | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Flights | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Airlines | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Health | 1280x900 | dark | en | 200 | en | no | 0 | no | 0 |
| Home | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |
| Display | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |
| Device | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |
| Flights | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |
| Airlines | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |
| Health | 390x844 | dark | en | 200 | en | no | 0 | no | 0 |

The one overflow cell (Health, 390x844, light+French) is the exact French-mobile Health overflow this wave's own `project_specifics` names as concurrently being fixed by the orchestrator on the main tree (`companion/pages/health_page.py`/`companion/i18n_fr/health.py`) — not touched here per this worktree's own file boundary. Every other cell is clean: no CSP violation, no inline script, no console error, anywhere.

## D-35 Handoff — findings.json (out of repo)

`.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` now marks S-01, S-03, S-05 and S-06 as `fixed (phase 20)`. **The audit dashboard's `findings.json` lives outside this repository and could not be edited from this worktree.** The orchestrator (or whoever owns that dashboard) needs to set the same four finding IDs — **S-01** (French localisation), **S-03** (theme picker live preview), **S-05** (battery-low/frame-silent notifications), **S-06** (per-person entry point / simple mode) — to "fixed", matching this plan's own 18-AUDIT.md change.

## User Setup Required

None for this plan's own automated scope. Four items remain genuinely browser-only human checks per this plan's own `<verification>` block (unchanged from the plan, not a gap introduced here):
- The FR/EN sweep is recorded above as an automated matrix (Playwright *was* able to drive a browser in this environment), so the `<human-check>` fallback for that specific item is not needed — but the same block's other three items still are: the native `confirm()` dialog before disconnecting a calendar / removing a rule; a screen reader announcing the three nav-footer switch groups by their `aria-label`s; a real ntfy push arriving on a phone for a battery-low transition, a frame-silent transition, and the "Send a test" button.
- The ten browser-only human checks recorded in `19-VERIFICATION.md` (this phase must not regress them) — no code path this plan touched intersects any of them.

## Next Phase Readiness

- Phase 20 is closed: `companion/test_i18n.py` (24/24), `companion/test_companion_app.py` (265/267, the two documented root-sandbox FAILs), and the full local suite (`scripts/run-all-tests.sh`) all show exactly the five documented root-sandbox failures and nothing else.
- `ruff check .` is clean; `python3 -m compileall -q companion server` passes.
- The D-08 harness this plan ships is what keeps every future phase's own new strings honest against the French catalogue — a hand-kept list can never drift back in, since the scanner reads real source every run.
- The one remaining action item outside this repo is the `findings.json` handoff above — flagged explicitly, not silently assumed done.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: companion/test_i18n.py
- FOUND: companion/test_companion_app.py
- FOUND: companion/layout.py
- FOUND: companion/i18n_fr/nav.py
- FOUND: companion/i18n_fr/display.py
- FOUND: companion/i18n_fr/flights.py
- FOUND: companion/i18n_fr/home.py
- FOUND: .claude/skills/sketch-findings-skypane/SKILL.md
- FOUND: .claude/skills/sketch-findings-skypane/references/control-density.md
- FOUND: .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md
- FOUND: .planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md
- FOUND commit: 63960bd (Task 1)
- FOUND commit: 68b78df (Task 2)
- FOUND commit: ca3c04c (Task 3)
