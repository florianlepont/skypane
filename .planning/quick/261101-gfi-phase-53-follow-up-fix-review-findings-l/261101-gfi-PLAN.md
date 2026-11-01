---
phase: quick-261101-gfi
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/detection.py
  - companion/detection_summary.py
  - companion/pages/detection_page.py
  - server/test_detection_spec.py
  - server/test_detection_settings.py
  - server/zone_fetch.py
  - server/poll_cycle.py
  - server/fleet_cycle.py
  - server/test_fleet_cycle.py
  - server/test_poll_cycle_steps.py
  - server/fleet_db.py
  - companion/detection_actions.py
  - companion/console_locations.py
  - server/test_fleet_schema3.py
  - companion/test_location_picker.py
  - companion/test_detection_position.py
  - companion/routes.py
  - companion/test_access_matrix.py
  - companion/test_detection_page.py
  - companion/test_browser_detection.py
  - .planning/workstreams/v1-2/phases/53-detection-modes-airport-runway-and-position-radius/53-REVIEW.md
autonomous: true
requirements: [LW-01, LW-03, LW-04, LW-06]
must_haves:
  truths:
    - "The rule 'position mode without a usable location' lives in exactly one function"
    - "A device never gates a fetch of another zone: on zone mismatch it keeps its image and reports stale zone"
    - "A location owned by user A cannot be assigned to a device owned by user B, by anyone; NULL-owner locations stay assignable by admins"
    - "device_location_name never returns a location name the viewer may not see"
    - "POST /detection and the location form require the CSRF token"
  artifacts:
    - path: "server/fleet_db.py"
      provides: "cross-owner refusal in set_device_location_checked"
    - path: "server/poll_cycle.py"
      provides: "zone check in _select_from_zone"
  key_links:
    - from: "companion/pages/detection_page.py"
      to: "companion/detection_summary.is_fail_safe"
      via: "single rule"
---

<objective>
Fix four low-severity review findings from the Phase 53 review (LW-01, LW-03, LW-04, LW-06), one atomic commit per finding, then run the full gate and add a "Fixed" note per finding to 53-REVIEW.md. The owner approved all four. Do not commit planning ROADMAP/STATE; do not touch Phase 47 files, hardware/, stub-server/, deploy/. No deploy.

Constraints for every task: English comments with no plan, phase or finding IDs; functions at most 80 lines; tests assert behaviour (served HTML, browser, DB state), never source text; keep `ruff`, mypy module list, `scripts/check_comment_history.py` clean. Commit messages end with the attribution trailer given in the session system reminder. Run each commit only after that task's targeted tests pass.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/workstreams/v1-2/phases/53-detection-modes-airport-runway-and-position-radius/53-REVIEW.md
@CLAUDE.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (LW-01): one source for the fail-safe rule</name>
  <files>server/detection.py, companion/detection_summary.py, companion/pages/detection_page.py, server/test_detection_spec.py, server/test_detection_settings.py</files>
  <read_first>
    - server/detection.py (DetectionSpec ~88-101, no_location_spec, _position_spec, _spec_from_doc, legacy_orly_spec, _legacy_spec, _catalogue_spec, spec_for ~407-431)
    - companion/detection_summary.py (is_fail_safe ~38)
    - companion/pages/detection_page.py (~250-265 `self.fail_safe = ...`, fail_safe_toast_html ~364)
    - server/test_detection_spec.py lines ~38, 58, 86, 282, 314, 326, 341; server/test_detection_settings.py ~145
  </read_first>
  <behavior>
    - Detail page for a position setting whose device has no usable location still shows the fail-safe toast; with a usable location or in runway mode it does not.
    - spec_for on corrupt or unknown config still returns the default Orly runway spec (display_id, zone unchanged).
  </behavior>
  <action>
    Verified by grep: `DetectionSpec.fail_safe` and its `fail_safe` parameters (`_spec_from_doc`, `legacy_orly_spec`, `_legacy_spec`, and the True/False arguments in `spec_for`/`_catalogue_spec`) are read only by tests; the page computes its own copy at detection_page.py:261 and `detection_summary.is_fail_safe` has no caller. Delete the dead copy in server: remove the `fail_safe` field from DetectionSpec, drop the parameter from `_spec_from_doc`, `legacy_orly_spec` (keep its other params and positional order for existing callers; grep callers first, including test_detection_kill_switch), `_legacy_spec`, and every call site, and fix the `spec_for` docstring (it must stop mentioning `fail_safe`). Keep the surviving single rule in `companion/detection_summary.is_fail_safe(selection, location_name)` and make detection_page.py:261 call it (`detection_summary.is_fail_safe(selection, location_name)` using the selection already loaded in that constructor; import detection_summary if not already imported, check for import cycles). Update tests: replace every `spec.fail_safe is True/False` assertion with an assertion on the observable behaviour (for corrupt config: `display_id`/`zone` equal the default Orly runway spec; for position without location: `no_location is True`). Add a companion test (in the existing detection page test module style) that renders the detection page for a position-mode device with no usable location and asserts the toast text is in the served HTML, and absent for a usable location.
  </action>
  <verify>
    <automated>python -m pytest server/test_detection_spec.py server/test_detection_settings.py server/test_detection_kill_switch.py companion/test_detection_page.py companion/test_display_detection_card.py -x -q -p no:cacheprovider</automated>
  </verify>
  <done>No `fail_safe` attribute or parameter remains in server/detection.py (`grep -n "fail_safe" server/detection.py` prints nothing); the rule exists once in detection_summary.is_fail_safe and the page uses it; tests green; commit "fix(detection): LW-01 ..." written without IDs in code comments.</done>
  <acceptance_criteria>
    - grep -rn "\.fail_safe\b" server companion (python files) shows only `view.fail_safe` in the page layer
    - toast shown/hidden behaviour test passes
    - one commit containing only LW-01 changes
  </acceptance_criteria>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (LW-03): refuse to gate a fetch of another zone</name>
  <files>server/zone_fetch.py, server/poll_cycle.py, server/fleet_cycle.py, server/test_fleet_cycle.py, server/test_poll_cycle_steps.py</files>
  <read_first>
    - server/zone_fetch.py (ZoneFetch dataclass, fetch_zone)
    - server/poll_cycle.py (_fetch_standalone ~915, _select_from_zone ~924, detect_flight ~938, run_once ~1410-1500 to see how an exception propagates and what state is written before detect_flight)
    - server/fleet_cycle.py (detection_resolver ~260, _FleetRun.run_device ~384, fetch ~412, serve_zone ~426, STATUS_* constants ~47)
    - server/test_fleet_cycle.py (how a fake runner/fetcher/resolver is wired; the ANSWERED fixture ~206 and line ~519 run_once call)
  </read_first>
  <behavior>
    - A ZoneFetch stamped with zone A's key, run by a device whose spec zone is B: no selection happens, the poll state/image is unchanged, the fleet outcome status is "stale_zone".
    - A ZoneFetch with no stamp (None; tests and legacy callers) behaves as before.
    - Same zone: unchanged behaviour.
    - Setting changes between plan and run: plan_zones puts the device in zone A, the device config is rewritten to a different airport before run_device, the device is not gated against A's aircraft and the next cycle (re-planned) serves it normally.
  </behavior>
  <action>
    1. In zone_fetch.py add an optional frozen field `zone_key: str | None = None` to ZoneFetch (last field, so positional constructions stay valid), documented as the key of the zone the aircraft were fetched for. fetch_zone itself keeps its signature; stamping is done by the callers that know the Zone.
    2. In fleet_cycle `_FleetRun.fetch`, stamp the result with `dataclasses.replace(fetched, zone_key=zone.key)` (also for the `_failed_fetch()` fallback). In poll_cycle `_fetch_standalone`, stamp with `ctx.spec.zone.key` the same way.
    3. In poll_cycle define `class StaleZone(Exception)` (module level, documented). In `_select_from_zone`, after obtaining `fetched`, if `fetched.zone_key is not None and fetched.zone_key != spec.zone.key` raise StaleZone before any selection. Confirm in run_once that the exception leaves poll state and the current image untouched (no persist before detect_flight; lock released); if some state is written earlier, move or guard it so a StaleZone leaves it as it was.
    4. In fleet_cycle add `STATUS_STALE_ZONE = "stale_zone"`; in `run_device` catch `poll_cycle.StaleZone` next to `PollBusy` and record that status with a short detail (no trace). `count()` and any status summary/logging keyed on status names must accept the new status (grep STATUS_ usages incl. systemd-facing exit codes; a stale zone must not make the oneshot exit non-zero or count as FAILED). Do not mark the zone served for stale devices (existing `ran` logic already only counts OK/FAILED).
    5. Tests: in test_poll_cycle_steps.py add a test that runs a cycle with a ZoneFetch stamped with a different zone key and asserts StaleZone is raised and the poll state file is byte-identical. In test_fleet_cycle.py add a test using the real `detection_resolver` and the real `poll_cycle.run_once` (or the file's existing equivalent) where the device config is rewritten (e.g. via device_config save of a different runway) after `plan_zones` and before the group is served; assert the outcome status is stale_zone, the device's rendered/current image file is unchanged, and a second run_fleet pass serves it with status ok.
  </action>
  <verify>
    <automated>python -m pytest server/test_fleet_cycle.py server/test_poll_cycle_steps.py server/test_poll_loop.py server/test_zone_fetch.py server/test_fleet_budget_simulation.py -x -q -p no:cacheprovider</automated>
  </verify>
  <done>Mismatched-zone fetch is never gated; fleet reports stale_zone; the changing-setting test fails on the old code and passes now.</done>
  <acceptance_criteria>
    - New tests fail when the zone comparison is removed (executor confirms once by temporarily disabling it)
    - Existing tests using unstamped ZoneFetch fixtures pass unchanged
    - Exit status of the fleet run is unchanged by a stale_zone outcome
    - one commit containing only LW-03 changes
  </acceptance_criteria>
</task>

<task type="auto" tdd="true">
  <name>Task 3 (LW-04): refuse cross-owner device/location links</name>
  <files>server/fleet_db.py, companion/detection_actions.py, companion/console_locations.py, server/test_fleet_schema3.py, companion/test_location_picker.py, companion/test_detection_position.py</files>
  <read_first>
    - server/fleet_db.py (set_device_location_checked ~680-714, get_location, list_locations_for, set_device_location ~873)
    - companion/detection_actions.py (scope_for ~67-84, card_location_name ~95, _store_detection ~176, _write_location ~246)
    - companion/console_locations.py (apply_device_location ~460-510 and its picker rows ~405-420, ownerless device handling at ~413)
    - companion/test_location_picker.py ~100-320 (admin assignment tests at ~270-300 incl. the "platform" location), server/test_fleet_schema3.py ~405-436, companion/test_console_locations.py (admin console edit/delete paths), companion/test_detection_position.py ~471
    - server/fleet_ops.py ~472 (ownership transfer clears location_id)
  </read_first>
  <behavior>
    - owner(device)=B, owner(location)=A, A != B, both non-NULL: refused with PermissionError for admins and users alike; device row unchanged.
    - location owner NULL (platform location): admin may assign it to any device; device owner NULL with an owned location: unchanged from today (no cross-owner conflict since a side is NULL).
    - A non-admin viewing a device whose stored location_id belongs to another owner gets `device_location_name` None; an admin viewing sees the name.
  </behavior>
  <action>
    Pre-check (mandatory, before editing): grep every caller of `set_device_location_checked`, `apply_device_location`, `_store_detection` and every test that assigns a location to a device with different owners (test_location_picker.py lines ~255-300, test_console_locations, test_console_pairing, test_fleet_ops, test_detection_position ~471). Confirm no production flow (Phase 55 admin console Display-form picker, device pairing, detection page) needs an admin to link owner-A location to owner-B device. If any legitimate flow does, STOP, do not edit code, and append a `## BLOCKER` section to this PLAN.md naming the flow, then return that to the orchestrator. If only tests assert the cross-owner admin assignment as a feature of the old behaviour (for example an admin assigning `target` at test_location_picker ~281), convert them to the new rule (refusal, or use a NULL-owner location) and say so in the commit message.
    1. fleet_db.set_device_location_checked: after resolving `loc` (inside the same `_atomic` block), for every actor (including admin) raise PermissionError("location belongs to another owner") when `loc["owner_user_id"] is not None and device["owner_user_id"] is not None and loc["owner_user_id"] != device["owner_user_id"]`. Keep the existing non-admin checks. Update the docstring ("an admin may assign any location" becomes: any location not owned by a different user than the device owner).
    2. The two callers already map PermissionError to a refusal (`ERROR_LOCATION_UNAVAILABLE` in detection_actions._store_detection; `_deny_assignment` audited denial in console_locations.apply_device_location); verify and keep that, no new error text needed.
    3. Edit path: in detection_actions._write_location the edit target is already limited to rows owned by the subject; add a check that when `subject.is_admin` acts on another user's device the location written belongs to the device owner (`subject.subject_id` is the device owner, confirm in subject_for) so an admin cannot edit a location owned by a third party through this form. Add a test.
    4. scope_for: set `name` only when the location is usable AND (`located["owner_user_id"] is None` or equals `subject.subject_id` or `subject.is_admin`) so a non-admin never receives another owner's location name via `device_location_name`; same rule must hold for `card_location_name` (it goes through scope_for).
    5. Tests: server/test_fleet_schema3.py add cases (admin cross-owner refused, admin NULL-owner location assigned, device row unchanged after refusal); companion tests: detection POST for a device whose owner differs from a forged location_id returns the inline location error and leaves the DB untouched; a non-admin GET of the Display/Detection page for a device whose stored location belongs to someone else does not contain that location's name in the served HTML (seed with a direct SQL UPDATE as the existing tests do).
  </action>
  <verify>
    <automated>python -m pytest server/test_fleet_schema3.py server/test_fleet_ops.py companion/test_location_picker.py companion/test_console_locations.py companion/test_console_pairing.py companion/test_detection_position.py companion/test_detection_page.py companion/test_display_detection_card.py -x -q -p no:cacheprovider</automated>
  </verify>
  <done>Cross-owner link impossible through set_device_location_checked and both UI paths; name does not leak; NULL-owner locations still assignable by admins.</done>
  <acceptance_criteria>
    - Pre-check result recorded in the commit body (callers audited, no legitimate cross-owner flow) or BLOCKER appended and work stopped
    - New tests fail against the old fleet_db code
    - one commit containing only LW-04 changes
  </acceptance_criteria>
</task>

<task type="auto" tdd="true">
  <name>Task 4 (LW-06): CSRF token on the detection and location forms</name>
  <files>companion/routes.py, companion/pages/detection_page.py, companion/test_access_matrix.py, companion/test_detection_page.py, companion/test_detection_position.py, companion/test_browser_detection.py</files>
  <read_first>
    - companion/routes.py (_POST_ROUTES DETECTION_ROUTE entry ~218-220; CSRF_ROUTE_KEYS ~317-325; the ROUTES comprehension ~327; how console routes pass `csrf=True`)
    - companion/ui_components.py csrf_field ~175
    - companion/pages/detection_page.py forms at ~391 and ~716 (and how calendar/rules pages place `csrf_field()`; grep "csrf_field" in companion/pages)
    - companion/test_access_matrix.py ~370-390 (how it posts with a token), companion/test_csrf.py ~150-250 (route-level CSRF test pattern), companion/test_detection_page.py and test_detection_position.py (every POST helper), companion/test_browser_detection.py
    - companion/conftest.py and test-support/companion_app_server.py `with_csrf`
  </read_first>
  <behavior>
    - POST /detection without a token: 403, nothing stored. With a valid token: unchanged behaviour (303 or inline 200 errors).
    - Both served forms contain exactly one hidden `csrf_token` input for the signed-in session.
    - Browser flow (save detection, add/edit a location) still works end to end.
  </behavior>
  <action>
    1. routes.py: follow how the other converted routes are declared. Existing form routes (rules add, calendar connect) are in `CSRF_ROUTE_KEYS`; add `("POST", Exact(DETECTION_ROUTE))` to that set, which is the pattern in this file (do not invent a second mechanism). Fix the comment above the set only if it becomes inaccurate (it lists "destructive and release actions"; reword to cover form posts that change location data, no IDs).
    2. detection_page.py: insert `layout.csrf_field()` (use whichever import the sibling pages use for `csrf_field`) as the first child inside both `<form method="post" ...>` elements (detection form ~391, location form ~716), matching the placement used in the calendar/rules forms. Dirty-form tracking (`data-dirty-form`) must ignore the hidden field as it does elsewhere; check the JS/serialisation does not post the token twice.
    3. Tests: update every helper that POSTs to /detection (test_detection_page.py, test_detection_position.py, test_browser_detection.py, test_access_matrix.py, any other hit of `/detection` POST found by grep of companion/test_*.py) to send the token via `with_csrf(cookie, fields)` (non-browser) — the browser tests submit the real form so need no change but must pass. In test_access_matrix.py, the table of POST routes expected to require a token must include the detection route (follow the existing entry style at ~382). Add tests: missing token is 403 and the stored config/location is unchanged; the served detection page and the location form each include the hidden token input equal to `auth.csrf_token` of the session (pattern at test_csrf.py ~231-243); a token from a different session is 403.
    4. Remove the now-false statement that detection relies on SameSite only wherever the comment sits (routes.py comment near the quick LED route is about LED only; leave it).
  </action>
  <verify>
    <automated>SKYPANE_REQUIRE_BROWSER=1 PLAYWRIGHT_BROWSERS_PATH=/tmp/claude-0/-home-user-skypane/35128d4b-9517-5708-a757-26023530ab20/scratchpad/pw python -m pytest companion/test_access_matrix.py companion/test_csrf.py companion/test_detection_page.py companion/test_detection_position.py companion/test_browser_detection.py companion/test_device_routes.py companion/test_display_detection_card.py -x -q -p no:cacheprovider</automated>
  </verify>
  <done>/detection POSTs require the token; both forms carry it; all dependent tests updated and green, including the browser test.</done>
  <acceptance_criteria>
    - 403 without token test passes; forms contain token test passes
    - No test posts to /detection without a token except the explicit negative tests
    - one commit containing only LW-06 changes
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 5: full gate and review notes</name>
  <files>.planning/workstreams/v1-2/phases/53-detection-modes-airport-runway-and-position-radius/53-REVIEW.md</files>
  <read_first>
    - scripts/run-all-tests.sh, scripts/check_function_size.py, scripts/check_comment_history.py, pyproject.toml [tool.mypy]
    - the 53-REVIEW.md Low section (existing "**Fixed:**" note style at LW-02/LW-05 lines)
    - how the Phase 47 freeze is checked (grep scripts/ and .github/workflows for "freeze" / "phase-47"; use that exact command)
  </read_first>
  <action>
    1. Ensure browsers: `ls /opt/pw-browsers`; under PLAYWRIGHT_BROWSERS_PATH=/tmp/claude-0/-home-user-skypane/35128d4b-9517-5708-a757-26023530ab20/scratchpad/pw recreate the `chromium-1248` and `chromium_headless_shell-1248` symlinks pointing at the installed 1243 builds in /opt/pw-browsers if missing.
    2. Run, fixing any failure in the owning finding's commit (use a fixup into that commit, keep one commit per finding): `ruff check .`, mypy using the module list in pyproject (`mypy` with no args if configured), `python scripts/check_function_size.py`, `python scripts/check_comment_history.py check`, the Phase 47 freeze check, then `PLAYWRIGHT_BROWSERS_PATH=/tmp/claude-0/-home-user-skypane/35128d4b-9517-5708-a757-26023530ab20/scratchpad/pw SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`. Confirm the coverage gate still passes (new code is covered by the added tests).
    3. In 53-REVIEW.md add a `**Fixed:**` line under each of LW-01, LW-03, LW-04, LW-06 (same format as the LW-02 note, one sentence each: single fail-safe rule and dead field removed; zone-stamped fetch and stale_zone skip; cross-owner link refused and location name gated; CSRF token required on detection and location forms). Commit these notes as a fifth small commit "docs(53): record review fixes". Do not edit ROADMAP.md or STATE.md.
    4. `git status` must show only the intended files; `git diff origin/main --stat` must show nothing under hardware/, stub-server/, deploy/ or Phase 47 files.
  </action>
  <verify>
    <automated>PLAYWRIGHT_BROWSERS_PATH=/tmp/claude-0/-home-user-skypane/35128d4b-9517-5708-a757-26023530ab20/scratchpad/pw SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh</automated>
  </verify>
  <done>Every gate green; four fix commits plus one docs commit; 53-REVIEW.md carries four Fixed notes.</done>
  <acceptance_criteria>
    - ruff, mypy, function-size, comment-history, Phase 47 freeze, full test run all exit 0
    - git log shows one commit per finding
    - no files outside the list above changed
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| browser to companion POST | cross-site form posts to /detection with ambient session cookie |
| admin surface to fleet.db | admin-chosen location_id assigned to another owner's device |
| poll plan to poll run | config can change between zone planning and device run |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-qgfi-01 | Tampering | POST /detection, location form | mitigate | CSRF token required (route in CSRF_ROUTE_KEYS, field in both forms) |
| T-qgfi-02 | Information disclosure | scope_for device_location_name | mitigate | name only returned when location owner is NULL, the subject, or viewer is admin |
| T-qgfi-03 | Tampering / Elevation | set_device_location_checked | mitigate | refuse when both owners non-NULL and different, for admins too |
| T-qgfi-04 | Tampering | zone/spec mismatch in one cycle | mitigate | ZoneFetch zone_key compared with spec zone key; StaleZone skip |
| T-qgfi-SC | Tampering | package installs | accept | no new dependencies are added |
</threat_model>

<verification>
Targeted tests per task, then the full gate in Task 5.
</verification>

<success_criteria>
LW-01, LW-03, LW-04, LW-06 fixed with tests, one commit each, full gate green, REVIEW notes added, no out-of-scope files touched.
</success_criteria>

<output>
Create `.planning/quick/261101-gfi-phase-53-follow-up-fix-review-findings-l/261101-gfi-SUMMARY.md` when done.
</output>
