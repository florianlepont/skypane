---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 04
current_phase_name: ci-cd-documentation-legal-compliance-github-actions-ci-tests
status: executing
stopped_at: 04-02 complete (dev tooling pins + pyproject.toml lint/coverage config + scripts/run-all-tests.sh) - Wave 2 of 4 done, 4 plans remaining
last_updated: "2026-08-26T19:21:41.107Z"
last_activity: 2026-08-26
last_activity_desc: 04-02 executed and verified
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 23
  completed_plans: 17
  percent: 74
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 03 — visual-polish-on-real-glass

## Current Position

Phase: 04 (ci-cd-documentation-legal-compliance-github-actions-ci-tests) — EXECUTING
Plans: 2/6 executed (6 plans, 4 waves - 04-01 through 04-06)
Status: 04-01 (Wave 1) and 04-02 (Wave 2) complete. 04-01: developer selected scrub scope a-b-c (Categories A+B+C) at the checkpoint:decision gate; git-filter-repo rewrote all 154 commits, verified zero occurrences of the approved literals across every ref, backed by a verified bundle outside the repo tree. Repo-root .gitignore (D-06) committed. 04-02: server/requirements-dev.txt pins ruff+coverage (provenance-verified, separate from production deps); repo-root pyproject.toml configures Ruff (E4,E7,E9,F selected, E402 suppressed for 8 documented sys.path bootstraps, green on the untouched codebase) and coverage (server+stub-server scope, parallel mode, fail_under=75 vs a measured 79% baseline); scripts/run-all-tests.sh is the canonical 9-harness runner, gate-failure demonstrated and restored. All 9 test harnesses still pass. Waves 3-4 (04-03 through 04-06) remain.
Last activity: 2026-08-26 — 04-02 executed and verified

Progress: [███░░░░░░░] 33% (Phase 4, 2/6 plans)

## Performance Metrics

**Velocity:**

- Total plans completed: 7
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 7 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P02 | 15min | 3 tasks | 6 files |
| Phase 01 P03 | 25min | 3 tasks | 15 files |
| Phase 01 P05 | 50min | 3 tasks | 22 files |
| Phase 01 P01 | 12min | 2 tasks | 1 files |
| Phase 01 P04 | 25min | 3 tasks | 1 files |
| Phase 02 P01 | 14min | 3 tasks | 21 files |
| Phase 02 P02 | 18min | 3 tasks | 9 files |
| Phase 02 P03 | 40min | 2 tasks | 5 files |
| Phase 02 P04 | 45min | 3 tasks | 3 files |
| Phase 01 P06 | 74min | 3 tasks | 5 files |
| Phase 01 P07 | 136min | 3 tasks | 8 files |
| Phase 01 P08 | 35min | 1 tasks | 5 files |
| Phase 03 P01 | 20min | 2 tasks | 7 files |
| Phase 03 P02 | 30min | 2 tasks | 4 files |
| Phase 03 P03 | 5min | 2 gaps closed (scoped re-entry, not a fresh execution) | 3 files |
| Phase 04 P01 | ~40min | 3 tasks (pre-work + Task 1 + Task 2 decision + Task 3 execution) | 3 files (.gitignore, SCRUB-RECORD.md, 04-01-SUMMARY.md) + history-wide content rewrite across ~154 commits |
| Phase 04 P02 | 5min | 3 tasks | 3 files |

## Accumulated Context

### Roadmap Evolution

- Phase 4 added (2026-08-25), then renumbered to Phase 3 — "Visual Polish on Real Glass": user asked to split Phase 2 into a functional pass and a design-polish pass; since Phase 2 already built up from basic to polished internally across its 5 plans (02-01 bare flight number → 02-04 route/airline captions) and its only remaining plan (02-05) is pure deployment infra with no visual work, the agreed split instead adds a new phase after real hardware exists, dedicated to refining the already-built design against actual Spectra 6 output — closing the hardware-verified-legibility items every Phase 2 SUMMARY.md carried forward rather than guessed at. Old Phase 3 (Low-Battery Indicator) renumbered to Phase 4.
- 01-08 (battery-life measurement, DEVICE-05) moved from Phase 1 to Phase 4 (2026-08-26), becoming 04-01: user wants the unattended multi-day (up to 21-day) discharge run scheduled at the end of the project, once other phases no longer need this Mac to stay awake continuously, rather than mid-Phase-1. Phase 1's goal/success-criteria trimmed to drop the on-battery-viability criterion (now Phase 4's job); Phase 1 is now 7/7 plans executed. Phase 4 renamed "Battery Life & Low-Battery Indicator", gained requirement DEVICE-05 alongside DEVICE-04 and a new success criterion for the measured mAh-per-cycle figure. Task 1 (checker + pre-registered protocol) was already done under the old numbering and carries over unchanged; only the phase/plan numbers and cross-references were updated. REQUIREMENTS.md's DEVICE-05 checkbox corrected from a stale pre-existing `[x] Complete` (predating this move, predating the actual measurement) to `[ ]` — only Task 1 of 3 is done.
- Phase 5 added (2026-08-26): "CI/CD, Documentation & Legal Compliance" — user flagged this as a missing v1 step during Phase 3 work. GitHub Actions CI (tests + build + code-quality/coverage) with automated (gated) deploy to the real OVH VPS, a README, a LICENSE, and documented third-party API terms-of-use compliance (PRIM/IDFM, ADS-B aggregators) plus consolidated asset attribution. Scoped as its own closing phase, orthogonal to the on-device experience Phases 1-4 build — not yet planned (requirements TBD, pending /gsd-discuss-phase 5).
- Phase 4 (Battery Life & Low-Battery Indicator) and Phase 5 (CI/CD, Documentation & Legal Compliance) swapped (2026-08-26, user request): CI/CD is now Phase 4, Battery Life is now Phase 5. Reason: Battery Life's remaining work (05-01 Tasks 2-3) is deliberately parked until the end of the project — it needs an unattended multi-day discharge run — while CI/CD has no such blocker and can run right after Phase 3. All cross-references renumbered: directories (`04-low-battery-indicator` → `05-low-battery-indicator`, `05-ci-cd-...` → `04-ci-cd-...`), plan/summary/context files (`04-01-*` → `05-01-*`, `05-CONTEXT.md`/`05-DISCUSSION-LOG.md` → `04-CONTEXT.md`/`04-DISCUSSION-LOG.md`), threat IDs (`T-04-01-*` → `T-05-01-*`), `ROADMAP.md`'s two phase entries and Depends-on chain (Phase 4 now depends on Phase 3, Phase 5 now depends on Phase 4), and `REQUIREMENTS.md`'s DEVICE-04/DEVICE-05 phase mapping. `DEVICE-05` itself (the requirement ID) was never touched — only phase/plan numbers moved.
- Phase 6 added (2026-08-26, user request): "Final On-Glass Verification". Phase 3's fourth and final plan (03-04, the on-glass verification battery — RGB calibration, PT Serif legibility, bezel clipping, forced departure/arrival, long names, two-flight composition) was moved out of Phase 3 and became this new phase's sole plan, `06-01-PLAN.md`. Reason, in the user's own words: "cause this will be my really last step" — they want one comprehensive real-hardware sign-off at the very end of the whole project (after Phase 4 CI/CD and Phase 5 Battery Life), not a mid-Phase-3 checkpoint. Renumbered: `03-04-PLAN.md` → `06-final-on-glass-verification/06-01-PLAN.md` (frontmatter `phase`/`plan`/`wave`/`depends_on`, threat IDs `T-03-04-*` → `T-06-01-*`, note ID `N-03-04-01` → `N-06-01-01`, output path → `06-01-SUMMARY.md`). Every genuine cross-reference the plan makes to Phase 3's own artifacts (`03-CONTEXT.md`, `03-UI-SPEC.md`, `03-RESEARCH.md`, `03-03-PLAN.md`) was deliberately left unchanged — this plan verifies Phase 3's shipped design, it just runs later in the project timeline now. `total_phases` becomes 7; `total_plans`/`completed_plans` are unaffected since the plan moved, not was added or removed. (Superseded in part by the next two entries.)
- Phase 6 scope widened (2026-08-26, user request): small font/geometry corrections (a font-weight swap to the already-vendored `PTSerif-Bold.ttf`, a point-size tweak within `fit_text_size()`'s floor, a geometry-constant nudge for bezel clearance) are now applied directly in Task 2's on-glass session and re-verified on the glass, not deferred to a hypothetical future phase — "cause this will be my really last step," small tweaks should happen here. `server/plane/render.py`/`server/test_render.py` added to Task 2's `files`. Only a genuine redesign need (new font family, new illustration asset, materially different composition) still gets recorded as a scope question. Task 3's role narrowed to confirming what Task 2 already applied is committed and documented.
- **Correction (2026-08-26, user request):** Phase 3's four on-glass success criteria (silhouette/illustration legibility, caption legibility, visual DEPARTING/ARRIVING distinction, overall composition) were initially left listed in *both* Phase 3 and Phase 6's ROADMAP sections — Phase 3 kept them with a "closed elsewhere" footnote instead of actually relinquishing them. The user caught this: "je suis un peu perturbé... pour moi la phase trois est complète." Fixed by removing all four criteria from Phase 3 entirely (they now live in Phase 6 alone, in full, not by reference) and reducing Phase 3 to a single criterion it can actually verify by itself — the illustration selection/compositing *mechanism* being correct per the automated suite, independent of how it looks on real glass. **Phase 3 is now marked Complete** (3/3 plans, its one remaining criterion satisfied by the shipped, tested code) — `completed_phases` becomes 3. Phase 6's criteria renumbered 1-9 in full (previously criterion 1 was a vague back-reference to "Phase 3's criteria 1-4"; now they're stated as Phase 6's own criteria directly).

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Local ADS-B receiver (geofenced to runway 3) chosen over public flight-data/schedule APIs — validate reception early in Phase 1
- Battery-only power for v1, solar deferred — Phase 1 must produce a real mAh/wake-cycle measurement
- Server on a small always-on cloud VPS, not a home server
- No freshness timestamp / stale-data indicator in v1 (explicit user tradeoff, despite research flagging it as a pitfall)
- [Phase 01]: Vendored byos_server.py byte-for-byte from flightportrait/frame @ ce3335fc, adding only a --state-dir flag so the harness's isolated test tokens never collide with the long-running stub instance the hardware plans keep alive
- [Phase 01]: make_test_panel.py's quadrants pattern splits left/right exactly on a byte-pair boundary (column 600 of 1200) so no byte mixes two colours except the two intentional border-edge bytes
- [Phase 01]: Disabled Bluetooth in firmware/sdkconfig.defaults (only functional delta from upstream) - Phase 1 has no BLE provisioning, hardcoded secrets.h credentials replace it
- [Phase 01]: Containerised build (espressif/idf:v5.3.1), native flash - build.sh runs the whole ESP-IDF toolchain in Docker as the invoking user; USB flashing stays on the host for plan 01-06 because Docker Desktop's macOS USB passthrough is unreliable
- [Phase 01]: Vendored+trimmed api_client.c/wifi.c to the three device endpoints and STA join, reading credentials from a gitignored secrets.h
- [Phase 01]: Trimmed nvs_schema.h from ~30 upstream keys to exactly 4: bearer token, image hash, failure counter, boot counter
- [Phase 01]: Added FP_ERR_HTTP_TRANSPORT/STATUS/JSON/FP_ERR_IMAGE_VERIFY sentinels so state_machine.c can emit the exact Log Line Contract step token
- [Phase 01]: Froze the five-line Log Line Contract in firmware/VENDOR.md for plans 01-06/01-07/01-08 to grep
- [Phase 01]: Hardware orders placed — Seeed EE02 kit (order <seeed-order-ref>) and Kubii battery+cable (order <kubii-order-ref>); Unblock Date 2026-08-26 gates only 01-06/01-07, not 01-05 (already complete)
- [Phase 01]: aggregator-sufficient (2026-08-05): both adsb.fi and airplanes.live cleared the coverage bar over ~92min real traffic (38/37 distinct aircraft <=3000ft, 2/2 on-ground); update-cadence miss (36.2s/22.4s vs 15s) judged immaterial given the device's multi-minute refresh cycle. No RTL-SDR hardware ordered; D-02 fallback not invoked.
- [Phase 01]: airplanes.live preferred as primary aggregator provider (tighter update gap, zero sample errors); adsb.fi retained as secondary given near-total hex overlap.
- [Phase 02]: D-P2-01 multi-aircraft selection rule implemented as (effective_altitude_ft, seen_pos, hex) total order, proven deterministic under shuffled input
- [Phase 02]: poll_loop.py hardcodes state=arriving for every detected flight - deliberate stub, marked in code, 02-02 replaces with real D-03 inference
- [Phase 02]: Deferred marking PLANE-01/02/03 complete in REQUIREMENTS.md - this slice only satisfies detect->render->serve mechanics, not the full requirement text (enrichment is 02-04, real state inference is 02-02, hardware-verified legibility is 02-05)
- [Phase 02]: D-P2-04 deadband (+-200 ft/min) implemented with explicit bool rejection; descent side backed by the real EJU84YF flare fixture, climb side documented as provisional/symmetry-derived per A-02-02-01 (02-RESEARCH.md Open Question 2, closed in 02-05's hardware QA)
- [Phase 02]: A first-ever detection whose vertical rate sits inside the deadband (confirmed_state is None) renders the Empty state rather than guessing a colour
- [Phase 02]: aircraft-silhouette source SVG is detailed 3/4-view line-art (evenodd multi-subpath), not a flat silhouette - cleaned via a from-scratch Pillow dilate/flood-fill/erode pipeline rather than a vector editor — no rsvg-convert/Inkscape/numpy/scipy available in this environment; the flood-fill approach turns any traced line-art into a flat solid mask without hand-editing vector paths
- [Phase 02]: Silhouette sized by fitting within both the 900px width cap and 02-02's existing 260px height cap while preserving the vendored asset's own ~2.22:1 aspect ratio - height cap binds first, leaving 02-02's zone-3 reservation and FLIGHT_NUMBER_TOP_Y untouched
- [Phase 02]: adsbdb.com live-verified at 52.6% real-world hit rate for this airport's traffic mix (worst on low-cost per-tail-rotating callsigns like Transavia's TVF*) - the "Route unavailable" fallback is a designed first-class state (N-02-04-01), not a rare edge case; enrichment cache persists hit *and* miss results in poll_state.json so a rotating callsign is never re-queried
- [Phase 02]: Airline-line Y position computed from fixed font-metric constants only, never from a rendered route line's bbox - guarantees the fallback caption lands at the exact same position as a resolved-route render, no doubled gap
- [Phase 02]: 02-05: deployment target switched from Hetzner CX22 to OVH VPS-1 (same spec, price parity) per explicit user redirect — D-P2-06 explicitly leaves infrastructure specifics to discretion, so treated as a provider substitution, not an architectural change; deploy/ scripts needed zero functional edits since they were already provider-agnostic
- [Phase 02]: 02-05 Task 2 complete: OVH VPS-1 (<public-host>, Ubuntu 26.04) live-provisioned and fully verified - TLS, auth gate, firewall, and real ADS-B pipeline all confirmed against the live host. Fixed 4 live-discovered deploy bugs: sudo-user support, generic python3 packaging, missing adsb-test/runway3.json geofence config, missing Caddy access logging.
- [Phase 02]: 02-05 Task 3 complete (2026-08-26): firmware flashed with the real OVH base URL. Found and fixed a real bug live - the device's NVS partition still held a bearer token from Phase 1 local-stub testing (NVS is untouched by an app-region-only flash), so the first poll against the real server 401'd; fixed by erasing just the NVS region (0x9000/0x6000), forcing re-enrollment. Confirmed end-to-end via server logs (setup 200 -> display 200 -> img 200, hash-matched 960,000 bytes) and developer sign-off on real glass: legibility "clearly legible", edges "hard, flat", layout correct (left-facing arrival, no clipping), real-flight cross-check (DAH1112 from Béjaïa), and a forced enrichment-fallback caption (EJU84YF, via the real render code path) both confirmed. Step 6 (real-departure threshold, A-02-02-01) explicitly deferred by developer choice - every real detection so far has been an arrival; carried forward as an open item for Phase 3. PLANE-01/02/03 now marked complete in REQUIREMENTS.md. Phase 2 closed (5/5 plans).
- [Phase 01]: EE02 board profile verified against real hardware with zero pin/config corrections needed - firmware/sdkconfig.ee02.defaults stays byte-identical to upstream
- [Phase 01]: 'Device appears then disappears on USB' during 01-06 was diagnosed as esp_deep_sleep_start() correctly powering off USB Serial/JTAG outside the RTC domain, not a boot loop/brownout - documented in hardware/BRINGUP-LOG.md
- [Phase 01]: measured panel full-refresh duration ~31.5s (two independent captures) - input for Phase 2 rendering-cadence UX
- [Phase 01]: 01-07 Task 1/2 complete - hardware/logtools.py (stdlib-only stamp/check-backoff/selftest) proven on 3 fixtures before hardware use; real doubling curve (300/600/1200/2400/4800s across backoff_n=0..4) captured on real hardware over an ~80min unattended run and machine-verified. Known low-severity finding: the WiFi SSID leaks into backoff-run.log via ESP-IDF's own wifi component debug line (not the project's Log Line Contract, not the bearer token/password/setup secret) - documented in 01-07-SUMMARY.md, not yet fixed (would need a reflash+recapture).
- [Phase 01]: 01-07 Task 3 (power-cycle persistence proof) deliberately deferred overnight at explicit user request - device left connected (USB) with battery still disconnected, holding backoff_n=5 in NVS; stub server left stopped (Task 3 needs it down through its own step 6); capture loop + caffeinate stopped so the Mac can sleep normally.
- [Phase 01]: 01-07 Task 3 complete: NVS failure counter proven to survive three real physical power cycles (no battery) - backoff_n continued 7->8 across a power-cycle where the wall-clock gap (12m37s vs a 6h/21600s armed sleep) makes an external interruption mathematically certain; recovery poll + follow-up failure proved a success resets to backoff_n=0/sleep_s=300. The literal 'wake reason=power-on' console line could not be captured on any of 3 cold power-ons (diagnosed via macOS kernel USB log as a genuine USB re-enumeration delay on this board's marginal connection, not a capture-script bug or firmware defect); corroborated instead via the device's own X-Boot-Reason=power-on HTTP telemetry header. Full diagnosis in hardware/BACKOFF-OBSERVATION.md. DEVICE-03 marked complete.
- [Phase 05]: 05-01 Task 1 (formerly 01-08, moved 2026-08-26): check-battery checker + BATTERY-RUN.md protocol pre-registered (thresholds, 21-day ceiling, 3000mAh capacity from BOM.md) before the battery pack was connected - proven on 3 new fixtures (battery-good accepted; battery-gap/battery-flat-mv rejected). Tasks 2 (multi-day unattended run) and 3 (post-mortem verdict) remain, deliberately deferred to end of project.
- [Phase 03]: 03-01 complete - Zilla Slab vendored from pinned google/fonts commit f473a26ceba660d85cf223ff121dea1fe91cfcb6 (SIL OFL 1.1), Inter fully retired from the active render path, D-16 co-equal hero pair (72px Bold flight number / 64px SemiBold destination, 8px gap) implemented, D-13 interim panel-RGB triples applied to PALETTE_RGB with zero index/nibble drift
- [Phase 03]: 03-02 mood background rejected the UI-SPEC's full-6-color-palette recipe after measuring it produced six-colour static for the arriving mood; replaced with a two-entry [White, state_base_rgb] sub-palette (hue-pure by construction), MOOD_LIGHT_TINT_MIX finalized at 0.40, measured 80.3% state-hue / 19.7% White per state
- [Phase 03]: 03-02 replaced the naive per-pixel jitter loop (measured 3.7s, would have blown the render-time budget) with bulk Random.randbytes() + row-scoped bytes.translate() LUTs, ~35x faster (~100ms), still fully deterministic from the same seeded local Random instance
- [Phase 03]: 03-02 replaced the whole-canvas 'exactly 2 palette indices' guard rail with a spatially-scoped _assert_palette_contract() (per-quiet-zone + illustration-bbox-aware whole-canvas check), with the illustration_bbox hook already wired for 03-03
- [Phase 04]: 04-01 Task 2 checkpoint:decision - developer selected scrub scope a-b-c (Categories A+B+C in full) over a-only or a-b, removing the home Wi-Fi SSID/BSSID/device MAC and home street address alongside the D-05-locked VPS IP/hostname, before the one-way git-filter-repo rewrite ran
- [Phase 04]: 04-01 Task 3 - git-filter-repo rewrote all 154 commits (--replace-text + --replace-message, since one literal only appeared in a commit message) in a scratch clone, re-homed onto main, verified zero occurrences of any approved literal across every ref; a verified git bundle backup exists outside the repo tree as the rollback path. Also deleted the stale, fully-redundant `claude/faience-blanche-mate-434eeb` branch ref (the removed 01-worktree's branch) which would otherwise have kept pre-rewrite objects reachable.
- [Phase 04]: 04-01 repo-root .gitignore committed (D-06), extending the five existing per-subdirectory ignore files without weakening any of them; nested worktree removed and working tree cleaned ahead of the history rewrite (F4/F5)
- [Phase 04]: 04-02 complete - Ruff restricted to E4,E7,E9,F (E402 suppressed for 8 documented sys.path bootstraps); coverage scoped to server+stub-server, parallel mode, fail_under=75 (4pts below measured 79% baseline); scripts/run-all-tests.sh is the canonical 9-harness runner for CI (04-04) and README (04-05), gate-failure demonstrated and restored

### Pending Todos

None yet.

### Blockers/Concerns

- Research flagged as unverified before commit: exact AeroDataBox tier/cost is not needed (project uses local ADS-B, not AeroDataBox, per PROJECT.md's reversed decision) — but PRIM/IDFM's exact SIRI Lite quota figures are community-sourced only; not a v1 blocker (RER deferred to v2 as of 2026-08-11) — verify against the live account dashboard before finalizing RER poll cadence when v2 planning starts.
- Spectra 6 dual-chip display driver — RESOLVED 2026-08-25 (01-06): EE02 board profile verified against real hardware with zero corrections needed, first light achieved (all 5 visual checks passed), Log Line Contract captured live.
- No publicly confirmed enclosure design exists for the EE02 kit — budget design time in Phase 1 or plan around an off-the-shelf enclosure.
- Battery-life real-world figure for this exact hardware combo is unmeasured — 05-01's Task 1 (check-battery checker + pre-registered protocol) is done; Tasks 2 (multi-day unattended discharge run, needs the Mac to stay awake continuously) and 3 (post-mortem readout) are deliberately deferred to the end of the project (user decision, 2026-08-26) rather than done now.
- Device wake interval (`sleep_s`, how often the physical frame polls the server) is currently **30s** on the live OVH deployment (`inkframe.env`'s `INK_SLEEP_S=30`, verified directly on the VPS 2026-08-26 — same cadence as the server's own ADS-B poll timer, not yet distinguished) — NOT yet a tuned production value, this is the bring-up/test default. Real tradeoff: shorter interval = fresher plane-departure info but faster battery drain; longer = more autonomy but a departure could be several minutes stale by the time it's shown. Decision deliberately deferred until Phase 5's 05-01 produces a real mAh-per-cycle figure — tune this once actual battery-life data exists, not before.
- A-02-02-01 (departure-side D-03 threshold, +200 ft/min) has never been observed against a real runway-3 departure — every real detection so far (Phase 1's sample and 02-05 Task 3's on-glass check) has been an arrival. Not a known defect, just unvalidated. Scoped to close in Phase 3 (success criterion 3 already names it); check `journalctl -u inkframe-poll` on the VPS for `confirmed_state=departing` whenever it's convenient before or during Phase 3 planning.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260826-p7a | Reconcile Phase 3 planning docs (03-UI-SPEC.md, 03-RESEARCH.md, 03-03/03-04-PLAN.md) with the two-flight poster layout actually implemented and committed (D-21/D-24/D-25/D-26/D-27) | 2026-08-26 | 9bce44e | [260826-p7a-reconcile-phase-3-planning-docs-03-ui-sp](./quick/260826-p7a-reconcile-phase-3-planning-docs-03-ui-sp/) |

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — first milestone)* | | | |

## Session Continuity

Last session: 2026-08-26T19:21:41.107Z
Stopped at: 04-02 complete (Wave 2 of 4) - dev tooling pins, pyproject.toml lint/coverage config, scripts/run-all-tests.sh all verified; Waves 3-4 (04-03 through 04-06) remain

Resume file: None - proceed to /gsd-execute-phase 4 for the remaining waves

**State at end of this session (2026-08-26, ~09:25):**

- Device: flashed with production firmware pointed at the real OVH server, running on battery power (JST connector repinned and verified against the board's silkscreen `+` marking earlier this session — correct polarity confirmed before connecting). Currently on its normal wake/poll/sleep cycle against the live deployment.
- Phase 2 fully closed: all 5 plans complete, ROADMAP success criterion 4 satisfied, PLANE-01/02/03 marked complete in REQUIREMENTS.md.
- The OVH VPS's `inkframe-poll.timer` is running normally (restarted after the Task 3 forced-fallback test); live ADS-B detection has resumed.
- Open item carried into Phase 3: A-02-02-01's real-departure threshold has never been observed (see Blockers/Concerns above).
- Prior-session battery-measurement context (`hardware/logtools.py check-battery`, `hardware/BATTERY-RUN.md`'s pre-registered protocol) is unchanged and still deliberately deferred to end-of-project per Phase 5's scope note — Tasks 2/3 of 05-01 not started.
- Next step: `/gsd-plan-phase 3` to plan Visual Polish on Real Glass.

**State at end of this session (2026-08-26, ~19:10) — supersedes the note above:**

- 04-01 complete: repo-root `.gitignore` (D-06), nested worktree removed, and a full git-filter-repo history scrub verified clean (zero occurrences of the VPS IP/hostname, home Wi-Fi SSID/BSSID/device MAC, and home street address across all 154 commits and every ref). All 9 test harnesses still pass. `SCRUB-RECORD.md` and `04-01-SUMMARY.md` document the operation without restating any scrubbed value.
- Every commit hash in this repo changed as a result of the rewrite (content unchanged, hashes rewritten) — any hash recorded before this session in a SUMMARY or elsewhere is now stale.
- A verified pre-rewrite backup bundle exists outside the repo tree; its path is recorded in `SCRUB-RECORD.md` (not restated here per the no-literal-restatement rule, though it is not itself one of the scrubbed literals).
- Next step: continue `/gsd-execute-phase 4` for Waves 2-4 (04-02 through 04-06).

**State at end of this session (2026-08-26, ~19:22) — supersedes the note above:**

- 04-02 complete (Wave 2): `server/requirements-dev.txt` pins `ruff==0.16.4`/`coverage==7.15.4` (provenance-verified against upstream, separate from `server/requirements.txt` so `deploy/deploy.sh` never installs them on the VPS). Repo-root `pyproject.toml` configures Ruff (`E4,E7,E9,F` selected, `E402` ignored repo-wide for 8 documented sys.path bootstrap blocks, zero findings on the untouched codebase) and coverage (`server`+`stub-server` scope, parallel mode, `fail_under=75` derived from a measured 79% production-only baseline). `scripts/run-all-tests.sh` runs all 9 harnesses, combines coverage, and enforces the threshold — demonstrated to fail when the threshold was temporarily raised to 100, then restored byte-identical. All 9 harnesses (117 checks) still pass; `git status` clean after every run.
- Progress counters corrected in this session's STATE.md update: `state.update-progress` (SDK verb) miscounted `completed_plans` as 18 by treating `05-01-SUMMARY.md` (status: in-progress, only Task 1/3 done) as a completed plan, and separately bumped `completed_phases` to 4 incorrectly. Corrected by hand to `completed_phases: 3`, `completed_plans: 17` (7+5+3+2), `percent: 74` — matches the known SDK progress-counter bug already on file in project memory.
- Next step: continue `/gsd-execute-phase 4` for Waves 3-4 (04-03 through 04-06).
