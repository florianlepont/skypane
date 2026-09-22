---
phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu
plan: 03
subsystem: testing
tags: [playwright, pytest-free-harness, ruff, docker, ci-parity, quiet-hours, wake-interval]

requires:
  - phase: 31-01
    provides: "companion/test_browser_ux_helpers.py shared module (quiet-dial decoder cluster + _handle_sel), 31-BASELINE-CHECKS.txt pre-split transcript"
  - phase: 31-02
    provides: "companion/test_browser_ux.py already reduced to 85/85; established verbatim-relocation + AST-import + three-way-comparison pattern this plan repeats"
provides:
  - "companion/test_browser_ux_quiet_wake.py — the 25-04/25-05 quiet-hours dial and wake-interval slider series (9 checks) as its own standalone, independently-runnable harness"
  - "companion/test_browser_ux.py reduced to 76/76, EXPECTED_CHECK_COUNT changelog appended"
  - "Empirical confirmation of RESEARCH.md Assumption A3 and Open Question 2 for BOTH mandatory D-04 extractions now that this plan has landed"
affects: [31-04, 31-05]

tech-stack:
  added: []
  patterns:
    - "Verbatim block relocation (zero rewording, zero reindentation) preserving comment provenance, continuing 31-01/31-02's established recipe"
    - "AST-derived free-variable import list against the finished file, catching exactly which of the plan's own read_first-suggested helpers (json/re stdlib, six now-orphaned helper-module names) were actually unused after the block moved"
    - "Three-way PASS-name-set comparison (baseline == new-file ∪ reduced-file, disjoint, all PASS) as the authoritative verdict-preservation proof, run as a script"
    - "Cross-architecture Docker verification (linux/amd64 via --platform, matching the real CI runner), continuing 31-01/31-02's established recipe — container-internal venv path (/opt/venv-docker) used instead of a bind-mounted one, to avoid the venv leaking into the host working tree as untracked files"

key-files:
  created:
    - companion/test_browser_ux_quiet_wake.py
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "Confirmed RESEARCH.md's boundary correction against the pre-plan-01 line numbers held exactly as the plan's own objective text specified: the real start is the '# ---' rule line above the 25-04-PLAN.md Task 4 banner (not RESEARCH.md's own mid-fixture line 11516), and the block ends at the wake-interval slider's last check() call, immediately before the 25-06-PLAN.md theme-carousel banner. Verified live: the extracted 9-check, 1944-line block has zero references to its own local constants/closures outside itself."
  - "Put the Docker-verification venv at a container-internal path (/opt/venv-docker) rather than inside the bind-mounted /repo directory this time — an earlier misstep (see Issues Encountered) put it at /repo/.venv-docker, which is the host repo directory via the bind mount, and 'rm -rf .venv-docker' to clean up the host git tree afterward also deleted it from inside the still-running container, breaking every subsequent docker exec until the venv was recreated at a path outside the mount."

requirements-completed: [D-04, D-07]

coverage:
  - id: D1
    description: "companion/test_browser_ux_quiet_wake.py created: the complete 25-04/25-05 quiet-hours dial and wake-interval slider series (9 checks) moved verbatim, zero reindentation, into its own harness with its own main()/Harness()/two-gate skip preamble naming itself, EXPECTED_CHECK_COUNT=9 re-derived by running natively (9/9 PASS on first attempt, no arm64 flake hit) and re-confirmed under linux/amd64 Docker (matching CI's ubuntu-latest runner)"
    requirement: "D-04"
    verification:
      - kind: automated_ui
        ref: "server/.venv/bin/python3 companion/test_browser_ux_quiet_wake.py (native arm64) -> 9/9 PASS, 0 FAIL, exit 0; re-run under linux/amd64 Docker -> 9/9 PASS, 0 FAIL, exit 0"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check companion/test_browser_ux_quiet_wake.py"
        status: pass
      - kind: other
        ref: "skip-path exercised via PLAYWRIGHT_BROWSERS_PATH pointed at an empty dir -> SKIP line naming this file, exit 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "companion/test_browser_ux.py reduced by deleting the exact moved 1944-line span, 8 now-unused imports dropped via ruff --fix (json, re, and 6 helper-module names whose only call sites left with the block), EXPECTED_CHECK_COUNT changelog appended with 76, re-derived by running rather than subtracted on paper; 76 + 11 + 9 = 96 conserved across all three files"
    requirement: "D-04"
    verification:
      - kind: automated_ui
        ref: "server/.venv/bin/python3 companion/test_browser_ux.py (linux/amd64 Docker) -> 76/76 PASS, 0 FAIL, exit 0"
        status: pass
      - kind: unit
        ref: "python3 -c AST assertion: EXPECTED_CHECK_COUNT(test_browser_ux.py)=76 + EXPECTED_CHECK_COUNT(test_browser_ux_health_drawings.py)=11 + EXPECTED_CHECK_COUNT(test_browser_ux_quiet_wake.py)=9 == 96"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check . (whole repo)"
        status: pass
      - kind: automated_ui
        ref: "the settings dirty-bar audit check ('a real Annuler click restores every surface...', which calls both _quiet_arc_minutes and _handle_sel) confirmed present and PASS in the 76-check Docker transcript by exact name match"
        status: pass
    human_judgment: false
  - id: D3
    description: "Verdict-preservation empirically proven per RESEARCH.md Pitfall 2/Assumption A3: three-way PASS-name-set comparison against 31-BASELINE-CHECKS.txt (base == new ∪ reduced ∪ drawings-file, all three post-split files pairwise disjoint, zero FAIL lines anywhere), plus all three files run concurrently in the same linux/amd64 container to confirm no ephemeral-port/temp-dir collision under real three-way contention"
    requirement: "D-07"
    verification:
      - kind: integration
        ref: "python3 compare.py (four-way PASS-name-set diff: 96-baseline vs 11+9+76 post-split) -> PITFALL-2-CLEAN: 96 == 11 + 9 + 76, names conserved, all PASS, three-way concurrent run green"
        status: pass
      - kind: other
        ref: "concurrent docker exec of all three files in the same linux/amd64 container -> concurrent-exits=0/0/0"
        status: pass
    human_judgment: false

duration: ~2h20m
completed: 2026-09-22
status: complete
---

# Phase 31 Plan 03: Quiet-Hours Dial + Wake-Interval Slider Extraction Summary

**Moved the complete 25-04/25-05 quiet-hours dial and wake-interval slider scenario group (9 checks) out of `companion/test_browser_ux.py` into a new standalone `companion/test_browser_ux_quiet_wake.py` harness, with an empirical three-way transcript comparison proving every verdict is unchanged — and, unlike plans 01/02, the new file's native run passed 9/9 on the first try with no arm64-environmental flake.**

## Performance

- **Duration:** ~2h20m (most of it re-provisioning a `linux/amd64` Docker container for verification — once at a bind-mounted path that had to be redone after an accidental host-side `rm -rf` also deleted it from inside the running container — and waiting out the QEMU-emulated wall time of the 76-check reduced parent harness across four separate full runs: task 2's native run, task 2's Docker run, task 3's solo Docker run, and task 3's concurrent Docker run)
- **Completed:** 2026-09-22
- **Tasks:** 3/3 completed
- **Files modified:** 2 (1 created harness, 1 reduced harness)

## Accomplishments

- Created `companion/test_browser_ux_quiet_wake.py`: the 9-check quiet-hours-dial/wake-interval-slider series moved byte-for-byte (zero reindentation) into its own `main()`, with its own two-gate Playwright skip preamble naming this file, its own `Harness()`/`seed_state_dir()` trio, and an import list derived from an AST free-variable scan of the finished block rather than guessed by eye — `ruff check` passed clean on the first attempt. Confirmed RESEARCH.md's own boundary correction (the real cut point is the banner-adjacent rule line, not RESEARCH.md's own mid-fixture line estimate) held with zero stranded references.
- Reduced `companion/test_browser_ux.py` by deleting the exact 1944-line span now living in the new file, dropped 8 now-unused imports (`json`, `re`, and six helper-module names whose only call sites left with the block) via `ruff check --fix`, and appended a new `EXPECTED_CHECK_COUNT = 76` changelog entry following the file's own append-only convention — re-derived by running the reduced file, not by subtracting 9 from 85 on paper.
- Proved the split verdict-preserving: a four-way comparison of PASS check-name sets (the pre-split 96-name baseline vs. the drawings file's 11 vs. the new file's 9 vs. the reduced file's 76) showed exact set equality with zero overlap and zero FAIL lines anywhere, and all three files were run concurrently in the same container to confirm no ephemeral-port or temp-dir collision under real three-way contention.

## Task Commits

1. **Task 1: Create companion/test_browser_ux_quiet_wake.py with the 9 dial and slider checks moved verbatim** - `c37a4f0` (feat)
2. **Task 2: Remove the 9 moved checks from companion/test_browser_ux.py and re-derive its counter by running** - `3562290` (refactor)
3. **Task 3: Prove no moved check changed verdict** - (this commit)

**Plan metadata:** (final commit)

## Files Created/Modified

- `companion/test_browser_ux_quiet_wake.py` - New standalone harness: the 25-04/25-05 quiet-hours dial and wake-interval slider series, 9/9 checks, `EXPECTED_CHECK_COUNT = 9`
- `companion/test_browser_ux.py` - The moved span deleted (1944 lines), 8 now-unused imports dropped, a new `EXPECTED_CHECK_COUNT = 76` changelog entry appended

## Decisions Made

- **Confirmed the plan's own boundary correction against RESEARCH.md live, with zero deviation needed.** The plan's objective text had already identified that RESEARCH.md's pre-plan-01 line 11516 (a `page.goto()` mid-fixture) was the wrong cut point, and that the real boundary starts at the `# ---` rule line immediately above the `25-04-PLAN.md Task 4 (CFG-48)` banner. An AST free-variable scan of the extracted block confirmed exactly the plan's own predicted name set (`QUIET_DIAL_SEL`, `QUIET_ARC_SEL`, `QUIET_HANDLES_SEL`, `QUIET_READOUT_SEL`, `_quiet_hours_on_disk`, `_set_window`, `_SETTLE_DIAL`, `_wake_interval_on_disk`, `_set_interval`) had zero references outside the block, and that `_handle_sel` was the one name correctly promoted ahead of time by plan 01.
- **Derived the import list from AST free-variable analysis, which caught six now-orphaned helper imports the by-eye read_first guidance did not anticipate.** After the block moved, `ruff check` flagged `json`, `re` (stdlib — both used only inside the moved block, confirmed by a whole-file grep showing zero other call sites), and six helper-module names (`_QUIET_READOUT_SELECTOR`, `_computed_paint`, `_expected_quiet_duration_text`, `_quiet_caption_minutes`, `_quiet_caption_shape`, `_quiet_duration_span_text`) as newly unused in the reduced parent. Applied `ruff check --fix` rather than hand-editing the import block, then re-verified the fix didn't remove anything still-needed (`_quiet_arc_minutes` and `_handle_sel`, both still referenced by the settings dirty-bar audit, were correctly retained).
- **Put the Docker-verification venv outside the bind-mounted repo directory.** First attempt provisioned `/repo/.venv-docker` (inside the same directory bind-mounted from the host), then a routine host-side cleanup of an accidentally-tracked directory (`rm -rf .venv-docker` on the host, to keep `git status` clean before committing) deleted the venv from inside the still-running container too, since a bind mount is the same filesystem on both sides. Re-provisioned at `/opt/venv-docker` (a path inside the container's own writable layer, not mounted from the host) for the rest of the plan's Docker verification, and confirmed `git status --short` was clean of Docker artifacts before every commit.

## Deviations from Plan

None - plan executed exactly as written. The import-list corrections (dropping `json`/`re` and six helper names) were explicitly anticipated by the plan's own instruction to derive the list mechanically "rather than by eye," not an unplanned change.

## Issues Encountered

- **The Docker-venv-inside-the-bind-mount mistake (self-inflicted, caught before any commit).** Documented above under Decisions Made. No test or application code was affected — the mistake only broke a verification container's own tooling, caught immediately when `docker exec` started returning `bash: line 3: /opt/venv-docker/bin/python3: No such file or directory`-shaped errors after the host-side cleanup, and fixed by re-provisioning at a non-mounted path.
- **Local arm64 Chromium's known environmental flake reproduced exactly as documented, and confirmed to be pre-existing rather than newly introduced.** The reduced parent's first native run (this session, task 2) failed 3 of 76 checks: "the leave-guard stays armed for a field that has been edited but never fired change" (expected the typed value to be held by the field before any commit), "with scripts blocked at 360px... the fallback Save is VISIBLE... and still saves to disk" (a Playwright `TimeoutError` on an "element was detached from the DOM" retry loop), and "a value the server's own validation rejects... echoes the user's rejected input back into the field" (expected `'30'`, got the corrupted `'301800'`). All three failure modes, including the literal corrupted value `301800`, match 31-01-SUMMARY.md's own documented root-cause writeup verbatim (Blink's macOS `Ctrl+A`-is-not-select-all `EditingBehavior` for the first and third, and an arm64-Chromium-specific DOM-detach compositor race for the second) — none of the three failing checks is among this plan's 9 moved checks, and none is a check plan 01/02 had not already flagged. Continued the established `--platform linux/amd64` Docker recipe rather than trusting the native run's verdict; the Docker run of the identical reduced file passed 76/76, 0 FAIL, matching CI's architecture.
- **The compound bash timeout auto-backgrounded every full run of the 76-check reduced file** (task 2's native run, task 2's Docker run, task 3's solo Docker run, task 3's concurrent Docker run), each taking 7-9 minutes under QEMU emulation. Waited each out via an until-loop polling the output file for a sentinel string, per this session's own tooling constraints, rather than a fixed sleep.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 04 (orchestration/coverage-config wiring) can now register three worker-pool-eligible files instead of two: `companion/test_browser_ux_health_drawings.py` (11 checks), `companion/test_browser_ux_quiet_wake.py` (9 checks), and the further-reduced `companion/test_browser_ux.py` (76 checks) — 18 of the original 96 checks now run in two extra processes, which is D-04's full mandate (both mandatory extractions complete; the optional third group named in RESEARCH.md's Open Question 1, Flights, remains unplanned and is explicitly conditional on plan 04's own timing check).
- The 96-check total is conserved and empirically proven verdict-preserving across both extractions: `companion/test_browser_ux.py` at 76/76, `companion/test_browser_ux_health_drawings.py` at 11/11, and `companion/test_browser_ux_quiet_wake.py` at 9/9, with RESEARCH.md's highest-risk assumption (A3 — no hidden cross-check order dependency) now settled PASS by evidence across BOTH mandatory groups, not just one.
- All three files were confirmed to run concurrently without a port or temp-dir collision (`concurrent-exits=0/0/0`), which is the exact three-way concurrency plan 04's worker-pool registration will create — no port-allocation surprises expected there.
- Standalone AND concurrent wall times recorded below for plan 04's own before/after accounting, measured under this host's `linux/amd64` Docker emulation (not directly comparable to `31-TIMINGS.md`'s native `JOBS=4` numbers, but internally consistent — solo vs. three-way-concurrent shows negligible contention overhead for all three files, itself further evidence supporting the concurrency-safety finding):
  - `companion/test_browser_ux_health_drawings.py`: solo 46.30s, concurrent-with-both-siblings 53.00s
  - `companion/test_browser_ux_quiet_wake.py`: solo 56.65s, concurrent-with-both-siblings 60.40s
  - `companion/test_browser_ux.py` (reduced, 76 checks): solo 422.16s (~7m2s), concurrent-with-both-siblings 422.53s (~7m2.5s)
- No open blockers.

## RESEARCH.md Pitfall 2 / Assumption A3 / Open Question 2 — Final Empirical Verdict

**PASS**, for both of D-04's mandatory extractions together, not just this one.

RESEARCH.md Assumption A3 stated: *"No check outside the two recommended groups reads or depends on state left behind by a check inside them — verified by grep for the specific named helpers/constants used inside each group, not by exhaustively tracing every one of the file's other 87 checks."* That grep-level verification is now backed by execution-level evidence across both groups:

- Four-way PASS-name-set comparison: `set(31-BASELINE-CHECKS.txt's 96 PASS names) == set(drawings file's 11) | set(this file's 9) | set(reduced file's 76)`, with all three post-split sets pairwise disjoint. Printed `PITFALL-2-CLEAN: 96 == 11 + 9 + 76, names conserved, all PASS, three-way concurrent run green`.
- Zero `FAIL ` lines in any post-split file's Docker-verified output.
- All three files run concurrently in the same linux/amd64 container exited `0/0/0` — no ephemeral-port or temp-dir collision under real three-way contention.

RESEARCH.md Open Question 2 asked: *"Does any check in the 87 checks NOT being extracted this phase quietly depend on state seeded/mutated by a check inside groups 1 or 2, beyond the one `_quiet_arc_minutes()` case already found?"* Answer, now that both groups have landed: **No.** The one confirmed cross-group coupling RESEARCH.md and plan 01 identified — `_quiet_arc_minutes` and (found independently by plan 01's own analysis) `_handle_sel`, both called from the settings dirty-bar audit check that stays in the parent forever — is the only one that exists. That audit check ("a real Annuler click restores every surface, read off the RESULTING DOM...") is confirmed present and PASS by exact name match in the 76-check reduced file's Docker transcript, proving the plan-01 promotion is load-bearing and complete. No other divergence was found in either extraction; no check needed a seeded-state fix or a widened boundary beyond what RESEARCH.md and the plan's own objective text already anticipated.

### The 9 moved check names (verbatim, matched by full text against the baseline)

1. the quiet window still SAVES with scripts blocked through the dial — both ends set natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way, at 360px and in BOTH shipped languages; the gated handle layer has zero height and no keyboard can reach into it with scripts blocked while it occupies space with them; and the server-drawn ARC, the readout, both time inputs, B14's two 24h siblings and the three presets are all present on the scripts-blocked page, asserted after the save so none of them can stand in for it (D-09/CFG-48, 25-04-PLAN.md Task 4)
2. dragging a quiet-hours handle changes its own native `<input type="time">`, moves the announcement ON THE HANDLE rather than on the wrapper, REVEALS the bar and PERSISTS to disk once Enregistrer is clicked; one ArrowRight moves exactly one stated step and End/Home reach 23:59 and 00:00 with zero pointer events fired and the recorder proving itself; and a preset click moves BOTH handles, which is what proves the two native inputs are the one source of truth (CFG-48, 25-04-PLAN.md Task 4; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78)
3. THE arc/handles/caption agreement check (CFG-62/CFG-71/D-32, 27-02-PLAN.md Task 4): in BOTH themes, after dragging the end handle to reach the developer's own recorded window (08:00→18:00) AND, in the same check, after pressing a preset (23:00→07:00, the wrap through midnight) from wherever the drag left it, all FOUR surfaces — the two native `<input type="time">` fields, the two handles' aria-valuenow, the arc's RESOLVED geometry, and the caption's own text — decode to the SAME canonical (start_minute, end_minute) pair; AND, after the same preset click, each B14 twin's own live `.hidden` property matches this browser's resolved hour12; separately, with scripts blocked, the arc still carries both presentation attributes and they still decode to whatever window is actually saved on disk (27-04-PLAN.md Task 4, CFG-63)
4. the dial caption keeps the SAME FORM the server emits at load after EACH of a drag, a keyboard step, a typed field edit and a preset click (CFG-73 Bug A, 28-03-PLAN.md Task 3): after every one, the caption's two "HH:MM" tokens decode to what the interaction requested, its duration segment is NON-EMPTY and equals the wrapped-difference computation worded from the page's own layout.DURATION_ATTRS, and the whole caption's structural shape matches the server-rendered reference captured before any interaction — in BOTH shipped languages, with the preset step crossing midnight
5. the quiet dial meets its floors at 360px — BOTH handles clear the 44px touch target by real hit-testing in THEIR OWN container with the window's ends far apart AND close together, with the overlapping case measured and its document-order z-rule confirmed; the drawing measures its emitter's own declared size by getBoundingClientRect rather than clientWidth, computes display:block, is centred in its card and captioned by a centred readout with no top margin; the four anchor hours each sit on their own axis; the page does not scroll sideways; and the paint is a FLOOR not a ceiling (CFG-48/CFG-52, 25-04-PLAN.md Task 4)
6. THE handle-stays-on-its-ring check (CFG-73 Bug B, 28-02-PLAN.md Task 2): holding the quiet-hours start handle down with no drag samples its resolved distance from the dial's own centre at least 10 times across at least 400ms, and asserts EVERY sample stays within a stated tolerance of the dial's own `--quiet-dial-radius`; the control's reported value is asserted IDENTICAL before mouse.down() and after mouse.up(); a final post-release sample is asserted on the ring too; and the whole check runs in BOTH themes at the 360px floor
7. the wake interval still SAVES with scripts blocked beside the slider — typed natively, submitted through the real form, re-read FROM DISK after a fresh GET and restored the same way, at 360px and in BOTH shipped languages; the gated range has zero height and no keyboard can reach into it with scripts blocked while it occupies space with them; both gauges are MEASURED (not counted) present on the scripts-blocked page; and the out-of-range trap is re-proven end to end — with 30s on disk the number input carries NO value attribute, no range and no gauge render at all, and the whole Settings form still saves a corrected value (D-09/CFG-49/T-25-05-B, 25-05-PLAN.md Task 3)
8. dragging the wake-interval range moves the native `<input type="number">` the form posts, moves BOTH gauge sentences with it, REVEALS the bar and PERSISTS to disk once Enregistrer is clicked — with the script's own wording asserted EQUAL to the server's for the same two cadences; one ArrowRight moves exactly one stated step and End/Home reach device_config's own ceiling and floor with zero pointer events fired and the recorder proving itself; typing into the number input moves the range back; and at no position does the battery gauge produce a days figure from this fixture's RISING series (CFG-49/CFG-52/T-25-05-C, 25-05-PLAN.md Task 3; retargeted from the retired auto-save onto the restored bar by 28-10-PLAN.md Task 1, CFG-77/CFG-78)
9. the wake-interval slider meets its floors at 360px — its hit area clears the 44px target by real hit-testing in ITS OWN container, it measures wider than the number input it steers and no wider than the card holding it, its wrapper keeps a real top margin off the field's own row, the Device page does not scroll sideways at that width; and the paint is a FLOOR not a ceiling: both gauge sentences and the control's own accent and surface all differ between the two themes and neither sentence is painted in the canvas colour (CFG-49/CFG-52, 25-05-PLAN.md Task 3)

---
*Phase: 31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: `companion/test_browser_ux_quiet_wake.py`
- FOUND: `.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/31-03-SUMMARY.md`
- FOUND commit `c37a4f0` (Task 1)
- FOUND commit `3562290` (Task 2)
- FOUND commit `68e61d0` (Task 3)
