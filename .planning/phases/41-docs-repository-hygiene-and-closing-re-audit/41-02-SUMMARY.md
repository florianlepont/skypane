---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 02
subsystem: docs
tags: [architecture-doc, compliance-doc, firmware-vendor-doc, doc-drift, comment-history]

# Dependency graph
requires:
  - phase: 41-01
    provides: "41-DOC-DRIFT-DEPLOY.md's row numbering (1-35) and its row 17 handoff of .claude/CLAUDE.md's systemd-unit-count fix"
provides:
  - "ARCHITECTURE.md, COMPLIANCE.md, .claude/CLAUDE.md and firmware/VENDOR.md (doc text only) corrected to match the code as it stands after Phases 32-40"
  - "41-DOC-DRIFT-DOCS.md, a 66-row claim-by-claim evidence log (rows 36-101) covering every ARCHITECTURE.md heading, every COMPLIANCE.md provider section, firmware/VENDOR.md's provenance table, and every Python writer-model comment this plan's context named"
  - "server/poll_loop.py's post-split writer model (device_policy.py's hysteresis, called from poll_cycle.py) correctly named everywhere a comment or docstring refers to it"
affects: [41-03, 41-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doc-drift verification: cite the current implementing file:line or a command's output, never the audit ledger or this plan's own 'known starting points', for every claim (accurate or corrected)"
    - "A grep-based reproduction step inside a doc (COMPLIANCE.md's PRIM/AeroDataBox check) must itself be re-run and re-verified, not just trusted because it once returned the claimed output - later code growth can turn a substring grep into a false positive"

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-DOC-DRIFT-DOCS.md
  modified:
    - ARCHITECTURE.md
    - COMPLIANCE.md
    - firmware/VENDOR.md
    - .claude/CLAUDE.md
    - stub-server/byos_server.py
    - server/state_store.py
    - server/device_policy.py
    - companion/wake.py
    - companion/test_request_connections.py
    - companion/test_freshness_token.py
    - companion/test_companion_app_05.py
    - companion/test_companion_app_helpers.py
    - companion/test_browser_ux_03.py
    - companion/pages/config_page.py

key-decisions:
  - "DOC-01 requirement left unticked here too: this is part 2 of 2 (41-01 owns deploy/ and .github/workflows/); 41-07 folds both plans' drift logs into the closing DOC-01 checkbox per 41-CONTEXT.md"
  - "Fixed the identical poll_loop-writer-model bug in two files outside this plan's enumerated <files> list (server/device_policy.py, companion/pages/config_page.py) under Rule 1 - both are one-line, comment-only, directly on-topic corrections of the exact pattern this plan's must-haves target ('No Python comment or docstring names a writer, owner or module location that the code contradicts'), matching 41-01's own precedent of fixing deploy/.gitignore outside its files_modified list"
  - "Used check_comment_history.py same-code --base 7bd8664 --allow stub-server/byos_server.py for that one file: its module docstring feeds argparse's description=__doc__, so the tool's own design treats it as literal code (a user-visible --help string), not a stripped-out docstring, even though the only change is the same wording fix applied everywhere else in the file. Confirmed by manual diff review that the file's entire change-set is comment/docstring text with no logic difference."
  - "README.md, CONTRIBUTING.md and server/README.md needed only two small factual corrections (server/README.md's 'one call per cycle' undercount and its stale 'unchanged this plan'/SKYPANE_BYOS_SECRET wording) - the rest of both files, and all of README.md/CONTRIBUTING.md, were already accurate and are logged as such rather than rewritten for its own sake"

requirements-completed: []

# Metrics
duration: ~90min
completed: 2026-09-28
---

# Phase 41 Plan 02: ARCHITECTURE/COMPLIANCE/VENDOR doc-drift and Python writer-model comment correction Summary

**Corrected six genuine doc-drift findings in ARCHITECTURE.md/COMPLIANCE.md/firmware/VENDOR.md/server/README.md (device authentication model, byos's actual persistence, NVS key count, adsbdb TTL-based cache expiry, a stale PRIM/AeroDataBox verification grep, and a removed-not-placeholdered firmware Kconfig option) plus the systemd-unit-count and CI-checks rows in .claude/CLAUDE.md, and repointed every stale `poll_loop`-as-writer comment/docstring across stub-server/, companion/ and server/ to the correct post-split owner (`server/poll_cycle.py`/`server/device_policy.py`), with all 66 checked claims logged in 41-DOC-DRIFT-DOCS.md.**

## Performance

- **Duration:** ~90 min
- **Started:** 2026-09-28 (session start)
- **Completed:** 2026-09-28T05:25:56Z
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 14 (plus 1 created: the drift log)

## Accomplishments

- Re-verified every claim ARCHITECTURE.md makes, section by section, against the current `server/poll_cycle.py`/`server/state_store.py`/`server/device_policy.py`/`stub-server/byos_server.py`/`firmware/` — not the audit ledger's original examples, several of which turned out to already be accurate (the "single writer" claim for `poll_state.json`, the byos bind address, the backoff formula, the display-pacing constants) and are logged as such rather than assumed stale.
- Found and corrected three real ARCHITECTURE.md inaccuracies the ledger's "known starting points" didn't name precisely: the device-authentication bullet still described a single shared `SKYPANE_BYOS_SECRET` when Phases 34/37 moved enrolment to a per-device `devices.json` registry; the "persists nothing of its own" claim about byos was false (it writes `battery_state.json`, just not a history); and the NVS-persistence bullet said "exactly four" keys when a fifth (the per-device enrolment secret) lives on its own dedicated partition. Also added the missing `state/poll.lock`/`fcntl.flock` detail the writer-model paragraph never named, closing this plan's own `key_links` requirement.
- Corrected COMPLIANCE.md's adsbdb caching description (INT-08): a callsign is NOT "never re-queried once seen" — Phase 36 added TTL-based expiry (1 day for a miss, 30 days for a hit) that does re-query it — fixed in both places the doc says this.
- Found that COMPLIANCE.md's own PRIM/AeroDataBox "returns zero matches" verification command, if re-run literally today, no longer returns zero output at all (later phases added test docstrings using "prim" as a word-fragment, e.g. "primary"/"priming"); repointed it to a word-bounded, git-tracked-files-only grep and re-verified it actually returns zero matches now.
- Found firmware/VENDOR.md (doc text only, zero firmware code touched) had a genuine drift in its own provenance table: `CONFIG_FP_API_BASE` was described as "changed... to a reserved placeholder" when `firmware/tests/check_production_config.sh` proves the option was removed outright as an "orphan `CONFIG_FP_*` symbol" — corrected both table rows that made this claim.
- Repointed every stale `poll_loop`-as-writer comment across `stub-server/byos_server.py` (7 locations), `companion/wake.py`, `companion/test_request_connections.py`, `companion/test_freshness_token.py` (x2), `companion/test_companion_app_05.py`, `companion/test_companion_app_helpers.py` and `companion/test_browser_ux_03.py` to the correct post-Phase-36/39 owner — while leaving every claim that is genuinely still true about `server/poll_loop.py` itself (its own sys.path bootstrap, the `"poll_loop: "` print prefix `poll_cycle.py` deliberately kept) untouched and logged as accurate.
- Ran a repo-wide grep for `single writer|sole writer|only writer|persists nothing` (per this plan's mandate) and found two more instances of the identical writer-model bug outside the plan's enumerated files (`server/device_policy.py`, `companion/pages/config_page.py`) — fixed both under Rule 1 and logged the file-scope deviation.

## Task Commits

1. **Task 1: Verify and correct ARCHITECTURE.md, COMPLIANCE.md and firmware/VENDOR.md** - `7ad0ff7` (docs)
2. **Task 2: Verify and correct README.md, CONTRIBUTING.md, .claude/CLAUDE.md, server/README.md and Python comment claims** - `83121a3` (docs)

_Both tasks are doc/comment-only; no `feat`/`fix` commits were needed since nothing here changes runtime behavior._

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-DOC-DRIFT-DOCS.md` - 66-row claim-by-claim evidence log, rows 36-101, continuing 41-01's numbering (created)
- `ARCHITECTURE.md` - device-authentication bullet rewritten (per-device registry, not a shared secret); "persists nothing" corrected; NVS key count corrected to five across two partitions; `state/poll.lock`/flock detail added to the writer-model paragraph
- `COMPLIANCE.md` - adsbdb caching/TTL description corrected in two places; PRIM/AeroDataBox verification grep repointed to a word-bounded, tracked-files-only form and re-verified
- `firmware/VENDOR.md` (doc text only) - two provenance-table rows corrected: `CONFIG_FP_API_BASE` was removed outright, not defaulted to a placeholder
- `.claude/CLAUDE.md` - Technology Stack table only: "three systemd units" corrected to six; Tests/CI row now lists mypy, the function-size gate and the comment-history guard
- `stub-server/byos_server.py` - 7 stale `poll_loop`-as-writer references repointed to `server/poll_cycle.py`/`server/device_policy.py` (module docstring, battery-critical-latch comment, quiet-hours docstring, `battery_critical_sleep_s()`'s docstring x2, `save_battery_state()`'s docstring, two `do_GET` comments)
- `server/state_store.py` - removed a stale "new, unwired file, do not edit callers yet" note; the module has been fully wired into all three callers since Phase 39
- `server/device_policy.py` - one writer-model comment repointed (found via the repo-wide grep, outside this plan's `<files>` list)
- `companion/wake.py`, `companion/test_request_connections.py`, `companion/test_freshness_token.py`, `companion/test_companion_app_05.py`, `companion/test_companion_app_helpers.py`, `companion/test_browser_ux_03.py` - one stale `poll_loop` reference each repointed to `poll_cycle`
- `companion/pages/config_page.py` - one writer-model comment repointed (found via the repo-wide grep, outside this plan's `<files>` list)

## Decisions Made

- Left `DOC-01`'s REQUIREMENTS.md checkbox unticked — this is explicitly part 2 of 2; 41-07 closes the requirement once both plans' drift logs exist.
- Fixed `server/device_policy.py` and `companion/pages/config_page.py` even though neither is in this plan's `files_modified`/`<files>` list, because both contain the exact writer-model bug pattern this plan's must-haves target ("No Python comment or docstring names a writer, owner or module location that the code contradicts"), the fix is one line and comment-only in each, and 41-01 set the precedent for this kind of adjacent fix (its `deploy/.gitignore` correction).
- Used `--allow stub-server/byos_server.py` on the `same-code` verification for that one file only, because its module docstring is fed into `argparse(description=__doc__)` and is therefore intentionally treated as literal "code" by the checker's own design (a user-facing `--help` string), not because anything besides wording changed — confirmed by reviewing the full `git diff` for that file line by line: every changed line is inside a `"""..."""` docstring or a `#` comment.
- Did not rewrite README.md or CONTRIBUTING.md beyond what was actually wrong: both were checked claim-by-claim and were already accurate except for the two `server/README.md` items listed below; logged as `accurate` rather than reworded for its own sake, matching this plan's "check-and-keep" instruction.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] ARCHITECTURE.md's device-authentication claim named a retired shared secret**
- **Found during:** Task 1 (verifying ARCHITECTURE.md's Deployment topology section)
- **Issue:** The doc said devices authenticate via a single shared `SKYPANE_BYOS_SECRET`; `stub-server/byos_server.py` actually gates `/device/v1/setup` against a per-device `devices.json` registry (MAC → SHA-256 of that device's own secret), a design that closed exactly the "one leaked value hijacks every device" gap the old model had.
- **Fix:** Rewrote the bullet to describe the per-device registry, the device's own dedicated NVS `secret` partition, and `firmware/provision.sh`'s role in provisioning it.
- **Files modified:** `ARCHITECTURE.md`
- **Verification:** Cited against `stub-server/byos_server.py:198-206,659-666`, `firmware/main/nvs_schema.h` (read-only); logged as row 46.
- **Committed in:** `7ad0ff7` (Task 1 commit)

**2. [Rule 1 - Bug] ARCHITECTURE.md's "persists nothing" claim about byos was false**
- **Found during:** Task 1 (same section)
- **Issue:** The doc said `stub-server/byos_server.py` "persists nothing of its own"; it actually writes `state/battery_state.json` on every poll via `save_battery_state()`.
- **Fix:** Reworded to state that byos persists one artefact (the single latest battery reading, overwritten every poll — not a history), which is why the companion's own battery *history* still comes from Caddy's access log — the doc's real point, which stays true.
- **Files modified:** `ARCHITECTURE.md`
- **Verification:** Cited against `stub-server/byos_server.py:557-565`, `server/state_store.py:load_battery_state()`; `grep -n "persists nothing" ARCHITECTURE.md` now prints nothing; logged as row 45.
- **Committed in:** `7ad0ff7`

**3. [Rule 1 - Bug] ARCHITECTURE.md undercounted NVS keys by one**
- **Found during:** Task 1 (Device firmware section)
- **Issue:** "trimmed... to exactly four" keys omitted the per-device enrolment secret, which lives on its own dedicated `secret` NVS partition (`FP_NVS_ENROL_SECRET`).
- **Fix:** Reworded to "five, split across two partitions" and named the fifth key.
- **Files modified:** `ARCHITECTURE.md`
- **Verification:** Cited against `firmware/main/nvs_schema.h` (read-only); logged as row 39.
- **Committed in:** `7ad0ff7`

**4. [Rule 2 - Missing critical detail] Writer-model paragraph never named the lock serialising the two `run_once()` callers**
- **Found during:** Task 1 (this plan's own `key_links` requirement)
- **Issue:** ARCHITECTURE.md said the systemd timer and the companion's `POST /poll-now` both call `run_once()`, but never said what stops them running concurrently.
- **Fix:** Added a sentence naming `state/poll.lock` (`server/poll_cycle.py`'s `poll_cycle_lock()`, an `fcntl.flock`) and the two callers' different wait behaviour.
- **Files modified:** `ARCHITECTURE.md`
- **Verification:** `grep -n "poll.lock" ARCHITECTURE.md` now prints a match (previously printed nothing); cited against `server/poll_cycle.py:93-127`, `companion/app.py:234-241`; logged as row 42.
- **Committed in:** `7ad0ff7`

**5. [Rule 1 - Bug] COMPLIANCE.md's adsbdb cache description omitted TTL expiry**
- **Found during:** Task 1 (COMPLIANCE.md's adsbdb section)
- **Issue:** "a callsign already seen is never re-queried" is false since Phase 36 added `CACHE_MISS_TTL_S`/`CACHE_HIT_TTL_S`; an expired entry is popped and the callsign IS re-queried.
- **Fix:** Rewrote both places the doc makes this claim to describe the TTL-bounded, outcome-gated caching (only 404/empty-route responses cache as a miss; everything transient is retried on the very next call).
- **Files modified:** `COMPLIANCE.md`
- **Verification:** Cited against `server/plane/enrich.py:65-76,217-309`; logged as rows 55-56.
- **Committed in:** `7ad0ff7`

**6. [Rule 1 - Bug] COMPLIANCE.md's own reproduction command for the PRIM/AeroDataBox verdict no longer returns zero output**
- **Found during:** Task 1 (re-running the doc's own cited command, as this plan's process requires)
- **Issue:** The plain-substring, non-tracked-files grep the doc tells a reader to run now returns dozens of false positives ("primary", "priming" in test docstrings added since 2026-08-26) and would also pick up a local `server/.venv/`.
- **Fix:** Repointed to `git grep -niE '\bprim\b|iledefrance|aerodatabox' -- 'server/**/*.py' 'stub-server/**/*.py'` and re-verified it returns zero matches today. The underlying verdict (PRIM/AeroDataBox genuinely unused) was never wrong.
- **Files modified:** `COMPLIANCE.md`
- **Verification:** Ran the corrected command directly; logged as rows 57-58.
- **Committed in:** `7ad0ff7`

**7. [Rule 1 - Bug] firmware/VENDOR.md's `CONFIG_FP_API_BASE` provenance rows described a placeholder default that doesn't exist**
- **Found during:** Task 1 (checking each VENDOR.md "differs from upstream" claim against firmware sources, read-only)
- **Issue:** Two rows said the option was "changed... to a reserved placeholder"; `firmware/tests/check_production_config.sh` actually asserts it's an "orphan `CONFIG_FP_*` symbol" that "must be gone" from `sdkconfig.defaults`, and no such Kconfig option exists in `main/Kconfig.projbuild` at all — the base URL comes from a `secrets.h` macro instead, as the doc's own `api_client.c` row already (correctly) says.
- **Fix:** Reworded both rows to describe outright removal, consistent with the already-accurate `api_client.c` row.
- **Files modified:** `firmware/VENDOR.md` (documentation text only — no file under `firmware/` other than `VENDOR.md` was written to; confirmed by `git diff --name-only 7bd8664 -- firmware/`)
- **Verification:** Cited against `firmware/tests/check_production_config.sh:76-78`, `firmware/main/Kconfig.projbuild` (both read-only); logged as rows 98-99.
- **Committed in:** `7ad0ff7`

**8. [Rule 1 - Bug] `.claude/CLAUDE.md` stack table's systemd-unit count and CI-checks list were stale**
- **Found during:** Task 2 (per 41-01's row 17 handoff)
- **Issue:** "three systemd units" undercounted (six exist); the Tests/CI row omitted mypy, the function-size gate and the comment-history guard.
- **Fix:** Corrected the unit count and expanded the CI-checks description; left every other section of the file byte-identical.
- **Files modified:** `.claude/CLAUDE.md`
- **Verification:** `ls deploy/*.service deploy/*.timer` (6 files); `.github/workflows/ci.yml` step list; `git diff 7bd8664 -- .claude/CLAUDE.md` touches only the two table rows.
- **Committed in:** `83121a3` (Task 2 commit)

**9. [Rule 1 - Bug, x11 locations across 9 files] Stale `poll_loop`-as-writer/owner comments and docstrings**
- **Found during:** Task 2 (this plan's context-listed locations plus a repo-wide grep for `single writer|sole writer|only writer|persists nothing`)
- **Issue:** Phases 36/39 moved the poll cycle body into `server/poll_cycle.py` and battery/quiet-hours policy into `server/device_policy.py`; a batch of comments across `stub-server/byos_server.py` (7 spots), `companion/wake.py`, `companion/test_request_connections.py` (x2), `companion/test_freshness_token.py` (x2), `companion/test_companion_app_05.py`, `companion/test_companion_app_helpers.py`, `companion/test_browser_ux_03.py`, `server/state_store.py` (a stale "unwired" note), `server/device_policy.py` and `companion/pages/config_page.py` still named `poll_loop.py`/`poll_loop` as the owner.
- **Fix:** Repointed each to the module that now actually implements the described behaviour, verified individually against the current source (see 41-DOC-DRIFT-DOCS.md rows 80-97 for the full per-location evidence).
- **Files modified:** listed in "Files Created/Modified" above.
- **Verification:** `check_comment_history.py same-code --base 7bd8664` (with `--allow stub-server/byos_server.py` for the reason in Decisions Made) exits 0; `check_comment_history.py check`, `ruff check .`, `mypy` all exit 0; full test suite `3074 passed, 144 skipped` (skips are pre-existing environment gaps — missing Chromium binary, root euid — not caused by this change); `grep -n "poll_loop.py's apply_battery_critical_hysteresis" stub-server/byos_server.py` prints nothing.
- **Committed in:** `83121a3`

**10. [Rule 1 - Bug] `server/README.md`'s "one call per cycle" and "unchanged this plan"/`SKYPANE_BYOS_SECRET` wording were both stale**
- **Found during:** Task 2 (verifying server/README.md against detect.py and the current device-enrolment model)
- **Issue:** Two aggregators (adsb.fi, adsb.lol) are queried per cycle today, not one; and the Phase-2-era "still vendored, unchanged this plan" note about `byos_server.py`, plus its `SKYPANE_SETUP_SECRET`/`SKYPANE_BYOS_SECRET` firmware-deployment instructions, describe the pre-Phase-34/37 shared-secret model this plan already found retired (see deviation 1 above).
- **Fix:** Reworded "one call per cycle" to "one call per provider per cycle"; removed the stale "unchanged this plan" note; reworded the firmware-side deployment note to describe per-device secret provisioning instead of a single shared value.
- **Files modified:** `server/README.md`
- **Verification:** Cited against `server/plane/detect.py:717-816`, `stub-server/byos_server.py:807-808` ("retired: ignored"); logged as rows 75-77.
- **Committed in:** `83121a3`

---

**Total deviations:** 10 auto-fixed (10 bugs — all Rule 1; two of the ten touched files outside this plan's enumerated `<files>` list, both logged individually above and in the drift log)
**Impact on plan:** All ten are necessary doc/comment corrections directly within this plan's stated purpose (DOC-01 part 2). No behavior changed anywhere — every `.py` edit is proven comment/docstring-only by `check_comment_history.py same-code`, and the full test suite passes unchanged. No scope creep beyond the two adjacent-file writer-model fixes, both justified above.

## Issues Encountered

`check_comment_history.py same-code --base 7bd8664` failed for `stub-server/byos_server.py` on the first run because that file's module docstring is fed into `argparse.ArgumentParser(description=__doc__)`, and the checker's own AST-based design (`_reads_module_dunder_doc()`/`keep_module_doc`) therefore treats the module docstring as literal code rather than a strippable docstring — any wording change to it fails a strict AST comparison, by design, since it changes the program's own `--help` output. Resolved by re-running with `--allow stub-server/byos_server.py` after manually confirming (via `git diff 7bd8664 -- stub-server/byos_server.py`) that every changed line in the file is inside a `"""..."""` docstring or a `#` comment — no logic differs. Documented in the drift log's summary and in Decisions Made above so a future reader isn't surprised by the `--allow` flag.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `41-DOC-DRIFT-DOCS.md` (rows 36-101) is ready for 41-07's closing DOC-01 row to fold in, alongside 41-01's `41-DOC-DRIFT-DEPLOY.md` (rows 1-35).
- Both parts of DOC-01's doc surface are now closed: 41-01 owned `deploy/`/`.github/workflows/`/`deploy/README.md`; this plan owned `ARCHITECTURE.md`, `COMPLIANCE.md`, `README.md`, `CONTRIBUTING.md`, `.claude/CLAUDE.md`, `firmware/VENDOR.md` (doc text), `server/README.md` and the Python writer-model comments.
- No blockers for 41-03 (repository hygiene) or the rest of the phase.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 14 claimed modified/created files found on disk (`ARCHITECTURE.md`, `COMPLIANCE.md`,
`firmware/VENDOR.md`, `.claude/CLAUDE.md`, `stub-server/byos_server.py`, `server/state_store.py`,
`server/device_policy.py`, `companion/wake.py`, `companion/test_request_connections.py`,
`companion/test_freshness_token.py`, `companion/test_companion_app_05.py`,
`companion/test_companion_app_helpers.py`, `companion/test_browser_ux_03.py`,
`companion/pages/config_page.py`), plus `41-DOC-DRIFT-DOCS.md` and this summary; both task commit
hashes (`7ad0ff7`, `83121a3`) found in `git log --oneline --all`.
