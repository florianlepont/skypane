# Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits - Research

**Researched:** 2026-10-30
**Domain:** Python stdlib + Pillow renderer geometry, hardware-profile data model, battery policy plumbing, companion public page
**Confidence:** HIGH on code facts (all read in this session), MEDIUM on the landscape composition numbers (design choice, not yet seen on glass), MEDIUM on adsb.fi / adsb.lol contact facts (one README fetched, one provider page blocked)

## Summary

The repository is closer to this phase than the roadmap suggests. `server/hardware.py` already has a `HardwareProfile` with width, height, palette and `BatteryProfile`, and a simulated `sim-landscape-800x480` type. `stub-server/byos_server.py` already builds a per-device `DeviceContext` with the profile's width, height and packed byte count, and `server/image_container.py` already takes width and height. What is still hard-coded to 1200x1600 is the renderer (`panel_format.new_canvas`/`pack_panel`, `dither.dithered_state_background`, and every `WIDTH`/`HEIGHT` import in `server/plane/render/*`), the poll cycle (no profile reaches `CycleContext`), and every battery consumer (they read `device_policy` module constants or `companion/battery.py` re-exports).

The least invasive route that keeps the live frame byte-identical is: (1) record a golden SHA-256 baseline of the current render FIRST, in a commit that changes no renderer code; (2) add optional `size` parameters (default = legacy) to the three shared geometry primitives; (3) leave every portrait module literally untouched and add a new landscape module that is selected by a `layout_family` field on the profile; (4) pass the profile through `run_once` to `CycleContext` and from there to `build_canvas(..., profile=)`; (5) give the battery functions optional curve/threshold arguments that default to the existing constants, and make callers pass `profile.battery`. `device_policy` constants stay (the Phase 47 freeze test and `measured_fields_freeze.json` read them), and `_LEGACY_BATTERY` stays derived from them, so the legacy profile cannot drift.

Themes, credits and the contact draft are small. Themes get a derived "required inks" accessor and a per-profile filter with fallback to `white` applied at the one render seam. The credits page is one new public `GET /credits` route plus one JSON data file, bilingual inside the file. Contact with adsb.fi / adsb.lol cannot be sent by Claude; a draft is prepared with status "to send". One finding the owner should know before sending: adsb.fi's README says its open data is "for personal, non-commercial use only" and asks heavy users to get in touch, and `COMPLIANCE.md` does not record that clause today.

**Primary recommendation:** Wave 1 = golden baseline commit (no renderer change) plus the profile data model (provenance, inks, layout family); Wave 2 = renderer geometry + landscape family + profile seam in the poll cycle, and battery plumbing; Wave 3 = themes per profile, credits page, contact draft. Never edit a portrait composition function; prove it with the golden test after every plan.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Owner-fixed
- **D-01:** The live frame's render and responses do not change by one pixel. A golden-image baseline of the legacy render is added and `stub-server/test_phase47_freeze.py` stays green. Expand-only. No production deploy.
- **D-02:** Legacy battery numbers are recorded as **provisional** with provenance, values unchanged. The future second hardware (Seeed EE04 7.3in, 800x480, ~20-25 s full refresh) gets only an empty "to be measured in Phase 58" slot; no number is invented.

#### Rendering (owner choice)
- **D-03:** "Native" means a dedicated landscape composition. The profile selects a layout family (portrait = the current composition, untouched; landscape = new). Geometry (width, height, packed size) comes from the profile; the simulated 800x480 type renders landscape natively. The layout family is reusable by the EE04 in Phase 58.

#### Themes and palette (owner choice)
- **D-04:** Themes declare the inks they need; a profile exposes only the themes its palette supports. A stored theme that a profile does not offer falls back to the default theme. Stored theme ids and the 16 existing themes stay unchanged on disk.

#### Battery provenance (owner choice)
- **D-05:** Provenance lives in the hardware profile, per value (curve, low, low-clear, critical, critical-recover): source, provisional/final status, date. Legacy values are marked provisional pending Phase 47. Thresholds, curve, percent and health views read the device's profile instead of module constants.

#### Credits (owner choice)
- **D-06:** A public companion page (reachable without sign-in), bilingual EN/FR, rendered from one data file listing adsb.fi (with link to its home page), adsb.lol, adsbdb and OurAirports. The README/COMPLIANCE credits can reference the same file.

#### adsb.fi / adsb.lol contact
- **D-07:** Claude cannot send messages. An English draft message about multi-zone usage is prepared for the owner, its status recorded as "to send" in the phase directory.

### Claude's Discretion
Module names, the golden-image mechanism, plan split and waves, how health views are parametrised, and how the data file is validated.

### Deferred Ideas (OUT OF SCOPE)
- EE04 battery model and real panel timings - Phase 58.
- Final legacy battery numbers - after Phase 47 closes.

Also out of scope per CONTEXT.md: second hardware battery model (Phase 58 rebuilds it), firmware (57), fleet poll loop (52), pairing/admin console (55), any production deploy. Phase 47 files and `hardware/` are untouched.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HWR-01 | The renderer, battery thresholds and health views are driven by the device's hardware profile, with provenance recorded for each battery number and a golden-image baseline of the legacy render. | Sections "Renderer geometry", "Landscape family", "Themes", "Battery", "Health views", "Golden baseline" and the Validation Architecture rows HWR-01a..g |
| HWR-02 | A credits page, generated from one data file, cites adsb.fi (with link), adsb.lol, adsbdb and OurAirports, and the project has recorded contact with adsb.fi / adsb.lol about multi-zone use. | Sections "Credits page" and "adsb.fi / adsb.lol contact" and Validation rows HWR-02a..d |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Python stdlib + Pillow + requests only (`server/requirements.txt`, hash-locked, Pillow 13.0.0). No new third-party package is needed or allowed in this phase.
- Code, comments, docstrings, docs, commit messages in English; companion UI bilingual EN/FR, French strings in `companion/i18n_fr/`, every user-facing literal through `i18n.msg`.
- Comments say what and why; NO plan, ticket, decision, review or phase IDs in comments or docstrings (`scripts/check_comment_history.py check` is a CI gate). Do not write "Phase 58" or "D-05" in code comments; say "a future hardware type" instead. Provenance `source` strings are data, but cite document paths and dates, not task IDs.
- CI gates a plan must keep green: `ruff check .`, `mypy` (module list in `pyproject.toml`; `server.hardware`, `server.themes`, `server.device_policy`, `server.panel_format` are in the strict override, `server.poll_cycle` is in the global list), `scripts/check_function_size.py check --max 80 server stub-server`, comment-history guard, `./scripts/run-all-tests.sh` (coverage floor 93), pytest-socket (loopback only).
- Companion tests obey `companion/test_suite_guards.py`: assert served HTML or a browser, never source text, never `.planning/`. Consequence: the contact-record file under `.planning/` cannot be asserted by a companion test (verify by hand or by the verifier).
- UI work must follow the `sketch-findings-skypane` skill (tokens, 360 px minimum width, card patterns). Public page uses the same shell as the 404/login pages.
- GSD workflow: edits go through a GSD command; no direct edits outside it.
- Phase 47 files and `hardware/` must not be modified (read-only for provenance text).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Hardware profile (geometry, inks, layout family, battery values, provenance) | `server/hardware.py` (committed registry) | - | Adding a type is a code change by design; stdlib only so byos can import it |
| Battery policy arithmetic (hysteresis, curve to percent) | `server/device_policy.py` (pure, stdlib) | - | Shared by poll cycle, byos and companion; must stay stdlib-only |
| Canvas geometry primitives (new canvas, pack, dithered field) | `server/panel_format.py`, `server/plane/dither.py` | - | Already shared by all families; gain an optional size |
| Portrait composition | `server/plane/render/{layout,text,glyphs,hold_screens,style}.py` | - | Untouched (D-01, D-03) |
| Landscape composition | new `server/plane/render/landscape.py` | reuses text/glyph/illustration helpers | Native composition, reusable by the next 800x480 hardware |
| Profile selection per cycle | `server/poll_cycle.py` (`run_once(profile=)`) | `companion/app.py` poll-now passes it | Phase 52 will own the fleet loop; this phase only adds the seam |
| Image serving by geometry | `stub-server/byos_server.py` | `server/image_container.py` | Already per-device (width/height/expected_bytes); only the critical-recover threshold needs the profile |
| Theme availability per palette | `server/themes.py` (leaf, no PIL) | `companion/settings/look.py` pickers | Pure data accessor; companion only filters what it lists |
| Health numbers (percent, low mark, ring, chart threshold) | `companion/battery.py`, `battery_chart.py`, pages | `device_scope` resolves device to profile | Companion reads, never defines, policy |
| Credits page | `companion/` (public route + page module + JSON data) | `README.md`, `COMPLIANCE.md` reference it | Public route in `routes.py` with `PUBLIC` access; no server tier involved |
| Provider contact record | `.planning/.../phases/56-.../` document | - | Owner sends it; not code |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib | 3.14 prod / 3.13 local venv | everything except Pillow | Project constraint [VERIFIED: pyproject.toml, `server/.venv/bin/python -V` 3.13.17] |
| Pillow | 13.0.0 (hash-locked) | canvas, dither, text | Already the only imaging dependency [VERIFIED: `server/requirements.txt`, `PIL.__version__` = 13.0.0 in venv] |
| pytest (+xdist, cov, socket) | per `server/requirements-dev.txt` | tests | Existing harness [VERIFIED: ran 44 tests in this session] |

### Supporting
None. No new package. Package Legitimacy Audit: not applicable, this phase installs nothing (no `pip`/`npm` change; slopcheck not run).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `landscape.py` module | Thread a `Geometry` object through every portrait function | Touches ~40 functions and risks the live render; rejected by D-03 ("portrait untouched") |
| SHA-256 manifest golden | Committed reference PNGs/bin files | 960 KB per case, noisy diffs; hashes are enough because Pillow is hash-locked. A failing hash can still be debugged by re-rendering from the pre-change commit |
| Derived theme ink accessor | Hand-written `inks` key on all 16 THEMES entries | Derived cannot drift from `departing_index`/`arriving_index`/`ink_index`/`band_index`; on-disk ids unchanged either way |

**Installation:** none.

## Architecture Patterns

### System Architecture Diagram

```
poll-now (companion)  --device.hardware_type-->  hardware.get_profile()  --\
systemd poll oneshot  --(legacy: profile=None)------------------------------+--> run_once(profile)
                                                                             |
                  load_cycle_context(profile)                                v
   battery_state.json --mV--> apply_battery_critical_hysteresis(mv, was, critical_mv, recover_mv)
                              apply_battery_hysteresis(mv, was, low_mv, clear_mv)   (thresholds from profile.battery)
                                                                             |
                                          decide_hold / detect / enrich ...  |
                                                                             v
                      render.build_canvas(..., profile)
                          |-- theme fallback: themes.theme_or_default(theme_id, profile.inks)
                          |-- profile.layout_family == "portrait" --> existing layout.py / hold_screens.py (unchanged)
                          `-- profile.layout_family == "landscape" --> landscape.py (new)
                                   uses: pf.new_canvas(size), dither.dithered_state_background(size),
                                         text/glyph helpers that take explicit positions
                          v
              pf.pack_panel(canvas)  (size from canvas)  -->  panel.bin (device dir)
                          v
   byos /device/v1/display: DeviceContext(width,height,expected_bytes) -> optional image container
                          v
        frame wakes; sleep_s pin uses profile.battery.critical_recover_mv

companion pages (home/health/chart) --device--> device_scope.profile_for(device) --> battery curve/low mark
anonymous browser --GET /credits--> routes.PUBLIC --> credits_page.render(load_credits(companion/credits.json), lang)
```

### Recommended Project Structure
```
server/
|-- hardware.py                    # + BatteryProvenance, inks, layout_family, planned-slot record
|-- themes.py                      # + theme_required_inks, themes_for_inks, theme_or_default
|-- device_policy.py               # + optional curve/threshold params (defaults = constants)
|-- panel_format.py                # + optional size on new_canvas / pack_panel
|-- poll_cycle.py                  # + profile on CycleContext / run_once / load_cycle_context
|-- plane/dither.py                # + optional size (cache key includes size)
|-- plane/render/landscape.py      # NEW: landscape family
|-- plane/render/layout.py         # build_canvas(profile=None) dispatch only
|-- fixtures/golden/legacy_render_baseline.json   # NEW golden manifest
|-- test_golden_render.py          # NEW
companion/
|-- credits.json                   # NEW single data file
|-- credits_page.py                # NEW load/validate + markup
|-- i18n_fr/credits.py             # NEW French chrome strings
|-- routes.py / app.py             # + PUBLIC GET /credits
.planning/workstreams/v1-2/phases/56-.../56-PROVIDER-CONTACT.md   # NEW, status: to send
```

### Pattern 1: Optional-size primitives with identical defaults
**What:** `new_canvas(bg_index, size=None)`, `pack_panel(canvas)` deriving width/height from `canvas.size`, `dithered_state_background(bg_idx, lighten_fraction=0.4, size=None)`.
**When to use:** the only three shared primitives that hard-code 1200x1600 (`panel_format.py:82-105`, `dither.py:45-80`).
**Example:**
```python
# panel_format.py (strict mypy module: keep fully typed)
def pack_panel(canvas: "PILImageModule.Image") -> bytes:
    width, height = canvas.size
    raw = canvas.tobytes()
    assert len(raw) == width * height and width % 2 == 0
    hi = raw[0::2].translate(_HIGH_NIBBLE_TABLE)
    lo = raw[1::2].translate(_LOW_NIBBLE_TABLE)
    out = (int.from_bytes(hi, "big") | int.from_bytes(lo, "big")).to_bytes(len(hi), "big")
    assert len(out) == (width // 2) * height
    return out
```
Source: existing code in `server/panel_format.py` (same algorithm, size-derived asserts). For 1200x1600 the output is identical by construction; the golden test proves it.

### Pattern 2: Profile-driven dispatch at the single render seam
**What:** `build_canvas(..., profile=None)`. `None` means legacy and takes the existing path with no new code executed except `profile is None`. For a profile: normalise the theme (`themes.theme_or_default`) then dispatch on `profile.layout_family`.
**Why here:** every render call in `poll_cycle.py` (lines 812, 814, 1135, 1145, 1201, 1209, 1237) and in the companion previews goes through `build_canvas`, so one seam covers base theme, arrivals theme, calendar theme and colour-rule results.

### Pattern 3: Battery functions take optional values, callers pass the profile
**What:** `apply_battery_hysteresis(mv, was_active, low_mv=BATTERY_LOW_THRESHOLD_MV, clear_mv=BATTERY_LOW_CLEAR_MV)`; same for critical and `battery_critical_pin_applies(latched, fresh_mv, recover_mv=BATTERY_CRITICAL_RECOVER_MV)`; `battery_fraction(mv, curve=BATTERY_DISCHARGE_CURVE)` and `battery_percent(mv, curve=...)` with the clamp endpoints derived from the curve passed in (not from the module constants).
**Why:** `device_policy.py` must stay stdlib-only and must not import `hardware.py` (hardware imports it). Constants stay because `test_phase47_freeze.py` and `measured_fields_freeze.json` (`wake_constants.values`) read them [VERIFIED: file read].

### Pattern 4: Companion resolves device to battery profile once
Add `device_scope.profile_for(device)`: `hardware.get_profile(device.hardware_type, os.environ)`, falling back to the legacy profile on `UnknownHardwareType` (a simulated type with the gate off must not break the Health page). Pages pass `profile.battery` into `companion/battery.py` functions (new optional `curve`/`battery` arguments, default legacy).

### Anti-Patterns to Avoid
- **Editing portrait composition functions** (`_build_active_canvas`, `_build_hold_canvas`, `draw_main_text_block`, ...). Even a "no-op" refactor invites byte drift. Write landscape beside them.
- **Importing `server.hardware` from `server/themes.py`:** `themes.py` is a leaf and `test_themes.py` asserts importing it never loads PIL. Pass `inks: frozenset[int]` instead.
- **Module-level cache keyed without size:** `dither._STATE_BACKGROUND_CACHE` is keyed `(bg_idx, lighten_fraction)`. A landscape render would poison the portrait cache and break the live frame. Key must include the size.
- **Inventing battery numbers for the sim types or the planned hardware.** The sim-landscape battery stays a copy of legacy values, labelled as such in its provenance.
- **Phase/decision IDs in comments** (comment-history gate).

## Renderer geometry: where 1200x1600 is hard-coded (read in this session)

| Place | What | Treatment |
|-------|------|-----------|
| `server/panel_format.py` | `WIDTH/HEIGHT/ROW_BYTES/IMAGE_BYTES`, `new_canvas`, `pack_panel` asserts | Keep constants (legacy, firmware docs, byos). Add size-derived behaviour to the two functions |
| `server/plane/dither.py` | `WIDTH = pf.WIDTH`, `HEIGHT = pf.HEIGHT` at import; `dithered_state_background` sized by them; cache key without size | Optional `size`; cache key `(bg_idx, lighten_fraction, size)`; module constants remain for legacy callers |
| `server/plane/render/style.py` | `SAFE_BOX`, `_band_edges` (`/ HEIGHT`), `BATTERY_ICON_BOTTOM`, `_assert_within_canvas` | Untouched. Landscape has its own bounds helper |
| `layout.py` | `draw_frame`, `draw_top_labels` (`WIDTH - MARGIN`), `_build_active_canvas` (`WIDTH`, `HEIGHT * *_FRAC`) | Untouched; `build_canvas` gains `profile=None` dispatch only |
| `text.py` | `draw_main_text_block`/previous block use `WIDTH//2`, `SAFE_BOX`, `_band_edges(…, WIDTH)` | Untouched. Reusable geometry-free helpers: `_role_fit_text_size`, `_role_fit_tracked_text_size`, `_role_font`, `_font`, `_flight_line1_text`, `_flight_line2_text`, `_wrap_text`, `draw_tracked_text`, `_tracked_text_width/bbox` |
| `glyphs.py` | `draw_source_fault_badge` and `draw_battery_icon` anchor to global `WIDTH/HEIGHT/BATTERY_ICON_BOTTOM`; the hold glyph functions (`draw_runway_icon`, `draw_moon_icon`, `draw_power_icon`, `draw_empty_battery_icon`, `draw_alert_icon`, `draw_updating_icon`) take `(draw, center_x, top_y, ink)` | Hold glyphs reusable as is. Landscape needs its own low-battery icon and source-fault badge placement (small functions in `landscape.py` that call the same primitives) |
| `hold_screens.py` | `_build_hold_canvas` uses `pf.WIDTH//2`, `pf.HEIGHT`, `style.SAFE_BOX` | Untouched. Landscape hold composer is new |
| `illustrations.py` | `ILLUSTRATION_MIN_WIDTH = 1200` is a source-art minimum, not a canvas size | No change; landscape downsizes the same PNGs |
| `stub-server/byos_server.py` | `from server.panel_format import HEIGHT, WIDTH`, `IMAGE_BYTES = 960000`, used only for the live context (`_live_context`) and `_served_image` defaults | Per-device context already uses the profile (lines 1045-1052). No change needed beyond the battery pin |
| `server/image_container.py` | none (width/height are arguments) | No change [VERIFIED: grep found no 1200/1600] |
| `server/poll_cycle.py` | `publish_canvas` calls `pack_panel(canvas)` (size-agnostic after the change); no profile on `CycleContext` | Add the seam (below) |
| `companion/device_scope.poll_supported` | refuses any profile whose size is not 1200x1600 | Replace by "profile available and its layout family can render it"; update `companion/test_device_scope.py::TestPollSupported::test_geometry_decides`, which currently asserts the landscape type is NOT supported |
| `companion/theme_preview.py` | crop box `(0, 390, 1200, 840)` of a portrait canvas | Out of scope; previews stay portrait samples (note in Open Questions) |

**Poll-cycle seam (least invasive):** `run_once(snapshot=None, state_dir=None, geofence=None, caddy_log=None, lock_timeout_s=None, reconcile_firmware=True, profile=None)`; `load_cycle_context(..., profile=None)` appends the keyword (existing tests call it positionally); `CycleContext` gains `profile` (None = legacy). `render.build_canvas(..., profile=ctx.profile)` at the seven call sites. `companion/app.py::_handle_poll_now` passes `hardware.get_profile(device.hardware_type, os.environ)` for non-live devices; the live frame and the systemd oneshot pass nothing. Phase 52 will later feed it from the fleet loop.

## Golden-image baseline

**Mechanism (recommended):** a SHA-256 manifest of packed panel bytes, because Pillow is hash-locked and the vendored fonts (`server/assets/fonts/PT*.ttf`) and illustrations (`server/assets/icons/illustrations/*.png`) are committed [VERIFIED: paths read]. I rendered seven representative cases in this session; each takes 0.01-0.19 s on the local venv, and `test_rendering_is_deterministic` already proves run-to-run determinism [VERIFIED: ran script; `server/test_render.py:548`].

- **Where:** manifest `server/fixtures/golden/legacy_render_baseline.json`; test `server/test_golden_render.py`. Do NOT put it under `.planning/` or `hardware/`.
- **Inputs:** reuse the fixtures from `server/test_render.py` (`TEST_FLIGHT`, `TEST_PREVIOUS_FLIGHT`, `TEST_ROUTE`, `TEST_PREVIOUS_ROUTE`, `TEST_LONG_ROUTE`) copied into the new test module (companion-style rule: tests must not import other test modules). They resolve vendored illustrations only (`state_dir=None`), so no network, no clock.
- **Case matrix (approx. 35 renders, a few seconds):** all 16 themes x `departing` (main card only); `arriving` + previous flight on `white`, `band_blue`, `red_light`, `band_red_field`; `battery_low` and `source_fault` overlays on two states; `empty` (default and one other runway id); `quiet_hours` with "07:00" and with `None`; `display_off`; `battery_empty`; the long-name stress route; `_build_no_connection_canvas(flat=True)` and `_build_updating_canvas(flat=True)` (firmware masks derive from them); plus one end-to-end `poll_cycle.run_once(snapshot=..., state_dir=tmp_path, geofence=...)` using the existing e2e fixtures, hashing the written `panel.bin`.
- **Manifest content:** `{"pillow_version": "13.0.0", "cases": {name: {"sha256": ..., "bytes": 960000}}}`. The test fails with a message that names the case and states "do not regenerate unless the change is proven renderer-neutral by re-rendering at the pre-change commit".
- **Generation:** a `__main__` entry in the test module prints the JSON; the baseline commit is made BEFORE any renderer file changes, from the unmodified tree. That ordering is the proof for D-01.
- **Flakiness guard:** Pillow version recorded in the manifest. If the hash-locked Pillow is ever bumped, the test reports the version mismatch first (FreeType in the wheel can shift glyph rasterisation), which tells the maintainer the failure is toolchain, not renderer. Python 3.13 (local) vs 3.14 (prod) do not matter: the same Pillow wheel is used and nothing in the render path uses Python-version-dependent float formatting [ASSUMED - confirm by running the manifest test on CI, which uses the prod Python].
- **Companion to freeze:** `stub-server/test_phase47_freeze.py` stays untouched and must pass at the end of every plan.

## Landscape family (800x480)

**Dispatch:** `HardwareProfile.layout_family: str` (`"portrait"` for legacy and `sim-ee02-clone`, `"landscape"` for `sim-landscape-800x480`), constants `LAYOUT_PORTRAIT`, `LAYOUT_LANDSCAPE` in `hardware.py`. Portrait is only valid at 1200x1600 (a registry-validation test enforces this); landscape takes any even width/height from the profile.

**Minimum set to prove "rendered natively" (all drawn from `profile.width/height`, no 1200/1600 anywhere):**
1. Active flight card, departing and arriving: top row (state label left, runway tag right), illustration nose-left on the left roughly 55 % of the width, text block (line 1 big, line 2 smaller) in the right column using `_role_fit_text_size` against the column width. Previous flight: a compact one-line strip at the bottom of the text column (or omitted when absent, as portrait does).
2. Empty state ("Watching ..."), quiet hours, display off, battery empty: one `_landscape_hold_canvas(profile, glyph_draw, glyph_height, label, sentences, field_idx, ink, dithered, ...)` composer with the glyph on the left and heading/rule/body on the right, reusing the existing `glyphs.draw_*_icon(draw, center_x, top_y, ink)` functions.
3. Overlays: low-battery icon and source-fault badge placed from canvas size.
4. Band themes (5 of 16 use a diagonal band): landscape draws the band as a right-hand parallelogram behind the text column using the theme's `band_index`/`band_dithered` and white ink; new constants local to `landscape.py`.
5. No-connection and updating canvases: cheap to expose because they are the same hold composer with different glyph/text. They are firmware-drawn from ink masks and only matter once firmware for the second hardware exists, so expose them (geometry-tested) but wire nothing.

**Sizing note (derived arithmetic):** 13.3 in at 1200x1600 is about 150 ppi; 7.3 in at 800x480 is about 128 ppi, so portrait type sizes (line 1 at 40 px, line 2 at 22 px, labels 18-20 px) are physically near-equal on the smaller panel; start from the same role fonts and let the fit helpers shrink [ASSUMED from panel names; the diagonal sizes are not measured].

**Own bounds helper:** copy the idea of `style._assert_within_canvas` as `landscape._assert_within(size, bbox, label)`; do not parametrise the portrait one.

**Reuse list (verified geometry-free):** `layout._load_illustration_safely`, `_left_for_centered_content`, `_top_for_centered_content`, `_left_for_right_aligned_content`, `draw_illustration`, `_assert_legal_palette`; `illustrations.select_illustration`; `text.*` helpers listed above.

**Manual QA:** the project's `ui_phase`/`UI hint: yes` flags and `human_verify_mode: end-of-phase` mean the owner should look at preview PNGs. Add `--hardware <key>` to `server/plane/render/cli.py` (it already writes `--preview` PNGs) so the owner can review landscape cards; this is the one human-verify item for rendering.

## Themes and palette (D-04)

- 16 themes in `server/themes.py`, each referencing `IDX_*` via `departing_index`, `arriving_index`, `ink_index`, optional `band_index` [VERIFIED]. All six `IDX_*` values appear across the registry.
- Add `theme_required_inks(theme_id) -> frozenset[int]` = union of `departing_index`, `arriving_index`, `ink_index`, `band_index` (if any) plus `IDX_WHITE` (the dithered path blends toward white; white is also the paper/hold ink). Derived, so the 16 entries and on-disk ids do not change.
- `themes_for_inks(inks) -> tuple[str, ...]` (registry order) and `theme_or_default(theme_id, inks) -> str` (returns `DEFAULT_THEME_ID` when the id is unknown OR needs an ink the profile lacks). `DEFAULT_THEME_ID = "white"` needs only black and white, so every profile must contain both (registry validation test).
- `HardwareProfile.inks: frozenset[int]` (new field with a default of all six; `palette` stays the RGB triples). Explicit beats inferring from `len(palette)//3` because the palette-order-equals-IDX-order coupling is implicit.
- **Where it applies:** `build_canvas` (render seam, one place) and the companion pickers: `look._cells()` iterates `device_config.THEME_IDS`; give it an optional `theme_ids` argument defaulting to all, and have the Display page pass `themes_for_inks(profile.inks)`. A theme the profile does not offer then becomes an ordinary "gap" cell (`REASON_NO_THEME`) - the picker already renders gaps disabled with a reason, no new UI needed. Keep `form_post` validation against the full registry (expand-only: a stored id stays valid; fallback happens at render).
- **Real profiles all offer 16 of 16** (both Spectra 6 and the sim types share `_PALETTE`). The mechanism is proven with a test-only reduced-ink profile built with `dataclasses.replace`, not a registered type.
- **Known limit:** illustration dithering (`dither_to_full_panel_palette`) always quantises to all six inks. A reduced-ink profile would need ink-restricted quantisation; no planned hardware needs it. Do not build it; assert in the registry validation that registered profiles have all six inks, or leave a documented guard. See Open Questions.

## Battery: consumers and provenance

**Consumers of `device_policy.BATTERY_*` / curve (all read in this session):**

| Consumer | Today | Change |
|----------|-------|--------|
| `server/poll_cycle.py:702` `apply_battery_critical_hysteresis` | module constants | pass `ctx.profile.battery.critical_mv/critical_recover_mv`; needs profile in `load_cycle_context` (before `CycleContext` exists - pass the profile argument in) |
| `server/poll_cycle.py:870` `apply_battery_hysteresis` (`update_battery_low`) | module constants | pass `low_mv/low_clear_mv` |
| `stub-server/byos_server.py:610-631` `battery_critical_sleep_s` -> `battery_critical_pin_applies` | `BATTERY_CRITICAL_RECOVER_MV` | the display handler already has `ctx` (`DeviceContext`); add an optional `recover_mv` to `battery_critical_sleep_s(base, state_dir, fresh_mv, recover_mv=default)` and have `DeviceContext` carry it (use `namedtuple(..., defaults=...)`; positional constructions exist at lines 1008 and 1048 only [VERIFIED: grep]). Existing tests call `battery_critical_sleep_s(base, dir, mv)` and keep working |
| `server/wake.py:74`, `device_config` | `BATTERY_CRITICAL_SLEEP_S` (a cadence, not a threshold) | unchanged; not hardware-specific |
| `companion/battery.py` | re-exports curve, `battery_fraction/percent`; `LOW_BATTERY_DISPLAY_MV` computed once at import from the curve at 20 % | add optional `curve` args; add `low_display_mv(curve)`; keep module constants as legacy defaults |
| `companion/pages/home_page.py:574,546`; `health_page.py:647,880`; `battery_chart.py:143,233,391-402`; `battery.battery_life_estimate` (lines 192-193) | percent via legacy curve; low mark from legacy constants | pass the device's curve |
| `companion/health_signals.py` `BATTERY_DROP_WARN_MV`, `battery.CHARGE_*` | single-pack EE02 calibration | stay global (see Health views) |

**Identity guarantee for the legacy device:** `_LEGACY_BATTERY` is built from the `device_policy` constants (`server/hardware.py:84-90`), so `profile.battery.curve is device_policy.BATTERY_DISCHARGE_CURVE`. Add a test sweeping `mv` from -1 to 4300 and a hysteresis grid asserting `fn(mv, ...)` with profile values equals `fn(mv)` defaults.

**Provenance model (recommended):**
```python
@dataclass(frozen=True)
class BatteryProvenance:
    value: str      # "curve" | "low_mv" | "low_clear_mv" | "critical_mv" | "critical_recover_mv"
    source: str     # document path + section, or "copied for simulation"
    status: str     # "provisional" | "final"
    date: str       # ISO date the value was set or last validated
# BatteryProfile gains: provenance: tuple[BatteryProvenance, ...] = ()
```
A tuple (hashable, immutable) rather than a dict, because `BatteryProfile` is a frozen dataclass. Add a lookup helper `BatteryProfile.provenance_for(name)`. A registry validation test requires every non-simulated profile to carry exactly the five names, statuses in the allowed set, non-empty source, parseable ISO date; `final` is only legal with a source that names a measurement.

**Legacy provenance text (found in the repo; do not invent more):**

| Value | Number | Source (document, section) | Date | Status |
|-------|--------|---------------------------|------|--------|
| curve | 14 knots 2946..4112 mV | `hardware/BATTERY-RUN.md`, "Calibration & Follow-Up Findings", outcome of finding 1: table built from the first discharge run's trend rows (12.34-day run, 2026-09-02 to 2026-09-14, last reading 2946 mV). `hardware/BATTERY-MODEL.md` ("Percentage calibration at the top of the curve", 2026-10-28) records that the top segment 4000-4112 mV was not calibrated against a discharge and that the curve is to be corrected once for the replacement pack | 2026-09-23 | provisional |
| low_mv | 3500 | `server/device_policy.py` rationale (margin above the logging tool's 3400 mV cutoff); validated, not changed, by `hardware/BATTERY-RUN.md` finding 2: would have fired 57.2 h before the device went silent | 2026-09-23 (validation) | provisional |
| low_clear_mv | 3600 | `server/device_policy.py`: 100 mV re-arm buffer against flapping. No measurement behind it | not recorded in repo history beyond the policy module | provisional |
| critical_mv | 3300 | `hardware/BATTERY-RUN.md`, "Follow-up: BATTERY EMPTY park": above the 2960 mV reading recorded 17 min before the device went silent, below the 3500 mV badge. Second run ended at this park (`hardware/BATTERY-MODEL.md`, "Inputs") | 2026-09-23 | provisional |
| critical_recover_mv | 3700 | same section: 400 mV re-arm buffer once charging resumes | 2026-09-23 | provisional |

Dates are the repo-recorded task dates (git history for the percent/park work, `.planning/quick/260923-gaf-*` and `260923-fr4-*` directory names) [VERIFIED: ls, `hardware/*.md` read]. Why all provisional: `hardware/BATTERY-MODEL.md` says the sleep-current question (VAL-03) is open and the pack is being replaced; `ROADMAP.md` line 23 says these numbers are final only after Phase 47.

**Sim types:** `sim-ee02-clone` shares `_LEGACY.battery` (same provenance object). `sim-landscape-800x480` currently copies the legacy values into a new `BatteryProfile` (`hardware.py:129-135`); give it provenance with `source="copied from the legacy profile for simulation; not a measurement"`, status `provisional`. It must not receive different numbers.

**Planned-hardware slot (D-02):** do NOT add an entry to `REGISTRY` (that would make it selectable and force invented numbers). Add a small frozen record in `hardware.py`, for example `PLANNED_BATTERY_SLOTS: Mapping[str, BatterySlot]` with `BatterySlot(label="Seeed EE04 7.3in, 800x480", status="unmeasured", note="to be measured in Phase 58", values=("curve","low_mv","low_clear_mv","critical_mv","critical_recover_mv"))`, each value `None`. A test asserts no `REGISTRY` profile references a slot and every slot value is `None`; the future hardware phase promotes the slot into a real profile. The slot key is a name choice (Open Question 3). The word "Phase 58" inside a string constant is data, not a comment, but prefer wording like "to be measured when the hardware is validated" if the owner wants the guard silent; the comment-history guard scans comments and docstrings only.

## Health views per profile

What each health surface computes from battery data and the treatment:

| Surface | Reads | Treatment |
|---------|-------|-----------|
| Home battery dial (`home_page._battery_pill_html/_battery_level`) | percent, `LOW_BATTERY_DISPLAY_PERCENT`, `battery_critical` latch, `health_state.battery_state` | percent via device curve; the 20 % "low" display policy stays a companion constant |
| Health battery row and ring (`health_page._battery_row`, `_battery_ring_html`) | percent | device curve |
| Chart (`battery_chart`) | percent unit, low threshold line at `LOW_BATTERY_DISPLAY_MV` (3540 mV for legacy), fixed axis 3000-4200 mV | threshold mV computed from the device curve at 20 %; the guard that hides the line when out of the fixed range already exists. Axis range stays fixed (both known hardware are single-cell LiPo; changing it would alter the legacy output) |
| `battery_life_estimate` | `battery_fraction` | device curve via an optional argument |
| `battery_status` (drop > 100 mV = warn) and `charging_estimate` (`CHARGE_PLATEAU_MV` 4090, step/ramp rules) | raw mV heuristics calibrated on one EE02 pack | stay global; their docstrings state they are one-pack calibrations. Making them per-profile needs measurements nobody has. Record in Open Questions, not as an invented per-profile value |

Resolve once per request: `PageContext` already carries the device (`ctx.device`); add `ctx.battery_profile` (or call `device_scope.profile_for(ctx.device).battery` where needed) so pages do not each re-derive it. `profile_for` must never raise (unknown or gated-off type falls back to legacy) because Health must render for every fleet row.

## Credits page (D-06)

- **Route:** add `Route("GET", Exact("/credits"), lambda h, m: h._handle_credits_get(), PUBLIC)` to `_GET_ROUTES` in `companion/routes.py` (the `PUBLIC` constant is the only pre-session grant and is already used by login, callback and static assets [VERIFIED]). Do NOT add it to `_DEVICE_SCOPED_KEYS`. `access.decide` returns ALLOW for `min_role == ANONYMOUS` before any session check.
- **Matrix test:** `companion/test_access_matrix.py` is a hand-written policy table with a completeness check that fails naming any route not listed; add `("GET", "/credits"): PUBLIC` to `ROUTE_POLICY`. The device-prefix check requires `/devices/<id>/credits` to stay refused automatically (not in `DEVICE_SCOPED`).
- **Handler pattern:** copy `_not_found_page`: `prefs.set_request_prefs(lang=self._lang_from_request())`, `health_alert = self._health_alert_for_admin()` (None for anonymous), `layout.page_shell(title=..., active="", body=..., ui_theme=self._resolved_ui_theme(), health_alert=health_alert)`. This works pre-auth today for the 404 page [VERIFIED: `companion/login_page.py:474`, `app.py:727-742`].
- **Entry points:** a "Credits" text link on the login card and in the account/sidebar footer so non-signed-in visitors can find it (discretion; keep within `sketch-findings-skypane` link patterns: accent text link, no new component).
- **Data file:** `companion/credits.json`, stdlib `json`. Shape:
  ```json
  {"version": 1, "sources": [
    {"id": "adsbfi", "name": "adsb.fi", "url": "https://adsb.fi", "licence": "...",
     "citation_required": true,
     "description": {"en": "...", "fr": "..."}},
    {"id": "adsblol", ...}, {"id": "adsbdb", ...}, {"id": "ourairports", ...}]}
  ```
  Bilingual text lives IN the file (single source), so the page picks `prefs.current_lang()`; UI chrome (heading, intro, link label, back link) uses `i18n.msg` ids in `credits_page.py` with French in new `companion/i18n_fr/credits.py` (modules in that package are auto-merged; ids unique, prefix `credits.`) [VERIFIED: `i18n_fr/__init__.py`].
- **Content facts (use as the file's starting data, each already in the repo):** adsb.fi must be cited with a link to its home page ("must cite adsb.fi and include a link to our home page") [CITED: github.com/adsbfi/opendata README, fetched 2026-10-30; also `COMPLIANCE.md` lines 34-48]; adsb.lol is CC0, credited by choice (`COMPLIANCE.md` lines 59-67); adsbdb.com is a free unauthenticated crowdsourced lookup (`COMPLIANCE.md` 130-142); OurAirports is public domain, credited as a courtesy [CITED: `.planning/workstreams/v1-2/research/STACK.md` line 108, from ourairports.com/data, checked 2026-10-28].
- **Validation function:** `credits_page.load_credits(path=DEFAULT_PATH)` raises `ValueError` unless: version known; exactly the four required ids present; each source has `name`, `url` starting with `https://` and a parseable host, `description.en` and `description.fr` non-empty; the adsb.fi entry's `url` host is `adsb.fi` (the citation requirement); no duplicate ids; no extra unknown keys. Tests call it with a good file and with `tmp_path` files that each break one rule (no source-text reading, per the guard).
- **Rendering safety:** every string through `layout.escape_html`; links `rel="noopener noreferrer"`; only `https://` URLs from the validated file are emitted.
- **README / COMPLIANCE:** both keep their text; add one sentence to each pointing to `companion/credits.json` and the live `/credits` page. Also add the omitted adsb.fi "personal, non-commercial use only" clause to `COMPLIANCE.md` (see next section).

## adsb.fi / adsb.lol contact (D-07)

Deliverable: `.planning/workstreams/v1-2/phases/56-per-hardware-rendering-battery-profiles-health-and-credits/56-PROVIDER-CONTACT.md` with a front-matter line `status: to-send`, the channel (unknown, see below), the English draft, and an empty "sent / reply" log for the owner. The requirement HWR-02 says "recorded contact"; Claude can only record the draft and its status, and the verifier must treat "sent" as an owner action. A companion test cannot read `.planning/` (guard), so this is a manual verification line.

What `COMPLIANCE.md` already records (so the draft need not repeat it): current usage is two requests per 30 s cycle, one to each provider, in parallel; each provider sees at most one request per cycle; at least 1.1 s between two requests to the same provider; adsb.fi documents 1 req/s and counts 4xx; adsb.lol documents dynamic limits and pre-announces a future feeder-contributed key; no raw data is republished (`COMPLIANCE.md` lines 218-250).

What the draft must say (facts to state):
1. Who/what: an open-source e-ink "next flight near me" frame; a rendered image of ONE selected flight is served to each frame, no feed or dataset is republished.
2. Change: from one fixed zone (Paris-Orly) to several zones, one per distinct location of the few registered users, all in France, queried on the existing ~30 s cycle.
3. Volume: queries are shared per zone (several frames in one zone cost one request), and the planned global budget is at most 1 request per second across all providers and all zones (planned in the fleet-poll work; not yet implemented, so say "planned"), with back-off on any error. Current actual: two requests per 30 s in total (about 0.07 req/s).
4. Asks: (a) is this multi-zone, multi-user personal use acceptable under adsb.fi's "personal, non-commercial use only" terms, given the frames belong to a small closed group and nothing is sold; (b) is the request pattern acceptable, or is a higher-rate/identified arrangement preferred; (c) for adsb.lol, whether the planned key-for-feeders requirement will apply and what is expected of a non-feeding consumer; (d) preferred User-Agent / contact string.
5. Credit: both are credited on a public credits page; adsb.fi home page linked.
6. Do not include coordinates, user names or e-mail addresses of users.

Facts gathered: adsb.fi README (fetched 2026-10-30): public endpoints 1 request/second; feeder endpoint 1 per 30 s; "400, 401, 403, 404, 429" responses count toward a temporary IP restriction; "adsb.fi open data is for personal, non-commercial use only"; "Please contact us if you have commercial or higher request rate requirements"; no email or Discord is listed in the README [CITED: github.com/adsbfi/opendata/blob/main/README.md]. adsb.lol: a web search summary says the GitHub README describes dynamic limits, a future API key obtainable by feeding, and asks API users in production to "let me know"; I could not fetch `adsb.lol/docs/open-data/api` (HTTP 403 from the fetcher) [LOW-MEDIUM: search summary only, repository README not opened]. The contact channel for both is therefore unverified: tell the owner to read the footer or Discord/GitHub links on adsb.fi and adsb.lol and fill in the channel before sending. Also note the repo's `COMPLIANCE.md` currently omits the non-commercial clause; recording it is part of this phase's doc work.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text fitting and tracked text for landscape | new measurement code | `text._role_fit_text_size`, `_role_fit_tracked_text_size`, `_wrap_text`, `draw_tracked_text` | Already geometry-free and tuned for PT Serif weights |
| Illustration load/placement | new resize/cache | `layout._load_illustration_safely`, `_left_for_centered_content`, `_top_for_centered_content`, `draw_illustration` | Handles corrupt/oversized PNGs and painted-pixel anchoring |
| Floyd-Steinberg field | custom dither | `dither.dithered_state_background(size=...)` | Existing two-colour quantise avoids the blue/green mix-up documented in the module |
| Nibble packing | per-pixel loop | `panel_format.pack_panel` | Vectorised, 30x faster |
| Image container for non-legacy geometry | a second encoder | `image_container.encode_container(image, w, h, version)` | Already width/height parametrised and used by byos |
| Credits page access control | custom session check | `routes.PUBLIC` + `access.decide` | The default-deny matrix already proves it |
| Language selection on a public page | cookie parsing | `self._lang_from_request()` + `prefs.set_request_prefs` | Same as the 404/login pages |
| JSON validation | a schema library | a small stdlib `load_credits()` | No new dependency allowed |
| Golden comparison | image-diff tooling | `hashlib.sha256` over packed bytes | Pillow is hash-locked |

**Key insight:** every hard part (text fitting, illustration placement, packing, container, access matrix, i18n merge) already exists geometry-free or policy-driven. The phase is wiring and one new composition, not new machinery.

## Common Pitfalls

### Pitfall 1: The dither cache poisons the live render
**What goes wrong:** `_STATE_BACKGROUND_CACHE` returns a 1200x1600 canvas for an 800x480 request (or the reverse) once sizes mix in one process (companion previews + poll-now for two devices).
**Why:** key is `(bg_idx, lighten_fraction)`.
**Avoid:** add size to the key in the same change that adds the parameter; test both orders in one process.
**Warning sign:** `ValueError`/size mismatch in `canvas.paste`, or a golden hash change after a landscape test ran first.

### Pitfall 2: "Harmless" edits to portrait code change bytes
**Avoid:** golden baseline committed first; run it after every plan; keep `profile=None` as the first-class legacy path (no new branches executed in portrait functions).

### Pitfall 3: Phase 47 freeze
`stub-server/test_phase47_freeze.py` reads `device_policy` constants, `measured_fields_freeze.json` values, the response key set, `sleep_s` per scenario and a replayed migration [VERIFIED]. Do not rename or alter constants or response shape; byos changes are limited to one optional parameter. Run the freeze test after every plan that touches `device_policy.py`, `byos_server.py` or `poll_cycle.py`.

### Pitfall 4: mypy strict modules
`hardware.py`, `themes.py`, `device_policy.py`, `panel_format.py` are in the strict override (no untyped defs, no implicit Any generics). New fields and functions there must be fully annotated; `poll_cycle.py` is under global settings. New modules may be added to the `files` list (and override list if strict) in `pyproject.toml`; adding is optional but recommended for the pure ones (`credits_page` is untyped companion code, leave it out).

### Pitfall 5: Function-size gate (80 lines, `server` and `stub-server` only)
`landscape.py` active-card composition will exceed 80 lines if written as one function; split into top labels, illustration, text block, overlays, band.

### Pitfall 6: Comment-history guard
No "Phase 58", "D-05", "HWR-01" in comments or docstrings. Provenance strings are data but still avoid task IDs; cite document paths and dates.

### Pitfall 7: pytest-socket
`--disable-socket` with loopback allowed. Tests of the credits route use the existing in-process app server fixtures (`companion/conftest.py`, `test-support/companion_app_server.py`), no external fetch; the data file holds URLs but the page never fetches them.

### Pitfall 8: Existing tests that encode old behaviour
`companion/test_device_scope.py::TestPollSupported::test_geometry_decides` asserts the landscape device is NOT pollable; it must change deliberately with `poll_supported`. `server/test_hardware.py` pins `profile.battery.*` equality with `device_policy` constants (still true) and `test_landscape_profile` (check its field assertions when adding fields).

### Pitfall 9: `DeviceContext` positional construction
Two positional constructions in `byos_server.py` (lines 1008, 1048). Use `defaults=` on the new field, or update both together.

### Pitfall 10: Theme fallback must not alter logged or stored values
Apply `theme_or_default` inside `build_canvas` only. Do not rewrite `device_config.json`, `poll_state` (`last_calendar_theme_id`) or the cycle result's `theme` fields; the freeze list names poll-state keys.

## Code Examples

### Hysteresis with optional thresholds (strict-typed)
```python
# server/device_policy.py
def apply_battery_hysteresis(
    battery_mv: int | None, was_active: bool,
    low_mv: int = BATTERY_LOW_THRESHOLD_MV, clear_mv: int = BATTERY_LOW_CLEAR_MV,
) -> bool:
    if battery_mv is None:
        return was_active
    if was_active:
        return battery_mv < clear_mv
    return battery_mv <= low_mv
```
Source: existing body of `apply_battery_hysteresis` with the two constants made parameters.

### Curve-driven fraction with endpoints from the curve passed in
```python
def battery_fraction(mv: object, curve: Sequence[tuple[int, int]] = BATTERY_DISCHARGE_CURVE) -> float | None:
    ...
    empty_mv, full_mv = curve[0][0], curve[-1][0]
    if value <= empty_mv: return 0.0
    if value >= full_mv: return 1.0
    for (lo_mv, lo_pct), (hi_mv, hi_pct) in zip(curve, curve[1:]): ...
```
Source: existing `battery_fraction` (the module-level `BATTERY_EMPTY_MV/FULL_MV` stay for the clamp defaults and `companion/battery.py` re-exports).

### Golden test skeleton
```python
# server/test_golden_render.py
import hashlib, json, os
import server.plane.render as render

MANIFEST = os.path.join(os.path.dirname(__file__), "fixtures", "golden", "legacy_render_baseline.json")

def _cases():
    yield "departing_white", lambda: render.render_panel(FLIGHT, "departing", route=ROUTE)
    ...

def test_legacy_render_is_byte_identical_to_the_recorded_baseline():
    with open(MANIFEST, encoding="utf-8") as fh:
        baseline = json.load(fh)
    mismatched = [name for name, make in _cases()
                  if hashlib.sha256(make()).hexdigest() != baseline["cases"][name]["sha256"]]
    assert not mismatched, "legacy render changed for: %s (pillow %s recorded)" % (mismatched, baseline["pillow_version"])
```

### Landscape native assertion
```python
canvas = render.build_canvas(FLIGHT, "departing", route=ROUTE, profile=hardware.REGISTRY[hardware.SIM_LANDSCAPE_KEY])
assert canvas.size == (800, 480)
assert len(pf.pack_panel(canvas)) == (800 // 2) * 480   # 192000, equals profile.firmware.max_image_bytes
```

### Public route and matrix row
```python
# companion/routes.py (in _GET_ROUTES)
Route("GET", Exact(CREDITS_ROUTE), lambda h, m: h._handle_credits_get(), PUBLIC),
# companion/test_access_matrix.py ROUTE_POLICY
("GET", "/credits"): PUBLIC,
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Module-level battery constants everywhere | Constants as legacy defaults, values read from `HardwareProfile.battery` | this phase | Second hardware can carry its own numbers |
| Poll refused for non-1200x1600 (`poll_supported`) | Refused only when no layout family can render the profile | this phase | Simulated landscape device can poll |
| adsb.fi `/api/v2/lat/lon/dist` | adsb.fi v3 recommended (deprecated, no sunset) | noted 2026-10-28 in v1.2 research | Not this phase (Phase 52 territory) |

**Deprecated/outdated:** nothing removed in this phase (expand-only).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Golden hashes are stable between local Python 3.13 and production-like Python 3.14 with the same Pillow wheel | Golden baseline | CI false failure on first run; mitigate by generating on CI's interpreter or recording pillow/python versions and checking in CI |
| A2 | Panel diagonals (13.3 in, 7.3 in) give ~150 / ~128 ppi so portrait font sizes transfer | Landscape family | Landscape text looks too large/small; the owner reviews preview PNGs |
| A3 | Landscape band themes are acceptable as a right-hand parallelogram | Landscape family | Owner may prefer no band themes on landscape; filter via ink/layout support instead |
| A4 | adsb.lol README asks production users to get in touch and plans a feeder key (from a search summary, README not opened; adsb.lol docs page returned 403) | Contact | Draft asks a question the provider already answered; low harm |
| A5 | Owner's contact channel for either provider is not documented in their README | Contact | Owner must find a channel manually |
| A6 | Slot key / label for the planned second hardware | Battery provenance | Naming churn when the hardware phase promotes it |
| A7 | Credits data file at `companion/credits.json` rather than `docs/` | Credits | Purely locational; README links follow |
| A8 | `ROADMAP`'s "UI hint: yes" implies owner visual review of landscape previews and the credits page | Validation | Extra manual step if not wanted |

## Open Questions (RESOLVED)

1. RESOLVED: **Reduced-ink profiles and illustration dithering**
   - Known: themes can be filtered by ink; illustrations always dither to six inks.
   - Unclear: whether any future hardware has fewer than six inks (EE04 is Spectra 6 per owner).
   - Recommendation: implement filtering and fallback only; guard the registry to six-ink profiles; do not build restricted dithering.

2. RESOLVED: **Per-profile charge/drop heuristics (`CHARGE_*`, `BATTERY_DROP_WARN_MV`)**
   - Known: they are calibrated on one EE02 pack.
   - Unclear: nobody has a second pack's data.
   - Recommendation: leave global, add a comment saying so; revisit with the second hardware's measurements.

3. RESOLVED: **Key and label for the planned second hardware slot**
   - Recommendation: `seeed-ee04-7in3-spectra6` as the slot key, owner can rename in the plan; no registry entry.

4. RESOLVED: **Theme previews for landscape devices** (`theme_preview.py` crops a portrait canvas)
   - Recommendation: out of scope; note in the plan summary that previews show the portrait sample.

5. RESOLVED: **Contact channel for adsb.fi / adsb.lol**
   - Recommendation: owner supplies; draft marks the channel `unknown`.

6. RESOLVED: **Should the Health page display battery provenance to the owner?**
   - Recommendation: not required by D-05 ("recorded"); keep it in the profile and tests; add UI only if the owner asks.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `server/.venv` | all tests | yes | 3.13.17, Pillow 13.0.0 | - |
| pytest, xdist, cov | tests | yes | ran 44 tests with `-n 0 --no-cov` | - |
| ruff | CI gate | yes | 0.17.2 | - |
| mypy | CI gate | yes | 2.4.0 | - |
| `scripts/check_function_size.py`, `check_comment_history.py` | CI gates | yes | stdlib; comment guard returned clean | - |
| Chromium / Playwright | only if a browser test is added for `/credits` | not checked | - | Server-HTML tests suffice; browser test optional |
| Network | tests | blocked by pytest-socket (by design) | - | no test may need it |

**Missing dependencies with no fallback:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9 with xdist, cov, pytest-socket (`pyproject.toml`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, importlib mode) |
| Quick run command | `server/.venv/bin/python3 -m pytest <paths> -q -n 0 --no-cov` |
| Full suite command | `./scripts/run-all-tests.sh` |
| Static gates | `server/.venv/bin/ruff check .`; `server/.venv/bin/mypy`; `server/.venv/bin/python scripts/check_function_size.py check --max 80 server stub-server`; `server/.venv/bin/python scripts/check_comment_history.py check` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HWR-01a | Legacy render byte-identical (themes, states, overlays, e2e panel.bin) | golden | `pytest server/test_golden_render.py -q -n 0 --no-cov` | Wave 0 (new) |
| HWR-01b | Live responses unchanged | freeze | `pytest stub-server/test_phase47_freeze.py -q -n 0 --no-cov` | exists |
| HWR-01c | Sim landscape renders natively: size 800x480, 192000 packed bytes, legal nibbles, background dominant, text inside bounds, all states, both flight states, band and non-band themes, deterministic | unit | `pytest server/test_render_landscape.py -q -n 0 --no-cov` | Wave 0 (new) |
| HWR-01d | `run_once(profile=sim landscape)` writes a 192000-byte panel.bin; byos serves it (raw and container) for a fleet device; portrait poll still works; dither cache not poisoned when mixing sizes | integration | `pytest server/test_poll_cycle_steps.py server/test_pipeline_e2e.py stub-server/test_device_fleet.py -q -n 0 --no-cov` plus new cases | partly exists |
| HWR-01e | Themes: required inks derived; 16 of 16 for six-ink profiles; reduced-ink fake profile filters and falls back to `white`; `themes.py` still imports no PIL | unit | `pytest server/test_themes.py server/test_hardware.py -q -n 0 --no-cov` | exists, extend |
| HWR-01f | Battery identity for legacy (sweep of mV and hysteresis grid), different synthetic profile changes decisions in poll cycle, byos pin, percent and low mark in rendered Home/Health HTML | unit + integration | `pytest server/test_device_policy.py stub-server/test_poll_cycle.py companion/test_battery_charging.py companion/test_health_signals.py -q -n 0 --no-cov` plus new tests | exists, extend |
| HWR-01g | Provenance complete for every non-simulated profile (five names, status, ISO date, source); planned slot has no numbers and is not in `REGISTRY` | unit | `pytest server/test_hardware.py -q -n 0 --no-cov` | extend |
| HWR-02a | Anonymous `GET /credits` returns 200 in EN and FR, with the four sources and an `href="https://adsb.fi"` link; `/devices/<id>/credits` is refused | HTTP | `pytest companion/test_access_matrix.py companion/test_credits_page.py -q -n 0 --no-cov` | matrix exists, credits new |
| HWR-02b | `load_credits` accepts the shipped file and rejects each broken variant (missing source, http URL, missing French, duplicate id, wrong adsb.fi host) | unit | `pytest companion/test_credits_page.py -q -n 0 --no-cov` | new |
| HWR-02c | French catalogue complete for new ids | unit | `pytest companion/test_i18n.py -q -n 0 --no-cov` | exists |
| HWR-02d | Contact draft recorded with status to-send | manual (guard forbids tests reading `.planning/`) | verifier opens `56-PROVIDER-CONTACT.md` | n/a |
| HWR-01h | Owner reviews landscape preview PNGs (`render --hardware ... --preview`) | manual | owner, end of phase | n/a |

### Sampling Rate
- **Per task commit:** golden test + the touched module's tests (quick command).
- **Per wave merge:** `pytest server stub-server companion -q -n auto --no-cov` plus ruff, mypy, function-size, comment-history.
- **Phase gate:** `./scripts/run-all-tests.sh` green (coverage floor 93) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `server/test_golden_render.py` and `server/fixtures/golden/legacy_render_baseline.json` (committed alone, first, from the unmodified tree)
- [ ] `server/test_render_landscape.py`
- [ ] `companion/test_credits_page.py`
- [ ] Extend `server/test_hardware.py`, `server/test_themes.py`, `server/test_device_policy.py`, `companion/test_access_matrix.py`, `companion/test_device_scope.py`
- [ ] No framework install needed.

## Security Domain

`security_enforcement` is enabled (ASVS level 1, block on high).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (the credits route is intentionally anonymous) | - |
| V3 Session Management | no change | - |
| V4 Access Control | yes | new route declared `PUBLIC` in the table; matrix test row; not device-scoped |
| V5 Input Validation | yes | no request input is used by `/credits` except the language cookie/Accept-Language through the existing resolver; data file validated by `load_credits`; HTML escaped |
| V6 Cryptography | no | - |
| V12/V13 (files/API) | minor | data file read from a fixed path, never from request input |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Stored XSS via data file text or URL (`javascript:`) | Tampering | `escape_html` on all text; accept only `https://` URLs; `rel="noopener noreferrer"` |
| Information leak on a public page (health alert, device names) | Information disclosure | `_health_alert_for_admin()` only for admin principal; page body contains only static credits |
| Public route accidentally device-scoped or giving device state | Elevation | not in `_DEVICE_SCOPED_KEYS`; matrix test covers `/devices/<id>/credits` |
| Hostile `hardware_type` in a fleet row breaks Health | DoS | `profile_for` never raises; falls back to legacy |
| Reduced-profile theme id from `device_config.json` reaching an unknown index | Tampering | `theme_or_default` returns the default for unknown ids and for ids needing absent inks |
| Draft message leaking coordinates/emails | Information disclosure | draft rules forbid them (above) |

## Plan split and waves (suggested, discretionary)

| Wave | Plan | Content | Files (conflict note) |
|------|------|---------|-----------------------|
| 1 | A: Golden baseline | manifest + test, committed before any renderer change | new files only |
| 1 | B: Profile model | `BatteryProvenance`, `inks`, `layout_family`, planned slot, provenance for legacy/sim types, `theme_required_inks`/`themes_for_inks`/`theme_or_default`, registry validation tests | `hardware.py`, `themes.py`, tests |
| 2 | C: Poll-cycle profile seam + renderer geometry | optional sizes in `panel_format`/`dither`, `landscape.py`, `build_canvas(profile=)`, `run_once/CycleContext/load_cycle_context(profile)`, `poll_supported`, render CLI `--hardware` | `poll_cycle.py` (shared with D: do C first), render package |
| 2 | D: Battery plumbing | `device_policy` optional params, poll cycle uses `ctx.profile.battery`, byos pin, companion `battery*`/pages/`profile_for` | depends on C for the `ctx.profile` field; `device_policy.py`, `byos_server.py`, companion |
| 3 | E: Themes per profile in pickers | `look._cells(theme_ids)`, Display page passes profile themes | companion settings |
| 3 | F: Credits page | route, data file, page, i18n, matrix row, README/COMPLIANCE pointers | companion; independent of A-E (can run in wave 1 in parallel if capacity) |
| 3 | G: Contact draft | `56-PROVIDER-CONTACT.md`, COMPLIANCE non-commercial clause | docs only |

Golden test runs at the end of B through G.

## Sources

### Primary (HIGH confidence) - read in this session
- Repo files: `server/hardware.py`, `panel_format.py`, `themes.py`, `device_policy.py`, `poll_cycle.py`, `plane/dither.py`, `plane/render/{__init__,layout,text,glyphs,hold_screens,style}.py`, `stub-server/byos_server.py`, `stub-server/test_phase47_freeze.py`, `measured_fields_freeze.json`, `companion/{battery,battery_chart,health_signals,device_scope,access,routes,login_page,i18n_fr}`, `companion/pages/{home_page,health_page}.py`, `companion/settings/look.py`, `pyproject.toml`, `COMPLIANCE.md`, `README.md`
- `hardware/BATTERY-RUN.md`, `hardware/BATTERY-MODEL.md` (read only)
- `.planning/workstreams/v1-2/{REQUIREMENTS,ROADMAP,STATE}.md`, `research/STACK.md`, `research/SUMMARY.md`, phase 51 CONTEXT (D-16)
- Experiment: rendered seven legacy cases locally and timed them (0.01-0.19 s each)

### Secondary (MEDIUM confidence)
- adsb.fi opendata README (https://github.com/adsbfi/opendata/blob/main/README.md), fetched 2026-10-30: 1 req/s, citation wording, "personal, non-commercial use only", "contact us" for higher rates

### Tertiary (LOW confidence)
- Web search summary of the adsb.lol API README (rate limits dynamic, future feeder key, "let me know" for production use); direct page fetch returned 403, repository README not opened. Also a competitor comparison page (flyitalyadsb.com) used only for context

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new packages, versions read from the lock file
- Architecture: HIGH for seams and reuse (code read); MEDIUM for the landscape composition (design choice)
- Pitfalls: HIGH - each tied to a concrete code location
- Provider contact facts: MEDIUM/LOW as marked

**Research date:** 2026-10-30
**Valid until:** 2026-11-30 for code facts (the tree is moving: Phases 52-55 are in flight in this workstream and touch `poll_cycle.py`, `routes.py`, `device_scope.py`); re-read those three files before executing if more than one phase lands first. Provider facts: 30 days.
