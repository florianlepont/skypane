# Roadmap: SkyPane

## Overview

SkyPane v1 ships as a single-view device in four phases. Phase 1 is a foundation spike that de-risks the thing everything else depends on — real ADS-B reception at the install address — by proving the core device protocol loop (including exponential backoff and NVS persistence) against a stub server. Phase 2 then delivers the first complete, user-visible capability: the plane view, wired end-to-end from ADS-B detection through server rendering to the physical display, built and verified against digital previews since real hardware isn't flashed yet. Phase 3 revisits that same visual design once real hardware exists — refining it against actual Spectra 6 E-ink output rather than a monitor preview. Phase 4 closes out v1 by measuring real on-battery wake/poll/sleep viability (an unattended multi-day discharge run, deliberately scheduled for the end of the project) and building the low-battery indicator that figure informs, completing the device experience.

**v2 scope note**: The RER view (originally Phase 3) and the physical-button view-switching work (originally part of Phase 4, requirements DEVICE-01/DEVICE-02) were deferred out of v1 — v1 ships as a single-view (plane-only) device. See git history for the removed Phase 3 (RER View — End-to-End Slice) content; it and the switching work are v2 candidates once a second view exists to switch to.

**Phase 5 note**: Added 2026-08-26 as a closing, project-hygiene phase — CI/CD, README, LICENSE, and third-party API compliance — orthogonal to the on-device single-view experience Phases 1-4 build.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation — Hardware Bring-up & ADS-B Validation** - Validate ADS-B reception on real hardware, with the core wake/poll/backoff loop proven against a stub server (completed 2026-08-26)
- [x] **Phase 2: Plane View — End-to-End Slice** - First complete vertical slice: real runway-3 plane data flowing from ADS-B detection through server rendering to the physical display (completed 2026-08-26)
- [x] **Phase 3: Visual Polish on Real Glass** - Refine the plane view's visual design against real Spectra 6 E-ink output, resolving legibility/balance items that a digital preview can't settle (completed 2026-08-26 — on-glass visual sign-off moved to Phase 7, not a blocker on this phase)
- [x] **Phase 3.1: Procedural Per-Airline Livery Rendering** (INSERTED) - Extends Phase 3's externally generated illustration set to real per-flight aircraft-type accuracy, by (a) surfacing the ADS-B ICAO type designator in `server/plane/detect.py`, (b) adding a second selection key plus a four-tier fallback in `server/plane/illustrations.py`, and (c) expanding the externally generated asset set per D-03's verified 24-airline / 7-base-shape table (completed 2026-08-27)
- [x] **Phase 4: CI/CD, Documentation & Legal Compliance** - GitHub Actions CI (tests, build, code quality, coverage) with automated deploy to the OVH VPS, a project README, a code LICENSE, third-party API terms-of-use compliance documentation, and consolidated asset attribution (completed 2026-08-26 — repo public at github.com/florianlepont/skypane, CI-block and deploy-gate proven on real infrastructure)
- [ ] **Phase 5: Battery Life & Low-Battery Indicator** - Measure real on-battery wake/poll/sleep viability via an unattended multi-day discharge run, then build the low-battery warning it informs, completing the v1 single-view device experience (05-02/05-03 complete 2026-08-27, DEVICE-04 fully closed and confirmed on real glass; 05-01's actual multi-day discharge run — success criterion 1, DEVICE-05 — still deliberately deferred to end of project)
- [x] **Phase 6: Companion Configuration Web Interface** - A password-protected web page (theme picker, runway selection, health/history, airline-coverage monitoring, flight log, manual poll trigger, render preview/gallery) covering CFG-01, CFG-03..12, promoted from the v2 backlog (12/12 plans complete — developer sign-off checkpoint passed 2026-08-28, two real defects found live and fixed: a poll-trigger crash and mobile table cropping) (completed 2026-08-28)
- [x] **Phase 6.1: Battery status on companion web interface** (INSERTED) - SUPERSEDED 2026-08-28, before planning — merged into Phase 6.5 (identical target: health_page.py's Battery Trend section). Never planned standalone; see Phase 6.5.
- [x] **Phase 6.2: LED enable/disable toggle** (INSERTED) - Allow the board's LEDs to be enabled/disabled from the companion interface (completed 2026-08-28).
- [x] **Phase 6.3: Companion UI visual design & desktop layout pass** (INSERTED) - More visual personality, a true desktop dashboard layout (sidebar nav + multi-column stat tiles), and History's missing mobile table-crop fix. Planned: 5 plans across 3 waves. (completed 2026-08-28)
- [x] **Phase 6.4: Runway picker — show runway number + airport map** (INSERTED) - Clearer runway numbering plus a small airport diagram on the Config page. Planned 2026-08-28 (1 plan). (completed 2026-08-28)
- [x] **Phase 6.5: Interactive battery trend chart with overall status** (INSERTED) - Replace the static sparkline with an interactive chart and an at-a-glance status indicator. 3 plans across 3 waves. (completed 2026-08-29)
- [x] **Phase 6.6: Companion UI clarity pass** (INSERTED) - Human-readable timestamps, a live poll-trigger cooldown countdown, and a verified/pinned corroboration-copy drift guard. Planned 2026-08-28 (3 plans across 2 waves). (completed 2026-08-30)
- [x] **Phase 6.6.1: Companion visual polish pass** (INSERTED) - Second visual-design pass on the companion app: serif headings and a crafted wordmark, a terracotta accent, card relief, airier spacing, a real mobile hamburger nav replacing the horizontal-scroll strip, Health density/redundancy cleanup with per-signal icons and a nav notification dot, a full-width battery chart, and History cut 9 columns to 7. Planned 2026-08-29 (6 plans across 4 waves). All 6 plans executed 2026-08-30; the blocking real-phone sign-off (plan 06) found 2 confirmed, root-caused CSS defects (`.mobile-nav`'s `position:absolute` prevented the push-down behavior D-06 requires; `.stat-tile svg`'s `width:100%` rule unintentionally stretched the new icon SVGs) — see `06.6.1-06-SUMMARY.md`. Both fixed directly (developer chose a quick fix over formal gap-closure planning, since both root causes were already precisely identified), re-verified live in-browser and by `gsd-verifier` (46/46 must-haves, `06.6.1-VERIFICATION.md`). (completed 2026-08-30)
- [x] **Phase 7: Final On-Glass Verification** - The project's true last step: one real-hardware sign-off pass (PT Serif legibility, bezel clipping, forced departing/arriving renders, long-name stress test, two-flight composition, final Yellow/Red panel calibration) done once everything else is finished (renumbered from Phase 6 when the companion interface was promoted from the v2 backlog) (completed 2026-08-28)
- [x] **Phase 8: Panel theme rework** - White default theme + Black/Yellow/Red/Blue/Green as optional CFG-01 themes, PT Serif Bold replaces the text backing-plate, `adsbdb` `callsign_iata` threaded through so the raw ADS-B callsign never displays, previous-card text sizing/alignment fix, and a required on-glass verification pass — implements spike `.planning/spikes/001-panel-theme-colours/`. Planned 2026-08-31: 6 plans across 5 waves (0/6 executed). (completed 2026-08-31)
- [x] **Phase 9: Diagonal band theme** - A new dedicated theme (additive to Phase 8's 11) adding a diagonal decorative trapezoid band behind the aircraft illustration in 5 colours (blue/blue-light-dithered/green-light-dithered/red/black), a split top-label tag, a three-tier flight-identifier hierarchy centred inside the band for both the main and previous cards, band-aware ink colour, and a required on-glass verification pass — implements spike `.planning/spikes/003-diagonal-band-theme/`. Planned 2026-09-02: 4 plans across 4 waves (0/4 executed). (completed 2026-09-02)
- [x] **Phase 10: Scheduled quiet hours** - Pause the frame's wake/poll/display cycle during a configurable window (curfew), via a server-side skip of the display refresh — promoted from `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md` at the developer's request (2026-09-02). Not yet planned. (completed 2026-09-03)
- [x] **Phase 11: Web-configurable wake interval** - Make `SKYPANE_SLEEP_S` configurable through the companion web interface instead of SSH-only env-file edits — promoted from `.planning/seeds/SEED-002-web-configurable-wake-interval.md` at the developer's request (2026-09-02). Planned 2026-09-04: 4 plans across 3 waves (3/4 executed). (completed 2026-09-04)

## Phase Details

### Phase 1: Foundation — Hardware Bring-up & ADS-B Validation

**Goal**: The highest-risk technical unknown — ADS-B reception at the install site — is validated on real hardware, with the core device protocol loop (wake, poll, download, display, deep sleep, backoff) working end-to-end against a stub server and proven byte-for-byte, including exponential backoff and NVS persistence across a full power loss. This is a foundation/spike phase: it de-risks Phases 2-4 rather than shipping a user-facing view.

**Note on scope (2026-08-26)**: Real on-battery wake/poll/sleep viability — originally this phase's second named risk, with its own success criterion and a DEVICE-05 plan (01-08) — was moved to Phase 4 at the user's request, to run the unattended multi-day discharge test at the end of the project rather than mid-Phase-1. See STATE.md's Roadmap Evolution note.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: DEVICE-03
**Success Criteria** (what must be TRUE):

  1. Device completes a full wake → HTTPS poll → download → display → deep-sleep cycle against a stub server, repeatably and without manual intervention.
  2. When the stub server is unreachable, the device backs off exponentially instead of retrying at a fixed interval, matching the flightportrait reference model.
  3. Free public ADS-B aggregator APIs (airplanes.live primary, adsb.fi secondary), geofenced to the install address (<street-address>), reliably detect real aircraft transiting runway 3's flight path — validated over ~92min of real traffic (38/37 distinct aircraft, 2/2 on-ground) against the coverage bar, with no RTL-SDR hardware needed. This validates the groundwork for PLANE-03, fully delivered in Phase 2.

**Plans**: 7/7 plans executed

- [x] 01-01-PLAN.md
- [x] 01-02-PLAN.md
- [x] 01-03-PLAN.md
- [x] 01-04-PLAN.md
- [x] 01-05-PLAN.md
- [x] 01-06-PLAN.md
- [x] 01-07-PLAN.md

### Phase 2: Plane View — End-to-End Slice

**Goal**: A user can glance at the frame and see live runway-3 plane data — the first complete vertical slice, wired end-to-end from ADS-B detection through server rendering to the physical display.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: PLANE-01, PLANE-02, PLANE-03
**Success Criteria** (what must be TRUE):

  1. User can see flight number, airline, and destination for the next plane departing Orly runway 3, rendered on the physical frame.
  2. When runway 3 is in arrival configuration, user instead sees flight number, airline, and origin for the next landing plane.
  3. As real aircraft use runway 3, the plane view updates to reflect the new flight as detected by the local ADS-B receiver — not a fixed schedule.
  4. The full pipeline (ADS-B detection → server render → device poll → display) runs end-to-end on real hardware, replacing the Phase 1 stub server.

**Note on criterion 3's wording**: corrected 2026-08-26 at Phase 1 close (was stale, said "local ADS-B receiver / RTL-SDR"; see 02-CONTEXT.md D-01 and PROJECT.md/REQUIREMENTS.md, corrected the same day).

**Plans**: 5/5 plans executed
**Wave 1**

- [x] 02-01-PLAN.md — Slice 1: live runway-3 flight number reaches the panel (detection, selection rule, minimal render, poll loop)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Slice 2: departing vs. arriving (D-03 deadband inference, full-bleed state colour, state label)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Slice 3: aircraft silhouette centrepiece (vendored CC0 asset, hard-edged compositing, state mirroring)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-04-PLAN.md — Slice 4: airline and route captions (adsbdb enrichment, persistent cache, "Route unavailable" fallback)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 02-05-PLAN.md — Slice 5: real HTTPS deployment (scheme fix, OVH VPS-1 + Caddy + systemd, on-glass verification)

**UI hint**: yes

### Phase 3: Visual Polish on Real Glass

**Goal**: The plane view's visual design is refined against real Spectra 6 E-ink output, not a rendered-PNG preview — closing out the hardware-verified-legibility items that every Phase 2 plan explicitly carried forward rather than guessed at, and replacing the generic flat-fill aircraft silhouette with a richer, per-airline generated illustration now that dithered/photographic rendering is confirmed viable on this exact panel (see Note on scope below).

**Note on scope (2026-08-26, discuss-phase):** Widened during `/gsd-discuss-phase 3` from a pure hardware-verification pass into also including a real visual upgrade to the aircraft artwork. The user confirmed via SenseCraft (Seeed's official companion app) that this panel renders dithered/photographic content well — the flat, no-dither rendering rule from 02-UI-SPEC.md Revision 2 was a deliberate Phase 2 style choice, not a hardware limit. This unlocks a per-airline illustration approach that was explicitly rejected in Phase 2 (D-02/02-UI-SPEC.md) only because no CC0/licensable per-airline livery art existed — the user will generate the illustrations themselves (AI image generation), sidestepping that licensing constraint. A personal photo as the panel's *background* was discussed and explicitly deferred to v2 (see REQUIREMENTS.md v2 backlog) — this phase's scope is the aircraft illustration only, not the background.

**Note on the on-glass verification plan (2026-08-26, renumbered 2026-08-27):** This phase's original fourth plan (03-04, the on-glass verification battery) was moved to **Phase 7: Final On-Glass Verification** (now `07-01-PLAN.md`; briefly Phase 6/`06-01-PLAN.md` between 2026-08-26 and 2026-08-27, see that phase's own numbering note) at the user's explicit request — they want one final real-hardware sign-off at the very end of the whole project, after CI/CD and Battery Life are also done, rather than a mid-project on-glass pass. **The four on-glass success criteria that used to live here (silhouette/illustration legibility, caption legibility, the visual DEPARTING state, and overall composition) moved with it — they are not duplicated below.** They are now Phase 7's own criteria in full (see that phase's section) — this phase's remaining criterion is the one thing that's genuinely code-verifiable without the physical device.

**Mode:** mvp
**Depends on**: Phase 1 (hardware flashed via 01-06/01-07) and Phase 2 (deployed via 02-05)
**Requirements**: PLANE-01, PLANE-02 (hardware-verified legibility closure — now Phase 7's job — and a richer visual treatment of the "airline" element both requirements already call for)
**Success Criteria** (what must be TRUE):

  1. Each detected flight renders a dithered, per-airline-generated aircraft illustration (not a flat-White CC0 silhouette) for airlines covered by the generated set, with a single dithered generic illustration as the fallback for uncovered airlines and the "Route unavailable" enrichment-failure state, never mirrored by state (D-24) — the selection and compositing mechanism itself, independent of how it looks on real glass, which is Phase 7's job. Verified by the automated suite (`server/test_illustrations.py`, `server/test_render.py`), not by eye.

**Plans**: 4/4 plans complete

Plans:
**Wave 1**

- [x] 03-01-PLAN.md — Serif typography (Zilla Slab) and the co-equal flight-number/destination hierarchy, plus D-13's interim panel RGB values

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03-02-PLAN.md — Dithered two-tone mood background per state, with flat quiet-zone plates behind every caption and a spatially-scoped palette contract

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03-03-PLAN.md — Per-airline dithered livery illustrations with a dithered generic fallback, gated on the developer's illustration hand-off

**Gap closure** *(added 2026-08-27 from `03-VERIFICATION.md`; independent of the three waves above, which are complete)*

- [x] 03-04-PLAN.md — Guard the live render path against a corrupt or oversized illustration file: a never-raises loader that degrades to `generic-fallback.png` at both D-25/D-26 call sites, plus a header-only `ILLUSTRATION_MAX_PIXELS` pre-check and three regression checks

**UI hint**: yes

### Phase 03.1: Procedural Per-Airline Livery Rendering (INSERTED)

**Goal:** Each detected flight's illustration and its `{airline} · {type}` caption reflect that flight's real ICAO aircraft type as reported by the ADS-B aggregator, selected from an expanded set of externally generated static illustrations through a four-tier fallback (exact airline+shape, airline-only, neutral-shape, universal fallback), degrading gracefully at every tier.

**Note on origin (2026-08-26):** Raised by the user during Phase 3's discuss/plan work as an alternative architecture to D-09's static-file hand-off (SVG template + programmatic per-airline color overlay, computed server-side at render time, instead of one pre-generated raster image per airline). Deliberately deferred out of Phase 3 rather than decided inline, because it depends on an unverified prerequisite — whether real ADS-B aircraft-type data (the `t`/ICAO-type-designator field, standard in the readsb/tar1090 JSON schema both `airplanes.live` and `adsb.fi` are built on, per `03-RESEARCH.md`) is actually present in this project's live aggregator responses; this project's own `server/plane/detect.py` does not currently extract it, and a live check could not be completed from the development sandbox (network-restricted). Confirming this from a real network connection is this phase's first task before any rendering work.

**Superseding note (2026-08-27, discuss-phase):** The discuss-phase investigation (`03.1-CONTEXT.md` D-02) found no free, license-compatible, correctly-oriented per-type source art (side-profile SVG/line-art shapes) — every real candidate source was either non-redistributable, wrong-angle (top-down plan view), wrong format with unverified per-file licensing, or lacked per-type differentiation. The render-time SVG-shape + livery-color-compositing architecture described above is therefore **shelved, not rejected in principle** — see `03.1-CONTEXT.md`'s Deferred section for the revisit condition (better-licensed source art, or a decision to commission/draw original shape templates). The prerequisite this note originally called unverified is now confirmed (D-01: the `t` field is genuinely present on real in-flight aircraft, re-confirmed live again in `03.1-LIVE-RESOLUTION.md`). The goal and success criterion 3 above were revised accordingly under D-10, to describe the static-but-type-accurate approach actually being built: an expanded set of externally AI-generated static illustrations (same D-09 hand-off discipline as Phase 3), selected via a new two-key (airline + aircraft-type) lookup with a four-tier fallback, rather than a server-side compositing engine.

**Depends on:** Phase 3 (its static-file approach and illustration-zone rendering path, which this phase replaces) and a confirmed source of real aircraft-type data

**Requirements**: PLANE-01, PLANE-02 (same "airline" element both requirements already call for, now at real per-flight type accuracy rather than Phase 3's representative-type approximation)

**Success Criteria** (what must be TRUE):

  1. Real aircraft-type data (ICAO type designator) is confirmed available and reliably present in this project's live ADS-B aggregator responses — or, if genuinely unavailable, this phase is descoped/re-planned around that finding rather than proceeding on an unverified assumption.
  2. `server/plane/detect.py` extracts and surfaces the aircraft-type field alongside the existing callsign/altitude/vertical-rate fields already captured.
  3. An externally generated static illustration is selected for the actual detected flight keyed on both the resolved `airline_name` and the classified aircraft-type shape bucket, through D-06/D-07/D-08's four fallback tiers (exact airline+shape match, known-airline-any-shape, unknown-airline-known-shape neutral fallback, universal fallback) — verified by `server/test_illustrations.py` and `server/test_render.py`, not by eye.
  4. The full automated test suite (`scripts/run-all-tests.sh`) stays green and `server/plane/illustrations.py --validate` passes for every delivered asset. (On-glass legibility sign-off is deliberately **Phase 7's** criterion, not this phase's — Phase 7 already owns the project's single real-hardware verification pass, the same precedent STATE.md records for Phase 3's own on-glass criteria.)
  5. Coverage gracefully degrades (a sensible fallback, not a crash or a blank illustration) for any airline/type combination not yet defined in the livery/shape mapping — mirroring D-08's existing generic-fallback discipline from Phase 3.

**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 03.1-01-PLAN.md — ROADMAP D-10 revision pass, plus the live-verified record of every target airline's exact resolved name and the `t` field's presence on both aggregator providers
- [x] 03.1-02-PLAN.md — `detect.py` extracts and normalises the ICAO aircraft-type designator, with fixture and harness coverage for the present, absent and malformed cases

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 03.1-03-PLAN.md — `classify_aircraft_type()` plus the four-tier (D-06/D-07/D-08) two-key `select_illustration()`, and the enumerable D-03 target file set

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 03.1-04-PLAN.md — `{airline} · {type}` line-2 rendering with friendly labels and a presentation-only brand alias, both illustration call sites threaded, type visible in the poll log
- [x] 03.1-05-PLAN.md — expanded illustration hand-off spec, the developer's blocking art-generation gate, and digest-backed provenance for everything delivered

### Phase 4: CI/CD, Documentation & Legal Compliance

**Note on scope (2026-08-26)**: Raised by the user as a missing v1 step — the project has shipped real, working code (Phases 1-3) with no CI, no README, no LICENSE, and no documented compliance check against the third-party APIs it depends on (AeroDataBox — unused per PROJECT.md's reversed decision, PRIM/IDFM, adsb.fi/airplanes.live). Scoped as its own phase rather than folded into Battery Life, since it's project-hygiene/shippability work orthogonal to the on-device experience Phases 1-3 & 5 build. **Ordered ahead of Battery Life (2026-08-26, user request)**: Battery Life's own remaining work is deliberately parked until the end of the project (its multi-day discharge run needs this Mac to stay awake continuously), so there is no reason for this phase — which has no such blocker — to wait behind it.

**Goal:** GitHub Actions runs the full test suite (server/test_*.py) and code-quality/coverage checks on every push/PR, with an automated (gated, not silently-triggered) deploy step pushing to the real OVH VPS on merge to main; the repository has a README a newcomer can build/deploy from, a LICENSE, and documented confirmation that PRIM/IDFM's and the ADS-B aggregators' terms of use are actually being honored (no raw-data republishing, rate-limit compliance, attribution where required); asset attribution (fonts, icons, illustrations) is consolidated and verifiably complete via the existing VENDOR.md files.
**Requirements**: D-01 through D-16 (this phase has no PLANE-*/DEVICE-* IDs of its own — it is infra/documentation work. The discuss-phase resolved its requirements into the locked decisions D-01..D-16 in `04-CONTEXT.md`, which are the traceability anchor each plan's `requirements` frontmatter cites, per `04-VALIDATION.md`'s Phase Requirement Map.)
**Depends on:** Phase 3
**Plans**: 6/6 plans executed — **phase complete**. Repository is live and public: https://github.com/florianlepont/skypane

Plans:
**Wave 1**

- [x] 04-01-PLAN.md — Pre-publish repo hygiene: root `.gitignore`, a gated scrub-scope decision, and the `git filter-repo` history rewrite (D-03/D-04/D-05/D-06)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 04-02-PLAN.md — Quality baseline: pinned dev tooling, a measured lint ruleset and coverage threshold, and one aggregate 9-harness runner (D-07/D-08/D-09)
- [x] 04-03-PLAN.md — Legal: MIT LICENSE, COMPLIANCE.md for all five data sources, and a machine-checked asset-attribution audit (D-13/D-14)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 04-04-PLAN.md — GitHub Actions: blocking CI, an environment-gated deploy wrapping `deploy.sh`, and a path-restricted firmware build (D-07/D-08/D-09/D-10/D-11/D-12)
- [x] 04-05-PLAN.md — Documentation: root README a newcomer can build from, a current-state ARCHITECTURE.md, and the visible adsb.fi attribution (D-14/D-15/D-16)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 04-06-PLAN.md — Go public: create the repo, provision a dedicated deploy key and the approval gate, push, and prove CI blocks and the deploy gate holds (D-01/D-02/D-05/D-09/D-11/D-12) — includes an unplanned second `git filter-repo` pass (supplier order numbers found during the pre-publish review) and a real gate defect found and fixed live (`can_admins_bypass` silently skipped the required-reviewer pause for repo admins)

### Phase 5: Battery Life & Low-Battery Indicator

**Goal**: Real on-battery wake/poll/sleep viability is measured on real hardware (not estimated), producing a mAh-per-cycle figure a wake-interval and battery-life plan can be built on; users can then see a clear low-battery warning on the frame — completing the v1 device experience for the single-view (plane-only) device.

**Note on scope (2026-08-26)**: The battery-measurement plan (05-01, formerly Phase 1's 01-08) was moved here at the user's request — the unattended multi-day (up to 21-day) discharge run is deliberately scheduled for the end of the project, once other phases no longer need this Mac to stay awake continuously. Task 1 (pre-registered protocol + `check-battery` checker, proven on fixtures) is already complete; Tasks 2-3 (the actual run and its verdict) remain. **Renumbered from Phase 4 to Phase 5 (2026-08-26, user request)** to run after CI/CD, Documentation & Legal Compliance instead of before it — see that phase's note.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: DEVICE-04, DEVICE-05
**Success Criteria** (what must be TRUE):

  1. The device completes multiple wake/poll/sleep cycles running on battery power alone, producing a measured mAh-per-cycle figure — not an estimate — that supports a realistic wake-interval and battery-life plan.
  2. User can see a low-battery indicator on the frame when the battery is running low.

**Plans**: 3/3 plans executed, but the phase is NOT complete — 05-01's Tasks 2-3 (success criterion 1, DEVICE-05) are deliberately parked until the end of the project; only DEVICE-04 (criterion 2, 05-02+05-03) is actually closed.
**Wave 1**

- [ ] 05-01-PLAN.md — Battery-life measurement: pre-registered D-07 protocol + check-battery checker (Task 1 done), unattended multi-day discharge run and verdict (Tasks 2-3 pending, deliberately deferred)
- [x] 05-02-PLAN.md — Low-battery indicator, server half: strict X-Battery-Mv validation and single-writer persistence, the 3500/3600 mV hysteresis decision, and the bottom-left battery icon drawn onto the served panel

**Wave 2**

- [x] 05-03-PLAN.md — Low-battery indicator, device half: host-tested divider conversion, a real calibrated ADC1 read off the EE02 board's existing factory battery-sense divider (A0/GPIO1, enabled via D5/GPIO6) replacing the compiled-in unknown sentinel, and the blocking hardware bring-up (flash-and-observe confirmation of the sense circuit, icon confirmed on real glass) — firmware and configuration only, no soldering and no added components

**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — Hardware Bring-up & ADS-B Validation | 7/7 | Complete    | 2026-08-26 |
| 2. Plane View — End-to-End Slice | 5/5 | Complete    | 2026-08-26 |
| 3. Visual Polish on Real Glass | 4/4 | Complete    | 2026-08-26 |
| 4. CI/CD, Documentation & Legal Compliance | 6/6 | Complete    | 2026-08-26 |
| 5. Battery Life & Low-Battery Indicator | 3/3 executed | In Progress (DEVICE-04 done, DEVICE-05 pending) | - |
| 6. Companion Configuration Web Interface | 12/12 | Complete    | 2026-08-28 |
| 7. Final On-Glass Verification | 1/1 | Complete   | 2026-08-28 |
**Plans:** 4/7 phases complete (1-4 plus inserted 3.1); 5 and 6 in progress, 7 not started

Plans:

- [x] 05-01-PLAN.md — Battery-life measurement (DEVICE-05) — Task 1 done, Tasks 2-3 parked to end of project
- [x] 05-02-PLAN.md — Low-battery indicator, server half (DEVICE-04) — Wave 1
- [x] 05-03-PLAN.md — Low-battery indicator, device half + hardware bring-up (DEVICE-04) — Wave 2 (completed 2026-08-27, confirmed on real glass)

### Phase 6: Companion Configuration Web Interface

**Note on origin (2026-08-27):** Promoted from REQUIREMENTS.md's v2 backlog, where it had lived as a "seed idea" since 2026-08-26 (`/gsd-discuss-phase 3`) and was expanded 2026-08-27 across two explore sessions (git commits `180fdd9`, `30f432f`, `8be8510`; seed notes `.planning/seeds/on-device-fault-icon.md` and the presence-adaptive-polling seed's sibling context) to also absorb view switching (superseding the physical-button concept), device health/battery status, airline-coverage monitoring, and a fault-icon affordance (CFG-05) — rather than staying three separate mechanisms. Promoted over four sibling seeds (AeroDataBox destination lookup, local RTL-SDR backup, presence-adaptive poll cadence, and the standalone device-local fault-icon fallback DEVICE-06) by explicit user choice.

**Note on numbering (2026-08-27):** Originally added as Phase 7 (appended after the then-existing Phase 6: Final On-Glass Verification, per `/gsd-phase add`'s default of appending to the end). The user asked why it depended on Phase 6 and, once told that dependency was just the tool's append-to-end default rather than a real technical or sequencing need, asked for it to run *before* the final on-glass sign-off instead — consistent with that phase's own stated intent to be "the project's true last step... done once everything else is finished." Renumbered to Phase 6; Final On-Glass Verification became Phase 7 (see that phase's own numbering note for the full cross-reference list touched by this swap).

**Note on scope (2026-08-27, `/gsd-discuss-phase 6`):** CFG-02 (view switching) removed — still nothing to switch to until a second view exists, moved back to v2 Requirements. In its place, discussion surfaced and the user chose to add seven new capabilities scoped as CFG-06 through CFG-12: a flight-history log, a manual poll trigger (rate-limited), airline-resolution statistics, a dark/light theme for the page itself, a live render preview, a gallery of recent renders, and — raised mid-discussion, after everything else was already settled — **runway selection (CFG-12)**: the device currently tracks only Orly's runway 3 (hardcoded); the two neighboring runways (06/24, 02/20) already have corridor geometry in `server/plane/detect.py` from the runway3-false-positive fix, currently used only to *exclude* their traffic, not to track it. This generalizes PLANE-01/02/03's detection logic (currently runway-3-specific) to be parameterized by a user-selected runway — a materially bigger change than the other CFG items, since it touches core detection code from Phase 1/2, not just a display/config layer over already-existing server data. CFG-01 (visual config) was narrowed during discussion to a DEPARTING/ARRIVING background-theme picker, constrained to variants Phase 7 validates on real glass — this reopens Phase 7's D-21 (see that phase's own scope note). Full discussion record: `06-CONTEXT.md`.

**Goal:** A user can reach a password-protected companion web page — a new, separate service on its own nip.io subdomain, not touching the vendored device-protocol server — to choose a validated display theme, select which Orly runway is tracked, monitor the device's health and the ADS-B sources' reliability over time, browse recent flight/render history, see airline-coverage gaps, and debug the render pipeline directly, all without SSH access to the VPS.
**Requirements**: CFG-01, CFG-03, CFG-04, CFG-05, CFG-06, CFG-07, CFG-08, CFG-09, CFG-10, CFG-11, CFG-12
**Depends on:** Phase 5
**Plans:** 12/12 plans complete

Plans:
**Wave 1**

- [x] 06-01-PLAN.md — Config and history persistence foundation (`server/device_config.py` theme/runway registries, `server/history_db.py` SQLite store + Caddy battery-log tailer)
- [x] 06-02-PLAN.md — Runway parameterization of the detection pipeline (CFG-12: `runways` block in the geofence, `select_aircraft_for_runway()`, all-providers-failed diagnostics)
- [x] 06-03-PLAN.md — Panel unpack for the live preview (`unpack_panel()`, the inverse of `pack_panel()`, plus PNG encoding)
- [x] 06-04-PLAN.md — Companion auth, layout shell and stylesheet (HMAC session cookie, single escaping helper, full UI-SPEC design system with dark/light and mobile)

**Wave 2**

- [x] 06-05-PLAN.md — Companion HTTP service and router (complete route table, whole-site auth gate, preview/gallery routes, manual poll trigger, five page stubs)
- [x] 06-06-PLAN.md — Render pipeline: theme-aware colours, runway-aware labels, CFG-05 source-fault badge

**Wave 3**

- [x] 06-07-PLAN.md — Config page: theme picker (CFG-01), runway picker (CFG-12), poll trigger (CFG-07)
- [x] 06-08-PLAN.md — Health page (CFG-03/CFG-05 landing) and Airlines page (CFG-04/CFG-08)
- [x] 06-09-PLAN.md — History page (CFG-06) and Preview page (CFG-10/CFG-11)
- [x] 06-10-PLAN.md — Poll-loop integration: config threading, history writes on state change, gallery retention, fault classification

**Wave 4**

- [x] 06-11-PLAN.md — Deployment (systemd unit, Caddy site block, durable access log, firewall deny, env template, push script, docs) and test-suite registration

**Wave 5**

- [x] 06-12-PLAN.md — Live verification: runway-gate capture (closes Assumption A1), Caddy log-shape confirmation (closes Assumption A3), developer sign-off checkpoint

### Phase 06.6: Companion UI clarity pass - timestamps, poll-trigger cooldown, corroboration copy (INSERTED)

**Goal:** Three independent clarity fixes to the companion web app, raised during Phase 6's live developer sign-off. (1) **Timestamps** — `health_page.py`'s already-shipped "absolute + relative" format (`"2026-08-28T13:58:02 (3m ago)"`, used today by the Device check-in and ADS-B pipeline rows) reaches the three spots that lack it: Health's own Battery Trend table, History's table, and Preview's "Captured" caption (D-02). The logic is promoted once into `companion/layout.py` rather than duplicated three times, because `companion/pages/__init__.py` forbids one page module importing another. (2) **Poll-trigger cooldown** — the remaining-seconds copy becomes a live, ticking countdown that re-enables the Trigger Poll Now button by itself at zero, seeded from the server-computed, `history_db`-persisted figure already in `ctx["poll_cooldown_remaining"]` and never from a client-side guess (D-01); it ships as an inline `<script>` block, not a new static file, so it cannot collide with sibling phase 06.5's "first JS file this project ships" framing. (3) **Corroboration copy** — investigation found the existing copy already satisfies "never mislabel the unknown state as failure," so this is verify-and-polish: confirm it against the live modules and convert the one-off confirmation into a permanent cross-page drift guard, inventing no copy change without a concrete found defect (D-03).

**Requirements**: None — unmapped backlog phase (promoted from 999.6), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (live ticking countdown), D-02 (extend the existing absolute+relative timestamp format to the three spots that lack it) and D-03 (corroboration copy, verify-only) in `06.6-CONTEXT.md`. All three fixes trace back to developer feedback captured during Phase 6's live sign-off (06-12).
**Depends on:** Phase 6. Soft, order-insensitive relationships with siblings 06.3, 06.4 and 06.5, which are planned-but-unexecuted against these same files — every 06.6 task locates its edit target by function/symbol name rather than line number, keeps `_battery_section(trend_rows)` single-argument (06.5-02 pins that call-site literal in its own gate), and leaves `_history_table_html()`'s return block to 06.3-03.
**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 06.6-01-PLAN.md — Promote the timestamp helpers into `companion/layout.py` as public `parse_iso()`/`age_seconds()`/`relative_age_text()`/`absolute_and_relative()`, rewire `health_page.py` onto them, and reformat Health's Battery Trend table (D-02)
- [x] 06.6-02-PLAN.md — Live, server-seeded poll-cooldown countdown as an inline `<script>` in `poll_trigger_section()`, with `json.dumps()` seeding and a permanent sink-safety gate (D-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06.6-03-PLAN.md — History's Timestamp column and Preview's Captured caption onto the shared helper, plus the D-03 corroboration verification and its cross-page drift guard (D-02, D-03)

### Phase 06.6.4: Companion sober visual refinement — Linear-inspired sobriety pass across buttons, cards/surfaces, banners, navigation, stat tiles, filter bar, icon buttons, segmented control, and tables (INSERTED)

**Goal:** Apply the already-fully-validated "sober, Linear-inspired" visual spec to the real companion codebase. Structural restraint only, not a rebrand: cards trade their resting shadow for a hairline with the shadow revealed on interaction; text buttons drop 44px→30px (a deliberate WCAG 2.5.5 AAA trade-off the developer accepted three times, still 2.5.8 AA-compliant) with an inset-highlighted primary and near-invisible quiet variants; icon buttons shrink to 28px while keeping a real 44px hit area via a pseudo-element; banners lose their colour wash for a neutral surface with a 3px edge and a status dot; both nav renderers tighten to 32px with a single tinted-pill active signal; the theme picker becomes one segmented control; tables lose zebra striping for a hover tint under quiet uppercase headers; and the filter bar tightens with both Clear controls converged on one rule. Every value was chosen and confirmed live against a rendered design-system artifact across ~8 rounds before planning began — this phase is pure application, with no design exploration remaining. Inserted urgently after the developer real-browser-tested Phase 06.6.3's shipped UI and reacted "c'est catastrophique d'un point de vue UI et UX".
**Requirements**: None — unmapped backlog phase, matching every prior `06.6.x` decimal phase's precedent (`requirements.mark-complete` returning `not_found` for these IDs is expected, not an error). Traced instead against `06.6.4-CONTEXT.md`'s own locked decisions D-01, D-01a, D-01b, D-01c, D-02, D-03, D-03a, D-04, D-04a, D-05, D-05a, D-06, D-06a, D-07, D-07a, D-08, D-09, plus the two explicit non-goals D-10 and D-11.
**Depends on:** Phase 06.6.3 (all its shipped markup/CSS) and the `heading-color-consistency` debug session (commit `01235a6`, already merged — this phase consumes its accent/status tokens and its serif/`legend` heading rule without revisiting them)
**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 06.6.4-01-PLAN.md — Emphasis typography and the card hairline treatment across all six card components, plus removal of the two dark-mode card-edge overrides that would pin the border on during hover (D-03, D-03a, D-09)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06.6.4-02-PLAN.md — Button system: 30px text buttons, primary inset highlight, quiet-at-rest secondaries with a hover reveal, pressed state, and the 28×28 icon button with a synthesized 44×44 hit area (D-01, D-01a, D-01b, D-01c, D-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06.6.4-03-PLAN.md — Flat banner surface with a 3px coloured edge and status dot across all three severities, the combined card-and-banner reconciliation for Health's source-fault block, and a contrast guard for the new surface (D-04, D-04a)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 06.6.4-04-PLAN.md — Both nav renderers at 32px with a single tinted-pill active signal and `:not()`-scoped hover states, and the theme picker as a CSS-only segmented control (D-05, D-05a, D-06, D-06a)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 06.6.4-05-PLAN.md — Data-table shell (both header rules together, no zebra striping, hover row tint) and filter bar, with both Clear controls converged via the existing data attribute and zero page-module edits (D-07, D-07a, D-08)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 06.6.4-06-PLAN.md — Closing wave: non-goal regression gate proving the typeface and every accent/status token held, full-suite gate, and the blocking developer real-browser verification in both themes (D-10, D-11)

### Phase 06.6.4.1: Companion page-by-page IA consolidation — Airlines→Health merge, Preview→History merge, Airlines reborn as illustration gallery (INSERTED)

**Goal:** Full page-by-page visual/content pass across all 5 companion pages, validated interactively against sketch artifacts this session. Settings (renamed from Config): single-column stacked sections replacing the broken 2-column runway grid, per-section descriptions, one page-level Discord-style unified unsaved-changes save bar replacing per-section dirty-bars (fixes a real dirty-state.js bug where the static fallback Save button never hides), backend route merge (LED form folds into the same POST route as Theme+Runway). Health absorbs the OLD Airlines page's diagnostics content entirely: anomaly banner uses short category-label pills instead of repeating tile sentences; Corroboration detail rows collapse behind a native details disclosure; Battery trend becomes a full-width interactive chart with labeled axes and a default latest-reading value; page restructures into Screen (device/battery) and Server-and-data (pipeline, corroboration, and a new resolution-rate tile) sections, with the old Airlines page's two sections (Unresolved prefixes registry, Resolution-statistics breakdown) demoted from cramped stat-tile grid cards into full-width stacked cards under Server-and-data — this fixes both the No-resolution-data-yet contradiction and the nested horizontal-scroll bug. History absorbs Preview entirely (Preview removed as a standalone nav item): a new Now-showing section carries the live-panel image plus colour caveat, with the render gallery demoted into a collapsed details disclosure; every History row gains a small icon-button that looks up the nearest-by-timestamp gallery render; unresolved-airline rows get a lightweight link to Health instead of duplicating the prefixes table. Airlines is REBORN, not removed: the nav slot is repurposed into a visual gallery of the panel's real illustration set (`server/plane/illustrations.py`/`server/assets/icons/illustrations/`, already-shipped art for 27 airlines, no new asset pipeline) — one card per airline with its real PNG (served through a new session-gated, membership-validated route mirroring the existing `/runway-image/{id}.png` pattern) and its fleet-type variant chips, plus a filter bar. Net navigation stays at 4 items (Settings/Health/Airlines/History) — the diagnostics content moves out of Airlines into Health, but the Airlines nav slot itself survives, repurposed. This phase also folds in and closes 06.6.3-08's own still-open closing checkpoint (Task 2), per the developer's explicit choice this session to fold that dangling checkpoint into this new pass rather than close it separately. All sketches were built and iteratively validated as standalone HTML artifacts against the real CSS design tokens and real page/asset content before this phase was opened — nothing in companion/ has been touched yet.
**Requirements**: None — unmapped backlog phase, matching every prior 06.6.x decimal phase's own precedent. Traced against `06.6.4.1-CONTEXT.md`'s 26 locked decisions D-01 through D-26 (all covered; see `06.6.4.1-ARTIFACTS.md`). Reorganizes the presentation of CFG-04, CFG-06, CFG-08, CFG-10 and CFG-11, all already marked complete under Phase 6 — this phase delivers no new requirement scope, so `requirements.mark-complete` returning `not_found` for its D-* ids is correct, not a gap.
**Depends on:** Phase 06.6.4
**Plans:** 8/9 plans executed

Plans:
**Wave 1** *(parallel, disjoint files — additive foundation only, nothing renamed or deleted)*

- [x] 06.6.4.1-01-PLAN.md — Shared CSS foundation: every class the four page plans consume, landed once in `style.css` (gallery cards, lightbox, chart axis labels, banner pills, the JS-gated save-fallback rule), plus the deletion of the two-column Settings grid (D-01, D-04, D-07, D-09, D-14, D-20)
- [x] 06.6.4.1-02-PLAN.md — Shared plumbing: the per-airline fleet-variant accessor, the session-gated validate-then-join illustration image route, and `panel-lookup.js` with its pre-auth static route (D-14, D-15, D-20)

**Wave 2** *(blocked on Wave 1; three page modules in parallel, disjoint files)*

- [x] 06.6.4.1-03-PLAN.md — Settings: single-column wrapped sections with descriptions, unified section-naming save bar, no-JS fallback fix, LED merged into one form and one all-or-nothing handler (D-01 through D-06, D-26)
- [x] 06.6.4.1-04-PLAN.md — Health: anomaly pills, Corroboration disclosure, interactive axis-labeled battery chart, Screen/Server-and-data restructure, and the old Airlines diagnostics absorbed as full-width cards (D-07 through D-12)
- [x] 06.6.4.1-05-PLAN.md — History absorbs Preview: Now-showing section, collapsed Recent-renders disclosure, server-side per-row nearest-render lookup with a native-dialog lightbox, unresolved-airline link to Health (D-18 through D-21)

**Wave 3** *(blocked on Wave 2 — closes the deliberate one-wave registry duplication)*

- [x] 06.6.4.1-06-PLAN.md — Airlines reborn as an illustration gallery: 27 cards with real art and fleet-variant chips, filter bar, and removal of the diagnostics content that moved to Health (D-13 through D-17)

**Wave 4** *(blocked on Wave 2 — shared route table)*

- [x] 06.6.4.1-07-PLAN.md — Settings route rename to `/settings` across router and nav, and retirement of the separate LED POST route, its handler, and its orphaned builders (D-05, D-26)

**Wave 5** *(blocked on Waves 2 and 4 — shared route table)*

- [x] 06.6.4.1-08-PLAN.md — Preview retirement: fixed 302 to `/history`, navigation shrunk from five items to four, `preview_page.py` deleted (D-22)

**Wave 6** *(blocked on all — blocking developer checkpoint)*

- [ ] 06.6.4.1-09-PLAN.md — Closing: full-suite and live-route gates, completed validation record, and the blocking 28-item developer verification pass translating 06.6.3-08's checklist, including the twice-deferred assistive-technology pass and production walkthrough (D-23, D-24, D-25)

### Phase 06.6.4.1.1: Settings theme picker and typography/spacing direction pass (INSERTED)

**Goal:** Close `06.6.4.1-UI-REVIEW.md`'s one BLOCKER and its seven "Design direction" findings by revising the companion's locked visual contract itself. Settings' Theme picker (UIR-01/02) — the first thing an operator sees after login, and today sixteen oversized 44px native radios in a bare square `<fieldset>` with no colour information for a colour setting — becomes a wrapping grid of ~160px selectable chips reusing the Runway picker's hidden-radio/accent-border mechanism, wrapped in the same `.theme-status` card Runway and Diagnostic LED already use. Each chip carries a **real** `server.plane.render` panel preview of its theme (not a CSS approximation): a net-new backend renders all 16 against one fixed fictional scene so themes stay visually comparable, crops a thin band out of the 1200x1600 panel, caches the PNG on disk under the state dir keyed on a theme+palette signature, and serves it through a new session-gated, membership-validated `/theme-preview/{id}.png` route following this project's own validate-then-join discipline. Alongside it, the typography and spacing direction items (UIR-20 through UIR-26) land as a coherent whole rather than as isolated tweaks: the serif stack reorders to lead with Iowan Old Style/Charter so Apple devices stop falling through to Georgia; a real three-tier ladder replaces size-only hierarchy (32px semibold page title / 22px regular section heading / 16px sans-semibold nested card title) with a 24px semibold wordmark above it; the two competing label voices collapse into one 12px sans-semibold uppercase voice across stat-tile captions, table headers, mobile card labels, filter counts and chips, retiring the serif Label role entirely; sibling-card gaps unify at 24px, desktop card padding grows to 24px while phones keep 16px, one-line card text gains a measure cap, section intros stack below 960px, History's secondary text moves to 13px/75%, buttons grow to 36px/14px on phones only (06.6.4 D-01's desktop density trade-off is extended, never reopened), and the "Saved —" banner moves below the page title so saving stops shifting the page. Both halves were prototyped and developer-validated as standalone HTML sketches (004-theme-picker-chips winner B, 005-type-ladder-health-page winner B) before this phase was planned. Note for reviewers: the nested-card-title change is a deliberate SECOND reversal — quick task 260901-uzi made it, quick task 260902-iag reverted it at the developer's direct request, and it returns here with explicit confirmation because it now lands as the bottom rung of a full ladder rather than as an isolated demotion.
**Requirements**: None — unmapped backlog phase, matching every prior 06.6.x decimal phase's own precedent. Traced against `06.6.4.1.1-CONTEXT.md`'s 19 locked decisions D-01 through D-19 (all covered; see each plan's "Artifacts this plan produces" section). Revises the presentation contract behind CFG-01 (theme picker), already marked complete under Phase 6 — this phase delivers no new requirement scope, so `requirements.mark-complete` returning `not_found` for its D-* ids is correct, not a gap. UIR-08 (the Airlines illustration file-size/pipeline finding) is deliberately out of scope; 260903-peo's SUMMARY records it as its own heavier follow-up.
**Depends on:** Phase 06.6.4.1
**Plans:** 6/6 plans complete

Plans:
**Wave 1** *(parallel, disjoint files — the new backend and the type foundation)*

- [x] 06.6.4.1.1-01-PLAN.md — Theme-preview backend: `companion/theme_preview.py`'s fixed-scene render through `server.plane.render`, band crop, signature-keyed disk cache under the state dir, and the session-gated membership-validated `/theme-preview/{id}.png` route (D-03, D-04, D-05, D-06, D-07)
- [x] 06.6.4.1.1-02-PLAN.md — Type ladder: serif-stack reorder, 32px semibold page title, 22px section headings, 24px semibold wordmark, nested card titles onto the 16px sans Emphasis tier, and the single uppercase label voice — plus the two harness type-contract checks retargeted from the state they pinned (D-09, D-10, D-11, D-12, D-13)

**Wave 2** *(parallel, disjoint files; blocked on Wave 1)*

- [x] 06.6.4.1.1-03-PLAN.md — Spacing rhythm and density: one 24px sibling-card gap, 24px desktop card padding with 16px kept on phones, a measure cap on one-line card text, stacked section intros below 960px, History's 13px/75% secondary text, and the file's first `max-width` query for 36px/14px phone buttons (D-14, D-15, D-16, D-18, D-19)
- [x] 06.6.4.1.1-04-PLAN.md — Flash banner renders after `page_header()` via a `layout.FLASH_SLOT_MARKER` slot with a preserved fallback for pages that do not use it, so saving stops shifting the page title; plus the serif-boundary guard extended onto what plan 02 actually changed (D-17)

**Wave 3** *(blocked on Wave 2 — shared stylesheet, and consumes plan 01's route)*

- [x] 06.6.4.1.1-05-PLAN.md — Theme chip picker: the `.theme-chip` component, `theme_fieldset()`'s multi-theme branch rewritten as a preview-bearing chip grid inside a `.theme-status` card, and `test_config_page.py` retargeted off the retired fieldset/radio-list contract (D-01, D-02, D-03, D-07, D-08)

**Wave 4** *(blocked on all — blocking developer checkpoint)*

- [x] 06.6.4.1.1-06-PLAN.md — Closing: full-suite and live-route gates including a pairwise theme-distinctness assertion over all 16 served previews, the blocking developer verification pass in both themes at 1440px and 375px (with the nested-card-title reversal called out for deliberate scrutiny), and the `sketch-findings-skypane` design system of record brought up to date

### Phase 06.6.3: Companion per-page redesign — Config, Health, History, Airlines, Preview (INSERTED)

**Goal:** Carry Phase 06.6.2's foundation (tokens, page-header pattern, sidebar, severity function, contrast checker) into a real recomposition of every companion page: Config's dirty-state save bar, read-only Theme status and runway cards; Health's roving-tabindex battery chart, specific anomaly summary, and disclosure-collapsed readings; History's mobile compact cards, filtering, and copy-to-clipboard; Airlines' filtering and simplified hierarchy; Preview's centered matte treatment, freshness signal, and task-oriented gallery captions. Split out 2026-08-31 from Phase 06.6.2 for context-budget reasons (see 06.6.2's Goal) — carries the nine per-page CONTEXT.md decisions and audit findings that need 06.6.2's shared primitives to land cleanly, avoiding double-touching the same page files.
**Requirements**: None — unmapped backlog phase. Traced against `06.6.3-CONTEXT.md`'s own locked decisions D-02 through D-05, D-06 (heading-dedup half), D-07 through D-10, D-12, D-13, D-18, D-20, D-22, D-23, plus the audit's UXA-01 (mobile-card half), UXA-05, UXA-06, UXA-11, UXA-13, UXA-16, UXA-17, UXA-18, and UXA-08 (Config-specific half).
**Depends on:** Phase 06.6.2 (consumes its design tokens, `page_header()`, sidebar footer region, and severity function)
**Plans:** 7/8 plans executed

Plans:
**Wave 1** *(parallel, no shared files)*

- [x] 06.6.3-01-PLAN.md — Shared foundation: `layout.concise_timestamp_html()`, `data_table(raw_columns=)`, 4 new icons, and 4 new pre-auth static JS files (dirty-state, list-filter, copy-button, freshness) wired through `app.py`
- [x] 06.6.3-02-PLAN.md — Shared foundation CSS: every new class this phase's five page plans reference (theme status, runway cards, dirty-bar, disclosures, history cards, filter bar, copy button, matte frame), landed once so no later plan touches `style.css`

**Wave 2** *(blocked on Wave 1; parallel with each other, disjoint files)*

- [x] 06.6.3-03-PLAN.md — Config: D-02/D-06 LED rename+dedup, D-04 read-only Theme swatch, D-05 Runway selectable cards, D-03 dirty-state save bar
- [x] 06.6.3-04-PLAN.md — Health: D-08 readings disclosure + chart reorder, UXA-06 specific anomaly copy, UXA-05 corroboration copy fix, D-13/UXA-11 roving-tabindex chart, D-12/UXA-13 freshness + stale-view banner
- [x] 06.6.3-05-PLAN.md — History: D-07/UXA-01 mobile compact cards, UXA-05 confirmed_state/runway labels, D-09 concise timestamps, D-20 filter bar, D-23 copy-to-clipboard

**Wave 3** *(blocked on Wave 2's shared-test-file plans; parallel with each other)*

- [x] 06.6.3-06-PLAN.md — Airlines: D-18 headline promotion + simplified hierarchy, D-09 raw_columns timestamps, D-20 filter bar
- [x] 06.6.3-07-PLAN.md — Preview: D-18 matte frame, UXA-16 sizing/loading hints, D-22 gallery caption reverse-parse, D-10 window label, D-12 freshness + stale-view banner

**Wave 4** *(blocked on all)*

- [ ] 06.6.3-08-PLAN.md — Full-suite gate plus a blocking local browser/keyboard/phone verification checkpoint across all five redesigned pages, closing this phase's two carried-forward deferred items (real assistive-technology testing, production authenticated walkthrough)

### Phase 06.6.2: Companion UX, accessibility, and responsive hardening (INSERTED)

**Goal:** Ship the shared UX/accessibility/design-token foundation the rest of the companion redesign builds on: color/surface/typography/motion tokens, a WCAG contrast checker, the joint mobile-nav closed-state + no-JS fallback fix, desktop table containment, a shared page-header pattern and refined sidebar (incl. sticky), warning/error severity propagation, a dedicated login shell with deep-link return and logout→POST, poll-trigger concurrency locking, and programmatic feedback roles. Split out 2026-08-31 from a single oversized "companion UX hardening" phase — the planner found the combined scope (~16 dense plans touching the same handful of already-shipped files) exceeded this project's own largest prior single-phase precedent (Phase 6's 12 plans, which was mostly additive). Nothing from the original 23 CONTEXT.md decisions or the audit's 18 findings was dropped — nine per-page items (Config/Health/History/Airlines/Preview redesign) moved to the new Phase 06.6.3, which depends on this phase's shared primitives.
**Requirements**: None — unmapped backlog phase (promoted from the 06.6.1-UX-AUDIT.md follow-up, itself promoted from real-device findings). Traced against `06.6.2-CONTEXT.md`'s own locked decisions D-01, D-06 (accent-color token half), D-11, D-14 through D-17, D-19, D-21, plus the audit's UXA-01 (desktop-containment half), UXA-02/03/04/07/09/10/14/15, and UXA-08 (accent-color half).
**Depends on:** Phase 06.6
**Plans:** 8/8 plans complete

Plans:
**Wave 1**

- [x] 06.6.2-01-PLAN.md — Design tokens (3 surface levels), a pure-Python WCAG contrast checker, UXA-04's light-accent fix, D-06's native-control accent-color, D-19's motion polish
- [x] 06.6.2-02-PLAN.md — UXA-15's server-side poll-concurrency lock plus a "Polling…" button affordance

**Wave 2** *(blocked on Wave 1)*

- [x] 06.6.2-03-PLAN.md — UXA-01's desktop History-containment fix and the joint UXA-02/UXA-12 mobile-nav semantic closed-state fix

**Wave 3** *(blocked on Wave 2)*

- [x] 06.6.2-04-PLAN.md — `layout.page_header()` + a distinct page-title typography role, applied across all five pages (D-15/D-16)

**Wave 4** *(blocked on Wave 3)*

- [x] 06.6.2-05-PLAN.md — Sidebar refinement (active pill, per-tab icons, sticky), a footer region grouping the theme picker with a new POST-only Sign out control, plus skip-link/aria-current/favicon (D-11/D-17/D-21/UXA-10)

**Wave 5** *(blocked on Wave 4)*

- [x] 06.6.2-06-PLAN.md — `health_severity()`/`overall_severity()` and severity-aware nav dot/banner/flash roles, closing UXA-14 and this phase's UXA-07 scope

**Wave 6** *(blocked on Wave 5)*

- [x] 06.6.2-07-PLAN.md — Dedicated `login_shell()`, allowlisted deep-link return, autocomplete/error-role/focus, and the D-01/UXA-09 language-policy regression, closing UXA-03

**Wave 7** *(blocked on all)*

- [x] 06.6.2-08-PLAN.md — Full-suite gate plus a blocking local browser/keyboard/contrast verification checkpoint

### Phase 06.6.1: Companion visual polish pass (INSERTED)

**Goal:** A second visual-design pass on the companion web app, evolving 06.3's shipped system rather than replacing it, driven by `06.6.1-UI-SPEC.md` (approved 6/6 by `gsd-ui-checker`) and three `/gsd-sketch` explorations. Five changes land together: (1) **a new token layer** — a warm system-serif family for headings and the "SkyPane" wordmark (body, tables, form controls and nav links stay sans-serif), a terracotta accent (`#E8622C` / `#FF8A5C`) replacing 06.3's blue and deliberately hue-separated from the amber warn-status colour, card shadows and softer radii replacing hairline outlines, warm off-white light-mode surfaces, and airier spacing globally; (2) **a real mobile hamburger menu** below 960px — a toggle in the header opening a push-down dropdown holding the five nav links and the relocated theme picker, closing on a second tap or Escape, with `aria-expanded` as the single source of truth for its state — replacing (and deleting) the horizontally-scrollable strip that real-device testing found hid Health/Airlines/History/Preview behind an undiscoverable swipe; (3) **Health density and redundancy cleanup** — the anomaly banner's detail list removed (the Overview tiles already carry the same information in colour), the battery-trend chart moved out of its 240px grid track into a full-width card section, and a five-symbol inline icon sprite giving each signal its own status-tinted icon; (4) **a notification dot on the Health nav link** whenever an anomaly is active, driven by a new never-raising cross-page `ctx` signal so no page module imports another; (5) **History cut from 9 columns to 7** by merging Callsign·Hex and Type·Airline into single one-line cells at today's row height. The phase closes with a blocking real-phone-and-real-browser sign-off — the step 06.3/06.4/06.5 all skipped in favour of computed-style inspection, which is precisely why this phase exists.
**Requirements**: None — unmapped backlog phase (promoted from 999.3's follow-on feedback), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (wordmark typography, no logo asset), D-02 (card relief, warmer headings, richer colour, airier layout), D-03 (serif on headings only), D-04 (new accent, distinct from warn-status; global density change), D-05 (sketch → UI-SPEC → plan rigour, including a real human visual sign-off) and D-06 (hamburger nav below 960px) in `06.6.1-CONTEXT.md`, plus D-00 (the already-fixed nav crush bug, superseded here by deleting the element that had it). It is UI-only follow-on work to Phase 06.3's design system, which is Complete and is not reopened.
**Depends on:** Phase 06.3 (the token/component system this phase evolves) and Phase 06.5 (the battery chart this phase relocates). **No formal ordering dependency on Phase 06.6** despite the roadmap position — the two are order-insensitive siblings that both touch `companion/layout.py`, `companion/pages/health_page.py`, `companion/pages/history_page.py` and two shared test harnesses. Every 06.6.1 plan locates its edit targets by function/symbol name rather than line number, leaves the section builders 06.6-01 rewires untouched, leaves History's Timestamp cell to 06.6-03, and recomputes each `EXPECTED_CHECK_COUNT` from the file's real on-disk value; whichever phase executes second re-reads the other's SUMMARY before assuming file structure — the same discipline 06.3/06.4/06.5 already used for their own mutual soft conflicts.
**Plans:** 6/6 plans complete

Plans:
**Wave 1** *(three parallel plans, disjoint file ownership)*

- [x] 06.6.1-01-PLAN.md — The whole design-token and component CSS layer: serif headings, terracotta accent, card relief, airier spacing, plus every class the later markup plans emit against and the removal of the nav strip's rules (D-00, D-01, D-02, D-03, D-04, D-06)
- [x] 06.6.1-02-PLAN.md — History's table cut 9 columns → 7 via merged one-line Callsign·Hex and Type·Airline cells, at unchanged row height (D-02)
- [x] 06.6.1-03-PLAN.md — Health's anomaly banner simplified, the battery chart moved to a full-width section, and `anomaly_active()` exposed as a never-raising cross-page signal (D-02, D-04)

**Wave 2** *(blocked on 01 + 03)*

- [x] 06.6.1-04-PLAN.md — A five-symbol inline icon sprite, a whitelisted `icon_html()`, per-tile status-tinted icons, and the Health nav notification dot wired through `ctx` (D-02, D-04)

**Wave 3** *(blocked on 01 + 04)*

- [x] 06.6.1-05-PLAN.md — The hamburger menu: `companion/static/nav-dropdown.js`, its pre-auth route, the header toggle + push-down dropdown, and deletion of the horizontal nav strip (D-00, D-06)

**Wave 4** *(blocked on all)*

- [x] 06.6.1-06-PLAN.md — Blocking real-phone and real-desktop visual sign-off, closing the human-eyes gap that caused this phase (D-05)

### Phase 06.5: Interactive battery trend chart with overall status (INSERTED)

**Goal:** The companion Health page's Battery trend section stops being the one section without a verdict and the one chart a user cannot interrogate. It gains (a) a persistent `status_dot()` badge rendered exactly as Device check-in and ADS-B pipeline already render theirs (D-01, the ask absorbed from the superseded Phase 06.1), and (b) real interactivity: every plotted point becomes a finger-sized, keyboard-focusable hit target carrying its exact millivolt reading and timestamp, revealed in a reserved readout line on tap **or** hover, working on a real phone and not only under a desktop mouse (D-02, against `06-CONTEXT.md` D-22's mobile bar). Two open questions are closed rather than deferred: the CONTEXT-flagged no-JS-vs-scoped-JS tension resolves to **scoped JS** — one external, cacheable ~30-line vanilla file served from a pre-auth `/static/battery-trend.js` route mirroring `/static/style.css`, because tap-triggered `:focus` on a non-native-control SVG shape is unreliable on iOS Safari and D-02 cannot be met by CSS alone; and the empty-history badge state is locked to **`"ok"`**, matching `corroboration_status()`'s "unknown is not a failure" precedent and avoiding a real coupling where a `"warn"` would make `collect_anomalies()` tell a zero-reading deployment it had suffered an abnormal drop. The pre-existing sparkline no-script regression test is left intact and unweakened; a new additive page-level check asserts exactly one `<script>` tag and zero inline event handlers instead.

**Requirements**: None — unmapped backlog phase (promoted from 999.5, having absorbed 999.1/06.1), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (persistent status badge reusing `status_dot()`) and D-02 (hover **or** tap reveals the exact mV + timestamp, mobile included) in `06.5-CONTEXT.md`. It is UI-only follow-on work to CFG-03, already Complete (Phase 6, plan 06-08), which is not reopened.
**Depends on:** Phase 6 (CFG-03's `_battery_section()`/`battery_sparkline_svg()`/`battery_status()`). Soft, order-insensitive relationship with Phase 06.3, which restructures the same file's `render()` into a stat-tile grid — `stat_tile()` passes `content_html` through byte-for-byte, so the badge and chart compose either way; `06.5-02-PLAN.md` and `06.3-04-PLAN.md` each carry a conditional note for whichever executes second.
**Plans:** 3/3 plans complete

Plans:
**Wave 1**

- [x] 06.5-01-PLAN.md — Wave 1: `companion/static/battery-trend.js` (the project's first shipped JS file) + its stylesheet rules + the pre-auth `text/javascript` static route mirroring `/static/style.css`

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06.5-02-PLAN.md — Wave 2: the D-01 badge with the empty-history `"ok"` decision written into the code, and D-02's server-rendered per-point hit targets, readout line and single external script reference

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06.5-03-PLAN.md — Wave 3: seeded live preview plus the real-phone tap/hover verification this project's stdlib harness structurally cannot automate

### Phase 06.4: Runway picker - show runway number and airport map (INSERTED)

**Goal:** The Config page's runway picker shows each runway's number/heading in the large Display type instead of a small inline radio label, and — for any runway whose airport-diagram image the user has supplied — that real diagram beside it, one image per runway id, served over a session-gated route that validates the requested id against `device_config.RUNWAY_IDS` before building any filesystem path. Because the images are the user's to supply (D-02), the phase's actual deliverable is the drop-in asset contract plus code that is correct in both states: with no image files present it renders the upgraded text-only picker with zero `<img>` tags and no error, and dropping `companion/static/runway-{id}.png` in makes that runway's diagram appear on the next page load with no code change and no service restart (D-03). UI-only — `server/plane/detect.py`'s runway-tracking logic (CFG-12, shipped in Phase 6) is not reopened.

**Requirements**: None — unmapped backlog phase (promoted from 999.4), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (real airport diagram/satellite excerpt with the runway highlighted), D-02 (the user supplies the image assets; the plan must not source, generate, or fetch one) and D-03 (graceful text-only fallback plus a predictable drop-in asset contract) in `06.4-CONTEXT.md`. It is UI-only follow-on work to CFG-12, which is already Complete (Phase 6, plan 06-07) and is not reopened.
**Depends on:** Phase 6 (CFG-12's registry and picker); Phase 06.3 for the `--color-border` token and the 2-column desktop fieldset grid — a soft dependency only, the CSS carries a fallback so it is correct either way
**Plans:** 1/1 plans complete

Plans:

- [x] 06.4-01-PLAN.md — Runway-image existence detection + ctx wiring, number-prominent fieldset with graceful fallback + D-03 asset contract, and the session-gated membership-validated `/runway-image/{id}.png` route

### Phase 06.3: Companion UI visual design and desktop layout pass (INSERTED)

**Goal:** The companion web app carries its own visual identity — revised colour, spacing and card treatment — and at desktop width becomes a genuine dashboard: a 240px sidebar navigation replacing the horizontal tab row, and Health/Airlines rendering their signals as status-coloured stat tiles in a responsive multi-column grid, with the main column capped and centred. Below 960px the existing mobile-first fluid layout is untouched. The pass also closes a real pre-existing gap: History's hand-rolled table never received the `.data-table-wrap` horizontal-scroll fix Airlines and Health already have, so it is still the one table that crops on a phone.

**Requirements**: None — unmapped backlog phase (promoted from 999.3), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (full colour/type/spacing refresh, superseding `06-CONTEXT.md` D-21), D-02 (true dashboard layout, not a wider single column) and D-03 (History's mobile table-crop fix) in `06.3-CONTEXT.md`, plus the carried-forward D-22/D-23/D-24/D-25 and the approved `06.3-UI-SPEC.md` design contract.
**Depends on:** Phase 6
**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 06.3-01-PLAN.md — `companion/layout.py`: shared `_nav_links()` helper, new `sidebar_nav()` and `stat_tile()` builders, and `page_shell()` extended into a `.dashboard-shell` that renders both nav copies
- [x] 06.3-02-PLAN.md — `companion/static/style.css`: revised colour tokens plus `--color-border`/`--space-3xl`, the stat-tile/dashboard-grid/page-section component rules (including the `min-width: 0` grid-blowout fix), and the single new 960px dashboard breakpoint
- [x] 06.3-03-PLAN.md — D-03's History `.data-table-wrap` fix, plus the Config form's `.config-form` class hook for the desktop two-column fieldset layout

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06.3-04-PLAN.md — Health's four signals and Airlines' two sections rendered as status-coloured stat tiles in dashboard grids under "Overview"/"Coverage" group headings

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 06.3-05-PLAN.md — full-suite gate, `06.3-VALIDATION.md` reconciled to the shipped breakdown, and the browser visual sign-off at 900px/960px/1200px/1440px+/phone width

### Phase 06.2: LED enable/disable toggle (INSERTED)

**Goal:** The board's bring-up LED can be turned on or off from the companion web interface, and the device obeys that choice on its next scheduled poll. Firmware and the wire protocol are already complete (`firmware/main/led.c`, `state_machine.c`, `api_client.c`); this phase closes the one remaining gap — no store, no endpoint, and no web control exist behind `byos_server.py`'s hardcoded `/display` field, so the setting can currently only be changed by physically reflashing the board.
**Requirements**: None — unmapped backlog phase (promoted from 999.2), not tied to a REQUIREMENTS.md REQ-ID. Traced instead against this phase's own locked decisions D-01 (own dedicated Config-page section) and D-02 (defaults to enabled) in `06.2-CONTEXT.md`, plus the inherited D-03 vendored-file discipline from `06-CONTEXT.md`.
**Depends on:** Phase 6
**Plans:** 2/2 plans complete

**Note on completion (2026-08-28):** Plan 06.2-02's sole task is a blocking human-verify checkpoint; the developer's sign-off is recorded in full in `06.2-02-SUMMARY.md`, including a real "LED still lit" false-alarm report from the first hardware observation round, investigated and root-caused (the firmware unconditionally lights the LED during the WiFi-connect+poll window regardless of `led_enabled`, per `firmware/main/app_main.c`/`state_machine.c`'s existing design) rather than silently dismissed. Second-round observation confirmed the toggle works as designed. No code changed in response — the report was a timing/expectation mismatch, not a defect.

Plans:
**Wave 1**

- [x] 06.2-01-PLAN.md — Wave 1: persist `led_enabled` in `server/device_config.py`, add the dedicated Config-page section and its own `/config-led` route, and read the value from the shared state directory in `byos_server.py`'s `/display` handler (VENDOR.md local modification #4)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 06.2-02-PLAN.md — Wave 2: blocking developer checkpoint — cross-process verification with both services on one explicit `--state-dir`, plus the physical LED confirmation (approved, both Part A and Part B confirmed)

### Phase 06.1: Battery status on companion web interface — SUPERSEDED (INSERTED)

**Goal:** Superseded 2026-08-28, before planning — merged into Phase 06.5. Codebase investigation during 06.5's discuss-phase found this phase's ask (a battery-status verdict on the companion web interface) targets the exact same code as 06.5 (`companion/pages/health_page.py`'s Battery Trend section), so both ship together there — an overall-status badge plus interactive hover/tooltip charting — rather than touching the same section twice. User confirmed the merge explicitly. See `06.5-CONTEXT.md` for the combined scope; this phase is intentionally never planned standalone.
**Requirements**: None — folded into Phase 06.5
**Depends on:** Phase 6
**Plans:** 0/0 plans complete

Plans:

- [x] N/A — superseded by Phase 06.5, see above

### Phase 7: Final On-Glass Verification

**Goal:** The project's true final sign-off, done once — not incrementally per phase — on the real, fully-finished device: Phase 3's shipped design (PT Serif Regular typography, the flat single-color background, the two-flight poster composition, per-airline dithered illustrations) is judged against actual Spectra 6 glass, the panel's still-interim Yellow/Red palette values are tuned by eye against the real ink, and every hardware-verification item this project has carried forward is closed out or explicitly recorded as a caveat. **This phase is not purely observational** — small font and structure corrections (a font-weight swap, a point-size adjustment, a geometry nudge for bezel clearance) are made directly here, based on what the glass actually shows, rather than deferred to a hypothetical future phase.

**Note on origin (2026-08-26):** This phase's sole plan (07-01) is Phase 3's original fourth plan (03-04), moved here at the user's explicit request — "cause this will be my really last step." Rather than doing the on-glass sign-off mid-Phase-3, the user wants one comprehensive real-hardware pass at the very end of the project, after Phase 4 (CI/CD) and Phase 5 (Battery Life) are also done. **Phase 3's original on-glass success criteria moved here in full, not just by reference** — Phase 3 closed on its code/mechanism work alone; the visual sign-off below is entirely this phase's to own. See `07-01-PLAN.md`'s own Provenance Note for the full renumbering record, and Phase 3's "Note on the on-glass verification plan" for the other side of this move.

**Note on numbering (2026-08-27):** Renumbered from Phase 6 to Phase 7 to make room for the new Phase 6 (Companion Configuration Web Interface), which the user wanted to run first — consistent with this phase's own stated intent to be the true last step, done once everything else is finished. Directory, plan file, threat IDs (`T-06-01-*` → `T-07-01-*`) and the expectation-note ID (`N-06-01-01` → `N-07-01-01`) all renumbered accordingly; no content beyond identity strings changed. See `07-01-PLAN.md`'s own "Second Renumbering Note" for the full record.

**Note on scope — D-21 reopened (2026-08-27, during Phase 6's `/gsd-discuss-phase 6`):** Phase 6's CFG-01 became a DEPARTING/ARRIVING background-theme picker, constrained to variants validated on real glass — which this phase is the only place that can happen. Success criterion 7 below is revised accordingly: instead of confirming Blue/Green unchanged, this phase now tests 2-3 alternate Blue/Green hue variants on the real panel (reopening `03-CONTEXT.md`'s D-21, previously "confirmed as 'parfait'" from screen previews only) and records the validated set for CFG-01 to expose. **Not yet reflected in `07-01-PLAN.md`'s own task detail/acceptance criteria** — that plan currently still assumes "Blue/Green confirmed unchanged" per the old criterion 7 wording; revise it when Phase 7 is next planned/re-verified, before executing Task 3.

**Depends on:** Phase 6 (sequential execution order — the plan's actual technical prerequisite is Phase 3's shipped render pipeline, already satisfied and complete)
**Requirements**: PLANE-01, PLANE-02 (the hardware-verified-legibility half of both — closing what Phase 3 could not close without the physical device)
**Success Criteria** (what must be TRUE):

  1. The aircraft illustration (per-airline or generic fallback) reads recognisably as a passenger jet at typical wall-viewing distance on real glass.
  2. The route/airline captions are legible on real Spectra 6 output, including `fit_text_size()`'s shrunk-overflow case for a long city/airline name — validated via a deliberately forced long-name render.
  3. A-02-02-01's departure-side deadband threshold is validated visually via a forced synthetic departure render (no real departure exists in Phase 1's captured sample data — 0 climbing readings across 217 real vertical-rate samples, max observed +48 ft/min). This confirms the *visual* DEPARTING state only — the real +200 ft/min threshold value itself stays unvalidated against real sensor data until a genuine runway-3 departure is observed in production.
  4. Overall poster composition reads as ambient art on the wall, not a data dump — a judgment call made with the frame in its current desk/temporary location as a provisional check; a final check once wall-mounted remains a caveat, not a blocker (D-03).
  5. PT Serif Regular's e-ink hairline-legibility risk (flagged in `server/assets/fonts/VENDOR.md`, never before checked on real glass) is judged per typographic role, including the previous-flight card's smallest text (16px/12px floor).
  6. Whether the frame/illustrations/text — positioned inside the old 64px safe-box band at a tighter 2.5%-of-width inset (D-26) — are clipped by the physical bezel is confirmed one way or the other.
  7. `PALETTE_RGB`'s two still-interim triples (Yellow, Red) carry values tuned against the real panel; 2-3 alternate Blue/Green DEPARTING/ARRIVING theme variants are tested on the real panel and the validated set is recorded for Phase 6's CFG-01 theme picker (reopens D-21 — see this phase's "Note on scope" above; supersedes the prior "verified unchanged" wording). **[PARTIALLY FULFILLED, 2026-08-28 — see `07-01-SUMMARY.md`:** Yellow/Red confirmed on real glass, no change needed. D-21 reopened as anticipated, but not the way this criterion expected: the developer found the *default* "sky" theme's Blue/Green too dark/saturated on real glass (both the six-band calibration swatch and, worse, the full-panel flat-fill field) and had `panel_format.PALETTE_RGB`'s Blue/Green re-tuned in place (two darkening passes) plus the flat background replaced with a dithered lighten-toward-White blend (`dither.dithered_state_background()`) to make a fixed physical ink visually lighter at all — a single corrected default, not 2-3 alternate selectable theme variants. **CFG-01's theme picker still has only the one "sky" theme; the multi-variant part of this criterion remains open**, now for a future phase to pick up if additional theme options are wanted.]
  8. Any small font-weight, font-size, or geometry correction the session's observations called for has been applied directly and re-confirmed on the glass — not just recorded for later. Only a genuine redesign need (a new font, a new asset, a different composition) is deferred as a scope question.
  9. The frame is left running live detection at the end of the session, not frozen on a synthetic test panel.

**Plans**: 1/1 plans complete

Plans:
**Wave 1**

- [x] 07-01-PLAN.md — On-glass verification battery (RGB calibration, PT Serif legibility, bezel clipping, forced departure/arrival, long names, two-flight composition) and the 02-UI-SPEC.md Colour addendum (moved from 03-04)

**UI hint**: no

### Phase 8: Panel theme rework

**Goal:** Glancing at the frame shows a clean white panel whose flight text is legible on real Spectra 6 ink with no box behind it, naming a real IATA flight number rather than a raw ADS-B callsign — with Black, Yellow, Red and the existing Sky theme selectable from the CFG-01 picker. Full scope, rationale, and the complete rendered decision trail are recorded in the spike this phase implements: `.planning/spikes/001-panel-theme-colours/README.md` and `.planning/spikes/MANIFEST.md`. Concretely: white becomes the new default theme with Black/Yellow/Red joining Blue/Green as optional CFG-01 themes; the text backing-plate is removed and replaced by PT Serif Bold everywhere; `adsbdb`'s `callsign_iata` is threaded through so the raw ADS-B callsign never displays; a previous-card text sizing/alignment fix; and a required, blocking on-glass verification pass before this phase can close.
**Requirements**: None — unmapped polish/refinement phase, no REQ-ID in REQUIREMENTS.md maps to it. Traced instead against `08-CONTEXT.md`'s locked decisions D-01 through D-13, the same precedent Phase 06.4 set. Each plan's `requirements` frontmatter field carries the decision IDs it implements; the full coverage table lives in `08-01-PLAN.md`'s Multi-Source Coverage Audit.
**Depends on:** Phase 7
**Plans:** 6/6 plans complete

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Theme registry: add White/Black/Yellow/Red, make White the default, relabel Sky (D-01..D-04)
- [x] 08-02-PLAN.md — Thread `callsign_iata` through enrich's parse/cache-write/cache-read chain (D-09)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-03-PLAN.md — Remove the text backing-plate, switch every text role to PT Serif Bold, grow the previous caption to 20px, record the font supersession (D-05/D-06/D-07/D-11)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-04-PLAN.md — Four-tier flight-identifier ladder, line-1-omitted handling in both text blocks, previous-card 20px optical offset, CLI tier forcing (D-08/D-10/D-12)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 08-05-PLAN.md — Illustration spot-check for the optical offset, `panel.bin` digest re-pin, full-suite reconciliation, forced-panel reminder unit-name fix (D-12)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 08-06-PLAN.md — Blocking on-glass verification battery on the real Spectra 6 panel, findings recorded to `hardware/BRINGUP-LOG.md` (D-13)

### Phase 9: Diagonal band theme

**Goal:** Implement spike `.planning/spikes/003-diagonal-band-theme/`'s validated findings: a new dedicated theme (additive to Phase 8's existing 11 — those stay untouched) adding a diagonal decorative band behind the aircraft illustration. Scope: (1) A new drawing primitive — a diagonal TRAPEZOID band (not a parallelogram) drawn behind the aircraft illustration. Geometry measured directly from the developer's reference image via per-row pixel scanning + linear regression: left edge x = -0.338*y + 595.2, right edge x = -0.250*y + 871.9 (as fractions: top spans 58.2%-85.2% of canvas width, bottom spans 7.4%-47.7%), band drawn with BAND_SHIFT_FRAC=0.0 (the reference's own unshifted position, confirmed clear of all text once the top tag was split per point 3). Reuses ImageDraw.polygon() for the shape and dither.dithered_state_background()'s toward-White blend technique for dithered variants. (2) Five band colour/treatment candidates to ship: blue light (dithered toward White), blue (flat), green light (dithered), red (flat), black (flat) — each must pass the real render._assert_legal_palette() background-dominance guard rail unmodified (verified in spike, White field stays pixel-dominant at every tested band width). (3) Top-label split: runway_tag_text()'s real output is partitioned on " · " — the airport code merges into the left state label ("DEPARTING FROM ORY" / "ARRIVING TO ORY", both keeping the existing 6px LABEL_TRACKING_PX tracking), "RWY 3" alone stays a separate right-aligned tracked tag. Must reuse runway_tag_text()'s real output (partition it), never hardcode/re-derive either half. (4) Main flight card gets a new three-tier text hierarchy: big bold flight-number line, a thin 1-2px dash rule under it, a tracked route line, then an airline·type line — built entirely from the real, unmodified content ladder (render._flight_line1_text()/_flight_line2_text() called verbatim: same four-tier fallback, same guarantee that the raw ADS-B ICAO callsign never displays). Positioned centred INSIDE the band, below the aircraft illustration, anchored at the same point production's real draw_main_text_block() already uses (main_placement.content[3] + MAIN_TEXT_GAP_PX). All three lines must share ONE computed centre-x value for the whole block, computed ONCE at the block's top y — not recomputed per line (confirmed real bug, spike round 12 regression, fixed round 15: recomputing per line visibly staggers the three lines since the trapezoid's centreline shifts ~50px over the block's own ~150px height). (5) Ink-colour rule: main-card text ink follows the band's own contrast colour rather than the theme's flat global ink_idx — white ink specifically when the band colour is Black (White theme's default IDX_BLACK ink is otherwise fully invisible against a black band — confirmed total-failure regression in spike round 12, fixed round 13), unchanged IDX_BLACK ink for every other band colour. (6) Previous/secondary flight card gets the identical three-tier hierarchy as the main card, right-aligned, scaled to its existing ~57% proportions (PREV_NUMBER_FONT 32px vs. the main card's 56px) — position stays below its own illustration, unchanged from current production (confirmed in spike the band never reaches far enough right at this card's height to collide). (7) PT Serif stays Regular project-wide for every new text role this phase adds — no italic vendoring (developer's explicit call, matches Phase 8's own on-glass finding that heavier weight reads "agressif" on this e-ink panel); ROUTE_LINE_FONT specifically uses Regular, not Bold. (8) A required, blocking on-glass verification pass before this phase can close, same D-13 precedent as every prior phase — every judgment in the spike was made from screen-preview PNGs only. Must specifically include: re-rendering all four content-ladder tiers against the FINAL confirmed geometry (last tier check predates the round 9-15 band-position changes); re-checking the previous card's band-collision clearance at the final geometry (last checked before round 11's tag-split-and-shift-to-0.0 change); and spot-checking each tier's content-aware block height against the final centred-in-band vertical/centring logic. Full rationale, exact measured geometry constants, all 15 rounds of iteration, every rejected/reverted approach, and the complete decision trail are in the spike's README.md and MANIFEST.md — read both in full before planning task breakdown.

**Requirements**: None — unmapped polish/refinement phase, no REQ-ID in REQUIREMENTS.md maps to it (`Requirements: TBD` at phase-add time, confirmed unmapped by `/gsd-plan-phase`). No `09-CONTEXT.md` exists either (developer explicitly skipped `/gsd-discuss-phase` and `/gsd-research-phase` for this phase, going straight from the validated spike to planning) — so unlike Phase 8's `D-01..D-13`, there are no CONTEXT.md decision IDs to trace against. Each plan's `requirements` frontmatter instead cites `PHASE9-1` through `PHASE9-8`, one per numbered clause of this Goal paragraph above (see `09-01-PLAN.md`'s objective for the full table) — the same traceability role D-XX decisions play elsewhere, anchored to this Goal text instead of a CONTEXT.md.
**Depends on:** Phase 8
**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 09-01-PLAN.md — Theme registry: 5 band THEMES entries (band_blue/band_blue_light/band_green_light/band_red/band_black) + theme_is_band()/theme_band_index()/theme_band_dithered() accessors (PHASE9-2, PHASE9-7)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 09-02-PLAN.md — draw_diagonal_band() + band geometry constants, band-aware draw_top_labels() split tag, partial _build_active_canvas() wiring (PHASE9-1, PHASE9-3)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 09-03-PLAN.md — Three-tier flight-identifier hierarchy on both cards, band-aware ink, single computed centre-x, completed wiring, full-suite reconciliation (PHASE9-4, PHASE9-5, PHASE9-6, PHASE9-7)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 09-04-PLAN.md — Blocking on-glass verification battery (5 band colours × both states, all 4 content-ladder tiers, previous-card clearance) and hardware/BRINGUP-LOG.md recording (PHASE9-8)

### Phase 10: Scheduled quiet hours

**Goal:** The frame sleeps through a configurable daily quiet-hours window instead of waking to poll. One recurring Europe/Paris start/end window plus an independent enabled flag (D-03/D-04) is set on the companion Settings page; the server extends the device's `sleep_s` past the window's end so it never wakes, connects or polls during it (D-01); and the panel shows a one-time "QUIET HOURS / Back at HH:MM" screen at window entry (D-05/D-06), with no symmetric screen at exit (D-07). Promoted from `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md`. **Supersedes this entry's earlier "developer chose seed option (b)" text:** `/gsd-discuss-phase 10` corrected the seed's own premise — extending `sleep_s` needs zero firmware change, since it is already a per-response, fully server-controlled value — so D-01 chose the full sleep-cycle extension after all, and it no longer depends on Phase 5's pending battery-discharge verdict.
**Requirements**: None — unmapped backlog phase promoted from SEED-001, matching every prior `06.6.x` decimal phase's precedent; `.planning/REQUIREMENTS.md` has no curfew/quiet-hours requirement ID.
**Depends on:** Phase 9
**Plans:** 5/5 plans complete

Plans:
**Wave 1**

- [x] 10-01-PLAN.md — Quiet-hours config registry fields plus DST-safe Europe/Paris window arithmetic in `server/device_config.py` (wave 1)
- [x] 10-02-PLAN.md — The "QUIET HOURS / Back at HH:MM" panel render state and its preview CLI in `server/plane/render.py` (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 10-03-PLAN.md — Extended `sleep_s` on `GET /device/v1/display` in the vendored `stub-server/byos_server.py`, with a duplication drift guard (wave 2)
- [x] 10-04-PLAN.md — `server/poll_loop.py` quiet-hours gate: render once at entry, hold, repaint the live board at exit (wave 2)
- [x] 10-05-PLAN.md — Companion Settings quiet-hours fieldset, `color-scheme` support and the shared checkbox class (wave 2)

### Phase 11: Web-configurable wake interval

**Goal:** The device's wake/poll interval is set from the companion Settings page instead of an SSH edit to `/opt/skypane/skypane.env` plus a `skypane-byos.service` restart. A new bounded `wake_interval_s` registry field (60-3600s, D-02, grounded in `FP_MIN_REFRESH_SPACING_S`'s own 60s default) is written by a plain `<input type="number">` — this codebase's first — and becomes the base value Phase 10's existing `quiet_hours_sleep_s()` extends, reaching the device as `sleep_s` on its very next `/device/v1/display` poll with zero firmware change and no service restart (D-01/D-03/D-06). The field pre-fills from the deployed `SKYPANE_SLEEP_S` that systemd already injects into the companion process, degrading honestly to a "Uses server default" placeholder when that value is absent or outside the field's own bounds (D-07). Promoted from `.planning/seeds/SEED-002-web-configurable-wake-interval.md`.
**Requirements**: None — unmapped backlog phase promoted from SEED-002, matching Phase 10's own precedent; `.planning/REQUIREMENTS.md` has no wake-interval requirement ID.
**Depends on:** Phase 10
**Plans:** 4/4 plans complete

Plans:
**Wave 1**

- [x] 11-01-PLAN.md — The bounded `wake_interval_s` registry field in `server/device_config.py`, with the deliberate `None`-sentinel "never explicitly set" contract (wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 11-02-PLAN.md — `read_wake_interval_s()` and the rebased `sleep_s` on `GET /device/v1/display` in the vendored `stub-server/byos_server.py` (wave 2)
- [x] 11-03-PLAN.md — The companion Settings page's fifth group, Wake interval, with this codebase's first `<input type="number">` and its string-to-int save gate (wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 11-04-PLAN.md — `SKYPANE_SLEEP_S` environment pre-fill for the Wake interval field in `companion/app.py` (wave 3)
