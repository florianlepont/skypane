---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 03
subsystem: ui
tags: [python, health-page, i18n, resolution-stats, honest-state-reporting]

# Dependency graph
requires:
  - phase: 22-01
    provides: the D-02 Playwright browser harness and its dev-only CI wiring (not consumed directly by this plan, but this plan's wave depends on 22-01 having landed first)
provides:
  - "companion.pages.health_page._pipeline_never_ran()/_pipeline_timestamp_only(): the never-ran-vs-overdue split and the verdict-free pipeline detail fragment"
  - "compute_health_state()'s new `pipeline_detail_html` key, mirroring `device_detail_html`, for Home (22-07) to render without re-embedding pipeline_html whole"
  - "PIPELINE_STATE_TEXT['off'] / the reused `dot--off` neutral-state vocabulary for a pipeline that has never run"
  - "resolution_stats()'s widened total (every route_source row, unknown values bucketed as 'Other') and _stats_section_html()'s conditional omission of the whole 'How well we name flights' card when empty"
affects: [22-07, 22-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Reuse an existing state token from the app's own vocabulary (\"off\", already defined for Screen off/Quiet hours off) rather than inventing a new status token or CSS class for a new neutral state"
    - "Verdict-free detail fragment as its own function (_pipeline_timestamp_only mirroring _device_timestamp_only), consumed both by the tile's own render and by the health-state dict Home reads"
    - "Whole-card conditional omission (not just an empty inner body) when a nested page-section has nothing to show"

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/test_status_pages.py

key-decisions:
  - "The never-ran pipeline state reuses the literal token \"off\" (companion/static/style.css's own pre-existing dot--off vocabulary, defined as 'a neutral, everyday state ... never a problem') rather than adding a new status token or a fifth dot colour -- layout.py's _STATUS_DOT_CLASSES/_STAT_TILE_BORDER_CLASSES are untouched (out of scope for this plan) and already default an unrecognised state to a safe fallback (stat-tile--accent for the border), so the tile's dot span is hand-built directly with the literal 'dot dot--off' classes rather than routed through layout.status_dot(), whose own documented fallback for an unrecognised state is the WARN class -- calling it here would print the exact 'dot--warn' token this fix removes"
  - "collect_anomalies()/overall_severity() explicitly treat pipeline_state='off' identically to 'ok' (an added membership-check exemption), not merely relying on it falling outside 'warn'/'error' -- collect_anomalies()'s own check was an inverted `!= 'ok'` that would otherwise still flag a never-ran pipeline as an anomaly even though overall severity computed 'ok'"
  - "The never-ran pipeline tile renders no second 'Last aircraft detected' line at all (rather than rendering it with a fallback) -- last_detection is falsy by the never-ran condition's own definition, so that line would always print the battery module's 'no reading yet' fallback, which is exactly the vocabulary leak B2 removes"
  - "resolution_stats()'s new 'Other' bucket is a value appended to `rows`, not folded into `_SOURCE_ROWS` -- that tuple is this page's fixed, documented enumeration of known resolution mechanisms, and adding an 'unknown' catch-all to it would misrepresent it as a sixth mechanism this page actually understands"
  - "_stats_section_html()'s omission is scoped to `stats['total'] == 0` only, not to the `_DB_UNAVAILABLE` sentinel -- a database read failure is a different, out-of-scope failure mode (D-11's pre-existing independent-degradation contract for this card), left rendering exactly as it did before this task"

requirements-completed: []  # CFG-30 is served by nine plans (D-07's B2-B18/X3-X9); NOT complete after this one alone.

# Metrics
duration: ~40min
completed: 2026-09-12
---

# Phase 22 Plan 03: Health tells the truth about the flight pipeline (B2/B3) Summary

**The Flight-data tile now distinguishes "never ran" from "overdue" (a real neutral `dot--off` state, never battery-borrowed vocabulary), publishes a verdict-free `pipeline_detail_html` for Home, and the naming-statistics card counts every row (unknown `route_source` bucketed as "Other") or disappears entirely when the window is empty.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-09-12T21:09:00Z (approx.)
- **Completed:** 2026-09-12T21:47:00Z
- **Tasks:** 2 completed
- **Files modified:** 3 (all pre-existing; no new files)

## Accomplishments

- **Task 1 (B2):** `health_page._pipeline_never_ran(pipeline_ts, last_detection)` is a two-input predicate — no `META_LAST_PIPELINE_RUN` AND no `META_LAST_DETECTION` — that lets `_pipeline_section()` branch to a genuinely neutral state before `staleness_status()` (unchanged, still `age is None -> "warn"` for every other caller) ever runs. That branch renders `PIPELINE_STATE_TEXT["off"]` ("No detection yet") with a hand-built `<span class="dot dot--off">` — reusing the app's pre-existing neutral-dot CSS rather than adding a new status token, a fifth dot colour, or touching `companion/layout.py` (out of scope for this plan) — and `PIPELINE_NEVER_RAN_DETAIL_TEXT` ("The frame has not reported a flight since it started.") in place of the second "Last aircraft detected" line, which is omitted entirely rather than rendering its own guaranteed battery-vocabulary fallback. `_pipeline_timestamp_only()` mirrors `_device_timestamp_only()` for the pipeline signal and is now what `compute_health_state()` publishes as `pipeline_detail_html`, verdict-free, for Home to consume without re-embedding `pipeline_html` whole. `collect_anomalies()`/`overall_severity()` gained an explicit `pipeline_state == "off"` exemption (treated exactly like `"ok"`), so a never-ran pipeline can never trip the anomaly banner even alongside an unrelated real problem.
- **Task 2 (B3):** `resolution_stats()`'s total now sums every row `history_db.route_source_counts()` returns, not only the five `_SOURCE_ROWS` keys — a NULL, empty, or otherwise unrecognised `route_source` used to silently vanish from both the total and the table. Anything outside the five known keys folds into one additional "Other" row (ordinary words, its own one-sentence gloss, no developer-facing identifier), appended only when non-zero, so an ordinary render with only known sources is byte-identical to before this task. `_stats_section_html()` now omits the whole "How well we name flights" `<section>` — heading, card, everything — when `stats["total"] == 0`, rather than the pre-existing bug of an unconditional heading over `_stats_table_html()`'s own empty string; the `_DB_UNAVAILABLE` sentinel is deliberately excluded from this omission (a different, out-of-scope failure mode, left rendering as before). The Resolution-rate tile's empty copy is replaced with wording that names the window ("No flights in the last %d days" / "The frame has not recorded a detection in this window. It will appear here after the next wake."), interpolating `RESOLUTION_WINDOW_DAYS` rather than a hard-coded "30".
- Every new/changed string shipped its French counterpart in the same commit as its English source (`companion/i18n_fr/health.py`), verified by `test_i18n.py`'s dead-translation scan (22/22 checks pass, no orphaned key in either direction).

## Task Commits

1. **Task 1: A real neutral never-ran state, and a verdict-free pipeline detail for Home** - `6254be8` (fix)
2. **Task 2: Count every row, bucket the unknown, and stop rendering an empty card** - `6f620da` (fix)

_Note: no TDD-mode gate applies to this plan (`tdd_mode: false` in project config) — each task's own new checks were written and run before commit, not as a separate RED/GREEN pair._

## Files Created/Modified

- `companion/pages/health_page.py` — `_pipeline_never_ran()`, `_pipeline_timestamp_only()`, `_pipeline_section()`'s never-ran branch, `PIPELINE_STATE_TEXT["off"]`, `PIPELINE_NEVER_RAN_DETAIL_TEXT`, `compute_health_state()`'s new `pipeline_detail_html` key, `collect_anomalies()`'s "off" exemption (Task 1); `resolution_stats()`'s widened total/"Other" bucket, `_OTHER_SOURCE_LABEL`/`_OTHER_SOURCE_GLOSS`, `_NO_STATS_HEADING`/`_NO_STATS_BODY`'s windowed copy, `_stats_section_html()` (Task 2)
- `companion/i18n_fr/health.py` — French entries for "No detection yet" / the never-ran detail sentence (Task 1); the windowed empty-state copy and "Other"/its gloss (Task 2)
- `companion/test_status_pages.py` — 5 new Task 1 checks (never-ran tile in EN/FR, `pipeline_detail_html` verdict-free for both never-ran and has-run, `collect_anomalies()`/`overall_severity()`'s "off" exemption) plus 1 existing check retargeted (`PIPELINE_STATE_TEXT`'s expected key set); 5 new Task 2 checks (unknown-source "Other" bucketing, known-sources-only byte-identical, empty section absent in both languages, a 36-row fixture, the window-derivation guard) plus 6 existing checks retargeted in place (two fixtures gained a seeded `route_source` row to keep exercising a now-conditionally-omitted card; two seeded/unseeded loops narrowed their per-fixture heading set; one slice boundary moved to end-of-document; one "always five headings" assumption became a per-fixture count). `EXPECTED_CHECK_COUNT`: 218 → 223 (Task 1) → 228 (Task 2), each re-derived by running the harness, not by arithmetic.

## Decisions Made

See `key-decisions` in the frontmatter above — five decisions, all scoped to staying inside this plan's `files_owned` boundary (`companion/layout.py`, `companion/pages/home_page.py`, `companion/static/style.css`, `server/wake.py` untouched) while still reusing existing, already-styled vocabulary rather than inventing new tokens.

## Deviations from Plan

None — plan executed exactly as written. All auto-fixes below are Rule 1/Rule 2 corrections the plan's own task text explicitly called for (the retargeted existing checks were named in the plan's own "Record in the SUMMARY any existing check that had to be retargeted rather than added" instruction, not an unplanned deviation).

### Retargeted existing checks (explicitly anticipated by the plan)

Task 2's own action text asked for this to be recorded: six existing `test_status_pages.py` checks needed a small fixture or assertion change because `_stats_section_html()`'s new omit-when-empty behavior changed what an unseeded fixture renders. None of the six checks' own *subject* changed — only what a zero-row fixture now produces:

1. `_quick_260902_gjj_card_status_borders_render_correct_modifiers` — seeded one `route_source="fresh_hit"` runway event so the Resolution-statistics card (whose "no status modifier" assertion is this check's actual subject) still renders.
2. The nested-heading-tier check (quick task 260901-uzi finding 4, Check 2) — same fixture fix, same reason.
3. The two-tier-hierarchy check (quick task 260902-iag Task 3) — its `seeded in (False, True)` loop's `seeded=False` pass now checks `STATS_SECTION_HEADING`'s *absence* instead of joining the per-heading card-class loop, since that fixture seeds no runway_events.
4. The heading-to-content-rhythm check (quick task 260902-bl2 Task 3, Check 2) — same loop-narrowing fix as #3.
5. `_no_chrome_with_no_data_and_no_cross_page_leak` (quick task 260903-ghy Task 2, Check D) — its slice boundary, previously anchored on the now-absent stats heading, moved to end-of-document.
6. `_health_page_tile_icons_only_no_glyph_in_any_heading` (quick task 260902-j8w) — its hardcoded "always five headings" expectation became an explicit per-fixture count (4, since neither of its two fixtures seeds a runway_event).

Plus one Task 1 retarget: `_state_text_dicts_have_expected_key_sets` — `PIPELINE_STATE_TEXT`'s expected key set widened from `{ok, warn, error}` to `{ok, warn, error, off}` (`DEVICE_STATE_TEXT`/`CORROBORATION_STATE_TEXT` untouched).

**Total deviations:** 0 unplanned. 7 checks retargeted in place (all anticipated/instructed by the plan's own task text), 10 new checks added.
**Impact on plan:** None beyond what the plan itself specified. No scope creep.

## Issues Encountered

**Git history reconstruction for atomic per-task commits.** Both tasks' source edits were made in one continuous pass before the first test run (health_page.py's Task 1 and Task 2 regions don't overlap, but I hadn't committed between them). To honor "one commit per task" I reconstructed the sequence: saved the final (both-tasks) file contents, reverted every Task 2 edit back to its pre-Task-2 text (health_page.py, i18n_fr/health.py, test_status_pages.py), reran the harness to confirm the Task-1-only intermediate state matched its own predicted count exactly (222/223), committed Task 1, then restored the saved final contents byte-for-byte (verified with `diff -q`), reran the harness to confirm it matched the original combined-state count (227/228), and committed Task 2. No content was lost or altered in the process — both `diff -q` checks against saved copies confirmed exact reconstruction at each step.

## Verification Detail — Did Every Acceptance Criterion Evaluate As Predicted?

Per the plan's critical constraint 4/5: every acceptance criterion was run for real, not assumed.

- `grep -c "pipeline_detail_html" companion/pages/health_page.py` → **2+** (computed via `_pipeline_timestamp_only()` call in `compute_health_state()`, published as a dict key) — matches.
- A never-ran render: zero `dot--warn` occurrences and zero `"no reading yet"`/French-fallback occurrences in the pipeline tile, in both languages — confirmed by the two new never-ran tile checks (EN/FR).
- `companion/test_status_pages.py` reports M/M at its new pin apart from the documented `anomaly_active()` FAIL — confirmed: 222/223 after Task 1, 227/228 after Task 2, in both cases the *only* failing check is `anomaly_active()`'s own root-sandbox case (verified by name, not just count — see below).
- `companion/test_i18n.py` exits 0, no orphaned-key failure — confirmed, 22/22 both before and after Task 2's catalogue edits.
- `ruff check .` clean — confirmed after each task's edits.
- A render with zero in-window rows: zero occurrences of `STATS_SECTION_HEADING` in both languages — confirmed by `_stats_section_absent_when_empty_both_languages`.
- A render with an unknown `route_source`: total equals the row count — confirmed by `_resolution_stats_counts_unknown_route_source_as_other` (3 rows: 1 known + 1 NULL + 1 unrecognised string, total == 3).
- `grep -c '"30"\|>30<' companion/pages/health_page.py` shows no new hard-coded window literal in visible copy — confirmed: `_NO_STATS_HEADING` is the unformatted template `"No flights in the last %d days"`, pinned by its own new check.

**No acceptance criterion evaluated differently than the plan predicted.** Nothing needed to be flagged as a bad criterion (unlike 22-02's executor, which the plan cited as the model for that situation) — every command here returned exactly what the plan's text stated it would.

## Root-sandbox Failure Check (Critical Constraint 6)

Ran `PYTHON=.../python bash scripts/run-all-tests.sh` after both commits: exactly 3 harnesses fail (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`), and each failing check's own name/message was inspected — all match the documented read-only-directory root-sandbox cases named in the plan (`ADD_FAILED`/`manual_save_failed`/`manual_delete_failed` flows expecting a write failure that cannot trip as root, and `test_status_pages.py`'s own `anomaly_active()` case). None of these three harnesses were touched by this plan's changes. No new failure was introduced or masked.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- `pipeline_detail_html` is ready for plan 22-07 (Home) to consume in place of re-embedding `pipeline_html`.
- Health's own tile anatomy (X8, one tile anatomy, neutral empty states body-sized) is plan 22-12's job — this plan's `_stats_section_html()`/pipeline-tile changes did not touch shared tile anatomy beyond what B2/B3 required.
- No blockers for the rest of Phase 22's wave 2/3 plans.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-12*

## Self-Check: PASSED

- FOUND: `.planning/phases/22-companion-audit-round-4-fix-the-blocking-display-save-bar-co/22-03-SUMMARY.md`
- FOUND: commit `6254be8` (Task 1)
- FOUND: commit `6f620da` (Task 2)
