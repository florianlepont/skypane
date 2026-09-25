# Phase 35 comment ratios, per PR group

Recorded by each group-closing plan as it purges its files, using
`server/.venv/bin/python scripts/check_comment_history.py ratio --before
35-BASELINE/ratio-before.tsv --markdown <files>`. "Before" figures come from
`35-BASELINE/ratio-before.tsv` (measured on commit `83f4620` plus the
foundation plan's own additions); "after" figures are measured on this
group's own HEAD once its files are code-unchanged (proven by `same-code`)
and history-free (proven by `check`). A file above the ~35% review-trigger
guideline after purge is listed with a one-line justification pulled from
its plan's SUMMARY — the guideline is advisory, not a hard gate; the actual
gate is 0 history hits.

## Group 2 — server/

Source plans: 35-02 (`server/plane/{render,illustrations,colour_rules,
dither,runway_config}.py`), 35-03 (`server/plane/{calendar_rules,enrich,
detect,manual_resolutions}.py`), 35-04 (`server/poll_loop.py,
device_config.py, history_db.py, wake.py, notify.py, panel_format.py,
panel_preview.py, requirements.in, requirements-dev.in, .gitignore,
state/.gitignore`), 35-05 (every `server/test_*.py`).

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| server/.gitignore | 15 | 15 | 26.7% | 26.7% | 0 -> 0 |
| server/device_config.py | 1154 | 726 | 55.6% | 29.5% | 113 -> 0 |
| server/history_db.py | 723 | 539 | 47.0% | 28.9% | 28 -> 0 |
| server/notify.py | 212 | 130 | 60.4% | 35.4% | 25 -> 0 |
| server/panel_format.py | 145 | 99 | 66.2% | 50.5% | 19 -> 0 |
| server/panel_preview.py | 160 | 126 | 47.5% | 33.3% | 7 -> 0 |
| server/plane/__init__.py | 0 | 0 | 0.0% | 0.0% | 0 -> 0 |
| server/plane/calendar_rules.py | 2221 | 1418 | 61.8% | 40.2% | 118 -> 0 |
| server/plane/colour_rules.py | 532 | 394 | 44.4% | 25.6% | 27 -> 0 |
| server/plane/detect.py | 1129 | 857 | 58.9% | 45.9% | 46 -> 0 |
| server/plane/dither.py | 140 | 105 | 53.6% | 38.1% | 10 -> 0 |
| server/plane/enrich.py | 1157 | 773 | 68.7% | 50.6% | 95 -> 0 |
| server/plane/illustrations.py | 1177 | 884 | 43.5% | 24.8% | 93 -> 0 |
| server/plane/manual_resolutions.py | 508 | 430 | 53.5% | 45.1% | 28 -> 0 |
| server/plane/render.py | 3044 | 2049 | 52.1% | 29.1% | 312 -> 0 |
| server/plane/runway_config.py | 97 | 61 | 74.2% | 59.0% | 12 -> 0 |
| server/poll_loop.py | 1986 | 1307 | 56.8% | 34.4% | 218 -> 0 |
| server/requirements-dev.in | 32 | 32 | 68.8% | 68.8% | 3 -> 0 |
| server/requirements.in | 12 | 12 | 83.3% | 83.3% | 0 -> 0 |
| server/state/.gitignore | 2 | 2 | 0.0% | 0.0% | 0 -> 0 |
| server/test_calendar_rules.py | 2145 | 2140 | 13.5% | 13.3% | 24 -> 0 |
| server/test_colour_rules.py | 481 | 480 | 10.8% | 10.6% | 13 -> 0 |
| server/test_config_history.py | 1889 | 1857 | 16.8% | 16.2% | 44 -> 0 |
| server/test_dither.py | 100 | 100 | 29.0% | 29.0% | 12 -> 0 |
| server/test_enrich.py | 1044 | 1038 | 14.1% | 13.6% | 61 -> 0 |
| server/test_fault_screen_mask.py | 60 | 59 | 28.3% | 27.1% | 2 -> 0 |
| server/test_illustrations.py | 821 | 830 | 13.9% | 13.6% | 40 -> 0 |
| server/test_manual_resolutions.py | 353 | 352 | 11.9% | 11.6% | 14 -> 0 |
| server/test_notify.py | 207 | 207 | 24.2% | 24.2% | 7 -> 0 |
| server/test_panel_preview.py | 204 | 204 | 19.6% | 19.6% | 1 -> 0 |
| server/test_pipeline_e2e.py | 462 | 457 | 29.9% | 29.1% | 12 -> 0 |
| server/test_plane_detection.py | 1114 | 1115 | 31.2% | 31.3% | 12 -> 0 |
| server/test_poll_loop.py | 3268 | 3265 | 15.8% | 15.7% | 65 -> 0 |
| server/test_render.py | 3750 | 3190 | 27.5% | 14.5% | 186 -> 0 |
| server/test_runway_config.py | 154 | 152 | 22.1% | 21.1% | 6 -> 0 |
| server/wake.py | 442 | 201 | 71.3% | 37.3% | 36 -> 0 |
| **Group 2 total** | **30940** | **25606** | **37.2%** | **24.1%** | **1689 -> 0** |

The group total matches `35-BASELINE/INDEX.md`'s "before" row for group 2
(36 files, 30940 lines, 37% ratio, 1689 history hits) exactly, confirming
every file the baseline counted is accounted for here.

### Files still above the ~35% guideline

Each was re-read a second time in its plan hunting for restatement, scope
talk, and "who calls this" asides; nothing remained to cut without dropping
a genuine invariant. Justifications summarized from the source plan
SUMMARYs (35-02/35-03/35-04):

| File | After | Justification |
|---|---:|---|
| server/plane/runway_config.py | 59.0% | Smallest file in the group (61 lines); its entire content is one asymmetric-confidence warning (descend threshold real-flight-backed, climb threshold symmetry-derived and unverified) that purge_rules require to survive — a 61-line file with one paragraph of that density cannot sit under 35%. |
| server/plane/enrich.py | 50.6% | Dominated by one 46-entry curated ICAO-airline-prefix table where roughly a third of entries need a short correction/attribution rationale so a future contributor does not "fix" a deliberately non-obvious mapping; purely evidentiary citations were already stripped. |
| server/panel_format.py | 50.5% | Smallest file in its plan (99 lines): the `PALETTE_RGB` table carries necessarily-brief per-entry hardware-calibration annotations, and `pack_panel()`'s docstring is a genuine bit-manipulation correctness proof. |
| server/plane/detect.py | 45.9% | Two functions document a genuinely complex contract — the candidate-set cross-validation algorithm across two independent ADS-B feeders, and the geofence output-tag contract — both compressed to algorithmic essence, not restatement. |
| server/plane/manual_resolutions.py | 45.1% | Small, security-dense file by design: this project's first runtime-writable identity namespace, where nearly every function documents a distinct defence-in-depth layer (two-layer path safety, write-lock vs. a plain race, deliberate no-touch on delete). |
| server/plane/calendar_rules.py | 40.2% | Concentrates six largely-independent security/correctness domains (SSRF-hardened fetch, cross-process advisory lock, hand-rolled RFC 5545 subset parser, tamper-resistant registry with two DoS bounds, permission-drift detector, matching algorithm) each earning its own short why-comment. |
| server/plane/dither.py | 38.1% | Documents three distinct, non-obvious Pillow footguns (palette-pad, `.point()` remap, 6-colour quantizer misclassification) across four short functions in a 105-line file; four one-line invariants alone put it above 35%. |
| server/wake.py | 37.3% | Small module (201 lines) of precedence lists and staleness-threshold derivations shared by server and companion; `next_wake_status()`'s docstring documents a genuinely non-obvious two-call composition that is algorithmic why, not restatement. |
| server/notify.py | 35.4% | Sits essentially at the guideline: remaining comments are almost entirely the SSRF-gate-reuse and redirect-refusal security invariants purge_rules require to survive. |
| server/requirements-dev.in | 68.8% | Hash-comment dependency manifest, not Python code — nearly every line is a one-line why-comment explaining an install/lint/test package's purpose or dev-only scope; already history-free (3 -> 0 hits). |
| server/requirements.in | 83.3% | Hash-comment dependency manifest never carried any history reference (0 hits before and after) — its comments explain the runtime-only dependency policy and the regeneration procedure, not project history. |

## Group 3 — stub-server/

Source plan: 35-07 (`byos_server.py`, `devices_cli.py`, `make_test_panel.py`,
`test_devices_registry.py`, `test_poll_cycle.py`, `.gitignore`).
`stub-server/README.md` and `stub-server/VENDOR.md` are markdown, out of
scope for this phase (Phase 41), and carry no comment-syntax the tool
extracts (0 in both before and after).

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| stub-server/.gitignore | 10 | 10 | 30.0% | 30.0% | 0 -> 0 |
| stub-server/byos_server.py | 915 | 661 | 53.2% | 35.2% | 49 -> 0 |
| stub-server/devices_cli.py | 132 | 132 | 22.7% | 22.7% | 0 -> 0 |
| stub-server/make_test_panel.py | 120 | 110 | 41.7% | 36.4% | 0 -> 0 |
| stub-server/test_devices_registry.py | 459 | 459 | 12.0% | 12.0% | 0 -> 0 |
| stub-server/test_poll_cycle.py | 1279 | 1255 | 25.7% | 24.3% | 20 -> 0 |
| **Group 3 total** | **2915** | **2627** | **32.7%** | **25.4%** | **69 -> 0** |

The group total matches `35-BASELINE/INDEX.md`'s "before" row for group 3
(6 files, 2915 lines, 33% ratio, 69 history hits) exactly, confirming every
file the baseline counted is accounted for here.

### Files still above the ~35% guideline

Both files were re-read a second time hunting for restatement, scope talk
and paraphrase; both dropped close to the guideline (52.2% -> 35.2% and
41.7% -> 36.4%) before further compression risked cutting a genuine
invariant.

| File | After | Justification |
|---|---:|---|
| stub-server/byos_server.py | 35.2% | This is the device-protocol security surface the plan's own must_haves require to keep its why-comments (registry fail-closed vs. load_state()'s fail-open, timing-safe secret comparison, X-Battery-Mv input bounds, and four sleep_s composition functions whose nesting order is load-bearing and independently documented on each function). Sits essentially at the guideline after two compression passes. |
| stub-server/make_test_panel.py | 36.4% | Small file (110 lines) whose comments are the non-obvious Spectra 6 nibble-packing byte math (which pixel occupies which nibble, why the half-width split lands exactly on a byte-pair boundary) — algorithmic why for bit-twiddling code, not restatement. |

## Group 4 — companion production (Python)

Source plans: 35-08 (`companion/app.py`, `auth.py` and ten small modules), 35-09
(`companion/pages/config_page.py`), 35-10 (`companion/pages/health_page.py`,
`history_page.py`), 35-11 (`companion/layout.py`, `draw.py`), 35-12
(`companion/pages/airlines_page.py`, `home_page.py`, `pages/__init__.py`,
`companion/i18n_fr/*.py`), 35-13 (HYG-05: deletes `health_page.health_severity()`,
`health_page.anomaly_active()`, `draw.usable_pairs()`, `draw.label_grid()`, confirmed
dead against current main — see this plan's own SUMMARY). Figures below are measured
on this group's own HEAD, after 35-13's dead-code deletion, so `app.py`/`draw.py`/
`health_page.py` read slightly lower than the source plans' own mid-process numbers.

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| companion/__init__.py | 1 | 1 | 100.0% | 100.0% | 2 -> 0 |
| companion/app.py | 3744 | 2258 | 57.2% | 29.1% | 457 -> 0 |
| companion/auth.py | 540 | 398 | 51.7% | 34.4% | 43 -> 0 |
| companion/battery.py | 457 | 269 | 63.0% | 37.2% | 31 -> 0 |
| companion/contrast_check.py | 226 | 154 | 61.9% | 44.2% | 8 -> 0 |
| companion/draw.py | 1367 | 857 | 63.9% | 44.9% | 21 -> 0 |
| companion/frame_state.py | 216 | 102 | 69.9% | 36.3% | 17 -> 0 |
| companion/i18n.py | 42 | 29 | 66.7% | 51.7% | 4 -> 0 |
| companion/i18n_fr/__init__.py | 47 | 34 | 51.1% | 32.4% | 3 -> 0 |
| companion/i18n_fr/airlines.py | 140 | 108 | 41.4% | 24.1% | 26 -> 0 |
| companion/i18n_fr/calendar_group.py | 77 | 28 | 68.8% | 32.1% | 15 -> 0 |
| companion/i18n_fr/common.py | 236 | 200 | 27.5% | 14.5% | 20 -> 0 |
| companion/i18n_fr/display.py | 485 | 247 | 63.7% | 29.1% | 102 -> 0 |
| companion/i18n_fr/flights.py | 160 | 110 | 55.6% | 35.5% | 26 -> 0 |
| companion/i18n_fr/frame_state.py | 70 | 26 | 90.0% | 76.9% | 9 -> 0 |
| companion/i18n_fr/health.py | 383 | 317 | 38.9% | 26.2% | 43 -> 0 |
| companion/i18n_fr/home.py | 146 | 94 | 60.3% | 38.3% | 27 -> 0 |
| companion/i18n_fr/nav.py | 101 | 53 | 69.3% | 41.5% | 30 -> 0 |
| companion/i18n_fr/notifications.py | 72 | 44 | 62.5% | 38.6% | 16 -> 0 |
| companion/i18n_fr/registry.py | 59 | 46 | 54.2% | 41.3% | 3 -> 0 |
| companion/i18n_fr/rules.py | 74 | 44 | 63.5% | 45.5% | 10 -> 0 |
| companion/illustration_normalize.py | 153 | 86 | 68.6% | 44.2% | 4 -> 0 |
| companion/layout.py | 4168 | 2582 | 65.4% | 43.0% | 458 -> 0 |
| companion/pages/__init__.py | 176 | 71 | 100.0% | 100.0% | 35 -> 0 |
| companion/pages/airlines_page.py | 2503 | 1293 | 66.0% | 34.5% | 382 -> 0 |
| companion/pages/config_page.py | 6652 | 3384 | 66.6% | 34.5% | 932 -> 0 |
| companion/pages/health_page.py | 4675 | 2358 | 68.3% | 37.4% | 554 -> 0 |
| companion/pages/history_page.py | 1821 | 1144 | 61.3% | 38.4% | 190 -> 0 |
| companion/pages/home_page.py | 950 | 696 | 52.3% | 34.9% | 89 -> 0 |
| companion/prefs.py | 59 | 30 | 76.3% | 53.3% | 5 -> 0 |
| companion/screens.py | 139 | 81 | 68.3% | 45.7% | 26 -> 0 |
| companion/theme_preview.py | 376 | 208 | 62.5% | 32.2% | 25 -> 0 |
| companion/wake.py | 38 | 19 | 78.9% | 57.9% | 7 -> 0 |
| **Group 4 total** | **30353** | **17371** | **63.6%** | **36.4%** | **3620 -> 0** |

The group total's "before" figures (33 files, 30353 lines, 19291 comment lines, 64%,
3620 history hits) match `35-BASELINE/INDEX.md`'s group-4 row exactly, confirming
every file the baseline counted is accounted for here. The group-total ratio (36.4%)
sits just above the ~35% guideline because roughly two-thirds of the group's files
are individually above it (see below) — small catalogue and helper modules where a
short module docstring and a handful of per-function invariant sentences dominate a
file with little code to dilute them against.

### Files still above the ~35% guideline

Each file below was re-read at least twice in its source plan hunting for
restatement, scope talk and paraphrase before its plan accepted the guideline miss;
justifications are summarized from the source plan SUMMARYs (35-08/35-09/35-10/
35-11/35-12).

| File | After | Justification |
|---|---:|---|
| companion/__init__.py | 100.0% | A one-line file: a single docstring, no code at all. Ratio is not a meaningful signal at this size. |
| companion/battery.py | 37.2% | `battery_life_estimate()`'s docstring documents the one output-field contract every caller keys off; the curve-derivation and threshold-distinction comments are each short. |
| companion/contrast_check.py | 44.2% | A pure-stdlib WCAG 2.1 implementation with little code to dilute against: the spec URL pointers the purge rules require to keep, three calibration-number comments and one signal-separation-vs-contrast distinction. |
| companion/draw.py | 44.9% | Geometry/units invariants for every emitter (fixed coordinate domains, SVG dash-route degenerate cases, element-count bounds, measured-pixel derivations) — hard-capped at <=15-line docstrings/<=5-line blocks file-wide in 35-11's second pass; no caps exceptions remain. |
| companion/frame_state.py | 36.3% | A 102-line single-source-of-truth state machine; module and all four function docstrings hold only the state/delay contract sentences every consumer relies on. |
| companion/i18n.py | 51.7% | A 29-line module: one real function and its test-only sibling, each with a short never-raise contract — two documented functions in a file this size cannot go lower without dropping the contract itself. |
| companion/i18n_fr/flights.py | 35.5% | 110 lines; nine cross-module key reuses, each condensed to one line. |
| companion/i18n_fr/frame_state.py | 76.9% | Smallest file in the group (26 lines, 3 key/value pairs) carrying a genuinely load-bearing docstring (an unresolved grammatical-agreement mismatch) — three catalogue entries cannot dilute a docstring that size below 35%. |
| companion/i18n_fr/home.py | 38.3% | 94 lines; one key reused from nav.py plus copy style, on a file with modest code volume. |
| companion/i18n_fr/nav.py | 41.5% | 53 lines; docstring enumerates 7 locked nav labels plus cross-module grouping. |
| companion/i18n_fr/notifications.py | 38.6% | 44 lines; 6 keys deliberately routed through a different resolver — a real routing fact, not history. |
| companion/i18n_fr/registry.py | 41.3% | 46 lines; the id-vs-label distinction this cross-page catalogue depends on is necessarily stated once. |
| companion/i18n_fr/rules.py | 45.5% | 44 lines, 9 key/value pairs; docstring states 6 absent keys plus the identifier/data exclusion. |
| companion/illustration_normalize.py | 44.2% | An 86-line geometry module: the crop-box derivation constant comment and the two function docstrings are the file's only comments. |
| companion/layout.py | 43.0% | Hard-capped at <=15-line docstrings/<=5-line blocks file-wide in 35-11's second pass (same pass as draw.py above); keeps the `escape_html()` choke-point discipline, the icon-id injection-guard whitelist, the duplicated-not-imported route-constant contract with `app.py`, and the "exactly one Primary navigation landmark" accessibility invariant. No caps exceptions remain. |
| companion/pages/__init__.py | 100.0% | Pure-documentation file: the entire file is the module docstring describing every page module's `ctx`/`render(ctx)` contract (which keys are query-string-derived and re-validated on every use, which reads must never hit the process-scoped cache). Condensing it to the module-docstring cap would have deleted the per-key contract, not history. |
| companion/pages/health_page.py | 37.4% | Dominated by ~60 short helper functions, each needing one real why (a threshold's unit, a WCAG rule, an SVG coordinate-system constraint) — further compression began threatening load-bearing content rather than restatement, per 35-10's own documented stopping point. |
| companion/pages/history_page.py | 38.4% | Same pattern as health_page.py above: ~30 short helper functions, each with a real why (the untrusted `?limit=` clamp contract, the day-separator grouping rule). |
| companion/prefs.py | 53.3% | A 30-line module whose only content is the one-set-path/two-read-path invariant; the module docstring is at the small-file floor for stating it at all. |
| companion/screens.py | 45.7% | An 81-line registry module: module docstring plus short per-group split/render-order comments. |
| companion/wake.py | 57.9% | A 19-line re-export shim; the docstring explaining why the shim exists is the whole file's content — no numbered list or module tour to cut. |

Files close to, but under, the guideline (kept for completeness, no justification
needed): `companion/auth.py` (34.4%), `companion/theme_preview.py` (32.2%),
`companion/pages/airlines_page.py` (34.5%), `companion/pages/config_page.py`
(34.5%), `companion/pages/home_page.py` (34.9%).

## Group 5 — companion tests + test-support

Source plans: 35-14 (`companion/test_browser_*.py`), 35-15
(`companion/test_status_pages_*.py`, `test_view_pages_*.py`), 35-16 (every
remaining `companion/test_*.py`, `companion/conftest.py`,
`test-support/*.py`). "Before" figures come from
`35-BASELINE/ratio-before.tsv`, as for every other group; one file
(`companion/test_status_pages_01.py`) shows a "before" line count 9 lines
lower than 35-15's own mid-process figure (940 vs 949) because group 4's
dead-code deletion (35-13, removing `health_page.anomaly_active()`) touched
this test file between the phase baseline commit and group 5's own base
`8a8b8b4` — inlining a local `_anomaly_active()` helper. The baseline TSV
predates that edit; group 5's own same-code proof (below) is against
`8a8b8b4`, which already includes it, so no group-5 commit re-touches those
9 lines.

| File | Lines before | Lines after | Comment % before | Comment % after | History hits before -> after |
|---|---:|---:|---:|---:|---:|
| companion/conftest.py | 218 | 218 | 37.2% | 37.2% | 5 -> 0 |
| companion/test_app_server_fixture.py | 211 | 211 | 24.6% | 24.6% | 2 -> 0 |
| companion/test_browser_origin.py | 159 | 144 | 20.1% | 13.2% | 4 -> 0 |
| companion/test_browser_policy.py | 134 | 116 | 26.9% | 15.5% | 2 -> 0 |
| companion/test_browser_ux_01.py | 1408 | 1105 | 38.5% | 21.7% | 136 -> 0 |
| companion/test_browser_ux_02.py | 1954 | 1703 | 28.8% | 18.8% | 115 -> 0 |
| companion/test_browser_ux_03.py | 1844 | 1759 | 14.6% | 10.9% | 110 -> 0 |
| companion/test_browser_ux_04.py | 1486 | 1400 | 22.9% | 18.5% | 79 -> 0 |
| companion/test_browser_ux_health_drawings.py | 1794 | 1594 | 30.9% | 22.2% | 60 -> 0 |
| companion/test_browser_ux_helpers.py | 2717 | 1847 | 51.5% | 28.7% | 57 -> 0 |
| companion/test_browser_ux_quiet_wake.py | 1938 | 1665 | 32.1% | 21.0% | 73 -> 0 |
| companion/test_companion_app_01.py | 897 | 880 | 29.8% | 28.4% | 65 -> 0 |
| companion/test_companion_app_02.py | 1618 | 1577 | 21.9% | 20.5% | 72 -> 0 |
| companion/test_companion_app_03.py | 1541 | 1482 | 22.1% | 19.0% | 111 -> 0 |
| companion/test_companion_app_04.py | 967 | 944 | 18.9% | 16.9% | 39 -> 0 |
| companion/test_companion_app_04b.py | 904 | 887 | 22.6% | 21.1% | 28 -> 0 |
| companion/test_companion_app_05.py | 1661 | 1644 | 17.8% | 17.0% | 70 -> 0 |
| companion/test_companion_app_helpers.py | 197 | 186 | 41.1% | 37.6% | 3 -> 0 |
| companion/test_config_page_01.py | 658 | 631 | 22.3% | 19.0% | 57 -> 0 |
| companion/test_config_page_02.py | 2220 | 2159 | 31.1% | 29.1% | 157 -> 0 |
| companion/test_config_page_03.py | 1777 | 1722 | 28.6% | 26.3% | 125 -> 0 |
| companion/test_config_page_04.py | 938 | 905 | 23.0% | 20.2% | 68 -> 0 |
| companion/test_config_page_04b.py | 1000 | 967 | 22.0% | 19.3% | 81 -> 0 |
| companion/test_config_page_05.py | 1578 | 1526 | 20.3% | 17.6% | 128 -> 0 |
| companion/test_config_page_helpers.py | 145 | 108 | 54.5% | 38.9% | 10 -> 0 |
| companion/test_contrast_check.py | 335 | 335 | 27.2% | 27.2% | 0 -> 0 |
| companion/test_health_offbox.py | 269 | 265 | 12.3% | 10.9% | 7 -> 0 |
| companion/test_i18n.py | 287 | 286 | 21.3% | 21.0% | 3 -> 0 |
| companion/test_login_throttle.py | 182 | 180 | 22.0% | 21.1% | 6 -> 0 |
| companion/test_post_origin.py | 232 | 231 | 16.8% | 16.5% | 5 -> 0 |
| companion/test_status_pages_01.py | 940 | 898 | 24.5% | 20.3% | 53 -> 0 |
| companion/test_status_pages_02.py | 1726 | 1659 | 26.4% | 23.4% | 124 -> 0 |
| companion/test_status_pages_03.py | 1836 | 1744 | 25.2% | 21.3% | 139 -> 0 |
| companion/test_status_pages_04.py | 1351 | 1283 | 17.5% | 13.1% | 6 -> 0 |
| companion/test_status_pages_05.py | 797 | 739 | 28.2% | 22.6% | 77 -> 0 |
| companion/test_status_pages_05b.py | 803 | 748 | 25.8% | 20.3% | 31 -> 0 |
| companion/test_status_pages_06.py | 1540 | 1479 | 27.1% | 24.1% | 117 -> 0 |
| companion/test_status_pages_07.py | 1402 | 1346 | 28.2% | 25.1% | 74 -> 0 |
| companion/test_status_pages_helpers.py | 179 | 166 | 31.3% | 25.9% | 1 -> 0 |
| companion/test_suite_guards.py | 777 | 777 | 10.7% | 10.7% | 1 -> 0 |
| companion/test_view_pages_01.py | 637 | 630 | 15.5% | 14.6% | 44 -> 0 |
| companion/test_view_pages_02.py | 1431 | 1401 | 22.5% | 20.8% | 121 -> 0 |
| companion/test_view_pages_03.py | 1464 | 1445 | 14.4% | 13.3% | 74 -> 0 |
| companion/test_view_pages_04.py | 1699 | 1664 | 27.7% | 26.2% | 60 -> 0 |
| companion/test_view_pages_helpers.py | 122 | 115 | 42.6% | 39.1% | 0 -> 0 |
| test-support/companion_app_server.py | 320 | 318 | 26.6% | 26.1% | 2 -> 0 |
| test-support/companion_markup.py | 594 | 594 | 19.9% | 19.9% | 1 -> 0 |
| test-support/sitecustomize.py | 26 | 26 | 38.5% | 38.5% | 0 -> 0 |
| test-support/skypane_test_support.py | 391 | 391 | 23.8% | 23.8% | 0 -> 0 |
| test-support/test_check_comment_history.py | 534 | 545 | 6.0% | 5.9% | 0 -> 0 |
| test-support/test_companion_markup.py | 190 | 190 | 4.2% | 4.2% | 2 -> 0 |
| test-support/test_test_support.py | 284 | 284 | 6.0% | 6.0% | 0 -> 0 |
| **Group 5 total** | **50312** | **47119** | **25.7%** | **20.7%** | **2605 -> 0** |

The group total's history-hits figure (2605) matches the sum of the three source
plans' own family totals exactly (636 + 921 + 1048 = 2605), confirming every hit
the three plans purged is accounted for here. The line-count totals differ from
that same sum by 19 lines (50312 here vs 50331), entirely attributable to the
`test_status_pages_01.py` baseline-vs-group-base discrepancy explained above.

### Files still above the ~20%-per-file guideline

Group 5's own plans used a stricter ~20% per-file guideline than groups 2-4's
~35% (test files carry proportionally less code to dilute a why-comment
against, and the family sizes here made a lower bar practical). 30 of the 52
files sit above it after purge; every one was re-read at least once hunting
for restatement before its plan accepted the guideline miss, and none had
unpurged history left (all report 0 hits). Justifications are condensed from
the three source plans' own SUMMARYs, grouped by family:

- **`companion/conftest.py`** (37.2%), **`test_companion_app_helpers.py`**
  (37.6%), **`test_config_page_helpers.py`** (38.9%), **`test-support/
  sitecustomize.py`** (38.5%) — short, fixture-dense files (conftest's own
  scope-rationale comments, the two `*_helpers.py` modules' one-why-
  paragraph-per-helper shape, `sitecustomize.py`'s 26-line body where one
  why-comment is already a large fraction of the file).
- **`test_browser_ux_01.py`** (21.7%), **`_health_drawings.py`** (22.2%),
  **`_helpers.py`** (28.7%), **`_quiet_wake.py`** (21.0%) — the browser-UX
  family's dense multi-branch behaviour checks (motion/timing contracts,
  reduced-motion controls, save-floor helper parameter contracts) 35-14
  documented as genuine why-content, not restatement.
- **`test_companion_app_01.py`** (28.4%), **`_02.py`** (20.5%), **`_04b.py`**
  (21.1%) and the config_page family's **`_02.py`** (29.1%), **`_03.py`**
  (26.3%), **`_04.py`** (20.2%) — the dense multi-hundred-test files 35-16
  documented as carrying genuine why-content per assertion (root-safety
  notes, paint-order/geometry rationale, why a fixture value was chosen).
- **`test_status_pages_02.py`** through **`_07.py`**, **`_helpers.py`**,
  **`test_view_pages_02.py`** and **`_04.py`** — the status_pages/view_pages
  family's declaration-by-declaration stylesheet assertions, per-language
  render sweeps and corroboration/anomaly state matrices 35-15 documented
  as genuine why-content (root-safety notes, paint-order rationale, fixture
  value justification).
- **`test_view_pages_helpers.py`** (39.1%) — 35-15's documented extreme
  case: an eight-function, 115-line helper module where the ratio is
  inherent to the file's shape (short bodies, one why-paragraph each), not
  unpurged history.
- **`test_contrast_check.py`** (27.2%), **`test-support/skypane_test_
  support.py`** (23.8%), **`test-support/companion_app_server.py`** (26.1%)
  — already at these ratios before this group's own edits (0 -> 0 or a
  small hit count unrelated to the bulk of the file); confirmed already
  clean by 35-16 and left untouched or edited only at the specific hit
  lines.
- **`companion/test_i18n.py`** (21.0%), **`test_login_throttle.py`**
  (21.1%) — small standalone files (35-16) sitting a fraction of a point
  over the guideline after their few real hits were purged; no further
  content to cut without dropping a genuine invariant.

No `--allow` was used for any of these files' own body content; the two
same-code `--allow` flags this group needs (see below) are both scoped to a
module docstring alone, unrelated to which files exceed the ratio guideline.

### same-code and check evidence

`server/.venv/bin/python scripts/check_comment_history.py same-code --base
8a8b8b4 --allow companion/test_companion_app_02.py --allow
companion/test_suite_guards.py <the 47 files changed since 8a8b8b4>` exits
0. The two `--allow` flags are for `test_companion_app_02.py` and
`test_suite_guards.py`'s module docstrings alone — both mention the literal
substring `__doc__` in ordinary prose (discussing a banned pattern in the
first case, describing the guard's own detection rule in the second), which
trips `same-code`'s own `keep_module_doc = "__doc__" in base_text or
"__doc__" in working_text` heuristic (built for group 2's `illustrations.py`
argparse `--help` pattern) regardless of what the docstring itself says.
35-16 diagnosed and isolated both cases to exactly the module docstring by
forcing `keep_module_doc=False` and diffing the resulting AST dumps
(identical outside the docstring in both cases); this plan re-ran that same
proof at the group level and confirms it still holds after the merge with
`origin/main` (which touches no companion test or test-support file — see
`git diff 8a8b8b4 origin/main --stat -- companion test-support`, empty).

`check --paths <all 52 group-5 files>` reports 0 history hits.
