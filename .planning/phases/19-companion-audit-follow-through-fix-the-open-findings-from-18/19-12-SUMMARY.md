---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 12
subsystem: ui
tags: [settings-form, device-config, wake-interval, screens-registry, accessibility]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "19-05's companion/wake.py (env_sleep_s()/effective_wake_interval_s()/device_staleness_thresholds()), extended here with its second export next_wake_at_iso(); 19-07/19-10/19-11's config_page.py render()/handle_post() errors/submitted signature and ARIA/aria-describedby helpers, extended here with next_wake_clock threading"
provides:
  - "device_config.RUNWAYS[*]['label'] reads plain English ('Runway 3 (07/25)', 'Runway 4 (06/24)', 'Runway 2 (02/20)'), reverting the French 'Piste N' vocabulary a prior quick task introduced (D-11/A-29)"
  - "device_config gains screen_id as its eleventh persisted key, with normalise_screen_id() and a duplicated-not-imported SCREEN_IDS/DEFAULT_SCREEN_ID pinned equal to companion.screens (D-23 persistence half)"
  - "ctx['screen_id'] and ctx['last_checkin_ts'], both read fresh per request in companion/app.py's page_context(), documented in companion/pages/__init__.py"
  - "config_page.py's conditional _screen_selector_html() (empty for today's single-screen registry, a real <select> for a multi-screen one), a screen_id handle_post() gate, and a Device-page 'Edit artwork' link to /airlines?edit=1 (D-23 UI half, D-22 Device-page half)"
  - "companion/wake.py's next_wake_at_iso(last_checkin_ts, device_cfg) — the one definition of the next-wake arithmetic, with no view dependency — consumed by Home's Frame tile and config_page.py's Display/Device captions plus the Device header (D-13/S-02)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "form=\"{SETTINGS_FORM_ID}\" attribute reuse: _screen_selector_html() lives in the header slot (visually/structurally before <form> opens) but submits with it via the same technique the dirty-bar's out-of-form Save button already established"
    - "_with_next_wake(caption, next_wake_clock): the single implementation appending a suffix at RENDER time, never baked into a caption constant, so a caption reads byte-identical to its own constant whenever the value is unknown"
    - "companion/wake.py stays free of any view/formatting import even though its return value is only ever fed through a clock-text formatter by a caller — each page module formats the ISO string itself"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py
    - server/test_runway_config.py
    - companion/wake.py
    - companion/app.py
    - companion/pages/__init__.py
    - companion/pages/config_page.py
    - companion/pages/home_page.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_view_pages.py

key-decisions:
  - "D-11: only device_config.RUNWAYS[*]['label'] changed — tag_text/empty_heading (the panel-render vocabulary server/plane/render.py uses) are untouched, and server/test_render.py confirms the panel render is undisturbed"
  - "D-23: server/device_config.py duplicates SCREEN_IDS/DEFAULT_SCREEN_ID as literals rather than importing companion.screens, preserving the one-way server/->companion/ dependency direction; a dedicated harness check pins the two equal"
  - "D-23 UI: _screen_selector_html() renders inside the header's action_html slot but submits with the settings form via form=\"{SETTINGS_FORM_ID}\", reusing the dirty-bar Save button's own established off-DOM-submission technique rather than inventing a second one"
  - "D-13: wake.next_wake_at_iso() deliberately imports no view/formatting module — each of its two consumers (home_page.py, config_page.py) formats the ISO string itself via layout.local_clock_text(), keeping wake.py's no-view-dependency rule intact"
  - "D-13: DISPLAY_SECTION_CAPTION deliberately never calls _with_next_wake() — it already states its own honest ~5-minute screen-off latency (12-CONTEXT.md D-01), and appending a wake-interval-derived figure there would contradict that sentence"

requirements-completed: [CFG-01, CFG-04]

# Metrics
duration: ~95min
completed: 2026-09-11
---

# Phase 19 Plan 12: Runway Relabel, Screen-ID Seam, and Next-Wake Display Summary

**Runway picker labels reverted to plain English with the ADP number in parentheses, `device_config` gained a validated `screen_id` eleventh key wired through a conditional (today empty) screen selector and a Device-page Edit-artwork link, and Home/Device now show "Next wake ≈ HH:MM" in Paris local time via a single new `wake.next_wake_at_iso()` function.**

## Performance

- **Duration:** ~95 min (first task commit to last)
- **Started:** 2026-09-11 (worktree base commit `f5ed638`)
- **Completed:** 2026-09-11
- **Tasks:** 3/3 complete
- **Files modified:** 11

## Accomplishments

- Closed A-29 (D-11): the runway cards read "Runway 3 (07/25)", "Runway 4 (06/24)", "Runway 2 (02/20)" — the French "Piste N" vocabulary a prior quick task had introduced is gone from the companion picker, while the physical panel's own `tag_text`/`empty_heading` vocabulary and `server/test_render.py`'s pinned expectations are untouched.
- Closed the A-40 remainder (D-23): `device_config.json` carries a validated `screen_id` key (default `"plane-frame"`), the on-disk persistence half and the UI half (`ctx["screen_id"]`, a conditional `_screen_selector_html()`, and `handle_post()`'s membership-test gate) are both wired end to end, and the duplicated-not-imported `SCREEN_IDS`/`DEFAULT_SCREEN_ID` contract is pinned equal to `companion.screens` by a dedicated harness check.
- Closed the Device-page half of A-39 (D-22): the Device page carries an "Edit artwork" link to `/airlines?edit=1`, built from `layout.AIRLINES_ROUTE` and `airlines_page.EDIT_QUERY_PARAM`, verified end to end against a real running service.
- Closed A-31/S-02 (D-13): a new `companion/wake.py` export, `next_wake_at_iso()`, is the one definition of the "when will the frame next wake up" arithmetic; Home's Frame tile and the Display/Device settings captions (plus the Device header) all show "Next wake ≈ HH:MM" in Paris local time when known, and show nothing at all when the last check-in or the effective wake interval is unknown.

## Task Commits

Each task was committed atomically:

1. **Task 1: Relabel the runways and add the screen_id config key (D-11, D-23 persistence half)** - `26fdc47` (feat)
2. **Task 2: Thread screen_id through ctx, render the conditional selector, and add the Edit artwork link (D-23, D-22)** - `cc45a0b` (feat)
3. **Task 3: Show "Next wake ≈ HH:MM" on Home and Device (D-13, S-02)** - `7bcaff4` (feat)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified

- `server/device_config.py` — `RUNWAYS[*]["label"]` relabelled to English (D-11); `DEFAULT_SCREEN_ID`/`SCREEN_IDS` literals with a duplicated-not-imported comment; `normalise_screen_id()`; `load_device_config()`/`save_device_config()` widened with the `screen_id` key/parameter (D-23)
- `server/test_config_history.py` — 9 full-config-dict literals retargeted with `"screen_id": "plane-frame"`; 4 new checks (hostile-value degrade, write-gate rejection, no-migration-on-read, cross-file registry agreement); `EXPECTED_CHECK_COUNT` 60 → 64
- `server/test_runway_config.py` — 1 new check pinning the English runway labels (no existing check pinned a label literally); `EXPECTED_CHECK_COUNT` 14 → 15
- `companion/wake.py` — new export `next_wake_at_iso(last_checkin_ts, device_cfg)`, imports `datetime`/`timedelta`/`timezone`, no view/formatting import
- `companion/app.py` — `sqlite3`/`wake` imports; `env_wake_interval_default()` delegates its raw read to `wake.env_sleep_s()`, keeping the `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` clamp local; new `_safe_last_checkin_ts()` helper; `page_context()` loads `device_config` once and threads `ctx["screen_id"]`/`ctx["last_checkin_ts"]`
- `companion/pages/__init__.py` — ctx contract documents `screen_id` and `last_checkin_ts`
- `companion/pages/config_page.py` — `EDIT_QUERY_PARAM` import from `airlines_page`; `SCREEN_SELECTOR_ID`/`SCREEN_SELECTOR_LABEL_TEXT`/`EDIT_ARTWORK_LINK_TEXT`/`EDIT_ARTWORK_LINK_CAPTION`/`NEXT_WAKE_HEADER_LABEL`/`NEXT_WAKE_HEADER_VALUE_TEMPLATE`/`NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE` constants; `_screen_selector_html()`, `_edit_artwork_link_html()`, `_next_wake_caption_html()`, `_with_next_wake()` (new); `handle_post()` gains a `screen_id` membership-test gate passed through to `save_device_config()`; `render()` computes `next_wake_clock` once and threads it into `theme_fieldset()`/`runway_fieldset()`/`led_group()`/`quiet_hours_group()`/`wake_interval_group()` and the Device header (display_group()/DISPLAY_SECTION_CAPTION deliberately excluded, D-01)
- `companion/pages/home_page.py` — `wake` import; `NEXT_WAKE_LABEL`/`NEXT_WAKE_VALUE_TEMPLATE` constants; `_status_tiles_html()`'s Frame tile gains a second detail line, omitted entirely when the value is unknown
- `companion/test_config_page.py` — 1 existing full-dict literal retargeted with `screen_id`; 10 new checks across Tasks 2/3; `EXPECTED_CHECK_COUNT` 170 → 176 → 180
- `companion/test_companion_app.py` — 1 new end-to-end HTTP check (Device page Edit-artwork link → `/airlines?edit=1` → artwork forms present); `EXPECTED_CHECK_COUNT` 220 → 221
- `companion/test_view_pages.py` — 2 new checks (`wake.next_wake_at_iso()`'s full contract; Home's conditional next-wake figure); `EXPECTED_CHECK_COUNT` 83 → 85

## Decisions Made

See `key-decisions` in the frontmatter above for the five load-bearing decisions (D-11's panel-render exclusion, D-23's duplicated-not-imported registry, the `form="..."` attribute reuse for the header-slot selector, `wake.py`'s no-view-dependency rule, and `DISPLAY_SECTION_CAPTION`'s deliberate exclusion).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base drift required a `git reset --hard` before any work could begin**
- **Found during:** Setup, before Task 1
- **Issue:** The worktree's initial HEAD (`ddeb34e`) predated the phase's wave-1–5 merges; the expected base commit (`f5ed638`) was not an ancestor. Files this plan needed to read/edit (the D-13/D-23 seams from plans 19-05/19-07/19-10/19-11) were missing entirely at that HEAD.
- **Fix:** Verified HEAD was on the `worktree-agent-*` namespace (not a protected ref) and the working tree was clean, then ran `git reset --hard f5ed638` — the documented, sanctioned recovery path.
- **Files modified:** None (git-level correction only).
- **Verification:** `git rev-parse HEAD` afterward matched `f5ed638`; all subsequently-read files matched the plan's own line-number references.
- **Committed in:** N/A (pre-work setup, not a code change)

---

**2. [Rule 1 - Bug] A leftover "Piste" substring in a rewritten comment tripped the plan's own literal grep**
- **Found during:** Task 1
- **Issue:** The rewritten `RUNWAYS` comment block quoted the superseded French label ("Piste N") for context, which the plan's acceptance criterion `grep -c '"Piste' server/device_config.py` (expected `0`) correctly flagged.
- **Fix:** Reworded the comment to describe the superseded vocabulary without quoting the literal string.
- **Files modified:** `server/device_config.py` (pre-commit).
- **Verification:** `grep -c '"Piste' server/device_config.py` returns `0`.
- **Committed in:** `26fdc47` (caught and fixed before this commit, not a separate commit)

---

**3. [Rule 1 - Bug] A leftover "companion.layout" substring in `wake.py`'s own docstrings tripped the plan's own literal grep**
- **Found during:** Task 3
- **Issue:** The plan's acceptance criterion `grep -c "companion.layout\|import layout" companion/wake.py` (expected `0`) exists to prove `wake.py` carries no view dependency, but an early draft's own PROSE (explaining why the module carries no such dependency) quoted `companion.layout.local_clock_text()` by name three times, which the literal grep correctly flagged.
- **Fix:** Reworded the docstrings to describe the formatter generically ("a clock-text formatter") without naming the module.
- **Files modified:** `companion/wake.py` (pre-commit).
- **Verification:** `grep -c "companion.layout\|import layout" companion/wake.py` returns `0`.
- **Committed in:** `7bcaff4` (caught and fixed before this commit, not a separate commit)

---

**4. [Rule 1 - Bug] A test's expected caption/clock literal did not go through `escape_html()`, and a caption was checked against the wrong scope**
- **Found during:** Task 3
- **Issue:** Two new `test_config_page.py` checks initially compared the raw (unescaped) caption constants against rendered HTML — several captions contain an apostrophe (e.g. "the device's"), which `escape_html()` renders as `&#x27;`, so the raw string never appears verbatim; separately, `DISPLAY_SECTION_CAPTION`'s own check queried the Device scope, but `GROUP_DISPLAY` is an everyday group that only renders on the Display scope.
- **Fix:** Both checks now build their expected literal through `escape_html()` before comparing, and the `DISPLAY_SECTION_CAPTION` check queries `SCOPE_DISPLAY`.
- **Files modified:** `companion/test_config_page.py` (pre-commit).
- **Verification:** `companion/test_config_page.py` 180/180.
- **Committed in:** `7bcaff4` (caught and fixed before this commit, not a separate commit)

---

**5. [Rule 1 - Bug] A Home-page test's expected clock literal did not account for the Europe/Paris DST offset**
- **Found during:** Task 3
- **Issue:** A new `test_view_pages.py` check computed its expected "Next wake" clock value in UTC (`12:10`) rather than Europe/Paris local time (`14:10`, CEST/UTC+2 in late August), which `layout.local_clock_text()` correctly renders — the fixture's own comment now records the arithmetic.
- **Fix:** Corrected the expected literal to `14:10` with an explanatory comment.
- **Files modified:** `companion/test_view_pages.py` (pre-commit).
- **Verification:** `companion/test_view_pages.py` 85/85.
- **Committed in:** `7bcaff4` (caught and fixed before this commit, not a separate commit)

---

**Total deviations:** 1 pre-work git-level correction (worktree base drift), 4 pre-commit self-catches (all caught and fixed before any commit, none required more than one correction). No scope creep — every fix stayed confined to the exact file/function the plan was already touching.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- This is the last plan of Phase 19. `PYTHON=$(command -v python3) bash scripts/run-all-tests.sh` reports exactly the three pre-existing-failure harnesses an untouched checkout also reports (`server/test_manual_resolutions.py` 21/23, `companion/test_companion_app.py` 219/221, `companion/test_status_pages.py` 190/191 — all read-only-directory/`anomaly_active()` root-sandbox artifacts, unrelated to this plan) — zero new failures.
- Every touched harness's `EXPECTED_CHECK_COUNT` was re-derived by running it: `server/test_config_history.py` 64/64, `server/test_runway_config.py` 15/15, `companion/test_config_page.py` 180/180, `companion/test_view_pages.py` 85/85, `companion/test_companion_app.py` 219/221 (documented), `server/test_render.py` 134/134 (panel render untouched).
- The end-of-phase `<human-check>` (runway cards read "Runway 3 (07/25)" etc.; Home shows "Next wake ≈ HH:MM" in Paris local time and shows nothing when the frame has never checked in; the Device page's "Applies on the next scheduled poll" captions carry the same figure; the Device page's "Edit artwork" link opens Airlines with the artwork forms available; no screen selector is visible with one registered screen type) is still outstanding — deferred to `/gsd:verify-work` per this plan's own verification section.
- No blockers for `/gsd:verify-work`. The screens seam (`screen_id`) is now fully plumbed end to end — a future plan adding a second screen type only needs to add a `companion/screens.py` registry entry plus its groups; no further `server/device_config.py`, `companion/app.py`, or `companion/pages/config_page.py` plumbing is needed.

## Threat Flags

None — every new surface this plan introduces (the `screen_id` config key and its `<select>`, the Edit-artwork link, the next-wake figures/caption suffixes) was already named in the plan's own `<threat_model>` (T-19-11, T-19-44, T-19-45, T-19-27, T-19-08, T-19-46, T-19-24) and is covered by the harness checks above; no new network endpoint, auth path, file-access pattern, or schema change beyond the additive `screen_id` key was added.

## Self-Check: PASSED

- FOUND: server/device_config.py
- FOUND: server/test_config_history.py
- FOUND: server/test_runway_config.py
- FOUND: companion/wake.py
- FOUND: companion/app.py
- FOUND: companion/pages/__init__.py
- FOUND: companion/pages/config_page.py
- FOUND: companion/pages/home_page.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND: companion/test_view_pages.py
- FOUND commit 26fdc47 (feat(19-12): relabel runways to English and add screen_id config key)
- FOUND commit cc45a0b (feat(19-12): thread screen_id through ctx and add the Edit artwork link)
- FOUND commit 7bcaff4 (feat(19-12): show "Next wake ~ HH:MM" on Home and Device (D-13/S-02))

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 12*
*Completed: 2026-09-11*
