---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
plan: 07
subsystem: api
tags: [http-server, forms, server-side-validation, config-persistence]

# Dependency graph
requires:
  - phase: 06-companion-configuration-web-interface-visual-settings-view-s
    provides: "server/device_config.py's THEMES/RUNWAYS registries + save_device_config() (06-01); companion/app.py's route table, page_context(), and companion/pages/config_page.py's contract-complete stub (06-05); companion/layout.py's escape_html()/page_shell() (06-04)"
provides:
  - "companion/pages/config_page.py — the real, live CFG-01 theme picker and CFG-12 runway picker, both rendered from server.device_config's own registries with the current value pre-selected"
  - "handle_post() — server-side registry-membership validation (never normalise_*, which is the read path's forgiving default-fallback), whole-submission rejection on any non-member field, and the D-07 confirmation on success"
  - "companion/app.py's page_context() gains poll_cooldown_remaining; the four flash-key string literals now live once, in config_page.py, referenced by app.py rather than restated"
  - "companion/test_config_page.py — 15 checks (14 unit + 1 real HTTP round trip)"
affects: [06-10, 06-11, 06-12]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A page module exposes its own module-level flash-key constants and the router imports them (rather than the router defining its own literals) — the flash-key strings live in exactly one place, in the page module that knows what they mean"
    - "ctx keys computed by companion/app.py's page_context() but only consumed by one page module (poll_cooldown_remaining) are added there rather than the page module importing companion/app.py, which would be a cycle"
    - "handle_post() validates with an explicit membership test against the registry's own key tuple, never the read path's normalise_*() fallback helpers — a write of an unrecognised value is a reportable client error, not a value to silently coerce"

key-files:
  created:
    - companion/test_config_page.py
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/pages/__init__.py

key-decisions:
  - "config_page.render() does not itself compose the flash banner, despite the plan's action text describing render(ctx) as composing 'the flash banner when ctx[\"flash\"] is set': companion/app.py's do_GET /config route (shipped in 06-05, unchanged and already tested) builds and passes the flash banner to layout.page_shell() as a shell-level concern, uniformly for all five tabs. Having config_page.render() also emit a banner would double-render it on every real page load. The banner-appears-after-save requirement is instead proven by this plan's own end-to-end HTTP check, which exercises the real save -> redirect -> re-render path exactly as a browser would."
  - "The poll-trigger cooldown's disabled-button copy ('Poll triggered recently — try again in {n}s.') is defined as its own module constant in config_page.py rather than imported from companion/app.py's FLASH_MESSAGES — importing app.py from a page module would be a cycle (app.py already imports config_page.py). The two literal copies are independent rendering sites for the same UI-SPEC row (one is the button-adjacent static copy, the other is the post-redirect flash banner) and were not unified into one shared string."

patterns-established:
  - "Registry-backed forms: a fieldset's radio inputs are built by iterating the registry's own *_IDS tuple in order, so adding a registry entry (Phase 7's future themes) requires zero page-module changes."

requirements-completed: [CFG-01, CFG-07, CFG-12]

coverage:
  - id: D1
    description: "The Config page's Theme fieldset renders one radio per server.device_config.THEMES entry (one today) with the currently-saved theme pre-selected and D-11's helper text verbatim; the Runway fieldset renders exactly three radios with the currently-saved (non-default) runway pre-selected and CFG-12's helper text verbatim."
    requirement: "CFG-01"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#render() emits exactly two fieldsets and a Save Settings submit button; #theme_fieldset() emits one radio per THEMES registry entry; #runway_fieldset() emits exactly three runway radio inputs; #the theme and runway helper texts both appear escaped-verbatim in render()'s output; #the currently-saved theme and (non-default) runway are the ones marked selected"
        status: pass
    human_judgment: false
  - id: D2
    description: "The CFG-07 manual poll-trigger button renders enabled at zero cooldown and disabled with the remaining-seconds copy otherwise, sourced from a poll_cooldown_remaining ctx key companion/app.py's page_context() now computes."
    requirement: "CFG-07"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#poll_trigger_section(0) renders an enabled button; #poll_trigger_section(17) renders a disabled button and the remaining-seconds copy"
        status: pass
    human_judgment: false
  - id: D3
    description: "handle_post() validates the submitted theme and runway against device_config.THEME_IDS/RUNWAY_IDS via an explicit membership test before either value is used anywhere; a non-member value on either field rejects the whole submission (device_config.json stays byte-identical) and reports the save-failure flash key; an absent field carries the current on-disk value forward; a save-layer OSError reports the same failure key instead of propagating."
    requirement: "CFG-12"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#a post with a valid theme and runway writes both and returns the saved flash key; #a post with a non-member theme writes nothing...; #a post with a non-member runway writes nothing...; #a post with a theme but no runway field carries the existing runway forward unchanged; #a post with a directory-traversal-shaped theme value is rejected...; #a post with a SQL-fragment-shaped theme value is rejected...; #a save that raises OSError returns the save-failure flash key rather than propagating"
        status: pass
    human_judgment: false
  - id: D4
    description: "A successful save shows D-07's mandatory verbatim confirmation copy ('Saved — will apply on the frame's next scheduled refresh.') on a real HTTP response, and the newly-saved runway is shown selected on that same re-rendered page — proving the router, config_page.py, and device_config.py's persistence layer agree end to end."
    requirement: "CFG-01"
    verification:
      - kind: e2e
        ref: "companion/test_config_page.py#a real HTTP save round trip shows D-07's confirmation copy and the newly-saved runway selected"
        status: pass
    human_judgment: false

# Metrics
duration: ~40min
completed: 2026-08-28
status: complete
---

# Phase 6 Plan 07: Config Page — Theme/Runway Save + Poll Trigger Summary

**`companion/pages/config_page.py`'s theme and runway pickers are now real and server-validated: radios render from `server.device_config`'s own registries, `handle_post()` rejects any non-member value with a whole-submission failure (never a silent normalise-to-default), and a successful save shows D-07's mandatory verbatim confirmation on a real HTTP response.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3
- **Files modified:** 3 (`companion/pages/config_page.py`, `companion/app.py`, `companion/pages/__init__.py`)
- **Files created:** 1 (`companion/test_config_page.py`)

## Accomplishments

- `theme_fieldset()`/`runway_fieldset()` iterate `device_config.THEME_IDS`/`RUNWAY_IDS` in registry order, marking the currently-saved id selected and carrying D-11's theme helper text and CFG-12's runway helper text verbatim (escaped through `layout.escape_html()`, the only escaping call site in this module).
- `poll_trigger_section(cooldown_remaining)` renders the CFG-07 trigger enabled at zero cooldown or `disabled` with the remaining-seconds copy otherwise — sourced from a new `poll_cooldown_remaining` key `companion/app.py`'s `page_context()` now computes (reusing its own existing `poll_cooldown_remaining()` function), so `config_page.py` never has to import `companion/app.py` itself.
- `handle_post(form, ctx)` validates the submitted `theme`/`tracked_runway` fields with an explicit membership test against `device_config.THEME_IDS`/`RUNWAY_IDS` — deliberately never `normalise_theme_id()`/`normalise_runway_id()`, which implement the *read* path's forgiving default-fallback, not a write-path validator. Either field present-but-non-member rejects the whole submission (proven byte-identical against a directory-traversal payload and a SQL-fragment payload); an absent field carries the current on-disk value forward via `save_device_config()`'s own `None`-means-unchanged contract; a `ValueError`/`OSError` from the save layer reports the failure key instead of propagating.
- The four flash-key strings (`FLASH_SAVED`/`FLASH_SAVE_FAILED`/`FLASH_POLL_TRIGGERED`/`FLASH_POLL_COOLDOWN`) now live once, as module constants in `config_page.py`; `companion/app.py`'s pre-existing `FLASH_KEY_*` names reference them instead of restating the literals, so D-07's confirmation sentence exists exactly once in the repository outside `.planning/` (in `app.py`'s `FLASH_MESSAGES` mapping).
- `companion/test_config_page.py`: 15 checks — 14 unit checks (fieldset shape/selection/helper-text, poll-trigger enabled/disabled states, valid save, non-member theme/runway rejection, partial-field carry-forward, two adversarial payloads, an `OSError`-from-save non-propagation check) plus one end-to-end check that launches the real `companion/app.py` subprocess, logs in, posts a valid theme/runway pair, follows the redirect, and asserts D-07's confirmation copy and the newly-saved runway both appear on a real HTTP response.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build the theme and runway fieldsets and the GET render** - `0d2a603` (feat)
2. **Task 2: Implement handle_post with server-side registry validation and the D-07 confirmation** - `e5bbef3` (feat)
3. **Task 3: Create companion/test_config_page.py** - `a57ec74` (test)

**Plan metadata:** (this commit)

_Note: Tasks 1 and 2 are marked `tdd="true"` in the plan, but the plan's own Task 3 is what creates `companion/test_config_page.py` — no prior test file existed for those tasks to extend. Genuine RED/GREEN verification was still performed for both: the harness (all 15 checks, covering every Task 1 and Task 2 behavior bullet) was written and run against a temporarily-reverted Task-1-only implementation (RED — the fieldset/selection checks failed against the pre-06-07 stub), then against the completed Task 1 implementation with Task 2's `handle_post()` still stubbed (GREEN for Task 1's checks, expected-fail for Task 2's), then against the full implementation (GREEN, 15/15). The test file itself is committed once, in Task 3, as its own atomic `test(...)` commit, matching the plan's own task boundary — but the RED/GREEN discipline was applied to the underlying behavior across both prior commits, not skipped._

## Files Created/Modified

- `companion/pages/config_page.py` - `theme_fieldset()`, `runway_fieldset()`, `poll_trigger_section()`, `render(ctx)` (completed), `handle_post(form, ctx)` (completed), `THEME_HELPER_TEXT`, `RUNWAY_HELPER_TEXT`, `POLL_COOLDOWN_HELPER_TEXT`, `FLASH_SAVED`, `FLASH_SAVE_FAILED`, `FLASH_POLL_TRIGGERED`, `FLASH_POLL_COOLDOWN`
- `companion/app.py` - `page_context()` gains a `poll_cooldown_remaining` key; `FLASH_KEY_SAVED`/`FLASH_KEY_SAVE_FAILED`/`FLASH_KEY_POLL_TRIGGERED`/`FLASH_KEY_POLL_COOLDOWN` now reference `config_page`'s own constants instead of restating the literal strings
- `companion/pages/__init__.py` - the `ctx` dict's documented key list gains `poll_cooldown_remaining`
- `companion/test_config_page.py` - `Harness`, `http_request()`, `_login()`, `_write_device_config()`, and 15 checks (`EXPECTED_CHECK_COUNT` = 15)

## Decisions Made

- `config_page.render()` deliberately does not compose the flash banner itself, even though the plan's Task 1 action text describes `render(ctx)` as doing so — `companion/app.py`'s existing (06-05, unchanged) `do_GET /config` route already builds and passes the banner to `layout.page_shell()` uniformly for all five tabs. Embedding it in `render()` too would double-render the banner on every page load. The plan's actual behavioral requirement (the banner appears with D-07's copy after a save) is proven instead by this plan's own end-to-end HTTP check, which is the more faithful test anyway — it exercises the real save→redirect→re-render path a browser takes, not a hand-built `ctx["flash"]`.
- The poll-trigger cooldown's disabled-button copy is its own constant in `config_page.py` (`POLL_COOLDOWN_HELPER_TEXT`), not imported from `companion/app.py`'s `FLASH_MESSAGES` — a page module importing `companion/app.py` would be a cycle (`app.py` already imports `config_page.py`). This duplicates the same UI-SPEC wording at two independent rendering sites (the button-adjacent copy vs. the post-redirect flash banner), which is an accepted, deliberate tradeoff to avoid the cycle.
- Renamed the plan's `SAVE_FAILED_FLASH_KEY` (06-05's stub name) to the plan's own specified `FLASH_SAVE_FAILED`/`FLASH_SAVED`/`FLASH_POLL_TRIGGERED`/`FLASH_POLL_COOLDOWN` four-constant set (per the plan's Artifacts section and Task 2's explicit instruction that "the router's allowlist reference them, so the key strings exist in exactly one place") — required editing `companion/app.py`'s existing `FLASH_KEY_*` definitions to import from `config_page.py` rather than restate the literals.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `companion/app.py` and `companion/pages/__init__.py` needed edits beyond the plan's stated `files_modified` list**
- **Found during:** Task 1
- **Issue:** The plan's frontmatter lists only `companion/pages/config_page.py` and `companion/test_config_page.py` under `files_modified`, but Task 1's own action text explicitly instructs: "add a `poll_cooldown_remaining` key to the context that `app.Handler.page_context()` already computes, rather than importing the app module from a page module (a page importing the router would be a cycle)." This is a genuine requirement of the task's stated design, not something config_page.py alone can satisfy — the ctx key must originate in app.py's page_context(). Task 2 similarly instructs "have the router's allowlist reference them, so the key strings exist in exactly one place," which requires app.py's FLASH_KEY_* definitions to reference config_page.py's new constants.
- **Fix:** Added `"poll_cooldown_remaining": poll_cooldown_remaining(state_dir)` to `page_context()`'s returned dict in `companion/app.py`; repointed `FLASH_KEY_SAVED`/`FLASH_KEY_SAVE_FAILED`/`FLASH_KEY_POLL_TRIGGERED`/`FLASH_KEY_POLL_COOLDOWN` to `config_page.FLASH_*`. Also updated `companion/pages/__init__.py`'s ctx-key documentation to list the new key, so the module contract doc stays accurate.
- **Files modified:** `companion/app.py`, `companion/pages/__init__.py`
- **Verification:** `companion/test_companion_app.py` (49/49, unchanged) and `companion/test_config_page.py` (15/15) both pass; `grep -c "FLASH_" companion/pages/config_page.py` = 13 (>= 8); D-07's confirmation sentence appears exactly once outside `.planning/` (`companion/app.py`'s `FLASH_MESSAGES`).
- **Committed in:** `0d2a603` (Task 1, the `poll_cooldown_remaining` half) and `e5bbef3` (Task 2, the `FLASH_KEY_*` half)

**2. [Rule 1 - Bug] An acceptance-criteria grep for `normalise_theme_id`/`normalise_runway_id` collided with the docstring explaining their deliberate absence**
- **Found during:** Task 2, while verifying the plan's own acceptance criteria
- **Issue:** `handle_post()`'s docstring originally named `device_config.normalise_theme_id()`/`normalise_runway_id()` literally, to explain why they are NOT called — but this made `grep -n "normalise_theme_id\|normalise_runway_id" companion/pages/config_page.py` report matches, the same class of literal-grep/docstring-prose collision 06-05-SUMMARY.md documented for `airlines_page.py`'s `<form>`/`<button>` mentions.
- **Fix:** Reworded the docstring to describe the two functions without naming them literally ("device_config's two read-path normalising helpers").
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `grep -n "normalise_theme_id\|normalise_runway_id" companion/pages/config_page.py` now returns no lines.
- **Committed in:** `e5bbef3` (Task 2 commit)

**3. [Rule 1 - Bug] The end-to-end test's own hardcoded D-07 sentence created a second verbatim occurrence outside `.planning/`**
- **Found during:** Task 3, while verifying Task 2's own acceptance criterion ("D-07's confirmation sentence appears verbatim exactly once in the repository outside the planning directory")
- **Issue:** The first draft of the end-to-end check in `companion/test_config_page.py` hardcoded the literal D-07 sentence to assert against, which itself became a second verbatim occurrence outside `.planning/` — failing the very criterion the check exists to prove.
- **Fix:** The check now imports `companion.app` and reads the expected copy from `companion_app.FLASH_MESSAGES[companion_app.FLASH_KEY_SAVED]` instead of re-typing the sentence.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `grep -rn "Saved — will apply on the frame's next scheduled refresh." --include="*.py" .` (outside `.planning/`) shows exactly one hit, in `companion/app.py`.
- **Committed in:** `a57ec74` (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking file-scope requirement explicit in the plan's own task text, 2 acceptance-criteria/grep-collision bugs)
**Impact on plan:** All three are small, self-contained, and directly satisfy the plan's own stated acceptance criteria — no scope creep, no behavior change beyond what the plan itself specified.

## Issues Encountered

None beyond the three auto-fixed deviations above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-01, CFG-07, and CFG-12 are now genuinely end-to-end functional: a user can pick a theme and a runway from a browser with no SSH access, save is server-side-validated against the registries, and the D-07 confirmation tells them the change lands on the frame's next scheduled poll, not immediately.
- `companion/pages/config_page.py` is fully complete for this phase's scope; plans 06-08 (Health/Airlines) and 06-09 (History/Preview) can proceed independently — neither depends on this plan's internals beyond the shared `companion/app.py` router, which is otherwise unchanged.
- Full 9-harness suite (`scripts/run-all-tests.sh`) green at 82% coverage; `companion/test_companion_app.py` unchanged at 49/49; `companion/test_config_page.py` new at 15/15; `ruff check .` clean; no stray subprocess left behind by either companion harness.
- `git diff --stat` for this plan touches `companion/pages/config_page.py`, `companion/test_config_page.py`, `companion/app.py`, and `companion/pages/__init__.py` — the plan's own `<verification>` section names only the first two; the latter two are documented above as a Rule-3 deviation required by the plan's own Task 1/Task 2 action text.

## Self-Check: PASSED
