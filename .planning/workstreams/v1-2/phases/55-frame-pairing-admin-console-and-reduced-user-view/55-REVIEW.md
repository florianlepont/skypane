---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
reviewed: 2026-10-31T00:00:00Z
depth: deep
files_reviewed: 41
files_reviewed_list:
  - server/fleet_ops.py
  - server/fleet_db.py
  - server/pairing_code.py
  - server/pairing_image.py
  - server/device_dirs.py
  - stub-server/byos_server.py
  - stub-server/fleet_cli.py
  - deploy/backup/skypane_backup.py
  - companion/app.py
  - companion/auth.py
  - companion/audit.py
  - companion/throttle.py
  - companion/route_types.py
  - companion/routes.py
  - companion/console_routes.py
  - companion/console_flash.py
  - companion/console_lifecycle.py
  - companion/console_locations.py
  - companion/console_pairing.py
  - companion/console_users.py
  - companion/device_dispatch.py
  - companion/device_scope.py
  - companion/user_view.py
  - companion/freshness.py
  - companion/page_context.py
  - companion/layout.py
  - companion/pages/account_page.py
  - companion/pages/audit_page.py
  - companion/pages/config_page.py
  - companion/pages/fleet_page.py
  - companion/pages/health_page.py
  - companion/pages/home_page.py
  - companion/pages/locations_page.py
  - companion/pages/update_page.py
  - companion/pages/users_page.py
  - companion/settings/calendar.py
  - companion/settings/form_post.py
  - companion/ui_nav.py
  - companion/ui_shell.py
  - server/plane/calendar_rules/__init__.py
findings:
  critical: 1
  warning: 4
  info: 9
  total: 14
status: issues_found
---

# Phase 55: Code Review Report

**Reviewed:** 2026-10-31
**Depth:** deep
**Files Reviewed:** 41 (some read in the parts the phase touches: `app.py` dispatch, `byos_server.py` pairing and device-context paths, `config_page.py` settings/scope, `health_page.py`/`home_page.py` user reductions, `ui_shell.py` selector)

## Summary

The core security design holds up under adversarial tracing.

- **Claim atomicity:** `claim_pairing_code` is one `BEGIN IMMEDIATE` transaction (scan, `DELETE`, `add_device`, provision, audit). Two concurrent claims cannot both win, and the code is single-use.
- **Wrong, expired, used and malformed codes:** they raise the same `ClaimRefused` after the same all-row constant-time scan. The dummy code is used for malformed input.
- **Audit and logs:** no guess or code reaches any audit row, flash, log line or URL. `audit_append` has no code parameter.
- **Authorization (IDOR):**
  - `access.decide` and `_effective_access` give 404 for a user on admin routes and on a foreign `/devices/<id>`.
  - The un-prefixed device routes are forced admin-only.
  - `load_devices_for` filters by owner.
  - Location edit and delete return the same 404 for foreign, ownerless and unknown ids.
  - `set_device_location_checked` re-checks ownership of both frame and location inside the transaction.
  - The location picker hides the name of an admin-assigned location from the user.
- **Role escalation:** the role is read only from `users.role`. Role names are whitelisted, and the last-admin and self-action guards share one transaction with the write.
- **Path and SQL safety:** device directories come only from `resolve_state_dir` (shape check, then realpath containment, symlinks refused). `wipe_device_dir` refuses ".". Path captures are regex-checked with `\Z`, and all SQL is parameterised. The only string-built SQL (`_target_name`, `_audit_where`) uses fixed or validated fragments.
- **XSS and redirects:** all dynamic output goes through `escape_html(quote=True)`. Redirect targets are allow-lists of fixed routes or validated ids, and the flash cookie only looks up registered keys.
- **Live frame:** nothing in `fleet_ops` touches the live frame's files. Reassigning it changes only the owner. Retire is refused and audited. `byos_server` pending handling writes only under `pairing/<id>`.

What remains is one data-loss ordering problem in the destructive operations, some partial-write and consistency issues, CSRF coverage that is narrower than the phase intent, and robustness and hygiene items.

## Critical Issues

### CR-01: Reassign and re-activate wipe the directory inside the transaction, before commit, with no guard against byos writers and no error handling in the handlers

**File:** `server/fleet_ops.py:340-342` (reassign), `server/fleet_ops.py:406-408` (reactivate); `companion/console_lifecycle.py:193-209`, `companion/console_lifecycle.py:155-164`
**Issue:** `wipe_device_dir` (an irreversible `shutil.rmtree`) and the re-provision run *before* the audit insert and `COMMIT`. Two consequences:

1. **Data loss on failure.** If anything after the wipe fails, the database change rolls back and the old owner keeps the frame row, but its config, history, gallery and calendar secret are already gone. Failure points include `provision_device_dir` (`OSError`), the `OpsError("fresh panel image missing or the wrong size")` check, `audit_append`, and the `COMMIT` itself. For reactivate, the "Its data is kept" promise of retire is broken in the same way.
2. **The busy guard does not cover the real concurrent writer.** `busy_guard` takes only the in-process poll lock and the poll-cycle flock. The byos service (a separate unit) writes `battery_state.json` and `history.db` into `devices/<id>/` on every display poll (`byos_server._handle_display` → `save_battery_state`, `_record_device_health`). A write that lands during `rmtree` can make `rmdir` fail (`ENOTEMPTY`), leaving a half-wiped tree.

`handle_reassign` and `handle_reactivate` catch only `NotFound`, `OwnerUnavailable` and `FrameBusy`. `OpsError`, `ValueError` (bad `state_path`), `OSError` and `sqlite3.Error` propagate as a 500, so the admin sees no flash and no audited failure, while the data may already be destroyed.

**Fix:** Make the database the last thing that can fail before the destructive step.
- Move the old directory aside first (`os.rename(dir, dir + ".wipe-<token>")` inside the guard). Do the DB update and audit, `COMMIT`, then `rmtree` the renamed directory. On rollback, rename it back.
- Provision the fresh directory only after the rename.
- Catch `fleet_ops.OpsError`, `ValueError`, `OSError` and `sqlite3.Error` in the two handlers. Write a `failed` audit row and redirect with a flash.

```python
# fleet_ops.reassign_frame (non-live branch), sketch
aside = _move_aside(root, dev["state_path"])      # rename, reversible
try:
    conn.execute("UPDATE devices SET owner_user_id=?, location_id=NULL, name=NULL WHERE id=?", ...)
    _provision_fresh(root, ...)
    fleet_db.audit_append(...)
except BaseException:
    _restore(aside); raise
# after COMMIT:
shutil.rmtree(aside, ignore_errors=True)
```

## Warnings

### WR-01: Reassigning the live frame leaves the previous owner's data (calendar secret, name, location, history) with the new owner

**File:** `server/fleet_ops.py:329-333`
**Issue:** The live branch changes only `owner_user_id`. The state root keeps the previous owner's `calendar_url.secret`. The poll loop keeps colouring flights from that private iCal feed, and the new owner's Display page reports "Connected" for a link they never entered and cannot see. The frame `name` and `location_id` also stay. The location is owned by the previous owner (`list_locations_for` hides it from the new owner), so the new owner cannot see or change it, and the picker shows it as "assigned". Flights history, gallery and manual resolutions carry over to a possibly different (plain) user. The "Only the owner changes. Nothing is erased." sentence tells the admin about the file wipe but not that private data transfers.
**Fix:** When the live frame moves to a different non-admin owner, at least clear the calendar secret and registry and null `location_id` and `name` in the same transaction. Alternatively, require an explicit "also clear private settings" choice on the confirm form and audit it. Keep the file-wipe prohibition for everything else.

### WR-02: `apply_device_location` commits before the settings save, so a failed save leaves a half-applied form

**File:** `companion/pages/config_page.py:879-890`, `companion/console_locations.py:480-495`
**Issue:** The location change commits (with its audit row) before `save_device_config`. If `save_device_config` then raises `ValueError` or `OSError`, the handler returns `FLASH_SAVE_FAILED` ("nothing applied") although the location was already changed and audited. The comment in `handle_post` ("a refused assignment leaves everything unchanged") covers only the opposite order.
**Fix:** Run the config save first and apply the location afterwards. Alternatively, return a distinct partial-failure flash. A cleaner design takes one fleet transaction that also writes the config, or rolls the assignment back when the save fails.

### WR-03: Per-session CSRF covers only the new console routes and a subset of old ones; every other state-changing POST relies on SameSite plus an Origin check that allows header-less requests

**File:** `companion/routes.py:297-305`, `companion/routes.py:213-218`, `companion/auth.py:176-211`
**Issue:** `CSRF_ROUTE_KEYS` lists only rule delete, calendar disconnect, manual-resolution delete, rename reset, and release install and cancel. These POSTs are session-gated but have no token:
- `/settings` (reachable by plain users: toggles, theme, quiet hours, calendar URL, location assignment)
- `/quick/display`, `/quick/quiet-hours`, `/quick/led`
- `/settings/calendar/connect` (triggers an outbound fetch)
- `/rules/add`
- airline resolve and rename
- illustration replace
- `/ui-theme`, `/ui-lang`, `/logout`

`post_origin_ok` allows requests with no `Origin` header, and only `Sec-Fetch-Site: same-site` or `cross-site` is blocked. Protection therefore rests on `SameSite=Strict` alone for those routes, while the phase adds a token elsewhere, which implies the intent was full coverage. The route comment on `/quick/led` already admits this.
**Fix:** Set `csrf=True` on every authenticated POST route. The shared `csrf_field()` is already emitted by the forms that need it; check the quick-switch fetch path and `freshness.js` forms send the field.

### WR-04: CLI reassign and re-activate wipe a frame directory with no busy guard

**File:** `stub-server/fleet_cli.py:234-235`, `stub-server/fleet_cli.py:278`
**Issue:** `cmd_devices_assign` and `cmd_devices_reactivate` call `reassign_frame` and `reactivate_frame` without a `busy_guard`. They can `rmtree` a directory while the poll timer is mid-cycle writing to it. This is the same hazard as CR-01, with no check at all.
**Fix:** Pass a CLI-side guard that takes the poll-cycle lock (non-blocking), or refuse with the "stop the poll timer" warning the CLI already prints for the registry edits.

## Info

### IN-01: Pairing throttle check and record are not atomic; in-memory state resets on restart; a success resets the session counter

**File:** `companion/console_pairing.py:310-329`, `companion/throttle.py`
**Issue:** `locked_for` is checked, then the claim is evaluated, then `record_failure` runs. `ThreadingHTTPServer` is unbounded, so a burst of concurrent requests (admin sessions only) can pass the check before any failure is recorded. The practical impact is negligible: about 39 bits of code space, the global 20 per 15 minutes cap, and admin-only access. A deploy or restart clears all lockouts, and a successful claim resets the per-session counter (the global counter is untouched, which is what actually bounds the attack).
**Fix:** Reserve an attempt up front (`try_acquire(key)` that increments under the lock) and release it on success, so a burst cannot over-run the limit. Optionally persist the global lockout in `fleet.db`.

### IN-02: `reassign_frame` and `reactivate_frame` wipe the stored `state_path` without checking it matches the row's own id

**File:** `server/fleet_ops.py:322-342`, `server/fleet_ops.py:399-408`
**Issue:** The wipe target is derived from `dev["state_path"]`. `add_device` only ever stores `devices/<its own id>`, but a hand-edited or imported row sharing another device's path would wipe that other device's data. Likewise `claim_pairing_code` calls `provision_device_dir` for a freshly generated id without checking that `devices/<id>` does not already exist (for example a retired device's kept directory after an id re-mint, probability about 2^-32). The new device would inherit that data, and the failure-path `rmtree(created_dir)` would delete it.
**Fix:** Assert `state_path == device_dirs.state_path_for(device_id)` before any wipe. In `claim_pairing_code`, fail and retry the id if the directory already exists.

### IN-03: `location_usage_counts` is global, so a user sees how many frames (of any owner) use their location

**File:** `companion/console_locations.py:233`, `server/fleet_db.py:659-665`
**Issue:** Counts are not scoped to the viewer. Only admin-assigned cross-owner use makes this visible, and no identity leaks, but a user's "used by N frames" can include frames they do not own.
**Fix:** For non-admins, count only devices where `owner_user_id = viewer`, or show a boolean "in use".

### IN-04: Id shape regexes use `$` rather than `\Z`

**File:** `companion/console_users.py:33`, `companion/console_locations.py:43`
**Issue:** `^[0-9]{1,9}$` accepts a trailing newline (`int("12\n")` works). A raw newline cannot occur in a request path, so this is not exploitable today. It is inconsistent with the `\Z` discipline used for device and pending ids.
**Fix:** Use `\A[0-9]{1,9}\Z` (or `fullmatch`).

### IN-05: Bidirectional and other format control characters survive in location names

**File:** `companion/console_locations.py:168-170`
**Issue:** `_clean_name` strips only categories `Cc`, `Zl` and `Zp`. Right-to-left override characters (`Cf`, for example U+202E) are kept, and are rendered unescaped-in-meaning in admin tables, audit "Target", and flash text. A low-privilege user can name a location to visually spoof admin-facing text.
**Fix:** Also strip `Cf` (and optionally `Co` and `Cs`).

### IN-06: Fleet page silently hides devices whose `state_path` fails validation

**File:** `companion/console_pairing.py:105-123`
**Issue:** `_device_rows` iterates `device_scope.load_devices`, which drops rows whose `state_path` does not resolve. Such a row disappears from the Fleet page and cannot be retired or reassigned from the UI, although it still owns a MAC and token.
**Fix:** Render rows from `list_devices` directly and show an "unusable state path" badge for those that fail resolution.

### IN-07: `fleet_db.transaction` does not roll back when `COMMIT` fails

**File:** `server/fleet_db.py:352-361`
**Issue:** `conn.execute("COMMIT")` sits outside the `try`. If it raises (for example a disk-full error), the connection is left inside an open transaction, and the next `BEGIN IMMEDIATE` on that connection fails. Per-request connections are closed, so the impact is limited. The long-lived byos and CLI connections are the exposure.
**Fix:** Put `COMMIT` inside the `try`, or `ROLLBACK` if it fails.

### IN-08: `fleet_cli devices add --state-path .` does not record the live MAC, and `devices remove` leaves the removed device's directory behind

**File:** `stub-server/fleet_cli.py:171-204`, `stub-server/fleet_cli.py:341-344`
**Issue:** The live-MAC record is written only on the `auto` path. If the live frame is registered after `devices/` already exists and `fleet.db` later becomes unreadable, byos refuses the live frame (fail-closed, but an outage). `remove_device` deletes the row but never the directory, so the old owner's data (including a calendar secret) stays on disk, unreferenced and unwiped.
**Fix:** Call `record_live_macs` for the "." path too. In `remove`, either wipe through `wipe_device_dir` or print the leftover path.

### IN-09: Small hygiene items

**File:** `server/fleet_db.py:943-946`, `companion/console_locations.py:262-278`, `companion/app.py:1233`
**Issue:**
- `_audit_where` binds `str(len(prefix))` as the `substr` length. It works through SQLite coercion but should be an `int`.
- For a user, `_render` calls `h.page_context()` and discards it. With no frame the call falls back to the live frame's directory and reads its config and health, so this is wasted work and a latent leak path if the result is later used.
- The calendar-URL settings save runs `refresh_calendar_registry` inline while holding the device poll lock for up to about 10 seconds (plus one read timeout), so a plain user can tie up a worker thread and the lock repeatedly.
**Fix:** Pass an `int`; drop the unused `page_context()` call for users; move the calendar sync to the poll cycle, or add a per-user throttle.

---

_Reviewed: 2026-10-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
