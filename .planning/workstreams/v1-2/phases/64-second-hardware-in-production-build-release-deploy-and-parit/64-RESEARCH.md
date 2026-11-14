# Phase 64: Second Hardware in Production - Research

**Researched:** 2026-11-14
**Domain:** Release pipeline, deploy import, hardware-type gate, fleet poll reconcile, companion parity, firmware assumptions of a second panel (Python stdlib server, GitHub Actions, POSIX shell, ESP-IDF 5.3.1 C)
**Confidence:** HIGH for code paths (read in this session on `main` at f88a974); MEDIUM for 7.3 inch timing (unmeasured, owner step)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The second type is exposed by a dedicated switch of its own (a new environment variable, separate from `SKYPANE_SIM_HARDWARE`). The two simulated types stay hidden in production. The profile's `gated` flag is not flipped in code. The switch ships closed (off).
- **D-02:** The switch is turned on in production only after the owner's written confirmation. Never lifted by the agent. The tests that pin the gate off are changed on purpose, with a comment saying why.
- **D-03:** The first signed image of the second type is published AFTER the Phase 57 release. Phase 57 is `human_needed` (bench B1-B9 not done, no release published).
- **D-04:** `.github/workflows/firmware-release.yml` is not edited while Phase 57 is in progress. All planning for that file goes in the last wave, gated on Phase 57's release being published. Everything else (CI build, server, companion, docs, provision.sh) can proceed first. A release carrying only live-frame assets must still import; the live frame's release path and signed image stay unchanged.
- **D-05:** The live-frame guard in `firmware/provision.sh` is typed, like `flash-second.sh`: read the chip MAC, refuse the live frame's MAC or type, and require the MAC typed back at an interactive prompt. Not a port-only check.
- **D-06:** Phase 58 still waits on the physical EE04 unit. Success criteria 5, 7 and 9 (real signed OTA on a second-type frame, measured wake/refresh/pin values, companion walk-through in English and French) are planned as owner-validated steps, never faked. Battery profile stays provisional until Phase 58 measures it.

### Claude's Discretion
Name of the new switch, wave split, plan sizing, test layout, reconcile and `import-dir` implementation details, battery-curve call-site refactor.

### Deferred Ideas (OUT OF SCOPE)
- 90/180 degree turn and photo mode (seed for v1.3).
- Update page install/cancel per device instead of per type (limit shared with several live frames).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HW2-03 | Second board built in production by CI, published by the release pipeline as a signed image with per-type manifest, production deploy imports it, offered/installed/reported over the air on a second-type frame, result in its own registry, live frame's release path unchanged | Sections "Switch", "CI build", "Release workflow (blocked)", "import-dir", "ci.yml download", "Reconcile" |
| HW2-04 | Second type available in production through its own switch, lifted only on owner's written confirmation; every companion view with a picture or battery number follows the frame's profile; owner can pair/administer/manage a second-type frame as admin and invited user (validated on a real frame) | Sections "Switch", "Companion parity" |
| HW2-05 | Second panel's firmware assumptions (wake-stage budget, refresh spacing, battery sense and pins) settled with measured values; documents describe both boards; provisioning guarded against the live frame | Sections "Firmware assumptions", "provision.sh guard", "Documents" |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Code, identifiers, comments, docstrings, docs, commit messages in English. Companion UI stays bilingual (`companion/i18n_fr/`, every user-facing string literal).
- Comments say what and why only. No plan, ticket, decision, review or phase IDs in comments (`scripts/check_comment_history.py check` enforces in CI). Do not write "Phase 64" or "D-01" in code or test comments.
- Function-size gate: max 80 lines over `server`/`stub-server` (`scripts/check_function_size.py`).
- Tests assert behaviour (served HTML/CSS/JS or a browser), never source text or `.planning/` (`companion/test_suite_guards.py` enforces). Existing deploy tests that scan workflow text are the established exception; prefer extracting logic into a script and testing that.
- mypy gate: `server/hardware.py` is in the `[tool.mypy]` file list; new code there must be typed, 3.14 syntax without PEP 695.
- pytest + xdist + cov; non-loopback socket guard; hash-locked `server/requirements*.txt` (no new packages are needed by this phase).
- Draft PRs only; the owner approves deploys. The agent never lifts the switch in production.
- Must not touch any file of Phase 47 / 47.1 (e.g. `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`). Those tests only delete `SKYPANE_SIM_HARDWARE`; a new switch that is unset by default leaves them unchanged. [VERIFIED: stub-server/test_phase47_freeze.py:121-123]

## Summary

The audit holds up when re-read against the code, with three corrections that change the plan. (1) The reconcile gap is narrower than "only the live frame reconciles": the live frame's cycle calls `apply_reconcile_all(root)`, which reconciles the legacy document and every *available* non-legacy type that has a registry file, because the registry and `device_report.json` live in the root state directory and byos writes second-type reports there too. What is missing is independence from the live cycle (it raises `PollBusy` or fails before reconcile) and that the type is only available when the gate is on. (2) `deploy/activate.sh` runs `firmware_cli import-dir` with `runuser` and never sources the env file, so a production switch placed only in `skypane.env` is NOT visible to the import step: a typed release would be skipped or refused at activation even after the owner lifts the switch. activate.sh must read the switch with its strict `_extract_env` and pass it to that one command. (3) `FP_WAKE_STAGE_BLIT_S` (70 s) is not just text: the 7.3 inch driver calls `wait_ready()` three times per wake (init power-on, refresh, power-off in sleep), each up to `BUSY_TIMEOUT_MS` = 60 s, so the compile-time worst case for an OTA wake becomes 285 + 2B seconds and exceeds the 460 s default budget as soon as B > 87 s. Budget, spacing and busy timeouts must be settled together from the unit's measured refresh time, which nobody has timed yet.

Everything except `firmware-release.yml`, the first signed release, the production lift and the three owner validations can be planned and implemented now. Gate change is one function in `server/hardware.py` that every caller already uses (`available_types`), so a single edit exposes the type in console, fleet CLI, poll cycle, byos, registry and Update page.

**Primary recommendation:** Add `SKYPANE_ENABLE_SECOND_HARDWARE` read in `hardware.available_types` (value exactly "1", gated non-simulated profiles only), pass it through activate.sh to `import-dir`, make `import-dir` skip (not fail) unknown or unavailable typed items, add a type-level reconcile to `fleet_cycle`, CI-build the second board in its own job, and park all `firmware-release.yml` work in the last wave.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Production gate for the second type | API / Backend (`server/hardware.py`) | Deploy (env file, activate.sh passthrough) | One registry function feeds byos, poll, companion, CLI |
| CI build and config check of the second board | CI (`firmware.yml`) | Firmware shell checks | Build output is a CI concern; checks are POSIX shell |
| Signed typed release | CI (`firmware-release.yml`, blocked) | `scripts/fw_release_manifest.py` | Signing only in the reviewer-gated environment |
| Typed deploy download and import | CI (`ci.yml`) + Deploy (`activate.sh`) | `server/firmware_cli.py` | Download selects assets; import validates and publishes |
| OTA result reconcile | API / Backend (`server/fleet_cycle.py`, `firmware_registry.py`) | byos (writes `device_report.json`) | Registry and report live in the root state directory |
| Preview shape and battery curve | Companion (server-rendered HTML + PNG) | `server/plane/render` | Companion calls the renderer with the frame's profile |
| Landscape hold warning marks | Render (`server/plane/render/landscape.py`) | `landscape_card` glyph helpers | Poll already passes `battery_low`/`source_fault` into `build_landscape_canvas` |
| Live-frame guard on provisioning | Host tooling (`firmware/provision.sh`) | Shell test | Runs on the developer laptop, before any write |
| Wake budget, refresh spacing | Firmware (Kconfig, `wake_deadline.h`, `sdkconfig.second.defaults`) | Host C tests | Compile-time asserts bound the budget |

## Standard Stack

No new packages. Everything uses what ships: Python 3.14 stdlib + Pillow + requests (`server/requirements.txt`), pytest/xdist/cov, ruff, mypy, POSIX shell, ESP-IDF 5.3.1 container `espressif/idf:v5.3.1`, GitHub Actions with the `gh` CLI already used by `ci.yml`. [VERIFIED: CLAUDE.md, .github/workflows]

### Package Legitimacy Audit
No external package is added or upgraded by this phase. slopcheck not run (nothing to check). Packages removed: none. Flagged: none.

### Installation
None.

## Architecture Patterns

### System Architecture Diagram

```
 tag fw-vX.Y.Z on main
   |
   v
 firmware-release.yml  (BLOCKED until Phase 57 release is out)
   |-- build ee02  --> sign --> verify --> release.json + skypane-<tag>.bin   (unchanged)
   |-- build second --> sign --> verify --> release-<key>.json + skypane-<key>-<tag>.bin
   v
 gh release create (all assets)  --> dispatch ci.yml
                                        |
 ci.yml deploy job (reviewer-gated)     v
   "Download firmware releases": per tag, list assets
      legacy pair present?  typed pairs present?  -> firmware-releases/<tag>/...
      neither -> warning, skip tag
   |
   v  deploy.sh ships dir -> activate.sh
 activate.sh: read SKYPANE_ENABLE_SECOND_HARDWARE from skypane.env (strict regex),
   pass to:  firmware_cli import-dir  (as skypane user)
      per tag dir: legacy pair -> registry.json
                   each release-<key>.json:
                      key invalid shape       -> item error (fails if new)
                      key unknown/unavailable -> "skipped" notice, exit stays 0
                      key available           -> publish_release -> registry.<key>.json
 swap current -> services restart (env file has the switch -> byos/companion/poll see it)

 second-type frame --poll--> byos (root state dir): device_report.json
                                        ^
 skypane-poll.timer -> fleet_cycle.run_fleet(root)
     (new) reconcile non-legacy available types with a registry file, once per run
     live cycle: poll_cycle.run_once -> apply_reconcile_all (unchanged)
```

### Recommended file touch list

```
server/hardware.py                  new switch + available_types (typed, mypy list)
server/firmware_cli.py              _import_tag_dir/_typed_key_error skip semantics
server/fleet_cycle.py               type-level reconcile once per run
server/firmware_registry.py         (optional) helper apply_reconcile_other_types
server/plane/render/landscape.py    marks on landscape hold screens
companion/theme_preview.py, preview_images.py, settings/{theme,calendar,layout_picker}.py
companion/{console_pairing,ui_shell,sign_in}.py   battery curve per frame
scripts/fw_release_manifest.py      resolve profile independent of the production switch
scripts/fw_release_assets.py (new)  pure asset selection for ci.yml download step
deploy/activate.sh                  pass the switch to import-dir
deploy/skypane.env.example          commented switch line (ships closed)
.github/workflows/firmware.yml      build-second job
.github/workflows/ci.yml            typed download
.github/workflows/firmware-release.yml   LAST WAVE, BLOCKED ON PHASE 57
firmware/tests/check_production_config.sh   optional board argument to `built`
firmware/provision.sh + firmware/tests/check_provision_guard.sh (new)
firmware/main/wake_deadline.h, Kconfig help, sdkconfig.second.defaults, tests/test_wake_deadline.c
docs: firmware/SIGNING.md, firmware/VENDOR.md, deploy/README.md, README.md, hardware/SECOND-HARDWARE*.md
```

### Pattern 1: dedicated switch (code path, gap 4)

`server/hardware.py:282-299` is the single gate. All callers go through `available_types()` / `get_profile()`: `fleet_ops.py:182`, `companion/console_pairing.py:233`, `companion/pages/update_page.py:233`, `stub-server/fleet_cli.py:391`, `stub-server/byos_server.py:1011,1244`, `server/firmware_registry.py:121,1056,1072`, `server/firmware_cli.py:195,321,403`, `server/fleet_cycle.py:_renders_here/_cycle_profile_kwargs`, `companion/device_scope.profile_for`. [VERIFIED: grep]

```python
# Proposed shape (typed; the name is the planner's call, this one is suggested)
SECOND_ENV_VAR = "SKYPANE_ENABLE_SECOND_HARDWARE"

def _flag(environ: Mapping[str, str] | None, name: str) -> bool:
    env = os.environ if environ is None else environ
    return env.get(name) == "1"

def available_types(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    sim = _flag(environ, SIM_ENV_VAR)
    second = _flag(environ, SECOND_ENV_VAR)
    return tuple(
        k for k, p in REGISTRY.items()
        if sim or not (p.simulated or p.gated) or (second and p.gated and not p.simulated))
```

Keep `gated=True` on `_EVALUATION` (D-01). `SIM=1` keeps exposing everything (bench runbook, dozens of tests rely on it). Update the module docstring (it says no env template sets the gate; the new variable also ships unset). Do not add the variable to `deploy/skypane.env.example` as an assignment, only as a commented line, because `server/test_hardware.py::test_production_config_never_enables_sim_types` parses assignments from that file.

### Tests that pin the gate off (what to change, what stays)

Closed behaviour is unchanged, so most pins stay valid. [VERIFIED: server/test_hardware.py]
- `test_available_types_without_gate_is_legacy_only` (20), `test_other_gate_values_leave_sim_types_out` (32-36), `test_evaluation_type_is_hidden_without_the_gate` (260-268): still correct with the switch closed. Add siblings: only the new switch -> `(LEGACY_KEY, EVALUATION_KEY)` and no `sim-*` key; values `"0"`, `"true"`, `""`, `"11"` leave it closed; SIM and second switch together = all four.
- `test_production_config_never_enables_sim_types` (127-137): extend, on purpose and with a comment saying why, to also assert the new variable is not an assignment in `deploy/skypane.env.example` and in no `deploy/*.service`, and that the type stays out of `available_types(env)`. This is the "ships closed" pin; it is the one test the owner changes if they ever decide to commit the switch to the template.
- Tests that `delenv(SIM_ENV_VAR)` to prove refusal (`server/test_firmware_cli.py:717`, `server/test_firmware_registry.py:1308,1495,1611`, `server/test_fleet_db.py:285`, `stub-server/test_evaluation_unit_image.py::test_evaluation_unit_is_refused_when_the_gate_is_off`, `companion/test_battery_profile.py:47`) keep working as long as they also do not have the new variable in the process environment; add `monkeypatch.delenv(hardware.SECOND_ENV_VAR, raising=False)` to a shared autouse fixture only where a CI machine could set it (it will not).
- `server/test_firmware_cli.py::test_import_dir_bad_type_key_is_an_item_error_and_others_still_import` and `test_import_dir_simulated_type_is_refused_when_simulation_is_off` pin rc 1 for unknown/unavailable typed keys; they must be rewritten for the new skip behaviour (see import-dir).
- Lift semantics: lifting is one line in `/opt/skypane/skypane.env` on the VPS plus restart, no repo change. [ASSUMED: owner performs it by hand as for other env settings; confirm in the lift runbook]

### Pattern 2: CI build of the second board (gap 3, criterion 1)

`firmware/build.sh` already supports `SKYPANE_BOARD=second` (prod -> `build-second`, dev -> `build-second-dev`), regenerates sdkconfig each build and works on the `espressif/idf:v5.3.1` image. `.github/workflows/firmware.yml` job `build` (job name "Build EE02 firmware image", steps 56-82) is the model. [VERIFIED: firmware/build.sh:53-131, firmware.yml]

- Add a separate job `build-second` (do not rename or restructure the existing job: its name can be a required status check). Steps: checkout (fetch-depth 0), `SKYPANE_BOARD=second ./firmware/build.sh`, `test -f firmware/build-second/skypane.bin`, `sh firmware/tests/check_production_config.sh built firmware/build-second second`, size gate `<= 0x250000*90/100` (same partition table, `FirmwareTarget.max_app_bytes` default is the same 0x250000, so reuse the literal and add a pytest that the profile bound equals the `ota_0` size in `partitions.csv`). `check_hw_type_key.sh` and `static` mode are board-independent; leave them in the existing job.
- Extend `check_production_config.sh built <dir>` with an optional third argument `ee02|second` (omitted = today's behaviour exactly, so the untouched release workflow keeps passing). For `second` assert in the built sdkconfig: `CONFIG_FP_PANEL_7IN3E=y`, `CONFIG_FP_PANEL_BUFFER_BYTES=192000`, `CONFIG_SKYPANE_HW_TYPE="seeed-ee04-7in3-spectra6"` (derive from `server.hardware.EVALUATION_KEY` with the same `python3 -I` call as `check_hw_type_key.sh`, never hard-code twice), `CONFIG_FP_HW_REV="proto-ee04"`, non-empty key. For `ee02` assert `# CONFIG_FP_PANEL_7IN3E is not set` and the legacy key. [ASSUMED: exact Kconfig line forms in a resolved sdkconfig (`# CONFIG_X is not set`); the first CI run proves them, so run the new job once on a draft PR before relying on it]
- Pitfall: the image descriptor cannot tell the two boards apart. Both are ESP32-S3 and project name `skypane`; `validate_for_target` checks chip, project name, version, signature, size only. The hardware key lives only in sdkconfig. So the per-board build directory plus the `built ... second` check are what keep a live-frame image from being published as the second type (and the reverse). Release workflow must derive each manifest from the matching build directory only. [VERIFIED: server/firmware_image.py:173-266, server/hardware.py FirmwareTarget]
- Host-test thinness: `HOST_TEST_PROFILES: second` exists in `test_fault_screen.c`, `test_panel_geometry.c`, `test_updating_screen.c`. Add the marker to `test_wake_deadline.c` and `test_panel_guard.c` (the runner compiles the second run with `-DCONFIG_FP_PANEL_7IN3E=1 -DCONFIG_FP_PANEL_BUFFER_BYTES=192000`). [VERIFIED: firmware/tests/run_host_tests.sh]
- `firmware/tests/check_panel_diff.sh` pins diffs to `main/epd13in3e.c` and `main/panel.c`; do not edit those two files in this phase. `main/epd7in3e.c` is not pinned.

### Pattern 3: typed import and `import-dir` (gap/partial, criterion 3)

Current behaviour: `_import_tag_dir` (`server/firmware_cli.py:~236-265`) calls `_typed_key_error(key)` which returns an error for invalid shape, `not is_known or key not in available_types()`, and the legacy key; for an unavailable type `known=False` makes `is_new=True`, so the item fails the whole command (rc 1) and activation aborts. [VERIFIED: server/firmware_cli.py:187-263, tests at server/test_firmware_cli.py:701-727]

Recommended behaviour:
- Shape-invalid key (not `[a-z0-9-]{1,64}`) or key == legacy: remain item errors.
- Valid-shape key that is unknown (a newer release meeting an older importer, e.g. after a rollback) or known-but-unavailable (switch off): print a `skipped <tag> [<key>]: hardware type not available here` line to stderr, do not count as a failure, never touch a path built from the key beyond the shape check. Re-run is idempotent and the next deploy after the lift imports it.
- Available type: unchanged (all errors fail only if the tag is new for that type).
- A release with only legacy assets, or only typed assets, keeps working (`has_legacy_files or not typed` logic already handles it).
- Mismatch with `release-<key>.json` `hardware_type` and symlink refusals stay failures for available types.
- `activate.sh` must forward the switch: it already parses `skypane.env` with `_extract_env` (strict anchored regex, never sourced) at lines 111-123 and runs the import as `runuser -u skypane -- python3 -m server.firmware_cli ...` at ~line 227 with a clean environment. Parse `SKYPANE_ENABLE_SECOND_HARDWARE` (accept only `1`/empty), and run `runuser -u skypane -- env SKYPANE_ENABLE_SECOND_HARDWARE=1 python3 ...` only when it is `1`. `deploy/tests/test_activate.py` uses a stand-in `server/firmware_cli.py` that logs its invocation, so the test asserts the forwarded environment, not real publishing. [VERIFIED: deploy/activate.sh:111-123,220-230; deploy/tests/test_activate.py:20-45]
- `scripts/fw_release_manifest.py` resolves the profile with `hardware.get_profile(hardware_type)` and thus `os.environ` (`size_bound`, `check_image`). The release tool should accept any registered non-simulated type regardless of the production switch (CI has no switch). Suggested: call `hardware.get_profile(key, {**os.environ, hardware.SECOND_ENV_VAR: "1"})`. Existing `deploy/tests/test_release_manifest.py::test_unknown_or_unavailable_hardware_type_exits_2` (SIM clone must exit 2, `no-such-type` exit 2) stays valid; add a test that the evaluation key now builds a manifest and that the sim keys are still refused.

### Pattern 4: typed download in `ci.yml` (gap 2)

`ci.yml` "Download firmware releases" step (lines ~462-490) requires `skypane-<tag>.bin` and `release.json` or skips the tag with a warning. [VERIFIED: ci.yml:462-490] Replace the inline selection by a small stdlib script `scripts/fw_release_assets.py` that takes a tag and the asset-name list on stdin and prints the names to download:
- legacy pair `skypane-<tag>.bin` + `release.json` when both are present;
- for each `release-<key>.json` with key matching `^[a-z0-9-]{1,64}$` and a present `skypane-<key>-<tag>.bin`, that pair;
- nothing (and a warning) when neither pair is complete.
Reasons: asset names come from a remote release and flow into shell (`gh release download --pattern`); a pure function with a regex allow-list is unit-testable and keeps injection surface closed. Keep the existing conventions of the step (`env: GH_TOKEN`, no `${{ }}` in `run:`; `deploy/tests/test_ci_secrets.py` scans every `run:` block). `ci.yml` is not blocked by D-04, but it is deployed on merge, so the change must be behaviour-neutral for existing live-only releases (test with the current asset-name lists).

### Pattern 5: reconcile of non-live types (partial, criterion 5)

Facts: `fleet_cycle.run_device` passes `reconcile_firmware=device.is_live` (399). Non-live devices poll with their own per-device `state_dir`, where no firmware registry exists, so reconcile for them is meaningless. The live device's `state_dir` IS the root, and `poll_cycle.run_once` -> `_reconcile_firmware(ctx.state_dir, now)` -> `firmware_registry.apply_reconcile_all` reconciles the legacy document and every available non-legacy type that has a registry file (`firmware_registry.py:1049-1062`). byos records every device's OTA report into the root `device_report.json` (`byos_server.py:1731-1736` passes `self.args.state_dir`). [VERIFIED]

Remaining weaknesses to close:
1. Result recording depends on the live cycle not failing earlier: `PollBusy` (lock timeout) and any exception in `load_cycle_context` skip reconcile.
2. `apply_reconcile_all` iterates `hardware.available_types()` at call time, so it works only with the switch on and the registry file present.

Recommended: in `fleet_cycle.run_fleet`, before the device loops, call a new small function (in `firmware_registry`: `apply_reconcile_other_types(state_root, now)` or the same loop inline) that runs `apply_reconcile(root, now, type)` for each available non-legacy type whose `registry_path` exists, wrapped like `_reconcile_firmware` (broad except, log type name only, never break polling). It must not touch the legacy document, so the live cycle's behaviour, golden hashes and the freeze test are unaffected; running both is idempotent because `apply_reconcile` writes only when `reconciled_seq` moves. Tests: runner stub that raises for the live device while a second-type report event sits in `device_report.json` -> second registry's `last_outcome` set; failing update keeps `schedule` attempts and no `installed_at`; gate off -> nothing touched; legacy registry bytes identical before and after. Existing patterns: `server/test_firmware_reconcile.py:206`, `server/test_fleet_cycle.py:572-587`. Keep `run_fleet` within the 80-line function gate (extract the helper).

### Pattern 6: companion parity (gap 5/6 and battery partial, criterion 6)

Preview call sites (all verified):
- `companion/theme_preview.py`: `FRAME_PREVIEW_CANVAS_SIZE = (1200, 1600)` (306), `FRAME_PREVIEW_PIXEL_SIZES` (307-310), `frame_preview_png_bytes` (320-345: `render.build_canvas(...)` without `profile`, `.reduce(factor)`), `frame_preview_signature`/`frame_cache_path`/`cached_frame_preview_bytes`/`frame_preview_src` (no profile in cache key), `preview_png_bytes` + `THEME_PREVIEW_CROP_BOX = (0, 390, 1200, 840)`, `THEME_PREVIEW_SIZE = (320, 120)` (portrait crop of the illustration band).
- `companion/preview_images.py`: `_serve_theme_preview_image` and `_serve_frame_preview_image` have `device` in hand but pass no profile.
- Consumers of the size constant for `<img width/height>`: `companion/settings/theme.py:178,297,348`, `settings/calendar.py:489`, `settings/layout_picker.py:80,128`.
- `render.build_canvas(..., profile=...)` already renders landscape natively at the profile size (`server/plane/render/layout.py:473-520`), so previews only need the profile threaded through.

Plan: add `frame_preview_pixel_size(profile, size)` (legacy returns exactly today's values), pass `device_scope.profile_for(device)` from the preview routes and settings pages, include `profile.key` (or width x height) in the cache signature and filename only for non-legacy profiles so legacy cache files keep their names, and pick a landscape crop box for the small chip preview by looking at the 800x480 canvas (the portrait box excludes the caption; the landscape crop is a design choice that needs a visual check, owner-validated in the walk-through). Tests assert PNG dimensions per profile and that legacy bytes are unchanged for the legacy profile.
- `device_scope.profile_for` (companion/device_scope.py:236) falls back to the legacy profile when a type is gated off. With the switch off no second-type row is manageable anyway; with it on it resolves. No change needed, but keep `test_profile_for_never_raises_and_falls_back` (companion/test_battery_profile.py:44-50).

Battery curve call sites using the legacy curve: `companion/console_pairing.py:83` (`_percent(millivolts)`, called at 117 for a device row and 142 for a pending row that has `row["hardware_type"]`), `companion/ui_shell.py:415` (`_switcher_status_row`, has `device`), `companion/sign_in.py:370-371` (has `profile = hardware.REGISTRY.get(device.hardware_type)` two lines above). Use `battery.percent(mv, curve)` with `page_context.device_curve(device)` or, for display-only rows, the REGISTRY profile of the stored type (like `_hardware_label` already does, independent of the gate). `home_page.py`, `health_page.py`, `battery_chart.py` already use `page_context.device_curve`. [VERIFIED: grep]

Landscape hold marks (gap 6): `server/plane/render/landscape.py:33-43` builds holds via `landscape_hold.build_*_canvas(size[, ...])` and drops `source_fault`/`battery_low`, while `landscape_card.draw_battery_low(canvas, size, ink)` and `draw_source_fault(canvas, size, geom, ink, weight)` exist (landscape_card.py:291-330) and `giant/compose_landscape.py:82-92` shows the geom shim (`SimpleNamespace(margin=..., overlay_right=...)`). `landscape_hold.py` states it must not import `layout.py`, and `landscape_card` imports `layout`, so draw the marks in `landscape.py` after the hold builder returns (empty, quiet_hours, display_off; NEVER battery_empty, whose bytes must stay constant for the whole parked episode). Use the ink the hold used (`style.EMPTY_INK` for empty, `style.DIMMED_INK` for dimmed). The portrait reference is `hold_screens._build_hold_canvas` (hold_screens.py:249-254). Tests (`server/test_render_landscape_hold.py` pattern): marks present in the bottom-left region when flags are on, absent when off, `battery_empty` byte-identical with flags on and off, marks do not overlap the glyph/text block (use `common.assert_within_canvas`). The default giant layout is unaffected (`layout.build_canvas` returns giant holds first). Legacy golden hashes (`server/test_golden_render.py`, `test_golden_giant_render.py`) are portrait and stay untouched.

### Pattern 7: provision.sh typed guard (gap 7, D-05)

Verified: `firmware/provision.sh` has no live-frame protection. It writes the secret partition (new random enrolment secret) of whatever device sits on the port, which on the live frame would silently break its enrolment. MAC is read at step 6 (`esptool ... read-mac`, ~line 357) and only in non-dry-run mode; dry-run takes a MAC argument and touches no hardware. [VERIFIED: provision.sh:4-58,329-420]

Model `firmware/flash-second.sh` exactly: optional `SKYPANE_LIVE_FRAME_PORT` and `SKYPANE_LIVE_FRAME_MAC` (case-insensitive MAC compare); refuse with exit 3 before any esptool call when the port equals the live port; after reading and printing the MAC, refuse with exit 3 if it equals the live MAC; then require the MAC typed back (`printf 'Type the MAC shown above to confirm: '; read -r CONFIRM`, lowercase compare), exit 3 on mismatch. Guard placement: port check right after argument validation (before the Wi-Fi password prompt, so a refusal costs nothing); MAC check and typed prompt right after the MAC validity check (step 6) and before the private work dir, Docker and any write. In `--dry-run <mac>` mode apply only the live-MAC refusal (no prompt, no hardware). The chip type cannot be read from the silicon (both boards are ESP32-S3), so "refuse the live frame's MAC or type" is realised through the declared live MAC and port, as `flash-second.sh` does; if the owner wants a stricter "type" meaning, that is an open question below.
Test: a new POSIX test `firmware/tests/check_provision_guard.sh` with stub `esptool`, `docker` (exit 99 to prove nothing ran) and `python3` untouched on a private PATH, `SKYPANE_WIFI_PASS=` set to skip the tty prompt, wired into `firmware/tests/run_host_tests.sh` next to `check_bench_floor_option.sh`. Cases: live port refused (exit 3, esptool never invoked), live MAC refused, wrong typed MAC refused, empty stdin refused, correct MAC proceeds to the Docker stub, dry-run with live MAC refused, dry-run with other MAC passes. Shell is outside the Python function-size gate.

### Pattern 8: firmware assumptions (risks, criterion 7)

- `wake_deadline.h:24` `FP_WAKE_STAGE_BLIT_S 70u` comment cites `epd13in3e.c`. `epd7in3e.c` calls `wait_ready()` at init (310), after refresh (328) and in sleep power-off (340), each bounded by `BUSY_TIMEOUT_MS 60000` (149). `wake_guard.c:26-37` static-asserts `CONFIG_SKYPANE_WAKE_BUDGET_S` (default 460, range 180..900) above `FP_WAKE_WORST_CASE_S(guard)` and `FP_WAKE_OTA_WORST_CASE_S(guard)`; default guard wait is 90. [VERIFIED]
- Arithmetic (B = blit stage seconds, guard 90): normal worst = 180 + B; OTA worst = 285 + 2B. With B = 70: 250 and 425 (both under 460). With B = 3 x 60 + SPI margin (about 190): 370 and 665, so the 7.3 inch profile needs a budget above 665 (for example 700, inside the 900 cap) unless the driver's busy timeout is lowered to a measured value (for instance 3 x 30 + margin).
- Do it without changing the live image: make `FP_WAKE_STAGE_BLIT_S` conditional in the header (`#if CONFIG_FP_PANEL_7IN3E`) so the ee02 resolved value is still 70 and no new Kconfig symbol is added (a new default-valued symbol would alter the ee02 resolved sdkconfig, which the legacy-identity proof compares). Set `CONFIG_SKYPANE_WAKE_BUDGET_S` in `sdkconfig.second.defaults` (existing symbol). Use the `HOST_TEST_PROFILES: second` run of `test_wake_deadline.c` to pin the second-profile worst cases against the second profile's budget. [ASSUMED: header can read `CONFIG_FP_PANEL_7IN3E` since `wake_deadline.c` is compiled in the host test with the profile macros; verify with the second host run]
- `CONFIG_FP_MIN_REFRESH_SPACING_S` (Kconfig.projbuild:205, default 60, help cites the GDEP133C02 13.3 inch panel). `wake_guard.c:39` requires it <= `FP_WAKE_STAGE_OTA_S` (90). Rewrite the help text to name both panels (help text does not change binaries) and set the second profile's value from the Phase 58 measurement; if it stays 60, say so with the panel's own datasheet reference instead of the 13.3 inch one. The 7.3 inch refresh time has not been timed (`hardware/SECOND-HARDWARE-VALIDATION.md` states so). [VERIFIED]
- Pins: `sdkconfig.second.defaults` says KEY0/1/2, battery ADC (1), ADC enable (6), LED (21, active low) are copied from the EE02 and unmeasured. Unit is on the bench (MAC 84:c7:bb:70:b2:7c, validation record 2026-11-14) but battery sense, LED and keys were not measured. Owner step.
- `panel_guard.h:32` still says "960 KB": cosmetic fix.
- `partitions.csv` is shared (8 MB layout, `ota_0/ota_1` 0x250000); the unit ran a 1118208-byte app at 0x20000, which is consistent. Flash size of the EE04 module is not recorded: owner step (`esptool flash_id`).
- Battery profile: `_EVALUATION` copies legacy numbers with provenance "copied ... not a measurement", `provisional`. After Phase 58 measures, update `server/hardware.py` values and provenance to `final` only with "measure" in the source (`_battery_problems` enforces it) and update `hardware.PLANNED_BATTERY_SLOTS`/tests that assert provisional.

### Anti-Patterns to Avoid
- Flipping `gated` or reusing `SKYPANE_SIM_HARDWARE` in production (violates D-01; would expose `sim-*` types).
- Sourcing `skypane.env` in activate.sh (the script deliberately parses with a fixed-key regex).
- Editing `firmware-release.yml` before the Phase 57 release is published (D-04). Do not even "prepare" a branch edit that gets merged.
- Making the release tool depend on the production switch.
- Adding new Kconfig symbols that change the ee02 resolved sdkconfig, or editing `panel.c` / `epd13in3e.c` (panel-diff gate).
- Writing phase or decision IDs in comments or test names.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Image validation and signing policy | custom parser in CI | `scripts/fw_release_manifest.py --check-only`, `server.firmware_image.validate_for_target` | Same code the registry's publish gate uses |
| Release manifest | hand-written JSON | `fw_release_manifest.py --hardware-type <key> --out release-<key>.json` | Already type-aware, derives build number, sha, notes |
| Typed asset names / import | new import tool | existing `firmware_cli import-dir` pair layout (`release-<key>.json` + `skypane-<key>-<tag>.bin`) | Layout and per-type registry exist and are tested |
| Per-type registry reconcile | new reconcile logic | `firmware_registry.apply_reconcile(state_dir, now, type)` | Idempotent, locked, already tested |
| Battery percentage | local math | `battery.percent(mv, curve)` + `page_context.device_curve` | One model for frame and companion |
| Landscape marks | new glyph drawing | `landscape_card.draw_battery_low` / `draw_source_fault` | Same geometry as the card |
| Live-frame guard | new design | `flash-second.sh` guard text and exit codes | Consistent operator experience |
| Asset-name handling in CI shell | inline grep/sed over remote names | allow-list regex in a tested Python function | Remote strings reach shell commands |

## Runtime State Inventory

Not a rename/refactor phase; one migration-like aspect only.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `/opt/skypane/state/firmware/registry.seeed-ee04-7in3-spectra6.json` will not exist until the first typed import after the lift; no existing rows carry the type in production [ASSUMED: owner has no second-type row in production fleet.db] | None now; first import creates it |
| Live service config | `skypane.env` on the VPS (not in git): the switch is added there by the owner | Owner step, restart byos/companion (poll reads it per run) |
| OS-registered state | systemd units use `EnvironmentFile=/opt/skypane/skypane.env` (byos, companion, poll) | None; no unit file change |
| Secrets/env vars | `FW_SIGNING_KEY` (environment `firmware-signing`) already signs; the same key signs both boards (option S) | None |
| Build artifacts | `firmware/build-second*` ignored by git | None |

## Common Pitfalls

### Pitfall 1: switch on in the env file but invisible to the import
**What goes wrong:** typed second release is skipped at activation although the owner lifted the switch.
**Why:** activate.sh runs `firmware_cli` under `runuser` with a clean env and never sources the env file.
**Avoid:** forward the parsed value (see Pattern 3); test via the fake `firmware_cli` in `deploy/tests/test_activate.py`.
**Warning signs:** `skipped ... not available here` in the deploy log with the switch set.

### Pitfall 2: unavailable typed release aborting every deploy
**What goes wrong:** `import-dir` returns 1 for any new tag carrying a typed pair whose type is not available, blocking all code deploys (current behaviour).
**Avoid:** skip semantics for valid-shape unknown/unavailable keys; keep failures for available types.

### Pitfall 3: wrong image published as the second type
**What goes wrong:** descriptor checks pass for any `skypane` ESP32-S3 image.
**Avoid:** separate build dirs per board, `check_production_config.sh built <dir> second` before signing, manifest generated from the matching dir; distinct file names.

### Pitfall 4: wake budget static assert breaks the build, or silently allows a too-small budget
**Avoid:** compute both worst cases for the second profile in the host test; budget >= worst case + margin; do not shrink `BUSY_TIMEOUT_MS` without a measurement.

### Pitfall 5: preview cache collisions and size constants
**What goes wrong:** a landscape frame served a cached portrait PNG, or `<img>` dimensions from the portrait constants.
**Avoid:** profile in cache key for non-legacy only; dimensions from a function of the profile; keep legacy filenames identical.

### Pitfall 6: reconcile running only when the live cycle succeeds
See Pattern 5.

### Pitfall 7: signing key handled twice
In the (blocked) release workflow the signing step writes the key to a temp file, signs, and a later `if: always()` step shreds it. Sign both images inside the same step and key lifetime; keep `--network none` and the digest-pinned image; never interpolate secrets into `run:`.

### Pitfall 8: dirty-tree refusal on the second build
`build.sh` release mode requires a clean tree at the tagged HEAD. `firmware/build*/` is git-ignored (verified in `.gitignore`), so a second build after the first is fine; generated files must stay inside ignored build dirs.

## Code Examples

### Typed asset selection (pure, testable)
```python
# scripts/fw_release_assets.py (sketch; stdlib only)
import re
_KEY = re.compile(r"\A[a-z0-9-]{1,64}\Z")
_MANIFEST = re.compile(r"\Arelease-(.+)\.json\Z")

def wanted_assets(tag: str, names: list[str]) -> list[str]:
    have = set(names)
    out: list[str] = []
    if f"skypane-{tag}.bin" in have and "release.json" in have:
        out += [f"skypane-{tag}.bin", "release.json"]
    for name in sorted(have):
        m = _MANIFEST.match(name)
        if m and _KEY.match(m.group(1)) and f"skypane-{m.group(1)}-{tag}.bin" in have:
            out += [name, f"skypane-{m.group(1)}-{tag}.bin"]
    return out
```

### Guard order in provision.sh (shape, mirrors flash-second.sh)
```sh
if [ -n "${SKYPANE_LIVE_FRAME_PORT:-}" ] && [ "${PORT}" = "${SKYPANE_LIVE_FRAME_PORT}" ]; then
    echo "REFUSED: ${PORT} is declared as the live frame's port" >&2; exit 3
fi
# ... after the MAC is read and validated ...
printf 'Type the MAC shown above to confirm: '
CONFIRM=""; read -r CONFIRM || true
CONFIRM=$(printf '%s' "${CONFIRM}" | tr 'A-F' 'a-f')
[ "${CONFIRM}" = "${MAC}" ] || { echo "REFUSED: confirmation did not match. Nothing was written." >&2; exit 3; }
```

### Release workflow additions (LAST WAVE, blocked on the Phase 57 release; sketch only)
Same job, appended after the live-frame steps and before "Publish": build with `SKYPANE_BOARD=second SKYPANE_RELEASE_TAG="$GITHUB_REF_NAME" ./firmware/build.sh`; `check_production_config.sh built firmware/build-second second`; sign `build-second/skypane.bin` inside the existing key-lifetime step by a second `espsecure.py sign_data` invocation (the first invocation's text unchanged); verify with `verify_signature`; `fw_release_manifest.py --check-only` and manifest generation with `--hardware-type seeed-ee04-7in3-spectra6 --image firmware/build-second/skypane-signed.bin --out release-seeed-ee04-7in3-spectra6.json`; stage `skypane-seeed-ee04-7in3-spectra6-${GITHUB_REF_NAME}.bin`; add both to the `gh release create` argument list; keep the final dispatch of `ci.yml` last so the deploy never races the typed assets. Single-job (atomic) is recommended over a second job because the dispatch step sits at the end of the one job. Trade-off to state to the owner: a second-board build failure then blocks the live frame's release; mitigated because CI builds the second board on every PR that touches `firmware/**`.

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| One switch for sim and gated types | Separate production switch for the gated real type | Production can expose the EE04 without sim types |
| Live-only release assets | `release-<key>.json` + `skypane-<key>-<tag>.bin` beside the legacy pair (already read by `firmware_cli`) | Nothing produces them yet |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Resolved sdkconfig line forms (`# CONFIG_FP_PANEL_7IN3E is not set`, `CONFIG_FP_PANEL_BUFFER_BYTES=192000`) as the built-mode check expects | CI build | New CI job red on first run; fix the grep strings |
| A2 | The lift is a hand edit of `/opt/skypane/skypane.env` plus service restart | Switch | Runbook wording differs |
| A3 | No second-type row exists in production fleet.db today | Runtime State | Existing row would start being served the moment the switch lifts |
| A4 | `wake_deadline.h` can see `CONFIG_FP_PANEL_7IN3E` in firmware and host builds | Firmware assumptions | Needs an include of `sdkconfig.h` or a different conditional |
| A5 | 7.3 inch refresh time is in the tens of seconds; no number exists in the repo | Firmware assumptions | Budget/spacing sized wrong; must be measured |
| A6 | Switch name `SKYPANE_ENABLE_SECOND_HARDWARE` (free choice under discretion) | Switch | Rename only |

## Open Questions

1. **"refuse the live frame's MAC or type" in provision.sh**
   - Known: both boards are ESP32-S3, the chip cannot tell its type; flash-second.sh uses declared port/MAC.
   - Unclear: whether the owner wants refusal also when the MAC is registered as a live-type row on the server (needs network), or only declared env values.
   - Recommendation: declared `SKYPANE_LIVE_FRAME_PORT`/`SKYPANE_LIVE_FRAME_MAC` plus mandatory typed MAC, identical to flash-second.sh; state the limit in the docs.
2. **Atomic release job vs second job** (Pattern release). Recommendation: one job; owner to confirm that a second-board build failure may block a live release.
3. **Does provisioning the live frame itself ever need to be possible again?** With the guard it is refused when the env declares it; document that unsetting the variable is the deliberate override.
4. **Lifting order:** the owner needs a deploy (workflow_dispatch of ci.yml) after the lift to import typed releases already published; document it.
5. **Phase 58 bench state:** STATE.md says 58 waits for the unit, but `hardware/SECOND-HARDWARE-VALIDATION.md` records a unit flashed, enrolled and paired on 2026-11-14 without refresh timing, battery, LED or key checks. Criteria 5, 7, 9 remain owner steps either way.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| docker | local firmware build, provision.sh | yes (`/usr/bin/docker`) | not probed | CI builds |
| shellcheck | `ci.yml` shellchecks deploy scripts | no on this machine | - | CI runs it; keep scripts POSIX/bash-clean |
| Physical EE04 unit + signed OTA path + VPS | criteria 5, 7, 9 | owner only | - | none (never faked) |
| Phase 57 published release | firmware-release.yml edit, first typed release | no | - | wave blocked |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + xdist + cov (Python); POSIX shell checks; C host tests via `firmware/tests/run_host_tests.sh`; Playwright for companion browser tests |
| Config file | `pyproject.toml` (`testpaths = server stub-server companion test-support deploy hardware`) |
| Quick run command | `server/.venv/bin/python3 -m pytest server/test_hardware.py server/test_firmware_cli.py server/test_fleet_cycle.py server/test_render_landscape_hold.py deploy/tests -x -q` |
| Full suite command | `./scripts/run-all-tests.sh` (add `sh firmware/tests/run_host_tests.sh` and `python3 scripts/check_function_size.py`, `python3 scripts/check_comment_history.py check`, ruff, mypy) |

### Phase Requirements -> Test Map
| Criterion | Behaviour | Test Type | Automated Command | Exists? |
|-----------|-----------|-----------|-------------------|---------|
| 1 | CI builds second board, built-mode check + size gate | CI job; shell check unit-tested with fake sdkconfig dirs | `sh firmware/tests/check_production_config.sh built <fixture-dir> second` (fixture-based test in `deploy/tests` or `firmware/tests`); real build runs in `firmware.yml` | Wave 0: fixtures + test; CI proves build |
| 2 | One tag -> typed signed assets; live path unchanged; legacy-only release still imports | `fw_release_manifest` tests with the evaluation key; `import-dir` tests for legacy-only and typed-only dirs; workflow itself only provable by a real tag | `pytest deploy/tests/test_release_manifest.py server/test_firmware_cli.py` | partly; workflow part is last wave and owner-observed |
| 3 | Deploy fetches/imports typed assets; unknown/unavailable type does not fail activation | pure asset-selection test; import-dir skip test; activate.sh passthrough test | `pytest deploy/tests/test_activate.py server/test_firmware_cli.py deploy/tests/test_release_assets.py` | Wave 0 for the new script test |
| 4 | Own switch; sim hidden; closed by default; pins changed on purpose | unit | `pytest server/test_hardware.py -q` | extend |
| 5 | Real signed OTA over https on a second-type frame, result recorded in its registry by the production poll; failed update keeps previous firmware | automated part: reconcile with a failing live cycle, failed-update stays previous (registry attempts, no `installed_at`); real signed OTA is OWNER-ONLY | `pytest server/test_firmware_reconcile.py server/test_fleet_cycle.py stub-server/test_ota_offer.py` | extend; device part owner |
| 6 | Previews and battery curve follow the profile; hold marks present | PNG size/cache tests; battery percent per profile in console/ui_shell/sign_in; render pixel tests; browser smoke of the Look page for a second-type frame | `pytest companion/test_theme_preview*.py companion/test_battery_profile.py server/test_render_landscape_hold.py` | extend; panel look owner |
| 7 | Wake budget, spacing, pins with measured values | automated: second-profile static asserts and host tests; measured values OWNER-ONLY | `sh firmware/tests/run_host_tests.sh` | add `HOST_TEST_PROFILES: second` |
| 8 | Docs for both boards; provision refuses live frame; no Phase 47/47.1 file touched | shell guard test; `deploy/tests/test_docs.py` style checks for doc claims; `git diff --stat` against the frozen file list | `sh firmware/tests/check_provision_guard.sh` | Wave 0 |
| 9 | Walk-through on a real frame, admin and invited user, English and French | OWNER-ONLY | n/a | n/a |

Must-not-break checks (every wave): `pytest stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py`; legacy production image identity at section level using the Phase 58 procedure (ee02 build before/after: resolved sdkconfig, size, `nm`, section dumps; recorded in `58-05-SUMMARY.md`); `sh firmware/tests/check_panel_diff.sh`; no edit under `.planning/phases/47*`.

### Sampling Rate
- Per task commit: the quick command for the touched area.
- Per wave merge: full pytest suite via `scripts/run-all-tests.sh`, host C suite, function-size and comment-history checks, ruff, mypy.
- Phase gate: full suite green plus the must-not-break list before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] fixtures and tests for `check_production_config.sh built <dir> second|ee02`
- [ ] `firmware/tests/check_provision_guard.sh` and its wiring in `run_host_tests.sh`
- [ ] `deploy/tests/test_release_assets.py` for `scripts/fw_release_assets.py`
- [ ] second-profile marker in `test_wake_deadline.c` and `test_panel_guard.c`
- [ ] pytest asserting each non-simulated profile's `max_app_bytes` equals the `ota_0` size in `firmware/partitions.csv`

### Owner-only (never faked)
Written confirmation to lift the switch; real signed https OTA on a second-type frame with the production channel, including a deliberately failing update that stays on the previous firmware (criterion 5); measured refresh time, busy waits, battery sense, LED, buttons, flash size (criterion 7); companion walk-through in English and French as admin and invited user: pair, assign, layout, display on/off, quiet hours, detection, health and battery, schedule update, retire, re-activate (criterion 9); the landscape preview crop look.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2/V3/V4 Auth, session, access | no change | existing Auth0 + local roles; second-type frames use existing per-device matrix |
| V5 Input Validation | yes | `[a-z0-9-]{1,64}` allow-list for type keys and release asset names before they reach a path or shell; symlink refusal in `import-dir`; env switch accepted only as exactly "1" |
| V6 Cryptography | yes | one RSA-3072 signing key, never hand-rolled; verify against the committed public key; key only via `env:` in the reviewer-gated environment |
| V10/V14 Config and supply chain | yes | digest-pinned signing container with `--network none`; production switch fails closed; deploy parses env file with fixed-key regex |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Hostile asset name in a GitHub release flows into shell | Tampering | allow-list regex in a Python function; no `eval`; quote everything |
| Typed key used as a path component | Tampering | `_TYPE_KEY_RE` shape check precedes path building (existing) |
| Live-frame secret overwritten by provisioning the wrong board | Tampering / DoS | typed MAC guard (D-05) |
| Wrong board's image published under the other type | Spoofing | per-board build dirs, built-mode config check, manifest from matching dir |
| Sim types exposed in production by reusing the sim switch | Elevation | dedicated switch; test pins that env template and units never set either |
| Signing key leaking through logs or `run:` text | Info disclosure | key via `env:` to a 0600 temp file, shredded in an `if: always()` step; existing test scans every `run:` block |

## Proposed Wave Split

Dependencies: switch name (W1-A) -> import/activate/manifest/reconcile (W2); behaviour known -> docs (W3); Phase 57 release published -> release workflow and everything after (W4). File ownership is disjoint inside a wave.

**Wave 1 (parallel, no blockers, nothing touches `firmware-release.yml`)**
- 64-01 Production switch in `server/hardware.py`, tests (`server/test_hardware.py`), `deploy/skypane.env.example` commented line, registry/test-support fixture. (HW2-04)
- 64-02 CI build of the second board: `firmware.yml` `build-second` job, `check_production_config.sh` board argument + fixtures, partitions-bound pytest. (HW2-03, crit 1)
- 64-03 `provision.sh` typed guard + `check_provision_guard.sh` + wiring. (HW2-05, crit 8)
- 64-04 Companion parity and render: previews with profile, battery curve at four call sites, landscape hold marks. (HW2-04, crit 6) Can be split in two plans (companion; render) since files are disjoint.
- 64-05 Firmware assumptions, code part: `wake_deadline.h` second-profile blit, second budget in `sdkconfig.second.defaults`, Kconfig help text, host test profiles, `panel_guard.h` text. Numbers use the documented worst-case formula until the owner supplies measured values. (HW2-05, crit 7 partial)

**Wave 2 (needs 64-01)**
- 64-06 `import-dir` skip semantics, `activate.sh` forwarding, `fw_release_manifest.py` switch independence, `ci.yml` typed download with `scripts/fw_release_assets.py` and tests. (HW2-03, crit 2-3)
- 64-07 Type-level reconcile in `fleet_cycle` and tests. (HW2-03, crit 5 automated part)

**Wave 3 (documents, after Wave 2)**
- 64-08 Docs: `firmware/SIGNING.md` per-type release section, `firmware/VENDOR.md`, `deploy/README.md` (typed release, lift runbook, import after lift), `README.md` second-board procedure, `hardware/SECOND-HARDWARE*.md` support guide. (HW2-05, crit 8)

**Wave 4 (BLOCKED on the Phase 57 release being published)**
- 64-09 `firmware-release.yml`: typed second-board build, sign, verify, manifest, stage, publish; dispatch stays last. Check the live frame's assets and signed image are unchanged against the Phase 57 release.
- 64-10 Owner-validated checkpoints (non-autonomous): lift confirmation and switch on the VPS; first signed typed release and deploy; real signed https OTA and failure case (crit 5); measured values entered in `sdkconfig.second.defaults`, `server/hardware.py` provenance and docs (crit 7); EN/FR walk-through as admin and invited user (crit 9).

## Sources

### Primary (HIGH confidence)
- Repository code read in this session: `server/hardware.py`, `server/firmware_cli.py`, `server/firmware_registry.py`, `server/fleet_cycle.py`, `server/poll_cycle.py`, `stub-server/byos_server.py`, `server/plane/render/{layout,landscape,landscape_hold,landscape_card}.py`, `companion/{theme_preview,preview_images,battery,page_context,device_scope,console_pairing,ui_shell,sign_in}.py`, `scripts/fw_release_manifest.py`, `firmware/{build.sh,provision.sh,flash-second.sh,sdkconfig.second.defaults,partitions.csv}`, `firmware/main/{wake_deadline.h,wake_guard.c,epd7in3e.c,Kconfig.projbuild}`, `firmware/tests/*`, `.github/workflows/{firmware,firmware-release,ci}.yml`, `deploy/{activate.sh,README.md,tests/*}`.
- `.planning/workstreams/v1-2/phases/64-*/64-CONTEXT.md`, `64-AUDIT.md`, ROADMAP "Phase 64", REQUIREMENTS HW2-03..05, STATE.md.

### Secondary / Tertiary
- None; no external documentation was needed (no new library).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (nothing new)
- Architecture and code paths: HIGH (read directly, audit claims re-checked; two audit claims corrected: reconcile scope, import env visibility)
- Pitfalls: HIGH for code-derived; MEDIUM for 7.3 inch timing (unmeasured)

**Research date:** 2026-11-14
**Valid until:** until Phase 57 publishes or `main` changes the files above (about 14 days)
