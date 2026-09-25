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
