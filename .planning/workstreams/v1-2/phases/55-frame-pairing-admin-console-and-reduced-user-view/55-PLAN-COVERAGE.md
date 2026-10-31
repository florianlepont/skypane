# Phase 55 plan coverage (source audit)

Planned 2026-10-31. 14 plans in 6 waves. Quick test command: `server/.venv/bin/python3 -m pytest <files> -n 4 --no-cov -p no:cacheprovider`.

## Wave and file ownership

| Wave | Plan | Subject | Depends on |
|------|------|---------|------------|
| 1 | 55-01 | Role-conditional reductions (Display, Home, Health, nav, settings form policy); routes still admin-only | none |
| 1 | 55-02 | Schema 3 (`pending_devices`, `audit_log`, `locations.owner_user_id`), typed fleet_db API, `wipe_device_dir` | none |
| 1 | 55-03 | `pairing_code` and `pairing_image` (pure, deterministic) | none |
| 2 | 55-04 | Ownership gate flip, per-route-form access, owner-aware scope, Account frames list, matrix updated | 01, 02 |
| 2 | 55-05 | `fleet_ops`: register, claim, retire, re-activate, reassign | 02, 03 |
| 3 | 55-06 | Real-handler HTTP layer of the matrix (new files only) | 01, 04 |
| 3 | 55-07 | BYOS pending and retired path, `/img/p_<id>/`, CLI verbs, backup and freeze siblings | 02, 03, 05 |
| 3 | 55-08 | CSRF mechanism and retrofit (`/update*` plus four destructive POSTs) | 04 |
| 4 | 55-09 | Console shell: throttle, audit helper, flash, route aggregator, nav, Releases entry, matrix row seams | 02, 04, 08 |
| 5 | 55-10 | Fleet page, register and pair handlers, claim throttling | 05, 09 |
| 5 | 55-11 | Retire, re-activate, reassign handlers, Audit log page, release audit events | 05, 09 |
| 5 | 55-12 | Users page and actions with last-admin guards | 02, 09 |
| 5 | 55-13 | Locations (admin and user) and Display location picker | 02, 09 |
| 6 | 55-14 | Browser tests, full verification, deploy docs, `55-HANDOFF.md` | 06, 07, 10 to 13 |

Same-wave plans touch disjoint files (checked against each plan's `files_modified`). Shared hot files are edited in sequence only: `pyproject.toml` (03 then 05), `companion/routes.py` (04, 08, 09), `companion/app.py` (01, 04, 08, 09, 11), `companion/test_access_matrix.py` and `test-support/access_matrix_support.py` (04, 08, 09), `server/fleet_db.py` (02 only), `companion/pages/config_page.py` (01, 08, 13).

## GOAL and requirements

| Item | Covered by |
|------|-----------|
| Goal: admins add frames to users and manage the fleet | 10, 11, 12, 13 |
| Goal: users manage only their own frames with a simpler view | 01, 04, 06, 13, 14 |
| Success criterion 1 (pair with short single-use expiring audited code) | 03, 05, 07, 10, 14 |
| Success criterion 2 (console: every device with owner/hardware/last seen/battery/firmware; users, reassign/retire, releases) | 09, 10, 11, 12 |
| Success criterion 3 (user sees only own frames, fewer options, no fleet or release controls) | 01, 04, 06, 14 |
| AUTH-04 | 02, 03, 05, 07, 10, 11, 14 |
| AUTH-05 | 01, 04, 06, 08, 09, 10, 11, 12, 13, 14 |

## CONTEXT decisions

| ID | Decision | Plan and task |
|----|----------|---------------|
| D-01 | MAC + secret auth kept, freeze green, expand-only | 07 T1 (live path untouched), 07 T3 (freeze siblings), 02 (expand-only migration) |
| D-02 | No deploy, no real Auth0, no real code or secret | all plans (fake Auth0, codes generated at test time); 14 T2 scan and diff-scope check |
| D-03 | Server-side only, firmware needs reported | 07 context rules, 14 T2 hand-off section D |
| D-04 | Roles anonymous / user / admin only | 04 (matrix kinds), 06 |
| D-05 | Co-management not implemented, `authorized_device_id` unchanged | 04 T2 acceptance (`git diff companion/access.py` empty), 14 hand-off B |
| D-06 | `pending_devices`, devices row only on claim, BYOS reads pending | 02 T1, 05 T1, 07 T1 |
| D-07 | Register form (MAC + SHA-256) and CLI verb, raw secret never accepted | 05 T1, 07 T2, 10 T2 |
| D-08 | Pairing image in the negotiated format, 300 s interval | 03 T2, 07 T1 |
| D-09 | 30-symbol alphabet, 8 chars, normalisation, salted hash, constant time | 03 T1 |
| D-10 | 30 min validity, rotation at next wake, 5 min wake | 03 T1 (constants), 07 T1 (rotation test) |
| D-11 | Atomic single-use claim, identical refusals | 05 T1, 10 T2 |
| D-12 | Claim throttled per session and globally, failures audited without guess | 09 T1 (throttle), 10 T2 |
| D-13 | Reassign wipes previous owner's data, live frame never wiped | 02 T2 (`wipe_device_dir`), 05 T2, 11 T1, 07 T2 (CLI) |
| D-14 | Retire keeps data and token, 24 h retired image, re-activate wipes, stored as `status='retired'` with previous owner, hard delete CLI-only | 02 T1/T2, 05 T2, 07 T1/T2, 11 T1 |
| D-15 | Console pages: Fleet, Users, Audit, Releases, Locations; open frame pages from Fleet | 09 (nav, Releases), 10 (Fleet), 12 (Users), 11 (Audit), 13 (Locations) |
| D-16 | User per-frame options and exclusions | 01, 04, 06 |
| D-17 | User Health frame-only, platform health admin-only | 01 T2, 06 T2 |
| D-18 | Locations for both roles, owner column, quota, validation, rate limit | 02 T1/T2, 13 |
| D-19 | Append-only audit_log, events list, read-only page | 02 T1 (triggers, API), 09 T1 (helper), 10, 11, 12, 13 (events), 11 T2 (page, release events) |
| D-20 | CSRF on new admin/pairing POSTs, `/update*`, four existing destructive POSTs | 08 (mechanism, retrofit), 10, 11, 12, 13 (`csrf=True` on new routes) |
| D-21 | One expand-only migration to schema 3, freeze and backup tests cover new tables, rollback caveat surfaced | 02 T1, 07 T3, 14 hand-off |

Owner facts to report: redraw cost, white after claim, migration index 3, no firmware need: 14 T2 (`55-HANDOFF.md` section D).

## Phase 54 hand-off section A

| Item | Plan |
|------|------|
| Real `/d/<id>/...` routes with `Access(USER, "device")` | 04 T2 |
| One matrix row per route and derived resource | 04 T2 (kinds, un-prefixed table), 09 T2 (row seams), 10 to 13 (new rows) |
| Probe family kept as canary | 04 T2 Test 6 |
| Re-run the HTTP layer with the real handlers | 06 |
| Account Frames empty state replaced | 04 T3 |
| Per-session CSRF revisited | 08 |
| Co-management extends `authorized_device_id` | 14 hand-off B (not implemented, D-05) |

## RESEARCH constraints and landmines

| Item | Plan |
|------|------|
| Pattern 1 per-route-form access (`_effective_access`) | 04 T2 |
| Pitfall 2 mass assignment on `/settings` | 01 T1, 06 T2 |
| Pitfall 3 live frame owned by a user, un-prefixed links | 04 T1, 06 T1 |
| Pitfall 4 and landmine 6: never write legacy files for pending frames | 07 T1, 07 T3 |
| Pitfall 5, landmine 7: pairing images outside `img/` and the backup | 07 T1, 07 T3 |
| Pitfall 6: MAC in both tables | 02 T1/T2, 07 T1 (`_apply_mirror`) |
| Pitfall 7: hash churn | 03 T2, 07 T1 |
| Pitfall 8: frame-only severity everywhere | 01 T2 |
| Pitfall 9: last admin and self-disable races | 02 T2, 12 T2 |
| Pitfall 10: identical refusals and timing | 03 T1, 05 T1, 10 T2 |
| Pitfall 11: white after claim | 14 hand-off D |
| Landmine 2: matrix semantics change | 04 T2 |
| Landmine 5: `registry_view`/`tokens_by_mac` untouched | 02 T1, 07 T1 |
| Landmine 8: `_handle_display` size budget | 07 T1 |
| Landmine 9: freeze list owner-only | 07 (sibling freeze file), 02 |
| Landmine 10: rollback caveats | 14 hand-off |
| Landmine 11: hard-coded schema version tests | 02 T1 |
| Landmine 12: throttle in memory | 09 context, 14 hand-off |
| Landmine 13: CSRF needs cached form | 08 T1 |
| Landmine 14: i18n and guards | every UI plan (`companion/test_i18n.py`, comment-history) |
| Landmine 15: Phase 52/56 hot files | 01 (bounded gating edits), 09, 13 (bounded config_page edit); `_handle_poll_now` and poll files never edited |
| Landmine 16: `devices remove` pending and retired | 07 T2 |
| Landmine 19: user calendar connect SSRF | 06 T2 Test 5 |
| Landmine 20: production safety | 14 T2 |
| Stale research items found at planning time | `auth.LoginThrottle` no longer exists (09 builds `LockoutThrottle`); `legacy-admin` fallback removed on main (no principal for it); line numbers stale (plans reference names) |

## Deferred ideas check

Co-management (Phase 60), firmware recovery after 401 and on-device pairing UI (Phase 57), view-as-user (AUTH-07), audit purge or export: no task implements any of them (the audit page has no route besides one GET; CLI assign wipe is D-13, not co-management).
