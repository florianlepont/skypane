---
phase: 53
slug: detection-modes-airport-runway-and-position-radius
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-31
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + pytest-xdist + pytest-cov + pytest-socket (non-loopback guard); pytest-playwright for `@pytest.mark.browser` |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`, importlib mode, `--disable-socket` with loopback allowed; `[tool.coverage.report] fail_under = 93`; `[tool.mypy] files`) |
| **Quick run command** | `server/.venv/bin/python -m pytest server/test_airports_catalogue.py server/test_detection_spec.py server/test_orly_replay.py -x -q --cov-fail-under=0` |
| **Full suite command** | `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` (CI command; coverage floor 93) |
| **Other gates** | `server/.venv/bin/ruff check .`; `server/.venv/bin/mypy`; `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`; `server/.venv/bin/python scripts/check_comment_history.py check`; `server/.venv/bin/python -m pytest stub-server/test_phase47_freeze.py -q` |
| **Estimated runtime** | quick about 30 s; companion non-browser about 3 min; full suite per CI |

---

## Sampling Rate

- **After every task commit:** the quick run command plus `server/.venv/bin/ruff check` on touched files.
- **After every plan wave:** `./scripts/run-all-tests.sh -- companion server stub-server` for the touched areas, then ruff, mypy, function-size, comment-history and `stub-server/test_phase47_freeze.py`.
- **Before `/gsd:verify-work`:** full suite green (coverage at or above 93) with `SKYPANE_REQUIRE_BROWSER=1`.
- **Max feedback latency:** 60 seconds for the quick run.

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | DET-01, DET-02 | T-53-01, T-53-04 | Hostile CSV rows rejected; half-width never 0; real designators; parallel rule | unit | `server/.venv/bin/python -m pytest server/test_airports_catalogue.py -x -q --cov-fail-under=0 -k "validation or filter or half_width or swap or rounding"` | ❌ W0 | ⬜ pending |
| 53-01-02 | 01 | 1 | DET-01, DET-02 | T-53-01, T-53-04 | Rebuild byte-identical; absent rows; LFPO 500.0; LFPG 193/192 m; LFMN/LFBO ~150 m; floor | unit | `server/.venv/bin/python -m pytest server/test_airports_catalogue.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-01-03 | 01 | 1 | DET-01 | T-53-02, T-53-03 | Exact-match ids only, capped accent-insensitive search | unit | `server/.venv/bin/python -m pytest server/test_airports_catalogue.py server/test_import_boundaries.py -x -q --cov-fail-under=0 && server/.venv/bin/mypy` | ❌ W0 | ⬜ pending |
| 53-02-01 | 02 | 2 | DET-01, DET-02 | T-53-06, T-53-07 | Unknown/corrupt selection falls back to legacy; runways[display_id] always present | unit | `server/.venv/bin/python -m pytest server/test_detection_spec.py -x -q --cov-fail-under=0 && server/.venv/bin/mypy` | ❌ W0 | ⬜ pending |
| 53-02-02 | 02 | 2 | DET-02 | T-53-08 | Orly decisions identical (fixtures + sweep + both providers); override equals runway3.json; kill switch | unit | `server/.venv/bin/python -m pytest server/test_orly_replay.py server/test_detection_spec.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-03-01 | 03 | 3 | DET-03 | T-53-15 | Airborne-only, <= 10,000 ft, radius edge, lowest first, corroboration | unit | `server/.venv/bin/python -m pytest server/test_plane_detection.py server/test_orly_replay.py -x -q --cov-fail-under=0 -k "position or replay or sweep"` | ✅ extend | ⬜ pending |
| 53-03-02 | 03 | 3 | DET-03 | T-53-11, T-53-12, T-53-13, T-53-14 | Rounded zone only; France box; radius 4..28 km; neighbours share a zone; URLs and logs carry no unrounded coordinate | unit + integration | `server/.venv/bin/python -m pytest server/test_detection_spec.py server/test_position_rounding.py server/test_zone_fetch.py -x -q --cov-fail-under=0 && server/.venv/bin/mypy` | ❌ W0 | ⬜ pending |
| 53-04-01 | 04 | 4 | DET-01, DET-03 | T-53-16, T-53-19 | Shape-only normalisation, three-state save, legacy bytes unchanged, previous-release reader | unit | `server/.venv/bin/python -m pytest server/test_runway_config.py server/test_retired_notifications.py server/test_config_history.py server/test_state_writers.py server/test_poll_loop.py stub-server/test_phase47_freeze.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-04-02 | 04 | 4 | DET-01, DET-03 | T-53-16, T-53-17 | Validated all-or-nothing apply; Orly choices store legacy id | unit | `server/.venv/bin/python -m pytest server/test_detection_settings.py server/test_detection_spec.py server/test_runway_config.py -x -q --cov-fail-under=0 && server/.venv/bin/mypy` | ❌ W0 | ⬜ pending |
| 53-05-01 | 05 | 5 | DET-01, DET-03 | T-53-21, T-53-22 | Per-device resolver; same-airport devices share a zone; corrupt config does not break the fleet | integration | `server/.venv/bin/python -m pytest server/test_fleet_cycle.py server/test_fleet_zones.py server/test_fleet_budget_simulation.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-05-02 | 05 | 5 | DET-02, DET-03 | T-53-20, T-53-24 | Selection gated by the device's own spec; generic vs legacy pipeline identical; freeze green | integration | `server/.venv/bin/python -m pytest server/test_detection_pipeline.py server/test_poll_cycle_steps.py server/test_pipeline_e2e.py server/test_orly_replay.py stub-server/test_phase47_freeze.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-05-03 | 05 | 5 | DET-01, DET-03 | T-53-23 | Tag/heading from display id; legacy text and goldens unchanged; tags fit portrait and landscape | unit | `server/.venv/bin/python -m pytest server/test_render.py server/test_render_landscape_card.py server/test_render_landscape_hold.py server/test_golden_render.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-06-01 | 06 | 6 | DET-01 | T-53-25 | Route x role x owner matrix includes GET/POST /detection (OWNER_DEVICE); other users and unknown ids 404; baseline only gains new keys | HTTP | `server/.venv/bin/python -m pytest companion/test_access_matrix.py companion/test_route_table.py companion/test_render_baseline.py companion/test_device_routes.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-06-02 | 06 | 6 | DET-01 | T-53-26, T-53-27, T-53-28, T-53-29, T-53-30 | No-JS search/pick/save; server-side validation; escaped q; GET read-only; EN/FR | HTTP | `server/.venv/bin/python -m pytest companion/test_detection_page.py companion/test_i18n.py companion/test_access_matrix.py companion/test_route_table.py companion/test_suite_guards.py companion/test_structure_guards.py companion/test_contrast_check.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-07-01 | 07 | 6 | DET-01, DET-03 | T-53-32, T-53-33 | COMPLIANCE.md OurAirports section, rounding statement | doc check | `grep -c "^## OurAirports" COMPLIANCE.md && grep -c "Seven sources" COMPLIANCE.md && grep -c "rounded to two decimals" COMPLIANCE.md` | ✅ | ⬜ pending |
| 53-07-02 | 07 | 6 | DET-01 | T-53-31 | Corrected credits text EN/FR; credits vs COMPLIANCE drift test | unit + HTTP | `server/.venv/bin/python -m pytest companion/test_credits_page.py companion/test_compliance_credits.py companion/test_i18n.py companion/test_suite_guards.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-08-01 | 08 | 7 | DET-03 | T-53-34, T-53-35, T-53-36, T-53-37, T-53-38 | Owner-scoped locations; strict radius and France checks server side; hidden-panel rule; admin saves for owner | HTTP | `server/.venv/bin/python -m pytest companion/test_detection_position.py companion/test_detection_page.py companion/test_i18n.py companion/test_suite_guards.py companion/test_structure_guards.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-08-02 | 08 | 7 | DET-03 | T-53-40 | Carried values re-rendered, guard bypass narrow, invalid carried radius ignored | HTTP | `server/.venv/bin/python -m pytest companion/test_detection_page.py companion/test_companion_app_03.py companion/test_status_pages_04.py companion/test_config_page_04b.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-09-01 | 09 | 7 | DET-01 | T-53-41, T-53-44 | Runway card gone; forged tracked_runway ignored; Display save leaves runway/detection untouched | HTTP | `server/.venv/bin/python -m pytest companion/test_config_page_01.py companion/test_config_page_02.py companion/test_config_page_03.py companion/test_config_page_04.py companion/test_config_page_04b.py companion/test_config_page_05.py -x -q --cov-fail-under=0 -p no:cacheprovider` | ✅ extend | ⬜ pending |
| 53-09-02 | 09 | 7 | DET-01 | T-53-42, T-53-43 | Read-only Detection card + link on Display and Device; history labels survive new ids; baseline diff limited | HTTP | `server/.venv/bin/python -m pytest companion/test_display_detection_card.py companion/test_render_baseline.py companion/test_i18n.py companion/test_access_matrix.py companion/test_route_table.py companion/test_suite_guards.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-12-01 | 12 | 8 | DET-01 | T-53-53 | Remaining non-browser tests describe the removed card; no guard weakened | HTTP | `server/.venv/bin/python -m pytest companion -q -x --cov-fail-under=0 -k "not browser" -p no:cacheprovider` | ✅ extend | ⬜ pending |
| 53-12-02 | 12 | 8 | DET-01 | T-53-54 | Test-support helpers consistent; freeze and baseline unaffected | unit | `server/.venv/bin/python -m pytest test-support companion/test_render_baseline.py stub-server/test_phase47_freeze.py -x -q --cov-fail-under=0` | ✅ extend | ⬜ pending |
| 53-10-01 | 10 | 8 | DET-01, DET-03 | T-53-45, T-53-46, T-53-47 | No-JS flow at 360 px; hidden-panel submit per mode; overflow, hit targets, Search button and accent measured | browser | `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python -m pytest companion/test_browser_detection.py -x -q --cov-fail-under=0 -m browser` | ❌ W0 | ⬜ pending |
| 53-10-02 | 10 | 8 | DET-01, DET-03 | T-53-46 | Dirty bar, Cancel, leave-guard bypass is narrow, typed radius survives search | browser | `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python -m pytest companion/test_browser_detection.py -x -q --cov-fail-under=0 -m browser` | ❌ W0 | ⬜ pending |
| 53-10-03 | 10 | 8 | DET-01 | T-53-46 | Legacy browser tests no longer use the removed Runway card | browser | `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python -m pytest companion/test_browser_phase44_walkthrough.py companion/test_browser_ux_01.py companion/test_browser_ux_03.py companion/test_browser_ux_04.py -x -q --cov-fail-under=0 -m browser` | ✅ extend | ⬜ pending |
| 53-11-01 | 11 | 9 | DET-02 | T-53-48, T-53-49 | Kill switch end to end through run_fleet; scoped to legacy ids; config bytes unchanged | integration | `server/.venv/bin/python -m pytest server/test_detection_kill_switch.py server/test_orly_replay.py server/test_detection_pipeline.py stub-server/test_phase47_freeze.py -x -q --cov-fail-under=0` | ❌ W0 | ⬜ pending |
| 53-11-02 | 11 | 9 | DET-01, DET-02, DET-03 | T-53-50, T-53-51, T-53-52 | All gates; Phase 47 and hardware untouched; no new dependency; no deploy | gate | `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh && server/.venv/bin/ruff check . && server/.venv/bin/mypy && server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server && server/.venv/bin/python scripts/check_comment_history.py check && server/.venv/bin/python -m pytest stub-server/test_phase47_freeze.py -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement coverage

| Requirement | Proven by |
|-------------|-----------|
| DET-01 | 53-01-01..03 (catalogue, designators, absent rows), 53-04 (storage), 53-06 (page), 53-09 and 53-12 (Display/Device), 53-10 (browser) |
| DET-02 | 53-01-02 (parallel airports), 53-02-02 (replay + sweep + drift + evidence + kill switch), 53-05-02 (pipeline equality), 53-11-01 |
| DET-03 | 53-03 (gate, bounds, rounding), 53-05 (zone sharing), 53-08 (position page, locations), 53-10 (browser) |

---

## Wave 0 Requirements

- [ ] `scripts/data/ourairports-fr-airports.csv`, `scripts/data/ourairports-fr-runways.csv`, `scripts/data/ourairports-source.json`, `scripts/data/ourairports-exclusions.json` and `server/data/airports_fr.json` (needed before any catalogue-dependent test can run; plan 01)
- [ ] `server/test_airports_catalogue.py`, `server/test_detection_spec.py`, `server/test_orly_replay.py`, `server/test_position_rounding.py`, `server/test_detection_settings.py`, `server/test_detection_pipeline.py`, `server/test_detection_kill_switch.py` (new files)
- [ ] `companion/test_detection_page.py`, `companion/test_detection_position.py`, `companion/test_display_detection_card.py`, `companion/test_compliance_credits.py`, `companion/test_browser_detection.py` (new files)
- [ ] `test-support/detection_sweep.py` (deterministic sweep helper shared by the replay and parallel tests)
- [ ] Regenerated `companion/testdata/render_baseline.json` (plans 06 and 09, confirmed in 11)
- [ ] No new framework or package install (Playwright Chromium is a tool download already required by CI)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Look of the detection page and the frame tag on a real panel | DET-01, DET-03 | The e-ink render of a new tag (`CDG · 08L/26R`, `NEARBY · 9 KM`) and the owner's taste on the page cannot be asserted by a script; the owner also decides when to deploy | After the owner chooses to deploy: set a spare device to LFPG 08L/26R and to a position, check the panel text and one real wake. Not part of this phase (no deploy). |
| Owner confirmation of the policy numbers | DET-01, DET-03 | The 50 m half-width floor, the 5 degree parallel threshold and the France box are research assumptions the owner accepted (D-18, D-26) | Review the SUMMARY of plans 01 and 03 for the measured results. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s for the quick run
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
