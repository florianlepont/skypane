---
phase: 02-plane-view-end-to-end-slice
verified: 2026-08-26T09:33:32Z
status: passed
score: 4/4 must-haves verified (roadmap success criteria); 18/18 plan-level must-have truths verified
behavior_unverified: 0
overrides_applied: 0
human_verification: []
---

# Phase 2: Plane View — End-to-End Slice Verification Report

**Phase Goal:** A user can glance at the frame and see live runway-3 plane data — the first complete vertical slice, wired end-to-end from ADS-B detection through server rendering to the physical display.
**Verified:** 2026-08-26T09:33:32Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (ROADMAP Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can see flight number, airline, and destination for the next plane departing Orly runway 3, rendered on the physical frame | ✓ VERIFIED | `server/plane/render.py`'s `draw_route_line()`/`draw_airline_line()` draw zones 7/9 with a `"TO " + destination_city` prefix for `STATE_DEPARTING` (`ROUTE_PREFIX_DEPARTING`). `server/test_render.py` (re-run live, 25/25 pass) directly asserts "departing render with a resolved route draws the route line ('TO' + destination city) and the airline line (airline name)". Confirmed further on real hardware in 02-05 Task 3 via the real production render code path (see Truth 4). |
| 2 | When runway 3 is in arrival configuration, user instead sees flight number, airline, and origin for the next landing plane | ✓ VERIFIED | Same mechanism mirrored for `STATE_ARRIVING` (`ROUTE_PREFIX_ARRIVING` = "FROM" + `origin_city`, via `enrich.city_for_state()`). `test_render.py`: "arriving render draws the route line with prefix 'FROM' + origin city" — re-run live, passes. Directly confirmed on real glass: 02-05 Task 3's real-flight cross-check rendered **DAH1112 from Béjaïa as an arrival**, origin shown (not destination), developer-confirmed layout "correct — left-facing, no clipping". |
| 3 | As real aircraft use runway 3, the plane view updates to reflect the new flight as detected by the local ADS-B receiver — not a fixed schedule | ✓ VERIFIED | `server/plane/detect.py`'s `poll_current_aircraft()`/`select_runway3_aircraft()` query the live aggregators (airplanes.live primary, adsb.fi secondary) every cycle; `server/poll_loop.py` re-detects and re-renders from scratch each invocation, with no timetable/schedule input anywhere in the pipeline. `server/test_plane_detection.py` (6/6, re-run live) and `server/test_pipeline_e2e.py` (5/5, re-run live, including the D-04 "empty poll leaves panel.bin byte-identical" check) confirm the mechanics. Directly confirmed running against real traffic on the live VPS: 02-05-SUMMARY.md quotes `journalctl -u inkframe-poll` showing successive real detections (e.g. `callsign=RAM664Y ... route_source=fresh_hit panel_changed=True`), and Task 3's forced-fallback test independently re-confirmed `state_source=held route_source=held panel_changed=False` during a real detection gap (D-04 hold-last, not a fixed schedule or an expiring/blank state). |
| 4 | The full pipeline (ADS-B detection → server render → device poll → display) runs end-to-end on real hardware, replacing the Phase 1 stub server | ✓ VERIFIED | 02-05 Task 3, re-checked in this verification: `firmware/flash.sh` flashed real firmware pointed at `INK_API_BASE=https://<public-host>`; `journalctl -u inkframe-byos` on the live VPS shows `setup` → 200, `display` → 200, `img/*.bin` → 200 (960,000 bytes, SHA-256-matched); Caddy's JSON access log shows real TLS 1.2 (`"version":771`) handshakes on port 443 for both requests, not port 80. Firmware source confirms this needed no protocol code change: `firmware/main/api_client.c` already compiles in `esp_crt_bundle_attach` and accepts either an `http://` or `https://` `INK_API_BASE` (git-blamed to `d06d08e`/`f55fe05`, both Phase 1 commits) — Phase 2's HTTPS move was a config change (`INK_API_BASE` + `stub-server/byos_server.py --image-url-scheme https`), exactly as `02-05-SUMMARY.md` and the code comment in `api_client.c` both claim. `stub-server/test_poll_cycle.py` (re-run live, 17/17 pass) directly exercises both the default-http and explicit-https `--image-url-scheme` code paths. Developer confirmed on-glass legibility ("clearly legible") and edge quality ("hard, flat edges") viewed from the frame's actual mounting distance. |

**Score:** 4/4 truths verified (0 present, behavior-unverified)

### Plan-Level Must-Haves (merged from PLAN frontmatter, Step 2b)

All 18 plan-level `must_haves.truths` across 02-01 through 02-05 were independently checked against the codebase (not just SUMMARY claims) and either exercised by a re-run automated test or confirmed by direct code inspection / real on-glass evidence.

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 02-01 | Server identifies exactly one aircraft as "using runway 3 right now", deterministically, even with several in the geofence | ✓ VERIFIED | `detect.select_runway3_aircraft()`'s total order (altitude, seen_pos, hex); `test_plane_detection.py` "is deterministic under input reordering" — re-run, pass |
| 2 | 02-01 | Served panel.bin changes to the detected aircraft's flight number, driven by ADS-B not a timetable (PLANE-03) | ✓ VERIFIED | See Roadmap Truth 3 |
| 3 | 02-01 | Phase 1 protocol loop downloads/hash-verifies the freshly rendered panel with no firmware code change | ✓ VERIFIED | See Roadmap Truth 4 — firmware HTTPS support predates Phase 2 (git blame) |
| 4 | 02-01 | No aircraft in geofence → previously rendered panel keeps being served, no waiting screen, no expiry (D-04) | ✓ VERIFIED | `stub-server/byos_server.py`'s `do_GET` reads `self.args.image` from disk on every request with no expiry/TTL logic; `test_pipeline_e2e.py` "run_once(empty fixture) leaves panel.bin byte-identical (D-04)" — re-run, pass |
| 5 | 02-02 | Colour + explicit word tells the user departing (PLANE-01) vs. arriving (PLANE-02) | ✓ VERIFIED | `render.py`'s `STATE_TO_BG_INDEX`/`STATE_TO_LABEL` maps; `test_render.py` palette/label assertions — re-run, pass; confirmed on-glass (Blue/Green full-bleed field + label, per 02-UI-SPEC) |
| 6 | 02-02 | Departing/arriving call comes from the aircraft's own vertical rate, not an external feed (D-03) | ✓ VERIFIED | `runway_config.infer_runway_config()` takes only `vertical_rate_fpm`; no NOTAM/schedule input anywhere in `server/` |
| 7 | 02-02 | A single noisy vertical-rate sample near touchdown does not flip DEPARTING/ARRIVING | ✓ VERIFIED | `test_runway_config.py`: "second +48 flare reading still holds arriving (real landing, not a bug)" against the real `track_arrival_440cb1.json` fixture — re-run, pass |
| 8 | 02-03 | Panel reads as an ambient poster — the silhouette is the first thing the eye lands on | ✓ VERIFIED (human-confirmed) | Already exercised as a real human-in-the-loop checkpoint in 02-05 Task 3, not re-flagged: developer reported the on-glass render as "expected, not washed out or noisy" with correct layout |
| 9 | 02-03 | Silhouette nose points right for departure (PLANE-01), left for arrival (PLANE-02) | ✓ VERIFIED | `render.py`'s `draw_silhouette()` `required_nose` logic + mirror; `test_render.py` mirroring assertions — re-run, pass; on-glass DAH1112 arrival confirmed "left-facing" |
| 10 | 02-03 | Silhouette renders as a flat White shape with hard edges, no grey halo/dither | ✓ VERIFIED | `test_render.py`: "contains exactly two distinct palette indices (no anti-aliasing)" — re-run, pass; on-glass confirmed "hard, flat edges" |
| 11 | 02-04 | Departing panel shows flight number, airline, destination city (PLANE-01) | ✓ VERIFIED | See Roadmap Truth 1 |
| 12 | 02-04 | Arriving panel shows flight number, airline, origin city (PLANE-02) | ✓ VERIFIED | See Roadmap Truth 2 |
| 13 | 02-04 | No-route lookup degrades cleanly to "Route unavailable" — no blank line, no placeholder, no crash | ✓ VERIFIED | `enrich.lookup_route()` returns `None` on every failure mode without raising; `test_render.py` "enrichment-miss render... draws the airline line with the exact fallback text 'Route unavailable'" and "still renders the silhouette, state label, and flight-number caption" — re-run, pass. Directly re-exercised on real hardware in 02-05 Task 3 via the actual production call `render.render_panel({"callsign":"EJU84YF",...}, "arriving", route=None)` (EJU84YF being the confirmed real adsbdb-404 fixture), developer-confirmed on-glass: "yes it does" |
| 14 | 02-04 | An already-looked-up callsign is never re-queried on a later poll cycle | ✓ VERIFIED | `enrich.lookup_route()`'s cache-hit/miss short-circuit; `test_enrich.py`: "a cached miss... is never re-queried on a later lookup" — re-run, pass |
| 15 | 02-05 | Physical frame shows the live runway-3 poster, fetched over HTTPS from an always-on internet-reachable server | ✓ VERIFIED | See Roadmap Truth 4 |
| 16 | 02-05 | Device downloads the panel image over HTTPS, not plaintext HTTP, once Caddy is in front | ✓ VERIFIED | Caddy TLS 1.2 handshake confirmed in access log (`version:771`); `deploy/inkframe-byos.service` hardcodes `--image-url-scheme https`; app port 8642 confirmed `ufw deny`d and externally unreachable (`curl` to `:8642` timed out per 02-05-SUMMARY) |
| 17 | 02-05 | Poll loop keeps running unattended on a timer, surviving reboots and individual cycle failures | ✓ VERIFIED (config-level; not reboot-tested this session) | `deploy/provision.sh` runs `systemctl enable inkframe-poll.timer` (survives reboot by systemd design); `inkframe-poll.service`'s comment and systemd's own default behaviour mean a failed oneshot does not disable its timer — corroborated live by `journalctl -u inkframe-poll` showing continued successive cycles across real detection gaps (D-04 hold) without the timer stopping. **Caveat:** an actual VPS reboot was not performed during this phase to empirically prove `OnBootSec=30s` fires post-reboot; this is inferred from systemd's documented `enable` semantics, not directly observed. Not a phase blocker (this is inherent, standard systemd unit behaviour, not custom project code), but worth an eventual real reboot check |
| 18 | 02-05 | Full pipeline replaces Phase 1's local stub server, closing ROADMAP Phase 2 success criterion 4 | ✓ VERIFIED | See Roadmap Truth 4 |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/panel_format.py` | Spectra 6 wire-format packer + palette bridge | ✓ VERIFIED | `INDEX_TO_NIBBLE` maps Pillow's 6 contiguous palette indices to the 6 non-contiguous legal nibble codes exactly as documented; `pack_panel()` re-exercised live via `test_pipeline_e2e.py`'s "panel.bin bytes decompose into only the six legal nibble codes" (pass) |
| `server/plane/detect.py` | Aggregator query + geofence filter + D-P2-01 selection rule | ✓ VERIFIED | 274 lines, substantive; re-run test suite 6/6 pass |
| `server/plane/runway_config.py` | D-03/D-P2-04 deadband state inference | ✓ VERIFIED | 97 lines; re-run test suite 14/14 pass, including real-fixture-backed descent and symmetry-derived climb cases (A-02-02-01 disclosed as provisional in-module, matching STATE.md) |
| `server/plane/enrich.py` | adsbdb enrichment client + persistent cache | ✓ VERIFIED | 265 lines; re-run test suite 16/16 pass |
| `server/plane/render.py` | Full panel compositor (silhouette, state colour/label, route/airline captions) | ✓ VERIFIED | 703 lines; re-run test suite 25/25 pass |
| `server/poll_loop.py` | systemd-oneshot detect→infer→enrich→render→atomic-swap entrypoint | ✓ VERIFIED | 288 lines; wires all four `server/plane/*` modules; re-run e2e suite 5/5 pass, exercising a real `byos_server.py` instance end to end |
| `server/assets/icons/aircraft-silhouette.png`, `plane-takeoff.png`, `plane-landing.png` | Vendored CC0 icon assets | ✓ VERIFIED | Present with `VENDOR.md` provenance; used by `render.py`'s `paste_mask()` and confirmed rendering correctly on-glass |
| `stub-server/byos_server.py` | Device-protocol server, now scheme-configurable | ✓ VERIFIED | `--image-url-scheme` flag confirmed present and both branches (http default / https) covered by `test_poll_cycle.py`, re-run 17/17 pass |
| `deploy/Caddyfile`, `deploy/inkframe-byos.service`, `deploy/inkframe-poll.{service,timer}`, `deploy/provision.sh`, `deploy/deploy.sh` | Full reviewable deploy-as-files infra | ✓ VERIFIED | All present, internally consistent (TLS termination → 127.0.0.1:8642 reverse proxy → hardened byos unit; 30s timer → hardened poll oneshot); live-provisioned and re-confirmed against the real OVH VPS per 02-05-SUMMARY's "Live Verification Evidence" section |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `detect.select_runway3_aircraft()` | `render.render_panel()` | direct function call through `poll_loop.run_once()` | ✓ WIRED | Confirmed in source (`poll_loop.py` lines 163-208) and by `test_pipeline_e2e.py`'s live exercise of the full chain |
| `render.render_panel()` | `poll_loop`'s atomic panel.bin swap | `write_panel_atomic()`, SHA-256 change-detection, tmp-write-then-`os.replace()` | ✓ WIRED | Confirmed in source; e2e test confirms unchanged input leaves panel.bin byte-identical (D-04) and a changed input produces a new hash |
| `poll_loop`'s panel.bin | `byos_server.py`'s `/device/v1/display` | `--image` CLI arg pointing at the same `panel.bin` path | ✓ WIRED | `deploy/inkframe-poll.service`'s `--state-dir ${INK_STATE_DIR}` and `deploy/inkframe-byos.service`'s `--image ${INK_STATE_DIR}/panel.bin` reference the identical `INK_STATE_DIR` env var — no path mismatch |
| `panel_format.INDEX_TO_NIBBLE` | wire bytes | `pack_panel()` | ✓ WIRED | Confirmed exact mapping in source; e2e test confirms only the 6 legal nibble codes ever appear in packed output |
| `runway_config.infer_runway_config()` | `render.render_panel()`'s background index / state label | `poll_loop.py`'s `confirmed_state` → `render_state` handoff | ✓ WIRED | Confirmed in source; `test_render.py` confirms departing/arriving renders differ correctly |
| `poll_state.json`'s `last_confirmed_state` | deadband hold-across-cycles behaviour | `load_poll_state()`/`save_poll_state()` around every `run_once()` | ✓ WIRED | Confirmed in source (D-P2-02); e2e test's second fixture run demonstrates state held across a simulated new process invocation |
| `enrich.lookup_route()` | `render.py` zones 7/9 | `route` param threaded through `poll_loop.py` into `render_panel()` | ✓ WIRED | Confirmed in source and by `test_render.py`'s resolved-route vs. fallback-route render assertions |
| `poll_state.json`'s `enrichment_cache` | never-re-query behaviour | persisted dict, not process memory | ✓ WIRED | Confirmed in source (D-P2-02, systemd oneshot has no in-process memory across cycles) and by `test_enrich.py`'s json round-trip cache test |
| Caddy (`:443`) | `byos_server.py` (`127.0.0.1:8642`) | `reverse_proxy` directive + `--image-url-scheme https` | ✓ WIRED | Confirmed in `Caddyfile` and `inkframe-byos.service`; live-confirmed via real TLS 1.2 handshakes in Caddy's access log and app-port 8642 refused externally (`ufw deny`) |
| `inkframe-poll.timer` | `inkframe-poll.service` | `Unit=inkframe-poll.service`, `OnUnitActiveSec=30s` | ✓ WIRED | Confirmed in unit file; `systemctl list-timers` live-confirmed the interval is honoured, and `journalctl` shows successive real cycles |
| Firmware `firmware/main/api_client.c` | real OVH server | `INK_API_BASE=https://<public-host>` + `esp_crt_bundle_attach` | ✓ WIRED | Confirmed via `secrets.h` (gitignored, referenced in 02-05-SUMMARY) and via live server logs showing successful `setup`/`display`/`img` round trips against the real device MAC |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| PLANE-01 | 02-01, 02-02, 02-03, 02-04, 02-05 | User can see flight number, airline, and destination for the next departing plane | ✓ SATISFIED | Roadmap Truths 1 and 4; REQUIREMENTS.md already marks `Complete`/`Phase 2`, corroborated by re-run tests and on-glass evidence |
| PLANE-02 | 02-01, 02-02, 02-03, 02-04, 02-05 | User can see flight number, airline, and origin for the next landing plane (wind-dependent) | ✓ SATISFIED | Roadmap Truths 2 and 4; directly corroborated by the real on-glass DAH1112 arrival cross-check |
| PLANE-03 | 02-01, 02-05 | Plane view updates one flight at a time, ADS-B-driven, not a fixed timetable | ✓ SATISFIED | Roadmap Truth 3; corroborated by real ADS-B detections logged on the live VPS |

No orphaned requirements: REQUIREMENTS.md's Phase-2-mapped requirements (PLANE-01/02/03) all appear in at least one plan's `requirements:` frontmatter field, and all three are marked `Complete`/`Phase 2` consistently across ROADMAP.md, REQUIREMENTS.md, and STATE.md.

### Anti-Patterns Found

A scan for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/"not yet implemented"/"coming soon" across `server/plane/*.py`, `server/poll_loop.py`, `server/panel_format.py`, `server/test_*.py`, `deploy/*.sh`, `deploy/*.service`, `deploy/*.timer`, `deploy/Caddyfile`, and `stub-server/byos_server.py` returned **no debt markers**. (One incidental match, `server/plane/render.py:15`, is a docstring note describing code that *used to be* a placeholder in 02-01 and was replaced in 02-03 — not a live stub.)

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `firmware/main/api_client.c` / `firmware/main/state_machine.c` | ~n/a (behavioural, not textual) | On a non-2xx `/device/v1/display` response (e.g. a stale/invalid bearer token), `fp_api_get_display()` returns `FP_ERR_HTTP_STATUS` and the poll cycle fails/backs off, but `fp_api_has_token()` is never reset — the same stale token is retried on every subsequent wake, forever, with no automatic recovery path | ℹ️ Info (not a Phase 2 blocker) | This is exactly the class of bug 02-05-SUMMARY.md's Task 3 diagnosed live and worked around by manually erasing the NVS partition (`esptool erase-region 0x9000 0x6000`). Confirmed by direct code read in this verification (`state_machine.c` line 46, `api_client.c` line 158-162) — the diagnosis in the SUMMARY is accurate, not spin. It is Phase-1-era firmware behaviour (DEVICE-03, already marked complete), not something Phase 2 introduced, and it does not prevent any of Phase 2's 4 success criteria from being true right now (the device is confirmed working against the real server post-fix). Not currently tracked in STATE.md's Blockers/Concerns list. **Recommendation:** file this as a small follow-up (e.g., clear the stored token and force re-enrollment on any `401`/`403` from `/device/v1/display`) — worth doing before the device is ever left unattended for a long stretch where a server-side token invalidation could silently strand it. Not required to close Phase 2. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Plane detection unit suite | `server/.venv/bin/python3 server/test_plane_detection.py` | `plane-detection: 6/6 checks pass` | ✓ PASS |
| Runway-config deadband suite | `server/.venv/bin/python3 server/test_runway_config.py` | `runway-config: 14/14 checks pass` | ✓ PASS |
| Render compositor suite | `server/.venv/bin/python3 server/test_render.py` | `render: 25/25 checks pass` | ✓ PASS |
| Enrichment client suite | `server/.venv/bin/python3 server/test_enrich.py` | `enrich: 16/16 checks pass` | ✓ PASS |
| Full pipeline e2e suite (detect→render→serve→verify) | `server/.venv/bin/python3 server/test_pipeline_e2e.py` | `pipeline-e2e: 5/5 checks pass` (real `byos_server.py` instance exercised) | ✓ PASS |
| Device-protocol contract suite (incl. https scheme) | `server/.venv/bin/python3 stub-server/test_poll_cycle.py` | `poll-cycle: 17/17 checks pass` | ✓ PASS |
| All `server/plane/*.py`, `poll_loop.py`, `panel_format.py` compile cleanly | `python3 -m py_compile ...` | `COMPILE OK` | ✓ PASS |

**Total: 66/66 hermetic automated checks pass, all independently re-run live in this verification (not taken on SUMMARY's word).**

### Human Verification Required

None outstanding. All human-in-the-loop checkpoints this phase required (legibility, edge quality, layout, real-flight cross-check, forced enrichment-fallback) were already executed and resolved within 02-05's own Task 3, with developer sign-off recorded in `02-05-SUMMARY.md`'s "Task 3: On-Glass Verification" section and cross-referenced against server/Caddy logs and firmware source in this verification.

### Gaps Summary

**No blocking gaps. Phase 2's goal is genuinely achieved, and independently re-verified against the live codebase and live server logs, not just SUMMARY claims.** All 66 hermetic automated checks across 6 test suites were re-run live in this session (not merely cited) and pass. All 4 ROADMAP success criteria and all 18 plan-level must-have truths are backed by either a passing re-run test, direct source inspection, or already-completed real-hardware evidence quoted with specifics (server logs, TLS handshake details, exact flight callsigns).

**Two items are explicitly acknowledged and carried forward, not new gaps (per instruction, not re-flagged as blockers):**
1. 02-05 Task 3 Step 2 (raw serial Log Line Contract capture) — not directly captured due to the board's deep-sleep USB power-off behaviour; evidenced indirectly via server request logs instead. Documented honestly in `02-05-SUMMARY.md`.
2. 02-05 Task 3 Step 6 / A-02-02-01 (real runway-3 departure threshold) — explicitly deferred by developer choice; every real detection so far has been an arrival. Carried forward as an open item for Phase 3 (already named in ROADMAP Phase 3's success criterion 3 and STATE.md's Blockers/Concerns).

**One new, non-blocking finding surfaced by this verification** (not previously called out in STATE.md's Blockers/Concerns or any SUMMARY): the firmware never clears a stale/invalid bearer token on a `401`/non-2xx `/device/v1/display` response, so it will retry the same stale token forever without automatic recovery — confirmed by direct code read of `state_machine.c`/`api_client.c`, and consistent with the exact bug 02-05 Task 3 diagnosed and manually worked around live. This does not block Phase 2 (the device is confirmed working correctly against the real server today) and is Phase-1-era firmware behaviour rather than a Phase 2 defect, but it is a real latent robustness gap worth a small follow-up fix before long-term unattended operation. See the Anti-Patterns table above for the specific recommendation.

---

*Verified: 2026-08-26T09:33:32Z*
*Verifier: Claude (gsd-verifier)*
