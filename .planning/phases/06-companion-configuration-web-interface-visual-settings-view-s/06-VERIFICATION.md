---
phase: 06-companion-configuration-web-interface-visual-settings-view-s
verified: 2026-08-28T09:45:00Z
status: passed
score: 12/12 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 6: Companion Configuration Web Interface Verification Report

**Phase Goal:** A user can reach a password-protected companion web page — a new, separate service on its own nip.io subdomain, not touching the vendored device-protocol server — to choose a validated display theme, select which Orly runway is tracked, monitor the device's health and the ADS-B sources' reliability over time, browse recent flight/render history, see airline-coverage gaps, and debug the render pipeline directly, all without SSH access to the VPS.
**Verified:** 2026-08-28
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Companion service runs as a separate, password-protected service on its own nip.io subdomain, never touching the vendored device-protocol server | ✓ VERIFIED | `companion/` is a standalone stdlib package (no imports from `stub-server/`); `deploy/skypane-companion.service` is a separate systemd unit; `deploy/Caddyfile` has a distinct `config-`-prefixed site block (`grep -c "nip.io {"` = 2); `git status --porcelain stub-server/` empty per 06-11/06-12. Live-verified in 06-12: companion hostname answers over TLS, unauthenticated `/config` redirects to `/login` (303), port 8643 refused directly from outside the VPS, device-protocol hostname unaffected (still 401 on unauth). |
| 2 (CFG-01) | User can choose a validated display theme, without SSH | ✓ VERIFIED | `companion/pages/config_page.py::theme_fieldset()` renders radios from `server/device_config.py::THEMES`; `handle_post()` server-side-validates against `THEME_IDS`; `server/plane/render.py` resolves colours through the same registry. `companion/test_config_page.py` 15/15 pass including a real HTTP save round trip. Only one theme (`sky`) is registered today — intentional per REQUIREMENTS.md CFG-01 text ("scoped to DEPARTING/ARRIVING theme variants validated on real glass during Phase 7"); the picker mechanism itself is fully functional and registry-driven (adding a second theme requires zero code change). |
| 3 (CFG-12) | User can select which of Orly's three runways is tracked | ✓ VERIFIED | `server/plane/detect.py::select_aircraft_for_runway()` generalizes runway-3-only detection; `config_page.py::runway_fieldset()`/`handle_post()` save/validate against `device_config.RUNWAYS`; `server/poll_loop.py` threads the saved runway into detection and rendering every cycle (`server/test_poll_loop.py` 42/43, see note below). Live-verified 2026-08-28 (`adsb-test/RUNWAY-GATE-VERIFICATION.md`, 90-min/480-poll real capture): runway 3 confirmed against fresh traffic, 02-20 selects real traffic correctly and exclusively (corridor threshold not fully re-derived — honestly reported, not a code defect), 06-24 observed zero traffic (genuine null result, honestly reported as still unvalidated). |
| 4 (CFG-03) | User can see device health (last poll, battery voltage trend) without SSH | ✓ VERIFIED | `companion/pages/health_page.py` renders two independently-thresholded freshness signals plus a battery trend table + inline SVG sparkline; `server/history_db.py::tail_caddy_battery_log()`/`ingest_caddy_battery_log()` extract `X-Battery-Mv` from Caddy's durable access log (the only path given the vendored device server can't change). `companion/test_status_pages.py` 25/25 pass. Live-verified in 06-12: real `device_health` rows landing with plausible mV values (4010/4078/4090). A real production gap was found and fixed live in 06-12 (`ingest_caddy_battery_log()` was built+tested in 06-01 but never wired into a production caller until 06-12's `--caddy-log` flag). |
| 5 (CFG-05) | Server-side ADS-B source failure surfaces an on-panel alert directing the user to the companion page | ✓ VERIFIED | `server/plane/detect.py::poll_current_aircraft(diagnostics=...)` distinguishes all-providers-failed from no-aircraft; `server/plane/render.py::draw_source_fault_badge()` is palette-safe and off by default; `poll_loop.py::_classify_source_fault()` gates strictly on all-providers-failed, never an empty selection; `health_page.py` renders the landing explanation when the flag is set. `server/test_render.py` 60/60, `server/test_poll_loop.py` covers the fault-transition re-render-once behavior. |
| 6 (CFG-06) | User can browse a log of recently detected flights, not just current/previous | ✓ VERIFIED | `server/history_db.py::runway_events` schema + `recent_runway_events()`; `poll_loop.py::_should_record_event()` writes rows only on a real hex/state/corroboration transition; `companion/pages/history_page.py` renders newest-first with the same wording the panel uses. `companion/test_view_pages.py` 19/19. |
| 7 (CFG-07) | User can manually trigger an immediate detection/render cycle, rate-limited | ✓ VERIFIED | `companion/app.py`'s `POST /poll-now` imports `server.poll_loop` and calls `run_once()` in-process (the real production path), gated by a server-global cooldown persisted in `history.db`'s meta table. `companion/test_companion_app.py` 51/51 (grown from 49 during the 06-12 checkpoint fix). Live-verified in 06-12 with a real defect found and fixed: the deployed companion service was missing `--geofence`, causing every trigger to crash with a misleading "couldn't save settings" message — fixed (`deploy/skypane-companion.service` now passes `--geofence`) and re-verified against the live service. |
| 8 (CFG-08) | User can see airline/route resolution statistics over time | ✓ VERIFIED | `server/history_db.py::route_source_counts()`/`corroboration_counts()`; `companion/pages/airlines_page.py::resolution_stats()` breaks down `enrich.resolve_route()`'s four documented categories with a resolved-percentage headline. `companion/test_status_pages.py` 25/25. |
| 9 (CFG-09) | User can toggle dark/light theme for the web interface itself | ✓ VERIFIED | `companion/static/style.css` implements `prefers-color-scheme` + `data-ui-theme` override; `companion/app.py`'s `POST /ui-theme` (exempt from session auth by design, cookie-only, low-stakes) validates and sets the cookie; live-verified via curl round trip in 06-05. Live-verified again in 06-12 (both palettes readable, "OK" per developer sign-off; toggle-placement UX feedback backlogged as 999.3, not a functional gap). |
| 10 (CFG-10) | User can see a live preview of the physical panel, without SSH | ✓ VERIFIED | `server/panel_preview.py::unpack_panel()` is a proven exact inverse of `pack_panel()` (11/11 checks, full-canvas round trip); `GET /preview.png` served by `companion/app.py`; `companion/pages/preview_page.py` renders it with the mandatory not-colour-accurate caveat and an honest no-panel-yet fallback. `companion/test_view_pages.py` includes a real end-to-end HTTP PNG fetch. |
| 11 (CFG-11) | User can browse a gallery of recently rendered panels, without SSH | ✓ VERIFIED | `companion/app.py`'s gallery file route resolves names against a real `os.scandir()` listing (never `os.path.join()` on a client string — proven against 3 traversal payloads + a canary file); `poll_loop.py::_save_to_gallery()`/`_prune_gallery()` cap the archive at 25, pruning oldest-first; `preview_page.py::gallery_tiles()` displays newest 12. Confirmed live by the developer in 06-12 sign-off ("OK", capacities explained correctly: 25 kept / 12 shown). |
| 12 (CFG-04) | User can see which ADS-B callsign prefixes have gone unrecognized, without another manual audit | ✓ VERIFIED | `companion/pages/airlines_page.py::unresolved_rows()` reads `poll_state.json`'s `unresolved_prefixes` strictly through `poll_loop.load_poll_state()`, read-only (no form/button, D-16), deterministic sort, malformed-entry-tolerant, hostile-value-escaped. `companion/test_status_pages.py` 25/25. |

**Score:** 12/12 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/device_config.py` | Theme/runway registry + validated persistence | ✓ VERIFIED | 235 lines, 16/16 own-harness checks pass, imported by render/config_page/poll_loop |
| `server/history_db.py` | SQLite history/health/meta store + Caddy battery tailer | ✓ VERIFIED | 406 lines, WAL+busy_timeout, used by health/airlines/history pages and poll_loop |
| `server/panel_preview.py` | Exact inverse of `pack_panel()`, PNG encode | ✓ VERIFIED | 153 lines, 11/11 checks, used by `/preview.png` route |
| `companion/auth.py` | HMAC session cookie, fail-closed, constant-time compare | ✓ VERIFIED | `hmac.compare_digest` used (grep confirms ≥2 occurrences), `AuthNotConfigured` fail-closed |
| `companion/layout.py` + `static/style.css` | Single escaping call site, full design system, dark/light/mobile | ✓ VERIFIED | `escape_html()` single call site; CSS has `prefers-color-scheme`, `data-ui-theme`, 44px tap targets, and (post-06-12 fix) `.data-table-wrap { overflow-x: auto }` for mobile table cropping |
| `companion/app.py` | Router, D-02 auth gate, poll trigger, preview/gallery routes | ✓ VERIFIED | 584 lines, 12 `require_session()` call sites across 9 gated routes, gallery route uses `os.scandir()` not `os.path.join()` |
| `companion/pages/*.py` (5 modules) | Config/health/airlines/history/preview page bodies | ✓ VERIFIED | All 5 non-stub, render real data from history_db/device_config/poll_loop, escaped throughout |
| `server/plane/render.py` | Theme/runway-aware colours+labels, fault badge | ✓ VERIFIED | 1243 lines, 60/60 own-harness checks, palette-legal with badge drawn |
| `server/poll_loop.py` | Config threading, history/gallery writes, fault classification | ✓ VERIFIED | 1093 lines, 42/43 own-harness checks (1 known macOS-vs-Linux font-rasterization digest mismatch, documented below, confirmed passing on CI/Linux) |
| `deploy/skypane-companion.service`, `deploy/Caddyfile`, `deploy/provision.sh` | Independent systemd unit, TLS site block, firewall deny | ✓ VERIFIED | Separate unit with 5 hardening directives, `ufw deny 8643/tcp`, distinct `config-` Caddy block, `--geofence` flag present (post-06-12 live fix) |
| `adsb-test/RUNWAY-GATE-VERIFICATION.md` | Live-capture verification of corridor thresholds | ✓ VERIFIED | Exists, 8.5KB, documents a real 90-min/480-poll capture with honest per-runway verdicts (confirmed/partially-confirmed/still-unvalidated) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `companion/pages/config_page.py` | `server/device_config.py` | registry-membership validation on save | ✓ WIRED | `handle_post()` validates against `THEME_IDS`/`RUNWAY_IDS`, never the forgiving `normalise_*` read-path helpers |
| `companion/app.py` (every authenticated route) | `companion/auth.py` | `require_session()` | ✓ WIRED | 12 call sites; live-demonstrated regression test in 06-05 (removing one call site drops the harness to 48/49) |
| `server/poll_loop.py` | `server/device_config.py` | `load_device_config()` read once per cycle | ✓ WIRED | `grep -c device_config.load_device_config server/poll_loop.py` == 1, confirmed in 06-10-SUMMARY.md |
| `server/poll_loop.py` | `server/history_db.py` | `record_runway_event()`/`record_device_health()`/`set_meta()` | ✓ WIRED | Gated on real transitions, degrade-without-raise proven against a simulated DB lock |
| `deploy/Caddyfile` (device-protocol block) | `server/history_db.py::tail_caddy_battery_log()` | durable rolled access-log file | ✓ WIRED | Log directive moved from `output stdout` to a rolled file (06-11); live-confirmed field-path match in 06-12; `poll_loop.py --caddy-log` wired as the missing reader (06-12 live fix, since 06-01 built but never called it) |
| `companion/app.py` `/poll-now` | `server/poll_loop.py::run_once()` | in-process call, no subprocess | ✓ WIRED | `grep -c subprocess companion/app.py` == 0; live-fixed in 06-12 (missing `--geofence` in the systemd unit caused a crash) |
| `companion/app.py` gallery route | filesystem | `os.scandir()` listing match, never path-join | ✓ WIRED | Proven against 3 traversal payloads + a canary file placed one level above the gallery dir |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|---------------------|--------|
| `health_page.py` battery trend | `history_db.recent_device_health()` | Caddy access log → `ingest_caddy_battery_log()` → SQLite | ✓ Yes — live-confirmed rows with real mV values (4010/4078/4090) | ✓ FLOWING |
| `history_page.py` flight log | `history_db.recent_runway_events()` | `poll_loop.py::_record_history()` on real transitions | ✓ Yes — schema + gating proven by `test_poll_loop.py`; live wiring confirmed by 06-10/06-11 deploy | ✓ FLOWING |
| `preview_page.py` live image | `panel_preview.read_panel_file()`/`panel_png_bytes()` | `state_dir/panel.bin` written by real poll cycles | ✓ Yes — live end-to-end HTTP PNG fetch in `test_view_pages.py`; distinct 404/503 failure modes | ✓ FLOWING |
| `preview_page.py` gallery | `companion/app.py::gallery_entries()` | `poll_loop.py::_save_to_gallery()` on changed panels | ✓ Yes — capped/pruned; live-confirmed by developer sign-off (25 kept / 12 shown matches design) | ✓ FLOWING |
| `airlines_page.py` unresolved registry | `poll_loop.load_poll_state()`'s `unresolved_prefixes` | `enrich.py`'s production registry writer | ✓ Yes — read-only pass-through, no re-derivation | ✓ FLOWING |
| `config_page.py` theme/runway pickers | `device_config.load_device_config()` | `save_device_config()` on a validated POST | ✓ Yes — real HTTP save round trip proven in `test_config_page.py`, plus a live 06-12 checkpoint save/confirm | ✓ FLOWING |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full canonical suite (15 harnesses) | `bash scripts/run-all-tests.sh` (run live, this session) | 14/15 harnesses fully green; `server/test_poll_loop.py` 42/43 (1 fail: pinned panel.bin digest, macOS vs Linux Pillow/FreeType text rasterization — documented in the test file itself as a known, non-logic, platform-specific difference; pinned to the Linux/CI value; confirmed passing on GitHub Actions `ubuntu-latest` for the corresponding PR #14 — see below) | ✓ PASS (with one documented, expected local-platform exception) |
| PR #14 CI (Linux) | `gh pr checks 14` (run live, this session) | "Lint, test, coverage, attribution: pass" | ✓ PASS |
| ruff lint | `server/.venv/bin/python3 -m ruff check .` (run live, this session) | "All checks passed!" | ✓ PASS |
| Debt-marker scan | `grep -rn -E "TBD|FIXME|XXX|TODO|HACK|placeholder"` across `companion/`, `server/device_config.py`, `server/history_db.py`, `server/panel_preview.py`, `server/plane/render.py`, `server/poll_loop.py`, `server/plane/detect.py`, `deploy/` | No matches | ✓ PASS |
| Auth gate route-by-route | `companion/test_companion_app.py` (51/51, includes 06-12's two new regression checks) | pass | ✓ PASS |
| Coverage threshold | `pyproject.toml` `fail_under=83`, measured 88% in this session's live run | 88% ≥ 83% | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|-------------|--------|----------|
| CFG-01 | 06-01, 06-06, 06-07 | Visual/theme configuration via web | ✓ SATISFIED | Theme picker live end-to-end; only one registry entry today, intentionally scoped to Phase 7 |
| CFG-03 | 06-01, 06-08, 06-10, 06-11, 06-12 | Device health status via web | ✓ SATISFIED | Live-confirmed real battery telemetry rows |
| CFG-04 | 06-01, 06-08 | Unrecognized ADS-B prefixes visible | ✓ SATISFIED | Read-only registry page, tested |
| CFG-05 | 06-02, 06-06, 06-08, 06-10 | On-panel fault icon + companion detail | ✓ SATISFIED | Diagnostics-driven, palette-safe, landing block wired |
| CFG-06 | 06-01, 06-09, 06-10 | Flight-history log via web | ✓ SATISFIED | Newest-first, transition-gated writes |
| CFG-07 | 06-05, 06-07, 06-12 | Manual poll trigger, rate-limited | ✓ SATISFIED | In-process, cooldown-gated; live defect found+fixed |
| CFG-08 | 06-01, 06-08 | Route-resolution statistics via web | ✓ SATISFIED | Windowed rate breakdown, tested |
| CFG-09 | 06-04, 06-05 | Dark/light theme toggle for the page | ✓ SATISFIED | Cookie-based, CSS-only mechanism, live-verified |
| CFG-10 | 06-03, 06-05, 06-09 | Live panel preview via web | ✓ SATISFIED | Exact-inverse decoder, real HTTP PNG round trip |
| CFG-11 | 06-05, 06-09, 06-10 | Render gallery via web | ✓ SATISFIED | Capped, pruned, path-traversal-safe |
| CFG-12 | 06-02, 06-06, 06-07, 06-10, 06-12 | Runway selection via web | ✓ SATISFIED | Mechanism fully functional; runway 3 live-confirmed, 02-20 partially, 06-24 still unvalidated (honest null result, not a code defect — see note below) |

No orphaned requirements: CFG-02 was explicitly and correctly descoped back to v2 during `/gsd-discuss-phase 6` (still nothing to switch to until a second view exists) — it does not appear in any plan's `requirements` field for this phase, matching REQUIREMENTS.md's own v2 section.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder markers in any file touched by this phase's 12 plans. `ruff check .` clean.

## Notes for the Record (non-blocking)

1. **REQUIREMENTS.md's "Traceability" table (lines 105-115) is stale** — it still reads "Pending (not yet planned)" for CFG-04/05/06/08/09/10/11 even though the checkbox list above it (the authoritative source, lines 28-38) marks all of CFG-01/03-12 `[x]` complete. This staleness was already self-identified and documented in 06-10-SUMMARY.md ("Noted, not fixed... a staleness gap left by prior plans"). Cosmetic documentation debt, not a functional gap — worth a small doc pass next time REQUIREMENTS.md is touched.
2. **`server/test_poll_loop.py`'s pinned panel.bin digest fails on this local macOS environment** but is explicitly documented in the test file as a macOS-vs-Linux Pillow/FreeType anti-aliased-text rasterization difference, pinned to the Linux/CI value (Linux is authoritative — it's what CI and the production VPS run). Confirmed passing on GitHub Actions in this session via `gh pr checks 14`. Not a real regression.
3. **Runway 06-24's corridor threshold remains genuinely unvalidated** against real traffic (zero observed selections in a 90-minute live capture) and runway 02-20's threshold is only partially re-derived (the capture method doesn't surface rejected-candidate geometry needed for a full empty-band re-derivation). This is honestly documented in `adsb-test/RUNWAY-GATE-VERIFICATION.md` itself, per the plan's own instruction that a null result must be reported as such rather than papered over. The CFG-12 must-have ("corridor thresholds checked against real captured traffic rather than shipped on a copied guess") was satisfied — the check was performed and reported honestly — but full confidence in 06-24 specifically awaits future real traffic on that runway.
4. **06-12-SUMMARY.md's Task 3 narrative ends with "Phase closure is not yet declared — awaiting the developer's explicit 'approved'"**, written before the final commit (`b8429c0`) that recorded the completed sign-off feedback. `.planning/ROADMAP.md` (locally modified, uncommitted at time of this verification) already marks Phase 6 as 12/12 complete. The developer's own item-by-item checkpoint record shows every one of 12 UAT items was actually tried (never skipped), two real functional defects were found, fixed, and re-verified live, and every remaining item is explicit UX/design feedback the developer themselves framed as "would be nicer" (not "broken"), backlogged as separate future phase items (999.3-999.6). Treating this as sufficient developer sign-off per this task's own briefing; flagging the literal "awaiting explicit approved" wording here so a human can close the loop with an explicit confirmation if desired.

### Human Verification Required

None. The phase's own live developer checkpoint (06-12 Task 3) already performed real-device UAT across all 12 items, found and fixed two genuine defects, and re-verified them live — this substitutes for a fresh human-verification pass at this stage. See Note 4 above for the one loose thread (an explicit final "approved" from the developer) that a human may wish to close out formally.

### Gaps Summary

No gaps found. All 12 observable truths derived from the phase goal and CFG-01/03-12 requirements are verified against the actual codebase: artifacts exist, are substantive (no stubs, no placeholders), are wired end-to-end, and — where checkable — carry real production data confirmed live on the deployed VPS during the 06-12 checkpoint (battery telemetry, poll-trigger fix, mobile table-crop fix, runway-gate live capture). The one local test failure is a documented, non-regression, platform-specific artifact confirmed green on the authoritative CI/Linux platform. The phase goal is achieved.

---
*Verified: 2026-08-28*
*Verifier: Claude (gsd-verifier)*
