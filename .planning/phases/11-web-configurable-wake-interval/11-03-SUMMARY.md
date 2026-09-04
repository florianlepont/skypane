---
phase: 11-web-configurable-wake-interval
plan: 03
subsystem: ui
tags: [companion-app, settings-page, html-forms, python-stdlib, input-number]

# Dependency graph
requires:
  - phase: 11-web-configurable-wake-interval (plan 11-01)
    provides: "server/device_config.py's WAKE_INTERVAL_MIN_S/MAX_S, normalise_wake_interval_s(), and save_device_config()'s wake_interval_s keyword"
provides:
  - "companion/pages/config_page.py's wake_interval_group() — the Settings page's fifth .theme-status group, this codebase's first plain <input type=\"number\">"
  - "handle_post()'s explicit string-to-int conversion gate for wake_interval_s, wired into the single existing save_device_config() call"
  - "render()'s wake_interval_env_default ctx-key fallback resolution (consumed by plan 11-04)"
affects: [11-04-web-configurable-wake-interval]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "wake_interval_group() mirrors led_group()'s .theme-status/no-fieldset structure, adapted for a numeric input instead of a checkbox"
    - "value attribute emitted only for an in-range, non-bool int — never a fabricated or out-of-range pre-fill, since an out-of-range native value attribute would fail HTML5 constraint validation and block the whole form's submission"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/test_config_page.py
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .claude/skills/sketch-findings-skypane/references/settings-page-patterns.md

key-decisions:
  - "handle_post() resolves an absent or empty-string wake_interval_s to None (leave unchanged), never a rejection — 11-RESEARCH.md Open Question 2"
  - "The explicit int() conversion happens only in handle_post(), never in wake_interval_group() or render() — quiet_hours_start/end stay string-passthrough while wake_interval_s alone needs the int gate, since it's the only int-typed field on this form"
  - "No CSS changes: the control inherits the existing global input,select 44px floor and input:focus-visible outline with zero new tokens or accent reservations (11-UI-SPEC.md)"

patterns-established:
  - "A fifth .theme-status group can be added to the Settings form by following the fixed sequence: constants block -> group-builder function -> render() wiring (resolve current value, append to template/tuple) -> handle_post() wiring (read form field, resolve to the save_device_config() keyword) -> repair any count-shaped/dict-shape-shaped test assertions the new group breaks by construction"

requirements-completed: []

coverage:
  - id: D1
    description: "The Settings page renders a fifth .theme-status group, Wake interval, last, with a native <input type=\"number\" min=\"60\" max=\"3600\"> carrying the locked heading/caption/placeholder copy"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_wake_interval_group_markup_in_range_value"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_render_places_wake_interval_last_and_resolves_prefill"
        status: pass
    human_judgment: false
  - id: D2
    description: "The input never renders a fabricated or out-of-range value attribute (None/True/False/a str/out-of-bounds ints all emit no value; in-range ints do)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_wake_interval_group_value_attribute_only_for_in_range_non_bool_int"
        status: pass
    human_judgment: false
  - id: D3
    description: "A submitted numeric string is explicitly converted to an int in handle_post() before save_device_config() sees it, and round-trips as an int (not a string)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_handle_post_wake_interval_string_converts_to_int_and_persists"
        status: pass
    human_judgment: false
  - id: D4
    description: "A non-numeric or out-of-bounds submission (\"abc\", \"1.5\", \"59\", \"3601\", \"-1\") returns the existing generic save-failed flash and leaves device_config.json byte-identical"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_handle_post_wake_interval_rejection_paths_byte_identical"
        status: pass
    human_judgment: false
  - id: D5
    description: "An empty-string or absent wake_interval_s in a POST leaves the stored value unchanged (never rejected)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_handle_post_wake_interval_empty_or_absent_leaves_unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "Real-browser visual verification of the rendered Wake interval group against 11-UI-SPEC.md's Interaction Contract (375px/960px, light/dark, spinner legibility, tap target, placeholder tone, dirty-bar wiring, focus ring)"
    verification: []
    human_judgment: true
    rationale: "Requires visual/interaction judgment (native number-input stepper rendering, touch-target feel, focus-ring colour match) that automated checks cannot substitute for. Deferred per workflow.human_verify_mode = end-of-phase — not performed in this plan's execution; recorded as outstanding below."

# Metrics
duration: 8min
completed: 2026-09-04
status: complete
---

# Phase 11 Plan 03: Wake Interval Settings Field Summary

**Added the Settings page's Wake interval field — a fifth `.theme-status` group with this codebase's first native `<input type="number">`, wired into `handle_post()`'s single `save_device_config()` call through an explicit string-to-int conversion gate.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-09-04T06:04:41Z
- **Completed:** 2026-09-04T06:12:31Z
- **Tasks:** 2 completed
- **Files modified:** 4

## Accomplishments
- `wake_interval_group()` renders the fifth Settings group, mirroring `led_group()`'s structure (`.theme-status` wrapper, `<h2>` heading, one caption `<p>`, no `<fieldset>`/`<legend>`), with a plain `<label>` wrapping `<input type="number" name="wake_interval_s" min="60" max="3600">` — bounds read live from `device_config.WAKE_INTERVAL_MIN_S`/`MAX_S`, never re-typed
- The `value` attribute is emitted only for an in-range, non-bool int; every other input (`None`, `True`/`False`, a string, or an out-of-bounds int) renders with no `value` at all, closing off the risk of a fabricated pre-fill blocking the whole form's HTML5 constraint validation
- `render()` resolves the current value from `device_config`'s on-disk `wake_interval_s`, falling back to `ctx["wake_interval_env_default"]` (plan 11-04's future contribution) via an explicit `is None` check
- `handle_post()` reads `form.get("wake_interval_s")`, resolves absent/empty-string to `None` (leave unchanged), and `int()`-converts anything else inside a `try`/`except ValueError` before passing it into the single existing `save_device_config()` call — preserving all-or-nothing rejection across all seven fields
- Repaired the two mechanical harness assertions the new group breaks by construction (the `.theme-status` count 3→4, the five-element dirty-section-order check, and the round-trip dict literal gaining `"wake_interval_s": None"`), then added 6 new checks covering markup, the empty-state guard, `render()`'s placement/pre-fill resolution, the string-to-int conversion, both rejection paths (byte-identical), and the leave-unchanged semantics — harness now at 79/79
- Recorded `<input type="number">` in the `sketch-findings-skypane` design-system skill's touch-target "kept" category and per-task changelog, and brought `settings-page-patterns.md`'s stale four-section enumeration current to six (Quiet hours had already been added by Phase 10 without updating this doc)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add wake_interval_group() and wire it into render()/handle_post()** - `4753ba5` (feat)
2. **Task 2: Add Wake interval page coverage and record the new control shape** - `a203da8` (test)

_Note: Task 2 also modified two design-system skill docs — combined into the same commit as it's the natural single unit of the "record the new control shape" work._

## Files Created/Modified
- `companion/pages/config_page.py` - Adds `WAKE_INTERVAL_SECTION_HEADING`/`_CAPTION`/`_PLACEHOLDER_TEXT` constants, `wake_interval_group()`, and wires the field into `render()`/`handle_post()`
- `companion/test_config_page.py` - Repairs 3 count/dict-shape assertions the new group breaks by construction; adds 6 new checks; bumps `EXPECTED_CHECK_COUNT` 73 → 79
- `.claude/skills/sketch-findings-skypane/SKILL.md` - Records `<input type="number">` in the touch-target register's "kept" category and per-task changelog
- `.claude/skills/sketch-findings-skypane/references/settings-page-patterns.md` - Brings the one-caption-per-section enumeration and caption-constant family current to six sections

## Decisions Made
- Absent/empty-string `wake_interval_s` resolves to `None` (leave unchanged), matching 11-RESEARCH.md's Open Question 2 resolution — an incomplete edit is not an invalid one
- No field-specific error copy: an out-of-bounds or non-numeric submission reuses the existing generic `FLASH_SAVE_FAILED` verbatim, per 11-UI-SPEC.md's Copywriting Contract
- No new CSS: the control inherits the global `input, select` 44px floor and `input:focus-visible` accent outline unmodified — `companion/static/style.css` is byte-identical to before this plan

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Repaired a third count-shaped assertion the plan didn't name**
- **Found during:** Task 1 verification (running the harness after the constants/group/wiring edits)
- **Issue:** Beyond the two assertions the plan explicitly named (the `.theme-status` count and the round-trip dict literal), a third pre-existing check — `render() carries exactly four data-dirty-section elements, in document order` — also broke by construction once Wake interval was wired in as a fifth `data-dirty-section` element. The plan itself anticipated this class of fallout ("repair any further purely-count-shaped or dict-shape-shaped failure the same way").
- **Fix:** Updated the check's expected list from `["Theme", "Runway", "Diagnostic LED", "Quiet hours"]` to the five-element order including `"Wake interval"`, renamed the function/description from "four" to "five", with a comment noting both Phase 10's and this plan's additions.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_config_page.py` — 73/73 pass after Task 1, 79/79 after Task 2
- **Committed in:** `4753ba5` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking, explicitly anticipated by the plan's own instructions)
**Impact on plan:** No scope creep — this was the plan's own named fallback path for count-shaped test breakage, applied to a third instance the plan enumerated only two of.

## Issues Encountered
- The plan's Task 1 acceptance criteria included `grep -c 'save_device_config(' companion/pages/config_page.py` expected to report `1`. The actual (and pre-existing, pre-Phase-11) count is 9 — `git show HEAD~2:companion/pages/config_page.py | grep -c 'save_device_config('` confirms the baseline was already 6 before this plan touched the file, because several docstrings mention `save_device_config()` in prose. The substantive intent — "no second write path was introduced" — holds: `grep -n 'device_config.save_device_config(' companion/pages/config_page.py` still matches exactly one real call site. Not treated as a defect; documented here rather than silently ignored.

## Known Stubs
None — every code path this plan touches is fully wired (no hardcoded empty values, no unwired data sources).

## Threat Flags
None — this plan's threat surface (the `handle_post()` int-conversion gate, the `min`/`max` client-side-only bounds, the interpolated group markup) is exactly what 11-03-PLAN.md's own `<threat_model>` already enumerates (T-11-03-01 through T-11-03-04); no new surface was introduced beyond it.

## User Setup Required

None - no external service configuration required.

## Outstanding Verification

The plan's Task 2 `<human-check>` (real-browser visual verification of the Wake interval group at 375px/960px, light/dark, spinner legibility, tap target, placeholder tone, dirty-bar wiring, and focus ring against `11-UI-SPEC.md`'s Interaction Contract) was **not performed** in this execution, per `workflow.human_verify_mode = end-of-phase` (`.planning/config.json`). It is deferred to the phase-level verification pass rather than this plan's own run. All automated checks (`companion/test_config_page.py` 79/79, `companion/test_companion_app.py` 125/125, `ruff check companion/`, `git diff --quiet companion/static/style.css`) pass.

## Next Phase Readiness
- `companion/app.py` (plan 11-04) can now populate `ctx["wake_interval_env_default"]` — `render()` already reads it as the `None`-fallback pre-fill source, confirmed by this plan's own render-placement/pre-fill-resolution check
- The end-of-phase human-verify pass should cover this plan's Task 2 `<human-check>` alongside plan 11-04's own verification once that plan lands

## Self-Check: PASSED

All claimed files exist on disk and all claimed commit hashes are present in `git log --oneline --all`.

---
*Phase: 11-web-configurable-wake-interval*
*Completed: 2026-09-04*
