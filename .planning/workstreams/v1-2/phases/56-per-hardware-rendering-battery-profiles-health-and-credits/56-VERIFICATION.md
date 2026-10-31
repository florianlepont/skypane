---
phase: 56-per-hardware-rendering-battery-profiles-health-and-credits
verified: 2026-10-31T00:00:00Z
status: passed
score: 3/3 success criteria verified in code; of the 3 human items, the browser tests are covered by CI and the other two are owner-deferred follow-ups, not gaps (closed 2026-10-31)
gaps: []
human_verification:
  - test: "Send 56-PROVIDER-CONTACT.md to adsb.fi and adsb.lol once the fleet has more than 10 registered users"
    expected: "Owner finds the channel, sends the English draft, records the date and any reply"
    why_human: "Claude cannot send messages; the owner deferred the sending on 2026-10-31"
  - test: "Review the simulated landscape preview PNGs (owner approved; follow-up: reposition plane/illustration)"
    expected: "Owner-approved; the follow-up is non-blocking"
    why_human: "Visual composition quality"
  - test: "Run the companion browser tests on a machine with Chromium"
    expected: "Previously skipped browser tests (566 skips in total) pass"
    why_human: "No Chromium in this sandbox"
---

# Phase 56 Verification

## Closure (owner, 2026-10-31)

Closed as `passed`. It was `human_needed` on 2026-10-31 with three human items:

1. **Companion browser tests (566 skipped in this sandbox).** Covered by CI: the check "Lint, test, coverage, attribution" succeeded on PR #257 (2026-10-31, 08:52 UTC), where a missing Playwright browser fails the run by project policy rather than skipping. Evidence is the CI result; individual tests were not re-confirmed in the run output.
2. **Contact with adsb.fi and adsb.lol about multi-zone use.** The English draft exists (`56-PROVIDER-CONTACT.md`). The owner deferred sending it until the fleet has more than 10 registered users. Open follow-up, not a gap: the roadmap criterion asks for the contact to be traced, and it is.
3. **Simulated landscape preview.** The owner approved the preview. Repositioning the plane and illustration is a non-blocking follow-up.

The legacy-frame battery numbers recorded in the profile stay provisional until Phase 47 closes (see the Phase 47 coordination note in the roadmap).

**Goal:** What a frame displays and how its health is judged follow its hardware
profile, and data sources are credited.
**Branch:** milestone/v1.2-phase-56-hardware-render. **Mode:** initial.

## Commands run

| Check | Result |
|---|---|
| `./scripts/run-all-tests.sh` | exit 0, 6138 passed, 566 skipped (Chromium missing for browser tests; root-permission and openssl skips) |
| `server/test_golden_render.py` + `stub-server/test_phase47_freeze.py` | 25 passed |
| `git log --oneline -- server/fixtures/golden` | one commit only, b2dd5be7 "test(56-01): record golden baseline of the legacy render" (manifest unchanged since 56-01) |
| ruff | all checks passed |
| mypy (server venv) | no issues, 19 source files |
| `check_function_size.py check --max 80 server stub-server` | 697 functions, none over 80 |
| `check_comment_history.py check` | exit 0 |
| `git diff origin/main --stat -- hardware .planning/phases/47*` | empty (nothing changed) |
| Files changed outside server/companion/stub-server/.planning | only COMPLIANCE.md and README.md (credits references); no deploy/, .github/, systemd or env artefacts |

## Success criteria

1. **Native second-geometry render, legacy unchanged: VERIFIED.**
   - `server/hardware.py` defines `sim-landscape-800x480` (800x480, `layout_family=landscape`, gated by `SKYPANE_SIM_HARDWARE=1`).
   - The profile is threaded through `render.build_canvas`, `poll_cycle.run_once` and `cli --hardware`.
   - Landscape layout lives in `server/plane/render/landscape*.py`. `panel_format.new_canvas/pack_panel` and `dither` take a size, with defaults equal to the legacy values.
   - The legacy path passes `profile=None` and is byte-identical. `legacy_render_baseline.json` is untouched since 56-01 and `test_golden_render` passes against it.
   - Tests: `test_render_landscape_card`, `test_render_landscape_hold`, `test_render_profile_dispatch`, `test_geometry_primitives`.
   - `device_scope` now treats landscape as pollable at any size.
2. **Battery thresholds and health views from the profile, provenance recorded: VERIFIED.**
   - Provenance is per value (`BatteryProvenance`: source, status, date) for curve, low, low-clear, critical and critical-recover.
   - Legacy entries are all `provisional`; sim copies are also `provisional` and say "not a measurement". `_battery_problems` validates this, and a `final` status needs a measurement source.
   - Consumers read the profile:
     - `poll_cycle._low_thresholds` and `_critical_thresholds`;
     - byos `recover_mv`;
     - the health page, battery chart and home page via the `curve` parameter and `page_context.device_curve`.
   - The EE04 entry (`PLANNED_BATTERY_SLOTS["seeed-ee04-7in3-spectra6"]`) has every value `None`. It sits outside `REGISTRY`, so it is unregistered and unselectable.
   - Tests: `test_battery_profile`, `test_poll_cycle_profile`, `test_device_policy`, `test_hardware`.
   - Global single-pack heuristics (`companion/battery.py` and `health_signals.py`) are deliberately kept global and documented.
3. **Credits page: VERIFIED in code. Contact sending is human-only.**
   - `GET /credits` is registered with `PUBLIC` in `companion/routes.py`.
   - The page is generated by `credits_page.py` from `companion/credits.json`. The file lists adsb.fi (`https://adsb.fi`, a loader check requires the host), adsb.lol, adsbdb and OurAirports.
   - It is bilingual (`i18n_fr/credits.py`), linked from the login page, and added to the access matrix and route-table tests (`test_credits_page`).
   - `56-PROVIDER-CONTACT.md` exists with `status: deferred` (owner decision: send once the fleet has more than 10 registered users), `channel: unknown`, an English draft and a French section. It is not sent.
   - Criterion 3's wording, "contact ... is recorded", is met as a recorded draft per D-07. Actual sending remains an owner action.

## Requirements

| Req | Status | Evidence |
|---|---|---|
| HWR-01 | SATISFIED | Criteria 1 and 2 above. The golden baseline exists and is green. Renderer, thresholds and health views are profile-driven. Provenance is per value. |
| HWR-02 | SATISFIED in code; contact pending | Criterion 3. The credits page comes from one data file. The contact draft is recorded as to-send, as D-07 requires. |

## Other checks

- **Themes and palette (D-04):** `themes.theme_required_inks`, `themes_for_inks` and `theme_or_default` are pure. Stored config is not rewritten, and an unsupported theme falls back to the default. `companion/settings/look.py` offers only the profile's themes, and `test_theme_picker_profile` and `test_themes` pass. Theme previews still show the portrait sample; this is declared out of scope in the 56-11 summary.
- **Expand-only, no deploy:** the diff has no migration, schema or deploy changes. Phase 47 files and `hardware/` are untouched. `test_phase47_freeze` is green.
- **Owner note:** landscape previews approved; reposition plane/illustration is a non-blocking follow-up.
- **Anti-patterns:** the comment-history guard passes, and the function-size gate and ruff are clean. I did not grep for TBD/FIXME/XXX separately. The Phase 56 diff touches `companion/testdata/render_baseline.json`, whose only change is the new Credits link on the login page, as expected.

## Gaps

None blocking. Status is `human_needed` only because of the owner-only items in the frontmatter: sending the provider contact, visual preview sign-off (already given) and the browser tests that need Chromium.
